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

## Character acceptance

`python -I handoff/tools/scan_mugen_build.py source/jf` must say LIKELY OK (or TEST IT with
sprites < 20 MB), `tools/check_char_refs.py` must show no MISSING files, and the character
must survive `tools/soak_test.py <id>`. Archive guide: under ~25 MB. (The Vita heap is
96 MB total; a 96 MB Goku SSJ2 JUS was rejected for a 70 MB sprite file.)

## Status

See `TODO.md`. Sourcing log: `reports/jf-sourcing.md`. Sourcing-agent prompt:
`docs/hermes-sourcing-prompt.md`.
