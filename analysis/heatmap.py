"""轨迹热力图生成。

根据每个有效 track 的中心点累计像素级访问强度，再生成伪彩色热力图、
叠加图和热点区域统计。
"""

import os
from datetime import datetime

import cv2
import numpy as np


class HeatmapAccumulator:
    """累积轨迹中心点，并按需要生成热力图和热点区域。"""

    def __init__(self, blur_size=25):
        """blur_size 控制热力图平滑程度。"""
        self.blur_size = blur_size
        self.accumulator = None
        self.frame_shape = None

    def update_tracks(self, tracks, frame_shape):
        """把当前帧已匹配轨迹的中心点累计到热力图矩阵。"""
        self._ensure_shape(frame_shape)
        h, w = self.accumulator.shape
        for track in tracks:
            if not track.get("matched", True):
                continue
            x1, y1, x2, y2 = track["bbox"]
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            if 0 <= cx < w and 0 <= cy < h:
                self.accumulator[cy, cx] += 1

    def generate(self, frame_shape=None):
        """生成 BGR 伪彩色热力图；无数据时返回空热力图。"""
        if self.accumulator is None:
            if frame_shape is None:
                return None
            h, w = frame_shape[:2]
            return np.zeros((h, w, 3), dtype=np.uint8)
        return _colorize_accumulator(self.accumulator, self.blur_size)

    def hotspots(self, grid=(4, 4), top_n=5):
        """把画面划分网格，返回累计强度最高的若干区域。"""
        if self.accumulator is None:
            return []
        rows, cols = grid
        h, w = self.accumulator.shape
        hotspots = []
        for row in range(rows):
            y1 = int(row * h / rows)
            y2 = int((row + 1) * h / rows)
            for col in range(cols):
                x1 = int(col * w / cols)
                x2 = int((col + 1) * w / cols)
                value = float(self.accumulator[y1:y2, x1:x2].sum())
                hotspots.append({
                    "rank": 0,
                    "grid_row": row,
                    "grid_col": col,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "intensity": value,
                })
        hotspots.sort(key=lambda item: item["intensity"], reverse=True)
        for rank, item in enumerate(hotspots[:top_n], start=1):
            item["rank"] = rank
        return hotspots[:top_n]

    def clear(self):
        """清空累计矩阵。"""
        self.accumulator = None
        self.frame_shape = None

    def _ensure_shape(self, frame_shape):
        """在首帧或分辨率变化时初始化累计矩阵。"""
        h, w = frame_shape[:2]
        if self.accumulator is None or self.accumulator.shape != (h, w):
            self.accumulator = np.zeros((h, w), dtype=np.float32)
            self.frame_shape = frame_shape


def generate_heatmap(trajectories, frame_shape, blur_size=25):
    """
    根据所有轨迹点生成热力图。
    trajectories: {track_id: [(cx, cy), ...]}
    """
    h, w = frame_shape[:2]
    accumulator = np.zeros((h, w), dtype=np.float32)

    for points in trajectories.values():
        for (cx, cy) in points:
            if 0 <= cx < w and 0 <= cy < h:
                accumulator[cy, cx] += 1

    if accumulator.max() > 0:
        return _colorize_accumulator(accumulator, blur_size)

    return np.zeros((h, w, 3), dtype=np.uint8)


def overlay_heatmap(frame, heatmap, alpha=0.4):
    """把热力图半透明叠加到原始帧上。"""
    return cv2.addWeighted(frame, 1 - alpha, heatmap, alpha, 0)


def save_heatmap_outputs(frame, heatmap, output_dir, prefix="heatmap"):
    """保存原始热力图和叠加热力图，返回两个文件路径。"""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    raw_path = os.path.join(output_dir, f"{prefix}_{timestamp}.png")
    overlay_path = os.path.join(output_dir, f"{prefix}_overlay_{timestamp}.png")
    overlay = overlay_heatmap(frame, heatmap) if frame is not None else heatmap

    if not cv2.imwrite(raw_path, heatmap):
        raise RuntimeError(f"热力图保存失败: {raw_path}")
    if not cv2.imwrite(overlay_path, overlay):
        raise RuntimeError(f"热力图叠加图保存失败: {overlay_path}")

    return {
        "heatmap": raw_path,
        "overlay": overlay_path,
    }


def _colorize_accumulator(accumulator, blur_size):
    """把累计矩阵归一化、平滑并转换为 OpenCV 伪彩色图。"""
    blur_size = int(blur_size)
    if blur_size % 2 == 0:
        blur_size += 1
    blurred = cv2.GaussianBlur(accumulator, (blur_size, blur_size), 0)
    if blurred.max() <= 0:
        return np.zeros((*accumulator.shape, 3), dtype=np.uint8)
    normalized = blurred / blurred.max() * 255
    return cv2.applyColorMap(normalized.astype(np.uint8), cv2.COLORMAP_JET)
