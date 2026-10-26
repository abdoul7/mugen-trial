"""Extract a .7z archive, skipping Windows executables/libraries (never needed for a Vita build)."""
import sys, py7zr
SKIP = ('.exe', '.dll', '.bat',  # .cmd is a MUGEN command file, keep it
        '.scr', '.vbs', '.ps1')
src, dst = sys.argv[1], sys.argv[2]
with py7zr.SevenZipFile(src, 'r') as z:
    names = [n for n in z.getnames() if not n.lower().endswith(SKIP)]
    print(f"{len(names)} entries kept, {len(z.getnames()) - len(names)} skipped")
    z.extract(path=dst, targets=names)
