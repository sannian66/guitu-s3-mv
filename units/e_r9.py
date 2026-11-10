"""E 组第五轮（用户 #46–#51 + 「何须伪装」）—— 以补丁形式挂到 sec_e_final_outro（E_R5=0 整体回退）。

分项开关（环境变量，默认开；设 '0' 关）：
  E_R5_WIND  角色精灵 wind 夹到 5–8（0 保持 0 = 道具/无发丝）
  E_R5_TEXT  #46 3:02 起画内歌词字全去（保留：天理昭彰匾 E04/E05/E27c、鬼屠印 E12、天理碑 E15；底部字幕由 subtitle.py 出，不在本段）
  E_R5_MARK  #46 对/错 → 毛笔 ✓ / ✗（E16/E17，E18 定格随之）
  E_R5_E19   「何须伪装」：黑剪影 + ？脸 + 躯干竖排骨白字（「伪」血红）+ 金边 + 墨烟
  E_R5_E22   #47 刀作秤：整张生图 R5_E/scale_b（不再代码拼秤）
  E_R5_E23   #48 E23/E24 同一张生图 R5_E/coil_c（E23 全景蓄力推近 → E24 同图刃身 ECU 扫光）
  E_R5_E25   #49 劈开的光不再挡人：裂屏/光带只作用于背景，人物整体压在光带之上
  E_R5_E34   #50 尾奏背影换写实生图 R5_E/back_rim_a/b（可见轮廓、金边发丝），太阳不压头
  E_R5_BEAT  #51 3:55 起按鼓点切：E34 拆成 4 镜（ELS → 背影 MS → 握鞘手 → 靴步），E35 收刀「咔」落在最强拍 7154
  E_R5_NOTITLE（默认关）片名/署名/终印也去掉 —— 「其余到结束文字全去」是否含片名署名，交总导演定
"""
import os, math
import numpy as np, cv2
import c1kit as K
import typo as T
import fx2
import rest_sprites as RS
import e_kit as E
import e_r3 as R3
from e_kit import W, H, BAR, GOLD, GOLDW, RED, REDT, WHITE_T, GOLD_T, sstep, c01, eio, eout, ein
from e_r3 import LyrO


def _on(k, d='1'): return os.environ.get(k, d) != '0'


ON = dict(wind=_on('E_R5_WIND'), text=_on('E_R5_TEXT'), mark=_on('E_R5_MARK'), e19=_on('E_R5_E19'), e22=_on('E_R5_E22'),
          e23=_on('E_R5_E23'), e25=_on('E_R5_E25'), e34=_on('E_R5_E34'), beat=_on('E_R5_BEAT'), notitle=_on('E_R5_NOTITLE', '0'))
R6FIX = _on('E_R6_FIX')       # r6 #47/#49/#50/#51 构图与卡点修正（'0' 回到 r5 画面，出对比图用）
KEEPTXT = _on('E_R6_KEEPTXT')   # r6 #55：镜内横排/刻/写/印歌词字保留（'0' 回到 r5 #46 全去）
R6B = R6FIX and _on('E_R6B')   # r6 第二棒（评审 REVIEW_E_r6 返工：#47 圆外残字 / #49 接地 / #50 ELS 人物可读 + LS / #51 强拍动作 / 3:40.6、3:41.3 亮斑）；'0' 回到第一棒
M = None


def _nil_text(self, fr, t): return fr


class _Nil:
    def draw(self, fr, *a, **k): return fr


# ------------------------------------------------------------------ 毛笔 ✓ / ✗（走 T.glyph 字形通道，LyrO 烧出/灰飞照常）
_BM = {}
_STROKES = {   # (起点, 控制点, 终点, 起宽, 收宽, 飞白起点)  坐标以字号为单位、字心为原点、y 向下
    '✓': [((-0.38, -0.04), (-0.24, 0.12), (-0.08, 0.30), 0.085, 0.15, 1.1),
          ((-0.08, 0.30), (0.12, -0.02), (0.44, -0.42), 0.15, 0.02, 0.45)],
    '✗': [((-0.34, -0.36), (-0.04, 0.06), (0.38, 0.40), 0.13, 0.07, 0.70),
          ((0.36, -0.40), (0.05, 0.04), (-0.40, 0.40), 0.11, 0.03, 0.55)],
}


def brush_mark(ch, size):
    size = max(8, int(round(size / 2) * 2)) if size < 400 else int(round(size / 8) * 8)
    k = (ch, size)
    if k in _BM: return _BM[k]
    g = int(size * 1.5) + 8
    S = 2 * g; c = S / 2; un = 2 * size
    can = np.zeros((S, S), np.uint8)
    rng = np.random.default_rng(ord(ch))
    for (p0, p1, p2, w0, w1, dry) in _STROKES[ch]:
        p0, p1, p2 = [np.array(p, np.float64) for p in (p0, p1, p2)]
        nb = 11
        ends = rng.uniform(min(dry + 0.12, 0.99), 1.0, nb); ends[rng.choice(nb, 3, replace=False)] = 1.0
        offs = np.linspace(-0.92, 0.92, nb) + rng.normal(0, 0.03, nb)
        for s in np.linspace(0, 1, 420):
            pt = (1 - s) ** 2 * p0 + 2 * (1 - s) * s * p1 + s * s * p2
            tg = 2 * (1 - s) * (p1 - p0) + 2 * s * (p2 - p1); tg /= (np.linalg.norm(tg) + 1e-9)
            nv = np.array([-tg[1], tg[0]])
            r = 0.5 * (w0 + (w1 - w0) * s) * (1 + 0.25 * math.exp(-s / 0.06)) * un
            if s < dry:
                cv2.circle(can, (int((c + pt[0] * un) * 16), int((c + pt[1] * un) * 16)), max(1, int(r * 16)), 255, -1, cv2.LINE_AA, 4)
            else:
                for j in range(nb):
                    if s > ends[j]: continue
                    q = c + (pt + nv * offs[j] * r / un) * un
                    cv2.circle(can, (int(q[0] * 16), int(q[1] * 16)), max(1, int(r / nb * 1.5 * 16)), 255, -1, cv2.LINE_AA, 4)
    a = cv2.GaussianBlur(can.astype(np.float32) / 255, (0, 0), 1.2)
    nz = cv2.resize(rng.random((max(2, S // 10), max(2, S // 10))).astype(np.float32), (S, S), interpolation=cv2.INTER_CUBIC)
    a = np.clip((a - 0.5 + (nz - 0.5) * 0.3) * 3 + 0.5, 0, 1)
    a = cv2.resize(a, (g, g), interpolation=cv2.INTER_AREA).astype(np.float32)
    _BM[k] = a
    return a


def _install_glyph():
    if getattr(T.glyph, '_r9', False): return
    g0 = T.glyph

    def glyph(ch, fname='kai', size=120, texture=True):
        if ch in _STROKES: return brush_mark(ch, size)
        return g0(ch, fname, size, texture)
    glyph._r9 = True; glyph._orig = g0
    T.glyph = glyph


# ------------------------------------------------------------------ 整张生图底板（2.39:1，1918×820）
_PL = {}
def plate(name):
    if name not in _PL:
        im = cv2.imread(RS.GEN + 'R5_E/' + name + '.png', cv2.IMREAD_COLOR)
        _PL[name] = (im[..., ::-1].astype(np.float32) / 255).copy()
    return _PL[name]


def warp_plate(img, s, cx, cy):
    """底板点 (cx,cy) → 屏幕中心 (960,540)，放大 s。可见区 y∈[120,960] 需 cy∈[420/s, 820-420/s]。"""
    A = np.float32([[s, 0, 960 - cx * s], [0, s, 540 - cy * s]])
    return cv2.warpAffine(img, A, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)


def unsharp(fr, amt=0.5, sig=2.0):
    return fr + amt * (fr - cv2.GaussianBlur(fr, (0, 0), sig))


def _clamp_wind():
    if getattr(M.put, '_r9', False): return
    p0 = M.put

    def put(*a, **k):
        w = k.get('wind', 6.0)
        if w and w > 0: k['wind'] = float(min(8.0, max(5.0, w)))
        return p0(*a, **k)
    put._r9 = True
    M.put = put


def _wrap_init(cls, post):
    f0 = cls.__init__

    def init(self, *a, **k):
        f0(self, *a, **k); post(self)
    cls.__init__ = init


# ================================================================== E19 何须伪装
class E19n:
    GR = dict(expo=0.8, sat=0.5, tint=(1.04, 0.98, 0.92), lift=0.0, gamma=1.1)

    def __init__(self):
        sky = E.dawn_sky(1250, horizon=0.9, mid=(0.30, 0.20, 0.11), hor=(0.9, 0.66, 0.36), cloud=0.6, sun=(1500, 900))
        yy, xx = E.grid()
        halo = np.exp(-(((xx - 1010) / 520) ** 2 + ((yy - 380) / 420) ** 2))
        self.bg = (cv2.GaussianBlur(sky, (0, 0), 10) * 0.72 + halo[..., None] * np.array([0.42, 0.30, 0.16], np.float32)).astype(np.float32)
        self.chips = R3.Shreds(125, n=26, gold=0.85, size=(14, 46), spread=(1100, 520), zr=(0.6, 2.6))
        self.smoke = K.fbm(H // 4, W // 4, 1255, base=5, octaves=5).astype(np.float32)
        self.lyr = None

    def _text(self):
        t0 = self.t0
        bone, blood = (0.90, 0.86, 0.76), (0.70, 0.05, 0.04)
        ts = [t0 + 0.10, M.CT(53, 9) + 0.03, M.CT(53, 10), M.CT(53, 11)]
        cols = [bone, bone, blood, bone]
        g = T.glyph('？', 'serif_black', 150, False)                        # 全角问号字面偏左：按墨迹包围盒居中到脸心
        ys, xs = np.nonzero(g > 0.3)
        ox = (g.shape[1] - 1) / 2 - (xs.min() + xs.max()) / 2; oy = (g.shape[0] - 1) / 2 - (ys.min() + ys.max()) / 2
        ch = [('？', self.face[0] + ox, self.face[1] + oy, 150, 'serif_black', bone, t0 + 0.18)]
        y0 = self.chin + 100
        for i, c in enumerate('何须伪装'):
            ch.append((c, self.face[0], y0 + 92 * i, 84, 'serif_black', cols[i], ts[i]))
        self.lyr = LyrO(ch, None, outline=0, seed=140, glow=0.22, shadow=0.0)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        fr = self.chips.draw(fr, (t - self.t0) * 0.5 + 0.2, to_cam=0.3, light=(0.6, -0.5, -0.6), dof=(3.0, 10.0), zfocus=1.4, emb=0.25)
        z, info = M.put(np.zeros((H, W, 3), np.float32), t, 'R5_E/sil_front_b', (960, 160), h=1200, anc=(0.5, 0.0),
                        rim=GOLDW, rim_amt=0.0, grade=self.GR, wind=6)
        A = np.clip(info['A'], 0, 1)
        if self.lyr is None:
            self.face = info['to_scr']((0.500, 0.2286)); self.chin = info['to_scr']((0.5, 0.293))[1]
            self._text()
        yy, xx = E.grid()
        body = sstep(self.chin - 10, self.chin + 60, yy)
        base = np.array([0.022, 0.018, 0.016], np.float32)
        fill = A[..., None] * base + z * (0.14 * body)[..., None]
        # 墨烟：从剪影外缘升起（只在剪影周围一圈）
        Mt = np.float32([[1, 0, 0], [0, 1, 26 * (t - self.t0)]])
        sm = cv2.resize(cv2.warpAffine(self.smoke, Mt, (W // 4, H // 4), borderMode=cv2.BORDER_REFLECT), (W, H))
        near = np.clip(cv2.GaussianBlur(A, (0, 0), 40) * 2.2 - A, 0, 1) * sstep(980, 300, yy)
        ink = np.clip((sm - 0.36) * 2.4, 0, 1) * near * 0.8
        fr = fr * (1 - ink[..., None])
        # 轮廓金边：右上来光，只亮朝光一侧的边
        Ab = cv2.GaussianBlur(A, (0, 0), 2.0)
        gx = cv2.Sobel(Ab, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(Ab, cv2.CV_32F, 0, 1, ksize=3)
        gn = np.sqrt(gx * gx + gy * gy) + 1e-6
        Lx, Ly = 0.5, -0.85; ln = math.hypot(Lx, Ly)
        lit = np.clip(-(gx * Lx + gy * Ly) / (gn * ln), 0, 1) ** 1.5
        band = np.clip(A - cv2.erode(A, np.ones((7, 7), np.uint8)), 0, 1)
        flick = 0.75 + 0.5 * np.clip(cv2.resize(self.smoke[:, ::-1], (W, H)) * 1.6 - 0.3, 0, 1)   # 金边随烟明暗起伏，不是均匀描边
        rim = cv2.GaussianBlur(band * lit * flick, (0, 0), 1.6)
        glow = np.clip(cv2.GaussianBlur(A, (0, 0), 22) - A, 0, 1) * cv2.GaussianBlur(lit, (0, 0), 14)
        fr = fr * (1 - A[..., None]) + fill
        fr = fr + rim[..., None] * np.array([1.0, 0.78, 0.45], np.float32) * 1.1 + glow[..., None] * GOLD * 0.55
        fr = self.lyr.draw(fr, t)
        return M.bloom(fr, 0.8, 0.35)

    text = _nil_text


# ================================================================== E22 刀作秤（整张生图）
PAD22 = 140


def _pad_top(img, pad):
    """r6：底板上沿补天空（顶行镜像 + 重模糊 + 渐压暗），给头顶留白，不再顶着画幅上沿。"""
    row = cv2.GaussianBlur(img[:14].mean(0, keepdims=True), (0, 0), 30)    # 只取头顶以上的天空行（头顶在 y≈26），不镜像，免得把头发翻上去成黑团
    tex = cv2.GaussianBlur(img[:pad][::-1] - cv2.GaussianBlur(img[:pad][::-1], (0, 0), 25), (0, 0), 3)   # 借云纹细节（去低频，头发的大块暗不进来）
    yy = np.arange(pad, dtype=np.float32)[:, None, None]
    g = np.linspace(0.82, 1.0, pad, dtype=np.float32)[:, None, None]
    ext = np.clip(np.repeat(row, pad, 0) + 0.35 * np.clip(tex, -0.04, 0.04) * (yy / pad), 0, 1) * g
    k = np.linspace(0, 1, 24, dtype=np.float32)[:, None, None]                 # 接缝 24 行羽化
    out = np.concatenate([ext, img], 0)
    out[pad:pad + 24] = ext[-1:] * (1 - k) + img[:24] * k
    out[pad - 24:pad + 24] = cv2.GaussianBlur(out[pad - 40:pad + 40], (0, 0), 6)[16:64]
    return out.astype(np.float32)


class E22n:
    def __init__(self): self.img = _pad_top(plate('scale_b'), PAD22) if R6FIX else plate('scale_b')

    def render(self, t):
        e = eio(self.u(t))
        s = 1.06 + 0.04 * e                                                   # 头顶（底板 y≈26）稳定在屏幕 y≈200，留白 ≈80px
        fr = warp_plate(self.img, s, 959, PAD22 + 26 + (540 - 200) / s) if R6FIX else warp_plate(self.img, 1.06 + 0.04 * e, 959, 410 - 10 * e)
        fr = E.dust_motes(fr, t, 1281, n=60, amt=0.3, drift=(14, -10), depth=True)
        return M.bloom(fr, 0.85, 0.25)

    text = _nil_text


# ================================================================== E23 / E24 同一张生图 coil_c
BLADE = [(1380, 200), (1000, 185), (700, 190), (300, 215), (100, 240)]   # 刀身中线（柄 → 尖，底板坐标）


def _blade_at(s):
    P = np.array(BLADE, np.float64)
    L = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    d = s * L[-1]
    i = min(len(P) - 2, int(np.searchsorted(L, d, 'right') - 1))
    k = (d - L[i]) / (L[i + 1] - L[i])
    p = P[i] + (P[i + 1] - P[i]) * k
    v = P[i + 1] - P[i]
    return p, math.degrees(math.atan2(v[1], v[0]))


class E23n:
    def __init__(self):
        self.img = plate('coil_c')
        h, w = self.img.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        by = np.interp(xx, [p[0] for p in BLADE[::-1]], [p[1] for p in BLADE[::-1]])
        wgt = sstep(860, 600, xx) * sstep(20, 90, yy) * (1 - sstep(480, 600, yy)) * (1 - np.exp(-((yy - by) / 48) ** 2))
        self.hw = (wgt * (0.4 + 0.6 * sstep(880, 380, xx))).astype(np.float32)   # 左侧散发：越往发梢摆越大，避开刀身/脸
        self.yy, self.xx = yy, xx

    def _hair(self, t):
        dx = (3.0 * np.sin(self.yy / 37 + t * 5.2) + 1.6 * np.sin(self.yy / 13 - t * 8.3)) * self.hw
        dy = 1.4 * np.sin(self.xx / 29 + t * 6.1) * self.hw
        return cv2.remap(self.img, self.xx + dx, self.yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def render(self, t):
        u = self.u(t); e = M.ease('expo_in', u)
        img = self._hair(t)
        fr = warp_plate(img, 1.06 + 0.16 * e, 960 - 30 * e, 410 - 50 * e)
        fr = RS.fx_embers(fr, t, 1292, amt=0.45, n=30)
        return M.bloom(fr, 0.85, 0.3)

    text = _nil_text


class E24n(E23n):
    def __init__(self):
        self.img = plate('coil_c')

    def render(self, t):
        u = self.u(t); e = eio(u)
        s = 1.75 + 0.10 * e; cx, cy = 900 - 140 * e, 262 - 12 * e
        fr = unsharp(warp_plate(self.img, s, cx, cy), 0.6, 1.6)
        p, ang = _blade_at(eio(c01(u * 1.15)))                               # 寒光自柄扫到尖
        sp = (960 + (p[0] - cx) * s, 540 + (p[1] - cy) * s)
        fr = E.flare_streak(fr, sp, amt=0.9 * (1 - 0.6 * c01((u - 0.85) / 0.15)), length=0.7, angle=ang)
        yy, xx = E.grid()
        P = np.array(BLADE, np.float32)
        lineY = np.interp(cx + (xx - 960) / s, P[::-1, 0], P[::-1, 1])
        ly = 540 + (lineY - cy) * s - 22 * s                                     # 刃口一侧的细亮线（刀身上缘）
        edge = np.exp(-((yy - ly) / 2.2) ** 2) * np.exp(-((xx - sp[0]) / 260) ** 2)
        fr = fr + edge[..., None] * GOLDW * 1.2
        return M.bloom(fr, 0.8, 0.4)


# ------------------------------------------------------------------ r6b #49 接地：接触阴影 / 脚下扬尘火星 / 朝光带轮廓光
def _feet(A):
    """两只脚的屏幕 x（取 alpha 最底 36 行的列投影，按中缝分左右）、底 y、站姿宽。"""
    ys = np.nonzero(A.max(1) > 0.5)[0]; yb = int(ys.max())
    xs = np.nonzero(A[yb - 40:yb + 1].max(0) > 0.5)[0]
    runs = np.split(xs, np.nonzero(np.diff(xs) > 6)[0] + 1)                 # 连续段：最左段 = 左靴，最右段 = 右靴
    l, r = runs[0], runs[-1]
    return dict(l=float(l.mean()), r=float(r.mean()), x0=float(xs.min()), x1=float(xs.max()), y=float(yb))


def _contact(fr, ft, gy):
    """脚下椭圆接触阴影：宽 ≈1.3× 站姿宽，alpha 0.5，羽化约 30px；两脚各一团更实的小影。"""
    m = np.zeros((H // 2, W // 2), np.float32)
    cx = (ft['x0'] + ft['x1']) / 2; hw = 0.65 * (ft['x1'] - ft['x0'])
    cv2.ellipse(m, (int(cx / 2), int(gy / 2)), (int(hw / 2), 11), 0, 0, 360, 0.6, -1, cv2.LINE_AA)
    for x in (ft['l'], ft['r']):
        cv2.ellipse(m, (int(x / 2), int(gy / 2)), (36, 6), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
    m = cv2.resize(cv2.GaussianBlur(m, (0, 0), 6), (W, H))
    return fr * (1 - 0.5 * np.clip(m, 0, 1)[..., None])


def _band_rim(A, by):
    """光带（y=by，全宽横在人身后）照来的轮廓光：2–3px 外缘带，朝光带的法向（上/下朝 by、左右朝外）更亮，离光带越近越亮。"""
    Ab = cv2.GaussianBlur(A, (0, 0), 1.5)
    gx = cv2.Sobel(Ab, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(Ab, cv2.CV_32F, 0, 1, ksize=3)
    gn = np.sqrt(gx * gx + gy * gy) + 1e-6
    nx, ny = -gx / gn, -gy / gn                                            # 外法向
    yy = np.arange(H, dtype=np.float32)[:, None]
    face = np.clip(0.55 * np.abs(nx) + np.maximum(0, ny * np.sign(by - yy)) + 0.15, 0, 1)
    band = np.clip(A - cv2.erode(A, np.ones((5, 5), np.uint8)), 0, 1)
    near = 0.25 + 0.75 * np.exp(-((yy - by) / 230) ** 2)
    return cv2.GaussianBlur(band * face * near, (0, 0), 0.8)


def _foot_dust(fr, t, ts, ft):
    """劈开那一帧两只脚各起一团尘 + 火星，0.3s 散掉。"""
    q = t - ts
    if q < 0 or q > 0.6: return fr
    dust = np.zeros((H // 4, W // 4), np.float32)
    if q < 0.3:
        r = 30 + 110 * eout(q / 0.3)
        for x in (ft['l'], ft['r']):
            cv2.ellipse(dust, (int(x / 4), int((ft['y'] - 10) / 4)), (int(r * 1.5 / 4), int(r * 0.55 / 4)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        dust = cv2.resize(cv2.GaussianBlur(dust, (0, 0), 5), (W, H)) * 0.7 * (1 - q / 0.3) ** 1.3
        fr = fr * (1 - dust[..., None]) + dust[..., None] * np.array([0.95, 0.60, 0.32], np.float32)    # 逆光里的尘：被身后光带照亮
    for k, x in enumerate((ft['l'], ft['r'])):
        fr = RS.fx_sparks(fr, t, ts, (x, ft['y'] - 8), 1311 + k, n=28, spd=420, dirv=(-0.5 if k == 0 else 0.5, -1), spread=1.0, grav=900, amt=0.9)
    return fr


# ================================================================== E25 横斩：光带只劈背景，人压在上面
class E25n:
    GR = dict(expo=1.15, sat=0.62, tint=(1.1, 0.95, 0.86), lift=0.02, gamma=1.0)

    def __init__(self):
        self.sky = E.dawn_sky(1300, horizon=0.92, top=(0.02, 0.012, 0.012), mid=(0.17, 0.05, 0.03), hor=(0.62, 0.20, 0.08), cloud=0.9, sun=None)
        n = K.fbm(H // 2, W // 2, 1302, base=10, octaves=5)
        self.ground = cv2.resize(((0.02 + 0.05 * n)[..., None] * np.array([1.0, 0.7, 0.6], np.float32)).astype(np.float32), (W, H))

    def render(self, t):
        fr = self.sky.copy()
        hy = 868 if R6B else 930                                           # r6b：地平线抬到脚后 → 人站在地面上（不是站在地平线那条缝上）
        m = sstep(hy - 2, hy + 20, np.arange(H, dtype=np.float32))[:, None, None]
        gnd = self.ground
        if R6B:                                                            # 地面受光：近地平线处被身后的天光/光带照暖，往镜头方向渐暗 → 接触阴影读得出
            yv = np.arange(H, dtype=np.float32)[:, None, None]
            gnd = gnd + np.exp(-np.clip(yv - hy, 0, None) / 70) * np.array([0.30, 0.12, 0.05], np.float32) + 0.05 * np.array([0.5, 0.25, 0.12], np.float32)
        fr = fr * (1 - m) + gnd * m
        ts = M.CT(55, 6)
        mb = (90, 0) if (t < ts + 0.04 and not R6FIX) else (0, 0)            # r6：硬切后不再留 2 帧动态模糊残影
        z, info = M.put(np.zeros((H, W, 3), np.float32), t, 'S130/hslash', (930, 924) if R6B else (930, hy - 6) if R6FIX else (930, 1200), h=720 if R6B else 760 if R6FIX else 1040,   # r6：脚落地平线入画、头顶留白 rim=(1.0, 0.7, 0.4), rim_amt=3.4,
                        rim_dir=(-0.9, -0.3), wind=6, mblur=mb, grade=self.GR)
        A = np.clip(info['A'], 0, 1)
        if R6B:                                                             # r6b #49：抠像边内缩 1px + 羽化 1.5px（去硬边贴纸感）
            A2 = cv2.GaussianBlur(cv2.erode(A, np.ones((3, 3), np.uint8)), (0, 0), 1.5)
            z = np.clip(z / np.maximum(A, 1e-3)[..., None], 0, 4) * A2[..., None]; A = A2
            if not hasattr(self, 'feet'): self.feet = _feet(A)
        by = info['tip'][1] if info['tip'] else 520
        q = t - ts
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        if q > 0:                                                          # 背景沿刀线裂开（人不裂）
            e = eout(q / 0.25)
            gap = 70 * e * (1 - 0.3 * c01((q - 0.6) / 0.5))
            top = K.cam(fr, 1.0, oy=-gap / 2); bot = K.cam(fr, 1.0, oy=gap / 2)
            if R6B:                                                        # r6b：地面不跟着裂开下沉（脚要一直踩在地上）
                wb = 1 - sstep(hy - 160, hy - 20, yy)
                bot = bot * wb + fr * (1 - wb)
            fr = np.where(yy < by, top, bot)
            band = np.exp(-((yy[..., 0] - by) / max(2, gap * 0.45)) ** 2)
            fr = fr * (1 - band[..., None] * 0.85) + band[..., None] * GOLDW * 1.8
            fr = fr + np.exp(-((yy - by) / (gap + 40)) ** 2) * GOLD * 0.7 * (1 + 2 * math.exp(-q / 0.12))
            if q < 0.08: fr = fr * 1.25 + np.array([0.25, 0.10, 0.03], np.float32) * (1 - q / 0.08)
        if R6B: fr = _contact(fr, self.feet, self.feet['y'] + 6)
        fr = fr * (1 - A[..., None]) + z
        if q > 0:                                                          # 光带从人身后照来：靠近刀线的轮廓镶金
            edge = np.clip(A - cv2.erode(A, np.ones((5, 5), np.uint8)), 0, 1)
            near = np.exp(-((yy[..., 0] - by) / 200) ** 2) * (0.5 + 1.5 * math.exp(-q / 0.25))
            fr = fr + (cv2.GaussianBlur(edge, (0, 0), 1.2) * near)[..., None] * GOLDW * 1.4
            if R6B:                                                         # r6b #49：朝光带一侧 2–3px 暖轮廓光，强度跟光带亮度走
                bandI = eout(q / 0.25) * (0.55 + 1.2 * math.exp(-q / 0.25))
                fr = fr + _band_rim(A, by)[..., None] * np.array([1.0, 0.80, 0.50], np.float32) * 1.25 * bandI
                fr = _foot_dust(fr, t, ts, self.feet)
            fr = RS.fx_sparks(fr, t, ts, (300, by), 1301, n=90, spd=1400, dirv=(1, -0.1), spread=0.35, grav=300, amt=1.2)
        fr = RS.fx_embers(fr, t, 1303, amt=0.7, n=50)
        return M.bloom(fr, 0.82, 0.5)

    text = _nil_text


# ================================================================== 尾奏 3:55 起：写实背影 + 鼓点切
def _shadow(fr, fx, fy, L=170.0, lean=0.55, wmax=34, amt=0.72):
    """逆光低日 → 脚下长影朝镜头、偏离太阳一侧铺开。"""
    yy, xx = E.grid()
    dy = (yy - fy) / L
    wv = 5 + wmax * np.clip(dy, 0, 1) ** 0.8
    sh = np.exp(-((xx - fx - lean * (yy - fy)) / wv) ** 2) * np.clip((dy + 0.02) / 0.02, 0, 1) * np.clip(1 - dy, 0, 1) ** 2.0
    sh = np.maximum(sh, np.exp(-(((xx - fx) / 26) ** 2 + ((yy - fy) / 5) ** 2)))
    sh = cv2.GaussianBlur(sh.astype(np.float32), (0, 0), 3.0)
    return fr * (1 - amt * sh[..., None])


G_BACK = dict(expo=0.40, sat=0.55, tint=(1.04, 0.96, 0.88), lift=0.0, gamma=1.15)

# r6 #51：3:54.6–3:56.3 ELS 原来对鼓点无反应。下列拍点取自 analysis.npz 的 low 峰（kick），帧号 /30
HITS34 = [(7040 / 30, 1.0), (7047 / 30, 0.6), (7054 / 30, 0.6), (7061 / 30, 1.0), (7072 / 30, 1.0)]


def beat_pulse(t, hits, tau=0.11):
    p = 0.0
    for th, a in hits:
        if th - 1 / 30 <= t < th + 0.5: p = max(p, a * math.exp(-max(0.0, t - th) / tau))
    return p


class E34n:   # ELS：日在左、人在右 1/3，头不压日面；写实背影，金边发丝
    def __init__(self):
        self.sky = E.dawn_sky(1380, horizon=0.68, mid=(0.48, 0.34, 0.19), hor=(1.0, 0.86, 0.6), cloud=0.7, sun=(820, 640))
        self.rd, self.ra = E.ridges(n=3, base=0.66, step=0.07, seed=136, amp=0.05, far=0.55, near=0.04)
        self.blocks = [('音乐', ['西几王'], 1660, 260, 234.55, 0.5)]

    def render(self, t):
        if R6B: return _els_r6b(self, t)
        u = self.u(t)
        fr = self.sky.copy()
        sun = (820, 690 - 40 * u)
        k = beat_pulse(t, HITS34) if R6FIX else 0.0                                            # r6 #51：低频鼓点 → 日轮/光柱随拍呼吸
        fr = E.sun_disc(fr, sun, 130, amt=(0.82 + 0.30 * k) if R6FIX else 1.15)                   # r6：1.15 → 0.82，日面不再糊成一大块白团
        fr = fx2.god_rays(fr, sun, strength=(0.55 + 0.45 * k) if R6FIX else 0.8, length=1.1, t=t)
        fr = E.place_layer(fr, self.rd, self.ra, z=1.05 - 0.05 * eio(u))
        bob = 3 * abs(math.sin(t * 5.5))
        fx, fy = 1190 - 30 * u, 872
        fr = _shadow(fr, fx, fy, L=90, lean=0.9, wmax=26)
        fr = M.bloom(fr, 0.85, 0.45)
        fr, info = M.put(fr, t, 'R5_E/back_rim_a', (fx, fy - bob), h=330 - 24 * u, rim=GOLDW, rim_amt=4.0, rim_dir=(-0.9, -0.35),
                         grade=G_BACK, wind=6)
        return fr * (1 + 0.07 * beat_pulse(t, HITS34)) if R6FIX else fr

    def credits(self, fr, t):                                                  # r6b：后面接 LS（同一署名延续），ELS 末尾不淡出
        if not R6B: return M.Credits.credits(self, fr, t)
        t1 = self.t1; self.t1 = 1e9
        try: return M.Credits.credits(self, fr, t)
        finally: self.t1 = t1


# ---- r6b #50/#51：ELS 人物在辉光之后合成 + 自带轮廓光；强拍 = 阶梯推镜 / 地平线逆光扬尘火星 / 7061 硬切 LS
HITS34W = [(7047 / 30, 0.6), (7054 / 30, 0.6)]                                # 弱拍：只作用于日面与光柱
STRONG34 = [7040 / 30, 7061 / 30, 7072 / 30]


def step_zoom(t, steps, z0=1.0, tau=0.06):
    """阶梯推镜：每个强拍一帧内进一级（只进不退），其余时间几乎静止。"""
    z = z0
    for th, dz in steps:
        if t >= th - 1 / 30: z += dz * (1 - math.exp(-(t - th + 1 / 30) / tau))
    return z


def horizon_burst(fr, t, hits, y, seed, n=150, amt=1.0, x0=0, x1=W):
    """地平线随强拍扬起一排逆光尘 + 火星（0.5s 散掉）。"""
    L = np.zeros((H // 2, W // 2), np.float32); haze = 0.0
    for k, th in enumerate(hits):
        q = t - th + 1 / 30
        if q < 0 or q > 0.6: continue
        r = np.random.default_rng(seed + k)
        xs = r.uniform(x0, x1, n); vy = r.uniform(120, 420, n); vx = r.uniform(-60, 60, n) + 30; sz = r.uniform(0.6, 1.8, n); y0 = y + r.normal(0, 10, n)
        life = r.uniform(0.25, 0.6, n); dl = r.uniform(0.0, 0.08, n)                     # 起跳错开 0–2 帧，不排成一条线
        for i in range(n):
            qi = q - dl[i]
            if qi < 0 or qi > life[i]: continue
            a = (1 - qi / life[i]) ** 1.5 * min(1.0, qi / 0.03 + 0.3)
            px = xs[i] + vx[i] * qi; py = y0[i] - vy[i] * qi + 300 * qi * qi
            p2 = (px - vx[i] * 0.035, py + (vy[i] - 600 * qi) * 0.035)                    # 短拖尾 = 被踢起的火星
            cv2.line(L, (int(px / 2), int(py / 2)), (int(p2[0] / 2), int(p2[1] / 2)), float(a), max(1, int(sz[i])), cv2.LINE_AA)
        haze = max(haze, math.exp(-q / 0.18))
    if haze <= 0: return fr
    L = cv2.resize(cv2.GaussianBlur(L, (0, 0), 0.8), (W, H))
    yy = np.arange(H, dtype=np.float32)[:, None]
    band = np.exp(-((yy - y + 10) / 26) ** 2) * haze                                       # 扬起的一层尘雾（逆光被照亮）
    return fr + (L * 1.3 + cv2.GaussianBlur(L, (0, 0), 4) * 0.8)[..., None] * np.array([1.0, 0.72, 0.38], np.float32) * amt \
              + band[..., None] * np.array([0.30, 0.20, 0.10], np.float32) * amt


def _person_lit(fr, t, key, at, h, sun, seed_dir=(-0.9, -0.35), rim_w=1.5, rim_amt=0.9, wind=6, grade=None):
    """人物在辉光之后合成（贴在黑底上取出，不吃背景光包裹），再给头肩上沿 1–2px 暖白轮廓光（朝日一侧更亮）。返回 (fr, A, info)。"""
    z, info = M.put(np.zeros((H, W, 3), np.float32), t, key, at, h=h, rim=GOLDW, rim_amt=2.0, rim_dir=seed_dir, grade=grade or G_BACK, wind=wind)
    A = np.clip(info['A'], 0, 1)
    fr = fr * (1 - A[..., None]) + z
    Ab = cv2.GaussianBlur(A, (0, 0), 1.0)
    gx = cv2.Sobel(Ab, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(Ab, cv2.CV_32F, 0, 1, ksize=3)
    gn = np.sqrt(gx * gx + gy * gy) + 1e-6
    yy, xx = E.grid()
    lx, ly = sun[0] - xx, sun[1] - yy - 250                                                # 低日在左后方，光略自上
    ln = np.sqrt(lx * lx + ly * ly) + 1e-6
    face = np.clip((-gx * lx - gy * ly) / (gn * ln), 0, 1) ** 0.8
    top = np.clip(-gy / gn, 0, 1)                                                           # 头顶 / 肩上沿
    k = max(1, int(round(rim_w * 2)) | 1)
    band = np.clip(A - cv2.erode(A, np.ones((k, k), np.uint8)), 0, 1)
    rim = cv2.GaussianBlur(band * np.clip(0.75 * face + 0.55 * top, 0, 1), (0, 0), 0.6)
    fr = fr + rim[..., None] * np.array([1.0, 0.90, 0.72], np.float32) * rim_amt
    return fr, A, info


def _tone_cap(fr, knee=0.80, top=1.0, keep=None):
    """亮部软压：最大通道超过 knee 的部分压缩到 top 以下（控制过曝面积）。keep=(cx,cy,r)：日面本身不压，只压日晕/天空。"""
    m = fr.max(-1, keepdims=True)
    over = np.clip(m - knee, 0, None)
    nm = knee + (top - knee) * (1 - np.exp(-over / (top - knee)))
    out = fr * np.where(m > knee, nm / np.maximum(m, 1e-6), 1.0)
    if keep is None: return out
    yy, xx = E.grid()
    k = np.clip((keep[2] - np.hypot(xx - keep[0], yy - keep[1])) / 4 + 0.5, 0, 1)[..., None]
    return out * (1 - k) + fr * k


def _els_r6b(self, t):
    if not hasattr(self, 'sky6'):
        self.sky6 = E.dawn_sky(1380, horizon=0.68, top=(0.20, 0.15, 0.10), mid=(0.58, 0.42, 0.25), hor=(0.95, 0.74, 0.48), cloud=0.7, sun=(640, 660))
    u = self.u(t)
    fr = self.sky6.copy()
    sun = (640, 700 - 30 * u)                                                              # 日心离头 ≈550px
    kw = beat_pulse(t, HITS34W) + beat_pulse(t, [(x, 1.0) for x in STRONG34])
    fr = E.sun_disc(fr, sun, 92, amt=0.80 + 0.16 * kw, halo=0.6)
    fr = fx2.god_rays(fr, sun, strength=0.42 + 0.40 * kw, length=1.1, t=t)
    fr = E.place_layer(fr, self.rd, self.ra, z=1.0)
    fr = horizon_burst(fr, t, STRONG34[:1], 712, 7340, n=170)
    bob = 3 * abs(math.sin(t * 5.5))
    fx, fy = 1200 - 24 * u, 872
    fr = _shadow(fr, fx, fy, L=90, lean=0.9, wmax=26)
    fr = _tone_cap(M.bloom(fr, 0.85, 0.35), 0.82, 1.04, keep=(sun[0], sun[1], 92))
    fr, A, info = _person_lit(fr, t, 'R5_E/back_rim_a', (fx, fy - bob), 340, sun, rim_w=1.2, rim_amt=0.85)
    fr = E.dust_motes(fr, t, 1381, n=40, amt=0.25, drift=(-18, -10))
    z = step_zoom(t, [(7040 / 30, 0.025)]) * (1 + 0.004 * u)
    return K.cam(fr, z, center=(fx, 640))


class E34L:   # r6b：7061 强拍硬切 LS（人高 ≈600px），头肩轮廓、马尾在中间调的天前清楚；7072 再进一级 + 地平线扬尘
    def __init__(self):
        self.sky = cv2.GaussianBlur(E.dawn_sky(1392, horizon=0.70, top=(0.24, 0.17, 0.11), mid=(0.62, 0.45, 0.27), hor=(0.95, 0.72, 0.46), cloud=0.7, sun=(600, 690)), (0, 0), 3)
        self.rd, self.ra = E.ridges(n=3, base=0.70, step=0.06, seed=1393, amp=0.04, far=0.5, near=0.03)
        self.rd = cv2.GaussianBlur(self.rd, (0, 0), 2.5); self.ra = cv2.GaussianBlur(self.ra, (0, 0), 2.5)   # 浅景深：远山略虚
        self.blocks = [('音乐', ['西几王'], 1660, 260, 234.55, 0.5)]                       # 署名④ 延续（p=1，不重新出场）

    def render(self, t):
        u = self.u(t)
        fr = self.sky.copy()
        sun = (600, 700 - 20 * u)
        kw = beat_pulse(t, [(x, 1.0) for x in STRONG34[1:]])
        fr = E.sun_disc(fr, sun, 110, amt=0.78 + 0.16 * kw, halo=0.6)
        fr = fx2.god_rays(fr, sun, strength=0.40 + 0.40 * kw, length=1.0, t=t)
        fr = E.place_layer(fr, self.rd, self.ra, z=1.0)
        fr = horizon_burst(fr, t, STRONG34[1:], 760, 7350, n=200, amt=1.1)
        bob = 4 * abs(math.sin(t * 5.5))
        fx, fy = 1250 - 30 * u, 936
        fr = _shadow(fr, fx, fy, L=60, lean=0.9, wmax=40, amt=0.6)
        fr = _tone_cap(M.bloom(fr, 0.85, 0.35), 0.82, 1.04, keep=(sun[0], sun[1], 110))
        fr, A, info = _person_lit(fr, t, 'R5_E/back_rim_a', (fx, fy - bob), 600, sun, rim_w=1.6, rim_amt=0.9)
        fr = E.dust_motes(fr, t, 1394, n=50, amt=0.3, drift=(-22, -12))
        z = step_zoom(t, [(7072 / 30, 0.03)]) * (1 + 0.006 * u)
        return K.cam(fr, z, center=(fx, 600))


class E34b:   # MS 背影上半身：日在头侧（不在头后），金边发丝在风里
    def __init__(self):
        self.sky = cv2.GaussianBlur(E.dawn_sky(1384, horizon=0.78, mid=(0.46, 0.32, 0.17), hor=(1.0, 0.82, 0.52), cloud=0.6, sun=(1250, 420)), (0, 0), 8)
        self.blocks = []

    def render(self, t):
        u = self.u(t)
        fr = self.sky.copy()
        sun = (1260 + 30 * u, 400)
        fr = E.sun_disc(fr, sun, 95, amt=1.1)
        fr = fx2.god_rays(fr, sun, strength=0.7, length=1.0, t=t)
        fr = M.bloom(fr, 0.85, 0.5)
        fr, info = M.put(fr, t, 'R5_E/back_rim_a|crop=0,0,1,0.55', (880 - 20 * u, 1010 + 6 * abs(math.sin(t * 5.5))), h=830, rim=GOLDW, rim_amt=3.6,
                         rim_dir=(0.9, -0.4), grade=G_BACK, wind=6)
        return E.dust_motes(fr, t, 1385, n=50, amt=0.35, drift=(-20, -15))


class E34c:   # 插入：握鞘的手 + 红穗
    def __init__(self):
        yy, xx = E.grid()
        n = cv2.resize(K.fbm(H // 4, W // 4, 1386, base=5, octaves=4), (W, H))
        key = np.exp(-(((xx - 1500) / 700) ** 2 + ((yy - 300) / 500) ** 2))
        self.bg = cv2.GaussianBlur(((0.06 + 0.06 * n)[..., None] * np.array([1.0, 0.8, 0.6], np.float32) + key[..., None] * np.array([0.9, 0.62, 0.32], np.float32)).astype(np.float32), (0, 0), 12)
        self.blocks = []

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        # 裁切左缘（切在身体上）锚在画外 x<0，上缘也在画外：画内只见握鞘手 + 红穗 + 鞘身，无硬切边
        fr, info = M.put(fr, t, 'R5_E/back_rim_b|crop=0.40,0.36,0.82,0.74', (-40 - 25 * u, 715 + 8 * math.sin(t * 5.5)), h=1700, anc=(0.0, 0.5),
                         rim=GOLDW, rim_amt=3.2, rim_dir=(0.9, -0.5), grade=dict(G_BACK, expo=0.55), wind=6)
        fr = E.dust_motes(fr, t, 1387, n=40, amt=0.3, drift=(-25, -10))
        return M.bloom(fr, 0.85, 0.35)


class E34d:   # 靴步：低机位贴地，落脚扬尘
    def __init__(self):
        sky = E.dawn_sky(1388, horizon=0.55, mid=(0.42, 0.29, 0.15), hor=(1.0, 0.80, 0.50), cloud=0.5, sun=(700, 560))
        n = cv2.resize(K.fbm(H // 2, W // 2, 1389, base=12, octaves=5), (W, H))
        yy, xx = E.grid()
        gnd = sstep(590, 640, yy)
        glint = np.exp(-((xx - 700) / 520) ** 2) * np.exp(-np.clip(yy - 600, 0, None) / 110)      # 低日在地面上的反光
        land = ((0.07 + 0.10 * n) * (1 + 3.0 * glint) + 0.05 * np.exp(-np.clip(yy - 600, 0, None) / 60))[..., None] * np.array([1.0, 0.72, 0.46], np.float32)
        bl = sstep(700, 960, yy)[..., None]                                     # 前景地面浅景深
        land = land * (1 - bl) + cv2.GaussianBlur(land, (0, 0), 6) * bl
        self.bg = (sky * (1 - gnd[..., None]) + land * gnd[..., None]).astype(np.float32)
        self.blocks = []

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        fr = fx2.god_rays(fr, (700, 560), strength=0.5, length=0.9, t=t)
        fr = _shadow(fr, 980, 905, L=120, lean=0.6, wmax=60, amt=0.6)
        fr, info = M.put(fr, t, 'R5_E/back_rim_a|crop=0,0.60,1,1', (980, 930 - 10 * u), h=900 - 30 * u, rim=GOLDW, rim_amt=3.0,
                         rim_dir=(-0.7, -0.6), grade=G_BACK, wind=6)
        q = t - self.t0                                                     # 落脚扬尘
        fr = RS.fx_sparks(fr, t, self.t0, (1000, 900), 1390, n=50, spd=260, dirv=(0.2, -1), spread=1.4, grav=120, amt=0.35,
                          col=(0.75, 0.62, 0.48))
        dust = np.zeros((H // 4, W // 4), np.float32)
        r = 30 + 90 * eout(q / 0.35)
        cv2.ellipse(dust, (1000 // 4, 900 // 4), (int(r * 1.8 / 4), int(r * 0.5 / 4)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        dust = cv2.resize(cv2.GaussianBlur(dust, (0, 0), 6), (W, H)) * 0.35 * math.exp(-q / 0.4)
        fr = fr * (1 - dust[..., None]) + dust[..., None] * np.array([0.62, 0.50, 0.38], np.float32)
        return M.bloom(fr, 0.85, 0.35)


HITS35 = [7133 / 30, 7143 / 30, 7160 / 30, 7167 / 30]


class E35n:   # 收刀「咔」落在最强拍 7154（切点 = 拍前 1 帧），印章落在 7161 拍
    def __init__(self):
        n = K.fbm(H // 2, W // 2, 1390, base=4, octaves=5)
        self.bg = cv2.resize(((0.02 + 0.04 * n)[..., None] * np.array([1.0, 0.82, 0.62], np.float32)).astype(np.float32), (W, H))
        self.tc = 7153 / 30

    def render(self, t):
        fr = self.bg.copy()
        fr = fx2.light_beam(fr, (1500, 100), (900, 960), 40, 600, t=t, strength=0.35, seed=13)
        slide = 0 if t >= self.tc else 70 * (1 - eio((t - self.t0) / (self.tc - self.t0)))
        dim = 0.55 if t >= self.tc + 0.4 else 1.0 - 0.45 * c01((t - self.tc) / 0.4) if t >= self.tc else 1.0
        fr, info = M.put(fr, t, 'S137/sheath_close|crop=0,0.58,1,1', (960 - slide, 600), w=2200, anc=(0.5, 0.5), rim=GOLDW, rim_amt=2.4, wind=0,
                         grade=dict(expo=0.8 * dim, sat=0.6, tint=(1.05, 0.98, 0.9), lift=0.0, gamma=1.12))
        if t >= self.tc:
            q = t - self.tc
            fr = E.flare_streak(fr, (1010, 640), amt=1.4 * math.exp(-q / 0.12), length=0.8)
            fr = RS.fx_sparks(fr, t, self.tc, (1010, 640), 1391, n=40, spd=500, dirv=(0, -1), spread=1.6, amt=0.9)
            p = c01((q - 0.13) / 0.35)
            if p > 0 and not ON['notitle']: fr = T.stamp_seal(fr, '鬼屠', 960, 470, 260, p, style='yin', rot=-4, seed=21)
        for th in HITS35:                                                  # 鼓点脉冲
            if t >= th: fr = fr * (1 + 0.12 * math.exp(-(t - th) / 0.08))
        return M.bloom(fr, 0.8, 0.35)


# ------------------------------------------------------------------ r6b：转场护栏
def _guard_frames():
    """#47：E21→E22 圆形 match_cut 圆外是 E21 定格帧，原来连 E21 的镜内字（#55 恢复的红「我」）一起定格 → 圆外挂一块红色残字。
    入圆这几帧里 E21 只出底板、不出字层。
    #50：E34 ELS 入镜的 warm_veil / 7061 硬切会给整帧 ca=2–3 的红青色差 → 人物轮廓挂红青边；这几帧色差归零。"""
    if getattr(M._Sec.frame_f, '_r6b', False): return
    f0 = M._Sec.frame_f
    t21 = M.E21.text

    def text21(self, fr, t):
        return fr if getattr(M, '_MC22', False) else t21(self, fr, t)
    M.E21.text = text21

    def frame_f(self, f):
        i22 = M.IDS.index('E22'); c22 = M.BOUNDS[i22]; post = M.CUTS.get('E22', ('hard', 0, 0))[2]
        M._MC22 = c22 <= f < c22 + post * M.FPS + 1
        try: fr, ca = f0(self, f)
        finally: M._MC22 = False
        if c22 <= f < c22 + post * M.FPS + 1: ca = 0                       # 色差 roll 会把右缘红通道卷到左缘 → 圆外一条红边
        if 'E34' in M.IDS:
            c34 = M.BOUNDS[M.IDS.index('E34')]
            if c34 - 6 <= f < (M.BOUNDS[M.IDS.index('E34L')] + 2 if 'E34L' in M.IDS else c34 + 10): ca = 0
        return fr, ca
    frame_f._r6b = True
    M._Sec.frame_f = frame_f


# ================================================================== 挂载
def _cls(name, body, base):
    c = type(name, (base,), {k: v for k, v in body.__dict__.items() if not k.startswith('__') or k == '__init__'})
    return c


def apply(mod):
    global M
    M = mod
    if getattr(M, '_r9_applied', False): return
    M._r9_applied = True
    if ON['wind']: _clamp_wind()
    if ON['mark']: _install_glyph()

    if ON['text'] and KEEPTXT:
        # r6 #55（2026-11-10 13:01 用户：「镜里那些横排或刻、写、印出来的歌词字，保留」）——晚于 #46，覆盖其「其余到结束文字全去」：
        # 横排大字 / 刀上刻字 / 朱印 / 血书 全部恢复；只去竖排（E06 若规则是、E08 伪装竖叠、E11 定/规 竖叠）与「判」（E21）。
        for nm in ('E06', 'E08', 'E11'):
            getattr(M, nm).text = _nil_text
        t21 = M.E21.text

        def text21(self, fr, t):                                            # 「判」照 D 段后令继续去，只留「我」
            r0 = R3.rub_text
            R3.rub_text = lambda fr_, items, *a, **k: r0(fr_, [it for it in items if it[0] != '判'], *a, **k)
            try: return t21(self, fr, t)
            finally: R3.rub_text = r0
        M.E21.text = text21
    elif ON['text']:
        for nm in ('E01', 'E02', 'E03', 'E04', 'E06', 'E07', 'E08', 'E09', 'E10', 'E11', 'E12', 'E13', 'E14T', 'E19', 'E20', 'E21', 'E22', 'E23', 'E24', 'E25', 'E26'):
            getattr(M, nm).text = _nil_text
        _wrap_init(M.E01, lambda s: setattr(s.B, 'engrave', lambda col, *a, **k: col))
        _wrap_init(M.E20, lambda s: setattr(s, 'tt', 1e9))
        # 2026-11-10 用户：片尾烧纸露出的「天」「理」「规」「章」「律」残字要保留 → E31 不再去字
        if not ON['mark']:                                                   # 对/错 不换符号时，至少去副句
            _wrap_init(M.E16, lambda s: setattr(s, 'l2', _Nil()))
            _wrap_init(M.E17, lambda s: setattr(s, 'l2', _Nil()))
            M.E16.text = lambda self, fr, t: self.l1.draw(fr, t)

    if ON['mark']:
        def p16(s):
            s.l1 = LyrO([('✓', 1450, 500, 470, 'serif_black', GOLD_T, M.CT(53, 0))], M.CT(53, 4) - 0.1, seed=120, glow=0.6, outline=4)
            s.l2 = _Nil()

        def p17(s):
            s.l1 = LyrO([('✗', 480, 500, 470, 'serif_black', REDT, M.CT(53, 4))], M.CT(53, 8) - 0.1, seed=130, glow=0.5, outline=4)
            s.l2 = _Nil()
        _wrap_init(M.E16, p16); _wrap_init(M.E17, p17)
        M.E16.text = lambda self, fr, t: self.l1.draw(fr, t)

    if ON['notitle']:
        M.Credits.credits = lambda self, fr, t: fr
        M.E33.credits = lambda self, fr, t: fr
        M.E29.render = lambda self, t: M.bloom(self.base(t), 0.85, 0.4)
        M.E30.render = lambda self, t: M.bloom(self.base(t), 0.85, 0.4)

    rep = {}
    if ON['e19']:
        rep['E19'] = _cls('E19', E19n, M.Shot); M.MOVE['E19'] = ('sine', 1.0, 1.04, 0, 0, 0, 0, 0, 0)
    if ON['e22']:
        rep['E22'] = _cls('E22', E22n, M.Shot); M.MOVE.pop('E22', None)
        M.CUTS['E22'] = ('match_cut', 0.0, 0.18, dict(shape='circle', center=(960, 352 if R6FIX else 286), radius=120))
    if ON['e23']:
        rep['E23'] = _cls('E23', E23n, M.Shot); M.MOVE.pop('E23', None)
        rep['E24'] = type('E24', (rep['E23'],), dict(__init__=E24n.__init__, render=E24n.render)); M.MOVE.pop('E24', None)
    if ON['e25']:
        rep['E25'] = _cls('E25', E25n, M.Shot)
        if R6FIX: M.MOVE['E25'] = ('expo_out', 1.05, 1.0, 0, 0, 0, 0, 0, 0)             # r6：1.12 起推会把头/脚推出画
        if R6FIX: M.CUTS['E25'] = ('impact', 0, 0, dict(col=(1.0, 0.8, 0.5), amp=8, soft=True))   # r6：slash_wipe 在 218.97–219.1 出 4 帧错位方块坏帧 → 硬切冲击，刀光在 6571 自己劈
    if ON['e34']:
        rep['E34'] = _cls('E34', E34n, M.Credits)
    shots = [(rep.get(c.__name__, c), f, a, b) for (c, f, a, b) in M.SHOTS]
    if ON['beat']:
        e34 = rep.get('E34', M.E34)
        tail = [(e34, 7037, 'S136', 'ELS')]
        if ON['e34'] and R6B:
            tail += [(_cls('E34L', E34L, M.Credits), 7061, 'S136L', 'LS')]
            M.CUTS['E34L'] = ('cut', 0, 0, {})                                    # 纯硬切（不加 hard 的 +15% 冲白帧，免得切点那帧过曝 10%）；重音靠抖 + 扬尘
            M.MOVE['E34'] = ('sine', 1.0, 1.0, 0, 0, 0, 0, 0, 0)                 # 推镜改在镜内做阶梯推（强拍才进）；保留条目让抖动生效
            M.MOVE['E34L'] = ('sine', 1.0, 1.0, 0, 0, 0, 0, 0, 0)
        if ON['e34']:
            tail += [(_cls('E34b', E34b, M.Credits), 7088, 'S136b', 'MS'), (_cls('E34c', E34c, M.Credits), 7105, 'S136c', 'ECU'),
                     (_cls('E34d', E34d, M.Credits), 7115, 'S136d', 'CU')]
            for k in ('E34b', 'E34c', 'E34d'): M.CUTS[k] = ('hard', 0, 0, {})
            M.MOVE['E34b'] = ('sine', 1.0, 1.04, 0, 0, 0, 0, 0, 0)
            M.MOVE['E34c'] = ('expo_out', 1.08, 1.0, 0, 0, 0, 0, 0, 0)
            M.MOVE['E34d'] = ('expo_out', 1.06, 1.0, 0, 0, 0, 0, 0, 0)
            M.SHAKE['E34b'] = [(7098 / 30, 3)]
            if R6FIX: M.SHAKE['E34'] = [(7040 / 30, 2), (7061 / 30, 2), (7072 / 30, 2)]          # r6 #51
            if R6B: M.SHAKE['E34'] = [(7040 / 30, 3)]; M.SHAKE['E34L'] = [(7061 / 30, 3), (7072 / 30, 3)]
        e35 = _cls('E35', E35n, M.Shot)
        tail += [(e35, 7126, 'S137', 'ECU')]
        M.SHAKE['E35'] = [(7133 / 30, 3), (7143 / 30, 3), (7153 / 30, 7), (7160 / 30, 4), (7167 / 30, 3)]
        rep['E35'] = e35
        shots = [s for s in shots if s[1] < 7037] + tail + [s for s in shots if s[1] >= 7174]
    if R6B: _guard_frames()
    for k, c in rep.items(): setattr(M, k, c)                               # E18/E36 按全局名取 E16/E17/E35
    M.SHOTS[:] = shots
    M.IDS[:] = [s[0].__name__ for s in shots]
    M.BOUNDS[:] = [s[1] for s in shots] + [M.F1]
