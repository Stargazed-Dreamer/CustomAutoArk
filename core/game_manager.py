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
    def wrapper(self, *args, **kwargs):
        tasks = func(self, *args, **kwargs)
        for task in tasks:
            self.task_manager.add_task(task)
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
        super().__init__()
        self.is_running = False
        self.is_paused = False
        self.b_exist_rare_tag = False
        self.current_mode = None
        self.execution_limit = 0
        self.b_special_stop = False
        self.task_manager = None
        self.top_item_count = 0
        self.gacha_mode = GachaMode.SINGLE
        self.recruit_mode = RecruitMode.BREAK
        
        # 操作计数
        self.operation_count = 0
        self.recruit_count = 0
        self.gacha_count = 0

        self.set_use_originite(False)

    def record(self, item):
        """记录数据"""
        self.log_with_time("INFO", f"记录: {item}")
            
        if isinstance(item, list):
            s_record = "!".join(item)
        if isinstance(item, str):
            s_record = item
        
        data_manager.update_data(s_record)
        self.data_updated.emit()

    def update_step(self, current_step: str, next_step: Optional[str] = None):
        """更新步骤信息"""
        # 发送步骤更新信号
        self.step_updated.emit(current_step, next_step)
        log_manager.update_step(current_step, next_step)
    
    def update_macro_step(self, level = "INFO", macro_step = None):
        self.macro_step_updated.emit(macro_step, level)
        self.log_with_time(level, macro_step)

    def _log(self, level = "INFO", message = None):
        """记录日志消息"""
        if message is None:
            return
        # 获取调用栈信息
        error_record(e)
    
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
        try:
            if hasattr(Task, "simulator"):
                del Task.simulator
            if hasattr(self, "task_manager"):
                del self.task_manager
        except Exception as e:
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
        return [
            Task(TaskType.CLICK_TEXT, "查看详情", b_reuse=True, description="点击查看详情"),
            Task(TaskType.CLICK_TEXT, "查询记录", b_reuse=True, description="点击查询记录"),
            Task(TaskType.RECORD_HISTORY_FLEX, self.gacha_count, pre_wait=0.3, description="记录招募历史"),
            Task(TaskType.CLICK_IMG, "gachaHistoryButton_exit", b_reuse=True, description="点击×退出"),
            Task(TaskType.CLICK_TEXT, None, pre_wait=0.3, description="点击任意位置退出"),
            Task(TaskType.END, None),
        ]
    @execute_tasks
    def taskAdd_endUp(self):
        return [
            Task(TaskType.END, None),
        ]
    @execute_tasks
    def taskAdd_recordScreen(self):
        return [
            Task(TaskType.RECORD_SCREEN, None),
            Task(TaskType.END, None),
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
        return ([
            Task(TaskType.CLICK_TEXT, "寻访一次", b_reuse=True, description="点击寻访一次"),
            ] + 
            self.l_originiteCheckTask + 
            [
            Task(TaskType.CLICK_TEXT, "确认", b_reuse=True, description="点击确认寻访"),
            #Task(TaskType.CLICK_TEXT, "SKIP", b_reuse=True, post_wait=0.3, description="点击SKIP"),
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.98, 0.02), pre_wait=0.5, description="点击SKIP"),
            Task(TaskType.RECORD_AGENT, None),
            Task(TaskType.WHILE, "isCertificateOnScreen", description="检查是否有凭证可以点击"),
            [
                Task(TaskType.CLICK_TEXT, None, description="点击任意处"),
            ],
            Task(TaskType.STEP_COMPLETED, None),
        ])
    @execute_tasks
    def taskAdd_gacha_ten(self):
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
            Task(TaskType.STEP_COMPLETED, None),
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