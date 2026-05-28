"""OpenCV 绘图工具。

所有函数都直接在传入 frame 上绘制，避免在处理循环里产生额外拷贝。
"""

import cv2

from utils.taxonomy import get_class_name

# 为不同 track_id 分配不同颜色
_COLORS = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
    (255, 0, 255), (0, 255, 255), (128, 0, 255), (255, 128, 0),
    (0, 128, 255), (128, 255, 0), (255, 0, 128), (0, 255, 128),
]

def _get_color(track_id):
    """为同一 track_id 稳定分配一种颜色。"""
    return _COLORS[hash(track_id) % len(_COLORS)]


def draw_boxes(frame, tracks, thickness=2, font_scale=0.6):
    """绘制车辆检测框、跟踪 ID 和类别标签。"""
    for t in tracks:
        color = _get_color(t["track_id"])
        x1, y1, x2, y2 = t["bbox"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        cls_name = t.get("class_name") or get_class_name(t["class_id"], "vehicle")
        label = f"ID:{t['track_id']} {cls_name}"
        cv2.putText(frame, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale, color, thickness)
    return frame


def draw_trajectories(frame, trajectory_store, tracks, thickness=2):
    """绘制当前可见车辆的历史中心点轨迹。"""
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
    """绘制越线计数使用的参考线。"""
    cv2.line(frame, pt1, pt2, (0, 0, 255), thickness)
    return frame


def draw_count_text(frame, count, position=(20, 40), font_scale=1.0):
    """在画面左上角绘制累计车辆数量。"""
    cv2.putText(frame, f"Count: {count}", position, cv2.FONT_HERSHEY_SIMPLEX,
                font_scale, (0, 0, 255), 2)
    return frame
