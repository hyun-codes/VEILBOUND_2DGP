"""A cat and its shadow form share the same ground patrol."""

from math import ceil, isfinite

from game.collision import CollisionWorld
from game.map_loader import MapFormatError
from game.player import AnimationSet


class CatEncounter:
    RANGE = 18
    STRIKE_FRAME = 4

    def __init__(self, obj, data, assets):
        self.x, self.y = obj.x, obj.y
        self.left = obj.properties.get("patrolLeft")
        self.right = obj.properties.get("patrolRight")
        if not all(type(x) in (int, float) and isfinite(x) for x in (self.left, self.right)):
            raise MapFormatError("Cat needs finite patrolLeft and patrolRight")
        if not 8 <= self.left < self.x < self.right <= data.width - 8:
            raise MapFormatError("Cat needs a patrol inside the map containing its start")
        terrain = CollisionWorld(s for s in data.solids if s.world == "common")
        samples = ceil(self.right - self.left)
        for i in range(samples + 1):
            x = self.left + (self.right - self.left) * i / samples
            if not terrain.supported(x, self.y, 1) or terrain.overlaps(x, self.y, 8, 14):
                raise MapFormatError("Cat patrol needs clear common ground")
        self.cat = AnimationSet(assets / "animals/cat/animations.json", ("idle", "walk"))
        self.imp = AnimationSet(assets / "monsters/imp/animations.json", ("idle", "run", "attack"))
        self.world = "real"
        self.facing = 1
        self.clip, self.time = "idle", 0.0

    def _play(self, clip, dt):
        self.time = self.time + dt if clip == self.clip else 0.0
        self.clip = clip

    def _near(self, player):
        if abs(player.x - self.x) > self.RANGE or abs(player.y - self.y) > 9:
            return False
        x, *_ = player.collision.move(self.x, self.y - 4, 1, 1, player.x - self.x, 0)
        return abs(x - player.x) < 1e-6

    def step(self, dt, player, world):
        if world != self.world:
            self.world = world
            self.clip, self.time = "idle", 0.0
        if self.clip == "attack":
            hit_time = self.imp.clips["attack"][1] * self.STRIKE_FRAME
            previous = self.time
            self.time += dt
            if self.time >= self.imp.duration("attack"):
                self.clip, self.time = "idle", 0.0
            return previous < hit_time <= previous + dt and self._near(player) and (
                self.facing * (player.x - self.x) >= -player.WIDTH / 2)
        if world == "shadow" and self._near(player):
            self.facing = 1 if player.x >= self.x else -1
            self._play("attack", dt)
            return False
        if self.clip == "idle" and self.time < 0.48:
            self._play("idle", dt)
            return False
        speed = 19 if world == "shadow" else 12
        self.x = max(self.left, min(self.right, self.x + self.facing * speed * dt))
        if self.x in (self.left, self.right):
            self.facing *= -1
            self._play("idle", dt)
        else:
            self._play("run" if world == "shadow" else "walk", dt)
        return False

    def finish_attack(self, dt):
        self.time += dt

    def draw(self, renderer, camera):
        animations = self.imp if self.world == "shadow" else self.cat
        sprite = animations.sprite(self.clip, self.time, self.x, self.y, self.facing)
        renderer.sprite(sprite, camera.screen_rect(sprite.x, sprite.y, sprite.width, sprite.height))
