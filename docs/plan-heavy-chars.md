# Plan: get Kaguya, Android 18 (C) and Vegito running on the Vita build

Handoff for a coding agent. Everything you need is in this file, the repo, and the paths below.
Owner of this work: Issa (GitHub `Issa-14`). Repo `abdoul7/mugen-trial`, local clone `C:\Users\issaa\mugen-trial`.

## Ground rules (read first)

- Work on branch **`roster/jf-on-vita`**. It has local, **unpushed** commits (`b644cae`, `437be4d`).
  **Do not push or open PRs** unless Issa asks: PR work is paused. Commit locally.
- Read `AGENTS.md`. Highlights: never commit game assets (character files, screenshots, `source/`,
  `build/`, `dist/`). Commit only `tools/`, `docs/`, `roster.json`, `reports/*.md|csv`.
- **Never edit `source/jf/...` (the original downloads) or `build/` by hand.** Every change to a
  character must be made by `tools/build_assets.py` while it copies the character into `build/game`,
  so a rebuild from scratch reproduces it. Character-specific settings go in that character's
  `roster.json` entry.
- Engine changes go in `tools/engine/patches/*.patch` (LF line endings), never into `source/`.
- Shell is git-bash on Windows. Use the venv: `.venv/Scripts/python.exe`. Files under `tools/` are
  CRLF: edit them with Python (`newline=''`), not sed, or matches fail.
- Treat `vegito` as untrusted. The download hides its text behind ~80,000 junk lines per file and
  references a `common1.dll`, a pattern used to disguise malware. Never extract or run anything from
  its archive. We only read its text files.

## Where things stand

The Vita build runs in the **Vita3K emulator** on this PC with the patched engine. 25 characters are
fine. These three fail in a mirror match (same character on both sides, the worst case):

| roster id | source folder (`source/jf/`) | failure | evidence |
|---|---|---|---|
| `otsutsuki_kaguya` | `otsutsuki_kaguya_v1_0/Otsutsuki_Kaguya` | crashes loading the 2nd copy: `Out of main memory requesting 707625 bytes` | one Kaguya = **78 MB of the 96 MB heap** |
| `androide_c_18` | `androide_c_18/Androide-C-18` | fight loads, then crawls/freezes on frame 1 | log spam: `ID 1508 state machine stuck in loop (stopped after 2500 loops): 0 -> 1101` (`repo/mugenstatehandler.cpp:148`) |
| `vegito` | `vegito/Vegito` | black screen for 2+ min, never reaches the fight | log stops after heap reaches 42 MB during loading; 4.8 MB of scripts even after the padding is stripped |

Logs and screenshots for these runs are in `reports/vita3k/fights/<id>/` (`prismlog.txt` is the
engine's log; `vita3k.log` is the emulator's). Ichibe works, so the texture side is fine; the
problems are **main memory (heap) and scripts**.

## Tools you will use

- `tools/build_assets.py [--no-music]`: builds `build/game/` from `roster.json` (about 1 min).
- `tools/vita_mem.py`: predicted texture memory per character. It does **not** model the heap; adding
  that is part of task 1.
- Engine build (WSL Ubuntu + VitaSDK, about 3 min):
  `wsl.exe -d Ubuntu -u root -- bash -c "cd /mnt/c/Users/issaa/mugen-trial && bash tools/engine/build_vita.sh --debug [--heap MB]" | tr -d '\0\r'`
  This writes `build/engine/DolmexicaInfinite.self`. `--debug` makes the engine log to
  `ux0:data/prismlog.txt`, including `Heap: … used` and `Free memory: cdram …, user …`.
- Load a build into the emulator (the game is already installed in Vita3K as `JFVT00001`):
  ```
  APP="$APPDATA/Vita3K/Vita3K/ux0/app/JFVT00001"
  rm -rf "$APP/assets" && cp -r build/game/assets "$APP/assets" && find "$APP/assets" -name "*.soakbak" -delete
  cp build/engine/DolmexicaInfinite.self "$APP/eboot.bin"
  ```
- Fight test: `SHOT_INTERVAL=10 .venv/Scripts/python.exe tools/vita3k_fight_test.py <id> [--vs <id>] --secs 120`.
  It writes screenshots, `prismlog.txt` and a row in `reports/vita3k/fights/results.csv`.
  One run takes about 2.5 min. **Test only the characters you changed**; Issa wants credits used
  carefully, so don't sweep the whole roster.
- Windows build (fast check of script behaviour, no Vita memory limits): `tools/soak_test.py`,
  `tools/drive_game.py`. Vita3K is the arbiter for memory.
- Engine source for reading: `source/dolmexica-src/{repo,prism}`. Useful places:
  `repo/main.cpp:40` (heap size), `repo/fightscreen.cpp:143-185` (load order and stats),
  `prism/mugenspritefilereader.cpp`, `prism/memoryhandler.cpp:483`.

## Task 0: measure before changing anything (all three)

1. For each of the three, record from its `prismlog.txt`: heap used after its sprites load, after
   sounds, and after scripts. The log has `Heap:` lines between load steps, and
   `fightscreen.cpp:181-185` prints `assignments / controllers / memory blocks`.
2. Record the file sizes in `build/game/assets/chars/<id>/`: `.sff`, `.snd`, and every
   `.cns/.cmd/.air/.st/.dat`.
3. Write the numbers into a new `reports/heavy-chars.md`. Every later step must show before/after
   numbers there.

## Task 1: script and file compression in the build (generic, all characters)

Make these changes in `build_assets.py`, each switchable and logged like the existing steps:

1. **Minify scripts** (`.cns .cmd .air .st .def`): drop comment-only lines, strip `;` comments
   (watch for `;` inside quoted strings), drop blank lines and trailing whitespace. This doesn't
   change behaviour. Vegito's `&cls` padding is already stripped (`strip_cls_padding`).
2. **Prune unreachable states**: build the set of `[Statedef N]`s reachable from the engine's common
   states (`common1.cns`), the `.cmd` (`changestate` values), and every `ChangeState` /
   `SelfState` / `TargetState` / `Helper stateno` / `HitDef p1stateno|p2stateno` in the scripts.
   - Drop any statedef that is never referenced.
   - If a value is an expression rather than a literal, keep every state in that number range
     (be conservative).
   - Log how many states were removed.
3. **Prune unused sprites** from the `.sff` (rewrite the file):
   - Keep every sprite referenced by `.air` animations.
   - Keep group 9000 (portraits) and every literal `spriteno`, `sprpriority`-free `ChangeAnim`
     target, and anything in ranges used by expressions.
   - Drop the rest. This reduces both heap and texture memory.
   - SFF v1 and v2 differ: see `tools/vita_mem.py` and `tools/shrink_snd.py` for parsers.
4. **Pre-shrink oversized sprites on disk**, in addition to the engine-side cap from patch 0002.
   Halve, by integer factor, any sprite whose size is over the character's `sprite_cap`, and record
   the scale so the drawing size stays right.
   - **Only do this if** you can keep drawing size correct without engine changes (e.g. the
     character's `xscale`/`yscale` don't apply per-sprite). Otherwise skip it: patch 0002 already
     handles textures.
5. **Sound**: allow `snd_rate` down to 11025 for these three (already supported per character in
   `roster.json`).

Verify on the Windows build that a light character (`kfm`) and one AK1 character (`kefla`) still
fight normally after each step (`soak_test.py`). Then check heap numbers in Vita3K.

## Task 2: Kaguya (heap)

1. Using Task 0's numbers, find what fills the 78 MB: sprite data, sounds, or script structures.
2. Apply Task 1 and re-measure.
3. Lever A: if one Kaguya still uses more than ~40 MB of heap, try a bigger engine heap:
   `build_vita.sh --heap 128` (or 160). The log shows ~152 MB of `user` memory free, but textures
   spill into that same memory once CDRAM is full (Ichibe hits `cdram 0`). So re-test **Ichibe,
   Kefla and Goku Black mirrors** after changing the heap, and record the result.
4. Pass condition: `otsutsuki_kaguya` mirror runs 120 s in Vita3K with both fighters on screen and
   the timer moving. Also run `--vs ichibe_hyosube` (the heaviest pairing).

## Task 3: Android 18 (C) (script loop)

1. In `build/game/assets/chars/androide_c_18/`, find:
   - the `Helper` with `id = 1508`;
   - its `stateno`;
   - state 0's and statedef 1101's `ChangeState` controllers.

   The log says the helper bounces 0 → 1101 → 0 … 2500 times per tick, so one of those triggers
   behaves differently in Dolmexica than in MUGEN. Likely suspects: helper-specific triggers
   (`IsHelper`, `Parent,…`, `Root,…`), `Time`, `AnimTime`, `var()` initial values, or `ctrl`.
2. Confirm on the Windows build: `soak_test.py` with `androide_c_18` should show the same loop if
   it's an engine incompatibility.
3. Fix it in one of these two ways (prefer the first):
   - **Script fix in the build:** add a generic `script_fixes` list to the character's
     `roster.json` entry, `[{"file": "...cns", "find": "...", "replace": "..."}]`. `build_assets.py`
     applies each fix exactly once and fails the build if `find` doesn't match exactly once. Keep
     every `find` string minimal: it lives in our public repo, so no large chunks of the
     character's code.
   - **Engine fix** as `tools/engine/patches/0004-*.patch`, if the trigger is genuinely
     mis-implemented in Dolmexica. That fixes it for every character, but needs a rebuild and a
     re-test of a few characters.
4. Pass condition: an `androide_c_18` mirror runs 120 s in Vita3K, the timer moves, and the loop
   message no longer appears in `prismlog.txt`.

## Task 4: Vegito (load time / hang)

1. First tell "slow" apart from "stuck":
   - Run him on the Windows build (`soak_test.py vegito`) and time the load.
   - In Vita3K, run with `--secs 300` and see whether the `Heap:` lines in `prismlog.txt` keep
     growing, which means it's still parsing.
2. Apply Task 1 (minify plus state pruning). His files are full of duplicated states across
   `SSJ.cns`, `SSJBlue.cns`, `Ultimate.cns`, `Skills.cns` and `Misc.cns`. Also check
   `AI.dat` (95 KB `st1` file).
   - If one file causes the stall, bisect: build with one `stN` removed at a time using
     `def_overrides` in `roster.json`, e.g. `{"st5": ""}`, and note what the character loses.
3. His `stcommon` was `common1.dll`. The build maps it to the engine's `common1.cns`
   (`def_overrides`). Check that's sufficient, i.e. he doesn't depend on custom common states
   that the `.dll` was supposed to hold. If the scripts reference `[Statedef 5xxx]` states that
   exist nowhere, say so in the report.
4. Pass condition: a `vegito` mirror loads within 60 s in Vita3K and runs 120 s with the timer
   moving.

## Finish

1. Add each character that passes to the roster (they're in `roster.json` already; don't re-add
   them). Move any that still fail to `"removed"` in `roster.json` with the reason, like `kfm720`.
2. Update `reports/heavy-chars.md` with before/after numbers per step, plus `TODO.md`.
3. Build a test vpk:
   ```
   .venv/Scripts/python.exe tools/build_assets.py
   .venv/Scripts/python.exe tools/make_vpk.py --version 00.05 --self build/engine/DolmexicaInfinite.self
   ```
   Check `make_vpk.py --help` for the exact flags, and copy the result to
   `dist/vita-test/JFVT00001-test5.vpk`. **Don't** build with `--debug` for this file unless Issa
   wants the log on hardware. Rebuild the engine without it first.
4. Commit locally on `roster/jf-on-vita` (tools, docs, roster.json, reports only). Don't push.
5. Report to Issa in plain language: what passed and what didn't, with file paths. State clearly
   that everything was verified **in the Vita3K emulator only, not on a Vita**. Kaguya's heap
   change especially needs hardware confirmation.
