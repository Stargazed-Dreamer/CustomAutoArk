import inspect
import os
import logging
import yaml
from datetime import datetime, timedelta
from PySide6.QtCore import QObject, Signal
import cv2

class LogManager(QObject):
    # 信号定义
    log_message = Signal(str)  # 日志消息信号
    step_message = Signal(str, bool)  # 步骤消息信号，bool表示是否为错误
    log_settings_changed = Signal(dict)  # 日志设置变更信号
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('ArknightsLogger')
        self.logger.setLevel(logging.DEBUG)
        
        # 加载配置
        self.config_file = 'config.yaml'
        self.settings = self.load_config().get('log', {})
        if not self.settings:
            self.settings = {
                'console_enabled': True,
                'file_enabled': True,
                'image_enabled': True,
                'console_level': logging.INFO,
                'file_level': logging.DEBUG,
                'log_dir': 'log',
                'cleanup_days': 30
            }
        
        # 设置日志格式化器
        self.formatter = logging.Formatter(
            '[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d]%(message)s',
            datefmt='%Y.%m.%d %H:%M:%S'
        )
        
        # 确保日志目录存在
        self.setup_log_dir()
        
        # 设置日志处理器
        self.setup_handlers()
    
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}
    
    def save_config(self, config):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True)
            return True
        except Exception as e:
            self.error(f"保存配置失败: {str(e)}")
            return False
    
    def setup_log_dir(self):
        """设置日志目录"""
        self.log_dir = self.settings.get('log_dir', 'log')
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(os.path.join(self.log_dir, 'img'), exist_ok=True)
    
    def setup_handlers(self):
        """设置日志处理器"""
        self.logger.handlers.clear()
        
        # 控制台处理器
        if self.settings.get('console_enabled', True):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.settings.get('console_level', logging.INFO))
            console_handler.setFormatter(self.formatter)
            self.logger.addHandler(console_handler)
        
        # 文件处理器
        if self.settings.get('file_enabled', True):
            log_file = os.path.join(self.log_dir, f'{datetime.now().strftime("%Y%m%d")}.log')
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(self.settings.get('file_level', logging.DEBUG))
            file_handler.setFormatter(self.formatter)
            self.logger.addHandler(file_handler)
    
    def update_settings(self, new_settings: dict):
        """更新日志设置"""
        self.settings.update(new_settings)
        self.setup_log_dir()
        self.setup_handlers()
        
        # 保存到配置文件
        config = self.load_config()
        config['log'] = self.settings
        self.save_config(config)
        
        # 发送设置变更信号
        self.log_settings_changed.emit(self.settings)
    
    def _log(self, level: int, message: str, is_step: bool = False):
        """
        记录日志
        :param level: 日志级别
        :param message: 日志消息
        :param is_step: 是否为步骤信息
        """
        # 获取调用者信息
        caller = inspect.currentframe().f_back.f_back
        filename = os.path.basename(caller.f_code.co_filename)
        lineno = caller.f_lineno
        
        # 创建日志记录
        record = logging.LogRecord(
            name=self.logger.name,
            level=level,
            pathname=filename,
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=None
        )
        
        # 格式化消息
        formatted_msg = self.formatter.format(record)
        
        # 根据日志级别确定是否为错误消息
        is_error = level >= logging.ERROR
        
        # 发送到UI
        if is_step:
            # 步骤信息发送到步骤栏
            timestamp = datetime.now().strftime('%H:%M:%S')
            step_msg = f"[{timestamp}] {message}"
            self.step_message.emit(step_msg, is_error)
        else:
            # 日志信息发送到日志栏
            self.log_message.emit(formatted_msg)
        
        # 处理控制台输出
        if self.settings.get('console_enabled', True) and level >= self.settings.get('console_level', logging.INFO):
            print(formatted_msg)
        
        # 处理文件输出
        if self.settings.get('file_enabled', True) and level >= self.settings.get('file_level', logging.DEBUG):
            log_file = os.path.join(self.log_dir, f'{datetime.now().strftime("%Y%m%d")}.log')
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(formatted_msg + '\n')
    
    def debug(self, message: str, is_step: bool = False):
        self._log(logging.DEBUG, message, is_step)
    
    def info(self, message: str, is_step: bool = False):
        self._log(logging.INFO, message, is_step)
    
    def warning(self, message: str, is_step: bool = False):
        self._log(logging.WARNING, message, is_step)
    
    def error(self, message: str, is_step: bool = False):
        self._log(logging.ERROR, message, is_step)
    
    def critical(self, message: str, is_step: bool = False):
        self._log(logging.CRITICAL, message, is_step)
    
    def img(self, img, prefix="screenshot"):
        """保存图片日志"""
        if not self.settings.get('image_enabled', True):
            return None
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.png"
            filepath = os.path.join(self.log_dir, 'img', filename)
            cv2.imwrite(filepath, img)
            self.debug(f"图片已保存: {filepath}")
            return filepath
        except Exception as e:
            self.error(f"保存图片失败: {str(e)}")
            return None
    
    def clear_logs(self, days: int = None):
        """清理指定天数之前的日志"""
        if days is None:
            days = self.settings.get('cleanup_days', 30)
            
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 清理文本日志
            for filename in os.listdir(self.log_dir):
                if filename.endswith('.log'):
                    try:
                        file_date = datetime.strptime(filename[:8], '%Y%m%d')
                        if file_date < cutoff_date:
                            os.remove(os.path.join(self.log_dir, filename))
                    except ValueError:
                        continue
            
            # 清理图片日志
            img_dir = os.path.join(self.log_dir, 'img')
            for filename in os.listdir(img_dir):
                try:
                    file_date = datetime.strptime(filename.split('_')[1][:8], '%Y%m%d')
                    if file_date < cutoff_date:
                        os.remove(os.path.join(img_dir, filename))
                except (ValueError, IndexError):
                    continue
                    
            self.info(f"已清理{days}天前的日志")
            return True
        except Exception as e:
            self.error(f"清理日志失败: {str(e)}")
            return False

# 创建全局日志管理器实例
log_manager = LogManager() 