"""Primitive art for the lantern room, drawn at integer scale."""

from math import isqrt

from game.camera import Camera


class LanternView:
    def __init__(self, room, width, height):
        self.room = room
        self.camera = Camera(room.data.width, room.data.height, width, height, scale=3)

    def draw(self, backend):
        room = self.room

        def rect(x, y, w, h, color, filled=True):
            backend.rectangle(self.camera.screen_rect(x, y, w, h), color, filled)

        backend.begin(room.data.background)
        for i in range(11):
            x = 10 + 25 * i
            top = 25 + (i * 37) % 67
            rect(x, top, 9, 174 - top, (23, 24, 36))
            rect(x + 8, top + 17, 13, 3, (23, 24, 36))
        rect(0, 174, room.data.width, 26, (10, 10, 16))
        if room.socket:
            lx, ly = room.socket.x, room.socket.y - 10
            for radius, color in ((room.RADIUS, (30, 27, 36)), (63, (44, 35, 39)), (31, (59, 44, 43))):
                for dy in range(-radius, radius, 3):
                    span = isqrt(radius * radius - dy * dy)
                    rect(lx - span, ly + dy, 2 * span, 3, color)

        for ground in room.ground:
            rect(ground.x, ground.y, ground.width, ground.height, (45, 43, 55))
            rect(ground.x, ground.y, ground.width, 2, (136, 122, 121))
            for x in range(int(ground.x) + 8, int(ground.x + ground.width), 16):
                rect(x, ground.y + 4, 1, ground.height - 4, (26, 25, 36))
        for p in room.platforms:
            lit = room.lit(p)
            rect(p.x, p.y, p.width, p.height, (163, 115, 72) if lit else (86, 78, 94), lit)
            rect(p.x + p.width / 2 - 1, p.y, 2, 2, (255, 218, 143) if lit else (117, 104, 123))

        door = room.exit
        rect(door.x, door.y, door.width, door.height, (177, 142, 98) if room.complete else (122, 107, 118), room.complete)
        rect(door.x + 3, door.y + 5, door.width - 6, door.height - 5, (42, 39, 48))
        rect(door.x + 9, door.y + 14, 1, 2, (255, 218, 143))
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
