"""fix_portraits.py -- give a character proper select-screen portraits (SFF v2 only).

Some downloads put the wrong picture in the slots our motif reads (baby_vegeta: a 34x57 body
sprite as the 9000,0 grid icon, no 9000,1 big portrait) while a good face exists elsewhere
(9000,10, 150x150 PNG). Set in roster.json:

    "portraits": {"from": [9000, 10]}

and build_assets.py calls fix(sff_path, (9000, 10)) on the COPY in build/game. It renders the source
sprite to a 27x27 icon (9000,0) and a 120x140 big portrait (9000,1, the stock motif's size), stores
both as PNG32 at the end of the file (the tdata block), and points the 9000,0 / 9000,1 entries at
them. If 9000,1 doesn't exist, an entry nothing references (another 9000,x besides the source) is
reused for it. Returns a one-line summary.
"""
import io
import struct

from PIL import Image

NODE = struct.Struct("<HHHHhhHBBIIHH")  # group item w h axisx axisy link fmt depth ofs len pal flags
ICON = (27, 27)
BIG = (120, 140)


def _png_bytes(img):
    b = io.BytesIO()
    img.save(b, "PNG")
    return b.getvalue()


def _fit(img, size, bottom=False):
    im = img.copy()
    im.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    x = (size[0] - im.size[0]) // 2
    y = size[1] - im.size[1] if bottom else (size[1] - im.size[1]) // 2
    canvas.paste(im, (x, y), im)
    return canvas


def fix(sff_path, source, used_elsewhere=()):
    d = bytearray(open(sff_path, "rb").read())
    if bytes(d[:12]) != b"ElecbyteSpr\x00" or d[15] != 2:
        raise ValueError(f"{sff_path}: not SFF v2")
    so, sn = struct.unpack_from("<II", d, 0x24)
    lo, ll, to, tl = struct.unpack_from("<IIII", d, 0x34)
    if to + tl != len(d):
        raise ValueError(f"{sff_path}: tdata isn't the last block; can't append safely")
    nodes = {}
    for i in range(sn):
        n = list(NODE.unpack_from(d, so + i * NODE.size))
        nodes.setdefault((n[0], n[1]), i)
    src_i = nodes.get(tuple(source))
    if src_i is None:
        raise ValueError(f"{sff_path}: source sprite {source} not found")
    s = NODE.unpack_from(d, so + src_i * NODE.size)
    if s[7] not in (10, 11, 12):
        raise ValueError(f"{sff_path}: source {source} is format {s[7]}, only PNG sources are supported")
    base = to if s[12] & 1 else lo
    face = Image.open(io.BytesIO(bytes(d[base + s[9] + 4: base + s[9] + s[10]]))).convert("RGBA")

    def put(slot, img, fallback_candidates):
        idx = nodes.get(slot)
        if idx is None:
            free = [nodes[k] for k in fallback_candidates if k in nodes]
            if not free:
                raise ValueError(f"{sff_path}: no free entry to reuse for {slot}")
            idx = free[0]
            nodes.pop(next(k for k, v in nodes.items() if v == idx))
            nodes[slot] = idx
        png = _png_bytes(img)
        ofs = len(d) - to
        d.extend(struct.pack("<I", img.size[0] * img.size[1] * 4) + png)
        NODE.pack_into(d, so + idx * NODE.size, slot[0], slot[1], img.size[0], img.size[1], 0, 0, 0,
                       12, 32, ofs, 4 + len(png), 0, 1)
        return idx

    spare = [k for k in sorted(nodes) if k[0] == 9000 and k[1] > 1 and k != tuple(source)
             and k not in set(map(tuple, used_elsewhere))]
    put((9000, 0), _fit(face, ICON), [])
    put((9000, 1), _fit(face, BIG, bottom=True), spare)
    struct.pack_into("<I", d, 0x40, len(d) - to)  # tdata length
    open(sff_path, "wb").write(d)
    return f"portraits 9000,0 {ICON[0]}x{ICON[1]} + 9000,1 {BIG[0]}x{BIG[1]} from {source[0]},{source[1]}"
