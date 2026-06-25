import json
import os
from typing import Dict, Any

class Config:
    def __init__(self):
        """初始化配置管理器，设置默认配置并加载配置文件。
    
        功能：
            1. 设置配置文件路径
            2. 定义包含绘图、数据、界面和分析模块的默认配置字典
            3. 创建配置的浅拷贝作为当前运行配置
            4. 从配置文件加载配置（覆盖默认值）
    
        参数：
            self: 类实例本身
    
        返回值：
            无（构造函数无返回值）
        """
        self.config_file = "config.json"  # 配置文件路径
        self.default_config = {
            "plot": {  # 绘图相关配置
                "show_grid": True,  # 是否显示网格线
                "show_points": False,  # 是否显示数据点
                "line_width": 1,  # 线条宽度
                "line_color": "blue",  # 线条颜色
                "point_size": 50,  # 数据点大小
                "point_color": "red",  # 数据点颜色
                "animation_duration": 0.5  # 动画持续时间（秒）
            },
            "data": {  # 数据处理相关配置
                "auto_save": True,  # 是否启用自动保存
                "auto_save_interval": 300,  # 自动保存间隔时间（秒）
                "max_history": 100,  # 最大历史记录数
                "default_save_format": "txt"  # 默认文件保存格式
            },
            "ui": {  # 用户界面相关配置
                "window_width": 1200,  # 窗口宽度（像素）
                "window_height": 800,  # 窗口高度（像素）
                "splitter_ratio": 0.7,  # 分割器比例
                "theme": "light"  # 界面主题（浅色/深色）
            },
            "analysis": {  # 数据分析相关配置
                "peak_threshold": 0.0,  # 波峰检测阈值
                "valley_threshold": 0.0,  # 波谷检测阈值
                "pattern_similarity_threshold": 0.1  # 模式相似度阈值
            }
        }
        # 创建默认配置的浅拷贝作为运行时配置
        self.config = self.default_config.copy()
        # 从配置文件加载配置，覆盖默认值
        self.load_config()
        
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # 递归更新配置
                    self._update_config(self.config, loaded_config)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            
    def save_config(self) -> None:
        """保存配置文件"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """获取配置项"""
        try:
            return self.config[section][key]
        except KeyError:
            return default
            
    def set(self, section: str, key: str, value: Any) -> None:
        """设置配置项"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save_config()
        
    def reset(self, section: str = None) -> None:
        """重置配置"""
        if section:
            if section in self.default_config:
                self.config[section] = self.default_config[section].copy()
        else:
            self.config = self.default_config.copy()
        self.save_config()
        
    def _update_config(self, target: Dict, source: Dict) -> None:
        """递归更新配置字典"""
        for key, value in source.items():
            if key in target:
                if isinstance(value, dict) and isinstance(target[key], dict):
                    self._update_config(target[key], value)
                else:
                    target[key] = value 