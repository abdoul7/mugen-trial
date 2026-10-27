# LEGENDS — mode design v0.1

Status: implementation specification and first art kit, not a playable mode.
Owner-approved direction: three selected fighters, AI-driven combat, coaching
through random cards, four card families, and spectacular anime crossover moments.
All numerical values below are first-playtest targets, not measured balance.

## 1. The experience

Legends is an additional main-menu mode in Jump Force Vita. You coach an ordered
squad of three fighters against a CPU-coached squad. Fighters conduct normal
MUGEN combat continuously. You influence their priorities, introduce attacks,
push their limits and play reversals through a compact three-card hand.

The central promise is: the draw is uncertain; a legal card's activation is
understandable and reliable; the resulting fight remains exciting to watch.
No turn system, collectible progression, real-money economy, deck-construction
screen or tournament mode is required for v0.1. Existing modes keep their rules.

Dolmexica only supports 1v1. Three-fighter squads are implemented by a mode-level
relay of separate 1v1 bouts, not engine teams, tag, simul or simultaneous 2v1.
True multi-fighter battles are outside this implementation. A comeback means
your last fighter beating the opponent's remaining fighters across successive
bouts. This constraint must be communicated honestly in UI and documentation.

## 2. Research and what is adapted

| Source | Observed principle | Legends adaptation |
|---|---|---|
| Pokémon TCG official rules | Cards have readable roles, named fields, persistent board zones and explicit effect text. | Distinct family icon, rarity mark, short effect, activation label and a separate Resolve slot. No Energy attachments, evolution chain or turn sequence. |
| Pokémon's Scarlet & Violet aesthetic article | Special illustration rares use full-art illustrations portraying the character/environment; visual treatments can be variants. | Rarity controls art coverage and background detail. Highest rarity is full art. Presentation rarity and effect parameters are separate data fields. |
| Yu-Gi-Oh! official conditions/activation/effects guidance | Eligibility, payment/targeting and resolution are separate concepts. | Explicit card states, validation before commitment, visible windups and defined interruption rules. No turn-based chain stack or manual response pauses. |
| Dragon Ball Legends official battle guide | Live battles use card-triggered actions and Ki; choose three battle fighters; conditional support effects also exist. | Live card interventions plus an ordered three-fighter relay. No manual attack-card combo spam and no copied Ki/vanish system. |
| Item Asylum's official description | Random items arrive in known functional slots. | Clear card roles and a useful guaranteed opening role, while later draws remain mixed. No unrelated weapon/meme dumping. |

Sources, consulted 2026-10-27:
- https://assets.pokemon.com/assets/cms2/pdf/trading-card-game/rulebook/swsh8_rulebook_en.pdf
- https://www.pokemon.com/uk/news/pokemon-tcg-scarlet-and-violet-revamps-pokemon-tcg-card-aesthetic
- https://www.yugioh-card.com/eu/play/understanding-card-text/part-3-conditions-activations-and-effects/
- https://www.yugioh-card.com/en/rulebook/
- https://dble.bn-ent.net/en/howtoplay.html
- https://www.roblox.com/games/5670218884/item-asylum

These are inspirations, not claims that those games use our odds, timing or AI.
High rarity is not universally synonymous with competitive strength in physical
TCGs. In this mode it signifies a scarcer, more elaborate, higher-impact effect
with explicit limits; common cards must remain useful and sometimes preferable.

## 3. Complete match flow

1. Main menu -> Legends -> brief controls/rules -> select three distinct fighters.
2. Choose squad order. There is no in-bout manual switching in v0.1.
3. CPU selects an ordered squad from the installed Legends-compatible roster.
4. Build each coach's eligible card pool and seed its random stream.
5. Deal three opening cards: one Resolve, then two cards from the full eligible
   pool restricted to Common/Rare. No duplicate IDs in the opening hand.
6. Opening screen allows attaching the Resolve to one of your three fighters.
   The CPU does the same. The equipped Resolve leaves the hand; normal Hype
   draws refill later. Playing it now gives an immediate, understandable identity.
7. Start the first 1v1 bout. Both fighters are CPU-controlled. Coach inputs go to
   Legends, never to normal movement/attack inputs.
8. Fight -> KO/timeout -> short relay interstitial -> next eligible bout.
9. Eliminate all three opponents to win. Results summarize useful card moments,
   cards drawn/played and the squad outcome. Rematch, squad select or main menu.

Bout rules: one elimination, no best-of-three submatch; 90-second limit initially.
Winner keeps its remaining HP fraction. Incoming fighter starts at full HP.
Native power starts at zero for a new bout unless a validated character adapter
requires another safe initialization. This rule is enforced after initialization,
not by blindly overwriting variables every tick. No free between-bout healing.
Temporary effects expire at the end of each bout. Attached Resolve remains on
the surviving fighter. Hand and Hype progress carry across the relay; all draws
and coaching timers pause during transitions. Queued uncommitted cards return
to Ready; nothing is allowed to target the incoming fighter accidentally.

Timeout compares current HP fractions, not raw HP. The lower fraction loses its
fighter; exact tie eliminates both. Simultaneous KO also eliminates both. If both
squads become empty together the encounter is a draw. Pending damage must settle
before the mode declares a result. Never resurrect a fighter already marked KO.

## 4. Exactly four card families

| ID / label | Role | Lifetime | Primary targeting |
|---|---|---|---|
| resolve / Resolve | Persistent game plan: preferred spacing, attack selection, resource priorities or conditional trait. | Until replacement or fighter elimination; one attached per fighter. | Own active fighter; opening screen can choose any squad member. |
| secret_arts / Secret Arts | Card-owned offensive opportunity: projectile, rush echo, tether or mapped signature action. | One execution, then discard; resulting effect has a bounded lifetime. | Opponent in the current bout. |
| awakenings / Awakenings | Temporary self enhancement, with defined caps and possible drawback. | Named timed buff; only one Awakening active per fighter. | Own active fighter. |
| plot_twists / Plot Twists | Special rule intervention: recovery, card manipulation, traps or time stop. | One-shot, timed effect or armed trigger, explicitly specified per card. | Explicit self/opponent/match scope. |

Family and rarity are independent. Legendary is not a fifth family. Healing,
traps and draw manipulation remain Plot Twists. Do not add submenus or extra
families to accommodate an individual reference.

Resolve replacement occurs atomically: remove the old Resolve's modifiers and
attach the new one. An Awakening cannot overwrite another Awakening; its card
is temporarily unplayable until the slot clears. No hidden buff stacking.

## 5. Hype, draws and controlled randomness

One card resource for v0.1: Hype generates draws. No additional Coach Points/Ki
currency. Native fighter power remains part of that fighter's own combat rules.
Cards use conditions, cooldowns and stated drawbacks as their limits.

Simulation is 60 fixed ticks/second. Hype has 900 integer units:
- +1 per eligible combat tick: a guaranteed draw every 15 active seconds.
- +60 on a meaningful exchange event: a knockdown caused, a reversal connected,
  or a completed defensive sequence that returns the defender to control.
- Bonus gain capped at +120 per rolling 60 combat ticks per coach. Deduplicate
  by exchange ID, including helper/projectile ownership; never reward every hit.
- No Hype from self-inflicted strain, healing, card-only damage, discarded cards,
  attached Resolve changes or draw effects. No card effect can farm itself.
- Hype pauses during intros, transitions, pause, KO and the global ZA WARUDO lock.
- At 900: spend those units and mint one normal draw ticket. At most one normal
  ticket may wait. If it cannot be delivered, Hype remains capped until it can.

Hand capacity is three card instances. Draw tickets deliver FIFO as slots open;
an Armed/committed card still reserves its slot until commitment/removal.
Bonus draw effects may add up to two bonus tickets, for a total queue capacity
of three including the normal ticket. All outstanding draws are shown by a small
count badge. Never replace a card silently or open a forced modal during a fight.

Rarity budgets for ordinary draws: Common 55%, Rare 30%, Epic 12%, Legendary 3%.
Choose rarity among eligible nonempty buckets, renormalizing their configured
weights; then choose an eligible card uniformly within that bucket. Do not apply
the rarity weight independently per card, which changes odds as the catalog grows.
Only one Legendary draw per coach per encounter. After drawing one, remove that
bucket for that coach even if the card is discarded. No duplicate ID already in
hand; exclude an identical currently equipped Resolve and exhausted unique cards.

Eligibility means authored, tested capability support for the current match,
not that its momentary activation condition is satisfied. A heal may be drawn at
full HP and saved. A card must not be drawn if the mode has no safe implementation
for its required hooks. No silent fake substitute when a reference cannot work.
At least one common safe card must remain eligible or Legends cannot start.

No pity system for v0.1; keep odds measurable before adding hidden adjustments.
Seeded draws are reproducible independently of cosmetic effects. Log seed, pool
version, draw index and selected ID. This does not promise deterministic replay
of all existing MUGEN character scripts or the whole engine.

## 6. Activation, latency and interruption

State machine:
`Ready -> Reserved/Armed -> Windup/Committed -> Active -> Resolved -> Discard`.
Rejected input stays Ready. A waiting card displays ARMED plus the reason.

- Acknowledge accepted input on the next simulation tick; target visible feedback
  within two rendered frames. Measure actual latency; never call this guaranteed
  hardware performance before testing.
- Only one reservation per coach. Normal attack reservations last at most 60
  combat ticks; they wait for a declared legal opening, not arbitrary AI whim.
- Before commitment: validate alive, target, capability, resource/slot limits,
  and card-specific conditions. A rejected/expired reservation returns the card
  to Ready with no cost. It cannot remain secretly queued for a later bout.
- At commitment: consume the instance, pay any explicit cost, start the shared
  90-tick play cooldown. A draw may fill the freed slot after this point.
- A committed windup can be interrupted where the card specifies. It then loses
  its card/cost; this is the deliberate risk, communicated by the card text.
- Timed buff duration starts on actual activation, not while waiting in hand.
- Instant cards run at the next legal event boundary. They never rewrite an
  arbitrary ongoing MUGEN state. No unlisted hitstun cancellation.
- Card effects do not require AI random command selection to accept their input.
  They still respect legal action windows and their authored windups.

Use a mode clock, per-fighter action clocks and explicit pause reasons. Time stop
counts down on the mode clock while the target's action clock is frozen. Buffs
owned by that target freeze with its action clock; the caster's buffs advance.
Hype pauses for both coaches during the time lock. Both coaches' card activation
is locked while time stop is active, preventing additional stacked card casts.

Collect human and CPU coach intents before mutation on a tick. Resolve legal
simultaneous intents with a documented seeded/alternating tie-break, not a fixed
P1-first advantage. A second conflicting exclusive world effect returns to Ready
before commitment. Log the arbitration. KO state from the previous tick always
prevents activation; finish this tick's actual hits before declaring its KO.

## 7. The coaching layer and existing MUGEN AI

Source inspected: Dolmexica `a6d63e9`, `ai.cpp`. Its generic AI chooses movement
from distance/state, attempts guards with a difficulty-dependent probability and
injects character commands at randomized intervals. Custom CMD/CNS state logic
then evaluates its own conditions and may implement a separate authored AI.
There is no universal built-in aggression/strategy setting we can simply change.

Implement a Legends-only bridge with:
- `CombatSnapshot`: living state, grounded/airborne, control/cancel eligibility,
  opponent distance and move state, HP fractions, native power, active card tags,
  current bout and stable fighter IDs. Obtain through typed engine APIs.
- `CoachProfile`: desired spacing band, advance/retreat preference, guard bias,
  native power reserve and weighted **tagged** move opportunities.
- `CharacterAdapter`: validated capabilities and optional tagged actions such as
  safe poke, approach, anti-air, punish, projectile, super. No guessed state IDs.
- `CardDirector`: ownership, draw, hand, validation, reservations, timed effects,
  event arbitration, relay state, card-opponent policy and logging.
- `ModifierRegistry`: source-tokened stat/priority changes with explicit lifetime;
  stacking/caps and cleanup never depend on editing a character variable number.

Resolve modifies choice weights within legal candidates; it does not increase
AILevel, force all probabilities to 100%, reveal hidden future actions or cancel
unsafe states. Clamp generic guard probability to a tested range, initially
15-85%. For characters with their own AI, map coach signals into a curated adapter
or mark the affected capability unsupported. Do not override every ChangeState
controller or silently claim generic AI weights affect custom logic.

Secret Arts should first use card-owned echo effects with separate original art,
owner attribution and hit limits. They are not a second character/team member.
Where a verified adapter exposes the correct native move, it may use that move
at the same declared legal boundary instead. Do not force all fighters to perform
Chidori by calling Sasuke's state number on Goku. Universal crossover powers are
allowed, but animation and physics need a safe shared implementation.

Unsupported characters may remain playable in ordinary modes. A Legends roster
is a runtime capability-filtered view, without changing roster.json. Show clear
compatibility information before selection, never silently remove installed
fighters from the normal roster. Start with two verified adapters for the vertical
slice, then expand to the 22-fighter inventory through actual tests.

CPU coach uses the same hand, odds, eligibility, cooldowns and restrictions. It
evaluates public combat state and its own cards every 15 ticks with an additional
seeded 6-12 tick reaction delay. No reading the human's hidden hand, future draws
or untelegraphed input. Test it without granting different resources.

## 8. Starter set: twelve authored cards

The machine-readable authority is `tools/legends/catalog.json`. This table is the
readable design. All cards are crossover interventions, not canon power rankings.

| Card | Family / rarity | Initial behavior | Constraint / risk |
|---|---|---|---|
| My Ninja Way | Resolve / Common | Prefer close pressure and approach opportunities. | Slightly lower guard preference; legal moves only. |
| Saiyan Pride | Resolve / Rare | Conserve native power for strong confirmed punish opportunities. | Avoid wasteful supers, not a free damage increase. Adapter required. |
| Scarlet Resolve | Resolve / Epic | Prefer measured counterplay after observed whiffs; modest guard bias. | Cannot react to hidden future actions or perfectly counter everything. |
| Chidori | Secret Arts / Common | Arm a short lightning-rush echo at the next grounded legal opening. | 60-tick reservation; 10-tick interruptible windup; can miss/block. |
| Spirit Gun | Secret Arts / Common | Fire a readable straight energy echo projectile. | 12-tick interruptible startup; one hit; no guaranteed tracking. |
| Bungee Gum | Secret Arts / Rare | A single-hit tether shot; on connection briefly limits separation and pulls. | Miss/block gives no attachment; never teleports or force-changes state. |
| Kaio-ken | Awakenings / Rare | 6 s of +20% card-registry attack multiplier and stronger approach preference. | 1% max-HP strain per second, cannot directly KO caster; no animation-speed hacks. |
| Bankai | Awakenings / Epic | 6 s of +15% attack and +25% validated native power gain. | No automatic character transformation; aura treatment only unless adapter supports form. |
| PLUS ULTRA | Awakenings / Epic | Below 35% HP, 5 s of +10% attack; reduce next two received hits by 35%. | One use per fighter/encounter; does not revive or erase hitstun. |
| ZA WARUDO | Plot Twists / Legendary | 18-tick telegraph, then 72-tick opponent-owner time lock; includes its projectiles/helpers. | Damage cap 20% target max HP ends lock early; no card casts during lock; one Legendary draw/coach. |
| Senzu Bean | Plot Twists / Common | Recover 12% max HP after a 30-tick recovery windup. | Grounded/control required; interrupted by a hit; no revive. |
| Pot of Greed | Plot Twists / Rare | Draw two through the bounded ticket queue. | One successful activation per coach/encounter; generated draws grant no Hype. |

Time stop is a difficult engine effect, not a SuperPause name swap. Freeze enemy
ownership consistently across fighter movement, animations, timers, helpers and
projectiles; suppress their frozen offensive collision while locked. Expire and
restore everything atomically, including KO/interruption/mode exit. If the engine
cannot support this safely, mark the card disabled and report why; do not ship an
immobilization debuff claiming to be complete time stop.

Canonical-reference research is in `reports/legends-research.md`. Numerical effects
are original balancing adaptations and may intentionally differ from fiction.

## 9. Rarity and art direction

Four rarity tiers, independent of the four families:

| Rarity | Printed identifier | Illustration treatment | Background detail |
|---|---|---|---|
| Common | C + one inset pip | Compact framed illustration, about 40% of the face. | Simple two/three-layer setting; strong recognizable subject. |
| Rare | R + two pips | Larger window/partial extension, about 55% of the face. | More context and one distinctive effect, restrained foil edge. |
| Epic | E + three pips | Extended art behind some framing, about 75% of the face. | Multi-layer dramatic scene, stronger effect composition. |
| Legendary | L + four pips | **Full art across the complete face**, including background behind title/rules overlays. | A fully composed narrative scene with the richest background, depth and fine pixel detail. |

ZA WARUDO is the starter Legendary/full-art card. Future Legendary cards in any
family use that same full-art rule. Never make the only difference a gold border.
Keep family icon and rarity shape readable over full art; use darkened title/rule
backplates, not illegible text on particles. No borrowed Pokémon/Yu-Gi-Oh! frame,
font layout or logo. Special visual treatment does not add unlisted effects.

Aesthetic: original hand-pixelled anime arcade illustration, closer to detailed
Neo Geo/CPS2-era sprites than literal NES restrictions. Consistent pixel density,
shading ramps, cream/navy materials, restrained orange/teal accents and accurate
costume colors. No random city skyline, generic mascot or unrelated smooth anime
poster. Portrait art is authored at 128x192; card faces at 128x192 with standalone
illustration and frame layers. Do not put rules text into generated illustrations.

Family roles: Resolve teal/crest, Secret Arts orange/slash, Awakenings red/flame,
Plot Twists violet/hourglass. Icons and labels accompany color. Rare/Epic/Legendary
trims use brighter material accents while retaining the family identifier.

## 10. UI inventory, controls and animation

Authoring sizes are sprite sizes, not a mandate to enlarge the engine's native
coordinate system. Layout is 320x240 logical with a 4:3-safe display at 960x544.
Review both actual window and handheld-size screenshots. Keep combat visible.

Required art/state assets:
- Four family frames, four rarity treatments and a reversible card back.
- Twelve card illustrations, twelve composed preview faces and small hand tiles.
- Four family icons, rarity markers, target/active/queued/locked icons.
- Three-slot collapsed hand dock, focus outline, Armed/blocked/cooldown overlays.
- Hype background/fill/segments, completed-draw indicator, pending draw count.
- Resolve socket and equipped badge; Awakening timer rail; time-stop lock indicator.
- Three-fighter squad rails with active/reserve/KO states, selection/order markers.
- Opening-deal tray, target highlight, relay and result panel bases.
- Draw/reveal/commit/spark animation sprites and a Legendary reveal accent.

In battle: Square/Triangle/Circle play the corresponding visible card. L held
inspects the focused card; D-pad shifts inspection focus without steering the
fighter. R held 0.5 s discards that focused Ready card, using the same shared
cooldown and granting no Hype. Cross is ordinary confirm on setup/results; during
battle it may close inspection. Actual input mapping must be verified against
the engine/Vita abstraction, not legacy PC scan codes. Touch is optional only.

The collapsed dock initially uses 86x26 tiles at x=14/117/220, y=207. Show family,
art thumbnail, short name and state, not unreadably tiny full rules. Hype rail is
at x=85,y=199,width=150,height=5. Expand one 80x120 inspection view near the edge
only while requested; do not obscure the center of the fight with permanent cards.
Validate occlusion against actual stages, HUD and fighter feet before locking
coordinates; these are layout targets, not verified in-game screenshots.

Focus motion: 6-9 ticks. Draw settle: 10 ticks. Normal reveal: 12 ticks, no pause.
Legendary reveal: up to 24 ticks in the dock, no mandatory full-screen interruption.
Use small reusable spark/foil layers. No hundreds of full-screen animation frames.
Draw, focus, commit, blocked, expiration and Legendary cues need distinct original
or authorized sounds. This first kit defines cue IDs, not finished audio files.

All rules labels, numbers and changing states remain runtime text/UI. The composed
PNG cards are review previews and optional collection views, not baked interactive
HUD logic. Native font rendering supports fixed colors; no font-bank assumptions.

## 11. Native implementation contract

Create a separate `GAME_MODE_LEGENDS` and mode-owned session/controller. Reuse
normal match loading and callbacks; isolate every new hook behind that mode.
Preserve the classic CPU behavior, input and roster when Legends is inactive.

Suggested components (names are proposals, not existing APIs):
`LegendsSession`, `RelayDirector`, `CardCatalog`, `DrawDirector`, `CardRuntime`,
`CoachBridge`, `CharacterAdapter`, `ModifierRegistry`, `EffectOwnershipScope`,
`LegendsHUD`, `CpuCoachPolicy`, `LegendsTelemetry`.

Card schema must include stable ID, revision, family, rarity, display/short text,
activation kind, targets, conditions, required capabilities, reservation/windup,
interrupt rules, effect IDs/parameters, duration, per-fighter/per-encounter limits,
icon/frame/illustration references and source-reference provenance. Validate
unknown IDs, duplicate IDs and unsupported enums before starting a match.

Read-only combat snapshot -> submitted intent -> reservation validation ->
arbitration -> commit -> scheduled effect -> safe engine action -> logged result.
Use stable fighter/bout IDs; never retain raw pointers across character unloads.
Register cleanup at cancellation, KO, relay, timeout, rematch and mode exit.
Do not patch arbitrary character var slots, AILevel or undocumented state IDs.

Configuration is data-driven; numerical balance must not require editing character
archives. Public repo contains only original code, docs and text manifests.
Generated art is external/ignored and reproducibly fetched or supplied locally.

## 12. Performance and asset budgets

Initial extra card/UI decoded-texture budget: <=4 MiB resident, measured including
padding/mips and actual native uploads. This is an allocation target, not a current
Vita measurement. A 128x192 RGBA card is 98,304 bytes; twelve are 1.125 MiB before
atlas padding or duplicated variants. Do not load 1x/2x/review PNG duplicates into
runtime. Share frame/effect sprites and one atlas page where supported.

Do not confuse compressed file bytes with decoded memory. Existing engine heap
is 96 MB; a larger heap is the engine lane's separate measured change. No MP3,
subtractive blending or binary SELF/VELF patching. No claim of 60 fps until measured
with real gameplay. Do not install on hardware; owner tests Vita.

## 13. Implementation order and acceptance

1. Audit source/mode lifecycle; implement a separate Legends entry and 1v1 CPU
   fixture with reliable return-to-menu. Prove classic modes unchanged.
2. Catalog validation, seeded draw/hand/ticket system, opening deal and HUD with
   four families. No need for all card effects to demonstrate the state machine.
3. CoachBridge with two verified adapters. Implement My Ninja Way and one attack
   echo. Demonstrate measurable strategy change while legal-state rules hold.
4. Registry and recovery/buff cards; validate costs, interruption and cleanup.
5. Relay persistence and CPU coach using identical rules. Implement the full set
   progressively; explicitly disable cards whose capabilities are absent.
6. ZA WARUDO only after owned-effect freezing and restoration tests pass.
7. Polish art/reveals/sound and audit the supported roster. Record native footage.

Required meaningful tests:
- Seeded draws/rarity fallback, opening guarantee, duplicate filtering and limits.
- No draw/bonus loops, full-hand pending tickets, Pot of Greed overflow behavior.
- Input rejected vs reserved vs committed; expiration; windup interruption; cost
  charged exactly once; effect duration starts on activation.
- Simultaneous intents/KO, invalid targets, loading/rematch cancellation.
- Resolve/awakening replacement/caps; modifier removal after every exit path.
- Custom AI respects or explicitly lacks each adapter capability.
- Time-stop fighter/helper/projectile cleanup; no stuck state after KO or timeout.
- Three-fighter relay, HP carryover, timeout fractions and double-KO outcomes.
- Original modes remain unchanged; repeated encounters do not leak memory.

Deliver Windows native recordings and measurements. Emulator results and live
hardware are labeled separately. The owner performs Vita installation/testing.

## 14. Handoff boundary

This document, starter catalog, original art kit and Claude prompt do not implement
Legends in the engine. Claude is asked to build that mode from source. UI work in
PR #7 and other engine/roster lanes may have advanced; inspect their current state
and coordinate before integrating. Keep the main-menu redesign and Legends mode
separate, with a small explicit integration seam for the new entry.
