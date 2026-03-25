import numpy as np
import cv2


def generate_heatmap(trajectories, frame_shape, blur_size=25):
    """
    根据所有轨迹点生成热力图
    trajectories: {track_id: [(cx, cy), ...]}
    """
    h, w = frame_shape[:2]
    accumulator = np.zeros((h, w), dtype=np.float32)

    for points in trajectories.values():
        for (cx, cy) in points:
            if 0 <= cx < w and 0 <= cy < h:
                accumulator[cy, cx] += 1

    if accumulator.max() > 0:
        accumulator = cv2.GaussianBlur(accumulator, (blur_size, blur_size), 0)
        accumulator = accumulator / accumulator.max() * 255
        heatmap = cv2.applyColorMap(accumulator.astype(np.uint8), cv2.COLORMAP_JET)
        return heatmap

    return np.zeros((h, w, 3), dtype=np.uint8)


def overlay_heatmap(frame, heatmap, alpha=0.4):
    return cv2.addWeighted(frame, 1 - alpha, heatmap, alpha, 0)
