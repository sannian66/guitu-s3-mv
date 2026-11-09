"""人物 v3（脸/发型按设定图）前后对比：python v3_face_cmp.py [front|profile|turn3q|full|all]
每组三联：v2（旧，rig_v2_baseline.py 冻结）| v3（新，lib/rig.py）| 设定图对应部位裁切（仅作对照，不进成片）。
输出 lib/rig_test/v3_face_cmp_<name>.jpg（1920 宽）。渲染速度打印在标签和 stdout。"""
import sys, os, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
import rig as RN, rig_v2_baseline as RO

PW, PH = 640, 720
FONT = ImageFont.truetype(os.path.join(ROOT, 'fonts', 'NotoSerifSC-SemiBold.otf'), 26)
REF = np.asarray(Image.open(os.path.join(ROOT, 'assets', 'characters', '男主_鬼屠.webp')).convert('RGB')).astype(np.float32) / 255.

def bg(h=1080, w=1920, a=0.20, b=0.07):
    return (np.linspace(a, b, h)[:, None, None] * np.ones((1, w, 3))).astype(np.float32)

def fit(img, w=PW, h=PH, fill=0.08):
    H, W = img.shape[:2]; s = min(w / W, h / H)
    r = cv2.resize(img, (max(1, int(W * s)), max(1, int(H * s))), interpolation=cv2.INTER_AREA)
    out = np.full((h, w, 3), fill, np.float32); y0 = (h - r.shape[0]) // 2; x0 = (w - r.shape[1]) // 2
    out[y0:y0 + r.shape[0], x0:x0 + r.shape[1]] = r; return out

def cu(R, view, action, phase, seed=43, head_px=400, cx=960, cy=470, glint=1.6, n=16):
    fr = bg(); sw = R.Swordsman(seed, view=view, hair=1.0)
    for k in range(n): R.profile_cu(np.zeros_like(fr), sw, k / 30, cx, cy, head_px, action=action, phase=phase * k / max(1, n - 1))
    t0 = time.time(); fr, _ = R.profile_cu(fr, sw, n / 30, cx, cy, head_px, light='moon', glint=glint, action=action, phase=phase)
    return fr, time.time() - t0

def full(R, view='side', wind=-200):
    fr = bg(a=0.30, b=0.10); sw = R.Swordsman(1, view=view)
    for k in range(40): sw.pose('stand_wind', 0.1, k / 30, wind=wind)
    t0 = time.time(); fr, _ = sw.draw(fr, 960, 1010, 820, rim_color=(0.9, 0.92, 1), rim_dir=(-0.8, -0.6))
    return fr, time.time() - t0

SC = {
    'front':   dict(fn=lambda R: cu(R, 'front', 'stand_wind', 0.0), crop=(160, 880, 640, 1280),
                    ref=(0, 900, 20, 820), refname='设定图 · 脸部特写', title='正面胸像特写'),
    'profile': dict(fn=lambda R: cu(R, 'side', 'turn_head', 0.0), crop=(110, 830, 600, 1240),
                    ref=(65, 330, 1300, 1530), refname='设定图 · 侧视头部', title='侧脸特写（S043 起势 / profile_cu）'),
    'turn3q':  dict(fn=lambda R: cu(R, 'side', 'turn_head', 0.48), crop=(110, 830, 560, 1200),
                    ref=(55, 300, 935, 1135), refname='设定图 · 正视头部', title='四分之三回头（turn_head 0.48）'),
    'full':    dict(fn=lambda R: full(R), crop=(60, 1080, 520, 1400),
                    ref=(55, 1065, 860, 1530), refname='设定图 · 正/侧视全身', title='全身站姿 · 风吹发（side, 逆风 wind -200）'),
}

def label(img, txt, sub=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 40], fill=(0, 0, 0)); d.text((12, 5), txt, font=FONT, fill=(235, 235, 235))
    if sub: d.text((12, im.height - 36), sub, font=FONT, fill=(200, 200, 200))
    return np.asarray(im).astype(np.float32) / 255.

def run(name):
    c = SC[name]; panels = []; times = {}
    for tag, R in (('v2 旧', RO), ('v3 新', RN)):
        c['fn'](R); fr, dt = c['fn'](R)       # 第二次计时（缓存热）
        times[tag] = dt
        y0, y1, x0, x1 = c['crop']
        panels.append(label(fit(fr[y0:y1, x0:x1]), '%s  %.2fs/帧' % (tag, dt)))
    y0, y1, x0, x1 = c['ref']
    panels.append(label(fit(REF[y0:y1, x0:x1], fill=1.0), c['refname'], '参考，仅对照'))
    img = np.hstack(panels)
    head = label(np.full((48, img.shape[1], 3), 0.0, np.float32), c['title'])[:48]
    img = np.vstack([head, img])
    out = os.path.join(HERE, 'v3_face_cmp_%s.jpg' % name)
    cv2.imwrite(out, (np.clip(img, 0, 1) * 255).astype(np.uint8)[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(name, {k: round(v, 3) for k, v in times.items()}, out, flush=True)

if __name__ == '__main__':
    names = sys.argv[1:] or ['all']
    for n in (list(SC) if names == ['all'] else names): run(n)
