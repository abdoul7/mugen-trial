import importlib
from pathlib import Path
import struct
import tempfile
import unittest

def require(name):
    try:
        module = importlib.import_module("mugen_prune")
    except ModuleNotFoundError:
        raise AssertionError("mugen_prune.py must exist") from None
    value = getattr(module, name, None)
    if not callable(value):
        raise AssertionError(f"mugen_prune.{name} must be callable")
    return value


class MinifyTests(unittest.TestCase):
    def test_minify_preserves_quoted_semicolons_and_removes_noise(self):
        source = (
            "; heading\r\n"
            "name = \"A;B\" ; trailing comment  \r\n"
            "\r\n"
            "  value = 1  \r\n"
            "  ; another comment\r\n"
        )
        self.assertEqual(
            'name = "A;B"\n  value = 1\n',
            require("minify_script")(source),
        )

    def test_minify_handles_empty_input_and_comment_only_files(self):
        self.assertEqual("", require("minify_script")(" ; one\n; two\n\n"))


class StatePruningTests(unittest.TestCase):
    def test_prunes_only_unreachable_states_and_follows_controller_targets(self):
        files = {
            "common1.cns": (
                "[Statedef 0]\n[State 0, go]\ntype = ChangeState\nvalue = 10\n"
                "[Statedef 10]\n[State 10, idle]\ntype = Null\n"
            ),
            "main.cns": (
                "[Statedef -1]\n[State -1, go]\ntype = ChangeState\nvalue = 100\n"
                "[Statedef 100]\n"
                "[State 100, hit]\ntype = HitDef\np1stateno = 200\np2stateno = 300\n"
                "[State 100, helper]\ntype = Helper\nstateno = 400\n"
                "[State 100, target]\ntype = TargetState\nvalue = 500\n"
                "[State 100, self]\ntype = SelfState\nvalue = 600\n"
                "[Statedef 200]\n[Statedef 300]\n[Statedef 400]\n"
                "[Statedef 500]\n[Statedef 600]\n"
                "[Statedef 999]\n[State 999, orphan]\ntype = Null\n"
            ),
        }
        result, stats = require("prune_state_scripts")(
            files, common_files={"common1.cns"}, command_files=set()
        )
        for number in (0, 10, -1, 100, 200, 300, 400, 500, 600):
            self.assertIn(f"[Statedef {number}]", result["main.cns"] if number not in (0, 10) else result["common1.cns"])
        self.assertNotIn("Statedef 999", result["main.cns"])
        self.assertNotIn("orphan", result["main.cns"])
        self.assertEqual(1, stats["removed"])

    def test_engine_invoked_states_are_kept_without_script_references(self):
        files = {
            "common1.cns": "[Statedef 0]\n",
            "custom.cns": "[Statedef 170]\n[Statedef 180]\n[Statedef 5900]\n[Statedef 5120]\n[Statedef 5500]\n[Statedef 9999]\n",
        }
        result, stats = require("prune_state_scripts")(files, common_files={"common1.cns"})
        for state in (170, 180, 5900, 5120, 5500):
            self.assertIn(f"Statedef {state}", result["custom.cns"])
        self.assertNotIn("Statedef 9999", result["custom.cns"])
        self.assertEqual(1, stats["removed"])

    def test_dynamic_target_in_reachable_state_conservatively_keeps_everything(self):
        files = {
            "common1.cns": "[Statedef 0]\n[State 0, go]\ntype = ChangeState\nvalue = 1000 + var(0)\n",
            "main.cns": "[Statedef 1000]\n[Statedef 9999]\n",
        }
        result, stats = require("prune_state_scripts")(
            files, common_files={"common1.cns"}, command_files=set()
        )
        self.assertIn("Statedef 9999", result["main.cns"])
        self.assertEqual(0, stats["removed"])
        self.assertTrue(stats["dynamic"])

    def test_dynamic_target_in_unreachable_state_does_not_keep_orphan(self):
        files = {
            "common1.cns": "[Statedef 0]\n",
            "main.cns": "[Statedef 999]\n[State 999, go]\ntype = SelfState\nvalue = var(0)\n",
        }
        result, stats = require("prune_state_scripts")(
            files, common_files={"common1.cns"}, command_files=set()
        )
        self.assertNotIn("Statedef 999", result["main.cns"])
        self.assertEqual(1, stats["removed"])

    def test_command_file_targets_are_roots_and_duplicate_definitions_survive(self):
        files = {
            "common1.cns": "[Statedef 0]\n",
            "custom.cmd": "[Statedef 42]\n[State 42, go]\ntype = ChangeState\nvalue = 123\n",
            "a.cns": "[Statedef 123]\n[State 123, a]\ntype = Null\n",
            "b.cns": "[Statedef 123]\n[State 123, b]\ntype = Null\n",
        }
        result, stats = require("prune_state_scripts")(
            files, common_files={"common1.cns"}, command_files={"custom.cmd"}
        )
        self.assertNotIn("Statedef 42", result["custom.cmd"])
        self.assertIn("State 123, a", result["a.cns"])
        self.assertIn("State 123, b", result["b.cns"])
        self.assertEqual(1, stats["removed"])


def make_pcx(tag, palette=None):
    data = bytes([tag]) * 128 + b"pixels"
    if palette is not None:
        data += b"\x0c" + bytes([palette]) * 768
    return data


def make_v1(records):
    header = bytearray(512)
    header[:12] = b"ElecbyteSpr\x00"
    header[12:16] = bytes((0, 1, 0, 1))
    struct.pack_into("<IIII", header, 16, len({r[0] for r in records}), len(records), 512, 32)
    offsets = []
    offset = 512
    for _, _, data, _, _ in records:
        offsets.append(offset)
        offset += 32 + len(data)
    body = bytearray()
    for index, (group, item, data, link, same) in enumerate(records):
        next_offset = offsets[index + 1] if index + 1 < len(records) else 0
        body += struct.pack("<IIhhhhhB12sx", next_offset, len(data), 0, 0, group, item, link, same, b"")
        body += data
    return bytes(header + body)


def read_v1(data):
    records = []
    offset = struct.unpack_from("<I", data, 24)[0]
    while offset and offset + 32 <= len(data):
        values = struct.unpack_from("<IIhhhhhB", data, offset)
        records.append({
            "group": values[4], "item": values[5], "length": values[1],
            "link": values[6], "same": values[7], "data": data[offset + 32:offset + 32 + values[1]],
        })
        if values[0] <= offset:
            break
        offset = values[0]
    return records


def make_v2():
    palette = b"PALPAL!!"
    sprite0 = struct.pack("<HHHHhhHBBIIHH", 0, 0, 1, 1, 0, 0, 0, 0, 8, 8, 4, 0, 0)
    sprite1 = struct.pack("<HHHHhhHBBIIHH", 1, 0, 1, 1, 0, 0, 0, 0, 8, 0, 4, 0, 1)
    linked = struct.pack("<HHHHhhHBBIIHH", 2, 0, 1, 1, 0, 0, 1, 0, 8, 0, 0, 0, 0)
    palette_record = struct.pack("<HHHHII", 0, 0, 256, 0, 0, len(palette))
    header = bytearray(512)
    header[:12] = b"ElecbyteSpr\x00"
    header[12:16] = bytes((0, 1, 0, 2))
    struct.pack_into("<IIII", header, 36, 528, 3, 512, 1)
    struct.pack_into("<IIII", header, 52, 612, 624, 624, 628)
    return bytes(header) + palette_record + sprite0 + sprite1 + linked + palette + b"AAAA" + b"BBBB"


class SpritePruningTests(unittest.TestCase):
    def test_collects_animation_frames_and_literal_spriteno(self):
        scripts = {"a.cns": "[State 0, image]\ntype = Explod\nspriteno = 12, 3\n"}
        animations = {"a.air": "[Begin Action 0]\n0,1, 0,0, 2\n[Begin Action 1]\n5,6, 0,0, 2\n"}
        references, dynamic = require("collect_sprite_references")(scripts, animations)
        self.assertEqual({(0, 1), (5, 6), (12, 3)}, references)
        self.assertFalse(dynamic)

    def test_dynamic_spriteno_disables_pruning(self):
        references, dynamic = require("collect_sprite_references")(
            {"a.cns": "spriteno = 12 + var(0), 3\n"}, {"a.air": "0,1, 0,0, 2\n"}
        )
        self.assertEqual({(0, 1)}, references)
        self.assertTrue(dynamic)

    def test_v1_rewrite_materializes_palette_and_remaps_link(self):
        original = make_v1([
            (0, 0, make_pcx(1, 1), 0, 0),
            (1, 0, make_pcx(2), 0, 1),
            (2, 0, make_pcx(3, 2), 0, 0),
            (3, 0, b"", 1, 0),
            (9000, 1, make_pcx(4, 3), 0, 0),
        ])
        rewritten, stats = require("prune_sff")(original, {(1, 0), (3, 0)})
        records = read_v1(rewritten)
        self.assertEqual([(1, 0), (3, 0), (9000, 1)], [(r["group"], r["item"]) for r in records])
        self.assertEqual(0, records[0]["same"])
        self.assertEqual(bytes([1]) * 768, records[0]["data"][-768:])
        self.assertEqual(0, records[1]["link"])
        self.assertEqual(2, stats["removed"])
        self.assertLess(len(rewritten), len(original))

    def test_shared_palette_sprites_keep_external_palette_semantics(self):
        original = make_v1([
            (0, 0, make_pcx(1, 1), 0, 0),
            (1, 0, make_pcx(2), 0, 1),
            (2, 0, make_pcx(3), 0, 1),
            (9000, 1, make_pcx(4, 3), 0, 0),
        ])
        try:
            rewritten, stats = require("prune_sff")(original, {(1, 0)}, has_palette=True)
        except TypeError as exc:
            self.fail(f"SFF pruning must accept external palette context: {exc}")
        records = read_v1(rewritten)
        self.assertEqual([(0, 0), (1, 0), (9000, 1)], [(r["group"], r["item"]) for r in records])
        self.assertEqual(1, records[1]["same"])
        self.assertEqual(1, stats["removed"])

    def test_v1_accepts_shared_palette_length_overstated_by_768_bytes(self):
        original = bytearray(make_v1([
            (0, 0, make_pcx(1, 1), 0, 0),
            (1, 0, make_pcx(2), 0, 1),
            (2, 0, make_pcx(3), 0, 1),
            (9000, 1, make_pcx(4, 3), 0, 0),
        ]))
        off = struct.unpack_from("<I", original, 512)[0]
        size = struct.unpack_from("<I", original, off + 4)[0]
        struct.pack_into("<I", original, off + 4, size + 768)
        rewritten, stats = require("prune_sff")(bytes(original), {(1, 0)}, has_palette=True)
        records = read_v1(rewritten)
        self.assertEqual([(0, 0), (1, 0), (9000, 1)], [(r["group"], r["item"]) for r in records])
        self.assertEqual(make_pcx(2), records[1]["data"])
        self.assertEqual(1, stats["removed"])

    def test_v2_rewrite_drops_orphan_data_and_remaps_link(self):
        original = make_v2()
        rewritten, stats = require("prune_sff")(original, {(2, 0)})
        sprite_offset, count = struct.unpack_from("<II", rewritten, 36)
        self.assertEqual(2, count)
        first = struct.unpack_from("<HHHHhhHBBIIHH", rewritten, sprite_offset)
        second = struct.unpack_from("<HHHHhhHBBIIHH", rewritten, sprite_offset + 28)
        self.assertEqual((1, 0), first[:2])
        self.assertEqual((2, 0), second[:2])
        self.assertEqual(0, second[6])
        ldata_offset, _, tdata_offset, _ = struct.unpack_from("<IIII", rewritten, 52)
        self.assertEqual(b"PALPAL!!", rewritten[ldata_offset:tdata_offset])
        self.assertEqual(b"BBBB", rewritten[tdata_offset:])
        self.assertNotIn(b"AAAA", rewritten)
        self.assertEqual(1, stats["removed"])

    def test_dynamic_references_leave_sff_byte_for_byte_unchanged(self):
        original = make_v2()
        rewritten, stats = require("prune_sff")(original, set(), dynamic=True)
        self.assertEqual(original, rewritten)
        self.assertEqual(0, stats["removed"])
        self.assertTrue(stats["dynamic"])


def make_character(root):
    char = root / "char"
    char.mkdir()
    definition = (
        '[Info]\nname = "Test" ; remove this comment\n\n[Files]\n'
        "sprite = test.sff\nanim = test.air\ncmd = test.cmd\ncns = test.cns\n"
        "stcommon = common1.cns\nst = test.cns\n"
    )
    state = (
        "[Statedef -1]\n[State -1, go]\ntype = ChangeState\nvalue = 1\n"
        "[Statedef 1]\n[State 1, image]\ntype = Explod\nspriteno = 2, 0\n"
        "[Statedef 999]\n[State 999, orphan]\ntype = Null\n"
    )
    (char / "test.def").write_text(definition, encoding="latin-1")
    (char / "test.cns").write_text(state, encoding="latin-1")
    (char / "test.cmd").write_text('[Command]\nname = "x"\ncommand = x\n', encoding="latin-1")
    (char / "common1.cns").write_text("[Statedef 0]\n", encoding="latin-1")
    (char / "test.air").write_text("[Begin Action 0]\n2,0, 0,0, 2 ; frame\n", encoding="latin-1")
    sff = make_v2()
    (char / "test.sff").write_bytes(sff)
    return char / "test.def", definition, state, sff


class CharacterCompressionIntegrationTests(unittest.TestCase):
    def test_character_pipeline_minifies_prunes_state_and_rewrites_main_sff(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            definition, _, _, _ = make_character(root)
            stats = require("compress_character")(definition, root / "data")
            self.assertEqual(1, stats["states_removed"])
            self.assertEqual(1, stats["sprites_removed"])
            self.assertNotIn("remove this comment", definition.read_text(encoding="latin-1"))
            self.assertNotIn("Statedef 999", (definition.parent / "test.cns").read_text(encoding="latin-1"))
            self.assertEqual(2, struct.unpack_from("<I", (definition.parent / "test.sff").read_bytes(), 40)[0])

    def test_all_compression_switches_can_be_disabled(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            definition, def_text, state_text, sff = make_character(root)
            stats = require("compress_character")(
                definition, root / "data", minify=False, prune_states=False, prune_sprites=False
            )
            self.assertEqual(def_text, definition.read_text(encoding="latin-1"))
            self.assertEqual(state_text, (definition.parent / "test.cns").read_text(encoding="latin-1"))
            self.assertEqual(sff, (definition.parent / "test.sff").read_bytes())
            self.assertEqual(0, stats["states_removed"])
            self.assertEqual(0, stats["sprites_removed"])


class ScriptFixTests(unittest.TestCase):
    def test_script_fix_adds_missing_projectile_cleanup_state(self):
        build_assets = importlib.import_module("build_assets")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "fighter.cns"
            script.write_text("[Statedef 1102]\n", encoding="latin-1")
            fix = {"file": "fighter.cns", "find": "[Statedef 1102]", "replace": "[Statedef 362]\ntype = S\nphysics = N\n[State 362, cleanup]\ntype = DestroySelf\ntrigger1 = 1\n[Statedef 1102]"}
            build_assets.apply_script_fixes(root, [fix])
            result = script.read_text(encoding="latin-1")
            self.assertEqual(1, result.count("[Statedef 362]"))
            self.assertIn("type = DestroySelf\ntrigger1 = 1\n[Statedef 1102]", result)

    def test_script_fix_rejects_missing_and_ambiguous_match(self):
        build_assets = importlib.import_module("build_assets")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "fighter.cns"
            for content in ("no match", "marker\nmarker\n"):
                script.write_text(content, encoding="latin-1")
                with self.assertRaises(ValueError):
                    build_assets.apply_script_fixes(root, [{"file": "fighter.cns", "find": "marker", "replace": "replacement"}])
                self.assertEqual(content, script.read_text(encoding="latin-1"))

    def test_script_fix_cannot_escape_character_directory(self):
        build_assets = importlib.import_module("build_assets")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "char"
            root.mkdir()
            outside = root.parent / "outside.cns"
            outside.write_text("marker", encoding="latin-1")
            with self.assertRaises(ValueError):
                build_assets.apply_script_fixes(root, [{"file": "../outside.cns", "find": "marker", "replace": "changed"}])
            self.assertEqual("marker", outside.read_text(encoding="latin-1"))


class BuildIntegrationTests(unittest.TestCase):
    def test_character_can_resample_sounds_to_11025_hz(self):
        import math
        import os
        import shrink_snd
        with tempfile.TemporaryDirectory(dir=os.environ.get("HERMES_TEST_TMP")) as temporary:
            root = Path(temporary)
            samples = [int(12000 * math.sin(2 * math.pi * 440 * n / 22050)) for n in range(2205)]
            pcm = struct.pack("<" + "h" * len(samples), *samples)
            wav = shrink_snd._wav(pcm, 22050, 16)
            header = b"ElecbyteSnd\x00" + bytes((0, 1, 0, 1)) + struct.pack("<II", 1, 512)
            source = root / "source.snd"
            target = root / "target.snd"
            source.write_bytes(header.ljust(512, b"\x00") + struct.pack("<IIII", 0, len(wav), 7, 3) + wav)
            _, _, changed, count = shrink_snd.shrink(str(source), str(target), 11025)
            result = target.read_bytes()
            self.assertEqual((1, 1), (changed, count))
            self.assertEqual((7, 3), struct.unpack_from("<II", result, 520))
            self.assertEqual((1, 11025, 16), shrink_snd._wav_info(result[528:]))

    def test_build_pipeline_applies_minification_to_copied_character(self):
        build_assets = importlib.import_module("build_assets")
        compress = getattr(build_assets, "compress_copied_character", None)
        self.assertTrue(callable(compress), "build_assets must expose the character compression pipeline")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            definition, _, _, _ = make_character(root)
            changes = build_assets.compress_copied_character(
                str(definition), str(root / "data"), minify=True, prune_states=False, prune_sprites=False
            )
            self.assertNotIn("remove this comment", definition.read_text(encoding="latin-1"))
            self.assertTrue(any("minif" in change.lower() for change in changes))


if __name__ == "__main__":
    unittest.main()
