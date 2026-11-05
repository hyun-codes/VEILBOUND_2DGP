import unittest

from game.camera import Camera
from game.timing import FixedStepper


class TimingTests(unittest.TestCase):
    def test_30_and_60_render_frames_produce_same_physics(self):
        totals = []
        for fps in (30, 60):
            clock, ticks = FixedStepper(), []
            for _ in range(fps):
                clock.advance(1 / fps, ticks.append)
            self.assertEqual(len(ticks), 60)
            self.assertEqual(set(ticks), {1 / 60})
            totals.append(sum(ticks))
        self.assertAlmostEqual(*totals)

    def test_stall_caps_work_and_discards_whole_backlog(self):
        clock, ticks = FixedStepper(), []
        self.assertEqual(clock.advance(0.5, ticks.append), 5)
        self.assertEqual(len(ticks), 5)
        self.assertLess(clock.accumulator, clock.dt)
        self.assertGreater(clock.dropped_seconds, 0.4)
        self.assertEqual(clock.advance(0, ticks.append), 0)
        clock.reset()
        self.assertEqual(clock.accumulator, 0)

    def test_invalid_elapsed_is_rejected(self):
        for elapsed in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                FixedStepper().advance(elapsed, lambda dt: None)


class CameraTests(unittest.TestCase):
    def test_stage_bounds_and_integer_pixel_edges(self):
        camera = Camera(320, 240)
        camera.set_position(1000, 1000)
        self.assertAlmostEqual(camera.x, 320 - 800 / 3)
        self.assertEqual(camera.y, 40)
        self.assertEqual(camera.screen_rect(320, 240, 0, 0), (800, 0, 0, 0))
        left = camera.screen_rect(120, 176, 8, 8)
        right = camera.screen_rect(128, 176, 8, 8)
        self.assertEqual(left[0] + left[2], right[0])
        self.assertEqual(left[2:], (24, 24))

    def test_small_map_centers_and_camera_does_not_change_world_objects(self):
        camera = Camera(100, 100)
        camera.focus(90, 90)
        self.assertAlmostEqual(camera.x, (100 - 800 / 3) / 2)
        self.assertEqual(camera.y, -50)
        self.assertEqual(camera.screen_rect(0, 0, 100, 100), (250, 150, 300, 300))
