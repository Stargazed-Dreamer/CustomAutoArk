"""
统计信息组件 (StatsWidget)
这个模块提供了数据统计信息的显示界面。

主要功能：
1. 全局统计：
   - 显示整体数据的统计信息
   - 包括：数据总量、最小值、最大值等
   - 支持添加自定义统计指标

2. 局部统计：
   - 显示选中数据的统计信息
   - 包括：选中数量、选中范围的最小值和最大值等
   - 随选择实时更新

界面布局：
- 左右分栏布局
- 使用表格形式展示数据
- 支持自适应列宽
- 统一的中文字体支持

主要接口：
- update_stats(data, selected_data): 更新统计信息
- add_custom_stat(name, value): 添加自定义统计指标
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, 
                              QTableWidget, QTableWidgetItem, QLabel)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
import numpy as np
import platform

class StatsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.layout = QHBoxLayout(self)  # 改为水平布局
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 设置中文字体
        if platform.system() == 'Windows':
            font = QFont('Microsoft YaHei', 9)
        elif platform.system() == 'Darwin':
            font = QFont('PingFang SC', 9)
        else:
            font = QFont('Sans', 9)
            
        # 创建左右两个表格
        self.global_table = QTableWidget()
        self.local_table = QTableWidget()
        
        # 设置表格属性
        for table in [self.global_table, self.local_table]:
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["指标", "值"])
            table.horizontalHeader().setStretchLastSection(True)
            table.setFont(font)
            table.horizontalHeader().setFont(font)
            
        # 添加标题标签
        self.global_label = QLabel("全局统计")
        self.local_label = QLabel("局部统计")
        self.global_label.setFont(font)
        self.local_label.setFont(font)
        
        # 创建左右布局
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()
        
        left_layout.addWidget(self.global_label)
        left_layout.addWidget(self.global_table)
        
        right_layout.addWidget(self.local_label)
        right_layout.addWidget(self.local_table)
        
        # 添加到主布局
        self.layout.addLayout(left_layout)
        self.layout.addLayout(right_layout)
        
    def update_stats(self, data, selected_data=None):
        """更新统计信息"""
        if data:
            # 更新全局统计
            global_stats = [
                ("数据总量", len(data)),
                ("最小值", int(np.min(data))),
                ("最大值", int(np.max(data)))
            ]
            self._update_table(self.global_table, global_stats)
            
        if selected_data:
            # 更新局部统计
            local_stats = [
                ("选中数量", len(selected_data)),
                ("选中最小值", int(np.min(selected_data))),
                ("选中最大值", int(np.max(selected_data)))
            ]
            self._update_table(self.local_table, local_stats)
        else:
            self.local_table.setRowCount(0)
            
    def _update_table(self, table, stats):
        """更新统计表格"""
        table.setRowCount(len(stats))
        
        for row, (name, value) in enumerate(stats):
            # 设置名称
            name_item = QTableWidgetItem(str(name))
            name_item.setTextAlignment(0x0001 | 0x0080)  # Qt.AlignLeft | Qt.AlignVCenter
            table.setItem(row, 0, name_item)
            
            # 设置值
            value_item = QTableWidgetItem(str(value))
            value_item.setTextAlignment(0x0002 | 0x0080)  # Qt.AlignRight | Qt.AlignVCenter
            table.setItem(row, 1, value_item)
        
        # 调整列宽
        table.resizeColumnsToContents()
            
    def add_custom_stat(self, name, value):
        """添加自定义统计信息到全局统计表格"""
        row = self.global_table.rowCount()
        self.global_table.insertRow(row)
        
        name_item = QTableWidgetItem(str(name))
        value_item = QTableWidgetItem(str(value))
        name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.global_table.setItem(row, 0, name_item)
        self.global_table.setItem(row, 1, value_item)
        self.global_table.resizeColumnsToContents() 