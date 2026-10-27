# Jump Force Vita UI (`motif: jfv`)

A restyle of the stock Dolmexica motif, drawn entirely by `tools/make_ui.py` (no third-party
art, no TBM files). It keeps every element the stock motif already has. Only the art and the
layout change.

```bash
.venv/Scripts/python.exe tools/build_assets.py --motif jfv      # or: build, then tools/make_ui.py
.venv/Scripts/python.exe tools/make_ui.py --preview             # + sprite sheets in ui-work/ (git-ignored)
```

## Design references

| Taken from | Used for |
|---|---|
| Street Fighter 6 | flat slanted health bars; super meter at the bottom corners, split into 3 levels, with a level chip |
| Tekken 8 | timer in a badge between the bars; round pips beside it; red recoverable-damage trail (the lifebar `mid` layer) |
| Guilty Gear Strive | one bold angular typeface on every screen, outlined for contrast over busy stages |
| Dragon Ball FighterZ | select screen: large portraits on team-colour slabs above a compact grid |
| Jump Force | colours: navy panels, orange/yellow accents; P1 cyan, P2 red |

## What's drawn

- **Font:** `tools/ui/glyphs.py` is an angular italic stroke font built from line segments.
  The build writes five MUGEN v1 `.fnt` files (`font/jfv_*.fnt`): small, medium, medium orange,
  numbers and large gradient, plus a timer font with an infinity glyph for untimed rounds.
- **Title:** gradient backdrop with a diagonal light band, additive speed lines, the
  "JUMP FORCE / VITA" logo and a slanted menu panel. The engine still draws its own credit bar
  (`titlescreen.cpp:345`).
- **Select:** header bar; P1/P2 slabs and name plates; a grid panel sized from the grid
  `build_assets.py` lays out for the roster; chamfered cells; 1P/2P tab cursors.
- **VS:** diagonal cyan/red split with a white seam, framed portraits, name plates, and a "VS"
  logo that slams in and flashes.
- **Fight:**
  - health bars: frame, dark back layer, red damage trail and gradient fill
  - power bars with a level chip
  - portrait frames, names under the bars, a hexagonal timer badge and win pips
  - "x HITS" combo counter
  - "ROUND n", "FIGHT!" and "K.O." (same animation timings as stock), plus DOUBLE K.O.,
    TIME OVER, "x WINS" and DRAW

Sprites are SFF v1 / 8-bit PCX (`tools/ui/sff1.py`). Both files total about 200 KB, so they
need almost no texture memory on the Vita. The old darkened bar backgrounds were subtractive
(`trans = S`); they are now opaque.

## Verified (2026-10-27)

- Windows build, demo mode: title, VS screen, HUD, timer, combo, ROUND / FIGHT seen in screenshots.
- Vita3K, patched engine (`tools/engine/build_vita.sh`), autotest fights Sasuke vs KFM and
  Madara vs Goenitz:
  - HUD, timer badge and countdown, combo, power levels and "SASUKE WINS" all render correctly.
- Windows build, driven with `tools/drive_game.py`: title menu, select screen (cursor moves, 1P tab,
  name plate, portrait) and VS screen seen in screenshots; fixed menu clipping and the name/cursor overlap.
- **Not yet seen running:** title, select and VS on the Vita renderer (the Vita3K autotest
  skips the menus), the 2P side of the select screen, and a physical Vita.
