"""legends_art.py -- the Legends HUD sprites (legends.sff), drawn with the jfv motif's helpers.

Group numbers must match the SPR_* enum in tools/legends/engine/legendsmode.cpp. Family index:
0 Resolve (teal, crest), 1 Secret Arts (orange, slash), 2 Awakenings (red, flame), 3 Plot Twists
(violet, hourglass), as in docs/legends-design.md section 9. Card illustrations are not drawn here:
the art window shows the family icon until the art kit exists (rarity art coverage is pending).
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import make_ui as ui  # noqa: E402
from make_ui import canvas, done, para, poly, px, spr  # noqa: E402

FAMILY = [(52, 214, 196), (255, 140, 40), (255, 72, 72), (176, 120, 255)]
NAVY, PANEL, EDGE, WHITE = ui.NAVY, ui.PANEL, ui.EDGE, ui.WHITE


def dark(c, k=0.35):
    return tuple(int(v * k) for v in c)


def icon(f, s=12):
    c = canvas(s, s)
    d = ImageDraw.Draw(c)
    col = (*FAMILY[f], 255)
    if f == 0:   # crest
        poly(d, [(2, 1), (10, 1), (10, 6), (6, 11), (2, 6)], col)
        poly(d, [(4, 3), (8, 3), (8, 6), (6, 8.5), (4, 6)], (*dark(FAMILY[f]), 255))
    elif f == 1:  # slash
        poly(d, [(9, 0.5), (11, 1.5), (3, 11.5), (1, 10.5)], col)
        poly(d, [(6, 1), (7, 1.6), (2, 8), (1.2, 7.2)], (*WHITE, 255))
    elif f == 2:  # flame
        poly(d, [(6, 0.5), (9, 4), (10, 7.5), (8, 11), (4, 11), (2, 7.5), (3, 4.5), (5, 6)], col)
        poly(d, [(6, 5), (7.6, 7.5), (6.8, 10), (5.2, 10), (4.4, 8)], (255, 230, 150, 255))
    else:        # hourglass
        poly(d, [(2, 1), (10, 1), (6.6, 6), (10, 11), (2, 11), (5.4, 6)], col)
        poly(d, [(4, 2.4), (8, 2.4), (6, 5)], (255, 240, 200, 255))
        poly(d, [(6, 7.5), (8.2, 9.8), (3.8, 9.8)], (255, 240, 200, 255))
    return done(c)


def pips(n):
    w = 4 * 5 + 2
    c = canvas(w, 6)
    d = ImageDraw.Draw(c)
    for k in range(4):
        x = 1 + k * 5
        on = k < n
        poly(d, [(x + 2, 0.5), (x + 4, 3), (x + 2, 5.5), (x, 3)], (255, 214, 90, 255) if on else (*EDGE, 255))
    return done(c)


def tile(f, w=86, h=26):
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, para(0, 0, w, h, 4), (*FAMILY[f], 255))
    poly(d, para(1.2, 1.2, w - 2.4, h - 2.4, 3.6), (*NAVY, 255))
    poly(d, para(1.2, 1.2, 22, h - 2.4, 3.6), (*dark(FAMILY[f], 0.45), 255))   # art window
    poly(d, para(24, h - 3, w - 28, 1, 0.2), (*dark(FAMILY[f], 0.7), 255))
    return done(c)


def outline(w, h, col, t=1.4, dashed=False):
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    if dashed:
        for x in range(0, w, 6):
            poly(d, [(x, 0), (x + 3, 0), (x + 3, t), (x, t)], (*col, 255))
            poly(d, [(x, h - t), (x + 3, h - t), (x + 3, h), (x, h)], (*col, 255))
        for y in range(0, h, 6):
            poly(d, [(0, y), (t, y), (t, y + 3), (0, y + 3)], (*col, 255))
            poly(d, [(w - t, y), (w, y), (w, y + 3), (w - t, y + 3)], (*col, 255))
    else:
        poly(d, [(0, 0), (w, 0), (w, t), (0, t)], (*col, 255))
        poly(d, [(0, h - t), (w, h - t), (w, h), (0, h)], (*col, 255))
        poly(d, [(0, 0), (t, 0), (t, h), (0, h)], (*col, 255))
        poly(d, [(w - t, 0), (w, 0), (w, h), (w - t, h)], (*col, 255))
    return done(c)


def card_face(f, w=76, h=104):
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, [(3, 0), (w, 0), (w, h - 3), (w - 3, h), (0, h), (0, 3)], (*FAMILY[f], 255))
    poly(d, [(3.6, 1.4), (w - 1.4, 1.4), (w - 1.4, h - 3.6), (w - 3.6, h - 1.4), (1.4, h - 1.4), (1.4, 3.6)], (*NAVY, 255))
    poly(d, [(1.4, 14), (w - 1.4, 14), (w - 1.4, 50), (1.4, 50)], (*dark(FAMILY[f], 0.4), 255))   # art window
    for k in range(6):  # simple diagonal backdrop in the art window (placeholder illustration)
        x = k * 14 - 6
        poly(d, [(x, 50), (x + 6, 50), (x + 26, 14), (x + 20, 14)], (*dark(FAMILY[f], 0.55), 255))
    poly(d, [(1.4, 50), (w - 1.4, 50), (w - 1.4, 51.4), (1.4, 51.4)], (*FAMILY[f], 255))
    img = done(c)
    ic = icon(f, 28)
    img.paste(ic, ((img.size[0] - ic.size[0]) // 2, px(18)), ic)
    return img


def echo_ball():
    c = canvas(18, 18)
    d = ImageDraw.Draw(c)
    for r, col in ((9, (40, 110, 255)), (7, (90, 170, 255)), (5, (180, 225, 255)), (3, (255, 255, 255))):
        d.ellipse([px(9 - r) * ui.SS, px(9 - r) * ui.SS, px(9 + r) * ui.SS - 1, px(9 + r) * ui.SS - 1], fill=(*col, 255))
    return done(c)


def echo_bolt():
    c = canvas(28, 14)
    d = ImageDraw.Draw(c)
    pts = [(0, 7), (6, 3), (10, 9), (15, 2), (19, 10), (24, 4), (28, 7)]
    for k in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[k], pts[k + 1]
        poly(d, [(x0, y0 - 1.6), (x1, y1 - 1.6), (x1, y1 + 1.6), (x0, y0 + 1.6)], (120, 190, 255, 255))
        poly(d, [(x0, y0 - 0.6), (x1, y1 - 0.6), (x1, y1 + 0.6), (x0, y0 + 0.6)], (255, 255, 255, 255))
    return done(c)


def spark():
    c = canvas(20, 20)
    d = ImageDraw.Draw(c)
    poly(d, [(10, 0), (12, 8), (20, 10), (12, 12), (10, 20), (8, 12), (0, 10), (8, 8)], (255, 230, 120, 255))
    poly(d, [(10, 5), (11, 9), (15, 10), (11, 11), (10, 15), (9, 11), (5, 10), (9, 9)], (255, 255, 255, 255))
    return done(c)


def squad_pip(state):
    c = canvas(6, 6)
    d = ImageDraw.Draw(c)
    col = [(255, 255, 255), (120, 130, 160), (150, 30, 40)][state]
    poly(d, [(3, 0), (6, 3), (3, 6), (0, 3)], (*col, 255))
    return done(c)


def panel(w, h, accent=ui.ORANGE):
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, para(0, 0, w, h, 10), (*PANEL, 240))
    poly(d, para(9, 0, w - 9, 1.6, 0.2), (*accent, 255))
    poly(d, para(0, h - 1.4, w - 10, 1.4, 0.2), (*EDGE, 255))
    return done(c)


def bar(w, h, col):
    c = canvas(w, h)
    poly(ImageDraw.Draw(c), [(0, 0), (w, 0), (w, h), (0, h)], (*col, 255))
    return done(c)


def sprites():
    s = [spr(ui.backdrop(), 0, 0, 1, 0), spr(panel(296, 206), 0, 0, 2, 0)]
    for f in range(4):
        s.append(spr(card_face(f), 0, 0, 3, f))
        s.append(spr(tile(f), 0, 0, 10, f))
        s.append(spr(icon(f), 0, 0, 20, f))
    s.append(spr(outline(90, 30, (255, 236, 150)), 0, 0, 11, 0))
    s.append(spr(outline(86, 26, ui.ORANGE, t=2), 0, 0, 12, 0))
    s.append(spr(outline(86, 26, EDGE, dashed=True), 0, 0, 13, 0))
    for r in range(4):
        s.append(spr(pips(r + 1), 0, 0, 21, r))
    s.append(spr(bar(150, 4, (30, 36, 60)), 0, 0, 30, 0))
    fill = ui.vgrad(150, 4, (255, 230, 120), (255, 120, 30)).convert("RGBA")
    s.append(spr(fill, 0, 0, 30, 1))
    s.append(spr(echo_ball(), 0, 0, 40, 0))
    s.append(spr(echo_bolt(), 0, 0, 40, 1))
    s.append(spr(spark(), 0, 0, 41, 0))
    for k in range(3):
        s.append(spr(squad_pip(k), 0, 0, 50, k))
    s.append(spr(panel(160, 28), 0, 0, 60, 0))
    s.append(spr(panel(110, 98, (255, 236, 150)), 0, 0, 61, 0))
    return s


def tile_body(w=86, h=26):
    c = canvas(w, h)
    d = ImageDraw.Draw(c)
    poly(d, [(1, 1), (w - 1, 1), (w - 1, h - 1), (1, h - 1)], (*NAVY, 235))
    poly(d, [(2, 2), (24, 2), (24, h - 2), (2, h - 2)], (*PANEL, 255))   # art window behind the thumbnail
    return done(c)


def write(path, card_ids=()):
    """legends.sff (drawn placeholders + the art kit when present) and legends.air next to it.
    Returns (sprite count, file KB, kit used, kit decoded 8-bit bytes)."""
    import legends_kit
    s = sprites()
    s.append(spr(tile_body(), 0, 0, 14, 0))
    kit = legends_kit.kit_dir()
    kit_pixels = 0
    if kit:
        extra, kit_pixels = legends_kit.sprites(kit, list(card_ids), spr)
        s += extra
    ui.sff1.write(path, s)
    with open(os.path.splitext(path)[0] + ".air", "w", encoding="latin-1", newline="\n") as f:
        f.write(legends_kit.air_text(kit is not None))
    return len(s), os.path.getsize(path) // 1024, kit, kit_pixels
