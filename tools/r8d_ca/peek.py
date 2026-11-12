"""CA 单元：一次进程渲多帧（全片管线 render_sprite_full.frame，含字幕 + STYLE_D 色板兜底）。
用法：MV_ROOT=.. MV_TMP=/tmp/mv_r8d_ca STYLE_D=1 python tools/r8d_ca/peek.py outdir f1 f2 ...   （帧号）
      SCALE=0.5 缩小保存；SHEET=out.jpg 拼联系表（每格标帧号）。"""
import os, sys
ROOT = os.environ['MV_ROOT']; sys.path[:0] = [ROOT, ROOT + '/units', ROOT + '/lib']
import render_sprite_full as R
from PIL import Image, ImageDraw, ImageFont
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
fs = [int(x) for x in sys.argv[2:]]
sc = float(os.environ.get('SCALE', '0.5'))
cache = {}; tiles = []
for f in fs:
    im = Image.fromarray(R.frame(f, cache))
    if sc != 1: im = im.resize((int(1920 * sc), int(1080 * sc)), Image.LANCZOS)
    p = f'{out}/{f}.png'; im.save(p); tiles.append((f, im)); print(f, flush=True)
sh = os.environ.get('SHEET')
if sh:
    cols = int(os.environ.get('COLS', '4')); tw, th = tiles[0][1].size; tw2 = min(tw, 1600 // cols); th2 = int(th * tw2 / tw)
    rows = (len(tiles) + cols - 1) // cols
    S = Image.new('RGB', (cols * tw2, rows * (th2 + 22)), (10, 10, 10)); d = ImageDraw.Draw(S)
    fnt = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 16)
    for k, (f, im) in enumerate(tiles):
        x, y = (k % cols) * tw2, (k // cols) * (th2 + 22)
        S.paste(im.resize((tw2, th2), Image.LANCZOS), (x, y)); d.text((x + 4, y + th2 + 2), f'{os.environ.get("LBL_" + str(f), "")} f{f}', fill=(240, 220, 120), font=fnt)
    S.save(sh, quality=88)
