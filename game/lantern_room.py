"""Light determines the visible surfaces and the collision geometry."""

from dataclasses import replace
from math import ceil, floor, isfinite, sqrt

from game.collision import CollisionWorld, Solid
from game.map_loader import MapFormatError, MapObject
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
    PROJECTOR_TURN = 0.60
    CHUTE_TRAVEL = 0.70
    FLOOD_TRAVEL = 0.65
    WIDTH, HEIGHT = 6, 13
    CHEST_HEIGHT = 7
    LANTERN_WIDTH, LANTERN_HEIGHT = 5, 9

    def __init__(self, data):
        self.data = data
        self.start = data.object_named("PlayerStart")
        self.exit = data.object_named("Exit")
        self.ground = tuple(Solid(o.x, o.y, o.width, o.height) for o in data.objects if o.kind == "Ground")
        self.platforms = tuple(Solid(o.x, o.y, o.width, o.height)
                               for o in data.objects if o.kind == "LightPlatform")
        self.props = tuple(o for o in data.objects if o.kind in ("Wall", "Box"))
        crates = tuple(o for o in data.objects if o.kind == "PushCrate")
        if len(crates) > 1:
            raise MapFormatError("A room supports one movable crate")
        self.crate_start = crates[0] if crates else None
        self.keys = tuple(o for o in data.objects if o.kind == "Key")
        self.floods = tuple(o for o in data.objects if o.kind == "Flood")
        self.terrain = self.ground + self.platforms + tuple(
            Solid(o.x, o.y, o.width, o.height) for o in self.props) + data.solids
        self.sockets = tuple(o for o in data.objects if o.kind == "Socket")
        initial = [o for o in self.sockets if o.properties.get("initial") is True]
        if len(initial) != 1 or not self.ground or not (self.platforms or data.solids):
            raise MapFormatError("A lantern room needs ground, light platforms and exactly one starting socket")
        for obj in (*self.terrain, *self.keys, *crates, *self.floods, self.exit):
            if not (0 <= obj.x < obj.x + obj.width <= data.width
                    and 0 <= obj.y < obj.y + obj.height <= data.height
                    and all(float(value).is_integer() for value in (obj.x, obj.y, obj.width, obj.height))):
                raise MapFormatError("Room rectangles need whole-pixel coordinates and positive size inside the map")
        ground = CollisionWorld(self.ground)
        terrain = CollisionWorld(self.terrain)
        for obj in (*self.sockets, self.start):
            surface = ground if obj is self.start else terrain
            if not (isfinite(obj.x) and self.WIDTH / 2 <= obj.x <= data.width - self.WIDTH / 2
                    and surface.supported(obj.x, obj.y, self.WIDTH)):
                raise MapFormatError("The start needs ground and sockets need a supporting surface")
        for socket in self.sockets:
            radius = socket.properties.get("radius", self.RADIUS)
            if type(radius) not in (int, float) or not isfinite(radius) or radius <= 0:
                raise MapFormatError("Socket radius must be positive")
        self.valves = tuple(o for o in data.objects if o.kind == "DrainValve")
        self.valve_links = {}
        for valve in self.valves:
            socket = data.object_named(valve.properties.get("socket"))
            flood = data.object_named(valve.properties.get("flood"))
            if socket not in self.sockets or flood not in self.floods or not terrain.supported(
                    valve.x, valve.y, self.WIDTH):
                raise MapFormatError("A drain valve needs a floor, socket and flood")
            self.valve_links[valve.name] = socket, flood
        if len(self.valve_links) != len(self.valves):
            raise MapFormatError("Drain valves need unique names")
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
        required_socket = self.exit.properties.get("socket")
        self.exit_socket = data.object_named(required_socket) if required_socket else None
        if self.exit_socket is not None and self.exit_socket not in self.sockets:
            raise MapFormatError("Exit socket must refer to a socket")
        self.switches = tuple(o for o in data.objects if o.kind == "ProjectorSwitch")
        if any(o.properties.get("projector") not in self.aims for o in self.switches):
            raise MapFormatError("A projector switch must name an existing projector")
        self.switch_relays = {}
        for switch in self.switches:
            if "relay" in switch.properties:
                relay = data.object_named(switch.properties["relay"])
                if relay.kind != "Relay" or not (0 <= relay.x < data.width and 0 <= relay.y < data.height):
                    raise MapFormatError("A projector switch relay must be an in-bounds Relay")
                self.switch_relays[switch.name] = relay
        self.selected_focus = {}
        for control in self.projectors + self.switches:
            if focus := control.properties.get("selectFocus"):
                targets = self.aims[control.properties.get("projector", control.name)]
                indices = [i for i, o in enumerate(targets) if o.name == focus]
                if len(indices) != 1:
                    raise MapFormatError("A control must name one of its projector's focus points")
                self.selected_focus[control.name] = indices[0]
        self.fixtures = tuple(o for o in data.objects if o.kind == "FixedLight")
        self.fixed_lights = tuple((o.x, o.y, o.properties.get("radius", 0)) for o in self.fixtures)
        if any(type(r) not in (int, float) or not isfinite(r) or r <= 0
               or not (0 <= x < data.width and 0 <= y < data.height)
               for x, y, r in self.fixed_lights):
            raise MapFormatError("A fixed light needs an in-bounds position and positive radius")
        self.chutes = tuple(o for o in data.objects if o.kind == "Chute")
        self.chute_targets = {}
        for chute in self.chutes:
            target = data.object_named(chute.properties.get("socket"))
            if target not in self.sockets or target.y <= chute.y:
                raise MapFormatError("A chute must lead to a socket below it")
            self.chute_targets[chute.name] = target
        beacons = tuple(o for o in data.objects if o.kind == "Beacon")
        self.beacons = {o.name: (o, o.properties.get("radius")) for o in beacons}
        if len(self.beacons) != len(beacons) or "" in self.beacons:
            raise MapFormatError("Beacons need unique names")
        for beacon, radius in self.beacons.values():
            if not (type(radius) in (int, float) and isfinite(radius) and radius > 0
                    and self.WIDTH / 2 <= beacon.x <= data.width - self.WIDTH / 2
                    and 8 <= beacon.y <= data.height
                    and terrain.supported(beacon.x, beacon.y, self.WIDTH)):
                raise MapFormatError("A beacon needs a supporting surface and positive radius")
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
        self.lit_beacons = set()
        self.elapsed = 0.0
        self.aim_indices = dict.fromkeys(self.aims, 0)
        self.turning = {}
        self.in_transit = None
        self.loose_lantern = None
        self.lantern_vy = 0.0
        self.crate = self.crate_start
        self.crate_vy = 0.0
        self.drained = None
        self.flood_from = {}
        self.drain_started = 0.0

    @property
    def carrying_lantern(self):
        return self.socket is None and self.loose_lantern is None and self.in_transit is None

    @property
    def light(self):
        if self.loose_lantern:
            return self.loose_lantern.x, self.loose_lantern.y - 4, self.CARRY_RADIUS
        if self.in_transit:
            chute, target, started = self.in_transit
            progress = min(1.0, (self.elapsed - started) / self.CHUTE_TRAVEL)
            return (chute.x + (target.x - chute.x) * progress,
                    chute.y - 10 + (target.y - chute.y) * progress ** 2, self.CARRY_RADIUS)
        if self.socket is None:
            return self.x, self.y - self.CHEST_HEIGHT, self.CARRY_RADIUS
        radius = self.socket.properties.get(
            "radius", self.START_RADIUS if self.socket is self.initial_socket else self.RADIUS)
        return self.socket.x, self.socket.y - 10, radius

    @property
    def lights(self):
        bases = (self.light, self.rail.at(self.elapsed)) if self.rail else (self.light,)
        return bases + self.fixed_lights + self.projected_lights + tuple(
            (beacon.x, beacon.y - 8, radius)
            for name, (beacon, radius) in self.beacons.items() if name in self.lit_beacons)

    @property
    def projected_lights(self):
        return tuple(self.projected_light(name) for name in self.aims)

    def projected_light(self, name):
        focus = self.aims[name][self.aim_indices[name]]
        destination = focus.x, focus.y, focus.properties["radius"]
        turn = self.turning.get(name)
        if turn is None:
            return destination
        origin, started = turn
        t = min(1.0, (self.elapsed - started) / self.PROJECTOR_TURN)
        ease = t * t * (3 - 2 * t)
        return tuple(a + (b - a) * ease for a, b in zip(origin, destination))

    def receiver_lit(self, receiver, *, projector=None):
        lights = self.projected_lights if projector is None else (self.projected_light(projector),)
        return any((receiver.x - x) ** 2 + (receiver.y - y) ** 2 <= radius ** 2
                   for x, y, radius in lights)

    def relay_lit(self, switch):
        return self.receiver_lit(self.switch_relays[switch.name],
                                 projector=switch.properties["projector"])

    def illuminated(self, x, y):
        return any((x - lx) ** 2 + (y - ly) ** 2 <= radius ** 2 for lx, ly, radius in self.lights)

    def water_depth(self, flood):
        start = self.flood_from.get(flood.name, flood.height)
        target = 0 if flood == self.drained else flood.height
        progress = min(1.0, (self.elapsed - self.drain_started) / self.FLOOD_TRAVEL)
        return start + (target - start) * progress

    def exposed(self, obj):
        right = obj.x + obj.width
        lights = self.lights
        for y in range(int(obj.y), int(obj.y + obj.height)):
            for light in lights:
                if span := light_span(light, y):
                    left, end = max(obj.x, span[0]), min(right, span[1])
                    if left < end:
                        yield Solid(left, y, end - left, 1)

    def collision(self, *, include_crate=True):
        bodies = self.terrain + ((self.crate,) if include_crate and self.crate else ())
        return CollisionWorld(strip for body in bodies for strip in self.exposed(body))

    def move_crate(self, dt, direction, jumping):
        crate = self.crate
        center, feet = crate.x + crate.width / 2, crate.y + crate.height
        world = self.collision(include_crate=False)
        edge = crate.x if direction > 0 else crate.x + crate.width
        touching = abs(self.x + direction * self.WIDTH / 2 - edge) < 1e-6
        dx = 0
        if (direction and self.grounded and not jumping and not self.carrying_lantern and touching
                and abs(self.y - feet) < 6 and self.illuminated(edge, self.y - 5)):
            dx = direction * 38 * dt
        self.crate_vy = min(350, self.crate_vy + 960 * dt)
        x, y, _, landed, _ = world.move(center, feet, crate.width, crate.height, dx, self.crate_vy * dt)
        if landed:
            self.crate_vy = 0.0
        self.crate = replace(crate, x=x - crate.width / 2, y=y - crate.height)
        lamp = self.loose_lantern
        if lamp and crate.x <= lamp.x <= crate.x + crate.width and abs(lamp.y - crate.y) < 1e-6:
            self.loose_lantern = replace(lamp, x=lamp.x + x - center, y=lamp.y + y - feet)

    def _touches(self, obj):
        return (self.x + self.WIDTH / 2 > obj.x and self.x - self.WIDTH / 2 < obj.x + obj.width
                and self.y > obj.y and self.y - self.HEIGHT < obj.y + obj.height)

    def socket_locked(self, socket):
        if socket.properties.get("fixed"):
            return True
        if socket is self.socket and socket.properties.get("releaseInLight"):
            return not self.receiver_lit(socket)
        return False

    @property
    def exit_ready(self):
        return (len(self.collected) == len(self.keys)
                and len(self.lit_beacons) == len(self.beacons)
                and (self.exit_socket is None or self.socket is self.exit_socket)
                and all(self.receiver_lit(receiver) for receiver in self.receivers))

    def interaction(self):
        if self.complete:
            return None
        if self.loose_lantern and (abs(self.x - self.loose_lantern.x) <= 9
                                   and abs(self.y - self.loose_lantern.y) <= 9):
            return self.loose_lantern
        if not self.grounded:
            return None
        sockets = self.sockets if self.carrying_lantern else (self.socket,) if self.socket else ()
        chutes = tuple(o for o in self.chutes
                       if self.carrying_lantern or self.socket is self.chute_targets[o.name])
        switches = tuple(s for s in self.switches
                         if s.name not in self.switch_relays or self.relay_lit(s))
        valves = tuple(v for v in self.valves if self.valve_links[v.name][0] is self.socket)
        candidates = self.projectors + switches + chutes + valves + tuple(
            o for o in sockets if not self.socket_locked(o))
        candidates += tuple(beacon for name, (beacon, _) in self.beacons.items()
                            if name not in self.lit_beacons
                            and self.illuminated(beacon.x, beacon.y - 8))
        return min((o for o in candidates if abs(self.x - o.x) <= 9 and abs(self.y - o.y) <= 2),
                   key=lambda o: abs(self.x - o.x), default=None)

    def interact(self):
        target = self.interaction()
        if target is None:
            if self.carrying_lantern:
                self.loose_lantern = MapObject("Lantern", "LooseLantern", self.x, self.y, 0, 0, {})
                self.lantern_vy = 0.0
        elif target.kind == "LooseLantern":
            self.loose_lantern = None
            self.lantern_vy = 0.0
        elif target.kind == "Beacon":
            self.lit_beacons.add(target.name)
        elif target.kind == "DrainValve":
            _, flood = self.valve_links[target.name]
            if flood != self.drained:
                self.flood_from = {o.name: self.water_depth(o) for o in self.floods}
                self.drain_started = self.elapsed
                self.drained = flood
        elif target.kind in ("Projector", "ProjectorSwitch"):
            name = target.name if target.kind == "Projector" else target.properties["projector"]
            next_index = (self.aim_indices[name] + 1) % len(self.aims[name])
            index = self.selected_focus.get(target.name, next_index)
            if index != self.aim_indices[name]:
                self.turning[name] = self.projected_light(name), self.elapsed
                self.aim_indices[name] = index
        elif target.kind == "Chute":
            if self.carrying_lantern:
                self.in_transit = target, self.chute_targets[target.name], self.elapsed
            else:
                self.socket = None
        else:
            self.socket = None if self.socket else target

    def step(self, dt, direction, jump=False, interact=False):
        if self.complete:
            return
        self.elapsed += dt
        if self.in_transit and self.elapsed - self.in_transit[2] >= self.CHUTE_TRAVEL:
            self.socket = self.in_transit[1]
            self.in_transit = None
        if direction:
            self.facing = direction
        if interact:
            self.interact()
        if self.crate:
            self.move_crate(dt, direction, jump)
            if self.crate.y > self.data.height:
                self.reset()
                return
        collision = self.collision()
        if lamp := self.loose_lantern:
            self.lantern_vy = min(350.0, self.lantern_vy + 960.0 * dt)
            _, feet, _, landed, _ = collision.move(lamp.x, lamp.y, self.LANTERN_WIDTH,
                                                    self.LANTERN_HEIGHT, 0, self.lantern_vy * dt)
            if landed:
                self.lantern_vy = 0.0
            if feet - self.LANTERN_HEIGHT > self.data.height:
                self.reset()
                return
            if feet != lamp.y:
                self.loose_lantern = replace(lamp, y=feet)
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
        if self.y - self.HEIGHT > self.data.height or any(
                flood.x <= self.x < flood.x + flood.width
                and flood.y + flood.height - self.water_depth(flood) < self.y < flood.y + flood.height
                for flood in self.floods):
            self.reset()
            return
        for index, key in enumerate(self.keys):
            if index not in self.collected and any(self._touches(part) for part in self.exposed(key)):
                self.collected.add(index)
        self.complete = (landed and self.exit_ready
                         and self.exit.x <= self.x <= self.exit.x + self.exit.width
                         and self.exit.y <= self.y <= self.exit.y + self.exit.height
                         and self.illuminated(self.x, self.y))
