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
        super().__init__(parent)
        self.setup_ui()
        self.setup_actions()
        
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 设置中文字体
        if platform.system() == 'Windows':
            font = QFont('Microsoft YaHei', 9)  # 微软雅黑
        elif platform.system() == 'Darwin':
            font = QFont('PingFang SC', 9)  # macOS 苹方
        else:
            font = QFont('Sans', 9)  # Linux 默认无衬线字体
        
        # 创建工具栏
        self.toolbar = QToolBar()
        self.toolbar.setFont(font)
        self.layout.addWidget(self.toolbar)
        
        # 创建文本编辑器
        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont('Consolas', 9))  # 使用等宽字体
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.editor.textChanged.connect(self.on_text_changed)
        self.layout.addWidget(self.editor)
        
        # 保存当前高亮的行
        self.current_highlights = []
        
    def setup_actions(self):
        # 添加工具栏按钮
        self.action_save = QAction("保存", self)
        self.action_save.triggered.connect(self.save_data)
        self.toolbar.addAction(self.action_save)
        
        self.action_reload = QAction("重新加载", self)
        self.action_reload.triggered.connect(self.reload_data)
        self.toolbar.addAction(self.action_reload)
        
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
        
    @Slot()
    def save_data(self):
        """保存数据"""
        # TODO: 实现保存功能
        print("未实现：data_view.py")
        
    @Slot()
    def reload_data(self):
        """重新加载数据"""
        # TODO: 实现重新加载功能
        print("未实现：data_view.py")
        
    def scroll_to_line(self, line):
        """滚动到指定行并使其居中显示"""
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, line)
        self.editor.setTextCursor(cursor)
        self.editor.centerCursor() 