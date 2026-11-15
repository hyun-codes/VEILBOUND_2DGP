"""Light determines the visible surfaces and the collision geometry."""

from math import ceil, floor, isfinite, sqrt

from game.collision import CollisionWorld, Solid
from game.map_loader import MapFormatError
from game.rail_light import RailLight


def light_span(light, row, fraction=1):
    x, y, radius = light
    remaining = (radius * fraction) ** 2 - (row + 0.5 - y) ** 2
    if remaining >= 0:
        span = sqrt(remaining)
        return ceil(x - span - 0.5), floor(x + span - 0.5) + 1


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
            Solid(o.x, o.y, o.width, o.height) for o in self.props) + data.solids
        self.sockets = tuple(o for o in data.objects if o.kind == "Socket")
        initial = [o for o in self.sockets if o.properties.get("initial") is True]
        if len(initial) != 1 or not self.ground or not (self.platforms or data.solids):
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
        for socket in self.sockets:
            radius = socket.properties.get("radius", self.RADIUS)
            if type(radius) not in (int, float) or not isfinite(radius) or radius <= 0:
                raise MapFormatError("Socket radius must be positive")
        self.initial_socket = initial[0]
        points = [obj for obj in data.objects if obj.kind == "RailPoint"]
        self.rail = RailLight(data, points) if points else None
        self.projectors = tuple(o for o in data.objects if o.kind == "Projector")
        self.aims = {}
        for projector in self.projectors:
            targets = tuple(o for o in data.objects
                            if o.kind == "Focus" and o.properties.get("projector") == projector.name)
            if len(targets) < 2 or any(not (0 <= o.x < data.width and 0 <= o.y < data.height)
                                       for o in targets):
                raise MapFormatError("Projector needs at least two in-bounds focus points")
            for target in targets:
                radius = target.properties.get("radius")
                if type(radius) not in (int, float) or not isfinite(radius) or radius <= 0:
                    raise MapFormatError("Focus radius must be positive")
            self.aims[projector.name] = targets
        self.receivers = tuple(o for o in data.objects if o.kind == "Receiver")
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
        self.elapsed = 0.0
        self.aim_indices = dict.fromkeys(self.aims, 0)

    @property
    def light(self):
        if self.socket is None:
            return self.x + 6 * self.facing, self.y - 7, self.CARRY_RADIUS
        radius = self.socket.properties.get(
            "radius", self.START_RADIUS if self.socket is self.initial_socket else self.RADIUS)
        return self.socket.x, self.socket.y - 10, radius

    @property
    def lights(self):
        bases = (self.light, self.rail.at(self.elapsed)) if self.rail else (self.light,)
        return bases + self.projected_lights

    @property
    def projected_lights(self):
        focuses = (targets[self.aim_indices[name]] for name, targets in self.aims.items())
        return tuple((o.x, o.y, o.properties["radius"]) for o in focuses)

    def receiver_lit(self, receiver):
        return any((receiver.x - x) ** 2 + (receiver.y - y) ** 2 <= radius ** 2
                   for x, y, radius in self.projected_lights)

    def illuminated(self, x, y):
        return any((x - lx) ** 2 + (y - ly) ** 2 <= radius ** 2 for lx, ly, radius in self.lights)

    def exposed(self, obj):
        right = obj.x + obj.width
        lights = self.lights
        for y in range(int(obj.y), int(obj.y + obj.height)):
            for light in lights:
                if span := light_span(light, y):
                    left, end = max(obj.x, span[0]), min(right, span[1])
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
        sockets = (self.socket,) if self.socket else self.sockets
        candidates = self.projectors + tuple(o for o in sockets if not o.properties.get("fixed"))
        return min((o for o in candidates if abs(self.x - o.x) <= 9 and abs(self.y - o.y) <= 2),
                   key=lambda o: abs(self.x - o.x), default=None)

    def step(self, dt, direction, jump=False, interact=False):
        if self.complete:
            return
        self.elapsed += dt
        if direction:
            self.facing = direction
        if interact and (target := self.interaction()):
            if target.kind == "Projector":
                name = target.name
                self.aim_indices[name] = (self.aim_indices[name] + 1) % len(self.aims[name])
            else:
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
                         and all(self.receiver_lit(receiver) for receiver in self.receivers)
                         and self.exit.x <= self.x <= self.exit.x + self.exit.width
                         and self.exit.y <= self.y <= self.exit.y + self.exit.height
                         and self.illuminated(self.x, self.y))
