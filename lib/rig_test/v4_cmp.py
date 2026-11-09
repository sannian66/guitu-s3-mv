"""人物 v4 前后对比：python v4_cmp.py [front|profile|turn3q|calm|wind|c1|all]  （环境变量 ONLY=v4 只渲新版到 /tmp 供迭代）
每组三联：v3（上一版，rig_v3_baseline.py 冻结 = commit a2ca0c9）| v4（新，lib/rig.py）| 设定图对应部位裁切（参考，仅对照，不进成片）。
副歌一组为两联：v3 规范下旧帧 | v4 新帧（同一 units/chorus1.py，切 rig.HAIR_V4）。
输出 lib/rig_test/v4_cmp_<name>.jpg（1920 宽）。每帧秒数打印在标签和 stdout，并写入 v4_speed.json。"""
import sys, os, time, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
import rig as RN, rig_v3_baseline as RO

PW, PH = 640, 760
FONT = ImageFont.truetype(os.path.join(ROOT, 'fonts', 'NotoSerifSC-SemiBold.otf'), 26)
REF = np.asarray(Image.open(os.path.join(ROOT, 'assets', 'characters', '男主_鬼屠.webp')).convert('RGB')).astype(np.float32) / 255.
ONLY = os.environ.get('ONLY')

def bg(h=1080, w=1920, a=0.20, b=0.07):
    return (np.linspace(a, b, h)[:, None, None] * np.ones((1, w, 3))).astype(np.float32)

def fit(img, w=PW, h=PH, fill=0.08):
    H, W = img.shape[:2]; s = min(w / W, h / H)
    r = cv2.resize(img, (max(1, int(W * s)), max(1, int(H * s))), interpolation=cv2.INTER_AREA)
    out = np.full((h, w, 3), fill, np.float32); y0 = (h - r.shape[0]) // 2; x0 = (w - r.shape[1]) // 2
    out[y0:y0 + r.shape[0], x0:x0 + r.shape[1]] = r; return out

def cu(R, view, action, phase, seed=43, head_px=400, cx=960, cy=470, glint=1.6, n=16):
    fr = bg(); sw = R.Swordsman(seed, view=view, hair=1.0)
    if ONLY: n = 4
    for k in range(n): R.profile_cu(np.zeros_like(fr), sw, k / 30, cx, cy, head_px, action=action, phase=phase * k / max(1, n - 1))
    t0 = time.time(); fr, _ = R.profile_cu(fr, sw, n / 30, cx, cy, head_px, light='moon', glint=glint, action=action, phase=phase)
    return fr, time.time() - t0

def full(R, view='side', wind=-200, n=60):
    fr = bg(a=0.30, b=0.10); sw = R.Swordsman(1, view=view)
    for k in range(n): sw.pose('stand_wind', 0.1, k / 30, wind=wind)
    t0 = time.time(); fr, _ = sw.draw(fr, 960, 1040, 860, rim_color=(0.9, 0.92, 1), rim_dir=(-0.8, -0.6))
    return fr, time.time() - t0

SC = {
    'front':   dict(fn=lambda R: cu(R, 'front', 'stand_wind', 0.0), crop=(150, 900, 620, 1300),
                    ref=(0, 900, 20, 820), refname='设定图 · 脸部特写', title='正面胸像特写'),
    'profile': dict(fn=lambda R: cu(R, 'side', 'turn_head', 0.0), crop=(110, 870, 560, 1260),
                    ref=(65, 330, 1300, 1530), refname='设定图 · 侧视头部', title='侧脸特写（profile_cu，S043 起势）'),
    'turn3q':  dict(fn=lambda R: cu(R, 'side', 'turn_head', 0.48), crop=(110, 870, 560, 1220),
                    ref=(55, 300, 935, 1135), refname='设定图 · 正视头部', title='四分之三回头（turn_head 0.48）'),
    'calm':    dict(fn=lambda R: full(R, 'side', 0), crop=(40, 1080, 500, 1420),
                    ref=(55, 1065, 1270, 1540), refname='设定图 · 侧视全身', title='全身静风站姿（side, wind 0：马尾在重力下垂过腰）'),
    'wind':    dict(fn=lambda R: full(R, 'side', -200), crop=(40, 1080, 460, 1420),
                    ref=(55, 1065, 1270, 1540), refname='设定图 · 侧视全身', title='全身风吹（side, 逆风 wind -200：马尾向后斜飘）'),
}

def label(img, txt, sub=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 40], fill=(0, 0, 0)); d.text((12, 5), txt, font=FONT, fill=(235, 235, 235))
    if sub:
        d.rectangle([0, im.height - 40, im.width, im.height], fill=(0, 0, 0)); d.text((12, im.height - 36), sub, font=FONT, fill=(220, 220, 220))
    return np.asarray(im).astype(np.float32) / 255.

def save(img, title, name):
    head = label(np.full((48, img.shape[1], 3), 0.0, np.float32), title)[:48]
    img = np.vstack([head, img])
    if img.shape[1] != 1920:
        img = cv2.resize(img, (1920, int(img.shape[0] * 1920 / img.shape[1])), interpolation=cv2.INTER_AREA)
    out = os.path.join(HERE, 'v4_cmp_%s.jpg' % name) if not ONLY else '/tmp/v4_%s.jpg' % name
    cv2.imwrite(out, (np.clip(img, 0, 1) * 255).astype(np.uint8)[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 90])
    return out

SPEED = os.path.join(HERE, 'v4_speed.json')
def log_speed(name, times):
    d = json.load(open(SPEED)) if os.path.exists(SPEED) else {}
    d[name] = times; json.dump(d, open(SPEED, 'w'), ensure_ascii=False, indent=1)

def run(name):
    if name == 'c1': return run_c1()
    c = SC[name]; panels = []; times = {}
    for tag, R in (('v3 上一版', RO), ('v4 新', RN)):
        if ONLY and R is RO: continue
        if not ONLY: c['fn'](R)
        fr, dt = c['fn'](R)                   # 第二次计时（缓存热）
        times[tag] = round(dt, 3)
        y0, y1, x0, x1 = c['crop']
        panels.append(label(fit(fr[y0:y1, x0:x1]), '%s  %.2fs/帧' % (tag, dt)))
    y0, y1, x0, x1 = c['ref']
    panels.append(label(fit(REF[y0:y1, x0:x1], fill=1.0), c['refname'], '参考，仅对照'))
    out = save(np.hstack(panels), c['title'], name)
    if not ONLY: log_speed(name, times)
    print(name, times, out, flush=True)

C1_T = [(82.70, 'S043 回头 MCU 82.70s'), (70.20, 'S035 全身 70.20s')]
def run_c1():
    sys.path[:0] = [os.path.join(ROOT, 'units'), ROOT]; os.chdir(ROOT)
    import chorus1
    panels = []; times = {}
    for t, nm in C1_T:
        row = []
        for tag, v4 in (('v3 规范 旧帧', False), ('v4 新帧', True)):
            if ONLY and not v4: continue
            RN.HAIR_V4 = v4
            X = chorus1.Chorus1()
            X.frame(t - 2 / 30); X.frame(t - 1 / 30)
            t0 = time.time(); fr, _ = X.frame(t); dt = time.time() - t0
            times['%s %s' % (nm, tag)] = round(dt, 3)
            row.append(label(cv2.resize(np.clip(fr, 0, 1).astype(np.float32), (960, 540), interpolation=cv2.INTER_AREA),
                             '%s · %s  %.2fs/帧(整帧)' % (nm, tag, dt)))
        panels.append(np.hstack(row) if len(row) > 1 else row[0])
    RN.HAIR_V4 = True
    out = save(np.vstack(panels), '副歌一重渲：左 v3 旧帧 | 右 v4 新帧（同帧同镜头）', 'c1')
    if not ONLY: log_speed('c1', times)
    print('c1', times, out, flush=True)

if __name__ == '__main__':
    names = sys.argv[1:] or ['all']
    for n in (list(SC) + ['c1'] if names == ['all'] else names): run(n)
