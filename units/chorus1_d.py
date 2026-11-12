"""units/chorus1_d.py — 第八轮 C1 副歌一 · 风格 D 全段铺开（STYLE_D=1 才装载；S028–S030 冻结不在此文件）
素材：assets/gen/R8_D/C1/（nananobanana RH_image2，提示词 jobs/r8_D_C1.json，记录 crew/round8/genlog_C1.md）
复用本轮 style D 素材：route1/D028_bg、D028_blade_cut（S027/S038 血墨母题与 S028 呼应）、D029_bg（S044 手握刀母题）、D035_gap（S035 劈缝内层）
规则（SPREAD_r8）：画面除底部字幕外不出字；精灵一律 grade=NEU / rim=NORIM / wrap=0 / shade=None；刀痕 = 干笔飞白生图；碎石 = 生图碎块逐块抠出；
特效笔触：雨 = 自适应墨线（白底变黑线、黑底变白线）、火星 = 白 + 血红。切点 / 镜长 / 转场 / 字幕时刻全部沿用 chorus1 剪辑表。
install(G) 由 chorus1_sprites.install 在 STYLE_D 下调用，G = chorus1 的全局，返回 {镜号: 类}。"""
import math
import numpy as np, cv2


def install(G):
    globals().update({k: v for k, v in G.items() if not k.startswith('__')})
    import sprite as SP
    C1 = ROOT + '/assets/gen/R8_D/C1/'
    R1 = ROOT + '/assets/gen/R8_D/route1/'
    NEU = dict(expo=1.0, sat=1.0, tint=(1.0, 1.0, 1.0), lift=0.0, gamma=1.0)
    NORIM = dict(col=(1.0, 1.0, 1.0), amt=0.0, dir=(0.0, -1.0))
    WHITE3 = np.array([1.0, 1.0, 1.0], np.float32)
    BLOOD = np.array([0.80, 0.04, 0.03], np.float32)
    X, Y = K.grid()

    # ------------------------------------------------------------------ 素材
    _PL = {}
    def plate(path, size=(W, H), gain=1.0, blur=0.0, sat=1.0):
        key = (path, size, gain, blur, sat)
        if key not in _PL:
            im = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
            im = cv2.resize(im, size, interpolation=cv2.INTER_AREA)
            if sat != 1.0:
                l = im.mean(-1, keepdims=True); im = l + (im - l) * sat
            if blur: im = cv2.GaussianBlur(im, (0, 0), blur)
            _PL[key] = (im * gain).astype(np.float32)
        return _PL[key]

    def flut(name, k=1.0, path=None):
        """私有精灵层：红带 / 衣摆 / 发丝的风吹权重加大（二级运动，不整张平移）"""
        sp = SP.SpriteLayer(path or (C1 + name + '_cut.png'))
        h_, w_ = sp.A.shape                                       # 画布四周羽化：图层边界在画面里永远不成直线 / 矩形边（11-11 硬规则）
        e = 0.05 * w_
        fx = np.clip(np.minimum(np.arange(w_), w_ - 1 - np.arange(w_)) / e, 0, 1)
        fy = np.clip(np.minimum(np.arange(h_), h_ - 1 - np.arange(h_)) / e, 0, 1)
        f = (fy[:, None] * fx[None, :]).astype(np.float32)
        sp.A = (sp.A * (f * f * (3 - 2 * f))).astype(np.float32)
        red = SP.red_mask(sp.F) * sp.A
        sp.wind_w = np.maximum(sp.wind_w, cv2.GaussianBlur(red, (0, 0), 8) * k).astype(np.float32)
        return sp

    def shaped_bottom(sp, y0=0.80, amp=0.09, feather=0.05, seed=0):
        """下沿按云形 / 撕口形状淡出（不是水平直切）：y0 以上不透明，y0 附近随低频噪声起伏，往下渐隐"""
        h, w = sp.A.shape
        n = cv2.resize(K.tile_crop(K.tile(256, seed + 771, 3, 3), 0, 0, 8, max(4, w // 16)), (w, 8), interpolation=cv2.INTER_CUBIC)
        prof = (n.mean(0) - 0.5) * 2.0
        cut = (y0 + amp * prof) * h
        a = np.clip((cut[None, :] - np.arange(h, dtype=np.float32)[:, None]) / (feather * h), 0, 1).astype(np.float32)
        sp.A = (sp.A * a).astype(np.float32)
        return sp

    def draw(sp, fr, t, anchor, dst, scale, **kw):
        kw.setdefault('wind_amp', 6.0); kw.setdefault('breathe', 0.003)
        return sp.draw(fr, t, anchor, dst, scale, grade=NEU, rim=NORIM, wrap=0, shade=None, **kw)

    def put_foot(sp, fr, t, h, foot, **kw):
        a, s = sp.fit(h)
        return draw(sp, fr, t, a, foot, s, **kw)

    def src2scr(sp, anchor, dst, s, p):
        """精灵归一化坐标 p → 画面像素（无旋转）"""
        return (dst[0] + (p[0] - anchor[0]) * sp.w * s, dst[1] + (p[1] - anchor[1]) * sp.h * s)

    def paste(fr, F, A, cx, cy, s, rot=0.0, alpha=1.0, blur=0.0):
        """RGBA 小块按中心 / 缩放 / 旋转贴到画面（只算落点 ROI）"""
        h, w = A.shape
        M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, s)
        M[0, 2] += cx - w / 2; M[1, 2] += cy - h / 2
        c = np.array([[0, 0], [w, 0], [0, h], [w, h]], np.float32) @ M[:, :2].T + M[:, 2]
        pad = 3 + 3 * blur
        x0, y0 = int(max(0, c[:, 0].min() - pad)), int(max(0, c[:, 1].min() - pad))
        x1, y1 = int(min(W, c[:, 0].max() + pad)), int(min(H, c[:, 1].max() + pad))
        if x1 <= x0 or y1 <= y0: return fr
        M2 = M.copy(); M2[0, 2] -= x0; M2[1, 2] -= y0
        Fw = cv2.warpAffine(F * A[..., None], M2, (x1 - x0, y1 - y0))
        Aw = cv2.warpAffine(A, M2, (x1 - x0, y1 - y0))
        if blur > 0.3:
            Fw = cv2.GaussianBlur(Fw, (0, 0), blur); Aw = cv2.GaussianBlur(Aw, (0, 0), blur)
        Aw = Aw * alpha; Fw = Fw * alpha
        roi = fr[y0:y1, x0:x1]
        fr[y0:y1, x0:x1] = roi * (1 - Aw[..., None]) + Fw
        return fr

    # 生图碎石：C1_rubble 逐块抠成独立小精灵（ink 勾边 + 网点，不画矢量多边形）
    _CH = []
    def chunks():
        if not _CH:
            im = cv2.cvtColor(cv2.imread(C1 + 'C1_rubble_cut.png', cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255
            im = cv2.resize(im, (1024, 576), interpolation=cv2.INTER_AREA)
            A = im[..., 3]
            n, lab, st, _ = cv2.connectedComponentsWithStats((A > 0.3).astype(np.uint8), 8)
            for i in np.argsort(-st[1:, 4]) + 1:
                x, y, w, h, a = st[i]
                if a < 120: continue
                x, y = max(0, x - 6), max(0, y - 6); w, h = min(1024 - x, w + 12), min(576 - y, h + 12)   # 四周留透明边
                m = (lab[y:y + h, x:x + w] == i).astype(np.float32)
                m = cv2.dilate(m, np.ones((3, 3), np.uint8))
                _CH.append((np.ascontiguousarray(im[y:y + h, x:x + w, :3]), np.ascontiguousarray(A[y:y + h, x:x + w] * m), max(w, h)))
        return _CH

    def debris(fr, t, t0, origin, seed, n=10, speed=(700, 1600), up=500, grav=1800, size=(0.35, 1.1), toward=0.0, dirc=None,
               spread=math.pi, blur=0.0, life=1.2, area=(40, 20)):
        """生图碎块迸发：抛物线 + 旋转；toward>0 时向镜头扑（放大 + 虚焦）"""
        a = t - t0
        if a < 0 or a > life: return fr
        r = np.random.default_rng(seed); cs = chunks()
        base = math.atan2(dirc[1], dirc[0]) if dirc else 0.0
        for i in range(n):
            F, A, sz = cs[int(r.integers(0, len(cs)))]
            ang = base + r.uniform(-spread, spread) if dirc else r.uniform(0, 2 * math.pi)
            sp = r.uniform(*speed); s0 = r.uniform(*size)
            ox, oy = origin[0] + r.uniform(-1, 1) * area[0], origin[1] + r.uniform(-1, 1) * area[1]
            px = ox + math.cos(ang) * sp * a
            py = oy + (math.sin(ang) * sp - up) * a + 0.5 * grav * a * a
            sc = s0 * (1 + toward * a * r.uniform(1.5, 3.0))
            rot = r.uniform(0, 360) + r.normal(0, 400) * a
            al = clamp01((life - a) / 0.2)
            if toward:
                px = W / 2 + (px - W / 2) * (1 + toward * a * 1.6); py = H / 2 + (py - H / 2) * (1 + toward * a * 1.6)
            fr = paste(fr, F, A, px, py, sc, rot, al, blur)          # 扑镜头不虚焦（景深虚化算 CG）
        return fr

    def ink_rain(fr, t, seed, n=300, amt=0.55, speed=1800, angle=8, near=0.25, length=(30, 90), region=None):
        """雨 = 细墨线：白底处画黑线、黑底处画白线（长短粗细有变化）"""
        m = K.rain(np.zeros((H, W, 3), np.float32), t, seed, n=n, amt=1.0, speed=speed, angle=angle, near=near, length=length,
                   region=region)[..., 0] / 0.78
        m = np.clip(m * amt, 0, 1)
        lum = cv2.blur(fr.mean(-1), (31, 31))
        tgt = np.where(lum > 0.45, 0.04, 0.92).astype(np.float32)
        return fr + (m * (tgt - fr.mean(-1)))[..., None]

    def ink_dust(fr, t, seed, n=80, amt=0.6, drift=(10, 60), size=(2, 5), region=(0, 120, W, 960)):
        """墙灰 / 灰烬：自适应墨点（白底灰黑、黑底灰白）"""
        m = K.dust(np.zeros((H, W, 3), np.float32), t, seed, n=n, amt=1.0, drift=drift, size=size, region=region, color=(1, 1, 1),
                   blur=1.0)[..., 0]
        m = np.clip(m * amt, 0, 1)
        lum = cv2.blur(fr.mean(-1), (31, 31))
        tgt = np.where(lum > 0.45, 0.18, 0.80).astype(np.float32)
        return fr + (m * (tgt - fr.mean(-1)))[..., None]

    def sparks2(fr, t, seed, origin, n=40, **kw):
        """火星：白 + 血红；白底上白火星加一道墨边才看得见"""
        z = np.zeros((H, W, 3), np.float32)
        mw = K.sparks(z, t, seed, origin, n=n, color=(1, 1, 1), **kw)[..., 0]
        mr = K.sparks(z, t, seed + 977, origin, n=max(1, n // 2), color=(1, 1, 1), **kw)[..., 0]
        mw = np.clip(mw, 0, 1.5); mr = np.clip(mr, 0, 1)
        edge = np.clip(cv2.GaussianBlur(mw, (0, 0), 2.0) * 1.4 - mw, 0, 1)
        lum = cv2.blur(fr.mean(-1), (31, 31))
        fr = fr * (1 - (edge * np.clip((lum - 0.5) * 3, 0, 1) * 0.8))[..., None]
        fr = fr + mw[..., None] * 0.95
        return fr * (1 - mr[..., None] * 0.9) + mr[..., None] * BLOOD

    class Brush:
        """干笔飞白斩痕（生图 C1_slash）：按 alpha 主轴把笔画映射到任意线段 P→Q（P = 起笔重端）"""
        def __init__(self, path):
            sl = cv2.cvtColor(cv2.imread(path, cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255
            self.F, self.A = sl[..., :3], sl[..., 3]
            ys, xs = np.nonzero(self.A > 0.5)
            P = np.stack([xs, ys], -1).astype(np.float64); c = P.mean(0)
            e = np.linalg.eigh(np.cov((P - c).T))[1][:, -1]
            if e[0] < 0: e = -e
            pr = (P - c) @ e
            self.a, self.b = c + e * pr.min(), c + e * pr.max()
            self.e, self.ep = e, np.array([-e[1], e[0]])
            self.cache = {}
        def warp(self, P, Q, wk=0.6, flip=False):
            key = (tuple(np.round(P, 1)), tuple(np.round(Q, 1)), wk, flip)
            if key in self.cache: return self.cache[key]
            P, Q = np.asarray(P, float), np.asarray(Q, float)
            L = np.linalg.norm(Q - P); d = (Q - P) / L; n = np.array([-d[1], d[0]]) * (-1 if flip else 1)
            s = L / np.linalg.norm(self.b - self.a)
            M2 = s * np.outer(d, self.e) + wk * s * np.outer(n, self.ep)
            M = np.hstack([M2, (P - M2 @ self.a)[:, None]])
            Fw = cv2.warpAffine(self.F, M, (W, H), flags=cv2.INTER_LINEAR)
            Aw = cv2.warpAffine(self.A, M, (W, H), flags=cv2.INTER_LINEAR)
            u = (((X - P[0]) * d[0] + (Y - P[1]) * d[1]) / L).astype(np.float32)
            if len(self.cache) > 1: self.cache.clear()             # 每镜一条固定笔画：只留最近 2 条（每条 ≈40MB）
            self.cache[key] = (Fw, Aw, u)
            return self.cache[key]
        def paint(self, fr, P, Q, head=1.0, wk=0.6, color=None, alpha=1.0, flip=False):
            Fw, Aw, u = self.warp(P, Q, wk, flip)
            a = np.clip((head - u) / 0.03, 0, 1) * Aw * alpha
            col = Fw if color is None else (Fw.mean(-1, keepdims=True) * 0 + np.asarray(color, np.float32))
            return fr * (1 - a[..., None]) + col * a[..., None]
    BR = Brush(C1 + 'C1_slash_cut.png')

    def speed_lines(fr, t, seed, amt=0.8, n=70, y0=140, y1=940, ln=(180, 700)):
        """漫画横向速度线：黑 + 白（白底看黑线、黑处看白线）"""
        r = np.random.default_rng(seed + int(round(t * 30)))
        Lk = np.zeros((H // 2, W // 2), np.float32); Lw = np.zeros_like(Lk)
        for i in range(n):
            yy = r.uniform(y0, y1) / 2; xx = r.uniform(-200, W) / 2; l = r.uniform(*ln) / 2
            cv2.line(Lk if i % 3 else Lw, (int(xx), int(yy)), (int(xx + l), int(yy)), r.uniform(0.4, 1.0), 1 if i % 4 else 2, cv2.LINE_AA)
        Lk = cv2.resize(cv2.GaussianBlur(Lk, (0, 0), 0.6), (W, H)); Lw = cv2.resize(cv2.GaussianBlur(Lw, (0, 0), 0.6), (W, H))
        fr = fr * (1 - np.clip(Lk * 0.85 * amt, 0, 1))[..., None]
        return fr + (Lw * 0.9 * amt)[..., None]

    def ray_lines(fr, c, amt, seed, n=70, r0=60, r1=1500):
        """漫画集中线（代替体积光）：从 c 放射的细墨线，亮处画黑、暗处画白，长短粗细有变化"""
        if amt <= 0.01: return fr
        r = np.random.default_rng(seed)
        L = np.zeros((H // 2, W // 2), np.float32)
        for i in range(n):
            a = r.uniform(0, 2 * math.pi); a0 = r0 * r.uniform(0.8, 2.5); a1 = r1 * r.uniform(0.4, 1.0)
            p0 = (c[0] + math.cos(a) * a0, c[1] + math.sin(a) * a0); p1 = (c[0] + math.cos(a) * a1, c[1] + math.sin(a) * a1)
            cv2.line(L, (int(p0[0] / 2), int(p0[1] / 2)), (int(p1[0] / 2), int(p1[1] / 2)), r.uniform(0.4, 1.0), 1 if i % 3 else 2, cv2.LINE_AA)
        m = np.clip(cv2.resize(L, (W, H)) * amt, 0, 1)
        lum = cv2.blur(fr.mean(-1), (31, 31))
        tgt = np.where(lum > 0.5, 0.04, 0.95).astype(np.float32)
        return fr + (m * (tgt - fr.mean(-1)))[..., None]

    def star(fr, p, g, lx=90, ly=40):
        """十字星芒（白）"""
        if g <= 0.01: return fr
        tx, ty = p
        st = np.exp(-(np.abs(X - tx) / 2.5 + np.abs(Y - ty) / ly)) + np.exp(-(np.abs(Y - ty) / 2.5 + np.abs(X - tx) / lx))
        return fr + (st * 1.4 + np.exp(-((X - tx) ** 2 + (Y - ty) ** 2) / 600)) [..., None] * g

    def split_frame(fr, P0, d, g, slide, mode='reflect'):
        """沿过 P0、方向 d 的直线把画面劈成两块，沿法线各错开 g/2、沿缝错开 slide/2；返回 (画面, 缝蒙版, 有向距离)"""
        n = np.array([-d[1], d[0]])
        sd = ((X - P0[0]) * n[0] + (Y - P0[1]) * n[1]).astype(np.float32)
        o = n * g / 2 + d * slide / 2
        bm = cv2.BORDER_REFLECT
        lo = cv2.warpAffine(fr, np.float32([[1, 0, o[0]], [0, 1, o[1]]]), (W, H), borderMode=bm)
        up = cv2.warpAffine(fr, np.float32([[1, 0, -o[0]], [0, 1, -o[1]]]), (W, H), borderMode=bm)
        ml = np.clip((sd - g / 2) + 0.5, 0, 1); mu = np.clip((-sd - g / 2) + 0.5, 0, 1)
        gm = np.clip(1 - ml - mu, 0, 1)
        return up * mu[..., None] + lo * ml[..., None], gm, sd

    out = {}

    # ================================================================== S027 CU 刃口热浪（血墨底 + 刀身，推进到白光吞没）
    class S027D(S027):
        def __init__(self):
            self.bg = plate(C1 + 'C1_bg027.png', gain=0.55)                  # 本镜专用血红热浪背景板（不与 S028 复用，不虚焦）
            self.blade = flut('blade', 0.0, R1 + 'D028_blade_cut.png')
            self.tex = K.tile(512, 271, 6, 4)
        def render(self, t):
            u = self.u(t)
            fr = self.bg.copy()
            heat = 0.4 + 0.6 * u
            fr, bm = self.blade.draw(fr, t, (0.5, 0.48), (980, 560), W / self.blade.w * 1.35, rot=-14, breathe=0, wind_amp=0,
                                     grade=NEU, rim=NORIM, wrap=0, shade=None)
            # 刃口烧红：刃下沿一道血红热线（墨边），越推越亮
            edge = np.clip(bm - cv2.erode(bm, np.ones((9, 9), np.uint8)), 0, 1) * (Y > 560 - (X - 980) * math.tan(math.radians(14)))
            fr = fr + (cv2.GaussianBlur(edge, (0, 0), 3) * 2.0 + K.blur_ds(edge, 24) * 1.2)[..., None] * BLOOD * heat
            n = cv2.resize(K.tile_crop(self.tex, 0, -t * 160, H // 8, W // 8), (W, H))
            amp = 6 + 10 * u
            fr = cv2.remap(fr, (X + (n - 0.5) * amp).astype(np.float32), (Y + (n - 0.5) * amp * 1.6).astype(np.float32), cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REFLECT)
            fr = sparks2(fr, t, 2701, (960, 700), n=40, life=1.0, speed=(150, 500), dirc=(0.3, -1), spread=0.6, grav=-80, area=(900, 200))
            z = 1.2 + 1.2 * ein(u, 2)
            dx, dy, dr = shake(t, 8 * u, 14, 27)
            fr = cam(fr, z / 1.2, dx, dy, dr, center=(1000, 560))
            fr = fr + ein(u, 4) * 0.9                              # 白光吞没（接 S028 血字头硬切）
            return K.radial_blur(fr, (1000, 560), 0.06 * ein(u, 3)), 0

    # ================================================================== S031 ELS 太上皇天幕巨像（白月作光环）+ 山脊一粒黑点
    class S031D(S031):
        def __init__(self):
            self.sky = plate(C1 + 'C1_sky.png', (2112, 1188))
            self.emp = shaped_bottom(flut('C1_emp_full', 0.6), 0.86, 0.08, 0.12, 31)   # 半身到膝的巨像；下摆烟化 + 云形不规则淡出
            self.sw = rig.Swordsman(310, view='back')
            self.ridge = K.ridge_line(W, 905, 40, 312, 2)
            n_ = cv2.resize(K.tile_crop(K.tile(512, 3131, 4, 4), 0, 0, H // 8, W // 8), (W, H))
            self.fn = ((n_ - 0.5) * 160 + 40 * np.sin(X / 140.0)).astype(np.float32)
        def render(self, t):
            u = self.u(t)
            cr = 60 * (1 - eio(u))
            dx = -30 + 60 * eio(u)                                  # 远景视差：天 0.3 / 巨像 0.6 / 山 1.0
            fr = self.sky[int(54 - cr * 0.3):int(54 - cr * 0.3) + H, int(96 + dx * 0.3):int(96 + dx * 0.3) + W].copy() * 1.06
            mc = (1040 / 2048 * 2112 - 96 - dx * 0.3, 279 / 1152 * 1188 - 54 + cr * 0.3)       # 背景板白月心
            s = 0.86 * (1 + 0.02 * u)
            anc, dst = (0.5, 0.09), (mc[0] + dx * 0.3, mc[1] - 150 + cr * 0.6)     # 发髻顶在白月里（月作光环），身体立在云海上
            fr, A = draw(self.emp, fr, t * 0.6, anc, dst, s, wind_amp=6, alpha=0.95)
            # 云海从下方漫过下摆（同一张背景板的云层，按亮度做遮罩 → 巨像立在云里，不是飘着）
            cl = self.sky[int(54 - cr * 0.3):int(54 - cr * 0.3) + H, int(96 + dx * 0.55):int(96 + dx * 0.55) + W]
            cm = np.clip((cl.mean(-1) - 0.55) * 3.0, 0, 1) * sstep(560, 760, Y)
            fr = fr * (1 - cm[..., None]) + cl * 1.06 * cm[..., None]
            # 眼底两点寒光（63.25 底鼓 + 军鼓）：墨线十字星芒，强度提高
            g = pulse(t, V(63.25), 0.18) * (t >= V(63.25))
            for ex in (0.462, 0.536):
                p = src2scr(self.emp, anc, dst, s, (ex, 0.150))
                fr = star(fr, p, g * 0.9, 60, 16)
            # 中景远山：代码山脊（顶点高低随机、上缘墨线、下沿随视差滑动，不是背景板切出来的横条）
            mtn = K.mountains(W, H, 835, 64, 3141, 5)                      # 缓存的山形（标量基线），按视差上下平移
            mtn = cv2.warpAffine(mtn, np.float32([[1, 0, dx * 0.7], [0, 1, cr * 0.7]]), (W, H), borderMode=cv2.BORDER_REPLICATE)
            fr = over(fr, mtn * 0.55, (0.10, 0.10, 0.11))
            rg = self.ridge + cr
            rm = K.ridge_mask(H, W, rg)
            fr = over(fr, rm, (0.015, 0.015, 0.015))
            self.sw.pose('stand_wind', (t * 0.3) % 1, t, wind=300)
            fr, _ = self.sw.draw(fr, 960, rg[960] + 6, 46, rim_color=(0.9, 0.9, 0.9), rim_dir=(0, -1))
            return cam(fr, 1.0 + 0.03 * u, 0, 0), 0

    # ================================================================== S032 「正 邪」重做分镜：白 / 红两格分镜 —— 谁定正邪
    #   1910 斜斩擦入：白纸半格 | 血红速度线半格（C1_split_bg），中缝是干笔墨线
    #   「正」字头 1914：太上皇脸（C1_emp）砸进白格（定「正」的人）；「邪」字头 1930：鬼屠脸（C1_gt_face）砸进红格（被定为「邪」的人）
    #   65.085（T_CUT）：一道干笔墨斩痕沿中缝竖劈，两格错开，缝里白热 + 血红火星；「一方」65.21 再一推
    class S032D(S032):
        def __init__(self):
            self.bg = plate(C1 + 'C1_split_bg.png')
            r = self.bg[..., 0] - self.bg[..., 1]
            bx = np.full(H, 1040.0, np.float32)
            for y in range(H):
                xs = np.nonzero(r[y, 700:1400] > 0.4)[0]
                if len(xs): bx[y] = 700 + xs[0]
            bx = cv2.GaussianBlur(bx[:, None], (0, 0), 6)[:, 0]
            yy = np.arange(H, dtype=np.float32); c = np.polyfit(yy, bx, 1)
            self.P0 = np.array([np.polyval(c, 0.0), 0.0]); self.d = np.array([c[0], 1.0]) / math.hypot(c[0], 1.0)
            self.left = np.clip((bx[:, None] - 6 - X) / 8, 0, 1).astype(np.float32)        # 白格（左）蒙版
            self.right = np.clip((X - bx[:, None] - 6) / 8, 0, 1).astype(np.float32)
            self.emp = shaped_bottom(flut('C1_emp', 0.6), 0.80, 0.10, 0.08, 32)     # 下颌以下按云形 / 撕口淡出，不平切
            self.gt = shaped_bottom(flut('C1_gt_face', 0.8), 0.78, 0.10, 0.08, 33)
            self.T_Z, self.T_X = V(CT(13, 4)), V(CT(13, 5))
        def panels(self, t):
            fr = self.bg.copy()
            u = self.u(t)
            for sp, T0, msk, anc, dst, s0, drift in ((self.emp, self.T_Z, self.left, (0.5, 0.40), (520, 520), 0.80, 30),
                                                      (self.gt, self.T_X, self.right, (0.5, 0.36), (1430, 500), 0.82, -30)):
                if t < T0: continue
                k = eout(clamp01((t - T0) / 0.12), 2)
                s = s0 * (1.12 - 0.12 * k) * (1 + 0.03 * u)
                lay, A = draw(sp, np.zeros_like(fr), t, anc, (dst[0] + drift * u, dst[1]), s, wind_amp=9, extra_A=msk)
                nf = int(round((t - T0) * 30))
                if nf == 0:                                        # 砸入帧：格内反相（漫画冲击）
                    base = fr * (1 - A[..., None]) + lay
                    l = base.mean(-1, keepdims=True)
                    neg = np.clip(1.0 - l, 0, 1) * np.ones(3, np.float32)
                    fr = fr * (1 - msk[..., None]) + neg * msk[..., None]
                else:
                    fr = fr * (1 - A[..., None]) + lay
            return fr
        def render(self, t):
            u = self.u(t)
            fr = self.panels(t)
            q = t - self.T_CUT
            if q >= -1 / 30:                                       # 竖劈：墨斩痕沿中缝落下（命中前一帧起笔）
                P = self.P0 + self.d * 60; Q = self.P0 + self.d * 1040
                fr = BR.paint(fr, P, Q, head=clamp01((q + 1 / 30) / 0.07), wk=0.32, color=(0.02, 0.02, 0.02))
            if q > 0:
                e = eout(q / 0.35, 4)
                fr, gm, sd = split_frame(fr, self.P0, self.d, 2 + 40 * e, 140 * e)
                core = np.exp(-(sd / 4) ** 2) * math.exp(-q / 0.3)
                fr = fr * (1 - gm[..., None]) + gm[..., None] * (0.02 + BLOOD * 0.6 * math.exp(-q / 0.6))
                fr = fr + core[..., None] * 1.6 * gm[..., None] + K.blur_ds(gm, 30)[..., None] * BLOOD * 0.6 * math.exp(-q / 0.4)
                fr = sparks2(fr, t, 3201, (1040, 540), n=60, life=0.7, speed=(300, 1100), dirc=(1, 0), spread=1.6, grav=700,
                             burst=True, t0=self.T_CUT, area=(10, 380))
            k = pulse(t, self.T_Z, 0.1) * (t >= self.T_Z) + pulse(t, self.T_X, 0.1) * (t >= self.T_X) \
                + 1.3 * pulse(t, self.T_CUT, 0.1) * (t >= self.T_CUT) + 0.5 * pulse(t, V(65.213), 0.1) * (t >= V(65.213))
            dx, dy, dr = shake(t, 12 * k, 14, 32)
            fr = cam(fr, (1.03 + 0.04 * eio(u)) * (1 + 0.03 * k), dx, dy, dr)
            return fr, (3 if k > 0.6 else 0)

    # ================================================================== S033 LS 大地裂开、白石巨墙轰然升起；鬼屠背影（前景左下）
    class S033D(S033):
        HOR = 700
        def __init__(self):
            self.sky = plate(C1 + 'C1_plain.png', sat=0.0)                   # 荒原（去色：墙升起前天地黑白）
            w = plate(C1 + 'C1_wall.png', (2400, 1350))
            yy = np.linspace(0, 1, 760, dtype=np.float32)[:, None, None]
            self.wall = np.ascontiguousarray(w[:760]) * (1.0 - 0.32 * yy)
            g = np.clip((Y - self.HOR) / (H - self.HOR), 0, 1)
            self.ground = ((0.05 + 0.10 * g * K.fbm(H, W, 334, 8, 6)) * (0.7 + 0.3 * ((X.astype(int) // 3 + Y.astype(int) // 3) % 2)))[..., None] \
                * np.ones(3, np.float32)
            self.gm = (Y >= self.HOR).astype(np.float32)
            self.crack = K.crack_path((180, self.HOR + 4), (1740, self.HOR + 10), 335, n=60, jag=0.01)
            self.sp = flut('C1_gt_back', 1.0)
            self.dust_t = K.tile(512, 332, 5, 5)
        def wall_top(self, t):
            return self.HOR - 560 * eout((t - self.t0 - 0.05) / 1.2, 3)
        def render(self, t):
            u = self.u(t)
            fr = self.sky * (1 - self.gm[..., None]) + self.ground * self.gm[..., None]
            top = self.wall_top(t); hh = int(self.HOR - top)
            if hh > 2:
                q = np.float32([[-60, top], [1980, top], [1980, self.HOR], [-60, self.HOR]])
                wl = K.warp_quad(self.wall[:hh], q)
                m = np.zeros((H, W), np.float32); cv2.fillConvexPoly(m, q.astype(np.int32), 1.0, cv2.LINE_AA)
                fr = fr * (1 - m[..., None]) + wl
                ed = np.zeros((H, W), np.float32); cv2.line(ed, (-60, int(top)), (1980, int(top)), 1.0, 4, cv2.LINE_AA)
                fr = over(fr, ed, (0.0, 0.0, 0.0))
            cm = K.draw_crack((H, W), self.crack, 3, branches=10, seed=336, prog=eout((t - self.t0) / 0.3))
            fr = over(fr, cm, (0.0, 0.0, 0.0))
            # 尘浪（灰墨网点）
            dm = cv2.resize(K.tile_crop(self.dust_t, t * 60, -t * 90, H // 4, W // 4), (W, H))
            band = np.exp(-((Y - self.HOR + 40) / 120) ** 2) * (0.3 + 0.7 * math.exp(-(t - self.t0) / 1.2))
            dmask = np.clip((dm - 0.3) * 1.8, 0, 1) * band * 0.8
            fr = over(fr, dmask * (0.6 + 0.4 * ((X.astype(int) // 4 + Y.astype(int) // 4) % 2)), (0.55, 0.55, 0.55))
            # 墙顶落石（生图碎块）
            for k_ in range(3):
                fr = debris(fr, t, self.t0 + 0.15 + 0.35 * k_, (960, self.wall_top(self.t0 + 0.15 + 0.35 * k_)), 3370 + k_, n=9,
                            speed=(60, 260), up=120, grav=1500, size=(0.10, 0.28), area=(860, 4), life=1.0)
            # 前景：鬼屠背影（左下，近景）
            fr, _ = put_foot(self.sp, fr, t, 760, (330, 1150), wind_amp=-14)
            fr = ink_dust(fr, t, 3380, n=60, amt=0.6, drift=(40, -30), size=(2, 5))
            dx, dy, dr = shake(t, 10 * (0.5 + 0.5 * math.exp(-(t - self.t0) / 1.0)), 11, 33)
            return cam(fr, 1.0 + 0.08 * eio(u), dx, dy, dr), 0

    # ================================================================== S034 ECU 白石巨墙仰拍（变焦推拉）；68.89「墙」：血光从砖缝炸开 + 碎块迸出
    class S034D(S034):
        def __init__(self):
            w = plate(C1 + 'C1_wall.png', (2400, 1350))
            w = np.vstack([w, w[::-1]])                            # 2700 行，供仰摇
            lum = w.mean(-1)
            self.seam = np.clip((cv2.GaussianBlur(lum, (0, 0), 5) - lum) * 5, 0, 1) * (lum < 0.4)
            xx = np.linspace(0, 1, w.shape[1], dtype=np.float32)[None, :, None]
            self.wall = (w * (0.86 - 0.28 * xx)).astype(np.float32)           # 压低：保纯黑砖缝和网点密度
            self.dtex = K.tile(512, 3403, 4, 5)
        def render(self, t):
            u = self.u(t)
            off = int(260 * min(1.2, max(0.0, u)))
            q = self.quad(t)
            fr = K.warp_quad(self.wall[off:off + 1300], q)
            sw_ = K.warp_quad(self.seam[off:off + 1300], q)
            topy = q[0][1]
            fr = fr * np.clip((Y - topy) / 520, 0, 1)[..., None] ** 1.3
            p1 = clamp01((t - self.t0 - 0.1) / (self.T_POP - self.t0 - 0.1))
            rr = np.sqrt(((X - 900) / 1.25) ** 2 + (Y - 560) ** 2)
            if t < self.T_POP:
                dg = 0.5 + 0.5 * np.sin(X / 5.2) * np.sin(Y / 5.2)          # 网点（不是平滑径向光斑）
                gm = np.exp(-(rr / (140 + 200 * eio(p1))) ** 2) * eio(p1) ** 2 * (0.10 + 0.26 * dg)
            else:
                a = t - self.T_POP
                R = 300 + 1400 * eout(a / 0.6, 2)
                dg = 0.5 + 0.5 * np.sin(X / 5.2) * np.sin(Y / 5.2)
                gm = (np.exp(-(rr / 420) ** 2) * (0.14 + 0.22 * dg) * (0.7 + math.exp(-a / 0.35))
                      + np.exp(-((rr - R) / 240) ** 2) * (0.25 + 0.45 * dg) * math.exp(-a / 0.4))
            nf = int(round((t - self.T_POP) * 30))
            gm = gm * {-1: 0.55, 0: 1.9, 1: 0.9}.get(nf, 1.0)
            sl = np.clip(K.blur_ds(sw_, 2) * gm * 2.5, 0, 1)
            fr = fr * (1 - sl[..., None]) + sl[..., None] * BLOOD * 1.2           # 血光从砖缝渗出
            fr = fr + K.blur_ds(sl, 14)[..., None] * BLOOD * 0.5
            if nf == 0: fr = fr + np.exp(-(rr / 360) ** 2)[..., None] * 0.6         # 卡点白闪（只在中心）
            if t >= self.T_POP:
                a = t - self.T_POP
                fr = debris(fr, t, self.T_POP, (900, 560), 3402, n=14, speed=(900, 2200), up=300, grav=2600, size=(0.25, 0.75),
                            toward=0.6, life=0.55, area=(80, 50))
                qd = clamp01(a / 0.733); R = 80 + 340 * eout(qd, 2)
                cloud = np.exp(-((((X - 900) / 1.25) ** 2 + (Y - 560) ** 2) / (2 * R * R)))
                nz = cv2.resize(K.tile_crop(self.dtex, a * 60, a * 25, H // 8, W // 8), (W, H))
                dm = np.clip(cloud * (0.55 + 0.6 * nz) * 0.7 * (1 - qd), 0, 0.7)
                fr = fr * (1 - dm[..., None]) + 0.6 * dm[..., None]
            dx, dy, dr = shake(t, 8 * pulse(t, self.T_POP, 0.25) * (t >= self.T_POP) + 2, 7, 34)
            if nf in (0, 1): dx, dy = dx + (6, -5)[nf], dy + (-5, 6)[nf]
            if nf == -1: fr = fr * 0.85
            return cam(fr, 1.0 + 0.05 * u, dx, dy, dr), 0

    # ================================================================== S035 「那就劈开它」样镜按 74 分评审返工
    #   2089–2094 冲刺（D035_dash，身体随步幅起伏 + 前倾）→ 2095–2098 起刀（C1_strike，刀举过顶）：两个姿势 + 起伏，背景白石墙疾掠
    #   2099 一闪帧：出刀姿势硬边反白（黑底白身、线稿反相），一条血红线沿刀身贯穿全画面
    #   2100「劈」：斩后背影定姿（C1_after_back 重抽），墙沿「刀身延长线」劈开 —— 干笔飞白斩痕（C1_slash）从刀尖起笔、向左上延伸出画，
    #        脸与刀痕在一条对角线上；缝里血红速度线（D035_gap），白热缝心；生图碎块从缝里迸出（2103 再扑向镜头）
    #   残心 2104–2127：红带 / 发丝 / 衣摆拆层风吹（私有精灵风权重），斩痕渗血往下淌，墙灰与小碎块从缝里飘落，缓推向脸–刀痕对角
    class S035D2(S035Sprite):
        T_K2 = V(70.582)
        AFT_H, AFT_FOOT = 770.0, (740.0, 925.0)
        def __init__(self):
            self.wallA = plate(C1 + 'C1_wall.png', (2496, 1404), gain=0.72)
            self.wallC = plate(C1 + 'C1_wall.png', gain=0.72)
            self.gapp = plate(R1 + 'D035_gap.png')
            self.dash = flut('dash', 0.8, R1 + 'D035_dash_cut.png')
            self.dash2 = flut('C1_dash2', 0.8); self.strike = flut('C1_strike', 0.8)
            self.after = flut('C1_after_back', 1.2)
            # 斩后：刀身方向（精灵内实测主轴）→ 画面里的刀尖与劈缝直线
            a_, s_ = self.after.fit(self.AFT_H)
            self.aft = (a_, s_)
            tip = src2scr(self.after, a_, self.AFT_FOOT, s_, (0.915, 0.979))
            d = np.array([0.80, -0.60]); d /= np.linalg.norm(d)              # 刀路：右上 → 刀尖（斜劈落点）；不穿过人物
            self.tip, self.d = np.array(tip), d
            self.n = np.array([-d[1], d[0]])
            self.P0 = self.tip                                             # 劈缝过刀尖
            self.Q = self.tip + d * 1150                                   # 斩痕：画外右上起笔（重端）→ 收笔在刀尖（尖端）
            self.gc = self.tip + d * 380
            gk = self.tip + d * 1250                                       # 爆光白芯放在画外（缝的起笔端），缝内只见血红速度线
            gp = cv2.warpAffine(self.gapp, np.float32([[2.0, 0, gk[0] - 960 * 2.0], [0, 2.0, gk[1] - 540 * 2.0]]), (W, H),
                                borderMode=cv2.BORDER_REFLECT)
            self.gapp = gp
            # 出刀姿势：刀身方向（精灵实测）
            self.sd_dir = np.array([0.733, 0.68]); self.sd_dir /= np.linalg.norm(self.sd_dir)
        def _gap(self, t):
            if t < self.T_HIT: return 0.0, 0.0
            g = 40 + 16 * eout((t - self.T_HIT) / 0.09, 2)
            if t >= self.T_LAND:
                a = t - self.T_LAND
                g = 56 + 50 * eout(a / 0.07, 2) + 26 * eio(a / 0.85)
            return g, g * 0.5
        DASH_STEPS = ((V(69.80), 'dash'), (V(69.87), 'dash2'), (V(69.93), 'strike'))   # 三姿势按拍硬切（图生图衍生，同角色同画面）
        def _pose_at(self, t):
            nm = 'dash'
            for T0, n in self.DASH_STEPS:
                if t >= T0 - 1e-6: nm = n
            return nm
        def _dashpanel(self, t):
            k = clamp01((t - self.t0) / (self.T_STRK - self.t0))
            ox = 60 + 420 * k
            fr = K.motion_blur(self.wallA[170:170 + H, int(ox):int(ox) + W].copy(), 46, 0)
            fr = speed_lines(fr, t, 3561, 0.8)
            nm = self._pose_at(t)
            sp = getattr(self, nm)
            spw = {'dash': 620, 'dash2': 630, 'strike': 640}[nm]
            step = int(round((t - self.t0) * 30)) % 3                      # 3 帧一步的起伏（姿势之间靠硬切，不再整张摆动）
            bob = (0, -13, 0)[step]
            a_, s_ = sp.fit(spw * (1 + 0.03 * k))
            fx = {'dash': 690 + 90 * eout(k, 2), 'dash2': 760 + 90 * eout(k, 2), 'strike': 820 + 40 * eout(clamp01((t - V(69.93)) / 0.06), 2)}[nm]
            fr, A = draw(sp, fr, t, a_, (fx, 975 - bob), s_, rot=(-1.5 * k + (2.5, 0, -2)[step]) * (nm != 'strike'), mblur=(12, 0),
                         wind_amp=12 if nm != 'strike' else 14)
            return fr, A
        def _impact(self, t):
            """一闪帧：出刀姿势硬边反白 + 血红线贯穿全画面"""
            fr = np.zeros((H, W, 3), np.float32) + 0.015
            fr = speed_lines(fr, t, 3563, 1.0, n=90)
            a_, s_ = self.strike.fit(660)
            foot = (840.0, 975.0)
            lay, A = draw(self.strike, np.zeros_like(fr), t, a_, foot, s_, wind_amp=0, breathe=0)
            Ah = (A > 0.5).astype(np.float32)
            l = (lay.mean(-1) / np.maximum(A, 1e-3))
            ink = np.clip(1.15 - l * 1.4, 0, 1)                              # 线稿反相：黑袍成白、白高光成黑线
            fr = fr * (1 - Ah[..., None]) + (ink * Ah)[..., None]
            p = src2scr(self.strike, a_, foot, s_, (0.879, 0.663))
            d = self.sd_dir
            sd = (X - p[0]) * (-d[1]) + (Y - p[1]) * d[0]
            line = np.clip(4.5 - np.abs(sd), 0, 1)
            fr = fr * (1 - line[..., None]) + line[..., None] * BLOOD * 1.25
            return fr
        def _wall(self, t):
            wall = self.wallC.copy()
            wall = BR.paint(wall, self.Q, self.P0, 1.0, wk=0.55)            # 干笔飞白斩痕：右上画外起笔（重端），收笔尖端落在刀尖
            # 斩痕渗血：沿斩痕下沿往下淌的血墨线
            a = t - self.T_HIT
            if a > 0.05:
                r = np.random.default_rng(3599)
                Lb = np.zeros((H // 2, W // 2), np.float32)
                for i in range(14):                                        # 每滴的随机量一次取齐（不因提前 continue 让随机流错位 → 不闪）
                    s, dy0, l0, dl, wd = r.uniform(0.05, 0.75), r.uniform(6, 26), r.uniform(40, 160), r.uniform(0, 0.3), int(r.uniform(2, 5))
                    x0, y0 = self.P0 + self.d * 1150 * s
                    y0 += dy0
                    ln = (40 + l0) * eout((a - 0.05 - dl) / 0.8, 2)
                    if ln <= 1: continue
                    cv2.line(Lb, (int(x0 / 2), int(y0 / 2)), (int(x0 / 2 + r.normal(0, 2)), int((y0 + ln) / 2)), 1.0, wd, cv2.LINE_AA)
                    cv2.circle(Lb, (int(x0 / 2), int((y0 + ln) / 2)), wd + 1, 1.0, -1, cv2.LINE_AA)
                Lb = cv2.resize(cv2.GaussianBlur(Lb, (0, 0), 0.6), (W, H))
                ink = np.clip(cv2.dilate(Lb, np.ones((5, 5), np.uint8)) - Lb, 0, 1)
                wall = over(wall, ink * 0.8, (0.02, 0.02, 0.02)); wall = over(wall, Lb, BLOOD * 0.85)
            g, slide = self._gap(t)
            fr, gm, sd = split_frame(wall, self.P0, self.d, g, slide)
            hot = 1.0 + 0.9 * math.exp(-a / 0.10) + 0.6 * pulse(t, self.T_LAND, 0.10) * (t >= self.T_LAND) \
                + 0.45 * pulse(t, self.T_K2, 0.10) * (t >= self.T_K2)
            gp = self.gapp * (0.85 + 0.2 * math.sin(t * 23)) * hot
            gp = gp + np.exp(-(sd / 4.0) ** 2)[..., None] * 1.2 * math.exp(-a / 0.08)
            fr = fr * (1 - gm[..., None]) + gp * gm[..., None]
            ink = np.exp(-((np.abs(sd) - g / 2) / 2.2) ** 2)
            fr = fr * (1 - 0.9 * ink)[..., None]
            return fr, gm
        def render(self, t):
            if t < self.T_STRK:
                fr, _ = self._dashpanel(t)
                z = 1.0 + 0.035 * eio(clamp01((t - self.t0) / (self.T_STRK - self.t0)))
                dx, dy, dr = shake(t, 3, 9, 3561)
                return cam(fr, z, dx, dy, dr), 0
            if t < self.T_HIT:
                return cam(self._impact(t), 1.03, 0, 0), 4
            a = t - self.T_HIT
            fr, gm = self._wall(t)
            u = clamp01((t - self.T_HIT) / (self.t1 - self.T_HIT))
            par = 12 * (u - 0.5)
            k = eout(clamp01(a / 0.10), 2)
            a_, s_ = self.aft
            fr, A = draw(self.after, fr, t, a_, (self.AFT_FOOT[0] + par - 14 * (1 - k), self.AFT_FOOT[1]), s_ * (1.03 - 0.03 * k),
                         mblur=(-12 * (1 - k), 0), wind_amp=16, breathe=0.004)
            # 火星（白 + 血红）沿劈缝三处迸发
            for i, s in enumerate((0.25, 0.45, 0.65)):
                o = tuple(self.P0 + self.d * 1150 * s)
                fr = sparks2(fr, t, 3570 + i, o, n=26, life=0.5, speed=(400, 1300), dirc=(-self.n[0], -self.n[1]), spread=1.1, grav=900,
                             burst=True, t0=self.T_HIT, area=(50, 16))
            # 生图碎块：命中从缝里迸出；二次冲击扑向镜头
            fr = debris(fr, t, self.T_HIT, tuple(self.gc), 3591, n=10, speed=(500, 1400), up=300, grav=2200, size=(0.2, 0.55),
                        dirc=(-self.n[0], -self.n[1]), spread=1.0, area=(300, 40), life=0.7)
            fr = debris(fr, t, self.T_LAND, tuple(self.gc), 3592, n=8, speed=(300, 900), up=100, grav=600, size=(0.5, 1.0),
                        toward=0.9, area=(400, 120), life=0.4)
            # 残心：墙灰飘落 + 小碎块从缝沿掉落
            if a > 0.25:
                fr = ink_dust(fr, t, 3593, n=70, amt=0.7, drift=(-8, 70), size=(2, 4), region=(900, 120, W, 960))
                for j in range(3):
                    fr = debris(fr, t, self.T_HIT + 0.30 + 0.2 * j, tuple(self.P0 + self.d * 1150 * (0.15 + 0.2 * j)), 3594 + j, n=2,
                                speed=(20, 60), up=0, grav=1400, size=(0.10, 0.18), area=(10, 4), life=0.8)
            x, y = X, Y
            nf = int(round(a * 30))
            if nf == 0:                                            # 命中：硬边整帧白闪（对齐 74 分样镜密度）
                fr = fr * 0.30 + 0.72
            if nf == 1:
                fr = fr * 0.80 + 0.16
            if int(round((t - self.T_LAND) * 30)) == 0:            # 二次冲击：再闪一帧 + 火星
                fr = fr * 0.42 + 0.55
                fr = sparks2(fr, t, 3597, tuple(self.gc), n=40, life=0.5, speed=(400, 1500), dirc=(-self.n[0], -self.n[1]),
                             spread=1.4, grav=900, burst=True, t0=self.T_LAND, area=(220, 120))
            sk = pulse(t, self.T_HIT, 0.10) + 0.9 * pulse(t, self.T_LAND, 0.10) * (t >= self.T_LAND) \
                + 0.35 * pulse(t, self.T_K2, 0.08) * (t >= self.T_K2)
            dx, dy, dr = shake(t, 26 * sk + 1.5, 16, 3562)          # 命中 14px（shake 内部系数 0.6 → 幅度加倍）
            cx, cy = (self.tip[0] * 0.5 + 724 * 0.5, self.tip[1] * 0.5 + 240 * 0.5)     # 推镜中心：脸（左上）–刀尖（右下）对角中点
            z = 1.0 + 0.07 * eio(u) + 0.03 * sk
            ca = 4 if nf in (0, 1) or int(round((t - self.T_LAND) * 30)) == 0 else 0
            return cam(fr, z, dx, dy, dr, center=(cx, cy)), ca

    # ================================================================== S036 CU 墙缝一线白光（体积光），沿缝推进；前景生图碎块虚焦
    class S036D(S036):
        """S035 劈缝的特写：白石墙沿同一方向（右上 → 左下）被劈开，缝里血红速度线 + 白热缝心，体积光向镜头散；沿缝推进"""
        def __init__(self):
            w = plate(C1 + 'C1_wall.png', (3456, 1944))
            self.wall = np.ascontiguousarray(w[300:300 + 1300, 400:400 + 2400] * 0.56).astype(np.float32)
            self.gapp = plate(R1 + 'D035_gap.png', (2400, 1350))[:1300]
            self.d = np.array([-0.80, 0.60])
            self.fogt = K.tile(512, 363, 5, 5)
        def render(self, t):
            u = self.u(t); e = eio(u)
            ox, oy = 380 - 300 * e, 60 + 160 * e                        # 沿缝向左下推进
            M = np.float32([[1, 0, -ox], [0, 1, -oy]])
            wall = cv2.warpAffine(self.wall, M, (W, H), borderMode=cv2.BORDER_REFLECT)
            P0 = np.array([1180.0, 540.0])
            g = 58 + 8 * math.sin(t * 7)
            fr, gm, sd = split_frame(wall, P0, self.d, g, 18)
            breath = 0.95 + 0.15 * math.sin(t * 9)
            # 缝内：沿缝方向的白色干线（长短粗细随机）+ 血红墨点（不是红白格丝带）
            r = np.random.default_rng(3605)
            Lw = np.zeros((H // 2, W // 2), np.float32); Lr = np.zeros_like(Lw)
            d_ = self.d; n_ = np.array([-d_[1], d_[0]])
            for i in range(70):
                s0 = r.uniform(-0.55, 0.55); off = r.normal(0, 10)
                b0 = P0 + d_ * s0 * 1000 + n_ * off; ln = r.uniform(40, 320)
                b1 = b0 + d_ * ln
                cv2.line(Lw, (int(b0[0] / 2), int(b0[1] / 2)), (int(b1[0] / 2), int(b1[1] / 2)), r.uniform(0.4, 1.0),
                         1 if r.random() < 0.7 else 2, cv2.LINE_AA)
            for i in range(90):
                s0 = r.uniform(-0.6, 0.6); off = r.normal(0, 16)
                b0 = P0 + d_ * s0 * 1000 + n_ * off
                cv2.circle(Lr, (int(b0[0] / 2), int(b0[1] / 2)), max(1, int(r.uniform(2, 22) / 2)), r.uniform(0.4, 1.0), -1, cv2.LINE_AA)
            Lw = cv2.resize(cv2.GaussianBlur(Lw, (0, 0), 0.7), (W, H)) * breath
            Lr = cv2.resize(cv2.GaussianBlur(Lr, (0, 0), 1.0), (W, H)) * breath
            gp = Lw[..., None] * 1.15 * breath + Lr[..., None] * BLOOD * 0.9
            gp = gp + np.exp(-(sd / 2.5) ** 2)[..., None] * 1.1
            fr = fr * (1 - gm[..., None]) + gp * gm[..., None]
            ink = np.exp(-((np.abs(sd) - g / 2) / 2.2) ** 2)
            fr = fr * (1 - 0.9 * ink)[..., None]
            spill = np.clip(K.blur_ds(gm, 40) * 1.4 - gm, 0, None)
            fr = fr * (1 - 0.25 * spill[..., None]) + spill[..., None] * BLOOD * 0.35
            fr = ray_lines(fr, (1180, 540), 0.45 * breath, 3601 + int(t * 15), n=60, r0=60, r1=1300)
            fr = ink_dust(fr, t, 3640, n=90, amt=0.7, size=(1, 4), drift=(25, -20))
            fr = cam(fr, 1.0 + 0.15 * e, 0, 0, center=(1180, 540))
            for j in range(3):                                         # 缝沿掉落的小碎块（生图，清晰）
                fr = debris(fr, t, self.t0 + 0.1 + 0.4 * j, (1180 + 260 * (j - 1) * 0.8, 540 - 260 * (j - 1) * 0.6), 3650 + j, n=3,
                            speed=(20, 80), up=0, grav=1300, size=(0.12, 0.22), area=(20, 6), life=0.9)
            return fr, 0

    # ================================================================== S037 ELS 长墙一线白缝，鬼屠背影立于缝前；「亮」光爆
    class S037D(S037):
        """长墙远景（专用背景板 C1_wall37），一线白缝，背影立于缝前；「亮」光爆 + 集中线"""
        def __init__(self):
            self.bg = plate(C1 + 'C1_wall37.png', (2112, 1188))
            self.sp = flut('C1_gt_back', 1.0)
            cr = K.crack_path((self.CX - 10, 330), (self.CX + 6, 820), 371, n=30, jag=0.04)
            self.cm = K.draw_crack((H, W), cr, 2.2, branches=3, seed=372)
            self.gm = sstep(820, 860, Y).astype(np.float32)
        def render(self, t):
            u = self.u(t)
            fr = self.bg[54:54 + H, 96:96 + W].copy()
            t_l = V(CT(15, 8))
            fl = 0.9 + 0.2 * math.sin(t * 11) + 1.2 * pulse(t, t_l, 0.5) * (t >= t_l)
            cm = self.cm
            fr = over(fr, K.blur_ds(cm, 14) * 0.9, (0.02, 0.02, 0.02))           # 缝两侧墨晕（白光靠黑衬出来）
            fr = fr * (1 - cm[..., None]) + cm[..., None] * min(1.3, fl)
            fr = fr + (K.blur_ds(cm, 50) * 0.8)[..., None] * BLOOD * fl * 0.6
            fr = ray_lines(fr, (self.CX, 580), 0.45 * min(1.6, fl), 3701 + int(t * 15), n=60, r0=40, r1=900)
            refl = (np.exp(-np.abs(X - self.CX) / 30) * np.exp(-np.maximum(Y - 830, 0) / 50) * 0.5 * self.gm)[..., None]
            fr = fr * (1 - refl) + refl
            fr, _ = put_foot(self.sp, fr, t, 330, (self.CX + 6, 870), wind_amp=-12)
            e = eio(u)
            return cam(fr, 1.1 - 0.1 * e, 0, 40 - 70 * e, center=(self.CX, 600)), 0

    # ================================================================== S038 CU 刃面倒映寒眼（生图），血墨沿刃流下；巨字「血」去掉
    class S038D(S038):
        def __init__(self):
            self.bg = plate(C1 + 'C1_bg038.png', gain=0.78)                # 白纸 + 墨溅（不与 S028 血墨底复用，不虚焦）
            self.bl = flut('C1_blade_eye', 0.0)
        def render(self, t):
            u = self.u(t); e = eio(u)
            fr = self.bg.copy()
            s = W / self.bl.w * 1.12
            fr, bm = draw(self.bl, fr, t, (0.5, 0.5), (960, 540), s, wind_amp=0, breathe=0)
            # 刃面冷光扫过
            q = clamp01((t - self.t0) / 0.8)
            band = np.exp(-(((X - (-300 + 2600 * q)) + (Y - 540) * 0.53) / 80) ** 2) * bm
            fr = fr + band[..., None] * 0.35
            # 血墨沿刃背流下（左上 → 右下），墨线描边
            d = np.array([1.0, 0.53]); d /= np.linalg.norm(d); n = np.array([-d[1], d[0]])
            p0 = np.array([60.0, 60.0])
            head = 0.15 + 0.65 * eio((t - self.t0) / 1.0)
            path = [p0 + d * 2100 * s_ + n * (150 + 8 * math.sin(s_ * 30)) for s_ in np.linspace(0, head, 50)]
            Lb = np.zeros((H // 2, W // 2), np.float32)
            P = (np.array(path) * 2).astype(np.int32)
            for i in range(len(P) - 1):
                cv2.line(Lb, tuple(P[i]), tuple(P[i + 1]), 1.0, 5, cv2.LINE_AA, 2)
            cv2.circle(Lb, tuple(P[-1] // 4), 9, 1.0, -1, cv2.LINE_AA)
            Lb = cv2.resize(cv2.GaussianBlur(Lb, (0, 0), 1), (W, H)) * bm
            ink = np.clip(cv2.dilate(Lb, np.ones((5, 5), np.uint8)) - Lb, 0, 1)
            fr = over(fr, ink, (0.02, 0.02, 0.02)); fr = over(fr, Lb, BLOOD * 0.95)
            hy = path[-1][1]
            z = 1.0 + 0.06 * pulse(t, self.t0, 0.15)
            fr = cam(fr, z * 1.05, 0, (hy - 540) * 0.2 - 30 + 60 * e)
            return fr, (3 if V(CT(16, 2)) <= t < V(CT(16, 2)) + 0.1 else 0)

    # ================================================================== S039 MS 战后断枪，鬼屠缓步穿过；两步态交替 + 起伏，墨线细雨
    class S039D(S039):
        def __init__(self):
            self.bg = plate(C1 + 'C1_battle.png', (2304, 1296), gain=0.88)
            self.wa = flut('C1_walk_a', 1.0); self.wb = flut('C1_walk_b', 1.0)
        def render(self, t):
            u = self.u(t)
            off = 320 * u
            fr = self.bg[100:100 + H, int(60 + off * 0.5):int(60 + off * 0.5) + W].copy()
            ph = (t - self.t0) / 0.36                                    # 一步 0.36s：两步态交替
            sp = self.wa if int(ph) % 2 == 0 else self.wb
            bob = 8 * abs(math.sin(math.pi * ph))
            fr, _ = put_foot(sp, fr, t, 790, (780 + 60 * u, 1000 - bob), wind_amp=-10, rot=0.8 * math.sin(math.pi * ph))
            fr = ink_rain(fr, t, 394, n=200, amt=0.55 * clamp01((t - self.t0) / 0.6 + 0.3), speed=1500, angle=10, near=0.2)
            dx, dy, dr = shake(t, 6, 1.4, 39)
            return cam(fr, 1.04, dx, dy, dr), 0

    # ================================================================== S040 「是非对错」重做分镜：漫画四格逐拍砸入
    #   2295 撕纸入：白漫画纸（C1_paper），76.54–77.15 墨线分格逐拍画出（76.99 底鼓推一下）
    #   「是」2316 左上白格：鬼屠正脸眼带；「非」2318 右上红格：太上皇眼带；77.455 底鼓推；「对」2329 左下白格：鬼屠侧脸；
    #   「错」2332 右下红格：刀遮半脸；2336–2342 一道血红干笔斩痕斜贯四格、四格沿缝错开（「我自己扛」前的决断）→ 2343 硬切
    class S040D(S040):
        M_, G_ = 70, 26
        def __init__(self):
            self.pap = plate(C1 + 'C1_paper.png')
            red = plate(C1 + 'C1_split_bg.png', gain=0.62, sat=1.35)[:, 1060:]     # 红格压深（不读成粉红）
            x0, x1, y0, y1 = self.M_, W - self.M_, 140, 940
            xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
            g = self.G_ / 2
            self.P = [(x0, y0, xm - g, ym - g), (xm + g, y0, x1, ym - g), (x0, ym + g, xm - g, y1), (xm + g, ym + g, x1, y1)]
            self.masks, self.fill = [], []
            for i, (a, b, c, d) in enumerate(self.P):
                m = np.zeros((H, W), np.float32); m[int(b):int(d), int(a):int(c)] = 1
                self.masks.append(m)
                if i in (1, 3):
                    f = cv2.resize(red, (int(c - a), int(d - b)), interpolation=cv2.INTER_AREA)
                    full = np.zeros((H, W, 3), np.float32); full[int(b):int(d), int(a):int(c)] = f
                    self.fill.append(full)
                else:
                    self.fill.append(None)
            # (精灵, 精灵内眼睛锚点, 目标比例尺)：四格都要读到眼睛
            # 锚点 = 各图实测的眼睛位置（归一化画布坐标）：眼睛对眼睛，脸放大也不会把眼顶出格
            self.sps = [(flut('C1_eyes_gt', 0.8), (0.500, 0.820), 1.0), (flut('C1_eyes_emp', 0.6), (0.505, 0.610), 1.0),
                        (flut('C1_gt_profile', 0.8), (0.265, 0.445), 1.05), (flut('C1_bladeface2', 0.6), (0.500, 0.360), 1.0)]
            self.EY = (0.40, 0.42, 0.42, 0.42)                        # 四格眼睛统一在格高 40–42%（脸的墨重部分占满格子）
            self.bt = K.tile(512, 404, 5, 4)
        def borders(self, t):
            """墨线分格：干笔质感（噪声断墨），逐段画出"""
            L = np.zeros((H, W), np.float32)
            segs = []
            for (a, b, c, d) in self.P:
                segs += [((a, b), (c, b)), ((c, b), (c, d)), ((c, d), (a, d)), ((a, d), (a, b))]
            n = len(segs)
            for i, (p, q) in enumerate(segs):
                st = V(76.60) + 0.55 * i / n
                k = eout(clamp01((t - st) / 0.12), 2)
                if k <= 0: continue
                qx = p[0] + (q[0] - p[0]) * k; qy = p[1] + (q[1] - p[1]) * k
                cv2.line(L, (int(p[0]), int(p[1])), (int(qx), int(qy)), 1.0, 9, cv2.LINE_AA)
            nz = cv2.resize(K.tile_crop(self.bt, 0, 0, H // 3, W // 3), (W, H))
            return np.clip(L * (0.55 + nz * 0.9), 0, 1)
        def render(self, t):
            u = self.u(t)
            fr = self.pap.copy()
            u0 = clamp01((t - self.t0) / 0.7)
            bl = np.clip(K.ink_blot(0.075 * eout(u0, 2), seed=4002, center=(260, 900)) + K.ink_blot(0.06 * eout(u0, 2), seed=4003, center=(1700, 200)), 0, 1)
            fr = fr * (1 - bl[..., None] * 0.9) + bl[..., None] * BLOOD * 0.55     # 前 0.7s 空纸：边角红墨晕（不糊成粉毯）
            for i, (m, T0) in enumerate(zip(self.masks, self.TS)):
                if t < T0: continue
                k = eout(clamp01((t - T0) / 0.12), 2)
                if self.fill[i] is not None:
                    fr = fr * (1 - m[..., None]) + self.fill[i]
                else:
                    fr = fr * (1 - m[..., None] * 0.04)
                sp, anc, s0 = self.sps[i]
                a, b, c, d = self.P[i]
                dst = ((a + c) / 2 + (18 if i % 2 else -18) * eio(u), b + (d - b) * self.EY[i])
                lay, A = draw(sp, np.zeros_like(fr), t, anc, dst, s0 * (1.15 - 0.15 * k) * (1 + 0.02 * u), wind_amp=8, extra_A=m)
                fr = fr * (1 - A[..., None]) + lay
                if int(round((t - T0) * 30)) == 0:                     # 砸入帧：格内反相
                    l = fr.mean(-1, keepdims=True)
                    fr = fr * (1 - m[..., None]) + np.clip(1 - l, 0, 1) * m[..., None]
            bd = self.borders(t)
            fr = fr * (1 - bd[..., None]) + 0.02 * bd[..., None]
            ts = V(77.90)                                               # 决断：血红干笔斩痕斜贯四格、四格沿缝错开
            if t >= ts - 1 / 30:
                P = np.array([180.0, 170.0]); Q = P + np.array([1580.0, 730.0]) / 1740.4 * 2150   # 重端起笔在画外右下
                hd = clamp01((t - ts + 1 / 30) / 0.08)
                if t >= ts:
                    a = t - ts; e = eout(a / 0.15, 3)
                    d = (Q - P) / np.linalg.norm(Q - P)
                    fr, gm, sd = split_frame(fr, P, d, 4 + 14 * e, 40 * e)
                    fr = fr * (1 - gm[..., None]) + gm[..., None] * 0.02
                    fr = sparks2(fr, t, 4005, tuple((P + Q) / 2), n=50, life=0.5, speed=(300, 1200), dirc=(-d[1], d[0]), spread=2.5,
                                 grav=900, burst=True, t0=ts, area=(600, 30))
                fr = BR.paint(fr, Q, P, hd, wk=0.5)
            pk = sum(pulse(t, ts_, 0.1) * (t >= ts_) for ts_ in self.TS) + 0.6 * pulse(t, V(76.991), 0.1) * (t >= V(76.991)) \
                + 0.6 * pulse(t, V(77.455), 0.1) * (t >= V(77.455)) + 1.2 * pulse(t, ts, 0.1) * (t >= ts)
            dx, dy, dr = shake(t, 9 * min(1.5, pk), 14, 40)
            z = (1.0 + 0.06 * eio(u)) * (1 + 0.03 * min(1, pk))
            return cam(fr, z, dx, dy, dr), (3 if pk > 0.9 else 0)

    # ================================================================== S041 LS 背影刀横扛肩，独对白石长墙（一线白缝）
    class S041D(S041):
        """仰拍巨墙（专用背景板 C1_wall41），一线白缝；扛刀背影；墨线雨"""
        def __init__(self):
            self.bg = plate(C1 + 'C1_wall41.png', (2112, 1188))
            cr = K.crack_path((940, 150), (960, 860), 411, n=40, jag=0.05)
            self.cm = K.draw_crack((H, W), cr, 3, branches=5, seed=412)
            self.sp = flut('C1_shoulder', 1.0)
        def render(self, t):
            u = self.u(t); e = eio(u)
            fr = self.bg[30 + int(40 * e):30 + int(40 * e) + H, 96:96 + W].copy()       # 背景板慢升（视差 0.5）
            fl = 0.85 + 0.15 * math.sin(t * 8)
            cm = self.cm
            fr = over(fr, K.blur_ds(cm, 14) * 0.8, (0.02, 0.02, 0.02))
            fr = fr * (1 - cm[..., None]) + cm[..., None] * 1.2 * fl
            fr = fr + K.blur_ds(cm, 60)[..., None] * BLOOD * 0.5 * fl
            fr = ray_lines(fr, (950, 520), 0.3 * fl, 4101 + int(t * 10), n=50, r0=40, r1=1100)
            fr, _ = put_foot(self.sp, fr, t, 1060, (920, 1240), wind_amp=-12)
            fr = ink_rain(fr, t, 413, n=260, amt=0.5, speed=1800, angle=8)
            return cam(fr, 1.0 + 0.05 * e, 0, -50 + 80 * e), 0

    # ================================================================== S042 ELS 白月（生图）→「不」干笔刀光横过月面 → 月洇成血月，天幕红云苏醒
    class S042D(S042):
        def __init__(self):
            self.sky = plate(C1 + 'C1_nightsky2.png', (2016, 1134))     # 换板（与 S045 不再同板）
            l = self.sky.mean(-1, keepdims=True)
            self.sky0 = (l * np.ones(3, np.float32)).astype(np.float32)     # 变色前：去色（红云 = 灰云）
            mo = cv2.cvtColor(cv2.imread(C1 + 'C1_moon_cut.png', cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255
            ys, xs = np.nonzero(mo[..., 3] > 0.5)
            cx, cy, r = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2, (xs.max() - xs.min()) / 2
            s = 240 / r
            M = np.float32([[s, 0, self.MC[0] - cx * s], [0, s, self.MC[1] - cy * s]])
            mF = cv2.warpAffine(mo[..., :3], M, (W, H)); self.mA = cv2.warpAffine(mo[..., 3], M, (W, H))
            ml = mF.mean(-1, keepdims=True)
            self.mW = (ml * 1.08).astype(np.float32)                          # 白月
            self.mR = (np.clip(ml * 1.6, 0, 1) * BLOOD * 1.1 + 0.02).astype(np.float32)   # 血月：同一月面纹理改色
            ang = math.radians(-32); self.dir = np.array([math.cos(ang), math.sin(ang)])
            self.dline = np.abs(-(X - self.MC[0]) * self.dir[1] + (Y - self.MC[1]) * self.dir[0]).astype(np.float32)
            d_ = np.sqrt((X - self.MC[0]) ** 2 + (Y - self.MC[1]) ** 2)
            self.halo = (np.exp(-(np.maximum(d_ - 240, 0) / 110) ** 2) * np.clip((d_ - 236) / 6, 0, 1)).astype(np.float32)
        def render(self, t):
            u = self.u(t)
            a = t - self.T_SL
            sh = int(30 + 60 * eio(u))
            rk = clamp01(a / 0.22) if a >= 0 else 0.0
            sky = self.sky0 * (1 - rk) + self.sky * rk
            fr = sky[54:54 + H, sh:sh + W].copy()
            if a < 0:
                mc = self.mW
            else:
                R = 30 + 1400 * eout(clamp01(a / 0.22), 2)
                m = sstep(R, R - 260, self.dline)[..., None]
                mc = self.mW * (1 - m) + self.mR * m
                fr = fr + self.halo[..., None] * BLOOD * (0.08 + 0.4 * math.exp(-a / 0.25))
            fr = fr * (1 - self.mA[..., None]) + mc * self.mA[..., None]
            q = (t - self.T_SL + 0.05) / 0.3
            if 0 <= q < 0.5:                                             # 干笔刀光（白）横过月面：起划 + 命中 + 两帧余墨
                P = np.array(self.MC) - self.dir * 1350; Q = np.array(self.MC) + self.dir * 1350   # 两端都在画外
                fr = BR.paint(fr, Q, P - self.dir * 500, 1.0, wk=0.42, color=(1.0, 1.0, 1.0),
                              alpha=clamp01(q / 0.14) * (1 - clamp01((q - 0.24) / 0.26)))   # 反向画：收笔端是笔刷尖端（渐细），重端在画外
            if self.T_SL - 1 / 30 <= t < self.T_SL + 3 / 30:              # 「不」字头：星芒 + 轻震
                fr = star(fr, (self.MC[0] - 520, self.MC[1] + 300), 0.9 * (1 - clamp01((t - self.T_SL) / 0.1)), 120, 40)
                dx0, dy0, dr0 = shake(t, 9, 22, 425)
                fr = cam(fr, 1.0, dx0, dy0, dr0)
            if 0 <= a < 1 / 30 + 1e-3: fr = fr * 0.7 + BLOOD * 0.3 + 0.05
            k = pulse(t, self.T_PAN, 0.12) * (t >= self.T_PAN)
            z = (1.0 + 0.06 * eio(u)) * (1 + 0.10 * k)
            dx, dy, dr = shake(t, 12 * k, 14, 42)
            fr = cam(fr, z, dx, -30 * eio(u) + dy, 3 * eio(u) + dr)
            if self.T_PAN <= t < self.T_PAN + 2 / 30 + 1e-3: fr = fr * 0.5 + BLOOD * 0.6
            if V(80.86) <= t < V(80.86) + 1 / 30 + 1e-3: fr = fr + 0.25
            return fr, (4 if k > 0.4 else 0)

    # ================================================================== S043 MCU 侧脸 → 转头正视镜头（两张生图，转头甩入），眼中寒光
    class S043D(Shot):
        T_SW = V(82.15)
        T_GLINT = 82.62
        def __init__(self):
            self.bg = plate(C1 + 'C1_bg043.png', (2016, 1134), gain=1.50)     # 雨夜专用背景板，不虚焦（清晰墨线）
            self.pf = flut('C1_gt_profile', 1.0); self.fc = flut('C1_gt_face', 1.0)
        def render(self, t):
            u = self.u(t)
            o = int(48 - 30 * eio(u))
            fr = self.bg[27:27 + H, o:o + W].copy()                       # 背景横移（视差 0.3）
            fr = ink_rain(fr, t, 4303, n=300, amt=0.35, speed=1500, angle=10, length=(20, 50), near=0.0)
            z = 0.98 * (1 + 0.08 * eout(u, 2))
            if t < self.T_SW:
                fr, _ = draw(self.pf, fr, t, (0.47, 0.43), (1000, 470), z, wind_amp=-12)
            else:
                k = eout(clamp01((t - self.T_SW) / 0.22), 3)
                anc = (0.5, 0.375); dst = (980 + 90 * (1 - k), 450)
                fr, _ = draw(self.fc, fr, t, anc, dst, z, rot=-2.5 * (1 - k), mblur=(60 * (1 - k), 0), wind_amp=-12)
                g = math.exp(-((t - self.T_GLINT) / 0.10) ** 2) + 0.25 * clamp01((t - self.T_GLINT) / 0.1)
                p = src2scr(self.fc, anc, dst, z, (0.555, 0.385))
                fr = star(fr, p, g * 0.7, 60, 14)
            fr = sparks2(fr, t, 4301, (200, 900), n=30, life=0.9, speed=(300, 800), dirc=(1, -0.6), spread=0.4, grav=80, area=(100, 100))
            fr = ink_rain(fr, t, 4304, n=60, amt=0.35, speed=2600, angle=12, length=(60, 140), near=0.6)
            return fr, 0

    # ================================================================== S044 CU 手按刀鞘，拇指推开护手，鞘口一线白光（吸气，风停）
    class S044D(S044):
        GAP = (0.688, 0.495)                                  # C1_hand3：鞘口露刃处（护手与鞘口之间，实测 x 0.655–0.69）
        GUARD = (0.628, 0.692, 0.33, 0.66)                    # 护手 + 露刃区（x0, x1, y0, y1，归一化；实测护手 x≈0.63–0.65）
        T_PUSH = 2500 / 30.0
        def __init__(self):
            self.bg = plate(C1 + 'C1_bg044.png', (2016, 1134), gain=1.15)   # 提亮 ≥65
            base = flut('C1_hand3', 1.0)
            h_, w_ = base.A.shape
            x0, x1, y0, y1 = self.GUARD
            xx = np.arange(w_, dtype=np.float32)[None, :] / w_; yy = np.arange(h_, dtype=np.float32)[:, None] / h_
            def box(a, b, c, d, f=0.004):                             # 软边框（4px 级羽化，不露直边）
                return (np.clip((xx - a) / f, 0, 1) * np.clip((b - xx) / f, 0, 1) * np.clip((yy - c) / f, 0, 1) * np.clip((d - yy) / f, 0, 1))
            g = box(x0, x1, y0, y1).astype(np.float32)
            right = np.clip((xx - x1) / 0.004, 0, 1).astype(np.float32)
            right = np.broadcast_to(right, (h_, w_))
            def mk(m):
                L_ = SP.SpriteLayer(C1 + 'C1_hand3_cut.png'); L_.A = (base.A * m).astype(np.float32); L_.wind_w = base.wind_w
                return L_
            self.guard = mk(g)                                            # 护手 + 露刃：随拇指前推
            self.sheath = mk(right * (1 - g))                             # 鞘 + 穗
            self.hand = mk(np.clip(1 - g - right, 0, 1))                  # 手 + 护腕
        def render(self, t):
            u = self.u(t)
            fr = self.bg[27:27 + H, 48 - int(24 * eio(u)):48 - int(24 * eio(u)) + W].copy()
            push = eout(clamp01((t - self.T_PUSH) / 0.55), 2)              # 拇指推开护手：6 → 10px
            s = W / self.hand.w * 1.02
            ax, ay = 960.0, 560.0
            fr, _ = draw(self.sheath, fr, t, (0.5, 0.5), (ax, ay), s, wind_amp=2.0, breathe=0.002)
            kx = ax + (6 + 4 * push) * (push > 0.01)                       # 护手 + 露刃被拇指推出 6→10px
            fr, _ = draw(self.guard, fr, t, (0.5, 0.5), (kx, ay), s, wind_amp=0.0, breathe=0.002)
            fr, A = draw(self.hand, fr, t, (0.5, 0.5), (ax + 3 * push, ay - 1.0 * push), s, wind_amp=1.2, breathe=0.002)   # 拇指跟着前移
            gx, gy0 = src2scr(self.hand, (0.5, 0.5), (kx, ay), s, self.GAP)
            g = (0.25 + 0.75 * push) * (0.85 + 0.15 * math.sin(t * 13))
            hh = 70 + 18 * push
            Lg = np.zeros((H, W), np.float32)
            cv2.line(Lg, (int(gx), int(gy0 - hh)), (int(gx), int(gy0 + hh)), 1.0, 3, cv2.LINE_AA)
            fr = fr + (Lg + cv2.GaussianBlur(Lg, (0, 0), 5) * 1.3 + cv2.GaussianBlur(Lg, (0, 0), 26) * 1.0)[..., None] * g
            fr = K.dust(fr, (t - self.t0) * 0.05, 4401, n=50, amt=0.4, size=(1, 3), blur=1.5, color=(1, 1, 1))
            return cam(fr, 1.0 + 0.08 * eio(u), 0, 0), 0

    # ================================================================== S045 LS 蓄势 → 剑光横贯 → 收势；血月旷野，雨被斩开
    class S045D(S045):
        T_GO = V(84.40)
        P0, P1 = (1880.0, 670.0), (40.0, 390.0)
        MOON = (1500, 372)
        def __init__(self):
            self.bg = plate(C1 + 'C1_moor2.png', gain=1.65)      # 换板：S042 用雾海夜，本镜用血月荒原                          # 血月荒原专用背景板（远山墨线 + 网点渐隐做纵深，不虚焦）
            self.gm = (Y >= 800).astype(np.float32)
            self.w1, self.w3 = flut('C1_spin_a', 1.0), flut('C1_spin_b', 1.0)
            x0, y0 = self.P0; x1, y1 = self.P1
            d = np.array([x1 - x0, y1 - y0]); d /= np.linalg.norm(d); self.dirv = d
            self.dist = ((X - x0) * d[1] - (Y - y0) * d[0]).astype(np.float32)
        def render(self, t):
            fr = self.bg.copy()
            fy = 868
            nf0 = int(round((t - self.T_HIT) * 30))
            if nf0 < 0:                                                # 蓄势：只有蓄势姿势（中间帧不会出现两个身体）
                k = clamp01((t - self.t0) / (self.T_HIT - self.t0))
                kk = clamp01((t - self.T_GO) / (self.T_HIT - self.T_GO))
                a_, s_ = self.w1.fit(560 * (1 + 0.03 * eio(k)))
                fr, _ = draw(self.w1, fr, t, a_, (950 + 10 * k, fy), s_, rot=-1.5 * k - 2.5 * kk, mblur=(-22 * kk, 0), wind_amp=-10)
                g = clamp01((t - V(84.22)) / 0.2) * (1 - 0.6 * kk)
                p = src2scr(self.w1, a_, (950 + 10 * k, fy), s_, (0.434, 0.876))
                fr = star(fr, p, g * 0.6 * (0.6 + 0.4 * math.sin(40 * t)), 70, 26)
            else:                                                      # 收势：硬切进来，只有收势姿势
                a = t - self.T_HIT; k = eout(clamp01(a / 0.12), 2)
                a_, s_ = self.w3.fit(600)
                fr, _ = draw(self.w3, fr, t, a_, (960 + 10 * k, fy), s_ * (0.985 + 0.015 * k), wind_amp=-14)
            if t >= self.T_GO:                                         # 剑光：白色干笔飞白，命中帧贯穿全画面
                q = (t - self.T_GO) / (self.T_HIT - self.T_GO)
                fade = 1.0 if t < self.T_HIT else math.exp(-(t - self.T_HIT) / 0.12)
                p0 = np.array(self.P0) + self.dirv * -260                     # 重端起笔在画外右侧
                fr = BR.paint(fr, p0, self.P1, clamp01(0.20 + 0.80 * q), wk=0.46, color=(1.0, 1.0, 1.0), alpha=fade)   # 加粗
                if t >= self.T_HIT:
                    fr = BR.paint(fr, p0 + self.dirv * 40, self.P1, 1.0, wk=0.20, alpha=0.9 * fade)   # 血红细缘（加粗）
            nf = int(round((t - self.T_HIT) * 30))
            wv = 0.92 if nf == 0 else ((0.55, 0.20)[nf - 1] if 1 <= nf <= 2 else 0.0)  # 命中帧整帧白闪（切点）
            fr = fr * (1 - wv) + wv * 1.12
            if 0 <= nf <= 1:                                               # 白闪里一条血红刀路硬边 + 墨线（冲击帧可读）
                fr = BR.paint(fr, np.array(self.P0) + self.dirv * -260, self.P1, 1.0, wk=0.22, alpha=1.0 - 0.4 * nf)
                fr = sparks2(fr, t, 4529, ((self.P0[0] + self.P1[0]) / 2, (self.P0[1] + self.P1[1]) / 2), n=60, life=0.45,
                             speed=(500, 1500), dirc=(-self.dirv[1], self.dirv[0]), spread=2.6, grav=900, burst=True, t0=self.T_HIT - 0.01,
                             area=(800, 30))
            band = 1 - np.exp(-(self.dist / 20) ** 2) * (t >= self.T_HIT)
            fr = ink_rain(fr, t, 451, n=320, amt=0.5, speed=2000 if t > 84.36 else 600, angle=6, region=band, near=0.0)
            if t >= self.T_HIT:
                for i, s_ in enumerate((0.3, 0.55, 0.8)):
                    o = (self.P0[0] + (self.P1[0] - self.P0[0]) * s_, self.P0[1] + (self.P1[1] - self.P0[1]) * s_)
                    fr = sparks2(fr, t, 4520 + i, o, n=20, life=0.45, speed=(300, 800), dirc=tuple(self.dirv), spread=1.0, grav=900,
                                 burst=True, t0=self.T_HIT, area=(120, 8))
            sh = 10 * pulse(t, self.T_HIT, 0.08)
            return cam(fr, 1.02, sh * math.sin(97 * t), sh * math.cos(71 * t)), 0

    # ================================================================== S046 MCU 刀遮半脸（生图），鼓停定格慢放；「答」眼光 + 朱墨炸一角
    class S046D(S046):
        EYE = (0.592, 0.405)
        def __init__(self):
            self.bg = plate(C1 + 'C1_bg046.png', gain=1.0)                # 暴雨云专用背景板，不虚焦
            self.sp = flut('C1_bladeface2', 0.8)
            n_ = cv2.resize(K.tile_crop(K.tile(512, 4646, 4, 5), 0, 0, H // 8, W // 8), (W, H))
            ex = 620 + 55 * np.sin(Y / 97.0 + 0.7) * np.cos(Y / 233.0) + 140 * (n_ - 0.5)        # 撕口墨晕：边线随 y 起伏，不成直线
            self.inkm = np.clip(0.5 - (X - ex) / 40, 0, 1).astype(np.float32)
        def render(self, t):
            tr = REAL_T[0] if REAL_T[0] is not None else t
            fr = self.bg.copy()
            s = 1.0 * (1 + 0.03 * eio(clamp01((t - self.t0) / (self.t1 - self.t0))))
            ex, ey = 1080, 430
            x0 = ex - self.EYE[0] * self.sp.w * s; x1 = x0 + self.sp.w * s
            ea = (np.clip((X - x0) / 120, 0, 1) * np.clip((x1 - X) / 120, 0, 1)).astype(np.float32)
            fr, Aw = draw(self.sp, fr, tr, self.EYE, (ex, ey), s, wind_amp=-8, breathe=0.004, extra_A=ea)
            bx0, bx1 = x0 + 0.405 * self.sp.w * s, x0 + 0.50 * self.sp.w * s
            bm = sstep(bx0 - 2, bx0 + 8, X) * sstep(bx1 + 2, bx1 - 8, X) * Aw
            sh = 0.0
            for ts, dur in ((self.t0 + 0.05, 0.55), (self.T_ANS - 0.30, 0.30)):
                q = (tr - ts) / dur
                if 0 <= q <= 1:
                    yc = 60 + 900 * eio(q)
                    sh = sh + np.exp(-((Y - yc - (X - bx0) * 0.6) / 46) ** 2) * math.sin(math.pi * q)
            if not isinstance(sh, float): fr = fr + (bm * sh)[..., None] * 0.8
            ga = pulse(tr, self.T_ANS - 0.05, 0.25) * (tr >= self.T_ANS - 0.05)
            fr = star(fr, (ex, ey), ga * 0.7, 70, 10)
            z = 1.0 + 0.04 * eio(clamp01((tr - self.t0 - 0.3) / 0.6))
            k = pulse(tr, self.T_ANS, 0.12) * (tr >= self.T_ANS)
            fr = cam(fr, z * (1 + 0.08 * k), 0, 0)
            if self.T_CRASH <= tr < self.T_CRASH + 1 / 30 + 1e-3: fr = fr * 0.4 + 0.8
            if self.T_ANS <= tr < self.T_ANS + 2 / 30 + 1e-3: fr = fr * 0.6 + BLOOD * 0.3 + 0.25
            if tr >= self.T_ANS + 1 / 30:                              # 朱墨从左下角炸开（干笔毛边），不溅上脸
                pb = 0.17 * eout((tr - self.T_ANS) / 0.2, 2)
                m = K.ink_blot(pb, seed=46, center=(150, 950)) * self.inkm
                edge = np.clip(K.blur_ds(m, 6) - m * 0.85, 0, 1)
                fr = fr * (1 - m[..., None]) + BLOOD * 0.75 * m[..., None]
                fr = fr * (1 - edge[..., None] * 0.8)
            return fr, (3 if k > 0.5 else 0)

    # ================================================================== S047（本段只露 2 帧：2584–2585 墨退）
    class S047D(S047):
        def __init__(self):
            self.bg = plate(C1 + 'C1_battle.png', gain=0.6)
        def render(self, t):
            u = self.u(t)
            fr = ink_rain(self.bg.copy(), t, 471, n=500, amt=0.6, speed=2300, angle=10, near=0.35, length=(40, 110))
            fr = cam(fr, 1.0 + 0.04 * eio(u), 0, -40 + 40 * eio(u))
            if t < self.t0 + 0.3:
                m = K.ink_blot(0.93 + 0.07 * eout((t - self.t0) / 0.2, 2), seed=47, center=(960, 600), reverse=True)
                fr = fr * (1 - m[..., None]) + 0.02 * m[..., None]          # 墨退（黑墨，不留红糊块）
            return fr, 0

    for c, nm in ((S027D, 'S027'), (S031D, 'S031'), (S032D, 'S032'), (S033D, 'S033'), (S034D, 'S034'), (S035D2, 'S035'),
                  (S036D, 'S036'), (S037D, 'S037'), (S038D, 'S038'), (S039D, 'S039'), (S040D, 'S040'), (S041D, 'S041'),
                  (S042D, 'S042'), (S043D, 'S043'), (S044D, 'S044'), (S045D, 'S045'), (S046D, 'S046'), (S047D, 'S047')):
        c.__name__ = nm; out[nm] = c
    return out
