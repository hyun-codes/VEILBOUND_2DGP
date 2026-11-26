import unittest

from game.app import STAGES, walk_into_room
from game.lantern_room import LanternRoom
from game.lantern_view import LanternView
from game.map_loader import load_map


ROUTES = {
    1: "70 j110 w30 134 j166 w30 225",
    2: ("81 119 137 w35 158 e 134 j113 w40 124 j145 w40 171 e "
        "134 w40 162 e 174 j199 w40 198 j221 w40 273"),
    3: "75 j113 w45 120 j145 w45 157 181 w45 196 j225 w45 234 j264 w45 305",
    4: "102 j133 w45 147 j178 w45 202 j238 w45 246 j275 w45 305",
    5: "172 e 186 w30 207 w40 247 w45 295 e 254 e 309 j337 w42 j363 w42 365 j387 w45 433",
    6: ("111 j142 w40 146 j172 w40 173 e j197 w35 e 173 w35 e 212 w55 "
        "264 e 282 284 j310 w40 312 j344 w40 385"),
    7: ("83 j108 w35 133 151 w45 163 e 174 e w50 282 e 162 e 292 j313 w40 304 j273 "
        "w40 277 j302 w40 305 j278 w40 267 e 289 j325 w40 348 w40 365 j395 w40 449"),
    8: ("110 j141 w40 148 j179 w40 201 j237 w40 216 w40 225 w40 e 229 e w45 272 j290 "
        "w50 e 227 e w45 204 j187 w40 j211 w40 j237 w40 e 216 w40 228 w40 223 e "
        "290 j316 w40 j345 w40 j377 w40 390 j423 w40 465"),
    9: ("110 133 w40 158 w40 213 270 319 j340 w35 341 j365 w35 358 j334 w35 329 e w40 e w40 "
        "313 j293 w40 e 313 w55 304 w50 337 213 e 195 e w45 199 j171 w45 163 174 e 199 w45 "
        "313 e 214 e 319 j340 w35 341 j365 w35 358 j334 w35 329 e w40 365 w45 386 409 w35 "
        "419 j452 w40 497"),
    10: "106 121 w40 139 w35 166 e 137 j118 w40 126 j146 w40 215 337 w60",
}


class StoryCampaignTest(unittest.TestCase):
    def replay(self, room, route):
        if room.exit.properties.get("carry"):
            route += f" {room.exit.x - room.start.x + 1:g}"
        for command in route.split():
            if room.complete:
                return
            if command == "e":
                room.step(1 / 60, 0, interact=True)
            elif command.startswith("w"):
                for _ in range(int(command[1:])):
                    room.step(1 / 60, 0)
            else:
                jump = command.startswith("j")
                x = room.start.x + int(command.lstrip("j"))
                direction = 1 if x > room.x else -1
                for tick in range(230):
                    if room.complete or (abs(room.x - x) <= 0.9 and (tick or not jump)):
                        break
                    room.step(1 / 60, direction, jump=jump and tick == 0)
                    self.assertIsNone(room.death_elapsed, command)
                else:
                    self.fail(f"{command}: stopped at {room.x - room.start.x:.1f}, {room.y:.1f}")
            self.assertIsNone(room.death_elapsed, command)
        self.assertTrue(room.complete)

    def test_story_is_solvable_using_game_inputs_at_all_ten_stage_entries(self):
        for stage, route in ROUTES.items():
            with self.subTest(stage=stage):
                room = LanternRoom(load_map(STAGES[stage]))
                self.replay(room, "e " + route)
                if stage == 4:
                    self.assertEqual(room.sibling_y, room.sibling.properties["fallY"])
                if stage == 10:
                    self.assertEqual(room.sibling_x, room.sibling.properties["destination"])
                    self.assertIs(room.socket, room.exit_socket)

    def test_all_ten_rooms_can_be_completed_in_one_run(self):
        room = LanternRoom(load_map(STAGES[1]))
        for stage, route in ROUTES.items():
            with self.subTest(stage=stage):
                self.replay(room, ("e " if stage == 1 else "") + route)
                if stage < 10:
                    upcoming = LanternRoom(load_map(STAGES[stage + 1]))
                    room = walk_into_room(LanternView(room, 800, 600), upcoming).room

    def test_late_rooms_have_mandatory_interaction_even_if_the_player_enters_with_the_orb(self):
        for stage in range(6, 11):
            with self.subTest(stage=stage):
                room = LanternRoom(load_map(STAGES[stage]))
                room.socket = None
                room.x, room.y = room.exit.x - 5, room.exit.y + room.exit.height
                for tick in range(120):
                    room.step(1 / 60, 1, jump=tick % 31 == 0)
                self.assertFalse(room.complete)

    def test_ten_rooms_share_the_lit_threshold(self):
        self.assertEqual(tuple(STAGES), tuple(range(1, 11)))
        rooms = [LanternRoom(load_map(path)) for path in STAGES.values()]
        for old, new in zip(rooms, rooms[1:]):
            with self.subTest(room=old.data.path.parent.name):
                old_view = LanternView(old, 800, 600)
                old.x, old.y = old.exit.x + 0.5, old.exit.y + old.exit.height
                old_view.camera.focus(old.x, old.y)
                old.walk_time = 0.25
                old.socket = None
                incoming = walk_into_room(old_view, new)
                self.assertEqual(incoming.camera.screen_rect(new.x, new.y, 1, 1),
                                 old_view.camera.screen_rect(old.x, old.y, 1, 1))
                self.assertEqual(new.walk_time, old.walk_time)
                self.assertTrue(new.carrying_lantern)
                self.assertTrue(new.collision().supported(new.x, new.y, new.WIDTH))

    def test_jump_over_a_threshold_preserves_motion(self):
        old = LanternRoom(load_map(STAGES[1]))
        new = LanternRoom(load_map(STAGES[2]))
        old.x = old.exit.x - 4
        old.socket = None
        view = LanternView(old, 800, 600)
        for tick in range(12):
            old.step(1 / 60, 1, jump=tick == 0)
            if old.complete:
                break
        self.assertTrue(old.complete)
        self.assertFalse(old.grounded)
        walk_into_room(view, new)
        self.assertEqual(new.y, old.y)
        self.assertEqual(new.vy, old.vy)
        self.assertEqual(new.grounded, old.grounded)
