# 故障排查指南

本文档按问题域分类，汇总「舟 / combine」项目运行与开发中常见故障的现象、原因与解决方案，并标注对应的 Bug 修复编号（BF-xx，见 [bugfix_log.md](bugfix_log.md)）。如按本文档仍无法解决，请参阅文末「提交 issue」。

## ADB / 模拟器连接问题

### 现象：连接设备失败，提示「无法连接到设备」

`Simulator.__init__` 在 `ensure_connected()` 失败时会抛 `ConnectionError("无法连接到设备")`，导致 `GameManager` 无法启动。

**原因与排查步骤**：

1. **ADB 路径错误**：`config.yaml` 中存在两个 ADB 路径——顶层 `adb_path` 与 `simulator.adb_path`，两者需指向真实存在的 `adb.exe`。命令行验证：
   ```bash
   "<adb_path>" version
   ```
   注意 `simulator.py` 顶部还硬编码了 `ADB_PATH = "D:\\YXArkNights-12.0\\shell\\adb.exe"`，作为 `Simulator` 构造默认值，实际运行应通过参数传入配置中的路径。

2. **端口不对**：`simulator.port` 必须与模拟器设置一致。手动连接验证：
   ```bash
   adb connect 127.0.0.1:7555
   ```
   连接成功后 `adb devices` 应能看到设备。各模拟器默认端口见 [配置说明 · 模拟器端口说明](configuration.md#模拟器端口说明)。

3. **模拟器未启动 / 设备离线**：确认模拟器进程正在运行，多开模拟器时端口会递增（如雷电 5555/5557、夜神 62001/62025）。

4. **端口被占用**：更换模拟器实例端口或关闭占用进程。

> 相关：`core/simulator.py` 内部使用 `threading.Lock` 保护 ADB 调用，minitouch 二进制按设备 ABI 自动选择并推送。

## OCR / PaddleOCR 问题

### 现象一：识别准确率低或抛 `OcrError`

**原因与解决**：

- **裁剪区域不匹配**：`tool.py` 顶部定义了 `region_tag`、`region_agent`、`region_history` 等百分比坐标常量。公招界面布局变化或模拟器分辨率不同时，裁剪区域会偏移。可用 `图片样本/` 下的截图离线验证（见 [测试指南](testing.md#不依赖设备的调试方法)）。
- **模板图片过期**：`img/` 下的按钮模板（`RecruitConfirm.png` 等）需与当前游戏界面一致，游戏更新后可能要重新截取。
- **截图清晰度**：固定模拟器分辨率与 DPI，避免缩放导致识别失真。
- `tool.ocr()` 内部有 `retry = 3` 重试，仍失败时返回空列表（`OcrError` 抛出代码当前被注释，见 `tool.py` 第 139 行）。

### 现象二：CUDA / cuDNN 加载失败

`tool.init_ocr()` 中 GPU 回退逻辑目前被注释，`PaddleOCR()` 采用默认参数初始化。若环境报 `cudnn64_8.dll` 缺失等错误：

- **切换 CPU 模式**：不安装 CUDA/cuDNN 即默认 CPU 运行（较慢但可用）。
- **GPU 配置**：参考 [开发指南 · GPU 加速](development.md#2-gpu-加速可选)，按 CUDA 11.8 / 12.4 / 12.6 安装对应 torch。

### 现象三：OpenMP 冲突（`OMP Error`）

**解决**：

```bash
pip uninstall intel-openmp
# 缺失时再重新安装
pip install intel-openmp
```

详见 [开发指南](development.md#3-paddleocr--openmp-冲突)。

## Qt / UI 问题

### 现象一：跨线程操作 UI 报错

后台线程（`TaskManager._task_loop`）中**不得**直接调用控件方法（如 `widget.setText(...)`），否则触发 Qt 跨线程警告或崩溃。

**解决**：必须通过 `Signal` 回主线程。`TaskManager` 已暴露 `task_completed`、`task_failed`、`step_completed`、`task_terminated`、`device_disconnected` 等信号，由 `GameManager` 转发到 UI。新增 Task 需更新 UI 时，走信号链路而非直连控件。详见 [架构文档 · 信号槽通信](architecture.md#信号槽通信)。

### 现象二：调用某 UI 功能时抛 `NameError: name 'Qt' is not defined`

**原因**：`ui/plot.py` 曾仅导入 `Signal`，未导入 `Qt`，右键拖动平移时崩溃。**BF-14** 已修复，导入改为 `from PySide6.QtCore import Signal, Qt`。若自行改动导入列表导致类似报错，对照 [bugfix_log.md](bugfix_log.md) BF-14 补全。

### 现象三：`handle_missing_tag` / `handle_missing_agent` 抛 `NameError: name 'QDialog' is not defined`

**原因**：`ui/main_window.py` 未导入 `QDialog`。**BF-15** 已在 `from PySide6.QtWidgets import (...)` 中补入 `QDialog`。新增对话框调用时注意导入完整。

### 现象四：日志级别下拉框显示「20」而非「INFO」

**原因**：`ui/settings.py` 的 `loadSettings` 用 `str(20)` 设置下拉框，与选项 `["DEBUG","INFO",...]` 不匹配。**BF-16** 已改为用 `logging.getLevelName()` 把整数转回名称。详见 [配置说明 · 日志级别对照表](configuration.md#日志级别对照表)。

## 任务执行问题

### 现象一：IF / WHILE 条件任务行为异常

**原因**：`core/task_manager.py` 中 IF 处理后用 `if`（非 `elif`）检查 WHILE，导致 WHILE 任务不走 `elif result` 分支、IF 任务误走该分支。**BF-08** 已将 `if` 改为 `elif`。

**修改控制流时的注意**：保持 `_task_loop` 中 `IF`/`WHILE`/`elif result`/`elif error` 的 `if/elif` 链完整，不要把 `elif` 误写成 `if`。同步检查 `GameManager._on_task_completed` 的处理分支。详见 [架构文档 · IF / WHILE 条件编排](architecture.md#if--while-条件编排)。

### 现象二：OCR 失败后任务无响应 / 重试机制

`tool.ocr()` 内置 `retry = 3` 循环重试，全部失败返回空列表。若需在 Task 层做超时/重试，应在 Task 执行分支中自行实现，`TaskManager` 本身不提供任务级超时。

### 现象三：`RuntimeError: 线程未结束`

**原因**：`TaskManager.execute_tasks()` 开头检查 `b_needJoin`，若上一轮任务线程尚未结束会抛此错。`b_needJoin` 在 `_task_loop` 退出时置 `True`（`task_manager.py` 第 183 行），下次启动时若 `thread.is_alive()` 为真则 join。频繁启停任务时若遇到此报错，确认上一轮线程已退出再启动。

## 数据问题

### 现象一：数据加载失败

`DataManager.load_data()` 捕获异常后返回 `False` 并记录 `log_manager.error(f"加载数据失败: {e}")`。常见原因：文件不存在、编码非 UTF-8、内容无法被 `data_convert` 解析。

### 现象二：`data_convert` 抛 `ValueError("无效数据")`

**原因**：`data_convert` 按顺序匹配 tag 组合（`!` 分隔）、干员名、`#/?/？` 前缀数字、纯数字，均不匹配时抛 `ValueError`。出现此错说明 `#record.txt` 中存在无法识别的行。

**解决**：检查记录文件内容，确认每行是合法的干员名、tag 组合或前缀数字。空行会被自动跳过。

### 现象三：拖放导入失败

主窗口支持的拖放文件类型见 [配置说明 · 拖放导入支持的文件](configuration.md#拖放导入支持的文件)：`.json`、`.txt`、图片（`.jpg/.jpeg/.png/.bmp/.tiff/.webp`）、目录（递归查找）。不支持的扩展名会被忽略。

### 现象四：干员数据两套并存导致行为不一致

项目同时维护 `data.py`（366 个，字段 `en/star/tag/subprofession`，被 `tool.py`、`data_manager.py`、`core/game_manager.py` 主流程使用）与 `newData.py`（376 个，含 `obtain_method`，被 `tag统计工具.py` 使用）。两套字段不兼容，更新时需明确目标数据源。详见 [开发指南 · 字段差异提醒](development.md#字段差异提醒)。

## 导入 / 循环依赖问题

### 现象一：`ImportError` / 循环导入

**原因**：`task.py` 与 `tool.py` 曾互相引用产生循环依赖。**BF-03** 通过新增 `core/exceptions.py` 集中定义 `CantFindNameError`、`OcrError`、`StopError`、`UserSuspendOperationError` 等异常类解决，两者都从该模块独立导入。

**原则**：新增公共异常 / 常量请放入 `core/exceptions.py` 或合适的独立模块，**不要**塞回循环路径上的文件。`task.py` 仍重新导出这些异常以保持向后兼容（`from core.task import StopError` 仍可用）。

### 现象二：`core` 包导入重库开销大 / 意外触发依赖

**原因**：`core/__init__.py` 对 `Simulator` / `Task` / `TaskManager` / `GameManager` 使用懒加载（`__getattr__` + `importlib`），只有真正访问时才导入，避免 `import core` 即加载 cv2/paddleocr/PySide6。`enums` / `exceptions` 是轻量模块，在包初始化时立即导入。

**注意**：若只需枚举或异常，用 `from core import TaskType` 不会触发重库导入；若访问 `core.GameManager` 则会触发。

## 日志问题

### 现象一：控制台出现重复日志输出

**原因**：`log.py` 第 137 行曾有调试残留 `print(formatted_msg)`，每次记录日志都打印到 stdout。**BF-13** 已删除该行。若再次出现重复输出，检查是否重新引入了 `print` 调试语句。

### 现象二：日志文件不生成

**原因**：`config.yaml` 默认 `log.file_enabled: false`，文件日志默认关闭。需开启时改为 `true`，并确认 `log.log_dir`（默认 `log`）目录可写。日志级别数值含义见 [配置说明 · 日志级别对照表](configuration.md#日志级别对照表)。

> 提示：`log.py` 依赖 PySide6（`LogManager` 继承 `QObject`）与 `cv2`、`yaml`，若这些依赖缺失会初始化失败。开发无 GUI 环境下的纯算法调试，测试中已整体 mock `log` 模块（见 [测试指南](testing.md#conftestpy-的-mock-策略)）。

## 提交 issue

若按上述步骤仍无法解决，请提交 issue 并附以下信息：

1. **复现步骤**：从启动程序到出现问题的完整操作序列。
2. **预期与实际行为**：分别说明期望发生什么、实际发生什么。
3. **日志**：开启 `log.file_enabled` 后捕获的日志文件，或控制台报错完整堆栈。
4. **环境信息**：
   - 操作系统（如 Windows 11）
   - Python 版本（项目要求 3.10）
   - 依赖版本（`pip freeze` 输出，尤其 `paddlepaddle` / `paddleocr` / `PySide6` / `torch`）
   - 模拟器类型与端口（如 MuMu 12 / 7555）
   - 是否使用 GPU
5. **相关截图**：若是 OCR / 识别问题，附 `图片样本/` 中能复现问题的截图。

提交 issue 前请先搜索是否已有相同问题，避免重复。贡献代码修复请遵循 [CONTRIBUTING.md](../CONTRIBUTING.md) 的分支与 PR 流程，Bug 修复请在 [bugfix_log.md](bugfix_log.md) 追加一条记录。
