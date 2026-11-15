"""A spotlight following ordered waypoints, with a pause at each landing."""

from math import hypot, isfinite

from game.map_loader import MapFormatError


class RailLight:
    def __init__(self, data, points):
        settings = data.properties
        self.radius = settings.get("railRadius", 38)
        speed = settings.get("railSpeed", 28)
        pause = settings.get("railPause", 1.2)
        if (len(points) < 2 or not all(isinstance(n, (int, float)) and isfinite(n) and n > 0
                                      for n in (self.radius, speed, pause))
                or any(not (0 <= p.x < data.width and 0 <= p.y < data.height) for p in points)):
            raise MapFormatError("A rail light needs at least two in-bounds points and positive timing")
        self.points = tuple((p.x, p.y) for p in points)
        loop = self.points + self.points[-2::-1]
        self.legs = []
        for a, b in zip(loop, loop[1:]):
            duration = hypot(a[0] - b[0], a[1] - b[1]) / speed
            if duration == 0:
                raise MapFormatError("Adjacent rail points must differ")
            self.legs.append((a, b, pause, duration))
        self.period = sum(pause + duration for _, _, pause, duration in self.legs)

    def at(self, elapsed):
        elapsed %= self.period
        for (ax, ay), (bx, by), pause, duration in self.legs:
            if elapsed < pause + duration:
                t = max(0, (elapsed - pause) / duration)
                return ax + (bx - ax) * t, ay + (by - ay) * t, self.radius
            elapsed -= pause + duration
        x, y = self.points[0]
        return x, y, self.radius
