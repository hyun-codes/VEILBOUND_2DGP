import unittest

from game.app import Game, STAGE_2, STAGE_3
from game.map_loader import load_map
from game.pico2d_backend import InputEvent
from game.player import Player
from game.stage_manager import StageManager
from tools.solve_stage3 import DT, Travel


class BlockStageTests(unittest.TestCase):
    def tap(self, game, key):
        game.handle_events([InputEvent("key_down", key), InputEvent("key_up", key)])
        game.step(DT)

    def travel(self, game, x, y, jump_x=None):
        path = Travel(x, y, game.player.x, jump_x)
        held = set()
        for _ in range(340):
            if path.done(game.player):
                game.handle_events([InputEvent("key_up", key) for key in held])
                return
            direction, jumping = path.input(game.player)
            desired = {"d"} if direction > 0 else {"a"} if direction < 0 else set()
            if jumping:
                desired.add("space")
            game.handle_events([InputEvent("key_up", key) for key in held - desired]
                               + [InputEvent("key_down", key) for key in desired - held])
            held = desired
            game.step(DT)
            self.assertEqual(game.respawns, 0)
        self.fail(f"Could not reach {(x, y)} from route: {(game.player.x, game.player.y)}")

    def hold(self, game, frames, *keys):
        game.handle_events([InputEvent("key_down", key) for key in keys])
        for _ in range(frames):
            game.step(DT)
        game.handle_events([InputEvent("key_up", key) for key in keys])

    def test_real_block_step_then_shadow_bridge_and_reality_exit(self):
        game = Game(load_map(STAGE_2), stages=StageManager({"Stage3": STAGE_3}))
        self.travel(game, 72, 175)
        self.assertEqual(game.interaction_target()[0], "block")
        self.tap(game, "e")
        self.hold(game, 12, "d")
        self.assertEqual(game.block.x, 80)
        self.hold(game, 80, "e", "d")
        self.assertEqual(game.player.animation, "push")
        self.assertGreater(game.block.x, 80)
        self.assertLess(game.block.x, 144)
        self.assertAlmostEqual(game.player.x + game.player.WIDTH / 2, game.block.x)
        stopped = game.block.x
        self.hold(game, 12, "d")
        self.assertEqual(game.block.x, stopped)
        self.hold(game, 200, "e", "d")
        self.assertAlmostEqual(game.block.x, 144)
        self.travel(game, 134, 175)
        self.travel(game, 154, 159, 134)
        self.travel(game, 180, 135, 159)
        self.tap(game, "shift_left")
        self.travel(game, 270, 135)
        self.tap(game, "shift_left")
        self.assertEqual(game.stage_number, 3)
        self.assertEqual(game.block.position, 0)

    def test_block_crossing_then_shadow_drop_through_hatch(self):
        game = Game(load_map(STAGE_3))
        self.travel(game, 64, 103)
        self.tap(game, "e")
        self.travel(game, 96, 103)
        self.travel(game, 138, 87, 101)
        self.travel(game, 194, 103, 148)
        self.travel(game, 246, 103)
        self.tap(game, "shift_left")
        self.travel(game, 246, 199)
        self.travel(game, 294, 199)
        self.assertFalse(game.completed)
        self.tap(game, "shift_left")
        self.assertTrue(game.completed)

    def test_block_is_solid_only_in_reality_and_resets(self):
        game = Game(load_map(STAGE_2))
        self.travel(game, 72, 175)
        self.tap(game, "shift_left")
        self.hold(game, 20, "e", "d")
        self.assertEqual(game.block.position, 0)
        self.assertFalse(game.collision.supported(88, 159, game.player.WIDTH))
        self.travel(game, 72, 175)
        self.tap(game, "shift_left")
        self.hold(game, 200, "e", "d")
        self.assertTrue(game.collision.supported(152, 159, game.player.WIDTH))
        self.travel(game, 150, 159, 135)
        self.travel(game, 164, 175)
        self.hold(game, 30, "e", "a")
        self.assertLess(game.block.x, 144)
        self.assertEqual((game.player.animation, game.player.facing), ("push", -1))
        self.tap(game, "r")
        self.assertTrue(game.collision.supported(88, 159, game.player.WIDTH))

    def test_unmoved_block_cannot_reach_the_other_side_by_jumping(self):
        for map_path, start, far_bank in ((STAGE_2, (112, 175), (168, 135)),
                                          (STAGE_3, (92, 87), (168, 103))):
            game = Game(load_map(map_path))
            for jump_tick in range(90):
                player = Player(game.player.animations, game.collision, game.data.width, start)
                player.direction = 1
                for tick in range(160):
                    if tick == jump_tick:
                        player.request_jump()
                    player.update(DT)
                    if player.y <= far_bank[1]:
                        self.assertLess(player.x + player.WIDTH / 2, far_bank[0])
                    if player.y > game.data.height + player.HEIGHT:
                        break
