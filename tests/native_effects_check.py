"""실제 SDL의 Shift/F3/R 입력으로 세계 연출과 동작 줄이기를 확인한다."""

import argparse
import ctypes
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.app import Game, STAGE_1, WIDTH, HEIGHT
from game.map_loader import load_map
from game.pico2d_backend import Pico2DBackend
from native_movement_check import ScriptedBackend


class EffectsBackend(ScriptedBackend):
    def poll_events(self):
        s, n, g = self.sdl, self.frames, self.game
        if n == 0 or g.paused:
            event = s.SDL_Event()
            event.type = s.SDL_WINDOWEVENT
            event.window.event = s.SDL_WINDOWEVENT_FOCUS_GAINED
            assert s.SDL_PushEvent(ctypes.byref(event)) == 1
        commands = {3: (s.SDLK_LSHIFT, True), 4: (s.SDLK_LSHIFT, False),
                    20: (s.SDLK_F3, True), 21: (s.SDLK_F3, False),
                    30: (s.SDLK_r, True), 31: (s.SDLK_r, False),
                    35: (s.SDLK_LSHIFT, True), 36: (s.SDLK_LSHIFT, False),
                    55: (s.SDLK_F3, True), 56: (s.SDLK_F3, False)}
        if n in commands:
            self.push_key(*commands[n])
        if n == 80:
            event = s.SDL_Event()
            event.type = s.SDL_QUIT
            assert s.SDL_PushEvent(ctypes.byref(event)) == 1
        return Pico2DBackend.poll_events(self)

    def present(self):
        n, g = self.frames, self.game
        if n == 15:
            assert g.scene.world == "shadow" and g.effects.shadow == 1
        if n == 21:
            assert not g.effects.motion_enabled
            self.frozen = (g.effects.clock, g.effects.fog_offset)
        if n == 26:
            assert self.frozen == (g.effects.clock, g.effects.fog_offset)
        if n == 31:
            assert not g.effects.motion_enabled and g.scene.world == "real"
            assert (g.effects.clock, g.effects.fog_offset, g.effects.notice) == (0, 0, 0)
        if n == 50:
            assert not g.effects.motion_enabled and g.scene.world == "shadow"
            assert g.effects.shadow == 1 and g.effects.clock == 0
        if n == 70:
            assert g.effects.motion_enabled and g.effects.clock > 0
        if n in (0, 5, 15, 26, 50, 70):
            self.save_screenshot(self.output / f"effects_{n:02}.bmp", WIDTH, HEIGHT)
        self.frames += 1
        Pico2DBackend.present(self)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    game = Game(load_map(STAGE_1))
    backend = EffectsBackend(game, output, "real")
    game.run(backend, max_frames=100)
    assert backend.frames == 80 and not game.running and not backend.opened
    print("Native effects OK: Shift palette/ripple, F3 motion OFF/ON, restart preference, close")


if __name__ == "__main__":
    main()
