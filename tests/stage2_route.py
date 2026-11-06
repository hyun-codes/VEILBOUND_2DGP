"""자동 검사와 실제 SDL 검사에서 공유하는 좌표 기반의 합법적인 입력 경로."""


class LampRoute:
    def __init__(self):
        self.phase = 0
        self.records = []

    def commands(self, game):
        p = game.player
        # 반환 (키, 누름 여부). 위치를 순간 이동하거나 물리 상태를 조작하지 않는다.
        if self.phase == 0:
            self.phase = 1
            return [("d", True)]
        if self.phase == 1 and p.x >= 80:
            self.phase = 2
            return [("d", False), ("e", True), ("e", False)]
        if self.phase == 2 and game.puzzle.mode == "stairs":
            self.phase = 2.5
            return [("shift_left", True), ("shift_left", False)]
        if self.phase == 2.5 and game.scene.world == "shadow":
            self.records.append("stairs")
            self.phase = 3
            return [("d", True)]
        if self.phase in (3, 5, 7) and p.x >= {3: 98, 5: 122, 7: 148}[self.phase] and p.grounded:
            self.phase += 1
            return [("space", True)]
        if self.phase in (4, 6, 8) and p.grounded and p.y == {4: 167, 6: 151, 8: 135}[self.phase]:
            self.records.append(f"land_{self.phase}")
            self.phase += 1
            return [("space", False)]
        if self.phase == 9 and p.x >= 176:
            self.phase = 10
            return [("d", False), ("shift_left", True), ("shift_left", False), ("e", True), ("e", False)]
        if self.phase == 10 and game.scene.world == "real" and game.puzzle.mode == "bridge":
            self.records.append("upper_bridge")
            self.phase = 10.2
            return [("d", True)]
        if self.phase == 10.2 and p.x >= 204:
            self.phase = 10.3
            return [("d", False), ("e", True), ("e", False)]
        if self.phase == 10.3 and game.puzzle.light_mode == "far":
            self.records.append("light_far")
            self.phase = 11
            return [("shift_left", True), ("shift_left", False), ("d", True)]
        if self.phase == 11 and p.x >= 312:
            self.phase = 11.2
            return [("d", False), ("shift_left", True), ("shift_left", False), ("e", True), ("e", False)]
        if self.phase == 11.2 and game.scene.world == "real" and game.puzzle.light_mode == "near":
            self.records.append("island_light_near")
            self.phase = 11.4
            return [("shift_left", True), ("shift_left", False), ("d", True)]
        if self.phase == 11.4 and game.player_at_exit():
            assert not game.completed
            self.records.append("shadow_exit_off")
            self.phase = 12
            return [("d", False), ("shift_left", True), ("shift_left", False)]
        if self.phase == 12 and game.completed:
            self.phase = 13
            self.records.append("clear")
        return []
