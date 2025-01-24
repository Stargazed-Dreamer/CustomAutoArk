"""
绘图工具函数集 (plot_utils)
这个模块提供了一系列用于增强图表功能的工具函数。

主要功能：
1. 曲线处理：
   - create_smooth_line: 创建平滑曲线
   - create_gradient_line: 创建渐变色线条

2. 动画效果：
   - create_zoom_animation: 创建缩放动画效果

3. 数据分析：
   - highlight_similar_points: 高亮显示相似的数据点

4. 图表注释：
   - add_annotations: 添加文本标注
   - add_grid: 添加网格线

所有函数都提供了类型提示和详细的参数说明，支持现代Python的类型检查。
"""

import numpy as np
from typing import List, Tuple, Optional
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.animation import Animation

def create_smooth_line(x: List[float], y: List[float], 
                      smoothing: float = 0.5) -> Tuple[List[float], List[float]]:
    """创建平滑曲线"""
    if len(x) < 3:
        return x, y
        
    # 使用三次样条插值
    from scipy.interpolate import make_interp_spline
    x_new = np.linspace(min(x), max(x), int(len(x) * (1 + smoothing)))
    spl = make_interp_spline(x, y, k=3)
    y_new = spl(x_new)
    
    return x_new.tolist(), y_new.tolist()

def create_zoom_animation(ax, x_range: Tuple[float, float], 
                        y_range: Tuple[float, float], 
                        duration: float = 0.5) -> Animation:
    """创建缩放动画"""
    from matplotlib.animation import FuncAnimation
    
    # 获取当前视图范围
    x_start, x_end = ax.get_xlim()
    y_start, y_end = ax.get_ylim()
    
    # 计算步长
    frames = 20
    x_step = (x_range[1] - x_range[0] - (x_end - x_start)) / frames
    y_step = (y_range[1] - y_range[0] - (y_end - y_start)) / frames
    
    def update(frame):
        ax.set_xlim(x_start + frame * x_step, 
                   x_end + frame * x_step)
        ax.set_ylim(y_start + frame * y_step, 
                   y_end + frame * y_step)
        
    return FuncAnimation(ax.figure, update, 
                        frames=frames, 
                        interval=duration * 1000 / frames)

def highlight_similar_points(ax, data: List[float], 
                           reference_indices: List[int], 
                           threshold: float = 0.1) -> None:
    """高亮显示相似的数据点"""
    if not reference_indices:
        return
        
    # 获取参考模式
    pattern = [data[i] for i in reference_indices]
    pattern = np.array(pattern)
    pattern = (pattern - np.mean(pattern)) / np.std(pattern)
    
    # 查找相似模式
    window_size = len(pattern)
    similar_positions = []
    
    for i in range(len(data) - window_size + 1):
        window = np.array(data[i:i+window_size])
        window = (window - np.mean(window)) / np.std(window)
        
        correlation = np.corrcoef(pattern, window)[0, 1]
        if correlation > (1 - threshold):
            similar_positions.extend(range(i, i + window_size))
            
    # 高亮显示
    x = list(range(len(data)))
    ax.scatter([x[i] for i in similar_positions],
              [data[i] for i in similar_positions],
              color='yellow', alpha=0.3, s=50)

def add_annotations(ax, x: List[float], y: List[float], 
                   indices: List[int], texts: List[str]) -> None:
    """添加文本标注"""
    for idx, text in zip(indices, texts):
        if 0 <= idx < len(x):
            ax.annotate(text,
                       xy=(x[idx], y[idx]),
                       xytext=(10, 10),
                       textcoords='offset points',
                       ha='left',
                       va='bottom',
                       bbox=dict(boxstyle='round,pad=0.5',
                               fc='yellow',
                               alpha=0.3),
                       arrowprops=dict(arrowstyle='->',
                                     connectionstyle='arc3,rad=0'))

def create_gradient_line(x: List[float], y: List[float], 
                        cmap: str = 'viridis') -> None:
    """创建渐变色线条"""
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    
    # 计算梯度
    values = np.gradient(y)
    norm = plt.Normalize(values.min(), values.max())
    
    # 创建渐变色线条集合
    from matplotlib.collections import LineCollection
    lc = LineCollection(segments, cmap=cmap, norm=norm)
    lc.set_array(values)
    
    return lc

def add_grid(ax, major: bool = True, minor: bool = False, 
             style: str = '--', alpha: float = 0.3) -> None:
    """添加网格线"""
    ax.grid(which='major' if major else 'both',
           linestyle=style,
           alpha=alpha)
    if minor:
        ax.minorticks_on()
        ax.grid(which='minor',
               linestyle=':',
               alpha=alpha/2) 