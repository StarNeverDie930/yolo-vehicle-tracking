"""车辆计数与流量统计。

支持两种计数口径：按 track_id 去重的累计计数，以及越过指定水平/垂直线
时才计数的越线模式。统计结果会继续用于界面展示和分析报表。
"""

from utils.taxonomy import CLASS_IDS, class_counts_template


class VehicleCounter:
    """维护车辆累计数量、车型数量和滑动流量窗口。"""

    VALID_MODES = ("unique_track", "line_crossing")
    VALID_DIRECTIONS = ("horizontal", "vertical")

    def __init__(self, flow_window=60, mode="unique_track",
                 line_position=0.6, direction="horizontal"):
        """初始化计数模式、越线参数和内部历史状态。"""
        self.flow_window = flow_window
        self.mode = self._normalize_mode(mode)
        self.line_position = self._normalize_line_position(line_position)
        self.direction = self._normalize_direction(direction)
        self._seen = {}
        self._flow_log = []
        self._last_centers = {}
        self._last_sides = {}
        self._last_timestamp = 0.0

    def update(self, tracks, frame_idx=None, fps=None, timestamp=None, frame_shape=None):
        """消费当前帧跟踪结果，并按配置更新计数。"""
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
        """当前累计车辆数。"""
        return len(self._seen)

    def get_class_counts(self):
        """按车型返回累计数量。"""
        result = class_counts_template()
        for cls in self._seen.values():
            if cls in result:
                result[cls] += 1
        return result

    def get_flow_rate(self, seconds=None):
        """返回最近 seconds 秒内新增车辆数，默认使用 flow_window。"""
        seconds = seconds or self.flow_window
        cutoff = self._last_timestamp - seconds
        result = class_counts_template()
        for ts, cls in self._flow_log:
            if ts >= cutoff and cls in result:
                result[cls] += 1
        return result

    def get_flow_buckets(self, bucket_size=None):
        """按时间桶聚合流量，供 CSV/JSON 报表使用。"""
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
        """清空所有已计数车辆和历史越线状态。"""
        self._seen.clear()
        self._flow_log.clear()
        self._last_centers.clear()
        self._last_sides.clear()
        self._last_timestamp = 0.0

    def configure(self, mode=None, line_position=None, direction=None, reset=True):
        """更新计数配置；配置变化时默认清空旧统计，避免语义混用。"""
        changed = False
        if mode is not None:
            new_mode = self._normalize_mode(mode)
            if new_mode != self.mode:
                self.mode = new_mode
                changed = True
        if line_position is not None:
            new_position = self._normalize_line_position(line_position)
            if new_position != self.line_position:
                self.line_position = new_position
                changed = True
        if direction is not None:
            new_direction = self._normalize_direction(direction)
            if new_direction != self.direction:
                self.direction = new_direction
                changed = True

        if changed and reset:
            self.reset()
        return changed

    def get_line_coords(self, frame_height, frame_width):
        """根据当前越线方向和相对位置生成画面中的线段坐标。"""
        if self.direction == "vertical":
            x = int(frame_width * self.line_position)
            return (x, 0), (x, frame_height)
        y = int(frame_height * self.line_position)
        return (0, y), (frame_width, y)

    def _record(self, track_id, class_id, timestamp):
        """记录一次有效计数，并写入流量日志。"""
        self._seen[track_id] = class_id
        self._flow_log.append((timestamp, class_id))

    def _resolve_timestamp(self, frame_idx, fps, timestamp):
        """优先使用外部时间戳，否则从帧号和 FPS 推算。"""
        if timestamp is not None:
            self._last_timestamp = float(timestamp)
        elif frame_idx is not None and fps and fps > 0:
            self._last_timestamp = float(frame_idx) / float(fps)
        return self._last_timestamp

    def _update_line_crossing(self, track_id, class_id, bbox, timestamp, frame_shape):
        """在目标从越线一侧移动到另一侧时记录一次计数。"""
        center = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
        self._last_centers[track_id] = center
        if track_id in self._seen or frame_shape is None:
            return

        frame_height, frame_width = frame_shape[:2]
        if self.direction == "vertical":
            line_value = frame_width * self.line_position
            current_value = center[0]
        else:
            line_value = frame_height * self.line_position
            current_value = center[1]

        side = self._side_of_line(current_value, line_value)
        previous_side = self._last_sides.get(track_id)
        if side:
            self._last_sides[track_id] = side

        if previous_side and side and previous_side != side:
            self._record(track_id, class_id, timestamp)

    def _normalize_mode(self, mode):
        return mode if mode in self.VALID_MODES else "unique_track"

    def _normalize_direction(self, direction):
        return direction if direction in self.VALID_DIRECTIONS else "horizontal"

    def _normalize_line_position(self, line_position):
        return min(max(float(line_position), 0.0), 1.0)

    def _side_of_line(self, value, line_value):
        diff = value - line_value
        if diff < 0:
            return -1
        if diff > 0:
            return 1
        return 0
