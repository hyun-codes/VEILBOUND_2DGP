"""Quarter-turn geometry with a continuous, physics-paused crank animation."""
from math import cos, isfinite, pi, sin

from game.map_loader import MapFormatError


class RotatingChamber:
    TURN_TIME = 0.75

    def __init__(self, pivot):
        self.x, self.y = pivot.x, pivot.y
        self.size = pivot.properties.get('size', 128)
        self.frame_size = pivot.properties.get('frameSize', self.size)
        self.exit_orientation = pivot.properties.get('exitOrientation', 2)
        if (type(self.size) is not int or self.size <= 0 or self.size % 2
                or type(self.frame_size) is not int or self.frame_size < self.size or self.frame_size % 2
                or type(self.exit_orientation) is not int or self.exit_orientation not in range(4)
                or not all(isfinite(v) and float(v).is_integer() for v in (self.x, self.y))):
            raise MapFormatError('A room pivot needs integer coordinates, an even size and exitOrientation 0..3')
        self.reset()

    def reset(self):
        self.orientation = 0
        self.direction = 0
        self.elapsed = 0.0

    @property
    def turning(self):
        return self.direction != 0

    @property
    def angle(self):
        progress = min(1, self.elapsed / self.TURN_TIME) if self.turning else 0
        ease = progress * progress * (3 - 2 * progress)
        return (self.orientation + self.direction * ease) * pi / 2

    def begin(self, direction):
        if direction not in (-1, 1) or self.turning:
            return
        self.direction, self.elapsed = direction, 0.0

    def advance(self, dt):
        self.elapsed += dt
        if self.turning and self.elapsed + 1e-9 >= self.TURN_TIME:
            self.orientation = (self.orientation + self.direction) % 4
            self.direction = 0
            self.elapsed = 0.0
            return True
        return False

    def contains(self, x, y):
        return abs(x - self.x) <= self.size / 2 and abs(y - self.y) <= self.size / 2

    def point(self, x, y, *, turns=None):
        turns = self.orientation if turns is None else turns
        dx, dy = x - self.x, y - self.y
        for _ in range(turns % 4):
            dx, dy = -dy, dx
        return self.x + dx, self.y + dy

    def animated_point(self, x, y, *, original=False):
        angle = self.angle if original else self.angle - self.orientation * pi / 2
        dx, dy = x - self.x, y - self.y
        return self.x + dx*cos(angle) - dy*sin(angle), self.y + dx*sin(angle) + dy*cos(angle)

    def rectangle(self, obj):
        points = [self.point(x, y) for x in (obj.x, obj.x + obj.width)
                  for y in (obj.y, obj.y + obj.height)]
        left, top = min(x for x, _ in points), min(y for _, y in points)
        return left, top, max(x for x, _ in points) - left, max(y for _, y in points) - top
