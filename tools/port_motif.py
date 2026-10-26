"""
port_motif.py -- re-lay-out the TBM 1.1 screenpack (1280x720) for Dolmexica on Vita.

The art is kept as-is; only the coordinates are rewritten, because Dolmexica scales
motif sprites from the declared localcoord (titlescreen.cpp: transformDreamCoordinates
uses localcoord.x) and the fight HUD from a fixed 320 or 640 coordinate space
(fightui.cpp: data/480p/fight.def selects 640).

  system.def  localcoord 1280,720 -> 960,720 (4:3, same height, so art keeps its scale)
              absolute screen positions shift x-160 (centre crop of the 16:9 layout);
              background `start` values are centre-relative in MUGEN and need no change
              select grid rebuilt for the real roster; team / unsupported menu items hidden
              logo + intro + game-over storyboards dropped (Intro.sff alone is 34 MB)
  fight.def   -> data/480p/fight.def: every top-level position/offset/spacing/range halved
              (1280 -> 640 space); HUD sprites halved via each element's .scale because
              Dolmexica also applies [FightFx] scale to the HUD (fightui.cpp:642)
  music       Title/Select/Versus/Victory MP3 -> OGG

    python tools/port_motif.py <assets dir> <character count>
(build_assets.py calls port() when roster.json has "motif": "tbm")
"""

import math
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.path.join(ROOT, "source", "screenpack", "TBM 1.1 2020")
SHIFT_X = -160          # 1280-wide layout centred in a 960-wide (4:3) frame
COLUMNS = 10            # select grid width for a 9..57 character roster
CELL = 53               # the author's alternate (large) cell size

# absolute screen-space keys per system.def section (x is shifted, y untouched)
ABSOLUTE = {
    "title info": {"menu.pos"},
    "select info": {"pos", "title.offset", "stage.pos", "p1.face.offset", "p2.face.offset",
                    "p1.name.offset", "p2.name.offset"},
    "vs screen": {"match.offset", "p1.offset", "p2.offset", "p1.name.offset", "p2.name.offset"},
    "victory screen": {"p1.offset", "p1.name.offset", "winquote.offset"},
    "continue screen": {"pos"},
    "win screen": {"wintext.offset"},
    "survival results screen": {"winstext.offset"},
}
HIDDEN_MENU = ["teamarcade", "teamversus", "teamcoop", "survivalcoop", "netplay", "freeplay", "credits",
               "story", "osu", "superwatch", "randomwatch"]
FIGHT_HALVE = re.compile(r"(^|\.)(pos|offset|spacing|range\.x|range|window|margins?|displaytime\.x)$", re.I)
FIGHT_SPRITE = re.compile(r"^(.*)\.(anim|spr)$", re.I)


def read(p):
    with open(p, encoding="latin-1") as f:
        return f.read().replace("\r\n", "\n")


def write(p, t):
    with open(p, "w", encoding="latin-1", newline="\r\n") as f:
        f.write(t)


def nums(v):
    return [x.strip() for x in v.split(",")]


def fmt(x):
    x = round(x, 3)
    return str(int(x)) if x == int(x) else str(x)


def first_value(line):
    """MUGEN treats ';' as a comment: `cell.size = 26,26;53,53;` really means 26,26.
    Returns (key, live value, alternate value after the first ';' or None)."""
    m = re.match(r"\s*([A-Za-z0-9._]+)\s*=\s*(.*)$", line)
    if not m:
        return None
    body = m.group(2)
    parts = body.split(";")
    alt = parts[1].strip() if len(parts) > 1 and re.match(r"^[-\d.,\s]+$", parts[1].strip() or "x") else None
    return m.group(1), parts[0].strip(), alt


def to_ogg(src, dst):
    import imageio_ffmpeg
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", src, "-vn", "-map_metadata", "-1",
                    "-c:a", "libvorbis", "-q:a", "3", "-ar", "44100", "-ac", "2", dst], check=True)


def port_system(assets, nchars):
    src = read(os.path.join(SP, "Data", "System.def"))
    rows = max(1, math.ceil(nchars / COLUMNS))
    grid_w = COLUMNS * CELL
    grid = {  # select screen rebuilt around the author's alternate 53px cells
        "rows": str(rows), "columns": str(COLUMNS), "pos": f"{(960 - grid_w) // 2},{206}",
        "cell.size": f"{CELL},{CELL}", "cell.spacing": "0,0", "showemptyboxes": "0", "moveoveremptyboxes": "0",
        "p1.cursor.startcell": "0,0", "p2.cursor.startcell": f"0,{min(COLUMNS, nchars) - 1}",
        "p1.cursor.active.anim": "352", "p2.cursor.active.anim": "353",
        "p1.cursor.done.spr": "161,2", "p2.cursor.done.spr": "161,3", "portrait.scale": ".5,.5",
    }
    out, section, seen = [], "", set()
    for line in src.split("\n"):
        m = re.match(r"\s*\[([^\]]+)\]", line)
        if m:
            if section == "select info":
                out += [f"{k} = {v}" for k, v in grid.items() if k not in seen]
            if section == "title info":
                out += [f'menu.itemname.{k} = ""' for k in HIDDEN_MENU if f"menu.itemname.{k}" not in seen]
            section, seen = m.group(1).strip().lower(), set()
            out.append(line)
            continue
        kv = first_value(line)
        if not kv:
            out.append(line)
            continue
        key, val, _ = kv
        k = key.lower()
        seen.add(k)
        if section == "info" and k == "localcoord":
            line = "localcoord = 960,720"
        elif section == "files" and k in ("logo.storyboard", "intro.storyboard"):
            line = f"{key} ="
        elif section == "music" and k.endswith(".bgm") and val:
            name = os.path.splitext(os.path.basename(val.replace("\\", "/")))[0].lower()
            line = f"{key} = sound/tbm_{name}.ogg"
        elif section == "title info" and k.startswith("menu.itemname.") and k[14:] in HIDDEN_MENU:
            line = f'{key} = ""'
        elif section == "select info" and k in grid:
            line = f"{key} = {grid[k]}"
        elif section in ABSOLUTE and k in ABSOLUTE[section]:
            v = nums(val)
            v[0] = fmt(float(v[0]) + SHIFT_X)
            line = f"{key} = {','.join(v)}"
        elif section == "victory screen" and k == "winquote.window":
            v = [float(x) for x in nums(val)]
            line = f"{key} = {fmt(v[0])},{fmt(v[1])},{fmt(min(959, v[2] + SHIFT_X))},{fmt(v[3])}"
        elif section == "game over screen" and k in ("enabled", "storyboard"):
            line = f"{key} = 0" if k == "enabled" else f"{key} ="  # GameOver.sff (8 MB) not shipped
        elif section == "demo mode" and k == "intro.waitcycles":
            line = f"{key} = 99"
        out.append(line)
    return "\n".join(out)


def port_fight():
    src = read(os.path.join(SP, "Data", "Fight.def"))
    out, section, comps, scaled = [], "", set(), set()

    def flush_scales():
        # elements that draw a sprite but declare no .scale still need the 0.5 HUD scale
        return [f"{c}.scale = .5,.5" for c in sorted(comps - scaled)]

    for line in src.split("\n"):
        m = re.match(r"\s*\[([^\]]+)\]", line)
        if m:
            if section and not section.startswith("begin action"):
                out += flush_scales()
            section, comps, scaled = m.group(1).strip().lower(), set(), set()
            out.append(line)
            continue
        if section.startswith("begin action"):
            out.append(line)  # animation frames are in sprite space: untouched
            continue
        kv = first_value(line)
        if not kv:
            out.append(line)
            continue
        key, val, _ = kv
        k = key.lower()
        sm = FIGHT_SPRITE.match(k)
        if sm:
            comps.add(sm.group(1))
        if section == "fightfx" and k == "scale":
            line = "scale = 1"  # 2 in 1280 space == 1 in 640 space for hit sparks
        elif k.endswith(".scale") and re.match(r"^[-\d.,\s]+$", val):
            comps.add(k[:-6])
            scaled.add(k[:-6])
            line = f"{key} = {','.join(fmt(float(x) * 0.5) for x in nums(val))}"
        elif FIGHT_HALVE.search(k) and re.match(r"^[-\d.,\s]+$", val):
            line = f"{key} = {','.join(fmt(round(float(x) * 0.5)) for x in nums(val) if x)}"
        out.append(line)
    out += flush_scales()
    return "\n".join(out)


def copy_ci(src_dir, name, dst):
    hit = next((e for e in os.listdir(src_dir) if e.lower() == name.lower()), None)
    if hit is None:
        raise FileNotFoundError(os.path.join(src_dir, name))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(os.path.join(src_dir, hit), dst)


def referenced_fonts(text):
    return {v.strip() for v in re.findall(r"(?im)^[ \t]*font\d+[ \t]*=[ \t]*([^;\n]*)", text) if v.strip()}


def port(assets, nchars):
    data, sp_data, sp_font = os.path.join(assets, "data"), os.path.join(SP, "Data"), os.path.join(SP, "Font")
    tbm = os.path.join(data, "tbm")
    p480 = os.path.join(data, "480p")
    os.makedirs(os.path.join(tbm, "00"), exist_ok=True)
    os.makedirs(p480, exist_ok=True)

    system = port_system(assets, nchars)
    write(os.path.join(tbm, "system.def"), system)
    copy_ci(sp_data, "System.sff", os.path.join(tbm, "system.sff"))
    copy_ci(sp_data, "System.snd", os.path.join(tbm, "system.snd"))
    for sff in re.findall(r"(?im)^\s*spr\s*=\s*(00/[^;\s]+)", system):
        copy_ci(os.path.join(sp_data, "00"), os.path.basename(sff), os.path.join(tbm, "00", os.path.basename(sff)))
    shutil.copy2(os.path.join(data, "select.def"), os.path.join(tbm, "select.def"))

    fight = port_fight()
    write(os.path.join(p480, "fight.def"), fight)
    for f in ("Fight.sff", "Fight.snd", "FightFX.sff", "FightFX.air"):
        copy_ci(sp_data, f, os.path.join(p480, f.lower()))
    shutil.copy2(os.path.join(data, "common.snd"), os.path.join(p480, "common.snd"))  # engine's own

    fonts = referenced_fonts(system) | referenced_fonts(fight)
    for fdef in sorted(fonts):
        for dst_dir in (os.path.join(assets, "font"),):
            copy_ci(sp_font, fdef, os.path.join(dst_dir, fdef))
            body = read(os.path.join(sp_font, next(e for e in os.listdir(sp_font) if e.lower() == fdef.lower())))
            m = re.search(r"(?im)^\s*file\s*=\s*([^;\n]+)", body)
            if m:
                copy_ci(sp_font, m.group(1).strip(), os.path.join(dst_dir, m.group(1).strip()))

    for track in ("Title", "Select", "Versus", "Victory"):
        to_ogg(os.path.join(sp_data, "00", f"{track}.mp3"), os.path.join(assets, "sound", f"tbm_{track.lower()}.ogg"))

    cfg = os.path.join(data, "mugen.cfg")
    t = read(cfg)
    t = re.sub(r"(?im)^(\s*motif\s*=\s*)[^;\n]*", r"\1data/tbm/system.def", t)
    write(cfg, t)
    return sorted(fonts)


if __name__ == "__main__":
    print(port(sys.argv[1], int(sys.argv[2])))
