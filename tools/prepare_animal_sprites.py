"""AI 동물 시트를 원본 에셋 팔레트·64px 셀에 맞추는 오프라인 작업.

Pillow가 필요하다. 게임 실행에는 사용하지 않으며 기존 캐릭터 PNG는 수정하지 않는다.
"""

from pathlib import Path
import hashlib
import json

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ANIMALS = ROOT / "assets" / "characters" / "animals"
PALETTE = ((89, 87, 87), (128, 123, 122), (42, 30, 35), (79, 52, 47))
CONFIGS = {"rat": (13, 5), "cat": (16, 9)}
ALPHA_CUTOFF = 230
COVERAGE_CUTOFF = 96


def prepare(species, size):
    folder = ANIMALS / species
    source = folder / "generated" / f"{species}_walk_ai_source.png"
    with Image.open(source) as image:
        raw = image.convert("RGBA")
    if raw.size != (1536, 1024):
        raise ValueError(f"Unexpected source size: {source}: {raw.size}")
    cells, bounds = [], []
    for i in range(6):
        x, y = i % 3 * 512, i // 3 * 512
        cell = raw.crop((x, y, x + 512, y + 512))
        alpha = cell.getchannel("A").point(lambda a: 255 if a >= ALPHA_CUTOFF else 0)
        cell.putalpha(alpha)
        box = alpha.getbbox()
        if box is None:
            raise ValueError(f"Empty source frame: {species}/{i}")
        cells.append(cell)
        bounds.append(box)
    # 공통 X 범위와 높이를 사용한다. 프레임별 발 끝의 1~2px 원본 오차만 정렬한다.
    left, right = min(b[0] for b in bounds), max(b[2] for b in bounds)
    height = max(b[3] for b in bounds) - min(b[1] for b in bounds)
    frames = []
    sheet = Image.new("RGBA", (64 * 6, 64))
    for i, (cell, box) in enumerate(zip(cells, bounds)):
        body = cell.crop((left, box[3] - height, right, box[3])).resize(size, Image.Resampling.BOX)
        pixels = []
        for r, g, b, a in (body.getpixel((x, y)) for y in range(body.height) for x in range(body.width)):
            if a < COVERAGE_CUTOFF:
                pixels.append((0, 0, 0, 0))
            else:
                color = min(PALETTE, key=lambda c: (c[0] - r) ** 2 + (c[1] - g) ** 2 + (c[2] - b) ** 2)
                pixels.append((*color, 255))
        body.putdata(pixels)
        frame = Image.new("RGBA", (64, 64))
        frame.paste(body, (32 - size[0] // 2, 44 - size[1]))
        if frame.getbbox() is None:
            raise ValueError(f"Empty prepared frame: {species}/{i}")
        frames.append(frame)
        sheet.paste(frame, (i * 64, 0))
    output = folder / f"{species}_walk.png"
    sheet.save(output)
    metadata = {
        "format": "veilbound-grid-animations", "schema_version": 1,
        "image": output.name, "image_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "image_size": {"width": 384, "height": 64},
        "grid": {"cell_width": 64, "cell_height": 64, "columns": 6, "rows": 1, "margin": 0, "spacing": 0},
        "coordinates": {"origin": "top_left", "index_base": 0, "units": "source_pixels"},
        "anchor": {"x": 32, "y": 44, "origin": "frame_top_left", "status": "prepared_shared_feet_reference_not_gameplay_verified"},
        "source_facing": "right", "default_animation": "walk",
        "timing_status": "initial_tuning_values_not_playtested",
        "runtime_status": "asset_only_not_integrated",
        "animations": {"walk": {"enabled": True, "loop": True, "row": 0, "columns": list(range(6)), "frame_duration_ms": 100}},
        "provenance": {
            "type": "ai_generated_then_python_pixel_cleanup", "source": f"generated/{source.name}",
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "source_grid": {"columns": 3, "rows": 2, "cell_width": 512, "cell_height": 512},
            "processor": "tools/prepare_animal_sprites.py", "body_box_size": list(size),
            "alpha_cutoff": ALPHA_CUTOFF, "coverage_cutoff": COVERAGE_CUTOFF,
            "palette_rgb": [list(c) for c in PALETTE],
        },
    }
    (folder / "animations.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(species, "bounds", [f.getbbox() for f in frames], "unique", len({f.tobytes() for f in frames}))
    return frames


if __name__ == "__main__":
    for species, size in CONFIGS.items():
        prepare(species, size)
