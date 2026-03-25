import os
import time
import yaml
import numpy as np
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                               QToolBar, QFileDialog, QMessageBox, QSplitter)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QAction

from app.video_widget import VideoWidget
from app.control_panel import ControlPanel
from app.result_panel import ResultPanel
from core.pipeline import ProcessingPipeline
from analysis.heatmap import overlay_heatmap


class ProcessingWorker(QThread):
    frame_ready = Signal(np.ndarray, int, int, int, int, object, object)  # frame, frame_idx, total, count, track_count, class_counts, flow_rate
    finished = Signal(int)

    def __init__(self, pipeline, video_path, output_path=None):
        super().__init__()
        self.pipeline = pipeline
        self.video_path = video_path
        self.output_path = output_path
        self._running = True

    def run(self):
        from utils.video_io import VideoReader, VideoWriter

        self.pipeline.reset()
        reader = VideoReader(self.video_path)
        writer = None
        if self.output_path:
            writer = VideoWriter(self.output_path, reader.fps, reader.width, reader.height)

        frame_idx = 0
        total = reader.frame_count

        while self._running:
            ret, frame = reader.read()
            if not ret:
                break

            annotated, tracks, count, class_counts, flow_rate = self.pipeline.process_frame(frame)

            if writer:
                writer.write(annotated)

            frame_idx += 1
            self.frame_ready.emit(annotated, frame_idx, total, count, len(tracks), class_counts, flow_rate)

        reader.release()
        if writer:
            writer.release()
        self.finished.emit(self.pipeline.counter.count)

    def stop(self):
        self._running = False


class MainWindow(QMainWindow):
    def __init__(self, config_path="config.yaml"):
        super().__init__()
        self.setWindowTitle("基于YOLO的车辆轨迹与目标检测系统")
        self.setMinimumSize(1200, 700)

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.pipeline = ProcessingPipeline(self.config)
        self.worker = None
        self.last_frame = None
        self._last_time = time.time()

        self._init_ui()
        self._init_toolbar()
        self._connect_signals()

        device = self.pipeline.detector.device
        import torch
        if device != "cpu" and torch.cuda.is_available():
            name = torch.cuda.get_device_name(int(device))
            self.result_panel.set_device(f"GPU ({name})")
        else:
            self.result_panel.set_device("CPU")

    def _init_ui(self):
        splitter = QSplitter(Qt.Horizontal)

        self.video_widget = VideoWidget()
        splitter.addWidget(self.video_widget)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.control_panel = ControlPanel(self.config)
        self.result_panel = ResultPanel()
        right_layout.addWidget(self.control_panel)
        right_layout.addWidget(self.result_panel)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        self.setCentralWidget(splitter)

    def _init_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        self.open_action = QAction("打开视频", self)
        toolbar.addAction(self.open_action)

        self.start_action = QAction("开始处理", self)
        self.start_action.setEnabled(False)
        toolbar.addAction(self.start_action)

        self.stop_action = QAction("停止", self)
        self.stop_action.setEnabled(False)
        toolbar.addAction(self.stop_action)

        self.export_action = QAction("导出视频", self)
        self.export_action.setEnabled(False)
        toolbar.addAction(self.export_action)

        self.heatmap_action = QAction("生成热力图", self)
        self.heatmap_action.setEnabled(False)
        toolbar.addAction(self.heatmap_action)

    def _connect_signals(self):
        self.open_action.triggered.connect(self._open_video)
        self.start_action.triggered.connect(self._start_processing)
        self.stop_action.triggered.connect(self._stop_processing)
        self.export_action.triggered.connect(self._export_video)
        self.heatmap_action.triggered.connect(self._show_heatmap)

        self.control_panel.conf_changed.connect(self._update_conf)
        self.control_panel.iou_changed.connect(self._update_iou)
        self.control_panel.line_pos_changed.connect(self._update_line_pos)
        self.control_panel.model_changed.connect(self._switch_model)

    def _open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mkv *.mov);;所有文件 (*)")
        if path:
            self.video_path = path
            self.start_action.setEnabled(True)
            self.setWindowTitle(f"基于YOLO的车辆轨迹与目标检测系统 - {path}")

    def _start_processing(self):
        if not hasattr(self, "video_path"):
            return

        self.start_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        self.export_action.setEnabled(False)
        self.heatmap_action.setEnabled(False)

        self.worker = ProcessingWorker(self.pipeline, self.video_path)
        self.worker.frame_ready.connect(self._on_frame_ready)
        self.worker.finished.connect(self._on_finished)
        self._last_time = time.time()
        self.worker.start()

    def _stop_processing(self):
        if self.worker:
            self.worker.stop()

    @Slot(np.ndarray, int, int, int, int, object, object)
    def _on_frame_ready(self, frame, frame_idx, total, count, track_count, class_counts, flow_rate):
        self.last_frame = frame
        self.video_widget.update_frame(frame)

        now = time.time()
        fps = 1.0 / max(now - self._last_time, 1e-6)
        self._last_time = now

        progress = int(frame_idx / max(total, 1) * 100)
        self.control_panel.set_progress(progress)
        self.result_panel.update_stats(count, frame_idx, total, track_count, fps, class_counts, flow_rate)

    @Slot(int)
    def _on_finished(self, total_count):
        self.start_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.export_action.setEnabled(True)
        self.heatmap_action.setEnabled(True)
        self.control_panel.set_progress(100)
        QMessageBox.information(self, "完成", f"处理完成！共检测到 {total_count} 辆车。")

    def _export_video(self):
        if not hasattr(self, "video_path"):
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出视频", "", "MP4 (*.mp4);;AVI (*.avi)")
        if path:
            self.start_action.setEnabled(False)
            self.worker = ProcessingWorker(self.pipeline, self.video_path, path)
            self.worker.frame_ready.connect(self._on_frame_ready)
            self.worker.finished.connect(self._on_export_finished)
            self.worker.start()

    @Slot(int)
    def _on_export_finished(self, total_count):
        self.start_action.setEnabled(True)
        QMessageBox.information(self, "导出完成", "视频已成功导出！")

    def _show_heatmap(self):
        if self.last_frame is not None:
            heatmap = self.pipeline.get_heatmap(self.last_frame.shape)
            result = overlay_heatmap(self.last_frame, heatmap)
            self.video_widget.update_frame(result)

    def _update_conf(self, value):
        self.pipeline.detector.conf = value

    def _update_iou(self, value):
        self.pipeline.detector.iou = value

    def _update_line_pos(self, _value):
        pass  # 已改为 track_id 去重计数，无计数线

    def _switch_model(self, model_path):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "提示", "请先停止当前处理再切换模型")
            return
        self.pipeline.switch_model(model_path)
        device = self.pipeline.detector.device
        import torch
        if device != "cpu" and torch.cuda.is_available():
            name = torch.cuda.get_device_name(int(device))
            self.result_panel.set_device(f"GPU ({name})")
        else:
            self.result_panel.set_device("CPU")
        self.statusBar().showMessage(f"已切换模型: {os.path.basename(model_path)}", 3000)