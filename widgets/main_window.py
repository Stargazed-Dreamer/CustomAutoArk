"""
主窗口组件 (MainWindow)
这个模块提供了应用程序的主窗口界面，负责组织和管理各个子组件。

主要功能：
1. 界面布局：
   - 左侧面板：绘图区域和统计信息
   - 右侧面板：数据编辑器
   - 可调节的分割器
   - 菜单栏和状态栏

2. 文件操作：
   - 打开/保存数据文件
   - 导出图表为PNG
   - 自动保存功能

3. 数据同步：
   - 在绘图、编辑器和统计之间同步数据
   - 支持撤销/重做操作
   - 剪切/复制/粘贴功能

4. 分析功能：
   - 波峰波谷分析
   - 相似模式查找

快捷键：
- Ctrl+O: 打开文件
- Ctrl+S: 保存文件
- Ctrl+E: 导出图片
- Ctrl+G: 切换网格
- Ctrl+P: 切换数据点
- Ctrl+F: 波峰波谷分析
- Ctrl+M: 相似模式查找

配置管理：
- 保存窗口大小和分割比例
- 自动保存设置
- 界面字体设置
"""

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QSplitter, QMenuBar, QMenu, 
                                QStatusBar, QFileDialog, QInputDialog)
from PySide6.QtCore import Qt, Slot, QTimer, QSignalBlocker
from PySide6.QtGui import QKeySequence, QShortcut, QFont
import numpy as np
from .plot_widget import PlotWidget, PlotStyle
from .data_view import DataView
from .stats_widget import StatsWidget
from utils.data_manager import DataManager
from config import Config
import platform

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("数据可视化工具")
        
        # 设置中文字体
        if platform.system() == 'Windows':
            font = QFont('Microsoft YaHei', 9)  # 微软雅黑
        elif platform.system() == 'Darwin':
            font = QFont('PingFang SC', 9)  # macOS 苹方
        else:
            font = QFont('Sans', 9)  # Linux 默认无衬线字体
        self.setFont(font)
        
        # 加载配置
        self.config = Config()
        
        # 设置窗口大小
        self.resize(
            self.config.get("ui", "window_width", 1200),
            self.config.get("ui", "window_height", 800)
        )
        
        # 创建数据管理器
        self.data_manager = DataManager()
        
        # 创建中心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Horizontal)
        
        # 创建左侧数据面板
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.plot_widget = PlotWidget()
        self.stats_widget = StatsWidget()
        self.left_layout.addWidget(self.plot_widget, stretch=7)
        self.left_layout.addWidget(self.stats_widget, stretch=3)
        
        # 创建右侧数据视图
        self.data_view = DataView()
        
        # 添加到分割器
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.data_view)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)
        
        # 添加到主布局
        self.main_layout.addWidget(self.splitter)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.statusBar.setFont(font)
        self.setStatusBar(self.statusBar)
        
        # 设置快捷键
        self.setup_shortcuts()
        
        # 连接信号
        self.setup_connections()
        
        # 设置自动保存
        self.setup_auto_save()
        
    def setup_auto_save(self):
        """设置自动保存"""
        if self.config.get("data", "auto_save", True):
            self.auto_save_timer = QTimer(self)
            self.auto_save_timer.timeout.connect(self.auto_save)
            interval = self.config.get("data", "auto_save_interval", 300) * 1000  # 转换为毫秒
            self.auto_save_timer.start(interval)
            
    def auto_save(self):
        """自动保存处理"""
        if self.data_manager.file_path and self.data_manager.data:
            if self.data_manager.save_data():
                self.statusBar.showMessage("自动保存完成", 3000)  # 显示3秒
                
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 保存窗口大小
        self.config.set("ui", "window_width", self.width())
        self.config.set("ui", "window_height", self.height())
        
        # 保存分割器比例
        sizes = self.splitter.sizes()
        if sum(sizes) > 0:
            ratio = sizes[0] / sum(sizes)
            self.config.set("ui", "splitter_ratio", ratio)
            
        # 保存数据
        if self.data_manager.file_path and self.data_manager.data:
            self.data_manager.save_data()
            
        event.accept()
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        open_action = file_menu.addAction("打开")
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_file)
        
        save_action = file_menu.addAction("保存")
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_file)
        
        export_action = file_menu.addAction("导出")
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_file)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        toggle_grid_action = view_menu.addAction("显示网格")
        toggle_grid_action.setShortcut("Ctrl+G")
        toggle_grid_action.triggered.connect(self.plot_widget.toggle_grid)
        toggle_grid_action.setCheckable(True)
        toggle_grid_action.setChecked(True)
        
        toggle_points_action = view_menu.addAction("显示数据点")
        toggle_points_action.setShortcut("Ctrl+P")
        toggle_points_action.triggered.connect(self.plot_widget.toggle_points)
        toggle_points_action.setCheckable(True)
        toggle_points_action.setChecked(False)
        
        # 分析菜单
        analyze_menu = menubar.addMenu("分析")
        
        peaks_action = analyze_menu.addAction("波峰波谷")
        peaks_action.setShortcut("Ctrl+F")
        peaks_action.triggered.connect(self.analyze_peaks)
        
        patterns_action = analyze_menu.addAction("相似模式")
        patterns_action.setShortcut("Ctrl+M")
        patterns_action.triggered.connect(self.find_patterns)
        
    def setup_shortcuts(self):
        """设置快捷键"""
        # 文件操作
        QShortcut(QKeySequence.Open, self, self.open_file)
        QShortcut(QKeySequence.Save, self, self.save_file)
        
        # 编辑操作
        QShortcut(QKeySequence.Undo, self, self.undo)
        QShortcut(QKeySequence.Redo, self, self.redo)
        QShortcut(QKeySequence.Copy, self, self.copy)
        QShortcut(QKeySequence.Cut, self, self.cut)
        QShortcut(QKeySequence.Paste, self, self.paste)
        
    def setup_connections(self):
        """设置信号连接"""
        # 数据修改信号
        self.plot_widget.data_modified.connect(self._on_data_modified)
        self.data_view.data_changed.connect(self._on_data_modified)
        
        # 数据选择信号
        self.plot_widget.data_selected.connect(self._on_data_selected)
        
        # 悬停点变化信号
        self.plot_widget.hover_point_changed.connect(self.data_view.highlight_hover_point)
        
    @Slot(list)
    def _on_data_modified(self, data):
        """数据修改处理"""
        if not data:
            return
            
        try:
            # 检查数据是否真的改变
            if (hasattr(self, '_last_data') and 
                len(self._last_data) == len(data) and 
                all(a == b for a, b in zip(self._last_data, data))):
                return
                
            # 更新数据管理器
            self.data_manager.data = data
            self._last_data = data.copy()
            
            # 更新界面组件（不触发新的数据修改信号）
            with QSignalBlocker(self.plot_widget):
                self.plot_widget.set_data(data)
            with QSignalBlocker(self.data_view):
                self.data_view.set_data(data)
            with QSignalBlocker(self.stats_widget):
                self.stats_widget.update_stats(data)
            
            # 更新状态栏
            self.statusBar.showMessage("数据已更新", 3000)
            
        except Exception as e:
            print(f"数据更新错误: {e}")
            import traceback
            traceback.print_exc()
            
    @Slot(list)
    def _on_data_selected(self, selected_points):
        """数据选择处理"""
        try:
            with QSignalBlocker(self.data_view):
                self.data_view.highlight_lines(selected_points)
                
            if selected_points:
                selected_data = [self.data_manager.data[i] for i in selected_points]
                with QSignalBlocker(self.stats_widget):
                    self.stats_widget.update_stats(self.data_manager.data, selected_data)
                    
        except Exception as e:
            print(f"选择处理错误: {e}")
            import traceback
            traceback.print_exc()
            
    @Slot()
    def open_file(self):
        """打开文件"""
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self, "打开文件", "", "文本文件 (*.txt);;所有文件 (*.*)")
            if not file_name:
                return
                
            if self.data_manager.load_data(file_name):
                # 使用阻塞方式更新界面
                with QSignalBlocker(self.plot_widget):
                    self.plot_widget.set_data(self.data_manager.data)
                with QSignalBlocker(self.data_view):
                    self.data_view.set_data(self.data_manager.data)
                with QSignalBlocker(self.stats_widget):
                    self.stats_widget.update_stats(self.data_manager.data)
                    
                self._last_data = self.data_manager.data.copy()
                self.statusBar.showMessage(f"已加载文件: {file_name}")
                
        except Exception as e:
            print(f"打开文件错误: {e}")
            import traceback
            traceback.print_exc()
            
    @Slot()
    def save_file(self):
        if not self.data_manager.file_path:
            file_name, _ = QFileDialog.getSaveFileName(
                self, "保存文件", "", "文本文件 (*.txt);;所有文件 (*.*)")
            if not file_name:
                return
            self.data_manager.file_path = file_name
            
        if self.data_manager.save_data():
            self.statusBar.showMessage("文件已保存")
            
    @Slot()
    def export_file(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "导出文件", "", "PNG图片 (*.png);;所有文件 (*.*)")
        if file_name:
            if self.data_manager.export_png(file_name):
                self.statusBar.showMessage(f"已导出到: {file_name}")
            
    @Slot()
    def undo(self):
        if self.data_manager.undo():
            self.plot_widget.set_data(self.data_manager.data)
            self.data_view.set_data(self.data_manager.data)
            self.stats_widget.update_stats(self.data_manager.data)
            
    @Slot()
    def redo(self):
        if self.data_manager.redo():
            self.plot_widget.set_data(self.data_manager.data)
            self.data_view.set_data(self.data_manager.data)
            self.stats_widget.update_stats(self.data_manager.data)
            
    @Slot()
    def copy(self):
        if self.plot_widget.selected_points:
            from PySide6.QtGui import QClipboard
            clipboard = self.application().clipboard()
            data = [str(self.data_manager.data[i]) 
                   for i in self.plot_widget.selected_points]
            clipboard.setText('\n'.join(data))
            
    @Slot()
    def cut(self):
        self.copy()
        if self.plot_widget.selected_points:
            self.data_manager.delete_points(self.plot_widget.selected_points)
            self.plot_widget.selected_points = []
            self.plot_widget.set_data(self.data_manager.data)
            self.data_view.set_data(self.data_manager.data)
            self.stats_widget.update_stats(self.data_manager.data)
            
    @Slot()
    def paste(self):
        from PySide6.QtGui import QClipboard
        clipboard = self.application().clipboard()
        text = clipboard.text()
        try:
            data = [float(line) for line in text.split('\n') if line.strip()]
            if data:
                # 在当前选中点后插入
                insert_pos = (max(self.plot_widget.selected_points) + 1 
                            if self.plot_widget.selected_points 
                            else len(self.data_manager.data))
                for value in reversed(data):
                    self.data_manager.data.insert(insert_pos, value)
                self.plot_widget.set_data(self.data_manager.data)
                self.data_view.set_data(self.data_manager.data)
                self.stats_widget.update_stats(self.data_manager.data)
        except (ValueError, AttributeError):
            pass
            
    @Slot()
    def toggle_grid(self):
        self.plot_widget.ax.grid(not self.plot_widget.ax.get_grid())
        self.plot_widget.canvas.draw()
        
    @Slot()
    def toggle_points(self):
        self.plot_widget.show_points = not self.plot_widget.show_points
        self.plot_widget.update_plot()
        
    @Slot()
    def analyze_peaks(self):
        # 获取阈值
        threshold, ok = QInputDialog.getDouble(
            self, "设置阈值", "请输入波峰波谷检测阈值:", 0.0, -1000000, 1000000, 2)
        if not ok:
            return
            
        # 查找波峰波谷
        peaks = self.data_manager.find_peaks(threshold)
        valleys = self.data_manager.find_valleys(threshold)
        
        # 在图表上标注
        self.plot_widget.ax.clear()
        
        # 绘制主线
        self.plot_widget.line, = self.plot_widget.ax.plot(
            self.plot_widget.x_data, 
            self.plot_widget.data, 
            'b-', 
            linewidth=1
        )
        
        # 标注波峰
        if peaks:
            peak_x = [self.plot_widget.x_data[i] for i in peaks]
            peak_y = [self.plot_widget.data[i] for i in peaks]
            self.plot_widget.ax.scatter(peak_x, peak_y, 
                                      color='red', s=100, 
                                      label='波峰', zorder=3)
            
        # 标注波谷
        if valleys:
            valley_x = [self.plot_widget.x_data[i] for i in valleys]
            valley_y = [self.plot_widget.data[i] for i in valleys]
            self.plot_widget.ax.scatter(valley_x, valley_y, 
                                      color='green', s=100, 
                                      label='波谷', zorder=3)
            
        # 添加图例
        self.plot_widget.ax.legend()
        
        # 绘制网格
        if self.plot_widget.grid_on:
            self.plot_widget.ax.grid(self.plot_widget.grid_on, linestyle=PlotStyle.GRID_STYLE, alpha=PlotStyle.GRID_ALPHA)

        # 更新统计信息
        self.stats_widget.add_custom_stat("波峰数量", len(peaks))
        self.stats_widget.add_custom_stat("波谷数量", len(valleys))
        
        if peaks:
            peak_values = [self.plot_widget.data[i] for i in peaks]
            self.stats_widget.add_custom_stat("最大波峰值", max(peak_values))
            self.stats_widget.add_custom_stat("最小波峰值", min(peak_values))
            
        if valleys:
            valley_values = [self.plot_widget.data[i] for i in valleys]
            self.stats_widget.add_custom_stat("最大波谷值", max(valley_values))
            self.stats_widget.add_custom_stat("最小波谷值", min(valley_values))
            
        # 重绘
        self.plot_widget.canvas.draw()
        
    @Slot()
    def find_patterns(self):
        if not self.plot_widget.selected_points:
            self.statusBar.showMessage("请先选择一段数据作为参考模式")
            return
            
        # 获取相似度阈值
        threshold, ok = QInputDialog.getDouble(
            self, "设置阈值", "请输入模式相似度阈值 (0-1):", 0.1, 0, 1, 2)
        if not ok:
            return
            
        # 查找相似模式
        similar_positions = self.data_manager.find_similar_patterns(
            [self.data_manager.data[i] for i in self.plot_widget.selected_points],
            threshold
        )
        
        # 高亮显示相似模式
        self.plot_widget.ax.clear()
        
        # 绘制主线
        self.plot_widget.line, = self.plot_widget.ax.plot(
            self.plot_widget.x_data, 
            self.plot_widget.data, 
            'b-', 
            linewidth=1
        )
        
        # 高亮显示参考模式
        ref_x = [self.plot_widget.x_data[i] for i in self.plot_widget.selected_points]
        ref_y = [self.plot_widget.data[i] for i in self.plot_widget.selected_points]
        self.plot_widget.ax.plot(ref_x, ref_y, 
                                'r-', linewidth=2, 
                                label='参考模式')
        
        # 高亮显示相似模式
        pattern_length = len(self.plot_widget.selected_points)
        for pos in similar_positions:
            if pos != self.plot_widget.selected_points[0]:  # 排除参考模式本身
                x = self.plot_widget.x_data[pos:pos+pattern_length]
                y = self.plot_widget.data[pos:pos+pattern_length]
                self.plot_widget.ax.plot(x, y, 
                                       'g-', linewidth=2, alpha=0.5)
                
        # 添加图例
        self.plot_widget.ax.legend()
        
        # 更新统计信息
        self.stats_widget.add_custom_stat("找到的相似模式数量", 
                                        len(similar_positions) - 1)  # 减去参考模式本身
        
        # 重绘
        self.plot_widget.canvas.draw()
        
    @Slot(list)
    def on_data_modified(self, data):
        """数据修改处理"""
        if data:
            self.data_manager.data = data
            self.plot_widget.set_data(data)
            self.data_view.set_data(data)
            self.stats_widget.update_stats(data)
        
    @Slot(list)
    def on_data_selected(self, indices):
        """数据选择处理"""
        if indices:
            selected_data = [self.data_manager.data[i] for i in indices]
            self.stats_widget.update_stats(self.data_manager.data, selected_data)
            self.data_view.highlight_lines(indices) 