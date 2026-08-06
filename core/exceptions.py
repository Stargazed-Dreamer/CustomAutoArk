"""核心异常定义模块

将原先散落在 task.py 中的异常类集中到此模块，解除 task.py 与 tool.py 之间的循环依赖：
- tool.py 需要引用 CantFindNameError / OcrError，但 task.py 又依赖 tool.py
- 集中到本模块后，两者都可独立导入

task.py 仍会重新导出这些异常（from .exceptions import ...），
因此现有的 `from core.task import StopError` 等导入无需修改，保持向后兼容。
"""


class CantFindNameError(Exception):
    """无法在屏幕/OCR结果中找到目标名称时抛出"""
    pass


class MouseMoveError(Exception):
    """鼠标移动相关错误（当前未使用，保留以备扩展）"""
    pass


class OcrError(Exception):
    """OCR 识别失败时抛出"""
    pass


class UserSuspendOperationError(InterruptedError):
    """用户主动中止操作时抛出，继承 InterruptedError 以区分于普通异常"""
    pass


class StopError(Exception):
    """任务循环停止信号，用于中断 TaskManager 的执行循环"""
    pass
