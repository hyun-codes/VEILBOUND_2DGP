"""Keyboard and mouse selection on the startup screen."""

from math import exp, sin
from pathlib import Path


ASSETS = Path(__file__).resolve().parents[1] / "assets"
FONT = ASSETS / "ui/fonts/Cinzel.ttf"
BACKGROUND = ASSETS / "ui/title_reservoir.png"
ORB = ASSETS / "props/light_orb.png"
TITLE_ROWS = (("PLAY", 293), ("SETTINGS", 244), ("QUIT", 195))
SETTINGS_ROWS = (("MENU MOTION", 232), ("BACK", 185))


class TitleScreen:
    def __init__(self):
        self.in_settings = False
        self.motion = True
        self.selected = 0
        self.orb_y = TITLE_ROWS[0][1]
        self.elapsed = 0.0

    @property
    def rows(self):
        return SETTINGS_ROWS if self.in_settings else TITLE_ROWS

    def handle(self, event):
        if event.kind in ("hover", "click"):
            selected = next((i for i, (_, y) in enumerate(self.rows)
                             if abs(event.y - y) <= 21 and 270 <= event.x <= 530), None)
            if selected is None:
                return None
            self.selected = selected
            if event.kind == "hover":
                return None
        elif event.kind == "key_down":
            if event.key in ("up", "w", "down", "s"):
                direction = -1 if event.key in ("up", "w") else 1
                self.selected = (self.selected + direction) % len(self.rows)
                return None
            if event.key == "escape":
                if self.in_settings:
                    self.open_settings(False)
                    return None
                return "quit"
            if event.key not in ("enter", "space"):
                return None
        else:
            return None

        if self.in_settings:
            if self.selected == 0:
                self.motion = not self.motion
            else:
                self.open_settings(False)
        elif self.selected == 1:
            self.open_settings(True)
        else:
            return "play" if self.selected == 0 else "quit"
        return None

    def open_settings(self, opened):
        self.in_settings = opened
        self.selected = 0 if opened else 1
        self.orb_y = self.rows[self.selected][1]

    def draw(self, backend, dt):
        backend.begin((8, 9, 16))
        backend.image(BACKGROUND, (0, 0, 400, 300), (0, 0, 800, 600))
        target_y = self.rows[self.selected][1]
        if self.motion:
            self.elapsed += dt
            self.orb_y += (target_y - self.orb_y) * (1 - exp(-18 * dt))
            orb_y = round(self.orb_y + 2 * sin(self.elapsed * 4))
        else:
            self.orb_y = orb_y = target_y

        ivory = (245, 244, 239)
        muted = (162, 165, 181)
        if self.in_settings:
            backend.text(FONT, 49, "Settings", 400, 453, ivory)
            backend.text(FONT, 19, "A / D    Move", 400, 381, muted)
            backend.text(FONT, 19, "Space    Jump", 400, 347, muted)
            backend.text(FONT, 19, "E    Interact     R    Restart", 400, 313, muted)
        else:
            backend.text(FONT, 74, "VEILBOUND", 400, 438, ivory)
            backend.overlay((343, 377, 114, 1), (186, 185, 198, 150))
            backend.image(ORB, (0, 0, 7, 7), (394, 371, 12, 12))
        for i, (label, y) in enumerate(self.rows):
            if self.in_settings and i == 0:
                label += "  ON" if self.motion else "  OFF"
            backend.text(FONT, 25, label, 400, y, ivory if i == self.selected else muted)
        orb_x = 242 if self.in_settings else 277
        backend.image(ORB, (0, 0, 7, 7), (orb_x, orb_y - 10, 21, 21))
