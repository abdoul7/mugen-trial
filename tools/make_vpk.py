"""
make_vpk.py -- package build/game into an installable .vpk (same result as the kit's
vita/make_vita.bat, with this project's name/TitleID and our own LiveArea art).

    python tools/make_vpk.py                       # dist/JFVT00001.vpk
    python tools/make_vpk.py --version 01.01
    python tools/make_vpk.py --self build/engine/DolmexicaInfinite.self   # engine built from
                                       # source by tools/engine/build_vita.sh instead of the kit's

Steps:
  1. draw icon0.png (128x128), bg.png (840x500), startup.png (280x158) as 8-bit indexed PNGs
     -- the Vita rejects LiveArea images that are not palettised
  2. param.sfo with TITLE_ID (exactly 9 chars, else install error 0xF0030000) -- tools/sfo.py
  3. zip: eboot.bin (the kit's prebuilt DolmexicaInfinite.self, or --self) + sce_sys + assets/
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


# Vita digital manual (sce_sys/manual/NNN.png, 960x544): opened from the game's LiveArea bubble.
# Button mapping is from the engine source: prism/vita/input_vita.cpp (Cross=A, Circle=B, Square=X,
# Triangle=Y, L=L, R=R) and repo/mugencommandhandler.cpp (MUGEN a=A, b=B, c=R, x=X, y=Y, z=L).
MANUAL = [
    ("CONTROLS", [
        ("D-pad / left stick", "Move, jump (up), crouch (down), block (hold back)"),
        ("Square", "Light punch   (x)"),
        ("Triangle", "Medium punch   (y)"),
        ("L", "Heavy punch   (z)"),
        ("Cross", "Light kick   (a)"),
        ("Circle", "Medium kick   (b)"),
        ("R", "Heavy kick   (c)"),
        ("Start", "Pause / resume a fight; confirm in menus"),
    ], "Punch/kick names follow the MUGEN convention; each fighter decides what its buttons do."),
    ("MENUS & SPECIAL MOVES", [
        ("Cross or Start", "Confirm (menus, character and stage select)"),
        ("D-pad", "Move the cursor"),
        ("Arcade", "You vs a series of CPU fighters"),
        ("Watch", "CPU vs CPU: pick both fighters and watch"),
        ("Quarter circle", "Down, down-forward, forward + punch or kick"),
        ("Dragon punch", "Forward, down, down-forward + punch"),
        ("Charge", "Hold back 1-2 s, then forward + button"),
        ("Remap buttons", "Options > Input Config > Key Config > Config all"),
    ], "Config all asks for each button in turn; saved automatically. Default (R) resets."),
]


def manual_page(title, rows, note, n, total):
    w, h = 960, 544
    img = Image.new("RGB", (w, h), (12, 14, 28))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 74], fill=(236, 112, 20))
    d.text((32, 12), title, font=font(48), fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    d.text((w - 110, 26), f"{n} / {total}", font=font(26), fill=(255, 255, 255))
    fk, fv = font(30), font(28)
    y = 92
    for k, v in rows:
        d.rounded_rectangle([32, y, 330, y + 40], 8, fill=(40, 48, 90))
        d.text((46, y + 3), k, font=fk, fill=(255, 220, 160))
        d.text((352, y + 5), v, font=fv, fill=(235, 235, 245))
        y += 47
    d.text((32, h - 46), note, font=font(22), fill=(170, 175, 200))
    return img.convert("P", palette=Image.ADAPTIVE, colors=255)


def main():
    version = sys.argv[sys.argv.index("--version") + 1] if "--version" in sys.argv else "01.00"
    engine = os.path.join(VITA, "common", "DolmexicaInfinite.self")
    if "--self" in sys.argv:
        engine = os.path.abspath(sys.argv[sys.argv.index("--self") + 1])
    with open(engine, "rb") as f:
        assert f.read(4) == b"SCE\0", f"{engine} is not a SELF"
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
    # --no-assets: engine + LiveArea only (a few MB, installs in seconds). The ~1.3 GB assets folder is then
    # copied straight to ux0:app/JFVT00001/assets over USB/FTP: a 1.3 GB vpk is slow for VitaShell to
    # unpack and promote, and the Vita going to sleep mid-install can hang the system.
    with_assets = "--no-assets" not in sys.argv
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("sce_sys/param.sfo", param)
        z.write(engine, "eboot.bin")
        for i, (title, rows, note) in enumerate(MANUAL, 1):
            path = os.path.join(sce, "manual", f"{i:03d}.png")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            manual_page(title, rows, note, i, len(MANUAL)).save(path, optimize=True)
            z.write(path, f"sce_sys/manual/{i:03d}.png")
        for rel in ("icon0.png", "livearea/contents/bg.png", "livearea/contents/startup.png", "livearea/contents/template.xml"):
            z.write(os.path.join(sce, rel), f"sce_sys/{rel}")
        for dp, _, fs in (os.walk(assets) if with_assets else []):
            for f in fs:
                if f.endswith((".soakbak", ".tmp")) or f.lower() == "thumbs.db":
                    continue
                full = os.path.join(dp, f)
                z.write(full, "assets/" + os.path.relpath(full, assets).replace(os.sep, "/"))
    os.makedirs(DIST, exist_ok=True)
    final = os.path.join(DIST, f"{TITLE_ID}.vpk")
    shutil.copy2(out, final)
    print(f"wrote {final} ({os.path.getsize(final) / 2**20:.1f} MB), TitleID {TITLE_ID}, version {version}, "
          f"engine {os.path.relpath(engine, ROOT)}")


if __name__ == "__main__":
    main()
