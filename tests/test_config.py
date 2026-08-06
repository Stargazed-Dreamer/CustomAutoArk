"""ConfigManager 单元测试

覆盖 config.py 中 ConfigManager 类的配置加载、保存、合并默认值、
便捷访问方法等行为。ConfigManager 继承 dict，顶部仅依赖 os/logging/yaml，
不涉及 cv2/paddleocr/PySide6/log 模块，可在 conftest 的 mock 环境下直接运行。

测试使用 tmp_path fixture 创建临时 yaml 文件，避免污染项目根的 config.yaml；
另有专门用例加载真实 config.yaml 验证集成。
"""
import os

import pytest

from config import ConfigManager, DEFAULT_CONFIG


_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_CONFIG = os.path.join(_PROJECT_ROOT, "config.yaml")


# ==================== load ====================

class TestLoad:
    """load() 方法测试"""

    def test_missing_file_uses_defaults(self, tmp_path):
        """配置文件不存在时不报错，使用默认值"""
        cfg = ConfigManager(config_path=str(tmp_path / "nonexistent.yaml"))
        # 顶层标量默认值
        assert cfg.get('adb_path') == DEFAULT_CONFIG['adb_path']
        assert cfg.get('record_path') == DEFAULT_CONFIG['record_path']
        assert cfg.get('save_interval') == DEFAULT_CONFIG['save_interval']
        # 子字典默认值
        assert cfg.get_simulator()['port'] == DEFAULT_CONFIG['simulator']['port']
        assert cfg.get_data()['data_file'] == DEFAULT_CONFIG['data']['data_file']

    def test_empty_file_uses_defaults(self, tmp_path):
        """空配置文件使用默认值"""
        p = tmp_path / "empty.yaml"
        p.write_text("", encoding="utf-8")
        cfg = ConfigManager(config_path=str(p))
        assert cfg.get('adb_path') == DEFAULT_CONFIG['adb_path']
        assert cfg.get_simulator() == DEFAULT_CONFIG['simulator']

    def test_partial_config_merges_defaults(self, tmp_path):
        """部分配置缺失时用默认值补全（浅合并每个子字典）"""
        p = tmp_path / "partial.yaml"
        p.write_text(
            "simulator:\n  port: 5555\n"  # 只设置 port，adb_path 缺失
            "adb_path: /custom/adb\n",
            encoding="utf-8"
        )
        cfg = ConfigManager(config_path=str(p))
        # 用户设置生效
        assert cfg.get_simulator()['port'] == 5555
        assert cfg.get('adb_path') == '/custom/adb'
        # 缺失的子键用默认值补全
        assert cfg.get_simulator()['adb_path'] == DEFAULT_CONFIG['simulator']['adb_path']
        # 完全缺失的子字典用默认值
        assert cfg.get_log() == DEFAULT_CONFIG['log']
        assert cfg.get_plot() == DEFAULT_CONFIG['plot']
        assert cfg.get_data() == DEFAULT_CONFIG['data']

    def test_load_real_config(self):
        """加载项目根的真实 config.yaml 不报错"""
        cfg = ConfigManager(config_path=_PROJECT_CONFIG)
        # 真实 config.yaml 中 simulator.port 为 7555
        assert cfg.get_port() == 7555
        # record_path 应为 #record.txt
        assert cfg.get('record_path') == '#record.txt'
        # adb_path 为非空字符串
        assert isinstance(cfg.get_adb_path(), str)

    def test_extra_keys_preserved(self, tmp_path):
        """加载配置中存在但默认配置中没有的键被保留"""
        p = tmp_path / "extra.yaml"
        p.write_text("custom_key: custom_value\n", encoding="utf-8")
        cfg = ConfigManager(config_path=str(p))
        assert cfg.get('custom_key') == 'custom_value'


# ==================== save / load 一致性 ====================

class TestSaveLoad:
    """save() 与 load() 一致性测试"""

    def test_save_then_load_consistent(self, tmp_path):
        """save 后再 load 数据一致"""
        p = tmp_path / "roundtrip.yaml"
        cfg = ConfigManager(config_path=str(p))
        cfg['adb_path'] = '/test/adb'
        cfg['simulator']['port'] = 1234
        cfg['custom_field'] = 'hello'
        assert cfg.save() is True

        cfg2 = ConfigManager(config_path=str(p))
        assert cfg2.get('adb_path') == '/test/adb'
        assert cfg2.get_simulator()['port'] == 1234
        assert cfg2.get('custom_field') == 'hello'

    def test_save_returns_true_on_success(self, tmp_path):
        """保存成功返回 True，且文件被创建"""
        p = tmp_path / "save_test.yaml"
        cfg = ConfigManager(config_path=str(p))
        assert cfg.save() is True
        assert p.exists()

    def test_save_preserves_unicode(self, tmp_path):
        """保存含中文的配置后 load 仍可读回（allow_unicode=True）"""
        p = tmp_path / "unicode.yaml"
        cfg = ConfigManager(config_path=str(p))
        cfg['record_path'] = '记录.txt'
        cfg.save()
        cfg2 = ConfigManager(config_path=str(p))
        assert cfg2.get('record_path') == '记录.txt'


# ==================== 便捷访问方法 ====================

class TestGetters:
    """get_simulator / get_log / get_data / get_plot 返回字典测试"""

    def test_get_simulator_returns_dict(self, tmp_path):
        """get_simulator 返回字典"""
        cfg = ConfigManager(config_path=str(tmp_path / "no.yaml"))
        assert isinstance(cfg.get_simulator(), dict)

    def test_get_log_returns_dict(self, tmp_path):
        """get_log 返回字典"""
        cfg = ConfigManager(config_path=str(tmp_path / "no.yaml"))
        assert isinstance(cfg.get_log(), dict)

    def test_get_data_returns_dict(self, tmp_path):
        """get_data 返回字典"""
        cfg = ConfigManager(config_path=str(tmp_path / "no.yaml"))
        assert isinstance(cfg.get_data(), dict)

    def test_get_plot_returns_dict(self, tmp_path):
        """get_plot 返回字典"""
        cfg = ConfigManager(config_path=str(tmp_path / "no.yaml"))
        assert isinstance(cfg.get_plot(), dict)


# ==================== get_adb_path 优先级 ====================

class TestAdbPath:
    """get_adb_path 优先级测试：simulator.adb_path > 顶层 adb_path"""

    def test_simulator_adb_path_takes_priority(self, tmp_path):
        """simulator.adb_path 优先于顶层 adb_path"""
        p = tmp_path / "adb.yaml"
        p.write_text(
            "adb_path: /top/adb\n"
            "simulator:\n  adb_path: /sim/adb\n  port: 7555\n",
            encoding="utf-8"
        )
        cfg = ConfigManager(config_path=str(p))
        assert cfg.get_adb_path() == '/sim/adb'

    def test_fallback_to_top_adb_path(self, tmp_path):
        """simulator.adb_path 为空时回退到顶层 adb_path"""
        p = tmp_path / "adb.yaml"
        p.write_text(
            "adb_path: /top/adb\n"
            "simulator:\n  adb_path: ''\n  port: 7555\n",
            encoding="utf-8"
        )
        cfg = ConfigManager(config_path=str(p))
        assert cfg.get_adb_path() == '/top/adb'

    def test_both_empty_returns_empty(self, tmp_path):
        """两者都为空时返回空字符串"""
        cfg = ConfigManager(config_path=str(tmp_path / "no.yaml"))
        assert cfg.get_adb_path() == ''


# ==================== get_port / get_record_path 默认值 ====================

class TestPortAndRecord:
    """get_port / get_record_path 默认值测试"""

    def test_default_port(self, tmp_path):
        """未设置 port 时默认 7555"""
        cfg = ConfigManager(config_path=str(tmp_path / "no.yaml"))
        assert cfg.get_port() == 7555

    def test_custom_port(self, tmp_path):
        """自定义 port 生效"""
        p = tmp_path / "port.yaml"
        p.write_text("simulator:\n  port: 1234\n", encoding="utf-8")
        cfg = ConfigManager(config_path=str(p))
        assert cfg.get_port() == 1234

    def test_default_record_path(self, tmp_path):
        """未设置 record_path 时默认 #record.txt"""
        cfg = ConfigManager(config_path=str(tmp_path / "no.yaml"))
        assert cfg.get_record_path() == '#record.txt'

    def test_custom_record_path(self, tmp_path):
        """自定义 record_path 生效"""
        p = tmp_path / "rec.yaml"
        p.write_text("record_path: /custom/record.txt\n", encoding="utf-8")
        cfg = ConfigManager(config_path=str(p))
        assert cfg.get_record_path() == '/custom/record.txt'
