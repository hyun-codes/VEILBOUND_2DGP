"""좌상단 월드 좌표의 고체 AABB. X/Y를 순서대로 이동하며 지나친 면에서 멈춘다."""

from dataclasses import dataclass


EPSILON = 1e-7


@dataclass(frozen=True)
class Solid:
    x: float
    y: float
    width: float
    height: float
    world: str = "common"
    lamp_state: str = ""


class CollisionWorld:
    def __init__(self, solids, world="real"):
        self.solids = tuple(s for s in solids if s.world in ("common", world))

    def overlaps(self, x, feet, width, height):
        """면 접촉을 제외한 몸체 내부 겹침. 전환 시 임의의 밀어내기는 하지 않는다."""
        return any(x + width / 2 > s.x + EPSILON and x - width / 2 < s.x + s.width - EPSILON
                   and feet > s.y + EPSILON and feet - height < s.y + s.height - EPSILON
                   for s in self.solids)

    def supported(self, x, feet, width):
        return any(abs(feet - s.y) <= EPSILON and
                   x + width / 2 > s.x + EPSILON and x - width / 2 < s.x + s.width - EPSILON
                   for s in self.solids)

    def move(self, x, feet, width, height, dx, dy):
        """반환: 중심 X, 발 Y, 옆면 충돌, 착지, 천장 충돌. 초기 겹침은 보정하지 않는다."""
        target_x = x + dx
        for s in self.solids:
            if feet <= s.y + EPSILON or feet - height >= s.y + s.height - EPSILON:
                continue
            if dx > 0 and x + width / 2 <= s.x + EPSILON:
                target_x = min(target_x, s.x - width / 2)
            elif dx < 0 and x - width / 2 >= s.x + s.width - EPSILON:
                target_x = max(target_x, s.x + s.width + width / 2)
        side = abs(target_x - (x + dx)) > EPSILON
        target_y = feet + dy
        for s in self.solids:
            if target_x + width / 2 <= s.x + EPSILON or target_x - width / 2 >= s.x + s.width - EPSILON:
                continue
            if dy > 0 and feet <= s.y + EPSILON:
                target_y = min(target_y, s.y)
            elif dy < 0 and feet - height >= s.y + s.height - EPSILON:
                target_y = max(target_y, s.y + s.height + height)
        vertical = abs(target_y - (feet + dy)) > EPSILON
        return target_x, target_y, side, vertical and dy > 0, vertical and dy < 0
