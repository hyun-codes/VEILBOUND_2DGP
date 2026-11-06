import unittest
from dataclasses import replace

from game.app import Game, STAGE_1, STAGE_2
from game.map_loader import load_map, MapFormatError
from game.lamp_puzzle import LampPuzzle
from game.pico2d_backend import InputEvent
from game.stage_manager import StageManager
from game.timing import FixedStepper
from stage2_route import LampRoute


DT = 1 / 60


class LampPuzzleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_map(STAGE_2)

    def key(self, game, key, down=True):
        game.handle_events([InputEvent("key_down" if down else "key_up", key)])

    def tap(self, game, key):
        self.key(game, key)
        self.key(game, key, False)

    def test_map_and_current_layout_share_display_and_collision_tags(self):
        g = Game(self.data)
        self.assertEqual(g.stage_number, 2)
        self.assertEqual(g.puzzle.mode, "bridge")
        self.assertEqual(len(g.puzzle.controls), 2)
        self.assertTrue(all(s.lamp_state in ("", "bridge") for s in g.data.sprites))
        self.assertTrue(all(s.lamp_state in ("", "bridge") for s in g.collision.solids))
        self.assertFalse(any(s.lamp_state == "stairs" for s in g.data.solids))
        lamp = next(s for s in g.data.sprites if s.object_name == "Route lamp")
        self.assertEqual(lamp.x, 92)

    def test_e_needs_real_ground_and_nearby_control_and_ignores_hold(self):
        g = Game(self.data)
        self.tap(g, "e")
        g.step(DT)
        self.assertEqual(g.puzzle.mode, "bridge")  # 시작점에서 원격 조작할 수 없다.
        g.player.x, g.player.y, g.player.grounded = 80, 180, False
        self.tap(g, "e")
        g.step(DT)
        self.assertEqual(g.puzzle.mode, "bridge")  # 공중에서는 조작하지 않는다.
        g.player.x = 80
        g.player.y, g.player.grounded = 183, True
        self.key(g, "e")
        g.step(DT)
        self.assertEqual(g.puzzle.mode, "stairs")
        for _ in range(8):
            self.key(g, "e")
            g.step(DT)
        self.assertEqual(g.puzzle.mode, "stairs")
        lamp = next(s for s in g.data.sprites if s.object_name == "Route lamp")
        self.assertEqual(lamp.x, 68)
        self.assertIs(g.player.collision, g.collision)
        self.assertIs(g.scene.data, g.data)
        self.key(g, "e", False)
        self.tap(g, "shift_left")
        self.tap(g, "e")
        g.step(DT)
        self.assertEqual(g.scene.world, "shadow")
        self.assertEqual(g.puzzle.mode, "stairs")
        self.assertGreater(g.interaction_notice, 0)
        self.assertTrue(g.collision.supported(120, 167, 6))

    def test_focus_and_restart_clear_e_and_reset_lamp_without_losing_effect_setting(self):
        g = Game(self.data)
        g.player.x = 80
        self.tap(g, "e")
        g.handle_events([InputEvent("focus_lost"), InputEvent("focus_gained")])
        g.step(DT)
        self.assertEqual(g.puzzle.mode, "bridge")
        self.tap(g, "e")
        g.step(DT)
        self.assertEqual(g.puzzle.mode, "stairs")
        g.effects.motion_enabled = False
        g.restart()
        self.assertEqual((g.stage_number, g.player.x, g.player.y, g.puzzle.mode, g.scene.world), (2, 28, 183, "bridge", "real"))
        self.assertFalse(g.effects.motion_enabled)
        self.assertEqual(g.pending_interactions, 0)

    def test_upper_control_only_reached_after_ladder_route_and_full_clear(self):
        g, route = Game(self.data), LampRoute()
        for tick in range(600):
            for key, down in route.commands(g):
                self.key(g, key, down)
            g.step(DT)
            if route.phase == 13:
                break
        self.assertEqual(route.phase, 13, (route.phase, g.player.x, g.player.y))
        self.assertEqual(g.respawns, 0)
        self.assertTrue(g.completed)
        self.assertEqual(g.scene.world, "real")
        self.assertEqual(route.records, ["stairs", "land_4", "land_6", "land_8", "upper_bridge", "shadow_exit_off", "clear"])

    def test_real_only_and_fixed_bridge_cannot_reach_high_island(self):
        # 위층은 48px 높다. 현재 최대 점프는 27px 미만이며 세계 전환은 위쪽 속도를 늘리지 않는다.
        for world in ("real", "shadow"):
            g = Game(self.data, world)
            g.player.x = 95
            self.key(g, "d")
            self.key(g, "space")
            minimum_y = 183
            for _ in range(90):
                g.step(DT)
                minimum_y = min(minimum_y, g.player.y)
            self.assertGreater(minimum_y, 135)
            self.assertFalse(g.completed)
        self.assertEqual(183 - 135, 48)

    def test_fixed_stairs_cannot_jump_across_eighty_pixel_exit_gap(self):
        g = Game(self.data)
        g.player.x = 80
        self.tap(g, "e")
        g.step(DT)
        # 계단을 오른 뒤의 최선 조건에서도 80px 간격을 점프로 우회하지 못한다.
        for jump_tick in range(50):
            g = Game(self.data)
            g.player.x = 80
            self.tap(g, "e")
            g.step(DT)
            self.tap(g, "shift_left")
            g.step(DT)
            g.player.x, g.player.y = 176, 135
            g.player.grounded, g.player.coyote = True, 0.08
            self.key(g, "d")
            for tick in range(100):
                if tick == jump_tick:
                    self.key(g, "space")
                g.step(DT)
                self.assertFalse(g.player.grounded and g.player.x >= 272)
                self.assertFalse(g.completed)
                if g.respawns:
                    break

    def test_same_stage2_route_at_30_and_60_render_fps(self):
        results = []
        for fps in (30, 60):
            g, route, clock = Game(self.data), LampRoute(), FixedStepper()
            ticks = []
            def update(dt):
                for key, down in route.commands(g):
                    self.key(g, key, down)
                g.step(dt)
                ticks.append((g.player.x, g.player.y, g.puzzle.mode, g.scene.world, g.completed))
            for _ in range(fps * 7):
                clock.advance(1 / fps, update)
            self.assertTrue(g.completed)
            results.append(ticks)
        self.assertEqual(*results)

    def test_stage1_portal_enters_registered_stage2_and_r_retries_stage2(self):
        manager = StageManager({"Stage2": STAGE_2})
        g = Game(load_map(STAGE_1), stages=manager)
        g.effects.motion_enabled = False
        g.player.x = 290
        g.step(DT)
        self.assertEqual(g.stage_number, 2)
        self.assertEqual((g.player.x, g.player.y, g.puzzle.mode), (28, 183, "bridge"))
        self.assertFalse(g.completed)
        self.assertFalse(g.effects.motion_enabled)
        self.tap(g, "r")
        self.assertEqual(g.stage_number, 2)
        self.assertIsNone(manager.next_map(self.data))  # Stage 3를 추측해 로드하지 않는다.

    def test_incomplete_tiled_puzzle_does_not_silently_enable_both_layouts(self):
        objects = tuple(o for o in self.data.objects if o.kind != "LampControl")
        with self.assertRaisesRegex(MapFormatError, "LampControl"):
            LampPuzzle(replace(self.data, objects=objects))
        solids = tuple(replace(s, world="common") if s.lamp_state else s for s in self.data.solids)
        with self.assertRaisesRegex(MapFormatError, "shadow-only"):
            LampPuzzle(replace(self.data, solids=solids))
