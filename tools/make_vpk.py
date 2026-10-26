"""
make_vpk.py -- package build/game into an installable .vpk (same result as the kit's
vita/make_vita.bat, with this project's name/TitleID and our own LiveArea art).

    python tools/make_vpk.py                       # dist/JFVT00001.vpk
    python tools/make_vpk.py --version 01.01

Steps:
  1. draw icon0.png (128x128), bg.png (840x500), startup.png (280x158) as 8-bit indexed PNGs
     -- the Vita rejects LiveArea images that are not palettised
  2. param.sfo with TITLE_ID (exactly 9 chars, else install error 0xF0030000) -- tools/sfo.py
  3. zip: eboot.bin (prebuilt DolmexicaInfinite.self) + sce_sys + the whole assets/ tree
"""

import os
import shutil
import sys
import zipfile

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfo  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VITA = os.path.join(ROOT, "build", "game", "vita")
DIST = os.path.join(ROOT, "dist")
SAMPLE_VPK = os.path.join(ROOT, "engine", "Dolmexica Infinite 1.8", "samples", "Dolmexica Infinite Version 1 8 for Vita.vpk")

GAME_NAME = "Jump Force Vita"
TITLE_ID = "JFVT00001"
assert len(TITLE_ID) == 9, "TitleID must be exactly 9 characters"


def font(size):
    for f in ("C:/Windows/Fonts/impact.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def panel(w, h, title, sub=None):
    img = Image.new("RGB", (w, h), (12, 14, 28))
    d = ImageDraw.Draw(img)
    for y in range(h):  # dark navy -> deep orange diagonal band
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=(int(12 + 70 * t), int(14 + 20 * t), int(28 + 10 * t)))
    d.polygon([(0, int(h * 0.62)), (w, int(h * 0.38)), (w, int(h * 0.5)), (0, int(h * 0.74))], fill=(236, 112, 20))
    f = font(int(h * (0.36 if sub is None else 0.24)))
    bw = d.textbbox((0, 0), title, font=f)
    d.text(((w - (bw[2] - bw[0])) / 2, h * (0.22 if sub else 0.28)), title, font=f, fill=(255, 255, 255),
           stroke_width=max(2, h // 60), stroke_fill=(0, 0, 0))
    if sub:
        fs = font(int(h * 0.09))
        sw = d.textbbox((0, 0), sub, font=fs)
        d.text(((w - (sw[2] - sw[0])) / 2, h * 0.78), sub, font=fs, fill=(255, 220, 160))
    return img.convert("P", palette=Image.ADAPTIVE, colors=255)


def main():
    version = sys.argv[sys.argv.index("--version") + 1] if "--version" in sys.argv else "01.00"
    sce = os.path.join(VITA, "common", "sce_sys")
    panel(128, 128, "JF").save(os.path.join(sce, "icon0.png"), optimize=True)
    panel(840, 500, "JUMP FORCE", "M.U.G.E.N  ·  Dolmexica Infinite").save(os.path.join(sce, "livearea", "contents", "bg.png"), optimize=True)
    panel(280, 158, "JUMP FORCE").save(os.path.join(sce, "livearea", "contents", "startup.png"), optimize=True)

    # param.sfo: the engine author's own sample build is the template (same keys/sizes the
    # kit's vita-mksfoex writes); only title, TitleID and version change. Packing is done here
    # in Python because Windows Smart App Control blocks the kit's unsigned vitasdk exes.
    with zipfile.ZipFile(SAMPLE_VPK) as z:
        entries = sfo.read(z.read("sce_sys/param.sfo"))
    values = {"TITLE": GAME_NAME, "STITLE": GAME_NAME, "TITLE_ID": TITLE_ID, "APP_VER": version}
    param = sfo.write([(k, f, m, values.get(k, v)) for k, f, m, v in entries])
    out = os.path.join(VITA, "build", f"{TITLE_ID}.vpk")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    assets = os.path.join(VITA, "..", "assets")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("sce_sys/param.sfo", param)
        z.write(os.path.join(VITA, "common", "DolmexicaInfinite.self"), "eboot.bin")
        for rel in ("icon0.png", "livearea/contents/bg.png", "livearea/contents/startup.png", "livearea/contents/template.xml"):
            z.write(os.path.join(sce, rel), f"sce_sys/{rel}")
        for dp, _, fs in os.walk(assets):
            for f in fs:
                if f.endswith((".soakbak", ".tmp")) or f.lower() == "thumbs.db":
                    continue
                full = os.path.join(dp, f)
                z.write(full, "assets/" + os.path.relpath(full, assets).replace(os.sep, "/"))
    os.makedirs(DIST, exist_ok=True)
    final = os.path.join(DIST, f"{TITLE_ID}.vpk")
    shutil.copy2(out, final)
    print(f"wrote {final} ({os.path.getsize(final) / 2**20:.1f} MB), TitleID {TITLE_ID}, version {version}")


if __name__ == "__main__":
    main()
