"""현재 세계 지형과 출구 안내. 시작점은 디버그 표시다."""

import math


class MapScene:
    def __init__(self, data, world="real"):
        if world not in ("real", "shadow"):
            raise ValueError("Map preview world must be real or shadow")
        self.data, self.world = data, world
        self.show_markers = True

    def update(self, dt):
        pass

    def draw(self, renderer, camera):
        vx, vy, vw, vh = camera.view
        for sprite in self.data.sprites:
            if sprite.world not in ("common", self.world):
                continue
            cols = self._copies(sprite.x, sprite.width, vx, vw, sprite.repeat_x)
            rows = self._copies(sprite.y, sprite.height, vy, vh, sprite.repeat_y)
            for row in rows:
                y = sprite.y + row * sprite.height
                for col in cols:
                    x = sprite.x + col * sprite.width
                    if x + sprite.width <= vx or x >= vx + vw or y + sprite.height <= vy or y >= vy + vh:
                        continue
                    renderer.sprite(sprite, camera.screen_rect(x, y, sprite.width, sprite.height))
        if self.show_markers:
            start = self.data.object_named("PlayerStart")
            sx, sy, _, _ = camera.screen_rect(start.x, start.y, 0, 0)
            renderer.rectangle((sx - 3, sy, 6, 6), (116, 223, 188), filled=True)
            renderer.label(sx - 20, sy + 12, "START", (116, 223, 188))
        end = self.data.object_named("Exit")
        rect = camera.screen_rect(end.x, end.y, end.width, end.height)
        renderer.rectangle(rect, (116, 223, 188))
        renderer.label(rect[0], rect[1] + rect[3] + 6, "EXIT", (116, 223, 188))

    @staticmethod
    def _copies(origin, size, view_origin, view_size, repeat):
        if not repeat:
            return (0,)
        first = math.floor((view_origin - origin) / size)
        last = math.ceil((view_origin + view_size - origin) / size)
        return range(first, last)
