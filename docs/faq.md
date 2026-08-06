# 常见问题（FAQ）

本文件以 Q&A 形式回答「舟 / combine」项目使用与开发中的高频问题。更详细的故障排查见 [故障排查指南](troubleshooting.md)，开发流程见 [开发指南](development.md)。

## Q: 项目支持哪些模拟器？默认端口是多少？

默认适配 **MuMu 模拟器 12**（默认 ADB 端口 `7555`）。其它模拟器需在 `config.yaml` 中修改 `simulator.port`：雷电（`5555` 起，每实例 +2）、BlueStacks（`5555` / `5565`）、夜神（`62001` 起，每实例 +2）、逍遥（`21503`）等。完整端口表见 [配置说明 · 模拟器端口说明](configuration.md#模拟器端口说明)。

## Q: 必须用 GPU 吗？CPU 能跑吗？

不是必须。CPU 模式可正常运行，仅 OCR 速度较慢。GPU 加速需安装 CUDA / cuDNN（支持 11.8 / 12.4 / 12.6）并覆盖安装对应版本 torch，配置方法见 [开发指南 · GPU 加速](development.md#2-gpu-加速可选)。

## Q: 为什么有两套干员数据（`data.py` 和 `newData.py`）？

历史遗留。`data.py` 含 366 个干员，字段为 `en` / `star` / `tag` / `subprofession`，被 `tool.py`、`data_manager.py`、`core/game_manager.py` 主流程使用；`newData.py` 含 376 个干员，多了 `obtain_method` 字段，仅被 `tag统计工具.py` 使用。两套字段不兼容，更新时需明确目标数据源，详见 [开发指南 · 字段差异提醒](development.md#字段差异提醒)。

## Q: PLAN 模式（自动规划）能用吗？

不能。`OperationMode.PLAN` 目前仅为占位。`core/game_manager.py` 的 `start_operation` 在收到 `OperationMode.PLAN` 时输出「自动规划未实现」并 `return`，`_arrange_next_task` 中对应分支是 `pass`（标注 `# TODO: 实现自动规划功能`）。详见 [README.md](../README.md)「已知问题」。

## Q: `statistics.py` 是干什么的？为什么 `main_window` 导入但没实例化？

`ui/statistics.py` 定义了 `StatisticsWidget`，一个用于显示「全局统计」与「选中区域统计」的 QWidget。`ui/main_window.py` 第 27 行 `from .statistics import StatisticsWidget` 导入了它，但全文未出现 `StatisticsWidget(` 实例化调用，属于死代码。统计功能实际由 `PlotWidget` 内部调用 `data_manager.get_statistics()` 完成。详见 [README.md](../README.md)「已知问题」。

## Q: 如何更新干员数据到最新版本？

围绕从 [PRTS Wiki](https://prts.wiki/) 「干员一览」页面提取 HTML 并解析，有两种方式：

1. **`data_updater.py`**：内嵌约 472KB HTML，运行后按内部规则解析。如需最新数据，需替换内嵌 HTML 或改为读取外部 `a.html`。
2. **`html_parser.py`**：通用解析器，核心函数 `extract_agents(html_content, d_transfer, d_func)`，通过正则匹配 `data-zh` 属性的 `<div>` 提取干员信息。

完整流程与字段差异见 [开发指南 · 如何更新干员数据](development.md#如何更新干员数据)。

## Q: `#record.txt` 是什么？可以删吗？

`#record.txt` 是招募 / 抽卡记录文件，UTF-8 纯文本，每行一条记录（干员名、tag 组合用 `!` 分隔、或 `#/?/？` 前缀数字）。由 `data_manager` 写入与加载。**可以删**，删除后历史记录清空，不影响程序运行；程序会在后续操作中重新生成。文件格式详见 [配置说明 · 数据文件格式](configuration.md#recordtxt招募抽卡记录)。该文件已被 `.gitignore` 忽略，不会入库。

## Q: 拖放导入支持哪些文件？

主窗口支持拖放 `.json`、`.txt`、图片（`.jpg` / `.jpeg` / `.png` / `.bmp` / `.tiff` / `.webp`）以及包含上述文件的目录（递归查找）。完整说明见 [配置说明 · 拖放导入支持的文件](configuration.md#拖放导入支持的文件)。

## Q: 如何添加新的任务类型？

需修改 `core/enums.py`（新增 `TaskType` 枚举）、`core/task.py`（实现执行分支）、按需修改 `core/task_manager.py`（控制流）与 `core/game_manager.py`（编排）。完整步骤见 [开发指南 · 如何添加新的 TaskType](development.md#如何添加新的-tasktype)。新增后建议补充测试，见 [测试指南](testing.md)。

## Q: 为什么日志级别保存后再打开下拉框显示不对？

这是 BF-16 修复的问题。`ui/settings.py` 的 `loadSettings` 原先用 `str(20)` 设置下拉框，与选项 `["DEBUG","INFO","WARNING","ERROR","CRITICAL"]` 不匹配，显示为「20」。修复后改用 `logging.getLevelName()` 把整数转回名称。若仍异常，检查 `save_settings` 与 `loadSettings` 是否一致使用整数↔名称转换。详见 [故障排查指南](troubleshooting.md#现象四日志级别下拉框显示20而非info) 与 [bugfix_log.md](bugfix_log.md) BF-16。

## Q: `test/` 和 `tests/` 有什么区别？

- `tests/`（复数）：**正式单元测试**目录，被 `pytest.ini` 的 `testpaths` 收录，运行 `python -m pytest tests/ -v` 执行。
- `test/`（单数）：**临时试验脚本**目录，存放一次性调试脚本，不作正式测试，已被 lint / 格式化 / coverage 配置排除。

新增测试一律放 `tests/`。详见 [测试指南 · 测试目录约定](testing.md#测试目录约定)。

## Q: 项目用 Git 管理吗？`.gitignore` 忽略了哪些？

是。`.gitignore` 忽略的内容包括：Python 编译产物（`__pycache__/`、`*.pyc`）、虚拟环境（`.venv/`）、测试 / 覆盖率缓存（`.pytest_cache/`、`.coverage`）、IDE 配置（`.idea/`、`.vscode/*`，但保留 `settings.json`）、日志（`log/`、`*.log`）、运行时数据（`#record.txt`）、临时 / 备份文件（`*.bak`、`*.tmp`）、大文件（`a.html`）、历史归档（`old/`）。`图片样本/` 默认未忽略（可按需取消注释）。

## Q: 如何贡献代码？

请遵循 [CONTRIBUTING.md](../CONTRIBUTING.md)：基于 `main` 创建特性分支（`feat-xxx` / `fix-xxx` / `docs-xxx`），保持提交粒度，提交前运行 `tests/` 测试并自测 `python mainUI.py`，同步更新文档与 `CHANGELOG.md`，Bug 修复在 [bugfix_log.md](bugfix_log.md) 追加记录。提交 PR 时说明改动目的、影响范围与测试方式。
