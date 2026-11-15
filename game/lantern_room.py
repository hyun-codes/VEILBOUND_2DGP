"""Light determines the visible surfaces and the collision geometry."""

from math import ceil, floor, isfinite, sqrt

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
        self.props = tuple(o for o in data.objects if o.kind in ("Wall", "Box"))
        self.keys = tuple(o for o in data.objects if o.kind == "Key")
        self.terrain = self.ground + self.platforms + tuple(
            Solid(o.x, o.y, o.width, o.height) for o in self.props)
        self.sockets = tuple(o for o in data.objects if o.kind == "Socket")
        initial = [o for o in self.sockets if o.properties.get("initial") is True]
        if len(initial) != 1 or not self.ground or not self.platforms:
            raise MapFormatError("A lantern room needs ground, light platforms and exactly one starting socket")
        for obj in (*self.terrain, *self.keys, self.exit):
            if not (0 <= obj.x < obj.x + obj.width <= data.width
                    and 0 <= obj.y < obj.y + obj.height <= data.height
                    and all(float(value).is_integer() for value in (obj.x, obj.y, obj.width, obj.height))):
                raise MapFormatError("Room rectangles need whole-pixel coordinates and positive size inside the map")
        ground = CollisionWorld(self.ground)
        for obj in (*self.sockets, self.start):
            if not (isfinite(obj.x) and self.WIDTH / 2 <= obj.x <= data.width - self.WIDTH / 2
                    and ground.supported(obj.x, obj.y, self.WIDTH)):
                raise MapFormatError("Starts and sockets must be on a Ground surface")
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
        self.collected = set()

    @property
    def light(self):
        if self.socket is None:
            return self.x + 6 * self.facing, self.y - 7, self.CARRY_RADIUS
        radius = self.START_RADIUS if self.socket is self.initial_socket else self.RADIUS
        return self.socket.x, self.socket.y - 10, radius

    def illuminated(self, x, y):
        lx, ly, radius = self.light
        return (x - lx) ** 2 + (y - ly) ** 2 <= radius ** 2

    def exposed(self, obj):
        lx, ly, radius = self.light
        right = obj.x + obj.width
        for y in range(int(obj.y), int(obj.y + obj.height)):
            remaining = radius ** 2 - (y + 0.5 - ly) ** 2
            if remaining < 0:
                continue
            span = sqrt(remaining)
            left = max(obj.x, ceil(lx - span - 0.5))
            end = min(right, floor(lx + span - 0.5) + 1)
            if left < end:
                yield Solid(left, y, end - left, 1)

    def collision(self):
        return CollisionWorld(strip for body in self.terrain for strip in self.exposed(body))

    def _touches(self, obj):
        return (self.x + self.WIDTH / 2 > obj.x and self.x - self.WIDTH / 2 < obj.x + obj.width
                and self.y > obj.y and self.y - self.HEIGHT < obj.y + obj.height)

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
        collision = self.collision()
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
        for index, key in enumerate(self.keys):
            if index not in self.collected and any(self._touches(part) for part in self.exposed(key)):
                self.collected.add(index)
        self.complete = (landed and len(self.collected) == len(self.keys)
                         and self.exit.x <= self.x <= self.exit.x + self.exit.width
                         and self.exit.y <= self.y <= self.exit.y + self.exit.height
                         and self.illuminated(self.x, self.y))
