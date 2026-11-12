"""units/r8d_a1.py — 第八轮风格 D（日漫墨线 + 网点 + 严格黑白血红）· A1 单元：片头 + 主歌一前半（A01–A08、V01–V07，帧 0–702）。

由 units/sec_a_intro_verse1.py 末尾的 STYLE_D 钩子调用 apply(mod)：把本单元负责的 15 个镜头类换成 *D 子类（继承原类，
t0/t1 与 CUTS / MOVES3 / INNER / FG 的键都沿用原类名），片名层换成画进生图的风格 D 片名（TitleD，接口同 Title.draw）。
STYLE_D=0 时本模块不加载，现版逐像素不变。V08 起由并行单元 r8d_a2 负责，本模块不碰。

素材：assets/gen/R8_D/A1/（nananobanana RH_image2，提示词 jobs/r8_D_A1.json，记录 crew/round8/genlog_A1.md）。
规则（crew/round8/SPREAD_r8.md）：
  - 切点 / 镜长 / 入出转场 / 主运镜（VCam3 MOVES3）/ 镜内推（INNER）/ 卡点脉冲 / 硬切冲击全部沿用原表，只换素材与镜内画法；
  - 精灵一律 grade=NEU、rim=NORIM、wrap=0、shade=None；各层视差偏移以镜头中点为零（m = u − 0.5），粒子同理；
  - 画面字只留片名（合同要求，画进生图）；V03「五百重甲」巨字、屏幕层 LY2 横排歌词（本段三句）去掉，底部字幕不动；
  - 雨 = 细墨线短划（亮处黑线、暗处白线），火星 = 白 + 血红，刀光 = 干笔飞白 + 血红边 + 溅点。"""
import os, math
from functools import lru_cache
import numpy as np, cv2
import sprite as SP
import c1kit as K
import fx2
from a_kit import clamp01, eio, eout, ein
from c1kit import pulse

W, H = 1920, 1080
ROOT = os.environ.get('MV_ROOT', '/workspace/work/mv')
G = ROOT + '/assets/gen/R8_D/A1/'
NEU = dict(expo=1.0, sat=1.0, tint=(1.0, 1.0, 1.0), lift=0.0, gamma=1.0)
NORIM = dict(col=(1.0, 1.0, 1.0), amt=0.0, dir=(0.0, -1.0))
KW = dict(grade=NEU, rim=NORIM, wrap=0, shade=None)
WHITE = np.array([1.0, 1.0, 1.0], np.float32)
RED = np.array([0.78, 0.04, 0.03], np.float32)
MINE = ('A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07a', 'A08', 'V01', 'V02', 'V03', 'V04', 'V05', 'V06', 'V07')
M = None                                                     # sec_a_intro_verse1 模块（apply 时注入：V / CT / fog / TITLE_HIT …）


# ------------------------------------------------------------------ 素材与合成小工具
@lru_cache(None)
def plate(name, flip=False, blur=0.0):
    im = cv2.cvtColor(cv2.imread(G + name + '.png'), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    if flip: im = np.ascontiguousarray(im[:, ::-1])
    if blur: im = cv2.GaussianBlur(im, (0, 0), blur)
    return im


@lru_cache(None)
def rgba(name):
    im = cv2.imread(G + name + '_cut.png', cv2.IMREAD_UNCHANGED)
    im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255
    return np.ascontiguousarray(im[..., :3] * im[..., 3:]), np.ascontiguousarray(im[..., 3])     # 预乘 F·A, A


def lay(name): return SP.layer(G + name + '_cut.png')


def lay_soft(name, px=36):
    """图生图的走路 / 连斩帧：人物在图里本来就顶到画布边（头发、靴底、刀尖），放大到画面里会露出画布直边。
    载入时把四边 px 像素内的 alpha 做羽化（墨一样淡出），保证任何位移 / 推镜都不会出现直线裁切（SPREAD §11.7）。"""
    key = ('soft', name, px)
    if key in _SOFT: return _SOFT[key]
    P, A = rgba(name)
    h, w = A.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ramp = np.clip(np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) / px, 0, 1)
    A = A * ramp
    path = '/tmp/mv_r8d_a1/soft_%s_%d.png' % (name, px)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        from PIL import Image
        Image.fromarray((np.dstack([np.clip(P / np.clip(A[..., None], 1e-3, None), 0, 1), A]) * 255 + 0.5).astype(np.uint8), 'RGBA').save(path)
    L = SP.layer(path)
    _SOFT[key] = L
    return L


_SOFT = {}


def at(img, k, dx=0.0, dy=0.0, cx=None, cy=None):
    """背景板：源点 (cx,cy)（默认图心）按 k 缩放落到屏幕 (960+dx, 540+dy)。返回新数组（可原地改）。"""
    h, w = img.shape[:2]
    cx = w / 2 if cx is None else cx; cy = h / 2 if cy is None else cy
    Mx = np.float32([[k, 0, 960 + dx - k * cx], [0, k, 540 + dy - k * cy]])
    return cv2.warpAffine(img, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def put(fr, t, L, src, dst, k, **kw):
    """精灵：源像素点 src 落到屏幕 dst，k = 源像素 → 屏幕像素。"""
    o = dict(KW); o.update(kw)
    return L.draw(fr, t, (src[0] / L.w, src[1] / L.h), dst, k, **o)


@lru_cache(None)
def spears(keep):
    """V06_fg 生图里的 6 根枪：按连通域选第 keep 根（0–5，左→右），整根带红缨，不用直线遮罩截断。"""
    P, A = rgba('V06_fg')
    n, lab, st, c = cv2.connectedComponentsWithStats((A > 0.2).astype(np.uint8), 8)
    big = [i for i in range(1, n) if st[i, 4] > 4000]
    big.sort(key=lambda i: c[i][0])
    mk = np.isin(lab, [big[k] for k in keep if k < len(big)]).astype(np.float32)
    mk = cv2.dilate(mk, np.ones((7, 7), np.uint8))
    mk = cv2.GaussianBlur(mk, (0, 0), 1.0) * (A > 0.01)
    h, w = A.shape; yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    mk = mk * np.clip(np.minimum(np.minimum(xx, w - 1 - xx), yy) / 40.0, 0, 1)   # §11.7：红缨碰到画布左/右/上缘的部分 40px 羽化掉，不留直线截断（下缘始终在画外）
    return P * mk[..., None], A * mk


WALK_DY = (0.0, -1.0, 0.0, -1.0)                              # 四拍循环的重心：接触拍低、过身拍高（× 振幅）


def walk_pose(poses, t, t0, beat):
    """连续走路：poses = 四张同机位图生图（接触 L / 过身 / 接触 R / 过身）；返回 (当前姿势, 重心偏移系数)。"""
    k = int((t - t0) / beat) % 4
    return poses[k], WALK_DY[k]


def foot_of(L, rows=40):
    """精灵脚底中点（源像素）：alpha 最下 rows 行的横向中点。"""
    A = L.A; ys = np.nonzero(A.max(1) > 0.5)[0]; yb = int(ys[-1])
    xs = np.nonzero((A[max(0, yb - rows):yb + 1] > 0.5).any(0))[0]
    return (float(xs.min() + xs.max()) / 2, float(yb))


def blit(fr, P, A, Mx, alpha=1.0, defocus=0.0):
    """预乘 RGBA 仿射合成（Mx 2×3，源 → 屏幕）。"""
    Pw = cv2.warpAffine(P, Mx, (W, H), flags=cv2.INTER_LINEAR)
    Aw = cv2.warpAffine(A, Mx, (W, H), flags=cv2.INTER_LINEAR)
    if defocus > 0.3: Pw = cv2.GaussianBlur(Pw, (0, 0), defocus); Aw = cv2.GaussianBlur(Aw, (0, 0), defocus)
    return fr * (1 - Aw[..., None] * alpha) + Pw * alpha, Aw


def affine(src, dst, k, rot=0.0):
    Mx = cv2.getRotationMatrix2D((float(src[0]), float(src[1])), rot, k)
    Mx[0, 2] += dst[0] - src[0]; Mx[1, 2] += dst[1] - src[1]
    return Mx


def ink_rain(fr, t, rs, amt, angle=8.0, layers=None, cam=(0, 0)):
    """风格 D 雨：同一套雨丝，亮处画成黑墨短划、暗处画成白线（长短粗细随 RainSheet 层变化）。"""
    if amt <= 0: return fr
    z = rs.draw(np.zeros((H, W, 3), np.float32), t, amt, angle=angle, color=(1.0, 1.0, 1.0), layers=layers, cam=cam)
    l = np.clip(z[..., :1] / 1.05, 0, 1)
    b = np.clip(fr.mean(-1, keepdims=True), 0, 1)
    return fr * (1 - 0.75 * l * b) + l * (1 - b) * 0.85


@lru_cache(None)
def _fg_rain_arr(scale, blur):
    P, A = rgba('RAIN_fg')
    n, lab, st, _ = cv2.connectedComponentsWithStats((A > 0.3).astype(np.uint8), 8)     # 去掉大水珠（虚焦后像灰蝌蚪），只留细雨丝
    dist = cv2.distanceTransform((A > 0.3).astype(np.uint8), cv2.DIST_L2, 3)
    fat = np.zeros(n, np.float32); np.maximum.at(fat, lab.ravel(), dist.ravel())
    edge = np.zeros(n, bool); edge[np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))] = True; edge[0] = False
    keep = cv2.dilate(((fat[lab] <= 9.0) & ~edge[lab]).astype(np.float32) * (lab > 0), np.ones((5, 5), np.uint8))   # 碰图边的雨丝去掉：平铺接缝处不出直线截断
    P, A = P * keep[..., None], A * keep
    w, h = int(W * scale), int(H * scale)
    P = cv2.resize(P, (w, h), interpolation=cv2.INTER_AREA); A = cv2.resize(A, (w, h), interpolation=cv2.INTER_AREA)
    if blur: P = cv2.GaussianBlur(P, (0, 0), blur); A = cv2.GaussianBlur(A, (0, 0), blur)
    return P, A


def fg_rain(fr, t, tm, amt=0.55, vel=(260.0, 760.0), scale=1.3, blur=0.0):
    """贴镜头的生图雨丝 / 大水珠层：沿雨向持续下落，位移以镜头中点 tm 为零（与主体层在中点对齐）。"""
    P, A = _fg_rain_arr(scale, blur)
    h, w = A.shape
    ox = int(round(vel[0] * (t - tm))) % w; oy = int(round(vel[1] * (t - tm))) % h
    Mx = np.float32([[1, 0, ox], [0, 1, oy]])
    P = cv2.warpAffine(P, Mx, (W, H), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_WRAP)
    A = cv2.warpAffine(A, Mx, (W, H), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_WRAP)
    return fr * (1 - A[..., None] * amt) + P * amt


_BR = np.random.default_rng(808).random(1024).astype(np.float32)
def brush(fr, p0, p1, prog, width, col=WHITE, tail=0.0, fade=1.0, dry=0.55, red_edge=0.8, seed=0, splat=18):
    """干笔飞白刀痕：p0→p1 一笔扫出（prog 0→1 为笔头位置），两端收尖，笔腹按「笔毛」断成飞白丝、越往笔尾越干；
    外沿一圈血红，笔头甩出血红溅点。"""
    if prog <= 0 or fade <= 0.01: return fr
    p0 = np.asarray(p0, np.float32); p1 = np.asarray(p1, np.float32)
    d = p1 - p0; L = float(np.hypot(*d)); u = d / L; n = np.array([-u[1], u[0]], np.float32)
    k = 2; h, w = H // k, W // k
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    X = xx * k - p0[0]; Y = yy * k - p0[1]
    s = (X * u[0] + Y * u[1]) / L; dd = X * n[0] + Y * n[1]
    hd = min(1.0, prog)
    wv = width * np.clip(np.sin(np.pi * np.clip(s, 0, 1)), 0, 1) ** 0.5 + 1.0
    inside = np.clip((wv / 2 - np.abs(dd)) / 1.2, 0, 1) * np.clip((hd - s) * L / 8, 0, 1) * np.clip((s - tail) * L / 40, 0, 1)
    if inside.max() <= 0: return fr
    idx = (np.clip(dd / wv * 0.5 + 0.5, 0, 1) * 300 + seed * 37).astype(np.int32) % 1024
    br = _BR[idx]
    thr = dry * np.clip((hd - s) / max(hd, 1e-3), 0, 1) ** 0.8               # 笔尾更干（飞白多），笔头饱满
    m = inside * np.clip((br - thr) * 6 + 0.5, 0, 1)
    edge = inside * np.clip((np.abs(dd) / (wv / 2) - 0.55) / 0.3, 0, 1)
    m = cv2.resize(m, (W, H)); edge = cv2.resize(edge, (W, H))
    c = np.asarray(col, np.float32)
    out = fr * (1 - m[..., None] * fade) + (c * (1 - red_edge * edge[..., None]) + RED * red_edge * edge[..., None]) * m[..., None] * fade
    out = out + K.blur_ds(m, 8)[..., None] * c * 0.35 * fade
    if splat:
        r = np.random.default_rng(seed + 991)
        hp = p0 + d * hd
        Ld = np.zeros((h, w), np.float32)
        for _ in range(splat):
            a_ = r.normal(0, 0.9); dist = r.uniform(20, 220) * prog
            q = hp + (u * math.cos(a_) + n * math.sin(a_)) * dist
            cv2.circle(Ld, (int(q[0] / k), int(q[1] / k)), max(1, int(r.uniform(1, 5))), 1.0, -1, cv2.LINE_AA)
        Ld = cv2.resize(Ld, (W, H))[..., None] * fade
        out = out * (1 - Ld) + RED * Ld
    return out


def sparks2(fr, t, seed, origin, **kw):
    """火星 = 白 + 血红两组。"""
    kw2 = dict(kw); n = kw.pop('n', 40)
    fr = K.sparks(fr, t, seed, origin, n=n, color=(1.0, 1.0, 1.0), **kw)
    kw2['n'] = max(4, n // 2); kw2.pop('color', None)
    return K.sparks(fr, t, seed + 1, origin, color=tuple(RED * 1.15), **kw2)


def glow(fr, c, r, amt, col=WHITE, aspect=1.0):
    return M.A.glow(fr, c, r, amt, tuple(np.asarray(col, float)), aspect=aspect)


def lightn_env(t, hits):
    e = 0.0
    for t0_, a_ in hits:
        if t >= t0_: e = max(e, a_ * math.exp(-(t - t0_) / 0.09))
    return e


# ------------------------------------------------------------------ 片名层（合同要求，画进生图：鬼屠·第二季 / 主题曲《谁定正邪》/ 印「鬼屠」）
class TitleD:
    """接口同 sec_a_intro_verse1.Title.draw(fr, t, out, sheen, glow)：屏幕层，机位沿用 Title.cam（A06 缓推 → A07a 缩到 0.80 挂到城上）。
    7.85 刀光扫过时主标题随刀光由左到右「斩出」（揭开 + 1.25→1 落定 + 去虚），8.31 印「鬼屠」盖下（1.6→1 + 震），8.35 副标题墨显；
    11.52 扫光 = 墨面上一道白高光；13.25 起墨噪溶解。墨字背后一层柔白「纸雾」托底，在暗底（城楼）上也读得清。"""
    CX, CY, KS = 1027.0, 500.0, 0.70                         # 源图 (1027,500) = 主标题中心 → 屏幕 (960, TITLE_Y)
    def __init__(self):
        P, A = rgba('A06_title')
        h, w = A.shape
        yy = np.arange(h)[:, None]; xx = np.arange(w)[None, :]
        seal = (xx >= 1840) & (yy >= 520) & (yy <= 770)
        n, lab, st, _ = cv2.connectedComponentsWithStats((A > 0.12).astype(np.uint8), 8)
        low = np.zeros(n, bool); low[1:] = st[1:, cv2.CC_STAT_TOP] >= 760       # 整个连通域都在 760 以下 = 副标题（主标题下拖的长笔画不算）
        sub = (low[lab] | ((xx >= 1095) & (xx < 1175) & (yy >= 765) & (yy < 850))) & ~seal   # 「定」被「第」的下拖笔画连进主标题连通域，按字框划回副标题
        main = ~seal & ~sub
        self.P = P; self.A = A
        self.masks = {nm: m.astype(np.float32) for nm, m in (('main', main), ('sub', sub), ('seal', seal))}
        self.xs = np.arange(w, dtype=np.float32)[None, :]
        self.w = w
        self.seal_c = (1912.0, 640.0)

    def _M(self, t, pop=1.0, about=None):
        sc, dx, dy, rot = M.Title.cam(t)
        Mc = cv2.getRotationMatrix2D((960.0, 520.0), rot, sc); Mc[0, 2] += dx; Mc[1, 2] += dy
        k = self.KS
        Ms = np.float64([[k, 0, 960 - k * self.CX], [0, k, M.TITLE_Y - k * self.CY], [0, 0, 1]])
        if pop != 1.0:
            ax, ay = about if about else (self.CX, self.CY)
            Ms = Ms @ np.float64([[pop, 0, ax * (1 - pop)], [0, pop, ay * (1 - pop)], [0, 0, 1]])
        return (np.vstack([Mc, [0, 0, 1]]) @ Ms)[:2].astype(np.float32)

    def _part(self, nm, Mx, a, blur=0.0, extra=None):
        mk = self.masks[nm] if extra is None else self.masks[nm] * extra
        Aw = cv2.warpAffine(self.A * mk, Mx, (W, H), flags=cv2.INTER_LINEAR) * a
        Pw = cv2.warpAffine(self.P * mk[..., None], Mx, (W, H), flags=cv2.INTER_LINEAR) * a      # self.P 已预乘，这里只乘区域遮罩
        if blur > 0.3: Aw = cv2.GaussianBlur(Aw, (0, 0), blur); Pw = cv2.GaussianBlur(Pw, (0, 0), blur)
        return Pw, Aw

    def draw(self, fr, t, out=0.0, sheen=None, glow=0.0):
        TH = M.TITLE_HIT
        if t < TH - 0.06: return fr
        k = t - TH
        sw = clamp01((k + 0.06) / 0.14)                                   # 与刀光同速：由左到右斩出
        xr = -0.05 + 1.15 * sw
        reveal = np.clip((xr * self.w - self.xs) / 60.0, 0, 1)
        e = eout(clamp01(k / 0.22))
        P1, A1 = self._part('main', self._M(t, 1 + 0.25 * (1 - e)), 1.0, blur=7 * (1 - e), extra=reveal)
        se = eout(clamp01((t - M.V(8.35)) / 0.45))
        P2, A2 = self._part('sub', self._M(t), se, blur=4 * (1 - se)) if se > 0 else (0.0, 0.0)
        ks = t - M.V(8.31)
        if ks > 0:
            q = clamp01(ks / 0.10)
            P3, A3 = self._part('seal', self._M(t, 1.6 - 0.6 * eout(q, 2), self.seal_c), clamp01(ks / 0.05))
        else:
            P3, A3 = 0.0, 0.0
        Pt = P1 + P2 + P3; At = np.clip(A1 + A2 + A3, 0, 1)
        if out > 0:
            nz = cv2.resize(M.A.ink_noise(77, 256), (W, H))
            dm = np.clip((nz - out * 1.15) * 5 + 0.5, 0, 1) * (1 - out) ** 1.2
            Pt = Pt * dm[..., None]; At = At * dm
        if At.max() <= 1e-3: return fr
        hal = K.blur_ds(At, 26) * (0.55 + 0.6 * glow)                     # 纸雾托底（柔白），节拍时略涨
        fr = fr + (np.clip(1.0 - fr, 0, None)) * np.clip(hal, 0, 0.85)[..., None]
        if sheen is not None and 0 <= sheen <= 1:
            band = np.exp(-((np.arange(W, dtype=np.float32)[None] - (300 + 1350 * sheen)) / 45) ** 2)
            Pt = Pt + (At * band * 0.55)[..., None] * WHITE
        return fr * (1 - At[..., None]) + Pt


# ------------------------------------------------------------------ 镜头
def _build(mod):
    V, CT = mod.V, mod.CT
    fog = mod.fog
    out = {}

    # A01 0–2.17 ELS 墨滴开天：一滴白墨落进黑场 → 墨晕开出云海（风格 D 生图：云海 + 云后白光束 + 地平线血红），
    #   三层：云海板（缓摇臂降）/ 白雾流（70px/s）/ 近景山脊精灵（摇臂降时升起，视差 ×3）；体积白光束随光源横移扫过
    class A01D(mod.A01):
        def __init__(self):
            self.bg = plate('A01_bg'); self.ridge = lay('A01_ridge')
        def scene(self, t):
            u = self.u(t); m = u - 0.5; c = eio(u)
            fr = at(self.bg, 1.10, dx=-40 * m, dy=-20 * (c - 0.5))
            lx = 1180 + 120 * t
            fr = fx2.god_rays(fr, (lx, 160), strength=0.16, length=1.0, color=(1.0, 1.0, 1.0), t=t * 2.5, src_r=160)
            fr = fog(fr, t, 0, 420, 760, 0.30, (0.88, 0.88, 0.88), speed=(70, 0))
            fr = fog(fr, t, 2, 560, 900, 0.22, (0.70, 0.70, 0.70), speed=(130, 0))
            fr, _ = put(fr, t, self.ridge, (1024, 1152), (960 - 110 * m, 1230 - 110 * (c - 0.5) - 60), 1.0, wind_amp=0, breathe=0)
            fr = fog(fr, t, 1, 900, 1080, 0.3, (0.6, 0.6, 0.6), speed=(160, 0))
            return fr
        def render(self, t):
            sc = self.scene(t)
            T_DROP = V(0.37)
            if t < T_DROP:
                fr = np.zeros_like(sc) + 0.004
                q = clamp01(t / T_DROP); y = 120 + (560 - 120) * q ** 2
                fr = glow(fr, (960, y), 10, 1.2); fr = glow(fr, (960, y - 40), 6, 0.6, aspect=0.15)
                return fr, 0
            p = eout((t - T_DROP) / 1.55, 2)
            fr = mod.TR.ink_bleed(np.zeros_like(sc) + 0.004, sc, p, seed=4, center=(960, 560), edge=0.85)
            kk = math.exp(-(t - T_DROP) / 0.12)
            fr = glow(fr, (960, 560), 60 + 300 * (1 - kk), 0.8 * kk)
            return fr, (2 if kk > 0.5 else 0)
    out['A01'] = A01D

    # A02 2.17–4.03 LS 鬼屠背影立于山岩（左 1/3），巨大血月只露右侧出框（风格 D 生图）；横移 truck：
    #   月夜板 0.3 / 白雾 / 山脊 0.7 / 人物 1.0（发丝、马尾、红带、衣摆风吹二级运动 + 呼吸）/ 前景雾 / 灰烬
    class A02D(mod.A02):
        def __init__(self):
            self.bg = plate('A02_bg'); self.ridge = lay('A01_ridge'); self.hero = lay('A02_hero')
        def render(self, t):
            u = self.u(t); m = u - 0.5
            fr = at(self.bg, 1.06, dx=-40 * m)
            fr = fog(fr, t, 2, 560, 860, 0.28, (0.82, 0.82, 0.82), speed=(-60, 0))
            fr, _ = put(fr, t, self.ridge, (1024, 1152), (960 - 100 * m, 1330), 1.0, wind_amp=0, breathe=0)
            fr, _ = put(fr, t, self.hero, (928, 1151), (640 - 150 * m, 968), 0.56, wind_amp=11, breathe=0.004)
            fr = fog(fr, t, 1, 900, 1080, 0.35, (0.55, 0.55, 0.55), speed=(120, 0))
            fr = mod.ASH.draw(fr, t, 0.6, wind=(220, 10))
            return fr, 0
    out['A02'] = A02D

    # A03 4.03–5.93 ECU 拇指推刀出鞘（风格 D 生图：直刀 + 中式护手 + 黑柄 + 红穗刀鞘），背后速度线特写板（清晰，不虚焦）；4.53 拍上刀柄真实向左抽出 40px
    #   （刃身露出段按位移拉长，不是整张平移）+ 手微颤 + 鞘口迸白尘 + 白扫光沿刃滑过；5.46 再抽 8px
    class A03D(mod.A03):
        S0, S1 = 700.0, 1340.0                                           # 源图：露刃段（护手 → 鞘口）
        def __init__(self):
            self.bg = plate('CU_bg1')
            self.P, self.A = rgba('A03_sword')
            h, w = self.A.shape
            self.gx = np.tile(np.arange(w, dtype=np.float32), (h, 1)); self.gy = np.repeat(np.arange(h, dtype=np.float32)[:, None], w, 1)
            lum = (self.P / np.clip(self.A[..., None], 1e-3, None)).mean(-1)
            self.steel = ((lum > 0.55) & (self.A > 0.9) & (self.gx > self.S0) & (self.gx < self.S1) & (self.gy > 480) & (self.gy < 596)).astype(np.float32)   # 只取露刃段，扫光不打到手上
        def render(self, t):
            u = self.u(t); m = u - 0.5
            fr = at(self.bg, 1.15, dx=-60 * m, dy=-20)                   # 速度线板：清晰，不做景深虚化
            k = 1.06
            push = (eout((t - V(4.53)) / 0.35) * 40 + 8 * eout((t - V(5.46)) / 0.25)) / k
            jit = 1.5 * math.sin(t * 47) * clamp01((t - V(4.53)) / 0.1) * math.exp(-max(0, t - V(4.53)) / 0.4)
            X = self.gx; s0, s1 = self.S0, self.S1
            sx = np.where(X < s0 - push, X + push, np.where(X < s1, s0 + (X - (s0 - push)) * ((s1 - s0) / (s1 - s0 + push)), X)).astype(np.float32)
            P = cv2.remap(self.P, sx, self.gy, cv2.INTER_LINEAR); A = cv2.remap(self.A, sx, self.gy, cv2.INTER_LINEAR)
            st = cv2.remap(self.steel, sx, self.gy, cv2.INTER_LINEAR)
            Mx = affine((1024, 540), (930 - 60 * m, 560 + jit), k)
            fr, Aw = blit(fr, P, A, Mx)
            q = clamp01((t - V(4.53)) / 0.95)
            if 0 < q < 1:
                stw = cv2.warpAffine(st, Mx, (W, H))
                x = 200 + 1500 * eio(q)
                band = np.exp(-((np.arange(W, dtype=np.float32)[None] - x) / 70) ** 2)
                fr = fr + (stw * band)[..., None] * 1.2                    # 白扫光只在露刃段（硬边，不加柔光晕）
            mouth = tuple(Mx @ np.array([s1 + 20, 540.0, 1.0]))
            fr = sparks2(fr, t, 33, mouth, n=60, life=0.9, speed=(40, 260), dirc=(0, -1), spread=2.4, grav=-60, area=(80, 40), amt=0.6,
                         t0=V(4.53), burst=True)
            fr = mod.ASH.draw(fr, t, 0.3, wind=(-60, -30))
            return fr, (2 if 0 <= t - V(4.53) < 0.07 else 0)
    out['A03'] = A03D

    # A04 5.93–7.33 CU 侧脸朝左（风格 D 生图），6.48 起微转头；三层视差：风云板反向漂 / 白雾 / 前景灰烬；
    #   发丝与马尾风吹二级运动（精灵发区网格形变）+ 呼吸
    class A04D(mod.A04):
        def __init__(self):
            self.bg = plate('A04_bg'); self.face = lay('A04_face')
        def render(self, t):
            u = self.u(t); m = u - 0.5
            fr = at(self.bg, 1.12, dx=90 * m)                              # 风云板反向漂（视差），清晰墨线，不做景深虚化
            fr = fog(fr, t, 2, 300, 1000, 0.22, (0.78, 0.78, 0.78), speed=(-90, 0))
            turn = eio((t - V(6.48)) / 0.5)
            fr, _ = put(fr, t, self.face, (640, 600), (820 + 50 * m, 560), 0.95, rot=-2.5 + 3.5 * turn, wind_amp=12, breathe=0.004)
            fr = mod.ASH.draw(fr, t, 0.45, wind=(-200, 0))
            return fr, 0
    out['A04'] = A04D

    # A05 7.33–7.83 ECU 双眼（风格 D 生图，瞳仁一点血红）→ 7.60 眼中寒光（白星芒 + 血红瞳光）→ 末 4 帧压暗蓄力；7.73 刀光预光条
    class A05D(mod.A05):
        PUP = ((789.0, 660.0), (1624.0, 646.0))
        def __init__(self):
            self.bg = plate('A05_eyes')
        def render(self, t):
            k = 1920 / 2048 * 1.02
            fr = at(self.bg, k)
            g = math.exp(-max(0, t - V(7.60)) / 0.10) * (t >= V(7.60))
            for (sx, sy) in self.PUP:
                p = (960 + k * (sx - 1024), 540 + k * (sy - 576))
                fr = mod.pupil_glint(fr, (p[0], p[1] - 6), 0.9 * g, 1.2, col=(1.0, 1.0, 1.0))
                fr = glow(fr, p, 26, 0.6 * g, RED)
            kk = clamp01((t - (self.t1 - 4 / 30)) / (4 / 30))
            fr = fr * (1 - 0.75 * kk)
            fr = mod.streak(fr, 520, -100, 2100, (t - V(7.73)) / 0.10, col=(1, 1, 1), amt=0.7)
            return fr, (3 if g > 0.4 else 0)
    out['A05'] = A05D

    # A06 7.83–10.57 片名重击（风格 D）：独立血月夜空板（A06_bg2，不再与 A02 共用），crane down —— 两层山脊精灵升起（远灰近黑，视差 90/340px）、
    #   血月下沉 + 每拍红光脉动、墨云横流腰斩月盘；7.85 白闪（全段唯一）+ 横向干笔刀光 + 白 / 血红火星迸发 + 色差；9.68 云内白闪电；
    #   前景焦外白光斑；片名本身是屏幕层 TitleD（画进生图的书法片名）
    class A06D(mod.A06):
        def __init__(self):
            self.bg = plate('A06_bg2'); self.ridge = lay('A01_ridge')      # §11-⑤ / 评审 P1-7：独立血月板，不再与 A02 共用
            self.bolt = fx2.Lightning(968, p0=(1500, 40), p1=(1760, 520), branches=6)
        def render(self, t):
            u = self.u(t); k = t - mod.TITLE_HIT; cr = eio(u); tc = t - (self.t0 + self.t1) / 2
            bp = sum(math.exp(-max(0.0, t - V(b)) / 0.16) * (t >= V(b)) for b in (8.75, 9.22, 9.68, 10.15))
            fr = at(self.bg, 1.16, dx=60, dy=-20 + 60 * cr)
            mx, my = 960 + 60 + 1.16 * (760 - 1024), 540 - 20 + 60 * cr + 1.16 * (330 - 576)   # 新月位（板里月在偏左中）
            fr = glow(fr, (mx, my), 420, 0.10 + 0.22 * bp, RED)
            fr = fog(fr, t - 7.0, 0, 150, 560, 0.42, (0.08, 0.08, 0.08), speed=(-150, 0))
            lt = t - V(9.68)
            if -0.06 <= lt < 0.9:
                fr = self.bolt.draw(fr, t, V(9.68), intensity=1.0, color=(1.0, 1.0, 1.0), sky=0.25)
            far = dict(expo=0.55, sat=1.0, tint=(1, 1, 1), lift=0.42, gamma=1.0)
            fr, _ = put(fr, t, self.ridge, (1024, 1152), (960 - 30 * tc, 1262.5 + 90 * (0.5 - cr)), 1.0, wind_amp=0, breathe=0, grade=far)
            fr = fog(fr, t, 1, 760, 980, 0.30, (0.75, 0.75, 0.75), speed=(110, 0))
            fr, _ = put(fr, t, self.ridge, (1024, 1152), (960 - 70 * tc, 1415 + 340 * (0.5 - cr)), 1.18, wind_amp=0, breathe=0)
            if k >= 0:
                fr = sparks2(fr, t, 851, (960, mod.TITLE_Y), n=90, life=0.8, speed=(300, 1300), dirc=(0, -1), spread=1.6, grav=500,
                             area=(700, 40), burst=True, t0=mod.TITLE_HIT, amt=1.0)
                fr = sparks2(fr, t, 861, (960, 900), n=40, life=1.6, speed=(80, 260), dirc=(0.4, -1), spread=0.6, grav=-30,
                             area=(1000, 60), amt=0.6 * (1 + 0.8 * bp))
            if 0 <= k < 0.14:
                fr = fr * (1 + 1.1 * (1 - k / 0.14)) + 0.22 * (1 - k / 0.14)
            q = (t - (mod.TITLE_HIT - 0.06)) / 0.12
            fr = brush(fr, (-100, mod.TITLE_Y + 70), (2020, mod.TITLE_Y - 40), q, 26, fade=1.0 - clamp01((k - 0.15) / 0.35), seed=6)
            ca = 6 if 0 <= k < 0.15 else (2 if 0 <= k < 0.4 else 0)
            return fr, ca
    out['A06'] = A06D

    # A07a 10.57–13.30 雨夜城楼大仰角（风格 D 生图：城楼精灵 + 墨云血红暴雨天），低机位推轨 + 升镜；
    #   11.98 / 12.89 云内白闪电照亮城楼；城下极小的背影（四拍走路姿势交替）走向门洞；墨线雨（远/中/近三层）+ 贴镜生图雨；
    #   前景虚焦旗杆擦过（推轨视差）；片名缩小挂在城前（TitleD，纸雾托底）
    class A07aD(mod.A07a):
        def __init__(self):
            self.sky = plate('A07_sky'); self.tower = lay('A07_tower')
            self.walk = [lay('A08_walk1')] + [lay_soft(n) for n in ('A08_w2', 'A08_w3', 'A08_w4')]
            self.bolts = (fx2.Lightning(1198, p0=(260, 30), p1=(520, 360), branches=6), fx2.Lightning(1289, p0=(1660, 30), p1=(1420, 330), branches=5))
            self.rs = fx2.RainSheet(705, density=0.8)
        def render(self, t):
            u = self.u(t); m = u - 0.5; tm = (self.t0 + self.t1) / 2
            env = lightn_env(t, ((V(11.98), 1.0), (V(11.98) + 0.13, 0.55), (V(12.89), 0.6)))
            fr = at(self.sky, 1.1, dy=-30 * m) * (1 + 0.6 * env)
            fr = self.bolts[0].draw(fr, t, V(11.98), intensity=1.0, color=(1, 1, 1), sky=0.2)
            fr = self.bolts[1].draw(fr, t, V(12.89), intensity=0.8, color=(1, 1, 1), sky=0.2)
            fr = ink_rain(fr, t, self.rs, 0.9, angle=10, layers=(0,), cam=(0, -40 * m))
            fr = fog(fr, t, 0, 300, 640, 0.25, (0.7, 0.7, 0.7), speed=(50, 0))
            tw = dict(expo=1.0 + 0.9 * env, sat=1.0, tint=(1, 1, 1), lift=0.0, gamma=1.0)
            fr, _ = put(fr, t, self.tower, (1024, 1152), (960, 1010), 1.06, wind_amp=0, breathe=0, grade=tw)
            pose, bob = walk_pose(self.walk, t, self.t0, 0.135)
            hh = 150 - 50 * eio(u)
            a_, k_ = pose.fit(hh)
            fr, _ = pose.draw(fr, t, a_, (960, 965 - 30 * eio(u) + 1.5 * bob), k_, wind_amp=4, breathe=0,
                              grade=dict(expo=0.5, sat=1.0, tint=(1, 1, 1), lift=0.0, gamma=1.0), rim=NORIM, wrap=0, shade=None)
            fr = fog(fr, t, 1, 820, 1060, 0.4, (0.6, 0.6, 0.6), speed=(-60, 0))
            fr = ink_rain(fr, t, self.rs, 0.9, angle=10, layers=(1, 2), cam=(0, -60 * m))
            fr = fg_rain(fr, t, tm, amt=0.45, vel=(150, 820))
            Lp = np.zeros((H // 2, W // 2), np.float32)
            px = (260 - 420 * u) / 2
            cv2.rectangle(Lp, (int(px - 16), 0), (int(px + 16), H // 2), 1.0, -1)
            Lp = cv2.resize(cv2.GaussianBlur(Lp, (0, 0), 7), (W, H))[..., None]
            fr = fr * (1 - Lp * 0.96) + Lp * 0.02
            if not hasattr(self, 'tz'):                                   # 片名区：不规则墨洗「纸雾」（评审 P1-5：不要椭圆白块）
                h4, w4 = H // 4, W // 4
                yy, xx = np.mgrid[0:h4, 0:w4].astype(np.float32)
                nz = cv2.resize(M.A.ink_noise(91, 256), (w4, h4)) if hasattr(M.A, 'ink_noise') else np.zeros((h4, w4), np.float32)
                d = np.sqrt(((xx - 240) / 205.) ** 2 + ((yy - 150) / 62.) ** 2)
                edge = np.clip((1.15 - d) / 0.55, 0, 1) * (0.55 + 0.9 * nz)          # 边缘被噪声咬成墨洗状
                tz = np.clip(edge ** 1.35, 0, 1) * 0.39                              # 峰值 0.39 × 加法只补到 100/255
                self.tz = cv2.resize(tz.astype(np.float32), (W, H))[..., None]
            fade = clamp01((V(13.42) - t) / 0.2)
            fr = fr + self.tz * fade * (1 - fr)                                  # 只往上补亮（不压暗），峰值 ≤100
            return fr, 0
    out['A07a'] = A07aD

    # A08 13.30–15.17 主角走出城门（风格 D 生图分层）：门外湿石大道板（门洞里透出）/ 背影（两张走路关键姿势交替，越走越远）/
    #   两扇包铁城门精灵（铰在门洞两侧，按开合角度横向透视压缩，先慢后快合上）/ 城墙门洞精灵（盖在最上）；
    #   人跨过门槛后先画人再画门 → 门在他身后合上；14.28 白闪电从门外劈亮、把他打成黑剪影；15.05 合成一线门缝 → a_seam 门缝开出 V01
    class A08D(mod.A08):
        HZ, K_WALL = 640.0, 1920 / 2048
        def __init__(self):
            self.out = plate('A08_out'); self.wall = lay('A08_wall')
            self.walk = [lay(n) for n in ('A08_walk1',) ] + [lay_soft(n) for n in ('A08_w2', 'A08_w3', 'A08_w4')]   # 图生图四拍（同机位同比例）；软边防画布直边
            self.feet = {id(L_): foot_of(L_) for L_ in self.walk}
            P, A = rgba('A08_door')
            lum = P.mean(-1, keepdims=True); P = lum + (P - lum) * 0.25          # 门板原图的大片红压到 25%（读成旧漆痕，不抢戏）
            ys, xs = np.nonzero(A > 0.5)
            self.dP, self.dA = P[ys.min():ys.max() + 1, xs.min():xs.max() + 1], A[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            hole = (self.wall.A < 0.5).astype(np.uint8)
            n, lab, st, _ = cv2.connectedComponentsWithStats(hole)
            i = 1 + int(np.argmax(st[1:, 4]))
            x, y, w, h = st[i, :4]
            kw = self.K_WALL
            self.hx0, self.hx1 = 960 + kw * (x - 1024), 960 + kw * (x + w - 1024)
            self.htop = 540 + kw * (y - 576)
            self.bolt = fx2.Lightning(1428, p0=(930, 380), p1=(1010, 640), branches=4)
            self.rs = fx2.RainSheet(805, density=0.8)
        def _door(self, fr, x0, wpx, flip):
            if wpx < 2: return fr
            hpx = 1080 - self.htop + 60
            P = cv2.resize(self.dP, (max(2, int(wpx)), int(hpx)), interpolation=cv2.INTER_AREA)
            A = cv2.resize(self.dA, (max(2, int(wpx)), int(hpx)), interpolation=cv2.INTER_AREA)
            if flip: P, A = P[:, ::-1], A[:, ::-1]
            X0 = int(round(x0)); Y0 = int(round(self.htop - 60))
            xa, xb = max(0, X0), min(W, X0 + P.shape[1]); ya, yb = max(0, Y0), min(H, Y0 + P.shape[0])
            if xb <= xa or yb <= ya: return fr
            Pc = P[ya - Y0:yb - Y0, xa - X0:xb - X0]; Ac = A[ya - Y0:yb - Y0, xa - X0:xb - X0, None]
            sh = 0.55 + 0.45 * (np.linspace(0, 1, xb - xa, dtype=np.float32)[None, :, None] if not flip else np.linspace(1, 0, xb - xa, dtype=np.float32)[None, :, None])
            fr[ya:yb, xa:xb] = fr[ya:yb, xa:xb] * (1 - Ac) + Pc * sh
            return fr
        def render(self, t):
            u = self.u(t); m = u - 0.5; tm = (self.t0 + self.t1) / 2
            q = clamp01((t - self.t0) / (V(15.05) - self.t0)); c = q ** 2.2
            env = lightn_env(t, ((V(14.28), 1.0), (V(14.28) + 0.12, 0.6), (V(14.28) + 0.3, 0.4)))
            fr = at(self.out, 1.08, cx=1045, cy=631, dy=self.HZ - 540) * (0.92 + 0.5 * env)
            bz = self.bolt.draw(np.zeros((H, W, 3), np.float32), t, V(14.28), intensity=1.0, color=(1.0, 1.0, 1.0), sky=0.0, glow=0.25)
            fr = fr * (1 - np.clip(bz[..., :1], 0, 1))                       # 白天幕上的闪电 = 墨线（减色）
            fr = ink_rain(fr, t, self.rs, 0.8, angle=6, layers=(0,))
            s_ = clamp01((t - self.t0) / (V(14.98) - self.t0)); z = 1 + 2.6 * s_
            pose, bob = walk_pose(self.walk, t, self.t0, 0.135)            # 一步 0.27s = 两拍
            hh = 760 / z; by = self.HZ + (1060 - self.HZ) / z + 6 * bob / z
            outside = by < 905                                               # 跨过门槛：此后先画人再画门 / 墙，门在他身后合上
            sil = clamp01((1000 - by) / 95)                                  # 走近门洞时渐变成逆光剪影（不在跨门槛那一帧跳变）
            def hero(fr):
                fx_, fy_ = self.feet[id(pose)]
                _, k_ = pose.fit(hh)
                g = dict(expo=(1.0 - 0.88 * sil) * (1 - 0.85 * env), sat=1.0, tint=(1, 1, 1), lift=0.0, gamma=1.0)
                return pose.draw(fr, t, (fx_ / pose.w, fy_ / pose.h), (960, by), k_, wind_amp=6, breathe=0, grade=g, rim=NORIM, wrap=0, shade=None)[0]
            if outside:
                yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
                shd = np.exp(-(((xx - 960) / (90 / z)) ** 2 + ((yy - by) / (8 / z)) ** 2))
                fr = fr * (1 - 0.6 * shd[..., None])
                fr = hero(fr)
            half = (self.hx1 - self.hx0) / 2
            wL = min(half * (0.10 + 0.90 * c), half - 2.0)
            fr = self._door(fr, self.hx0, wL, False)
            fr = self._door(fr, self.hx1 - wL, wL, True)
            gap = (self.hx1 - self.hx0) - 2 * wL
            if gap < 60:
                xx = np.arange(W, dtype=np.float32)[None, :]
                ln = np.exp(-((xx - (self.hx0 + self.hx1) / 2) / max(1.5, gap * 0.4)) ** 2) * (np.arange(H, dtype=np.float32)[:, None] > self.htop)
                fr = fr + ln[..., None] * 0.6 * (1 - gap / 60)
            wg = dict(expo=1.0 + 0.8 * env, sat=1.0, tint=(1, 1, 1), lift=0.0, gamma=1.0)
            fr, _ = put(fr, t, self.wall, (1024, 576), (960, 540), self.K_WALL, wind_amp=0, breathe=0, grade=wg)
            if not outside: fr = hero(fr)
            fr = ink_rain(fr, t, self.rs, 0.9, angle=6, layers=(1, 2))
            fr = fg_rain(fr, t, tm, amt=0.35, vel=(80, 840))
            fr = fog(fr, t, 0, 880, 1060, 0.30, (0.55, 0.55, 0.55), speed=(-45, 0))
            return fr, (3 if env > 0.6 else 0)
    out['A08'] = A08D

    # V01 15.17–16.97 ECU 雨打刃口（风格 D 生图：带水珠的斜刃 + 墨云压顶暴雨天）：墨云板下压（-80→+40）、刃身缓移推近；
    #   雨点打刃冠状白溅、墨线雨三层 + 贴镜生图雨；16.83「刀」一道干笔白刃光沿刃走（血红边、溅点）+ 色差
    class V01D(mod.V01):
        CM, EV = np.array([890.7, 615.7]), np.array([-0.8965, 0.4430])
        def __init__(self):
            self.bg = plate('V01_bg'); self.blade = lay('V01_blade')
            r = np.random.default_rng(15); self.drops = [(r.uniform(0.08, 0.92), r.uniform(0, 1.8)) for _ in range(26)]
            self.rs = fx2.RainSheet(915, density=0.8)
        def render(self, t):
            u = self.u(t); m = u - 0.5; tm = (self.t0 + self.t1) / 2
            fr = at(self.bg, 1.12, dy=-20 + 120 * (eio(u) - 0.5))
            fr = ink_rain(fr, t, self.rs, 0.8, angle=8, layers=(0, 1))
            k = 1.2 * (1 + 0.05 * u); dst = (980 - 90 * m, 600)              # §11.7：刃根在源图左缘截断 → 放大到 1.2，截断端始终在画外
            fr, _ = put(fr, t, self.blade, tuple(self.CM), dst, k, wind_amp=0, breathe=0)
            E1 = self.CM + self.EV * 1035; E2 = self.CM - self.EV * 1298        # 刃根（左下）/ 刃尖（右上）
            P0 = (dst[0] + k * (E1[0] - self.CM[0]), dst[1] + k * (E1[1] - self.CM[1]))
            P1 = (dst[0] + k * (E2[0] - self.CM[0]), dst[1] + k * (E2[1] - self.CM[1]))
            for i, (s, ph) in enumerate(self.drops):
                kk = (t * 1.3 + ph) % 1.8
                if kk < 0.18:
                    x = P0[0] + (P1[0] - P0[0]) * s; y = P0[1] + (P1[1] - P0[1]) * s - 18
                    Lc = np.zeros((H // 2, W // 2), np.float32); r_ = int((5 + 30 * kk) / 2)
                    cv2.ellipse(Lc, (int(x / 2), int(y / 2)), (r_, max(1, r_ // 3)), 0, 180, 360, 1.0, 1, cv2.LINE_AA)
                    fr = fr + cv2.resize(Lc, (W, H))[..., None] * 0.9 * (1 - kk / 0.18)
            fr = mod.ASH.draw(fr, t, 0.35, wind=(-30, 90))
            fr = ink_rain(fr, t, self.rs, 0.7, angle=8, layers=(2,))
            fr = fg_rain(fr, t, tm, amt=0.5, vel=(110, 900))
            a = t - CT(0, 5)
            if a >= 0:
                fr = brush(fr, (P0[0], P0[1] - 22), (P1[0], P1[1] - 22), a / 0.12, 16, fade=1 - clamp01((a - 0.12) / 0.3), seed=11, splat=10)
            return fr, (4 if 0 <= a < 0.1 else 0)
    out['V01'] = V01D

    # V02 16.97–17.90 CU 低机位：靴子踏进水洼（风格 D 生图：靴 + 衣摆精灵，湿石街夜雨背景板）；起脚（抬靴 + 前倾）→ 17.46 一脚踏下：
    #   水洼白溅 + 涟漪 + 震；衣摆风吹二级运动；水洼倒影（波纹扰动）；墨线雨 + 贴镜生图雨
    # 用户 20:05：脚步特写「假」的根因是整身图裁腿。改成同一机位的两张生图（踏下前 / 踏下，nano-banana-pro 图生图衍生），
    #   机位、街道、水洼、光向完全一致，只在 17.46 这一拍硬切，水花是生图里本来的，代码只补涟漪、白色硬边溅点和震。
    class V02D(mod.V02):
        def __init__(self):
            self.gain = 1.45                                               # 用户 20:05 返工后 V02 偏暗（平均 53）→ 提到 65 以上
            self.lift = plate('V02_lift3')                    # 踏下前一拍：靴抬起（外侧看，布底无纹路）、水洼平静
            self.stamp = plate('V02_boot3')                   # 踏下：布底靴踩实、溅水
            self.rs = fx2.RainSheet(925, density=0.8)
        def render(self, t):
            u = self.u(t); m = u - 0.5; tm = (t - (self.t0 + self.t1) / 2)
            ts = V(17.46)
            fr = at(self.stamp if t >= ts else self.lift, 1.06, dx=-24 * m, dy=10 * m)      # 机位缓移，以中点为零
            fr = ink_rain(fr, t, self.rs, 0.55, angle=8, layers=(0, 2))
            fr = fg_rain(fr, t, tm, amt=0.40, vel=(110, 900))
            if t >= ts:
                a = t - ts
                sp = (1180.0, 900.0)                                                     # 靴底入水点（两张图里同一处）
                fr = fx2.ripples(fr, t, [sp], [ts], color=(0.95, 0.95, 0.95), speed=520, amt=0.9, life=0.8)
                fr = sparks2(fr, t, 17, sp, n=34, life=0.45, speed=(260, 700), dirc=(0, -1), spread=1.3, grav=1500, area=(150, 12), amt=0.7,
                             t0=ts, burst=True)
            return fr * self.gain, (2 if 0 <= t - ts < 0.07 else 0)
    out['V02'] = V02D

    # V03 17.90–19.73 大俯瞰五百重甲方阵（风格 D 生图铺满画面，红缨、枪林）；去掉巨字「五百重甲」（不是点名保留的字）→ 方阵本身做主体：
    #   高机位横移 + 推进（方阵前压）+ 俯仰；行间白雾两层流动、墨线雨；步伐节奏的轻微上下颠（行军）
    class V03D(mod.V03):
        def __init__(self):
            self.bg = plate('V03_army'); self.rs = fx2.RainSheet(935, density=0.7)
        def render(self, t):
            u = self.u(t); m = u - 0.5
            march = 3.0 * math.sin(2 * math.pi * (t - self.t0) / 0.47)
            fr = at(self.bg, 1.10 * (1 + 0.05 * u), dx=-50 * m, dy=-30 * m + march)
            fr = fog(fr, t, 1, 300, 960, 0.26, (0.82, 0.82, 0.82), speed=(60, 10))
            fr = fog(fr, t, 2, 600, 1080, 0.18, (0.65, 0.65, 0.65), speed=(-40, 5))
            fr = ink_rain(fr, t, self.rs, 0.8, angle=12)
            return fr, 0
    out['V03'] = V03D

    # V04 19.73–20.67 LS 低机位雨夜长街（风格 D 生图：远处军阵枪林 + 血红日 + 湿石倒影）；鬼屠迎镜走近（两张走路关键姿势交替、步伐起伏、
    #   身形 600→800px，发丝 / 红带风吹）；背景板与人物视差（侧移 + 前推）；前景两支虚焦枪杆（生图）高速反向掠过；墨线雨 + 贴镜雨
    class V04D(mod.V04):
        def __init__(self):
            self.bg = plate('V04_bg2')                                         # 评审 P1-3 / 用户 20:05-5：中式札甲群演，单一消失点、同一地平面
            self.walk = [lay(n) for n in ('V04_walk1',)] + [lay_soft(n) for n in ('V04_w2', 'V04_w3', 'V04_w4')]   # 迎镜走四拍（图生图衍生，软边防直边）
            self.feet = {id(L_): foot_of(L_) for L_ in self.walk}
            self.spP, self.spA = spears((0, 5))
            self.rs = fx2.RainSheet(945, density=0.8)
        def render(self, t):
            u = self.u(t); m = u - 0.5; e = eio(u); tm = (self.t0 + self.t1) / 2
            fr = at(self.bg, 1.12 * (1 + 0.04 * u), dx=-60 * m, dy=-20)
            fr = fog(fr, t, 2, 450, 760, 0.35, (0.78, 0.78, 0.78), speed=(-50, 0), cam=(-160 * e, 0))
            fr = ink_rain(fr, t, self.rs, 0.8, angle=10, layers=(0, 1))
            pose, bob = walk_pose(self.walk, t, self.t0, 0.155)
            fx_, fy_ = self.feet[id(pose)]
            hh = 600 + 200 * e; _, k_ = pose.fit(hh)
            px, py = 1250 - 180 * e, 930 + 20 * e
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)                 # 接地阴影（与背景群演同一地面、同一光向）
            shd = np.exp(-(((xx - px) / (0.22 * hh)) ** 2 + ((yy - py - 4) / (0.02 * hh)) ** 2))
            fr = fr * (1 - 0.55 * shd[..., None])
            fr, _ = pose.draw(fr, t, (fx_ / pose.w, fy_ / pose.h), (px, py + 0.012 * hh * bob), k_, wind_amp=9, breathe=0, **KW)
            fr = ink_rain(fr, t, self.rs, 0.7, angle=10, layers=(2,))
            fr = fg_rain(fr, t, tm, amt=0.45, vel=(150, 860))
            Mx = affine((1024, 576), (960 - 1600 * m, 500), 1.25)
            fr, _ = blit(fr, self.spP * 0.35, self.spA, Mx)                   # 前景枪杆 = 清晰墨剪影（压暗），不做景深虚化
            return fr, 0
    out['V04'] = V04D

    # V05 20.67–21.17 ECU 手 + 刀特写拔刀（风格 D 生图，脸出画）：刀柄随拔刀沿刃向左上抽出 + 急推；20.82 刃口寒光（白星芒 + 白扫光沿刃滑过）
    class V05D(mod.V05):
        B0, B1 = np.array([1000.0, 522.0]), np.array([1330.0, 770.0])        # 源图：露刃段（护手 → 鞘口）
        def __init__(self):
            self.bg = plate('CU_bg1', flip=True); self.sp = lay('V05_draw')
        def render(self, t):
            u = self.u(t); m = u - 0.5
            fr = at(self.bg, 1.35, dx=-160, dy=80)                           # 与 A03 同类速度线，翻转 + 换裁切；清晰不虚化
            d = (self.B0 - self.B1) / np.linalg.norm(self.B0 - self.B1)
            pull = 30 * eio(u)
            k = 1920 / 2048 * 1.05 * (1 + 0.08 * u)
            dst = (960 - 40 * m + d[0] * pull, 560 + d[1] * pull)
            fr, Aw = put(fr, t, self.sp, (1024, 576), dst, k, wind_amp=3, breathe=0)
            def S(p): return (dst[0] + k * (p[0] - 1024), dst[1] + k * (p[1] - 576))
            g = math.exp(-max(0, t - V(20.82)) / 0.14) * (t >= V(20.82))
            q = clamp01((t - (V(20.82) - 0.08)) / 0.22)
            if 0 < q < 1:                                                    # 白刃光：一道硬边白线沿刃身由鞘口扫向护手
                a_, b_ = S(self.B1), S(self.B1 + (self.B0 - self.B1) * eio(q))
                Ls = np.zeros((H, W), np.float32); cv2.line(Ls, (int(a_[0]), int(a_[1] - 6)), (int(b_[0]), int(b_[1] - 6)), 1.0, 3, cv2.LINE_AA)
                fr = fr + Ls[..., None] * 0.9 * math.sin(math.pi * q)
            gp = S(self.B0 + (self.B1 - self.B0) * 0.45)
            fr = mod.pupil_glint(fr, gp, 1.0 * g, 1.6, col=(1.0, 1.0, 1.0))      # 墨线星芒
            return fr, (3 if g > 0.5 else 0)
    out['V05'] = V05D

    # V06 21.17–22.50 三连击（用户 20:05：「三连击很假，角色跟背景人物的高度不一致 → 换个方式，不必主角与敌人同框」）
    #   呈现 = 主角单人三连击 + 干笔刀光分格：白色纸底 + 放射墨线，鬼屠站在自己的接地阴影上（不再与军阵同框，比例矛盾从根上消失）；
    #   四张姿势由同一张图生图衍生（蓄势 → 21.20 横斩 → 21.47 收刀 → 21.86 上撩），切姿势帧是硬切（不带动态模糊），
    #   每刀命中：画面沿刀线被干笔刀光劈开一道白缝，缝里透出血红 / 墨色分格（两格不同明度、错开 10px），加白硬边闪、白 + 血红火星、震屏；
    #   21.20 那一刀的刀线 y≈600 与 V07 丹陛顶边做匹配剪辑（保留）。
    class V06D(mod.V06):
        RC = 21.47
        GROUND = 905.0
        SCALE = 0.66
        @staticmethod
        @lru_cache(None)
        def _paper():
            """漫画纸底：白纸 + 网点渐隐 + 从人物胸口放射的干笔速度线（两端收尖、笔毛飞白），全部代码画线，不用平滑渐变。"""
            q = 2
            base = np.full((H // q, W // q, 3), 0.80, np.float32)          # 纸底压到浅墨灰（V06 原 0.93 全白，亮度 178 过曝）
            yy, xx = np.mgrid[0:H // q, 0:W // q].astype(np.float32)
            d = np.hypot((xx - W / 4) / (W / 4), (yy - 540 / q) / (H / 3))
            dots = (np.sin(xx * 1.6) * np.sin(yy * 1.6) > 0.86).astype(np.float32)      # 网点
            tp = np.clip((d - 0.55) / 0.5, 0, 1)
            base = base * (1 - (0.38 * tp)[..., None] * (0.55 + 0.45 * dots[..., None]))
            cx, cy = W / q, 240.0
            L = np.zeros((H // q, W // q), np.float32)
            r = np.random.default_rng(6601)
            for i in range(150):
                ang = r.uniform(0, 2 * math.pi); ln = r.uniform(120, 620) / q
                r0 = r.uniform(60, 190) / q
                x0, y0 = cx + math.cos(ang) * r0, cy + math.sin(ang) * r0
                x1, y1 = cx + math.cos(ang) * (r0 + ln), cy + math.sin(ang) * (r0 + ln)
                w_ = r.uniform(0.6, 2.2)
                cv2.line(L, (int(x0), int(y0)), (int(x1), int(y1)), float(r.uniform(0.35, 1.0)), max(1, int(round(w_))), cv2.LINE_AA)
            L = cv2.GaussianBlur(L, (0, 0), 0.7)
            base = base * (1 - (L * 0.95)[..., None])
            base = cv2.resize(base, (W, H), interpolation=cv2.INTER_LINEAR)
            band = np.clip((np.arange(H, dtype=np.float32)[:, None] - 880) / 60, 0, 1)   # 地平线以下的灰场（墨洗，带网点）
            base = base * (1 - band[..., None] * 0.42)
            return base

        def __init__(self):
            self.poses = [lay('V06_wind')] + [lay_soft(n, 30) for n in ('V06_k1', 'V06_k2', 'V06_k3')]
            self.feet = {id(L_): foot_of(L_) for L_ in self.poses}
            self.rs = fx2.RainSheet(965, density=0.5)
        def render(self, t):
            u = self.u(t); m = u - 0.5; ts = CT(1, 10); ts2 = V(21.86); rc = V(self.RC)
            fr = self._paper().copy()
            fr = K.cam(fr, 1.0 + 0.02 * eio(u), 6 * m, 0)                       # 纸底极慢推，位移以中点为零
            F_ = int(round(t * 30))
            b1, rcF, b2 = int(round(ts * 30)), int(round(rc * 30)), int(round(ts2 * 30))
            k = 0 if F_ < b1 else (1 if F_ < rcF else (0 if F_ < b2 else 3))
            L_ = self.poses[k]
            fx_, fy_ = self.feet[id(L_)]
            fw = 26 * eout(clamp01((t - ts) / 0.3)) + 26 * eout(clamp01((t - ts2) / 0.4))
            ax = 900 + fw
            yy2, xx2 = np.mgrid[0:H, 0:W].astype(np.float32)
            shd = np.exp(-(((xx2 - ax) / 300) ** 2 + ((yy2 - self.GROUND) / 18) ** 2)) * 0.7 + \
                  np.exp(-(((xx2 - ax) / 520) ** 2 + ((yy2 - self.GROUND) / 46) ** 2)) * 0.25
            fr = fr * (1 - 0.85 * shd[..., None])
            fr, _ = put(fr, t, L_, (fx_, fy_), (ax, self.GROUND), self.SCALE, wind_amp=8, breathe=0, mblur=(0, 0))
            for (t0_, p0, p1, wd, sd) in ((ts, (ax - 250, 612), (ax + 720, 590), 26, 61),
                                         (ts2, (ax - 270, 780), (ax + 660, 150), 32, 62)):
                a_ = t - t0_
                if a_ < 0: continue
                g = math.exp(-a_ / 0.55)
                for sgn, col in ((1, RED * 0.9), (-1, np.array([0.05, 0.05, 0.06], np.float32))):
                    band = np.zeros((H // 2, W // 2), np.float32)
                    off = sgn * 10 * eout(clamp01(a_ / 0.06))
                    y0b, y1b = p0[1] + off + sgn * 4, p1[1] + off + sgn * 4
                    cv2.fillPoly(band, [np.array([(p0[0] / 2, y0b / 2), (p1[0] / 2, y1b / 2),
                                                  (p1[0] / 2, (y1b + sgn * 24) / 2), (p0[0] / 2, (y0b + sgn * 24) / 2)], np.int32)], 1.0, cv2.LINE_AA)
                    wb = cv2.resize(band, (W, H))[..., None] * 0.55 * (g ** 3)       # 分格缝只在命中 1–2 帧可见；三次方衰减，避免留下一条灰条
                    fr = fr * (1 - wb) + col * wb
                fr = brush(fr, p0, p1, clamp01(a_ / 0.07), wd, fade=g, seed=sd, splat=16)
                if a_ < 0.09:
                    fr = fr * (1 + 0.85 * (1 - a_ / 0.09)) + 0.08 * (1 - a_ / 0.09)
            a1 = t - ts; a2 = t - ts2
            if a1 >= 0:
                fr = sparks2(fr, t, 663, (ax + 430, 600), n=55, life=0.5, speed=(400, 1300), dirc=(1, -0.2), spread=0.8, grav=900,
                             burst=True, t0=ts, area=(120, 30), amt=0.9)
            if a2 >= 0:
                fr = sparks2(fr, t, 673, (ax + 380, 420), n=60, life=0.5, speed=(400, 1300), dirc=(1, -0.8), spread=0.9, grav=900,
                             burst=True, t0=ts2, area=(90, 40), amt=0.9)
            sk = pulse(t, ts, 0.09) * (t >= ts) + 0.9 * pulse(t, ts2, 0.09) * (t >= ts2)
            dx, dy, dr = K.shake(t, 13 * sk + 1.2, 15, 966)
            z = 1.0 + 0.03 * eio(u) + 0.025 * sk
            fr = ink_rain(fr, t, self.rs, 0.30, angle=12, layers=(0, 2), cam=(10 * m, 0))
            return K.cam(fr, z, dx, dy, dr), (5 if (0 <= a1 < 0.08 or 0 <= a2 < 0.08) else 0)
    out['V06'] = V06D

    # V07 22.50–23.43 LS 仰拍宫阶（风格 D 生图：殿门白光大逆光、黑檐压顶、两列血红宫灯）；丹陛顶边 y=600 接 V06 横刀光（匹配剪辑）；
    #   太上皇（按太上皇定妆照生图：无须无冠、小髻黑簪、黑纱宽袖、暗血红腰带长穗）立于丹陛顶端，逆光近剪影 + 白描边，纱袖风吹；
    #   摇臂升（MOVES3）、殿门白色体积光、灰白尘埃飘浮；「谁在高处」屏幕层横排字去掉（只留底部字幕）
    class V07D(mod.V07):
        def __init__(self):
            self.bg = plate('V07_bg'); self.emp = lay('V07_emperor')
            mod.EXPO['V07'] = mod.EXPO.get('V08', 1.0)                     # V07→V08 转场跨切点：V07 的段落曝光跟 V08 同值（不论 r8d_a2 是否改 V08），切点两侧不跳；
            self.gain = 1.0 / (mod.EXPO_ALL * mod.EXPO['V07'])              # 镜内乘回，V07 本身仍是生图原亮度
        def render(self, t):
            u = self.u(t); m = u - 0.5
            fr = at(self.bg, 1.3, dx=-20 * m, cx=1024, cy=760, dy=60)
            fr = fx2.god_rays(fr, (960, 380), strength=0.22, length=1.0, color=(1.0, 1.0, 1.0), t=t, src_r=160)
            ge = dict(expo=0.55, sat=1.0, tint=(1, 1, 1), lift=0.0, gamma=1.0)
            fr, _ = put(fr, t, self.emp, (1018, 1033), (960, 602), 0.39 * (1 + 0.04 * u), wind_amp=5, breathe=0.003, grade=ge)
            fr = mod.ASH.draw(fr, t, 0.5, wind=(30, -20))
            fr = fog(fr, t, 1, 860, 1080, 0.25, (0.55, 0.55, 0.55), speed=(40, 0))
            return fr * self.gain, 0
    out['V07'] = V07D
    return out


def apply(mod):
    """STYLE_D=1：替换 A01–V07 镜头类 + 片名层；本段画面字（V03 巨字、屏幕层 LY2 三句）去掉；风格 D 的曝光 / 前景粒子 / 转场边光。"""
    global M
    M = mod
    new = _build(mod)
    for nm, c in new.items():
        c.__name__ = nm
    for i, S_ in enumerate(mod.SHOTS):
        if S_.__name__ in new and not getattr(S_, '_r8d', False):
            c = new[S_.__name__]; c._r8d = True
            mod.SHOTS[i] = c
    mod.TITLE = TitleD()
    for sid in MINE[:-1]:                                              # V07 在 V07D.__init__ 里按 V08 设（见那里）
        mod.EXPO[sid] = 1.0 / mod.EXPO_ALL                            # 抵消段落 EXPO_ALL=1.15 提亮，保留生图本身的白纸 / 网点层次
    mod.EXPO['V01'] = mod.EXPO['V01'] * 1.30                                   # 评审 P1-6：V01 墨云占满画面、偏暗 → 提到 ≥65
    mod.EXPO['V03'] = mod.EXPO['V03'] * 1.20
    mod.FG.update({'A06': ('ash', 0.4), 'V07': ('ash', 0.3)})          # 金 / 橙火星前景 → 灰烬（火星由镜头自己画白 + 血红）
    mod.MOVES3['V06'] = mod.M3('sine_io', None, z=(1.05, 1.03), yaw=(-6, 6), note='风格 D：去掉 expo_out 急拉（径向模糊把前 3 帧整帧糊掉），冲击由镜内刀光 / 曝光脉冲 / 硬切冲击承担')
    n, pre, post, kw = mod.CUTS['V07']
    mod.CUTS['V07'] = (n, pre, post, dict(kw, glow=(1.0, 1.0, 1.0)))   # 匹配剪辑边光：金 → 白
    def mine(e):
        li, chars = e[0], e[1]
        return li in (0, 1) or (li == 2 and chars[0][0] == 0)          # 长夜压在我刀锋之上 / 拦不住一道 / 谁在高处（屏幕层字体叠加）
    mod.LY2[:] = [e for e in mod.LY2 if not mine(e)]
    mod.R5.ON['credits_off'] = True                                    # 第五轮 #1 用户原话：片头职务字幕全部去掉（片尾已有、重复）；片名区不受影响
