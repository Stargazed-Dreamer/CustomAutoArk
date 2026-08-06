"""ui 包 — PySide6 用户界面模块

集中管理应用程序的所有 UI 组件：主窗口、控制面板、数据视图、绘图、设置等。

## 公共 API

```python
from ui import MainWindow, ControlWidget, PlotWidget
from ui import DataViewWidget, SettingsWidget, ConsoleWidget
from ui import g  # 全局状态单例
```

## 注意
导入此包会触发 PySide6、matplotlib、cv2 等重依赖的加载。
仅在需要 UI 功能时导入。
"""

from .global_state import g
from .console import ConsoleWidget
from .control import ControlWidget
from .data_view import DataViewWidget
from .dialogs import InputWithImageDialog
from .main_window import MainWindow
from .plot import PlotWidget
from .settings import SettingsWidget

__all__ = [
    'g',
    'ConsoleWidget',
    'ControlWidget',
    'DataViewWidget',
    'InputWithImageDialog',
    'MainWindow',
    'PlotWidget',
    'SettingsWidget',
]
