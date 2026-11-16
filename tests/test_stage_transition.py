import unittest
from itertools import count
from unittest.mock import Mock, patch

from game import app
from game.pico2d_backend import InputEvent


class StageTransitionTest(unittest.TestCase):
    def test_next_room_is_revealed_after_blackout_and_ignores_transition_inputs(self):
        old_room = Mock(complete=True)
        new_room = Mock(complete=False)
        backend = Mock()
        clock = count(0, 1 / 120)
        frames = []
        current = {}

        def draw(room):
            view = Mock()
            view.draw.side_effect = lambda backend: current.update(room=room, overlays=[], orb=False)
            return view

        def events():
            if 8 < len(frames) < 37:
                return [InputEvent("key_down", key) for key in ("d", "r", "space", "e")]
            return []

        backend.poll_events.side_effect = events
        backend.overlay.side_effect = lambda bounds, color: current["overlays"].append(color[3])
        backend.image.side_effect = lambda *args: current.update(orb=True)
        backend.present.side_effect = lambda: frames.append(current.copy())
        with patch.object(app, "Pico2DBackend", return_value=backend), patch.object(app, "sleep"), \
                patch.object(app, "perf_counter", side_effect=clock), \
                patch.object(app, "load_map") as load_map, \
                patch.object(app, "LanternRoom", return_value=new_room), \
                patch.object(app, "LanternView", side_effect=lambda room, *size: draw(room)):
            app.run(old_room, 55, None, next_room=2)

        load_map.assert_called_once_with(app.STAGE_2)
        first_new = next(i for i, frame in enumerate(frames) if frame["room"] is new_room)
        self.assertTrue(any(0 < f["overlays"][0] < 255 for f in frames[:first_new] if f["overlays"]))
        self.assertEqual(frames[first_new]["overlays"][0], 255)
        self.assertTrue(any(f["orb"] for f in frames if f["overlays"] and f["overlays"][0] == 255))
        self.assertEqual(frames[-1]["overlays"], [])
        old_room.step.assert_called_once()
        new_room.reset.assert_not_called()
        self.assertTrue(new_room.step.called)
        self.assertTrue(all(call.args[1:] == (0, False, False) for call in new_room.step.call_args_list))
