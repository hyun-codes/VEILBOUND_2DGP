import unittest

from game.app import STAGE_6
from game.lantern_room import LanternRoom
from game.map_loader import load_map


class RelayGateTest(unittest.TestCase):
    def test_crosses_dark_wall_and_returns_to_power_exit(self):
        room = LanternRoom(load_map(STAGE_6))
        relay_switch, = room.switches

        def go(x, *, jump=False):
            direction = 1 if x > room.x else -1
            for tick in range(140):
                if room.complete or (abs(room.x - x) < 1.18 and (tick or not jump)):
                    return
                room.step(1 / 60, direction, jump and tick == 0)
            self.fail(f"Could not reach x={x} from {(room.x, room.y)}")

        def settle(*, interact=False):
            for tick in range(40):
                room.step(1 / 60, 0, interact=interact and tick == 0)

        def wall_blocks():
            return room.collision().overlaps(115, 140, room.WIDTH, room.HEIGHT)

        self.assertTrue(wall_blocks())
        go(36)
        settle(interact=True)
        self.assertFalse(wall_blocks())
        go(70)
        self.assertTrue(room.receiver_lit(room.switch_relays[relay_switch.name]))
        self.assertIsNone(room.interaction())
        settle(interact=True)
        self.assertFalse(room.exit_ready)
        go(101)
        go(128, jump=True)
        settle()
        go(170)
        settle(interact=True)
        settle(interact=True)
        self.assertFalse(room.exit_ready)
        go(128)
        go(101, jump=True)
        settle()
        go(70)
        self.assertEqual(room.interaction(), relay_switch)
        settle(interact=True)
        self.assertIsNone(room.interaction())
        self.assertTrue(room.exit_ready)
        go(101)
        go(128, jump=True)
        settle()
        go(191)
        go(206, jump=True)
        settle()
        self.assertEqual(room.y, 132)
        go(212)
        go(233, jump=True)
        settle()
        self.assertEqual(room.y, 114)
        go(242)
        self.assertTrue(room.complete)

        room.reset()
        self.assertTrue(wall_blocks())
        self.assertFalse(room.exit_ready)
