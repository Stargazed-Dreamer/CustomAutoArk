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
        """
        初始化数据可视化工具的主窗口。

        功能：设置窗口标题、字体、大小，创建UI组件（包括布局、分割器、数据面板等），加载配置，并连接信号与槽。
        参数：无（除了实例自身self）
        返回值：None（__init__方法不返回值）
        """
        super().__init__()  # 调用父类QWidget的构造函数，初始化基本窗口属性
        self.setWindowTitle("数据可视化工具")  # 设置主窗口标题，显示在标题栏
    
        # 设置中文字体，根据操作系统平台选择默认字体以确保界面文字正常显示
        if platform.system() == 'Windows':
            font = QFont('Microsoft YaHei', 9)  # 微软雅黑，Windows系统常用中文字体
        elif platform.system() == 'Darwin':
            font = QFont('PingFang SC', 9)  # macOS 苹方，苹果系统默认中文字体
        else:
            font = QFont('Sans', 9)  # Linux 默认无衬线字体，确保跨平台兼容性
        self.setFont(font)  # 将选中的字体应用到整个窗口及其子部件
    
        # 加载配置文件，实例化Config对象以读取和存储应用程序设置（如窗口大小）
        self.config = Config()
    
        # 设置窗口大小，从配置中获取宽度和高度，如果未配置则使用默认值1200x800像素
        self.resize(
            self.config.get("ui", "window_width", 1200),  # 窗口宽度，默认1200像素
            self.config.get("ui", "window_height", 800)   # 窗口高度，默认800像素
        )
    
        # 创建数据管理器实例，用于处理数据的加载、存储、分析和可视化
        self.data_manager = DataManager()
    
        # 创建中心部件，作为窗口的主内容区域容器
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)  # 将中心部件设置到窗口中央
    
        # 创建主布局，使用水平布局管理器将组件排列在一行
        self.main_layout = QHBoxLayout(self.central_widget)
    
        # 创建分割器，允许用户通过拖动分隔线调整左右面板的大小比例
        self.splitter = QSplitter(Qt.Horizontal)  # 创建水平分割器，方向为水平
    
        # 创建左侧数据面板，包含绘图和统计部件，用于数据可视化
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)  # 使用垂直布局管理左侧部件
        self.plot_widget = PlotWidget()  # 实例化绘图部件，用于显示图表和图形
        self.stats_widget = StatsWidget()  # 实例化统计部件，用于显示数据统计信息
        self.left_layout.addWidget(self.plot_widget, stretch=7)  # 将绘图部件添加到布局，拉伸因子为7，占用更多空间
        self.left_layout.addWidget(self.stats_widget, stretch=3)  # 将统计部件添加到布局，拉伸因子为3，占用较少空间
    
        # 创建右侧数据视图，用于以表格或列表形式显示和编辑原始数据
        self.data_view = DataView()
    
        # 将左侧数据面板和右侧数据视图添加到分割器中
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.data_view)
        self.splitter.setStretchFactor(0, 7)  # 设置左侧面板在分割器中的拉伸因子为7
        self.splitter.setStretchFactor(1, 3)  # 设置右侧数据视图在分割器中的拉伸因子为3
    
        # 将分割器添加到主布局，使其占据整个窗口宽度
        self.main_layout.addWidget(self.splitter)
    
        # 创建菜单栏，提供文件、编辑、视图等应用程序菜单选项
        self.create_menu_bar()
    
        # 创建状态栏，用于显示应用程序状态信息（如操作提示、错误消息）
        self.statusBar = QStatusBar()
        self.statusBar.setFont(font)  # 将状态栏字体设置为与主窗口一致的字体
        self.setStatusBar(self.statusBar)  # 将状态栏添加到窗口底部
    
        # 设置键盘快捷键，绑定常用操作（如保存、打开）以提高用户操作效率
        self.setup_shortcuts()
    
        # 连接UI部件的信号（如按钮点击、数据变化）到相应的槽函数，实现交互逻辑
        self.setup_connections()
    
        # 设置自动保存功能，定期保存数据到配置中指定的位置，防止数据丢失
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
        """将选中的点数据复制到剪贴板。
    
        检查 plot_widget 中是否有选中的点，如果有则获取对应的数据，
        将这些数据转换为字符串并用换行符连接，最后复制到系统剪贴板。
    
        Args:
            self: 类实例，包含 plot_widget 和 data_manager 属性。
    
        Returns:
            None: 该方法没有返回值。
        """
        # 检查是否有选中的点
        if self.plot_widget.selected_points:
            # 从 PySide6 导入剪贴板类
            from PySide6.QtGui import QClipboard
            # 获取应用程序的剪贴板对象
            clipboard = self.application().clipboard()
            # 根据选中的点索引，提取对应的数据并转换为字符串列表
            data = [str(self.data_manager.data[i]) 
                   for i in self.plot_widget.selected_points]
            # 将数据用换行符连接成文本，并设置到剪贴板
            clipboard.setText('\n'.join(data))
            
    @Slot()
    def cut(self):
        """剪切选中的数据点。

        此方法首先复制当前数据，然后删除图表中选中的数据点，
        并更新相关视图和统计信息。

        参数:
            self: 类的实例

        返回值:
            无
        """
        self.copy()  # 首先复制当前数据以支持撤销操作
        if self.plot_widget.selected_points:  # 检查是否有选中的数据点
            self.data_manager.delete_points(self.plot_widget.selected_points)  # 从数据管理器中删除选中的点
            self.plot_widget.selected_points = []  # 清空图表控件中的选中点列表
            self.plot_widget.set_data(self.data_manager.data)  # 用更新后的数据刷新图表显示
            self.data_view.set_data(self.data_manager.data)  # 用更新后的数据刷新数据视图
            self.stats_widget.update_stats(self.data_manager.data)  # 更新统计信息部件的数据显示
            
    @Slot()
    def paste(self):
        """从系统剪贴板粘贴数据到图表中。

        从剪贴板读取文本，解析为浮点数列表，然后将这些数据插入到当前选中点之后。
        如果剪贴板内容无法解析为有效数据，则静默失败。

        Args:
            self: 实例自身

        Returns:
            None: 该方法不返回任何值，但会修改数据视图和图表的显示。
        """
        from PySide6.QtGui import QClipboard
        clipboard = self.application().clipboard()  # 获取应用程序的剪贴板对象
        text = clipboard.text()  # 从剪贴板读取文本内容
        try:
            # 将文本按行分割，并尝试将每行转换为浮点数，过滤掉空行
            data = [float(line) for line in text.split('\n') if line.strip()]
            if data:
                # 计算插入位置：如果有选中的点，则在最大选中点之后插入；否则插入到数据末尾
                insert_pos = (max(self.plot_widget.selected_points) + 1 
                            if self.plot_widget.selected_points 
                            else len(self.data_manager.data))
                # 将数据逆序插入，以保持原有顺序（因为插入位置在逐个后移）
                for value in reversed(data):
                    self.data_manager.data.insert(insert_pos, value)
                # 更新图表、数据视图和统计信息的显示
                self.plot_widget.set_data(self.data_manager.data)
                self.data_view.set_data(self.data_manager.data)
                self.stats_widget.update_stats(self.data_manager.data)
        except (ValueError, AttributeError):
            # 如果转换失败或剪贴板对象属性异常，则静默忽略
            pass
            
    @Slot()
    def toggle_grid(self):
        """切换网格的显示和隐藏。

        参数:
            无

        返回值:
            无
        """
        self.plot_widget.ax.grid(not self.plot_widget.ax.get_grid())  # 获取当前网格状态并取反，以切换显示
        self.plot_widget.canvas.draw()  # 重绘画布，使网格变化生效
        
    @Slot()
    def toggle_points(self):
        """
        切换点的显示状态并更新绘图。
    
        功能：此方法用于切换 plot_widget 中点的显示状态，如果当前显示则隐藏，反之亦然，并调用 update_plot 方法更新绘图。
        参数：self - 实例引用，隐式参数。
        返回值：无返回值。
        """
        # 切换点的显示状态
        self.plot_widget.show_points = not self.plot_widget.show_points
        # 更新绘图以应用新的显示状态
        self.plot_widget.update_plot()
        
    @Slot()
    def analyze_peaks(self):
        """分析数据中的波峰和波谷，并在图表上进行标注和统计。

        该方法通过弹出对话框获取用户设定的阈值，然后查找数据中的波峰和波谷，
        在图表上用不同颜色进行标注，并在统计组件中显示相关统计信息。

        参数:
            self: 实例对象自身

        返回:
            None（直接修改图表和统计组件的状态）
        """
        # 通过输入对话框获取用户设定的波峰波谷检测阈值
        threshold, ok = QInputDialog.getDouble(
            self, "设置阈值", "请输入波峰波谷检测阈值:", 0.0, -1000000, 1000000, 2)
        if not ok:  # 如果用户点击取消，则不进行分析，直接返回
            return

        # 使用数据管理器根据阈值查找波峰和波谷的索引
        peaks = self.data_manager.find_peaks(threshold)
        valleys = self.data_manager.find_valleys(threshold)

        # 清空当前图表，准备重新绘制
        self.plot_widget.ax.clear()

        # 绘制原始数据主线，使用蓝色实线
        self.plot_widget.line, = self.plot_widget.ax.plot(
            self.plot_widget.x_data,  # X轴数据
            self.plot_widget.data,    # Y轴数据
            'b-',                     # 蓝色实线样式
            linewidth=1               # 线宽为1
        )

        # 如果存在波峰，则在图表上用红色散点标注
        if peaks:
            peak_x = [self.plot_widget.x_data[i] for i in peaks]  # 提取波峰点的X坐标
            peak_y = [self.plot_widget.data[i] for i in peaks]     # 提取波峰点的Y坐标
            self.plot_widget.ax.scatter(peak_x, peak_y,            # 绘制红色散点标记波峰
                                      color='red', s=100,          # 颜色为红色，点大小为100
                                      label='波峰', zorder=3)       # 添加图例标签，并设置绘制层级为3

        # 如果存在波谷，则在图表上用绿色散点标注
        if valleys:
            valley_x = [self.plot_widget.x_data[i] for i in valleys]  # 提取波谷点的X坐标
            valley_y = [self.plot_widget.data[i] for i in valleys]     # 提取波谷点的Y坐标
            self.plot_widget.ax.scatter(valley_x, valley_y,            # 绘制绿色散点标记波谷
                                      color='green', s=100,            # 颜色为绿色，点大小为100
                                      label='波谷', zorder=3)           # 添加图例标签，并设置绘制层级为3

        # 在图表上显示图例
        self.plot_widget.ax.legend()

        # 根据网格开关状态绘制网格线
        if self.plot_widget.grid_on:
            self.plot_widget.ax.grid(self.plot_widget.grid_on, linestyle=PlotStyle.GRID_STYLE, alpha=PlotStyle.GRID_ALPHA)

        # 向统计组件中添加波峰和波谷的数量统计
        self.stats_widget.add_custom_stat("波峰数量", len(peaks))
        self.stats_widget.add_custom_stat("波谷数量", len(valleys))

        # 如果存在波峰，统计并添加波峰的最大值和最小值
        if peaks:
            peak_values = [self.plot_widget.data[i] for i in peaks]  # 获取所有波峰点的Y值
            self.stats_widget.add_custom_stat("最大波峰值", max(peak_values))  # 添加最大波峰值统计
            self.stats_widget.add_custom_stat("最小波峰值", min(peak_values))  # 添加最小波峰值统计

        # 如果存在波谷，统计并添加波谷的最大值和最小值
        if valleys:
            valley_values = [self.plot_widget.data[i] for i in valleys]  # 获取所有波谷点的Y值
            self.stats_widget.add_custom_stat("最大波谷值", max(valley_values))  # 添加最大波谷值统计
            self.stats_widget.add_custom_stat("最小波谷值", min(valley_values))  # 添加最小波谷值统计

        # 重绘画布以更新图表显示
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