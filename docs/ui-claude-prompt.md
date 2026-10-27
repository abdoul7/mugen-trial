# Claude implementation prompt: modern motion, authentic arcade art

Copy the prompt below into Claude with the latest menu screenshot and the owner's
arcade sprite reference. Research notes follow it. This is an implementation task,
not a request for another set of AI concept boards.

---

You are taking ownership of the native menu/UI redesign for **Jump Force Vita**,
a 1v1 community M.U.G.E.N game running on Dolmexica Infinite for a modded PS Vita.
Repository: https://github.com/abdoul7/mugen-trial .

Read AGENTS.md, TODO.md, NOTES.md, handoff/CLAUDE.md and handoff/UI.md first.
Inspect the actual current checkout and active motif before changing anything.
Preserve other agents' work. Continue the UI branch or establish the correct UI
branch for the current checkout; one task, one branch, one PR. Only integration
edits roster.json. The owner has authorized pushing the completed source work.

## What I want

Make the menus feel like a newly released fighting game with the tactile,
nostalgic arcade/anime sprite art of the game itself. The screenshot's oversized
logo, boxed flat list and weak focus feedback look dated. A moving background
alone will not solve this. Improve layout, hierarchy, responsiveness, navigation,
transitions and audiovisual feedback together.

When I say "8-bit arcady PS Vita", use my actual reference: detailed hand-pixelled
fighters and stages, cohesive shading, expressive sprites and deliberate palettes.
Do not reduce everything to crude NES shapes, huge 5x7 lettering, a generic pixel
website, a dashboard or smooth HD anime posters. Characters, stages, effects,
portraits and UI must belong to the same game. Keep current **Jump Force Vita**
branding for this pass; "Jump Rift" and earlier generated boards were not approved.

## Research before implementation

Inspect real menu footage/screens from **Tekken 8**, **Street Fighter 6 Fighting
Ground**, and **Guilty Gear Strive**. Use official material where possible; cite
the actual clips/pages and timestamps you inspect. Study focus movement,
selected/unselected hierarchy, contextual information, transition rhythm,
background composition, controller prompts and audio cues. Take interaction
principles from these games and translate them into our sprite aesthetic.
Do not copy their assets, 3D presentation, online services or monetization UI.
Distinguish observations from your proposed adaptations; do not claim exact
animation timings from a text article.

Use these official starting points:
- Tekken main-menu character display: https://en.bandainamcoent.eu/tekken/news/tekken-8-patch-108
- SF6 Fighting Ground modes: https://game.capcom.com/manual/SF6/en/switch2/page/6/1
- Capcom's mode overview: https://blog.playstation.com/2023/04/20/street-fighter-6-showcase-new-gameplay-details-future-fighters-revealed-and-demo-launched/
- Strive menu, contextual help and Quick Start updates: https://www.guiltygear.com/ggst/en/news/post-2851/

Keep the research bounded, then implement a complete functional vertical slice.
Do not burn the session generating many unrelated mood boards.

## Main-menu design and motion

1. Give the screen one clear focal area and a stable navigation area. Reduce the
   logo's dominance so the actual selected action leads. Design all available
   choices, including options/return paths; don't make them disappear below an
   arbitrary five-item crop. Verify which existing modes work before relabeling.
2. Replace the weak rectangle cursor with a clear arcade selection treatment:
   coherent accent, framing and contrast, supported by a short responsive motion.
   The selected item should be unmistakable without relying only on color.
3. Use a small layered pixel-art background with purposeful depth: slow base
   movement, restrained foreground atmosphere and an occasional accent. Keep
   motion away from text. Reuse real authorized game art where appropriate;
   do not invent a random city skyline or a Goku-like mascot for a crossover game.
4. Add state-driven feedback: selected-mode name/short description, useful
   controller hints and a preview/illustration region only when it adds meaning.
   Every label must describe a real working mode. No fake online/store/rank tabs.
5. Define a consistent motion language. Starting targets, to be tuned in-engine:
   focus movement around 100-150 ms; confirmation/scene change around 150-250 ms;
   subtle idle loops around 4-8 s. These are design targets, not measured facts or
   excuses to delay input. Handle rapid repeat and reversals without queued,
   laggy animations. Keep pixel edges stable and avoid fractional-scale shimmer.
6. Pair movement, confirm and back with distinct short sound cues using existing
   authorized sounds or original assets. Avoid restart spam during held input.
7. Keep navigation usable during motion; back/cancel must consistently return
   to the previous state. Don't force a long intro every time the menu opens.
8. **Remove the entire blue strip at the bottom of the menu.** Remove its
   background rectangle, "Dolmexica Infinite 1.8" text on the left, and the
   date/presenter text on the right. Reclaim the space for the game's layout or
   controller hints. Do not conceal the strip behind an image. These elements
   are hardcoded in `titlescreen.cpp` around lines 345-352 in the inspected engine;
   locate the exact function in the version being built and remove/disable the
   whole footer cleanly. Preserve required engine attribution/license information
   in the project's credits/docs.

## Character select and related screens

Carry the same materials, typography, spacing, color roles and transition rhythm
through character select, stage select and versus. Preserve all 22 current
fighters plus randomselect, and allow the grid to grow safely. The current known
bugs are portrait overflow and overlapping mode/title text; fix those first.

Use real installed portraits, with bounded small and large portrait regions and
consistent framing. Audit high-resolution exceptions, offsets, palettes and
SFF formats; do not assume every small portrait is 25x25. Smooth the cursor/focus
treatment and selected-fighter preview without obscuring the portraits or
introducing input lag. Support the one-player and two-selector states correctly.
Do not show fake opponent information in an engine state that has none.

## Implement within the actual engine

This is a native Dolmexica game, not a browser prototype. No HTML/CSS overlay,
Electron shell, game-engine replacement or invented Ikemen-only configuration.
First identify what motif DEF/AIR/background layers can genuinely do and what
requires native C++ changes. Background loops are not a substitute for interactive
focus interpolation or context-driven descriptions. Implement the smallest
focused native extension where needed, preserving the existing menu callbacks
and controls. Keep changes reproducible as source/patches; never binary-patch a
shipped SELF/VELF. Coordinate with the engine lane if rebuilding is necessary.

Target a 960x544 Vita display with the engine's 4:3-safe layout and sensible native
sprite coordinates. Maintain a 60 fps target. Use small reusable layers rather
than hundreds of full-screen frames. Measure decoded texture cost and process
behavior; compressed archive size does not represent memory use. No MP3,
subtractive blending, font-bank assumptions, teams/tag or unsupported features.
Test real handheld-size legibility. Respect the current heap budget.

Higgsfield may help create a carefully specified original pixel-art asset if
needed, but generated art must match the existing sprites and be reviewed at
native resolution. UI labels, hitboxes, focus states and navigation must remain
functional engine elements. Do not bake the entire interface into a wallpaper.

## Verification and delivery

Build from source and test the actual full roster, not the old 8-fighter fixture.
Verify every roster cell/portrait is visible, the cursor can reach every entry,
rapid navigation stays correct, and confirm/back/held input work. Check options,
character and stage selection, versus, a playable fight, and return-to-menu.
Fix clipping, overlapping text, missing sprites, palette changes, broken menus
and load errors before declaring the redesign usable.

Capture a short **actual engine** recording showing background loops, several
selection changes, confirmation and back navigation, plus stills at 960x544.
Report tested modes, frame-rate observations, asset-memory estimates and what
remains untested. Windows or emulator success is not a hardware Vita test;
installation and on-device testing belong to the owner.

Commit only our own source, tools and text reports. No game art, screenshots,
downloaded archives or VPKs in this public repo. Push the UI branch and open a
PR with a concise verified/untested section. Update AGENTS.md and the UI handoff
so another agent can continue. Do not stop at a plan, a mockup, or "it should work."

---

## Research interpretation

The official Tekken 1.08 notes confirm character-centric menu presentation is a
supported feature. The applicable idea here is giving the menu a game-relevant
visual anchor; its 3D assets or customization system are not requirements.

Capcom's official material groups traditional modes in Fighting Ground. The
applicable idea is understandable mode hierarchy and short routes to play, not
adding SF6's unsupported online/team modes to Dolmexica.

Arc System Works' official 2.00 notes confirm a renewed main menu, mode-select
voice updates, help-guide access and Quick Start changes. The applicable ideas
are coordinated feedback, contextual explanations and quick access to play.

The proposed timing, layer composition and focus behavior above are design
recommendations. Text sources alone do not verify a game's easing curves or
animation durations; Claude should inspect footage before describing those.
