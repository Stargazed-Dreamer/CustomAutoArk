"""pytest 全局配置与 mock 注入

在测试收集之前向 sys.modules 注入 mock 模块，避免导入被测模块时触发
PySide6 / paddleocr / cv2 等重依赖；同时将 log 模块整体 mock 掉，防止
LogManager 实例化产生副作用（创建日志目录、文件处理器等）。

保留真实导入的模块：
- numpy：纯数值库，已安装，被测算法直接依赖
- data / newData：纯 Python 数据定义
- core.exceptions：纯 Python 异常定义
"""
import os
import sys
from unittest.mock import MagicMock

# 将项目根目录加入 sys.path，保证被测模块可被正常导入
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# 1. mock PySide6 及其常用子模块（log.py 依赖，此处防御性 mock）
for _mod in ['PySide6', 'PySide6.QtCore', 'PySide6.QtWidgets', 'PySide6.QtGui']:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# 2. mock paddleocr（tool.py 顶部 from paddleocr import PaddleOCR）
sys.modules['paddleocr'] = MagicMock()

# 3. mock cv2（tool.py 顶部 import cv2；log.py 亦依赖）
sys.modules['cv2'] = MagicMock()

# 4. mock log 模块整体：log.py 依赖 PySide6/cv2/yaml，且实例化 LogManager
#    会创建日志目录与文件处理器，直接 mock 整个模块最干净。
#    data_manager.py 与 tool.py 均通过 `from log import log_manager` 引用。
sys.modules['log'] = MagicMock()

import pytest


@pytest.fixture
def dm():
    """返回一个干净的 DataManager 实例"""
    from data_manager import DataManager
    return DataManager()


@pytest.fixture
def tool_obj():
    """返回一个 Tool 实例（不调用 init_ocr，不触发 PaddleOCR）"""
    from tool import Tool
    return Tool()


@pytest.fixture(scope="session")
def tag_module():
    """加载文件名含中文的 tag统计工具.py 模块

    因文件名包含中文，无法用常规 import 语句导入，故使用 importlib 按文件路径加载。
    newData 为纯 Python 模块，项目根目录已在 sys.path 中，可被其内部 import 正常解析。
    """
    import importlib.util
    path = os.path.join(_PROJECT_ROOT, "tag统计工具.py")
    spec = importlib.util.spec_from_file_location("tag统计工具", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def finder(tag_module):
    """每个测试返回一个新的 TagFinder 实例，避免共享状态"""
    return tag_module.TagFinder()
