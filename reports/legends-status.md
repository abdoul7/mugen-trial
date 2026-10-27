# Legends: implementation status

Design contract: `docs/legends-design.md`; brief: `docs/legends-claude-prompt.md`.
Branch `mode/legends`, stacked on `motif/jfv-ui` (PR abdoul7/mugen-trial#6), which has the
menu and 640-space motif work it builds on.

Status: **native vertical slice**, run in Vita3K only. It is not Vita-proven: install and on-device
testing are the owner's.

## What exists

| Part | Where | State |
|---|---|---|
| Rules: catalog, seeded draws, hand, Hype, tickets, card states, modifiers, relay, CPU coach | `tools/legends/engine/legendscore.cpp` | done, unit-tested (no engine dependency) |
| Unit tests | `tools/legends/tests/test_legendscore.cpp`, `run.sh` | 301 checks pass, also under ASan + UBSan |
| Engine mode: squad select, opening deal, relay, results, rematch | `tools/legends/engine/legendsmode.cpp` | done |
| In-fight HUD: 3-card dock, Hype rail, tickets, armed/cooldown state, inspect, banners, squad pips, Awakening timer, bout clock | same | done (layout validated on one stage only, see below) |
| Engine hooks | `tools/engine/patches/0010-legends-mode-hooks.patch` | `GAME_MODE_LEGENDS`, menu item, fight actor, AI coaching, damage scale, autotest |
| Data | `tools/legends/catalog.json`, `adapters.json` -> `data/legends/*.txt` | 12 cards, 7 enabled; 2 verified adapters |
| HUD sprites | `tools/legends/legends_art.py` -> `data/legends/legends.sff` | 127 sprites, about 448 KB on disk with the local kit; faces, thumbnails, frames and animated VFX |
| Hands-off test | `tools/legends/vita3k_legends_autotest.py` + `legends_autotest.txt` | runs a CPU-coach vs CPU-coach encounter to the results |

Build: `python tools/make_ui.py` (writes the motif and `data/legends`), then
`wsl -d Ubuntu -u root -- bash tools/engine/build_vita.sh`. The build script copies
`tools/legends/engine/*` into the engine tree before the patches. The Windows exe is the stock
prebuilt engine: it has no Legends, and its menu skips the item.

## Cards

| Card | Family / rarity | State | Implementation, or the reason it is disabled |
|---|---|---|---|
| My Ninja Way | Resolve / C | enabled | Coach profile: approach band 24/12 (stock 50/30), guard -5%, moves tried 20% more often. Tagged approach/poke moves only on adapted fighters |
| Saiyan Pride | Resolve / R | disabled | needs adapters that tag supers and punish windows |
| Scarlet Resolve | Resolve / E | disabled | whiff detection is not implemented |
| Chidori | Secret Arts / C | enabled | Card-owned lightning echo: grounded and in control to start, 10-tick interruptible windup, 9 px/tick, range 140, 7% max HP, can be blocked |
| Spirit Gun | Secret Arts / C | enabled | Energy echo: 12-tick windup, 5 px/tick, range 260, 6%, one hit, blockable, no tracking |
| Bungee Gum | Secret Arts / R | disabled | no safe way yet to limit separation without forcing states |
| Kaio-ken | Awakening / R | enabled | 6 s: x1.2 damage dealt (damage hook), closer approach band, 1% max HP/s strain that never KOs |
| Bankai | Awakening / E | disabled | power-gain scaling is not hooked; shipping only half of the card is not allowed |
| PLUS ULTRA | Awakening / E | enabled | Below 35% HP, once per encounter: 5 s of x1.1 damage dealt; the next two clean hits taken within those 5 s do 35% less |
| ZA WARUDO | Plot Twist / L | disabled | freezing a fighter together with its helpers and projectiles, then restoring them on KO/exit, is not implemented |
| Senzu Bean | Plot Twist / C | enabled | 30-tick windup, grounded and in control; a hit interrupts it; recovers 12% max HP |
| Pot of Greed | Plot Twist / R | enabled | 2 bonus tickets through the bounded queue (at most 2 bonus, 3 total), once per encounter |

With no Legendary enabled, the Legendary bucket is empty and draws renormalise to 55/30/12 out of
97 (unit-tested). Disabled cards are never drawn.

## Coaching: what it can and cannot do

- **Generic AI** (`ai.cpp`): Legends changes three things, per fighter:
  - the approach band
  - the guard chance (bias, clamped to 15-85%)
  - the command interval

  It also lets tagged commands take a share (`tag.bias`) of the random command picks. Nothing
  forces states, and AILevel is not touched.
- **Adapters:** two verified ones, Kung Fu Man and Pupa. Both have stock-style commands and no
  CPU-detect commands. Their `FF` dash is tagged approach; `x`, `a`, `down_a` are tagged poke.
  The engine only uses a tagged command if the character really defines it.
- **Characters with their own AI:** 18 of the 27 run their own scripted AI (AILevel triggers, or
  `cpu1`..`cpuN` detect commands, as Goenitz has). Generic coaching changes their spacing and
  guarding but may be overridden by their own logic. They have no adapters, so cards that need
  one are not drawn for them.
- **Bout telemetry:** at the end of every bout the log records average distance, the share of
  ticks spent close, and commands vs tagged commands. That is how strategy change is measured
  (below).

## Verified

- **Unit tests:** 301 checks pass (also under ASan + UBSan).
- **Vita3K, patched engine (all 10 patches), hands-off autotest:** full 3-bout encounters ran to
  the results screen.
  - 3 bouts in 217 s; another encounter of 5 bouts.
  - Every enabled card was played by a CPU coach, with the logged behaviour: heals of 180 HP
    (12% of 1500), PLUS ULTRA absorbed exactly 2 hits, Pot of Greed delivered 2 bonus tickets,
    echoes hit, were blocked and were interrupted.
- **Vita3K, menu route:** title, LEGENDS, three picks, opening deal.
- **Resolve comparison rerun:** seed 777, Kung Fu Man vs Gouken in bout 1. With My Ninja Way:
  61/115 commands tagged, 28% close, average distance 54. With `--ban-p1 my_ninja_way`:
  0/103 tagged, 21% close, average distance 59. Both encounters completed four bouts.
  The control log has no player-coach draw, attach or commit of the banned card.
  Native fighter RNG is not seeded by this harness; these are observations, not balance proof.
- **Renderer continuation:** kit hand tiles/faces and animated effects are wired in. Actual
  opening/inspect captures were reviewed and text collisions fixed. Details and commands:
  `reports/legends-renderer.md`.

## Not done / not verified

- On a physical Vita: frame rate, texture memory, legibility. The kit alone decodes to 1.01 MiB at 8 bits (about 4.04 MiB at 32 bits), plus
  placeholders/palettes/engine overhead. Hardware texture allocation remains unmeasured.
- **Art kit (Codex v0.1):**
  - Done: `tools/legends/legends_kit.py` converts the kit's three runtime atlases (kept locally in
    ignored `source/legends-art/kit/`) into `legends.sff` plus `legends.air`. That is 1.01 MiB
    decoded at 8 bits, about 4 MiB at 32-bit.
  - Done: the catalog takes its names, rules text, flavor and timings from the kit.
  - Done: engine rendering for tiles, full faces and animated VFX. Missing-kit installations
    retain the placeholder fallback. No art binaries are committed.
- The 5 disabled cards, including ZA WARUDO.
- Squad order is the pick order: there is no separate reorder step.
- Hype bonus events: knockdowns only. Reversals and defensive sequences are not detected.
- PLUS ULTRA is once per coach per encounter, not per fighter.
- HUD occlusion checked on the stages the autotest happened to pick, not all of them.
- Sound cues: none.
- Booting straight into the Legends screen crashed Vita3K itself (host access violation). The
  autotest now starts from the title screen, the way a player enters the mode. The original
  cause is unknown.
- Windows footage: not possible here, because the Windows exe is the stock prebuilt engine.
  Building Windows from source needs FMOD and about a dozen SDKs. Footage is from Vita3K, labelled
  as such.
