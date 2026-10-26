# Tasks

Work in order. Each task lists what to produce and how to know it worked. Do not start a
later task before the earlier one's acceptance criteria are met — the pipeline is being
proven, not built in parallel.

Reference material: `BRIEF.md` (scope), `FACTS.md` (numbers + sources), `inventory/` and
`extracts/` (measured data from the source pack and the engine).

---

## T1 — Get the engine and a known-good baseline

- Download Dolmexica Infinite 1.8 (`captaindreamcast.itch.io/dolmexica-infinite`), extract.
- Run `Dolmexica Infinite for Windows.exe` once to confirm it boots.
- Confirm the extracted tree contains: the Windows engine, `assets/`, `Dolmexica Infinite
  Make-your-own-game kit for Vita.exe`, and `vita/make_vita.bat`.

**Done when:** the stock Windows build plays a KFM vs KFM round, and you can name every
file the Vita kit needs.

---

## T2 — First playable `.vpk` from the source pack's own characters (milestone M1)

- Copy the demo's characters into `assets/chars/<Franchise>/<Char>/` (they are already
  organised by franchise; mapping in `inventory/demo-char-folders.txt`).
- Copy the demo's 11 stages into `assets/stages/`.
- Write `assets/data/select.def` — start from `inventory/demo-roster-select.def`, fix stage
  paths, drop `Shiki_Nanaya` (TEST IT) for v1.
- Test the same `assets/` tree on Windows first; fix every missing-file error there.
- Generate the `.vpk` with the kit: GameName, **TitleID exactly 9 characters**, version.
- Install with VitaShell on the user's Vita and play one round.

**Done when:** a full round is playable on hardware, no crash, audio present, and you can
report the frame rate you observed.

---

## T3 — Audio budget pass

- Measure per-character `.snd` sizes; the demo already shows one character carrying 44 MB.
- Trim or re-encode oversized `.snd` content (keep the moves' key sounds), convert any
  referenced MP3 to OGG.
- Re-run `tools/scan_mugen_build.py` and confirm no character is flagged "heavy audio".

**Done when:** every kept character is under ~6 MB total media, and the same build still
passes T2's acceptance.

---

## T4 — Style spike: three screens at 960×544

- Extract from the screenpack (`MANIFEST.txt`): `Data/system.sff`, `Data/fight.sff`,
  `Data/fightfx.sff`, `Data/00/title.sff|select.sff|versus.sff|victory.sff`, `Font/`.
- Downscale art to 960×544 (or 4:3 frames upscaled — compare both, this art is often crisper
  that way).
- Rewrite `System.def`: `localcoord`, menu positions, and `[Select Info]` to a grid sized for
  8–12 slots (not 550×49). Rewrite `Fight.def` for the new resolution; drop `[Lifebar]`
  features Dolmexica cannot render (full animation/text coverage is incomplete).
- Remove the team-mode menu entries (`teamarcade`, `teamversus`, `teamcoop`).
- Convert the 9 font `.def`s to Dolmexica-safe fixed-colour fonts.
- Package and screenshot **title, character select, and in-fight HUD** on the Vita.

**Done when:** the team has three screenshots to judge, and a written call: motif fidelity is
worth continuing, or fall back to the stock motif (decide by end of T4, not open-endedly).

---

## T5 — Jump Force roster sourcing + triage

- For each of the 57 (`roster/jumpforce-roster.md`), search mugenarchive.com and
  andersonkenya1.net for the closest community character.
- Run `tools/scan_mugen_build.py` on every candidate; keep only LIKELY OK / reviewed TEST IT.
- Record a table: Jump Force name → MUGEN folder → verdict → notes (missing? substitute?).
- Never rip from the commercial Jump Force game; if no community character exists, either
  substitute or leave the slot empty and say so.

**Done when:** the table exists, at least 12 characters are confirmed playable, and every
rejection names the specific constraint that killed it.

---

## T6 — Heap rebuild (only if T2–T5 show crashes on load)

- Edit `main.cpp`: `_newlib_heap_size_user` 96 → **144**, rebuild with VitaSDK
  (317 MB-ish toolchain; Docker image `vitasdk/vitasdk` is the least painful route; no
  Docker/cmake/gcc is currently installed on the user's PC — coordinate before installing).
- Test 144, then 192, then 224; stop at the first value that is stable in a full round.
- Never exceed what the OS will grant: a failed launch means the value is too high.

**Done when:** a build with the raised heap loads the heaviest kept character + stage and
survives three consecutive fights.

---

## T7 — Select screen for the real roster

- Rebuild `[Select Info]` for the final slot count (portraits on, `portraits` can be 0 to
  save load time on big rosters).
- Verify the cursor, preview, and stage preview work with 1P only.
- Confirm the roster file matches the folders on disk (this is the #1 crash cause).

**Done when:** every roster slot is selectable, portraits render, and no slot points at a
missing folder.

---

## T8 — Release packaging

- Final `.vpk` + install notes (TitleID, where assets install, the fast mod loop through
  `ux0:app/<TITLEID>/assets`).
- Credits file: engine (Captain Dreamcast, MIT), characters (their authors), motif
  (evil_dark_lxs), tools used.
- A short "how this was built" doc so the user can rebuild it himself.

**Done when:** the user can install, play, and rebuild from the repo without asking questions.

---

## Questions to put to the user before T5

1. Roster scope: focused 8–12 or push for all 57?
2. Is 1v1 truly final (no tag), or should a Dolmexica teams patch be scoped separately?
3. If the rebuilt motif looks worse than the original at 960×544, which wins — look or
   schedule?
