"""paper.py · 美术·角色组 —— 纸人 / 纸糊巨影 / 提线木偶 / 皮影 / 纸片飞散 / 纸帘（skia 矢量绘制）

所有形状用 skia 路径光栅化（解析抗锯齿、剪刀剪纸毛边、MaskFilter 模糊做景深与投影），
材质在 numpy 里做：纸纤维、背光透光（叠层越多越暗）、受潮墨晕、燃烧（烧穿透明 + 焰线金红 + 焦边）。
帧级参数全部由 draw(fr, t, ...) 传入，无逐帧状态。坐标：角色单位 身高=100，原点脚底中心，y 向上。

PaperFigure   单个无面纸人（侧面/正面）：鞠躬 bow、受潮 wet、燃烧 burn、翻转 card、提线 strings、逆光 backlit
PaperCrowd    纸人队列：波浪鞠躬、雨中受潮、提线汇聚到一点、整排倒下
Marionette    提线木偶（style='paper' 纸扎 / 'piying' 皮影）：关节铆钉、丝线牵动手脚、cut 断线后瘫倒
PaperGiant    纸糊太上皇巨影：竹骨架透光 reveal、自脸部燃起烧穿 burn（背后空无一物）、烧边纸片飞散
PaperShreds   纸片飞散：3D 翻滚碎纸（逆光金边、景深模糊、可燃边），可整体飞向镜头
PaperCurtain  规则纸帘：竖条纸卷垂挂随风翻飞，可被刀线斩断（下半截飘落）
"""
import math
import numpy as np, cv2
import sk
from sk import skia
import fx2

W, H = 1920, 1080
RED = np.array([0.72, 0.06, 0.05], np.float32)
GOLD = np.array([1.0, 0.76, 0.40], np.float32)
PAPER = np.array([0.90, 0.87, 0.80], np.float32)
INK = np.array([0.03, 0.03, 0.035], np.float32)
EMBER = np.array([1.0, 0.55, 0.18], np.float32)      # 焰线（金与朱之间，仍属金红系）


# ============================================================== 工具
def raster(paths, blur=0.0, pad=4, clip=None):
    """路径（屏幕坐标）→ 局部覆盖率 (m float32, x0, y0)。clip=(W,H) 裁到画面。"""
    if not isinstance(paths, (list, tuple)): paths = [paths]
    r = None
    for P in paths:
        b = P.computeTightBounds()
        if b.isEmpty(): continue
        r = b if r is None else skia.Rect.MakeLTRB(min(r.left(), b.left()), min(r.top(), b.top()), max(r.right(), b.right()), max(r.bottom(), b.bottom()))
    if r is None: return None, 0, 0
    pad = pad + blur * 3
    x0 = int(math.floor(r.left() - pad)); y0 = int(math.floor(r.top() - pad))
    x1 = int(math.ceil(r.right() + pad)); y1 = int(math.ceil(r.bottom() + pad))
    if clip is not None:
        x0, y0 = max(x0, -200), max(y0, -200); x1, y1 = min(x1, clip[0] + 200), min(y1, clip[1] + 200)
    if x1 - x0 < 2 or y1 - y0 < 2: return None, 0, 0
    buf = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv_ = skia.Surface(buf, colorType=skia.kAlpha_8_ColorType, alphaType=skia.kPremul_AlphaType).getCanvas()
    cv_.translate(-x0, -y0)
    p = skia.Paint(AntiAlias=True)
    if blur > 0: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, float(blur)))
    for P in paths: cv_.drawPath(P, p)
    return buf.astype(np.float32) * (1 / 255.), x0, y0

def comp(fr, m, x0, y0, col, alpha=1.0, add=None):
    """把局部覆盖 m 与颜色 col (h,w,3 或 3) 合成到 fr；add=局部加色层 (h,w,3)。"""
    h, w = m.shape; Hh, Ww = fr.shape[:2]
    xa, ya = max(0, x0), max(0, y0); xb, yb = min(Ww, x0 + w), min(Hh, y0 + h)
    if xb <= xa or yb <= ya: return fr
    sl = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    a = (m[sl] * alpha)[..., None]
    c = col[sl] if np.ndim(col) == 3 else np.asarray(col, np.float32)
    fr[ya:yb, xa:xb] = fr[ya:yb, xa:xb] * (1 - a) + c * a
    if add is not None: fr[ya:yb, xa:xb] += add[sl]
    return fr

def jag(pts, step=2.0, amp=0.35, seed=0, closed=True):
    """把多边形加密并沿法向加细碎抖动 → 剪刀剪纸的毛边。"""
    p = np.asarray(pts, float); rng = np.random.default_rng(seed)
    if closed: p = np.vstack([p, p[:1]])
    out = []
    for a, b in zip(p[:-1], p[1:]):
        L = np.hypot(*(b - a)); n = max(1, int(L / step))
        for i in range(n): out.append(a + (b - a) * i / n)
    out = np.array(out)
    d = np.roll(out, -1, 0) - np.roll(out, 1, 0); nn = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
    return out + nn * rng.normal(0, amp, (len(out), 1))

def xform(pts, M):
    p = np.asarray(pts, float).reshape(-1, 2); return p @ M[:, :2].T + M[:, 2]

def _aff(x, y, s, rot=0.0, sx=1.0, flip=False):
    c, si = math.cos(math.radians(rot)), math.sin(math.radians(rot)); f = -1.0 if flip else 1.0
    # 单位(u,v) → 先横向 sx*f，再旋转（v 向上），再 y 取反到屏幕
    A = np.array([[c, -si], [si, c]]) @ np.diag([sx * f, 1.0])
    return np.array([[s * A[0, 0], s * A[0, 1], x], [-s * A[1, 0], -s * A[1, 1], y]])

def rot_about(pts, c, deg):
    a = math.radians(deg); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (np.asarray(pts, float) - c) @ R.T + c

def paper_tex(h, w, x0=0, y0=0, seed=21, scale=1.0):
    fib = fx2.tile(fx2.noise(512, seed, base=48, octaves=3), x0, y0, h, w)
    blot = fx2.tile(fx2.noise(512, seed + 1, base=6, octaves=4), x0 // 2, y0 // 2, h, w)
    return (0.82 + 0.12 * fib + 0.10 * blot).astype(np.float32)

def edge_of(m, w=2.0):
    return np.clip(m - cv2.GaussianBlur(m, (0, 0), w), 0, 1) * 2.2

def burn_field(m, x0, y0, origin, radius, prog, seed=5, rough=0.35):
    """燃烧场：返回 keep(保留), ember(焰线), char(焦边)。origin 屏幕坐标，radius 烧满所需半径（像素）。"""
    h, w = m.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.hypot(xx + x0 - origin[0], yy + y0 - origin[1]) / max(radius, 1)
    nz = fx2.tile(fx2.noise(512, seed, base=9, octaves=5), x0, y0, h, w)
    f = d + (nz - 0.5) * rough * 2
    th = prog * (1 + rough) - 0.02
    keep = np.clip((f - th) / 0.01, 0, 1)
    ember = np.exp(-((f - th) / 0.012) ** 2)
    char = np.clip(1 - (f - th) / 0.06, 0, 1) * keep
    return keep, ember, char


# ============================================================== 纸人
class PaperFigure:
    """单个无面纸人（纸扎）。
    PaperFigure(seed=0, view='side'|'front', cheeks=True)
    draw(fr, x, y, height, t=0, bow=0, sway=1, wet=0, burn=0, burn_origin=(0,0.9) 相对(0=脚,1=头), card=0(度，绕竖轴翻转),
         tilt=0(度，整体倾倒), flip=False, light='back'|'front', light_color=GOLD, rim=1, alpha=1, blur=0(景深px),
         strings=None 或 (x,y) 控制点, string_color=RED, ink=0(墨染整体变灰))
    返回 (fr, info)  info: head/hands 屏幕坐标、bbox。"""
    def __init__(self, seed=0, view='side', cheeks=True):
        self.seed = seed; self.view = view; self.cheeks = cheeks
        r = np.random.default_rng(seed); self.r = r
        j = lambda pts, a=0.28: jag(pts, 1.6, a, seed=int(r.integers(1e9)))
        if view == 'side':     # 侧面朝右
            self.lower = j([(-7, 50), (7, 50), (9, 30), (13, 3), (15, 0), (-12, 0), (-10, 22)])
            self.upper = j([(-6.5, 49), (6.5, 49), (6, 66), (5, 79), (0, 81.5), (-6, 79), (-7.5, 64)])
            self.sleeve = j([(-1, 79), (5.5, 78), (10, 64), (14, 50), (13, 45.5), (5.5, 46), (2, 58), (-3, 70)])
            self.head = (1.2, 89.0, 7.6)
            self.hand = (13.0, 47.0)
        else:
            self.lower = j([(-10, 50), (10, 50), (13, 28), (17, 0), (-17, 0), (-13, 28)])
            self.upper = j([(-10, 49), (10, 49), (12.5, 76), (6, 81), (-6, 81), (-12.5, 76)])
            self.sleeve = np.vstack([j([(-12.5, 77), (-6, 78), (-9, 58), (-12, 44), (-20, 44), (-19, 56)]), [[np.nan, np.nan]],
                                     j([(12.5, 77), (6, 78), (9, 58), (12, 44), (20, 44), (19, 56)])])
            self.head = (0.0, 89.5, 8.0)
            self.hand = (-16.0, 45.0)
        self.hinge = np.array([0.0, 49.0])

    def _paths(self, M, bow, sway_a):
        def P(poly, deg=0.0):
            parts = []
            seg = []
            for q in poly:
                if np.isnan(q[0]): parts.append(np.array(seg)); seg = []
                else: seg.append(q)
            parts.append(np.array(seg))
            out = skia.Path()
            for s in parts:
                if len(s) < 3: continue
                if deg: s = rot_about(s, self.hinge, deg)
                out.addPoly(sk._pts(xform(s, M)), True)
            return out
        deg = -bow * (80 if self.view == 'side' else 0) + sway_a
        up = P(self.upper, deg); sl = P(self.sleeve, deg)
        hc = np.array(self.head[:2]); r = self.head[2]
        if self.view == 'front' and bow > 0:            # 正面：上身向镜头折下 → 竖向压缩
            k = math.cos(bow * 1.2)
            Mup = M.copy()
            def sq(pts): p = np.array(pts, float); p[:, 1] = self.hinge[1] + (p[:, 1] - self.hinge[1]) * k; return p
            up = skia.Path(); up.addPoly(sk._pts(xform(sq(self.upper), M)), True)
            sl = skia.Path()
            for s in np.split(self.sleeve, np.where(np.isnan(self.sleeve[:, 0]))[0]):
                s = s[~np.isnan(s[:, 0])]
                if len(s) > 2: sl.addPoly(sk._pts(xform(sq(s), M)), True)
            hc = np.array([hc[0], self.hinge[1] + (hc[1] - self.hinge[1]) * k - 3 * bow]); r = r * (1 + 0.15 * bow)
        else:
            hc = rot_about(hc[None], self.hinge, deg)[0]
        hp = xform(hc[None], M)[0]; rs = r * math.hypot(M[0, 0], M[1, 0])
        hpath = skia.Path()
        hj = jag([(hc[0] + r * math.cos(a), hc[1] + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 28, endpoint=False)], 1.4, 0.18, seed=self.seed)
        hpath.addPoly(sk._pts(xform(hj, M)), True)
        hand = rot_about(np.array([self.hand]), self.hinge, deg)[0] if self.view == 'side' else np.array(self.hand)
        return P(self.lower), up, sl, hpath, hp, rs, xform(hand[None], M)[0], deg

    def draw(self, fr, x, y, height, t=0.0, bow=0.0, sway=1.0, wet=0.0, burn=0.0, burn_origin=(0.0, 0.9), card=0.0, tilt=0.0,
             flip=False, light='back', light_color=GOLD, rim=1.0, alpha=1.0, blur=0.0, strings=None, string_color=RED, ink=0.0,
             string_alpha=1.0):
        s = height / 100.0
        sx = math.cos(math.radians(card))
        if abs(sx) < 0.03: return fr, {}
        sway_a = sway * 2.0 * math.sin(t * 1.7 + self.seed)
        M = _aff(x, y, s, rot=tilt, sx=sx, flip=flip)
        low, up, sl, hd, hp, rs, hand, deg = self._paths(M, bow, sway_a)
        mL, x0, y0 = raster([low, up, sl, hd], blur=blur, pad=6)
        if mL is None: return fr, {}
        h, w = mL.shape
        def loc(P):
            b = np.zeros((h, w), np.uint8)
            c = skia.Surface(b, colorType=skia.kAlpha_8_ColorType, alphaType=skia.kPremul_AlphaType).getCanvas(); c.translate(-x0, -y0)
            c.drawPath(P, skia.Paint(AntiAlias=True)); return b.astype(np.float32) / 255.
        m_up, m_sl = loc(up), loc(sl)
        layers = loc(low) + m_up + m_sl + loc(hd)                     # 叠层数（透光用）
        tex = paper_tex(h, w, x0, y0, seed=self.seed + 21)
        back = 1.0 if light == 'back' else 0.0
        if sx < 0: back = 1 - back                                  # 翻到背面
        lc = np.asarray(light_color, np.float32)
        trans = np.exp(-0.42 * np.clip(layers - 1, 0, 3))           # 叠层越多越暗
        col_back = (PAPER * 0.55 + lc * 0.55)[None, None] * (tex * trans)[..., None] * (0.55 + 0.45 * abs(sx))
        col_front = PAPER[None, None] * (tex * (0.62 + 0.25 * abs(sx)) * (0.75 + 0.25 * trans))[..., None]
        col = col_back * back + col_front * (1 - back)
        # 衣褶折痕：袖与身交界暗线
        e_sl = edge_of(m_sl, 1.2) * m_up
        col = col * (1 - 0.35 * np.clip(e_sl, 0, 1))[..., None]
        if self.cheeks and abs(sx) > 0.3 and bow < 0.6:             # 纸扎人的两团腮红
            ck = np.zeros((h, w), np.float32)
            off = [(0.42, -0.38)] if self.view == 'side' else [(-0.5, -0.36), (0.5, -0.36)]
            for ox, oy in off:                                       # 腮红：大而淡的晕
                cx, cy = hp[0] + ox * rs * (-1 if flip else 1) * sx - x0, hp[1] - oy * rs - y0
                cv2.circle(ck, (int(cx * 4), int(cy * 4)), int(rs * 0.30 * 4), 1.0, -1, cv2.LINE_AA, 2)
            ck = cv2.GaussianBlur(ck, (0, 0), max(0.8, rs * 0.16)) * mL * 0.55
            col = col * (1 - ck[..., None]) + RED * 1.1 * ck[..., None]
        # 受潮：自上而下墨晕
        if wet > 0:
            nz = fx2.tile(fx2.noise(512, self.seed + 3, base=7, octaves=5), x0, y0, h, w)
            yy = (np.arange(h, dtype=np.float32)[:, None] + y0 - (y - height)) / height
            f = nz * 0.7 + yy * 0.5
            wm = np.clip((wet * 1.3 - f) / 0.12, 0, 1)
            wm = np.maximum(wm, cv2.GaussianBlur(wm, (0, 0), 0.5)[::1] * 0)
            run = cv2.blur(wm, (1, int(max(3, height * 0.08)))) * 0.6                # 往下淌
            wm = np.clip(wm + run, 0, 1) * mL
            col = col * (1 - wm[..., None] * 0.62) + (INK + 0.06) * wm[..., None] * 0.5
        if ink > 0: col = col * (1 - ink) + (INK + 0.05) * ink
        A = mL.copy(); add = None
        if burn > 0:
            org = (x + burn_origin[0] * height * sx, y - burn_origin[1] * height)
            keep, ember, char = burn_field(mL, x0, y0, org, height * 1.1, burn, seed=self.seed + 7)
            col = col * (1 - char[..., None] * 0.9)
            A = A * keep
            em = ember * mL
            add = em[..., None] * (EMBER * 1.6 + 0.4) + cv2.GaussianBlur(em, (0, 0), 3 + height * 0.01)[..., None] * (RED * 1.2 + GOLD * 0.5)
        if rim > 0:
            e = edge_of(mL, 1.0 + height * 0.004)
            col = col + (lc * (0.5 + 0.8 * back) * rim)[None, None] * e[..., None]
        fr = comp(fr, A, x0, y0, col, alpha, add=None if add is None else add * alpha)
        info = dict(head=tuple(hp), hand=tuple(hand), bbox=(x0, y0, x0 + w, y0 + h), top=(hp[0], hp[1] - rs))
        if strings is not None and string_alpha > 0:
            draw_strings(fr, [(hp[0], hp[1] - rs), tuple(hand)], strings, t, color=string_color, alpha=string_alpha * alpha, seed=self.seed)
        return fr, info


def draw_strings(fr, attach, control, t=0.0, color=RED, alpha=1.0, width=1.4, glow=0.6, seed=0, cut=None, cut_y=None):
    """提线：attach 点列 → control 点（或每根各自的控制点列表），轻微颤动；cut=0..1 断线（自 cut_y 断开、上下两截回弹飘落）。"""
    c = np.asarray(color, np.float32)
    ctrl = control if isinstance(control, (list, tuple)) and len(control) and isinstance(control[0], (list, tuple)) else [control] * len(attach)
    paths = []
    for i, (a, b) in enumerate(zip(attach, ctrl)):
        a = np.array(a, float); b = np.array(b, float)
        vib = math.sin(t * 13 + i * 1.7 + seed) * 2.0
        mid = (a + b) / 2 + np.array([vib, 0])
        if cut is not None and cut > 0:
            cy = cut_y if cut_y is not None else (a[1] + b[1]) / 2
            u = np.clip((cy - b[1]) / max(1e-3, a[1] - b[1]), 0.05, 0.95); pc = b + (a - b) * u
            k = cut
            lo_end = pc + np.array([math.sin(i * 2.1) * 40 * k, 120 * k * k])        # 下截坠落
            hi_end = pc + np.array([math.sin(i * 1.3) * 30 * k, -160 * k])            # 上截回弹
            P = skia.Path(); P.moveTo(*a); P.quadTo(*((a + lo_end) / 2 + np.array([20 * k, 0])), *lo_end); paths.append(P)
            P = skia.Path(); P.moveTo(*b); P.quadTo(*((b + hi_end) / 2 + np.array([-15 * k, 0])), *hi_end); paths.append(P)
        else:
            P = skia.Path(); P.moveTo(*a); P.quadTo(*mid, *b); paths.append(P)
    # 描边成填充后光栅化
    sp = skia.Paint(Style=skia.Paint.kStroke_Style, StrokeWidth=float(width), StrokeCap=skia.Paint.kRound_Cap)
    fill = []
    for P in paths:
        o = skia.Path(); sp.getFillPath(P, o); fill.append(o)
    m, x0, y0 = raster(fill, pad=8, clip=(W, H))
    if m is None: return fr
    g = cv2.GaussianBlur(m, (0, 0), 3.0) * glow
    col = np.broadcast_to(c * 1.2, m.shape + (3,)).astype(np.float32)
    add = g[..., None] * (c * 1.4 + GOLD * 0.15) * alpha
    return comp(fr, np.clip(m, 0, 1), x0, y0, col, alpha, add=add)


class PaperCrowd:
    """纸人队列（同向鞠躬 / 雨中受潮 / 提线 / 倒下）。
    PaperCrowd(seed=0, rows=3, cols=9, view='side', x_span=(220,1700), y_front=900, h_front=260, depth_scale=0.72)
    draw(fr, t, bow=0, wave=0.5, wet=0, strings=None(控制点 (x,y) 或 None), string_alpha=1, burn=0, fall=0,
         light='back', light_color=GOLD, dof=1.0, fog=(0.10,0.10,0.11), rim=1)
      bow 0..1 + wave：从队首到队尾依次鞠躬（「顾全大局」）；fall 0..1 整排向前倒下（卡片翻倒）。"""
    def __init__(self, seed=0, rows=3, cols=9, view='side', x_span=(220, 1700), y_front=900, h_front=260, depth_scale=0.72):
        rng = np.random.default_rng(seed)
        self.items = []
        for r in range(rows - 1, -1, -1):
            sc = depth_scale ** r
            for c in range(cols):
                x = x_span[0] + (x_span[1] - x_span[0]) * (c + 0.5 + rng.normal(0, 0.08)) / cols
                x = W / 2 + (x - W / 2) * (0.75 + 0.25 * sc)
                self.items.append(dict(fig=PaperFigure(seed * 100 + r * 31 + c, view=view), x=x, y=y_front - (1 - sc) * 260,
                                       h=h_front * sc * rng.uniform(0.94, 1.05), row=r, col=c, ph=rng.uniform(0, 6.28)))
        self.cols = cols

    def draw(self, fr, t, bow=0.0, wave=0.5, wet=0.0, strings=None, string_alpha=1.0, burn=0.0, fall=0.0, light='back',
             light_color=GOLD, dof=1.0, fog=(0.10, 0.10, 0.11), rim=1.0, x_off=0.0):
        infos = []
        for it in self.items:
            r = it['row']; d = it['col'] / max(1, self.cols - 1)
            b = float(np.clip(bow * (1 + wave) - wave * (1 - d), 0, 1))
            fl = float(np.clip(fall * (1 + wave) - wave * d, 0, 1))
            f = it['fig']
            fr, info = f.draw(fr, it['x'] + x_off, it['y'], it['h'], t, bow=b, wet=wet, burn=burn, tilt=-85 * fl ** 2,
                              light=light, light_color=light_color, blur=r * 1.6 * dof, rim=rim * (1 - 0.25 * r),
                              ink=0.18 * r, strings=strings, string_alpha=string_alpha * (1 - 0.3 * r))
            infos.append(info)
        return fr, infos


# ============================================================== 提线木偶 / 皮影
class Marionette:
    """提线木偶 / 皮影（关节式纸偶，侧面）。
    Marionette(seed=0, style='paper'|'piying')
    draw(fr, x, y, height, t, ctrl=None, lift=0.5, dance=1.0, cut=0.0, cut_t=None, strings=True, light_color=GOLD,
         rim=1.0, alpha=1.0, blur=0.0, flip=False, screen=None)
      ctrl   控制点（屏幕坐标），丝线汇聚处；None=头顶正上方 height*1.2
      lift   手被提起程度；dance 摆动幅度（被操纵感）
      cut    断线进度 0..1：丝线断开回弹，肢体失去支撑垂落、身体向前瘫倒
      style='piying'：皮影——半透明朱/金镂刻皮料、黑色勾边、关节铆钉，适合配 screen=(亮度) 的幕布背光；
      返回 (fr, info) info: joints 屏幕坐标、attach 丝线挂点。"""
    def __init__(self, seed=0, style='paper'):
        self.seed = seed; self.style = style
        rng = np.random.default_rng(seed)
        j = lambda pts, a=0.22: jag(pts, 1.4, a if style == 'paper' else 0.05, seed=int(rng.integers(1e9)))
        # 部件（局部坐标，关节在原点，沿 -y 方向下垂）
        self.parts = dict(
            torso=j([(-7, 0), (7, 0), (8.5, -26), (-8, -27)]),
            skirt=j([(-8, 0), (8, 0), (12, -24), (-10, -24)]),
            uarm=j([(-2.6, 1), (2.6, 1), (2.2, -15), (-2.2, -15)]),
            larm=j([(-2.2, 1), (2.2, 1), (4, -14), (-3.5, -15)]),
            thigh=j([(-3.2, 1), (3.2, 1), (2.8, -19), (-2.8, -19)]),
            shin=j([(-2.8, 1), (2.8, 1), (2.6, -18), (7, -20), (7, -22), (-3, -22)]),
            head=j([(4.5 * math.cos(a) + 1, 5.2 * math.sin(a) + 6) for a in np.linspace(0, 2 * math.pi, 22, endpoint=False)]),
        )
        rng2 = np.random.default_rng(seed + 1)
        self.holes = [(hx + (0.9 if (k % 2) else 0), hy, 0.75) for k, hy in enumerate(np.arange(-4, -23, -2.6))
                      for hx in np.arange(-4.5, 5, 1.9)]                                  # 皮影镂空：错位小孔阵（回纹感）

    def _pose(self, t, lift, dance, cut, cut_age):
        s = math.sin; d = dance; c = np.clip(cut, 0, 1)
        g = c ** 1.5                                    # 失去支撑
        A = dict(
            torso=s(t * 1.3) * 4 * d + 25 * g, skirt=0,
            uarmR=-30 - 100 * lift * (1 - g) + s(t * 2.1) * 25 * d * (1 - g) + 10 * g,
            larmR=-20 - 40 * lift * (1 - g) + s(t * 2.7 + 1) * 30 * d * (1 - g),
            uarmL=10 + 80 * lift * (1 - g) + s(t * 1.9 + 2) * 25 * d * (1 - g) - 10 * g,
            larmL=20 + 30 * lift * (1 - g) + s(t * 2.3 + 3) * 25 * d * (1 - g),
            thighR=s(t * 2.0) * 22 * d * (1 - g) - 70 * g, shinR=abs(s(t * 2.0)) * 30 * d * (1 - g) + 80 * g,
            thighL=-s(t * 2.0) * 22 * d * (1 - g) - 60 * g, shinL=abs(s(t * 2.0 + 1.5)) * 30 * d * (1 - g) + 70 * g,
            head=s(t * 1.1) * 8 * d + 35 * g,
            drop=g * 0.42, fall=g * 70,
        )
        return A

    def draw(self, fr, x, y, height, t=0.0, ctrl=None, lift=0.5, dance=1.0, cut=0.0, cut_t=None, strings=True, light_color=GOLD,
             rim=1.0, alpha=1.0, blur=0.0, flip=False, screen=None):
        s = height / 100.0; fs = -1 if flip else 1
        A = self._pose(t, lift, dance, cut, 0)
        def R(a): a = math.radians(a); return np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
        hip = np.array([0.0, 50.0 - 50 * A['drop']])
        ang_body = A['fall']
        Rb = R(-ang_body)
        P = {}; J = {}
        tor = (np.array(self.parts['torso']) * np.array([1, -1])) @ R(-ang_body + A['torso']).T + hip
        P['torso'] = [tor]
        neck = hip + R(-ang_body + A['torso']) @ np.array([0, 26.5])
        P['skirt'] = [np.array(self.parts['skirt']) @ R(-ang_body * 0.6).T + hip]
        P['head'] = [np.array(self.parts['head']) @ R(-ang_body + A['head']).T + neck]
        J['neck'] = neck; J['head_top'] = neck + R(-ang_body + A['head']) @ np.array([1, 11.5])
        sh = neck + R(-ang_body + A['torso']) @ np.array([0, -2.0])
        hands = []
        for side, sgn in (('L', -1), ('R', 1)):
            ua = A['uarm' + side]; la = A['larm' + side]
            P.setdefault('uarm', []).append(np.array(self.parts['uarm']) @ R(ua - ang_body).T + sh)
            el = sh + R(ua - ang_body) @ np.array([0, -15.0])
            P.setdefault('larm', []).append(np.array(self.parts['larm']) @ R(ua + la - ang_body).T + el)
            hd = el + R(ua + la - ang_body) @ np.array([0.3, -14.5]); hands.append(hd)
            J['elbow' + side] = el
            th = A['thigh' + side]; sn = A['shin' + side]
            hp_ = hip + R(-ang_body * 0.6) @ np.array([sgn * 1.5, -20.0])
            P.setdefault('thigh', []).append(np.array(self.parts['thigh']) @ R(th - ang_body * 0.3).T + hp_)
            kn = hp_ + R(th - ang_body * 0.3) @ np.array([0, -19.0])
            P.setdefault('shin', []).append(np.array(self.parts['shin']) @ R(th + sn - ang_body * 0.3).T + kn)
            J['knee' + side] = kn
        M = _aff(x, y, s, flip=flip)
        order = [('thigh', 0), ('shin', 0), ('uarm', 0), ('larm', 0), ('skirt', 0), ('torso', 0), ('head', 0), ('thigh', 1), ('shin', 1),
                 ('uarm', 1), ('larm', 1)]
        paths = []
        for name, i in order:
            q = P[name][i] if i < len(P[name]) else None
            if q is None: continue
            pp = skia.Path(); pp.addPoly(sk._pts(xform(q, M)), True); paths.append((name, pp, xform(q, M)))
        mAll, x0, y0 = raster([p for _, p, _ in paths], blur=blur, pad=8)
        if mAll is None: return fr, {}
        h, w = mAll.shape
        piy = self.style == 'piying'
        # 逐部件 painter 合成：每块各自着色、勾边，后画的压前
        layer = np.zeros((h, w, 3), np.float32); acc = np.zeros((h, w), np.float32)
        tex = paper_tex(h, w, x0, y0, seed=self.seed + 4)
        lc = np.asarray(light_color, np.float32)
        for k, (name, pp, q) in enumerate(paths):
            b = np.zeros((h, w), np.uint8)
            c = skia.Surface(b, colorType=skia.kAlpha_8_ColorType, alphaType=skia.kPremul_AlphaType).getCanvas(); c.translate(-x0, -y0)
            pa = skia.Paint(AntiAlias=True)
            if blur > 0: pa.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, float(blur)))
            c.drawPath(pp, pa)
            if piy and name in ('torso', 'skirt'):                       # 镂空花纹
                holes = skia.Path()
                ang = -ang_body + (A['torso'] if name == 'torso' else 0)
                for hx, hy, hr in self.holes:
                    hc = xform((np.array([[hx, hy * (1 if name == 'skirt' else -1)]]) @ R(ang).T + hip), M)[0]
                    rr = hr * s
                    holes.addPoly(sk._pts([(hc[0], hc[1] - rr * 1.3), (hc[0] + rr, hc[1]), (hc[0], hc[1] + rr * 1.3), (hc[0] - rr, hc[1])]), True)
                pc = skia.Paint(AntiAlias=True); pc.setBlendMode(skia.BlendMode.kClear); c.drawPath(holes, pc)
            m = b.astype(np.float32) / 255.
            if piy:
                base = (RED * 0.9 if name in ('torso', 'skirt', 'head') else GOLD * 0.75)
                col = base[None, None] * (0.55 + 0.45 * tex)[..., None]
                if screen is not None: col = col * (0.6 + 0.8 * screen)
            else:
                col = PAPER[None, None] * (tex * 0.75)[..., None] * (0.6 + 0.6 * lc / lc.max())
            e = edge_of(m, 0.8 + s * 0.4)
            col = col * (1 - (0.75 if piy else 0.35) * np.clip(e, 0, 1))[..., None]          # 勾边（皮影黑线）
            layer = layer * (1 - m[..., None]) + col * m[..., None]; acc = acc * (1 - m) + m
        # 关节铆钉（金）
        riv = np.zeros((h, w), np.float32)
        for key in ('neck', 'elbowL', 'elbowR', 'kneeL', 'kneeR'):
            p = xform(J[key][None], M)[0]
            cv2.circle(riv, (int((p[0] - x0) * 4), int((p[1] - y0) * 4)), int(max(1.5, 1.3 * s) * 4), 1.0, -1, cv2.LINE_AA, 2)
        p = xform(sh[None], M)[0]; cv2.circle(riv, (int((p[0] - x0) * 4), int((p[1] - y0) * 4)), int(max(1.5, 1.3 * s) * 4), 1.0, -1, cv2.LINE_AA, 2)
        layer = layer * (1 - riv[..., None]) + GOLD * 0.9 * riv[..., None]; acc = np.maximum(acc, riv)
        if rim > 0:
            layer = layer + lc * edge_of(acc, 1.0 + s * 0.3)[..., None] * 0.6 * rim
        fr = comp(fr, acc, x0, y0, layer, alpha)
        hs = [tuple(xform(hh[None], M)[0]) for hh in hands]; ht = tuple(xform(J['head_top'][None], M)[0])
        info = dict(attach=[ht] + hs, joints={k: tuple(xform(v[None], M)[0]) for k, v in J.items()}, bbox=(x0, y0, x0 + w, y0 + h))
        if strings:
            ctrl_ = ctrl if ctrl is not None else (x, y - height * 1.25)
            if piy:      # 皮影用操纵杆（黑色细杆）
                fr = draw_strings(fr, info['attach'][1:], [(hx + 30 * fs, hy + height * 0.7) for hx, hy in hs], t, color=INK + 0.05,
                                  width=2.2 * max(1, s * 0.5), glow=0.0, seed=self.seed)
            else:
                fr = draw_strings(fr, info['attach'], ctrl_, t, alpha=alpha, seed=self.seed, cut=cut if cut > 0 else None,
                                  cut_y=y - height * 1.05)
        return fr, info


# ============================================================== 纸糊巨影
class PaperGiant:
    """纸糊太上皇巨影（S116–S117）：以 rig.Emperor 的剪影为外形，纸面 + 竹骨架 + 透光 + 自脸部燃烧烧穿。
    PaperGiant(height=1500, seed=0, emperor=None, action='stand_backlit', phase=0.5, view='front')
      预计算一次剪影（静态姿态），逐帧只做轻微呼吸摆动 + 材质 + 燃烧。
    draw(fr, t, x=960, y=1180, reveal=1.0, burn=0.0, burn_origin=(0.5,0.12)(剪影内相对坐标，默认脸部),
         light_color=GOLD, backlight=1.0, sway=1.0, frame_lines=1.0, alpha=1.0, hole_color=None, flakes=True)
      reveal 0=纯黑剪影（像真人巨影）→ 1=看出是纸糊（纸面透光、竹骨架阴影、纸缝、边缘透光）
      burn   0..1 烧穿进度：焰线金红、焦边卷黑、烧穿处透明（露出背后 → 空无一物 / 或 hole_color 填色）
      返回 (fr, info) info: burn_front 点列（用于挂火星/纸片）、bbox。"""
    def __init__(self, height=1500, seed=0, emperor=None, action='stand_backlit', phase=0.5, view='front'):
        import rig
        em = emperor or rig.Emperor(seed, view=view)
        for f in range(24): em.pose(action, phase, f / 30, wind=80)
        Wc, Hc = int(height * 0.9), int(height * 1.06)
        z = np.zeros((Hc, Wc, 3), np.float32); o = np.ones((Hc, Wc, 3), np.float32)
        z, _ = em.draw(z, Wc / 2, Hc - 4, height, rim=0, lift=0.6, gold_trim=0.0)
        o, _ = em.draw(o, Wc / 2, Hc - 4, height, rim=0, lift=0.6, gold_trim=0.0)
        a = np.clip(1 - (o - z).mean(2), 0, 1)
        ys, xs = np.nonzero(a > 0.01)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        self.A = a[y0:y1, x0:x1].astype(np.float32)
        self.tone = (z[y0:y1, x0:x1].mean(2) / np.maximum(self.A, 1e-3)).astype(np.float32)
        self.foot = (float(Wc / 2 - x0), float(Hc - 4 - y0)); self.height = height; self.seed = seed
        h, w = self.A.shape
        # 竹骨架：横竖 + 斜撑（skia 描边），只在剪影内
        rng = np.random.default_rng(seed)
        P = skia.Path()
        for yy in np.arange(h * 0.04, h, h / 11): P.moveTo(0, yy + rng.normal(0, 4)); P.lineTo(w, yy + rng.normal(0, 6))
        for xx in np.arange(w * 0.1, w, w / 7): P.moveTo(xx + rng.normal(0, 4), 0); P.quadTo(xx + rng.normal(0, 20), h / 2, xx + rng.normal(0, 6), h)
        for k in range(6):
            a0 = rng.uniform(0, h); P.moveTo(0, a0); P.lineTo(w, a0 + rng.uniform(-0.5, 0.5) * h)
        fp = skia.Path(); skia.Paint(Style=skia.Paint.kStroke_Style, StrokeWidth=float(max(1.5, height * 0.0028))).getFillPath(P, fp)
        b = np.zeros((h, w), np.uint8)
        skia.Surface(b, colorType=skia.kAlpha_8_ColorType, alphaType=skia.kPremul_AlphaType).getCanvas().drawPath(fp, skia.Paint(AntiAlias=True))
        self.frame = (b.astype(np.float32) / 255.) * self.A
        # 纸缝（糊纸的接缝，细而淡）
        P2 = skia.Path()
        for yy in np.arange(h * 0.07, h, h / 16): P2.moveTo(0, yy); P2.lineTo(w, yy + rng.normal(0, 3))
        fp2 = skia.Path(); skia.Paint(Style=skia.Paint.kStroke_Style, StrokeWidth=1.2).getFillPath(P2, fp2)
        b2 = np.zeros((h, w), np.uint8)
        skia.Surface(b2, colorType=skia.kAlpha_8_ColorType, alphaType=skia.kPremul_AlphaType).getCanvas().drawPath(fp2, skia.Paint(AntiAlias=True))
        self.seam = (b2.astype(np.float32) / 255.) * self.A
        self.tex = paper_tex(h, w, 0, 0, seed=seed + 8)
        dist = cv2.distanceTransform((self.A > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
        self.thin = np.exp(-dist / max(6, height * 0.02)).astype(np.float32)          # 边缘薄 → 更透
        self.flakes = PaperShreds(seed + 3, n=70)

    def draw(self, fr, t, x=960, y=1180, reveal=1.0, burn=0.0, burn_origin=(0.5, 0.12), light_color=GOLD, backlight=1.0, sway=1.0,
             frame_lines=1.0, alpha=1.0, hole_color=None, flakes=True):
        A = self.A; h, w = A.shape
        ang = sway * 0.6 * math.sin(t * 0.7)
        M = cv2.getRotationMatrix2D((self.foot[0], self.foot[1]), ang, 1.0)
        warp = lambda a: cv2.warpAffine(a, M, (w, h), flags=cv2.INTER_LINEAR)
        Aw = warp(A); fw = warp(self.frame); sw = warp(self.seam); thin = warp(self.thin); tex = self.tex; tone = warp(self.tone)
        lc = np.asarray(light_color, np.float32)
        silh = (INK + tone[..., None] * np.array([0.10, 0.10, 0.11], np.float32))
        trans = (0.35 + 0.65 * thin) * tex * (1 - 0.5 * cv2.GaussianBlur(fw, (0, 0), 1.5) * frame_lines) * (1 - 0.25 * sw)
        glow_col = (PAPER * 0.35 + lc * 0.75)[None, None] * trans[..., None] * backlight
        col = silh * (1 - reveal) + (glow_col * 0.85 + silh * 0.25) * reveal
        x0 = int(round(x - self.foot[0])); y0 = int(round(y - self.foot[1]))
        Aout = Aw.copy(); add = None; info = dict(bbox=(x0, y0, x0 + w, y0 + h))
        if burn > 0:
            org = (x0 + burn_origin[0] * w, y0 + burn_origin[1] * h)
            keep, ember, char = burn_field(Aw, x0, y0, org, max(w, h) * 0.95, burn, seed=self.seed + 11, rough=0.28)
            # 焦边卷曲：焦黑带 + 内侧薄纸被烤得透亮
            col = col * (1 - char[..., None] * 0.92) + (lc * 0.6)[None, None] * (np.clip(char * 3, 0, 1) * (1 - char))[..., None] * 0.6
            em = ember * Aw
            if hole_color is not None:
                col = col * keep[..., None] + np.asarray(hole_color, np.float32) * (1 - keep)[..., None]
                Aout = Aw
            else:
                Aout = Aw * keep
            add = em[..., None] * (EMBER * 2.0 + 0.5) + fx2.blur_ds(em, 8 + self.height * 0.006)[..., None] * (RED * 1.6 + GOLD * 0.9)
            ys, xs = np.nonzero(em[::6, ::6] > 0.4)
            info['burn_front'] = np.stack([xs * 6 + x0, ys * 6 + y0], 1) if len(xs) else np.zeros((0, 2))
        fr = comp(fr, Aout, x0, y0, col, alpha, add=None if add is None else add * alpha)
        if burn > 0 and flakes and len(info.get('burn_front', [])):
            bf = info['burn_front']
            fr = self.flakes.draw(fr, t, emit=bf, burn=1.0, scale=self.height / 1500, amount=min(1.0, burn * 3))
        return fr, info


# ============================================================== 纸片飞散
class PaperShreds:
    """纸片飞散（3D 翻滚碎纸）。无状态：位置/姿态 = f(t - t0)。
    PaperShreds(seed=0, n=120, size=(18,60))
    draw(fr, t, t0=0, origin=(960,540), spread=(900,500), to_camera=0.0, gravity=180, wind=(60,0), burn=0.0,
         light_color=GOLD, backlit=1.0, dof=1.0, emit=None, scale=1.0, amount=1.0, text=False)
      origin/spread 起始区域（矩形中心与半宽高）；to_camera 0..1 朝镜头飞来（z 减小→放大、近处景深虚化）；
      burn>0 纸边带焰线与焦痕；emit=点列（如燃烧前沿）则纸片从这些点不断生成（循环）；backlit 逆光金边透光。"""
    def __init__(self, seed=0, n=120, size=(18, 60)):
        r = np.random.default_rng(seed); self.n = n; self.seed = seed
        self.shape = []
        for i in range(n):
            k = int(r.integers(4, 8)); ang = np.sort(r.uniform(0, 2 * math.pi, k)); rad = r.uniform(0.55, 1.0, k)
            pts = np.stack([np.cos(ang) * rad, np.sin(ang) * rad * r.uniform(0.5, 1.0)], 1)
            self.shape.append(jag(pts, 0.12, 0.025, seed=int(r.integers(1e9))))
        self.sz = r.uniform(*size, n); self.u = r.uniform(-1, 1, (n, 2)); self.z = r.uniform(0, 1, n)
        self.v = r.normal(0, 1, (n, 3)); self.ax = r.normal(0, 1, (n, 3)); self.ax /= np.linalg.norm(self.ax, axis=1, keepdims=True)
        self.w = r.uniform(2, 7, n) * r.choice([-1, 1], n); self.ph = r.uniform(0, 1, n); self.tone = r.uniform(0.75, 1.0, n)
        self.life = r.uniform(1.2, 2.6, n)

    def draw(self, fr, t, t0=0.0, origin=(960, 540), spread=(900, 500), to_camera=0.0, gravity=180, wind=(60, 0), burn=0.0,
             light_color=GOLD, backlit=1.0, dof=1.0, emit=None, scale=1.0, amount=1.0, text=False):
        lc = np.asarray(light_color, np.float32)
        F = sk.FloatSurface(H, W)
        items = []
        for i in range(int(self.n * amount)):
            if emit is not None:
                age = (t * 0.6 + self.ph[i] * self.life[i]) % self.life[i]
                e = emit[int(self.ph[i] * 9973) % len(emit)]
                px0, py0, z0 = e[0], e[1], 0.5 + 0.5 * self.z[i]
            else:
                age = t - t0
                if age < 0: continue
                px0 = origin[0] + self.u[i, 0] * spread[0]; py0 = origin[1] + self.u[i, 1] * spread[1]; z0 = 1.0 + self.z[i] * 1.5
            vx, vy, vz = self.v[i] * np.array([160, 120, 0.35])
            px = px0 + (vx + wind[0]) * age + 25 * math.sin(age * 3 + i)
            py = py0 + (vy - 60) * age + 0.5 * gravity * age * age * (0.4 if emit is None else -0.6) + wind[1] * age
            z = z0 - (to_camera * 0.95 * min(1.0, age / 1.6) * z0) + vz * age * 0.1
            z = max(0.06, z)
            persp = 1.0 / z
            if to_camera > 0:
                px = W / 2 + (px - W / 2) * persp ** 0.5 * 1.0; py = H / 2 + (py - H / 2) * persp ** 0.5
            s = self.sz[i] * scale * persp ** (0.9 if to_camera > 0 else 0.0) * (1 if emit is None else 0.5)
            th = self.w[i] * age + self.ph[i] * 6.28
            a = self.ax[i]; c, sn = math.cos(th), math.sin(th)
            Rm = np.array([[c + a[0] ** 2 * (1 - c), a[0] * a[1] * (1 - c) - a[2] * sn], [a[1] * a[0] * (1 - c) + a[2] * sn, c + a[1] ** 2 * (1 - c)]])
            nz = c + a[2] ** 2 * (1 - c)                        # 法线 z 分量 → 朝向
            q = self.shape[i] @ Rm.T * s + [px, py]
            if not (-200 < px < W + 200 and -200 < py < H + 200): continue
            fade = 1.0 if emit is None else math.sin(math.pi * age / self.life[i])
            items.append((z, q, nz, s, fade, i))
        items.sort(key=lambda it: -it[0])
        for z, q, nz, s, fade, i in items:
            facing = abs(nz)
            bright = (0.35 + 0.65 * facing) * self.tone[i]
            if backlit > 0:
                cc = PAPER * 0.4 * bright + lc * (0.75 * backlit) * (0.35 + 0.65 * (1 - facing) ** 0.5)
            else:
                cc = PAPER * 0.75 * bright
            if burn > 0: cc = cc * (1 - 0.25 * burn) + EMBER * 0.25 * burn
            blur = abs(z - 1.0) * 6 * dof if to_camera > 0 else 0.0
            P = skia.Path(); P.addPoly(sk._pts(q), True)
            F.path(P, color=tuple(np.clip(cc, 0, 4)), alpha=float(fade), blur=blur)
            if burn > 0 or backlit > 0:                         # 边：逆光金边 / 焰线
                ec = (EMBER * 1.8 if burn > 0 else lc * 1.4)
                F.path(P, color=tuple(np.clip(ec, 0, 4)), alpha=float(fade * (0.9 if burn > 0 else 0.5 * backlit)),
                       stroke=max(0.8, s * 0.06), blur=blur * 0.8 + 0.3)
        A = F.alpha(); C = F.rgb()
        fr[:] = fr * (1 - np.clip(A, 0, 1)[..., None]) + C
        if burn > 0:
            fr += fx2.blur_ds(np.clip(C.mean(2) - 0.6, 0, None), 6)[..., None] * (RED * 0.8 + GOLD * 0.4)
        return fr


# ============================================================== 纸帘
class PaperCurtain:
    """规则纸帘（S115/S118）：从画面上方垂下的竖条纸卷，晨风中翻飞；可被刀线斩断（下半截飘落、上半截回弹）。
    PaperCurtain(seed=0, n=14, x_span=(80,1840), top=40, length=(700,1000), width=(70,120), text=True)
    draw(fr, t, wind=1.0, light_color=GOLD, backlit=1.0, cuts=None, alpha=1.0, depth_blur=1.0)
      cuts: [(p0, p1, t_cut)] 刀线（屏幕两点）与斩断时刻；t>t_cut 时线以下部分脱落：旋转、飘落、淡出。
      每条纸有宋体律令竖排（思源宋，墨色、背光时透出）。"""
    def __init__(self, seed=0, n=14, x_span=(80, 1840), top=40, length=(700, 1000), width=(70, 120), text=True):
        r = np.random.default_rng(seed); self.seed = seed
        xs = np.linspace(x_span[0], x_span[1], n) + r.normal(0, 25, n)
        self.strips = [dict(x=float(xs[i]), top=top + r.uniform(-30, 20), L=r.uniform(*length), w=r.uniform(*width),
                            ph=r.uniform(0, 6.28), z=r.uniform(0, 1), tone=r.uniform(0.85, 1.0)) for i in range(n)]
        self.text = None
        if text:
            try:
                tf = skia.Typeface.MakeFromFile('/Users/sannian/Downloads/鬼屠OP_new/out/devsnap/code/fonts/NotoSerifSC.otf')
                self.font = skia.Font(tf, 40)
                RULES = '天理昭彰顾全大局理所应当法度森严尊卑有序上令下行'
                self.text = [''.join(r.choice(list(RULES), 14)) for _ in range(n)]
            except Exception:
                self.text = None

    def _strip_pts(self, s, t, wind, nseg=24):
        u = np.linspace(0, 1, nseg + 1)
        sway = wind * (np.sin(t * 1.4 + s['ph'] + u * 3.0) * 26 * u ** 1.3 + np.sin(t * 3.1 + s['ph'] * 2 + u * 7) * 6 * u)
        cx = s['x'] + sway; cy = s['top'] + u * s['L']
        twist = np.cos(t * 1.1 + s['ph'] + u * 4.0 * wind) * 0.45 + 0.55       # 翻飞：宽度随扭转变化
        wv = s['w'] * (0.25 + 0.75 * np.abs(twist))
        shade = 0.55 + 0.45 * np.sign(twist) * np.abs(twist) ** 0.5
        return np.stack([cx, cy], 1), wv, shade

    def draw(self, fr, t, wind=1.0, light_color=GOLD, backlit=1.0, cuts=None, alpha=1.0, depth_blur=1.0):
        lc = np.asarray(light_color, np.float32)
        F = sk.FloatSurface(H, W)
        order = sorted(range(len(self.strips)), key=lambda i: -self.strips[i]['z'])
        for i in order:
            s = self.strips[i]
            C, wv, shade = self._strip_pts(s, t, wind)
            blur = s['z'] * 3.0 * depth_blur
            pieces = [(C, wv, shade, 0.0, None)]
            if cuts:
                for (p0, p1, tc) in cuts:
                    if t < tc: continue
                    p0 = np.array(p0, float); p1 = np.array(p1, float); d = p1 - p0
                    side = (C[:, 0] - p0[0]) * d[1] - (C[:, 1] - p0[1]) * d[0]
                    sgn = np.sign(side); idx = np.nonzero(np.diff(sgn))[0]
                    if not len(idx): continue
                    k = idx[0] + 1; age = t - tc
                    up = (C[:k + 1], wv[:k + 1], shade[:k + 1], 0.0, None)
                    lo = (C[k:], wv[k:], shade[k:], age, C[k])
                    pieces = [up, lo]
                    break
            for (Cp, wp, sp_, age, piv) in pieces:
                if len(Cp) < 2: continue
                if piv is not None and age > 0:                 # 脱落段：绕断口旋转 + 下落 + 淡出
                    ang = (0.9 if i % 2 else -0.9) * age * (1.2 + 0.3 * math.sin(i))
                    Rm = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
                    Cp = (Cp - piv) @ Rm.T + piv + np.array([60 * age * (1 if i % 2 else -1), 300 * age * age + 80 * age])
                    fade = max(0.0, 1 - age / 1.8)
                else:
                    fade = 1.0
                d = np.gradient(Cp, axis=0); nn = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
                # 逐段四边形（带明暗），相邻重叠
                for j in range(len(Cp) - 1):
                    q = np.array([Cp[j] + nn[j] * wp[j] / 2, Cp[j + 1] + nn[j + 1] * wp[j + 1] / 2 + (Cp[j + 1] - Cp[j]) * 0.04,
                                  Cp[j + 1] - nn[j + 1] * wp[j + 1] / 2 + (Cp[j + 1] - Cp[j]) * 0.04, Cp[j] - nn[j] * wp[j] / 2])
                    sh = float(sp_[j])
                    cc = PAPER * (0.35 + 0.35 * max(0, sh)) * s['tone'] + lc * backlit * (0.25 + 0.45 * (1 - abs(sh)))
                    P = skia.Path(); P.addPoly(sk._pts(q), True)
                    F.path(P, color=tuple(np.clip(cc, 0, 3)), alpha=float(fade), blur=blur)
                # 纸边光
                Pe = skia.Path(); Pe.addPoly(sk._pts(np.vstack([Cp + nn * wp[:, None] / 2, (Cp - nn * wp[:, None] / 2)[::-1]])), True)
                F.path(Pe, color=tuple(lc * 1.2), alpha=float(0.35 * backlit * fade), stroke=1.4, blur=blur + 0.4)
                # 文字（竖排，沿纸条中心）
                if self.text is not None and fade > 0.05 and age == 0:
                    txt = self.text[i]; fs = float(np.mean(wp) * 0.42)
                    if fs >= 15:
                        self.font.setSize(fs)
                        tp = skia.Paint(AntiAlias=True); tp.setColor4f(skia.Color4f(0.05, 0.05, 0.06, float(0.6 * fade)))
                        if blur > 0.5: tp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, float(blur)))
                        n = len(Cp)
                        for cidx, ch in enumerate(txt):
                            u = 0.06 + cidx * fs * 1.15 / max(1, s['L'])
                            if u > 0.95: break
                            jj = min(n - 1, int(u * (n - 1)))
                            if abs(wp[jj]) < fs * 1.25: continue
                            F.cv.drawString(ch, float(Cp[jj, 0] - fs / 2), float(Cp[jj, 1] + fs * 0.35), self.font, tp)
        A = np.clip(F.alpha(), 0, 1); C = F.rgb()
        a = A[..., None] * alpha
        fr[:] = fr * (1 - a) + C * alpha
        return fr
