"""明日方舟助手 — 程序入口

负责 QApplication 初始化、高 DPI 适配、异常兜底与日志引导。

## 启动流程
1. 设置高 DPI 属性（必须在 QApplication 构造前调用）
2. 创建 QApplication，加载日志系统
3. 构造 MainWindow 并展示
4. 进入 Qt 事件循环

## 异常处理
- 启动期异常会写入日志并弹出 QMessageBox 提示，避免静默崩溃
- 事件循环内的异常由 Qt 自身处理，可通过 log_message 信号在控制台查看
"""

import sys
import traceback

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox


def _enable_high_dpi():
    """启用高 DPI 支持（必须在 QApplication 构造前调用）

    PySide6 6.5+ 默认开启 HighDPI，此处显式设置以防某些环境下回退。
    """
    # PySide6 6.5+ 中 AA_EnableHighDpiScaling / AA_UseHighDpiPixmaps 默认为 True
    # 这里显式 setAttribute 以兼容旧版本及显式表达意图
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        # 部分较新版本已移除这些枚举（默认开启），忽略即可
        pass


def _bootstrap_logging():
    """引导日志系统，确保启动期日志可见

    LogManager 在 log.py 模块导入时即实例化为全局单例 log_manager，
    此处只做兜底：若导入失败则退化为 print，避免日志系统不可用导致程序无法启动。
    """
    try:
        from log import log_manager
        log_manager.info("===== 程序启动 =====")
        return log_manager
    except Exception as e:
        # 日志系统本身不可用时退化为 print，不阻塞启动
        print(f"[WARN] 日志系统初始化失败，退化为 print: {e}")
        return None


def main():
    """程序主入口"""
    _enable_high_dpi()

    app = QApplication(sys.argv)
    app.setApplicationName("明日方舟助手")
    app.setOrganizationName("combine")

    log_manager = _bootstrap_logging()

    try:
        from ui.main_window import MainWindow
        window = MainWindow()
        window.show()
    except Exception as e:
        # 启动期异常：写日志 + 弹窗 + 退出
        tb = traceback.format_exc()
        if log_manager is not None:
            log_manager.error(f"启动失败: {e}\n{tb}")
        else:
            print(tb)
        QMessageBox.critical(
            None,
            "启动失败",
            f"程序启动时发生错误：\n{e}\n\n详细信息已写入日志。",
        )
        return 1

    # 进入 Qt 事件循环
    exit_code = app.exec()

    try:
        if log_manager is not None:
            log_manager.info(f"===== 程序退出 (code={exit_code}) =====")
    except Exception:
        pass

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
