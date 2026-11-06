import unittest

from game.app import Game, STAGE_1, main
from game.map_loader import load_map
from game.pico2d_backend import InputEvent


class FakeBackend:
    def __init__(self):
        self.frames = 0
        self.closed = False

    def open(self, width, height):
        self.dimensions = width, height

    def close(self):
        self.closed = True

    def poll_events(self):
        return []

    def begin(self, color):
        pass

    def sprite(self, sprite, rect):
        pass

    def label(self, *args):
        pass

    def rectangle(self, *args, **kwargs):
        pass

    def present(self):
        self.frames += 1


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_map(STAGE_1)

    def test_focus_and_reset_clear_keys_and_time(self):
        game = Game(self.data)
        game.handle_events([InputEvent("key_down", "right")])
        game.step(0.1)
        self.assertGreater(game.player.x, 28)
        self.assertEqual(game.camera.x, 0)  # 시작 근처의 이동은 데드존 안이다.
        game.stepper.accumulator = 0.01
        self.assertTrue(game.handle_events([InputEvent("focus_lost")]))
        self.assertTrue(game.paused)
        self.assertEqual(game.keys, set())
        self.assertEqual(game.stepper.accumulator, 0)
        self.assertEqual(game.player.jump_buffer, 0)
        game.handle_events([InputEvent("key_down", "right"), InputEvent("focus_gained")])
        self.assertFalse(game.paused)
        self.assertEqual(game.keys, set())
        game.handle_events([InputEvent("key_down", "r")])
        self.assertEqual(game.camera.x, 0)
        self.assertEqual((game.player.x, game.player.y, game.player.vy), (28, 183, 0))

    def test_space_is_single_press_and_survives_frames_without_a_step(self):
        game = Game(self.data)
        game.handle_events([InputEvent("key_down", "space")])
        self.assertGreater(game.player.jump_buffer, 0)
        game.step(1 / 60)
        self.assertLess(game.player.vy, 0)

        for _ in range(90):
            game.handle_events([InputEvent("key_down", "space")])
            game.step(1 / 60)
        self.assertTrue(game.player.grounded)
        self.assertEqual(game.player.y, 183)
        game.handle_events([InputEvent("key_up", "space"), InputEvent("key_down", "space")])
        game.step(1 / 60)
        self.assertLess(game.player.vy, 0)

    def test_space_release_before_step_and_focus_clear_jump_hold(self):
        game = Game(self.data)
        game.handle_events([InputEvent("key_down", "space"), InputEvent("key_up", "space")])
        game.step(1 / 60)
        self.assertFalse(game.player.jump_held)
        self.assertLess(game.player.vy, 0)
        self.assertGreaterEqual(game.player.vy, -game.player.RELEASE_SPEED)
        game.handle_events([InputEvent("key_down", "space"), InputEvent("focus_lost")])
        self.assertFalse(game.player.jump_held)
        self.assertEqual(game.player.jump_buffer, 0)

    def test_fall_and_r_restore_position_inputs_camera_and_animation(self):
        game = Game(self.data)
        game.player.x, game.player.y = 160, self.data.height + game.player.HEIGHT + 1
        game.player.grounded, game.player.coyote = False, 0
        game.handle_events([InputEvent("key_down", "right"), InputEvent("key_down", "space")])
        game.step(1 / 60)
        self.assertEqual(game.respawns, 1)
        self.assertEqual(game.keys, set())
        self.assertEqual((game.player.x, game.player.y, game.player.vy), (28, 183, 0))
        self.assertEqual((game.player.animation, game.player.jump_buffer), ("idle", 0))
        game.handle_events([InputEvent("key_down", "right")])
        for _ in range(5):
            game.step(1 / 60)
        game.handle_events([InputEvent("key_down", "r")])
        self.assertEqual((game.player.x, game.player.y, game.player.vx), (28, 183, 0))
        self.assertEqual((game.camera.x, game.camera.y, game.camera.look_ahead), (0, 40, 0))

    def test_shadow_start_can_walk_to_exit_and_stop_at_completion(self):
        game = Game(self.data, "shadow")
        game.handle_events([InputEvent("key_down", "right")])
        for _ in range(250):
            game.step(1 / 60)
        self.assertGreater(game.player.x + game.player.WIDTH / 2, 288)
        self.assertTrue(game.completed)
        self.assertEqual(game.respawns, 0)
        self.assertEqual(game.player.y, 183)
        self.assertGreater(game.camera.x, 0)
        game.handle_events([InputEvent("key_down", "left")])
        before = game.player.x
        game.step(1 / 60)
        self.assertEqual(game.player.x, before)  # 좌우 동시 입력은 정지한다.

    def test_ad_and_arrow_keys_combine_without_speed_or_release_errors(self):
        game = Game(self.data)
        game.handle_events([InputEvent("key_down", "d"), InputEvent("key_down", "right")])
        game.step(1 / 60)
        self.assertAlmostEqual(game.player.x, 28 + game.player.SPEED / 60)
        game.handle_events([InputEvent("key_up", "right")])
        game.step(1 / 60)
        self.assertEqual(game.player.direction, 1)  # D가 남아 있으면 계속 이동한다.
        game.handle_events([InputEvent("key_down", "a")])
        before = game.player.x
        game.step(1 / 60)
        self.assertEqual(game.player.x, before)
        game.handle_events([InputEvent("key_up", "d")])
        game.step(1 / 60)
        self.assertEqual(game.player.direction, -1)
        game.handle_events([InputEvent("focus_lost"), InputEvent("focus_gained")])
        game.step(1 / 60)
        self.assertEqual(game.player.direction, 0)

    def test_quit_and_escape_work_even_when_paused(self):
        for event in (InputEvent("quit"), InputEvent("key_down", "escape")):
            game = Game(self.data)
            game.handle_events([InputEvent("focus_lost"), event])
            self.assertFalse(game.running)

    def test_bounded_run_closes_backend_and_releases_world(self):
        game, backend = Game(self.data), FakeBackend()
        game.run(backend, max_frames=2)
        self.assertEqual(backend.dimensions, (800, 600))
        self.assertEqual(backend.frames, 2)
        self.assertTrue(backend.closed)

    def test_cli_map_validation_needs_no_renderer(self):
        self.assertEqual(main(["--check-map"]), 0)

    def test_backend_is_closed_on_render_failure(self):
        backend = FakeBackend()

        def fail(color):
            raise RuntimeError("render failure")

        backend.begin = fail
        with self.assertRaisesRegex(RuntimeError, "render failure"):
            Game(self.data).run(backend, max_frames=1)
        self.assertTrue(backend.closed)
