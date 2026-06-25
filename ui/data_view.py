from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QWidget, QVBoxLayout, QPlainTextEdit, QPushButton, QLabel, QTextEdit
from PySide6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor
from PySide6.QtCore import Signal

# 数据视图组件
class DataViewWidget(QWidget):
    data_changed = Signal(list)  # 数据修改信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        """初始化用户界面，创建包含数值数据和干员/Tag信息的标签页，并设置相关布局和信号连接。

        该方法构建主界面结构，包括一个标签页控件，分别用于显示数值数据（只读）和编辑干员/Tag信息。
        同时连接相关信号以响应标签页切换和文本编辑事件。

        Args:
            self: 实例对象自身。

        Returns:
            None: 此方法不返回任何值，仅完成界面初始化和信号连接。
        """
        # 创建垂直布局管理器，并设置到当前窗口
        layout = QVBoxLayout(self)
        # 设置布局边距为0，使控件紧贴窗口边缘
        layout.setContentsMargins(0, 0, 0, 0)
    
        # 创建标签页控件，用于容纳多个标签页
        self.tab_widget = QTabWidget()
    
        # 创建数值数据标签页
        numeric_widget = QWidget()
        numeric_layout = QVBoxLayout(numeric_widget)
        # 创建纯文本编辑器，用于显示数值数据
        self.numeric_editor = QPlainTextEdit()
        # 设置等宽字体Consolas，便于对齐数值
        self.numeric_editor.setFont(QFont('Consolas', 9))
        # 禁用自动换行，保持数据原始格式
        self.numeric_editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        # 设为只读模式，防止用户误修改数值数据
        self.numeric_editor.setReadOnly(True)
        # 将编辑器添加到数值数据页面的布局中
        numeric_layout.addWidget(self.numeric_editor)
        # 将数值数据页面添加到标签页，并设置标签名称
        self.tab_widget.addTab(numeric_widget, "数值数据")
    
        # 创建干员/Tag信息编辑标签页
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        # 创建纯文本编辑器，用于编辑干员和Tag信息
        self.info_editor = QPlainTextEdit()
        # 设置中文字体微软雅黑，便于显示中文信息
        self.info_editor.setFont(QFont('Microsoft YaHei', 9))
        # 将编辑器添加到信息页面的布局中
        info_layout.addWidget(self.info_editor)
    
        # 创建保存按钮，用于应用对干员/Tag信息的修改
        self.save_button = QPushButton("应用修改")
        # 连接按钮的点击信号到保存修改的方法
        self.save_button.clicked.connect(self.save_changes)
        # 将按钮添加到信息页面的布局中
        info_layout.addWidget(self.save_button)
    
        # 将干员/Tag信息页面添加到标签页，并设置标签名称
        self.tab_widget.addTab(info_widget, "干员/Tag信息")
    
        # 将标签页控件添加到主布局中
        layout.addWidget(self.tab_widget)

        # 初始化当前高亮行列表，用于存储文本高亮信息
        self.current_highlights = []
        # 默认将数值编辑器设为当前活动编辑器
        self.editor = self.numeric_editor

        # 连接标签页切换信号到处理函数，当标签页切换时触发
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
        # 连接文本编辑信号到处理函数，当干员/Tag信息文本改变时触发
        self.info_editor.textChanged.connect(self.on_info_text_changed)

    def highlight_lines(self, line_numbers):
        """高亮显示指定行"""
        self.current_highlights = line_numbers
        
        # 清除现有选择
        extra_selections = []
        
        # 为每一行创建新的选择
        for line_number in line_numbers:
            selection = QTextEdit.ExtraSelection()
            
            # 设置格式
            format = QTextCharFormat()
            format.setBackground(QColor(255, 255, 0, 100))
            format.setForeground(QColor(0, 0, 0))
            selection.format = format
            
            # 设置光标位置
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            for _ in range(line_number):
                cursor.movePosition(QTextCursor.NextBlock)
            cursor.select(QTextCursor.BlockUnderCursor)
            selection.cursor = cursor
            
            extra_selections.append(selection)
        
        self.editor.setExtraSelections(extra_selections)
        
        # 确保第一个选中的行可见
        if line_numbers:
            self.scroll_to_line(line_numbers[0])
            
    def highlight_hover_point(self, point_index):
        """高亮显示悬停点"""
        if point_index >= 0:
            self.highlight_lines([point_index])
        
    def scroll_to_line(self, line):
        """滚动到指定行并使其居中显示"""
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, line)
        self.editor.setTextCursor(cursor)
        self.editor.centerCursor() 

    def set_data(self, numeric_data = None, info_data = None):
        """设置数据"""
        # 设置数值数据
        if isinstance(numeric_data, list):
            text = "\n".join(str(x) for x in numeric_data)
            self.numeric_editor.setPlainText(text)
        elif isinstance(numeric_data, str):
            self.numeric_editor.setPlainText(numeric_data)
        elif numeric_data is False:
            self.numeric_editor.clear()
        elif numeric_data is not None:
            raise RuntimeError("未定义行为")
        
        # 设置信息数据
        if isinstance(info_data, list):
            text = "\n".join(str(x) for x in info_data)
            self.info_editor.setPlainText(text)
        elif isinstance(info_data, str):
            self.info_editor.setPlainText(info_data)
        elif info_data is False:
            self.info_editor.clear()
        elif info_data is not None:
            raise RuntimeError("未定义行为")
    
    def get_data(self) -> list:
        """获取数值数据"""
        try:
            text = self.numeric_editor.toPlainText()
            return [int(x) for x in text.split('\n') if x.strip()]
        except:
            return []
    
    def get_info_data(self) -> list:
        """获取干员/Tag信息数据"""
        return [x for x in self.info_editor.toPlainText().split('\n') if x.strip()]
    
    def on_tab_changed(self, index):
        """标签页切换处理"""
        # 如果切换到数值数据页，禁用保存按钮
        self.save_button.setEnabled(index == 1)
        if index == 0:
            self.editor = self.numeric_editor
        elif index == 1:
            self.editor = self.info_editor
    
    def on_info_text_changed(self):
        """信息文本改变处理"""
        # 启用保存按钮
        self.save_button.setEnabled(True)
    
    def save_changes(self):
        """保存修改"""
        try:
            # 获取当前编辑的数据
            info_data = self.get_info_data()
            from log import log_manager
            log_manager.debug(f"准备应用数据修改，数据条数：{len(info_data)}")
            
            # 通知主窗口保存更改
            from .global_state import g
            if hasattr(g.mainWindow, 'on_user_changed_data'):
                g.mainWindow.on_user_changed_data(info_data)
                log_manager.info("数据修改已应用")
            else:
                log_manager.error("找不到保存数据的方法")
            
            # 禁用保存按钮
            self.save_button.setEnabled(False)
            
        except Exception as e:
            from tool import error_record
            error_record(e)
            from PySide6.QtWidgets import QMessageBox
            log_manager = __import__('log').log_manager
            log_manager.error(f"保存失败：{str(e)}")
            QMessageBox.warning(self, "错误", f"保存失败：{str(e)}")