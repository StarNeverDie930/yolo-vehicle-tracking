"""轨迹点缓存。

为每个 track_id 保存最近一段中心点坐标，用于在画面上绘制车辆移动轨迹。
"""

from collections import defaultdict


class TrajectoryStore:
    """按 track_id 维护固定长度的轨迹点列表。"""

    def __init__(self, max_length=50):
        """max_length 限制单个目标在画面上显示的轨迹长度。"""
        self.trajectories = defaultdict(list)
        self.max_length = max_length

    def update(self, track_id, bbox):
        """根据目标框中心点追加一条轨迹记录。"""
        cx = (bbox[0] + bbox[2]) // 2
        cy = (bbox[1] + bbox[3]) // 2
        traj = self.trajectories[track_id]
        traj.append((cx, cy))
        if len(traj) > self.max_length:
            traj.pop(0)

    def get(self, track_id):
        """返回指定目标的轨迹点。"""
        return self.trajectories.get(track_id, [])

    def get_all(self):
        """返回所有目标的轨迹点快照。"""
        return dict(self.trajectories)

    def clear(self):
        """清空所有轨迹。"""
        self.trajectories.clear()
