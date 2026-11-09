"""units/e_r7.py — E 组第七棒辅助：宣纸折痕/接缝/纤维、三层烧洞边、笔画自燃字、金属刀身着色。"""
import math
import numpy as np, cv2
import c1kit as K
import typo as T
from e_kit import W, H, c01

_C = {}


def _grid():
    if 'g' not in _C:
        _C['g'] = np.mgrid[0:H, 0:W].astype(np.float32)
    return _C['g']


def paper_creases(seed=717, n=26):
    """宣纸叠皱：随机长折痕（一侧亮一侧暗的脊）+ 细纤维 + 大块起伏。返回 mul (H,W)，均值≈1。右上光。"""
    key = ('cr', seed)
    if key in _C: return _C[key]
    h2, w2 = H // 2, W // 2
    r = np.random.default_rng(seed)
    hgt = np.zeros((h2, w2), np.float32)
    for k in range(n):
        x0, y0 = r.uniform(-100, w2 + 100), r.uniform(-100, h2 + 100)
        a = r.uniform(0, math.pi); L = r.uniform(180, 700)
        pts = []
        for s in np.linspace(-0.5, 0.5, 7):
            pts.append((x0 + math.cos(a) * L * s + r.uniform(-8, 8), y0 + math.sin(a) * L * s + r.uniform(-8, 8)))
        m = np.zeros((h2, w2), np.float32)
        cv2.polylines(m, [np.array(pts, np.int32)], False, float(r.uniform(0.5, 1.0)), int(r.integers(1, 3)), cv2.LINE_AA)
        hgt += cv2.GaussianBlur(m, (0, 0), r.uniform(1.5, 4.0)) * r.choice([-1, 1])
    hgt += 0.6 * (K.fbm(h2, w2, seed + 3, base=9, octaves=4).astype(np.float32) - 0.5)
    gy, gx = np.gradient(hgt)
    shade = (gx * 0.7 - gy * 0.7) * 6.0                                 # 右上光：折痕一侧亮一侧暗
    fib = K.fbm(h2, w2 * 6, seed + 4, base=60, octaves=2).astype(np.float32)
    fib = cv2.resize(fib, (w2, h2))
    mul = 1.0 + np.clip(shade, -0.45, 0.45) + 0.10 * (fib - 0.5)
    # 纸纤维：短亮丝
    F = np.zeros((h2, w2), np.float32)
    for k in range(900):
        x, y = r.uniform(0, w2), r.uniform(0, h2); a = r.uniform(0, math.pi); l = r.uniform(4, 18)
        cv2.line(F, (int(x), int(y)), (int(x + math.cos(a) * l), int(y + math.sin(a) * l)), float(r.uniform(0.3, 1)), 1, cv2.LINE_AA)
    mul = mul + 0.07 * cv2.GaussianBlur(F, (0, 0), 0.5)
    mul = cv2.resize(mul.astype(np.float32), (W, H))
    _C[key] = mul
    return mul


def paper_seams(segs, seed=718):
    """糊纸接缝：每条 = 一条斜折线；线一侧多一层纸（略亮略暖），线上一条压暗的纸边阴影 + 一条亮的纸口 + 毛边纤维。
    segs = [((x0,y0),(x1,y1)), ...]。返回 (mul, add)。"""
    key = ('sm', seed, tuple(segs))
    if key in _C: return _C[key]
    r = np.random.default_rng(seed)
    yy, xx = _grid()
    mul = np.ones((H, W), np.float32); add = np.zeros((H, W, 3), np.float32)
    for (x0, y0), (x1, y1) in segs:
        dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy); nx, ny = -dy / L, dx / L
        wob = 0
        # 毛边：沿线方向参数 s 的随机抖动
        s = ((xx - x0) * dx + (yy - y0) * dy) / L
        jit = 3.0 * np.sin(s / 23.0 + 1.3) + 2.0 * np.sin(s / 7.1) + 1.2 * np.sin(s / 2.7 + 0.5)
        d = (xx - x0) * nx + (yy - y0) * ny + jit
        over = np.clip(d / 2.0 + 0.5, 0, 1)                                 # 叠层一侧
        mul *= 1 + 0.07 * over
        mul *= 1 - 0.38 * np.exp(-((d + 4) / 3.0) ** 2)                     # 纸边投下的细阴影
        add += (0.07 * np.exp(-((d - 1.5) / 1.6) ** 2))[..., None] * np.array([1.0, 0.9, 0.75], np.float32)   # 纸口亮线
        add += (0.025 * over * np.exp(-np.clip(d, 0, None) / 40))[..., None] * np.array([1.0, 0.85, 0.6], np.float32)
    _C[key] = (mul, add)
    return mul, add


def hole_noise(seed=719):
    """烧洞边缘的各频段噪声（全帧，[-0.5,0.5]）：lo 大轮廓、mid 锯齿、hi 纤维毛边、brk 火线断续。"""
    key = ('hn', seed)
    if key in _C: return _C[key]
    r = np.random.default_rng(seed)
    lo = cv2.resize(r.random((5, 9)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC) - 0.5
    mid = cv2.resize(r.random((34, 60)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC) - 0.5
    hi = r.random((H, W)).astype(np.float32)
    hi = cv2.GaussianBlur(hi, (0, 0), 1.1)
    hi = (hi - hi.mean()) / (hi.std() * 4 + 1e-6)
    hair = np.zeros((H, W), np.float32)                                 # 纸纤维毛边：短丝向外
    for k in range(5000):
        x, y = r.uniform(0, W), r.uniform(0, H); a = r.uniform(0, math.pi); l = r.uniform(5, 22)
        cv2.line(hair, (int(x), int(y)), (int(x + math.cos(a) * l), int(y + math.sin(a) * l)), 1.0, 1, cv2.LINE_AA)
    brk = K.fbm(H // 4, W // 4, seed + 9, base=14, octaves=3).astype(np.float32)
    brk = cv2.resize(brk, (W, H)) - 0.5
    _C[key] = (lo, mid, hi, hair, brk)
    return _C[key]


def burn_hole(fr, void, F, t, seed=719):
    """三层烧洞：F = 有符号距离（<0 洞内，>0 纸面）。
    外圈：不规则暗褐焦痕（宽 20–40px）+ 纸纤维毛边；中间：断续、粗细随机的橙红火线；内圈：卷起的碳化黑边（带一道受火光的卷沿）。
    洞内：void。返回 fr。"""
    lo, mid, hi, hair, brk = hole_noise(seed)
    wsc = 30 + 20 * (mid * 2)                                            # 焦痕宽度 20–40px
    # 洞缘紧邻外侧纸面微微翘起、透火光（暖），越往外越弱
    lift = np.exp(-np.clip(F - wsc, 0, None) / 45.0) * (F > wsc)
    fr = fr + lift[..., None] * np.array([0.30, 0.12, 0.03], np.float32) * 0.45
    # 外圈焦痕：内深外浅 + 纤维毛边
    sc = np.clip(1 - F / np.maximum(wsc, 6), 0, 1) * (F > 0)
    sc = np.clip(sc * 1.6, 0, 1) ** 0.7
    fuzz = np.clip((wsc + 14 - F) / 14, 0, 1) * (F > wsc * 0.6) * hair * 0.85
    S = np.clip(sc + fuzz * 0.6, 0, 1)
    brown = np.array([0.085, 0.032, 0.008], np.float32)
    toast = np.clip(1 - np.clip(F - wsc * 0.5, 0, None) / (wsc * 1.6 + 1), 0, 1) * (F > 0)    # 烤黄过渡带（焦痕外侧纸被烤成焦糖褐）
    fr = fr * (1 - toast[..., None] * np.array([0.25, 0.48, 0.70], np.float32))
    fr = fr * (1 - 0.94 * S[..., None]) + S[..., None] * brown * (0.8 + 0.9 * hi[..., None]) * (1 + 1.2 * np.exp(-F / 6.0))[..., None]
    # 洞内
    hole = np.clip(-F / 1.5, 0, 1)[..., None]
    fr = fr * (1 - hole) + void * hole
    # 内圈：卷起的碳化黑边（F ∈ [-wcar, 0]），外沿是黑炭、内沿一条卷曲的受光卷沿
    wcar = 14 + 12 * np.clip(lo * 2 + 0.5, 0, 1)
    car = np.clip((1 + F / wcar) * 4, 0, 1) * (F < 0)
    curl = np.clip(-F / wcar, 0, 1)                                       # 0 = 火线处，1 = 卷沿处
    char = np.array([0.032, 0.024, 0.019], np.float32) * (0.55 + 0.9 * curl)[..., None] * (1 + 2.2 * np.abs(hi)[..., None])
    fr = fr * (1 - car[..., None]) + car[..., None] * char
    lip = np.exp(-((F + wcar) / 2.0) ** 2) * (0.4 + 0.6 * np.clip(brk * 2 + 0.6, 0, 1))
    fr = fr + lip[..., None] * np.array([0.32, 0.13, 0.04], np.float32)
    shd = np.exp(-np.clip(-F - wcar, 0, None) / 5.0) * (F < -wcar)        # 卷沿下的投影
    fr = fr * (1 - 0.8 * shd[..., None])
    # 中间：断续火线（在洞缘 F≈0），粗细随机、明灭
    flick = 0.5 + 0.5 * np.sin(t * 13 + mid * 30)
    on = np.clip((brk + 0.03 + 0.06 * flick) * 5, 0, 1)                  # 断续
    thick = 1.5 + 4.0 * np.clip(mid * 2 + 0.5, 0, 1)
    line = np.exp(-((F + 1.5) / thick) ** 2) * on
    core = np.exp(-((F + 1.5) / (thick * 0.4)) ** 2) * on
    lg = cv2.GaussianBlur(line, (0, 0), 7)
    fr = fr + line[..., None] * np.array([1.0, 0.36, 0.07], np.float32) * 1.25 + core[..., None] * np.array([1.0, 0.72, 0.32], np.float32) * 0.9 \
        + lg[..., None] * np.array([0.9, 0.25, 0.04], np.float32) * 0.5
    return fr


def self_burn_glyph(fr, A, t, t0, seed=0, ink=(0.42, 0.035, 0.02)):
    """「字自燃」：无外框、无发光描边。字身暗朱墨 + 笔画边缘内侧碳化 + 边缘上断续的火星火线 + 由边缘飞起的火星。
    A = 全帧字 alpha（已含入场）。"""
    if t < t0 or A.max() <= 0: return fr
    q = t - t0
    ys, xs = np.nonzero(A > 0.02)
    if len(xs) == 0: return fr
    y0, y1, x0, x1 = max(0, ys.min() - 40), min(H, ys.max() + 40), max(0, xs.min() - 40), min(W, xs.max() + 40)
    a = A[y0:y1, x0:x1]
    ab = (a > 0.5).astype(np.uint8)
    inner = cv2.distanceTransform(ab, cv2.DIST_L2, 3).astype(np.float32)
    r = np.random.default_rng(seed)
    nz = cv2.resize(r.random(((y1 - y0) // 10 + 2, (x1 - x0) // 10 + 2)).astype(np.float32), (x1 - x0, y1 - y0), interpolation=cv2.INTER_CUBIC)
    nz2 = cv2.resize(r.random(((y1 - y0) // 4 + 2, (x1 - x0) // 4 + 2)).astype(np.float32), (x1 - x0, y1 - y0), interpolation=cv2.INTER_CUBIC)
    burn = c01(q / 0.5)                                                   # 火沿笔画边缘吃进去的深度
    sub = fr[y0:y1, x0:x1]
    body = np.asarray(ink, np.float32) * (0.85 + 0.3 * nz2[..., None])
    charw = 2 + 7 * burn * (0.5 + nz)
    char = np.clip(1 - inner / np.maximum(charw, 1), 0, 1) * (inner > 0)
    body = body * (1 - 0.85 * char[..., None])                           # 笔画边内侧碳化
    sub = sub * (1 - a[..., None]) + body * a[..., None]
    flick = np.sin(t * 17 + nz * 40) * 0.5 + 0.5
    on = np.clip((nz - 0.42 + 0.15 * flick) * 6, 0, 1) * min(1, q / 0.12)
    ring = np.exp(-((inner - charw * 0.55) / 1.6) ** 2) * (inner > 0) * on
    sub = sub + ring[..., None] * np.array([1.0, 0.5, 0.12], np.float32) * 1.4 + cv2.GaussianBlur(ring, (0, 0), 4)[..., None] * np.array([0.9, 0.3, 0.05], np.float32) * 0.6
    fr = fr.copy(); fr[y0:y1, x0:x1] = sub
    # 火星：从笔画边缘起飞、上飘、明灭
    P = np.zeros((H, W), np.float32)
    ey, ex = np.nonzero((inner > 0) & (inner < 2))
    if len(ex):
        rr = np.random.default_rng(seed + 7)
        for j in range(60):
            k = rr.integers(len(ex)); born = rr.uniform(0, 1.2)
            age = q - born
            if age < 0 or age > 0.7: continue
            x = x0 + ex[k] + 25 * age * rr.uniform(-1, 1) + 6 * math.sin(age * 9 + j)
            y = y0 + ey[k] - (60 + 120 * rr.random()) * age
            cv2.circle(P, (int(x), int(y)), 1 + int(rr.random() * 1.6), float(1 - age / 0.7), -1, cv2.LINE_AA)
    return fr + cv2.GaussianBlur(P, (0, 0), 0.7)[..., None] * np.array([1.4, 0.65, 0.2], np.float32)


def _mb(m, k, horiz=True):
    if k < 2: return m
    ker = np.ones((1, k), np.float32) / k if horiz else np.ones((k, 1), np.float32) / k
    return cv2.filter2D(m, -1, ker)


def warm_veil(A, B, p, axis='x', direction=-1, seed=7301, cap=0.68, warm=(1.0, 0.78, 0.48), dark=(0.10, 0.075, 0.06), shafts=True):
    """第七棒：有层次的暖色雾/烟幕转场（替代满屏平灰的 fog_wall / smoke_through 中间帧）。
    雾墙扫过（axis='x' 横扫 / 'y' 自下而上翻涌），浓度封顶 cap → 前后两镜的剪影在雾里始终透出；
    雾色 = 暗部暖褐 → 受光处淡金，叠斜入光束（明暗条纹）与翻卷的亮边。返回帧。"""
    h2, w2 = H // 2, W // 2
    yy, xx = np.mgrid[0:h2, 0:w2].astype(np.float32)
    e = c01(p); e = e * e * (3 - 2 * e)
    key = ('veil', seed)
    if key not in _C:
        n1 = K.fbm(h2, w2 * 2, seed, base=4, octaves=4).astype(np.float32)
        n2 = K.fbm(h2, w2 * 2, seed + 1, base=16, octaves=3).astype(np.float32)
        _C[key] = (n1, n2)
    n1, n2 = _C[key]
    off = int((e * 300) % w2)
    N = 0.6 * n1[:, off:off + w2] + 0.4 * n2[:, off:off + w2]
    if axis == 'x':
        span = w2 * 2.6; c = (w2 * 1.8 - span * e) if direction < 0 else (-w2 * 0.8 + span * e)
        d = (xx - c) * (-direction)
    else:
        span = h2 * 2.8; c = h2 * 1.9 - span * e
        d = -(yy - c)
    core = (w2 if axis == 'x' else h2) * 0.40
    dd = d + (N - 0.5) * 260
    dens = sstep_(-core - 120, -core + 60, dd) * sstep_(core + 120, core - 60, dd)
    dens = np.clip(dens * (0.55 + 0.7 * N), 0, 1) * cap
    lightv = np.clip(1.1 - yy / h2 * 0.8, 0, 1)
    if shafts:                                                     # 斜入光束：明暗条纹（左上 → 右下）
        sh = 0.5 + 0.5 * np.sin((xx * 0.9 + yy * 0.45) / 38.0 + 1.7) * np.sin((xx * 0.9 + yy * 0.45) / 91.0)
        lightv = lightv * (0.55 + 0.75 * sh)
    rim = np.clip(N - cv2.GaussianBlur(N, (0, 0), 6), 0, 1) * 5        # 翻卷亮边
    L = np.clip(lightv * (0.5 + 0.8 * N) + rim * 0.4, 0, 1.4)
    fogc = np.asarray(dark, np.float32) + (np.asarray(warm, np.float32) - np.asarray(dark, np.float32)) * L[..., None]
    up = lambda m: cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
    D = _mb(up(dens), 40, axis == 'x'); F = _mb(up(fogc), 40, axis == 'x')
    sw = up(d)
    base = np.where((sw > 0)[..., None], B, A)
    out = base * (1 - D[..., None]) + F * D[..., None]
    return out


def sstep_(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)
