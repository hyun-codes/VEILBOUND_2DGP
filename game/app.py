"""VEILBOUND의 첫 등불 퍼즐 실행과 입력 처리."""

import argparse
from pathlib import Path
from time import perf_counter, sleep

from game.lantern_room import LanternRoom
from game.lantern_view import LanternView
from game.map_loader import MapFormatError, load_map
from game.pico2d_backend import Pico2DBackend
from game.timing import FixedStepper


STAGE_1 = Path(__file__).resolve().parents[1] / "maps/stage_01/stage1_lantern_room.tmj"
STAGE_2 = STAGE_1.parent.parent / "stage_02/stage2_rail_light.tmj"
STAGE_3 = STAGE_1.parent.parent / "stage_03/stage3_crossed_lenses.tmj"
STAGE_4 = STAGE_1.parent.parent / "stage_04/stage4_counterweight.tmj"
STAGE_5 = STAGE_1.parent.parent / "stage_05/stage5_beacon_vault.tmj"
STAGES = {1: STAGE_1, 2: STAGE_2, 3: STAGE_3, 4: STAGE_4, 5: STAGE_5}
WIDTH, HEIGHT = 800, 600


def run(room, frames, screenshot, next_room=None):
    backend = Pico2DBackend()
    view = LanternView(room, WIDTH, HEIGHT)
    stepper = FixedStepper()
    keys = set()
    pending = set()
    paused = False

    def step(dt):
        nonlocal room, view, next_room
        direction = int(bool(keys & {"d", "right"})) - int(bool(keys & {"a", "left"}))
        room.step(dt, direction, "space" in pending, "e" in pending)
        pending.clear()
        if room.complete and next_room is not None:
            room = LanternRoom(load_map(STAGES[next_room]))
            view = LanternView(room, WIDTH, HEIGHT)
            next_room = next_room + 1 if next_room + 1 in STAGES else None
            keys.clear()

    try:
        backend.open(WIDTH, HEIGHT)
        count, previous = 0, perf_counter()
        while frames is None or count < frames:
            now = perf_counter()
            elapsed, previous = now - previous, now
            for event in backend.poll_events():
                if event.kind == "quit" or (event.kind == "key_down" and event.key == "escape"):
                    return
                if event.kind in ("focus_lost", "focus_gained"):
                    paused = event.kind == "focus_lost"
                    keys.clear()
                    pending.clear()
                    stepper.reset()
                    elapsed = 0.0
                elif event.kind == "key_up":
                    keys.discard(event.key)
                elif event.kind == "key_down" and not paused and event.key not in keys:
                    keys.add(event.key)
                    if event.key == "r":
                        room.reset()
                        keys.clear()
                        pending.clear()
                        stepper.reset()
                        elapsed = 0.0
                    elif event.key in ("space", "e"):
                        pending.add(event.key)
            if not paused:
                stepper.advance(elapsed, step)
            view.draw(backend)
            count += 1
            if screenshot and count == frames:
                backend.save_screenshot(screenshot, WIDTH, HEIGHT)
            backend.present()
            sleep(max(0.0, 1 / 60 - (perf_counter() - now)))
    finally:
        backend.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="VEILBOUND - lantern puzzle")
    parser.add_argument("--stage", type=int, choices=STAGES, default=1)
    parser.add_argument("--check-map", action="store_true")
    parser.add_argument("--frames", type=int)
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args(argv)
    if args.frames is not None and args.frames < 1:
        parser.error("--frames must be positive")
    if args.screenshot and (args.frames is None or args.screenshot.suffix.lower() != ".bmp"):
        parser.error("--screenshot requires --frames and a .bmp output path")
    try:
        room = LanternRoom(load_map(STAGES[args.stage]))
        if args.check_map:
            print(f"Map OK: {room.data.width}x{room.data.height}, {len(room.platforms)} light platforms")
        else:
            run(room, args.frames, args.screenshot, args.stage + 1 if args.stage + 1 in STAGES else None)
        return 0
    except (MapFormatError, OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"VEILBOUND could not start: {exc}\n")
