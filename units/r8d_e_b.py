"""第八轮 STYLE_D：E 段后半（EB 单元）—— 副歌终章收尾 + 尾奏片尾，帧 6638–7241（原镜号 S132–S138）。
只在 STYLE_D=1 时由 sec_e_final_outro 末尾的钩子 import 并 apply(mod)；STYLE_D=0 完全不加载，现版逐像素不变。

风格 D（日漫墨线 + 网点 + 严格黑白血红）：全部镜头换成 assets/gen/R8_D/EB/ 的新生图（RH_image2，提示词 jobs/r8_D_EB.json），
精灵合成一律 grade=NEU / rim=NORIM / wrap=0 / shade=None。切点、镜长、入转场、MOVE 运镜、SHAKE 冲击、鼓点表全部沿用 e_r9 之后的现版。
文字（USER_NOTES_r8）：
  - E31（S134）灼烧露出的「天」「理」「规」「章」「律」—— 画进生图 EB_scraps（逐字放大核对），代码只做「灰烬烧开、露出字」的动画。
  - 片名「谁定正邪」/「鬼屠 · 第二季」/「主题曲《谁定正邪》」、6 行出品署名、「鬼屠」印章 —— 合同要求（HANDOFF §1），保留；
    改为宣纸墨书（墨晕洇开，无描边/投影/外发光的电脑字效果），「邪」与印章血红，不用金。
  - E27c「天理昭彰」匾字（用户 11-11 要求看到）：画进生图 EB_plaque_front，代码只做斩开 —— 斩线落在「理｜昭」字缝。
  - 其余画面字一律不出。
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


def plate4(name):
    """4K 背景板（3840×2160 原分辨率；配 view4 取景，推近不糊）。"""
    k = ('4k', name)
    if k not in _P:
        _P[k] = cv2.cvtColor(cv2.imread(D + name + '.png'), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    return _P[k]


def view4(img, z=1.0, cx=W / 2, cy=H / 2, rot=0.0):
    """4K 板按 1920 坐标取景：z=1 = 整幅铺满画面。"""
    k = img.shape[1] / W
    return view(img, z / k, cx * k, cy * k, rot)


_L = {}
def lay(name, flip=False, base=D, feather=0):
    """精灵层（绿幕抠像 *_cut.png）；flip 水平翻转（同 c_kit.spr 的做法）。
    feather>0：alpha 碰到画布边的地方按噪声形状羽化掉 feather px（用户硬规则：任何图层不得露出裁切直边）。"""
    k = (base + name, flip, feather)
    if k not in _L:
        L = SP.SpriteLayer(base + name + '_cut.png') if (flip or feather) else SP.layer(base + name + '_cut.png')
        if flip:                                                                                 # 翻转写法同 c_kit.spr（新实例，不改共享缓存）
            for a in ('A', 'F', 'wind_w', 'ring'): setattr(L, a, np.ascontiguousarray(getattr(L, a)[:, ::-1]))
            x0, y0, x1, y1 = L.bbox; L.bbox = (1 - x1, y0, 1 - x0, y1); L.top = (1 - L.top[0], L.top[1])
        if feather:
            h, w = L.A.shape
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            dmin = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
            nz = cv2.resize(np.random.default_rng(len(name)).random((h // 24 + 2, w // 24 + 2)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
            A2 = L.A * np.clip((dmin - feather * (0.4 + 0.9 * nz)) / (feather * 0.5), 0, 1)
            L.A = np.ascontiguousarray(A2).astype(np.float32)
            ys, xs = np.nonzero(L.A > 0.5)                                                        # 羽化后重算包围盒 / 最高点 / 描边环（否则落脚与身高偏）
            if len(xs):
                L.bbox = (xs.min() / w, ys.min() / h, xs.max() / w, ys.max() / h)
                L.top = (xs[ys.argmin()] / w, ys.min() / h)
            L.ring = cv2.GaussianBlur(np.clip(L.A - cv2.erode(L.A, np.ones((5, 5), np.uint8)), 0, 1), (0, 0), 1.5)
        L._path = name
        _L[k] = L
    return _L[k]


EDGE_LOG = []
EV_LOG = []
def edge_check(L, M2, tag):
    """EB_EDGECHECK=1：精灵画布上 alpha>0 的边界点映射到画面后不得落进可见区（画幅 0..W × BAR..H-BAR，留 4px），否则记一条。"""
    if os.environ.get('EB_EDGECHECK') != '1': return
    A = L.A; h, w = A.shape
    pts = []
    for (ys, xs) in ((np.zeros(w, int), np.arange(w)), (np.full(w, h - 1), np.arange(w)), (np.arange(h), np.zeros(h, int)), (np.arange(h), np.full(h, w - 1))):
        m = A[ys, xs] > 0.06
        pts += list(zip(xs[m], ys[m]))
    if not pts: return
    P = np.float32(pts) @ M2[:, :2].T + M2[:, 2]
    vis = (P[:, 0] > 4) & (P[:, 0] < W - 4) & (P[:, 1] > BAR + 4) & (P[:, 1] < H - BAR - 4)
    if vis.any(): EDGE_LOG.append((tag, int(vis.sum())))


def draw(fr, L, t, src_px, dst, s, **kw):
    """src_px：精灵像素坐标（2048 宽工作分辨率）→ 画面 dst；s = 画面像素 / 精灵像素。"""
    a = dict(KW); a.update(kw)
    if os.environ.get('EB_EDGECHECK') == '1':
        Mx = cv2.getRotationMatrix2D((float(src_px[0]), float(src_px[1])), a.get('rot', 0.0), s); Mx[0, 2] += dst[0] - src_px[0]; Mx[1, 2] += dst[1] - src_px[1]
        edge_check(L, Mx, '%s@%.3f' % (os.path.basename(str(getattr(L, '_path', '?'))), t))
    return L.draw(fr, t, (src_px[0] / L.w, src_px[1] / L.h), dst, s, **a)


def draw_fit(fr, L, t, foot, h, **kw):
    """按包围盒高度落脚（put / fit 的写法）。"""
    a_, s_ = L.fit(h)
    return draw(fr, L, t, (a_[0] * L.w, a_[1] * L.h), foot, s_, **kw)


_NF = {}
def _noise2(seed, t, rate=0.7, gh=5, gw=9):
    """低频、随时间缓慢变化的 2 通道噪声场（约 -1..1）：粗网格随机数按 t*rate 在相邻两帧间 smoothstep 插值，再三次插值放大。
    rate 小 = 变化慢（0.6–0.9，1 秒才换 0.6–0.9 个网格）。"""
    q = t * rate; k0 = int(math.floor(q)); f = q - k0; f = f * f * (3 - 2 * f)
    out = []
    for k in (k0, k0 + 1):
        key = (seed, k, gh, gw)
        if key not in _NF:
            g = np.random.default_rng(int(seed) * 1009 + k).uniform(-1, 1, (gh, gw, 2)).astype(np.float32)
            _NF[key] = cv2.resize(g, (W, H), interpolation=cv2.INTER_CUBIC)
            if len(_NF) > 48: _NF.pop(next(iter(_NF)))
        out.append(_NF[key])
    return out[0] * (1 - f) + out[1] * f


def flutter(z, A, t, amp, band=36.0, seed=0, hair=1.0, cloth=1.0, red=1.0, wdir=(-1.0, 0.0)):
    """二级运动（用户 20:05：「湍流置换波浪太假」）：对透明底人物层 (z 预乘, A) 做**低振幅（2–5px）、低频、
    随时间缓慢变化**的噪声位移；只在轮廓内外 band px 的带里生效——躯干内部、脸、刀身一律不动。
    发丝（上部深色）/ 衣摆（下部）/ 红带（血红）各用一张独立噪声场驱动，互不同相；不加规则正弦（不会整张脸「水波」）。"""
    if amp <= 0: return z, A
    m = (A > 0.5).astype(np.uint8)
    din = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    edge = np.clip(1 - din / band, 0, 1) ** 1.5                                              # 轮廓内 band 宽的带
    ys, xs = np.nonzero(m)
    if not len(ys): return z, A
    top, bot = ys.min(), ys.max(); hh = max(1, bot - top)
    yy = np.arange(H, dtype=np.float32)[:, None]
    C = z / np.maximum(A, 1e-3)[..., None]
    lum = C.mean(-1); redm = np.clip((C[..., 0] - np.maximum(C[..., 1], C[..., 2])) * 3, 0, 1)
    skin = np.clip((lum - 0.55) * 5, 0, 1) * (1 - redm)                                       # 肤色 / 亮面（脸、手）：不动
    up = 1 - np.clip((yy - top - 0.45 * hh) / (0.15 * hh), 0, 1)
    low = np.clip((yy - top - 0.55 * hh) / (0.20 * hh), 0, 1)
    sup = cv2.dilate(A, np.ones((int(band) | 1, int(band) | 1), np.uint8))                     # 轮廓外一圈（飘出去的发梢）
    wh = cv2.GaussianBlur((up * (1 - redm) * (lum < 0.35)).astype(np.float32), (0, 0), 5) * hair
    wc = cv2.GaussianBlur((low * (1 - redm)).astype(np.float32), (0, 0), 5) * cloth
    wr = cv2.GaussianBlur(redm * A, (0, 0), 5) * red
    base = edge * sup * (1 - skin)
    N1, N2, N3 = _noise2(seed + 1, t, 0.8), _noise2(seed + 2, t, 0.6), _noise2(seed + 3, t, 0.9)
    dx = (wh * N1[..., 0] + wc * N2[..., 0] + wr * N3[..., 0] * 1.3 + (wh + wr) * 0.35 * wdir[0]) * base * amp
    dy = (wh * N1[..., 1] + wc * N2[..., 1] * 0.5 + wr * N3[..., 1]) * base * amp * 0.7
    dx = cv2.GaussianBlur(dx.astype(np.float32), (0, 0), 6); dy = cv2.GaussianBlur(dy.astype(np.float32), (0, 0), 6)
    yg, xg = E.grid()
    mx = (xg - dx).astype(np.float32); my = (yg - dy).astype(np.float32)
    return cv2.remap(z, mx, my, cv2.INTER_LINEAR), cv2.remap(A, mx, my, cv2.INTER_LINEAR)


def hard_star(fr, c, r, amt=1.0, n=8, rot=0.0, col=(1.0, 1.0, 1.0)):
    """墨线星芒：硬边白色尖刺（无高斯光晕），四长四短，外加一圈墨线勾边。"""
    if amt <= 0.02 or r < 2: return fr
    Lw = np.zeros((H, W), np.float32)                                                       # 1:1 画布（不要 *8 再缩小 —— 会整块落进画布外）
    for i in range(n):
        a = math.radians(rot + i * 360.0 / n); ln = r * (1.0 if i % 2 == 0 else 0.45); wd = r * (0.06 if i % 2 == 0 else 0.04)
        tip = (c[0] + math.cos(a) * ln, c[1] + math.sin(a) * ln)
        b1 = (c[0] + math.cos(a + 1.5708) * wd, c[1] + math.sin(a + 1.5708) * wd); b2 = (c[0] - math.cos(a + 1.5708) * wd, c[1] - math.sin(a + 1.5708) * wd)
        cv2.fillConvexPoly(Lw, np.float32([tip, b1, b2]).astype(np.int32), 1.0, cv2.LINE_AA, 3)
    cv2.circle(Lw, (int(c[0]), int(c[1])), max(1, int(r * 0.09)), 1.0, -1, cv2.LINE_AA, 3)
    ink = np.clip(cv2.dilate(Lw, np.ones((5, 5), np.uint8)) - Lw, 0, 1)
    fr = fr * (1 - (ink * amt * 0.8)[..., None]) + (ink * amt * 0.8)[..., None] * INKC
    return fr * (1 - (Lw * amt)[..., None]) + (Lw * amt)[..., None] * np.asarray(col, np.float32)


def to_scr(L, src_px, dst, s, p, rot=0.0):
    X = (p[0] - src_px[0]) * s; Y = (p[1] - src_px[1]) * s
    c, si = math.cos(math.radians(-rot)), math.sin(math.radians(-rot))
    return (dst[0] + X * c - Y * si, dst[1] + X * si + Y * c)


def view(img, z=1.0, cx=W / 2, cy=H / 2, rot=0.0):
    """全幅图层：图上 (cx,cy) 放到画面中心、缩放 z。取景中心夹回图内（倍率 z 本身不动），保证画面不越出图外、
    不会出现反射接缝或图层直边；确实夹了才记一条 EV_LOG（EB_EDGECHECK=1 时打印）。"""
    h, w = img.shape[:2]
    hw, hh = W / (2.0 * z), H / (2.0 * z)
    cx2 = float(np.clip(cx, hw, max(hw, w - hw))); cy2 = float(np.clip(cy, hh, max(hh, h - hh)))
    if (abs(cx2 - cx) > 0.5 or abs(cy2 - cy) > 0.5) and os.environ.get('EB_EDGECHECK') == '1':
        EV_LOG.append(('view clamp', round(cx, 1), round(cy, 1), round(cx2, 1), round(cy2, 1), round(z, 3), (w, h)))
    cx, cy = cx2, cy2
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
def credit(fr, role, names, x, y, p, color, role_size=42, name_size=84, seal_text=None, seed=None, bed=True):
    """署名（用户 20:05「文字信息看不清」）：字号加大到职务 42 / 人名 84（原 32 / 66）；bed=True 时先在字块下铺一块干净的底——
    墨字铺宣纸白（毛边、淡网点边），白字铺墨黑——底与字一起淡入，保证 1080p 下清楚；章也随字号放大。"""
    st = seal_text or (role[0] if names[0][0].isascii() else names[0][0])
    sd = zlib.crc32(role.encode('utf-8')) % 50 if seed is None else seed
    kw = dict(role_size=role_size, name_size=name_size, seal_text=st, seal_size=int(name_size * 0.62), color=color, name_font='kai', seed=sd)
    if bed:
        ink = color != 'white'
        base = np.full((H, W, 3), 1.0 if ink else 0.0, np.float32)
        g = R3.credit_block_up(base.copy(), role, names, x, y, 1.0, **kw)
        m = np.clip(np.abs(g - base).max(-1) * 3, 0, 1)
        if m.max() > 0:
            k = ('bed', role, x, y, int(ink))
            if k not in _P:
                ys_, xs_ = np.nonzero(m > 0.05)
                pad = int(name_size * 0.5)
                bx0, by0, bx1, by1 = xs_.min() - pad, ys_.min() - pad, xs_.max() + pad, ys_.max() + pad
                yy, xx = E.grid()
                nz = cv2.resize(np.random.default_rng(sd).random((H // 24 + 2, W // 24 + 2)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
                d = np.minimum.reduce([xx - bx0, bx1 - xx, yy - by0, by1 - yy]) + (nz - 0.5) * pad * 0.9          # 毛边纸块
                _P[k] = (np.clip(d / (pad * 0.55), 0, 1) * np.clip((bx1 - bx0) / 320, 0.35, 1)).astype(np.float32)
            b = _P[k] * eout(c01(p * 3))
            col = np.float32([0.975, 0.975, 0.965]) if ink else np.float32([0.025, 0.025, 0.025])
            fr = fr * (1 - b[..., None] * 0.94) + col * b[..., None] * 0.94
    return R3.credit_block_up(fr, role, names, x, y, p, **kw)


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
        self.L = lay('EB_eyes', feather=30)
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


class E27b(Shot):   # S132x 斩（返工：亮底 + 两个关键姿势）：白天血红日（EB_sky）前，EB_stroke 生图飞白斩痕沿弧线一笔写出（墨线勾边，白芯在亮底上也读得出）；
    #  6658–6659 反白冲击（硬边纯黑剪影 + 只留血红）→ 出刀定姿 EB_slash → 6666 鼓点硬切收势 EB_slash_end（起身、刀尖垂向右下）；发梢 / 红带二级飘动
    T_END = 6666 / 30

    def __init__(self):
        self.L = lay('EB_slash'); self.L2 = lay('EB_slash_end', feather=12); self.S = lay('EB_stroke')
        self.bg = view4(plate4('EB_sky'), 1.30, 1060, 470)
        self.sx = np.ascontiguousarray(np.broadcast_to(self.S.gx / max(1, self.S.w - 1), (self.S.h, self.S.w))).astype(np.float32)

    def render(self, t):
        u = self.u(t); a = t - self.t0; k = int(round(a * FPS))
        pr = eout(c01(a / 0.20), 3)
        head = 0.02 + 1.03 * pr
        ext = np.clip((head - self.sx) / 0.04, 0, 1)
        fr = view(self.bg, 1.06 + 0.02 * u, 960 + 20 * (u - 0.5), 540)
        ss = W / self.S.w * 1.06; dst = (960 + 30 * (u - 0.5), 520)
        z, As = draw(np.zeros_like(fr), self.S, t, (1024, 576), dst, ss, breathe=0, wind_amp=0)
        Mx = cv2.getRotationMatrix2D((1024.0, 576.0), 0, ss); Mx[0, 2] += dst[0] - 1024; Mx[1, 2] += dst[1] - 576
        ew = cv2.warpAffine(ext, Mx, (W, H))
        Aw = As * ew
        Fz = z / np.maximum(As, 1e-3)[..., None]
        ink = np.clip(cv2.dilate(Aw, np.ones((5, 5), np.uint8)) - Aw, 0, 1)                    # 斩痕墨线勾边
        fr = fr * (1 - 0.9 * ink[..., None]) + INKC * 0.9 * ink[..., None]
        fr = fr * (1 - Aw[..., None]) + Fz * Aw[..., None]
        # 人物：出刀定姿（滑入 + 横向模糊衰减）→ 鼓点硬切收势；发梢 / 红带二级飘动
        sp = 1 - eout(c01(a / 0.12), 2)
        zc = np.zeros_like(fr)
        if t < self.T_END:
            zc, A = draw(zc, self.L, t, (1072, 1146), (720 - 50 * sp, 1010), 880 / 1141, mblur=(int(40 * sp) if k >= 2 else 0, 0), wind_amp=6.0, breathe=0)
        else:
            zc, A = draw_fit(zc, self.L2, t, (800, 1012), 905, wind_amp=6.0, breathe=0.004)
        zc, A = flutter(zc, A, t, 4.0, band=40.0, seed=2)
        fr = fr * (1 - A[..., None]) + zc
        if t >= self.T_END and t < self.T_END + 2 / 30:                                         # 收势硬切：一帧白边闪
            fr = fr * 1.12 + 0.05
        if t < self.T_END:
            tip = to_scr(self.L, (1072, 1146), (720 - 50 * sp, 1010), 880 / 1141, (1990, 1060))
        else:
            a2, s2 = self.L2.fit(905)
            tip = to_scr(self.L2, (a2[0] * self.L2.w, a2[1] * self.L2.h), (800, 1012), s2, (1345, 925))
        fr = spark2(fr, t, 2720, tip, self.t0 + 0.02, n=70, life=0.55, speed=(500, 1500), dirc=(0.6, -0.5), spread=1.0, grav=1300, area=(30, 20))
        fr = ink_spatter(fr, t, 2726, tip, self.t0 + 0.02, n=60, life=0.5, speed=(400, 1300), dirc=(0.7, -0.4), spread=1.2, grav=1200, area=(40, 20))
        fr = ash(fr, t, self.t0, 2725, n=30, amt=0.45, drift=(80, -60), red=0.3)
        if k < 2:                                                                              # 反白冲击帧：白底、人物硬边纯黑剪影、只留斩痕的血红
            Ah = np.clip((A - 0.35) * 4, 0, 1)
            red = np.clip((Fz[..., 0] - np.maximum(Fz[..., 1], Fz[..., 2])) * 3, 0, 1) * Aw
            fr = np.ones_like(fr) * 0.97
            fr = fr * (1 - red[..., None]) + REDC * red[..., None]
            fr = fr * (1 - Ah[..., None]) + 0.015 * Ah[..., None]
        elif k == 2:
            fr = fr * 1.15 + 0.04
        return fr


class E27c(Shot):   # S132y 匾碎（用户 11-11：「天理昭彰」要看得到字）：EB_plaque_front 墨线黑漆匾，「天理昭彰」白字刻进生图（逐字核对）；
    #  低角度 3/4 透视（左近右远、仰视），一刀从「理｜昭」字缝斩开（斩线按生图字形蒙版定位，不碰任何笔画），两半各自翻转错开、下坠，
    #  断口血红余烬 + 白热斩线，碎木片扑镜（EB_plaque 的碎片层），背景 EB_hall 暗殿慢推
    CUT = ((1078.0, 163.0), (1032.0, 949.0))              # 生图 2048 宽坐标：理 右缘 x≈1001、昭 左缘 x≈1107，斩线全程在字缝内
    SRC = ((29.0, 163.0), (2021.0, 163.0), (2021.0, 949.0), (29.0, 949.0))   # 匾包围盒四角（2048 宽）
    DST = ((70.0, 250.0), (1790.0, 175.0), (1820.0, 735.0), (40.0, 895.0))   # 画面：左近右远、轻仰视

    def __init__(self):
        self.bg = np.clip(plate('EB_hall'), 0, 1) ** 0.55                                       # 暗殿提一档（网点中灰，不压成一团黑）
        P = cv2.cvtColor(cv2.imread(D + 'EB_plaque_front_cut.png', cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255
        F, A = P[..., :3], P[..., 3]
        h, w = A.shape
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        (x0, y0), (x1, y1) = self.CUT
        side = (xx - (x0 + (x1 - x0) * (yy - y0) / (y1 - y0))) > 0                         # True = 右半（昭彰）
        sd = np.abs(xx - (x0 + (x1 - x0) * (yy - y0) / (y1 - y0)))
        edge = (np.exp(-(sd / 7.0) ** 2) * A).astype(np.float32)                             # 断口带（生图空间）
        Mp = cv2.getPerspectiveTransform(np.float32(self.SRC), np.float32(self.DST))
        warp = lambda a: cv2.warpPerspective(a, Mp, (W, H), flags=cv2.INTER_LINEAR)
        self.halves = []
        for sg in (False, True):
            m = (side == sg).astype(np.float32)
            Am = warp(A * m); Fm = warp(F * (A * m)[..., None]); Em = warp(edge * m)
            ys_, xs_ = np.nonzero(Am > 0.5)
            self.halves.append((Fm, Am, Em, (float(xs_.mean()), float(ys_.mean()))))
        c0 = cv2.perspectiveTransform(np.float32([[self.CUT[0], self.CUT[1]]]), Mp)[0]
        self.cut_scr = (tuple(c0[0]), tuple(c0[1]))
        # 碎木片：从同一张正面匾里切下断口两侧的一窄条木料 + 边框屑，按斩线重新散射（不再借用另一张背面匾）
        band = (sd < 26).astype(np.float32) * A                                                # 生图空间（h×w）
        ys_, xs_ = np.nonzero(band > 0.4)
        if len(xs_) > 200:
            r = np.random.default_rng(2731)
            pick = r.choice(len(xs_), size=min(700, len(xs_)), replace=False)
            db = np.zeros(A.shape, np.float32); db[ys_[pick], xs_[pick]] = 1.0
            db = cv2.dilate(db, np.ones((3, 3), np.uint8)) * A
            Fw = warp(F * db[..., None].repeat(3, -1)); Aw = warp(db)
            self.deb = (Fw, Aw)
        else:
            self.deb = None
        yv, xv = E.grid()
        (a0x, a0y), (a1x, a1y) = self.cut_scr
        d = np.array([a1x - a0x, a1y - a0y]); d /= np.linalg.norm(d); n = np.array([-d[1], d[0]])
        self.sline = ((xv - a0x) * n[0] + (yv - a0y) * n[1]).astype(np.float32)                # 画面上斩线的有符号距离
        self.cmid = ((a0x + a1x) / 2, (a0y + a1y) / 2)

    def render(self, t):
        u = self.u(t); a = t - self.t0
        fr = view(self.bg, 1.04 + 0.03 * u, 960, 540 - 20 * (u - 0.5))                         # 背景慢推（比匾慢 = 视差）
        g = eout(c01(a / 0.10), 2)                                                              # 0–0.1s：沿斩线裂开一道缝（字完整清楚）
        q = c01((a - 0.10) / 0.40)                                                              # 0.1s 起两半错开、翻转、下坠
        hot = 1.0 + 1.4 * math.exp(-a / 0.12)
        for j, (Fm, Am, Em, c) in enumerate(self.halves):
            sg = -1 if j == 0 else 1
            rot = -sg * 7 * eout(q, 2)
            dx = sg * (14 * g + 80 * eout(q, 2)); dy = (0 if j == 0 else -10 * g) + 170 * q * q * (0.8 if j == 0 else 1.0)
            Mx = cv2.getRotationMatrix2D(c, rot, 1.0); Mx[0, 2] += dx; Mx[1, 2] += dy
            Fw = cv2.warpAffine(Fm, Mx, (W, H)); Aw = cv2.warpAffine(Am, Mx, (W, H)); Ew = cv2.warpAffine(Em, Mx, (W, H))
            fr = fr * (1 - Aw[..., None]) + Fw + (Ew * (hot - 1) * 1.1)[..., None] * REDC + (Ew * math.exp(-a / 0.06))[..., None] * 0.9
        sl = np.exp(-(self.sline / (3 + 30 * q)) ** 2) * math.exp(-a / 0.08)                  # 白热斩线余光（墨线画面上一道硬白）
        fr = fr + sl[..., None] * 1.2
        sd = 1.0 + 0.9 * eout(c01(a / 0.5), 2)
        al = 1 - sstep(0.25, 0.5, a)
        if self.deb is not None and al > 0.01:                                                   # 断口木屑扑镜
            F, Ad = self.deb
            fr, _ = rgba_piece(fr, F, Ad * al, 960, 540, sd, 0, pc=(960, 540))
        fr = spark2(fr, t, 2730, self.cmid, self.t0, n=60, life=0.5, speed=(300, 1200), dirc=(0, -1), spread=1.5, grav=900, area=(30, 200))
        fr = ink_spatter(fr, t, 2733, self.cmid, self.t0, n=40, life=0.5, speed=(300, 1000), dirc=(1, 0), spread=2.5, grav=800, area=(20, 220))
        return fr


class E28(Shot):   # S132b ECU 马尾 + 血红腰带在逆光里翻飞：EB_sash（风吹 + 腰带行波二级运动），背景 EB_dawn 天空虚焦
    def __init__(self):
        self.L = lay('EB_sash', feather=30)
        self.bg = view4(plate4('EB_sky'), 1.45, 700, 440)
        yy, xx = E.grid(); self.xx, self.yy = xx, yy

    def render(self, t):
        u = self.u(t)
        fr = view(self.bg, 1.06, 960 - 30 * (u - 0.5), 540)                                        # 背景视差（以中点为零）
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
    """片名底板：EB_paper 拆层——宣纸底（去掉山和日后补纸）/ 远山 / 近山与溅墨 / 血红朝日；各层慢视差（以镜头中点为零），
    朝日缓升，远山墨色轻轻呼吸（墨晕一涨一收），两层墨雾横向漂移。图层都比画面大 PAD，位移不会露出图层直边。"""
    PAD = 48
    _LAY = {}

    def __init__(self):
        if not TitleD._LAY:
            p = self.PAD
            im = cv2.resize(cv2.cvtColor(cv2.imread(D + 'EB_paper.png'), cv2.COLOR_BGR2RGB), (W + 2 * p, H + 2 * p), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
            lum = im.mean(-1)
            red = np.clip((im[..., 0] - np.maximum(im[..., 1], im[..., 2])) * 3, 0, 1)
            red = cv2.GaussianBlur(cv2.dilate(red, np.ones((5, 5), np.uint8)), (0, 0), 1.5)
            ink = np.clip((0.86 - lum) / 0.5, 0, 1) * (1 - red)
            yy = np.arange(H + 2 * p, dtype=np.float32)[:, None]
            far = ink * (1 - sstep(760, 860, yy)); near = ink * sstep(760, 860, yy)
            hole = (cv2.dilate(((red > 0.05) | (ink > 0.05)).astype(np.uint8), np.ones((9, 9), np.uint8)))
            sm = cv2.resize(im, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
            hs = cv2.resize(hole, (sm.shape[1], sm.shape[0]), interpolation=cv2.INTER_NEAREST)
            fill = cv2.inpaint((sm * 255).astype(np.uint8), hs, 6, cv2.INPAINT_TELEA).astype(np.float32) / 255
            fill = cv2.resize(fill, (W + 2 * p, H + 2 * p))
            grain = im - cv2.GaussianBlur(im, (0, 0), 3)
            paper = np.where(hole[..., None] > 0, fill + grain * 0.5, im)
            TitleD._LAY.update(paper=paper.astype(np.float32), im=im, red=red.astype(np.float32), far=far.astype(np.float32), near=near.astype(np.float32))

    def _crop(self, a, dx, dy):
        p = self.PAD; x0 = int(round(p - dx)); y0 = int(round(p - dy))
        return a[y0:y0 + H, x0:x0 + W]

    def base(self, t):
        u = self.u(t); tm = (self.t0 + self.t1) / 2; L = TitleD._LAY
        v = (t - tm)                                                                            # 中点为零
        fr = self._crop(L['paper'], 3 * v, 0).copy()
        br = 1.0 + 0.10 * math.sin(2 * math.pi * t / 1.7)                                       # 墨晕呼吸
        for key, dx, halo in (('far', 8 * v, 0.05), ('near', 18 * v, 0.03)):
            a = self._crop(L[key], dx, 0); c = self._crop(L['im'], dx, 0)
            hal = cv2.GaussianBlur(a, (0, 0), 10) * halo * (0.5 + 0.5 * math.sin(2 * math.pi * t / 1.7))
            fr = fr * (1 - hal[..., None])
            a = np.clip(a * br, 0, 1)
            fr = fr * (1 - a[..., None]) + c * a[..., None]
        a = self._crop(L['red'], 5 * v, -14 * v)                                                # 朝日缓升
        c = self._crop(L['im'], 5 * v, -14 * v)
        fr = fr * (1 - a[..., None]) + c * a[..., None]
        fr = mist(fr, t, 1341, 700, 960, 22, amt=0.30, col=(0.97, 0.97, 0.97), t_ref=tm)
        fr = mist(fr, t, 1342, 820, 960, 40, amt=0.22, col=(0.55, 0.55, 0.55), scale=6, t_ref=tm)
        return fr


class E29(TitleD):   # S133 片名「谁定正邪」墨书洇开
    def render(self, t):
        fr = self.base(t)
        L = title_ink(t)
        return T.compose(fr, L, shadow=0, glow=0)


class E30(TitleD):   # S133b 血红干笔斩痕（EB_brush_line 生图飞白 + 溅墨）劈过片名 → 「谁定正邪」沿斩线碎成墨屑散干净（0.45s）→
    #  再墨晕洇出「鬼屠 · 第二季」→ 血红「鬼屠」印 → 副标题「主题曲《谁定正邪》」（加大、墨黑）。两段不叠。
    def __init__(self):
        TitleD.__init__(self)
        ang = math.radians(-12)
        d = np.array([math.cos(ang), math.sin(ang)]); n = np.array([-d[1], d[0]])
        c = np.array([960.0, 470.0])
        self.d, self.n, self.c = d, n, c
        yy, xx = E.grid()
        self.s = ((xx - c[0]) * n[0] + (yy - c[1]) * n[1]).astype(np.float32)
        self.uu = (((xx - c[0]) * d[0] + (yy - c[1]) * d[1]) / 2200 + 0.5).astype(np.float32)
        sl = cv2.cvtColor(cv2.imread(D + 'EB_brush_line_cut.png', cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255
        ys, xs = np.nonzero(sl[..., 3] > 0.5)
        x0, x1 = xs.min(), xs.max(); y0 = float(np.median(ys))
        Q0, Q1 = c - d * 1180, c + d * 1180
        sc = np.linalg.norm(Q1 - Q0) / (x1 - x0)
        M2 = sc * np.outer(d, [1, 0]) + 0.75 * sc * np.outer(n, [0, 1])
        Mx = np.hstack([M2, (Q0 - M2 @ np.array([x0, y0]))[:, None]])
        w_ = cv2.warpAffine(sl, Mx, (W, H), flags=cv2.INTER_LINEAR)
        self.slF, self.slA = w_[..., :3], w_[..., 3]
        self.title = None
        self.nz = cv2.resize(K.fbm(H // 8, W // 8, 3021, base=6, octaves=4), (W, H)).astype(np.float32)

    def render(self, t):
        fr = self.base(t)
        q = t - TS
        if self.title is None: self.title = title_ink(999.0)
        L = self.title
        if q < 0:
            return T.compose(fr, L, shadow=0, glow=0)
        if q < 0.45:                                                                            # 片名沿斩线错开、碎成墨屑散尽
            e = eout(q / 0.30)
            dis = c01(q / 0.42)
            up = (self.s < 0)
            Lz = T.Layer()
            for part, sg in ((up, -1), (~up, 1)):
                Mx = np.float32([[1, 0, sg * 50 * e], [0, 1, sg * 30 * e + 40 * q * q]])
                Ap = cv2.warpAffine(L.A * part, Mx, (W, H)); Cp = cv2.warpAffine(L.C * part[..., None], Mx, (W, H))
                sel = Ap > Lz.A; Lz.A = np.maximum(Lz.A, Ap); Lz.C[sel] = Cp[sel]
            keep = np.clip((self.nz - dis * 1.15 + 0.05) * 9, 0, 1)                             # 噪声溶解：一块块剥成墨屑
            Lz.A = Lz.A * keep
            Lz._touch(0, 0, W, H)
            fr = T.compose(fr, Lz, shadow=0, glow=0)
            fr = ink_spatter(fr, t, 3016, (960, 470), TS + 0.08, n=90, life=0.45, speed=(150, 700), dirc=(0, 1), spread=2.6, grav=700, area=(480, 90))
        hd = c01((q + 0.03) / 0.08)                                                            # 干笔斩痕一笔写出（左→右）、0.22s 起沿笔势收走
        if hd > 0:
            er = 1.08 * eio(c01((q - 0.22) / 0.26))
            rev = np.clip((hd * 1.05 - self.uu) / 0.03, 0, 1) * np.clip((self.uu - er) / 0.03, 0, 1) * self.slA
            fr = fr * (1 - rev[..., None]) + self.slF * rev[..., None]
        fr = ink_spatter(fr, t, 3010, (960, 470), TS, n=50, life=0.5, speed=(300, 1100), dirc=(self.n[0], self.n[1]), spread=1.4, grav=900, area=(500, 10))
        fr = K.sparks(fr, t, 3012, (960, 470), n=30, life=0.45, speed=(250, 900), dirc=(-self.n[0], -self.n[1]), spread=1.2, grav=900, burst=True, t0=TS,
                      area=(500, 10), color=(0.75, -0.25, -0.25))
        p = c01((q - 0.50) / 0.6)                                                               # 片名散尽后才洇出主标题
        if p > 0:
            L2 = T.Layer()
            for i, (ch, x, sz) in enumerate((('鬼', 505, 200), ('屠', 705, 200), ('第', 1025, 200), ('二', 1215, 214), ('季', 1405, 200))):
                e = c01(p * 1.6 - i * 0.12)
                if e <= 0: continue
                L2.paste(T.ink_bleed_glyph(ch, 'kai', sz, e, seed=21 + i, bleed=0.5), x, 470, tuple(INKC))
            fr = T.compose(fr, L2, shadow=0, glow=0)
            cv2.circle(fr, (860, 475), int(13 * eout(p)), tuple(float(v) for v in REDC), -1, cv2.LINE_AA)
            sp = c01((q - 0.80) / 0.5)
            if sp > 0: fr = T.stamp_seal(fr, '鬼屠', 1610, 470, 130, sp, style='yin', rot=-5, seed=9, color=tuple(REDC))
            s2 = c01((q - 1.00) / 0.5)
            if s2 > 0:
                L3 = T.Layer()
                for i, ch in enumerate('主题曲《谁定正邪》'):
                    T.place(L3, ch, 960 + (i - 4) * 70, 660, 58, (0.015, 0.015, 0.015), 'serif_b', alpha=eout(s2), texture=False)
                fr = T.compose(fr, L3, shadow=0, glow=0)
        return fr


# ================================================================== 尾奏 · 署名
class E31(CreditsD):   # S134 正俯拍：焦土（EB_ground）上散着五片烧焦残纸（EB_scraps，字画进生图）；灰烬自纸面烧开、露出「天」「理」「规」「章」「律」，
    #  焦边余烬一明一灭逐渐冷却、细烟上升；署名① 出品人 / 编剧导演（白字，暗地）
    LAYOUT = {'天': (430, 400, -12, 0.60), '理': (810, 660, 14, 0.56), '规': (1075, 335, 6, 0.50), '章': (330, 790, -18, 0.50), '律': (1150, 805, 22, 0.48)}
    ORDER = ['理', '天', '规', '章', '律']     # 生图里的连通块按质心 (x,y) 映射：见 __init__

    def __init__(self):
        self.blocks = [('出品人', ['西几王传媒'], 1700, 185, 227.85, 0.9), ('编剧 / 导演', ['苏打'], 1430, 185, 228.45, 0.8)]
        self.bg = np.clip(plate('EB_ground', flip=True), 0, 1) ** 0.62                        # 焦土提一档（网点中灰，白灰烬占面积）
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
        fr = view(self.bg, 1.06, 960 - 14 * (u - 0.5), 540)
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


class E32(CreditsD):   # S135 握刀（返工：中式直刀 + 中式护手 EB_hilt2，与定妆照 / E35 统一）手沿刀身滑移，寒光自护手扫到刀尖（硬边白条 + 墨线星芒）；
    #  背景清晰的白天墨云（EB_sky，无景深虚化）；署名② 移到右上纯白天空（墨书）
    ccol = 'ink'

    def __init__(self):
        self.blocks = [('美术设计', ['Cait'], 1720, 170, 230.15, 0.8), ('后期总监', ['沉溺'], 1440, 170, 230.75, 0.8)]
        self.L = lay('EB_hilt2', feather=30)
        self.bg = view4(plate4('EB_sky'), 1.35, 1100, 520)          # 白天墨云上部（1.35 倍，取景中心在窗口内）
        self.d = np.array([0.964, -0.268])

    def render(self, t):
        u = self.u(t)
        fr = view(self.bg, 1.06 + 0.02 * u, 960 + 20 * (u - 0.5), 540)
        sl = 60 * (eio(u) - 0.5)
        s = 1.10; src = (860, 840)
        dst = (990 + self.d[0] * sl, 780 + self.d[1] * sl)
        zc, A = draw(np.zeros_like(fr), self.L, t, src, dst, s, breathe=0.002, wind_amp=3.0)
        zc, A = flutter(zc, A, t, 2.5, band=50.0, seed=5, red=0.3, cloth=0.6)                 # 发梢 / 衣领：只动轮廓带
        fr = fr * (1 - A[..., None]) + zc
        g0 = to_scr(self.L, src, dst, s, (930, 815)); g1 = to_scr(self.L, src, dst, s, (2040, 505))
        k = eio(c01((u - 0.15) / 0.7))
        px, py = g0[0] + (g1[0] - g0[0]) * k, g0[1] + (g1[1] - g0[1]) * k
        if 0.02 < k < 0.99:
            yy, xx = E.grid()
            along = (xx - px) * self.d[0] + (yy - py) * self.d[1]
            band = np.clip(1 - np.abs(along) / 46, 0, 1) ** 0.3 * (np.abs(along) < 46)            # 硬边白条（刃面反光，只落在刀身上）
            C = zc / np.maximum(A, 1e-3)[..., None]
            steel = np.clip((C.mean(-1) - 0.45) * 4, 0, 1) * A
            fr = fr + (band * steel)[..., None] * 0.6
            fr = hard_star(fr, (px, py), 46, amt=0.9 * math.sin(math.pi * k), rot=12)
        return fr


class E33(CreditsD):   # S135b（返工：换景 + 去亮漆）雪地上横着一柄中式直刀（EB_scabbard2，哑光墨线 + 网点），血红穗在晨风里摆；
    #  刀身压进雪里一道浅槽 + 网点接触影，细雪飘落；署名③ AI画师（墨书，左上）
    ccol = 'ink'

    def __init__(self):
        self.blocks = [('AI画师', ['沉溺', '雪晴', '索恩'], 380, 175, 232.35, 1.0)]
        self.kws = dict(role_size=44, name_size=82, seal_text='画', seed=7)
        self.fade = False
        self.L = lay('EB_scabbard2')
        self.bg = view4(plate4('EB_snow'), 2.1, 1000, 790)
        yy, xx = E.grid(); self.xx, self.yy = xx, yy

    def render(self, t):
        u = self.u(t)
        fr = view(self.bg, 1.06 + 0.02 * u, 960 - 24 * (u - 0.5), 540)
        s = 0.84; src = (1024, 510); dst = (1010 - 36 * (u - 0.5), 650)
        zc, A = draw(np.zeros_like(fr), self.L, t, src, dst, s, breathe=0, wind_amp=0)
        top = to_scr(self.L, src, dst, s, (40, 560)); bot = to_scr(self.L, src, dst, s, (480, 1000))
        wy = np.clip((self.yy - top[1]) / max(1.0, bot[1] - top[1]), 0, 1) ** 1.3
        wx = np.clip((self.xx - (top[0] - 60)) / 600, 0, 1) * (self.xx < bot[0] + 160)
        dx = (30 * math.sin(t * 2.6) + 11 * math.sin(t * 5.3 + 1.0)) * wy * wx                 # 红穗摆（越往下越大）
        dy = 6 * math.sin(t * 3.1) * wy * wx
        mx = (self.xx - dx).astype(np.float32); my = (self.yy - dy).astype(np.float32)
        zc = cv2.remap(zc, mx, my, cv2.INTER_LINEAR); A = cv2.remap(A, mx, my, cv2.INTER_LINEAR)
        C = zc / np.maximum(A, 1e-3)[..., None]
        red = np.clip((C[..., 0] - np.maximum(C[..., 1], C[..., 2])) * 3, 0, 1)
        lum = C.mean(-1, keepdims=True)
        matte = np.minimum(C, 0.30 + 0.25 * lum)                                                 # 去镜面亮漆：高光压成哑光
        C = C * red[..., None] + matte * (1 - red[..., None])
        zc = C * A[..., None]
        body = A * (1 - red)                                                                     # 雪槽 + 网点接触影（只在刀身下）
        sh = cv2.GaussianBlur(np.roll(body, 14, 0), (0, 0), 7)
        groove = np.clip(cv2.dilate(body, np.ones((1, 9), np.uint8)) - body, 0, 1)                 # 雪面压痕：一道浅槽（唯一的一层压暗）
        shade = np.clip(0.22 * sh + 0.25 * cv2.GaussianBlur(np.roll(body, 10, 0), (0, 0), 6) + 0.16 * groove, 0, 0.42)
        fr = fr * (1 - shade[..., None]) + toned(shade * 0.6, 1.0)[..., None] * 0.10
        ink = np.clip(cv2.dilate(A, np.ones((3, 3), np.uint8)) - A, 0, 1)                         # 墨线勾边
        fr = fr * (1 - ink[..., None] * 0.85) + INKC * ink[..., None] * 0.85
        fr = fr * (1 - A[..., None]) + zc
        fr = E.dust_motes(fr, t, 1373, n=70, amt=0.5, drift=(-30, 70), col=(1.0, 1.0, 1.0), size=(1, 3))   # 细雪
        fr = ash(fr, t, self.t0, 1374, n=18, amt=0.5, drift=(-40, 110), red=0.25)
        return fr


# ---- 尾奏日出：EB_dawn（水墨远山 + 白天 + 血红朝日）
HITS34 = [(7040 / 30, 1.0), (7047 / 30, 0.6), (7054 / 30, 0.6), (7061 / 30, 1.0), (7072 / 30, 1.0)]
STRONG34 = [7040 / 30, 7061 / 30, 7072 / 30]
SUN = (440.0, 452.0)            # EB_dawn 缩到 1920 后的日心（画面坐标），半径 ≈250


class _Dawn:
    def dawn_init(self):
        self.pl = plate4('EB_dawn4k')
        if 'dglow' not in _P:
            im = cv2.resize(self.pl, (W, H), interpolation=cv2.INTER_AREA)
            sunm = np.clip((im[..., 0] - np.maximum(im[..., 1], im[..., 2])) * 3, 0, 1).astype(np.float32)
            _P['dglow'] = cv2.resize(cv2.GaussianBlur(sunm, (0, 0), 30), (self.pl.shape[1], self.pl.shape[0]))[..., None] * REDC * 0.35
        self.glow = _P['dglow']
        self.walk = WALK()

    def sky(self, t, z, cx, cy, hits):
        k = beat_pulse(t, hits)
        fr = self.pl + self.glow * k if k > 0.01 else self.pl                                   # 鼓点：红日辉光呼吸
        return view4(fr, z, cx, cy), k


STEPS = [f / 30 for f in range(7033, 7130, 7)]                                                  # 步点：与强 / 弱拍 7040·7047·7054·7061… 同相，每 7 帧一步


def WALK():
    """走路三姿势（用户 20:05：两张分别生图的走姿位置不一致 → 来回跳）：EB_walk2a 为母图，
    nano-banana-pro 图生图衍生「过渡步」EB_walk_pass 与「换脚」EB_walk_b——同一画布、同一位置与比例
    （肩线中心 x 515±1px），所以三张共用同一个变换，切换时不会跳。"""
    return (lay('EB_walk2a'), lay('EB_walk_pass'), lay('EB_walk_b'))


def gait(t):
    """(姿势序号：0 = 左脚前着地 / 1 = 过渡 / 2 = 右脚前着地, 步内相位 0..1)。
    每步 7 帧（对齐 hitmap 的 kick 间隔）：着地姿势 4 帧 + 过渡姿势 3 帧，左右交替 → 是一个连续步循环，不再是两张图硬切。"""
    i = max(0, sum(1 for s_ in STEPS if t >= s_ - 1e-6) - 1)
    ph = c01((t - STEPS[i]) / (7 / 30))
    return (1 if ph >= 4 / 7 else (0 if i % 2 == 0 else 2)), ph


def walker(fr, t, poses, foot, h, amp, seed=0):
    """背影行走（独立人物层）：三姿势按步点循环，落脚与比例**统一取母图 poses[0] 的包围盒**（三张同画布，切姿势不跳）；
    步内起伏；发丝 / 红带 / 衣摆低频噪声二级运动（低振幅，只在轮廓带）。返回 (fr, A)。"""
    i, ph = gait(t)
    a_, s_ = poses[0].fit(h)
    bob = h * 0.010 * math.sin(math.pi * ph)
    z, A = draw(np.zeros_like(fr), poses[i], t, (a_[0] * poses[0].w, a_[1] * poses[0].h), (foot[0], foot[1] - bob), s_, wind_amp=0, breathe=0)
    z, A = flutter(z, A, t, amp, band=max(9.0, h * 0.05), seed=seed)
    return fr * (1 - A[..., None]) + z, A


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
    """强拍 / 落脚：白尘 + 血红火星（0.5s 散）。"""
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
        fr = fr * (1 - toned(puff, 1.0)[..., None] * 0.3) + puff[..., None] * 0.35
    return fr


class E34(CreditsD, _Dawn):   # S136 ELS：晨雾山水、血红朝日在左，刀客背影（独立层）朝朝日方向往画面深处走去：两张走姿按步点交替、
    #  位置往地平线移、身高缩小 13%；发尾 / 红带拆层飘；强拍 7040 阶梯推镜 + 脚下扬尘，弱拍红日呼吸；署名④ 音乐（墨书）
    ccol = 'ink'
    fade = False

    def __init__(self):
        self.blocks = [('音乐', ['西几王'], 1700, 230, 234.55, 0.5)]
        self.dawn_init()

    def render(self, t):
        u = self.u(t); tm = (self.t0 + self.t1) / 2
        z = step_zoom(t, [(7040 / 30, 0.025)]) * (1 + 0.004 * u)
        fr, k = self.sky(t, 1.03, 960, 540, HITS34)
        fr = mist(fr, t, 1366, 560, 760, 18, amt=0.30, t_ref=tm)
        fx, fy = 1240 - 60 * u, 912 - 34 * u
        h = 236 * (1 - 0.13 * u)
        fr = shadow(fr, fx, fy, L=80, lean=0.8, wmax=22, amt=0.5)
        fr, A = walker(fr, t, self.walk, (fx, fy), h, 1.5, seed=1)
        fr = mist(fr, t, 1367, 700, 880, 34, amt=0.22, col=(0.88, 0.88, 0.88), scale=6, t_ref=tm)
        fr = kick_dust(fr, t, STRONG34[:1], (fx, fy), 7340, n=40, spread=140)
        fr = E.dust_motes(fr, t, 1381, n=40, amt=0.25, drift=(-18, -10), col=(0.9, 0.9, 0.9))
        return K.cam(fr, z, center=(fx, 640))


class E34L(CreditsD, _Dawn):   # S136L LS（7061 强拍硬切）：同一日出推近；人物同样往深处走（身高 620→540），两姿势交替，发尾红带飘；7072 再进一级 + 扬尘
    ccol = 'ink'

    def __init__(self):
        self.blocks = [('音乐', ['西几王'], 1700, 230, 234.55, 0.5)]
        self.dawn_init()

    def render(self, t):
        u = self.u(t); tm = (self.t0 + self.t1) / 2
        z = step_zoom(t, [(7072 / 30, 0.03)]) * (1 + 0.006 * u)
        fr, k = self.sky(t, 1.55, 760, 640, HITS34)
        fr = mist(fr, t, 1396, 520, 760, 26, amt=0.32, t_ref=tm)
        fx, fy = 1250 - 70 * u, 1000 - 70 * u
        h = 620 * (1 - 0.13 * u)
        fr, A = walker(fr, t, self.walk, (fx, fy), h, 3.5, seed=3)
        fr = mist(fr, t, 1397, 800, 980, 50, amt=0.22, col=(0.88, 0.88, 0.88), scale=6, t_ref=tm)
        fr = kick_dust(fr, t, STRONG34[1:], (fx, fy - 20), 7350, n=50, spread=220)
        fr = E.dust_motes(fr, t, 1394, n=50, amt=0.3, drift=(-22, -12), col=(0.9, 0.9, 0.9))
        return K.cam(fr, z, center=(fx, 600))


class E34b(CreditsD, _Dawn):   # S136b MS 背影上半身（返工）：清晰白天墨云 + 血红日轮在头侧（EB_sky，无景深虚化）；马尾 / 红带拆层大幅飘动，步伐起伏
    def __init__(self):
        self.blocks = []
        self.walk = WALK()                                                                       # 只用走姿层（三姿势同画布）
        self.bgb = view4(plate4('EB_sky'), 1.4, 700, 480)

    def render(self, t):
        u = self.u(t)
        fr = view(self.bgb, 1.06 + 0.02 * u, 960 + 24 * (u - 0.5), 540)
        i, ph = gait(t)
        bob = 7 * math.sin(math.pi * ph)
        zc, A = draw(np.zeros_like(fr), self.walk[i], t, (480, 380), (990 - 20 * u, 820 - bob), 1.72, breathe=0.004, wind_amp=0)
        zc, A = flutter(zc, A, t, 5.0, band=46.0, seed=4)
        fr = fr * (1 - A[..., None]) + zc
        return E.dust_motes(fr, t, 1385, n=50, amt=0.35, drift=(-20, -15), col=(0.9, 0.9, 0.9))


class E34c(CreditsD):   # S136c 插入：握鞘的手 + 血红穗（EB_grip）；刀鞘随步伐以手为轴摆（±2.5°），红带 / 穗拆层飘；清晰白天墨云
    def __init__(self):
        self.blocks = []
        self.L = lay('EB_grip', feather=40)
        self.bg = view4(plate4('EB_sky'), 1.5, 760, 440)

    def render(self, t):
        u = self.u(t)
        fr = view(self.bg, 1.06 + 0.02 * u, 960 + 30 * (u - 0.5), 540)
        i, ph = gait(t)
        sw = math.sin(math.pi * ph) * (1 if i == 2 else -1)
        zc, A = draw(np.zeros_like(fr), self.L, t, (1150, 560), (1070 - 25 * u, 560 + 8 * abs(sw)), W / self.L.w * 1.16, rot=2.5 * sw, breathe=0, wind_amp=0)
        zc, A = flutter(zc, A, t, 4.0, band=44.0, seed=6, red=1.4)
        fr = fr * (1 - A[..., None]) + zc
        return E.dust_motes(fr, t, 1387, n=40, amt=0.3, drift=(-25, -10), col=(0.9, 0.9, 0.9))


class E34d(CreditsD, _Dawn):   # S136d 靴步：低机位贴地；EB_steps2a 母图 + 图生图衍生的过渡步 / 换脚（同画布同位置），7118 过渡、7120 落脚，同一变换不跳；落脚扬尘
    T_STEP = 7120 / 30

    def __init__(self):
        self.blocks = []
        self.dawn_init()
        self.bgd = view4(self.pl, 1.6, 900, 690)
        self.a = lay('EB_steps2a', feather=30); self.m = lay('EB_steps_pass', feather=30); self.b = lay('EB_steps_b', feather=30)

    def render(self, t):
        u = self.u(t)
        fr = view(self.bgd, 1.06 + 0.02 * u, 960 + 20 * (u - 0.5), 540)
        fr = shadow(fr, 960, 905, L=120, lean=0.6, wmax=60, amt=0.45)
        L = self.a if t < self.T_STEP - 2 / 30 - 1e-6 else (self.m if t < self.T_STEP - 1e-6 else self.b)
        zc, A = draw(np.zeros_like(fr), L, t, (430, 1040), (960 - 30 * u, 925), 0.86, breathe=0, wind_amp=0)   # 三张同一变换
        zc, A = flutter(zc, A, t, 3.0, band=40.0, seed=7, red=1.4)
        fr = fr * (1 - A[..., None]) + zc
        fr = kick_dust(fr, t, [self.t0 + 1 / 30, self.T_STEP], (980, 915), 1390, n=50, spread=150)
        return fr


HITS35 = [7133 / 30, 7143 / 30, 7160 / 30, 7167 / 30]


class E35(Shot):   # S137 ECU 收刀「咔」（EB_sheath）：刀滑入鞘口、7153 最强拍硬停 + 鞘口墨线星芒 / 硬边白闪 + 火星；7157 起「鬼屠」血红印；
    #  背景清晰白天墨云 + 血红日轮（EB_sky，无景深虚化）
    def __init__(self):
        self.L = lay('EB_sheath', feather=30)
        self.bg = view4(plate4('EB_sky'), 1.6, 700, 520)
        self.tc = 7153 / 30

    def scene(self, t):
        fr = self.bg.copy()
        slide = 0 if t >= self.tc else 80 * (1 - eio((t - self.t0) / (self.tc - self.t0)))
        s = 1.42
        dst = (960 - slide, 640)
        z, A = draw(np.zeros_like(fr), self.L, t, (1050, 790), dst, s, breathe=0, wind_amp=0)
        z, A = flutter(z, A, t, 3.0, band=40.0, seed=8, red=1.4)                              # 发梢 / 红穗
        fr = fr * (1 - A[..., None]) + z * 1.08
        mouth = to_scr(self.L, (1050, 790), dst, s, (1270, 790))
        if t < self.tc:                                                                         # 刀身寒光（硬边白条）推向鞘口
            g0 = to_scr(self.L, (1050, 790), dst, s, (780, 790))
            k = eio(c01((t - self.t0) / (self.tc - self.t0)))
            px = g0[0] + (mouth[0] - g0[0]) * k
            yy, xx = E.grid()
            bl = (np.abs(xx - px) < 34) * (np.abs(yy - mouth[1]) < 40) * A
            fr = fr + bl[..., None] * 0.45
        return fr, mouth

    def render(self, t):
        fr, mouth = self.scene(t)
        if t >= self.tc:
            q = t - self.tc
            fr = hard_star(fr, mouth, 150 * (1 - 0.4 * c01(q / 0.2)), amt=math.exp(-q / 0.14), rot=8)
            if q < 2 / 30:                                                                      # 硬边白闪：鞘口一道横向白楔（不是镜头光斑）
                Lw = np.zeros((H, W), np.float32)
                cv2.fillConvexPoly(Lw, np.int32([[mouth[0] - 520, mouth[1]], [mouth[0], mouth[1] - 9], [mouth[0] + 520, mouth[1]], [mouth[0], mouth[1] + 9]]), 1.0, cv2.LINE_AA)
                fr = fr * (1 - Lw[..., None]) + Lw[..., None]
            fr = spark2(fr, t, 1391, mouth, self.tc, n=50, life=0.6, speed=(200, 700), dirc=(0, -1), spread=1.6, grav=900)
            p = c01((q - 0.13) / 0.35)
            if p > 0: fr = T.stamp_seal(fr, '鬼屠', 960, 470, 260, p, style='yin', rot=-4, seed=21, color=tuple(REDC))
        for th in HITS35:
            if t >= th: fr = fr * (1 + 0.10 * math.exp(-(t - th) / 0.08))
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
    if os.environ.get('EB_EDGECHECK') == '1':                                               # 图层边界自检：每次 import 后汇总一次
        import atexit, sys as _s
        def _dump():
            print('[r8d_e_b] EDGE (sprite canvas in frame):', EDGE_LOG[:20], file=_s.stderr)
            print('[r8d_e_b] EDGE (view clamped):', EV_LOG[:20], file=_s.stderr)
        atexit.register(_dump)
    # 风格 D 无金：E27b 入点冲击闪由白金改纯白（E27a/E28 的血红闪保留）
    M.CUTS['E27b'] = ('cut', 0, 0, {})                                                     # 镜内自带两帧反白冲击（现版 impact 的闪会把剪影冲灰）
    M.SHAKE['E27b'] = [(6658 / 30, 14)]
    # 风格 D 无金：入转场的暖金烟 / 暖刃口改中性白灰（墨烟），金色不再依赖全局兜底去色
    M.CUTS['E29'] = ('ink_bleed', 0.18, 0.18, dict(center=(1000, 500), seed=9, white=False))       # 墨晕吞屏（暗底设计）→ 墨在宣纸上洇开（同时长、同中心）
    M.CUTS['E32'] = ('blade_sweep', 0.12, 0.16, dict(direction=1, warm=(1.0, 1.0, 1.0)))
    M.CUTS['E33'] = ('warm_veil', 0.14, 0.20, dict(axis='x', direction=-1, seed=7301, cap=0.66, warm=(0.96, 0.96, 0.96), dark=(0.06, 0.06, 0.06)))
    M.CUTS['E34'] = ('warm_veil', 0.20, 0.30, dict(axis='y', seed=7341, cap=0.62, warm=(0.96, 0.96, 0.96), dark=(0.10, 0.10, 0.10)))
