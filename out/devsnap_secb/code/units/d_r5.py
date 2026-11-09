"""units/d_r5.py — [D组] 第五棒新增素材（只供 units/sec_d_bridge.py 使用）。
- Plaques：悬挂的律令木牌（深色木纹 + 阴刻宋体字 + 麻绳），三层纵深、钟摆摇晃、可被一刀斩断（下半截坠落翻转）。
- bamboo_scroll：摊在湿石地上的巨幅竹简（竖条 + 竹节 + 两道编绳 + 墨书），取代副歌一同款的灰色正交字砖。
- iron_seal：「当」——黑铁官印整方压顶（铁面锻纹 + 斜面高光 + 阴刻金字），取代朱印（避开副歌一 S040 是非对错朱印）。
- zhupi：朱批——朱砂笔一笔写出 + 一道朱圈圈住（「理所应」）。
- crowd：水墨人群剪影（站/跪），做中景层。
全部无状态、按 t 计算。"""
import sys, math
ROOT = '/Users/sannian/Downloads/鬼屠OP_new/out/devsnap_secb/code'
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, cv2
import c1kit as K
import typo as T
import d_kit as D
from d_kit import W, H, BAR, INK, CINNABAR, GOLD

_C = {}


def cl(x): return K.clamp01(x)


def eo(x, k=3): return K.eout(x, k)


def _noise(seed, h, w, sx=1.0, sy=1.0):
    t = D._tile(seed)
    hh, ww = max(2, int(h / sy)), max(2, int(w / sx))
    return cv2.resize(cv2.resize(t, (ww % 512 or 512, hh % 512 or 512)) if (ww > 512 or hh > 512) else t[:hh, :ww], (w, h))


# ===================================================================== 律令木牌
PLAQUE_TXT = '律令规矩法度尊卑名分天条纲常忠孝礼义本分'


def wood_tex(w, h, seed, base=(0.20, 0.12, 0.07)):
    r = np.random.default_rng(seed)
    g = _noise(seed + 900, h, w, sx=0.35, sy=6.0)                       # 顺纹
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rings = 0.5 + 0.5 * np.sin(xx / (w * 0.06) + g * 9 + r.uniform(0, 6))
    v = 0.62 + 0.38 * g + 0.18 * rings
    col = np.array(base, np.float32) * r.uniform(0.85, 1.15)
    return np.clip(v[..., None] * col, 0, 1).astype(np.float32)


def plaque_img(ch, w, h, seed, gold=False):
    """木牌 RGBA（局部图）：木纹、四边斜面、阴刻宋体字（字底更暗、上缘高光）、顶端绳孔"""
    key = ('pl', ch, w, h, seed, gold)
    if key in _C: return _C[key]
    rgb = wood_tex(w, h, seed)
    A = np.zeros((h, w), np.float32)
    cv2.rectangle(A, (2, 2), (w - 3, h - 3), 1.0, -1)
    # 圭首：上端两角削斜
    cut = int(w * 0.22)
    tri = np.array([[0, 0], [cut, 0], [0, cut]], np.int32); cv2.fillPoly(A, [tri], 0)
    tri = np.array([[w, 0], [w - cut, 0], [w, cut]], np.int32); cv2.fillPoly(A, [tri], 0)
    A = cv2.GaussianBlur(A, (0, 0), 0.8)
    d = cv2.distanceTransform((A > 0.5).astype(np.uint8), cv2.DIST_L2, 3)
    bev = np.clip(1 - d / 7, 0, 1)
    gy, gx = np.gradient(cv2.GaussianBlur(np.clip(d / 7, 0, 1), (0, 0), 1.0))
    rgb = rgb * (1 + (gx * -2.5 + gy * -2.5)[..., None] * 0.9) * (1 - 0.25 * bev[..., None])
    # 阴刻字
    gs = int(w * 0.78)
    a = T.glyph(ch, 'serif_black', gs, False).astype(np.float32)
    L = np.zeros((h, w), np.float32)
    gh, gw = a.shape
    y0 = int(h * 0.42 - gh / 2); x0 = int(w / 2 - gw / 2)
    ys, xs = max(0, y0), max(0, x0); ye, xe = min(h, y0 + gh), min(w, x0 + gw)
    L[ys:ye, xs:xe] = a[ys - y0:ye - y0, xs - x0:xe - x0]
    up = np.clip(np.roll(L, 3, 0) - L, 0, 1)        # 字槽上壁阴影
    dn = np.clip(np.roll(L, -2, 0) - L, 0, 1)       # 下壁受光
    fill = np.array([0.85, 0.62, 0.25], np.float32) if gold else np.array([0.035, 0.025, 0.02], np.float32)
    rgb = rgb * (1 - L[..., None]) + fill * L[..., None] * (0.8 + 0.4 * rgb.mean(-1, keepdims=True) / 0.15)
    rgb = rgb * (1 - 0.6 * up[..., None]) + dn[..., None] * np.array([0.5, 0.42, 0.32], np.float32) * 0.6
    # 绳孔
    cv2.circle(rgb, (w // 2, int(h * 0.06)), max(3, w // 22), (0.01, 0.01, 0.01), -1, cv2.LINE_AA)
    _C[key] = (np.clip(rgb, 0, 1).astype(np.float32), A.astype(np.float32))
    return _C[key]


class Plaques:
    """悬挂木牌阵。每块：挂点 (x, ytop)、尺寸、深度 z（0 远 → 1 近），摆角 = A·sin(ωt+φ)。
    cut=(t_cut, (x0,y0), (x1,y1))：屏幕上的一道斩线；斩线穿过的牌在 t_cut 一分为二，下半截带初速坠落翻转。"""
    def __init__(self, seed=0, n_far=14, n_mid=8, n_near=3, ytop=60, cut=None, gold_chars=()):
        r = np.random.default_rng(seed)
        self.items = []
        layers = [(n_far, 0.25, (60, 90)), (n_mid, 0.6, (120, 160)), (n_near, 1.0, (230, 290))]
        for n, z, wr in layers:
            xs = np.linspace(-80, W + 80, n) + r.uniform(-50, 50, n)
            for k in range(n):
                w = int(r.uniform(*wr)); h = int(w * r.uniform(3.2, 3.9))
                ch = PLAQUE_TXT[r.integers(len(PLAQUE_TXT))]
                self.items.append(dict(x=float(xs[k]), y=float(ytop - r.uniform(0, 140) * (1.2 - z) + (1 - z) * 120), w=w, h=h, z=z, ch=ch,
                                       amp=r.uniform(2.5, 6.0) * (0.6 + 0.6 * z), om=r.uniform(1.6, 2.6), ph=r.uniform(0, 6.28),
                                       seed=int(r.integers(1e6)), rope=r.uniform(40, 160), gold=ch in gold_chars))
        self.items.sort(key=lambda d: d['z'])
        self.cut = cut

    def ang(self, it, t, boost=0.0):
        return (it['amp'] + boost) * math.sin(it['om'] * t + it['ph'])

    def _M(self, it, ang, dx=0.0, dy=0.0, extra_rot=0.0, piv=None):
        w, h = it['w'], it['h']
        px, py = (w / 2, 0.0) if piv is None else piv
        M = cv2.getRotationMatrix2D((px, py), ang + extra_rot, 1.0)
        M[0, 2] += it['x'] - px + dx; M[1, 2] += it['y'] + it['rope'] - py + dy
        return M

    def render(self, fr, t, light=1.0, rim=(0.62, 0.74, 1.0), rim_amt=1.0, flash=0.0, blur_far=2.5, blur_near=5.0,
               fog=(0.05, 0.055, 0.07), only=None, fall_t=None):
        out = fr
        for it in self.items:
            if only is not None and not only(it): continue
            rgb, A = plaque_img(it['ch'], it['w'], it['h'], it['seed'], it['gold'])
            z = it['z']
            pieces = [(rgb, A, 0.0, 0.0, 0.0, None)]
            boost = 0.0
            if self.cut is not None:
                tc, p0, p1 = self.cut
                # 牌的中线 x 处斩线的 y
                if p0[0] - 60 < it['x'] < p1[0] + 60 or p1[0] - 60 < it['x'] < p0[0] + 60:
                    yl = p0[1] + (p1[1] - p0[1]) * (it['x'] - p0[0]) / (p1[0] - p0[0] + 1e-6) - (it['y'] + it['rope'])
                    if 0.15 * it['h'] < yl < 0.9 * it['h'] and z > 0.4:
                        if t >= tc:
                            ang0 = self.ang(it, tc)
                            yy, xx = np.mgrid[0:it['h'], 0:it['w']].astype(np.float32)
                            slope = (p1[1] - p0[1]) / (p1[0] - p0[0] + 1e-6)
                            line = yl + (xx - it['w'] / 2) * slope
                            top = (yy < line).astype(np.float32); bot = 1 - top
                            age = t - tc
                            r = np.random.default_rng(it['seed'])
                            vx = r.uniform(-120, 120); spin = r.uniform(-260, 260)
                            gy = 0.5 * 2600 * age * age
                            pieces = [(rgb, A * top, 0.0, 0.0, 0.0, None),
                                      (rgb, A * bot, vx * age, gy + 40 * age, spin * age * age * 3 + ang0, (it['w'] / 2, yl))]
                            boost = 14 * math.exp(-age / 0.6)
            ang = self.ang(it, t, boost)
            for k, (prgb, pa, dx, dy, er, piv) in enumerate(pieces):
                if k == 1:
                    M = self._M(it, 0.0, dx, dy, er, piv)
                    M[0, 2] += piv[0]; M[1, 2] += piv[1]      # 下半截：绕断口旋转、保持断开时的位置
                else:
                    M = self._M(it, ang)
                Aw = cv2.warpAffine(pa, M, (W, H))
                if Aw.max() < 0.01: continue
                Cw = cv2.warpAffine(prgb, M, (W, H))
                bl = blur_far * (1 - z) / 0.75 if z < 0.5 else (blur_near if z > 0.9 else 0.0)
                if bl > 0.3:
                    Aw = cv2.GaussianBlur(Aw, (0, 0), bl); Cw = cv2.GaussianBlur(Cw, (0, 0), bl)
                lit = (0.45 + 0.75 * z) * light * (1 + 1.5 * flash)
                Cw = Cw * lit
                fogk = (1 - z) * 0.65
                Cw = Cw * (1 - fogk) + np.array(fog, np.float32) * fogk
                edge = cv2.GaussianBlur(np.clip(Aw - np.roll(np.roll(Aw, 4, 1), 3, 0), 0, 1), (0, 0), 1.5)
                Cw = Cw + edge[..., None] * np.array(rim, np.float32) * rim_amt * (0.4 + 0.8 * z) * (1 + 2 * flash)
                out = out * (1 - Aw[..., None]) + Cw * Aw[..., None]
                if k == 0:   # 绳
                    top_pt = M @ np.array([it['w'] / 2, 0, 1.0])
                    rope = np.zeros((H, W), np.float32)
                    cv2.line(rope, (int(top_pt[0]), int(top_pt[1])), (int(it['x']), -10), 1.0, max(1, int(3 * z)), cv2.LINE_AA)
                    if bl > 0.3: rope = cv2.GaussianBlur(rope, (0, 0), bl)
                    out = out * (1 - rope[..., None] * 0.85) + rope[..., None] * np.array([0.09, 0.08, 0.07], np.float32) * lit
        return out


# ===================================================================== 竹简地面
def bamboo_scroll(seed=4, slip_w=74, rows_h=2200, text=PLAQUE_TXT + '大局理所应当忍让上下'):
    """竹简大图（rows_h × W）：竖条竹片（每片略不同色、竹节、边缘暗缝）、两道横向编绳、每片一列墨书小字。返回 rgb, gap(缝/绳遮罩)"""
    key = ('bamboo', seed, slip_w, rows_h)
    if key in _C: return _C[key]
    r = np.random.default_rng(seed)
    Hh, Ww = rows_h, W + 400
    rgb = np.zeros((Hh, Ww, 3), np.float32)
    g = _noise(seed + 70, Hh, Ww, sx=0.5, sy=8.0)
    n = Ww // slip_w + 1
    gap = np.zeros((Hh, Ww), np.float32)
    Lt = T.Layer(Hh, Ww)
    for k in range(n):
        x0 = k * slip_w
        base = np.array([0.36, 0.30, 0.17], np.float32) * r.uniform(0.75, 1.1)
        sl = slice(x0, min(Ww, x0 + slip_w))
        xx = np.arange(sl.start, sl.stop) - x0
        prof = (0.75 + 0.25 * np.sin(np.pi * (xx + 0.5) / slip_w))[None, :, None]   # 竹片弧面
        rgb[:, sl] = base * prof * (0.75 + 0.45 * g[:, sl, None])
        cv2.line(gap, (x0, 0), (x0, Hh), 1.0, 5)
        for yk in np.arange(r.uniform(80, 400), Hh, r.uniform(500, 800)):     # 竹节
            cv2.line(rgb, (x0 + 4, int(yk)), (x0 + slip_w - 4, int(yk)), tuple(float(c) for c in base * 0.55), 3, cv2.LINE_AA)
        # 一列墨书
        y = r.uniform(30, 120)
        while y < Hh - 60:
            s = r.uniform(34, 46)
            T.place(Lt, text[r.integers(len(text))], x0 + slip_w / 2, y + s / 2, s, 'white', 'serif_b', alpha=r.uniform(0.6, 0.9), texture=False)
            y += s * 1.18
    for yc in (Hh * 0.18, Hh * 0.62):
        for k in range(0, Ww, 18):
            cv2.ellipse(gap, (k, int(yc + 4 * math.sin(k * 0.3))), (12, 5), 25, 0, 360, 0.8, -1, cv2.LINE_AA)
    gap = cv2.GaussianBlur(gap, (0, 0), 1.0)
    rgb = rgb * (1 - Lt.A[..., None] * 0.85)
    _C[key] = (rgb.astype(np.float32), np.clip(gap, 0, 1).astype(np.float32), Lt.A.astype(np.float32))
    return _C[key]


# ===================================================================== 黑铁官印「当」
def iron_seal_img(ch, size, seed=0):
    key = ('iron', ch, int(size), seed)
    if key in _C: return _C[key]
    s = int(size)
    pad = int(s * 0.1); n = s + 2 * pad
    A = np.zeros((n, n), np.float32)
    cv2.rectangle(A, (pad, pad), (pad + s, pad + s), 1.0, -1)
    nz = _noise(seed + 500, n, n, 1.5, 1.5)
    A = np.clip(cv2.GaussianBlur(A, (0, 0), 1.2) - (nz - 0.5) * 0.08 * (cv2.GaussianBlur(A, (0, 0), 6) < 0.98), 0, 1)
    d = cv2.distanceTransform((A > 0.5).astype(np.uint8), cv2.DIST_L2, 3)
    # 铁面：锻纹 + 锈斑
    fn = _noise(seed + 510, n, n, 0.6, 0.6)
    base = (0.07 + 0.06 * fn)[..., None] * np.array([0.95, 0.97, 1.05], np.float32)
    rust = np.clip((_noise(seed + 520, n, n, 2, 2) - 0.62) * 4, 0, 1)[..., None] * np.array([0.16, 0.06, 0.02], np.float32)
    rgb = base + rust
    bev = np.clip(1 - d / (s * 0.045), 0, 1)
    gy, gx = np.gradient(np.clip(d / (s * 0.045), 0, 1))
    rgb = rgb + np.clip(-gx - gy, 0, None)[..., None] * 0.9 * np.array([0.8, 0.85, 0.95], np.float32) - bev[..., None] * 0.02
    # 边框（阳线）
    fr_ = np.zeros((n, n), np.float32)
    m = int(s * 0.07); cv2.rectangle(fr_, (pad + m, pad + m), (pad + s - m, pad + s - m), 1.0, int(s * 0.025))
    # 阴刻金字
    g = T.glyph(ch, 'serif_black', int(s * 0.74), False).astype(np.float32)
    G = np.zeros((n, n), np.float32)
    gh, gw = g.shape; y0 = n // 2 - gh // 2; x0 = n // 2 - gw // 2
    G[max(0, y0):y0 + gh, max(0, x0):x0 + gw] = g[:min(gh, n - y0), :min(gw, n - x0)]
    G = np.maximum(G, fr_)
    gold = np.array([0.95, 0.70, 0.30], np.float32)
    gv = (0.75 + 0.35 * fn[..., None])
    up = np.clip(np.roll(G, 4, 0) - G, 0, 1)
    rgb = rgb * (1 - G[..., None]) + G[..., None] * gold * gv
    rgb = rgb * (1 - 0.8 * np.clip(np.roll(G, -4, 0) * (1 - G), 0, 1)[..., None]) + up[..., None] * 0.0
    _C[key] = (np.clip(rgb, 0, 2).astype(np.float32), A.astype(np.float32), G)
    return _C[key]


def iron_seal(fr, ch, cx, cy, size, t, th, rot=-3.0, seed=0):
    """黑铁官印自高处砸下（0.12s），落定瞬间：纸面压出暗环 + 金字闪一下 + 纸屑/墨尘冲出；之后整方静止压顶。"""
    if t < th - 0.12: return fr
    rgb, box, G = iron_seal_img(ch, size, seed)
    e = cl((t - (th - 0.12)) / 0.12)
    sc = 1.0 + 0.6 * (1 - e) ** 2 + 0.02 * math.exp(-max(0, t - th) / 0.08) * (t >= th)
    s = rgb.shape[0]
    M = cv2.getRotationMatrix2D((s / 2, s / 2), -rot, sc)
    M[0, 2] += cx - s / 2; M[1, 2] += cy - s / 2
    A = cv2.warpAffine(box, M, (W, H)) * (0.4 + 0.6 * e ** 0.5)
    C = cv2.warpAffine(rgb, M, (W, H))
    Gw = cv2.warpAffine(G, M, (W, H))
    sh = cv2.GaussianBlur(cv2.warpAffine(box, M, (W, H)), (0, 0), 10 + 50 * (1 - e))
    sh = np.roll(sh, (int(18 + 40 * (1 - e)), int(14 + 30 * (1 - e))), (0, 1))
    out = fr * (1 - 0.7 * sh[..., None] * (1 - A[..., None]))
    if t >= th:     # 压痕暗环
        ring = cv2.GaussianBlur(cv2.warpAffine(box, M, (W, H)), (0, 0), 22) - cv2.warpAffine(box, M, (W, H))
        out = out * (1 - np.clip(ring, 0, 1)[..., None] * 0.6 * (0.5 + 0.5 * math.exp(-(t - th) / 0.3)))
    out = out * (1 - A[..., None]) + C * A[..., None]
    if t >= th:
        fl = math.exp(-(t - th) / 0.12)
        out = out + (Gw * A)[..., None] * np.array([1.0, 0.8, 0.45], np.float32) * 0.9 * fl
    return out


# ===================================================================== 朱批
def zhupi(fr, ch, cx, cy, size, p, seed=0, ring=True, col=None):
    """朱砂笔一笔写出（brush_glyph，朱色乘纸）+ 写完一道朱圈（不闭合的飞白圆）"""
    col = CINNABAR if col is None else np.array(col, np.float32)
    if p <= 0: return fr
    pw = cl(p / 0.7)
    A = T.brush_glyph(ch, 'serif_black', size, pw, seed, 0.35, 0.6)
    L = T.Layer(); L.paste(A, cx, cy, tuple(col))
    out = fr * (1 - L.A[..., None] * 0.92) + L.A[..., None] * col * 0.92 * (fr / 0.93)
    if ring and p > 0.55:
        q = eo(cl((p - 0.55) / 0.45), 2)
        m = np.zeros((H, W), np.float32)
        r0 = size * 0.66
        a0 = -120 + seed * 23
        pts = [(cx + r0 * (1 + 0.04 * math.sin(i * 0.4)) * math.cos(math.radians(a0 + i * 6)),
                cy + r0 * 0.92 * math.sin(math.radians(a0 + i * 6))) for i in range(int(56 * q) + 1)]
        for i in range(len(pts) - 1):
            w = int(max(2, size * 0.05 * (1 - i / 70)))
            cv2.line(m, (int(pts[i][0]), int(pts[i][1])), (int(pts[i + 1][0]), int(pts[i + 1][1])), 1.0, w, cv2.LINE_AA)
        dry = np.clip(_noise(seed + 33, H, W, 0.4, 0.4) * 1.6 - 0.25, 0, 1)
        m = cv2.GaussianBlur(m, (0, 0), 1.0) * dry
        out = out * (1 - m[..., None] * 0.9) + m[..., None] * col * 0.9 * (out / 0.93)
    return out


# ===================================================================== 人群剪影
def crowd_mask(seed, n=120, y_far=560, y_near=840, s_far=26, s_near=90, kneel=0.0, x_rng=(-60, W + 60)):
    """一片人群剪影（头 + 肩 + 身），远小近大、远淡近浓；kneel>0 时低头跪伏。返回 (A 浓度 HxW)。"""
    key = ('crowd', seed, n, y_far, y_near, s_far, s_near, kneel, x_rng)
    if key in _C: return _C[key]
    r = np.random.default_rng(seed)
    A = np.zeros((H, W), np.float32)
    pts = sorted([(r.uniform(0, 1) ** 1.4, r.uniform(*x_rng)) for _ in range(n)])
    for z, x in pts:
        y = y_far + (y_near - y_far) * z; s = s_far + (s_near - s_far) * z
        dens = 0.35 + 0.65 * z
        m = np.zeros((H, W), np.float32)
        if kneel > 0:
            cv2.ellipse(m, (int(x), int(y)), (int(s * 0.55), int(s * 0.42)), 0, 180, 360, 1.0, -1, cv2.LINE_AA)
            cv2.circle(m, (int(x + s * 0.42), int(y - s * 0.12)), int(s * 0.17), 1.0, -1, cv2.LINE_AA)
            cv2.rectangle(m, (int(x - s * 0.55), int(y - 2)), (int(x + s * 0.55), int(y + s * 0.08)), 1.0, -1)
        else:
            lean = r.uniform(-0.12, 0.12) * s
            cv2.ellipse(m, (int(x + lean), int(y - s * 0.74)), (int(s * 0.15), int(s * 0.18)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)        # 头
            cv2.ellipse(m, (int(x + lean * 0.5), int(y - s * 0.50)), (int(s * 0.30), int(s * 0.13)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)  # 圆肩
            poly = np.array([[x - s * 0.29 + lean * 0.5, y - s * 0.5], [x + s * 0.29 + lean * 0.5, y - s * 0.5], [x + s * 0.36, y + s * 0.35], [x - s * 0.36, y + s * 0.35]], np.int32)
            cv2.fillPoly(m, [poly], 1.0, cv2.LINE_AA)
            m = cv2.GaussianBlur(m, (0, 0), 0.6 + 2.2 * (1 - z))
        A = np.maximum(A, m * dens)
    A = cv2.GaussianBlur(A, (0, 0), 1.2)
    _C[key] = A
    return A


# ===================================================================== 宫阙远影 / 淡墨远山
def palace_mask(seed=9, y_base=900, n=5, x_rng=(80, 1840), hmax=330):
    """一排宫阙剪影（台基 + 殿身 + 起翘的歇山顶），用作淡墨远景层。"""
    key = ('palace', seed, y_base, n, x_rng, hmax)
    if key in _C: return _C[key]
    r = np.random.default_rng(seed)
    A = np.zeros((H, W), np.float32)
    xs = np.linspace(x_rng[0], x_rng[1], n) + r.uniform(-60, 60, n)
    for k, x in enumerate(xs):
        main = (k == n // 2)
        w = r.uniform(220, 300) * (1.5 if main else 1.0); h = hmax * (1.0 if main else r.uniform(0.55, 0.8))
        yb = y_base - (40 if main else 0)
        cv2.rectangle(A, (int(x - w * 0.62), int(yb - h * 0.12)), (int(x + w * 0.62), int(yb)), 1.0, -1)             # 台基
        cv2.rectangle(A, (int(x - w * 0.42), int(yb - h * 0.55)), (int(x + w * 0.42), int(yb - h * 0.12)), 0.85, -1)  # 殿身
        ey = yb - h * 0.55
        pts = []
        for i in range(21):                                   # 起翘檐口
            u = i / 20 * 2 - 1
            pts.append((x + u * w * 0.78, ey - h * 0.10 * abs(u) ** 3))
        pts += [(x + w * 0.45, ey - h * 0.40), (x + w * 0.12, ey - h * 0.46), (x - w * 0.12, ey - h * 0.46), (x - w * 0.45, ey - h * 0.40)]
        cv2.fillPoly(A, [np.array(pts, np.int32)], 1.0, cv2.LINE_AA)
        if main:                                              # 重檐
            ey2 = ey - h * 0.46
            pts2 = [(x + (i / 14 * 2 - 1) * w * 0.5, ey2 - h * 0.07 * abs(i / 14 * 2 - 1) ** 3) for i in range(15)]
            pts2 += [(x + w * 0.22, ey2 - h * 0.28), (x - w * 0.22, ey2 - h * 0.28)]
            cv2.fillPoly(A, [np.array(pts2, np.int32)], 1.0, cv2.LINE_AA)
    A = cv2.GaussianBlur(A, (0, 0), 3)
    _C[key] = A
    return A


def mountains_mask(seed=5, y0=640, amp=150, layers=2):
    """淡墨远山（两层山脊，上实下虚）。返回 [(A, 浓度)]"""
    key = ('mtn', seed, y0, amp, layers)
    if key in _C: return _C[key]
    out = []
    x = np.arange(W, dtype=np.float32)
    for k in range(layers):
        r = np.random.default_rng(seed + k)
        ridge = y0 + k * 70 - amp * (0.6 * np.abs(np.sin(x / r.uniform(260, 380) + r.uniform(0, 6))) + 0.4 * np.abs(np.sin(x / r.uniform(90, 140) + r.uniform(0, 6))))
        yy = np.arange(H, dtype=np.float32)[:, None]
        A = np.clip((yy - ridge[None, :]) / 6, 0, 1) * np.clip(1 - (yy - ridge[None, :]) / (260 + 80 * k), 0, 1) ** 0.8
        out.append((cv2.GaussianBlur(A.astype(np.float32), (0, 0), 2 + 3 * (1 - k)), 0.10 + 0.08 * k))
    _C[key] = out
    return out
