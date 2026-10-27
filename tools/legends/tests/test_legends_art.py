"""Round-trip Legends SFF/AIR assets, including the optional local kit."""
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools/legends"), str(ROOT / "tools/ui")]
import legends_art
import legends_kit
import sff1
import json


def check(folder, ids, kit):
    path = str(folder / "legends.sff")
    count, _, used, pixels = legends_art.write(path, ids)
    sprites = sff1.read(path)
    keys = {(s.group, s.item) for s in sprites}
    assert len(keys) == count == len(sprites), "duplicate or unreadable sprites"
    for line in Path(path).with_suffix(".air").read_text().splitlines():
        if re.match(r"^\d+,", line):
            g, i = map(int, line.split(",")[:2])
            assert (g, i) in keys, f"AIR references absent sprite {g},{i}"
    if kit:
        assert used and pixels > 0
        assert all((g, i) in keys for g in (100, 101) for i in range(len(ids)))
        assert (144, 3) in keys, "teal aura missing"
    else:
        assert not used and pixels == 0
    return count


def main():
    ids = [c["id"] for c in json.loads((ROOT / "tools/legends/catalog.json").read_text())["cards"]]
    (ROOT / "build").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / "build", prefix="legends-art-test-") as tmp:
        folder = Path(tmp)
        if legends_kit.kit_dir():
            print(f"kit: {check(folder, ids, True)} sprites, all faces/thumbs/AIR references readable")
        with patch.object(legends_kit, "kit_dir", return_value=None):
            print(f"fallback: {check(folder, ids, False)} sprites, all AIR references readable")


if __name__ == "__main__":
    main()
