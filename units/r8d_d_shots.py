"""units/r8d_d_shots.py — 第八轮风格 D · D 段 30 镜（工具见 units/r8d_d.py）。切点与现版 sec_d_bridge 完全一致。
2:41–2:58（S01–S15）的字全部画在生图里、按演唱时刻揭开；2:58 以后（S16–S30）画面不出任何字。"""
import math
import numpy as np, cv2
import c1kit as K
import d_kit as D
import r8d_d as R
from r8d_d import (V, W, H, BAR, RED, WHT, INKC, SPK, cl, eo, ei, eio, lerp, hit, plate, view, bg_cover, bg_flow, spr, put, put2, warp, pt,
                   GlyphPlate, ink_rain, dry_slash, chips, sparks_d, embers_d, speedlines, flash_inv, shake_cam)

_PL = R._PL
O = {i: D.onsets(i) for i in range(40, 48)}
def tv(li, k): return V(O[li][k])


def tip_of(name, side='top'):
    """精灵最顶端（或最右端）的点在精灵里的归一化坐标（刀尖）"""
    sp = spr(name); A = sp.A > 0.5
    if side == 'top':
        ys = np.where(A.any(1))[0]; y = ys[0] + 4
        while not A[y].any(): y -= 1                                   # 细刀尖 / 孤立点：退回到有像素的行（ys[0] 行必有）
        xs = np.where(A[y])[0]
        return float(xs.mean()) / sp.w, float(y) / sp.h
    xs = np.where(A.any(0))[0]; x = xs[-1] - 4
    while not A[:, x].any(): x += 1
    ys = np.where(A[:, x])[0]
    return float(x) / sp.w, float(ys.mean()) / sp.h


# 刀 / 刀鞘（D19_sword / D19_sheath，同一张生图拆的两层）：源图像素点 → 归一化
SWORD_TIP = (30 / 2048, 857 / 1152); SWORD_GUARD = (1416 / 2048, 256 / 1152)
SWORD_ANG = math.degrees(math.atan2(857 - 256, 1416 - 30))          # 刃的轴线（y 向上为正，刀尖在左下）≈ 23.4°
SWORD_TIP_ANG = 180 + SWORD_ANG                                    # 刀尖指向（≈ 203.4°，即左下）
SHEATH_MOUTH = (1597 / 2048, 477 / 1152); SHEATH_ANG = math.degrees(math.atan2(1022 - 477, 1597 - 136))   # ≈ 20.5°


def spt(name, h, foot, nx, ny):
    """put(name, h, foot) 之后，精灵归一化点 (nx,ny) 在画面上的位置"""
    sp = spr(name); (ax, ay), sc = sp.fit(h)
    return foot[0] + (nx * sp.w - ax * sp.w) * sc, foot[1] + (ny * sp.h - ay * sp.h) * sc


def glow_at(fr, p, r, amt, col=WHT):
    if amt <= 0.01: return fr
    x, y = K.grid()
    g = np.exp(-(((x - p[0]) ** 2 + (y - p[1]) ** 2) / (r * r)))
    return fr + (g * amt)[..., None] * col


def drop(fr, x, y, s=1.0):
    """漫画血滴：墨线描边 + 血红 + 白高光"""
    lay = np.zeros((H, W), np.float32)
    cv2.ellipse(lay, (int(x * 4), int(y * 4)), (int(18 * s * 4), int(24 * s * 4)), 0, 0, 360, 1.0, -1, cv2.LINE_AA, 2)
    tri = np.array([[x - 16 * s, y - 10 * s], [x + 16 * s, y - 10 * s], [x, y - 64 * s]]) * 4
    cv2.fillConvexPoly(lay, tri.astype(np.int32), 1.0, cv2.LINE_AA, 2)
    lay = cv2.GaussianBlur(lay, (0, 0), 0.8)
    ink = np.clip(cv2.dilate(lay, np.ones((5, 5), np.uint8)) - lay, 0, 1)
    fr = fr * (1 - ink[..., None]) + INKC * ink[..., None]
    fr = fr * (1 - lay[..., None]) + RED * 1.1 * lay[..., None]
    hl = np.zeros((H, W), np.float32); cv2.circle(hl, (int(x - 6 * s), int(y - 4 * s)), max(2, int(5 * s)), 1.0, -1, cv2.LINE_AA)
    return fr + cv2.GaussianBlur(hl, (0, 0), 1.2)[..., None] * 0.9


def rings(fr, t, c, th, s=1.0, n=3, col=0.92, aspect=0.32):
    """水面涟漪：白墨线圆环"""
    age = t - th
    if age <= 0: return fr
    L = np.zeros((H // 2, W // 2), np.float32)
    for k in range(n):
        a0 = age - 0.07 * k
        if a0 <= 0: continue
        Rr = (60 + 340 * a0 ** 0.7) * s
        a = math.exp(-age * 1.4) * (1 - 0.22 * k)
        cv2.ellipse(L, (int(c[0] / 2), int(c[1] / 2)), (int(Rr / 2), int(Rr * aspect / 2)), 0, 0, 360, a, max(1, int(3 - k)), cv2.LINE_AA)
    L = cv2.resize(L, (W, H))[..., None]
    return fr * (1 - L) + col * L


# ---------------------------------------------------------------- 字的揭开方式（全部用生图原像素）
def rv_carve(G, k, t, tk, dur=0.22, d=(0.0, 1.0), groove=0.25):
    """刻：两帧凿出暗槽（载体压暗），随后墨 / 血从上往下灌满"""
    if t < tk - 0.067: return None
    if t >= tk + dur * 1.3: return 1.0, None                           # 灌满：直接原图（可缓存）
    ca = cl((t - (tk - 0.067)) / 0.067)
    x0, y0, x1, y1 = G.boxes[k]
    r, _ = G.field(k, eo(cl((t - tk) / dur), 2), d=d, feather=0.14, seed=k)
    C = G.clean[y0:y1, x0:x1]; F = G.F[y0:y1, x0:x1]; ink = G.ink[k][..., None]
    Fg = F * (1 - ink) + C * groove * ink                                # 凹槽态：只有笔画处压暗，笔画外保留生图的刻痕斜面
    alt = Fg * (1 - r[..., None]) + F * r[..., None]
    return ca, alt


def rv_wipe(G, k, t, tk, dur=0.2, d=(0.0, 1.0), feather=0.16):
    """写 / 划：沿笔势方向擦开，tk 后 1 帧写完"""
    p = cl((t - (tk + 0.033 - dur)) / dur)
    if p <= 0: return None
    if p >= 1: return 1.0, None
    r, _ = G.field(k, p, d=d, feather=feather, seed=k)
    return r, None


def rv_stamp(t, tk):
    if t < tk - 0.034: return None
    return cl((t - tk + 0.034) / 0.034), None


_PR = {}
def plate_rgba(G, reveals):
    """揭开状态全是 0/1（没有字正在揭）时按状态缓存整张 RGBA，免得每帧拷一张 4K 浮点图"""
    live = {k: v for k, v in reveals.items() if v is not None}
    done = all(np.isscalar(v[0]) and v[0] >= 1 and v[1] is None for v in live.values())
    key = (G.name, tuple(sorted(live))) if done else None
    if key is not None and key in _PR: return _PR[key]
    img = G.compose(live)
    out = img if G.A is None else np.concatenate([img, G.A[..., None]], -1)
    if key is not None:
        if len(_PR) > 6: _PR.clear()
        _PR[key] = out
    return out


def paste(fr, src4, src_pt, dst, s, rot=0.0):
    """RGBA 源图 src_pt → dst、缩放 s 合到画面；返回 (fr, M)"""
    o, M = warp(src4, src_pt, dst, s, rot)
    if o.shape[2] == 4:
        a = o[..., 3:4]; return fr * (1 - a) + o[..., :3] * a, M
    return o, M


GLYPH_CFG = {
    'stele': ('D02_steles_cut', [(0.15, 0.29, 0.06, 0.88, 5, 'dark', 'v'), (0.43, 0.58, 0.06, 0.88, 5, 'both', 'v'), (0.73, 0.87, 0.06, 0.88, 5, 'dark', 'v')],
              dict(width=3840, thr=0.22, rthr=0.12, grow=25, fill_sig=(30, 30), hp_shift=[(0.065, 0), (-0.065, 0), (0.04, 0.13), (-0.04, -0.13), (0.09, 0.05)])),
    'scale': ('D06_scale_cut', [(0.10, 0.90, 0.17, 0.29, 9, 'dark', 'h')],
              dict(width=3840, thr=0.2, grow=15, fill_sig=(60, 8), hp_shift=[(0.0, 0.035), (0.0, -0.035)])),
    'seals': ('D08_seals', [(0.13, 0.32, 0.04, 0.27, 1, 'seal', 'h'), (0.28, 0.47, 0.19, 0.43, 1, 'seal', 'h'), (0.44, 0.65, 0.34, 0.61, 1, 'seal', 'h'),
                            (0.60, 0.91, 0.51, 0.94, 1, 'seal', 'h')],
              dict(width=2048, rthr=0.2, grow=9, fill_sig=(20, 20), hp_shift=[(0, 0.3), (0, -0.3), (-0.25, 0)])),
    'edict': ('D09_edict', [(0.54, 0.82, 0.18, 0.82, 3, 'dark', 'v'), (0.29, 0.53, 0.22, 0.86, 4, 'dark', 'v')],
              dict(width=3200, thr=0.3, grow=13, fill_sig=(25, 25), hp_shift=[(-0.25, 0), (0.25, 0), (0, 0.3)])),
    'red': ('D11_redpaper', [(0.69, 0.96, 0.02, 0.97, 4, 'red', 'v'), (0.40, 0.68, 0.02, 0.97, 4, 'red', 'v')],
            dict(width=3200, rthr=0.15, grow=13, fill_sig=(25, 25), hp_shift=[(-0.35, 0), (-0.5, 0)])),
    'fun': ('D13_funeral', [(0.83, 0.98, 0.10, 0.92, 4, 'dark', 'v'), (0.66, 0.82, 0.13, 0.30, 1, 'dark', 'v'), (0.66, 0.82, 0.30, 0.72, 2, 'red', 'v'),
                            (0.66, 0.82, 0.72, 0.92, 1, 'dark', 'v'), (0.45, 0.66, 0.17, 0.95, 2, 'red', 'v')],
            dict(width=3200, thr=0.3, rthr=0.15, grow=13, fill_sig=(25, 25), hp_shift=[(-0.4, 0), (-0.55, 0)])),
}
_G = {}
def GP(key):
    if key not in _G:
        c = GLYPH_CFG[key]; _G[key] = GlyphPlate(c[0], c[1], **c[2])
    return _G[key]


class Shot:
    t0 = t1 = 0.0
    def u(self, t): return cl((t - self.t0) / (self.t1 - self.t0))
    @property
    def tm(self): return 0.5 * (self.t0 + self.t1)


# ---------------------------------------------------------------- 碑林（S02–S05 共用同一个刚体层：三块碑 + 15 个刻字）
def stele_state(t):
    G = GP('stele')
    rv = {k: rv_carve(G, k, t, tv(40, k), dur=0.26 if k in (8, 9) else 0.2, groove=0.22) for k in range(15)}
    return G, plate_rgba(G, rv)


def stele_fx(fr, t, G, M, ks, amp=1.0):
    """刻字瞬间：白闪 + 石屑；「牺牲」溅血（发射点跟着碑走）"""
    for k in ks:
        tk = tv(40, k)
        if tk - 0.07 <= t < tk + 0.55:
            cx, cy = G.center(k)
            p = pt(M, cx * G.w, cy * G.h)
            fr = glow_at(fr, p, 90 * amp, 0.9 * K.pulse(t, tk - 0.03, 0.06) * (t >= tk - 0.07))
            fr = chips(fr, t, tk - 0.03, p, 4000 + k, n=34, power=650 * amp, life=0.5)
            if k in (8, 9):
                fr = sparks_d(fr, t, 4100 + k, p, n=40, red_frac=0.7, life=0.5, speed=(200, 700), dirc=(0, -1), spread=1.3,
                              grav=1400, size=2, burst=True, t0=tk, area=(40, 20))
    return fr


class S01_Drop(Shot):
    """ECU 黑水：朱墨两滴落拍（161.77 / 162.21），白墨线涟漪，水下血墨从落点洇开（其余去色）"""
    t0, t1 = 161.31, 162.58
    def __init__(self):
        self.hits = [(V(161.77), (960, 600), 1.0), (V(162.21), (1060, 630), 0.7)]

    def render(self, t):
        u = self.u(t)
        bg, _, _ = view(plate('D01_water'), 0.5, 0.52, 1.0 / (1.0 + 0.08 * eio(u)))
        lum = bg @ np.array([0.3, 0.59, 0.11], np.float32)
        x, y = K.grid()
        m = np.full((H, W), 0.12, np.float32)
        for th, c, s in self.hits:
            age = t - th
            if age <= 0: continue
            Rr = (80 + 900 * eo(age / 1.1, 2)) * s
            d = np.sqrt((x - c[0]) ** 2 + ((y - c[1]) * 2.2) ** 2)
            m = np.maximum(m, np.clip((Rr - d) / 260, 0, 1))
        fr = lum[..., None] * (1 - m[..., None]) + bg * m[..., None]
        for th, c, s in self.hits:
            fr = rings(fr, t, c, th, s)
            if th - 0.3 <= t < th:
                q = (t - (th - 0.3)) / 0.3
                fr = drop(fr, c[0], lerp(140, c[1], q ** 1.7), s)
            fr = sparks_d(fr, t, 1100 + int(s * 10), c, n=40, red_frac=0.5, life=0.45, speed=(250, 750), dirc=(0, -1), spread=0.7,
                          grav=1700, size=2, burst=True, t0=th, area=(20, 4))
            fr = glow_at(fr, c, 70, 0.6 * K.pulse(t, th, 0.05) * (t >= th))
        fr = fr * cl((t - self.t0) / 0.18)
        return shake_cam(fr, t, [h[0] for h in self.hits], amp=6), 0


class S02_Steles(Shot):
    """ELS 白纸虚空：三块巨碑立在地平线上，鬼屠背影拖刀走向碑林；「什」「么」「叫」左碑逐字凿出、灌墨"""
    t0, t1 = 162.58, 164.05
    def render(self, t):
        e = eio(self.u(t))
        G, st = stele_state(t)
        fr, _, _ = view(plate('D02_void'), 0.5 - 0.02 * (e - 0.5), 0.52, 1.0 / (1.02 + 0.03 * e))
        s = lerp(0.33, 0.38, e)
        fr, M = paste(fr, st, (1920 - 260 * e, 2050), (960 - 60 * (e - 0.5), 815), s)
        fr = D.ash(fr, t, 211, n=60, fall=(20, 60), size=(2, 6), amt=0.6, col=(0.08, 0.08, 0.08))
        fr = stele_fx(fr, t, G, M, (0, 1, 2), amp=0.6)
        fr, _ = put(fr, 'D02_walk', t, lerp(250, 228, e), (900 + 30 * e, 975 - 12 * e + 3 * math.sin(t * 7.3)), wind=4)
        return shake_cam(fr, t, [tv(40, k) for k in (0, 1, 2)], amp=7), 1


class S03_TypeSlam(Shot):
    """仰拍近景：左碑「叫大局」——「大」「局」两记凿进碑面（白闪、石屑、墨灌满），镜头逐字下压"""
    t0, t1 = 164.05, 164.98
    def render(self, t):
        e = eio(self.u(t))
        G, st = stele_state(t)
        fr, _, _ = view(plate('D02_void'), 0.30, 0.40, 0.55)
        fr = R.haze(fr, 6)
        cy = lerp(0.50, 0.60, e) * 2160
        fr, M = paste(fr, st, (0.23 * 3840, cy), (900 + 40 * (e - 0.5), 560), lerp(0.70, 0.76, e), rot=-4.0)
        fr = stele_fx(fr, t, G, M, (2, 3, 4), amp=1.2)
        fr = D.ash(fr, t, 311, n=40, fall=(40, 120), size=(3, 9), amt=0.7, col=(0.06, 0.06, 0.06))
        hits = [tv(40, 3), tv(40, 4)]
        return shake_cam(fr, t, hits, amp=14, z=1 + 0.03 * sum(hit(t, h, 0.1) for h in hits)), 1


class S04_Snow(Shot):
    """中碑：「什么叫」连凿三字，镜头下摇到「牺牲」——凿开后灌的是血"""
    t0, t1 = 164.98, 165.88
    def render(self, t):
        e = eio(self.u(t))
        G, st = stele_state(t)
        fr, _, _ = view(plate('D02_void'), 0.6, 0.35, 0.6)
        fr = R.haze(fr, 8)
        fr, M = paste(fr, st, (0.505 * 3840, lerp(0.34, 0.58, e) * 2160), (960, 540), lerp(0.50, 0.56, e), rot=2.0)
        fr = stele_fx(fr, t, G, M, (5, 6, 7, 8, 9), amp=1.0)
        fr = D.ash(fr, t, 411, n=70, fall=(60, 160), size=(2, 8), amt=0.6, col=(0.07, 0.07, 0.07))
        return shake_cam(fr, t, [tv(40, k) for k in (6, 7, 8, 9)], amp=9), 1


class S05_Ren(Shot):
    """右碑：「什么叫」→「忍」最重一凿（反白冲击帧）→「让」；随后拉回全景，三碑十五字刻满；一滴血落向左下（接秤盘朱红小人）"""
    t0, t1 = 165.88, 167.25
    DROP = (560, 760)
    def render(self, t):
        G, st = stele_state(t)
        tr = tv(40, 13)
        q = eio(cl((t - (tv(40, 14) + 0.12)) / 0.45))
        fr, _, _ = view(plate('D02_void'), 0.5 + 0.2 * (1 - q), 0.5 - 0.1 * (1 - q), lerp(0.6, 1.0, q))
        fr = R.haze(fr, 6 * (1 - q))
        u0 = eio(cl((t - self.t0) / (tr - self.t0)))
        cy = lerp(0.36, 0.60, u0) * 2160
        s = lerp(lerp(0.52, 0.58, u0), 0.36, q)
        src = (lerp(0.80, 0.5, q) * 3840, lerp(cy, 2050, q))
        fr, M = paste(fr, st, src, (960, lerp(540, 820, q)), s * (1 + 0.04 * hit(t, tr, 0.1)), rot=lerp(-2.0, 0.0, q))
        fr = stele_fx(fr, t, G, M, (10, 11, 12, 13, 14), amp=1.0 + 0.6 * (t > tr - 0.1))
        fr = D.ash(fr, t, 511, n=60, fall=(40, 120), size=(2, 7), amt=0.6, col=(0.07, 0.07, 0.07))
        if q > 0.3:
            fr, _ = put(fr, 'D02_walk', t, 200, (900, 960), wind=4)
        td = self.t1 - 0.32
        if td <= t < self.t1:
            k = (t - td) / 0.32
            fr = drop(fr, lerp(self.DROP[0] + 80, self.DROP[0], k), lerp(250, self.DROP[1], k ** 1.6), 0.9)
        fr = flash_inv(fr, 1.0 if tr <= t < tr + 0.034 else 0.0)
        return shake_cam(fr, t, [tv(40, k) for k in (11, 12, 13, 14)], amp=10 + 8 * (t > tr - 0.05)), 1


# ---------------------------------------------------------------- 秤（S06 / S07 / S26 同一张图）
def scale_state(t, text=True):
    G = GP('scale')
    if not text: return G, np.concatenate([G.clean, G.A[..., None]], -1)
    rv = {k: rv_carve(G, k, t, tv(41, k), dur=0.18, groove=0.3) for k in range(9)}
    return G, plate_rgba(G, rv)


def scale_fx(fr, t, G, M, ks):
    for k in ks:
        tk = tv(41, k)
        if tk - 0.07 <= t < tk + 0.5:
            cx, cy = G.center(k); p = pt(M, cx * G.w, cy * G.h)
            fr = glow_at(fr, p, 60, 0.7 * K.pulse(t, tk - 0.03, 0.06) * (t >= tk - 0.07))
            fr = chips(fr, t, tk - 0.03, p, 600 + k, n=20, power=420, life=0.45)
    return fr


def ink_people(fr, t, seed, x0, x1, ytop, ybot, n=60, amt=0.9):
    """墨点小人从天倾倒进右盘（黑点拖短线）"""
    r = np.random.default_rng(seed)
    L = np.zeros((H // 2, W // 2), np.float32)
    xs = r.uniform(x0, x1, n); ph = r.random(n); sp = r.uniform(700, 1300, n); sz = r.uniform(2, 5, n)
    hgt = max(1.0, ybot - ytop)
    for i in range(n):
        y = ytop + ((t * sp[i] + ph[i] * hgt) % hgt)
        cv2.line(L, (int(xs[i] / 2), int(y / 2)), (int(xs[i] / 2), int((y - 30) / 2)), 1.0, max(1, int(sz[i] / 2)), cv2.LINE_AA)
    L = cv2.resize(L, (W, H))[..., None] * amt
    return fr * (1 - L) + 0.03 * L


class S06_Scale(Shot):
    """白纸上的巨秤：左盘一个朱红小人，右盘千人；秤梁上逐字刻出「什么叫以一人」；缓推，天上往右盘倾倒墨点小人"""
    t0, t1 = 167.25, 168.62
    def render(self, t):
        e = eio(self.u(t))
        G, st = scale_state(t)
        fr, _, _ = view(plate('D02_void'), 0.5, 0.45, 1.0 / (1.0 + 0.03 * e))
        fr, M = paste(fr, st, (1920, 1250), (960, 600 - 10 * e), lerp(0.47, 0.52, e))
        fr = scale_fx(fr, t, G, M, range(6))
        px0, _ = pt(M, 0.66 * 3840, 0); px1, _ = pt(M, 0.94 * 3840, 0); _, py = pt(M, 0, 0.50 * 2160)
        fr = ink_people(fr, t, 611, px0, px1, BAR - 40, py, n=int(10 + 50 * e))
        return shake_cam(fr, t, [tv(41, k) for k in range(6)], amp=4), 1


class S07_Heap(Shot):
    """右盘近景：墨点小人不断倒进千人堆，秤盘每拍往下一沉；梁上刻出「人换千人」"""
    t0, t1 = 168.62, 169.55
    def render(self, t):
        e = eio(self.u(t))
        G, st = scale_state(t)
        fr, _, _ = view(plate('D02_void'), 0.7, 0.4, 0.7)
        fr = R.haze(fr, 5)
        hits = [tv(41, k) for k in (5, 6, 7, 8)]
        sink = sum(18 * (1 - math.exp(-max(0, t - h) / 0.05)) for h in hits)
        fr, M = paste(fr, st, (0.74 * 3840, 0.43 * 2160), (960 - 30 * e, 560 + sink * 0.6), lerp(0.74, 0.80, e), rot=-1.5)
        fr = scale_fx(fr, t, G, M, (5, 6, 7, 8))
        px0, _ = pt(M, 0.68 * 3840, 0); px1, _ = pt(M, 0.94 * 3840, 0); _, py = pt(M, 0, 0.55 * 2160)
        fr = ink_people(fr, t, 711, px0, px1, BAR - 40, py, n=110)
        return shake_cam(fr, t, hits, amp=8), 1


class S08_Seals(Shot):
    """俯拍宣纸：「理」「所」「应」三方朱印砸下，「当」最大最狠（反白一帧）——印落前影子先压下来，落印纸面一震、墨点四溅"""
    t0, t1 = 169.55, 170.92
    def render(self, t):
        e = eio(self.u(t))
        G = GP('seals')
        img = G.clean.copy()
        rv = {}
        for k in range(4):
            tk = tv(41, 9 + k)
            q = cl((t - (tk - 0.16)) / 0.16)
            if 0 < q < 1:
                x0, y0, x1, y1 = G.boxes[k]
                sh = cv2.GaussianBlur(G.masks[k], (0, 0), 45 * (1 - q) + 8) * (0.08 + 0.32 * q)
                img[y0:y1, x0:x1] *= (1 - sh[..., None])
            rv[k] = rv_stamp(t, tk)
        img = G.compose({k: v for k, v in rv.items() if v is not None}, base=img)
        hits = [tv(41, 9 + k) for k in range(4)]
        cs = [G.center(k) for k in range(4)]
        c = cs[0]; zz = 1.15
        for i in range(3):                                           # 镜头在下一方印落下前移过去（印影先到）
            q = eio(cl((t - (hits[i] + 0.04)) / max(0.05, hits[i + 1] - 0.14 - hits[i] - 0.04)))
            c = (lerp(c[0], cs[i + 1][0], q), lerp(c[1], cs[i + 1][1], q))
        qo = eio(cl((t - (hits[3] + 0.12)) / 0.3))                     # 「当」落定后拉开看四方印
        c = (lerp(c[0], 0.55, qo), lerp(c[1], 0.48, qo)); zz = lerp(zz, 1.0, qo)
        fr, M = warp(img, (c[0] * 2048, c[1] * 1152), (960, 560), zz * 1920 / 2048, rot=lerp(-3.0, 0.0, e), border=cv2.BORDER_REFLECT)
        x, y = K.grid()
        for k, th in enumerate(hits):
            cx, cy = G.center(k); p = pt(M, cx * G.w, cy * G.h)
            amp = 1.6 if k == 3 else 1.0
            fr = D.ink_spray(fr, t, th, p, n=int(40 * amp), seed=800 + k, power=520 * amp)
            if th <= t < th + 0.25:
                a = (t - th) / 0.25
                d = np.sqrt((x - p[0]) ** 2 + (y - p[1]) ** 2)
                ring = np.exp(-((d - (120 + 700 * a) * amp) / 18) ** 2) * (1 - a) * 0.35
                fr = fr * (1 - ring[..., None])
        fr = flash_inv(fr, 0.85 if hits[3] <= t < hits[3] + 0.034 else 0.0)
        z = 1 + 0.02 * sum(hit(t, h, 0.08) * (2 if i == 3 else 1) for i, h in enumerate(hits))
        return shake_cam(fr, t, hits, amp=10, z=z), 1


# ---------------------------------------------------------------- 圣旨（S09 / S10）
def edict_state(t):
    G = GP('edict')
    rv = {}
    for k in range(7):
        r = rv_wipe(G, k, t, tv(42, k), dur=0.2, d=(0.25, 1.0))
        if r is not None: rv[k] = r
    return G, G.compose(rv)


def edict_fx(fr, t, G, M, ks):
    for k in ks:
        tk = tv(42, k)
        if tk - 0.2 <= t < tk + 0.5:
            cx, cy = G.center(k); p = pt(M, cx * G.w, cy * G.h)
            fr = D.ink_spray(fr, t, tk, p, n=26, seed=900 + k, power=300)
    return fr


class S09_Brush(Shot):
    """俯拍黑漆案上的圣旨：浓墨楷书一字一字写出「若正义 / 由」（笔势从上往下擦开、墨点溅）"""
    t0, t1 = 170.92, 171.83
    def render(self, t):
        e = eio(self.u(t))
        G, img = edict_state(t)
        c = (lerp(0.66, 0.50, e) * 3200, lerp(0.42, 0.40, e) * 1800)
        fr, M = warp(img, c, (960, 560), lerp(0.80, 0.70, e), rot=lerp(4, 2, e), border=cv2.BORDER_REFLECT)
        fr = edict_fx(fr, t, G, M, range(4))
        return shake_cam(fr, t, [tv(42, k) for k in range(4)], amp=4), 1


class S10_Giant(Shot):
    """仰拍：太上皇（定妆照）握巨笔从画右压下来，笔锋悬在圣旨上方，「你」「定」「义」随他落笔写完"""
    t0, t1 = 171.83, 172.56
    def render(self, t):
        u = self.u(t); e = eio(u)
        G, img = edict_state(t)
        fr, M = warp(img, (0.42 * 3200, 0.55 * 1800), (720, 640), lerp(0.62, 0.66, e), rot=-6, border=cv2.BORDER_REFLECT)
        fr = edict_fx(fr, t, G, M, (4, 5, 6))
        x, _ = K.grid()
        fr = fr * (0.55 + 0.45 * np.clip(1.0 - x / W * 1.2, 0, 1))[..., None]
        hits = [tv(42, k) for k in (4, 5, 6)]
        lean = eo(u, 2) + 0.15 * sum(hit(t, h, 0.1) for h in hits)
        ps = [pt(M, G.center(k)[0] * G.w, G.center(k)[1] * G.h) for k in (4, 5, 6)]
        tgt = ps[0]
        for i in range(2):
            q = eio(cl((t - hits[i]) / max(0.05, hits[i + 1] - hits[i])))
            tgt = (lerp(tgt[0], ps[i + 1][0], q), lerp(tgt[1], ps[i + 1][1], q))
        tip = (tgt[0] + 40, tgt[1] - 60 + 30 * sum(hit(t, h, 0.08) for h in hits))
        fr, _ = put2(fr, 'D10_emperor', t, (0.19, 0.83), tip, 0.72 + 0.05 * lean, rot=3 - 3 * lean, wind=4)
        return shake_cam(fr, t, hits, amp=8, z=1 + 0.05 * e), 0.5


# ---------------------------------------------------------------- 血书（S11 / S12）
def red_state(t):
    G = GP('red')
    rv = {}
    for k in range(8):
        r = rv_wipe(G, k, t, tv(42, 7 + k), dur=0.1, d=(-0.55, 1.0), feather=0.08)
        if r is not None: rv[k] = r
    return G, G.compose(rv)


def red_fx(fr, t, G, M, ks):
    for k in ks:
        tk = tv(42, 7 + k)
        if tk - 0.1 <= t < tk + 0.5:
            cx, cy = G.center(k); p = pt(M, cx * G.w, cy * G.h)
            fr = D.ink_spray(fr, t, tk, p, n=36, seed=1100 + k, power=520, col=RED)
            fr = glow_at(fr, p, 120, 0.5 * K.pulse(t, tk, 0.05) * (t >= tk))
    return fr


class S11_Answer(Shot):
    """仰拍：鬼屠举刀立在挂起的白纸前，纸上一刀一刀划出血书「谁来定义」（斩痕方向划开 + 血点溅）"""
    t0, t1 = 172.56, 173.66
    def render(self, t):
        e = eio(self.u(t))
        G, img = red_state(t)
        fr, M = warp(img, (0.62 * 3200, 0.5 * 1800), (1050 - 50 * (e - 0.5), 540), 0.62, border=cv2.BORDER_REFLECT)
        fr = red_fx(fr, t, G, M, range(5))
        x, _ = K.grid()
        fr = fr * (1 - 0.35 * np.clip((700 - x) / 600, 0, 1))[..., None]
        fr, _ = put(fr, 'D24_raise', t, 820, (430 + 25 * (e - 0.5), 1010), wind=6)
        return shake_cam(fr, t, [tv(42, 7 + k) for k in range(4)], amp=8, oy=-8 * (e - 0.5)), 1


class S12_Pierce(Shot):
    """血书「你的罪状」近景：「罪」「状」划出，一柄真刀沿斜线冲过画面，「状」落字那一刻纸沿刀线一刀两断"""
    t0, t1 = 173.66, 174.59
    ANG = -27.0
    def render(self, t):
        e = eio(self.u(t))
        G, img = red_state(t)
        fr, M = warp(img, (0.54 * 3200, lerp(0.40, 0.62, e) * 1800), (960, 540), lerp(0.80, 0.86, e), rot=-3, border=cv2.BORDER_REFLECT)
        fr = red_fx(fr, t, G, M, (5, 6, 7))
        th = tv(42, 14)
        ang = math.radians(self.ANG); d = np.array([math.cos(ang), math.sin(ang)]); nrm = np.array([-d[1], d[0]])
        c = np.array([960.0, 600.0])
        if t >= th:
            a = eo(cl((t - th) / 0.25), 2)
            x, y = K.grid()
            sd = (x - c[0]) * nrm[0] + (y - c[1]) * nrm[1]
            off = 26 * a
            A1 = cv2.warpAffine(fr, np.float32([[1, 0, -nrm[0] * off], [0, 1, -nrm[1] * off]]), (W, H), borderMode=cv2.BORDER_REFLECT)
            A2 = cv2.warpAffine(fr, np.float32([[1, 0, nrm[0] * off], [0, 1, nrm[1] * off]]), (W, H), borderMode=cv2.BORDER_REFLECT)
            fr = np.where((sd > 0)[..., None], A2, A1)
            fr = np.where((np.abs(sd) < off)[..., None], np.float32(0.02), fr)
            fr = dry_slash(fr, c - d * 1400, c + d * 1400, 1.0, 1 - a * 0.6, width=10, seed=12)
        q = eo(cl((t - (th - 0.15)) / 0.3), 2)
        if 0 < q:
            tip = c + d * lerp(-1300, 1600, q)
            fr, _ = put2(fr, 'D19_sword', t, SWORD_TIP, (float(tip[0]), float(tip[1])), 1.0, rot=-self.ANG - SWORD_TIP_ANG, wind=0, breathe=0,
                         mblur=(float(d[0] * 30), float(d[1] * 30)))
        fr = flash_inv(fr, 1.0 if th <= t < th + 0.034 else 0.0)
        return shake_cam(fr, t, [tv(42, k) for k in (12, 13, 14)], amp=12), 1


# ---------------------------------------------------------------- 祭文（S13 / S14 / S15）
def fun_state(t):
    G = GP('fun')
    rv = {}
    for k in range(8):
        r = rv_wipe(G, k, t, tv(43, k), dur=0.22 if k not in (5, 6) else 0.32, d=(0.15, 1.0))
        if r is not None: rv[k] = r
    for k in (8, 9):                                                 # 陪葬：火从下往上烧出来
        p = cl((t - (tv(43, k) + 0.033 - 0.3)) / 0.3)
        if p > 0: rv[k] = (G.field(k, p, d=(0.0, -1.0), feather=0.12, seed=k)[0], None)
    return G, G.compose(rv)


def fun_fx(fr, t, G, M, ks):
    for k in ks:
        tk = tv(43, k)
        if tk - 0.2 <= t < tk + 0.5:
            cx, cy = G.center(k); p = pt(M, cx * G.w, cy * G.h)
            fr = D.ink_spray(fr, t, tk, p, n=22, seed=1300 + k, power=260, col=RED if k in (5, 6) else INKC)
    return fr


def burn_fields(t, t_start, speed, seed, base=H - BAR + 40):
    x, y = K.grid()
    key = ('burnn', seed)
    if key not in _PL: _PL[key] = cv2.resize(D._tile(seed)[:H // 8, :W // 8], (W, H), interpolation=cv2.INTER_CUBIC)
    n = _PL[key]
    yf = base - max(0.0, t - t_start) * speed
    f = (yf - y) + (n - 0.5) * 180
    intact = np.clip(f / 5, 0, 1)
    edge = np.exp(-(f / 10) ** 2) * (t > t_start)
    char = np.clip(1 - np.abs(f - 28) / 36, 0, 1) * (f > 0) * (t > t_start)
    return intact, edge, char


class S13_PaperCut(Shot):
    """白纸祭文：右侧竖排「谁又来为」逐字写出，左侧四个朱红剪纸同伴（师兄谢玄洲、师姐丁昭、殷若、徒弟杨不丢，按各自定妆照）立在纸上；镜末脚下起火"""
    t0, t1 = 174.59, 175.96
    def render(self, t):
        e = eio(self.u(t))
        G, img = fun_state(t)
        fr, M = warp(img, (lerp(0.56, 0.60, e) * 3200, 0.52 * 1800), (960, 540), lerp(0.60, 0.64, e), border=cv2.BORDER_REFLECT)
        fr = fun_fx(fr, t, G, M, range(5))
        fr, Ac = put(fr, 'D13_papercut', t, 600, (560 - 30 * (e - 0.5), 900), wind=3, breathe=0.006)
        s = cv2.GaussianBlur(np.roll(Ac, 18, 1), (0, 0), 14) * (1 - Ac)
        fr = fr * (1 - 0.25 * s[..., None])
        ts = self.t1 - 0.35
        if t > ts:
            fr = embers_d(fr, t, 1310, n=int(80 * cl((t - ts) / 0.35)), area=(150, 700, 1000, H - BAR), rise=(120, 300))
        return shake_cam(fr, t, [tv(43, k) for k in range(5)], amp=4), 1


class S14_Burn(Shot):
    """近景：火从剪纸同伴脚下烧上来（焦黑卷边、白热火线、血红余烬），右侧「牺牲」以血写出"""
    t0, t1 = 175.96, 176.87
    def render(self, t):
        e = eio(self.u(t))
        G, img = fun_state(t)
        fr, M = warp(img, (0.64 * 3200, 0.50 * 1800), (1080, 540), 0.95, border=cv2.BORDER_REFLECT)
        fr = fun_fx(fr, t, G, M, (5, 6))
        lay = np.zeros((H, W, 3), np.float32)
        lay, Ac = put(lay, 'D13_papercut', t, 1000, (430 + 30 * (e - 0.5), 1180), wind=3)
        intact, edge, char = burn_fields(t, self.t0 - 0.2, 360, 1401)
        A = (Ac * intact)[..., None]
        fr = fr * (1 - A) + lay / np.maximum(Ac[..., None], 1e-3) * A        # lay 是黑底预乘 alpha，按烧剩部分重新合成
        ca = (char * Ac)[..., None]
        fr = fr * (1 - ca * 0.9) + ca * 0.03
        ea = edge * Ac
        fr = fr + ea[..., None] * WHT * 1.5 + cv2.GaussianBlur(ea, (0, 0), 12)[..., None] * RED * 2.0
        fr = embers_d(fr, t, 1410, n=110, area=(0, 300, 900, H - BAR), rise=(140, 360))
        return shake_cam(fr, t, [tv(43, 6)], amp=6, z=1 + 0.04 * e), 1


class S15_Hole(Shot):
    """整张祭文从左侧烧穿成洞：洞里是余烬与跪地的鬼屠；纸上「陪葬」被火从下往上烧出来；镜头随灰上摇"""
    t0, t1 = 176.87, 178.26
    def render(self, t):
        e = eio(self.u(t))
        G, img = fun_state(t)
        back = bg_flow('D16_embers', t, self.tm, z=1.25, cy=0.55 - 0.05 * e, drift=(0.5, 0, -40), turb=28, seed=15)   # 洞里的烟往上飘
        back, _ = put(back, 'D15_kneel', t, 380, (560, 860), wind=4)
        back = embers_d(back, t, 1510, n=90, area=(150, 300, 1000, H - BAR), rise=(60, 200))
        fr, M = warp(img, (0.56 * 3200, (0.52 - 0.04 * e) * 1800), (960, 540), lerp(0.58, 0.62, e), border=cv2.BORDER_REFLECT)
        fr = fun_fx(fr, t, G, M, (7,))
        x, y = K.grid()
        key = ('holen', 1)
        if key not in _PL: _PL[key] = cv2.resize(D._tile(1501)[:H // 8, :W // 8], (W, H), interpolation=cv2.INTER_CUBIC)
        n = _PL[key]
        Rr = 120 + 420 * eo(cl((t - self.t0) / 0.9), 2)
        d = np.sqrt(((x - 560) / 1.15) ** 2 + (y - 640) ** 2) + (n - 0.5) * 220
        f = Rr - d
        hole = np.clip(f / 4, 0, 1)
        char = np.clip(1 - np.abs(f + 30) / 40, 0, 1) * (f < 0)
        edge = np.exp(-(f / 8) ** 2)
        fr = fr * (1 - hole[..., None]) + back * hole[..., None]
        fr = fr * (1 - char[..., None] * 0.92)
        fr = fr + edge[..., None] * WHT * 1.2 + cv2.GaussianBlur(edge, (0, 0), 14)[..., None] * RED * 1.8
        for k in (8, 9):
            tk = tv(43, k); p = cl((t - (tk + 0.033 - 0.3)) / 0.3)
            if 0 < p < 1:
                _, ed = G.field(k, p, d=(0.0, -1.0), feather=0.12, seed=k)
                x0, y0, x1, y1 = G.boxes[k]
                big = np.zeros((G.h, G.w), np.float32); big[y0:y1, x0:x1] = ed * G.masks[k]
                o = warp(big, (0, 0), pt(M, 0, 0), M[0, 0] if abs(M[0, 1]) < 1e-6 else math.hypot(M[0, 0], M[0, 1]))[0]
                fr = fr + o[..., None] * WHT * 1.4 + cv2.GaussianBlur(o, (0, 0), 10)[..., None] * RED * 2.5
            if tk - 0.1 <= t < tk + 0.8:
                cx, _ = G.center(k); sx = pt(M, cx * G.w, 0)[0]
                fr = embers_d(fr, t, 1520 + k, n=40, area=(int(sx - 220), 150, int(sx + 220), H - BAR), rise=(100, 260))
        fr = D.ash(fr, t, 1530, n=70, fall=(-60, -20), size=(2, 6), amt=0.5, col=(0.15, 0.15, 0.15))
        return shake_cam(fr, t, [tv(43, k) for k in (8, 9)], amp=8, oy=40 * e), 0.6


# ---------------------------------------------------------------- 2:58 以后：画面不出字
class S16_Closed(Shot):
    """余烬里低头闭目的侧脸：灰从上往下落、火星往上飘，一粒余烬飞向下一镜瞳孔的位置"""
    t0, t1 = 178.26, 179.17
    def render(self, t):
        e = eio(self.u(t))
        fr = bg_cover('D02_void', t, self.tm, z=1.25, cy=0.4, par=(-30, 0), blur=3)
        fr = D.embers(fr, t, 1610, n=40, rise=(40, 140), size=(1.5, 4), col=tuple(RED * 1.4))
        fr, _ = put2(fr, 'D16_closed', t, (0.5, 0.5), (1040 + 20 * (e - 0.5), 560), 1.08 + 0.05 * e, wind=5, breathe=0.008)
        fr = D.ash(fr, t, 1611, n=90, fall=(40, 110), size=(2, 6), amt=0.7, col=(0.05, 0.05, 0.05))
        q = cl((t - (self.t1 - 0.45)) / 0.45)
        if q > 0:
            p = (lerp(1500, 0.29 * W, eo(q, 2)), lerp(820, 0.555 * H, eo(q, 2)))
            fr = glow_at(fr, p, 10 + 30 * q, 1.2)
            fr = glow_at(fr, p, 40, 0.6, RED)
        return K.cam(fr, 1.0 + 0.05 * e, 0, 0), 0


class S17_Eye(Shot):
    """ECU 睁眼：瞳孔里一点火；「刀」字头一道白刃寒光横扫过双眼（反白一帧）"""
    t0, t1 = 179.17, 180.09
    def render(self, t):
        e = eio(self.u(t))
        fr = bg_cover('D02_void', t, self.tm, z=1.3, blur=10, gain=0.9)
        op = eo(cl((t - self.t0) / 0.18), 2)
        fr, _ = put2(fr, 'D17_eye', t, (0.39, 0.63), (0.29 * W, 0.555 * H), 1.17 * (1 + 0.05 * e), wind=3, breathe=0)
        fr = glow_at(fr, (0.29 * W, 0.555 * H), 22, 0.7 * op, RED)
        th = tv(44, 6)
        if th - 0.05 <= t < th + 0.3:
            q = cl((t - (th - 0.05)) / 0.12)
            fr = dry_slash(fr, (-100, 640), (2020, 470), q, 1 - cl((t - th) / 0.3), width=14, seed=17, col=WHT, splat=False)
            fr = glow_at(fr, (lerp(-100, 2020, q), lerp(640, 470, q)), 160, 0.8)
        return shake_cam(fr, t, [th], amp=12, z=1.0 + 0.04 * e), 0


class S18_Draw(Shot):
    """中景雨夜：鬼屠侧身缓缓出鞘，寒光沿刃走过；墨线雨，背后黑城墙的裂缝透出血光"""
    t0, t1 = 180.09, 181.0
    def render(self, t):
        e = eio(self.u(t))
        fr = bg_flow('D30_sky', t, self.tm, z=1.6, par=(-20, 0), cx=0.25, cy=0.35, blur=4, drift=(0.506, 45, -12), turb=26, seed=18)   # 云沿裂缝往两侧撕开流动
        fr = ink_rain(fr, t, 1801, n=180, angle=10, amt=0.45)
        fr, A = put(fr, 'D18_draw', t, 960, (1020 + 30 * e, 1050), wind=6)   # D18_draw2 上下贴图边：顶 90 / 底 1050 都离画幅区 ≥30px（呼吸 + 震屏也不露）
        lum = fr.mean(-1)
        steel = A * np.clip((lum - 0.55) / 0.2, 0, 1)
        x, y = K.grid()
        sx = lerp(600, 1700, eio(cl((t - (self.t0 + 0.1)) / 0.6)))
        band = np.exp(-(((x - sx) * 0.8 + (y - 600) * 0.6) / 40) ** 2)
        fr = fr + (steel * band * 1.4)[..., None]
        fr = ink_rain(fr, t, 1802, n=90, angle=10, amt=0.7, length=(40, 110), speed=2600)
        return shake_cam(fr, t, [tv(44, 7), tv(44, 8)], amp=5, z=1 + 0.04 * e), 0


class S19_Forge(Shot):
    """ECU 刃面斜贯全屏、继续出鞘滑动：鞘口擦出白 / 血红火星，「我」「主」「张」三拍各迸一次"""
    t0, t1 = 181.0, 181.91
    def render(self, t):
        e = eio(self.u(t))
        fr = bg_cover('D02_void', t, self.tm, z=1.2, cy=0.62, par=(60, 0), blur=4, gain=1.0)
        fr = D.wash(fr, 0.25, 0.55, 1.0, seed=19)
        ro = 6.0                                                    # 刀鞘轴线在画面上 ≈ 26.5° 斜向右上
        ang = math.radians(SHEATH_ANG + ro); d = np.array([math.cos(ang), -math.sin(ang)])
        mouth = np.array([700.0, 640.0]) + d * 40 * (e - 0.5)        # 鞘口（随镜头微移，中点为零）
        slide = lerp(60, 720, eio(self.u(t)))                       # 刀沿鞘口往右上抽出
        g = mouth + d * slide
        fr, A1 = put2(fr, 'D19_sword', t, SWORD_GUARD, (float(g[0]), float(g[1])), 1.0, rot=ro + SHEATH_ANG - SWORD_ANG,
                      wind=0, breathe=0, mblur=(float(5 * d[0]), float(5 * d[1])))
        fr, A2 = put2(fr, 'D19_sheath', t, SHEATH_MOUTH, (float(mouth[0]), float(mouth[1])), 1.0, rot=ro, wind=3, breathe=0)
        A = np.clip(A1 - A2, 0, 1)
        dst = mouth
        lum = fr.mean(-1)
        x, y = K.grid()
        sx = lerp(300, 1900, cl((t - self.t0) / 0.7))
        band = np.exp(-(((x - sx) * 0.9 + (y - 540) * 0.45) / 50) ** 2)
        fr = fr + (A * np.clip((lum - 0.5) / 0.3, 0, 1) * band * 1.0)[..., None]
        mp = (float(dst[0]), float(dst[1]) + 10)
        for k in (9, 10, 11):
            th = tv(44, k)
            fr = sparks_d(fr, t, 1900 + k, mp, n=70, red_frac=0.4, life=0.6, speed=(500, 1400), dirc=(-0.9, -0.3), spread=0.5,
                          grav=600, size=2, burst=True, t0=th, area=(10, 10))
            fr = glow_at(fr, mp, 120, 0.9 * K.pulse(t, th, 0.05) * (t >= th))
        fr = sparks_d(fr, t, 1950, mp, n=30, red_frac=0.3, life=0.5, speed=(300, 900), dirc=(-0.9, -0.2), spread=0.6, grav=500, size=1)
        return shake_cam(fr, t, [tv(44, k) for k in (9, 10, 11)], amp=7), 0


class S20_Wall(Shot):
    """大仰拍：黑色巨城墙压顶，鬼屠小小的背影站在墙下；「规」「矩」两拍墙缝里血光爆亮、碎石往下掉；镜头沿墙上摇"""
    t0, t1 = 181.91, 182.81
    def render(self, t):
        e = eio(self.u(t))
        fr, _, _ = view(plate('D20_wall'), 0.5, lerp(0.58, 0.48, e), 0.92)
        hits = [tv(45, 3), tv(45, 4)]
        k = sum(hit(t, h, 0.15) for h in hits)
        r = fr[..., 0] - np.maximum(fr[..., 1], fr[..., 2])
        crack = np.clip((r - 0.15) / 0.3, 0, 1)
        fr = np.clip(fr * 1.25 + 0.06, 0, 1) + crack[..., None] * (RED * 1.2 + 0.6 * k) * (0.3 + 0.9 * k)
        fr = fr + cv2.GaussianBlur(crack, (0, 0), 18)[..., None] * RED * 1.5 * k
        for i, h in enumerate(hits):
            fr = chips(fr, t, h, (700 + 500 * i, 300), 2000 + i, n=60, power=500, life=0.7, size=(3, 10))
        fr = ink_rain(fr, t, 2001, n=200, angle=6, amt=0.5)
        fr, _ = put(fr, 'D02_walk', t, 230, (980, 1000 + 40 * (e - 0.5)), wind=6)
        return shake_cam(fr, t, hits, amp=9), 0


class S21_Charge(Shot):
    """鬼屠正面朝镜头冲来，城墙在身后；集中线 + 冲刺推近；183.06 白刃横斩，「我」重拍反白"""
    t0, t1 = 182.81, 183.69
    def render(self, t):
        u = self.u(t); e = eio(u)
        fr = bg_cover('D02_void', t, self.tm, z=1.4, cy=0.45, blur=2, gain=1.0)
        fr = speedlines(fr, t, 2101, c=(960, 520), n=120, amt=0.75, r0=330, col=0.02)
        fr = ink_rain(fr, t, 2102, n=150, angle=6, amt=0.4)
        h = lerp(700, 1050, ei(u, 2))
        fr, _ = put(fr, 'D21_charge', t, h, (960, 1000 + 0.25 * (h - 700)), wind=9, mblur=(0, 6 * u))
        ts = 183.06
        if ts - 0.03 <= t < ts + 0.3:
            q = cl((t - (ts - 0.03)) / 0.1)
            fr = dry_slash(fr, (100, 760), (1820, 380), q, 1 - cl((t - ts) / 0.3), width=24, seed=21, col=WHT)
        return shake_cam(fr, t, [ts, tv(45, 5)], amp=10, z=1.0 + 0.06 * e), 0


class S22_Chuang(Shot):
    """墙裂：血红裂纹爬满墙面，184.18「闯」反白冲击帧，墙从中间炸开，生图碎石扑向镜头，鬼屠从洞里冲出"""
    t0, t1 = 183.69, 184.67
    def render(self, t):
        e = eio(self.u(t))
        th = tv(45, 8)
        wall, _, _ = view(plate('D20_wall'), 0.48, 0.52, 0.55 - 0.05 * e)
        x, y = K.grid()
        q = cl((t - self.t0) / (th - self.t0))
        key = ('cr22',)
        if key not in _PL:
            _PL[key] = [K.crack_path((960, 560), (960 + 1100 * math.cos(a), 560 + 700 * math.sin(a)), 2200 + i, jag=0.06)
                        for i, a in enumerate(np.linspace(0, 2 * math.pi, 9)[:-1])]
        crk = np.zeros((H, W), np.float32)
        for i, pts in enumerate(_PL[key]):
            crk = np.maximum(crk, K.draw_crack((H, W), pts, 4, branches=3, seed=2210 + i, prog=ei(q, 1.5)))
        wall = wall * (1 - crk[..., None] * 0.8) + crk[..., None] * RED * 1.3
        wall = wall + cv2.GaussianBlur(crk, (0, 0), 10)[..., None] * RED * 1.2 * q
        if t < th:
            return shake_cam(wall, t, [tv(45, 6), tv(45, 7)], amp=6 + 8 * q), 0
        a = eo(cl((t - th) / 0.35), 2)
        back, _, _ = view(plate('D30_sky'), 0.5, 0.5, 0.6)
        back, _ = put(back, 'D21_charge', t, lerp(1050, 1350, a), (960, 1050 + 150 * a), wind=10)
        key = ('n22',)
        if key not in _PL: _PL[key] = cv2.resize(D._tile(2230)[:H // 8, :W // 8], (W, H), interpolation=cv2.INTER_CUBIC)
        Rr = 60 + 1500 * a
        d = np.sqrt((x - 960) ** 2 + ((y - 560) * 1.3) ** 2) + (_PL[key] - 0.5) * 300
        hole = np.clip((Rr - d) / 6, 0, 1)
        fr = wall * (1 - hole[..., None]) + back * hole[..., None]
        fr = fr + np.exp(-((Rr - d) / 14) ** 2)[..., None] * WHT * (1 - a)
        deb = spr('D22_debris')
        z = lerp(0.9, 2.6, eo(cl((t - th) / 0.5), 1.5))
        al = 1 - cl((t - th - 0.25) / 0.25)
        if al > 0.01:
            fr, _ = deb.draw(fr, t, (0.5, 0.5), (960, 560), W / deb.w * z, rot=8 * a, wind_amp=0, breathe=0, alpha=al, **SPK)
        fr = sparks_d(fr, t, 2240, (960, 560), n=90, red_frac=0.5, life=0.6, speed=(600, 1800), dirc=(0, -1), spread=3.0,
                      grav=300, size=2, burst=True, t0=th, area=(60, 40))
        fr = flash_inv(fr, 1.0 if t < th + 0.034 else 0.0)
        return shake_cam(fr, t, [th], amp=22, z=1 + 0.05 * hit(t, th, 0.1)), 0


def ridge(fr, seed, y0=884, sag=0.00005, jag=16.0):
    """墨线山脊（静止地面）：黑剪影 + 背光白边 + 几道干笔白丝，左右微微下弯（仰拍的地平线）"""
    key = ('ridge', seed, y0)
    if key not in _PL:
        xs = np.arange(W, dtype=np.float32)
        n = cv2.resize(D._tile(seed)[:1, :64], (W, 1), interpolation=cv2.INTER_CUBIC)[0] - 0.5
        n2 = cv2.resize(D._tile(seed + 1)[:1, :256], (W, 1), interpolation=cv2.INTER_LINEAR)[0] - 0.5
        yl = y0 + sag * (xs - W / 2) ** 2 + n * jag * 3 + n2 * jag * 0.6
        x, y = K.grid()
        ground = np.clip((y - yl[None, :]) / 1.5, 0, 1)
        rim = np.exp(-((y - yl[None, :] + 1.5) / 1.6) ** 2) * (0.55 + 0.45 * np.clip(1 - np.abs(x - W / 2) / (W / 2), 0, 1))
        r = np.random.default_rng(seed)
        hat = np.zeros((H, W), np.float32)
        for _ in range(26):
            xx = r.uniform(0, W); L = r.uniform(30, 140); yy = np.interp(xx, xs, yl) + r.uniform(6, 50)
            cv2.line(hat, (int(xx), int(yy)), (int(xx + L), int(yy + L * 0.04)), r.uniform(0.15, 0.45), 1, cv2.LINE_AA)
        _PL[key] = (ground.astype(np.float32), rim.astype(np.float32), hat * ground)
    g, rim, hat = _PL[key]
    fr = fr * (1 - g[..., None]) + INKC * g[..., None]
    return fr + (rim * 0.9 + hat)[..., None]


class S23_Eye(Shot):
    """大远景仰拍：风暴之眼在天上旋转，小小的背影站在地平线上；185.26 一道白闪电照亮云眼"""
    t0, t1 = 184.67, 185.57
    def render(self, t):
        e = eio(self.u(t))
        fr = bg_flow('D23_storm', t, self.tm, z=1.15, cx=0.6, cy=0.45, gain=0.95, swirl=(0.51, 0.356, 70, 240), turb=34, seed=23)   # 风眼差速旋转（内快外慢、亮云带快）+ 湍流，不是整张旋转
        th = tv(46, 0)
        fr = D.lightning(fr, t, th, (1250, BAR), (1110, 884), seed=231, life=0.2, amt=1.5, col=(1.0, 1.0, 1.0), branches=5, width=3)
        fr = fr * (1 + 0.6 * K.pulse(t, th, 0.06) * (t >= th))
        fr = glow_at(fr, (960, 790), 170, 0.32 + 0.5 * K.pulse(t, th, 0.08) * (t >= th))       # 剪影背后的天光（人物读得出来）
        fr = ridge(fr, 2310)                                                                 # 地平线山脊：人站在地上，不飘在天上
        fr, _ = put(fr, 'D02_walk', t, 170, (960, 892), wind=7, look='sil')
        fr = ink_rain(fr, t, 2301, n=160, angle=14, amt=0.45)
        return shake_cam(fr, t, [th], amp=6, z=1.0 + 0.04 * e), 0


class S24_Defy(Shot):
    """仰拍中景：鬼屠双手举刀向天，雨夜狂风；「不」「判」两拍闪电劈中刀尖（反白一帧）"""
    t0, t1 = 185.57, 186.5
    FOOT, HH = (1000, 1120), 1000
    def render(self, t):
        e = eio(self.u(t))
        fr = bg_flow('D23_storm', t, self.tm, z=1.4, cx=0.62, cy=0.32, blur=3, gain=1.05, par=(0, 30), swirl=(0.51, 0.356, 55, 300), turb=30, seed=24)
        fr = ink_rain(fr, t, 2401, n=160, angle=-12, amt=0.45)
        tp = spt('D24_raise', self.HH, self.FOOT, *tip_of('D24_raise'))
        hits = [tv(46, 1), tv(46, 2)]
        for i, h in enumerate(hits):
            fr = D.lightning(fr, t, h, (tp[0] + 300 - 500 * i, BAR - 30), tp, seed=2410 + i, life=0.18, amt=1.6, col=(1.0, 1.0, 1.0), branches=3, width=3)
        fr, _ = put(fr, 'D24_raise', t, self.HH, self.FOOT, wind=9)
        k = sum(K.pulse(t, h, 0.06) * (t >= h) for h in hits)
        fr = glow_at(fr, tp, 140, 1.4 * k)
        fr = ink_rain(fr, t, 2402, n=80, angle=-12, amt=0.7, length=(50, 120), speed=2800)
        return shake_cam(fr, t, hits, amp=10, z=1.0 + 0.05 * e, oy=-20 * e), 0


class S25_Leap(Shot):
    """背面仰拍：鬼屠跃起向天斜斩，干笔血红斩痕沿 -37° 撕开天幕（接下一镜劈秤）"""
    t0, t1 = 186.5, 187.41
    def render(self, t):
        e = eio(self.u(t))
        fr = bg_flow('D30_sky', t, self.tm, z=1.3, cx=0.62, cy=0.32, drift=(0.506, 80, 10), turb=40, seed=25)   # 斩开天幕：云往两侧急流
        fr = speedlines(fr, t, 2501, c=(1080, 420), n=80, amt=0.5, r0=420, col=0.02)
        ts = tv(46, 3)
        rise = eo(cl((t - self.t0) / 0.35), 2)
        # 两个关键姿势是同一张底图图生图衍生（nano-banana-pro，SPREAD §12-1），用同一个画布变换 → 人物位置 / 透视 / 服装连续不跳
        an, sc = spr('D25_leap').fit(880)
        if t < ts - 0.06:                                            # 关键姿势 1：蓄势收刀、上升（D25_windup）
            fr, _ = put2(fr, 'D25_windup', t, an, (800, 1010 + 120 * (1 - rise)), sc, rot=-4 + 3 * (1 - rise), wind=9, mblur=(0, -8 * (1 - rise)))
        else:                                                        # 关键姿势 2：斜斩（字头硬切；D25_leap2 整把直刀连穗在图内）
            fr, _ = put2(fr, 'D25_leap', t, an, (800, 1010), sc, rot=-4, wind=9)
        q = cl((t - (ts - 0.06)) / 0.12)
        ang = math.radians(-37); d = np.array([math.cos(ang), math.sin(ang)]); c = np.array([1080.0, 420.0])
        fr = dry_slash(fr, c - d * 1100, c + d * 1100, q, 1.0, width=30, seed=25, col=RED)
        return shake_cam(fr, t, [ts], amp=12, z=1 + 0.04 * e), 0


class S26_Judge(Shot):
    """血红余烬里那架秤（梁上已无字）：斩线沿 -37° 劈下，「判」字头秤一刀两断，两半沿法线错开，缝里白热、火星喷；最后 3 帧黑场憋气"""
    t0, t1 = 187.41, 188.34
    def render(self, t):
        e = eio(self.u(t))
        if t >= self.t1 - 0.1: return np.zeros((H, W, 3), np.float32), 0
        fr = bg_flow('D16_embers', t, self.tm, z=1.1, gain=0.7, blur=2, drift=(0.5, 0, -45), turb=30, seed=26)   # 烟往上飘
        G, st = scale_state(t, text=False)
        lay, M = warp(st, (1920, 1150), (1000, 600), 0.50 * (1 + 0.03 * e))
        th = tv(46, 5)
        ang = math.radians(-37); d = np.array([math.cos(ang), math.sin(ang)]); nrm = np.array([-d[1], d[0]])
        c = np.array([1080.0, 420.0])
        x, y = K.grid()
        sd = (x - c[0]) * nrm[0] + (y - c[1]) * nrm[1]
        a = eo(cl((t - th) / 0.3), 2) if t >= th else 0.0
        if a > 0:
            off = 60 * a
            A1 = cv2.warpAffine(lay, np.float32([[1, 0, nrm[0] * off - d[0] * 20 * a], [0, 1, nrm[1] * off - d[1] * 20 * a]]), (W, H))
            A2 = cv2.warpAffine(lay, np.float32([[1, 0, -nrm[0] * off + d[0] * 20 * a], [0, 1, -nrm[1] * off + d[1] * 20 * a]]), (W, H))
            lay = np.where((sd > 0)[..., None], A1, A2)
        al = lay[..., 3:4]
        fr = fr * (1 - al) + lay[..., :3] * al
        q = cl((t - self.t0) / (th - self.t0))
        fr = dry_slash(fr, c - d * 1300, c + d * 1300, q, 1.0 if t < th else 1 - 0.7 * a, width=16 + 30 * a, seed=26, col=RED)
        if t >= th:
            gl = np.exp(-(sd / (6 + 18 * a)) ** 2)
            fr = fr + gl[..., None] * WHT * 1.3 * (1 - 0.5 * a)
            for i in range(3):
                pp = c + d * (-500 + 500 * i)
                fr = sparks_d(fr, t, 2610 + i, (float(pp[0]), float(pp[1])), n=60, red_frac=0.5, life=0.7, speed=(300, 1100),
                              dirc=(float(nrm[0]), float(nrm[1])), spread=1.4, grav=500, size=2, burst=True, t0=th, area=(30, 30))
            fr = embers_d(fr, t, 2620, n=int(120 * a), rise=(60, 200))
        fr = flash_inv(fr, 1.0 if th <= t < th + 0.034 else 0.0)
        return shake_cam(fr, t, [th], amp=18), 0


class S27_Bullet(Shot):
    """CU 子弹时间：雨滴悬停，插地的刀与按在刀柄上的手静立其中，镜头缓慢环绕；189.00「刀」寒光沿刃一闪"""
    t0, t1 = 188.34, 189.71
    def render(self, t):
        e = eio(self.u(t))
        fr = bg_cover('D02_void', t, self.tm, z=1.3, cy=0.55, blur=6, gain=0.95, par=(-50, 0))
        fr = D.droplets(fr, t, 2701, n=150, frozen=True, orbit=-(e - 0.5) * 0.8, focus=0.2)
        fr, A = put(fr, 'D27_planted', t, 960, (980 + 60 * (e - 0.5), 1010), wind=5, breathe=0)
        th = tv(47, 0)
        lum = fr.mean(-1)
        _, y = K.grid()
        sy = lerp(BAR, H - BAR, cl((t - th) / 0.3))
        band = np.exp(-((y - sy) / 50) ** 2) * ((t >= th) and (t < th + 0.35))
        fr = fr + (A * np.clip((lum - 0.45) / 0.3, 0, 1) * band * 1.6)[..., None]
        fr = D.droplets(fr, t, 2702, n=60, frozen=True, orbit=-(e - 0.5) * 1.6, focus=0.9)
        return shake_cam(fr, t, [th], amp=4, z=1.0 + 0.06 * e), 0


class S28_Spin(Shot):
    """回旋斩：前 0.2s 旋入带残影，之后姿态定住；「我」那一拍悬停的雨滴被刀圈全部炸开（白 + 血红火星）"""
    t0, t1 = 189.71, 190.61
    def render(self, t):
        e = eio(self.u(t))
        fr = bg_flow('D30_sky', t, self.tm, z=1.5, cx=0.22, cy=0.32, blur=3, drift=(0.506, 50, 0), turb=30, seed=28)
        th = tv(47, 3)
        fr = D.droplets(fr, t, 2801, n=180, frozen=True, burst=(th, (960, 600)), focus=0.5)
        q = eo(cl((t - self.t0) / 0.2), 2)
        if q < 1:
            for k in range(4, 0, -1):
                fr, _ = put(fr, 'D28_spin', t, 880, (960 + 70 * k * (1 - q), 1040), rot=-12 * k * (1 - q), alpha=0.18, wind=0)
        fr, _ = put(fr, 'D28_spin', t, 880, (960, 1040), rot=-10 * (1 - q), wind=8, mblur=(30 * (1 - q), 0))
        fr = sparks_d(fr, t, 2810, (960, 640), n=80, red_frac=0.5, life=0.6, speed=(500, 1500), dirc=(1, 0), spread=3.0, grav=200,
                      size=2, burst=True, t0=th, area=(300, 40))
        return shake_cam(fr, t, [th], amp=14, z=1.0 + 0.04 * e), 0


class S29_Thrust(Shot):
    """背面仰拍：鬼屠立在乱石上把刀直刺入云；「来」那一拍刀尖迸出一道白光，云层从刀尖处往上裂开"""
    t0, t1 = 190.61, 191.54
    FOOT, HH = (900, 1110), 860
    def render(self, t):
        e = eio(self.u(t))
        fr = bg_flow('D23_storm', t, self.tm, z=1.2, cx=0.25, cy=0.35, gain=1.05, par=(0, 25), swirl=(0.51, 0.356, 45, 300), turb=28, seed=29)
        tp = spt('D29_thrust', self.HH, self.FOOT, *tip_of('D29_thrust'))
        th = tv(47, 4)
        if t >= th - 0.05:
            a = eo(cl((t - (th - 0.05)) / 0.3), 2)
            x, y = K.grid()
            top = tp[1] - (tp[1] - BAR + 60) * a
            key = ('n29',)
            if key not in _PL: _PL[key] = cv2.resize(D._tile(2901)[:H // 8, :8], (W, H), interpolation=cv2.INTER_CUBIC) - 0.5
            dx = np.abs(x - tp[0] - _PL[key] * 60)
            wv = (6 + 40 * a) * np.clip((tp[1] - y) / 400, 0.2, 1)
            core = np.clip((wv - dx) / 4, 0, 1) * (y < tp[1]) * (y > top)
            fr = fr * (1 - core[..., None]) + core[..., None] * 1.2
            fr = fr + (np.exp(-(dx / (60 + 120 * a)) ** 2) * (y < tp[1]) * (y > top) * 0.6 * a)[..., None] * WHT
            fr = fr + (np.exp(-(dx / (20 + 60 * a)) ** 2) * (y < tp[1]) * (y > top) * 0.4)[..., None] * RED
        fr, _ = put(fr, 'D29_thrust', t, self.HH, self.FOOT, wind=8)
        fr = glow_at(fr, tp, 100, 1.2 * K.pulse(t, th, 0.08) * (t >= th) + 0.3 * (t >= th))
        fr = ink_rain(fr, t, 2902, n=140, angle=8, amt=0.4)
        return shake_cam(fr, t, [th], amp=10, z=1.0 + 0.04 * e), 0


class S30_Da(Shot):
    """大远景升镜：云层沿刀线裂开，白光倾泻；山脊上的鬼屠剪影举刀；「答」一拍白光从刀尖爆开，最后 0.6s 白光铺满出画（接 E 段）"""
    t0, t1 = 191.54, 193.24
    FOOT, HH = (960, 1000), 380
    def render(self, t):
        e = eio(self.u(t))
        fr = bg_flow('D30_sky', t, self.tm, z=1.25 - 0.12 * e, cy=lerp(0.62, 0.42, e), drift=(0.506, 40, -15), turb=24, seed=30)
        th = tv(47, 5)
        fr, _ = put(fr, 'D29_thrust', t, self.HH, self.FOOT, wind=6, look='sil')
        tp = spt('D29_thrust', self.HH, self.FOOT, *tip_of('D29_thrust'))
        fr = glow_at(fr, tp, 60 + 200 * cl((t - th) / 0.4), 1.5 * (t >= th) + 0.4)
        if t >= th:
            x, y = K.grid(); a = cl((t - th) / 0.5)
            d = np.sqrt((x - tp[0]) ** 2 + (y - tp[1]) ** 2)
            fr = fr + (np.exp(-((d - 1600 * eo(a, 2)) / 40) ** 2) * (1 - a))[..., None] * WHT * 1.2
        fr = embers_d(fr, t, 3001, n=60, rise=(80, 200))
        w = cl((t - (self.t1 - 0.6)) / 0.6)
        fr = fr * (1 + 1.6 * w) + w ** 1.5 * 0.9
        return shake_cam(fr, t, [th], amp=10, oy=-30 * e), 0


SHOTS = [S01_Drop, S02_Steles, S03_TypeSlam, S04_Snow, S05_Ren, S06_Scale, S07_Heap, S08_Seals, S09_Brush, S10_Giant,
         S11_Answer, S12_Pierce, S13_PaperCut, S14_Burn, S15_Hole, S16_Closed, S17_Eye, S18_Draw, S19_Forge, S20_Wall,
         S21_Charge, S22_Chuang, S23_Eye, S24_Defy, S25_Leap, S26_Judge, S27_Bullet, S28_Spin, S29_Thrust, S30_Da]


def s29_tip():
    """S29 画面上的刀尖（S28→S29 白光竖劈、S29→S30 刀尖白光圆都从这里出）"""
    return spt('D29_thrust', S29_Thrust.HH, S29_Thrust.FOOT, *tip_of('D29_thrust'))


def tip_iris(A, B, p, tip=None, seed=0):
    """S29→S30：白光从刀尖以圆铺开，圆内是下一镜，圆缘一圈白焰 + 血红外晕（替代 gold_tip，不带「答」字）"""
    tip = tip or s29_tip()
    x, y = K.grid()
    d = np.sqrt((x - tip[0]) ** 2 + (y - tip[1]) ** 2)
    n = cv2.resize(D._tile(311 + seed)[:H // 4, :W // 4], (W, H))
    Rr = 40 + 2300 * ei(p, 2)
    m = np.clip((Rr - d + (n - 0.5) * 260) / 140, 0, 1)
    out = A * (1 - m[..., None]) + B * m[..., None]
    ring = np.exp(-((d - Rr + (n - 0.5) * 260) / (40 + 80 * p)) ** 2)
    return out + (ring * (1 - p * 0.6))[..., None] * WHT * 0.9 + cv2.GaussianBlur(ring, (0, 0), 20)[..., None] * RED * 0.8


def ink_sweep(A, B, p, seed=0, pw=980, tilt=-6.0):
    """S20→S21（替代 plaque_sweep 的灰色木牌，评审算 CG + 直边）：一笔巨大的干笔浓墨贴着镜头从右往左扫过，
    墨扫过之处换成下一镜。笔的两缘是毛边（噪声扰动 + 飞白丝），没有任何直线边；墨身有干笔白丝和横向拖影。"""
    x, y = K.grid()
    th = math.radians(tilt)
    xr = (x - W / 2) * math.cos(th) + (y - H / 2) * math.sin(th) + W / 2
    xl = lerp(W + 260, -pw - 260, ei(p, 1.25) * 0.5 + p * 0.5)
    key = ('inksweep', seed)
    if key not in _PL:
        nL = cv2.resize(D._tile(seed + 831)[:, :6], (1, H), interpolation=cv2.INTER_CUBIC)[:, 0] - 0.5
        nR = cv2.resize(D._tile(seed + 832)[:, :6], (1, H), interpolation=cv2.INTER_CUBIC)[:, 0] - 0.5
        fib = cv2.resize(D._tile(seed + 833)[:, :3], (W + 2 * pw, H), interpolation=cv2.INTER_LINEAR)
        hair = cv2.resize(D._tile(seed + 834)[:64, :], (W + 2 * pw, H), interpolation=cv2.INTER_LINEAR)
        _PL[key] = (nL.astype(np.float32), nR.astype(np.float32), fib.astype(np.float32), hair.astype(np.float32))
    nL, nR, fib, hair = _PL[key]
    gx = np.clip((xr - xl + pw).astype(np.int32), 0, fib.shape[1] - 1); gy = np.clip(y.astype(np.int32), 0, H - 1)
    fb = fib[gy, gx]; hr = hair[gy, gx]
    eL = xl + nL[gy] * 220 + (hr - 0.5) * 90                      # 前沿：毛边
    eR = xl + pw + nR[gy] * 260 + (hr - 0.5) * 140                # 尾沿：拖出飞白
    body = np.clip((xr - eL) / 6, 0, 1) * np.clip((eR - xr) / 40, 0, 1)
    passed = np.clip((xr - eR) / 40, 0, 1)
    dry = np.clip((fb - 0.62) * 6, 0, 1) * np.clip((xr - eL) / pw, 0, 1)        # 越往尾越飞白
    ink = body * (1 - dry * 0.9)
    out = A * (1 - np.clip(body + passed, 0, 1))[..., None] + B * passed[..., None]
    out = out + B * (body * dry * 0.9)[..., None]                 # 飞白缝里透出下一镜
    out = out * (1 - ink[..., None]) + INKC * ink[..., None]
    shadow = np.exp(-np.clip(eL - xr, 0, None) / 120) * (xr < eL) * 0.35
    return out * (1 - shadow[..., None])

