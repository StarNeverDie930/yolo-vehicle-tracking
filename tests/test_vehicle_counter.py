import unittest

from analysis.counter import VehicleCounter


FRAME_SHAPE = (100, 200, 3)


def make_track(track_id, bbox, class_id=0):
    return {
        "track_id": track_id,
        "class_id": class_id,
        "bbox": bbox,
    }


class VehicleCounterTest(unittest.TestCase):
    def test_unique_track_counts_each_track_once(self):
        counter = VehicleCounter(mode="unique_track")

        counter.update([make_track(1, [0, 10, 10, 20])], timestamp=0)
        counter.update([make_track(1, [0, 20, 10, 30])], timestamp=1)
        counter.update([make_track(2, [0, 30, 10, 40], class_id=1)], timestamp=2)

        self.assertEqual(counter.count, 2)
        self.assertEqual(counter.get_class_counts()[0], 1)
        self.assertEqual(counter.get_class_counts()[1], 1)

    def test_horizontal_line_crossing_counts_when_center_changes_sides(self):
        counter = VehicleCounter(
            mode="line_crossing",
            line_position=0.5,
            direction="horizontal",
        )

        counter.update([make_track(1, [0, 10, 10, 20])], timestamp=0, frame_shape=FRAME_SHAPE)
        counter.update([make_track(1, [0, 70, 10, 80])], timestamp=1, frame_shape=FRAME_SHAPE)

        self.assertEqual(counter.count, 1)
        self.assertEqual(counter.get_class_counts()[0], 1)
        self.assertEqual(counter.get_flow_rate()[0], 1)

    def test_vertical_line_crossing_counts_when_center_changes_sides(self):
        counter = VehicleCounter(
            mode="line_crossing",
            line_position=0.5,
            direction="vertical",
        )

        counter.update([make_track(1, [20, 0, 30, 10], class_id=2)], timestamp=0, frame_shape=FRAME_SHAPE)
        counter.update([make_track(1, [140, 0, 150, 10], class_id=2)], timestamp=1, frame_shape=FRAME_SHAPE)

        self.assertEqual(counter.count, 1)
        self.assertEqual(counter.get_class_counts()[2], 1)

    def test_touching_line_does_not_count_until_track_reaches_other_side(self):
        counter = VehicleCounter(
            mode="line_crossing",
            line_position=0.5,
            direction="horizontal",
        )

        counter.update([make_track(1, [0, 35, 10, 45])], timestamp=0, frame_shape=FRAME_SHAPE)
        counter.update([make_track(1, [0, 45, 10, 55])], timestamp=1, frame_shape=FRAME_SHAPE)
        self.assertEqual(counter.count, 0)

        counter.update([make_track(1, [0, 55, 10, 65])], timestamp=2, frame_shape=FRAME_SHAPE)
        self.assertEqual(counter.count, 1)

    def test_tracks_on_same_side_are_not_counted(self):
        counter = VehicleCounter(
            mode="line_crossing",
            line_position=0.5,
            direction="horizontal",
        )

        counter.update([make_track(1, [0, 10, 10, 20])], timestamp=0, frame_shape=FRAME_SHAPE)
        counter.update([make_track(1, [0, 20, 10, 30])], timestamp=1, frame_shape=FRAME_SHAPE)

        self.assertEqual(counter.count, 0)
        self.assertEqual(sum(counter.get_class_counts().values()), 0)

    def test_same_track_is_not_counted_twice_after_crossing(self):
        counter = VehicleCounter(
            mode="line_crossing",
            line_position=0.5,
            direction="horizontal",
        )

        counter.update([make_track(1, [0, 10, 10, 20])], timestamp=0, frame_shape=FRAME_SHAPE)
        counter.update([make_track(1, [0, 70, 10, 80])], timestamp=1, frame_shape=FRAME_SHAPE)
        counter.update([make_track(1, [0, 10, 10, 20])], timestamp=2, frame_shape=FRAME_SHAPE)

        self.assertEqual(counter.count, 1)
        self.assertEqual(counter.get_flow_rate()[0], 1)

    def test_configure_resets_counts_when_counter_semantics_change(self):
        counter = VehicleCounter(mode="unique_track")

        counter.update([make_track(1, [0, 10, 10, 20])], timestamp=0)
        changed = counter.configure(mode="line_crossing")

        self.assertTrue(changed)
        self.assertEqual(counter.count, 0)
        self.assertEqual(counter.mode, "line_crossing")


if __name__ == "__main__":
    unittest.main()
