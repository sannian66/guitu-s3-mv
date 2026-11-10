"""trans.py —《谁定正邪》MV 转场库 + 镜头工具（字幕·转场组）

纯代码程序化（numpy / OpenCV）。所有帧 float32 RGB (1080,1920,3) 0–1。
  transition(name, frA, frB, p, **kw) -> frame      p: 0→1（0=全 A，1=全 B）
  camera(fr, t, spec) -> frame                       镜头运动（推拉摇移/旋转/甩镜/手持柏林抖动/速度坡度/鼓点冲击）
随机性全部来自传入 seed 的 np.random.default_rng，同一 (p, seed) 结果可复现。

耗时（2 vCPU 实测，1080p 单帧，9 相位平均/最大；原始数据 lib/typo_test/timing_trans.txt）：
  hard_cut_on_beat 0.01/0.01   match_cut 0.05/0.06   slash_wipe 0.10/0.13   slash_wipe(circle) 0.09/0.12
  ink_bleed 0.05/0.06          whip_pan_blur 0.03/0.05 (rotate 0.02)        flash_white 0.02/0.03   flash_red 0.05/0.05
  paper_tear 0.21/0.23         shatter 0.09/0.14     occlusion 0.07/0.07    iris_moon 0.07/0.08 (sun 0.16, collapse 0.09)
  smoke_through 0.05/0.05      zoom_through 0.02/0.03 (raindrop 0.08/0.12, paper 0.05, glint 0.04)
  glitch_cut 0.03/0.05         fade_black 0.004      split_slide 0.16/0.17  freeze_glitch 0.06/0.08
  camera（推拉+抖动+冲击）0.01/0.03（甩镜带运动模糊时 +0.02）
"""
import math
from functools import lru_cache
import numpy as np, cv2

W, H = 1920, 1080
BAR = 120
RED = np.array([0.72, 0.06, 0.05], np.float32)
GOLD = np.array([1.0, 0.76, 0.40], np.float32)
INK = np.array([0.03, 0.03, 0.035], np.float32)
PAPER = np.array([0.93, 0.90, 0.84], np.float32)


def _rng(s): return np.random.default_rng(int(s) & 0x7fffffff)
def _c(x): return float(min(1.0, max(0.0, x)))
def ease_io(x): x = _c(x); return x * x * (3 - 2 * x)
def ease_out(x, k=3): x = _c(x); return 1 - (1 - x) ** k
def ease_in(x, k=3): x = _c(x); return x ** k
def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0, 1); return t * t * (3 - 2 * t)


@lru_cache(64)
def _noise(h, w, scale, seed, ax=1, ay=1):
    r = _rng(seed)
    n = cv2.resize(r.random((max(2, int(h / scale / ay)), max(2, int(w / scale / ax)))).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    return np.clip(n, 0, 1)


def fbm(h, w, seed, scale=200, oct=4):
    out = np.zeros((h, w), np.float32); a = 0.5; tot = 0
    for o in range(oct):
        out += _noise(h, w, max(2, scale / 2 ** o), seed + o) * a; tot += a; a *= 0.5
    return out / tot


@lru_cache(4)
def _grid():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32); return x, y


def _blur_dir(fr, dx, dy, scale=4):
    """方向运动模糊（低分辨率卷积再放大）。"""
    L = math.hypot(dx, dy) / scale
    if L < 1: return fr
    k = int(L) * 2 + 1
    ker = np.zeros((k, k), np.float32)
    c = k // 2; ux, uy = dx / (L * scale), dy / (L * scale)
    cv2.line(ker, (int(c - ux * L), int(c - uy * L)), (int(c + ux * L), int(c + uy * L)), 1.0, 1)
    ker /= ker.sum()
    sm = cv2.resize(fr, (W // scale, H // scale), interpolation=cv2.INTER_AREA)
    sm = cv2.filter2D(sm, -1, ker, borderType=cv2.BORDER_REFLECT)
    return cv2.resize(sm, (W, H), interpolation=cv2.INTER_LINEAR)


def _radial_blur(fr, c, amt, n=6, scale=2):
    """径向（推镜）模糊：多张围绕中心的放大副本求平均（半分辨率）。"""
    if amt < 0.003: return fr
    sw, sh = W // scale, H // scale
    sm = cv2.resize(fr, (sw, sh), interpolation=cv2.INTER_AREA)
    acc = np.zeros_like(sm)
    for i in range(n):
        s = 1 + amt * i / (n - 1)
        M = cv2.getRotationMatrix2D((c[0] / scale, c[1] / scale), 0, s)
        acc += cv2.warpAffine(sm, M, (sw, sh), borderMode=cv2.BORDER_REFLECT)
    return cv2.resize(acc / n, (W, H), interpolation=cv2.INTER_LINEAR)


def _zoom(fr, s, c=(W / 2, H / 2), rot=0.0, tx=0.0, ty=0.0, border=cv2.BORDER_REFLECT):
    M = cv2.getRotationMatrix2D(c, rot, s); M[:, 2] += [tx, ty]
    return cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=border)


def _bloom(fr, amt=0.5, thr=0.75, sigma=20):
    hi = np.clip(fr - thr, 0, None)
    sm = cv2.GaussianBlur(cv2.resize(hi, (W // 4, H // 4), interpolation=cv2.INTER_AREA), (0, 0), sigma / 4)
    return fr + cv2.resize(sm, (W, H)) * amt


def _lerp(a, b, m):
    if np.isscalar(m): return a * (1 - m) + b * m
    m = m[..., None] if m.ndim == 2 else m
    return a * (1 - m) + b * m


# ======================================================================== 转场
def hard_cut_on_beat(A, B, p, frames=6, impact=0.06, flash=0.18, at=0.5):
    """硬切：p<at 为 A，之后 B；切后第 1 帧冲击（放大 impact + 提亮 flash），第 2 帧余波一半。
    frames：该转场覆盖的帧数（用于判断“第 1 帧”）；常用做法 frames=2、at=0.5 即恰在切点那一帧冲击。"""
    if p < at: return A.copy()
    k = int((p - at) * frames + 1e-6)
    if k >= 2: return B.copy()
    a = 1.0 if k == 0 else 0.45
    out = _zoom(B, 1 + impact * a)
    return out * (1 + flash * a) + flash * 0.25 * a


def match_cut(A, B, p, mask=None, shape='circle', center=(W / 2, H / 2), radius=200, angle=0.0, feather=30,
              mode='grow', glow=GOLD):
    """匹配剪辑：A 中某形状（mask：A 中匹配物体的 0–1 蒙版；或 shape='circle'/'line'）作为门，
    B 从这个形状里长出来铺满全屏（mode='grow'）；mode='cut' 则在 0.5 处硬切并在形状处闪一下金边。
    'line' 用 center/angle 定义一条线（地平线↔刀身）。"""
    x, y = _grid()
    if mask is None:
        if shape == 'circle':
            d = np.sqrt((x - center[0]) ** 2 + (y - center[1]) ** 2) - radius
        else:
            th = math.radians(angle)
            d = np.abs(-(x - center[0]) * math.sin(th) + (y - center[1]) * math.cos(th)) - 3
    else:
        m = (mask > 0.5).astype(np.uint8)
        d = cv2.distanceTransform(1 - m, cv2.DIST_L2, 3) - cv2.distanceTransform(m, cv2.DIST_L2, 3)
    if mode == 'cut':
        base = A if p < 0.5 else B
        edge = np.exp(-(d / 4) ** 2) * max(0, 1 - abs(p - 0.5) / 0.2)
        return base + edge[..., None] * glow * 0.8
    R = (float(d.max()) + feather) * ease_in(p, 1.8)
    m = np.clip((R - d) / feather, 0, 1)
    out = _lerp(A, B, m)
    edge = np.exp(-((d - R) / 6) ** 2) * (1 - p) * (p > 0.01)
    return out + edge[..., None] * glow * 0.9


def _slash_streak(fr, c, d, q, length=2600, width=3, color=(1, 0.97, 0.92), amt=1.0):
    if q <= 0 or q > 1: return fr
    head = min(1, q / 0.6); tail = max(0, (q - 0.3) / 0.7)
    p0 = np.array(c) + d * length * (tail - 0.5); p1 = np.array(c) + d * length * (head - 0.5)
    L = np.zeros((H // 2, W // 2), np.float32)
    cv2.line(L, tuple((p0 / 2).astype(int)), tuple((p1 / 2).astype(int)), 1.0, width, cv2.LINE_AA)
    s = cv2.GaussianBlur(L, (0, 0), 0.8) * 2.5 + cv2.GaussianBlur(L, (0, 0), 12) * 5
    return fr + cv2.resize(s, (W, H))[..., None] * np.array(color, np.float32) * amt * (1 - tail)


def slash_wipe(A, B, p, angle=-30.0, center=(W / 2, H / 2), circle=False, radius=330, gap_glow=True, seed=0, soft_edges=False):
    """刀光擦除。直线版：0–0.25 刀光沿斜线划过，随后 A 沿斩线一分为二、两半反向滑出，B 从缝中露出。
    angle=90/-90 为竖斩，0 为横斩。circle=True：圆形刀光（spin_slash）——刀光沿圆周旋一圈，圆内换成 B 并向外扩到全屏。"""
    x, y = _grid()
    if circle:
        out = A.copy()
        r = radius
        if p < 0.4:
            q = p / 0.4
            L = np.zeros((H // 2, W // 2), np.float32)
            a1 = 360 * ease_io(q); a0 = max(0, a1 - 200)
            cv2.ellipse(L, (int(center[0] / 2), int(center[1] / 2)), (int(r / 2), int(r / 2)), -90, a0, a1, 1.0, 2, cv2.LINE_AA)
            s = cv2.GaussianBlur(L, (0, 0), 0.8) * 2.5 + cv2.GaussianBlur(L, (0, 0), 12) * 5
            return out + cv2.resize(s, (W, H))[..., None] * np.array([1, 0.96, 0.9], np.float32)
        q = (p - 0.4) / 0.6
        R = r + 2000 * ease_in(q, 2)
        d = np.sqrt((x - center[0]) ** 2 + (y - center[1]) ** 2)
        m = np.clip((R - d) / 3, 0, 1)
        # 圆内 A 的圆片被“旋开”：先把 A 圆片转一下再露 B
        inner = _zoom(A, 1 + 0.3 * q, center, rot=40 * q)
        out = _lerp(_lerp(A, inner, (d < r)), B, m)
        edge = np.exp(-((d - R) / 5) ** 2) * (1 - q)
        return out + edge[..., None] * np.array([1, 0.95, 0.85], np.float32) * 1.5
    th = math.radians(angle); dv = np.array([math.cos(th), math.sin(th)]); nv = np.array([-dv[1], dv[0]])
    sd = (x - center[0]) * nv[0] + (y - center[1]) * nv[1]
    if p < 0.22:
        return _slash_streak(A, center, dv, 0.6 * p / 0.22)
    q = (p - 0.22) / 0.78
    e = ease_in(q, 2.2) * 1.15
    shift = e * 2200
    s1 = _zoom(A, 1, tx=-dv[0] * shift * 0.5 - nv[0] * e * 60, ty=-dv[1] * shift * 0.5 - nv[1] * e * 60, border=cv2.BORDER_CONSTANT)
    s2 = _zoom(A, 1, tx=dv[0] * shift * 0.5 + nv[0] * e * 60, ty=dv[1] * shift * 0.5 + nv[1] * e * 60, border=cv2.BORDER_CONSTANT)
    # 两半的掩膜随各自位移
    M1 = np.float32([[1, 0, -dv[0] * shift * 0.5 - nv[0] * e * 60], [0, 1, -dv[1] * shift * 0.5 - nv[1] * e * 60]])
    M2 = np.float32([[1, 0, dv[0] * shift * 0.5 + nv[0] * e * 60], [0, 1, dv[1] * shift * 0.5 + nv[1] * e * 60]])
    if soft_edges:
        # r6-B3（#32 105.9）：两半滑开时 A 自身画布的四条边会跟着滑进画面，成了带橙色描边的硬边方框。
        # 改：半片掩膜用 REPLICATE 平移（只剩斩线一条边）；画布边改 220px 羽化淡出到 B；橙色缝光只沿斩线、不描画布边。
        sm = cv2.GaussianBlur((sd < 0).astype(np.float32), (0, 0), 1.2)
        h1 = cv2.warpAffine(sm, M1, (W, H), borderMode=cv2.BORDER_REPLICATE)
        h2 = cv2.warpAffine(1 - sm, M2, (W, H), borderMode=cv2.BORDER_REPLICATE)
        fx = np.clip(np.minimum(x, W - 1 - x) / 220, 0, 1); fy = np.clip(np.minimum(y, H - 1 - y) / 220, 0, 1)
        F = (fx * fy) ** 1.5
        f1 = cv2.warpAffine(F, M1, (W, H)); f2 = cv2.warpAffine(F, M2, (W, H))
        m1 = h1 * f1; m2 = h2 * f2
        seam = np.clip(h1 + h2, 0, 1)
    else:
        m1 = cv2.warpAffine(((sd < 0)).astype(np.float32), M1, (W, H))
        m2 = cv2.warpAffine(((sd >= 0)).astype(np.float32), M2, (W, H))
        seam = m1 + m2
    Bz = _zoom(B, 1.08 - 0.08 * ease_out(q))
    out = _lerp(Bz, s1, m1); out = _lerp(out, s2, m2)
    if gap_glow:
        rim = np.clip(np.abs(cv2.Sobel(seam, cv2.CV_32F, 0, 1)) + np.abs(cv2.Sobel(seam, cv2.CV_32F, 1, 0)), 0, 1)
        rim = cv2.GaussianBlur(rim, (0, 0), 3) * 2 * (1 - q)
        out += rim[..., None] * np.array([1, 0.6, 0.25], np.float32)
    return _slash_streak(out, center, dv, 0.6 + q * 0.4, amt=1 - q)


def ink_bleed(A, B, p, seed=0, center=None, edge=0.85, scale=1.0, white=False):
    """墨晕有机扩散：fbm 噪声 + 距中心距离构成到达时间场，B 随墨迹洇开出现，边缘一圈浓墨（white=True 为白色宣纸晕）。"""
    hs, ws = H // 4, W // 4
    c = center or (W / 2, H / 2)
    y, x = np.mgrid[0:hs, 0:ws].astype(np.float32)
    d = np.sqrt(((x * 4 - c[0]) / W) ** 2 * 3.1 + ((y * 4 - c[1]) / H) ** 2) / 1.05 / scale
    f = d + (fbm(hs, ws, seed, 60) - 0.5) * 0.6 + (_noise(hs, ws, 4, seed + 9) - 0.5) * 0.08
    thr = -0.15 + p * 1.6
    m = np.clip((thr - f) * 9, 0, 1)
    band = np.exp(-((thr - f - 0.05) / 0.06) ** 2) * (0 < p < 1)
    m = cv2.resize(m, (W, H)); band = cv2.resize(band.astype(np.float32), (W, H))
    out = _lerp(A, B, m)
    col = PAPER if white else INK
    return _lerp(out, np.broadcast_to(col, out.shape), np.clip(band * edge, 0, 1))


def whip_pan_blur(A, B, p, direction='right', strength=1.0, rot_deg=60.0):
    """甩镜：A 加速甩出（方向运动模糊增强），0.5 处换 B，B 带模糊减速入位。direction: left/right/up/down/rotate。"""
    dirs = {'right': (1, 0), 'left': (-1, 0), 'up': (0, -1), 'down': (0, 1)}
    if direction == 'rotate':
        src = A if p < 0.5 else B
        q = p / 0.5 if p < 0.5 else (1 - p) / 0.5
        e = ease_in(q, 2)
        ang = rot_deg * e * (1 if p < 0.5 else -1)
        sm = cv2.resize(src, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        acc = np.zeros_like(sm); n = 7
        for i in range(n):
            M = cv2.getRotationMatrix2D((W / 8, H / 8), ang + (i / (n - 1) - 0.5) * 40 * e * strength, 1 + 0.15 * e)
            acc += cv2.warpAffine(sm, M, (W // 4, H // 4), borderMode=cv2.BORDER_REFLECT)
        bl = cv2.resize(acc / n, (W, H))
        sharp = _zoom(src, 1 + 0.15 * e, rot=ang)
        return _lerp(sharp, bl, min(1, e * 1.6))
    dx, dy = dirs[direction]
    if p < 0.5:
        q = p / 0.5; e = ease_in(q, 2.5); src = A; off = -e * 0.6
    else:
        q = (1 - p) / 0.5; e = ease_in(q, 2.5); src = B; off = e * 0.6
    tx, ty = dx * off * W * strength, dy * off * H * strength
    moved = _zoom(src, 1.0 + 0.04 * e, tx=tx, ty=ty)
    bl = _blur_dir(moved, dx * e * 700 * strength, dy * e * 500 * strength)
    return _lerp(moved, bl, min(1, e * 2)) * (1 + 0.15 * e)


def flash_white(A, B, p, color=(1, 1, 1), peak=0.5, width=0.5, bloom=True):
    """闪白：在 peak 处曝光到纯色，前半 A 后半 B。width 为闪光占转场比例。"""
    col = np.array(color, np.float32)
    base = A if p < peak else B
    env = max(0.0, 1 - abs(p - peak) / (width / 2)) ** 1.5
    out = base * (1 + env * 1.2)
    out = _lerp(out, np.broadcast_to(col, out.shape), env * 0.9)
    if bloom and env > 0.05: out = _bloom(out, env * 0.8, 0.6)
    return out


def flash_red(A, B, p, peak=0.5, width=0.35, one_frame=False, frames=6):
    """红闪（朱红曝光 + 暗部压红）；one_frame=True 只在切点那一帧红（frames=转场帧数）。"""
    if one_frame:
        if p < peak: return A.copy()
        if int((p - peak) * frames) == 0:
            lum = (B * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
            return np.clip(lum * 1.4, 0, 1) * np.array([1.0, 0.12, 0.08], np.float32) + RED * 0.35
        return B.copy()
    base = A if p < peak else B
    env = max(0.0, 1 - abs(p - peak) / (width / 2)) ** 1.3
    lum = (base * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
    red = np.clip(lum * 1.5 + 0.25, 0, 1.2) * np.array([1.0, 0.1, 0.07], np.float32)
    return _lerp(base, red, env)


def paper_tear(A, B, p, seed=0, angle=8.0, pull=1.0, fiber=True):
    """纸撕裂：A 沿一道锯齿撕口（大起伏+细锯齿）一分为二，两片向两侧拉开并轻微旋转，撕口边缘带白色纸纤维毛边；露出 B。"""
    r = _rng(seed)
    yy = np.arange(H, dtype=np.float32)
    big = np.interp(yy, np.linspace(0, H, 9), r.uniform(-90, 90, 9))
    fine = np.interp(yy, np.linspace(0, H, 120), r.uniform(-14, 14, 120))
    tear = W / 2 + big + fine + (yy - H / 2) * math.tan(math.radians(angle))
    x, y = _grid()
    side = (x > tear[None, :].T.reshape(H, 1)).astype(np.float32)
    e = ease_in(p, 1.8) * pull
    pieces = []
    dist = np.abs(x - tear.reshape(H, 1))
    fn = _noise(H, W, 2, seed + 3, ax=1, ay=5)
    wv = 6 + 14 * _noise(H, W, 40, seed + 4)
    for s_, sgn in ((1 - side, -1), (side, 1)):
        tx = sgn * e * W * 0.65; rot = -sgn * e * 7
        cx_ = W / 2 + sgn * W * 0.5
        M = cv2.getRotationMatrix2D((cx_, H * (0.0 if sgn < 0 else 1.0)), rot, 1.0); M[0, 2] += tx
        piece = cv2.warpAffine(A, M, (W, H), borderMode=cv2.BORDER_CONSTANT)
        m = cv2.warpAffine(s_, M, (W, H), borderMode=cv2.BORDER_CONSTANT)
        if fiber:   # 纤维毛边：撕口附近一圈纸白、带拉丝噪声
            band = np.clip((wv - dist) / 3, 0, 1) * s_ * np.clip((fn - 0.25) * 2.5, 0, 1)
            band = cv2.warpAffine(band, M, (W, H))
            piece = _lerp(piece, np.broadcast_to(PAPER, piece.shape), band)
            m = np.maximum(m, band)
        pieces.append((piece, m))
    mm = np.maximum(pieces[0][1], pieces[1][1])
    shadow = cv2.resize(cv2.GaussianBlur(cv2.resize(mm, (W // 4, H // 4)), (0, 0), 6), (W, H))
    out = B * (1 - 0.55 * shadow[..., None])      # 撕片在 B 上的投影
    for piece, m in pieces:
        out = _lerp(out, piece, m)
    return out


def _tris(n, seed, x0=0, y0=0, x1=W, y1=H, center=None):
    r = _rng(seed)
    if center is not None:   # 抖动网格（碎片大小均匀、无针状三角）+ 冲击点附近加密
        gx, gy = int(math.sqrt(n * 1.6)), max(2, int(math.sqrt(n / 1.6)))
        xx, yy = np.meshgrid((np.arange(gx) + 0.5) / gx, (np.arange(gy) + 0.5) / gy)
        pts = np.stack([x0 + (xx.ravel() + r.uniform(-0.35, 0.35, xx.size) / gx) * (x1 - x0),
                        y0 + (yy.ravel() + r.uniform(-0.35, 0.35, yy.size) / gy) * (y1 - y0)], 1)
        k = max(4, n // 5); ang = r.uniform(0, 2 * math.pi, k); rad = r.uniform(30, 260, k)
        pts = np.concatenate([pts, np.stack([center[0] + np.cos(ang) * rad, center[1] + np.sin(ang) * rad], 1)])
    else:
        pts = r.uniform([x0, y0], [x1, y1], (n, 2))
    border = np.concatenate([np.stack([np.linspace(x0, x1, 8), np.full(8, y0)], 1), np.stack([np.linspace(x0, x1, 8), np.full(8, y1)], 1),
                             np.stack([np.full(6, x0), np.linspace(y0, y1, 6)], 1), np.stack([np.full(6, x1), np.linspace(y0, y1, 6)], 1)])
    pts = np.concatenate([np.clip(pts, [x0, y0], [x1, y1]), border])
    sub = cv2.Subdiv2D((x0 - 2, y0 - 2, x1 - x0 + 5, y1 - y0 + 5))
    for q in pts: sub.insert((float(q[0]), float(q[1])))
    T = sub.getTriangleList().reshape(-1, 3, 2)
    ok = (T[..., 0] >= x0 - 1).all(1) & (T[..., 0] <= x1 + 1).all(1) & (T[..., 1] >= y0 - 1).all(1) & (T[..., 1] <= y1 + 1).all(1)
    return T[ok].astype(np.float32)


def shatter(A, B, p, seed=0, center=(W / 2, H / 2), n=70, crack=0.15, power=1.0):
    """玻璃/瓷碎裂：0–crack 冲击点放射裂纹（白线）；之后 A 碎成三角块朝镜头飞散（放大、旋转、受光明暗不同），露出 B。"""
    T = _tris(n, seed, center=center)
    r = _rng(seed + 1)
    if p < crack:
        q = p / crack
        L = np.zeros((H // 2, W // 2), np.float32)
        for tri in T:
            c = tri.mean(0)
            if np.linalg.norm(c - center) < 1500 * q:
                cv2.polylines(L, [(tri / 2).astype(np.int32)], True, 1.0, 1, cv2.LINE_AA)
        Ls = cv2.resize(cv2.GaussianBlur(L, (0, 0), 0.6), (W, H))
        out = A + Ls[..., None] * 0.8
        return _zoom(out, 1 + 0.02 * q)
    q = (p - crack) / (1 - crack)
    out = _zoom(B, 1.06 - 0.06 * ease_out(q))
    e = ease_in(q, 1.6)
    k = 2                                   # 飞散碎片在半分辨率合成（运动中肉眼无差），保证 ≤0.25s
    As = cv2.resize(A, (W // k, H // k), interpolation=cv2.INTER_AREA)
    acc = np.zeros_like(As); aa = np.zeros(As.shape[:2], np.float32)
    cen = np.array(center) / k
    items = []
    for tri in T:
        tri = tri / k
        c = tri.mean(0); v = c - cen; dist = np.linalg.norm(v) + 1e-3; v /= dist
        z = 1 + (r.uniform(0.8, 3.0) * e) * power
        sp = r.uniform(200, 900) * power * e / k
        ang = r.uniform(-1, 1) * 260 * e
        shade = r.uniform(0.75, 1.3)
        items.append((z, tri, c, v, sp, ang, shade))
    items.sort(key=lambda it: it[0])
    fade = 1 - smooth(0.75, 1.0, q)
    Wk, Hk = W // k, H // k
    for z, tri, c, v, sp, ang, shade in items:
        x0, y0 = np.floor(tri.min(0)).astype(int); x1, y1 = np.ceil(tri.max(0)).astype(int) + 1
        x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(Wk, x1), min(Hk, y1)
        if x1 - x0 < 2 or y1 - y0 < 2: continue
        patch = As[y0:y1, x0:x1]
        m = np.zeros((y1 - y0, x1 - x0), np.float32)
        cv2.fillConvexPoly(m, np.round((tri - [x0, y0]) * 4).astype(np.int32), 1.0, cv2.LINE_AA, shift=2)
        nc = cen + (c - cen) * z + v * sp
        d = int(max(x1 - x0, y1 - y0) * z * 1.5) + 2
        ox, oy = int(nc[0] - d / 2), int(nc[1] - d / 2)
        xs, ys = max(0, ox), max(0, oy); xe, ye = min(Wk, ox + d), min(Hk, oy + d)
        if xe <= xs or ye <= ys: continue
        M = cv2.getRotationMatrix2D((c[0] - x0, c[1] - y0), ang, z); M[:, 2] += [d / 2 - (c[0] - x0) - (xs - ox), d / 2 - (c[1] - y0) - (ys - oy)]
        sz = (xe - xs, ye - ys)
        wp = cv2.warpAffine(patch, M, sz); wm = cv2.warpAffine(m, M, sz)[..., None]
        acc[ys:ye, xs:xe] = acc[ys:ye, xs:xe] * (1 - wm) + np.clip(wp * shade, 0, 1.3) * wm
        aa[ys:ye, xs:xe] = aa[ys:ye, xs:xe] * (1 - wm[..., 0]) + wm[..., 0]
    accU = cv2.resize(acc, (W, H)); aaU = cv2.resize(aa, (W, H))[..., None] * fade
    return out * (1 - aaU) + accU * aaU


@lru_cache(8)
def _occluder(kind, seed):
    """前景遮挡物剪影（宽画布 1.8W×H，半分辨率），1=实。"""
    w2, h2 = int(W * 1.8) // 2, H // 2
    m = np.zeros((h2, w2), np.float32); r = _rng(seed)
    cx = w2 // 2
    if kind == 'pillar':
        cv2.rectangle(m, (cx - 170, 0), (cx + 170, h2), 1.0, -1)
    elif kind == 'branch':   # 松枝：主干 + 针叶簇
        pts = [(cx - 120, h2 + 40)]
        for i in range(8): pts.append((pts[-1][0] + int(r.integers(30, 70)), pts[-1][1] - int(r.integers(40, 80))))
        for a, b in zip(pts[:-1], pts[1:]): cv2.line(m, a, b, 1.0, 26 - len(pts))
        for (px, py) in pts[1:]:
            for _ in range(10):
                bx, by = px + r.integers(-120, 120), py + r.integers(-90, 60)
                cv2.line(m, (px, py), (bx, by), 1.0, 5)
                for k in range(40):
                    ang = r.uniform(0, 2 * math.pi); l = r.uniform(25, 70)
                    cv2.line(m, (bx, by), (int(bx + math.cos(ang) * l), int(by + math.sin(ang) * l * 0.6)), 1.0, 2, cv2.LINE_AA)
        m = cv2.dilate(m, np.ones((3, 3), np.uint8))
        cv2.rectangle(m, (cx - 200, 0), (cx + 60, h2), 1.0, -1)            # 枝干后紧跟的暗块，切换线藏在其中
    elif kind == 'crowd':   # 人群背影：肩+头剪影
        x = 0
        while x < w2:
            hw = r.integers(70, 110); hy = h2 - r.integers(160, 300)
            cv2.ellipse(m, (x, hy + hw), (hw, hw + 40), 0, 180, 360, 1.0, -1)
            cv2.rectangle(m, (x - hw, hy + hw), (x + hw, h2), 1.0, -1)
            cv2.circle(m, (x, hy - 10), int(hw * 0.45), 1.0, -1)
            x += r.integers(60, 120)
        cv2.rectangle(m, (cx - 260, 0), (cx + 260, h2), 1.0, -1)
    elif kind == 'spear':  # 枪林
        for i in range(-12, 13):
            x = cx + i * 55 + r.integers(-15, 15)
            cv2.line(m, (x, h2), (x + r.integers(-40, 40), 0), 1.0, int(r.integers(8, 16)))
        cv2.rectangle(m, (cx - 200, 0), (cx + 200, h2), 1.0, -1)
    else:  # 'blade' 横扫的刀身/天平臂：粗斜条
        cv2.rectangle(m, (cx - 230, -50), (cx + 230, h2 + 50), 1.0, -1)
    m = cv2.GaussianBlur(m, (0, 0), 1.5)
    cols = np.nonzero(m.max(0) > 0.02)[0]
    return m, (cx - cols.min()) * 2 + 80, (cols.max() - cx) * 2 + 80    # 左/右伸展（全分辨率 px）


def occlusion(A, B, p, kind='pillar', direction=1, seed=0, color=INK, blur=16):
    """前景遮挡转场：一道近景暗剪影（pillar 柱 / branch 松枝 / crowd 人群背影 / spear 枪林 / blade 刀身臂）横扫过镜，
    在剪影最宽处完成 A→B 切换（切换线藏在剪影里）。direction=1 左→右，-1 右→左。带运动模糊。"""
    occ, le, re = _occluder(kind, seed)
    w2 = occ.shape[1]
    if direction > 0:   # 起止时剪影完全在画外
        pos = -re - blur + (W + le + re + 2 * blur) * ease_io(p)
    else:
        occ = occ[:, ::-1]; le, re = re, le
        pos = W + le + blur - (W + le + re + 2 * blur) * ease_io(p)
    M = np.float32([[2, 0, pos - w2], [0, 2, 0]])  # 半分辨率→全分辨率并平移
    S = cv2.warpAffine(occ, M, (W, H))
    S = _blur_dir(np.repeat(S[..., None], 3, -1), blur * direction * 4, 0)[..., 0] if blur else S
    x, _ = _grid()
    wipe = (x < pos) if direction > 0 else (x > pos)
    out = np.where(wipe[..., None], B, A)
    return _lerp(out, np.broadcast_to(np.asarray(color, np.float32), out.shape), np.clip(S * 1.05, 0, 1))


def iris_moon(A, B, p, center=(W / 2, H / 2), radius=180, mode='open', sun=False, ring=True, dot_color=RED):
    """月轮光圈。
    mode='open'      B 在一轮月形圆中出现（从 radius 起）并扩到全屏（“月为光圈”）
    mode='close'     A 收拢进圆、圆收到 0 后再从圆开出 B（经典 iris in/out）
    mode='collapse'  反向收拢：A 收进一点，最后剩一点朱红（dot_color）在黑中，再淡出到 B（片尾“收墨成一点朱红”）
    sun=True         日轮版：圆缘金色光芒+放射光束+强泛光，圆内过曝后回落"""
    x, y = _grid()
    d = np.sqrt((x - center[0]) ** 2 + (y - center[1]) ** 2)
    rim_col = GOLD if sun else np.array([0.92, 0.92, 0.88], np.float32)
    if mode == 'open':
        R = radius + 2100 * ease_in(p, 2.4)
        m = np.clip((R - d) / 2.5, 0, 1)
        inner = _zoom(B, 1.12 - 0.12 * ease_out(p))
        if sun: inner = inner + (1 - p) * 0.6
        out = _lerp(A, inner, m)
        rim_d = d - R
    elif mode == 'close':
        if p < 0.5:
            R = (1 - ease_in(p / 0.5, 1.5)) * 1200; src = A
        else:
            R = ease_out((p - 0.5) / 0.5, 2) * 1200; src = B
        m = np.clip((R - d) / 2.5, 0, 1)
        out = src * m[..., None] + INK * (1 - m[..., None])
        rim_d = d - R
    else:   # collapse
        if p < 0.7:
            q = p / 0.7; R = 12 + (1 - ease_out(q, 2)) * 1300
            m = np.clip((R - d) / 2.5, 0, 1)
            tint = smooth(0.6, 1.0, q)
            src = _lerp(A, np.broadcast_to(dot_color, A.shape), tint)
            out = src * m[..., None] + INK * (1 - m[..., None])
            rim_d = d - R
        else:
            q = (p - 0.7) / 0.3
            m = np.clip((12 - d) / 2.5, 0, 1) * (1 - q)
            out = _lerp(INK * (1 - q) + B * q, np.broadcast_to(dot_color, A.shape), m)
            g = np.exp(-(d / 40) ** 2) * (1 - q) * 0.6
            return out + g[..., None] * dot_color
    if ring:
        rim = np.exp(-(rim_d / 4) ** 2) * 1.2 + np.exp(-(np.maximum(rim_d, 0) / 40)) * 0.35 * (rim_d > 0)
        out = out + rim[..., None] * rim_col * (1.0 if sun else 0.6) * (1 - max(0, p - 0.85) / 0.15 if mode == 'open' else 1)
    if sun:
        ang = np.arctan2(y - center[1], x - center[0])
        rays = (np.sin(ang * 23) * 0.5 + 0.5) ** 6 * np.exp(-np.maximum(rim_d, 0) / 260) * (rim_d > 0)
        out = out + rays[..., None] * GOLD * 0.5 * (1 - p)
        out = _bloom(out, 0.7, 0.7)
    return out


def smoke_through(A, B, p, seed=0, direction=1, color=None, density=1.0):
    """墨烟穿过：一团翻涌的 fbm 墨烟从一侧涌入、横贯画面再从另一侧散去；烟团最浓的中段内完成 A→B 切换
    （切换边界随烟团形状起伏，藏在烟里）。color 默认墨黑，传 PAPER 为白雾。"""
    hs, ws = H // 4, W // 4
    col = INK if color is None else np.asarray(color, np.float32)
    big = fbm(hs, ws * 3, seed, 70, 5)
    sh = int(p * ws * 0.8)                               # 烟本身也在流动
    f = big[:, ws - sh: 2 * ws - sh] if direction > 0 else big[:, ws + sh: 2 * ws + sh]
    xn = np.linspace(0, 1, ws, dtype=np.float32)[None, :]
    if direction < 0: xn = 1 - xn
    wob = (f - 0.5) * 0.7
    k = 3.4
    front = np.clip((p * k - xn - wob) * 3.2, 0, 1)                 # 烟头
    tail = np.clip(((p - 0.5) * k - xn - wob) * 3.2, 0, 1)          # 烟尾
    body = np.clip((f - 0.30) * 3.0, 0, 1) * 0.55 + 0.45
    D = np.clip(front * (1 - tail) * body * 1.15 * density, 0, 1)
    sw = np.clip(((p - 0.25) * k - xn - wob) * 3.2, 0, 1)           # 切换线位于烟团正中
    D = cv2.resize(D.astype(np.float32), (W, H)); sw = cv2.resize(sw.astype(np.float32), (W, H))
    out = _lerp(A, B, sw)
    return _lerp(out, np.broadcast_to(col, out.shape), D)


def zoom_through(A, B, p, center=(W / 2, H / 2), variant=None, seed=0, strength=1.0, inner=None):
    """推镜穿越：A 加速推近（径向模糊）→ 穿过 → B 从放大状态减速回到 1（径向模糊消退）。
    variant:
      None       纯推镜穿越 + 中点闪光
      'raindrop' 穿过一滴雨：中心水滴膨胀，滴内是 B 的倒影（上下颠倒+鱼眼），水滴充满画面后 B 正位
      'paper'    穿过纸片：纸片从中心飞向镜头铺满画面（白纸纤维），再从纸面推出 B
      'glint'    钻进刃口反光：中心一道横向锐利反光线展开成白场，再推出 B
    inner：raindrop 滴内显示的图（默认 B）。"""
    if variant == 'raindrop':
        x, y = _grid()
        d = np.sqrt((x - center[0]) ** 2 + (y - center[1]) ** 2)
        if p < 0.75:
            q = p / 0.75
            R = 30 + 1300 * ease_in(q, 2.6)
            pre = _radial_blur(_zoom(A, 1 + 0.25 * q, center), center, 0.12 * q)
            src = B if inner is None else inner
            k = 1.6 - 0.6 * q
            rn = np.clip(d / max(R, 1), 0, 1)
            fe = rn ** 0.6 * R / max(rn.max(), 1e-3)   # 鱼眼
            sx = center[0] + (x - center[0]) * (fe / np.maximum(d, 1)) * k
            sy = center[1] - (y - center[1]) * (fe / np.maximum(d, 1)) * k   # 上下颠倒 = 倒影
            refl = cv2.remap(src, sx.astype(np.float32), sy.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            refl = refl * 0.85 + 0.05
            m = np.clip((R - d) / 2, 0, 1)
            out = _lerp(pre, refl, m)
            rim = np.exp(-((d - R) / 3) ** 2) * 0.7 + np.exp(-(((x - center[0] + R * 0.35) ** 2 + (y - center[1] + R * 0.4) ** 2) / (R * 0.12 + 2) ** 2)) * 0.8
            return out + rim[..., None] * np.array([0.9, 0.95, 1.0], np.float32)
        q = (p - 0.75) / 0.25        # 水滴充满后：B 正位、从轻微鱼眼放大回落
        return _radial_blur(_zoom(B, 1 + 0.15 * (1 - ease_out(q)), center), center, 0.08 * (1 - q))
    if variant == 'paper':
        if p < 0.5:
            q = p / 0.5
            base = _radial_blur(_zoom(A, 1 + 0.4 * ease_in(q)), center, 0.1 * q)
            s = 0.08 + 1.9 * ease_in(q, 2.2)
            pw, ph = W * s, H * s * 0.85
            rot = 25 * (1 - q)
            pap = np.zeros((H, W), np.float32)
            box = cv2.boxPoints(((center[0], center[1]), (pw, ph), rot))
            cv2.fillConvexPoly(pap, box.astype(np.int32), 1.0, cv2.LINE_AA)
            tex = PAPER * (0.92 + 0.08 * _noise(H, W, 3, seed + 2)[..., None])
            return _lerp(base, tex, pap)
        q = (p - 0.5) / 0.5
        tex = PAPER * (0.92 + 0.08 * _noise(H, W, 3, seed + 2)[..., None])
        out = _radial_blur(_zoom(B, 1.5 - 0.5 * ease_out(q)), center, 0.12 * (1 - q))
        return _lerp(tex, out, ease_io(min(1, q * 1.6)))
    if variant == 'glint':
        x, y = _grid()
        if p < 0.5:
            q = p / 0.5
            base = _radial_blur(_zoom(A, 1 + 0.6 * ease_in(q)), center, 0.15 * q)
            hgt = 2 + H * ease_in(q, 3)
            band = np.exp(-((y - center[1]) / hgt) ** 2) * np.exp(-((x - center[0]) / (W * (0.2 + 0.8 * q))) ** 2)
            line = np.exp(-((y - center[1]) / 2.5) ** 2) * (q < 0.9)
            return base + (band * 1.6 * q + line * 2)[..., None] * np.array([1, 0.98, 0.94], np.float32)
        q = (p - 0.5) / 0.5
        out = _radial_blur(_zoom(B, 1.4 - 0.4 * ease_out(q)), center, 0.15 * (1 - q))
        return _lerp(np.ones_like(out), out, ease_out(q, 2))
    if p < 0.5:
        q = p / 0.5; e = ease_in(q, 2.5)
        out = _radial_blur(_zoom(A, 1 + 1.5 * e * strength, center), center, 0.35 * e)
        return out + e ** 3 * 0.6
    q = (p - 0.5) / 0.5; e = 1 - ease_out(q, 3)
    out = _radial_blur(_zoom(B, 1 + 0.8 * e * strength, center), center, 0.3 * e)
    return out + e ** 3 * 0.6


def glitch_cut(A, B, p, seed=0, frames=8, ink=True):
    """水墨故障切：横向笔刷状条带在 A/B 之间错位撕裂（条带边缘是干笔纹理不是像素块），夹杂墨色拖影与纸白断裂，
    单色、无 RGB 分离（RGB 错位只在 typo.typewriter 的指定字上使用）。"""
    step = int(p * frames)
    r = _rng(seed * 131 + step)
    base = A if p < 0.5 else B
    other = B if p < 0.5 else A
    out = base.copy()
    inten = math.sin(math.pi * _c(p)) ** 0.6
    if inten < 0.05: return out
    nb = int(2 + 16 * inten)
    for _ in range(nb):
        y = int(r.integers(BAR, H - BAR - 10)); h = int(r.integers(6, 30 + 90 * inten))
        h = min(h, H - y)
        dx = int(r.normal(0, 120 * inten))
        src = other if r.random() < 0.45 else base
        band = np.roll(src[y:y + h], dx, 1)
        if ink:   # 条带边缘干笔纹理
            edge = _noise(h, W, 3, seed + y, ax=12, ay=1)
            m = np.clip((edge - 0.25) * 3, 0, 1)[..., None]
        else: m = 1
        out[y:y + h] = out[y:y + h] * (1 - m) + band * m
        if r.random() < 0.35:   # 墨色拖影
            sm = _noise(h, W, 2, seed + y + 7, ax=20, ay=1)
            k = np.clip((sm - 0.45) * 3, 0, 1)[..., None] * 0.85
            out[y:y + h] = out[y:y + h] * (1 - k) + INK * k
        if r.random() < 0.12:   # 纸白断裂细线
            out[y:y + 2] = PAPER
    if r.random() < 0.3 * inten:   # 偶发整帧错位
        out = np.roll(out, int(r.normal(0, 40)), 1)
    return out


def fade_black(A, B, p, hold=0.15, ink=False, seed=0):
    """淡出到黑再淡入（hold：中间纯黑占比）。ink=True：黑场以墨滴从中心晕开的方式到来。"""
    a = (1 - hold) / 2
    if ink and p < a:
        m = ink_bleed(A, np.zeros_like(A) + INK, p / a, seed=seed)
        return m
    if p < a: return A * (1 - ease_io(p / a))
    if p < a + hold: return np.zeros_like(A) + INK * 0
    return B * ease_io((p - a - hold) / a)


def split_slide(A, B, p, angle=90.0, center=(W / 2, H / 2), seam=True):
    """分屏反向平移：画面沿过 center 的直线（angle=90 竖分、0 横分、45 对角）分成两半，
    A 的两半沿分割线方向反向滑出，B 的两半从反方向滑入，接缝处一道细光。"""
    x, y = _grid()
    th = math.radians(angle); dv = np.array([math.cos(th), math.sin(th)]); nv = np.array([-dv[1], dv[0]])
    sd = (x - center[0]) * nv[0] + (y - center[1]) * nv[1]
    side = (sd > 0).astype(np.float32)
    e = ease_io(p)
    L = W * abs(dv[0]) + H * abs(dv[1])          # 画面沿分割线方向的投影长度 → A、B 首尾相接无黑缝
    out = np.zeros_like(A)
    for s_, sgn in ((1 - side, -1), (side, 1)):
        ta = dv * sgn * e * L; tb = ta - dv * sgn * L
        a_ = _zoom(A, 1, tx=ta[0], ty=ta[1])
        b_ = _zoom(B, 1, tx=tb[0], ty=tb[1])
        sx, sy = x - ta[0], y - ta[1]
        inA = ((sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)).astype(np.float32)
        out += _lerp(b_, a_, inA) * s_[..., None]
    if seam:
        g = np.exp(-(sd / 2) ** 2) * math.sin(math.pi * e)
        out += g[..., None] * np.array([1, 0.95, 0.88], np.float32) * 1.2
    return out


def freeze_glitch(A, B, p, seed=0, black_at=0.8, frames=10):
    """冻结帧 + 故障后切黑：A 定格（调用方传冻结帧），故障条逐渐加剧、去色、墨噪；black_at 处硬切黑（B=None）或切到 B。"""
    if p >= black_at:
        return np.zeros_like(A) if B is None else B.copy()
    q = p / black_at
    lum = (A * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
    fr = _lerp(A, np.repeat(lum, 3, -1), min(1, q * 1.5))
    out = glitch_cut(fr, fr, 0.15 + 0.35 * q, seed=seed + int(q * frames), frames=frames)
    if q > 0.6:   # 末段剧烈：整帧抽帧/变暗
        r = _rng(seed + int(q * frames * 3))
        if r.random() < 0.5: out = out * 0.35
        out = np.roll(out, int(r.normal(0, 60)), 0 if r.random() < 0.3 else 1)
    return out


TRANSITIONS = {
    'hard_cut_on_beat': hard_cut_on_beat, 'match_cut': match_cut, 'slash_wipe': slash_wipe, 'ink_bleed': ink_bleed,
    'whip_pan_blur': whip_pan_blur, 'flash_white': flash_white, 'flash_red': flash_red, 'paper_tear': paper_tear,
    'shatter': shatter, 'occlusion': occlusion, 'iris_moon': iris_moon, 'smoke_through': smoke_through,
    'zoom_through': zoom_through, 'glitch_cut': glitch_cut, 'fade_black': fade_black, 'split_slide': split_slide,
    'freeze_glitch': freeze_glitch,
    # 别名
    'spin_slash': lambda A, B, p, **kw: slash_wipe(A, B, p, circle=True, **kw),
    'cut': hard_cut_on_beat,
}


def transition(name, frA, frB, p, **kw):
    """统一入口。name 可写成 shots.json 里的写法，如 'slash_wipe(竖)'、'whip_pan_blur(上)'、'iris_moon(月为光圈)'——
    括号内的中文提示会被解析为常用参数（竖/横/对角/圆形/上下左右/旋转/穿过雨滴/纸片/刃口/日轮/收拢/松枝/枪林/人群…）。"""
    base, hint = name, ''
    if '(' in name:
        base, hint = name.split('(', 1); hint = hint.rstrip(')')
    base = base.strip()
    kw = dict(_parse_hint(base, hint), **kw)
    fn = TRANSITIONS[base]
    if frB is None and base not in ('freeze_glitch',):
        frB = np.zeros_like(frA)
    out = fn(frA, frB, float(np.clip(p, 0, 1)), **kw)
    return out.astype(np.float32)


def _parse_hint(base, h):
    kw = {}
    if not h: return kw
    if base == 'slash_wipe':
        if '圆' in h: kw['circle'] = True
        elif '竖' in h: kw['angle'] = 90 - 12
        elif '对角' in h or '斜' in h: kw['angle'] = -32
        elif '横' in h or '左→右' in h: kw['angle'] = -6
    elif base == 'whip_pan_blur':
        for k, v in (('上', 'up'), ('下', 'down'), ('左', 'left'), ('右', 'right'), ('旋', 'rotate')):
            if k in h: kw['direction'] = v
    elif base == 'zoom_through':
        if '雨' in h: kw['variant'] = 'raindrop'
        elif '纸' in h: kw['variant'] = 'paper'
        elif '刃' in h or '反光' in h or '刀身' in h: kw['variant'] = 'glint'
    elif base == 'iris_moon':
        if '日' in h: kw['sun'] = True
        if '收' in h or '朱红' in h: kw['mode'] = 'collapse'
    elif base == 'occlusion':
        for k, v in (('松', 'branch'), ('枝', 'branch'), ('枪', 'spear'), ('人', 'crowd'), ('士兵', 'crowd'), ('臂', 'blade'), ('旗杆', 'pillar'), ('纸卷', 'pillar'), ('坠石', 'pillar')):
            if k in h: kw['kind'] = v; break
    elif base == 'ink_bleed':
        if '白' in h: kw['white'] = True
    elif base == 'flash_red':
        if '1 帧' in h or '1帧' in h: kw['one_frame'] = True
    elif base == 'fade_black':
        if '墨' in h: kw['ink'] = True
    elif base == 'match_cut':
        if '线' in h or '地平线' in h or '刀身' in h or '横' in h: kw['shape'] = 'line'
    return kw


# ======================================================================== 镜头
def perlin1(x, seed=0):
    """1D 柏林噪声（梯度噪声），x 可为标量/数组，返回约 [-1,1]。"""
    x = np.asarray(x, np.float64)
    i0 = np.floor(x).astype(np.int64); f = x - i0
    def g(i):
        h = (i * 374761393 + seed * 668265263) & 0xffffffff
        h = (h ^ (h >> 13)) * 1274126177 & 0xffffffff
        return ((h & 0xffff) / 32767.5) - 1.0
    u = f * f * f * (f * (f * 6 - 15) + 10)
    return (g(i0) * f * (1 - u) + g(i0 + 1) * (f - 1) * u) * 2.0


def handheld(t, amp=10.0, freq=1.3, rot=0.4, seed=0):
    """手持抖动偏移 (dx, dy, drot)：两层柏林噪声（慢漂 + 细颤）。"""
    dx = perlin1(t * freq, seed) * amp + perlin1(t * freq * 4.3, seed + 7) * amp * 0.25
    dy = perlin1(t * freq * 0.9, seed + 3) * amp * 0.8 + perlin1(t * freq * 3.7, seed + 11) * amp * 0.2
    dr = perlin1(t * freq * 0.7, seed + 5) * rot
    return float(dx), float(dy), float(dr)


def ramp(u, kind='io', amt=0.6):
    """速度坡度：把线性进度 u 映射为带速度变化的进度。
    'io' 缓入缓出；'out' 快起慢收；'in' 慢起快收；'bullet' 中段慢动作（两端快）；'surge' 中段加速（两端慢）。"""
    u = _c(u)
    if kind == 'linear': return u
    if kind == 'io': return u * u * (3 - 2 * u)
    if kind == 'out': return 1 - (1 - u) ** 3
    if kind == 'in': return u ** 3
    if kind == 'bullet': return u + amt * math.sin(2 * math.pi * u) / (2 * math.pi)
    if kind == 'surge': return u - amt * math.sin(2 * math.pi * u) / (2 * math.pi)
    return u


def punch(t, beats_list, amt=0.05, decay=0.12):
    """鼓点冲击缩放倍率：最近已过节拍后 1+amt·exp(-Δt/decay)。"""
    if beats_list is None or len(beats_list) == 0: return 1.0
    b = np.asarray(beats_list)
    i = np.searchsorted(b, t) - 1
    if i < 0: return 1.0
    return 1.0 + amt * math.exp(-(t - b[i]) / decay)


@lru_cache(1)
def _beats():
    return np.load(__import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/analysis.npz')['beats'].astype(np.float64)


def camera(fr, t, spec):
    """镜头运动。fr 建议比输出大（如 1.2× 预渲染层）或接受 BORDER_REFLECT 边缘；输出 1920×1080。
    spec 字段（都可选）：
      t0, t1            镜头起止（秒），u=(t-t0)/(t1-t0)
      ease              'linear'|'io'|'out'|'in'|'bullet'|'surge'（速度坡度 ramp），ramp_amt
      zoom=(z0,z1)      推拉（>1 推近）
      pan=(x0,y0,x1,y1) 摇移：视点中心相对画面中心的偏移（px，正 x 看向右）
      rot=(r0,r1)       旋转（度）
      shake=amp         手持抖动幅度（px），shake_freq（Hz，默认 1.3），shake_rot（度），seed
      whip=(tw, dur, dx, dy)  甩镜：在 tw 时刻 dur 秒内额外平移 (dx,dy) px，带方向运动模糊
      punch=True|list   鼓点冲击：True=用 analysis 节拍，list=指定时间；punch_amt(0.05), punch_decay(0.12), punch_every(1)
    返回 float32 帧。"""
    t0 = spec.get('t0', t); t1 = spec.get('t1', t0 + 1)
    u = ramp((t - t0) / max(1e-6, t1 - t0), spec.get('ease', 'io'), spec.get('ramp_amt', 0.6))
    z0, z1 = spec.get('zoom', (1.0, 1.0))
    z = z0 + (z1 - z0) * u
    px0, py0, px1, py1 = spec.get('pan', (0, 0, 0, 0))
    cx = px0 + (px1 - px0) * u; cy = py0 + (py1 - py0) * u
    r0, r1 = spec.get('rot', (0.0, 0.0)); rot = r0 + (r1 - r0) * u
    seed = spec.get('seed', 0)
    if spec.get('shake'):
        dx, dy, dr = handheld(t, spec['shake'], spec.get('shake_freq', 1.3), spec.get('shake_rot', 0.3), seed)
        cx += dx; cy += dy; rot += dr
    mb = None
    if spec.get('whip'):
        tw, dur, wx, wy = spec['whip']
        q = (t - tw) / dur
        e = ease_io(q)
        cx += wx * e; cy += wy * e
        vel = 6 * q * (1 - q) if 0 < q < 1 else 0     # d(ease)/dq
        if vel > 0.05: mb = (wx * vel * 0.25, wy * vel * 0.25)
    pu = spec.get('punch')
    if pu:
        bl = _beats()[::spec.get('punch_every', 1)] if pu is True else pu
        z *= punch(t, bl, spec.get('punch_amt', 0.05), spec.get('punch_decay', 0.12))
    ih, iw = fr.shape[:2]
    s = z * max(W / iw, H / ih)
    vc = np.array([iw / 2 + cx / s, ih / 2 + cy / s])      # 视点中心（源图坐标）→ 移到输出中心
    M = cv2.getRotationMatrix2D((float(vc[0]), float(vc[1])), rot, s)
    M[:, 2] += np.array([W / 2, H / 2]) - vc
    out = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if mb is not None:
        out = _blur_dir(out, mb[0], mb[1])
    return out


__all__ = ['transition', 'TRANSITIONS', 'camera', 'handheld', 'perlin1', 'ramp', 'punch'] + list(TRANSITIONS)
