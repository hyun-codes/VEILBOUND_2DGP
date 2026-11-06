import unittest

from game.app import STAGE_1, PLAYER_ANIMATIONS
from game.camera import Camera
from game.collision import CollisionWorld, Solid
from game.map_loader import load_map
from game.player import AnimationSet, Player
from game.timing import FixedStepper


DT = 1 / 60


class MovementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_map(STAGE_1)
        cls.animations = AnimationSet(PLAYER_ANIMATIONS)
        cls.real = CollisionWorld(cls.data.solids)

    def player(self, start=(28, 183), collision=None):
        return Player(self.animations, collision or self.real, self.data.width, start)

    def test_solid_surfaces_match_pixels_and_decorations_are_excluded(self):
        self.assertEqual(len(self.data.solids), 264)
        self.assertEqual(min(s.y for s in self.data.solids), 183)
        self.assertEqual({s.y for s in self.data.solids if s.height == 1}, {183})
        self.assertTrue(self.real.supported(28, 183, 6))
        self.assertFalse(self.real.supported(160, 183, 6))
        shadow = CollisionWorld(self.data.solids, "shadow")
        self.assertTrue(shadow.supported(160, 183, 6))

    def test_swept_floor_wall_and_ceiling_do_not_tunnel(self):
        floor = CollisionWorld([Solid(0, 100, 200, 8)])
        self.assertEqual(floor.move(50, 50, 6, 14, 0, 150)[1:5], (100, False, True, False))
        wall = CollisionWorld([Solid(100, 0, 8, 200)])
        self.assertEqual(wall.move(50, 80, 6, 14, 150, 0)[:3], (97, 80, True))
        self.assertEqual(wall.move(150, 80, 6, 14, -150, 0)[:3], (111, 80, True))
        ceiling = CollisionWorld([Solid(0, 50, 200, 8)])
        self.assertEqual(ceiling.move(50, 100, 6, 14, 0, -150)[1:5], (72, False, False, True))

    def test_ground_is_stable_and_same_height_seams_do_not_block(self):
        p = self.player()
        for _ in range(600):
            p.update(DT)
        self.assertEqual((p.x, p.y, p.vy), (28, 183, 0))
        p.direction = 1
        for _ in range(60):
            p.update(DT)
            self.assertEqual(p.y, 183)
        self.assertAlmostEqual(p.x, 92)

    def test_jump_apex_landing_and_no_air_jump(self):
        p = self.player()
        p.request_jump()
        lowest_y = p.y
        for i in range(60):
            p.update(DT)
            lowest_y = min(lowest_y, p.y)
            if i == 2:
                before = p.vy
                p.request_jump()
                p.update(DT)
                self.assertGreater(p.vy, before)
        self.assertTrue(p.grounded)
        self.assertEqual(p.y, 183)

        self.assertAlmostEqual(183 - lowest_y, 27, delta=1)

    def test_tap_and_hold_height_and_faster_descent(self):
        results = []
        for release_tick in (0, 2, 6, None):
            p = self.player()
            p.request_jump()
            apex_y, apex_tick, landing_tick = p.y, 0, None
            for tick in range(90):
                if tick == release_tick:
                    p.release_jump()
                p.update(DT)
                if p.y < apex_y:
                    apex_y, apex_tick = p.y, tick + 1
                if p.grounded:
                    landing_tick = tick + 1
                    break
            self.assertIsNotNone(landing_tick)
            results.append((183 - apex_y, apex_tick, landing_tick))
        self.assertLess(results[0][0], results[1][0])
        self.assertLess(results[1][0], results[2][0])
        self.assertLess(results[2][0], results[3][0])
        height, apex_tick, landing_tick = results[-1]
        self.assertGreater(height, 26)
        self.assertLess(landing_tick - apex_tick, apex_tick)

    def test_repress_after_jump_cut_does_not_restore_upward_speed(self):
        p = self.player()
        p.request_jump()
        p.update(DT)
        p.release_jump()
        p.update(DT)
        cut_speed = p.vy
        p.request_jump()
        p.update(DT)
        self.assertGreater(p.vy, cut_speed)

    def test_jump_release_during_descent_does_not_change_fall(self):
        p = self.player()
        p.request_jump()
        while p.vy < 0 or p.grounded:
            p.update(DT)
        before = p.vy
        p.release_jump()
        p.update(DT)
        self.assertAlmostEqual(p.vy, min(p.MAX_FALL, before + p.FALL_GRAVITY * DT))

    def test_coyote_inside_and_outside_window(self):
        # 중심이 가장자리 밖으로 3px 이상 나가면 몸체의 지면 겹침도 끝난다.
        for delay, allowed in ((2, True), (7, False)):
            p = self.player((130.5, 183))
            p.direction = 1
            p.update(DT)
            self.assertFalse(p.grounded)
            for _ in range(delay):
                p.update(DT)
            p.request_jump()
            p.update(DT)
            self.assertEqual(p.vy < 0, allowed)

    def test_landing_buffer_is_once_and_expires(self):
        p = self.player((28, 180))
        p.vy = 60
        p.request_jump()
        for _ in range(4):
            p.update(DT)
        self.assertLess(p.vy, 0)
        self.assertEqual(p.jump_buffer, 0)
        for _ in range(90):
            p.update(DT)
        self.assertTrue(p.grounded)
        p = self.player((28, 100))
        p.request_jump()
        for _ in range(6):
            p.update(DT)
        self.assertEqual(p.jump_buffer, 0)  # 0.10초 뒤 부동소수점 잔여로 한 틱 늘어나지 않는다.
        for _ in range(90):
            p.update(DT)
        self.assertTrue(p.grounded)
        self.assertEqual(p.y, 183)

        p = self.player((28, 180))
        p.vy = 60
        p.request_jump()
        p.release_jump()  # 착지 전 놓은 입력도 버리지 않고 낮은 점프로 소비한다.
        for _ in range(4):
            p.update(DT)
        self.assertLess(p.vy, 0)
        self.assertGreaterEqual(p.vy, -p.RELEASE_SPEED)
        self.assertEqual(p.jump_buffer, 0)

    def test_map_bounds_and_opposite_input_never_resize_body(self):
        p = self.player()
        p.direction = -1
        for _ in range(90):
            p.update(DT)
        self.assertEqual(p.x, p.WIDTH / 2)
        self.assertEqual(p.facing, -1)
        p.direction = 0
        p.update(DT)
        self.assertEqual((p.x, p.WIDTH, p.HEIGHT), (3, 6, 14))

    def test_30_and_60_fps_produce_identical_movement_and_apex(self):
        logs = []
        for fps in (30, 60):
            p, clock, states = self.player(), FixedStepper(), []
            def step(dt):
                tick = len(states)
                p.direction = 1 if tick < 45 else -1
                if tick in (10, 55):
                    p.request_jump()
                if tick in (12, 64):
                    p.release_jump()
                p.update(dt)
                states.append((p.x, p.y, p.vy, p.grounded))
            for _ in range(fps * 2):
                clock.advance(1 / fps, step)
            logs.append(states)
        self.assertEqual(logs[0], logs[1])

    def test_real_gap_cannot_be_skipped_with_any_edge_jump_tick(self):
        # 모든 출발 틱을 바꿔 가장자리 겹침과 coyote time까지 포함한다.
        max_x_at_surface = 0
        for jump_tick in range(110):
            p = self.player((60, 183))
            p.direction = 1
            for tick in range(200):
                if tick == jump_tick:
                    p.request_jump()
                p.update(DT)
                if p.y <= 183:
                    max_x_at_surface = max(max_x_at_surface, p.x)
                self.assertFalse(p.grounded and p.x > 131)
                if p.y - p.HEIGHT > self.data.height:
                    break
        self.assertLess(max_x_at_surface + Player.WIDTH / 2, 192)

    def test_only_enabled_weapon_free_clips_and_stable_flip_anchor(self):
        self.assertEqual(set(self.animations.clips), set(AnimationSet.REQUIRED))
        self.assertEqual(self.animations.frame("run", 0), (0, 192, 64, 64))
        self.assertEqual(self.animations.frame("land", 10), (192, 384, 64, 64))
        p = self.player()
        class Recorder:
            def sprite(self, sprite, rect):
                self.item = sprite
        r, c = Recorder(), Camera(320, 240)
        for facing in (-1, 1):
            p.facing = facing
            p.draw(r, c)
            self.assertEqual((r.item.x + 32, r.item.y + 44), (p.x, p.y))
            self.assertEqual(r.item.flip_x, facing < 0)

    def test_camera_deadzone_jump_direction_change_and_bounds(self):
        c = Camera(320, 240)
        c.focus(28, 183)
        for _ in range(30):
            c.follow(100, 162, 1, DT)
        self.assertEqual((c.x, c.y), (0, 40))
        for _ in range(60):
            c.follow(280, 183, 1, DT)
        self.assertGreater(c.x, 0)
        self.assertLessEqual(c.x, 320 - 800 / 3)
        before = c.x
        c.follow(200, 183, -1, DT)
        self.assertLessEqual(abs(c.x - before), 2)
        c.focus(28, 183)
        self.assertEqual((c.x, c.y, c.look_ahead), (0, 40, 0))
