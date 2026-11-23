import unittest
from dataclasses import replace

from game.app import STAGE_1
from game.lantern_room import LanternRoom
from game.map_loader import MapFormatError, MapObject, load_map


class PressurePlateTest(unittest.TestCase):
    def make_room(self, **properties):
        data = load_map(STAGE_1)
        y = data.object_named('PlayerStart').y
        plate = MapObject('Treadle', 'PressurePlate', 20, y, 18, 3,
                          {'projector': 'Linked lamp', **properties})
        objects = (
            plate, MapObject('Linked lamp', 'Projector', 29, y, 0, 0, {}),
            MapObject('Rest', 'Focus', 40, 70, 0, 0, {'projector': 'Linked lamp', 'radius': 28}),
            MapObject('Load', 'Focus', 180, 100, 0, 0, {'projector': 'Linked lamp', 'radius': 40}),
        )
        return LanternRoom(replace(data, objects=data.objects + objects))

    def test_player_and_crate_hold_beam_then_release_resets_it(self):
        room = self.make_room()
        self.assertIn('Treadle', room.pressed_plates)
        room.x = 60
        room.step(1 / 60, 0)
        self.assertNotIn('Treadle', room.pressed_plates)
        room.crate = MapObject('Test load', 'PushCrate', 22, room.start.y - 16, 16, 16, {})
        room.step(1 / 60, 0)
        self.assertIn('Treadle', room.pressed_plates)
        for _ in range(40):
            room.step(1 / 60, 0)
        self.assertEqual(room.projected_light('Linked lamp'), (180, 100, 40))
        room.crate = None
        room.step(1 / 60, 0)
        self.assertNotIn('Treadle', room.pressed_plates)
        room.reset()
        self.assertIn('Treadle', room.pressed_plates)

    def test_invalid_link_is_rejected(self):
        with self.assertRaises(MapFormatError):
            self.make_room(projector='Missing lamp')
