"""
shrink_snd.py -- rewrite a M.U.G.E.N .snd so it fits the Vita's memory budget.

A .snd is a container of WAV clips keyed by (group, number). Character audio is the
heaviest part of these characters (Bender: 16 MB of 44.1 kHz stereo). Every clip above
the target is re-encoded to mono at `rate` Hz (16-bit, or 8-bit if the source was 8-bit);
clips already at/below the target are kept byte-for-byte. Group/number ids are unchanged,
so the character's PlaySnd calls still resolve.

    python tools/shrink_snd.py in.snd out.snd [rate=22050]
    (build_assets.py calls shrink() directly)
"""

import struct
import subprocess
import sys

HEADER = 512


def _ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _wav_info(w):
    """(channels, rate, bits) from the fmt chunk, or None if this is not a PCM WAV."""
    if w[:4] != b"RIFF" or w[8:12] != b"WAVE":
        return None
    i = 12
    while i + 8 <= len(w):
        cid, size = w[i:i + 4], struct.unpack("<I", w[i + 4:i + 8])[0]
        if cid == b"fmt ":
            fmt, ch, rate, _, _, bits = struct.unpack("<HHIIHH", w[i + 8:i + 24])
            return (ch, rate, bits) if fmt == 1 else None
        i += 8 + size + (size & 1)
    return None


def _wav(pcm, rate, bits):
    ba = bits // 8
    return (b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE" +
            b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * ba, ba, bits) +
            b"data" + struct.pack("<I", len(pcm)) + pcm)


def _reencode(w, rate, bits):
    fmt, codec = ("u8", "pcm_u8") if bits == 8 else ("s16le", "pcm_s16le")
    r = subprocess.run([_ffmpeg(), "-loglevel", "error", "-f", "wav", "-i", "pipe:0", "-ac", "1", "-ar", str(rate),
                        "-c:a", codec, "-f", fmt, "pipe:1"], input=w, capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    return _wav(r.stdout, rate, bits)


def shrink(src, dst, rate=22050):
    d = open(src, "rb").read()
    if d[:12] != b"ElecbyteSnd\x00":
        raise ValueError(f"{src}: not an Elecbyte .snd")
    version = d[12:16]
    count, off = struct.unpack("<II", d[16:24])
    clips = []
    for _ in range(count):
        nxt, ln, grp, num = struct.unpack("<IIII", d[off:off + 16])
        clips.append((grp, num, d[off + 16:off + 16 + ln]))
        if not nxt:
            break
        off = nxt

    out_clips, changed = [], 0
    for grp, num, w in clips:
        info = _wav_info(w)
        if info and (info[0] > 1 or info[1] > rate):
            new = _reencode(w, min(rate, info[1]), 8 if info[2] == 8 else 16)
            if new and len(new) < len(w):
                w, changed = new, changed + 1
        out_clips.append((grp, num, w))

    body, pos = bytearray(), HEADER
    for k, (grp, num, w) in enumerate(out_clips):
        nxt = 0 if k == len(out_clips) - 1 else pos + 16 + len(w)
        body += struct.pack("<IIII", nxt, len(w), grp, num) + w
        pos += 16 + len(w)
    head = b"ElecbyteSnd\x00" + version + struct.pack("<II", len(out_clips), HEADER)
    with open(dst, "wb") as f:
        f.write(head.ljust(HEADER, b"\x00") + bytes(body))
    return len(d), HEADER + len(body), changed, len(out_clips)


if __name__ == "__main__":
    before, after, changed, n = shrink(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 22050)
    print(f"{before / 2**20:.1f} MB -> {after / 2**20:.1f} MB ({changed}/{n} clips re-encoded)")
