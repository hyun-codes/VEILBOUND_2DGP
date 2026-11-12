"""세계 전환과 가로등 배치로 길을 만들고 현실 포털로 진행한다."""

import argparse
from pathlib import Path
import sys
from time import perf_counter, sleep

from game.camera import Camera
from game.game_world import GameWorld
from game.map_loader import load_map, MapFormatError, Sprite
from game.map_scene import MapScene
from game.timing import FixedStepper
from game.player import AnimationSet, Player
from game.world_state import WorldState
from game.world_effects import WorldEffects
from game.lamp_puzzle import LampPuzzle
from game.stage_manager import StageManager
from game.lever_gate import LeverGate, nearest_control
from game.sliding_block import SlidingBlock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE_1 = PROJECT_ROOT / "maps" / "stage_01" / "stage1_missing_bridge.tmj"
STAGE_2 = PROJECT_ROOT / "maps" / "stage_02" / "stage2_block_ledge.tmj"
STAGE_3 = PROJECT_ROOT / "maps" / "stage_03" / "stage3_block_hatch.tmj"
STAGE_2_DRAFT = STAGE_2.with_name("stage2_lamp_room.tmj")
STAGE_3_DRAFT = STAGE_3.with_name("stage3_return_circuit.tmj")
PLAYER_ANIMATIONS = PROJECT_ROOT / "assets" / "characters" / "player" / "animations.json"
INTERACT_ICON = PROJECT_ROOT / "assets" / "ui" / "interact_e.png"
WIDTH, HEIGHT, SCALE = 800, 600, 3
SHIFT_KEYS = {"shift_left", "shift_right"}


class Game:
    def __init__(self, map_data, world="real", camera_position=None, stages=None):
        self.stages = stages
        self.animations = {
            "real": AnimationSet(PLAYER_ANIMATIONS),
            "shadow": AnimationSet(PLAYER_ANIMATIONS.parent / "shadow" / "animations.json"),
        }
        self.effects = WorldEffects(world)
        self.stepper = FixedStepper()
        self.keys = set()
        self.running = True
        self.paused = False
        self.enter_map(map_data, world, camera_position)

    def enter_map(self, map_data, world="real", camera_position=None):
        self.source_data = map_data
        self.puzzle = LampPuzzle(map_data)
        self.mechanism = LeverGate(map_data)
        self.block = SlidingBlock(map_data)
        self.data = self.block.compose(self.mechanism.compose(self.puzzle.data))
        self.stage_number = map_data.properties.get("stageNumber", 1)
        self.camera = Camera(self.data.width, self.data.height, WIDTH, HEIGHT, SCALE)
        self.effects.reset(world)
        self.scene = MapScene(self.data, world, self.effects)
        self.scene.show_markers = False
        self.world_state = WorldState(self.data.solids, world)
        start = self.data.object_named("PlayerStart")
        self.player = Player(self.animations[world], self.collision, self.data.width, (start.x, start.y))
        if hasattr(self, "objects"):
            self.objects.clear()
        self.objects = GameWorld()
        self.objects.add_object(self.scene)
        self.objects.add_object(self.player, depth=1)
        self.keys.clear()
        self.pending_switches = self.pending_interactions = 0
        self.blocked_notice = 0.0
        self.completed = False
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
        count = self.respawns + int(fallen)
        debug = self.scene.show_markers
        self.enter_map(self.source_data)
        self.scene.show_markers = debug
        self.respawns = count

    def player_at_exit(self):
        p, area = self.player, self.data.object_named("Exit")
        return (p.x + p.WIDTH / 2 > area.x and p.x - p.WIDTH / 2 < area.x + area.width
                and p.y > area.y and p.y - p.HEIGHT < area.y + area.height)

    def refresh_layout(self):
        self.data = self.block.compose(self.mechanism.compose(self.puzzle.data))
        self.scene.data = self.data
        self.world_state = WorldState(self.data.solids, self.scene.world)
        self.player.collision = self.collision

    def interaction_target(self):
        if self.scene.world != "real" or not self.player.grounded or self.completed or self.paused:
            return None, None
        if control := self.block.nearby_control(self.player):
            return "block", control
        kind, control = nearest_control(self.player, self.puzzle, self.mechanism)
        if kind == "lever" and self.mechanism.activated:
            return None, None
        return kind, control

    def handle_events(self, events):
        reset_clock = False
        for event in events:
            if event.kind == "quit" or (event.kind == "key_down" and event.key == "escape"):
                self.running = False
            elif event.kind in ("focus_lost", "focus_gained"):
                self.paused = event.kind == "focus_lost"
                self.keys.clear()
                self.player.clear_input()
                self.pending_switches = self.pending_interactions = 0
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
                elif event.key == "f3":
                    self.effects.motion_enabled = not self.effects.motion_enabled
                elif self.completed:
                    continue
                elif event.key in SHIFT_KEYS and not shift_was_held:
                    self.pending_switches += 1
                elif event.key == "e":
                    self.pending_interactions += 1
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
                self.player.animations = self.animations[self.scene.world]
                self.effects.switch(self.world_state.name)
                self.blocked_notice = 0.0
            else:
                self.blocked_notice = 0.45
                self.effects.reject()
        pending, self.pending_interactions = self.pending_interactions, 0
        for _ in range(pending):
            kind, control = self.interaction_target()
            if control is None:
                continue
            device = {"block": self.block, "lever": self.mechanism, "lamp": self.puzzle}[kind]
            if device.interact(self.player, self.world_state.name):
                self.refresh_layout()
        if self.mechanism.advance(dt):
            self.refresh_layout()
        dx = int(bool(self.keys & {"d", "right"})) - int(bool(self.keys & {"a", "left"}))
        self.player.direction = dx
        self.objects.update(dt)
        if self.player.y - self.player.HEIGHT > self.data.height:
            # 화면 밖 추락은 가짜 사망 모션 없이 즉시 복귀한다. stepper는 콜백 안에서 초기화하지 않는다.
            self.restart(fallen=True)
            return
        elif self.player.y <= self.data.height:
            self.camera.follow(self.player.x, self.player.y, dx, dt)
        p = self.player
        if self.world_state.name == "real" and self.player_at_exit():
            next_map = self.stages.next_map(self.data) if self.stages else None
            if next_map is not None:
                self.enter_map(next_map)
                return
            # 등록한 다음 스테이지가 없으면 현재 완료 상태로 멈춘다.
            self.completed = True
            p.vx = p.vy = 0.0
            p.clear_input()
            p.animation, p.animation_time = "idle", 0.0
            self.keys.clear()
            self.pending_switches = self.pending_interactions = 0
            self.blocked_notice = 0.0

    def draw(self, renderer):
        renderer.begin(self.data.background)
        self.objects.render(renderer, self.camera)
        self.mechanism.draw(renderer, self.camera)
        self.puzzle.draw(renderer, self.camera, self.scene.world)
        kind, control = self.interaction_target()
        if control is not None:
            x = control.x - 7
            y = control.y - (28 if kind in ("lever", "block") else 21)
            icon = Sprite(INTERACT_ICON, (0, 0, 15, 9), x, y, 15, 9)
            renderer.sprite(icon, self.camera.screen_rect(x, y, 15, 9))
        if self.scene.show_markers:
            p = self.player
            renderer.rectangle(self.camera.screen_rect(p.x - p.WIDTH / 2, p.y - p.HEIGHT,
                                                       p.WIDTH, p.HEIGHT), (255, 220, 100))

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
                    # 새 입력으로 막 시작한 효과에 이전 프레임 지연 시간을 적용하지 않는다.
                    self.effects.advance(elapsed, environment=not self.completed)
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
    parser = argparse.ArgumentParser(description="VEILBOUND - light and shadow puzzle platformer")
    parser.add_argument("--stage", type=int, choices=(1, 2, 3), default=1, help="start at the selected stage")
    parser.add_argument("--check-map", action="store_true", help="validate map data without opening a window")
    parser.add_argument("--world", choices=("real", "shadow"), default="real", help="initial world for testing; restart always returns to real")
    parser.add_argument("--frames", type=_positive_int, help="close automatically after this many render frames")
    parser.add_argument("--camera", nargs=2, type=float, metavar=("X", "Y"), help="initial camera top-left in world pixels")
    parser.add_argument("--screenshot", type=Path, metavar="FILE.bmp", help="save actual final frame; requires --frames")
    args = parser.parse_args(argv)
    if args.screenshot and (args.frames is None or args.screenshot.suffix.lower() != ".bmp"):
        parser.error("--screenshot requires --frames and a .bmp output path")
    try:
        paths = {"Stage1": STAGE_1, "Stage2": STAGE_2, "Stage3": STAGE_3}
        data = load_map(paths[f"Stage{args.stage}"])
        if args.check_map:
            LampPuzzle(data)  # 순수 데이터 검사에서 퍼즐 프리셋·필수 오브젝트도 확인한다.
            LeverGate(data)
            SlidingBlock(data)
            print(f"Map OK: {data.width}x{data.height}, {len(data.sprites)} sprites, {len(data.objects)} game objects")
            return 0
        from game.pico2d_backend import Pico2DBackend
        Game(data, args.world, args.camera, StageManager(paths)).run(Pico2DBackend(), args.frames, args.screenshot)
        return 0
    except (MapFormatError, OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        print(f"VEILBOUND could not start: {exc}", file=sys.stderr)
        return 1
