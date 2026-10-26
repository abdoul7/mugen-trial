"""motif_cost.py -- estimate Vita texture memory for the TBM motif, per screen.

Collects every sprite a .def references (spriteno / *.spr / actionno / *.anim -> [Begin Action]
frames), looks each up in the SFF the screen would use, and sums decoded RGBA bytes
(prism makes 32-bit textures from paletted PNGs on Vita), full size and downscaled.

    python tools/motif_cost.py build/game/assets/data   # after build_assets.py --motif tbm
"""
import re
import struct
import sys

def sff_index(path):
    d = open(path, "rb").read()
    spr_off, nspr = struct.unpack_from("<II", d, 36)
    idx = {}
    for i in range(nspr):
        grp, num, w, h, x, y, link, fmt, depth, ldata, llen, pal, flags = struct.unpack_from("<HHHHhhHBBIIHH", d, spr_off + i * 28)
        idx[(grp, num)] = (w, h, llen == 0)
    return idx

def sections(text):
    out, name = {}, None
    for line in text.splitlines():
        s = line.split(";")[0].strip()
        m = re.match(r"\[([^\]]+)\]", s)
        if m:
            name = m.group(1).strip().lower()
            out.setdefault(name, []).append([])
        elif name and s:
            out[name][-1].append(s)
    return out

def refs(text, want_sections):
    secs = sections(text)
    actions = {}
    for name, blocks in secs.items():
        m = re.match(r"begin action\s+(-?\d+)", name)
        if m:
            frames = set()
            for ln in blocks[0]:
                f = re.match(r"(-?\d+)\s*,\s*(-?\d+)\s*,", ln)
                if f:
                    frames.add((int(f.group(1)), int(f.group(2))))
            actions[int(m.group(1))] = frames
    sprites = set()
    for name, blocks in secs.items():
        if not any(name.startswith(w) for w in want_sections):
            continue
        for block in blocks:
            for ln in block:
                kv = re.match(r"([\w.]+)\s*=\s*(.*)", ln)
                if not kv:
                    continue
                k, v = kv.group(1).lower(), kv.group(2)
                nums = [x.strip() for x in v.split(",")]
                if (k == "spriteno" or k.endswith(".spr")) and len(nums) >= 2 and all(re.match(r"-?\d+$", x) for x in nums[:2]):
                    sprites.add((int(nums[0]), int(nums[1])))
                elif (k == "actionno" or k.endswith(".anim")) and re.match(r"-?\d+$", nums[0]):
                    sprites |= actions.get(int(nums[0]), set())
    return sprites

def cost(sprites, idx, scale):
    total = missing = 0
    for key in sprites:
        if key not in idx:
            missing += 1
            continue
        w, h, linked = idx[key]
        if not linked:
            total += max(1, round(w * scale)) * max(1, round(h * scale)) * 4
    return total, missing

if __name__ == "__main__":
    data = sys.argv[1]  # build/game/assets/data
    sysdef = open(f"{data}/tbm/system.def", encoding="latin-1").read()
    fightdef = open(f"{data}/480p/fight.def", encoding="latin-1").read()
    # TBM display scale: 1280x720 art shown on a 544-high screen = 0.755; HUD art is drawn at .5
    jobs = [
        ("title", sysdef, ["titlebg", "title info"], f"{data}/tbm/00/title.sff", 544 / 720),
        ("select", sysdef, ["selectbg", "select info"], f"{data}/tbm/00/select.sff", 544 / 720),
        ("versus", sysdef, ["versusbg", "vs screen"], f"{data}/tbm/00/Versus.sff", 544 / 720),
        ("victory", sysdef, ["victorybg", "victory screen"], f"{data}/tbm/00/Victory.sff", 544 / 720),
        ("fight HUD", fightdef, ["lifebar", "powerbar", "face", "name", "time", "combo", "round", "winicon", "timer", "score", "guardbar", "stunbar", "action"], f"{data}/480p/fight.sff", 0.5 * 544 / 480),
    ]
    print(f"{'screen':10} {'refs':>5} {'miss':>5} {'full MB':>8} {'scaled MB':>9}  (scale)")
    for label, text, secs, sff, sc in jobs:
        idx = sff_index(sff)
        s = refs(text, secs)
        full, miss = cost(s, idx, 1.0)
        small, _ = cost(s, idx, sc)
        allfile = sum(w * h * 4 for w, h, l in idx.values() if not l)
        print(f"{label:10} {len(s):5d} {miss:5d} {full / 2**20:8.1f} {small / 2**20:9.1f}  ({sc:.2f})   whole file {allfile / 2**20:.0f} MB")
