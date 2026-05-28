"""右侧结果展示面板。

集中展示累计计数、当前帧目标数、处理帧率、预计剩余时间、分车型统计和
滑动流量窗口统计。
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox

from utils.taxonomy import CLASS_NAMES


class ResultPanel(QWidget):
    """处理过程中的统计信息展示组件。"""

    def __init__(self, parent=None):
        """构建统计、车型和流量三个展示区域。"""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.count_mode = "unique_track"
        self._last_count = 0

        # 总计数
        group = QGroupBox("统计信息")
        g_layout = QVBoxLayout(group)

        self.count_label = QLabel("累计车辆数: 0")
        self.count_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        g_layout.addWidget(self.count_label)

        self.fps_label = QLabel("处理帧率: --")
        g_layout.addWidget(self.fps_label)

        self.frame_label = QLabel("当前帧: 0 / 0")
        g_layout.addWidget(self.frame_label)

        self.track_label = QLabel("当前画面: 0 辆")
        g_layout.addWidget(self.track_label)

        self.eta_label = QLabel("预计剩余: --")
        g_layout.addWidget(self.eta_label)

        self.device_label = QLabel("计算设备: --")
        g_layout.addWidget(self.device_label)

        layout.addWidget(group)

        # 分车型计数
        self.cls_group = QGroupBox("分车型统计（累计）")
        cls_layout = QVBoxLayout(self.cls_group)
        self.class_labels = {}
        for cid, name in CLASS_NAMES.items():
            lbl = QLabel(f"{name}: 0")
            cls_layout.addWidget(lbl)
            self.class_labels[cid] = lbl
        layout.addWidget(self.cls_group)

        # 流量统计
        self.flow_group = QGroupBox("流量窗口统计")
        flow_layout = QVBoxLayout(self.flow_group)
        self.flow_total_label = QLabel("合计: 0 辆")
        self.flow_total_label.setStyleSheet("font-weight: bold;")
        flow_layout.addWidget(self.flow_total_label)
        self.flow_labels = {}
        for cid, name in CLASS_NAMES.items():
            lbl = QLabel(f"{name}: 0")
            flow_layout.addWidget(lbl)
            self.flow_labels[cid] = lbl
        layout.addWidget(self.flow_group)

        layout.addStretch()

    def update_stats(self, count, current_frame, total_frames, track_count, fps=None,
                     class_counts=None, flow_rate=None, count_mode=None):
        """刷新当前处理进度和各类统计数字。"""
        if count_mode is not None:
            self.set_count_mode(count_mode)
        self._last_count = count
        self.count_label.setText(f"{self._count_title()}: {count}")
        self.frame_label.setText(f"当前帧: {current_frame} / {total_frames}")
        self.track_label.setText(f"当前画面: {track_count} 辆")
        if fps is not None:
            self.fps_label.setText(f"处理帧率: {fps:.1f}")
            remaining = total_frames - current_frame
            if fps > 0 and remaining > 0:
                eta_sec = remaining / fps
                m, s = divmod(int(eta_sec), 60)
                self.eta_label.setText(f"预计剩余: {m}分{s}秒")
            else:
                self.eta_label.setText("预计剩余: --")

        if class_counts is not None:
            for cid, lbl in self.class_labels.items():
                lbl.setText(f"{CLASS_NAMES[cid]}: {class_counts.get(cid, 0)}")

        if flow_rate is not None:
            total_flow = sum(flow_rate.values())
            self.flow_total_label.setText(f"合计: {total_flow} 辆")
            for cid, lbl in self.flow_labels.items():
                lbl.setText(f"{CLASS_NAMES[cid]}: {flow_rate.get(cid, 0)}")

    def set_device(self, device_name):
        """显示当前推理设备。"""
        self.device_label.setText(f"计算设备: {device_name}")

    def set_count_mode(self, count_mode):
        """切换计数口径对应的文案。"""
        self.count_mode = count_mode if count_mode == "line_crossing" else "unique_track"
        self.count_label.setText(f"{self._count_title()}: {self._last_count}")
        if self.count_mode == "line_crossing":
            self.cls_group.setTitle("分车型统计（越线）")
            self.flow_group.setTitle("流量窗口统计（越线）")
        else:
            self.cls_group.setTitle("分车型统计（累计）")
            self.flow_group.setTitle("流量窗口统计")

    def reset_stats(self):
        """把所有统计标签恢复到初始状态。"""
        self._last_count = 0
        self.count_label.setText(f"{self._count_title()}: 0")
        self.fps_label.setText("处理帧率: --")
        self.frame_label.setText("当前帧: 0 / 0")
        self.track_label.setText("当前画面: 0 辆")
        self.eta_label.setText("预计剩余: --")
        for cid, lbl in self.class_labels.items():
            lbl.setText(f"{CLASS_NAMES[cid]}: 0")
        self.flow_total_label.setText("合计: 0 辆")
        for cid, lbl in self.flow_labels.items():
            lbl.setText(f"{CLASS_NAMES[cid]}: 0")

    def _count_title(self):
        """根据当前计数模式返回主计数标签标题。"""
        if self.count_mode == "line_crossing":
            return "越线车辆数"
        return "累计车辆数"
