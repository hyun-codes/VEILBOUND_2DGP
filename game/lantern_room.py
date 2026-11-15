"""A docked lantern lights entire platforms whose centers are within reach."""

from math import hypot, isfinite

from game.collision import CollisionWorld, Solid
from game.map_loader import MapFormatError


class LanternRoom:
    RADIUS = 110
    CARRY_RADIUS = 46
    START_RADIUS = 39
    WIDTH, HEIGHT = 6, 13

    def __init__(self, data):
        self.data = data
        self.start = data.object_named("PlayerStart")
        self.exit = data.object_named("Exit")
        self.ground = tuple(Solid(o.x, o.y, o.width, o.height) for o in data.objects if o.kind == "Ground")
        self.platforms = tuple(Solid(o.x, o.y, o.width, o.height)
                               for o in data.objects if o.kind == "LightPlatform")
        self.sockets = tuple(o for o in data.objects if o.kind == "Socket")
        initial = [o for o in self.sockets if o.properties.get("initial") is True]
        if len(initial) != 1 or not self.ground or not self.platforms:
            raise MapFormatError("A lantern room needs ground, light platforms and exactly one starting socket")
        for obj in (*self.ground, *self.platforms, self.exit):
            if not (0 <= obj.x < obj.x + obj.width <= data.width
                    and 0 <= obj.y < obj.y + obj.height <= data.height):
                raise MapFormatError("Room rectangle must have positive size and fit inside the map")
        ground = CollisionWorld(self.ground)
        for obj in (*self.sockets, self.start):
            if not (isfinite(obj.x) and self.WIDTH / 2 <= obj.x <= data.width - self.WIDTH / 2
                    and ground.supported(obj.x, obj.y, self.WIDTH)):
                raise MapFormatError("Starts and sockets must be on permanent ground")
        self.initial_socket = initial[0]
        self.reset()

    def reset(self):
        self.x, self.y = self.start.x, self.start.y
        self.vy = 0.0
        self.walk_time = 0.0
        self.facing = 1
        self.grounded = True
        self.complete = False
        self.socket = self.initial_socket

    @property
    def light(self):
        if self.socket is None:
            return self.x + 6 * self.facing, self.y - 7, self.CARRY_RADIUS
        radius = self.START_RADIUS if self.socket is self.initial_socket else self.RADIUS
        return self.socket.x, self.socket.y - 10, radius

    def lit(self, platform):
        if self.socket is None:
            return False
        x, y, radius = self.light
        return hypot(platform.x + platform.width / 2 - x, platform.y - y) <= radius

    def interaction(self):
        if not self.grounded or self.complete:
            return None
        candidates = (self.socket,) if self.socket else self.sockets
        return min((o for o in candidates if abs(self.x - o.x) <= 9 and abs(self.y - o.y) <= 2),
                   key=lambda o: abs(self.x - o.x), default=None)

    def step(self, dt, direction, jump=False, interact=False):
        if self.complete:
            return
        if direction:
            self.facing = direction
        if interact and (target := self.interaction()):
            self.socket = None if self.socket else target
        collision = CollisionWorld(self.ground + tuple(p for p in self.platforms if self.lit(p)))
        if jump and self.grounded and collision.supported(self.x, self.y, self.WIDTH):
            self.vy = -238.0
        self.vy = min(350.0, self.vy + 960.0 * dt)
        previous_x = self.x
        self.x, self.y, _, landed, ceiling = collision.move(
            self.x, self.y, self.WIDTH, self.HEIGHT, direction * 72.0 * dt, self.vy * dt)
        self.x = max(self.WIDTH / 2, min(self.x, self.data.width - self.WIDTH / 2))
        self.grounded = landed
        if landed or ceiling:
            self.vy = 0.0
        self.walk_time = self.walk_time + dt if landed and self.x != previous_x else 0.0
        if self.y - self.HEIGHT > self.data.height:
            self.reset()
            return
        self.complete = (landed and self.exit.x <= self.x <= self.exit.x + self.exit.width
                         and self.exit.y <= self.y <= self.exit.y + self.exit.height)
