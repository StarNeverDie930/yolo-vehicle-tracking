import os

import cv2


class VideoReader:
    def __init__(self, path, fallback_fps=30):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise FileNotFoundError(f"无法打开视频: {path}")
        self.fallback_fps = fallback_fps

    @property
    def fps(self):
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
        return self.cap.read()

    def release(self):
        self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()


class VideoWriter:
    def __init__(self, path, fps, width, height, codec="mp4v", fallback_fps=30):
        fps = fps if fps and fps > 0 else fallback_fps
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*codec)
        self.writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
        if not self.writer.isOpened():
            raise RuntimeError(f"无法创建视频写入器: {path}")

    def write(self, frame):
        self.writer.write(frame)

    def release(self):
        self.writer.release()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()
