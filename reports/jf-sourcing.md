# Jump Force roster — sourcing log (T5)

Source: AK1 (andersonkenya1.net) file search, 2026-10-27. Sizes are the **archive** size
AK1 lists; the unpacked sprites + sounds are what the Vita heap (96 MB total) has to hold.
Rule of thumb from the first download: keep archives under ~25 MB.

## Downloaded and triaged

| Jump Force | File | Archive | Unpacked | Verdict |
|---|---|---|---|---|
| Son Goku | Goku SSJ2 JUS [此赤非彼枫] (AK1 61679) | 96 MB | sff 71 MB, snd 54 MB | **UNLIKELY (31)**: sprites alone are 70 MB. Rejected. |

## Candidates found, not yet downloaded (smallest first)

| Jump Force | File | Archive | Link |
|---|---|---|---|
| Monkey D. Luffy | Luffy TS JUS – Sektor | 14.3 MB | https://www.andersonkenya1.net/files/file/56847-luffy-ts-jus-sektor/ |
| Monkey D. Luffy | Luffy PTS JUS – Mikel8888 | 23.0 MB | https://www.andersonkenya1.net/files/file/56905-luffy-pts-jus-mikel8888/ |
| Monkey D. Luffy | Monkey D. Luffy GPC edited | 29.4 MB | https://www.andersonkenya1.net/files/file/57287-monkey-d-luffy-gpc-edited/ |
| Monkey D. Luffy | Luffy TS JUS (Fresh Prince 24) | 41.0 MB | https://www.andersonkenya1.net/files/file/61102-luffy-ts-jus-fresh-prince-24-jus-one-piece-series/ |
| Renji Abarai | Renji Abarai (2021) | 5.9 MB | https://www.andersonkenya1.net/files/file/16703-renji-abarai/ |
| Renji Abarai | Renji Abarai (2020) | 11.4 MB | https://www.andersonkenya1.net/files/file/6841-renji-abarai/ |
| Renji Abarai | Renji Abarai CVS | 13.6 MB | https://www.andersonkenya1.net/files/file/42213-renji-abarai-cvs/ |
| Renji Abarai | Renji Abarai (COH) | 26.7 MB | https://www.andersonkenya1.net/files/file/50684-renji-abarai-coh/ |

Too big to consider for Luffy: Egghead JUS 175 MB, Yonko Onigashima 160 MB, PTS Thriller Bark 90 MB, TS Anhthai 62 MB.

## Not searched yet

Everyone else on `handoff/roster/jumpforce-roster.md`. AK1 started answering automated
searches with HTTP 429 + an interactive Cloudflare check after ~10 searches, so the lookup
has to go slowly, with the check cleared by a person.
The three Jump Force originals (Galena, Kane, Prometheus) almost certainly have no MUGEN versions.

## 2026-10-26 — blocked at AK1 (Cloudflare), nothing downloaded

- First lookup of the session: `files/file/56847-luffy-ts-jus-sektor/`.
- The response was Cloudflare's "Performing security verification" interstitial
  (Ray ID `a50ba9b7ed50a2bb`), not the file page.
- Per `AGENTS.md`: stopped immediately. No retry, no alternate route, no attempt to solve
  the check.
- Consequence: **no archives were fetched this session.** The two entries previously listed
  as "known good picks" are still *candidates only* — neither has been downloaded, triaged
  or soaked.
- This matches the earlier observation that AK1 starts answering with 429 + an interactive
  check after roughly ten searches. Plan for 2–4 short sessions with the check cleared in
  between, not one long run.

## Tool validation (2026-10-26, against 10 real characters)

Both acceptance tools were run against the 10 characters extracted from the TBM demo before
trusting them on AK1 downloads:

- `handoff/tools/scan_mugen_build.py` → 9 × LIKELY OK, 1 × TEST IT (Shiki Nanaya: 5.6 MB
  sprites, 44 MB audio). Two defects found and fixed in the copy now in `handoff/`:
  1. values were not split on `;`, so `mugenversion` came back as `04.14.2001` (the trailing
     comment) instead of the real version — every character looked like an unknown engine;
  2. "team/tag triggers" was weighted −20, but most WinMUGEN-era characters ship optional
     tag code that is harmless in 1v1; this alone rejected good characters. Now −6 and
     relabelled "team/tag code present".
- `tools/check_char_refs.py` → no MISSING files on the same 10 characters, and on a copy
  with one `.sff` deliberately deleted it reports `MISSING sprite = <file>` as expected.

## Two things to settle before the next sourcing batch

1. **The prompt is looser than `AGENTS.md`.** `docs/hermes-sourcing-prompt.md` step 4 accepts
   on triage + reference check alone, while `AGENTS.md` also requires
   `tools/soak_test.py <id>` to pass. The soak is the only gate that catches broken states
   and dead AI. Nothing was accepted this session, so nothing slipped through — but the
   prompt should be brought in line before the next batch.
2. **Judge on unpacked size, not archive size.** Evidence from the demo set: sprites run
   0.9–5.6 MB while one character carried 44 MB of audio, so a small archive can still be a
   memory problem and a 14 MB archive of 4:3 sprites is perfectly fine. The `sff MB` +
   `snd MB` columns decide, with the archive size as a first filter only.

