"""drive_game.py -- launch the Windows Dolmexica build, press keys, take screenshots.

    python tools/drive_game.py <out_dir> "<script>"

The script is a space-separated list of steps:
    wait:<seconds>     sleep
    key:<name>[*n]     tap a key n times (names: up down left right return a s q w e d y u ...)
    hold:<name>:<sec>  hold a key
    shot:<label>       screenshot of the game window only (PrintWindow) -> <out_dir>/<nn>-<label>.png
The game window is brought to the foreground for key input (SendInput needs focus).
Example (title -> versus -> pick P1/P2 -> fight):
    python tools/drive_game.py reports/drive/run1 "wait:4 shot:title key:down key:return wait:2 shot:select"
"""

import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import soak_test  # noqa: E402  (window_of / shot helpers)

user32 = ctypes.windll.user32
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "build", "game")
EXE = os.path.join(GAME, "Dolmexica Infinite for Windows.exe")

# hardware scan codes (set 1); E0-extended keys flagged with 0x100
SCAN = {"esc": 0x01, "return": 0x1C, "enter": 0x1C, "space": 0x39, "up": 0x148, "down": 0x150, "left": 0x14B, "right": 0x14D,
        "f1": 0x3B, "f2": 0x3C, "f3": 0x3D, "f4": 0x3E, "f5": 0x3F}
for i, ch in enumerate("qwertyuiop"):
    SCAN[ch] = 0x10 + i
for i, ch in enumerate("asdfghjkl"):
    SCAN[ch] = 0x1E + i
for i, ch in enumerate("zxcvbnm"):
    SCAN[ch] = 0x2C + i
for i, ch in enumerate("1234567890"):
    SCAN[ch] = 0x02 + i

INPUT_KEYBOARD, KEYEVENTF_KEYUP, KEYEVENTF_SCANCODE, KEYEVENTF_EXTENDEDKEY = 1, 0x2, 0x8, 0x1


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("pad", ctypes.c_byte * 32)]
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _U)]


def send(name, up):
    code = SCAN[name]
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_EXTENDEDKEY if code & 0x100 else 0) | (KEYEVENTF_KEYUP if up else 0)
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.ki = KEYBDINPUT(0, code & 0xFF, flags, 0, 0)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def focus(pid):
    hwnd = soak_test.window_of(pid)
    if hwnd and user32.GetForegroundWindow() != hwnd:
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        send("0", False)  # the first key event after a focus change is swallowed: spend it on
        time.sleep(0.08)  # a key the game doesn't use
        send("0", True)
        time.sleep(0.3)
    return hwnd


def main():
    out, script = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    p = subprocess.Popen([EXE], cwd=GAME)
    n = 0
    try:
        for step in script.split():
            kind, _, arg = step.partition(":")
            if p.poll() is not None:
                print(f"game exited (code {p.returncode}) before step {step}")
                break
            if kind == "wait":
                time.sleep(float(arg))
            elif kind == "key":
                name, _, times = arg.partition("*")
                for _ in range(int(times or 1)):
                    focus(p.pid)
                    send(name, False)
                    time.sleep(0.08)
                    send(name, True)
                    time.sleep(0.25)
            elif kind == "hold":
                name, secs = arg.split(":")
                focus(p.pid)
                send(name, False)
                time.sleep(float(secs))
                send(name, True)
            elif kind == "shot":
                path = os.path.join(out, f"{n:02d}-{arg}.png")
                print(("ok   " if soak_test.shot(p.pid, path) else "FAIL ") + path)
                n += 1
    finally:
        alive = p.poll() is None
        if alive:
            p.kill()
            p.wait()
        print("game was", "running" if alive else f"exited code {p.returncode}")


if __name__ == "__main__":
    main()
