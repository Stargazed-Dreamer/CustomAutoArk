from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTextEdit, QSplitter, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

from log import log_manager
from .global_state import g

# 控制台组件
class ConsoleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 左侧日志区域
        log_container = QWidget()
        log_container.setMinimumWidth(100)
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        
        log_label = QLabel("日志")
        log_label.setStyleSheet("font-weight: bold;")
        log_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        # 右侧步骤区域
        step_container = QWidget()
        step_container.setMinimumWidth(100)
        step_layout = QVBoxLayout(step_container)
        step_layout.setContentsMargins(0, 0, 0, 0)
        
        step_label = QLabel("步骤")
        step_label.setStyleSheet("font-weight: bold;")
        step_layout.addWidget(step_label)
        
        # 添加步骤显示区域
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(5, 5, 5, 5)
        status_layout.setSpacing(2)
        
        self.current_step = QLabel("正在进行：")
        self.next_step = QLabel("即将进行：")
        status_layout.addWidget(self.current_step)
        status_layout.addWidget(self.next_step)
        
        step_layout.addWidget(status_frame)
        
        # 宏观步骤记录区域
        self.step_text = QTextEdit()
        self.step_text.setReadOnly(True)
        self.step_text.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
            }
        """)
        step_layout.addWidget(self.step_text)
        
        # 添加分隔线
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(log_container)
        splitter.addWidget(step_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
    
    def append_message(self, message: str, level: str = "INFO"):
        """添加消息到日志区域"""
        # 根据日志级别设置颜色
        color = {
            "DEBUG": "#808080",    # 灰色
            "INFO": "#000000",     # 黑色
            "WARNING": "#FFA500",  # 橙色
            "ERROR": "#FF0000",    # 红色
            "CRITICAL": "#8B0000"  # 深红色
        }.get(level.upper(), "#000000")
        
        # 格式化消息
        formatted_message = f'<span style="color: {color};">{message}</span><br>'.replace("\n", "<br>")
        
        # 添加到日志区域
        self.log_text.moveCursor(QTextCursor.End)
        self.log_text.insertHtml(formatted_message)
        self.log_text.ensureCursorVisible()

        if level in ["WARNING", "ERROR", "CRITICAL"]:
            self.append_macro_step(message, level, True)
    
    def update_step(self, current_step: str, next_step: str = None):
        """更新步骤信息"""
        # 更新步骤显示区域
        self.current_step.setText(f"正在进行：{current_step}")
        self.next_step.setText(f"即将进行：{next_step if next_step else ''}")
        
        # 添加到日志记录
        # self.append_message(current_step, "INFO")
    
    def append_macro_step(self, macro_step, level = "INFO", formated = False):
        """添加消息到宏观步骤区域"""
        if formated:
            formatted_message = macro_step + "<br>"
        else:
            # 添加时间戳
            macro_step = log_manager.format(macro_step)

            # 根据级别设置颜色
            color = {
                "DEBUG": "#808080",    # 灰色
                "INFO": "#000000",     # 黑色
                "WARNING": "#FFA500",  # 橙色
                "ERROR": "#FF0000",    # 红色
                "CRITICAL": "#8B0000"  # 深红色
            }.get(level.upper(), "#000000")
            
            # 格式化消息
            formatted_message = f'<span style="color: {color};">{macro_step}</span><br>'.replace("\n", "<br>")
        
        # 添加到宏观步骤区域
        self.step_text.moveCursor(QTextCursor.End)
        self.step_text.insertHtml(formatted_message)
        self.step_text.ensureCursorVisible()