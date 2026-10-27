# Legends design and first art kit — 2026-10-27

## Delivered scope

- Full mode design: `docs/legends-design.md`.
- Claude implementation prompt: `docs/legends-claude-prompt.md`.
- Twelve data-authored starter cards, three per family: `tools/legends/catalog.json`.
- Four original Higgsfield illustration strips, split into twelve 128x192 native
  illustration assets with nearest-neighbour sampling and 96-color quantization.
- Twelve composed card review faces; Legendary ZA WARUDO is full art. The
  Common/Rare/Epic/Legendary comparison sheet demonstrates visual templates only,
  not four mechanically different versions of that card.
- Sixteen reusable family/rarity frame templates and a card back.
- Three runtime atlas pages: text-free card bases, UI primitives and small VFX.
- Icons, rarity marks, controller glyphs, hand states/focus, Hype/draw indicators,
  Resolve/Awakening widgets, squad states, deal/relay/result panels.
- Small projectile, lightning, tether, aura, heal, time-ring, draw-spark and
  reveal-edge sprites; these are images, not working damage/time-stop handlers.
- Review sheets, a labelled HUD layout concept and an animated Legendary reveal
  preview. The preview is not native engine footage.

## Local deliverables

Output directory:
`C:\Users\abdou\Documents\Codex\2026-10-27\jump-force-vita-onboarding-a-m\outputs\legends`

Art source directory: ignored `source/legends-art/` within this checkout.
The deliverable kit also includes source sheets for offline regeneration.
No PNG/GIF/ZIP, engine binaries or game assets are committed to git.

Rebuild using already supplied source sheets:

```powershell
.venv/Scripts/python.exe tools/build_legends_kit.py --out build/legends-art-kit
.venv/Scripts/python.exe tools/validate_legends_kit.py build/legends-art-kit
```

To retrieve only the recorded original generated images when missing:

```powershell
.venv/Scripts/python.exe tools/build_legends_kit.py --fetch --out build/legends-art-kit
```

No generation is submitted by that script. It fetches the exact recorded URLs and
checks SHA-256. If a URL expires, supply the matching source sheets locally using
`--source <folder>`. Do not regenerate automatically and pretend it is identical.
The original live jobs are listed in `tools/legends/art_sources.json`.

## Higgsfield provenance

Model: `gpt_image_2_5`. Four jobs completed successfully:

| Family sheet | Job ID | SHA-256 |
|---|---|---|
| resolve | 4e63e9d3-f6a9-433e-a535-9cddfcb137c0 | b7994d6ba38064d73fbfd8137fb7ffa080607b9b22bf6c22f36faca09ca33034 |
| secret_arts | 03dafb25-cb63-4f1d-8736-c70398f0db66 | 287e21476cd309a06f62ee279521eecbb501413c1a922b72e7c1ecd778fdc14e |
| awakenings | 59949fc9-7de1-4c50-8c63-31e5869a0943 | 1584740269edf72695a0320a5c7c2d1c812949a0742bc322bfc819d087b49485 |
| plot_twists | 017e3e4e-1475-4832-b5ae-f1279507ab1a | bb1f93a93e3c0aa9584f131cc505f46408056fa5d797af3aac560f2349f6d51c |

The service coerced the requested 2:1 ratio to 16:9; returned sheets are 1344x752.
The builder records exact third-panel slices and normalizes their aspect ratio
to native 128x192. Card-specific focal positions keep faces visible inside the
different rarity windows. All four source sheets and final card sheet were
visually inspected. No rules text was generated into the illustrations.

## Asset verification

`tools/validate_legends_kit.py` passed for the delivered kit:
- 12 unique cards, 4 families and all 16 family/rarity frame templates.
- Catalog fields/rarity weights/card outputs checked.
- 12 card-base, 50 UI and 45 VFX atlas regions bounded and non-overlapping.
- Individual UI/VFX visible pixels match their atlas regions over light/dark backgrounds.
- Animation references resolve and the Legendary GIF has multiple frames.
- Source image hashes match the recorded manifest.
- Python source compilation passed for builder and validator.
- Rebuilding offline from the source sheets included in the bundle reproduced
  all three runtime atlas PNGs byte-for-byte on this Windows environment.

Actual runtime atlas pixel allocation (RGBA, before native overhead):

| Page | Dimensions | Bytes |
|---|---|---:|
| cards_base | 512x1024 | 2,097,152 |
| ui | 512x256 | 524,288 |
| vfx | 512x256 | 524,288 |
| Total | | **3,145,728 (3.00 MiB)** |

This figure excludes native texture alignment/mips, fonts and engine overhead;
Vita upload memory is not measured. The design's initial full budget is <=4 MiB.
Do not load authoring templates, composed review cards and individual PNG exports
alongside their atlas equivalents. Text-free runtime bases take native labels,
numbers, state and timer overlays; the contact sheet is not a functional interface.

## Still to implement / verify

There is no Legends game mode, native card runtime, AI coaching adapter, relay,
CPU coach or working card effect in this delivery. The catalog contains capability
contracts, not functioning handlers. No engine fight or hardware test was run for
these assets. No finished audio files are included; the kit names the needed cues.
The HUD layout must be tested for occlusion with the actual current stage/HUD.
The owner performs Vita installation and testing. Numerical balance needs playtests.

The research, design, code-authored UI and original generated illustrations are
available for the next agent; prior rejected menu boards are not used as the
approved identity for these cards.
