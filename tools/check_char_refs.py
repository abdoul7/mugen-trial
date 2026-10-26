"""For each character .def: print mugenversion/localcoord and any referenced file that is
missing or only matches with different letter case (the #1 Dolmexica crash cause)."""
import os, re, sys
root = sys.argv[1]
KEYS = ('cmd', 'cns', 'st', 'stcommon', 'anim', 'sound', 'sprite', 'pal', 'intro.storyboard', 'ending.storyboard')
for dp, _, fs in os.walk(root):
    for f in fs:
        if not f.lower().endswith('.def') or 'intro' in f.lower() or 'ending' in f.lower():
            continue
        p = os.path.join(dp, f)
        txt = open(p, encoding='latin-1').read()
        if not re.search(r'(?im)^\s*\[files\]', txt):
            continue
        ver = re.search(r'(?im)^\s*mugenversion\s*=\s*([^\r\n;]+)', txt)
        lc = re.search(r'(?im)^\s*localcoord\s*=\s*([^\r\n;]+)', txt)
        print(f"== {os.path.relpath(p, root)}  mugenversion={ver.group(1).strip() if ver else '-'}  localcoord={lc.group(1).strip() if lc else '-'}")
        for m in re.finditer(r'(?im)^\s*([a-z0-9.]+)\s*=\s*([^\r\n;]+)', txt.split('[Files]')[-1].split('[')[0] if '[Files]' in txt else ''):
            k, v = m.group(1).lower(), m.group(2).strip().strip('"')
            if not (k in KEYS or re.match(r'(st\d*|pal\d+)$', k)) or not v:
                continue
            ref = os.path.normpath(os.path.join(dp, v.replace(chr(92), '/')))
            if os.path.exists(ref):
                real = os.listdir(os.path.dirname(ref))
                if os.path.basename(ref) not in real:
                    print(f"   CASE  {k} = {v}")
            elif not os.path.exists(os.path.normpath(os.path.join(root, '..', 'Data', v))):
                print(f"   MISSING {k} = {v}")
