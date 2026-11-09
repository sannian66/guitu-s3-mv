"""units/c_trans.py — C 组自用转场（第三棒）。原则：中间帧必须同时带前后两镜的画面内容，不出现纯白/纯灰/纯黑/灰雾。
所有函数 (A, B, p, **kw) -> frame，A/B float32 (1080,1920,3)，p 0..1。"""
import math
import numpy as np, cv2

W, H = 1920, 1080


def _s(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-9), 0, 1); return t * t * (3 - 2 * t)


def _zoom(fr, z, c):
    M = np.float32([[z, 0, c[0] * (1 - z)], [0, z, c[1] * (1 - z)]])
    return cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def _radial(fr, c, amt, n=5):
    if amt <= 0.002: return fr
    acc = fr.copy()
    for i in range(1, n):
        acc += _zoom(fr, 1 + amt * i / n, c)
    return acc / n


def push(A, B, p, center=(W / 2, H / 2), z=0.35, blur=0.12):
    """推进穿越：A 向 center 加速推入（径向拖影），B 从 0.8 倍拉回 1.0；交叉区两镜内容都可见。"""
    e = p * p * (3 - 2 * p)
    a = _radial(_zoom(A, 1 + z * e, center), center, blur * e)
    b = _radial(_zoom(B, 0.82 + 0.18 * e, center), center, blur * (1 - e))
    # 亮部先透出（B 的亮处先出现），避免平均成灰
    lb = B.mean(-1, keepdims=True)
    m = np.clip((e - 0.5) * 2.2 + 0.5 + (np.clip(lb, 0, 1) - 0.3) * 0.6, 0, 1)
    return a * (1 - m) + b * m


def luma(A, B, p, invert=False, soft=0.18):
    """亮度擦除：B 先从 A 的亮处（电光/缺口/刀光）长出来，再吞掉暗部。"""
    la = np.clip(A.mean(-1, keepdims=True) / max(1e-3, float(np.percentile(A, 99.5))), 0, 1)
    la = cv2.GaussianBlur(la[..., 0], (0, 0), 6)[..., None]
    if invert: la = 1 - la
    th = 1.0 - p * (1 + soft * 2) + soft
    m = np.clip((la - th) / soft + 0.5, 0, 1)
    out = A * (1 - m) + B * m
    edge = np.clip(1 - np.abs(la - th) / soft, 0, 1) * (1 - abs(2 * p - 1))
    return out + edge * np.array([0.9, 0.95, 1.0], np.float32) * 0.35


def seam(A, B, p, y=None, col=(1.0, 0.72, 0.30), horizontal=True):
    """缝隙光：A 上一道金缝亮起并张开，缝里是 B（箱盖缝 → 闪电照亮的脸）。"""
    y = H / 2 if y is None else y
    g = _s(0.0, 1.0, p)
    half = (H * 0.6) * g ** 1.6
    yy = np.arange(H, dtype=np.float32)[:, None]
    d = np.abs(yy - y)
    m = np.clip((half - d) / 18 + 0.5, 0, 1)[..., None]
    out = A * (1 - m) + B * m
    line = np.exp(-((d - half) / (3 + 10 * g)) ** 2)[..., None] * (1 - g * 0.6)
    glow = np.exp(-((d - half) / 60) ** 2)[..., None] * 0.35 * (1 - g)
    return out + (line * 1.4 + glow) * np.asarray(col, np.float32)


def over(A, B, p, center=(W / 2, H / 3), col=(0.85, 0.9, 1.0)):
    """闪电过曝切（替代白闪）：A 末帧过曝 + 冷色，切到 B 过曝回落；峰值帧仍保留 B 的明暗结构（不是纯白）。"""
    if p < 0.5:
        k = p / 0.5
        fr = A * (1 + 1.2 * k) + 0.08 * k
    else:
        k = (1 - p) / 0.5
        fr = B * (1 + 1.4 * k) + 0.10 * k
    yy, xx = np.ogrid[0:H, 0:W]
    r = np.exp(-(((xx - center[0]) / 900.0) ** 2 + ((yy - center[1]) / 600.0) ** 2)).astype(np.float32)
    fr = fr + r[..., None] * np.asarray(col, np.float32) * 0.25 * (1 - abs(2 * p - 1))
    return np.minimum(fr, 1.6 + 0 * fr)


def whip(A, B, p, direction=1, dist=520):
    """甩镜（带内容）：A 朝 direction 甩出、B 从反向甩入，模糊长度随速度；中间帧仍看得到两镜的形体拖影。"""
    e = p * p * (3 - 2 * p)
    v = math.sin(math.pi * p)                     # 速度包络
    k = max(1, int(56 * v)) | 1

    def sh(fr, dx):
        M = np.float32([[1, 0, dx], [0, 1, 0]])
        fr = cv2.warpAffine(fr, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        return cv2.blur(fr, (k, 1)) if k > 1 else fr
    a = sh(A, direction * dist * e)
    b = sh(B, -direction * dist * (1 - e))
    m = float(_s(0.3, 0.7, p))
    return a * (1 - m) + b * m


def tip(A, B, p, center=(W / 2, H / 2), z=0.9, col=(0.9, 0.95, 1.0)):
    """第七棒：穿过刀尖光点——A 朝刀尖那点冷光加速推入，光点长成十字星芒；B 从光点处以圆形开口（软边、带冷辉环）
    放大铺开、径向拖影消退。中间帧两镜都在，光只占星芒/环，不出整白帧（zoom_through glint 中点是白卡）。"""
    e = p * p * (3 - 2 * p)
    a = _radial(_zoom(A, 1 + z * e, center), center, 0.18 * e)
    b = _radial(_zoom(B, 1.35 - 0.35 * e, center), center, 0.16 * (1 - e))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((xx - center[0]) ** 2 + (yy - center[1]) ** 2)
    R = 2400 * _s(0.30, 1.0, p) ** 1.7
    m = np.clip((R - d) / 90.0 + 0.0, 0, 1) if R > 1 else np.zeros_like(d)
    out = a * (1 - m[..., None]) + b * m[..., None]
    ring = np.exp(-((d - R) / 26.0) ** 2) * (R > 1) * (1 - p) * 1.2
    g = math.sin(math.pi * min(1.0, p / 0.7)) if p < 0.7 else 0.0           # 星芒先亮后收
    dx, dy = np.abs(xx - center[0]), np.abs(yy - center[1])
    star = (np.exp(-dy / 3.0) * np.exp(-dx / (900 * g + 1)) + np.exp(-dx / 3.0) * np.exp(-dy / (260 * g + 1))) * g
    core = np.exp(-(d / (40 + 120 * g)) ** 2) * g
    return out + (ring + star * 1.3 + core * 1.5)[..., None] * np.asarray(col, np.float32)


def dark_breath(fr, q):
    """吸气：压暗到 15%，只留高光（进副歌前 2–4 帧）"""
    l = fr.mean(-1, keepdims=True)
    return fr * (1 - 0.85 * q) + np.clip(l - 0.7, 0, 1) * fr * 0.8 * q


_NZ = {}
def _noise(key, sig, seed):
    if key not in _NZ:
        q = cv2.GaussianBlur(np.random.default_rng(seed).random((H // 2, W // 2)).astype(np.float32), (0, 0), sig)
        q = (q - q.min()) / (q.max() - q.min() + 1e-6)
        _NZ[key] = cv2.resize(q, (W, H))
    return _NZ[key]


def ink_crack(A, B, p, center=(W / 2, H / 2), seed=7, ink=(0.02, 0.018, 0.02), ember=(0.9, 0.22, 0.06)):
    """第十二棒（critic_C_r6 P2⑦ 白闪同质化）：墨裂——A 像一层干裂的墨皮，从 center 起裂成网（Voronoi 裂缝 + 噪声扭曲），
    缝里透出 B；裂片随后逐块剥落（按到中心距离 + 噪声先后），裂缝边缘是浓墨，缝心一丝朱红余烬。中间帧两镜都在，不提亮。"""
    key = ('ic', seed)
    if key not in _NZ:
        r = np.random.default_rng(seed)
        h2, w2 = H // 2, W // 2
        pts = np.stack([r.uniform(-50, w2 + 50, 90), r.uniform(-50, h2 + 50, 90)], 1).astype(np.float32)
        lab = np.zeros((h2, w2), np.int32); best = np.full((h2, w2), 1e9, np.float32); sec = best.copy()
        yy, xx = np.mgrid[0:h2, 0:w2].astype(np.float32)
        wn = _noise('icw', 18, seed + 1)[::2, ::2] * 40
        for i, (px, py) in enumerate(pts):
            d = np.sqrt((xx + wn - px) ** 2 + (yy - wn * 0.7 - py) ** 2)
            m1 = d < best
            sec = np.where(m1, best, np.minimum(sec, d)); best = np.where(m1, d, best); lab = np.where(m1, i, lab)
        crack = cv2.resize(sec - best, (W, H))                      # 到裂缝的距离（像素/2）
        cell_d = np.hypot(pts[:, 0] * 2 - center[0], pts[:, 1] * 2 - center[1])
        order = cell_d[lab] / 2400 + 0.12 * r.random(len(pts))[lab]
        _NZ[key] = (crack, cv2.resize(order.astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST))
    crack, order = _NZ[key]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dc = np.sqrt((xx - center[0]) ** 2 + (yy - center[1]) ** 2) / 2200
    grow = np.clip((p * 1.6 - dc) * 6, 0, 1)                         # 裂缝从中心长出去
    wid = 0.6 + 5.0 * p
    line = np.clip((wid - crack) / 1.2, 0, 1) * grow
    off = np.clip((p * 1.25 - 0.25 - order) * 8, 0, 1)                # 裂片剥落
    m = np.maximum(off, line * _s(0.15, 0.6, p))
    rim = np.clip((wid + 3 - crack) / 2.5, 0, 1) * grow * (1 - off)
    sh = cv2.GaussianBlur(off, (0, 0), 6)                              # 剥落的墨片在 B 上投一点阴影
    a = _zoom(A, 1 + 0.03 * p, center)
    b = B * (1 - 0.35 * np.clip(sh - off, 0, 1)[..., None])
    out = a * (1 - m[..., None]) + b * m[..., None]
    out = out * (1 - 0.85 * (rim * (1 - m))[..., None]) + (rim * (1 - m))[..., None] * np.asarray(ink, np.float32)
    emb = np.exp(-(crack / (0.8 + 0.8 * p)) ** 2) * grow * (1 - off) * (1 - p)
    return out + emb[..., None] * np.asarray(ember, np.float32) * 1.1


def paper_tear(A, B, p, angle=-12.0, seed=4, fiber=(0.93, 0.86, 0.72)):
    """第十二棒（critic_C_r6 P2⑦ glitch_cut 数码扫描线出戏）：纸撕——A 是一张纸，沿一条参差的斜线被撕开，
    上下两半各自错开、翻起一点（下半略暗 = 翻折背面），撕口是毛糙的纸纤维白边，缝里露出 B。"""
    e = p * p * (3 - 2 * p)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    n1 = _noise('pt1', 30, seed) - 0.5; n2 = _noise('pt2', 3, seed + 1) - 0.5
    d = (yy - H / 2) * ca - (xx - W / 2) * sa + 90 * n1[:, :] + 14 * n2           # 到撕线的有符号距离
    gap = 1400 * e ** 1.6
    up = d < -gap / 2; dn = d > gap / 2
    Mu = np.float32([[1, 0, -60 * e], [0, 1, -gap / 2 - 30 * e]]); Md = np.float32([[1, 0, 60 * e], [0, 1, gap / 2 + 30 * e]])
    Au = cv2.warpAffine(A, Mu, (W, H), borderMode=cv2.BORDER_REFLECT); Ad = cv2.warpAffine(A, Md, (W, H), borderMode=cv2.BORDER_REFLECT)
    out = B * _s(0.0, 0.4, p) + A * (1 - _s(0.0, 0.4, p)) * 0.4
    out = np.where(up[..., None], Au, out); out = np.where(dn[..., None], Ad * (1 - 0.25 * e), out)
    fu = np.clip(1 - np.abs(d + gap / 2) / (6 + 18 * np.clip(n2 + 0.5, 0, 1)), 0, 1)
    fd = np.clip(1 - np.abs(d - gap / 2) / (6 + 18 * np.clip(0.5 - n2, 0, 1)), 0, 1)
    fib = np.maximum(fu, fd) * (1 - _s(0.7, 1.0, p)) * (gap > 1)
    sh = np.exp(-np.abs(d - gap / 2 - 10) / 20) * (d > gap / 2) * e * 0.4
    out = out * (1 - sh[..., None])
    return out * (1 - fib[..., None]) + fib[..., None] * np.asarray(fiber, np.float32) * (0.9 + 0.2 * n2[..., None])


def bolt_split(A, B, p, x0=1100, seed=37, col=(0.80, 0.88, 1.0)):
    """第十二棒（白闪同质化）：雷劈开画面——一道竖向锯齿闪电从顶到底劈下，A 沿雷路向两侧裂开推走，B 从裂缝里展开；
    只有雷路本身发光（细芯 + 窄辉），整幅不提亮。"""
    r = np.random.default_rng(seed)
    ys = np.linspace(0, H, 24)
    xs = x0 + np.cumsum(r.normal(0, 38, 24)); xs -= (xs.mean() - x0)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    bx = np.interp(yy[:, 0], ys, xs)[:, None]
    reach = H * _s(0.0, 0.25, p)
    on = yy < reach
    dx = xx - bx
    e = _s(0.15, 1.0, p)
    half = 1300 * e ** 1.5
    m = (np.abs(dx) < half) & on
    shl = cv2.warpAffine(A, np.float32([[1, 0, -half], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    shr = cv2.warpAffine(A, np.float32([[1, 0, half], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    out = np.where((dx < 0)[..., None], shl, shr)
    out = np.where(m[..., None], B * (0.75 + 0.25 * e), out)
    out = np.where(on[..., None], out, A)
    glow = (np.exp(-np.abs(np.abs(dx) - half) / 3.0) * 1.4 + np.exp(-np.abs(np.abs(dx) - half) / 30.0) * 0.35) * on * (1 - _s(0.6, 1.0, p))
    return out + glow[..., None] * np.asarray(col, np.float32)


NAMES = dict(push=push, luma=luma, seam=seam, over=over, whip=whip, tip=tip, ink_crack=ink_crack, paper_tear=paper_tear, bolt_split=bolt_split)
