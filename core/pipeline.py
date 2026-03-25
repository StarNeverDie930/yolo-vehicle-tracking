import yaml
from core.detector import VehicleDetector
from core.tracker import VehicleTracker
from analysis.trajectory import TrajectoryStore
from analysis.counter import VehicleCounter
from analysis.heatmap import generate_heatmap, overlay_heatmap
from utils.video_io import VideoReader, VideoWriter
from utils.drawing import draw_boxes, draw_trajectories, draw_count_text


class ProcessingPipeline:
    def __init__(self, config):
        self.config = config
        self.detector = VehicleDetector(
            model_path=config["model"]["path"],
            conf=config["model"]["conf"],
            iou=config["model"]["iou"],
            classes=config["model"]["classes"],
            device=config["model"].get("device", "auto"),
        )
        self.tracker = VehicleTracker(
            max_age=config["tracker"]["max_age"],
            n_init=config["tracker"]["n_init"],
            max_cosine_distance=config["tracker"]["max_cosine_distance"],
            nn_budget=config["tracker"]["nn_budget"],
        )
        self.trajectory_store = TrajectoryStore(
            max_length=config["display"]["trajectory_length"]
        )
        self.counter = VehicleCounter(
            flow_window=config["counter"].get("flow_window", 60),
        )

    @classmethod
    def from_config_file(cls, config_path="config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return cls(config)

    def process_frame(self, frame):
        """处理单帧，返回 (annotated_frame, tracks, count, class_counts, flow_rate)"""
        detections = self.detector.detect(frame)
        tracks = self.tracker.update(detections, frame)

        h, w = frame.shape[:2]
        for t in tracks:
            if t.get("matched", True):
                self.trajectory_store.update(t["track_id"], t["bbox"])

        self.counter.update(tracks)
        count = self.counter.count
        class_counts = self.counter.get_class_counts()
        flow_rate = self.counter.get_flow_rate(60)

        annotated = frame.copy()
        draw_boxes(annotated, tracks,
                   thickness=self.config["display"]["box_thickness"],
                   font_scale=self.config["display"]["font_scale"])
        draw_trajectories(annotated, self.trajectory_store, tracks)
        draw_count_text(annotated, count)

        return annotated, tracks, count, class_counts, flow_rate

    def process_video(self, input_path, output_path=None, progress_callback=None):
        """处理整个视频"""
        self.reset()

        with VideoReader(input_path) as reader:
            writer = None
            if output_path:
                writer = VideoWriter(output_path, reader.fps, reader.width, reader.height)

            frame_idx = 0
            total = reader.frame_count

            while True:
                ret, frame = reader.read()
                if not ret:
                    break

                annotated, tracks, count, _, _ = self.process_frame(frame)

                if writer:
                    writer.write(annotated)

                frame_idx += 1
                if progress_callback:
                    progress_callback(frame_idx, total, count)

            if writer:
                writer.release()

        return self.counter.count

    def get_heatmap(self, frame_shape):
        return generate_heatmap(self.trajectory_store.get_all(), frame_shape)

    def reset(self):
        self.tracker.reset()
        self.trajectory_store.clear()
        self.counter.reset()

    def switch_model(self, model_path):
        self.detector = VehicleDetector(
            model_path=model_path,
            conf=self.detector.conf,
            iou=self.detector.iou,
            classes=self.detector.classes,
            device=self.config["model"].get("device", "auto"),
        )