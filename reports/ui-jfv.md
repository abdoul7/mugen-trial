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

Sprites are SFF v1 / 8-bit PCX (`tools/ui/sff1.py`).

### 640x480 space (sharper on the Vita)

The engine's logical screen is 320x240 (`main.cpp:71`), and the Vita shows it about 2.27x
(544/240). Art made in 320 space is therefore drawn about 2.27x on the Vita, which looks
blocky. The motif is now drawn at 2x (`K` in `make_ui.py`) and runs in 640x480 space, so
UI art is drawn at about 1.13x and text and edges look sharp:

- `system.def` has `localcoord = 640,480`.
- The fight HUD is in `data/480p/fight.def`, the only way to get 640 space for the fight
  (`fightui.cpp:524`). The same file goes in `data/jfv/fight.def`, because fight fonts load
  from the motif's own fight.def (`config.cpp:383`).
- Hit sparks are drawn in the HUD's space, so `data/480p` gets a 2x copy of the stock
  fightfx. Stock fight sprites we don't redraw are also 2x (nearest-neighbour).
- Layouts are still written in 320 units. `to_k_space()` doubles every coordinate key and
  every animation frame offset.
- Engine quirk: some texts ignore the coordinate space and draw fonts 1:1 on the 320 screen:
  - select-screen title, names and stage text
  - fight timer, round/KO/win text, combo and win counter

  Those use 1x fonts (`jfv_*1.fnt`). Select `title.offset` is read untransformed, so it stays
  in 320 units.

Sprite files total about 760 KB, still small next to one character's sprites. Before and
after screenshots of the HUD were compared on the Windows build. The old darkened bar backgrounds were subtractive
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
