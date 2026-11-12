"""pico2d/SDL 의존성을 모아 로더와 게임 상태를 창 없이 검사할 수 있게 한다."""

from dataclasses import dataclass
from pathlib import Path
import ctypes

from game.world_effects import shadow_lamp_pixel


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
        # pico2d Image의 소멸자가 살아 있는 renderer에서 texture를 정리하게 한다.
        self.images.clear()
        if self.opened:
            self.pico.close_canvas()
            self.opened = False

    def poll_events(self):
        sdl = self.sdl
        key_names = {sdl.SDLK_ESCAPE: "escape", sdl.SDLK_LEFT: "left",
                     sdl.SDLK_RIGHT: "right", sdl.SDLK_UP: "up",
                     sdl.SDLK_DOWN: "down", sdl.SDLK_r: "r", sdl.SDLK_F1: "f1",
                     sdl.SDLK_SPACE: "space", sdl.SDLK_a: "a", sdl.SDLK_d: "d",
                     sdl.SDLK_LSHIFT: "shift_left", sdl.SDLK_RSHIFT: "shift_right", sdl.SDLK_F3: "f3", sdl.SDLK_e: "e"}
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
        key = (sprite.image, sprite.palette)
        image = self.images.get(key)
        if image is None:
            image = self._load_palette_image(sprite.image) if sprite.palette == "shadow_lamp" else self.pico.load_image(str(sprite.image))
            self.sdl.SDL_SetTextureScaleMode(image.texture, self.sdl.SDL_ScaleModeNearest)
            self.images[key] = image
        self.sdl.SDL_SetTextureColorMod(image.texture, *sprite.tint)
        image.opacify(sprite.opacity)
        x, y_top, w, h = sprite.source
        dx, dy, dw, dh = rect
        if sprite.flip_x:
            image.clip_composite_draw(x, image.h - y_top - h, w, h, 0, "h",
                                      dx + dw / 2, dy + dh / 2, dw, dh)
        else:
            image.clip_draw_to_origin(x, image.h - y_top - h, w, h, dx, dy, dw, dh)

    def _load_palette_image(self, path):
        """원본 PNG는 그대로 두고 SDL 메모리 표면에서 램프의 두 밝은 색만 바꾼다."""
        from sdl2.sdlimage import IMG_Load
        sdl = self.sdl
        original = IMG_Load(str(path).encode("utf-8"))
        if not original:
            raise RuntimeError(f"Cannot load lamp image: {path}")
        try:
            surface = sdl.SDL_ConvertSurfaceFormat(original, sdl.SDL_PIXELFORMAT_RGBA32, 0)
        finally:
            sdl.SDL_FreeSurface(original)
        if not surface:
            raise RuntimeError("Cannot prepare lamp palette")
        try:
            if sdl.SDL_LockSurface(surface) != 0:
                raise RuntimeError("Cannot lock lamp palette")
            try:
                pixels = ctypes.cast(surface.contents.pixels, ctypes.POINTER(ctypes.c_uint8))
                for y in range(surface.contents.h):
                    for x in range(surface.contents.w):
                        i = y * surface.contents.pitch + x * 4
                        rgba = shadow_lamp_pixel(tuple(pixels[i + c] for c in range(4)))
                        for c, value in enumerate(rgba):
                            pixels[i + c] = value
            finally:
                sdl.SDL_UnlockSurface(surface)
            texture = sdl.SDL_CreateTextureFromSurface(self.native.renderer, surface)
            if not texture:
                raise RuntimeError("Cannot create lamp palette texture")
            sdl.SDL_SetTextureBlendMode(texture, sdl.SDL_BLENDMODE_BLEND)
            return self.pico.Image(texture)
        finally:
            sdl.SDL_FreeSurface(surface)

    def rectangle(self, rect, color, filled=False):
        x, y, width, height = rect
        self.pico.draw_rectangle(x, y, x + width, y + height, *color, filled=filled)

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
