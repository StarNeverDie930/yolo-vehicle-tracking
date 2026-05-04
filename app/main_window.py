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
    frame_ready = Signal(np.ndarray, int, int, int, int, object, object)
    processing_completed = Signal(str, int, object, object)
    processing_cancelled = Signal(str, object)
    processing_failed = Signal(str, str)

    def __init__(self, pipeline, video_path, mode="process", output_path=None):
        super().__init__()
        self.pipeline = pipeline
        self.video_path = video_path
        self.mode = mode
        self.output_path = output_path
        self._running = True
        self._stop_requested = False

    def run(self):
        from utils.video_io import VideoReader, VideoWriter

        reader = None
        writer = None
        frame_idx = 0
        result_dir = None
        error_message = None
        cancelled = False

        try:
            self.pipeline.reset()
            reader = VideoReader(self.video_path, fallback_fps=self.pipeline.video_fallback_fps)
            fps = reader.fps or self.pipeline.video_fallback_fps
            if self.output_path:
                writer = VideoWriter(
                    self.output_path,
                    fps,
                    reader.width,
                    reader.height,
                    codec=self.pipeline.video_output_codec,
                    fallback_fps=self.pipeline.video_fallback_fps,
                )

            total = reader.frame_count
            start_time = time.perf_counter()

            while self._running:
                ret, frame = reader.read()
                if not ret:
                    break

                annotated, tracks, count, class_counts, flow_rate = self.pipeline.process_frame(
                    frame,
                    frame_idx=frame_idx,
                    fps=fps,
                )

                if writer:
                    writer.write(annotated)

                frame_idx += 1
                self.frame_ready.emit(annotated, frame_idx, total, count, len(tracks), class_counts, flow_rate)

            cancelled = self._stop_requested
            elapsed = time.perf_counter() - start_time
            if not cancelled:
                if frame_idx == 0:
                    raise RuntimeError("视频没有可读取帧")
                avg_fps = frame_idx / elapsed if elapsed > 0 else 0.0
                result_dir = self.pipeline.export_analysis(
                    video_path=self.video_path,
                    frame_count=frame_idx,
                    elapsed_sec=elapsed,
                    average_fps=avg_fps,
                )
        except Exception as exc:
            error_message = str(exc)
        finally:
            if reader:
                reader.release()
            if writer:
                writer.release()

        if error_message:
            self.processing_failed.emit(self.mode, error_message)
        elif cancelled:
            self.processing_cancelled.emit(self.mode, result_dir)
        else:
            self.processing_completed.emit(
                self.mode,
                self.pipeline.counter.count,
                result_dir,
                self.output_path,
            )

    def stop(self):
        self._stop_requested = True
        self._running = False


class MainWindow(QMainWindow):
    STATE_IDLE_NO_VIDEO = "idle_no_video"
    STATE_IDLE_VIDEO_LOADED = "idle_video_loaded"
    STATE_PROCESSING = "processing"
    STATE_STOPPING = "stopping"
    STATE_PROCESSED_UNSAVED = "processed_unsaved"
    STATE_PROCESSED_SAVED = "processed_saved"
    STATE_EXPORTING = "exporting"
    STATE_ERROR = "error"

    def __init__(self, config_path="config.yaml"):
        super().__init__()
        self.setWindowTitle("基于YOLO的车辆轨迹与目标检测系统")
        self.setMinimumSize(1200, 700)

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.pipeline = ProcessingPipeline(self.config)
        self.worker = None
        self.video_path = None
        self.last_frame = None
        self.last_result_dir = None
        self.processing_completed = False
        self.processed_video_saved = False
        self.processed_output_path = None
        self._pending_output_path = None
        self._pre_export_snapshot = None
        self._close_after_worker_finished = False
        self._force_close = False
        self._pending_message = None
        self._last_time = time.time()
        self.ui_state = self.STATE_IDLE_NO_VIDEO

        self._init_ui()
        self._init_toolbar()
        self._connect_signals()
        self._refresh_controls()

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
        toolbar.addAction(self.start_action)

        self.stop_action = QAction("停止", self)
        toolbar.addAction(self.stop_action)

        self.export_action = QAction("导出视频", self)
        toolbar.addAction(self.export_action)

        self.view_heatmap_action = QAction("查看热力图", self)
        toolbar.addAction(self.view_heatmap_action)

        self.save_heatmap_action = QAction("保存热力图", self)
        toolbar.addAction(self.save_heatmap_action)

        self.heatmap_action = self.save_heatmap_action

    def _connect_signals(self):
        self.open_action.triggered.connect(self._open_video)
        self.start_action.triggered.connect(self._start_processing)
        self.stop_action.triggered.connect(self._stop_processing)
        self.export_action.triggered.connect(self._export_video)
        self.view_heatmap_action.triggered.connect(self._view_heatmap)
        self.save_heatmap_action.triggered.connect(self._save_heatmap)

        self.control_panel.conf_changed.connect(self._update_conf)
        self.control_panel.iou_changed.connect(self._update_iou)
        self.control_panel.line_pos_changed.connect(self._update_line_pos)
        self.control_panel.model_changed.connect(self._switch_model)

    def closeEvent(self, event):
        if self._force_close or not self._is_worker_running():
            event.accept()
            return

        reply = QMessageBox.question(
            self,
            "退出确认",
            "后台任务仍在运行，是否停止任务并退出？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            event.ignore()
            return

        self._close_after_worker_finished = True
        self._request_stop("正在停止后台任务并准备退出...")
        if self.worker and self.worker.wait(5000):
            self._close_after_worker_finished = False
            self._force_close = True
            self.worker = None
            event.accept()
        else:
            QMessageBox.warning(self, "提示", "后台任务仍在停止中，请稍后再关闭窗口。")
            event.ignore()

    def _open_video(self):
        if self._is_worker_running():
            QMessageBox.warning(self, "提示", "请先等待当前任务结束或停止后再打开新视频")
            return

        if self.processing_completed and not self.processed_video_saved:
            reply = QMessageBox.question(
                self,
                "未保存视频",
                "您还有一个处理完成的视频未保存，是否要继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov);;所有文件 (*)",
        )
        if path:
            self._load_video(path)

    def _load_video(self, path):
        self.video_path = path
        self.pipeline.reset()
        self.last_frame = None
        self.last_result_dir = None
        self.processing_completed = False
        self.processed_video_saved = False
        self.processed_output_path = None
        self._pre_export_snapshot = None
        self.control_panel.set_progress(0)
        self.video_widget.clear()
        self.setWindowTitle(f"基于YOLO的车辆轨迹与目标检测系统 - {path}")
        self.ui_state = self.STATE_IDLE_VIDEO_LOADED
        self._refresh_controls()
        self.statusBar().showMessage(f"已打开视频: {os.path.basename(path)}", 3000)

    def _start_processing(self):
        if not self.video_path:
            return
        if self._is_worker_running():
            QMessageBox.warning(self, "提示", "请先停止当前处理再开始新的任务")
            return

        self._clear_result_state()
        self.ui_state = self.STATE_PROCESSING
        self._start_worker(mode="process")

    def _stop_processing(self):
        if not self._is_worker_running():
            return
        self._request_stop("正在停止任务...")

    def _request_stop(self, message):
        if self.worker:
            self.worker.stop()
        self.ui_state = self.STATE_STOPPING
        self._refresh_controls()
        self.statusBar().showMessage(message, 3000)

    def _start_worker(self, mode, output_path=None):
        self.worker = ProcessingWorker(self.pipeline, self.video_path, mode=mode, output_path=output_path)
        self.worker.frame_ready.connect(self._on_frame_ready)
        self.worker.processing_completed.connect(self._on_processing_completed)
        self.worker.processing_cancelled.connect(self._on_processing_cancelled)
        self.worker.processing_failed.connect(self._on_worker_error)
        self.worker.finished.connect(self._on_worker_thread_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self._last_time = time.time()
        self._refresh_controls()
        self.worker.start()

    @Slot(np.ndarray, int, int, int, int, object, object)
    def _on_frame_ready(self, frame, frame_idx, total, count, track_count, class_counts, flow_rate):
        self.last_frame = frame
        self.video_widget.update_frame(frame)

        now = time.time()
        fps = 1.0 / max(now - self._last_time, 1e-6)
        self._last_time = now

        progress = int(frame_idx / max(total, 1) * 100) if total else 0
        progress = min(progress, 99)
        self.control_panel.set_progress(progress)
        self.result_panel.update_stats(count, frame_idx, total, track_count, fps, class_counts, flow_rate)

    @Slot(str, int, object, object)
    def _on_processing_completed(self, mode, total_count, result_dir, output_path):
        self.last_result_dir = result_dir
        self._pre_export_snapshot = None

        if mode == "export":
            self.processing_completed = True
            self.processed_video_saved = True
            self.processed_output_path = output_path
            self.ui_state = self.STATE_PROCESSED_SAVED
            self.control_panel.set_progress(100)
            self._refresh_controls()
            if not self._close_after_worker_finished:
                QMessageBox.information(
                    self,
                    "导出完成",
                    f"视频已成功导出！\n导出路径：{output_path}\n分析结果已保存到：{result_dir}",
                )
            return

        self.processing_completed = True
        self.processed_video_saved = False
        self.processed_output_path = None
        self.ui_state = self.STATE_PROCESSED_UNSAVED
        self.control_panel.set_progress(100)
        self._refresh_controls()
        if not self._close_after_worker_finished:
            QMessageBox.information(
                self,
                "完成",
                f"处理完成！共检测到 {total_count} 辆车。\n结果已保存到：{result_dir}",
            )

    @Slot(str, object)
    def _on_processing_cancelled(self, mode, result_dir):
        if mode == "export" and self._pre_export_snapshot is not None:
            self._restore_snapshot_after_export()
        else:
            self._clear_result_state()
            self.ui_state = self.STATE_IDLE_VIDEO_LOADED if self.video_path else self.STATE_IDLE_NO_VIDEO

        self._refresh_controls()
        if not self._close_after_worker_finished:
            QMessageBox.information(self, "已停止", "当前任务已停止。")

    @Slot(str, str)
    def _on_worker_error(self, mode, message):
        if mode == "export" and self._pre_export_snapshot is not None:
            self._restore_snapshot_after_export()
        else:
            self._clear_result_state()
            self.ui_state = self.STATE_IDLE_VIDEO_LOADED if self.video_path else self.STATE_IDLE_NO_VIDEO

        self._refresh_controls()
        if not self._close_after_worker_finished:
            title = "导出失败" if mode == "export" else "处理失败"
            QMessageBox.critical(self, title, message)

    @Slot()
    def _on_worker_thread_finished(self):
        worker = self.sender()
        if worker is self.worker:
            self.worker = None
        self._refresh_controls()
        if self._close_after_worker_finished:
            self._force_close = True
            self.close()

    def _export_video(self):
        if not self.video_path:
            return
        if self._is_worker_running():
            QMessageBox.warning(self, "提示", "请先停止当前任务后再导出视频")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出视频",
            "",
            "MP4 (*.mp4);;AVI (*.avi)",
        )
        if not path:
            return

        self._pre_export_snapshot = self._capture_current_result_snapshot()
        self._pending_output_path = path
        if not self.processing_completed:
            self._clear_result_state()
        self.ui_state = self.STATE_EXPORTING
        self._start_worker(mode="export", output_path=path)

    def _view_heatmap(self):
        if not self._can_use_heatmap():
            QMessageBox.information(self, "提示", "当前没有可查看的热力图。")
            return

        base_frame = self.last_frame
        heatmap = self.pipeline.get_heatmap(base_frame.shape)
        result = overlay_heatmap(base_frame, heatmap)
        self.video_widget.update_frame(result)
        self.statusBar().showMessage("热力图已显示到画面中", 3000)

    def _save_heatmap(self):
        if not self._can_use_heatmap():
            QMessageBox.information(self, "提示", "当前没有可保存的热力图。")
            return

        frame = self.pipeline.last_frame if self.pipeline.last_frame is not None else self.last_frame
        output_dir = self.last_result_dir or self.pipeline.last_result_dir
        if output_dir is None:
            output_dir = self.pipeline._default_result_dir()
            self.last_result_dir = output_dir

        paths = self.pipeline.save_heatmap(output_dir=output_dir, frame=frame)
        QMessageBox.information(
            self,
            "热力图已保存",
            f"原始热力图：{paths['heatmap']}\n叠加热力图：{paths['overlay']}",
        )

    def _update_conf(self, value):
        self.pipeline.detector.conf = value

    def _update_iou(self, value):
        self.pipeline.detector.iou = value

    def _update_line_pos(self, _value):
        self.config["counter"]["line_position"] = float(_value)
        self.pipeline.counter.line_position = float(_value)

    def _switch_model(self, model_path):
        if not model_path:
            return
        if self._is_worker_running():
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

    def _restore_idle_controls(self):
        self._refresh_controls()

    def _refresh_controls(self):
        busy = self._is_worker_running() or self.ui_state in {
            self.STATE_PROCESSING,
            self.STATE_STOPPING,
            self.STATE_EXPORTING,
        }
        has_video = bool(self.video_path)
        has_heatmap = self._can_use_heatmap()

        self.open_action.setEnabled(not busy)
        self.start_action.setEnabled(has_video and not busy)
        self.stop_action.setEnabled(
            self._is_worker_running()
            and self.ui_state in {self.STATE_PROCESSING, self.STATE_EXPORTING}
        )
        self.export_action.setEnabled(has_video and not busy)
        self.view_heatmap_action.setEnabled(has_heatmap and not busy)
        self.save_heatmap_action.setEnabled(has_heatmap and not busy)
        self.control_panel.setEnabled(not busy)

    def _is_worker_running(self):
        return self.worker is not None and self.worker.isRunning()

    def _clear_result_state(self):
        self.last_frame = None
        self.last_result_dir = None
        self.processing_completed = False
        self.processed_video_saved = False
        self.processed_output_path = None
        self._pending_output_path = None
        self.control_panel.set_progress(0)
        self.ui_state = self.STATE_IDLE_VIDEO_LOADED if self.video_path else self.STATE_IDLE_NO_VIDEO
        self._refresh_controls()

    def _capture_current_result_snapshot(self):
        return {
            "processing_completed": self.processing_completed,
            "processed_video_saved": self.processed_video_saved,
            "processed_output_path": self.processed_output_path,
            "last_result_dir": self.last_result_dir,
        }

    def _restore_snapshot_after_export(self):
        snapshot = self._pre_export_snapshot or {}
        self.processing_completed = snapshot.get("processing_completed", False)
        self.processed_video_saved = snapshot.get("processed_video_saved", False)
        self.processed_output_path = snapshot.get("processed_output_path")
        self.last_result_dir = snapshot.get("last_result_dir")
        self.last_frame = None
        self._pending_output_path = None
        self._pre_export_snapshot = None
        if self.processing_completed:
            self.ui_state = self._completed_state()
        else:
            self.ui_state = self.STATE_IDLE_VIDEO_LOADED if self.video_path else self.STATE_IDLE_NO_VIDEO

    def _completed_state(self):
        return self.STATE_PROCESSED_SAVED if self.processed_video_saved else self.STATE_PROCESSED_UNSAVED

    def _can_use_heatmap(self):
        return self.processing_completed and self.last_frame is not None and self.ui_state in {
            self.STATE_PROCESSED_UNSAVED,
            self.STATE_PROCESSED_SAVED,
        }
