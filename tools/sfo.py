"""sfo.py -- read/write PSF (param.sfo) files, so packaging needs no external vitasdk exe.

Layout: 20-byte header ("\0PSF", 0x101, key table offset, data table offset, count),
16-byte index entries (key offset, fmt, used len, max len, data offset), NUL-terminated
keys (table padded to 4 bytes), then each value padded to its max length.
fmt 0x0204 = UTF-8 string (NUL included in len), 0x0404 = uint32.
"""
import struct


def read(data):
    _, _, kt, dt, n = struct.unpack("<4sIIII", data[:20])
    out = []
    for i in range(n):
        ko, fmt, ln, mx, do = struct.unpack("<HHIII", data[20 + 16 * i:36 + 16 * i])
        key = data[kt + ko:data.index(b"\0", kt + ko)].decode()
        raw = data[dt + do:dt + do + ln]
        val = struct.unpack("<I", raw)[0] if fmt == 0x404 else raw.rstrip(b"\0").decode()
        out.append((key, fmt, mx, val))
    return out


def write(entries):
    entries = sorted(entries, key=lambda e: e[0])
    keys, index, values = b"", b"", b""
    for key, fmt, mx, val in entries:
        raw = struct.pack("<I", val) if fmt == 0x404 else val.encode() + b"\0"
        if len(raw) > mx:
            raise ValueError(f"{key}={val!r} longer than {mx}")
        index += struct.pack("<HHIII", len(keys), fmt, len(raw), mx, len(values))
        keys += key.encode() + b"\0"
        values += raw.ljust(mx, b"\0")
    keys = keys.ljust((len(keys) + 3) & ~3, b"\0")
    kt = 20 + len(index)
    return struct.pack("<4sIIII", b"\0PSF", 0x101, kt, kt + len(keys), len(entries)) + index + keys + values
