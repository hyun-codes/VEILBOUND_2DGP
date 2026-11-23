import unittest

from game.app import STAGE_6
from game.lantern_room import LanternRoom
from game.map_loader import load_map


class FloodedReservoirTest(unittest.TestCase):
    def setUp(self):
        self.room = LanternRoom(load_map(STAGE_6.with_name('stage6_flooded_reservoir.tmj')))
        self.west, self.east = self.room.floods

    def act(self, frames=1, direction=0, *, jump=False, interact=False):
        for i in range(frames):
            self.room.step(1 / 60, direction, jump and i == 0, interact and i == 0)

    def go(self, x, *, jump=False):
        direction = 1 if x > self.room.x else -1
        for tick in range(210):
            if self.room.complete or (abs(x - self.room.x) < 1.18 and (tick or not jump)):
                return
            self.act(direction=direction, jump=jump and tick == 0)
        self.fail(f"Could not reach x={x} from {(self.room.x, self.room.y)}")

    def use(self):
        self.act(46, interact=True)

    def reach_pump(self):
        self.go(40)
        self.use()
        self.act(70, direction=1)
        self.assertEqual((self.room.x, self.room.y), (103, 101))
        self.go(72)
        self.use()
        self.assertEqual(self.room.socket.name, "Pump cradle")
        self.go(119)
        self.act(40)
        self.assertEqual(self.room.y, 160)

    def test_full_route_switches_water_back_for_the_exit(self):
        self.reach_pump()
        self.go(151)
        self.use()
        self.assertEqual(self.room.water_depth(self.east), 0)
        self.go(130)
        self.use()
        self.go(219)
        self.assertEqual(self.room.collected, {1})
        self.go(130)
        self.use()
        self.go(109)
        self.use()
        self.assertEqual(self.room.water_depth(self.east), self.east.height)

        self.go(130)
        self.use()
        self.act(90, direction=-1)
        self.assertEqual((self.room.x, self.room.y), (58, 160))
        self.go(103)
        self.use()
        self.go(61)
        self.go(40, jump=True)
        self.act(40)
        self.go(32)
        self.assertEqual(self.room.collected, {0, 1})
        self.assertFalse(self.room.exit_ready)
        self.go(41)
        self.go(64, jump=True)
        self.act(40)
        self.go(103)
        self.use()
        self.go(130)
        self.use()
        self.go(151)
        self.use()

        self.go(130)
        self.use()
        self.go(216)
        self.go(233, jump=True)
        self.act(40)
        self.go(213, jump=True)
        self.act(40)
        self.go(218)
        self.go(244, jump=True)
        self.act(40)
        self.assertEqual(self.room.y, 103)
        self.assertFalse(self.room.exit_ready)
        self.go(253)
        self.use()
        self.go(241)
        self.assertTrue(self.room.complete)

    def test_valve_needs_docked_orb_and_flooding_resets_the_room(self):
        self.reach_pump()
        self.go(130)
        self.use()
        self.go(151)
        self.assertIsNone(self.room.interaction())
        self.act(24, direction=1)
        self.assertIsNotNone(self.room.death_elapsed)
        fallen_at = self.room.x, self.room.y
        radius = self.room.light[2]
        self.act(12, direction=-1, jump=True, interact=True)
        self.assertEqual((self.room.x, self.room.y), fallen_at)
        self.assertTrue(self.room.carrying_lantern)
        self.assertLess(self.room.light[2], radius)
        self.act(30)
        self.assertIs(self.room.socket, self.room.initial_socket)
        self.assertEqual(self.room.y, self.room.start.y)
        self.assertEqual(self.room.water_depth(self.east), self.east.height)

    def test_surface_moves_between_full_and_empty(self):
        self.reach_pump()
        self.go(151)
        self.act(interact=True)
        self.assertEqual(self.room.water_depth(self.east), self.east.height)
        self.act(19)
        self.assertGreater(self.room.water_depth(self.east), 0)
        self.assertLess(self.room.water_depth(self.east), self.east.height)
        self.act(30)
        self.assertEqual(self.room.water_depth(self.east), 0)
