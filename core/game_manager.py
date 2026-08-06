import inspect
import os
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from data import data as DATA
from data_manager import data_manager
from log import log_manager
from tool import tool, error_record

from .enums import OperationMode, GachaMode, RecruitMode, TaskType
from .task import Task, UserSuspendOperationError
from .task_manager import TaskManager
from .simulator import Simulator

log = log_manager

#==============================================
def execute_tasks(func):
    """
    装饰器：用于为类的方法添加任务执行功能。
    该装饰器将被装饰函数返回的任务列表自动添加到任务管理器并执行。
    
    参数：
        func (callable): 被装饰的函数，应返回一个任务列表。
    
    返回值：
        callable: 返回包装后的函数wrapper，该函数在执行时会自动处理任务添加和执行。
    """
    def wrapper(self, *args, **kwargs):
        # 调用被装饰的函数，获取任务列表
        tasks = func(self, *args, **kwargs)
        # 将每个任务添加到任务管理器
        for task in tasks:
            self.task_manager.add_task(task)
        # 执行任务管理器中的所有任务
        self.task_manager.execute_tasks()
    return wrapper

class GameManager(QObject):
    # 信号定义
    device_connected = Signal(bool)  # 设备连接状态信号
    operation_started = Signal()     # 操作开始信号
    operation_stopped = Signal()     # 操作停止信号
    operation_paused = Signal()      # 操作暂停信号
    operation_resumed = Signal()     # 操作恢复信号
    step_updated = Signal(str, str)  # 步骤更新信号
    macro_step_updated = Signal(str, str)  # 宏观步骤更新信号
    log_message = Signal(str, str)   # 日志消息信号(消息, 级别)
    data_updated = Signal()          # 数据更新通知
    
    def __init__(self):
        """初始化类的实例，设置默认属性和状态。

        参数：
        无

        返回值：
        无
        """
        super().__init__()  # 调用父类的初始化方法
        self.is_running = False  # 运行状态标志，初始为False
        self.is_paused = False  # 暂停状态标志，初始为False
        self.b_exist_rare_tag = False  # 是否存在稀有标签的布尔标志，初始为False
        self.current_mode = None  # 当前操作模式，初始为None
        self.execution_limit = 0  # 执行限制次数，初始为0
        self.b_special_stop = False  # 特殊停止标志，初始为False
        self.task_manager = None  # 任务管理器实例，初始为None
        self.top_item_count = 0  # 顶级物品计数，初始为0
        self.gacha_mode = GachaMode.SINGLE  # 抽卡模式，设置为单抽
        self.recruit_mode = RecruitMode.BREAK  # 招聘模式，设置为中断模式
    
        # 操作计数
        self.operation_count = 0  # 操作总次数，初始为0
        self.recruit_count = 0  # 招聘操作次数，初始为0
        self.gacha_count = 0  # 抽卡操作次数，初始为0

        self.set_use_originite(False)  # 设置使用起源石为False

    def record(self, item):
        """记录数据"""
        self.log_with_time("INFO", f"记录: {item}")
            
        if isinstance(item, list):
            s_record = "!".join(item)
        elif isinstance(item, str):
            s_record = item
        else:
            s_record = str(item)

        data_manager.update_data(s_record)
        self.data_updated.emit()

    def update_step(self, current_step: str, next_step: Optional[str] = None):
        """更新步骤信息"""
        # 发送步骤更新信号
        self.step_updated.emit(current_step, next_step)
        log_manager.update_step(current_step, next_step)
    
    def update_macro_step(self, level = "INFO", macro_step = None):
        """
        更新宏步骤并记录日志。

        参数:
        self -- 方法的实例对象。
        level (str): 日志级别，默认为 "INFO"。
        macro_step: 宏步骤的值，默认为 None。

        返回值:
        无返回值。
        """
        self.macro_step_updated.emit(macro_step, level)  # 发射宏步骤更新信号
        self.log_with_time(level, macro_step)  # 记录带时间的日志

    def _log(self, level = "INFO", message = None):
        """记录日志消息"""
        if message is None:
            return
        # 获取调用栈信息
        self.log_with_time(level, message)
    
    def log_with_time(self, level: str, message: str, filename: str = None, lineno: int = None):
        """带时间戳的日志记录"""
        if (filename is None) or (lineno is None):
            # 获取调用者信息
            frame = inspect.currentframe().f_back
            if frame:
                filename = os.path.basename(frame.f_code.co_filename)
                lineno = frame.f_lineno
        
        log_manager.log(message, level, filename, lineno)
    
    def connect_device(self, adb_path: str):
        """连接设备"""
        try:
            self.break_connection()
            self.task_manager = TaskManager()
            Task.simulator = Simulator(adb_path = adb_path)
            
            # 连接任务管理器信号
            self.task_manager.task_started.connect(self._on_task_started)
            self.task_manager.task_completed.connect(self._on_task_completed)
            self.task_manager.task_failed.connect(self._on_task_failed)
            self.task_manager.task_terminated.connect(self.reset_operation)
            self.task_manager.step_completed.connect(self._arrange_next_task)
            self.task_manager.device_disconnected.connect(lambda:self.device_connected.emit(False))
            
            # 连接自身信号
            self.operation_paused.connect(self.task_manager.pause_tasks)
            self.operation_resumed.connect(self.task_manager.resume_tasks)

            self.update_macro_step("INFO", "设备连接成功")
            self.device_connected.emit(True)
        except Exception as e:
            self.update_macro_step("ERROR", f"设备连接失败: {str(e)}")
            error_record(e)
            self.device_connected.emit(False)
    
    def break_connection(self):
        """
        功能：清理ADB连接，删除Task类的simulator属性和当前实例的task_manager属性。
        参数：无额外参数。
        返回值：无返回值。
        """
        try:
            # 检查Task类是否有simulator属性，如果有则删除
            if hasattr(Task, "simulator"):
                del Task.simulator
            # 检查当前实例是否有task_manager属性，如果有则删除
            if hasattr(self, "task_manager"):
                del self.task_manager
        except Exception as e:
            # 捕获异常，记录错误并输出日志
            error_record(e)
            self._log("ERROR", f"adb清理失败: {str(e)}")

    def set_gacha_mode(self, mode: GachaMode):
        """设置寻访模式"""
        self.gacha_mode = mode
        self.log_with_time("INFO", f"寻访模式已设置为：{mode.value}")
    
    def set_recruit_mode(self, mode: RecruitMode):
        """设置公招模式"""
        self.recruit_mode = mode
        self.log_with_time("INFO", f"公招模式已设置为：{mode.value}")
    
    def set_recruit_slot(self, slot: int):
        """设置公招栏位"""
        Task.aimRecruitSlot = slot
        self.log_with_time("INFO", f"公招栏位已设置为：{slot}")

    def set_gacha_pool(self, pool: int):
        """设置寻访池"""
        Task.aimGachaPage = pool
        self.log_with_time("INFO", f"寻访池已设置为：{pool}")

    def set_use_originite(self, use: bool):
        """设置是否使用源石"""
        if use:
            self.l_originiteCheckTask = []
        else:
            self.l_originiteCheckTask = [
                Task(TaskType.IF, "isOriginiteOnScreen", description="检查是否消耗源石"),
                [
                    Task(TaskType.CLICK_TEXT, "取消", description="取消操作"),
                    Task(TaskType.END, None),
                ]
            ]
        self.log_with_time("INFO", f"源石消耗已设置为：{'开启' if use else '关闭'}")

    def start_operation(self, mode: OperationMode, param: int):
        """开始操作"""
        if self.is_running:
            return
            
        self.is_running = True
        self.is_paused = False
        self.current_mode = mode
        if param >= 0:
            self.execution_limit = param
        elif param < 0:
            self.b_special_stop = True
        if mode == OperationMode.GACHA:
            self.update_macro_step("INFO", f"开始寻访, 次数:{'循环直到遇见好东西' if self.b_special_stop else ('无限循环' if self.execution_limit == 0 else self.execution_limit)}, 模式:{self.gacha_mode.value}, 源石消耗:{'开启' if not self.l_originiteCheckTask else '关闭'}, 寻访池:{Task.aimGachaPage}")
        elif mode == OperationMode.RECRUIT:
            self.update_macro_step("INFO", f"开始公招, 次数:{'循环直到遇见好东西' if self.b_special_stop else ('无限循环' if self.execution_limit == 0 else self.execution_limit)}, 模式:{self.recruit_mode.value}, 公招栏:{Task.aimRecruitSlot}")
        elif mode == OperationMode.PLAN:
            self.update_macro_step("ERROR", "自动规划未实现")
            self.reset_operation()
            return
            #self.update_macro_step(f"开始自动规划, 次数:{'循环直到遇见好东西' if self.b_special_stop else ('无限循环' if self.execution_limit == 0 else self.execution_limit)}, 公招模式:{self.recruit_mode.value}, 源石消耗:{'开启' if not self.l_originiteCheckTask else '关闭'}, 寻访池:{Task.aimGachaPage}")
        self.operation_started.emit()

        self._arrange_next_task()
    
    def pause_operation(self):
        """暂停操作"""
        if not self.is_running or self.is_paused:
            return
            
        self.is_paused = True
        self.update_macro_step("INFO", "操作已暂停")
        self.operation_paused.emit()
    
    def resume_operation(self):
        """恢复操作"""
        if not self.is_running or not self.is_paused:
            return
            
        self.is_paused = False

        self.update_macro_step("INFO", "操作已恢复")
        self.operation_resumed.emit()
    
    @Slot()
    def reset_operation(self):
        """重置操作状态"""
        self.is_running = False
        self.is_paused = False
        self.b_exist_rare_tag = False
        self.b_special_stop = False
        self.top_item_count = 0
        self.operation_count = 0
        self.recruit_count = 0
        self.gacha_count = 0
        if self.task_manager:
            self.task_manager.stop_tasks()
        self.operation_stopped.emit()
        self.update_step("", "")
        self.update_macro_step("INFO", "操作已重置")
    
    @Slot()
    def _arrange_next_task(self):
        if not self.is_running or self.is_paused:
            return

        try:
            if self.current_mode == OperationMode.GACHA:
                if self.gacha_mode == GachaMode.SINGLE:
                    self.update_macro_step("INFO", f"开始第{self.gacha_count+1}次寻访")
                    self.taskAdd_gacha_once()
                    self.gacha_count += 1
                    self.operation_count += 1
                elif self.gacha_mode == GachaMode.TEN:
                    if self.execution_limit > 0 and self.execution_limit - self.operation_count < 10:
                        self.gacha_mode = GachaMode.SINGLE
                        self._arrange_next_task()
                    self.update_macro_step("INFO", f"开始第{self.gacha_count+1}~{self.gacha_count+10}次寻访")
                    self.taskAdd_gacha_ten()
                    self.gacha_count += 10
                    self.operation_count += 10
            
            elif self.current_mode == OperationMode.RECRUIT:
                self.operation_count += 1
                self.recruit_count += 1
                self.update_macro_step("INFO", f"开始第{self.recruit_count}次公招")
                self.taskAdd_recruit_enter()
                if self.recruit_mode == RecruitMode.BREAK:
                    self.taskAdd_recruit_break()
                elif self.recruit_mode == RecruitMode.ACCELERATE:
                    self.taskAdd_recruit_accelerate()
            
            elif self.current_mode == OperationMode.PLAN:
                # self.log_with_time("INFO", f"开始第{self.operation_count}次规划")
                # TODO: 实现自动规划功能
                # (!！AI！!)
                pass
            
            # 检查是否达到目标（为0的时候无限制）
            if  (
                (self.b_special_stop and
                    (self.b_exist_rare_tag or (self.top_item_count > 0))
                )
                or
                ((not self.b_special_stop) and
                    self.execution_limit > 0 and self.operation_count >= self.execution_limit
                )
                ):
                self.update_macro_step("INFO", "已达到目标，操作结束")
                if self.current_mode == OperationMode.GACHA and self.gacha_mode == GachaMode.TEN:
                    self.taskAdd_tenModeEndUp()
                elif self.current_mode == OperationMode.RECRUIT:
                    self.taskAdd_recruitEndUp()
                else:
                    self.taskAdd_endUp()
                self.is_running = False
        except Exception as e:
            error_record(e)
            self.log_with_time("ERROR", f"任务分配过程中发生错误：{str(e)}")
            self.reset_operation()

    @Slot()
    def _on_task_started(self, description: str):
        """任务开始处理，更新步骤"""
        next_task = self.task_manager.get_next_task_description()
        self.update_step(description, next_task)
    
    @Slot()
    def _on_task_completed(self, result):
        """任务完成处理"""
        if result is True:
            return
        try:
            # result = (success: bool, taskType: TaskType, result)
            b_success, taskType, result = result

            if taskType == TaskType.RECORD_TAG:
                if not b_success:
                    self.pause_operation()
                    self.log_with_time("WARNING", f"tag无法识别")
                    result = self.parent().handle_missing_tag(result) # result: img
                    if result is None:
                        self.log_with_time("ERROR", "用户取消输入tag")
                        raise UserSuspendOperationError("用户取消操作")
                    self.resume_operation()
                self.log_with_time("INFO", f"获得tag：{', '.join(result)}")
                self.record(result)
                # 检查是否有罕见tag
                rare_tags = [tag for tag in result if DATA.is_special(tag)]
                if rare_tags:
                    self.update_macro_step("INFO", f"出现罕见tag:{', '.join(rare_tags)}！")
                    self.b_exist_rare_tag = True

            elif taskType == TaskType.RECORD_AGENT:
                if not b_success:
                    self.pause_operation()
                    self.log_with_time("WARNING", f"干员无法识别")
                    result = self.parent().handle_missing_agent(result) # result: img
                    if result is None:
                        self.log_with_time("ERROR", "用户取消输入干员")
                        raise UserSuspendOperationError("用户取消操作")
                    self.resume_operation()
                self.log_with_time("INFO", f"获得干员：{result}")
                self.record(result)
                # 检查是否为六星干员
                if result in DATA.d_agent and int(DATA.d_agent[result]["star"])+1 == 6:
                    self.update_macro_step("INFO", f"获得六星干员{result}！")
                    self.top_item_count += 1

            elif taskType == TaskType.RECORD_HISTORY_PAGE:
                if not b_success:
                    self.pause_operation()
                    self.log_with_time("WARNING", f"记录无法识别")
                    result = self.parent().handle_missing_record(result) # result: (img, l_agent)
                    if result is None:
                        self.log_with_time("ERROR", "用户取消输入记录")
                        raise UserSuspendOperationError("用户取消操作")
                    self.resume_operation()
                self.log_with_time("INFO", f"获得记录：{result}")
                for agent in result:
                    self.record(agent)
                    # 检查是否为六星干员
                    if agent in DATA.d_agent and int(DATA.d_agent[agent]["star"])+1 == 6:
                        self.update_macro_step("INFO", f"获得六星干员{agent}！")
                        self.top_item_count += 1

            elif taskType == TaskType.RECORD_SCREEN and not b_success:
                self.log_with_time("ERROR", f"屏幕识别失败，正在保存截图")
                log.img(result)
                raise ValueError(f"屏幕识别失败，截图已保存")

            elif taskType == TaskType.RECORD_HISTORY_FLEX and not b_success:
                self.log_with_time("ERROR", f"历史记录识别失败，正在保存截图")
                log.img(result)
                raise ValueError(f"历史记录识别失败，截图已保存")

            elif taskType == TaskType.CLICK_BEST_TAGS and not b_success:
                self.log_with_time("ERROR", f"tag点击识别结果：{result}，数量不正确，失败")
                raise ValueError(f"tag点击识别结果：{result}，数量不正确，失败")

        except Exception as e:
            error_record(e)
            log.error(str(e))
            self.reset_operation()

    @Slot()
    def _on_task_failed(self, error: str):
        """任务失败处理"""
        self.log_with_time("ERROR", f"出现错误：{error}")
        self.reset_operation()

    @execute_tasks
    def taskAdd_recruitEndUp(self):
        return [
            Task(TaskType.ENTER_SLOT, None, post_wait=0.3, description="进入公招池"),
            Task(TaskType.RECORD_TAG, None),
            Task(TaskType.CLICK_IMG, "RecruitRefuse", b_reuse=True, description="点击×退出"),
            Task(TaskType.END, None),
        ]
    @execute_tasks
    def taskAdd_tenModeEndUp(self):
        """执行十连抽模式的结束任务流程。

        功能：构建并返回一系列在十连抽模式结束时需要执行的任务列表，包括查看结果、查询记录、记录历史等步骤。
        参数：无（除 self 外）
        返回值：list[Task] - 一个包含多个Task对象的列表，按顺序描述了要执行的操作。
        """
        return [
            Task(TaskType.CLICK_TEXT, "查看详情", b_reuse=True, description="点击查看详情"),  # 点击“查看详情”按钮，查看本次抽取结果
            Task(TaskType.CLICK_TEXT, "查询记录", b_reuse=True, description="点击查询记录"),  # 点击“查询记录”按钮，打开历史记录页面
            Task(TaskType.RECORD_HISTORY_FLEX, self.gacha_count, pre_wait=0.3, description="记录招募历史"),  # 记录本次招募的历史数据，等待页面稳定
            Task(TaskType.CLICK_IMG, "gachaHistoryButton_exit", b_reuse=True, description="点击×退出"),  # 点击历史记录页面的“×”关闭按钮
            Task(TaskType.CLICK_TEXT, None, pre_wait=0.3, description="点击任意位置退出"),  # 点击屏幕任意空白处，确保完全退出历史页面
            Task(TaskType.END, None),  # 标记整个任务流程结束
        ]
    @execute_tasks
    def taskAdd_endUp(self):
        """用于生成并返回一个“结束”类型的任务。

        该方法创建一个指定任务类型为 END 的 Task 对象，并将其封装在一个列表中返回。
        这通常用于标志某个任务序列或流程的终止点。

        参数:
            self: 表示类的实例本身。

        返回:
            list: 一个包含单个 Task 对象的列表，该对象的类型为 TaskType.END。
        """
        return [
            Task(TaskType.END, None),  # 创建一个类型为 END、无额外参数的任务实例
        ]
    @execute_tasks
    def taskAdd_recordScreen(self):
        """
        功能：创建并返回一个任务列表，用于记录屏幕活动。该方法生成一个包含开始记录屏幕和结束任务的序列，通常用于自动化任务流程。

        参数：
            self: 表示类实例本身，用于访问实例属性和方法。

        返回值：
            list: 返回一个列表，包含两个Task对象。第一个Task对象的任务类型为RECORD_SCREEN，表示开始记录屏幕；第二个Task对象的任务类型为END，表示结束任务。两个任务的附加参数均为None。
        """
        return [
            Task(TaskType.RECORD_SCREEN, None),  # 创建开始记录屏幕的任务对象，参数为None表示无额外设置
            Task(TaskType.END, None),  # 创建结束任务的任务对象，用于终止任务序列
        ]
    @execute_tasks
    def taskAdd_recruit_enter(self):
        return [
            Task(TaskType.ENTER_SLOT, None, post_wait=0.3, description="进入公招池"),
            Task(TaskType.RECORD_TAG, None),
        ]
    @execute_tasks
    def taskAdd_recruit_break(self):
        return [
            Task(TaskType.CLICK_IMG, "RecruitConfirm", b_reuse=True, description="点击对勾开始招募"),
            Task(TaskType.CLICK_TEXT, "停止招募", b_recruitCheck=True, description="点击停止招募"),
            Task(TaskType.CLICK_TEXT, "确认停止", b_recruitCheck=True, description="点击确认停止"),
            Task(TaskType.STEP_COMPLETED, None),
        ]
    @execute_tasks
    def taskAdd_recruit_accelerate(self):
        return [
            Task(TaskType.CLICK_IMG, "RecruitTimerDecrement", b_reuse=True, description="点击向下箭头增加时间"),
            Task(TaskType.CLICK_BEST_TAGS, None, description="选好tag"),
            Task(TaskType.CLICK_IMG, "RecruitConfirm", b_reuse=True, description="点击对勾开始招募"),
            Task(TaskType.CLICK_TEXT, "立即招募", b_recruitCheck=True, description="点击立即招募"),
            Task(TaskType.CLICK_IMG, "RecruitNowConfirm", b_reuse=True, description="确认使用加速券"),
            Task(TaskType.CLICK_TEXT, "聘用候选人", b_recruitCheck=True, description="点击聘用候选人"),
            Task(TaskType.CLICK_TEXT, "SKIP", b_reuse=True, description="点击SKIP"),
            Task(TaskType.WHILE, "isCertificateOnScreen", description="检查是否有凭证可以点击"),
            [
                Task(TaskType.CLICK_TEXT, None, description="点击任意处"),
            ],
            Task(TaskType.STEP_COMPLETED, None),
        ]
    @execute_tasks
    def taskAdd_gacha_once(self):
        """生成并返回“进行一次寻访”（即单抽）的完整任务序列。

        功能:
            该方法编排了一次标准的抽卡（寻访）流程所需的所有自动化操作步骤。
            流程包括：发起单次寻访、处理可能的原石检查、确认寻访、跳过动画、
            处理可能出现的凭证（如五星干员）展示画面，以及最终完成任务。

        参数:
            self: 类实例对象。

        返回值:
            list[Task]: 一个Task对象的列表，按顺序描述了完成单次寻访所需的全部操作。
        """
        return ([
            Task(TaskType.CLICK_TEXT, "寻访一次", b_reuse=True, description="点击寻访一次"),
            ] + 
            self.l_originiteCheckTask + # 拼接来自实例变量的任务列表，通常用于检查和处理原石（抽卡资源）
            [
            Task(TaskType.CLICK_TEXT, "确认", b_reuse=True, description="点击确认寻访"),
            #Task(TaskType.CLICK_TEXT, "SKIP", b_reuse=True, post_wait=0.3, description="点击SKIP"), # 注释掉的另一种SKIP方式
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.98, 0.02), pre_wait=0.5, description="点击SKIP"), # 使用相对坐标点击屏幕右上角的SKIP按钮
            Task(TaskType.RECORD_AGENT, None), # 记录一个Agent操作（可能用于状态跟踪或回放）
            Task(TaskType.WHILE, "isCertificateOnScreen", description="检查是否有凭证可以点击"), # 循环开始：检查屏幕上是否出现“凭证”（例如获得高星干员时的展示）
            [   # 循环体：如果凭证出现，则执行以下任务
                Task(TaskType.CLICK_TEXT, None, description="点击任意处"), # 点击屏幕任意位置以关闭凭证展示
            ],
            Task(TaskType.STEP_COMPLETED, None), # 标记当前任务步骤（单抽流程）完成
        ])
    @execute_tasks
    def taskAdd_gacha_ten(self):
        """执行十次寻访（抽卡）的完整任务序列
    
        功能：生成一个任务列表，该列表依次包含以下操作：
        1. 点击“寻访十次”按钮
        2. 执行必要的源石检查任务
        3. 点击“确认”按钮进行寻访
        4. 跳过动画和结果展示
        5. 标记任务完成
    
        参数：无（使用self访问实例属性）
    
        返回值：包含多个Task对象的列表，用于自动化执行十次寻访流程
        """
        return ([
            Task(TaskType.CLICK_TEXT, "寻访十次", b_reuse=True, description="点击寻访十次"),  # 第一步：点击十次寻访按钮
            ] + 
            self.l_originiteCheckTask +  # 第二步：插入源石检查任务（如果需要）
            [
            Task(TaskType.CLICK_TEXT, "确认", b_reuse=True, description="点击确认寻访"),  # 第三步：确认寻访操作
            #Task(TaskType.CLICK_TEXT, "SKIP", b_reuse=True, description="点击SKIP"),  # 被注释的跳过按钮
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.98, 0.02), pre_wait=0.5, description="点击SKIP"),  # 第四步：点击右上角跳过按钮（相对坐标）
            Task(TaskType.CLICK_TEXT, None, pre_wait=2.5, description="点击任意位置跳过干员"),  # 第五步：等待2.5秒后点击任意位置跳过干员展示
            #Task(TaskType.CLICK_TEXT, None, pre_wait=0.5, description="点击任意位置跳过信物"),  # 被注释的跳过信物展示
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.5, 0.9), pre_wait=0.5, description="点击屏幕下方"),  # 第六步：点击屏幕下方区域（可能是为了返回主界面）
            Task(TaskType.STEP_COMPLETED, None),  # 第七步：标记任务步骤完成
        ])
    @execute_tasks
    def taskAdd_gacha_tenWithRecord(self):
        return ([
            Task(TaskType.CLICK_TEXT, "寻访十次", b_reuse=True, description="点击寻访十次"),
            ] + 
            self.l_originiteCheckTask + 
            [
            Task(TaskType.CLICK_TEXT, "确认", b_reuse=True, description="点击确认寻访"),
            #Task(TaskType.CLICK_TEXT, "SKIP", b_reuse=True, description="点击SKIP"),
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.98, 0.02), pre_wait=0.5, description="点击SKIP"),
            Task(TaskType.CLICK_TEXT, None, pre_wait=2.5, description="点击任意位置跳过干员"),
            #Task(TaskType.CLICK_TEXT, None, pre_wait=0.5, description="点击任意位置跳过信物"),
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.5, 0.9), pre_wait=0.5, description="点击屏幕下方"),
            Task(TaskType.CLICK_TEXT, "查看详情", b_reuse=True, description="点击查看详情"),
            Task(TaskType.CLICK_TEXT, "查询记录", b_reuse=True, description="点击查询记录"),
            Task(TaskType.RECORD_HISTORY_PAGE, None, pre_wait=0.3, description="记录一页招募历史"),
            Task(TaskType.CLICK_IMG, "gachaHistoryButton_exit", b_reuse=True, description="点击×退出"),
            Task(TaskType.CLICK_TEXT, None, pre_wait=0.3, description="点击任意位置退出"),
            Task(TaskType.STEP_COMPLETED, None),
        ])