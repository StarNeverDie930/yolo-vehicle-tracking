import time


class VehicleCounter:
    CLASS_NAMES = {0: "car", 1: "bus", 2: "van", 3: "truck"}

    def __init__(self, flow_window=60):
        self.flow_window = flow_window
        self._seen = {}       # {track_id: class_id}
        self._flow_log = []   # [(timestamp, class_id)]

    def update(self, tracks):
        for t in tracks:
            tid = t["track_id"]
            if tid not in self._seen:
                self._seen[tid] = t["class_id"]
                self._flow_log.append((time.time(), t["class_id"]))

    @property
    def count(self):
        return len(self._seen)

    def get_class_counts(self):
        result = {i: 0 for i in self.CLASS_NAMES}
        for cls in self._seen.values():
            if cls in result:
                result[cls] += 1
        return result

    def get_flow_rate(self, seconds=60):
        cutoff = time.time() - seconds
        result = {i: 0 for i in self.CLASS_NAMES}
        for ts, cls in self._flow_log:
            if ts >= cutoff and cls in result:
                result[cls] += 1
        return result

    def reset(self):
        self._seen.clear()
        self._flow_log.clear()

    def get_line_coords(self, frame_height, frame_width):
        return None