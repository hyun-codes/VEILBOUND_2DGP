import unittest

from game.app import STAGE_5
from game.lantern_room import LanternRoom
from game.map_loader import load_map


class BeaconVaultTest(unittest.TestCase):
    def setUp(self):
        self.room = LanternRoom(load_map(STAGE_5))

    def act(self, frames=1, direction=0, *, jump=False, interact=False):
        for i in range(frames):
            self.room.step(1 / 60, direction, jump and i == 0, interact and i == 0)

    def go(self, x, *, jump=False):
        direction = 1 if x > self.room.x else -1
        for tick in range(160):
            if self.room.complete or (abs(x - self.room.x) < 1.19 and (tick or not jump)):
                return
            self.act(direction=direction, jump=jump and tick == 0)
        self.fail(f"Could not reach x={x} from {(self.room.x, self.room.y)}")

    def jump_to(self, x, y):
        self.go(x, jump=True)
        self.act(35)
        self.assertEqual(self.room.y, y)

    def enter_cistern(self, lamp_x):
        self.go(lamp_x)
        self.act(interact=True)
        self.assertIsNotNone(self.room.loose_lantern)
        self.assertFalse(self.room.collision().supported(172, 142, self.room.WIDTH))
        self.go(179)
        self.act(35)
        self.assertEqual(self.room.y, 178)

    def light_east(self):
        self.enter_cistern(112)
        self.act(interact=True)
        self.go(194)
        self.jump_to(204, 160)
        self.act(interact=True)
        self.go(207)
        self.jump_to(220, 143)
        self.act(interact=True)

    def test_solves_the_room_with_both_branches(self):
        self.go(104)
        self.act(interact=True)
        self.assertTrue(self.room.collision().overlaps(86, 146, self.room.WIDTH, self.room.HEIGHT))
        self.go(137)
        self.act(interact=True)
        self.assertFalse(self.room.collision().overlaps(86, 146, self.room.WIDTH, self.room.HEIGHT))
        self.go(98)
        self.jump_to(67, 155)
        self.go(60)
        self.act(interact=True)
        self.go(56)
        self.jump_to(43, 135)
        self.act(interact=True)
        self.go(35)
        self.jump_to(22, 115)
        self.act(interact=True)
        self.assertEqual(len(self.room.lit_beacons), 3)
        self.assertFalse(self.room.exit_ready)

        self.go(67)
        self.act(35)
        self.go(70)
        self.jump_to(99, 146)
        self.go(137)
        self.act(interact=True)
        self.light_east()
        self.assertEqual(len(self.room.lit_beacons), 6)
        self.go(221)
        self.jump_to(235, 124)
        self.jump_to(253, 106)
        self.assertTrue(self.room.complete)

    def test_east_can_be_explored_first_and_reset_extinguishes_beacons(self):
        self.go(104)
        self.act(interact=True)
        self.light_east()
        self.assertFalse(self.room.exit_ready)
        self.go(215)
        self.jump_to(202, 124)
        self.jump_to(177, 110)
        self.go(147)
        self.act(35)
        self.assertEqual(self.room.y, 146)
        self.assertEqual(len(self.room.lit_beacons), 3)
        self.room.reset()
        self.assertFalse(self.room.lit_beacons)
        self.assertIs(self.room.socket, self.room.initial_socket)

    def test_east_hatch_allows_more_than_one_lantern_position(self):
        for lamp_x in (110, 119):
            with self.subTest(lamp_x=lamp_x):
                self.room.reset()
                self.go(104)
                self.act(interact=True)
                self.go(158)
                self.assertTrue(self.room.collision().supported(172, 142, self.room.WIDTH))
                self.enter_cistern(lamp_x)
