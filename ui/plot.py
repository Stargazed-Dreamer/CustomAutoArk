import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from PySide6.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from PySide6.QtCore import Signal

from log import log_manager
from data_manager import data_manager
from .global_state import g

import numpy as np

matplotlib.use('Qt5Agg')
# 设置matplotlib的默认字体
plt.rcParams['font.family'] = ['sans-serif']
import platform
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

# 数据展示组件
class PlotWidget(QWidget):
    # 自定义信号
    data_selected = Signal(list)  # 数据选中信号
    data_modified = Signal(list)  # 数据修改信号
    hover_point_changed = Signal(int)  # 悬停点变化信号
    
    def __init__(self, parent=None):
        """初始化方法，用于设置对象的初始状态。

        参数:
            parent: 可选参数，指定父对象，默认为None。

        返回值:
            无返回值。

        """
        super().__init__(parent)  # 调用父类的初始化方法，传递parent参数
        self._updating = False  # 防止循环更新
        self.initUI()  # 初始化用户界面
        self.setup_plot()  # 设置绘图组件
        self.setup_interactions()  # 设置交互功能
        
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
        """
        清除当前图表的所有图形元素并重新绘制数据。

        该方法会：
        1. 清除所有先前的图形元素引用。
        2. 检查数据是否为空，若为空则直接返回。
        3. 计算数据和坐标轴的边界范围及边距。
        4. 绘制数据主线、可选的数据点、选中的高亮数据点。
        5. 设置网格、坐标轴范围和标签。
        6. 刷新画布以显示更新。

        参数:
            self: 实例对象本身，包含绘图所需的数据和状态。

        返回值:
            None: 无显式返回值，但通过副作用更新图表显示。
        """
        self.ax.clear()
        # 清除所有图形元素的引用，以避免内存泄漏和绘制重影
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

        # 重新绘制逻辑：首先检查数据是否存在
        if not self.data:
            return

        # 计算数据的最小值和最大值，用于确定Y轴范围
        data_min = min(self.data)
        data_max = max(self.data)
        # X轴的默认范围基于数据点的索引
        x_min = 0
        x_max = len(self.data) - 1

        # 设置合适的边距，防止数据点紧贴坐标轴边缘
        # y_margin: 取数据范围的5%和1中的较大值，确保最小间距
        y_margin = max((data_max - data_min) * 0.05, 1)
        # x_margin: 取数据长度的2%和1中的较大值，确保最小间距
        x_margin = max(len(self.data) * 0.02, 1)

        # 计算默认视图范围，为数据范围加上边距
        default_xlim = (x_min - x_margin, x_max + x_margin)
        default_ylim = (data_min - y_margin, data_max + y_margin)

        # 保存当前视图范围，以便在重绘时保持用户的缩放/平移状态
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        # 如果当前范围是Matplotlib的默认值(0,1)，则使用计算出的默认范围
        if xlim == (0, 1) or ylim == (0, 1):
            xlim = default_xlim
            ylim = default_ylim

        # 绘制主线，使用连续的实线，线宽为1
        self.line, = self.ax.plot(self.x_data, self.data, '-', lw=1)

        # 根据配置决定是否绘制数据点
        if self.show_points:
            self.scatter = self.ax.scatter(self.x_data, self.data, s=20)

        # 如果有选中的数据点，则用红色、较大的点进行高亮显示
        if self.selected_indices:
            # 从索引列表中提取对应的x和y坐标
            selected_x = [self.x_data[i] for i in self.selected_indices]
            selected_y = [self.data[i] for i in self.selected_indices]
            self.ax.scatter(selected_x, selected_y, color='red', s=50, zorder=3)

        # 设置网格的显示状态和样式
        self.ax.grid(self.grid_on, linestyle='--', alpha=0.7)

        # 设置坐标轴的范围
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)

        # 设置坐标轴的标签
        self.ax.set_xlabel('时间点')
        self.ax.set_ylabel('数值')

        # 刷新画布，使所有更改在图形用户界面上可见
        self.canvas.draw()
    
    def _safe_remove(self, artist):
        """安全移除元素，避免NotImplementedError"""
        if artist is not None:
            try:
                artist.remove()
            except (NotImplementedError, ValueError):
                pass

    def on_mouse_press(self, event):
        """处理鼠标按下事件，用于选择或平移视图。

        根据鼠标按键（左键或右键）触发不同的交互逻辑：
        - 左键单击：重置当前选择，并开始框选。
        - 右键单击：开始平移视图。

        参数:
            self: 类实例自身。
            event: 鼠标事件对象，包含点击坐标、所在坐标轴、按键等信息。

        返回值:
            无。
        """
        # 检查鼠标点击是否发生在当前绑定的坐标轴内，如果不是则直接返回，忽略事件
        if event.inaxes != self.ax:
            return

        # 判断鼠标按键
        if event.button == 1:
            # 单击左键时清除已有选择
            self.selected_indices = []
            # 如果主窗口存在数据视图组件，则清除其高亮显示
            if hasattr(g.mainWindow, 'data_view'):
                g.mainWindow.data_view.highlight_lines([])

            # 设置状态：正在框选
            self.is_selecting = True
            # 记录框选的起始坐标点
            self.selection_start = (event.xdata, event.ydata)
            # 安全移除旧的矩形选择框图形对象
            self._safe_remove(self.selection_rect)
            self.selection_rect = None
            # 安全移除旧的悬停标注图形对象
            self._safe_remove(self.hover_annotation)
            self.hover_annotation = None
            # 刷新画布以显示变化
            self.canvas.draw()
        elif event.button == 3:  # 右键
            # 设置状态：正在平移
            self.is_panning = True
            # 记录平移操作的起始坐标点
            self.pan_start = (event.xdata, event.ydata)
            # 导入PySide6的QApplication用于修改光标样式
            from PySide6.QtWidgets import QApplication
            # 将鼠标光标设置为手型（抓住），表示平移模式
            QApplication.setOverrideCursor(Qt.ClosedHandCursor)
        
    def on_mouse_release(self, event):
        from PySide6.QtWidgets import QApplication
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
        """切换点显示状态并更新绘图。

        参数：
            self - 当前实例

        返回值：
            无
        """
        self.show_points = not self.show_points  # 切换点显示状态
        self._update_plot()  # 更新绘图

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
            
        from PySide6.QtWidgets import QInputDialog
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