# Jump Force Vita — handoff package

Everything from the MUGEN-on-Vita research session, packaged so another agent (or a person)
can pick the work up cold. Hand the whole folder over as-is.

## What this project is

A custom M.U.G.E.N fighting game that runs **natively on a PS Vita** as an installable
`.vpk` — Jump Force roster, visual style borrowed from the PC pack *The Best M.U.G.E.N 1.1
(Beta 2)* by evil_dark_lxs, movesets from community M.U.G.E.N characters.

## Read in this order

| File | Why |
|---|---|
| `CLAUDE.md` | agent-facing rules: engine, hard constraints, what not to do |
| `BRIEF.md` | intent, goals, non-goals, decisions and their reasons, risks, open questions |
| `FACTS.md` | every verified number with its source, plus on-disk measurements |
| `TASKS.md` | the ordered work list, each with acceptance criteria |
| `roster/jumpforce-roster.md` | the 57-character target roster, grouped by series |

Supporting data:

- `inventory/style-anatomy.csv` — all 187 files of the source motif with sizes and roles
- `inventory/demo-roster-triage.csv` / `demo-roster-select.def` — measured per-character
  compatibility verdicts, plus a paste-ready roster file
- `inventory/demo-char-folders.txt` — franchise → character-folder mapping
- `extracts/` — verbatim source excerpts (the engine's memory ceiling, its Vita build config,
  the motif's `system.def` header)
- `tools/scan_mugen_build.py` — the triage tool; run it on any new roster before adopting it
- `MANIFEST.txt` — where the big archives live locally, and their download URLs

## The three findings that shaped the plan

1. **The engine and the art style are separate.** Ikemen's "look" is just its default
   screenpack; the source pack's look is `system.def/sff` + `fight.def/sff` + fonts + music.
   Nobody needs to port an engine to get a look — and the source pack publishes its
   screenpack on its own (97 MB) instead of the 47.2 GB full pack.
2. **The Vita's wall is memory, not disk.** 512 MB RAM + 128 MB VRAM vs a pack whose author
   documents 2.8–3.4 GB of use. But its *characters* are 1–6 MB sprite sheets, so a Jump
   Force–sized roster (57 × ~3 MB ≈ 200–300 MB) is genuinely achievable — the 720p HUD is the
   expensive part, not the fighters.
3. **Only one engine runs natively: Dolmexica Infinite** (MIT, C++, official Vita build +
   `.vpk` kit). Ikemen GO is Go and has no Vita runtime target; the classic C++ Ikemen could
   theoretically be ported but is a months-long project, deliberately out of scope. Dolmexica
   cannot do teams, so Jump Force's 3v3 becomes 1v1.

## Honest limits (do not let anyone discover these later)

- 1v1 only — no tag, no assists, no 3v3.
- 720p motif must be re-laid-out for 960 × 544.
- No font banks; `RemapPal` only `source = 1,1`; no subtractive blending; no MP3.
- The engine's Vita heap is pinned at 96 MB in source; growing it needs a rebuild.
- The full 47.2 GB pack will never run on the console — only cherry-picked characters will.

## Current state

Research complete, artefacts downloaded and measured, triage tool written and validated
against real data (9 of 10 demo characters pass). Nothing has been built or installed yet.
First milestone: **M1** in `TASKS.md` — an installable `.vpk` using the source pack's own
characters, so the pipeline is proven before the Jump Force roster and the rebuilt motif.
