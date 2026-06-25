from PySide6.QtWidgets import QWidget, QHBoxLayout, QFrame, QVBoxLayout, QLabel, QTextEdit

# 数据展示组件
class StatisticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        """
        初始化用户界面，创建全局统计和选中区域统计的水平布局面板。
    
        功能：
            创建一个水平布局的界面，包含两个带边框的统计区域（全局统计和选中区域统计），
            以及一个可伸展的空白区域用于布局平衡。
        参数：
            无（除了默认的 self 参数）
        返回值：
            无
        """
        layout = QHBoxLayout(self)  # 改为水平布局
        layout.setContentsMargins(5, 5, 5, 5)  # 设置布局的边距为5像素
    
        # 全局统计区域
        global_group = QFrame()  # 创建一个QFrame容器用于全局统计
        global_group.setFrameStyle(QFrame.Panel | QFrame.Raised)  # 设置面板样式为凸起
        global_layout = QVBoxLayout(global_group)  # 在容器内创建垂直布局
        global_layout.setContentsMargins(5, 5, 5, 5)  # 设置内部边距
    
        global_layout.addWidget(QLabel("<b>全局统计</b>"))  # 添加标题标签（加粗）
        self.global_stats = QTextEdit()  # 创建一个文本编辑框用于显示全局统计数据
        self.global_stats.setReadOnly(True)  # 设置为只读，防止用户编辑
        self.global_stats.setMaximumWidth(150)  # 限制宽度，避免过度伸展
        self.global_stats.setMaximumHeight(100)  # 限制高度，保持紧凑
        global_layout.addWidget(self.global_stats)  # 将文本编辑框添加到全局统计布局中
    
        # 选中区域统计区域
        selection_group = QFrame()  # 创建一个QFrame容器用于选中区域统计
        selection_group.setFrameStyle(QFrame.Panel | QFrame.Raised)  # 设置面板样式为凸起
        selection_layout = QVBoxLayout(selection_group)  # 在容器内创建垂直布局
        selection_layout.setContentsMargins(5, 5, 5, 5)  # 设置内部边距
    
        selection_layout.addWidget(QLabel("<b>选中区域统计</b>"))  # 添加标题标签（加粗）
        self.selection_stats = QTextEdit()  # 创建一个文本编辑框用于显示选中区域统计数据
        self.selection_stats.setReadOnly(True)  # 设置为只读，防止用户编辑
        self.selection_stats.setMaximumWidth(150)  # 限制宽度，避免过度伸展
        self.selection_stats.setMaximumHeight(100)  # 限制高度，保持紧凑
        selection_layout.addWidget(self.selection_stats)  # 将文本编辑框添加到选中区域统计布局中
    
        layout.addWidget(global_group)  # 将全局统计容器添加到主水平布局中
        layout.addWidget(selection_group)  # 将选中区域统计容器添加到主水平布局中
        layout.addStretch()  # 添加一个可伸展的空白区域，用于将统计区域推到左侧
    
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