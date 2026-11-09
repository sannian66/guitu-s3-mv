"""[B组] 按帧号渲若干帧拼网格（自动按帧号选 pre1/verse2）：
  python3 tools/b_peek.py out.jpg f1 f2 ...      （>1 帧须 tools/cpu_slot.sh 包裹）
  FULL=1 另存全尺寸 /tmp/bp_<f>.png；COLS=n 改列数（默认 3）"""
import sys, os, time
ROOT = '/workspace/work/mv'; sys.path[:0] = [ROOT, ROOT + '/units', ROOT + '/lib']; os.chdir(ROOT)
os.environ.setdefault('SPRITE_MODE', '1')
from PIL import Image, ImageDraw, ImageFont
import sec_b_pre1 as P1, sec_b_verse2 as V2
out = sys.argv[1]; fs = [int(x) for x in sys.argv[2:]]
font = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 22)
TW, TH = 640, 360
ims = []
for f in fs:
    m = P1 if f < 2000 else V2
    a = time.time(); arr = m.frame(f, {}); im = Image.fromarray(arr)
    if os.environ.get('FULL'): im.save(f'/tmp/bp_{f}.png')
    im = im.resize((TW, TH), Image.LANCZOS)
    ImageDraw.Draw(im).text((6, 4), f'f{f} {f / 30:.2f}s', fill=(240, 220, 120), font=font); ims.append(im)
    print(f, round(time.time() - a, 2), flush=True)
cols = min(int(os.environ.get('COLS', 3)), len(ims)); rows = (len(ims) + cols - 1) // cols
sh = Image.new('RGB', (TW * cols, TH * rows))
for i, im in enumerate(ims): sh.paste(im, ((i % cols) * TW, (i // cols) * TH))
sh.save(out, quality=88)
