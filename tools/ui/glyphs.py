"""glyphs.py -- the Jump Force Vita display font: angular stroke letters drawn from line
segments (our own design, nothing traced), plus a writer for MUGEN v1 .fnt files.

Letters sit on a grid 6 units tall; most are 4 wide. Corners are chamfered top-left and
bottom-right, which gives the slanted, "speed" look of modern fighting-game type.

    img = text("ROUND 1", cap=14, fill=(255,255,255), outline=(0,0,0))
    write_fnt("jfv_s.fnt", cap=7)
"""
import io
import struct

from PIL import Image, ImageDraw, ImageFilter

C = 1.2  # chamfer
G = {
    "A": [[(0, 6), (0, C), (C, 0), (4, 0), (4, 6)], [(0, 3.4), (4, 3.4)]],
    "B": [[(0, 0), (3.2, 0), (4, 0.8), (4, 2.3), (3.3, 3), (0, 3)], [(3.3, 3), (4, 3.7), (4, 6 - C), (4 - C, 6), (0, 6), (0, 0)]],
    "C": [[(4, 0), (C, 0), (0, C), (0, 6), (4 - C, 6), (4, 6 - C)]],
    "D": [[(0, 0), (4 - C, 0), (4, C), (4, 6 - C), (4 - C, 6), (0, 6), (0, 0)]],
    "E": [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3.2, 3)]],
    "F": [[(4, 0), (0, 0), (0, 6)], [(0, 3), (3.2, 3)]],
    "G": [[(4, 0), (C, 0), (0, C), (0, 6), (4 - C, 6), (4, 6 - C), (4, 3), (2.2, 3)]],
    "H": [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    "I": [[(0, 0), (0, 6)]],
    "J": [[(4, 0), (4, 6 - C), (4 - C, 6), (0, 6), (0, 4.4)]],
    "K": [[(0, 0), (0, 6)], [(0, 3.2), (1.6, 3.2), (4, 0)], [(1.6, 3.2), (4, 6)]],
    "L": [[(0, 0), (0, 6), (4, 6)]],
    "M": [[(0, 6), (0, 0), (2.5, 3), (5, 0), (5, 6)]],
    "N": [[(0, 6), (0, 0), (4, 6), (4, 0)]],
    "O": [[(C, 0), (4, 0), (4, 6 - C), (4 - C, 6), (0, 6), (0, C), (C, 0)]],
    "P": [[(0, 6), (0, 0), (4 - C, 0), (4, C), (4, 3), (0, 3)]],
    "Q": [[(C, 0), (4, 0), (4, 6 - C), (4 - C, 6), (0, 6), (0, C), (C, 0)], [(2.6, 4.6), (4.2, 6.4)]],
    "R": [[(0, 6), (0, 0), (4 - C, 0), (4, C), (4, 3), (0, 3)], [(2, 3), (4, 6)]],
    "S": [[(4, 0), (C, 0), (0, C), (0, 3), (4, 3), (4, 6 - C), (4 - C, 6), (0, 6)]],
    "T": [[(0, 0), (4, 0)], [(2, 0), (2, 6)]],
    "U": [[(0, 0), (0, 6), (4 - C, 6), (4, 6 - C), (4, 0)]],
    "V": [[(0, 0), (2, 6), (4, 0)]],
    "W": [[(0, 0), (1.2, 6), (2.5, 2.4), (3.8, 6), (5, 0)]],
    "X": [[(0, 0), (4, 6)], [(4, 0), (0, 6)]],
    "Y": [[(0, 0), (2, 3), (4, 0)], [(2, 3), (2, 6)]],
    "Z": [[(0, 0), (4, 0), (0, 6), (4, 6)]],
    "0": [[(C, 0), (4, 0), (4, 6 - C), (4 - C, 6), (0, 6), (0, C), (C, 0)]],
    "1": [[(0, 1.2), (1.4, 0), (1.4, 6)]],
    "2": [[(0, C), (C, 0), (4, 0), (4, 3), (0, 6), (4, 6)]],
    "3": [[(0, 0), (4, 0), (4, 6 - C), (4 - C, 6), (0, 6)], [(1.4, 3), (4, 3)]],
    "4": [[(3, 6), (3, 0), (0, 4), (4, 4)]],
    "5": [[(4, 0), (0, 0), (0, 3), (4, 3), (4, 6 - C), (4 - C, 6), (0, 6)]],
    "6": [[(4, 0), (C, 0), (0, C), (0, 6), (4, 6), (4, 3), (0, 3)]],
    "7": [[(0, 0), (4, 0), (4, 1.2), (1.6, 6)]],
    "8": [[(C, 0), (4, 0), (4, 6 - C), (4 - C, 6), (0, 6), (0, C), (C, 0)], [(0, 3), (4, 3)]],
    "9": [[(4, 3), (0, 3), (0, C), (C, 0), (4, 0), (4, 6), (0, 6)]],
    ".": [[(0, 5.7), (0, 6)]],
    ",": [[(0.4, 5.5), (0, 6.6)]],
    ":": [[(0, 1.7), (0, 2.0)], [(0, 5.7), (0, 6)]],
    "!": [[(0, 0), (0, 4)], [(0, 5.7), (0, 6)]],
    "?": [[(0, C), (C, 0), (4, 0), (4, 2.6), (2, 3.6), (2, 4.2)], [(2, 5.7), (2, 6)]],
    "-": [[(0, 3), (2.4, 3)]],
    "+": [[(0, 3), (3, 3)], [(1.5, 1.5), (1.5, 4.5)]],
    "/": [[(0, 6), (3, 0)]],
    "'": [[(0, 0), (0, 1.6)]],
    "(": [[(1.6, 0), (0, 1.6), (0, 4.4), (1.6, 6)]],
    ")": [[(0, 0), (1.6, 1.6), (1.6, 4.4), (0, 6)]],
    "&": [[(4, 6), (0.6, 2.6), (0.6, 0.8), (1.4, 0), (2.6, 0), (2.6, 1.6), (0, 3.8), (0, 6), (2.6, 6), (4, 4)]],
    "%": [[(0, 6), (4, 0)], [(0, 0), (0.9, 0)], [(3.1, 6), (4, 6)]],
    "o": [[(0, 3), (1, 1.6), (2, 1.6), (3, 3), (4, 4.4), (5, 4.4), (6, 3), (5, 1.6), (4, 1.6), (3, 3), (2, 4.4), (1, 4.4), (0, 3)]],  # infinity (timer)
    "#": [[(1.2, 0), (0.8, 6)], [(3.2, 0), (2.8, 6)], [(0, 2), (4, 2)], [(0, 4), (4, 4)]],
}
SPACE = 2.4
GAP = 1.4  # between letters, in units
STROKE = 1.15  # stroke width, in units
ITALIC = 0.22  # x shear per unit of height


def _width(ch):
    pts = [p for line in G[ch] for p in line]
    return max(x for x, _ in pts) - min(x for x, _ in pts)


def text(s, cap, fill=(255, 255, 255), outline=(0, 0, 0), ow=1, italic=ITALIC, stroke=STROKE, ss=6, gradient=None):
    """Render s to an RGBA image `cap` px tall (plus outline). gradient=(top, bottom) colours."""
    u = cap / 6.0 * ss  # supersampled px per unit
    sw = stroke * u
    pad = sw + ow * ss + 2
    chars = [c if c == "o" else c for c in (s if s == "o" else s.upper())]
    total = sum((_width(c) if c in G else SPACE) + GAP for c in chars) - GAP
    W = int(total * u + 2 * pad + 6 * u * italic) + 1
    H = int(6 * u + 2 * pad) + 1
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    x = pad
    for c in chars:
        if c not in G:
            x += (SPACE + GAP) * u
            continue
        minx = min(px for line in G[c] for px, _ in line)
        for line in G[c]:
            pts = [(x + (px - minx) * u + (6 - py) * u * italic, pad + py * u) for px, py in line]
            if len(pts) == 2 and pts[0] == pts[1]:
                pts[1] = (pts[1][0] + 0.01, pts[1][1])
            d.line(pts, fill=255, width=max(1, int(sw)))
            for px, py in pts:  # square joints
                h = sw / 2
                d.rectangle([px - h, py - h, px + h, py + h], fill=255)
        x += (_width(c) + GAP) * u
    body = mask.resize((W // ss, H // ss), Image.Resampling.LANCZOS)
    w, h = body.size
    if gradient:
        top, bot = gradient
        col = Image.new("RGB", (w, h))
        cd = ImageDraw.Draw(col)
        for yy in range(h):
            t = yy / max(1, h - 1)
            cd.line([(0, yy), (w, yy)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bot)))
    else:
        col = Image.new("RGB", (w, h), fill)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if outline is not None and ow:
        o = body.point(lambda a: 255 if a > 40 else 0)
        for _ in range(ow):
            o = o.filter(ImageFilter.MaxFilter(3))
        out.paste(Image.new("RGBA", (w, h), outline + (255,)), mask=o)
        # inside the outline, blend the fill over the outline colour (anti-aliased edge, no alpha)
        base = Image.new("RGB", (w, h), outline)
        base.paste(col, mask=body)
        out.paste(base, mask=body.point(lambda a: 255 if a > 20 else 0))
    else:
        out.paste(col.convert("RGBA"), mask=body.point(lambda a: 255 if a >= 110 else 0))
    return out.crop(out.getbbox()) if out.getbbox() else out


# characters each font provides; lowercase reuses the capitals
CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:!?-+/'()&%#"


def write_fnt(path, cap, fill=(255, 255, 255), outline=(0, 0, 0), ow=1, digits_only=False, gradient=None, gap=1):
    """MUGEN v1 bitmap font: one PCX strip + [Def]/[Map] text. Variable width."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import sff1

    chars = "0123456789o" if digits_only else CHARSET
    imgs = [text(c, cap, fill, outline, ow, gradient=gradient) for c in chars]
    h = max(i.size[1] for i in imgs)
    strip_w = sum(i.size[0] for i in imgs)
    strip = Image.new("RGBA", (strip_w, h), (0, 0, 0, 0))
    mapping, x = [], 0
    for c, im in zip(chars, imgs):
        # baseline-align: punctuation such as "." sits at the bottom of the cap height
        y = h - im.size[1] if c in ".,:" else (0 if c not in "-+'" else (h - im.size[1]) // 2 if c != "'" else 0)
        strip.paste(im, (x, y), im)
        mapping.append((c, x, im.size[0]))
        x += im.size[0]
    spr = sff1.from_rgba(strip)
    b = io.BytesIO()
    spr.image.save(b, "PCX")
    pcx = b.getvalue()
    if not (len(pcx) > 769 and pcx[-769] == 0x0C):
        pcx += b"\x0c" + bytes(spr.image.getpalette()[:768])
    space = max(2, int(cap * SPACE / 6))
    if not digits_only:
        # each glyph's box includes its italic slant (cap * ITALIC px) and boxes never overlap, so
        # without this every letter gets a quarter-em of extra air: tuck most of the slant back in
        gap -= int(round(cap * ITALIC * 0.7))
    lines = ["[Def]", f"Size = {space},{h}", f"Spacing = {gap},0", "Colors = 255", "Offset = 0,0", "Type = Variable", "", "[Map]"]
    for c, sx, w in mapping:
        lines.append(f"{c} {sx} {w}")
        if c.isalpha() and c.isupper():
            lines.append(f"{c.lower()} {sx} {w}")
    txt = ("\r\n".join(lines) + "\r\n").encode("latin-1")
    hdr = b"ElecbyteFnt\0" + struct.pack("<HH", 0x0100, 0)
    tex_off = 64
    text_off = tex_off + len(pcx)
    hdr += struct.pack("<IIII", tex_off, len(pcx), text_off, len(txt))
    hdr += bytes(64 - len(hdr))
    with open(path, "wb") as f:
        f.write(hdr + pcx + txt)
