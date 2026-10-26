# Jump Force Vita — agent instructions

You are helping build a **custom M.U.G.E.N fighting game that runs natively on a PS Vita**
as an installable `.vpk`. Roster: the Jump Force lineup. Visual style: borrowed from the
PC pack *"The Best M.U.G.E.N 1.1 (Beta 2)"* by evil_dark_lxs. This folder is the complete
handoff: read `BRIEF.md`, then `FACTS.md`, then work `TASKS.md` in order.

## Hard rules (do not re-litigate these)

1. **Engine = Dolmexica Infinite** (MIT, `github.com/CaptainDreamcast/DolmexicaInfinite`).
   It is the only M.U.G.E.N interpreter with a native Vita build and a `.vpk` kit.
2. **Do NOT attempt a port of Ikemen GO.** It is written in Go; Go has no Vita/newlib
   target. This was investigated and rejected — see `FACTS.md`. (A classic C++ Ikemen port
   is a separate, months-long "maybe", explicitly out of scope here.)
3. **1v1 only.** Dolmexica removed teams, tag, simul, and all team triggers engine-wide.
   Jump Force's 3v3 cannot be reproduced. Do not design around teams.
4. **Target 960×544, 4:3-safe layout.** Nothing above 4:3: hi-res stages get clamped and
   720p characters are the top crash risk. The source motif is 1280×720 and must be re-laid-out.
5. **No MP3.** Vita build plays OGG. Convert all BGM.
6. **No font banks.** Dolmexica supports fixed font colours 0–8 only.
7. **`RemapPal` only with `source = 1,1`.** No subtractive blending on Vita (`trans = sub`).
8. **TitleID must be exactly 9 characters** or the install fails with `0xF0030000`.
9. **Never patch the shipped `.velf`.** Rebuild from source instead — a patched SELF no
   longer validates. The memory ceiling lives in `main.cpp` (`_newlib_heap_size_user`).

## Do not

- Do not download the full 47.2 GB TBM pack. The style assets are published separately
  (see `MANIFEST.txt`); the demo build is enough character quarry.
- Do not rip assets out of the commercial *Jump Force* game. Use community M.U.G.E.N
  characters (mugenarchive.com, andersonkenya1.net) — that is what the existing
  Jump Force MUGEN builds do.
- Do not install anything on a physical Vita without the user's explicit go-ahead.
- Do not redistribute the TBM screenpack files; they are for local personal use.

## Layout of this folder

```
CLAUDE.md                      this file
README.md                      human-facing summary
BRIEF.md                       intent, goals, non-goals, decisions, approach
FACTS.md                       verified numbers, sources, measurements (with evidence)
TASKS.md                       ordered work items + acceptance criteria
MANIFEST.txt                   where the big archive files live, and their URLs
roster/jumpforce-roster.md     the 57-character roster, grouped by series
inventory/style-anatomy.csv    187 files of the TBM motif with sizes and roles
inventory/demo-roster-triage.csv   per-character Vita-risk verdicts (measured)
inventory/demo-roster-select.def   paste-ready select.def from the same run
inventory/demo-char-folders.txt    franchise → character folder mapping
extracts/dolmexica-vita-heap.txt   the compiled memory ceiling (source excerpt)
extracts/dolmexica-vita-cmake.txt  Vita build config (libraries, vpk packaging)
extracts/tbm-system.def-head.txt   the motif's [Info]/[Files] block
tools/scan_mugen_build.py      character triage tool — run this on any new roster
```

## Working method the user expects

- Step-by-step, plain language: explain what each file and tool does, in build order.
- Cite the exact file and line when a finding comes from source.
- Verify before claiming: a `.vpk` is "done" only after it installs and a fight runs on
  real hardware; a character is "compatible" only after it survives a test fight.
- Keep the Windows build of Dolmexica in the loop: the same `assets/` tree runs on PC,
  so test there first (30 seconds) instead of reinstalling on the Vita (minutes).

## Definition of done for the first milestone (M1)

A single `.vpk`, installed from VitaShell, that boots to a title screen, lets you pick
from at least 8 characters with visible portraits, loads a stage, and plays a 1v1 round
at a playable frame rate without crashing — using the source pack's own characters.
Style fidelity comes later; a working pipeline comes first.
