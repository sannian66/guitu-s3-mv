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

    # ---------------------------------------------------------------- S031 ELS 太上皇天幕巨像
    #   r5 F组 用户 #21：代码建模 → 生图；r6 F组（评审 6 分）：换冕服生图 R6_F/emp_mian_b（冕旒 + 龙纹），
    #   逆光（满月压在冕冠后、轮廓冷银 rim、正脸压暗），去掉眼中金光，冕冠顶部留白（≥ 画幅黑边下 80px）
    class S031Sprite(S031):
        ANC = (0.5, 0.33)                                 # emp_mian_b 精灵内锚点 = 两眼中点
        CROWN = 0.03                                      # 冕板顶（归一化 y）
        def __init__(self):
            super().__init__(); self.sp = L('R6_F/emp_mian_b')
        def render(self, t):
            u = self.u(t)
            cr = -240 * (1 - eio(u))                      # 机位从低处升起 + 上摇（同原镜）
            fr = cam(self.bg, 1.0, 0, -cr * 0.25)
            s = 0.36 * (1 + 0.02 * u)                     # 巨像缓慢逼近；冕冠整顶留在画内
            ax, ay = 960, 565 + cr
            hcy = ay - (self.ANC[1] - 0.12) * self.sp.h * s     # 冕冠中心
            fr = K.paste_sprite(fr, *self.moon, ax, hcy + 12, scale=0.88)   # 满月压在冕冠后：逆光光源
            x, y = K.grid()
            halo = np.exp(-((x - ax) ** 2 + (y - hcy) ** 2) / (2 * 420.0 ** 2)).astype(np.float32)
            fr = fr + halo[..., None] * np.array([0.10, 0.11, 0.13], np.float32)
            fade = np.clip(1.0 - (y - (ay + 340)) / 400, 0.2, 1.0).astype(np.float32)   # 胸以下渐隐入云
            fr, _ = self.sp.draw(fr, t * 0.6, self.ANC, (ax, ay), s, wind_amp=5.0, breathe=0.0,
                                 grade=dict(expo=0.47, sat=0.50, tint=(0.86, 0.92, 1.08), lift=0.02, gamma=1.3),
                                 rim=dict(col=(0.88, 0.92, 1.0), amt=3.6, dir=(0, -1)), wrap=0.9,
                                 shade=None, alpha=0.96, extra_A=fade)
            # 云层在巨像前流过（天幕感）
            cl = cv2.resize(K.tile_crop(self.cloud, t * 40, 0, H // 4, W // 4), (W, H))
            ca_ = np.clip((cl - 0.5) * 2.2, 0, 1) * 0.38 * sstep(380, 620, y)
            fr = over(fr, ca_, (0.10, 0.11, 0.13))
            # 地面草浪 + 一粒黑点（远景小剪影仍用代码 rig）
            rg = self.ridge + cr
            rm = K.ridge_mask(H, W, rg)
            wave = cv2.resize(K.tile_crop(self.cloud, t * 120, 300, H // 4, W // 4), (W, H))
            ground = (0.02 + 0.03 * wave)[..., None] * np.array([1, 1, 1.05], np.float32)
            fr = fr * (1 - rm[..., None]) + ground * rm[..., None]
            self.sw.pose('stand_wind', (t * 0.3) % 1, t, wind=300)
            fr, _ = self.sw.draw(fr, 960, rg[960] + 6, 46, rim_color=(0.8, 0.85, 0.95), rim_dir=(0, -1))
            return cam(fr, 1.0 + 0.03 * u, 0, 0), 0

    # ---------------------------------------------------------------- S035 MS 蓄力 → 腾空举刀 → 俯冲斜劈（命中）→ 落地收刀
    class S035Sprite(S035):
        # r5 F组（用户 #23「跳斩姿势丑 → 帅气，多张图让动作顺畅」）：生图关键姿势按节拍串接
        # r6 F组（评审 4 分：姿势一闪而过不可辨、人太小、歌词被刀光打碎）：
        #   · 4 个清楚姿势，每个至少停 3 帧：蓄力 js1_crouch_b（3 帧）→ 腾空举刀 js3_apex_b（3 帧，含 1 帧上升甩动）
        #     → 俯冲斜劈 js4_strike_a（命中 70.00，停 ~10 帧随势慢推）→ 落地收刀 js5_land_a（~20 帧）
        #   · 人物包围盒高 600–640px（≈ 画面 1080 的 56–60%），脚底统一落在 y≈900（2.39 黑边内）
        #   · 命中闪白降到 0.45（命中帧仍看得见劈刀姿势），去掉起跳闪
        #   · 镜内字「那就劈开它」按用户 #55 保留：移到左上墙面（刻字位），刀痕斩开后两半只错开 0.10 字高，始终可读；
        #     底部横排字幕区不再压任何刀光/碎砖
        T_APEX = 69.865
        T_STRK = 69.955         # 命中前一帧（69.967）先见俯冲斜劈姿势
        T_LAND = 70.30
        GY = 900                # 脚底线
        POSES = {'crouch': ('R5_F/js1_crouch_b', 600), 'apex': ('R5_F/js3_apex_b', 640),
                 'strike': ('R5_F/js4_strike_a', 600), 'land': ('R5_F/js5_land_a', 600)}
        def __init__(self):
            super().__init__()
            self.P = {k: L(p) for k, (p, h) in self.POSES.items()}
        def _pose(self, t):
            """→ (姿势名, 包围盒中心屏幕位置, 旋转, mblur, 残影 (名, 位置, alpha) | None)"""
            hb = lambda n: self.POSES[n][1] / 2
            if t < self.T_APEX:                                            # 蓄力：压低重心向右滑步
                k = eio(clamp01((t - self.t0) / (self.T_APEX - self.t0)))
                return 'crouch', (620 + 70 * k, self.GY - hb('crouch')), 0.0, (8 * k, 0), None
            if t < self.T_STRK:                                            # 腾空举刀：第 1 帧带上升甩动，随后滞空
                k = eout(clamp01((t - self.T_APEX) / (self.T_STRK - self.T_APEX)), 2)
                g = ('crouch', (690, self.GY - hb('crouch')), 0.35 * (1 - k))
                return 'apex', (880 + 70 * k, 540 - 50 * k), -3 * (1 - k), (10 * (1 - k), -40 * (1 - k)), g
            if t < self.T_LAND:                                            # 俯冲斜劈：刀从左上劈向右下（过裂缝）
                k = eout(clamp01((t - self.T_STRK) / (self.T_LAND - self.T_STRK)), 2)
                g = ('apex', (950, 490), 0.3 * (1 - clamp01((t - self.T_STRK) / 0.07)))
                return 'strike', (1060 + 90 * k, 470 + 80 * k), 0.0, (12 * (1 - k), 10 * (1 - k)), g
            a = t - self.T_LAND                                            # 落地收刀：沉身
            k = eout(clamp01(a / 0.2), 2)
            g = ('strike', (1150, 550), 0.3 * (1 - clamp01(a / 0.07)))
            return 'land', (1250 + 40 * clamp01(a / 0.65), self.GY - hb('land') - 26 * (1 - k)), 0.0, (16 * (1 - k), 18 * (1 - k)), g
        def _put(self, fr, t, name, pos, rot=0.0, mblur=(0, 0), alpha=1.0, rim=None, gr=None):
            sp = self.P[name]; th = self.POSES[name][1]
            x0, y0, x1, y1 = sp.bbox
            s = th / ((y1 - y0) * sp.h)
            return sp.draw(fr, t, ((x0 + x1) / 2, (y0 + y1) / 2), pos, s, rot=rot, mblur=mblur, rim=rim, grade=gr,
                           shade=None, wind_amp=6.5, alpha=alpha, wrap=0.4)[0]
        def render(self, t):
            camx = 0.0 if t < self.T_HIT else 40 * clamp01((t - self.T_HIT) / 0.6)
            src = self.wall[200:1280, int(200 + camx * 0.6) % 400: int(200 + camx * 0.6) % 400 + 1920]
            fr = src * 0.8
            x, y = K.grid()
            fr = fr * (0.55 + 0.6 * np.exp(-(((x - 1050) / 900) ** 2 + ((y - 450) / 600) ** 2)))[..., None]
            if t >= self.T_HIT:
                pc = eout((t - self.T_HIT) / 0.15, 2)
                cm = K.draw_crack((H, W), self.crack - [camx * 0.6, 0], 6, branches=14, seed=352, prog=pc)
                fr = over(fr, cm, (0, 0, 0))
                fr += K.blur_ds(cm, 6)[..., None] * 1.5 * GOLD * 0.5 * (0.4 + 0.6 * math.exp(-(t - self.T_HIT) / 0.4))
            rim = dict(col=(1.0, 0.78, 0.5), amt=1.8, dir=(0.0, 1.0))     # 底部金红火光逆打
            gr = dict(expo=0.80, sat=0.6, tint=(1.0, 0.95, 0.9), lift=0.0, gamma=1.18)
            name, pos, rot, mb, ghost = self._pose(t)
            pos = (pos[0] - camx, pos[1])
            if name == 'apex':
                fr = speed_lines(fr, t, 352, 0.6, 0.22)
            elif name == 'crouch':
                fr = speed_lines(fr, t, 351, 1.0, 0.18 * clamp01((t - self.t0) / 0.1))
            if ghost and ghost[2] > 0.02:                                  # 前一姿势残影（冷灰半透，动作连贯）
                fr = self._put(fr, t, ghost[0], (ghost[1][0] - camx, ghost[1][1]), alpha=ghost[2],
                               rim=dict(col=(0.7, 0.78, 0.95), amt=1.0, dir=(0, -1)),
                               gr=dict(expo=0.45, sat=0.2, tint=(0.85, 0.92, 1.05), lift=0.04, gamma=1.0))
            if name == 'strike' or (name == 'land' and t - self.T_LAND < 0.3):   # 斜劈刀弧（左上 → 右下），在人物身后
                a = t - self.T_STRK
                fr = arc_trail(fr, (1120 - camx, 520), 560, 120, -175, 5, eout(clamp01(a / 0.06)),
                               math.exp(-max(0.0, t - self.T_HIT) / 0.16), w=18, rot=50)
            fr = self._put(fr, t, name, pos, rot, mb, rim=rim, gr=gr)
            if t >= self.T_HIT:
                a = t - self.T_HIT
                r = np.random.default_rng(3530)
                Lb = np.zeros((H // 2, W // 2), np.float32)
                for i in range(22):
                    ox, oy = r.uniform(1050, 1500), r.uniform(250, 700)
                    vx, vy = r.normal(250, 500), r.normal(-250, 300)
                    s = (r.uniform(18, 60)) * (1 + 2 * a)
                    px, py = ox + vx * a - camx * 0.6, oy + vy * a + 500 * a * a
                    if py > 860: continue                                   # 碎砖不落进底部字幕区
                    box = cv2.boxPoints(((px / 2, py / 2), (s / 2, s * 0.45 / 2), r.uniform(0, 180) + 300 * a))
                    cv2.fillConvexPoly(Lb, box.astype(np.int32), 1.0, cv2.LINE_AA)
                fr = over(fr, cv2.resize(cv2.GaussianBlur(Lb, (0, 0), 2), (W, H)), (0.03, 0.03, 0.035))
                fr = K.sparks(fr, t, 3540, (1180, 520), n=70, life=0.5, speed=(400, 1200), dirc=(0.3, -0.6), spread=1.2,
                              grav=800, burst=True, t0=self.T_HIT, area=(150, 220))
            if self.T_LAND <= t < self.T_LAND + 0.5:                       # 落地扬尘
                fr = K.sparks(fr, t, 3550, (1250 - camx, self.GY - 8), n=40, life=0.5, speed=(150, 450), dirc=(1, -0.2), spread=1.4,
                              grav=300, burst=True, t0=self.T_LAND, area=(260, 10), color=(0.6, 0.58, 0.55), amt=0.5)
            fl = white(t, self.T_HIT, 0.035)
            sk = pulse(t, self.T_HIT, 0.12) * (t >= self.T_HIT)
            dx, dy, dr = shake(t, 12 * sk, 16, 35)
            fr = cam(fr * (1 - 0.2 * fl) + fl * 0.32, 1.02 + 0.025 * sk, dx, dy, dr)
            p = clamp01((t - 69.60) / 0.9)
            pl = [dict(q, x=q['x'] - 960 + 470, y=250, size=86) for q in LY.places('那就劈开它', 'bottom', red=('劈',))]
            for i, q in enumerate(pl): q['x'] = 470 + (i - 2) * 86 * 1.12
            fr = T.slash_cut(fr, '那就劈开它', p, places=pl, color=LY.WHITE, angle=12,
                             cut_at=(self.T_HIT - 69.60) / 0.9, emph=('劈',), emph_color=LY.RED_T, slide=0.10, seed=35,
                             style_kw=dict(LY.STYLE))
            return fr, 0

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
            Lg = T.giant_layer('血', 'serif_black', 'red', XUE_X, 540, 440)
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
        """r5 #27：去掉转一圈旋斩 + 圆环 → 蓄势（刀尖星芒）→ 一道横贯全画面的剑光 + 闪白 → 收刀定格（生图 s45_follow_a）"""
        T_GO = V(84.40)                                  # 光头起划（命中前 2 帧）
        P0, P1, BUL = (1880.0, 670.0), (40.0, 390.0), 50.0    # 剑光：右下 → 左上，略上拱，末端贴着收刀的刀身
        def __init__(self):
            super().__init__(); self.w1, self.w3 = L('S045/windup'), L('R5_F/s45_follow_a')
            x, y = K.grid(); (x0, y0), (x1, y1) = self.P0, self.P1
            d = np.array([x1 - x0, y1 - y0]); d /= np.linalg.norm(d); self.dirv = d
            self.dist = ((x - x0) * d[1] - (y - y0) * d[0]).astype(np.float32)     # 到剑光线的有符号距离
        def _pt(self, s):
            (x0, y0), (x1, y1) = self.P0, self.P1
            nx, ny = -self.dirv[1], self.dirv[0]
            b = self.BUL * 4 * s * (1 - s)
            return x0 + (x1 - x0) * s + nx * b, y0 + (y1 - y0) * s + ny * b
        def streak(self, fr, head, tail, fade, wmax=16.0):
            """刀形剑光：两端尖、中段宽；白芯 + 冷蓝辉光 + 朱红细缘"""
            if fade <= 0.01 or head <= tail: return fr
            n = 48; ss = np.linspace(tail, head, n)
            up, dn = [], []
            for s_ in ss:
                px, py = self._pt(s_)
                w = wmax * math.sin(math.pi * clamp01((s_ - tail) / max(head - tail, 1e-3))) ** 0.7 + 1.0
                up.append((px / 2 - self.dirv[1] * w / 2, py / 2 + self.dirv[0] * w / 2))
                dn.append((px / 2 + self.dirv[1] * w / 2, py / 2 - self.dirv[0] * w / 2))
            poly = np.array(up + dn[::-1], np.float32)
            Lb = np.zeros((H // 2, W // 2), np.float32)
            cv2.fillPoly(Lb, [np.round(poly * 4).astype(np.int32)], 1.0, cv2.LINE_AA, shift=2)
            core = cv2.GaussianBlur(Lb, (0, 0), 0.7)
            glow = cv2.GaussianBlur(Lb, (0, 0), 6) * 2.2 + cv2.GaussianBlur(Lb, (0, 0), 26) * 3.0
            edge = np.clip(cv2.GaussianBlur(Lb, (0, 0), 2.5) - core, 0, 1)
            add = (core[..., None] * np.array([1.4, 1.38, 1.34], np.float32) + glow[..., None] * np.array([0.55, 0.68, 0.95], np.float32)
                   + edge[..., None] * np.array([0.9, 0.08, 0.05], np.float32) * 0.6)
            return fr + cv2.resize(add, (W, H)) * fade
        # r6 F组（评审 #27 7 分）：脚入画（脚底线 925 → 868，离 2.39 黑边 ≥ 70px）；蓄势/收刀两张按「头一样大、
        #   双脚落同一点」对齐（windup 包围盒高 557 / follow 640，脚心都在 x≈960），切换时姿势接得上；
        #   闪白只留 2 帧（0.45 → 0.15），第 3 帧人物完全复原；剑光命中后 0.12s 衰减不再糊在人身上
        FY = 868
        WFOOT = (0.50, 1393 / 1440); FFOOT = (0.57, 1948 / 2048)          # 两张精灵的双脚中点（归一化）
        WTIP = (2410 / 2560, 579 / 1440)                                  # windup 刀尖
        HW, HF = 557, 640                                                  # 包围盒高：两张头同大
        def render(self, t):
            fr = self.bg * (1 - self.gm[..., None] * 0.75)
            rim = dict(col=(0.75, 0.84, 1.0), amt=1.8, dir=(0.5, -0.8))
            gr = dict(expo=0.74, sat=0.55, tint=(0.9, 0.96, 1.06), lift=0.0, gamma=1.2)
            fy = self.FY
            if t < self.T_HIT:
                k = clamp01((t - self.t0) / (self.T_HIT - self.t0))
                kk = clamp01((t - self.T_GO) / (self.T_HIT - self.T_GO))          # 最后 2 帧：拧身发力
                sc = self.w1.fit(self.HW)[1] * (1 + 0.03 * eio(k))
                fx = 950 + 10 * k
                fr, _ = self.w1.draw(fr, t, self.WFOOT, (fx, fy), sc, rim=rim, grade=gr, shade=None,
                                     rot=-1.5 * k - 2.5 * kk, mblur=(-22 * kk, 0), wind_amp=6)
                # 刀尖星芒：蓄势
                g = clamp01((t - V(84.22)) / 0.2) * (1 - 0.6 * kk)
                if g > 0:
                    tx = fx + (self.WTIP[0] - self.WFOOT[0]) * self.w1.w * sc
                    ty = fy + (self.WTIP[1] - self.WFOOT[1]) * self.w1.h * sc
                    st = np.zeros((H // 2, W // 2), np.float32); c = (int(tx / 2), int(ty / 2))
                    cv2.line(st, (c[0] - 70, c[1]), (c[0] + 70, c[1]), 1.0, 1, cv2.LINE_AA)
                    cv2.line(st, (c[0], c[1] - 26), (c[0], c[1] + 26), 0.7, 1, cv2.LINE_AA)
                    st = cv2.GaussianBlur(st, (0, 0), 1.2) * 1.6 + cv2.GaussianBlur(st, (0, 0), 6) * 2.0
                    fr = fr + cv2.resize(st, (W, H))[..., None] * np.array([1.0, 0.97, 0.9], np.float32) * g * (0.6 + 0.4 * math.sin(40 * t))
            else:
                a = t - self.T_HIT
                k = eout(clamp01(a / 0.12), 2)
                fr, _ = self.w3.draw(fr, t, self.FFOOT, (960 + 10 * k, fy), self.w3.fit(self.HF)[1] * (0.985 + 0.015 * k),
                                     rim=dict(col=(0.85, 0.9, 1.0), amt=2.4, dir=(-0.6, -0.8)),
                                     grade=gr, shade=None, mblur=(-36 * (1 - k), 0), wind_amp=7)
            # 剑光：命中前 1 帧光头从右下划出，命中帧贯穿全画面，之后收尾余辉
            if t >= self.T_GO:
                q = (t - self.T_GO) / (self.T_HIT - self.T_GO)
                head = clamp01(0.08 + 0.92 * q); tail = clamp01((t - self.T_HIT) / 0.22) ** 0.6
                fade = 1.0 if t < self.T_HIT else math.exp(-(t - self.T_HIT) / 0.12)
                fr = self.streak(fr, head, min(tail, head - 1e-3), fade, 18 if t >= self.T_HIT else 12)
            # 闪白（命中帧满白，随后约 2 帧收）
            nf = int(round((t - self.T_HIT) * 30))
            wv = (0.45, 0.15)[nf] if 0 <= nf < 2 else 0.0
            fr = fr * (1 - wv) + wv * 1.1
            band = 1 - np.exp(-(self.dist / 20) ** 2) * (t >= self.T_HIT)                  # 雨丝沿剑光被斩开
            fr = K.rain(fr, t, 451, n=320, amt=0.4, speed=2000 if t > 84.36 else 600, angle=6, region=band)
            if t >= self.T_HIT:
                for i, s_ in enumerate((0.3, 0.55, 0.8)):
                    fr = K.sparks(fr, t, 4520 + i, self._pt(s_), n=22, life=0.45, speed=(300, 800), dirc=tuple(self.dirv), spread=1.0,
                                  grav=900, burst=True, t0=self.T_HIT, area=(120, 8), color=(0.78, 0.84, 0.96), amt=0.7)
            sh = 10 * pulse(t, self.T_HIT, 0.08)
            return cam(fr, 1.02, sh * math.sin(97 * t), sh * math.cos(71 * t)), 0

    # ---------------------------------------------------------------- S046 MCU 刀遮半脸（r5 #28：去刀身刻字「这里就是我的回答」+ 代码刀身 → 生图 bladeface_a）
    class S046Sprite(S046):
        EYE = (0.61, 0.375)                               # bladeface_a：露出的琥珀右眼
        BLADE = (0.312, 0.458)                            # 刀身左右缘（归一化 x），护手在 0.81
        def __init__(self):
            super().__init__(); self.sp = L('R5_F/bladeface_a')
            x, y = K.grid(); self.x, self.y = x, y; self.inkm = sstep(950, 870, x).astype(np.float32)
        def render(self, t):
            tr = REAL_T[0] if REAL_T[0] is not None else t     # 画面定格慢放；风/刀光/闪光/墨爆按真实时间
            x, y = self.x, self.y
            fr = self.bg.copy() * 0.85
            s = 0.50 * (1 + 0.035 * eio(clamp01((t - self.t0) / (self.t1 - self.t0))))
            ex, ey = 1060, 405
            sp = self.sp
            x0 = ex - self.EYE[0] * sp.w * s; x1 = x0 + sp.w * s
            hf = np.clip((x - x0) / 160, 0, 1) * np.clip((x1 - x) / 160, 0, 1)            # 肩线两侧（生图画幅边）渐隐进夜色
            ea = 1 - (1 - hf) * sstep(560, 760, y)
            fr, Aw = sp.draw(fr, tr, self.EYE, (ex, ey), s, breathe=0.004, wind_amp=5,
                             grade=dict(expo=0.62, sat=0.50, tint=(0.90, 0.95, 1.05), lift=0.0, gamma=1.22),
                             rim=dict(col=(0.80, 0.86, 1.0), amt=2.0, dir=(0.7, -0.7)), wrap=0.45, shade=None, extra_A=ea, keep_red=0.45)    # 压唇色（防只有唇红抢眼）
            # 刀身：冷光扫过（入镜一次、「答」前再一次）
            bx0 = x0 + self.BLADE[0] * sp.w * s; bx1 = x0 + self.BLADE[1] * sp.w * s
            gy = ey + (0.81 - self.EYE[1]) * sp.h * s
            bm = (sstep(bx0 - 2, bx0 + 8, x) * sstep(bx1 + 2, bx1 - 8, x) * sstep(gy, gy - 20, y) * Aw)
            sh = 0.0
            for ts, dur in ((self.t0 + 0.05, 0.55), (self.T_ANS - 0.30, 0.30)):
                q = (tr - ts) / dur
                if 0 <= q <= 1:
                    yc = 60 + (gy - 60) * eio(q)
                    sh = sh + np.exp(-((y - yc - (x - bx0) * 0.6) / 46) ** 2) * math.sin(math.pi * q)
            if not isinstance(sh, float):
                fr = fr + (bm * sh)[..., None] * np.array([0.85, 0.92, 1.05], np.float32) * 0.75
            # 琥珀眼：「答」上金色眼光
            ga = pulse(tr, self.T_ANS - 0.05, 0.25) * (tr >= self.T_ANS - 0.05)
            if ga > 0.01:
                fr += (np.exp(-(((x - ex) / 9) ** 2 + ((y - ey) / 3) ** 2)) * ga * 1.2)[..., None] * GOLD
                fr += (np.exp(-(((x - ex) / 60) ** 2 + ((y - ey) / 6) ** 2)) * ga * 0.35)[..., None] * GOLD
            # 定格 0.3s 后推
            z = 1.0 + 0.04 * eio(clamp01((tr - self.t0 - 0.3) / 0.6))
            k = pulse(tr, self.T_ANS, 0.12) * (tr >= self.T_ANS)
            fr = cam(fr, z * (1 + 0.08 * k), 0, 0)
            if self.T_CRASH <= tr < self.T_CRASH + 1 / 30 + 1e-3: fr = fr * 0.4 + 0.8          # 鼓回归：闪白
            if self.T_ANS <= tr < self.T_ANS + 2 / 30 + 1e-3: fr = fr * 0.6 + GOLD * 0.5
            # 朱墨爆开（左下角一角，金边）
            if tr >= self.T_ANS + 1 / 30:
                pb = 0.17 * eout((tr - self.T_ANS) / 0.2, 2)
                m = K.ink_blot(pb, seed=46, center=(150, 950)) * self.inkm     # 墨点不溅上脸（只在刀身左侧）
                edge = np.clip(K.blur_ds(m, 6) - m * 0.85, 0, 1)
                fr = over(fr, m, RED * 0.22 + 0.015)
                fr += edge[..., None] * GOLD * 1.2 * (1 - 0.5 * pb)
            return fr, (3 if k > 0.5 else 0)

    out = {}
    for c in (S029Sprite, S030Sprite, S031Sprite, S035Sprite, S037Sprite, S038Sprite, S039Sprite, S041Sprite, S044Sprite, S045Sprite, S046Sprite):
        nm = c.__name__.replace('Sprite', ''); c.__name__ = nm; out[nm] = c
    return out
