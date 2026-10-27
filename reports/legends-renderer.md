# Legends renderer and corrected Resolve comparison

Updated 2026-10-27. Native Dolmexica Vita build, tested in **Vita3K**, not on a physical Vita.
Branch `mode/legends`; PR is stacked on `motif/jfv-ui` (PR #6).

## Rendering

`legendsmode.cpp` now draws the local kit rather than leaving its SFF groups unused:

- Each hand slot uses its card thumbnail and ready/armed/cooldown/empty frame, with native
  names and status text. Focus uses the six-frame kit animation. Newly dealt card instances
  restart a 12-tick draw spark; reusing the same card ID still triggers it through its UID.
- Opening deal shows each actual card face (catalog ID/order, not family), with its native
  short name. The target and controls remain native. Full rules live in the inspect view.
- Inspect puts the 64x96 face next to a wider native rules panel. In-game captures exposed
  caption/squad and rules/footer collisions; both were fixed and recaptured.
- Spirit Gun and Chidori use their AIR animations, track the rules-core echo positions,
  mirror with fighter facing, and remove their handler elements at echo end.
- Successful healing starts the short heal animation at the recipient, following its screen
  position. Interrupted heals never emit it. Awakening auras follow the fighter while active:
  red for Kaio-ken, teal for PLUS ULTRA; hidden on expiry/KO.
- Static animation definitions used by changing hand/UI sprites are cached per bout. This
  prevents a long fight from accumulating a new definition on every hand-state change.

`legends_kit.py` now also exports the teal aura action. `legends_art.py` enlarges the native
inspect backing panel. No generated art, screenshots, binaries or VPKs are committed.
Place the kit's `runtime/` and `data/` inside ignored `source/legends-art/kit/`, or set
`LEGENDS_KIT`. Without it the existing placeholder sprites remain usable.

Memory: 127 SFF sprites, approximately 448 KB on disk. The kit sprites alone occupy 1.01 MiB
of decoded 8-bit pixels, before placeholder sprites, palettes and engine allocation overhead.
This is not a physical Vita texture-memory measurement.

## Corrected comparison

`--attach 0` only keeps the opening Resolve in hand, so it was never a valid no-Resolve control.
New `--ban-p1 my_ninja_way` writes `ban.p1` into the autotest config. The Match stores the
exclusion per coach and filters the common eligibility path used by both opening and ticket
draws. The opponent's pool is unchanged. Defaults reset at the start of each autotest.

Seed **777**; player squad: Kung Fu Man, Pupa, Bender. CPU: Gouken, Lucario, Janemba.

| First bout: Kung Fu Man vs Gouken | Resolve attached | My Ninja Way banned for player coach |
|---|---:|---:|
| Average separation (320-space units) | 54 | 59 |
| Combat ticks within 40 units | 28% | 21% |
| Commands / tagged commands | 115 / 61 | 103 / 0 |
| Combat ticks in bout | 2082 | 2309 |
| Encounter completion | 4 bouts, 236 s | 4 bouts, 241 s |

Control-log audit: **zero** player-side draw, attachment or commit of `my_ninja_way` throughout
the encounter. Opponent use is expected and permitted. Logs are local in
`build/legends-verify/{final-layout,without-resolve}/legends_log.txt`.
An earlier attached run (`with-resolve`, 248 s) measured 42% close and 93/184 tagged;
that repeat variability is another reason not to infer a precise balance effect.

These runs demonstrate the coaching hook and a clean exclusion. They do not isolate every
balance variable: native fighter RNG is not seeded by this harness, the different legal pool
changes the opening hand, Kaio-ken can also affect spacing, and bout lengths differ. Do not
interpret the close-time difference as a precise expected buff or win-rate claim.

## Reproduce

```powershell
.venv/Scripts/python.exe tools/make_ui.py
.venv/Scripts/python.exe tools/legends/tests/test_legends_art.py
wsl -d Ubuntu -u root -- bash tools/legends/tests/run.sh
wsl -d Ubuntu -u root -- bash tools/engine/build_vita.sh
```

Install that engine and generated assets into the local Vita3K game, then run:

```powershell
.venv/Scripts/python.exe tools/legends/vita3k_legends_autotest.py build/legends-verify/with-resolve --seed 777 --attach 1 --p1 kfm/kfm.def,pupa/Pupa.def,bender/bender.def --p2 gouken/gouken.def,lucario/Lucario_M.def,janemba/janemba.def
.venv/Scripts/python.exe tools/legends/vita3k_legends_autotest.py build/legends-verify/without-resolve --seed 777 --attach 0 --ban-p1 my_ninja_way --p1 kfm/kfm.def,pupa/Pupa.def,bender/bender.def --p2 gouken/gouken.def,lucario/Lucario_M.def,janemba/janemba.def
```

`--inspect --setup-ticks 300 --shot-every 0.25` exercises the opening/inspect art without sending
keystrokes. It changes only test dwell/rendering, not coaching decisions. The test runner now
requires a normal process exit plus an explicit results-completion log marker, checks banned
IDs against player draw/attach/commit lines, and writes `result.json`. A crash is not success.

## Checks and remaining work

- Rules: **301 checks pass**, also with AddressSanitizer and UndefinedBehaviorSanitizer.
- Asset round-trip: **127 kit sprites** and **32 fallback sprites** read back; all AIR sprite
  references resolve; all twelve card faces and thumbnails exist; teal aura exists.
- Native VitaSDK engine build succeeds with patches 0001–0010.
- Both comparison encounters reached results. The final renderer also completed four bouts in 236 s, with a confirmed results
  marker and exit code 0 (`build/legends-verify/final-layout/result.json`).
- Python compile checks and `git diff --check` pass.

Still outstanding: five disabled cards (including ZA WARUDO's safe fighter/helper/projectile
freeze and restoration), squad reordering, sound, and physical Vita testing. No roster edit.
HUD occlusion across every stage and character is still unverified.
