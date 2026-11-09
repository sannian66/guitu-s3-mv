"""units/e_r6.py — E 组第六棒辅助：纸脸材质、横向光扫转场、金箔碎片转场、熔岩裂缝、秤。"""
import math
import numpy as np, cv2
import c1kit as K
from e_kit import W, H, sstep, c01, eio, eout, GOLDW

_C = {}


def paper_skin(seed=617):
    """宣纸糊面：叠皱（折痕脊线 + 受光明暗）+ 糊纸接缝 + 纤维。返回 (mul, add)：C' = C*mul + add。右上光。"""
    if seed in _C: return _C[seed]
    h2, w2 = H // 2, W // 2
    hgt = K.fbm(h2, w2, seed, base=7, octaves=5).astype(np.float32)
    rid = 1 - np.abs(2 * K.fbm(h2, w2, seed + 1, base=5, octaves=4).astype(np.float32) - 1)       # 折痕脊线
    rid = rid ** 6
    hh = hgt * 0.6 + rid * 0.5
    gy, gx = np.gradient(cv2.GaussianBlur(hh, (0, 0), 1.2))
    shade = np.clip(0.5 + 9.0 * (gx * 0.7 - gy * 0.7), 0, 1)                                   # 右上光
    fib = K.fbm(h2, w2 * 4, seed + 2, base=40, octaves=2).astype(np.float32)
    fib = cv2.resize(fib, (w2, h2))
    r = np.random.default_rng(seed)
    seam = np.zeros((h2, w2), np.float32); side = np.zeros((h2, w2), np.float32)
    for k in range(4):                                                                           # 糊纸接缝：不规则折线，一侧纸叠一层略亮
        if k % 2 == 0:
            y = r.uniform(0.15, 0.85) * h2; pts = [(x, y + r.uniform(-14, 14)) for x in np.linspace(-20, w2 + 20, 9)]
        else:
            x = r.uniform(0.2, 0.8) * w2; pts = [(x + r.uniform(-14, 14), y_) for y_ in np.linspace(-20, h2 + 20, 7)]
        P = np.array(pts, np.int32)
        cv2.polylines(seam, [P], False, 1.0, 1, cv2.LINE_AA)
        m = np.zeros((h2, w2), np.uint8)
        if k % 2 == 0: poly = np.vstack([P, [[w2 + 20, -20], [-20, -20]]])
        else: poly = np.vstack([P, [[-20, h2 + 20], [-20, -20]]])
        cv2.fillPoly(m, [poly.astype(np.int32)], 1)
        side += m * 0.05
    seam = cv2.GaussianBlur(seam, (0, 0), 0.7)
    mul = 0.72 + 0.42 * shade + 0.10 * (fib - 0.5) + side - 0.30 * seam
    add = (0.020 * rid)[..., None] * np.array([1.0, 0.85, 0.65], np.float32)
    mul = cv2.resize(mul.astype(np.float32), (W, H)); add = cv2.resize(add.astype(np.float32), (W, H))
    _C[seed] = (mul, add)
    return mul, add


def light_sweep(A, B, p, y=600, col=(1.0, 0.82, 0.5)):
    """横向光线扫入：一道贴地平线的白金光带自左向右扫过（带拖尾、上下扩散），光带经过处由 A 换成 B。"""
    e = eio(c01(p))
    xx = np.arange(W, dtype=np.float32)[None, :]
    yy = np.arange(H, dtype=np.float32)[:, None]
    x = -300 + (W + 600) * e
    m = np.clip((x - xx) / 420 + 0.5, 0, 1) ** 1.5                             # 光头之后 = B（宽软边，光幕里完成交接）
    m = np.broadcast_to(m, (H, W))
    out = A * (1 - m[..., None]) + B * m[..., None]
    d = xx - x
    head = np.exp(-(d / 60) ** 2) + 0.55 * np.exp(-np.clip(-d, 0, None) / 520) * (d < 0)
    vert = np.exp(-((yy - y) / 26) ** 2) * 1.6 + np.exp(-((yy - y) / 220) ** 2) * 0.35
    curtain = np.exp(-(d / 110) ** 2) * (0.55 + 0.45 * np.exp(-((yy - y) / 380) ** 2))     # 光头 = 一道竖向光幕，盖住交接线
    L = (head * vert + curtain * 1.1) * (1 - abs(2 * e - 1) ** 3)
    return out + L[..., None] * np.asarray(col, np.float32) * 1.4


def gold_leaf(A, B, p, center=(960, 540), seed=19, red_frac=0.12):
    """金箔碎片转场：A 碎成有厚度的金箔片（正面金、侧缘暗金厚度、少量朱红），向外翻飞，露出 B。"""
    e = c01(p)
    out = B.copy()
    r = np.random.default_rng(seed)
    n = 110
    cov = np.clip(1 - e * 1.35, 0, 1)
    if cov > 0:
        # A 先被一张随时间扩大的不规则洞吃掉
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.hypot(xx - center[0], yy - center[1]) / 1100
        nz = cv2.resize(K.fbm(H // 8, W // 8, seed, base=5, octaves=3).astype(np.float32), (W, H))
        hole = np.clip((e * 1.5 - d - 0.25 * nz) / 0.05, 0, 1)
        out = A * (1 - hole[..., None]) + B * hole[..., None]
    for i in range(n):
        ang = r.uniform(0, 2 * math.pi); sp = r.uniform(300, 1300); sz = r.uniform(12, 52)
        x = center[0] + math.cos(ang) * (r.uniform(0, 500) + sp * e); y = center[1] + math.sin(ang) * (r.uniform(0, 300) + sp * e) + 200 * e * e
        rot = r.uniform(0, 6.28) + e * r.uniform(-8, 8)
        flip = abs(math.cos(e * r.uniform(4, 12) + i))                      # 3D 翻转：宽度随 cos 变化
        k = r.integers(3, 6)
        pts = [(math.cos(rot + j * 2 * math.pi / k + r.uniform(-0.4, 0.4)) * sz * (0.3 + 0.7 * flip), math.sin(rot + j * 2 * math.pi / k) * sz) for j in range(k)]
        P = np.array([(x + a, y + b) for a, b in pts], np.int32)
        a = (1 - sstep(0.7, 1.0, e)) * sstep(0.0, 0.08, e)
        if a <= 0: continue
        red = r.random() < red_frac
        face = np.array([0.75, 0.10, 0.06], np.float32) * (0.5 + 0.6 * flip) if red else np.array([1.0, 0.76, 0.38], np.float32) * (0.25 + 1.1 * flip ** 3)
        edge = np.array([0.30, 0.18, 0.06], np.float32)
        Pt = P + np.array([4, 7], np.int32)                                   # 厚度：错位的暗缘
        cv2.fillPoly(out, [Pt], tuple(float(v) * a + 0 for v in edge), cv2.LINE_AA)
        m = np.zeros((H, W), np.float32)
        cv2.fillPoly(m, [P], 1.0, cv2.LINE_AA)
        out = out * (1 - a * m[..., None]) + a * m[..., None] * face
        cv2.line(out, tuple(int(v) for v in P[0]), tuple(int(v) for v in P[1]), tuple(float(v) * a for v in (1.6, 1.4, 1.0)), 1, cv2.LINE_AA)   # 箔边高光
    return out


def lava_crack(fr, x, t, seed=18, width=34, top=120, bot=960):
    """有厚度的熔岩裂缝（竖向，中心 x）：黑焦外缘 → 暗红 → 橙黄核心，噪声扰动；喷出碎屑。返回 (fr, offset(y)->dx)。"""
    yy = np.arange(H, dtype=np.float32)
    r = np.random.default_rng(seed)
    path = np.zeros(H, np.float32)
    for k in range(5):
        f = r.uniform(0.006, 0.05); path += r.uniform(3, 9) * np.sin(yy * f + r.uniform(0, 6))       # 小幅抖动：裂缝贴住两卡接缝
    cx = x + path
    xx = np.arange(W, dtype=np.float32)[None, :]
    d = np.abs(xx - cx[:, None])
    wv = width * (0.7 + 0.5 * np.sin(yy * 0.05 + t * 9)[:, None] * 0.3 + 0.3 * np.sin(yy * 0.013)[:, None])
    core = np.exp(-(d / (wv * 0.28)) ** 2)
    hot = np.exp(-(d / (wv * 0.7)) ** 2)
    char = np.clip(1 - d / (wv * 1.6), 0, 1)
    vis = ((yy >= top) & (yy <= bot)).astype(np.float32)[:, None]
    fr = fr * (1 - 0.85 * char * vis)[..., None]
    fr = fr + (hot * vis)[..., None] * np.array([0.9, 0.18, 0.04], np.float32) * 1.3 + (core * vis)[..., None] * np.array([1.0, 0.75, 0.35], np.float32) * 1.6
    gl = cv2.GaussianBlur((hot * vis).astype(np.float32), (0, 0), 30)
    fr = fr + gl[..., None] * np.array([1.0, 0.35, 0.08], np.float32) * 0.7
    # 碎屑
    P = np.zeros((H, W), np.float32)
    rr = np.random.default_rng(int(t * 30) + seed)
    for i in range(60):
        y = rr.uniform(top, bot); xi = int(min(max(int(y), 0), H - 1))
        age = rr.random()
        sx = cx[xi] + (rr.random() - 0.5) * 2 * (40 + 260 * age); sy = y - 120 * age
        cv2.circle(P, (int(sx), int(sy)), int(1 + 3 * (1 - age)), float(1 - age), -1, cv2.LINE_AA)
    fr = fr + cv2.GaussianBlur(P, (0, 0), 0.8)[..., None] * np.array([1.4, 0.7, 0.25], np.float32)
    return fr, cx


def weave(h, w, seed=28, pitch=7):
    """布料编织纹（经纬交错的明暗），0..1。"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nz = cv2.resize(K.fbm(max(2, h // 8), max(2, w // 8), seed, base=6, octaves=3).astype(np.float32), (w, h))
    wx = 0.5 + 0.5 * np.sin(2 * math.pi * (xx + 6 * nz) / pitch)
    wy = 0.5 + 0.5 * np.sin(2 * math.pi * (yy + 6 * nz) / pitch)
    chk = ((np.floor(xx / pitch) + np.floor(yy / pitch)) % 2).astype(np.float32)
    return np.clip(chk * wx + (1 - chk) * wy, 0, 1)
