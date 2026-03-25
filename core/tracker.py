from deep_sort_realtime.deepsort_tracker import DeepSort


class VehicleTracker:
    def __init__(self, max_age=10, n_init=5, max_cosine_distance=0.2, nn_budget=100,
                 max_staleness=3):
        self.max_staleness = max_staleness
        self.tracker = DeepSort(
            max_age=max_age,
            n_init=n_init,
            max_cosine_distance=max_cosine_distance,
            nn_budget=nn_budget,
        )

    def update(self, detections, frame):
        """
        输入: detections = [([x1,y1,x2,y2], conf, class_id), ...]
        返回: [{"track_id": int, "bbox": [x1,y1,x2,y2], "class_id": int}, ...]
        """
        if not detections:
            self.tracker.update_tracks([], frame=frame)
            return []

        # deep-sort-realtime 需要 ([left,top,w,h], conf, class) 格式
        ds_detections = []
        for (xyxy, conf, cls) in detections:
            x1, y1, x2, y2 = xyxy
            ds_detections.append(([x1, y1, x2 - x1, y2 - y1], conf, cls))

        tracks = self.tracker.update_tracks(ds_detections, frame=frame)

        h, w = frame.shape[:2]
        results = []
        for track in tracks:
            if not track.is_confirmed():
                continue
            # 跳过丢失匹配超过阈值的轨迹（幽灵框）
            if track.time_since_update > self.max_staleness:
                continue
            ltrb = track.to_ltrb()
            # 过滤超出画面的框
            if ltrb[0] < 0 and ltrb[2] < 0 or ltrb[1] < 0 and ltrb[3] < 0:
                continue
            if ltrb[0] > w or ltrb[1] > h:
                continue
            results.append({
                "track_id": track.track_id,
                "bbox": [int(max(0, v)) for v in ltrb],
                "class_id": track.det_class if track.det_class is not None else -1,
                "matched": track.time_since_update == 0,
            })
        return results

    def reset(self):
        self.tracker.delete_all_tracks()
