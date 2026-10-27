"""vita3k_legends_autotest.py -- a hands-off Legends encounter in Vita3K (engine patch 0010).

    python tools/legends/vita3k_legends_autotest.py <out dir> --seed 1234 --attach 1 \
        --p1 kfm/kfm.def,pupa/Pupa.def,bender/ben.def --p2 lucario/Lucario.def,gouken/gouken.def,janemba/janemba.def

Writes ux0:data/JFVT00001/legends_autotest.txt (both coaches CPU), starts Vita3K without taking
focus, takes window screenshots every few seconds, waits for the encounter to finish (the game
exits at the results), then copies legends_log.txt into <out dir> and removes the autotest file.
Needs the patched engine and data/legends installed in Vita3K. No keystrokes are sent.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import soak_test  # noqa: E402

VITA3K = os.environ.get("VITA3K", r"C:\Users\abdou\Tools\Vita3K\Vita3K.exe")
DATA = os.path.join(os.environ["APPDATA"], "Vita3K", "Vita3K", "ux0", "data", "JFVT00001")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--attach", type=int, default=1)
    ap.add_argument("--p1", required=True)
    ap.add_argument("--p2", required=True)
    ap.add_argument("--secs", type=int, default=900)
    ap.add_argument("--shot-every", type=float, default=4)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    os.makedirs(DATA, exist_ok=True)
    auto = os.path.join(DATA, "legends_autotest.txt")
    log = os.path.join(DATA, "legends_log.txt")
    if os.path.exists(log):
        os.remove(log)
    sq = lambda s: ", ".join("assets/chars/" + x.strip() for x in s.split(","))
    with open(auto, "w", newline="\n") as f:
        f.write(f"seed = {a.seed}\nattach = {a.attach}\np1 = {sq(a.p1)}\np2 = {sq(a.p2)}\n")
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 4  # SW_SHOWNOACTIVATE
    p = subprocess.Popen([VITA3K, "--frontend", "sdl", "-r", "JFVT00001"], cwd=os.path.dirname(VITA3K), startupinfo=si,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0, n = time.time(), 0
    try:
        while time.time() - t0 < a.secs and p.poll() is None:
            time.sleep(a.shot_every)
            if time.time() - t0 > 12:
                n += soak_test.shot(p.pid, os.path.join(a.out, f"{n:03d}-{int(time.time() - t0):04d}s.png"))
    finally:
        finished = p.poll() is not None
        if p.poll() is None:
            p.kill()
            p.wait()
        os.remove(auto)
    if os.path.exists(log):
        shutil.copy(log, os.path.join(a.out, "legends_log.txt"))
    text = open(log, encoding="latin-1").read() if os.path.exists(log) else ""
    print(f"{'finished' if finished else 'TIMED OUT'} after {int(time.time() - t0)} s, {n} shots, log lines {len(text.splitlines())}")
    for line in text.splitlines():
        if "bout" in line and ("ends" in line or "telemetry" in line) or "commits" in line:
            print("  " + line)


if __name__ == "__main__":
    main()
