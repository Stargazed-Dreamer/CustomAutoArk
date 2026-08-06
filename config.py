"""配置管理器模块

提供对 config.yaml 的统一访问接口，支持类型化取值和默认值。

## 设计说明
- ConfigManager 继承 dict，完全向后兼容现有的 `g.config['log']` 等访问方式
- 额外提供 get_simulator() / get_log() / get_data() / get_plot() 等便捷方法
- 每个便捷方法都带有默认值，避免 KeyError

## 使用示例
```python
from config import config_manager

# dict 方式访问（向后兼容）
adb_path = config_manager.get('adb_path', '')

# 类型化访问
sim = config_manager.get_simulator()
port = sim.get('port', 7555)

# 修改并保存
config_manager['simulator']['port'] = 7555
config_manager.save()
```

## 与现有代码的关系
- log.py 的 LogManager.load_config() / save_config() 仍可独立使用
- main_window.py 中 `g.config = log_manager.load_config()` 可改为 `g.config = config_manager`
- settings.py 中 `g.config` 的读写操作无需修改（dict 兼容）
"""

import os
import logging

import yaml


# ==================== 默认配置 ====================

DEFAULT_CONFIG = {
    # ADB 配置
    'adb_path': '',
    'addr': '',

    # 日志配置
    'log': {
        'console_enabled': True,
        'console_level': logging.INFO,      # 20
        'file_enabled': False,
        'file_level': logging.DEBUG,        # 10
        'image_enabled': False,
        'log_dir': 'log',
        'cleanup_days': 30,
    },

    # 模拟器配置
    'simulator': {
        'adb_path': '',
        'port': 7555,
    },

    # 数据配置
    'data': {
        'auto_save': False,
        'auto_save_interval': 10,
        'data_file': '#record.txt',
    },

    # 绘图配置
    'plot': {
        'line_width': 1,
        'point_size': 3,
        'show_grid': True,
        'show_points': True,
        'smooth_factor': 0.5,
    },

    # 其他
    'record_path': '#record.txt',
    'save_interval': 3000,
    'log_path': 'log',
}


class ConfigManager(dict):
    """配置管理器

    继承 dict 以保证向后兼容，同时提供便捷的类型化访问方法。
    """

    def __init__(self, config_path='config.yaml'):
        super().__init__()
        self.config_path = config_path
        self.load()

    def load(self):
        """从 config.yaml 加载配置，合并默认值"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded = yaml.safe_load(f) or {}
        except FileNotFoundError:
            loaded = {}
        except Exception:
            loaded = {}

        # 合并默认配置（浅合并每个子字典）
        merged = {}
        for key, default_val in DEFAULT_CONFIG.items():
            if isinstance(default_val, dict):
                merged[key] = {**default_val, **(loaded.get(key, {}) or {})}
            else:
                merged[key] = loaded.get(key, default_val)

        # 也保留加载配置中存在但默认配置中没有的键
        for key, val in loaded.items():
            if key not in merged:
                merged[key] = val

        self.clear()
        self.update(merged)
        return self

    def save(self):
        """保存配置到 config.yaml"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(dict(self), f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    # ==================== 便捷访问方法 ====================

    def get_simulator(self) -> dict:
        """获取模拟器配置"""
        return self.get('simulator', DEFAULT_CONFIG['simulator'])

    def get_log(self) -> dict:
        """获取日志配置"""
        return self.get('log', DEFAULT_CONFIG['log'])

    def get_data(self) -> dict:
        """获取数据配置"""
        return self.get('data', DEFAULT_CONFIG['data'])

    def get_plot(self) -> dict:
        """获取绘图配置"""
        return self.get('plot', DEFAULT_CONFIG['plot'])

    def get_adb_path(self) -> str:
        """获取 ADB 路径（优先 simulator.adb_path，其次顶层 adb_path）"""
        sim_path = self.get_simulator().get('adb_path', '')
        if sim_path:
            return sim_path
        return self.get('adb_path', '')

    def get_port(self) -> int:
        """获取模拟器端口"""
        return self.get_simulator().get('port', 7555)

    def get_record_path(self) -> str:
        """获取数据记录文件路径"""
        return self.get('record_path', self.get_data().get('data_file', '#record.txt'))


# 模块级单例
config_manager = ConfigManager()
