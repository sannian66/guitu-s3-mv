"""c1kit.py — 副歌一摄制组的程序化素材与镜头工具（只供 units/chorus1.py 使用）。
全部 numpy / OpenCV 生成：夜空、月、山、砖墙、刀身、宣纸、雾、雨、火星、草叶、墨爆、调色收尾。
粒子全部“无状态”（位置是 t 的解析函数），分段并行渲染结果一致。"""
import sys, math, os
from functools import lru_cache
ROOT = '/workspace/work/mv'
for p in (ROOT, ROOT + '/lib'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, cv2
import proc

W, H, BAR = 1920, 1080, 120
RED = np.array([0.72, 0.06, 0.05], np.float32)
GOLD = np.array([1.0, 0.76, 0.40], np.float32)
STEEL = np.array([0.80, 0.86, 0.95], np.float32)
MOONC = np.array([0.93, 0.93, 0.90], np.float32)


def clamp01(x): return float(min(1.0, max(0.0, x)))
def eio(x): x = clamp01(x); return x * x * (3 - 2 * x)
def eout(x, k=3): x = clamp01(x); return 1 - (1 - x) ** k
def ein(x, k=3): x = clamp01(x); return x ** k
def sstep(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-9), 0, 1); return t * t * (3 - 2 * t)
def pulse(t, t0, decay=0.12):
    return 0.0 if t < t0 else math.exp(-(t - t0) / decay)
def win(t, a, b, fi=0.1, fo=0.1):
    if t < a or t > b: return 0.0
    return min(1.0, (t - a) / max(1e-6, fi), (b - t) / max(1e-6, fo))


@lru_cache(None)
def beats():
    return np.load(ROOT + '/analysis.npz')['beats'].astype(np.float64)


@lru_cache(None)
def grid(h=H, w=W):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32); return x, y


def fbm(h, w, seed, base=4, octaves=6, persist=0.55):
    return proc.fbm2(h, w, seed, base, octaves, persist)


@lru_cache(None)
def tile(n=1024, seed=0, base=6, octaves=5):
    rig = sys.modules.get('rig') or __import__('rig')
    return rig.noise_tex(n, seed, base, octaves)


def tile_crop(tex, x0, y0, h, w):
    n = tex.shape[0]
    ys = (np.arange(h) + int(y0)) % n; xs = (np.arange(w) + int(x0)) % n
    return tex[np.ix_(ys, xs)]


# ------------------------------------------------------------------ 镜头
def cam(fr, z=1.0, ox=0.0, oy=0.0, rot=0.0, center=None, border=cv2.BORDER_REFLECT):
    """以 center（默认画面中心）为锚点缩放 z、旋转 rot（度），再平移视点 (ox,oy)（正值=镜头向右/下看）。"""
    if abs(z - 1) < 1e-4 and abs(ox) < 0.05 and abs(oy) < 0.05 and abs(rot) < 1e-3: return fr
    c = center or (W / 2, H / 2)
    M = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), rot, z)
    M[0, 2] -= ox * z; M[1, 2] -= oy * z
    return cv2.warpAffine(fr, M, (fr.shape[1], fr.shape[0]), flags=cv2.INTER_LINEAR, borderMode=border)


def perlin1(x, seed=0):
    x = float(x); i0 = math.floor(x); f = x - i0
    def g(i):
        h = (i * 374761393 + seed * 668265263) & 0xffffffff
        h = (h ^ (h >> 13)) * 1274126177 & 0xffffffff
        return ((h & 0xffff) / 32767.5) - 1.0
    u = f * f * f * (f * (f * 6 - 15) + 10)
    return (g(i0) * f * (1 - u) + g(i0 + 1) * (f - 1) * u) * 2.0


def shake(t, amp, freq=9.0, seed=0):
    """手持/冲击抖动 (dx,dy,rot)"""
    if amp <= 0: return 0.0, 0.0, 0.0
    return (perlin1(t * freq, seed) * amp + perlin1(t * freq * 3.1, seed + 9) * amp * 0.3,
            perlin1(t * freq * 0.93, seed + 3) * amp * 0.8 + perlin1(t * freq * 2.7, seed + 5) * amp * 0.25,
            perlin1(t * freq * 0.6, seed + 7) * amp * 0.03)


def motion_blur(fr, dx, dy, scale=4):
    L = math.hypot(dx, dy) / scale
    if L < 1: return fr
    h, w = fr.shape[:2]
    sm = cv2.resize(fr, (w // scale, h // scale), interpolation=cv2.INTER_AREA)
    k = int(L) * 2 + 1
    ker = np.zeros((k, k), np.float32)
    c = k // 2; ux, uy = dx / math.hypot(dx, dy), dy / math.hypot(dx, dy)
    for i in range(k):
        s = (i - c)
        x = int(round(c + ux * s)); y = int(round(c + uy * s))
        ker[y, x] = 1
    ker /= ker.sum()
    b = cv2.filter2D(sm, -1, ker, borderType=cv2.BORDER_REFLECT)
    big = cv2.resize(b, (w, h), interpolation=cv2.INTER_LINEAR)
    m = min(1.0, L / 4)
    return fr * (1 - m) + big * m


def radial_blur(fr, c, amt, n=6, scale=2):
    if amt < 0.004: return fr
    h, w = fr.shape[:2]
    sm = cv2.resize(fr, (w // scale, h // scale), interpolation=cv2.INTER_AREA)
    acc = sm.copy(); cc = (c[0] / scale, c[1] / scale)
    for k in range(1, n):
        s = 1 + amt * k / n
        M = cv2.getRotationMatrix2D(cc, 0, s)
        acc += cv2.warpAffine(sm, M, (sm.shape[1], sm.shape[0]), borderMode=cv2.BORDER_REFLECT)
    acc /= n
    return cv2.resize(acc, (w, h))


def blur_ds(a, sig, k=4):
    h, w = a.shape[:2]
    s = cv2.resize(a, (max(1, w // k), max(1, h // k)), interpolation=cv2.INTER_AREA)
    s = cv2.GaussianBlur(s, (0, 0), max(0.5, sig / k))
    return cv2.resize(s, (w, h), interpolation=cv2.INTER_LINEAR)


def bloom(fr, thr=0.7, amt=0.6, sigma=24):
    hi = np.clip(fr - thr, 0, None)
    return fr + blur_ds(hi, sigma) * amt + blur_ds(hi, sigma * 0.3, 2) * amt * 0.5


def over(fr, a, col):
    """alpha 合成：a (H,W) 或 (H,W,1)，col RGB 或图像"""
    if a.ndim == 2: a = a[..., None]
    return fr * (1 - a) + np.asarray(col, np.float32) * a


# ------------------------------------------------------------------ 天空 / 月 / 山
@lru_cache(None)
def sky(w=W, h=H, seed=1, horizon=0.75, cloud=0.6, top=(0.018, 0.021, 0.03), bot=(0.11, 0.12, 0.14), stars=1.0):
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    g = np.clip(y / horizon, 0, 1) ** 1.6
    base = np.array(top, np.float32) * (1 - g) + np.array(bot, np.float32) * g
    base = np.broadcast_to(base, (h, w, 3)).copy()
    n = fbm(h, w, seed, base=3, octaves=7)
    n2 = fbm(h, w, seed + 5, base=12, octaves=4)
    cl = np.clip((n * 0.75 + n2 * 0.25 - 0.48) * 3.2, 0, 1) * cloud
    cl = cl * (1 - np.clip((y[..., 0] - horizon) * 4, 0, 1))
    base = base * (1 - cl[..., None] * 0.55) + cl[..., None] * np.array([0.13, 0.14, 0.16], np.float32) * (0.4 + n2[..., None])
    if stars > 0:
        r = np.random.default_rng(seed + 9)
        k = int(w * h / 9000 * stars)
        sx = r.integers(0, w, k); sy = (r.random(k) ** 1.5 * h * horizon * 0.9).astype(int)
        st = np.zeros((h, w), np.float32)
        st[sy, sx] = r.uniform(0.15, 0.7, k) * (1 - cl[sy, sx])
        st = cv2.GaussianBlur(st, (0, 0), 0.7) * 3
        base += st[..., None] * np.array([0.85, 0.9, 1.0], np.float32)
    return base.astype(np.float32)


@lru_cache(None)
def moon_sprite(r, seed=4, phase=0.0):
    """返回 (rgb, alpha) 大小 (2r*3) 含光晕。phase>0 为残缺（阴影从右侧）"""
    s = int(r * 3) * 2; c = s / 2
    x, y = np.meshgrid(np.arange(s, dtype=np.float32) - c, np.arange(s, dtype=np.float32) - c)
    d = np.sqrt(x * x + y * y)
    disc = np.clip((r - d) / 1.5 + 0.5, 0, 1)
    tex = fbm(s, s, seed, base=5, octaves=6)
    mare = np.clip((fbm(s, s, seed + 1, base=3, octaves=4) - 0.5) * 3, 0, 1)
    lum = 0.95 - 0.16 * mare - 0.06 * tex
    limb = np.clip(1 - (d / r) ** 4 * 0.25, 0, 1)
    lum = lum * limb
    if phase > 0:
        sh = np.clip(((x - r * (1 - 2 * phase)) ** 2 + y * y) ** 0.5 / r - 1, 0, 1)
        disc = disc * np.clip(sh * 8, 0, 1)
    rgb = np.stack([lum * 0.95, lum * 0.95, lum * 0.92], -1)
    halo = (1 / (1 + (d / r) ** 2 * 1.2)) * 0.55 + np.exp(-((d - r) / (r * 0.08)) ** 2) * 0.15
    halo = halo * (1 - disc) * np.clip((c - d) / (r * 1.2), 0, 1) ** 2      # 光晕在精灵边缘前衰减到 0（v1 有方框台阶）
    A = np.clip(disc + halo, 0, 1)
    col = (rgb * disc[..., None] + np.array([0.75, 0.80, 0.9], np.float32) * halo[..., None]) / np.maximum(A, 1e-4)[..., None]
    return col.astype(np.float32), A.astype(np.float32)


def paste_sprite(fr, rgb, A, cx, cy, scale=1.0, alpha=1.0, add=False):
    if scale != 1.0:
        s = max(2, int(A.shape[0] * scale))
        rgb = cv2.resize(rgb, (s, s), interpolation=cv2.INTER_LINEAR); A = cv2.resize(A, (s, s), interpolation=cv2.INTER_LINEAR)
    h, w = A.shape
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xs, ys, xe, ye = max(0, x0), max(0, y0), min(fr.shape[1], x0 + w), min(fr.shape[0], y0 + h)
    if xe <= xs or ye <= ys: return fr
    a = A[ys - y0:ye - y0, xs - x0:xe - x0, None] * alpha
    c = rgb[ys - y0:ye - y0, xs - x0:xe - x0]
    if add: fr[ys:ye, xs:xe] += c * a
    else: fr[ys:ye, xs:xe] = fr[ys:ye, xs:xe] * (1 - a) + c * a
    return fr


@lru_cache(None)
def mountains(w, h, base_y, amp, seed, peaks=3):
    return proc.mountain_layer(w, h, base_y, amp, seed, peaks=peaks)


@lru_cache(None)
def ridge_line(w, base_y, amp, seed, peaks=3):
    r = proc.fbm1(w, seed, base=peaks, octaves=8)
    r = (r - r.min()) / (r.max() - r.min() + 1e-6)
    return (base_y - r * amp).astype(np.float32)


def ridge_mask(h, w, ridge, soft=1.5):
    y = np.arange(h, dtype=np.float32)[:, None]
    return np.clip((y - ridge[None]) / soft + 0.5, 0, 1)


# ------------------------------------------------------------------ 砖墙
@lru_cache(None)
def brick_wall(w=2400, h=1600, bw=150, bh=64, mortar=7, seed=9, tone=(0.16, 0.30)):
    """返回 (rgb, seam)：带倒角、风化、崩角的青砖墙（月光左上）。"""
    r = np.random.default_rng(seed)
    x, y = grid(h, w)
    row = (y // bh).astype(np.int32)
    off = (row % 2) * (bw // 2) + (row * 37 % 23)
    col_ = ((x + off) // bw).astype(np.int32)
    lx = (x + off) % bw; ly = y % bh
    ids = (row * 1009 + col_ * 31) % 4096
    lut = r.uniform(*tone, 4096).astype(np.float32)
    lut2 = r.uniform(-1, 1, 4096).astype(np.float32)
    t = lut[ids]
    n1 = fbm(h, w, seed, base=24, octaves=5); n2 = fbm(h, w, seed + 1, base=90, octaves=3)
    ed = np.minimum(np.minimum(lx, bw - lx), np.minimum(ly, bh - ly))
    chip = fbm(h, w, seed + 2, base=60, octaves=3)
    edge = np.clip((ed - mortar * 0.5 - (chip - 0.5) * 10) / 4.0, 0, 1)
    seam = 1 - edge
    bevel = np.clip(1 - np.minimum(ly, lx) / 7.0, 0, 1) * 0.10 - np.clip(1 - np.minimum(bh - ly, bw - lx) / 7.0, 0, 1) * 0.08
    lum = t * (0.75 + 0.5 * n1) * (0.85 + 0.3 * n2) + bevel * edge + lut2[ids] * 0.015
    lum = lum * edge + 0.035 * (1 - edge)
    # 大尺度风化/水渍
    stain = fbm(h, w, seed + 3, base=3, octaves=4)
    lum = lum * (0.7 + 0.5 * stain)
    rgb = np.stack([lum * 0.97, lum * 0.99, lum * 1.04], -1).astype(np.float32)
    return rgb, seam.astype(np.float32)


def warp_quad(src, quad, out_shape=(H, W), border=cv2.BORDER_CONSTANT):
    h, w = src.shape[:2]
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), np.float32(quad))
    return cv2.warpPerspective(src, M, (out_shape[1], out_shape[0]), flags=cv2.INTER_LINEAR, borderMode=border)


def crack_path(p0, p1, seed, n=40, jag=0.04):
    r = np.random.default_rng(seed)
    p0 = np.array(p0, float); p1 = np.array(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); nn = np.array([-d[1], d[0]]) / (L + 1e-9)
    u = np.linspace(0, 1, n)
    off = np.cumsum(r.normal(0, 1, n)); off -= np.linspace(off[0], off[-1], n)
    off = off / (np.abs(off).max() + 1e-6) * L * jag + r.normal(0, L * jag * 0.15, n)
    off[0] = off[-1] = 0
    return p0[None] + u[:, None] * d[None] + off[:, None] * nn[None]


def draw_crack(shape, pts, width, branches=6, seed=0, prog=1.0):
    """裂缝 alpha（带分叉）"""
    m = np.zeros(shape, np.float32)
    n = max(2, int(len(pts) * clamp01(prog)))
    P = (pts[:n] * 4).astype(np.int32)
    for i in range(n - 1):
        wv = max(1, int(width * (0.6 + 0.4 * math.sin(i * 0.7)) * 4))
        cv2.line(m, tuple(P[i]), tuple(P[i + 1]), 1.0, max(1, wv // 4), cv2.LINE_AA, 2)
    r = np.random.default_rng(seed)
    for b in range(branches):
        k = int(r.uniform(0.1, 0.9) * (n - 1))
        if k < 1: continue
        a = pts[k]; ang = r.uniform(0, 2 * math.pi); L = r.uniform(20, 90) * width / 3
        q = crack_path(a, a + [math.cos(ang) * L, math.sin(ang) * L], seed + b, n=8, jag=0.15)
        Q = (q * 4).astype(np.int32)
        for i in range(len(Q) - 1):
            cv2.line(m, tuple(Q[i]), tuple(Q[i + 1]), 0.8, 1, cv2.LINE_AA, 2)
    return m


# ------------------------------------------------------------------ 刀身（大特写）
@lru_cache(None)
def blade_strip(L=2600, Wd=300, seed=5):
    """水平刀身贴图 (Wd, L)：上=刀背(暗)、镐线、刃纹(hamon)、下=刃口(亮)。返回 rgb, alpha, hamon_mask"""
    r = np.random.default_rng(seed)
    x, y = grid(Wd, L)
    v = y / Wd                        # 0 背 → 1 刃
    tipx = L * 0.92
    # 刀尖收窄（右端）
    edge_y = np.where(x > tipx, 1 - ((x - tipx) / (L - tipx)) ** 1.6 * 0.95, 1.0)
    inside = (v < edge_y).astype(np.float32) * (v > 0.0)
    inside = cv2.GaussianBlur(inside, (0, 0), 0.8)
    brushed = cv2.resize(r.random((Wd, L // 30)).astype(np.float32), (L, Wd), interpolation=cv2.INTER_LINEAR)
    brushed = cv2.GaussianBlur(brushed, (0, 0), 0.6)
    base = 0.22 + 0.10 * brushed
    shin = 0.34
    base = np.where(v < shin, base * 0.55, base)                          # 镐地更暗
    base += np.exp(-((v - shin) / 0.012) ** 2) * 0.55                    # 镐线高光
    ham_c = 0.70 + 0.05 * np.sin(x / 55 + 1.3) + 0.03 * np.sin(x / 17) + 0.015 * (fbm(1, L, seed, base=40, octaves=3)[0][None] - 0.5) * 4
    ham = sstep(ham_c - 0.03, ham_c + 0.05, v)
    nie = fbm(Wd, L, seed + 2, base=60, octaves=3)
    base = base + ham * (0.30 + 0.15 * nie)                               # 刃文白雾
    base += np.exp(-((v - (edge_y - 0.025)) / 0.018) ** 2) * 0.7          # 刃口亮线
    base += np.exp(-((v - 0.02) / 0.02) ** 2) * 0.25                      # 刀背棱
    rgb = np.stack([base * 0.92, base * 0.96, base * 1.04], -1).astype(np.float32)
    return rgb, inside.astype(np.float32), (ham * inside).astype(np.float32)


def draw_blade(fr, p0, p1, width, shine=0.5, shine_w=0.08, heat=0.0, alpha=1.0, return_mask=False, seed=5):
    """把刀身贴图从 p0(护手侧) 到 p1(刀尖) 画进帧；shine=高光带沿刀身位置(0..1)。"""
    rgb, A, ham = blade_strip(seed=seed)
    Lb, Wd = A.shape[1], A.shape[0]
    p0 = np.array(p0, np.float32); p1 = np.array(p1, np.float32)
    d = p1 - p0; L = float(np.linalg.norm(d)); u = d / L; n = np.array([-u[1], u[0]], np.float32)
    src = np.float32([[0, 0], [Lb, 0], [0, Wd]])
    dst = np.float32([p0 - n * width / 2, p1 - n * width / 2, p0 + n * width / 2])
    M = cv2.getAffineTransform(src, dst)
    h, w = fr.shape[:2]
    pts = np.array([dst[0], dst[1], dst[1] + n * width, dst[2]])
    x0, y0 = np.clip(np.floor(pts.min(0)).astype(int) - 2, 0, [w, h]); x1, y1 = np.clip(np.ceil(pts.max(0)).astype(int) + 2, 0, [w, h])
    if x1 <= x0 or y1 <= y0: return (fr, np.zeros((h, w), np.float32)) if return_mask else fr
    M2 = M.copy(); M2[:, 2] -= [x0, y0]
    ww, hh = x1 - x0, y1 - y0
    a = cv2.warpAffine(A, M2, (ww, hh)) * alpha
    c = cv2.warpAffine(rgb, M2, (ww, hh))
    # 高光带
    xx, yy = np.meshgrid(np.arange(x0, x1, dtype=np.float32), np.arange(y0, y1, dtype=np.float32))
    s = ((xx - p0[0]) * u[0] + (yy - p0[1]) * u[1]) / L
    band = np.exp(-((s - shine) / shine_w) ** 2)
    c = c + band[..., None] * np.array([0.9, 0.93, 1.0], np.float32) * 0.9
    if heat > 0:
        hm = np.clip(heat * (0.6 + 0.6 * s), 0, 1.5)[..., None]
        c = c * (1 - 0.5 * np.clip(hm, 0, 1)) + (RED * 1.4 + GOLD * 0.25) * hm * 0.8
    sub = fr[y0:y1, x0:x1]
    fr[y0:y1, x0:x1] = sub * (1 - a[..., None]) + c * a[..., None]
    if return_mask:
        m = np.zeros((h, w), np.float32); m[y0:y1, x0:x1] = a
        return fr, m
    return fr


# ------------------------------------------------------------------ 纸
@lru_cache(None)
def paper_light(seed=11):
    p = proc.paper(H, W, seed)
    f = fbm(H, W, seed + 4, base=80, octaves=3)
    return np.clip(p * (0.94 + 0.08 * f[..., None]), 0, 1).astype(np.float32)


@lru_cache(None)
def paper_dark(seed=12):
    """墨染深色宣纸（漆黑带纤维与云纹）"""
    n = fbm(H, W, seed, base=4, octaves=7)
    fib = cv2.GaussianBlur(np.random.default_rng(seed).random((H, W)).astype(np.float32), (0, 0), 0.8)
    streak = cv2.resize(np.random.default_rng(seed + 1).random((H // 3, 60)).astype(np.float32), (W, H))
    l = 0.055 + 0.05 * n + 0.02 * fib + 0.012 * streak
    return np.stack([l * 1.02, l, l * 0.98], -1).astype(np.float32)


# ------------------------------------------------------------------ 雾 / 雨 / 火星 / 草
def fog(fr, t, seed, amt=0.25, speed=(30, 0), scale=4, y0=0.5, y1=1.0, color=(0.55, 0.58, 0.64), tex_n=512):
    T = tile(tex_n, seed, scale, 5)
    sm = tile_crop(T, t * speed[0] / 4, t * speed[1] / 4, H // 4, W // 4)
    g = np.linspace(0, 1, H // 4, dtype=np.float32)[:, None]
    band = sstep(y0 - 0.15, y0 + 0.1, g) * (1 - sstep(y1, y1 + 0.15, g))
    a = np.clip((sm - 0.35) * 1.6, 0, 1) * band * amt
    a = cv2.resize(a, (W, H))
    return over(fr, a, color)


def rain(fr, t, seed=3, n=500, speed=2100, angle=8.0, length=(30, 80), amt=0.35, near=0.3, region=None):
    """无状态雨丝：两层（远细、近粗虚）。"""
    r = np.random.default_rng(seed)
    x0 = r.uniform(-200, W + 200, n); y0 = r.uniform(0, H, n); sp = r.uniform(0.7, 1.3, n) * speed
    ln = r.uniform(*length, n); depth = r.random(n)
    th = math.radians(angle); dx, dy = math.sin(th), math.cos(th)
    y = (y0 + sp * t) % (H + 200) - 100; x = x0 + (y - y0) * dx / dy
    L = np.zeros((H // 2, W // 2), np.float32); Ln = np.zeros_like(L)
    for i in range(n):
        a = (x[i] / 2, y[i] / 2); b = ((x[i] - dx * ln[i]) / 2, (y[i] - dy * ln[i]) / 2)
        if depth[i] < near:
            cv2.line(Ln, (int(a[0]), int(a[1])), (int(b[0] * 1.0), int(b[1] - ln[i] * 0.5)), 0.5, 2, cv2.LINE_AA)
        else:
            cv2.line(L, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), 0.28 + 0.3 * depth[i], 1, cv2.LINE_AA)
    Ln = cv2.GaussianBlur(Ln, (0, 0), 2.0)
    m = cv2.resize(L + Ln, (W, H))
    if region is not None: m = m * region
    return fr + m[..., None] * amt * np.array([0.78, 0.83, 0.92], np.float32)


def sparks(fr, t, seed, origin, n=60, life=0.9, speed=(300, 900), dirc=(0, -1), spread=0.9, grav=500, size=1.0,
           amt=1.0, t0=None, burst=False, color=(1.0, 0.55, 0.18), area=(0, 0)):
    """无状态火星。burst=True：全部在 t0 迸发；否则按 life 周期循环发射。"""
    r = np.random.default_rng(seed)
    ph = r.random(n); sp = r.uniform(*speed, n)
    base = math.atan2(dirc[1], dirc[0]); ang = base + r.normal(0, spread, n)
    ox = origin[0] + r.uniform(-1, 1, n) * area[0]; oy = origin[1] + r.uniform(-1, 1, n) * area[1]
    lf = life * r.uniform(0.5, 1.2, n)
    if burst:
        age = np.full(n, t - (t0 or 0.0)); alive = (age >= 0) & (age < lf)
    else:
        age = ((t / lf + ph) % 1.0) * lf; alive = np.ones(n, bool)
    if not alive.any(): return fr
    vx = np.cos(ang) * sp; vy = np.sin(ang) * sp
    px = ox + vx * age; py = oy + vy * age + 0.5 * grav * age * age
    qx = px - (vx) * 0.025; qy = py - (vy + grav * age) * 0.025
    L = np.zeros((H // 2, W // 2), np.float32)
    k = 1 - age / lf
    for i in np.nonzero(alive)[0]:
        if not (-50 < px[i] < W + 50 and -50 < py[i] < H + 50): continue
        cv2.line(L, (int(px[i] * 4), int(py[i] * 4)), (int(qx[i] * 4), int(qy[i] * 4)), float(k[i]), max(1, int(size)), cv2.LINE_AA, 3)
    Lb = cv2.GaussianBlur(L, (0, 0), 2.5) * 2.0 + L * 1.5
    return fr + cv2.resize(Lb, (W, H))[..., None] * np.array(color, np.float32) * amt


def dust(fr, t, seed, n=120, amt=0.5, drift=(20, -10), size=(1, 3), region=(0, BAR, W, H - BAR), color=(0.8, 0.8, 0.85), blur=1.0):
    r = np.random.default_rng(seed)
    x0 = r.uniform(region[0], region[2], n); y0 = r.uniform(region[1], region[3], n)
    sz = r.uniform(*size, n); ph = r.random(n) * 6.28
    x = (x0 + drift[0] * t + 8 * np.sin(t * 0.7 + ph) - region[0]) % (region[2] - region[0]) + region[0]
    y = (y0 + drift[1] * t + 6 * np.cos(t * 0.9 + ph) - region[1]) % (region[3] - region[1]) + region[1]
    L = np.zeros((H // 2, W // 2), np.float32)
    for i in range(n):
        cv2.circle(L, (int(x[i] * 2), int(y[i] * 2)), max(1, int(sz[i])), 0.5 + 0.5 * math.sin(t * 2 + ph[i]), -1, cv2.LINE_AA, 2)
    L = cv2.GaussianBlur(L, (0, 0), blur)
    return fr + cv2.resize(L, (W, H))[..., None] * np.array(color, np.float32) * amt


class Grass:
    """前景草叶剪影（虚焦），随风摆。"""
    def __init__(self, seed, n=90, y_base=980, height=(120, 380), x_range=(-100, W + 100), width=(4, 12)):
        r = np.random.default_rng(seed)
        self.x = r.uniform(*x_range, n); self.h = r.uniform(*height, n); self.w = r.uniform(*width, n)
        self.lean = r.normal(0.25, 0.25, n); self.ph = r.random(n) * 6.28; self.yb = y_base + r.uniform(-30, 40, n)
    def mask(self, t, wind=1.0, dx=0.0, dy=0.0, blur=6):
        L = np.zeros((H // 2, W // 2), np.float32)
        for i in range(len(self.x)):
            sway = self.lean[i] + wind * (0.18 * math.sin(t * 2.1 + self.ph[i]) + 0.08 * math.sin(t * 5.3 + self.ph[i] * 2))
            k = 8; pts_l = []; pts_r = []
            for j in range(k + 1):
                s = j / k; bend = sway * s * s * self.h[i]
                cx = self.x[i] + dx + bend; cy = self.yb[i] + dy - s * self.h[i] * (1 - 0.15 * abs(sway) * s)
                ww = self.w[i] * (1 - s) + 0.5
                pts_l.append((cx - ww, cy)); pts_r.append((cx + ww, cy))
            poly = np.array(pts_l + pts_r[::-1]) / 2
            cv2.fillPoly(L, [(poly * 4).astype(np.int32)], 1.0, cv2.LINE_AA, 2)
        if blur > 0: L = cv2.GaussianBlur(L, (0, 0), blur / 2)
        return cv2.resize(L, (W, H))


# ------------------------------------------------------------------ 墨爆 / 冲击
def ink_blot(p, seed=0, center=(W / 2, H / 2), reverse=False):
    """墨爆蒙版 0..1：p 0→1 墨从 center 炸开吞没全画面（reverse=True 则墨退）。"""
    if reverse: p = 1 - p
    x, y = grid()
    n = tile(512, seed + 30, 5, 5)
    nn = cv2.resize(tile_crop(n, 0, 0, H // 4, W // 4), (W, H))
    d = np.sqrt(((x - center[0]) / W) ** 2 + ((y - center[1]) / W) ** 2)
    R = eout(p, 2) * 1.35
    f = R - d - (nn - 0.5) * 0.35
    m = np.clip(f * 30, 0, 1)
    # 飞溅墨点
    r = np.random.default_rng(seed)
    sp = np.zeros((H // 2, W // 2), np.float32)
    if 0 < p < 0.9:
        for i in range(40):
            ang = r.uniform(0, 6.28); dd = r.uniform(0.2, 1.3) * W * (0.3 + eout(p, 2))
            rr = r.uniform(3, 18) * (1 + p)
            cv2.circle(sp, (int((center[0] + math.cos(ang) * dd) / 2), int((center[1] + math.sin(ang) * dd) / 2)), int(rr / 2), 1.0, -1, cv2.LINE_AA)
        m = np.maximum(m, cv2.resize(sp, (W, H)))
    return m


def vignette_mask(strength=0.55):
    return _vig(round(strength, 3))


@lru_cache(None)
def _vig(strength):
    x, y = grid()
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H * 0.42)) ** 2)
    v = np.clip(1 - (d - 0.5) * 0.85, 0, 1) ** 1.5
    return (1 - strength + strength * v)[..., None].astype(np.float32)


@lru_cache(None)
def _grain(k):
    r = np.random.default_rng(1000 + k)
    return cv2.GaussianBlur(r.standard_normal((H // 2, W // 2)).astype(np.float32), (0, 0), 0.7)


def finish(fr, t, ca=0, grain=0.04, vig=0.5, bloom_amt=0.35, grade=True, red_keep=0.0):
    """统一调色收尾：冷灰底 + 保留朱/金、辉光、色差、暗角、颗粒、上下黑边。"""
    fr = np.clip(fr, 0, 4)
    if grade:
        r, g, b = fr[..., 0], fr[..., 1], fr[..., 2]
        lum = 0.3 * r + 0.59 * g + 0.11 * b
        sat = np.clip((np.maximum(r, np.maximum(g, b)) - np.minimum(r, np.minimum(g, b))) * 3.0, 0, 1)
        if red_keep:   # SPRITE_MODE：暗红按色相比例保色（暗红内领/红穗/血），不被冷灰去饱和吃掉
            ratio = (r - np.maximum(g, b)) / (r + 1e-3)
            rk = np.clip((ratio - 0.38) / 0.24, 0, 1) * np.clip((r - 0.03) / 0.06, 0, 1)
            sat = np.maximum(sat, rk * red_keep)
        mono = np.stack([lum * 0.96, lum * 0.99, lum * 1.05], -1)
        fr = mono * (1 - sat[..., None]) + fr * sat[..., None]
    if bloom_amt > 0: fr = bloom(fr, 0.72, bloom_amt, 26)
    if ca:
        ca = int(round(ca))
        o = fr.copy(); o[..., 0] = np.roll(fr[..., 0], ca, 1); o[..., 2] = np.roll(fr[..., 2], -ca, 1); fr = o
    fr = fr * vignette_mask(vig)
    k = int(t * 30) % 12
    g = cv2.resize(_grain(k), (W, H))
    fr = fr + g[..., None] * grain * (0.35 + 0.65 * (1 - np.clip(fr, 0, 1)))
    # 高光柔肩
    fr = np.where(fr > 0.85, 0.85 + (1 - np.exp(-(fr - 0.85) * 4)) * 0.15 / 1.0, fr)
    fr[:BAR] = 0; fr[H - BAR:] = 0
    return np.clip(fr, 0, 1).astype(np.float32)


def to8(fr):
    return (np.clip(fr, 0, 1) * 255 + 0.5).astype(np.uint8)
