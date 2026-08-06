# 更新日志（CHANGELOG）

本项目所有重要变更均会记录在此文件中。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，并遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

> 详细的 Bug 修复记录（含原代码 / 新代码 / 回滚方法）请见 [docs/bugfix_log.md](docs/bugfix_log.md)。

## [Unreleased]

### 新增 — 工程基础设施

- **`pyproject.toml`**：项目级工具配置汇总，集中配置构建系统、运行时/开发依赖、`black` / `isort` / `ruff` / `mypy` / `pytest` / `coverage` 等工具。支持 `pip install -e ".[dev]"` 一键安装开发依赖。
- **`.editorconfig`**：统一缩进（4 空格）、编码（UTF-8）、换行（LF）风格，覆盖 Python / YAML / Markdown / JSON / TOML。
- **`.github/workflows/ci.yml`**：GitHub Actions 持续集成配置，在 push / PR 时自动运行 `pytest`（Python 3.10 / 3.11 × ubuntu / windows 矩阵）与 `ruff` lint。CI 仅安装轻量依赖（pytest / numpy / PyYAML），依赖 `conftest.py` 的 mock 机制避免重库。
- **完善 `.gitignore`**：从仅 `__pycache__/` 扩充为覆盖虚拟环境、测试缓存、IDE 临时文件、日志目录、运行时数据（`#record.txt` 等）、`a.html` 大文件、`old/` 归档、`test/` 临时脚本（保留 `test/README.md`）。
- **完善 `requirements.txt`**：添加版本约束（如 `numpy>=1.24,<2.0`），修正 `yaml` → `PyYAML`（PyPI 包名错误），保留 GPU 加速与 OpenMP 冲突的说明。
- **完善 `requirements-dev.txt`**：补充 `pytest-cov`、`black`、`isort`、`ruff`、`mypy` 等开发工具。
- **完善 `mainUI.py`**：从 5 行扩展为带高 DPI 适配、日志引导、启动期异常兜底（写日志 + 弹窗）、退出清理的完整入口。

### 新增 — 测试

- **测试覆盖从 43 个扩展到 106 个用例**（+63），新增四个测试文件：
  - `tests/test_config.py`（19 个）：`ConfigManager` 的加载、默认合并、保存/加载一致性、便捷访问方法（`get_simulator` / `get_log` / `get_adb_path` 优先级等）。
  - `tests/test_html_parser.py`（13 个）：`extract_agents` 的基本提取、空 HTML、缺主键跳过、函数调用规则、直接属性映射、非法函数格式、缺失属性/函数抛错。
  - `tests/test_data.py`（19 个）：`Data` 类的 `is_special`、`getTagPriority`、`l_agent` / `l_tag` / `d_agent` 结构与已知干员验证。
  - `tests/test_tool_functions.py`（12 个）：`_get_filename`（Windows/Unix/混合路径）、`error_record`（有/无 traceback）。

### 新增 — 文档

- **`docs/testing.md`**：测试指南，介绍目录约定、conftest.py 的 mock 策略、fixture 用法、运行命令、命名约定、离线调试方法。
- **`docs/troubleshooting.md`**：故障排查指南，按问题域分类（ADB / OCR / Qt / 任务执行 / 数据 / 导入 / 日志），每条含现象、原因、解决方案、相关 BF 编号。
- **`docs/faq.md`**：13 个常见问题 Q&A，覆盖模拟器、GPU、两套数据、PLAN 模式、statistics.py、数据更新、拖放导入等。
- **`old/README.md`**：历史归档目录说明，含迁移对照表与清理建议。
- **`test/README.md`**：临时脚本目录说明，明确与 `tests/` 的区别。

### 新增 — 异常模块（前期）

- **新增异常模块** `core/exceptions.py`：集中定义 `CantFindNameError`、`OcrError`、`UserSuspendOperationError`、`StopError`、`MouseMoveError`，解除 `task.py` 与 `tool.py` 之间的循环依赖（配合 BF-03）。
- **新增常量模块** `core/constants.py`：集中定义路径、屏幕区域、设备端口、星级、OCR 等常量。
- **新增配置管理器** `config.py`：`ConfigManager` 继承 dict，提供 `get_simulator()` / `get_log()` 等类型化访问方法，向后兼容现有 `g.config['log']` 用法。
- **完善 `core/__init__.py`**：使用懒加载（`__getattr__`）延迟导入 `Simulator` / `Task` / `TaskManager` / `GameManager`，避免循环导入。
- **完善 `ui/__init__.py`**：规范 UI 模块导出，集中管理组件。

### 新增 — 文档体系（前期）

- `README.md` 扩充为完整项目说明（功能特性、环境要求、快速开始、项目结构、配置、开发指南、测试、代码风格、已知问题、许可证）。
- `CHANGELOG.md`（本文件）。
- `CONTRIBUTING.md` 贡献指南。
- `LICENSE`（MIT 协议）。
- `docs/architecture.md` 架构文档。
- `docs/configuration.md` 配置说明。
- `docs/development.md` 开发指南。
- `docs/bugfix_log.md` Bug 修复记录（含每条修复的位置、问题、修复、原因、回滚方法）。
- **测试目录约定**：明确 `test/` 为临时脚本目录，正式单元测试应放在 `tests/`。

### 修复

本次共修复 17 项 Bug（编号 BF-01 ~ BF-17），策略为「保守修复」——只改明确的缺陷，不动业务逻辑、不重构。摘要如下：

- **BF-01** `tool.py`：`cropping()` 中两处 `ValueError(...)` 缺少 `raise` 关键字，异常被静默吞掉，改为 `raise ValueError(...)`。
- **BF-02** `tool.py`：`group = group.sort(...)` 误用原地排序的返回值（`None`），改为 `group.sort(...)`。
- **BF-03** `tool.py`：引用未定义的 `CantFindNameError` / `OcrError` 会抛 `NameError`；通过新增 `core/exceptions.py` 并在 `tool.py`、`core/task.py` 中导入修复（`task.py` 保留重新导出以向后兼容）。
- **BF-04** `newData.py`：`self.l_tag = [...],` 尾随逗号使 `l_tag` 变成元组，导致所有 `'XXX' in self.l_tag` 判断失效，删除尾随逗号。
- **BF-05** `core/task.py`：`find_imgOnScreen` 在设置 `region` 时引用了不存在的 `img` 变量（应为 `screenshot`），导致 `CLICK_IMG` + `region` 组合崩溃，修正变量名。
- **BF-06** `core/task.py`：`SAVE_FROM_MEM` 的 txt 模式在 `pop` 后又访问已弹出的索引，改为统一使用 `item` 变量。
- **BF-07** `core/task_manager.py`：`hasattr(self.tasks, "description")` 检查的是列表对象（永远 False），改为 `hasattr(self.tasks[0], "description")`。
- **BF-08** `core/task_manager.py`：IF/WHILE 处理使用 `if`/`if` 而非 `if`/`elif`，导致 WHILE 任务不 emit `task_completed`、IF 任务误入 `elif result` 分支；将第二个 `if` 改为 `elif`。
- **BF-09** `core/game_manager.py`：十连转单抽递归调用 `_arrange_next_task()` 后未 `return`，会继续执行十连逻辑，补充 `return`。
- **BF-10** `core/game_manager.py`：`_log()` 引用未定义的 `e` 且忽略 `message` 参数，改为 `self.log_with_time(level, message)`。
- **BF-11** `core/game_manager.py`：`record()` 中两个独立 `if` 导致 `s_record` 可能未定义，改为 `if/elif/else` 并用 `str(item)` 兜底。
- **BF-12** `core/simulator.py`：`click`/`swipe` 的 `except` 未绑定异常变量却引用 `e`，且 `swipe` 使用裸 `except:`，统一改为 `except Exception as e:`。
- **BF-13** `log.py`：残留的调试 `print(formatted_msg)` 污染控制台输出，删除该行。
- **BF-14** `ui/plot.py`：右键拖动平移时引用未导入的 `Qt`，在 `PySide6.QtCore` 导入中补充 `Qt`。
- **BF-15** `ui/main_window.py`：`handle_missing_tag`/`handle_missing_agent` 引用未导入的 `QDialog`，在 `PySide6.QtWidgets` 导入中补充 `QDialog`。
- **BF-16** `ui/settings.py`：日志级别在保存（整数）与加载（字符串）之间往返转换坏掉，加载时改用 `logging.getLevelName()` 转回名称。
- **BF-17** `data_manager.py`：`find_similar_patterns` 在 `for` 循环中修改循环变量无效（无法跳过相邻模式），改为 `while` 循环按需自增。

### 变更

- 无业务逻辑层面的破坏性变更；所有修复均保持对外导入路径兼容（如 `from core.task import StopError` 仍可用）。
- `requirements.txt` 中 `yaml` 修正为 `PyYAML`（PyPI 包名）。如已误装 `yaml` 包，请 `pip uninstall yaml` 后重装 `PyYAML`。

## 历史版本

本项目此前未维护正式版本号，本次为首次建立变更日志。更早的演进历史请参考 Git 提交记录。
