"""첫 실행 단위: 고정 루프와 Stage 1 맵 미리보기. 플레이어 물리는 다음 단계다."""

import argparse
from pathlib import Path
import sys
from time import perf_counter, sleep

from game.camera import Camera
from game.game_world import GameWorld
from game.map_loader import load_map, MapFormatError
from game.map_scene import MapScene
from game.timing import FixedStepper


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE_1 = PROJECT_ROOT / "maps" / "stage_01" / "stage1_missing_bridge.tmj"
WIDTH, HEIGHT, SCALE = 800, 600, 3


class Game:
    def __init__(self, map_data, world="real", camera_position=None):
        self.data = map_data
        self.camera = Camera(map_data.width, map_data.height, WIDTH, HEIGHT, SCALE)
        self.scene = MapScene(map_data, world)
        self.objects = GameWorld()
        self.objects.add_object(self.scene)
        self.stepper = FixedStepper()
        self.keys = set()
        self.running = True
        self.paused = False
        self.reset_camera()
        if camera_position is not None:
            self.camera.set_position(*camera_position)

    def reset_camera(self):
        start = self.data.object_named("PlayerStart")
        self.camera.focus(start.x, start.y)

    def handle_events(self, events):
        reset_clock = False
        for event in events:
            if event.kind == "quit" or (event.kind == "key_down" and event.key == "escape"):
                self.running = False
            elif event.kind in ("focus_lost", "focus_gained"):
                self.paused = event.kind == "focus_lost"
                self.keys.clear()
                self.stepper.reset()
                reset_clock = True
            elif event.kind == "key_up":
                self.keys.discard(event.key)
            elif event.kind == "key_down" and not self.paused:
                if event.key == "r":
                    self.reset_camera()
                    self.keys.clear()
                    self.stepper.reset()
                    reset_clock = True
                elif event.key == "f1":
                    self.scene.show_markers = not self.scene.show_markers
                else:
                    self.keys.add(event.key)
        return reset_clock

    def step(self, dt):
        dx = int("right" in self.keys) - int("left" in self.keys)
        dy = int("down" in self.keys) - int("up" in self.keys)
        self.camera.set_position(self.camera.x + dx * 80 * dt, self.camera.y + dy * 80 * dt)
        self.objects.update(dt)

    def draw(self, renderer):
        renderer.begin(self.data.background)
        self.objects.render(renderer, self.camera)
        renderer.rectangle((0, HEIGHT - 31, WIDTH, 31), (25, 27, 38), filled=True)
        title = f"STAGE 1 / {self.scene.world.upper()} - MAP PREVIEW"
        renderer.label(12, HEIGHT - 22, title)
        renderer.rectangle((0, 0, WIDTH, 26), (25, 27, 38), filled=True)
        status = "PAUSED - focus window to resume" if self.paused else "Arrows: camera | R: reset | F1: markers | Esc: quit"
        renderer.label(12, 8, status)

    def run(self, backend, max_frames=None, screenshot=None):
        try:
            backend.open(WIDTH, HEIGHT)
            last = perf_counter()
            frames = 0
            while self.running:
                frame_start = perf_counter()
                elapsed, last = frame_start - last, frame_start
                if self.handle_events(backend.poll_events()):
                    elapsed = 0.0
                    last = perf_counter()
                if not self.running:
                    break
                if not self.paused:
                    self.stepper.advance(elapsed, self.step)
                self.draw(backend)
                frames += 1
                if screenshot is not None and max_frames is not None and frames == max_frames:
                    backend.save_screenshot(screenshot, WIDTH, HEIGHT)
                backend.present()
                if max_frames is not None and frames >= max_frames:
                    break
                # 프레임 제한만 위한 양보. 물리·애니메이션의 시간 기준으로 사용하지 않는다.
                sleep(max(0.0, 1 / 60 - (perf_counter() - frame_start)))
        finally:
            self.objects.clear()
            backend.close()


def _positive_int(text):
    number = int(text)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description="VEILBOUND Stage 1 map preview (player gameplay not implemented yet)")
    parser.add_argument("--check-map", action="store_true", help="validate map data without opening a window")
    parser.add_argument("--world", choices=("real", "shadow"), default="real", help="static preview world, not gameplay switching")
    parser.add_argument("--frames", type=_positive_int, help="close automatically after this many render frames")
    parser.add_argument("--camera", nargs=2, type=float, metavar=("X", "Y"), help="initial camera top-left in world pixels")
    parser.add_argument("--screenshot", type=Path, metavar="FILE.bmp", help="save actual final frame; requires --frames")
    args = parser.parse_args(argv)
    if args.screenshot and (args.frames is None or args.screenshot.suffix.lower() != ".bmp"):
        parser.error("--screenshot requires --frames and a .bmp output path")
    try:
        data = load_map(STAGE_1)
        if args.check_map:
            print(f"Map OK: {data.width}x{data.height}, {len(data.sprites)} sprites, {len(data.objects)} game objects")
            return 0
        from game.pico2d_backend import Pico2DBackend
        Game(data, args.world, args.camera).run(Pico2DBackend(), args.frames, args.screenshot)
        return 0
    except (MapFormatError, OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        print(f"VEILBOUND could not start: {exc}", file=sys.stderr)
        return 1
