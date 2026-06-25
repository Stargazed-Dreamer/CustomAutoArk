"""
数据视图组件 (DataView)
这个模块提供了一个用于显示和编辑数据的文本编辑器组件。

主要功能：
1. 提供文本编辑器界面，支持数据的查看和编辑
2. 支持数据的保存和重新加载
3. 支持行高亮显示
4. 支持数据修改信号的发送

主要接口：
- set_data(data): 设置要显示的数据
- get_data(): 获取当前编辑器中的数据
- highlight_lines(line_numbers): 高亮显示指定行
- highlight_hover_point(point_index): 高亮显示悬停点
- save_data(): 保存数据
- reload_data(): 重新加载数据

信号：
- data_changed: 当数据被修改时发出此信号
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPlainTextEdit,
                                QToolBar, QTextEdit)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QTextCursor, QAction, QFont, QColor, QTextCharFormat
import platform

class DataView(QWidget):
    # 自定义信号
    data_changed = Signal(list)  # 数据修改信号
    
    def __init__(self, parent=None):
        """
        初始化类实例。

        参数:
            self: 类实例自身。
            parent: 可选的父对象，默认为None。

        返回值:
            无。
        """
        # 调用父类的初始化方法，传入parent参数
        super().__init__(parent)
        # 初始化用户界面
        self.setup_ui()
        # 初始化动作
        self.setup_actions()
        
    def setup_ui(self):
        """初始化用户界面。

        此方法负责设置主窗口的布局、字体，并创建工具栏和文本编辑器。

        参数:
            self: 类实例本身。

        返回:
            无返回值。
        """
        # 创建一个垂直布局管理器，并应用到窗口
        self.layout = QVBoxLayout(self)
        # 设置布局的边距为零，使控件紧贴窗口边缘
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 根据操作系统类型选择合适的字体
        if platform.system() == 'Windows':
            # Windows 系统使用微软雅黑字体
            font = QFont('Microsoft YaHei', 9)
        elif platform.system() == 'Darwin':
            # macOS 系统使用苹方字体
            font = QFont('PingFang SC', 9)
        else:
            # Linux 及其他系统使用默认的无衬线字体
            font = QFont('Sans', 9)

        # 创建工具栏实例并应用字体
        self.toolbar = QToolBar()
        self.toolbar.setFont(font)
        # 将工具栏添加到布局中
        self.layout.addWidget(self.toolbar)

        # 创建文本编辑器实例
        self.editor = QPlainTextEdit()
        # 为编辑器设置等宽字体，便于代码显示
        self.editor.setFont(QFont('Consolas', 9))
        # 禁用自动换行，保持代码格式
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        # 将编辑器的文本变化信号连接到相应处理方法
        self.editor.textChanged.connect(self.on_text_changed)
        # 将文本编辑器添加到布局中
        self.layout.addWidget(self.editor)

        # 初始化一个列表，用于记录当前被高亮的行号
        self.current_highlights = []
        
    def set_data(self, data):
        """设置数据"""
        # 保存当前光标位置和滚动条位置
        cursor = self.editor.textCursor()
        current_position = cursor.position()
        scrollbar = self.editor.verticalScrollBar()
        scroll_pos = scrollbar.value()
        
        # 更新文本
        text = "\n".join(str(int(round(x))) for x in data)
        self.editor.setPlainText(text)
        
        # 恢复光标位置
        cursor.setPosition(min(current_position, len(text)))
        self.editor.setTextCursor(cursor)
        
        # 恢复滚动条位置
        scrollbar.setValue(scroll_pos)
        
    def get_data(self):
        """获取数据内容"""
        text = self.editor.toPlainText()
        try:
            # 保存当前光标位置和滚动条位置
            cursor = self.editor.textCursor()
            current_position = cursor.position()
            scrollbar = self.editor.verticalScrollBar()
            scroll_pos = scrollbar.value()
            
            # 转换数据
            data = [int(round(float(line))) for line in text.split('\n') if line.strip()]
            
            # 恢复光标位置
            cursor.setPosition(current_position)
            self.editor.setTextCursor(cursor)
            
            # 恢复滚动条位置
            scrollbar.setValue(scroll_pos)
            
            return data
        except ValueError:
            return None
            
    @Slot()
    def on_text_changed(self):
        """文本内容改变时的处理"""
        data = self.get_data()
        if data is not None:
            self.data_changed.emit(data)
            
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
        if point_index >= 0 and not self.current_highlights:
            self.highlight_lines([point_index])
        
    def scroll_to_line(self, line):
        """滚动到指定行并使其居中显示"""
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, line)
        self.editor.setTextCursor(cursor)
        self.editor.centerCursor() 