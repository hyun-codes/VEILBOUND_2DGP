import unittest

from game.app import STAGE_1
from game.lantern_room import LanternRoom
from game.map_loader import load_map


class LanternRoomTest(unittest.TestCase):
    def setUp(self):
        self.room = LanternRoom(load_map(STAGE_1))

    def move(self, frames, direction=0):
        for _ in range(frames):
            self.room.step(1 / 60, direction)

    def press(self, *, direction=0, **action):
        self.room.step(1 / 60, direction, **action)

    def test_lantern_placement_and_lit_platform_route(self):
        room = self.room
        self.assertEqual(room.light, (48, 132, room.START_RADIUS))
        self.assertEqual([room.lit(p) for p in room.platforms], [False, False])
        self.move(20, 1)
        self.press(interact=True)
        self.assertIsNone(room.socket)
        self.move(45, 1)
        self.assertEqual(room.light, (room.x + 6, room.y - 7, room.CARRY_RADIUS))
        self.press(interact=True)
        self.assertEqual(room.light, (100, 132, room.RADIUS))
        self.assertEqual([room.lit(p) for p in room.platforms], [True, False])
        self.press(interact=True)
        self.move(30, 1)
        self.press(interact=True)
        self.assertEqual([room.lit(p) for p in room.platforms], [True, True])

        self.press(direction=1, jump=True)
        self.move(22, 1)
        self.move(22)
        self.assertEqual(room.y, room.platforms[0].y)
        self.move(12, 1)
        self.press(direction=1, jump=True)
        self.move(23, 1)
        self.move(22)
        self.assertEqual(room.y, room.platforms[1].y)
        self.move(24, 1)
        self.assertTrue(room.complete)

    def test_dark_platform_does_not_support_player_and_fall_resets_lantern(self):
        self.move(20, 1)
        self.press(interact=True)
        self.move(75, 1)
        self.press(direction=1, jump=True)
        self.move(22, 1)
        self.move(75)
        self.assertEqual((self.room.x, self.room.y), (self.room.start.x, self.room.start.y))
        self.assertIs(self.room.socket, self.room.initial_socket)
        self.assertFalse(self.room.complete)
