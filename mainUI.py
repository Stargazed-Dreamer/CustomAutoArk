import json
import logging
import os
import platform
import sys

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QComboBox, 
                             QSpinBox, QCheckBox, QTabWidget, QTextEdit,
                             QFileDialog, QMessageBox, QScrollArea, QFrame,
                             QSplitter, QLineEdit, QPlainTextEdit, QDoubleSpinBox,
                             QInputDialog, QGroupBox, QGridLayout, QDialog,
                             QDialogButtonBox)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QAction, QFont, QTextCursor, QTextCharFormat, QImage, QPixmap

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import cv2 as cv
import numpy as np

from data import data as DATA
from data_manager import data_manager
from game_manager import Task, GameManager, OperationMode, GachaMode, RecruitMode, TaskType
from log import log_manager
from tool import tool, error_record

matplotlib.use('Qt5Agg')
# 设置matplotlib的默认字体
plt.rcParams['font.family'] = ['sans-serif']
if platform.system() == 'Windows':
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
elif platform.system() == 'Darwin':
    plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Arial']
else:
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

# 其他全局设置
plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号
plt.rcParams['font.size'] = 9
plt.rcParams['figure.dpi'] = 100

# 全局变量保存
class Global:
    def __init__(self):
        self.mainWindow = None
g = Global()

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

# 数据展示组件
class PlotWidget(QWidget):
    # 自定义信号
    data_selected = Signal(list)  # 数据选中信号
    data_modified = Signal(list)  # 数据修改信号
    hover_point_changed = Signal(int)  # 悬停点变化信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False  # 防止循环更新
        self.initUI()
        self.setup_plot()
        self.setup_interactions()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建画布
        self.figure = Figure(dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # 创建绘图区
        self.ax = self.figure.add_subplot(111)
        self.ax.grid(True, linestyle='--', alpha=0.7)
        
        # 设置标签
        self.ax.set_xlabel('时间点')
        self.ax.set_ylabel('数值')
        
    def setup_plot(self):
        # 初始化所有图形元素为None
        self.data = []
        self.x_data = []
        self.line = None
        self.scatter = None
        self.peak_scatter = None  # 确保所有图形元素属性初始化
        self.selection_rect = None
        self.hover_annotation = None
        
        # 初始化视图状态
        self.current_xlim = None
        self.current_ylim = None
        self.show_points = True
        self.grid_on = True
        
        # 初始化交互状态
        self.selected_indices = []
        self.is_selecting = False
        self.is_panning = False
        self.selection_start = None
        self.hover_index = -1
        self.pan_start = None
        
    def setup_interactions(self):
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        
    def set_data(self, data):
        if self._updating:
            return
            
        self._updating = True
        try:
            self.data = data
            self.x_data = list(range(len(data)))
            self._update_plot()
            self.data_modified.emit(self.data)
            
            # 更新全局统计信息
            stats = data_manager.get_statistics()
            if hasattr(g.mainWindow, 'global_stats'):
                g.mainWindow.global_stats.setText("\n".join(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}" for k, v in stats.items()))
        finally:
            self._updating = False

    def _update_plot(self):
        self.ax.clear()
        # 清除所有图形元素的引用
        self._safe_remove(self.line)
        self.line = None
        self._safe_remove(self.scatter)
        self.scatter = None
        self._safe_remove(self.peak_scatter)
        self.peak_scatter = None
        self._safe_remove(self.selection_rect)
        self.selection_rect = None
        self._safe_remove(self.hover_annotation)
        self.hover_annotation = None
        
        # 重新绘制逻辑
        if not self.data:
            return
        
        # 计算数据范围
        data_min = min(self.data)
        data_max = max(self.data)
        x_min = 0
        x_max = len(self.data) - 1
        
        # 设置合适的边距
        y_margin = max((data_max - data_min) * 0.05, 1)
        x_margin = max(len(self.data) * 0.02, 1)
        
        # 计算默认视图范围
        default_xlim = (x_min - x_margin, x_max + x_margin)
        default_ylim = (data_min - y_margin, data_max + y_margin)
        
        # 保存当前视图范围
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        if xlim == (0, 1) or ylim == (0, 1):
            xlim = default_xlim
            ylim = default_ylim
        
        # 绘制主线
        self.line, = self.ax.plot(self.x_data, self.data, '-', lw=1)
        
        # 绘制数据点
        if self.show_points:
            self.scatter = self.ax.scatter(self.x_data, self.data, s=20)
        
        # 绘制选中的点
        if self.selected_indices:
            selected_x = [self.x_data[i] for i in self.selected_indices]
            selected_y = [self.data[i] for i in self.selected_indices]
            self.ax.scatter(selected_x, selected_y, color='red', s=50, zorder=3)
        
        # 设置网格
        self.ax.grid(self.grid_on, linestyle='--', alpha=0.7)
        
        # 设置范围
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        
        # 设置标签
        self.ax.set_xlabel('时间点')
        self.ax.set_ylabel('数值')
        
        # 刷新画布
        self.canvas.draw()
    
    def _safe_remove(self, artist):
        """安全移除元素，避免NotImplementedError"""
        if artist is not None:
            try:
                artist.remove()
            except (NotImplementedError, ValueError):
                pass

    def on_mouse_press(self, event):
        if event.inaxes != self.ax:
            return
            
        if event.button == 1:
            # 单击左键时清除已有选择
            self.selected_indices = []
            if hasattr(g.mainWindow, 'data_view'):
                g.mainWindow.data_view.highlight_lines([])
            
            self.is_selecting = True
            self.selection_start = (event.xdata, event.ydata)
            # 安全移除选择框和悬停标注
            self._safe_remove(self.selection_rect)
            self.selection_rect = None
            self._safe_remove(self.hover_annotation)
            self.hover_annotation = None
            self.canvas.draw()
        elif event.button == 3:  # 右键
            self.is_panning = True
            self.pan_start = (event.xdata, event.ydata)
            QApplication.setOverrideCursor(Qt.ClosedHandCursor)
        
    def on_mouse_release(self, event):
        if event.button == 1 and self.is_selecting:  # 左键释放
            self.is_selecting = False
            if hasattr(self, 'hover_annotation') and self.hover_annotation in self.ax.texts:
                self.ax.texts.remove(self.hover_annotation)
            if self.selection_start and event.xdata:
                x_start = min(self.selection_start[0], event.xdata)
                x_end = max(self.selection_start[0], event.xdata)
                self.selected_indices = [i for i, x in enumerate(self.x_data)
                                      if x_start <= x <= x_end]
                self.data_selected.emit(self.selected_indices)
                
                # 更新选中区域统计信息
                if self.selected_indices:
                    start_idx = min(self.selected_indices)
                    end_idx = max(self.selected_indices) + 1
                    stats = data_manager.get_statistics(start_idx, end_idx)
                    if hasattr(g.mainWindow, 'selection_stats'):
                        g.mainWindow.selection_stats.setText("\n".join(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}" for k, v in stats.items()))
                    g.mainWindow.data_view.highlight_lines(list(range(start_idx, end_idx)))
        
        elif event.button == 3 and self.is_panning:  # 右键释放
            self.is_panning = False
            QApplication.restoreOverrideCursor()
        
        # 保持当前视图范围
        current_xlim = self.ax.get_xlim()
        current_ylim = self.ax.get_ylim()
        self._update_plot()
        self.ax.set_xlim(current_xlim)
        self.ax.set_ylim(current_ylim)
        self.canvas.draw()
    
    def on_mouse_move(self, event):
        if event.inaxes != self.ax:
            return
            
        if self.is_selecting and self.selection_start:
            # 移除旧的选择框
            self._safe_remove(self.selection_rect)
            # 创建新的选择框
            width = event.xdata - self.selection_start[0]
            height = self.ax.get_ylim()[1] - self.ax.get_ylim()[0]
            self.selection_rect = plt.Rectangle(
                (min(self.selection_start[0], event.xdata), self.ax.get_ylim()[0]),
                abs(width), height, alpha=0.2, color='yellow'
            )
            self.ax.add_patch(self.selection_rect)
            
        elif self.is_panning and self.pan_start:
            # 平移视图
            dx = self.pan_start[0] - event.xdata
            dy = self.pan_start[1] - event.ydata
            self.ax.set_xlim(self.ax.get_xlim() + dx)
            self.ax.set_ylim(self.ax.get_ylim() + dy)
        
        # 处理悬停标注，只在没有选中区域时响应
        elif not self.is_selecting and not self.is_panning and not self.selected_indices:
            self._safe_remove(self.hover_annotation)
            self.hover_annotation = None
            if event.xdata is not None:
                index = int(round(event.xdata))
                if 0 <= index < len(self.data):
                    self.hover_index = index
                    self.hover_point_changed.emit(index)
                    # 创建新标注
                    self.hover_annotation = self.ax.annotate(
                        f'({index}, {self.data[index]})',
                        (index, self.data[index]),
                        xytext=(10, 10), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                        arrowprops=dict(arrowstyle='->')
                    )
                    # 同步到数据视图
                    if hasattr(g.mainWindow, 'data_view'):
                        g.mainWindow.data_view.highlight_hover_point(index)
                        g.mainWindow.data_view.scroll_to_line(index)
        self.canvas.draw()

    def on_scroll(self, event):
        if event.inaxes != self.ax:
            return
            
        # 获取当前视图范围
        cur_xlim = self.ax.get_xlim()
        
        # 计算缩放中心（鼠标位置）
        x_data = event.xdata
        
        # 设置缩放因子
        base_scale = 1.1
        if event.button == 'up':
            scale_factor = 1/base_scale
        else:
            scale_factor = base_scale
        
        # 计算新的视图范围
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        
        # 设置新的视图范围（保持鼠标位置不变）
        rel_x = (x_data - cur_xlim[0]) / (cur_xlim[1] - cur_xlim[0])
        
        self.ax.set_xlim([x_data - rel_x * new_width,
                         x_data + (1-rel_x) * new_width])
        
        self.canvas.draw()
    
    def toggle_grid(self):
        self.grid_on = not self.grid_on
        self._update_plot()
    
    def toggle_points(self):
        self.show_points = not self.show_points
        self._update_plot()

    def loadSettings(self):
        """加载图表设置"""
        if not hasattr(self, 'ax'):
            return

        config = g.config
        plot_settings = config.get('plot', {})
        
        self.grid_on = plot_settings.get('show_grid', True)
        self.show_points = plot_settings.get('show_points', True)
        
        if self.line is not None:
            self.line.set_linewidth(plot_settings.get('line_width', 1))
        
        self._update_plot()
    
    def saveSettings(self):
        """保存图表设置"""
        if not hasattr(self, 'ax'):
            return
            
        config = g.config
        
        plot_settings = {
            'show_grid': self.grid_on,
            'show_points': self.show_points,
            'line_width': float(self.line.get_linewidth()) if self.line is not None else 1,
            'point_size': 20,
        }
        
        config['plot'] = plot_settings
        log_manager.save_config(config)

    def analyze_peaks(self):
        """波峰波谷分析"""
        if not self.data:
            QMessageBox.warning(self, "警告", "没有数据可供分析")
            return
            
        peaks, valleys = data_manager.find_peaks()
        
        # 清除之前的标记
        if hasattr(self, 'peak_scatter'):
            if self.peak_scatter in self.ax.collections:
                self.ax.collections.remove(self.peak_scatter)
        if hasattr(self, 'valley_scatter'):
            if self.valley_scatter in self.ax.collections:
                self.ax.collections.remove(self.valley_scatter)
        
        # 标记波峰
        peak_x = [self.x_data[i] for i in peaks]
        peak_y = [self.data[i] for i in peaks]
        self.peak_scatter = self.ax.scatter(peak_x, peak_y, color='red', 
                                          s=100, label='波峰', zorder=5)
        
        # 标记波谷
        valley_x = [self.x_data[i] for i in valleys]
        valley_y = [self.data[i] for i in valleys]
        self.valley_scatter = self.ax.scatter(valley_x, valley_y, color='blue',
                                            s=100, label='波谷', zorder=5)
        
        self.ax.legend()
        self.canvas.draw()
        
        # 显示统计信息
        msg = f"找到 {len(peaks)} 个波峰，{len(valleys)} 个波谷"
        QMessageBox.information(self, "分析结果", msg)
    
    def find_patterns(self):
        """相似模式查找"""
        if not self.data:
            QMessageBox.warning(self, "警告", "没有数据可供分析")
            return
            
        # 获取查找参数
        threshold, ok = QInputDialog.getDouble(
            self, "设置参数", "请输入相似度阈值 (0-1):",
            0.8, 0.1, 1.0, 2)
            
        if not ok:
            return
            
        # 使用选中区域的长度作为模式长度
        if not self.selected_indices:
            QMessageBox.warning(self, "警告", "请先选择一段数据作为模式")
            return
            
        pattern_length = len(self.selected_indices)
            
        # 执行查找
        patterns = data_manager.find_patterns(pattern_length, threshold)
        
        if not patterns:
            QMessageBox.information(self, "查找结果", "未找到相似模式")
            return
            
        # 高亮显示所有相似模式
        colors = ['r', 'g', 'b', 'c', 'm', 'y']  # 循环使用的颜色
        for i, (start1, start2) in enumerate(patterns):
            end1 = start1 + pattern_length
            end2 = start2 + pattern_length
            
            x1 = list(range(start1, end1))
            x2 = list(range(start2, end2))
            y1 = self.data[start1:end1]
            y2 = self.data[start2:end2]
            
            color = colors[i % len(colors)]
            self.ax.plot(x1, y1, f'{color}-', linewidth=2, alpha=0.5)
            self.ax.plot(x2, y2, f'{color}-', linewidth=2, alpha=0.5)
        
        self.canvas.draw()        
        # 显示结果
        msg = f"找到 {len(patterns)} 组相似模式\n已在图表中全部标记"
        QMessageBox.information(self, "查找结果", msg)

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

class DataViewWidget(QWidget):
    data_changed = Signal(list)  # 数据修改信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 数值数据页
        numeric_widget = QWidget()
        numeric_layout = QVBoxLayout(numeric_widget)
        self.numeric_editor = QPlainTextEdit()
        self.numeric_editor.setFont(QFont('Consolas', 9))
        self.numeric_editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.numeric_editor.setReadOnly(True)  # 设为只读
        numeric_layout.addWidget(self.numeric_editor)
        self.tab_widget.addTab(numeric_widget, "数值数据")
        
        # 干员/tag数据页
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        self.info_editor = QPlainTextEdit()
        self.info_editor.setFont(QFont('Microsoft YaHei', 9))
        info_layout.addWidget(self.info_editor)
        
        # 添加保存按钮
        self.save_button = QPushButton("应用修改")
        self.save_button.clicked.connect(self.save_changes)
        info_layout.addWidget(self.save_button)
        
        self.tab_widget.addTab(info_widget, "干员/Tag信息")
        
        layout.addWidget(self.tab_widget)

        # 保存当前高亮的行
        self.current_highlights = []
        self.editor = self.numeric_editor

        # 连接标签页切换信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # 连接文本编辑信号
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
            log_manager.debug(f"准备应用数据修改，数据条数：{len(info_data)}")
            
            # 通知主窗口保存更改
            if hasattr(g.mainWindow, 'on_user_changed_data'):
                g.mainWindow.on_user_changed_data(info_data)
                log_manager.info("数据修改已应用")
            else:
                log_manager.error("找不到保存数据的方法")
            
            # 禁用保存按钮
            self.save_button.setEnabled(False)
            
        except Exception as e:
            error_record(e)
            log_manager.error(f"保存失败：{str(e)}")
            QMessageBox.warning(self, "错误", f"保存失败：{str(e)}")

# 控制组件
class SettingsWidget(QWidget):
    # 添加设置变更信号
    settings_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 模拟器设置组
        simulator_group = QGroupBox("模拟器设置")
        simulator_layout = QVBoxLayout()
        
        # ADB路径设置
        adb_layout = QHBoxLayout()
        adb_layout.addWidget(QLabel("ADB路径:"))
        self.adb_path = QLineEdit()
        self.browse_adb_btn = QPushButton("浏览")
        adb_layout.addWidget(self.adb_path)
        adb_layout.addWidget(self.browse_adb_btn)
        simulator_layout.addLayout(adb_layout)
        
        # 端口设置
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("监听端口:"))
        self.port = QSpinBox()
        self.port.setRange(1024, 65535)
        self.port.setValue(7555)
        port_layout.addWidget(self.port)
        port_layout.addStretch()
        simulator_layout.addLayout(port_layout)
        
        simulator_group.setLayout(simulator_layout)
        layout.addWidget(simulator_group)
        
        # 日志设置组
        log_group = QGroupBox("日志设置")
        log_layout = QVBoxLayout()
        
        # 控制台日志
        console_layout = QHBoxLayout()
        self.console_enabled = QCheckBox("控制台日志")
        self.console_enabled.setChecked(log_manager.settings['console_enabled'])
        self.console_level = QComboBox()
        self.console_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.console_level.setCurrentText(
            str(logging.getLevelName(log_manager.settings['console_level']))
        )
        console_layout.addWidget(self.console_enabled)
        console_layout.addWidget(self.console_level)
        log_layout.addLayout(console_layout)
        
        # 文件日志
        file_layout = QHBoxLayout()
        self.file_enabled = QCheckBox("文件日志")
        self.file_enabled.setChecked(log_manager.settings['file_enabled'])
        self.file_level = QComboBox()
        self.file_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.file_level.setCurrentText(
            str(logging.getLevelName(log_manager.settings['file_level']))
        )
        file_layout.addWidget(self.file_enabled)
        file_layout.addWidget(self.file_level)
        log_layout.addLayout(file_layout)
        
        # 图片日志
        image_layout = QHBoxLayout()
        self.image_enabled = QCheckBox("图片日志")
        self.image_enabled.setChecked(log_manager.settings['image_enabled'])
        image_layout.addWidget(self.image_enabled)
        image_layout.addStretch()
        log_layout.addLayout(image_layout)
        
        # 日志目录
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("日志目录:"))
        self.log_path = QLineEdit()
        self.log_path.setText(log_manager.settings['log_dir'])
        self.browse_log_btn = QPushButton("浏览")
        dir_layout.addWidget(self.log_path)
        dir_layout.addWidget(self.browse_log_btn)
        log_layout.addLayout(dir_layout)
        
        # 日志清理
        clean_layout = QHBoxLayout()
        self.clean_days = QSpinBox()
        self.clean_days.setRange(1, 365)
        self.clean_days.setValue(30)
        self.clean_btn = QPushButton("清理日志")
        clean_layout.addWidget(QLabel("保留天数:"))
        clean_layout.addWidget(self.clean_days)
        clean_layout.addWidget(self.clean_btn)
        log_layout.addLayout(clean_layout)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # 数据设置组
        data_group = QGroupBox("数据设置")
        data_layout = QVBoxLayout()
        
        # 数据文件路径
        data_file_layout = QHBoxLayout()
        self.data_file = QLineEdit()
        data_file_layout.addWidget(QLabel("数据文件:"))
        data_file_layout.addWidget(self.data_file)
        browse_data_btn = QPushButton("浏览")
        browse_data_btn.clicked.connect(self.browse_data)
        data_file_layout.addWidget(browse_data_btn)
        data_layout.addLayout(data_file_layout)
        
        # 自动保存设置
        auto_save_layout = QHBoxLayout()
        self.auto_save = QCheckBox("自动保存")
        auto_save_layout.addWidget(self.auto_save)
        auto_save_layout.addWidget(QLabel("间隔:"))
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(1, 60)
        self.auto_save_interval.setValue(5)
        auto_save_layout.addWidget(self.auto_save_interval)
        auto_save_layout.addWidget(QLabel("分钟"))
        data_layout.addLayout(auto_save_layout)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        # 保存按钮
        self.save_btn = QPushButton("保存设置")
        layout.addWidget(self.save_btn)
        
        # 连接信号
        self.browse_log_btn.clicked.connect(self.browse_log)
        self.clean_btn.clicked.connect(self.clean_logs)
        self.save_btn.clicked.connect(self.save_settings)
        
        # 连接日志设置变更信号
        log_manager.log_settings_changed.connect(self.on_log_settings_changed)
        
        # 连接模拟器设置变更信号
        self.browse_adb_btn.clicked.connect(self.browse_adb)
    
    def browse_log(self):
        """选择日志目录"""
        path = QFileDialog.getExistingDirectory(self, "选择日志目录")
        if path:
            self.log_path.setText(path)
    
    def clean_logs(self):
        """清理日志"""
        days = self.clean_days.value()
        reply = QMessageBox.question(
            self,
            "确认清理",
            f"确定要清理{days}天前的日志吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            log_manager.clear_logs(days)
    
    def save_settings(self):
        """保存设置"""
        # 保存日志设置
        new_log_settings = {
            'console_enabled': self.console_enabled.isChecked(),
            'file_enabled': self.file_enabled.isChecked(),
            'image_enabled': self.image_enabled.isChecked(),
            'console_level': getattr(logging, self.console_level.currentText()),
            'file_level': getattr(logging, self.file_level.currentText()),
            'log_dir': self.log_path.text().strip()
        }
        log_manager.update_settings(new_log_settings)
        
        # 保存模拟器设置
        simulator_settings = {
            'adb_path': self.adb_path.text().strip(),
            'port': self.port.value()
        }
        
        # 保存数据设置
        data_settings = {
            'data_file': self.data_file.text().strip(),
            'auto_save': self.auto_save.isChecked(),
            'auto_save_interval': self.auto_save_interval.value()
        }
        
        # 加载当前配置
        config = g.config
        
        # 更新配置
        config['log'] = new_log_settings
        config['simulator'] = simulator_settings
        config['data'] = data_settings
        
        # 保存配置
        g.config = config

        if log_manager.save_config(config):
            g.mainWindow.loadSettings()
            g.mainWindow.statusBar().showMessage("设置已保存", 3000)
        else:
            g.mainWindow.statusBar().showMessage("设置保存失败", 3000)
    
    def on_log_settings_changed(self, settings: dict):
        """处理日志设置变更"""
        self.console_enabled.setChecked(settings['console_enabled'])
        self.file_enabled.setChecked(settings['file_enabled'])
        self.image_enabled.setChecked(settings['image_enabled'])
        self.console_level.setCurrentText(str(logging.getLevelName(settings['console_level'])))
        self.file_level.setCurrentText(str(logging.getLevelName(settings['file_level'])))
        self.log_path.setText(settings['log_dir'])
    
    def browse_data(self):
        """选择数据文件"""
        path, _ = QFileDialog.getOpenFileName(self, "选择数据文件", "", "文本文件 (*.txt)")
        if path:
            self.data_file.setText(path)
    
    def browse_adb(self):
        """选择ADB文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择ADB文件",
            "",
            "ADB文件 (adb.exe);;所有文件 (*.*)"
        )
        if file_path:
            self.adb_path.setText(file_path)

    def loadSettings(self):
        """加载设置"""
        config = g.config
        
        # 加载模拟器设置
        simulator_settings = config.get('simulator', {})
        self.adb_path.setText(simulator_settings.get('adb_path', ''))
        self.port.setValue(simulator_settings.get('port', 7555))
        
        # 加载日志设置
        log_settings = config.get('log', {})
        self.console_enabled.setChecked(log_settings.get('console_enabled', True))
        self.file_enabled.setChecked(log_settings.get('file_enabled', True))
        self.image_enabled.setChecked(log_settings.get('image_enabled', True))
        self.console_level.setCurrentText(str(log_settings.get('console_level', 'INFO')))
        self.file_level.setCurrentText(str(log_settings.get('file_level', 'DEBUG')))
        self.log_path.setText(log_settings.get('log_dir', 'log'))
        self.clean_days.setValue(log_settings.get('cleanup_days', 30))
        
        # 加载数据设置
        data_settings = config.get('data', {})
        self.data_file.setText(data_settings.get('file_path', '#record.txt'))
        self.auto_save.setChecked(data_settings.get('auto_save', True))
        self.auto_save_interval.setValue(data_settings.get('auto_save_interval', 5))

class ControlWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.game_manager = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 设备连接区域
        device_group = QFrame()
        device_group.setFrameStyle(QFrame.Panel | QFrame.Raised)
        device_layout = QVBoxLayout(device_group)
        
        # 小面板按钮
        self.btn_mini_panel = QPushButton("打开小面板")
        self.btn_mini_panel.clicked.connect(self.show_mini_panel)
        self.btn_mini_panel.setEnabled(False)
        device_layout.addWidget(self.btn_mini_panel)
        
        # 连接按钮
        self.btn_connect = QPushButton("连接设备")
        self.btn_connect.clicked.connect(self.on_connect_clicked)
        device_layout.addWidget(self.btn_connect)
        
        # 记录画面按钮
        self.btn_record = QPushButton("记录画面")
        font = self.btn_record.font()
        font.setPointSize(9)
        self.btn_record.setFont(font)
        self.btn_record.clicked.connect(self.do_record_screen)
        self.btn_record.setEnabled(False)
        device_layout.addWidget(self.btn_record)
        
        layout.addWidget(device_group)
        
        # 模式设置区域
        mode_group = QFrame()
        mode_group.setFrameStyle(QFrame.Panel | QFrame.Raised)
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.addWidget(QLabel("<b>模式设置</b>"))
        
        # 公招模式选择
        recruit_layout = QGridLayout()
        recruit_layout.addWidget(QLabel("公招模式:"), 0, 0)
        self.recruit_mode = QComboBox()
        self.recruit_mode.addItems([mode.value for mode in RecruitMode])
        self.recruit_mode.setEnabled(False)
        self.recruit_mode.currentTextChanged.connect(self.on_recruit_mode_changed)
        recruit_layout.addWidget(self.recruit_mode, 0, 1)
        
        # 公招栏位选择
        recruit_layout.addWidget(QLabel("选择栏位:"), 1, 0)
        self.recruit_slot_select = QSpinBox()
        self.recruit_slot_select.setRange(1, 4)
        self.recruit_slot_select.setEnabled(False)
        self.recruit_slot_select.valueChanged.connect(self.on_recruit_slot_changed)
        recruit_layout.addWidget(self.recruit_slot_select, 1, 1)
        mode_layout.addLayout(recruit_layout)
        
        # 抽卡模式选择
        gacha_layout = QGridLayout()
        gacha_layout.addWidget(QLabel("抽卡模式:"), 0, 0)
        self.gacha_mode = QComboBox()
        self.gacha_mode.addItems([mode.value for mode in GachaMode])
        self.gacha_mode.setEnabled(False)
        self.gacha_mode.currentTextChanged.connect(self.on_gacha_mode_changed)
        gacha_layout.addWidget(self.gacha_mode, 0, 1)

        # 卡池选择
        gacha_layout.addWidget(QLabel("选择卡池:"), 1, 0)
        self.gacha_pool_select = QSpinBox()
        self.gacha_pool_select.setRange(1, 10)
        self.gacha_pool_select.setEnabled(False)
        self.gacha_pool_select.valueChanged.connect(self.on_gacha_pool_changed)
        gacha_layout.addWidget(self.gacha_pool_select, 1, 1)
        # 源石消耗选项
        self.use_originite = QCheckBox("使用源石")
        self.use_originite.setEnabled(False)
        self.use_originite.stateChanged.connect(self.on_use_originite_changed)
        gacha_layout.addWidget(self.use_originite, 1, 2, 1, 2)
        
        mode_layout.addLayout(gacha_layout)
        
        layout.addWidget(mode_group)
        
        # 循环操作组
        loop_group = QFrame()
        loop_group.setFrameStyle(QFrame.Panel | QFrame.Raised)
        loop_layout = QVBoxLayout(loop_group)
        
        loop_layout.addWidget(QLabel("<b>循环操作</b>"))
        
        # 模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([mode.value for mode in OperationMode])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.mode_combo.setEnabled(False)
        mode_layout.addWidget(self.mode_combo)
        loop_layout.addLayout(mode_layout)
        
        # 停止条件设置
        stop_layout = QHBoxLayout()
        self.stop_condition = QCheckBox()
        self.stop_condition.setEnabled(False)
        self.stop_condition.stateChanged.connect(self.on_stop_condition_changed)
        stop_layout.addWidget(self.stop_condition)
        self.stop_condition_label = QLabel("在遇见六星干员时停止")  # 默认显示
        stop_layout.addWidget(self.stop_condition_label)
        stop_layout.addStretch()
        loop_layout.addLayout(stop_layout)
        
        # 循环次数设置
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("执行次数:"))
        self.count_input = QSpinBox()
        self.count_input.setRange(0, 999999)
        self.count_input.setValue(0)
        self.count_input.setEnabled(False)
        count_layout.addWidget(self.count_input)
        count_layout.addWidget(QLabel("(0表示无限循环)"))
        count_layout.addStretch()
        loop_layout.addLayout(count_layout)
        
        # 启停控制
        control_layout = QHBoxLayout()
        
        # 开始/暂停按钮
        self.btn_start_pause = QPushButton("开始")
        font = self.btn_start_pause.font()
        font.setPointSize(14)
        self.btn_start_pause.setFont(font)
        self.btn_start_pause.setMinimumHeight(50)
        self.btn_start_pause.clicked.connect(self.toggle_operation)
        self.btn_start_pause.setEnabled(False)
        control_layout.addWidget(self.btn_start_pause)
        
        # 继续按钮（初始隐藏）
        self.btn_resume = QPushButton("继续")
        self.btn_resume.setFont(font)
        self.btn_resume.setMinimumHeight(50)
        self.btn_resume.clicked.connect(self.resume_operation)
        self.btn_resume.hide()
        control_layout.addWidget(self.btn_resume)
        
        # 重置按钮（初始隐藏）
        self.btn_reset = QPushButton("重置")
        self.btn_reset.setFont(font)
        self.btn_reset.setMinimumHeight(50)
        self.btn_reset.clicked.connect(self.reset_operation)
        self.btn_reset.hide()
        control_layout.addWidget(self.btn_reset)
        
        loop_layout.addLayout(control_layout)
        layout.addWidget(loop_group)        
        layout.addStretch()
    
    def on_recruit_mode_changed(self, mode_text: str):
        """公招模式改变处理"""
        mode = RecruitMode(mode_text)
        self.game_manager.set_recruit_mode(mode)
    
    def on_gacha_mode_changed(self, mode_text: str):
        """抽卡模式改变处理"""
        mode = GachaMode(mode_text)
        self.game_manager.set_gacha_mode(mode)
    
    def on_use_originite_changed(self, state):
        """源石消耗选项改变处理"""
        self.game_manager.set_use_originite(state)
    
    def on_recruit_slot_changed(self, value: int):
        """公招栏位改变处理"""
        self.game_manager.set_recruit_slot(value)
    
    def on_gacha_pool_changed(self, value: int):
        """卡池改变处理"""
        self.game_manager.set_gacha_pool(value)
    
    def on_mode_changed(self, index):
        """模式切换处理"""
        # 启用停止条件设置
        self.stop_condition.setEnabled(True)
        
        # 根据模式调整UI状态
        if index == 0:  # 干员寻访
            self.stop_condition_label.setText("在遇见六星干员时停止")
        elif index == 1:  # 公开招募
            self.stop_condition_label.setText("在遇见罕见tag时停止")
        else:  # 自动规划
            self.stop_condition_label.setText("在遇见六星干员/罕见tag时停止")
    
    def on_stop_condition_changed(self, state):
        """停止条件改变时的处理"""
        self.count_input.setEnabled(not state)
    
    def enable_controls(self, enabled: bool):
        """启用或禁用所有控件"""
        # 记录按钮
        self.btn_record.setEnabled(enabled)
        self.btn_mini_panel.setEnabled(enabled and not self.btn_start_pause.text() == "暂停")
        
        # 循环操作控件
        self.mode_combo.setEnabled(enabled)
        self.stop_condition.setEnabled(enabled)
        self.count_input.setEnabled(enabled and not self.stop_condition.isChecked())
        self.btn_start_pause.setEnabled(enabled and not hasattr(self, 'mini_panel'))
        
        # 模式设置控件
        self.recruit_mode.setEnabled(enabled)
        self.gacha_mode.setEnabled(enabled)
        self.recruit_slot_select.setEnabled(enabled)
        self.gacha_pool_select.setEnabled(enabled)
        self.use_originite.setEnabled(enabled)
    
    def disable_settings(self):
        """禁用所有设置项"""
        self.recruit_mode.setEnabled(False)
        self.gacha_mode.setEnabled(False)
        self.recruit_slot_select.setEnabled(False)
        self.gacha_pool_select.setEnabled(False)
        self.use_originite.setEnabled(False)
        self.mode_combo.setEnabled(False)
        self.stop_condition.setEnabled(False)
        self.count_input.setEnabled(False)
        self.btn_record.setEnabled(False)
    
    def toggle_operation(self):
        """切换操作状态"""
        if self.btn_start_pause.text() == "开始":
            reply = QMessageBox.question(
                self, '确认开始',
                "确定要开始执行吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No)
                
            if reply == QMessageBox.Yes:
                mode = self.mode_combo.currentText()
                if self.stop_condition.isChecked():
                    param = -1  # 遇到特定条件时停止
                else:
                    param = self.count_input.value()  # 使用用户设置的循环次数
                self.game_manager.start_operation(OperationMode(mode), param)
        else:  # 暂停
            self.game_manager.pause_operation()
    
    def resume_operation(self):
        """恢复操作"""
        self.game_manager.resume_operation()
    
    def reset_operation(self):
        """重置操作"""
        reply = QMessageBox.question(
            self, '确认重置',
            "确定要重置操作吗？这将停止当前操作并清除计数。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            self.game_manager.reset_operation()
    
    def on_connect_clicked(self):
        """连接设备"""
        adb_path = g.mainWindow.settings_widget.adb_path.text().strip()
        if not adb_path:
            QMessageBox.warning(self, "警告", "请先设置ADB路径")
            return
            
        # 初始化游戏管理器
        self.game_manager = g.mainWindow.game_manager
        
        # 连接游戏管理器信号
        self.game_manager.device_connected.connect(self.on_device_connection_changed)
        self.game_manager.operation_started.connect(self.on_operation_started)
        self.game_manager.operation_stopped.connect(self.on_operation_stopped)
        self.game_manager.operation_paused.connect(self.on_operation_paused)
        self.game_manager.operation_resumed.connect(self.on_operation_resumed)
        
        # 连接设备
        self.game_manager.connect_device(adb_path)
    
    def do_record_screen(self):
        """记录画面"""
        if self.game_manager:
            self.game_manager.taskAdd_recordScreen()
    
    def on_device_connection_changed(self, connected: bool):
        """设备连接状态改变时的处理"""
        # 启用/禁用所有控件
        self.enable_controls(connected)
        
        # 更新连接按钮状态
        if connected:
            self.btn_connect.setText("已连接")
            self.btn_connect.setEnabled(False)
        else:
            self.btn_connect.setText("连接设备")
            self.btn_connect.setEnabled(True)
    
    def on_operation_started(self):
        """操作开始时的处理"""
        self.btn_start_pause.setText("暂停")
        self.btn_start_pause.setStyleSheet("background-color: #ff9800;")  # 橙色
        self.btn_resume.hide()
        self.btn_reset.hide()
        self.disable_settings()  # 禁用设置
        self.btn_mini_panel.setEnabled(False)  # 禁用小面板按钮
    
    def on_operation_stopped(self):
        """操作停止时的处理"""
        self.btn_start_pause.setText("开始")
        self.btn_start_pause.setStyleSheet("")
        self.btn_start_pause.show()
        self.btn_resume.hide()
        self.btn_reset.hide()
        self.enable_settings()  # 启用设置
    
    def on_operation_paused(self):
        """操作暂停时的处理"""
        self.btn_start_pause.hide()
        self.btn_resume.show()
        self.btn_reset.show()
        self.btn_resume.setStyleSheet("background-color: #4caf50;")  # 绿色
        self.btn_reset.setStyleSheet("background-color: #f44336;")   # 红色
        # 暂停时不改变设置状态
    
    def on_operation_resumed(self):
        """操作恢复时的处理"""
        self.btn_resume.hide()
        self.btn_reset.hide()
        self.btn_start_pause.show()
        self.btn_start_pause.setText("暂停")
        self.btn_start_pause.setStyleSheet("background-color: #ff9800;")  # 橙色
        self.disable_settings()  # 重新禁用设置

    def enable_settings(self):
        """启用所有设置项"""
        enabled = self.btn_start_pause.isEnabled()  # 根据当前连接状态决定是否启用
        self.btn_mini_panel.setEnabled(enabled)
        self.recruit_mode.setEnabled(enabled)
        self.gacha_mode.setEnabled(enabled)
        self.recruit_slot_select.setEnabled(enabled)
        self.gacha_pool_select.setEnabled(enabled)
        self.use_originite.setEnabled(enabled)
        self.mode_combo.setEnabled(enabled)
        self.stop_condition.setEnabled(enabled)
        self.count_input.setEnabled(enabled and not self.stop_condition.isChecked())
        self.btn_record.setEnabled(enabled)

    def show_mini_panel(self):
        """显示小面板"""
        if not hasattr(self, 'mini_panel'):
            self.mini_panel = MiniPanel(self.game_manager, self)
            self.mini_panel.show()
            # 禁用循环模式的启动按钮
            self.btn_start_pause.setEnabled(False)
        else:
            self.mini_panel.show()
            self.mini_panel.raise_()

class MiniPanel(QWidget):
    def __init__(self, game_manager, control_widget):
        super().__init__()
        self.game_manager = game_manager
        self.control_widget = control_widget
        self.initUI()
        self.setWindowFlags(Qt.Window)  # 设置为独立窗口

    def initUI(self):
        self.setWindowTitle('测试面板')
        layout = QVBoxLayout(self)
        
        # 创建任务类型选择下拉框
        task_type_layout = QHBoxLayout()
        task_type_layout.addWidget(QLabel("任务类型:"))
        self.task_type_combo = QComboBox()
        self.task_type_combo.addItems([t.value for t in TaskType])
        self.task_type_combo.currentTextChanged.connect(self.on_task_type_changed)
        task_type_layout.addWidget(self.task_type_combo)
        layout.addLayout(task_type_layout)
        
        # 创建参数输入区域
        param_group = QGroupBox("参数设置")
        self.param_layout = QVBoxLayout(param_group)
        
        # 通用参数
        common_params = QGridLayout()
        
        # 超时设置
        common_params.addWidget(QLabel("超时(秒):"), 0, 0)
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(1, 60)
        self.timeout_input.setValue(4)
        common_params.addWidget(self.timeout_input, 0, 1)
        
        # 重试次数
        common_params.addWidget(QLabel("重试次数:"), 0, 2)
        self.retry_input = QSpinBox()
        self.retry_input.setRange(1, 100)
        self.retry_input.setValue(50)
        common_params.addWidget(self.retry_input, 0, 3)
        
        # 前置等待
        common_params.addWidget(QLabel("前置等待(秒):"), 1, 0)
        self.pre_wait_input = QDoubleSpinBox()
        self.pre_wait_input.setRange(0, 10)
        self.pre_wait_input.setSingleStep(0.1)
        common_params.addWidget(self.pre_wait_input, 1, 1)
        
        # 后置等待
        common_params.addWidget(QLabel("后置等待(秒):"), 1, 2)
        self.post_wait_input = QDoubleSpinBox()
        self.post_wait_input.setRange(0, 10)
        self.post_wait_input.setSingleStep(0.1)
        common_params.addWidget(self.post_wait_input, 1, 3)
        
        self.param_layout.addLayout(common_params)
        
        # 特定参数区域（动态变化）
        self.specific_param_widget = QWidget()
        self.specific_param_layout = QVBoxLayout(self.specific_param_widget)
        self.param_layout.addWidget(self.specific_param_widget)
        
        layout.addWidget(param_group)
        
        # 执行按钮
        self.execute_btn = QPushButton("执行任务")
        self.execute_btn.clicked.connect(self.execute_task)
        layout.addWidget(self.execute_btn)

        # 自定义任务按钮
        self.execute_custom_task_btn = QPushButton("执行自定义任务")
        self.execute_custom_task_btn.clicked.connect(self.execute_custom_task)
        layout.addWidget(self.execute_custom_task_btn)
        
        # 初始化特定参数界面
        self.on_task_type_changed(self.task_type_combo.currentText())
        
        # 设置合适的窗口大小
        self.setMinimumWidth(400)
    
    def clear_specific_params(self):
        """清除特定参数区域的所有控件"""
        while self.specific_param_layout.count():
            item = self.specific_param_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def on_task_type_changed(self, task_type):
        """当任务类型改变时更新参数输入界面"""
        self.clear_specific_params()
        
        if task_type in ["点击文字", "点击图片"]:
            # 添加目标输入
            target_layout = QHBoxLayout()
            target_layout.addWidget(QLabel("目标:"))
            self.target_input = QLineEdit()
            target_layout.addWidget(self.target_input)
            self.specific_param_layout.addLayout(target_layout)
            
            # 添加复用和公招检查选项
            options_layout = QHBoxLayout()
            self.reuse_check = QCheckBox("坐标复用")
            self.recruit_check = QCheckBox("公招检查")
            options_layout.addWidget(self.reuse_check)
            options_layout.addWidget(self.recruit_check)
            self.specific_param_layout.addLayout(options_layout)
            
        elif task_type in ["点击指定坐标"]:
            coord_layout = QHBoxLayout()
            coord_layout.addWidget(QLabel("X:"))
            self.x_input = QSpinBox()
            self.x_input.setRange(0, 1920)
            coord_layout.addWidget(self.x_input)
            coord_layout.addWidget(QLabel("Y:"))
            self.y_input = QSpinBox()
            self.y_input.setRange(0, 1080)
            coord_layout.addWidget(self.y_input)
            self.specific_param_layout.addLayout(coord_layout)
            
        elif task_type in ["点击相对位置"]:
            coord_layout = QHBoxLayout()
            coord_layout.addWidget(QLabel("相对X(0-1):"))
            self.rx_input = QDoubleSpinBox()
            self.rx_input.setRange(0, 1)
            self.rx_input.setSingleStep(0.1)
            coord_layout.addWidget(self.rx_input)
            coord_layout.addWidget(QLabel("相对Y(0-1):"))
            self.ry_input = QDoubleSpinBox()
            self.ry_input.setRange(0, 1)
            self.ry_input.setSingleStep(0.1)
            coord_layout.addWidget(self.ry_input)
            self.specific_param_layout.addLayout(coord_layout)
            
        elif task_type in ["记录指定数量抽卡记录"]:
            count_layout = QHBoxLayout()
            count_layout.addWidget(QLabel("记录数量:"))
            self.count_input = QSpinBox()
            self.count_input.setRange(1, 100)
            count_layout.addWidget(self.count_input)
            self.specific_param_layout.addLayout(count_layout)
    
    def execute_task(self):
        """执行选定的任务"""
        task_type = TaskType(self.task_type_combo.currentText())
        param = None
        
        # 根据任务类型获取参数
        if task_type in [TaskType.CLICK_TEXT, TaskType.CLICK_IMG]:
            param = self.target_input.text()
        elif task_type == TaskType.CLICK_COORDINATE:
            param = (self.x_input.value(), self.y_input.value())
        elif task_type == TaskType.CLICK_COORDINATE_RELATIVE:
            param = (self.rx_input.value(), self.ry_input.value())
        elif task_type == TaskType.RECORD_HISTORY_FLEX:
            param = self.count_input.value()
            
        # 创建任务
        task = Task(
            task_type,
            param,
            timeout=self.timeout_input.value(),
            retry_count=self.retry_input.value(),
            pre_wait=self.pre_wait_input.value(),
            post_wait=self.post_wait_input.value(),
            b_reuse=getattr(self, 'reuse_check', QCheckBox()).isChecked(),
            b_recruitCheck=getattr(self, 'recruit_check', QCheckBox()).isChecked()
        )
        
        # 添加并执行任务
        self.game_manager.task_manager.add_task(task)
        self.game_manager.task_manager.execute_tasks()

    def execute_custom_task(self):
        self.game_manager.taskAdd_customTask_loop()

    def closeEvent(self, event):
        """关闭窗口时启用主界面的开始按钮"""
        if self.control_widget:
            self.control_widget.btn_start_pause.setEnabled(True)
            self.control_widget.enable_settings()
            delattr(self.control_widget, 'mini_panel')
        self.game_manager.task_manager.stop_tasks()
        event.accept()

class InputWithImageDialog(QDialog):
    def __init__(self, title, label, img, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        
        # 图片显示区域
        img_label = QLabel()
        h, w = img.shape[:2]
        """
        # 限制图片大小
        max_size = 400
        if h > max_size or w > max_size:
            scale = min(max_size/h, max_size/w)
            h, w = int(h*scale), int(w*scale)
        """
        
        # 转换numpy数组为QImage
        if len(img.shape) == 3:
            # 确保数据是C连续的
            img_c = np.ascontiguousarray(img)
            height, width, channel = img_c.shape
            bytes_per_line = 3 * width
            q_img = QImage(img_c.data, width, height, bytes_per_line, QImage.Format_RGB888)
        else:
            # 确保数据是C连续的
            img_c = np.ascontiguousarray(img)
            height, width = img_c.shape
            q_img = QImage(img_c.data, width, height, width, QImage.Format_Grayscale8)
            
        pixmap = QPixmap.fromImage(q_img)
        img_label.setPixmap(pixmap.scaled(w, h, Qt.KeepAspectRatio))
        layout.addWidget(img_label)
        
        # 输入区域
        layout.addWidget(QLabel(label))
        self.input_field = QLineEdit()
        layout.addWidget(self.input_field)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_input(self):
        return self.input_field.text()

    def set_text(self, text):
        self.input_field.setText(text)

# 主窗口类
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        g.mainWindow = self

        self.game_manager = GameManager()
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        
        # 设置游戏管理器的父对象
        self.game_manager.setParent(self)
        
        # 连接游戏管理器信号
        self.game_manager.log_message.connect(self.on_log_message)
        self.game_manager.step_updated.connect(self.on_step_updated)
        self.game_manager.data_updated.connect(self.on_data_updated)
        self.game_manager.macro_step_updated.connect(self.on_macro_step_updated)
        
        # 连接日志管理器信号
        log_manager.log_message.connect(self.on_log_message)
        
        self.initUI()
        self.loadSettings()
        self.setupMenuBar()

        self.img_extension = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        self.supported_extension = self.img_extension + [".json", ".txt"]

    def setupMenuBar(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        # 打开文件动作
        open_action = QAction('打开', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        # 保存文件动作
        save_action = QAction('保存', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        # 导出PNG动作
        export_action = QAction('导出PNG', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_png)
        file_menu.addAction(export_action)

    def initUI(self):
        """初始化UI布局"""
        self.setWindowTitle('明日方舟助手')
        self.resize(1280, 800)
        
        # 创建主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # 创建垂直分隔器
        main_splitter = QSplitter(Qt.Vertical)
        
        # 上部数据展示区
        data_display = QWidget()
        data_layout = QHBoxLayout(data_display)
        data_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 创建水平分隔器
        data_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧图表区域
        plot_area = QWidget()
        plot_layout = QVBoxLayout(plot_area)
        plot_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 图表
        self.plot_widget = PlotWidget()
        plot_layout.addWidget(self.plot_widget, 4)
        
        # 统计和操作区（水平布局）
        stats_ops = QWidget()
        stats_ops_layout = QHBoxLayout(stats_ops)
        
        # 统计信息（一个框内左右布局）
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        stats_layout = QHBoxLayout(stats_frame)
        
        # 全局统计
        global_layout = QVBoxLayout()
        global_layout.addWidget(QLabel("<b>全局统计</b>"))
        self.global_stats = QTextEdit()
        self.global_stats.setReadOnly(True)
        self.global_stats.setMaximumHeight(100)
        global_layout.addWidget(self.global_stats)
        stats_layout.addLayout(global_layout)
        
        # 选中区域统计
        selection_layout = QVBoxLayout()
        selection_layout.addWidget(QLabel("<b>选中区域统计</b>"))
        self.selection_stats = QTextEdit()
        self.selection_stats.setReadOnly(True)
        self.selection_stats.setMaximumHeight(100)
        selection_layout.addWidget(self.selection_stats)
        stats_layout.addLayout(selection_layout)
        
        # 图表操作区
        ops_frame = QFrame()
        ops_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        ops_layout = QHBoxLayout(ops_frame)
        
        # 左侧设置区
        settings_layout = QVBoxLayout()
        self.show_predict = QCheckBox("显示预测结果")
        settings_layout.addWidget(self.show_predict)
        
        predict_layout = QVBoxLayout()
        predict_range_layout = QHBoxLayout()
        predict_range_layout.addWidget(QLabel("预测后"))
        self.predict_range = QSpinBox()
        self.predict_range.setRange(1, 100)
        self.predict_range.setValue(10)
        predict_range_layout.addWidget(self.predict_range)
        predict_range_layout.addWidget(QLabel("个"))
        predict_layout.addLayout(predict_range_layout)
        
        self.probability_label = QLabel("下一次出六星概率：0%")
        predict_layout.addWidget(self.probability_label)
        settings_layout.addLayout(predict_layout)
        settings_layout.addStretch()
        
        # 右侧按钮区
        buttons_layout = QVBoxLayout()
        self.btn_peaks = QPushButton("波峰波谷分析")
        self.btn_patterns = QPushButton("相似模式查找")
        self.btn_save = QPushButton("保存右侧数据")
        buttons_layout.addWidget(self.btn_peaks)
        buttons_layout.addWidget(self.btn_patterns)
        buttons_layout.addWidget(self.btn_save)
        self.btn_peaks.clicked.connect(self.plot_widget.analyze_peaks)
        self.btn_patterns.clicked.connect(self.plot_widget.find_patterns)
        self.btn_save.clicked.connect(self.save_current_data)
        buttons_layout.addStretch()
        
        ops_layout.addLayout(settings_layout)
        ops_layout.addLayout(buttons_layout)
        
        stats_ops_layout.addWidget(stats_frame, 2)
        stats_ops_layout.addWidget(ops_frame, 1)
        
        plot_layout.addWidget(stats_ops, 1)
        
        # 将图表区域添加到水平分隔器
        plot_area_container = QWidget()
        plot_area_container.setLayout(plot_layout)
        data_splitter.addWidget(plot_area_container)
        
        # 右侧数据视图添加到水平分隔器
        self.data_view = DataViewWidget()
        self.data_view.setMinimumWidth(100)
        data_splitter.addWidget(self.data_view)

        # 设置分隔器的初始比例
        data_splitter.setStretchFactor(0, 4)  # 图表区域占80%
        data_splitter.setStretchFactor(1, 1)  # 数据视图占20%
        
        data_layout.addWidget(data_splitter)
        
        # 将数据展示区添加到垂直分隔器
        data_display_container = QWidget()
        data_display_container.setLayout(data_layout)
        main_splitter.addWidget(data_display_container)
        
        # 底部控制区域
        control_area = QWidget()
        control_layout = QHBoxLayout(control_area)
        control_layout.setContentsMargins(5, 5, 5, 5)
        control_layout.setSpacing(5)
        
        # 创建水平分隔器
        control_splitter = QSplitter(Qt.Horizontal)
        
        # 设置区（添加滚动区域）
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        self.settings_widget = SettingsWidget()
        settings_scroll.setWidget(self.settings_widget)
        settings_scroll.setMinimumWidth(200)
        control_splitter.addWidget(settings_scroll)
        
        # 控制台
        self.console = ConsoleWidget()
        control_splitter.addWidget(self.console)
        
        # 功能执行区（添加滚动区域）
        control_scroll = QScrollArea()
        control_scroll.setWidgetResizable(True)
        self.control_widget = ControlWidget()
        control_scroll.setWidget(self.control_widget)
        control_scroll.setMinimumWidth(200)
        control_splitter.addWidget(control_scroll)
        
        # 设置分隔器的初始大小比例
        control_splitter.setStretchFactor(0, 2)  # 设置区占20%
        control_splitter.setStretchFactor(1, 4)  # 控制台占40%
        control_splitter.setStretchFactor(2, 4)  # 功能执行区占40%
        
        control_layout.addWidget(control_splitter)
        
        # 将控制区域添加到主分隔器
        control_area_container = QWidget()
        control_area_container.setLayout(control_layout)
        main_splitter.addWidget(control_area_container)
        
        # 设置主分隔器的初始大小比例
        main_splitter.setStretchFactor(0, 3)  # 数据展示区占30%
        main_splitter.setStretchFactor(1, 7)  # 控制区域占70%
        
        main_layout.addWidget(main_splitter)
        
        # 设置窗口最小尺寸
        self.setMinimumSize(1024, 768)
    
    def loadSettings(self):
        """加载所有设置"""
        g.config = log_manager.load_config()
        self.settings_widget.loadSettings()
        self.plot_widget.loadSettings()
        
        # 应用自动保存设置
        config = g.config
        data_settings = config.get('data', {})
        if data_settings.get('auto_save', True):
            interval = data_settings.get('auto_save_interval', 5) * 60 * 1000  # 转换为毫秒
            self.auto_save_timer.start(interval)
    
    def auto_save(self):
        """自动保存数据"""
        try:
            if data_manager.save_data():
                log_manager.debug("数据自动保存成功")
            else:
                log_manager.warning("数据自动保存失败")
        except Exception as e:
            error_record(e)
            log_manager.error(f"自动保存时发生错误: {str(e)}")
    
    def closeEvent(self, event):
        """关闭窗口时的处理"""
        try:
            # 停止自动保存定时器
            self.auto_save_timer.stop()
            
            # 保存数据
            if data_manager.save_data():
                log_manager.info("数据已保存")
            
            # 保存设置
            self.settings_widget.save_settings()

            # 清理adb连接
            self.game_manager.break_connection()
            
        except Exception as e:
            error_record(e)
            log_manager.error(f"关闭窗口时发生错误: {str(e)}")
        
        event.accept()

    @Slot()
    def open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开数据文件", "", "文本文件 (*.txt)")
        if file_path:
            if data_manager.load_data(file_path):
                self.plot_widget.set_data(data_manager.data)
                self.data_view.set_data(data_manager.data, data_manager.real_data)
                log_manager.info(f"成功加载文件：{file_path}")
            else:
                log_manager.error(f"加载文件失败：{file_path}")

    @Slot()
    def save_file(self):
        """保存文件"""
        if not data_manager.file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存数据文件", "", "文本文件 (*.txt)")
            if not file_path:
                return False
            data_manager.file_path = file_path
        
        if data_manager.save_data():
            log_manager.info(f"成功保存文件：{data_manager.file_path}")
            return True
        else:
            log_manager.error(f"保存文件失败：{data_manager.file_path}")
            return False

    @Slot()
    def export_png(self):
        """导出PNG图片"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出PNG", "", "PNG图片 (*.png)")
        if file_path:
            if data_manager.export_png(file_path):
                log_manager.info(f"成功导出PNG：{file_path}")
            else:
                log_manager.error(f"导出PNG失败：{file_path}")

    def handle_missing_tag(self, img):
        """处理找不到tag的情况"""
        while True:
            dialog = InputWithImageDialog(
                "输入标签",
                "请输入5个tag，用逗号分隔：",
                img,
                self
            )
            if dialog.exec_() != QDialog.Accepted:
                return None
                
            text = dialog.get_input()
            l_input = [t.strip() for t in text.split(",") if t.strip()]
            if len(l_input) != 5:
                QMessageBox.warning(self, "错误", "请输入5个tag")
                continue
                
            # 验证tag是否合法
            invalid_tags = [t for t in l_input if t not in DATA.l_tag]
            if invalid_tags != []:
                QMessageBox.warning(self, "错误", f"以下tag不合法：{invalid_tags}")
                continue
                
            return l_input

    def handle_missing_agent(self, img):
        """处理找不到干员的情况"""
        while True:
            dialog = InputWithImageDialog(
                "输入干员",
                "请输入干员中文名称：",
                img,
                self
            )
            if dialog.exec_() != QDialog.Accepted:
                return None
                
            text = dialog.get_input().strip()
            if not text:
                QMessageBox.warning(self, "错误", "请输入干员名称")
                continue
                
            # 验证干员是否存在
            if text not in DATA.l_agent:
                QMessageBox.warning(self, "错误", "干员不存在")
                continue
                
            return text

    def handle_missing_record(self, errorTuple):
        """处理无法识别记录的情况"""
        img, l_result = errorTuple
        while True:
            dialog = InputWithImageDialog(
                "输入干员",
                "无法识别记录，请输入所有干员中文名称，空格分隔：",
                img,
                self
            )
            dialog.set_text(" ".join(l_result))
            if dialog.exec_() != QDialog.Accepted:
                return None
                
            text = dialog.get_input().strip()
            if not text:
                QMessageBox.warning(self, "错误", "请输入所有干员名称")
                continue
                
            # 验证干员是否存在
            invalid_agent = [agent for agent in text.split(" ") if agent not in DATA.l_agent]
            if invalid_agent:
                QMessageBox.warning(self, "错误", f"{invalid_agent} 不存在")
                continue
                
            return text

    def on_step_updated(self, current_step: str, next_step: str):
        """处理步骤更新"""
        if hasattr(self, "console"):
            self.console.update_step(current_step, next_step)
    
    def on_macro_step_updated(self, macro_step, level):
        """处理宏观步骤更新"""
        if hasattr(self, "console"):
            self.console.append_macro_step(macro_step, level)

    def on_log_message(self, message: str, level: str = "INFO"):
        """处理日志消息"""
        if hasattr(self, "console"):
            self.console.append_message(message, level)

    def on_user_changed_data(self, info_data: list):
        """用户应用数据的修改"""
        data_manager.set_data("\n".join(info_data))
        self.plot_widget.set_data(data_manager.data)
        self.data_view.set_data(numeric_data=data_manager.data)

    def on_data_updated(self):
        self.plot_widget.set_data(data_manager.data)
        self.data_view.set_data(numeric_data=data_manager.data, info_data=data_manager.real_data)
    
    def save_current_data(self):
        """保存核心数据"""
        try:
            config = g.config
            data_settings = config.get('data', {})
            file_path = data_settings.get('file_path', '#record.txt')
            
            if data_manager.save_data(file_path):
                log_manager.info(f"数据已保存到 {file_path}")
            else:
                log_manager.error("保存数据失败")
        except Exception as e:
            error_record(e)
            QMessageBox.warning(self, "错误", f"保存失败：{str(e)}")
            log_manager.error(f"保存数据时发生错误：{str(e)}")

    def dragEnterEvent(self, event):
        """拖入事件处理，支持目录、图片、JSON和TXT文件"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                # 检查是否为目录
                if os.path.isdir(file_path):
                    event.acceptProposedAction()
                    return
                # 检查文件扩展名
                ext = os.path.splitext(file_path)[1].lower()
                if ext in self.supported_extension:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        """放下事件处理，支持多种文件类型和目录"""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            try:
                if os.path.isdir(file_path):
                    self.append_data_from_dir(file_path)
                    self.statusBar().showMessage(f"成功导入目录: {file_path}", 3000)
                else:
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in self.img_extension:
                        self.append_data_from_img(file_path)
                        self.statusBar().showMessage(f"成功导入图片: {file_path}", 3000)
                    elif ext == '.json':
                        self.append_data_from_json(file_path)
                        self.statusBar().showMessage(f"成功导入JSON文件: {file_path}", 3000)
                    elif ext == '.txt':
                        self.append_data_from_txt(file_path)
                        self.statusBar().showMessage(f"成功导入TXT文件: {file_path}", 3000)
            except Exception as e:
                self.statusBar().showMessage(f"导入失败: {str(e)}", 3000)
                error_record(e)
                log_manager.error(f"文件处理失败 {file_path}: {e}", e)
        event.acceptProposedAction()

    def append_data_from_json(self, jsonPath):
        log_manager.debug(f"从json文件 {jsonPath} 中录入")
        with open(jsonPath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        l_agents = []
        for entry in data['data']['list']:
            for char in entry['chars']:
                l_agents.append(char['name'])
        data_manager.update_data(l_agents[::-1])
        self.plot_widget.set_data(data_manager.data)
        self.data_view.set_data(
            data_manager.data,
            data_manager.real_data
        )

    def append_data_from_txt(self, txtPath):
        log_manager.debug(f"从文本文件 {txtPath} 中录入")
        if data_manager.load_data(txtPath):
            self.plot_widget.set_data(data_manager.data)
            self.data_view.set_data(
                data_manager.data,
                data_manager.real_data
            )
        else:
            raise RuntimeError(f"文件 {txtPath} 解析失败")

    def append_data_from_img(self, imgPath, refresh = False):
        log_manager.debug(f"从图片 {imgPath} 中录入")
        file_ext = os.path.splitext(imgPath)[1].lower()
        if file_ext in self.img_extension:
            img = cv.imread(imgPath)
        else:
            raise RuntimeError(f"无法将 {imgPath} 读取为图片")
        if img is None:
            raise RuntimeError(f"无法将 {imgPath} 读取为图片，可能是路径有中文？")
        # 三种识别挨个判定正确的
        l_tag = tool.getTag(img)
        if len(l_tag) == 5:
            data_manager.update_data("!".join(l_tag))
        else:
            agent = tool.getAgent(img)
            if agent is not None:
                data_manager.update_data(agent)
            else:
                l_history, b_flag = tool.getHistory(img)
                if b_flag:
                    data_manager.update_data("\n".join(l_history))
                else:
                    log_manager.debug(f"{imgPath}识别结果: tag={l_tag}, 干员={agent}, 历史={l_history}, 标志={b_flag}")
                    raise RuntimeError(f"无法识别图像 {imgPath}")
        if refresh:
            self.plot_widget.set_data(data_manager.data)
            self.data_view.set_data(
                data_manager.data,
                data_manager.real_data
            )

    def append_data_from_dir(self, dirPath):
        log_manager.debug(f"从目录 {dirPath} 中录入")

        # 收集所有文件及其创建时间
        l_files = []
        # 是否所有文件都是纯数字命名
        all_numeric = True

        # 遍历文件夹中的所有文件
        for root, dirs, files in os.walk(dirPath):
            for file in files:
                # 获取文件完整路径
                #file_path = root.replace("/", "\\") + "\\" + file
                file_path = os.path.join(root, file)

                # 检查文件扩展名是否为图像文件
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext not in self.supported_extension:
                    continue

                try:
                    # 获取文件修改时间
                    creation_time = os.path.getmtime(file_path)
                except Exception as e:
                    error_record(e)
                    print(f"无法获取文件 {file_path} 的修改时间: {e}")
                    continue

                l_files.append((file_path, creation_time, file_ext))

                # 判断文件名是否纯数字（无扩展名部分）
                base_name = os.path.splitext(file)[0]
                if not base_name.isdigit():
                    all_numeric = False

        # 根据 all_numeric 决定排序键
        if all_numeric and l_files:
            l_files.sort(key=lambda t: int(os.path.splitext(os.path.basename(t[0]))[0]))
        else:
            # 按创建时间排序（从老到新）
            l_files.sort(key=lambda t: t[1])

        l_error = []
        for file_path, _, file_ext in l_files:
            try:
                if file_ext in self.img_extension:
                    self.append_data_from_img(file_path, refresh = False)
                elif file_ext == ".txt":
                    self.append_data_from_txt(file_path)
                elif file_ext == ".json":
                    self.append_data_from_json(file_path)
                else:
                    raise RuntimeError("shouldn't be here")
            except Exception as e:
                error_record(e)
                l_error.append(file_path)

        self.plot_widget.set_data(data_manager.data)
        self.data_view.set_data(
            data_manager.data,
            data_manager.real_data
        )
        if l_error:
            raise RuntimeError("以下文件在载入时出错：\n" + "\n".join(l_error))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 
