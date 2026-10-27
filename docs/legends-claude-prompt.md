# Claude implementation prompt — LEGENDS

You are implementing a **new, separate mode called Legends** in Jump Force Vita,
repository https://github.com/abdoul7/mugen-trial . This is a native Dolmexica
Infinite C++ implementation, not an HTML prototype or a reskin of Watch mode.

Design/art branch: `motif/legends-mode-design`. Fetch it to obtain the design,
catalog and asset builder if they are not yet on main. Create the implementation
branch from the agreed current engine/integration base; do not overwrite the
ongoing menu redesign. The art bundle can also be supplied directly by the owner.

Read AGENTS.md, TODO.md, NOTES.md, handoff/CLAUDE.md, then
**docs/legends-design.md** and **tools/legends/catalog.json** in full. The design
document is the behavioral contract; the catalog is the starter content authority.
Read reports/legends-research.md and reports/legends-art.md for provenance, asset
locations, measured art checks and unfinished work. Review the actual current
engine/UI branches before choosing the integration point. Preserve other agents'
work. Only the integration lane edits roster.json.

## What to build

Add a menu entry and isolated mode/session with this flow:
select three distinct fighters -> order squad -> receive three opening cards ->
equip the opening Resolve -> live CPU-vs-CPU 1v1 fight with card coaching ->
successive elimination bouts -> match results/rematch.

The engine supports 1v1 only. Implement three-fighter squads as a **mode-level
relay of separate bouts**, with HP carryover and lifecycle rules from the design.
Do not attempt to restore teams, tag, simul or actual simultaneous 2v1. Tournament
Night is explicitly deferred. Existing Arcade/Versus/Training/Watch must retain
their behavior outside Legends.

Exactly four card families: **Resolve, Secret Arts, Awakenings, Plot Twists**.
Common/Rare/Epic/Legendary are separate rarities, not more families. Implement the
Hype-driven draw, opening guarantee, three-card hand, bounded pending tickets,
seeded RNG, eligibility filtering, duplication limits and Legendary cap exactly
as specified, with editable balance data rather than hardcoded character patches.

## Coaching is real engine work

Inspect `ai.cpp`, command/state evaluation, match loading, player ownership,
damage/guard events, projectiles/helpers and input dispatch. Build typed snapshots,
CoachProfile, explicit per-character adapters and source-tokened modifiers.
Do not claim that increasing AILevel or randomly forcing ChangeState controllers
implements strategic coaching. Custom character AI can ignore generic priorities;
map supported behaviors deliberately and report unsupported ones honestly.

Cards must go through validation/reservation/commit/effect/cleanup states. Provide
immediate feedback, legal-action buffering and declared windups/interruption.
No arbitrary mid-hitstun attacks, hidden lost inputs or infinite reservations.
The CPU coach follows the same draw/cooldown/eligibility rules and bounded reaction
delay, using only public combat information and its own hand.

Start with two verified fighters, My Ninja Way, one Secret Art, Senzu Bean and a
basic Awakening. Prove the framework and cleanup before wiring every reference.
Add the remaining starter cards progressively. A capability-unimplemented card
is disabled visibly, not faked with an unrelated stat boost.

The inspected engine declares modes in `gamelogic.h` and wires title-menu
callbacks in `titlescreen.cpp`. Add a real mode and callback; a new DEF menu name
alone is not enough. Inspect the current source before applying those locations.

ZA WARUDO requires freezing the opponent's owned fighter/helper/projectile scope,
not simply calling global SuperPause and hoping it behaves. Implement the damage
cap, card lock, clocks, deterministic conflict arbitration and restoration on
KO/timeout/relay/exit. Test failures before exposing it in normal draws.

## Art and native UI

Use the provided Legends art kit as a starting point and keep the actual game's
nostalgic detailed arcade sprite style. Do not replace it with a browser dashboard,
generic block art, smooth AI anime paintings or a random mascot/city backdrop.
Preserve current Jump Force Vita branding; Legends is a mode label.

Legendary cards must be **full art with a visibly richer, detailed background**.
Common cards have a compact framed illustration, Rare more coverage, Epic extended
art. Keep family icon, rarity marker and rules legible at every tier. Text,
cooldowns, timers, targets, focus and card availability are runtime UI elements;
do not bake the whole functional hand into one generated image.

Implement the three-slot collapsed dock, inspection view, Hype meter/pending draws,
Resolve slot, Awakening timer, squad rails, card states, opening deal, relay panel
and results. Wire actual Vita/controller inputs through the engine abstraction.
All critical content stays 4:3-safe at 960x544. Use integer pixel sampling where
appropriate. Keep the fight visible; validate hand/HUD occlusion on real stages.
Use small shared sprites and measure decoded memory against the initial <=4 MiB
card/UI budget. No full-screen frame sequences, MP3, subtractive blending or font
bank assumptions. Sound cue IDs in the kit are a brief, not completed audio.

## Execution and delivery

Proceed beyond planning. First deliver a working native vertical slice with an
actual 1v1 CPU fight, cards drawn and played, visible coaching behavior and a safe
return to the original menu. Then expand relay/content and polish. Keep commit
boundaries small and update the handoff with concrete tested status.

Add meaningful tests for draws/queues, activation/cost timing, modifier cleanup,
custom-AI adapters, simultaneous events, time-stop restoration and relay outcomes.
Check classic-mode regressions, repeated-session memory and controller navigation.
Capture real Windows engine footage; label emulator and hardware results separately.
Do not call it Vita-proven without the owner's on-device test.

Work on one appropriate branch and open a PR into main. Commit only our original
source/tools/docs/text manifests; no art, screenshots, engine binaries, archives or
VPKs. If engine rebuilding is needed, provide reproducible source patches/build
steps and coordinate the engine lane. Never patch a shipped SELF/VELF. The owner
has authorized pushing completed source work, not bypassing repo asset rules.

The exact first playtest numbers may be revised after evidence, but document the
change rather than silently simplifying away the coaching layer or card effects.
