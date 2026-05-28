"""主窗口与后台处理线程。

该模块连接 GUI 控件和 ProcessingPipeline：主线程负责界面状态、用户操作和
结果展示，ProcessingWorker 在线程中执行耗时的视频处理，避免界面卡死。
"""

import os
import shutil
import tempfile
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
    """后台视频处理线程，按帧发送结果给主线程刷新界面。"""

    frame_ready = Signal(np.ndarray, int, int, int, int, object, object)
    processing_completed = Signal(str, int, object, object)
    processing_cancelled = Signal(str, object)
    processing_failed = Signal(str, str)

    def __init__(self, pipeline, video_path, mode="process", output_path=None, optional_output=False):
        """保存任务参数；mode 用于区分普通处理和导出任务。"""
        super().__init__()
        self.pipeline = pipeline
        self.video_path = video_path
        self.mode = mode
        self.output_path = output_path
        self.optional_output = optional_output
        self._running = True
        self._stop_requested = False

    def run(self):
        """读取视频、逐帧处理，并可选写出标注视频。"""
        from utils.video_io import VideoReader, VideoWriter

        reader = None
        writer = None
        actual_output_path = self.output_path
        frame_idx = 0
        result_dir = None
        error_message = None
        cancelled = False

        try:
            self.pipeline.reset()
            reader = VideoReader(self.video_path, fallback_fps=self.pipeline.video_fallback_fps)
            fps = reader.fps or self.pipeline.video_fallback_fps
            if self.output_path:
                try:
                    writer = VideoWriter(
                        self.output_path,
                        fps,
                        reader.width,
                        reader.height,
                        codec=self.pipeline.video_output_codec,
                        fallback_fps=self.pipeline.video_fallback_fps,
                    )
                except Exception:
                    # 普通处理时缓存视频只是加速后续导出，失败不应中断分析任务。
                    if not self.optional_output:
                        raise
                    if actual_output_path and os.path.exists(actual_output_path):
                        try:
                            os.remove(actual_output_path)
                        except OSError:
                            pass
                    actual_output_path = None

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
                actual_output_path,
            )

    def stop(self):
        """请求线程在当前帧处理结束后尽快退出。"""
        self._stop_requested = True
        self._running = False


class MainWindow(QMainWindow):
    """应用主窗口，集中维护视频任务状态和所有用户操作。"""

    STATE_IDLE_NO_VIDEO = "idle_no_video"
    STATE_IDLE_VIDEO_LOADED = "idle_video_loaded"
    STATE_PROCESSING = "processing"
    STATE_STOPPING = "stopping"
    STATE_PROCESSED_UNSAVED = "processed_unsaved"
    STATE_PROCESSED_SAVED = "processed_saved"
    STATE_EXPORTING = "exporting"
    STATE_ERROR = "error"

    def __init__(self, config_path="config.yaml"):
        """加载配置、初始化流水线，并构建主界面。"""
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
        self.processed_cache_path = None
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
        """创建视频显示区、控制面板和结果面板。"""
        splitter = QSplitter(Qt.Horizontal)

        self.video_widget = VideoWidget()
        splitter.addWidget(self.video_widget)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.control_panel = ControlPanel(self.config)
        self.result_panel = ResultPanel()
        self.result_panel.set_count_mode(self.pipeline.counter.mode)
        right_layout.addWidget(self.control_panel)
        right_layout.addWidget(self.result_panel)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        self.setCentralWidget(splitter)

    def _init_toolbar(self):
        """创建顶部工具栏动作。"""
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
        """把工具栏和控制面板信号连接到主窗口槽函数。"""
        self.open_action.triggered.connect(self._open_video)
        self.start_action.triggered.connect(self._start_processing)
        self.stop_action.triggered.connect(self._stop_processing)
        self.export_action.triggered.connect(self._export_video)
        self.view_heatmap_action.triggered.connect(self._view_heatmap)
        self.save_heatmap_action.triggered.connect(self._save_heatmap)

        self.control_panel.conf_changed.connect(self._update_conf)
        self.control_panel.iou_changed.connect(self._update_iou)
        self.control_panel.count_mode_changed.connect(self._update_count_mode)
        self.control_panel.line_direction_changed.connect(self._update_line_direction)
        self.control_panel.line_pos_changed.connect(self._update_line_pos)
        self.control_panel.model_changed.connect(self._switch_model)

    def closeEvent(self, event):
        """关闭窗口时安全停止后台任务并清理临时处理缓存。"""
        if self._force_close or not self._is_worker_running():
            self._discard_processed_cache()
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
            self._discard_processed_cache()
            event.accept()
        else:
            QMessageBox.warning(self, "提示", "后台任务仍在停止中，请稍后再关闭窗口。")
            event.ignore()

    def _open_video(self):
        """弹出文件选择框并载入新视频。"""
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
        """重置当前状态并绑定新的输入视频路径。"""
        self._discard_processed_cache()
        self.video_path = path
        self.pipeline.reset()
        self.last_frame = None
        self.last_result_dir = None
        self.processing_completed = False
        self.processed_video_saved = False
        self.processed_output_path = None
        self.processed_cache_path = None
        self._pre_export_snapshot = None
        self.control_panel.set_progress(0)
        self.video_widget.clear()
        self.setWindowTitle(f"基于YOLO的车辆轨迹与目标检测系统 - {path}")
        self.ui_state = self.STATE_IDLE_VIDEO_LOADED
        self._refresh_controls()
        self.statusBar().showMessage(f"已打开视频: {os.path.basename(path)}", 3000)

    def _start_processing(self):
        """开始普通处理任务，并同步生成可供快速导出的临时视频缓存。"""
        if not self.video_path:
            return
        if self._is_worker_running():
            QMessageBox.warning(self, "提示", "请先停止当前处理再开始新的任务")
            return

        self._clear_result_state()
        self.processed_cache_path = self._create_processed_cache_path()
        self.ui_state = self.STATE_PROCESSING
        self._start_worker(
            mode="process",
            output_path=self.processed_cache_path,
            optional_output=True,
        )

    def _stop_processing(self):
        """响应用户停止按钮。"""
        if not self._is_worker_running():
            return
        self._request_stop("正在停止任务...")

    def _request_stop(self, message):
        """请求后台线程停止，并把界面切换到停止中状态。"""
        if self.worker:
            self.worker.stop()
        self.ui_state = self.STATE_STOPPING
        self._refresh_controls()
        self.statusBar().showMessage(message, 3000)

    def _start_worker(self, mode, output_path=None, optional_output=False):
        """创建并启动后台处理线程。"""
        self.worker = ProcessingWorker(
            self.pipeline,
            self.video_path,
            mode=mode,
            output_path=output_path,
            optional_output=optional_output,
        )
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
        """接收后台线程输出的标注帧并刷新预览和统计面板。"""
        self.last_frame = frame
        self.video_widget.update_frame(frame)

        now = time.time()
        fps = 1.0 / max(now - self._last_time, 1e-6)
        self._last_time = now

        progress = int(frame_idx / max(total, 1) * 100) if total else 0
        progress = min(progress, 99)
        self.control_panel.set_progress(progress)
        self.result_panel.update_stats(
            count,
            frame_idx,
            total,
            track_count,
            fps,
            class_counts,
            flow_rate,
            count_mode=self.pipeline.counter.mode,
        )

    @Slot(str, int, object, object)
    def _on_processing_completed(self, mode, total_count, result_dir, output_path):
        """处理线程正常结束后，根据任务类型更新保存状态。"""
        self.last_result_dir = result_dir
        self._pre_export_snapshot = None

        if mode == "export":
            self.processing_completed = True
            self.processed_video_saved = True
            self.processed_output_path = output_path
            self.processed_cache_path = None
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
        self.processed_cache_path = output_path if output_path and os.path.exists(output_path) else None
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
        """后台任务被用户取消后的状态恢复。"""
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
        """后台任务异常后的状态恢复和错误提示。"""
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
        """线程对象结束后释放引用，并处理延迟关闭。"""
        worker = self.sender()
        if worker is self.worker:
            self.worker = None
        self._refresh_controls()
        if self._close_after_worker_finished:
            self._force_close = True
            self.close()

    def _export_video(self):
        """导出标注视频；优先复制首次处理生成的缓存，必要时重新处理。"""
        if not self.video_path:
            return
        if self._is_worker_running():
            QMessageBox.warning(self, "提示", "请先停止当前任务后再导出视频")
            return

        export_filter = "MP4 (*.mp4);;AVI (*.avi)"
        if self.processing_completed and self._has_processed_cache():
            cache_ext = os.path.splitext(self.processed_cache_path)[1].lower()
            export_filter = "AVI (*.avi)" if cache_ext == ".avi" else "MP4 (*.mp4)"

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出视频",
            "",
            export_filter,
        )
        path = self._normalize_export_path(path, selected_filter)
        if not path:
            return

        if self.processing_completed and self._has_processed_cache():
            path = self._match_cached_export_extension(path)
            try:
                source = os.path.abspath(self.processed_cache_path)
                target = os.path.abspath(path)
                target_dir = os.path.dirname(target)
                if target_dir:
                    os.makedirs(target_dir, exist_ok=True)
                if source != target:
                    shutil.copy2(source, target)
            except Exception as exc:
                QMessageBox.critical(self, "导出失败", str(exc))
                return

            self.processing_completed = True
            self.processed_video_saved = True
            self.processed_output_path = path
            self.ui_state = self.STATE_PROCESSED_SAVED
            self.control_panel.set_progress(100)
            self._refresh_controls()
            analysis_text = f"\n分析结果已保存到：{self.last_result_dir}" if self.last_result_dir else ""
            QMessageBox.information(
                self,
                "导出完成",
                f"视频已成功导出！\n导出路径：{path}{analysis_text}",
            )
            return

        self._pre_export_snapshot = self._capture_current_result_snapshot()
        self._pending_output_path = path
        if not self.processing_completed:
            self._clear_result_state()
        else:
            self.statusBar().showMessage("处理缓存不可用，正在重新生成导出视频...", 3000)
        self.ui_state = self.STATE_EXPORTING
        self._start_worker(mode="export", output_path=path)

    def _view_heatmap(self):
        """在当前最后一帧上叠加并展示热力图。"""
        if not self._can_use_heatmap():
            QMessageBox.information(self, "提示", "当前没有可查看的热力图。")
            return

        base_frame = self.last_frame
        heatmap = self.pipeline.get_heatmap(base_frame.shape)
        result = overlay_heatmap(base_frame, heatmap)
        self.video_widget.update_frame(result)
        self.statusBar().showMessage("热力图已显示到画面中", 3000)

    def _save_heatmap(self):
        """把当前热力图输出到分析结果目录。"""
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
        """更新检测置信度阈值，并让旧处理结果失效。"""
        changed = self.pipeline.detector.conf != value
        self.pipeline.detector.conf = value
        if changed:
            self._invalidate_processed_result()

    def _update_iou(self, value):
        """更新 NMS IoU 阈值，并让旧处理结果失效。"""
        changed = self.pipeline.detector.iou != value
        self.pipeline.detector.iou = value
        if changed:
            self._invalidate_processed_result()

    def _update_count_mode(self, mode):
        """更新计数模式，配置变化时清空已有统计结果。"""
        if self._is_worker_running():
            QMessageBox.warning(self, "提示", "请先停止当前处理再切换计数模式")
            return
        changed = self.pipeline.counter.configure(mode=mode)
        self.config.setdefault("counter", {})["mode"] = self.pipeline.counter.mode
        self.result_panel.set_count_mode(self.pipeline.counter.mode)
        if changed:
            self._clear_result_state()
        self.statusBar().showMessage("已更新计数模式", 3000)

    def _update_line_direction(self, direction):
        """更新越线方向，避免与旧越线统计混用。"""
        if self._is_worker_running():
            QMessageBox.warning(self, "提示", "请先停止当前处理再调整越线方向")
            return
        changed = self.pipeline.counter.configure(direction=direction)
        self.config.setdefault("counter", {})["direction"] = self.pipeline.counter.direction
        if changed:
            self._clear_result_state()
        self.statusBar().showMessage("已更新越线方向", 3000)

    def _update_line_pos(self, _value):
        """更新越线位置，避免与旧越线统计混用。"""
        if self._is_worker_running():
            QMessageBox.warning(self, "提示", "请先停止当前处理再调整越线位置")
            return
        changed = self.pipeline.counter.configure(line_position=_value)
        self.config.setdefault("counter", {})["line_position"] = self.pipeline.counter.line_position
        if changed:
            self._clear_result_state()
        self.statusBar().showMessage("已更新越线位置", 3000)

    def _switch_model(self, model_path):
        """切换检测权重并清空依赖旧模型的处理结果。"""
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
        self._invalidate_processed_result()
        self.statusBar().showMessage(f"已切换模型: {os.path.basename(model_path)}", 3000)

    def _restore_idle_controls(self):
        """后台任务结束后恢复空闲状态下的控件可用性。"""
        self._refresh_controls()

    def _refresh_controls(self):
        """根据当前状态统一刷新工具栏和控制面板启用状态。"""
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
        """判断后台线程是否仍在运行。"""
        return self.worker is not None and self.worker.isRunning()

    def _clear_result_state(self):
        """清空当前视频的处理结果和缓存。"""
        self._discard_processed_cache()
        self.last_frame = None
        self.last_result_dir = None
        self.processing_completed = False
        self.processed_video_saved = False
        self.processed_output_path = None
        self.processed_cache_path = None
        self._pending_output_path = None
        self.control_panel.set_progress(0)
        self.result_panel.reset_stats()
        self.ui_state = self.STATE_IDLE_VIDEO_LOADED if self.video_path else self.STATE_IDLE_NO_VIDEO
        self._refresh_controls()

    def _capture_current_result_snapshot(self):
        """导出任务开始前保存状态，便于失败或取消时回滚。"""
        return {
            "processing_completed": self.processing_completed,
            "processed_video_saved": self.processed_video_saved,
            "processed_output_path": self.processed_output_path,
            "processed_cache_path": self.processed_cache_path,
            "last_result_dir": self.last_result_dir,
        }

    def _restore_snapshot_after_export(self):
        """导出失败或取消时恢复导出前的处理状态。"""
        snapshot = self._pre_export_snapshot or {}
        self.processing_completed = snapshot.get("processing_completed", False)
        self.processed_video_saved = snapshot.get("processed_video_saved", False)
        self.processed_output_path = snapshot.get("processed_output_path")
        self.processed_cache_path = snapshot.get("processed_cache_path")
        self.last_result_dir = snapshot.get("last_result_dir")
        self.last_frame = None
        self._pending_output_path = None
        self._pre_export_snapshot = None
        if self.processing_completed:
            self.ui_state = self._completed_state()
        else:
            self.ui_state = self.STATE_IDLE_VIDEO_LOADED if self.video_path else self.STATE_IDLE_NO_VIDEO

    def _completed_state(self):
        """根据视频是否已导出返回完成态。"""
        return self.STATE_PROCESSED_SAVED if self.processed_video_saved else self.STATE_PROCESSED_UNSAVED

    def _can_use_heatmap(self):
        """判断当前是否有可展示或保存的热力图数据。"""
        return self.processing_completed and self.last_frame is not None and self.ui_state in {
            self.STATE_PROCESSED_UNSAVED,
            self.STATE_PROCESSED_SAVED,
        }

    def _invalidate_processed_result(self):
        """参数变化后清理依赖旧配置的结果。"""
        if self.processing_completed or self.processed_cache_path:
            self._clear_result_state()

    def _create_processed_cache_path(self):
        """创建首次处理时使用的临时标注视频路径。"""
        try:
            cache_file = tempfile.NamedTemporaryFile(
                prefix="bishe_processed_",
                suffix=self._cache_video_suffix(),
                delete=False,
            )
            cache_path = cache_file.name
            cache_file.close()
            return cache_path
        except OSError:
            return None

    def _cache_video_suffix(self):
        """根据编码器选择缓存文件扩展名。"""
        codec = (self.pipeline.video_output_codec or "").lower()
        return ".avi" if codec in {"xvid", "mjpg", "divx"} else ".mp4"

    def _discard_processed_cache(self):
        """删除内部临时缓存；不会删除用户手动导出的文件。"""
        path = self.processed_cache_path
        self.processed_cache_path = None
        if not path or path == self.processed_output_path:
            return
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    def _has_processed_cache(self):
        """确认临时标注视频缓存仍可用。"""
        return bool(self.processed_cache_path and os.path.exists(self.processed_cache_path))

    def _normalize_export_path(self, path, selected_filter):
        """用户未输入扩展名时，根据保存对话框选项补全扩展名。"""
        if not path:
            return path
        if os.path.splitext(path)[1]:
            return path
        selected_filter = selected_filter or ""
        suffix = ".avi" if "AVI" in selected_filter.upper() else ".mp4"
        return f"{path}{suffix}"

    def _match_cached_export_extension(self, path):
        """直接复制缓存时保持输出扩展名与缓存视频格式一致。"""
        cache_ext = os.path.splitext(self.processed_cache_path or "")[1]
        if not cache_ext:
            return path
        root, ext = os.path.splitext(path)
        if ext.lower() == cache_ext.lower():
            return path
        return f"{root}{cache_ext}"
