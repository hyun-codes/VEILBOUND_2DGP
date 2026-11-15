import unittest
from dataclasses import replace

from game.app import STAGE_1
from game.lantern_room import LanternRoom
from game.map_loader import MapObject, load_map


class LanternRoomTest(unittest.TestCase):
    def setUp(self):
        self.room = LanternRoom(load_map(STAGE_1))

    def move(self, frames, direction=0):
        for _ in range(frames):
            self.room.step(1 / 60, direction)

    def press(self, *, direction=0, **action):
        self.room.step(1 / 60, direction, **action)

    def lit_platforms(self):
        return [bool(tuple(self.room.exposed(p))) for p in self.room.platforms]

    def test_lantern_placement_and_lit_platform_route(self):
        room = self.room
        self.assertEqual(room.light, (48, 132, room.START_RADIUS))
        self.assertEqual(self.lit_platforms(), [False, False])
        self.move(20, 1)
        self.press(interact=True)
        self.assertIsNone(room.socket)
        self.move(45, 1)
        self.assertEqual(room.light, (room.x + 6, room.y - 7, room.CARRY_RADIUS))
        self.press(interact=True)
        self.assertEqual(room.light, (100, 132, room.RADIUS))
        self.assertEqual(self.lit_platforms(), [True, True])
        self.assertFalse(room.collision().supported(228, room.platforms[1].y, room.WIDTH))
        self.press(interact=True)
        self.move(30, 1)
        self.press(interact=True)
        self.assertTrue(room.collision().supported(228, room.platforms[1].y, room.WIDTH))

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
        self.move(61, 1)
        self.assertFalse(self.room.grounded)
        self.assertGreater(self.room.y, self.room.start.y)
        self.move(55)
        self.assertEqual((self.room.x, self.room.y), (self.room.start.x, self.room.start.y))
        self.assertIs(self.room.socket, self.room.initial_socket)

    def test_carried_light_makes_the_floor_under_the_player_solid(self):
        self.move(20, 1)
        self.press(interact=True)
        self.move(75, 1)
        self.assertGreater(self.room.x, 130)
        self.assertEqual(self.room.y, self.room.start.y)
        self.assertTrue(self.room.grounded)

    def test_walls_boxes_and_keys_need_light(self):
        data = self.room.data
        objects = (
            MapObject("Wall sample", "Wall", 125, 118, 4, 24, {}),
            MapObject("Box sample", "Box", 133, 134, 8, 8, {}),
            MapObject("Key sample", "Key", 113, 133, 4, 6, {}),
        )
        self.room = LanternRoom(replace(data, objects=data.objects + objects))
        wall, box, key = objects
        self.assertFalse(any(self.room.exposed(wall)))
        self.assertFalse(any(self.room.exposed(box)))
        self.assertFalse(any(self.room.exposed(key)))
        self.assertFalse(self.room.collision().overlaps(126, 141, 6, 13))
        self.assertFalse(self.room.collision().supported(136, 134, 6))
        self.move(20, 1)
        self.press(interact=True)
        self.move(75, 1)
        self.assertEqual(self.room.x, wall.x - self.room.WIDTH / 2)
        self.assertTrue(self.room.collision().supported(136, 134, 6))
        self.assertEqual(self.room.collected, {0})
