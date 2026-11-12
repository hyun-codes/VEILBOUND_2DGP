from collections import deque
import unittest

from game.app import Game, STAGE_2, STAGE_3
from game.pico2d_backend import InputEvent
from game.stage_manager import StageManager
from stage3_route import SolverRoute
from tools.solve_stage3 import DT, Solver


class VerticalStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solvers = [Solver(path) for path in (STAGE_2, STAGE_3)]
        cls.solutions = [solver.solve() for solver in cls.solvers]

    def test_input_route_climbs_both_maps_and_enters_stage_three(self):
        game = Game(self.solvers[0].data, stages=StageManager({"Stage3": STAGE_3}))
        for number, solver, solution, rise in zip((2, 3), self.solvers, self.solutions, (384, 768)):
            with self.subTest(stage=number):
                self.assertEqual(game.stage_number, number)
                self.assertEqual(solution["dead_states"], [])
                self.assertGreaterEqual(sum(a["kind"] == "shift" for a in solution["route"]), 2)
                route = SolverRoute(solution, game.data)
                min_feet = start = game.player.y
                budget = sum(a.get("ticks", 0) for a in solution["route"]) + 8 * len(solution["route"])
                for _ in range(budget):
                    game.handle_events([InputEvent("key_down" if down else "key_up", key)
                                        for key, down in route.commands(game)])
                    game.step(DT)
                    if game.stage_number != number or game.completed:
                        break
                    min_feet = min(min_feet, game.player.y)
                    self.assertEqual(game.respawns, 0)
                self.assertTrue(game.stage_number == 3 if number == 2 else game.completed)
                self.assertGreaterEqual(start - min_feet, rise)

    def test_elevated_shortcuts_rejoin_the_main_route_in_real_world(self):
        for solver in self.solvers:
            forks = [name for name in solver.nodes if name.startswith("Fork ")]
            self.assertTrue(forks)
            for fork in forks:
                with self.subTest(map=solver.data.path.name, fork=fork):
                    rejoin = fork.replace("Fork", "Rejoin")
                    main_y = solver.nodes[fork].y
                    seen, pending = {fork}, deque([fork])
                    while pending:
                        source = pending.popleft()
                        for target in solver.links[source]:
                            if target in seen or (target != rejoin and solver.nodes[target].y >= main_y):
                                continue
                            if solver.probe(source, target, "real", "bridge", "near"):
                                seen.add(target)
                                pending.append(target)
                    self.assertIn(rejoin, seen)
