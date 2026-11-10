"""tools/r6_contact.py — 成片联系表：每 2 秒一格（0,2,…,240s），从成片 mp4 抽帧。
  python3 tools/r6_contact.py out/render_r6/guitu_s3_mv_r6.mp4
产物：out/round6/FULL_r6_contact.jpg（总览 11 列 × 145px，≤1600 宽）+ FULL_r6_contact_p1..p4.jpg（5 列 × 320px，含字幕区可读）。"""
import sys, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont
src = sys.argv[1]
ROOT = '/workspace/work/mv'
fnt = lambda s: ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', s)
# 一次解码：每 60 帧取一帧（fps=0.5 会取区间中点，改用 select 取 n%60==0）
r = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-vf', "select=not(mod(n\\,60)),scale=320:180:flags=area", '-vsync', '0',
                    '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE, check=True)
fr = np.frombuffer(r.stdout, np.uint8).reshape(-1, 180, 320, 3)
ts = [i * 2 for i in range(len(fr))]
print(len(fr), 'tiles')

def sheet(idx, cols, tw, th, fs, outp, title):
    rows = (len(idx) + cols - 1) // cols; lh = fs + 6
    S = Image.new('RGB', (cols * tw, 34 + rows * (th + lh)), (14, 14, 14)); d = ImageDraw.Draw(S)
    d.text((8, 6), title, fill=(235, 225, 200), font=fnt(20))
    for k, i in enumerate(idx):
        x, y = (k % cols) * tw, 34 + (k // cols) * (th + lh)
        S.paste(Image.fromarray(fr[i]).resize((tw - 2, th), Image.LANCZOS), (x + 1, y))
        t = ts[i]; d.text((x + 4, y + th + 1), f'{t // 60}:{t % 60:02d}', fill=(240, 205, 110), font=fnt(fs))
    S.save(outp, quality=88); print(outp, S.size)

n = len(fr)
sheet(list(range(n)), 11, 145, 82, 13, ROOT + '/out/round6/FULL_r6_contact.jpg', f'《谁定正邪》MV r6 成片 · 每 2 秒一格 · 0:00–{ts[-1] // 60}:{ts[-1] % 60:02d}')
per = 35
for p in range(0, n, per):
    idx = list(range(p, min(n, p + per)))
    a, b = ts[idx[0]], ts[idx[-1]]
    sheet(idx, 5, 320, 180, 16, ROOT + f'/out/round6/FULL_r6_contact_p{p // per + 1}.jpg',
          f'r6 成片 第 {p // per + 1} 页 · {a // 60}:{a % 60:02d}–{b // 60}:{b % 60:02d} · 每 2 秒一格')
