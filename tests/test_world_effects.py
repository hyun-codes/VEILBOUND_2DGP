from dataclasses import replace
import unittest
from unittest.mock import patch

from game.app import Game, STAGE_1
from game.camera import Camera
from game.map_loader import load_map
from game.map_scene import MapScene
from game.pico2d_backend import InputEvent
from game.world_effects import WorldEffects, shadow_lamp_pixel


class Recorder:
    def __init__(self):
        self.sprites = []
        self.labels = []

    def begin(self, *args):
        pass

    def sprite(self, sprite, rect):
        self.sprites.append((sprite, rect))

    def label(self, x, y, text, *args):
        self.labels.append(text)

    def rectangle(self, *args, **kwargs):
        pass


class FakeBackend(Recorder):
    def __init__(self, events):
        super().__init__()
        self.events = events
        self.closed = False

    def open(self, *args):
        pass

    def poll_events(self):
        return self.events

    def present(self):
        pass

    def close(self):
        self.closed = True


class WorldEffectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_map(STAGE_1)

    def test_visual_roles_come_from_map_and_shared_lamp_definition(self):
        roles = {s.visual_role for s in self.data.sprites}
        self.assertEqual(roles, {"background", "fog", "terrain", "prop", "lamp"})
        self.assertTrue(all(s.visual_role == "lamp" for s in self.data.sprites if "lamp" in s.object_name.lower()))
        self.assertEqual(sum(s.visual_role == "fog" for s in self.data.sprites), 1)

    def test_transition_uses_elapsed_time_and_interrupts_without_color_jump(self):
        fx = WorldEffects()
        fx.switch("shadow")
        fx.advance(0.1)
        self.assertAlmostEqual(fx.shadow, 0.5)
        fx.switch("real")
        self.assertAlmostEqual(fx.shadow, 0.5)
        fx.advance(0.2)
        self.assertEqual(fx.shadow, 0)
        fx.switch("shadow")
        fx.advance(0.5)
        self.assertEqual(fx.shadow, 1)
        self.assertEqual(fx.notice, 0)

    def test_render_rate_does_not_change_transition_length(self):
        for fps in (30, 60, 120):
            fx = WorldEffects()
            fx.switch("shadow")
            for _ in range(int(fps * 0.2)):
                fx.advance(1 / fps)
            self.assertAlmostEqual(fx.shadow, 1)
            self.assertAlmostEqual(fx.age, 0.2)

    def test_wave_splits_only_background_and_keeps_shared_pixel_edges(self):
        fx = WorldEffects("shadow")
        fx.advance(0.3)
        bg = next(s for s in self.data.sprites if s.visual_role == "background")
        pieces = list(fx.pieces(bg, bg.x, bg.y))
        self.assertGreater(len(pieces), 1)
        self.assertEqual(sum(s.source[3] for s in pieces), bg.source[3])
        self.assertTrue(any(s.x != bg.x for s in pieces))
        for a, b in zip(pieces, pieces[1:]):
            self.assertEqual(a.y + a.height, b.y)
        for role in ("terrain", "lamp", "prop", "none"):
            sprite = replace(bg, visual_role=role)
            result = list(fx.pieces(sprite, 12, 15))
            self.assertEqual(len(result), 1)
            self.assertEqual((result[0].x, result[0].y, result[0].source), (12, 15, bg.source))

    def test_motion_off_freezes_fog_and_retains_palette_and_world_notice(self):
        fx = WorldEffects()
        fx.advance(1)
        offset, clock = fx.fog_offset, fx.clock
        fx.motion_enabled = False
        fx.switch("shadow")
        fx.advance(0.2)
        self.assertEqual((fx.fog_offset, fx.clock), (offset, clock))
        self.assertEqual(fx.shadow, 1)
        self.assertGreater(fx.notice, 0)
        bg = next(s for s in self.data.sprites if s.visual_role == "background")
        self.assertEqual(len(list(fx.pieces(bg, bg.x, bg.y))), 1)
        self.assertNotEqual(fx.style(bg).tint, bg.tint)

    def test_fog_reverses_and_stops_after_completion(self):
        real, shadow = WorldEffects(), WorldEffects("shadow")
        real.advance(1)
        shadow.advance(1)
        self.assertEqual(real.fog_offset, 2)
        self.assertEqual(shadow.fog_offset, 317)
        old = shadow.fog_offset
        shadow.advance(1, environment=False)
        self.assertEqual(shadow.fog_offset, old)

    def test_foreground_positions_and_physics_are_independent_of_motion_setting(self):
        games = [Game(self.data), Game(self.data)]
        games[1].effects.motion_enabled = False
        for game in games:
            game.handle_events([InputEvent("key_down", "d"), InputEvent("key_down", "shift_left")])
            for _ in range(180):
                game.step(1 / 60)
                game.effects.advance(1 / 60)
        states = [(g.player.x, g.player.y, g.player.vy, g.camera.x, g.completed) for g in games]
        self.assertEqual(*states)
        records = [Recorder(), Recorder()]
        for game, record in zip(games, records):
            game.draw(record)
        geometry = [[(s.image, s.source, rect) for s, rect in r.sprites
                     if s.visual_role in ("terrain", "lamp", "prop", "none")] for r in records]
        self.assertEqual(*geometry)

    def test_rejected_switch_and_restart_do_not_leave_success_effects(self):
        g = Game(self.data)
        p = g.player
        p.x, p.y, p.grounded = 160, 190, False
        g.handle_events([InputEvent("key_down", "shift_left")])
        g.step(1 / 60)
        self.assertEqual(g.effects.world, "real")
        self.assertEqual(g.effects.notice, 0)
        g.effects.motion_enabled = False
        g.effects.switch("shadow")
        g.restart()
        self.assertFalse(g.effects.motion_enabled)
        self.assertEqual((g.effects.world, g.effects.shadow, g.effects.notice, g.effects.fog_offset), ("real", 0, 0, 0))

    def test_lamp_palette_preserves_pole_and_transparency(self):
        self.assertEqual(shadow_lamp_pixel((255, 240, 137, 255)), (151, 187, 255, 255))
        self.assertEqual(shadow_lamp_pixel((255, 255, 255, 100)), (220, 231, 255, 100))
        for rgba in ((23, 21, 22, 255), (0, 0, 0, 0)):
            self.assertEqual(shadow_lamp_pixel(rgba), rgba)

    def test_sky_wave_covers_both_viewport_edges(self):
        fx, camera, r = WorldEffects("shadow"), Camera(320, 240), Recorder()
        for x in (0, 320 - 800 / 3):
            camera.set_position(x, 40)
            r.sprites.clear()
            MapScene(self.data, "shadow", fx).draw(r, camera)
            sky = [(s, rect) for s, rect in r.sprites if s.image.name == "Outer_City_Sky_BG.png"]
            for y in range(600):
                intervals = sorted((rect[0], rect[0] + rect[2]) for s, rect in sky if rect[1] <= y < rect[1] + rect[3])
                edge = 0
                for left, right in intervals:
                    if left <= edge:
                        edge = max(edge, right)
                self.assertGreaterEqual(edge, 800)

    def test_f3_input_changes_motion_without_a_text_indicator(self):
        g, r = Game(self.data), Recorder()
        g.handle_events([InputEvent("key_down", "f3")])
        g.draw(r)
        self.assertFalse(g.effects.motion_enabled)
        self.assertFalse(r.labels)
        g.handle_events([InputEvent("key_down", "f3")])
        self.assertFalse(g.effects.motion_enabled)
        g.handle_events([InputEvent("key_up", "f3"), InputEvent("key_down", "f3")])
        self.assertTrue(g.effects.motion_enabled)

    def test_focus_pause_does_not_advance_visual_time(self):
        g = Game(self.data)
        g.effects.switch("shadow")
        g.effects.advance(0.05)
        backend = FakeBackend([InputEvent("focus_lost")])
        before = (g.effects.age, g.effects.notice, g.effects.clock, g.effects.fog_offset)
        g.run(backend, max_frames=2)
        self.assertEqual(before, (g.effects.age, g.effects.notice, g.effects.clock, g.effects.fog_offset))
        self.assertTrue(backend.closed)

    def test_old_frame_stall_does_not_skip_new_transition_first_frame(self):
        g = Game(self.data)
        backend = FakeBackend([InputEvent("key_down", "shift_left")])
        with patch("game.app.perf_counter", side_effect=[0.0, 0.5]):
            g.run(backend, max_frames=1)
        self.assertEqual(g.scene.world, "shadow")
        self.assertEqual(g.effects.age, 0)
        self.assertEqual(g.effects.notice, 0.5)
