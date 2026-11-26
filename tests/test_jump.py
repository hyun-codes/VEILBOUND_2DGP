import unittest

from game.app import STAGE_1
from game.collision import CollisionWorld, Solid
from game.lantern_room import LanternRoom
from game.map_loader import load_map


class JumpTest(unittest.TestCase):
    def test_holding_jump_softens_descent_just_past_the_apex(self):
        self.room.step(1 / 60, 0, jump=True, jump_held=True)
        for _ in range(14):
            self.room.step(1 / 60, 0, jump_held=True)
        self.assertGreaterEqual(self.room.vy, 0)
        before = self.room.vy
        self.room.step(1 / 60, 0, jump_held=True)
        self.assertLess(self.room.vy - before, self.room.FALL_GRAVITY / 60)

        before = self.room.vy
        self.room.step(1 / 60, 0, jump_held=False)
        self.assertAlmostEqual(self.room.vy - before, self.room.FALL_GRAVITY / 60)
        before = self.room.vy
        self.room.step(1 / 60, 0, jump_held=True)
        self.assertAlmostEqual(self.room.vy - before, self.room.FALL_GRAVITY / 60)

    def test_walking_off_after_a_jump_uses_normal_fall_gravity(self):
        self.room.step(1 / 60, 0, jump=True, jump_held=True)
        for _ in range(55):
            self.room.step(1 / 60, 0, jump_held=True)
        self.assertTrue(self.room.grounded)
        self.room.x = 64
        self.room.step(1 / 60, 0, jump_held=True)
        self.assertAlmostEqual(self.room.vy, self.room.FALL_GRAVITY / 60)

    def test_quick_tap_has_useful_height_and_no_velocity_snap(self):
        self.room.step(1/60, 0, jump=True, jump_held=False)
        self.assertAlmostEqual(self.room.vy, -222)
        peak = self.room.y
        previous = self.room.vy
        for _ in range(35):
            self.room.step(1/60, 0, jump_held=False)
            if previous < 0 and self.room.vy < 0:
                self.assertLessEqual(self.room.vy - previous, 40.01)
            previous = self.room.vy
            peak = min(peak, self.room.y)
        self.assertGreaterEqual(100-peak, 18)
        self.assertLess(100-peak, 23)

    def test_buffered_jump_starts_on_landing_frame(self):
        self.room.y, self.room.vy, self.room.grounded = 99, 100, False
        self.room.jump_grace = 0
        self.room.step(1/60, 0, jump=True, jump_held=False)
        self.assertEqual(self.room.y, 100)
        self.assertLess(self.room.vy, 0)
        self.assertFalse(self.room.grounded)

    def setUp(self):
        self.room = LanternRoom(load_map(STAGE_1))
        self.solids = [Solid(0, 100, 60, 6)]
        self.room.collision = lambda: CollisionWorld(self.solids)
        self.room.x, self.room.y = 30, 100
        self.room.step(1/60, 0)

    def test_late_jump_after_walking_off_edge(self):
        self.room.x = 64
        self.room.step(1/60, 0)
        self.room.step(1/60, 0, jump=True)
        self.assertLess(self.room.vy, 0)

    def test_disappearing_floor_does_not_grant_coyote_jump(self):
        self.solids.clear()
        self.room.step(1/60, 0, jump=True)
        self.assertGreater(self.room.vy, 0)

    def test_jump_pressed_before_landing_is_buffered_once(self):
        self.room.y, self.room.vy, self.room.grounded = 95, 100, False
        self.room.jump_grace = 0.0
        self.room.step(1/60, 0, jump=True)
        self.assertGreater(self.room.vy, 0)
        for _ in range(5):
            self.room.step(1/60, 0)
        self.assertLess(self.room.vy, 0)
        self.assertLess(self.room.y, 100)

    def test_coyote_and_buffer_expire(self):
        self.room.x = 64
        for _ in range(8):
            self.room.step(1/60, 0)
        self.room.step(1/60, 0, jump=True)
        self.assertGreater(self.room.vy, 0)
        self.room.x, self.room.y, self.room.vy = 30, 40, 0
        self.room.step(1/60, 0, jump=True)
        for _ in range(45):
            self.room.step(1/60, 0)
        self.assertEqual(self.room.y, 100)
        self.assertEqual(self.room.vy, 0)

    def test_held_key_does_not_repeat_jump_and_reset_clears_pending_input(self):
        self.room.step(1/60, 0, jump=True, jump_held=True)
        for _ in range(60):
            self.room.step(1/60, 0, jump_held=True)
        self.assertEqual(self.room.y, 100)
        self.room.jump_buffer = 0.12
        self.room.reset()
        self.assertEqual(self.room.jump_buffer, 0)
        self.assertEqual(self.room.jump_grace, 0)

    def test_wide_ceiling_still_blocks_jump(self):
        self.solids = [Solid(0, 60, 100, 5)]
        self.room.y, self.room.vy, self.room.grounded = 79, -150, False
        self.room.step(1/60, 0)
        self.assertEqual(self.room.x, 30)
        self.assertEqual(self.room.vy, 0)

    def test_app_passes_space_hold_and_release_to_physics(self):
        from itertools import count
        from unittest.mock import Mock, patch
        from game import app
        from game.pico2d_backend import InputEvent
        backend, room = Mock(), Mock(complete=False)
        backend.poll_events.side_effect = [
            [InputEvent('key_down', 'space')], [], [InputEvent('key_up', 'space')]]
        with patch.object(app, 'Pico2DBackend', return_value=backend), \
                patch.object(app, 'LanternView'), patch.object(app, 'sleep'), \
                patch.object(app, 'perf_counter', side_effect=count(0, 1/60)):
            app.run(room, 3, None)
        calls = room.step.call_args_list
        self.assertTrue(calls[0].args[2])
        self.assertTrue(calls[0].kwargs['jump_held'])
        self.assertTrue(calls[1].kwargs['jump_held'])
        self.assertFalse(calls[1].args[2])
        self.assertFalse(calls[-1].kwargs['jump_held'])

    def test_short_press_is_lower_than_held_jump(self):
        def height(held):
            self.room.reset()
            self.room.x, self.room.y = 30, 100
            self.room.step(1/60, 0, jump=True, jump_held=True)
            peak = self.room.y
            for _ in range(40):
                self.room.step(1/60, 0, jump_held=held)
                peak = min(peak, self.room.y)
            return 100-peak
        full, short = height(True), height(False)
        self.assertGreaterEqual(full, 27)
        self.assertLessEqual(full, 28)
        self.assertGreater(full, short+8)

    def test_reholding_after_release_does_not_restore_upward_boost(self):
        self.room.step(1/60, 0, jump=True, jump_held=True)
        for _ in range(5):
            self.room.step(1/60, 0, jump_held=False)
        before = self.room.vy
        self.room.step(1/60, 0, jump_held=True)
        self.assertAlmostEqual(self.room.vy-before, 40)

    def test_small_ceiling_corner_is_corrected_without_going_through_wall(self):
        self.solids = [Solid(32, 60, 15, 5)]
        self.room.y, self.room.vy, self.room.grounded = 79, -150, False
        self.room.step(1/60, 0)
        self.assertLess(self.room.x, 30)
        self.assertLess(self.room.vy, 0)
        self.assertFalse(self.room.collision().overlaps(
            self.room.x, self.room.y, self.room.WIDTH, self.room.HEIGHT))
