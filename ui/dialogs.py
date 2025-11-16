import numpy as np
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QLineEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

class InputWithImageDialog(QDialog):
    def __init__(self, title, label, img, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        
        # 图片显示区域
        img_label = QLabel()
        h, w = img.shape[:2]
        """
        # 限制图片大小
        max_size = 400
        if h > max_size or w > max_size:
            scale = min(max_size/h, max_size/w)
            h, w = int(h*scale), int(w*scale)
        """
        
        # 转换numpy数组为QImage
        if len(img.shape) == 3:
            # 确保数据是C连续的
            img_c = np.ascontiguousarray(img)
            height, width, channel = img_c.shape
            bytes_per_line = 3 * width
            q_img = QImage(img_c.data, width, height, bytes_per_line, QImage.Format_RGB888)
        else:
            # 确保数据是C连续的
            img_c = np.ascontiguousarray(img)
            height, width = img_c.shape
            q_img = QImage(img_c.data, width, height, width, QImage.Format_Grayscale8)
            
        pixmap = QPixmap.fromImage(q_img)
        img_label.setPixmap(pixmap.scaled(w, h, Qt.KeepAspectRatio))
        layout.addWidget(img_label)
        
        # 输入区域
        layout.addWidget(QLabel(label))
        self.input_field = QLineEdit()
        layout.addWidget(self.input_field)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_input(self):
        return self.input_field.text()

    def set_text(self, text):
        self.input_field.setText(text)