import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QCheckBox, QFileDialog, QMessageBox, QComboBox

from log import log_manager
from .global_state import g

# 控制组件
class SettingsWidget(QWidget):
    # 添加设置变更信号
    from PySide6.QtCore import Signal
    settings_changed = Signal(dict)
    
    def __init__(self, parent=None):
        """初始化实例，调用父类的构造函数并初始化用户界面。

        参数:
            parent: 可选，指定父对象，默认为None。
        返回值:
            无
        """
        super().__init__(parent)  # 调用父类的初始化方法，传递parent参数
        self.initUI()  # 调用initUI方法，用于初始化用户界面
    
    def initUI(self):
        """初始化用户界面设置。创建模拟器设置、日志设置和数据设置的控件，并连接信号与槽。"""
        layout = QVBoxLayout(self)  # 创建主垂直布局，用于组织所有UI控件
    
        # 模拟器设置组
        simulator_group = QGroupBox("模拟器设置")
        simulator_layout = QVBoxLayout()
    
        # ADB路径设置
        adb_layout = QHBoxLayout()
        adb_layout.addWidget(QLabel("ADB路径:"))
        self.adb_path = QLineEdit()  # 用于输入ADB可执行文件的路径
        self.browse_adb_btn = QPushButton("浏览")
        adb_layout.addWidget(self.adb_path)
        adb_layout.addWidget(self.browse_adb_btn)
        simulator_layout.addLayout(adb_layout)
    
        # 端口设置
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("监听端口:"))
        self.port = QSpinBox()
        self.port.setRange(1024, 65535)  # 设置端口范围，1024-65535为常用TCP端口区间
        self.port.setValue(7555)  # 默认端口设置为7555
        port_layout.addWidget(self.port)
        port_layout.addStretch()
        simulator_layout.addLayout(port_layout)
    
        simulator_group.setLayout(simulator_layout)
        layout.addWidget(simulator_group)
    
        # 日志设置组
        log_group = QGroupBox("日志设置")
        log_layout = QVBoxLayout()
    
        # 控制台日志
        console_layout = QHBoxLayout()
        self.console_enabled = QCheckBox("控制台日志")
        self.console_enabled.setChecked(log_manager.settings['console_enabled'])  # 从全局设置读取控制台日志启用状态
        self.console_level = QComboBox()
        self.console_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])  # 添加日志级别选项，从详细到严重
        self.console_level.setCurrentText(
            str(logging.getLevelName(log_manager.settings['console_level']))  # 设置当前日志级别，使用logging模块转换
        )
        console_layout.addWidget(self.console_enabled)
        console_layout.addWidget(self.console_level)
        log_layout.addLayout(console_layout)
    
        # 文件日志
        file_layout = QHBoxLayout()
        self.file_enabled = QCheckBox("文件日志")
        self.file_enabled.setChecked(log_manager.settings['file_enabled'])  # 从全局设置读取文件日志启用状态
        self.file_level = QComboBox()
        self.file_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])  # 文件日志级别选项，与控制台一致
        self.file_level.setCurrentText(
            str(logging.getLevelName(log_manager.settings['file_level']))  # 设置文件日志级别
        )
        file_layout.addWidget(self.file_enabled)
        file_layout.addWidget(self.file_level)
        log_layout.addLayout(file_layout)
    
        # 图片日志
        image_layout = QHBoxLayout()
        self.image_enabled = QCheckBox("图片日志")
        self.image_enabled.setChecked(log_manager.settings['image_enabled'])  # 从全局设置读取图片日志启用状态
        image_layout.addWidget(self.image_enabled)
        image_layout.addStretch()
        log_layout.addLayout(image_layout)
    
        # 日志目录
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("日志目录:"))
        self.log_path = QLineEdit()
        self.log_path.setText(log_manager.settings['log_dir'])  # 设置日志存储目录路径，从全局设置读取
        self.browse_log_btn = QPushButton("浏览")
        dir_layout.addWidget(self.log_path)
        dir_layout.addWidget(self.browse_log_btn)
        log_layout.addLayout(dir_layout)
    
        # 日志清理
        clean_layout = QHBoxLayout()
        self.clean_days = QSpinBox()
        self.clean_days.setRange(1, 365)  # 设置日志保留天数范围为1到365天
        self.clean_days.setValue(30)  # 默认保留30天日志
        self.clean_btn = QPushButton("清理日志")
        clean_layout.addWidget(QLabel("保留天数:"))
        clean_layout.addWidget(self.clean_days)
        clean_layout.addWidget(self.clean_btn)
        log_layout.addLayout(clean_layout)
    
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
    
        # 数据设置组
        data_group = QGroupBox("数据设置")
        data_layout = QVBoxLayout()
    
        # 数据文件路径
        data_file_layout = QHBoxLayout()
        self.data_file = QLineEdit()  # 用于输入数据文件的路径
        data_file_layout.addWidget(QLabel("数据文件:"))
        data_file_layout.addWidget(self.data_file)
        browse_data_btn = QPushButton("浏览")
        browse_data_btn.clicked.connect(self.browse_data)  # 连接浏览按钮点击信号到browse_data方法
        data_file_layout.addWidget(browse_data_btn)
        data_layout.addLayout(data_file_layout)
    
        # 自动保存设置
        auto_save_layout = QHBoxLayout()
        self.auto_save = QCheckBox("自动保存")
        auto_save_layout.addWidget(self.auto_save)
        auto_save_layout.addWidget(QLabel("间隔:"))
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(1, 60)  # 设置自动保存间隔范围为1到60分钟
        self.auto_save_interval.setValue(5)  # 默认间隔5分钟
        auto_save_layout.addWidget(self.auto_save_interval)
        auto_save_layout.addWidget(QLabel("分钟"))
        data_layout.addLayout(auto_save_layout)
    
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
    
        # 保存按钮
        self.save_btn = QPushButton("保存设置")
        layout.addWidget(self.save_btn)
    
        # 连接信号
        self.browse_log_btn.clicked.connect(self.browse_log)  # 连接日志目录浏览按钮信号
        self.clean_btn.clicked.connect(self.clean_logs)  # 连接日志清理按钮信号
        self.save_btn.clicked.connect(self.save_settings)  # 连接保存按钮信号到save_settings方法
    
        # 连接日志设置变更信号
        log_manager.log_settings_changed.connect(self.on_log_settings_changed)  # 连接全局日志设置变更信号到处理函数
    
        # 连接模拟器设置变更信号
        self.browse_adb_btn.clicked.connect(self.browse_adb)  # 连接ADB路径浏览按钮信号
    
    def browse_log(self):
        """选择日志目录"""
        path = QFileDialog.getExistingDirectory(self, "选择日志目录")
        if path:
            self.log_path.setText(path)
    
    def clean_logs(self):
        """清理日志"""
        days = self.clean_days.value()
        reply = QMessageBox.question(
            self,
            "确认清理",
            f"确定要清理{days}天前的日志吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            log_manager.clear_logs(days)
    
    def save_settings(self):
        """保存设置"""
        # 保存日志设置
        from PySide6.QtWidgets import QComboBox
        new_log_settings = {
            'console_enabled': self.console_enabled.isChecked(),
            'file_enabled': self.file_enabled.isChecked(),
            'image_enabled': self.image_enabled.isChecked(),
            'console_level': getattr(logging, self.console_level.currentText()),
            'file_level': getattr(logging, self.file_level.currentText()),
            'log_dir': self.log_path.text().strip()
        }
        log_manager.update_settings(new_log_settings)
        
        # 保存模拟器设置
        simulator_settings = {
            'adb_path': self.adb_path.text().strip(),
            'port': self.port.value()
        }
        
        # 保存数据设置
        data_settings = {
            'data_file': self.data_file.text().strip(),
            'auto_save': self.auto_save.isChecked(),
            'auto_save_interval': self.auto_save_interval.value()
        }
        
        # 加载当前配置
        config = g.config
        
        # 更新配置
        config['log'] = new_log_settings
        config['simulator'] = simulator_settings
        config['data'] = data_settings
        
        # 保存配置
        g.config = config

        if log_manager.save_config(config):
            g.mainWindow.loadSettings()
            g.mainWindow.statusBar().showMessage("设置已保存", 3000)
        else:
            g.mainWindow.statusBar().showMessage("设置保存失败", 3000)
    
    def on_log_settings_changed(self, settings: dict):
        """处理日志设置变更"""
        self.console_enabled.setChecked(settings['console_enabled'])
        self.file_enabled.setChecked(settings['file_enabled'])
        self.image_enabled.setChecked(settings['image_enabled'])
        from PySide6.QtWidgets import QComboBox
        self.console_level.setCurrentText(str(logging.getLevelName(settings['console_level'])))
        self.file_level.setCurrentText(str(logging.getLevelName(settings['file_level'])))
        self.log_path.setText(settings['log_dir'])
    
    def browse_data(self):
        """选择数据文件"""
        path, _ = QFileDialog.getOpenFileName(self, "选择数据文件", "", "文本文件 (*.txt)")
        if path:
            self.data_file.setText(path)
    
    def browse_adb(self):
        """选择ADB文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择ADB文件",
            "",
            "ADB文件 (adb.exe);;所有文件 (*.*)"
        )
        if file_path:
            self.adb_path.setText(file_path)

    def loadSettings(self):
        """加载设置"""
        config = g.config
        
        # 加载模拟器设置
        simulator_settings = config.get('simulator', {})
        self.adb_path.setText(simulator_settings.get('adb_path', ''))
        self.port.setValue(simulator_settings.get('port', 7555))
        
        # 加载日志设置
        log_settings = config.get('log', {})
        self.console_enabled.setChecked(log_settings.get('console_enabled', True))
        self.file_enabled.setChecked(log_settings.get('file_enabled', True))
        self.image_enabled.setChecked(log_settings.get('image_enabled', True))
        self.console_level.setCurrentText(str(logging.getLevelName(log_settings.get('console_level', logging.INFO))))
        self.file_level.setCurrentText(str(logging.getLevelName(log_settings.get('file_level', logging.DEBUG))))
        self.log_path.setText(log_settings.get('log_dir', 'log'))
        self.clean_days.setValue(log_settings.get('cleanup_days', 30))
        
        # 加载数据设置
        data_settings = config.get('data', {})
        self.data_file.setText(data_settings.get('file_path', '#record.txt'))
        self.auto_save.setChecked(data_settings.get('auto_save', True))
        self.auto_save_interval.setValue(data_settings.get('auto_save_interval', 5))