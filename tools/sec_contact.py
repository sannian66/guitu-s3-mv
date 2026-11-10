"""段落联系表：每个镜头（shots.json）取中点一帧，按段落帧区间出图，标镜号与时间。
  tools/cpu_slot.sh python3 tools/sec_contact.py <段落key> out.jpg [mid|beats]   （段落 key 见 units/sections.py）
  环境变量 V4_FORCE=<key> 让未 READY 的组也接入（组内自测）。"""
import os, sys, json
ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv'); sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + '/units')
os.chdir(ROOT)
from PIL import Image, ImageDraw, ImageFont
import sections as SEC
import render_sprite_full as R
key, out = sys.argv[1], sys.argv[2]
f0, f1 = [(a, b) for k, a, b, *_ in SEC.SECTIONS if k == key][0]
shots = [s for s in json.load(open('crew/shots.json')) if f0 <= round((s['t0'] + s['t1']) / 2 * 30) < f1]
font = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 22)
tw, th = 480, 270; cols = 4; rows = (len(shots) + cols - 1) // cols
sheet = Image.new('RGB', (cols * tw, rows * (th + 30)), (12, 12, 12)); d = ImageDraw.Draw(sheet)
for i, s in enumerate(shots):
    t = s['t0'] + 0.55 * (s['t1'] - s['t0']); f = int(round(t * 30))
    im = Image.fromarray(R.frame(f, {})).resize((tw, th), Image.LANCZOS)
    x, y = (i % cols) * tw, (i // cols) * (th + 30)
    sheet.paste(im, (x, y + 30)); d.text((x + 6, y + 2), f"{s['id']}  {t:.2f}s  {s['size']}", fill=(240, 220, 120), font=font)
    print(s['id'], round(t, 2), flush=True)
sheet.save(out, quality=88); print('saved', out)
