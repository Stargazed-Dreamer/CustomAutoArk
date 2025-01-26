import sys
import os
import platform
import matplotlib
matplotlib.use('Qt5Agg')

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QComboBox, 
                             QSpinBox, QCheckBox, QTabWidget, QTextEdit,
                             QFileDialog, QMessageBox, QScrollArea, QFrame,
                             QSplitter, QLineEdit, QToolBar, QPlainTextEdit,
                             QInputDialog, QGroupBox)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QPainter, QColor, QAction, QFont, QTextCursor, QTextCharFormat
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import json
from datetime import datetime
import logging

from utils.plot_utils import (create_smooth_line, create_zoom_animation,
                            highlight_similar_points, add_annotations,
                            create_gradient_line, add_grid)
from utils.data_manager import DataManager
from game_manager import GameManager
from log import log_manager

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

# 工具组件
class ConsoleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)  # 减小组件间距
        
        # 左侧控制台输出
        console_container = QWidget()
        console_container.setMinimumWidth(100)  # 最小宽度
        console_container.setMaximumWidth(400)  # 最大宽度
        console_layout = QVBoxLayout(console_container)
        console_layout.setContentsMargins(0, 0, 0, 0)
        
        self.console_text = QTextEdit()
        self.console_text.setReadOnly(True)
        font = QFont('Microsoft YaHei', 9)
        self.console_text.setFont(font)
        console_layout.addWidget(self.console_text)
        
        # 右侧状态显示
        status_container = QWidget()
        status_container.setMinimumWidth(100)  # 最小宽度
        status_container.setMaximumWidth(400)  # 最大宽度
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setFont(font)
        status_layout.addWidget(self.status_text)
        
        # 添加到布局（先左后右）
        layout.addWidget(console_container, 1)  # 设置为相等的伸缩比例
        layout.addWidget(status_container, 1)  # 设置为相等的伸缩比例
        
        # 初始化颜色格式
        self.time_format = QTextCharFormat()
        self.time_format.setForeground(QColor("#666666"))
        
        self.step_format = QTextCharFormat()
        self.step_format.setForeground(QColor("#2196F3"))
        
        self.next_step_format = QTextCharFormat()
        self.next_step_format.setForeground(QColor("#4CAF50"))
        
        self.count_format = QTextCharFormat()
        self.count_format.setForeground(QColor("#FF9800"))
    
    def append_status(self, message: str, message_type: str = "normal"):
        cursor = self.status_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # 添加时间戳
        time_str = f"[{datetime.now().strftime('%H:%M:%S')}]"
        cursor.insertText(time_str, self.time_format)
        
        # 根据消息类型设置颜色
        if message_type == "step":
            cursor.insertText(message + "\n", self.step_format)
        elif message_type == "next_step":
            cursor.insertText(message + "\n", self.next_step_format)
        elif message_type == "count":
            cursor.insertText(message + "\n", self.count_format)
        else:
            cursor.insertText(message + "\n")
        
        self.status_text.setTextCursor(cursor)
    
    def append_date_separator(self):
        cursor = self.status_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # 添加日期分隔符
        date_str = f"\n--{datetime.now().strftime('%Y.%m.%d')}--\n"
        cursor.insertText(date_str)
        
        self.status_text.setTextCursor(cursor)
    
    def append_message(self, message: str):
        self.console_text.append(message)
    
    def update_current_next_step(self, current: str, next: str = None):
        cursor = self.status_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        cursor.insertText("\n正在进行：", self.step_format)
        cursor.insertText(current, self.step_format)
        
        if next:
            cursor.insertText("\n即将进行：", self.next_step_format)
            cursor.insertText(next, self.next_step_format)
        
        cursor.insertText("\n")
        self.status_text.setTextCursor(cursor)

class StatusBarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        
        # 当前模式
        self.mode_label = QLabel("当前模式：暂停")
        layout.addWidget(self.mode_label)
        
        # 执行步骤
        self.step_label = QLabel("执行步骤：-")
        layout.addWidget(self.step_label)
        
        # 抽卡计数
        self.gacha_count = QLabel("已执行0次抽卡")
        layout.addWidget(self.gacha_count)
        
        # 公招计数
        self.recruit_count = QLabel("已执行0次公招")
        layout.addWidget(self.recruit_count)
        
        layout.addStretch()
    
    def update_mode(self, mode: str):
        self.mode_label.setText(f"当前模式：{mode}")
    
    def update_step(self, current: str, next: str = None):
        text = f"执行步骤：{current}"
        if next:
            text += f" -> {next}"
        self.step_label.setText(text)
    
    def update_gacha_count(self, count: int):
        self.gacha_count.setText(f"已执行{count}次抽卡")
    
    def update_recruit_count(self, count: int):
        self.recruit_count.setText(f"已执行{count}次公招")

# 数据展示组件
class PlotWidget(QWidget):
    # 自定义信号
    data_selected = Signal(list)  # 数据选中信号
    data_modified = Signal(list)  # 数据修改信号
    hover_point_changed = Signal(int)  # 悬停点变化信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.setup_plot()
        self.setup_interactions()

        # 数据相关
        self.data = []
        self.selected_indices = []
        self.hover_index = -1
        
        # 交互状态
        self.is_selecting = False
        self.is_panning = False
        self.selection_start = None
        self.pan_start = None
        
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建画布
        self.figure = Figure(dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
    def setup_plot(self):
        self.ax = self.figure.add_subplot(111)
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.line = None
        self.scatter = None
        self.selection_rect = None
        self.hover_annotation = None
        
    def setup_interactions(self):
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('key_press_event', self.on_key_press)
        
    def set_data(self, data):
        self.data = data
        self._update_plot()

    def loadSettings(self):
        """加载图表设置"""
        if not hasattr(self, 'ax'):
            return
            
        config = log_manager.load_config()
        plot_settings = config.get('plot', {})
        
        # 更新网格显示
        self.ax.grid(plot_settings.get('show_grid', True))
        
        # 更新点显示和大小
        if self.scatter is not None:
            self.scatter.set_visible(plot_settings.get('show_points', True))
            self.scatter.set_sizes([plot_settings.get('point_size', 3)])
        
        # 更新线宽
        if self.line is not None:
            self.line.set_linewidth(plot_settings.get('line_width', 1))
        
        # 刷新画布
        self.canvas.draw()
    
    def saveSettings(self):
        """保存图表设置"""
        if not hasattr(self, 'ax'):
            return
            
        config = log_manager.load_config()
        
        plot_settings = {
            'show_grid': bool(self.ax.get_gridlines()),
            'show_points': bool(self.scatter.get_visible()) if self.scatter is not None else True,
            'line_width': float(self.line.get_linewidth()) if self.line is not None else 1,
            'point_size': float(self.scatter.get_sizes()[0]) if self.scatter is not None else 3,
            'smooth_factor': 0.5  # 默认平滑因子
        }
        
        config['plot'] = plot_settings
        log_manager.save_config(config)

    def _update_plot(self):
        self.ax.clear()
        if not self.data:
            return
        
        x = list(range(len(self.data)))
        
        # 绘制主线
        self.line, = self.ax.plot(x, self.data, '-', lw=1)
        
        # 绘制数据点
        if self.scatter:
            self.scatter.remove()
        self.scatter = self.ax.scatter(x, self.data, s=20)
        
        # 绘制网格
        self.ax.grid(True, linestyle='--', alpha=0.7)
        
        # 更新画布
        self.canvas.draw()
    
    def on_mouse_press(self, event):
        if event.inaxes != self.ax:
            return
            
        if event.button == 1:  # 左键
            self.is_selecting = True
            self.selection_start = (event.xdata, event.ydata)
            if self.selection_rect:
                self.selection_rect.remove()
                self.selection_rect = None
        elif event.button == 3:  # 右键
            self.is_panning = True
            self.pan_start = (event.xdata, event.ydata)
            self.ax.set_cursor(plt.Cursor(self.ax, useblit=True, color='red', linewidth=1))
        
    def on_mouse_release(self, event):
        if event.inaxes != self.ax:
            return
        
        if event.button == 1 and self.is_selecting:  # 左键释放
            self.is_selecting = False
            if self.selection_start and event.xdata:
                x_start = min(self.selection_start[0], event.xdata)
                x_end = max(self.selection_start[0], event.xdata)
                selected = [i for i, x in enumerate(range(len(self.data)))
                          if x_start <= x <= x_end]
                self.selected_indices = selected
                self.data_selected.emit(selected)
        
        elif event.button == 3 and self.is_panning:  # 右键释放
            self.is_panning = False
            self.ax.set_cursor(None)
        
        self.canvas.draw()
    
    def on_mouse_move(self, event):
        if event.inaxes != self.ax:
            return
            
        if self.is_selecting and self.selection_start:
            # 更新选择框
            if self.selection_rect:
                self.selection_rect.remove()
            width = event.xdata - self.selection_start[0]
            height = self.ax.get_ylim()[1] - self.ax.get_ylim()[0]
            self.selection_rect = plt.Rectangle(
                (min(self.selection_start[0], event.xdata), self.ax.get_ylim()[0]),
                abs(width), height, alpha=0.2, color='yellow')
            self.ax.add_patch(self.selection_rect)
            
        elif self.is_panning and self.pan_start:
            # 平移视图
            dx = self.pan_start[0] - event.xdata
            dy = self.pan_start[1] - event.ydata
            self.ax.set_xlim(self.ax.get_xlim() + dx)
            self.ax.set_ylim(self.ax.get_ylim() + dy)
        
        else:
            # 处理悬停
            if event.xdata is not None:
                index = int(round(event.xdata))
                if 0 <= index < len(self.data):
                    if index != self.hover_index:
                        self.hover_index = index
                        self.hover_point_changed.emit(index)
                        if self.hover_annotation:
                            self.hover_annotation.remove()
                        self.hover_annotation = self.ax.annotate(
                            f'({index}, {self.data[index]:.2f})',
                            (index, self.data[index]),
                            xytext=(10, 10), textcoords='offset points',
                            bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                            arrowprops=dict(arrowstyle='->'))
        
        self.canvas.draw()

    def on_scroll(self, event):
        if event.inaxes != self.ax:
            return
            
        # 获取当前视图范围
        cur_xlim = self.ax.get_xlim()
        #cur_ylim = self.ax.get_ylim()
        
        # 计算缩放中心（鼠标位置）
        x_data = event.xdata
        #y_data = event.ydata
        
        # 设置缩放因子
        base_scale = 1.1
        if event.button == 'up':
            scale_factor = 1/base_scale
        else:
            scale_factor = base_scale
        
        # 计算新的视图范围
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        #new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        
        # 设置新的视图范围（保持鼠标位置不变）
        rel_x = (x_data - cur_xlim[0]) / (cur_xlim[1] - cur_xlim[0])
        #rel_y = (y_data - cur_ylim[0]) / (cur_ylim[1] - cur_ylim[0])
        
        self.ax.set_xlim([x_data - rel_x * new_width,
                         x_data + (1-rel_x) * new_width])
        #self.ax.set_ylim([y_data - rel_y * new_height,
        #                 y_data + (1-rel_y) * new_height])
        
        self.canvas.draw()
    
    def on_key_press(self, event):
        if event.key == 'g':
            self.ax.grid(not self.ax.get_gridlines())
            self.canvas.draw()
        elif event.key == 'p':
            self.scatter.set_visible(not self.scatter.get_visible())
            self.canvas.draw()
    
    def toggle_grid(self):
        self.ax.grid(not self.ax.get_gridlines())
        self.canvas.draw()
    
    def toggle_points(self):
        self.scatter.set_visible(not self.scatter.get_visible())
        self.canvas.draw()

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
        self.setup_actions()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 数值数据页
        self.numeric_editor = QPlainTextEdit()
        self.numeric_editor.setFont(QFont('Consolas', 9))
        self.numeric_editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.numeric_editor.textChanged.connect(self.on_text_changed)
        self.tab_widget.addTab(self.numeric_editor, "数值数据")
        
        # 干员/tag数据页
        self.info_editor = QPlainTextEdit()
        self.info_editor.setFont(QFont('Microsoft YaHei', 9))
        self.info_editor.setReadOnly(True)
        self.tab_widget.addTab(self.info_editor, "干员/Tag信息")
        
        layout.addWidget(self.tab_widget)
    
    def setup_actions(self):
        pass  # 移除所有动作，因为已经移到图表操作区
    
    def set_data(self, data: list, info: str = None):
        # 设置数值数据
        text = "\n".join(str(x) for x in data)
        self.numeric_editor.setPlainText(text)
        
        # 设置信息数据
        if info:
            self.info_editor.setPlainText(info)
    
    def get_data(self) -> list:
        try:
            text = self.numeric_editor.toPlainText()
            return [float(x) for x in text.split('\n') if x.strip()]
        except:
            return []
    
    @Slot()
    def on_text_changed(self):
        data = self.get_data()
        self.data_changed.emit(data)
    
    @Slot()
    def find_peaks(self):
        data = self.get_data()
        if not data:
            return
            
        threshold, ok = QInputDialog.getDouble(
            self, "波峰分析", "请输入阈值（0-1之间）：",
            value=0.5, min=0.0, max=1.0, decimals=2)
            
        if ok:
            # 使用scipy的find_peaks函数
            from scipy.signal import find_peaks
            peaks, _ = find_peaks(data, height=max(data)*threshold)
            valleys, _ = find_peaks([-x for x in data], height=max(data)*threshold)
            
            # 在info_editor中显示结果
            result = "波峰位置：\n"
            for i, peak in enumerate(peaks):
                result += f"{peak}: {data[peak]:.2f}\n"
            
            result += "\n波谷位置：\n"
            for i, valley in enumerate(valleys):
                result += f"{valley}: {data[valley]:.2f}\n"
                
            self.info_editor.setPlainText(result)
    
    @Slot()
    def find_patterns(self):
        data = self.get_data()
        if not data:
            return
            
        # 获取选中的数据作为模式
        if not hasattr(self, 'selected_indices') or not self.selected_indices:
            QMessageBox.warning(self, "错误", "请先在图表中选择一段数据作为模式！")
            return
            
        threshold, ok = QInputDialog.getDouble(
            self, "模式查找", "请输入相似度阈值（0-1之间）：",
            value=0.8, min=0.0, max=1.0, decimals=2)
            
        if ok:
            pattern = [data[i] for i in self.selected_indices]
            pattern_len = len(pattern)
            
            # 计算相似度（使用相关系数）
            similar_positions = []
            for i in range(len(data) - pattern_len + 1):
                segment = data[i:i+pattern_len]
                correlation = np.corrcoef(pattern, segment)[0, 1]
                if correlation > threshold:
                    similar_positions.append((i, correlation))
            
            # 在info_editor中显示结果
            result = "相似模式位置：\n"
            for pos, corr in similar_positions:
                result += f"位置 {pos}: 相似度 {corr:.2f}\n"
                
            self.info_editor.setPlainText(result)

    def plot_data(self):
        """绘制数据"""
        if not hasattr(self, 'canvas'):
            return
        
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # 设置更小的边距
        self.figure.subplots_adjust(left=0.05, right=0.98, top=0.95, bottom=0.05)
        
        # 绘制数据
        data = self.get_data()
        if data:
            ax.plot(data, '-o', markersize=3)
            
            # 如果有选中的点，高亮显示
            if hasattr(self, 'selected_indices') and self.selected_indices:
                selected_x = self.selected_indices
                selected_y = [data[i] for i in self.selected_indices]
                ax.plot(selected_x, selected_y, 'ro', markersize=5)
        
        # 设置网格
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # 刷新画布
        self.canvas.draw()

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
        config = log_manager.load_config()
        
        # 更新配置
        config['simulator'] = simulator_settings
        config['data'] = data_settings
        
        # 保存配置
        if log_manager.save_config(config):
            self.parent().parent().parent().statusBar().showMessage("设置已保存", 3000)
        else:
            self.parent().parent().parent().statusBar().showMessage("设置保存失败", 3000)
    
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
        config = log_manager.load_config()
        
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
        self.data_manager = DataManager()
        self.game_manager = GameManager()
        
        # 连接信号
        self.game_manager.device_connected.connect(self.on_device_connection_changed)
        self.game_manager.operation_started.connect(self.on_operation_started)
        self.game_manager.operation_stopped.connect(self.on_operation_stopped)
        self.game_manager.operation_paused.connect(self.on_operation_paused)
        self.game_manager.operation_resumed.connect(self.on_operation_resumed)
        self.game_manager.log_message.connect(self.on_log_message)
        
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 设备连接区域
        device_group = QFrame()
        device_group.setFrameStyle(QFrame.Panel | QFrame.Raised)
        device_layout = QVBoxLayout(device_group)
        
        # 连接按钮
        self.connect_btn = QPushButton("连接设备")
        self.connect_btn.clicked.connect(self.on_connect_clicked)
        device_layout.addWidget(self.connect_btn)
        
        layout.addWidget(device_group)
        
        # 单次操作组（上）
        single_group = QFrame()
        single_group.setFrameStyle(QFrame.Panel | QFrame.Raised)
        single_layout = QVBoxLayout(single_group)
        
        single_layout.addWidget(QLabel("<b>单次操作</b>"))
        
        self.btn_gacha = QPushButton("抽卡一次")
        self.btn_recruit = QPushButton("公招一次")
        self.btn_record = QPushButton("记录画面")
        
        # 初始状态禁用，需要连接设备后启用
        self.btn_gacha.setEnabled(False)
        self.btn_recruit.setEnabled(False)
        self.btn_record.setEnabled(False)
        
        single_layout.addWidget(self.btn_gacha)
        single_layout.addWidget(self.btn_recruit)
        single_layout.addWidget(self.btn_record)
        
        # 循环操作组（下）
        loop_group = QFrame()
        loop_group.setFrameStyle(QFrame.Panel | QFrame.Raised)
        loop_layout = QVBoxLayout(loop_group)
        
        loop_layout.addWidget(QLabel("<b>循环操作</b>"))
        
        # 模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["干员寻访", "公开招募", "自动规划"])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.mode_combo.setEnabled(False)  # 初始禁用
        mode_layout.addWidget(self.mode_combo)
        loop_layout.addLayout(mode_layout)
        
        # 参数设置
        param_layout = QHBoxLayout()
        self.param_label = QLabel("选择卡池:")
        param_layout.addWidget(self.param_label)
        self.param_spin = QSpinBox()
        self.param_spin.setRange(1, 10)
        self.param_spin.setEnabled(False)  # 初始禁用
        param_layout.addWidget(self.param_spin)
        loop_layout.addLayout(param_layout)
        
        # 启停控制
        control_layout = QHBoxLayout()
        
        # 开始/暂停按钮
        self.btn_start_pause = QPushButton("开始")
        font = self.btn_start_pause.font()
        font.setPointSize(14)
        self.btn_start_pause.setFont(font)
        self.btn_start_pause.setMinimumHeight(50)
        self.btn_start_pause.clicked.connect(self.toggle_operation)
        self.btn_start_pause.setEnabled(False)  # 初始禁用
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
        
        # 连接按钮事件
        self.btn_gacha.clicked.connect(self.game_manager.do_single_gacha)
        self.btn_recruit.clicked.connect(self.game_manager.do_single_recruit)
        self.btn_record.clicked.connect(self.game_manager.do_record_screen)
        
        # 添加到主布局
        layout.addWidget(single_group)
        layout.addWidget(loop_group)
        layout.addStretch()
    
    def on_mode_changed(self, index):
        # 更新参数提示
        if index == 0:  # 干员寻访
            self.param_label.setText("选择卡池:")
        elif index == 1:  # 公开招募
            self.param_label.setText("选择栏位:")
        else:  # 自动规划
            self.param_label.setText("目标6星:")
    
    def on_connect_clicked(self):
        adb_path = self.parent().parent().parent().settings_widget.adb_path.text().strip()
        if not adb_path:
            QMessageBox.warning(self, "警告", "请先设置ADB路径")
            return
            
        # 初始化Core并连接设备
        self.game_manager.connect_device(adb_path)
    
    def on_device_connection_changed(self, connected: bool):
        """设备连接状态改变时的处理"""
        self.enable_controls(connected)
        if connected:
            self.connect_btn.setText("已连接")
            self.connect_btn.setEnabled(False)
        else:
            self.connect_btn.setText("连接设备")
            self.connect_btn.setEnabled(True)
    
    def enable_controls(self, enabled: bool):
        """启用或禁用所有控件"""
        self.btn_gacha.setEnabled(enabled)
        self.btn_recruit.setEnabled(enabled)
        self.btn_record.setEnabled(enabled)
        self.mode_combo.setEnabled(enabled)
        self.param_spin.setEnabled(enabled)
        self.btn_start_pause.setEnabled(enabled)
    
    def on_operation_started(self):
        """操作开始时的处理"""
        self.btn_start_pause.setText("暂停")
        self.btn_start_pause.setStyleSheet("background-color: #ff9800;")  # 橙色
        self.btn_resume.hide()
        self.btn_reset.hide()
    
    def on_operation_stopped(self):
        """操作停止时的处理"""
        self.btn_start_pause.setText("开始")
        self.btn_start_pause.setStyleSheet("")
        self.btn_resume.hide()
        self.btn_reset.hide()
    
    def on_operation_paused(self):
        """操作暂停时的处理"""
        self.btn_start_pause.hide()
        self.btn_resume.show()
        self.btn_reset.show()
        self.btn_resume.setStyleSheet("background-color: #4caf50;")  # 绿色
        self.btn_reset.setStyleSheet("background-color: #f44336;")   # 红色
    
    def on_operation_resumed(self):
        """操作恢复时的处理"""
        self.btn_resume.hide()
        self.btn_reset.hide()
        self.btn_start_pause.show()
        self.btn_start_pause.setText("暂停")
        self.btn_start_pause.setStyleSheet("background-color: #ff9800;")  # 橙色
    
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
                param = self.param_spin.value()
                self.game_manager.start_operation(mode, param)
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
    
    def on_log_message(self, message: str):
        """处理日志消息"""
        # 如果父窗口有console，则发送日志
        if hasattr(self.parent().parent().parent(), "console"):
            self.parent().parent().parent().console.append_message(message)

# 主窗口类
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data_manager = DataManager()
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        
        # 初始化UI
        self.initUI()
        self.setupMenuBar()
        self.setupStatusBar()
        self.setupStepPanel()
        self.setupConnections()
        
        # 加载设置
        self.loadSettings()
        
        # 连接游戏管理器的信号
        self.game_manager = GameManager()
        self.game_manager.step_updated.connect(self.update_step)
        self.game_manager.log_message.connect(self.console.append_message)
        
        # 连接日志管理器的信号
        log_manager.log_message.connect(self.console.append_message)
        log_manager.step_message.connect(self.append_step)
    
    def initUI(self):
        """初始化UI布局"""
        self.setWindowTitle('明日方舟助手')
        self.resize(1280, 800)
        
        # 创建主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # 上部数据展示区
        data_display = QWidget()
        data_layout = QHBoxLayout(data_display)
        
        # 左侧图表区域
        plot_area = QWidget()
        plot_layout = QVBoxLayout(plot_area)
        
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
        self.show_grid = QCheckBox("显示网格")
        self.show_grid.setChecked(True)
        self.show_points = QCheckBox("显示数据点")
        self.show_points.setChecked(True)
        self.show_predict = QCheckBox("显示预测结果")
        settings_layout.addWidget(self.show_grid)
        settings_layout.addWidget(self.show_points)
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
        self.btn_save = QPushButton("保存本页数据")
        buttons_layout.addWidget(self.btn_peaks)
        buttons_layout.addWidget(self.btn_patterns)
        buttons_layout.addWidget(self.btn_save)
        buttons_layout.addStretch()
        
        ops_layout.addLayout(settings_layout)
        ops_layout.addLayout(buttons_layout)
        
        stats_ops_layout.addWidget(stats_frame, 2)
        stats_ops_layout.addWidget(ops_frame, 1)
        
        plot_layout.addWidget(stats_ops, 1)
        
        # 右侧数据视图
        self.data_view = DataViewWidget()
        self.data_view.setMinimumWidth(100)  # 设置最小宽度
        self.data_view.setMaximumWidth(250)  # 设置最大宽度
        
        data_layout.addWidget(plot_area, 4)
        data_layout.addWidget(self.data_view, 1)
        
        # 底部控制区域
        control_area = QWidget()
        control_layout = QHBoxLayout(control_area)
        control_layout.setContentsMargins(5, 5, 5, 5)
        control_layout.setSpacing(5)  # 减小组件间距
        
        # 设置区
        self.settings_widget = SettingsWidget()
        self.settings_widget.setMinimumWidth(250)  # 设置最小宽度
        
        # 控制台
        self.console = ConsoleWidget()
        
        # 功能执行区
        self.control_widget = ControlWidget()
        self.control_widget.setMinimumWidth(200)  # 设置最小宽度
        self.control_widget.setMaximumWidth(250)  # 设置最大宽度
        
        # 使用伸缩因子控制宽度分配
        control_layout.addWidget(self.settings_widget, 2)  # 设置区占更多空间
        control_layout.addWidget(self.console, 3)         # 控制台占中等空间
        control_layout.addWidget(self.control_widget, 2)  # 功能区占更多空间
        
        main_layout.addWidget(data_display, 7)
        main_layout.addWidget(control_area, 3)
        
        # 设置窗口最小尺寸
        self.setMinimumSize(1024, 768)
    
    def setupMenuBar(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        open_action = QAction('打开', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction('保存', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        export_action = QAction('导出PNG', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_png)
        file_menu.addAction(export_action)
    
    def setupStatusBar(self):
        """设置状态栏"""
        self.statusBar().showMessage("就绪")
    
    def setupStepPanel(self):
        """设置步骤面板"""
        self.step_panel = QTextEdit()
        self.step_panel.setReadOnly(True)
        self.step_panel.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                font-family: Arial;
                font-size: 12px;
            }
        """)
    
    def update_step(self, current_step: str, next_step: str = None):
        """更新步骤信息"""
        if not hasattr(self, 'step_panel'):
            return
        
        if next_step:
            text = f"当前步骤: {current_step}\n即将执行: {next_step}"
        else:
            text = f"当前步骤: {current_step}"
        
        self.step_panel.setPlainText(text)
    
    def append_step(self, message: str, is_error: bool = False):
        """添加步骤信息"""
        if not hasattr(self, 'step_panel'):
            return
        
        cursor = self.step_panel.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        format = QTextCharFormat()
        if is_error:
            format.setForeground(QColor("#f44336"))  # 红色
        
        cursor.insertText(f"{message}\n", format)
        self.step_panel.setTextCursor(cursor)
        self.step_panel.ensureCursorVisible()
    
    def setupConnections(self):
        """设置信号连接"""
        # 连接设置变更信号
        self.settings_widget.settings_changed.connect(self.on_settings_changed)
        
        # 连接日志消息信号
        log_manager.log_message.connect(self.console.append_message)
    
    def on_settings_changed(self, settings: dict):
        """处理设置变更"""
        # 更新数据文件路径
        if 'data_file' in settings:
            self.data_manager.file_path = settings['data_file']
        
        # 更新自动保存设置
        if 'auto_save' in settings and 'auto_save_interval' in settings:
            if settings['auto_save']:
                interval = settings['auto_save_interval'] * 60 * 1000  # 转换为毫秒
                self.auto_save_timer.start(interval)
            else:
                self.auto_save_timer.stop()
    
    def loadSettings(self):
        """加载所有设置"""
        self.settings_widget.loadSettings()
        self.plot_widget.loadSettings()
        
        # 应用自动保存设置
        config = log_manager.load_config()
        data_settings = config.get('data', {})
        if data_settings.get('auto_save', True):
            interval = data_settings.get('auto_save_interval', 5) * 60 * 1000  # 转换为毫秒
            self.auto_save_timer.start(interval)
    
    def auto_save(self):
        """自动保存数据"""
        try:
            if self.data_manager.save_data():
                log_manager.debug("数据自动保存成功")
            else:
                log_manager.warning("数据自动保存失败")
        except Exception as e:
            log_manager.error(f"自动保存时发生错误: {str(e)}")
    
    def closeEvent(self, event):
        """关闭窗口时的处理"""
        try:
            # 停止自动保存定时器
            self.auto_save_timer.stop()
            
            # 保存数据
            if self.data_manager.save_data():
                log_manager.info("数据已保存")
            
            # 保存设置
            self.settings_widget.save_settings()
            
        except Exception as e:
            log_manager.error(f"关闭窗口时发生错误: {str(e)}")
        
        event.accept()
    
    @Slot()
    def undo(self):
        if self.data_manager.undo():
            self.plot_widget.set_data(self.data_manager.data)
            self.data_view.set_data(self.data_manager.data)
    
    @Slot()
    def redo(self):
        if self.data_manager.redo():
            self.plot_widget.set_data(self.data_manager.data)
            self.data_view.set_data(self.data_manager.data)
    
    @Slot()
    def cut(self):
        if hasattr(self, 'selected_indices') and self.selected_indices:
            self.copy()
            self.data_manager.delete_points(self.selected_indices)
            self.plot_widget.set_data(self.data_manager.data)
            self.data_view.set_data(self.data_manager.data)
    
    @Slot()
    def copy(self):
        if hasattr(self, 'selected_indices') and self.selected_indices:
            data = [self.data_manager.data[i] for i in self.selected_indices]
            QApplication.clipboard().setText('\n'.join(map(str, data)))
    
    @Slot()
    def paste(self):
        try:
            text = QApplication.clipboard().text()
            data = [float(x) for x in text.split() if x.strip()]
            if data:
                if hasattr(self, 'selected_indices') and self.selected_indices:
                    # 替换选中的数据
                    self.data_manager.modify_points(self.selected_indices, data)
                else:
                    # 追加到末尾
                    self.data_manager.data.extend(data)
                self.plot_widget.set_data(self.data_manager.data)
                self.data_view.set_data(self.data_manager.data)
        except ValueError:
            QMessageBox.warning(self, "错误", "剪贴板中的数据格式不正确！")

    @Slot()
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开数据文件", "", "文本文件 (*.txt)")
        if file_path:
            if self.data_manager.load_data(file_path):
                self.plot_widget.set_data(self.data_manager.data)
                self.data_view.set_data(self.data_manager.data)
                
                # 更新全局统计信息
                stats = {
                    "数量": len(self.data_manager.data),
                    "平均值": np.mean(self.data_manager.data),
                    "最大值": max(self.data_manager.data),
                    "最小值": min(self.data_manager.data)
                }
                self.global_stats.setText(text)

    @Slot()
    def save_file(self):
        if not self.data_manager.file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存数据文件", "", "文本文件 (*.txt)")
            if not file_path:
                return False
            self.data_manager.file_path = file_path
        return self.data_manager.save_data()

    @Slot()
    def export_png(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出PNG", "", "PNG图片 (*.png)")
        if file_path:
            self.plot_widget.figure.savefig(file_path)

    @Slot()
    def toggle_grid(self):
        self.plot_widget.toggle_grid()

    @Slot()
    def toggle_points(self):
        self.plot_widget.toggle_points()

    @Slot()
    def analyze_peaks(self):
        self.data_view.find_peaks()

    @Slot()
    def find_patterns(self):
        self.data_view.find_patterns()

    @Slot()
    def on_data_modified(self, data):
        self.data_manager.update_data(data)
        self.plot_widget.set_data(data)
        
        # 更新全局统计信息
        stats = {
            "数量": len(data),
            "平均值": np.mean(data) if data else 0,
            "最大值": max(data) if data else 0,
            "最小值": min(data) if data else 0
        }
        self.global_stats.setText(text)
    
    @Slot()
    def on_data_selected(self, indices):
        self.selected_indices = indices
        # 更新统计信息
        if indices:
            selected_data = [self.data_manager.data[i] for i in indices]
            stats = {
                "数量": len(selected_data),
                "平均值": np.mean(selected_data),
                "最大值": max(selected_data),
                "最小值": min(selected_data)
            }
            self.selection_stats.setText(text)
        else:
            self.selection_stats.setText("")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 