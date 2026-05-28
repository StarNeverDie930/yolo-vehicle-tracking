"""OpenCV 视频读写薄封装。

集中处理 FPS 缺失、输出目录创建和资源释放，让流水线代码保持简洁。
"""

import os

import cv2


class VideoReader:
    """支持上下文管理器的视频读取器。"""

    def __init__(self, path, fallback_fps=30):
        """打开视频文件；当元数据 FPS 不可用时使用 fallback_fps。"""
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise FileNotFoundError(f"无法打开视频: {path}")
        self.fallback_fps = fallback_fps

    @property
    def fps(self):
        """返回视频 FPS，异常或缺失时回退到配置值。"""
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        return fps if fps and fps > 0 else self.fallback_fps

    @property
    def frame_count(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    @property
    def width(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def height(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def read(self):
        """读取下一帧，返回 OpenCV 的 (ret, frame)。"""
        return self.cap.read()

    def release(self):
        """释放底层 VideoCapture。"""
        self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()


class VideoWriter:
    """支持上下文管理器的视频写入器。"""

    def __init__(self, path, fps, width, height, codec="mp4v", fallback_fps=30):
        """创建输出视频；目录不存在时自动创建。"""
        fps = fps if fps and fps > 0 else fallback_fps
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*codec)
        self.writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
        if not self.writer.isOpened():
            raise RuntimeError(f"无法创建视频写入器: {path}")

    def write(self, frame):
        """写入一帧 BGR 图像。"""
        self.writer.write(frame)

    def release(self):
        """释放底层 VideoWriter，确保文件头尾写完整。"""
        self.writer.release()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()
