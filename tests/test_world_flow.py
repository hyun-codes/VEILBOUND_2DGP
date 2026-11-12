from dataclasses import replace
import unittest

from game.app import Game, STAGE_1
from game.collision import Solid
from game.map_loader import load_map
from game.pico2d_backend import InputEvent
from game.world_state import WorldState


DT = 1 / 60


class WorldFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_map(STAGE_1)

    def press(self, game, key="shift_left"):
        game.handle_events([InputEvent("key_down", key)])

    def release(self, game, key="shift_left"):
        game.handle_events([InputEvent("key_up", key)])

    def assert_synchronized(self, game, name):
        self.assertEqual(game.world_state.name, name)
        self.assertEqual(game.scene.world, name)
        self.assertIs(game.player.collision, game.collision)
        self.assertTrue(all(s.world in ("common", name) for s in game.collision.solids))
        image = "shadow_jack_flame.png" if name == "shadow" else "Red_Hand_Jack_SPRITESHEET.png"
        self.assertEqual(game.player.animations.image.name, image)

    def test_shift_consumed_once_on_physics_step_and_taps_are_not_dropped(self):
        game = Game(self.data)
        game.player.animation_time = 0.3
        self.press(game)
        self.assert_synchronized(game, "real")  # 고정 갱신 전 그리기는 이전 상태 그대로다.
        self.assertEqual(game.pending_switches, 1)
        game.step(DT)
        self.assert_synchronized(game, "shadow")
        self.assertAlmostEqual(game.player.animation_time, 0.3 + DT)
        for _ in range(10):
            self.press(game)
            game.step(DT)
        self.assert_synchronized(game, "shadow")
        self.release(game)
        self.press(game)
        self.release(game)
        self.press(game)
        self.assertEqual(game.pending_switches, 2)
        game.step(DT)
        self.assert_synchronized(game, "shadow")

    def test_two_shift_keys_are_one_logical_hold(self):
        game = Game(self.data)
        self.press(game, "shift_left")
        self.press(game, "shift_right")
        game.step(DT)
        self.assert_synchronized(game, "shadow")
        self.release(game, "shift_left")
        self.press(game, "shift_left")
        game.step(DT)
        self.assert_synchronized(game, "shadow")
        self.release(game, "shift_left")
        self.release(game, "shift_right")
        self.press(game, "shift_right")
        game.step(DT)
        self.assert_synchronized(game, "real")

    def test_toggle_preserves_position_velocity_camera_and_jump_state(self):
        game = Game(self.data)
        p = game.player
        p.x, p.y, p.vx, p.vy, p.grounded = 150, 150, 64, -100, False
        p.jump_held, p.jump_buffer = True, 0.1
        before = (p.x, p.y, p.vx, p.vy, game.camera.x, game.camera.y, p.jump_held, p.jump_buffer)
        self.assertTrue(game.world_state.try_toggle(p))
        self.assertEqual(before, (p.x, p.y, p.vx, p.vy, game.camera.x, game.camera.y, p.jump_held, p.jump_buffer))
        self.assertIs(p.collision, game.world_state.collision)

    def test_surface_contact_allowed_and_bridge_removal_cannot_grant_coyote_jump(self):
        game = Game(self.data, "shadow")
        p = game.player
        p.x, p.y, p.grounded, p.coyote = 160, 183, True, p.COYOTE_TIME
        self.press(game, "space")
        self.press(game)
        game.step(DT)
        self.assert_synchronized(game, "real")
        self.assertFalse(p.grounded)
        self.assertEqual(p.coyote, 0)
        self.assertGreater(p.vy, 0)
        self.assertGreater(p.y, 183)
        # 평평한 공통 지면의 면 접촉은 거부하지 않는다.
        game = Game(self.data)
        self.press(game)
        game.step(DT)
        self.assert_synchronized(game, "shadow")
        self.assertTrue(game.player.grounded)
        self.assertEqual(game.player.y, 183)

    def test_switch_into_bridge_interior_rejected_without_retry_or_teleport(self):
        game = Game(self.data)
        p = game.player
        p.x, p.y, p.vx, p.vy, p.grounded, p.coyote = 160, 190, 0, 60, False, 0
        before = (p.x, p.y, p.vx, p.vy, p.collision)
        self.assertFalse(game.world_state.try_toggle(p))
        self.assertEqual(before, (p.x, p.y, p.vx, p.vy, p.collision))
        self.press(game)
        game.step(DT)
        self.assert_synchronized(game, "real")
        self.assertGreater(game.blocked_notice, 0)
        self.assertEqual(game.pending_switches, 0)
        p.x, p.y, p.vy = 28, 183, 0
        game.step(DT)
        self.assert_synchronized(game, "real")  # 위치가 안전해져도 자동 재시도하지 않는다.
        self.release(game)
        self.press(game)
        game.step(DT)
        self.assert_synchronized(game, "shadow")
        self.assertEqual(game.blocked_notice, 0)

    def test_target_overlap_uses_body_and_allows_side_and_ceiling_touch(self):
        game = Game(self.data)
        p = game.player
        state = WorldState([Solid(100, 100, 8, 8, "shadow")])
        for x, feet, expected in ((97, 108, True), (111, 108, True), (104, 100, True),
                                  (104, 122, True), (104, 110, False)):
            state.reset()
            p.x, p.y = x, feet
            self.assertEqual(state.try_toggle(p), expected)

    def test_focus_or_restart_discards_pending_switch_and_resets_real(self):
        game = Game(self.data, "shadow")
        self.press(game)
        game.handle_events([InputEvent("focus_lost"), InputEvent("focus_gained")])
        self.assertEqual(game.pending_switches, 0)
        game.step(DT)
        self.assert_synchronized(game, "shadow")
        self.press(game)
        self.press(game, "r")
        game.step(DT)
        self.assert_synchronized(game, "real")
        self.assertEqual(game.pending_switches, 0)
        self.assertEqual((game.player.x, game.player.y), (28, 183))

    def test_play_real_switch_cross_bridge_clear_then_restart(self):
        game = Game(self.data)
        self.press(game, "d")
        for _ in range(65):
            game.step(DT)
        self.assertFalse(game.completed)
        self.press(game)
        game.step(DT)
        self.assert_synchronized(game, "shadow")
        self.release(game)
        for _ in range(220):
            game.step(DT)
            if game.player_at_exit():
                break
        self.assertFalse(game.completed)
        self.assertTrue(game.player_at_exit())
        self.release(game, "d")
        self.press(game)
        game.step(DT)
        self.assert_synchronized(game, "real")
        self.assertTrue(game.completed)
        self.assertEqual(game.respawns, 0)
        snapshot = (game.player.x, game.player.y, game.camera.x, game.scene.world)
        self.press(game, "space")
        self.release(game)
        self.press(game)
        for _ in range(10):
            game.step(DT)
        self.assertEqual(snapshot, (game.player.x, game.player.y, game.camera.x, game.scene.world))
        self.assertEqual(game.pending_switches, 0)
        self.assertEqual(game.player.jump_buffer, 0)
        self.press(game, "r")
        self.assertFalse(game.completed)
        self.assert_synchronized(game, "real")
        self.assertEqual((game.player.x, game.player.y, game.player.vy), (28, 183, 0))
        self.assertEqual((game.camera.x, game.camera.y), (0, 40))

    def test_exit_only_in_real_and_fall_takes_priority_over_exit(self):
        for name in ("real", "shadow"):
            game = Game(self.data, name)
            game.player.x = 290
            game.step(DT)
            self.assertEqual(game.completed, name == "real")
            self.assertEqual(game.scene.world, name)
        objects = tuple(replace(obj, x=150, y=260, width=30, height=80)
                        if obj.name == "Exit" else obj for obj in self.data.objects)
        game = Game(replace(self.data, objects=objects), "shadow")
        game.player.x, game.player.y, game.player.grounded = 160, 270, False
        game.step(DT)
        self.assertEqual(game.respawns, 1)
        self.assertFalse(game.completed)
        self.assert_synchronized(game, "real")

    def test_switch_to_shadow_midair_can_land_on_bridge(self):
        game = Game(self.data)
        p = game.player
        p.x, p.y, p.vy, p.grounded, p.coyote = 160, 160, 50, False, 0
        self.press(game)
        for _ in range(30):
            game.step(DT)
        self.assert_synchronized(game, "shadow")
        self.assertTrue(p.grounded)
        self.assertEqual(p.y, 183)

    def test_coyote_is_kept_only_if_previous_support_still_exists(self):
        game = Game(self.data, "shadow")
        p = game.player
        p.grounded, p.coyote = False, 0.04
        p.x, p.y = 160, 183.5
        p.last_support = (160, 183)
        self.assertTrue(game.world_state.try_toggle(p))
        self.assertEqual(p.coyote, 0)
        # 두 세계 공통 지면에서 생긴 정상 유예는 전환 때문에 취소하지 않는다.
        p.x, p.y = 28, 180
        p.last_support, p.coyote = (28, 183), 0.04
        self.assertTrue(game.world_state.try_toggle(p))
        self.assertEqual(p.coyote, 0.04)
        self.assertFalse(p.grounded)

    def test_exit_frames_distinguish_worlds_without_text(self):
        game = Game(self.data)
        class Recorder:
            def __init__(self):
                self.boxes = []
            def begin(self, *args):
                pass
            def sprite(self, *args):
                pass
            def rectangle(self, rect, color, **kwargs):
                self.boxes.append(color)
            def label(self, x, y, text, *args):
                raise AssertionError(f"Unexpected gameplay text: {text}")
        r = Recorder()
        game.blocked_notice = 0.4
        game.draw(r)
        self.assertIn((116, 223, 188), r.boxes)
        shadow = Game(self.data, "shadow")
        shadow.player.x = 290
        shadow.step(DT)
        r.boxes.clear()
        shadow.draw(r)
        self.assertIn((150, 151, 170), r.boxes)
        self.assertFalse(shadow.completed)
        game.player.x = 290
        game.step(DT)
        r.boxes.clear()
        game.draw(r)
        self.assertTrue(game.completed)
