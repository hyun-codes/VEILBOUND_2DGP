"""실제 SDL 입력으로 가로등 퍼즐을 풀고 원형 완료·재시작을 검사한다."""

import argparse
import ctypes
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.app import Game, STAGE_1, STAGE_2, WIDTH, HEIGHT
from game.map_loader import load_map
from game.pico2d_backend import Pico2DBackend
from native_movement_check import ScriptedBackend
from stage2_route import LampRoute
from game.stage_manager import StageManager


class LampBackend(ScriptedBackend):
    def __init__(self, game, output):
        super().__init__(game, output, "real")
        self.route = LampRoute()
        self.captured = set()
        self.finished = False
        self.restarted = False
        self.stage1_phase = 0

    def poll_events(self):
        s, g = self.sdl, self.game
        if self.frames == 0 or g.paused:
            event = s.SDL_Event()
            event.type = s.SDL_WINDOWEVENT
            event.window.event = s.SDL_WINDOWEVENT_FOCUS_GAINED
            assert s.SDL_PushEvent(ctypes.byref(event)) == 1
        mapping = {"d": s.SDLK_d, "e": s.SDLK_e, "space": s.SDLK_SPACE, "shift_left": s.SDLK_LSHIFT}
        if g.stage_number == 1:
            if self.stage1_phase == 0:
                self.push_key(s.SDLK_d)
                self.stage1_phase = 1
            elif self.stage1_phase == 1 and g.player.x >= 100:
                self.push_key(s.SDLK_LSHIFT)
                self.push_key(s.SDLK_LSHIFT, False)
                self.stage1_phase = 2
            elif self.stage1_phase == 2 and g.player_at_exit():
                self.push_key(s.SDLK_d, False)
                self.push_key(s.SDLK_LSHIFT)
                self.push_key(s.SDLK_LSHIFT, False)
                self.stage1_phase = 3
        elif not self.finished:
            for key, down in self.route.commands(g):
                self.push_key(mapping[key], down)
            if self.route.phase == 13:
                assert g.stage_number == 2 and g.completed and g.scene.world == "real"
                assert g.respawns == 0
                self.finished = True
        elif "clear" in self.captured and not self.restarted:
            self.push_key(s.SDLK_r)
            self.restarted = True
        elif self.restarted and not g.completed:
            assert g.puzzle.mode == "bridge" and g.scene.world == "real"
            assert g.puzzle.light_mode == "near"
            assert (g.player.x, g.player.y) == (28, 183)
            event = s.SDL_Event()
            event.type = s.SDL_QUIT
            assert s.SDL_PushEvent(ctypes.byref(event)) == 1
        return Pico2DBackend.poll_events(self)

    def present(self):
        g = self.game
        name = None
        if g.stage_number == 1:
            name = "stage1"
        elif "start" not in self.captured:
            name = "start"
        elif self.route.phase in (3, 4):
            name = "stairs"
        elif self.route.phase == 10:
            name = "upper_control"
        elif self.route.phase == 11 and g.player.x > 270:
            name = "bridge"
        elif self.route.phase == 11.2:
            name = "island"
        elif self.route.phase == 11.4 and g.player.x > 350:
            name = "rear_bridge"
        elif g.completed:
            name = "clear"
        if name and name not in self.captured:
            self.save_screenshot(self.output / f"stage2_{name}.bmp", WIDTH, HEIGHT)
            self.captured.add(name)
        self.frames += 1
        Pico2DBackend.present(self)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--from-stage1", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    game = Game(load_map(STAGE_1 if args.from_stage1 else STAGE_2),
                stages=StageManager({"Stage2": STAGE_2}) if args.from_stage1 else None)
    backend = LampBackend(game, output)
    game.run(backend, max_frames=900)
    assert backend.finished and backend.restarted and not game.running, (backend.route.phase, game.player.x, game.player.y, game.respawns)
    if args.from_stage1:
        assert backend.stage1_phase == 3
    print("Native Stage 2 OK:", backend.route.records, "captures:", sorted(backend.captured), "frames:", backend.frames)


if __name__ == "__main__":
    main()
