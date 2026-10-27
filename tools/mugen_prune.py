"""Lossless M.U.G.E.N script and asset pruning used by build_assets.py."""

import re
import struct
from pathlib import Path


def strip_script_comment(line):
    """Remove a M.U.G.E.N semicolon comment, ignoring semicolons in quotes."""
    in_quotes = False
    escaped = False
    for index, char in enumerate(line):
        if char == '"' and not escaped:
            in_quotes = not in_quotes
        if char == ";" and not in_quotes:
            return line[:index]
        if in_quotes and char == "\\":
            escaped = not escaped
        else:
            escaped = False
    return line


def minify_script(text):
    """Drop comments, blank lines and trailing whitespace without changing tokens."""
    output = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = strip_script_comment(line).rstrip()
        if line:
            output.append(line)
    return "\n".join(output) + ("\n" if output else "")


SECTION = re.compile(r"^[ \t]*\[([^\]\r\n]+)\][^\r\n]*(?:\r?\n|$)", re.I | re.M)
STATEDEF = re.compile(r"^statedef\s+([+-]?\d+)\s*$", re.I)
STATE_CONTROLLER = re.compile(r"^state(?!def)\b", re.I)
TARGET_KEYS = {
    "changestate": ("value",),
    "selfstate": ("value",),
    "targetstate": ("value",),
    "helper": ("stateno",),
    "hitdef": ("p1stateno", "p2stateno"),
}


def _controller_targets(text):
    type_match = re.search(r"(?im)^\s*type\s*=\s*([^\r\n]+)", text)
    if not type_match:
        return []
    controller = type_match.group(1).strip().lower()
    targets = []
    for key in TARGET_KEYS.get(controller, ()):
        value_match = re.search(rf"(?im)^\s*{key}\s*=\s*([^\r\n]+)", text)
        if value_match:
            targets.append(value_match.group(1).strip())
    return targets


def _parse_state_file(path, text):
    matches = list(SECTION.finditer(text))
    sections = []
    if not matches:
        return [{"text": text, "block": None}], [], False
    if matches[0].start():
        sections.append({"text": text[:matches[0].start()], "block": None})
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append({"header": match.group(1).strip(), "text": text[match.start():end], "block": None})

    blocks = []
    current = None
    invalid = False
    for section in sections:
        header = section.get("header", "")
        state_match = STATEDEF.match(header)
        if state_match:
            current = len(blocks)
            blocks.append({"file": path, "number": int(state_match.group(1)), "controllers": []})
            section["block"] = current
        elif header.lower().startswith("statedef"):
            current = None
            invalid = True
        elif STATE_CONTROLLER.match(header) and current is not None:
            section["block"] = current
            blocks[current]["controllers"].append(section["text"])
        else:
            current = None
    return sections, blocks, invalid


def _literal_state(value):
    return int(value) if re.fullmatch(r"[+-]?\d+", value.strip()) else None


def prune_state_scripts(files, common_files=frozenset(), command_files=frozenset()):
    """Return script text with only provably unreachable Statedef blocks removed.

    Common states and negative states are roots. Command-file targets are also roots,
    matching Dolmexica's command-driven entry points. A dynamic target reachable from
    a root disables pruning because its possible state set is not statically known.
    """
    parsed = {}
    blocks = []
    invalid = False
    for path, text in files.items():
        sections, file_blocks, file_invalid = _parse_state_file(path, text)
        block_offset = len(blocks)
        for section in sections:
            if section["block"] is not None:
                section["block"] += block_offset
        parsed[path] = sections
        blocks.extend(file_blocks)
        invalid = invalid or file_invalid

    by_number = {}
    for index, block in enumerate(blocks):
        block["index"] = index
        by_number.setdefault(block["number"], []).append(block)

    # The engine enters standard movement, intros, win/lose and hit states itself,
    # including character overrides that need not occur in common1.cns.
    engine_roots = {-3, -2, -1, 0, 10, 11, 12, 20, 40, 45, 51, 52, 120, 170, 180, 5120, 5500, 5900}
    reachable = {block["number"] for block in blocks if block["file"] in common_files or block["number"] in engine_roots}
    dynamic = invalid
    for block in blocks:
        if block["file"] not in command_files:
            continue
        for controller in block["controllers"]:
            for value in _controller_targets(controller):
                target = _literal_state(value)
                if target is None:
                    dynamic = True
                else:
                    reachable.add(target)

    queue = list(reachable)
    visited = set()
    while queue and not dynamic:
        number = queue.pop()
        for block in by_number.get(number, ()):
            if block["index"] in visited:
                continue
            visited.add(block["index"])
            for controller in block["controllers"]:
                for value in _controller_targets(controller):
                    target = _literal_state(value)
                    if target is None:
                        dynamic = True
                        break
                    if target not in reachable:
                        reachable.add(target)
                        queue.append(target)
                if dynamic:
                    break
            if dynamic:
                break

    if dynamic:
        return dict(files), {"removed": 0, "dynamic": True}

    output = {}
    for path, sections in parsed.items():
        kept = []
        for section in sections:
            block_index = section["block"]
            if block_index is not None and blocks[block_index]["number"] not in reachable:
                continue
            kept.append(section["text"])
        output[path] = "".join(kept)
    removed = sum(block["number"] not in reachable for block in blocks)
    return output, {"removed": removed, "dynamic": False}


FRAME_SPRITE = re.compile(r"(?im)^\s*(\d+)\s*,\s*(\d+)\s*,")
SPRITENO = re.compile(r"(?im)^\s*spriteno\s*=\s*([^\r\n]+)")


def collect_sprite_references(scripts, animations):
    """Return literal (group, item) references and whether any are dynamic.

    All animation frames are retained, which also covers every literal or dynamic
    ChangeAnim target. Dynamic spriteno expressions conservatively disable pruning.
    """
    references = set()
    dynamic = False
    for text in animations.values():
        references.update((int(match.group(1)), int(match.group(2))) for match in FRAME_SPRITE.finditer(text))
    for text in scripts.values():
        for match in SPRITENO.finditer(text):
            value = match.group(1).strip()
            literal = re.fullmatch(r"(\d+)\s*,\s*(\d+)", value)
            if literal:
                references.add((int(literal.group(1)), int(literal.group(2))))
            else:
                dynamic = True
    return references, dynamic


def _sff_stats(version, total, kept, dynamic, before_bytes, after_bytes):
    return {
        "version": version,
        "before": total,
        "kept": kept,
        "removed": total - kept,
        "dynamic": dynamic,
        "before_bytes": before_bytes,
        "after_bytes": after_bytes,
    }


def _parse_sff_v1(data):
    first = struct.unpack_from("<I", data, 24)[0]
    if first < 512 or first >= len(data):
        raise ValueError("SFF v1 has an invalid first sprite offset")
    records = []
    offset = first
    seen = set()
    while offset:
        if offset in seen or offset + 32 > len(data):
            raise ValueError("SFF v1 has a cyclic or out-of-bounds sprite chain")
        seen.add(offset)
        values = struct.unpack_from("<IIhhhhhB", data, offset)
        next_offset, length, _, _, group, item, link, same = values
        end = min(next_offset, len(data)) if next_offset > offset else len(data)
        available = end - offset - 32
        if length > available:
            if not same or length - available != 768:
                raise ValueError("SFF v1 sprite data is out of bounds")
            length = available
        header = bytearray(data[offset:offset + 32])
        struct.pack_into("<I", header, 4, length)
        records.append({
            "header": header,
            "data": data[offset + 32:offset + 32 + length],
            "length": length,
            "group": group,
            "item": item,
            "link": link,
            "same": same,
        })
        if next_offset in (0, len(data)):
            break
        if next_offset <= offset:
            raise ValueError("SFF v1 sprite chain does not advance")
        offset = next_offset
    return first, records


def _linked_closure(records, references):
    keep = {
        index for index, record in enumerate(records)
        if record["group"] == 9000 or (record["group"], record["item"]) in references
    }
    queue = list(keep)
    while queue:
        index = queue.pop()
        record = records[index]
        if record["length"]:
            continue
        target = record["link"]
        if not 0 <= target < len(records):
            raise ValueError(f"SFF linked sprite {index} targets invalid index {target}")
        if target not in keep:
            keep.add(target)
            queue.append(target)
    return keep


def _prune_sff_v1(data, references, dynamic, has_palette):
    first, records = _parse_sff_v1(data)
    if has_palette:
        references = set(references) | {(0, 0)}
    keep = _linked_closure(records, references)
    if dynamic or len(keep) == len(records):
        return data, _sff_stats(1, len(records), len(records), dynamic, len(data), len(data))

    current_palette = None
    dynamic_palette = bool(has_palette)
    for record in records:
        if has_palette and (record["group"], record["item"]) == (0, 0):
            dynamic_palette = True
        if not record["length"]:
            continue
        pcx = record["data"]
        if record["same"]:
            if current_palette is None and not dynamic_palette:
                raise ValueError("SFF v1 sprite inherits a missing palette")
            record["palette"] = None if dynamic_palette else current_palette
        else:
            if len(pcx) < 769 or pcx[-769] != 12:
                raise ValueError("SFF v1 own-palette sprite has no PCX palette")
            current_palette = pcx[-768:]
            if not (has_palette and (record["group"], record["item"]) == (0, 0)):
                dynamic_palette = False
            record["palette"] = None if dynamic_palette else current_palette

    ordered = sorted(keep)
    new_index = {old: new for new, old in enumerate(ordered)}
    prepared = []
    for old in ordered:
        record = records[old]
        header = bytearray(record["header"])
        sprite_data = record["data"]
        if record["length"] and record["same"] and record["palette"] is not None:
            if len(sprite_data) >= 769 and sprite_data[-769] == 12:
                sprite_data = sprite_data[:-768] + record["palette"]
            else:
                sprite_data += b"\x0c" + record["palette"]
            struct.pack_into("<I", header, 4, len(sprite_data))
            header[18] = 0
        elif not record["length"]:
            struct.pack_into("<h", header, 16, new_index[record["link"]])
        prepared.append((old, header, sprite_data))

    offsets = {}
    offset = first
    for old, _, sprite_data in prepared:
        offsets[old] = offset
        offset += 32 + len(sprite_data)
    header = bytearray(data[:first])
    groups = {records[old]["group"] for old in ordered}
    struct.pack_into("<II", header, 16, len(groups), len(ordered))
    output = bytearray(header)
    for position, (old, sprite_header, sprite_data) in enumerate(prepared):
        next_offset = offsets[prepared[position + 1][0]] if position + 1 < len(prepared) else 0
        struct.pack_into("<I", sprite_header, 0, next_offset)
        output += sprite_header
        output += sprite_data
    return bytes(output), _sff_stats(1, len(records), len(ordered), False, len(data), len(output))


def _pad4(data):
    data += b"\x00" * ((-len(data)) % 4)


def _parse_sff_v2(data):
    sprite_offset, sprite_total, palette_offset, palette_total = struct.unpack_from("<IIII", data, 36)
    ldata_offset, ldata_length, tdata_offset, tdata_length = struct.unpack_from("<IIII", data, 52)
    if sprite_offset + sprite_total * 28 > len(data) or palette_offset + palette_total * 16 > len(data):
        raise ValueError("SFF v2 tables are out of bounds")
    palettes = []
    for index in range(palette_total):
        raw = bytearray(data[palette_offset + index * 16:palette_offset + (index + 1) * 16])
        data_offset, data_length = struct.unpack_from("<II", raw, 8)
        if ldata_offset + data_offset + data_length > len(data):
            raise ValueError("SFF v2 palette data is out of bounds")
        palettes.append({"header": raw, "data": data[ldata_offset + data_offset:ldata_offset + data_offset + data_length]})
    records = []
    for index in range(sprite_total):
        raw = bytearray(data[sprite_offset + index * 28:sprite_offset + (index + 1) * 28])
        group, item, _, _, _, _, link, _, _, data_offset, length, _, flags = struct.unpack(
            "<HHHHhhHBBIIHH", raw
        )
        base = tdata_offset if flags else ldata_offset
        if length and base + data_offset + length > len(data):
            raise ValueError("SFF v2 sprite data is out of bounds")
        records.append({
            "header": raw,
            "data": data[base + data_offset:base + data_offset + length] if length else b"",
            "length": length,
            "group": group,
            "item": item,
            "link": link,
            "flags": flags,
        })
    lengths_are_ends = ldata_length == tdata_offset and tdata_length == len(data)
    return palettes, records, lengths_are_ends


def _prune_sff_v2(data, references, dynamic):
    palettes, records, lengths_are_ends = _parse_sff_v2(data)
    keep = _linked_closure(records, references)
    if dynamic or len(keep) == len(records):
        return data, _sff_stats(2, len(records), len(records), dynamic, len(data), len(data))

    ordered = sorted(keep)
    new_index = {old: new for new, old in enumerate(ordered)}
    ldata = bytearray()
    tdata = bytearray()
    palette_headers = []
    for palette in palettes:
        header = bytearray(palette["header"])
        _pad4(ldata)
        struct.pack_into("<I", header, 8, len(ldata))
        ldata += palette["data"]
        palette_headers.append(header)

    sprite_headers = []
    for old in ordered:
        record = records[old]
        header = bytearray(record["header"])
        if record["length"]:
            target = tdata if record["flags"] else ldata
            _pad4(target)
            struct.pack_into("<I", header, 16, len(target))
            target += record["data"]
        else:
            struct.pack_into("<H", header, 12, new_index[record["link"]])
        sprite_headers.append(header)

    palette_offset = 512
    sprite_offset = palette_offset + len(palette_headers) * 16
    ldata_offset = sprite_offset + len(sprite_headers) * 28
    tdata_offset = ldata_offset + len(ldata)
    header = bytearray(data[:512])
    struct.pack_into("<IIII", header, 36, sprite_offset, len(ordered), palette_offset, len(palette_headers))
    final_size = tdata_offset + len(tdata)
    struct.pack_into(
        "<IIII", header, 52, ldata_offset,
        tdata_offset if lengths_are_ends else len(ldata),
        tdata_offset,
        final_size if lengths_are_ends else len(tdata),
    )
    output = bytearray(header)
    for palette_header in palette_headers:
        output += palette_header
    for sprite_header in sprite_headers:
        output += sprite_header
    output += ldata
    output += tdata
    return bytes(output), _sff_stats(2, len(records), len(ordered), False, len(data), len(output))


def prune_sff(data, references, dynamic=False, has_palette=False):
    """Rewrite an SFF v1/v2 with unreferenced sprites and orphan data removed."""
    if len(data) < 512 or data[:12] != b"ElecbyteSpr\x00":
        raise ValueError("Not an Elecbyte SFF file")
    if data[15] == 1:
        return _prune_sff_v1(data, references, dynamic, has_palette)
    if data[15] == 2:
        return _prune_sff_v2(data, references, dynamic)
    raise ValueError(f"Unsupported SFF version byte {data[15]}")


def _read_text(path):
    with open(path, encoding="latin-1") as handle:
        return handle.read()


def _write_text(path, text):
    with open(path, "w", encoding="latin-1", newline="\r\n") as handle:
        handle.write(text.replace("\r\n", "\n"))


def _definition_files(def_path):
    text = _read_text(def_path)
    section = re.search(r"(?ims)^\s*\[files\][^\r\n]*(?:\r?\n|$)(.*?)(?=^\s*\[|\Z)", text)
    if not section:
        return {}
    return {
        match.group(1).lower(): match.group(2).strip().strip('"')
        for match in re.finditer(r"(?im)^\s*([a-z0-9.]+)\s*=\s*([^;\r\n]+)", section.group(1))
        if match.group(2).strip()
    }


def _inside(path, folder):
    try:
        path.resolve().relative_to(folder.resolve())
        return True
    except ValueError:
        return False


def compress_character(def_path, data_dir, minify=True, prune_states=True, prune_sprites=True):
    """Apply configured compression to one copied character and return measured stats."""
    def_path = Path(def_path)
    data_dir = Path(data_dir)
    char_root = def_path.parent
    definitions = _definition_files(def_path)

    def resolve(value):
        local = char_root / value.replace("\\", "/")
        if local.is_file():
            return local
        shared = data_dir / value.replace("\\", "/")
        return shared if shared.is_file() else local

    script_paths = {}
    for key, value in definitions.items():
        if re.fullmatch(r"(?:cmd|cns|stcommon|st\d*|anim)", key):
            path = resolve(value)
            if path.is_file():
                script_paths[key] = path

    stats = {
        "minify_files": 0,
        "minify_changed": 0,
        "minify_before": 0,
        "minify_after": 0,
        "states_removed": 0,
        "states_dynamic": False,
        "sprites_removed": 0,
        "sprites_dynamic": False,
        "sprites_before": 0,
        "sprites_kept": 0,
        "sprite_before_bytes": 0,
        "sprite_after_bytes": 0,
    }

    if minify:
        loaded_paths = set(script_paths.values())
        candidates = []
        for path in char_root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() in {".cns", ".cmd", ".air", ".st", ".def"} or path in loaded_paths:
                candidates.append(path)
        for path in sorted(set(candidates)):
            before = path.stat().st_size
            original = _read_text(path)
            minified = minify_script(original)
            if minified != original:
                _write_text(path, minified)
            after = path.stat().st_size
            stats["minify_files"] += 1
            stats["minify_changed"] += minified != original
            stats["minify_before"] += before
            stats["minify_after"] += after

    state_paths = {key: path for key, path in script_paths.items() if key != "anim"}
    if prune_states and state_paths:
        texts = {path: _read_text(path) for path in set(state_paths.values())}
        common_files = {state_paths["stcommon"]} if "stcommon" in state_paths else set()
        command_files = {state_paths["cmd"]} if "cmd" in state_paths else set()
        rewritten, state_stats = prune_state_scripts(texts, common_files, command_files)
        stats["states_removed"] = state_stats["removed"]
        stats["states_dynamic"] = state_stats["dynamic"]
        for path, text in rewritten.items():
            if _inside(path, char_root) and text != texts[path]:
                _write_text(path, text)

    if prune_sprites and definitions.get("sprite"):
        sprite_path = resolve(definitions["sprite"])
        scripts = {path: _read_text(path) for path in set(state_paths.values())}
        animations = {script_paths["anim"]: _read_text(script_paths["anim"])} if "anim" in script_paths else {}
        references, dynamic = collect_sprite_references(scripts, animations)
        if sprite_path.is_file() and _inside(sprite_path, char_root):
            original = sprite_path.read_bytes()
            has_palette = any(re.fullmatch(r"pal\d+", key) and resolve(value).is_file()
                              for key, value in definitions.items())
            rewritten, sprite_stats = prune_sff(original, references, dynamic, has_palette)
            if rewritten != original:
                sprite_path.write_bytes(rewritten)
            stats.update({
                "sprites_removed": sprite_stats["removed"],
                "sprites_dynamic": sprite_stats["dynamic"],
                "sprites_before": sprite_stats["before"],
                "sprites_kept": sprite_stats["kept"],
                "sprite_before_bytes": sprite_stats["before_bytes"],
                "sprite_after_bytes": sprite_stats["after_bytes"],
            })
    return stats
