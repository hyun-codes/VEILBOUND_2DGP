"""무기 없는 모션과 발 기준 물리 상태. 애니메이션이 입력·충돌을 기다리게 하지 않는다."""

import hashlib
import json
from pathlib import Path

from game.map_loader import Sprite, MapFormatError, _png_size


class AnimationSet:
    REQUIRED = ("idle", "run", "jump_start", "fall", "land")

    def __init__(self, path):
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("format") != "veilbound-grid-animations" or data.get("schema_version") != 1:
            raise MapFormatError("Unsupported player animation format")
        self.image = (path.parent / data["image"]).resolve()
        if hashlib.sha256(self.image.read_bytes()).hexdigest() != data["image_sha256"]:
            raise MapFormatError("Player sprite sheet hash differs from animations.json")
        iw, ih = _png_size(self.image)
        if (iw, ih) != (data["image_size"]["width"], data["image_size"]["height"]):
            raise MapFormatError("Player sprite sheet size disagrees with animations.json")
        grid = data["grid"]
        self.width, self.height = grid["cell_width"], grid["cell_height"]
        self.anchor = (data["anchor"]["x"], data["anchor"]["y"])
        if grid.get("margin", 0) or grid.get("spacing", 0) or data["source_facing"] != "right":
            raise MapFormatError("Unsupported player grid/facing")
        self.clips = {}
        for name in self.REQUIRED:
            clip = data["animations"][name]
            if not clip["enabled"] or not clip["columns"] or clip["frame_duration_ms"] <= 0:
                raise MapFormatError(f"Missing/invalid weapon-free animation: {name}")
            rects = tuple((c * self.width, clip["row"] * self.height, self.width, self.height)
                          for c in clip["columns"])
            if any(x < 0 or y < 0 or x + w > iw or y + h > ih for x, y, w, h in rects):
                raise MapFormatError(f"Player clip exceeds sheet: {name}")
            self.clips[name] = (rects, clip["frame_duration_ms"] / 1000, clip["loop"])

    def frame(self, name, elapsed):
        rects, duration, loop = self.clips[name]
        index = int((elapsed + 1e-9) / duration)
        return rects[index % len(rects) if loop else min(index, len(rects) - 1)]

    def duration(self, name):
        rects, duration, _ = self.clips[name]
        return len(rects) * duration


class Player:
    WIDTH, HEIGHT = 6, 14
    SPEED, JUMP_SPEED, GRAVITY, MAX_FALL = 64.0, 240.0, 1000.0, 360.0
    FALL_GRAVITY, RELEASE_SPEED = 1600.0, 130.0
    COYOTE_TIME, JUMP_BUFFER = 0.08, 0.10

    def __init__(self, animations, collision, map_width, start):
        self.animations, self.collision, self.map_width = animations, collision, map_width
        self.start = start
        self.reset()

    def reset(self):
        self.x, self.y = self.start
        self.vx = self.vy = 0.0
        self.direction, self.facing = 0, 1
        self.grounded = self.collision.supported(self.x, self.y, self.WIDTH)
        self.last_support = (self.x, self.y)
        self.coyote = self.COYOTE_TIME if self.grounded else 0.0
        self.jump_buffer = 0.0
        self.jump_held = False
        self.animation, self.animation_time = "idle", 0.0

    def clear_input(self):
        self.direction = 0
        self.jump_buffer = 0.0
        self.jump_held = False

    def request_jump(self):
        self.jump_buffer = self.JUMP_BUFFER
        self.jump_held = True

    def release_jump(self):
        self.jump_held = False

    def _jump(self):
        self.vy = -self.JUMP_SPEED
        self.grounded = False
        self.coyote = self.jump_buffer = 0.0

    def update(self, dt):
        was_grounded = self.grounded
        if was_grounded:
            self.last_support = (self.x, self.y)
            self.coyote = self.COYOTE_TIME
        if self.jump_buffer > 0 and (self.grounded or self.coyote > 0):
            self._jump()
        self.vx = self.direction * self.SPEED
        if self.direction:
            self.facing = self.direction
        # 상승 중 버튼을 놓으면 짧게 뛴다. 다시 눌러도 위쪽 속도를 더하지 않는다.
        if self.vy < 0 and not self.jump_held:
            self.vy = max(self.vy, -self.RELEASE_SPEED)
        gravity = self.GRAVITY if self.vy < 0 else self.FALL_GRAVITY
        self.vy = min(self.MAX_FALL, self.vy + gravity * dt)
        self.x, self.y, side, landed, ceiling = self.collision.move(
            self.x, self.y, self.WIDTH, self.HEIGHT, self.vx * dt, self.vy * dt)
        self.x = max(self.WIDTH / 2, min(self.x, self.map_width - self.WIDTH / 2))
        if side:
            self.vx = 0.0
        if landed or ceiling:
            self.vy = 0.0
        self.grounded = landed
        if landed:
            self.last_support = (self.x, self.y)
            self.coyote = self.COYOTE_TIME
            if self.jump_buffer > 0:
                self._jump()  # 착지 스텝에서 소비하되 위치를 즉시 옮기지는 않는다.
        else:
            self.coyote = max(0.0, self.coyote - dt)
        self.jump_buffer = max(0.0, self.jump_buffer - dt)
        if self.jump_buffer < 1e-9:
            self.jump_buffer = 0.0
        if not self.grounded:
            name = "jump_start" if self.vy < 0 else "fall"
        elif self.direction:
            name = "run"
        elif not was_grounded or (self.animation == "land" and
                                  self.animation_time < self.animations.duration("land")):
            name = "land"
        else:
            name = "idle"
        if name != self.animation:
            self.animation, self.animation_time = name, 0.0
        else:
            self.animation_time += dt

    def draw(self, renderer, camera):
        ax, ay = self.animations.anchor
        if self.facing < 0:
            ax = self.animations.width - ax
        sprite = Sprite(self.animations.image, self.animations.frame(self.animation, self.animation_time),
                        self.x - ax, self.y - ay, self.animations.width, self.animations.height,
                        flip_x=self.facing < 0)
        renderer.sprite(sprite, camera.screen_rect(sprite.x, sprite.y, sprite.width, sprite.height))
