"""
数据管理器 (DataManager)
这个模块提供了数据的管理、分析和持久化功能。

主要功能：
1. 数据操作：
   - 加载和保存数据文件
   - 更新和修改数据点
   - 删除数据点
   - 导出数据为PNG图片

2. 数据分析：
   - 查找波峰波谷
   - 查找相似数据模式
   - 计算统计信息

3. 历史记录：
   - 支持撤销/重做操作
   - 自动维护操作历史
   - 限制历史记录长度

主要接口：
- load_data(file_path): 加载数据文件
- save_data(file_path): 保存数据到文件
- update_data(data): 更新数据
- modify_points(indices, values): 修改指定点
- delete_points(indices): 删除指定点
- find_peaks(threshold): 查找波峰
- find_valleys(threshold): 查找波谷
- find_similar_patterns(pattern, threshold): 查找相似模式
- get_statistics(indices): 获取统计信息
- undo(): 撤销操作
- redo(): 重做操作

类型提示：
所有方法都提供了类型提示，支持静态类型检查
"""

import numpy as np
from typing import List, Tuple, Optional
import json
import os

class DataManager:
    def __init__(self):
        self.data: List[float] = []
        self.file_path: Optional[str] = None
        self.history: List[List[float]] = []
        self.history_index: int = -1
        
    def load_data(self, file_path: str) -> bool:
        """加载数据文件"""
        try:
            with open(file_path, 'r') as f:
                self.data = [float(line.strip()) for line in f if line.strip()]
            self.file_path = file_path
            self._add_to_history()
            return True
        except Exception as e:
            print(f"加载数据失败: {e}")
            return False
            
    def save_data(self, file_path: Optional[str] = None) -> bool:
        """保存数据到文件"""
        try:
            save_path = file_path or self.file_path
            if not save_path:
                return False
                
            with open(save_path, 'w') as f:
                for value in self.data:
                    f.write(f"{value}\n")
            return True
        except Exception as e:
            print(f"保存数据失败: {e}")
            return False
            
    def export_png(self, file_path: str) -> bool:
        """导出为PNG图片"""
        try:
            import matplotlib.pyplot as plt
            plt.figure(figsize=(12, 6))
            plt.plot(self.data)
            plt.grid(True)
            plt.savefig(file_path)
            plt.close()
            return True
        except Exception as e:
            print(f"导出PNG失败: {e}")
            return False
            
    def update_data(self, data: List[float]) -> None:
        """更新数据"""
        self.data = data.copy()
        self._add_to_history()
        
    def modify_points(self, indices: List[int], values: List[float]) -> None:
        """修改指定位置的数据点"""
        if len(indices) != len(values):
            return
            
        for idx, value in zip(indices, values):
            if 0 <= idx < len(self.data):
                self.data[idx] = value
                
        self._add_to_history()
        
    def delete_points(self, indices: List[int]) -> None:
        """删除指定位置的数据点"""
        indices = sorted(indices, reverse=True)
        for idx in indices:
            if 0 <= idx < len(self.data):
                self.data.pop(idx)
                
        self._add_to_history()
        
    def find_peaks(self, threshold: float = 0.0) -> List[int]:
        """查找波峰"""
        peaks = []
        for i in range(1, len(self.data) - 1):
            if (self.data[i] > self.data[i-1] and 
                self.data[i] > self.data[i+1] and 
                self.data[i] > threshold):
                peaks.append(i)
        return peaks
        
    def find_valleys(self, threshold: float = 0.0) -> List[int]:
        """查找波谷"""
        valleys = []
        for i in range(1, len(self.data) - 1):
            if (self.data[i] < self.data[i-1] and 
                self.data[i] < self.data[i+1] and 
                self.data[i] < threshold):
                valleys.append(i)
        return valleys
        
    def find_similar_patterns(self, pattern: List[float], 
                            threshold: float = 0.1) -> List[int]:
        """查找相似模式"""
        if not pattern or len(pattern) > len(self.data):
            return []
            
        pattern = np.array(pattern)
        pattern = (pattern - np.mean(pattern)) / np.std(pattern)
        
        similar_positions = []
        window_size = len(pattern)
        
        for i in range(len(self.data) - window_size + 1):
            window = np.array(self.data[i:i+window_size])
            window = (window - np.mean(window)) / np.std(window)
            
            # 计算相关系数
            correlation = np.corrcoef(pattern, window)[0, 1]
            if correlation > (1 - threshold):
                similar_positions.append(i)
                
        return similar_positions
        
    def get_statistics(self, indices: Optional[List[int]] = None) -> dict:
        """获取统计信息"""
        if indices is None:
            data = self.data
        else:
            data = [self.data[i] for i in indices if 0 <= i < len(self.data)]
            
        if not data:
            return {}
            
        return {
            "count": len(data),
            "mean": np.mean(data),
            "std": np.std(data),
            "min": np.min(data),
            "max": np.max(data),
            "median": np.median(data)
        }
        
    def undo(self) -> bool:
        """撤销操作"""
        if self.history_index > 0:
            self.history_index -= 1
            self.data = self.history[self.history_index].copy()
            return True
        return False
        
    def redo(self) -> bool:
        """重做操作"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.data = self.history[self.history_index].copy()
            return True
        return False
        
    def _add_to_history(self) -> None:
        """添加当前状态到历史记录"""
        # 删除当前位置之后的历史记录
        self.history = self.history[:self.history_index + 1]
        
        # 添加新的状态
        self.history.append(self.data.copy())
        self.history_index = len(self.history) - 1
        
        # 限制历史记录长度
        max_history = 100
        if len(self.history) > max_history:
            self.history = self.history[-max_history:]
            self.history_index = len(self.history) - 1 