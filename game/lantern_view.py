"""Lantern room sprites and the light overlay, drawn at integer scale."""

from pathlib import Path

from game.camera import Camera


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
        for ground in room.ground:
            ledge("tiles/stone_ledge.png", ground, 16)
        for p in room.platforms:
            ledge("tiles/lantern_ledge.png", p, 5)
        for prop in room.props:
            if prop.kind == "Wall":
                ledge("tiles/stone_ledge.png", prop, 16)
            else:
                rect(prop.x, prop.y, prop.width, prop.height, (121, 88, 61))
                rect(prop.x, prop.y, prop.width, prop.height, (196, 151, 102), False)
        for index, key in enumerate(room.keys):
            if index not in room.collected:
                rect(key.x, key.y, key.width, key.height, (228, 174, 97), False)

        door = room.exit
        sprite("props/exit_door.png", (13 if room.complete else 0, 0, 13, 24),
               door.x, door.y, door.width, door.height)
        for socket in room.sockets:
            sprite("props/lantern_socket.png", (0, 0, 10, 7), socket.x - 5, socket.y - 7, 10, 7)

        lx, ly, radius = room.light
        draw_darkness(backend, self.camera, lx, ly, radius)

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
