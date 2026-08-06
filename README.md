# 舟 / combine —— 明日方舟公招自动化与数据分析工具

本项目是一个面向《明日方舟》（Arknights）的桌面自动化与数据分析工具，基于 Python + PySide6 构建 GUI，使用 ADB 控制安卓模拟器，通过 PaddleOCR 识别游戏画面，实现公开招募、干员寻访等流程的自动化，并对招募/抽卡数据进行记录、分析与可视化。

工具的核心思路是「任务列表（tasklist）驱动」：把游戏中的每一步操作（点击文字、点击图片、记录屏幕、滑动、条件判断等）抽象为 `Task` 对象，由 `TaskManager` 在后台线程顺序执行，再由 `GameManager` 编排出寻访、公招等完整业务流程。配合内置的数据管理与 matplotlib 可视化模块，可对历史记录做波峰波谷检测、DTW 相似模式匹配和交互式绘图。

> 本项目完全自用，如果你很想试试，可以按照以下方法使用
>
> 1. 完整获取项目
> 2. 按照requirements安装环境
> 3. 检查core/game_manager.py中的任务，以此了解功能的实现方式。
> 4. 依据你的需要自己编写tasklist
>
> 注：此项目默认支持抽卡数据导入，相关文件拖进来可以自动解析
>
> 项目较为庞杂，初次上手建议让AI工具审阅并给出摘要

---

## 功能特性

- **公招自动化**：自动识别公招标签、选择最优 tag 组合、招募、加速 / 中止。
- **寻访自动化**：支持单抽 / 十连，自动记录结果，可控制源石消耗与执行次数上限；剩余次数不足十连时自动切换为单抽。
- **任务系统**：内置 22 种 `TaskType`，支持点击、滑动、截图、记录、坐标点击、页面切换等原子任务，以及 `IF` / `WHILE` 条件编排与 `END` 终止、`STEP_COMPLETED` 步骤推进等流程控制。
- **数据记录**：招募历史写入 `#record.txt`，支持干员、tag、历史记录页等多种记录方式。
- **数据分析**：波峰波谷检测、基于 DTW（动态时间规整）的相似模式匹配、统计信息计算。
- **数据可视化**：基于 matplotlib 的交互式折线图，支持选择、平移、缩放，鼠标悬停与数据点同步高亮，可标记波峰波谷与匹配模式。
- **数据导入**：向主窗口拖放 JSON / TXT / 图片 / 目录即可自动解析并载入。
- **数据更新**：`data_updater.py` / `html_parser.py` 可从 PRTS Wiki 的 HTML 中提取干员信息并更新本地数据。
- **模拟器适配**：默认适配 MuMu 模拟器 12（端口 7555），支持 minitouch 多架构二进制，可配置 ADB 路径与端口。

## 环境要求

- **Python**：3.10
- **核心依赖**（见 `requirements.txt`）：
  - `opencv-python`、`numpy`、`matplotlib`
  - `pyside6`（GUI）
  - `paddlepaddle`、`paddleocr`（OCR 识别）
  - `yaml`（配置文件）
- **GPU 加速（可选但推荐）**：需安装 CUDA 与 cuDNN（支持 11.8 / 12.4 / 12.6），并覆盖安装对应版本的 `torch` / `torchvision`。CPU 模式可运行但 OCR 速度较慢。
- **ADB**：需配置 ADB 可执行文件路径，默认指向 MuMu 模拟器 12 自带的 `adb.exe`。
- **模拟器**：默认 MuMu 12（端口 7555），亦可改为雷电、BlueStacks 等（需调整端口，详见 [docs/configuration.md](docs/configuration.md)）。

## 快速开始

1. **获取项目**：克隆或下载本项目到本地。
2. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```
3. **（可选）配置 GPU 加速**：参考 `requirements.txt` 中的说明，安装 CUDA/cuDNN 后覆盖安装 torch：
   ```bash
   pip install --force-reinstall torch==2.6.0 torchvision==0.21.1 "numpy<2.0.0" --index-url https://download.pytorch.org/whl/cu124
   ```
   如遇 OpenMP 冲突，尝试 `pip uninstall intel-openmp`，缺失时再重新安装。
4. **配置模拟器**：编辑 `config.yaml`，将 `simulator.adb_path` 与 `adb_path` 指向你本机的 ADB 路径，确认 `simulator.port` 与模拟器一致（MuMu 12 默认 7555）。
5. **启动程序**：
   ```bash
   python mainUI.py
   ```
6. **连接设备**：在控制面板中连接模拟器，选择操作模式（寻访 / 公招），设置参数后启动。
7. **数据导入**：将 JSON / TXT / 图片或包含这些文件的目录拖入主窗口，可自动解析为抽卡数据。

## 项目结构概览

```
combine/
├── core/                        # 核心自动化模块
│   ├── enums.py                 # 枚举：OperationMode/GachaMode/RecruitMode/TaskType(22种任务)
│   ├── exceptions.py            # 集中异常定义，解除 task.py 与 tool.py 循环依赖
│   ├── constants.py             # 集中常量定义（路径/区域/端口/星级）
│   ├── simulator.py             # ADB 模拟器交互：点击/滑动/截图/minitouch
│   ├── task.py                  # 任务执行：OCR识别/图像匹配/点击/条件判断
│   ├── task_manager.py          # 任务队列管理：线程化执行/IF-WHILE 条件编排
│   └── game_manager.py          # 顶层业务编排：寻访/公招流程/Qt 信号通信
├── ui/                          # PySide6 UI 模块
│   ├── main_window.py           # 主窗口
│   ├── control.py               # 控制面板（设备连接/模式设置/循环操作）
│   ├── console.py               # 控制台日志面板
│   ├── data_view.py             # 数据视图（数值/文本双标签页）
│   ├── plot.py                  # matplotlib 绘图（交互式/波峰波谷/模式匹配）
│   ├── settings.py              # 设置面板（模拟器/日志/数据）
│   ├── dialogs.py               # 带图片的输入对话框
│   ├── global_state.py          # 全局状态单例 g
│   └── statistics.py            # 统计组件（当前未使用，见已知问题）
├── tests/                       # 正式单元测试（pytest，106 个用例）
├── img/                         # 模板图片（公招界面按钮等）
├── minitouch/                   # minitouch 二进制（多架构）
├── data.py / newData.py         # 干员数据（366 / 376 个）
├── data_manager.py              # 数据管理与分析
├── data_updater.py / html_parser.py  # HTML 数据更新脚本
├── tool.py                      # 工具类（PaddleOCR/cv2/模板匹配/文字相似度）
├── log.py                       # 日志系统（PySide6 QObject）
├── config.py                    # ConfigManager 配置管理器
├── tag统计工具.py                # Tag 组合分析工具
├── mainUI.py                    # 程序入口（高DPI/异常兜底/日志引导）
├── config.yaml                  # 配置文件
├── requirements.txt             # 运行时依赖（带版本约束）
├── requirements-dev.txt         # 开发与测试依赖
├── pyproject.toml               # 工具配置汇总（black/ruff/isort/mypy/pytest/coverage）
├── pytest.ini                   # pytest 配置
├── .editorconfig                # 编辑器风格统一
├── .gitignore                   # Git 忽略规则
├── .github/workflows/ci.yml     # CI 配置（pytest + ruff）
├── old/                         # 历史归档（不入库，见 old/README.md）
├── test/                        # 临时试验脚本（不入库，见 test/README.md）
└── docs/                        # 文档
    ├── architecture.md          # 架构文档
    ├── configuration.md         # 配置说明
    ├── development.md           # 开发指南
    ├── testing.md               # 测试指南
    ├── troubleshooting.md       # 故障排查
    ├── faq.md                   # 常见问题
    └── bugfix_log.md            # Bug 修复记录
```

更详细的架构说明见 [docs/architecture.md](docs/architecture.md)。

## 配置说明

程序运行时读取根目录下的 `config.yaml`，包含 ADB 路径、模拟器端口、日志、绘图、数据存储等配置。完整配置项说明见 [docs/configuration.md](docs/configuration.md)。

最常需要修改的是模拟器相关配置：

```yaml
adb_path: D:\YXArkNights-12.0\shell\adb.exe   # 本机 adb.exe 路径
simulator:
  adb_path: F:\ProgramFiles\YXArkNights-12.0\shell\adb.exe
  port: 7555                                    # 模拟器端口
```

## 开发指南

如需二次开发、添加新的任务类型或更新干员数据，请参考 [docs/development.md](docs/development.md)。贡献代码请遵循 [CONTRIBUTING.md](CONTRIBUTING.md) 中的约定。

更多文档：

- [docs/testing.md](docs/testing.md) — 测试指南（如何运行与编写测试）
- [docs/troubleshooting.md](docs/troubleshooting.md) — 故障排查（ADB/OCR/Qt/任务/数据等问题）
- [docs/faq.md](docs/faq.md) — 常见问题
- [docs/bugfix_log.md](docs/bugfix_log.md) — Bug 修复记录（含原代码/新代码/回滚方法）

### 运行测试

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行全部测试
python -m pytest tests/ -v

# 生成覆盖率报告
python -m pytest tests/ --cov --cov-report=term-missing
```

测试在 `tests/` 目录下，共 106 个用例，覆盖 `data_manager`、`tool`、`tag统计工具`、`config`、`html_parser`、`data` 等纯函数模块。详见 [docs/testing.md](docs/testing.md)。

### 代码风格

项目使用 [black](https://black.readthedocs.io/)、[isort](https://pycqa.github.io/isort/)、[ruff](https://docs.astral.sh/ruff/) 进行代码格式化与 lint，配置统一在 [pyproject.toml](pyproject.toml) 中。编辑器风格见 [.editorconfig](.editorconfig)。

## 已知问题

- **PLAN 模式未实现**：`OperationMode.PLAN`（自动规划）目前仅为占位，无实际逻辑。
- **`statistics.py` 为死代码**：文件被 `main_window.py` 导入但从未实例化。统计功能实际由 `PlotWidget` 调用 `data_manager.get_statistics()` 实现。保留以备未来启用，详见 [docs/faq.md](docs/faq.md)。
- **干员数据重复且不兼容**：`data.py`（366 个，含 `en/star/tag/subprofession`）与 `newData.py`（376 个，含 `obtain_method`）字段定义不一致，存在维护负担。
- **`data_updater.py` 内嵌大段 HTML**：约 472KB 的 PRTS Wiki HTML 直接写在源码中，应外置为单独文件（当前 `a.html` 已在 `.gitignore` 中排除）。
- **`Task` 类属性共享状态**：任务类使用类属性保存执行状态，缺乏线程同步机制，并发场景下可能存在风险。
- **`simulator.py` 硬编码 ADB 路径**：模块顶部 `ADB_PATH = "D:\\YXArkNights-12.0\\shell\\adb.exe"` 为开发机默认值，实际使用时应通过 `config.yaml` 或构造参数覆盖。

## 许可证

本项目采用 [MIT 许可证](LICENSE)。
