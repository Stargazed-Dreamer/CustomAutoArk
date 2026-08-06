# 配置说明

本文档详细说明项目根目录下 `config.yaml` 的所有配置项、日志级别对照、模拟器端口说明以及数据文件格式。程序启动时由 `log.py` 的 `LogManager` 等模块读取该文件。

## 配置文件示例

```yaml
adb_path: D:\YXArkNights-12.0\shell\adb.exe
addr: ''
data:
  auto_save: false
  auto_save_interval: 10
  data_file: '#record.txt'
log:
  console_enabled: true
  console_level: 30
  file_enabled: false
  file_level: 20
  image_enabled: false
  log_dir: log
log_path: log
plot:
  line_width: 1
  point_size: 3
  show_grid: true
  show_points: true
  smooth_factor: 0.5
record_path: '#record.txt'
save_interval: 3000
simulator:
  adb_path: F:\ProgramFiles\YXArkNights-12.0\shell\adb.exe
  port: 7555
```

## 配置项详解

### 模拟器与 ADB

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `adb_path` | string | `D:\YXArkNights-12.0\shell\adb.exe` | 顶层 ADB 路径，部分模块直接读取此值。 |
| `addr` | string | `''` | 设备地址（如 `127.0.0.1:7555`），留空时由 `Simulator` 自动拼接 `127.0.0.1:<port>`。 |
| `simulator.adb_path` | string | `F:\ProgramFiles\YXArkNights-12.0\shell\adb.exe` | `Simulator` 初始化使用的 ADB 路径，需指向真实存在的 `adb.exe`。 |
| `simulator.port` | int | `7555` | 模拟器 ADB 端口，与模拟器设置保持一致。 |

> 提示：`adb_path` 与 `simulator.adb_path` 在配置文件中重复出现，建议保持二者一致，避免不同模块读取到不同路径。修改后请确认路径存在且可执行。

### 日志（log）

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `log.console_enabled` | bool | `true` | 是否启用控制台日志输出。 |
| `log.console_level` | int | `30` | 控制台日志级别（数值，见下表）。 |
| `log.file_enabled` | bool | `false` | 是否启用文件日志。 |
| `log.file_level` | int | `20` | 文件日志级别。 |
| `log.image_enabled` | bool | `false` | 是否启用图片日志（保存识别截图等）。 |
| `log.log_dir` | string | `log` | 日志输出目录。 |
| `log_path` | string | `log` | 顶层日志路径，与 `log.log_dir` 含义相近。 |

日志格式为 `[级别][时间][文件:行号]消息`，公共格式为 `[时间]消息`。

### 数据（data）

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `data.auto_save` | bool | `false` | 是否自动保存数据。 |
| `data.auto_save_interval` | int | `10` | 自动保存间隔（单位：分钟/次，具体由定时器决定）。 |
| `data.data_file` | string | `#record.txt` | 数据文件路径。 |
| `record_path` | string | `#record.txt` | 记录文件路径（与 `data.data_file` 含义一致，顶层冗余项）。 |
| `save_interval` | int | `3000` | 保存间隔（毫秒），用于定时保存计时器。 |

### 绘图（plot）

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `plot.line_width` | int/float | `1` | 折线宽度。 |
| `plot.point_size` | int/float | `3` | 数据点大小。 |
| `plot.show_grid` | bool | `true` | 是否显示网格。 |
| `plot.show_points` | bool | `true` | 是否显示数据点。 |
| `plot.smooth_factor` | float | `0.5` | 平滑因子（用于曲线平滑）。 |

## 日志级别对照表

本项目使用 Python 标准库 `logging` 的数值级别。配置文件中以整数表示。

| 数值 | 常量 | 名称 | 说明 |
|------|------|------|------|
| 10 | `logging.DEBUG` | DEBUG | 最详细日志，开发调试用。 |
| 20 | `logging.INFO` | INFO | 常规运行信息。 |
| 30 | `logging.WARNING` | WARNING | 警告，表示潜在问题。 |
| 40 | `logging.ERROR` | ERROR | 错误，某些功能受阻。 |
| 50 | `logging.CRITICAL` | CRITICAL | 严重错误，程序可能无法继续运行。 |

> 默认配置中控制台级别为 `30`（WARNING），文件级别为 `20`（INFO）。如需更详细的运行日志，可把 `console_level` 改为 `20` 或 `10`。
>
> 注意：设置面板（`ui/settings.py`）中日志级别以名称（`DEBUG`/`INFO`/...）显示，保存时会转换为整数写入配置，加载时再用 `logging.getLevelName()` 转回名称（BF-16 修复，详见 [bugfix_log.md](bugfix_log.md)）。

## 模拟器端口说明

不同模拟器默认的 ADB 端口不同，需根据实际使用的模拟器调整 `simulator.port`：

| 模拟器 | 默认 ADB 端口 | 备注 |
|--------|--------------|------|
| MuMu 模拟器 12 | `7555` | 本项目默认适配对象，推荐使用。 |
| MuMu 模拟器（旧版） | `7555` / `16384` | 不同版本端口可能不同，以模拟器设置为准。 |
| 雷电模拟器（LDPlayer） | `5555`（第一个实例，依次 +2） | 实例 2 为 `5557`，以此类推。 |
| BlueStacks | `5555` / `5565` | 需在设置中开启 ADB。 |
| 夜神模拟器（Nox） | `62001`（第一个实例，依次 +2） | 实例 2 为 `62025`。 |
| 逍遥模拟器（MEmu） | `21503` | —— |

连接方式：`Simulator` 内部使用 `adb connect 127.0.0.1:<port>` 连接设备。如遇连接失败，可在命令行手动执行该命令确认端口正确，并检查 `adb_path` 是否指向可用的 `adb.exe`。

> minitouch：`Simulator` 支持通过 minitouch 进行触控，`minitouch/` 目录下提供了 `x86_64`、`x86`、`arm64-v8a`、`armeabi-v7a`、`armeabi`、`maatouch` 等多架构二进制，`Simulator` 会根据设备 ABI 自动选择并推送。

## 数据文件格式说明

### `#record.txt`（招募/抽卡记录）

- 纯文本，UTF-8 编码。
- **每行一条记录**，按时间顺序追加。
- 一条记录可能是一个干员名、一个 tag，或由多个字段用 `!` 分隔而成的组合（`data_manager` 在写入时用 `"!".join(item)` 处理列表型记录）。
- 空行会被加载时忽略（`data_manager.load_data` 过滤空字符串）。
- `data_manager` 加载时会调用 `data_convert` 把这些字符串转换为数值序列，供绘图与分析使用。

示例：

```
能天使
德克萨斯
高级资深干员!术师干员!近战位
拉普兰德
```

### 拖放导入支持的文件

主窗口支持拖放以下文件/目录自动解析：

| 扩展名 | 类型 | 处理方式 |
|--------|------|----------|
| `.json` | JSON 数据 | 解析为抽卡数据结构。 |
| `.txt` | 文本数据 | 按记录文件格式加载。 |
| `.jpg` `.jpeg` `.png` `.bmp` `.tiff` `.webp` | 图片 | 作为游戏截图送入识别流程。 |
| 目录 | —— | 递归查找上述类型文件并批量处理。 |

### 干员数据文件

- `data.py`：`Data` 类，包含 `d_agent`（干员字典，含 `en`/`star`/`tag`/`subprofession`）、`d_tag`（按优先级分组的 tag 字典）、`l_agent`、`l_tag` 等结构，共 366 个干员。
- `newData.py`：另一套干员数据，376 个，字段含 `obtain_method`，与 `data.py` 不完全兼容。`tag统计工具.py` 使用 `newData`。
- 两套数据并存是历史遗留，新增功能时请注意区分依赖哪一套（详见 [README.md](../README.md) 已知问题）。
