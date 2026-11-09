"""A 组快速核帧：python3 tools/a_peek.py out.jpg t1 t2 ...（>1 帧须 tools/cpu_slot.sh 包一层）→ 2 列网格，每格 960×540，左上标时间。
FULL=1 时另存全尺寸 /tmp/ap_<t>.png。"""
import os, sys
ROOT = '/workspace/work/mv'; sys.path[:0] = [ROOT, ROOT + '/units', ROOT + '/lib']; os.chdir(ROOT)
from PIL import Image, ImageDraw, ImageFont
import sec_a_intro_verse1 as M
out = sys.argv[1]; ts = [float(x) for x in sys.argv[2:]]
font = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 26)
cols = 2 if len(ts) > 1 else 1; rows = (len(ts) + cols - 1) // cols
sh = Image.new('RGB', (cols * 960, rows * 540)); d = ImageDraw.Draw(sh); c = {}
for i, t in enumerate(ts):
    im = Image.fromarray(M.frame(int(round(t * 30)), c))
    if os.environ.get('FULL'): im.save('/tmp/ap_%.2f.png' % t)
    x, y = (i % cols) * 960, (i // cols) * 540
    sh.paste(im.resize((960, 540), Image.LANCZOS), (x, y)); d.text((x + 8, y + 4), '%.2f' % t, fill=(255, 220, 90), font=font)
sh.save(out, quality=85); print('saved', out)
