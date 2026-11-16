import unittest

from game.app import STAGE_4
from game.lantern_room import LanternRoom
from game.map_loader import load_map


class CounterweightTest(unittest.TestCase):
    def setUp(self):
        self.room = LanternRoom(load_map(STAGE_4))

    def act(self, frames=1, direction=0, *, jump=False, interact=False):
        for i in range(frames):
            self.room.step(1 / 60, direction, jump and i == 0, interact and i == 0)

    def go(self, x, *, jump=False):
        direction = 1 if x > self.room.x else -1
        for tick in range(350):
            if self.room.complete or (abs(x - self.room.x) <= 1.2 and (tick or not jump)):
                return
            self.act(direction=direction, jump=jump and tick == 0)
        self.fail(f"Could not reach x={x} from {(self.room.x, self.room.y)}")

    def send_crate(self):
        self.go(36)
        self.act(interact=True)
        self.go(54)
        self.act(interact=True)
        self.go(68)
        self.act(interact=True)
        self.act(56, 1)
        self.act(44)
        self.assertAlmostEqual(self.room.crate.y + self.room.crate.height, 156)

    def descend_with_lamp(self):
        self.go(68)
        self.act(interact=True)
        self.go(117, jump=True)
        self.act(39)
        self.go(93)
        self.act(20)
        self.assertEqual(self.room.collected, {0})

    def push_lit_crate(self):
        self.go(103)
        self.go(114, jump=True)
        self.act(35)
        self.act(interact=True)
        self.assertEqual(self.room.loose_lantern.y, self.room.crate.y)
        lamp_x = self.room.loose_lantern.x
        crate_x = self.room.crate.x
        self.go(100)
        self.act(25)
        self.go(177)
        self.assertAlmostEqual(self.room.loose_lantern.x - lamp_x, self.room.crate.x - crate_x)
        self.assertGreater(self.room.crate.x, 175)

    def test_drops_crate_loads_lantern_and_uses_crate_to_finish(self):
        self.send_crate()
        self.descend_with_lamp()
        self.push_lit_crate()
        self.go(188, jump=True)
        self.act(35)
        self.assertEqual(self.room.y, self.room.crate.y)
        self.go(212, jump=True)
        self.act(35)
        self.assertEqual(self.room.y, 116)
        self.go(229)
        self.assertTrue(self.room.complete)

    def test_holding_lantern_does_not_push_and_floor_jump_cannot_reach_exit(self):
        self.go(36)
        self.act(interact=True)
        self.act(90, 1)
        self.assertEqual(self.room.crate, self.room.crate_start)
        self.setUp()
        self.send_crate()
        self.descend_with_lamp()
        self.go(118, jump=True)
        self.act(38)
        self.go(180, jump=True)
        self.act(32)
        self.assertEqual(self.room.y, 156)
        self.go(195)
        self.act(jump=True)
        minimum_y = self.room.y
        for _ in range(36):
            self.act()
            minimum_y = min(minimum_y, self.room.y)
        self.assertGreater(minimum_y, 116)
        self.assertFalse(self.room.complete)
