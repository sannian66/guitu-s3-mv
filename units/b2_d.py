"""units/b2_d.py — 第八轮风格 D · B2 主歌二（V01–V25，帧 2586–3534）。只在 STYLE_D=1 时由 units/sec_b_verse2.py 接入。
切点 / 镜长 / 入出转场 / 字幕 / 卡点时刻全部沿用 sec_b_verse2（CUT_F、CUTS、CT() 字头）；每镜素材换成风格 D 生图分层（assets/gen/R8_D/B2/，
提示词 jobs/r8_D_B2.json），精灵一律 grade=NEU / rim=NORIM / wrap=0 / shade=None；特效笔触 D 化（墨线细雨、干笔飞白刀痕、白 + 血红火星、墨点碎屑）。
画面字只保留用户点名的：V07「权」（窗光投影，生图）、V09–V11「牺牲多少才算够分量」（同一架算盘梁上刻字，生图，逐字遮罩揭开：先白热、再灌血）、
V16「天命」（碑刻，生图）、V20/V21「黑」「白」（两面幡，生图；「白」幡倒置入水，V21 转 180° 后正读）。其余画面字一律不出。
防漂移：每镜的主体是一个刚体层，镜头运动统一在最后 cam() 一次做；层间视差偏移都以镜头中点为零。"""
import os, sys, math, copy
import numpy as np, cv2
import c1kit as K
from c1kit import clamp01, eio, eout, ein, sstep, pulse, cam, RED, W, H
import b_kit as BK
from b_kit import V, CT, shake, Shot
import sprite as SP
import fx2
import b_carve as BV
import b_staff as BSF

ROOT = os.environ.get('MV_ROOT', '/workspace/work/mv')
G = ROOT + '/assets/gen/R8_D/B2/'
FPS = 30
NEU = dict(expo=1.0, sat=1.0, tint=(1.0, 1.0, 1.0), lift=0.0, gamma=1.0)
NORIM = dict(col=(1.0, 1.0, 1.0), amt=0.0, dir=(0.0, -1.0))
DKW = dict(grade=NEU, rim=NORIM, wrap=0, shade=None)
WHITE = np.array([0.95, 0.95, 0.95], np.float32)
INK = np.array([0.02, 0.02, 0.02], np.float32)
REDC = tuple(float(v) for v in RED * 1.1)


def _bv2():
    """sec_b_verse2 的共用件（neg_grade / roll_pad / ring_warp）；渲染时该模块已加载完"""
    return sys.modules.get('sec_b_verse2') or __import__('sec_b_verse2')


# ------------------------------------------------------------------ 素材
def plate(name, sc=1.0, gain=1.0, blur=0.0):
    im = cv2.cvtColor(cv2.imread(G + name + '.png'), cv2.COLOR_BGR2RGB)
    im = cv2.resize(im, (int(W * sc), int(H * sc)), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    if blur: im = cv2.GaussianBlur(im, (0, 0), blur)
    return im * gain


def view(P, cx, cy, z=1.0, rot=0.0, ox=0.0, oy=0.0):
    """从底板 P 取景：底板点 (cx,cy) 放到屏幕 (W/2+ox, H/2+oy)，缩放 z、旋转 rot 度"""
    M = cv2.getRotationMatrix2D((float(cx), float(cy)), rot, z)
    M[0, 2] += W / 2 - cx + ox; M[1, 2] += H / 2 - cy + oy
    return cv2.warpAffine(P, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


_SPR = {}


def spr(name, work_w=2048, flip=False):
    k = (name, work_w, flip)
    if k not in _SPR:
        sp = SP.SpriteLayer(G + name + '_cut.png', work_w=work_w)
        if flip:
            sp = copy.copy(sp)
            sp.F = np.ascontiguousarray(sp.F[:, ::-1]); sp.A = np.ascontiguousarray(sp.A[:, ::-1])
            sp.ring = np.ascontiguousarray(sp.ring[:, ::-1]); sp.wind_w = np.ascontiguousarray(sp.wind_w[:, ::-1])
            x0, y0, x1, y1 = sp.bbox; sp.bbox = (1 - x1, y0, 1 - x0, y1); sp.top = (1 - sp.top[0], sp.top[1])
            SP._UID[0] += 1; sp._uid = SP._UID[0]; sp._supp = None; sp._supp_for = None; sp._box = {}
        _SPR[k] = sp
    return _SPR[k]


def put(fr, sp, t, h_px, foot, **kw):
    """按 alpha 包围盒高度落脚（脚底中点 → foot）"""
    a, s = sp.fit(h_px)
    return sp.draw(fr, t, a, foot, s, **{**DKW, **kw})


def put_at(fr, sp, t, src, dst, width_px, **kw):
    return sp.draw(fr, t, src, dst, width_px / sp.w, **{**DKW, **kw})


def rgba(name):
    im = cv2.imread(G + name + '_cut.png', cv2.IMREAD_UNCHANGED)
    im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255
    return im[..., :3].copy(), im[..., 3].copy()


def paste_affine(fr, F, A, M, alpha=1.0, blur=0.0, tone=None):
    """小贴图 (F,A) 经 2×3 仿射 M 贴到屏幕，只在落点包围盒内计算"""
    h, w = A.shape
    c = np.float32([[0, 0, 1], [w, 0, 1], [w, h, 1], [0, h, 1]]) @ M.T
    x0, y0 = int(max(0, c[:, 0].min() - 4 - 2 * blur)), int(max(0, c[:, 1].min() - 4 - 2 * blur))
    x1, y1 = int(min(W, c[:, 0].max() + 4 + 2 * blur)), int(min(H, c[:, 1].max() + 4 + 2 * blur))
    if x1 <= x0 or y1 <= y0: return fr, None
    M2 = M.copy(); M2[0, 2] -= x0; M2[1, 2] -= y0
    Fw = cv2.warpAffine(F * A[..., None], M2, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
    Aw = cv2.warpAffine(A, M2, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
    if blur > 0.4:
        Fw = cv2.GaussianBlur(Fw, (0, 0), blur); Aw = cv2.GaussianBlur(Aw, (0, 0), blur)
    if tone is not None:                                   # (目标色, 混合量)：雾里远排 / 剪影
        col, k = tone
        Fw = Fw * (1 - k) + Aw[..., None] * np.asarray(col, np.float32) * k
    Aw = Aw * alpha
    roi = fr[y0:y1, x0:x1]
    fr[y0:y1, x0:x1] = roi * (1 - Aw[..., None]) + Fw * alpha
    return fr, (x0, y0, x1, y1)


def M_foot(w, h, foot_src, foot_dst, scale, rot=0.0, flip=False):
    M = cv2.getRotationMatrix2D((float(foot_src[0]), float(foot_src[1])), rot, scale)
    M[0, 2] += foot_dst[0] - foot_src[0]; M[1, 2] += foot_dst[1] - foot_src[1]
    if flip:
        Fm = np.float32([[-1, 0, w], [0, 1, 0], [0, 0, 1]])
        M = (np.vstack([M, [0, 0, 1]]) @ Fm)[:2]
    return M.astype(np.float32)


# ------------------------------------------------------------------ D 化特效笔触
class InkRain:
    """漫画细雨：细墨线短划（长短、粗细、角度各有变化）；亮底上画墨色、暗底上画白色。avoid=(H,W) 0..1 的避让遮罩（出字帧字周围不落雨）"""
    def __init__(self, seed, n=520, angle=10.0, speed=(1500, 2500), length=(14, 70), par=(0.4, 1.5)):
        r = np.random.default_rng(seed)
        self.x = r.uniform(0, W * 1.3, n); self.y = r.uniform(0, H * 1.5, n)
        self.v = r.uniform(*speed, n); self.l = r.uniform(*length, n) * r.choice([0.6, 1.0, 1.0, 1.6], n)
        self.a = np.radians(angle + r.normal(0, 2.2, n)); self.p = r.uniform(*par, n)
        self.wd = (r.random(n) < 0.22).astype(np.int32) + 1
        self.k = r.uniform(0.45, 1.0, n)

    def draw(self, fr, t, amt=1.0, cam=(0.0, 0.0), avoid=None, frac=1.0, near=None):
        n = int(len(self.x) * frac)
        ux, uy = np.sin(self.a[:n]), np.cos(self.a[:n])
        x = (self.x[:n] + self.v[:n] * t * ux - cam[0] * self.p[:n]) % (W * 1.3) - W * 0.15
        y = (self.y[:n] + self.v[:n] * t * uy - cam[1] * self.p[:n]) % (H * 1.5) - H * 0.25
        L = self.l[:n] * (self.p[:n] if near is None else near)
        buf = np.zeros((H, W), np.float32)
        P = np.round(np.stack([np.stack([x - ux * L, y - uy * L], 1), np.stack([x, y], 1)], 1) * 4).astype(np.int32)
        for wdv in (1, 2):
            for kk in (0.5, 0.8, 1.0):
                m = (self.wd[:n] == wdv) & (np.abs(self.k[:n] - kk) < 0.18)
                if m.any(): cv2.polylines(buf, list(P[m]), False, kk, wdv, cv2.LINE_AA, 2)
        a = np.clip(buf, 0, 1) * amt * 0.62
        if avoid is not None: a = a * (1 - np.clip(avoid, 0, 1))
        lum = fr.mean(-1)
        tgt = np.where(lum < 0.42, 0.90, 0.04).astype(np.float32)[..., None]
        return fr * (1 - a[..., None]) + tgt * a[..., None]


def splash(fr, t, seed, origin, t0, n=60, area=(40, 10), speed=(250, 900), dirc=(0, -1), spread=1.5, grav=1500, red=0.3, life=0.5, size=1.4):
    """白 + 血红溅点（火星 / 水花一律 D 化）"""
    fr = K.sparks(fr, t, seed, origin, n=n, life=life, speed=speed, dirc=dirc, spread=spread, grav=grav, size=size, area=area,
                  color=(0.95, 0.95, 0.95), amt=1.0, t0=t0, burst=True)
    if red > 0:
        fr = K.sparks(fr, t, seed + 7, origin, n=max(4, int(n * red)), life=life, speed=speed, dirc=dirc, spread=spread, grav=grav,
                      size=size + 0.6, area=area, color=REDC, amt=1.0, t0=t0, burst=True)
    return fr


def ink_debris(fr, t, seed, origin, t0, n=50, area=(60, 10), speed=(200, 800), dirc=(0, -1), spread=1.6, grav=1600, life=0.6, size=2):
    """墨点碎屑（碎石 / 泥点）：黑色实心小块，乘性压在画面上"""
    if t < t0 or t > t0 + life * 1.3: return fr
    m = K.sparks(np.zeros((H, W, 3), np.float32), t, seed, origin, n=n, life=life, speed=speed, dirc=dirc, spread=spread, grav=grav,
                 size=size, area=area, color=(1.0, 1.0, 1.0), amt=1.0, t0=t0, burst=True)[..., 0]
    m = np.clip(m * 1.4, 0, 1)
    return fr * (1 - 0.9 * m[..., None]) + m[..., None] * 0.02


def brush_slash(fr, p0, p1, q, width=16, seed=0, fade=1.0, red=1.0, core=1.0):
    """干笔飞白斩痕：一束断续的平行细笔（白芯）+ 血红外晕 + 两侧溅墨；q 0..1 从 p0 划到 p1"""
    if fade <= 0.01 or q <= 0: return fr
    r = np.random.default_rng(seed)
    p0 = np.float32(p0); p1 = np.float32(p1); d = p1 - p0; L = float(np.hypot(*d)); u = d / L; nrm = np.float32([-u[1], u[0]])
    head = p0 + d * q
    buf = np.zeros((H // 2, W // 2), np.float32)
    for i in range(18):
        o = r.normal(0, width * 0.42)
        s0 = r.uniform(0, 0.25)
        segs = np.cumsum(r.uniform(0.04, 0.22, 12)) + s0
        for j in range(0, len(segs) - 1, 2):
            a_, b_ = segs[j] * L, min(segs[j + 1], q) * L
            if a_ >= b_: continue
            pa = (p0 + u * a_ + nrm * o) / 2; pb = (p0 + u * b_ + nrm * o) / 2
            cv2.line(buf, (int(pa[0]), int(pa[1])), (int(pb[0]), int(pb[1])), float(r.uniform(0.5, 1.0)), int(r.integers(1, 3)), cv2.LINE_AA)
    m = cv2.resize(buf, (W, H))
    glow = K.blur_ds(m, 14)
    fr = fr + glow[..., None] * RED * 1.4 * red * fade
    fr = fr * (1 - np.clip(m * 0.9, 0, 1)[..., None] * fade) + (m * core * fade)[..., None] * WHITE * 1.3
    # 溅墨：沿斩痕两侧的黑点
    sp = np.zeros((H // 2, W // 2), np.float32)
    for i in range(40):
        s = r.uniform(0, min(1.0, q)) * L; o = r.normal(0, width * 2.2)
        c = (p0 + u * s + nrm * o) / 2
        cv2.circle(sp, (int(c[0]), int(c[1])), int(r.integers(1, 5)), 1.0, -1, cv2.LINE_AA)
    sp = cv2.resize(sp, (W, H))
    return fr * (1 - 0.85 * sp[..., None] * fade)


def drybrush_trail(fr, pts, widths, seed=0, heat=None, red=1.0):
    """地面刀痕（干笔 + 溅墨）：pts 屏幕折线，widths 各点宽度；heat 0..1 每点白热程度（刀尖附近）"""
    r = np.random.default_rng(seed)
    m = np.zeros((H // 2, W // 2), np.float32); hm = np.zeros_like(m); ink = np.zeros_like(m)
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        w = max(1.0, widths[i])
        for k in range(5):
            o = r.normal(0, w * 0.25)
            if r.random() < 0.18: continue
            cv2.line(m, (int(a[0] / 2), int((a[1] + o) / 2)), (int(b[0] / 2), int((b[1] + o) / 2)), float(r.uniform(0.6, 1.0)),
                     max(1, int(w / 3)), cv2.LINE_AA)
        if heat is not None and heat[i] > 0.02:
            cv2.line(hm, (int(a[0] / 2), int(a[1] / 2)), (int(b[0] / 2), int(b[1] / 2)), float(heat[i]), max(1, int(w / 5)), cv2.LINE_AA)
        if r.random() < 0.6:
            c = (a[0] + r.normal(0, w * 1.2), a[1] + r.normal(0, w * 0.7))
            cv2.circle(ink, (int(c[0] / 2), int(c[1] / 2)), int(r.integers(1, 4)), 1.0, -1, cv2.LINE_AA)
    m = cv2.resize(m, (W, H)); hm = cv2.resize(hm, (W, H)); ink = cv2.resize(ink, (W, H))
    fr = fr * (1 - 0.9 * cv2.dilate(m, np.ones((3, 3), np.uint8))[..., None]) + 0.0
    fr = fr + m[..., None] * RED * 1.15 * red + K.blur_ds(m, 18)[..., None] * RED * 0.6 * red
    fr = fr + hm[..., None] * WHITE * 1.2 + K.blur_ds(hm, 10)[..., None] * WHITE * 0.5
    return fr * (1 - 0.85 * ink[..., None])


def halo_dim(fr, c, r, k):
    """出字帧：字周围压暗（字本身在暗梁 / 暗碑上，不受影响）"""
    if k <= 0.01: return fr
    x, y = K.grid()
    g = np.exp(-(((x - c[0]) / r) ** 2 + ((y - c[1]) / (r * 0.75)) ** 2))
    return fr * (1 - 0.45 * k * g)[..., None]


# ===================================================================== V01 钟楼撞钟（86.19–87.53，86.66 撞钟）
class V01D(Shot):
    T_HIT = 86.66
    BS, BTOP = 0.80, (1290.0, 18.0)        # 钟：精灵顶中点 → 屏幕，缩放
    LIP = (740.0, 650.0)                    # 钟沿接触点（钟精灵源像素）
    RAM_END = (2001.0, 612.0)               # 撞木头（撞木精灵源像素）
    RS = 0.90

    def __init__(self):
        self.P = plate('V01_bg', 1.10)
        self.bell = spr('V01_bell'); self.ram = spr('V01_ram')
        self.rain = InkRain(4706, n=460, angle=12)
        self.dust = np.random.default_rng(4710).uniform(0, 1, (160, 4))

    def contact(self):
        return (self.BTOP[0] + (self.LIP[0] - 1024) * self.BS, self.BTOP[1] + self.LIP[1] * self.BS)

    def ram_off(self, t):
        th = V(self.T_HIT)
        if t < th:
            q = clamp01((t - self.t0) / (th - self.t0))
            return -280 + 290 * q ** 2.6                      # 拉后 → 加速撞上（顶进 10px）
        q = t - th
        if q < 0.10: return 10.0
        q2 = q - 0.10
        return 10 * math.exp(-q2 / 0.06) - 90 * math.sin(min(q2 / 0.34, 1.0) * math.pi * 0.5) * math.exp(-max(0, q2 - 0.34) / 0.6)

    def render(self, t):
        u = self.u(t); e = eio(u)
        th = V(self.T_HIT)
        hk = 0.0 if t < th else math.exp(-(t - th) / 0.35)
        hk2 = 0.0 if t < th else math.exp(-(t - th) / 0.09)
        hkd = 0.0 if t < th + 0.10 else math.exp(-(t - th - 0.10) / 0.35)
        thunder = pulse(t, th + 0.28, 0.18) * (t > th)
        par = 40 * (e - 0.5)                                   # 背景视差（中点为零）
        fr = view(self.P, self.P.shape[1] / 2, self.P.shape[0] / 2, 1.0, 0, -0.35 * par, 0)
        fr = fr * (1 + 0.25 * thunder) + thunder * 0.10
        fr = self.rain.draw(fr, t, 0.7, cam=(par * 0.35, 0), frac=0.5)
        # 钟：撞后被顶开 + 衰减摆动（绕吊点转）
        rt = max(0.0, t - th)
        push = 0.0 if t < th else 18 * (1 - math.exp(-rt / 0.012)) * math.exp(-max(0.0, rt - 0.10) / 0.08)
        osc = 0.0 if t < th else math.sin(rt * 2 * math.pi * 11) * 4 * hk
        swing = 0.0 if t < th else 1.6 * math.sin(rt * 2 * math.pi * 1.6) * math.exp(-rt / 0.9)
        bdst = (self.BTOP[0] + push + osc, self.BTOP[1])
        fr, Ab = put_at(fr, self.bell, t, (0.5, 0.0), bdst, self.bell.w * self.BS, rot=swing, wind_amp=0, breathe=0)
        # 撞木：沿吊绳摆弧
        o = self.ram_off(t); o2 = self.ram_off(t - 1 / 60)
        cx, cy = self.contact()
        lift = -0.0009 * min(o, 0) ** 2
        fr, _ = put_at(fr, self.ram, t, (self.RAM_END[0] / 2048, self.RAM_END[1] / 1152), (cx + o, cy + lift), self.ram.w * self.RS,
                       rot=-0.012 * o, wind_amp=0, breathe=0, mblur=((o - o2) * 2.0, 0))
        hit = (cx + max(o, 0), cy)
        if t >= th:
            BV2 = _bv2()
            for k in range(3):
                if rt > 0.10 * k:
                    rr = 90 + 1500 * (rt - 0.10 * k) ** 0.8
                    fr, edge = BV2.ring_warp(fr, hit if k == 0 else (1290, 600), rr, 30 + 10 * k, 10 * hk, sy=0.85)
                    fr = fr * (1 - edge[..., None] * 0.35 * hk)                # 声波环：墨线
            x, y = K.grid()
            d = np.sqrt((x - hit[0]) ** 2 + ((y - hit[1]) * 1.3) ** 2)
            fr = fr + (np.exp(-(d / 26) ** 2) * 0.8 + np.exp(-(d / 210) ** 2) * 0.12)[..., None] * WHITE * hk2
            fr = splash(fr, t, 4720, hit, th, n=70, area=(10, 30), speed=(400, 1200), dirc=(-0.4, -1), spread=1.0, grav=1300, red=0.35, life=0.45)
            fr = ink_debris(fr, t, 4730, (900, 160), th + 0.03, n=90, area=(700, 30), speed=(20, 120), dirc=(0, 1), spread=0.3, grav=1500, life=0.7, size=1)
        fr = self.rain.draw(fr, t, 1.0, cam=(par, 0))
        dx, dy, dr = shake(t, 2 + 18 * hkd, 13, 471)
        return cam(fr, (1.0 + 0.05 * e) * (1 + 0.015 * hk2), dx, dy, dr), (3 if abs(t - th) < 0.04 else 0)


# ===================================================================== V02 宫城广场顶拍（87.53–89.40，88.905 雷）
class V02D(Shot):
    T_THUNDER = 88.905
    S = 1.22

    def __init__(self):
        P = plate('V02_plaza', self.S)
        h, w = P.shape[:2]; self.h, self.w = h, w
        L = P.mean(-1); yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); self.xx, self.yy = xx, yy
        y0 = 0.36 * h
        m = ((L < 0.22) & (yy > y0)).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
        keep = np.zeros(n, np.uint8); keep[1:] = (st[1:, 4] > 120) & (st[1:, 4] < 40000); m = keep[lab].astype(np.float32)
        self.Ad = cv2.GaussianBlur(cv2.dilate(m, np.ones((5, 5), np.uint8)), (0, 0), 2.5)
        self.persp = np.clip((yy - y0) / (h - y0), 0, 1)
        self.delay = ((cv2.resize(K.fbm(h // 40, w // 40, 4824, 3, 3), (w, h)) - 0.5) * 0.30).astype(np.float32)
        self.P = P
        self.roof = np.clip(1 - yy / (h * 0.30), 0, 1)[..., None]
        self.fg = spr('V02_fg')
        self.rain = InkRain(4810, n=520, angle=-6)
        self.drip = np.random.default_rng(4811).uniform(0, 1, (20, 3))

    def render(self, t):
        u = self.u(t); e = eio(u)
        tl = V(self.T_THUNDER)
        env = 0.0 if t < tl else math.exp(-(t - tl) / 0.28)
        arr = self.t0 + 0.12 + 0.95 * self.persp + self.delay           # 叩首浪：从大殿（远）推向近排
        q = np.clip((t - arr) / 0.30, 0, 1); b = q * q * (3 - 2 * q)
        dy = b * (5 + 20 * self.persp) * self.Ad
        P = cv2.remap(self.P, self.xx, (self.yy - dy).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        P = P * (1 + self.roof * 0.9 * env) + env * 0.15 * self.roof
        ax, ay = self.w * 0.5, self.h * 0.30                          # 顶拍压近：锚点钉在殿门（屏幕位置不动，四周外扩）
        fr = view(P, ax, ay, 1.0 + 0.17 * ein(u, 1.6), 0, 0, 0.30 * H - H / 2)
        BV2 = _bv2(); rt = t - self.t0
        for k in range(2):
            if rt > 0.18 * k:
                rr = 80 + 1500 * (rt - 0.18 * k) ** 0.85
                fr, edge = BV2.ring_warp(fr, (960, 330), rr, 34, 12 * math.exp(-rt / 1.2), sy=0.55)
                fr = fr * (1 - edge[..., None] * 0.30 * math.exp(-rt / 1.0))
        fr = self.rain.draw(fr, t, 1.0, cam=(0, -120 * e))
        # 前景檐角：视差最快、虚焦、滴水（中点为零）
        ox = 300 * (e - 0.5)
        fr, Ae = put_at(fr, self.fg, t, (0.0, 0.0), (-220 + ox, -40), 1300, wind_amp=0, breathe=0, defocus=4.0)
        dbuf = np.zeros((H, W), np.float32)
        for (a, b_, s_) in self.drip:
            x0 = -220 + ox + 120 + a * 760; y0 = 260 + a * 260
            ph = (t * (0.9 + s_) + b_) % 1.0
            yd = y0 + 900 * ph * ph
            cv2.line(dbuf, (int(x0), int(yd)), (int(x0), int(yd + 30 + 50 * ph)), 0.8, 3, cv2.LINE_AA)
        fr = fr * (1 - cv2.GaussianBlur(dbuf, (0, 0), 2)[..., None] * 0.5) + cv2.GaussianBlur(dbuf, (0, 0), 2)[..., None] * 0.3
        if t >= tl: fr = fr * (1 + 0.30 * pulse(t, tl + 0.05, 0.12))
        return fr, (3 if abs(t - tl) < 0.04 else 0)


# ===================================================================== 群臣（V03 / V04 / V05 / V14 共用一张纸扎百官分姿势表）
_FIGS = []


def figs():
    """V03_figs 拆成 6 个单体（从直立到深躬，按 x 排序）：[(F, A, foot_src)]"""
    if not _FIGS:
        F, A = rgba('V03_figs')
        n, lab, st, _ = cv2.connectedComponentsWithStats((A > 0.3).astype(np.uint8), 8)
        idx = [i for i in range(1, n) if st[i, 4] > 50000]
        for i in sorted(idx, key=lambda i: st[i, 0]):
            mk = cv2.dilate((lab == i).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(np.float32)
            ys, xs = np.nonzero((lab == i) & (A > 0.5))
            rows = np.bincount(ys, minlength=A.shape[0]); ok = np.nonzero(rows > 6)[0]
            ya, yb = int(ok.min()), int(ok.max()) + 1
            xa, xb = int(xs.min()), int(xs.max()) + 1
            Fc = F[ya:yb, xa:xb].copy(); Ac = (A * mk)[ya:yb, xa:xb].copy()
            bot = np.nonzero(Ac[-8:].max(0) > 0.5)[0]
            fx = float(bot.mean()) if len(bot) else Ac.shape[1] / 2
            _FIGS.append((Fc, Ac, (fx, float(Ac.shape[0]))))
    return _FIGS


def draw_fig(fr, k, foot, h_px, rot=0.0, flip=False, blur=0.0, tone=None, alpha=1.0):
    Fc, Ac, fs = figs()[k]
    s = h_px / Ac.shape[0]
    M = M_foot(Ac.shape[1], Ac.shape[0], fs, foot, s, rot, False)
    if flip:
        Fc = Fc[:, ::-1]; Ac = Ac[:, ::-1]
        fs2 = (Ac.shape[1] - fs[0], fs[1]); M = M_foot(Ac.shape[1], Ac.shape[0], fs2, foot, s, rot, False)
    return paste_affine(fr, np.ascontiguousarray(Fc), np.ascontiguousarray(Ac), M, alpha, blur, tone)[0]


class V03D(Shot):
    """V03 平视雨中宫院：三排纸扎百官由左向右依次躬身（姿势表逐级切换，不平移），横移 + 雾"""
    def __init__(self):
        self.P = plate('V03_bg', 1.12)
        r = np.random.default_rng(4903)
        self.rows = []
        for row, (n, fy, hh, bl, mist) in enumerate(((9, 690, 200, 2.2, 0.55), (7, 800, 320, 1.0, 0.28), (5, 1010, 520, 0.0, 0.0))):
            for i in range(n):
                if r.uniform() < 0.12: continue
                x_ = -120 + (2200 / n) * (i + 0.5) + r.uniform(-0.35, 0.35) * (2200 / n) + (row % 2) * 60
                dfy = r.uniform(-18, 18) * (1 + row)
                self.rows.append((row, x_, fy + dfy, hh * r.uniform(0.9, 1.1), bl, mist, (x_ + 200) / 2400 * 0.55 + row * 0.05 + r.uniform(-0.1, 0.15),
                                  r.uniform(-2, 2)))
        self.rows.sort(key=lambda q: q[2])
        self.fog = fx2.Fog(4902)
        self.rain = InkRain(4904, n=520, angle=12)

    def render(self, t):
        u = self.u(t); e = eio(u)
        pan = -180 * (e - 0.5)
        fr = view(self.P, self.P.shape[1] / 2, self.P.shape[0] / 2, 1.0, 0, 0.25 * pan, 0)
        fr = self.fog.draw(fr, t, density=0.35, y0=480, y1=880, color=(0.90, 0.90, 0.90), speed=(30, 0), cam=(pan * 0.3, 0))
        par = (0.45, 0.7, 1.0)
        tb = V(CT(20, 4)) - 0.55
        for (row, x_, fy, hh, bl, mist, dl, tj) in self.rows:
            bk = clamp01((t - tb - dl) / 0.45)
            k = int(min(4, math.floor(bk * 4.999)))              # 姿势表：0 直立 … 4 深躬（关键姿势逐级切换）
            fr = draw_fig(fr, k, (x_ + pan * par[row], fy), hh * (1 - 0.04 * k), rot=tj + 0.8 * math.sin(t * 2 + x_),
                          blur=bl, tone=((0.82, 0.82, 0.82), mist) if mist else None)
        fr = self.rain.draw(fr, t, 1.0, cam=(pan, 0))
        return cam(fr, 1.02 + 0.02 * e, 0, 0, 0.6 * e), 0


class V04D(Shot):
    """V04 低机位：四个捧笏的臣子（笏板空白，不刻字），每到「大 局 退 让」字头，对应那个人再低一分头（位移场，不整张平移）；雨珠在笏板上炸开"""
    TAB = [142, 725, 1306, 1930]          # 四块笏板中心（精灵源 x）
    WPX = 2100

    def __init__(self):
        self.sp = spr('V04_hu')
        self.bg = plate('V03_bg', 1.0, 0.55, blur=8)
        self.rain = InkRain(4913, n=500, angle=6)
        x, y = K.grid(); self.x, self.y = x, y
        self.cx = [960 + (c / 2048 - 0.5) * self.WPX for c in self.TAB]

    def render(self, t):
        u = self.u(t)
        tks = [max(V(CT(20, k)), self.t0 + 0.02) for k in (6, 7, 8, 9)]
        fr, Aw = put_at(self.bg.copy(), self.sp, t, (0.5, 0.5), (960, 560 + 14 * eio(u)), self.WPX, wind_amp=0, breathe=0.002)
        x, y = self.x, self.y
        dy = np.zeros((H, W), np.float32)
        for k, tk in enumerate(tks):
            bk = eout(clamp01((t - tk) / 0.22), 3)
            if bk > 0: dy += (34 * bk) * np.exp(-((x - self.cx[k]) / 260) ** 2) * np.clip((y - 100) / 500, 0, 1)
        if dy.max() > 0.5:
            fr = cv2.remap(fr, x, (y - dy).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        fr = fr * (0.80 + 0.30 * np.exp(-(((x - 900) / 900) ** 2 + ((y - 300) / 420) ** 2)))[..., None]
        for k, tk in enumerate(tks):
            fr = splash(fr, t, 4915 + k, (self.cx[k], 330), tk, n=50, area=(50, 8), speed=(200, 700), red=0.0, life=0.4, size=1.2)
        fr = self.rain.draw(fr, t, 1.0)
        hk = max(BK.kick_env(t), max(pulse(t, tk, 0.1) * (t >= tk) for tk in tks))
        dx, dy_, dr = shake(t, 3 + 8 * hk, 11, 404)
        return cam(fr, 1.0 + 0.05 * eio(u) + 0.015 * hk, dx, dy_, dr), (2 if hk > 0.7 else 0)


class V05D(Shot):
    """V05 越过群臣背影：烛光照亮的纸屏风上投着太上皇执杖的影子（剪影精灵 → 投影，随烛焰晃）；前景群臣背影虚焦下沉"""
    def __init__(self):
        self.P = plate('V05_screen', 1.06)
        self.sh = spr('V05_shadow')

    def render(self, t):
        u = self.u(t); e = eio(u)
        fl = 0.92 + 0.08 * math.sin(t * 17) * math.sin(t * 7.3)
        fr = view(self.P, self.P.shape[1] / 2, self.P.shape[0] / 2, 1.0) * fl
        z = np.zeros_like(fr)
        _, Aw = put(z, self.sh, t, 1020, (980 + 14 * math.sin(t * 3), 1050), wind_amp=5, breathe=0)
        Aw = K.blur_ds(Aw, 6 + 2 * math.sin(t * 5), 2)
        fr = fr * (1 - 0.86 * Aw[..., None])
        sink = 140 * e
        for i in (0, 2, 4, 1, 3):
            xx = 80 + i * 440 + (i % 2) * 40
            fr = draw_fig(fr, (i % 2), (xx, 1080 + 340 + sink + 40 * (i % 3)), 1050 + 60 * (i % 2), rot=2 * math.sin(t * 1.5 + i),
                          flip=(i % 2 == 0), blur=6, tone=((0.01, 0.01, 0.01), 0.92))
        return cam(fr, 1.0 + 0.07 * e, 0, -30 * e), 0


class V06D(Shot):
    """V06 屏风后真相：太上皇半张脸被烛光从下照亮（影 → 脸匹配剪辑），冷笑时下巴微抬、慢推"""
    FACE = (1001 / 2048, 463 / 1152)

    def __init__(self):
        self.sp = spr('V06_face')
        self.bg = plate('V05_screen', 1.0, 0.30, blur=10)
        x, y = K.grid(); self.x, self.y = x, y

    def render(self, t):
        u = self.u(t); e = eio(u); x, y = self.x, self.y
        fl = 0.88 + 0.12 * math.sin(t * 19) * math.sin(t * 6.1)
        fr = self.bg + np.exp(-(((x - 960) / 600) ** 2 + ((y - 1150) / 380) ** 2))[..., None] * RED * 0.35 * fl
        fr, _ = put_at(fr, self.sp, t, self.FACE, (930 - 36 * e, 400 - 22 * e), 2050 * (1 + 0.03 * e), rot=-2.2 * e, wind_amp=2, breathe=0.004)
        sway = 90 * math.sin(t * 7.3) + 40 * math.sin(t * 13.1)
        fr = fr * (0.62 + 0.45 * sstep(120, 760, y))[..., None]
        fr = fr * (1 + 0.18 * np.exp(-(((x - 930 - sway) / 380) ** 2 + ((y - 760) / 260) ** 2)))[..., None]
        return cam(fr, 1.0 + 0.11 * e, 30 * e, 0), 0


class V07D(Shot):
    """V07「权」（保留）：暗殿墙上，94.02 烛焰一跳，窗光斜投进来，窗棂木花投下的影就是一个「权」（字是生图画进光斑里的）。
    攥杖的手在左前景（翻转摆位，不压字），攥紧 + 指节发颤；光里浮尘"""
    T_QUAN = 94.02

    def __init__(self):
        self.P = plate('V07_wall', 1.0)
        L = self.P.mean(-1)
        lp = cv2.morphologyEx((L > 0.55).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((61, 61), np.uint8)).astype(np.float32)
        self.lp = cv2.GaussianBlur(lp, (0, 0), 8)[..., None]
        self.sp = spr('V07_grip', flip=True)

    def render(self, t):
        u = self.u(t)
        pq = clamp01((t - (V(self.T_QUAN) - 0.06)) / 0.12)
        fl = 0.86 + 0.14 * math.sin(t * 23) * math.sin(t * 7.1)
        hit = pulse(t, V(self.T_QUAN), 0.15) * (t >= V(self.T_QUAN))
        lit = 0.20 + 0.80 * pq * fl * (1 + 0.35 * hit)
        fr = self.P * (0.28 * (1 - self.lp) + lit * self.lp + 0.72 * (1 - self.lp) * pq)
        fr = K.dust(fr, t, 5203, n=70, amt=0.45 * pq, size=(1, 3), drift=(20, -14), color=(0.95, 0.95, 0.95))
        k = eout(clamp01((t - self.t0) / 0.25), 3)
        tr = 1.6 * math.sin(t * 41) * k
        fr, _ = put_at(fr, self.sp, t, (1058 / 2048, 0.55), (430 + tr, 600 + 0.6 * tr), 1640 * (1.0 + 0.04 * k), rot=2.5 * k, wind_amp=0, breathe=0)
        fr = fr * (0.55 + 0.45 * pq)
        hk = pulse(t, V(self.T_QUAN), 0.1) * (t >= V(self.T_QUAN))
        dx, dy, dr = shake(t, 2 + 8 * hk, 11, 52)
        return cam(fr, 1.0 + 0.16 * eio(u) + 0.03 * hk, dx - 40 * eio(u), dy, dr), (3 if hk > 0.5 else 0)


class V08D(Shot):
    """V08 低机位贴地：雨夜宫阶，太上皇的权杖自上方两记杵地（94.76 / 95.32），石板墨线裂开、水冠炸起；地上不出字"""
    T1, T2 = 94.76, 95.32
    F1, F2 = (680, 760), (1220, 790)

    def __init__(self):
        self.P = plate('V08_floor', 1.05)
        self.sp = spr('V08_staff')
        self.rain = InkRain(5402, n=520, angle=9)
        self.spl = fx2.Splashes(5403)
        self.z0 = np.zeros((H, W), np.float32)

    def foot(self, t):
        T1, T2 = V(self.T1), V(self.T2)
        if t < T1:
            q = clamp01((t - self.t0) / (T1 - self.t0))
            return (self.F1[0], self.F1[1] - 330 * (1 - q ** 2.4)), 8.0, 30 * q
        if t < T2 - 0.24: return self.F1, 8.0, 0.0
        if t < T2:
            q = clamp01((t - (T2 - 0.24)) / 0.24)
            x = self.F1[0] + (self.F2[0] - self.F1[0]) * eio(q); yb = self.F1[1] + (self.F2[1] - self.F1[1]) * q
            return (x, yb - 240 * math.sin(math.pi * q ** 0.8)), 8.0 - 12.0 * q, 20.0 * (1 - abs(2 * q - 1))
        q = t - T2
        return self.F2, -4.0 + 1.0 * math.sin(q * 30) * math.exp(-q / 0.15), 0.0

    def render(self, t):
        u = self.u(t); e = eio(u)
        T1, T2 = V(self.T1), V(self.T2)
        fr = view(self.P, self.P.shape[1] / 2, self.P.shape[0] / 2 + 20, 1.0, 0, 30 * (e - 0.5), 0)
        fr = self.spl.draw(fr, t, y_far=640, y_near=1000, rate=110, size=1.0, amt=0.6, color=WHITE)
        for i, (tk, fp) in enumerate(((T1, self.F1), (T2, self.F2))):
            if t < tk: continue
            p = eout(clamp01((t - tk) / 0.16), 2)
            _, lines = BSF.crack_mask(self.z0, fp, p, seed=5480 + i, n=8, reach=240)
            fr = fr * (1 - np.clip(lines * 1.4, 0, 1)[..., None] * 0.9) + np.roll(lines, -2, 0)[..., None] * 0.18
            fr = fx2.ripples(fr, t, [fp, (fp[0] + 40, fp[1] + 8)], [tk, tk + 0.06], color=WHITE, amt=0.9, flat=0.3, speed=420, life=0.9)
        ft, ang, mb = self.foot(t)
        z = np.zeros_like(fr)
        Rf, Ar = put_at(z, self.sp, t, (0.5, 0.981), ft, 1000, rot=ang, wind_amp=0, breathe=0, mblur=(0, mb))
        x, y = K.grid()
        sh = 2 * ft[1]
        My = (sh - y).astype(np.float32); wob = (np.sin(y * 0.09 + t * 11) * 4).astype(np.float32)
        Rf2 = cv2.remap(Rf, x + wob, My, cv2.INTER_LINEAR); Ra = cv2.remap(Ar, x + wob, My, cv2.INTER_LINEAR)
        f_ = ((y > ft[1]) * 0.35 * np.clip(1 - (y - ft[1]) / 260, 0, 1)).astype(np.float32)[..., None]      # 积水倒影（预乘色）
        fr = fr * (1 - Ra[..., None] * f_) + Rf2 * f_
        fr = fr * (1 - Ar[..., None]) + Rf
        for i, tk in enumerate((T1, T2)):
            fp = self.F1 if i == 0 else self.F2
            fr = splash(fr, t, 5420 + i, (fp[0], fp[1] - 6), tk, n=130, area=(60, 10), speed=(250, 900), spread=1.6, grav=1600, red=0.08, life=0.55)
            fr = ink_debris(fr, t, 5430 + i, fp, tk, n=40, area=(40, 8), speed=(150, 500), spread=2.6, grav=1800, life=0.45, size=2)
        fr = self.rain.draw(fr, t, 1.0)
        gk = max(pulse(t, T1, 0.12) * (t >= T1), pulse(t, T2, 0.14) * (t >= T2))
        dx, dy, dr = shake(t, 14 * gk, 12, 53)
        return cam(fr, 1.02 + 0.06 * e + 0.03 * gk, -40 + 90 * e + dx, dy, dr), (3 if gk > 0.6 else 0)


# ===================================================================== V09–V11 算盘：整句「牺牲多少才算够分量」刻在同一架算盘的梁上（同一刚体层、同一张生图）
class Abacus:
    """生图 V09_abacus（3840×2160，绿幕抠像）。梁上 9 字由生图画好；代码只做：未唱到的字用梁面木纹补平藏起来；
    字头前 1 帧刻出——槽里先白热，再血从上往下灌满（灌满即原图像素）；同时这一字下面那档的下珠整串被拨上梁（停在梁下，算进去了）。"""
    SEGS = [(282, 548), (669, 929), (1060, 1262), (1395, 1642), (1775, 2006), (2154, 2393), (2512, 2769), (2906, 3178), (3308, 3566)]
    RODS = [435, 823, 1225, 1653, 2075, 2458, 2836, 3199, 3498]
    BEAM = (767, 1112)
    LOW = (1322, 1797)          # 下珠整串（源图行）
    UP = (266, 560)             # 上珠
    GAP_LO = 1112 + 6           # 梁下空档起（拨上去后珠顶贴到这里）
    GAP_UP = 761                # 梁上空档止（上珠拨下来后珠底贴到这里）
    HB = 104                    # 每档珠子半宽
    _inst = None

    @classmethod
    def get(cls):
        if cls._inst is None: cls._inst = cls()
        return cls._inst

    def __init__(self):
        F, A = rgba('V09_abacus')
        self.F, self.A = F, A
        self.sh, self.sw = A.shape
        r, g, b = F[..., 0], F[..., 1], F[..., 2]
        red = (((r - np.maximum(g, b)) > 0.18) & (A > 0.5)).astype(np.float32)
        y0, y1 = self.BEAM
        self.glyph = []
        hole = np.zeros_like(A)
        for k, (x0, x1) in enumerate(self.SEGS):
            m = np.zeros_like(A); m[y0:y1, x0 - 10:x1 + 10] = red[y0:y1, x0 - 10:x1 + 10]
            reg = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
            reg[:y0 + 2] = 0; reg[y1 - 2:] = 0
            reg = cv2.GaussianBlur(reg, (0, 0), 2.0)
            mm = cv2.GaussianBlur(m, (0, 0), 0.8)
            self.glyph.append((x0 - 40, x1 + 40, mm, reg))
            hole = np.maximum(hole, reg)
        self.hidden = self._fill(hole)
        self.cols = [self._rod(k) for k in range(9)]

    def _fill(self, hole):
        """藏字：梁面是黑漆 + 横向白丝纹，逐行用同一行无字处的像素补（每字一个取样起点），保持横纹连贯"""
        y0, y1 = self.BEAM
        F = self.F; out = F.copy()
        hb = hole > 0.02
        rng = np.random.default_rng(5409)
        for k, (xa, xb, _, reg) in enumerate(self.glyph):
            st = int(rng.integers(0, 4000))
            for y in range(y0 + 2, y1 - 2):
                xs = np.nonzero(reg[y, xa:xb] > 0.01)[0] + xa
                if not len(xs): continue
                ok = np.nonzero(~hb[y, 200:3640])[0] + 200
                if len(ok) < 50: continue
                out[y, xs] = F[y, ok[(st + np.arange(len(xs))) % len(ok)]]
        h = cv2.GaussianBlur(hole, (0, 0), 1.0)[..., None]
        return F * (1 - h) + out * h

    def _rod(self, k):
        """第 k 档：空档纹理（只有竖杆）+ 上下珠块，供「拨珠」重排"""
        x = self.RODS[k]; xa, xb = x - self.HB, x + self.HB
        F, A = self.F, self.A
        gapF = F[1150:1300, xa:xb]; gapA = A[1150:1300, xa:xb]
        lo = (F[self.LOW[0]:self.LOW[1], xa:xb].copy(), A[self.LOW[0]:self.LOW[1], xa:xb].copy())
        up = (F[self.UP[0]:self.UP[1], xa:xb].copy(), A[self.UP[0]:self.UP[1], xa:xb].copy())
        return dict(xa=xa, xb=xb, gapF=gapF, gapA=gapA, lo=lo, up=up)

    def _tile(self, c, n):
        reps = n // c['gapF'].shape[0] + 1
        return np.tile(c['gapF'], (reps, 1, 1))[:n].copy(), np.tile(c['gapA'], (reps, 1))[:n].copy()

    def set_beads(self, rgb, A, k, lo_up, up_dn):
        """lo_up 0..1：下珠被拨上梁的程度；up_dn 0..1：上珠被拨下梁的程度（像素位移，不是平移整张）"""
        c = self.cols[k]; xa, xb = c['xa'], c['xb']
        if lo_up > 0.002:
            ya, yb = self.GAP_LO, self.LOW[1] + 4
            Fz, Az = self._tile(c, yb - ya)
            d = (self.LOW[0] - self.GAP_LO) * lo_up
            top = int(round(self.LOW[0] - d)) - ya
            bf, ba = c['lo']; n = bf.shape[0]
            Fz[top:top + n] = bf; Az[top:top + n] = ba
            rgb[ya:yb, xa:xb] = Fz; A[ya:yb, xa:xb] = Az
        if up_dn > 0.002:
            ya, yb = self.UP[0] - 2, self.GAP_UP
            Fz, Az = self._tile(c, yb - ya)
            d = (self.GAP_UP - self.UP[1]) * up_dn
            bf, ba = c['up']; n = bf.shape[0]
            top = int(round(self.UP[0] + d)) - ya
            n2 = min(n, Fz.shape[0] - top)
            Fz[top:top + n2] = bf[:n2]; Az[top:top + n2] = ba[:n2]
            rgb[ya:yb, xa:xb] = Fz; A[ya:yb, xa:xb] = Az

    @staticmethod
    def tk(k): return V(CT(22, k))

    def state(self, t, upk=()):
        """当前梁面 + 珠位 + 白热遮罩（源图空间）"""
        rgb = self.hidden.copy(); A = self.A.copy()
        hot = np.zeros(A.shape, np.float32)
        y0, y1 = self.BEAM
        yy = np.arange(y0, y1, dtype=np.float32)[:, None]
        for k in range(9):
            tk = self.tk(k)
            if t >= tk - 0.034:
                xa, xb, m, reg = self.glyph[k]
                ca = clamp01((t - (tk - 0.034)) / 0.067)
                sl = (slice(y0, y1), slice(xa, xb))
                fill = eout(clamp01((t - tk - 0.03) / 0.24), 2)
                xx = np.arange(xa, xb, dtype=np.float32)[None, :]
                front = (y0 + 30) + fill * (y1 - y0 - 40) + 10 * np.sin(xx * 0.05 + k * 1.7)
                wet = np.clip((front - yy) / 8, 0, 1)
                mk = m[sl][..., None]
                cool = clamp01((t - tk) / 0.35)
                white = np.float32(1.0 - 0.75 * cool)                         # 白热 → 冷成暗槽
                groove = self.F[sl] * (1 - mk) + mk * white
                cell = groove * (1 - wet[..., None]) + self.F[sl] * wet[..., None]
                r_ = reg[sl][..., None] * ca
                rgb[sl] = rgb[sl] * (1 - r_) + cell * r_
                hot[sl] += m[sl] * (1 - wet) * (1 - cool) * ca
            # 拨珠：字头前 2 帧起 3 帧内拨上去，略过头再回弹
            q = clamp01((t - (tk - 0.067)) / 0.10)
            if q > 0:
                self.set_beads(rgb, A, k, eout(q, 2), 0.0)
        for k, tu in upk:                                                     # 重拍：上珠整串砸下
            q = clamp01((t - (tu - 0.05)) / 0.06)
            if q > 0: self.set_beads(rgb, A, k, 1.0 if t >= self.tk(k) - 0.067 else 0.0, eout(q, 2))
        return rgb, A, hot

    def glyph_center(self, k):
        x0, x1 = self.SEGS[k]; return (0.5 * (x0 + x1), 0.5 * sum(self.BEAM))

    def homog(self, c, s, yaw=0.0, pitch=-5.0, dst=(960.0, 540.0)):
        """源图点 c 放到屏幕 dst；s = 屏幕像素/源像素；yaw/pitch 度（低机位、左近右远）"""
        yaw = math.radians(yaw); pit = math.radians(pitch); f = 2400.0
        src = np.float32([[0, 0], [self.sw, 0], [self.sw, self.sh], [0, self.sh]])
        dsts = []
        for x, y in src:
            X, Y, Z = (x - c[0]) * s, (y - c[1]) * s, 0.0
            X, Z = X * math.cos(yaw) + Z * math.sin(yaw), -X * math.sin(yaw) + Z * math.cos(yaw)
            Y, Z = Y * math.cos(pit) - Z * math.sin(pit), Y * math.sin(pit) + Z * math.cos(pit)
            kk = f / (f + Z)
            dsts.append([dst[0] + X * kk, dst[1] + Y * kk])
        return cv2.getPerspectiveTransform(src, np.float32(dsts))


class _AbacusShot(Shot):
    """V09/V10/V11 共用：背景板（白纸雨墙 + 血红日）视差 0.3、算盘刚体层、细墨雨（避开梁）、出字白闪 + 血溅 + 震屏"""
    KS = ()                 # 本镜要「卡」的字（字头冲击）
    UPK = ()
    SEED = 5400

    def __init__(self):
        self.ab = Abacus.get()
        self.bg = plate('V09_bg', 1.25)
        self.rain = InkRain(self.SEED, n=420, angle=-8, length=(10, 46))

    def camera(self, t):
        raise NotImplementedError

    def compose(self, t, drop=0.0):
        c, s, yaw, pan = self.camera(t)
        ab = self.ab
        fr = view(self.bg, self.bg.shape[1] / 2, self.bg.shape[0] / 2, 1.0, 0, -0.3 * pan, 0)
        rgb, A, hot = ab.state(t, self.UPK)
        M = ab.homog(c, s, yaw, dst=(960.0, 540.0 + drop))
        Wf = cv2.warpPerspective(rgb, M, (W, H), flags=cv2.INTER_LINEAR)
        Af = cv2.warpPerspective(A, M, (W, H), flags=cv2.INTER_LINEAR)[..., None]
        Hf = cv2.warpPerspective(hot, M, (W, H), flags=cv2.INTER_LINEAR)
        sh = cv2.GaussianBlur(np.roll(Af[..., 0], 26, 0), (0, 0), 20)              # 算盘落在纸墙上的影
        fr = fr * (1 - 0.35 * sh[..., None])
        fr = fr * (1 - Af) + Wf * Af
        # 出字：字周围压暗 + 白热辉光 + 血光（只在字上）
        beam = cv2.warpPerspective(np.pad(np.ones((ab.BEAM[1] - ab.BEAM[0], ab.sw), np.float32),
                                          ((ab.BEAM[0], ab.sh - ab.BEAM[1]), (0, 0))), M, (W, H))
        for k in range(9):
            tk = ab.tk(k); kk = pulse(t, tk, 0.25) * (t >= tk - 0.034)
            if kk > 0.02:
                p = cv2.perspectiveTransform(np.float32([[ab.glyph_center(k)]]), M)[0, 0]
                fr = halo_dim(fr, p, 330 * s / 0.5, kk)
        if Hf.max() > 0.01:
            fr = fr + (K.blur_ds(Hf, 10) * 0.8 + Hf * 0.5)[..., None] * WHITE
            fr = fr + K.blur_ds(Hf, 40)[..., None] * RED * 0.7
        avoid = cv2.dilate(beam, np.ones((25, 25), np.uint8))
        fr = self.rain.draw(fr, t, 1.0, cam=(pan, 0), avoid=avoid)
        for k in self.KS:
            tk = ab.tk(k)
            if tk - 0.034 <= t < tk + 0.6:
                p = cv2.perspectiveTransform(np.float32([[[ab.glyph_center(k)[0], ab.BEAM[0] + 20]]]), M)[0, 0]
                fr = splash(fr, t, self.SEED + 10 + k, (float(p[0]), float(p[1])), tk, n=40, area=(60, 6), speed=(250, 800), dirc=(0.1, -1),
                            spread=1.2, grav=1700, red=0.8, life=0.55, size=1.6)
        return fr, M


class V09D(_AbacusShot):
    """V09 96.07–97.50：牺 牲 多 少 才（每字一记刻 + 灌血 + 拨珠）；镜头跟字向右横移"""
    KS = (0, 1, 2, 3, 4)
    SEED = 5401

    def camera(self, t):
        e = eio(self.u(t))
        cx = 900 + 1000 * e
        return (cx, 940.0), 0.50 + 0.04 * e, 9.0 - 3.0 * e, -500 * (e - 0.5)

    def render(self, t):
        fr, _ = self.compose(t)
        hk = max(pulse(t, V(CT(22, k)), 0.08) * (t >= V(CT(22, k))) for k in self.KS)
        dx, dy, dr = shake(t, 8 * hk, 14, 54)
        return cam(fr, 1.0 + 0.02 * hk, dx, dy, dr), (2 if hk > 0.5 else 0)


class V10D(_AbacusShot):
    """V10 97.50–98.43：贴近梁的中段——算、够刻出；98.373 重拍「算」「够」两档上珠一记砸下，画面震、雨珠炸开"""
    T_HIT = 98.373
    KS = (5, 6)
    SEED = 5501

    def __init__(self):
        super().__init__()
        self.UPK = ((5, V(self.T_HIT)), (6, V(self.T_HIT)))

    def camera(self, t):
        e = eio(self.u(t))
        cx = 2280 + 330 * e
        return (cx, 900.0), 0.78 + 0.04 * e, -6.0 + 2.0 * e, -260 * (e - 0.5)

    def render(self, t):
        fr, M = self.compose(t)
        th = V(self.T_HIT)
        hk = pulse(t, th, 0.15) * (t >= th)
        if t >= th:
            for k in (5, 6):
                p = cv2.perspectiveTransform(np.float32([[[self.ab.RODS[k], self.ab.BEAM[0] - 10]]]), M)[0, 0]
                fr = splash(fr, t, 5510 + k, (float(p[0]), float(p[1])), th, n=90, area=(80, 8), speed=(300, 1200), spread=2.0, red=0.25, life=0.55)
        hk2 = max(hk, max(pulse(t, V(CT(22, k)), 0.08) * (t >= V(CT(22, k))) for k in self.KS))
        dx, dy, dr = shake(t, 26 * hk + 6 * hk2, 14, 55)
        return cam(fr, 1.0 + 0.05 * hk, dx, dy, dr), (4 if hk > 0.5 else 0)


class V11D(_AbacusShot):
    """V11 98.43–99.43：分、量刻出；99.0「量」落定时整架算盘被压得一沉（刚体整体下顿 + 回弹），珠上的雨水震飞；
    随后镜头拉开，整句「牺牲多少才算够分量」血字齐亮在同一根梁上"""
    T_LIANG = 99.0
    KS = (7, 8)
    SEED = 5601

    def camera(self, t):
        th = V(self.T_LIANG)
        e = eio(clamp01((t - self.t0) / (th - self.t0)))
        q = eout(clamp01((t - th - 0.05) / 0.32), 3)
        cx = 2900 + 300 * e
        cx = cx + (1920 - cx) * q
        s = (0.72 + 0.03 * e) * (1 - q) + 0.44 * q
        return (cx, 940.0), s, -8.0 * (1 - q) + 4.0 * q, -300 * (e - 0.5)

    def render(self, t):
        th = V(self.T_LIANG)
        rt = t - th
        drop = 0.0 if rt < 0 else 26 * math.exp(-rt / 0.10) * math.cos(rt * 40) * (rt < 0.5)
        fr, M = self.compose(t, drop)
        if t >= th:
            p = cv2.perspectiveTransform(np.float32([[[3100, self.ab.BEAM[0]]]]), M)[0, 0]
            fr = splash(fr, t, 5606, (float(p[0]), float(p[1])), th, n=150, area=(700, 10), speed=(250, 900), spread=1.7, red=0.15, life=0.6)
        hk = pulse(t, th, 0.14) * (t >= th)
        hk2 = max(hk, max(pulse(t, V(CT(22, k)), 0.08) * (t >= V(CT(22, k))) for k in self.KS))
        dx, dy, dr = shake(t, 20 * hk + 6 * hk2, 13, 56)
        return cam(fr, 1.0 + 0.03 * hk, dx, dy, dr), (4 if hk > 0.5 else 0)


# ===================================================================== V12 名帖纸人被算盘拨落、翻滚着坠下（99.43–100.53；「人」100.39 砸进积水）
class V12D(Shot):
    def __init__(self):
        self.ab = Abacus.get()
        self.bg = plate('V09_bg', 1.15, blur=2.0)
        self.F, self.A = rgba('V12_effigy')
        self.Fs, self.As = cv2.resize(self.F, (512, 288)), cv2.resize(self.A, (512, 288))
        self.rain = InkRain(5703, n=420, angle=4)
        self.cen = (1032.0, 559.0)

    def render(self, t):
        u = self.u(t); e = eio(u)
        fr = view(self.bg, self.bg.shape[1] / 2, self.bg.shape[0] / 2, 1.0, 0, 0, 120 * (e - 0.5))
        # 上方：算盘底框（虚焦）随下摇离开画面
        rgb, A, _ = self.ab.state(t)
        M = self.ab.homog((1920, 1980), 0.55, 0, dst=(960, 60 - 420 * e))
        Wf = cv2.GaussianBlur(cv2.warpPerspective(rgb, M, (W, H)), (0, 0), 7); Af = cv2.GaussianBlur(cv2.warpPerspective(A, M, (W, H)), (0, 0), 7)
        fr = fr * (1 - Af[..., None]) + Wf * Af[..., None]
        for i in range(7):                                                 # 远处更多纸人在坠（灰、小、虚）
            qq = (u * 0.8 + (i * 0.37) % 1.0) % 1.0
            fx = 160 + i * 250 + 40 * math.sin(t * 2 + i)
            Mi = M_foot(512, 288, (256, 144), (fx, -100 + 1300 * qq), (150 + 30 * (i % 3)) / 288, 70 * math.sin(i * 1.7 + t * 1.5) + 150)
            fr = paste_affine(fr, self.Fs, self.As, Mi, 0.7, 3 + 2 * (i % 3), ((0.75, 0.75, 0.75), 0.6))[0]
        T_REN = V(CT(23, 4))
        for k, dt in enumerate((0.09, 0.05, 0.0)):                         # 主纸人 + 两帧残影（翻滚、越来越近）
            tt = t - dt; q = clamp01((tt - self.t0) / (T_REN - self.t0))
            h = 560 + 420 * q ** 1.3
            Mi = M_foot(self.A.shape[1], self.A.shape[0], self.cen, (960 + 80 * q + 40 * math.sin(q * 2.6), 420 + 380 * q), h / 1152,
                        -8 + 40 * q + 6 * math.sin(q * 9))
            fr = paste_affine(fr, self.F, self.A, Mi, (0.15, 0.25, 1.0)[k], (6, 3, 0.6)[k] + 1.0 * q)[0]
        if t >= T_REN:                                                     # 「人」：落进血水，墨血炸开
            o = (1000, 860)
            fr = splash(fr, t, 5709, o, T_REN, n=160, area=(220, 10), speed=(300, 1100), spread=1.2, grav=2400, red=0.9, life=0.45, size=1.6)
            fr = fx2.ripples(fr, t, [o, (o[0] + 30, o[1] + 20)], [T_REN, T_REN + 0.04], color=WHITE, amt=1.0, flat=0.25, speed=520, life=0.6, rings=5)
        fr = self.rain.draw(fr, t * 0.6 + self.t0 * 0.4, 1.0)
        hk = pulse(t, T_REN, 0.10) * (t >= T_REN)
        dx, dy, _ = shake(t, 14 * hk, 14, 571)
        return cam(fr, 1.04 + 0.02 * hk, dx, dy, 2 * u), (3 if hk > 0.5 else 0)


# ===================================================================== V13–V15 雨原（同一张背景板，不同取景）
class V13D(Shot):
    """V13 匹配剪辑：鬼屠单膝砸进泥水（入镜冲击）→ 100.92「曾」字头起身（两个关键姿势硬切 + 起身上移）"""
    def __init__(self):
        self.P = plate('V13_bg', 1.15)
        self.a = spr('V13_kneel'); self.b = spr('V13_rise')
        self.rain = InkRain(5803, n=560, angle=10)
        self.spl = fx2.Splashes(5804)

    def render(self, t):
        u = self.u(t); e = eio(u)
        fr = view(self.P, self.P.shape[1] / 2, self.P.shape[0] / 2 + 40, 1.0, 0, 20 * (e - 0.5), 0)
        ts = V(CT(23, 6))
        if t < ts:
            fr, _ = put(fr, self.a, t, 600, (900, 960), wind_amp=8)
        else:
            k = eout(clamp01((t - ts) / 0.35), 3)
            fr, _ = put(fr, self.b, t, 700 + 40 * k, (900, 960 + 40 * (1 - k)), wind_amp=10, mblur=(0, -30 * (1 - k)))
        tl = self.t0
        if t < tl + 0.45:
            fr = splash(fr, t, 5806, (900, 950), tl - 1 / 30, n=140, area=(300, 10), speed=(300, 900), spread=1.5, red=0.1, life=0.55)
            fr = ink_debris(fr, t, 5807, (900, 955), tl - 1 / 30, n=70, area=(260, 8), speed=(200, 700), spread=1.4, life=0.5, size=3)
        fr = self.spl.draw(fr, t, y_far=820, y_near=1000, rate=120, amt=0.7, color=WHITE)
        fr = self.rain.draw(fr, t, 1.0)
        return cam(fr, 1.0 + 0.18 * e, 0, -60 * e), (3 if abs(t - tl) < 0.04 else 0)


class V14D(Shot):
    """V14 低机位：鬼屠在跪伏的百官中猛然起身（0.3s 拔起站定），102.18「反」脚下气浪一圈泥水冲击环，周围跪着的人被掀得后仰；画面不出字"""
    FOOT = (760, 1040)

    def __init__(self):
        self.P = plate('V13_bg', 1.30)
        self.sp = spr('V14_defy')
        r = np.random.default_rng(5903)
        self.back = [(r.uniform(-50, 1970), r.uniform(770, 800), r.uniform(150, 200)) for _ in range(12)]
        self.front = [(80, 1180, 760, True), (1900, 1180, 760, False)]
        self.rain = InkRain(5905, n=560, angle=8)
        self.spl = fx2.Splashes(5906)

    def render(self, t):
        u = self.u(t); x, y = K.grid()
        fr = view(self.P, self.P.shape[1] * 0.42, self.P.shape[0] * 0.52, 1.0)
        tf = V(CT(23, 10)); tk2 = V(CT(23, 11))
        push = eout(clamp01((t - tf) / 0.5), 2)
        for (bx, fy, hh) in self.back:
            away = 1 if bx > self.FOOT[0] else -1
            fr = draw_fig(fr, 4 if push < 0.3 else 2, (bx, fy), hh, rot=14 * push * away, flip=bx < self.FOOT[0], blur=2.0,
                          tone=((0.80, 0.80, 0.80), 0.45))
        rise = eout(clamp01((t - self.t0) / 0.30), 3)
        fr, _ = put(fr, self.sp, t, 880 * (0.96 + 0.04 * rise), (self.FOOT[0], self.FOOT[1] + 170 * (1 - rise)), wind_amp=12, mblur=(0, 30 * (1 - rise)))
        if t >= tf:
            q = t - tf
            d = np.sqrt((x - self.FOOT[0]) ** 2 + ((y - self.FOOT[1] + 10) * 4.0) ** 2)
            R = 80 + 1800 * eout(clamp01(q / 0.5), 2)
            ring = np.exp(-((d - R) / (10 + 30 * q)) ** 2) * (y > 760) * (1 - clamp01(q / 0.5))
            fr = fr * (1 - 0.6 * ring[..., None])
            fr = splash(fr, t, 5907, (self.FOOT[0], self.FOOT[1] - 10), tf, n=160, area=(260, 10), speed=(300, 1100), spread=2.6, red=0.12, life=0.6)
            fr = ink_debris(fr, t, 5908, (self.FOOT[0], self.FOOT[1] - 10), tf, n=90, area=(240, 10), speed=(300, 1000), spread=2.4, life=0.6, size=3)
        for (fx_, fy, hh, fl) in self.front:
            fr = draw_fig(fr, 4, (fx_ + (-40 if fl else 40) * push, fy), hh, rot=-10 * push * (-1 if fl else 1), flip=fl, blur=9,
                          tone=((0.01, 0.01, 0.01), 0.85))
        fr = self.spl.draw(fr, t, y_far=780, y_near=1000, rate=140, amt=0.7, color=WHITE)
        fr = self.rain.draw(fr, t, 1.0)
        hk = max(pulse(t, tf, 0.12) * (t >= tf), pulse(t, tk2, 0.12) * (t >= tk2))
        dx, dy, dr = shake(t, 3 + 16 * hk, 10, 59)
        return cam(fr, 1.0 + 0.05 * eio(u) + 0.04 * hk, dx, dy, dr), (3 if hk > 0.5 else 0)


class V15D(Shot):
    """V15 暴雨中行走（walk）→ 103.99 闪电（反白一帧 + 墨线闪电），他抬头（look，关键姿势切换）"""
    T_BOLT = 103.987

    def __init__(self):
        self.P = plate('V13_bg', 1.20)
        self.a = spr('V15_walk'); self.b = spr('V15_look')
        self.bolt = fx2.Lightning(6003, p0=(1500, 130), p1=(1700, 700), branches=6)
        self.rain = InkRain(6004, n=620, angle=14)
        self.spl = fx2.Splashes(6005)

    def render(self, t):
        u = self.u(t); e = eio(u)
        tl = V(self.T_BOLT)
        env = 0.0 if t < tl - 0.02 else math.exp(-max(0, t - tl) / 0.3)
        fr = view(self.P, self.P.shape[1] * 0.62, self.P.shape[0] * 0.48, 1.0, 0, -40 * (e - 0.5), 0)
        fr = fr * (1 - 0.25 * env) + 0.25 * env
        if t >= tl - 0.06: fr = self.bolt.draw(fr, t, tl, intensity=1.0, color=(0.98, 0.98, 0.98))
        walk = 1120 - 90 * e; bob = 6 * abs(math.sin(t * 6.5))
        fy = 900
        if t < tl:
            fr, _ = put(fr, self.a, t, 680, (walk, fy - bob), wind_amp=9)
        else:
            fr, _ = put(fr, self.b, t, 690, (walk, fy), wind_amp=11)
        fr = self.spl.draw(fr, t, y_far=830, y_near=1000, rate=160, amt=0.8, color=WHITE)
        fr = self.rain.draw(fr, t, 1.1, cam=(80 * e, 0))
        if 0 <= t - tl < 1 / 30 + 1e-3:                                    # 闪电那一帧：漫画式反白
            lum = fr.mean(-1, keepdims=True)
            fr = np.clip(1.05 - lum, 0, 1) * np.ones(3, np.float32)
        return cam(fr, 1.0 + 0.05 * e, 30 * e, 0, 0.8 * math.sin(t * 1.7)), (3 if abs(t - tl) < 0.04 else 0)


# ===================================================================== V16「天命」碑（保留）：104.34 天雷照碑，105.62 一刀从「天」「命」之间斩断碑身
class V16D(Shot):
    T_SLASH = 105.62
    SC = 0.80

    def __init__(self):
        self.sky = plate('V16_sky', 1.30)
        self.sp = spr('V16_stele')
        self.bolt = fx2.Lightning(6105, p0=(300, 130), p1=(560, 760), branches=5)
        self.rain = InkRain(6104, n=560, angle=6)
        self.cut_y = 1080 - (1151 - 622) * self.SC              # 碑上「天」「命」之间那道缝（源图 y≈622）

    def render(self, t):
        u = self.u(t); x, y = K.grid()
        P = self.sky
        fr = view(P, 1039 * 1.30, 335 * 1.30, 1.0, 6.0 * u, 0, -160)
        tb = V(CT(24, 4))
        env = math.exp(-max(0.0, t - tb) / 0.25) * (t >= tb - 0.02)
        fr = fr * (1 + 0.5 * env)
        if t >= tb - 0.04: fr = self.bolt.draw(fr, t, tb, intensity=0.9, color=(0.98, 0.98, 0.98))
        z = np.zeros_like(fr)
        Fz, Aw = put_at(z, self.sp, t, (0.5, 1151 / 1152), (1000, 1080), 2048 * self.SC, wind_amp=0, breathe=0)
        Fz = Fz * (0.85 + 0.35 * env)
        ts = V(self.T_SLASH)
        p0, p1 = (420, self.cut_y + 8), (1560, self.cut_y - 10)
        if t >= ts:
            q = t - ts
            fall = eout(clamp01(q / 0.22), 2)
            Fz, Aw2, line = BV.split_layer(Fz, Aw, p0, p1, (-50 * fall, 50 * fall + 140 * q * q), (5 * fall, 5 * fall))
            Aw = Aw2
            Fz = Fz + (line * Aw * math.exp(-q / 0.25))[..., None] * WHITE * 1.3
        halo = np.clip(K.blur_ds(Aw, 30) * 1.5 - Aw, 0, 1)                   # 碑沿一圈血红天光
        fr = fr + halo[..., None] * RED * (0.35 + 0.15 * math.sin(t * 3.0))
        fr = fr * (1 - Aw[..., None]) + Fz
        if t >= ts - 0.05:
            ql = clamp01((t - (ts - 0.05)) / 0.10)
            fr = brush_slash(fr, (p0[0] - 400, p0[1] + 30), (p1[0] + 400, p1[1] - 30), ql, width=18, seed=6121, fade=math.exp(-max(0.0, t - ts) / 0.22))
            fr = ink_debris(fr, t, 6120, (1000, self.cut_y), ts, n=80, area=(300, 20), speed=(200, 800), dirc=(0.3, -1), spread=2.0, life=0.7, size=3)
            fr = splash(fr, t, 6122, (1000, self.cut_y), ts, n=60, area=(300, 10), speed=(300, 900), red=0.6, life=0.5)
        fr = self.rain.draw(fr, t, 1.0, avoid=K.blur_ds(Aw, 20) * 0.6)
        hk = pulse(t, ts, 0.14) * (t >= ts)
        dx, dy, dr = shake(t, 3 + 22 * hk, 12, 616)
        return cam(fr, 1.0 + 0.06 * eio(u) + 0.04 * hk, dx, dy + 20 * eio(u), dr), (4 if hk > 0.5 else 0)


# ===================================================================== V17 摊掌承雨 / V18 握拳（同一只手、同一机位：掌 → 拳）
class V17D(Shot):
    PALM = (1048 / 2048, 568 / 1152)
    PC = (965, 600)

    def __init__(self):
        self.bg = plate('V13_bg', 1.0, 1.0, blur=14)
        self.sp = spr('V17_palm')
        F, A = rgba('V17_palm')
        l = F.mean(-1)
        cr = np.clip((cv2.GaussianBlur(l, (0, 0), 5) - l - 0.03) * 12, 0, 1) * (A > 0.9)
        self.cr = cv2.GaussianBlur(cr.astype(np.float32), (0, 0), 1.2)
        self.rain = InkRain(6202, n=380, angle=6)

    def render(self, t):
        u = self.u(t); e = eio(u)
        tm = V(CT(25, 2))
        s0 = clamp01((t - (tm - 0.6)) / 0.6)
        sp = self.sp
        if s0 > 0:                                                         # 掌纹渗血（命字头前后）：红沿掌纹爬开
            sp = copy.copy(self.sp)
            if not hasattr(self, '_crw'):
                self._crw = cv2.resize(self.cr, (self.sp.w, self.sp.h))
            k = (self._crw * min(1.0, s0 * 1.3))[..., None]
            sp.F = (self.sp.F * (1 - k) + k * RED * 0.9).astype(np.float32)
        fr, _ = put_at(self.bg.copy(), sp, t, self.PALM, self.PC, 2050, wind_amp=0, breathe=0.003)
        fr = fx2.ripples(fr, t, [(self.PC[0] - 60, self.PC[1] + 10), (self.PC[0] + 70, self.PC[1] - 30), (self.PC[0], self.PC[1] + 40)],
                         [106.1, 106.7, 107.1], color=WHITE, amt=0.5, flat=0.4, speed=90, life=0.8)
        fr = self.rain.draw(fr, t, 0.8)
        return cam(fr, 1.0 + 0.09 * e, 0, 0, center=self.PC), 0


class V18D(Shot):
    T_WO = 107.58
    FIST = (900, 590)

    def __init__(self):
        self.bg = plate('V13_bg', 1.0, 1.0, blur=14)
        self.palm = spr('V17_palm'); self.fist = spr('V18_fist')
        self.rain = InkRain(6302, n=380, angle=8)

    def render(self, t):
        x, y = K.grid()
        th = V(self.T_WO)
        fr = self.bg.copy()
        if t < th:                                                          # 握拳前 2 帧：手掌一收
            q = clamp01((t - self.t0) / max(th - self.t0, 0.02))
            fr, _ = put_at(fr, self.palm, t, V17D.PALM, V17D.PC, 2050 * (1.09 - 0.06 * q), wind_amp=0, breathe=0)
        else:
            fr, _ = put_at(fr, self.fist, t, (1116 / 2048, 669 / 1152), self.FIST, 1750 * (1.0 - 0.03 * pulse(t, th, 0.12)), wind_amp=0, breathe=0)
            fr = splash(fr, t, 6303, (self.FIST[0] - 20, self.FIST[1] - 280), th, n=120, area=(260, 30), speed=(300, 1100), spread=2.2, red=0.15, life=0.6)
            qq = t - th
            if qq < 0.30:
                d = np.sqrt((x - self.FIST[0]) ** 2 + ((y - self.FIST[1]) * 1.25) ** 2)
                R = 260 + 1400 * eout(qq / 0.30, 2)
                ring = np.exp(-((d - R) / (8 + 40 * qq)) ** 2) * (1 - qq / 0.30)
                fr = fr * (1 - 0.7 * ring[..., None])                         # 墨线冲击环
        fr = self.rain.draw(fr, t, 0.9)
        hk = pulse(t, th, 0.12) * (t >= th)
        dx, dy, dr = shake(t, 16 * hk, 14, 63)
        return cam(fr, 1.02 + 0.04 * hk, dx, dy, dr), (4 if hk > 0.5 else 0)


class V19D(Shot):
    """V19 握刀转身：甩镜入（0.4s 落定 + 运动模糊），马尾甩出雨珠，红带飘"""
    def __init__(self):
        self.P = plate('V13_bg', 1.25, blur=3)
        self.sp = spr('V19_grab')
        self.rain = InkRain(6402, n=560, angle=10)

    def render(self, t):
        u = self.u(t)
        e = eout(clamp01(u * 3.0), 3); whip = 1 - e
        fr = view(self.P, self.P.shape[1] * 0.35, self.P.shape[0] * 0.40, 1.0, 0, 300 * whip, 0)
        if whip > 0.05: fr = K.motion_blur(fr, int(60 * whip), 0)
        fr, _ = put_at(fr, self.sp, t, (0.42, 0.85), (980 - 260 * whip, 1005), 1720, wind_amp=14, mblur=(-55 * whip, 0))
        fr = splash(fr, t, 6404, (640, 300), self.t0 + 0.05, n=40, area=(220, 160), speed=(300, 900), dirc=(-1, -0.2), spread=1.1, grav=900, red=0.0, life=0.45, size=1.0)
        fr = self.rain.draw(fr, t, 1.0, cam=(-300 * whip, 0))
        return cam(fr, 1.02, 0, 0, -2 * whip), 0


# ===================================================================== V20 / V21「黑」「白」（保留）：水面倒影，世界转 180° + 负片
class V20D(Shot):
    """贴水面平视，水线在画面正中 y=540。岸上：雾中城墙 + 低头看倒影的鬼屠（左三分线）+ 一面白幡「黑」（右三分线）；
    水里：鬼屠倒影 + 那面幡的「倒影」是一面倒置的黑幡「白」——黑白在水里颠倒。后半拍起世界开始 roll，V21 转满 180° 后「白」正读、「黑」倒入水中。"""
    WL = 540
    PLATE_WL = 668                        # 背景板水线（源图行，2048 宽）

    def __init__(self):
        P = plate('V20_bg2', 1.0)
        s = W / 2048
        sh = int(round(self.WL - self.PLATE_WL * s))
        self.P = cv2.warpAffine(P, np.float32([[1, 0, 0], [0, 1, sh]]), (W, H), borderMode=cv2.BORDER_REFLECT)
        self.st = spr('V20_stand')
        sp = copy.copy(self.st)                                    # 去掉生图自带的水洼，倒影由代码按水线镜像
        yy = np.arange(sp.h, dtype=np.float32)[:, None]
        cut = 1 - sstep(1020, 1036, yy)
        dark = (sp.F.mean(-1) < 0.45).astype(np.float32)
        keep = np.where(yy < 945, 1.0, dark * cut).astype(np.float32)
        sp.A = (self.st.A * keep).astype(np.float32); sp.ring = (self.st.ring * keep).astype(np.float32)
        SP._UID[0] += 1; sp._uid = SP._UID[0]; sp._supp = None; sp._box = {}
        ys, xs = np.nonzero(sp.A > 0.5); sp.bbox = (xs.min() / sp.w, ys.min() / sp.h, xs.max() / sp.w, ys.max() / sp.h)
        self.st = sp
        self.hei = spr('V20_banner_hei'); self.bai = spr('V20_banner_bai')
        self.rain = InkRain(6504, n=420, angle=2)
        self.r = np.random.default_rng(6505).uniform(0, 1, (34, 3))
        self.wn = K.tile(256, 6506, 6, 3)

    def scene(self, t):
        x, y = K.grid()
        up = self.P.copy()
        up, _ = put(up, self.st, t, 320, (700, self.WL + 4), wind_amp=7)
        up, Ah = put(up, self.hei, t, 400, (1300, self.WL + 2), wind_amp=6, breathe=0)
        # 倒影：上半关于水线翻转 + 涟漪
        nz = cv2.resize(K.tile_crop(self.wn, t * 20, t * 55, H // 8, W // 8), (W, H))
        refl = np.zeros_like(up); refl[self.WL:] = up[self.WL - 1::-1][:H - self.WL]
        # 水里那面幡换成倒置的黑幡「白」（盖住「黑」幡的镜像）
        bz = np.zeros_like(up)
        bz, Ab = put(bz, self.bai, t, 400, (1300, self.WL + 2), wind_amp=6, breathe=0)
        bz = bz[::-1]; Ab = Ab[::-1]
        bz = np.roll(bz, 2 * self.WL - H, 0); Ab = np.roll(Ab, 2 * self.WL - H, 0)
        refl = refl * (1 - Ab[..., None]) + bz
        mx = (x + (nz - 0.5) * 12).astype(np.float32); my = (y + (nz - 0.5) * 5).astype(np.float32)
        refl = cv2.remap(refl, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        low = sstep(self.WL - 1, self.WL + 2, y)[..., None]
        water = self.P * 0.55
        refl = refl * 0.85 + water * 0.15
        fr = up * (1 - low) + refl * low
        fr = fr * (1 - np.exp(-((y - self.WL) / 2.5) ** 2)[..., None] * 0.6)
        cs = [(a * W, self.WL + 30 + b * 400) for a, b, _ in self.r]; ts = [math.floor(t * 2 + c * 2) / 2 - c * 0.5 for _, _, c in self.r]
        fr = fx2.ripples(fr, t, cs, ts, color=WHITE, amt=0.5, flat=0.25, speed=160, life=1.0)
        return self.rain.draw(fr, t, 0.8)

    def render(self, t):
        u = self.u(t)
        fr = self.scene(t)
        ang = 90 * ein(clamp01((u - 0.45) / 0.55), 2)
        fr, = _bv2().roll_pad(fr, ang, 1.0 + 0.06 * eio(u))
        return fr, 0


class V21D(Shot):
    def __init__(self):
        self.v20 = V20D()

    def render(self, t):
        u = self.u(t); e = eio(u)
        fr = self.v20.scene(t)
        BV2 = _bv2()
        fr, = BV2.roll_pad(fr, 90 + 90 * eout(u, 2), 1.04 + 0.04 * (1 - e))
        k = sstep(0.2, 0.55, u)
        return fr * (1 - k) + BV2.neg_grade(fr) * k, 0


# ===================================================================== V22 负片世界里横斩（112.29–113.60，113.34 一刀斩回正片）
class V22D(Shot):
    T_CUT = 113.34

    def __init__(self):
        self.P = plate('V13_bg', 1.15)
        self.a = spr('V22_wind'); self.b = spr('V22_slash')
        self.rain = InkRain(6603, n=560, angle=10)

    def render(self, t):
        u = self.u(t); x, y = K.grid()
        fr = view(self.P, self.P.shape[1] * 0.5, self.P.shape[0] * 0.45, 1.0)
        tc = V(self.T_CUT)
        z = np.zeros_like(fr)
        if t < tc:
            Fz, am = put(z, self.a, t, 820, (960, 1000), wind_amp=10)
        else:
            k = eout(clamp01((t - tc) / 0.06), 2)
            Fz, am = put(z, self.b, t, 820, (960 + 30 * (1 - k), 1000), wind_amp=12, mblur=(60 * (1 - k), 0))
        line_y = 470 + 0.06 * (x - 960)
        m = np.ones((H, W), np.float32) if t < tc else sstep(-6, 6, y - line_y)
        fr = fr * (1 - m[..., None]) + _bv2().neg_grade(fr) * m[..., None]       # 颠倒的是世界：人不反相
        fr = fr * (1 - am[..., None]) + Fz
        fr = self.rain.draw(fr, t, 1.0)
        if t >= tc - 0.05:
            ql = clamp01((t - (tc - 0.05)) / 0.12)
            fr = brush_slash(fr, (-80, 470 - 0.06 * 1040), (2000, 470 + 0.06 * 1040), ql, width=14, seed=6620, fade=math.exp(-max(0.0, t - tc) / 0.30))
        hk = pulse(t, tc, 0.12) * (t >= tc)
        dx, dy, dr = shake(t, 20 * hk, 14, 66)
        return cam(fr, 1.0 + 0.06 * eio(u) + 0.03 * hk, dx, dy, dr), (4 if hk > 0.5 else 0)


# ===================================================================== V23–V25 刀痕划出方向
class V23D(Shot):
    """V23 低机位跟拍：他拖刀前行，刀尖在泥水里犁出一道干笔血痕（刀尖处白热 + 白/血红火星 + 蒸汽），身后的痕迹延伸出画"""
    TIP = (750 / 2048, 1075 / 1152)

    def __init__(self):
        self.P = plate('V23_mud', 1.20)
        self.sp = spr('V23_drag')
        self.fog = fx2.Fog(6702)
        self.rain = InkRain(6703, n=480, angle=8)

    def render(self, t):
        u = self.u(t); e = eio(u)
        pan = -220 * (e - 0.5)
        fr = view(self.P, self.P.shape[1] / 2, self.P.shape[0] * 0.55, 1.0, 0, pan, 0)
        tipx = 640 + 260 * e; gy = 905
        pts = []; ws = []; heat = []
        xs = np.linspace(tipx, -80, 40)
        for i, xx in enumerate(xs):
            pts.append((float(xx), gy + 0.02 * (tipx - xx) + 4 * math.sin(xx * 0.02)))
            ws.append(26 * (1 - 0.5 * i / 40)); heat.append(max(0.0, 1 - i / 6))
        fr = drybrush_trail(fr, pts, ws, seed=6704, heat=heat)
        bob = 5 * abs(math.sin(t * 6.0))
        fr, _ = put_at(fr, self.sp, t, self.TIP, (tipx, gy - bob * 0.2), 2048, wind_amp=10, rot=0.6 * math.sin(t * 3.0))
        fr = K.sparks(fr, t, 6705, (tipx, gy - 5), n=90, life=0.5, speed=(300, 1000), dirc=(-0.6, -1), spread=0.8, grav=1300, size=1.2,
                      area=(20, 10), amt=1.0, color=(0.95, 0.95, 0.95))
        fr = K.sparks(fr, t, 6706, (tipx, gy - 5), n=40, life=0.5, speed=(300, 900), dirc=(-0.6, -1), spread=0.9, grav=1300, size=1.6,
                      area=(20, 10), amt=1.0, color=REDC)
        fr = self.fog.draw(fr, t, density=0.30, y0=620, y1=960, color=(0.92, 0.92, 0.92), speed=(60, -40))
        fr = self.rain.draw(fr, t, 0.9, cam=(pan, 0))
        hk = pulse(t, V(113.64), 0.12) * (t >= V(113.64))
        dx, dy, dr = shake(t, 4 + 12 * hk, 10, 67)
        return cam(fr, 1.04, dx, dy, dr), (3 if hk > 0.5 else 0)


class V24D(Shot):
    """V24 摇臂升高：一道血红刀痕从他脚下沿大道向远方城门疾速延伸（近宽远细）；他是刀痕起点的小小背影"""
    S = 1.0

    def __init__(self):
        self.P = plate('V24_wide', 1.0)
        self.sp = spr('V25_back')
        self.fog = fx2.Fog(6804)
        self.rain = InkRain(6805, n=480, angle=10)

    def render(self, t):
        u = self.u(t); e = eio(u)
        fr = self.P.copy()
        grow = clamp01(u * 1.25 + 0.15)
        y0, y1 = 1080.0, 238.0
        yh = y0 - (y0 - y1) * eout(grow, 1.8)
        n = 60
        pts = []; ws = []; heat = []
        for i in range(n + 1):
            yy = y0 - (y0 - yh) * i / n
            f = (yy - y1) / (y0 - y1)
            pts.append((961 + 14 * (1 - f) + 6 * math.sin(yy * 0.03), yy)); ws.append(2 + 34 * f ** 1.6)
            heat.append(max(0.0, 1 - (n - i) / 5))
        fr = drybrush_trail(fr, pts, ws, seed=6806, heat=heat)
        fr = self.fog.draw(fr, t, density=0.45, y0=60, y1=360, color=(0.92, 0.92, 0.92), speed=(30, 0))
        fr, _ = put(fr, self.sp, t, 300, (880, 1010), wind_amp=8)
        fr = self.rain.draw(fr, t, 1.0)
        return cam(fr, 1.10 - 0.10 * e, 0, 60 - 60 * e), 0


class V25D(Shot):
    """V25 贴地沿刀痕望去：犁沟直指山口；鬼屠背影立在刀痕起点；116.46「向」一记——血光沿刀痕冲向山口；末拍推进压暗，刀痕红线留在画面中线"""
    T_XIANG = 116.46

    def __init__(self):
        self.P = plate('V25_plate', 1.10)
        self.sp = spr('V25_back')
        self.fog = fx2.Fog(6904)
        self.rain = InkRain(6905, n=480, angle=8)
        s = 1.10 * W / 2048
        ox = -(self.P.shape[1] - W) / 2 - 180; oy = -(self.P.shape[0] - H) / 2
        pts = [(1375, 1100), (1258, 1000), (1139, 900), (1143, 800), (1194, 700), (1194, 660)]
        self.furrow = [(px * s + ox, py * s + oy) for px, py in pts]
        self.ox, self.oy = ox, oy

    def render(self, t):
        u = self.u(t); x, y = K.grid()
        fr = cv2.warpAffine(self.P, np.float32([[1, 0, self.ox], [0, 1, self.oy]]), (W, H), borderMode=cv2.BORDER_REFLECT)
        tx = V(self.T_XIANG)
        q = clamp01((t - tx) / 0.45)
        if t >= tx - 0.03:
            P = np.float32(self.furrow); seg = []
            for i in range(len(P) - 1):
                for k in range(12): seg.append(P[i] + (P[i + 1] - P[i]) * k / 12)
            seg = np.float32(seg); hd = int(len(seg) * eout(q, 2))
            buf = np.zeros((H, W), np.float32)
            for i in range(max(0, hd - 14), hd):
                a, b = seg[i], seg[min(i + 1, len(seg) - 1)]
                cv2.line(buf, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), 1.0, max(2, int(22 * (1 - i / len(seg)))), cv2.LINE_AA)
            fade = math.exp(-max(0.0, t - tx - 0.45) / 0.4)
            fr = fr + (K.blur_ds(buf, 20) * 1.1 * fade)[..., None] * RED + (buf * 0.9 * fade)[..., None] * WHITE
            fr = splash(fr, t, 6910, self.furrow[0], tx, n=70, area=(60, 10), speed=(250, 800), red=0.8, life=0.5)
        fr = self.fog.draw(fr, t, density=0.40, y0=430, y1=760, color=(0.92, 0.92, 0.92))
        fr, Am = put(fr, self.sp, t, 600, (640, 960), wind_amp=10)
        fr = self.rain.draw(fr, t, 1.0)
        end = clamp01((t - 117.33) / 0.45)
        fr = fr * (1 - 0.7 * eio(end))
        hk = pulse(t, tx, 0.12) * (t >= tx)
        dx, dy, dr = shake(t, 10 * hk, 12, 69)
        return cam(fr, 1.0 + 0.06 * eio(u) + 0.10 * ein(end, 2), dx, dy, dr, center=(960, 600)), (3 if hk > 0.5 else 0)


def shots():
    out = []
    for i, c in enumerate((V01D, V02D, V03D, V04D, V05D, V06D, V07D, V08D, V09D, V10D, V11D, V12D, V13D, V14D, V15D, V16D, V17D, V18D,
                           V19D, V20D, V21D, V22D, V23D, V24D, V25D)):
        c.__name__ = 'V%02d' % (i + 1)
        out.append(c)
    return out
