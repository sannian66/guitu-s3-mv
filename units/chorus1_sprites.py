"""units/chorus1_sprites.py — 副歌一人物精灵镜头（SPRITE_MODE=1，2026-11-09 05:25 用户确认的规则）
人物 = assets/gen/<镜号>/<姿势>_cut.png（RH_image2 生图 + tools/cutout.py 抠图）；场景/字幕/卡点/运镜/粒子/刀光仍是代码。
动作镜头按卡点拆 2–3 个关键姿势硬切（切点加甩动模糊/闪白），刀光/残影/速度线代码画在精灵之上，不做假连续动作。
install(G) 由 chorus1.py 调用，G = chorus1 的全局（复用 K/T/cam/背景等），返回 {镜号: 精灵类}。"""
import math, os
import numpy as np, cv2


def install(G):
    globals().update({k: v for k, v in G.items() if not k.startswith('__')})
    import sprite as SP
    GEN = ROOT + '/assets/gen/'
    def L(p): return SP.layer(GEN + p + '_cut.png')
    COLD = dict(col=(0.62, 0.74, 1.0), amt=1.6, dir=(-0.8, -0.6))

    def put(fr, sp, t, target_h, foot, rim=COLD, grade=None, **kw):
        """按包围盒高度把精灵脚底放到 foot（屏幕像素）"""
        a, s = sp.fit(target_h)
        g = grade or dict(expo=0.70, sat=0.55, tint=(0.90, 0.96, 1.06), lift=0.0, gamma=1.2)
        return sp.draw(fr, t, a, foot, s, rim=rim, grade=g, **kw)

    def speed_lines(fr, t, seed, dirx=1.0, amt=0.5, y0=200, y1=900):
        r = np.random.default_rng(seed + int(t * 30))
        Lb = np.zeros((H // 2, W // 2), np.float32)
        for _ in range(40):
            y = r.uniform(y0, y1) / 2; x = r.uniform(0, W) / 2; ln = r.uniform(80, 260) / 2
            cv2.line(Lb, (int(x), int(y)), (int(x - dirx * ln), int(y)), r.uniform(0.3, 1.0), 1, cv2.LINE_AA)
        Lb = cv2.resize(cv2.GaussianBlur(Lb, (0, 0), 0.8), (W, H))
        return fr + Lb[..., None] * amt * np.array([0.75, 0.82, 0.95], np.float32)

    def arc_trail(fr, c, rx, ry, a0, a1, prog, fade, w=10, rot=0.0):
        """代码刀光：椭圆弧（白刃 + 朱红外缘 + 辉光），prog 0→1 扫过，fade 衰减"""
        if fade <= 0.01: return fr
        Lb = np.zeros((H // 2, W // 2), np.float32); Le = np.zeros_like(Lb)
        aa = a0 + (a1 - a0) * prog
        n = 40
        for i in range(n):
            u = i / n
            t0 = a0 + (aa - a0) * u; t1 = a0 + (aa - a0) * (u + 1 / n)
            ww = max(1, int(w * (0.2 + 0.8 * u) / 2))
            cv2.ellipse(Lb, (int(c[0] / 2), int(c[1] / 2)), (int(rx / 2), int(ry / 2)), rot, t0, t1, 1.0, ww, cv2.LINE_AA)
            cv2.ellipse(Le, (int(c[0] / 2), int(c[1] / 2)), (int(rx / 2 + ww), int(ry / 2 + ww)), rot, t0, t1, 1.0, max(1, ww // 2), cv2.LINE_AA)
        Lb = cv2.resize(Lb, (W, H)); Le = cv2.resize(Le, (W, H))
        fr = fr + (Lb * 1.3 + cv2.GaussianBlur(Lb, (0, 0), 10) * 1.2)[..., None] * fade * np.array([1.0, 0.97, 0.94], np.float32)
        fr = fr + cv2.GaussianBlur(Le, (0, 0), 3)[..., None] * fade * RED * 1.4
        return fr

    def white(t, t_hit, d=0.05): return pulse(t, t_hit, d) * (t >= t_hit)

    # ---------------------------------------------------------------- S029 MCU 握刀手收紧（脸 + 拳）
    class S029Sprite(S029):
        def __init__(self):
            super().__init__(); self.sp = L('S029/grip')
        def render(self, t):
            u = self.u(t)
            fr = self.bg.copy()
            k = clamp01((t - self.t0) / 0.35)
            clench = 1.0 + 0.015 * eout(k, 2) + 0.012 * pulse(t, self.T_DAO, 0.12) * (t >= self.T_DAO)   # 收紧 = 微推
            fr, _ = self.sp.draw(fr, t, (0.5, 0.5), (960 + 40, 560), W / self.sp.w * 1.04 * clench, rot=-2 + 2 * eout(k),
                                 rim=dict(col=(0.75, 0.82, 1.0), amt=1.8, dir=(0.2, -1.0)), wind_amp=4.0,
                                 grade=dict(expo=0.80, sat=0.55, tint=(0.90, 0.96, 1.06), lift=0.0, gamma=1.15),
                                 shade=(900, 1900, 0.25, 700, 0.35))
            fr = K.sparks(fr, t, 2901, (300, 760), n=55, life=0.8, speed=(600, 1300), dirc=(1, -0.25), spread=0.25,
                          grav=120, area=(200, 120), amt=1.0)
            kk = pulse(t, self.T_DAO, 0.06) * (t >= self.T_DAO - 0.04)
            if kk > 0.02:
                fr = T._slash_light(fr, (1210, 360), np.array([math.cos(-0.95), math.sin(-0.95)]), clamp01((t - self.T_DAO + 0.04) / 0.35), 1600)
            z = 1.0 + 0.05 * eio(u)
            dx, dy, dr = shake(t, 5 + 6 * kk * 3, 1.6, 29)
            return cam(fr, z, dx, dy, dr), 0

    # ---------------------------------------------------------------- S030 LS 垂刀仰望 → 举刀指月（刃光处硬切）
    class S030Sprite(S030):
        T_SW = V(61.40)
        def __init__(self):
            super().__init__(); self.a = L('S030/ready'); self.b = L('S030/raise')
        def render(self, t):
            u = self.u(t)
            crane = -70 + 120 * eio(u)
            fr = cam(self.bg, 1.0, 0, -crane * 0.3)
            rm = K.ridge_mask(H, W, self.ridge - crane * 0.0 + crane * 0.6)
            fr = over(fr, rm, (0.025, 0.025, 0.03))
            fy = 935 + crane * 0.6
            rim = dict(col=(0.80, 0.86, 1.0), amt=2.0, dir=(0.1, -1.0))
            if t < self.T_SW:
                fr, _ = put(fr, self.a, t, 560, (905, fy), rim=rim)
                tip = None
            else:
                k = clamp01((t - self.T_SW) / 0.08)
                fr, _ = put(fr, self.b, t, 690 + 10 * eout(k), (905, fy), rim=rim, mblur=(0, -50 * (1 - k)))
                a_, s_ = self.b.fit(690 + 10 * eout(k))
                tip = (905 + (self.b.top[0] - a_[0]) * self.b.w * s_, fy + (self.b.top[1] - a_[1]) * self.b.h * s_)
            fr = fr + white(t, self.T_SW, 0.04) * 0.5
            g = pulse(t, V(61.88), 0.12) * (t >= V(61.88))
            if g > 0.01 and tip:
                tx, ty = tip; x, y = K.grid()
                st = np.exp(-(np.abs(x - tx) / 3 + np.abs(y - ty) / 60)) + np.exp(-(np.abs(y - ty) / 3 + np.abs(x - tx) / 90))
                fr += (st * g * 1.6 + np.exp(-((x - tx) ** 2 + (y - ty) ** 2) / 900) * g)[..., None] * 1.0
            gm = self.grass.mask(t, 1.2, dy=crane * 1.2, blur=10)
            return over(fr, gm, (0.01, 0.01, 0.012)), 0

    # ---------------------------------------------------------------- S035 MS 疾跑 → 腾空举刀 → 落地斜劈（命中闪白）
    class S035Sprite(S035):
        T_LEAP = V(69.86)
        def __init__(self):
            super().__init__(); self.run, self.leap, self.sl = L('S035/run'), L('S035/leap'), L('S035/slash')
        def render(self, t):
            tt = t + self.SH
            camx = 0.0 if t < self.T_HIT else 40 * clamp01((t - self.T_HIT) / 0.6)
            src = self.wall[200:1280, int(200 + camx * 0.6) % 400: int(200 + camx * 0.6) % 400 + 1920]
            fr = src * 0.8
            x, y = K.grid()
            fr = fr * (0.55 + 0.6 * np.exp(-(((x - 1100) / 900) ** 2 + ((y - 400) / 600) ** 2)))[..., None]
            if t >= self.T_HIT:
                pc = eout((t - self.T_HIT) / 0.15, 2)
                cm = K.draw_crack((H, W), self.crack - [camx * 0.6, 0], 6, branches=14, seed=352, prog=pc)
                fr = over(fr, cm, (0, 0, 0))
                fr += K.blur_ds(cm, 6)[..., None] * 1.5 * GOLD * 0.5 * (0.4 + 0.6 * math.exp(-(t - self.T_HIT) / 0.4))
            rim = dict(col=(1.0, 0.78, 0.5), amt=1.8, dir=(0.0, 1.0))     # 底部金红火光逆打
            gr = dict(expo=0.72, sat=0.6, tint=(1.0, 0.95, 0.9), lift=0.0, gamma=1.2)
            if t < self.T_LEAP:                                           # 疾跑：从左冲入
                k = clamp01((t - self.t0) / (self.T_LEAP - self.t0))
                X = 380 + 420 * eout(k, 2)
                fr = speed_lines(fr, t, 351, 1.0, 0.45)
                fr, _ = put(fr, self.run, t, 720, (X - camx, 1020), rim=rim, grade=gr, mblur=(36, 0), shade=None)
            elif t < self.T_HIT:                                          # 腾空（升到高点）
                k = clamp01((t - self.T_LEAP) / (self.T_HIT - self.T_LEAP))
                fr = speed_lines(fr, t, 352, 0.6, 0.35)
                fr, _ = put(fr, self.leap, t, 600, (860 + 80 * k, 960 - 110 * eout(k)), rim=rim, grade=gr, mblur=(24, -16), shade=None)
            else:                                                         # 斜劈落地（慢放随势）
                a = t - self.T_HIT
                k = eout(clamp01(a / 0.12), 2)
                fr, _ = put(fr, self.sl, t, 640, (1000 + 60 * clamp01(a / 0.8) - camx, 950 - 60 * (1 - k)), rim=rim, grade=gr,
                            mblur=(30 * (1 - k), 30 * (1 - k)), shade=None)
                fr = arc_trail(fr, (1000, 520), 560, 420, -110, 40, eout(clamp01(a / 0.08)), math.exp(-a / 0.22), w=14, rot=10)
                r = np.random.default_rng(3530)
                Lb = np.zeros((H // 2, W // 2), np.float32)
                for i in range(26):
                    ox, oy = r.uniform(950, 1450), r.uniform(250, 900)
                    vx, vy = r.normal(0, 600), r.normal(-200, 400)
                    s = (r.uniform(20, 70)) * (1 + 3 * a)
                    px, py = ox + vx * a - camx * 0.6, oy + vy * a + 600 * a * a
                    box = cv2.boxPoints(((px / 2, py / 2), (s / 2, s * 0.45 / 2), r.uniform(0, 180) + 300 * a))
                    cv2.fillConvexPoly(Lb, box.astype(np.int32), 1.0, cv2.LINE_AA)
                fr = over(fr, cv2.resize(cv2.GaussianBlur(Lb, (0, 0), 2), (W, H)), (0.03, 0.03, 0.035))
                fr = K.sparks(fr, t, 3540, (1200, 560), n=90, life=0.6, speed=(400, 1400), dirc=(-1, -0.3), spread=1.2,
                              grav=800, burst=True, t0=self.T_HIT, area=(150, 300))
            fl = white(t, self.T_HIT) + 0.6 * white(t, self.T_LEAP, 0.03)
            fr = cam(fr + fl * 0.8, 1.03, 0, 0)
            p = clamp01((t - 69.60) / 0.9)
            # [r1] LYRIC_UNI=1 时这句由统一字幕层出，画内不再重复画一遍（否则底部两份叠在一起）
            if os.environ.get('LYRIC_UNI') == '1': return fr, (3 if fl > 0.3 else 0)
            fr = T.slash_cut(fr, '那就劈开它', p, places=LY.places('那就劈开它', 'bottom', red=('劈',)), color=LY.WHITE, angle=12,
                             cut_at=(self.T_HIT - 69.60) / 0.9, emph=('劈',), emph_color=LY.RED_T, slide=0.5, seed=35,
                             style_kw=dict(LY.STYLE))
            return fr, (3 if fl > 0.3 else 0)

    # ---------------------------------------------------------------- S037 ELS 背影站在金缝前（小人，金 rim）
    class S037Sprite(S037):
        def __init__(self):
            super().__init__(); self.sp = L('S037/stand')
            self.sw.draw = self._draw
        def _draw(self, fr, x, y, sc, **kw):
            return put(fr, self.sp, self._t, 340, (x, y + 14), rim=dict(col=tuple(float(v) for v in GOLD), amt=4.2, dir=(0, -1)),   # 11-09 重抽：亮背影 + 放大
                       grade=dict(expo=0.68, sat=0.5, tint=(0.98, 0.96, 1.0), lift=0.015, gamma=1.15), wrap=0.8, shade=None, wind_amp=5)
        def render(self, t):
            self._t = t; return super().render(t)

    # ---------------------------------------------------------------- S038 CU 刃面倒映（生图眼睛特写作倒影纹理）
    class S038Sprite(S038):
        def __init__(self):
            super().__init__()
            from PIL import Image
            im = np.asarray(Image.open(GEN + 'S038/eyes_raw.png').convert('RGB')).astype(np.float32) / 255
            h, w = im.shape[:2]
            self.eye = im[int(h * 0.38):int(h * 0.80), int(w * 0.50):int(w * 0.86)]     # 画面右眼 + 眉 + 发丝
        def render(self, t):
            u = self.u(t); e = eio(u)
            fr = self.bg.copy()
            Lg = T.giant_layer('血', 'serif_black', 'red', 330, 540, 440)
            fr = T.compose(fr, Lg, **T.auto_style('red'))
            p0, p1 = (1520, 1180), (1150, -150)
            fr, bm = draw_blade(fr, p0, p1, 380, shine=0.6 - 0.3 * e, shine_w=0.12, return_mask=True, seed=8)
            ew = 520; eh = int(ew * self.eye.shape[0] / self.eye.shape[1])
            ey = cv2.resize(self.eye, (ew, eh), interpolation=cv2.INTER_AREA)
            lum = ey.mean(-1, keepdims=True)
            ey = lum * np.array([0.78, 0.85, 1.0], np.float32) * 0.85 + (ey - lum) * 0.9 * np.array([1, 1, 0.6], np.float32)  # 琥珀留一点
            M = cv2.getRotationMatrix2D((ew / 2, eh / 2), 6, 1.0)
            M[0, 2] += 1322 - ew / 2; M[1, 2] += 470 + 30 * e - eh / 2
            refl = cv2.warpAffine(ey, M, (W, H))
            em = cv2.warpAffine(np.ones((eh, ew), np.float32), M, (W, H))
            em = cv2.GaussianBlur(cv2.erode(em, np.ones((61, 61), np.uint8)), (0, 0), 28)
            fr = fr * (1 - 0.65 * (bm * em)[..., None]) + refl * (bm * em)[..., None] * 1.35
            d = np.array(p1, float) - np.array(p0, float); Ld = np.linalg.norm(d); d /= Ld; n = np.array([-d[1], d[0]])
            head = 0.85 - 0.6 * eio((t - self.t0) / 1.0)
            path = [np.array(p1) - d * Ld * s + n * (60 + 10 * math.sin(s * 30)) for s in np.linspace(0, 1 - head, 40)]
            Lb = np.zeros((H // 2, W // 2), np.float32)
            P = (np.array(path) * 2).astype(np.int32)
            for i in range(len(P) - 1): cv2.line(Lb, tuple(P[i]), tuple(P[i + 1]), 1.0, 5, cv2.LINE_AA, 2)
            if len(P): cv2.circle(Lb, tuple((P[-1] // 4)), 9, 1.0, -1, cv2.LINE_AA)
            Lb = cv2.resize(cv2.GaussianBlur(Lb, (0, 0), 1), (W, H)) * bm
            fr = over(fr, Lb, RED * 0.8); fr += K.blur_ds(Lb, 6)[..., None] * RED * 0.3
            hy = path[-1][1] if path else 540
            z = 1.0 + 0.06 * pulse(t, self.t0, 0.15)
            fr = cam(fr, z * 1.05, 0, (hy - 540) * 0.25 - 40 + 80 * e)
            return fr, (3 if V(CT(16, 2)) <= t < V(CT(16, 2)) + 0.1 else 0)

    # ---------------------------------------------------------------- S039 MS 战后缓行（横移 + 轻微起伏）
    class S039Sprite(S039):
        def __init__(self):
            super().__init__(); self.sp = L('S039/walk')
        def render(self, t):
            u = self.u(t); off = 320 * u
            fr = self.bg.copy()
            g = (0.04 + 0.02 * np.linspace(0, 1, H)[:, None])[..., None] * np.ones(3, np.float32)
            fr = fr * (1 - self.ground[..., None]) + g * self.ground[..., None]
            fr = over(fr, self.spear_layer(t, 0, 0.45, off) * 0.8, (0.07, 0.075, 0.085))
            fr = K.fog(fr, t, 393, amt=0.5, speed=(-30, 0), y0=0.55, y1=0.8, color=(0.22, 0.23, 0.26))
            bob = 6 * abs(math.sin(math.pi * (t - self.t0) * 1.6))
            fr, _ = put(fr, self.sp, t, 800, (800 + 70 * u, 1010 - bob), rim=dict(col=(0.72, 0.8, 0.95), amt=1.5, dir=(-0.6, -0.8)),
                        grade=dict(expo=0.62, sat=0.5, tint=(0.9, 0.95, 1.05), lift=0.0, gamma=1.2), shade=None, wrap=0.45)
            fr = over(fr, K.blur_ds(self.spear_layer(t, 0.75, 1.01, off * 2.2), 6), (0.01, 0.01, 0.012))
            fr = K.rain(fr, t, 394, n=160, amt=0.25 * clamp01((t - self.t0) / 0.6), speed=1500, angle=10, near=0.15)
            dx, dy, dr = shake(t, 6, 1.4, 39)
            return cam(fr, 1.04, dx, dy, dr), 0

    # ---------------------------------------------------------------- S041 LS 背影刀横扛肩，独对长墙
    class S041Sprite(S041):
        def __init__(self):
            super().__init__(); self.sp = L('S041/shoulder')
            self.sw.draw = self._draw
        def _draw(self, fr, x, y, sc, **kw):
            return put(fr, self.sp, self._t, 1060, (920, 1240), rim=dict(col=tuple(float(v) for v in GOLD * 0.9 + 0.1), amt=2.2, dir=(0, -1)),
                       grade=dict(expo=0.55, sat=0.5, tint=(0.95, 0.95, 1.0), lift=0.0, gamma=1.25), wrap=0.5, shade=None, wind_amp=6)
        def render(self, t):
            self._t = t; return super().render(t)

    # ---------------------------------------------------------------- S044 CU 拇指推刀，鞘口一线光（风停：不吹）
    class S044Sprite(S044):
        GAP = (0.434, 0.57)
        def __init__(self):
            super().__init__(); self.sp = L('S044/thumb')
        def render(self, t):
            u = self.u(t)
            fr = self.bg.copy()
            prog = eio(clamp01((t - self.t0 - 0.15) / 0.8))
            s = W / self.sp.w * 1.02
            ax, ay = 960 - 12 * prog, 560
            fr, _ = self.sp.draw(fr, t, (0.5, 0.5), (ax, ay), s, wind_amp=0.0, breathe=0.002,
                                 rim=dict(col=(0.80, 0.86, 1.0), amt=1.6, dir=(-0.3, -1.0)),
                                 grade=dict(expo=0.80, sat=0.55, tint=(0.9, 0.96, 1.06), lift=0.0, gamma=1.15), shade=None, wrap=0.2)
            gx = ax + (self.GAP[0] - 0.5) * self.sp.w * s; gy = ay + (self.GAP[1] - 0.5) * self.sp.h * s
            Lg = np.zeros((H, W), np.float32)
            cv2.line(Lg, (int(gx), int(gy - 55)), (int(gx), int(gy + 55)), 1.0, 3, cv2.LINE_AA)
            g = prog * (0.8 + 0.2 * math.sin(t * 13))
            fr = fr + (Lg * 0.8 + cv2.GaussianBlur(Lg, (0, 0), 6) * 1.2 + cv2.GaussianBlur(Lg, (0, 0), 30) * 1.5)[..., None] * g * np.array([0.9, 0.95, 1.0], np.float32)
            fr = K.dust(fr, (t - self.t0) * 0.05, 4401, n=50, amt=0.35, size=(1, 3), blur=1.5)
            return cam(fr, 1.0 + 0.08 * eio(u), 0, 0), 0

    # ---------------------------------------------------------------- S045 LS 蓄势 → 旋斩（命中）→ 收势；环形刀光代码
    class S045Sprite(S045):
        T_SPIN = V(84.30)
        def __init__(self):
            super().__init__(); self.w1, self.w2, self.w3 = L('S045/windup'), L('S045/spin'), L('S045/finish')
        def render(self, t):
            u = self.u(t)
            fr = self.bg * (1 - self.gm[..., None] * 0.75)
            cx, fy = 960, 960
            ring_y = 600
            # [r1-#27] 用户：1m24 主角转圈挥刀很丑 → 改成「剑光 + 闪白」，不画旋身人物
            if True:
                q = clamp01((t - (self.t0 + 0.10)) / 0.34)
                if 0.0 < q < 1.4:
                    G = np.zeros((H // 2, W // 2), np.float32)
                    x0, y0 = 220, 900
                    x1 = x0 + int(1520 * eout(min(1.0, q)))
                    cv2.line(G, (x0 // 2, y0 // 2), (max(0, x1) // 2, int((y0 - 540 * min(1.0, q)) / 2)), 1.0, 3, cv2.LINE_AA)
                    G = cv2.GaussianBlur(G, (0, 0), 1.2) * 3.0 + cv2.GaussianBlur(G, (0, 0), 9) * 5.0
                    g8 = cv2.resize(G, (W, H))
                    fr = fr + g8[..., None] * np.array([1.0, 0.97, 0.92], np.float32) * (1.0 - clamp01((q - 1.0) / 0.4))
                    fr = fr + g8[..., None] * np.array([0.92, 0.16, 0.09], np.float32) * 0.30 * math.exp(-max(0.0, q - 0.5) * 6)
                fa = t - self.T_HIT
                if 0 <= fa < 0.16:
                    e = math.exp(-fa / 0.05)
                    fr = fr * (1 - 0.55 * e) + 0.55 * e * np.array([0.97, 0.97, 1.0], np.float32)
                return fr, 0
            rim = dict(col=(0.75, 0.84, 1.0), amt=1.8, dir=(0.5, -0.8))
            gr = dict(expo=0.70, sat=0.55, tint=(0.9, 0.96, 1.06), lift=0.0, gamma=1.2)
            if t < self.T_SPIN:
                k = clamp01((t - self.t0) / (self.T_SPIN - self.t0))
                fr, _ = put(fr, self.w1, t, 660, (cx - 20, fy), rim=rim, grade=gr, shade=None, rot=-2 * k)
            elif t < self.T_HIT:
                k = clamp01((t - self.T_SPIN) / (self.T_HIT - self.T_SPIN))
                fr, _ = put(fr, self.w2, t, 660, (cx, fy), rim=dict(col=(0.8, 0.88, 1.0), amt=2.6, dir=(0.5, -0.8)), grade=gr, shade=None, mblur=(-10 * (1 - k), 0))   # 11-09 重抽：清楚的背身转体，不靠模糊
                fr = arc_trail(fr, (cx, ring_y), 560, 130, 200, 200 + 300 * k, 1.0, 1.0, w=12)
            else:
                a = t - self.T_HIT
                k = eout(clamp01(a / 0.1), 2)
                fr, _ = put(fr, self.w3, t, 640 + 20 * k, (cx + 30, fy), rim=rim, grade=gr, shade=None, mblur=(-30 * (1 - k), 0))
                fr = arc_trail(fr, (cx, ring_y), 560, 130, 200, 560, 1.0, math.exp(-a / 0.25), w=12)
                R = 520 + 900 * eout(a / 0.6, 2)
                ring = np.zeros((H // 2, W // 2), np.float32)
                cv2.ellipse(ring, (cx // 2, int(ring_y / 2)), (int(R / 2), int(R * 0.22 / 2)), 0, 0, 360, 1.0, 2, cv2.LINE_AA)
                ring = cv2.GaussianBlur(ring, (0, 0), 1.5) * 2 + cv2.GaussianBlur(ring, (0, 0), 8) * 3
                fr += cv2.resize(ring, (W, H))[..., None] * np.array([1.0, 0.95, 0.9], np.float32) * math.exp(-a / 0.35)
            fr = fr + white(t, self.T_HIT, 0.04) * 0.6
            x, y = K.grid()
            band = 1 - np.exp(-((y - ring_y) / 18) ** 2) * (t >= self.T_HIT)
            fr = K.rain(fr, t, 451, n=320, amt=0.4, speed=2000 if t > 84.36 else 600, angle=6, region=band)
            if t >= self.T_HIT:
                fr = K.sparks(fr, t, 4520, (cx, ring_y), n=120, life=0.6, speed=(300, 900), dirc=(1, 0), spread=3.0, grav=900,
                              burst=True, t0=self.T_HIT, area=(500, 20), color=(0.75, 0.82, 0.95), amt=0.9)
            return cam(fr, 1.02, 0, 0), 0

    # ---------------------------------------------------------------- S046 MCU 刀在镜前（代码刀身 + 刻字），人物精灵在后虚焦
    class S046Sprite(S046):
        def __init__(self):
            super().__init__(); self.sp = L('S046/stare')
            self.sw.pose = lambda *a, **k: None
            self.sw.draw = self._draw
        def _draw(self, fr, x, y, sc, **kw):
            a, s = (0.52, 0.30), 1300 / self.sp.h
            fr, _ = self.sp.draw(fr, self._t, a, (1330, 330), s, rim=dict(col=(0.8, 0.85, 1.0), amt=1.6, dir=(0.6, -0.8)),
                                 grade=dict(expo=0.62, sat=0.55, tint=(0.9, 0.96, 1.06), lift=0.0, gamma=1.2), shade=None, wind_amp=4)
            return fr, {}
        def render(self, t):
            self._t = t; return super().render(t)

    out = {}
    for c in (S029Sprite, S030Sprite, S035Sprite, S037Sprite, S038Sprite, S039Sprite, S041Sprite, S044Sprite, S045Sprite, S046Sprite):
        nm = c.__name__.replace('Sprite', ''); c.__name__ = nm; out[nm] = c
    return out
