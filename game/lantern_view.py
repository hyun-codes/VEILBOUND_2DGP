"""Lantern room sprites and the light overlay, drawn at integer scale."""

from math import hypot
from pathlib import Path

from game.camera import Camera
from game.lantern_room import light_span


ASSETS = Path(__file__).resolve().parents[1] / "assets"
DARKNESS_MASK = ASSETS / "environments/stage_01/lantern_darkness.png"
MASK_SIZE = 221


def draw_darkness(backend, camera, x, y, radius):
    lit_area = camera.screen_rect(x - radius, y - radius, 2 * radius, 2 * radius)
    left, bottom, width, height = lit_area
    right, top = left + width, bottom + height
    screen_w, screen_h = camera.width, camera.height
    left, right = (max(0, min(screen_w, edge)) for edge in (left, right))
    bottom, top = (max(0, min(screen_h, edge)) for edge in (bottom, top))
    for bounds in ((0, 0, screen_w, bottom), (0, top, screen_w, screen_h - top),
                   (0, bottom, left, top - bottom), (right, bottom, screen_w - right, top - bottom)):
        if bounds[2] and bounds[3]:
            backend.overlay(bounds, (0, 0, 0, 255))
    backend.image(DARKNESS_MASK, (0, 0, MASK_SIZE, MASK_SIZE), lit_area)


def draw_combined_darkness(backend, camera, lights):
    for fraction, alpha in ((1, 255), (0.87, 117), (0.68, 62), (0.42, 26)):
        for row in range(camera.world_height):
            spans = sorted(span for light in lights if (span := light_span(light, row, fraction)))
            cursor = 0
            for left, right in spans + [(camera.world_width, camera.world_width)]:
                edge = min(camera.world_width, left)
                if edge > cursor:
                    backend.overlay(camera.screen_rect(cursor, row, edge - cursor, 1), (0, 0, 0, alpha))
                cursor = max(cursor, right)


class LanternView:
    def __init__(self, room, width, height):
        self.room = room
        self.camera = Camera(room.data.width, room.data.height, width, height, scale=3)
        self.rail_marks = []
        if room.rail:
            for (ax, ay), (bx, by) in zip(room.rail.points, room.rail.points[1:]):
                count = max(1, round(hypot(ax - bx, ay - by) / 4))
                self.rail_marks.extend((round(ax + (bx - ax) * i / count),
                                        round(ay + (by - ay) * i / count)) for i in range(count))

    def draw(self, backend):
        room = self.room

        def rect(x, y, w, h, color, filled=True):
            backend.rectangle(self.camera.screen_rect(x, y, w, h), color, filled)

        def sprite(path, source, x, y, width, height, flip=False):
            backend.image(ASSETS / path, source, self.camera.screen_rect(x, y, width, height), flip)

        def ledge(path, platform, tile_height):
            for offset in range(0, round(platform.width), 16):
                width = min(16, round(platform.width) - offset)
                sprite(path, (0, 0, width, tile_height), platform.x + offset, platform.y,
                       width, platform.height)

        backend.begin(room.data.background)
        sprite("environments/stage_01/pump_hall.png", (0, 0, 264, 200), 0, 0, room.data.width, room.data.height)
        for rx, ry in self.rail_marks:
            rect(rx, ry, 2, 1, (67, 59, 67))
        if room.rail:
            for rx, ry in room.rail.points:
                rect(rx - 1, ry - 1, 3, 3, (97, 84, 81), False)
        for ground in room.ground:
            ledge("tiles/stone_ledge.png", ground, 16)
        for p in room.platforms:
            ledge("tiles/lantern_ledge.png", p, 5)
        for part in room.data.sprites:
            backend.image(part.image, part.source,
                          self.camera.screen_rect(part.x, part.y, part.width, part.height))
        for prop in room.props:
            if prop.kind == "Wall":
                ledge("tiles/stone_ledge.png", prop, 16)
            else:
                rect(prop.x, prop.y, prop.width, prop.height, (121, 88, 61))
                rect(prop.x, prop.y, prop.width, prop.height, (196, 151, 102), False)
        for index, key in enumerate(room.keys):
            if index not in room.collected:
                rect(key.x, key.y, key.width - 2, 3, (228, 174, 97), False)
                rect(key.x + key.width - 3, key.y + 2, 1, key.height - 2, (228, 174, 97))
                rect(key.x + key.width - 2, key.y + key.height - 1, 2, 1, (228, 174, 97))

        door = room.exit
        sprite("props/exit_door.png", (13 if room.complete else 0, 0, 13, 24),
               door.x, door.y, door.width, door.height)
        for socket in room.sockets:
            sprite("props/lantern_socket.png", (0, 0, 10, 7), socket.x - 5, socket.y - 7, 10, 7)
        for projector, (target_x, target_y, _) in zip(room.projectors, room.projected_lights):
            x, y = projector.x, projector.y
            color = (196, 135, 89) if projector.x < room.start.x else (154, 182, 190)
            marks = max(2, round(hypot(target_x - x, target_y - y) / 7))
            for i in range(1, marks):
                t = i / marks
                rect(round(x + (target_x - x) * t), round(y - 12 + (target_y - y + 12) * t),
                     2, 1, color)
            rect(x - 4, y - 11, 8, 11, (88, 78, 88))
            active = room.aim_indices[projector.name]
            for index in range(len(room.aims[projector.name])):
                rect(x - 3 + index * 3, y - 9, 2, 3,
                     color if active == index else (48, 43, 58))
        for receiver in room.receivers:
            rect(receiver.x - 2, receiver.y - 2, 5, 5,
                 (246, 210, 144) if room.receiver_lit(receiver) else (76, 67, 78))

        lx, ly, radius = room.light
        if room.rail or room.projectors:
            draw_combined_darkness(backend, self.camera, room.lights)
        else:
            draw_darkness(backend, self.camera, lx, ly, radius)
        if room.rail:
            rx, ry, _ = room.lights[1]
            rect(rx - 4, ry - 3, 8, 5, (105, 91, 77))
            rect(rx - 2, ry - 2, 4, 3, (239, 199, 132))

        x, y = round(room.x), round(room.y)
        if not room.grounded:
            frame = 5 if room.vy < 0 else 6
        elif room.walk_time:
            frame = 1 + int(room.walk_time * 12) % 4
        else:
            frame = 0
        sprite("characters/player/lantern_keeper.png", (frame * 16, 0, 16, 18),
               x - 8, y - 16, 16, 18, flip=room.facing < 0)

        sprite("props/lantern.png", (0, 0, 7, 9), lx - 3, ly - 5, 7, 9)
        if target := room.interaction():
            sx, sy = target.x - 2, target.y - 22
            rect(sx - 2, sy - 2, 8, 9, (20, 19, 29))
            rect(sx, sy, 1, 5, (255, 221, 170))
            for offset in (0, 2, 4):
                rect(sx, sy + offset, 3, 1, (255, 221, 170))
