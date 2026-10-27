"""vita3k_autotest.py -- hands-off fight test in Vita3K: no keystrokes, window minimized.

    python tools/vita3k_autotest.py <p1 id> [<p2 id>] [--stage stages/kfm.def] [--secs 90]

Writes ux0:data/JFVT00001/autotest.txt (engine patch 0006 reads it at boot, skips the menus and runs
that fight CPU vs CPU), starts Vita3K minimized without taking focus, waits until the fight has
loaded and run --secs seconds (or the game exits), then reads the engine log. Needs the --debug engine
installed in Vita3K (load timings and memory lines are only logged there).

Prints and appends to reports/vita3k/autotest.csv: the load time of each step, total load time,
peak heap, minimum free CDRAM, and any engine error. Removes autotest.txt afterwards, so the
installed game boots normally again.
"""
import csv
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
VITA3K = os.environ.get("VITA3K", r"C:\Users\issaa\Tools\Vita3K\Vita3K.exe")
VFS = os.path.join(os.environ["APPDATA"], "Vita3K", "Vita3K")
APP = os.path.join(VFS, "ux0", "app", "JFVT00001")
DATA = os.path.join(VFS, "ux0", "data", "JFVT00001")
LOG = os.path.join(VFS, "ux0", "data", "prismlog.txt")
OUT = os.path.join(ROOT, "reports", "vita3k", "autotest.csv")
STEPS = ["setup", "stage", "players (scripts, animations, sounds)", "player sprites", "rest"]


def def_path(cid):
    folder = os.path.join(APP, "assets", "chars", cid)
    sel = open(os.path.join(APP, "assets", "data", "select.def"), encoding="latin-1").read()
    m = re.search(rf"(?im)^\s*({re.escape(cid)}/[^,;\r\n]+\.def)", sel)
    if m:
        return "assets/chars/" + m.group(1).strip()
    if re.search(rf"(?im)^\s*{re.escape(cid)}\s*,", sel):  # bare "kfm" means kfm/kfm.def
        return f"assets/chars/{cid}/{cid}.def"
    defs = [f for f in os.listdir(folder) if f.lower().endswith(".def")]
    return f"assets/chars/{cid}/{defs[0]}"


def hide_window(pid, timeout=20):
    """Place the emulator window where it won't get in the way, without ever activating it.

    Default: a small always-on-top window (480x272, half the Vita screen) in the bottom-right corner of
    the work area, so the fight can be watched while the user keeps working. JFV_AUTOTEST_WINDOW=hidden
    moves it off-screen instead (it keeps running either way: minimizing would stop the renderer)."""
    import os as _os
    hidden = _os.environ.get("JFV_AUTOTEST_WINDOW", "corner") == "hidden"
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    rect = wintypes.RECT()
    user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)  # SPI_GETWORKAREA (excludes taskbar)
    w, h = 480, 272
    x, y = rect.right - w - 8, rect.bottom - h - 8
    HWND_TOPMOST = wintypes.HWND(-1)
    SWP_NOSIZE, SWP_NOZORDER, SWP_NOACTIVATE = 0x0001, 0x0004, 0x0010

    def place(hwnd):
        if hidden:
            user32.SetWindowPos(hwnd, None, -4000, -4000, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)
        else:
            user32.SetWindowPos(hwnd, HWND_TOPMOST, x, y, w, h, SWP_NOACTIVATE)

    end = time.time() + timeout
    while time.time() < end:
        found.clear()
        user32.EnumWindows(cb, 0)
        for hwnd in found:
            place(hwnd)
        if found:
            for _ in range(3):  # the window can be re-created/resized while the game boots: catch it again
                time.sleep(1.5)
                found.clear()
                user32.EnumWindows(cb, 0)
                for hwnd in found:
                    place(hwnd)
            return True
        time.sleep(0.2)
    return False


def parse(log):
    r = {}
    for step in STEPS:
        m = re.search(rf"\[JFV\] load {re.escape(step)}: (\d+) ms \(total (\d+) ms\)", log)
        if m:
            r[step] = int(m.group(1))
            r["total_ms"] = int(m.group(2))
    heap = [int(x) for x in re.findall(r"Heap: (\d+) used", log)]
    cdram = [int(x) for x in re.findall(r"Free memory: cdram (\d+)", log)]
    r["max_heap_mb"] = round(max(heap) / 2**20, 1) if heap else ""
    r["min_free_cdram_mb"] = round(min(cdram) / 2**20, 1) if cdram else ""
    r["files"] = "; ".join(f"p{m[0]} {m[1]} {m[2]}" for m in re.findall(r"\[JFV\] player (\d) ([^:]+): (\d+) ms", log))
    errs = [e for e in re.findall(r"(?im)^.*(?:out of main memory|out of vita texture|abort|stuck in loop).*$", log)]
    r["errors"] = " | ".join(e.strip()[-110:] for e in errs[:2])
    r["done"] = "[JFV] autotest done" in log
    return r


def main():
    args = [a for a in sys.argv[1:]]
    stage = args[args.index("--stage") + 1] if "--stage" in args else "stages/kfm.def"
    secs = int(args[args.index("--secs") + 1]) if "--secs" in args else 90
    shots = float(args[args.index("--shots") + 1]) if "--shots" in args else 0  # seconds between screenshots
    ids = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--stage", "--secs", "--shots"))]
    p1 = ids[0]
    p2 = ids[1] if len(ids) > 1 else p1
    os.makedirs(DATA, exist_ok=True)
    auto = os.path.join(DATA, "autotest.txt")
    with open(auto, "w", newline="\n") as f:
        f.write(f"{def_path(p1)}\n{def_path(p2)}\nassets/{stage}\n")
    if os.path.exists(LOG):
        os.remove(LOG)

    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 4  # SW_SHOWNOACTIVATE: doesn't take focus (minimized would stop Vulkan rendering)
    start = time.time()
    p = subprocess.Popen([VITA3K, "--frontend", "sdl", "-r", "JFVT00001"], cwd=os.path.dirname(VITA3K),
                         startupinfo=si, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    hide_window(p.pid)
    loaded_at = None
    log = ""
    shot_dir = os.path.join(ROOT, "reports", "vita3k", "autotest", f"{p1}_vs_{p2}")
    if shots:
        import shutil
        import soak_test
        shutil.rmtree(shot_dir, ignore_errors=True)
        os.makedirs(shot_dir)
    next_shot = 0
    try:
        while time.time() - start < 300 + secs:
            time.sleep(1 if shots else 2)
            if shots and loaded_at and time.time() >= next_shot:
                soak_test.shot(p.pid, os.path.join(shot_dir, f"{int(time.time() - loaded_at):03d}s.png"))
                next_shot = time.time() + shots
            log = open(LOG, encoding="latin-1", errors="replace").read() if os.path.exists(LOG) else ""
            if loaded_at is None and "[JFV] load rest" in log:
                loaded_at = time.time()
            if p.poll() is not None or (loaded_at and time.time() - loaded_at > secs):
                break
    finally:
        crashed = p.poll() is not None and "[JFV] autotest done" not in log
        if p.poll() is None:
            p.kill()
            p.wait()
        os.remove(auto)

    r = {"p1": p1, "p2": p2, "stage": stage}
    r.update(parse(log))
    r["result"] = ("CRASH" if crashed else "did not finish loading" if loaded_at is None else "ok")
    fields = ["p1", "p2", "stage", "result"] + STEPS + ["total_ms", "max_heap_mb", "min_free_cdram_mb", "errors", "done", "files"]
    new = not os.path.exists(OUT)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(r)
    print(f"{p1} vs {p2}: {r['result']}  load {r.get('total_ms', '?')} ms  " +
          "  ".join(f"{s.split(' ')[0]} {r.get(s, '?')}" for s in STEPS) +
          f"  heap {r['max_heap_mb']} MB  cdram min {r['min_free_cdram_mb']} MB  {r['errors']}\n    {r['files']}")


if __name__ == "__main__":
    main()
