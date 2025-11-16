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

类型提示：
所有方法都提供了类型提示，支持静态类型检查
"""
from typing import List, Tuple, Optional

import numpy as np

from data import data as DATA
from log import log_manager

class DataManager:
    def __init__(self):
        self.real_data = []  # 原始数据（干员/tag字符串列表）
        self.data = []       # 转换后的数值数据
        self.file_path = None
        
    def load_data(self, file_path: str) -> bool:
        """加载数据文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.real_data += [x for x in f.read().split("\n") if x != ""]
            self.data += self.data_convert(self.real_data)
            self.file_path = file_path
            return True
        except Exception as e:
            log_manager.error(f"加载数据失败: {e}")
            return False
            
    def save_data(self, file_path: Optional[str] = None) -> bool:
        """保存数据到文件"""
        try:
            save_path = file_path or self.file_path
            if not save_path:
                return False
                
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.real_data))
            return True
        except Exception as e:
            log_manager.error(f"保存数据失败: {e}")
            return False
    
    def data_convert(self, raw_data: list) -> list:
        """将原始数据转换为数值数据"""
        output = []
        for data in raw_data:
            if data == "":
                continue
            if "!" in data:
                #TODO:(!！暂时直接放的tag优先级！!)
                tags = data.split("!")
                sum_value = sum(DATA.getTagPriority(tag) for tag in tags)
                output.append(sum_value)
            elif data in DATA.d_agent:
                #TODO:(!！暂时直接放的干员星级！!)
                output.append(int(DATA.d_agent[data]['star']))
            elif data.replace("#", "").replace("?", "").replace("？", "").isdigit():
                output.append(int(data.replace("#", "").replace("?", "").replace("？", "")))
            else:
                raise ValueError(f"无效数据: {data}")
        return output

    def set_data(self, new_data):
        if isinstance(new_data, str):
            if new_data == "":
                self._set_data([])
            elif "\n" in new_data:
                self._set_data(new_data.strip("\n").split("\n"))
            else:
                self._set_data([new_data])
        elif isinstance(new_data, list):
            self._set_data(new_data)
        else:
            raise ValueError("无效数据")

    def _set_data(self, new_data: list) -> None:
        """设置新的原始数据"""
        self.real_data = new_data
        self.data = self.data_convert(self.real_data)

    def update_data(self, new_data):
        if isinstance(new_data, str):
            if new_data == "":
                return
            elif "\n" in new_data:
                self._update_data(new_data.strip("\n").split("\n"))
            else:
                self._update_data([new_data])
        elif isinstance(new_data, list):
            self._update_data(new_data)
        else:
            raise ValueError("无效数据")

    def _update_data(self, new_data: list) -> None:
        """更新数据"""
        self.real_data += new_data
        self.data = self.data_convert(self.real_data)

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
            log_manager.error(f"导出PNG失败: {e}")
            return False

    def find_peaks(self) -> tuple:
        """查找波峰波谷"""
        peaks = []
        valleys = []
        
        if len(self.data) < 3:
            return peaks, valleys
            
        for i in range(1, len(self.data) - 1):
            # 查找波峰
            if (self.data[i] > self.data[i-1] and 
                self.data[i] > self.data[i+1]):
                peaks.append(i)
            # 查找波谷
            if (self.data[i] < self.data[i-1] and 
                self.data[i] < self.data[i+1]):
                valleys.append(i)
                
        return peaks, valleys

    def normalize(self, series):
        """Z-score归一化"""
        mean = np.mean(series)
        std = np.std(series)
        if std == 0:
            return [0] * len(series)
        return [(x - mean)/std for x in series]

    def dtw_distance(self, ts_a, ts_b):
        """计算两个时间序列的DTW距离"""
        ts_a = self.normalize(ts_a)
        ts_b = self.normalize(ts_b)
        n, m = len(ts_a), len(ts_b)
        dtw_matrix = np.full((n+1, m+1), np.inf)
        dtw_matrix[0, 0] = 0
        
        for i in range(1, n+1):
            for j in range(1, m+1):
                cost = abs(ts_a[i-1] - ts_b[j-1])
                dtw_matrix[i, j] = cost + min(
                    dtw_matrix[i-1, j],    # 插入
                    dtw_matrix[i, j-1],    # 删除
                    dtw_matrix[i-1, j-1]   # 匹配
                )
        return dtw_matrix[n, m]

    def find_patterns(self, pattern_length: int = 5, threshold: float = 0.8) -> list:
        """查找相似模式
        Args:
            pattern_length: 模式长度
            threshold: 相似度阈值 (0-1)
        Returns:
            相似模式的起始位置列表 [(start1, start2), ...]
        """
        if len(self.data) < pattern_length * 2:
            return []

        patterns = []
        for i in range(len(self.data) - pattern_length):
            pattern = self.data[i:i+pattern_length]
            
            for j in range(i + pattern_length, len(self.data) - pattern_length):
                compare = self.data[j:j+pattern_length]
                
                # 计算DTW距离
                dist = self.dtw_distance(pattern, compare)
                
                # 将DTW距离转换为相似度分数 (0-1)
                similarity = 1 / (1 + dist)
                
                if similarity >= threshold:
                    patterns.append((i, j))
                    
                    # 避免重复添加相邻的模式
                    j += pattern_length
        
        return patterns

    def get_statistics(self, start: int = None, end: int = None) -> dict:
        """获取统计信息"""
        data = self.data[start:end] if start is not None and end is not None else self.data
        if not data:
            return {}
            
        n = len(data)
        mean = sum(data) / n
            
        return {
            "数据点数": n,
            "平均值": mean,
            "六星数量": sum(1 for x in data if x == 6),
            "五星数量": sum(1 for x in data if x == 5),
        }

data_manager = DataManager()