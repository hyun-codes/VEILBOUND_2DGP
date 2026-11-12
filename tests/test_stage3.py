import hashlib
import json
from collections import deque
import unittest

from game.app import Game, STAGE_2_DRAFT as STAGE_2, STAGE_3_DRAFT as STAGE_3
from game.map_loader import load_map
from game.pico2d_backend import InputEvent
from game.stage_manager import StageManager
from game.timing import FixedStepper
from tools.solve_stage3 import Solver, DT
from stage3_route import SolverRoute


class Stage3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solver = Solver()
        cls.solution = cls.solver.solve()

    def test_saved_solution_matches_actual_map_and_all_reachable_safe_states_recover(self):
        saved = json.loads((STAGE_3.parent / "solution.json").read_text(encoding="utf-8"))
        self.assertEqual(self.solution, saved)
        self.assertEqual(saved["map_sha256"], hashlib.sha256(STAGE_3.read_bytes()).hexdigest())
        self.assertFalse(saved["dead_states"])
        self.assertEqual(saved["reachable_states"], saved["recoverable_states"])
        self.assertGreaterEqual(saved["shortest_macro_actions"], 20)

    def test_both_lamp_controls_and_world_switch_are_required_in_authored_graph(self):
        for blocked in ("A", "B", "shift", "lever"):
            seen, queue = {self.solver.start}, deque([self.solver.start])
            while queue:
                for target, action in self.solver.neighbors(queue.popleft()):
                    if action.get("lamp") == blocked or action.get("device") == blocked or action["kind"] == blocked:
                        continue
                    if target not in seen:
                        seen.add(target)
                        queue.append(target)
            self.assertFalse(any(s[0] == "Goal" and s[1] == "real" for s in seen), blocked)

    def test_solver_route_replays_without_teleport_and_is_identical_at_30_60_fps(self):
        results = []
        for fps in (30, 60):
            g = Game(self.solver.data)
            route, clock, ticks = SolverRoute(self.solution, g.data), FixedStepper(), []
            def update(dt):
                g.handle_events([InputEvent("key_down" if down else "key_up", key)
                                 for key, down in route.commands(g)])
                g.step(dt)
                ticks.append((g.player.x, g.player.y, g.scene.world, g.puzzle.mode, g.puzzle.light_mode,
                              g.mechanism.progress, g.completed))
            for _ in range(fps * 30):
                clock.advance(1 / fps, update)
            self.assertTrue(g.completed, (route.index, g.player.x, g.player.y, g.respawns))
            self.assertEqual(g.respawns, 0)
            results.append(ticks)
        self.assertEqual(*results)

    def test_stage2_exit_enters_stage3_and_restart_stays_there(self):
        g = Game(load_map(STAGE_2), stages=StageManager({"Stage3": STAGE_3}))
        g.player.x, g.player.y = 436, 135  # 포털 연결만 분리 검사한다.
        g.step(DT)
        self.assertEqual(g.stage_number, 3)
        self.assertEqual((g.player.x, g.player.y), (28, 247))
        g.restart()
        self.assertEqual(g.stage_number, 3)
        self.assertEqual((g.puzzle.mode, g.puzzle.light_mode), ("bridge", "near"))

    def test_replay_waits_for_physics_before_sending_the_next_toggle(self):
        g = Game(self.solver.data)
        route = SolverRoute(self.solution, g.data)
        route.index = next(i for i, a in enumerate(route.route) if a["kind"] == "e")
        g.player.x = 88
        for _ in range(3):
            events = [InputEvent("key_down" if down else "key_up", key) for key, down in route.commands(g)]
            g.handle_events(events)
        self.assertEqual(g.pending_interactions, 1)
        self.assertEqual(g.pending_switches, 0)
        g.step(DT)
        self.assertEqual(g.puzzle.light_mode, "far")
        route.commands(g)
        self.assertFalse(route.waiting)
