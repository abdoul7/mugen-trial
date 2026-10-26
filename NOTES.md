# Build notes — what was found and decided

Dated 2026-10-27. Source-code references are to Dolmexica `a6d63e9` (cloned to
`source/dolmexica-src/repo`) and prism (`source/dolmexica-src/prism`).

## Pipeline facts (verified)

- **The Vita kit needs no compiler.** `vita/make_vita.bat` only runs `vita-mksfoex` and
  `vita-pack-vpk` around the prebuilt `common/DolmexicaInfinite.self` plus `../assets`.
  `tools/make_vpk.py` does the same with our TitleID and LiveArea art.
- **No command line, no log.** `main.cpp:59-66` ignores argv and sets log level NONE in
  release builds, so the Windows exe can't be told to start a fight.
- **Unattended testing works anyway:** the title screen's demo mode (`titlescreen.cpp:283`,
  `[Demo Mode]` in system.def) starts a CPU-vs-CPU exhibit fight after `title.waittime`
  idle ticks. `tools/soak_test.py` writes a one-character roster, shortens the wait, turns
  on lifebars/BGM and watches the process. Screenshots use `PrintWindow` on the game window
  only, so nothing else on the desktop is captured.

## Asset fixes the build applies (and why)

| Problem | Where | Fix |
|---|---|---|
| `localcoord = 450,370` on 7 characters | TBM's trick to shrink 320×240 chars under a 720p motif | removed → native 320×240 size (verified in screenshots) |
| `localcoord = 1780,1220` on Kung Fu Man 720 | same trick on a hi-res char | set to its real `1280,720` |
| `localcoord = 400` (single value) on Janemba | malformed | removed |
| `st9 = goenitz_um_common1.cns`, `pal = paletas\…` | case/backslash mismatch | rewritten to exact on-disk case, forward slashes |
| select.def `Stages\streetfighter\…`, `pupa\pupa.def` | case mismatch vs folders | every char/stage renamed to a lowercase id with no spaces |
| Janemba `ending.storyboard = ..\data\final.def` | file doesn't exist; real one plays MP3 | blanked |
| Kaede folder carries a second character (`kaede.*`, `kaede2.def`) | dead weight | dropped |
| non-ASCII readme filenames | engine author: unparseable names are a top crash cause | dropped |
| all stage BGM is MP3 | Vita build can't play MP3 | converted to OGG q3 |
| character `.snd` up to 17 MB | 44.1 kHz stereo voice clips | `shrink_snd.py`: clips above target → mono 22 kHz (Bender 16 kHz) |

## Memory evidence (Windows working set during a 75 s CPU fight, before audio shrink)

Windows numbers are not the Vita heap (the PC build keeps decoded textures), but they rank
the risk. See `reports/soak/results.csv` for the latest run.

## Motif port (T4)

- Title/select/VS screens scale motif coordinates **by `localcoord.x` only**
  (`titlescreen.cpp:249`, `characterselectscreen.cpp:1000`). Declaring the 1280×720 pack as
  `960,720` keeps the art at the same scale on a 4:3 frame; absolute screen positions shift
  x−160 (centre crop). Background `start` values are centre-relative and need no change.
- The fight HUD has only two coordinate spaces, 320 and 640 (`fightui.cpp:524-548`);
  `data/480p/fight.def` selects 640. The 1280-wide `Fight.def` is halved into it.
- Dolmexica multiplies HUD sprites by `[FightFx] scale` (`fightui.cpp:642`) — unlike
  M.U.G.E.N, where it only scales hit sparks. TBM sets 2; we set 1 and halve every HUD
  element through its own `.scale` instead.
- Bitmap (FNT v2 + SFF) and TrueType fonts are both supported (`prism/mugentexthandler.cpp:155`).
- The pack's live select values are a 550×49 mosaic of 26 px cells (everything after `;`
  is a comment). We use the author's alternate 53 px cells in a 10-column grid.
