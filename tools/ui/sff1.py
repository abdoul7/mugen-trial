"""sff1.py -- read and write MUGEN SFF v1 sprite files (PCX sprites), the format of the
stock motif's system.sff / fight.sff.

    sprites = read("fight.sff")          # list of Sprite (group, item, axis, PIL "P" image)
    write("out.sff", sprites)            # every sprite gets its own palette

Index 0 of each sprite's palette is the transparent colour, as in MUGEN.
"""
import io
import struct
from dataclasses import dataclass

from PIL import Image

HEADER = b"ElecbyteSpr\0" + bytes([0, 1, 0, 1])


@dataclass
class Sprite:
    group: int
    item: int
    ax: int
    ay: int
    image: Image.Image  # mode "P"


def _pcx_palette(data):
    return data[-768:] if len(data) > 769 and data[-769] == 0x0C else None


def read(path):
    d = open(path, "rb").read()
    _, nimg, off = struct.unpack_from("<III", d, 16)
    out, raw, last_pal = [], [], None
    while off and off < len(d) and len(out) < nimg:
        nxt, ln, ax, ay, g, i, link, same = struct.unpack_from("<IIhhHHHB", d, off)
        if ln == 0:  # linked: same image as sprite `link`
            img = out[link].image.copy()
        else:
            pcx = d[off + 32: off + 32 + ln]
            pal = _pcx_palette(pcx)
            if same or pal is None:
                pcx = (pcx[:-769] if pal is not None else pcx) + b"\x0c" + (last_pal or bytes(768))
                pal = last_pal
            else:
                last_pal = pal
            img = Image.open(io.BytesIO(pcx))
            img.load()
            if img.mode != "P":
                img = img.convert("P")
        out.append(Sprite(g, i, ax, ay, img))
        raw.append(ln)
        off = nxt
    return out


def from_rgba(img, ax=0, ay=0, group=0, item=0, colors=255):
    """RGBA -> Sprite. Pixels with alpha < 128 become index 0 (transparent)."""
    img = img.convert("RGBA")
    rgb = Image.new("RGB", img.size, (0, 0, 0))
    rgb.paste(img, mask=img.getchannel("A"))
    q = rgb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = q.getpalette()[: colors * 3]
    # shift every index up by one so 0 is free for transparency
    alpha = img.getchannel("A").tobytes()
    idx = bytes(0 if a < 128 else i + 1 for i, a in zip(q.tobytes(), alpha))
    out = Image.frombytes("P", img.size, idx)
    full = [0, 0, 0] + pal + [0, 0, 0] * (255 - colors)
    out.putpalette(full[:768])
    return Sprite(group, item, ax, ay, out)


def _pcx_bytes(img):
    b = io.BytesIO()
    img.save(b, "PCX")
    data = b.getvalue()
    if _pcx_palette(data) is None:
        pal = (img.getpalette() or [])[:768]
        data += b"\x0c" + bytes(pal + [0] * (768 - len(pal)))
    return data


def write(path, sprites):
    groups = len({s.group for s in sprites})
    blobs = [_pcx_bytes(s.image) for s in sprites]
    hdr = HEADER + struct.pack("<IIII", groups, len(sprites), 512, 32) + b"\0"  # palette type 0: individual
    hdr += bytes(512 - len(hdr))
    out = bytearray(hdr)
    off = 512
    for s, blob in zip(sprites, blobs):
        nxt = off + 32 + len(blob)
        out += struct.pack("<IIhhHHHB", nxt if s is not sprites[-1] else 0, len(blob), s.ax, s.ay, s.group, s.item, 0, 0)
        out += bytes(32 - 19) + blob
        off = nxt
    with open(path, "wb") as f:
        f.write(out)
