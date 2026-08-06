# 贡献指南（CONTRIBUTING）

感谢你愿意为本项目贡献代码！本文件说明了开发环境搭建、代码风格、提交规范、测试要求与 PR 流程。在开始之前，建议先阅读 [README.md](README.md)、[docs/architecture.md](docs/architecture.md) 与 [docs/development.md](docs/development.md) 以了解项目全貌。

## 开发环境设置

1. **Python 版本**：使用 Python 3.10（与 `requirements.txt` 一致），建议使用虚拟环境隔离依赖。
   ```bash
   python -3.10 -m venv .venv
   .venv\Scripts\activate          # Windows
   # source .venv/bin/activate     # macOS / Linux
   ```

2. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

3. **GPU 加速（可选）**：如需 GPU 加速 OCR，按 `requirements.txt` 中的说明安装 CUDA/cuDNN 并覆盖安装 torch。纯 CPU 环境也可运行，便于做 UI、数据逻辑相关的开发与调试。

4. **模拟器与 ADB**：安装 MuMu 模拟器 12（默认端口 7555）或其它安卓模拟器，并在 `config.yaml` 中配置正确的 `adb_path` 与 `simulator.port`。无模拟器时也可启动 GUI，但自动化相关功能无法运行。

5. **编辑器配置**：项目根目录提供了 `.vscode/settings.json` 与 `combine.code-workspace`，使用 VS Code 打开工作区即可获得推荐的配置。

## 代码风格约定

本项目代码中大量使用中文注释和中文变量/函数名，请在贡献时保持一致的风格。

### 通用规则

- **Python 版本**：3.10，可使用 3.10 引入的语法（如 `match/case`、新的类型标注等），但不要使用更高版本的独有特性。
- **缩进**：4 个空格，禁止 Tab。
- **编码**：所有源文件使用 UTF-8。
- **行宽**：建议不超过 120 字符，超长行在不影响可读性的前提下可换行。

### 命名与注释

- **变量与函数名**：本项目混用中文命名与英文命名。新增代码可沿用所在文件已有风格；与业务概念强相关的命名（如干员、tag、寻访）允许使用中文变量名以便与注释、游戏术语对应。
- **类名**：使用驼峰命名（`TaskManager`、`GameManager`、`Simulator`）。
- **常量**：全大写加下划线（`ADB_PATH`、`LOCK`、`region_tag`）。
- **注释**：鼓励为函数、复杂逻辑编写中文注释与文档字符串（docstring），说明参数、返回值与意图。注释应解释「为什么」，而非复述代码本身。

### 模块与依赖

- **避免循环依赖**：本项目曾因 `task.py` 与 `tool.py` 互相引用产生循环依赖，已通过新增 `core/exceptions.py` 解决（见 [docs/bugfix_log.md](docs/bugfix_log.md) BF-03）。新增公共异常、常量请放入 `core/exceptions.py` 或合适的独立模块，不要把定义塞进已有循环路径上的文件。
- **分层**：遵循 `ui/ → core/game_manager → core/task → core/simulator` + `tool.py` + 数据层的层次（详见架构文档）。UI 层不应直接调用 `Simulator`/`Task`，应通过 `GameManager` 暴露的接口与信号交互。

### 异常处理

- 不要静默吞掉异常（如 `except: pass`、抛出异常对象却不 `raise`）。
- 捕获异常时绑定异常变量（`except Exception as e:`）再记录，避免引用未定义的 `e`。
- 业务流程控制优先使用项目已有的异常类型（`StopError`、`UserSuspendOperationError`、`CantFindNameError`、`OcrError`）。

### Qt 信号槽

- `core` 与 `ui` 之间通过 Qt 信号解耦，新增跨层通信请优先使用信号而非直接调用。
- 在后台线程（`TaskManager` 的执行线程）中不要直接操作 UI 控件，必须通过信号回主线程。

## 提交规范

### Commit Message

使用中文或英文均可，建议格式：

```
<类型>: <简短描述>

<可选的详细说明>
```

常用类型：

- `feat`：新功能
- `fix`：Bug 修复
- `docs`：文档变更
- `refactor`：重构（不改变行为）
- `perf`：性能优化
- `test`：测试相关
- `chore`：构建、依赖、配置等杂项

示例：

```
fix: 修复 task_manager IF/WHILE 处理的 if/elif 逻辑错误 (BF-08)
docs: 新增架构与配置文档
feat: 公招标签识别增加容错
```

如修复有对应的 BF 编号（见 `docs/bugfix_log.md`），请在提交信息中标注。

### 提交粒度

- 一次提交只做一件事，避免把无关改动混在一起。
- 不要在提交中夹带调试用的 `print`、注释掉的代码块或临时文件。

## 测试要求

- **正式测试目录**：`tests/`。请在此目录下使用 `unittest` 或 `pytest` 编写单元测试。
- **临时脚本目录**：`test/`（注意是单数）目前存放的是临时试验脚本，**不要**把正式测试放在这里。
- 测试覆盖重点：
  - 数据层（`data.py` / `newData.py` / `data_manager.py`）的转换、波峰波谷、DTW 匹配逻辑。
  - `tool.py` 的图像处理、模板匹配、文字相似度等纯函数。
  - `tag统计工具.py` 的 tag 组合分析。
  - 涉及 ADB / OCR / 模拟器的部分难以单测，可通过构造截图样本（`图片样本/`）做集成验证。
- 提交前请确保：新增/修改的逻辑有对应测试，且全部通过。

## PR 流程

1. **Fork & 分支**：基于 `main` 创建特性分支，命名建议 `feat-xxx` / `fix-xxx` / `docs-xxx`。
2. **开发**：在分支上完成开发，保持提交历史清晰。如需合并多个零碎提交，可在 PR 前整理。
3. **自测**：
   - 确认 `python mainUI.py` 可正常启动。
   - 运行 `tests/` 下的测试。
   - 涉及 UI 改动时，手动验证相关交互。
4. **文档同步**：若改动涉及行为变化、配置项、新模块，请同步更新 `README.md`、`docs/` 下相关文档，并在 `CHANGELOG.md` 的 `[Unreleased]` 区块补充条目。Bug 修复请在 `docs/bugfix_log.md` 追加一条记录（含位置、问题、修复、原因、回滚方法）。
5. **提交 PR**：在 PR 描述中说明改动目的、影响范围、测试方式，并关联相关 issue。
6. **Review**：等待 review，根据反馈在原分支上迭代（不要新开 PR）。
7. **合并**：通过后合并到 `main`。

## 行为准则

- 保持友善、尊重的交流氛围。
- 以解决问题为导向，对事不对人。
- 欢迎报告问题：提交 issue 时请附上复现步骤、日志（如有）与运行环境信息。
