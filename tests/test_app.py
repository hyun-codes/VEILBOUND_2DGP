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
        self.assertGreater(game.camera.x, 0)
        game.stepper.accumulator = 0.01
        self.assertTrue(game.handle_events([InputEvent("focus_lost")]))
        self.assertTrue(game.paused)
        self.assertEqual(game.keys, set())
        self.assertEqual(game.stepper.accumulator, 0)
        game.handle_events([InputEvent("key_down", "right"), InputEvent("focus_gained")])
        self.assertFalse(game.paused)
        self.assertEqual(game.keys, set())
        game.handle_events([InputEvent("key_down", "r")])
        self.assertEqual(game.camera.x, 0)

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
