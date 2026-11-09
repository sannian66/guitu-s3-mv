"""units/chorus1.py —《谁定正邪》副歌一「立」（月夜·独战）摄制组
实现 crew/shots.json 的 S027(尾)–S048：58.5–89.5s。
接口：Chorus1().frame(t, dt) -> (float32 RGB 1080x1920x3 已收尾含黑边, ca)
每镜一个类（render(t) -> (fr, ca)，fr 为未收尾的线性画面）；切点转场由 CUTS 表驱动。"""
# [r4-props] 副歌一 6 处：S029/S032/S034/S039/S041/S043 末尾各加一层 PD.play（只加不删）。
import sys, math
ROOT = '/workspace/work/mv'
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, cv2
import props_dev as PD
import os
if os.environ.get('C1_RIG', 'live') == 'frozen':      # 默认用共享库 lib/rig.py（Skia）；C1_RIG=frozen 回退冻结版
    import c1_rig_frozen as rig
    sys.modules['rig'] = rig
else:
    import rig
import typo as T, trans as TR
from c1kit import *
import c1kit as K
import json
import vcam as VC
import grade_unify as GU                     # 全片统一 grade 层（GRADE_UNIFY=1 生效）
import vcam3 as V3
import fx2
import props as PR
import lyric3 as LY
# v3 字幕规范：思源宋多字重；宋体字形不加墨迹纹理
for _k, _f in (('serif_r', 'Regular'), ('serif_m', 'Medium'), ('serif_sb', 'SemiBold'), ('serif_b', 'Bold'), ('serif_black', 'Black')):
    T.FONTS[_k] = ROOT + f'/fonts/NotoSerifSC-{_f}.otf'
_glyph0 = T.glyph
def _glyph_v3(ch, fname='kai', size=120, texture=True):
    return _glyph0(ch, fname, size, texture and not str(fname).startswith('serif'))
T.glyph = _glyph_v3
MAIN_FONT = {'墙': os.environ.get('C1_MAIN_QIANG', 'serif_black'), '天': os.environ.get('C1_MAIN_TIAN', 'serif_black')}

_shake_v2 = shake
def shake(t, amp, freq=9.0, seed=0):
    """v3 震动克制：镜头内部的高频冲击抖（>5Hz）压到 35%，低频手持晃（≤5Hz）压到 60%"""
    return _shake_v2(t, amp * (0.35 if freq > 5 else 0.6), freq, seed)

LINES = T.load_lines()
FPS = 30
HM = json.load(open(ROOT + '/crew/hitmap_c1.json'))          # units/hitmap.py 卡点图（鼓轨分离 + 人声字头精修）
_WT = {}
for _w in HM['words']: _WT[(_w['line'], _w['k'])] = _w['t']
REAL_T = [None]          # 镜头内时间被重映射（定格/慢放）时，歌词仍按真实时间落点


def V(t):
    """声音时刻 → 视觉帧时刻（最近帧再提前 1 帧，感知同步）"""
    return (round(t * FPS) - 1) / FPS


def CT(li, k):
    """第 li 句第 k 个可见字的字头时间（人声 onset 精修）"""
    n = len([x for x in LINES[li]['times'] if x is not None])
    k = min(k, n - 1)
    return _WT.get((li, k), [x for x in LINES[li]['times'] if x is not None][k])


def tprog(li, chars_idx, t, dur=0.2, lead=0.0):
    """字的进度：在字头前 dur 秒开始，恰好在「字头视觉帧」落定（=1）"""
    tr = REAL_T[0] if REAL_T[0] is not None else t
    return [clamp01((tr - (V(CT(li, k)) - dur)) / dur) for k in chars_idx]


def dark_bg(seed=0, lo=0.02, hi=0.07):
    n = K.fbm(H // 4, W // 4, seed, base=3, octaves=5)
    l = lo + (hi - lo) * n
    return cv2.resize(np.stack([l, l * 1.01, l * 1.06], -1).astype(np.float32), (W, H))


def sw_project(sw, S, P, x, y, scale):
    th = (rig.VIEWS.get(sw.view, sw.view) if isinstance(sw.view, str) else sw.view) * rig.D2R
    fs = -1. if sw.flip else 1.
    X = P[0] * math.cos(th) + P[2] * math.sin(th)
    return (x + fs * X * scale / 100, y - P[1] * scale / 100)


def trail_hist(sw, chan_fn, t, x_fn, y_fn, scale, n=7, step=1 / 90):
    """纯骨骼采样得到刀光历史 [(guard, tip)]（不依赖布料状态，分段渲染一致）"""
    out = []
    for k in range(n, -1, -1):
        tt = t - k * step
        c = chan_fn(tt)
        S = sw._skeleton(c)
        out.append((sw_project(sw, S, S['guard'], x_fn(tt), y_fn(tt), scale), sw_project(sw, S, S['tip'], x_fn(tt), y_fn(tt), scale)))
    return out


def eye_layer(t, cx, cy, w, rot=0.0, blink=0.0):
    """程序化眼睛（刀面倒影用）：眉、上眼睑粗线、虹膜、瞳孔、眼神光、几缕乱发。返回亮度图 (H,W)。"""
    s = 4; Lc = np.zeros((H // 2, W // 2), np.float32)
    k = w / 300.0
    def P(pts):
        pts = np.asarray(pts, float) * k
        c, si = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        q = np.stack([pts[:, 0] * c - pts[:, 1] * si, pts[:, 0] * si + pts[:, 1] * c], 1) + [cx, cy]
        return (q / 2 * s).astype(np.int32)
    xs = np.linspace(-150, 150, 40)
    up = np.stack([xs, -55 * (1 - (xs / 150) ** 2) ** 0.8 + 6], 1)
    lo = np.stack([xs[::-1], 38 * (1 - (xs[::-1] / 150) ** 2) ** 1.1 + 6], 1)
    white = np.zeros_like(Lc); cv2.fillPoly(white, [P(np.vstack([up, lo]))], 0.35, cv2.LINE_AA, 2)
    ir = np.zeros_like(Lc)
    cv2.circle(ir, tuple(P([[8, 2]])[0]), int(46 * k / 2 * s), 1.0, -1, cv2.LINE_AA, 2)
    ir = ir * (white > 0)
    Lc = white * (1 - ir) + ir * 0.12
    cv2.circle(Lc, tuple(P([[8, 2]])[0]), int(18 * k / 2 * s), 0.0, -1, cv2.LINE_AA, 2)
    cv2.polylines(Lc, [P(up)], False, 0.9, max(1, int(5 * k)), cv2.LINE_AA, 2)          # 上睑线
    cv2.polylines(Lc, [P(lo)], False, 0.45, max(1, int(2 * k)), cv2.LINE_AA, 2)
    brow = np.stack([xs * 1.1, -125 - 25 * (1 - (xs / 150) ** 2) + xs * 0.12], 1)
    cv2.polylines(Lc, [P(brow)], False, 0.6, max(1, int(9 * k)), cv2.LINE_AA, 2)
    r = np.random.default_rng(380)
    for i in range(7):                                                                     # 乱发
        x0 = r.uniform(-220, 200); sw_ = 12 * math.sin(t * 2 + i)
        hs = np.stack([x0 + np.linspace(0, 160, 12) + sw_ * np.linspace(0, 1, 12), np.linspace(-260, 60, 12) + r.uniform(-40, 40)], 1)
        cv2.polylines(Lc, [P(hs)], False, 0.55, max(1, int(3 * k)), cv2.LINE_AA, 2)
    Lc = cv2.GaussianBlur(Lc, (0, 0), 1.0)
    gl = np.zeros_like(Lc); cv2.circle(gl, tuple(P([[-6, -12]])[0]), int(8 * k / 2 * s), 1.0, -1, cv2.LINE_AA, 2)
    Lc = Lc + cv2.GaussianBlur(gl, (0, 0), 1.2) * 1.6 + cv2.GaussianBlur(gl, (0, 0), 8) * 0.8
    return cv2.resize(Lc, (W, H))


class Shot:
    t0 = t1 = 0.0
    def u(self, t): return (t - self.t0) / (self.t1 - self.t0)


# =====================================================================================
# S027 尾 57.79–59.48  CU 刃口热浪，推进直到白光吞没（副歌前上冲）
class S027(Shot):
    t0, t1 = 57.794, 59.48
    def __init__(self):
        self.bg = dark_bg(27, 0.01, 0.05)
        self.bg[..., 0] *= 1.25
        self.tex = K.tile(512, 271, 6, 4)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        # 背景远处火光虚斑
        x, y = K.grid()
        fr += (np.exp(-(((x - 1500) / 500) ** 2 + ((y - 300) / 300) ** 2)) * 0.25)[..., None] * RED
        heat = 0.55 + 0.45 * u
        fr, bm = draw_blade(fr, (-300, 980), (2400, 180), 560, shine=0.15 + 0.9 * u, shine_w=0.06, return_mask=True)
        # 刃口烧红：只在刃口一侧（法线方向）渐变
        d0 = np.array([2700., -800.]); d0 /= np.linalg.norm(d0); n0 = np.array([-d0[1], d0[0]])
        sd = ((x + 300) * n0[0] + (y - 980) * n0[1]) / 280.0          # -1 背 … +1 刃
        hz = np.clip((sd - 0.1) / 0.9, 0, 1) ** 2 * heat
        fr = fr * (1 - 0.35 * hz[..., None] * bm[..., None]) + (hz * bm)[..., None] * (RED * 1.1 + GOLD * 0.15 * hz[..., None])
        # 刃口炽光线
        Lg = np.zeros((H // 2, W // 2), np.float32)
        d = np.array([2700., -800.]); d /= np.linalg.norm(d); nn = np.array([-d[1], d[0]])
        e0 = np.array([-300, 980]) + nn * 280 * 0.92; e1 = np.array([2400, 180]) + nn * 280 * 0.92
        cv2.line(Lg, tuple((e0 / 2).astype(int)), tuple((e1 / 2).astype(int)), 1.0, 2, cv2.LINE_AA)
        Lg = cv2.GaussianBlur(Lg, (0, 0), 6) * 3 + cv2.GaussianBlur(Lg, (0, 0), 1)
        fr += cv2.resize(Lg, (W, H))[..., None] * (RED * 1.3 + GOLD * 0.5) * heat
        # 热浪扭曲
        n = cv2.resize(K.tile_crop(self.tex, 0, -t * 160, H // 8, W // 8), (W, H))
        amp = 6 + 10 * u
        mx = (x + (n - 0.5) * amp).astype(np.float32); my = (y + (n - 0.5) * amp * 1.6).astype(np.float32)
        fr = cv2.remap(fr, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        fr = K.sparks(fr, t, 2701, (960, 700), n=50, life=1.0, speed=(150, 500), dirc=(0.3, -1), spread=0.6, grav=-80,
                      area=(900, 200), amt=0.8)
        z = 1.2 + 1.2 * ein(u, 2)
        dx, dy, dr = shake(t, 8 * u, 14, 27)
        fr = cam(fr, z / 1.2, dx, dy, dr, center=(1000, 560))
        fr = K.radial_blur(fr, (1000, 560), 0.06 * ein(u, 3))
        return fr, 0


# =====================================================================================
# S028 59.48–60.53 ECU 血滴落刃（慢放），背景巨字「血」朱红墨晕
class S028(Shot):
    t0, t1 = 59.48, 60.534
    T_HIT = V(59.70)         # 血滴落刃 = 「未」字头
    def __init__(self):
        self.bg = dark_bg(28, 0.02, 0.07)
        T.glyph('血', 'serif_black', 460, False)
        T.warm('未冷', 'xing', 130)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        # 巨字 血：墨洇显出（虚焦一点，作后景）
        p = eout((t - self.t0) / 0.35, 2)
        L = T.Layer()
        a = T.ink_bleed_glyph('血', 'serif_black', 460, max(0.02, p), seed=3, bleed=1.0)
        L.paste(a, 960, 470, (0.62, 0.05, 0.04))
        A = K.blur_ds(L.A, 3, 2)
        fr = over(fr, A * 0.95, np.array([0.55, 0.04, 0.03], np.float32) * (0.85 + 0.3 * K.blur_ds(L.A, 30)[..., None]))
        # 刀身横陈（中景）
        fr, bm = draw_blade(fr, (-200, 760), (2200, 640), 250, shine=0.25 + 0.5 * u, shine_w=0.1, return_mask=True)
        # 血滴（慢放）
        ts = 0.4                                      # 0.4x 慢放
        y_top = 735 - 0.04 * (2200 - 960) * 0 - 125  # 刀面上沿近似
        hit_y = 700 - (960 + 200) * (120 / 2400) - 115
        cx = 960
        if t < self.T_HIT:
            q = (t - (self.T_HIT - 0.5)) / 0.5
            yy = 60 + (hit_y - 60) * clamp01(q) ** 1.6
            lay = np.zeros((H, W), np.float32)
            cv2.ellipse(lay, (cx * 4, int(yy * 4)), (22 * 4, 30 * 4), 0, 0, 360, 1.0, -1, cv2.LINE_AA, 2)
            tri = np.array([[cx - 20, yy - 12], [cx + 20, yy - 12], [cx, yy - 78]]) * 4
            cv2.fillConvexPoly(lay, tri.astype(np.int32), 1.0, cv2.LINE_AA, 2)
            lay = cv2.GaussianBlur(lay, (0, 0), 1.0)
            fr = over(fr, lay, RED * 0.9)
            hl = np.zeros((H, W), np.float32); cv2.circle(hl, (cx - 8, int(yy - 6)), 6, 1.0, -1, cv2.LINE_AA)
            fr += cv2.GaussianBlur(hl, (0, 0), 2)[..., None] * 0.9
            # 速度残影
            fr = over(fr, K.blur_ds(lay, 6) * 0.3, RED)
        else:
            q = (t - self.T_HIT) * ts * 3
            # 刀面上的血迹扩散
            st = np.zeros((H, W), np.float32)
            rr = int(30 + 140 * eout(q / 0.8, 3))
            cv2.ellipse(st, (cx, int(hit_y + 8)), (rr, max(4, rr // 6)), -3, 0, 360, 1.0, -1, cv2.LINE_AA)
            nz = cv2.resize(K.tile_crop(K.tile(512, 2803, 8, 4), 0, 0, H // 4, W // 4), (W, H))
            st = np.clip(st * (nz * 1.6), 0, 1) * bm
            fr = over(fr, st * 0.92, RED * 0.75)
            # 皇冠飞溅（无状态）
            r = np.random.default_rng(2810)
            Lsp = np.zeros((H // 2, W // 2), np.float32)
            for i in range(46):
                ang = -math.pi / 2 + r.normal(0, 0.75); sp = r.uniform(250, 900)
                tt = q * 0.55
                px = cx + math.cos(ang) * sp * tt; py = hit_y + math.sin(ang) * sp * tt + 900 * tt * tt
                rad = r.uniform(2, 7) * (1 - 0.3 * tt)
                if py < hit_y + 30:
                    cv2.circle(Lsp, (int(px * 2), int(py * 2)), max(1, int(rad)), 1.0, -1, cv2.LINE_AA, 2)
                    cv2.line(Lsp, (int(px / 2), int(py / 2)), (int((px - math.cos(ang) * sp * 0.02) / 2),
                             int((py - math.sin(ang) * sp * 0.02) / 2)), 0.7, 1, cv2.LINE_AA)
            fr = over(fr, cv2.resize(Lsp, (W, H)), RED * 0.95)
            # 冲击白光
            fr += (np.exp(-q / 0.08) * 0.8) * cv2.GaussianBlur(st, (0, 0), 20)[..., None]
        # 前景虚焦飘尘
        fr = K.dust(fr, t, 2812, n=40, amt=0.35, size=(3, 8), blur=4, color=(0.9, 0.5, 0.4))
        z = (1.0 + 0.06 * eio(u)) * (1 + 0.06 * pulse(t, self.t0, 0.15))
        fr = cam(fr, z, 0, 0)
        ca = 3 if V(59.96) <= t < V(59.96) + 0.1 else 0
        pr = tprog(12, [1, 2], t, 0.18)
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        return fr, ca


# =====================================================================================
# S029 60.53–61.46 MCU 握刀手收紧，火星掠过；虚焦月；「未冷」右下错落
class S029(Shot):
    t0, t1 = 60.534, 61.463
    MOON = (900, 380)
    def __init__(self):
        self.hand = rig.HandCU(29)
        self.bg = K.sky(seed=29, cloud=0.5)
        rgb, A = K.moon_sprite(200)
        self.bg = K.paste_sprite(self.bg.copy(), rgb, A, *self.MOON)
        self.bg = cv2.GaussianBlur(self.bg, (0, 0), 14)
        T.warm('刀', 'xing', 300)
        self.T_DAO = V(CT(12, 3))

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        prog = eout((t - self.t0) / 0.5, 2) * 0.9 + 0.1 * pulse(t, self.T_DAO, 0.2) * (t >= self.T_DAO)
        fr = self.hand.draw(fr, 'grip', prog, t, self.MOON[0] + 20, self.MOON[1] + 170, 400, angle=-8,
                            rim_color=(0.9, 0.93, 1.0), rim_dir=(-0.2, -1.0), lift=0.35)
        fr = fr[0] if isinstance(fr, tuple) else fr
        fr = K.sparks(fr, t, 2901, (300, 760), n=55, life=0.8, speed=(600, 1300), dirc=(1, -0.25), spread=0.25,
                      grav=120, area=(200, 120), amt=1.0)
        # 「刀」字头：白刃一闪
        k = pulse(t, self.T_DAO, 0.06) * (t >= self.T_DAO - 0.04)
        if k > 0.02:
            fr = T._slash_light(fr, (960, 600), np.array([math.cos(-0.35), math.sin(-0.35)]), clamp01((t - self.T_DAO + 0.04) / 0.35), 2600)
        z = 1.05 + 0.07 * eio(u)
        dx, dy, dr = shake(t, 5 + 6 * k * 3, 1.6, 29)
        fr = cam(fr, z, dx, dy, dr)
        # 文字（屏幕层，不随镜头）
        pr = tprog(12, [3], t, 0.16)
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        fr = PD.play(fr, 'L13', t)  # [r4-props]
        return fr, 0


# =====================================================================================
# S030 61.46–62.83 LS 月下举刀指月；「刀」方印盖在月面；前景草叶
class S030(Shot):
    t0, t1 = 61.463, 62.833
    MOON = (900, 330); R = 210
    def __init__(self):
        self.sw = rig.Swordsman(30, view='side')
        sk = K.sky(seed=30, cloud=0.45).copy()
        rgb, A = K.moon_sprite(self.R)
        self.bg = K.paste_sprite(sk, rgb, A, *self.MOON)
        far = K.mountains(W, H, 760, 160, 301, 4)
        self.bg = over(self.bg, far * 0.55, (0.10, 0.11, 0.13))
        self.ridge = K.ridge_line(W, 930, 70, 302, 2)
        self.grass = K.Grass(303, n=70, y_base=1000, height=(180, 420))
        T.warm('不放', 'xing', 90)

    def render(self, t):
        u = self.u(t)
        crane = -70 + 120 * eio(u)          # 升降：画面整体下移 = 机位上升
        fr = cam(self.bg, 1.0, 0, -crane * 0.3)
        # 山脊（中景）
        rm = K.ridge_mask(H, W, self.ridge - crane * 0.0 + crane * 0.6)
        fr = over(fr, rm, (0.025, 0.025, 0.03))
        ph = clamp01((t - (self.t0 + 0.05)) / 0.9)
        S = self.sw.pose('raise_sword_sky', ph, t, wind=-220)
        fy = 935 + crane * 0.6
        fr, info = self.sw.draw(fr, 905, fy, 300, rim_color=(0.85, 0.9, 1.0), rim_dir=(0.1, -1), rim=1.4)
        # 刃光一闪（刀尖指月）
        g = pulse(t, V(61.88), 0.12) * (t >= V(61.88))
        if g > 0.01:
            tx, ty = info['tip']
            x, y = K.grid()
            st = np.exp(-(np.abs(x - tx) / 3 + np.abs(y - ty) / 60)) + np.exp(-(np.abs(y - ty) / 3 + np.abs(x - tx) / 90))
            fr += (st * g * 1.6 + np.exp(-((x - tx) ** 2 + (y - ty) ** 2) / 900) * g)[..., None] * 1.0
        # 印「刀」盖在月面（落印在 61.93 拍上）
        ps = clamp01((t - (V(61.88) - 0.18)) / 0.6)
        if ps > 0:
            pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        # 前景草叶（虚焦，视差更大）
        gm = self.grass.mask(t, 1.2, dy=crane * 1.2, blur=10)
        fr = over(fr, gm, (0.01, 0.01, 0.012))
        pr = tprog(12, [4, 5], t, 0.2)
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        return fr, 0


# =====================================================================================
# S031 62.83–64.20 ELS 太上皇天幕巨影 vs 一粒黑点；竖排天书「谁人来定」
class S031(Shot):
    t0, t1 = 62.833, 64.203
    def __init__(self):
        self.emp = rig.Emperor(31)
        self.sw = rig.Swordsman(310, view='back')
        self.bg = K.sky(seed=31, cloud=0.7, top=(0.015, 0.017, 0.025), bot=(0.09, 0.095, 0.11)).copy()
        rgb, A = K.moon_sprite(230)
        self.moon = (rgb, A)
        self.ridge = K.ridge_line(W, 905, 40, 312, 2)
        self.cloud = K.tile(512, 313, 4, 5)
        T.warm('谁人来定', 'xing', 150)

    def render(self, t):
        u = self.u(t)
        cr = -240 * (1 - eio(u))                  # 机位从低处升起 + 上摇（起幅看地面，落幅见巨影全貌）
        fr = cam(self.bg, 1.0, 0, -cr * 0.25)
        # 月在巨影头部（日食般背光）
        hx, hy = 960, 330 + cr
        fr = K.paste_sprite(fr, *self.moon, hx, hy - 30, scale=1.0)
        self.emp.pose('stand_backlit', (t * 0.2) % 1, t, wind=120)
        fr, _ = self.emp.draw(fr, 960, 330 + cr + 1700, 1880, rim_color=(0.85, 0.88, 0.95), rim_dir=(0, -1), rim=1.0,
                              lift=0.25, alpha=0.88)
        # 云层在巨影前流过（天幕感）
        cl = cv2.resize(K.tile_crop(self.cloud, t * 40, 0, H // 4, W // 4), (W, H))
        ca_ = np.clip((cl - 0.5) * 2.2, 0, 1) * 0.45
        fr = over(fr, ca_, (0.10, 0.11, 0.13))
        # 眼位两点金光
        x, y = K.grid()
        for ex in (-28, 28):
            fr += (np.exp(-(((x - (hx + ex)) / 9) ** 2 + ((y - (hy + 8)) / 2.5) ** 2)) * 0.9)[..., None] * GOLD
        # 地面草浪 + 一粒黑点
        rg = self.ridge + cr
        rm = K.ridge_mask(H, W, rg)
        wave = cv2.resize(K.tile_crop(self.cloud, t * 120, 300, H // 4, W // 4), (W, H))
        ground = (0.02 + 0.03 * wave)[..., None] * np.array([1, 1, 1.05], np.float32)
        fr = fr * (1 - rm[..., None]) + ground * rm[..., None]
        self.sw.pose('stand_wind', (t * 0.3) % 1, t, wind=300)
        fr, _ = self.sw.draw(fr, 960, rg[960] + 6, 46, rim_color=(0.8, 0.85, 0.95), rim_dir=(0, -1))
        # 63.82「正」金闪 1 帧
        fr = cam(fr, 1.0 + 0.04 * u, 0, 0)
        # 天书竖排（悬于云间，左上）
        pr = tprog(13, [0, 1, 2, 3], t, 0.3)
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        return fr, 0


# =====================================================================================
# S032 64.20–66.04 CU 正(金)/邪(朱)两印，中线一刀劈开、错位推开
class S032(Shot):
    t0, t1 = 64.203, 66.038
    T_CUT = V(65.085)
    def __init__(self):
        self.pap = K.paper_dark(32)
        x, y = K.grid()
        self.pap = self.pap * (1 + 0.6 * np.exp(-(((x - 960) / 700) ** 2 + ((y - 540) / 380) ** 2)))[..., None]
        T.warm('一方', 'xing', 110)

    def seals(self, t):
        fr = self.pap.copy()
        fr = T.stamp_seal(fr, '正', 640, 520, 320, clamp01((t - (V(CT(13, 4)) - 0.18)) / 0.6), style='yin', rot=-3, seed=321, color='gold')
        fr = T.stamp_seal(fr, '邪', 1280, 540, 320, clamp01((t - (V(CT(13, 5)) - 0.18)) / 0.6), style='yin', rot=4, seed=322, color='red')
        return fr

    def render(self, t):
        u = self.u(t)
        fr = self.seals(t)
        q = (t - self.T_CUT)
        if q > 0:
            e = eout(q / 0.35, 4)
            # 竖斩：左右两半错位推开
            th = math.radians(84); cx, cy = 960, 540
            x, y = K.grid()
            sd = (x - cx) * math.sin(th) - (y - cy) * math.cos(th)
            left = (sd < 0)[..., None]
            Lf = cam(fr, 1.0, 60 * e, 70 * e)          # 左半上移左移
            Rf = cam(fr, 1.0, -60 * e, -70 * e)
            g = np.abs(sd)
            out = np.where(left, Lf, Rf)
            gap = np.clip(1 - (g - 4 * e) / 3, 0, 1) * (e > 0.02)
            out = over(out, gap, (0.0, 0.0, 0.0))
            hot = np.exp(-g / 5) * math.exp(-q / 0.35) * 2 + np.exp(-g / 40) * math.exp(-q / 0.2) * 0.6
            out += hot[..., None] * np.array([1.0, 0.75, 0.45], np.float32)
            fr = out
            fr = K.sparks(fr, t, 3201, (960, 540), n=80, life=0.7, speed=(300, 1100), dirc=(1, 0), spread=1.6, grav=700,
                          burst=True, t0=self.T_CUT, area=(10, 380))
            fr = T._slash_light(fr, (960, 540), np.array([math.cos(th - math.pi / 2), math.sin(th - math.pi / 2)]) * -1,
                                clamp01(q / 0.5), 1500)
        else:
            # 刀光预兆：斜光从画面外扫入
            pass
        fr = cam(fr, 1.04 + 0.04 * eio(u), 0, 0)
        tx = V(CT(13, 5))
        if tx <= t < tx + 1 / 30 + 1e-3: fr = fr * 0.6 + RED * 0.5
        pr = tprog(13, [6, 7], t, 0.25)
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        fr = PD.play(fr, 'L14', t)  # [r4-props]
        return fr, 0


# =====================================================================================
# S033 66.04–67.87 LS 大地裂开，砖墙轰然升起；字刻在墙砖上「若规则是」
class S033(Shot):
    t0, t1 = 66.038, 67.872
    HOR = 700
    def __init__(self):
        self.bg = K.sky(seed=33, cloud=0.55, horizon=0.62).copy()
        far = K.mountains(W, H, 690, 90, 331, 5)
        self.bg = over(self.bg, far * 0.4, (0.12, 0.13, 0.15))
        # v3：换 props.CharWall 字砖（律令刻字），冷月顶光 —— 与 S034/S035/S036 材质/光区分
        cw = PR.CharWall(seed=33, cols=16, rows=11, brick=(150, 64), fname='song')
        y_ = np.linspace(0, 1, cw.tex.shape[0], dtype=np.float32)[:, None, None]
        self.wall = np.ascontiguousarray(cw.tex[:700, :2400]) * (1.55 - 0.5 * y_[:700]) * np.array([0.92, 0.97, 1.08], np.float32)
        self.sw = rig.Swordsman(330, view='back3q')
        self.dust_t = K.tile(512, 332, 5, 5)
        # 地面
        x, y = K.grid()
        g = np.clip((y - self.HOR) / (H - self.HOR), 0, 1)
        self.ground = (0.035 + 0.05 * g * K.fbm(H, W, 334, 8, 6))[..., None] * np.ones(3, np.float32)
        self.gm = (y >= self.HOR).astype(np.float32)
        self.crack = K.crack_path((180, self.HOR + 4), (1740, self.HOR + 10), 335, n=60, jag=0.01)
        T.warm('若规则是', 'song', 80)

    def wall_top(self, t):
        return self.HOR - 560 * eout((t - self.t0 - 0.05) / 1.2, 3)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        fr = fr * (1 - self.gm[..., None]) + self.ground * self.gm[..., None]
        top = self.wall_top(t)
        hh = int(self.HOR - top)
        if hh > 2:
            # 墙体：从地下升起（纹理随之上移）
            src = self.wall[:hh, 0:2400]
            q = np.float32([[-60, top], [1980, top], [1980, self.HOR], [-60, self.HOR]])
            wl = K.warp_quad(src, q)
            m = np.zeros((H, W), np.float32); cv2.fillConvexPoly(m, q.astype(np.int32), 1.0, cv2.LINE_AA)
            wl = wl * (0.55 + 0.45 * np.clip((np.arange(H)[:, None] - top) / 300, 0, 1))[..., None]
            fr = fr * (1 - m[..., None]) + wl
            # 墙顶月光边
            ed = np.zeros((H, W), np.float32); cv2.line(ed, (-60, int(top)), (1980, int(top)), 1.0, 2, cv2.LINE_AA)
            fr += cv2.GaussianBlur(ed, (0, 0), 1.5)[..., None] * 0.4 * np.array([0.8, 0.85, 1.0], np.float32)
            # 刻字：随墙升起
            pc = clamp01((t - 66.25) / 1.0)
            if pc > 0:
                yy = top + 110
                pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        # 地裂发光
        cm = K.draw_crack((H * 4 // 4, W), self.crack, 3, branches=10, seed=336, prog=eout((t - self.t0) / 0.3))
        fr = over(fr, cm, (0.0, 0.0, 0.0))
        # 尘浪 + 落石
        dm = cv2.resize(K.tile_crop(self.dust_t, t * 60, -t * 90, H // 4, W // 4), (W, H))
        y = np.arange(H, dtype=np.float32)[:, None]
        band = np.exp(-((y - self.HOR + 40) / 120) ** 2) * (0.3 + 0.7 * math.exp(-(t - self.t0) / 1.2))
        fr = over(fr, np.clip((dm - 0.3) * 1.8, 0, 1) * band * 0.85, (0.30, 0.31, 0.33))
        r = np.random.default_rng(3370)
        Lr = np.zeros((H // 2, W // 2), np.float32)
        for i in range(70):
            x0 = r.uniform(160, 1760); tb = r.uniform(0, 1.4); vy = r.uniform(-300, -50); sz = r.uniform(2, 9)
            a = t - self.t0 - tb
            if a < 0: continue
            yb = self.wall_top(self.t0 + tb)
            py = yb + vy * a + 900 * a * a; px = x0 + r.normal(0, 40) * a
            if py < self.HOR + 80:
                cv2.circle(Lr, (int(px / 2), int(py / 2)), max(1, int(sz / 2)), 1.0, -1, cv2.LINE_AA)
        fr = over(fr, cv2.resize(Lr, (W, H)), (0.02, 0.02, 0.02))
        # 前景：鬼屠背影（左下，近景剪影）
        self.sw.pose('stand_wind', (t * 0.35) % 1, t, wind=-260)
        fr, _ = self.sw.draw(fr, 330, 1110, 760, rim_color=(0.75, 0.8, 0.95), rim_dir=(0.4, -1), rim=0.8, lift=0.4)
        fr = K.dust(fr, t, 3380, n=60, amt=0.4, size=(2, 6), blur=3, drift=(40, -30))
        dx, dy, dr = shake(t, 10 * (0.5 + 0.5 * math.exp(-(t - self.t0) / 1.0)), 11, 33)
        fr = cam(fr, 1.0 + 0.08 * eio(u), dx, dy, dr)
        return fr, 0


# =====================================================================================
# S034 67.87–69.76 ECU 墙砖仰拍，墙高无尽；「墙」巨字从砖缝里浮起
class S034(Shot):
    t0, t1 = 67.872, 69.76
    T_POP = V(68.89)
    def __init__(self):
        wall, seam = K.brick_wall(2400, 1600, 220, 92, 9, 34)
        # v3：换光 —— 左侧掠射硬光（砖面浮雕 + 砖缝投影）+ 右侧沉入冷黑，铁青色调；与 S033/S035 字砖区分
        hgt = cv2.GaussianBlur(1 - seam, (0, 0), 3)
        gx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=5) / 16; gy = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=5) / 16
        rake = np.clip(1.0 + 3.2 * gx + 0.8 * gy, 0.15, 2.2)
        xx = np.linspace(0, 1, wall.shape[1], dtype=np.float32)[None, :]
        fall = 1.35 * np.exp(-xx * 1.6) + 0.12
        lum = wall.mean(-1) * rake * fall
        self.wall = np.stack([lum * 0.86, lum * 0.95, lum * 1.12], -1).astype(np.float32); self.seam = seam
        L = T.giant_layer('墙', MAIN_FONT['墙'], 'white', 900, 540, 440 if MAIN_FONT['墙'].startswith('serif') else 500)
        self.gA = L.A.copy()
        T.warm('铁壁铜墙', 'kai', 70)

    def quad(self, t):
        u = self.u(t)
        k = 0.55 - 0.3 * eio(u)          # 仰角加大 → 顶部收窄
        topy = 120 - 260 * eio(u)
        cx = 960
        return np.float32([[cx - 1500 * k, topy], [cx + 1500 * k, topy], [cx + 1600, 1160], [cx - 1600, 1160]])

    def render(self, t):
        u = self.u(t)
        off = int(260 * min(1.2, max(0.0, u)))
        src = self.wall[off:off + 1300, :]
        sm = self.seam[off:off + 1300, :]
        q = self.quad(t)
        fr = K.warp_quad(src, q)
        sw_ = K.warp_quad(sm, q)
        y = np.arange(H, dtype=np.float32)[:, None, None]
        topy = q[0][1]
        fr = fr * np.clip((y - topy) / 520, 0, 1) ** 1.3         # 墙顶消失于黑
        # 「墙」从砖缝里浮起：先缝里透光，再整字凸起
        p1 = clamp01((t - self.t0 - 0.1) / (self.T_POP - self.t0 - 0.1))
        gA = self.gA
        seamlight = gA * sw_ * eio(p1)
        fill = gA * (eout((t - self.T_POP) / 0.12) if t >= self.T_POP else 0.15 * p1)
        A = np.clip(np.maximum(seamlight * 1.4, fill), 0, 1)
        # 石质浮雕：上亮下暗
        bl = cv2.GaussianBlur(gA, (0, 0), 4)
        gy = cv2.Sobel(bl, cv2.CV_32F, 0, 1, ksize=5) * 0.02
        stone = (0.58 + np.clip(-gy, -0.3, 0.4))[..., None] * np.array([0.95, 0.97, 1.0], np.float32)
        sh = K.blur_ds(A, 22)
        fr = fr * (1 - 0.7 * sh[..., None] * (t >= self.T_POP))
        fr = over(fr, A, stone)
        fr += K.blur_ds(seamlight, 8)[..., None] * np.array([0.85, 0.88, 1.0], np.float32) * 0.6 * (1 - 0.7 * (t >= self.T_POP))
        fr = K.dust(fr, t, 3401, n=90, amt=0.5, size=(1, 4), drift=(10, 40), blur=1.2)
        if t >= self.T_POP:
            fr = K.sparks(fr, t, 3402, (900, 540), n=70, life=1.0, speed=(200, 700), dirc=(0, 1), spread=1.5, grav=900,
                          burst=True, t0=self.T_POP, area=(300, 280), color=(0.55, 0.56, 0.6), amt=0.8)
        dx, dy, dr = shake(t, 8 * pulse(t, self.T_POP, 0.25) * (t >= self.T_POP) + 2, 7, 34)
        fr = cam(fr, 1.0 + 0.05 * u, dx, dy, dr)
        pr = tprog(14, [4, 5, 6, 7], t, 0.25)
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        fr = PD.play(fr, 'L15', t)  # [r4-props]
        return fr, 0


# =====================================================================================
# S035 69.76–71.05 MS 疾跑起跳，空中斜劈墙，裂缝炸开；「那就劈开它」被斩断
class S035(Shot):
    t0, t1 = 69.76, 71.053
    T_HIT = V(70.02)
    SH = 70.02 - V(70.02)
    def __init__(self):
        self.sw = rig.Swordsman(35, view='side')
        # v3：换 CharWall（大字砖、楷体刻字），底部金红火光逆打 —— 与 S033 冷月顶光区分
        cw = PR.CharWall(seed=35, cols=16, rows=18, brick=(170, 72), fname='kai', chars_ratio=0.6,
                         text='顾全大局理所应当规矩方圆不得僭越')
        tex = cw.tex
        yy = np.linspace(0, 1, tex.shape[0], dtype=np.float32)[:, None, None]
        warm = (0.75 + 1.1 * np.clip((yy - 0.45) / 0.55, 0, 1) ** 1.5) * np.array([1.12, 0.92, 0.72], np.float32)
        self.wall = (tex * warm).astype(np.float32)
        self.crack = K.crack_path((900, 160), (1500, 960), 351, n=50, jag=0.03)
        T.warm('那就劈开它', 'kai', 110)

    def chan(self, t):
        t = t + self.SH
        if t < 69.95:
            ph = clamp01((t - 69.70) / 0.25) * 0.55
            c = rig.sample_action('leap', ph)
        else:
            if t < self.T_HIT: ph = 0.25 + 0.17 * (t - 69.95) / (self.T_HIT - 69.95)
            elif t < 70.30: ph = 0.42 + 0.16 * (t - self.T_HIT) / (70.30 - self.T_HIT)       # 慢放随势
            else: ph = 0.58 + 0.42 * clamp01((t - 70.30) / 0.35)
            c = rig.sample_action('slash_diag', ph)
            lp = rig.sample_action('leap', 0.62)
            air = clamp01(1 - (t - 70.45) / 0.2)
            for k in ('rf', 'lf', 'rfa', 'lfa'):
                c[k] = rig._lerp_ch(c[k], lp[k], air)
        return c

    def xy(self, t):
        t = t + self.SH
        x = 260 + 700 * eout((t - self.t0) / 0.4, 2) + 80 * clamp01((t - 70.1) / 0.6)
        a = clamp01((t - 69.82) / 0.75)
        y = 1000 - 330 * math.sin(math.pi * a) ** 0.8
        return x, y

    def render(self, t):
        u = self.u(t)
        camx = (self.xy(t)[0] - 960) * 0.55
        src = self.wall[200:1280, int(200 + camx * 0.6) % 400: int(200 + camx * 0.6) % 400 + 1920]
        fr = src * 0.8
        x, y = K.grid()
        fr = fr * (0.55 + 0.6 * np.exp(-(((x - 1100) / 900) ** 2 + ((y - 400) / 600) ** 2)))[..., None]
        # 裂缝（命中后沿刀线炸开）
        if t >= self.T_HIT:
            pc = eout((t - self.T_HIT) / 0.15, 2)
            cr = self.crack - [camx * 0.6, 0]
            cm = K.draw_crack((H, W), cr, 6, branches=14, seed=352, prog=pc)
            fr = over(fr, cm, (0, 0, 0))
            glow = K.blur_ds(cm, 6) * 1.5
            fr += glow[..., None] * GOLD * 0.5 * (0.4 + 0.6 * math.exp(-(t - self.T_HIT) / 0.4))
        X, Y = self.xy(t)
        sx = X - camx
        c = self.chan(t)
        self.sw.pose(None, 0, t, wind=-300, channels=c, travel=250)
        fr, info = self.sw.draw(fr, sx, Y, 640, rim_color=(0.85, 0.9, 1.0), rim_dir=(-0.6, -0.8), rim=1.2)
        hist = trail_hist(self.sw, self.chan, t, lambda tt: self.xy(tt)[0] - camx, lambda tt: self.xy(tt)[1], 640, n=7, step=1 / 100)
        if 69.93 < t < 70.5:
            fr = rig.blade_trail(fr, hist, intensity=1.4, glow=1.2, edge_color=RED)
        # 碎砖飞向镜头（前景）
        if t >= self.T_HIT:
            r = np.random.default_rng(3530)
            a = t - self.T_HIT
            Lb = np.zeros((H // 2, W // 2), np.float32)
            for i in range(26):
                ox, oy = r.uniform(950, 1450), r.uniform(250, 900)
                vx, vy = r.normal(0, 600), r.normal(-200, 400)
                s = (r.uniform(20, 70)) * (1 + 3 * a)
                px, py = ox + vx * a - camx * 0.6, oy + vy * a + 600 * a * a
                ang = r.uniform(0, 180) + 300 * a
                box = cv2.boxPoints(((px / 2, py / 2), (s / 2, s * 0.45 / 2), ang))
                cv2.fillConvexPoly(Lb, box.astype(np.int32), 1.0, cv2.LINE_AA)
            Lb = cv2.GaussianBlur(Lb, (0, 0), 2)
            fr = over(fr, cv2.resize(Lb, (W, H)), (0.03, 0.03, 0.035))
            fr = K.sparks(fr, t, 3540, (1200, 560), n=90, life=0.6, speed=(400, 1400), dirc=(-1, -0.3), spread=1.2,
                          grav=800, burst=True, t0=self.T_HIT, area=(150, 300))
        # 冲击：闪白 + 抖动；速度坡度用运动模糊表现
        fl = pulse(t, self.T_HIT, 0.05) * (t >= self.T_HIT)
        fr = fr + fl * 0.8
        fr = cam(fr, 1.03, 0, 0)
        if t > 70.27 and t < 70.57: fr = K.motion_blur(fr, 40, 0)
        p = clamp01((t - 69.60) / 0.9)
        fr = T.slash_cut(fr, '那就劈开它', p, places=LY.places('那就劈开它', 'bottom', red=('劈',)), color=LY.WHITE, angle=12,
                         cut_at=(self.T_HIT - 69.60) / 0.9, emph=('劈',), emph_color=LY.RED_T, slide=0.5, seed=35,
                         style_kw=dict(LY.STYLE))
        return fr, (3 if fl > 0.3 else 0)


# =====================================================================================
# S036 71.05–72.45 CU 墙缝透出一线金光（体积光）；「看个」沿缝洇出
class S036(Shot):
    t0, t1 = 71.053, 72.446
    def __init__(self):
        # v3：换 CharWall 超大字砖（一砖一字，宋体律令被金缝劈过），压暗，只靠缝里金光侧照
        cw = PR.CharWall(seed=36, cols=5, rows=7, brick=(520, 220), fname='song', chars_ratio=1.0, text='律令纲常尊卑规矩法度天理昭彰')
        xx = np.linspace(0, 1, 2300, dtype=np.float32)[None, :, None]
        self.wall = np.ascontiguousarray(cw.tex[:1300, :2300]) * (0.55 + 0.6 * xx) * np.array([1.05, 0.98, 0.9], np.float32)
        self.crack = K.crack_path((300, -100), (1900, 1300), 361, n=80, jag=0.025)
        cm = K.draw_crack((1300, 2300), self.crack, 7, branches=24, seed=362, prog=1.0)
        self.cm = cm
        self.wall_d = self.wall * (1 - cm[..., None])
        T.warm('看个', 'xing', 110)

    def render(self, t):
        u = self.u(t)
        # 沿缝推进（镜头沿裂缝方向移动）
        e = eio(u)
        ox, oy = 100 + 260 * e, 60 + 200 * e
        M = np.float32([[1, 0, -ox], [0, 1, -oy]])
        fr = cv2.warpAffine(self.wall_d, M, (W, H))
        cm = cv2.warpAffine(self.cm, M, (W, H))
        # 金光：缝内过曝 + 向镜头散射的体积光
        x, y = K.grid()
        core = cm
        lightA = K.blur_ds(core, 4) * 2.2 + K.blur_ds(core, 30) * 1.4
        breath = 0.95 + 0.15 * math.sin(t * 9)
        fr = fr * 0.7 + lightA[..., None] * GOLD * breath
        fr += core[..., None] * np.array([1.0, 0.95, 0.85], np.float32) * 1.2
        rays = K.radial_blur(np.repeat(np.clip(lightA, 0, 1)[..., None], 3, -1) * GOLD, (960, 540), 0.5, n=8, scale=4)
        fogm = cv2.resize(K.tile_crop(K.tile(512, 363, 5, 5), t * 50, t * 20, H // 4, W // 4), (W, H))
        fr += rays * (0.35 + 0.5 * fogm[..., None]) * 0.9
        fr = K.dust(fr, t, 3640, n=110, amt=0.7, size=(1, 4), drift=(25, -20), color=(1.0, 0.8, 0.5), blur=1.5)
        fr = cam(fr, 1.0 + 0.15 * e, 0, 0)
        # 「看个」沿裂缝方向，白色墨洇（光洇）
        th = math.degrees(math.atan2(1400, 1600))
        pr = tprog(15, [5, 6], t, 0.25)
        P = [dict(ch='看', x=640, y=470, size=120, rot=-th * 0.0, font='xing', idx=0, emph=False),
             dict(ch='个', x=800, y=610, size=120, rot=0.0, font='xing', idx=1, emph=False)]
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        return fr, 0


# =====================================================================================
# S037 72.45–74.10 ELS 长墙中一线金缝，鬼屠剪影立于缝前；「天亮」金字烧起又熄
class S037(Shot):
    t0, t1 = 72.446, 74.10
    CX = 1010
    def __init__(self):
        self.bg = K.sky(seed=37, cloud=0.6, horizon=0.7).copy()
        wall, _ = K.brick_wall(2400, 1600, 90, 38, 5, 37)
        self.wall = wall[:520, :2400]
        self.sw = rig.Swordsman(37, view='back')
        x, y = K.grid()
        self.gm = (y >= 820).astype(np.float32)
        T.warm('天亮', 'xing', 180)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        q = np.float32([[-200, 330], [2120, 360], [2120, 830], [-200, 830]])
        wl = K.warp_quad(self.wall, q)
        m = np.zeros((H, W), np.float32); cv2.fillConvexPoly(m, q.astype(np.int32), 1.0, cv2.LINE_AA)
        fr = fr * (1 - m[..., None]) + wl * 0.38        # 逆光：墙压成近剪影，只留金光
        ed = np.zeros((H, W), np.float32); cv2.line(ed, (-200, 330), (2120, 360), 1.0, 2, cv2.LINE_AA)
        fr += cv2.GaussianBlur(ed, (0, 0), 1.2)[..., None] * 0.3
        # 一线金缝
        x, y = K.grid()
        cr = K.crack_path((self.CX - 10, 340), (self.CX + 6, 830), 371, n=30, jag=0.04)
        cm = K.draw_crack((H, W), cr, 2.2, branches=3, seed=372)
        t_l = V(CT(15, 8))
        fl = 0.9 + 0.2 * math.sin(t * 11) + 1.0 * pulse(t, t_l, 0.5) * (t >= t_l)
        fr += (cm * 1.5 + K.blur_ds(cm, 10) * 2.2 + K.blur_ds(cm, 60) * 1.4)[..., None] * GOLD * fl
        # 体积光：金光从缝里向天空和镜头扇形喷出（与其他砖墙镜头区分：逆光大光柱）
        fr = fx2.god_rays(fr, (self.CX, 560), emit=np.clip(cm * 1.2 + K.blur_ds(cm, 12) * 2, 0, 1), strength=3.2 * fl,
                          length=1.0, color=GOLD, t=t, shafts=0.75, seed=37)
        # 地面 + 地面上的金光反射
        g = (0.03 + 0.02 * K.blur_ds(cm, 80))[..., None]
        fr = fr * (1 - self.gm[..., None]) + (g + (np.exp(-np.abs(x - self.CX) / 40) * np.exp(-(y - 820) / 60) * 0.25)[..., None] * GOLD) * self.gm[..., None]
        # 鬼屠剪影（缝前）
        self.sw.pose('stand_wind', (t * 0.3) % 1, t, wind=-250)
        fr, _ = self.sw.draw(fr, self.CX + 4, 870, 150, rim_color=tuple(float(v) for v in GOLD), rim_dir=(0, -1), rim=1.6, lift=0.3)
        fr = K.fog(fr, t, 373, amt=0.45, speed=(40, 0), y0=0.68, y1=1.0, color=(0.30, 0.32, 0.36))
        e = eio(u)
        fr = cam(fr, 1.1 - 0.1 * e, 0, 40 - 70 * e, center=(self.CX, 600))
        pb = clamp01((t - (V(CT(15, 7)) - 0.15)) / 1.9)
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        return fr, 0


# =====================================================================================
# S038 74.10–75.19 CU 刃面倒映眼睛，血沿刃纹流下；巨字「血」左侧半出画
class S038(Shot):
    t0, t1 = 74.10, 75.186
    def __init__(self):
        self.sw = rig.Swordsman(38, view='side', hair=2)
        self.bg = dark_bg(38, 0.008, 0.03)
        T.glyph('血', 'serif_black', 440, False)
        T.warm('未冷', 'xing', 120)

    def render(self, t):
        u = self.u(t)
        e = eio(u)
        fr = self.bg.copy()
        # 巨字 血（左侧半出画）
        L = T.giant_layer('血', 'serif_black', 'red', 330, 540, 440)
        fr = T.compose(fr, L, **T.auto_style('red'))
        p0, p1 = (1520, 1180), (1150, -150)
        fr, bm = draw_blade(fr, p0, p1, 380, shine=0.6 - 0.3 * e, shine_w=0.12, return_mask=True, seed=8)
        # 倒影：眼睛（profile 特写渲染到离屏，再按刀身蒙版合成，冷色）
        eye = eye_layer(t, 1322, 470 + 30 * e, 330, rot=-6, blink=0.0)
        refl = eye[..., None] * np.array([0.78, 0.85, 1.0], np.float32)
        fr = fr * (1 - 0.65 * bm[..., None]) + refl * bm[..., None] * 1.25
        # 血线沿刃纹流下
        d = np.array(p1, float) - np.array(p0, float); Ld = np.linalg.norm(d); d /= Ld; n = np.array([-d[1], d[0]])
        head = 0.85 - 0.6 * eio((t - self.t0) / 1.0)
        path = [np.array(p1) - d * Ld * s + n * (60 + 10 * math.sin(s * 30)) for s in np.linspace(0, 1 - head, 40)]
        Lb = np.zeros((H // 2, W // 2), np.float32)
        P = (np.array(path) * 2).astype(np.int32)
        for i in range(len(P) - 1):
            cv2.line(Lb, tuple(P[i]), tuple(P[i + 1]), 1.0, 5, cv2.LINE_AA, 2)
        if len(P): cv2.circle(Lb, tuple((P[-1] // 4)), 9, 1.0, -1, cv2.LINE_AA)
        Lb = cv2.resize(cv2.GaussianBlur(Lb, (0, 0), 1), (W, H)) * bm
        fr = over(fr, Lb, RED * 0.8)
        fr += K.blur_ds(Lb, 6)[..., None] * RED * 0.3
        hy = path[-1][1] if path else 540
        z = 1.0 + 0.06 * pulse(t, self.t0, 0.15)
        fr = cam(fr, z * 1.05, 0, (hy - 540) * 0.25 - 40 + 80 * e)
        ca = 3 if V(CT(16, 2)) <= t < V(CT(16, 2)) + 0.1 else 0
        pr = tprog(16, [1, 2], t, 0.18)
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        return fr, ca


# =====================================================================================
# S039 75.19–76.58 MS 战后断枪头盔，鬼屠缓步穿过，第一丝细雨；「未冷 骨未凉」右上错落
class S039(Shot):
    t0, t1 = 75.186, 76.579
    def __init__(self):
        self.sw = rig.Swordsman(39, view='side')
        self.bg = K.sky(seed=39, cloud=0.8, horizon=0.66, top=(0.03, 0.033, 0.04), bot=(0.13, 0.135, 0.15)).copy()
        far = K.mountains(W, H, 640, 70, 391, 5)
        self.bg = over(self.bg, far * 0.45, (0.16, 0.17, 0.19))
        r = np.random.default_rng(392)
        self.spears = [(r.uniform(-300, 2600), r.uniform(0, 1), r.uniform(-35, 35), r.uniform(160, 420)) for _ in range(34)]
        x, y = K.grid()
        self.ground = (y >= 700).astype(np.float32)
        T.warm('未冷骨未凉', 'xing', 90)

    def spear_layer(self, t, depth_lo, depth_hi, off):
        L = np.zeros((H // 2, W // 2), np.float32)
        for (x, dpt, ang, ln) in self.spears:
            if not (depth_lo <= dpt < depth_hi): continue
            s = 0.4 + 1.4 * dpt
            gx = ((x - off * (0.3 + dpt)) % 2900) - 300
            gy = 700 + 330 * dpt ** 1.5
            a = math.radians(ang)
            tip = (gx + math.sin(a) * ln * s, gy - math.cos(a) * ln * s)
            cv2.line(L, (int(gx * 2), int(gy * 2)), (int(tip[0] * 2), int(tip[1] * 2)), 1.0, max(1, int(3 * s)), cv2.LINE_AA, 2)
            if dpt > 0.5:   # 断口/枪缨
                cv2.circle(L, (int(tip[0] / 2), int(tip[1] / 2)), max(1, int(3 * s)), 1.0, -1, cv2.LINE_AA)
            if int(x) % 3 == 0:  # 头盔
                cv2.ellipse(L, (int((gx + 40 * s) / 2), int(gy / 2)), (int(22 * s), int(14 * s)), 0, 180, 360, 1.0, -1, cv2.LINE_AA)
        return cv2.resize(L, (W, H))

    def render(self, t):
        u = self.u(t)
        off = 320 * u                                # 横移（truck right）
        fr = self.bg.copy()
        g = (0.04 + 0.02 * np.linspace(0, 1, H)[:, None])[..., None] * np.ones(3, np.float32)
        fr = fr * (1 - self.ground[..., None]) + g * self.ground[..., None]
        fr = over(fr, self.spear_layer(t, 0, 0.45, off) * 0.8, (0.07, 0.075, 0.085))
        fr = K.fog(fr, t, 393, amt=0.5, speed=(-30, 0), y0=0.55, y1=0.8, color=(0.22, 0.23, 0.26))
        ph = ((t - self.t0) * 0.9) % 1
        self.sw.pose('walk', ph, t, wind=-180)
        fr, _ = self.sw.draw(fr, 820 + 60 * u, 985, 520, rim_color=(0.78, 0.84, 0.95), rim_dir=(-0.6, -0.8), rim=1.1)
        fl = self.spear_layer(t, 0.75, 1.01, off * 2.2)
        fr = over(fr, K.blur_ds(fl, 6), (0.01, 0.01, 0.012))
        fr = K.rain(fr, t, 394, n=160, amt=0.25 * clamp01((t - self.t0) / 0.6), speed=1500, angle=10, near=0.15)
        dx, dy, dr = shake(t, 6, 1.4, 39)
        fr = cam(fr, 1.04, dx, dy, dr)
        pr = tprog(16, [3, 4, 5], t, 0.18)
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        # fr = PD.play(fr, 'L17', t)  # [r4-props]  # [skip:载面丢失 2026-11-09]
        return fr, 0


# =====================================================================================
# S040 76.58–78.41 CU 四印逐拍落下拼成田字格：是/非/对/错
class S040(Shot):
    t0, t1 = 76.579, 78.414
    TS = tuple(V(CT(17, k)) for k in range(4))
    def __init__(self):
        pap = K.paper_light(40).copy()
        # 背景淡墨律令小字（宋体，权力的字）
        L = T.Layer()
        txt = '律令条文规矩方圆尊卑有序顾全大局理所应当不得逾越'
        r = np.random.default_rng(40)
        for cx in range(1800, 80, -64):
            for k, cy in enumerate(range(180, 920, 60)):
                T.place(L, txt[(cx // 64 + k * 3) % len(txt)], cx, cy, 44, 'ink', 'song', alpha=0.10 + 0.05 * r.random())
        self.pap = T.compose(pap, L, shadow=0, glow=0)
        x, y = K.grid()
        self.pap = self.pap * (0.75 + 0.3 * np.exp(-(((x - 960) / 900) ** 2 + ((y - 540) / 500) ** 2)))[..., None]

    def render(self, t):
        u = self.u(t)
        pr = [clamp01((t - (ts - 0.18)) / 0.6) for ts in self.TS]
        fr = T.seal_grid(self.pap.copy(), '是非对错', 960, 540, 260, pr, colors=['ink', 'red', 'ink', 'red'], seed=40)
        z = 1.0 + 0.1 * eio(u)
        pk = sum(pulse(t, ts, 0.1) * (t >= ts) for ts in self.TS)
        z *= 1 + 0.03 * min(1, pk)
        fr = cam(fr, z, 0, 0)
        return fr, 0


# =====================================================================================
# S041 78.41–80.22 LS 背影：刀横扛肩，独对长墙（金缝）；「我自己扛」右侧竖排
class S041(Shot):
    t0, t1 = 78.414, 80.225
    def __init__(self):
        self.bg = K.sky(seed=41, cloud=0.7, horizon=0.6).copy()
        wall, _ = K.brick_wall(2400, 1600, 120, 50, 6, 41)
        q = np.float32([[-300, 180], [2220, 180], [2220, 880], [-300, 880]])
        self.wall = K.warp_quad(wall[:800, :2400], q) * 0.8
        self.wm = np.zeros((H, W), np.float32); cv2.fillConvexPoly(self.wm, q.astype(np.int32), 1.0)
        cr = K.crack_path((940, 190), (960, 880), 411, n=40, jag=0.05)
        self.cm = K.draw_crack((H, W), cr, 3, branches=5, seed=412)
        self.sw = rig.Swordsman(41, view='back')
        T.warm('我自己扛', 'xing', 120)

    def render(self, t):
        u = self.u(t)
        fr = self.bg * (1 - self.wm[..., None]) + self.wall
        fl = 0.85 + 0.15 * math.sin(t * 8)
        fr = fr * 0.75
        fr += (self.cm * 1.3 + K.blur_ds(self.cm, 12) * 1.8 + K.blur_ds(self.cm, 70) * 1.0)[..., None] * GOLD * fl
        x, y = K.grid()
        fr = fr * (1 - (y > 880)[..., None] * 0.6)
        self.sw.pose('sword_on_shoulder', (t * 0.4) % 1, t, wind=-200)
        occ = np.zeros((H, W), np.float32)
        fr = fx2.god_rays(fr, (950, 520), emit=np.clip(self.cm * 1.5 + K.blur_ds(self.cm, 12) * 2, 0, 1), strength=0.9,
                          length=0.8, color=GOLD, t=t, shafts=0.8, seed=41)
        fr, _ = self.sw.draw(fr, 900, 1330, 980, rim_color=tuple(float(v) for v in GOLD * 0.9 + 0.1), rim_dir=(0, -1), rim=1.3, lift=0.35)
        fr = K.rain(fr, t, 413, n=260, amt=0.35, speed=1800, angle=8)
        fr = K.fog(fr, t, 414, amt=0.35, speed=(25, 0), y0=0.75, y1=1.0, color=(0.25, 0.26, 0.3))
        e = eio(u)
        fr = cam(fr, 1.0 + 0.05 * e, 0, -50 + 80 * e)
        pr = tprog(17, [4, 5, 6, 7], t, 0.3)
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        fr = PD.play(fr, 'L18', t)  # [r4-props]
        return fr, 0


# =====================================================================================
# S042 80.22–82.06 ELS 月被云吞没，「天」巨字在月晕中，被一道刀光划掉
class S042(Shot):
    t0, t1 = 80.225, 82.059
    T_SL = V(81.14)
    T_PAN = V(81.52)
    def __init__(self):
        self.bg = K.sky(seed=42, cloud=0.3, top=(0.01, 0.012, 0.018), bot=(0.05, 0.055, 0.065)).copy()
        rgb, A = K.moon_sprite(240)
        self.bg = K.paste_sprite(self.bg, rgb, A, 960, 520)
        self.cl = K.tile(1024, 421, 4, 6)
        self.L = T.giant_layer('天', MAIN_FONT['天'], (0.03, 0.03, 0.035), 960, 540, 440 if MAIN_FONT['天'].startswith('serif') else 500)
        T.warm('不判', 'xing', 110)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        # 天字（月晕中，墨色剪影在月面上更有压迫感）
        if t < self.T_SL:
            fr = T.compose(fr, self.L, shadow=0.0, outline=2, outline_color=(0.75, 0.8, 0.9), glow=0.6, glow_color=(0.7, 0.78, 0.95),
                           opacity=eout((t - self.t0 - 0.1) / 0.4))
        else:
            fr = T.slash_layer(fr, self.L, clamp01((t - self.T_SL) / 0.8), (960, 540), -32, slide=0.35, sz=520, length=1700,
                               style_kw=dict(shadow=0.0, outline=2, outline_color=(0.75, 0.8, 0.9), glow=0.6, glow_color=(0.7, 0.78, 0.95)), seed=42)
        # 云吞月（前景云卷过）
        sh = 200 + 900 * eio(u)
        cl = cv2.resize(K.tile_crop(self.cl, sh, 100 - 80 * u, H // 2, W // 2), (W, H))
        x, y = K.grid()
        cov = np.clip((cl - 0.62 + 0.25 * u) * 3.5, 0, 1)
        lit = np.exp(-((x - 960) ** 2 + (y - 520) ** 2) / (2 * 420 ** 2))
        fr = over(fr, cov * 0.9, (0.05 + 0.25 * lit)[..., None] * np.array([0.9, 0.93, 1.0], np.float32))
        fr = fr * (1 - 0.35 * eio(u))
        # 81.62「判」冲击
        k = pulse(t, self.T_PAN, 0.12) * (t >= self.T_PAN)
        z = (1.0 + 0.06 * eio(u)) * (1 + 0.10 * k)
        dx, dy, dr = shake(t, 12 * k, 14, 42)
        fr = cam(fr, z, dx, -30 * eio(u) + dy, 3 * eio(u) + dr)
        if self.T_PAN <= t < self.T_PAN + 2 / 30 + 1e-3: fr = fr * 0.5 + RED * 0.6
        if V(80.86) <= t < V(80.86) + 1 / 30 + 1e-3: fr = fr + 0.25
        pr = tprog(18, [1, 2], t, 0.18)
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        return fr, (4 if k > 0.4 else 0)


# =====================================================================================
# S043 82.06–82.99 MCU 鬼屠转头正视镜头，眼中寒光；「量」方印右下
class S043(Shot):
    t0, t1 = 82.059, 82.988
    def __init__(self):
        self.sw = rig.Swordsman(43, view='side', hair=1.0)
        self.bg = dark_bg(43, 0.02, 0.08)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        fr = K.fog(fr, t, 431, amt=0.35, speed=(60, 0), y0=0.2, y1=1.0, color=(0.2, 0.21, 0.24))
        ph = clamp01((t - self.t0 + 0.1) / 0.8)
        fr, info = rig.profile_cu(fr, self.sw, t, 880, 560, 400, light='moon', glint=1.0 + 2.5 * clamp01((ph - 0.5) / 0.3),
                                  action='turn_head', phase=ph)
        fr = K.sparks(fr, t, 4301, (200, 900), n=40, life=0.9, speed=(300, 800), dirc=(1, -0.6), spread=0.4, grav=80,
                      area=(100, 100), amt=0.9)
        z = 1.0 + 0.18 * eout(u, 2)
        fr = cam(fr, z, 0, 0, center=(860, 500))
        pr = tprog(18, [3], t, 0.16)
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        fr = PD.play(fr, 'L19', t)  # [r4-props]
        return fr, 0


# -------------------------------------------------------------------------------------
# S043 生图精灵版（SPRITE_MODE=1 才启用；默认仍是上面的代码人物）。人物 = assets/gen/hero/S043_cut.png，
# 场景/雾/雨/火星/运镜/字幕仍为代码。SPRITE_EXT="t0,t1" 可把镜头拉长到试点窗口（单镜试渲用，不影响剪辑表）。
SPRITE_MODE = os.environ.get('SPRITE_MODE', '0') == '1'
class S043Sprite(Shot):
    t0, t1 = 82.059, 82.988
    PNG = ROOT + '/assets/gen/hero/S043_cut.png'
    FACE = (0.556, 0.478)                       # 精灵内脸中心（归一化）
    EYES = ((0.5175, 0.4256), (0.597, 0.420))   # 两眼（画面左/右）
    def __init__(self):
        import sprite as SP
        self.sp = SP.layer(self.PNG)
        self.bg = dark_bg(43, 0.02, 0.07)
        ext = os.environ.get('SPRITE_EXT')
        self.win = tuple(float(x) for x in ext.split(',')) if ext else None
        self.T_GLINT = 82.62

    def render(self, t):
        a, b = self.win or (self.t0, self.t1)
        u = clamp01((t - a) / (b - a))
        tt = t - a                                       # 镜内秒
        # --- 背景（远）：暗底 + 背后冷月光晕（rim 光的来源）+ 远雾 + 远雨，推得慢（视差）
        fr = self.bg.copy()
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        glow = np.exp(-(((xx - 560) / 620) ** 2 + ((yy - 230) / 420) ** 2))
        fr = fr + glow[..., None] * np.array([0.10, 0.12, 0.16], np.float32)
        fr = K.fog(fr, t, 431, amt=0.32, speed=(60, 0), y0=0.15, y1=1.0, color=(0.2, 0.21, 0.24))
        fr = K.rain(fr, t, seed=4303, n=380, speed=1500, angle=10, length=(20, 50), amt=0.16, near=0.0)
        fr = cam(fr, 1.0 + 0.03 * eio(u), 10 * eio(u), 0)
        # --- 人物：转头动势（前 0.25s 从右侧甩入 + 方向模糊）→ 静止慢推；推得比背景快 = 2.5D
        k = eout(clamp01(tt / 0.26), 3)
        dx = 110 * (1 - k); rot = -2.5 * (1 - k)
        z = 0.95 * (1.0 + 0.09 * eout(u, 2))
        cx = 1010 + dx - 30 * eio(u); cy = 470 + 6 * eio(u)
        mb = (60 * (1 - k) if tt < 0.26 else 0.0, 0.0)
        s = z * W / self.sp.w * 1.0
        fr, Aw = self.sp.draw(fr, t, self.FACE, (cx, cy), s * self.sp.w / self.sp.w, rot=rot, mblur=mb)
        # --- 眼中寒光（代码画的星芒，落在「我」后乐句上）
        g = math.exp(-((t - self.T_GLINT) / 0.10) ** 2) + 0.25 * clamp01((t - self.T_GLINT) / 0.1)
        if g > 0.02:
            ang = math.radians(rot)
            L = np.zeros((H, W), np.float32)
            for ex, ey in self.EYES[1:]:
                px = cx + (ex - self.FACE[0]) * self.sp.w * s; py = cy + (ey - self.FACE[1]) * self.sp.h * s
                p = (int(px), int(py))
                cv2.line(L, (p[0] - 38, p[1] + 2), (p[0] + 38, p[1] - 2), 0.35, 1, cv2.LINE_AA)
                cv2.line(L, (p[0], p[1] - 12), (p[0], p[1] + 12), 0.25, 1, cv2.LINE_AA)
                cv2.circle(L, p, 2, 1.0, -1, cv2.LINE_AA)
            L = cv2.GaussianBlur(L, (0, 0), 1.0) + cv2.GaussianBlur(L, (0, 0), 6) * 0.9
            fr = fr + L[..., None] * g * np.array([0.8, 0.9, 1.0], np.float32)
        # --- 前景（近）：火星 + 近雨丝（压在人物上 = 人物在场景里）
        fr = K.sparks(fr, t, 4301, (200, 900), n=40, life=0.9, speed=(300, 800), dirc=(1, -0.6), spread=0.4, grav=80,
                      area=(100, 100), amt=0.9)
        fr = K.rain(fr, t, seed=4304, n=70, speed=2600, angle=12, length=(60, 140), amt=0.22, near=0.6)
        return fr, 0
S043Sprite.__name__ = 'S043'          # 剪辑/运镜/前景/曝光表沿用 S043 的键


# =====================================================================================
# S044 82.99–84.10 CU 手按刀柄，拇指推刀，鞘口一线光（吸气停顿）
class S044(Shot):
    t0, t1 = 82.988, 84.10
    def __init__(self):
        self.hand = rig.HandCU(44)
        self.bg = dark_bg(44, 0.006, 0.03)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        prog = eio(clamp01((t - self.t0 - 0.15) / 0.8))
        r = self.hand.draw(fr, 'thumb_push', prog, t, 960, 560, 560, angle=0, rim_color=(0.85, 0.9, 1.0), rim_dir=(-0.3, -1))
        fr = r[0] if isinstance(r, tuple) else r
        fr = K.dust(fr, 0.0 + (t - self.t0) * 0.05, 4401, n=50, amt=0.35, size=(1, 3), blur=1.5)   # 尘埃悬停（风停）
        fr = cam(fr, 1.0 + 0.08 * eio(u), 0, 0)
        pr = tprog(18, [4], t, 0.18)
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        pass  # v3 字幕统一：此处歌词移到 lyric3 统一字幕层
        return fr, 0


# =====================================================================================
# S045 84.10–85.29 LS 旋身斩一圈，刀光成圆环，雨滴被斩开；「这一刀」沿圆环环绕
class S045(Shot):
    t0, t1 = 84.10, 85.287
    T_HIT = V(84.50)
    SH = 84.56 - V(84.50)
    def __init__(self):
        self.sw = rig.Swordsman(45, view=60)
        # 去掉砖墙：开阔月夜旷野（与墙镜头区分）
        sk = K.sky(seed=45, cloud=0.55, horizon=0.72, top=(0.03, 0.035, 0.05), bot=(0.16, 0.17, 0.2)).copy()
        rgb, A = K.moon_sprite(170)
        sk = K.paste_sprite(sk, rgb, A, 1500, 300)
        far = K.mountains(W, H, 760, 120, 451, 4)
        self.bg = over(sk, far * 0.6, (0.07, 0.075, 0.09))
        x, y = K.grid(); self.gm = (y >= 800).astype(np.float32)
        T.warm('这一刀', 'xing', 240)

    def phase(self, t):
        t = t + self.SH
        if t < 84.42: return 0.30 * clamp01((t - self.t0) / 0.32) ** 1.5 * 0.6      # 慢起 0.3x
        if t < 84.74: return 0.18 + 0.62 * (t - 84.42) / 0.32                 # 1.5x 爆发
        return 0.80 + 0.2 * clamp01((t - 84.74) / 0.4)

    def render(self, t):
        u = self.u(t)
        fr = self.bg * (1 - self.gm[..., None] * 0.75)
        view = 60 + 30 * eio(u)           # 环绕 30°
        self.sw.view = view
        ph = self.phase(t)
        self.sw.pose('spin_slash', ph, t, wind=-200)
        cx, fy, sc = 960, 940, 560
        hist = trail_hist(self.sw, lambda tt: rig.sample_action('spin_slash', self.phase(tt)), t, lambda tt: cx, lambda tt: fy, sc,
                          n=10, step=1 / 120)
        ring_y = fy - 59 * sc / 100 - 8 * sc / 100
        # 文字绕环（后半圈在人后）
        prog = tprog(19, [0, 1, 2], t, 0.16)
        front = None   # v3 字幕统一：「这一刀」移到 lyric3 统一字幕层（右侧竖排）
        fr, info = self.sw.draw(fr, cx, fy, sc, rim_color=(0.85, 0.9, 1.0), rim_dir=(-0.5, -0.8), rim=1.3)
        if 84.3 < t < 85.0:
            fr = rig.blade_trail(fr, hist, intensity=1.5, glow=1.4, edge_color=RED)
        # 圆形刀光环（命中拍扩散）
        if t >= self.T_HIT:
            a = t - self.T_HIT
            R = 520 + 900 * eout(a / 0.6, 2)
            ring = np.zeros((H // 2, W // 2), np.float32)
            cv2.ellipse(ring, (cx // 2, int(ring_y / 2)), (int(R / 2), int(R * 0.22 / 2)), 0, 0, 360, 1.0, 2, cv2.LINE_AA)
            ring = cv2.GaussianBlur(ring, (0, 0), 1.5) * 2 + cv2.GaussianBlur(ring, (0, 0), 8) * 3
            fr += cv2.resize(ring, (W, H))[..., None] * np.array([1.0, 0.95, 0.9], np.float32) * math.exp(-a / 0.35)
        # 雨：被斩开的雨（环带附近雨丝断开并溅散）
        x, y = K.grid()
        band = 1 - np.exp(-((y - ring_y) / 18) ** 2) * (t >= self.T_HIT)
        fr = K.rain(fr, t, 451, n=320, amt=0.4, speed=2000 if t > 84.36 else 600, angle=6, region=band)
        if t >= self.T_HIT:
            fr = K.sparks(fr, t, 4520, (cx, ring_y), n=120, life=0.6, speed=(300, 900), dirc=(1, 0), spread=3.0, grav=900,
                          burst=True, t0=self.T_HIT, area=(500, 20), color=(0.75, 0.82, 0.95), amt=0.9)
        fr = cam(fr, 1.02, 0, 0)
        return fr, 0


# =====================================================================================
# S046 85.29–86.19 MCU 定格：刀停在镜头前，刀身浮现「就是我的回答」，墨爆吞没
class S046(Shot):
    t0, t1 = 85.287, 86.192
    T_ANS = V(CT(19, 8))      # 答
    T_CRASH = V(85.69)       # 鼓组回归（重音镲）
    def __init__(self):
        self.bg = K.sky(seed=46, cloud=0.5).copy()
        rgb, A = K.moon_sprite(140)
        self.bg = cv2.GaussianBlur(K.paste_sprite(self.bg, rgb, A, 1500, 330), (0, 0), 10)
        self.sw = rig.Swordsman(46, view='front3q')
        T.warm('就是我的回', 'song', 72); T.warm('答', 'song', 72)

    def render(self, t):
        u = self.u(t)
        tr = REAL_T[0] if REAL_T[0] is not None else t     # 画面定格慢放，刻字/闪光/墨爆按真实时间
        fr = self.bg.copy()
        self.sw.pose('stand_wind', 0.3, self.t0 + min(t - self.t0, 0.3) * 0.0 + (t - self.t0), wind=-150)
        fr, _ = self.sw.draw(fr, 1350, 1700, 1500, rim_color=(0.8, 0.85, 1.0), rim_dir=(0.6, -0.8), rim=1.0, lift=0.3,
                             sword_visible=False)
        fr = cv2.GaussianBlur(fr, (0, 0), 3)
        p0, p1 = (-150, 700), (2050, 470)
        fr = draw_blade(fr, p0, p1, 230, shine=0.2 + 0.7 * clamp01((t - self.t0) / 0.6), shine_w=0.07, seed=6)
        # 护手 + 刀柄（左）
        cv2.ellipse(fr, (60, 690), (26, 110), -6, 0, 360, (0.18, 0.15, 0.1), -1, cv2.LINE_AA)
        cv2.ellipse(fr, (60, 690), (26, 110), -6, 0, 360, tuple(float(v) for v in GOLD * 0.6), 3, cv2.LINE_AA)
        # 刀身刻字
        d = np.array(p1, float) - np.array(p0, float); d /= np.linalg.norm(d); n = np.array([-d[1], d[0]])
        a0 = np.array(p0) + d * 420 - n * 10; a1 = np.array(p0) + d * 1520 - n * 10; a2 = np.array(p0) + d * 1720 - n * 10
        pc = clamp01((tr - (V(CT(19, 3)) - 0.1)) / (V(CT(19, 7)) - V(CT(19, 3)) + 0.2))
        fr = T.carved_on_blade(fr, '就是我的回', [tuple(a0), tuple(a1)], height=86, p=pc, fname='serif_b', finish='steel', taper=(1, 1))
        pa = clamp01((tr - (self.T_ANS - 0.15)) / 0.15)
        if pa > 0:
            fr = T.carved_on_blade(fr, '答', [tuple(a1 + d * 10), tuple(a2)], height=86, p=pa, fname='serif_b', finish='red', taper=(1, 1))
        # 定格 0.3s 后推
        z = 1.0 + 0.04 * eio(clamp01((tr - self.t0 - 0.3) / 0.6))
        k = pulse(tr, self.T_ANS, 0.12) * (tr >= self.T_ANS)
        fr = cam(fr, z * (1 + 0.08 * k), 0, 0)
        if self.T_CRASH <= tr < self.T_CRASH + 1 / 30 + 1e-3: fr = fr * 0.4 + 0.8          # 鼓回归：闪白
        if self.T_ANS <= tr < self.T_ANS + 2 / 30 + 1e-3: fr = fr * 0.6 + GOLD * 0.5
        # 朱墨爆开（不再纯黑：暗朱墨 + 金边，避免整屏死黑）
        if tr >= self.T_ANS + 1 / 30:
            pb = 0.17 * eout((tr - self.T_ANS) / 0.2, 2)     # 墨只从左下角炸开一角，留出刀身「答」（v1 85.9–86.5 近全黑）
            m = K.ink_blot(pb, seed=46, center=(150, 950))
            edge = np.clip(K.blur_ds(m, 6) - m * 0.85, 0, 1)
            fr = over(fr, m, RED * 0.22 + 0.015)
            fr += edge[..., None] * GOLD * 1.2 * (1 - 0.5 * pb)
        return fr, (3 if k > 0.5 else 0)


# =====================================================================================
# S047 86.19–87.56 ELS 墨退，夜雨倾盆；刀斜插泥地；远山雨雾；小款「鬼屠」+朱印
class S047(Shot):
    t0, t1 = 86.192, 87.562
    def __init__(self):
        sk = K.sky(seed=47, cloud=0.9, horizon=0.7, top=(0.07, 0.075, 0.085), bot=(0.24, 0.25, 0.27), stars=0.0).copy()
        for i, (by, amp, tone, al) in enumerate(((620, 200, 0.17, 0.55), (720, 160, 0.10, 0.7), (830, 120, 0.04, 0.9))):
            m = K.mountains(W, H, by, amp, 470 + i, 3 + i)
            sk = over(sk, m * al, (tone, tone * 1.02, tone * 1.08))
            sk = over(sk, K.blur_ds(m, 40) * 0.25, (0.2, 0.21, 0.23))
        x, y = K.grid()
        self.gm = sstep(840, 860, y)
        mud = (0.03 + 0.03 * K.fbm(H, W, 475, 10, 6))[..., None] * np.ones(3, np.float32)
        self.bg = sk * (1 - self.gm[..., None]) + mud * self.gm[..., None]
        T.warm('鬼屠', 'song', 40)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        # 积水倒影
        ref = fr[::-1] * 0.25
        fr = fr + ref * self.gm[..., None] * 0.6
        # 斜插的刀（中景）
        base = np.array([960, 900]); tip_up = base + np.array([-130, -560])
        fr = draw_blade(fr, tuple(base + [8, 40]), tuple(tip_up), 44, shine=0.5 + 0.3 * math.sin(t * 2), shine_w=0.05)
        cv2.line(fr, tuple((tip_up + (tip_up - base) * -0.0).astype(int)), tuple((tip_up + (tip_up - base) * 0.33).astype(int)),
                 (0.05, 0.045, 0.04), 18, cv2.LINE_AA)          # 刀柄
        g0 = tip_up + (tip_up - base) * 0.0
        cv2.ellipse(fr, tuple(g0.astype(int)), (46, 12), -13, 0, 360, (0.12, 0.10, 0.07), -1, cv2.LINE_AA)
        cv2.ellipse(fr, tuple(g0.astype(int)), (46, 12), -13, 0, 360, tuple(float(v) for v in GOLD * 0.45), 2, cv2.LINE_AA)
        # 刀身雨水下流（亮点沿刃滑落）
        for k_ in range(4):
            s = ((t * 0.7 + k_ * 0.27) % 1.0)
            pnt = tip_up + (base - tip_up) * s
            cv2.circle(fr, tuple(pnt.astype(int)), 4, (0.8, 0.85, 0.95), -1, cv2.LINE_AA)
        fr = K.rain(fr, t, 471, n=700, amt=0.55, speed=2300, angle=10, near=0.35, length=(40, 110))
        # 地面溅水
        fr = K.sparks(fr, t, 4720, (960, 880), n=90, life=0.35, speed=(80, 260), dirc=(0, -1), spread=1.0, grav=900,
                      area=(900, 40), color=(0.55, 0.6, 0.68), amt=0.6)
        fr = fr * np.array([0.92, 0.97, 1.08], np.float32)
        e = eio(u)
        fr = cam(fr, 1.0 + 0.04 * e, 0, -40 + 40 * e)
        # 墨退
        if t < self.t0 + 0.3:
            m = K.ink_blot(0.93 + 0.07 * eout((t - self.t0) / 0.2, 2), seed=47, center=(960, 600), reverse=True)
            fr = over(fr, m, RED * 0.22 + 0.015)
        pk = clamp01((t - 86.6) / 0.6)
        if pk > 0:
            fr = T.ink_bleed_in(fr, '鬼屠', [pk, clamp01(pk * 1.2 - 0.1)], style='h', size=34, fname='serif_r', color='white',
                                box=(120, 830, 300, 900), style_kw=dict(shadow=0.6, glow=0.1))
            fr = T.stamp_seal(fr, '屠', 330, 865, 54, clamp01((t - 86.95) / 0.5), style='yin', seed=47)
        return fr, 0


# =====================================================================================
# S048 87.56–89.40 ECU 雨滴落下，镜头追进雨滴，滴中倒映城墙与巨影
class S048(Shot):
    t0, t1 = 87.562, 89.397
    def __init__(self):
        # 倒影小场景：城墙 + 太上皇剪影 + 月
        sc = K.sky(seed=48, cloud=0.6, horizon=0.72, stars=0.3).copy()
        rgb, A = K.moon_sprite(90)
        sc = K.paste_sprite(sc, rgb, A, 960, 260)
        emp = rig.Emperor(48); emp.pose('stand_backlit', 0.3, 0.0)
        sc, _ = emp.draw(sc, 960, 1350, 1250, rim_color=(0.85, 0.88, 0.95), rim=1.0, lift=0.2, alpha=0.9)
        wall, _ = K.brick_wall(2400, 1600, 80, 34, 4, 48)
        q = np.float32([[-100, 600], [2020, 600], [2020, 1080], [-100, 1080]])
        wl = K.warp_quad(wall[:500, :2200], q)
        m = np.zeros((H, W), np.float32); cv2.fillConvexPoly(m, q.astype(np.int32), 1.0)
        for xx in range(-100, 2020, 70):               # 城垛
            cv2.rectangle(m, (xx, 560), (xx + 40, 600), 1.0, -1)
            cv2.rectangle(wl, (xx, 560), (xx + 40, 600), (0.13, 0.135, 0.15), -1)
        self.scene = sc * (1 - m[..., None]) + wl * 0.8
        self.bg = cv2.GaussianBlur(K.sky(seed=480, cloud=0.9, stars=0.0), (0, 0), 6) * 0.8

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        fr = K.rain(fr, t, 481, n=220, amt=0.25, speed=900, angle=4, near=0.5, length=(60, 160))
        fr = cv2.GaussianBlur(fr, (0, 0), 3)
        # 雨滴（慢放下落，镜头追进）
        z = 1.0 + 2.0 * ein(clamp01(u), 2.2)
        cx, cy = 960, 470 + 60 * u
        R = 150
        x, y = K.grid()
        Rz = R * z
        d = np.sqrt((x - cx) ** 2 + ((y - cy) * 0.92) ** 2)
        # 内部：倒置鱼眼的倒影
        rn = np.clip(d / max(Rz, 1), 0, 1)
        fe = rn ** 0.65
        k = 1.0 / (0.9 + 0.6 * (1 - u))
        sx = (960 + (x - cx) / max(Rz, 1) * 960 * fe / np.maximum(rn, 1e-3) * k).astype(np.float32)
        sy = (540 - (y - cy) / max(Rz, 1) * 960 * fe / np.maximum(rn, 1e-3) * k).astype(np.float32)
        inner = cv2.remap(self.scene, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        m = np.clip((Rz - d) / 2, 0, 1)
        rim = np.exp(-((d - Rz) / (2 + 0.01 * Rz)) ** 2) * 0.6
        spec = np.exp(-(((x - cx + Rz * 0.35) ** 2 + (y - cy + Rz * 0.42) ** 2) / (Rz * 0.1 + 2) ** 2)) * 0.9
        fr = fr * (1 - m[..., None]) + inner * m[..., None] * 0.9
        fr += (rim + spec * m)[..., None] * np.array([0.85, 0.9, 1.0], np.float32)
        # 雷声闪
        tl = V(88.90)
        if tl <= t < tl + 1 / 30 + 1e-3: fr = fr * 0.5 + 0.7
        elif t > tl: fr = fr * (1 + 0.6 * pulse(t, tl + 0.04, 0.15))
        return fr, 0


# =====================================================================================
SHOTS = [S027, S028, S029, S030, S031, S032, S033, S034, S035, S036, S037, S038, S039, S040, S041, S042,
         S043Sprite if SPRITE_MODE else S043, S044, S045,
         S046, S047, S048]
# SPRITE_MODE=1：副歌一全部人物镜头换成生图精灵（units/chorus1_sprites.py；2026-11-09 05:25 用户确认）。
# SPRITE_SHOTS 可限定镜号（逗号分隔），默认全部；S031 远景一粒黑点保留代码 rig。
if SPRITE_MODE:
    import chorus1_sprites as _CS
    _SPR = _CS.install(globals())
    _only = os.environ.get('SPRITE_SHOTS')
    _only = set(_only.split(',')) if _only else None
    SHOTS = [(_SPR[S.__name__] if S.__name__ in _SPR and (_only is None or S.__name__ in _only) else S) for S in SHOTS]

# ---------------- v2 剪辑表：切点 = 卡点（鼓/字头）最近帧再提前 1 帧，单位：帧（30fps）
#  S027 58.50 | S028「血」59.35 | S029 drop 重音镲 60.05 | S030 底鼓 60.97 | S031 军鼓 62.34 | S032 小节头 63.72 | S033 小节头 65.54
#  S034 小节头 67.38 | S035 底鼓 69.67 | S036「看」/镲 70.95 | S037「天」72.11 | S038「血」74.01 | S039「骨」75.01
#  S040 小节头 76.54 | S041「我」78.13 | S042 小节头 80.20 | S043 小节头 82.03 | S044 底鼓 82.95 | S045「这」/重音镲 84.08
#  S046「就」84.76（鼓停·憋住）| S047 军鼓 86.16 | S048 小节头 87.53 | 89.50
CUT_F = [1755, 1779, 1800, 1828, 1869, 1910, 1965, 2020, 2089, 2128, 2162, 2219, 2249, 2295, 2343, 2405, 2460, 2487, 2521,
         2542, 2584, 2625, 2685]
for _S, _a, _b in zip(SHOTS, CUT_F, CUT_F[1:]):
    _S.t0, _S.t1 = _a / FPS, _b / FPS
SHOTS[0].t0 = 57.794           # S027 内部起点不变（窗口从 58.5 开始取）

# 切点转场：(名称, pre, post, kw) —— 'hard' = 刻意硬切（切后 2 帧冲击），'whip' 由 VCam 甩镜完成（方向连贯）
CUTS = {
    'S028': ('hard', 0, 0, {}),                                   # 定格憋住 →「血」字头硬切
    'S029': ('flash_white', 0.0, 0.17, {}),                       # drop 重音镲：smash cut + 闪白
    'S030': ('whip', 0, 0, dict(dir=(0, -1), L=420)),             # 握刀 → 举刀指月：上甩
    'S031': ('iris_moon', 0.06, 0.20, dict(center=(900, 330), radius=200)),
    'S032': ('slash_wipe', 0.06, 0.16, dict(angle=78)),
    'S033': ('hard', 0, 0, {}),
    'S034': ('whip', 0, 0, dict(dir=(0, -1), L=460)),             # 墙升起 → 仰拍墙：继续上甩
    'S035': ('whip', 0, 0, dict(dir=(1, 0), L=520)),              # → 疾跑起跳：右甩（人物向右冲）
    'S036': ('hard', 0, 0, {}),
    'S037': ('zoom_through', 0.08, 0.16, dict(center=(960, 540))),
    'S038': ('flash_red', 0.03, 0.12, {}),
    'S039': ('whip', 0, 0, dict(dir=(1, 0), L=400)),              # 刀面 → 战场横移：右甩（与横移同向）
    'S040': ('paper_tear', 0.06, 0.20, {}),
    'S041': ('hard', 0, 0, {}),
    'S042': ('whip', 0, 0, dict(dir=(0, -1), L=460)),             # 背影 → 天：上甩
    'S043': ('hard', 0, 0, {}),
    'S044': ('whip', 0, 0, dict(dir=(0, 1), L=380)),              # 转头 → 手按刀：下甩
    'S045': ('slash_wipe', 0.05, 0.18, dict(circle=True, center=(960, 560), radius=330)),
    'S046': ('hard', 0, 0, {}),
    'S047': ('cut', 0, 0, {}),                                    # 朱墨爆 → 墨退
    'S048': ('zoom_through', 0.08, 0.16, dict(center=(960, 470))),
}

# 基础运镜（叠加在各镜自身运动之上）：缓动 + 速度坡度
M = VC.Move
MOVES = {
    'S027': M('expo_in', z=(1.0, 1.14)),                              # 军鼓滚奏：加速推进
    'S028': M('expo_out', z=(1.08, 1.0)),                             # 慢放：冲进后缓拉
    'S029': M('cubic_io', 'fsf', z=(1.0, 1.06), x=(40, -30)),
    'S030': M('quint_io', y=(70, -20)),                               # 承接上甩：继续升
    'S031': M('expo_out', z=(1.10, 1.0)),
    'S032': M('sine_io', 'fsf', x=(-50, 50)),
    'S033': M('cubic_io', z=(1.0, 1.08), rot=(-1.5, 0.6)),
    'S034': M('expo_out', 'fs', y=(90, -60)),                         # 仰拍上摇，刹住
    'S035': M('quint_io', 'fsf', x=(-70, 70)),                        # 跟拍：甩入→空中憋住→甩出
    'S036': M('quint_io', z=(1.0, 1.10), x=(-20, 30)),
    'S037': M('expo_out', z=(1.14, 1.0), rot=(-6, -3.5)),             # 荷兰角 + 拉开（与其他墙镜头区分）
    'S038': M('expo_in', z=(1.0, 1.08)),
    'S039': M('sine_io', x=(-60, 60)),
    'S040': M('cubic_io', z=(1.05, 1.0), rot=(1.5, -1.0)),
    'S041': M('quint_io', 'fsf', z=(1.0, 1.07), rot=(4.5, 2.0), y=(-30, 10)),   # 低机位斜构图背影
    'S042': M('cubic_io', z=(1.0, 1.08)),
    'S043': M('expo_out', z=(1.0, 1.06), x=(40, -20)),
    'S044': M('expo_in', z=(1.0, 1.12)),                              # 吸气：越推越快
    'S045': M('expo_io', z=(1.06, 1.0), rot=(-3, 3)),
    'S046': M('sine_io', z=(1.0, 1.10)),                              # 憋住：极慢推
    'S047': M('sine_io', z=(1.05, 1.0), y=(-30, 20)),
    'S048': M('expo_in', z=(1.0, 1.15)),
}
# ---------------- v3 主运镜（2.5D）：每镜一条有设计的主运镜；'beat' = 小节头/重音字上加速、镜尾（乐句末）减速刹住
#  方向衔接：S027→S029 一路向右（推轨→环绕）→ S029 末上升接上甩 → S030 摇臂升 → S031/S032 继续向右 → S033 摇臂升
#  → 上甩 → S034 仰摇+变焦推拉 → 右甩 → S035 横移跟拍向右 → S036 沿裂缝右下 → S037 摇臂降 → S038 继续下摇 → 右甩
#  → S039 横移向右 → S040 环绕向右 → S041 焦点转移+升 → 上甩 → S042 推 → S043 随转头向左环绕 → 下甩 → S044 推+沿刀身右移
#  → S045 急速环绕 → S046 变焦推拉（鼓停憋住）→ S047 焦点转移+升 → S048 推进雨滴
M3 = V3.Move3
MOVES3 = {
    'S027': M3('expo_in', None, z=(1.0, 1.16), x=(-30, 50), rot=(0, -3), note='推轨 dolly in 沿刃向右 + 滚转，滚奏加速'),
    'S028': M3('expo_out', None, z=(1.12, 1.0), x=(50, 90), rot=(-3, 0), yaw=(4, 0), note='拉出 dolly out + 滚转回正，继续向右漂'),
    'S029': M3('sine_io', 'beat', z=(1.06, 1.0), yaw=(-9, 7), x=(-40, 40), y=(0, -30), note='环绕 orbit 绕握刀手向右，末段上抬接上甩'),
    'S030': M3('sine_io', 'beat', z=(1.0, 1.07), y=(60, -50), pitch=(-6, 2), note='摇臂升 crane up（低机位仰→平视）'),
    'S031': M3('sine_io', 'beat', z=(1.02, 1.0), x=(-50, 50), yaw=(-7, 7), rot=(2, -1), note='环绕 orbit 向右（巨影透视转动）'),
    'S032': M3('sine_io', 'beat', z=(1.0, 1.08), x=(-40, 40), pitch=(9, 0), note='俯摇压下 tilt + 推，继续向右；斩落在小节头加速'),
    'S033': M3('sine_io', 'beat', z=(1.0, 1.05), y=(110, -50), pitch=(-7, 1), rot=(-1.5, 0.5), note='摇臂升 crane up 随墙升起（前景碎砖视差）'),
    'S034': M3('sine_io', 'beat', z=(1.0, 1.10), y=(40, -40), rot=(0, -7), vtg=(0.0, 0.30), note='变焦推拉 dolly zoom ① + 仰摇 + 荷兰角滚转'),
    'S035': M3('sine_io', 'beat', x=(-90, 90), yaw=(-4, 4), note='横移跟拍 truck 向右跟人物起跳（前景碎砖视差）'),
    'S036': M3('sine_io', 'beat', z=(1.03, 1.10), yaw=(12, 4), pitch=(-4, 2), x=(-30, 30), note='斜角环绕 orbit 收正 + 推（侧光斜看字砖）'),
    'S037': M3('sine_io', 'beat', z=(1.12, 1.0), y=(-50, 40), pitch=(5, -2), rot=(-6, -2), note='摇臂降 crane down + 拉开 + 荷兰角回正（前景芦苇升入）'),
    'S038': M3('sine_io', 'beat', z=(1.0, 1.06), y=(-40, 40), rot=(2, -1), note='下摇 tilt down 跟血沿刃流'),
    'S039': M3('sine_io', 'beat', x=(-100, 100), yaw=(-3, 3), note='横移跟拍 truck 向右（前景芦苇 2.8x 视差）'),
    'S040': M3('sine_io', 'beat', z=(1.06, 1.0), pitch=(9, 0), yaw=(-6, 4), note='摇臂降 + 环绕压到纸面 crane/orbit'),
    'S041': M3('sine_io', 'beat', keys=[(0.0, dict(focus=0.0, y=50, pitch=-4, rot=4.5, z=1.0)),
                                       (0.38, dict(focus=1.0, y=25, pitch=-2.5, rot=3.6, z=1.02)),
                                       (1.0, dict(focus=1.0, y=-30, pitch=1, rot=2.0, z=1.06))],
               note='焦点转移 rack focus ①（前景墙角→背影）+ 摇臂升 + 荷兰角'),
    'S042': M3('sine_io', 'beat', z=(1.0, 1.16), y=(20, -10), rot=(0, 2), note='推轨 dolly in，重拍上加速'),
    'S043': M3('sine_io', 'beat', z=(1.0, 1.05), yaw=(9, -6), x=(40, -30), note='环绕 orbit 向左，随转头（match on action）'),
    'S044': M3('sine_io', 'beat', z=(1.0, 1.13), x=(-50, 40), pitch=(3, 0), note='推 + 沿刀身横移（吸气）'),
    'S045': M3('sine_io', 'beat', z=(1.06, 1.0), yaw=(-10, 8), rot=(-3, 3), x=(-30, 30), note='急速环绕 orbit + 荷兰角翻转（随旋身斩）'),
    'S046': M3('sine_io', None, z=(1.0, 1.12), vtg=(0.0, 0.32), note='变焦推拉 dolly zoom ②（鼓停憋住，背景被拉远）'),
    'S047': M3('sine_io', 'beat', keys=[(0.0, dict(focus=0.0, y=60, pitch=-5, z=1.05)),
                                       (0.40, dict(focus=1.0, y=30, pitch=-2, z=1.03)),
                                       (1.0, dict(focus=1.0, y=-40, pitch=3, z=1.0))],
               note='焦点转移 rack focus ②（前景芦苇→插地的刀）+ 摇臂升'),
    'S048': M3('expo_in', None, z=(1.0, 1.18), rot=(0, 3), note='推进雨滴 dolly in + 慢滚转'),
}
# 前景遮挡物（前中后景视差）：(kind, side, depth, rim 颜色)
OCC = {'S033': ('rubble', 'right', 2.8, (0.7, 0.75, 0.9)), 'S035': ('rubble', 'both', 3.0, (1.0, 0.7, 0.35)),
       'S036': ('rubble', 'left', 2.2, (1.0, 0.76, 0.4)), 'S037': ('reeds', 'both', 2.4, (1.0, 0.76, 0.4)),
       'S039': ('reeds', 'both', 2.8, (0.75, 0.8, 0.9)), 'S041': ('post', 'left', 2.0, (1.0, 0.76, 0.4)),
       'S047': ('reeds', 'both', 2.6, (0.7, 0.75, 0.85))}
RACK_SIGMA = 8.0                                  # 焦点转移：场景最虚 σ
RACK_PROTECT = {'S041': (1500, 120, 1920, 960)}   # 歌词区不参与虚焦（字是屏幕层）
GAIN = {'S028': 0.6, 'S034': 0.8, 'S038': 0.8, 'S043': 0.7, 'S046': 0.5, 'S047': 0.6}

# 时间重映射：定格 / 慢放（憋住乐句尾）
def _hold(t0, k):
    return lambda t: t if t < t0 else t0 + (t - t0) * k
def _hold2(t0, t1, k):
    return lambda t: t if t < t0 else (t0 + (t - t0) * k if t < t1 else t0 + (t1 - t0) * k + (t - t1))
REMAP = {
    'S046': _hold2(84.80, V(85.69), 0.15),        # 鼓停：刀身定格慢放（刻字仍按真实字头落点）
    'S027': _hold(V(59.13), 0.06),     # 军鼓滚奏最后一击后定格，鼓停的静默里憋住，等「血」
    'S041': _hold(V(79.61) + 0.12, 0.3),   # 「扛」后慢放 0.3x 憋到小节头
}

# 段落能量包络（强弱交替 / 呼吸）：(时间, 能量)
ENERGY = [(58.5, 0.8), (59.10, 0.9), (59.2, 0.25), (59.95, 0.3), (60.0, 1.1), (65.4, 1.0), (65.5, 0.7), (69.55, 0.75),
          (69.65, 1.15), (73.9, 1.2), (74.0, 0.8), (76.45, 0.8), (76.5, 1.0), (80.1, 1.0), (80.15, 0.65), (83.9, 0.75),
          (84.0, 1.3), (84.75, 1.2), (84.8, 0.0), (85.6, 0.0), (85.65, 1.4), (86.05, 1.2), (86.1, 0.45), (87.45, 0.5),
          (87.5, 1.2), (89.5, 1.3)]
_ET = np.array([e[0] for e in ENERGY]); _EV = np.array([e[1] for e in ENERGY])
def energy(t): return float(np.interp(t, _ET, _EV))

# 插入闪切（2–4 帧）：(起始帧, 帧数, 类型, 参数) —— 鼓点加花处
#  'neg' 反相帧 / 'white' 闪白 / 'red' 朱红剪影帧 / ('shot', 镜头id, 内部时间) 闪回其他镜头最强帧
INSERTS = [
    (round(58.79 * FPS) - 1, 2, 'neg', None),           # 滚奏加花
    (round(59.02 * FPS) - 1, 1, 'white', None),
    (round(73.21 * FPS) - 1, 3, 'shot', ('S035', 70.05)),     # 「天亮」后的鼓加花：闪回劈墙
    (round(73.56 * FPS) - 1, 2, 'neg', None),
    (round(73.68 * FPS) - 1, 2, 'shot', ('S032', 65.20)),     # 正邪印劈开
    (round(73.91 * FPS) - 1, 1, 'white', None),
    (round(81.34 * FPS) - 1, 2, 'red', None),                 # 「判」前军鼓双击
    (round(87.88 * FPS) - 1, 3, 'shot', ('S030', 62.05)),     # 尾段过门：闪回蒙太奇冲进主歌二
    (round(88.22 * FPS) - 1, 3, 'shot', ('S035', 70.08)),
    (round(88.44 * FPS) - 1, 2, 'neg', None),
    (round(88.57 * FPS) - 1, 3, 'shot', ('S045', 84.62)),
    (round(89.14 * FPS) - 1, 3, 'shot', ('S040', 78.0)),
    (round(89.37 * FPS) - 1, 3, 'shot', ('S029', 60.62)),
]
_INS = {}
for _f0, _n, _k, _a in INSERTS:
    for _i in range(_n): _INS[_f0 + _i] = (_k, _a, _i, _n)

FG = {'S027': ('ember', 0.6), 'S028': ('ember', 0.25), 'S029': ('ember', 0.6), 'S030': ('ash', 0.35), 'S031': ('ash', 0.35),
      'S032': ('ember', 0.4), 'S033': ('ash', 0.5), 'S034': ('ash', 0.4), 'S035': ('ember', 0.6), 'S036': ('gold', 0.5),
      'S037': ('gold', 0.45), 'S039': ('rain', 0.35), 'S041': ('rain', 0.4), 'S042': ('ash', 0.3), 'S043': ('ember', 0.4),
      'S044': ('ash', 0.3), 'S045': ('rain', 0.45), 'S047': ('rain', 0.5), 'S048': ('rain', 0.4)}
# 曝光（v1 整体偏暗）：全局 1.2，个别镜头再补
EXPO_ALL = 1.2
EXPO = {'S031': 1.15, 'S039': 1.1, 'S043': 1.25, 'S044': 1.3, 'S047': 1.15, 'S048': 1.3, 'S041': 1.1, 'S042': 1.15}


# ---------------- v3 统一字幕（units/lyric3.py）：同屏一句；版位 bottom=底部三分之一横排 / right=右侧竖排
SL = LY.Sentence
SENTENCES = [
    SL('血未冷', 12, [0, 1, 2], 'right', 60.10, red='血'),
    SL('刀不放', 12, [3, 4, 5], 'right', 61.98, red='刀'),
    SL('谁人来定正邪一方', 13, list(range(8)), 'right', 65.12, red='邪'),
    SL('若规则是铁壁铜墙', 14, list(range(8)), 'right', 69.25, red='墙'),
    SL('那就劈开它', 15, [0, 1, 2, 3, 4], 'bottom', 70.62, red='劈', skip=True),   # S035 被斩开（互动版，同字体同版位）
    SL('看个天亮', 15, [5, 6, 7, 8], 'right', 73.55, gold='天亮'),
    SL('血未冷', 16, [0, 1, 2], 'bottom', 74.62, red='血'),
    SL('骨未凉', 16, [3, 4, 5], 'right', 76.12, red='骨'),
    SL('是非对错我自己扛', 17, list(range(8)), 'right', 79.85, red='扛'),
    SL('天不判', 18, [0, 1, 2], 'bottom', 81.68, red='判'),
    SL('我来量', 18, [3, 4, 5], 'bottom', 83.68, red='量'),
    SL('这一刀', 19, [0, 1, 2], 'right', 84.44, red='刀'),
    SL('就是我的回答', 19, [3, 4, 5, 6, 7, 8], 'bottom', 86.0, red='答', skip=True),  # S046 刻在刀上（互动版）
]


class _Lazy:
    def __init__(self, cls): self.cls = cls; self.t0 = cls.t0; self.t1 = cls.t1; self.obj = None; self.id = cls.__name__
    def render(self, t):
        if self.obj is None: self.obj = self.cls()
        f = REMAP.get(self.id)
        REAL_T[0] = t
        try:
            return self.obj.render(f(t) if f else t)
        finally:
            REAL_T[0] = None


def build_cam(v=3):
    if v == 2:
        cam_ = VC.VCam(ROOT + '/crew/hitmap_c1.json', energy=energy); MV = MOVES
    else:
        cam_ = V3.VCam3(ROOT + '/crew/hitmap_c1.json', energy=energy); MV = MOVES3
    for S in SHOTS:
        cam_.shot(max(S.t0, 58.5), S.t1, MV.get(S.__name__), GAIN.get(S.__name__, 1.0))
        c = CUTS.get(S.__name__)
        if c and c[0] == 'whip':
            cam_.whip(S.t0, c[3]['dir'], c[3].get('L', 400))
        else:
            cam_.cut(S.t0)
    cam_.hold(V(59.13), 59.267)
    cam_.hold(84.80, V(85.69))
    return cam_


class Chorus1:
    T0, T1 = 58.5, 89.5

    def __init__(self):
        self.shots = [_Lazy(S) for S in SHOTS]       # 镜头按需构建（分段渲染时只初始化用到的镜头）
        self.ids = [S.__name__ for S in SHOTS]
        self.byid = dict(zip(self.ids, self.shots))
        self.cam = build_cam(int(os.environ.get('C1_CAM', '3')))
        self.fg = VC.FGLayer(11, n=24)
        self.lyr = LY.LyricLayer(SENTENCES, lambda li, k: V(CT(li, k)))
        self.occ = {k: V3.FGOcc(a, b, d, seed=int(k[1:]), rim=r) for k, (a, b, d, r) in OCC.items()}

    def idx(self, t):
        for i, s in enumerate(self.shots):
            if t < s.t1 - 1e-6: return i
        return len(self.shots) - 1

    def raw(self, t):
        i = self.idx(t)
        s = self.shots[i]
        for j in (i, i + 1):
            if j <= 0 or j >= len(self.shots): continue
            b = self.shots[j]; name, pre, post, kw = CUTS.get(self.ids[j], ('hard', 0, 0, {}))
            c = b.t0
            if name in ('hard', 'cut', 'whip') or not (c - pre - 1e-6 <= t < c + post - 1e-6): continue
            a = self.shots[j - 1]
            B, ca2 = b.render(t)
            A, ca1 = a.render(t) if pre > 0 or t < c else (B, 0)
            p = (t - (c - pre)) / (pre + post)
            if pre == 0:            # 切点即冲击：转场只做「切后」半程
                p = 0.5 + 0.5 * p
            return TR.transition(name, np.clip(A, 0, 4).astype(np.float32), np.clip(B, 0, 4).astype(np.float32), p, **kw), max(ca1, ca2)
        fr, ca = s.render(t)
        name = CUTS.get(self.ids[i], ('hard',))[0]
        if name == 'hard' and i > 0:
            k = int((t - s.t0) * 30 + 1e-6)
            if k < 2:
                a = 1.0 if k == 0 else 0.45
                fr = cam(fr, 1 + 0.025 * a) * (1 + 0.15 * a) + 0.04 * a   # v3：切点冲击推近减半（亮度冲击保留=卡点）
                ca = max(ca, 3 if k == 0 else 1)
        return fr, ca

    def insert(self, t, ins):
        kind, arg, i, n = ins
        if kind == 'shot':
            sid, ti = arg
            fr, ca = self.byid[sid].render(ti + i / FPS * 0.5)
            fr = cam(fr, 1.10 - 0.03 * i) * 1.25
            return fr, 4
        fr, ca = self.raw(t)
        if kind == 'neg':
            l = fr.mean(-1, keepdims=True)
            return np.clip(1.0 - l * 1.4, 0, 1) * np.array([1.0, 0.98, 0.95], np.float32), 5
        if kind == 'white':
            return fr * 0.3 + 0.95, 2
        if kind == 'red':
            l = fr.mean(-1, keepdims=True)
            return RED * 1.1 * (1 - np.clip(l * 2.5, 0, 1)) + 0.02, 4
        return fr, ca

    def frame(self, t, dt=1 / 30):
        """返回已收尾的成片帧（调色/辉光/色差/暗角/颗粒/黑边均已做；色差已烘焙，故返回 ca=0，外部勿再 finish）。"""
        f = int(round(t * FPS))
        ins = _INS.get(f)
        if ins: fr, ca = self.insert(t, ins)
        else: fr, ca = self.raw(t)
        sid = self.ids[self.idx(t)]
        fr, st = self.cam.apply(np.clip(fr, 0, 4).astype(np.float32), t)
        foc = st.get('focus', 1.0)
        if foc < 0.999 and not ins:                      # 焦点转移：场景虚 → 实
            sig = RACK_SIGMA * (1 - foc) ** 1.2
            b = V3.defocus(fr, sig)
            pb = RACK_PROTECT.get(sid)
            if pb:
                m = np.ones((H, W), np.float32); m[:, pb[0]:] = 0
                m = cv2.GaussianBlur(m, (0, 0), 40)[..., None]
                fr = b * m + fr * (1 - m)
            else:
                fr = b
        oc = self.occ.get(sid)
        if oc is not None and not ins:
            fr = oc.draw(fr, st, t)
        kind, amt = FG.get(sid, (None, 0))
        if kind and not ins:
            fr = self.fg.draw(fr, t, st, kind, amt)
        fr = fr * (EXPO_ALL * EXPO.get(sid, 1.0))
        fr = fr + 0.012 * (1 - np.clip(fr, 0, 1))        # 抬一点黑位（避免死黑）
        if os.environ.get('C1_LYR', '3') == '3':
            fr = self.lyr.draw(fr, t)                       # 统一字幕层（屏幕层，不随镜头）
        ca = max(ca, int(round(4 * min(1.0, st['punch']))))
        return GU.apply(finish(fr, t, ca=ca, vig=0.42, red_keep=1.0 if SPRITE_MODE else 0.0), t, 'chorus1'), 0   # 统一 grade 层


X = Chorus1
