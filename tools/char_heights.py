"""char_heights.py -- how tall each fighter stands on screen, and the scale that would match the median.

    python tools/char_heights.py [assets_dir]      (default build/game/assets)

Height = the standing sprite's axis y (pixels from the top of the sprite to the feet; MUGEN puts the
axis at the feet) x the character's [Size] yscale x (240 / its localcoord height), i.e. in the 320x240
stage space every fighter is drawn in. The standing sprite is the first frame of animation 0 in the
.air. Writes reports/char-heights.csv and prints a table with the scale factor to the median.
"""
import csv
import os
import re
import statistics
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(p):
    return open(p, encoding="latin-1").read()


def find_ci(folder, rel):
    p = os.path.join(folder, rel.replace("\\", "/"))
    if os.path.exists(p):
        return p
    d, name = os.path.split(p)
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.lower() == name.lower():
                return os.path.join(d, f)
    return None


def files_key(text, key):
    m = re.search(r"(?is)\[files\](.*?)(?:\n\s*\[|$)", text)
    if not m:
        return None
    k = re.search(rf"(?im)^\s*{key}\s*=\s*([^;\r\n]+)", m.group(1))
    return k.group(1).strip().strip('"') if k else None


def size_value(texts, key, default):
    for t in texts:
        m = re.search(r"(?is)\[size\](.*?)(?:\n\s*\[|$)", t)
        if m:
            v = re.search(rf"(?im)^\s*{key}\s*=\s*([-0-9.]+)", m.group(1))
            if v:
                return float(v.group(1))
    return default


def stand_sprite(air_text):
    m = re.search(r"(?is)\[\s*begin\s+action\s+0\s*\](.*?)(?:\n\s*\[|$)", air_text)
    if not m:
        return (0, 0)
    for line in m.group(1).splitlines():
        line = line.split(";")[0].strip()
        f = re.match(r"(-?\d+)\s*,\s*(-?\d+)\s*,", line)
        if f:
            return int(f.group(1)), int(f.group(2))
    return (0, 0)


def sprite_axis(sff, group, item):
    d = open(sff, "rb").read()
    if d[15] == 2:
        so, sn = struct.unpack_from("<II", d, 36)
        for i in range(sn):
            g, it, w, h, ax, ay = struct.unpack_from("<HHHHhh", d, so + i * 28)
            if (g, it) == (group, item):
                return w, h, ax, ay
        return None
    off = struct.unpack_from("<I", d, 24)[0]
    seen = set()
    while off and off not in seen and off + 32 <= len(d):
        seen.add(off)
        nxt, ln, ax, ay, g, it = struct.unpack_from("<IIhhHH", d, off)
        if (g, it) == (group, item):
            w = h = None
            if ln >= 12:
                x0, y0, x1, y1 = struct.unpack_from("<HHHH", d, off + 32 + 4)
                w, h = x1 - x0 + 1, y1 - y0 + 1
            return w, h, ax, ay
        off = nxt
    return None


def measure(assets):
    sel = read(os.path.join(assets, "data", "select.def"))
    part = sel.split("[Characters]")[1].split("\n[")[0]
    rows = []
    for line in part.splitlines():
        entry = line.split(";")[0].split(",")[0].strip()
        if not entry or entry.lower() == "randomselect":
            continue
        cid = entry.split("/")[0]
        def_path = os.path.join(assets, "chars", entry if entry.lower().endswith(".def") else f"{entry}/{entry}.def")
        if not os.path.exists(def_path):
            continue
        folder = os.path.dirname(def_path)
        t = read(def_path)
        lc = re.search(r"(?im)^\s*localcoord\s*=\s*(\d+)\s*,\s*(\d+)", t)
        lc_h = int(lc.group(2)) if lc else 240
        cns = [find_ci(folder, files_key(t, k)) for k in ("cns", "st") if files_key(t, k)]
        cns_texts = [read(p) for p in cns if p]
        yscale = size_value(cns_texts, "yscale", 1.0)
        air = find_ci(folder, files_key(t, "anim") or "")
        spr = find_ci(folder, files_key(t, "sprite") or "")
        g, i = stand_sprite(read(air)) if air else (0, 0)
        ax = sprite_axis(spr, g, i) if spr else None
        if not ax:
            rows.append({"id": cid, "note": f"stand sprite {g},{i} not found"})
            continue
        w, h, axx, axy = ax
        height = axy * yscale * 240 / lc_h
        rows.append({"id": cid, "stand": f"{g},{i}", "axis_y": axy, "yscale": yscale, "localcoord_h": lc_h,
                     "height": round(height, 1), "def": def_path})
    return rows


def main():
    assets = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "game", "assets")
    rows = measure(assets)
    hs = [r["height"] for r in rows if "height" in r]
    med = statistics.median(hs)
    for r in rows:
        if "height" in r:
            r["scale_to_median"] = round(med / r["height"], 3)
    print(f"median standing height: {med:.1f} px (of 240)")
    print(f"{'id':22} {'stand':>9} {'axis_y':>6} {'yscale':>6} {'lc_h':>5} {'height':>7} {'x median':>8}")
    for r in sorted(rows, key=lambda r: r.get("height", 0)):
        if "height" not in r:
            print(f"{r['id']:22} {r['note']}")
            continue
        print(f"{r['id']:22} {r['stand']:>9} {r['axis_y']:6d} {r['yscale']:6.2f} {r['localcoord_h']:5d} "
              f"{r['height']:7.1f} {r['scale_to_median']:8.2f}")
    out = os.path.join(ROOT, "reports", "char-heights.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "stand", "axis_y", "yscale", "localcoord_h", "height", "scale_to_median", "note"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("wrote", out)


if __name__ == "__main__":
    main()
