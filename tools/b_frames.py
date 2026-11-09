"""[B组] 按秒渲若干帧拼图：python3 tools/b_frames.py <pre1|verse2> out.jpg t1 t2 ...（>1 帧须 tools/cpu_slot.sh 包裹）"""
import sys, os, time
ROOT = '/workspace/work/mv'; sys.path[:0] = [ROOT, ROOT + '/units', ROOT + '/lib']; os.chdir(ROOT)
os.environ.setdefault('SPRITE_MODE', '1')
import importlib
from PIL import Image, ImageDraw, ImageFont
m = importlib.import_module('sec_b_' + sys.argv[1])
out = sys.argv[2]; ts = [float(x) for x in sys.argv[3:]]
font = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 20)
ims = []
for t in ts:
    a = time.time(); im = Image.fromarray(m.frame(int(round(t * 30)), {})).resize((640, 360), Image.LANCZOS)
    ImageDraw.Draw(im).text((6, 4), f'{t:.2f}s', fill=(240, 220, 120), font=font); ims.append(im)
    print(t, round(time.time() - a, 2), flush=True)
cols = min(4, len(ims)); rows = (len(ims) + cols - 1) // cols
sh = Image.new('RGB', (640 * cols, 360 * rows))
for i, im in enumerate(ims): sh.paste(im, ((i % cols) * 640, (i // cols) * 360))
sh.save(out, quality=86)
