import unittest
from unittest.mock import Mock

from game.app import STAGE_2
from game.lantern_room import LanternRoom
from game.lantern_view import LanternView
from game.map_loader import load_map


class RailRoomTest(unittest.TestCase):
    def setUp(self):
        self.room = LanternRoom(load_map(STAGE_2))

    def act(self, frames, direction=0, *, jump=False, interact=False):
        for tick in range(frames):
            self.room.step(1 / 60, direction, jump and tick == 0, interact and tick == 0)

    def dock_lantern(self):
        self.act(13, 1)
        self.act(1, interact=True)
        self.act(32, 1)
        self.act(1, interact=True)
        self.assertEqual(self.room.socket.name, "Hatch observation")

    def test_spotlight_drops_player_to_key_and_lights_route_back(self):
        room = self.room
        self.dock_lantern()
        self.act(109)
        self.act(43, 1)
        self.assertEqual(room.y, 106)
        self.act(180)
        self.assertEqual(room.y, 158)
        self.act(15, 1)
        self.assertEqual(room.collected, {0})
        self.act(180)
        for _ in range(4):
            self.act(11, -1)
            self.act(18)
        self.act(20, -1, jump=True)
        self.act(15)
        self.assertEqual(room.y, 142)
        self.act(20, -1, jump=True)
        self.act(60)
        self.assertEqual(room.y, 136)
        self.act(16, -1, jump=True)
        self.act(18)
        self.act(8, -1)
        self.assertTrue(room.complete)

    def test_carried_lantern_keeps_the_cover_solid_across_the_span(self):
        self.act(13, 1)
        self.act(1, interact=True)
        self.act(220, 1)
        self.assertIsNone(self.room.socket)
        self.assertGreater(self.room.x, 250)
        self.assertEqual(self.room.y, 106)
        self.assertFalse(self.room.collected)
        self.assertFalse(self.room.complete)

    def test_observation_socket_stays_safe_for_one_full_cycle(self):
        self.dock_lantern()
        origin = self.room.x, self.room.y
        self.act(round(self.room.rail.period * 60) + 1)
        self.assertEqual((self.room.x, self.room.y), origin)
        self.assertTrue(self.room.grounded)

    def test_chain_animation_follows_carriage_motion_and_pause(self):
        view = LanternView(self.room, 800, 600)
        rail = self.room.rail

        def chain_frame(elapsed):
            self.room.elapsed = elapsed
            backend = Mock()
            view.draw(backend)
            source, = (call.args[1] for call in backend.image.call_args_list
                       if call.args[0].name == "hoist_chain.png")
            return source

        self.assertEqual(chain_frame(0), chain_frame(rail.pause / 2))
        first = chain_frame(rail.pause + 0.10)
        second = chain_frame(rail.pause + 0.20)
        self.assertNotEqual(first, second)
        self.assertEqual(second, chain_frame(rail.period - 0.20))
        self.assertEqual(first, chain_frame(rail.period - 0.10))
