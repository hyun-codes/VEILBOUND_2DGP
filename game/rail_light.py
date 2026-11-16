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
        self.pause = pause
        forward = []
        distance = 0.0
        for a, b in zip(self.points, self.points[1:]):
            length = hypot(a[0] - b[0], a[1] - b[1])
            if length == 0:
                raise MapFormatError("Adjacent rail points must differ")
            forward.append((a, b, distance, distance + length, length / speed))
            distance += length
        self.legs = forward + [(b, a, end, start, duration)
                               for a, b, start, end, duration in reversed(forward)]
        self.period = sum(pause + duration for _, _, _, _, duration in self.legs)

    def at(self, elapsed):
        x, y, _ = self._sample(elapsed)
        return x, y, self.radius

    def distance_at(self, elapsed):
        return self._sample(elapsed)[2]

    def _sample(self, elapsed):
        elapsed %= self.period
        for (ax, ay), (bx, by), start, end, duration in self.legs:
            if elapsed < self.pause + duration:
                t = max(0, (elapsed - self.pause) / duration)
                return ax + (bx - ax) * t, ay + (by - ay) * t, start + (end - start) * t
            elapsed -= self.pause + duration
        x, y = self.points[0]
        return x, y, 0.0
