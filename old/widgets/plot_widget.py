"""
绘图组件 (PlotWidget)
这个模块提供了一个用于数据可视化的绘图组件，基于Matplotlib实现。

主要功能：
1. 数据可视化：支持线图和散点图的绘制
2. 交互功能：支持缩放、平移、选择等交互操作
3. 数据分析：支持数据统计和模式识别
4. 导出功能：支持图表导出为PNG格式

交互功能详解：
1. 鼠标操作：
   - 左键拖拽：框选数据点
   - 右键拖拽：平移视图
   - 滚轮：缩放视图（以鼠标位置为中心）
   - 悬停：显示数据点详细信息

2. 数据选择：
   - 支持框选数据点
   - 选中点高亮显示（红色）
   - 可查找相似数据模式

3. 拖放功能：
   - 支持拖入txt文件导入数据

主要接口：
- set_data(data): 设置要显示的数据
- toggle_grid(): 切换网格显示
- toggle_points(): 切换数据点显示
- find_patterns(): 查找数据模式
- export_png(filename): 导出为PNG图片
- get_statistics(): 获取数据统计信息

信号：
- data_selected: 当数据被选中时发出此信号
- data_modified: 当数据被修改时发出此信号
- hover_point_changed: 当鼠标悬停点改变时发出此信号

样式配置：
通过PlotStyle类定义了图表的默认样式，包括背景色、网格样式、字体大小等
"""

import matplotlib
matplotlib.use('Qt5Agg')

from PySide6.QtWidgets import QWidget, QVBoxLayout, QInputDialog
from PySide6.QtCore import Qt, Signal, Slot
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import platform
import sys

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

class PlotStyle:
    """图表样式配置类"""
    BACKGROUND_COLOR = '#f0f0f0'
    GRID_STYLE = '--'
    GRID_ALPHA = 0.7
    DPI = 100
    FONT_SIZE = 9
    SELECTION_COLOR = 'yellow'
    SELECTION_ALPHA = 0.2
    HOVER_ANNOTATION_STYLE = {
        'bbox': dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
        'arrowprops': dict(arrowstyle='->', connectionstyle='arc3,rad=0')
    }

class PlotWidget(QWidget):
    # 自定义信号
    data_selected = Signal(list)  # 数据选中信号
    data_modified = Signal(list)  # 数据修改信号
    hover_point_changed = Signal(int)  # 悬停点变化信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置递归限制
        sys.setrecursionlimit(10000)
        # 添加更新锁，防止循环更新
        self._updating = False
        # 启用拖放
        self.setAcceptDrops(True)
        self.setup_ui()
        self.setup_plot()
        self.setup_interactions()
        
    def setup_ui(self):
        """初始化UI"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建matplotlib画布
        self.fig = Figure(dpi=PlotStyle.DPI)
        self.canvas = FigureCanvas(self.fig)
        self.layout.addWidget(self.canvas)
        
        # 创建绘图区
        self.ax = self.fig.add_subplot(111)
        
        # 设置基本样式
        self.ax.set_facecolor(PlotStyle.BACKGROUND_COLOR)
        self.ax.grid(True, linestyle=PlotStyle.GRID_STYLE, alpha=PlotStyle.GRID_ALPHA)
        
        # 设置标签
        self.ax.set_xlabel('时间点')
        self.ax.set_ylabel('数值')
        
    def setup_plot(self):
        """初始化绘图设置"""
        # 初始化数据相关属性
        self.data = []
        self.x_data = []
        self.line = None
        self.scatter = None
        
        # 初始化视图状态
        self.current_xlim = None
        self.current_ylim = None
        self.show_points = False
        self.grid_on = True
        
        # 初始化交互状态
        self.selected_points = []
        self.dragging = False
        self.selection_start = None
        self.hover_point = None
        self.pan_start = None
        
        # 设置默认样式
        self._apply_default_style()
        
        # 初始化绘图
        self.canvas.draw()
        
    def _apply_default_style(self):
        """应用默认样式"""
        self.ax.set_facecolor(PlotStyle.BACKGROUND_COLOR)
        if self.grid_on:
            self.ax.grid(self.grid_on, linestyle=PlotStyle.GRID_STYLE, alpha=PlotStyle.GRID_ALPHA)
        self.ax.set_xlabel('时间点')
        self.ax.set_ylabel('数值')
        
    def setup_interactions(self):
        """设置交互事件"""
        self._connect_mouse_events()
        self._connect_keyboard_events()
        
    def _connect_mouse_events(self):
        """连接鼠标事件"""
        events = {
            'button_press_event': self.on_mouse_press,
            'button_release_event': self.on_mouse_release,
            'motion_notify_event': self.on_mouse_move,
            'scroll_event': self.on_scroll
        }
        for event, handler in events.items():
            self.canvas.mpl_connect(event, handler)
            
    def _connect_keyboard_events(self):
        """连接键盘事件"""
        self.canvas.mpl_connect('key_press_event', self.on_key_press)
        
    def set_data(self, data):
        """设置数据并更新图表"""
        if not data:
            print("警告: 收到空数据")
            return
            
        # 防止重复更新
        if self._updating:
            return
            
        self._updating = True
        
        try:
            # 检查数据是否相同
            if hasattr(self, 'data') and len(self.data) == len(data):
                if np.array_equal(self.data, [int(round(float(x))) for x in data]):
                    print("数据未发生变化，跳过更新")
                    return
                    
            # 转换数据为整数
            try:
                new_data = []
                for x in data:
                    try:
                        value = int(round(float(x)))
                        new_data.append(value)
                    except (ValueError, TypeError) as e:
                        print(f"警告: 跳过无效数据 {x}: {e}")
                        continue
                        
                if not new_data:
                    print("警告: 没有有效数据")
                    return
                    
                self.data = np.array(new_data, dtype=np.int32)
                self.x_data = np.arange(len(self.data), dtype=np.int32)
                #print(f"数据转换完成，转换后数据长度: {len(self.data)}")
                
                # 更新图表
                self._update_plot()
                
                # 发送数据修改信号
                self.data_modified.emit(self.data.tolist())
                
            except (ValueError, TypeError, IndexError) as e:
                print(f"数据转换错误: {e}")
                return
            except Exception as e:
                print(f"未预期的错误: {e}")
                return
                
        finally:
            self._updating = False

    def _update_plot(self):
        """更新图表显示"""
        if not hasattr(self, 'data') or len(self.data) == 0:
            return
            
        # 计算数据范围
        data_min = np.min(self.data)
        data_max = np.max(self.data)
        x_min = 0
        x_max = len(self.data) - 1
        
        # 设置合适的边距
        y_margin = max((data_max - data_min) * 0.05, 1)
        x_margin = max(len(self.data) * 0.02, 1)
        
        # 计算默认视图范围
        default_xlim = (x_min - x_margin, x_max + x_margin)
        default_ylim = (data_min - y_margin, data_max + y_margin)
            
        # 保存当前视图范围
        try:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            # 检查当前范围是否合理
            if xlim == (0, 1) or ylim == (0, 1):
                xlim = default_xlim
                ylim = default_ylim
        except Exception:
            xlim = default_xlim
            ylim = default_ylim
            
        # 重置图表
        self.ax.clear()
        self._apply_default_style()
        
        # 绘制数据
        self.line, = self.ax.plot(self.x_data, self.data, 'b-', linewidth=1)
        
        # 绘制选中的点
        if hasattr(self, 'selected_points') and self.selected_points:
            selected_x = [self.x_data[i] for i in self.selected_points]
            selected_y = [self.data[i] for i in self.selected_points]
            self.ax.scatter(selected_x, selected_y, color='red', s=50, zorder=3)
            
        if self.show_points:
            self.scatter = self.ax.scatter(self.x_data, self.data, 
                                         color='blue', s=20, alpha=0.5)
            
        # 设置范围
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        
        # 设置刻度
        self.ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        
        # 刷新画布
        self.canvas.draw()

    def on_mouse_press(self, event):
        """鼠标按下事件处理"""
        if event.inaxes != self.ax:
            return
            
        if event.button == 1:  # 左键
            self.dragging = True
            self.selection_start = (event.xdata, event.ydata)
            self.selected_points = []
            self._update_plot()
        elif event.button == 3:  # 右键
            self.pan_start = event.xdata
            
    def on_mouse_release(self, event):
        """鼠标释放事件处理"""
        if event.inaxes != self.ax and not self.dragging:
            return
            
        if event.button == 1:  # 左键
            self.dragging = False
            if self.selection_start:
                x_start = self.selection_start[0]
                x_end = event.xdata
                
                # 确保起点小于终点
                x_min = min(x_start, x_end)
                x_max = max(x_start, x_end)
                
                # 选择范围内的点
                self.selected_points = [i for i, x in enumerate(self.x_data)
                                     if x_min <= x <= x_max]
                                     
                # 发送选中点信号
                self.data_selected.emit(self.selected_points)
                
                # 更新图表
                self._update_plot()
                
            self.selection_start = None
        elif event.button == 3:  # 右键
            self.pan_start = None
            
    def on_mouse_move(self, event):
        """鼠标移动事件处理"""
        if event.inaxes != self.ax:
            return
            
        if self.dragging and self.selection_start:
            self._handle_selection_drag(event)
        elif self.pan_start is not None:
            self._handle_pan_drag(event)
        elif not self.dragging and not self.selected_points:
            self._handle_hover(event)
            
    def _handle_selection_drag(self, event):
        """处理选择区域拖拽"""
        if event.xdata is None:
            return
            
        x_start = min(self.selection_start[0], event.xdata)
        x_end = max(self.selection_start[0], event.xdata)
        
        # 清除之前的选择矩形
        self._clear_selection_rectangle()
        
        # 绘制新的选择矩形
        import matplotlib.patches as patches
        rect = patches.Rectangle(
            (x_start, self.ax.get_ylim()[0]),
            x_end - x_start,
            self.ax.get_ylim()[1] - self.ax.get_ylim()[0],
            facecolor='yellow',
            alpha=0.2,
            zorder=1
        )
        self.ax.add_patch(rect)
        
        # 预览选中的点
        selected_indices = [i for i, x in enumerate(self.x_data)
                          if x_start <= x <= x_end]
        if selected_indices:
            selected_x = [self.x_data[i] for i in selected_indices]
            selected_y = [self.data[i] for i in selected_indices]
            # 清除之前的散点
            for collection in self.ax.collections:
                collection.remove()
            # 绘制新的散点
            self.ax.scatter(selected_x, selected_y, 
                          color='red', s=50, zorder=3)
        
        self.canvas.draw()
        
    def _handle_hover(self, event):
        """处理悬停效果"""
        if self.line and not self.selected_points:  # 只在没有选中点时处理悬停
            cont, ind = self.line.contains(event)
            if cont:
                point_index = ind["ind"][0]
                self._show_point_info(point_index)
                # 发送悬停点变化信号
                self.hover_point_changed.emit(point_index)
                
    def _show_point_info(self, index):
        """显示数据点信息"""
        if not (0 <= index < len(self.data)):
            return
            
        value = self.data[index]
        
        # 移除旧的标注
        for artist in self.ax.texts:
            artist.remove()
            
        # 添加新的标注
        self.ax.annotate(
            f'点 {index}\n值: {value}',
            xy=(self.x_data[index], value),
            xytext=(10, 10),
            textcoords='offset points',
            **PlotStyle.HOVER_ANNOTATION_STYLE
        )
        
        # 重绘
        self.canvas.draw()

    def find_patterns(self):
        """查找相似模式"""
        if not self.selected_points:
            return
            
        # 获取相似度阈值
        threshold, ok = QInputDialog.getDouble(
            self, "设置阈值", "请输入模式相似度阈值 (0-1):", 0.1, 0, 1, 2)
        if not ok:
            return
            
        # 查找相似模式
        similar_positions = self.data_manager.find_similar_patterns(
            [self.data_manager.data[i] for i in self.selected_points],
            threshold
        )
        
        # 高亮显示相似模式
        self.ax.clear()
        
        # 绘制主线
        self.line, = self.ax.plot(
            self.x_data, 
            self.data, 
            'b-', 
            linewidth=1
        )
        
        # 高亮显示参考模式
        ref_x = [self.x_data[i] for i in self.selected_points]
        ref_y = [self.data[i] for i in self.selected_points]
        self.ax.plot(ref_x, ref_y, 
                     'r-', linewidth=2, 
                     label='参考模式')
        
        # 高亮显示相似模式
        pattern_length = len(self.selected_points)
        for pos in similar_positions:
            if pos != self.selected_points[0]:  # 排除参考模式本身
                x = self.x_data[pos:pos+pattern_length]
                y = self.data[pos:pos+pattern_length]
                self.ax.plot(x, y, 
                            color='#FF00FF',  # 洋红色
                            linewidth=2, alpha=0.7)
                
        # 添加图例
        self.ax.legend()
        
        # 重绘
        self.canvas.draw() 

    def toggle_grid(self):
        """切换网格显示状态"""
        self.grid_on = not self.grid_on
        self._update_plot()
        
    def toggle_points(self):
        """切换数据点显示状态"""
        self.show_points = not self.show_points
        self._update_plot() 

    def on_scroll(self, event):
        """鼠标滚轮事件处理"""
        if event.inaxes != self.ax:
            return
            
        self._handle_zoom(event)
        
    def _handle_zoom(self, event):
        """处理缩放"""
        # 修改缩放因子：向前滚动放大，向后滚动缩小
        factor = 0.9 if event.button == 'up' else 1.1
        
        # 获取当前视图范围
        cur_xlim = self.ax.get_xlim()
        
        # 计算鼠标位置相对于视图的比例
        xdata = event.xdata
        cur_width = cur_xlim[1] - cur_xlim[0]
        rel_pos = (xdata - cur_xlim[0]) / cur_width
        
        # 计算新的视图范围
        new_width = cur_width * factor
        new_left = xdata - rel_pos * new_width
        new_right = new_left + new_width
        
        # 限制缩放范围
        if len(self.data) > 0:
            min_x = min(self.x_data) - 1
            max_x = max(self.x_data) + 1
            if new_left < min_x:
                new_left = min_x
            if new_right > max_x:
                new_right = max_x
                
        # 应用新的范围
        self.ax.set_xlim(new_left, new_right)
        self.canvas.draw()
        
    def on_key_press(self, event):
        """键盘事件处理"""
        key_handlers = {
            'p': self.toggle_points,
            'g': self.toggle_grid,
        }
        
        if event.key in key_handlers:
            key_handlers[event.key]()
            
    def export_png(self, filename):
        """导出为PNG图片"""
        try:
            self.fig.savefig(filename, dpi=300, bbox_inches='tight')
            return True
        except Exception as e:
            print(f"导出图片失败: {e}")
            return False
            
    def get_statistics(self):
        """获取数据统计信息"""
        if not self.data:
            return {}
            
        return {
            'count': len(self.data),
            'mean': np.mean(self.data),
            'std': np.std(self.data),
            'min': min(self.data),
            'max': max(self.data),
            'selected_count': len(self.selected_points),
            'selected_mean': np.mean([self.data[i] for i in self.selected_points]) if self.selected_points else None
        } 

    def _clear_selection_rectangle(self):
        """清除选择矩形"""
        for patch in self.ax.patches:
            patch.remove() 

    def dragEnterEvent(self, event):
        """拖入事件处理"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith('.txt'):
                    event.acceptProposedAction()
                    return
                    
    def dropEvent(self, event):
        """放下事件处理"""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith('.txt'):
                self.load_data_file(file_path)
                event.acceptProposedAction()
                return
                
    def load_data_file(self, file_path):
        """加载数据文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = []
                for line in f:
                    try:
                        value = float(line.strip())
                        data.append(value)
                    except ValueError:
                        continue
                        
            if data:
                self.set_data(data)
                
        except Exception as e:
            print(f"加载文件失败: {e}") 