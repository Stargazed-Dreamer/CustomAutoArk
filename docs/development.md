# 开发指南

本文档面向二次开发者，介绍开发环境搭建、调试技巧、常见问题、干员数据更新方法以及如何扩展任务系统。阅读前建议先了解 [架构文档](architecture.md) 与 [配置说明](configuration.md)。

## 开发环境搭建

### 1. 创建虚拟环境并安装依赖

```bash
python -3.10 -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

依赖清单（`requirements.txt`）：

- `opencv-python`、`numpy`、`matplotlib`
- `pyside6`
- `paddlepaddle`、`paddleocr`
- `yaml`

### 2. GPU 加速（可选）

PaddleOCR 在 CPU 模式下可运行但较慢。如需 GPU 加速，安装 CUDA/cuDNN（支持 11.8 / 12.4 / 12.6）后覆盖安装 torch：

```bash
pip install --force-reinstall torch==2.6.0 torchvision==0.21.1 "numpy<2.0.0" --index-url https://download.pytorch.org/whl/cu124
```

如遇 OpenMP 冲突报错，尝试 `pip uninstall intel-openmp`，缺失时再重新安装。

### 3. 模拟器与 ADB

- 安装 MuMu 模拟器 12（默认端口 7555）。
- 在 `config.yaml` 中把 `simulator.adb_path`、`adb_path` 指向真实可用的 `adb.exe`。
- 确认 `simulator.port` 与模拟器一致。

### 4. 启动

```bash
python mainUI.py
```

无模拟器时 GUI 仍可启动，便于开发 UI、数据、绘图等不依赖设备的模块。

## 调试技巧

### 日志

- 日志系统在 `log.py`，由 `LogManager`（继承 `PySide6.QtCore.QObject`）统一管理，同时输出到控制台、文件、图片（按配置开关）。
- 默认控制台级别为 WARNING（`30`）。调试时可在 `config.yaml` 中把 `log.console_level` 改为 `20`（INFO）或 `10`（DEBUG），或通过设置面板实时调整。
- 日志格式：`[级别][时间][文件:行号]消息`。在代码中用 `from log import log_manager as log`，再调用 `log.info(...)` / `log.debug(...)` / `log.error(...)`。
- 记录异常请使用 `tool.error_record(e)`（注意需绑定异常变量 `except Exception as e:`，见 BF-12）。

### 断点与交互调试

- VS Code 打开 `combine.code-workspace` 即可获得推荐配置。
- 在 `mainUI.py` 的入口处下断点，或使用「Python: 当前文件」调试配置启动。
- 由于 `TaskManager` 在独立线程执行，调试任务流程时注意线程切换；可在 `TaskManager._task_loop` 与具体 `Task` 执行方法处下断点。

### 不依赖设备的调试

- 数据层（`data_manager.py`、`data.py`、`newData.py`）和工具层（`tool.py` 的纯函数、`tag统计工具.py`）可在无模拟器环境下单测。
- 利用 `图片样本/` 下的截图样本，可对 OCR/模板匹配逻辑做离线验证，无需真机。

### 测试

- 正式单元测试放 `tests/`，使用 `unittest` 或 `pytest`。
- `test/`（单数）目录下是临时试验脚本，不要作为正式测试目录。
- 建议优先为 `data_manager` 的波峰波谷、DTW 匹配，以及 `tool.py` 的模板匹配、文字相似度等纯函数补充测试。

## 常见问题

### 1. ADB 连接失败 / 找不到设备

- 确认 `adb_path` 指向真实存在的 `adb.exe`。
- 在命令行手动执行 `adb connect 127.0.0.1:7555`（端口换成你的模拟器）确认端口正确。
- 模拟器未运行或端口被占用时也会失败；多开模拟器时注意端口递增规则（见 [configuration.md](configuration.md#模拟器端口说明)）。

### 2. OCR 识别准确率低 / 识别失败抛 `OcrError`

- 检查 `tool.py` 顶部的 `region_tag` / `region_agent` / `region_history` 等裁剪区域是否匹配当前游戏界面分辨率。
- 公招界面布局变化时需更新 `img/` 下的模板图片与裁剪区域。
- 截图清晰度受模拟器分辨率与 DPI 影响，建议固定模拟器分辨率。
- GPU 未正确配置时 PaddleOCR 可能回退 CPU 模式或报错，检查 CUDA/cuDNN 与 torch 版本。

### 3. PaddleOCR / OpenMP 冲突

报错类似 `OMP Error` 时：

```bash
pip uninstall intel-openmp
# 缺失时再安装
pip install intel-openmp
```

### 4. Qt 跨线程操作 UI 报错

- 后台线程（`TaskManager`）中**不要**直接操作控件，必须通过 `Signal` 回主线程。
- 若新增的 Task 需要更新 UI，请通过 `TaskManager` 的信号或 `GameManager` 的信号转发，而非直接 `widget.setText(...)`。

### 5. 日志级别设置不生效 / 下拉框显示异常

- BF-16 修复了日志级别往返转换的问题。若仍异常，检查 `ui/settings.py` 的 `save_settings` 与 `loadSettings` 是否使用 `logging.getLevelName()` 做整数↔名称转换。

### 6. 循环依赖导入失败

- `task.py` 与 `tool.py` 曾互相引用导致循环依赖，已通过 `core/exceptions.py` 解决（BF-03）。新增公共异常/常量请放入独立模块，不要塞回循环路径上的文件。

## 如何更新干员数据

干员数据存在两套（`data.py` 与 `newData.py`），更新流程围绕从 PRTS Wiki 提取 HTML 并解析展开。

### 方式一：使用 `data_updater.py`

`data_updater.py` 内嵌了一份从 [PRTS Wiki](https://prts.wiki/) 「干员一览」页面抓取的 HTML（约 472KB），并定义了提取逻辑。

步骤：

1. （如需最新数据）从 PRTS Wiki 「干员一览」页面保存最新 HTML，替换 `data_updater.py` 中内嵌的 `html` 字符串，或改为读取外部 HTML 文件。
2. 运行 `data_updater.py`，按其内部规则解析 HTML 并生成干员数据。
3. 将结果同步到 `data.py` 或 `newData.py`（注意两套数据的字段差异）。

> 注意：内嵌大段 HTML 不易维护，建议将其外置为 `a.html` 之类的独立文件，由脚本读取。

### 方式二：使用 `html_parser.py`（通用 HTML 解析器）

`html_parser.py` 提供了通用的 HTML 提取能力，核心函数：

```python
def extract_agents(html_content, d_transfer, d_func):
    """
    从 HTML 内容中提取干员信息。

    参数:
        html_content (str): 包含干员信息的 HTML。
        d_transfer (dict): 转换规则字典，'__key__' 指定主键字段，
            其它键为「目标字段名 -> 属性名或函数调用规则」。
        d_func (dict): 可用函数字典，键为函数名，值为函数对象，
            供转换规则中以 '\\' 开头的字符串调用。

    返回:
        dict: 以干员中文名为键、数据字典为值的字典。
    """
```

它通过正则匹配带 `data-zh` 属性的 `<div>`，提取所有 `data-*` 属性，并按 `d_transfer` 规则映射为目标字段。流程：

1. 准备 HTML 内容（可来自 `a.html` 文件或 `data_updater.py` 内嵌的 `html`）。
2. 构造 `d_transfer` 转换规则与 `d_func` 处理函数。
3. 调用 `extract_agents(...)` 得到干员字典。
4. 把结果整理为 `data.py` / `newData.py` 所需结构并写入。

### 字段差异提醒

| 数据源 | 干员数 | 主要字段 | 被谁使用 |
|--------|--------|----------|----------|
| `data.py` | 366 | `en` / `star` / `tag` / `subprofession` | `tool.py`、`data_manager.py`、`core/game_manager.py` 等主流程 |
| `newData.py` | 376 | 含 `obtain_method` | `tag统计工具.py` |

更新时请明确目标数据源，并保持字段结构一致，避免破坏依赖该数据的模块。

## 如何添加新的 TaskType

新增一种任务类型需修改 `core/enums.py`、`core/task.py`，并在编排层（`core/game_manager.py`）按需使用。步骤如下：

### 1. 在 `core/enums.py` 中新增枚举值

在 `TaskType(Enum)` 中按分组添加，例如新增一种点击操作：

```python
class TaskType(Enum):
    # ... 已有枚举
    CLICK_NEW_THING = "点击新的东西"
```

### 2. 在 `core/task.py` 中实现执行逻辑

`Task` 的执行方法（如 `execute` / `find_imgOnScreen` 等）会根据 `self.taskType` 分发到不同分支。在对应的分发位置新增 `elif` 分支实现新逻辑：

```python
elif self.taskType == TaskType.CLICK_NEW_THING:
    # 实现你的逻辑，可调用 tool 与 self.simulator
    # 需要返回结果时通过约定返回，交由 TaskManager emit task_completed
    ...
```

实现时注意：

- 复用 `tool.py` 的 OCR、模板匹配、裁剪、文字相似度等能力，避免重复造轮子。
- 通过 `self.simulator` 下发点击/滑动/截图指令，不要在 `Task` 里直接构造 ADB 命令。
- 需要记录数据时，返回结果让 `GameManager` 通过 `record()` 写入，而非在 `Task` 内直接写文件。
- 异常按语义抛出 `CantFindNameError` / `OcrError`，不要静默吞掉。
- 如果新任务需要裁剪区域，遵循 `tool.py` 中 `region_*` 常量的百分比坐标约定。

### 3. 在 `core/task_manager.py` 中处理控制流（如需要）

- 普通的原子任务无需改 `TaskManager`，默认会取队列首部执行并 emit `task_completed`。
- 若新增的是控制流任务（类似 `IF`/`WHILE`/`END`），需在 `TaskManager._task_loop` 中添加对应分支，并注意与 `IF`/`WHILE` 的 `if`/`elif` 结构保持正确（参考 BF-08 的教训，不要把 `elif` 误写成 `if`）。

### 4. 在 `core/game_manager.py` 中编排使用

在业务方法（通常用 `@execute_tasks` 装饰）中构造新任务并加入返回列表：

```python
@execute_tasks
def my_flow(self):
    return [
        Task(taskType=TaskType.CLICK_NEW_THING, ...),
        # ...
    ]
```

如需在新任务完成后做特殊处理，可在 `_on_task_completed` 中针对新 `taskType` 增加分支（注意保持现有分支的 `if/elif` 结构完整）。

### 5. 测试与文档

- 为新任务类型补充单元测试或离线截图样本验证。
- 在本文件或架构文档的任务系统表格中补充新枚举的说明。
- 如行为影响用户可见流程，在 `CHANGELOG.md` 的 `[Unreleased]` 区块记录。
