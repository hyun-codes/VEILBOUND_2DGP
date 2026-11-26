import unittest
from unittest.mock import Mock, patch

from game import app
from game.pico2d_backend import InputEvent
from game.title_screen import TitleScreen


class TitleScreenTest(unittest.TestCase):
    def test_keyboard_opens_settings_toggles_motion_and_returns(self):
        title = TitleScreen()
        title.handle(InputEvent("key_down", "s"))
        self.assertIsNone(title.handle(InputEvent("key_down", "enter")))
        self.assertTrue(title.in_settings)
        title.handle(InputEvent("key_down", "space"))
        self.assertFalse(title.motion)
        title.handle(InputEvent("key_down", "escape"))
        self.assertFalse(title.in_settings)
        title.handle(InputEvent("key_down", "up"))
        self.assertEqual(title.handle(InputEvent("key_down", "enter")), "play")

    def test_mouse_hover_does_not_activate_and_click_only_accepts_menu_rows(self):
        title = TitleScreen()
        self.assertIsNone(title.handle(InputEvent("hover", x=400, y=195)))
        self.assertEqual(title.selected, 2)
        self.assertIsNone(title.handle(InputEvent("click", x=400, y=60)))
        self.assertEqual(title.handle(InputEvent("click", x=400, y=195)), "quit")

    def test_default_run_loads_first_room_only_after_play(self):
        backend = Mock()
        backend.poll_events.side_effect = [[], [InputEvent("key_down", "enter")]]
        with patch.object(app, "Pico2DBackend", return_value=backend), patch.object(app, "sleep"), \
                patch.object(app, "load_map", wraps=app.load_map) as load, \
                patch.object(app, "LanternView") as view:
            app.run(None, 2, None)
        load.assert_called_once_with(app.STAGES[1])
        self.assertEqual(view.call_args.args[0].data.path, app.STAGES[1])
        backend.text.assert_any_call(unittest.mock.ANY, 74, "VEILBOUND", 400, 438, unittest.mock.ANY)
        backend.close.assert_called_once()

    def test_stage_argument_bypasses_title(self):
        with patch.object(app, "run") as run:
            self.assertEqual(app.main(["--stage", "6", "--frames", "1"]), 0)
        self.assertEqual(run.call_args.args[0].data.path, app.STAGES[6])
