import unittest

from game.app import Game, STAGE_3, STAGE_4
from game.map_loader import load_map
from game.stage_manager import StageManager
import test_block_stages
from tools.solve_stage3 import DT


class CatEncounterTests(unittest.TestCase):
    def setUp(self):
        self.game = Game(load_map(STAGE_4))
        self.route = test_block_stages.BlockStageTests()

    def cross_bridge(self):
        self.route.travel(self.game, 55, 167)
        self.route.tap(self.game, "shift_left")
        self.route.travel(self.game, 130, 167)

    def wait_for_attack(self):
        self.route.travel(self.game, 166, 167)
        for _ in range(200):
            if self.game.encounter.clip == "attack":
                return
            self.game.step(DT)
        self.fail("The imp did not start a melee attack")

    def test_cat_idles_walks_and_real_contact_is_safe(self):
        g = self.game
        self.assertEqual(g.encounter.clip, "idle")
        self.route.hold(g, 45)
        self.assertEqual(g.encounter.clip, "walk")
        self.assertGreater(g.encounter.x, 178)
        self.cross_bridge()
        self.route.tap(g, "shift_left")
        self.route.hold(g, 155, "d")
        self.assertTrue(g.completed)
        self.assertEqual(g.respawns, 0)

    def test_melee_warns_hits_and_restarts_in_reality(self):
        g = self.game
        self.cross_bridge()
        self.wait_for_attack()
        self.route.hold(g, 12)
        self.assertFalse(g.dying)
        for _ in range(45):
            if g.dying:
                break
            g.step(DT)
        self.assertTrue(g.dying)
        self.assertEqual(g.player.animation, "hurt")
        hit_x = g.player.x
        self.route.hold(g, 12, "shift_left", "d", "space")
        self.assertEqual((g.player.animation, g.player.x, g.scene.world), ("death", hit_x, "shadow"))
        self.route.hold(g, 23)
        self.assertEqual((g.stage_number, g.scene.world, g.respawns), (4, "real", 1))
        self.assertEqual((g.player.x, g.encounter.x), (28, 178))

    def test_stepping_out_of_melee_range_during_warning_avoids_damage(self):
        g = self.game
        self.cross_bridge()
        self.wait_for_attack()
        direction = "a" if g.encounter.facing < 0 else "d"
        self.route.hold(g, 36, direction)
        self.assertFalse(g.dying)
        self.assertEqual(g.respawns, 0)

    def test_stage_3_portal_points_to_stage_4(self):
        next_map = StageManager({"Stage4": STAGE_4}).next_map(load_map(STAGE_3))
        self.assertEqual(next_map.properties["stageNumber"], 4)
