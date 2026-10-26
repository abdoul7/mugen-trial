# Status and next work (2026-10-27)

## Done (verified on Windows only)

- Engine fetched; asset pipeline (`build_assets.py`) builds a clean tree from `roster.json`.
- 7 demo characters + stock KFM pass a 60–75 s CPU fight soak (Kaede dropped at the owner's request).
- Character audio shrunk (Bender 17.3 → 3.6 MB); all BGM converted to OGG.
- `.vpk` packaging in pure Python (Windows Smart App Control blocks the kit's vitasdk exes).
  `dist/JFVT00001.vpk` v00.01 built, **not yet installed on a Vita**.

## Open

- [ ] **Owner:** install `dist/JFVT00001.vpk` on the Vita and play a round (M1 sign-off).
- [ ] **Sourcing:** Jump Force characters from AK1 → `reports/jf-sourcing.md` (Luffy, Renji candidates found).
- [ ] **Integration:** add accepted JF characters to `roster.json` (needs `build_assets.py`
      to accept a per-character source root, and to leave `localcoord` alone when unset).
- [ ] **Motif (T4):** set `"motif": "tbm"` in `roster.json`, build, screenshot title / select /
      fight HUD, then decide whether to keep the TBM look or the stock one.
- [ ] **Engine (T6):** only if the Vita crashes on load — rebuild with heap 96 → 144 MB.
- [ ] Gouken is the top memory risk (1,785 sprites, 638 MB peak on Windows); first to cut if the Vita struggles.
