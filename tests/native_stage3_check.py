"""저장된 BFS 해법을 실제 SDL 키 이벤트로 재생한다."""

import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.app import Game, STAGE_3, WIDTH, HEIGHT
from game.map_loader import load_map
from game.pico2d_backend import Pico2DBackend
from native_movement_check import ScriptedBackend
from stage3_route import SolverRoute


class Backend(ScriptedBackend):
    def __init__(self, game, output, solution):
        super().__init__(game, output, "real")
        self.route = SolverRoute(solution, game.data)
        self.captured = set()
        self.restarted = False
        self.passed_gate = False

    def poll_events(self):
        s, g = self.sdl, self.game
        if self.frames == 0 or g.paused:
            event = s.SDL_Event()
            event.type = s.SDL_WINDOWEVENT
            event.window.event = s.SDL_WINDOWEVENT_FOCUS_GAINED
            assert s.SDL_PushEvent(ctypes.byref(event)) == 1
        if "clear" in self.captured and not self.restarted:
            assert g.completed and g.respawns == 0
            assert g.mechanism.is_open and self.passed_gate
            self.push_key(s.SDLK_r)
            self.restarted = True
        elif self.restarted:
            assert g.stage_number == 3 and not g.completed
            assert (g.player.x, g.player.y, g.scene.world) == (28, 247, "real")
            assert (g.puzzle.mode, g.puzzle.light_mode) == ("bridge", "near")
            assert not g.mechanism.activated and not g.mechanism.is_open
            event = s.SDL_Event()
            event.type = s.SDL_QUIT
            assert s.SDL_PushEvent(ctypes.byref(event)) == 1
        else:
            keys = {"a": s.SDLK_a, "d": s.SDLK_d, "space": s.SDLK_SPACE,
                    "e": s.SDLK_e, "shift_left": s.SDLK_LSHIFT}
            for key, down in self.route.commands(g):
                self.push_key(keys[key], down)
        return Pico2DBackend.poll_events(self)

    def present(self):
        g, i = self.game, self.route.index
        name = "start" if self.frames == 0 else None
        if i == 4 and g.player.x > 150:
            name = "lower_bridge"
        elif g.scene.world == "shadow" and g.player.x > 410 and 175 <= g.player.y <= 231:
            name = "stairs"
        elif g.player.x > 504 and g.player.y == 167:
            name = "upper_right"
        elif g.scene.world == "real" and g.player.y == 167 and 380 < g.player.x < 430:
            name = "real_return"
            if g.player.x < 392 and g.mechanism.is_open:
                self.passed_gate = True
        elif g.scene.world == "shadow" and g.player.y == 167 and g.player.x < 220:
            name = "shadow_return"
        if g.mechanism.nearby_control(g.player):
            if not g.mechanism.activated:
                name = "lever_ready"
            elif 0.09 <= g.mechanism.age <= 0.15:
                name = "gate_opening"
            elif g.mechanism.is_open:
                name = "lever_open"
        if g.completed:
            name = "clear"
        if name and name not in self.captured:
            self.save_screenshot(self.output / f"stage3_{name}.bmp", WIDTH, HEIGHT)
            self.captured.add(name)
        self.frames += 1
        Pico2DBackend.present(self)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    solution = json.loads((STAGE_3.parent / "solution.json").read_text(encoding="utf-8"))
    assert solution["map_sha256"] == hashlib.sha256(STAGE_3.read_bytes()).hexdigest()
    game = Game(load_map(STAGE_3))
    backend = Backend(game, args.output.resolve(), solution)
    game.run(backend, max_frames=2400)
    assert backend.restarted and not game.running, (backend.route.index, game.player.x, game.player.y)
    print("Native Stage 3 OK: BFS route, zero falls, real-only exit, restart; frames", backend.frames,
          "captures", sorted(backend.captured))
