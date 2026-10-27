"""
build_assets.py -- assemble the Jump Force Vita game tree from the downloaded sources.

Re-runnable: it wipes build/game and recreates it, so every change lives in this file
(or in roster.json), never as a hand edit inside build/.

    python tools/build_assets.py            # build build/game
    python tools/build_assets.py --no-music # skip the MP3 -> OGG step (fast rebuilds)
    python tools/build_assets.py --no-shrink # keep character .snd files untouched
    python tools/build_assets.py --skip-missing # leave out characters whose source folder is
                                                # absent (e.g. AK1 archives you haven't got)
    python tools/build_assets.py --no-minify    # do not minify character scripts
    python tools/build_assets.py --prune-states # enable conservative state pruning
    python tools/build_assets.py --prune-sprites # enable conservative sprite pruning
    python tools/build_assets.py --motif tbm    # override roster.json's "motif" for this build

What it does, in order:
  1. copies the Dolmexica 1.8 engine (Windows exe + Vita kit + stock assets) to build/game
  2. copies every character listed in roster.json into assets/chars/<id>/ and patches
     its .def: localcoord as configured, file references fixed to the exact on-disk case,
     unused/non-ASCII files dropped, .snd re-encoded to the Vita budget (shrink_snd.py)
  3. copies each character's stage to assets/stages/<id>.def/.sff with paths normalised
  4. converts the stage BGM from MP3 to OGG Vorbis (the Vita build cannot play MP3)
  5. writes assets/data/select.def
  6. if roster.json says "motif": "tbm", ports the TBM screenpack (tools/port_motif.py)
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_motif  # noqa: E402
import shrink_snd  # noqa: E402
import mugen_prune  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "engine", "Dolmexica Infinite 1.8")
OUT = os.path.join(ROOT, "build", "game")
ASSETS = os.path.join(OUT, "assets")

# engine folders not needed in the game tree (other platforms' kits, prebuilt samples)
ENGINE_SKIP = {"samples", "dreamcast", "web", "Dolmexica Infinite Make-your-own-game kit for Dreamcast.exe",
               "Dolmexica Infinite Make-your-own-game kit for Web.exe"}
# file keys in a character's [Files] section that point at a file next to the .def
FILE_KEY = re.compile(r"(cmd|cns|st\d*|stcommon|anim|sound|sprite|pal\d+|intro\.storyboard|ending\.storyboard)$", re.I)


def log(msg):
    print(msg, flush=True)


def read(path):
    with open(path, encoding="latin-1") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="latin-1", newline="\r\n") as f:
        f.write(text.replace("\r\n", "\n"))


def exact_case(folder, name):
    """Return `name` spelled the way it is on disk (Windows forgives case, the parser may not)."""
    want = name.replace("\\", "/")
    parts, cur = [], folder
    for p in want.split("/"):
        hit = next((e for e in os.listdir(cur) if e.lower() == p.lower()), None) if os.path.isdir(cur) else None
        if hit is None:
            return None
        parts.append(hit)
        cur = os.path.join(cur, hit)
    return "/".join(parts)


KEEP = object()  # roster entry has no "localcoord": leave the character's own value alone


CLS_LINE = re.compile(rb"(?m)^[^\x00-\x7f]*&cls[ \t]*\r?\n")


def strip_cls_padding(folder):
    """Remove lines that are only '<non-ASCII bytes>&cls' from a character's script files.

    Some AK1 downloads (vegito) pad every .def/.cns/.cmd with ~80,000 of them, apparently to hide the real
    text from editors. They mean nothing to MUGEN, but Dolmexica parses every line: ~8 MB of padding stalled
    the select screen on the Vita. Returns the number of lines removed."""
    n = 0
    for dp, _, fs in os.walk(folder):
        for f in fs:
            if os.path.splitext(f)[1].lower() not in (".def", ".cns", ".cmd", ".st", ".air", ".dat"):
                continue
            path = os.path.join(dp, f)
            data = open(path, "rb").read()
            if b"&cls" not in data:
                continue
            new, k = CLS_LINE.subn(b"", data)
            if k:
                open(path, "wb").write(new)
                n += k
    return n


def patch_char_def(def_path, localcoord, overrides=None):
    folder = os.path.dirname(def_path)
    text = read(def_path)
    overrides = {k.lower(): v for k, v in (overrides or {}).items()}
    out, section, changes = [], "", []
    junk = 0
    for line in text.replace("\r\n", "\n").split("\n"):
        s = line.strip()
        if not section and s and not s.startswith((";", "[")) and "=" not in s:
            # filler before the first section that is neither a comment nor a key (e.g. vegito's 80,000
            # "<BOM>&cls" lines that hide the real text from editors): the engine parses every line, and on
            # the Vita that stalled the select screen, so drop it
            junk += 1
            continue
        m = re.match(r"\[([^\]]+)\]", s)
        if m:
            section = m.group(1).strip().lower()
        kv = re.match(r"(\s*)([A-Za-z0-9.]+)(\s*=\s*)([^;]*?)(\s*(;.*)?)$", line)
        if kv and kv.group(2).lower() in overrides:
            line = f"{kv.group(1)}{kv.group(2)} = {overrides[kv.group(2).lower()]}"
            changes.append(f"{kv.group(2)}: {kv.group(4).strip()!r} -> {overrides[kv.group(2).lower()]!r}")
        elif kv and section == "info" and kv.group(2).lower() == "localcoord" and localcoord is not KEEP:
            if localcoord is None:
                changes.append(f"removed localcoord {kv.group(4)}")
                continue
            line = f"{kv.group(1)}localcoord = {localcoord}"
            changes.append(f"localcoord {kv.group(4)} -> {localcoord}")
        elif kv and section == "files" and FILE_KEY.match(kv.group(2)) and kv.group(4).strip():
            v = kv.group(4).strip().strip('"')
            fixed = exact_case(folder, v)
            if fixed is None and re.match(r"pal\d+$", kv.group(2), re.I):
                changes.append(f"dropped missing {kv.group(2)} = {v}")  # palette lives in the SFF v2
                continue
            if fixed and fixed != v:
                line = f"{kv.group(1)}{kv.group(2)}{kv.group(3)}{fixed}{kv.group(5)}"
                changes.append(f"{kv.group(2)}: {v} -> {fixed}")
        out.append(line)
    write(def_path, "\n".join(out))
    if junk:
        changes.append(f"dropped {junk} junk lines before [Info]")
    return changes


def apply_script_fixes(character_dir, fixes):
    """Apply exact, uniquely matching text replacements to copied character files."""
    root = os.path.realpath(character_dir)
    for fix in fixes:
        target = os.path.realpath(os.path.join(root, fix["file"]))
        if os.path.commonpath((root, target)) != root or target == root:
            raise ValueError("script fix must stay inside the character directory")
        original = read(target)
        find = fix["find"]
        if not find or original.count(find) != 1:
            raise ValueError(f"script fix must match exactly once: {fix['file']}")
        write(target, original.replace(find, fix["replace"], 1))


def compress_copied_character(def_path, data_dir, minify=True, prune_states=False, prune_sprites=False):
    stats = mugen_prune.compress_character(def_path, data_dir, minify, prune_states, prune_sprites)
    changes = []
    if minify:
        changes.append(f"minified {stats['minify_changed']}/{stats['minify_files']} files "
                       f"({stats['minify_before']}->{stats['minify_after']} bytes)")
    if prune_states:
        changes.append(f"states removed {stats['states_removed']}" +
                       (" (dynamic target: kept all)" if stats['states_dynamic'] else ""))
    if prune_sprites:
        changes.append(f"sprites removed {stats['sprites_removed']}/{stats['sprites_before']} "
                       f"({stats['sprite_before_bytes']}->{stats['sprite_after_bytes']} bytes)" +
                       (" (dynamic sprite: kept all)" if stats['sprites_dynamic'] else ""))
    return changes


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def to_ogg(src, dst, quality):
    if os.path.exists(dst) and os.path.getmtime(dst) > os.path.getmtime(src):
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", src, "-vn", "-map_metadata", "-1",
                    "-c:a", "libvorbis", "-q:a", str(quality), "-ar", "44100", "-ac", "2", dst], check=True)


def patch_stage_def(src_def, dst_def, stage_id, music):
    text = read(src_def).replace("\r\n", "\n")
    text = re.sub(r"(?im)^(\s*spr\s*=\s*)[^;\n]*", lambda m: f"{m.group(1)}{stage_id}.sff", text)
    text = re.sub(r"(?im)^(\s*bgmusic\s*=\s*)[^;\n]*", lambda m: f"{m.group(1)}{music}", text)
    write(dst_def, text)


def copy_engine():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    for e in os.listdir(ENGINE):
        if e in ENGINE_SKIP:
            continue
        s, d = os.path.join(ENGINE, e), os.path.join(OUT, e)
        (shutil.copytree if os.path.isdir(s) else shutil.copy2)(s, d)


def main():
    with open(os.path.join(ROOT, "roster.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    music = "--no-music" not in sys.argv
    no_shrink = "--no-shrink" in sys.argv
    minify = "--no-minify" not in sys.argv
    prune_states = "--prune-states" in sys.argv
    prune_sprites = "--prune-sprites" in sys.argv
    skip_missing = "--skip-missing" in sys.argv
    if "--motif" in sys.argv:  # try a motif without editing roster.json
        cfg["motif"] = sys.argv[sys.argv.index("--motif") + 1]
    demo = os.path.join(ROOT, cfg["demo_root"])
    music_cache = os.path.join(ROOT, "build", "ogg-cache")

    log("1. engine -> build/game")
    copy_engine()

    select_chars, extra_stages = [], []
    for c in cfg["characters"]:
        cid = c["id"]
        if c.get("source") == "stock":
            entry = c.get("def", cid)
            stock_def = os.path.join(ASSETS, "chars", cid, f"{cid}.def")
            if os.path.isfile(stock_def):
                changes = compress_copied_character(stock_def, os.path.join(ASSETS, "data"),
                                                    minify, prune_states, prune_sprites)
                log(f"2. char {cid:10s} <- stock  {'; '.join(changes) or 'compression disabled'}")
        else:
            src = os.path.join(ROOT, c["root"], c["folder"]) if "root" in c else os.path.join(demo, "Chars", c["folder"])
            if skip_missing and not os.path.isdir(src):
                log(f"2. char {cid:10s} SKIPPED: {os.path.relpath(src, ROOT)} not found (--skip-missing)")
                continue
            dst = os.path.join(ASSETS, "chars", cid)
            shutil.copytree(src, dst)
            for rel_src, rel_dst in c.get("copy_files", []):  # e.g. a common*.cns the char expects
                shutil.copy2(os.path.join(demo, exact_case(demo, rel_src)), os.path.join(dst, rel_dst))
            dropped = 0
            for pattern in c.get("drop_files", []):
                for p in glob.glob(os.path.join(dst, pattern)):
                    (shutil.rmtree if os.path.isdir(p) else os.remove)(p)
                    dropped += 1
            for dp, _, fs in os.walk(dst):  # non-ASCII names are a known parser crash
                for f in fs:
                    if not f.isascii():
                        os.remove(os.path.join(dp, f))
                        dropped += 1
            def_path = os.path.join(dst, c["def"])
            changes = patch_char_def(def_path, c["localcoord"] if "localcoord" in c else KEEP, c.get("def_overrides"))
            padding = strip_cls_padding(os.path.dirname(def_path))
            if padding:
                changes.append(f"stripped {padding} '&cls' padding lines from scripts")
            if c.get("portraits"):
                # wrong/missing select-screen portraits: rebuild 9000,0 and 9000,1 from another sprite
                import fix_portraits
                spr = re.search(r"(?im)^\s*sprite\s*=\s*([^;\r\n]+)", read(def_path)).group(1).strip()
                air = "".join(read(os.path.join(dst, f)) for f in os.listdir(dst) if f.lower().endswith(".air"))
                used = {(9000, int(m)) for m in re.findall(r"(?m)^\s*9000\s*,\s*(\d+)\s*,", air)}
                changes.append(fix_portraits.fix(os.path.join(dst, spr), c["portraits"]["from"], used))
            if c.get("sprite_cap"):
                # read by the Vita engine (tools/engine/patches/0002): this fighter's sprites above N px
                # are stored downscaled; other fighters keep the engine default (512)
                d = read(def_path)
                d = re.sub(r"(?im)^(\s*\[info\][^\n]*\n)", lambda m: f"{m.group(1)}jfv.spritecap = {int(c['sprite_cap'])}\n", d, count=1)
                write(def_path, d)
                changes.append(f"jfv.spritecap {c['sprite_cap']}")
            fixes = c.get("script_fixes", [])
            if fixes:
                apply_script_fixes(dst, fixes)
                changes.append(f"applied {len(fixes)} script fixes")
            changes.extend(compress_copied_character(def_path, os.path.join(ASSETS, "data"),
                                                      minify, prune_states, prune_sprites))
            snd = re.search(r"(?im)^\s*sound\s*=\s*([^;\r\n]+)", read(def_path))
            if snd and not no_shrink:
                sp = os.path.join(dst, snd.group(1).strip())
                before, after, _, _ = shrink_snd.shrink(sp, sp + ".tmp", c.get("snd_rate", cfg.get("snd_rate", 22050)))
                os.replace(sp + ".tmp", sp)
                changes.append(f"snd {before / 2**20:.1f}->{after / 2**20:.1f} MB")
            if dropped:
                changes.append(f"dropped {dropped} unused files")
            log(f"2. char {cid:10s} <- {c['folder']}  {'; '.join(changes) or 'no def changes'}")
            entry = f"{cid}/{c['def']}"

        stage_entry = "stages/kfm.def"
        st = c.get("stage")
        if st and st.get("source") == "stock":
            stage_entry = st["def"]
        elif st:
            sid = st["id"]
            sdir = os.path.join(demo, "Stages")
            src_def = os.path.join(sdir, exact_case(sdir, st["def"]))
            spr = re.search(r"(?im)^\s*spr\s*=\s*([^;\r\n]+)", read(src_def)).group(1).strip()
            src_sff = os.path.join(os.path.dirname(src_def), exact_case(os.path.dirname(src_def), spr))
            os.makedirs(os.path.join(ASSETS, "stages"), exist_ok=True)
            shutil.copy2(src_sff, os.path.join(ASSETS, "stages", f"{sid}.sff"))
            bgm = ""
            if st.get("music") and music:
                ogg = os.path.join(music_cache, f"{sid}.ogg")
                to_ogg(os.path.join(demo, exact_case(demo, st["music"])), ogg, cfg.get("ogg_quality", 3))
                os.makedirs(os.path.join(ASSETS, "sound"), exist_ok=True)
                shutil.copy2(ogg, os.path.join(ASSETS, "sound", f"{sid}.ogg"))
                bgm = f"sound/{sid}.ogg"
            patch_stage_def(src_def, os.path.join(ASSETS, "stages", f"{sid}.def"), sid, bgm)
            stage_entry = f"stages/{sid}.def"
            log(f"3. stage {sid:10s} <- {st['def']}  music={bgm or 'none'}")
        select_chars.append(f"{entry}, {stage_entry}")
        if stage_entry not in extra_stages:
            extra_stages.append(stage_entry)

    lines = ["; generated by tools/build_assets.py from roster.json -- do not edit by hand", "",
             "[Characters]"] + select_chars + (["randomselect"] if cfg.get("randomselect") else []) + \
            ["", "[ExtraStages]"] + extra_stages + ["", "[Options]",
             "arcade.maxmatches = " + cfg.get("arcade_maxmatches", "6,1,1,0,0,0,0,0,0,0"),
             "team.maxmatches = 4,1,1,0,0,0,0,0,0,0", ""]
    write(os.path.join(ASSETS, "data", "select.def"), "\n".join(lines))
    log(f"5. select.def: {len(select_chars)} characters, {len(extra_stages)} stages")

    slots = len(select_chars) + (1 if cfg.get("randomselect") else 0)
    if cfg.get("motif") != "tbm":
        # stock motif ships a 2x5 grid (27px cells + 2px spacing, 320x240 screen): widen it to 10
        # columns and add rows from the bottom up so every character gets a box
        cols = 10 if slots > 10 else 5
        rows = -(-slots // cols)
        sysdef = os.path.join(ASSETS, "data", "system.def")
        t = read(sysdef)
        top = min(170, 236 - rows * 29)
        grid = {"rows": rows, "columns": cols, "pos": f"{(320 - cols * 29) // 2},{top}",
                "p2.cursor.startcell": f"0,{cols - 1}"}
        if top < 170:
            # the stock layout puts 120x140 portraits at y=13 and the names/stage at y=162/237: a taller
            # grid would run over them, so shrink the portraits to end above the name line, and put the
            # names in the gap just above the grid (the stage name goes under the title: long names reach the middle)
            label_y = top - 6
            face = round(min(1.0, (label_y - 12 - 13) / 140), 2)
            grid.update({"p1.face.scale": f"{face},{face}", "p2.face.scale": f"{face},{face}",
                         "p1.name.offset": f"10,{label_y}", "p2.name.offset": f"309,{label_y}",
                         "stage.pos": "160,30"})  # under the title, between the portraits
        sel = re.search(r"(?is)\[Select Info\](.*?)(?=\n\[)", t)
        body = sel.group(1)
        for k, v in grid.items():
            body = re.sub(rf"(?im)^(\s*{re.escape(k)}\s*=\s*)[^;\n]*", lambda m, v=v: f"{m.group(1)}{v}", body)
        t = t[:sel.start(1)] + body + t[sel.end(1):]
        if top < 170:
            # [SelectBG 1] "Dark box" (a 320x62 trans=sub strip, tiled sideways) shades the stock 2-row grid at
            # y=166 inside window x 85-235. Re-fit it to the bigger grid: start at the grid's top, tile down too,
            # and clip it to the grid's outline -- otherwise it shows as a stray dark rectangle over the cells.
            x0 = (320 - cols * 29) // 2
            box = {"start": f"0, {top - 2}", "tile": "1,1",
                   "window": f"{x0 - 2},{top - 2}, {x0 + cols * 29},{top + rows * 29}"}
            bg = re.search(r"(?is)\[SelectBG 1\][^\n]*\n(.*?)(?=\n\[)", t)
            if bg:
                body = bg.group(1)
                for k, v in box.items():
                    body = re.sub(rf"(?im)^(\s*{re.escape(k)}\s*=\s*)[^;\n]*", lambda m, v=v: f"{m.group(1)}{v}", body)
                t = t[:bg.start(1)] + body + t[bg.end(1):]
        write(sysdef, t)
        log(f"6. stock select grid -> {rows}x{cols} for {slots} slots")

    if cfg.get("motif") == "tbm":
        fonts = port_motif.port(ASSETS, len(select_chars) + (1 if cfg.get("randomselect") else 0))
        log(f"6. motif: TBM screenpack re-laid-out for 4:3 (data/tbm, data/480p), fonts {', '.join(fonts)}")

    sizes = {}
    for dp, _, fs in os.walk(ASSETS):
        top = os.path.relpath(dp, ASSETS).split(os.sep)[0]
        sizes[top] = sizes.get(top, 0) + sum(os.path.getsize(os.path.join(dp, f)) for f in fs)
    log("assets: " + ", ".join(f"{k} {v / 2**20:.1f} MB" for k, v in sorted(sizes.items())) +
        f"  | total {sum(sizes.values()) / 2**20:.1f} MB")


if __name__ == "__main__":
    main()
