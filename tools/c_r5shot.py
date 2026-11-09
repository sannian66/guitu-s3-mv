"""tools/c_r5shot.py — C 组第五轮核帧：成片帧（含总导演统一字幕）按秒批渲。
用法：tools/cpu_slot.sh python3 tools/c_r5shot.py PREFIX t1 t2 ...  → PREFIX_<t>.png
      加 --grid OUT.jpg 再拼一张 2 列缩略联系图（每格 960 宽，左上角标秒数）。"""
import os, sys
ROOT = '/workspace/work/mv'
sys.path.insert(0, ROOT); os.chdir(ROOT)
from PIL import Image, ImageDraw
import render_sprite_full as R

args = sys.argv[1:]
grid = None
if '--grid' in args:
    i = args.index('--grid'); grid = args[i + 1]; del args[i:i + 2]
pre, ts = args[0], args[1:]
cache, outs = {}, []
for a in ts:
    t = float(a)
    p = f'{pre}_{t:.2f}.png'
    Image.fromarray(R.frame(int(round(t * R.FPS)), cache)).save(p)
    outs.append((t, p)); print(p, flush=True)
if grid:
    cols = 2; rows = (len(outs) + 1) // 2
    G = Image.new('RGB', (960 * cols, 540 * rows))
    for k, (t, p) in enumerate(outs):
        im = Image.open(p).resize((960, 540)); d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 120, 34), fill=(0, 0, 0)); d.text((8, 8), f'{t:.2f}s', fill=(255, 220, 0))
        G.paste(im, ((k % cols) * 960, (k // cols) * 540))
    G.save(grid, quality=88); print(grid)
