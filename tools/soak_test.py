"""
soak_test.py -- unattended fight test on the Windows Dolmexica build.

Dolmexica's title screen starts an exhibit (CPU vs CPU) fight after `title.waittime`
idle ticks (titlescreen.cpp, [Demo Mode]). This script uses that so no input is needed:
for each character it writes a one-character select.def (the character fights itself on
its own stage), turns demo mode on with a short wait and visible lifebars/BGM, launches
the game, and records whether the process survives, its peak memory, and screenshots.

    python tools/soak_test.py                 # every character in build/game select.def
    python tools/soak_test.py bender kaede    # just these ids
    python tools/soak_test.py --all --secs 240  # whole roster at once, random matchups

The game's own select.def/system.def are restored afterwards.
Results: reports/soak/<id>/*.png and reports/soak/results.csv
"""

import csv
import ctypes
import ctypes.wintypes as wt
import os
import re
import shutil
import subprocess
import sys
import time

import psutil
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "build", "game")
EXE = os.path.join(GAME, "Dolmexica Infinite for Windows.exe")
DATA = os.path.join(GAME, "assets", "data")
OUTDIR = os.path.join(ROOT, "reports", "soak")

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()

DEMO = """[Demo Mode]
enabled = 1
select.enabled = {select}
vsscreen.enabled = 1
title.waittime = 90
fight.endtime = {endtime}
fight.playbgm = 1
fight.bars.display = 1
intro.waitcycles = 99
debuginfo = 0
"""


def read(p):
    with open(p, encoding="latin-1") as f:
        return f.read()


def write(p, t):
    with open(p, "w", encoding="latin-1", newline="\r\n") as f:
        f.write(t.replace("\r\n", "\n"))


def window_of(pid):
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(cb, 0)
    return found[0] if found else None


def shot(pid, path):
    """Capture only the game window's own pixels (PrintWindow), never the desktop, so
    whatever else is open on screen can't leak into the report. No focus stealing."""
    hwnd = window_of(pid)
    if not hwnd:
        return False
    r = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    w, h = r.right, r.bottom
    if w <= 0 or h <= 0:
        return False
    hdc = user32.GetDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mdc, bmp)
    ok = user32.PrintWindow(hwnd, mdc, 3)  # PW_CLIENTONLY | PW_RENDERFULLCONTENT
    buf = ctypes.create_string_buffer(w * h * 4)
    bi = (ctypes.c_uint32 * 10)(40, w, (-h) & 0xFFFFFFFF, 1 | (32 << 16), 0, 0, 0, 0, 0, 0)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, bi, 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mdc)
    user32.ReleaseDC(hwnd, hdc)
    if not ok:
        return False
    Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1).save(path)
    return True


def roster():
    chars, stages, sec = [], [], ""
    for line in read(os.path.join(DATA, "select.def")).splitlines():
        s = line.split(";")[0].strip()
        if s.startswith("["):
            sec = s.lower()
        elif s and sec == "[characters]" and s != "randomselect":
            name, stage = [x.strip() for x in s.split(",")[:2]]
            chars.append((name.split("/")[0], name, stage))
    return chars


def run_one(label, select_text, secs, endtime, select_enabled):
    out = os.path.join(OUTDIR, label)
    os.makedirs(out, exist_ok=True)
    write(os.path.join(DATA, "select.def"), select_text)
    sysdef = read(SYSTEM_BAK)
    sysdef = re.sub(r"(?is)\[Demo Mode\].*?(?=\n\s*;-{5,}|\n\[)", DEMO.format(select=select_enabled, endtime=endtime).strip(), sysdef)
    write(os.path.join(DATA, "system.def"), sysdef)

    p = subprocess.Popen([EXE], cwd=GAME)
    proc = psutil.Process(p.pid)
    peak, t0, n, crashed = 0, time.time(), 0, False
    while time.time() - t0 < secs:
        time.sleep(1)
        if p.poll() is not None:
            crashed = True
            break
        try:
            peak = max(peak, proc.memory_info().rss)
        except psutil.Error:
            pass
        el = time.time() - t0
        if el > 8 + n * 12 and n < 30:
            shot(p.pid, os.path.join(out, f"{n:02d}-{int(el):03d}s.png"))
            n += 1
    alive = p.poll() is None
    if alive:
        p.kill()
        p.wait()
    return {"label": label, "result": "OK" if alive else f"EXITED code={p.returncode}",
            "seconds": int(time.time() - t0), "peak_mb": round(peak / 2**20), "shots": n}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    secs = int(sys.argv[sys.argv.index("--secs") + 1]) if "--secs" in sys.argv else 75
    if "--secs" in sys.argv:
        args.remove(str(secs))
    shutil.copy2(os.path.join(DATA, "select.def"), SELECT_BAK)
    shutil.copy2(os.path.join(DATA, "system.def"), SYSTEM_BAK)
    results = []
    try:
        if "--all" in sys.argv:
            results.append(run_one("all", read(SELECT_BAK), secs, 1500, 1))
        else:
            for cid, entry, stage in roster():
                if args and cid not in args:
                    continue
                sel = f"[Characters]\n{entry}, {stage}\n\n[ExtraStages]\n{stage}\n\n[Options]\narcade.maxmatches = 6,1,1,0,0,0,0,0,0,0\nteam.maxmatches = 4,1,1,0,0,0,0,0,0,0\n"
                r = run_one(cid, sel, secs, 3000, 0)
                print(r, flush=True)
                results.append(r)
    finally:
        shutil.copy2(SELECT_BAK, os.path.join(DATA, "select.def"))
        shutil.copy2(SYSTEM_BAK, os.path.join(DATA, "system.def"))
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, "results.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["label", "result", "seconds", "peak_mb", "shots"])
        if new:
            w.writeheader()
        w.writerows(results)
    for r in results:
        print(r)


SELECT_BAK = os.path.join(DATA, "select.def.soakbak")
SYSTEM_BAK = os.path.join(DATA, "system.def.soakbak")

if __name__ == "__main__":
    main()
