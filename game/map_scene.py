"""현재 세계 지형과 출구 안내. 시작점은 디버그 표시다."""

import math
from dataclasses import replace


class MapScene:
    def __init__(self, data, world="real", effects=None):
        if world not in ("real", "shadow"):
            raise ValueError("Map preview world must be real or shadow")
        self.data, self.world = data, world
        self.show_markers = True
        self.effects = effects

    def update(self, dt):
        pass

    def draw(self, renderer, camera):
        vx, vy, vw, vh = camera.view
        for sprite in self.data.sprites:
            if sprite.world not in ("common", self.world):
                continue
            if self.effects is not None and sprite.visual_role == "fog":
                sprite = replace(sprite, x=sprite.x + self.effects.fog_offset % sprite.width, repeat_x=True)
            # 배경 일렁임의 좌우 여유를 포함해 하늘 반복 이음새를 채운다.
            margin = 2 if sprite.visual_role == "background" and self.effects else 0
            cols = self._copies(sprite.x, sprite.width, vx - margin, vw + 2 * margin, sprite.repeat_x)
            rows = self._copies(sprite.y, sprite.height, vy, vh, sprite.repeat_y)
            for row in rows:
                y = sprite.y + row * sprite.height
                for col in cols:
                    x = sprite.x + col * sprite.width
                    if x + sprite.width <= vx - margin or x >= vx + vw + margin or y + sprite.height <= vy or y >= vy + vh:
                        continue
                    pieces = self.effects.pieces(sprite, x, y) if self.effects else (replace(sprite, x=x, y=y),)
                    for piece in pieces:
                        renderer.sprite(piece, camera.screen_rect(piece.x, piece.y, piece.width, piece.height))
        if self.show_markers:
            start = self.data.object_named("PlayerStart")
            sx, sy, _, _ = camera.screen_rect(start.x, start.y, 0, 0)
            renderer.rectangle((sx - 3, sy, 6, 6), (116, 223, 188), filled=True)
            renderer.label(sx - 20, sy + 12, "START", (116, 223, 188))
        end = self.data.object_named("Exit")
        rect = camera.screen_rect(end.x, end.y, end.width, end.height)
        active = self.world == "real"
        color = (116, 223, 188) if active else (150, 151, 170)
        renderer.rectangle(rect, color)  # 포털 에셋 도입 전의 임시 테두리. 그림자는 내부를 채우지 않는다.
        renderer.label(rect[0], rect[1] + rect[3] + 6, "EXIT" if active else "EXIT OFF", color)

    @staticmethod
    def _copies(origin, size, view_origin, view_size, repeat):
        if not repeat:
            return (0,)
        first = math.floor((view_origin - origin) / size)
        last = math.ceil((view_origin + view_size - origin) / size)
        return range(first, last)
