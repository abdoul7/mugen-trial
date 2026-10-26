"""contact_sheet.py -- one row per soak-test folder: python tools/contact_sheet.py out.png id [id ...]"""
import glob, os, sys
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out, ids = sys.argv[1], sys.argv[2:]
W, H = 256, 192
rows = [sorted(glob.glob(os.path.join(ROOT, "reports", "soak", i, "*.png"))) for i in ids]
cols = max(len(r) for r in rows)
sheet = Image.new("RGB", (90 + cols * W, len(ids) * H), (20, 20, 20))
d = ImageDraw.Draw(sheet)
for y, (cid, shots) in enumerate(zip(ids, rows)):
    d.text((6, y * H + H // 2), cid, fill=(255, 255, 255))
    for x, s in enumerate(shots):
        sheet.paste(Image.open(s).convert("RGB").resize((W, H)), (90 + x * W, y * H))
sheet.save(out)
print(out, sheet.size)
