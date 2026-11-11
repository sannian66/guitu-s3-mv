"""候选原图联系表：python tools/r8d_ca/cands.py out.jpg 名1 名2 ...（绿幕原图照原样显示）"""
import sys, glob, os
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.expanduser('~/Downloads/gen_cands/R8_D/CA')
names = sys.argv[2:]
tw, th = 480, 270; cols = 3
S = Image.new('RGB', (cols * tw, ((len(names) + cols - 1) // cols) * (th + 24)), (10, 10, 10))
d = ImageDraw.Draw(S); fnt = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 18)
for k, n in enumerate(names):
    ps = sorted(glob.glob(f'{OUT}/{n}/*.png') + glob.glob(f'{OUT}/{n}/*.jpg'))
    if not ps: continue
    im = Image.open(ps[0]).convert('RGB').resize((tw, th), Image.LANCZOS)
    x, y = (k % cols) * tw, (k // cols) * (th + 24)
    S.paste(im, (x, y)); d.text((x + 4, y + th + 2), n, fill=(240, 220, 120), font=fnt)
S.save(sys.argv[1], quality=85)
