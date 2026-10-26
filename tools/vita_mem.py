"""
vita_mem.py -- predict what each character / fight costs in Vita memory, following the
Dolmexica Infinite 1.8 loading code (source/dolmexica-src, release commit a6d63e9/0bf177e).

    python tools/vita_mem.py                 # every character in build/game select.def
    python tools/vita_mem.py --csv out.csv   # also write a CSV

Texture rules (prism/mugenspritefilereader.cpp, prism/vita/texture_vita.cpp):
  * players load sprites with the "real palette" on (playerdefinition.cpp:500), P1 with
    pal1 and P2 with pal2 (gamelogic.cpp:788-789); a missing palN file = no palette file
  * SFF v2: palette = sprite palette index + 1 if a palette file is used, else the index
    (mugenspritefilereader.cpp:1199). Paletted (raw/RLE8/LZ5) or PNG8 sprites with
    palette 0 become 8-bit P8 textures (texture_vita.cpp:395); everything else is
    converted to 32-bit ARGB. RLE5 (format 3) is "Unrecognized image format" (:1227).
  * SFF v1: a sprite stays 8-bit only while the file has exactly one palette loaded
    (:838); every sprite that carries its own palette adds one, so after the first
    extra palette all later sprites are 32-bit. With a palette file, sprite 0,0 resets
    the list (:942).
  * one texture per sprite on Vita (no split below 4096 px, :467-469); size =
    align8(width) * height * bytes, rounded to 64 B (texture_vita.cpp:267-268, slab alignment 187);
    above 4096 px the texture can't be created and the game aborts (texture_vita.cpp:265, 211).
  * textures come from 8 MB slabs, CDRAM first, then main memory (texture_vita.cpp:250,
    memoryhandler_vita.cpp:43-51) -- NOT from the 96 MB newlib heap.
Heap (allocMemory = newlib malloc, main.cpp:40 sets 96 MB):
  * every sound is kept as a WAV copy (mugensoundfilereader.cpp:54-56); 8-bit WAVs are
    widened to 16-bit (soundeffect_vita.cpp:98, 158), so they cost double.
  * parsed .cns/.st/.cmd/.air are also on the heap; their text size is listed (the
    parsed size isn't modelled).
"""

import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "build", "game", "assets")
MB = 2 ** 20


def read(p):
    with open(p, encoding="latin-1") as f:
        return f.read()


def find_ci(folder, rel):
    cur = folder
    for part in rel.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if not os.path.isdir(cur):
            return None
        hit = next((e for e in os.listdir(cur) if e.lower() == part.lower()), None)
        if hit is None:
            return None
        cur = os.path.join(cur, hit)
    return cur


def tex_bytes(w, h, bpp):
    return (((w + 7) & ~7) * h * bpp + 63) & ~63


class Cost:
    def __init__(self):
        self.p8 = self.argb = self.n8 = self.n32 = 0
        self.too_big = []      # sprites > 4096 px: engine aborts
        self.bad_format = []   # RLE5 etc.: engine error
        self.engine_p8 = 0     # what-if: engine keeps every 8-bit sprite as P8 + its own palette
        self.reorder = None    # what-if (SFF v1): main-palette sprites written first

    @property
    def total(self):
        return self.p8 + self.argb

    def add(self, w, h, eight, key, paletted=True):
        if w > 4096 or h > 4096:
            self.too_big.append(key)
            return
        self.engine_p8 += tex_bytes(w, h, 1 if paletted else 4) + (1024 if paletted and not eight else 0)
        if eight:
            self.p8 += tex_bytes(w, h, 1)
            self.n8 += 1
        else:
            self.argb += tex_bytes(w, h, 4)
            self.n32 += 1


def sff_cost(path, has_pal_file, portraits_only=False):
    d = open(path, "rb").read()
    c = Cost()
    v = d[12:16]  # engine: mVersion[1]==1 && mVersion[3]==1 -> v1; mVersion[3]==2 -> v2
    if v[3] == 1:
        nimg, first = struct.unpack_from("<I", d, 20)[0], struct.unpack_from("<I", d, 24)[0]
        pals = 1 if has_pal_file else 0
        off, n = first, 0
        eff, prev, sizes = [], None, []   # (palette bytes, w, h) per real sprite
        while off and off + 32 <= len(d) and n < 100000:
            nxt, ln, ax, ay, grp, img, link, same = struct.unpack_from("<IIhhHHHB", d, off)
            n += 1
            if has_pal_file and grp == 0 and img == 0:
                pals = 1
            if ln and not (portraits_only and not (grp == 9000 and img <= 1)):
                pcx = off + 32
                xmin, ymin, xmax, ymax = struct.unpack_from("<HHHH", d, pcx + 4)
                own = not same and not (has_pal_file and grp == 0 and img == 0)
                if own:
                    pals += 1
                w, h = xmax - xmin + 1, ymax - ymin + 1
                c.add(w, h, pals == 1, (grp, img))
                if has_pal_file and grp == 0 and img == 0:
                    cur = "ACT"
                elif same and prev is not None:
                    cur = prev
                else:
                    cur = d[pcx + ln - 768 + 3: pcx + ln]  # colour 0 is transparent: ignore it
                prev = cur
                eff.append((cur, w, h))
            if not nxt or nxt <= off:
                break
            off = nxt
        if eff:  # main palette = the one covering the most pixels (the act file if one is used)
            area = {}
            for pal, w, h in eff:
                area[pal] = area.get(pal, 0) + w * h
            others = {k: v for k, v in area.items() if k != "ACT"}
            main_set = {"ACT"} if "ACT" in area else set()
            if others:  # with an act file, sprite 0,0 defines the colours; the biggest own palette is the same art
                main_set.add(max(others, key=others.get))
            c.reorder = sum(tex_bytes(w, h, 1 if pal in main_set else 4) for pal, w, h in eff if w <= 4096 and h <= 4096)
        return c, "v1"
    spr_off, nspr = struct.unpack_from("<II", d, 36)
    for i in range(nspr):
        grp, num, w, h, ax, ay, link, fmt, depth, doff, dlen, pidx, flags = struct.unpack_from("<HHHHhhHBBIIHH", d, spr_off + i * 28)
        if portraits_only and not (grp == 9000 and num <= 1):
            continue
        if dlen == 0:
            continue  # linked: shares the target's texture
        palette = pidx + 1 if has_pal_file else pidx
        if fmt in (0, 2, 4):
            c.add(w, h, palette == 0, (grp, num))
        elif fmt in (10, 11, 12):
            c.add(w, h, depth == 8 and palette == 0, (grp, num), paletted=(fmt == 10))
        else:
            c.bad_format.append((grp, num, fmt))
    return c, "v2"


def snd_heap(path):
    d = open(path, "rb").read()
    n, off = struct.unpack_from("<II", d, 16)
    total = count = 0
    for _ in range(n):
        if off + 16 > len(d):
            break
        nxt, ln, grp, smp = struct.unpack_from("<IIII", d, off)
        wav = d[off + 16:off + 16 + 44]
        bits = struct.unpack_from("<H", wav, 34)[0] if len(wav) >= 36 and wav[8:12] == b"WAVE" else 16
        total += ln * (2 if bits == 8 else 0.5 if bits == 32 else 1)
        count += 1
        if not nxt:
            break
        off = nxt
    return int(total), count


def char_files(def_path):
    folder = os.path.dirname(def_path)
    t = read(def_path)
    files = re.search(r"(?is)\[files\](.*?)(\n\s*\[|$)", t).group(1)
    kv = {m.group(1).lower(): m.group(2).strip().strip('"')
          for m in re.finditer(r"(?im)^\s*([a-z0-9.]+)\s*=\s*([^\r\n;]*)", files)}
    get = lambda k: find_ci(folder, kv[k]) if kv.get(k) else None
    scripts = [get(k) for k in kv if re.match(r"(cmd|cns|st\d*|anim)$", k)]
    return {"sprite": get("sprite"), "sound": get("sound"), "pal1": get("pal1"), "pal2": get("pal2"),
            "script_bytes": sum(os.path.getsize(s) for s in scripts if s)}


def roster():
    out, sec = [], ""
    for line in read(os.path.join(ASSETS, "data", "select.def")).splitlines():
        s = line.split(";")[0].strip()
        if s.startswith("["):
            sec = s.lower()
        elif s and sec == "[characters]" and s != "randomselect":
            ch, st = [x.strip() for x in s.split(",")[:2]]
            out.append((ch, st))
    return out


def resolve_char(entry):
    p = os.path.join(ASSETS, "chars", *entry.split("/"))
    return p if p.lower().endswith(".def") else os.path.join(p, os.path.basename(p) + ".def")


def stage_cost(stage_rel):
    sdef = os.path.join(ASSETS, *stage_rel.split("/"))
    m = re.search(r"(?im)^\s*spr\s*=\s*([^;\r\n]+)", read(sdef))
    sff = find_ci(os.path.dirname(sdef), m.group(1).strip()) if m else None
    return sff_cost(sff, False)[0] if sff else Cost()


def main():
    rows = []
    stages = {}
    for entry, stage in roster():
        cid = entry.split("/")[0]
        f = char_files(resolve_char(entry))
        p1, ver = sff_cost(f["sprite"], bool(f["pal1"]))
        p2, _ = sff_cost(f["sprite"], bool(f["pal2"]))
        nopal, _ = sff_cost(f["sprite"], False)
        heap, nsnd = snd_heap(f["sound"]) if f["sound"] else (0, 0)
        if stage not in stages:
            stages[stage] = stage_cost(stage)
        rows.append({"id": cid, "sff": ver, "sff_mb": os.path.getsize(f["sprite"]) / MB,
                     "p1": p1, "p2": p2, "nopal": nopal, "snd_heap": heap, "nsnd": nsnd,
                     "script_kb": f["script_bytes"] / 1024, "stage": stage, "stage_tex": stages[stage].total})

    rows.sort(key=lambda r: -r["p1"].total)
    hdr = (f"{'id':22} {'sff':>3} {'file':>6} {'P1 tex':>7} {'(8bit/32bit)':>14} {'no-pal':>7} "
           f"{'v1 reord':>8} {'eng P8':>7} {'snd heap':>8} {'scripts':>8} {'mirror':>7}  flags")
    print("MB; tex = Vita texture memory, heap = newlib heap (96 MB). mirror = P1+P2 same char + own stage\n")
    print(hdr)
    for r in rows:
        p1 = r["p1"]
        mirror = (r["p1"].total + r["p2"].total + r["stage_tex"]) / MB
        flags = []
        if p1.too_big:
            flags.append(f"ABORT: {len(p1.too_big)} sprite(s) > 4096 px")
        if p1.bad_format:
            flags.append(f"ERROR: {len(p1.bad_format)} RLE5/unknown sprites")
        print(f"{r['id']:22} {r['sff']:>3} {r['sff_mb']:6.1f} {p1.total / MB:7.1f} "
              f"{p1.p8 / MB:6.1f}/{p1.argb / MB:6.1f} {r['nopal'].total / MB:7.1f} "
              f"{(p1.reorder / MB if p1.reorder is not None else float('nan')):8.1f} {p1.engine_p8 / MB:7.1f} "
              f"{r['snd_heap'] / MB:8.1f} {r['script_kb'] / 1024:8.1f} {mirror:7.1f}  {'; '.join(flags)}")
    if "--csv" in sys.argv:
        import csv
        out = sys.argv[sys.argv.index("--csv") + 1]
        with open(out, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "sff_version", "sff_file_mb", "p1_tex_mb", "p1_tex_8bit_mb", "p1_tex_32bit_mb",
                        "p2_tex_mb", "tex_without_palette_file_mb", "tex_v1_reordered_mb", "tex_engine_p8_mb",
                        "snd_heap_mb", "sounds", "script_mb",
                        "stage", "stage_tex_mb", "mirror_match_tex_mb", "sprites_over_4096", "unsupported_sprites"])
            for r in rows:
                w.writerow([r["id"], r["sff"], f"{r['sff_mb']:.1f}", f"{r['p1'].total / MB:.1f}", f"{r['p1'].p8 / MB:.1f}",
                            f"{r['p1'].argb / MB:.1f}", f"{r['p2'].total / MB:.1f}", f"{r['nopal'].total / MB:.1f}",
                            "" if r["p1"].reorder is None else f"{r['p1'].reorder / MB:.1f}", f"{r['p1'].engine_p8 / MB:.1f}",
                            f"{r['snd_heap'] / MB:.1f}", r["nsnd"], f"{r['script_kb'] / 1024:.1f}", r["stage"],
                            f"{r['stage_tex'] / MB:.1f}", f"{(r['p1'].total + r['p2'].total + r['stage_tex']) / MB:.1f}",
                            len(r["p1"].too_big), len(r["p1"].bad_format)])
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
