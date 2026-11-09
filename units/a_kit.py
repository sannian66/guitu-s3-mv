"""units/a_kit.py — A 组（前奏 + 主歌一）工具：差值抠像、精灵摆放、背景元件、歌词版式（马善政楷逐笔竖排）。
只被 units/sec_a_intro_verse1.py 使用。"""
import math, os, hashlib, json
import numpy as np, cv2
from PIL import Image
ROOT = '/workspace/work/mv'
import sys
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
import sprite as SP
import c1kit as K
import fx2
import typo as T

W, H, BAR = 1920, 1080, 120
COLD = (0.62, 0.74, 1.0); GOLD = (1.0, 0.78, 0.45); REDR = (1.0, 0.32, 0.22); WARM = (1.0, 0.85, 0.62)
RED = np.array([0.72, 0.06, 0.05], np.float32)
G_COLD = dict(expo=0.80, sat=0.55, tint=(0.90, 0.96, 1.06), lift=0.0, gamma=1.12)
CACHE = '/tmp/a_spr'
GEN = ROOT + '/assets/gen/'


def clamp01(x): return float(min(1.0, max(0.0, x)))
def eio(x): x = clamp01(x); return x * x * (3 - 2 * x)
def eout(x, k=3): x = clamp01(x); return 1 - (1 - x) ** k
def ein(x, k=3): x = clamp01(x); return x ** k


# ------------------------------------------------------------------ 差值抠像（纯灰底已知背景色）：保留刀钢/发丝，去灰边
def diff_matte(key, lo=0.035, hi=0.13, work=2560, keep_cut=True, crop=None):
    """assets/gen/<key>_raw.png → RGBA PNG（缓存）。alpha = 与背景灰的色差（角落采样）∪ 原抠图腐蚀；颜色反预乘去灰溢。"""
    os.makedirs(CACHE, exist_ok=True)
    out = CACHE + '/dm_' + hashlib.md5(f'{key}{lo}{hi}{work}{keep_cut}{crop}'.encode()).hexdigest()[:12] + '.png'
    if os.path.exists(out): return out
    im = Image.open(GEN + key + '_raw.png').convert('RGB')
    im = im.resize((work, round(work * im.size[1] / im.size[0])), Image.LANCZOS)
    F = np.asarray(im).astype(np.float32) / 255
    h, w = F.shape[:2]
    # 背景色场：四边带采样后低频插值（灰底常有轻微渐变）
    m = 24
    pts = np.concatenate([F[:m].reshape(-1, 3), F[-m:].reshape(-1, 3), F[:, :m].reshape(-1, 3), F[:, -m:].reshape(-1, 3)])
    lum = pts.mean(1); med = np.median(lum); sel = np.abs(lum - med) < 0.06
    g = pts[sel].mean(0)
    sm = cv2.resize(F, (64, 36), interpolation=cv2.INTER_AREA)
    bgfield = cv2.resize(cv2.GaussianBlur(sm, (0, 0), 6), (w, h))
    near = np.linalg.norm(bgfield - g, axis=-1, keepdims=True) < 0.05
    B = np.where(near, bgfield, g)
    d = np.sqrt(((F - B) ** 2).sum(-1))
    A = np.clip((d - lo) / (hi - lo), 0, 1)
    if keep_cut and os.path.exists(GEN + key + '_cut.png'):
        c = np.asarray(Image.open(GEN + key + '_cut.png').convert('RGBA').resize((w, h))).astype(np.float32)[..., 3] / 255
        c = cv2.erode(c, np.ones((9, 9), np.uint8))
        A = np.maximum(A, c)
    # 小孔填充（内部偶然接近灰的像素）：闭运算后只在内部生效
    Ac = cv2.morphologyEx(A, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    inner = cv2.erode((A > 0.5).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(np.float32)
    A = np.maximum(A, Ac * cv2.GaussianBlur(inner, (0, 0), 3))
    A = cv2.GaussianBlur(A, (0, 0), 0.7)
    Fu = np.clip((F - B * (1 - A[..., None])) / np.maximum(A[..., None], 0.08), 0, 1)
    if crop:
        x0, y0, x1, y1 = crop; X0, Y0, X1, Y1 = int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)
        r = np.ones((h, w), np.float32); f = int(0.03 * w)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        if X0 > 0: r *= np.clip((xx - X0) / f, 0, 1)
        if X1 < w: r *= np.clip((X1 - xx) / f, 0, 1)
        if Y0 > 0: r *= np.clip((yy - Y0) / f, 0, 1)
        if Y1 < h: r *= np.clip((Y1 - yy) / f, 0, 1)
        A = A * r
    rgba = np.concatenate([Fu, A[..., None]], -1)
    Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA').save(out)
    return out


_LRU = {}
def sprite(path, work_w=1600):
    k = (path, work_w)
    if k in _LRU:
        v = _LRU.pop(k); _LRU[k] = v; return v
    sp = SP.SpriteLayer(path, work_w=work_w)
    _LRU[k] = sp
    while len(_LRU) > 6: _LRU.pop(next(iter(_LRU)))
    return sp


def src(key, mode='cut', **kw):
    """精灵源文件路径：mode 'cut' 原抠图 / 'dm' 差值抠像（raw 灰底）"""
    if mode == 'dm': return diff_matte(key, **kw)
    return GEN + key + '_cut.png'


def place(fr, t, path, at, h=None, w=None, anc=(0.5, 1.0), rim=COLD, rim_amt=1.8, rim_dir=(0.0, -1.0), grade=None,
          wind=6.0, mblur=(0, 0), alpha=1.0, defocus=0.0, look=None, rot=0.0, flip=False, work=None, wrap=0.4, breathe=0.004):
    """按 alpha 包围盒摆放：anc = 包围盒内归一化锚点 → 屏幕 at；h 或 w 指包围盒在屏幕上的高/宽(px)。返回 fr, info。"""
    tgt_w = w if w else None
    sp0 = sprite(path, 640)
    x0, y0, x1, y1 = sp0.bbox
    asp = (x1 - x0) * sp0.w / max(1e-6, (y1 - y0) * sp0.h)
    scr_w = (h * asp) if h else w
    ww = int(min(2560, max(512, round(scr_w * 1.1 / (x1 - x0) / 64) * 64)))
    sp = sprite(path, work or ww)
    if flip:
        sp = _flipped(path, work or ww)
    x0, y0, x1, y1 = sp.bbox
    s = h / ((y1 - y0) * sp.h) if h else w / ((x1 - x0) * sp.w)
    a_src = (x0 + anc[0] * (x1 - x0), y0 + anc[1] * (y1 - y0))
    g = dict(G_COLD); g.update(grade or {})
    fr, Aw = sp.draw(fr, t, a_src, at, s, rot=rot, rim=dict(col=rim, amt=rim_amt, dir=rim_dir), grade=g, wind_amp=wind, shade=None,
                     wrap=wrap, mblur=mblur, alpha=alpha, defocus=defocus, look=look, breathe=breathe)
    def to_scr(p):
        return (at[0] + (p[0] - a_src[0]) * sp.w * s, at[1] + (p[1] - a_src[1]) * sp.h * s)
    return fr, dict(A=Aw, to_scr=to_scr, box=(to_scr((x0, y0)), to_scr((x1, y1))))


_FL = {}
def _flipped(path, ww):
    k = (path, ww)
    if k not in _FL:
        out = CACHE + '/fl_' + hashlib.md5(path.encode()).hexdigest()[:12] + '.png'
        if not os.path.exists(out):
            os.makedirs(CACHE, exist_ok=True)
            Image.open(path).transpose(Image.FLIP_LEFT_RIGHT).save(out)
        _FL[k] = SP.SpriteLayer(out, work_w=ww)
    return _FL[k]


# ------------------------------------------------------------------ 背景元件
def vgrad(top, bot, y0=0, y1=H, gamma=1.0):
    y = np.clip((np.arange(H, dtype=np.float32) - y0) / max(1, y1 - y0), 0, 1)[:, None, None] ** gamma
    g = np.array(top, np.float32) * (1 - y) + np.array(bot, np.float32) * y
    return np.broadcast_to(g, (H, W, 3)).astype(np.float32).copy()


def glow(fr, c, r, amt, col, aspect=1.0):
    q = 4
    yy, xx = np.mgrid[0:H // q, 0:W // q].astype(np.float32)
    g = np.exp(-(((xx * q - c[0]) / aspect) ** 2 + (yy * q - c[1]) ** 2) / (2 * r * r))
    return fr + cv2.resize(g, (W, H))[..., None] * amt * np.array(col, np.float32)


_TEX = {}
def tex(seed, n=512, base=4, octaves=6):
    k = (seed, n, base, octaves)
    if k not in _TEX: _TEX[k] = fx2.noise(n, seed, base=base, octaves=octaves)
    return _TEX[k]


def clouds(fr, t, seed=1, speed=(20, 0), y0=120, y1=700, amt=0.6, col=(0.20, 0.22, 0.27), dark=0.5, scale=1.0, thr=0.42, light=None,
           light_col=(0.9, 0.9, 1.0), light_r=500, cam=(0, 0)):
    """云层（两层视差 fbm）：暗部压暗、受光边（light=(x,y) 月/光源附近云边提亮）。"""
    out = fr
    for li, (sp, s, a) in enumerate(((1.0, 1.0, 1.0), (1.7, 0.6, 0.7))):
        n = fx2.scroll(tex(seed + li, 512, 3, 6), -t * speed[0] * sp - cam[0] * sp * 0.3, -t * speed[1] * sp - cam[1] * 0.3, H // 4, W // 4,
                       scale=scale * s)
        n = cv2.resize(n, (W, H))
        m = np.clip((n - thr) * 3.0, 0, 1)
        yy = np.arange(H, dtype=np.float32)[:, None]
        band = np.clip((yy - y0) / 80, 0, 1) * np.clip((y1 - yy) / 160, 0, 1)
        m = m * band * amt * a
        c = np.array(col, np.float32)
        lit = 0.0
        if light is not None:
            q = np.exp(-(((np.arange(W, dtype=np.float32)[None] - light[0]) ** 2) + (yy - light[1]) ** 2) / (2 * light_r ** 2))
            edge = np.clip(m - cv2.GaussianBlur(m, (0, 0), 6), 0, 1) * 4
            lit = (q * (edge + 0.35 * m))[..., None] * np.array(light_col, np.float32)
        out = out * (1 - m[..., None] * dark) + m[..., None] * c * (0.6 + 0.5 * n[..., None]) + lit
    return out


_MOON = {}
def moon(fr, cx, cy, r, amt=1.0, col=(1.0, 1.0, 1.0), phase=0.0, halo=0.5, bright=0.78):
    """月亮（第二棒：压亮度 + 月海对比，避免过曝成白盘；bright 为盘面峰值亮度）"""
    k = (int(r), phase)
    if k not in _MOON:
        rgb, A_ = K.moon_sprite(int(r), 4, phase)
        disc = np.clip(A_ * 1.0, 0, 1)
        lum = rgb.mean(-1, keepdims=True)
        inner = (lum > 0.6).astype(np.float32)     # 盘面像素（光晕是 0.75 左右蓝灰，盘面 ≥0.75 的亮白）
        rgb2 = np.where(rgb.min(-1, keepdims=True) > 0.62, (rgb / 0.95) ** 2.6, rgb * 0.8)
        _MOON[k] = (rgb2.astype(np.float32), A_)
        if len(_MOON) > 8: _MOON.pop(next(iter(_MOON)))
    rgb, A = _MOON[k]
    fr = K.paste_sprite(fr, rgb * np.array(col, np.float32) * bright, A, cx, cy, alpha=amt)
    # 光晕只在盘外（盘内叠加会把月海冲成白盘）
    q = 4
    yy, xx = np.mgrid[0:H // q, 0:W // q].astype(np.float32)
    d = np.hypot(xx * q - cx, yy * q - cy)
    g = np.exp(-d * d / (2 * (r * 2.4) ** 2)) * np.clip((d - r * 0.80) / (r * 0.22), 0, 1)
    return fr + cv2.resize(g, (W, H))[..., None] * halo * amt * 0.8 * np.array((0.55, 0.62, 0.78), np.float32)


def ridge(fr, base_y, amp, seed, tone=(0.03, 0.035, 0.045), rim=None, rim_amt=0.6, peaks=3, dx=0.0, fogcol=None, fog=0.0, w_extra=400):
    rl = K.ridge_line(W + w_extra, int(base_y), int(amp), seed, peaks)
    o = int(w_extra / 2 + dx) % w_extra if w_extra else 0
    rl = rl[o:o + W]
    m = K.ridge_mask(H, W, rl, soft=1.2)
    c = np.array(tone, np.float32)
    if fogcol is not None and fog > 0:
        yy = np.arange(H, dtype=np.float32)[:, None]
        f = np.clip(1 - (yy - rl[None]) / 260, 0, 1) * fog
        cc = c[None, None] * (1 - f[..., None]) + np.array(fogcol, np.float32) * f[..., None]
    else:
        cc = c
    fr = fr * (1 - m[..., None]) + cc * m[..., None]
    if rim is not None:
        e = np.exp(-np.clip(np.arange(H, dtype=np.float32)[:, None] - rl[None], 0, None) / 2.5) * (np.arange(H)[:, None] >= rl[None] - 1)
        fr = fr + e[..., None] * np.array(rim, np.float32) * rim_amt
    return fr, rl


def ink_noise(seed, n=256):
    return tex(seed, n, 6, 5)


def grade_contrast(fr, k=1.15, pivot=0.18):
    return np.clip(pivot + (fr - pivot) * k, 0, 8)


def letterbox_safe(y):
    return min(max(y, BAR + 40), H - BAR - 40)


# ------------------------------------------------------------------ 歌词：主歌一体系 = 马善政楷 逐笔竖排（brush_write），关键字朱红
LYR_F = 'kai'
LYR_WHITE = (0.96, 0.93, 0.87)
LYR_RED = (0.86, 0.12, 0.08)
LYR_GOLD = (1.0, 0.80, 0.46)


def col_places(text, x, y0, size, gap=1.08):
    P = []
    y = y0
    for i, c in enumerate(text):
        P.append(dict(ch=c, x=x, y=y + size / 2, size=size, font=LYR_F, idx=i, rot=0.0))
        y += size * gap
    return P


def brush_column(fr, text, prog, x, y0, size=84, red='', gold='', out=0.0, seed=0, alpha=1.0, glow_amt=0.25):
    """逐笔竖排：prog 每字 0..1；out 0..1 墨散退场（自上而下）。"""
    P = col_places(text, x, y0, size)
    L = T.Layer()
    n = len(P)
    for i, (p, pc) in enumerate(zip(P, prog)):
        if pc <= 0: continue
        if p['ch'] in T.PUNCT or p['ch'] == ' ': continue
        A = T.brush_glyph(p['ch'], LYR_F, size, min(1.0, pc), seed + i, 0.8, splatter=True)
        q = clamp01((out * (n + 3) - i) / 3.0)
        if q > 0:
            g = A.shape[0]
            nz = cv2.resize(ink_noise(ord(p['ch']) + i, 64)[:g // 8 + 2, :g // 8 + 2], (g, g))
            A = A * np.clip((nz - q * 1.1) * 6 + 0.5, 0, 1)
            A = cv2.GaussianBlur(A, (0, 0), 0.5 + 3 * q)
        c = LYR_RED if p['ch'] in red else (LYR_GOLD if p['ch'] in gold else LYR_WHITE)
        L.paste(A, p['x'], p['y'] - 14 * q, c, alpha)
    return T.compose(fr, L, shadow=0.75, shadow_sigma=22, glow=glow_amt, glow_sigma=16)


def defringe(key, erode=5, work=2560):
    """第二棒：recut 抠图灰边处理 → 收 alpha + 边缘色用内部颜色外推（去灰底溢色）。返回缓存 PNG 路径。"""
    os.makedirs(CACHE, exist_ok=True)
    out = CACHE + '/df_' + hashlib.md5(f'{key}{erode}{work}'.encode()).hexdigest()[:12] + '.png'
    if os.path.exists(out): return out
    im = Image.open(GEN + key + '_cut.png').convert('RGBA')
    im = im.resize((work, round(work * im.size[1] / im.size[0])), Image.LANCZOS)
    F = np.asarray(im).astype(np.float32) / 255
    rgb, A = F[..., :3], F[..., 3]
    Ae = cv2.erode(A, np.ones((erode, erode), np.uint8))
    Ae = cv2.GaussianBlur(Ae, (0, 0), 1.2)
    inner = (cv2.erode(A, np.ones((erode + 6, erode + 6), np.uint8)) > 0.98).astype(np.float32)
    num = cv2.GaussianBlur(rgb * inner[..., None], (0, 0), 6); den = cv2.GaussianBlur(inner, (0, 0), 6)[..., None]
    ext = num / np.maximum(den, 1e-4)
    w = np.clip((0.98 - A) / 0.5, 0, 1)[..., None] * (den > 0.02)
    rgb = rgb * (1 - w) + np.minimum(rgb, ext) * w
    Image.fromarray((np.concatenate([rgb, Ae[..., None]], -1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(out)
    return out


def bg_matte(key, lo=0.05, hi=0.14, work=2560):
    """第二棒：背景有暗角/渐变的灰底 → 遮住主体后 inpaint 估出背景场，再做色差抠像（救回 recut 丢掉的手、飞刀）。"""
    os.makedirs(CACHE, exist_ok=True)
    out = CACHE + '/bm4_' + hashlib.md5(f'{key}{lo}{hi}{work}'.encode()).hexdigest()[:12] + '.png'
    if os.path.exists(out): return out
    im = Image.open(GEN + key + '_raw.png').convert('RGB')
    im = im.resize((work, round(work * im.size[1] / im.size[0])), Image.LANCZOS)
    F = np.asarray(im).astype(np.float32) / 255
    h, w = F.shape[:2]
    q = 8; sm = cv2.resize(F, (w // q, h // q), interpolation=cv2.INTER_AREA)
    # 粗主体：与局部中值差异大 / 很暗 / 有饱和度
    med = cv2.medianBlur((sm * 255).astype(np.uint8), 31).astype(np.float32) / 255
    d0 = np.abs(sm - med).max(-1)
    m = ((d0 > 0.05) | (sm.max(-1) - sm.min(-1) > 0.08)).astype(np.uint8)
    m = cv2.dilate(m, np.ones((9, 9), np.uint8))
    bg = cv2.inpaint((sm * 255).astype(np.uint8), m * 255, 9, cv2.INPAINT_TELEA).astype(np.float32) / 255
    bg = cv2.GaussianBlur(bg, (0, 0), 4)
    B = cv2.resize(bg, (w, h), interpolation=cv2.INTER_CUBIC)
    d = np.sqrt(((F - B) ** 2).sum(-1))
    A = np.clip((d - lo) / (hi - lo), 0, 1)
    A = cv2.morphologyEx(A, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    if os.path.exists(GEN + key + '_cut.png'):                      # 并上 recut 主体（填身体内部近灰的洞）
        c = np.asarray(Image.open(GEN + key + '_cut.png').convert('RGBA').resize((w, h))).astype(np.float32)[..., 3] / 255
        A = np.maximum(A, cv2.erode(c, np.ones((5, 5), np.uint8)) * np.clip((d - 0.012) / 0.02, 0, 1))
    inner = cv2.erode((A > 0.5).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(np.float32)
    Ac = cv2.morphologyEx(A, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    A = np.maximum(A, Ac * cv2.GaussianBlur(inner, (0, 0), 3))
    # 小洞填实（与外界不连通、面积 < 0.4% 的透明区）
    bm = (A < 0.5).astype(np.uint8)
    n, lab, stt, _ = cv2.connectedComponentsWithStats(bm, 4)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    small = [i for i in range(1, n) if i not in border and stt[i, cv2.CC_STAT_AREA] < 0.004 * h * w]
    if small:
        A = np.where(np.isin(lab, small), 1.0, A).astype(np.float32)
    A = cv2.GaussianBlur(A, (0, 0), 0.8)
    Fu = np.clip((F - B * (1 - A[..., None])) / np.maximum(A[..., None], 0.08), 0, 1)
    Image.fromarray((np.concatenate([Fu, A[..., None]], -1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(out)
    return out
