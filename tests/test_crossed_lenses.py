import unittest
from itertools import product

from game.app import STAGE_3
from game.lantern_room import LanternRoom
from game.map_loader import load_map


class CrossedLensesTest(unittest.TestCase):
    def setUp(self):
        self.room = LanternRoom(load_map(STAGE_3))

    def act(self, frames=1, direction=0, *, jump=False, interact=False):
        for i in range(frames):
            self.room.step(1 / 60, direction, jump and i == 0, interact and i == 0)

    def go(self, x, *, jump=False):
        direction = 1 if x > self.room.x else -1
        for tick in range(110):
            if self.room.complete:
                return
            if abs(x - self.room.x) <= 1.2 and (tick or not jump):
                return
            self.act(direction=direction, jump=jump and tick == 0)
        self.fail(f"Could not reach x={x} from {(self.room.x, self.room.y)}")

    def west_key(self):
        self.go(149)
        self.act(interact=True)
        self.go(105)
        self.go(80, jump=True)
        self.act(30)
        self.go(65)
        self.go(49, jump=True)
        self.act(30)
        self.go(35)
        self.act(5)
        self.assertEqual(self.room.collected, {0})

    def east_key(self):
        self.go(58)
        self.go(80, jump=True)
        self.act(35)
        self.go(87)
        self.go(108, jump=True)
        self.act(35)
        self.act(interact=True)
        self.go(149)
        self.act(interact=True)
        self.act(interact=True)
        self.go(152)
        self.go(179, jump=True)
        self.act(32)
        self.go(199)
        self.go(223, jump=True)
        self.act(35)
        self.go(238)
        self.act(5)
        self.assertEqual(self.room.collected, {0, 1})

    def turn_to_exit(self):
        self.go(209)
        self.go(192, jump=True)
        self.act(25)
        self.go(173)
        self.go(147, jump=True)
        self.act(30)
        self.act(interact=True)
        self.act(interact=True)
        self.go(108)
        self.act(interact=True)
        self.act(37)

    def climb_to_exit(self):
        self.go(104)
        self.go(84, jump=True)
        self.act(32)
        self.go(65)
        self.go(52, jump=True)
        self.act(30)
        self.go(54)
        self.go(76, jump=True)
        self.act(30)
        self.go(80)
        self.go(100, jump=True)
        self.act(32)
        self.go(104)
        self.go(127, jump=True)
        self.act(33)
        self.go(140)

    def test_collects_two_keys_then_switches_both_projectors_to_exit(self):
        self.west_key()
        self.east_key()
        self.assertFalse(any(map(self.room.receiver_lit, self.room.receivers)))
        self.turn_to_exit()
        self.assertTrue(all(map(self.room.receiver_lit, self.room.receivers)))
        self.climb_to_exit()
        self.assertTrue(self.room.complete)

    def test_all_nine_combinations_require_reaiming_after_key_collection(self):
        room = self.room
        names = tuple(room.aim_indices)
        for positions in product(range(3), repeat=2):
            with self.subTest(positions=positions):
                room.aim_indices.update(zip(names, positions))
                reachable_keys = tuple(any(room.exposed(key)) for key in room.keys)
                opened_receivers = tuple(map(room.receiver_lit, room.receivers))
                if reachable_keys == (True, True):
                    self.assertFalse(room.collision().supported(78, 129, room.WIDTH))
                if opened_receivers == (True, True):
                    self.assertEqual(positions, (2, 2))
                    self.assertEqual(reachable_keys, (False, False))

    def test_light_and_collision_follow_turn_and_retarget_without_jumping(self):
        room = self.room
        self.go(149)
        name = room.projectors[1].name
        before = room.projected_light(name)
        self.act(interact=True)
        self.assertEqual(room.projected_light(name), before)
        self.assertTrue(room.collision().supported(182, 152, room.WIDTH))
        self.act(18)
        midpoint = room.projected_light(name)
        self.assertAlmostEqual(midpoint[0], (177 + 39) / 2)
        self.assertFalse(room.collision().supported(182, 152, room.WIDTH))
        self.act(interact=True)
        retargeted = room.projected_light(name)
        self.assertLess(abs(retargeted[0] - midpoint[0]), 6)
        self.act(37)
        self.assertEqual(room.projected_light(name), (136, 65, 43))
        room.reset()
        self.assertEqual(room.projected_light(name), before)
