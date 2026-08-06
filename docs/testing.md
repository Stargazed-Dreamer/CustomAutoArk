# 测试指南

本文档说明「舟 / combine」项目的测试目录约定、pytest 配置、conftest.py 的 mock 策略、现有测试覆盖范围，以及如何运行与编写新测试。阅读前建议先了解 [开发指南](development.md) 与 [贡献指南](../CONTRIBUTING.md)。

## 测试目录约定

项目根目录下存在两个名字相近、用途不同的目录，请勿混淆：

| 目录 | 用途 | 说明 |
|------|------|------|
| `tests/` | 正式单元测试 | 提交前必须通过的测试均放在此处，被 `pytest.ini` 的 `testpaths` 收录 |
| `test/` | 临时试验脚本 | 单数命名，仅存放一次性调试脚本（如 `ocr.py`、`test.py`、`素材.png`），**不**作为正式测试目录，已被 `pyproject.toml` 的 lint/格式化/coverage 配置排除 |

> 新增测试一律放 `tests/`，不要往 `test/` 里写。详见 [README.md](../README.md)「已知问题」与 [CONTRIBUTING.md](../CONTRIBUTING.md)「测试要求」。

## 测试框架与配置

项目使用 **pytest**（>=7.0）作为测试框架，依赖声明在 `requirements-dev.txt` 与 `pyproject.toml` 的 `[project.optional-dependencies] dev` 中：

```bash
pip install -r requirements-dev.txt
# 或
pip install -e ".[dev]"
```

pytest 的配置同时存在于两处，二者互补：

- `pytest.ini`：核心收集规则。
  ```ini
  [pytest]
  testpaths = tests
  python_files = test_*.py
  python_classes = Test*
  python_functions = test_*
  ```
- `pyproject.toml` 的 `[tool.pytest.ini_options]`：补充 `addopts`（`-ra`、`--strict-markers`、`--strict-config`）与自定义 marker（`slow`、`integration`）。

## conftest.py 的 mock 策略

`tests/conftest.py` 在测试收集之前向 `sys.modules` 注入若干 mock 模块，使被测模块能脱离重依赖正常导入。被 mock 的模块及原因如下：

| 被 mock 的模块 | 引用方 | mock 原因 |
|----------------|--------|-----------|
| `PySide6` / `PySide6.QtCore` / `PySide6.QtWidgets` / `PySide6.QtGui` | `log.py`（防御性） | GUI 库安装重、实例化有副作用，单元测试无需真实 Qt 环境 |
| `paddleocr` | `tool.py`（`from paddleocr import PaddleOCR`） | PaddleOCR 体积大、初始化慢，且会触发 CUDA/cuDNN 加载 |
| `cv2` | `tool.py`、`log.py` | OpenCV 非纯 Python，避免二进制依赖影响纯算法测试 |
| `log` | `data_manager.py`、`tool.py`（`from log import log_manager`） | `LogManager` 实例化会创建日志目录与文件处理器，产生副作用 |

保留真实导入的模块：`numpy`（纯数值库，被测算法直接依赖）、`data` / `newData`（纯 Python 数据定义）、`core.exceptions`（纯 Python 异常定义）。

此外，`conftest.py` 还会把项目根目录加入 `sys.path`，保证 `from data_manager import DataManager` 这类顶层导入可用。

> 原则：单元测试只验证纯算法逻辑，凡涉及 ADB / OCR / Qt / 文件 IO 的部分要么 mock，要么改用 `图片样本/` 做离线集成验证。

## 现有测试覆盖范围

`tests/` 下现有三个测试文件，覆盖数据层与工具层的纯函数：

| 文件 | 被测对象 | 覆盖方法 |
|------|----------|----------|
| `test_data_manager.py` | `DataManager` | `data_convert`（tag 组合 / 干员名 / 前缀数字 / 空串 / 混合格式 / 非法抛 `ValueError`）、`find_peaks`（波峰波谷 / 短序列 / 单调 / 平台）、`dtw_distance`（相同序列 / 正距离 / 对称性 / 不等长）、`find_patterns`（短数据 / 重复模式 / 阈值 / 返回结构）、`get_statistics`（全量 / 切片 / 空数据 / 部分参数）、`normalize`（零标准差 / Z-score 性质 / 数值一致 / 长度不变） |
| `test_tool.py` | `Tool.cosine_similarity` | 相同字符串 / 空串 / 忽略大小写 / `new` 前缀剥离 / 高相似 / 无公共字符 / 区间 / 部分重叠 |
| `test_tag_finder.py` | `tag统计工具.TagFinder.find_agents_by_tags` | 空输入 / 单 tag / 组合键排序 / 排除 5 星 / 仅匹配被排除干员 / 子集不变量 / 非空子集 / 结果非空 / 仅返回 valid_agents |

## 如何运行测试

在项目根目录执行：

```bash
python -m pytest tests/ -v
```

常用变体：

```bash
# 只跑某个文件
python -m pytest tests/test_data_manager.py -v

# 跑指定类或方法
python -m pytest tests/test_data_manager.py::TestFindPeaks -v
python -m pytest tests/test_data_manager.py::TestFindPeaks::test_basic -v

# 生成覆盖率报告（需安装 pytest-cov）
python -m pytest tests/ --cov=core --cov=tool --cov=data_manager --cov-report=term-missing
```

`pyproject.toml` 注册了两个自定义 marker：`slow`（较慢的测试）与 `integration`（需要真实设备 / OCR 的集成测试）。默认集成测试不跑，可显式选择：

```bash
python -m pytest tests/ -m "not integration"
```

## 如何编写新测试

### 1. 命名约定

遵循 `pytest.ini` 的收集规则：

- 文件：`tests/test_<被测模块>.py`
- 类：`Test<被测对象>`，用类对相关用例分组
- 方法：`test_<行为>`，方法名见名知意

### 2. 风格约定

参考现有测试文件，保持一致：

- 模块顶部写中文 docstring，说明覆盖范围与注意事项。
- 用 `class` 按方法分组，每组前加 `# ======== 方法名 ========` 分隔注释。
- 每个测试方法配中文 docstring，一句话描述断言意图。
- 断言用裸 `assert`，浮点比较用 `pytest.approx`。

### 3. 复用 fixture

`conftest.py` 提供四个 fixture，直接在测试方法参数中声明即可注入：

| fixture | 作用域 | 说明 |
|---------|--------|------|
| `dm` | function | 返回干净的 `DataManager()` 实例，无共享状态 |
| `tool_obj` | function | 返回 `Tool()` 实例，**不**调用 `init_ocr`，不触发 PaddleOCR |
| `tag_module` | session | 用 `importlib` 按文件路径加载 `tag统计工具.py`（文件名含中文，无法常规 import） |
| `finder` | function | 基于 `tag_module` 每次返回新的 `TagFinder()`，避免共享状态 |

示例：

```python
class TestMyFeature:
    """my_feature 方法测试"""

    def test_basic(self, dm):
        """基本行为"""
        dm.data = [1, 2, 3]
        assert dm.find_peaks() == ([], [])
```

如需新增 fixture，统一放 `conftest.py`，便于全 `tests/` 复用。

## 不依赖设备的调试方法

涉及 ADB / OCR 的逻辑难以单测，可借助 `图片样本/` 目录下的真实截图做离线验证：

- `图片样本/公招界面.png`、`高资.png`、`向右箭头.png` 等可用于验证 `tool.py` 的裁剪区域（`region_tag` / `region_agent` / `region_history`）与模板匹配。
- `图片样本/MuMu12-*.png` 是 MuMu 12 模拟器实际截图序列，可用于复现 OCR 识别问题。

用法：在临时脚本中读取截图，直接调用 `tool.ocr(...)` / `tool.match_template(...)`，无需连接真机。临时脚本可放 `test/`，但不要纳入正式测试。详见 [开发指南 · 不依赖设备的调试](development.md#不依赖设备的调试)。

## 相关文档

- [开发指南](development.md)：调试技巧、不依赖设备的调试、扩展任务系统。
- [贡献指南](../CONTRIBUTING.md)：测试要求、提交规范、PR 流程。
- [架构文档](architecture.md)：模块层次与依赖关系，有助于判断被测对象的边界。
- [Bug 修复记录](bugfix_log.md)：BF-17 等修复附带测试用例，可作为编写范例。
