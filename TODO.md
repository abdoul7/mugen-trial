# Status and next work (updated 2026-10-27)

## Done (verified on Windows only — nothing has run on a Vita yet)

- Engine fetched; asset pipeline (`build_assets.py`) builds a clean tree from `roster.json`.
- **Roster: 22 characters** = 7 TBM-demo characters + stock KFM + 14 AK1 downloads
  (batch 1, see `reports/jf-sourcing.md`). All 22 fought a 60–75 s CPU match in the Windows soak.
  Gohan (Teen) dropped (engine can't parse its commands); Kaede dropped at the owner's request.
- Stock select screen widened to 3×10 automatically for 23 slots.
- Character audio shrunk (22 kHz, 16 kHz for the six heaviest); all BGM converted to OGG.
- `.vpk` packaging in pure Python (Windows Smart App Control blocks the kit's vitasdk exes).
  `dist/JFVT00001.vpk` **v00.02**, 327 MB, built locally (not in the repo).
- `tools/ingest_chars.py` unpacks + triages a folder of downloaded archives in one command.
- `tools/soak_test.py` now also fails a character that only shows the engine's red error screen.

## Open

- [ ] **Owner:** install `dist/JFVT00001.vpk` v00.02 on the Vita and report: boots? select
      screen? which matchups load? frame rate? Most AK1 characters peak at 400–800 MB on
      Windows versus 210–370 MB for the demo ones, so expect heavy ones to fail.
- [x] **Vita memory model:** `tools/vita_mem.py`, findings in `reports/vita-memory.md`. Every AK1
      character needs 185-832 MB of textures per fighter (the engine turns their per-sprite-palette
      art into 32-bit textures; 60-75% of it is a few huge cut-in/aura sprites). Only the demo/stock
      characters are plausible on the Vita as things stand.
- [ ] **Engine:** set up the Dolmexica build (VitaSDK) and implement the memory fixes from
      `reports/vita-memory.md`: P8 textures with per-sprite palettes (~4x), drawing downscaled
      oversized sprites at their original size, sharing sprites in mirror matches.
- [ ] **Engine (T6):** if the Vita runs out of memory on load, rebuild Dolmexica with
      `_newlib_heap_size_user` 96 → 144 MB (`main.cpp:38-40`), via VitaSDK in Docker.
- [ ] **Sourcing:** the actual Jump Force headliners are still missing (Goku, Vegeta, Luffy,
      Naruto, Ichigo, Deku, Jotaro, Kenshiro, Yusuke…). Target sprites **≤ 10 MB** this time:
      the 15–30 MB JUS characters run noticeably slow even on the PC.
      Prompt: `docs/hermes-sourcing-prompt.md`. Known small picks: Luffy TS JUS – Sektor, Renji Abarai.
- [ ] **Uchiha Obito:** re-download — the owner's .zip.001+.002 are 21 MB short of what the zip declares.
- [ ] **Motif (T4):** set `"motif": "tbm"` in `roster.json`, build, screenshot title / select /
      fight HUD, then decide whether to keep the TBM look or the stock one.
- [ ] Stages: the 14 new characters reuse 3 existing stages; give them their own series stages.
- [ ] `trans = sub` effects (most JUS characters) are not implemented on Vita — check how they look on hardware.
