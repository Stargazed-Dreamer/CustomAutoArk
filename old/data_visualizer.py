import sys
from PySide6.QtWidgets import QApplication
from widgets.main_window import MainWindow

def main():
    """程序的主入口点。
    
    负责初始化PyQt应用，创建并显示主窗口，并启动应用的事件循环。
    该函数通常不被直接调用，而是由Python解释器执行。
    
    参数：
        无。
        
    返回值：
        无。函数通过 `sys.exit()` 结束进程，不返回有意义的值。
    """
    # 创建一个QApplication实例，它是所有PyQt GUI程序的必需部分，负责管理应用程序的控制流和主要设置。
    app = QApplication(sys.argv)
    # 实例化我们自定义的主窗口类 MainWindow。
    window = MainWindow()
    # 调用窗口的show()方法，使其在屏幕上可见。
    window.show()
    # 启动应用的事件循环。当窗口被关闭时，app.exec()会返回一个退出代码。
    # sys.exit()确保程序以该代码退出，进行干净的清理工作。
    sys.exit(app.exec())

if __name__ == "__main__":
    main()