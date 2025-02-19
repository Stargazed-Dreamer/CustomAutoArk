import json
import os
from typing import Dict, Any

class Config:
    def __init__(self):
        self.config_file = "config.json"
        self.default_config = {
            "plot": {
                "show_grid": True,
                "show_points": False,
                "line_width": 1,
                "line_color": "blue",
                "point_size": 50,
                "point_color": "red",
                "animation_duration": 0.5
            },
            "data": {
                "auto_save": True,
                "auto_save_interval": 300,  # 秒
                "max_history": 100,
                "default_save_format": "txt"
            },
            "ui": {
                "window_width": 1200,
                "window_height": 800,
                "splitter_ratio": 0.7,
                "theme": "light"
            },
            "analysis": {
                "peak_threshold": 0.0,
                "valley_threshold": 0.0,
                "pattern_similarity_threshold": 0.1
            }
        }
        self.config = self.default_config.copy()
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