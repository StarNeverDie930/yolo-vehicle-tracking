from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
import numpy as np


class VideoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QLabel("请打开视频文件")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background-color: #1e1e1e; color: #aaa; font-size: 16px;")
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)

    def update_frame(self, frame: np.ndarray):
        h, w, ch = frame.shape
        img = QImage(frame.data, w, h, ch * w, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(img)
        scaled = pixmap.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(scaled)

    def clear(self):
        self.label.clear()
        self.label.setText("请打开视频文件")
