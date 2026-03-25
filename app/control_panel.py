import glob
import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QSlider, QDoubleSpinBox, QPushButton, QProgressBar,
                               QComboBox)
from PySide6.QtCore import Qt, Signal


class ControlPanel(QWidget):
    conf_changed = Signal(float)
    iou_changed = Signal(float)
    line_pos_changed = Signal(float)
    model_changed = Signal(str)  # 模型路径

    def __init__(self, config, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # 模型选择
        layout.addWidget(QLabel("检测模型"))
        self.model_combo = QComboBox()
        self._scan_models(config["model"]["path"])
        self.model_combo.currentIndexChanged.connect(
            lambda _: self.model_changed.emit(self.model_combo.currentData())
        )
        layout.addWidget(self.model_combo)

        # 置信度阈值
        layout.addWidget(QLabel("置信度阈值"))
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.1, 1.0)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(config["model"]["conf"])
        self.conf_spin.valueChanged.connect(self.conf_changed.emit)
        layout.addWidget(self.conf_spin)

        # IoU 阈值
        layout.addWidget(QLabel("IoU 阈值"))
        self.iou_spin = QDoubleSpinBox()
        self.iou_spin.setRange(0.1, 1.0)
        self.iou_spin.setSingleStep(0.05)
        self.iou_spin.setValue(config["model"]["iou"])
        self.iou_spin.valueChanged.connect(self.iou_changed.emit)
        layout.addWidget(self.iou_spin)

        # 计数线位置
        layout.addWidget(QLabel("计数线位置"))
        self.line_slider = QSlider(Qt.Horizontal)
        self.line_slider.setRange(10, 90)
        self.line_slider.setValue(int(config["counter"]["line_position"] * 100))
        self.line_slider.valueChanged.connect(lambda v: self.line_pos_changed.emit(v / 100.0))
        layout.addWidget(self.line_slider)

        # 进度条
        layout.addWidget(QLabel("处理进度"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

    def _scan_models(self, current_model):
        """扫描项目中所有 .pt 模型文件"""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        patterns = [
            os.path.join(base, "*.pt"),
            os.path.join(base, "weights", "*.pt"),
            os.path.join(base, "runs", "**", "*.pt"),
        ]
        paths = set()
        for p in patterns:
            paths.update(glob.glob(p, recursive=True))

        current_idx = 0
        for i, path in enumerate(sorted(paths)):
            name = os.path.relpath(path, base)
            self.model_combo.addItem(name, path)
            if os.path.basename(path) == os.path.basename(current_model):
                current_idx = i
        self.model_combo.setCurrentIndex(current_idx)

    def set_progress(self, value):
        self.progress_bar.setValue(value)
