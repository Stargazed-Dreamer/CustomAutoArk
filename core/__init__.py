"""core 包 — 核心自动化模块

集中管理游戏自动化所需的核心组件：设备控制、任务执行、任务编排、业务流程。

## 公共 API

```python
from core import GameManager, TaskManager, Task, Simulator
from core import OperationMode, GachaMode, RecruitMode, TaskType
from core import StopError, UserSuspendOperationError, CantFindNameError
```

## 导入策略
- enums / exceptions 是轻量模块，在包初始化时立即导入
- simulator / task / task_manager / game_manager 依赖 cv2 / paddleocr / PySide6 等重库，
  使用懒加载（__getattr__）避免循环导入和不必要的导入开销
"""

from .enums import OperationMode, GachaMode, RecruitMode, TaskType
from .exceptions import (
    CantFindNameError,
    MouseMoveError,
    OcrError,
    UserSuspendOperationError,
    StopError,
)

__all__ = [
    # 枚举
    'OperationMode',
    'GachaMode',
    'RecruitMode',
    'TaskType',
    # 异常
    'CantFindNameError',
    'MouseMoveError',
    'OcrError',
    'UserSuspendOperationError',
    'StopError',
    # 核心类（懒加载）
    'Simulator',
    'Task',
    'TaskManager',
    'GameManager',
]

# 核心类的懒加载映射
_LAZY_MAP = {
    'Simulator': '.simulator',
    'Task': '.task',
    'TaskManager': '.task_manager',
    'GameManager': '.game_manager',
}


def __getattr__(name):
    """懒加载核心类，避免循环导入"""
    if name in _LAZY_MAP:
        import importlib
        module = importlib.import_module(_LAZY_MAP[name], __package__)
        cls = getattr(module, name)
        globals()[name] = cls  # 缓存，后续直接访问
        return cls
    raise AttributeError(f"module 'core' has no attribute {name}")
