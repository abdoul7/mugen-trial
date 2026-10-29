# UI continuation — 2026-10-27

## Current state (Claude, branch `motif/jfv-ui`, PR abdoul7/mugen-trial#6)

The active motif is **jfv**, built by `tools/make_ui.py` on top of `roster/jf-on-vita`
(27 fighters + randomselect). Build it with `python tools/build_assets.py --motif jfv`, or
run `tools/make_ui.py` after a build. Details, research and verification are in
`reports/ui-jfv.md`. The owner's brief is `docs/ui-claude-prompt.md`.

- **Native:** engine patch `tools/engine/patches/0009-jfv-menu-focus-descriptions-portraits.patch`
  (built by `tools/engine/build_vita.sh`). It:
  - removes the footer
  - adds focus name, descriptions, animated cursor and eased motion on the title
  - fits cell portraits, bounds big portraits and glides the cursor on the select screen
- **Art space:** the motif is drawn at 2x and runs in 640x480 space (sharper on the 960x544
  screen). Layout stays in 320 units.
- **Menu:** 8 working modes. VS MODE is removed because the Vita build gives player 2 no
  input, and netplay is Windows-only.
- **Testing:** native features only show on the Vita engine. Test them in Vita3K: install
  `build/engine/DolmexicaInfinite.self` as `ux0/app/JFVT00001/eboot.bin` and copy `data/jfv`,
  `data/480p`, `font/jfv_*`. The Windows exe is the stock prebuilt engine: it shows the layout
  with the old box cursor and footer. Building Windows from source needs FMOD and a dozen
  SDKs that aren't installed here.
- **Scripted input in Vita3K:** the first keypress after boot is swallowed, and the title
  remembers its last item. Start every script from a known item. Leaving Options writes
  `ux0:data/JFVT00001/options.bin`; a script that wanders into Options changes the saved
  settings.

Next, in order:
1. Owner check on a physical Vita: frame rate, legibility, hit-spark texture memory.
2. Featured-fighter panel (Tekken-style anchor): copy one roster big portrait into
   system.sff at build time.
3. Select screen: hint bar, stage select styling (Free Play / Watch).
4. Two-pad input on the Vita (PS TV), then restore VS MODE.

The notes below are Codex's handoff from `motif/ui-overhaul` (kept for history). Resolved since:
- the footer
- select-portrait overflow (now `portrait.fit` / `face.window`)
- full-roster testing (27 fighters, Vita3K)
- the mode-label overlap does not occur in jfv

---

## (Codex) Owner's intent

Make a new-release-quality native fighting-game menu while keeping the actual
game's nostalgic arcade/anime sprite aesthetic. Modernize hierarchy, focus,
navigation, animated backgrounds and selection transitions. Art direction must
also fit the characters, stages and effects; it cannot be a separate polished
illustration pasted onto inconsistent gameplay art.

Latest requested deliverable: a researched implementation prompt for Claude.
See `docs/ui-claude-prompt.md`. Owner also explicitly requested this handoff in
AGENTS.md and that source work be pushed to the repo.

Additional explicit request: remove the entire bottom blue engine footer,
including its background, left engine name and right date/presenter line. This
is part of Claude's menu task. It is not implemented in this branch and requires
a clean native engine source change, not a covering image.

## Current checkout and branches

Local checkout:
`C:\Users\abdou\Documents\Codex\2026-10-27\jump-force-vita-onboarding-a-m\work\mugen-trial`

Branch: `motif/ui-overhaul`, based on main `8c87d82`.
Separate remote branch `origin/motif/tbm-spike` contains another agent's T4 report
and tools. Read its `reports/motif-t4.md` before attempting the full TBM motif;
it documents missing backgrounds and excessive decoded texture memory. It has
not been cherry-picked into this branch.

## Assets and builds on this PC

- Venv is installed with py7zr, imageio-ffmpeg, pillow and psutil.
- Engine: `engine/Dolmexica Infinite 1.8`.
- Demo: `source/demo/TBM_Last_Beta(Screenpack)`.
- Engine reference source: `source/dolmexica-src/repo`, and `.../prism`.
- AK1 original archives: `C:\Users\abdou\Downloads\ak1 jump force characters handoff`.
  All 14 archives used by the roster matched the byte size and SHA-256 in
  `reports/jf-archives.csv`; they were extracted into ignored `source/jf/<id>/`.
- `build/game` was assembled using the unchanged `tools/build_assets.py`.
  It contains 22 character directories and 22 fighters + randomselect in
  `assets/data/select.def`. Inspect current `mugen.cfg` before applying a motif.
- `build/arcade-preview` is an earlier isolated 8-fighter fixture. It is NOT a
  substitute for the full build, even though its executable is playable.
- `build/rift-smoke` is an obsolete stock-KFM-only experiment.
- `tools/fetch_sources.py` successfully fetched the demo but the standalone TBM
  screenpack fetch failed because its MediaFire direct-link regex found no link.
  The demo was extracted independently. Do not report the standalone pack fetched.

All paths above except source tools/docs are local/ignored, not repo assets.

## Source work preserved on this branch

- `tools/arcade_motif.py`: experimental native 320x240 motif with original
  rasterized logo, menu backgrounds, real installed portrait strips, select,
  versus, victory, game-over and custom HUD SFF generation. CLI:
  `.venv/Scripts/python.exe tools/arcade_motif.py build/game/assets`.
  It is not integrated into `build_assets.py`; integration lane owns that file.
  `--preview` creates the smaller fixture only when its output does not exist.
  Reapplying the motif reads stock `data/system.def` and `data/fight.def`.
- `tools/verify_arcade.py`: Windows-only process/window capture smoke harness for
  **build/arcade-preview**, not build/game. `--interactive --seconds 180` holds
  the menu for manual navigation. Noninteractive mode selects one fighter through
  the existing demo mechanism. Restores temporary config in `finally`.
- `tools/normalize_portraits.py`: newly written, experimental SFF v1/v2 portrait
  normalizer. Targets 9000,0 -> 25x25 and 9000,1 -> 120x140; attempts to preserve
  other sprite payloads/palettes and use nearest-neighbour contain. It is not
  imported or called by the motif builder. It has not been exercised against the
  real roster. Review linked-sprite/palette handling and add meaningful regression
  tests before enabling it. Do not patch source archives or source/jf originals.

## Observed bugs / next concrete actions

1. **Select portrait overflow (owner screenshot):** KFM720 has a 100x100 small
   portrait and a 480x560 big portrait, while the UI assumes 25x25 / 120x140.
   `characterselectscreen.cpp:579-583` applies one global `portrait.scale` without
   clipping per cell. Sizing the grid correctly does not bound the actual images.
   Audit all 22 portrait dimensions, axes and formats. Normalize only generated
   build copies, preserve combat payloads, validate palettes and fight behavior.
2. **Overlapping mode label:** `title.font = -1` in the motif does not hide the
   mode name. `characterselectscreen.cpp:894-898` creates a fallback text element.
   Give the mode label a deliberate separate position/font, or implement a proper
   source-level visibility control. Do not just hide it beneath other art.
3. **Full roster:** rebuild/apply/test against `build/game` with the 22 actual
   fighters. The previous screenshot with 8 fighters was the smaller fixture,
   not evidence that the main roster was removed.
4. Test both selector states: Arcade/Training have one human selector, Versus has
   two. An empty P2 preview in Arcade may be the engine's intended state; design
   around it rather than promising a fake opponent.
5. The latest screenshot supplied by the owner shows a different `Jump Force
   Vita` menu running at 960x544, with a large logo, flat vertical list, orange
   speed lines and engine footer. Do not assume this local experimental tool is
   the generator of that exact screenshot. First identify the active checkout,
   executable and `mugen.cfg`/motif path that produced it.
6. Modern focus interpolation, contextual descriptions and state-driven preview
   changes may need native C++ changes. Background AIR loops alone do not create
   interactive focus transitions. Inspect support before adding MUGEN/Ikemen keys
   the engine silently ignores. Never patch the prebuilt SELF/VELF.

## Verification actually performed

- Earlier KFM-only UI process survived 70 s; screenshots showed title, VS and fight.
  This was a discarded visual direction and does not validate this new motif.
- Arcade-preview interactive process survived 180 s, peak working set 358 MB,
  45 window captures, no detected red error screen. See local
  `reports/arcade-smoke/interactive/result.csv`. The owner's later screenshot
  demonstrates visual bugs, so this is **process survival only**, not UI acceptance.
- Grid geometry was checked in Python for 1..60 slots; that check did not inspect
  portrait dimensions and therefore missed the overflow.
- All 14 roster archive hashes matched. `build/game/assets/chars` has 22 folders.
- No successful full-roster UI navigation pass, new-motif fight soak, hardware
  installation, Vita performance measurement, or final visual approval yet.

## Engine details worth retaining

- Native screen is 320x240; target display is 960x544 with 4:3-safe content.
- Title menu colors/focus cursor are partly native engine behavior; a DEF-only
  redesign has limits. The desktop title/footer credits are hardcoded in
  `titlescreen.cpp:345-352`, not text baked into the motif images.
- Windows key config uses `[P1 Keys Dolmexica]` and the engine's key enum, not the
  legacy `[P1 Keys]` scan codes. Inspect `config.cpp:196-223` and
  `prism/windows/input_win.cpp` before diagnosing navigation from the wrong map.
- Computer Use was once stopped by physical Escape. Respect a fresh stop and do
  not claim any navigation action succeeded without inspecting the resulting screen.
- Vita: 1v1, no subtractive blending, no MP3, fixed font colors, 96 MB current heap.
- Full TBM HUD animation is much too large. Prefer small reusable sprites, modest
  layer counts and inexpensive procedural/native motion.

## Design decisions that are NOT approved

The owner rejected: ivory editorial poster style; giant anime/Goku-like mascot;
arbitrary city skyline; simplistic block-font mockups resembling a browser game.
All previous Higgsfield boards are rejected references, not an approved asset kit.
`Jump Rift` was an agent-created working name, not accepted branding. Retain
`Jump Force Vita` for the next pass unless directed otherwise.

The owner requested Discord milestone updates and provided a webhook in chat.
Do not put that secret into AGENTS.md, source files, reports or git. No secret has
been written into this handoff. Prefer reviewing the existing chat authorization
and secure access rather than copying it into a public repository.

## Finishing and delivery

Keep source and text-only reports on one UI branch; no assets/screenshots/VPKs in
git. Push the branch and open a PR with explicit tested/untested status. A draft
handoff PR is appropriate while these bugs remain. Do not merge or claim the
whole visual overhaul is complete merely because a process remained running.
