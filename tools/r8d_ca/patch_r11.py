"""一次性改稿（SPREAD §10 §11 + 裁切边硬规则）：对 units/r8d_c_a.py 做逐条替换，每条必须命中。"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
p = ROOT + '/units/r8d_c_a.py'
s = open(p).read()
R = [
# ---- plate：去 blur（景深虚化 = CG），改网点渐隐；加水平镜像（跨镜复用换机位）
('''_PL = {}
def plate(name, gain=1.0, blur=0.0, size=(W, H)):
    k = (name, gain, blur, size)
    if k not in _PL:
        im = cv2.cvtColor(cv2.imread(A_DIR + name + '.jpg'), cv2.COLOR_BGR2RGB)
        im = cv2.resize(im, size, interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        if blur: im = cv2.GaussianBlur(im, (0, 0), blur)
        _PL[k] = im * gain
    return _PL[k]''',
'''_PL = {}
def plate(name, gain=1.0, recede=0.0, size=(W, H), flip=False):
    """背景板。recede>0：远景用「降反差 + 网点」渐隐做纵深（SPREAD §11：不用景深虚化）；flip：水平镜像（跨镜复用时换机位）。"""
    k = (name, gain, recede, size, flip)
    if k not in _PL:
        im = cv2.cvtColor(cv2.imread(A_DIR + name + '.jpg'), cv2.COLOR_BGR2RGB)
        im = cv2.resize(im, size, interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        if flip: im = np.ascontiguousarray(im[:, ::-1])
        if recede: im = tone_recede(im, recede)
        _PL[k] = im * gain
    return _PL[k]


_DOT = {}
def dots(h=H, w=W, pitch=7.0):
    """45° 漫画网点底纹（-1..1），网点密度用阈值控制"""
    k = (h, w, pitch)
    if k not in _DOT:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        u = (xx + yy) / math.sqrt(2); v = (xx - yy) / math.sqrt(2)
        _DOT[k] = ((np.cos(2 * math.pi * u / pitch) + np.cos(2 * math.pi * v / pitch)) / 2).astype(np.float32)
    return _DOT[k]


def tone_recede(im, amt):
    """远景渐隐：反差压向中灰 + 一层细网点（清晰墨线仍在，只是退远）"""
    h, w = im.shape[:2]
    lum = im.mean(-1, keepdims=True)
    out = im * (1 - 0.45 * amt) + (0.30 + 0.25 * lum) * 0.45 * amt
    d = dots(h, w, 6.0)
    dm = np.clip((d - 0.55) / 0.15, 0, 1)[..., None]
    return out * (1 - 0.18 * amt * dm) + 0.10 * amt * dm * (lum < 0.3)


def halo_tone(fr, c, r, amt, col=(1.0, 1.0, 1.0)):
    """网点光晕（代替柔光辉光 / 镜头光斑）：越近中心网点越密越亮，边缘是一颗颗清楚的网点"""
    if amt <= 0.005: return fr
    x, y = _grid()
    g = np.exp(-(((x - c[0]) ** 2 + (y - c[1]) ** 2) / (r * r)))
    d = dots(pitch=8.0)
    m = np.clip((d - (1 - 2 * g * min(1.0, amt * 1.4))) / 0.12, 0, 1) * min(1.0, amt * 1.6)
    return fr * (1 - m[..., None] * 0.55) + m[..., None] * np.asarray(col, np.float32) * 0.85'''),
# ---- 各镜背景板：去 blur → recede；复用板换镜像 / 裁切
("        self.bg = plate('CA_room', 0.55, blur=7)", "        self.bg = plate('CA_room', 0.62, recede=0.5)"),
("        fr = K.vol_light(fr, (1560, 250), 700, (1.0, 1.0, 1.0), 0.10 * flick)", "        fr = halo_tone(fr, (1560, 250), 520, 0.45 * flick)"),
("        # 前景：血红灯笼焦外光斑（视差 1.6）+ 浮尘\n        fr = K.vol_light(fr, (90 - _par(u, 120), 260), 230, (0.85, 0.06, 0.04), 0.55)\n", "        # 前景浮尘（不做焦外光斑：SPREAD §11）\n"),
("        self.bg = plate('CA_room', 0.42, blur=9)", "        self.bg = plate('CA_room', 0.55, recede=0.6, flip=True)          # 同殿换机位：镜像 + 上部裁切"),
("        fr = view(self.bg, 1.08, -_par(u, 30), oy * 0.3)\n        fr = K.vol_light(fr, (960, 120), 600, (1.0, 1.0, 1.0), 0.10)",
 "        fr = view(self.bg, 1.35, -_par(u, 30), 160 + oy * 0.3)\n        fr = halo_tone(fr, (960, 160), 520, 0.40)"),
("        self.bg = plate('CA_room', 0.40, blur=10)", "        self.bg = plate('CA_room', 0.55, recede=0.6)"),
("        fr = view(self.bg, 1.10, -_par(u, 40), 0)\n        fr = K.vol_light(fr, (1500, 250), 520, (1.0, 1.0, 1.0), 0.10)",
 "        fr = view(self.bg, 1.5, 260 - _par(u, 40), 60)                  # 同殿换机位：放大取左侧灯笼与立柱\n        fr = halo_tone(fr, (1500, 250), 420, 0.35)"),
("            fr = fr + fl * 0.35 * np.exp(-(((np.arange(W)[None, :] - rpan[0]) / 380) ** 2 + ((np.arange(H)[:, None] - rpan[1]) / 260) ** 2))[..., None]",
 "            fr = halo_tone(fr, (rpan[0], rpan[1] - 40), 300, 0.9 * fl)"),
("        fr = K.vol_light(fr, (120 - _par(u, 150), 860), 170, (0.85, 0.06, 0.04), 0.50)      # 前景灯笼光斑\n", ""),
("        self.bg = plate('CA_room', 0.30, blur=14)", "        self.bg = plate('CA_room', 0.50, recede=0.7, flip=True)"),
("        fr = view(self.bg, 1.15 + 0.1 * u, 0, 0)", "        fr = view(self.bg, 1.6 + 0.1 * u, 0, -220)                     # 同殿换机位：镜像 + 取地面一角"),
("        fr = K.vol_light(fr, (cx, cy), 300 * z, (1.0, 1.0, 1.0), 0.05)", "        fr = halo_tone(fr, (cx, cy), 260 * z, 0.25)"),
("        self.bg = plate('CA_room', 0.75, blur=8)", "        self.bg = plate('CA_room', 0.75, recede=0.4)"),
("        self.blade = Prop('C11_blade', work=0.5); self.bg = plate('CA_sky', 0.45, blur=10)",
 "        self.blade = Prop('C11_blade', work=0.5); self.bg = plate('CA_sky', 0.55, recede=0.7, flip=True)"),
("        fr = view(self.bg, 1.15, -_par(u, 50), 0)\n        x = lerp(1060, 860, eio(u))\n        fr, A = self.blade.draw(fr, self.blade.src(1024, 555), (x, 560), 1.02)",
 "        fr = view(self.bg, 1.5, -_par(u, 50), 150)\n        x = lerp(-60, -200, eio(u))                                  # 护手压在画左外（刀柄不入画），画面里只有刀身\n        fr, A = self.blade.draw(fr, self.blade.src(560, 555), (x, 560), 1.45)"),
("        fr = sparks(fr, t, 111, (x + 380, 545),", "        fr = sparks(fr, t, 111, (1250, 545),"),
("        fr = sparks(fr, t, 112, (x + 380, 545),", "        fr = sparks(fr, t, 112, (1250, 545),"),
("        self.blade = Prop('C11_blade', work=1.0); self.bg = plate('CA_sky', 0.25, blur=16)",
 "        self.blade = Prop('C11_blade', work=1.0); self.bg = plate('CA_sky', 0.35, recede=0.8)"),
("        fr = view(self.bg, 1.2, -_par(u, 30), 0)\n        fr, A = self.blade.draw(fr, self.blade.src(1500, 560)",
 "        fr = view(self.bg, 1.9, -300 - _par(u, 30), 80)\n        fr, A = self.blade.draw(fr, self.blade.src(1500, 560)"),
# C13：旋转时板必须盖满画幅（内切圆半径 ≥ 画幅区半对角 1048）
("        far = view(self.bg, z * 0.85, 0, 0, rot=rot)", "        far = view(self.bg, z * 1.58, 0, 0, rot=rot)"),
("        near = view(self.bg, nz * 0.85, 0, 0, rot=nrot); na = view(self.nearA, nz * 0.85, 0, 0, rot=nrot)\n        near = cv2.GaussianBlur(near, (0, 0), 5); na = cv2.GaussianBlur(na, (0, 0), 5) * 0.55",
 "        near = view(self.bg, nz * 1.58, 0, 0, rot=nrot); na = view(self.nearA, nz * 1.58, 0, 0, rot=nrot) * 0.55"),
("        self.sp = spr('C14_ots'); self.bg = plate('C13_vortex', 0.85, blur=2, size=(2400, 1350))",
 "        self.sp = spr('C14_ots'); self.bg = plate('C13_vortex', 0.85, recede=0.3, size=(2400, 1350), flip=True)"),
("        fr = view(self.bg, 0.9, 140 - _par(u, 40), -200, rot=8 * u)", "        fr = view(self.bg, 1.62, 160 - _par(u, 40), 180, rot=8 * u)"),
# C08 发丝层位移不露边
("        z = 1.0 + 0.05 * u + 0.05 * pulse(t, tf, 0.15) * (t >= tf)", "        z = 1.03 + 0.05 * u + 0.05 * pulse(t, tf, 0.15) * (t >= tf)"),
("        fr = rain_fg(fr, t, 2, amt=0.6, speed=2600, scale=0.8, blur=1.5, cam=(_par(u, 80), 0))", "        fr = rain_fg(fr, t, 2, amt=0.6, speed=2600, scale=0.8, cam=(_par(u, 80), 0))"),
# C15 / C16 / C17 / C18：同一积水原换机位
("        self.a = spr('C15_stand'); self.b = spr('C15_flick'); self.bg = plate('CA_water', 0.9)",
 "        self.a = spr('C15_stand'); self.b = spr('C15_flick'); self.bg = plate('CA_water', 0.9, flip=True)"),
("        fr = K.vol_light(fr, (foot[0], 560), 420, (1.0, 1.0, 1.0), 0.22 + 0.3 * fl)    # 背光把人从血红天边托出",
 "        fr = halo_tone(fr, (foot[0], 560), 420, 0.55 + 0.4 * fl)    # 网点背光把人从血红天边托出"),
("        fr = view(self.bg, 1.15, -_par(u, 30), -150)", "        fr = view(self.bg, 1.35, 200 - _par(u, 30), -170)"),
("        self.sp = spr('C17_kneel'); self.bg = plate('CA_water', 0.85)", "        self.sp = spr('C17_kneel'); self.bg = plate('CA_water', 0.85, flip=True)"),
("        fr = view(self.bg, 1.1, -_par(u, 30), 20)", "        fr = view(self.bg, 1.6, -260 - _par(u, 30), 60)"),
("            fr = fr + pulse(t, tl, 0.06) * 0.35 * np.exp(-(((np.arange(W)[None, :] - 960) / 500) ** 2 + ((np.arange(H)[:, None] - 870) / 200) ** 2))[..., None]",
 "            fr = halo_tone(fr, (960, 870), 420, 1.2 * pulse(t, tl, 0.06))"),
("        self.hero = spr('C18_draw'); self.bg = plate('CA_water', 0.8)", "        self.hero = spr('C18_draw'); self.bg = plate('CA_water', 0.8, recede=0.3)"),
("        fr = view(self.bg, 1.05, -_par(u, 20), -40)", "        fr = view(self.bg, 1.3, 220 - _par(u, 20), -60)"),
# C18：甲士不再按直线切成三份 —— 整组三人一个刚体（避免长枪 / 披风被直线截断）
('''        im = cv2.imread(A_DIR + 'C18_soldiers_cut.png', cv2.IMREAD_UNCHANGED)
        h, w = im.shape[:2]; xx = np.arange(w)[None, :]
        cuts = [(0, 560), (560, 1480), (1480, w)]
        self.sold = [Prop('C18_soldiers', mask=np.broadcast_to(((xx >= a) & (xx < b)).astype(np.float32), (h, w)), work=0.5) for a, b in cuts]
        self.fx = [((a + b) / 2) for a, b in cuts]''',
'''        self.sold = Prop('C18_soldiers', work=0.5)                  # 三人一组整张刚体（不切：长枪、披风互相交叠）'''),
("                n = 4 if row < 3 else 3 if row < 5 else 1", "                n = 2 if row < 3 else 1"),
("                    xw = side * (0.55 + (i + (0.5 if row % 2 else 0)) * 0.62 + r.uniform(-0.08, 0.08))",
 "                    xw = side * (0.95 + (i + (0.5 if row % 2 else 0)) * 1.25 + r.uniform(-0.08, 0.08))"),
('''        P = self.sold[d['k']]
        src_h = 1000 if d['k'] == 1 else 760
        sc = h / src_h
        fr2, Aw = P.draw(fr, P.src(self.fx[d['k']], 1050), (x, y), sc, blur=(3.0 + 6.0 * (1 - fade) if z < 1.6 else 1.2 * far), alpha=fade)''',
'''        P = self.sold
        sc = h / 1050
        fr2, Aw = P.draw(fr, P.src(1024, 1080), (x, y), sc, alpha=fade)'''),
("        fr = K.fog(fr, t, 18, density=0.45, y0=560, y1=880, color=(0.8, 0.8, 0.8), speed=(30, 0))\n        fr, A = put(fr, self.hero",
 "        fr, A = put(fr, self.hero"),
# C19：枪杆 / 枪头在杆上切（红缨不被直线截断，切口就是被斩的位置）；枪不做焦外虚化
('''        h, w = im.shape[:2]; xx = np.broadcast_to(np.arange(w)[None, :], (h, w))
        self.shaft = Prop('C19_spear', mask=(xx < 1480).astype(np.float32), work=0.5)
        self.head = Prop('C19_spear', mask=(xx >= 1480).astype(np.float32), work=0.5)''',
'''        h, w = im.shape[:2]; xx = np.broadcast_to(np.arange(w, dtype=np.float32)[None, :], (h, w))
        cut = np.clip((xx - 1240) / 3 + 0.5, 0, 1)                # 斩口在红缨后面的杆上（杆细，切口即刀口）
        self.shaft = Prop('C19_spear', mask=1 - cut, work=0.5)
        self.head = Prop('C19_spear', mask=cut, work=0.5)'''),
("        blur = 7.0 if sp['near'] else 0.8\n", "        blur = 0.0\n"),
("        self.a = spr('C18_draw'); self.b = spr('C19_spin'); self.bg = plate('CA_sky', 0.7, blur=4)",
 "        self.a = spr('C18_draw'); self.b = spr('C19_spin'); self.bg = plate('CA_sky', 0.75, recede=0.4, flip=True)"),
("        fr = view(self.bg, 1.1, -_par(u, 50), 0)\n        fr = lit(fr, fl * 0.4)\n        fr = K.fog(fr, t, 19",
 "        fr = view(self.bg, 1.35, 180 - _par(u, 50), -120)\n        fr = lit(fr, fl * 0.4)\n        fr = K.fog(fr, t, 19"),
("        fr = K.vol_light(fr, (960, 640), 520, (1.0, 1.0, 1.0), 0.30 + 0.5 * fl)      # 背光：白光把人从暗云里托出来",
 "        fr = halo_tone(fr, (960, 640), 520, 0.6 + 0.4 * fl)      # 网点背光：把人从暗云里托出来"),
# C13 近层不再虚化（上面已改）；C02 纱袖下沿：有形状的羽化（噪声扰动），不是直线渐隐
('''        self.fadeA = np.broadcast_to(np.clip((560 - g * H) / 160, 0, 1), (H, W)).astype(np.float32)   # 纱袖下沿渐隐（原图平切）''',
'''        nz = cv2.resize(cv2.GaussianBlur(np.random.default_rng(202).random((H // 24, W // 24)).astype(np.float32), (0, 0), 1.0), (W, H),
                        interpolation=cv2.INTER_CUBIC)
        self.fadeA = np.clip((540 + (nz - 0.5) * 260 - g * H) / 110, 0, 1).astype(np.float32)   # 纱袖下沿：噪声扰动的不规则羽化'''),
# C04：天平铰接件按真实结构分：横梁（含中央饰件）/ 立柱 + 底座 / 两盘（从挂钩下连链条）；分界在空隙里或羽化
('''        yy, xx = np.mgrid[0:h, 0:w]
        beam = (yy < 215).astype(np.float32)
        lpan = ((yy >= 215) & (xx < 760)).astype(np.float32)
        rpan = ((yy >= 215) & (xx > 1290)).astype(np.float32)
        post = ((yy >= 215) & (xx >= 760) & (xx <= 1290)).astype(np.float32)''',
'''        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        nz = cv2.resize(np.random.default_rng(404).random((h // 16, w // 16)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        beam = np.clip((236 + (nz - 0.5) * 24 - yy) / 14, 0, 1)                       # 横梁下沿：中央立柱处不规则羽化（梁转动时与立柱自然衔接）
        side = ((xx < 820) | (xx > 1230)).astype(np.float32)
        beam = np.where(side > 0, (yy < 210).astype(np.float32), beam)                 # 两端：梁与链条之间是空隙，直接分
        pans = side * (yy >= 210) * (yy < 870)
        lpan = pans * (xx < 820); rpan = pans * (xx > 1230)
        post = np.clip(1 - beam - lpan - rpan, 0, 1)                                    # 立柱 + 底座（底座横跨两侧，整块不动）'''),
]
for a, b in R:
    assert a in s, 'MISS: ' + a[:90]
    s = s.replace(a, b)
open(p, 'w').write(s)
print('ok', len(R))
