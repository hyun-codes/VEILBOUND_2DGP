"""Lantern room sprites and the light overlay, drawn at integer scale."""

from math import atan2, ceil, floor, hypot
from pathlib import Path

from game.camera import Camera
from game.lantern_room import light_span


ASSETS = Path(__file__).resolve().parents[1] / "assets"
DARKNESS_MASK = ASSETS / "environments/stage_01/lantern_darkness.png"
MASK_SIZE = 221
CHAIN_FRAMES = 8
CHAIN_FRAME_TRAVEL = 1.5
DEATH_KICK = ((4, -1), (-3, 1), (2, -1), (-1, 0))
SHOCK_DURATION = 0.18
DEATH_FADE_START = 0.30


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


class LanternView:
    def __init__(self, room, width, height):
        self.room = room
        self.camera = Camera(room.data.width, room.data.height, width, height, scale=3)

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

        backend.begin(room.data.background)
        sprite("environments/stage_01/pump_hall.png", (0, 0, 264, 200), 0, 0, room.data.width, room.data.height)
        for part in room.data.sprites:
            if part.visual_role == "backdrop":
                backend.image(part.image, part.source,
                              self.camera.screen_rect(part.x, part.y, part.width, part.height))
            elif part.visual_role == "hoist_chain":
                sx, sy, sw, sh = part.source
                frame = int(room.rail.distance_at(room.elapsed) / CHAIN_FRAME_TRAVEL) % CHAIN_FRAMES
                backend.image(part.image, (sx + frame * sw, sy, sw, sh),
                              self.camera.screen_rect(part.x, part.y, part.width, part.height))
        for ground in room.ground:
            ledge("tiles/stone_ledge.png", ground, 16)
        for p in room.platforms:
            ledge("tiles/lantern_ledge.png", p, 5)
        for part in room.data.sprites:
            if part.visual_role not in ("hoist_chain", "backdrop"):
                backend.image(part.image, part.source,
                              self.camera.screen_rect(part.x, part.y, part.width, part.height))
        for prop in room.props:
            if prop.kind == "Wall":
                ledge("tiles/stone_ledge.png", prop, 16)
            else:
                rect(prop.x, prop.y, prop.width, prop.height, (121, 88, 61))
                rect(prop.x, prop.y, prop.width, prop.height, (196, 151, 102), False)
        if crate := room.crate:
            sprite("props/cargo_crate.png", (0, 0, 16, 16), crate.x, crate.y, crate.width, crate.height)
        for index, key in enumerate(room.keys):
            if index not in room.collected:
                sprite("props/brass_key.png", (0, 0, 14, 10),
                       key.x + key.width / 2 - 7, key.y + key.height - 10, 14, 10)

        door = room.exit
        door_open = room.complete or (bool(room.exit_socket or room.beacons or room.switch_relays) and room.exit_ready)
        sprite("props/exit_door.png", (13 if door_open else 0, 0, 13, 24),
               door.x, door.y, door.width, door.height)
        for socket in room.sockets:
            sprite("props/lantern_socket.png", (0, 0, 10, 7), socket.x - 5, socket.y - 7, 10, 7)
            if socket.properties.get("releaseInLight"):
                open_cell = 9 if room.receiver_lit(socket) else 0
                sprite("props/lens_receiver.png", (open_cell, 0, 9, 11), socket.x + 6, socket.y - 11, 9, 11)
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
            sprite("props/vault_beacon.png", (frame, 0, 11, 14),
                   beacon.x - 5, beacon.y - 14, 11, 14)
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

        lx, ly, radius = room.light
        if len(room.lights) > 1:
            draw_combined_darkness(backend, self.camera, room.lights)
        else:
            draw_darkness(backend, self.camera, lx, ly, radius)
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
        if room.death_elapsed is not None:
            frame = min(5, int(6 * room.death_elapsed / room.DEATH_DURATION))
            sheet = "characters/player/shadow_child_death.png"
        else:
            sheet = "characters/player/shadow_child.png"
            if not room.grounded:
                frame = 5 if room.vy < 0 else 6
            elif room.walk_time:
                frame = 1 + int(room.walk_time * 12) % 4
            else:
                frame = 0
        sprite(sheet, (frame * 21, 0, 21, 22), x - 10, y - 20, 21, 22, flip=room.facing < 0)

        if room.carrying_lantern:
            if room.death_elapsed is None:
                sprite("props/light_orb.png", (16, 2, 3, 3),
                       round(lx) - 1, round(ly) - 1, 3, 3)
        else:
            sprite("props/light_orb.png", (0, 0, 7, 7), round(lx) - 3, round(ly) - 3, 7, 7)
        if target := room.interaction():
            sx, sy = target.x - 2, target.y - 22
            if relay := room.switch_relays.get(target.name):
                sy = min(sy, relay.y - 15)
            rect(sx - 2, sy - 2, 8, 9, (20, 19, 29))
            rect(sx, sy, 1, 5, (255, 221, 170))
            for offset in (0, 2, 4):
                rect(sx, sy + offset, 3, 1, (255, 221, 170))

        if death is not None and death < SHOCK_DURATION:
            frame = int(5 * death / SHOCK_DURATION)
            sprite("props/death_shock.png", (frame * 29, 0, 29, 29),
                   x - 14, y - room.CHEST_HEIGHT - 14, 29, 29)
        if death is not None and death >= DEATH_FADE_START:
            fade = (death - DEATH_FADE_START) / (room.DEATH_DURATION - DEATH_FADE_START)
            backend.overlay((0, 0, self.camera.width, self.camera.height), (0, 0, 0, round(255 * fade)))
        elif room.respawn_elapsed is not None:
            fade = 1 - room.respawn_elapsed / room.RESPAWN_DURATION
            backend.overlay((0, 0, self.camera.width, self.camera.height), (0, 0, 0, round(255 * fade)))
