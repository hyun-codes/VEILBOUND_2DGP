"""미리 편집한 계단/다리 배치를 같은 가로등의 두 위치로 선택한다."""

from dataclasses import replace

from game.collision import CollisionWorld
from game.map_loader import MapFormatError


class LampPuzzle:
    def __init__(self, source):
        self.source = source
        self.controls = tuple(o for o in source.objects if o.kind == "LampControl")
        self.enabled = bool(self.controls)
        if not self.enabled and any(s.lamp_state for s in source.solids):
            raise MapFormatError("Lamp terrain presets require LampControl objects")
        self.mode = source.properties.get("lampInitialState", "bridge")
        if self.mode not in ("stairs", "bridge"):
            raise MapFormatError("lampInitialState must be stairs or bridge")
        self._layouts = {}
        if self.enabled:
            if any(s.lamp_state and s.world != "shadow" for s in source.solids):
                raise MapFormatError("Lamp preset solids must be shadow-only")
            if {s.lamp_state for s in source.solids if s.lamp_state} != {"stairs", "bridge"}:
                raise MapFormatError("Lamp puzzle needs both stairs and bridge terrain presets")
            rail = source.object_named("LampRail")
            for mode in ("stairs", "bridge"):
                sprites = tuple(replace(s, x=rail.properties[f"{mode}X"])
                                if s.object_name == "Route lamp" else s
                                for s in source.sprites if s.lamp_state in ("", mode))
                solids = tuple(s for s in source.solids if s.lamp_state in ("", mode))
                self._layouts[mode] = replace(source, sprites=sprites, solids=solids)
            if sum(s.object_name == "Route lamp" for s in source.sprites) != 1:
                raise MapFormatError("Lamp puzzle requires exactly one Route lamp tile object")

    @property
    def data(self):
        return self._layouts[self.mode] if self.enabled else self.source

    def near_control(self, player):
        return any(abs(player.x - o.x) <= o.properties.get("radius", 16)
                   and abs(player.y - o.y) <= 6 for o in self.controls)

    def hint(self, player, world):
        if not self.enabled:
            return ""
        if self.near_control(player):
            if world != "real":
                return "Lamp control: return to REAL, then press E"
            if not player.grounded:
                return "Land beside the lamp control to use E"
            target = "BRIDGE" if self.mode == "stairs" else "STAIRS"
            return f"E: move lamp -> {target}"
        return f"Lamp: {self.mode.upper()} - controls are marked RAIL"

    def interact(self, player, world):
        if not self.enabled or not self.near_control(player) or not player.grounded or world != "real":
            return False
        target = "bridge" if self.mode == "stairs" else "stairs"
        if CollisionWorld(self._layouts[target].solids, world).overlaps(player.x, player.y, player.WIDTH, player.HEIGHT):
            return False
        self.mode = target
        return True

    def draw(self, renderer, camera):
        for control in self.controls:
            x, y, _, _ = camera.screen_rect(control.x, control.y, 0, 0)
            renderer.label(x - 16, y + 16, "RAIL", (255, 218, 146))
