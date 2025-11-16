import time
import threading
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from log import log_manager
from tool import error_record

from .enums import TaskType
from .task import Task, StopError

log = log_manager

class TaskManager(QObject):
    """任务管理器，负责任务队列的管理和执行"""
    task_started = Signal(str)          # 任务开始信号
    task_completed = Signal(object)     # 任务完成信号，传递任务结果
    task_failed = Signal(str)           # 任务失败信号
    step_completed = Signal()           # 步骤完成信号，用于请求下一组任务
    task_terminated = Signal()          # 任务终止信号，遇见END任务时触发
    device_disconnected = Signal()      # 设备离线信号
    
    def __init__(self):
        super().__init__()
        self.tasks = []
        self.current_task = None
        self.is_running = False
        self.is_paused = False
        self.thread = None
        self.b_needJoin = False
    
    def add_task(self, task: Task):
        """添加任务到队列"""
        self.tasks.append(task)
    
    def clear_tasks(self):
        """清空任务队列"""
        self.tasks.clear()
    
    def get_next_task_description(self) -> Optional[str]:
        """获取下一个任务的描述"""
        if not self.tasks:
            return None
        return self.tasks[0].description if hasattr(self.tasks, "description") else None
    
    def execute_tasks(self):
        """开始执行任务队列"""
        log.debug(f"线程执行标志：{self.is_running}")
        if self.is_running:
            return
        if self.b_needJoin:
            if self.thread.is_alive():
                raise RuntimeError("线程未结束")
            if self.thread != threading.current_thread():
                self.thread.join()
        self.is_running = True
        self.is_paused = False
        self.thread = threading.Thread(target=self._task_loop)
        self.thread.start()
    
    def stop_tasks(self):
        """停止任务执行"""
        self.clear_tasks()
        self.is_running = False
        self.is_paused = True
    
    @Slot()
    def pause_tasks(self):
        self.is_paused = True

    @Slot()
    def resume_tasks(self):
        self.is_paused = False

    def _task_loop(self):
        """任务执行循环"""
        while self.is_running:
            if self.tasks == [] or self.is_paused:
                time.sleep(0.1)
                continue
            try:
                self.current_task = self.tasks.pop(0)
                
                # 前置等待
                if self.current_task.pre_wait > 0:
                    time.sleep(self.current_task.pre_wait)

                while self.is_paused:
                    if not self.is_running:
                        raise StopError
                    time.sleep(0.1)

                # 发送任务开始信号
                self.task_started.emit(self.current_task.description)
                
                # 执行任务
                result = None
                error = None

                if self.current_task.taskType == TaskType.STEP_COMPLETED:
                    self.step_completed.emit()
                    continue
                elif self.current_task.taskType == TaskType.END:
                    self.task_terminated.emit()
                    break

                start_time = time.time()
                for _ in range(self.current_task.retry_count):
                    if not Task.simulator.ensure_connected():
                        self.device_disconnected.emit()
                        raise RuntimeError("模拟器离线")
                    try:
                        result = self.current_task.execute()
                        if result is True or (isinstance(result, tuple)):
                            break
                            
                    except Exception as e:
                        error = str(e)
                        error_record(e)
                        time.sleep(0.1)  # 重试前短暂等待

                
                    while self.is_paused:
                        if not self.is_running:
                            raise StopError
                        time.sleep(0.1)
                        start_time += 0.1


                    if time.time() - start_time > self.current_task.timeout:
                        error = "任务超时"
                        break

                while self.is_paused:
                    if not self.is_running:
                        raise StopError
                    time.sleep(0.1)

                # 后置等待
                if self.current_task.post_wait > 0:
                    time.sleep(self.current_task.post_wait)

                while self.is_paused:
                    if not self.is_running:
                        raise StopError
                    time.sleep(0.1)

                # 发送任务结果
                if self.current_task.taskType == TaskType.IF:
                    if not isinstance(self.tasks[0], list):
                        raise TypeError("IF 类型的任务后必须接一个任务列表")
                    if result[2] is True:
                        l = self.tasks.pop(0)
                        self.tasks = l + self.tasks
                    else:
                        self.tasks.pop(0)
                if self.current_task.taskType == TaskType.WHILE:
                    if not isinstance(self.tasks[0], list):
                        raise TypeError("WHILE 类型的任务后必须接一个任务列表")
                    if result[2] is True:
                        l = self.tasks.pop(0)
                        selfTaskGroup = [self.current_task, l]
                        self.tasks = l + selfTaskGroup + self.tasks
                    else:
                        self.tasks.pop(0)
                elif result:
                    self.task_completed.emit(result)
                    if isinstance(result, tuple) and result[0] is False:
                        self.is_paused = True
                elif error:
                    self.task_failed.emit(error)
                    break
                else:
                    raise RuntimeError("不可能运行到此处")
            except StopError:
                break
            except Exception as e:
                self.task_failed.emit(str(e))
                error_record(e)
                break
        self.is_running = False
        self.b_needJoin = True