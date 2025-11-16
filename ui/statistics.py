from PySide6.QtWidgets import QWidget, QHBoxLayout, QFrame, QVBoxLayout, QLabel, QTextEdit

# 数据展示组件
class StatisticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        layout = QHBoxLayout(self)  # 改为水平布局
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 全局统计
        global_group = QFrame()
        global_group.setFrameStyle(QFrame.Panel | QFrame.Raised)
        global_layout = QVBoxLayout(global_group)
        global_layout.setContentsMargins(5, 5, 5, 5)
        
        global_layout.addWidget(QLabel("<b>全局统计</b>"))
        self.global_stats = QTextEdit()
        self.global_stats.setReadOnly(True)
        self.global_stats.setMaximumWidth(150)  # 限制宽度
        self.global_stats.setMaximumHeight(100)
        global_layout.addWidget(self.global_stats)
        
        # 选中区域统计
        selection_group = QFrame()
        selection_group.setFrameStyle(QFrame.Panel | QFrame.Raised)
        selection_layout = QVBoxLayout(selection_group)
        selection_layout.setContentsMargins(5, 5, 5, 5)
        
        selection_layout.addWidget(QLabel("<b>选中区域统计</b>"))
        self.selection_stats = QTextEdit()
        self.selection_stats.setReadOnly(True)
        self.selection_stats.setMaximumWidth(150)  # 限制宽度
        self.selection_stats.setMaximumHeight(100)
        selection_layout.addWidget(self.selection_stats)
        
        layout.addWidget(global_group)
        layout.addWidget(selection_group)
        layout.addStretch()
    
    def update_global_stats(self, stats: dict):
        text = ""
        for key, value in stats.items():
            if isinstance(value, float):
                text += f"{key}: {value:.2f}\n"
            else:
                text += f"{key}: {value}\n"
        self.global_stats.setText(text)
    
    def update_selection_stats(self, stats: dict):
        text = ""
        for key, value in stats.items():
            if isinstance(value, float):
                text += f"{key}: {value:.2f}\n"
            else:
                text += f"{key}: {value}\n"
        self.selection_stats.setText(text)