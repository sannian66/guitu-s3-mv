"""units/e_kit.py — E 组（副歌终「定」+ 尾奏）场景/字幕/精灵工具。全部纯代码；人物 = assets/gen 精灵。
破晓色板：墨黑 → 暖灰 → 金 → 白；朱红只给血/印/关键字。"""
import math, os, sys
ROOT = '/Users/sannian/Downloads/鬼屠OP_new/out/devsnap/code'
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, cv2
from PIL import Image
import c1kit as K
import typo as T
import rest_sprites as RS
import fx2

W, H, BAR = 1920, 1080, 120
GOLD = np.array([1.0, 0.76, 0.40], np.float32)
GOLDW = np.array([1.0, 0.88, 0.66], np.float32)
RED = np.array([0.80, 0.08, 0.05], np.float32)
REDT = (0.86, 0.10, 0.06)
WHITE_T = (0.98, 0.95, 0.88)
GOLD_T = (1.0, 0.80, 0.45)
INK = np.array([0.02, 0.018, 0.016], np.float32)
for _k, _f in (('serif_r', 'Regular'), ('serif_m', 'Medium'), ('serif_sb', 'SemiBold'), ('serif_b', 'Bold'), ('serif_black', 'Black')):
    T.FONTS[_k] = ROOT + f'/fonts/NotoSerifSC-{_f}.otf'

_G = {}
def grid():
    if 'g' not in _G: _G['g'] = np.mgrid[0:H, 0:W].astype(np.float32)
    return _G['g']


def sstep(a, b, x):
    x = np.clip((x - a) / (b - a), 0, 1); return x * x * (3 - 2 * x)


def c01(x): return float(min(1.0, max(0.0, x)))
def eio(x): x = c01(x); return x * x * (3 - 2 * x)
def eout(x, k=3): x = c01(x); return 1 - (1 - x) ** k
def ein(x, k=3): x = c01(x); return x ** k


# ------------------------------------------------------------------ 天空 / 太阳 / 云 / 山
def dawn_sky(seed=1, horizon=0.72, warm=1.0, cloud=0.7, top=(0.05, 0.045, 0.042), mid=(0.30, 0.21, 0.13), hor=(1.0, 0.76, 0.44),
             sun=None, w=W, h=H):
    """静态天空（预计算）：上墨下金的渐变 + 横向云带（下缘被日光镶金边）。sun=(x,y) 时朝阳方向更亮。"""
    hs, ws = h // 2, w // 2
    y = np.linspace(0, 1, hs, dtype=np.float32)[:, None]
    a = sstep(0.0, horizon, y)
    top, mid, hor = [np.array(c, np.float32) for c in (top, mid, hor)]
    col = top * (1 - a[..., None]) + mid * a[..., None]
    b = sstep(horizon * 0.55, horizon, y)[..., None] ** 1.6
    col = col * (1 - b) + hor * warm * b
    col = np.broadcast_to(col, (hs, ws, 3)).copy()
    if sun is not None:
        yy, xx = np.mgrid[0:hs, 0:ws].astype(np.float32)
        d = np.hypot(xx - sun[0] / 2 * w / W, (yy - sun[1] / 2 * h / H) * 1.6) / ws
        col += (np.exp(-d * 3.5) * 0.55)[..., None] * GOLDW * warm
    if cloud > 0:
        n = K.fbm(hs, ws, seed, base=5, octaves=6)
        n2 = K.fbm(hs, ws, seed + 7, base=14, octaves=4)
        band = np.clip((n * 0.7 + n2 * 0.5 - 0.62) * 3.0, 0, 1)
        stretch = cv2.resize(cv2.resize(band, (ws, hs // 4)), (ws, hs))           # 横向拉长 = 层云
        cmask = stretch * sstep(0.08, 0.45, y) * (1 - sstep(horizon - 0.02, horizon + 0.06, y)) * cloud
        lit = np.clip(stretch - np.roll(stretch, 6, 0), 0, 1)                      # 下缘受光
        cc = col * 0.35 + 0.02
        col = col * (1 - cmask[..., None]) + cc * cmask[..., None] + (lit * cmask * 3.0)[..., None] * hor * warm * 0.9
    return cv2.resize(col, (w, h), interpolation=cv2.INTER_LINEAR)


def sun_disc(fr, c, r, amt=1.0, halo=1.0, core=(1.0, 0.97, 0.88), t=0.0, corona=True):
    """日轮：过曝核心 + 金色光晕（1/4 分辨率算）。"""
    k = 4; hs, ws = H // k, W // k
    yy, xx = np.mgrid[0:hs, 0:ws].astype(np.float32)
    d = np.hypot(xx - c[0] / k, yy - c[1] / k) * k
    disc = np.clip((r - d) / 3.0 + 0.5, 0, 1)
    g1 = np.exp(-np.maximum(d - r, 0) / (r * 0.35 + 8)) * 0.9
    g2 = np.exp(-np.maximum(d - r, 0) / (r * 2.2 + 60)) * 0.45
    L = cv2.resize(disc, (W, H), interpolation=cv2.INTER_LINEAR)
    G = cv2.resize((g1 + g2) * halo, (W, H), interpolation=cv2.INTER_LINEAR)
    fr = fr * (1 - L[..., None]) + L[..., None] * np.array(core, np.float32) * 1.25 * amt
    return fr + G[..., None] * GOLD * amt


def ridges(h=H, w=W, n=4, base=0.70, step=0.055, seed=3, amp=0.10, haze=GOLD, far=0.55, near=0.03):
    """层叠山脊（预计算，返回 (rgb, alpha)）：远山被金雾吃掉，近山墨黑。"""
    out = np.zeros((h, w, 3), np.float32); A = np.zeros((h, w), np.float32)
    for i in range(n):
        k = i / max(1, n - 1)
        rl = K.ridge_line(w, int(h * (base + step * i)), int(h * amp * (0.6 + 0.6 * k)), seed + i * 11, peaks=3 + i)
        m = K.ridge_mask(h, w, rl, 1.5)
        tone = np.asarray(haze, np.float32) * (far * (1 - k) + near * k) + INK * k
        tex = K.fbm(h // 4, w // 4, seed + 50 + i, base=6, octaves=4)
        tex = cv2.resize(tex, (w, h))[..., None]
        col = tone * (0.85 + 0.3 * tex)
        mist = sstep(0.0, 0.10, (np.arange(h, dtype=np.float32)[:, None] / h - (base + step * i)))   # 山脚雾
        col = col * (1 - mist[..., None] * 0.5 * (1 - k)) + np.asarray(haze, np.float32) * mist[..., None] * 0.25 * (1 - k)
        out = out * (1 - m[..., None]) + col * m[..., None]; A = np.maximum(A, m)
    return out, A


def cloud_layer(seed, w, h, density=0.6, soft=1.0):
    """云海单层（预计算，可平铺横移）：返回 (亮度, alpha)。"""
    n = K.fbm(h, w, seed, base=4, octaves=6)
    n2 = K.fbm(h, w, seed + 3, base=12, octaves=4)
    v = n * 0.75 + n2 * 0.35
    yv = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    a = np.clip((v - (0.62 - density * 0.25) + yv * 0.25) * 3.5 / soft, 0, 1)
    top = np.clip(a - np.roll(a, 8, 0), 0, 1)                      # 云顶受光
    lum = 0.25 + 0.5 * v + top * 1.6
    return lum.astype(np.float32), a.astype(np.float32)


def scroll(img, ox, oy=0):
    h, w = img.shape[:2]
    M = np.float32([[1, 0, -ox], [0, 1, -oy]])
    return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_WRAP)


def place_layer(fr, rgb, a, ox=0.0, oy=0.0, z=1.0, center=(W / 2, H / 2)):
    """把一个全幅（或更大）图层按 2.5D 偏移/缩放贴上。"""
    M = np.float32([[z, 0, center[0] * (1 - z) + ox], [0, z, center[1] * (1 - z) + oy]])
    hh, ww = a.shape[:2]
    if (hh, ww) != (H, W):
        M[0, 2] -= (ww - W) / 2 * z; M[1, 2] -= (hh - H) / 2 * z
    R = cv2.warpAffine(rgb, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    A = cv2.warpAffine(a, M, (W, H), borderMode=cv2.BORDER_CONSTANT)
    return fr * (1 - A[..., None]) + R * A[..., None]


def dust_motes(fr, t, seed, n=90, amt=0.6, drift=(30, -18), col=GOLDW, size=(1, 3), blur=1.2, depth=False):
    r = np.random.default_rng(seed); L = np.zeros((H // 2, W // 2), np.float32)
    x0 = r.uniform(0, W, n); y0 = r.uniform(BAR, H - BAR, n); v = r.uniform(0.4, 1.6, n); ph = r.uniform(0, 6.28, n); s = r.uniform(*size, n)
    for i in range(n):
        x = (x0[i] + drift[0] * t * v[i] + 18 * math.sin(t * 0.9 + ph[i])) % W
        y = BAR + (y0[i] - BAR + drift[1] * t * v[i]) % (H - 2 * BAR)
        fl = 0.5 + 0.5 * math.sin(t * 5 + ph[i] * 3)
        cv2.circle(L, (int(x / 2), int(y / 2)), max(1, int(s[i] * (2.5 if depth and i % 5 == 0 else 1) / 2)), float(fl), -1, cv2.LINE_AA)
    L = cv2.resize(cv2.GaussianBlur(L, (0, 0), blur), (W, H))
    return fr + (L + cv2.GaussianBlur(L, (0, 0), 5) * 1.2)[..., None] * amt * np.asarray(col, np.float32)


def flare_streak(fr, p, amt=1.0, length=1.0, angle=0.0, col=GOLDW):
    """镜头横向眩光条 + 小光斑（日光扫过刃口时）。"""
    if amt <= 0.01: return fr
    yy, xx = grid()
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    u = (xx - p[0]) * ca + (yy - p[1]) * sa; v = -(xx - p[0]) * sa + (yy - p[1]) * ca
    st = np.exp(-(v / 5) ** 2) * np.exp(-np.abs(u) / (900 * length)) + np.exp(-(v / 40) ** 2) * np.exp(-np.abs(u) / (300 * length)) * 0.35
    core = np.exp(-(u ** 2 + v ** 2) / (2 * 60 ** 2)) * 1.4
    out = fr + (st + core)[..., None] * amt * np.asarray(col, np.float32)
    for k, (f, rr) in enumerate(((-0.4, 40), (-0.7, 22), (0.35, 70))):            # 光学鬼影
        q = (W / 2 + (p[0] - W / 2) * f, H / 2 + (p[1] - H / 2) * f)
        g = np.exp(-((xx - q[0]) ** 2 + (yy - q[1]) ** 2) / (2 * rr * rr))
        out = out + g[..., None] * 0.18 * amt * np.array([1.0, 0.7, 0.4], np.float32)
    return out


def paper_tex(seed=11, tone=(0.86, 0.80, 0.68)):
    n = K.fbm(H // 2, W // 2, seed, base=40, octaves=4)
    f = K.fbm(H // 2, W // 2, seed + 1, base=160, octaves=2)
    v = 0.88 + 0.10 * n + 0.06 * (f - 0.5)
    return cv2.resize(v, (W, H))[..., None] * np.array(tone, np.float32)


# ------------------------------------------------------------------ 精灵
_ASP = {}
def put(fr, t, key, at, h=None, w=None, anc=(0.5, 1.0), rim=GOLD, rim_amt=2.2, rim_dir=(0.3, -1.0), grade=None, wind=6.0,
        look=None, alpha=1.0, mblur=(0, 0), defocus=0.0, rot=0.0):
    """精灵摆放（包围盒锚点 anc → 屏幕 at；h/w 包围盒高/宽像素）。返回 (fr, info)。"""
    if key not in _ASP:
        _w, _h = Image.open(RS._prep(key)).size; _ASP[key] = _w / _h
    tgt = h if h else w
    scr_w = tgt * _ASP[key] if h else tgt
    sp = RS.layer(key, scr_w * 1.1)
    x0, y0, x1, y1 = sp.bbox
    s = tgt / ((y1 - y0) * sp.h) if h else tgt / ((x1 - x0) * sp.w)
    a_src = (x0 + anc[0] * (x1 - x0), y0 + anc[1] * (y1 - y0))
    g = dict(grade or G_DAWN)
    fr, Aw = sp.draw(fr, t, a_src, at, s, rot=rot, rim=dict(col=tuple(rim), amt=rim_amt, dir=rim_dir), grade=g, wind_amp=wind,
                     shade=None, wrap=0.45, mblur=mblur, alpha=alpha, defocus=defocus, look=look)
    def to_scr(p):
        X = (p[0] - a_src[0]) * sp.w * s; Y = (p[1] - a_src[1]) * sp.h * s
        c, si = math.cos(math.radians(-rot)), math.sin(math.radians(-rot))
        return (at[0] + X * c - Y * si, at[1] + X * si + Y * c)
    return fr, dict(A=Aw, to_scr=to_scr, tip=to_scr(sp.tip) if sp.tip else None, top=to_scr(sp.top),
                    box=(to_scr((x0, y0)), to_scr((x1, y1))))


G_DAWN = dict(expo=0.86, sat=0.62, tint=(1.05, 0.98, 0.90), lift=0.0, gamma=1.10)
G_HOT = dict(expo=0.95, sat=0.6, tint=(1.08, 0.97, 0.86), lift=0.01, gamma=1.05)
G_SIL = dict(expo=0.30, sat=0.4, tint=(1.0, 0.95, 0.9), lift=0.0, gamma=1.3)


# ------------------------------------------------------------------ 字：E 组「金火」排版
#  入场「火线烧出」：每字在字头前 0.22s 起，噪声火线自下而上烧出字形（火线金白发光），字头视觉帧落定；
#  出场「灰飞」：字从边缘碳化变暗，碎成余烬上飘（0.3s）。主字 Black、整句 SemiBold、署名 Regular。
IN_D, OUT_D = 0.22, 0.30
_NZ = {}
def _nz(g, seed):
    k = (g, seed % 97)
    if k not in _NZ:
        r = np.random.default_rng(seed % 97)
        a = cv2.resize(r.random((max(2, g // 10), max(2, g // 10))).astype(np.float32), (g, g), interpolation=cv2.INTER_CUBIC)
        b = cv2.resize(r.random((max(2, g // 3), max(2, g // 3))).astype(np.float32), (g, g), interpolation=cv2.INTER_CUBIC)
        _NZ[k] = np.clip(a * 0.7 + b * 0.3, 0, 1)
    return _NZ[k]


def burn_glyph(ch, font, size, e, q=0.0, seed=0, direction=(0.25, -1.0)):
    """返回 (alpha, ember) 方形图：e 烧出进度 0..1；q 灰飞进度 0..1。"""
    a = T.glyph(ch, font, size, False)
    g = a.shape[0]
    if e >= 1 and q <= 0: return a, None
    yy, xx = np.mgrid[0:g, 0:g].astype(np.float32) / g
    dv = np.array(direction, np.float32); dv /= np.linalg.norm(dv)
    F = ((xx - 0.5) * dv[0] + (yy - 0.5) * dv[1]) / (abs(dv[0]) + abs(dv[1])) + 0.5
    F = F * 0.7 + _nz(g, seed + ord(ch)) * 0.3
    em = None
    if e < 1 and size < 120:   # 第五棒：小字（副句/署名）不走火线烧出 —— 半烧中间态会截出半个偏旁像乱码；改为末 3 帧整字由虚到实淡入
        k = c01((e - 0.55) / 0.45)
        b = cv2.GaussianBlur(a, (0, 0), 0.5 + 4.0 * (1 - k))
        a = b * k
        e = 1.0
    if e < 1:
        fr_ = e * 1.25 - 0.1
        m = np.clip((fr_ - F) / 0.05, 0, 1)
        band = np.exp(-((F - fr_) / 0.035) ** 2)
        em = cv2.GaussianBlur(a, (0, 0), 1.0) * band
        a = a * m
    if q > 0:
        G = _nz(g, seed + ord(ch) + 31)
        thr = q * 1.15
        a = a * np.clip((G - thr) * 6 + 0.5, 0, 1)
        e2 = cv2.GaussianBlur(a, (0, 0), 1.0) * np.exp(-((G - thr) / 0.06) ** 2) * (1 - q)
        em = e2 if em is None else em + e2
    return a, em


class Lyr:
    """一句字：chars [(ch, x, y, size, font, color, t_in)]，t_out 起灰飞（按序 0.03s）。"""
    def __init__(self, chars, t_out, seed=0, glow=0.35, shadow=0.7, direction=(0.25, -1.0)):
        self.c = chars; self.t_out = t_out; self.seed = seed; self.glow = glow; self.shadow = shadow; self.dir = direction
        for (ch, x, y, s, f, col, ti) in chars: T.glyph(ch, f, s, False)

    def draw(self, fr, t, alpha=1.0, dx=0.0, dy=0.0):
        L = T.Layer(); E = T.Layer(); any_ = False
        for i, (ch, x, y, s, f, col, ti) in enumerate(self.c):
            e = (t - (ti - IN_D)) / IN_D
            if e <= 0: continue
            q = (t - (self.t_out + 0.03 * i)) / OUT_D if self.t_out is not None else 0
            if q >= 1: continue
            a, em = burn_glyph(ch, f, s, min(1.0, e), max(0.0, q), self.seed + i, self.dir)
            lift = -14 * max(0.0, q)
            L.paste(a, x + dx, y + dy + lift, col, alpha); any_ = True
            if em is not None: E.paste(np.clip(em * 1.5, 0, 1), x + dx, y + dy + lift, (1.0, 0.85, 0.55), alpha)
        if not any_: return fr
        fr = T.compose(fr, L, shadow=self.shadow, shadow_sigma=20, glow=self.glow, glow_sigma=16)
        bx = E.box(30)
        if bx:
            x0, y0, x1, y1 = bx
            A = E.A[y0:y1, x0:x1]
            fr[y0:y1, x0:x1] += (A * 1.6 + cv2.GaussianBlur(A, (0, 0), 6) * 1.4)[..., None] * np.array([1.0, 0.72, 0.38], np.float32)
        return fr


def row(text, times, cx, cy, size=62, font='serif_sb', red='', gold='', track=0.2, vertical=False, base=WHITE_T, sizes=None):
    """横排/竖排一行 → Lyr chars。times 与 text 中非空格字一一对应。"""
    out = []; k = 0
    chars = [c for c in text]
    szs = sizes or [size] * len(chars)
    adv = [s * (1 + track) for s in szs]
    tot = sum(adv) - adv[-1] * track / (1 + track)
    p = (cy if vertical else cx) - tot / 2
    for i, c in enumerate(chars):
        s = szs[i]; mid = p + s / 2
        if c != ' ':
            col = REDT if c in red else (GOLD_T if c in gold else base)
            out.append((c, cx if vertical else mid, mid if vertical else cy, s, font if s < 200 else 'serif_black', col, times[k])); k += 1
        p += adv[i]
    return out
