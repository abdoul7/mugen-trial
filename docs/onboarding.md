# Onboarding (for new agents, e.g. Astra)

**Project:** a M.U.G.E.N fighting game for a modded PS Vita, built on the Dolmexica Infinite
engine, packaged as `dist/JFVT00001.vpk`. The target is the Jump Force roster, with the look
of the PC pack *The Best M.U.G.E.N 1.1*. 1v1 only.

**Read first:** `AGENTS.md` (rules + lanes), `TODO.md` (open work), `handoff/CLAUDE.md`
(hard technical limits).

**Where it stands:** 22 characters build and fight on the Windows version of the engine. v00.02
`.vpk` is built but **not yet tested on a Vita** (the owner does that). Only Sasuke and Madara
are actual Jump Force roster characters so far.

**Setup:** `python -m venv .venv`, `pip install py7zr imageio-ffmpeg pillow psutil`, then
`tools/fetch_sources.py` → `tools/build_assets.py` → `tools/make_vpk.py`. Character archives
aren't in the repo (it's public); `reports/jf-archives.csv` lists them by SHA-256.

**Most useful next work:**
1. Source the Jump Force headliners (Goku, Vegeta, Luffy, Naruto, Ichigo, Deku…), with sprite
   files **≤ 10 MB**. Unpack and check them with `tools/ingest_chars.py <folder>`, and log
   them in `reports/jf-sourcing.md`. Prompt: `docs/hermes-sourcing-prompt.md`.
2. Port the TBM look: set `"motif": "tbm"` in `roster.json`, build, and judge screenshots.

**Hard rules:** never commit game assets, archives or `.vpk`s. One branch + PR per task, and
only the integration lane edits `roster.json`. On AK1 browse at a person's pace; on a 429 or
a Cloudflare check, stop and hand it to the owner. Never sign in anywhere.
