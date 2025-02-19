class UI:
    class _OverlayWindow(QWidget):
        """
        小窗口框架，且有动画淡入淡出准备
        使用：实例化，调用setMainWidget设置内容控件
        """
        def __init__(self, parent, func_preClose=None):
            if func_preClose is not None:
                self.preClose = func_preClose
            super().__init__(parent, Qt.FramelessWindowHint)
            # 设置窗口透明度
            self.setWindowOpacity(0.01)
            #
            class Blackground(QWidget):
                def __init__(self, parent):
                    super().__init__(parent, Qt.FramelessWindowHint)
                    # 设置窗口透明度
                    #self.setWindowOpacity(0.01)

                def mousePressEvent(self, event):
                    self.parent().preClose()

                def paintEvent(self, event):
                    # 在这里绘制半透明遮罩层
                    painter = QPainter(self)
                    # 半透明黑色遮罩
                    painter.setBrush(QBrush(QColor(0, 0, 0, 128)))
                    painter.drawRect(self.rect())

            self.Blackground = Blackground
            #
            self.mainWidget = None
            self.init_widget()

        def init_widget(self):
            self.wdgt_blackGround = self.Blackground(self)
            self.vLyt_mainLayout = QVBoxLayout(self)
            self.parent().resized.connect(self.refresh)
            self.refresh()

        def setMainWidget(self, mainWidget):
            self.mainWidget = mainWidget
            self.refresh(b_grab = True)

        def refresh(self, b_grab=False):
            parentGeometry = self.parent().geometry()
            width = parentGeometry.width()
            height = parentGeometry.height()
            self.wdgt_blackGround.setGeometry(QRect(0, 0, width, height))
            self.setGeometry(QRect(0, 0, width, height))
            if self.mainWidget is not None:
                mainWidget_width = self.mainWidget.sizeHint().width()
                mainWidget_height = self.mainWidget.sizeHint().height()
                x = (width - mainWidget_width) // 2
                y = (height - mainWidget_height) // 2
                self.mainWidget.wdgt_backGround.setGeometry(QRect(0, 0, mainWidget_width, mainWidget_height))
                self.mainWidget.setGeometry(x, y, mainWidget_width, mainWidget_height)
            if b_grab:
                self.screenshot = self.grab()

        def setCloseFunc(self, func_close):
            self.preClose = func_close

        def preClose(self):
            self.close()

    def secondaryEncapsulation(self):
        Qte = self
        class _InputBox(QWidget):
            """
            带有提示label、输入、确定、取消，的输入框
            text     是一个对象，存储多语言文本
            s_prompt 是提示label的内容
            func_validator 是核验输入是否合法的函数
            func_finally   是退出时执行的函数（无论输入是否合法，合法才提供输入，否则提供None）
            """
            def __init__(self, parent, text, s_prompt, func_validator, func_finally):
                self.text = text
                self.s_prompt = s_prompt
                self.func_validator = func_validator
                if func_finally is None:
                    self.func_finally = lambda a:None
                else:
                    self.func_finally = func_finally
                #
                super().__init__(parent)
                #
                class Background(QWidget):
                    def paintEvent(self, event):
                        self.setWindowFlags(Qt.FramelessWindowHint)
                        painter = QPainter(self)
                        painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
                        painter.drawRect(self.rect())
                self.Background = Background
                #
                self.output = None
                self.init_UI()

            def init_UI(self):
                self.wdgt_backGround = self.Background(self)
                self.layout = QGridLayout(self)
                self.label = QLabel(self.s_prompt, self)
                self.lineEdit = QLineEdit(self)
                self.pBtn_ok = QPushButton(self.text["确定"], self)
                self.pBtn_cancel = QPushButton(self.text["取消"], self)
                #
                self.lineEdit.textChanged.connect(self.check)
                self.pBtn_ok.clicked.connect(self.preClose)
                self.pBtn_cancel.clicked.connect(self.preClose)
                self.pBtn_ok.setEnabled(False)
                self.label.setFont(g.font_btn_1)
                self.lineEdit.setFont(g.font_btn_1)
                self.pBtn_cancel.setFont(g.font_btn_1)
                self.pBtn_ok.setFont(g.font_btn_1)
                #
                self.layout.addWidget(self.label, 1,1, 1,3)
                self.layout.addWidget(self.lineEdit, 2,1, 1,3)
                self.layout.addWidget(self.pBtn_cancel, 3,1)
                self.layout.addWidget(self.pBtn_ok, 3,3)

            def check(self, text):
                if self.func_validator(text):
                    self.output = text
                    self.pBtn_ok.setEnabled(True)
                else:
                    self.output = None
                    self.pBtn_ok.setEnabled(False)

            def preClose(self):
                if self.output is not None:
                    self.func_finally(self.output)
                self.parent().preClose()
        self._InputBox = _InputBox
        #
        class _MessageBox(QWidget):
            """
            带有两种模式的弹窗提示
            模式一：label、确定按钮、取消按钮
            模式二：label、确定按钮
            参数详见Qte的入口函数
            """
            def __init__(self, parent, text, s_prompt, func_finally, b_cancelMode, b_warning):
                self.text = text
                self.s_prompt = s_prompt
                if func_finally is None:
                    self.func_finally = lambda a:None
                else:
                    self.func_finally = func_finally
                self.b_cancelMode = b_cancelMode
                self.b_warning = b_warning
                #
                super().__init__(parent)
                #
                class Background(QWidget):
                    def paintEvent(self, event):
                        self.setWindowFlags(Qt.FramelessWindowHint)
                        painter = QPainter(self)
                        painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
                        painter.drawRect(self.rect())
                self.Background = Background
                #
                self.init_UI()

            def init_UI(self):
                self.wdgt_backGround = self.Background(self)
                self.layout = QGridLayout(self)
                self.label = QLabel(self.s_prompt, self)
                self.pBtn_ok = QPushButton(self.text["确定"], self)
                if self.b_cancelMode:
                    self.pBtn_cancel = QPushButton(self.text["取消"], self)
                #
                self.pBtn_ok.clicked.connect(closureProduce(self.preClose, True))
                if self.b_cancelMode:
                    self.pBtn_cancel.clicked.connect(closureProduce(self.preClose, False))
                self.label.setFont(g.font_btn_1)
                if self.b_cancelMode:
                    self.pBtn_cancel.setFont(g.font_btn_1)
                self.pBtn_ok.setFont(g.font_btn_1)
                if self.b_warning:
                    bg = "#FF0000"
                    fg = "#FFFFFF"
                    self.pBtn_ok.setStyleSheet(f"background-color: {bg}; color: {fg};")
                #
                self.layout.addWidget(self.label, 1,1, 1,3)
                if self.b_cancelMode:
                    self.layout.addWidget(self.pBtn_cancel, 2,1)
                self.layout.addWidget(self.pBtn_ok, 2,3)

            def preClose(self, b_choice):
                self.func_finally(b_choice)
                self.parent().preClose()
        self._MessageBox = _MessageBox