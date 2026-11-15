"""Lantern room sprites and the light overlay, drawn at integer scale."""

from math import isqrt
from pathlib import Path

from game.camera import Camera


ASSETS = Path(__file__).resolve().parents[1] / "assets"


class LanternView:
    def __init__(self, room, width, height):
        self.room = room
        self.camera = Camera(room.data.width, room.data.height, width, height, scale=3)

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
        if room.socket:
            lx, ly = room.socket.x, room.socket.y - 10
            for radius, alpha in ((room.RADIUS, 23), (63, 30), (31, 42)):
                for dy in range(-radius, radius, 3):
                    span = isqrt(radius * radius - dy * dy)
                    region = self.camera.screen_rect(lx - span, ly + dy, 2 * span, 3)
                    backend.overlay(region, (171, 107, 57, alpha))

        for ground in room.ground:
            ledge("tiles/stone_ledge.png", ground, 16)
        for p in room.platforms:
            lit = room.lit(p)
            if lit:
                ledge("tiles/lantern_ledge.png", p, 5)
            else:
                rect(p.x, p.y, p.width, p.height, (86, 78, 94), False)
            rect(p.x + p.width / 2 - 1, p.y, 2, 2, (255, 218, 143) if lit else (117, 104, 123))

        door = room.exit
        sprite("props/exit_door.png", (13 if room.complete else 0, 0, 13, 24),
               door.x, door.y, door.width, door.height)
        for socket in room.sockets:
            rect(socket.x - 4, socket.y - 3, 8, 3, (126, 100, 89))
            rect(socket.x - 2, socket.y - 5, 4, 2, (91, 68, 70))
        x, y = round(room.x), round(room.y)
        rect(x - 3, y - 13, 6, 5, (201, 184, 169))
        rect(x - 3, y - 8, 6, 6, (119, 108, 130))
        stride = int(room.walk_time * 12) % 2
        rect(x - 2 - stride, y - 3, 2, 3, (173, 157, 154))
        rect(x + 1, y - 3, 2, 3 - stride, (173, 157, 154))
        lx = room.socket.x if room.socket else room.x + 5
        ly = room.socket.y - 10 if room.socket else room.y - 7
        rect(lx - 2, ly - 3, 4, 6, (222, 149, 75))
        rect(lx - 1, ly - 2, 2, 4, (255, 230, 166))
        if target := room.interaction():
            sx, sy = target.x - 2, target.y - 22
            rect(sx - 2, sy - 2, 8, 9, (20, 19, 29))
            rect(sx, sy, 1, 5, (255, 221, 170))
            for offset in (0, 2, 4):
                rect(sx, sy + offset, 3, 1, (255, 221, 170))
