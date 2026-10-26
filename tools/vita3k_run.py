"""vita3k_run.py -- install/run a .vpk (or an installed title) in Vita3K and screenshot it.

    python tools/vita3k_run.py <out_dir> <vpk or TITLEID> "<script>"

Script steps are the same as tools/drive_game.py (wait:/key:/hold:/shot:). Vita3K's default
keyboard map: arrows = d-pad, Return = Start, X/C/V... see Vita3K Controls; we use
  cross = x, circle = c, square = z, triangle = s, start = return, select = backspace? (see notes)
Screenshots capture only the emulator window (PrintWindow).
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_game  # noqa: E402
import soak_test  # noqa: E402

VITA3K = os.environ.get("VITA3K", r"C:\Users\issaa\Tools\Vita3K\Vita3K.exe")


def main():
    out, target, script = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    if target.lower().endswith(".vpk"):
        args = [VITA3K, os.path.abspath(target)]
    else:
        args = [VITA3K, "--frontend", "sdl", "-r", target]
    log = open(os.path.join(out, "vita3k.log"), "w", encoding="utf-8", errors="replace")
    p = subprocess.Popen(args, cwd=os.path.dirname(VITA3K), stdout=log, stderr=subprocess.STDOUT)
    n = 0
    try:
        for step in script.split():
            kind, _, arg = step.partition(":")
            if p.poll() is not None:
                print(f"Vita3K exited (code {p.returncode}) before step {step}")
                break
            if kind == "wait":
                time.sleep(float(arg))
            elif kind == "key":
                name, _, times = arg.partition("*")
                for _ in range(int(times or 1)):
                    drive_game.focus(p.pid)
                    drive_game.send(name, False)
                    time.sleep(0.1)
                    drive_game.send(name, True)
                    time.sleep(0.3)
            elif kind == "hold":
                name, secs = arg.split(":")
                drive_game.focus(p.pid)
                drive_game.send(name, False)
                time.sleep(float(secs))
                drive_game.send(name, True)
            elif kind == "shot":
                path = os.path.join(out, f"{n:02d}-{arg}.png")
                print(("ok   " if soak_test.shot(p.pid, path) else "FAIL ") + path)
                n += 1
    finally:
        alive = p.poll() is None
        if alive:
            p.kill()
            p.wait()
        log.close()
        print("Vita3K was", "running" if alive else f"exited code {p.returncode}")


if __name__ == "__main__":
    main()
