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

Sprite files total about 790 KB, still small next to one character's sprites. Before and
after screenshots of the HUD were compared on the Windows build. The old darkened bar
backgrounds were subtractive (`trans = S`); they are now opaque.

## Main menu redesign (owner brief `docs/ui-claude-prompt.md`)

### Research (bounded; pages and stills, no video footage was watched)

| Source | What it says (observation) | What we took (adaptation) |
|---|---|---|
| [Tekken 8 patch 1.08](https://en.bandainamcoent.eu/tekken/news/tekken-8-patch-108) | the main menu can display a chosen character | not done yet: a featured-fighter panel needs portraits copied into system.sff at build time (follow-up) |
| [SF6 manual, Fighting Ground](https://game.capcom.com/manual/SF6/en/switch2/page/6/1) | the traditional modes are grouped under one heading, described in one line: "Play through modes such as arcade, training..." | one stable list of the real modes, each with a one-line description of what it actually does |
| [PlayStation Blog, SF6 showcase](https://blog.playstation.com/2023/04/20/street-fighter-6-showcase-new-gameplay-details-future-fighters-revealed-and-demo-launched/) | Fighting Ground holds Arcade, Versus, Team Battle, Extreme Battle; online lives elsewhere | no online, store or team entries: Dolmexica has none on the Vita |
| Strive news post-2851 | could not be read: guiltygear.com returned 403 (CloudFront) and was not retried | the 1.29 notes found by search describe a reworked main menu and one-button Quick Access; not adopted |

Proposed, not measured from footage: focus moves settle in about 100-150 ms, scene changes keep
the engine's 10-tick fades, idle loops run every few seconds.

### What the engine does now (patch 0009, `tools/engine/patches/0009-*.patch`)

All keys are optional. A stock engine ignores them and still works, with the old box cursor.

| Key | Section | Effect |
|---|---|---|
| (none) | title | the blue footer bar, "Dolmexica Infinite 1.8" and the date/presenter line are gone (`loadCredits` removed); the engine is credited in `CREDITS.md` |
| `menu.itemdesc.<item>` | Title Info | description of each mode |
| `menu.focus.pos/.font/.offset` | Title Info | the selected mode's name, which slides in by `.offset` on every change |
| `menu.desc.pos/.font/.width` | Title Info | the selected mode's description, wrapped at `.width` |
| `menu.cursor.anim`, `menu.cursor.offset` | Title Info | animated cursor (replaces the box cursor); it restarts on every change (flash, then hold) |
| `menu.ease` | Title Info | share of the remaining distance covered per frame (0.35: about 90% in 6 frames, 100 ms) |
| `menu.item.active.offset` | Title Info | the selected item slides out by this; the previous one slides back |
| `portrait.fit = 1` | Select Info | each cell portrait is scaled down to fit its cell and centred |
| `p1/p2.face.window = w,h` | Select Info | the big portrait is scaled down to fit and bottom-aligned in that box |
| `cursor.ease` | Select Info | the cell cursor glides to its cell |

Easing always heads for the latest target, so held or rapid input and reversals never queue
motion. The selection itself changes on the frame of the press.

### Layout and art (`tools/make_ui.py`)

- Small logo at the top left. The mode list on the left shows every working mode (8): the
  selected one sits on an orange plate with a notch, slides right and turns white, so
  selection doesn't depend on colour alone.
- A focus panel on the right shows "MODE", the mode name and what it does. A hint bar
  ("MOVE", "SELECT", with drawn Vita button icons) replaces the engine footer.
- Background: navy gradient, slow additive speed lines, embers drifting up, and a light
  sweep about every 6 s (BG anim 1310). The busy layers sit behind the panels, away from text.
- Options screen: jfv backdrop; its text uses a 1x font (it draws font 2 unscaled,
  `optionsscreen.cpp:846`).
- Credits mode: name/author/date in the P2 slab, with a 1x font.
- Italic fonts are kerned: each glyph box included its slant, which spaced letters too far apart.

### Modes: what was checked

| Item | Status |
|---|---|
| ARCADE | selected and played to the fight in Vita3K |
| FREE PLAY | description checked in source: P1 human vs CPU (`gamelogic.cpp:776`) |
| SURVIVAL | source: one round per fight, life carried over, CPU opponent (`gamelogic.cpp:818`) |
| TRAINING | Vita3K select screen and back; source: infinite timer |
| WATCH | source: CPU vs CPU |
| OPTIONS | opened and left in Vita3K; leaving it saves `ux0:data/JFVT00001/options.bin` (patch 0005) |
| CREDITS | opened and left in Vita3K |
| EXIT | source only (`abortScreenHandling`) |
| VS MODE | **removed from the menu**: on the Vita, player 2 gets no input at all (prism `vita/input_vita.cpp`, every `evaluateVitaButton*` returns 0 for `i != 0`), so player 2 can never pick |
| NETPLAY | not listed: Windows-only in the engine |

### Portraits (all 27 fighters)

Measured from each character's SFF (`ui-work/portrait_audit.py`, local). Most are 25x25 and 120x140.
Exceptions:
- android_18_1 small portrait: 21x54, axis (10,52)
- tenshinhan_saga_cell small portrait: 45x33
- metal_bat small portrait: 30x29
- android_21_1_1 small portrait: 25x28
- janemba: 22x22 and 107x124
- kawashiki big portrait: 46x61

`portrait.fit` and `face.window` bound all of them. In Vita3K every cell showed its icon
inside the cell.

### Texture cost (estimate from pixel counts; Vita3K does not report real use)

| Screen | 8-bit (patch 0001 paletted path) | 32-bit upper bound |
|---|---|---|
| whole system.sff (title/select/VS load it once) | about 2.2 MB | about 9 MB |
| fight HUD (fight.sff, incl. stock sprites at 2x) | 0.3 MB | 1.2 MB |
| hit sparks (fightfx at 2x) | 2.0 MB | 8.1 MB (stock 1x: 2.0 MB) |

The 2x hit sparks are the one real cost. If the Vita runs short in fights, keep fightfx at 1x and
halve the HUD instead (`[FightFx] scale = 2` with `.scale = .5` on each element, as
`port_motif.py` does). Not measured on hardware.

## Verified (2026-10-27)

- Windows build, demo mode: title, VS screen, HUD, timer, combo, ROUND / FIGHT seen in screenshots.
- Vita3K, patched engine (`tools/engine/build_vita.sh`), autotest fights Sasuke vs KFM and
  Madara vs Goenitz:
  - HUD, timer badge and countdown, combo, power levels and "SASUKE WINS" all render correctly.
- Windows build, driven with `tools/drive_game.py`: title menu, select screen (cursor moves, 1P tab,
  name plate, portrait) and VS screen seen in screenshots; fixed menu clipping and the name/cursor overlap.
- Vita3K, patched engine with 0009, driven with keystrokes (`ui-work/v3k_drive.py`, local):
  - title, focus panel and descriptions; no footer
  - moving through all 8 items, including a fast reversal
  - Arcade and Training select screens: cursor glide, fitted portraits
  - Back (Circle) from select to the title; the title remembers the last item
  - Options and Credits opened and left
  - Arcade select, VS and fight HUD
  - a 20 s recording (`ui-work/jfv-menu-vita3k.mp4`, local, not committed: shows game art)
- **Not checked:**
  - a physical Vita: frame rate, real texture memory, legibility at 5 inches
  - the 2P side of the select screen (no 2-player mode on the Vita)
  - stage select (no mode used here shows it)
  - Free Play, Survival and Watch played through
  - Arcade's continue and ending screens with this motif
  - frame rate: Vita3K speed says nothing about the hardware
