import cv2


class VideoReader:
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise FileNotFoundError(f"无法打开视频: {path}")

    @property
    def fps(self):
        return self.cap.get(cv2.CAP_PROP_FPS)

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
    def __init__(self, path, fps, width, height, codec="mp4v"):
        fourcc = cv2.VideoWriter_fourcc(*codec)
        self.writer = cv2.VideoWriter(path, fourcc, fps, (width, height))

    def write(self, frame):
        self.writer.write(frame)

    def release(self):
        self.writer.release()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()
