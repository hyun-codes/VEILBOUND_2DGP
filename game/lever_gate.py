"""현실에서 조작해 열고 유지하는 레버·차단문 한 쌍. 위치와 연결은 Tiled에서 읽는다."""

from dataclasses import replace
import hashlib
import json
import math

from game.collision import Solid
from game.map_loader import MapFormatError, _png_size


def nearest_control(player, puzzle, mechanism):
    candidates = [("lamp", puzzle.nearby_control(player)), ("lever", mechanism.nearby_control(player))]
    return min(((kind, control) for kind, control in candidates if control is not None),
               key=lambda item: abs(player.x - item[1].x), default=(None, None))


class LeverGate:
    def __init__(self, source):
        levers = [o for o in source.objects if o.kind == "Lever" and o.properties.get("interactionEnabled", False)]
        gates = [o for o in source.objects if o.kind == "Gate"]
        self.enabled = bool(levers or gates)
        self.activated = False
        self.age = self.progress = 0.0
        self.lever = self.gate = None
        if not self.enabled:
            return
        if len(levers) != 1 or len(gates) != 1:
            raise MapFormatError("LeverGate currently requires exactly one enabled lever and one gate")
        self.lever, self.gate = levers[0], gates[0]
        if self.lever.properties.get("targetGate") != self.gate.name:
            raise MapFormatError("Lever targetGate must name its Gate object")
        for obj, key, default in ((self.lever, "radius", 6), (self.gate, "openSeconds", 0.4),
                                  (self.gate, "liftHeight", self.gate.height)):
            value = obj.properties.get(key, default)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise MapFormatError(f"{obj.name}.{key} must be positive and finite")
        if min(self.gate.width, self.gate.height) <= 0:
            raise MapFormatError("Gate must have positive rectangle dimensions")
        self.duration = self.gate.properties.get("openSeconds", 0.4)
        self.lift = self.gate.properties.get("liftHeight", self.gate.height)
        self.sprite_name = self.lever.properties["spriteObject"]
        self.bar_prefix = self.gate.properties["spritePrefix"]
        sprites = [s for s in source.sprites if s.object_name == self.sprite_name]
        bars = [s for s in source.sprites if s.object_name.startswith(self.bar_prefix)]
        if len(sprites) != 1 or not bars:
            raise MapFormatError("Lever/gate sprite objects are missing or duplicated")
        if any(s.world != "common" for s in sprites + bars):
            raise MapFormatError("Lever and physical gate sprites must be common to both worlds")
        cursor = self.gate.y
        for bar in sorted(bars, key=lambda s: s.y):
            if bar.x != self.gate.x or bar.width != self.gate.width or bar.y != cursor:
                raise MapFormatError("Gate sprites must cover its collision rectangle without gaps")
            cursor += bar.height
        if cursor != self.gate.y + self.gate.height:
            raise MapFormatError("Gate sprite height differs from collision rectangle")
        sprite = sprites[0]
        path = sprite.image.parent / "animations.json"
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
            grid = metadata["grid"]
            clip = metadata["animations"]["activate"]
            if ((path.parent / metadata["image"]).resolve() != sprite.image
                    or metadata["image_sha256"] != hashlib.sha256(sprite.image.read_bytes()).hexdigest()):
                raise ValueError("Lever animation image/hash mismatch")
            w, h = grid["cell_width"], grid["cell_height"]
            self.frames = tuple((c * w, clip["row"] * h, w, h) for c in clip["columns"])
            self.frame_seconds = clip["frame_duration_ms"] / 1000
            if not self.frames or self.frame_seconds <= 0 or not math.isfinite(self.frame_seconds):
                raise ValueError("Invalid lever clip")
            if self.frame_seconds * (len(self.frames) - 1) > self.duration:
                raise ValueError("Lever must reach its final pose before the gate finishes opening")
            iw, ih = metadata["image_size"]["width"], metadata["image_size"]["height"]
            if _png_size(sprite.image) != (iw, ih):
                raise ValueError("Lever metadata dimensions differ from PNG")
            if any(x < 0 or y < 0 or x + fw > iw or y + fh > ih for x, y, fw, fh in self.frames):
                raise ValueError("Lever frame outside sheet")
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise MapFormatError(f"Invalid lever metadata: {exc}") from exc

    @property
    def is_open(self):
        return self.enabled and self.progress >= 1.0

    def nearby_control(self, player):
        if not self.enabled:
            return None
        o = self.lever
        return o if abs(player.x - o.x) <= o.properties.get("radius", 6) and abs(player.y - o.y) <= 6 else None

    def interact(self, player, world):
        if not self.nearby_control(player) or not player.grounded or world != "real" or self.activated:
            return False
        self.activated = True
        return True

    def advance(self, dt):
        if not self.enabled or not self.activated or self.is_open:
            return False
        self.age = min(self.duration, self.age + dt)
        self.progress = min(1.0, self.age / self.duration)
        return True

    def compose(self, data, open_state=None):
        if not self.enabled:
            return data
        progress = self.progress if open_state is None else float(open_state)
        age = self.age if open_state is None else (self.duration if open_state else 0.0)
        frame = self.frames[min(int((age + 1e-9) / self.frame_seconds), len(self.frames) - 1)]
        sprites = []
        for sprite in data.sprites:
            if sprite.object_name == self.sprite_name:
                sprite = replace(sprite, source=frame)
            elif sprite.object_name.startswith(self.bar_prefix):
                sprite = replace(sprite, y=sprite.y - self.lift * progress)
            sprites.append(sprite)
        gate = Solid(self.gate.x, self.gate.y - self.lift * progress, self.gate.width, self.gate.height)
        return replace(data, sprites=tuple(sprites), solids=data.solids + (gate,))

    def draw(self, renderer, camera):
        if not self.enabled:
            return
        color = (116, 223, 188) if self.is_open else (229, 181, 103) if self.activated else (165, 124, 79)
        lever, gate = self.lever, self.gate
        cable_y = gate.properties.get("cableY", gate.y + gate.height + 24)
        points = [(lever.x, lever.y - 6), (lever.x, cable_y),
                  (gate.x + gate.width / 2, cable_y), (gate.x + gate.width / 2, gate.y + gate.height)]
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            renderer.rectangle(camera.screen_rect(min(x1, x2), min(y1, y2),
                                                  max(1, abs(x2 - x1)), max(1, abs(y2 - y1))), color, filled=True)
        # 어두운 원본 철제 난간을 식별할 문틀과 실제 이동 경계선. 열린 통로의 틀은 남는다.
        renderer.rectangle(camera.screen_rect(gate.x - 1, gate.y, gate.width + 2, gate.height),
                           (114, 125, 144))
        renderer.rectangle(camera.screen_rect(gate.x, gate.y - self.lift * self.progress,
                                              gate.width, gate.height), color)
