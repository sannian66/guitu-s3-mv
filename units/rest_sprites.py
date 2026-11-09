"""units/rest_sprites.py — 副歌一以外的人物精灵镜头（SPRITE_MODE=1；规则见 HANDOFF 第 0 节 05:25）。
全片 = scenes.py 的场景（背景/字幕/卡点/粒子纯代码）+ 本模块按 crew/shots.json 的镜头时间窗把生图精灵合进去：
  scenes.run_scene → 场景背景 → spr_hook(fr, t)（Intro/Scroll/Bridge/Outro 在自己的文字之前调用；其余场景在 frame 返回后）→ 字幕。
  镜头时长不改（shots.json t0/t1）；动作镜头按卡点硬切姿势 + 闪白 + 对齐刀尖的代码刀光，不做假连续动作。
  代码人物 put_hero：大号剪影场景在 SPRITE_MODE 下一律隐藏；远景小剪影（peak/throne）只在精灵镜头里隐藏。

SHOT 表字段：
  poses  [(切换时刻 or None, 素材键)]；素材键 = '镜号/姿势' + 修饰：'|flip' 水平翻转 '|raw' 整帧原图 '|crop=x0,y0,x1,y1'（相对抠图原图，羽化切边）
  at     屏幕像素：包围盒锚点 anc（默认脚底中点 (0.5,1.0)）放到这里；h / w 包围盒高 / 宽（像素）
  move   dict(dx,dy,z) 整镜线性缓动位移/缩放；bob 走路起伏（px）；look 'sil'/'ink'/'paper'/'neg'/'shadow'
  fx     'flash'（切换闪白） 'slash'（切换时刀光弧，过刀尖） 'rain' 'embers' 'bokeh' 'fog_feet' 'sparks_tip' 'halo' 'rays' 'sun' 'sheen' 'strings' 'dust' 'shake' 'ring'
"""
import math, os, json, hashlib
import numpy as np, cv2
from PIL import Image, ImageOps
import sprite as SP

ROOT = '/workspace/work/mv'
GEN = ROOT + '/assets/gen/'
CACHE = '/tmp/spr_cache'
W, H, BAR = 1920, 1080, 120
GOLD = (1.0, 0.80, 0.45); COLD = (0.62, 0.74, 1.0); REDR = (1.0, 0.35, 0.25); WARM = (1.0, 0.85, 0.6)
SH = {x['id']: x for x in json.load(open(ROOT + '/crew/shots.json'))}
AN = np.load(ROOT + '/analysis.npz'); BEATS = AN['beats']


def snap(t, tol=0.15):
    i = np.argmin(np.abs(BEATS - t)); return float(BEATS[i]) if abs(BEATS[i] - t) <= tol else t


def ease(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def eout(x): x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3


# ------------------------------------------------------------------ 素材：裁到包围盒、翻转、切边羽化 → 缓存 PNG → SpriteLayer（LRU）
def _prep(key):
    os.makedirs(CACHE, exist_ok=True)
    out = CACHE + '/' + hashlib.md5(key.encode()).hexdigest()[:12] + '.png'
    if os.path.exists(out): return out
    parts = key.split('|'); sp, mods = parts[0], parts[1:]
    if 'raw' in mods:
        im = Image.open(GEN + sp + '_raw.png').convert('RGB')
        im = im.resize((2560, round(2560 * im.size[1] / im.size[0])), Image.LANCZOS).convert('RGBA')
        a = np.asarray(im).copy()
    else:
        a = np.asarray(Image.open(GEN + sp + '_cut.png').convert('RGBA')).copy()
    h, w = a.shape[:2]
    al = a[..., 3].astype(np.float32) / 255
    for m in mods:
        if m.startswith('crop='):
            x0, y0, x1, y1 = [float(v) for v in m[5:].split(',')]
            X0, Y0, X1, Y1 = int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)
            mask = np.zeros((h, w), np.float32); mask[Y0:Y1, X0:X1] = 1
            f = int(0.035 * w)                                   # 切边羽化（贴图像边的不羽化）
            r = np.ones((h, w), np.float32)
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            if X0 > 0: r *= np.clip((xx - X0) / f, 0, 1)
            if X1 < w: r *= np.clip((X1 - xx) / f, 0, 1)
            if Y0 > 0: r *= np.clip((yy - Y0) / f, 0, 1)
            if Y1 < h: r *= np.clip((Y1 - yy) / f, 0, 1)
            al = al * mask * r
    if 'raw' not in mods:                                        # 抠图碰到原图上/左/右边：软化成渐隐，避免直线切口
        f = int(0.03 * h)
        top = (al[1, :] > 0.5).mean(); lef = (al[:, 1] > 0.5).mean(); rig = (al[:, -2] > 0.5).mean()
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        if top > 0.01: al *= np.clip(yy / f, 0, 1) ** 0.7
        if lef > 0.03: al *= np.clip(xx / f, 0, 1) ** 0.7
        if rig > 0.03: al *= np.clip((w - 1 - xx) / f, 0, 1) ** 0.7
    a[..., 3] = (al * 255).astype(np.uint8)
    ys, xs = np.nonzero(a[..., 3] > 12)
    if len(xs):
        mx, my = int(0.02 * w), int(0.02 * h)
        a = a[max(0, ys.min() - my):ys.max() + my, max(0, xs.min() - mx):xs.max() + mx]
    im = Image.fromarray(a, 'RGBA')
    if 'flip' in mods: im = ImageOps.mirror(im)
    im.save(out)
    return out


_LRU = {}
def layer(key, work_w):
    work_w = int(min(2048, max(320, round(work_w / 64) * 64)))
    k = (key, work_w)
    if k in _LRU:
        v = _LRU.pop(k); _LRU[k] = v; return v
    p = _prep(key)
    sp = SP.SpriteLayer(p, work_w=min(work_w, Image.open(p).size[0]))
    sp.tip = _tip(sp)
    _LRU[k] = sp
    while len(_LRU) > 5: _LRU.pop(next(iter(_LRU)))
    return sp


def _tip(sp):
    """刀尖：亮、低饱和（钢）且离人物重心最远的像素（归一化）；找不到返回 None。"""
    F, A = sp.F, sp.A
    mx, mn = F.max(-1), F.min(-1)
    steel = (A > 0.6) & (mx - mn < 0.10) & (mx > 0.42)
    ys, xs = np.nonzero(steel)
    if len(xs) < 50: return None
    cy, cx = np.nonzero(A > 0.5); c = np.array([cx.mean(), cy.mean()])
    d = (xs - c[0]) ** 2 + (ys - c[1]) ** 2
    i = np.argsort(d)[-max(5, len(d) // 400):]
    return (float(xs[i].mean() / sp.w), float(ys[i].mean() / sp.h))


# ------------------------------------------------------------------ 代码特效
def _rng(seed): return np.random.default_rng(seed)

def fx_rain(fr, t, seed, amt=0.35, n=260, ang=8, near=False):
    r = _rng(seed); L = np.zeros((H // 2, W // 2), np.float32)
    x0 = r.uniform(0, W, n); y0 = r.uniform(0, H, n); sp = r.uniform(1400, 2400, n); ln = r.uniform(30, 90, n) * (2.2 if near else 1)
    a = math.radians(ang)
    y = (y0 + sp * t) % (H + 200) - 100; x = (x0 + math.tan(a) * sp * t) % W
    for i in range(n):
        cv2.line(L, (int(x[i] / 2), int(y[i] / 2)), (int((x[i] - math.sin(a) * ln[i]) / 2), int((y[i] - math.cos(a) * ln[i]) / 2)),
                 float(r.uniform(0.3, 1)), 2 if near and i % 3 == 0 else 1, cv2.LINE_AA)
    L = cv2.resize(cv2.GaussianBlur(L, (0, 0), 1.6 if near else 0.6), (W, H))
    return fr + L[..., None] * amt * np.array([0.75, 0.82, 0.95], np.float32)

def fx_embers(fr, t, seed, amt=1.0, n=70, col=(1.0, 0.55, 0.22), big=False, rise=90):
    r = _rng(seed); L = np.zeros((H // 2, W // 2), np.float32)
    x0 = r.uniform(0, W, n); y0 = r.uniform(0, H, n); v = r.uniform(0.5, 1.5, n); ph = r.uniform(0, 6.28, n)
    s = r.uniform(1, 3, n) * (3 if big else 1)
    for i in range(n):
        x = (x0[i] + 40 * math.sin(t * 1.3 + ph[i]) + 60 * t * v[i]) % W
        y = (y0[i] - rise * t * v[i]) % H
        fl = 0.6 + 0.4 * math.sin(t * 9 + ph[i])
        cv2.circle(L, (int(x / 2), int(y / 2)), max(1, int(s[i] / 2)), fl, -1, cv2.LINE_AA)
    L = cv2.resize(cv2.GaussianBlur(L, (0, 0), 2.5 if big else 0.8), (W, H))
    g = cv2.GaussianBlur(L, (0, 0), 6)
    return fr + (L * 1.2 + g * 1.5)[..., None] * amt * np.array(col, np.float32)

def fx_bokeh(fr, t, seed, amt=0.35, n=14, col=(0.7, 0.8, 1.0)):
    """前景虚焦光斑（特写纵深）"""
    r = _rng(seed); L = np.zeros((H // 4, W // 4), np.float32)
    for i in range(n):
        x = (r.uniform(0, W) + 25 * t * r.uniform(-1, 1)) / 4; y = (r.uniform(BAR, H - BAR) - 15 * t) / 4
        cv2.circle(L, (int(x), int(y)), int(r.uniform(8, 26)), float(r.uniform(0.3, 1)), -1, cv2.LINE_AA)
    L = cv2.resize(cv2.GaussianBlur(L, (0, 0), 3), (W, H))
    return fr + L[..., None] * amt * np.array(col, np.float32)

def fx_fog_feet(fr, t, y, amt=0.8, col=(0.10, 0.11, 0.13)):
    """脚部遮挡：地面雾带（避免平移时「滑行」）"""
    yy = np.arange(H, dtype=np.float32)[:, None]
    xx = np.arange(W, dtype=np.float32)[None, :]
    n = 0.5 + 0.25 * np.sin(xx / 140 + t * 0.7) + 0.25 * np.sin(xx / 57 - t * 1.3)
    m = np.clip((yy - (y - 70 - 25 * n)) / 90, 0, 1) * amt
    return fr * (1 - m[..., None]) + np.array(col, np.float32) * m[..., None]

def fx_arc(fr, c, r, a_tip, sweep, prog, fade, w=12, col=(1.0, 0.97, 0.94), edge=(0.75, 0.08, 0.06), squash=1.0):
    """刀光：以 c 为圆心、过刀尖的圆弧（终点 = 刀尖角度 a_tip，向后扫 sweep 度），白刃 + 朱红外缘 + 辉光"""
    if fade <= 0.01 or r < 20: return fr
    Lb = np.zeros((H // 2, W // 2), np.float32); Le = np.zeros_like(Lb)
    a0 = a_tip - sweep; a1 = a0 + sweep * prog
    n = 36
    for i in range(n):
        u0, u1 = i / n, (i + 1) / n
        t0 = a0 + (a1 - a0) * u0; t1 = a0 + (a1 - a0) * u1
        ww = max(1, int(w * (0.15 + 0.85 * u1) / 2))
        cv2.ellipse(Lb, (int(c[0] / 2), int(c[1] / 2)), (int(r / 2), int(r * squash / 2)), 0, t0, t1, 1.0, ww, cv2.LINE_AA)
        cv2.ellipse(Le, (int(c[0] / 2), int(c[1] / 2)), (int(r / 2) + ww, int(r * squash / 2) + ww), 0, t0, t1, 1.0, max(1, ww // 2), cv2.LINE_AA)
    Lb = cv2.resize(Lb, (W, H)); Le = cv2.resize(Le, (W, H))
    fr = fr + (Lb * 1.3 + cv2.GaussianBlur(Lb, (0, 0), 10) * 1.1)[..., None] * fade * np.array(col, np.float32)
    return fr + cv2.GaussianBlur(Le, (0, 0), 3)[..., None] * fade * np.array(edge, np.float32) * 1.4

def fx_sparks(fr, t, t0, p, seed, n=60, col=(1.0, 0.7, 0.35), spd=900, dirv=(0, -1), spread=1.2, grav=900, amt=1.0):
    a = t - t0
    if a < 0 or a > 0.9: return fr
    r = _rng(seed); L = np.zeros((H // 2, W // 2), np.float32)
    base = math.atan2(dirv[1], dirv[0])
    for i in range(n):
        ang = base + r.uniform(-spread, spread); v = spd * r.uniform(0.3, 1.0)
        x = p[0] + math.cos(ang) * v * a; y = p[1] + math.sin(ang) * v * a + grav * a * a
        x2 = x - math.cos(ang) * v * 0.02; y2 = y - (math.sin(ang) * v + 2 * grav * a) * 0.02
        cv2.line(L, (int(x / 2), int(y / 2)), (int(x2 / 2), int(y2 / 2)), 1.0, 1, cv2.LINE_AA)
    L = cv2.resize(L, (W, H)) * (1 - a / 0.9)
    return fr + (L * 1.4 + cv2.GaussianBlur(L, (0, 0), 4) * 1.5)[..., None] * amt * np.array(col, np.float32)

def fx_glow(fr, p, rad, amt, col):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    g = np.exp(-((xx - p[0]) ** 2 + (yy - p[1]) ** 2) / (2 * rad * rad))
    return fr + g[..., None] * amt * np.array(col, np.float32)

def fx_rays(fr, p, t, amt=0.5, col=GOLD, n=18):
    yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
    ang = np.arctan2(yy - p[1] / 2, xx - p[0] / 2); d = np.sqrt((xx - p[0] / 2) ** 2 + (yy - p[1] / 2) ** 2)
    rays = np.clip(np.sin(ang * n + t * 0.3) * 0.5 + 0.5, 0, 1) ** 6 * np.exp(-d / 500)
    rays = cv2.resize(cv2.GaussianBlur(rays.astype(np.float32), (0, 0), 3), (W, H))
    return fr + rays[..., None] * amt * np.array(col, np.float32)

def fx_star(fr, p, g, col=(1.0, 0.95, 0.85)):
    if g <= 0.01: return fr
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    st = np.exp(-(np.abs(xx - p[0]) / 3 + np.abs(yy - p[1]) / 50)) + np.exp(-(np.abs(yy - p[1]) / 3 + np.abs(xx - p[0]) / 110))
    st += np.exp(-((xx - p[0]) ** 2 + (yy - p[1]) ** 2) / 300)
    return fr + st[..., None] * g * np.array(col, np.float32)

def shake(t, amp, seed=0):
    return amp * math.sin(t * 53 + seed) * math.cos(t * 31 + 2 * seed), amp * math.sin(t * 47 + 3 * seed)


# ------------------------------------------------------------------ 镜头表
def B(t0, k): return snap(t0 + k)
G_COLD = dict(expo=0.70, sat=0.55, tint=(0.90, 0.96, 1.06), lift=0.0, gamma=1.2)
G_WARM = dict(expo=0.78, sat=0.75, tint=(1.06, 0.98, 0.88), lift=0.0, gamma=1.15)
G_GOLD = dict(expo=0.74, sat=0.6, tint=(1.04, 0.98, 0.9), lift=0.0, gamma=1.18)

S = {
 # ---------------- intro（署名在左 x≈0.30，人物放右侧；片名/署名在精灵之上）
 'S002': dict(poses=[(None, 'S002/back_wind')], at=(1360, 975), h=560, move=dict(dx=-30, z=0.05), rim=COLD, fx=['fog_feet', 'embers'], wind=9),
 'S003': dict(poses=[(None, 'S003/thumb_push|raw')], full=True, move=dict(z=0.06, dx=-20), fx=['sheen', 'bokeh', 'credit_shade'], grade=dict(expo=0.82, sat=0.6, tint=(0.92, 0.96, 1.04), lift=0.0, gamma=1.1)),
 'S004': dict(poses=[(None, 'S004/profile'), (7.60, 'S004/profile_open')], at=(1380, 1010), h=900, anc=(0.5, 1.0), move=dict(z=0.04), rim=COLD,
              fx=['flash', 'eye', 'bokeh'], eye=(0.80, 0.28)),
 'S007': dict(poses=[(None, 'S011/backlit')], at=(1500, 1060), h=860, look='sil', rim=GOLD, rim_amt=5.5, alpha=0.86, defocus=1, move=dict(z=0.03), fx=['halo']),   # 11-09 第四任：缩小露出头顶、背靠血月、提高不透明度（原 h=980 alpha=0.62 糊成一团）
 # ---------------- verse1
 'S010': dict(poses=[(None, 'S010/walk'), (20.80, 'S010/draw'), (21.20, 'S010/slash_h')], at=(760, 1015), h=700, move=dict(dx=120), bob=7,
              rim=COLD, fx=['flash', 'slash', 'fog_feet', 'sparks_tip'], slash=dict(sweep=170, dir=-1, squash=0.28)),
 'S011': dict(poses=[(None, 'S011/backlit')], at=(960, 1075), h=900, look='sil', rim=GOLD, rim_amt=3.2, fx=['halo'], move=dict(z=0.05, dy=10)),
 'S014': dict(poses=[(None, 'S014/slash_diag'), (31.25, 'S014/sheath')], at=(900, 1010), h=680, rim=COLD, rim_amt=2.4, grade=dict(expo=0.92, sat=0.55, tint=(0.9, 0.96, 1.06), lift=0.0, gamma=1.15), fx=['flash', 'slash', 'rain', 'fog_feet'],
              slash=dict(sweep=110, dir=1), slash_t=29.95, move=dict(dx=-30)),
 'S015': dict(poses=[(None, 'S015/hand_draw|crop=0,0.47,1,1')], at=(960, 120), anc=(0.5, 0.0), w=2300, move=dict(z=0.07, dx=-40), rim=COLD,
              fx=['embers_fg', 'sheen', 'bokeh'], grade=dict(expo=0.78, sat=0.55, tint=(0.92, 0.96, 1.04), lift=0.0, gamma=1.15)),
 'S016': dict(poses=[(None, 'S120/plant|flip')], at=(1240, 790), h=190, look='sil', rim=COLD, rim_amt=3.0, fx=['halo_s']),
 'S017': dict(poses=[(None, 'S011/backlit|flip')], at=(1380, 920), h=560, look='sil', rim=GOLD, rim_amt=3.0, alpha=0.85),
 'S018': dict(poses=[(None, 'S018/turn'), (40.55, 'S018/look_up')], at=(1060, 1100), anc=(0.5, 1.0), h=900, rim=COLD,
              fx=['flash', 'eye', 'dust_fg'], eye=(0.52, 0.32), eye_t=40.9, move=dict(z=0.05)),
 # ---------------- pre1（宣纸：水墨化，避开右侧竖排字）
 'S021': dict(poses=[(None, 'S021/finger')], at=(430, 70), anc=(0.5, 0.0), h=560, look='ink', move=dict(dy=70), wind=2),
 'S023': dict(poses=[(None, 'S023/look_up_low')], at=(520, 990), h=760, look='ink', move=dict(z=0.05), wind=5),
 'S024': dict(poses=[(None, 'S024/fist'), (52.84, 'S024/pommel_thrust')], at=(600, 1060), h=900, look='ink', fx=['flash_ink'], move=dict(z=0.05)),
 # ---------------- verse2
 'S050': dict(poses=[(None, 'S050/scepter')], at=(1000, 1110), h=1050, look='shadow', defocus=6, move=dict(z=0.06, dx=-20)),
 'S051': dict(poses=[(None, 'S051/grip_scepter|crop=0,0,0.36,1')], at=(820, 1080), h=1000, look='ink', move=dict(z=0.06)),
 'S054': dict(poses=[(None, 'S054/rise')], at=(960, 960), h=420, look='ink', move=dict(z=0.55), wind=3),
 'S055': dict(poses=[(None, 'S055/walk_look_up')], at=(1150, 1020), h=680, move=dict(dx=-160), bob=8, rim=COLD, fx=['rain', 'fog_feet', 'rain_near']),
 'S056': dict(poses=[(None, 'S056/palm_open|crop=0,0.32,0.40,1'), (107.6, 'S056/palm_fist')], at=(1000, 560), anc=(0.5, 0.5), h=820,
              rim=COLD, rim_amt=3.2, grade=dict(expo=0.84, sat=0.6, tint=(0.92, 0.97, 1.05), lift=0.0, gamma=1.1),
              fx=['backglow', 'flash', 'rain_near', 'splash', 'bokeh'], move=dict(z=0.05)),   # 11-09 第四任：palm_fist 重抽（湿拳特写，无脸）+ recut_flat 抠图 + 背后冷光
 'S057': dict(poses=[(None, 'S057/grab_turn')], at=(980, 1090), h=880, rim=COLD, fx=['rain_near', 'whip'], move=dict(z=0.05)),
 'S058': dict(poses=[(None, 'S010/slash_h|flip')], at=(960, 980), h=560, look='neg', fx=['reflect'], move=dict(dx=40)),
 'S059': dict(poses=[(None, 'S010/slash_h')], at=(900, 1010), h=700, rim=COLD, fx=['slash', 'flash'], slash_t=113.2, slash=dict(sweep=170, dir=-1, squash=0.28)),
 # ---------------- pre2（宣纸）
 'S062': dict(poses=[(None, 'S062/puppeteer|crop=0,0,1,0.86')], at=(760, 30), anc=(0.5, 0.0), h=760, look='ink', fx=['strings'], move=dict(dy=40), wind=1),   # 11-09 第四任：tools/recut_flat.py 重抠（旧抠图把手背抠穿、袖口成马赛克）
 'S065': dict(poses=[(None, 'S065/chin_up')], at=(620, 1080), h=920, look='ink', move=dict(z=0.05, dy=-15), wind=4),
 'S066': dict(poses=[(None, 'S079/leap_slash_up|flip')], at=(600, 900), h=660, look='ink', move=dict(dy=-60), fx=['slash_red'], slash=dict(sweep=130, dir=-1)),
 'S069': dict(poses=[(None, 'S079/leap_slash_up')], at=(960, 560), h=280, look='sil', rim=COLD, rim_amt=3.5, fx=['bolt'], move=dict(dy=-30)),
 # ---------------- chorus2
 'S071': dict(poses=[(None, 'S071/land_kneel')], at=(960, 980), h=560, rim=COLD, fx=['ring', 'flash0', 'rain'], move=dict(dy=8)),
 'S072': dict(poses=[(None, 'S072/rise_draw')], at=(960, 1010), h=640, rim=COLD, fx=['rain', 'fog_feet', 'sparks_tip'], move=dict(dy=-20, z=0.04)),
 'S073': dict(poses=[(None, 'S073/spin1'), (137.92, 'S073/spin2')], at=(960, 1010), h=680, rim=COLD, fx=['flash', 'slash', 'rain'], slash=dict(sweep=260, dir=1, squash=0.25)),
 'S074': dict(poses=[(None, 'S074/head_turn')], at=(820, 1080), h=1000, look='sil', rim=(0.85, 0.9, 1.0), rim_amt=3.4, fx=['lightning'], move=dict(z=0.04)),
 'S075': dict(split=True, poses=[(None, 'S010/draw')], at=(560, 1020), h=640, rim=REDR, rim_amt=2.6,
              second=dict(key='S011/backlit', at=(1400, 1060), h=820, look='sil', rim=GOLD)),
 'S078': dict(poses=[(None, 'S078/run')], at=(1350, 1010), h=640, move=dict(dx=-520), bob=10, rim=GOLD, rim_amt=2.0, fx=['sparks_trail', 'speed', 'fog_feet'],
              mblur=(30, 0)),
 'S079': dict(poses=[(None, 'S079/leap_slash_up')], at=(960, 980), h=660, move=dict(dy=-90), rim=GOLD, fx=['slash', 'flash'], slash_t=145.14, slash=dict(sweep=140, dir=-1)),
 'S082': dict(poses=[(None, 'S082/walk_front')], at=(960, 1020), h=700, move=dict(z=0.12), bob=6, rim=GOLD, fx=['debris', 'fog_feet']),
 'S083': dict(poses=[(None, 'S083/sash|crop=0,0.50,1,1')], at=(960, 560), anc=(0.5, 0.5), w=2100, rim=GOLD, fx=['embers_fg', 'bokeh'], wind=14, move=dict(dx=-50)),
 'S084': dict(poses=[(None, 'S084/knock_back')], at=(1020, 1010), h=640, move=dict(dx=-120, ease='out'), rim=GOLD, fx=['handshadow', 'shake', 'dust'], mblur=(-20, 0)),
 'S085': dict(poses=[(None, 'S078/run|flip')], at=(520, 1010), h=500, move=dict(dx=700), bob=9, rim=COLD, fx=['speed', 'fog_feet', 'slam']),
 'S086': dict(poses=[(None, 'S014/slash_diag|flip')], at=(1000, 1010), h=660, rim=REDR, fx=['slash', 'flash'], slash_t=153.12, slash=dict(sweep=120, dir=-1),
              slash2=153.55),
 'S087': dict(poses=[(None, 'S087/brace_overhead')], at=(960, 1010), h=720, move=dict(dy=25), rim=GOLD, fx=['shake', 'dust', 'press']),
 'S090': dict(poses=[(None, 'S090/wind_up')], at=(1080, 1090), h=870, rim=GOLD, fx=['embers_fg'], move=dict(z=0.06, dx=30)),
 # ---------------- bridge（雨夜排比叠字之前；文字在精灵之上）
 'S095': dict(poses=[(None, 'S082/walk_front|flip')], at=(960, 1000), h=560, move=dict(z=0.10), bob=5, rim=COLD, grade=dict(expo=0.55, sat=0.4, tint=(0.9, 0.95, 1.05), lift=0.0, gamma=1.2), fx=['fog_feet']),
 'S098': dict(poses=[(None, 'S098/point_down')], at=(1560, 1075), h=820, look='sil', rim=(0.9, 0.9, 0.95), rim_amt=4.0, move=dict(z=0.06), fx=['whitesky']),   # 11-09 第四任：整身入画、右移让开歌词（原 h=1000 顶出画框挡字）
 'S099': dict(poses=[(None, 'S099/point_up')], at=(1060, 1100), h=1010, rim=COLD, fx=['tipstar'], move=dict(z=0.05)),
 'S102': dict(poses=[(None, 'S102/eye_open|raw')], full=True, move=dict(z=0.08), fx=['embers_fg', 'eyefire'], grade=dict(expo=1.0, sat=0.7, tint=(1.0, 0.96, 0.92), lift=0.0, gamma=1.15)),
 'S103': dict(poses=[(None, 'S103/slow_draw')], at=(960, 1010), h=720, rim=COLD, fx=['sheen_blade', 'fog_feet'], move=dict(z=0.05)),
 'S105': dict(poses=[(None, 'S105/charge_front')], at=(960, 1010), h=560, move=dict(z=0.75, ease='in'), bob=8, rim=COLD, fx=['speed_radial', 'flash_end']),
 'S107': dict(poses=[(None, 'S010/slash_h|flip')], at=(1000, 1000), h=600, rim=REDR, fx=['slash_red', 'flash'], slash_t=186.62, slash=dict(sweep=170, dir=1, squash=0.28)),
 'S109': dict(poses=[(None, 'S073/spin1|flip'), (190.40, 'S073/spin2|flip')], at=(960, 1000), h=640, rim=GOLD, fx=['flash', 'slash_gold', 'gold_burst'], slash=dict(sweep=260, dir=-1, squash=0.25)),
 'S110': dict(poses=[(None, 'S112/sword_sky')], at=(960, 1080), h=880, rim=GOLD, rim_amt=3.0, grade=dict(expo=0.9, sat=0.6, tint=(1.02, 0.98, 0.92), lift=0.0, gamma=1.12), fx=['backglow', 'beam'], move=dict(z=0.05)),   # 11-09 第四任：放大提亮（原 h=660 又小又暗）
 # ---------------- chorus3
 'S112': dict(poses=[(None, 'S112/sword_sky|flip')], at=(960, 1010), h=640, rim=GOLD, rim_amt=2.4, fx=['rays', 'tipstar'], move=dict(z=0.05), grade=G_GOLD),
 'S116': dict(poses=[(None, 'S011/backlit')], at=(960, 1080), h=930, look='paper', rim=GOLD, move=dict(z=0.04)),
 'S118': dict(poses=[(None, 'S014/slash_diag')], at=(940, 1010), h=660, rim=GOLD, fx=['slash', 'flash'], slash_t=203.5, slash=dict(sweep=120, dir=1), slash2=204.1, grade=G_GOLD),
 'S120': dict(poses=[(None, 'S120/plant')], at=(960, 1000), h=680, rim=GOLD, fx=['seal_ring', 'dust'], move=dict(z=0.05), grade=G_GOLD),
 'S121': dict(poses=[(None, 'S121/wind_sash')], at=(1000, 1120), h=880, rim=GOLD, rim_amt=2.4, wind=12, fx=['embers_fg'], grade=G_GOLD, move=dict(z=0.04)),
 'S122': dict(poses=[(None, 'S082/walk_front')], at=(960, 1010), h=620, move=dict(z=0.08), bob=6, rim=GOLD, fx=['fog_feet'], grade=G_GOLD),
 'S123': dict(poses=[(None, 'S123/front')], at=(660, 1110), h=890, rim=GOLD, grade=G_GOLD, move=dict(z=0.04)),
 'S124': dict(poses=[(None, 'S123/front|flip')], at=(1260, 1110), h=890, rim=REDR, grade=dict(expo=0.7, sat=0.6, tint=(1.06, 0.94, 0.92), lift=0.0, gamma=1.2), move=dict(z=0.04)),
 'S125': dict(poses=[(None, 'S125/stare')], at=(960, 1110), h=900, rim=GOLD, fx=['bokeh_gold', 'eye'], eye=(0.36, 0.36), eye_t=213.0, grade=G_GOLD, move=dict(z=0.06)),
 'S127': dict(poses=[(None, 'S004/profile|flip')], at=(560, 1010), h=900, rim=GOLD, rim_amt=2.6, grade=G_GOLD, fx=['bokeh_gold'], move=dict(z=0.04)),
 'S128': dict(poses=[(None, 'S128/blade_level')], at=(960, 1010), h=640, rim=GOLD, fx=['sun'], grade=G_GOLD, move=dict(z=0.03)),
 'S129': dict(poses=[(None, 'S090/wind_up|flip')], at=(860, 1090), h=870, rim=GOLD, grade=G_GOLD, move=dict(z=0.10, ease='in')),
 'S130': dict(poses=[(None, 'S073/spin2|flip')], at=(960, 1010), h=660, rim=GOLD, fx=['slash_gold', 'flash', 'gold_burst'], slash_t=219.15, slash=dict(sweep=260, dir=-1, squash=0.25), grade=G_GOLD),
 # ---------------- outro（片名/署名在精灵之上）
 'S132': dict(poses=[(None, 'S132/back_walk')], at=(1500, 900), h=380, move=dict(z=-0.18, dy=-25), bob=4, rim=WARM, fx=['fog_feet'], grade=G_GOLD),
 'S135': dict(poses=[(None, 'S135/sheath_hand|crop=0,0.45,0.62,1')], at=(600, 560), anc=(0.5, 0.5), h=820, rim=WARM, fx=['sheen_gold', 'bokeh_gold'], grade=G_GOLD, move=dict(z=0.05)),
 'S137': dict(poses=[(None, 'S135/sheath_hand|crop=0.15,0.55,0.62,1')], at=(620, 560), anc=(0.5, 0.5), h=760, rim=WARM, grade=dict(expo=0.6, sat=0.45, tint=(1.0, 0.95, 0.9), lift=0.0, gamma=1.25), move=dict(z=0.04), fx=['click']),
}
for k, v in S.items(): v['t0'], v['t1'] = SH[k]['t0'], SH[k]['t1']
ORDER = sorted(S, key=lambda k: S[k]['t0'])
_T0 = np.array([S[k]['t0'] for k in ORDER]); _T1 = np.array([S[k]['t1'] for k in ORDER])


def active(t):
    i = np.nonzero((_T0 <= t) & (t < _T1))[0]
    return ORDER[i[0]] if len(i) else None


BIG_HERO = {'army', 'duel', 'wall', 'storm', 'invert', 'bridge', 'blade', 'dscales'}
def hide_hero(t, key):
    """代码人物：大号剪影一律隐藏；远景小剪影（peak/throne）只在精灵镜头里隐藏。"""
    return key in BIG_HERO or active(t) is not None


# ------------------------------------------------------------------ 合成
def _place(fr, t, sid, key, c, at, h=None, w=None, anc=(0.5, 1.0), look=None, rim=COLD, rim_amt=1.8, alpha=1.0, defocus=0.0,
           grade=None, wind=6.0, mblur=(0, 0), k_move=0.0, extra=None):
    mv = c.get('move', {}); z = 1 + mv.get('z', 0) * k_move
    tgt = (h or 600) * z if h else (w or 1920) * z
    # 先按包围盒宽高比估工作分辨率
    if key not in _ASPECT:
        _w, _h = Image.open(_prep(key)).size; _ASPECT[key] = _w / _h
    asp = _ASPECT[key]
    scr_w = tgt * asp if h else tgt
    sp = layer(key, scr_w * 1.15)
    x0, y0, x1, y1 = sp.bbox
    if h: s = tgt / ((y1 - y0) * sp.h)
    else: s = tgt / ((x1 - x0) * sp.w)
    a_src = (x0 + anc[0] * (x1 - x0), y0 + anc[1] * (y1 - y0))
    dst = (at[0] + mv.get('dx', 0) * k_move, at[1] + mv.get('dy', 0) * k_move)
    if extra: dst = (dst[0] + extra[0], dst[1] + extra[1])
    g = dict(grade or c.get('grade') or G_COLD)
    if c.get('_scene') == 'bridge' and look is None:            # 桥段雨夜场景极暗：人物提亮、轮廓光加强
        g['expo'] *= 1.45; rim_amt *= 1.6
    rimd = dict(col=rim, amt=rim_amt, dir=c.get('rim_dir', (0.0, -1.0)))
    fr, Aw = sp.draw(fr, t, a_src, dst, s, rim=rimd, grade=g, wind_amp=wind, shade=None, wrap=0.4, mblur=mblur,
                     alpha=alpha, defocus=defocus, look=look)
    # 精灵坐标 → 屏幕
    def to_scr(p):
        return (dst[0] + (p[0] - a_src[0]) * sp.w * s, dst[1] + (p[1] - a_src[1]) * sp.h * s)
    info = dict(tip=to_scr(sp.tip) if sp.tip else None, top=to_scr(sp.top), box=(to_scr((x0, y0)), to_scr((x1, y1))), to_scr=to_scr, A=Aw)
    return fr, info
_ASPECT = {}


def apply(fr, t, scene_key=None):
    sid = active(t)
    if sid is None: return fr
    c = S[sid]; t0, t1 = c['t0'], c['t1']
    u = (t - t0) / (t1 - t0)
    em = c.get('move', {}).get('ease', 'io')
    k_move = eout(u) if em == 'out' else (u * u if em == 'in' else ease(u) * 0.35 + u * 0.65)
    # 当前姿势（卡点硬切）
    sw = [(t0 if s is None else snap(s, 0.08)) for s, _ in c['poses']]
    pi = max(i for i, s in enumerate(sw) if t >= s - 1e-6)
    key = c['poses'][pi][1]; ts = sw[pi]
    seed = int(sid[1:]) * 7
    fxs = c.get('fx', [])

    c['_scene'] = scene_key
    # ---- 背景层特效
    if scene_key == 'bridge' and not c.get('full'):            # 背光：人物后方一团冷白天光，剪影可读
        fr = fx_glow(fr, (c['at'][0], c['at'][1] - (c.get('h') or 600) * 0.6), (c.get('h') or 600) * 0.55, 0.30, (0.75, 0.8, 0.9))
    if 'whitesky' in fxs:                                        # S098 白空间：上半画面提成灰白天幕，黑巨影压上
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        fr = fr * 0.4 + np.clip(1 - (yy - 150) / 900, 0, 1) * np.array([0.78, 0.78, 0.76], np.float32) * 0.85
    if 'credit_shade' in fxs:                                    # 署名区压暗，保证片头字可读
        xx = np.arange(W, dtype=np.float32)[None, :, None]
        shade_m = np.clip(1 - (xx - 380) / 700, 0, 1) * 0.6
    if 'backglow' in fxs: fr = fx_glow(fr, (c['at'][0], c['at'][1] - (c['h'] * 0.55 if c.get('anc', (0.5, 1.0))[1] > 0.9 else 0)), c['h'] * 0.5, 0.32, (0.7, 0.78, 0.92))   # 人物背后柔光，暗底上分离轮廓
    if 'halo' in fxs: fr = fx_glow(fr, (c['at'][0], c['at'][1] - c['h'] * 0.85), 260, 0.55, GOLD)
    if 'halo_s' in fxs: fr = fx_glow(fr, (c['at'][0], c['at'][1] - 120), 120, 0.35, (0.8, 0.85, 1.0))
    if 'rays' in fxs: fr = fx_rays(fr, (c['at'][0], c['at'][1] - c['h'] * 1.05), t, 0.55)
    if 'bolt' in fxs:
        f = math.exp(-((t - t0 - 0.25) % 0.9) / 0.08)
        fr = fr + f * 0.35 * np.array([0.8, 0.85, 1.0], np.float32)
    if 'lightning' in fxs:
        f = max(math.exp(-max(0, t - t0 - 0.12) / 0.07) * (t > t0 + 0.12), math.exp(-max(0, t - t0 - 0.55) / 0.1) * (t > t0 + 0.55))
        fr = fr * (1 + 0.6 * f) + f * 0.25
    if 'sun' in fxs:
        pass   # 太阳在人物刀身中点，人物画完后加（需刀身位置）
    if 'handshadow' in fxs:
        k = ease((t - t0) / 0.5)
        yy = np.arange(H, dtype=np.float32)[:, None]
        m = np.clip(1 - (yy - (-200 + 700 * k)) / 500, 0, 1) * 0.75 * k
        fr = fr * (1 - m[..., None])

    # ---- 人物
    if c.get('full'):                                   # 整帧原图（S003/S102）
        mv = c['move']; z = 1 + mv.get('z', 0) * k_move
        sp = layer(key, 1920)
        s = W / sp.w * 1.02 * z
        fr, Aw = sp.draw(fr, t, (0.5, 0.5), (960 + mv.get('dx', 0) * k_move, 540), s, rim=dict(col=COLD, amt=0.0, dir=(0, -1)),
                         grade=c['grade'], wind_amp=1.5, shade=None, wrap=0.0, breathe=0.002)
        info = dict(tip=None, top=None, box=((0, 0), (W, H)), A=Aw)
    else:
        mb = c.get('mblur', (0, 0))
        if t - ts < 0.08 and pi > 0: mb = (mb[0] + 24 * (1 - (t - ts) / 0.08), mb[1])     # 切换瞬间的动势模糊
        bob = c.get('bob', 0) * abs(math.sin(math.pi * (t - t0) * 1.7))
        ex = (0, -bob)
        if 'shake' in fxs: dx, dy = shake(t, 7 * math.exp(-(t - t0) / 0.6) + 2, seed); ex = (ex[0] + dx, ex[1] + dy)
        fr, info = _place(fr, t, sid, key, c, c['at'], h=c.get('h'), w=c.get('w'), anc=c.get('anc', (0.5, 1.0)), look=c.get('look'),
                          rim=c.get('rim', COLD), rim_amt=c.get('rim_amt', 1.8), alpha=c.get('alpha', 1.0), defocus=c.get('defocus', 0.0),
                          wind=c.get('wind', 6.0), mblur=mb, k_move=k_move, extra=ex)
        if c.get('split'):                              # S075 对角分屏：右侧太上皇金边剪影，斜刀线隔开
            s2 = c['second']
            fr2, _ = _place(fr.copy(), t, sid, s2['key'], s2, s2['at'], h=s2['h'], look=s2.get('look'), rim=s2['rim'], rim_amt=3.0, k_move=k_move)
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            d = (xx - 960) * 0.87 - (yy - 540) * 0.5      # 斜线
            m = np.clip(d / 4 + 0.5, 0, 1)
            fr = fr * (1 - m[..., None]) + fr2 * m[..., None]
            line = np.exp(-(d / 3) ** 2)
            fr = fr + (line * 1.2 + np.exp(-(d / 25) ** 2) * 0.4)[..., None] * np.array([1.0, 0.85, 0.7], np.float32) * ease((t - t0) / 0.2)

    if 'credit_shade' in fxs: fr = fr * (1 - shade_m)
    tip = info['tip']
    # ---- 刀光（过刀尖的圆弧）/ 闪白
    sl_times = []
    if 'slash' in fxs or 'slash_red' in fxs or 'slash_gold' in fxs:
        sl_times = [c.get('slash_t', ts if pi > 0 else t0 + 0.05)]
        if c.get('slash2'): sl_times.append(c['slash2'])
    for k_, st in enumerate(sl_times):
        a = t - st
        if 0 <= a < 0.5 and tip:
            bx = info['box']; cxy = ((bx[0][0] + bx[1][0]) / 2, bx[0][1] + (bx[1][1] - bx[0][1]) * 0.42)
            sd = c.get('slash', {}); sq = sd.get('squash', 1.0)
            r = math.hypot(tip[0] - cxy[0], (tip[1] - cxy[1]) / sq)
            ang = math.degrees(math.atan2((tip[1] - cxy[1]) / sq, tip[0] - cxy[0]))
            sweep = sd.get('sweep', 140) * sd.get('dir', 1) * (1 if k_ == 0 else -1)
            col = (1.0, 0.97, 0.94); edge = (0.75, 0.08, 0.06)
            if 'slash_gold' in fxs: col, edge = (1.0, 0.9, 0.6), (0.9, 0.55, 0.15)
            if 'slash_red' in fxs: col, edge = (1.0, 0.75, 0.7), (0.8, 0.06, 0.05)
            fr = fx_arc(fr, cxy, r, ang, sweep, eout(a / 0.07), math.exp(-a / 0.2), w=14, col=col, edge=edge, squash=sq)
            fr = fx_sparks(fr, t, st, tip, seed + k_, n=50, spd=900, dirv=(math.cos(math.radians(ang + 90 * np.sign(sweep))), math.sin(math.radians(ang + 90 * np.sign(sweep)))))
    if 'flash' in fxs:
        for s in sw[1:] + sl_times:
            if 0 <= t - s < 0.1: fr = fr + 0.55 * (1 - (t - s) / 0.1)
    if 'flash0' in fxs and t - t0 < 0.1: fr = fr + 0.5 * (1 - (t - t0) / 0.1)
    if 'flash_end' in fxs and t1 - t < 0.12: fr = fr + 0.7 * (1 - (t1 - t) / 0.12)
    if 'flash_ink' in fxs:
        for s in sw[1:]:
            if 0 <= t - s < 0.12: fr = fr * (1 - 0.35 * (1 - (t - s) / 0.12)) + 0.35 * (1 - (t - s) / 0.12) * np.array([0.62, 0.1, 0.07], np.float32)

    # ---- 人物之上的特效
    if 'eye' in fxs:
        bx = info['box']; e = c['eye']
        p = (bx[0][0] + e[0] * (bx[1][0] - bx[0][0]), bx[0][1] + e[1] * (bx[1][1] - bx[0][1]))
        te = c.get('eye_t', sw[-1] + 0.02)
        g = math.exp(-max(0, t - te) / 0.18) * (t >= te) * 0.9
        fr = fx_star(fr, p, g)
    if 'tipstar' in fxs and tip:
        fr = fx_star(fr, tip, 0.5 + 0.4 * math.sin(t * 7), GOLD)
    if 'beam' in fxs and tip:
        k = ease((t - t0 - 0.3) / 0.8)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        beam = np.exp(-((xx - tip[0] - (yy - tip[1]) * -0.15) / (30 + 0.12 * np.clip(tip[1] - yy, 0, None) + 1)) ** 2) * (yy < tip[1])
        fr = fr + beam[..., None] * k * 0.6 * np.array(GOLD, np.float32)
        fr = fx_star(fr, tip, k * 1.0, GOLD)
    if 'sun' in fxs:
        bx = info['box']; p = ((bx[0][0] + bx[1][0]) / 2, bx[0][1] + 0.215 * (bx[1][1] - bx[0][1]))
        k = ease((t - t0) / 0.6)
        fr = fx_glow(fr, p, 60, 1.1 * k, (1.0, 0.8, 0.5)); fr = fx_glow(fr, p, 260, 0.45 * k, GOLD); fr = fx_star(fr, p, 0.6 * k, GOLD)
    if 'sheen' in fxs or 'sheen_gold' in fxs or 'sheen_blade' in fxs:
        q = (t - t0) / (t1 - t0)
        yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
        band = np.exp(-(((xx * 2 + yy * 2 * 0.6) - (-200 + 2600 * q)) / 90) ** 2)
        steel = cv2.resize(np.clip((fr[::2, ::2].max(-1) - 0.28) * 3, 0, 1).astype(np.float32), (W // 2, H // 2))
        Am = cv2.resize(info['A'][::2, ::2], (W // 2, H // 2)) if info['A'] is not None else 1
        sh = cv2.resize((band * steel * Am).astype(np.float32), (W, H))
        col = GOLD if 'sheen_gold' in fxs else (0.9, 0.95, 1.0)
        fr = fr + sh[..., None] * 0.9 * np.array(col, np.float32)
    if 'strings' in fxs:                              # 指尖垂下朱红丝线
        A = info['A']; L = np.zeros((H, W), np.float32)
        ys, xs = np.nonzero(A[::4, ::4] > 0.5)
        if len(xs):
            xs, ys = xs * 4, ys * 4
            for b in np.linspace(xs.min(), xs.max(), 6)[:-1]:
                sel = (xs >= b) & (xs < b + (xs.max() - xs.min()) / 5)
                if sel.sum() < 3: continue
                j = np.argmax(ys[sel]); px, py = xs[sel][j], ys[sel][j]
                sway = 12 * math.sin(t * 2 + b)
                cv2.line(L, (int(px), int(py)), (int(px + sway), H), 1.0, 2, cv2.LINE_AA)
        fr = fr * (1 - L[..., None] * 0.9) + L[..., None] * np.array([0.68, 0.06, 0.05], np.float32)
    if 'sparks_tip' in fxs and tip:
        st = ts if pi > 0 else t0
        fr = fx_sparks(fr, t, st, tip, seed + 5, n=40, spd=600, dirv=(0, -1), spread=1.4)
    if 'sparks_trail' in fxs and tip:                 # 刀尖擦墙火星
        for j in range(4):
            fr = fx_sparks(fr, t, t - 0.05 - 0.1 * j, tip, seed + int(t * 30) + j, n=12, spd=500, dirv=(1, -0.6), spread=0.7, grav=1400, amt=0.8)
    if 'speed' in fxs:
        r = _rng(seed + int(t * 30)); L = np.zeros((H // 2, W // 2), np.float32)
        dirx = 1 if c.get('move', {}).get('dx', 0) < 0 else -1
        for _ in range(36):
            y = r.uniform(BAR, H - BAR) / 2; x = r.uniform(0, W) / 2; ln = r.uniform(60, 200) / 2
            cv2.line(L, (int(x), int(y)), (int(x + dirx * ln), int(y)), float(r.uniform(0.3, 1)), 1, cv2.LINE_AA)
        fr = fr + cv2.resize(L, (W, H))[..., None] * 0.35 * np.array([0.8, 0.85, 0.95], np.float32)
    if 'speed_radial' in fxs:
        r = _rng(seed + int(t * 30)); L = np.zeros((H // 2, W // 2), np.float32)
        for _ in range(50):
            a = r.uniform(0, 6.28); d0 = r.uniform(300, 900) / 2; ln = r.uniform(60, 220) / 2
            p0 = (480 + math.cos(a) * d0, 270 + math.sin(a) * d0); p1 = (480 + math.cos(a) * (d0 + ln), 270 + math.sin(a) * (d0 + ln))
            cv2.line(L, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), float(r.uniform(0.3, 1)), 1, cv2.LINE_AA)
        fr = fr + cv2.resize(L, (W, H))[..., None] * 0.4 * u * np.array([0.85, 0.9, 1.0], np.float32)
    if 'ring' in fxs:
        a = t - t0 - 0.03
        if a > 0:
            R_ = 120 + 1400 * eout(a / 0.7); L = np.zeros((H // 2, W // 2), np.float32)
            cv2.ellipse(L, (int(c['at'][0] / 2), int((c['at'][1] - 20) / 2)), (int(R_ / 2), int(R_ * 0.12 / 2)), 0, 0, 360, 1.0, 2, cv2.LINE_AA)
            L = cv2.resize(cv2.GaussianBlur(L, (0, 0), 1.5), (W, H))
            fr = fr + (L * 1.6 + cv2.GaussianBlur(L, (0, 0), 8) * 2)[..., None] * math.exp(-a / 0.4) * np.array([0.8, 0.88, 1.0], np.float32)
            fr = fx_sparks(fr, t, t0, (c['at'][0], c['at'][1] - 20), seed + 9, n=80, spd=700, dirv=(0, -1), spread=1.5, col=(0.75, 0.85, 1.0), grav=1500)
    if 'seal_ring' in fxs:
        a = t - t0 - 0.2
        if a > 0:
            R_ = 200 + 900 * eout(a / 0.8); L = np.zeros((H // 2, W // 2), np.float32)
            cv2.ellipse(L, (int(c['at'][0] / 2), int((c['at'][1] - 10) / 2)), (int(R_ / 2), int(R_ * 0.16 / 2)), 0, 0, 360, 1.0, 3, cv2.LINE_AA)
            L = cv2.resize(cv2.GaussianBlur(L, (0, 0), 2), (W, H))
            fr = fr * (1 - L[..., None] * 0.6) + L[..., None] * np.array([0.72, 0.06, 0.05], np.float32) * math.exp(-a / 1.2) * 1.5
    if 'debris' in fxs or 'dust' in fxs or 'press' in fxs or 'slam' in fxs:
        r = _rng(seed); L = np.zeros((H // 2, W // 2), np.float32); a = t - t0
        for i in range(22 if 'debris' in fxs else 12):
            x = r.uniform(200, 1700); y = r.uniform(-300, 400) + 900 * a * a + 200 * a
            s = r.uniform(10, 45)
            box = cv2.boxPoints(((x / 2, y / 2), (s / 2, s * 0.6 / 2), r.uniform(0, 180) + 200 * a))
            cv2.fillConvexPoly(L, box.astype(np.int32), 1.0, cv2.LINE_AA)
        L = cv2.resize(cv2.GaussianBlur(L, (0, 0), 1.2), (W, H))
        fr = fr * (1 - L[..., None] * 0.9) + L[..., None] * 0.03
        if 'dust' in fxs or 'press' in fxs:
            fr = fx_fog_feet(fr, t, c['at'][1] - 10, amt=0.55, col=(0.30, 0.27, 0.23))
    if 'splash' in fxs and len(sw) > 1:
        fr = fx_sparks(fr, t, sw[1], (960, 520), seed + 3, n=90, spd=1100, dirv=(0, -1), spread=2.4, col=(0.75, 0.85, 1.0), grav=1800)
    if 'whip' in fxs:                                 # 马尾甩出的水珠
        fr = fx_sparks(fr, t, t0 + 0.15, (info['top'][0] + 80, info['top'][1] + 120), seed + 4, n=50, spd=800, dirv=(1, 0.2), spread=0.8,
                       col=(0.7, 0.8, 1.0), grav=1200)
    if 'gold_burst' in fxs and len(sw) > 1:
        fr = fx_sparks(fr, t, sw[-1], (960, 560), seed + 6, n=140, spd=1000, dirv=(0, -1), spread=3.1, col=GOLD, grav=300)
    if 'eyefire' in fxs:
        k = ease((t - t0 - 0.35) / 0.4)
        p = (0.33 * W, 0.53 * H)                    # 原图瞳孔位置（S102 eye_open raw）
        fr = fx_glow(fr, p, 22, 0.6 * k, (1.0, 0.6, 0.25)); fr = fx_star(fr, p, 0.35 * k, (1.0, 0.75, 0.4))
    if 'reflect' in fxs:                              # 积水倒影：下半画面上下翻转叠一层
        hy = 700
        ref = fr[hy - (H - hy):hy][::-1]
        wob = (np.sin(np.arange(ref.shape[0])[:, None] / 6 + t * 5) * 4).astype(np.int32)
        fr[hy:] = fr[hy:] * 0.55 + np.roll(ref, 0, 1) * 0.45
    if 'click' in fxs:
        k = math.exp(-max(0, t - (t0 + 0.9)) / 0.15) * (t > t0 + 0.9)
        fr = fr + k * 0.25
        if info['tip']: fr = fx_star(fr, info['tip'], k, GOLD)

    # ---- 前景纵深层（特写：火星/雨/虚焦光斑；全景：脚部雾带）
    if 'fog_feet' in fxs and not c.get('full'): fr = fx_fog_feet(fr, t, c['at'][1] + 10, amt=0.85)
    if 'rain' in fxs: fr = fx_rain(fr, t, seed, amt=0.3)
    if 'rain_near' in fxs: fr = fx_rain(fr, t, seed + 1, amt=0.22, n=60, near=True)
    if 'embers' in fxs: fr = fx_embers(fr, t, seed, amt=0.6)
    if 'embers_fg' in fxs: fr = fx_embers(fr, t, seed + 2, amt=0.7, n=18, big=True, rise=140)
    if 'dust_fg' in fxs: fr = fx_embers(fr, t, seed + 2, amt=0.25, n=30, big=True, col=(0.8, 0.8, 0.85), rise=40)
    if 'bokeh' in fxs: fr = fx_bokeh(fr, t, seed, 0.22)
    if 'bokeh_gold' in fxs: fr = fx_bokeh(fr, t, seed, 0.3, col=GOLD)
    return fr
