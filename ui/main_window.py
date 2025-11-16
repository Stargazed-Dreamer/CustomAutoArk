import json
import logging
import os
import sys

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QComboBox, 
                             QSpinBox, QCheckBox, QTabWidget, QTextEdit,
                             QFileDialog, QMessageBox, QScrollArea, QFrame,
                             QSplitter, QLineEdit, QPlainTextEdit)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QAction

import cv2 as cv

from data import data as DATA
from data_manager import data_manager
from log import log_manager
from tool import tool, error_record

from core.enums import OperationMode, GachaMode, RecruitMode, TaskType
from core.game_manager import GameManager

from .global_state import g
from .console import ConsoleWidget
from .plot import PlotWidget
from .statistics import StatisticsWidget
from .data_view import DataViewWidget
from .settings import SettingsWidget
from .control import ControlWidget
from .dialogs import InputWithImageDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        g.mainWindow = self

        self.game_manager = GameManager()
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        
        # 设置游戏管理器的父对象
        self.game_manager.setParent(self)
        
        # 连接游戏管理器信号
        self.game_manager.log_message.connect(self.on_log_message)
        self.game_manager.step_updated.connect(self.on_step_updated)
        self.game_manager.data_updated.connect(self.on_data_updated)
        self.game_manager.macro_step_updated.connect(self.on_macro_step_updated)
        
        # 连接日志管理器信号
        log_manager.log_message.connect(self.on_log_message)
        
        self.initUI()
        self.loadSettings()
        self.setupMenuBar()

        self.img_extension = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        self.supported_extension = self.img_extension + [".json", ".txt"]

    def setupMenuBar(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        # 打开文件动作
        open_action = QAction('打开', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        # 保存文件动作
        save_action = QAction('保存', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        # 导出PNG动作
        export_action = QAction('导出PNG', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_png)
        file_menu.addAction(export_action)

    def initUI(self):
        """初始化UI布局"""
        self.setWindowTitle('明日方舟助手')
        self.resize(1280, 800)
        
        # 创建主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # 创建垂直分隔器
        main_splitter = QSplitter(Qt.Vertical)
        
        # 上部数据展示区
        data_display = QWidget()
        data_layout = QHBoxLayout(data_display)
        data_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 创建水平分隔器
        data_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧图表区域
        plot_area = QWidget()
        plot_layout = QVBoxLayout(plot_area)
        plot_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 图表
        self.plot_widget = PlotWidget()
        plot_layout.addWidget(self.plot_widget, 4)
        
        # 统计和操作区（水平布局）
        stats_ops = QWidget()
        stats_ops_layout = QHBoxLayout(stats_ops)
        
        # 统计信息（一个框内左右布局）
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        stats_layout = QHBoxLayout(stats_frame)
        
        # 全局统计
        global_layout = QVBoxLayout()
        global_layout.addWidget(QLabel("<b>全局统计</b>"))
        self.global_stats = QTextEdit()
        self.global_stats.setReadOnly(True)
        self.global_stats.setMaximumHeight(100)
        global_layout.addWidget(self.global_stats)
        stats_layout.addLayout(global_layout)
        
        # 选中区域统计
        selection_layout = QVBoxLayout()
        selection_layout.addWidget(QLabel("<b>选中区域统计</b>"))
        self.selection_stats = QTextEdit()
        self.selection_stats.setReadOnly(True)
        self.selection_stats.setMaximumHeight(100)
        selection_layout.addWidget(self.selection_stats)
        stats_layout.addLayout(selection_layout)
        
        # 图表操作区
        ops_frame = QFrame()
        ops_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        ops_layout = QHBoxLayout(ops_frame)
        
        # 左侧设置区
        settings_layout = QVBoxLayout()
        self.show_predict = QCheckBox("显示预测结果")
        settings_layout.addWidget(self.show_predict)
        
        predict_layout = QVBoxLayout()
        predict_range_layout = QHBoxLayout()
        predict_range_layout.addWidget(QLabel("预测后"))
        self.predict_range = QSpinBox()
        self.predict_range.setRange(1, 100)
        self.predict_range.setValue(10)
        predict_range_layout.addWidget(self.predict_range)
        predict_range_layout.addWidget(QLabel("个"))
        predict_layout.addLayout(predict_range_layout)
        
        self.probability_label = QLabel("下一次出六星概率：0%")
        predict_layout.addWidget(self.probability_label)
        settings_layout.addLayout(predict_layout)
        settings_layout.addStretch()
        
        # 右侧按钮区
        buttons_layout = QVBoxLayout()
        self.btn_peaks = QPushButton("波峰波谷分析")
        self.btn_patterns = QPushButton("相似模式查找")
        self.btn_save = QPushButton("保存右侧数据")
        buttons_layout.addWidget(self.btn_peaks)
        buttons_layout.addWidget(self.btn_patterns)
        buttons_layout.addWidget(self.btn_save)
        self.btn_peaks.clicked.connect(self.plot_widget.analyze_peaks)
        self.btn_patterns.clicked.connect(self.plot_widget.find_patterns)
        self.btn_save.clicked.connect(self.save_current_data)
        buttons_layout.addStretch()
        
        ops_layout.addLayout(settings_layout)
        ops_layout.addLayout(buttons_layout)
        
        stats_ops_layout.addWidget(stats_frame, 2)
        stats_ops_layout.addWidget(ops_frame, 1)
        
        plot_layout.addWidget(stats_ops, 1)
        
        # 将图表区域添加到水平分隔器
        plot_area_container = QWidget()
        plot_area_container.setLayout(plot_layout)
        data_splitter.addWidget(plot_area_container)
        
        # 右侧数据视图添加到水平分隔器
        self.data_view = DataViewWidget()
        self.data_view.setMinimumWidth(100)
        data_splitter.addWidget(self.data_view)

        # 设置分隔器的初始比例
        data_splitter.setStretchFactor(0, 4)  # 图表区域占80%
        data_splitter.setStretchFactor(1, 1)  # 数据视图占20%
        
        data_layout.addWidget(data_splitter)
        
        # 将数据展示区添加到垂直分隔器
        data_display_container = QWidget()
        data_display_container.setLayout(data_layout)
        main_splitter.addWidget(data_display_container)
        
        # 底部控制区域
        control_area = QWidget()
        control_layout = QHBoxLayout(control_area)
        control_layout.setContentsMargins(5, 5, 5, 5)
        control_layout.setSpacing(5)
        
        # 创建水平分隔器
        control_splitter = QSplitter(Qt.Horizontal)
        
        # 设置区（添加滚动区域）
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        self.settings_widget = SettingsWidget()
        settings_scroll.setWidget(self.settings_widget)
        settings_scroll.setMinimumWidth(200)
        control_splitter.addWidget(settings_scroll)
        
        # 控制台
        self.console = ConsoleWidget()
        control_splitter.addWidget(self.console)
        
        # 功能执行区（添加滚动区域）
        control_scroll = QScrollArea()
        control_scroll.setWidgetResizable(True)
        self.control_widget = ControlWidget()
        control_scroll.setWidget(self.control_widget)
        control_scroll.setMinimumWidth(200)
        control_splitter.addWidget(control_scroll)
        
        # 设置分隔器的初始大小比例
        control_splitter.setStretchFactor(0, 2)  # 设置区占20%
        control_splitter.setStretchFactor(1, 4)  # 控制台占40%
        control_splitter.setStretchFactor(2, 4)  # 功能执行区占40%
        
        control_layout.addWidget(control_splitter)
        
        # 将控制区域添加到主分隔器
        control_area_container = QWidget()
        control_area_container.setLayout(control_layout)
        main_splitter.addWidget(control_area_container)
        
        # 设置主分隔器的初始大小比例
        main_splitter.setStretchFactor(0, 3)  # 数据展示区占30%
        main_splitter.setStretchFactor(1, 7)  # 控制区域占70%
        
        main_layout.addWidget(main_splitter)
        
        # 设置窗口最小尺寸
        self.setMinimumSize(1024, 768)
    
    def loadSettings(self):
        """加载所有设置"""
        g.config = log_manager.load_config()
        self.settings_widget.loadSettings()
        self.plot_widget.loadSettings()
        
        # 应用自动保存设置
        config = g.config
        data_settings = config.get('data', {})
        if data_settings.get('auto_save', True):
            interval = data_settings.get('auto_save_interval', 5) * 60 * 1000  # 转换为毫秒
            self.auto_save_timer.start(interval)
    
    def auto_save(self):
        """自动保存数据"""
        try:
            if data_manager.save_data():
                log_manager.debug("数据自动保存成功")
            else:
                log_manager.warning("数据自动保存失败")
        except Exception as e:
            error_record(e)
            log_manager.error(f"自动保存时发生错误: {str(e)}")
    
    def closeEvent(self, event):
        """关闭窗口时的处理"""
        try:
            # 停止自动保存定时器
            self.auto_save_timer.stop()
            
            # 保存数据
            if data_manager.save_data():
                log_manager.info("数据已保存")
            
            # 保存设置
            self.settings_widget.save_settings()

            # 清理adb连接
            self.game_manager.break_connection()
            
        except Exception as e:
            error_record(e)
            log_manager.error(f"关闭窗口时发生错误: {str(e)}")
        
        event.accept()

    @Slot()
    def open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开数据文件", "", "文本文件 (*.txt)")
        if file_path:
            if data_manager.load_data(file_path):
                self.plot_widget.set_data(data_manager.data)
                self.data_view.set_data(data_manager.data, data_manager.real_data)
                log_manager.info(f"成功加载文件：{file_path}")
            else:
                log_manager.error(f"加载文件失败：{file_path}")

    @Slot()
    def save_file(self):
        """保存文件"""
        if not data_manager.file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存数据文件", "", "文本文件 (*.txt)")
            if not file_path:
                return False
            data_manager.file_path = file_path
        
        if data_manager.save_data():
            log_manager.info(f"成功保存文件：{data_manager.file_path}")
            return True
        else:
            log_manager.error(f"保存文件失败：{data_manager.file_path}")
            return False

    @Slot()
    def export_png(self):
        """导出PNG图片"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出PNG", "", "PNG图片 (*.png)")
        if file_path:
            if data_manager.export_png(file_path):
                log_manager.info(f"成功导出PNG：{file_path}")
            else:
                log_manager.error(f"导出PNG失败：{file_path}")

    def handle_missing_tag(self, img):
        """处理找不到tag的情况"""
        while True:
            dialog = InputWithImageDialog(
                "输入标签",
                "请输入5个tag，用逗号分隔：",
                img,
                self
            )
            if dialog.exec_() != QDialog.Accepted:
                return None
                
            text = dialog.get_input()
            l_input = [t.strip() for t in text.split(",") if t.strip()]
            if len(l_input) != 5:
                QMessageBox.warning(self, "错误", "请输入5个tag")
                continue
                
            # 验证tag是否合法
            invalid_tags = [t for t in l_input if t not in DATA.l_tag]
            if invalid_tags != []:
                QMessageBox.warning(self, "错误", f"以下tag不合法：{invalid_tags}")
                continue
                
            return l_input

    def handle_missing_agent(self, img):
        """处理找不到干员的情况"""
        while True:
            dialog = InputWithImageDialog(
                "输入干员",
                "请输入干员中文名称：",
                img,
                self
            )
            if dialog.exec_() != QDialog.Accepted:
                return None
                
            text = dialog.get_input().strip()
            if not text:
                QMessageBox.warning(self, "错误", "请输入干员名称")
                continue
                
            # 验证干员是否存在
            if text not in DATA.l_agent:
                QMessageBox.warning(self, "错误", "干员不存在")
                continue
                
            return text

    def handle_missing_record(self, errorTuple):
        """处理无法识别记录的情况"""
        img, l_result = errorTuple
        while True:
            dialog = InputWithImageDialog(
                "输入干员",
                "无法识别记录，请输入所有干员中文名称，空格分隔：",
                img,
                self
            )
            dialog.set_text(" ".join(l_result))
            if dialog.exec_() != QDialog.Accepted:
                return None
                
            text = dialog.get_input().strip()
            if not text:
                QMessageBox.warning(self, "错误", "请输入所有干员名称")
                continue
                
            # 验证干员是否存在
            invalid_agent = [agent for agent in text.split(" ") if agent not in DATA.l_agent]
            if invalid_agent:
                QMessageBox.warning(self, "错误", f"{invalid_agent} 不存在")
                continue
                
            return text

    def on_step_updated(self, current_step: str, next_step: str):
        """处理步骤更新"""
        if hasattr(self, "console"):
            self.console.update_step(current_step, next_step)
    
    def on_macro_step_updated(self, macro_step, level):
        """处理宏观步骤更新"""
        if hasattr(self, "console"):
            self.console.append_macro_step(macro_step, level)

    def on_log_message(self, message: str, level: str = "INFO"):
        """处理日志消息"""
        if hasattr(self, "console"):
            self.console.append_message(message, level)

    def on_user_changed_data(self, info_data: list):
        """用户应用数据的修改"""
        data_manager.set_data("\n".join(info_data))
        self.plot_widget.set_data(data_manager.data)
        self.data_view.set_data(numeric_data=data_manager.data)

    def on_data_updated(self):
        self.plot_widget.set_data(data_manager.data)
        self.data_view.set_data(numeric_data=data_manager.data, info_data=data_manager.real_data)
    
    def save_current_data(self):
        """保存核心数据"""
        try:
            config = g.config
            data_settings = config.get('data', {})
            file_path = data_settings.get('file_path', '#record.txt')
            
            if data_manager.save_data(file_path):
                log_manager.info(f"数据已保存到 {file_path}")
            else:
                log_manager.error("保存数据失败")
        except Exception as e:
            error_record(e)
            QMessageBox.warning(self, "错误", f"保存失败：{str(e)}")
            log_manager.error(f"保存数据时发生错误：{str(e)}")

    def dragEnterEvent(self, event):
        """拖入事件处理，支持目录、图片、JSON和TXT文件"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                # 检查是否为目录
                if os.path.isdir(file_path):
                    event.acceptProposedAction()
                    return
                # 检查文件扩展名
                ext = os.path.splitext(file_path)[1].lower()
                if ext in self.supported_extension:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        """放下事件处理，支持多种文件类型和目录"""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            try:
                if os.path.isdir(file_path):
                    self.append_data_from_dir(file_path)
                    self.statusBar().showMessage(f"成功导入目录: {file_path}", 3000)
                else:
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in self.img_extension:
                        self.append_data_from_img(file_path)
                        self.statusBar().showMessage(f"成功导入图片: {file_path}", 3000)
                    elif ext == '.json':
                        self.append_data_from_json(file_path)
                        self.statusBar().showMessage(f"成功导入JSON文件: {file_path}", 3000)
                    elif ext == '.txt':
                        self.append_data_from_txt(file_path)
                        self.statusBar().showMessage(f"成功导入TXT文件: {file_path}", 3000)
            except Exception as e:
                self.statusBar().showMessage(f"导入失败: {str(e)}", 3000)
                error_record(e)
                log_manager.error(f"文件处理失败 {file_path}: {e}", e)
        event.acceptProposedAction()

    def append_data_from_json(self, jsonPath):
        log_manager.debug(f"从json文件 {jsonPath} 中录入")
        with open(jsonPath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        l_agents = []
        for entry in data['data']['list']:
            for char in entry['chars']:
                l_agents.append(char['name'])
        data_manager.update_data(l_agents[::-1])
        self.plot_widget.set_data(data_manager.data)
        self.data_view.set_data(
            data_manager.data,
            data_manager.real_data
        )

    def append_data_from_txt(self, txtPath):
        log_manager.debug(f"从文本文件 {txtPath} 中录入")
        if data_manager.load_data(txtPath):
            self.plot_widget.set_data(data_manager.data)
            self.data_view.set_data(
                data_manager.data,
                data_manager.real_data
            )
        else:
            raise RuntimeError(f"文件 {txtPath} 解析失败")

    def append_data_from_img(self, imgPath, refresh = False):
        log_manager.debug(f"从图片 {imgPath} 中录入")
        file_ext = os.path.splitext(imgPath)[1].lower()
        if file_ext in self.img_extension:
            img = cv.imread(imgPath)
        else:
            raise RuntimeError(f"无法将 {imgPath} 读取为图片")
        if img is None:
            raise RuntimeError(f"无法将 {imgPath} 读取为图片，可能是路径有中文？")
        # 三种识别挨个判定正确的
        l_tag = tool.getTag(img)
        if len(l_tag) == 5:
            data_manager.update_data("!".join(l_tag))
        else:
            agent = tool.getAgent(img)
            if agent is not None:
                data_manager.update_data(agent)
            else:
                l_history, b_flag = tool.getHistory(img)
                if b_flag:
                    data_manager.update_data("\n".join(l_history))
                else:
                    log_manager.debug(f"{imgPath}识别结果: tag={l_tag}, 干员={agent}, 历史={l_history}, 标志={b_flag}")
                    raise RuntimeError(f"无法识别图像 {imgPath}")
        if refresh:
            self.plot_widget.set_data(data_manager.data)
            self.data_view.set_data(
                data_manager.data,
                data_manager.real_data
            )

    def append_data_from_dir(self, dirPath):
        log_manager.debug(f"从目录 {dirPath} 中录入")

        # 收集所有文件及其创建时间
        l_files = []
        # 是否所有文件都是纯数字命名
        all_numeric = True

        # 遍历文件夹中的所有文件
        for root, dirs, files in os.walk(dirPath):
            for file in files:
                # 获取文件完整路径
                #file_path = root.replace("/", "\\") + "\\" + file
                file_path = os.path.join(root, file)

                # 检查文件扩展名是否为图像文件
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext not in self.supported_extension:
                    continue

                try:
                    # 获取文件修改时间
                    creation_time = os.path.getmtime(file_path)
                except Exception as e:
                    error_record(e)
                    print(f"无法获取文件 {file_path} 的修改时间: {e}")
                    continue

                l_files.append((file_path, creation_time, file_ext))

                # 判断文件名是否纯数字（无扩展名部分）
                base_name = os.path.splitext(file)[0]
                if not base_name.isdigit():
                    all_numeric = False

        # 根据 all_numeric 决定排序键
        if all_numeric and l_files:
            l_files.sort(key=lambda t: int(os.path.splitext(os.path.basename(t[0]))[0]))
        else:
            # 按创建时间排序（从老到新）
            l_files.sort(key=lambda t: t[1])

        l_error = []
        for file_path, _, file_ext in l_files:
            try:
                if file_ext in self.img_extension:
                    self.append_data_from_img(file_path, refresh = False)
                elif file_ext == ".txt":
                    self.append_data_from_txt(file_path)
                elif file_ext == ".json":
                    self.append_data_from_json(file_path)
                else:
                    raise RuntimeError("shouldn't be here")
            except Exception as e:
                error_record(e)
                l_error.append(file_path)

        self.plot_widget.set_data(data_manager.data)
        self.data_view.set_data(
            data_manager.data,
            data_manager.real_data
        )
        if l_error:
            raise RuntimeError("以下文件在载入时出错：\n" + "\n".join(l_error))