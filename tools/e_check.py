"""tools/e_check.py — E 组核查小样：渲若干帧拼成网格（每格 640 宽）。用法：python3 tools/e_check.py out.jpg f1 f2 ...（多帧须 cpu_slot）"""
import sys, os, time
ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv')
sys.path.insert(0, ROOT + '/units'); sys.path.insert(0, ROOT)
os.environ.setdefault('V4_FORCE', 'e_final_outro')
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sec_e_final_outro as S
out = sys.argv[1]; fs = [int(x) for x in sys.argv[2:]]
tw = int(os.environ.get('TW', 640)); th = tw * 9 // 16; cols = 3
G = Image.new('RGB', (cols * tw, ((len(fs) + cols - 1) // cols) * (th + 22)), (10, 10, 10)); d = ImageDraw.Draw(G)
fnt = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Regular.otf', 15); cache = {}
for i, f in enumerate(fs):
    a = time.time(); fr = S.frame(f, cache)
    if os.environ.get('FULL'): Image.fromarray(fr).save('/tmp/e_%d.png' % f)
    im = Image.fromarray(fr).resize((tw, th), Image.LANCZOS)
    x, y = (i % cols) * tw, (i // cols) * (th + 22)
    G.paste(im, (x, y + 22)); d.text((x + 4, y + 2), 'f%d %.2fs  %s' % (f, f / 30, S.IDS[max(k for k in range(len(S.SHOTS)) if S.BOUNDS[k] <= f)]), font=fnt, fill=(230, 210, 150))
    print(f, '%.1fs' % (time.time() - a), flush=True)
G.save(out, quality=88)
