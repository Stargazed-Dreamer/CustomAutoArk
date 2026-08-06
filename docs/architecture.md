# 架构文档

本文档描述「舟 / combine」项目的模块层次、设计模式、数据流、任务系统与信号槽通信机制。

## 模块层次

项目自上而下分为五个层次，每层只依赖其下层与同级工具/数据层，UI 层不直接接触设备控制层。

```
┌──────────────────────────────────────────────────────────────┐
│  UI 层 (ui/)                                                   │
│  main_window / control / console / data_view / plot /          │
│  settings / dialogs / global_state                             │
│  职责：界面展示、用户交互、拖放解析、绘图                          │
└───────────────┬──────────────────────────────────────────────┘
                │  Qt 信号 / 槽（解耦）
┌───────────────▼──────────────────────────────────────────────┐
│  业务编排层 (core/game_manager.py)                             │
│  GameManager：寻访/公招流程编排、计数、源石控制、                  │
│  step_completed 回调中按需生成下一组任务                          │
└───────────────┬──────────────────────────────────────────────┘
                │  add_task / execute_tasks
┌───────────────▼──────────────────────────────────────────────┐
│  任务执行层 (core/task.py + core/task_manager.py)              │
│  Task：命令对象，封装 OCR/匹配/点击/记录/条件判断                  │
│  TaskManager：后台线程顺序执行，处理 IF/WHILE/END                 │
└───────────────┬──────────────────────────────────────────────┘
                │  click / swipe / screenshot
┌───────────────▼──────────────────────────────────────────────┐
│  设备控制层 (core/simulator.py)                                 │
│  Simulator：ADB 命令封装、截图、minitouch 触控                   │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  工具层 (tool.py)        ← 被 task.py / simulator.py 等复用      │
│  PaddleOCR、cv2 图像处理、模板匹配、文字相似度、error_record       │
├──────────────────────────────────────────────────────────────┤
│  数据层                                                   │
│  data.py / newData.py  —— 干员静态数据                          │
│  data_manager.py       —— 数据加载/分析/持久化/历史记录          │
│  data_updater.py / html_parser.py —— 从 PRTS Wiki 更新数据      │
│  log.py                —— 日志系统（PySide6 QObject）           │
│  core/exceptions.py    —— 集中异常定义                          │
│  core/enums.py         —— 枚举定义                              │
└──────────────────────────────────────────────────────────────┘
```

## 核心设计模式

### 1. 命令模式（Command）

`Task` 是命令对象，封装了一次原子操作所需的所有信息（任务类型、目标文字/图片、坐标、region、条件等）。`TaskManager` 是调用者（Invoker），负责排队与执行；`GameManager` 是客户端（Client），负责构造任务列表并提交。该模式使新增操作类型时无需修改执行引擎，只需新增 `TaskType` 枚举值与对应执行分支。

### 2. 观察者模式（Observer / Qt 信号槽）

`core` 层与 `ui` 层之间不直接持有引用，而是通过 Qt 的 `Signal`/`Slot` 通信：

- `GameManager` 暴露 `device_connected`、`operation_started`、`operation_stopped`、`step_updated`、`macro_step_updated`、`log_message`、`data_updated` 等信号。
- `TaskManager` 暴露 `task_started`、`task_completed`、`task_failed`、`step_completed`、`task_terminated`、`device_disconnected` 等信号。
- `LogManager`（`log.py`）暴露 `log_message`、`step_updated`、`log_settings_changed` 信号。

这样后台线程的执行进度可以安全地回传到主线程的 UI 控件上，避免跨线程操作 UI。

### 3. 装饰器模式（Decorator）

`core/game_manager.py` 中的 `@execute_tasks` 装饰器用于为类方法自动注入任务执行能力：被装饰的方法只需返回一个 `Task` 列表，装饰器会自动把它们加入 `TaskManager` 并触发执行，简化业务方法的编写。

```python
@execute_tasks
def some_flow(self):
    return [Task(...), Task(...), ...]
```

### 4. 单例模式（Singleton，轻量）

`ui/global_state.py` 中的 `g` 是一个全局状态对象，`MainWindow` 在初始化时把自身赋给 `g.mainWindow`，供其它 UI 组件在无法通过参数传递时访问主窗口。`data_manager`、`log_manager`、`tool` 等也在模块级别以单例方式被导入复用。

## 数据流

以一次「公招标签识别 → 选择最优 tag → 招募 → 记录」为例，数据流如下：

```
用户点击「开始」
   │
   ▼
GameManager 启动流程，构造任务列表（OCR 识别 tag、点击最优 tag、确认招募…）
   │
   ▼
TaskManager.execute_tasks()  ── 在后台线程循环取队列首部 Task 执行
   │
   ├── Task(RECORD_TAG / CLICK_TEXT …)
   │      │
   │      ▼  调用 tool.py
   │      tool.ocr(...)          ← PaddleOCR 识别截图文字
   │      tool.match_template(...)← cv2 模板匹配 img/*.png
   │      tool.cosine_similarity(...)← 文字相似度匹配干员名
   │      │
   │      ▼  调用 Simulator
   │      Simulator.click(coord) / swipe(...)  ← 通过 ADB 下发指令
   │      Simulator.screenshot()                ← ADB screencap 拉回画面
   │
   ▼
Task 完成 → TaskManager emit task_completed(result)
   │
   ▼
GameManager._on_task_completed(result)
   ├── 识别结果为干员/tag → GameManager.record(item)
   │        │
   │        ▼
   │   data_manager.update_data(s_record)   ← 写入内存数据
   │   data_manager.save_data(#record.txt)  ← 持久化（受 save_interval / auto_save 控制）
   │        │
   │        ▼
   │   GameManager.emit data_updated()
   │        │
   │        ▼
   │   MainWindow.on_data_updated() → PlotWidget / DataViewWidget 刷新
   │
   └── step_completed → GameManager._arrange_next_task() 生成下一组任务
```

关键点：

- **截图来源**：`Simulator` 通过 ADB `screencap` 获取设备画面，作为后续 OCR/匹配的输入。`tool.py` 顶部定义了若干 `region_*` 常量，用于在不同界面下裁剪感兴趣区域，提升识别精度与速度。
- **OCR 与匹配**：`tool.py` 封装了 PaddleOCR 实例，并提供模板匹配、裁剪、文字相似度等工具。识别失败时抛出 `OcrError` / `CantFindNameError`，由上层决定重试或中止。
- **数据落盘**：招募/抽卡记录默认写入 `#record.txt`，每行一条；`data_manager` 负责把字符串列表转换为数值序列供分析使用。
- **可视化**：`PlotWidget` 基于 matplotlib 嵌入 PySide6，支持选择、平移、缩放、悬停同步，并可在图上标记波峰波谷与 DTW 匹配到的相似模式。

## 任务系统

### TaskType 枚举

`core/enums.py` 中的 `TaskType` 定义了 22 种任务类型，可分为五组：

| 分组 | 枚举值 | 说明 |
|------|--------|------|
| 点击操作 | `CLICK_TEXT`、`CLICK_IMG`、`CLICK_BEST_TAGS` | 点击屏幕上的文字/图片/最优 tag 组合 |
| 记录操作 | `RECORD_TAG`、`RECORD_AGENT`、`RECORD_HISTORY_PAGE`、`RECORD_SCREEN`、`RECORD_HISTORY_FLEX` | 记录 tag / 干员 / 一面抽卡记录 / 屏幕内容 / 指定数量记录 |
| 底层操作 | `CLICK_COORDINATE`、`CLICK_COORDINATE_RELATIVE`、`SWIPE_TO_RIGHT`、`SWIPE_TO_LEFT`、`SCREEN_TO_MEM`、`CROP_FROM_MEM`、`SAVE_FROM_MEM` | 坐标点击、滑动、截屏入内存、裁切/存储内存图片 |
| 界面切换 | `ENTER_SLOT`、`SWIPE_TO_PAGE` | 进入指定公招池、滑动到指定页面 |
| 流程控制 | `NOP`、`STEP_COMPLETED`、`IF`、`WHILE`、`END` | 无操作、步骤完成、条件组、条件循环、终止 |

### IF / WHILE 条件编排

`TaskManager` 在执行循环中会对 `IF` / `WHILE` / `END` 等控制任务做特殊处理，从而支持条件分支与循环：

- **IF**：条件任务组，可带 `negation` 参数表示取反。条件成立时执行其子任务，否则跳过。
- **WHILE**：条件循环任务组，条件成立时反复执行其子任务，直到条件不成立或遇到 `END`。
- **END**：终止信号，触发 `task_terminated` 信号，用于单次执行的任务收尾。
- **STEP_COMPLETED**：标记一个步骤完成，用于循环任务阶段性完成后，由 `GameManager` 经 `step_completed` 信号回调分配下一组任务（例如寻访流程中每完成一次抽卡就编排下一次）。

> 注意：BF-08 修复了 IF/WHILE 处理中 `if`/`if` 误用为 `if`/`elif` 的逻辑错误（详见 [docs/bugfix_log.md](bugfix_log.md)）。修改此类控制流时请同步检查 `GameManager._on_task_completed` 中的处理分支。

## 信号槽通信

下表列出主要的跨层信号及其用途：

| 信号源 | 信号 | 接收方 | 用途 |
|--------|------|--------|------|
| `GameManager` | `device_connected(bool)` | `ControlWidget` | 更新设备连接状态显示 |
| `GameManager` | `operation_started/stopped/paused/resumed` | `ControlWidget` | 切换按钮可用状态 |
| `GameManager` | `step_updated(str, str)` | `MainWindow` | 显示当前步骤与下一步 |
| `GameManager` | `macro_step_updated(str, str)` | `MainWindow` | 显示宏观步骤（如「寻访中」「公招中」） |
| `GameManager` | `log_message(str, str)` | `ConsoleWidget` | 输出日志到控制台 |
| `GameManager` | `data_updated()` | `MainWindow` | 触发数据视图与绘图刷新 |
| `TaskManager` | `task_completed(object)` | `GameManager` | 回传单任务结果，驱动 record 与下一步编排 |
| `TaskManager` | `step_completed()` | `GameManager` | 请求分配下一组任务 |
| `TaskManager` | `task_terminated()` | `GameManager` | END 任务终止 |
| `TaskManager` | `device_disconnected()` | `GameManager` | 设备离线处理 |
| `LogManager` | `log_message(str, str)` | `MainWindow` | 第三方日志输出 |
| `LogManager` | `log_settings_changed(dict)` | `SettingsWidget` | 日志配置变更同步 |

### 线程模型

- **主线程**：Qt 事件循环，负责所有 UI 操作与信号槽分发。
- **任务线程**：`TaskManager` 在独立 `threading.Thread` 中执行 `_task_loop`，依次取出并执行 `Task`。Task 执行过程中产生的结果通过 `task_completed` 等信号回主线程，**不得**在任务线程中直接操作控件。
- **同步**：`Simulator` 内部使用 `threading.Lock` 保护 ADB 调用。`Task` 类目前使用类属性保存执行状态，缺乏显式线程同步（见 [README.md](../README.md) 已知问题），并发场景需谨慎。

## 模块依赖关系

```
mainUI.py
  └─ ui.main_window.MainWindow
       ├─ core.game_manager.GameManager ──┬─ core.task_manager.TaskManager ── core.task.Task
       │                                   └─ core.simulator.Simulator
       ├─ ui.control / console / data_view / plot / settings / dialogs
       ├─ data_manager.data_manager
       ├─ log.log_manager
       └─ tool.tool / error_record

core.task ── tool ── data (data.py)
core.task ── core.exceptions   （解除循环依赖）
core.task ── core.enums
core.simulator ── tool
data_manager ── data (data.py)
data_updater ── html_parser ── a.html （内嵌）
tag统计工具 ── newData
```
