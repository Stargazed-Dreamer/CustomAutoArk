import os
import time
from datetime import datetime
from PySide6.QtCore import QObject, Signal
from arknights_automation import Tool, MUMU, CantFindNameError, MouseMoveError
from utils.data_manager import DataManager
from data import l_tag0, l_tag1, l_tag2, l_tag3, l_tag4, d_agents
from log import log_manager
import threading
import cv2

class GameManager(QObject):
    # 信号定义
    device_connected = Signal(bool)  # 设备连接状态信号
    operation_started = Signal()     # 操作开始信号
    operation_stopped = Signal()     # 操作停止信号
    operation_paused = Signal()      # 操作暂停信号
    operation_resumed = Signal()     # 操作恢复信号
    step_updated = Signal(str, str)  # 步骤更新信号
    log_message = Signal(str)        # 日志消息信号
    count_updated = Signal(int)      # 计数更新
    data_updated = Signal()          # 数据更新通知
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_paused = False
        self.tool = Tool()
        self.mumu = None
        self.current_mode = None
        self.current_param = None
        
        # 使用全局日志管理器
        self.log = log_manager
        
        # 数据管理器初始化
        self.data_manager = DataManager()
        
        # 重试相关配置
        self.max_retries = 3
        self.retry_delay = 1
        
        # 操作计数
        self.operation_count = 0
        
        # 上次日期记录（用于日期分隔）
        self.last_date = None
        
        # 加载标签和干员数据
        self.tags = l_tag0 + l_tag1 + l_tag2 + l_tag3 + l_tag4
        self.agents = d_agents
    
    def load_data(self, file_path: str) -> bool:
        """加载数据文件"""
        success = self.data_manager.load_data(file_path)
        if success:
            self.log_with_time("INFO", f"数据加载成功: {file_path}")
            self.data_updated.emit()
        else:
            self.log_with_time("ERROR", f"数据加载失败: {file_path}")
        return success
    
    def save_data(self, file_path: str = None) -> bool:
        """保存数据到文件"""
        success = self.data_manager.save_data(file_path)
        if success:
            self.log_with_time("INFO", f"数据保存成功: {file_path or self.data_manager.file_path}")
        else:
            self.log_with_time("ERROR", f"数据保存失败: {file_path or self.data_manager.file_path}")
        return success
    
    def record(self, item):
        """记录数据"""
        self.log_with_time("INFO", f"记录: {item}")
            
        if isinstance(item, list):
            s_record = "!".join(item)
        if isinstance(item, str):
            s_record = item
        
        self.data_manager.update_data(s_record)
        self.data_updated.emit()

    def update_step(self, current_step: str, next_step: str = None):
        """更新步骤信息"""
        if next_step:
            self.log_with_time("INFO", f"正在进行：{current_step}\n即将进行：{next_step}", True)
        else:
            self.log_with_time("INFO", f"正在进行：{current_step}", True)
    
    def update_count(self, count: int):
        """更新计数"""
        self.operation_count = count
        self.count_updated.emit(count)
    
    def check_date_separator(self):
        """检查是否需要添加日期分隔符"""
        current_date = datetime.now().date()
        if self.last_date is None or current_date != self.last_date:
            self.last_date = current_date
            separator = f"\n--{current_date.strftime('%Y.%m.%d')}--\n"
            self.log_message.emit(separator)
    
    def _log(self, level: str, message: str, is_step: bool = False):
        """统一的日志处理方法"""
        # 发送日志到日志栏
        getattr(self.log, level.lower())(message, is_step)
    
    def log_with_time(self, level: str, message: str, is_step: bool = False):
        """
        记录带时间戳的日志
        :param level: 日志级别
        :param message: 日志消息
        :param is_step: 是否为步骤信息
        """
        # 记录到日志系统
        if level == "DEBUG":
            self.log.debug(message, is_step)
        elif level == "INFO":
            self.log.info(message, is_step)
        elif level == "WARNING":
            self.log.warning(message, is_step)
        elif level == "ERROR":
            self.log.error(message, is_step)
        elif level == "CRITICAL":
            self.log.critical(message, is_step)
    
    def save_screenshot(self, img, prefix="screenshot"):
        """
        保存截图
        :param img: 图片数据
        :param prefix: 文件名前缀
        :return: 保存的文件路径
        """
        if img is None:
            return None
        
        return self.log.img(img, prefix)
    
    def retry_operation(self, operation, *args, **kwargs):
        """通用重试机制"""
        retries = 0
        last_exception = None
        
        while retries < self.max_retries:
            try:
                return operation(*args, **kwargs)
            except (CantFindNameError, MouseMoveError) as e:
                last_exception = e
                retries += 1
                if retries < self.max_retries:
                    self.log_with_time("WARNING", f"操作失败: {str(e)}, 第{retries}次重试")
                    time.sleep(self.retry_delay)
                continue
            except Exception as e:
                self.log_with_time("ERROR", f"发生未预期的错误: {str(e)}")
                raise e
        
        self.log_with_time("ERROR", f"操作失败，已达到最大重试次数: {str(last_exception)}")
        return None

    def connect_device(self, adb_path: str):
        """连接设备"""
        try:
            self.mumu = MUMU(adb_path)
            self._log("INFO", "设备连接成功")
            self.device_connected.emit(True)
        except Exception as e:
            self._log("ERROR", f"设备连接失败: {str(e)}")
            self.device_connected.emit(False)
    
    def start_operation(self, mode: str, param: int):
        """开始操作"""
        if self.is_running:
            return
            
        self.is_running = True
        self.is_paused = False
        self.current_mode = mode
        self.current_param = param
        
        self._log("INFO", f"开始{mode}操作，参数: {param}")
        self.operation_started.emit()
        
        # 启动操作线程
        self.operation_thread = threading.Thread(target=self._operation_loop)
        self.operation_thread.start()
    
    def pause_operation(self):
        """暂停操作"""
        if not self.is_running or self.is_paused:
            return
            
        self.is_paused = True
        self._log("INFO", "操作已暂停")
        self.operation_paused.emit()
    
    def resume_operation(self):
        """恢复操作"""
        if not self.is_running or not self.is_paused:
            return
            
        self.is_paused = False
        self._log("INFO", "操作已恢复")
        self.operation_resumed.emit()
    
    def reset_operation(self):
        """重置操作"""
        self.is_running = False
        self.is_paused = False
        self._log("INFO", "操作已重置")
        self.operation_stopped.emit()
    
    def _operation_loop(self):
        """操作循环"""
        try:
            while self.is_running:
                if self.is_paused:
                    time.sleep(1)
                    continue
                    
                if self.current_mode == "干员寻访":
                    self._do_draw()
                elif self.current_mode == "公开招募":
                    self._do_recruit()
                else:
                    self._do_auto_plan()
                    
                time.sleep(1)
        except Exception as e:
            self._log("ERROR", f"操作执行出错: {str(e)}")
        finally:
            self.reset_operation()
    
    def _do_draw(self):
        """执行抽卡"""
        try:
            self.update_step("抽卡", "正在执行抽卡操作")
            agent = self.mumu.draw()
            if agent:
                self.log_with_time("INFO", f"抽到干员: {agent}", True)
                self.record(agent)
            else:
                self.log_with_time("WARNING", "未能识别抽到的干员", True)
        except Exception as e:
            self.log_with_time("ERROR", f"抽卡失败: {str(e)}", True)
    
    def _do_recruit(self):
        """执行公招"""
        try:
            self.update_step("公招", "正在执行公招操作")
            tags = self.mumu.recruit()
            if tags:
                self.log_with_time("INFO", f"获得标签: {', '.join(tags)}", True)
                self.record(tags)
            else:
                self.log_with_time("WARNING", "未能识别公招标签", True)
        except Exception as e:
            self.log_with_time("ERROR", f"公招失败: {str(e)}", True)
    
    def _do_auto_plan(self):
        """执行自动规划"""
        try:
            self.update_step("自动规划", "正在执行自动规划")
            # TODO: 实现自动规划逻辑
            self.log_with_time("INFO", "自动规划执行完成", True)
        except Exception as e:
            self.log_with_time("ERROR", f"自动规划失败: {str(e)}", True)
    
    def do_single_gacha(self):
        """执行单次抽卡"""
        try:
            self.update_step("单抽", "正在执行单次抽卡")
            agent = self.mumu.draw()
            if agent:
                self.log_with_time("INFO", f"抽到干员: {agent}", True)
                self.record(agent)
            else:
                self.log_with_time("WARNING", "未能识别抽到的干员", True)
        except Exception as e:
            self.log_with_time("ERROR", f"单抽失败: {str(e)}", True)
    
    def do_single_recruit(self):
        """执行单次公招"""
        try:
            self.update_step("单招", "正在执行单次公招")
            tags = self.mumu.recruit()
            if tags:
                self.log_with_time("INFO", f"获得标签: {', '.join(tags)}", True)
                self.record(tags)
            else:
                self.log_with_time("WARNING", "未能识别公招标签", True)
        except Exception as e:
            self.log_with_time("ERROR", f"单招失败: {str(e)}", True)
    
    def do_record_screen(self):
        """记录当前画面数据"""
        try:
            self.update_step("记录", "正在记录当前画面")
            img = self.mumu.screenshot()
            if img is not None:
                if self._log.img(img) is not None:
                    self.log_with_time("INFO", f"画面已保存")
                
                l_tags = self.tool.getTag(img)
                agent = self.tool.getAgent(img)
                
                if agent is not None:
                    self.record(agent)
                elif len(l_tags) == 5:
                    self.record(l_tags)
                self.log_with_time("WARNING", "未识别到有效信息", True)
            else:
                self.log_with_time("WARNING", "截图失败", True)
        except Exception as e:
            self.log_with_time("ERROR", f"记录画面失败: {str(e)}", True)