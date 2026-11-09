"""crowd.py · 美术·角色组 —— 军阵 / 群像

Army      五百重甲方阵：透视地面网格 + 深度分层景深 + 大气透视 + 甲光闪烁 + 旗帜随风 + 火把
          整体齐步（march）/ 举刀举枪（raise）/ 平枪冲锋（level）/ 跪地（kneel，可波浪传递）/ 向两侧分开让路（part）
Kneelers  跪地人群剪影（平民，长袍发髻）：跪 → 叩首，逐个波浪；逆光勾边

精灵管线：每种姿态在 __init__ 里以 2× 超采样画好（alpha / 明暗 / 金 / 朱 四通道 + 边缘光），逐帧只做
          缩放缓存 + 粘贴 + 每层一次景深模糊。帧级参数全部由 draw(t, ...) 给出，无状态。
坐标：世界单位米，x 右、y 上、z 远；相机 cam=dict(x,y,z,pitch,f) —— z 越小越靠前（dolly 推拉改 z）。
"""
import math
import numpy as np, cv2

W, H = 1920, 1080
RED = np.array([0.72, 0.06, 0.05], np.float32)
GOLD = np.array([1.0, 0.76, 0.40], np.float32)
INK = np.array([0.028, 0.028, 0.034], np.float32)
COLD = np.array([0.80, 0.86, 1.0], np.float32)

UNIT = 3.4          # 精灵：每 1 身高单位（身高=100）的像素
SS = 2              # 超采样


# ============================================================== 2D 绘制小工具（超采样画布）
class _FigCV:
    """旧版 cv2 光栅（保留作前后对比）。"""
    def __init__(self, wu, hu, ox, oy):
        """wu,hu 画布单位尺寸；(ox,oy)=原点（脚底中心）在画布单位坐标中的位置"""
        self.k = UNIT * SS; self.ox, self.oy = ox, oy
        self.h, self.w = int(hu * self.k), int(wu * self.k)
        self.A = np.zeros((self.h, self.w), np.float32)   # 覆盖
        self.T = np.zeros((self.h, self.w), np.float32)   # 明暗 0 墨 .. 1 亮甲片
        self.G = np.zeros((self.h, self.w), np.float32)   # 金
        self.R = np.zeros((self.h, self.w), np.float32)   # 朱
        self.anchors = {}

    def P(self, p):
        p = np.asarray(p, float).reshape(-1, 2)
        return np.round(np.stack([(p[:, 0] + self.ox) * self.k, (self.oy - p[:, 1]) * self.k], 1) * 8).astype(np.int32)

    def _paint(self, fn, tone, gold, red):
        m = np.zeros_like(self.A); fn(m)
        self.A = np.maximum(self.A, m)
        for ch, v in ((self.T, tone), (self.G, gold), (self.R, red)):
            ch *= (1 - m); ch += m * v

    def poly(self, pts, tone=0.0, gold=0.0, red=0.0):
        self._paint(lambda m: cv2.fillPoly(m, [self.P(pts)], 1.0, cv2.LINE_AA, 3), tone, gold, red)

    def cap(self, a, b, r, tone=0.0, gold=0.0, red=0.0, r2=None):
        r2 = r if r2 is None else r2
        a, b = np.asarray(a, float), np.asarray(b, float); d = b - a; L = np.hypot(*d) + 1e-9; n = np.array([-d[1], d[0]]) / L
        def f(m):
            cv2.fillPoly(m, [self.P([a + n * r, b + n * r2, b - n * r2, a - n * r])], 1.0, cv2.LINE_AA, 3)
            for c, rr in ((a, r), (b, r2)):
                q = self.P(c)[0]; cv2.circle(m, (int(q[0]), int(q[1])), int(rr * self.k * 8), 1.0, -1, cv2.LINE_AA, 3)
        self._paint(f, tone, gold, red)

    def ell(self, c, ax, ang=0, tone=0.0, gold=0.0, red=0.0, a0=0, a1=360):
        q = self.P(c)[0]
        self._paint(lambda m: cv2.ellipse(m, (int(q[0]), int(q[1])), (int(ax[0] * self.k * 8), int(ax[1] * self.k * 8)), -ang, a0, a1,
                                          1.0, -1, cv2.LINE_AA, 3), tone, gold, red)

    def line(self, a, b, w, tone=0.5, gold=0.0, red=0.0, cover=True):
        def f(m):
            cv2.line(m, tuple(self.P(a)[0]), tuple(self.P(b)[0]), 1.0, max(1, int(w * self.k)), cv2.LINE_AA, 3)
        if cover: self._paint(f, tone, gold, red)
        else:     # 只改色不增加覆盖（甲片纹）
            m = np.zeros_like(self.A); f(m); m *= self.A
            for ch, v in ((self.T, tone), (self.G, gold), (self.R, red)):
                ch *= (1 - m); ch += m * v

    def lamellar(self, x0, x1, y0, y1, rows, tone=0.42, clip_poly=None, stagger=True):
        """甲片：一排排小鳞片（上沿高光），只画在已有覆盖内"""
        dy = (y1 - y0) / rows
        m = np.zeros_like(self.A)
        for r in range(rows):
            y = y1 - r * dy; off = (r % 2) * 0.5 if stagger else 0
            n = max(2, int((x1 - x0) / 3.2))
            for i in range(n + 1):
                x = x0 + (i + off) * (x1 - x0) / n
                q = self.P([x, y])[0]
                cv2.ellipse(m, (int(q[0]), int(q[1])), (int(1.5 * self.k * 8), int(dy * 0.55 * self.k * 8)), 0, 200, 340, 1.0,
                            max(1, int(0.35 * self.k)), cv2.LINE_AA, 3)
        if clip_poly is not None:
            cm = np.zeros_like(self.A); cv2.fillPoly(cm, [self.P(clip_poly)], 1.0, cv2.LINE_AA, 3); m *= cm
        m *= self.A
        self.T = self.T * (1 - m) + m * tone

    def finish(self, rim_dir=(-0.6, -0.8), rimw=1.2):
        """降采样 → 返回精灵 dict：A, base(RGB), rim(边缘光强), anchors(像素)"""
        hs, ws = self.h // SS, self.w // SS
        dn = lambda a: cv2.resize(a, (ws, hs), interpolation=cv2.INTER_AREA)
        A, T, G, R = dn(self.A), dn(self.T), dn(self.G), dn(self.R)
        inv = 1 / np.maximum(A, 1e-3)
        T, G, R = np.clip(T * inv * (A > 0), 0, 1), np.clip(G * inv * (A > 0), 0, 1), np.clip(R * inv * (A > 0), 0, 1)
        yy = np.linspace(1.0, 0.0, hs, dtype=np.float32)[:, None]
        base = INK[None, None] + (T * 0.30 + 0.02 * yy)[..., None] * np.array([0.95, 0.97, 1.0], np.float32)
        base = base * (1 - G[..., None] * 0.7) + GOLD * (0.30 + 0.5 * T)[..., None] * G[..., None] * 0.7
        base = base * (1 - R[..., None]) + RED * (0.55 + 0.4 * T)[..., None] * R[..., None]
        dx, dy = np.array(rim_dir, float) / np.linalg.norm(rim_dir)
        def sh(a, s):
            M = np.float32([[1, 0, -dx * s], [0, 1, -dy * s]])
            return cv2.warpAffine(a, M, (ws, hs), borderValue=0)
        rw = rimw * UNIT
        rim = np.clip(A - sh(A, rw * 0.5), 0, 1) * 1.0 + cv2.GaussianBlur(np.clip(A - sh(A, rw * 2.0), 0, 1), (0, 0), rw) * A * 0.45
        rim = rim + np.clip(T - 0.3, 0, 1) * A * 0.25                 # 甲片也吃一点光
        ys, xs = np.nonzero(A > 0.01)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        anc = {k: ((v[0] + self.ox) * UNIT - x0, (self.oy - v[1]) * UNIT - y0) for k, v in self.anchors.items()}
        foot = (self.ox * UNIT - x0, self.oy * UNIT - y0)
        return dict(A=A[y0:y1, x0:x1].copy(), base=base[y0:y1, x0:x1].astype(np.float32).copy(), rim=rim[y0:y1, x0:x1].copy(),
                    anchors=anc, foot=foot)


class _SkFig(_FigCV):
    """skia 矢量版精灵画布：A/T/G/R 存在一张 RGBA 预乘面里（R=明暗 G=金 B=朱 A=覆盖），
    不透明色 SrcOver = 按覆盖率逐通道 lerp；甲片纹用 SrcATop（只画在已有覆盖内）+ 路径裁剪。finish() 与旧版一致。"""
    def __init__(self, wu, hu, ox, oy):
        self.k = UNIT * SS; self.ox, self.oy = ox, oy
        self.h, self.w = int(hu * self.k), int(wu * self.k)
        self.B = np.zeros((self.h, self.w, 4), np.uint8)
        self.cv = skia.Surface(self.B, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType).getCanvas()
        self.anchors = {}
    def Pf(self, p):
        p = np.asarray(p, float).reshape(-1, 2)
        return np.stack([(p[:, 0] + self.ox) * self.k, (self.oy - p[:, 1]) * self.k], 1)
    def _paint(self, tone, gold, red, atop=False, stroke=None):
        p = skia.Paint(AntiAlias=True, Color=skia.Color(int(tone * 255 + .5), int(gold * 255 + .5), int(red * 255 + .5), 255))
        if atop: p.setBlendMode(skia.BlendMode.kSrcATop)
        if stroke:
            p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(float(stroke)); p.setStrokeCap(skia.Paint.kRound_Cap)
        return p
    def poly(self, pts, tone=0.0, gold=0.0, red=0.0):
        self.cv.drawPath(_sk.path_poly(self.Pf(pts)), self._paint(tone, gold, red))
    def cap(self, a, b, r, tone=0.0, gold=0.0, red=0.0, r2=None):
        r2 = r if r2 is None else r2
        q = self.Pf([a, b])
        self.cv.drawPath(_sk.path_capsule_union(q[0], q[1], r * self.k, r2 * self.k), self._paint(tone, gold, red))
    def ell(self, c, ax, ang=0, tone=0.0, gold=0.0, red=0.0, a0=0, a1=360):
        q = self.Pf(c)[0]; rx, ry = ax[0] * self.k, ax[1] * self.k
        P = skia.Path()
        R = skia.Rect.MakeLTRB(q[0] - rx, q[1] - ry, q[0] + rx, q[1] + ry)
        if a1 - a0 >= 360: P.addOval(R)
        else: P.moveTo(*q); P.arcTo(R, float(a0), float(a1 - a0), False); P.close()
        if ang: P.transform(skia.Matrix.RotateDeg(float(-ang), skia.Point(*q)))
        self.cv.drawPath(P, self._paint(tone, gold, red))
    def line(self, a, b, w, tone=0.5, gold=0.0, red=0.0, cover=True):
        self.cv.drawPath(_sk.path_poly(self.Pf([a, b]), closed=False), self._paint(tone, gold, red, atop=not cover, stroke=max(0.5, w * self.k)))
    def lamellar(self, x0, x1, y0, y1, rows, tone=0.42, clip_poly=None, stagger=True):
        dy = (y1 - y0) / rows
        self.cv.save()
        if clip_poly is not None: self.cv.clipPath(_sk.path_poly(self.Pf(clip_poly)), skia.ClipOp.kIntersect, True)
        P = skia.Path()
        for r in range(rows):
            y = y1 - r * dy; off = (r % 2) * 0.5 if stagger else 0
            n = max(2, int((x1 - x0) / 3.2))
            for i in range(n + 1):
                x = x0 + (i + off) * (x1 - x0) / n
                q = self.Pf([x, y])[0]; rx, ry = 1.5 * self.k, dy * 0.55 * self.k
                P.addArc(skia.Rect.MakeLTRB(q[0] - rx, q[1] - ry, q[0] + rx, q[1] + ry), 200, 140)
        self.cv.drawPath(P, self._paint(tone, 0, 0, atop=True, stroke=max(0.6, 0.35 * self.k)))
        self.cv.restore()
    def finish(self, rim_dir=(-0.6, -0.8), rimw=1.2):
        B = self.B.astype(np.float32) / 255.
        self.A, self.T, self.G, self.R = B[..., 3], B[..., 0], B[..., 1], B[..., 2]
        return _FigCV.finish(self, rim_dir, rimw)

try:
    import sk as _sk
    skia = _sk.skia
    BACKEND = 'skia' if _sk.HAVE_SKIA else 'cv'
except Exception:
    _sk = None; BACKEND = 'cv'
_Fig = _SkFig if BACKEND == 'skia' else _FigCV
def set_backend(name):
    """'skia'（默认）/'cv'：影响之后新建的 Army/Kneelers 精灵。"""
    global _Fig, BACKEND
    BACKEND = name; _Fig = _SkFig if name == 'skia' else _FigCV


# ============================================================== 重甲兵
def soldier_sprite(phase=0.0, arm=0.0, kneel=0.0, bow=0.0, weapon='spear', view='front', rim_dir=(-0.6, -0.8), seed=0,
                   tassel=True, level=0.0):
    """单个重甲兵精灵。phase 齐步相位 0..1（None=立定）；arm 举兵器 0..1；level 平枪/前指 0..1；kneel 跪 0..1；bow 低头 0..1。
    view='front'（正对镜头）/'side'（侧面朝右，冲锋）。"""
    r = np.random.default_rng(seed)
    F = _Fig(150, 236, 75, 230)
    if view == 'side':
        return _soldier_side(F, phase, arm, level, rim_dir, weapon, tassel)
    ph = 0 if phase is None else phase
    s1 = math.sin(2 * math.pi * ph)
    liftL, liftR = max(0, s1), max(0, -s1)
    bob = 1.6 * abs(s1) * (1 - kneel); sway = 0.8 * s1 * (1 - kneel)
    hy = 50 - 23 * kneel + bob * 0.4
    ny = hy + 30 * (1 - 0.35 * bow) - 0 * kneel
    cx = sway
    # 腿
    for sx, lift in ((-1, liftL), (1, liftR)):
        kL = kneel if sx < 0 else kneel * 0.5
        hip = (cx + sx * 6, hy)
        knee = (cx + sx * (7 + 2 * kneel), (25 + 6 * lift) * (1 - kL) + 5 * kL + (24 - 25) * (kneel if sx > 0 else 0))
        ank = (cx + sx * 7, 3 + 5 * lift * (1 - kneel))
        if sx > 0 and kneel > 0: knee = (cx + 10, 25 - 1 * kneel)
        F.cap(hip, knee, 5.6, 0.06, r2=4.8); F.cap(knee, ank, 4.8, 0.05, r2=3.8)
        F.poly([(ank[0] - 3.4 * 1, ank[1] + 1.5), (ank[0] + 3.6, ank[1] + 1.5), (ank[0] + 4.5 * sx * 0.3 + 4, ank[1] - 3.5),
                (ank[0] - 4.2, ank[1] - 3.5)], 0.08)
        F.ell((knee[0], knee[1] + 1), (3.6, 3.0), tone=0.35)        # 护膝
    # 甲裙
    sk = [(cx - 14, hy + 7), (cx + 14, hy + 7), (cx + 19 + 2 * kneel, hy - 15 + 6 * kneel), (cx + 2, hy - 17 + 6 * kneel),
          (cx - 2, hy - 17 + 6 * kneel), (cx - 19 - 2 * kneel, hy - 15 + 6 * kneel)]
    F.poly(sk, 0.04); F.lamellar(cx - 19, cx + 19, hy - 16 + 6 * kneel, hy + 6, 5, clip_poly=sk)
    F.line((cx, hy + 6), (cx, hy - 16 + 6 * kneel), 0.5, 0.0)
    # 躯干
    tor = [(cx - 18, ny - 1), (cx + 18, ny - 1), (cx + 14, hy + 7), (cx - 14, hy + 7)]
    F.poly(tor, 0.05); F.lamellar(cx - 16, cx + 16, hy + 8, ny - 9, 6, tone=0.38, clip_poly=tor)
    F.ell((cx, ny - 12), (4.6, 4.6), tone=0.42, gold=0.45)                                   # 护心镜（单面）
    F.ell((cx, ny - 12), (2.8, 2.8), tone=0.14, gold=0.25)
    F.line((cx - 15, ny - 5), (cx - 5, ny - 12), 0.6, 0.30); F.line((cx + 15, ny - 5), (cx + 5, ny - 12), 0.6, 0.30)   # 甲带
    F.anchors['mirror'] = (cx - 1.5, ny - 10.5)
    F.poly([(cx - 15, hy + 9), (cx + 15, hy + 9), (cx + 15, hy + 5), (cx - 15, hy + 5)], 0.22, gold=0.35)   # 腰带
    F.ell((cx, hy + 7), (2.6, 2.4), tone=0.6, gold=0.9)
    # 手臂与兵器
    shL, shR = np.array([cx + 17, ny - 4]), np.array([cx - 17, ny - 4])
    # 左手（画面右）自然下垂/扶腰
    elL = shL + [4, -14 + 4 * kneel]; haL = shL + [3, -27 + 6 * kneel]
    if kneel > 0.3: haL = np.array([cx + 13, hy + 2 + 6 * kneel])
    F.cap(shL, elL, 4.3, 0.06, r2=3.8); F.cap(elL, haL, 3.8, 0.06, r2=3.3); F.ell(haL, (3.4, 3.2), tone=0.1)
    # 右手（画面左）持兵器：carry → raise（过顶）/ level（前指，正视时缩短）
    a = arm
    hand = np.array([cx - 19, hy + 2]) * (1 - a) + np.array([cx - 12, ny + 33]) * a
    hand = hand * (1 - level) + np.array([cx - 15, ny - 10]) * level
    elb = (shR + hand) / 2 + np.array([-7 - 4 * a, -2 + 8 * a])
    if weapon == 'spear':
        ang = math.radians(4 + 18 * a)
        L1, L2 = 22 + 10 * a, 150 - 40 * level
        u = np.array([math.sin(ang), math.cos(ang)])
        if level > 0: u = u * (1 - level) + np.array([0.35, 0.55]) * level; u = u / np.linalg.norm(u)
        b0 = hand - u * L1; b1 = hand + u * L2
        F.line(b0, b1, 1.6, 0.25)
        tip = b1 + u * 12; nn = np.array([-u[1], u[0]])
        if tassel:                                                              # 红缨（垂坠）
            for j in range(10):
                dn = np.array([0.0, -1.0]) * 0.75 - u * 0.25
                F.line(b1 - u * 0.5, b1 - u * 0.5 + dn * (8 + r.uniform(0, 4)) + nn * (j - 4.5) * 0.9, 1.0, 0.4, red=1.0)
        F.poly([b1 - nn * 2.2, b1 - nn * 1.4 + u * 6, tip, b1 + nn * 1.4 + u * 6, b1 + nn * 2.2, b1 - u * 1.5], 0.9)   # 枪头（亮钢）
        F.line(b1 + u * 1, tip - u * 2, 0.4, 0.4)
        F.anchors['tip'] = tuple(tip); F.anchors['tipb'] = tuple(b1)
    else:   # 刀
        ang = math.radians(-160 * (1 - a) + 15 * a)
        u = np.array([math.sin(ang), math.cos(ang)])
        if level > 0: u = u * (1 - level) + np.array([0.6, 0.3]) * level; u /= np.linalg.norm(u)
        F.line(hand - u * 9, hand, 2.2, 0.12)
        nn = np.array([-u[1], u[0]])
        tip = hand + u * 62
        F.poly([hand + nn * 2.4, hand - nn * 1.8, tip - nn * 0.5, tip + nn * 1.6 + u * -4], 0.9)
        F.line(hand + nn * 3.5, hand - nn * 3.5, 1.2, 0.5, gold=0.8)
        F.anchors['tip'] = tuple(tip); F.anchors['tipb'] = tuple(hand)
    F.cap(shR, elb, 4.3, 0.06, r2=3.8); F.cap(elb, hand, 3.8, 0.06, r2=3.3); F.ell(hand, (3.4, 3.2), tone=0.1)
    for sx, sh in ((1, shL), (-1, shR)):                                     # 披膊（层叠）
        for j in range(3):
            F.ell(sh + [sx * (1 + j * 0.7), -j * 3.2], (8.5 - j * 0.8, 5.8), tone=0.10 + 0.14 * (2 - j), a0=180, a1=360)
            F.ell(sh + [sx * (1 + j * 0.7), -j * 3.2], (8.5 - j * 0.8, 1.2), tone=0.50)
    # 头盔（顿项护颈 + 盔体 + 盔沿 + 缨枪）
    hcx = cx; hcy = ny + 10 - 13 * bow
    F.poly([(hcx - 11, hcy - 2), (hcx + 11, hcy - 2), (hcx + 13, hcy - 13), (hcx - 13, hcy - 13)], 0.07)
    F.lamellar(hcx - 12, hcx + 12, hcy - 13, hcy - 3, 3, tone=0.32)
    F.ell((hcx, hcy + 1), (8.6, 9.2), tone=0.12)
    F.ell((hcx - 2.5, hcy + 4), (4.5, 5.2), tone=0.45, a0=180, a1=300)      # 盔顶高光
    F.poly([(hcx - 10.5, hcy - 2.5), (hcx + 10.5, hcy - 2.5), (hcx + 9, hcy - 0.5), (hcx - 9, hcy - 0.5)], 0.55, gold=0.4)
    F.poly([(hcx - 6, hcy - 2), (hcx + 6, hcy - 2), (hcx + 5, hcy - 7), (hcx - 5, hcy - 7)], 0.0)   # 面部阴影
    F.line((hcx - 4.4, hcy - 4.3), (hcx - 1.5, hcy - 4.1), 0.5, 0.25); F.line((hcx + 1.5, hcy - 4.1), (hcx + 4.4, hcy - 4.3), 0.5, 0.25)
    F.line((hcx, hcy + 9), (hcx, hcy + 17), 1.0, 0.6, gold=0.7)
    F.ell((hcx, hcy + 10), (2.0, 1.2), tone=0.6, gold=0.8)
    F.anchors['helm'] = (hcx - 3, hcy + 6)
    if tassel:
        for j in range(11):
            ang = math.radians(-50 + j * 10 + r.normal(0, 4))
            F.line((hcx, hcy + 16.5), (hcx + math.sin(ang) * 7, hcy + 17 + math.cos(ang) * 4 - 6 + abs(j - 5) * -0.4), 1.0, 0.35, red=1.0)
    return F.finish(rim_dir)


def _soldier_side(F, phase, arm, level, rim_dir, weapon, tassel):
    """侧面（朝右）奔跑冲锋。"""
    ph = 0 if phase is None else phase
    w = 2 * math.pi * ph
    lean = 8 * (phase is not None)
    hy = 48 + 2.5 * abs(math.sin(w))
    for sgn, tone in ((1, 0.02), (-1, 0.08)):
        sw = math.sin(w) * sgn
        hip = np.array([0, hy]); knee = hip + [12 * sw + 3, -22 + 4 * max(0, sw)]
        ank = knee + [-6 + 8 * min(0, sw) * -0.5 - 8 * max(0, -sw), -20 + 9 * max(0, -sw)]
        F.cap(hip, knee, 4.6, tone, r2=4.0); F.cap(knee, ank, 4.0, tone, r2=3.2)
        F.poly([ank + [-3, 1.5], ank + [7, 0], ank + [7, -3.5], ank + [-4, -3.5]], tone)
    rc = math.radians(lean)
    def R(p): p = np.asarray(p, float); return np.array([p[0] * math.cos(rc) + p[1] * math.sin(rc), -p[0] * math.sin(rc) + p[1] * math.cos(rc)])
    base = np.array([0, hy])
    sk = [base + R(p) for p in ([-9, 8], [9, 8], [13, -16], [-12, -16])]
    F.poly(sk, 0.04); F.lamellar(-12, 13, hy - 16, hy + 6, 5, clip_poly=sk)
    tor = [base + R(p) for p in ([-10, 7], [9, 7], [11, 30], [-9, 32])]
    F.poly(tor, 0.05); F.lamellar(-10, 12, hy + 7, hy + 30, 6, tone=0.38, clip_poly=tor)
    sh = base + R([1, 28]); hcen = base + R([3, 40])
    F.poly([hcen + [-11, -2], hcen + [3, -2], hcen + [2, -12], hcen + [-12, -11]], 0.07)
    F.ell(hcen, (8.6, 9.0), tone=0.12); F.poly([hcen + [-9, -3], hcen + [10, -3], hcen + [11, -1], hcen + [-9, -1]], 0.55, gold=0.4)
    F.line(hcen + [0, 8], hcen + [-2, 16], 1.0, 0.6, gold=0.7)
    if tassel:
        for j in range(9): F.line(hcen + [-2, 15.5], hcen + [-2 - 6 - j * 0.6, 14 - j * 0.9], 1.0, 0.35, red=1.0)
    F.anchors['helm'] = tuple(hcen + [2, 5]); F.anchors['mirror'] = tuple(base + R([8, 20]))
    for j in range(3): F.ell(sh + [0, -j * 3.2], (7.5 - j, 5.5), tone=0.1 + 0.14 * (2 - j), a0=180, a1=360)
    hand = sh + [16 - 4 * arm, -6 + 30 * arm]; elb = sh + [6, -12 + 14 * arm]
    if weapon == 'spear':
        u = np.array([1, 0.04 + 0.9 * arm]); u /= np.linalg.norm(u)
        b0, b1 = hand - u * 70, hand + u * 70
        F.line(b0, b1, 1.6, 0.25); nn = np.array([-u[1], u[0]]); tip = b1 + u * 12
        if tassel:
            for j in range(8): F.line(b1 - u, b1 - u * 9 + nn * (j - 3.5) * 1.0 + [0, -4], 1.0, 0.4, red=1.0)
        F.poly([b1 - nn * 2.2, b1 - nn * 1.4 + u * 6, tip, b1 + nn * 1.4 + u * 6, b1 + nn * 2.2, b1 - u * 1.5], 0.9)
        F.anchors['tip'] = tuple(tip); F.anchors['tipb'] = tuple(b1)
    else:
        u = np.array([0.8, 0.6 + 0.8 * arm]); u /= np.linalg.norm(u); nn = np.array([-u[1], u[0]]); tip = hand + u * 60
        F.poly([hand + nn * 2.4, hand - nn * 1.8, tip - nn * 0.5, tip + nn * 1.6 - u * 4], 0.9)
        F.anchors['tip'] = tuple(tip); F.anchors['tipb'] = tuple(hand)
    F.cap(sh, elb, 4.3, 0.06, r2=3.8); F.cap(elb, hand, 3.8, 0.06, r2=3.3)
    return F.finish(rim_dir)


# ============================================================== 精灵缓存与合成
def _resize_sprite(sp, s):
    """s = 输出/精灵 尺寸比"""
    h, w = sp['A'].shape
    nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
    it = cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR
    return (cv2.resize(sp['A'], (nw, nh), interpolation=it), cv2.resize(sp['base'], (nw, nh), interpolation=it),
            cv2.resize(sp['rim'], (nw, nh), interpolation=it))

class _SpriteCache:
    def __init__(self, sprites, step=1.045):
        self.S = sprites; self.c = {}; self.lstep = math.log(step)
    def get(self, idx, s):
        b = int(round(math.log(max(s, 1e-3)) / self.lstep))
        key = (idx, b)
        if key not in self.c:
            if len(self.c) > 4000: self.c.clear()
            self.c[key] = _resize_sprite(self.S[idx], math.exp(b * self.lstep)) + (math.exp(b * self.lstep),)
        return self.c[key]

def _paste(bufC, bufA, A, C, x, y, alpha=1.0):
    """premultiplied over：bufC (h,w,3)、bufA (h,w)；A,C 精灵；(x,y) 左上（像素，可越界）"""
    h, w = A.shape; Hh, Ww = bufA.shape
    x0, y0 = int(round(x)), int(round(y)); xa, ya = max(0, x0), max(0, y0); xb, yb = min(Ww, x0 + w), min(Hh, y0 + h)
    if xb <= xa or yb <= ya: return
    a = A[ya - y0:yb - y0, xa - x0:xb - x0] * alpha
    c = C[ya - y0:yb - y0, xa - x0:xb - x0]
    inv = (1 - a)
    bufC[ya:yb, xa:xb] = bufC[ya:yb, xa:xb] * inv[..., None] + c * a[..., None]
    bufA[ya:yb, xa:xb] = bufA[ya:yb, xa:xb] * inv + a


def project(P, cam):
    """P (...,3) 世界坐标 → (sx, sy, depth)。cam: x,y,z,pitch(度，正=俯),f(焦距像素),cx,cy(主点)"""
    P = np.asarray(P, float)
    X = P[..., 0] - cam['x']; Y = P[..., 1] - cam['y']; Z = P[..., 2] - cam['z']
    p = math.radians(cam.get('pitch', 0)); cp, sp = math.cos(p), math.sin(p)
    Yc = Y * cp + Z * sp; Zc = -Y * sp + Z * cp
    Zc = np.maximum(Zc, 1e-3)
    f = cam.get('f', 1500)
    return cam.get('cx', W / 2) + f * X / Zc, cam.get('cy', H / 2) - f * Yc / Zc, Zc


# ============================================================== 军阵
class Army:
    """五百重甲方阵。
    Army(seed=0, rows=20, cols=25, dx=1.5, dz=1.7, weapon='spear', view='front', rim_dir=(-0.6,-0.8), banners=12,
         torches=40, jitter=0.18)
    draw(fr, t, cam=None, advance=0.0, march=1.0, cadence=1.075, raise_=0.0, level=0.0, kneel=0.0, kneel_wave=0.6, part=0.0,
         focus=None, dof=1.0, rim_color=COLD, rim=1.0, fog_color=(0.11,0.115,0.13), fog_dist=110, glint=1.0, wind=1.0,
         torch=1.0, sync=0.06, flip=False, origin=(0,0,12))
      advance   方阵整体前移（米，正=朝镜头）。march 0..1：齐步幅度（0 立定）；cadence 步频(Hz，≈129BPM/2)
      raise_    举兵器 0..1（全体同时，带 0.08 拍延迟的波浪）；level 平枪前指
      kneel     跪下 0..1，kneel_wave 波浪传递量（从前排到后排、从中线向两侧）
      part      向两侧分开让路 0..1（中线留出通道）
      focus     对焦距离（米，相机空间深度）；None=自动对前排；dof 景深强度（0 关）
      fog_*     大气透视：远处溶入雾色
      origin    方阵前排中心的世界坐标
    返回 (fr, info)  info: front_y(前排脚底屏幕y)、bbox、depths"""
    def __init__(self, seed=0, rows=20, cols=25, dx=1.5, dz=1.7, weapon='spear', view='front', rim_dir=(-0.6, -0.8),
                 banners=12, torches=40, jitter=0.18):
        rng = np.random.default_rng(seed); self.seed = seed
        self.rows, self.cols, self.dx, self.dz, self.view = rows, cols, dx, dz, view
        gx, gz = np.meshgrid((np.arange(cols) - (cols - 1) / 2) * dx, np.arange(rows) * dz)
        self.X = (gx + rng.normal(0, jitter, gx.shape)).ravel(); self.Z = (gz + rng.normal(0, jitter * 0.6, gz.shape)).ravel()
        self.R = np.repeat(np.arange(rows), cols); self.Cc = np.tile(np.arange(cols), rows)
        self.off = rng.normal(0, 1, self.X.size); self.hv = rng.uniform(0.96, 1.05, self.X.size)
        self.gph = rng.uniform(0, 1, self.X.size); self.gsp = rng.uniform(0.15, 0.45, self.X.size)
        self.NM, self.NA, self.NK = 8, 6, 6
        sp = []
        for i in range(self.NM): sp.append(soldier_sprite(i / self.NM, weapon=weapon, view=view, rim_dir=rim_dir, seed=seed))
        for i in range(self.NA): sp.append(soldier_sprite(None, arm=(i + 1) / self.NA, weapon=weapon, view=view, rim_dir=rim_dir, seed=seed))
        for i in range(self.NK): sp.append(soldier_sprite(None, kneel=(i + 1) / self.NK, bow=(i + 1) / self.NK * 0.8, weapon=weapon,
                                                          view=view, rim_dir=rim_dir, seed=seed))
        for i in range(4): sp.append(soldier_sprite(None, level=(i + 1) / 4, weapon=weapon, view=view, rim_dir=rim_dir, seed=seed))
        self.sprites = sp; self.cache = _SpriteCache(sp)
        self.sp_h = sp[0]['foot'][1] / UNIT        # 精灵中脚底以上像素对应身高单位（≈100+冠）
        # 旗帜：位于后排间隙
        nb = banners
        self.ban = [dict(x=(rng.uniform(-0.45, 0.45)) * cols * dx, z=rng.uniform(0.3, 0.95) * rows * dz, h=rng.uniform(3.9, 4.6),
                         w=rng.uniform(1.7, 2.3), hh=rng.uniform(1.0, 1.3), ph=rng.uniform(0, 6.28), red=rng.random() < 0.45,
                         tri=rng.random() < 0.3) for _ in range(nb)]
        self.tor = [dict(i=int(rng.integers(0, self.X.size)), ph=rng.uniform(0, 6.28)) for _ in range(torches)]

    def _pose_idx(self, phase, a, k, lv):
        if k > 0.04: return self.NM + self.NA + min(self.NK - 1, int(k * self.NK))
        if lv > 0.08: return self.NM + self.NA + self.NK + min(3, int(lv * 4))
        if a > 0.06: return self.NM + min(self.NA - 1, int(a * self.NA))
        if phase is None: return 0
        return int(phase * self.NM) % self.NM

    def draw(self, fr, t, cam=None, advance=0.0, march=1.0, cadence=1.075, raise_=0.0, level=0.0, kneel=0.0, kneel_wave=0.6,
             part=0.0, focus=None, dof=1.0, rim_color=COLD, rim=1.0, fog_color=(0.11, 0.115, 0.13), fog_dist=110.0, glint=1.0,
             wind=1.0, torch=1.0, sync=0.06, flip=False, origin=(0.0, 0.0, 12.0), alpha=1.0, max_slabs=6):
        cam = cam or dict(x=0, y=6, z=0, pitch=12, f=1500)
        ox, oy, oz = origin
        gap = part * (self.dx * 3.0)
        X = ox + self.X + np.sign(self.X) * gap * (1 + 0.15 * np.abs(self.X) / (self.cols * self.dx))
        Z = oz + self.Z - advance
        if march > 0:
            Zst = Z - 0.0
        sx, sy, d = project(np.stack([X, np.zeros_like(X), Z], 1), cam)
        f = cam.get('f', 1500)
        scl = f * 1.8 / d / 100 * self.hv          # 像素 / 身高单位
        vis = (d > 0.6) & (sx > -400) & (sx < W + 400) & (sy > -200) & (sy < H + 1600)
        idx = np.nonzero(vis)[0]
        if not len(idx): return fr, {}
        # 每人姿态
        delay = self.R * 0.035 + np.abs(self.Cc - (self.cols - 1) / 2) * 0.012
        kk = np.clip(kneel * (1 + kneel_wave * 1.5) - delay * kneel_wave * 1.7, 0, 1)
        aa = np.clip(raise_ * 1.3 - self.R * 0.015 - self.off * 0.01, 0, 1)
        ll = np.clip(level * 1.3 - self.R * 0.015, 0, 1)
        phs = (t * cadence + self.off * sync) % 1.0
        # 景深分层
        if focus is None: focus = float(np.min(d[idx])) * 1.15
        coc = np.abs(1 / d - 1 / focus) * f * 0.045 * dof     # 光圈≈4.5cm
        order = idx[np.argsort(-d[idx])]
        lv = np.array([0.0, 1.2, 2.5, 4.5, 8, 14, 24])
        bl = np.digitize(coc[order], (lv[1:] + lv[:-1]) / 2)
        # 切片：相邻同 blur 等级合并成一个 slab
        slabs = []; cur = None
        for j, b in zip(order, bl):
            if cur is None or b != cur[0]:
                cur = [b, []]; slabs.append(cur)
            cur[1].append(j)
        while len(slabs) > max_slabs:          # 合并最小的相邻 slab
            m = min(range(len(slabs) - 1), key=lambda i: len(slabs[i][1]) + len(slabs[i + 1][1]))
            slabs[m] = [max(slabs[m][0], slabs[m + 1][0]), slabs[m][1] + slabs[m + 1][1]]; del slabs[m + 1]
        rc = np.asarray(rim_color, np.float32) * rim
        fogc = np.asarray(fog_color, np.float32)
        glints = []; torches = []; info = dict(front_y=float(sy[idx].max()), depths=(float(d[idx].min()), float(d[idx].max())))
        tor_set = {o['i']: o for o in self.tor}
        # 旗帜按深度插入对应 slab
        bans = []
        for b in self.ban:
            bz = oz + b['z'] - advance; bx = ox + b['x'] + np.sign(b['x']) * gap
            px, py, bd = project(np.array([[bx, 0, bz], [bx, b['h'], bz]]), cam)
            if bd[0] < 0.6: continue
            bans.append((float(bd[0]), b, px, py))
        for sb, members in slabs:
            k = 1 if lv[sb] < 2 else (2 if lv[sb] < 6 else 4)
            hh, ww = H // k, W // k
            bufC = np.zeros((hh, ww, 3), np.float32); bufA = np.zeros((hh, ww), np.float32)
            dmin, dmax = d[members].min(), d[members].max()
            for (bd, b, px, py) in bans:          # 远于本 slab 最近者、近于最远者的旗帜
                if dmin <= bd <= dmax + 1e-6:
                    self._banner(bufC, bufA, k, b, px, py, bd, t, wind, rc, fogc, fog_dist, cam)
            for j in members:
                s = scl[j]; sprite_s = s / UNIT / k
                pi = self._pose_idx(None if march <= 0 else phs[j], aa[j], kk[j], ll[j])
                A, B, Rm, sb_ = self.cache.get(pi, sprite_s)
                fd = 1 - math.exp(-d[j] / fog_dist)
                C = B * (1 - fd) + fogc * fd + Rm[..., None] * rc * (1 - fd * 0.8)
                foot = self.sprites[pi]['foot']
                bob = 0.0
                x0 = sx[j] / k - foot[0] * sb_; y0 = sy[j] / k - foot[1] * sb_ - bob
                if flip: C = C[:, ::-1]; A = A[:, ::-1]; x0 = sx[j] / k - (A.shape[1] - foot[0] * sb_)
                _paste(bufC, bufA, A, C, x0, y0, alpha)
                anc = self.sprites[pi]['anchors']
                if glint > 0 and 'mirror' in anc:
                    g = max(0.0, math.sin(2 * math.pi * (t * self.gsp[j] + self.gph[j]))) ** 80
                    if g > 0.05:
                        for key in ('mirror', 'helm'):
                            ax, ay = anc[key]
                            glints.append((x0 * k + ax * sb_ * k, y0 * k + ay * sb_ * k, g * glint * (1 - fd), s))
                    gt = max(0.0, math.sin(2 * math.pi * (t * self.gsp[j] * 1.3 + self.gph[j] + 0.4))) ** 60
                    if gt > 0.05 and 'tip' in anc:
                        ax, ay = anc['tip']; glints.append((x0 * k + ax * sb_ * k, y0 * k + ay * sb_ * k, gt * glint * (1 - fd), s))
                if torch > 0 and j in tor_set and 'tipb' in anc:
                    ax, ay = anc['helm']
                    torches.append((x0 * k + (ax - 18 * UNIT) * sb_ * k, y0 * k + (ay - 26 * UNIT) * sb_ * k, s, tor_set[j]['ph'], fd))
            sig = lv[sb] / k
            if sig > 0.5:
                bufC = cv2.GaussianBlur(bufC, (0, 0), sig); bufA = cv2.GaussianBlur(bufA, (0, 0), sig)
            if k > 1:
                bufC = cv2.resize(bufC, (W, H), interpolation=cv2.INTER_LINEAR); bufA = cv2.resize(bufA, (W, H), interpolation=cv2.INTER_LINEAR)
            ys, xs = np.nonzero(bufA[::8, ::8] > 0.002)
            if len(ys):
                y0_, y1_ = max(0, ys.min() * 8 - 8), min(H, ys.max() * 8 + 16); x0_, x1_ = max(0, xs.min() * 8 - 8), min(W, xs.max() * 8 + 16)
                a = bufA[y0_:y1_, x0_:x1_, None]
                fr[y0_:y1_, x0_:x1_] = fr[y0_:y1_, x0_:x1_] * (1 - a) + bufC[y0_:y1_, x0_:x1_]
        # 火把与甲光（加色，最后叠）
        if torches or glints:
            L = np.zeros((H // 2, W // 2), np.float32); Lg = np.zeros((H // 2, W // 2), np.float32)
            for (x, y, s, ph, fd) in torches:
                fl = 0.75 + 0.25 * math.sin(t * 17 + ph) * math.sin(t * 7.3 + ph * 2)
                r_ = max(1.0, s * 2.2)
                cv2.circle(L, (int(x * 2), int(y * 2)), int(r_ * 2), float(fl * (1 - fd * 0.6)), -1, cv2.LINE_AA, 2)
                cv2.ellipse(L, (int(x * 2), int((y - r_ * 1.2) * 2)), (int(r_ * 1.3), int(r_ * 3)), 0, 0, 360, float(fl * 0.7), -1, cv2.LINE_AA, 2)
            for (x, y, g, s) in glints:                     # 甲光：小亮点 + 横向细芒（随距离缩小）
                r_ = float(np.clip(s * 1.6, 1.0, 9.0)) * (0.5 + 0.5 * g)
                cv2.line(Lg, (int((x - r_ * 3) * 4), int(y * 4)), (int((x + r_ * 3) * 4), int(y * 4)), float(g * 0.6), 1, cv2.LINE_AA, 3)
                cv2.circle(Lg, (int(x * 4), int(y * 4)), int(max(2, r_ * 1.2)), float(g), -1, cv2.LINE_AA, 3)
            if torches:
                Lb = cv2.GaussianBlur(L, (0, 0), 1.0) + cv2.GaussianBlur(cv2.resize(L, (W // 8, H // 8), interpolation=cv2.INTER_AREA), (0, 0), 3).repeat(4, 0).repeat(4, 1)[:H // 2, :W // 2] * 3
                fr += cv2.resize(Lb, (W, H))[..., None] * (GOLD * 1.2 * torch)
            if glints:
                Lg2 = Lg + cv2.GaussianBlur(Lg, (0, 0), 3) * 1.5
                fr += cv2.resize(Lg2, (W, H))[..., None] * (np.asarray(rim_color, np.float32) * 0.5 + 0.5) * 1.3
        return fr, info

    def _banner(self, bufC, bufA, k, b, px, py, bd, t, wind, rc, fogc, fog_dist, cam):
        """旗帜：旗杆 + 布面（行波 + 噪声，按斜率明暗），画进当前 slab。"""
        f = cam.get('f', 1500); s = f / bd / k         # 像素/米
        x0, yb, yt = px[0] / k, py[0] / k, py[1] / k
        fd = 1 - math.exp(-bd / fog_dist)
        hb, wb = bufA.shape
        xa, xb = int(max(0, x0 - 0.3 * s - 3)), int(min(wb, x0 + 0.3 * s + 4))
        ya, yb2 = int(max(0, yt - 0.5 * s - 3)), int(min(hb, yb + 3))
        if xb > xa and yb2 > ya:
            pole = np.zeros((yb2 - ya, xb - xa), np.float32)
            cv2.line(pole, (int((x0 - xa) * 8), int((yb - ya) * 8)), (int((x0 - xa) * 8), int((yt - 0.3 * s - ya) * 8)), 1.0,
                     max(1, int(0.07 * s) + 1), cv2.LINE_AA, 3)
            cv2.circle(pole, (int((x0 - xa) * 8), int((yt - 0.3 * s - ya) * 8)), int(max(1, 0.1 * s) * 8), 1.0, -1, cv2.LINE_AA, 3)
            a = pole[..., None]
            bufC[ya:yb2, xa:xb] = bufC[ya:yb2, xa:xb] * (1 - a) + (INK * (1 - fd) + fogc * fd) * a
            bufA[ya:yb2, xa:xb] = bufA[ya:yb2, xa:xb] * (1 - pole) + pole
        nu, nv = 14, 4
        u = np.linspace(0, 1, nu + 1); v = np.linspace(0, 1, nv + 1)
        ww, hh = b['w'] * s, b['hh'] * s
        om = 7.0 * wind; kx = 9.0
        def disp(uu, vv):
            ph = kx * uu - om * t + b['ph']
            dy = (math.sin(ph) * 0.18 + 0.06 * math.sin(2.3 * ph + vv * 2)) * hh * uu * wind
            dx = -abs(math.sin(ph * 0.5)) * 0.08 * ww * uu
            slope = math.cos(ph) * (0.6 + 0.4 * uu)
            return dx, dy, slope
        col_base = RED * 0.85 if b['red'] else np.array([0.06, 0.06, 0.07], np.float32)
        for i in range(nu):
            for j in range(nv):
                qs = []
                for (uu, vv) in ((u[i], v[j]), (u[i + 1], v[j]), (u[i + 1], v[j + 1]), (u[i], v[j + 1])):
                    if b['tri'] and vv > 1 - uu * 0.0: pass
                    dx, dy, _ = disp(uu, vv)
                    vy = vv * hh * (1 - 0.6 * uu if b['tri'] else 1)
                    qs.append((x0 + uu * ww + dx, yt + vy + dy))
                _, _, sl = disp((u[i] + u[i + 1]) / 2, (v[j] + v[j + 1]) / 2)
                m = np.zeros((1, 1)); P = np.round(np.array(qs) * 8).astype(np.int32)
                xs_, ys_ = P[:, 0] // 8, P[:, 1] // 8
                xa, xb, ya, yb2 = max(0, xs_.min() - 2), min(bufA.shape[1], xs_.max() + 3), max(0, ys_.min() - 2), min(bufA.shape[0], ys_.max() + 3)
                if xb <= xa or yb2 <= ya: continue
                m = np.zeros((yb2 - ya, xb - xa), np.float32)
                cv2.fillPoly(m, [P - np.array([xa * 8, ya * 8])], 1.0, cv2.LINE_AA, 3)
                shade = 0.55 + 0.45 * sl
                c = col_base * (0.5 + 0.8 * shade) + rc * max(0, sl) ** 3 * 0.25
                if j == 0 or (i == nu - 1): c = c + GOLD * 0.18 * (1 if b['red'] else 0.6)   # 金边
                c = c * (1 - fd) + fogc * fd
                a = m[..., None]
                bufC[ya:yb2, xa:xb] = bufC[ya:yb2, xa:xb] * (1 - a) + c * a; bufA[ya:yb2, xa:xb] = bufA[ya:yb2, xa:xb] * (1 - m) + m


# ============================================================== 跪地人群（平民）
def civ_sprite(kneel=1.0, bow=0.0, hands=0.0, seed=0, rim_dir=(0.0, -1.0), female=False):
    """平民剪影：长袍、广袖、发髻。kneel 0..1（站→跪坐）、bow 0..1（叩首，正侧面）、hands 合手举起。侧面朝右。"""
    r = np.random.default_rng(seed)
    F = _Fig(120, 120, 50, 115)
    hy = 50 - 26 * kneel
    # 跪坐：臀部落在脚跟上，袍子成一个丘
    if kneel > 0.5:
        F.poly([(-16, 0), (22, 0), (20, 8), (8, hy + 6), (-8, hy + 6), (-17, 6)], 0.04)
    else:
        F.poly([(-12, 0), (14, 0), (10, hy + 4), (-8, hy + 4)], 0.04)
    b = math.radians(85 * bow)
    def R(p): return np.array([p[0] * math.cos(b) + p[1] * math.sin(b), -p[0] * math.sin(b) + p[1] * math.cos(b)])
    base = np.array([0, hy])
    tor = [base + R(p) for p in ([-9, 2], [8, 2], [7, 28], [-6, 30])]
    F.poly(tor, 0.05)
    head = base + R([1, 38]); F.ell(head, (6.5, 7.2), tone=0.06)
    F.ell(head + R([-3, 6]), (3.8, 3.4), tone=0.10)       # 发髻
    if female: F.line(head + R([-3, 6]), head + R([-9, 4]), 0.8, 0.5, gold=0.5)
    sh = base + R([0, 27])
    hand = sh + R([14 + 2 * hands, -10 + 16 * hands]) if bow < 0.6 else base + R([4, 50])
    if bow > 0.6: hand = np.array([head[0] + 6, max(2, head[1] - 4)])
    F.cap(sh, hand, 4.8, 0.08, r2=6.5)                    # 广袖
    F.poly([hand + [-4, -6], hand + [5, -7], hand + [3, 4]], 0.08)
    F.line(base + R([-8, 6]), base + R([8, 6]), 0.8, 0.22)  # 腰带
    F.anchors['head'] = tuple(head)
    return F.finish(rim_dir, rimw=1.0)


class Kneelers:
    """跪地人群剪影（平民）。Kneelers(seed, n=40, spread=(200,1720), y_base=900, scale=(0.7,1.2), depth_rows=3)
    draw(fr, t, kneel=1, bow=0, wave=0.4, sway=1, rim_color=GOLD, rim=1, x_off=0, flip_ratio=0.5, dof=1.0, fog_color=None)
      kneel/bow 全体目标值；wave 波浪延迟（从左到右依次叩首）；sway 呼吸起伏；后排更小更淡更虚。"""
    def __init__(self, seed=0, n=40, spread=(200, 1720), y_base=900, scale=(0.7, 1.2), depth_rows=3, rim_dir=(0.0, -1.0)):
        rng = np.random.default_rng(seed)
        self.N = n
        self.x = rng.uniform(*spread, n); self.row = rng.integers(0, depth_rows, n)
        self.s = rng.uniform(*scale, n) * (1 - 0.22 * self.row); self.yb = y_base - self.row * 38 + rng.normal(0, 6, n)
        self.flip = rng.random(n) < 0.5; self.ph = rng.uniform(0, 6.28, n); self.fem = rng.random(n) < 0.4
        self.NB = 6
        self.sp = [civ_sprite(1.0, i / (self.NB - 1), seed=seed, rim_dir=rim_dir) for i in range(self.NB)]
        self.sp += [civ_sprite(1.0, i / (self.NB - 1), seed=seed, rim_dir=rim_dir, female=True) for i in range(self.NB)]
        self.cache = _SpriteCache(self.sp)
        self.order = np.argsort(-self.row)
        self.depth_rows = depth_rows

    def draw(self, fr, t, kneel=1.0, bow=0.0, wave=0.4, sway=1.0, rim_color=GOLD, rim=1.0, x_off=0.0, scale=1.0, dof=1.0,
             fog_color=None, alpha=1.0):
        rc = np.asarray(rim_color, np.float32) * rim
        for row in range(self.depth_rows - 1, -1, -1):
            k = 1 if row == 0 or dof <= 0 else 2
            bufC = np.zeros((H // k, W // k, 3), np.float32); bufA = np.zeros((H // k, W // k), np.float32)
            for i in np.nonzero(self.row == row)[0]:
                bb = np.clip(bow * (1 + wave) - wave * (self.x[i] / W), 0, 1)
                bb = np.clip(bb + 0.04 * sway * math.sin(t * 1.6 + self.ph[i]), 0, 1)
                pi = min(self.NB - 1, int(round(bb * (self.NB - 1)))) + (self.NB if self.fem[i] else 0)
                s = self.s[i] * scale
                A, B, Rm, sb = self.cache.get(pi, s / k)
                C = B + Rm[..., None] * rc
                if fog_color is not None:
                    fd = 0.25 * row; C = C * (1 - fd) + np.asarray(fog_color, np.float32) * fd
                foot = self.sp[pi]['foot']
                x0 = (self.x[i] + x_off) / k - foot[0] * sb; y0 = self.yb[i] / k - foot[1] * sb
                if self.flip[i]:
                    A = A[:, ::-1]; C = C[:, ::-1]; x0 = (self.x[i] + x_off) / k - (A.shape[1] - foot[0] * sb)
                _paste(bufC, bufA, A, C, x0, y0, alpha)
            sig = (row * 1.6 * dof) / k
            if sig > 0.4: bufC = cv2.GaussianBlur(bufC, (0, 0), sig); bufA = cv2.GaussianBlur(bufA, (0, 0), sig)
            if k > 1: bufC = cv2.resize(bufC, (W, H)); bufA = cv2.resize(bufA, (W, H))
            fr[:] = fr * (1 - bufA[..., None]) + bufC
        return fr
