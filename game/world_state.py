"""현실/그림자 전환 규칙. 객체 목록 관리자인 GameWorld와는 별개다."""

from game.collision import CollisionWorld


class WorldState:
    def __init__(self, solids, initial="real"):
        self._collisions = {name: CollisionWorld(solids, name) for name in ("real", "shadow")}
        self.reset(initial)

    @property
    def collision(self):
        return self._collisions[self.name]

    def reset(self, initial="real"):
        if initial not in self._collisions:
            raise ValueError("World must be real or shadow")
        self.name = initial

    def try_toggle(self, player):
        target = "shadow" if self.name == "real" else "real"
        collision = self._collisions[target]
        if collision.overlaps(player.x, player.y, player.WIDTH, player.HEIGHT):
            return False
        self.name = target
        player.collision = collision
        # 전환이 사라진 발판의 점프 권한을 남기거나 새 공중 점프 권한을 만들지 않는다.
        if player.grounded and not collision.supported(player.x, player.y, player.WIDTH):
            player.grounded = False
            player.coyote = 0.0
        elif not player.grounded and not collision.supported(*player.last_support, player.WIDTH):
            player.coyote = 0.0
        return True
