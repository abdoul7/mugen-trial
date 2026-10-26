# Installing on a PS Vita

You need a Vita with HENkaku/Ensō and **VitaShell**. Nothing else: Dolmexica 1.6+ no longer
uses vitaGL, so `libshacccg.suprx` is not required (the engine's bundled docs still mention it).

## 1. Prove the install path first (optional, 2 minutes)

`engine/Dolmexica Infinite 1.8/samples/Dolmexica Infinite Version 1 8 for Vita.vpk` is the
engine author's own stock build. If that installs and runs, any problem with ours is in our
assets, not in your Vita setup.

## 2. Install Jump Force Vita

1. Copy `dist/JFVT00001.vpk` to the Vita (VitaShell: press SELECT for FTP, or USB transfer)
   — e.g. to `ux0:data/`.
2. In VitaShell, highlight the `.vpk`, press ✕, confirm the install.
3. Start **Jump Force Vita** from the LiveArea.

TitleID is `JFVT00001`. If you ever change it, it must stay exactly 9 characters
(otherwise the install fails with `0xF0030000`).

## 3. Fast iteration without reinstalling

The game reads everything from `ux0:app/JFVT00001/assets/`, which VitaShell can write to.
To try a change, copy just the changed files from `build/game/assets/` over FTP into that
folder and relaunch — no new `.vpk` needed.

## Controls

The Vita maps its buttons to the engine's six attack buttons plus START; see the in-game
OPTIONS screen. 1 player vs CPU (arcade, versus-CPU, survival, training, watch).

## If it crashes

Note *when* (boot / select / loading a fight / mid-fight / after N fights) and which two
characters + stage. Memory-related crashes on load are what T6 in `handoff/TASKS.md`
(engine heap 96 MB → 144 MB rebuild) addresses.
