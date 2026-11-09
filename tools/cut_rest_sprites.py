"""抠图 + 联系表（副歌一以外段落）。
  python3 tools/cut_rest_sprites.py cut  [最多张数=2]   对 assets/gen/<镜号>/<姿势>_raw.png 中还没有 _cut 的跑 tools/cutout.py 灰底流程
  python3 tools/cut_rest_sprites.py zoom S010 walk      输出发丝/手指局部放大检查图 /tmp/zoom_<镜号>_<姿势>.jpg
  python3 tools/cut_rest_sprites.py sheet               每段一张联系表 assets/gen/_sheet_<段落>.jpg（灰白棋盘底）
"""
import sys, os, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
import sprite_plan_rest as plan, cutout
ROOT = plan.ROOT
GEN = os.path.join(ROOT, 'assets/gen')


def mine():
    return [(j['sid'], j['pose'], j['section']) for j in plan.jobs()]


def cut(maxn=2):
    n = 0
    for sid, pose, _ in mine():
        raw = os.path.join(GEN, sid, pose + '_raw.png'); out = os.path.join(GEN, sid, pose + '_cut.png')
        if os.path.exists(raw) and not os.path.exists(out):
            cutout.cutout(raw, out, 2560); print('cut', out); n += 1
            if n >= maxn: break


def checker(w, h, s=24):
    yy, xx = np.mgrid[0:h, 0:w]
    c = (((yy // s) + (xx // s)) % 2).astype(np.uint8)
    a = np.where(c[..., None] == 1, 205, 160).astype(np.uint8)
    return Image.fromarray(np.repeat(a, 3, -1), 'RGB')


def zoom(sid, pose):
    im = Image.open(os.path.join(GEN, sid, pose + '_cut.png'))
    a = np.asarray(im)[..., 3]
    ys, xs = np.nonzero(a > 10)
    W, H = im.size
    # 发区：前景最上方；其余：前景左右边缘中部
    boxes = [(xs[ys.argmin()], ys.min()), (xs.min(), int(np.median(ys))), (xs.max(), int(np.median(ys)))]
    tiles = []
    for cx, cy in boxes:
        x0 = int(np.clip(cx - 200, 0, W - 400)); y0 = int(np.clip(cy - 100, 0, H - 400))
        crop = im.crop((x0, y0, x0 + 400, y0 + 400))
        for bg in (checker(400, 400, 16), Image.new('RGB', (400, 400), (20, 24, 32))):
            b = bg.copy(); b.paste(crop, (0, 0), crop); tiles.append(b.resize((600, 600), Image.LANCZOS))
    sheet = Image.new('RGB', (600 * len(tiles) // 2, 1200))
    for i, t in enumerate(tiles): sheet.paste(t, ((i // 2) * 600, (i % 2) * 600))
    p = '/tmp/zoom_%s_%s.jpg' % (sid, pose); sheet.save(p, quality=88); print(p)


def font(sz):
    for f in glob.glob(os.path.join(ROOT, 'fonts/*')) + ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
        try: return ImageFont.truetype(f, sz)
        except Exception: pass
    return ImageFont.load_default()


def sheet():
    secs = {}
    for sid, pose, sec in mine():
        p = os.path.join(GEN, sid, pose + '_cut.png')
        if os.path.exists(p): secs.setdefault(sec, []).append((sid, pose, p))
    f = font(30)
    for sec, items in secs.items():
        cols = 4; tw, th = 640, 360; rows = (len(items) + cols - 1) // cols
        S = checker(cols * tw, rows * (th + 50), 20)
        d = ImageDraw.Draw(S)
        for i, (sid, pose, p) in enumerate(items):
            im = Image.open(p); im.thumbnail((tw - 10, th - 10), Image.LANCZOS)
            x = (i % cols) * tw; y = (i // cols) * (th + 50)
            S.paste(im, (x + (tw - im.size[0]) // 2, y + 5), im)
            d.rectangle((x, y + th, x + tw, y + th + 50), fill=(20, 20, 20))
            d.text((x + 12, y + th + 8), '%s  %s' % (sid, pose), fill=(240, 240, 240), font=f)
        out = os.path.join(GEN, '_sheet_%s.jpg' % sec); S.save(out, quality=88); print(out, len(items))


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'cut': cut(int(sys.argv[2]) if len(sys.argv) > 2 else 2)
    elif c == 'zoom': zoom(sys.argv[2], sys.argv[3])
    elif c == 'sheet': sheet()
