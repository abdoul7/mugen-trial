#!/usr/bin/env python3
"""
scan_mugen_build.py -- find out which characters from a big PC M.U.G.E.N build
can realistically be re-packed into a PS Vita game (Dolmexica Infinite).

WHY THIS EXISTS
---------------
The PS Vita has 512 MB of RAM. A 2000-character 720p M.U.G.E.N 1.1 pack needs
gigabytes. So we do not port "the build" -- we cherry-pick characters that are
small enough and old enough, and repack those into a .vpk with Dolmexica's
"Make-your-own-game kit for Vita".

This script reads a plain M.U.G.E.N folder on your PC and writes:
  * triage.csv  -- one row per character with the reasons it was flagged
  * select.def  -- a ready-to-paste roster of the safe picks
  * a printed summary

HOW TO RUN
----------
    python scan_mugen_build.py "C:/path/to/TBM 1.1"

Nothing is modified or moved; the script only reads.
"""

import csv
import os
import re
import sys

# ---------------------------------------------------------------- thresholds
# 512 MB main memory on the Vita, and Dolmexica has to fit the game image,
# the char SFF (sprites), the SND (sound) and the stage in there at once.
SFF_WARN_MB = 12.0     # above this a single char is a real memory risk
SFF_FAIL_MB = 30.0     # above this it almost certainly will not fit
SND_WARN_MB = 4.0

# Text patterns we look for inside the character's text files (.cns/.cmd/.def).
# Each entry: (label, regex, weight, human reason)
RISK_PATTERNS = [
    ("hi-res localcoord", r"localcoord\s*=\s*(?:1280|1920|2560|1280\.0|1920\.0)",
     25, "made for 720p/1080p; Vita build wants 4:3-era coordinates"),
    ("1.1-only syntax", r"\b(?:zoom|posfreeze|modelzoom)\s*=",
     12, "M.U.G.E.N 1.1 feature; Dolmexica emulates 1.1b only partly"),
    ("team/tag code present", r"\b(?:teamside|teammode|partner|tag_in|tag_out|simul)\b",
     6, "contains team code; usually harmless in 1v1, but tags/assists will not work"),
    ("subtractive blend", r"trans\s*=\s*sub\b",
     15, "Vita build has no subtractive blending (FX render wrong)"),
    ("multi-palette remap", r"remappal[\s\S]{0,80}?source\s*=\s*(?!1\s*,\s*1)\d",
     15, "Vita only supports RemapPal with source = 1,1"),
    ("mp3 audio", r"\.mp3\b",
     8, "Vita build plays OGG; mp3 must be converted"),
    ("font bank", r"\bfont\s*=\s*\d\s*,\s*[1-9]",
     6, "Dolmexica dropped font banks; colours 0-8 only"),
]

FOOTER = "-" * 68


def read_text(path):
    """M.U.G.E.N files are old Windows text; never trust the encoding."""
    try:
        with open(path, "r", encoding="latin-1", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def ini_get(text, section, key):
    """Tiny .def parser: return value of `key` inside `[section]`."""
    section_re = re.compile(r"^\s*\[" + re.escape(section) + r"\]\s*$", re.I | re.M)
    m = section_re.search(text)
    if not m:
        return None
    block = text[m.end():]
    stop = re.search(r"^\s*\[", block, re.M)
    if stop:
        block = block[: stop.start()]
    key_re = re.compile(r"^\s*" + re.escape(key) + r"\s*=\s*(.+?)\s*$", re.I | re.M)
    km = key_re.search(block)
    if not km:
        return None
    # M.U.G.E.N defs carry trailing ; comments after values
    return km.group(1).split(";")[0].strip() or None


def find_char_defs(root):
    """
    A character folder holds a .def that lists cmd/cns/sff. The pack nests them
    as chars/<Franchise>/<Character>/<file>.def (sometimes two levels deep).
    """
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if not name.lower().endswith(".def"):
                continue
            path = os.path.join(dirpath, name)
            text = read_text(path)
            # real character defs have a [Files] block pointing at sprites
            if re.search(r"^\s*\[Files\]", text, re.I | re.M) and ini_get(text, "Files", "sprite"):
                yield path, text


def size_mb(path):
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except OSError:
        return 0.0


def folder_size_mb(folder, exts=(".sff", ".snd")):
    total = 0.0
    for dirpath, _d, filenames in os.walk(folder):
        for name in filenames:
            if name.lower().endswith(exts):
                total += size_mb(os.path.join(dirpath, name))
    return total


def analyse(def_path, def_text):
    folder = os.path.dirname(def_path)
    name = ini_get(def_text, "Info", "name") or os.path.basename(folder)
    version = (ini_get(def_text, "Info", "mugenversion") or "?").strip()
    localcoord = (ini_get(def_text, "Info", "localcoord") or "").strip()

    # gather every text file the character owns, so patterns are found anywhere
    corpus = [def_text]
    for dirpath, _d, filenames in os.walk(folder):
        for fname in filenames:
            if fname.lower().endswith((".cns", ".cmd", ".st", ".txt")):
                corpus.append(read_text(os.path.join(dirpath, fname)))
    blob = "\n".join(corpus).lower()

    sff = size_mb(os.path.join(folder, ini_get(def_text, "Files", "sprite") or ""))
    media = folder_size_mb(folder)

    flags, score = [], 100
    if sff > SFF_FAIL_MB:
        flags.append("sprite file too big (%.0f MB)" % sff); score -= 40
    elif sff > SFF_WARN_MB:
        flags.append("large sprite file (%.0f MB)" % sff); score -= 18
    if media - sff > SND_WARN_MB:
        flags.append("heavy audio (%.0f MB)" % (media - sff)); score -= 8

    for label, pattern, weight, _reason in RISK_PATTERNS:
        if re.search(pattern, blob, re.I):
            flags.append(label)
            score -= weight

    if localcoord and re.match(r"\s*(1280|1920)", localcoord):
        pass  # already caught by hi-res localcoord pattern

    score = max(0, min(100, score))
    if score >= 75:
        verdict = "LIKELY OK"
    elif score >= 45:
        verdict = "TEST IT"
    else:
        verdict = "UNLIKELY"

    return {
        "name": name,
        "folder": os.path.relpath(folder, os.path.dirname(os.path.dirname(def_path)) or "."),
        "mugenversion": version,
        "localcoord": localcoord or "default 320x240",
        "sff_mb": round(sff, 1),
        "media_mb": round(media, 1),
        "score": score,
        "verdict": verdict,
        "flags": "; ".join(flags) if flags else "none",
        "def_path": def_path,
    }


def write_select_def(rows, out_path):
    keep = [r for r in rows if r["verdict"] in ("LIKELY OK", "TEST IT")]
    keep.sort(key=lambda r: (-r["score"], r["name"].lower()))
    lines = [
        "; generated by scan_mugen_build.py",
        "; paste the [Characters] block into assets/data/select.def",
        "",
        "[Characters]",
    ]
    for r in keep:
        lines.append("%s, stages/placeholder.def" % r["folder"].replace("\\", "/"))
    lines += ["", "[ExtraStages]", "; add your stage defs here", ""]
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return len(keep)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        print("usage: python scan_mugen_build.py <path to mugen folder>")
        return 2
    root = argv[1]
    if not os.path.isdir(root):
        print("not a folder: %s" % root)
        return 2

    rows = [analyse(p, t) for p, t in find_char_defs(root)]
    rows.sort(key=lambda r: (r["verdict"] != "LIKELY OK", -r["score"], r["name"].lower()))
    if not rows:
        print("No character .def files found under %s" % root)
        print("Point the script at the folder that contains chars/ (or at chars/ itself).")
        return 1

    csv_path = os.path.join(os.getcwd(), "triage.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    select_path = os.path.join(os.getcwd(), "select.def")
    kept = write_select_def(rows, select_path)

    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print(FOOTER)
    print("scanned %d characters in %s" % (len(rows), root))
    for verdict in ("LIKELY OK", "TEST IT", "UNLIKELY"):
        print("  %-10s %d" % (verdict, counts.get(verdict, 0)))
    print(FOOTER)
    print("best candidates (score, name, flags):")
    for r in rows[:15]:
        print("  %3d  %-30s %s" % (r["score"], r["name"][:30], r["flags"][:60]))
    print(FOOTER)
    print("wrote %s (%d rows)" % (csv_path, len(rows)))
    print("wrote %s (%d characters pre-filled)" % (select_path, kept))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
