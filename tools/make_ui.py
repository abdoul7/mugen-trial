"""
make_ui.py -- the Jump Force Vita motif ("jfv"): a modern restyle of the stock Dolmexica
motif that keeps every element it already has (title menu, select grid + cursors +
portraits, VS screen, lifebars, power bars, faces, names, timer, win icons, combo,
round / FIGHT / KO), and redraws them in one visual language taken from current fighting
games:

  * flat, slanted bars and panels instead of bevelled boxes (SF6, Tekken 8, Strive)
  * a red "damage trail" behind the health fill (the lifebar `mid` layer)
  * super meter moved to the bottom corners with a level chip (SF6, DBFZ)
  * the timer in a badge between the bars, round pips next to it (Tekken 8)
  * one angular italic typeface everywhere (tools/ui/glyphs.py), outlined for contrast
  * Jump Force colours: deep navy panels, orange/yellow accents, P1 cyan, P2 red

Everything is drawn here (no third-party art). Sprites are SFF v1 / PCX, 8-bit, 320x240
space, so they cost little texture memory on the Vita (the whole HUD is under 1 MB).

    python tools/make_ui.py            # after build_assets.py: writes build/game/assets/data/jfv
    python tools/make_ui.py --preview  # also writes ui-work/preview-*.png mock-ups

Output: data/jfv/{system.def, system.sff, fight.def, fight.sff, + stock snd/fx copies},
font/jfv_*.fnt, and mugen.cfg `motif = data/jfv/system.def`.
"""
import os
import re
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui"))
import glyphs  # noqa: E402
import sff1  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "build", "game", "assets")
DATA = os.path.join(ASSETS, "data")
OUT = os.path.join(DATA, "jfv")

NAVY = (9, 13, 28)
PANEL = (17, 23, 43)
PANEL2 = (26, 34, 60)
EDGE = (64, 84, 124)
ORANGE = (255, 122, 26)
YELLOW = (255, 208, 64)
P1C = (40, 190, 255)
P2C = (255, 56, 88)
WHITE = (255, 255, 255)
SS = 4  # supersampling for slanted edges


# ---------------------------------------------------------------- drawing helpers
def canvas(w, h, bg=(0, 0, 0, 0)):
    return Image.new("RGBA", (w * SS, h * SS), bg)


def done(img):
    return img.resize((img.size[0] // SS, img.size[1] // SS), Image.Resampling.LANCZOS)


def poly(d, pts, fill):
    d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)


def para(x, y, w, h, s):
    """Parallelogram, both ends leaning right ("/"), slant s px."""
    return [(x + s, y), (x + w, y), (x + w - s, y + h), (x, y + h)]


def vgrad(w, h, top, bottom, stops=None):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for yy in range(h):
        t = yy / max(1, h - 1)
        if stops:
            col = stops(t)
        else:
            col = tuple(int(a + (b - a) * t) for a, b in zip(top, bottom))
        d.line([(0, yy), (w, yy)], fill=col)
    return img


def masked(fill_img, shape_pts, size):
    """Fill image cut to a polygon (anti-aliased, then hard-thresholded for 8-bit)."""
    w, h = size
    m = Image.new("L", (w * SS, h * SS), 0)
    poly(ImageDraw.Draw(m), shape_pts, 255)
    m = m.resize((w, h), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(fill_img.convert("RGBA").resize((w, h)), mask=m)
    return out


def spr(img, ax, ay, g, i):
    return sff1.from_rgba(img, ax, ay, g, i)


# ---------------------------------------------------------------- fonts
FONTS = {  # file: (cap px, kwargs)
    "jfv_s.fnt": (7, {}),
    "jfv_m.fnt": (9, {}),
    "jfv_mhi.fnt": (9, {"gradient": ((255, 240, 150), ORANGE)}),
    "jfv_num.fnt": (12, {"digits_only": True}),
    "jfv_time.fnt": (9, {"digits_only": True, "gap": 0}),
    "jfv_l.fnt": (18, {"gradient": ((255, 246, 180), ORANGE), "ow": 2}),
}


def make_fonts():
    fd = os.path.join(ASSETS, "font")
    for name, (cap, kw) in FONTS.items():
        glyphs.write_fnt(os.path.join(fd, name), cap, **kw)


# ---------------------------------------------------------------- fight HUD
LIFE_W, LIFE_H, LIFE_S = 112, 9, 5      # health bar: range, height, slant
POW_W, POW_H, POW_S = 96, 5, 3          # super meter
P1_LIFE_X, P2_LIFE_X, LIFE_Y = 146, 174, 8
POW_Y = 226


def bar_sprite(w, h, s, fill, g, i, ax_pad=0):
    img = masked(fill, para(0, 0, w, h, s), (w, h))
    return spr(img, w - 1, 0, g, i)


def life_frame(accent, g):
    w, h = LIFE_W + 8, LIFE_H + 5
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, para(0, 0, w, h - 1, LIFE_S + 1), (*EDGE, 255))
    poly(d, para(1.4, 1.2, w - 2.8, h - 3.4, LIFE_S), (*NAVY, 255))
    poly(d, para(0, h - 2.2, w - 6, 2.2, 0.8), (*accent, 255))  # team colour underline
    return spr(done(c), LIFE_W + 3, 2, g, 0)


def pow_frame(accent, g):
    chip = 13
    w, h = POW_W + 6 + chip, POW_H + 4
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, para(chip, 0, w - chip, h, POW_S + 1), (*EDGE, 255))
    poly(d, para(chip + 1.2, 1, w - chip - 2.4, h - 2, POW_S), (*NAVY, 255))
    poly(d, para(0, 0, chip - 1, h, POW_S + 1), (*accent, 255))  # level chip
    for k in (1, 2):  # level ticks at 1/3 and 2/3
        x = chip + 3 + POW_W * k / 3
        poly(d, [(x, 1), (x + 1, 1), (x - 1, h - 1), (x - 2, h - 1)], (*EDGE, 255))
    return spr(done(c), POW_W + 2, 2, g, 0)


def face_frame(accent, g):
    w = h = 31
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, [(4, 0), (w, 0), (w, h - 4), (w - 4, h), (0, h), (0, 4)], (*accent, 255))
    poly(d, [(5, 1.5), (w - 1.5, 1.5), (w - 1.5, h - 5), (w - 5, h - 1.5), (1.5, h - 1.5), (1.5, 5)], (*PANEL2, 255))
    return spr(done(c), 0, 0, g, 0)


def timer_badge():
    w, h = 34, 22
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    hexa = lambda m: [(6 + m, m), (w - 6 - m, m), (w - m, h / 2), (w - 6 - m, h - m), (6 + m, h - m), (m, h / 2)]
    poly(d, hexa(0), (*ORANGE, 255))
    poly(d, hexa(1.6), (*NAVY, 255))
    return spr(done(c), w // 2, h // 2, 120, 0)


def pip(color, g, letter=None):
    w = h = 7
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, [(3.5, 0), (7, 3.5), (3.5, 7), (0, 3.5)], (0, 0, 0, 255))
    poly(d, [(3.5, 1), (6, 3.5), (3.5, 6), (1, 3.5)], (*color, 255))
    return spr(done(c), 3, 3, g, 0)


def big_word(word, cap, flash=False):
    grad = ((255, 255, 255), (255, 255, 230)) if flash else ((255, 246, 180), ORANGE)
    return glyphs.text(word, cap, gradient=grad, outline=(20, 8, 0), ow=2)


def squash(img, fx, fy):
    w, h = img.size
    return img.resize((max(1, int(w * fx)), max(1, int(h * fy))), Image.Resampling.LANCZOS)


def fight_sprites():
    life_fill = vgrad(LIFE_W, LIFE_H, None, None,
                      stops=lambda t: (255, 250, 200) if t < 0.18 else
                      tuple(int(a + (b - a) * (t - 0.18) / 0.82) for a, b in zip((255, 222, 80), (255, 150, 20))))
    trail = vgrad(LIFE_W, LIFE_H, (255, 90, 70), (200, 30, 30))
    dark = Image.new("RGB", (LIFE_W, LIFE_H), (5, 7, 16))
    pow_fill = vgrad(POW_W, POW_H, (170, 240, 255), (30, 120, 255))
    pdark = Image.new("RGB", (POW_W, POW_H), (5, 7, 16))
    s = [
        bar_sprite(LIFE_W, LIFE_H, LIFE_S, dark, 10, 0),
        life_frame(P1C, 11), life_frame(P2C, 14),
        bar_sprite(LIFE_W, LIFE_H, LIFE_S, trail, 12, 0),
        bar_sprite(LIFE_W, LIFE_H, LIFE_S, life_fill, 13, 0),
        bar_sprite(POW_W, POW_H, POW_S, pdark, 40, 0),
        pow_frame(P1C, 41), pow_frame(P2C, 44),
        bar_sprite(POW_W, POW_H, POW_S, pow_fill, 43, 0),
        face_frame(P1C, 50), face_frame(P2C, 51),
        timer_badge(),
    ]
    # win icons: one diamond per round won, coloured by how it was won
    for g, col in ((100, ORANGE), (101, P1C), (102, YELLOW), (103, (90, 220, 120)), (104, (150, 150, 160)),
                   (105, WHITE), (106, (150, 150, 160)), (107, (150, 150, 160)), (110, (255, 240, 120))):
        s.append(pip(col, g))
    # FIGHT! (anim 80): 80,0 normal, 80,1-5 squash out, 80,6-7 flash
    f = big_word("FIGHT!", 30)
    fw, fh = f.size
    s.append(spr(f, fw // 2, fh // 2, 80, 0))
    for k, fy in enumerate((0.8, 0.6, 0.4, 0.22, 0.08), 1):
        im = squash(f, 1 + 0.12 * k, fy)
        s.append(spr(im, im.size[0] // 2, im.size[1] // 2, 80, k))
    fl = big_word("FIGHT!", 30, flash=True)
    s.append(spr(fl, fw // 2, fh // 2, 80, 6))
    s.append(spr(f, fw // 2, fh // 2, 80, 7))
    # K.O. (anim 200): built up letter by letter, flash, then squash out
    full, fullfl = big_word("K.O.", 36), big_word("K.O.", 36, flash=True)
    W, H = full.size
    def part(txt, flash):
        im = big_word(txt, 36, flash)
        c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        c.paste(im, (0, H - im.size[1]), im)
        return c
    seq = {0: full, 1: part("K", True), 2: part("K", False), 3: part("K.O", True), 4: part("K.O", False), 5: fullfl}
    for k, fy in zip(range(6, 11), (0.8, 0.6, 0.4, 0.22, 0.08)):
        seq[k] = squash(full, 1 + 0.1 * (k - 5), fy)
    for k, im in seq.items():
        s.append(spr(im, im.size[0] // 2, 0 if k <= 5 else -(H - im.size[1]) // 2, 200, k))
    return s


FIGHT_KEYS = {
    "files": {"font1": "jfv_m.fnt", "font2": "jfv_num.fnt", "font3": "jfv_s.fnt", "font4": "jfv_l.fnt", "font5": "jfv_mhi.fnt", "font6": "jfv_time.fnt"},
    "lifebar": {
        "p1.pos": f"{P1_LIFE_X},{LIFE_Y}", "p1.range.x": f"0,-{LIFE_W - 1}",
        "p2.pos": f"{P2_LIFE_X},{LIFE_Y}", "p2.range.x": f"0,{LIFE_W - 1}", "p2.bg1.spr": "14,0",
    },
    "powerbar": {
        "p1.pos": f"{P1_LIFE_X - 8},{POW_Y}", "p1.range.x": f"0,-{POW_W - 1}", "p1.counter.offset": f"-{POW_W - 5},4",
        "p1.counter.font": "1,0,0",
        "p2.pos": f"{P2_LIFE_X + 8},{POW_Y}", "p2.range.x": f"0,{POW_W - 1}", "p2.counter.offset": f"{POW_W - 4},4",
        "p2.counter.font": "1,0,0", "p2.bg1.spr": "44,0",
    },
    "face": {
        "p1.pos": "2,3", "p1.face.offset": "2,2",
        "p2.pos": "317,3", "p2.bg.spr": "51,0", "p2.face.offset": "-2,2",
    },
    "name": {"p1.pos": "36,29", "p1.name.font": "3,0,1", "p2.pos": "284,29", "p2.name.font": "3,0,-1"},
    "time": {"pos": "160,17", "bg.spr": "120,0", "bg.offset": "0,-9", "counter.font": "6,0,0"},
    "winicon": {"p1.pos": "141,25", "p2.pos": "179,25", "p1.iconoffset": "-9,0", "p2.iconoffset": "9,0",
                "p1.counter.font": "3,0", "p2.counter.font": "3,0"},
    "combo": {
        "team1.pos": "10,90", "team1.start.x": "-90", "team2.start.x": "410", "team1.counter.font": "2,5,1", "team1.text.text": "HITS", "team1.text.font": "1,0,1",
        "team1.text.offset": "4,0",
        "team2.pos": "309,90", "team2.counter.font": "2,5,-1", "team2.text.text": "HITS", "team2.text.font": "1,0,-1",
        "team2.text.offset": "4,0",
    },
    "round": {
        "round.default.font": "4,0,0", "round.default.text": "ROUND %i", "round.default.offset": "160,104",
        "fight.offset": "160,96", "ko.offset": "160,78",
        "dko.font": "4,0,0", "dko.text": "DOUBLE K.O.", "to.font": "4,0,0", "to.text": "TIME OVER",
        "win.font": "4,0,0", "win.text": "%s WINS", "win2.font": "4,0,0", "draw.font": "4,0,0", "draw.text": "DRAW",
    },
}


# ---------------------------------------------------------------- title / select / VS
def speed_lines(w, h, color, n=22, seed=7):
    import random
    rnd = random.Random(seed)
    c = canvas(w, h, (0, 0, 0, 255))
    d = ImageDraw.Draw(c)
    for _ in range(n):
        y = rnd.uniform(0, h)
        x = rnd.uniform(-w * 0.2, w)
        L = rnd.uniform(w * 0.15, w * 0.5)
        t = rnd.uniform(0.4, 1.4)
        k = rnd.uniform(0.25, 1.0)
        col = tuple(int(v * k) for v in color) + (255,)
        poly(d, [(x, y), (x + L, y - L * 0.18), (x + L, y - L * 0.18 + t), (x, y + t)], col)
    return done(c)


def backdrop(w=320, h=240, tint=(0, 0, 0)):
    """Navy gradient with a diagonal orange light band: the shared background of every screen."""
    bg = vgrad(w, h, (16, 22, 46), (4, 6, 14)).convert("RGBA")
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, [(w * 0.42, 0), (w * 0.62, 0), (w * 0.38, h), (w * 0.18, h)], (255, 110, 20, 38))
    poly(d, [(w * 0.66, 0), (w * 0.70, 0), (w * 0.46, h), (w * 0.42, h)], (255, 190, 60, 30))
    for k in range(0, h, 4):  # fine scanline texture
        poly(d, [(0, k), (w, k), (w, k + 0.6), (0, k + 0.6)], (255, 255, 255, 6))
    bg.alpha_composite(done(c))
    if tint != (0, 0, 0):
        bg.alpha_composite(Image.new("RGBA", (w, h), tint + (40,)))
    return bg


def logo():
    jf = glyphs.text("JUMP FORCE", 30, gradient=((255, 250, 210), (255, 132, 24)), outline=(24, 8, 0), ow=2)
    vt = glyphs.text("VITA", 12, fill=WHITE, outline=None, ow=0)
    w = jf.size[0] + 6
    tag_w, tag_h = vt.size[0] + 16, vt.size[1] + 6
    h = jf.size[1] + tag_h + 2
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    c.paste(jf, (0, 0), jf)
    tag = canvas(tag_w, tag_h)
    d = ImageDraw.Draw(tag)
    poly(d, para(0, 0, tag_w, tag_h, 5), (*P2C, 255))
    tag = done(tag)
    tag.paste(vt, ((tag_w - vt.size[0]) // 2, 3), vt)
    c.paste(tag, (w - tag_w - 4, jf.size[1] + 1), tag)
    return c


def menu_panel():
    w, h = 170, 84
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, para(0, 0, w, h, 12), (*PANEL, 255))
    poly(d, para(10, 0, w - 10, 2, 0.4), (*ORANGE, 255))
    poly(d, para(0, h - 2, w - 12, 2, 0.4), (*EDGE, 255))
    return done(c)


def footer(text):
    t = glyphs.text(text, 5, fill=(150, 165, 200), outline=None, ow=0)
    c = Image.new("RGBA", (320, 11), (5, 7, 15, 255))
    c.paste(t, ((320 - t.size[0]) // 2, 3), t)
    return c


def header(w=320, h=22):
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, [(0, 0), (w, 0), (w, h - 4), (0, h - 4)], (*NAVY, 255))
    poly(d, para(96, h - 5, w - 192, 3, 2), (*ORANGE, 255))
    poly(d, [(0, h - 4), (w, h - 4), (w, h - 3), (0, h - 3)], (*EDGE, 255))
    return done(c)


def side_panel(accent, flip):
    """Slanted colour slab behind a select-screen portrait: team colour fading into navy."""
    w, h = 132, 122
    grad = vgrad(w, h, tuple(int(v * 0.55) for v in accent), tuple(int(v * 0.12) for v in accent))
    img = masked(grad, para(0, 0, w, h, 18), (w, h))
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, para(0, 0, w, 2.5, 0.4), (*accent, 255))
    poly(d, [(w - 1.6, 0), (w, 0), (w - 18, h), (w - 19.6, h)], (*accent, 255))  # inner edge
    for k in range(4):  # hairlines
        y = 30 + k * 22
        poly(d, [(0, y), (w, y - 14), (w, y - 13.4), (0, y + 0.6)], (*[min(255, int(v * 0.8)) for v in accent], 70))
    img.alpha_composite(done(c))
    return img.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if flip else img


def name_plate(accent, flip, w=124, h=13):
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, para(0, 0, w, h, 6), (*PANEL, 255))
    poly(d, para(0, 0, 4, h, 6), (*accent, 255))
    img = done(c)
    return img.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if flip else img


def grid_panel(w=300, h=94):
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, [(6, 0), (w, 0), (w, h - 6), (w - 6, h), (0, h), (0, 6)], (*EDGE, 255))
    poly(d, [(6.5, 1), (w - 1, 1), (w - 1, h - 6.5), (w - 6.5, h - 1), (1, h - 1), (1, 6.5)], (7, 10, 22, 255))
    return done(c)


def cell(random_cell=False):
    w = h = 27
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, [(3, 0), (w, 0), (w, h - 3), (w - 3, h), (0, h), (0, 3)], (*EDGE, 255))
    poly(d, [(3.5, 1), (w - 1, 1), (w - 1, h - 3.5), (w - 3.5, h - 1), (1, h - 1), (1, 3.5)], (*PANEL2, 255))
    img = done(c)
    if random_cell:
        q = glyphs.text("?", 14, gradient=((255, 240, 150), ORANGE), ow=1)
        img.paste(q, ((w - q.size[0]) // 2, (h - q.size[1]) // 2), q)
    return img


def cursor(accent, label, filled):
    w, h = 33, 39
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    o = 10  # label tab height above the cell frame
    t = 3.6 if filled else 2.2
    poly(d, [(0, o), (w, o), (w, h), (0, h)], (*accent, 255))
    poly(d, [(t, o + t), (w - t, o + t), (w - t, h - t), (t, h - t)], (0, 0, 0, 0))
    poly(d, para(0, 0, 21, o + 0.5, 3), (*accent, 255))
    img = done(c)
    # clear the inside properly (polygon with alpha 0 doesn't erase)
    inner = Image.new("L", img.size, 0)
    ImageDraw.Draw(inner).rectangle([int(t) + 1, o + int(t) + 1, w - int(t) - 2, h - int(t) - 2], fill=255)
    img.paste((0, 0, 0, 0), mask=inner)
    x = 3
    for ch in label:  # one glyph at a time: at this size the italic "1" runs into the "P"
        g = glyphs.text(ch, 7, fill=(8, 10, 20), outline=None, ow=0, stroke=1.6)
        img.paste(g, (x, 1), g)
        x += g.size[0] + 1
    return img


def vs_backdrop():
    w, h = 320, 240
    bg = backdrop()
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, [(0, 0), (178, 0), (142, h), (0, h)], (*P1C, 46))
    poly(d, [(178, 0), (w, 0), (w, h), (142, h)], (*P2C, 46))
    poly(d, [(176, 0), (181, 0), (145, h), (140, h)], (255, 255, 255, 220))
    bg.alpha_composite(done(c))
    lines = speed_lines(w, h, (255, 160, 60), n=30)
    bg.alpha_composite(Image.merge("RGBA", (*lines.split()[:3], lines.convert("L").point(lambda v: min(255, v)))))
    return bg


def portrait_frame(accent, w=124, h=144):
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, [(8, 0), (w, 0), (w, h - 8), (w - 8, h), (0, h), (0, 8)], (*accent, 255))
    poly(d, [(9, 2), (w - 2, 2), (w - 2, h - 9), (w - 9, h - 2), (2, h - 2), (2, 9)], (*NAVY, 255))
    return done(c)


def vs_logo(flash=False):
    grad = ((255, 255, 255), (255, 255, 235)) if flash else ((255, 250, 200), ORANGE)
    return glyphs.text("VS", 34, gradient=grad, outline=(24, 8, 0), ow=2, stroke=1.5)


def system_sprites(grid):
    s = []
    s.append(spr(backdrop(), 0, 0, 1000, 0))
    s.append(spr(speed_lines(320, 240, (255, 140, 40)), 0, 0, 1001, 0))
    lg = logo()
    s.append(spr(lg, lg.size[0] // 2, 0, 1002, 0))
    s.append(spr(menu_panel(), 85, 0, 1003, 0))
    # select
    s.append(spr(backdrop(), 0, 0, 1100, 0))
    s.append(spr(grid_panel(grid["cols"] * 29 + 8, grid["rows"] * 29 + 8), 0, 0, 1101, 0))
    s.append(spr(header(), 0, 0, 1102, 0))
    s.append(spr(side_panel(P1C, False), 0, 0, 1103, 0))
    s.append(spr(side_panel(P2C, True), 0, 0, 1104, 0))
    s.append(spr(name_plate(P1C, False), 0, 0, 1105, 0))
    s.append(spr(name_plate(P2C, True), 0, 0, 1106, 0))
    s.append(spr(cell(), 1, 1, 150, 0))
    s.append(spr(cell(True), 1, 1, 151, 0))
    for g, col, lab, fill in ((160, P1C, "1P", False), (161, P1C, "1P", True), (170, P2C, "2P", False), (171, P2C, "2P", True)):
        s.append(spr(cursor(col, lab, fill), 3, 13, g, 0))
    # VS
    s.append(spr(vs_backdrop(), 0, 0, 1200, 0))
    s.append(spr(portrait_frame(P1C), 0, 0, 1201, 0))
    s.append(spr(portrait_frame(P2C), 0, 0, 1202, 0))
    s.append(spr(name_plate(P1C, False, 132, 15), 0, 0, 1203, 0))
    s.append(spr(name_plate(P2C, True, 132, 15), 0, 0, 1204, 0))
    v, vf = vs_logo(), vs_logo(True)
    W, H = v.size
    s.append(spr(v, W // 2, H // 2, 200, 0))
    for k, (fx, fy) in zip((4, 3, 2, 1), ((3.0, 0.2), (2.2, 0.45), (1.6, 0.7), (1.2, 0.9))):
        im = squash(v, fx, fy)
        s.append(spr(im, im.size[0] // 2, im.size[1] // 2, 200, k))
    for k in (5, 7):
        s.append(spr(vf, W // 2, H // 2, 200, k))
    for k in (6, 8):
        s.append(spr(v, W // 2, H // 2, 200, k))
    return s


def bg(name, **kv):
    if kv.get("type") == "normal" and not kv.get("start", "").startswith("-160,0"):
        kv.setdefault("mask", "1")  # colour 0 is only transparent in BG layers with mask = 1
    return f"[{name}]\n" + "".join(f"{k} = {v}\n" for k, v in kv.items()) + "\n"


TITLE_BG = (bg("TitleBGdef", bgclearcolor="0,0,0")
            + bg("TitleBG 0", type="normal", spriteno="1000,0", start="-160,0")
            + bg("TitleBG 1", type="normal", spriteno="1001,0", start="-160,0", tile="1,0", velocity="-3,0", trans="add")
            + bg("TitleBG 2", type="normal", spriteno="1002,0", start="0,34")
            + bg("TitleBG 3", type="normal", spriteno="1003,0", start="0,136"))
SELECT_BG = (bg("SelectBGdef", bgclearcolor="0,0,0")
             + bg("SelectBG 0", type="normal", spriteno="1100,0", start="-160,0")
             + bg("SelectBG 1", type="normal", spriteno="1103,0", start="-152,20")
             + bg("SelectBG 2", type="normal", spriteno="1104,0", start="20,20")
             + bg("SelectBG 3", type="normal", spriteno="1105,0", start="-154,121")
             + bg("SelectBG 4", type="normal", spriteno="1106,0", start="30,121")
             + bg("SelectBG 5", type="normal", spriteno="1101,0", start="{gx},{gy}")
             + bg("SelectBG 6", type="normal", spriteno="1102,0", start="-160,0"))
VS_BG = (bg("VersusBGdef", bgclearcolor="0,0,0")
         + bg("VersusBG 0", type="normal", spriteno="1200,0", start="-160,0")
         + bg("VersusBG 1", type="normal", spriteno="1201,0", start="-142,29")
         + bg("VersusBG 2", type="normal", spriteno="1202,0", start="18,29")
         + bg("VersusBG 3", type="normal", spriteno="1203,0", start="-150,181")
         + bg("VersusBG 4", type="normal", spriteno="1204,0", start="18,181")
         + bg("VersusBG 5", type="anim", actionno="200", layerno="1", start="0,100")
         + "[Begin Action 200]\n"  # VS logo: slams in wide and flat, settles, flashes
         + "".join(f"200,{k}, 0,0, {t}\n" for k, t in ((4, 1), (3, 2), (2, 2), (1, 2), (0, 8), (5, 2), (6, 3), (7, 2), (8, 3)))
         + "200,0, 0,0, -1\n\n")

SYSTEM_KEYS = {
    "files": {"font1": "font/jfv_s.fnt", "font2": "font/jfv_m.fnt", "font3": "font/jfv_m.fnt", "font4": "font/jfv_mhi.fnt",
              "font5": "font/jfv_l.fnt"},
    "title info": {"menu.pos": "160,154", "menu.item.font": "3,0,0", "menu.item.active.font": "4,0,0",
                   "menu.item.spacing": "0,14", "menu.boxcursor.coords": "-62,-13,61,1",
                   "menu.window.margins.y": "14,-3", "menu.window.visibleitems": "5"},
    "select info": {"title.offset": "160,15", "title.font": "4,0,0",
                    "p1.face.offset": "20,22", "p2.face.offset": "299,22",
                    "p1.face.scale": "0.75,0.75", "p2.face.scale": "0.75,0.75",
                    "p1.name.offset": "16,131", "p1.name.font": "3,0,1",
                    "p2.name.offset": "304,131", "p2.name.font": "3,0,-1",
                    "stage.pos": "160,40", "stage.active.font": "4,0,0", "stage.active2.font": "3,0,0",
                    "stage.done.font": "4,0,0"},
    "vs screen": {"p1.pos": "20,31", "p2.pos": "299,31", "p1.name.pos": "80,192", "p1.name.font": "1,0,0",
                  "p2.name.pos": "240,192", "p2.name.font": "1,0,0"},
}


# ---------------------------------------------------------------- def editing
def read(p):
    with open(p, encoding="latin-1") as f:
        return f.read().replace("\r\n", "\n")


def write(p, t):
    with open(p, "w", encoding="latin-1", newline="\r\n") as f:
        f.write(t)


def set_keys(text, section, kv):
    """Replace (or add) key = value lines inside [section] (case-insensitive)."""
    m = re.search(rf"(?im)^\[{re.escape(section)}\][^\n]*\n", text)
    if not m:
        return text + f"\n[{section}]\n" + "".join(f"{k} = {v}\n" for k, v in kv.items())
    start = m.end()
    nxt = re.search(r"(?m)^\[", text[start:])
    end = start + nxt.start() if nxt else len(text)
    body = text[start:end]
    for k, v in kv.items():
        pat = rf"(?im)^[ \t]*;?[ \t]*{re.escape(k)}[ \t]*=[^\n]*"
        if re.search(pat, body):
            body = re.sub(pat, f"{k} = {v}", body, count=1)
        else:
            body = body.rstrip("\n") + f"\n{k} = {v}\n\n"
    return text[:start] + body + text[end:]


def replace_sections(text, prefix, new):
    """Drop every [prefix...] section (and the Begin Action blocks between them) and insert `new`."""
    pat = rf"(?ims)^\[{prefix}.*?(?=^\[(?!{prefix}|Begin Action))"
    first = re.search(pat, text)
    text2 = re.sub(pat, "", text)
    pos = first.start() if first else len(text2)
    return text2[:pos] + new + text2[pos:]


def build_fight(stock):
    t = stock
    for sec, kv in FIGHT_KEYS.items():
        t = set_keys(t, sec, kv)
    # the darkened backgrounds were subtractive (trans S); draw them opaque
    t = re.sub(r"(?im)^(\s*(?:10|20|40),0,\s*0,0,\s*1),\s*,\s*S\s*$", r"\1", t)
    return t


def grid_of(sysdef):
    """Select grid as build_assets.py laid it out for this roster (rows grow with the roster)."""
    sec = re.search(r"(?is)\[Select Info\](.*?)(?=\n\[)", sysdef).group(1)
    val = lambda k: re.search(rf"(?im)^\s*{re.escape(k)}\s*=\s*([^;\n]+)", sec).group(1).strip()
    x, y = (int(v) for v in val("pos").split(","))
    return {"rows": int(val("rows")), "cols": int(val("columns")), "x": x, "y": y}


def build_system(stock):
    t = stock
    for sec, kv in SYSTEM_KEYS.items():
        t = set_keys(t, sec, kv)
    t = replace_sections(t, "TitleBG", TITLE_BG)
    g = grid_of(stock)
    t = replace_sections(t, "SelectBG", SELECT_BG.replace("{gx},{gy}", f"{g['x'] - 5 - 160},{g['y'] - 5}"))
    t = replace_sections(t, "VersusBG", VS_BG)
    t = re.sub(r"(?im)^(\s*)(fight|spr|snd)(\s*=\s*)(fight\.def|system\.sff|system\.snd)", r"\1\2\3\4", t)
    return t


def preview(sprites, name):
    """Contact sheet of the generated sprites, for review (ui-work/ is git-ignored)."""
    os.makedirs(os.path.join(ROOT, "ui-work"), exist_ok=True)
    ims = [s.image.convert("RGBA") for s in sprites]
    W = 330
    x = y = rowh = 0
    pos = []
    for im in ims:
        if x + im.size[0] > W:
            x, y, rowh = 0, y + rowh + 4, 0
        pos.append((x, y))
        x += im.size[0] + 4
        rowh = max(rowh, im.size[1])
    sheet = Image.new("RGBA", (W, y + rowh + 4), (60, 60, 70, 255))
    for im, p in zip(ims, pos):
        sheet.alpha_composite(im, p)
    sheet.resize((sheet.size[0] * 2, sheet.size[1] * 2), Image.NEAREST).save(os.path.join(ROOT, "ui-work", f"sprites-{name}.png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    make_fonts()
    fs = fight_sprites()
    ss = system_sprites(grid_of(read(os.path.join(DATA, "system.def"))))
    # keep any stock fight sprite we didn't redraw (e.g. team-mode bars), under the new ones
    mine = {(s.group, s.item) for s in fs}
    stock_fight = [s for s in sff1.read(os.path.join(DATA, "fight.sff")) if (s.group, s.item) not in mine]
    sff1.write(os.path.join(OUT, "fight.sff"), fs + stock_fight)
    sff1.write(os.path.join(OUT, "system.sff"), ss)
    write(os.path.join(OUT, "fight.def"), build_fight(read(os.path.join(DATA, "fight.def"))))
    write(os.path.join(OUT, "system.def"), build_system(read(os.path.join(DATA, "system.def"))))
    # sounds, fight fx and select.def are not copied: the engine falls back to data/ for any
    # file missing from the motif folder (config.cpp findMugenSystemOrFightFilePath)
    cfg = os.path.join(DATA, "mugen.cfg")
    t = read(cfg)
    t = re.sub(r"(?im)^(\s*motif\s*=\s*)[^;\n]*", r"\1data/jfv/system.def", t)
    write(cfg, t)
    if "--preview" in sys.argv:
        preview(fs, "fight")
        preview(ss, "system")
    kb = sum(os.path.getsize(os.path.join(OUT, f)) for f in ("fight.sff", "system.sff")) // 1024
    print(f"jfv motif -> {os.path.relpath(OUT, ROOT)} ({len(fs)} fight + {len(ss)} system sprites, {kb} KB)")


if __name__ == "__main__":
    main()
