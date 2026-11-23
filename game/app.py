"""VEILBOUND의 타이틀, 플레이 화면과 입력 처리."""

import argparse
from pathlib import Path
from time import perf_counter, sleep

from game.lantern_room import LanternRoom
from game.lantern_view import ASSETS, LanternView
from game.map_loader import MapFormatError, load_map
from game.pico2d_backend import Pico2DBackend
from game.timing import FixedStepper
from game.title_screen import TitleScreen


STAGE_1 = Path(__file__).resolve().parents[1] / "maps/stage_01/stage1_lantern_room.tmj"
STAGE_2 = STAGE_1.parent.parent / "stage_02/stage2_rail_light.tmj"
STAGE_3 = STAGE_1.parent.parent / "stage_03/stage3_crossed_lenses.tmj"
STAGE_4 = STAGE_1.parent.parent / "stage_04/stage4_counterweight.tmj"
STAGE_5 = STAGE_1.parent.parent / "stage_05/stage5_beacon_vault.tmj"
STAGE_6 = STAGE_1.parent.parent / "stage_06/stage6_pressure_foundry.tmj"
STAGE_7 = STAGE_1.parent.parent / "stage_07/stage7_reverse_foundry.tmj"
STAGE_8 = STAGE_1.parent.parent / "stage_08/stage8_freight_interlock.tmj"
STAGE_9 = STAGE_1.parent.parent / "stage_09/stage9_reservoir_interlock.tmj"
STAGES = {1: STAGE_1, 2: STAGE_2, 3: STAGE_3, 4: STAGE_4, 5: STAGE_5,
          6: STAGE_6, 7: STAGE_7, 8: STAGE_8, 9: STAGE_9}
WIDTH, HEIGHT = 800, 600
FADE_OUT = 0.28
BLACKOUT = 0.14
FADE_IN = 0.30


def draw_stage_transition(backend, elapsed):
    black_time = elapsed - FADE_OUT
    if black_time < 0:
        fade = elapsed / FADE_OUT
    elif black_time < BLACKOUT:
        fade = 1.0
    else:
        fade = max(0.0, 1 - (black_time - BLACKOUT) / FADE_IN)
    bounds = (0, 0, WIDTH, HEIGHT)
    backend.overlay(bounds, (0, 0, 0, round(255 * fade * fade * (3 - 2 * fade))))
    if 0 <= black_time < BLACKOUT:
        backend.image(ASSETS / "props/light_orb.png", (0, 0, 7, 7),
                      (WIDTH // 2 - 10, HEIGHT // 2 - 10, 21, 21))
        glow = min(1.0, black_time / 0.04, (BLACKOUT - black_time) / 0.04)
        backend.overlay(bounds, (0, 0, 0, round(255 * (1 - glow))))


def run(room, frames, screenshot, next_room=None):
    backend = Pico2DBackend()
    title = TitleScreen() if room is None else None
    view = LanternView(room, WIDTH, HEIGHT) if room is not None else None
    stepper = FixedStepper()
    keys = set()
    pending = set()
    paused = False
    transition = None

    def step(dt):
        nonlocal room, view, next_room, transition
        if transition is not None:
            previous = transition
            transition += dt
            if previous < FADE_OUT <= transition:
                room = LanternRoom(load_map(STAGES[next_room]))
                view = LanternView(room, WIDTH, HEIGHT)
                next_room = next_room + 1 if next_room + 1 in STAGES else None
            if transition >= FADE_OUT + BLACKOUT + FADE_IN:
                transition = None
            return
        direction = int(bool(keys & {"d", "right"})) - int(bool(keys & {"a", "left"}))
        room.step(dt, direction, "space" in pending, "e" in pending)
        pending.clear()
        if room.complete and next_room is not None:
            transition = 0.0
            keys.clear()

    try:
        backend.open(WIDTH, HEIGHT)
        count, previous = 0, perf_counter()
        while frames is None or count < frames:
            now = perf_counter()
            elapsed, previous = now - previous, now
            for event in backend.poll_events():
                if event.kind == "quit":
                    return
                if event.kind in ("focus_lost", "focus_gained"):
                    paused = event.kind == "focus_lost"
                    keys.clear()
                    pending.clear()
                    stepper.reset()
                    elapsed = 0.0
                    continue
                if title is not None:
                    if not paused:
                        action = title.handle(event)
                        if action == "quit":
                            return
                        if action == "play":
                            room = LanternRoom(load_map(STAGE_1))
                            view = LanternView(room, WIDTH, HEIGHT)
                            next_room = 2
                            title = None
                            elapsed = 0.0
                            break
                    continue
                if event.kind == "key_down" and event.key == "escape":
                    return
                if transition is not None:
                    continue
                if event.kind == "key_up":
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
            if title is not None:
                title.draw(backend, 0.0 if paused else elapsed)
            else:
                if not paused:
                    stepper.advance(elapsed, step)
                view.draw(backend)
                if transition is not None:
                    draw_stage_transition(backend, transition)
            count += 1
            if screenshot and count == frames:
                backend.save_screenshot(screenshot, WIDTH, HEIGHT)
            backend.present()
            sleep(max(0.0, 1 / 60 - (perf_counter() - now)))
    finally:
        backend.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="VEILBOUND - lantern puzzle")
    parser.add_argument("--stage", type=int, choices=STAGES)
    parser.add_argument("--check-map", action="store_true")
    parser.add_argument("--frames", type=int)
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args(argv)
    if args.frames is not None and args.frames < 1:
        parser.error("--frames must be positive")
    if args.screenshot and (args.frames is None or args.screenshot.suffix.lower() != ".bmp"):
        parser.error("--screenshot requires --frames and a .bmp output path")
    try:
        if args.check_map:
            room = LanternRoom(load_map(STAGES[args.stage or 1]))
            print(f"Map OK: {room.data.width}x{room.data.height}, {len(room.platforms)} light platforms")
        elif args.stage is None:
            run(None, args.frames, args.screenshot)
        else:
            room = LanternRoom(load_map(STAGES[args.stage]))
            run(room, args.frames, args.screenshot, args.stage + 1 if args.stage + 1 in STAGES else None)
        return 0
    except (MapFormatError, OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"VEILBOUND could not start: {exc}\n")
