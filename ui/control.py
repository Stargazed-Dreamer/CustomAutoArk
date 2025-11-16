from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QVBoxLayout, QPushButton, QLabel, QGridLayout, QComboBox, QSpinBox, QCheckBox, QHBoxLayout, QMessageBox, QScrollArea, QGroupBox, QDoubleSpinBox, QLineEdit
from PySide6.QtCore import Qt

from .global_state import g
from log import log_manager
from .dialogs import InputWithImageDialog

from core.enums import OperationMode, GachaMode, RecruitMode, TaskType
from core.task import Task

class ControlWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.game_manager = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 设备连接区域
        device_group = QFrame()
        device_group.setFrameStyle(QFrame.Panel | QFrame.Raised)
        device_layout = QVBoxLayout(device_group)
        
        # 小面板按钮
        self.btn_mini_panel = QPushButton("打开小面板")
        self.btn_mini_panel.clicked.connect(self.show_mini_panel)
        self.btn_mini_panel.setEnabled(False)
        device_layout.addWidget(self.btn_mini_panel)
        
        # 连接按钮
        self.btn_connect = QPushButton("连接设备")
        self.btn_connect.clicked.connect(self.on_connect_clicked)
        device_layout.addWidget(self.btn_connect)
        
        # 记录画面按钮
        self.btn_record = QPushButton("记录画面")
        font = self.btn_record.font()
        font.setPointSize(9)
        self.btn_record.setFont(font)
        self.btn_record.clicked.connect(self.do_record_screen)
        self.btn_record.setEnabled(False)
        device_layout.addWidget(self.btn_record)
        
        layout.addWidget(device_group)
        
        # 模式设置区域
        mode_group = QFrame()
        mode_group.setFrameStyle(QFrame.Panel | QFrame.Raised)
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.addWidget(QLabel("<b>模式设置</b>"))
        
        # 公招模式选择
        recruit_layout = QGridLayout()
        recruit_layout.addWidget(QLabel("公招模式:"), 0, 0)
        self.recruit_mode = QComboBox()
        self.recruit_mode.addItems([mode.value for mode in RecruitMode])
        self.recruit_mode.setEnabled(False)
        self.recruit_mode.currentTextChanged.connect(self.on_recruit_mode_changed)
        recruit_layout.addWidget(self.recruit_mode, 0, 1)
        
        # 公招栏位选择
        recruit_layout.addWidget(QLabel("选择栏位:"), 1, 0)
        self.recruit_slot_select = QSpinBox()
        self.recruit_slot_select.setRange(1, 4)
        self.recruit_slot_select.setEnabled(False)
        self.recruit_slot_select.valueChanged.connect(self.on_recruit_slot_changed)
        recruit_layout.addWidget(self.recruit_slot_select, 1, 1)
        mode_layout.addLayout(recruit_layout)
        
        # 抽卡模式选择
        gacha_layout = QGridLayout()
        gacha_layout.addWidget(QLabel("抽卡模式:"), 0, 0)
        self.gacha_mode = QComboBox()
        self.gacha_mode.addItems([mode.value for mode in GachaMode])
        self.gacha_mode.setEnabled(False)
        self.gacha_mode.currentTextChanged.connect(self.on_gacha_mode_changed)
        gacha_layout.addWidget(self.gacha_mode, 0, 1)

        # 卡池选择
        gacha_layout.addWidget(QLabel("选择卡池:"), 1, 0)
        self.gacha_pool_select = QSpinBox()
        self.gacha_pool_select.setRange(1, 10)
        self.gacha_pool_select.setEnabled(False)
        self.gacha_pool_select.valueChanged.connect(self.on_gacha_pool_changed)
        gacha_layout.addWidget(self.gacha_pool_select, 1, 1)
        # 源石消耗选项
        self.use_originite = QCheckBox("使用源石")
        self.use_originite.setEnabled(False)
        self.use_originite.stateChanged.connect(self.on_use_originite_changed)
        gacha_layout.addWidget(self.use_originite, 1, 2, 1, 2)
        
        mode_layout.addLayout(gacha_layout)
        
        layout.addWidget(mode_group)
        
        # 循环操作组
        loop_group = QFrame()
        loop_group.setFrameStyle(QFrame.Panel | QFrame.Raised)
        loop_layout = QVBoxLayout(loop_group)
        
        loop_layout.addWidget(QLabel("<b>循环操作</b>"))
        
        # 模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([mode.value for mode in OperationMode])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.mode_combo.setEnabled(False)
        mode_layout.addWidget(self.mode_combo)
        loop_layout.addLayout(mode_layout)
        
        # 停止条件设置
        stop_layout = QHBoxLayout()
        self.stop_condition = QCheckBox()
        self.stop_condition.setEnabled(False)
        self.stop_condition.stateChanged.connect(self.on_stop_condition_changed)
        stop_layout.addWidget(self.stop_condition)
        self.stop_condition_label = QLabel("在遇见六星干员时停止")  # 默认显示
        stop_layout.addWidget(self.stop_condition_label)
        stop_layout.addStretch()
        loop_layout.addLayout(stop_layout)
        
        # 循环次数设置
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("执行次数:"))
        self.count_input = QSpinBox()
        self.count_input.setRange(0, 999999)
        self.count_input.setValue(0)
        self.count_input.setEnabled(False)
        count_layout.addWidget(self.count_input)
        count_layout.addWidget(QLabel("(0表示无限循环)"))
        count_layout.addStretch()
        loop_layout.addLayout(count_layout)
        
        # 启停控制
        control_layout = QHBoxLayout()
        
        # 开始/暂停按钮
        self.btn_start_pause = QPushButton("开始")
        font = self.btn_start_pause.font()
        font.setPointSize(14)
        self.btn_start_pause.setFont(font)
        self.btn_start_pause.setMinimumHeight(50)
        self.btn_start_pause.clicked.connect(self.toggle_operation)
        self.btn_start_pause.setEnabled(False)
        control_layout.addWidget(self.btn_start_pause)
        
        # 继续按钮（初始隐藏）
        self.btn_resume = QPushButton("继续")
        self.btn_resume.setFont(font)
        self.btn_resume.setMinimumHeight(50)
        self.btn_resume.clicked.connect(self.resume_operation)
        self.btn_resume.hide()
        control_layout.addWidget(self.btn_resume)
        
        # 重置按钮（初始隐藏）
        self.btn_reset = QPushButton("重置")
        self.btn_reset.setFont(font)
        self.btn_reset.setMinimumHeight(50)
        self.btn_reset.clicked.connect(self.reset_operation)
        self.btn_reset.hide()
        control_layout.addWidget(self.btn_reset)
        
        loop_layout.addLayout(control_layout)
        layout.addWidget(loop_group)        
        layout.addStretch()
    
    def on_recruit_mode_changed(self, mode_text: str):
        """公招模式改变处理"""
        mode = RecruitMode(mode_text)
        self.game_manager.set_recruit_mode(mode)
    
    def on_gacha_mode_changed(self, mode_text: str):
        """抽卡模式改变处理"""
        mode = GachaMode(mode_text)
        self.game_manager.set_gacha_mode(mode)
    
    def on_use_originite_changed(self, state):
        """源石消耗选项改变处理"""
        self.game_manager.set_use_originite(state)
    
    def on_recruit_slot_changed(self, value: int):
        """公招栏位改变处理"""
        self.game_manager.set_recruit_slot(value)
    
    def on_gacha_pool_changed(self, value: int):
        """卡池改变处理"""
        self.game_manager.set_gacha_pool(value)
    
    def on_mode_changed(self, index):
        """模式切换处理"""
        # 启用停止条件设置
        self.stop_condition.setEnabled(True)
        
        # 根据模式调整UI状态
        if index == 0:  # 干员寻访
            self.stop_condition_label.setText("在遇见六星干员时停止")
        elif index == 1:  # 公开招募
            self.stop_condition_label.setText("在遇见罕见tag时停止")
        else:  # 自动规划
            self.stop_condition_label.setText("在遇见六星干员/罕见tag时停止")
    
    def on_stop_condition_changed(self, state):
        """停止条件改变时的处理"""
        self.count_input.setEnabled(not state)
    
    def enable_controls(self, enabled: bool):
        """启用或禁用所有控件"""
        # 记录按钮
        self.btn_record.setEnabled(enabled)
        self.btn_mini_panel.setEnabled(enabled and not self.btn_start_pause.text() == "暂停")
        
        # 循环操作控件
        self.mode_combo.setEnabled(enabled)
        self.stop_condition.setEnabled(enabled)
        self.count_input.setEnabled(enabled and not self.stop_condition.isChecked())
        self.btn_start_pause.setEnabled(enabled and not hasattr(self, 'mini_panel'))
        
        # 模式设置控件
        self.recruit_mode.setEnabled(enabled)
        self.gacha_mode.setEnabled(enabled)
        self.recruit_slot_select.setEnabled(enabled)
        self.gacha_pool_select.setEnabled(enabled)
        self.use_originite.setEnabled(enabled)
    
    def disable_settings(self):
        """禁用所有设置项"""
        self.recruit_mode.setEnabled(False)
        self.gacha_mode.setEnabled(False)
        self.recruit_slot_select.setEnabled(False)
        self.gacha_pool_select.setEnabled(False)
        self.use_originite.setEnabled(False)
        self.mode_combo.setEnabled(False)
        self.stop_condition.setEnabled(False)
        self.count_input.setEnabled(False)
        self.btn_record.setEnabled(False)
    
    def toggle_operation(self):
        """切换操作状态"""
        if self.btn_start_pause.text() == "开始":
            reply = QMessageBox.question(
                self, '确认开始',
                "确定要开始执行吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No)
                
            if reply == QMessageBox.Yes:
                mode = self.mode_combo.currentText()
                if self.stop_condition.isChecked():
                    param = -1  # 遇到特定条件时停止
                else:
                    param = self.count_input.value()  # 使用用户设置的循环次数
                self.game_manager.start_operation(OperationMode(mode), param)
        else:  # 暂停
            self.game_manager.pause_operation()
    
    def resume_operation(self):
        """恢复操作"""
        self.game_manager.resume_operation()
    
    def reset_operation(self):
        """重置操作"""
        reply = QMessageBox.question(
            self, '确认重置',
            "确定要重置操作吗？这将停止当前操作并清除计数。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            self.game_manager.reset_operation()
    
    def on_connect_clicked(self):
        """连接设备"""
        adb_path = g.mainWindow.settings_widget.adb_path.text().strip()
        if not adb_path:
            QMessageBox.warning(self, "警告", "请先设置ADB路径")
            return
            
        # 初始化游戏管理器
        self.game_manager = g.mainWindow.game_manager
        
        # 连接游戏管理器信号
        self.game_manager.device_connected.connect(self.on_device_connection_changed)
        self.game_manager.operation_started.connect(self.on_operation_started)
        self.game_manager.operation_stopped.connect(self.on_operation_stopped)
        self.game_manager.operation_paused.connect(self.on_operation_paused)
        self.game_manager.operation_resumed.connect(self.on_operation_resumed)
        
        # 连接设备
        self.game_manager.connect_device(adb_path)
    
    def do_record_screen(self):
        """记录画面"""
        if self.game_manager:
            self.game_manager.taskAdd_recordScreen()
    
    def on_device_connection_changed(self, connected: bool):
        """设备连接状态改变时的处理"""
        # 启用/禁用所有控件
        self.enable_controls(connected)
        
        # 更新连接按钮状态
        if connected:
            self.btn_connect.setText("已连接")
            self.btn_connect.setEnabled(False)
        else:
            self.btn_connect.setText("连接设备")
            self.btn_connect.setEnabled(True)
    
    def on_operation_started(self):
        """操作开始时的处理"""
        self.btn_start_pause.setText("暂停")
        self.btn_start_pause.setStyleSheet("background-color: #ff9800;")  # 橙色
        self.btn_resume.hide()
        self.btn_reset.hide()
        self.disable_settings()  # 禁用设置
        self.btn_mini_panel.setEnabled(False)  # 禁用小面板按钮
    
    def on_operation_stopped(self):
        """操作停止时的处理"""
        self.btn_start_pause.setText("开始")
        self.btn_start_pause.setStyleSheet("")
        self.btn_start_pause.show()
        self.btn_resume.hide()
        self.btn_reset.hide()
        self.enable_settings()  # 启用设置
    
    def on_operation_paused(self):
        """操作暂停时的处理"""
        self.btn_start_pause.hide()
        self.btn_resume.show()
        self.btn_reset.show()
        self.btn_resume.setStyleSheet("background-color: #4caf50;")  # 绿色
        self.btn_reset.setStyleSheet("background-color: #f44336;")   # 红色
        # 暂停时不改变设置状态
    
    def on_operation_resumed(self):
        """操作恢复时的处理"""
        self.btn_resume.hide()
        self.btn_reset.hide()
        self.btn_start_pause.show()
        self.btn_start_pause.setText("暂停")
        self.btn_start_pause.setStyleSheet("background-color: #ff9800;")  # 橙色
        self.disable_settings()  # 重新禁用设置

    def enable_settings(self):
        """启用所有设置项"""
        enabled = self.btn_start_pause.isEnabled()  # 根据当前连接状态决定是否启用
        self.btn_mini_panel.setEnabled(enabled)
        self.recruit_mode.setEnabled(enabled)
        self.gacha_mode.setEnabled(enabled)
        self.recruit_slot_select.setEnabled(enabled)
        self.gacha_pool_select.setEnabled(enabled)
        self.use_originite.setEnabled(enabled)
        self.mode_combo.setEnabled(enabled)
        self.stop_condition.setEnabled(enabled)
        self.count_input.setEnabled(enabled and not self.stop_condition.isChecked())
        self.btn_record.setEnabled(enabled)

    def show_mini_panel(self):
        """显示小面板"""
        if not hasattr(self, 'mini_panel'):
            self.mini_panel = MiniPanel(self.game_manager, self)
            self.mini_panel.show()
            # 禁用循环模式的启动按钮
            self.btn_start_pause.setEnabled(False)
        else:
            self.mini_panel.show()
            self.mini_panel.raise_()

class MiniPanel(QWidget):
    def __init__(self, game_manager, control_widget):
        super().__init__()
        self.game_manager = game_manager
        self.control_widget = control_widget
        self.initUI()
        self.setWindowFlags(Qt.Window)  # 设置为独立窗口

    def initUI(self):
        self.setWindowTitle('测试面板')
        layout = QVBoxLayout(self)
        
        # 创建任务类型选择下拉框
        task_type_layout = QHBoxLayout()
        task_type_layout.addWidget(QLabel("任务类型:"))
        self.task_type_combo = QComboBox()
        self.task_type_combo.addItems([t.value for t in TaskType])
        self.task_type_combo.currentTextChanged.connect(self.on_task_type_changed)
        task_type_layout.addWidget(self.task_type_combo)
        layout.addLayout(task_type_layout)
        
        # 创建参数输入区域
        param_group = QGroupBox("参数设置")
        self.param_layout = QVBoxLayout(param_group)
        
        # 通用参数
        common_params = QGridLayout()
        
        # 超时设置
        common_params.addWidget(QLabel("超时(秒):"), 0, 0)
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(1, 60)
        self.timeout_input.setValue(4)
        common_params.addWidget(self.timeout_input, 0, 1)
        
        # 重试次数
        common_params.addWidget(QLabel("重试次数:"), 0, 2)
        self.retry_input = QSpinBox()
        self.retry_input.setRange(1, 100)
        self.retry_input.setValue(50)
        common_params.addWidget(self.retry_input, 0, 3)
        
        # 前置等待
        common_params.addWidget(QLabel("前置等待(秒):"), 1, 0)
        self.pre_wait_input = QDoubleSpinBox()
        self.pre_wait_input.setRange(0, 10)
        self.pre_wait_input.setSingleStep(0.1)
        common_params.addWidget(self.pre_wait_input, 1, 1)
        
        # 后置等待
        common_params.addWidget(QLabel("后置等待(秒):"), 1, 2)
        self.post_wait_input = QDoubleSpinBox()
        self.post_wait_input.setRange(0, 10)
        self.post_wait_input.setSingleStep(0.1)
        common_params.addWidget(self.post_wait_input, 1, 3)
        
        self.param_layout.addLayout(common_params)
        
        # 特定参数区域（动态变化）
        self.specific_param_widget = QWidget()
        self.specific_param_layout = QVBoxLayout(self.specific_param_widget)
        self.param_layout.addWidget(self.specific_param_widget)
        
        layout.addWidget(param_group)
        
        # 执行按钮
        self.execute_btn = QPushButton("执行任务")
        self.execute_btn.clicked.connect(self.execute_task)
        layout.addWidget(self.execute_btn)

        # 自定义任务按钮
        self.execute_custom_task_btn = QPushButton("执行自定义任务")
        self.execute_custom_task_btn.clicked.connect(self.execute_custom_task)
        layout.addWidget(self.execute_custom_task_btn)
        
        # 初始化特定参数界面
        self.on_task_type_changed(self.task_type_combo.currentText())
        
        # 设置合适的窗口大小
        self.setMinimumWidth(400)
    
    def clear_specific_params(self):
        """清除特定参数区域的所有控件"""
        while self.specific_param_layout.count():
            item = self.specific_param_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def on_task_type_changed(self, task_type):
        """当任务类型改变时更新参数输入界面"""
        self.clear_specific_params()
        
        if task_type in ["点击文字", "点击图片"]:
            # 添加目标输入
            target_layout = QHBoxLayout()
            target_layout.addWidget(QLabel("目标:"))
            self.target_input = QLineEdit()
            target_layout.addWidget(self.target_input)
            self.specific_param_layout.addLayout(target_layout)
            
            # 添加复用和公招检查选项
            options_layout = QHBoxLayout()
            self.reuse_check = QCheckBox("坐标复用")
            self.recruit_check = QCheckBox("公招检查")
            options_layout.addWidget(self.reuse_check)
            options_layout.addWidget(self.recruit_check)
            self.specific_param_layout.addLayout(options_layout)
            
        elif task_type in ["点击指定坐标"]:
            coord_layout = QHBoxLayout()
            coord_layout.addWidget(QLabel("X:"))
            self.x_input = QSpinBox()
            self.x_input.setRange(0, 1920)
            coord_layout.addWidget(self.x_input)
            coord_layout.addWidget(QLabel("Y:"))
            self.y_input = QSpinBox()
            self.y_input.setRange(0, 1080)
            coord_layout.addWidget(self.y_input)
            self.specific_param_layout.addLayout(coord_layout)
            
        elif task_type in ["点击相对位置"]:
            coord_layout = QHBoxLayout()
            coord_layout.addWidget(QLabel("相对X(0-1):"))
            self.rx_input = QDoubleSpinBox()
            self.rx_input.setRange(0, 1)
            self.rx_input.setSingleStep(0.1)
            coord_layout.addWidget(self.rx_input)
            coord_layout.addWidget(QLabel("相对Y(0-1):"))
            self.ry_input = QDoubleSpinBox()
            self.ry_input.setRange(0, 1)
            self.ry_input.setSingleStep(0.1)
            coord_layout.addWidget(self.ry_input)
            self.specific_param_layout.addLayout(coord_layout)
            
        elif task_type in ["记录指定数量抽卡记录"]:
            count_layout = QHBoxLayout()
            count_layout.addWidget(QLabel("记录数量:"))
            self.count_input = QSpinBox()
            self.count_input.setRange(1, 100)
            count_layout.addWidget(self.count_input)
            self.specific_param_layout.addLayout(count_layout)
    
    def execute_task(self):
        """执行选定的任务"""
        task_type = TaskType(self.task_type_combo.currentText())
        param = None
        
        # 根据任务类型获取参数
        if task_type in [TaskType.CLICK_TEXT, TaskType.CLICK_IMG]:
            param = self.target_input.text()
        elif task_type == TaskType.CLICK_COORDINATE:
            param = (self.x_input.value(), self.y_input.value())
        elif task_type == TaskType.CLICK_COORDINATE_RELATIVE:
            param = (self.rx_input.value(), self.ry_input.value())
        elif task_type == TaskType.RECORD_HISTORY_FLEX:
            param = self.count_input.value()
            
        # 创建任务
        task = Task(
            task_type,
            param,
            timeout=self.timeout_input.value(),
            retry_count=self.retry_input.value(),
            pre_wait=self.pre_wait_input.value(),
            post_wait=self.post_wait_input.value(),
            b_reuse=getattr(self, 'reuse_check', QCheckBox()).isChecked(),
            b_recruitCheck=getattr(self, 'recruit_check', QCheckBox()).isChecked()
        )
        
        # 添加并执行任务
        self.game_manager.task_manager.add_task(task)
        self.game_manager.task_manager.execute_tasks()

    def execute_custom_task(self):
        self.game_manager.taskAdd_customTask_loop()
        
    def closeEvent(self, event):
        """关闭窗口时启用主界面的开始按钮"""
        if self.control_widget:
            self.control_widget.btn_start_pause.setEnabled(True)
            self.control_widget.enable_settings()
            delattr(self.control_widget, 'mini_panel')
        self.game_manager.task_manager.stop_tasks()
        event.accept()