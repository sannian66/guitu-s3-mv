"""副歌一精灵版联系表：SPRITE_MODE=1 python3 lib/rig_test/c1_sprite_contact.py [out.jpg] [t ...]
默认每个人物镜头一帧（动作镜头每姿势一帧），左上角标镜号。"""
import sys, os, time
os.environ.setdefault('SPRITE_MODE', '1')
ROOT = '/workspace/work/mv'
for p in (ROOT, ROOT + '/lib', ROOT + '/units'): sys.path.insert(0, p)
import chorus1 as C
from PIL import Image, ImageDraw, ImageFont
X = C.Chorus1()
out = sys.argv[1] if len(sys.argv) > 1 else ROOT + '/lib/rig_test/c1_sprite_contact.jpg'
ts = [float(x) for x in sys.argv[2:]] or [60.55, 61.2, 61.75, 62.05, 63.2, 69.75, 69.95, 70.25, 72.9, 74.5, 75.6, 79.0, 82.6, 83.6, 84.15, 84.4, 84.8, 85.3]
font = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 28)
ims = []
for t in ts:
    a = time.time(); fr, _ = X.frame(t)
    sid = X.ids[X.idx(t)]
    im = Image.fromarray(C.to8(fr)).resize((640, 360))
    d = ImageDraw.Draw(im); d.text((10, 6), f'{sid}  {t:.2f}s', font=font, fill=(255, 220, 120))
    ims.append(im); print(f'{t:.2f} {sid} {time.time() - a:.2f}s', flush=True)
cols = 3; rows = (len(ims) + cols - 1) // cols
S = Image.new('RGB', (640 * cols, 360 * rows))
for k, i in enumerate(ims): S.paste(i, ((k % cols) * 640, (k // cols) * 360))
S.save(out, quality=86); print(out)
