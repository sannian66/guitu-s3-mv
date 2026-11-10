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

    def red_moon(r, gain=0.8):
        """r6 第二棒（评审 #27 月色连续性 / #26 暗环）：沿用 S042 #26 猩红之月配色，月海纹理保留（×0.85–1.0），亮度 ×gain。
        返回 (rgb, A_盘, 晕)：盘按 alpha 贴，血晕另行加色（不再用暗红盖一圈 → 无贴纸暗环）"""
        rgb, A = K.moon_sprite(r)
        lum = rgb.mean(-1, keepdims=True)
        s_ = A.shape[0]; yy_, xx_ = np.mgrid[0:s_, 0:s_].astype(np.float32) - s_ / 2
        dd_ = np.sqrt(xx_ ** 2 + yy_ ** 2)
        disc = np.clip((r - dd_) / 2 + 0.5, 0, 1)
        limb0 = np.clip(1 - (dd_ / r) ** 4 * 0.25, 0.05, 1)[..., None]
        moon_r = np.clip((lum / limb0 - 0.76) / 0.19, 0, 1)                   # 去掉白月自带的边缘压暗，只留月海/环形山
        det = lum - cv2.GaussianBlur(lum, (0, 0), r * 0.04)[..., None]
        limb_r = np.clip(1 - 0.22 * (dd_ / r) ** 4, 0, 1)[..., None]
        rgb_r = limb_r * (1 + 3.0 * det) * (np.array([0.80, 0.045, 0.17], np.float32) * (0.45 + 0.55 * moon_r) ** 1.6
                          + np.array([0.14, 0.03, 0.04], np.float32) * moon_r ** 3) * gain
        halo = (1 / (1 + (np.maximum(dd_ - r, 0) / (r * 0.55)) ** 2) * (1 - disc) * np.clip((s_ / 2 - dd_) / (r * 1.2), 0, 1) ** 2)
        return rgb_r.astype(np.float32), disc.astype(np.float32), halo.astype(np.float32)

    def paste_red_moon(fr, r, c, gain=0.8, glow=0.30):
        rgb, Ad, halo = red_moon(r, gain)
        fr = K.paste_sprite(fr, rgb, Ad, *c)
        z = np.zeros_like(rgb)
        return K.paste_sprite(fr, z + np.array([0.75, 0.04, 0.12], np.float32) * glow * gain, halo, *c, add=True)

    def sky_redden(sky, c, rad=600, amt=0.07):
        x, y = K.grid(); d = np.sqrt((x - c[0]) ** 2 + (y - c[1]) ** 2)
        tint = (np.exp(-(d / rad) ** 2) * amt)[..., None] * np.array([1.0, 0.05, 0.15], np.float32)
        return sky * np.array([1.04, 0.88, 0.88], np.float32) + tint

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
    #   r5 F组 用户 #21：代码建模 → 生图；r6 F组：冕服生图；
    #   r6 F组第二棒（评审 7.5：冕冠读成高黑盒、顶边硬灰条、脸最亮不是逆光、龙纹看不见、人小）：
    #   · 换生图 R6_F/emp_flat_a（薄平冕板 + 低冠身、无前旒、冷灰眼），预处理 emp_flat_a_f（板压到 ≈18px 厚、alpha 收边羽化、
    #     脸压暗、龙纹提饱和/局部对比），见 crew/round6/F_r6b_prep_emp.py
    #   · 冕旒改为代码画：12 串玉珠从冕板前沿垂到眼下，随风微摆，月光下珠子闪 1–2 点；起幅双眼在旒与冕板阴影后，
    #     落幅 63.30–63.53 前排两串被风分开 ≈6 帧，露出一只冷灰、不发光的眼睛，随后合上（评审裁定的「戏眼」）
    #   · 比例 0.36 → 0.42，冕板顶 ≥ y200；满月 0.74 压在头后（月顶仍在画内），冕板剪影横过月面 = 逆光
    #   · 云只在胸口以下流过
    class S031Sprite(S031):
        SW = SH_ = 2048
        ANC = (1042 / 2048, 655 / 2048)                   # 两眼中点（源图像素 / 源图边长）
        BOARD_Y, BOARD_X = 127.0, (640.0, 1428.0)         # 冕板前沿（源图像素）
        EYE_L = (930.0, 655.0)                            # 露出的那只眼（画面左眼）
        T_OPEN, T_HOLD, T_CLOSE = 63.30, 63.37, 63.47
        def __init__(self):
            super().__init__(); self.sp = L('R6_F/emp_flat_a_f')
            self.sx = np.linspace(self.BOARD_X[0] + 20, self.BOARD_X[1] - 20, 12)
            k = int(np.argmin(np.abs(self.sx - self.EYE_L[0])))
            self.sx += self.EYE_L[0] - self.sx[k]                      # 让一串正好垂在左眼前
            self.kL = k
        def _open(self, t):
            if t < self.T_OPEN or t >= self.T_CLOSE + 0.07: return 0.0
            if t < self.T_HOLD: return eio((t - self.T_OPEN) / (self.T_HOLD - self.T_OPEN))
            if t < self.T_CLOSE: return 1.0
            return 1 - eio((t - self.T_CLOSE) / 0.07)
        def _beads(self, fr, t, ax, ay, s):
            """12 串玉珠（屏幕空间画）：小珠密串；逆光下是暗剪影，背后越亮（月面）勾边越亮；月光下闪 1–2 点"""
            S2 = lambda px, py: (ax + (px - self.ANC[0] * self.SW) * s, ay + (py - self.ANC[1] * self.SH_) * s)
            op = self._open(t)
            Lb = np.zeros((H, W), np.float32); Lr = np.zeros((H, W), np.float32); Lg = np.zeros((H, W), np.float32)
            rr = max(2.0, 10.5 * s)
            nb = 16; step = 35.0
            glint = []
            for i, x0 in enumerate(self.sx):
                sway = 6.0 * math.sin(t * 2.3 + i * 0.9) + 3.0 * math.sin(t * 3.7 + i * 1.7)
                part = 0.0
                if i == self.kL: part = -64.0 * op
                elif i == self.kL + 1: part = 34.0 * op
                elif i == self.kL - 1: part = -20.0 * op
                top = S2(x0, self.BOARD_Y)
                prev = top
                for j in range(nb):
                    yy = self.BOARD_Y + 22 + j * step
                    f = (yy - self.BOARD_Y) / (nb * step)
                    px, py = S2(x0 + (sway + part) * f ** 0.9, yy)
                    cv2.line(Lb, (int(prev[0] * 4), int(prev[1] * 4)), (int(px * 4), int(py * 4)), 0.7, 1, cv2.LINE_AA, 2)
                    r_ = rr * (0.85 + 0.3 * ((i * 7 + j * 3) % 5) / 4)
                    cv2.circle(Lb, (int(px * 4), int(py * 4)), int(r_ * 4), 1.0, -1, cv2.LINE_AA, 2)
                    cv2.circle(Lr, (int(px * 4), int(py * 4)), int(r_ * 4), 1.0, 2, cv2.LINE_AA, 2)
                    prev = (px, py)
                    ph = math.sin(t * 7.0 + i * 2.1 + j * 1.3)
                    if ph > 0.992 and j < 5 and abs(i - self.kL - 1.5) > 3: glint.append((px - r_ * 0.35, py - r_ * 0.4, (ph - 0.992) / 0.008))
            glint.sort(key=lambda g: -g[2])
            for gx, gy, g in glint[:2]:                                    # 月光点：同屏最多 2 粒
                cv2.circle(Lg, (int(gx), int(gy)), 1, float(g), -1, cv2.LINE_AA)
            back = cv2.GaussianBlur(fr.mean(-1), (0, 0), 6)                # 珠子背后的亮度：月面前 = 剪影 + 亮勾边
            Lb = cv2.GaussianBlur(Lb, (0, 0), 0.5)
            fr = fr * (1 - 0.9 * Lb[..., None]) + Lb[..., None] * np.array([0.018, 0.026, 0.024], np.float32)
            rim = cv2.GaussianBlur(Lr, (0, 0), 0.6) * np.clip(Lb * 1.2, 0, 1) * np.clip(back * 0.7, 0.05, 0.45)
            fr = fr + rim[..., None] * np.array([0.62, 0.68, 0.78], np.float32) * 0.7
            if glint:
                fr = fr + (cv2.GaussianBlur(Lg, (0, 0), 0.9) * 5 + cv2.GaussianBlur(Lg, (0, 0), 4) * 8)[..., None] * np.array([0.85, 0.92, 1.0], np.float32)
            return fr
        def render(self, t):
            u = self.u(t)
            cr = 60 * (1 - eio(u))                       # 巨像从地平线后缓缓升起 60px 落定
            fr = cam(self.bg, 1.0, 0, -cr * 0.25)
            s = 0.42 * (1 + 0.02 * u)
            ax, ay = 960, 448 + cr
            S2 = lambda px, py: (ax + (px - self.ANC[0] * self.SW) * s, ay + (py - self.ANC[1] * self.SH_) * s)
            mx, my = S2(1034, 430)
            fr = K.paste_sprite(fr, *self.moon, mx, my, scale=0.74)     # 满月压在头后：逆光光源，冕板剪影横过月面
            x, y = K.grid()
            halo = np.exp(-((x - mx) ** 2 + (y - my) ** 2) / (2 * 380.0 ** 2)).astype(np.float32)
            fr = fr + halo[..., None] * np.array([0.08, 0.09, 0.11], np.float32)
            fade = np.clip(1.0 - (y - (ay + 420)) / 360, 0.2, 1.0).astype(np.float32)   # 胸以下渐隐入云
            fr, _ = self.sp.draw(fr, t * 0.6, self.ANC, (ax, ay), s, wind_amp=3.0, breathe=0.0,
                                 grade=dict(expo=0.40, sat=0.62, tint=(0.88, 0.93, 1.07), lift=0.0, gamma=1.3),
                                 rim=dict(col=(0.88, 0.92, 1.0), amt=2.8, dir=(0, -1)), wrap=0.9,
                                 shade=None, alpha=0.97, extra_A=fade)
            # 冕板在眼部的投影（旒后双眼沉在暗里）；分旒那一刻左眼局部移开阴影 + 一点冷灰眼神光（不发光）
            op = self._open(t)
            ex0, ey0 = S2(*self.EYE_L); ex1, ey1 = S2(1155, 655)
            band = np.exp(-((y - ey0) / (60 * s / 0.42)) ** 2) * np.exp(-((x - (ex0 + ex1) / 2) / (260 * s / 0.42)) ** 4)
            eyeL = np.exp(-(((x - ex0) / (46 * s / 0.42)) ** 2 + ((y - ey0) / (26 * s / 0.42)) ** 2))
            fr = fr * (1 - (0.55 * band * (1 - 0.85 * op * eyeL))[..., None])
            fr = fr * (1 + (0.9 * op * eyeL)[..., None] * np.array([0.92, 0.98, 1.08], np.float32))   # 分旒处漏进一缕冷月光：这只眼读得清
            if op > 0.01:
                fr = fr + (np.exp(-(((x - ex0 - 3) / 2.2) ** 2 + ((y - ey0 + 2) / 1.6) ** 2)) * 0.14 * op)[..., None] * np.array([0.80, 0.85, 0.90], np.float32)
            fr = self._beads(fr, t, ax, ay, s)
            # 云层只在胸口以下流过（天幕感），不遮脸
            cl = cv2.resize(K.tile_crop(self.cloud, t * 40, 0, H // 4, W // 4), (W, H))
            ca_ = np.clip((cl - 0.5) * 2.2, 0, 1) * 0.40 * sstep(ay + 380, ay + 560, y)
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
        # r6 F组第二棒（评审 6.5：69.867 糊团、跳不高、70.1 独立白光横穿字、字像标题不像刻）：
        #   · 4 姿势沿一条看得见的抛物线：蓄力脚底 y900 → 腾空 apex 脚底 ≈y712（头顶 ≥ y150）→ 俯冲斜劈右下斜落 → 落地 y900
        #   · 腾空首帧 = js3_apex_b 清晰版（运动模糊 ≤4px、残影 ≤0.25）；落地首帧残影减半
        #   · 「那就劈开它」= 墙面阴刻（字内压暗 ~30%、上沿内侧压暗、下沿内侧提亮、砖纹穿过笔画、「劈」填朱）
        #   · 斩痕 = 人物刀弧本身：一条从字腰斜切入、弯向右下刀尖的刀弧（不再有独立白带）；字沿刀弧被切开，
        #     上下两半沿法线错开 12px 后不合拢，切口红热 0.8s 冷却成暗红；火星不进字的包围盒
        T_APEX = 69.865
        T_STRK = 69.955         # 命中前一帧（69.967）先见俯冲斜劈姿势
        T_LAND = 70.10          # r6 第三棒：俯冲压到 4 帧（69.967–70.067），每帧位移 ≈47px，不再冻帧
        GY = 900                # 脚底线
        # r6 第三棒（评审 #23-1 起跳缩小）：四张生图的人物比例尺不同（头宽实测：蓄力 230px / 腾空 290 / 斩 230 / 落地 180 源像素），
        # 屏幕缩放统一按「人物比例尺」= CS / REL，各姿势头宽一致（±3%），高度变化只靠位置
        CS = 0.45
        REL = {'crouch': 1.0, 'apex': 1.26, 'strike': 1.0, 'land': 0.78}
        POSES = {'crouch': ('R5_F/js1_crouch_b', 600), 'apex': ('R5_F/js3_apex_b', 560),
                 'strike': ('R5_F/js4_strike_a', 600), 'land': ('R5_F/js5_land_a', 600)}
        TXT, TX, TY, TS = '那就劈开它', 470.0, 252.0, 88      # 刻字：整句中心、字号
        C0, C1 = (150.0, 226.0), (790.0, 282.0)                # 字上的切线（≈5°，穿过五字中腰），刀弧由此弯向右下
        GAP = 12.0                                             # 劈开后上下两半沿法线错开
        FLASH_C, FLASH_R, FLASH_A = (760.0, 300.0), 330.0, 0.30      # 命中暖白闪：中心（刀弧交字处偏右下）、σ、峰值
        def __init__(self):
            super().__init__()
            self.P = {k: L(p) for k, (p, h) in self.POSES.items()}
            # 刻字那片墙去掉原有的小楷律令字（同 seed 重建一面无字墙，只在刻字区羽化替换），免得底纹字和刻字打架
            cw0 = PR.CharWall(seed=35, cols=16, rows=18, brick=(170, 72), fname='kai', chars_ratio=0.0,
                              text='顾全大局理所应当规矩方圆不得僭越')
            yy = np.linspace(0, 1, cw0.tex.shape[0], dtype=np.float32)[:, None, None]
            warm = (0.75 + 1.1 * np.clip((yy - 0.45) / 0.55, 0, 1) ** 1.5) * np.array([1.12, 0.92, 0.72], np.float32)
            clean = (cw0.tex * warm).astype(np.float32)
            m = np.zeros(self.wall.shape[:2], np.float32)
            m[200 + 170:200 + 335, 200 + 150:200 + 800] = 1.0
            m = cv2.GaussianBlur(m, (0, 0), 14)[..., None]
            self.wall = self.wall * (1 - m) + clean * m
            # 刀弧路径：字上直线段 → 三次曲线弯向右下（命中时刀尖处）
            c0, c1 = np.array(self.C0), np.array(self.C1); d = (c1 - c0) / np.linalg.norm(c1 - c0)
            q1, q2, q3 = c1 + d * 380, np.array([1430.0, 560.0]), np.array([1560.0, 800.0])
            seg = [c0 + (c1 - c0) * u for u in np.linspace(0, 1, 30)]
            seg += [(1 - u) ** 3 * c1 + 3 * (1 - u) ** 2 * u * q1 + 3 * (1 - u) * u * u * q2 + u ** 3 * q3 for u in np.linspace(0, 1, 60)[1:]]
            self.path = np.array(seg, np.float32)
            self.d = d; self.n = np.array([-d[1], d[0]])                 # n 指向切线下方
            # 刻字蒙版（整句 / 朱红「劈」）
            La, Lr = T.Layer(), T.Layer()
            adv = self.TS * (1 + LY.TRACK_H)
            for i, ch in enumerate(self.TXT):
                g = T.glyph(ch, LY.F_MAIN, self.TS, False)
                cx = self.TX + (i - 2) * adv
                La.paste(g, cx, self.TY, (1, 1, 1))
                if ch == '劈': Lr.paste(g, cx, self.TY, (1, 1, 1))
            x, y = K.grid()
            side = ((x - c0[0]) * self.n[0] + (y - c0[1]) * self.n[1]).astype(np.float32)
            self.side = side
            self.MA, self.MR = La.A.copy(), Lr.A.copy()
            bb = np.argwhere(La.A > 0.02); (yy0, xx0), (yy1, xx1) = bb.min(0), bb.max(0)
            self.tbox = (xx0 - 40, yy0 - 40, xx1 + 40, yy1 + 40)          # 火星禁区（字包围盒外扩，含错开余量）
        def _pose(self, t):
            """→ (姿势名, 脚底屏幕位置 (x, y), 旋转, mblur, 残影 (名, 脚底位置, alpha) | None)"""
            fps = 1 / 30
            if t < self.T_APEX:                                            # 蓄力：压低重心向右滑步
                k = eio(clamp01((t - self.t0) / (self.T_APEX - self.t0)))
                return 'crouch', (620 + 70 * k, self.GY), 0.0, (6 * k, 0), None
            if t < self.T_STRK:                                            # 腾空：抛物线顶点附近，清晰，几乎不糊
                i = int(round((t - self.T_APEX) / fps))                    # 0,1,2
                fx = (845, 885, 915)[min(i, 2)]; fy = (800, 788, 782)[min(i, 2)]
                g = ('crouch', (690, self.GY), 0.22) if i == 0 else None
                return 'apex', (fx, fy), (-2.0, -1.0, 0.0)[min(i, 2)], ((4, -3), (2, -1), (0, 0))[min(i, 2)], g
            if t < self.T_LAND:                                            # 俯冲斜劈：沿抛物线右下斜落
                k = clamp01((t - self.T_STRK) / (self.T_LAND - self.T_STRK))
                fx = 990 + 170 * k; fy = 790 + 110 * k                     # 匀速斜落：每帧 ≈47px
                g = ('apex', (915, 782), 0.22 * (1 - clamp01((t - self.T_STRK) / 0.07)))
                return 'strike', (fx, fy), 0.0, (8, 6), g
            a = t - self.T_LAND                                            # 落地收刀：沉身
            k = eout(clamp01(a / 0.2), 2)
            g = ('strike', (1160, 890), 0.12 * (1 - clamp01(a / 0.05)))
            return 'land', (1250 + 40 * clamp01(a / 0.65), self.GY + 14 * (1 - k) - 14), 0.0, (6 * (1 - k), 6 * (1 - k)), g
        def _put(self, fr, t, name, foot, rot=0.0, mblur=(0, 0), alpha=1.0, rim=None, gr=None):
            sp = self.P[name]
            x0, y0, x1, y1 = sp.bbox
            s = self.CS / self.REL[name] * 2048 / max(sp.w, sp.h)       # 人物比例尺统一（源图长边 2048 归一）
            return sp.draw(fr, t, ((x0 + x1) / 2, y1), foot, s, rot=rot, mblur=mblur, rim=rim, grade=gr,
                           shade=None, wind_amp=6.5, alpha=alpha, wrap=0.4)[0]
        def _carve(self, fr, t, shift):
            """墙面阴刻「那就劈开它」；命中后沿刀弧切开，上下两半错开 GAP（不合拢）"""
            a = t - self.T_HIT
            off = self.GAP * eout(clamp01(a / 0.07), 2) if a >= 0 else 0.0
            sd = self.side
            if off > 0:
                up = np.clip(0.5 - sd / 1.2, 0, 1); dn = 1 - up
                def mv(m, k):
                    M = np.float32([[1, 0, shift + self.n[0] * k + self.d[0] * k * 0.3], [0, 1, self.n[1] * k + self.d[1] * k * 0.3]])
                    return cv2.warpAffine(m, M, (W, H), flags=cv2.INTER_LINEAR)
                MA = mv(self.MA * up, -off / 2) + mv(self.MA * dn, off / 2)
                MR = mv(self.MR * up, -off / 2) + mv(self.MR * dn, off / 2)
            else:
                M = np.float32([[1, 0, shift], [0, 1, 0]])
                MA = cv2.warpAffine(self.MA, M, (W, H)); MR = cv2.warpAffine(self.MR, M, (W, H))
            x, y = K.grid()
            pool = np.exp(-(((x - self.TX - shift) / 420) ** 2 + ((y - self.TY - 10) / 110) ** 2)).astype(np.float32)
            fr = fr * (1 + 0.9 * pool[..., None] * np.array([1.0, 0.9, 0.78], np.float32))            # 斜掠火光照亮刻字那片墙
            Mb = cv2.GaussianBlur(MA, (0, 0), 0.8)
            dn2 = np.roll(Mb, 4, axis=0); up2 = np.roll(Mb, -3, axis=0)
            top = np.clip(Mb - dn2, 0, 1); bot = np.clip(Mb - up2, 0, 1)
            lum = fr.mean(-1, keepdims=True)
            fr = fr * (1 - 0.42 * Mb[..., None]) * (1 - 0.85 * top[..., None])
            fr = fr + np.clip(bot * 1.6, 0, 1)[..., None] * (0.10 + 1.8 * lum) * np.array([1.0, 0.82, 0.60], np.float32)   # 下沿内侧受火光
            lip = np.clip(np.roll(Mb, -2, axis=0) - Mb, 0, 1)                                       # 字口上沿外棱（未凿的砖面）一线微光
            fr = fr + lip[..., None] * (0.03 + 0.5 * lum) * np.array([1.0, 0.86, 0.7], np.float32)
            outl = np.clip(cv2.GaussianBlur(MA, (0, 0), 2.2) - Mb, 0, 1)                              # 刻口外缘一圈微压暗
            fr = fr * (1 - 0.18 * outl[..., None])
            mr = cv2.GaussianBlur(MR, (0, 0), 0.6)[..., None]
            red = np.array(LY.RED_T, np.float32) * (0.55 + 2.2 * lum)                                 # 朱砂填色，砖纹透出
            fr = fr * (1 - 0.82 * mr) + red * 0.82 * mr
            if off > 0:                                                    # 切口：沿切线一道深槽 + 红热边，0.8s 冷却成暗红
                Ls = np.zeros((H, W), np.float32)
                c0 = np.array(self.C0) + [shift, 0]; c1 = np.array(self.C1) + [shift, 0]
                cv2.line(Ls, tuple((c0 * 4).astype(int)), tuple((c1 * 4).astype(int)), 1.0, max(2, int(off * 0.5)), cv2.LINE_AA, 2)
                Ls = cv2.GaussianBlur(Ls, (0, 0), 0.8)
                inside = cv2.GaussianBlur(cv2.dilate(MA, np.ones((7, 7), np.uint8)), (0, 0), 3)
                Ls = Ls * np.clip(inside * 1.5, 0.35, 1)
                hot = math.exp(-a / 0.28)
                col = np.array([1.0, 0.42, 0.12], np.float32) * hot + np.array([0.42, 0.05, 0.03], np.float32) * (1 - hot)
                fr = fr * (1 - 0.85 * Ls[..., None])
                rim = np.clip(cv2.GaussianBlur(Ls, (0, 0), 2.0) * 1.6 - Ls, 0, 1)
                fr = fr + rim[..., None] * col * (0.30 + 0.55 * hot) + cv2.GaussianBlur(Ls, (0, 0), 5)[..., None] * col * 0.25 * hot
            return fr
        def _trail(self, fr, t, shift):
            """人物刀弧：69.967 起从字腰切入，命中帧到刀尖；字上那段 2 帧内熄灭，刀尖段 0.16s 衰减"""
            a = t - self.T_STRK
            if a < 0: return fr
            head = clamp01(0.55 + 0.45 * a / max(self.T_HIT - self.T_STRK, 1e-3))
            if t < self.T_HIT: head = 0.55
            n = len(self.path); i1 = max(2, int(head * n))
            Lb = np.zeros((H // 2, W // 2), np.float32)
            tt = max(0.0, t - self.T_HIT)
            for i in range(i1 - 1):
                u = i / n
                f = math.exp(-tt / (0.045 if u < 0.33 else 0.12)) * (0.35 if u < 0.33 else 1.0)
                w = max(1, int((3 + 14 * math.sin(math.pi * min(1.0, u / max(head, 1e-3))) ** 0.8) / 2))
                p0 = self.path[i] + [shift, 0]; p1 = self.path[i + 1] + [shift, 0]
                cv2.line(Lb, tuple((p0 / 2 * 4).astype(int)), tuple((p1 / 2 * 4).astype(int)), float(f), w, cv2.LINE_AA, 2)
            if Lb.max() < 0.01: return fr
            Lb = cv2.resize(Lb, (W, H))
            core = cv2.GaussianBlur(Lb, (0, 0), 1.0)
            fr = fr + core[..., None] * np.array([1.2, 1.15, 1.08], np.float32) + cv2.GaussianBlur(Lb, (0, 0), 10)[..., None] * np.array([0.8, 0.55, 0.35], np.float32)
            edge = np.clip(cv2.GaussianBlur(Lb, (0, 0), 4) - core, 0, 1)
            return fr + edge[..., None] * RED * 1.2
        def render(self, t):
            camx = 0.0 if t < self.T_HIT else 40 * clamp01((t - self.T_HIT) / 0.6)
            sh = -camx * 0.6                                               # 墙面（含刻字）跟随视差
            src = self.wall[200:1280, int(200 + camx * 0.6) % 400: int(200 + camx * 0.6) % 400 + 1920]
            fr = src * 0.8
            x, y = K.grid()
            fr = fr * (0.55 + 0.6 * np.exp(-(((x - 1050) / 900) ** 2 + ((y - 450) / 600) ** 2)))[..., None]
            if t >= self.T_HIT:
                pc = eout((t - self.T_HIT) / 0.15, 2)
                cm = K.draw_crack((H, W), self.crack - [camx * 0.6, 0], 6, branches=14, seed=352, prog=pc)
                fr = over(fr, cm, (0, 0, 0))
                fr += K.blur_ds(cm, 6)[..., None] * 1.5 * GOLD * 0.5 * (0.4 + 0.6 * math.exp(-(t - self.T_HIT) / 0.4))
            fr = self._carve(fr, t, sh)
            rim = dict(col=(1.0, 0.78, 0.5), amt=1.8, dir=(0.0, 1.0))     # 底部金红火光逆打
            gr = dict(expo=0.80, sat=0.6, tint=(1.0, 0.95, 0.9), lift=0.0, gamma=1.18)
            name, pos, rot, mb, ghost = self._pose(t)
            pos = (pos[0] - camx, pos[1])
            if name == 'crouch':
                fr = speed_lines(fr, t, 351, 1.0, 0.14 * clamp01((t - self.t0) / 0.1), y0=500, y1=880)
            if ghost and ghost[2] > 0.02:                                  # 前一姿势残影（冷灰半透，动作连贯）
                fr = self._put(fr, t, ghost[0], (ghost[1][0] - camx, ghost[1][1]), alpha=ghost[2],
                               rim=dict(col=(0.7, 0.78, 0.95), amt=1.0, dir=(0, -1)),
                               gr=dict(expo=0.45, sat=0.2, tint=(0.85, 0.92, 1.05), lift=0.04, gamma=1.0))
            fr = self._trail(fr, t, 0.0)                                   # 刀弧在人物身后
            fr = self._put(fr, t, name, pos, rot, mb, rim=rim, gr=gr)
            if name == 'crouch' or name == 'land':                         # 接触阴影
                cs = np.exp(-(((x - pos[0]) / 230) ** 2 + ((y - self.GY - 4) / 14) ** 2)).astype(np.float32)
                fr = fr * (1 - 0.5 * cs[..., None])
            xa, ya, xb, yb = self.tbox
            keep = np.ones((H, W), np.float32); keep[max(0, ya):yb, max(0, xa):xb] = 0
            keep = cv2.GaussianBlur(keep, (0, 0), 8)[..., None]
            if t >= self.T_HIT:
                a = t - self.T_HIT
                r = np.random.default_rng(3530)
                Lb = np.zeros((H // 2, W // 2), np.float32)
                # r6 第三棒（评审 #23-2 落地后浮着的方形暗斑）：碎砖重力 500→2600、不再随时间放大，沿速度方向拉运动模糊，
                # 0.25–0.38s 内淡出 / 落出画（70.4 以后墙面上没有任何碎块）
                fade = 1 - sstep(0.25, 0.38, a)
                for i in range(22):
                    ox, oy = r.uniform(1100, 1500), r.uniform(380, 720)
                    vx, vy = r.normal(250, 500), r.normal(-250, 300)
                    s = r.uniform(18, 50); rot0 = r.uniform(0, 180)
                    if fade <= 0.01: continue
                    for k in range(4):                                       # 4 次采样 = 运动模糊
                        aa = max(0.0, a - k * 0.008)
                        px, py = ox + vx * aa - camx * 0.6, oy + vy * aa + 2600 * aa * aa
                        if py > 940: continue
                        box = cv2.boxPoints(((px / 2, py / 2), (s / 2, s * 0.45 / 2), rot0 + 300 * aa))
                        cv2.fillConvexPoly(Lb, box.astype(np.int32), 0.3 * fade, cv2.LINE_AA)
                Lb = np.clip(Lb, 0, 1)
                fr = over(fr, cv2.resize(cv2.GaussianBlur(Lb, (0, 0), 1.5), (W, H)), (0.03, 0.03, 0.035))
                base = fr
                fr = K.sparks(fr, t, 3540, (1250, 600), n=70, life=0.5, speed=(400, 1200), dirc=(0.5, -0.5), spread=0.9,
                              grav=900, burst=True, t0=self.T_HIT, area=(150, 200))
                fr = base + (fr - base) * keep                             # 火星不进字的包围盒
            if self.T_LAND <= t < self.T_LAND + 0.5:                       # 落地扬尘
                fr = K.sparks(fr, t, 3550, (1250 - camx, self.GY - 8), n=40, life=0.5, speed=(150, 450), dirc=(1, -0.2), spread=1.4,
                              grav=300, burst=True, t0=self.T_LAND, area=(260, 10), color=(0.6, 0.58, 0.55), amt=0.5)
            # r6 第三棒（评审 #23-4 命中帧发灰）：整帧抬灰 → 只在命中帧（1 帧）加一团暖白加色闪，中心在刀弧交字处，四角几乎不动，黑位不抬
            sk = pulse(t, self.T_HIT, 0.12) * (t >= self.T_HIT)
            if abs(t - self.T_HIT) < 0.5 / 30:
                fx_, fy_ = self.FLASH_C
                fl = np.exp(-((x - fx_) ** 2 + (y - fy_) ** 2) / (2 * self.FLASH_R ** 2)).astype(np.float32)
                fr = fr + (fl * self.FLASH_A)[..., None] * np.array([1.0, 0.9, 0.74], np.float32)
            dx, dy, dr = shake(t, 12 * sk, 16, 35)
            fr = cam(fr, 1.02 + 0.025 * sk, dx, dy, dr)
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
            # r6 F组第二棒（评审「83.6 袖口/衣襟抠像白描边」）：alpha 腐蚀 2px 再羽化，轮廓环带重算，去 halo
            sp = self.sp
            sp.A = cv2.GaussianBlur(cv2.erode(sp.A, np.ones((5, 5), np.uint8)), (0, 0), 1.2)
            sp.F = sp.F * np.clip(sp.A * 1.5, 0, 1)[..., None] + sp.F * 0                   # 边缘残留亮色随 alpha 一起收掉
            ring = sp.A - cv2.erode(sp.A, np.ones((5, 5), np.uint8))
            sp.ring = cv2.GaussianBlur(np.clip(ring, 0, 1), (0, 0), 1.5)
        def render(self, t):
            u = self.u(t)
            fr = self.bg.copy()
            prog = eio(clamp01((t - self.t0 - 0.15) / 0.8))
            s = W / self.sp.w * 1.02
            ax, ay = 960 - 12 * prog, 560
            fr, _ = self.sp.draw(fr, t, (0.5, 0.5), (ax, ay), s, wind_amp=0.0, breathe=0.002,
                                 rim=dict(col=(0.80, 0.86, 1.0), amt=0.7, dir=(-0.3, -1.0)),
                                 grade=dict(expo=0.80, sat=0.55, tint=(0.9, 0.96, 1.06), lift=0.0, gamma=1.15), shade=None, wrap=0.0)
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
        MOON = (1500, 372)                               # r6 第二棒：月心下移 72px → 月顶 ≥ y200，不被 2.39 上黑边切平
        def __init__(self):
            super().__init__(); self.w1, self.w3 = L('S045/windup'), L('R5_F/s45_follow_a')
            # r6 第二棒（评审 #27）：沿用 #26 的猩红之月（亮度 ×0.8，人物剪影仍有对比），叙事不再从红月跳回白月
            sk = K.sky(seed=45, cloud=0.55, horizon=0.72, top=(0.03, 0.035, 0.05), bot=(0.16, 0.17, 0.2)).copy()
            sk = sky_redden(sk, self.MOON)
            sk = paste_red_moon(sk, 170, self.MOON)
            far = K.mountains(W, H, 760, 120, 451, 4)
            self.bg = over(sk, far * 0.6, (0.07, 0.075, 0.09))
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
        HW, HF = 557, 590                                                  # 包围盒高：r6 第二棒 follow 0.92 倍（640→590），切换不再往前跳一步
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
            fr = K.rain(fr, t, 451, n=320, amt=0.4, speed=2000 if t > 84.36 else 600, angle=6, region=band, near=0.0)
            fr = K.rain(fr, t, 457, n=36, amt=0.22, speed=2600 if t > 84.36 else 800, angle=6, region=band, near=0.0, length=(90, 160))   # 近层：细（≤5px）、半透
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
            bg = sky_redden(K.sky(seed=46, cloud=0.5).copy(), (1500, 330))                       # r6 第二棒：月色沿用猩红之月
            self.bg = cv2.GaussianBlur(paste_red_moon(bg, 140, (1500, 330)), (0, 0), 10)
            x, y = K.grid(); self.x, self.y = x, y
            self.inkm = sstep(660, 580, x).astype(np.float32)        # r6：墨爆收在刀身左侧更远处，不再有墨滴溅上刀身（读作血点）
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
            # r6 F组（#28 可选「去掉红点」）：左耳廓内侧的红（耳朵透光）在暗画面里读成一个红点 → 局部去饱和
            k_ = s / 0.50
            erx, ery = ex + 205 * k_, ey - 110 * k_
            em_ = np.exp(-(((x - erx) / (46 * k_)) ** 2 + ((y - ery) / (60 * k_)) ** 2)).astype(np.float32)[..., None]
            lum_ = fr.mean(-1, keepdims=True)
            fr = fr * (1 - em_) + lum_ * np.array([0.97, 0.99, 1.03], np.float32) * em_
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
                # r6 F组第二棒（评审 #28 可选）：颗粒/飞白版试过像毛毡（见 F_r6.md 第二棒），回退形状，只把平涂橙压成朱砂墨色
                edge = np.clip(K.blur_ds(m, 6) - m * 0.85, 0, 1)
                fr = over(fr, m, np.array([0.30, 0.040, 0.030], np.float32))
                fr += edge[..., None] * np.array([0.55, 0.16, 0.06], np.float32) * (1 - 0.5 * pb)
            return fr, (3 if k > 0.5 else 0)

    out = {}
    for c in (S029Sprite, S030Sprite, S031Sprite, S035Sprite, S037Sprite, S038Sprite, S039Sprite, S041Sprite, S044Sprite, S045Sprite, S046Sprite):
        nm = c.__name__.replace('Sprite', ''); c.__name__ = nm; out[nm] = c
    return out
