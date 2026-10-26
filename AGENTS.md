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
