import torch
from ultralytics import YOLO
import numpy as np


class VehicleDetector:
    # COCO 类别映射
    COCO_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
    # DETRAC 类别映射
    DETRAC_CLASSES = {0: "car", 1: "bus", 2: "van", 3: "others"}

    def __init__(self, model_path="yolo11n.pt", conf=0.5, iou=0.45, classes=None, device="auto"):
        if device == "auto":
            device = "0" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.model = YOLO(model_path)
        self.model.to(f"cuda:{device}" if device != "cpu" else "cpu")
        self.conf = conf
        self.iou = iou

        # 自动判断模型类型：DETRAC 训练的模型只有 4 类，不需要过滤
        nc = len(self.model.names)
        if nc <= 10:
            # 自定义训练的模型（如 DETRAC），检测所有类别
            self.classes = None
            self.class_names = {i: name for i, name in self.model.names.items()}
        else:
            # COCO 预训练模型，只检测车辆类别
            self.classes = classes or [2, 3, 5, 7]
            self.class_names = self.COCO_CLASSES

    def detect(self, frame):
        """返回检测结果列表: [([x1,y1,x2,y2], conf, class_id), ...]"""
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
                detections.append((xyxy, conf, cls))
        return detections

    def get_class_name(self, class_id):
        return self.class_names.get(class_id, "unknown")
