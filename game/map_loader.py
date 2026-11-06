"""현재 사용하는 유한 직교 TMJ/외부 TSJ를 그래픽 라이브러리 없이 읽는다."""

from dataclasses import dataclass
from pathlib import Path
import json
import math
import struct

from game.collision import Solid


class MapFormatError(ValueError):
    pass


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MapFormatError(f"Cannot read JSON {path}: {exc}") from exc


def _png_size(path):
    try:
        with path.open("rb") as stream:
            header = stream.read(24)
        if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
            raise ValueError("Only PNG images are supported")
        return struct.unpack(">II", header[16:24])
    except (OSError, ValueError) as exc:
        raise MapFormatError(f"Cannot read image {path}: {exc}") from exc


def _color(text):
    if not isinstance(text, str) or not text.startswith("#") or len(text) not in (7, 9):
        raise MapFormatError(f"Unsupported color: {text!r}")
    try:
        rgb = text[-6:]
        return tuple(int(rgb[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError as exc:
        raise MapFormatError(f"Invalid color: {text!r}") from exc


@dataclass(frozen=True)
class Sprite:
    image: Path
    source: tuple  # x, y_top, width, height in the PNG
    x: float
    y: float
    width: float
    height: float
    world: str = "common"
    opacity: float = 1.0
    tint: tuple = (255, 255, 255)
    repeat_x: bool = False
    repeat_y: bool = False
    flip_x: bool = False
    visual_role: str = "none"
    palette: str = "original"


@dataclass(frozen=True)
class MapObject:
    name: str
    kind: str
    x: float
    y: float
    width: float
    height: float
    properties: dict


@dataclass(frozen=True)
class MapData:
    path: Path
    width: int
    height: int
    background: tuple
    sprites: tuple
    objects: tuple
    solids: tuple = ()

    def object_named(self, name):
        found = [obj for obj in self.objects if obj.name == name]
        if len(found) != 1:
            raise MapFormatError(f"Expected exactly one {name!r} object in {self.path}")
        return found[0]


def load_map(path):
    path = Path(path).resolve()
    root = _read_json(path)
    if root.get("orientation") != "orthogonal" or root.get("infinite", False):
        raise MapFormatError("Only finite orthogonal maps are supported")
    if root.get("renderorder", "right-down") != "right-down":
        raise MapFormatError("Only right-down render order is supported")
    tw, th = root["tilewidth"], root["tileheight"]
    if min(tw, th, root["width"], root["height"]) <= 0:
        raise MapFormatError("Map dimensions must be positive")
    images, tiles, sprites, objects, solids = {}, {}, [], [], []
    collision_tops = {}
    visual_roles = {}

    def image_info(owner, spec):
        image = (owner.parent / spec["image"]).resolve()
        if image not in images:
            images[image] = _png_size(image)
        iw, ih = images[image]
        for key, actual in (("imagewidth", iw), ("imageheight", ih)):
            if key in spec and spec[key] != actual:
                raise MapFormatError(f"Image dimensions disagree: {image}")
        if spec.get("transparentcolor") or spec.get("trans"):
            raise MapFormatError("Color-key transparency is not supported")
        return image, iw, ih

    for reference in root.get("tilesets", []):
        if "source" not in reference:
            raise MapFormatError("Use an external TSJ tileset")
        owner = (path.parent / reference["source"]).resolve()
        ts = _read_json(owner)
        definitions = {t["id"]: {p["name"]: p["value"] for p in t.get("properties", [])}
                       for t in ts.get("tiles", [])}
        if ts.get("objectalignment", "bottomleft") not in ("bottomleft", "unspecified"):
            raise MapFormatError(f"Unsupported tile object alignment: {owner}")
        if any("animation" in t for t in ts.get("tiles", [])):
            raise MapFormatError("Animated tiles are not supported yet")
        offset = ts.get("tileoffset", {})
        if offset.get("x", 0) or offset.get("y", 0):
            raise MapFormatError("Tileset drawing offsets are not supported yet")
        entries = []
        if "image" in ts:
            image, iw, ih = image_info(owner, ts)
            cw, ch, cols = ts["tilewidth"], ts["tileheight"], ts["columns"]
            margin, spacing = ts.get("margin", 0), ts.get("spacing", 0)
            if min(cw, ch, cols) <= 0 or min(margin, spacing) < 0:
                raise MapFormatError(f"Invalid tileset grid: {owner}")
            for local in range(ts["tilecount"]):
                x = margin + local % cols * (cw + spacing)
                y = margin + local // cols * (ch + spacing)
                if x + cw > iw or y + ch > ih:
                    raise MapFormatError(f"Tile {local} exceeds image: {owner}")
                entries.append((local, image, (x, y, cw, ch)))
        else:
            for tile in ts.get("tiles", []):
                image, iw, ih = image_info(owner, tile)
                entries.append((tile["id"], image, (0, 0, iw, ih)))
        for local, image, rect in entries:
            gid = reference["firstgid"] + local
            if gid <= 0 or gid in tiles:
                raise MapFormatError(f"Overlapping/invalid GID: {gid}")
            tiles[gid] = (image, rect)
            inset = definitions.get(local, {}).get("collisionTop", 0)
            if not isinstance(inset, (int, float)) or not math.isfinite(inset) or not 0 <= inset < rect[3]:
                raise MapFormatError(f"Invalid collisionTop for GID {gid}")
            collision_tops[gid] = inset
            visual_roles[gid] = definitions.get(local, {}).get("visualRole", "prop")

    def tile(gid):
        if gid & 0xF0000000:
            raise MapFormatError("Flipped/rotated tile GIDs are not supported yet")
        if gid not in tiles:
            raise MapFormatError(f"Unknown tile GID: {gid}")
        return tiles[gid]

    def walk(layers, px=0, py=0, world="common", opacity=1.0, tint=(255, 255, 255), visible=True, solid=False):
        for layer in layers:
            name, kind = layer.get("name", ""), layer["type"]
            props = {p["name"]: p["value"] for p in layer.get("properties", [])}
            is_solid = props.get("solid", solid)
            declared = props.get("world", {"RealOnly": "real", "ShadowOnly": "shadow"}.get(name))
            active_world = {"both": "common", None: world}.get(declared, declared)
            if active_world not in ("common", "real", "shadow"):
                raise MapFormatError(f"Unknown world tag: {active_world}")
            # ShadowOnly의 에디터 숨김은 실행 시 영구 비활성화를 뜻하지 않는다.
            show = visible and (True if declared in ("real", "shadow") else layer.get("visible", True))
            if not show:
                continue
            if layer.get("parallaxx", 1) != 1 or layer.get("parallaxy", 1) != 1:
                raise MapFormatError("Parallax layers are not supported yet")
            if layer.get("x", 0) or layer.get("y", 0):
                raise MapFormatError("Use pixel offsetx/offsety instead of layer x/y")
            x, y = px + layer.get("offsetx", 0), py + layer.get("offsety", 0)
            alpha = opacity * layer.get("opacity", 1.0)
            if not all(math.isfinite(v) for v in (x, y, alpha)) or not 0 <= alpha <= 1:
                raise MapFormatError(f"Invalid layer transform: {name}")
            rgb = _color(layer["tintcolor"]) if "tintcolor" in layer else (255, 255, 255)
            color = tuple(round(a * b / 255) for a, b in zip(tint, rgb))
            if kind == "group":
                walk(layer["layers"], x, y, active_world, alpha, color, show, is_solid)
            elif kind == "imagelayer":
                image, iw, ih = image_info(path, layer)
                sprites.append(Sprite(image, (0, 0, iw, ih), x, y, iw, ih,
                                      active_world, alpha, color,
                                      layer.get("repeatx", False), layer.get("repeaty", False),
                                      visual_role=props.get("visualRole", "fog" if name == "Low fog" else "background")))
            elif kind == "tilelayer":
                data = layer.get("data")
                if not isinstance(data, list) or len(data) != layer["width"] * layer["height"]:
                    raise MapFormatError(f"Expected uncompressed tile array: {name}")
                for i, gid in enumerate(data):
                    if not gid:
                        continue
                    image, rect = tile(gid)
                    cw, ch = rect[2:]
                    sprites.append(Sprite(image, rect, x + i % layer["width"] * tw,
                                          y + (i // layer["width"] + 1) * th - ch,
                                          cw, ch, active_world, alpha, color, visual_role="terrain"))
                    if is_solid:
                        item = sprites[-1]
                        inset = collision_tops[gid]
                        solids.append(Solid(item.x, item.y + inset, cw, ch - inset, active_world))
            elif kind == "objectgroup":
                for obj in layer.get("objects", []):
                    if not obj.get("visible", True):
                        continue
                    if obj.get("rotation", 0):
                        raise MapFormatError("Rotated objects are not supported yet")
                    ox, oy = x + obj["x"], y + obj["y"]
                    if "gid" in obj:
                        image, rect = tile(obj["gid"])
                        w, h = obj.get("width", rect[2]), obj.get("height", rect[3])
                        sprites.append(Sprite(image, rect, ox, oy - h, w, h,
                                              active_world, alpha * obj.get("opacity", 1), color,
                                              visual_role=visual_roles[obj["gid"]]))
                    else:
                        if any(k in obj for k in ("ellipse", "polygon", "polyline", "text", "template")):
                            raise MapFormatError("Only point/rectangle game objects are supported")
                        objects.append(MapObject(obj.get("name", ""), obj.get("type", obj.get("class", "")),
                                                 ox, oy, obj.get("width", 0), obj.get("height", 0),
                                                 {p["name"]: p["value"] for p in obj.get("properties", [])}))
            else:
                raise MapFormatError(f"Unsupported layer type: {kind}")

    walk(root["layers"])
    result = MapData(path, root["width"] * tw, root["height"] * th,
                     _color(root.get("backgroundcolor", "#272a39")), tuple(sprites), tuple(objects), tuple(solids))
    result.object_named("PlayerStart")
    result.object_named("Exit")
    return result
