import unittest
from pathlib import Path

from game.map_loader import MapObject
from game.rotating_chamber import RotatingChamber
from game.lantern_room import LanternRoom
from game.map_loader import load_map

MAP = Path(__file__).resolve().parents[1] / 'maps/stage_09/stage9_clockwork_chamber.tmj'


class RotatingGeometryTest(unittest.TestCase):
    def test_quarter_turn_rectangles_and_four_turn_identity(self):
        pivot = MapObject('Axle', 'RoomPivot', 148, 100, 0, 0, {'size': 128})
        chamber = RotatingChamber(pivot)
        rect = MapObject('Shelf', 'RotatingPlatform', 88, 144, 44, 6, {})
        self.assertEqual(chamber.rectangle(rect), (88, 144, 44, 6))
        chamber.orientation = 1
        self.assertEqual(chamber.rectangle(rect), (98, 40, 6, 44))
        chamber.orientation = 4
        self.assertEqual(chamber.rectangle(rect), (88, 144, 44, 6))

    def test_rotation_commits_after_visible_animation_and_resets(self):
        chamber = RotatingChamber(MapObject('Axle', 'RoomPivot', 148, 100, 0, 0, {'size': 128}))
        chamber.begin(1)
        self.assertFalse(chamber.advance(0.3))
        self.assertEqual(chamber.orientation, 0)
        self.assertGreater(chamber.angle, 0)
        self.assertTrue(chamber.advance(0.5))
        self.assertEqual(chamber.orientation, 1)
        chamber.reset()
        self.assertEqual(chamber.orientation, 0)
        self.assertFalse(chamber.turning)


class RotatingRoomTest(unittest.TestCase):
    def setUp(self):
        self.room = LanternRoom(load_map(MAP))

    def act(self, frames=45, direction=0, *, jump=False, interact=False):
        for tick in range(frames):
            self.room.step(1/60, direction, jump and tick == 0, interact and tick == 0)
            self.assertIsNone(self.room.death_elapsed)

    def go(self, x, *, jump=False):
        direction = 1 if x > self.room.x else -1
        for tick in range(400):
            if self.room.complete or (abs(self.room.x-x) < 1.18 and (tick or not jump)):
                return
            self.act(1, direction, jump=jump and tick == 0)
        self.fail(f'Blocked at {self.room.x,self.room.y} trying to reach {x}')

    def climb_outside(self):
        self.go(44)
        self.go(24, jump=True)
        self.act()
        self.go(54, jump=True)
        self.act()
        self.go(77, jump=True)
        self.act()

    def turn(self, direction):
        self.act(1)
        self.act(1, direction)
        self.act(45, direction)

    def test_rotating_platforms_do_not_overlap_in_any_orientation(self):
        from itertools import combinations
        for orientation in range(4):
            self.room.chamber.orientation = orientation
            rectangles = [self.room.chamber.rectangle(p) for p in self.room.rotating_platforms]
            for a, b in combinations(rectangles, 2):
                overlap = (a[0] < b[0]+b[2] and a[0]+a[2] > b[0]
                           and a[1] < b[1]+b[3] and a[1]+a[3] > b[1])
                self.assertFalse(overlap, (orientation, a, b))

    def test_crank_freezes_player_one_turn_per_press_and_reset_restores_room(self):
        self.go(26)
        self.act(interact=True)
        position = self.room.x, self.room.y
        self.act(80, 1, jump=True)
        self.assertEqual(self.room.chamber.orientation, 1)
        self.assertEqual((self.room.x, self.room.y), position)
        self.turn(-1)
        self.assertEqual(self.room.chamber.orientation, 0)
        self.room.reset()
        self.assertFalse(self.room.rotation_control)
        self.assertEqual(self.room.chamber.orientation, 0)
        self.assertEqual(self.room.keys, self.room.key_starts)

    def test_loose_orb_rotates_with_room_and_four_turns_restore_geometry(self):
        from dataclasses import replace
        self.go(26)
        self.act(interact=True)
        self.room.loose_lantern = replace(self.room.initial_socket, x=160, y=132)
        self.room.socket = None
        original = self.room.terrain
        self.turn(1)
        self.assertEqual(self.room.light[:2], (120,112))
        self.assertEqual(self.room.lantern_vy, 0)
        self.assertNotEqual(self.room.terrain, original)
        for _ in range(3):
            self.turn(1)
        self.assertEqual(self.room.terrain, original)
        self.assertEqual(self.room.light[:2], (160,128))

    def test_orb_falls_again_after_releasing_crank_and_orientation_is_required(self):
        from dataclasses import replace
        self.go(26)
        self.act(interact=True)
        self.room.loose_lantern = replace(self.room.initial_socket, x=160, y=132)
        self.room.socket = None
        self.turn(1)
        self.act(interact=True)
        self.act(60)
        self.assertEqual(self.room.loose_lantern.y, 184)
        self.room.collected = set(range(len(self.room.keys)))
        self.room.socket = self.room.exit_socket
        self.room.loose_lantern = None
        self.room.chamber.orientation = 0
        self.assertFalse(self.room.exit_ready)
        self.room.chamber.orientation = 2
        self.assertFalse(self.room.exit_ready)
        self.room.chamber.orientation = 1
        self.assertTrue(self.room.exit_ready)

    def test_full_solution_rotates_room_both_directions_and_delivers_orb(self):
        self.go(48)
        self.act(interact=True)
        self.climb_outside()
        self.go(116, jump=True)
        self.act()
        self.go(136)
        self.act()
        self.go(160, jump=True)
        self.act()
        self.go(164)
        self.go(191, jump=True)
        self.act()
        self.go(196)
        self.go(212)
        self.act(10)
        self.go(198)
        self.act()
        self.assertEqual(self.room.collected, {1,2})
        self.go(170)
        self.act()
        self.go(103)
        self.go(76, jump=True)
        self.act()
        self.go(26)
        self.act(interact=True)
        self.turn(1)
        self.turn(1)
        self.act(interact=True)
        self.go(182)
        self.act(jump=True)
        self.act(40)
        self.assertEqual(self.room.collected, {0,1,2})
        self.assertFalse(self.room.exit_ready)
        self.go(103)
        self.go(76, jump=True)
        self.act()
        self.go(26)
        self.act(interact=True)
        self.turn(-1)
        self.act(interact=True)
        self.climb_outside()
        self.go(110, jump=True)
        self.act()
        self.go(118)
        self.go(129, jump=True)
        self.act()
        self.go(147, jump=True)
        self.act()
        self.go(165)
        self.act()
        self.go(190)
        self.go(205, jump=True)
        self.act()
        self.go(209)
        self.go(229, jump=True)
        self.act()
        self.go(251)
        self.assertFalse(self.room.complete)
        self.act(interact=True)
        self.go(241)
        self.assertTrue(self.room.complete)
