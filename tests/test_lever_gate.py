import unittest
from dataclasses import replace

from game.app import Game, STAGE_1, STAGE_3_DRAFT as STAGE_3
from game.collision import CollisionWorld
from game.lever_gate import LeverGate, nearest_control
from game.map_loader import load_map, MapFormatError
from game.pico2d_backend import InputEvent


DT = 1 / 60


class LeverGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_map(STAGE_3)

    def game_at_lever(self, world="real"):
        g = Game(self.data, world)
        g.player.x, g.player.y, g.player.grounded = 344, 247, True
        return g

    def tap(self, g, key="e"):
        g.handle_events([InputEvent("key_down", key), InputEvent("key_up", key)])

    def finish(self, g):
        for _ in range(30):
            g.step(DT)

    def test_only_real_grounded_nearby_lever_works_without_toggling_a(self):
        for world, x, grounded in (("shadow", 344, True), ("real", 330, True), ("real", 344, False)):
            g = self.game_at_lever(world)
            g.player.x, g.player.grounded = x, grounded
            self.tap(g)
            g.step(DT)
            self.assertFalse(g.mechanism.activated)
        g = self.game_at_lever()
        self.assertEqual(g.interaction_target()[0], "lever")
        self.tap(g)
        g.step(DT)
        self.assertTrue(g.mechanism.activated)
        self.assertEqual(g.interaction_target(), (None, None))
        self.assertEqual((g.puzzle.mode, g.puzzle.light_mode), ("bridge", "near"))
        g.player.x = 360
        self.assertEqual(nearest_control(g.player, g.puzzle, g.mechanism)[0], "lamp")

    def test_lever_poses_gate_sprites_and_collision_move_in_the_same_step(self):
        g = self.game_at_lever()
        self.tap(g)
        for _ in range(6):
            g.step(DT)
        self.assertGreater(g.mechanism.progress, 0)
        self.assertFalse(g.mechanism.is_open)
        lever = next(s for s in g.data.sprites if s.object_name == "Service lever")
        self.assertEqual(lever.source, (64, 0, 64, 32))
        gate = next(s for s in g.data.solids if s.width == 24 and s.height == 40)
        bars = [s for s in g.data.sprites if s.object_name.startswith("Service gate bar ")]
        self.assertAlmostEqual(gate.y, min(s.y for s in bars))
        self.assertAlmostEqual(gate.y + gate.height, max(s.y + s.height for s in bars))
        self.finish(g)
        self.assertEqual(next(s for s in g.data.sprites if s.object_name == "Service lever").source, (128, 0, 64, 32))
        self.assertIs(g.player.collision, g.collision)
        self.assertIs(g.scene.data, g.data)

    def test_closed_gate_blocks_both_worlds_open_gate_clears_the_actual_corridor(self):
        mechanism = LeverGate(self.data)
        for world in ("real", "shadow"):
            closed = CollisionWorld(mechanism.compose(self.data, False).solids, world)
            opened = CollisionWorld(mechanism.compose(self.data, True).solids, world)
            self.assertEqual(closed.move(380, 167, 6, 14, 60, 0)[0], 389)
            self.assertEqual(opened.move(380, 167, 6, 14, 60, 0)[0], 440)
            self.assertTrue(closed.overlaps(400, 167, 6, 14))
            self.assertFalse(opened.overlaps(400, 167, 6, 14))

    def test_open_gate_latches_across_repeat_e_world_switch_and_lamp_layout_change(self):
        g = self.game_at_lever()
        g.handle_events([InputEvent("key_down", "e")])
        self.finish(g)
        for _ in range(3):
            g.handle_events([InputEvent("key_down", "e")])
            g.step(DT)
        self.assertTrue(g.mechanism.is_open)
        self.tap(g, "shift_left")
        g.step(DT)
        self.assertTrue(g.mechanism.is_open)
        self.tap(g, "shift_left")
        g.step(DT)
        g.handle_events([InputEvent("key_up", "e")])
        g.player.x = 360
        self.tap(g)
        g.step(DT)
        self.assertEqual(g.puzzle.mode, "stairs")
        self.assertTrue(g.mechanism.is_open)
        self.assertEqual(len([s for s in g.data.solids if s.width == 24 and s.height == 40]), 1)

    def test_restart_and_fall_reset_gate_and_lever_while_preserving_f3(self):
        g = self.game_at_lever()
        self.tap(g)
        self.finish(g)
        g.effects.motion_enabled = False
        g.player.y = self.data.height + 30
        g.step(DT)
        self.assertFalse(g.mechanism.activated)
        self.assertEqual(g.mechanism.progress, 0)
        self.assertEqual(g.respawns, 1)
        self.assertFalse(g.effects.motion_enabled)
        g.player.x, g.player.y, g.player.grounded = 344, 247, True
        self.tap(g)
        g.step(DT)
        self.tap(g, "r")
        self.assertFalse(g.mechanism.activated)
        self.assertEqual(next(s for s in g.data.sprites if s.object_name == "Service lever").source, (0, 0, 64, 32))

    def test_focus_loss_cancels_pending_lever_input(self):
        g = self.game_at_lever()
        self.tap(g)
        g.handle_events([InputEvent("focus_lost"), InputEvent("focus_gained")])
        g.step(DT)
        self.assertFalse(g.mechanism.activated)

    def test_missing_gate_target_or_visual_bars_fails_before_play(self):
        for name in ("ServiceGate", "ServiceLever"):
            with self.subTest(name=name), self.assertRaises(MapFormatError):
                LeverGate(replace(self.data, objects=tuple(o for o in self.data.objects if o.name != name)))
        with self.assertRaisesRegex(MapFormatError, "sprite"):
            LeverGate(replace(self.data, sprites=tuple(s for s in self.data.sprites if s.object_name != "Service gate bar 2")))

    def test_stage_without_lever_has_no_gate_or_extra_solids(self):
        data = load_map(STAGE_1)
        mechanism = LeverGate(data)
        self.assertFalse(mechanism.enabled)
        self.assertIs(mechanism.compose(data), data)
