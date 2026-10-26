# Prompt for a sourcing agent (Hermes or similar)

Paste everything in the block below into the agent. It works on branch `sourcing/<batch>` and
opens a PR with `reports/jf-sourcing.md` updated.

```text
You are sourcing community M.U.G.E.N characters for a personal PS Vita fan project
("Jump Force Vita", engine: Dolmexica Infinite). Repo: https://github.com/abdoul7/mugen-trial
Read AGENTS.md first. Work on a branch named sourcing/<batch-name> and open a PR.

GOAL
For each character in handoff/roster/jumpforce-roster.md (skip Galena, Kane, Prometheus),
find the lightest decent community MUGEN version on AK1 (https://www.andersonkenya1.net),
preferably JUS style, download it, triage it, and record it in reports/jf-sourcing.md.
Stop at 12 accepted characters, then report back.

SITE RULES — NON-NEGOTIABLE
- Browse like a person: one search, then open at most 3 file pages, then wait at least
  20 seconds before the next request. No parallel requests, no bulk scripts.
- If you get HTTP 429, a "Just a moment..." page, or any Cloudflare / "verify you are
  human" check: STOP immediately, do not retry, do not try to solve or bypass it.
  Tell the owner and wait until they say it has been cleared.
- Never sign in, create accounts, or enter credentials. If a file needs an account, skip it
  and note "login required".
- Only download from AK1's own "Download this file" button. Don't follow off-site mirrors.

HOW TO CHOOSE A VERSION
- Search "<name> JUS" first, then just "<name>".
- Read "File Size" on each file page. Prefer archives under 15 MB; never take one over 30 MB.
  After extracting, the sprite file (.sff) should be 10 MB or less: batch 1 showed 15-30 MB
  JUS characters run slow even on the PC. Skip anything already in reports/jf-archives.csv.
- Prefer JUS / POTS / CvS style, base form (no "all forms" packs), single character.
- Known good picks: Luffy TS JUS – Sektor (14.3 MB, AK1 file 56847), Renji Abarai (5.9 MB, file 16703).
- Already rejected: Goku SSJ2 JUS by 此赤非彼枫 (file 61679), sprites 70 MB.

AFTER EACH DOWNLOAD
1. Move the archive to downloads/jf/ (git-ignored).
2. Extract to source/jf/<lowercase-id>/ with C:\Windows\System32\tar.exe (zip/rar) or
   .venv/Scripts/python.exe tools/extract_7z.py (7z). Exclude .exe .dll .bat.
   Never run anything from inside an extracted archive.
3. Run  python -I handoff/tools/scan_mugen_build.py source/jf
   and  python -I tools/check_char_refs.py source/jf
4. Accept only LIKELY OK (or TEST IT with sprite file <= 10 MB) with no MISSING files.
   Faster alternative to steps 2-3: .venv/Scripts/python.exe tools/ingest_chars.py <folder>
   Otherwise reject it with the exact reason (sprite size, audio, missing file, hi-res
   localcoord, trans = sub).
5. Add a row to reports/jf-sourcing.md:
   Jump Force name | AK1 title + file number | archive size | sff MB | snd MB | verdict | reason

DO NOT
- Commit any downloaded or extracted file (the repo is public; .gitignore covers them,
  never force-add). Only reports/jf-sourcing.md changes in your PR.
- Edit roster.json, tools/, build/ or dist/ — integration is a separate lane.
- Download anything from the commercial Jump Force game or rip sites.

WHEN DONE (or blocked)
Report: accepted list, rejected list with reasons, characters with no usable version, and
where you stopped.
```
