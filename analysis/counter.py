from utils.taxonomy import CLASS_IDS, class_counts_template


class VehicleCounter:
    def __init__(self, flow_window=60, mode="unique_track",
                 line_position=0.6, direction="horizontal"):
        self.flow_window = flow_window
        self.mode = mode if mode in ("unique_track", "line_crossing") else "unique_track"
        self.line_position = float(line_position)
        self.direction = direction if direction in ("horizontal", "vertical") else "horizontal"
        self._seen = {}
        self._flow_log = []
        self._last_centers = {}
        self._last_timestamp = 0.0

    def update(self, tracks, frame_idx=None, fps=None, timestamp=None, frame_shape=None):
        timestamp = self._resolve_timestamp(frame_idx, fps, timestamp)
        for t in tracks:
            tid = t["track_id"]
            class_id = int(t.get("class_id", -1))
            if class_id not in CLASS_IDS:
                continue

            if self.mode == "line_crossing":
                self._update_line_crossing(tid, class_id, t["bbox"], timestamp, frame_shape)
            elif tid not in self._seen:
                self._record(tid, class_id, timestamp)

    @property
    def count(self):
        return len(self._seen)

    def get_class_counts(self):
        result = class_counts_template()
        for cls in self._seen.values():
            if cls in result:
                result[cls] += 1
        return result

    def get_flow_rate(self, seconds=None):
        seconds = seconds or self.flow_window
        cutoff = self._last_timestamp - seconds
        result = class_counts_template()
        for ts, cls in self._flow_log:
            if ts >= cutoff and cls in result:
                result[cls] += 1
        return result

    def get_flow_buckets(self, bucket_size=None):
        bucket_size = bucket_size or self.flow_window
        buckets = {}
        for ts, cls in self._flow_log:
            start = int(ts // bucket_size) * bucket_size
            row = buckets.setdefault(start, {"start_sec": start, "end_sec": start + bucket_size,
                                             "total": 0, **class_counts_template()})
            row["total"] += 1
            row[cls] += 1
        return [buckets[start] for start in sorted(buckets)]

    def reset(self):
        self._seen.clear()
        self._flow_log.clear()
        self._last_centers.clear()
        self._last_timestamp = 0.0

    def get_line_coords(self, frame_height, frame_width):
        if self.direction == "vertical":
            x = int(frame_width * self.line_position)
            return (x, 0), (x, frame_height)
        y = int(frame_height * self.line_position)
        return (0, y), (frame_width, y)

    def _record(self, track_id, class_id, timestamp):
        self._seen[track_id] = class_id
        self._flow_log.append((timestamp, class_id))

    def _resolve_timestamp(self, frame_idx, fps, timestamp):
        if timestamp is not None:
            self._last_timestamp = float(timestamp)
        elif frame_idx is not None and fps and fps > 0:
            self._last_timestamp = float(frame_idx) / float(fps)
        return self._last_timestamp

    def _update_line_crossing(self, track_id, class_id, bbox, timestamp, frame_shape):
        center = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
        previous = self._last_centers.get(track_id)
        self._last_centers[track_id] = center
        if previous is None or track_id in self._seen or frame_shape is None:
            return

        frame_height, frame_width = frame_shape[:2]
        if self.direction == "vertical":
            line_value = frame_width * self.line_position
            crossed = (previous[0] - line_value) * (center[0] - line_value) <= 0
        else:
            line_value = frame_height * self.line_position
            crossed = (previous[1] - line_value) * (center[1] - line_value) <= 0

        if crossed:
            self._record(track_id, class_id, timestamp)
