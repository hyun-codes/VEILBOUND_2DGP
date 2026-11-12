"""A block on two rail stops. It supports the player in the real world."""

from dataclasses import replace
import math

from game.collision import CollisionWorld, Solid
from game.map_loader import MapFormatError


class SlidingBlock:
    def __init__(self, data):
        blocks = [obj for obj in data.objects if obj.kind == "SlidingBlock"]
        self.block = data.object_named(blocks[0].name) if blocks else None
        self.position = 0
        if not self.block:
            return
        block = self.block
        target = block.properties.get("destinationX")
        if (len(blocks) != 1 or not isinstance(target, (int, float)) or not math.isfinite(target)
                or target == block.x or min(block.width, block.height) <= 0
                or min(block.x, target, block.y) < 0 or max(block.x, target) + block.width > data.width
                or block.y + block.height > data.height):
            raise MapFormatError("SlidingBlock requires one in-bounds block and a different destinationX")
        self.stops = (block.x, target)
        self.sweep = CollisionWorld((Solid(min(self.stops), block.y,
                                          abs(target - block.x) + block.width, block.height),))
        if any(self.sweep.overlaps(s.x + s.width / 2, s.y + s.height, s.width, s.height)
               for s in data.solids if s.world in ("common", "real")):
            raise MapFormatError("SlidingBlock rail intersects solid terrain")
        self.art = tuple(s for s in data.sprites if s.object_name.startswith("Sliding block "))
        if not self.art:
            raise MapFormatError("SlidingBlock requires tile objects named Sliding block …")

    def nearby_control(self, player):
        if not self.block:
            return None
        block = self.block
        x = self.stops[self.position]
        bottom = block.y + block.height
        if not (x - 16 <= player.x <= x + block.width + 16 and abs(player.y - bottom) <= 6):
            return None
        if self.sweep.overlaps(player.x, player.y, player.WIDTH, player.HEIGHT):
            return None
        return replace(block, x=x + block.width / 2, y=bottom)

    def interact(self, player, world):
        if world != "real" or not player.grounded or not self.nearby_control(player):
            return False
        self.position = 1 - self.position
        return True

    def compose(self, data):
        if not self.block:
            return data
        block = self.block
        x = self.stops[self.position]
        sprites = tuple(s for s in data.sprites if s not in self.art)
        for piece in self.art:
            moved = replace(piece, x=piece.x + x - block.x, world="real")
            sprites += (moved, replace(moved, world="shadow", opacity=0.20, tint=(169, 124, 226)))
        solid = Solid(x, block.y, block.width, block.height, "real")
        return replace(data, sprites=sprites, solids=data.solids + (solid,))
