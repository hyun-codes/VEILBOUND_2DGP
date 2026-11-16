"""pico2d/SDL 의존성을 모아 로더와 게임 상태를 창 없이 검사할 수 있게 한다."""

from dataclasses import dataclass
from pathlib import Path
import ctypes

@dataclass(frozen=True)
class InputEvent:
    kind: str
    key: str = ""
    x: int = 0
    y: int = 0


class Pico2DBackend:
    def __init__(self):
        import pico2d
        from pico2d import pico2d as native
        import sdl2
        self.pico, self.native, self.sdl = pico2d, native, sdl2
        self.images = {}
        self.fonts = {}
        self.labels = {}
        self.opened = False

    def open(self, width, height):
        self.sdl.SDL_SetHint(self.sdl.SDL_HINT_RENDER_SCALE_QUALITY, b"0")
        self.pico.open_canvas(width, height, sync=False)
        self.opened = True
        if not self.native.window or not self.native.renderer:
            raise RuntimeError("SDL could not create a game window/renderer")
        self.pico.hide_lattice()
        self.sdl.SDL_SetWindowTitle(self.native.window, b"VEILBOUND")
        self.sdl.SDL_SetRenderDrawBlendMode(self.native.renderer, self.sdl.SDL_BLENDMODE_BLEND)

    def close(self):
        self.images.clear()
        self.labels.clear()
        for font in self.fonts.values():
            self.native.TTF_CloseFont(font.font)
        self.fonts.clear()
        if self.opened:
            self.pico.close_canvas()
            self.opened = False

    def poll_events(self):
        sdl = self.sdl
        key_names = {sdl.SDLK_ESCAPE: "escape", sdl.SDLK_LEFT: "left",
                     sdl.SDLK_RIGHT: "right",
                     sdl.SDLK_UP: "up", sdl.SDLK_DOWN: "down", sdl.SDLK_RETURN: "enter",
                     sdl.SDLK_KP_ENTER: "enter", sdl.SDLK_w: "w", sdl.SDLK_s: "s",
                     sdl.SDLK_r: "r",
                     sdl.SDLK_SPACE: "space", sdl.SDLK_a: "a", sdl.SDLK_d: "d",
                     sdl.SDLK_e: "e"}
        event = sdl.SDL_Event()
        result = []
        while sdl.SDL_PollEvent(ctypes.byref(event)):
            if event.type == sdl.SDL_QUIT:
                result.append(InputEvent("quit"))
            elif event.type == sdl.SDL_WINDOWEVENT:
                if event.window.event == sdl.SDL_WINDOWEVENT_FOCUS_LOST:
                    result.append(InputEvent("focus_lost"))
                elif event.window.event == sdl.SDL_WINDOWEVENT_FOCUS_GAINED:
                    result.append(InputEvent("focus_gained"))
                elif event.window.event == sdl.SDL_WINDOWEVENT_CLOSE:
                    result.append(InputEvent("quit"))
            elif event.type == sdl.SDL_MOUSEMOTION:
                result.append(InputEvent("hover", x=event.motion.x, y=self.pico.get_canvas_height() - event.motion.y - 1))
            elif event.type == sdl.SDL_MOUSEBUTTONDOWN and event.button.button == sdl.SDL_BUTTON_LEFT:
                result.append(InputEvent("click", x=event.button.x, y=self.pico.get_canvas_height() - event.button.y - 1))
            elif event.type in (sdl.SDL_KEYDOWN, sdl.SDL_KEYUP) and not event.key.repeat:
                key = key_names.get(event.key.keysym.sym)
                if key:
                    result.append(InputEvent("key_down" if event.type == sdl.SDL_KEYDOWN else "key_up", key))
        return result

    def begin(self, color):
        self.sdl.SDL_SetRenderDrawColor(self.native.renderer, *color, 255)
        self.sdl.SDL_RenderClear(self.native.renderer)

    def rectangle(self, rect, color, filled=False):
        x, y, width, height = rect
        self.pico.draw_rectangle(x, y, x + width, y + height, *color, filled=filled)

    def overlay(self, rect, color):
        x, y, width, height = rect
        window_height = self.pico.get_canvas_height()
        area = self.sdl.SDL_Rect(x, window_height - y - height, width, height)
        self.sdl.SDL_SetRenderDrawColor(self.native.renderer, *color)
        self.sdl.SDL_RenderFillRect(self.native.renderer, ctypes.byref(area))

    def image(self, path, source, destination, flip=False, angle=0.0):
        image = self.images.get(path)
        if image is None:
            image = self.pico.load_image(str(path))
            self.sdl.SDL_SetTextureScaleMode(image.texture, self.sdl.SDL_ScaleModeNearest)
            self.images[path] = image
        x, y, width, height = source
        y = image.h - y - height
        dx, dy, dw, dh = destination
        if flip or angle:
            image.clip_composite_draw(x, y, width, height, angle, "h" if flip else "",
                                      dx + dw / 2, dy + dh / 2, dw, dh)
        else:
            image.clip_draw_to_origin(x, y, width, height, dx, dy, dw, dh)

    def present(self):
        self.pico.update_canvas()

    def text(self, path, size, value, x, y, color):
        key = path, size, value, color
        label = self.labels.get(key)
        if label is None:
            font_key = path, size
            if font_key not in self.fonts:
                self.fonts[font_key] = self.pico.load_font(str(path), size)
            font = self.fonts[font_key]
            surface = self.native.TTF_RenderUTF8_Blended(
                font.font, value.encode("utf-8"), self.sdl.SDL_Color(*color, 255))
            if not surface:
                raise RuntimeError(f"Could not rasterize menu text: {value}")
            try:
                texture = self.sdl.SDL_CreateTextureFromSurface(self.native.renderer, surface)
            finally:
                self.sdl.SDL_FreeSurface(surface)
            if not texture:
                raise RuntimeError(f"Could not load menu label: {value}")
            label = self.native.Image(texture)
            self.labels[key] = label
        label.draw(x, y)

    def save_screenshot(self, path, width, height):
        """점검용: present 전에 실제 SDL back buffer를 BMP로 저장한다."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        sdl = self.sdl
        surface = sdl.SDL_CreateRGBSurfaceWithFormat(0, width, height, 32, sdl.SDL_PIXELFORMAT_ARGB8888)
        if not surface:
            raise RuntimeError("Could not allocate screenshot surface")
        try:
            if sdl.SDL_RenderReadPixels(self.native.renderer, None, sdl.SDL_PIXELFORMAT_ARGB8888,
                                        surface.contents.pixels, surface.contents.pitch) != 0:
                raise RuntimeError("Could not read rendered pixels")
            if sdl.SDL_SaveBMP(surface, str(path).encode("utf-8")) != 0:
                raise RuntimeError(f"Could not save screenshot: {path}")
        finally:
            sdl.SDL_FreeSurface(surface)
