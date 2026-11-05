"""월드 좌표는 좌상단 기준으로 유지하고 화면 표시만 변환한다."""

import math


class Camera:
    def __init__(self, world_width, world_height, width=800, height=600, scale=3):
        if min(world_width, world_height, width, height, scale) <= 0:
            raise ValueError("Camera dimensions and scale must be positive")
        if int(scale) != scale:
            raise ValueError("Pixel art requires an integer scale")
        self.world_width, self.world_height = world_width, world_height
        self.width, self.height, self.scale = width, height, int(scale)
        self.x = self.y = 0.0
        self.set_position(0, 0)

    def set_position(self, x, y):
        if not all(math.isfinite(v) for v in (x, y)):
            raise ValueError("Camera position must be finite")
        self.x = self._clamp(x, self.world_width, self.width / self.scale)
        self.y = self._clamp(y, self.world_height, self.height / self.scale)

    @staticmethod
    def _clamp(value, world_extent, visible_extent):
        if world_extent < visible_extent:
            return (world_extent - visible_extent) / 2
        return max(0.0, min(value, world_extent - visible_extent))

    def focus(self, x, y):
        self.set_position(x - self.width / self.scale / 2,
                          y - self.height / self.scale / 2)

    @property
    def view(self):
        return (self.x, self.y, self.width / self.scale, self.height / self.scale)

    def screen_rect(self, x, y, width, height):
        """pico2d용 좌하단 사각형. 공유 모서리는 같은 화면 픽셀로 반올림한다."""
        left = round(x * self.scale) - round(self.x * self.scale)
        top = round(y * self.scale) - round(self.y * self.scale)
        right = round((x + width) * self.scale) - round(self.x * self.scale)
        bottom = round((y + height) * self.scale) - round(self.y * self.scale)
        return left, self.height - bottom, right - left, bottom - top
