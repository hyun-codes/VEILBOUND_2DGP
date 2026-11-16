import unittest

from game.app import STAGE_4
from game.lantern_room import LanternRoom
from game.map_loader import load_map


class LanternChuteTest(unittest.TestCase):
    def setUp(self):
        self.room = LanternRoom(load_map(STAGE_4.with_name("stage4_lantern_chute.tmj")))

    def act(self, frames=1, direction=0, *, jump=False, interact=False):
        for i in range(frames):
            self.room.step(1 / 60, direction, jump and i == 0, interact and i == 0)

    def go(self, x, *, jump=False):
        direction = 1 if x > self.room.x else -1
        for tick in range(120):
            if self.room.complete or (abs(x - self.room.x) <= 1.2 and (tick or not jump)):
                return
            self.act(direction=direction, jump=jump and tick == 0)
        self.fail(f"Could not reach x={x} from {(self.room.x, self.room.y)}")

    def prepare_descent(self):
        self.go(101)
        self.act(interact=True)
        self.act(37)

    def take_lantern(self):
        self.go(122)
        self.act(interact=True)
        self.assertIsNone(self.room.socket)

    def send_lantern(self):
        self.go(148)
        self.act(interact=True)
        self.assertIsNotNone(self.room.in_transit)
        self.act(44)
        self.assertEqual(self.room.socket.name, "Lower cradle")

    def reach_key(self):
        self.go(198)
        self.act(38)
        self.assertEqual(self.room.y, 151)
        self.go(188)
        self.act(2)
        self.assertEqual(self.room.collected, {0})

    def light_return(self):
        self.go(168)
        self.act(interact=True)
        self.act(37)
        self.assertEqual(tuple(self.room.aim_indices.values()), (2,))

    def climb_to_exit(self):
        self.go(135)
        self.go(117, jump=True)
        self.act(33)
        self.go(109)
        self.go(95, jump=True)
        self.act(33)
        self.go(85)
        self.go(70, jump=True)
        self.act(33)
        self.go(64)
        self.go(44, jump=True)
        self.act(33)

    def test_routes_light_to_vault_then_back_to_exit(self):
        self.prepare_descent()
        self.take_lantern()
        self.send_lantern()
        self.reach_key()
        self.assertFalse(self.room.collision().supported(45, 106, self.room.WIDTH))
        self.go(148)
        self.assertTrue(self.room.socket_locked(self.room.socket))
        self.act(interact=True)
        self.assertEqual(self.room.socket.name, "Lower cradle")
        self.light_return()
        self.go(148)
        self.assertFalse(self.room.socket_locked(self.room.socket))
        self.act(interact=True)
        self.assertIsNone(self.room.socket)
        self.climb_to_exit()
        self.assertEqual(self.room.y, 106)
        self.assertFalse(self.room.complete)
        self.go(56)
        self.act(interact=True)
        self.assertIs(self.room.socket, self.room.exit_socket)
        self.go(46)
        self.assertTrue(self.room.complete)

    def test_unprepared_or_handheld_light_keeps_shutter_solid(self):
        self.take_lantern()
        self.send_lantern()
        self.act(60, 1)
        self.assertAlmostEqual(self.room.x, 179)
        self.assertEqual(self.room.y, 80)

        self.go(148)
        self.act(interact=True)
        self.assertIsNone(self.room.socket)
        self.prepare_descent()
        self.act(110, 1)
        self.assertAlmostEqual(self.room.x, 179)
        self.assertEqual(self.room.y, 80)
        self.act(40, 1, jump=True)
        self.assertAlmostEqual(self.room.x, 179)
        self.assertFalse(self.room.collected)

    def test_rapid_interaction_cannot_duplicate_the_travelling_lantern(self):
        self.take_lantern()
        self.go(148)
        self.act(interact=True)
        transit = self.room.in_transit
        self.act(16)
        self.act(interact=True)
        self.assertEqual(self.room.in_transit, transit)
        self.assertGreater(self.room.light[1], 70)
        self.assertLess(self.room.light[1], 141)
        self.act(30)
        self.assertEqual(self.room.socket.name, "Lower cradle")
        self.act(interact=True)
        self.assertIsNone(self.room.socket)
        self.assertIsNone(self.room.in_transit)
