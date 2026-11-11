"""第八轮 STYLE_D：E 段后半（EB 单元）—— 副歌终章收尾 + 尾奏片尾，帧 6638–7241（原镜号 S132–S138）。
只在 STYLE_D=1 时由 sec_e_final_outro 末尾的钩子 import 并 apply(mod)；STYLE_D=0 完全不加载，现版逐像素不变。

风格 D（日漫墨线 + 网点 + 严格黑白血红）：全部镜头换成 assets/gen/R8_D/EB/ 的新生图（RH_image2，提示词 jobs/r8_D_EB.json），
精灵合成一律 grade=NEU / rim=NORIM / wrap=0 / shade=None。切点、镜长、入转场、MOVE 运镜、SHAKE 冲击、鼓点表全部沿用 e_r9 之后的现版。
文字（USER_NOTES_r8）：
  - E31（S134）灼烧露出的「天」「理」「规」「章」「律」—— 画进生图 EB_scraps（逐字放大核对），代码只做「灰烬烧开、露出字」的动画。
  - 片名「谁定正邪」/「鬼屠 · 第二季」/「主题曲《谁定正邪》」、6 行出品署名、「鬼屠」印章 —— 合同要求（HANDOFF §1），保留；
    改为宣纸墨书（墨晕洇开，无描边/投影/外发光的电脑字效果），「邪」与印章血红，不用金。
  - 其余画面字一律不出（E27c 匾只给背面，不出「天理昭彰」）。
"""
import math, os, zlib
import numpy as np, cv2
import c1kit as K
import typo as T
import trans as TR
import sprite as SP
import rest_sprites as RS
import e_kit as E
import e_r3 as R3
from e_kit import W, H, BAR, c01, eio, eout, sstep

M = None
ROOT = os.environ.get('MV_ROOT', '/workspace/work/mv')
D = ROOT + '/assets/gen/R8_D/EB/'
R1 = ROOT + '/assets/gen/R8_D/route1/'
NEU = dict(expo=1.0, sat=1.0, tint=(1.0, 1.0, 1.0), lift=0.0, gamma=1.0)
NORIM = dict(col=(1.0, 1.0, 1.0), amt=0.0, dir=(0.0, -1.0))
KW = dict(grade=NEU, rim=NORIM, wrap=0, shade=None, keep_red=1.0)
REDC = np.array([0.74, 0.04, 0.04], np.float32)            # 血红
INKC = np.array([0.03, 0.03, 0.03], np.float32)
WHT = np.array([1.0, 1.0, 1.0], np.float32)
FPS = 30


class Shot:
    def u(self, t): return (t - self.t0) / (self.t1 - self.t0)
    def render(self, t): return np.zeros((H, W, 3), np.float32)
    def text(self, fr, t): return fr


# ------------------------------------------------------------------ 素材
_P = {}
def plate(name, flip=False, blur=0.0, gain=1.0):
    k = (name, flip, blur, gain)
    if k not in _P:
        im = cv2.cvtColor(cv2.imread(D + name + '.png'), cv2.COLOR_BGR2RGB)
        im = cv2.resize(im, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        if flip: im = np.ascontiguousarray(im[:, ::-1])
        if blur: im = cv2.GaussianBlur(im, (0, 0), blur)
        _P[k] = im * gain
    return _P[k]


_L = {}
def lay(name, flip=False, base=D):
    """精灵层（绿幕抠像 *_cut.png）；flip 水平翻转（同 c_kit.spr 的做法，只读共享数组拷贝一份）。"""
    k = (base + name, flip)
    if k not in _L:
        L = SP.SpriteLayer(base + name + '_cut.png') if flip else SP.layer(base + name + '_cut.png')
        if flip:                                                                                 # 翻转写法同 c_kit.spr（新实例，不改共享缓存）
            for a in ('A', 'F', 'wind_w', 'ring'): setattr(L, a, np.ascontiguousarray(getattr(L, a)[:, ::-1]))
            x0, y0, x1, y1 = L.bbox; L.bbox = (1 - x1, y0, 1 - x0, y1); L.top = (1 - L.top[0], L.top[1])
        _L[k] = L
    return _L[k]


def draw(fr, L, t, src_px, dst, s, **kw):
    """src_px：精灵像素坐标（2048 宽工作分辨率）→ 画面 dst；s = 画面像素 / 精灵像素。"""
    a = dict(KW); a.update(kw)
    return L.draw(fr, t, (src_px[0] / L.w, src_px[1] / L.h), dst, s, **a)


def to_scr(L, src_px, dst, s, p, rot=0.0):
    X = (p[0] - src_px[0]) * s; Y = (p[1] - src_px[1]) * s
    c, si = math.cos(math.radians(-rot)), math.sin(math.radians(-rot))
    return (dst[0] + X * c - Y * si, dst[1] + X * si + Y * c)


def view(img, z=1.0, cx=W / 2, cy=H / 2, rot=0.0):
    """全幅图层：图上 (cx,cy) 放到画面中心、缩放 z（反射边界）。"""
    Mx = cv2.getRotationMatrix2D((float(cx), float(cy)), rot, z)
    Mx[0, 2] += W / 2 - cx; Mx[1, 2] += H / 2 - cy
    return cv2.warpAffine(img, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def rgba_piece(fr, F, A, cx, cy, s, rot, pc=None, extra=None):
    """刚体碎片（预乘前色 F、alpha A，局部坐标中心 pc）贴到 (cx,cy)。返回 (fr, Aw)。"""
    h, w = A.shape
    pc = pc or (w / 2, h / 2)
    Mx = cv2.getRotationMatrix2D(pc, rot, s); Mx[0, 2] += cx - pc[0]; Mx[1, 2] += cy - pc[1]
    Fw = cv2.warpAffine(F * A[..., None], Mx, (W, H)); Aw = cv2.warpAffine(A, Mx, (W, H))
    if extra is not None: Fw = Fw + cv2.warpAffine(extra, Mx, (W, H))
    return fr * (1 - Aw[..., None]) + Fw, Aw


def screentone(h, w, pitch=7, ang=45):
    """网点（0..1，点心 1）——给代码画的雾/烟/影子加漫画网点质感。"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = math.radians(ang)
    u = (xx * math.cos(a) + yy * math.sin(a)) / pitch; v = (-xx * math.sin(a) + yy * math.cos(a)) / pitch
    return (0.5 + 0.25 * (np.cos(2 * math.pi * u) + np.cos(2 * math.pi * v))).astype(np.float32)


_TONE = {}
def tone():
    if 'k' not in _TONE: _TONE['k'] = screentone(H, W)
    return _TONE['k']


def toned(m, amt=1.0):
    """把平滑浓度 m (0..1) 变成网点覆盖率（漫画网点阶调）。"""
    return np.clip((m * 1.15 - (1 - tone())) * 4.0, 0, 1) * amt


def ink_lines(fr, t, seed, center, n=90, r0=380, amt=0.9, col=INKC, width=(1, 3)):
    """漫画集中线：从画面四周指向 center 的墨线（内端留空 r0）。"""
    r = np.random.default_rng(seed)
    Lk = np.zeros((H // 2, W // 2), np.float32)
    for i in range(n):
        a = r.uniform(0, 2 * math.pi); r1 = r0 * r.uniform(0.9, 1.6); r2 = 1500
        p1 = (center[0] + math.cos(a) * r1, center[1] + math.sin(a) * r1 * 0.75); p2 = (center[0] + math.cos(a) * r2, center[1] + math.sin(a) * r2 * 0.75)
        cv2.line(Lk, (int(p1[0] / 2), int(p1[1] / 2)), (int(p2[0] / 2), int(p2[1] / 2)), r.uniform(0.5, 1.0), int(r.integers(width[0], width[1] + 1)), cv2.LINE_AA)
    Lk = cv2.resize(cv2.GaussianBlur(Lk, (0, 0), 0.6), (W, H)) * amt
    return fr * (1 - Lk[..., None]) + Lk[..., None] * np.asarray(col, np.float32)


def mist(fr, t, seed, y0, y1, speed, amt=0.35, col=(0.95, 0.95, 0.95), scale=4, t_ref=0.0):
    """横向漂移的雾带（位移以 t_ref 为零：镜头中点对齐）。"""
    k = ('mist', seed)
    if k not in _P: _P[k] = K.fbm(H // 4, W // 2, seed, base=scale, octaves=5).astype(np.float32)
    n = _P[k]
    m = cv2.resize(R3.slide(n, (t - t_ref) * speed / 4), (W, H))
    yy = np.arange(H, dtype=np.float32)[:, None]
    band = sstep(y0 - 60, y0 + 40, yy) * (1 - sstep(y1 - 40, y1 + 60, yy))
    a = np.clip((m - 0.42) * 2.4, 0, 1) * band * amt
    return fr * (1 - a[..., None]) + a[..., None] * np.asarray(col, np.float32)


def ash(fr, t, t0, seed, n=60, amt=0.7, drift=(-30, 140), red=0.15, size=(3, 9)):
    """飘落的灰烬片（灰白片 + 少量血红余烬心）。"""
    r = np.random.default_rng(seed)
    Pg = np.zeros((H // 2, W // 2), np.float32); Pr = np.zeros_like(Pg)
    for i in range(n):
        x0, y0 = r.uniform(0, W), r.uniform(-200, H); sp = r.uniform(0.4, 1.0); ph = r.uniform(0, 6.28); sz = r.uniform(*size)
        y = (y0 + (t - t0) * drift[1] * sp) % (H + 200) - 100
        x = x0 + (t - t0) * drift[0] * sp + 25 * math.sin(t * 1.6 + ph)
        tgt = Pr if r.random() < red else Pg
        cv2.ellipse(tgt, (int(x / 2), int(y / 2)), (max(1, int(sz / 2)), max(1, int(sz * 0.22))), (t * 70 + ph * 57) % 180, 0, 360, sp, -1, cv2.LINE_AA)
    Pg = cv2.resize(cv2.GaussianBlur(Pg, (0, 0), 0.6), (W, H)); Pr = cv2.resize(cv2.GaussianBlur(Pr, (0, 0), 0.8), (W, H))
    fr = fr * (1 - 0.55 * Pg[..., None] * amt) + Pg[..., None] * 0.55 * amt * 0.85
    return fr + Pr[..., None] * REDC * 1.4 * amt


def spark2(fr, t, seed, origin, t0, n=40, **kw):
    """火星（白 + 血红）。"""
    kw.setdefault('burst', True)
    fr = K.sparks(fr, t, seed, origin, n=n, t0=t0, color=(1.0, 1.0, 1.0), **kw)
    return K.sparks(fr, t, seed + 1, origin, n=max(4, n // 2), t0=t0, color=(0.85, 0.03, 0.03), **kw)


def ink_spatter(fr, t, seed, origin, t0, n=40, **kw):
    """溅墨（墨点从 origin 迸出）——在亮底上压暗。"""
    a = t - t0
    if a < 0 or a > kw.get('life', 0.6) * 1.3: return fr
    z = K.sparks(np.zeros_like(fr), t, seed, origin, n=n, t0=t0, burst=True, color=(1.0, 1.0, 1.0), **kw)
    m = np.clip(z[..., :1] * 1.6, 0, 1)
    return fr * (1 - m) + INKC * m


from e_r9 import beat_pulse, step_zoom                                                         # 鼓点脉冲 / 阶梯推镜：与现版同一实现


# ------------------------------------------------------------------ 署名（合同署名，HANDOFF §1 一字不差）
def credit(fr, role, names, x, y, p, color, role_size=32, name_size=66, seal_text=None, seed=None):
    st = seal_text or (role[0] if names[0][0].isascii() else names[0][0])
    sd = zlib.crc32(role.encode('utf-8')) % 50 if seed is None else seed
    return R3.credit_block_up(fr, role, names, x, y, p, role_size=role_size, name_size=name_size, seal_text=st,
                              seal_size=46, color=color, name_font='kai', seed=sd)


class CreditsD(Shot):
    """blocks = (role, names, x, y_top, t_start, dur)；ccol 'white'（暗底）/ 'ink'（亮底：宣纸墨书，无描边/投影/外发光）。"""
    blocks = []
    ccol = 'white'
    fade = True
    kws = {}

    def credits(self, fr, t):
        for (role, names, x, y, ts, dur) in self.blocks:
            p = c01((t - ts) / dur)
            if p <= 0: continue
            out = c01((t - (self.t1 - 0.35)) / 0.35) if self.fade else 0.0
            g = credit(fr.copy(), role, names, x, y, p, self.ccol, **self.kws)
            fr = g * (1 - out) + fr * out
        return fr

    def text(self, fr, t): return self.credits(fr, t)


# ================================================================== 副歌终章收尾
class E27a(Shot):   # S132 眼 ECU：EB_eyes（左半脸压在墨影里、右颊血红轮廓光）；入点集中线 + 冲击，镜内急推；发丝随风
    def __init__(self):
        self.L = lay('EB_eyes')
        yy, xx = E.grid()
        self.bg = (np.zeros((H, W, 3), np.float32) + 0.02) + (np.exp(-((xx - 1500) / 380) ** 2) * 0.9)[..., None] * REDC

    def render(self, t):
        u = self.u(t)
        s = 1.50 * (1 + 0.05 * eout(u))
        fr, A = draw(self.bg.copy(), self.L, t, (1080, 845), (960 + 24 * (u - 0.5), 540), s, breathe=0, wind_amp=5.0)
        k = (t - self.t0) * FPS
        fr = ink_lines(fr, t, 2701, (960, 520), n=110, r0=420, amt=0.85 * math.exp(-k / 6.0))   # 冲击集中线：入点满、0.2s 散去
        g = math.exp(-((t - self.t0 - 0.30) / 0.06) ** 2)                                       # 0.3s 眼神光一闪（白十字星芒，右眼）
        if g > 0.02:
            ex, ey = to_scr(self.L, (1080, 845), (960 + 24 * (u - 0.5), 540), s, (1300, 840))
            yy, xx = E.grid()
            st = np.exp(-(np.abs(xx - ex) / 3 + np.abs(yy - ey) / 50)) + np.exp(-(np.abs(yy - ey) / 3 + np.abs(xx - ex) / 140))
            fr = fr + (st * g * 1.4)[..., None]
        return fr


class E27b(Shot):   # S132x 斩：EB_slash 出刀定姿剪影 + EB_stroke 生图飞白斩痕沿弧线一笔写出（干笔飞白 + 溅墨）；入点两帧反白冲击
    def __init__(self):
        self.L = lay('EB_slash'); self.S = lay('EB_stroke')
        n = cv2.resize(K.fbm(H // 4, W // 4, 2710, base=5, octaves=5), (W, H))
        self.bg = (0.025 + 0.05 * n)[..., None] * np.ones(3, np.float32)
        yy, xx = E.grid()
        self.bg = self.bg + (np.exp(-(((xx - 1400) / 700) ** 2 + ((yy - 300) / 420) ** 2)) * 0.55)[..., None] * REDC
        self.sx = np.ascontiguousarray(np.broadcast_to(self.S.gx / max(1, self.S.w - 1), (self.S.h, self.S.w))).astype(np.float32)                       # 笔画沿 x 的进度

    def render(self, t):
        u = self.u(t); a = t - self.t0; k = int(round(a * FPS))
        pr = eout(c01(a / 0.20), 3)                                                             # 斩痕 0.2s 写完
        head = 0.02 + 1.03 * pr
        ext = np.clip((head - self.sx) / 0.04, 0, 1)
        fr = self.bg.copy()
        ss = W / self.S.w * 1.06
        z, As = draw(np.zeros_like(fr), self.S, t, (1024, 576), (960 + 30 * (u - 0.5), 520), ss, breathe=0, wind_amp=0, extra_A=None)
        # 写出遮罩：在精灵空间按 x 进度裁切，再按同一仿射搬到画面
        Mx = cv2.getRotationMatrix2D((1024.0, 576.0), 0, ss); Mx[0, 2] += 960 + 30 * (u - 0.5) - 1024; Mx[1, 2] += 520 - 576
        ew = cv2.warpAffine(ext, Mx, (W, H))
        Aw = As * ew
        Fz = z / np.maximum(As, 1e-3)[..., None]
        fr = fr * (1 - Aw[..., None]) + Fz * Aw[..., None]
        hx = to_scr(self.S, (1024, 576), (960 + 30 * (u - 0.5), 520), ss, (head * self.S.w, 0))[0]
        # 笔头白热（只在写出过程中）
        if pr < 0.98:
            yy, xx = E.grid()
            hg = np.exp(-((xx - hx) / 60) ** 2) * Aw * (1 - pr)
            fr = fr + hg[..., None] * 1.2
        # 人物：出刀定姿，随斩痕落地（微滑入 + 横向模糊衰减），刀尖在斩痕尾端
        sp = 1 - eout(c01(a / 0.12), 2)
        fr, A = draw(fr, self.L, t, (1072, 1146), (720 - 50 * sp, 1010), 880 / 1141, mblur=(int(40 * sp) if k >= 2 else 0, 0), wind_amp=9.0, breathe=0.004)
        tip = to_scr(self.L, (1072, 1146), (720 - 50 * sp, 1010), 880 / 1141, (1990, 1060))
        fr = spark2(fr, t, 2720, tip, self.t0 + 0.02, n=70, life=0.55, speed=(500, 1500), dirc=(0.6, -0.5), spread=1.0, grav=1300, area=(30, 20))
        fr = ash(fr, t, self.t0, 2725, n=40, amt=0.5, drift=(80, -60), red=0.3)
        if k < 2:                                                                              # 反白冲击帧：白底、人物硬边纯黑剪影、只留斩痕的血红
            Ah = np.clip((A - 0.35) * 4, 0, 1)
            red = np.clip((Fz[..., 0] - np.maximum(Fz[..., 1], Fz[..., 2])) * 3, 0, 1) * Aw
            fr = np.ones_like(fr) * 0.97
            fr = fr * (1 - red[..., None]) + REDC * red[..., None]
            fr = fr * (1 - Ah[..., None]) + 0.015 * Ah[..., None]
        elif k == 2:
            fr = fr * 1.25 + 0.06
        return fr


class E27c(Shot):   # S132y 匾碎：EB_hall 暗殿（高窗斜光、红墙）+ EB_plaque 匾被一刀两断（只给背面，不出字）：两半各自翻转下坠、断口血红余烬、碎木片扑镜
    def __init__(self):
        self.bg = plate('EB_hall')
        P = cv2.cvtColor(cv2.imread(D + 'EB_plaque_cut.png', cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255
        P = cv2.resize(P, (W, H), interpolation=cv2.INTER_AREA)
        F, A = P[..., :3], P[..., 3]
        k, lab, st, cen = cv2.connectedComponentsWithStats((A > 0.04).astype(np.uint8), 8)
        big = sorted(range(1, k), key=lambda i: -st[i, 4])[:2]
        big = sorted(big, key=lambda i: cen[i][0])
        self.halves = []
        for i in big:
            m = (lab == i).astype(np.float32)
            m = cv2.dilate(m, np.ones((3, 3), np.uint8))
            self.halves.append((F, A * m, tuple(cen[i])))
        deb = A * (1 - np.clip(sum(cv2.dilate((lab == i).astype(np.float32), np.ones((3, 3), np.uint8)) for i in big), 0, 1))
        self.deb = (F, deb)
        self.red = np.clip((F[..., 0] - np.maximum(F[..., 1], F[..., 2])) * 3, 0, 1) * A        # 断口余烬（生图里的血红断面）

    def render(self, t):
        u = self.u(t); a = t - self.t0
        fr = view(self.bg, 1.04 + 0.03 * u, 960, 540 - 20 * (u - 0.5))                         # 背景慢推（视差：比匾慢）
        q = eout(c01(a / 0.5), 2)
        hot = 1.0 + 1.2 * math.exp(-a / 0.12)
        for j, (F, Ah, c) in enumerate(self.halves):
            sgn = -1 if j == 0 else 1
            rot = sgn * 9 * q; dx = sgn * 70 * q; dy = 30 * q + 260 * (a / 0.5) ** 2 * (0.8 if j == 0 else 1.0)
            ex = (self.red * Ah)[..., None] * REDC * (hot - 1) * 1.2
            fr, Aw = rgba_piece(fr, F, Ah, c[0] + dx, c[1] + dy, 1.0, rot, pc=c, extra=ex)
        F, Ad = self.deb                                                                         # 碎片：以画面中心为原点扑向镜头
        sd = 1.0 + 0.9 * eout(c01(a / 0.5), 2)
        al = 1 - sstep(0.25, 0.5, a)
        if al > 0.01:
            fr, _ = rgba_piece(fr, F, Ad * al, 960, 540, sd, 0, pc=(960, 540))
        fr = spark2(fr, t, 2730, (930, 520), self.t0, n=60, life=0.5, speed=(300, 1200), dirc=(0, -1), spread=1.5, grav=900, area=(40, 160))
        return fr


class E28(Shot):   # S132b ECU 马尾 + 血红腰带在逆光里翻飞：EB_sash（风吹 + 腰带行波二级运动），背景 EB_dawn 天空虚焦
    def __init__(self):
        self.L = lay('EB_sash')
        self.bg = view(plate('EB_dawn', flip=True, blur=7), 1.5, 1300, 330)
        yy, xx = E.grid(); self.xx, self.yy = xx, yy

    def render(self, t):
        u = self.u(t)
        fr = view(self.bg, 1.0, 960 - 30 * (u - 0.5), 540)                                        # 背景视差（以中点为零）
        z, A = draw(np.zeros_like(fr), self.L, t, (1024, 576), (960 + 20 * (u - 0.5), 540), W / self.L.w * 1.04, breathe=0, wind_amp=14.0)
        w = np.clip((1250 - self.xx) / 1250, 0, 1) ** 1.4                                        # 自由端（左）摆幅大，靠头（右）不动
        dy = (26 * np.sin(self.xx / 210.0 + t * 9.0) + 10 * np.sin(self.xx / 90.0 - t * 13.0)) * w
        dx = 14 * np.sin(self.yy / 160.0 + t * 7.0) * w
        mx = (self.xx - dx).astype(np.float32); my = (self.yy - dy).astype(np.float32)
        z = cv2.remap(z, mx, my, cv2.INTER_LINEAR); A = cv2.remap(A, mx, my, cv2.INTER_LINEAR)
        fr = fr * (1 - A[..., None]) + z
        fr = E.dust_motes(fr, t, 1331, n=70, amt=0.45, drift=(-160, -20), col=(1.0, 1.0, 1.0), depth=True)
        return fr


# ================================================================== 片名（宣纸墨书）
TITLE_S, TITLE_ADV, TITLE_Y = 340, 340 * 0.86, 470
TS = 225.42 - 1 / 30


def title_ink(t, start=223.97, stagger=0.10, dur=0.32):
    """「谁定正邪」行书：墨在宣纸上逐字洇开（按序错 0.10s，224.60s 前四字成形），「邪」血红。返回 Layer。"""
    L = T.Layer()
    x0 = 960 - TITLE_ADV * 1.5
    for k, ch in enumerate('谁定正邪'):
        e = c01((t - (start + stagger * k)) / dur)
        if e <= 0: continue
        a = T.ink_bleed_glyph(ch, 'xing', TITLE_S, e, seed=3 + k, bleed=0.55)
        L.paste(a, x0 + TITLE_ADV * k, TITLE_Y, tuple(REDC) if ch == '邪' else tuple(INKC))
    return L


class TitleD(Shot):
    """片名底板：EB_paper 宣纸 + 下方墨染远山与淡血红朝日；墨雾横向漂移（两层不同速度 = 视差）。"""
    def __init__(self):
        self.bg = plate('EB_paper')

    def base(self, t):
        u = self.u(t)
        fr = view(self.bg, 1.0 + 0.01 * u, 960 + 10 * (u - 0.5), 540)
        tm = (self.t0 + self.t1) / 2
        fr = mist(fr, t, 1341, 700, 960, 22, amt=0.30, col=(0.97, 0.97, 0.97), t_ref=tm)
        fr = mist(fr, t, 1342, 820, 960, 40, amt=0.22, col=(0.55, 0.55, 0.55), scale=6, t_ref=tm)
        return fr


class E29(TitleD):   # S133 片名「谁定正邪」墨书洇开
    def render(self, t):
        fr = self.base(t)
        L = title_ink(t)
        return T.compose(fr, L, shadow=0, glow=0)


class E30(TitleD):   # S133b 一道血红干笔斩痕劈过片名 → 宣纸上的墨字沿斩线错开淡去，洇出「鬼屠 · 第二季」+「主题曲《谁定正邪》」+ 鬼屠朱印
    def __init__(self):
        TitleD.__init__(self)
        ang = math.radians(-12)
        d = np.array([math.cos(ang), math.sin(ang)]); n = np.array([-d[1], d[0]])
        c = np.array([960.0, 470.0])
        self.d, self.n, self.c = d, n, c
        yy, xx = E.grid()
        self.s = ((xx - c[0]) * n[0] + (yy - c[1]) * n[1]).astype(np.float32)                  # 到斩线的有符号距离
        self.uu = (((xx - c[0]) * d[0] + (yy - c[1]) * d[1]) / 2200 + 0.5).astype(np.float32)     # 沿线进度
        # 斩痕笔刷（route1/D035_slash，本轮风格 D 生图）：按 alpha 主轴映射到斩线，横向压扁
        sl = cv2.cvtColor(cv2.imread(R1 + 'D035_slash_cut.png', cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255
        ys, xs = np.nonzero(sl[..., 3] > 0.5)
        P = np.stack([xs, ys], -1).astype(np.float64); pc = P.mean(0)
        e = np.linalg.eigh(np.cov((P - pc).T))[1][:, -1]
        if e[0] < 0: e = -e
        pr = (P - pc) @ e; A0, B0 = pc + e * pr.min(), pc + e * pr.max()
        Q0, Q1 = c - d * 1150, c + d * 1150
        sc = np.linalg.norm(Q1 - Q0) / np.linalg.norm(B0 - A0); ep = np.array([-e[1], e[0]])
        M2 = sc * np.outer(d, e) + 0.35 * sc * np.outer(n, ep)
        Mx = np.hstack([M2, (Q0 - M2 @ A0)[:, None]])
        w_ = cv2.warpAffine(sl, Mx, (W, H), flags=cv2.INTER_LINEAR)
        self.slF, self.slA = w_[..., :3], w_[..., 3]
        self.title = None

    def render(self, t):
        fr = self.base(t)
        q = t - TS
        if self.title is None: self.title = title_ink(999.0)
        L = self.title
        if q < 0:
            return T.compose(fr, L, shadow=0, glow=0)
        if q < 0.9:                                                                             # 墨字沿斩线上下错开 + 淡去
            e = eout(q / 0.5)
            up = (self.s < 0)
            Lz = T.Layer()
            for part, sg in ((up, -1), (~up, 1)):
                Mx = np.float32([[1, 0, sg * 60 * e], [0, 1, sg * 34 * e]])
                Ap = cv2.warpAffine(L.A * part, Mx, (W, H)); Cp = cv2.warpAffine(L.C * part[..., None], Mx, (W, H))
                sel = Ap > Lz.A; Lz.A = np.maximum(Lz.A, Ap); Lz.C[sel] = Cp[sel]
            Lz._touch(0, 0, W, H)
            fr = T.compose(fr, Lz, shadow=0, glow=0, opacity=1 - c01(q / 0.9))
        hd = c01((q + 0.03) / 0.08)                                                            # 斩痕一笔写出（左→右）、0.6s 内褪成淡痕
        if hd > 0:
            er = 1.08 * eio(c01((q - 0.22) / 0.30))                                              # 0.22s 起斩痕沿笔势收走（保持血红，不淡成粉灰），副标题出来前收干净
            rev = np.clip((hd * 1.05 - self.uu) / 0.03, 0, 1) * np.clip((self.uu - er) / 0.03, 0, 1) * self.slA
            fr = fr * (1 - rev[..., None]) + self.slF * rev[..., None]
            core = np.exp(-(self.s / 3.0) ** 2) * math.exp(-max(0.0, q) / 0.10) * (self.uu < hd)
            fr = fr + core[..., None] * 0.8
        fr = ink_spatter(fr, t, 3010, (960, 470), TS, n=50, life=0.5, speed=(300, 1100), dirc=(self.n[0], self.n[1]), spread=1.4, grav=900, area=(500, 10))
        fr = K.sparks(fr, t, 3012, (960, 470), n=30, life=0.45, speed=(250, 900), dirc=(-self.n[0], -self.n[1]), spread=1.2, grav=900, burst=True, t0=TS,
                      area=(500, 10), color=(0.75, -0.25, -0.25))
        p = c01((q - 0.25) / 0.6)
        if p > 0:
            L2 = T.Layer()
            for i, (ch, x, sz) in enumerate((('鬼', 505, 200), ('屠', 705, 200), ('第', 1025, 200), ('二', 1215, 214), ('季', 1405, 200))):
                e = c01(p * 1.6 - i * 0.12)
                if e <= 0: continue
                L2.paste(T.ink_bleed_glyph(ch, 'kai', sz, e, seed=21 + i, bleed=0.5), x, 470, tuple(INKC))
            fr = T.compose(fr, L2, shadow=0, glow=0)
            cv2.circle(fr, (860, 475), int(13 * eout(p)), tuple(float(v) for v in REDC), -1, cv2.LINE_AA)
            s2 = c01((q - 0.75) / 0.5)
            if s2 > 0:
                L3 = T.Layer()
                for i, ch in enumerate('主题曲《谁定正邪》'):
                    T.place(L3, ch, 960 + (i - 4) * 58, 650, 46, tuple(INKC), 'serif_m', alpha=eout(s2), texture=False)
                fr = T.compose(fr, L3, shadow=0, glow=0)
            sp = c01((q - 0.55) / 0.5)
            if sp > 0: fr = T.stamp_seal(fr, '鬼屠', 1610, 470, 130, sp, style='yin', rot=-5, seed=9, color=tuple(REDC))
        return fr


# ================================================================== 尾奏 · 署名
class E31(CreditsD):   # S134 正俯拍：焦土（EB_ground）上散着五片烧焦残纸（EB_scraps，字画进生图）；灰烬自纸面烧开、露出「天」「理」「规」「章」「律」，
    #  焦边余烬一明一灭逐渐冷却、细烟上升；署名① 出品人 / 编剧导演（白字，暗地）
    LAYOUT = {'天': (430, 400, -12, 0.60), '理': (810, 660, 14, 0.56), '规': (1075, 335, 6, 0.50), '章': (330, 790, -18, 0.50), '律': (1150, 805, 22, 0.48)}
    ORDER = ['理', '天', '规', '章', '律']     # 生图里的连通块按质心 (x,y) 映射：见 __init__

    def __init__(self):
        self.blocks = [('出品人', ['西几王传媒'], 1660, 230, 227.85, 0.9), ('编剧 / 导演', ['苏打'], 1430, 230, 228.45, 0.8)]
        self.bg = plate('EB_ground', flip=True, gain=0.92)
        P = cv2.cvtColor(cv2.imread(D + 'EB_scraps_cut.png', cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255
        F, A = P[..., :3], P[..., 3]
        k, lab, st, cen = cv2.connectedComponentsWithStats((A > 0.04).astype(np.uint8), 8)
        big = sorted(range(1, k), key=lambda i: -st[i, 4])[:5]
        # 质心 → 字：上排左中右 = 天 理 规；下排左右 = 章 律（逐字放大核对过）
        byy = sorted(big, key=lambda i: cen[i][1])
        top = sorted(byy[:3], key=lambda i: cen[i][0]); bot = sorted(byy[3:], key=lambda i: cen[i][0])
        names = dict(zip(top, '天理规')); names.update(dict(zip(bot, '章律')))
        assert len(big) == 5 and len(names) == 5, 'EB_scraps 应为 5 片残纸'
        self.pcs = []
        for i in big:
            x, y, w, h = st[i, :4]; pad = 12
            x0, y0 = max(0, x - pad), max(0, y - pad); x1, y1 = min(A.shape[1], x + w + pad), min(A.shape[0], y + h + pad)
            m = cv2.dilate((lab[y0:y1, x0:x1] == i).astype(np.float32), np.ones((3, 3), np.uint8))
            a = A[y0:y1, x0:x1] * m; f = F[y0:y1, x0:x1].copy()
            red = np.clip((f[..., 0] - np.maximum(f[..., 1], f[..., 2])) * 3, 0, 1) * a
            hh, ww = a.shape
            r = np.random.default_rng(1350 + i)
            nz = cv2.resize(r.random((9, 9)).astype(np.float32), (ww, hh), interpolation=cv2.INTER_CUBIC)
            nf = cv2.resize(r.random((40, 40)).astype(np.float32), (ww, hh), interpolation=cv2.INTER_LINEAR)
            yv = np.linspace(0, 1, hh, dtype=np.float32)[:, None]
            burn = 0.55 * nz + 0.15 * nf + 0.30 * (1 - yv)                                     # 灰烬烧开的到达场（自下而上 + 噪声）
            burn = (burn - burn.min()) / (burn.max() - burn.min() + 1e-6)
            self.pcs.append(dict(ch=names[i], F=f, A=a, red=red, burn=burn.astype(np.float32)))
        self.pcs.sort(key=lambda d: self.ORDER.index(d['ch']))
        self.smoke = K.fbm(H // 4, W // 4, 1355, base=5, octaves=5).astype(np.float32)

    def render(self, t):
        u = self.u(t); a = t - self.t0
        fr = view(self.bg, 1.0, 960 - 14 * (u - 0.5), 540)
        EMB = np.zeros((H, W), np.float32)
        for k, pc in enumerate(self.pcs):
            cx, cy, rot, s = self.LAYOUT[pc['ch']]
            rot = rot + 0.6 * math.sin(t * 0.9 + k)                                             # 热浪里极轻的漂移
            F, A, red, burn = pc['F'], pc['A'], pc['red'], pc['burn']
            hh, ww = A.shape
            prog = c01((a - 0.30 - 0.14 * k) / 0.75)                                            # 灰烬烧开：0.3s 起按序 0.14s 错开，0.75s 烧完
            front = prog * 1.15 - 0.08
            cov = np.clip((burn - front) / 0.05, 0, 1)                                          # 1 = 仍盖着灰烬
            band = np.exp(-((burn - front) / 0.035) ** 2) * (0 < prog < 1)
            Mi = cv2.invertAffineTransform(cv2.getRotationMatrix2D((ww / 2, hh / 2), rot, s) + np.float32([[0, 0, cx - ww / 2], [0, 0, cy - hh / 2]]))
            ashc = cv2.warpAffine(fr, Mi, (ww, hh), borderMode=cv2.BORDER_REFLECT) * 0.85         # 盖着的是焦土本身：字从焦土里烧出来
            G = F * (1 - cov[..., None]) + ashc * cov[..., None]
            fl = (0.55 + 0.45 * math.sin(t * (7 + k) + k * 1.7)) * (1 - 0.6 * u)                # 焦边余烬一明一灭、逐渐冷却
            redc = red[..., None] * (fl - 0.6)
            G = np.clip(G + redc * np.array([0.6, -0.15, -0.15], np.float32), 0, 1.5)
            ex = (band * A)[..., None] * (REDC * 1.8 + 0.6)
            shm = cv2.GaussianBlur(A, (0, 0), 9) * (1 - cov.mean() * 0.9)
            Ms = cv2.getRotationMatrix2D((ww / 2, hh / 2), rot, s); Ms[0, 2] += cx - ww / 2 + 12; Ms[1, 2] += cy - hh / 2 + 16
            fr = fr * (1 - 0.6 * cv2.warpAffine(shm, Ms, (W, H)))[..., None]                     # 接触影
            fr, Aw = rgba_piece(fr, G, A, cx, cy, s, rot, extra=ex)
            Mx = cv2.getRotationMatrix2D((ww / 2, hh / 2), rot, s); Mx[0, 2] += cx - ww / 2; Mx[1, 2] += cy - hh / 2
            EMB += cv2.warpAffine(red * max(0.0, fl) + band * A, Mx, (W, H))
        fr = fr + cv2.GaussianBlur(EMB, (0, 0), 7)[..., None] * REDC * 0.45
        Mt = np.float32([[1, 0, 0], [0, 1, -12 * (t - self.t0)]])                               # 细烟上升（网点烟）
        sm = cv2.resize(cv2.warpAffine(self.smoke, Mt, (W // 4, H // 4), borderMode=cv2.BORDER_REFLECT), (W, H))
        sm = np.clip((sm - 0.5) * 2.0, 0, 1)
        fr = fr * (1 - 0.18 * sm[..., None]) + (toned(sm, 0.22))[..., None] * 0.75
        fr = ash(fr, t, self.t0, 1356, n=40, amt=0.5, drift=(-10, -70), red=0.35, size=(2, 5))
        return fr


class E32(CreditsD):   # S135 CU 握刀柄的手沿刀身滑移（EB_hilt），刀身寒光自镡扫到刀尖；背景 EB_dawn 云天虚焦；署名② 美术设计 / 后期总监（墨书，亮底）
    ccol = 'ink'

    def __init__(self):
        self.blocks = [('美术设计', ['Cait'], 1700, 230, 230.15, 0.8), ('后期总监', ['沉溺'], 1470, 230, 230.75, 0.8)]
        self.L = lay('EB_hilt')
        self.bg = view(plate('EB_dawn', blur=6), 1.35, 1200, 360)

    def render(self, t):
        u = self.u(t)
        fr = view(self.bg, 1.0, 960 + 25 * (u - 0.5), 540 - 10 * (u - 0.5))
        d = np.array([0.74, -0.67])
        sl = 60 * eio(u)
        s = W / self.L.w * 1.0
        dst = (960 - 380 + d[0] * sl, 600 + d[1] * sl)
        fr, A = draw(fr, self.L, t, (1024, 576), dst, s, breathe=0.002, wind_amp=2.0)
        g0 = to_scr(self.L, (1024, 576), dst, s, (1470, 300)); g1 = to_scr(self.L, (1024, 576), dst, s, (2040, -120))
        k = eio(c01((u - 0.15) / 0.7))                                                          # 寒光自镡扫到刀尖（只亮在刀身上）
        px, py = g0[0] + (g1[0] - g0[0]) * k, g0[1] + (g1[1] - g0[1]) * k
        yy, xx = E.grid()
        along = ((xx - px) * d[0] + (yy - py) * d[1])
        perp = ((xx - g0[0]) * -d[1] + (yy - g0[1]) * d[0])
        bl = np.exp(-(along / 70) ** 2) * np.exp(-(perp / 40) ** 2) * A * (1.0 if 0.3 < k < 0.999 else 0.0)
        fr = fr + bl[..., None] * 1.3
        if 0.05 < k < 0.98: fr = E.flare_streak(fr, (px, py), amt=0.25, angle=-42, length=0.35, col=(1.0, 1.0, 1.0))
        return fr


class E33(CreditsD):   # S135b 焦土上横着一柄黑漆刀鞘（EB_scabbard），血红穗在晨风里摆、漆面晨光掠过、灰烬飘落；署名③ AI画师（白字，左侧）
    def __init__(self):
        self.blocks = [('AI画师', ['沉溺', '雪晴', '索恩'], 330, 200, 232.35, 1.0)]
        self.kws = dict(role_size=40, name_size=62, seal_text='画', seed=7)
        self.fade = False
        self.L = lay('EB_scabbard', flip=True)
        self.bg = view(plate('EB_ground', gain=0.95), 1.25, 1100, 600)
        yy, xx = E.grid(); self.xx, self.yy = xx, yy

    def render(self, t):
        u = self.u(t)
        fr = view(self.bg, 1.0, 960 - 30 * (u - 0.5), 540)
        s = 0.80; src = (1024, 576); dst = (1180 - 40 * (u - 0.5), 560)
        z, A = draw(np.zeros_like(fr), self.L, t, src, dst, s, breathe=0, wind_amp=0)
        top = to_scr(self.L, src, dst, s, (2048 - 170, 500)); bot = to_scr(self.L, src, dst, s, (2048 - 330, 1060))
        wy = np.clip((self.yy - top[1]) / max(1.0, bot[1] - top[1]), 0, 1) ** 1.3
        wx = np.exp(-((self.xx - (top[0] + bot[0]) / 2) / 240) ** 2)
        dx = (28 * math.sin(t * 2.6) + 10 * math.sin(t * 5.3 + 1.0)) * wy * wx                 # 红穗摆（越往下越大）
        mx = (self.xx - dx).astype(np.float32); my = self.yy.astype(np.float32)
        z = cv2.remap(z, mx, my, cv2.INTER_LINEAR); A = cv2.remap(A, mx, my, cv2.INTER_LINEAR)
        sh = cv2.GaussianBlur(A, (0, 0), 20)
        fr = fr * (1 - 0.65 * np.roll(np.roll(sh, 24, 0), -16, 1)[..., None])
        fr = fr * (1 - A[..., None]) + z
        notred = 1 - np.clip((z[..., 0] - np.maximum(z[..., 1], z[..., 2])) * 4, 0, 1)
        sweep = np.exp(-((self.xx - (200 + 1700 * u) + (self.yy - 540) * 0.6) / 110) ** 2) * A * notred
        fr = fr + sweep[..., None] * 0.45
        fr = ash(fr, t, self.t0, 1373, n=70, amt=0.8, drift=(-40, 150), red=0.12)
        return fr


# ---- 尾奏日出：EB_dawn（水墨远山 + 白天 + 血红朝日）
HITS34 = [(7040 / 30, 1.0), (7047 / 30, 0.6), (7054 / 30, 0.6), (7061 / 30, 1.0), (7072 / 30, 1.0)]
STRONG34 = [7040 / 30, 7061 / 30, 7072 / 30]
SUN = (440.0, 452.0)            # EB_dawn 缩到 1920 后的日心（画面坐标），半径 ≈250


class _Dawn:
    def dawn_init(self):
        self.pl = plate('EB_dawn')
        im = self.pl
        sunm = np.clip((im[..., 0] - np.maximum(im[..., 1], im[..., 2])) * 3, 0, 1).astype(np.float32)   # 红日 / 红云遮罩
        self.glow = cv2.GaussianBlur(sunm, (0, 0), 30)[..., None] * REDC * 0.35
        self.back = lay('EB_back')

    def sky(self, t, z, cx, cy, hits):
        k = beat_pulse(t, hits)
        fr = self.pl + self.glow * k                                                            # 鼓点：红日辉光呼吸
        return (fr if (z == 1.0 and cx == W / 2 and cy == H / 2) else view(fr, z, cx, cy)), k


def walker(fr, t, L, foot, h, rot=0.0, wind=6.0):
    """背影行走：按包围盒高度落脚；步伐起伏。"""
    a_, s_ = L.fit(h)
    return L.draw(fr, t, a_, foot, s_, rot=rot, breathe=0.004, wind_amp=wind, **KW)


def shadow(fr, fx, fy, L=90.0, lean=0.9, wmax=26, amt=0.7):
    """逆光长影朝镜头铺开（网点影）。"""
    yy, xx = E.grid()
    dy = (yy - fy) / L
    wv = 5 + wmax * np.clip(dy, 0, 1) ** 0.8
    sh = np.exp(-((xx - fx - lean * (yy - fy)) / wv) ** 2) * np.clip((dy + 0.02) / 0.02, 0, 1) * np.clip(1 - dy, 0, 1) ** 2.0
    sh = np.maximum(sh, np.exp(-(((xx - fx) / 26) ** 2 + ((yy - fy) / 5) ** 2)))
    sh = cv2.GaussianBlur(sh.astype(np.float32), (0, 0), 2.0)
    return fr * (1 - amt * np.maximum(sh, toned(sh, 1.0) * 0.6)[..., None])


def kick_dust(fr, t, hits, foot, seed, n=60, spread=260):
    """强拍：脚下 / 地平线扬起一排白尘 + 血红火星（0.5s 散）。"""
    for j, th in enumerate(hits):
        q = t - th + 1 / 30
        if q < 0 or q > 0.6: continue
        fr = K.sparks(fr, t, seed + j, foot, n=n, life=0.55, speed=(80, 360), dirc=(0.2, -1), spread=1.3, grav=260, burst=True, t0=th - 1 / 30,
                      area=(spread, 6), color=(0.85, 0.85, 0.85))
        fr = K.sparks(fr, t, seed + 50 + j, foot, n=n // 3, life=0.45, speed=(120, 420), dirc=(0.1, -1), spread=1.1, grav=300, burst=True, t0=th - 1 / 30,
                      area=(spread * 0.6, 6), color=(0.85, 0.03, 0.03))
        yy, xx = E.grid()
        r = 40 + 160 * eout(q / 0.4)
        puff = np.exp(-(((xx - foot[0]) / (r * 1.8)) ** 2 + ((yy - foot[1] + 0.3 * r) / (r * 0.45)) ** 2)) * math.exp(-q / 0.35) * 0.55
        fr = fr * (1 - puff[..., None]) + puff[..., None] * 0.9
    return fr


class E34(CreditsD, _Dawn):   # S136 ELS：晨雾山水、血红朝日在左，刀客小背影在右 1/3 向远方走去；强拍 7040 阶梯推镜 + 脚下扬尘，弱拍红日呼吸；署名④ 音乐（墨书）
    ccol = 'ink'
    fade = False                                                                                 # 同一署名延续到 E34L（这里不淡出）

    def __init__(self):
        self.blocks = [('音乐', ['西几王'], 1660, 260, 234.55, 0.5)]
        self.dawn_init()

    def render(self, t):
        u = self.u(t); tm = (self.t0 + self.t1) / 2
        z = step_zoom(t, [(7040 / 30, 0.025)]) * (1 + 0.004 * u)
        fr, k = self.sky(t, 1.0, 960, 540, HITS34)
        fr = mist(fr, t, 1366, 560, 760, 18, amt=0.30, t_ref=tm)
        fr = mist(fr, t, 1367, 700, 880, 34, amt=0.25, col=(0.85, 0.85, 0.85), scale=6, t_ref=tm)
        bob = 3 * abs(math.sin(t * 5.5))
        fx, fy = 1235 - 22 * u, 905
        fr = shadow(fr, fx, fy, L=80, lean=0.8, wmax=22, amt=0.55)
        fr, A = walker(fr, t, self.back, (fx, fy - bob), 230 - 12 * u)
        fr = kick_dust(fr, t, STRONG34[:1], (fx, fy), 7340, n=40, spread=140)
        fr = E.dust_motes(fr, t, 1381, n=40, amt=0.25, drift=(-18, -10), col=(0.9, 0.9, 0.9))
        return K.cam(fr, z, center=(fx, 640))


class E34L(CreditsD, _Dawn):   # S136L LS（7061 强拍硬切）：同一日出推近，人高 ≈560px；7072 再进一级 + 扬尘
    ccol = 'ink'

    def __init__(self):
        self.blocks = [('音乐', ['西几王'], 1660, 260, 234.55, 0.5)]
        self.dawn_init()

    def render(self, t):
        u = self.u(t); tm = (self.t0 + self.t1) / 2
        z = step_zoom(t, [(7072 / 30, 0.03)]) * (1 + 0.006 * u)
        fr, k = self.sky(t, 1.55, 760, 640, HITS34)
        fr = mist(fr, t, 1396, 520, 760, 26, amt=0.32, t_ref=tm)
        fr = mist(fr, t, 1397, 760, 960, 50, amt=0.28, col=(0.85, 0.85, 0.85), scale=6, t_ref=tm)
        bob = 4 * abs(math.sin(t * 5.5))
        fx, fy = 1250 - 30 * u, 985
        fr, A = walker(fr, t, self.back, (fx, fy - bob), 620, wind=7.0)
        fr = kick_dust(fr, t, STRONG34[1:], (fx, fy - 30), 7350, n=50, spread=220)
        fr = E.dust_motes(fr, t, 1394, n=50, amt=0.3, drift=(-22, -12), col=(0.9, 0.9, 0.9))
        return K.cam(fr, z, center=(fx, 600))


class E34b(CreditsD, _Dawn):   # S136b MS 背影上半身：红日在头侧，马尾与腰带随风（二级运动），白尘
    def __init__(self):
        self.blocks = []
        self.dawn_init()
        self.bgb = view(cv2.GaussianBlur(self.pl, (0, 0), 5), 1.7, 560, 500)

    def render(self, t):
        u = self.u(t)
        fr = view(self.bgb, 1.0, 960 + 30 * (u - 0.5), 540)
        s = 1.36
        fr, A = draw(fr, self.back, t, (1060, 620), (1010 - 20 * u, 1015 + 6 * abs(math.sin(t * 5.5))), s, breathe=0.004, wind_amp=10.0)
        return E.dust_motes(fr, t, 1385, n=50, amt=0.35, drift=(-20, -15), col=(0.9, 0.9, 0.9))


class E34c(CreditsD):   # S136c 插入：握鞘的手 + 血红穗（EB_grip），随步伐微摆
    def __init__(self):
        self.blocks = []
        self.L = lay('EB_grip')
        self.bg = view(plate('EB_dawn', blur=10), 1.4, 640, 420)

    def render(self, t):
        u = self.u(t)
        fr = view(self.bg, 1.0, 960 + 30 * (u - 0.5), 540)
        sw = math.sin(t * 5.5)
        fr, A = draw(fr, self.L, t, (1024, 576), (960 - 25 * u, 560 + 8 * sw), W / self.L.w * 1.06, rot=1.2 * sw, breathe=0, wind_amp=10.0)
        return E.dust_motes(fr, t, 1387, n=40, amt=0.3, drift=(-25, -10), col=(0.9, 0.9, 0.9))


class E34d(CreditsD, _Dawn):   # S136d 靴步：低机位贴地，落脚扬尘（白尘 + 血红火星）
    def __init__(self):
        self.blocks = []
        self.dawn_init()
        self.bgd = view(self.pl, 1.35, 700, 700)

    def render(self, t):
        u = self.u(t)
        fr = view(self.bgd, 1.0, 960 + 20 * (u - 0.5), 540)
        fr = shadow(fr, 980, 905, L=120, lean=0.6, wmax=60, amt=0.55)
        fr, A = draw(fr, self.back, t, (975, 1143), (980, 930 - 10 * u), 2.25 - 0.06 * u, breathe=0, wind_amp=8.0)
        q = t - self.t0
        fr = kick_dust(fr, t, [self.t0 + 1 / 30], (1000, 905), 1390, n=50, spread=150)
        return fr


HITS35 = [7133 / 30, 7143 / 30, 7160 / 30, 7167 / 30]


class E35(Shot):   # S137 ECU 收刀「咔」（EB_sheath）：刀滑入鞘口、7153 最强拍硬停 + 鞘口白闪火星；7157 起「鬼屠」血红印盖在画面中心；背后血红日轮虚焦
    def __init__(self):
        self.L = lay('EB_sheath')
        self.bg = view(plate('EB_dawn', blur=9, gain=0.85), 2.2, 520, 470)
        self.tc = 7153 / 30

    def scene(self, t):
        a = t - self.t0
        fr = view(self.bg, 1.0, 900 + 0.0 * a, 540)
        slide = 0 if t >= self.tc else 80 * (1 - eio((t - self.t0) / (self.tc - self.t0)))
        s = 1.42
        dst = (960 - slide, 640)
        dim = 0.55 if t >= self.tc + 0.4 else (1.0 - 0.45 * c01((t - self.tc) / 0.4) if t >= self.tc else 1.0)
        z, A = draw(np.zeros_like(fr), self.L, t, (1050, 790), dst, s, breathe=0, wind_amp=4.0)
        fr = fr * (1 - A[..., None]) + z * dim
        mouth = to_scr(self.L, (1050, 790), dst, s, (1270, 790))
        if t < self.tc:                                                                         # 刀身寒光推向鞘口
            g0 = to_scr(self.L, (1050, 790), dst, s, (780, 790))
            k = eio(c01((t - self.t0) / (self.tc - self.t0)))
            px = g0[0] + (mouth[0] - g0[0]) * k
            yy, xx = E.grid()
            bl = np.exp(-((xx - px) / 60) ** 2 - ((yy - mouth[1]) / 26) ** 2) * A
            fr = fr + bl[..., None] * 0.9
        return fr, mouth

    def render(self, t):
        fr, mouth = self.scene(t)
        if t >= self.tc:
            q = t - self.tc
            fr = E.flare_streak(fr, mouth, amt=1.2 * math.exp(-q / 0.12), length=0.7, col=(1.0, 1.0, 1.0))
            fr = spark2(fr, t, 1391, mouth, self.tc, n=50, life=0.6, speed=(200, 700), dirc=(0, -1), spread=1.6, grav=900)
            p = c01((q - 0.13) / 0.35)
            if p > 0: fr = T.stamp_seal(fr, '鬼屠', 960, 470, 260, p, style='yin', rot=-4, seed=21, color=tuple(REDC))
        for th in HITS35:
            if t >= th: fr = fr * (1 + 0.12 * math.exp(-(t - th) / 0.08))
        return fr

    def text(self, fr, t): return fr


class E36(Shot):   # S138 墨从四角收拢，只剩中心一点血红 → 黑（干净落版）；起幅 = 本模块 E35 的末帧
    def __init__(self):
        self.src = None

    def render(self, t):
        if self.src is None:                                                                    # 起幅 = E35 末帧（含 MOVE 运镜与抖动，经 _Sec.full）
            i = M.IDS.index('E35')
            self.src = np.clip(_SEC.full(i, M.BOUNDS[i + 1] / FPS - 1 / FPS), 0, 4).astype(np.float32)
        p = c01((t - self.t0) / 0.9)
        if p < 1:
            return TR.transition('iris_moon', self.src, np.zeros_like(self.src), p, mode='collapse', center=(960, 470), dot_color=REDC)
        q = t - (self.t0 + 0.9); end = c01((t - (self.t1 - 0.3)) / 0.3)
        yy, xx = E.grid()
        d = np.hypot(xx - 960, yy - 470)
        r = 9 * (1 + 0.45 * math.sin(math.pi * c01(q / 0.5)) ** 2) * (1 - end)
        dot = np.clip(r + 0.8 - d, 0, 1)
        R = 30 + 260 * eout(q / 1.0)
        n = cv2.resize(K.fbm(H // 4, W // 4, 1381, base=6, octaves=4), (W, H))
        ink = np.exp(-((d - R * 0.55) / (R * 0.45)) ** 2) * math.exp(-q / 0.6) * 0.18 * (1 - end) * (0.6 + 0.8 * n)
        return ink[..., None] * REDC * 0.6 + dot[..., None] * REDC * 1.1

    def text(self, fr, t): return fr


# ================================================================== 挂载
class _SecRef:
    """E36 取 E35 末帧要走 _Sec.full（含运镜/抖动）：用一个独立 _Sec 实例，不碰渲染中的缓存。"""
    def full(self, i, t):
        if not hasattr(self, 's'): self.s = M._Sec()
        return self.s.full(i, t)


_SEC = _SecRef()


NEW = dict(E27a=E27a, E27b=E27b, E27c=E27c, E28=E28, E29=E29, E30=E30, E31=E31, E32=E32, E33=E33,
           E34=E34, E34L=E34L, E34b=E34b, E34c=E34c, E34d=E34d, E35=E35, E36=E36)
F_LO = 6638


def apply(mod):
    global M
    M = mod
    if getattr(M, '_r8d_e_b_applied', False): return
    M._r8d_e_b_applied = True
    shots = [((NEW[c.__name__] if (f >= F_LO and c.__name__ in NEW) else c), f, a, b) for (c, f, a, b) in M.SHOTS]
    missing = set(NEW) - {c.__name__ for (c, f, a, b) in M.SHOTS if f >= F_LO}
    if missing: raise RuntimeError('r8d_e_b: SHOTS 里找不到 %s（e_r9 镜头表变了？）' % sorted(missing))
    M.SHOTS[:] = shots
    M.IDS[:] = [s[0].__name__ for s in shots]
    M.BOUNDS[:] = [s[1] for s in shots] + [M.F1]
    for nm, c in NEW.items(): setattr(M, nm, c)
    # 风格 D 无金：E27b 入点冲击闪由白金改纯白（E27a/E28 的血红闪保留）
    M.CUTS['E27b'] = ('cut', 0, 0, {})                                                     # 镜内自带两帧反白冲击（现版 impact 的闪会把剪影冲灰）
    M.SHAKE['E27b'] = [(6658 / 30, 14)]
    # 风格 D 无金：入转场的暖金烟 / 暖刃口改中性白灰（墨烟），金色不再依赖全局兜底去色
    M.CUTS['E29'] = ('ink_bleed', 0.18, 0.18, dict(center=(1000, 500), seed=9, white=False))       # 墨晕吞屏（暗底设计）→ 墨在宣纸上洇开（同时长、同中心）
    M.CUTS['E32'] = ('blade_sweep', 0.12, 0.16, dict(direction=1, warm=(1.0, 1.0, 1.0)))
    M.CUTS['E33'] = ('warm_veil', 0.14, 0.20, dict(axis='x', direction=-1, seed=7301, cap=0.66, warm=(0.96, 0.96, 0.96), dark=(0.06, 0.06, 0.06)))
    M.CUTS['E34'] = ('warm_veil', 0.20, 0.30, dict(axis='y', seed=7341, cap=0.62, warm=(0.96, 0.96, 0.96), dark=(0.10, 0.10, 0.10)))
