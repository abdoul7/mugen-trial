"""char_review.py -- how complete/deep is each fighter in build/game? Writes reports/char-review.csv.

Per character: states, commands (moves wired to inputs), specials/supers (commands whose input has a
motion and ends in a button), animations, sprites, sounds, AI hints, and missing basics: core animations
the engine needs (stand 0, walk 20, crouch 11, jump 41-47, guard 120-155, get-hit 5000-5100, KO 5150...).
"""
import csv
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "build", "game", "assets")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import char_heights as ch  # noqa: E402

CORE_ANIMS = {0: "stand", 20: "walk", 11: "crouch", 41: "jump", 120: "guard", 5000: "get hit (stand)",
              5010: "get hit (crouch)", 5030: "get hit (air)", 5050: "falling", 5100: "hit ground",
              5150: "KO lying", 180: "win pose", 190: "intro"}


def read(p):
    return open(p, encoding="latin-1", errors="replace").read()


def files(def_text, folder):
    out = {"st": []}
    m = re.search(r"(?is)\[files\](.*?)(?:\n\s*\[|$)", def_text)
    for k, v in re.findall(r"(?im)^\s*([a-z0-9]+)\s*=\s*([^;\r\n]+)", m.group(1) if m else ""):
        p = ch.find_ci(folder, v.strip().strip('"'))
        if not p:
            continue
        k = k.lower()
        if k in ("cns", "cmd") or re.match(r"st\d*$", k):
            out["st"].append(p)
        out.setdefault(k, p)
    return out


def sff_count(p):
    d = open(p, "rb").read(64)
    return struct.unpack_from("<I", d, 0x28 if d[15] == 2 else 20)[0]


def snd_count(p):
    d = open(p, "rb").read(32)
    return struct.unpack_from("<I", d, 16)[0] if len(d) >= 20 else 0  # SND v1: count at 16


def review(entry):
    def_path = os.path.join(ASSETS, "chars", entry if entry.lower().endswith(".def") else f"{entry}/{entry}.def")
    folder = os.path.dirname(def_path)
    t = read(def_path)
    f = files(t, folder)
    scripts = "\n".join(read(p) for p in dict.fromkeys(f["st"]))
    states = set(int(x) for x in re.findall(r"(?im)^\s*\[\s*statedef\s+(-?\d+)", scripts))
    cmd = read(f["cmd"]) if "cmd" in f else ""
    commands = re.findall(r"(?is)\[command\](.*?)(?=\n\s*\[|$)", cmd)
    names, motions = set(), set()
    for c in commands:
        n = re.search(r'(?im)^\s*name\s*=\s*"([^"]+)"', c)
        k = re.search(r"(?im)^\s*command\s*=\s*([^;\r\n]+)", c)
        if not n or not k:
            continue
        names.add(n.group(1))
        steps = [s.strip().lower() for s in k.group(1).split(",")]
        # a special move: at least one direction step before a final button (e.g. "~D, DF, F, x" or "D,F+x")
        dirs = [s for s in steps[:-1] if re.search(r"(?<![a-z])(u|d|f|b|df|db|uf|ub)(?![a-z])", s.replace("~", "").replace("$", "").replace("/", ""))]
        if steps and re.search(r"(?<![a-z])[abcxyz](?![a-z])", steps[-1]) and (dirs or "+" in steps[-1] and re.search(r"(?<![a-z])(d|f|b|u|df|db)(?![a-z])", steps[-1])) \
                and not n.group(1).lower().startswith(("ai", "cpu")):
            motions.add(n.group(1))
    air = read(f["anim"]) if "anim" in f else ""
    anims = set(int(x) for x in re.findall(r"(?im)^\s*\[\s*begin\s+action\s+(-?\d+)", air))
    missing = [name for num, name in CORE_ANIMS.items() if num not in anims]
    ai = bool(re.search(r"(?i)ailevel|\bai\b.*\.cns|var\(59\)|var\(58\)", scripts + " ".join(f["st"])) or
              any("ai" in os.path.basename(p).lower() for p in f["st"]))
    supers = len(re.findall(r"(?im)^\s*\[\s*statedef\s+(3\d{3})", scripts))
    return {"id": os.path.basename(folder) if "/" not in entry else entry.split("/")[0],
            "states": len(states), "commands": len(names), "motion_moves": len(motions),
            "states_3000s(supers)": supers, "animations": len(anims),
            "sprites": sff_count(f["sprite"]) if "sprite" in f else 0,
            "sounds": snd_count(f["sound"]) if "sound" in f else 0,
            "ai": "yes" if ai else "no", "missing_core_anims": ", ".join(missing)}


def main():
    sel = read(os.path.join(ASSETS, "data", "select.def")).split("[Characters]")[1].split("\n[")[0]
    rows = []
    for line in sel.splitlines():
        e = line.split(";")[0].split(",")[0].strip()
        if e and e.lower() != "randomselect":
            try:
                rows.append(review(e))
            except Exception as ex:  # noqa: BLE001
                rows.append({"id": e, "missing_core_anims": f"ERROR {ex}"})
    out = os.path.join(ROOT, "reports", "char-review.csv")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{'id':22} {'states':>6} {'cmds':>5} {'motion':>6} {'supers':>6} {'anims':>5} {'sprites':>7} {'sounds':>6} ai   missing core anims")
    for r in sorted(rows, key=lambda r: r.get("motion_moves", 0)):
        print(f"{r['id']:22} {r.get('states', 0):6} {r.get('commands', 0):5} {r.get('motion_moves', 0):6} "
              f"{r.get('states_3000s(supers)', 0):6} {r.get('animations', 0):5} {r.get('sprites', 0):7} "
              f"{r.get('sounds', 0):6} {r.get('ai', '?'):4} {r.get('missing_core_anims', '')}")


if __name__ == "__main__":
    main()
