from collections import defaultdict


class TrajectoryStore:
    def __init__(self, max_length=50):
        self.trajectories = defaultdict(list)
        self.max_length = max_length

    def update(self, track_id, bbox):
        cx = (bbox[0] + bbox[2]) // 2
        cy = (bbox[1] + bbox[3]) // 2
        traj = self.trajectories[track_id]
        traj.append((cx, cy))
        if len(traj) > self.max_length:
            traj.pop(0)

    def get(self, track_id):
        return self.trajectories.get(track_id, [])

    def get_all(self):
        return dict(self.trajectories)

    def clear(self):
        self.trajectories.clear()
