"""vita3k_fight_test.py -- fight test on the Vita build inside the Vita3K emulator.

    python tools/vita3k_fight_test.py [id ...] [--vs ID] [--secs 45]

For each character id (default: every character in the installed select.def) it starts Vita3K,
goes Title -> Watch, picks the character for P1 and either the same character (mirror match, the
worst case: both sides load their own copy) or --vs ID for P2, confirms a random stage and
screenshots the fight. Afterwards it reads the engine's debug log (ux0:data/prismlog.txt, needs an
engine built with tools/engine/build_vita.sh --debug) for the free CDRAM and heap after loading.

Needs: Vita3K with firmware (tools/vita3k_run.py), the game installed as JFVT00001 in Vita3K
(install a .vpk once, then copy build/game/assets + build/engine/DolmexicaInfinite.self over
ux0/app/JFVT00001/{assets,eboot.bin}).
Results: reports/vita3k/fights/<id>/*.png and reports/vita3k/fights/results.csv
"""
import csv
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_game  # noqa: E402
import soak_test  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VITA3K = os.environ.get("VITA3K", r"C:\Users\issaa\Tools\Vita3K\Vita3K.exe")
VFS = os.path.join(os.environ["APPDATA"], "Vita3K", "Vita3K")
APP = os.path.join(VFS, "ux0", "app", "JFVT00001")
LOG = os.path.join(VFS, "ux0", "data", "prismlog.txt")
OUT = os.path.join(ROOT, "reports", "vita3k", "fights")
COLS = 10           # stock select grid width (build_assets.py)
P2_START = (0, 9)   # p2.cursor.startcell
INTERVAL = float(os.environ.get("SHOT_INTERVAL", "5"))


def roster():
    t = open(os.path.join(APP, "assets", "data", "select.def"), encoding="latin-1").read()
    part = t.split("[Characters]")[1].split("[")[0]
    return [s.split(",")[0].strip().split("/")[0] for s in (l.split(";")[0].strip() for l in part.splitlines())
            if s and s != "randomselect"]


def tap(pid, key, hold=0.12):
    drive_game.focus(pid)
    drive_game.send(key, False)
    time.sleep(hold)
    drive_game.send(key, True)
    time.sleep(0.25)


def move(pid, frm, to):
    dr, dc = to[0] - frm[0], to[1] - frm[1]
    for _ in range(abs(dr)):
        tap(pid, "down" if dr > 0 else "up")
    for _ in range(abs(dc)):
        tap(pid, "right" if dc > 0 else "left")


def parse_log():
    if not os.path.exists(LOG):
        return {}
    t = open(LOG, encoding="latin-1", errors="replace").read()
    cdram = [int(x) for x in re.findall(r"Free memory: cdram (\d+)", t)]
    heap = [int(x) for x in re.findall(r"Heap: (\d+) used", t)]
    errors = [e for e in re.findall(r"(?im)^.*(?:out of vita texture memory|unable to|abort|error).*$", t)
              if "Unable to find palette file" not in e]  # harmless: char without a palN file
    return {"min_free_cdram_mb": round(min(cdram) / 2**20, 1) if cdram else "",
            "start_free_cdram_mb": round(cdram[0] / 2**20, 1) if cdram else "",
            "max_heap_mb": round(max(heap) / 2**20, 1) if heap else "",
            "log_errors": " | ".join(e.strip()[:120] for e in errors[:3])}


def run(p1, p2, ids, secs):
    label = p1 if p1 == p2 else f"{p1}_vs_{p2}"
    out = os.path.join(OUT, label)
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        os.remove(os.path.join(out, f))
    if os.path.exists(LOG):
        os.remove(LOG)
    i1, i2 = ids.index(p1), ids.index(p2)
    c1, c2 = (i1 // COLS, i1 % COLS), (i2 // COLS, i2 % COLS)
    log = open(os.path.join(out, "vita3k.log"), "w", encoding="utf-8", errors="replace")
    p = subprocess.Popen([VITA3K, "--frontend", "sdl", "-r", "JFVT00001"], cwd=os.path.dirname(VITA3K),
                         stdout=log, stderr=subprocess.STDOUT)
    shots, crashed, t0 = 0, False, time.time()
    try:
        time.sleep(12)
        tap(p.pid, "left")            # first key after focus is swallowed
        for _ in range(5):
            tap(p.pid, "down")        # ARCADE -> ... -> WATCH
        tap(p.pid, "x")
        time.sleep(3)
        move(p.pid, (0, 0), c1)
        tap(p.pid, "x", 0.4)
        time.sleep(1.5)
        move(p.pid, P2_START, c2)
        tap(p.pid, "x", 0.4)
        time.sleep(1.5)
        soak_test.shot(p.pid, os.path.join(out, "00-select.png"))
        tap(p.pid, "x", 0.4)          # stage: random
        load_start = time.time()
        end = load_start + secs
        n = 1
        while time.time() < end:
            time.sleep(INTERVAL)
            if p.poll() is not None:
                crashed = True
                break
            soak_test.shot(p.pid, os.path.join(out, f"{n:02d}-{int(time.time() - load_start):03d}s.png"))
            n += 1
        shots = n
    finally:
        alive = p.poll() is None
        if alive:
            p.kill()
            p.wait()
        log.close()
    pngs = sorted(f for f in os.listdir(out) if f.endswith(".png"))
    result = "CRASH (emulator exited)" if crashed else "ran"
    if not crashed and pngs and soak_test.is_error_screen(os.path.join(out, pngs[-1])):
        result = "ENGINE ERROR (see screenshots)"
    r = {"label": label, "p1": p1, "p2": p2, "result": result, "seconds": int(time.time() - t0), "shots": shots}
    r.update(parse_log())
    return r


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    vs = sys.argv[sys.argv.index("--vs") + 1] if "--vs" in sys.argv else None
    secs = int(sys.argv[sys.argv.index("--secs") + 1]) if "--secs" in sys.argv else 45
    for opt in (vs, str(secs)):
        if opt in args:
            args.remove(opt)
    ids = roster()
    targets = args or ids
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "results.csv")
    fields = ["label", "p1", "p2", "result", "seconds", "shots", "start_free_cdram_mb", "min_free_cdram_mb",
              "max_heap_mb", "log_errors"]
    for cid in targets:
        r = run(cid, vs or cid, ids, secs)
        print(r, flush=True)
        new = not os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            if new:
                w.writeheader()
            w.writerow(r)


if __name__ == "__main__":
    main()
