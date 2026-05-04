from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox

from utils.taxonomy import CLASS_NAMES


class ResultPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # 总计数
        group = QGroupBox("统计信息")
        g_layout = QVBoxLayout(group)

        self.count_label = QLabel("车辆总数: 0")
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
        cls_group = QGroupBox("分车型统计（累计）")
        cls_layout = QVBoxLayout(cls_group)
        self.class_labels = {}
        for cid, name in CLASS_NAMES.items():
            lbl = QLabel(f"{name}: 0")
            cls_layout.addWidget(lbl)
            self.class_labels[cid] = lbl
        layout.addWidget(cls_group)

        # 流量统计
        flow_group = QGroupBox("流量窗口统计")
        flow_layout = QVBoxLayout(flow_group)
        self.flow_total_label = QLabel("合计: 0 辆")
        self.flow_total_label.setStyleSheet("font-weight: bold;")
        flow_layout.addWidget(self.flow_total_label)
        self.flow_labels = {}
        for cid, name in CLASS_NAMES.items():
            lbl = QLabel(f"{name}: 0")
            flow_layout.addWidget(lbl)
            self.flow_labels[cid] = lbl
        layout.addWidget(flow_group)

        layout.addStretch()

    def update_stats(self, count, current_frame, total_frames, track_count, fps=None,
                     class_counts=None, flow_rate=None):
        self.count_label.setText(f"车辆总数: {count}")
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

        if class_counts:
            for cid, lbl in self.class_labels.items():
                lbl.setText(f"{CLASS_NAMES[cid]}: {class_counts.get(cid, 0)}")

        if flow_rate:
            total_flow = sum(flow_rate.values())
            self.flow_total_label.setText(f"合计: {total_flow} 辆")
            for cid, lbl in self.flow_labels.items():
                lbl.setText(f"{CLASS_NAMES[cid]}: {flow_rate.get(cid, 0)}")

    def set_device(self, device_name):
        self.device_label.setText(f"计算设备: {device_name}")
