"""명시적으로 실행하는 실제 SDL 통합 점검. unittest 자동 검색에서는 창을 열지 않는다.

python tests/native_movement_check.py --output <캡처 폴더>
사람이 조작한 플레이 테스트와 구분하며 SDL 큐에 시험 입력을 넣는다.
"""

import argparse
import ctypes
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.app import Game, STAGE_1, WIDTH, HEIGHT
from game.map_loader import load_map
from game.pico2d_backend import Pico2DBackend


class ScriptedBackend(Pico2DBackend):
    def __init__(self, game, output, world):
        super().__init__()
        self.game, self.output, self.world = game, output, world
        self.frames = 0
        self.seen = []
        self.snapshots = {}

    def push_key(self, key, down=True, repeat=0):
        event = self.sdl.SDL_Event()
        event.type = self.sdl.SDL_KEYDOWN if down else self.sdl.SDL_KEYUP
        event.key.keysym.sym = key
        event.key.repeat = repeat
        assert self.sdl.SDL_PushEvent(ctypes.byref(event)) == 1

    def poll_events(self):
        sdl, n = self.sdl, self.frames
        if n == 0 or self.game.paused:
            event = sdl.SDL_Event()
            event.type = sdl.SDL_WINDOWEVENT
            event.window.event = sdl.SDL_WINDOWEVENT_FOCUS_GAINED
            assert sdl.SDL_PushEvent(ctypes.byref(event)) == 1
            self.push_key(sdl.SDLK_RIGHT)
        elif self.world == "shadow" and "right" not in self.game.keys:
            # OS의 비동기 창 포커스 알림 뒤에는 새 누름으로 시험 입력을 재개한다.
            self.push_key(sdl.SDLK_RIGHT)
        if self.world == "real":
            if n == 30:
                self.push_key(sdl.SDLK_SPACE)
            if n == 31:
                self.push_key(sdl.SDLK_SPACE, repeat=1)
            if n == 32:
                self.push_key(sdl.SDLK_SPACE, down=False)
            if n == 68:
                self.push_key(sdl.SDLK_RIGHT, down=False)
                self.push_key(sdl.SDLK_LEFT)
            if n == 85:
                self.push_key(sdl.SDLK_LEFT, down=False)
                self.push_key(sdl.SDLK_RIGHT)
        if n == 260:
            event = sdl.SDL_Event()
            event.type = sdl.SDL_WINDOWEVENT
            event.window.event = sdl.SDL_WINDOWEVENT_CLOSE
            assert sdl.SDL_PushEvent(ctypes.byref(event)) == 1
        events = super().poll_events()
        if n == 31 and self.world == "real":
            assert not any(e.kind == "key_down" and e.key == "space" for e in events)
        self.seen.extend((e.kind, e.key) for e in events)
        return events

    def present(self):
        p = self.game.player
        captures = {1: "start", 36: "jump", 76: "left", 240: "end"} if self.world == "real" else {250: "exit"}
        if self.frames in captures:
            name = captures[self.frames]
            self.save_screenshot(self.output / f"movement_{self.world}_{name}.bmp", WIDTH, HEIGHT)
            self.snapshots[name] = (round(p.x, 2), round(p.y, 2), p.animation, p.facing)
        self.frames += 1
        super().present()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    for world in ("real", "shadow"):
        game = Game(load_map(STAGE_1), world)
        backend = ScriptedBackend(game, output, world)
        game.run(backend, max_frames=300)
        assert backend.frames == 260, "SDL window-close event did not stop the loop"
        assert not backend.opened
        assert ("key_down", "right") in backend.seen
        if world == "real":
            assert game.respawns >= 1, "Real gap did not cause a respawn"
            assert backend.snapshots["jump"][1] < 183
            assert backend.snapshots["left"][3] == -1
        else:
            assert game.respawns == 0
            assert game.completed and game.player.y == 183, (game.player.x, game.player.y, game.paused, game.keys)
            assert game.camera.x > 0
        print(world, "OK; respawns:", game.respawns, "snapshots:", backend.snapshots)


if __name__ == "__main__":
    main()
