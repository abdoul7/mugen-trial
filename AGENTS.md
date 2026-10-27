# Agents working on Jump Force Vita

Several agents (Claude Code, Hermes, others) share this repo. Read this file, then
`handoff/CLAUDE.md` (hard technical rules) and `NOTES.md` (what has been verified).

## The repo is PUBLIC — what may be committed

Only our own work: `tools/`, `*.md`, `roster.json`, `handoff/` (minus the TBM excerpt),
`reports/**/*.md|csv`. **Never** commit engine binaries, the TBM screenpack, characters,
stages, music, screenshots of game art, archives or `.vpk`s. `.gitignore` enforces this;
don't use `git add -f` to get around it. Third-party files are fetched locally:

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install py7zr imageio-ffmpeg pillow psutil
.venv/Scripts/python.exe tools/fetch_sources.py   # engine + TBM demo + screenpack (~850 MB)
.venv/Scripts/python.exe tools/build_assets.py    # -> build/game
.venv/Scripts/python.exe tools/soak_test.py       # Windows CPU-vs-CPU test, ~75 s/char
.venv/Scripts/python.exe tools/make_vpk.py        # -> dist/JFVT00001.vpk
```

## How to split work

| Lane | Owns | Output |
|---|---|---|
| **Sourcing** (e.g. Hermes) | `downloads/jf/`, `source/jf/`, `reports/jf-sourcing.md` | accepted / rejected characters with sizes and reasons |
| **Integration** | `roster.json`, `tools/build_assets.py` | characters added, build + soak green |
| **Motif** | `tools/port_motif.py` | TBM look ported, screenshots judged |
| **Packaging / engine** | `tools/make_vpk.py`, heap rebuild (T6) | `.vpk` |

- One branch per piece of work: `sourcing/<batch>`, `roster/<chars>`, `motif/<topic>`.
  Open a PR into `main`; don't push to `main` directly.
- Only the integration lane edits `roster.json`, which stops two agents from rewriting it at once.
- Every PR says what was **verified** (soak result, screenshots seen locally) and what wasn't.
  On-hardware Vita testing is done by the owner only.

## Rules for any agent touching websites

- Character sources: AK1 (andersonkenya1.net). Browse like a person: one search, then
  ≤3 file pages, then ≥20 s pause. No bulk scripts, no parallel requests.
- On HTTP 429, a "Just a moment…" page or any Cloudflare / human-verification check:
  **stop, don't retry, don't solve or bypass it**, and hand it to the owner.
- Never sign in, create accounts or enter credentials. Never download from the commercial
  Jump Force game or rip sites. Never run anything from inside a downloaded archive.

## Getting the AK1 characters the roster uses

`roster.json` entries with `"root": "source/jf"` come from AK1 archives that are **not** in
this repo. `reports/jf-archives.csv` lists each one's filename, byte size and SHA-256.
Download the same files from AK1 (by hand, see the website rules), put them in one folder, run

```bash
.venv/Scripts/python.exe tools/ingest_chars.py "<that folder>"
```

and check the SHA-256s match. A character whose archive you don't have will fail
`build_assets.py`; comment it out of `roster.json` locally rather than committing that.

## Character acceptance

`python -I handoff/tools/scan_mugen_build.py source/jf` must say LIKELY OK (or TEST IT with
sprites < 20 MB), `tools/check_char_refs.py` must show no MISSING files, and the character
must survive `tools/soak_test.py <id>` (result `OK`, not `ENGINE ERROR`). Size guide for new
picks: sprites (`.sff`) **≤ 10 MB**. The batch-1 JUS characters at 15–30 MB pass on Windows
but run visibly slow there, and the Vita heap is 96 MB total.

## Status

See `TODO.md`. Sourcing log: `reports/jf-sourcing.md`. Sourcing-agent prompt:
`docs/hermes-sourcing-prompt.md`.

## UI handoff — 2026-10-27 (unfinished; read before UI work)

Read `handoff/UI.md` for the current checkout, assets, bugs and verification limits.
Read `docs/ui-claude-prompt.md` for the owner's latest menu redesign request and
researched implementation brief. Continue branch `motif/ui-overhaul`; keep it a
reviewable PR, and do not describe the current experiment as an approved design.

The owner wants modern fighting-game menu motion and polish **within the game's
own nostalgic arcade sprite art style**. This applies to characters, stages,
effects and UI together. Their reference is detailed hand-pixelled arcade art,
not a literal low-detail NES/5x7 treatment. Earlier AI concept boards were
rejected: generic browser-game UI, unrelated city skyline, Goku-like mascot,
and inconsistent illustration styles. `Jump Rift` was only an unapproved working
name; the latest screenshot still uses `Jump Force Vita`. Retain current branding
unless the owner approves a replacement.

Latest explicit requirement: remove the whole hardcoded bottom engine footer,
including the blue bar, Dolmexica text and date/presenter text. This needs a
native source change; see `titlescreen.cpp` around lines 345-352. Do not conceal
it with artwork. Preserve license/engine attribution in credits/documentation.

Current experimental tools: `tools/arcade_motif.py`, `tools/verify_arcade.py`,
`tools/normalize_portraits.py`. The portrait normalizer is **not wired into the
motif builder and has not been validated**. Known native bugs: high-resolution
portraits overflow select cells; `title.font = -1` draws the engine fallback
instead of hiding the mode heading. Fix and verify these before adding effects.

The old `build/arcade-preview` contains only 8 demo/stock fighters + randomselect;
it is not the full roster. The owner's AK1 archives are at
`C:\Users\abdou\Downloads\ak1 jump force characters handoff`. All 14 roster archive
SHA-256s were checked against `reports/jf-archives.csv`, extracted into ignored
`source/jf/`, and `build/game` now contains all 22 character directories and the
23-entry select list. The new UI has **not** been verified on that full build.
Do not edit `roster.json` from this lane. Do not commit game assets or screenshots.
