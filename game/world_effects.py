"""배경 표시만 바꾸는 세계 연출. 물리·입력·카메라 좌표를 변경하지 않는다."""

from dataclasses import replace
import math


def shadow_lamp_pixel(rgba):
    """기존 램프의 밝은 두 색만 교체하고 기둥·알파는 보존한다."""
    r, g, b, a = rgba
    rgb = {(255, 240, 137): (151, 187, 255), (255, 255, 255): (220, 231, 255)}.get((r, g, b), (r, g, b))
    return (*rgb, a)


class WorldEffects:
    DURATION = 0.2

    def __init__(self, world="real"):
        self.motion_enabled = True
        self.reset(world)

    def reset(self, world="real"):
        self.world = world
        self.shadow = self.origin = float(world == "shadow")
        self.age = self.DURATION
        self.notice = self.clock = self.fog_offset = 0.0

    def switch(self, world):
        self.world = world
        self.origin = self.shadow  # 연타 시 현재 보이는 색에서 새 목표로 이어 간다.
        self.age = 0.0
        self.notice = 0.5

    def reject(self):
        self.age = self.DURATION
        self.shadow = float(self.world == "shadow")
        self.notice = 0.0

    def advance(self, elapsed, environment=True):
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("Visual elapsed time must be finite and non-negative")
        self.age = min(self.DURATION, self.age + elapsed)
        progress = self.age / self.DURATION
        smooth = progress * progress * (3 - 2 * progress)
        self.shadow = self.origin + (float(self.world == "shadow") - self.origin) * smooth
        self.notice = max(0.0, self.notice - elapsed)
        if self.motion_enabled and environment:
            self.clock += elapsed
            self.fog_offset = (self.fog_offset + (2 - 5 * self.shadow) * elapsed) % 320

    @property
    def indicator(self):
        return (160, 193, 255) if self.world == "shadow" else (255, 218, 146)

    def style(self, sprite):
        role = sprite.visual_role
        if role in ("none", "direct_light"):
            return sprite  # 플레이어와 B의 직접광은 두 세계에서 원본 색을 유지한다.
        if role == "terrain":
            # 지형은 전환 즉시 표시한다. 과거 세계의 발판을 겹쳐 그리지 않는다.
            tint = (210, 210, 255) if self.world == "shadow" else (255, 255, 255)
        else:
            warm = (255, 244, 222) if role == "background" else (255, 255, 255)
            cool = (157, 174, 255) if role == "background" else (202, 195, 255)
            tint = tuple(round(a + (b - a) * self.shadow) for a, b in zip(warm, cool))
        color = tuple(round(a * b / 255) for a, b in zip(sprite.tint, tint))
        palette = "shadow_lamp" if role == "lamp" and self.world == "shadow" else "original"
        return replace(sprite, tint=color, palette=palette)

    def pieces(self, sprite, x, y):
        sprite = self.style(sprite)
        pulse = max(0.0, 1 - self.age / self.DURATION)
        if sprite.visual_role != "background" or not self.motion_enabled or (pulse == 0 and self.shadow == 0):
            yield replace(sprite, x=x, y=y)
            return
        sx, sy, sw, sh = sprite.source
        for row in range(0, sh, 8):
            height = min(8, sh - row)
            world_y = y + row * sprite.height / sh
            shift = round(math.sin(world_y * 0.22 - self.clock * 24) * pulse
                          + math.sin(world_y * 0.15 - self.clock * 3) * self.shadow * 0.7)
            yield replace(sprite, source=(sx, sy + row, sw, height), x=x + shift,
                          y=world_y, height=height * sprite.height / sh)
