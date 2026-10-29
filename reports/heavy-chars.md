# Heavy characters on the Vita build

This report tracks Kaguya, Android 18 (C), and Vegito. Baseline evidence is from the existing Vita3K logs and the asset tree at commit `7c7744b`. **All runtime evidence in this report is from the Vita3K emulator, not a physical Vita.**

## Measurement rules

- Heap values are bytes used by the whole fight-loading process, not memory attributed to only one fighter.
- `P1` and `P2` identify the point immediately after that copy finished a load stage. The values are cumulative.
- `State scripts` is the heap log after the last `stN` file and before the `.air` file. `Scripts + anim` is immediately after `.air` loading. `Sounds` and `sprites` are the corresponding per-player heap logs.
- Line numbers refer to each character's baseline `reports/vita3k/fights/<id>/prismlog.txt`.
- File sizes below are exact bytes in `build/game/assets/chars/<id>/` before Task 1 changes.

## Task 0 — baseline

### `otsutsuki_kaguya`

The first sprite load finishes with 77932472 bytes of heap in use. The second copy starts and then allocation fails while requesting 707625 bytes (log lines 205–228). Sound and script loading completed before the sprite crash. The pre-sprite memory-stack shrink leaves 24440040 bytes used (line 203).

| Load stage | Heap after P1 (bytes) | Heap after P2 (bytes) | Evidence |
|---|---:|---:|---|
| State scripts | 3460000 | 14665232 | lines 130, 173 |
| Scripts + anim | 4077656 | 15283128 | lines 151, 194 |
| Sounds | 14552216 | 25757656 | lines 153, 196 |
| Sprites | 77932472 | Not reached: out of memory | lines 216, 218–228 |
| Fight screen loaded | Not reached | Not reached | allocation abort at line 228 |

No post-load `assignments / controllers / memory blocks` statistics were emitted.

| File | Bytes |
|---|---:|
| Resources/anim.air | 98890 |
| Resources/cmd.cmd | 4052 |
| Resources/extra.cns | 71636 |
| Resources/main.cns | 332304 |
| Resources/snd.snd | 10111894 |
| Resources/source.cns | 108250 |
| Resources/spr.sff | 55546198 |

Baseline totals: `.sff` 55546198 bytes; `.snd` 10111894 bytes; listed scripts 615132 bytes.

### `androide_c_18`

Both fighters load and the fight screen starts. The later failure is the helper state-machine loop, not an initial heap exhaustion.

| Load stage | Heap after P1 (bytes) | Heap after P2 (bytes) | Evidence |
|---|---:|---:|---|
| State scripts | 3493640 | 12421760 | lines 145, 185 |
| Scripts + anim | 4364536 | 13292816 | lines 147, 187 |
| Sounds | 12262736 | 21191000 | lines 149, 189 |
| Sprites | 22231048 | 23468352 | lines 201, 205 |
| Fight screen loaded | 28357752 | 28357752 | line 237 |

Post-load statistics (lines 239–243): assignments 147804; controllers 8906; maps 53; memory blocks 36127; memory stack used 1974272 bytes. The repeated baseline error is `ID 1508 state machine stuck in loop (stopped after 2500 loops): 0 -> 1101`.

| File | Bytes |
|---|---:|
| Androide-C-18-AI.cmd | 19582 |
| Androide-C-18-AI.cns | 263990 |
| Androide-C-18.air | 197045 |
| Androide-C-18.cmd | 20260 |
| Androide-C-18.cns | 327216 |
| Androide-C-18.sff | 119135005 |
| Androide-C-18.snd | 7661225 |
| common1-AI.cns | 55494 |
| common1-AILevel.cns | 51608 |
| common1.cns | 66458 |
| final.sff | 73182 |
| IA.cns | 29709 |
| intro.sff | 5662238 |
| Supers.cns | 46897 |
| Visuals.cns | 326622 |

Baseline totals: `.sff` 124870425 bytes; `.snd` 7661225 bytes; listed scripts 1404881 bytes.

### `vegito`

P1 finishes state scripts, animations, and sounds. P2 stops during state-script parsing: the last log is after `st4 = SSJ.cns`, before `st5 = SSJBlue.cns` finishes. Neither player reaches the fight-screen sprite-load stage in this log.

| Load stage | Heap after P1 (bytes) | Heap after P2 (bytes) | Evidence |
|---|---:|---:|---|
| State scripts | 13426808 | Incomplete; last value 42100696 after `st4` | lines 139, 169 |
| Scripts + anim | 16245240 | Not reached | line 141 |
| Sounds | 30731360 | Not reached | line 143 |
| Sprites | Not reached | Not reached | no fight-screen character sprite load |
| Fight screen loaded | Not reached | Not reached | log ends at line 170 |

No post-load `assignments / controllers / memory blocks` statistics were emitted.

| File | Bytes |
|---|---:|
| AI.dat | 95083 |
| Misc.cns | 544284 |
| Skills.cns | 447896 |
| SSJ.cns | 1154737 |
| SSJBlue.cns | 1496995 |
| Ultimate.cns | 591170 |
| Vegito.air | 826970 |
| Vegito.cmd | 55186 |
| Vegito.cns | 522410 |
| Vegito.sff | 72431683 |
| Vegito.snd | 14275506 |

Baseline totals: `.sff` 72431683 bytes; `.snd` 14275506 bytes; listed scripts 5734731 bytes.

## Task 1 — generic build compression

### Minification (Windows; Vita3K pending)

| Character | Script files measured before → after (bytes) | Windows 75 s mirror |
|---|---:|---|
| `kfm` | 139378 → 92153 | process alive; active fight visible at 32 and 68 s |
| `kefla` | 653241 → 591924 | process alive; active fight visible at 32–56 s; 68 s capture is black, so the final frame is inconclusive |
| `otsutsuki_kaguya` | 615880 → 580214 | not yet tested |
| `androide_c_18` | 1408871 → 1261027 | not yet tested |
| `vegito` | 5735631 → 5223445 | not yet tested |

The byte totals include the `.def` and every script the minifier processes, so they differ from the Task 0 script-only totals. Windows soak logs: `.superpowers/sdd/plan-heavy-chars/minify-soak.log`; captures in `reports/soak/kfm/` and `reports/soak/kefla/`. The soak runner uses an infinite fight timer; captures do not prove a countdown.

### Conservative state pruning (Windows; Vita3K pending)

The state pass removed **0 states** from each of KFM, Kefla, Kaguya, Android 18 (C), and Vegito because reachable dynamic targets could not be bounded safely. Thus the five characters' post-state script bytes are unchanged from the minification table. KFM and Kefla Windows mirrors both stayed alive for 75 seconds; both showed two fighters actively fighting at 56 seconds. The runner's `OK` does not prove the entire match is bug-free. Build and soak output are in `.superpowers/sdd/plan-heavy-chars/states-build.log` and `states-soak.log`.

### Sprite pruning (Windows; Vita3K pending)

| Character | Sprites removed / original | Main `.sff` bytes before → after |
|---|---:|---:|
| `kfm` | 44 / 274 | 563020 → 539894 |
| `kefla` | 35 / 1104 | 23979599 → 23515263 |
| `otsutsuki_kaguya` | 338 / 2332 | 55546198 → 44807013 |
| `androide_c_18` | 741 / 3819 | 119135005 → 100521516 |
| `vegito` | 3197 / 7285 | 72431683 → 57171181 |

KFM and Kefla Windows mirrors stayed alive for 75 seconds, with both fighters visible at 56 seconds. This does **not** establish every animation is correct. State and sprite pruning remain opt-in until the targeted character fights and a safety review. Logs: `.superpowers/sdd/plan-heavy-chars/sprites-build.log` and `sprites-soak.log`.

Pre-shrinking on disk is skipped: the existing engine patch preserves each sprite's logical drawing size separately from its reduced texture dimensions; changing SFF dimensions alone cannot preserve that per-sprite scale without engine support.

### 11025 Hz audio

For Kaguya, Android 18 (C), and Vegito respectively, the prior 16000 Hz `.snd` baseline was 10,111,894 / 7,661,225 / 14,275,506 bytes; the rebuilt 11025 Hz files are 7,002,524 / 5,299,416 / 9,849,025 bytes. First embedded WAVs were checked as mono, 11025 Hz, 16-bit. Windows KFM and Kefla 75-second smoke runs survived, though their own audio rates were unchanged. Fidelity has not been subjectively assessed.

## Task 2 — Kaguya heap work

With script minification, opt-in state/sprite pruning and 11025 Hz audio, the 96 MiB debug heap still crashed during the second sprite load: 60,985,064 bytes used after player 1, then an allocation of 1,012,500 bytes failed. The original baseline was 77,932,472 bytes after player 1. Logs from the interrupted 96 MiB experiment were overwritten by the subsequent run; its console result appears in `results.csv`.

A 128 MiB **debug** engine completed 120-second Vita3K runs: Kaguya mirror peak 99.0 MiB heap, timer 98 at 40 seconds and 84 at 100 seconds; Kaguya vs Ichibe peak 75.5 MiB, both fighters visible and Ichibe wins. Mirror retests at 128 MiB: Ichibe peak 53.5 MiB (timer 99→50), Kefla 61.5 MiB (98→50), Goku Black 66.9 MiB (82→34). All three reported zero minimum free CDRAM, so actual Vita hardware remains unverified and memory headroom is a concern. These experiments used opt-in pruning, which is not the default final build.

## Task 3 — Android 18 (C) script-loop work

The pre-fix Vita3K 120-second mirror reported **12 state-machine loop warnings** and **32,246 attempts to enter missing state 362**. The affected Destructo Disc helpers (states 1101 and 1102) both target 362 for hit override and expiration, but no such state exists. This caused repeated immediate reevaluation and severe slowdown; the runtime helper ID is dynamically assigned, not a literal `id = 1508` in the character script.

A roster-controlled, exactly-once build fix adds a minimal state 362 that destroys the projectile helper. This changes that projectile's cleanup behavior; it does not edit the downloaded original. `tools/build_assets.py` rejects missing/ambiguous matches and paths outside the character directory.

After rebuilding and installing the copied script, a 120-second Vita3K mirror produced **zero loop warnings and zero missing-state-362 errors**. The timer reached 41 at 100 seconds and a later round was underway at 120 seconds. Other missing-state warnings remain: state 358 (16), 9999 (6), and 640 (4). Screenshots and logs are in `reports/vita3k/fights/androide_c_18/`; pre-fix evidence is preserved in `reports/vita3k/fights/heavy-chars-android-before-fix/`. This is emulator evidence, not a frame-rate benchmark or physical-Vita test.

## Task 4 — Vegito load-time work

Pending.

## Final packaging and verification

Pending.
