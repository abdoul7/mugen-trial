# T4 — TBM motif spike: findings and call

Dated 2026-10-26. Windows build only, nothing run on a Vita. Built with
`build_assets.py --skip-missing --motif tbm` (the 8 demo/stock characters; the AK1 ones
weren't available locally). Screenshots are in `reports/soak/tbm_run1/` and
`reports/soak/stock_run1/` locally; they show game art, so they aren't committed.

## What the port looks like today

| Screen | Stock motif | TBM port (`port_motif.py`) |
|---|---|---|
| Title | renders, menu legible | **black**: nothing but the bottom text line, for the full 15 s it was held |
| Select | not reachable from demo mode (the engine skips it in both motifs) | — |
| VS | both portraits, names, background | one portrait at top-left, oversized name text overlapping it, no background |
| Fight HUD | lifebars, timer, names, faces | lifebar area garbled (white blobs), no bars/faces visible |

## Cause 1: Dolmexica only reads `[Files] spr` (blocking, fixable)

Every motif screen loads its sprites from `[Files] spr` and ignores the per-screen
`[XxxBGdef] spr`:
`titlescreen.cpp:395-408`, `characterselectscreen.cpp:992-1003`, `versusscreen.cpp:211-218`,
`victoryquotescreen.cpp:220-225`, `optionsscreen.cpp:858-868`.
TBM keeps each screen's art in its own file (`00/title.sff`, `00/select.sff`,
`00/Versus.sff`, `00/Victory.sff`, `00/Option.sff`) with only 79 sprites in `system.sff`,
so the backgrounds look up sprites that aren't loaded and draw nothing. Fixing this means
merging those SFFs into one `system.sff` and renumbering any colliding groups in the `.def`.

## Cause 2: memory (the deciding factor)

On Vita, prism turns every PNG sprite that has its own palette into a **32-bit texture**
(`prism/mugenspritefilereader.cpp:279-285` → `loadTextureFromPalettedImageData1bppTo32ARGB`;
only Dreamcast gets 16-bit). Textures go to CDRAM (128 MB) first and spill into main RAM
(`prism/vita/texture_vita.cpp:250`). TBM is 1280×720 art in PNG8 with one palette per sprite.
Windows hides this: the textures live in GPU memory, which the soak's RSS figure doesn't count.

`tools/motif_cost.py` estimates the cost from the `.def` files and SFF headers.
"Referenced" means only sprites the screen's `.def` sections actually use; "scaled" means
downscaled to the size shown on a 960×544 screen (the best a resize step could do).

| Screen | Whole SFF | Referenced, full size | Referenced, scaled |
|---|---|---|---|
| Title (394-frame animated layers) | 82 MB | 78 MB | **45 MB** |
| Select | 22 MB | 18 MB | 10 MB |
| VS | 109 MB | 109 MB | **62 MB** |
| Victory | 18 MB | 18 MB | 10 MB |
| Fight HUD (1v1 sections only) | 420 MB | 419 MB | **135 MB** |

The fight HUD alone is ~135 MB at best: more than all of CDRAM, before the two characters
and the stage are loaded. Most of it is the full-screen round / KO animations
(groups 500 + 600 ≈ 343 MB at full size). The stock HUD is a 70 KB SFF v1 of 8-bit sprites.

## The call

**Full-fidelity TBM is not viable on the Vita.** Keep the **stock motif** for M1, which
works today.

If the TBM look is still wanted afterwards, the only realistic route is a **TBM-lite** port:

1. merge the per-screen SFFs into `system.sff` (fixes the black title / broken VS);
2. keep static frames only: one frame of each animated title/VS layer, no full-screen
   round/KO animations (use stock ones), TBM lifebars/faces only;
3. downscale the art to its displayed size in the build;
4. possibly re-quantise to one shared palette (palette-0 PNG8 sprites stay 8-bit
   paletted, 4× cheaper; untested whether the motif path takes that branch).

That's a new SFF rewriting tool plus re-validation on hardware. Estimated at a day or more.
Owner decision whether it's worth it before M1 is signed off.

## Tooling changes made during the spike

- `build_assets.py --skip-missing`: leaves out characters whose source folder is absent
  (lets anyone without the AK1 archives build), logging each one.
- `build_assets.py --motif tbm`: tries a motif without editing `roster.json`.
- `soak_test.py` now patches `[Demo Mode]` in the **active** motif's `system.def`
  (from `mugen.cfg`); it used to always patch `data/system.def`, which the TBM motif doesn't
  read. New `--wait/--first/--every` options hold the title screen and take denser screenshots.
- `tools/motif_cost.py`: the memory estimate above.
