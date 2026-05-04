import torch
from ultralytics import YOLO

from utils.taxonomy import (
    CLASS_NAMES,
    COCO_TO_UNIFIED,
    get_class_name,
    normalize_model_class_id,
)


class VehicleDetector:
    def __init__(self, model_path="yolo11m.pt", conf=0.5, iou=0.45, classes=None, device="auto"):
        if device == "auto":
            device = "0" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.model = YOLO(model_path)
        self.model.to(f"cuda:{device}" if device != "cpu" else "cpu")
        self.conf = conf
        self.iou = iou

        raw_names = getattr(self.model, "names", {}) or {}
        if isinstance(raw_names, dict):
            self.model_names = dict(raw_names)
        else:
            self.model_names = {i: name for i, name in enumerate(raw_names)}
        nc = len(self.model_names)
        self.uses_coco_taxonomy = nc > len(CLASS_NAMES)
        self.class_names = CLASS_NAMES

        if self.uses_coco_taxonomy:
            selected = classes if classes is not None else list(COCO_TO_UNIFIED)
            self.classes = [int(cid) for cid in selected if int(cid) in COCO_TO_UNIFIED]
        else:
            self.classes = None

    def detect(self, frame):
        """返回统一 taxonomy 后的检测结果: [([x1,y1,x2,y2], conf, class_id), ...]"""
        results = self.model(frame, conf=self.conf, iou=self.iou, classes=self.classes, device=self.device, verbose=False)
        detections = []
        for r in results:
            boxes = r.boxes
            if boxes is None:
                continue
            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                if self.uses_coco_taxonomy:
                    cls = COCO_TO_UNIFIED.get(cls)
                else:
                    cls = normalize_model_class_id(cls, self.model_names)
                if cls is None:
                    continue
                detections.append((xyxy, conf, cls))
        return detections

    def get_class_name(self, class_id):
        return get_class_name(class_id, "unknown")
