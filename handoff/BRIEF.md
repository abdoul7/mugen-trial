# Brief — "Jump Force Vita"

## Intent

Build our own M.U.G.E.N fighting game that runs **natively on a PS Vita** (not streamed),
with:

- **Roster:** the *Jump Force* lineup (57 characters, 16 Shōnen Jump series).
- **Movesets:** taken from the characters used by the PC pack *The Best M.U.G.E.N 1.1
  (Beta 2)* by evil_dark_lxs — i.e. community M.U.G.E.N characters, JUS-era styling.
- **Look:** the same art direction as that pack (its 720p motif: menus, character-select
  grid, lifebars, HUD), re-laid-out for a 960×544 screen.

Why: the user likes that pack's presentation, wants a Jump Force roster, and wants it on
the Vita rather than a PC. They are willing to develop/port where necessary.

## Goals

- G1. A `.vpk` that installs and plays on a real Vita with Enso + VitaShell.
- G2. Jump Force roster, as many of the 57 as the hardware and asset availability allow.
- G3. Visual identity recognisably that of the source pack.
- G4. 1v1 versus + arcade against CPU, 60 fps target.
- G5. Everything reproducible from source/community assets — no ripped commercial art.

## Non-goals

- N1. 3v3 tag/simul. The engine cannot do it (teams were removed engine-wide).
- N2. The full 47.2 GB / 2069-character TBM pack.
- N3. Porting Ikemen GO (Go runtime has no Vita target) or Ikemen classic (months).
- N4. Netplay, story mode, osu mode, custom character creator.
- N5. Vita TV two-player parity.

## Anti-goals (would count as failure even if it "works")

- A build that only survives 1–2 fights before a heap crash.
- A "720p motif squeezed in" that loses readability at 960×544.
- Silent asset substitution that abandons the source pack's identity.
- Shipping something the user cannot explain or rebuild themselves.

## Constraints (measurements and their sources are in FACTS.md)

- Vita: 512 MB RAM + 128 MB VRAM; a homebrew app realistically gets ~200–260 MB.
- Dolmexica's Vita build pins its newlib heap at **96 MB** (`main.cpp`), which is the
  real ceiling for loading large sprites/stages. Raising it requires a rebuild (144 → 192 →
  224 MB, tested one at a time).
- Engine gaps: no teams/tag, no font banks, `RemapPal` only `source = 1,1`, no subtractive
  blending on Vita, MP3 unsupported, >4:3 clamped.
- Packaging: `.vpk` via `Dolmexica Infinite Make-your-own-game kit for Vita.exe` or
  `vita/make_vita.bat GameName TitleID Version`; TitleID exactly 9 chars.

## Decisions taken (with reasons)

| # | Decision | Reason |
|---|---|---|
| D1 | Engine = Dolmexica Infinite | Only native Vita M.U.G.E.N interpreter; MIT; active (source pushed Oct 2026); already proven by third-party ports (SF1MR Vita) |
| D2 | No Ikemen GO port | Go has no Vita/newlib runtime target — GC, scheduler, mmap/futex would all need porting first |
| D3 | 1v1, not 3v3 | Teams removed engine-wide; adding them to Dolmexica is a separate weeks-long C++ project, deliberately deferred |
| D4 | Style is copied as **assets**, not as an engine | The look is `system.def/sff`, `fight.def/sff`, `font/`, music. The bundled Lua/HLSL in the pack are stock Elecbyte 2013 samples, not style drivers |
| D5 | Rebuild the motif at 960×544 / 4:3 | 720p cannot run; select grid is 550×49 cells and must be re-laid-out |
| D6 | Rebuild engine rather than patch `.velf`, if the heap must grow | Patched SELF stops validating on retail firmware |
| D7 | Source characters from community archives | Legal/technical: no ripping from the commercial game; community chars are the norm in this scene |
| D8 | Test on Windows Dolmexica first | Same `assets/` tree; 30-second loop instead of reinstall cycles |

## Roster approach

The Jump Force list is 40 launch + 14 DLC + 3 free-update = **57** (see
`roster/jumpforce-roster.md`). Design target for M1 is 8–12 characters; full 57 is the
stretch goal. Measured evidence says the roster is the *cheap* part: the source pack's own
demo characters have **0.9–5.6 MB** sprite sheets, so 57 characters ≈ 200–300 MB of assets,
which is comfortably inside a `.vpk` on an SD2Vita card. Each candidate must pass
`tools/scan_mugen_build.py` before it is kept.

Character sources: mugenarchive.com, andersonkenya1.net (AK1). Prefer characters whose
`.def` says `mugenversion = win` or `1.0` and whose sprites are 4:3-era; reject 1280×720
localcoord characters, `trans = sub` effects, and multi-palette (`RemapPal` ≠ 1,1) costumes.

## Style approach

Copy from the extracted screenpack (`MANIFEST.txt` → `extract_screenpack/TBM 1.1 2020`):

1. Keep the **art**, discard the 720p **coordinates**: take `system.sff`, `fight.sff`,
   `fightfx.sff`, `font/`, `00/*.sff` and downscale to 960×544 (or 4:3 320×240 frames scaled
   up, which is often crisper with this art).
2. Rewrite `system.def` `[Select Info]` for a grid that suits 8–57 slots instead of 550×49,
   and rewrite every position/animation reference for the new resolution.
3. `fight.def`: keep the lifebar/powerbar/combo layout and art; drop sections Dolmexica
   does not support (full animation/text coverage in lifebars is incomplete).
4. Fonts: 9 external font `.def`s → Dolmexica-safe fixed-colour fonts.
5. Music: 7 MP3 tracks → OGG.
6. Skip entirely: `00/Intro.sff` (34 MB), ReShade, `OpenGL32.dll`, the stock Lua/HLSL.

Known-good fallback if the motif resists: ship with Dolmexica's stock motif and spend the
time on roster + movesets instead. Decide this by the end of M2, not open-endedly.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Heap crashes with real anime characters | High | Heap rebuild + per-character triage; keep `.snd` files trimmed |
| Motif downscale looks bad at 960×544 | Medium | Spike with 3 screens (title, select, fight) before doing all of it |
| Missing Jump Force characters in community archives | Medium | Substitute nearest equivalent; never rip from the commercial game |
| VPK packaging tool fails on this PC | Medium | Kit ships its own vitasdk exes; if they fail, run `make_vita.bat` steps manually and read `vita/build` logs |
| Roster grows past what a select grid can show | Low | ~100 characters were tested fine upstream; portraits cost load time, not memory |

## Open questions for the user (ask, do not assume)

1. **Roster scope for M1:** a focused 8–12 (faster, polished) or push straight for all 57?
2. **3v3:** if tags matter enough, is a months-long Dolmexica teams patch on the table, or
   is 1v1 final?
3. **Style fidelity vs schedule:** if the rebuilt motif looks worse than the pack, keep the
   pack's look approximated, or ship stock motif and prioritise gameplay?
4. **Distribution:** personal use only, or eventually shared publicly (affects credits,
   licensing, and asset sourcing)?
