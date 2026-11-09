"""units/b_kit.py — B 组（预副歌一 + 间奏/主歌二）公共件。只供 units/sec_b_pre1.py / units/sec_b_verse2.py 使用。
- 时间：V()（声音→视觉帧，早 1 帧）、CT()（逐字字头）、tp()（字进度）、kicks（B 组卡点图强拍）
- 精灵：spr(name) 读 assets/gen/B_r4/<name>_cutd.png（去灰边版）或 assets/gen/<镜号>/<姿势>_cut.png
- 道具：blade_prop()（从 blade_face 生图里裁出的真实刀身贴图，用于烧红/横刀特写，取代矢量刀）
- 收尾：Section（CUTS 表驱动转场、切点冲击、前景粒子、曝光、c1kit.finish 与副歌一同一套调色）"""
import sys, math, os, json
ROOT = '/workspace/work/mv'
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, cv2
from PIL import Image
import c1kit as K
from c1kit import clamp01, eio, eout, ein, sstep, pulse, cam, over, RED, GOLD, W, H, BAR
import typo as T
import trans as TR
import sprite as SP
import vcam as VC
import grade_unify as GU                     # 全片统一 grade 层（GRADE_UNIFY=1 生效）

for _k, _f in (('serif_r', 'Regular'), ('serif_m', 'Medium'), ('serif_sb', 'SemiBold'), ('serif_b', 'Bold'), ('serif_black', 'Black')):
    T.FONTS.setdefault(_k, ROOT + f'/fonts/NotoSerifSC-{_f}.otf')

FPS = 30
LINES = T.load_lines()
COLD = np.array([0.62, 0.74, 1.0], np.float32)
WARM = np.array([1.0, 0.68, 0.36], np.float32)
WHITE = np.array([0.96, 0.94, 0.90], np.float32)


def V(t):
    return (round(t * FPS) - 1) / FPS


def CT(li, k):
    ts = [x for x in LINES[li]['times'] if x is not None]
    return ts[min(k, len(ts) - 1)]


def tp(li, ks, t, dur=0.22):
    """第 li 句第 ks 个字的进度（字头视觉帧恰好 =1）"""
    return [clamp01((t - (V(CT(li, k)) - dur)) / dur) for k in ks]


def _hits(tag):
    d = json.load(open(ROOT + f'/crew/round4/B_hitmap_{tag}.json'))
    return [h['t'] for h in d['hits'] if h['strength'] >= 0.62]
KICKS = sorted(_hits('pre1') + _hits('verse2'))


def kick_env(t, decay=0.10):
    """最近一个强拍后的冲击包络（0..1）"""
    i = np.searchsorted(KICKS, t + 1 / 60) - 1
    if i < 0: return 0.0
    dt = t - V(KICKS[i])
    return math.exp(-dt / decay) if 0 <= dt < 0.5 else 0.0


def shake(t, amp, freq=9.0, seed=0):
    return K.shake(t, amp * (0.35 if freq > 5 else 0.6), freq, seed)


# ------------------------------------------------------------------ 精灵
GEN = ROOT + '/assets/gen/'


_SPR = {}


def defringe(sp, choke=0.12, band=7):
    """去灰边（第二棒）：半透明边带的颜色换成内部颜色向外扩散（色彩去污染），alpha 收紧一点。
    原地修改 SpriteLayer（F/A/ring），同一张精灵只做一次。"""
    A = sp.A
    core = (A > 0.92).astype(np.float32)
    core = cv2.erode(core, np.ones((3, 3), np.uint8))
    num = cv2.GaussianBlur(sp.F * core[..., None], (0, 0), band)
    den = cv2.GaussianBlur(core, (0, 0), band)[..., None]
    inner = num / np.clip(den, 1e-4, None)
    edge = ((A < 0.97) & (den[..., 0] > 1e-3)).astype(np.float32)
    edge = cv2.GaussianBlur(edge, (0, 0), 1.0)[..., None]
    sp.F = (sp.F * (1 - edge) + np.minimum(sp.F, inner) * edge).astype(np.float32)
    sp.A = np.clip((A - choke) / (1 - choke), 0, 1).astype(np.float32)
    ring = sp.A - cv2.erode(sp.A, np.ones((5, 5), np.uint8))
    sp.ring = cv2.GaussianBlur(np.clip(ring, 0, 1), (0, 0), 1.5)
    return sp


def spr(name, clean=True, work_w=2048):
    """B 组精灵（独立实例，不污染 SP.layer 共享缓存）；clean=True 时做 defringe 去灰边；
    work_w：工作分辨率（第九棒：特写手部用 3072/3840，避免 2048 再放大成「泥团手」）"""
    key = (name, clean, work_w)
    if key in _SPR: return _SPR[key]
    p = GEN + 'B_r4/' + name + '_cutd.png'
    if not os.path.exists(p): p = GEN + name + '_cut.png'
    sp = SP.SpriteLayer(p, work_w=work_w)
    if clean: defringe(sp)
    _SPR[key] = sp
    return sp


def spr_feather(name, left=0.0, right=0.0, top=0.0, bottom=0.0, keep_col=None):
    """满幅特写精灵（如 tsh_brush_hand）：靠画布边缘的部分渐隐进暗部，避免生图边框成硬边；
    keep_col=(x0,x1) 归一化列范围在 bottom 渐隐里保留（例如笔杆）"""
    key = ('feather', name, left, right, top, bottom, keep_col)
    if key in _SPR: return _SPR[key]
    p = GEN + 'B_r4/' + name + '_cutd.png'
    sp = SP.SpriteLayer(p)
    h, w = sp.A.shape
    xx = np.linspace(0, 1, w, dtype=np.float32)[None]; yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    m = np.ones((h, w), np.float32)
    if left: m *= sstep(0, left, xx)
    if right: m *= sstep(1, 1 - right, xx)
    if top: m *= sstep(0, top, yy)
    if bottom:
        mb = sstep(1, 1 - bottom, yy) * np.ones((1, w), np.float32)
        if keep_col:
            kc = sstep(keep_col[0] - 0.02, keep_col[0], xx) * sstep(keep_col[1] + 0.02, keep_col[1], xx)
            mb = np.maximum(mb, kc * sstep(1.0, 0.96, yy))
        m *= mb
    sp.A = sp.A * m; sp.ring = sp.ring * m
    _SPR[key] = sp
    return sp


GR_COLD = dict(expo=0.72, sat=0.55, tint=(0.90, 0.96, 1.06), lift=0.0, gamma=1.18)
GR_WARM = dict(expo=0.80, sat=0.75, tint=(1.06, 0.97, 0.86), lift=0.0, gamma=1.12)
RIM_COLD = dict(col=(0.62, 0.74, 1.0), amt=1.8, dir=(-0.8, -0.6))
RIM_WARM = dict(col=(1.0, 0.70, 0.40), amt=1.6, dir=(0.8, -0.4))


def put(fr, sp, t, h_px, foot, grade=None, rim=None, **kw):
    """按 alpha 包围盒高度 h_px 把精灵脚底（包围盒底中点）放到屏幕 foot"""
    a, s = sp.fit(h_px)
    return sp.draw(fr, t, a, foot, s * sp.w / sp.w, grade=grade or GR_COLD, rim=rim or RIM_COLD, **kw)


def put_at(fr, sp, t, src, dst, width_px, grade=None, rim=None, **kw):
    """精灵内归一化点 src → 屏幕 dst；width_px = 精灵整幅宽在屏幕上的像素"""
    return sp.draw(fr, t, src, dst, width_px / sp.w, grade=grade or GR_COLD, rim=rim or RIM_COLD, **kw)


# ------------------------------------------------------------------ 真实刀身贴图（blade_face 生图）
_BL = {}


def blade_prop():
    """返回 (F, A)：竖直刀身贴图（刃尖朝上，底部带护手），float32，约 120×1345 → 统一放大 2 倍 240×2690"""
    if 'b' in _BL: return _BL['b']
    im = np.asarray(Image.open(GEN + 'B_r4/blade_face_raw.png').convert('RGB')).astype(np.float32) / 255
    x0, x1 = 1700, 2100
    F = im[0:1345, x0:x1].copy()
    A = np.zeros(F.shape[:2], np.float32)
    A[:1222, 1841 - x0:1957 - x0] = 1.0                    # 刀身
    gd = np.zeros_like(A); cv2.rectangle(gd, (1718 - x0, 1222), (2075 - x0, 1340), 1.0, -1)   # 护手
    A = np.maximum(A, gd)
    A = cv2.GaussianBlur(A, (0, 0), 0.8)
    F = cv2.resize(F, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    A = cv2.resize(A, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    lum = F.mean(-1, keepdims=True)
    F = np.clip(lum + (F - lum) * 0.35, 0, 1)                 # 去掉一点暖色（护手之外是钢）
    _BL['b'] = (F.astype(np.float32), A.astype(np.float32))
    return _BL['b']


def blade_strip():
    """只要刀身（不含护手）横置：刃口朝下，刀尖方向朝右。返回 (F, A) 尺寸约 232×2444"""
    if 's' in _BL: return _BL['s']
    F, A = blade_prop()
    F = F[:2444]; A = A[:2444]
    xs = np.nonzero(A[1000] > 0.5)[0]; a, b = xs.min() - 4, xs.max() + 5
    F = F[:, a:b]; A = A[:, a:b]
    F = np.ascontiguousarray(np.rot90(F, -1)); A = np.ascontiguousarray(np.rot90(A, -1))     # 刀尖朝左→翻
    _BL['s'] = (F, A)
    return _BL['s']


def paste_rgba(fr, F, A, M, alpha=1.0, add=None):
    """仿射 M（2×3，源→屏幕）贴 RGBA"""
    Fw = cv2.warpAffine(F, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    Aw = cv2.warpAffine(A, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT) * alpha
    if add is not None: Fw = Fw + add
    return fr * (1 - Aw[..., None]) + Fw * Aw[..., None], Aw


def M_line(src_w, src_h, p0, p1, width):
    """把横置贴图（宽 src_w 高 src_h）的左边中点→p0、右边中点→p1，高度缩放为 width"""
    p0 = np.array(p0, float); p1 = np.array(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); u = d / L; n = np.array([-u[1], u[0]])
    sx = L / src_w; sy = width / src_h
    M = np.zeros((2, 3), np.float32)
    M[:, 0] = u * sx; M[:, 1] = n * sy
    M[:, 2] = p0 - n * sy * src_h / 2
    return M


# ------------------------------------------------------------------ 背景 / 质感
def dark_bg(seed=0, lo=0.02, hi=0.07, tint=(1.0, 1.01, 1.06)):
    n = K.fbm(H // 4, W // 4, seed, base=3, octaves=5)
    l = lo + (hi - lo) * n
    return cv2.resize(np.stack([l * tint[0], l * tint[1], l * tint[2]], -1).astype(np.float32), (W, H))


def paper(seed=11, tone=(0.80, 0.74, 0.62), dark=0.0):
    """旧纸（生死簿）：纤维 + 斑驳 + 边缘焦黄"""
    x, y = K.grid()
    n1 = K.fbm(H // 2, W // 2, seed, base=5, octaves=6); n1 = cv2.resize(n1, (W, H))
    r = np.random.default_rng(seed)
    fib = cv2.GaussianBlur(r.standard_normal((H, W)).astype(np.float32), (0, 0), 0.6)
    fib = cv2.blur(fib, (9, 1)) * 0.6 + cv2.blur(fib, (1, 7)) * 0.4
    base = np.array(tone, np.float32) * (0.82 + 0.22 * n1[..., None]) + fib[..., None] * 0.03
    stain = np.clip(K.fbm(H // 8, W // 8, seed + 7, base=3, octaves=4) - 0.55, 0, 1)
    base = base * (1 - cv2.resize(stain, (W, H))[..., None] * np.array([0.3, 0.38, 0.5], np.float32))
    return np.clip(base * (1 - dark), 0, 1).astype(np.float32)


def volumetric(fr, src, color, strength=0.6, length=0.9, seed=0):
    """简易体积光（径向模糊亮区）"""
    L = np.clip(fr.mean(-1) - 0.25, 0, 1)
    L = K.radial_blur(L[..., None].repeat(3, -1), src, length * 0.5, n=8)
    return fr + L * np.asarray(color, np.float32) * strength


def rain(fr, t, seed, amt=0.45, n=600, angle=10, speed=2300, near=0.35):
    return K.rain(fr, t, seed, n=n, amt=amt, speed=speed, angle=angle, near=near, length=(40, 120))


def glyph_layer(text_places, fname, color, scale=1.0):
    L = T.Layer()
    for p in text_places:
        T.place(L, p['ch'], p['x'], p['y'], p['size'], color=color, fname=fname, scale=scale)
    return L


# ---------------------------------------------------------------- B 组自写转场（第四棒：替换灰雾 smoke_through）
def _bfbm(seed, sc=70, oc=5):
    return cv2.resize(TR.fbm(H // 4, W // 4, seed, sc, oc).astype(np.float32), (W, H))


def cloud_wipe(A, B, p, seed=0, soft=0.06):
    """云幕下压：B（天空）带着翻卷云边从画面顶端压下来盖住 A；云边受闪电冷光照亮（冷蓝细边 + 边前轻压暗），
    不加满屏灰雾——中间帧上半是 B、下半是 A。"""
    x, y = K.grid()
    nz = _bfbm(seed)
    e = eio(p)
    yn = y / H
    front = -0.15 + 1.35 * e + (nz - 0.5) * 0.35 + 0.04 * np.sin(x / 90.0 + seed)
    m = np.clip((front - yn) / soft, 0, 1)
    out = A * (1 - m[..., None]) + B * m[..., None]
    d = (front - yn)
    rim = np.exp(-(d / 0.012) ** 2) * (0.6 + 0.8 * nz) * math.sin(math.pi * e)
    pre = np.clip(-d / 0.10, 0, 1) * (1 - np.clip(-d / 0.35, 0, 1))
    out = out * (1 - 0.45 * pre[..., None] * math.sin(math.pi * e))
    return out + rim[..., None] * COLD * 0.9


def rain_curtain(A, B, p, seed=0):
    """雨帘落幕：B 被一条条竖向雨柱从上往下「冲」进画面（每列随机延迟、长短不一），雨柱头是冷白水珠；
    中间帧是 A/B 竖条交错，带前后两镜元素，无整屏灰。"""
    x, y = K.grid()
    r = np.random.default_rng(seed)
    ncol = 160
    dl = r.uniform(0, 0.45, ncol).astype(np.float32)
    sp = r.uniform(1.6, 2.4, ncol).astype(np.float32)
    ci = np.clip((x / W * ncol).astype(np.int32), 0, ncol - 1)
    head = (p - dl[ci]) * sp[ci] * 1.25
    yn = y / H
    m = np.clip((head - yn) / 0.03, 0, 1)
    out = A * (1 - m[..., None]) + B * m[..., None]
    tip = np.exp(-((yn - head) / 0.012) ** 2) * (head > 0) * (head < 1.05)
    return out + tip[..., None] * WHITE * 0.55 * math.sin(math.pi * clamp01(p))


def zoom_dark(A, B, p, center=(W / 2, H / 2), strength=1.0):
    """推镜穿越（无白场版）：同 trans.zoom_through 的推近/径向模糊，但中点不加 +0.6 白，改为两镜在径向模糊里交叉叠化。"""
    e = eio(p)
    a = TR._radial_blur(TR._zoom(A, 1 + 1.5 * ein(min(1, p * 1.6), 2.5) * strength, center), center, 0.35 * ein(min(1, p * 1.6), 2))
    b = TR._radial_blur(TR._zoom(B, 1 + 0.8 * (1 - eout(max(0, p * 1.6 - 0.6), 3)) * strength, center), center, 0.3 * (1 - eout(max(0, p * 1.6 - 0.6), 3)))
    return a * (1 - e) + b * e


BTRANS = dict(cloud_wipe=cloud_wipe, rain_curtain=rain_curtain, zoom_dark=zoom_dark)


# ------------------------------------------------------------------ 镜头基类与段落运行器
class Shot:
    t0 = t1 = 0.0
    def u(self, t): return clamp01((t - self.t0) / (self.t1 - self.t0))


class _Lazy:
    def __init__(self, cls): self.cls = cls; self.t0 = cls.t0; self.t1 = cls.t1; self.obj = None; self.id = cls.__name__
    def render(self, t):
        if self.obj is None: self.obj = self.cls()
        return self.obj.render(t)


class Section:
    """shots：按时间排序的 Shot 子类列表；cuts：{镜名: (转场名, pre, post, kw)}；
    'hard' = 切点冲击（推近 + 提亮 2 帧）；'flash'/'flashr'/'gold' = 硬切 + 白/红/金闪 2 帧；'none' = 无冲击（连续机位）"""
    def __init__(self, shots, cuts, fg=None, expo=None, expo_all=1.15, outside=None):
        self.shots = [_Lazy(S) for S in shots]
        self.ids = [S.__name__ for S in shots]
        self.cuts = cuts; self.fgk = fg or {}; self.expo = expo or {}; self.expo_all = expo_all
        self.fg = VC.FGLayer(23, n=24)
        self.outside = outside or {}
        self.move = {}                                  # 第八棒：{镜名: (z0, z1, dx, dy, rot)} 镜内补充运镜（节奏表里静止 >1 拍的镜头）

    def _render(self, j, t):
        fr, ca = self.shots[j].render(t)
        mv = self.move.get(self.ids[j])
        if mv:
            s = self.shots[j]; u = eio(clamp01((t - s.t0) / max(1e-3, s.t1 - s.t0)))
            z0, z1, dx, dy, rot = mv
            fr = cam(fr, z0 + (z1 - z0) * u, dx * (u - 0.5), dy * (u - 0.5), rot * u)
        return fr, ca

    def idx(self, t):
        for i, s in enumerate(self.shots):
            if t < s.t1 - 1e-6: return i
        return len(self.shots) - 1

    def raw(self, t):
        i = self.idx(t)
        s = self.shots[i]
        for j in (i, i + 1):
            if j <= 0 or j >= len(self.shots): continue
            b = self.shots[j]; name, pre, post, kw = self.cuts.get(self.ids[j], ('hard', 0, 0, {}))
            c = b.t0
            if name in ('hard', 'flash', 'flashr', 'gold', 'punch', 'none') or not (c - pre - 1e-6 <= t < c + post - 1e-6): continue
            a = self.shots[j - 1]
            B, ca2 = self._render(j, t)
            A, ca1 = self._render(j - 1, t) if (pre > 0 or t < c) else (B, 0)
            p = (t - (c - pre)) / (pre + post)
            if pre == 0: p = 0.5 + 0.5 * p
            A_ = np.clip(A, 0, 4).astype(np.float32); B_ = np.clip(B, 0, 4).astype(np.float32)
            out = BTRANS[name](A_, B_, float(np.clip(p, 0, 1)), **kw) if name in BTRANS else TR.transition(name, A_, B_, p, **kw)
            return out, max(ca1, ca2)
        fr, ca = self._render(i, t)
        name = self.cuts.get(self.ids[i], ('hard',))[0]
        if i > 0 and name in ('hard', 'flash', 'flashr', 'gold', 'punch'):
            k = int((t - s.t0) * 30 + 1e-6)
            if k < 2:
                a = 1.0 if k == 0 else 0.45
                fr = cam(fr, 1 + 0.03 * a) * (1 + 0.15 * a) + 0.04 * a
                if name == 'flash': fr = fr * (1 - 0.6 * a) + 0.85 * a
                elif name == 'flashr': fr = fr * (1 - 0.55 * a) + RED * 1.2 * a
                elif name == 'gold': fr = fr * (1 - 0.5 * a) + GOLD * 0.9 * a
                elif name == 'punch':                       # 无白闪的硬切冲击：推近 + 色散错位
                    fr = np.stack([np.roll(fr[..., 0], int(10 * a), 1), fr[..., 1], np.roll(fr[..., 2], -int(10 * a), 1)], -1)
                ca = max(ca, 3 if k == 0 else 1)
        return fr, ca

    def frame_f(self, t):
        fr, ca = self.raw(t)
        sid = self.ids[self.idx(t)]
        ke = kick_env(t)
        if ke > 0.05:                                         # 强拍：微推 + 暗角脉冲
            fr = cam(fr, 1 + 0.012 * ke)
            ca = max(ca, int(round(2 * ke)))
        kind, amt = self.fgk.get(sid, (None, 0))
        if kind:
            fr = self.fg.draw(fr, t, dict(x=0.0, y=0.0, z=1.0), kind, amt)
        fr = fr * (self.expo_all * self.expo.get(sid, 1.0))
        fr = fr + 0.012 * (1 - np.clip(fr, 0, 1))
        return GU.apply(K.finish(fr, t, ca=ca, vig=0.42, red_keep=1.0), t, GU.key_for_t(t))   # 统一 grade 层

    def frame(self, f):
        return K.to8(self.frame_f(f / FPS))
