"""Stage 1: 세계 전환으로 다리를 연결하고 출구에 도달한다."""

import argparse
from pathlib import Path
import sys
from time import perf_counter, sleep

from game.camera import Camera
from game.game_world import GameWorld
from game.map_loader import load_map, MapFormatError
from game.map_scene import MapScene
from game.timing import FixedStepper
from game.player import AnimationSet, Player
from game.world_state import WorldState


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE_1 = PROJECT_ROOT / "maps" / "stage_01" / "stage1_missing_bridge.tmj"
PLAYER_ANIMATIONS = PROJECT_ROOT / "assets" / "characters" / "player" / "animations.json"
WIDTH, HEIGHT, SCALE = 800, 600, 3
SHIFT_KEYS = {"shift_left", "shift_right"}


class Game:
    def __init__(self, map_data, world="real", camera_position=None):
        self.data = map_data
        self.camera = Camera(map_data.width, map_data.height, WIDTH, HEIGHT, SCALE)
        self.scene = MapScene(map_data, world)
        self.scene.show_markers = False
        self.world_state = WorldState(map_data.solids, world)
        start = map_data.object_named("PlayerStart")
        self.player = Player(AnimationSet(PLAYER_ANIMATIONS), self.collision,
                             map_data.width, (start.x, start.y))
        self.objects = GameWorld()
        self.objects.add_object(self.scene)
        self.objects.add_object(self.player, depth=1)
        self.stepper = FixedStepper()
        self.keys = set()
        self.running = True
        self.paused = False
        self.pending_switches = 0
        self.blocked_notice = 0.0
        self.completed = False
        self.fall_notice = 0.0
        self.respawns = 0
        self.reset_camera()
        if camera_position is not None:
            self.camera.set_position(*camera_position)

    def reset_camera(self):
        start = self.data.object_named("PlayerStart")
        self.camera.focus(start.x, start.y)

    @property
    def collision(self):
        return self.world_state.collision

    def restart(self, fallen=False):
        self.world_state.reset()
        self.scene.world = self.world_state.name
        self.player.collision = self.collision
        self.player.reset()
        self.keys.clear()
        self.pending_switches = 0
        self.blocked_notice = 0.0
        self.completed = False
        self.reset_camera()
        self.fall_notice = 0.45 if fallen else 0.0
        if fallen:
            self.respawns += 1

    def handle_events(self, events):
        reset_clock = False
        for event in events:
            if event.kind == "quit" or (event.kind == "key_down" and event.key == "escape"):
                self.running = False
            elif event.kind in ("focus_lost", "focus_gained"):
                self.paused = event.kind == "focus_lost"
                self.keys.clear()
                self.player.clear_input()
                self.pending_switches = 0
                self.stepper.reset()
                reset_clock = True
            elif event.kind == "key_up":
                self.keys.discard(event.key)
                if event.key == "space":
                    self.player.release_jump()
            elif event.kind == "key_down" and not self.paused:
                if event.key in self.keys:
                    continue
                shift_was_held = bool(self.keys & SHIFT_KEYS)
                self.keys.add(event.key)
                if event.key == "r":
                    self.restart()
                    self.stepper.reset()
                    reset_clock = True
                elif event.key == "f1":
                    self.scene.show_markers = not self.scene.show_markers
                elif self.completed:
                    continue
                elif event.key in SHIFT_KEYS and not shift_was_held:
                    self.pending_switches += 1
                elif event.key == "space":
                    self.player.request_jump()
        return reset_clock

    def step(self, dt):
        if self.completed:
            return
        self.blocked_notice = max(0.0, self.blocked_notice - dt)
        pending, self.pending_switches = self.pending_switches, 0
        for _ in range(pending):
            if self.world_state.try_toggle(self.player):
                self.scene.world = self.world_state.name
                self.blocked_notice = 0.0
            else:
                self.blocked_notice = 0.45
        dx = int(bool(self.keys & {"d", "right"})) - int(bool(self.keys & {"a", "left"}))
        self.player.direction = dx
        self.objects.update(dt)
        self.fall_notice = max(0.0, self.fall_notice - dt)
        if self.player.y - self.player.HEIGHT > self.data.height:
            # 화면 밖 추락은 가짜 사망 모션 없이 즉시 복귀한다. stepper는 콜백 안에서 초기화하지 않는다.
            self.restart(fallen=True)
            return
        elif self.player.y <= self.data.height:
            self.camera.follow(self.player.x, self.player.y, dx, dt)
        p, exit_area = self.player, self.data.object_named("Exit")
        if (p.x + p.WIDTH / 2 > exit_area.x and p.x - p.WIDTH / 2 < exit_area.x + exit_area.width
                and p.y > exit_area.y and p.y - p.HEIGHT < exit_area.y + exit_area.height):
            # Stage 2 데이터가 없으므로 파일을 추측해 읽지 않고 단독 완료 상태로 멈춘다.
            self.completed = True
            p.vx = p.vy = 0.0
            p.clear_input()
            p.animation, p.animation_time = "idle", 0.0
            self.keys.clear()
            self.pending_switches = 0
            self.blocked_notice = self.fall_notice = 0.0

    def draw(self, renderer):
        renderer.begin(self.data.background)
        self.objects.render(renderer, self.camera)
        renderer.rectangle((0, HEIGHT - 31, WIDTH, 31), (25, 27, 38), filled=True)
        title = f"STAGE 1 / {self.scene.world.upper()}"
        renderer.label(12, HEIGHT - 22, title)
        renderer.rectangle((0, 0, WIDTH, 26), (25, 27, 38), filled=True)
        status = "PAUSED - focus window to resume" if self.paused else "A/D: move | Space: tap/hold jump | Shift: switch | R: restart | F1: debug | Esc: quit"
        renderer.label(12, 8, status)
        if self.fall_notice > 0:
            renderer.label(12, HEIGHT - 48, "FELL - returned to start")
        if self.blocked_notice > 0:
            renderer.label(12, HEIGHT - 48, "Cannot switch: solid terrain blocks your body", (255, 181, 142))
        if self.scene.show_markers:
            p = self.player
            renderer.rectangle(self.camera.screen_rect(p.x - p.WIDTH / 2, p.y - p.HEIGHT,
                                                       p.WIDTH, p.HEIGHT), (255, 220, 100))
        if self.completed:
            renderer.rectangle((200, 245, 400, 110), (25, 27, 38), filled=True)
            renderer.label(325, 315, "STAGE 1 CLEAR", (116, 223, 188))
            renderer.label(290, 280, "R: try again   Esc: quit")

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
    parser = argparse.ArgumentParser(description="VEILBOUND Stage 1 - switch worlds and reach the exit")
    parser.add_argument("--check-map", action="store_true", help="validate map data without opening a window")
    parser.add_argument("--world", choices=("real", "shadow"), default="real", help="initial world for testing; restart always returns to real")
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
