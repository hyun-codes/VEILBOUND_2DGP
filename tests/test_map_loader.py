import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from game.app import PROJECT_ROOT, STAGE_1
from game.map_loader import load_map, MapFormatError
from game.map_scene import MapScene
from game.camera import Camera


class Recorder:
    def __init__(self):
        self.sprites = []

    def sprite(self, sprite, rect):
        self.sprites.append((sprite, rect))

    def rectangle(self, *args, **kwargs):
        pass

    def label(self, *args):
        pass


class MapLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="map_test_", dir=PROJECT_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "fixture.tmj"
        self.data = json.loads(STAGE_1.read_text(encoding="utf-8"))

        def relocate(value):
            if isinstance(value, list):
                return [relocate(v) for v in value]
            if isinstance(value, dict):
                return {k: os.path.relpath((STAGE_1.parent / v).resolve(), self.path.parent).replace("\\", "/")
                        if k in ("image", "source") and isinstance(v, str) else relocate(v)
                        for k, v in value.items()}
            return value

        self.data = relocate(self.data)

    def load_fixture(self):
        self.path.write_text(json.dumps(self.data), encoding="utf-8")
        return load_map(self.path)

    def test_actual_stage_coordinates_and_relative_paths_from_another_cwd(self):
        previous = Path.cwd()
        try:
            os.chdir(self.temp.name)
            stage = load_map(STAGE_1)
        finally:
            os.chdir(previous)
        self.assertEqual((stage.width, stage.height), (640, 240))
        self.assertEqual(len(stage.objects), 3)
        self.assertEqual(stage.object_named("PlayerStart").y, 183)
        self.assertEqual(stage.object_named("Exit").y + stage.object_named("Exit").height, 167)
        self.assertTrue(all(sprite.image.is_file() for sprite in stage.sprites))

    def test_nested_group_offset_moves_objects_and_sprites_consistently(self):
        original = self.load_fixture()
        # Common 하위 소품과 별도 Objects를 같은 새 부모 아래 넣는다.
        self.data["layers"] = [{"type": "group", "name": "parent", "offsetx": 7,
                                "offsety": 11, "layers": self.data["layers"]}]
        moved = self.load_fixture()
        self.assertEqual(moved.sprites[0].x, original.sprites[0].x + 7)
        self.assertEqual(moved.sprites[0].y, original.sprites[0].y + 11)
        self.assertEqual(moved.object_named("PlayerStart").x, 35)
        self.assertEqual(moved.object_named("PlayerStart").y, 194)
        self.assertEqual(moved.solids[0].x, original.solids[0].x + 7)
        self.assertEqual(moved.solids[0].y, original.solids[0].y + 11)

    def test_world_preview_uses_hidden_shadow_layer_and_resets_tint_per_sprite(self):
        stage = self.load_fixture()
        camera = Camera(stage.width, stage.height)
        real, shadow = Recorder(), Recorder()
        MapScene(stage, "real").draw(real, camera)
        MapScene(stage, "shadow").draw(shadow, camera)
        self.assertTrue(any(s.world == "real" for s, _ in real.sprites))
        self.assertFalse(any(s.world == "shadow" for s, _ in real.sprites))
        self.assertTrue(any(s.world == "shadow" and s.tint == (157, 181, 223) for s, _ in shadow.sprites))
        self.assertFalse(any(s.world == "real" for s, _ in shadow.sprites))
        self.assertTrue(any(s.world == "common" and s.tint == (255, 255, 255) for s, _ in shadow.sprites))

    def test_unknown_gid_and_flips_fail_instead_of_drawing_wrong_tile(self):
        original = copy.deepcopy(self.data)
        for gid in (9999, 0x80000002):
            self.data = copy.deepcopy(original)
            layer = next(l for l in self.data["layers"] if l["name"] == "RealOnly")
            layer["data"][0] = gid
            with self.assertRaises(MapFormatError):
                self.load_fixture()

    def test_missing_image_and_bad_tile_array_have_clear_errors(self):
        original = copy.deepcopy(self.data)
        self.data["layers"][0]["layers"][0]["image"] = "missing.png"
        with self.assertRaisesRegex(MapFormatError, "Cannot read image"):
            self.load_fixture()
        self.data = original
        self.data["layers"][1]["data"] = []
        with self.assertRaisesRegex(MapFormatError, "tile array"):
            self.load_fixture()

    def test_non_image_objects_do_not_become_solid_or_rendered_sprites(self):
        stage = self.load_fixture()
        self.assertEqual({obj.kind for obj in stage.objects}, {"PlayerStart", "Exit", "PuzzleRegion"})
        self.assertFalse(stage.object_named("BridgeGap").properties["solid"])
