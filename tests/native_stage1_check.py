"""실제 SDL 입력으로 Stage 1 전환·추락·거부·클리어·재시작을 검사한다.

python tests/native_stage1_check.py --output <캡처 폴더>
"""

import argparse
import ctypes
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.app import Game, STAGE_1, WIDTH, HEIGHT
from game.map_loader import load_map
from game.pico2d_backend import Pico2DBackend
from native_movement_check import ScriptedBackend


class StageBackend(ScriptedBackend):
    def __init__(self, game, output):
        super().__init__(game, output, "real")
        self.phase = "walk"
        self.capture = "start"
        self.checked = []
        self.complete_wait = 0

    def poll_events(self):
        s, g, p = self.sdl, self.game, self.game.player
        if self.frames == 0 or g.paused:
            event = s.SDL_Event()
            event.type = s.SDL_WINDOWEVENT
            event.window.event = s.SDL_WINDOWEVENT_FOCUS_GAINED
            assert s.SDL_PushEvent(ctypes.byref(event)) == 1
        if self.phase in ("walk", "walk_again", "cross", "cross_again") and "d" not in g.keys:
            self.push_key(s.SDLK_d)

        if self.phase in ("walk", "walk_again") and p.x >= 100:
            self.push_key(s.SDLK_d, down=False)
            self.push_key(s.SDLK_LSHIFT)
            self.phase = "toggle" if self.phase == "walk" else "toggle_again"
        elif self.phase in ("toggle", "toggle_again") and g.scene.world == "shadow":
            assert p.collision is g.collision
            self.checked.append("shift_to_shadow")
            self.capture = "shadow_bridge"
            self.push_key(s.SDLK_LSHIFT, down=False)
            self.push_key(s.SDLK_d)
            self.phase = "cross" if self.phase == "toggle" else "cross_again"
        elif self.phase == "cross" and p.x >= 155:
            self.push_key(s.SDLK_d, down=False)
            self.push_key(s.SDLK_LSHIFT)
            self.phase = "fall"
        elif self.phase == "fall" and g.scene.world == "real" and p.y > 183:
            assert not p.grounded and p.coyote == 0 and p.vy > 0
            self.checked.append("bridge_removed_fall")
            self.capture = "real_gap"
            # 왼쪽 Shift를 누른 중 오른쪽 Shift를 눌러도 추가 전환하지 않는다.
            self.push_key(s.SDLK_RSHIFT)
            self.phase = "release_shifts"
        elif self.phase == "release_shifts":
            assert g.scene.world == "real"
            self.checked.append("two_shifts_one_hold")
            self.push_key(s.SDLK_LSHIFT, down=False)
            self.push_key(s.SDLK_RSHIFT, down=False)
            self.phase = "inside_gap"
        elif self.phase == "inside_gap" and p.y >= 190:
            self.push_key(s.SDLK_LSHIFT)
            self.phase = "blocked"
        elif self.phase == "blocked" and g.blocked_notice > 0:
            assert g.scene.world == "real"
            self.checked.append("inside_bridge_rejected")
            self.capture = "blocked"
            self.phase = "respawn"
        elif self.phase == "respawn" and g.respawns == 1:
            assert g.scene.world == "real" and p.y == 183
            self.checked.append("respawn_real")
            self.push_key(s.SDLK_LSHIFT, down=False)
            self.phase = "walk_again"
        elif self.phase == "cross_again" and g.completed:
            assert g.respawns == 1 and p.vx == p.vy == 0
            self.checked.append("clear")
            self.capture = "clear"
            self.frozen = (p.x, p.y, g.scene.world, g.camera.x, g.camera.y)
            self.push_key(s.SDLK_d, down=False)
            self.push_key(s.SDLK_SPACE)
            self.push_key(s.SDLK_RSHIFT)
            self.phase = "completed"
        elif self.phase == "completed":
            assert self.frozen == (p.x, p.y, g.scene.world, g.camera.x, g.camera.y)
            self.complete_wait += 1
            if self.complete_wait == 4:
                self.checked.append("clear_ignores_gameplay")
                self.push_key(s.SDLK_SPACE, down=False)
                self.push_key(s.SDLK_RSHIFT, down=False)
                self.push_key(s.SDLK_r)
                self.phase = "restart"
        elif self.phase == "restart" and not g.completed:
            assert g.scene.world == "real" and (p.x, p.y) == (28, 183)
            self.checked.append("restart_real")
            self.capture = "restarted"
            self.phase = "done"
        elif self.phase == "done" and self.capture is None:
            event = s.SDL_Event()
            event.type = s.SDL_QUIT
            assert s.SDL_PushEvent(ctypes.byref(event)) == 1
        events = Pico2DBackend.poll_events(self)
        self.seen.extend((e.kind, e.key) for e in events)
        return events

    def present(self):
        if self.capture:
            self.save_screenshot(self.output / f"stage1_{self.capture}.bmp", WIDTH, HEIGHT)
            self.capture = None
        self.frames += 1
        Pico2DBackend.present(self)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    game = Game(load_map(STAGE_1))
    backend = StageBackend(game, output)
    game.run(backend, max_frames=1500)
    assert backend.phase == "done", (backend.phase, game.player.x, game.player.y, game.paused)
    assert not backend.opened
    assert ("key_down", "shift_left") in backend.seen
    assert ("key_down", "shift_right") in backend.seen
    assert not game.running
    print("Native Stage 1 OK:", backend.checked, "frames:", backend.frames)


if __name__ == "__main__":
    main()
