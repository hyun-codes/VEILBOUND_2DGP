"""Lantern room sprites and the light overlay, drawn at integer scale."""

from math import atan2, ceil, floor, hypot, sin, tau
from pathlib import Path

from game.camera import Camera
from game.lantern_room import light_span


ASSETS = Path(__file__).resolve().parents[1] / "assets"
HINT_FONT = ASSETS / "ui/fonts/GowunBatang-Hints.ttf"
DARKNESS_MASK = ASSETS / "environments/stage_01/lantern_darkness.png"
MASK_SIZE = 221
CHAIN_FRAMES = 8
CHAIN_FRAME_TRAVEL = 1.5
DEATH_KICK = ((4, -1), (-3, 1), (2, -1), (-1, 0))
DEATH_FRAME_STARTS = (0, 0.08, 0.16, 0.25, 0.35, 0.50)
DEATH_FADE_START = 0.55
FIRE_FRAMES = (0, 1, 2, 1, 3, 2)
FIRE_ATLAS = "props/beacon_fire.png"


def draw_darkness(backend, camera, x, y, radius):
    lit_area = camera.screen_rect(x - radius, y - radius, 2 * radius, 2 * radius)
    left, bottom, width, height = lit_area
    right, top = left + width, bottom + height
    screen_w, screen_h = camera.width, camera.height
    left, right = (max(0, min(screen_w, edge)) for edge in (left, right))
    bottom, top = (max(0, min(screen_h, edge)) for edge in (bottom, top))
    for bounds in ((0, 0, screen_w, bottom), (0, top, screen_w, screen_h - top),
                   (0, bottom, left, top - bottom), (right, bottom, screen_w - right, top - bottom)):
        if bounds[2] and bounds[3]:
            backend.overlay(bounds, (0, 0, 0, 255))
    backend.image(DARKNESS_MASK, (0, 0, MASK_SIZE, MASK_SIZE), lit_area)


def draw_combined_darkness(backend, camera, lights):
    for fraction, alpha in ((1, 255), (0.87, 117), (0.68, 62), (0.42, 26)):
        for row in range(camera.world_height):
            spans = sorted(span for light in lights if (span := light_span(light, row, fraction)))
            cursor = 0
            for left, right in spans + [(camera.world_width, camera.world_width)]:
                edge = min(camera.world_width, left)
                if edge > cursor:
                    backend.overlay(camera.screen_rect(cursor, row, edge - cursor, 1), (0, 0, 0, alpha))
                cursor = max(cursor, right)


def draw_projector_beam(backend, camera, x, y, target_x, target_y, color):
    dx, dy = target_x - x, target_y - y
    length = hypot(dx, dy)
    if length < 1:
        return
    # A faint cone through the air marks aim. The illuminated surface is handled by the light mask.
    for spread, alpha in ((9, 13), (4, 19)):
        nx, ny = -dy / length * spread, dx / length * spread
        points = ((x, y), (target_x + nx, target_y + ny), (target_x - nx, target_y - ny))
        for row in range(floor(min(p[1] for p in points)), ceil(max(p[1] for p in points))):
            sample = row + 0.5
            edges = [ax + (bx - ax) * (sample - ay) / (by - ay)
                     for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1])
                     if min(ay, by) <= sample < max(ay, by)]
            if len(edges) == 2:
                left, right = sorted(edges)
                backend.overlay(camera.screen_rect(left, row, right - left, 1), (*color, alpha))


def exit_hint(room):
    unlit = [beacon for name, (beacon, _) in room.beacons.items() if name not in room.lit_beacons]
    if unlit:
        if all(beacon.properties.get("socket") for beacon in unlit) and not any(
                room.socket and room.socket.name == beacon.properties["socket"] for beacon in unlit):
            action = "받침대에 구슬을 두고 등잔 앞에서 E를 누르자."
        elif all(beacon.properties.get("beam") for beacon in unlit):
            action = "투광기로 등잔을 비춘 뒤 가까이서 E를 누르자."
        else:
            action = "빛이 닿은 등잔 앞에서 E를 눌러 켜자."
        return f"아직 꺼진 등잔이 {len(unlit)}개 남았다.", action
    if remaining := len(room.keys) - len(room.collected):
        return f"아직 찾지 못한 열쇠가 {remaining}개 남았다.", "빛을 옮겨 어두운 길을 살펴보자."
    if any(not room.receiver_lit(receiver) for receiver in room.receivers):
        return "수광부에 빛이 닿지 않는다.", "투광기를 돌려 수광부를 비추자."
    if room.exit_socket and room.socket is not room.exit_socket:
        return "받침대가 비어 있다.", "구슬을 마지막 받침대에 놓자."
    if room.exit.properties.get("waitSibling"):
        return "동생이 아직 건너는 중이다.", "빛을 남겨 두고 문턱에서 기다리자."
    if room.exit.properties.get("carry") and not room.carrying_lantern:
        return "구슬이 뒤에 남아 있다.", "구슬을 다시 품고 길을 나서자."
    return None


def draw_beacon_fire(sprite, x, wick, elapsed):
    frame = FIRE_FRAMES[int(elapsed * 11) % len(FIRE_FRAMES)]
    sprite(FIRE_ATLAS, (frame * 12, 0, 12, 12), x - 6, wick - 12, 12, 12)
    for index, drift in enumerate((-5, 2, 6)):
        age = (elapsed + index * 0.31) % 0.94 / 0.94
        ember = int(age * 4)
        sprite(FIRE_ATLAS, (ember * 12, 12, 4, 4),
               x - 2 + round(drift * age), wick - 7 - round(17 * age), 4, 4)


class LanternView:
    def __init__(self, room, width, height):
        self.room = room
        self.camera = Camera(room.data.width, room.data.height, width, height, scale=3)
        self.intro = None
        if room.walk_through:
            self.camera.focus(room.x, room.y)

    def draw(self, backend):
        room = self.room
        death = room.death_elapsed
        kick = int(death * 32) if death is not None else len(DEATH_KICK)
        self.camera.render_offset = DEATH_KICK[kick] if kick < len(DEATH_KICK) else (0, 0)

        def rect(x, y, w, h, color, filled=True):
            backend.rectangle(self.camera.screen_rect(x, y, w, h), color, filled)

        def sprite(path, source, x, y, width, height, flip=False, angle=0.0):
            backend.image(ASSETS / path, source, self.camera.screen_rect(x, y, width, height), flip, angle)

        def ledge(path, platform, tile_height):
            for offset in range(0, round(platform.width), 16):
                width = min(16, round(platform.width) - offset)
                sprite(path, (0, 0, width, tile_height), platform.x + offset, platform.y,
                       width, platform.height)

        def draw_chamber():
            chamber = room.chamber
            sprite('props/rotating_room_frame.png', (0, 0, 160, 160),
                   chamber.x - chamber.frame_size / 2, chamber.y - chamber.frame_size / 2,
                   chamber.frame_size, chamber.frame_size, angle=-chamber.angle)
            for part in room.rotating_platforms:
                vertical = part.height > part.width
                length = part.height if vertical else part.width
                thickness = part.width if vertical else part.height
                for offset in range(0, int(length), 16):
                    width = min(16, int(length) - offset)
                    x = part.x + (part.width / 2 if vertical else offset + width / 2)
                    y = part.y + (offset + width / 2 if vertical else part.height / 2)
                    cx, cy = chamber.animated_point(x, y, original=True)
                    sprite('tiles/lantern_ledge.png', (0, 0, width, 5),
                           cx - width / 2, cy - thickness / 2, width, thickness,
                           angle=-chamber.angle - (tau / 4 if vertical else 0))

        def draw_key(index, key):
            if index in room.collected:
                return
            cx, cy = key.x + key.width / 2, key.y + key.height - 5
            angle = 0
            if room.chamber and key.properties.get('rotates'):
                cy = key.y + key.height / 2
                cx, cy = room.chamber.animated_point(cx, cy)
                angle = -room.chamber.angle
            sprite('props/brass_key.png', (0, 0, 14, 10), cx - 7, cy - 5, 14, 10, angle=angle)

        story = room.walk_through
        backend.begin(room.data.background)
        if not story:
            sprite("environments/stage_01/pump_hall.png", (0, 0, 264, 200), 0, 0, room.data.width, room.data.height)
        for part in room.data.sprites:
            if part.visual_role == "backdrop":
                backend.image(part.image, part.source,
                              self.camera.screen_rect(part.x, part.y, part.width, part.height))
            elif part.visual_role in ("hoist_chain", "hoist_gears"):
                sx, sy, sw, sh = part.source
                distance = room.rail.distance_at(room.elapsed)
                frame = int(distance / CHAIN_FRAME_TRAVEL) % CHAIN_FRAMES
                x, y, w, h = self.camera.screen_rect(part.x, part.y, part.width, part.height)
                if part.visual_role == "hoist_chain":
                    recent = room.rail.distance_at(max(0.0, room.elapsed - 0.12))
                    tension = min(1.0, abs(distance - recent) / 2.5)
                    y += round(2 * sin(tau * distance / 21) * tension)
                backend.image(part.image, (sx + frame * sw, sy, sw, sh), (x, y, w, h))
        if room.chamber:
            draw_chamber()
        stone = "environments/story/stone.png" if story else "tiles/stone_ledge.png"
        for ground in room.ground:
            ledge(stone, ground, 16)
        for p in room.platforms:
            ledge(stone if story else "tiles/lantern_ledge.png", p, 5)
        for plate in room.plates:
            pressed = plate.name in room.pressed_plates
            sprite("props/pressure_treadle.png", (3, 13, 26, 11),
                   plate.x + plate.width / 2 - 13, plate.y - (1 if pressed else 3), 26, 11)
        for part in room.data.sprites:
            if part.visual_role not in ("hoist_chain", "hoist_gears", "backdrop", 'rotating_frame', 'room_crank'):
                backend.image(part.image, part.source,
                              self.camera.screen_rect(part.x, part.y, part.width, part.height))
        for prop in room.props:
            if prop.kind == "Wall":
                ledge(stone, prop, 16)
            else:
                rect(prop.x, prop.y, prop.width, prop.height, (121, 88, 61))
                rect(prop.x, prop.y, prop.width, prop.height, (196, 151, 102), False)
        if crate := room.crate:
            sprite("props/cargo_crate.png", (0, 0, 16, 16), crate.x, crate.y, crate.width, crate.height)
        for index, key in enumerate(room.keys):
            draw_key(index, key)

        door = room.exit
        door_open = room.complete or (bool(room.exit_socket or room.beacons or room.switch_relays) and room.exit_ready)
        locked = room.story_door_closed
        if not story or locked:
            sprite("props/exit_door.png", (13 if door_open else 0, 0, 13, 24),
                   door.x, door.y, door.width, door.height)
        for socket in room.sockets:
            if story and socket is room.initial_socket:
                continue
            sprite("props/lantern_socket.png", (0, 0, 10, 7), socket.x - 5, socket.y - 7, 10, 7)
            if socket.properties.get("releaseInLight"):
                open_cell = 9 if room.receiver_lit(socket) else 0
                sprite("props/lens_receiver.png", (open_cell, 0, 9, 11), socket.x + 6, socket.y - 11, 9, 11)
        if not story:
            for fixture in room.fixtures:
                sprite("props/light_orb.png", (7, 0, 7, 9), fixture.x - 3, fixture.y - 4, 7, 9)
        for chute in room.chutes:
            sprite("props/lantern_chute.png", (0, 0, 14, 15), chute.x - 7, chute.y - 15, 14, 15)
        for valve in room.valves:
            socket, flood = room.valve_links[valve.name]
            frame = 12 if room.socket is socket else 0
            if room.drained == flood:
                frame = 24
            sprite("props/drain_valve.png", (frame, 0, 12, 14),
                   valve.x - 6, valve.y - 14, 12, 14)
        for switch in room.switches:
            sprite("props/projector_stand.png", (0, 0, 15, 16), switch.x - 7, switch.y - 16, 15, 16)
            if relay := room.switch_relays.get(switch.name):
                sprite("props/lens_receiver.png", (9 if room.relay_lit(switch) else 0, 0, 9, 11),
                       relay.x - 4, relay.y - 5, 9, 11)
        for receiver in room.receivers:
            sprite("props/lens_receiver.png", (9 if room.receiver_lit(receiver) else 0, 0, 9, 11),
                   receiver.x - 4, receiver.y - 5, 9, 11)
        for i, (name, (beacon, _)) in enumerate(room.beacons.items()):
            frame = 11 if name in room.lit_beacons else 0
            top = 5 if frame else 0
            sprite("props/vault_beacon.png", (frame, top, 11, 14 - top),
                   beacon.x - 5, beacon.y - 14 + top, 11, 14 - top)
            if not story or locked:
                sprite("props/vault_beacon.png", (frame + 4, 4, 3, 3),
                       door.x - 2 + i % 3 * 6, door.y - 9 + i // 3 * 4, 3, 3)

        for flood in room.floods:
            depth = round(room.water_depth(flood))
            if not depth:
                continue
            surface = flood.y + flood.height - depth
            ripple = int(room.elapsed * 5) % 2 * 16
            rim = min(3, depth)
            for offset in range(0, int(flood.width), 16):
                width = min(16, int(flood.width) - offset)
                x = flood.x + offset
                sprite("environments/stage_06/reservoir_water.png", (ripple, 0, width, rim),
                       x, surface, width, rim)
                if depth > rim:
                    sprite("environments/stage_06/reservoir_water.png", (ripple, 3, width, 5),
                           x, surface + rim, width, depth - rim)

        if room.sibling:
            bob = bool(room.sibling_travel) and int(room.elapsed * 12) % 2
            sprite("characters/story/sibling.png", (0, 0, 8, 15),
                   round(room.sibling_x) - 4, round(room.sibling_y) - 15 - bob, 8, 15,
                   flip=room.sibling_travel < 0 or (not room.sibling_travel and room.sibling_x > room.x))
        lx, ly, radius = room.light
        left, top, width, height = self.camera.view
        visible_lights = (room.light, *(light for light in room.lights[1:] if
                          left < light[0] + light[2] and light[0] - light[2] < left + width
                          and top < light[1] + light[2] and light[1] - light[2] < top + height))
        if len(visible_lights) > 1:
            draw_combined_darkness(backend, self.camera, visible_lights)
        else:
            draw_darkness(backend, self.camera, lx, ly, radius)
        for i, (name, (beacon, _)) in enumerate(room.beacons.items()):
            if name in room.lit_beacons:
                draw_beacon_fire(sprite, beacon.x, beacon.y - 9, room.elapsed + i * 0.16)
        if room.chamber and room.rotation_control:
            draw_chamber()
            for platform in room.platforms:
                ledge('tiles/lantern_ledge.png', platform, 5)
            sprite('props/exit_door.png', (13 if door_open else 0, 0, 13, 24),
                   door.x, door.y, door.width, door.height)
            for socket in room.sockets:
                sprite('props/lantern_socket.png', (0, 0, 10, 7), socket.x-5, socket.y-7, 10, 7)
            for index, key in enumerate(room.keys):
                draw_key(index, key)
        for crank in room.cranks:
            sprite('props/room_handwheel_base.png', (0, 0, 24, 3),
                   crank.x - 12, crank.y - 24, 24, 3)
            sprite('props/room_handwheel_rotor.png', (0, 0, 24, 24),
                   crank.x - 12, crank.y - 48, 24, 24, angle=-room.chamber.angle)
        for projector, (target_x, target_y, _) in zip(room.projectors, room.projected_lights):
            x, y = projector.x, projector.y
            copper = x < room.start.x
            color = (209, 155, 103) if copper else (155, 183, 205)
            head = "props/projector_head_copper.png" if copper else "props/projector_head_silver.png"
            draw_projector_beam(backend, self.camera, x, y - 13, target_x, target_y, color)
            sprite("props/projector_stand.png", (0, 0, 15, 16), x - 7, y - 16, 15, 16)
            angle = atan2(y - 13 - target_y, target_x - x)
            sprite(head, (0, 0, 18, 12), x - 9, y - 19, 18, 12, angle=angle)
        if room.rail:
            rx, ry, _ = room.lights[1]
            sprite("props/chain_carriage.png", (0, 0, 13, 13), round(rx) - 6, round(ry) - 6, 13, 13)

        x, y = round(room.x), round(room.y)
        if death is not None:
            frame = sum(death >= start for start in DEATH_FRAME_STARTS[1:])
            sheet = "characters/player/raincoat_child_shadow_death.png"
        else:
            sheet = "characters/player/raincoat_child.png"
            if not room.grounded:
                frame = 5 if room.vy < 0 else 6
            elif room.walk_time:
                frame = 1 + int(room.walk_time * 12) % 4
            else:
                frame = 0
        if self.intro is not None:
            pose = sum(self.intro >= mark for mark in (0.92, 1.52, 2.20))
            sprite(f"characters/story/rise_{pose}.png", (0, 0, 21, 20), x - 10, y - 20, 21, 20)
        else:
            sprite(sheet, (frame * 21, 0, 21, 22), x - 10, y - 20, 21, 22, flip=room.facing < 0)

        if room.carrying_lantern:
            if death is None or death < DEATH_FRAME_STARTS[1]:
                sprite("props/light_orb.png", (16, 2, 3, 3),
                       round(lx) - 1, round(ly) - 1, 3, 3)
        else:
            sprite("props/light_orb.png", (0, 0, 7, 7), round(lx) - 3, round(ly) - 3, 7, 7)
        if self.intro is None and (target := room.interaction()):
            sx, sy = target.x - 2, target.y - 22
            if target.kind == 'RoomCrank':
                sy = target.y - 64
            if relay := room.switch_relays.get(target.name):
                sy = min(sy, relay.y - 15)
            rect(sx - 2, sy - 2, 8, 9, (20, 19, 29))
            rect(sx, sy, 1, 5, (255, 221, 170))
            for offset in (0, 2, 4):
                rect(sx, sy + offset, 3, 1, (255, 221, 170))

        if (locked and self.intro is None and death is None and room.respawn_elapsed is None
                and abs(room.x - (door.x + door.width / 2)) <= 29
                and abs(room.y - (door.y + door.height)) <= 23
                and (hint := exit_hint(room))):
            x, y, _, _ = self.camera.screen_rect(door.x + door.width / 2, door.y, 0, 0)
            panel_width = 432
            margin = panel_width // 2 + 12
            x = max(margin, min(self.camera.width - margin, x))
            y = min(y + 16, self.camera.height - 78)
            backend.overlay((x - panel_width // 2, y, panel_width, 64), (11, 14, 21, 229))
            backend.text(HINT_FONT, 22, hint[0], x, y + 43, (235, 218, 183))
            backend.text(HINT_FONT, 18, hint[1], x, y + 19, (207, 211, 215))

        if self.intro is not None and self.intro < 0.55:
            backend.overlay((0, 0, self.camera.width, self.camera.height),
                            (0, 0, 0, round(255 * (1 - self.intro / 0.55))))
        elif death is not None and death >= DEATH_FADE_START:
            fade = (death - DEATH_FADE_START) / (room.DEATH_DURATION - DEATH_FADE_START)
            backend.overlay((0, 0, self.camera.width, self.camera.height), (0, 0, 0, round(255 * fade)))
        elif room.respawn_elapsed is not None:
            fade = 1 - room.respawn_elapsed / room.RESPAWN_DURATION
            backend.overlay((0, 0, self.camera.width, self.camera.height), (0, 0, 0, round(255 * fade)))
