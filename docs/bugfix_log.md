# Bug 修复记录

> 本文档记录所有 Bug 修复，确保可追溯、可回滚。每条记录包含：位置、问题、修复、原因、回滚方法。
>
> 修复策略：**保守修复** — 只改明确的 bug（如缺 `raise`、变量未定义、`if`/`elif` 错误），不动业务逻辑、不重构。
>
> 修复日期：2026-08-07

---

## BF-01: tool.py 缺少 raise 关键字

- **文件**: `tool.py`
- **行号**: 328, 335（修复后行号可能偏移）
- **问题**: `ValueError(...)` 创建了异常对象但未抛出，相当于无操作。`cropping()` 方法在传入非法 `format` 或 `mode` 时不会报错，而是静默继续执行，可能导致后续逻辑使用未定义变量。
- **修复**: 在 `ValueError(...)` 前添加 `raise` 关键字。
- **原代码**:
  ```python
  ValueError(f"'{format}'格式不是合法的值")
  # ...
  ValueError(f"'{mode}'处理模式不是合法的值")
  ```
- **新代码**:
  ```python
  raise ValueError(f"'{format}'格式不是合法的值")
  # ...
  raise ValueError(f"'{mode}'处理模式不是合法的值")
  ```
- **回滚**: 删除两处 `raise` 关键字即可恢复原状。

---

## BF-02: tool.py group.sort() 返回 None

- **文件**: `tool.py`
- **行号**: 576（修复后: 577）
- **问题**: `group = group.sort(key=...)` — `list.sort()` 是原地排序并返回 `None`，执行后 `group` 变成 `None`，后续 `group[0][0][0][0]` 等访问会抛 `TypeError`。
- **修复**: 改为 `group.sort(key=...)`（原地排序，不重新赋值）。
- **原代码**:
  ```python
  group = group.sort(key=lambda x: x[0][0][0])
  ```
- **新代码**:
  ```python
  group.sort(key=lambda x: x[0][0][0])
  ```
- **回滚**: 改回 `group = group.sort(...)`。

---

## BF-03: tool.py 引用未定义的异常类

- **文件**: `tool.py`
- **行号**: 138（注释中）, 407（活跃代码）
- **问题**: `OcrError` 和 `CantFindNameError` 在 `tool.py` 中未定义。行 407 `raise CantFindNameError(...)` 会抛 `NameError` 而非预期的异常。行 138 虽被注释但意图是使用 `OcrError`。
- **修复**: 创建 `core/exceptions.py` 集中定义异常类，在 `tool.py` 中导入。
- **新增文件**: `core/exceptions.py`
- **原代码** (tool.py 导入区):
  ```python
  from data import data as DATA
  from log import log_manager as log
  ```
- **新代码**:
  ```python
  from data import data as DATA
  from log import log_manager as log
  from core.exceptions import CantFindNameError, OcrError
  ```
- **同步修改**: `core/task.py` 中的异常类定义改为从 `.exceptions` 导入（保持向后兼容的重新导出）。
- **回滚**: 删除 `tool.py` 中的 `from core.exceptions import ...` 行；将 `core/task.py` 中的 import 改回本地 class 定义；删除 `core/exceptions.py`。

---

## BF-04: newData.py 尾随逗号导致 l_tag 变元组

- **文件**: `newData.py`
- **行号**: 67（修复后: 67）
- **问题**: `self.l_tag = [...],` 尾随逗号使 `self.l_tag` 成为元组 `([...],)` 而非列表。后续 `'XXX' in self.l_tag` 检查的是字符串是否在元组中（永远 False），破坏所有依赖 `l_tag` 的逻辑。
- **修复**: 删除尾随逗号。
- **原代码**:
  ```python
              '高级资深干员',
          ],
  ```
- **新代码**:
  ```python
              '高级资深干员',
          ]
  ```
- **回滚**: 在 `]` 后添加逗号。

---

## BF-05: task.py find_imgOnScreen 中 img 变量未定义

- **文件**: `core/task.py`
- **行号**: 503-506（修复后: 495-498）
- **问题**: 当 `self.region is not None` 时，引用了不存在的 `img` 变量（应为 `screenshot`），会抛 `NameError`。只要在使用 `CLICK_IMG` 任务时设置了 `region` 参数就会崩溃。
- **修复**: 将 `img` 替换为 `screenshot`。
- **原代码**:
  ```python
  if self.region is not None:
      h, w = img.shape[:2]
      regionOffset = (int(self.region[0] * w), int(self.region[1] * h))
      img = tool.cropping(img, self.region, mode="percent")
  ```
- **新代码**:
  ```python
  if self.region is not None:
      h, w = screenshot.shape[:2]
      regionOffset = (int(self.region[0] * w), int(self.region[1] * h))
      screenshot = tool.cropping(screenshot, self.region, mode="percent")
  ```
- **回滚**: 将 `screenshot` 改回 `img`。

---

## BF-06: task.py SAVE_FROM_MEM txt 模式访问已 pop 的索引

- **文件**: `core/task.py`
- **行号**: 294-300（修复后: 286-293）
- **问题**: `img = self.l_MEM.pop(self.memIndex)` 先弹出元素，txt 模式下再访问 `self.l_MEM[self.memIndex]` — 此时 `memIndex` 可能越界或指向错误元素。
- **修复**: 将 popped 元素存入 `item` 变量，两种模式都使用 `item`。
- **原代码**:
  ```python
  img = self.l_MEM.pop(self.memIndex)
  if self.kwargs["mode"] == "png":
      cv2.imwrite(path, img)
  elif self.kwargs["mode"] == "txt":
      with open(path, "w") as f:
          f.write(self.l_MEM[self.memIndex])
  ```
- **新代码**:
  ```python
  item = self.l_MEM.pop(self.memIndex)
  if self.kwargs["mode"] == "png":
      cv2.imwrite(path, item)
  elif self.kwargs["mode"] == "txt":
      with open(path, "w") as f:
          f.write(item)
  ```
- **回滚**: 恢复为 `img = ...` 和 `self.l_MEM[self.memIndex]`。

---

## BF-07: task_manager.py hasattr 检查对象错误

- **文件**: `core/task_manager.py`
- **行号**: 45
- **问题**: `hasattr(self.tasks, "description")` 检查的是列表对象本身（永远 False），导致 `get_next_task_description()` 永远返回 None。
- **修复**: 改为 `hasattr(self.tasks[0], "description")`。
- **原代码**:
  ```python
  return self.tasks[0].description if hasattr(self.tasks, "description") else None
  ```
- **新代码**:
  ```python
  return self.tasks[0].description if hasattr(self.tasks[0], "description") else None
  ```
- **回滚**: 改回 `hasattr(self.tasks, ...)`。

---

## BF-08: task_manager.py IF/WHILE 处理 if/elif 逻辑错误

- **文件**: `core/task_manager.py`
- **行号**: 158（修复后: 158）
- **问题**: IF 处理后用 `if`（非 `elif`）检查 WHILE，导致：(1) WHILE 任务处理后不走到 `elif result` 分支，永不 emit `task_completed`；(2) IF 任务会走到 `elif result` 并 emit IF 元组。
- **修复**: 将 WHILE 的 `if` 改为 `elif`。经核查 `GameManager._on_task_completed`，IF 的 taskType 不匹配任何处理分支（no-op），因此停止 emit 无功能影响。
- **原代码**:
  ```python
  if self.current_task.taskType == TaskType.IF:
      ...
  if self.current_task.taskType == TaskType.WHILE:
  ```
- **新代码**:
  ```python
  if self.current_task.taskType == TaskType.IF:
      ...
  elif self.current_task.taskType == TaskType.WHILE:
  ```
- **影响分析**: IF 任务不再 emit `task_completed`（GameManager 对 IF 结果是 no-op，无功能影响）。WHILE 行为不变（原本就不 emit）。
- **回滚**: 将 `elif` 改回 `if`。

---

## BF-09: game_manager.py 十连转单抽递归后未 return

- **文件**: `core/game_manager.py`
- **行号**: 284-290（修复后: 283-291）
- **问题**: 当剩余次数不足十连时，切换到单抽模式并递归调用 `_arrange_next_task()`，但递归返回后**未 return**，继续执行十连逻辑，与切换意图矛盾。
- **修复**: 在递归调用后添加 `return`。
- **原代码**:
  ```python
  if self.execution_limit > 0 and self.execution_limit - self.operation_count < 10:
      self.gacha_mode = GachaMode.SINGLE
      self._arrange_next_task()
  self.update_macro_step("INFO", ...)
  ```
- **新代码**:
  ```python
  if self.execution_limit > 0 and self.execution_limit - self.operation_count < 10:
      self.gacha_mode = GachaMode.SINGLE
      self._arrange_next_task()
      return
  self.update_macro_step("INFO", ...)
  ```
- **回滚**: 删除 `return` 行。

---

## BF-10: game_manager.py _log 中 e 未定义

- **文件**: `core/game_manager.py`
- **行号**: 119
- **问题**: `_log()` 方法中 `error_record(e)` 引用未定义的 `e`，一旦调用即抛 `NameError`。且该方法忽略了 `message` 参数。
- **修复**: 改为调用 `self.log_with_time(level, message)`，正确使用参数。
- **原代码**:
  ```python
  def _log(self, level="INFO", message=None):
      if message is None:
          return
      error_record(e)
  ```
- **新代码**:
  ```python
  def _log(self, level="INFO", message=None):
      if message is None:
          return
      self.log_with_time(level, message)
  ```
- **回滚**: 改回 `error_record(e)`。

---

## BF-11: game_manager.py record 中 s_record 可能未定义

- **文件**: `core/game_manager.py`
- **行号**: 85-90
- **问题**: 两个 `if isinstance(...)` 而非 `if/elif`，若 item 既非 list 也非 str，`s_record` 未定义，后续 `data_manager.update_data(s_record)` 抛 `NameError`。
- **修复**: 改为 `if/elif/else`，else 中用 `str(item)` 兜底。
- **原代码**:
  ```python
  if isinstance(item, list):
      s_record = "!".join(item)
  if isinstance(item, str):
      s_record = item
  ```
- **新代码**:
  ```python
  if isinstance(item, list):
      s_record = "!".join(item)
  elif isinstance(item, str):
      s_record = item
  else:
      s_record = str(item)
  ```
- **回滚**: 改回两个独立 `if`，删除 `else` 分支。

---

## BF-12: simulator.py error_record(e) 中 e 未定义

- **文件**: `core/simulator.py`
- **行号**: 319（click）, 372（swipe）
- **问题**: `except Exception:` 未绑定异常变量，但 `error_record(e)` 引用 `e`，抛 `NameError`。swipe 方法还使用了裸 `except:`（反模式）。
- **修复**: 改为 `except Exception as e:`。
- **原代码**:
  ```python
  except Exception:
      error_record(e)
  # ...
  except:
      error_record(e)
  ```
- **新代码**:
  ```python
  except Exception as e:
      error_record(e)
  # ...
  except Exception as e:
      error_record(e)
  ```
- **回滚**: 改回不带 `as e` 的形式。

---

## BF-13: log.py 调试 print 残留

- **文件**: `log.py`
- **行号**: 137
- **问题**: `print(formatted_msg)` 是调试残留，每次记录日志都会打印到 stdout，与正式日志系统冲突，污染控制台输出。
- **修复**: 删除 `print(formatted_msg)` 行。
- **原代码**:
  ```python
  formatted_msg = self.formatter.format(record)

  print(formatted_msg)

  # 处理控制台输出
  ```
- **新代码**:
  ```python
  formatted_msg = self.formatter.format(record)

  # 处理控制台输出
  ```
- **回滚**: 在格式化和控制台输出之间添加 `print(formatted_msg)`。

---

## BF-14: plot.py Qt 未导入

- **文件**: `ui/plot.py`
- **行号**: 261
- **问题**: `QApplication.setOverrideCursor(Qt.ClosedHandCursor)` 引用 `Qt`，但仅从 `PySide6.QtCore` 导入了 `Signal`。用户右键拖动平移时抛 `NameError`。
- **修复**: 在导入中添加 `Qt`。
- **原代码**:
  ```python
  from PySide6.QtCore import Signal
  ```
- **新代码**:
  ```python
  from PySide6.QtCore import Signal, Qt
  ```
- **回滚**: 改回 `from PySide6.QtCore import Signal`。

---

## BF-15: main_window.py QDialog 未导入

- **文件**: `ui/main_window.py`
- **行号**: 358, 384
- **问题**: `dialog.exec_() != QDialog.Accepted` 引用 `QDialog`，但未在导入列表中。调用 `handle_missing_tag`/`handle_missing_agent` 时抛 `NameError`。
- **修复**: 在 `from PySide6.QtWidgets import (...)` 中添加 `QDialog`。
- **原代码**:
  ```python
  from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QComboBox,
                               QSpinBox, QCheckBox, QTabWidget, QTextEdit,
                               QFileDialog, QMessageBox, QScrollArea, QFrame,
                               QSplitter, QLineEdit, QPlainTextEdit)
  ```
- **新代码**:
  ```python
  from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QComboBox,
                               QSpinBox, QCheckBox, QTabWidget, QTextEdit,
                               QFileDialog, QMessageBox, QScrollArea, QFrame,
                               QSplitter, QLineEdit, QPlainTextEdit, QDialog)
  ```
- **回滚**: 删除导入中的 `QDialog`。

---

## BF-16: settings.py 日志级别往返转换坏掉

- **文件**: `ui/settings.py`
- **行号**: 264-265
- **问题**: `save_settings` 用 `getattr(logging, "INFO")` 保存为整数 20，`loadSettings` 用 `setCurrentText(str(20))` → `"20"` 不匹配下拉框选项（`["DEBUG","INFO","WARNING","ERROR","CRITICAL"]`），下拉框显示错误。
- **修复**: 使用 `logging.getLevelName()` 将整数转回字符串名，与 `on_log_settings_changed`（行 229）保持一致。
- **原代码**:
  ```python
  self.console_level.setCurrentText(str(log_settings.get('console_level', 'INFO')))
  self.file_level.setCurrentText(str(log_settings.get('file_level', 'DEBUG')))
  ```
- **新代码**:
  ```python
  self.console_level.setCurrentText(str(logging.getLevelName(log_settings.get('console_level', logging.INFO))))
  self.file_level.setCurrentText(str(logging.getLevelName(log_settings.get('file_level', logging.DEBUG))))
  ```
- **回滚**: 改回 `str(log_settings.get(...))`。

---

## BF-17: data_manager.py for 循环中修改循环变量无效

- **文件**: `data_manager.py`
- **行号**: 206-219（修复后: 203-222）
- **问题**: `for j in range(...):` 内部 `j += pattern_length` 试图跳过相邻模式，但 Python for 循环中修改循环变量不影响下一次迭代（下次仍取 range 的下一个值）。
- **修复**: 将内层 for 循环改为 while 循环，匹配时 `j += pattern_length`，不匹配时 `j += 1`。
- **原代码**:
  ```python
  for j in range(i + pattern_length, len(self.data) - pattern_length):
      compare = self.data[j:j+pattern_length]
      dist = self.dtw_distance(pattern, compare)
      similarity = 1 / (1 + dist)
      if similarity >= threshold:
          patterns.append((i, j))
          j += pattern_length
  ```
- **新代码**:
  ```python
  j = i + pattern_length
  while j < len(self.data) - pattern_length:
      compare = self.data[j:j+pattern_length]
      dist = self.dtw_distance(pattern, compare)
      similarity = 1 / (1 + dist)
      if similarity >= threshold:
          patterns.append((i, j))
          j += pattern_length
      else:
          j += 1
  ```
- **回滚**: 改回 for 循环结构。

---

## 附：新增文件

| 文件 | 用途 |
|------|------|
| `core/exceptions.py` | 集中定义异常类，解除 task.py 与 tool.py 循环依赖（BF-03 依赖） |
| `docs/bugfix_log.md` | 本文档 |

## 附：修改文件清单

| 文件 | 涉及修复编号 |
|------|-------------|
| `tool.py` | BF-01, BF-02, BF-03 |
| `newData.py` | BF-04 |
| `core/task.py` | BF-03, BF-05, BF-06 |
| `core/task_manager.py` | BF-07, BF-08 |
| `core/game_manager.py` | BF-09, BF-10, BF-11 |
| `core/simulator.py` | BF-12 |
| `log.py` | BF-13 |
| `ui/plot.py` | BF-14 |
| `ui/main_window.py` | BF-15 |
| `ui/settings.py` | BF-16 |
| `data_manager.py` | BF-17 |
