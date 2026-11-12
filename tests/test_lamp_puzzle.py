import unittest
from dataclasses import replace

from game.app import Game, STAGE_1, STAGE_2
from game.map_loader import load_map, MapFormatError
from game.lamp_puzzle import LampPuzzle
from game.pico2d_backend import InputEvent
from game.stage_manager import StageManager
from game.timing import FixedStepper
from game.collision import CollisionWorld
from game.world_state import WorldState
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
        self.assertEqual(len(g.puzzle.controls), 4)
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
        self.assertEqual(route.records, ["stairs", "land_4", "land_6", "land_8", "upper_bridge", "light_far", "island_light_near", "shadow_exit_off", "clear"])

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
                self.assertFalse(g.player.grounded and g.player.x >= 296)
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
                ticks.append((g.player.x, g.player.y, g.puzzle.mode, g.puzzle.light_mode, g.scene.world, g.completed))
            for _ in range(fps * 11):
                clock.advance(1 / fps, update)
            self.assertTrue(g.completed)
            results.append(ticks)
        self.assertEqual(*results)

    def test_stage1_portal_enters_registered_stage2_and_r_retries_stage2(self):
        manager = StageManager({"Stage2": STAGE_2})
        g = Game(load_map(STAGE_1), stages=manager)
        g.effects.motion_enabled = False
        portal = g.data.object_named("Exit")
        g.player.x, g.player.y = portal.x + 2, portal.y + portal.height
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

    def test_both_lamp_combinations_remove_exactly_the_lit_bridge_section(self):
        puzzle = LampPuzzle(self.data)
        for mode in ("stairs", "bridge"):
            for light in ("near", "far"):
                puzzle.mode, puzzle.light_mode = mode, light
                data = puzzle.data
                shadow = CollisionWorld(data.solids, "shadow")
                self.assertEqual(shadow.supported(250, 135, 6), mode == "bridge" and light == "far")
                self.assertEqual(shadow.supported(360, 135, 6), mode == "bridge" and light == "near")
                self.assertEqual(shadow.supported(120, 167, 6), mode == "stairs")
                # 지워진 타일은 그림과 충돌 양쪽에 없어야 한다.
                beam = puzzle.beams[light]
                self.assertFalse(any(s.lamp_state == "bridge" and puzzle._inside(s, beam) for s in data.sprites))
                self.assertFalse(any(s.lamp_state == "bridge" and puzzle._inside(s, beam) for s in data.solids))
                for s in data.solids:
                    if s.lamp_state:
                        self.assertTrue(any(t.x == s.x and t.y <= s.y < t.y + t.height
                                            and t.lamp_state == s.lamp_state for t in data.sprites))
                for world in ("real", "shadow"):
                    collision = CollisionWorld(data.solids, world)
                    for x in (172, 204, 312, 432):
                        self.assertTrue(collision.supported(x, 135, 6))
                        self.assertFalse(collision.overlaps(x, 135, 6, 14))
                b = next(s for s in data.sprites if s.object_name == "Eraser lamp")
                self.assertEqual(b.x, 196 if light == "near" else 208)
                from game.world_effects import WorldEffects
                self.assertEqual(WorldEffects("shadow").style(b).palette, "original")

    def test_b_control_is_independent_real_grounded_and_not_repeated_while_held(self):
        g = Game(self.data)
        g.player.x, g.player.y, g.player.grounded = 204, 135, True
        self.key(g, "e")
        g.step(DT)
        self.assertEqual((g.puzzle.mode, g.puzzle.light_mode), ("bridge", "far"))
        self.assertIs(g.scene.data, g.data)
        self.assertIs(g.player.collision, g.collision)
        for _ in range(6):
            self.key(g, "e")
            g.step(DT)
        self.assertEqual(g.puzzle.light_mode, "far")
        self.key(g, "e", False)
        self.tap(g, "shift_left")
        self.tap(g, "e")
        g.step(DT)
        self.assertEqual(g.puzzle.light_mode, "far")
        self.assertTrue(g.collision.supported(250, 135, 6))
        g.player.x, g.player.y = 312, 135
        self.tap(g, "shift_left")
        g.step(DT)
        g.player.grounded = False
        self.tap(g, "e")
        g.step(DT)
        self.assertEqual(g.puzzle.light_mode, "far")
        self.tap(g, "e")
        g.step(DT)
        self.assertEqual(g.puzzle.light_mode, "near")
        self.assertEqual(g.player.y, 135)
        self.assertEqual(g.puzzle.mode, "bridge")

    def test_middle_island_allows_wrong_b_setting_to_be_reversed_without_restart(self):
        g = Game(self.data)
        g.player.x, g.player.y, g.player.grounded = 312, 135, True
        for _ in range(4):
            self.tap(g, "e")
            g.step(DT)
            self.assertTrue(g.player.grounded)
            self.tap(g, "shift_left")
            g.step(DT)
            self.assertTrue(g.player.grounded)
            self.tap(g, "shift_left")
            g.step(DT)
        self.assertEqual(g.respawns, 0)
        g.effects.motion_enabled = False
        self.tap(g, "e")
        g.step(DT)
        g.restart()
        self.assertEqual((g.puzzle.mode, g.puzzle.light_mode), ("bridge", "near"))
        self.assertFalse(g.effects.motion_enabled)

    def test_either_fixed_b_setting_leaves_an_unjumpable_gap(self):
        # 조작점과 무관한 물리 우회 검사: 가장자리 유예까지 포함해 시작 시점을 훑는다.
        for light, start, target in (("near", 200, 296), ("far", 312, 408)):
            for jump_tick in range(50):
                g = Game(self.data)
                g.puzzle.light_mode = light
                g.data = g.puzzle.data
                g.scene.data = g.data
                g.world_state = WorldState(g.data.solids, "shadow")
                g.scene.world = "shadow"
                g.player.collision = g.collision
                g.player.x, g.player.y = start, 135
                g.player.grounded, g.player.coyote = True, 0.08
                self.key(g, "d")
                for tick in range(110):
                    if tick == jump_tick:
                        self.key(g, "space")
                    g.step(DT)
                    self.assertFalse(g.player.grounded and g.player.x >= target)
                    self.assertFalse(g.completed)
                    if g.respawns:
                        break

    def test_invalid_eraser_metadata_is_rejected_before_rendering(self):
        for name in ("Beam_near", "Beam_far", "EraserRail"):
            with self.subTest(name=name), self.assertRaises(MapFormatError):
                LampPuzzle(replace(self.data, objects=tuple(o for o in self.data.objects if o.name != name)))
        with self.assertRaisesRegex(MapFormatError, "Eraser lamp"):
            LampPuzzle(replace(self.data, sprites=tuple(s for s in self.data.sprites if s.object_name != "Eraser lamp")))
        objects = tuple(replace(o, x=o.x + 1) if o.name == "Beam_near" else o for o in self.data.objects)
        with self.assertRaisesRegex(MapFormatError, "align"):
            LampPuzzle(replace(self.data, objects=objects))
        properties = dict(self.data.properties, lightInitialState="both")
        with self.assertRaisesRegex(MapFormatError, "lightInitialState"):
            LampPuzzle(replace(self.data, properties=properties))

    def test_light_visuals_remain_visible_without_motion_effects(self):
        from test_app import FakeBackend
        g = Game(self.data)
        g.effects.motion_enabled = False
        g.camera.set_position(160, 40)
        class Recorder(FakeBackend):
            def __init__(self):
                self.boxes = []
            def label(self, x, y, text, color=None):
                raise AssertionError(f"Unexpected gameplay text: {text}")
            def rectangle(self, rect, color, filled=False):
                self.boxes.append((rect, color))
        renderer = Recorder()
        g.draw(renderer)
        self.assertTrue(any(color == (243, 199, 107) for _, color in renderer.boxes))

    def test_pixel_prompt_is_drawn_over_a_usable_switch_only(self):
        from test_app import FakeBackend

        class Recorder(FakeBackend):
            def __init__(self):
                self.sprites = []

            def sprite(self, sprite, rect):
                self.sprites.append(sprite)

        g = Game(self.data)
        for world, x, grounded, paused, completed, shown in (
            ("real", 28, True, False, False, False),
            ("real", 80, True, False, False, True),
            ("real", 80, False, False, False, False),
            ("shadow", 80, True, False, False, False),
            ("real", 80, True, True, False, False),
            ("real", 80, True, False, True, False),
        ):
            with self.subTest(world=world, x=x, grounded=grounded, paused=paused, completed=completed):
                g.enter_map(self.data, world)
                g.player.x, g.player.grounded = x, grounded
                g.paused, g.completed = paused, completed
                renderer = Recorder()
                g.draw(renderer)
                prompts = [s for s in renderer.sprites if s.image.name == "interact_e.png"]
                self.assertEqual(len(prompts), int(shown))
                if shown:
                    switch = next(s for s in renderer.sprites if s.image.name == "lamp_switch.png")
                    self.assertLess(prompts[0].y + prompts[0].height, switch.y)
                    self.assertEqual(prompts[0].x + prompts[0].width / 2,
                                     switch.x + switch.width / 2)
