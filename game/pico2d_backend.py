"""pico2d/SDL 의존성을 모아 로더와 게임 상태를 창 없이 검사할 수 있게 한다."""

from dataclasses import dataclass
from pathlib import Path
import ctypes


@dataclass(frozen=True)
class InputEvent:
    kind: str
    key: str = ""


class Pico2DBackend:
    def __init__(self):
        import pico2d
        from pico2d import pico2d as native
        import sdl2
        self.pico, self.native, self.sdl = pico2d, native, sdl2
        self.images = {}
        self.font = None
        self.opened = False

    def open(self, width, height):
        self.sdl.SDL_SetHint(self.sdl.SDL_HINT_RENDER_SCALE_QUALITY, b"0")
        self.pico.open_canvas(width, height, sync=False)
        self.opened = True
        if not self.native.window or not self.native.renderer:
            raise RuntimeError("SDL could not create a game window/renderer")
        self.pico.hide_lattice()
        self.sdl.SDL_SetWindowTitle(self.native.window, b"VEILBOUND - Stage 1 Map Preview")
        self.sdl.SDL_SetRenderDrawBlendMode(self.native.renderer, self.sdl.SDL_BLENDMODE_BLEND)
        font_path = Path(self.pico.__file__).parent / "data" / "ConsolaMalgun.ttf"
        self.font = self.pico.load_font(str(font_path), 15)

    def close(self):
        # pico2d Image의 소멸자가 살아 있는 renderer에서 texture를 정리하게 한다.
        self.images.clear()
        if self.font is not None:
            from sdl2.sdlttf import TTF_CloseFont
            TTF_CloseFont(self.font.font)
            self.font = None
        if self.opened:
            self.pico.close_canvas()
            self.opened = False

    def poll_events(self):
        sdl = self.sdl
        key_names = {sdl.SDLK_ESCAPE: "escape", sdl.SDLK_LEFT: "left",
                     sdl.SDLK_RIGHT: "right", sdl.SDLK_UP: "up",
                     sdl.SDLK_DOWN: "down", sdl.SDLK_r: "r", sdl.SDLK_F1: "f1"}
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
            elif event.type in (sdl.SDL_KEYDOWN, sdl.SDL_KEYUP) and not event.key.repeat:
                key = key_names.get(event.key.keysym.sym)
                if key:
                    result.append(InputEvent("key_down" if event.type == sdl.SDL_KEYDOWN else "key_up", key))
        return result

    def begin(self, color):
        self.sdl.SDL_SetRenderDrawColor(self.native.renderer, *color, 255)
        self.sdl.SDL_RenderClear(self.native.renderer)

    def sprite(self, sprite, rect):
        image = self.images.get(sprite.image)
        if image is None:
            image = self.pico.load_image(str(sprite.image))
            self.sdl.SDL_SetTextureScaleMode(image.texture, self.sdl.SDL_ScaleModeNearest)
            self.images[sprite.image] = image
        self.sdl.SDL_SetTextureColorMod(image.texture, *sprite.tint)
        image.opacify(sprite.opacity)
        x, y_top, w, h = sprite.source
        dx, dy, dw, dh = rect
        image.clip_draw_to_origin(x, image.h - y_top - h, w, h, dx, dy, dw, dh)

    def rectangle(self, rect, color, filled=False):
        x, y, width, height = rect
        self.pico.draw_rectangle(x, y, x + width, y + height, *color, filled=filled)

    def label(self, x, y, text, color=(244, 237, 228)):
        self.font.draw(x, y, text, color)

    def present(self):
        self.pico.update_canvas()

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
