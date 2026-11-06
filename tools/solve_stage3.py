"""Tiled의 안전 지점·연결 후보를 실제 Player 물리로 검사하고 상태 그래프를 BFS 탐색한다.

보수적인 지점 그래프이며 모든 연속 좌표·공중 전환·순찰 시간의 완전 탐색은 아니다.
"""

from collections import deque
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game.app import STAGE_3, PLAYER_ANIMATIONS
from game.collision import CollisionWorld
from game.lamp_puzzle import LampPuzzle
from game.map_loader import load_map
from game.player import AnimationSet, Player
from game.lever_gate import LeverGate, nearest_control

DT = 1 / 60


class Travel:
    """좌표 도착을 종료 조건으로 삼는 입력. 물리 검사와 입력 재생에서 공유한다."""
    def __init__(self, x, y, start_x, jump_x=None):
        self.x, self.y, self.jump_x = x, y, jump_x
        self.direction = 1 if x > start_x else -1
        self.jumped = False

    def done(self, player):
        return abs(player.x - self.x) <= 1.1 and abs(player.y - self.y) < 1e-6 and player.grounded

    def input(self, player):
        direction = 0 if abs(player.x - self.x) <= 1.1 else (1 if self.x > player.x else -1)
        if self.jump_x is not None and not self.jumped and (player.x - self.jump_x) * self.direction >= -0.01:
            self.jumped = True
        return direction, self.jumped


class Solver:
    def __init__(self, path=STAGE_3):
        self.data = load_map(path)
        self.puzzle = LampPuzzle(self.data)
        self.mechanism = LeverGate(self.data)
        self.animations = AnimationSet(PLAYER_ANIMATIONS)
        self.nodes = {o.name: o for o in self.data.objects if o.kind == "PuzzleNode"}
        self.links = {name: [] for name in self.nodes}
        for obj in self.data.objects:
            if obj.kind == "PuzzleLink":
                a, b = obj.properties["source"], obj.properties["target"]
                if a not in self.nodes or b not in self.nodes:
                    raise ValueError("PuzzleLink references a missing node")
                self.links[a].append(b)
                self.links[b].append(a)
        self.start = (self.data.properties["solverStart"], "real", self.puzzle.mode, self.puzzle.light_mode, False)
        self.goal_name = self.data.properties["solverGoal"]
        start, goal = self.nodes[self.start[0]], self.nodes[self.goal_name]
        actual_start, exit_area = self.data.object_named("PlayerStart"), self.data.object_named("Exit")
        if (start.x, start.y) != (actual_start.x, actual_start.y):
            raise ValueError("Solver start differs from PlayerStart")
        if not (goal.x + Player.WIDTH / 2 > exit_area.x and goal.x - Player.WIDTH / 2 < exit_area.x + exit_area.width
                and goal.y > exit_area.y and goal.y - Player.HEIGHT < exit_area.y + exit_area.height):
            raise ValueError("Solver goal is outside Exit")
        self.cache = {}
        self.collisions = {}
        for a in ("stairs", "bridge"):
            for b in ("near", "far"):
                self.puzzle.mode, self.puzzle.light_mode = a, b
                for opened in (False, True):
                    layout = self.mechanism.compose(self.puzzle.data, open_state=opened)
                    for world in ("real", "shadow"):
                        self.collisions[world, a, b, opened] = CollisionWorld(layout.solids, world)

    def stable(self, name, world, a, b, opened=False):
        node, collision = self.nodes[name], self.collisions[world, a, b, opened]
        return collision.supported(node.x, node.y, Player.WIDTH) and not collision.overlaps(
            node.x, node.y, Player.WIDTH, Player.HEIGHT)

    def probe(self, source, target, world, a, b, opened=False):
        collision = self.collisions[world, a, b, opened]
        key = source, target, collision.solids
        if key in self.cache:
            return self.cache[key]
        src, dst = self.nodes[source], self.nodes[target]
        # 최대 상승량을 넘는 링크에는 점프를 시도하지 않는다.
        candidates = [None]
        if src.y - dst.y <= 27:
            direction = 1 if dst.x > src.x else -1
            candidates += [src.x + direction * Player.SPEED * DT * t
                           for t in range(int(abs(dst.x - src.x) / (Player.SPEED * DT)) + 1)]
        for jump_x in candidates:
            player = Player(self.animations, collision, self.data.width, (src.x, src.y))
            travel = Travel(dst.x, dst.y, src.x, jump_x)
            for tick in range(600):
                if travel.done(player):
                    result = {"kind": "move", "node": target, "jump_x": jump_x, "ticks": tick}
                    self.cache[key] = result
                    return result
                direction, held = travel.input(player)
                if held and not player.jump_held:
                    player.request_jump()
                player.direction, player.jump_held = direction, held
                old_x = player.x
                player.update(DT)
                if direction and abs(player.x - old_x) < 1e-8 and player.grounded:
                    break
                if player.y > self.data.height + Player.HEIGHT or (player.y > max(src.y, dst.y) + 32):
                    break
        self.cache[key] = None
        return None

    def neighbors(self, state):
        name, world, a, b, opened = state
        other = "shadow" if world == "real" else "real"
        if self.stable(name, other, a, b, opened):
            yield (name, other, a, b, opened), {"kind": "shift"}
        node = self.nodes[name]
        if world == "real":
            # 실행과 같은 근접·높이 조건으로 가장 가까운 조작점을 선택한다.
            kind, control = nearest_control(node, self.puzzle, self.mechanism)
            if kind == "lever" and not opened:
                yield (name, world, a, b, True), {"kind": "e", "device": "lever", "wait_for": "gate_open"}
            elif kind == "lamp":
                aa, bb = a, b
                if control.properties.get("lamp", "A") == "A":
                    aa = "bridge" if a == "stairs" else "stairs"
                else:
                    bb = "far" if b == "near" else "near"
                if self.stable(name, world, aa, bb, opened):
                    yield (name, world, aa, bb, opened), {"kind": "e", "lamp": control.properties.get("lamp", "A")}
        for target in self.links[name]:
            if self.stable(target, world, a, b, opened):
                action = self.probe(name, target, world, a, b, opened)
                if action:
                    yield (target, world, a, b, opened), action

    def solve(self):
        if not self.stable(*self.start):
            raise ValueError("Solver start has no safe support")
        queue, previous, edges = deque([self.start]), {self.start: None}, {}
        while queue:
            state = queue.popleft()
            edges[state] = list(self.neighbors(state))
            for target, action in edges[state]:
                if target not in previous:
                    previous[target] = state, action
                    queue.append(target)
        goals = [s for s in previous if s[0] == self.goal_name and s[1] == "real"]
        if not goals:
            raise ValueError("No solution in the authored safe-node graph")
        goal = goals[0]
        route, cursor = [], goal
        while previous[cursor] is not None:
            source, action = previous[cursor]
            route.append(dict(source=list(source), target=list(cursor), **action))
            cursor = source
        route.reverse()
        # 목표로 역탐색하여 방문한 안전 지점 상태의 복구 가능성을 검사한다.
        reverse = {s: [] for s in previous}
        for state, next_states in edges.items():
            for target, _ in next_states:
                reverse[target].append(state)
        recoverable, queue = set(goals), deque(goals)
        while queue:
            for state in reverse[queue.popleft()]:
                if state not in recoverable:
                    recoverable.add(state)
                    queue.append(state)
        return {"map": self.data.path.name, "map_sha256": hashlib.sha256(self.data.path.read_bytes()).hexdigest(),
                "model": "authored_safe_nodes_world_A_B_gate_with_actual_player_probes",
                "reachable_states": len(previous), "recoverable_states": len(recoverable),
                "dead_states": [list(s) for s in previous if s not in recoverable],
                "shortest_macro_actions": len(route), "route": route,
                "limits": "Not exhaustive continuous physics, airborne switches, falls or timed enemies; BFS minimizes macro actions, not time"}


if __name__ == "__main__":
    result = Solver().solve()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "route"}, ensure_ascii=False, indent=2))
    for step in result["route"]:
        print(step)
