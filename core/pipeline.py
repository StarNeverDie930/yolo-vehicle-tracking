import os
import time

import yaml

from analysis.counter import VehicleCounter
from analysis.heatmap import HeatmapAccumulator, save_heatmap_outputs
from analysis.results import AnalysisRecorder, export_analysis_results, make_result_dir
from analysis.trajectory import TrajectoryStore
from core.detector import VehicleDetector
from core.tracker import VehicleTracker
from utils.drawing import draw_boxes, draw_count_line, draw_count_text, draw_trajectories
from utils.taxonomy import get_class_name
from utils.video_io import VideoReader, VideoWriter


class ProcessingPipeline:
    def __init__(self, config):
        self.config = config
        model_cfg = config["model"]
        tracker_cfg = config["tracker"]
        display_cfg = config["display"]
        counter_cfg = config["counter"]
        video_cfg = config.get("video", {})
        analysis_cfg = config.get("analysis", {})

        self.detector = VehicleDetector(
            model_path=model_cfg["path"],
            conf=model_cfg["conf"],
            iou=model_cfg["iou"],
            classes=model_cfg.get("classes"),
            device=model_cfg.get("device", "auto"),
        )
        self.tracker = VehicleTracker(
            max_age=tracker_cfg["max_age"],
            n_init=tracker_cfg["n_init"],
            max_cosine_distance=tracker_cfg["max_cosine_distance"],
            nn_budget=tracker_cfg["nn_budget"],
        )
        self.trajectory_store = TrajectoryStore(
            max_length=display_cfg["trajectory_length"]
        )
        self.counter = VehicleCounter(
            flow_window=counter_cfg.get("flow_window", 60),
            mode=counter_cfg.get("mode", "unique_track"),
            line_position=counter_cfg.get("line_position", 0.6),
            direction=counter_cfg.get("direction", "horizontal"),
        )
        self.heatmap = HeatmapAccumulator()
        self.analysis_recorder = AnalysisRecorder()

        self.video_output_codec = video_cfg.get("output_codec", "mp4v")
        self.video_fallback_fps = video_cfg.get("fallback_fps", video_cfg.get("output_fps", 30))
        self.analysis_output_dir = analysis_cfg.get("output_dir", os.path.join("analysis", "results"))

        self.last_frame = None
        self.last_result_dir = None

    @classmethod
    def from_config_file(cls, config_path="config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return cls(config)

    def process_frame(self, frame, frame_idx=0, fps=None, timestamp=None):
        """处理单帧，返回 (annotated_frame, tracks, count, class_counts, flow_rate)"""
        detections = self.detector.detect(frame)
        tracks = self.tracker.update(detections, frame)

        fps = fps or self.video_fallback_fps
        if timestamp is None:
            timestamp = float(frame_idx) / float(fps) if fps else 0.0

        self.last_frame = frame.copy()

        for track in tracks:
            track["class_name"] = get_class_name(track["class_id"])
            if track.get("matched", True):
                self.trajectory_store.update(track["track_id"], track["bbox"])

        self.counter.update(tracks, frame_idx=frame_idx, fps=fps, timestamp=timestamp, frame_shape=frame.shape)
        self.heatmap.update_tracks(tracks, frame.shape)
        self.analysis_recorder.update(tracks, frame_idx, timestamp)

        count = self.counter.count
        class_counts = self.counter.get_class_counts()
        flow_rate = self.counter.get_flow_rate()

        annotated = frame.copy()
        draw_boxes(
            annotated,
            tracks,
            thickness=self.config["display"]["box_thickness"],
            font_scale=self.config["display"]["font_scale"],
        )
        draw_trajectories(annotated, self.trajectory_store, tracks)
        draw_count_text(annotated, count)

        if self.counter.mode == "line_crossing":
            pt1, pt2 = self.counter.get_line_coords(frame.shape[0], frame.shape[1])
            draw_count_line(annotated, pt1, pt2)

        return annotated, tracks, count, class_counts, flow_rate

    def process_video(self, input_path, output_path=None, progress_callback=None, analysis_output_dir=None):
        """处理整个视频，并在结束后导出分析结果。"""
        self.reset()
        analysis_output_dir = analysis_output_dir or self.analysis_output_dir
        start_time = time.perf_counter()

        with VideoReader(input_path, fallback_fps=self.video_fallback_fps) as reader:
            fps = reader.fps or self.video_fallback_fps
            writer = None
            if output_path:
                writer = VideoWriter(
                    output_path,
                    fps,
                    reader.width,
                    reader.height,
                    codec=self.video_output_codec,
                    fallback_fps=self.video_fallback_fps,
                )

            frame_idx = 0
            total = reader.frame_count

            try:
                while True:
                    ret, frame = reader.read()
                    if not ret:
                        break

                    annotated, _, count, _, _ = self.process_frame(frame, frame_idx=frame_idx, fps=fps)

                    if writer:
                        writer.write(annotated)

                    frame_idx += 1
                    if progress_callback:
                        progress_callback(frame_idx, total, count)
            finally:
                if writer:
                    writer.release()

        elapsed = time.perf_counter() - start_time
        if frame_idx == 0:
            raise RuntimeError("视频没有可读取帧")
        average_fps = frame_idx / elapsed if elapsed > 0 else 0.0
        self.last_result_dir = self.export_analysis(
            output_dir=analysis_output_dir,
            video_path=input_path,
            frame_count=frame_idx,
            elapsed_sec=elapsed,
            average_fps=average_fps,
        )
        return self.counter.count

    def get_heatmap(self, frame_shape):
        return self.heatmap.generate(frame_shape)

    def save_heatmap(self, output_dir=None, frame=None, prefix="heatmap"):
        if frame is None:
            frame = self.last_frame
        if frame is None:
            raise ValueError("没有可用于保存热力图的帧")
        heatmap = self.get_heatmap(frame.shape)
        result_dir = output_dir or self.last_result_dir
        if result_dir is None:
            result_dir = self._default_result_dir()
            self.last_result_dir = result_dir
        return save_heatmap_outputs(frame, heatmap, result_dir, prefix=prefix)

    def export_analysis(
        self,
        output_dir=None,
        video_path=None,
        frame_count=None,
        elapsed_sec=None,
        average_fps=None,
        representative_frame=None,
    ):
        base_dir = output_dir or self.analysis_output_dir
        result_dir = make_result_dir(base_dir, source_path=video_path)
        if representative_frame is None:
            representative_frame = self.last_frame
        if representative_frame is None:
            raise ValueError("没有可用于导出分析结果的帧")

        heatmap = self.get_heatmap(representative_frame.shape)
        heatmap_paths = save_heatmap_outputs(representative_frame, heatmap, result_dir)
        performance = {
            "video_path": video_path or "",
            "model_path": self.config["model"]["path"],
            "device": self.detector.device,
            "counter_mode": self.counter.mode,
            "frame_count": frame_count if frame_count is not None else len(self.analysis_recorder.summaries()),
            "elapsed_sec": float(elapsed_sec or 0.0),
            "average_fps": float(average_fps or 0.0),
            "video_fallback_fps": self.video_fallback_fps,
        }
        export_analysis_results(
            result_dir,
            self.counter.get_class_counts(),
            self.counter.get_flow_buckets(),
            self.analysis_recorder.summaries(),
            self.heatmap.hotspots(),
            performance,
            heatmap_paths=heatmap_paths,
        )
        self.last_result_dir = result_dir
        return result_dir

    def reset(self):
        self.tracker.reset()
        self.trajectory_store.clear()
        self.counter.reset()
        self.heatmap.clear()
        self.analysis_recorder.clear()
        self.last_frame = None
        self.last_result_dir = None

    def switch_model(self, model_path):
        self.config["model"]["path"] = model_path
        self.detector = VehicleDetector(
            model_path=model_path,
            conf=self.detector.conf,
            iou=self.detector.iou,
            classes=self.config["model"].get("classes"),
            device=self.config["model"].get("device", "auto"),
        )

    def _default_result_dir(self, video_path=None):
        base_dir = self.analysis_output_dir
        return make_result_dir(base_dir, source_path=video_path)
