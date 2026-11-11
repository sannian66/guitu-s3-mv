"""units/r8d_a2.py — 第八轮风格 D · A2 单元（主歌一后半 V08–V21，帧 703–1321）
只在 STYLE_D=1 时由 sec_a_intro_verse1.py 末尾的钩子加载：apply(mod) 把 mod.SHOTS 里 V08–V21 换成本文件的 *D 类，
并只改这些镜头自己的 CUTS / FG / EXPO / INNER 项；STYLE_D=0 时本文件不被 import，现版逐像素不变。
切点（CUT_F）、镜长、字幕时刻全部沿用现版；素材 = assets/gen/R8_D/A2/（nananobanana RH_image2，提示词 jobs/r8_D_A2.json）。
画面里不出任何字（本单元没有点名保留的字）：罪状 / 杀放 / 刀身刻字 / 我的主张 / 正 / 锋芒 全部去掉，屏幕层横排歌词 LY2 在本段也不画。
各层位移以镜头中点为零；人物按包围盒高度落脚（SpriteLayer.fit）；精灵一律 grade=NEU、rim=NORIM、wrap=0、shade=None。"""
import math, os
import numpy as np, cv2

NAMES = ('V08', 'V09', 'V10', 'V11', 'V12', 'V13', 'V14', 'V15', 'V16', 'V17', 'V18', 'V19', 'V20', 'V21')
NEU = dict(expo=1.0, sat=1.0, tint=(1.0, 1.0, 1.0), lift=0.0, gamma=1.0)
NORIM = dict(col=(1.0, 1.0, 1.0), amt=0.0, dir=(0.0, -1.0))
WHITE = np.array([1.0, 1.0, 1.0], np.float32)
BLOOD = np.array([0.80, 0.03, 0.03], np.float32)
INKC = np.array([0.012, 0.012, 0.012], np.float32)


# =====================================================================================
# 公共小工具
_L, _P = {}, {}
def lay(name):
    p = GEN + name + '_cut.png'
    if p not in _L: _L[p] = SP.layer(p)
    return _L[p]


def plate(name, scale=1.0):
    k = (name, scale)
    if k not in _P:
        im = cv2.cvtColor(cv2.imread(GEN + name + '.png'), cv2.COLOR_BGR2RGB)
        _P[k] = cv2.resize(im, (int(W * scale), int(H * scale)), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    return _P[k]


def bgview(name, scale=1.1, dx=0.0, dy=0.0, z=1.0, rot=0.0, pivot=(0.5, 0.5), at=None, blur=0.0):
    """背景板：按 scale 预放大（留视差余量），板内 pivot 点（归一化）落到屏幕 at（默认画面中心 + (dx,dy)），绕该点缩放 z / 旋转 rot。"""
    im = plate(name, scale)
    h, w = im.shape[:2]
    px, py = pivot[0] * w, pivot[1] * h
    ax, ay = at if at else (W / 2 + (px - w / 2), H / 2 + (py - h / 2))
    M = cv2.getRotationMatrix2D((px, py), rot, z)
    M[0, 2] += ax + dx - px; M[1, 2] += ay + dy - py
    out = cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return cv2.GaussianBlur(out, (0, 0), blur) if blur > 0.3 else out


def brighten(fr, k):
    """背景板提亮：暗部抬起（白纸感），亮部不爆；k 0..1"""
    return 1 - (1 - np.clip(fr, 0, 1)) ** (1 + 1.4 * k) if k > 0 else fr


def sput(fr, t, name, a_src, dst, s, **kw):
    k = dict(grade=NEU, rim=NORIM, wrap=0, shade=None, breathe=0, wind_amp=0)
    k.update(kw)
    return lay(name).draw(fr, t, a_src, dst, s, **k)


def sfit(fr, t, name, h, foot, **kw):
    """按包围盒高度落脚（脚底中点 → foot）；人物默认带呼吸"""
    a, s = lay(name).fit(h)
    kw.setdefault('breathe', 0.004)
    return sput(fr, t, name, a, foot, s, **kw)


def spt(name, a_src, dst, s, p, rot=0.0):
    """精灵内归一化点 p 在屏幕上的位置（与 draw 同一仿射）"""
    sp = lay(name)
    ax, ay = a_src[0] * sp.w, a_src[1] * sp.h
    M = cv2.getRotationMatrix2D((ax, ay), rot, s)
    M[0, 2] += dst[0] - ax; M[1, 2] += dst[1] - ay
    x, y = p[0] * sp.w, p[1] * sp.h
    return (float(M[0, 0] * x + M[0, 1] * y + M[0, 2]), float(M[1, 0] * x + M[1, 1] * y + M[1, 2]))


_LOW = {}
def lowest(name):
    """alpha 最低点（刀尖 / 脚）的归一化坐标（缓存）"""
    if name in _LOW: return _LOW[name]
    sp = lay(name)
    ys, xs = np.nonzero(sp.A > 0.5)
    i = int(np.argmax(ys))
    _LOW[name] = (xs[i] / sp.w, ys[i] / sp.h)
    return _LOW[name]


_TX = {}
def texr(seed, n, base, oct_):
    """A.tex 放大到全画幅（缓存）"""
    k = (seed, n, base, oct_)
    if k not in _TX: _TX[k] = cv2.resize(A.tex(seed, n, base, oct_), (W, H))
    return _TX[k]


_INZ = []
def INKNZ():
    if not _INZ: _INZ.append(cv2.resize(A.ink_noise(5, 256), (W // 2, H // 2)))
    return _INZ[0]


def over(fr, a, col):
    a = a[..., None] if a.ndim == 2 else a
    return fr * (1 - a) + np.asarray(col, np.float32) * a


def flash(fr, amt):
    return fr * (1 + 0.6 * amt) + 0.25 * amt if amt > 0.01 else fr


def invert_frame(fr, subj=None):
    """反白冲击帧：黑白反转，主体纯黑剪影"""
    lum = fr.mean(-1)
    inv = np.clip(1.10 - lum * 1.1, 0, 1) ** 1.3
    out = np.repeat(inv[..., None], 3, -1)
    if subj is not None: out = out * (1 - subj[..., None]) + 0.02 * subj[..., None]
    return out


def focus_lines(fr, c, amt, seed, r0=380, n=110, col=0.0, wmax=16):
    """漫画集中线：从画外指向 c 的黑（或白）楔形线"""
    if amt <= 0.01: return fr
    rr = np.random.default_rng(seed)
    L = np.zeros((H // 2, W // 2), np.float32)
    for _ in range(n):
        a = rr.uniform(0, 2 * math.pi); rin = r0 * rr.uniform(0.9, 1.8)
        ca, sa = math.cos(a), math.sin(a); wd = rr.uniform(3, wmax)
        p0 = (c[0] + ca * rin, c[1] + sa * rin); p1 = (c[0] + ca * 2600, c[1] + sa * 2600)
        pts = np.array([p0, (p1[0] - sa * wd, p1[1] + ca * wd), (p1[0] + sa * wd, p1[1] - ca * wd)]) / 2
        cv2.fillConvexPoly(L, (pts * 4).astype(np.int32), float(rr.uniform(0.6, 1.0)), cv2.LINE_AA, 2)
    L = cv2.resize(L, (W, H))[..., None] * amt
    return fr * (1 - L) + L * col


def speed_lines(fr, t, seed, ang, amt, n=70, y0=140, y1=940):
    """平行速度线（黑 + 白），ang 方向（度）"""
    if amt <= 0.01: return fr
    r = np.random.default_rng(seed + int(round(t * 30)))
    Lk = np.zeros((H // 2, W // 2), np.float32); Lw = np.zeros_like(Lk)
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    for i in range(n):
        x = r.uniform(-200, W + 200); y = r.uniform(y0, y1); ln = r.uniform(160, 640)
        tgt = Lk if i % 3 else Lw
        cv2.line(tgt, (int(x / 2), int(y / 2)), (int((x + ca * ln) / 2), int((y + sa * ln) / 2)), float(r.uniform(0.4, 1.0)), 1 if i % 4 else 2, cv2.LINE_AA)
    Lk = cv2.resize(Lk, (W, H)); Lw = cv2.resize(Lw, (W, H))
    fr = fr * (1 - np.clip(Lk * 0.8 * amt, 0, 1))[..., None]
    return fr + (Lw * 0.8 * amt)[..., None]


_BR = {}
def brush(fr, pts, width, prog, fade, seed, core=WHITE, edge=BLOOD, ink=True):
    """干笔飞白刀痕：pts 屏幕折线（起 → 止），两端收尖、中段最粗；26 根笔毛，靠边和靠尾断丝（飞白）；
    白芯 + 血红外缘 + 沿笔路的溅墨点。prog 0→1 画出，fade 1→0 退。"""
    if prog <= 0 or fade <= 0.01: return fr
    P = np.asarray(pts, np.float32); n = len(P)
    key = (seed, n)
    if key not in _BR:
        r = np.random.default_rng(seed)
        nb = 28
        br = []
        for b in range(nb):
            off = (b / (nb - 1) - 0.5) * 2
            nz = np.convolve(r.random(n + 10), np.ones(11) / 11, 'valid')[:n]
            br.append((off, float(r.uniform(0.55, 1.0)), nz))
        spl = [(float(r.uniform(0.05, 0.95)), float(r.normal(0, 1.2)), float(r.uniform(2, 9))) for _ in range(46)]
        _BR[key] = (br, spl)
    br, spl = _BR[key]
    d = np.gradient(P, axis=0); d /= (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
    nrm = np.stack([-d[:, 1], d[:, 0]], 1)
    s = np.linspace(0, 1, n)
    prof = np.clip(np.sin(np.pi * s) ** 0.55, 0.04, 1)
    m = int(max(2, min(n, round(prog * n))))
    q = 2
    body = np.zeros((H // q, W // q), np.float32)
    for off, val, nz in br:
        Q = (P + nrm * (off * width / 2 * prof)[:, None]) / q
        thr = 0.30 + 0.22 * abs(off) ** 2 + 0.25 * s
        th = max(1, int(round(width / q / len(br) * 2.2)))
        for i in range(m - 1):
            if nz[i] < thr[i]: continue
            cv2.line(body, (int(Q[i, 0] * 4), int(Q[i, 1] * 4)), (int(Q[i + 1, 0] * 4), int(Q[i + 1, 1] * 4)), val, th, cv2.LINE_AA, 2)
    body = cv2.resize(cv2.GaussianBlur(body, (0, 0), 0.6), (W, H))
    cl = np.zeros((H // q, W // q), np.float32)
    C = P[:m] / q
    for i in range(m - 1):
        cv2.line(cl, (int(C[i, 0] * 4), int(C[i, 1] * 4)), (int(C[i + 1, 0] * 4), int(C[i + 1, 1] * 4)), 1.0,
                 max(1, int(width * 0.12 * prof[i] / q)), cv2.LINE_AA, 2)
    cl = cv2.resize(cv2.GaussianBlur(cl, (0, 0), 1.0), (W, H))
    halo = np.clip(K.blur_ds(body, 14) * 1.6 - body, 0, 1)
    fr = over(fr, np.clip(body * 0.95 * fade, 0, 1), edge)
    fr = fr + halo[..., None] * edge * 0.6 * fade
    fr = over(fr, np.clip(cl * fade, 0, 1), core)
    fr = fr + K.blur_ds(cl, 10)[..., None] * 0.5 * fade
    if ink:
        Ls = np.zeros((H // q, W // q), np.float32)
        for (u, o, rad) in spl:
            if u > prog: continue
            i = int(u * (n - 1)); p = P[i] + nrm[i] * o * width * 0.6
            cv2.circle(Ls, (int(p[0] / q * 4), int(p[1] / q * 4)), int(rad / q * 4), 1.0, -1, cv2.LINE_AA, 2)
        fr = over(fr, cv2.resize(Ls, (W, H)) * fade, INKC)
    return fr


def star(fr, p, g, size=1.0, rot=0.0):
    """墨线星芒（替代柔光十字 pupil_glint，SPREAD §11-2）：硬边白色四角星 + 细墨线勾边 + 两根细长白刺，g 0..1 控制大小与不透明"""
    if g <= 0.02: return fr
    q = 2; L = np.zeros((H // q, W // q), np.float32); K_ = np.zeros_like(L)
    r1 = 46 * size * (0.4 + 0.6 * g); r0 = r1 * 0.16
    pts = []
    for i in range(8):
        a = math.radians(rot + 45 * i); r = r1 * (1.0 if i % 4 == 0 else (0.62 if i % 2 == 0 else r0 / r1))
        pts.append((p[0] + math.cos(a) * r, p[1] + math.sin(a) * r))
    P = (np.array(pts) / q * 4).astype(np.int32)
    cv2.fillPoly(K_, [P], 1.0, cv2.LINE_AA, 2); cv2.polylines(K_, [P], True, 1.0, 3, cv2.LINE_AA, 2)
    cv2.fillPoly(L, [P], 1.0, cv2.LINE_AA, 2)
    for a in (rot, rot + 180):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        cv2.line(L, (int(p[0] / q * 4), int(p[1] / q * 4)), (int((p[0] + ca * r1 * 3.2) / q * 4), int((p[1] + sa * r1 * 3.2) / q * 4)), 1.0, 1, cv2.LINE_AA, 2)
    ink = np.clip(cv2.resize(K_, (W, H)) - cv2.resize(cv2.erode(L, np.ones((3, 3), np.uint8)), (W, H)), 0, 1)
    al = min(1.0, 1.3 * g)
    fr = over(fr, ink * al, INKC)
    return over(fr, cv2.resize(L, (W, H)) * al, WHITE)


def bez(p0, p1, p2, n=60):
    s = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = (np.asarray(p, np.float32) for p in (p0, p1, p2))
    return (1 - s) ** 2 * p0 + 2 * (1 - s) * s * p1 + s * s * p2


_CR = {}
def ink_cracks(origin, n, length, prog, width=3, seed=0):
    """自 origin 向外的墨裂缝 alpha（带分叉）；按 (origin, prog 取 3 位) 缓存"""
    key = (round(origin[0], 1), round(origin[1], 1), n, length, round(prog, 3), width, seed)
    if key in _CR: return _CR[key]
    if len(_CR) > 4: _CR.clear()                                       # 每帧 prog 不同，只留最近几张（单张 8 MB）
    r = np.random.default_rng(seed)
    m = np.zeros((H, W), np.float32)
    for i in range(n):
        a = 2 * math.pi * (i + r.uniform(-0.3, 0.3)) / n
        L = length * r.uniform(0.55, 1.1)
        p1 = (origin[0] + math.cos(a) * L, origin[1] + math.sin(a) * L * 0.42)
        pts = K.crack_path(origin, p1, seed * 31 + i, n=30, jag=0.06)
        m = np.maximum(m, K.draw_crack((H, W), pts, width * r.uniform(0.7, 1.3), branches=4, seed=seed + i, prog=prog))
    _CR[key] = m
    return m


_PB = {}
def paper_bg(seed, red=None):
    """风格 D 白纸底：纸纹 + 网点渐变（四角压灰）+ 可选一块干笔边血红墨块 red=(cx, cy, r)"""
    k = (seed, red)
    if k not in _PB:
        nz = cv2.resize(A.tex(seed, 256, 6, 5), (W, H)); fine = cv2.resize(A.tex(seed + 1, 512, 40, 3), (W, H))
        x, y = K.grid()
        v = np.clip(np.hypot((x - 960) / 1100, (y - 540) / 700), 0, 1)
        dots = ((np.sin(x * 0.42) * np.sin(y * 0.42)) > 1 - 1.6 * v ** 2).astype(np.float32)
        fr = (0.93 - 0.06 * fine - 0.08 * v)[..., None] * np.ones(3, np.float32)
        fr = fr * (1 - 0.55 * dots[..., None])
        if red:
            cx, cy, r = red
            d = np.hypot(x - cx, y - cy) + (nz - 0.5) * r * 0.35
            core = np.clip((r - d) / 4, 0, 1)
            rim = np.clip((r - d) / 70, 0, 1)                                       # 外沿 70px 干笔飞白
            m = core * np.where(rim < 1, np.clip((fine - 0.55 + 0.6 * rim) * 6, 0, 1), 1.0)
            fr = over(fr, m, BLOOD)
        _PB[k] = fr.astype(np.float32)
    return _PB[k].copy()


class DShot:
    t0 = t1 = 0.0
    def u(self, t): return clamp01((t - self.t0) / (self.t1 - self.t0))
    def mid(self): return 0.5 * (self.t0 + self.t1)


# =====================================================================================
# V08 23.43–25.27「谁在高处定对错罪状」——太上皇的手把玉玺压下（侧面桌高机位）→ 24.48「罪」落印 → 俯拍宣纸上的朱印
#   去掉「罪状」印文和右侧乱码诏文：印面换成生图里只有盘龙云纹、没有字的朱印（A2_v08_imprint）。
#   层：殿内背景板 A2_v08_bg（视差 0.4）/ 桌面宣纸带（A2_v08_paper 压扁）/ 手 + 袖 + 玉玺 A2_v08_hand（纱袖风动）/ 玺影 /
#       落印：集中线 + 白闪 + 纸尘（白）+ 印泥飞点（血红）+ 震屏；俯拍：宣纸背景板 A2_v08_paper / 朱印 A2_v08_imprint / 玺影抬离 / 纸尘
class V08D(DShot):
    def __init__(self):
        self.pap = cv2.resize(plate('A2_v08_paper', 1.0)[300:800, 200:1700], (W, 110), interpolation=cv2.INTER_AREA)

    def render(self, t):
        th = CT(2, 7); tsw = th + 0.10
        if t < tsw: return self.side(t, th)
        return self.top(t, th, tsw)

    def side(self, t, th):
        u = self.u(t); e = eio(u); a = t - th
        fr = bgview('A2_v08_bg', 1.12, dx=-50 * (e - 0.5))
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        band = np.clip((yy - 868) / 4, 0, 1)
        pap = np.zeros_like(fr); pap[870:980] = self.pap[:110]
        fr = fr * (1 - band) + pap * band * (0.85 + 0.25 * np.clip((yy - 868) / 90, 0, 1))
        q = clamp01((t - self.t0) / (th - self.t0))
        drop = 120 * (1 - ein(q, 1.8)) if a < 0 else -6 * math.exp(-a / 0.05)
        trem = 1.5 * math.sin(t * 37) * (a < 0)
        # 玺影：离纸越近越实
        sh = np.zeros((H // 2, W // 2), np.float32)
        sw_ = 320 + 240 * (1 - q)
        cv2.ellipse(sh, (int((975 - 40 * (1 - q)) / 2), 442), (int(sw_ / 2), int(7 + 6 * (1 - q))), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        sh = cv2.resize(cv2.GaussianBlur(sh, (0, 0), 3 + 16 * (1 - q)), (W, H))[..., None] * band
        fr = fr * (1 - (0.35 + 0.55 * q) * sh)
        fr, Am = sput(fr, t, 'A2_v08_hand', (0.52, 0.95), (975 + trem, 882 - drop), 1.03, wind_amp=3.0)     # 画布左缘 x≈-50（出画）
        # 桌前沿压住袖摆
        edge = np.clip((yy - 930) / 4, 0, 1)
        fr = fr * (1 - edge) + edge * 0.015
        fr = fr + np.exp(-((yy - 870) / 1.5) ** 2) * 0.35
        if a >= 0:
            k = math.exp(-a / 0.05)
            fr = focus_lines(fr, (975, 870), 0.9 * (a < 0.067), 801 + int(a * 30), r0=420)
            fr = flash(fr, 0.8 * k)
            fr = K.sparks(fr, t, 81, (975, 878), n=70, life=0.45, speed=(150, 560), dirc=(0, -1), spread=2.6, grav=900,
                          area=(260, 6), amt=0.7, t0=th, burst=True, color=(0.95, 0.95, 0.95))
            fr = K.sparks(fr, t, 82, (975, 880), n=26, life=0.4, speed=(220, 700), dirc=(0, -1), spread=2.0, grav=1400,
                          area=(240, 4), amt=1.0, t0=th, burst=True, color=tuple(BLOOD))
        dx, dy, dr = K.shake(t, 1.5 + (12 * math.exp(-a / 0.08) if a >= 0 else 0), 14, 808)
        return K.cam(fr, 1.0, dx, dy, dr), (3 if 0 <= a < 0.07 else 0)

    def top(self, t, th, tsw):
        k = t - tsw; a2 = t - CT(2, 8)
        fr = bgview('A2_v08_paper', 1.10, z=1.0 + 0.04 * eio(k / 0.7))
        # 朱印：玺抬起时露出，「状」字拍印泥洇开一圈
        bleed = eout(clamp01(a2 / 0.3)) if a2 >= 0 else 0.0
        P0 = np.zeros_like(fr)
        P, Ai = sput(P0, t, 'A2_v08_imprint', (0.5, 0.5), (820, 560), 0.62 * (1 + 0.01 * bleed), rot=-3.0)
        Ai = np.clip(Ai, 0, 1)
        halo = np.clip(K.blur_ds(Ai, 6 + 10 * bleed) - Ai, 0, 1) * (0.25 + 0.35 * bleed)
        fr = fr * (1 - Ai[..., None]) + P
        fr = over(fr, halo, BLOOD * 0.9)
        # 玺影：抬起变大变虚，向右上滑出
        e = eout(clamp01(k / 0.55))
        sh = np.zeros((H // 2, W // 2), np.float32)
        c = (820 + 520 * e - 40, 560 - 300 * e + 50); hs = 200 + 150 * e
        cv2.rectangle(sh, (int((c[0] - hs) / 2), int((c[1] - hs) / 2)), (int((c[0] + hs) / 2), int((c[1] + hs) / 2)), 1.0, -1)
        sh = cv2.resize(cv2.GaussianBlur(sh, (0, 0), 6 + 40 * e), (W, H))[..., None]
        fr = fr * (1 - 0.6 * (1 - e) * sh)
        fr = K.sparks(fr, t, 83, (820, 560), n=30, life=0.6, speed=(40, 180), dirc=(0.4, -1), spread=2.0, grav=-40,
                      area=(200, 200), amt=0.45, t0=tsw - 0.02, burst=True, color=(0.9, 0.9, 0.9))
        if a2 >= 0:
            fr = K.sparks(fr, t, 84, (820, 560), n=24, life=0.35, speed=(200, 600), dirc=(1, 0), spread=3.0, grav=0,
                          area=(240, 240), amt=0.9, t0=CT(2, 8), burst=True, color=tuple(BLOOD))
        return fr, (2 if k < 0.06 else 0)


# =====================================================================================
# V09 25.27–27.07「谁把人命装进天平」——暗殿里的青铜天平：左盘纸人丘，右盘玉玺；唱到「装进」纸人从上方落进左盘，
#   「命」字拍玉玺一侧猛沉（横梁阻尼余摆）+ 白火星 + 震屏。横梁按支点剪切（R8.shear_beam），立柱不动。
#   层：殿堂背景板 A2_v09_bg（视差 0.45）/ 天平 A2_v09_scale（梁剪切 + 地面倒影）/ 落入的纸人 A2_v10_fall / 白火星 / 雾
class V09D(DShot):
    FOOT, HGT = (960.0, 935.0), 800.0
    PIV = (0.50, 0.195)
    PANL, PANR = (0.244, 0.74), (0.756, 0.80)

    def render(self, t):
        u = self.u(t); e = eio(u)
        par = e - 0.5
        fr = brighten(bgview('A2_v09_bg', 1.14, dx=-70 * par), 0.55)
        a_, s_ = lay('A2_v09_scale').fit(self.HGT)
        fx, fy = self.FOOT
        dst = (fx + 18 * par, fy)
        P, Al = sput(np.zeros_like(fr), t, 'A2_v09_scale', a_, dst, s_)
        piv = spt('A2_v09_scale', a_, dst, s_, self.PIV)
        half = float((self.PANR[0] - self.PIV[0]) * lay('A2_v09_scale').w * s_)
        tm = CT(3, 3); a = t - tm
        sl = -0.012 + 0.010 * math.sin(t * 4.2)
        if a >= 0: sl += 0.085 * (1 - math.exp(-a / 0.07)) + 0.030 * math.exp(-a / 0.28) * math.sin(a * 26)
        P, Al = R8.shear_beam(P, Al[..., None], piv, float(sl), piv[1] + 60, float(sl * half), col_half=60, fade=160)
        P, Al = np.nan_to_num(P), np.nan_to_num(Al)                                # shear_beam 的 remap 出界处是 NaN
        # 地面倒影（磨光金砖 → 黑石）
        y0 = int(fy)
        Rf = cv2.flip(P[y0 - 120:y0], 0); Ra = cv2.flip(Al[y0 - 120:y0, :, 0], 0)[..., None]
        hh = min(80, H - y0)
        g = np.linspace(0.30, 0.0, hh, dtype=np.float32)[:, None, None]
        fr[y0:y0 + hh] = fr[y0:y0 + hh] * (1 - Ra[:hh] * g) + cv2.GaussianBlur(Rf[:hh], (0, 0), 3) * g
        fr = fr * (1 - Al) + P
        # 「装进」：纸人自上方落入左盘
        pl = spt('A2_v09_scale', a_, dst, s_, self.PANL)
        pl = (pl[0], pl[1] - sl * half)
        tz = CT(3, 4) - 0.30
        if tz <= t:
            q = clamp01((t - tz) / 0.55)
            y = -60 + (pl[1] - 120 + 60) * q ** 1.6 + 40 * eout(clamp01((t - tz - 0.55) / 0.3))   # 落定后陷进纸人堆（被盘沿裁掉）
            Pf, Af = sput(np.zeros_like(fr), t, 'A2_v10_fall', (0.5, 0.5), (pl[0], y), 0.20, rot=40 * q)
            clip = np.clip((pl[1] - 70 - np.arange(H, dtype=np.float32)[:, None]) / 12, 0, 1)
            fr = fr * (1 - (Af * clip)[..., None]) + Pf * clip[..., None]
        if a >= 0:
            pr = spt('A2_v09_scale', a_, dst, s_, self.PANR)
            fr = K.sparks(fr, t, 91, (pr[0], pr[1] + sl * half), n=60, life=0.5, speed=(200, 700), dirc=(0, -1), spread=1.6, grav=1200,
                          area=(160, 10), amt=0.9, t0=tm, burst=True, color=(1.0, 1.0, 1.0))
            fr = flash(fr, 0.35 * math.exp(-a / 0.06))
        fr = fog(fr, t, 1, 700, 900, 0.14, (0.25, 0.25, 0.25), speed=(-30, 0))
        dx, dy, dr = K.shake(t, 10 * K.pulse(t, tm, 0.10) * (a >= 0), 15, 909)
        return K.cam(fr, 1.0, dx, dy, dr), (2 if 0 <= a < 0.07 else 0)


# =====================================================================================
# V10 27.10–28.93「里 称量」——低机位仰看那只秤盘：纸人堆在盘里，盘在链上摆；「里」字拍盘一沉、纸人从盘沿成串翻落，
#   28.10 一滴血从链上落到盘沿溅开，「称」「量」两拍盘猛摆 + 第二波纸人贴镜头落下（虚焦前景）。
#   层：白纸网点底 + 血红墨块 + 竖速度线 / 秤盘 A2_v10_pan（绕链顶摆动）/ 落纸人 A2_v10_fall ×2（中景 + 贴镜头前景，动态模糊）/ 血滴 / 火星
class V10D(DShot):
    def swing(self, t):
        tl = CT(3, 8); a = t - tl
        r = 2.2 * math.sin(t * 2.6)
        drop = 0.0
        if a >= 0:
            drop = 26 * (1 - math.exp(-a / 0.06)) * math.exp(-a / 0.9)
            r += 3.0 * math.exp(-a / 0.35) * math.sin(a * 14)
        for k in (9, 10):
            b = t - CT(3, k)
            if b >= 0: r += 4.0 * math.exp(-b / 0.30) * math.sin(b * 16)
        return r, drop

    def render(self, t):
        u = self.u(t); e = eio(u)
        fr = paper_bg(1001, red=(1500, 260, 420))
        fr = speed_lines(fr, t, 1003, 90, 0.35, n=40)
        rot, drop = self.swing(t)
        s = W / lay('A2_v10_pan').w * 0.92
        top = (960 + 20 * (e - 0.5), -10 + drop)                  # 链顶画布边：最大摆角 ≈9° 时 y<100（藏在上黑边里）
        tl = CT(3, 8)
        # 中景落纸人（「里」起）：自盘沿翻落
        a1 = t - (tl - 0.04)
        fr, Ap = sput(fr, t, 'A2_v10_pan', (0.5, 0.0), top, s, rot=rot, wind_amp=2.0)
        rim = spt('A2_v10_pan', (0.5, 0.0), top, s, (0.5, 0.62), rot)
        if a1 >= 0:
            y = rim[1] - 40 + 0.5 * 1500 * a1 * a1 + 120 * a1
            al = clamp01(1 - (a1 - 0.6) / 0.4)
            fr, _ = sput(fr, t, 'A2_v10_fall', (0.5, 0.5), (rim[0] + 40, y), 0.95, rot=-25 * a1, alpha=al)
            fr = K.sparks(fr, t, 101, rim, n=50, life=0.5, speed=(100, 400), dirc=(0, 1), spread=1.4, grav=800,
                          area=(600, 10), amt=0.6, t0=tl, burst=True, color=(0.95, 0.95, 0.95))
        # 血滴：自右链落下，28.10 打在盘沿
        td = V(28.10)
        rx = rim[0] + 330
        ry = rim[1] + 30 + math.tan(math.radians(-rot)) * 330
        if t < td:
            q = clamp01((t - (td - 0.45)) / 0.45)
            yd = 140 + (ry - 140) * q ** 2
            Ld = np.zeros((H, W), np.float32)
            cv2.ellipse(Ld, (int(rx), int(yd)), (9, int(12 + 10 * q)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
            ink = np.clip(cv2.dilate(Ld, np.ones((5, 5), np.uint8)) - Ld, 0, 1)
            fr = over(fr, ink, INKC); fr = over(fr, Ld, BLOOD)
        else:
            a = t - td
            fr = K.sparks(fr, t, 102, (rx, ry), n=60, life=0.5, speed=(150, 650), dirc=(0, -1), spread=1.5, grav=1500,
                          area=(30, 6), amt=1.1, t0=td, burst=True, color=tuple(BLOOD))
            fr = flash(fr, 0.25 * math.exp(-a / 0.05))
        # 「称」「量」：第二波纸人贴镜头落下（前景，视差大）
        a2 = t - (CT(3, 9) - 0.06)
        if a2 >= 0:
            y = -250 + 0.5 * 1800 * a2 * a2 + 300 * a2
            fr, _ = sput(fr, t, 'A2_v10_fall', (0.5, 0.5), (900, y), 1.9, rot=180 + 30 * a2, alpha=0.95, mblur=(0, 30))
        hk = max(K.pulse(t, tl, 0.08) * (t >= tl), K.pulse(t, CT(3, 9), 0.08) * (t >= CT(3, 9)), K.pulse(t, CT(3, 10), 0.10) * (t >= CT(3, 10)))
        dx, dy, dr = K.shake(t, 12 * hk, 15, 1010)
        return K.cam(fr, 1.0, dx, dy, dr), (3 if 0 <= t - tl < 0.07 else 0)


# =====================================================================================
# V11 28.93–29.86 ——竖刀当面：一柄直刀竖在脸前把脸劈成两半（右半脸在阴影里），刃口一线血光自下而上爬升；
#   层：背景（墨黑 + 右侧血红块，飞白边）/ 脸 A2_v11_face（发丝风动、极慢推）/ 竖刃 A2_v11_blade（视差 1.6，中点为零）/ 刃口血光 / 灰烬
class V11D(DShot):
    def __init__(self):
        self.bg = paper_bg(1101, red=(1700, 520, 560))

    def render(self, t):
        u = self.u(t); e = eio(u); par = e - 0.5
        fr = self.bg.copy()
        s = W / lay('A2_v11_face').w * 1.12 * (1 + 0.04 * e)
        fr, _ = sput(fr, t, 'A2_v11_face', (0.54, 0.52), (960 + 10 * par, 560), s, wind_amp=4.0)
        sb = 1250 / (0.976 * lay('A2_v11_blade').h)
        bx = 958 + 1.6 * 24 * par
        fr, Ab = sput(fr, t, 'A2_v11_blade', (0.5, 0.5), (bx, 540), sb)
        q = clamp01((t - (self.t0 + 0.20)) / 0.50)
        if q > 0:
            y = 1080 - 1150 * eio(q)
            yy = np.arange(H, dtype=np.float32)[:, None]
            ln = ((yy > y) & (np.abs(np.arange(W, dtype=np.float32)[None] - bx - 5) < 3.5)).astype(np.float32)
            ink = np.clip(cv2.dilate(ln.astype(np.float32), np.ones((1, 5), np.uint8)) - ln, 0, 1)
            fr = over(fr, ink, INKC); fr = over(fr, ln.astype(np.float32), BLOOD)
            fr = K.sparks(fr, t, 1102 + int(q * 8), (bx + 5, y), n=6, life=0.25, speed=(80, 260), dirc=(0, -1), spread=1.6, grav=900,
                          area=(4, 4), amt=1.0, color=tuple(BLOOD))
        fr = ASH.draw(fr, t, 0.3, wind=(-60, -20))
        return fr, 0


# =====================================================================================
# V12 + V13 29.86–32.60「我杀过恶徒 也放过混账」——一镜到底（沿用现版 'cont' 与 31.03 起的冷刀光擦除前沿，切点/节奏不变），
#   去掉「殺」「放」两个字；反差全部交给画面：
#   殺世界：血红天幕的雨夜荒路（A2_v12_bg）/ 斩后定势的鬼屠（A2_v12_hero）/ 恶徒（A2_v12_villain：被斩前伤口与血去色，30.10 斩下 →
#           沿伤口一刀两断，上半斜滑坠落、下半跪塌沉进地雾，断口血雾）/ 干笔飞白斩痕（白芯 + 血红缘 + 溅墨）+ 集中线 + 白闪 + 震屏
#   放世界：灰白冷雨的同一条路（A2_v13_bg）/ 同位收刀的鬼屠（A2_v13_hero 镜像朝右）/ 跪地磕头的混账（A2_v13_kneel，越磕越深、发抖）
#   31.03 起白刃前沿自左向右擦过，前沿左侧换成放世界；31.65 收刀入鞘「咔」：鞘口白火星 + 轻震
HERO_FOOT = (720.0, 905.0)
OPP_X = 1330.0
FANG_DX = 0.0
VILL_CUT = ((0.40, 0.17), (0.66, 0.44))           # A2_v12_villain 源图里伤口斜线两端（左肩 → 右胯）


def _ground(fr, col):
    yy = np.arange(H, dtype=np.float32)[:, None, None]
    g = np.clip((yy - 880) / 30, 0, 1)
    return fr * (1 - 0.35 * g) + g * 0.35 * np.asarray(col, np.float32) * 0.2


def _contact(fr, x, y, rx=200):
    cs = np.zeros((H // 2, W // 2), np.float32)
    cv2.ellipse(cs, (int(x / 2), int(y / 2)), (int(rx / 2), 9), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
    return fr * (1 - 0.7 * cv2.resize(cv2.GaussianBlur(cs, (0, 0), 5), (W, H))[..., None])


def _sf_u(t): return clamp01((t - V12.t0) / (V13.t1 - V12.t0))


VGR = dict(NEU, expo=0.85)                       # 恶徒：斩前斩后同一调色（伤口的红一直在，斩下时才裂开）


def sha_world(t):
    ts = CT(4, 1); a = t - ts
    u = _sf_u(t)
    fr = brighten(bgview('A2_v12_bg', 1.10, dx=-40 * (u - 0.5)), 0.35)
    fr = RAIN.draw(fr, t, 0.8, angle=4, color=(0.10, 0.02, 0.02), layers=(0, 1))
    fr = _contact(fr, HERO_FOOT[0] + 10, HERO_FOOT[1])
    # 恶徒
    sp = lay('A2_v12_villain')
    a_, s_ = sp.fit(640)
    foot = (OPP_X, HERO_FOOT[1] + 6)
    if a < 0:
        lean = -2.0 * clamp01((t - V12.t0) / max(1e-3, ts - V12.t0))       # 斩下帧接 rot=-2（两半与前一帧同姿）
        fr = _contact(fr, OPP_X, HERO_FOOT[1] + 6, rx=180)
        fr, _ = sput(fr, t, 'A2_v12_villain', a_, foot, s_, rot=lean, grade=VGR, wind_amp=2.0)
    else:
        P, Av = sput(np.zeros_like(fr), t, 'A2_v12_villain', a_, foot, s_, rot=-2.0, grade=VGR, wind_amp=2.0)
        p0 = np.array(spt('A2_v12_villain', a_, foot, s_, VILL_CUT[0])); p1 = np.array(spt('A2_v12_villain', a_, foot, s_, VILL_CUT[1]))
        d = (p1 - p0) / np.linalg.norm(p1 - p0); n = np.array([d[1], -d[0]])
        if n[1] > 0: n = -n                                                              # n 指向上方（上半身一侧）
        x, y = K.grid()
        sd = (x - p0[0]) * n[0] + (y - p0[1]) * n[1]
        mu = np.clip(sd + 0.5, 0, 1)
        g = 0.5 * 1400 * a * a
        up_off = d * (160 * eout(a / 0.5)) + np.array([0, g * 0.6]) - n * 10 * eout(a / 0.1)
        rot = -25 * eout(a / 0.6)
        c = (p0 + p1) / 2
        Mu = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), rot, 1.0); Mu[:, 2] += up_off
        Pu = cv2.warpAffine(P * mu[..., None], Mu, (W, H)); Au = cv2.warpAffine(Av * mu, Mu, (W, H))
        sink = 220 * ein(clamp01((a - 0.15) / 0.8), 2)
        Ml = np.float32([[1, 0, 0], [0, 1, sink]])
        Pl = cv2.warpAffine(P * (1 - mu)[..., None], Ml, (W, H)); Al = cv2.warpAffine(Av * (1 - mu), Ml, (W, H))
        clip = np.clip((HERO_FOOT[1] + 10 - y) / 18, 0, 1)
        Pl = Pl * clip[..., None]; Al = Al * clip
        fr = fr * (1 - Al[..., None]) + Pl
        fr = fr * (1 - Au[..., None]) + Pu
        fr = K.sparks(fr, t, 1201, tuple(c), n=90, life=0.7, speed=(200, 900), dirc=(1, -0.5), spread=1.1, grav=1300,
                      area=(80, 30), amt=1.2, t0=ts, burst=True, color=tuple(BLOOD))
        mist = np.exp(-(((x - c[0]) / 240) ** 2 + ((y - c[1]) / 150) ** 2)) * 0.5 * math.exp(-a / 0.5)
        fr = over(fr, mist.astype(np.float32), BLOOD * 0.8)
    fr = fog(fr, t, 2, 830, 960, 0.30, (0.25, 0.05, 0.05), speed=(-40, 0))
    fr, _ = sfit(fr, t, 'A2_v12_hero', 640, HERO_FOOT, wind_amp=6.0)
    if a >= 0:
        prog = clamp01(a / 0.08); fade = 1.0 if a < 0.12 else math.exp(-(a - 0.12) / 0.18)
        pts = bez((1700, 300), (1300, 520), (420, 760), 60)
        fr = brush(fr, pts, 60, prog, fade, 1202)
        fr = focus_lines(fr, (1220, 560), 0.85 * (a < 0.067), 1203 + int(a * 30), r0=360)
        fr = flash(fr, 0.6 * math.exp(-a / 0.04))
    return fr


def fang_world(t):
    u = _sf_u(t)
    fr = bgview('A2_v13_bg', 1.10, dx=-40 * (u - 0.5))
    fr = RAIN.draw(fr, t, 0.9, angle=4, color=(0.25, 0.25, 0.25), layers=(0, 1))
    fr = _contact(fr, HERO_FOOT[0] + 10 + FANG_DX, HERO_FOOT[1])
    fr, Ah = sfit(fr, t, 'A2_v13_hero', 660, (HERO_FOOT[0] + FANG_DX, HERO_FOOT[1]), wind_amp=5.0)
    tc = CT(4, 6) + 0.17
    if t >= tc:
        mouth = (HERO_FOOT[0] + FANG_DX - 10, HERO_FOOT[1] - 330)
        fr = K.sparks(fr, t, 1301, mouth, n=30, life=0.35, speed=(150, 500), dirc=(0, -1), spread=1.4, grav=900,
                      area=(10, 10), amt=1.0, t0=tc, burst=True, color=(1.0, 1.0, 1.0))
    bow = 1.0 + 5.0 * eio(u) + 1.4 * math.sin(t * 6.0) + 4.0 * K.pulse(t, CT(4, 6), 0.15) * (t >= CT(4, 6))
    trem = 2.5 * math.sin(t * 41) + 1.5 * math.sin(t * 67)
    fr = _contact(fr, OPP_X + FANG_DX, HERO_FOOT[1] + 4, rx=230)
    fr, _ = sfit(fr, t, 'A2_v13_kneel', 330, (OPP_X + FANG_DX + trem, HERO_FOOT[1] + 4), rot=-bow, wind_amp=1.5)
    fr = fog(fr, t, 2, 830, 960, 0.35, (0.55, 0.55, 0.55), speed=(-40, 0))
    return fr


class V12D(DShot):
    def render(self, t):
        a = t - CT(4, 1)
        fr = sha_world(t)
        dx, dy, dr = K.shake(t, 14 * K.pulse(t, CT(4, 1), 0.10) * (a >= 0), 16, 1204)
        return K.cam(fr, 1.0, dx, dy, dr), (3 if 0 <= a < 0.1 else 0)


class V13D(DShot):
    def render(self, t):
        xe = _sf_edge(t)
        if xe is None: fr = sha_world(t)
        elif xe > W + 400: fr = fang_world(t)
        else:
            m = _sf_mask(xe)[..., None]
            fr = sha_world(t) * (1 - m) + fang_world(t) * m
        fr = _sf_edge_glow(fr, xe, 1.2)
        fr = RAIN.draw(fr, t, 0.6, angle=4, color=(0.8, 0.8, 0.8), layers=(2,))
        tc = CT(4, 6) + 0.17
        dx, dy, dr = K.shake(t, 6 * K.pulse(t, tc, 0.08) * (t >= tc), 16, 1302)
        return K.cam(fr, 1.0, dx, dy, dr), 0


# =====================================================================================
# V14 32.60–34.44「每一次拔刀都」——用户：主角要有拔刀动作。三张同构图关键姿势（定妆照一致），按字拍硬切：
#   起势（按刀待发，A2_v14_p1）：「每」「一」「次」每拍护手处一点白光、身体蓄力微压；
#   33.78「拔」：半出鞘（A2_v14_p2），切入带横向动态模糊 + 白闪，刃面一道白光沿出鞘方向滑过；
#   34.10「刀」：全出鞘横扫（A2_v14_p3），干笔飞白刀弧（白芯 + 血红缘）沿刀路扫出、鞘口火星（白 + 血红）、集中线、白闪、震屏、色差
#   层：夜空背景板 A2_v14_bg（视差 0.5）/ 主体三姿势（按脸中心与脸宽对齐，发丝衣带风动；直刀 + 中式护手 + 素黑柄 + 环首红穗）/ 刀光 / 火星 / 前景灰烬
class V14D(DShot):
    HEAD = (880.0, 400.0)                                  # 脸中心落点（三姿势按脸对齐）
    S = (1.05, 0.90, 1.0)                                 # 按脸宽对齐（p1 0.090 / p2 0.105 / p3 0.095）
    POSE = ('A2_v14_p1', 'A2_v14_p2', 'A2_v14_p3')
    FACE = ((0.525, 0.27), (0.49, 0.30), (0.455, 0.29))     # 各姿势脸中心（源图归一化）
    GUARD = ((0.485, 0.735), (0.345, 0.585), (0.295, 0.42))  # 各姿势护手（源图归一化）
    # 画布：上缘 y<120（藏在黑边里）；p3 红带出左画布边 → 画布左缘 x≈-37

    def pose(self, t):
        tb, td = CT(5, 3) - 0.03, CT(5, 4) - 0.03
        return 0 if t < tb else (1 if t < td else 2), tb, td

    def render(self, t):
        u = self.u(t); e = eio(u); par = e - 0.5
        fr = bgview('A2_v14_bg', 1.12, dx=-50 * par, rot=-1.5 * par)
        fr = RAIN.draw(fr, t, 0.5, angle=-10, color=(0.7, 0.7, 0.7), layers=(0, 1))
        i, tb, td = self.pose(t)
        name = self.POSE[i]
        sp = lay(name)
        s = W / sp.w * self.S[i]
        a_src = self.FACE[i]
        dx_, mb = 0.0, (0.0, 0.0)
        if i == 0:
            press = 0.0
            for k in range(3):
                b = t - (CT(5, k) - 0.03)
                if b >= 0: press += 6 * math.exp(-b / 0.12)
            dst = (self.HEAD[0], self.HEAD[1] + press)
        elif i == 1:
            b = t - tb
            dx_ = 14 * eout(b / 0.3)
            mb = (40 * max(0.0, 1 - b / 0.07), 0)
            dst = (self.HEAD[0] + dx_, self.HEAD[1])
        else:
            b = t - td
            mb = (60 * max(0.0, 1 - b / 0.07), 0)
            dst = (self.HEAD[0] - 8 * eout(b / 0.25), self.HEAD[1])
        fr, Am = sput(fr, t, name, a_src, dst, s, wind_amp=5.0 if i < 2 else 9.0, mblur=mb)
        G = spt(name, a_src, dst, s, self.GUARD[i])
        if i == 0:
            for k in range(3):
                b = t - (CT(5, k) - 0.03)
                if 0 <= b < 0.4:
                    fr = star(fr, G, math.exp(-b / 0.10), 0.7, rot=15)
                    fr = K.sparks(fr, t, 1400 + k, G, n=14, life=0.3, speed=(120, 380), dirc=(1, -0.3), spread=0.8, grav=300,
                                  area=(6, 6), amt=0.9, t0=CT(5, k) - 0.03, burst=True, color=(1.0, 1.0, 1.0))
        elif i == 1:
            b = t - tb
            # 出鞘白光沿刃滑过（护手 → 鞘口方向）
            T_ = spt(name, a_src, dst, s, (0.655, 0.765))
            q = clamp01(b / 0.22)
            P = (G[0] + (T_[0] - G[0]) * q, G[1] + (T_[1] - G[1]) * q)
            fr = star(fr, P, 1.0 - 0.5 * q, 1.0, rot=31)
            fr = flash(fr, 0.5 * math.exp(-b / 0.04))
            fr = speed_lines(fr, t, 1410, 28, 0.5 * max(0.0, 1 - b / 0.15))
        else:
            b = t - td
            tip = spt(name, a_src, dst, s, (0.985, 0.41))
            pts = bez((G[0] + 120, G[1] + 260), (G[0] + 600, G[1] + 40), (tip[0] + 60, tip[1] - 10), 60)
            fade = 1.0 if b < 0.10 else math.exp(-(b - 0.10) / 0.22)
            fr = brush(fr, pts, 80, clamp01(b / 0.07), fade, 1411)
            mouth = spt(name, a_src, dst, s, (0.765, 0.775))
            fr = K.sparks(fr, t, 1412, mouth, n=50, life=0.5, speed=(300, 900), dirc=(1, -0.6), spread=0.9, grav=700,
                          area=(10, 10), amt=1.0, t0=td, burst=True, color=(1.0, 1.0, 1.0))
            fr = K.sparks(fr, t, 1413, mouth, n=30, life=0.45, speed=(250, 800), dirc=(1, -0.4), spread=1.0, grav=700,
                          area=(10, 10), amt=1.0, t0=td, burst=True, color=tuple(BLOOD))
            fr = focus_lines(fr, (tip[0] - 300, tip[1]), 0.8 * (b < 0.067), 1414 + int(b * 30), r0=420)
            fr = flash(fr, 0.7 * math.exp(-b / 0.04))
        hk = max(K.pulse(t, tb, 0.08) * (t >= tb), 1.5 * K.pulse(t, td, 0.10) * (t >= td))
        dx, dy, dr = K.shake(t, 2.5 + 10 * hk, 12, 1415)
        return K.cam(fr, 1.0 + 0.015 * hk, dx, dy, dr), (4 if 0 <= t - td < 0.1 else (2 if 0 <= t - tb < 0.07 else 0))


# =====================================================================================
# V15 34.44–36.27「是我的主张」——用户：「我的主张」刻字分镜不合适 → 改为「立刀」：雨夜空旷的宫前广场，低机位仰拍，
#   鬼屠反手双握长刀举在胸前（A2_v15_raise），「我」「的」两拍刀再提一档、风起；35.46「主」：反白冲击帧后硬切插刀定姿（A2_v15_plant）——
#   刀尖贯入石板，墨裂缝自刀尖放射（缝里透血红）、冲击环推开雨雾、前景碎石扑向镜头、集中线、白闪、震屏；35.82「张」：裂缝再裂一档、血光一跳。
#   「主张」= 他把刀插在这里，不靠任何字。层：广场背景板 A2_plaza（视差 0.4，与 V20 共用）/ 主体两姿势 / 裂缝 / 冲击环 / 前景碎石 A2_shards / 雨
class V15D(DShot):
    FOOT, HGT = (960.0, 940.0), 790.0

    def render(self, t):
        u = self.u(t); e = eio(u); par = e - 0.5
        T1, T2 = CT(5, 9), CT(5, 10)
        fr = brighten(bgview('A2_plaza', 1.15, dx=-40 * par, dy=-60 + 30 * par), 0.45)
        fr = RAIN.draw(fr, t, 0.75, angle=-6, color=(0.80, 0.80, 0.80), layers=(0, 1))
        a1 = t - T1
        if a1 < -1 / 30 + 1e-4:
            lift = 0.0
            for k, amt in ((7, 10), (8, 10)):
                b = t - CT(5, k)
                if b >= 0: lift += amt * eout(b / 0.15)
            lift += 22 * ein(clamp01((t - (T1 - 0.20)) / 0.17), 2)
            name = 'A2_v15_raise'; foot = (self.FOOT[0], self.FOOT[1] - lift)
            wind = 5.0 + 5.0 * clamp01((t - CT(5, 8)) / 0.2)
            fr = _contact(fr, self.FOOT[0], self.FOOT[1], rx=210)
            fr, Am = sfit(fr, t, name, self.HGT, foot, wind_amp=wind)
            return fr, 0
        if a1 < 0:                                                       # 反白冲击帧（命中前一帧）
            fr = _contact(fr, self.FOOT[0], self.FOOT[1], rx=210)
            fr, Am = sfit(fr, t, 'A2_v15_raise', self.HGT, (self.FOOT[0], self.FOOT[1] - 30), wind_amp=8.0)
            return invert_frame(fr, Am), 4
        sp = lay('A2_v15_plant'); a_, s_ = sp.fit(self.HGT)
        tipn = lowest('A2_v15_plant')
        tip = spt('A2_v15_plant', a_, self.FOOT, s_, tipn)
        a2 = t - T2
        prog = 0.55 * eout(a1 / 0.10) + (0.45 * eout(a2 / 0.12) if a2 >= 0 else 0)
        cr = ink_cracks(tip, 9, 900, prog, width=3.5, seed=151)
        hot = 1.0 + 1.2 * math.exp(-a1 / 0.15) + (0.9 * math.exp(-a2 / 0.12) if a2 >= 0 else 0)
        glow = K.blur_ds(cr, 10)
        fr = over(fr, np.clip(cr * 1.2, 0, 1), INKC)
        fr = fr + (glow * 0.9 * hot)[..., None] * BLOOD
        # 冲击环：推开雨雾的白环（扁椭圆贴地）
        x, y = K.grid()
        rr = 80 + 1500 * eout(a1 / 0.5)
        dd = np.sqrt(((x - tip[0]) / 1.0) ** 2 + ((y - tip[1]) / 0.30) ** 2)
        nz = texr(1506, 256, 6, 4)
        ring = np.exp(-((dd - rr + (nz - 0.5) * 120) / 22) ** 2) * math.exp(-a1 / 0.30) * np.clip((nz - 0.35) * 3, 0, 1)
        fr = over(fr, np.clip(ring * 0.9, 0, 1).astype(np.float32), INKC)
        fr = _contact(fr, self.FOOT[0], self.FOOT[1], rx=220)
        kick = 6 * math.exp(-a1 / 0.06)
        fr, Am = sfit(fr, t, 'A2_v15_plant', self.HGT, (self.FOOT[0], self.FOOT[1] + kick), wind_amp=7.0 + 6 * math.exp(-a1 / 0.3))
        fr = K.sparks(fr, t, 1501, tip, n=80, life=0.55, speed=(300, 1100), dirc=(0, -1), spread=1.3, grav=1300,
                      area=(20, 6), amt=1.0, t0=T1, burst=True, color=(1.0, 1.0, 1.0))
        fr = K.sparks(fr, t, 1502, tip, n=40, life=0.5, speed=(250, 900), dirc=(0, -1), spread=1.2, grav=1300,
                      area=(20, 6), amt=1.0, t0=T1, burst=True, color=tuple(BLOOD))
        if a2 >= 0:
            fr = K.sparks(fr, t, 1503, tip, n=40, life=0.45, speed=(200, 700), dirc=(0, -1), spread=1.6, grav=1300,
                          area=(200, 6), amt=0.9, t0=T2, burst=True, color=tuple(BLOOD))
        # 前景碎石：扑向镜头放大出画，0.36s 内淡出
        if a1 < 0.4:
            q = clamp01(a1 / 0.4)
            al = 0.95 * (1 - K.sstep(0.22, 0.36, a1))
            if al > 0.01:
                fr, _ = sput(fr, t, 'A2_shards', (0.5, 0.5), (960, 560), W / lay('A2_shards').w * (1.05 + 1.0 * eout(q, 2)),
                             alpha=al, mblur=(0, 20 * q))
        fr = focus_lines(fr, (tip[0], tip[1] - 300), 0.9 * (a1 < 0.067) + 0.6 * (0 <= a2 < 0.034), 1504 + int(a1 * 30), r0=460)
        fr = flash(fr, 0.75 * math.exp(-a1 / 0.04) + (0.35 * math.exp(-a2 / 0.04) if a2 >= 0 else 0))
        sk = K.pulse(t, T1, 0.10) + (0.6 * K.pulse(t, T2, 0.08) if a2 >= 0 else 0)
        dx, dy, dr = K.shake(t, 16 * sk + 1.0, 16, 1505)
        ca = 3 if a1 < 0.067 or 0 <= a2 < 0.034 else 0
        return K.cam(fr, 1.0 + 0.03 * sk, dx, dy, dr), ca


# =====================================================================================
# V16 36.27–38.10「若正义」——仰拍：太上皇（定妆照一致）立在风里举手召印，头顶墨云漩涡旋开、涡心白炽；36.9 起一方玉玺自涡心成形、
#   放大下压（白光 + 血红放射线）；37.13 军鼓 / 37.50「正」/ 37.78「义」三拍涡心光与印身一闪。
#   层：漩涡背景板 A2_vortex（绕涡心慢旋）/ 玉玺 A2_seal（由虚到实、放大下压）/ 太上皇 A2_v16_emperor（纱袍与长发风动）/ 灰烬
class V16D(DShot):
    EYE = (1180.0, 300.0)

    def render(self, t):
        u = self.u(t); e = eio(u)
        fr = bgview('A2_vortex', 1.30, pivot=(0.53, 0.32), at=self.EYE, rot=-14 * e)
        hits = [K.pulse(t, x, 0.12) * (t >= x) for x in (V(37.129), CT(6, 1), CT(6, 2))]
        hk = max(hits)
        k = eio(clamp01((t - V(36.9)) / 1.0))
        if k > 0:
            sp = lay('A2_seal')
            s = (0.06 + 0.26 * k) * W / sp.w * 1.6
            c = (self.EYE[0] - 20, self.EYE[1] + 40 + 110 * k)
            fr, As = sput(fr, t, 'A2_seal', (0.5, 0.55), c, s, alpha=min(1.0, 1.4 * k),
                          grade=dict(NEU, expo=0.55 + 0.45 * k + 0.4 * hk))
        fr, Ae = sfit(fr, t, 'A2_v16_emperor', 900, (640, 1010), wind_amp=9.0)
        fr = ASH.draw(fr, t, 0.35, wind=(-120, -40))
        return flash(fr, 0.25 * hk), (2 if hk > 0.7 else 0)


# =====================================================================================
# V17 38.10–39.47「由权势」——侧面低机位：玉玺自天坠落（越落越快、竖向动态模糊、两侧速度线、雨被推开），38.72「势」落地：
#   反白冲击一帧 → 俯拍印坑（A2_v17_crater）：碎石扑向镜头、尘浪环、裂缝血光脉动、集中线、震屏；38.99 底鼓裂缝再亮一下。
#   层：仰角天幕背景板 A2_v17_sky / 玉玺 A2_seal / 速度线 / 印坑背景板 A2_v17_crater / 尘浪 / 前景碎石 A2_shards
class V17D(DShot):
    def render(self, t):
        th = V(38.72); a = t - th
        if a < 0: return self.side(t, th)[0], 0
        if a < 1 / 30 - 1e-4:
            fr, As = self.side(t, th, land=True)
            return invert_frame(fr, As), 4
        return self.top(t, a)

    def side(self, t, th, land=False):
        q = 1.0 if land else clamp01((t - self.t0) / (th - self.t0))
        fr = bgview('A2_v17_sky', 1.10, dy=30 * q)                                 # 独立板：仰角天幕，涡心留白给坠印
        fr = RAIN.draw(fr, t, 0.8, angle=-6, color=(0.8, 0.8, 0.8), layers=(0, 1))
        by = 330 + 560 * ein(q, 1.8)
        sp = lay('A2_seal')
        s = 720 / ((sp.bbox[2] - sp.bbox[0]) * sp.w)
        fr = speed_lines(fr, t, 1701, -90, 0.6 * q, n=60)
        fr, As = sput(fr, t, 'A2_seal', (0.5, 0.97), (960, by), s, mblur=(0, 3 + 30 * q * q))
        # 雨被推开：印身两侧的白色气流线
        if q > 0.3:
            for side in (-1, 1):
                fr = K.sparks(fr, t, 1702 + side, (960 + side * 380, by - 120), n=24, life=0.25, speed=(300, 700),
                              dirc=(side, 0.6), spread=0.4, grav=0, area=(10, 100), amt=0.6 * q, color=(1.0, 1.0, 1.0))
        return fr, As

    def top(self, t, a):
        z = 1.10 - 0.08 * eout(a / 0.5)
        fr = bgview('A2_v17_crater', 1.08, z=z)
        # 裂缝血光脉动（原图里的红）
        rm = SD.red_mask(fr)
        k2 = t - V(38.992)
        hot = 0.6 * math.exp(-a / 0.2) + (0.5 * math.exp(-k2 / 0.12) if k2 >= 0 else 0)
        fr = fr + K.blur_ds(rm, 12)[..., None] * BLOOD * hot
        # 尘浪：贴坑沿外推的灰白墨烟环
        x, y = K.grid()
        rr = 330 + 700 * eout(a / 0.7)
        d = np.sqrt((x - 960) ** 2 + ((y - 560) / 0.85) ** 2)
        nz = texr(1703, 256, 6, 4)
        ring = np.exp(-((d - rr + (nz - 0.5) * 160) / 45) ** 2) * math.exp(-a / 0.35)
        ring = ring * np.clip((nz - 0.35) * 3, 0, 1)                                   # 飞白断丝
        fr = over(fr, np.clip(ring * 0.85, 0, 1).astype(np.float32), (0.06, 0.06, 0.06))
        if a < 0.4:
            q = clamp01(a / 0.4); al = 0.95 * (1 - K.sstep(0.22, 0.36, a))
            if al > 0.01:
                fr, _ = sput(fr, t, 'A2_shards', (0.5, 0.5), (960, 540), W / lay('A2_shards').w * (1.0 + 1.1 * eout(q, 2)),
                             rot=180, alpha=al, mblur=(0, 20 * q))
        fr = focus_lines(fr, (960, 560), 0.85 * (a < 0.1), 1704 + int(a * 30), r0=520)
        fr = flash(fr, 0.6 * math.exp(-a / 0.05))
        sk = K.pulse(t, V(38.72), 0.12) + (0.4 * K.pulse(t, V(38.992), 0.08) if k2 >= 0 else 0)
        dx, dy, dr = K.shake(t, 18 * sk + 1.0, 16, 1705)
        return K.cam(fr, 1.0, dx, dy, dr), (3 if a < 0.1 else 0)


# =====================================================================================
# V18 39.47–40.84「执掌」——高机位俯拍：雨夜广场，左上是同一个印坑的一角，裂缝一路裂到鬼屠脚下；他极小、长影拖向右下。
#   层：俯拍背景板 A2_v18_plate（缓拉 + 回旋）/ 鬼屠 A2_v18_hero（自带长影，衣带风动）/ 俯视雨（短划）/ 地雾 / 39.90 底鼓裂缝血光一跳
class V18D(DShot):
    def render(self, t):
        u = self.u(t); e = eio(u)
        fr = bgview('A2_v18_plate', 1.12, rot=-2.5 * (e - 0.5), z=1.0 + 0.03 * (1 - e))
        rm = SD.red_mask(fr)
        k = t - V(39.903)
        if k >= 0: fr = fr + K.blur_ds(rm, 10)[..., None] * BLOOD * 0.6 * math.exp(-k / 0.15)
        fr = fog(fr, t, 0, 120, 960, 0.20, (0.6, 0.6, 0.6), speed=(-35, 10))
        fr, _ = sfit(fr, t, 'A2_v18_hero', 300, (1270, 720), wind_amp=6.0)
        fr = RAIN.draw(fr, t, 0.7, angle=-25, color=(0.85, 0.85, 0.85), layers=(0, 1, 2))
        return fr, 0


# =====================================================================================
# V19 40.84–41.77「那我宁愿」——MCU 仰望：人在左、脸朝右上，望向右上一轮干笔血红日（白纸网点天 + 集中线指向血日）；
#   肩后露出直刀黑柄、中式护手、环首红穗（穗子风动）；雨打在脸上；41.40「乱」眼中一点白星。
#   层：白纸网点底 + 血红日轮 + 集中线 / 主体 A2_v19_mcu（发丝风动、呼吸、极慢升）/ 眼光 / 雨
class V19D(DShot):
    FACE = (0.58, 0.32)
    AT = (760.0, 470.0)                         # 画布：左缘 x≈-630、上缘 y≈40（黑边内），右缘只在下黑边里有像素
    EYE = (0.555, 0.215)

    def render(self, t):
        u = self.u(t); e = eio(u)
        fr = paper_bg(1901, red=(1480, 330, 360))
        fr = focus_lines(fr, (1480, 300), 0.75, 1902, r0=300, n=90)
        s = W / lay('A2_v19_mcu').w * 1.25
        fr, Am = sput(fr, t, 'A2_v19_mcu', self.FACE, (self.AT[0], self.AT[1] - 10 * (e - 0.5)), s, wind_amp=6.0, breathe=0.004)
        g = math.exp(-max(0, t - V(41.40)) / 0.12) * (t >= V(41.40))
        if g > 0.01:
            ep = spt('A2_v19_mcu', self.FACE, (self.AT[0], self.AT[1] - 10 * (e - 0.5)), s, self.EYE)
            fr = star(fr, ep, g, 0.45, rot=10)
        fr = RAIN.draw(fr, t, 0.7, angle=-8, color=(0.85, 0.85, 0.85), layers=(1, 2))
        return fr, 0


# =====================================================================================
# V20 41.77–42.68「做乱世的」——极低机位全身：低伏蓄势（A2_v20_coil）→ 42.0 撩刀：一帧过身（上冲姿势 + 强动态模糊）→
#   弓步上冲送刀（A2_v20_rise）；干笔飞白刀弧从左下刀尖位扫到右上刀尖位（白芯 + 血红缘 + 溅墨），火星（白 + 血红）、蹬地扬尘、白闪、震屏。
#   层：广场背景板 A2_plaza（与 V15 同板但水平翻转、仰角更低、裁切不同，天空换成白纸网点 + 血红日轮）/ 主体两姿势 / 刀弧 / 火星 / 扬尘
class V20D(DShot):
    FOOT = (900.0, 935.0)

    def render(self, t):
        u = self.u(t); e = eio(u)
        ts = V(42.0); a = t - ts
        fr = brighten(bgview('A2_plaza', 1.25, dx=-30 * (e - 0.5), dy=120)[:, ::-1].copy(), 0.35)
        sky = paper_bg(2006, red=(1330, 330, 250))                               # 血红天幕 → 白纸天 + 血红日轮（对标 S030），与 V15 拉开
        rm = SD.red_mask(fr) * (np.arange(H, dtype=np.float32)[:, None] < 800)
        rm = cv2.GaussianBlur(rm.astype(np.float32), (0, 0), 1.2)[..., None]
        fr = fr * (1 - rm) + sky * rm
        fr = RAIN.draw(fr, t, 0.6, angle=-6, color=(0.8, 0.8, 0.8), layers=(0, 1))
        fr = _contact(fr, self.FOOT[0], self.FOOT[1], rx=200 if a < 0 else 240)
        sx, sy = R8.shake(t, ts, amp=14, tau=0.10, seed=3)
        if a < 0:
            dy = 8 * eio(clamp01((t - self.t0) / max(1e-3, ts - self.t0)))
            fr, Am = sfit(fr, t, 'A2_v20_coil', 560, (self.FOOT[0], self.FOOT[1] + dy), wind_amp=8.0)
            return fr, 0
        if a < 1 / 30 - 1e-4:
            foot = (self.FOOT[0] + sx, self.FOOT[1] + 30 + sy)
            fr, Am = sfit(fr, t, 'A2_v20_rise', 820, foot, wind_amp=10.0, mblur=(36, -30))
        else:
            dy = -10 * eout(clamp01(a / 0.4))
            foot = (self.FOOT[0] + sx, self.FOOT[1] + dy + sy)
            fr, Am = sfit(fr, t, 'A2_v20_rise', 820, foot, wind_amp=10.0, mblur=(0, 18 * max(0.0, 1 - a / 0.12)))
        sp = lay('A2_v20_rise'); a_, s_ = sp.fit(820)
        tip = spt('A2_v20_rise', a_, foot, s_, sp.top)
        pts = bez((430, 860), (1250, 700), (tip[0] + 30, tip[1] - 20), 60)
        fade = 1.0 if a < 0.10 else math.exp(-(a - 0.10) / 0.25)
        fr = brush(fr, pts, 90, clamp01(a / 0.07), fade, 2001)
        fr = K.sparks(fr, t, 2002, tip, n=60, life=0.6, speed=(200, 900), dirc=(0.6, -0.8), spread=1.2, grav=900,
                      area=(40, 40), amt=1.0, t0=ts, burst=True, color=(1.0, 1.0, 1.0))
        fr = K.sparks(fr, t, 2003, tip, n=40, life=0.5, speed=(200, 800), dirc=(0.6, -0.8), spread=1.3, grav=900,
                      area=(40, 40), amt=1.0, t0=ts, burst=True, color=tuple(BLOOD))
        fr = K.sparks(fr, t, 2004, self.FOOT, n=40, life=0.5, speed=(80, 300), dirc=(0, -1), spread=1.6, grav=500,
                      area=(160, 6), amt=0.4, t0=ts, burst=True, color=(0.7, 0.7, 0.7))
        fr = focus_lines(fr, (tip[0] - 200, tip[1] + 150), 0.8 * (a < 0.067), 2005 + int(a * 30), r0=420)
        fr = flash(fr, 0.6 * math.exp(-a / 0.04))
        return fr, (5 if a < 0.12 else 0)


# =====================================================================================
# V21 42.68–44.03「锋芒」——用户：「锋芒」纯文字镜不要 → 把「锋芒」画成真东西：刀锋特写（直刀、平直刃线，无波纹刃纹）。
#   V20 的刀弧斩开画面（a_cleave，转场不变）→ 刀尖段大特写沿 −62° 斜线自左下滑入（动态模糊，刀尖停在画内、护手与柄在上黑边外），42.84「锋」落定一震；
#   42.84→43.08 一道白光沿刃口从护手一侧走到刀尖；43.08「芒」：刀尖白色十字星芒 + 血红光晕 + 白闪；
#   43.30 刀沿自身那条线把整个画面劈开、两半错开，缝里一线血红；43.57 底鼓两半再一震；43.65 起墨从斜缝向两侧吞满画面、
#   只留一道血红细缝（交给 B 组「墨渗成纸」，出口与现版一致）。
#   层：白纸网点底 + 血红墨块 + 集中线 / 刀身 A2_v21_edge / 刃口白光 / 刀尖星芒 / 劈开 / 墨缝
class V21D(DShot):
    ANG = -62.0
    ROT = 35.8                                   # 源图刀轴 −26.2°（刀尖 (0.023,0.905) → 护手 (0.83,0.20)）→ −62°
    C = (960.0, 540.0)
    TIPN = (0.023, 0.905)                        # 源图刀尖
    HILTN = (0.83, 0.20)                         # 源图护手

    def scene(self, t):
        tf, tm = CT(7, 8), CT(7, 9)
        fr = paper_bg(2100, red=(1500, 760, 520))
        fr = focus_lines(fr, self.C, 0.55, 2103, r0=520, n=80)
        sp = lay('A2_v21_edge')
        s = 1.30
        th = math.radians(self.ANG); dv = np.array([math.cos(th), math.sin(th)])
        q = clamp01((t - self.t0) / (tf - self.t0))
        off = -1100 * (1 - eout(q, 3))
        nv = np.array([-dv[1], dv[0]])
        tip0 = np.array(self.C) - dv * 362 - nv * 170            # 落定后刀尖 ≈(640,780)；刀身在劈线左侧 170px，43.30 沿刃旁这条线劈开、左半带刀滑走
        dst = (tip0[0] + dv[0] * off, tip0[1] + dv[1] * off)
        mb = (dv[0] * 60 * (1 - q), dv[1] * 60 * (1 - q)) if q < 1 else (0, 0)
        fr, Ab = sput(fr, t, 'A2_v21_edge', self.TIPN, dst, s, rot=self.ROT, mblur=mb)
        tipp = spt('A2_v21_edge', self.TIPN, dst, s, self.TIPN, self.ROT)
        hilt = spt('A2_v21_edge', self.TIPN, dst, s, self.HILTN, self.ROT)
        if hilt[1] < 120:                                         # 白光从刃身入画处起走（护手在黑边外）
            k_ = (120 - tipp[1]) / (hilt[1] - tipp[1]); hilt = (tipp[0] + (hilt[0] - tipp[0]) * k_, 120.0)
        a = t - tf
        if a >= 0:
            k = clamp01(a / (tm - tf))
            P = (hilt[0] + (tipp[0] - hilt[0]) * k, hilt[1] + (tipp[1] - hilt[1]) * k)
            if t < tm + 0.05: fr = star(fr, P, 1.0, 0.9, rot=-62)
        b = t - tm
        if b >= 0:
            g = math.exp(-b / 0.25)
            fr = star(fr, tipp, g, 2.2, rot=-17)
            fr = flash(fr, 0.6 * math.exp(-b / 0.04))
        return fr, a, b

    def render(self, t):
        fr, a, b = self.scene(t)
        ts = V(43.30); c = t - ts
        hk = max(K.pulse(t, CT(7, 8), 0.08) * (a >= 0), K.pulse(t, CT(7, 9), 0.08) * (b >= 0))
        if c >= 0:
            th = math.radians(self.ANG); dv = (math.cos(th), math.sin(th)); nv = (-dv[1], dv[0])
            x, y = K.grid()
            sd = (x - self.C[0]) * nv[0] + (y - self.C[1]) * nv[1]
            sep = 10 + 40 * eout(c / 0.12) + (14 * math.exp(-(t - V(43.566)) / 0.08) if t >= V(43.566) else 0)
            sl = 60 * eout(c / 0.3)
            out = np.zeros_like(fr) + INKC
            for sg in (1, -1):
                M = np.float32([[1, 0, sg * (nv[0] * sep / 2 + dv[0] * sl)], [0, 1, sg * (nv[1] * sep / 2 + dv[1] * sl)]])
                half = cv2.warpAffine(fr, M, (W, H), borderMode=cv2.BORDER_REFLECT)
                mk = np.clip((sg * sd - sep / 2) + 0.5, 0, 1)[..., None]
                out = out * (1 - mk) + half * mk
            fr = out
            seam = np.exp(-(sd / 3.0) ** 2)
            fr = fr + seam[..., None] * (BLOOD * 1.4 + WHITE * 0.6 * math.exp(-c / 0.06))
            if c < 0.07: fr = flash(fr, 0.6)
            fr = brush(fr, bez((self.C[0] - dv[0] * 1300, self.C[1] - dv[1] * 1300), self.C,
                               (self.C[0] + dv[0] * 1300, self.C[1] + dv[1] * 1300), 50), 40, clamp01(c / 0.06),
                       math.exp(-c / 0.2), 2101, ink=False)
            k = clamp01((c - 0.50) / 0.12) ** 1.3
            if k > 0:
                yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
                n = (-(xx * 2 - 960) * math.sin(th) + (yy * 2 - 540) * math.cos(th))
                nz = INKNZ()
                ink = np.clip((60 + 900 * k ** 2 + nz * 200 - np.abs(n)) / 40, 0, 1)
                ink = cv2.resize(ink, (W, H))[..., None]
                fr = fr * (1 - ink) + INK * ink
                sm = cv2.resize(np.exp(-(n / 4) ** 2), (W, H))[..., None]
                fr = fr + sm * RED * 1.2 * (1 - k * 0.5)
            hk = max(hk, K.pulse(t, ts, 0.10))
        dx, dy, dr = K.shake(t, 12 * hk, 16, 2102)
        return K.cam(fr, 1.0 + 0.02 * hk, dx, dy, dr), (5 if 0 <= c < 0.1 else (3 if 0 <= b < 0.07 else 0))


# =====================================================================================
D = dict(V08=V08D, V09=V09D, V10=V10D, V11=V11D, V12=V12D, V13=V13D, V14=V14D, V15=V15D, V16=V16D, V17=V17D, V18=V18D,
         V19=V19D, V20=V20D, V21=V21D)


def apply(mod):
    """把 mod.SHOTS 里 V08–V21 换成 D 版（同名、同 t0/t1），并只改这些镜头自己的 CUTS / FG / EXPO / INNER 项。"""
    G = {k: v for k, v in vars(mod).items() if not k.startswith('__') and k not in ('apply', 'D', 'NAMES')}
    globals().update(G)
    import sprite, style_d
    globals().update(SP=sprite, SD=style_d, GEN=mod.ROOT + '/assets/gen/R8_D/A2/')
    for i, S_ in enumerate(mod.SHOTS):
        nm = S_.__name__
        if nm in D:
            Dc = D[nm]
            Dc.t0, Dc.t1 = S_.t0, S_.t1
            Dc.__name__ = nm
            mod.SHOTS[i] = Dc
    # 转场：只改含字或金色的两处，切点 / 时长不变
    mod.CUTS['V15'] = ('match_cut', 0.08, 0.12, dict(shape='line', center=(960, 470), angle=0, mode='cut', glow=WHITE))   # 拔刀横刃 ↔ 立刀镜
    mod.CUTS['V16'] = ('ink_bleed', 0.08, 0.34, dict(seed=16, center=(960, 360)))                                     # 原 a_glyph「主」字形遮罩 → 墨晕
    mod.CUTS['V12'] = ('a_cleave', 0.10, 0.16, dict(angle=58, center=(960, 540), mode='open', col=(1.0, 0.9, 0.9)))     # 斩缝去暖橙
    mod.CUTS['V21'] = ('a_cleave', 0.10, 0.16, dict(angle=-62, center=(1420, 540), mode='open', col=(1.0, 0.9, 0.9)))
    t_lo, t_hi = D['V08'].t0, D['V21'].t1
    _fgdraw = mod.VC.FGLayer.draw
    class _FGD(mod.VC.FGLayer):
        def draw(self, fr, t, st, kind='ash', amt=0.5, wind=(30, -40)):
            if t_lo - 1e-6 <= t < t_hi and kind in ('ember', 'gold'): kind = 'ash'     # 风格 D：本段无金红余烬
            return _fgdraw(self, fr, t, st, kind, amt, wind)
    _init = mod.Section.__init__
    def _sec_init(self, _i=_init):
        _i(self); self.fg.__class__ = _FGD
    mod.Section.__init__ = _sec_init
    for nm in NAMES:
        k = mod.FG.get(nm)
        if k and k[0] in ('gold', 'ember'): mod.FG[nm] = ('ash', k[1])
    for nm in ('V10', 'V11', 'V19', 'V21'):
        mod.EXPO[nm] = 1.0 / mod.EXPO_ALL                                         # 白纸底镜头：抵消段落 1.15 提亮，纸白不削顶；其余镜沿用提亮（SPREAD §10 亮度）
    for nm in ('V09', 'V10', 'V13', 'V19', 'V20'): mod.INNER.pop(nm, None)
    mod.INNER['V14'] = dict(z=(1.0, 1.04), c=(960, 500), rot=(-4.0, 0.0))          # 荷兰角回正（拔刀时机位随刀扶正），幅度收小、不裁头
    mod.INNER['V12'] = dict(z=(1.0, 1.012), c=(960, 540), ease='lin')
    mod.INNER['V13'] = dict(z=(1.012, 1.037), c=(960, 540), ease='lin')
    # 屏幕层横排歌词（LY2，字体叠加）在本段不画；本段之外照旧交给前一个函数（可能已被 r8d_a1 替换）
    prev = mod.lyrics
    lo = mod.CUT_F[mod.SHOTS.index(D['V08'])] / mod.FPS
    hi = t_hi
    def lyrics(fr, t, _prev=prev):
        if t >= hi: return _prev(fr, t)                                   # 本段之后照旧
        k = clamp01((t - lo) / (4 / 30))                                # 切点起 4 帧淡出（V07 里已开写的「谁在高处」不再在切点上硬消失）
        if k >= 1: return fr
        out = _prev(fr.copy(), t)
        return out if k <= 0 else out * (1 - k) + fr * k
    mod.lyrics = lyrics
