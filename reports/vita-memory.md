# Vita memory model: what each character costs, and why

Dated 2026-10-26. Tool: `tools/vita_mem.py` (full table: `reports/vita-mem.csv`).
Everything here comes from the **Dolmexica 1.8 source** (`source/dolmexica-src`, release commits
`a6d63e9` / `0bf177e`, the same release as the shipped `.self`). **Nothing was measured on a Vita.**

## How the engine spends memory on the Vita

| What | Where it goes | Source |
|---|---|---|
| Sprite textures | 8 MB slabs, CDRAM (128 MB) first, then main RAM. **Not** the 96 MB heap | `prism/vita/texture_vita.cpp:240-260`, `prism/vita/memoryhandler_vita.cpp:43-51` |
| 8-bit sprite using the player's palette | `P8` texture, 1 byte/pixel | `texture_vita.cpp:395` |
| 8-bit sprite with **its own palette** | converted to ARGB, **4 bytes/pixel** | `prism/mugenspritefilereader.cpp:279-285, 732-745` |
| SFF v2 + a `palN` file present | palette index +1 for every sprite → **all** sprites 4 B/px | `mugenspritefilereader.cpp:1199-1207`, `repo/playerdefinition.cpp:212-226` |
| SFF v1 | 1 B/px only while exactly one palette has been seen; after the first sprite with a different palette, every later sprite is 4 B/px | `mugenspritefilereader.cpp:838, 942` |
| Sprite wider/taller than 4096 px | texture creation fails → `abortSystem()` | `texture_vita.cpp:211, 265` |
| Sounds | WAV copies on the heap; 8-bit WAVs are widened to 16-bit (2×) | `prism/mugensoundfilereader.cpp:54`, `prism/vita/soundeffect_vita.cpp:98, 158` |
| Palettes | P1 = `pal1`, P2 = `pal2` | `repo/gamelogic.cpp:788-789` |

Both fighters load their own copy of the sprites, so a mirror match costs double.

## Validation

There's no Vita reading yet. As a cross-check, the predicted texture size tracks the independent
Windows soak peaks (`reports/soak/results.csv`, same prism loader): **Pearson r = 0.88, n = 22**.
Goku Black is 832 MB predicted vs 732 MB peak, Android 21 822 vs 800, KFM 1 vs 168 (engine
baseline). The numbers line up for the heavy characters; the light ones are dominated by the
engine baseline.

## Results (texture MB per fighter, P1)

| Character | SFF | Now | 8-bit fix (engine) | Snd heap |
|---|---|---|---|---|
| goku_black_ssr | v2 | **832** | 209 | 8.5 |
| android_21_1_1 | v2 | **822** | 207 | 8.1 |
| kefla | v2 | **717** | 294 | 12.9 |
| vegito_ssb | v2 | **600** | 151 | 9.5 |
| android_17 | v2 | 453 | 116 | 8.0 |
| android_18_1 | v1 | 446 | 112 | 5.5 |
| baby_vegeta | v2 | 435 | 122 | 6.6 |
| metal_bat | v2 | 373 | 105 | 5.6 |
| tank_top_master | v1 | 323 | 82 | 3.6 |
| bardock_ssj | v1 | 319 | 81 | 8.3 |
| madara_revived | v1 | 313 | 80 | 5.4 |
| tenshinhan_saga_cell | v1 | 204 | 52 | 3.9 |
| sasuke_hebi_white | v1 | 185 | 47 | 4.1 |
| gouken | v1 | 83 | 26 | 3.8 |
| janemba | v1 | 52 | 14 | 5.8 |
| lucario | v1 | 31 | 16 | 3.1 |
| kfm720 | v2 | 22 | 21 | 0.1 |
| garou_hunters | v1 | 17 | 4 | 1.0 |
| bender, goenitz, pupa, kfm | v1 | 1–11 | 1–11 | ≤ 3.7 |

Stages: `janshell` alone is **83 MB** of textures; the rest are 0.6–13 MB.

The Vita has 512 MB RAM + 128 MB CDRAM in total, and an app gets less than that.
**All 13 AK1 characters that were kept are beyond what the hardware can hold, even for one
fighter.** Only the 8 demo/stock characters are plausible today, and Gouken (83 MB, 166 MB
in a mirror match) is borderline. This matches TODO's warning ("expect heavy ones to fail")
but puts numbers on it: the problem is about 10×, not 2×.

The heap side is fine: sounds are 1–13 MB per fighter after `shrink_snd.py`, against a 96 MB heap.

## Why the AK1 characters are so heavy

1. **Every sprite is 4 bytes/pixel.** The v2 characters give each sprite its own palette
   (Goku Black: 63 palettes, 60 distinct; Kefla 127/127; Baby Vegeta 429/429), and the
   v1 ones switch palettes early. The art itself is 8-bit.
2. **A few huge effect sprites.** These characters are 320×240-scale (no `localcoord`), yet
   60–75% of their pixels are in sprites larger than 640×480: super-move cut-ins of
   1920×1080 (Android 21 group 7088), 2187×2181 (Goku Black 1550,11) and 1500×1500 auras
   (Kefla 1080). On a 960×544 screen those are drawn far below their stored resolution.

## What fixes it

| Fix | Saves | Lossless? | Where |
|---|---|---|---|
| **A. P8 texture + per-sprite palette** for 8-bit sprites that have their own palette (GXM supports a palette per texture) | **~4×** on every character | yes | engine (prism `texture_vita.cpp` / `mugenspritefilereader.cpp`): needs the Vita toolchain |
| **B. Downscale oversized sprites** at build time, with a per-sprite scale factor the engine applies when drawing | ~2–4× more on the AK1 characters (the >640×480 sprites) | visually ~yes on 960×544 | SFF rewrite in `build_assets.py` **plus** an engine change to draw them at the original size |
| C. Share sprites between P1 and P2 in a mirror match | 2× in mirrors | yes | engine |
| D. Reorder SFF v1 so main-palette sprites come first | 10–25% (v1 only) | yes | build only |
| E. Quantise each character to one 256-colour palette | ~4× | **no**: Android 21 uses ~9,800 colours, Vegito SSB ~8,000 | build only |

A + B together put Goku Black near 50–60 MB and Bardock near 25–30 MB. That's the
size class of the demo characters, which are believed to fit.

**Recommendation:** go to the engine toolchain next (track B). A, B and C all need it, and
it's also what T6 (heap size) needs. D and E aren't worth doing on their own.

## Not verified

- No Vita measurement. The engine logs free CDRAM/user memory at every slab allocation
  (`texture_vita.cpp:235`), but release builds log nothing (`repo/main.cpp:62-68`). The first
  engine rebuild should be a debug build so these numbers can be checked on hardware.
- Exactly how much CDRAM/RAM an app can get isn't pinned down here.
- The heap cost of parsed `.cns/.cmd/.air` isn't modelled (only the text size, 0.2–1.3 MB).
