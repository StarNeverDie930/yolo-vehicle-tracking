"""左侧控制面板。

负责收集模型选择、检测阈值、计数模式和处理进度等用户输入，并通过 Qt
信号把配置变更通知主窗口。
"""

import glob
import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QDoubleSpinBox,
                               QProgressBar, QComboBox)
from PySide6.QtCore import Signal


class ControlPanel(QWidget):
    """参数控制组件，主窗口只监听信号，不直接读取控件细节。"""

    conf_changed = Signal(float)
    iou_changed = Signal(float)
    count_mode_changed = Signal(str)
    line_direction_changed = Signal(str)
    line_pos_changed = Signal(float)
    model_changed = Signal(str)  # 模型路径

    def __init__(self, config, parent=None):
        """根据配置文件初始化所有控制项。"""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        counter_cfg = config.get("counter", {})

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

        # 计数模式
        layout.addWidget(QLabel("计数模式"))
        self.count_mode_combo = QComboBox()
        self.count_mode_combo.addItem("按 ID 去重计数", "unique_track")
        self.count_mode_combo.addItem("越线计数", "line_crossing")
        self._set_combo_data(
            self.count_mode_combo,
            counter_cfg.get("mode", "unique_track"),
        )
        self.count_mode_combo.currentIndexChanged.connect(
            self._on_count_mode_changed
        )
        layout.addWidget(self.count_mode_combo)

        # 越线方向
        self.line_direction_label = QLabel("越线方向")
        layout.addWidget(self.line_direction_label)
        self.line_direction_combo = QComboBox()
        self.line_direction_combo.addItem("水平线", "horizontal")
        self.line_direction_combo.addItem("垂直线", "vertical")
        self._set_combo_data(
            self.line_direction_combo,
            counter_cfg.get("direction", "horizontal"),
        )
        self.line_direction_combo.currentIndexChanged.connect(
            self._on_line_direction_changed
        )
        layout.addWidget(self.line_direction_combo)

        # 越线位置
        self.line_position_label = QLabel("越线位置")
        layout.addWidget(self.line_position_label)
        self.line_pos_spin = QDoubleSpinBox()
        self.line_pos_spin.setRange(0.05, 0.95)
        self.line_pos_spin.setSingleStep(0.05)
        self.line_pos_spin.setDecimals(2)
        self.line_pos_spin.setValue(counter_cfg.get("line_position", 0.6))
        self.line_pos_spin.valueChanged.connect(self.line_pos_changed.emit)
        layout.addWidget(self.line_pos_spin)
        self._set_line_controls_enabled(
            self.count_mode_combo.currentData() == "line_crossing"
        )

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
        """更新处理进度条。"""
        self.progress_bar.setValue(value)

    def _set_combo_data(self, combo, value):
        """按业务值选中下拉框项，找不到时回退到第一项。"""
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    def _on_count_mode_changed(self, _index):
        """计数模式变化时，同步控制越线相关控件显隐状态。"""
        mode = self.count_mode_combo.currentData()
        self._set_line_controls_enabled(mode == "line_crossing")
        self.count_mode_changed.emit(mode)

    def _on_line_direction_changed(self, _index):
        """转发越线方向变更。"""
        self.line_direction_changed.emit(self.line_direction_combo.currentData())

    def _set_line_controls_enabled(self, enabled):
        """仅在越线计数模式下启用越线方向和位置控件。"""
        self.line_direction_label.setEnabled(enabled)
        self.line_direction_combo.setEnabled(enabled)
        self.line_position_label.setEnabled(enabled)
        self.line_pos_spin.setEnabled(enabled)
