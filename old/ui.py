import sys
import os
import yaml
import cv2
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget,
                            QVBoxLayout, QHBoxLayout, QLineEdit, QPlainTextEdit,
                            QLabel, QFileDialog, QMessageBox, QScrollArea)
from PySide6.QtCore import Qt, QThread, Signal
from main2x import Main, Log, CreatPath
import logging

class LogHandler(logging.Handler):
    """自定义日志处理器,将日志输出到QTextEdit"""
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        
    def emit(self, record):
        msg = self.format(record)
        self.text_edit.appendPlainText(msg)

class WorkerThread(QThread):
    """工作线程,用于执行耗时操作"""
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        try:
            self.func(*self.args, **self.kwargs)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.main = Main()
        self.worker = None
        self.initUI()
        self.loadConfig()
        
    def initUI(self):
        """初始化UI界面"""
        self.setWindowTitle('明日方舟抽卡记录器')
        self.setGeometry(100, 100, 800, 600)
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 创建主布局
        layout = QHBoxLayout()
        
        # 左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # 记录按钮
        self.record_btn = QPushButton('记录当前画面')
        self.record_btn.clicked.connect(self.recordCurrent)
        left_layout.addWidget(self.record_btn)
        
        # 开始/停止按钮
        btn_layout = QHBoxLayout()
        self.start_draw_btn = QPushButton('开始抽卡')
        self.start_draw_btn.clicked.connect(self.startDraw)
        self.start_recruit_btn = QPushButton('开始招募')
        self.start_recruit_btn.clicked.connect(self.startRecruit)
        self.stop_btn = QPushButton('停止')
        self.stop_btn.clicked.connect(self.stopWorker)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.start_draw_btn)
        btn_layout.addWidget(self.start_recruit_btn)
        btn_layout.addWidget(self.stop_btn)
        left_layout.addLayout(btn_layout)
        
        # 保存按钮
        self.save_btn = QPushButton('保存当前记录')
        self.save_btn.clicked.connect(self.saveRecord)
        left_layout.addWidget(self.save_btn)
        
        # 模拟器连接
        conn_layout = QHBoxLayout()
        self.connect_btn = QPushButton('连接模拟器')
        self.connect_btn.clicked.connect(self.connectEmulator)
        self.addr_input = QLineEdit()
        self.addr_input.setPlaceholderText('127.0.0.1:7555')
        conn_layout.addWidget(self.connect_btn)
        conn_layout.addWidget(self.addr_input)
        left_layout.addLayout(conn_layout)
        
        # 设置区域
        settings_label = QLabel('设置')
        left_layout.addWidget(settings_label)
        
        # ADB路径
        adb_layout = QHBoxLayout()
        adb_layout.addWidget(QLabel('ADB路径:'))
        self.adb_path_input = QLineEdit()
        self.adb_path_input.setPlaceholderText('自动查找')
        adb_layout.addWidget(self.adb_path_input)
        left_layout.addLayout(adb_layout)
        
        # 日志目录
        log_layout = QHBoxLayout()
        log_layout.addWidget(QLabel('日志目录:'))
        self.log_path_input = QLineEdit()
        self.log_path_input.setText('log')
        log_layout.addWidget(self.log_path_input)
        left_layout.addLayout(log_layout)
        
        # 记录文件
        record_layout = QHBoxLayout()
        record_layout.addWidget(QLabel('记录文件:'))
        self.record_path_input = QLineEdit()
        self.record_path_input.setText('#record.txt')
        record_layout.addWidget(self.record_path_input)
        left_layout.addLayout(record_layout)
        
        # 保存间隔
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel('保存间隔(秒):'))
        self.save_interval_input = QLineEdit()
        self.save_interval_input.setText('300')
        interval_layout.addWidget(self.save_interval_input)
        left_layout.addLayout(interval_layout)
        
        # 保存设置按钮
        self.save_settings_btn = QPushButton('保存设置')
        self.save_settings_btn.clicked.connect(self.saveSettings)
        left_layout.addWidget(self.save_settings_btn)
        
        left_panel.setLayout(left_layout)
        
        # 右侧日志面板
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        
        # 设置日志处理器
        log_handler = LogHandler(self.log_text)
        log_handler.setFormatter(logging.Formatter('[%(levelname)s][%(asctime)s]\n%(message)s\n', 
                                                 datefmt='%Y.%m.%d %H:%M:%S'))
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)
        
        # 添加到主布局
        layout.addWidget(left_panel, stretch=3)
        layout.addWidget(self.log_text, stretch=1)
        
        main_widget.setLayout(layout)
        
        # 设置接受拖放
        self.setAcceptDrops(True)
        
    def dragEnterEvent(self, event):
        """处理拖入事件"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        """处理放下事件"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        for file_path in files:
            if os.path.isfile(file_path):
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    self.recordImage(file_path)
            elif os.path.isdir(file_path):
                self.main.record_fromDir(file_path)
                
    def recordImage(self, file_path):
        """记录单个图片"""
        try:
            img = cv2.imread(file_path)
            if img is not None:
                self.main.record_fromImage(img, file_path)
        except Exception as e:
            logging.error(f"处理图片{file_path}失败: {e}")
            
    def recordCurrent(self):
        """记录当前画面"""
        if not self.checkConnection():
            return
        try:
            img = self.main.mumu.screenshot()
            if img is not None:
                self.main.record_fromImage(img, "当前画面")
        except Exception as e:
            logging.error(f"记录当前画面失败: {e}")
            
    def startDraw(self):
        """开始抽卡模式"""
        if not self.checkConnection():
            return
        if QMessageBox.question(self, '确认', '确定要开始抽卡模式吗?') == QMessageBox.StandardButton.Yes:
            self.startWorker(self.main.mode_draw)
            
    def startRecruit(self):
        """开始招募模式"""
        if not self.checkConnection():
            return
        if QMessageBox.question(self, '确认', '确定要开始招募模式吗?') == QMessageBox.StandardButton.Yes:
            self.startWorker(self.main.mode_recruit)
            
    def startWorker(self, func):
        """启动工作线程"""
        self.worker = WorkerThread(func)
        self.worker.finished.connect(self.onWorkerFinished)
        self.worker.error.connect(self.onWorkerError)
        self.worker.start()
        
        self.stop_btn.setEnabled(True)
        self.start_draw_btn.setEnabled(False)
        self.start_recruit_btn.setEnabled(False)
        
    def stopWorker(self):
        """停止工作线程"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.onWorkerFinished()
            
    def onWorkerFinished(self):
        """工作线程完成"""
        self.stop_btn.setEnabled(False)
        self.start_draw_btn.setEnabled(True)
        self.start_recruit_btn.setEnabled(True)
        
    def onWorkerError(self, error_msg):
        """工作线程错误"""
        logging.error(error_msg)
        self.onWorkerFinished()
        
    def saveRecord(self):
        """保存当前记录"""
        try:
            record_file = self.record_path_input.text()
            if not record_file:
                record_file = '#record.txt'
            self.main.record(None, record_file)
            logging.info(f"记录已保存到{record_file}")
        except Exception as e:
            logging.error(f"保存记录失败: {e}")
            
    def connectEmulator(self):
        """连接模拟器"""
        try:
            adb_path = self.adb_path_input.text() or None
            if self.main.mumu.connect(adb_path):
                logging.info("模拟器连接成功")
            else:
                logging.error("模拟器连接失败")
        except Exception as e:
            logging.error(f"连接模拟器失败: {e}")
            
    def checkConnection(self):
        """检查模拟器连接状态"""
        if not self.main.mumu.connected:
            if QMessageBox.question(self, '连接', '需要连接模拟器,是否现在连接?') == QMessageBox.StandardButton.Yes:
                self.connectEmulator()
                return self.main.mumu.connected
            return False
        return True
        
    def loadConfig(self):
        """加载配置"""
        try:
            if os.path.exists('config.yaml'):
                with open('config.yaml', 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    self.addr_input.setText(config.get('addr', ''))
                    self.adb_path_input.setText(config.get('adb_path', ''))
                    self.log_path_input.setText(config.get('log_path', 'log'))
                    self.record_path_input.setText(config.get('record_path', '#record.txt'))
                    self.save_interval_input.setText(str(config.get('save_interval', 300)))
        except Exception as e:
            logging.error(f"加载配置失败: {e}")
            
    def saveSettings(self):
        """保存设置"""
        try:
            config = {
                'addr': self.addr_input.text(),
                'adb_path': self.adb_path_input.text(),
                'log_path': self.log_path_input.text(),
                'record_path': self.record_path_input.text(),
                'save_interval': int(self.save_interval_input.text())
            }
            with open('config.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True)
            logging.info("设置已保存")
        except Exception as e:
            logging.error(f"保存设置失败: {e}")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()

if __name__ == '__main__':
    main()
