"""A의 그림자 지형에서 B의 직접광 영역을 제외한다. 자유 광학 계산은 하지 않는다."""

from dataclasses import replace
import math

from game.collision import CollisionWorld
from game.map_loader import MapFormatError


class LampPuzzle:
    def __init__(self, source):
        self.source = source
        self.controls = tuple(o for o in source.objects if o.kind == "LampControl")
        self.enabled = bool(self.controls)
        self.has_eraser = source.properties.get("puzzleType") == "lightErasure"
        if not self.enabled and (self.has_eraser or any(s.lamp_state for s in source.solids)):
            raise MapFormatError("Lamp terrain presets require LampControl objects")
        self.mode = source.properties.get("lampInitialState", "bridge")
        self.light_mode = source.properties.get("lightInitialState", "near")
        self.beams = {}
        if self.light_mode not in ("near", "far"):
            raise MapFormatError("lightInitialState must be near or far")
        if self.mode not in ("stairs", "bridge"):
            raise MapFormatError("lampInitialState must be stairs or bridge")
        self._layouts = {}
        if self.enabled:
            if any(s.lamp_state and s.world != "shadow" for s in source.solids):
                raise MapFormatError("Lamp preset solids must be shadow-only")
            if {s.lamp_state for s in source.solids if s.lamp_state} != {"stairs", "bridge"}:
                raise MapFormatError("Lamp puzzle needs both stairs and bridge terrain presets")
            rail = source.object_named("LampRail")
            for control in self.controls:
                if control.properties.get("lamp", "A") not in ("A", "B"):
                    raise MapFormatError("LampControl.lamp must be A or B")
                radius = control.properties.get("radius", 16)
                if not isinstance(radius, (int, float)) or not math.isfinite(radius) or radius <= 0:
                    raise MapFormatError("LampControl.radius must be positive and finite")
            if any(c.properties.get("lamp") == "B" for c in self.controls) != self.has_eraser:
                raise MapFormatError("B controls require puzzleType=lightErasure and vice versa")
            if not any(c.properties.get("lamp", "A") == "A" for c in self.controls):
                raise MapFormatError("Lamp puzzle requires an A control")
            if self.has_eraser:
                if sum(s.object_name == "Eraser lamp" for s in source.sprites) != 1:
                    raise MapFormatError("Lamp puzzle requires exactly one Eraser lamp tile object")
                b_rail = source.object_named("EraserRail")
                for state in ("near", "far"):
                    beam = source.object_named(f"Beam_{state}")
                    values = (beam.x, beam.y, beam.width, beam.height)
                    if (not all(isinstance(v, (int, float)) and math.isfinite(v) and v % 8 == 0 for v in values)
                            or min(beam.width, beam.height) <= 0 or min(beam.x, beam.y) < 0
                            or beam.x + beam.width > source.width or beam.y + beam.height > source.height):
                        raise MapFormatError("Beam rectangles must fit map and align to 8px cells")
                    if not any(s.lamp_state == "bridge" and self._inside(s, beam) for s in source.solids):
                        raise MapFormatError("Each beam must erase bridge tiles")
                    self.beams[state] = beam
                if self.beams["near"].x == self.beams["far"].x:
                    raise MapFormatError("Beam presets must target different bridge sections")
            for mode in ("stairs", "bridge"):
                for light in ("near", "far"):
                    beam = self.beams.get(light)
                    def keep(item):
                        return (item.lamp_state in ("", mode) and
                                not (beam and item.lamp_state == "bridge" and self._inside(item, beam)))
                    sprites = []
                    for sprite in source.sprites:
                        if not keep(sprite):
                            continue
                        if sprite.object_name == "Route lamp":
                            sprite = replace(sprite, x=self._rail_x(rail, f"{mode}X"))
                        elif self.has_eraser and sprite.object_name == "Eraser lamp":
                            sprite = replace(sprite, x=self._rail_x(b_rail, f"{light}X"),
                                             visual_role="direct_light")
                        sprites.append(sprite)
                    self._layouts[mode, light] = replace(source, sprites=tuple(sprites),
                                                         solids=tuple(s for s in source.solids if keep(s)))
            if sum(s.object_name == "Route lamp" for s in source.sprites) != 1:
                raise MapFormatError("Lamp puzzle requires exactly one Route lamp tile object")

    @property
    def data(self):
        return self._layouts[self.mode, self.light_mode] if self.enabled else self.source

    @staticmethod
    def _rail_x(rail, key):
        value = rail.properties.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise MapFormatError(f"{rail.name}.{key} must be finite")
        return value

    @staticmethod
    def _inside(item, beam):
        return (item.x >= beam.x and item.x + item.width <= beam.x + beam.width
                and item.y >= beam.y and item.y + item.height <= beam.y + beam.height)

    def nearby_control(self, player):
        nearby = [o for o in self.controls if abs(player.x - o.x) <= o.properties.get("radius", 16)
                  and abs(player.y - o.y) <= 6]
        return min(nearby, key=lambda o: abs(player.x - o.x), default=None)

    def near_control(self, player):
        return self.nearby_control(player) is not None

    def hint(self, player, world):
        if not self.enabled:
            return ""
        control = self.nearby_control(player)
        if control:
            lamp = control.properties.get("lamp", "A")
            if world != "real":
                return f"Lamp {lamp}: return to REAL to use E"
            if not player.grounded:
                return "Land beside the lamp control to use E"
            if lamp == "B":
                target = "FAR" if self.light_mode == "near" else "NEAR"
                return f"E: aim B light {target} - light erases shadow paths"
            target = "BRIDGE" if self.mode == "stairs" else "STAIRS"
            return f"E: A -> {target}"
        if self.has_eraser:
            return f"A: {self.mode.upper()} | B: {self.light_mode.upper()} | Light erases shadow paths"
        return f"Lamp: {self.mode.upper()} - controls are marked A"

    def interact(self, player, world):
        control = self.nearby_control(player)
        if not control or not player.grounded or world != "real":
            return False
        mode, light = self.mode, self.light_mode
        if control.properties.get("lamp", "A") == "B":
            light = "far" if light == "near" else "near"
        else:
            mode = "bridge" if mode == "stairs" else "stairs"
        if CollisionWorld(self._layouts[mode, light].solids, world).overlaps(player.x, player.y, player.WIDTH, player.HEIGHT):
            return False
        self.mode, self.light_mode = mode, light
        return True

    def draw(self, renderer, camera, world="real"):
        if self.has_eraser:
            beam = self.beams[self.light_mode]
            lamp = next(s for s in self.data.sprites if s.object_name == "Eraser lamp")
            # 광선 테두리만 그려 플레이어를 가리지 않고 도착 영역을 설명한다.
            for target_x in (beam.x, beam.x + beam.width):
                dx, dy = target_x - lamp.x - 3, beam.y + 7 - lamp.y - 6
                steps = max(1, math.ceil(max(abs(dx), abs(dy)) / 3))
                for i in range(steps + 1):
                    renderer.rectangle(camera.screen_rect(lamp.x + 3 + dx * i / steps,
                                                          lamp.y + 6 + dy * i / steps, 1, 1),
                                       (187, 157, 94), filled=True)
            for x in range(int(beam.x), int(beam.x + beam.width), 8):
                renderer.rectangle(camera.screen_rect(x, beam.y + 7, 4, 1), (243, 199, 107), filled=True)
            x, y, _, _ = camera.screen_rect(beam.x + 8, beam.y - 2, 0, 0)
            renderer.label(x, y, "LIGHT / NO PATH", (243, 199, 107))
            # 현실에서도 다음 그림자 지형과 밝아서 지워진 쪽을 비교할 수 있다.
            if world == "real" and self.mode == "bridge":
                for other in self.beams.values():
                    if other is not beam:
                        for x in range(int(other.x), int(other.x + other.width), 8):
                            renderer.rectangle(camera.screen_rect(x, other.y + 7, 4, 1),
                                               (119, 146, 187), filled=True)
        for control in self.controls:
            x, y, _, _ = camera.screen_rect(control.x, control.y, 0, 0)
            color = (243, 199, 107) if control.properties.get("lamp") == "B" else (172, 198, 238)
            renderer.label(x - 8, y + 16, control.properties.get("lamp", "A"), color)
