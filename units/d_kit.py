"""units/d_kit.py — [D组] Bridge「风暴之眼」专用工具（只供 units/sec_d_bridge.py 使用）。
宣纸世界：水墨精灵（把生图人物按亮度换算成墨量、乘进纸里，暗红保留为朱）、墨字（乘法合成，纸纹透出、边缘洇墨）；
暗世界：风暴云涡、闪电、余烬、金光；统一收尾 d_finish（纸面暖白不被冷灰调色吃掉）。粒子全部无状态。"""
import sys, math, os
ROOT = '/workspace/work/mv'
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, cv2
from functools import lru_cache
import c1kit as K
import typo as T
import sprite as SP

W, H, BAR = 1920, 1080, 120
FPS = 30
INK = np.array([0.055, 0.05, 0.048], np.float32)
CINNABAR = np.array([0.74, 0.10, 0.06], np.float32)
RED = K.RED; GOLD = K.GOLD
PAPER_TINT = np.array([1.0, 0.975, 0.925], np.float32)

for _k, _f in (('serif_r', 'Regular'), ('serif_m', 'Medium'), ('serif_sb', 'SemiBold'), ('serif_b', 'Bold'), ('serif_black', 'Black')):
    T.FONTS.setdefault(_k, ROOT + f'/fonts/NotoSerifSC-{_f}.otf')

LINES = T.load_lines()
LYRIC_UNI = os.environ.get('LYRIC_UNI', '0') == '1'   # [lyric-uni] 全片统一字幕层开关


def onsets(li):
    return [x for x in LINES[li]['times'] if x is not None]


def V(t):
    """声音时刻 → 视觉帧时刻（最近帧再提前 1 帧）"""
    return (round(t * FPS) - 1) / FPS


def cp(t, t_on, dur=0.18):
    """字进度：在 t_on 视觉帧恰好落定"""
    return K.clamp01((t - (V(t_on) - dur)) / dur)


# ------------------------------------------------------------------ 纸 / 背景
@lru_cache(None)
def paper(seed=11, tone=0.93):
    p = K.paper_light(seed)
    l = p.mean(-1, keepdims=True)
    f = K.fbm(H // 4, W // 4, seed + 40, base=3, octaves=4)
    blot = cv2.resize(f, (W, H))[..., None]
    out = (tone * (0.93 + 0.07 * (l / max(1e-3, float(l.mean())))) * (0.97 + 0.05 * blot)) * PAPER_TINT
    return np.clip(out, 0, 1).astype(np.float32)


@lru_cache(None)
def fiber(seed=3):
    """纸纤维细纹（乘法用，~1）"""
    r = np.random.default_rng(seed)
    a = np.zeros((H, W), np.float32)
    for _ in range(900):
        x, y = r.uniform(0, W), r.uniform(0, H); L = r.uniform(20, 90); th = r.uniform(0, math.pi)
        cv2.line(a, (int(x), int(y)), (int(x + L * math.cos(th)), int(y + L * math.sin(th))), float(r.uniform(0.3, 1)), 1, cv2.LINE_AA)
    return 1 - 0.05 * cv2.GaussianBlur(a, (0, 0), 0.6)


def wash(fr, amt, y0=0.0, y1=1.0, seed=5, col=INK):
    """淡墨晕染（上→下或任意带）"""
    n = cv2.resize(K.fbm(H // 6, W // 6, seed, base=3, octaves=5), (W, H))
    g = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    band = K.sstep(y0, y1, g)
    m = np.clip(band * (0.6 + 0.8 * n) * amt, 0, 1)[..., None]
    return fr * (1 - m) + col * m


# ------------------------------------------------------------------ 精灵
_SPR = {}


class DSprite(SP.SpriteLayer):
    """去灰边：轮廓带内接近底灰(0.5)且不饱和的像素降透明度（抠图残留的灰片）"""
    def __init__(self, path, work_w=2048):
        super().__init__(path, work_w)
        F, A = self.F, self.A
        lum = F.mean(-1); sat = F.max(-1) - F.min(-1)
        inside = (A > 0.5).astype(np.uint8)
        dist = cv2.distanceTransform(inside, cv2.DIST_L2, 5)
        greyish = (np.abs(lum - 0.47) < 0.13) & (sat < 0.07) & (dist < 40)
        g = cv2.GaussianBlur(greyish.astype(np.float32), (0, 0), 2)
        self.A = np.clip(A * (1 - 0.92 * g), 0, 1).astype(np.float32)
        self.A = cv2.GaussianBlur(cv2.erode(self.A, np.ones((3, 3), np.uint8)), (0, 0), 0.7)
        ring = self.A - cv2.erode(self.A, np.ones((5, 5), np.uint8))
        self.ring = cv2.GaussianBlur(np.clip(ring, 0, 1), (0, 0), 1.5)


def spr(name):
    if name not in _SPR:
        p = name if name.startswith('/') else (ROOT + '/assets/gen/' + (name if '/' in name else 'D_bridge/' + name) + '_cut.png')
        _SPR[name] = DSprite(p)
    return _SPR[name]


def fit_scale(sp, h):
    x0, y0, x1, y1 = sp.bbox
    return h / ((y1 - y0) * sp.h)


def feet(sp):
    x0, y0, x1, y1 = sp.bbox
    return ((x0 + x1) / 2, y1)


def warp(sp, t, anchor_src, dst, scale, rot=0.0, flip=False, wind=5.0):
    F, A, R = sp.wind(t, wind) if wind > 0 else (sp.F, sp.A, sp.ring)
    ax, ay = anchor_src
    if flip:
        F = F[:, ::-1]; A = A[:, ::-1]; R = R[:, ::-1]; ax = 1 - ax
    ax, ay = ax * sp.w, ay * sp.h
    M = cv2.getRotationMatrix2D((ax, ay), rot, scale)
    M[0, 2] += dst[0] - ax; M[1, 2] += dst[1] - ay
    Fw = cv2.warpAffine(np.ascontiguousarray(F), M, (W, H), flags=cv2.INTER_LINEAR)
    Aw = cv2.warpAffine(np.ascontiguousarray(A), M, (W, H), flags=cv2.INTER_LINEAR)
    return Fw, Aw


def ink_figure(fr, sp, t, anchor_src, dst, scale, rot=0.0, flip=False, wind=5.0, k=1.55, gamma=0.85, dens=0.96,
               bleed=0.16, red=True, shadow=0.0, alpha=1.0, blur=0.0):
    """水墨人物：亮度→墨量，乘进纸里（纸纹透出），暗红保留为朱；边缘洇墨。返回 (fr, Aw)。"""
    Fw, Aw = warp(sp, t, anchor_src, dst, scale, rot, flip, wind)
    Aw = Aw * alpha
    lum = (Fw * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1)
    d = np.clip(1 - lum * k, 0, 1) ** gamma * dens
    rm = SP.red_mask(Fw) if red else np.zeros_like(lum)
    if blur > 0.3:
        Aw = cv2.GaussianBlur(Aw, (0, 0), blur); d = cv2.GaussianBlur(d, (0, 0), blur)
    m = (Aw * np.maximum(d, rm * 0.85))[..., None]
    colr = INK * (1 - rm[..., None]) + CINNABAR * rm[..., None]
    out = fr * (1 - m) + colr * m * (fr / 0.93)          # 墨乘纸
    if bleed > 0:
        hb = cv2.GaussianBlur(Aw * d, (0, 0), 7) - Aw * d
        out = out * (1 - np.clip(hb, 0, 1)[..., None] * bleed * 2.2)
    if shadow > 0:
        ys, xs = np.nonzero(Aw > 0.5)
        if len(ys):
            fy = ys.max(); fx = xs[ys > fy - 6].mean() if (ys > fy - 6).any() else xs.mean()
            sh = np.zeros((H, W), np.float32)
            cv2.ellipse(sh, (int(fx), int(fy)), (int((xs.max() - xs.min()) * 0.55 + 10), int(12 + (xs.max() - xs.min()) * 0.06)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
            sh = cv2.GaussianBlur(sh, (0, 0), 14) * shadow
            out = out * (1 - sh[..., None] * (1 - Aw[..., None]))
    return out, Aw


def real_figure(fr, sp, t, anchor_src, dst, scale, rot=0.0, expo=0.8, sat=0.6, tint=(0.95, 0.97, 1.03), gamma=1.15,
                rim=(0.62, 0.74, 1.0), rim_amt=2.0, rim_dir=(-0.8, -0.6), wrap=0.35, wind=6.0, keep_red=1.0, **kw):
    out, Aw = sp.draw(fr, t, anchor_src, dst, scale, rot=rot, wind_amp=wind,
                      grade=dict(expo=expo, sat=sat, tint=tint, lift=0.0, gamma=gamma),
                      rim=dict(col=rim, amt=rim_amt, dir=rim_dir), wrap=wrap, shade=None, keep_red=keep_red, **kw)
    return out, Aw


def metal_sheen(fr, Aw, F_scr_lum, t, center, angle, speed=1.0, width=60, amt=1.2, col=(1.0, 0.97, 0.9)):
    """刀身流光：高亮低饱和像素（金属）× 移动光带"""
    x, y = K.grid()
    th = math.radians(angle)
    s = (x - center[0]) * math.cos(th) + (y - center[1]) * math.sin(th)
    band = np.exp(-((s - speed) / width) ** 2)
    m = Aw * np.clip((F_scr_lum - 0.35) * 3, 0, 1) * band
    return fr + m[..., None] * np.array(col, np.float32) * amt


# ------------------------------------------------------------------ 字
def text_layer(chars, color='ink', fname='serif_black', blur=0.0):
    """chars: [(ch, x, y, size, alpha, scale, rot, color?)] → Layer"""
    L = T.Layer()
    for c in chars:
        ch, x, y, s, a = c[:5]
        sc = c[5] if len(c) > 5 else 1.0; rot = c[6] if len(c) > 6 else 0.0; cc = c[7] if len(c) > 7 else color
        T.place(L, ch, x, y, s, cc, fname, alpha=a, scale=sc, rot=rot, blur=blur, texture=False)
    return L


def ink_text(fr, L, bleed=0.22, sig=5.0, dens=1.0):
    """墨字乘进纸：纸纹透出 + 外缘洇墨"""
    bx = L.box(int(sig * 4) + 4)
    if bx is None: return fr
    x0, y0, x1, y1 = bx
    out = fr.copy()
    A = L.A[y0:y1, x0:x1] * dens; C = L.C[y0:y1, x0:x1]
    F = out[y0:y1, x0:x1]
    if bleed > 0:
        hb = np.clip(cv2.GaussianBlur(A, (0, 0), sig) - A, 0, 1)
        F *= (1 - hb * bleed * 2.0)[..., None]
    F[:] = F * (1 - A[..., None]) + C * A[..., None] * (F / 0.93)
    return out


def light_text(fr, L, style=None):
    kw = dict(shadow=0.7, shadow_sigma=22, glow=0.25, glow_sigma=14)
    kw.update(style or {})
    return T.compose(fr, L, **kw)


def column(text, x, y0, size, prog, adv=1.18, color='ink', emph=None, fname='serif_sb', drop=40, horiz=False):
    if LYRIC_UNI: return []                    # [lyric-uni] LYRIC_UNI=1 时由 units/lyric_uni.py 统一出字幕
    """竖（横）排逐字：prog 每字 0..1，入场 下落+放大回弹+淡入"""
    out = []
    for i, ch in enumerate(text):
        p = prog[i] if i < len(prog) else 0
        if p <= 0: continue
        e = K.eout(p, 3)
        c = (emph or {}).get(ch, color)
        x = x + (i * size * adv if horiz else 0) if False else (x + i * size * adv if horiz else x)
        y = y0 if horiz else y0 + i * size * adv
        out.append((ch, (x if not horiz else x), y - drop * (1 - e), size, min(1, p * 1.6), 1 + 0.25 * (1 - e), 0.0, c))
    return out


def ink_spray(fr, t, t0, origin, n=40, seed=0, power=600, size=(2, 9), col=INK, life=0.5, grav=900):
    """墨点飞溅（乘法，纸上）"""
    if t < t0: return fr
    age = t - t0
    if age > life * 3: age = life * 3
    r = np.random.default_rng(seed)
    ang = r.uniform(math.pi, 2 * math.pi, n) if True else 0
    ang = r.uniform(0, 2 * math.pi, n)
    sp_ = r.uniform(0.3, 1, n) * power
    m = np.zeros((H // 2, W // 2), np.float32)
    k = K.eout(min(1, age / life), 3) * life
    for i in range(n):
        px = origin[0] + math.cos(ang[i]) * sp_[i] * k
        py = origin[1] + math.sin(ang[i]) * sp_[i] * k * 0.45 + 0.5 * grav * 0.0
        rr = r.uniform(*size)
        cv2.circle(m, (int(px / 2), int(py / 2)), max(1, int(rr / 2)), 1.0, -1, cv2.LINE_AA)
    m = cv2.resize(cv2.GaussianBlur(m, (0, 0), 0.6), (W, H))[..., None]
    return fr * (1 - m * 0.9) + col * m * 0.9


def fall_chars(fr, t, text, seed, density=10, sizes=(26, 70), speed=(180, 420), layers=3, ink=True, alpha=0.8,
               region=(0, W), t0=150.0, emph=None, wind=30, fname='serif_m', near_blur=6):
    """景深字雨：远小清淡、近大虚焦；无状态（t 绝对时间，周期循环）"""
    r = np.random.default_rng(seed)
    N = int(density * 6)
    Ls = []
    for li in range(layers):
        z = (li + 1) / layers                     # 0.33 远 … 1 近
        L = T.Layer()
        n = int(N * (1.4 - z * 0.6))
        xs = r.uniform(region[0], region[1], n); ph = r.random(n); sp_ = r.uniform(*speed, n) * (0.5 + z)
        sz = r.uniform(*sizes, n) * (0.45 + z * 0.9); rot0 = r.uniform(-40, 40, n); spin = r.uniform(-60, 60, n)
        span = (H + 300)
        for i in range(n):
            y = ((t - t0) * sp_[i] + ph[i] * span) % span - 150
            x = xs[i] + wind * z * (t - t0) % 400 * 0 + math.sin(t * 1.3 + ph[i] * 9) * 18
            ch = text[(i + li * 7) % len(text)]
            c = (emph or {}).get(ch, 'ink' if ink else 'white')
            a = alpha * (0.35 + 0.65 * z) if isinstance(c, str) and c in ('ink', 'white') else min(1, alpha * 1.2)
            T.place(L, ch, x, y, sz[i], c, fname, alpha=a, rot=rot0[i] + spin[i] * t, texture=False)
        bl = near_blur * max(0, z - 0.5) * 2
        Ls.append((L, bl, z))
    out = fr
    for L, bl, z in Ls:
        if bl > 0.5:
            L.A = cv2.GaussianBlur(L.A, (0, 0), bl)
        out = ink_text(out, L, bleed=0.1 if ink else 0, dens=0.9) if ink else light_text(out, L, dict(shadow=0.3, glow=0.1))
    return out


# ------------------------------------------------------------------ 暗世界
@lru_cache(None)
def _tile(seed, n=512, base=5, octaves=6):
    return K.tile(n, seed, base, octaves)


def storm(t, seed=7, c=(960, 380), spin=0.05, twist=0.55, base=(0.035, 0.04, 0.055), lit=(0.42, 0.46, 0.56), eye=150,
          bright=1.0, scale=1, glow=None):
    """风暴云涡（第二棒重写，去「旋转滤镜」味）：三层不同尺度的云密度（极坐标 + 对数螺旋，整数倍频率无接缝），
    朝风眼一侧的云边吃光（银边）、背光侧自阴影、云底暗；风眼内是发光的雾；外圈拉丝的风带；可选 glow=(x,y,amt) 云内闪电照亮。"""
    h2, w2 = H // 2, W // 2
    yy, xx = np.mgrid[0:h2, 0:w2].astype(np.float32)
    dx = xx * 2 - c[0]; dy = (yy * 2 - c[1]) * 1.35
    r = np.sqrt(dx * dx + dy * dy) + 1
    th = np.arctan2(dy, dx)
    lr = np.log(r)
    u0 = (th / (2 * math.pi)) + spin * t + twist * lr * 0.25
    v0 = lr * 140 - t * 22
    def samp(tx, ku, kv, off, du=0.0):
        return cv2.remap(tx, ((u0 * ku + du) * 512 % 512).astype(np.float32), ((v0 * kv + off) % 512).astype(np.float32),
                         cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    n1 = samp(_tile(seed), 1, 1.0, 0)
    n2 = samp(_tile(seed + 1, 512, 9, 5), 2, 1.7, 40, 0.13 * t)
    n3 = samp(_tile(seed + 2, 512, 17, 4), 4, 2.9, 90, -0.2 * t)
    streak = samp(_tile(seed + 3, 512, 24, 3), 6, 0.35, 0)            # 外圈风带：角向高频、径向低频 → 拉丝
    n = n1 * 0.62 + n2 * 0.28 + n3 * 0.10
    ringw = np.exp(-((r - eye * 1.7) / (eye * 1.1)) ** 2)
    dens = K.sstep(0.36, 0.74, n + 0.10 * ringw)
    dens = np.maximum(dens, K.sstep(0.55, 0.85, streak) * 0.35 * np.clip((r - eye * 2.5) / (eye * 3), 0, 1))
    # 光：来自风眼（向内的法线吃光）
    lx, ly = -dx / r, -dy / r
    gx = cv2.Sobel(dens, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(dens, cv2.CV_32F, 0, 1, ksize=3)
    facing = cv2.GaussianBlur(np.clip(-(gx * lx + gy * ly) * 1.2, 0, 1), (0, 0), 1.2)
    sm = cv2.GaussianBlur(dens, (0, 0), 6)
    M = np.float32([[1, 0, 0], [0, 1, 0]])
    shadow = np.clip(sm - cv2.GaussianBlur(dens, (0, 0), 2), 0, 1)       # 云团内部、背光侧更暗
    falloff = np.exp(-(r / (eye * 7.0)) ** 1.3)
    eyem = np.exp(-(r / eye) ** 2)
    body = dens * (0.30 + 0.55 * falloff) * (1 - 1.6 * shadow)
    rim = facing * dens * (0.35 + 0.9 * falloff + 0.6 * ringw)
    mist = eyem * (0.55 + 0.25 * n2)
    lit_ = np.array(lit, np.float32) * bright
    col = np.array(base, np.float32) * (0.6 + 0.8 * (1 - dens))[..., None] + body[..., None] * lit_ \
        + rim[..., None] * lit_ * 0.85 * np.array([1.0, 1.02, 1.08], np.float32) + mist[..., None] * (lit_ * 0.9 + 0.04)
    if glow is not None:                                                # 云内闪电：一团云从里面亮
        gx_, gy_, ga = glow
        g = np.exp(-(((xx * 2 - gx_) / 420) ** 2 + ((yy * 2 - gy_) / 300) ** 2)) * (0.4 + dens) * ga
        col = col + g[..., None] * np.array([0.75, 0.82, 1.0], np.float32)
    return cv2.resize(np.clip(col, 0, 3).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)


def lightning(fr, t, t_hit, p0, p1, seed=0, life=0.18, amt=1.6, col=(0.85, 0.9, 1.0), branches=4, width=3):
    """闪电（无状态，第二棒重写）：中点位移分形主干 + 渐细分叉；细亮芯 + 两级辉光 + 整屏冷光；life 内两次频闪"""
    age = t - t_hit
    if age < 0 or age > life: return fr
    k = (1 - age / life) ** 0.7 * (0.55 + 0.45 * (int(age * 60) % 2))
    r = np.random.default_rng(seed)
    m = np.zeros((H // 2, W // 2), np.float32)

    def path(a, b, rough=0.22, depth=7):
        P = [np.array(a, float), np.array(b, float)]
        for d in range(depth):
            Q = [P[0]]
            for i in range(len(P) - 1):
                u, v = P[i], P[i + 1]; L = np.linalg.norm(v - u) + 1e-6
                nrm = np.array([-(v - u)[1], (v - u)[0]]) / L
                Q += [(u + v) / 2 + nrm * r.normal(0, rough * L), v]
            P = Q
        return np.array(P)

    def bolt(a, b, w, depth, inten):
        P = path(a, b)
        cv2.polylines(m, [(P / 2).astype(np.int32)], False, inten, max(1, int(w)), cv2.LINE_AA)
        if depth > 0:
            for _ in range(branches if depth > 1 else 2):
                j = r.integers(len(P) // 6, len(P) * 5 // 6); s0 = P[j]
                dirv = (np.array(b) - np.array(a)); dirv = dirv / (np.linalg.norm(dirv) + 1e-6)
                ang = r.uniform(-0.9, 0.9); ca, sa = math.cos(ang), math.sin(ang)
                dv = np.array([dirv[0] * ca - dirv[1] * sa, dirv[0] * sa + dirv[1] * ca])
                e = s0 + dv * np.linalg.norm(np.array(b) - np.array(a)) * r.uniform(0.15, 0.4)
                bolt(s0, e, max(1, w - 1), depth - 1, inten * 0.55)
    bolt(p0, p1, max(1, width - 1), 2, 1.0)
    g = cv2.GaussianBlur(m, (0, 0), 0.7) * 1.8 + cv2.GaussianBlur(m, (0, 0), 5) * 0.9 + cv2.GaussianBlur(m, (0, 0), 24) * 1.4
    return fr * (1 + 0.25 * k * amt) + cv2.resize(g, (W, H))[..., None] * np.array(col, np.float32) * amt * k + 0.06 * k * amt


def embers(fr, t, seed, n=80, area=(0, BAR, W, H - BAR), rise=(40, 140), size=(1.0, 3.2), amt=1.0, col=(1.0, 0.5, 0.15), blur=1.2):
    r = np.random.default_rng(seed)
    x0 = r.uniform(area[0], area[2], n); ph = r.random(n); sp_ = r.uniform(*rise, n); sz = r.uniform(*size, n)
    hgt = area[3] - area[1] + 100
    y = area[3] + 50 - ((t * sp_ + ph * hgt) % hgt)
    x = x0 + 30 * np.sin(t * 1.1 + ph * 20) + 12 * np.sin(t * 3.7 + ph * 7)
    L = np.zeros((H // 2, W // 2), np.float32)
    fl = 0.55 + 0.45 * np.sin(t * 9 + ph * 30)
    for i in range(n):
        cv2.circle(L, (int(x[i] * 2), int(y[i] * 2)), max(1, int(sz[i] * 2)), float(fl[i]), -1, cv2.LINE_AA, 2)
    L = cv2.GaussianBlur(L, (0, 0), blur) * 1.4 + cv2.GaussianBlur(L, (0, 0), 6) * 1.2
    return fr + cv2.resize(L, (W, H))[..., None] * np.array(col, np.float32) * amt


def ash(fr, t, seed, n=90, fall=(30, 90), size=(2, 7), amt=0.5, col=(0.55, 0.53, 0.5), dark=False):
    r = np.random.default_rng(seed)
    x0 = r.uniform(-100, W + 100, n); ph = r.random(n); sp_ = r.uniform(*fall, n); sz = r.uniform(*size, n)
    y = ((t * sp_ + ph * (H + 200)) % (H + 200)) - 100
    x = x0 + 50 * np.sin(t * 0.8 + ph * 13)
    L = np.zeros((H // 2, W // 2), np.float32)
    for i in range(n):
        ang = (t * 90 + ph[i] * 360) % 180
        cv2.ellipse(L, (int(x[i] / 2), int(y[i] / 2)), (max(1, int(sz[i] / 2)), max(1, int(sz[i] / 5))), ang, 0, 360, 1.0, -1, cv2.LINE_AA)
    L = cv2.resize(cv2.GaussianBlur(L, (0, 0), 0.8), (W, H))[..., None]
    if dark: return fr * (1 - L * amt) + np.array(col, np.float32) * L * amt
    return fr * (1 - L * amt) + np.array(col, np.float32) * L * amt


def rays(c, t, seed=0, n=48, spread=1.0, length=1.0):
    """放射光束蒙版（金光从缝中射下 / 爆开）"""
    x, y = K.grid()
    ang = np.arctan2(y - c[1], x - c[0])
    d = np.sqrt((x - c[0]) ** 2 + (y - c[1]) ** 2)
    r = np.random.default_rng(seed)
    a = np.zeros_like(ang)
    for i in range(6):
        f = r.integers(5, n); ph = r.uniform(0, 6.28); sp_ = r.uniform(-0.3, 0.3)
        a += (0.5 + 0.5 * np.sin(ang * f + ph + t * sp_)) ** 6 / 6 * 2
    fall = np.exp(-d / (900 * length))
    return np.clip(a, 0, 1.5) * fall


def godrays(fr, mask, c, amt=0.8, col=GOLD, n=10):
    """径向模糊体积光：把亮区沿中心径向拉长"""
    sm = cv2.resize(mask.astype(np.float32), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    acc = sm.copy()
    cx, cy = c[0] / 4, c[1] / 4
    for i in range(1, n):
        s = 1 + i * 0.06
        M = np.float32([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)]])
        acc += cv2.warpAffine(sm, M, (W // 4, H // 4)) * (1 - i / n)
    acc = cv2.resize(acc / n * 2.2, (W, H))
    return fr + acc[..., None] * np.array(col, np.float32) * amt


def droplets(fr, t, seed, n=160, frozen=True, orbit=0.0, burst=None, gold=0.0, focus=0.55):
    """悬停雨滴（子弹时间）：每滴 = 细长高光 + 暗边；orbit 横向视差；burst=(t0,c) 金色炸开"""
    r = np.random.default_rng(seed)
    x0 = r.uniform(-200, W + 200, n); y0 = r.uniform(BAR - 40, H - BAR + 40, n); z = r.uniform(0.2, 1.0, n)
    L = np.zeros((H // 2, W // 2), np.float32); D = np.zeros_like(L); G = np.zeros_like(L)
    for i in range(n):
        x = x0[i] + orbit * (z[i] - 0.5) * 900; y = y0[i] + (0 if frozen else t * 600 * z[i])
        ln = 6 + 22 * z[i]; wd = 1 + 3 * z[i]
        blur_k = abs(z[i] - focus)
        if burst is not None and t >= burst[0]:
            age = t - burst[0]; c = burst[1]
            v = np.array([x - c[0], y - c[1]]); dd = np.linalg.norm(v) + 1; v /= dd
            x += v[0] * age * (900 + 1200 * z[i]); y += v[1] * age * (900 + 1200 * z[i])
            cv2.line(G, (int(x / 2), int(y / 2)), (int((x - v[0] * 60 * z[i]) / 2), int((y - v[1] * 60 * z[i]) / 2)), float(max(0, 1 - age * 1.4)), max(1, int(wd / 2)), cv2.LINE_AA)
            continue
        a = 0.35 + 0.65 * (1 - min(1, blur_k * 2))
        cv2.ellipse(D, (int(x / 2), int(y / 2)), (max(1, int(wd)), max(1, int(ln / 2))), 0, 0, 360, a * 0.5, -1, cv2.LINE_AA)
        cv2.ellipse(L, (int(x / 2 - wd * 0.3), int(y / 2 - ln * 0.15)), (max(1, int(wd * 0.4)), max(1, int(ln * 0.3))), 0, 0, 360, a, -1, cv2.LINE_AA)
    L = cv2.resize(cv2.GaussianBlur(L, (0, 0), 0.8) + cv2.GaussianBlur(L, (0, 0), 4) * 0.5, (W, H))
    D = cv2.resize(cv2.GaussianBlur(D, (0, 0), 1.2), (W, H))
    out = fr * (1 - D[..., None] * 0.45) + L[..., None] * np.array([0.8, 0.86, 0.95], np.float32) * 0.45
    out = out + L[..., None] * GOLD * gold
    if G.any():
        Gb = cv2.GaussianBlur(G, (0, 0), 1.0) * 1.5 + cv2.GaussianBlur(G, (0, 0), 6) * 1.5
        out = out + cv2.resize(Gb, (W, H))[..., None] * GOLD * 1.3
    return out


# ------------------------------------------------------------------ 收尾
def d_finish(fr, t, ca=0, grain=0.04, vig=0.45, bloom_amt=0.3, bloom_thr=0.75, paper_mode=0.0, red_keep=1.0):
    """K.finish 的 D 组版：paper_mode∈[0,1] 时调色保留纸面暖白（不压成冷灰），辉光阈值随之抬高"""
    fr = np.clip(fr, 0, 4).astype(np.float32)
    r, g, b = fr[..., 0], fr[..., 1], fr[..., 2]
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    sat = np.clip((np.maximum(r, np.maximum(g, b)) - np.minimum(r, np.minimum(g, b))) * 3.0, 0, 1)
    ratio = (r - np.maximum(g, b)) / (r + 1e-3)
    rk = np.clip((ratio - 0.38) / 0.24, 0, 1) * np.clip((r - 0.03) / 0.06, 0, 1)
    sat = np.maximum(sat, rk * red_keep)
    tint = np.array([0.96, 0.99, 1.05], np.float32) * (1 - paper_mode) + np.array([1.02, 1.0, 0.95], np.float32) * paper_mode
    mono = lum[..., None] * tint
    fr = mono * (1 - sat[..., None]) + fr * sat[..., None]
    if bloom_amt > 0: fr = K.bloom(fr, bloom_thr + 0.17 * paper_mode, bloom_amt * (1 - 0.6 * paper_mode), 26)
    if ca:
        ca = int(round(ca)); o = fr.copy(); o[..., 0] = np.roll(fr[..., 0], ca, 1); o[..., 2] = np.roll(fr[..., 2], -ca, 1); fr = o
    fr = fr * K.vignette_mask(vig)
    k = int(t * 30) % 12
    gr = cv2.resize(K._grain(k), (W, H))
    fr = fr + gr[..., None] * grain * (0.35 + 0.65 * (1 - np.clip(fr, 0, 1)) + 0.4 * paper_mode)
    fr = np.where(fr > 0.85, 0.85 + (1 - np.exp(-(fr - 0.85) * 4)) * 0.15, fr)
    fr[:BAR] = 0; fr[H - BAR:] = 0
    return np.clip(fr, 0, 1).astype(np.float32)


# ===================================================================== 第三棒：后半段统一字体系统（宋体大字 + 朱印）与新空间
SONG_WHITE = (0.96, 0.93, 0.86)


def song(fr, items, glow=0.15):
    if LYRIC_UNI and items and max(i[3] for i in items) <= 160: return fr   # [lyric-uni] 只关 ≤160px 的字幕副句；>160px 是画内大字（第47句「判」等），保留等 props 接管
    """后半段歌词：宋体（serif_black，带墨迹毛边）大字砸落。items: (ch, x, y, size, p, color)；
    color: 'w' 暖白 / 'r' 朱红 / 'g' 金 / 'k' 墨。p 为 cp() 落字进度（0→1 时放大回弹 + 去虚焦）。"""
    groups = {}
    for it in items:
        ch, x, y, s, p, c = it
        if p <= 0: continue
        groups.setdefault(c, []).append(it)
    for c, its in groups.items():
        L = T.Layer()
        colr = {'w': SONG_WHITE, 'r': RED, 'g': GOLD, 'k': INK}[c]
        for ch, x, y, s, p, _ in its:
            e = K.eout(p, 3)
            T.place(L, ch, x, y, s, colr, 'serif_black', alpha=min(1, p * 2), scale=1 + 0.45 * (1 - e), blur=7 * (1 - e), texture=False)
        if c == 'r':
            fr = T.compose(fr, L, shadow=0.7, shadow_sigma=30, outline=3, outline_color=(0.03, 0.02, 0.02), glow=0.5 * glow / 0.15,
                           glow_color=(0.9, 0.12, 0.06), glow_sigma=26)
        elif c == 'g':
            fr = T.compose(fr, L, shadow=0.75, shadow_sigma=30, glow=0.55, glow_color=(1.0, 0.55, 0.2), glow_sigma=30)
        elif c == 'k':
            fr = ink_text(fr, L, bleed=0.1, sig=4)
        else:
            fr = T.compose(fr, L, shadow=0.85, shadow_sigma=30, glow=glow, glow_color=(1, 0.93, 0.85), glow_sigma=18)
    return fr


def seal_p(t, t_on, hold=1.4):
    """stamp_seal 进度：落印正好在 V(t_on)"""
    th = V(t_on)
    if t < th - 0.1: return 0.0
    return 0.3 * K.clamp01((t - (th - 0.1)) / 0.1) if t < th else min(1.0, 0.3 + (t - th) / hold)


def night(t, seed, top=(0.035, 0.04, 0.055), bot=(0.012, 0.012, 0.016), glow=None, clouds=0.5, drift=40):
    """非漩涡夜空：纵向渐变 + 横向漂移的层云（不旋转）+ 可选光源晕。glow=(x, y, r, col, amt)"""
    x, y = K.grid()
    v = (y / H)[..., None]
    fr = np.array(top, np.float32) * (1 - v) + np.array(bot, np.float32) * v
    if clouds > 0:
        tx = _tile(seed)
        n = cv2.remap(tx, ((x / 3.2 + t * drift) % 512).astype(np.float32), ((y / 1.6) % 512).astype(np.float32), cv2.INTER_LINEAR)
        n2 = cv2.remap(_tile(seed + 1), ((x / 1.4 + t * drift * 2.2) % 512).astype(np.float32), ((y / 0.9) % 512).astype(np.float32), cv2.INTER_LINEAR)
        c = np.clip((n * 0.65 + n2 * 0.35 - 0.45) * 2.2, 0, 1) * (1 - v[..., 0]) ** 0.8
        fr = fr * (1 + c[..., None] * clouds * 2.2)
    if glow is not None:
        gx, gy, r, col, amt = glow
        g = np.exp(-(((x - gx) ** 2 + (y - gy) ** 2) / (2 * r * r)))
        fr = fr + g[..., None] * np.array(col, np.float32) * amt
    return fr.astype(np.float32)


_SHARDS = {}


def seal_shards(seed=0, n=70):
    """碎印章：若干方朱印（阴文宋体字）被裂成三角碎片 → [(rgba alpha, w)]"""
    if seed in _SHARDS: return _SHARDS[seed]
    r = np.random.default_rng(seed)
    out = []
    chars = '正义规矩理所应当天判忍让大局'
    for k in range(n):
        s = int(r.uniform(150, 260))
        a = T._seal_img(chars[k % len(chars)], s, 'yin', seed * 100 + k)
        pts = r.uniform(0, s, (3, 2)).astype(np.int32)
        pts[0] = (r.uniform(0, s * 0.3), r.uniform(0, s * 0.3)) if k % 2 else pts[0]
        m = np.zeros((s, s), np.float32); cv2.fillConvexPoly(m, pts, 1.0, cv2.LINE_AA)
        if m.sum() < s * s * 0.06: m = np.zeros((s, s), np.float32); cv2.rectangle(m, (0, 0), (s // 2, s // 2), 1.0, -1)
        out.append(a * m)
    _SHARDS[seed] = out
    return out


def shard_rain(fr, t, seed, n=55, speed=(500, 1100), depth=(0.3, 1.3), t0=0.0, burst=None, col=(0.72, 0.06, 0.04), blur_far=2.5):
    """碎印章雨：朱红印章碎片从天坠落、翻转（远小慢糊、近大快），burst=(t_hit, (x,y)) 时从该点炸开"""
    S = seal_shards(seed)
    r = np.random.default_rng(seed + 7)
    items = []
    for k in range(n):
        z = r.uniform(*depth); a = S[k % len(S)]
        x0 = r.uniform(-100, W + 100); ph = r.uniform(0, 1)
        v = r.uniform(*speed) * z
        y = (ph * (H + 400) + (t - t0) * v) % (H + 400) - 200
        x = x0 + math.sin(t * 1.3 + k) * 40 * z
        rot = (r.uniform(-1, 1) * 200 * (t - t0) + r.uniform(0, 360)) % 360
        if burst is not None and t > burst[0]:
            q = t - burst[0]; dx, dy = x - burst[1][0], y - burst[1][1]; d = math.hypot(dx, dy) + 1
            x += dx / d * 900 * q * z; y += dy / d * 900 * q * z
        items.append((z, a, x, y, rot))
    items.sort(key=lambda it: it[0])
    out = fr
    for z, a, x, y, rot in items:
        sc = 0.5 * z
        g = a.shape[0]; d = int(g * sc * 1.5) + 4
        M = cv2.getRotationMatrix2D((g / 2, g / 2), rot, sc); M[:, 2] += (d - g) / 2
        aa = cv2.warpAffine(a, M, (d, d))
        if z < 0.7: aa = cv2.GaussianBlur(aa, (0, 0), blur_far * (0.7 - z) / 0.4 + 0.3)
        sh = 0.45 + 0.55 * min(1, z)          # 远处更暗（大气）
        L = T.Layer(); L.paste(aa, x, y, tuple(np.array(col) * sh), 1.0)
        out = T.compose(out, L, shadow=0.0, glow=0.0)
    return out


# ------------------------------------------------------------------ [r4] 后半段「他的字」：每个「我/来」一种和画面互动的处理
_GLYPH = {}


def glyph_alpha(ch, size, rot=0.0, fname='serif_black'):
    """单字 alpha 局部图（中心对齐，边长 ≈ 1.5 size）"""
    key = (ch, int(size), round(rot, 1), fname)
    if key not in _GLYPH:
        n = int(size * 1.6)
        L = T.Layer(n, n)
        T.place(L, ch, n / 2, n / 2, size, 'white', fname, rot=rot, texture=False)
        _GLYPH[key] = L.A.copy()
    return _GLYPH[key]


def _paste_full(a, cx, cy):
    """局部 alpha 贴到全帧（float32 HxW）"""
    out = np.zeros((H, W), np.float32)
    h, w = a.shape
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xs, ys, xe, ye = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xe > xs and ye > ys: out[ys:ye, xs:xe] = a[ys - y0:ye - y0, xs - x0:xe - x0]
    return out


def shard_glyph(fr, ch, cx, cy, size, p, seed=0, n=7, col=(0.70, 0.71, 0.76), rim=(0.62, 0.74, 1.0), spread=520):
    """字由碎石块拼出：字形切成 n×n 不规则块，从四散（带旋转、虚焦）飞回原位，p=1 拼合；石纹 + 冷轮廓光 + 投影。"""
    G = glyph_alpha(ch, size)
    s = G.shape[0]
    r = np.random.default_rng(seed)
    # 不规则切块：jitter 网格的 Voronoi 标签
    key = ('lab', ch, int(size), seed, n)
    if key not in _GLYPH:
        pts = np.array([((i + 0.5 + r.uniform(-0.35, 0.35)) * s / n, (j + 0.5 + r.uniform(-0.35, 0.35)) * s / n) for i in range(n) for j in range(n)], np.float32)
        yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
        d = (xx[..., None] - pts[:, 0]) ** 2 + (yy[..., None] - pts[:, 1]) ** 2
        lab = d.argmin(-1)
        crack = (cv2.Laplacian(lab.astype(np.float32), cv2.CV_32F) != 0).astype(np.float32)
        _GLYPH[key] = (pts, lab, np.clip(1 - cv2.GaussianBlur(crack, (0, 0), 0.8) * 1.5, 0, 1))
    pts, lab, crk = _GLYPH[key]
    tex = cv2.resize(_tile(seed + 400)[:256, :256], (s, s))
    A = np.zeros((H, W), np.float32)
    for k in range(len(pts)):
        piece = G * (lab == k) * crk
        if piece.sum() < 4: continue
        rr = np.random.default_rng(seed * 997 + k)
        ang = rr.uniform(0, 2 * math.pi); dist = spread * rr.uniform(0.5, 1.2)
        lag = rr.uniform(0, 0.35)
        q = K.eout(K.clamp01((p - lag) / (1 - lag)), 3)
        tx = math.cos(ang) * dist * (1 - q); ty = math.sin(ang) * dist * (1 - q) - 120 * (1 - q)
        rot = rr.uniform(-180, 180) * (1 - q)
        sc = 1 + 0.5 * (1 - q) * rr.uniform(0.3, 1)
        px, py = pts[k]
        M = cv2.getRotationMatrix2D((float(px), float(py)), rot, sc)
        M[0, 2] += cx - s / 2 + tx; M[1, 2] += cy - s / 2 + ty
        A = np.maximum(A, cv2.warpAffine(piece, M, (W, H)) * min(1.0, q * 3 + 0.2))
    if A.max() <= 0: return fr
    T_ = _paste_full(tex, cx, cy) * (A > 0)
    sh = cv2.GaussianBlur(np.roll(A, (14, 10), (0, 1)), (0, 0), 10)
    out = fr * (1 - 0.75 * sh[..., None])
    top = np.clip(A - np.roll(A, 3, 0), 0, 1)            # 上缘受冷光
    body = np.array(col, np.float32) * (0.7 + 0.5 * T_[..., None])
    out = out * (1 - A[..., None]) + body * A[..., None] + top[..., None] * np.array(rim, np.float32) * 1.4
    return out


def light_glyph(fr, ch, cx, cy, size, reveal, rot=0.0, d=(0.8, -0.6), core=(1.0, 0.92, 0.85), glow=(1.0, 0.18, 0.08), fill=0.22):
    """刀光刻字：沿刀光方向 d 依次「刻」出空心发光字（白热描边 + 朱红外发光 + 暗红内填），reveal 0→1。"""
    G = _paste_full(glyph_alpha(ch, size, rot), cx, cy)
    x, y = K.grid()
    dn = np.array(d, np.float32) / np.linalg.norm(d)
    s = (x - cx) * dn[0] + (y - cy) * dn[1]
    lo, hi = -size * 0.75, size * 0.75
    front = lo + (hi - lo) * reveal
    m = K.clamp01(1.0) * np.clip((front - s) / 25, 0, 1)
    Gm = G * m
    edge = np.clip(Gm - cv2.erode(Gm, np.ones((9, 9), np.uint8)), 0, 1)
    out = fr * (1 - Gm[..., None] * 0.55) + Gm[..., None] * np.array(glow, np.float32) * fill
    out = out + cv2.GaussianBlur(edge, (0, 0), 14)[..., None] * np.array(glow, np.float32) * 2.2
    out = out + edge[..., None] * np.array(core, np.float32) * 1.6
    # 刻刀前沿火花线
    fl = np.exp(-((s - front) / 6) ** 2) * cv2.dilate(G, np.ones((15, 15), np.uint8)) * (0 < reveal < 1)
    return out + fl[..., None] * np.array(core, np.float32) * 2.0


def echo_glyph(fr, ch, cx, cy, size, p, n=5, step=(46, -10), col=(1.0, 0.78, 0.40), fade=1.0):
    """定格残影字：主字清晰金色，身后 n 层错位残影（越远越淡越虚、偏暖），fade→0 残影散去。"""
    if p <= 0: return fr
    e = K.eout(p, 3)
    out = fr
    for k in range(n, 0, -1):
        a = 0.5 * (1 - k / (n + 1)) * fade * e
        if a < 0.02: continue
        L = T.Layer()
        T.place(L, ch, cx - step[0] * k * (0.4 + 0.6 * e), cy - step[1] * k * (0.4 + 0.6 * e), size * (1 + 0.04 * k), col, 'serif_black',
                alpha=a, blur=1.5 * k, texture=False)
        out = T.compose(out, L, shadow=0.0, glow=0.25, glow_color=(1.0, 0.5, 0.15), glow_sigma=20)
    L = T.Layer()
    T.place(L, ch, cx, cy, size, col, 'serif_black', alpha=min(1, p * 2), scale=1 + 0.3 * (1 - e), blur=6 * (1 - e), texture=False)
    return T.compose(out, L, shadow=0.8, shadow_sigma=28, outline=2, outline_color=(0.06, 0.03, 0.01), glow=0.45,
                     glow_color=(1.0, 0.55, 0.2), glow_sigma=26)


def crack_glyph(fr, ch, cx, cy, size, p, seed=0, col=(1.0, 0.80, 0.42)):
    """金光从石里裂出字：先沿字形笔画亮起细金缝（不规则阈值推进），随后整字金光爆亮 + 光芒外溢，p 0→1。"""
    G = glyph_alpha(ch, size)
    s = G.shape[0]
    nz = cv2.resize(_tile(seed + 77)[:128, :128], (s, s))
    dist = cv2.distanceTransform((G > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    skel = np.exp(-(dist - dist.max() * 0.5) ** 2 / (2 * (dist.max() * 0.25) ** 2)) * (G > 0.5)
    thr = K.clamp01(p * 1.6)
    seam = skel * np.clip((thr - nz) * 6, 0, 1)
    full = G * K.clamp01((p - 0.55) / 0.3)
    a = np.maximum(seam * 0.9, full)
    A = _paste_full(a, cx, cy)
    out = fr * (1 - _paste_full(G, cx, cy)[..., None] * 0.35 * K.clamp01(p * 3))     # 字位先压暗（刻痕）
    c = np.array(col, np.float32)
    out = out + cv2.GaussianBlur(A, (0, 0), 30)[..., None] * c * 0.55 + cv2.GaussianBlur(A, (0, 0), 6)[..., None] * c * 0.35
    # 深色描边 → 金字在金光里也有边
    ring = np.clip(cv2.dilate(A, np.ones((7, 7), np.uint8)) - A, 0, 1)
    out = out * (1 - ring[..., None] * 0.7)
    hi = np.clip(A - np.roll(A, 4, 0), 0, 1)
    out = out * (1 - A[..., None]) + A[..., None] * (np.array([0.95, 0.62, 0.22], np.float32) * 1.0) + hi[..., None] * 0.6
    return out


def steel_glyph(fr, items, t, sweep_x, col_dark=(0.30, 0.33, 0.38), col_hi=(0.92, 0.95, 1.0)):
    """冷钢字：竖向金属渐变 + 与刀刃同步扫过的高光带 + 刃口亮边 + 投影。items: (ch, x, y, size, p)"""
    L = T.Layer()
    for ch, x, y, s, p in items:
        if p <= 0: continue
        e = K.eout(p, 3)
        T.place(L, ch, x, y, s, 'white', 'serif_black', alpha=min(1, p * 2), scale=1 + 0.35 * (1 - e), blur=6 * (1 - e), texture=False)
    A = L.A
    if A.max() <= 0: return fr
    x, y = K.grid()
    grad = 0.55 + 0.45 * np.cos((y / 160.0) * math.pi) ** 2
    band = np.exp(-(((x + (y - 540) * 0.35) - sweep_x) / 70) ** 2)
    base = np.array(col_dark, np.float32) * (1 - grad[..., None]) + np.array(col_hi, np.float32) * grad[..., None] * 0.75
    rgb = base + band[..., None] * np.array(col_hi, np.float32) * 1.2
    edge = np.clip(A - np.roll(A, 3, 0), 0, 1)
    sh = cv2.GaussianBlur(np.roll(A, (12, 8), (0, 1)), (0, 0), 12)
    out = fr * (1 - 0.8 * sh[..., None])
    out = out * (1 - A[..., None]) + rgb * A[..., None] + edge[..., None] * np.array(col_hi, np.float32) * 0.9
    return out
