"""
ingest_chars.py -- unpack a folder of downloaded character archives and triage them.

    python tools/ingest_chars.py "C:/Users/me/Downloads/some folder"

For every .zip / .rar / .7z (split .zip.001/.002 parts are joined first):
  1. copy it to downloads/jf/ (the original is left where it is)
  2. extract to source/jf/<id>/, never extracting Windows executables/libraries
  3. find the character .def(s), measure sprite (.sff) and sound (.snd) sizes,
     check every referenced file exists (case-insensitive) and read localcoord/version
  4. run the handoff triage tool over source/jf
Writes reports/jf-ingest.csv and prints a table. Nothing is added to roster.json.
"""

import csv
import glob
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DL = os.path.join(ROOT, "downloads", "jf")
SRC = os.path.join(ROOT, "source", "jf")
TAR = r"C:\Windows\System32\tar.exe"
SKIP = (".exe", ".dll", ".bat", ".scr", ".vbs", ".ps1", ".com", ".msi")
FILE_KEY = re.compile(r"(cmd|cns|st\d*|stcommon|anim|sound|sprite|pal\d+)$", re.I)
SFF_FAIL_MB, SFF_WARN_MB = 30.0, 15.0


def slug(name):
    base = re.sub(r"\.(zip|rar|7z)(\.\d+)?$", "", name, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_")


def read(p):
    with open(p, encoding="latin-1") as f:
        return f.read()


def find_ci(folder, rel):
    cur = folder
    for part in rel.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            cur = os.path.dirname(cur)
            continue
        if not os.path.isdir(cur):
            return None
        hit = next((e for e in os.listdir(cur) if e.lower() == part.lower()), None)
        if hit is None:
            return None
        cur = os.path.join(cur, hit)
    return cur


def extract(archive, dst):
    os.makedirs(dst, exist_ok=True)
    if archive.lower().endswith(".7z"):
        import py7zr
        with py7zr.SevenZipFile(archive) as z:
            names = [n for n in z.getnames() if not n.lower().endswith(SKIP)]
        with py7zr.SevenZipFile(archive) as z:
            z.extract(path=dst, targets=names)
        return ""
    excl = sum([["--exclude", f"*{e}"] for e in SKIP] + [["--exclude", f"*{e.upper()}"] for e in SKIP], [])
    r = subprocess.run([TAR, "-xf", archive] + excl, cwd=dst, capture_output=True, text=True, errors="replace")
    return r.stderr.strip()


def inspect(char_dir, data_dir):
    rows = []
    for dp, _, fs in os.walk(char_dir):
        for f in fs:
            if not f.lower().endswith(".def"):
                continue
            p = os.path.join(dp, f)
            txt = read(p)
            files = re.search(r"(?is)\[files\](.*?)(\n\s*\[|$)", txt)
            if not files or not re.search(r"(?im)^\s*sprite\s*=", files.group(1)):
                continue  # not a character def (intro/ending/stage/font)
            info = {"def": os.path.relpath(p, SRC).replace("\\", "/"), "missing": [], "sff_mb": 0.0, "snd_mb": 0.0}
            for key in ("mugenversion", "localcoord", "displayname", "author"):
                m = re.search(rf"(?im)^\s*{key}\s*=\s*([^\r\n;]+)", txt)
                info[key] = m.group(1).strip().strip('"') if m else ""
            for m in re.finditer(r"(?im)^\s*([a-z0-9.]+)\s*=\s*([^\r\n;]*)", files.group(1)):
                k, v = m.group(1).lower(), m.group(2).strip().strip('"')
                if not FILE_KEY.match(k) or not v:
                    continue
                hit = find_ci(dp, v) or (find_ci(data_dir, v) if k == "stcommon" else None)
                if not hit and k == "stcommon" and v.lower() in ("common1.cns", "common2.cns"):
                    hit = "engine"  # Dolmexica ships common1.cns; common2.cns is copied in at build time
                if not hit:
                    info["missing"].append(f"{k}={v}")
                elif hit != "engine" and k == "sprite":
                    info["sff_mb"] = round(os.path.getsize(hit) / 2**20, 1)
                elif hit != "engine" and k == "sound":
                    info["snd_mb"] = round(os.path.getsize(hit) / 2**20, 1)
            trans_sub = 0
            for dp2, _, fs2 in os.walk(dp):
                for f2 in fs2:
                    if f2.lower().endswith((".cns", ".st", ".cmd")):
                        trans_sub += len(re.findall(r"(?im)^\s*trans\s*=\s*sub", read(os.path.join(dp2, f2))))
            info["trans_sub"] = trans_sub
            rows.append(info)
    return rows


def verdict(r):
    lc = r["localcoord"].replace(" ", "")
    hires = bool(re.match(r"(1280|1920|2560|960),", lc))
    hard = [m for m in r["missing"] if not re.match(r"pal\d+=", m)]  # build drops missing palettes
    if hard:
        return "REJECT", "missing files: " + ", ".join(hard[:4])
    if r["sff_mb"] > SFF_FAIL_MB:
        return "REJECT", f"sprites {r['sff_mb']} MB (> {SFF_FAIL_MB:.0f})"
    if hires and r["sff_mb"] > SFF_WARN_MB:
        return "REJECT", f"hi-res localcoord {lc} with {r['sff_mb']} MB sprites"
    notes = []
    if r["sff_mb"] > SFF_WARN_MB:
        notes.append(f"big sprites {r['sff_mb']} MB")
    if hires:
        notes.append(f"hi-res localcoord {lc}")
    if r["trans_sub"]:
        notes.append(f"{r['trans_sub']}x trans=sub (not implemented on Vita: some effects will look wrong)")
    if r["missing"]:
        notes.append("missing palette files dropped: " + ", ".join(r["missing"][:3]))
    if r["snd_mb"] > 6:
        notes.append(f"snd {r['snd_mb']} MB (will be shrunk)")
    return ("TEST" if notes else "OK"), "; ".join(notes)


def main():
    src_folder = sys.argv[1]
    os.makedirs(DL, exist_ok=True)
    os.makedirs(SRC, exist_ok=True)
    data_dir = os.path.join(ROOT, "engine", "Dolmexica Infinite 1.8", "assets", "data")
    archives = sorted(f for f in os.listdir(src_folder) if re.search(r"\.(zip|rar|7z)(\.0*1)?$", f, re.I))
    results = []
    for a in archives:
        cid = slug(a)
        dst_archive = os.path.join(DL, re.sub(r"\.0*1$", "", a))
        if re.search(r"\.0*1$", a):  # split archive: join all parts
            parts = sorted(glob.glob(os.path.join(src_folder, glob.escape(a[:-3]) + "[0-9][0-9][0-9]")))
            with open(dst_archive, "wb") as out:
                for p in parts:
                    with open(p, "rb") as f:
                        shutil.copyfileobj(f, out)
        elif not os.path.exists(dst_archive):
            shutil.copy2(os.path.join(src_folder, a), dst_archive)
        dst = os.path.join(SRC, cid)
        err = ""
        if not os.path.isdir(dst):
            err = extract(dst_archive, dst)
        chars = inspect(dst, data_dir)
        if not chars:
            results.append({"id": cid, "archive": a, "def": "", "verdict": "REJECT",
                            "reason": "no character .def found" + (f" ({err[:80]})" if err else "")})
            continue
        for r in chars:
            v, why = verdict(r)
            results.append({"id": cid, "archive": a, "def": r["def"], "name": r["displayname"], "author": r["author"],
                             "mugenversion": r["mugenversion"], "localcoord": r["localcoord"],
                             "sff_mb": r["sff_mb"], "snd_mb": r["snd_mb"], "verdict": v, "reason": why})
    out = os.path.join(ROOT, "reports", "jf-ingest.csv")
    cols = ["id", "archive", "def", "name", "author", "mugenversion", "localcoord", "sff_mb", "snd_mb", "verdict", "reason"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(results)
    for r in results:
        print(f"{r['verdict']:6s} {r['id']:32s} sff {r.get('sff_mb', ''):>5} snd {r.get('snd_mb', ''):>5}  "
              f"{r.get('localcoord', ''):10s} {r['def'][:55]:55s} {r['reason']}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
