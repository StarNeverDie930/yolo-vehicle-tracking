import cv2
import numpy as np

# 为不同 track_id 分配不同颜色
_COLORS = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
    (255, 0, 255), (0, 255, 255), (128, 0, 255), (255, 128, 0),
    (0, 128, 255), (128, 255, 0), (255, 0, 128), (0, 255, 128),
]

CLASS_NAMES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


def _get_color(track_id):
    return _COLORS[hash(track_id) % len(_COLORS)]


def draw_boxes(frame, tracks, thickness=2, font_scale=0.6):
    for t in tracks:
        color = _get_color(t["track_id"])
        x1, y1, x2, y2 = t["bbox"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        cls_name = CLASS_NAMES.get(t["class_id"], "vehicle")
        label = f"ID:{t['track_id']} {cls_name}"
        cv2.putText(frame, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale, color, thickness)
    return frame


def draw_trajectories(frame, trajectory_store, tracks, thickness=2):
    for t in tracks:
        tid = t["track_id"]
        points = trajectory_store.get(tid)
        if len(points) < 2:
            continue
        color = _get_color(tid)
        for i in range(1, len(points)):
            cv2.line(frame, points[i - 1], points[i], color, thickness)
    return frame


def draw_count_line(frame, pt1, pt2, thickness=2):
    cv2.line(frame, pt1, pt2, (0, 0, 255), thickness)
    return frame


def draw_count_text(frame, count, position=(20, 40), font_scale=1.0):
    cv2.putText(frame, f"Count: {count}", position, cv2.FONT_HERSHEY_SIMPLEX,
                font_scale, (0, 0, 255), 2)
    return frame
