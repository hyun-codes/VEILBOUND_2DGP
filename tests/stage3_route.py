"""BFS 결과를 실제 키 입력으로 재생한다. 플레이어 위치·속도를 수정하지 않는다."""

from tools.solve_stage3 import Travel


class SolverRoute:
    def __init__(self, solution, data):
        self.route = solution["route"]
        self.nodes = {o.name: o for o in data.objects if o.kind == "PuzzleNode"}
        self.index = 0
        self.travel = None
        self.held = set()
        self.waiting = False

    def keys(self, desired):
        changes = [(key, False) for key in sorted(self.held - desired)]
        changes += [(key, True) for key in sorted(desired - self.held)]
        self.held = desired
        return changes

    def commands(self, game):
        if game.completed or self.index == len(self.route):
            return self.keys(set())
        action = self.route[self.index]
        if action["kind"] != "move":
            if self.waiting:
                expected = tuple(action["target"][1:])
                if (game.scene.world, game.puzzle.mode, game.puzzle.light_mode) == expected:
                    self.index += 1
                    self.waiting = False
                return self.keys(set())
            changes = self.keys(set())
            key = "e" if action["kind"] == "e" else "shift_left"
            self.waiting = True
            return changes + [(key, True), (key, False)]
        if self.travel is None:
            node = self.nodes[action["node"]]
            self.travel = Travel(node.x, node.y, game.player.x, action["jump_x"])
        if self.travel.done(game.player):
            self.index += 1
            self.travel = None
            return self.keys(set())
        direction, jump = self.travel.input(game.player)
        desired = {"d"} if direction > 0 else {"a"} if direction < 0 else set()
        if jump:
            desired.add("space")
        return self.keys(desired)
