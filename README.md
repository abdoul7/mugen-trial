# Jump Force Vita

A M.U.G.E.N fighting game for the PS Vita, built on the Dolmexica Infinite 1.8 engine.
Everything in `build/` and `dist/` is generated: change `roster.json` or `tools/`, never
the generated files.

## Layout

| Path | What it is |
|---|---|
| `handoff/` | the original research package (brief, facts, task list, roster) |
| `roster.json` | **the one file you edit**: characters, stages, music, motif, audio budget |
| `tools/build_assets.py` | assembles `build/game/` (engine + assets) from the sources |
| `tools/shrink_snd.py` | re-encodes a character's `.snd` to fit the Vita memory budget |
| `tools/port_motif.py` | re-lays-out the TBM 1280×720 screenpack for the 4:3 Vita frame |
| `tools/soak_test.py` | unattended CPU-vs-CPU fight test on the Windows build |
| `tools/contact_sheet.py` | turns soak screenshots into one image per run |
| `tools/make_vpk.py` | packages `build/game` into `dist/JFVT00001.vpk` |
| `tools/check_char_refs.py` | lists missing / wrong-case files referenced by character `.def`s |
| `tools/extract_7z.py` | unpacks the demo archive (skipping Windows binaries) |
| `engine/` | Dolmexica Infinite 1.8 as downloaded from itch.io (untouched) |
| `source/` | extracted TBM demo + screenpack, engine source (`dolmexica-src/`) |
| `downloads/` | the original archives |
| `reports/` | triage output, soak-test results and screenshots |

## Rebuild from scratch

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install py7zr imageio-ffmpeg pillow psutil
.venv/Scripts/python.exe tools/fetch_sources.py
.venv/Scripts/python.exe tools/build_assets.py
.venv/Scripts/python.exe tools/soak_test.py
.venv/Scripts/python.exe tools/make_vpk.py
```

`build_assets.py` takes about a minute; `--no-music` skips the MP3→OGG step on rebuilds.
The soak test takes ~75 s per character and leaves screenshots in `reports/soak/<id>/`.

See `INSTALL.md` for putting the `.vpk` on a Vita, `NOTES.md` for what was found and
decided along the way, and `CREDITS.md` for authors.
