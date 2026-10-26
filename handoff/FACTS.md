# Facts, measurements and sources

Everything here was verified during the research session (2026-10-26) either by reading the
engine's source, by fetching the pages listed, or by measuring the downloaded archives on
disk. Anything unverified is labelled as such.

## 1. The Vita hardware

| Fact | Value | Source |
|---|---|---|
| Main RAM | 512 MB | Sony Vita product spec (sonyinteractive.com press release, sony.com.hk spec sheet) |
| VRAM | 128 MB | same |
| Screen | 960 × 544 | same |
| CPU | 4× ARM Cortex-A9 | same |

Practical budget for a homebrew app: **~200–260 MB**, the rest belonging to the OS/GPU
(community consensus; treat as an estimate, verify with `sceKernelTotalFreeMemSize` at runtime).

## 2. The source pack ("The Best M.U.G.E.N. 1.1 Beta 2", evil_dark_lxs, 2020)

- Size **47.2 GB**, **2,069 characters**, **2,533 stages**, M.U.G.E.N **1.1**, **1280×720** hi-res, 32-bit.
- Author's own warning: *"The game for default starts at 2,8 Gb of memory and about 3,4 Gb
  crashes"*; recommended fix in the thread is editing `chars/` folder names; *"The next
  version will improve this RAM problem"* → later *"the next version will be in Ikemen Go"*.
- Download mirrors: MediaFire split archive `TBM 1.1-1.bin … -14.bin` (14 × 2 GB + `TBM 1.1.exe`)
  is live; the MEGA folder is now empty. Source: mugenfreeforall.com/topic/38810.
- Arithmetic: 3.4 GB demand vs ~256 MB usable ⇒ **~13× over budget**. Cannot be ported whole.

## 3. Dolmexica Infinite — the engine we are using

- Repo `github.com/CaptainDreamcast/DolmexicaInfinite`, MIT, ~33★, source pushed **2026-10-06**.
- Docs: `captaindreamcast.github.io/DolmexicaInfinite/` (site version 1.8).
- itch: `captaindreamcast.itch.io/dolmexica-infinite` — the download contains the Windows
  engine, the `assets/` tree, and the Make-your-own-game kits for Dreamcast/Web/**Vita**.
- Feature coverage: WinMugen → **M.U.G.E.N 1.1b**; where versions conflict, the older
  behaviour wins (Dreamcast memory legacy).
- Vita build history that matters: **1.6 removed the vitaGL dependency** in favour of
  vita2D ("much improved performance", "less random crashes") ⇒ `libshacccg.suprx` is no
  longer required, despite older guides and the itch FAQ still saying so.
- Vita changelog entries worth knowing: repeated "random crashing … it was a heap size
  thing" fixes; *"Some SFX improvements (vita sound improvements are ever-ongoing)"*.

### The memory ceiling (verbatim, `main.cpp` lines 38–40)

```cpp
// VitaSDK defaults the newlib heap to 32MB, not enough for large sprites like in stages (or Dream Fight story credits etc). 96MB seems to work, even with fragmentation.
extern "C" {
    unsigned int _newlib_heap_size_user = 96 * 1024 * 1024;
}
```

Raising it (144 → 192 → 224 MB) is the documented way to load bigger characters/stages.
Rebuild with VitaSDK; do not patch the `.velf`.

### Packaging (from `vita/CmakeLists.txt`)

- `set(VITA_TITLEID "DOLM00001")`, `set(VITA_VERSION "01.08")` — **TitleID exactly 9 chars**.
- `vita_create_self(...)` then `vita_create_vpk(... FILE ../assets assets FILE ../debug debug)`
  ⇒ **the whole `assets/` tree is packed into the VPK** and installed to
  `ux0:app/<TITLEID>/assets`, which stays writable through VitaShell (fast iteration loop).
- Links: `prism vita2d mikmod vorbisfile vorbis ogg png jpeg webp FLAC pthread z zstd drakonsound`
  plus the standard Sce* stubs.

### Engine limitations (from the official differences doc)

- **Teams and every team trigger / team controller removed** (not Vita-specific).
- Font banks removed → fixed colours 0 = white, 1 red, 2 green, 3 blue, 4 cyan, 5 yellow,
  6 magenta, 7 black, 8 light gray.
- `RemapPal` only with `source = 1,1`; disabled on helpers/projectiles.
- `data.ko.echo` removed; `[Video Win]`, `[Video Linux]`, joystick groups removed.
- **Missing on Vita specifically:** subtractive blending, trigger-parsing performance,
  graphical performance, display stretched (all "not implemented yet", not "impossible").
- 480p lifebars: add a `480p` folder inside `data/`.
- MP3 not supported on Dreamcast/Vita ("stick to ogg there").

### Evidence from the field

- `SF1MR Vita` (v1.1, 2025-01) — a Street Fighter 1 MUGEN remake shipped as a Vita port built
  on Dolmexica. Its notes: intro removed, "Versus mode cannot be fully utilized (because Vita
  is 1P)", endings removed, "Loading times may take a little while". Proof the pipeline works.
- Creator on character limits: *"there is no fixed upper limit … the highest character count
  I have tried is roughly 100"*; crashes are usually *"some file it can't find, or a problem
  with file names it can't parse"*.

## 4. Engine comparison (why not something else)

| Engine | Language | Vita status | Verdict |
|---|---|---|---|
| M.U.G.E.N (Elecbyte) | C, closed source, Win32 | none possible | No source, x86 binary, no Windows layer on Vita |
| **Dolmexica Infinite** | C++ + SDL-ish, MIT | **native build + vpk kit** | **chosen** |
| Ikemen GO | **Go** | none | Go has no Vita/newlib target (GC, scheduler, mmap/futex would need porting first) |
| Classic Ikemen / Ikemen-Plus-Ultra | C/C++ | none | 109★ fork, actively pushed; portable in principle via SDL2-vita, but a months-long project — out of scope |
| InfCat (PSP) | closed, 2006 | via Adrenaline | 10-character cap, 2006-era chars only, needs `StConv` per char |
| DOS M.U.G.E.N 1999 | DOS | via DOSBox on Vita | 1999 beta; no modern characters |
| Moonlight streaming | — | works today | Runs the real engine on a PC; not native |

## 5. The style package — measured on disk

Both archives were downloaded from the author's Resources page and extracted:

| Item | Size | Detail |
|---|---|---|
| `Screenpack TBM Last Beta 1.1 (x86)` | **97 MB** rar | the exact motif; MediaFire `2xz0qqzq4h31zfx/TBM_1.1_2020.rar` |
| `Screenpack TBIG Beta 2021 (x64)` | 492 MB | the same look built for **Ikemen GO 0.96.3**; MediaFire `lrf54bzu2fh5ave/…0.96.3.rar` |
| `Demo TBM Last Beta 1.1` | **719 MB** | 10 characters, 11 stages, playable build |

Extracted screenpack (`TBM 1.1 2020`, 115 MB on disk) — `Data/`:

| File | Size | Role |
|---|---|---|
| `00/Intro.sff` | 34.1 MB | intro art (skip for Vita) |
| `Fight.sff` | 18.3 MB | lifebars/powerbars/combo art |
| `00/GameOver.sff` | 8.1 MB | game-over art |
| `FightFX.sff` | 7.1 MB | hit sparks |
| `00/Title.sff` | 6.4 MB | title screen |
| `00/Versus.sff` | 3.9 MB | versus screen |
| `00/Select.sff` | 1.4 MB | select-screen art |
| `00/Victory.sff` | 0.8 MB | victory screen |
| `System.sff` | 323 KB | menu art (tiny) |
| `System.def` | 36 KB | **`localcoord = 1280,720`**, select grid **`rows = 550`, `columns = 49`**, dual cell sizes 26 and 53 px |
| `Fight.def` | — | 55 sections incl. `[Lifebar] [Powerbar] [Face] [Time] [Combo]` |
| `Font/` | 1.9 MB | ADAM, ADAM1, ADAM2, ADAMN, Continue, Hashtag, Title, Title2, Stages001, Stages002, Victory, DarkFlame, f-4x6 |
| 7 × `.mp3` | ~8.9 MB | title, select, versus, victory, intro, logo, gameover |

Full 187-file inventory with sizes and roles: `inventory/style-anatomy.csv`.

**Important:** the `*.lua` and `*.frag`/`*.vert` files in `Data/` are dated 2013-08-04 and are
**Elecbyte's stock M.U.G.E.N 1.1 Lua/HLSL samples**, not this pack's own effects. The look is
therefore pure art + `.def` text and is portable in principle. The demo additionally bundles
`ReShade32/64.dll`, `ReShade.ini`, `OpenGL32.dll` (PC-only post-processing).

The motif also wires **team modes into its title menu** (`teamarcade`, `teamversus`,
`teamcoop`) — those entries must be removed for the Vita build.

## 6. Character triage — measured on the demo's 10 characters

Run: `python tools/scan_mugen_build.py "<demo>/Chars"` → 9 × LIKELY OK, 1 × TEST IT.

| Verdict | Character | SFF | Media total | Notes |
|---|---|---|---|---|
| LIKELY OK 100 | Kung Fu Man 720 | 0.9 MB | 1.1 MB | clean template |
| LIKELY OK 94 | Pupa (Rage of the Dragons) | 1.1 MB | 3.4 MB | team code present (harmless 1v1) |
| LIKELY OK 92 | Bender (Cartoon) | 2.7 MB | 19.9 MB | 17 MB audio |
| LIKELY OK 92 | Lucario (Pokémon) | 2.5 MB | 9.8 MB | — |
| LIKELY OK 86 | Goenitz (KOF) | 1.8 MB | 7.2 MB | team code present |
| LIKELY OK 86 | Gouken (Street Fighter) | 5.5 MB | 9.8 MB | team code present |
| LIKELY OK 86 | Janemba (Dragon Ball) | 4.8 MB | 11.8 MB | team code present |
| LIKELY OK 86 | Kaede (Last Blade) | 1.4 MB | 9.0 MB | team code present |
| LIKELY OK 86 | kaede2 (Last Blade) | 1.9 MB | 9.0 MB | duplicate entry |
| TEST IT 71 | Shiki Nanaya (Melty Blood) | 5.6 MB | 49.8 MB | 44 MB audio + `trans = sub` |

Conclusion: the characters in such packs are **1–6 MB sprite sheets** — the portable class.
Audio (`.snd`) is the heavy part, not sprites. 57 characters ≈ 200–300 MB of assets.

## 7. Jump Force roster

40 launch + 14 DLC + 3 free-update = **57 playable** across 16 series, per Wikipedia's
*Jump Force* article (Characters → Playable characters). Full list in
`roster/jumpforce-roster.md`.

## 8. Source list

- Sony Vita spec: `sonyinteractive.com/en/press-releases/2011/playstationvita-launches-from-22-february-2012-in-europe/`
- Source pack thread: `mugenfreeforall.com/topic/38810-the-best-mugen-11-beta-2-2020/`
- Author site (resources/screenpacks/demo): `edl7.es.tl/Resources.htm`
- Dolmexica docs: `captaindreamcast.github.io/DolmexicaInfinite/dolmexica.html`,
  `…/differences.html`, `…/makeyourowngamevita.html`
- Dolmexica source: `github.com/CaptainDreamcast/DolmexicaInfinite`
- Bug reports / creator statements: `itch.io/t/3400376/dolmexica-bug-reports`, `itch.io/t/3400378/dolmexica-faq`
- SF1MR Vita (proof of pipeline): `gamebrew.org/wiki/SF1MR_Vita`, `github.com/anas-halid/SF1MR-VITA`
- PSP-era route: `psp-archive.github.io/games/mugen-PSP.html`, `github.com/PSP-Archive/infcat`
- Jump Force roster: `en.wikipedia.org/wiki/Jump_Force`
