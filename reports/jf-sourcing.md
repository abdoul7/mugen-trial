# Jump Force roster — sourcing log (T5)

Machine-readable triage of every downloaded archive: `reports/jf-ingest.csv`
(regenerate with `tools/ingest_chars.py <folder>`). Sizes below are unpacked MB.
Limits: sprites (`.sff`) ≤ 30 MB to try at all; sound is shrunk by the build.

## Batch 1 — 24 archives downloaded by the owner from AK1 (2026-10-27)

Only **2 of these are on the Jump Force roster** (Sasuke, Madara); Kaguya is on it too but was
rejected for size. The rest are same-series characters (Dragon Ball, One Punch Man) kept as
extras / stand-ins.

| Character | On JF roster? | sff | snd (raw → built) | Triage | Soak (Windows) |
|---|---|---|---|---|---|
| Sasuke (Hebi, white) | **yes** (Sasuke Uchiha) | 22.5 | 6.7 → 3.8 | TEST | OK · 437 MB |
| Madara Revived | **yes** (Madara Uchiha) | 31.0 | 14.6 → 5.2 | over 30 MB, tried anyway | OK · 509 MB |
| Ōtsutsuki Kaguya v1.0 | **yes** | 53.0 | 36.6 | **REJECT**: sprites 53 MB | — |
| Android 17 | no (DB) | 17.3 | 23.3 → 10.9 | TEST | OK · 622 MB |
| Android 21 1.1 | no (DB) | 22.9 | 24.0 → 11.1 | TEST | OK · 800 MB |
| Android 18 | no (DB) | 25.8 | 7.9 → 5.2 | TEST | OK · 504 MB |
| Baby Vegeta | no (DB) | 18.3 | 10.9 → 6.4 | TEST (backup/ copy dropped) | OK · 544 MB |
| Bardock SSJ | no (DB) | 28.4 | 17.3 → 8.0 | TEST | OK · 475 MB |
| Gohan (Teen) 1.1 | no (DB) | 16.8 | 28.5 → 13.2 | TEST (missing pal1 dropped) | **FAIL**: engine error, cannot parse its command inputs ($UF …) — dropped |
| Goku Black (SSR) | no (DB) | 23.8 | 28.2 → 11.6 | TEST | OK · 732 MB |
| Kefla | no (DB) | 22.9 | 40.7 → 17.1 | TEST | OK · 655 MB |
| Tenshinhan (Cell Saga) | no (DB) | 20.1 | 5.4 → 3.5 | TEST | OK · 399 MB |
| Vegito (SSB) | no (DB) | 16.0 | 30.0 → 12.7 | TEST (missing pal1 dropped) | OK · 696 MB |
| Garou (Hunters) | no (OPM) | 1.6 | 2.0 → 0.9 | TEST | OK · 190 MB |
| Metal Bat | no (OPM) | 16.2 | 18.3 → 5.5 | TEST | OK · 536 MB |
| Tank-top Master | no (OPM) | 21.5 | 10.6 → 3.5 | TEST | OK · 555 MB |
| Androide C-18 | no (DB) | 113.6 | 24.6 | **REJECT**: sprites 114 MB | — |
| Gohan Teen JUS K | no (DB) | 35.5 | 6.0 | **REJECT**: sprites 35.5 MB | — |
| Hiruzen | no (Naruto) | 43.7 | 23.5 | **REJECT**: sprites 44 MB | — |
| Ichibe Hyōsube V2 | no (Bleach) | 162.5 | 78.8 | **REJECT**: sprites 163 MB | — |
| Kawashiki | no (Boruto) | 33.5 | 10.6 | **REJECT**: sprites 33.5 MB | — |
| Vegito | no (DB) | 69.1 | 37.0 | **REJECT**: sprites 69 MB, and its `.def` loads `common1.dll` | — |
| Uchiha Obito (.zip.001+.002) | no (Naruto) | — | — | **INCOMPLETE**: zip declares a 198 MB file, both parts total 177 MB — a part is missing or truncated | — |

Soak = 60 s CPU-vs-CPU fight on the Windows build, peak working set (demo characters: 210–370 MB).
Owner decision 2026-10-27: keep all 14 that fought, including the heavy ones; the Vita test decides.

"TEST" = passes the file checks; most use `trans = sub` effects, which the Vita build does
not implement yet, so some hit sparks / auras will look wrong there.

## Earlier lookups (AK1 search, before rate limit)

| Jump Force | Candidate | Archive | Link |
|---|---|---|---|
| Monkey D. Luffy | Luffy TS JUS – Sektor | 14.3 MB | https://www.andersonkenya1.net/files/file/56847-luffy-ts-jus-sektor/ |
| Monkey D. Luffy | Luffy PTS JUS – Mikel8888 | 23.0 MB | https://www.andersonkenya1.net/files/file/56905-luffy-pts-jus-mikel8888/ |
| Renji Abarai | Renji Abarai (2021) | 5.9 MB | https://www.andersonkenya1.net/files/file/16703-renji-abarai/ |
| Renji Abarai | Renji Abarai (2020) | 11.4 MB | https://www.andersonkenya1.net/files/file/6841-renji-abarai/ |
| Son Goku | Goku SSJ2 JUS [此赤非彼枫] (61679) | 96 MB | **rejected**: sprites 70 MB |

## Still needed from the actual Jump Force roster

Everything in `handoff/roster/jumpforce-roster.md` except Sasuke and Madara — notably the
headliners: Goku, Vegeta, Luffy, Naruto, Ichigo, Deku, Jotaro, Kenshiro, Yusuke.
