"""[B组] 联系表 / 关键帧（按本组 SHOTS/CUT 表取帧，不用 tools/sec_contact.py）
  python3 tools/b_contact.py render <tag> i0 i1     渲第 i0..i1 帧条目到 $B_CACHE（默认 ../b_cache）/<tag>/（分块跑，>1 帧须 tools/cpu_slot.sh 包裹）
  python3 tools/b_contact.py sheet  <tag> out.jpg   拼图
tag: contact（每镜中点帧，预副歌一 14 + 主歌二 25） | keys（转场中间帧 + 歌词关键帧）"""
import sys, os, json
ROOT = '/workspace/work/mv'; sys.path[:0] = [ROOT, ROOT + '/units', ROOT + '/lib']; os.chdir(ROOT)
os.environ.setdefault('SPRITE_MODE', '1')
from PIL import Image, ImageDraw, ImageFont
import sec_b_pre1 as P1, sec_b_verse2 as V2
FPS = 30
CACHE = os.environ.get('B_CACHE', os.path.realpath(ROOT + '/../b_cache'))


def items(tag):
    out = []
    if tag == 'contact':
        for m, key in ((P1, 'pre1'), (V2, 'verse2')):
            for S, a, b in zip(m.SHOTS, m.CUT_F, m.CUT_F[1:]):
                out.append((key, (a + b) // 2, f'{S.__name__} {a / FPS:.2f}-{b / FPS:.2f}'))
    else:
        for m, key in ((P1, 'pre1'), (V2, 'verse2')):
            for S, a in zip(m.SHOTS[1:], m.CUT_F[1:]):
                name = m.CUTS.get(S.__name__, ('hard',))[0]
                if name not in ('hard', 'none'):
                    out.append((key, a + 2, f'切{S.__name__} {name}'))
        lyr = [('pre1', 45.75, '写生死簿'), ('pre1', 47.75, '善恶框'), ('pre1', 50.0, '血'), ('pre1', 52.45, '天劈开'), ('pre1', 52.95, '命'), ('pre1', 56.55, '刀弧'), ('pre1', 57.95, '滚烫'), ('pre1', 59.0, '横刀蓄势'),
               ('verse2', 90.6, '空间字'), ('verse2', 91.3, '笏板刻字'), ('verse2', 93.2, '屏风字'), ('verse2', 94.15, '权·窗棂光'), ('verse2', 95.5, '嚣张'), ('verse2', 97.3, '算盘刻梁'),
               ('verse2', 99.1, '量'), ('verse2', 102.7, '反抗'), ('verse2', 104.0, '天命'), ('verse2', 105.4, '上苍'), ('verse2', 105.75, '碑断'),
               ('verse2', 107.3, '命'), ('verse2', 110.3, '倒影'), ('verse2', 111.8, '颠倒'), ('verse2', 113.5, '刀'), ('verse2', 114.9, '锋重新划'), ('verse2', 117.0, '向')]
        out += [(k, int(round(t * FPS)), f'字 {s}') for k, t, s in lyr]
    return out


def render(tag, i0, i1):
    d = f'{CACHE}/{tag}'; os.makedirs(d, exist_ok=True)
    for i, (key, f, lab) in enumerate(items(tag)):
        if not (i0 <= i <= i1): continue
        m = P1 if key == 'pre1' else V2
        im = Image.fromarray(m.frame(f, {})).resize((640, 360), Image.LANCZOS)
        im.save(f'{d}/{i:03d}.jpg', quality=90); print(i, f, lab, flush=True)


def sheet(tag, out):
    font = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 20)
    its = items(tag); cols = 6; rows = (len(its) + cols - 1) // cols
    sh = Image.new('RGB', (cols * 640 // 2 * 2, rows * 360))
    for i, (key, f, lab) in enumerate(its):
        p = f'{CACHE}/{tag}/{i:03d}.jpg'
        if not os.path.exists(p): continue
        im = Image.open(p); ImageDraw.Draw(im).text((6, 4), f'{lab}  f{f}', fill=(240, 220, 120), font=font)
        sh.paste(im, ((i % cols) * 640, (i // cols) * 360))
    w = 2880; sh = sh.resize((w, int(sh.size[1] * w / sh.size[0])), Image.LANCZOS)
    sh.save(out, quality=82); print(out, len(its), os.path.getsize(out))


def pages(tag, out_prefix, cols=3, rows=3):
    """评审用分页：每页 cols×rows 张 640×360 原尺寸缩略（3×3 = 1920×1080 ≤ 1920×1400），out_prefix_p<N>.jpg"""
    font = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 22)
    its = items(tag); per = cols * rows; n = 0
    for k in range(0, len(its), per):
        chunk = its[k:k + per]; r = (len(chunk) + cols - 1) // cols
        sh = Image.new('RGB', (cols * 640, r * 360))
        for j, (key, f, lab) in enumerate(chunk):
            pth = f'{CACHE}/{tag}/{k + j:03d}.jpg'
            if not os.path.exists(pth): continue
            im = Image.open(pth); ImageDraw.Draw(im).text((6, 4), f'{lab}  f{f}', fill=(240, 220, 120), font=font)
            sh.paste(im, ((j % cols) * 640, (j // cols) * 360))
        sh.save(f'{out_prefix}_p{n}.jpg', quality=85); n += 1
    print(out_prefix, n)


def split(src, outdir, maxw=1920, maxh=1400):
    """把联系表切成 ≤maxw×maxh 的块（大图 read_file 读不出来）"""
    im = Image.open(src); os.makedirs(outdir, exist_ok=True)
    if im.size[0] > maxw: im = im.resize((maxw, int(im.size[1] * maxw / im.size[0])), Image.LANCZOS)
    n = 0
    for y in range(0, im.size[1], maxh):
        im.crop((0, y, im.size[0], min(im.size[1], y + maxh))).save(f'{outdir}/{os.path.basename(src)[:-4]}_{n}.jpg', quality=88); n += 1
    print(n)


if __name__ == '__main__':
    if sys.argv[1] == 'pages': pages(sys.argv[2], sys.argv[3]); sys.exit()
    if sys.argv[1] == 'split': split(sys.argv[2], sys.argv[3]); sys.exit()
    if sys.argv[1] == 'render': render(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    else: sheet(sys.argv[2], sys.argv[3])
