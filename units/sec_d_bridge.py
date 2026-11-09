"""units/sec_d_bridge.py — [D组] Bridge「风暴之眼」（帧 4839–5797，161.31–193.23s）第四轮重做。
设计说明见 crew/round4/D_storyboard.md。30 镜，平均 1.06s；每镜一个类（render(t) -> (float 帧, paper_mode)），
切点转场由 CUTS 表驱动；收尾 d_kit.d_finish（白纸段保留暖白）。
叙事：朱墨入水 → 白纸审判庭（宋体字 = 权力的话，从天而降、堆成雪、立成碑、盖成印）→ 剪纸里的被牺牲者被火烧穿，
白纸世界烧出黑洞 → 余烬中睁眼、拔刀（字体切回手写 = 他的话）→ 撞碎字墙 →「天」在风暴之眼里 → 刀光在天上刻「判」→
子弹时间 → 雨滴炸成金 →「答」在裂开的云里金色爆开，白金出画接副歌终。"""
import sys, math, os
ROOT = '/workspace/work/mv'
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, cv2
from PIL import Image
import c1kit as K
import typo as T
import trans as TR
import d_kit as D
import d_r5 as R5
import d_r7 as R7
from d_kit import V, cp, seal_p, INK, CINNABAR, GOLD, RED, W, H, BAR

READY = True
F0, F1 = 4839, 5797
T0, T1 = F0 / 30, F1 / 30
O = {i: D.onsets(i) for i in range(40, 48)}
WHITE = (0.97, 0.94, 0.88)
EMBER = np.array([1.0, 0.5, 0.16], np.float32)
COLD = (0.62, 0.74, 1.0)
GOLDR = (1.0, 0.78, 0.45)


def eo(x, k=3): return K.eout(x, k)
def ei(x, k=3): return K.ein(x, k)
def cl(x): return K.clamp01(x)
def lerp(a, b, u): return a + (b - a) * u


def impact(t, t_hit, decay=0.12):
    return 0.0 if t < t_hit else math.exp(-(t - t_hit) / decay)


def shake_cam(fr, t, hits, amp=10, z=1.0, ox=0.0, oy=0.0, rot=0.0, center=None):
    a = sum(amp * impact(t, h) for h in hits)
    dx, dy, dr = K.shake(t, a, 14, int(t * 3) % 7)
    return K.cam(fr, z * (1 + 0.012 * a / max(1, amp)), ox + dx, oy + dy, rot + dr, center)


def vcol(fr, text, x, y0, size, onsets_, t, color='ink', emph=None, fname='serif_sb', adv=1.2, ink=True, horiz=False, dur=0.2):
    prog = [cp(t, o, dur) for o in onsets_]
    L = D.text_layer(D.column(text, x, y0, size, prog, adv, color, emph, fname, drop=size * 0.4, horiz=horiz), fname=fname)
    return D.ink_text(fr, L, bleed=0.18) if ink else D.light_text(fr, L)


class Shot:
    t0 = t1 = 0.0
    paper = 0.0
    def u(self, t): return cl((t - self.t0) / (self.t1 - self.t0))


# ===================================================================================== 第一幕：白纸审判庭
class S01_Drop(Shot):
    """ECU 朱墨滴入黑水：两滴（落拍 161.77 / 162.21），涟漪 + 水下朱墨云翻涌。黑场接 C 组。"""
    t0, t1 = 161.31, 162.58
    def __init__(self):
        self.c = np.array([960., 560.])
        x, y = K.grid(); self.x, self.y = x, y
        self.base = (0.012 + 0.03 * cv2.resize(K.fbm(H // 8, W // 8, 93, base=3, octaves=4), (W, H)))[..., None] * np.array([0.8, 0.9, 1.1], np.float32)
        self.tex = D._tile(91)
        self.hits = [(V(161.77), (960, 560), 1.0), (V(162.21), (1010, 585), 0.6)]

    def render(self, t):
        u = self.u(t)
        x, y = self.x, self.y
        fr = self.base.copy()
        h = np.zeros((H, W), np.float32)
        for th, c, s in self.hits:
            age = t - th
            if age <= 0: continue
            r = np.sqrt((x - c[0]) ** 2 + ((y - c[1]) * 2.4) ** 2)
            for k in range(3):
                R = (160 + 120 * k) * age ** 0.8 * 2.2
                h += s * np.sin((r - R) / 9.0) * np.exp(-((r - R) / (28 + 30 * age)) ** 2) * math.exp(-age * 1.6) * (1 - 0.25 * k)
        # [r4] 段首不再 0.6s 全黑：第一滴朱墨从画顶坠落（拉长的朱红水珠 + 高光），水面映出越来越近的红点、冷月光掠过水面
        th1 = self.hits[0][0]
        if t < th1:
            q = cl((t - self.t0) / (th1 - self.t0))
            dy = lerp(250, 560, ei(q, 2))
            dm = np.exp(-(((x - 960) / 7) ** 2 + ((y - dy) / (10 + 26 * q)) ** 2))
            fr = fr * (1 - dm[..., None]) + dm[..., None] * np.array([0.85, 0.08, 0.05], np.float32) + \
                 (np.exp(-(((x - 957) / 2.5) ** 2 + ((y - dy + 6) / 4) ** 2)) * 0.9)[..., None]
            rf = np.exp(-(((x - 960) / (14 + 30 * q)) ** 2 + ((y - 566) / (4 + 6 * q)) ** 2)) * q ** 2
            fr = fr + rf[..., None] * np.array([0.6, 0.06, 0.04], np.float32)
        sheen = np.exp(-((y - 600 - 40 * math.sin(t * 0.7)) / 90) ** 2) * (0.5 + 0.5 * np.sin(x / 40 + t * 2.0) * np.sin(x / 13 - t)) * 0.035
        fr = fr + sheen[..., None] * np.array([0.7, 0.8, 1.0], np.float32)
        gy, gx = np.gradient(h)
        spec = np.clip(-gx * 0.6 - gy * 1.4, 0, None) ** 1.5 * 6
        fr = fr + spec[..., None] * np.array([0.8, 0.85, 0.95], np.float32) * 0.7
        # [r5] 涟漪冷轮廓光（背光侧的环边一线亮）+ 斜上方一束月光体积 + 水面贴地雾
        rimr = np.clip(gx * 0.9 + gy * 0.5, 0, None) ** 1.3 * 9
        fr = fr + rimr[..., None] * np.array(COLD, np.float32) * 0.55
        dl = np.abs((x - 620) * 0.86 - (y - 120) * 0.5) / 1.0
        shaft = np.exp(-(dl / (110 + 0.25 * y)) ** 2) * np.clip((y - BAR) / 500, 0, 1) * (0.5 + 0.5 * np.clip(1 - (y - 600) / 500, 0, 1))
        fr = fr + (shaft * (0.13 + 0.03 * math.sin(t * 2.3)))[..., None] * np.array([0.7, 0.8, 1.0], np.float32)
        fr = K.fog(fr, t, 911, amt=0.55, speed=(45, 0), y0=0.40, y1=0.80, color=(0.15, 0.16, 0.20))
        # 水下朱墨云
        for th, c, s in self.hits:
            age = t - th
            if age <= 0: continue
            Rr = (40 + 330 * eo(age / 1.2, 2)) * s
            n = cv2.remap(self.tex, ((x / 3 + t * 20) % 512).astype(np.float32), ((y / 3 * 1.0 + age * 40) % 512).astype(np.float32), cv2.INTER_LINEAR)
            d = np.sqrt((x - c[0]) ** 2 + ((y - c[1]) * 2.0) ** 2) / max(1, Rr)
            m = np.clip((1.15 - d - (n - 0.5) * 1.2) * 2.2, 0, 1) * min(1, age * 6) * (0.8 + 0.2 * s)
            fr = fr * (1 - m[..., None] * 0.6) + m[..., None] * np.array([0.42, 0.03, 0.02], np.float32) * (0.6 + 0.6 * n[..., None])
        # 下落的墨滴（落前）
        for th, c, s in self.hits:
            if th - 0.28 <= t < th:
                q = (t - (th - 0.28)) / 0.28
                yy = 120 + (c[1] - 120) * q ** 1.8
                L = np.zeros((H, W), np.float32)
                cv2.ellipse(L, (int(c[0]), int(yy)), (int(9 * s + 4), int(16 * s + 6)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
                L = cv2.GaussianBlur(L, (0, 0), 1.2)
                fr = fr * (1 - L[..., None]) + L[..., None] * np.array([0.65, 0.05, 0.03], np.float32)
                hl = np.zeros((H, W), np.float32); cv2.circle(hl, (int(c[0] - 3), int(yy - 6)), 3, 1.0, -1, cv2.LINE_AA)
                fr += cv2.GaussianBlur(hl, (0, 0), 1.5)[..., None] * 1.5
        # 冠状水花
        for th, c, s in self.hits:
            age = t - th
            if 0 <= age < 0.35:
                fr = K.sparks(fr, t, 300 + int(s * 10), c, n=int(40 * s), life=0.35, speed=(200, 600), dirc=(0, -1), spread=0.9,
                              grav=2200, burst=True, t0=th, color=(0.75, 0.15, 0.1), amt=0.9)
        # 第三棒 P3：第二滴之后，朱墨云里浮出第一个字「什」（水波扭动），提前进入「什么叫」
        q = cl((t - 162.08) / 0.4)
        if q > 0:
            L = D.text_layer([('什', 960, 545, 300, 0.8 * q, 1.08 - 0.08 * eo(q), 0.0, (0.85, 0.12, 0.08))], fname='serif_black')
            wob = (np.sin(y / 23.0 + t * 9) * 5 * (1 - 0.6 * q)).astype(np.float32)
            L.A = cv2.remap(L.A, (x + wob).astype(np.float32), y.astype(np.float32), cv2.INTER_LINEAR)
            L.C = cv2.remap(L.C, (x + wob).astype(np.float32), y.astype(np.float32), cv2.INTER_LINEAR); L.bb = [0, 0, W, H]
            fr = T.compose(fr, L, shadow=0.0, glow=0.5 * q, glow_color=(0.9, 0.15, 0.08), glow_sigma=24)
        fr = fr * min(1, (t - self.t0) / 0.18 + 0.0)
        return K.cam(fr, 1.0 + 0.05 * eo(u, 2), center=(960, 560)), 0.0


class S02_Steles(Shot):
    """ELS 白纸虚空：小小的水墨鬼屠背影前行；宋体巨字「什」「么」「叫」从天砸下立成碑，墨点飞溅"""
    t0, t1 = 162.58, 164.05
    paper = 1.0
    CH = [('什', 520, 560, 430, O[40][0]), ('么', 1420, 520, 400, O[40][1]), ('叫', 960, 330, 300, O[40][2])]
    def __init__(self):
        self.sp = D.spr('walk_back')
        for c in self.CH: T.glyph(c[0], 'serif_black', c[3], False)

    def render(self, t):
        u = self.u(t)
        fr = D.paper(11).copy()
        fr = D.wash(fr, 0.10, 0.0, 0.5, seed=21)
        fr = D.fall_chars(fr, t, '什么叫大局牺牲忍让规矩正义', 31, density=7, sizes=(18, 46), alpha=0.55, near_blur=3)
        hits = []
        for ch, x, y, s, on in self.CH:
            th = V(on)
            if t < th - 0.24: continue
            q = cl((t - (th - 0.24)) / 0.24)
            hits.append(th)
            yy = lerp(y - 900, y, ei(q, 2))
            sq = impact(t, th, 0.07)
            # 落地阴影
            if q > 0.2:
                sh = D.text_layer([(ch, x + 30, y + s * 0.46, s, 0.35 * q, 1.0, 0.0)], fname='serif_black')
                sh.A = cv2.GaussianBlur(cv2.resize(cv2.resize(sh.A, (W, H // 6)), (W, H)), (0, 0), 9) * 0.0 + cv2.GaussianBlur(sh.A, (0, 0), 18) * 0.5
                fr = fr * (1 - sh.A[..., None] * 0.4)
            L = D.text_layer([(ch, x, yy, s, min(1, q * 2), 1.0 + 0.0, 0.0)], fname='serif_black')
            if q < 1: L.A = cv2.GaussianBlur(L.A, (0, 0), 0.1 + 6 * (1 - q))
            if sq > 0.01:
                L = D.text_layer([(ch, x, yy + s * 0.05 * sq, s, 1.0, 1.0, 0.0)], fname='serif_black')
            fr = D.ink_text(fr, L, bleed=0.3, sig=7)
            fr = D.ink_spray(fr, t, th, (x, y + s * 0.42), n=46, seed=ord(ch), power=420)
        # 鬼屠：远离镜头慢走
        z = 300 - 18 * u
        fr, _ = D.ink_figure(fr, self.sp, t, D.feet(self.sp), (960, 830 - 14 * u + 3 * math.sin(t * 7.3)), D.fit_scale(self.sp, z), shadow=0.55)
        fr = shake_cam(fr, t, hits, 7, z=1.0 + 0.05 * eo(u, 2), oy=-30 * (1 - eo(u, 2)))
        return fr, 1.0


class S03_TypeSlam(Shot):
    """仰拍地平：「大」「局」两枚宋体铅字块（带厚度）砸进纸面，墨尘翻起"""
    t0, t1 = 164.05, 164.98
    paper = 1.0
    CH = [('大', 700, 560, 520, O[40][3]), ('局', 1290, 620, 540, O[40][4])]

    def render(self, t):
        u = self.u(t)
        fr = D.paper(12).copy()
        g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        fr = fr * (1 - 0.10 * K.sstep(0.55, 0.62, g) * (1 - K.sstep(0.62, 0.9, g)))  # 地平线淡墨
        fr = D.wash(fr, 0.16, 0.6, 1.0, seed=33)
        fr = D.fall_chars(fr, t, '什么叫大局', 32, density=5, sizes=(16, 40), alpha=0.5, near_blur=2)
        # [r5] 中景：地平线上黑压压一片人群剪影（远淡近浓），「大」「局」压在他们头上；每次落字人群往下一缩
        cr = R5.crowd_mask(303, n=320, y_far=640, y_near=960, s_far=18, s_near=62)
        sq = sum(impact(t, V(c[4]), 0.1) for c in self.CH)
        if sq > 0.01:
            M = np.float32([[1, 0, 0], [0, 1 - 0.03 * sq, 930 * 0.03 * sq]]); cr = cv2.warpAffine(cr, M, (W, H))
        fr = fr * (1 - cr[..., None] * 0.62) + INK * cr[..., None] * 0.62 * (fr / 0.93)
        hits = []
        for ch, x, y, s, on in self.CH:
            th = V(on)
            ws = min(th - 0.2, self.t0 - 0.01) if ch == '大' else th - 0.2   # [r4] 切入那一帧「大」已在画内下坠（去掉 5 帧空纸）
            if t < ws: continue
            q = cl((t - ws) / (th - ws)); hits.append(th)
            yy = lerp(y - 560, y, ei(q, 2))
            sc = 1.6 - 0.6 * ei(q, 2)
            # 厚度（铅字块侧面）
            depth = [(ch, x + 2.2 * k, yy - 1.4 * k, s, 1.0, sc, 0.0, (0.28 + 0.01 * k,) * 3) for k in range(16, 0, -1)]
            Ld = D.text_layer(depth, fname='serif_black')
            # 地面投影
            if q > 0.0:
                Ls = D.text_layer([(ch, x + 60, y + s * 0.5, s, 1.0, 1.0)], fname='serif_black')
                A = Ls.A; M = np.float32([[1, -1.2, 0], [0, 0.22, 0]]); M[1, 2] = (y + s * 0.5) * (1 - 0.22); M[0, 2] = 1.2 * (y + s * 0.5)
                A = cv2.GaussianBlur(cv2.warpAffine(A, M, (W, H)), (0, 0), 10) * 0.45 * q
                fr = fr * (1 - A[..., None])
            fr = D.ink_text(fr, Ld, bleed=0.0)
            L = D.text_layer([(ch, x, yy, s, 1.0, sc, 0.0)], fname='serif_black')
            fr = D.ink_text(fr, L, bleed=0.25)
            fr = D.ink_spray(fr, t, th, (x, y + s * 0.45), n=60, seed=ord(ch) + 3, power=700)
            # 墨尘
            a = cl((t - th) / 0.5) * (1 - cl((t - th - 0.3) / 0.6))
            if a > 0:
                fr = K.fog(fr, t, 40 + ord(ch) % 9, amt=0.55 * a, speed=(80, -30), y0=(y + s * 0.2) / H, y1=(y + s * 0.6) / H, color=(0.2, 0.19, 0.18))
        fr = shake_cam(fr, t, hits, 12, z=1.02 + 0.04 * u, oy=10 * u)
        return fr, 1.0


class S04_Snow(Shot):
    """贴地 MS：字落如雪，地上堆起宋体字堆；鬼屠的靴子和拖地的刀尖走进字堆；朱红「牺牲」落在镜头前"""
    t0, t1 = 164.98, 165.88
    paper = 1.0
    def __init__(self):
        self.sp = D.spr('walk_back')
        r = np.random.default_rng(44)
        pool = '什么叫大局牺牲忍让理所应当规矩正义'
        items = []
        for i in range(520):
            yy = r.uniform(0, 1) ** 0.6
            y = 760 + yy * 220; s = 12 + yy * 58
            items.append((pool[i % len(pool)], r.uniform(-40, W + 40), y, s, 0.85, 1.0, r.uniform(-60, 60)))
        items.sort(key=lambda c: c[2])
        self.pile = D.text_layer(items, fname='serif_m')
        near = [c for c in items if c[2] > 930]
        self.near = D.text_layer(near, fname='serif_m'); self.near.A = cv2.GaussianBlur(self.near.A, (0, 0), 4)

    def render(self, t):
        u = self.u(t)
        fr = D.paper(13).copy()
        fr = D.wash(fr, 0.08, 0.0, 0.4, seed=8)
        fr = D.fall_chars(fr, t, '什么叫大局牺牲忍让', 41, density=9, sizes=(20, 60), alpha=0.6, near_blur=5)
        fr = D.ink_text(fr, self.pile, bleed=0.08, dens=0.75)
        fr, _ = D.ink_figure(fr, self.sp, t, D.feet(self.sp), (1060 - 40 * u, 950 + 6 * math.sin(t * 7)), D.fit_scale(self.sp, 1450), wind=8)
        fr = D.ink_text(fr, self.near, bleed=0.0, dens=0.8)
        # 朱红「牺」「牲」近景坠落
        for ch, x, on in (('牺', 560, O[40][8]), ('牲', 1420, O[40][9])):
            th = V(on)
            if t < th - 0.35: continue
            q = (t - (th - 0.35)) / 0.35
            y = lerp(-100, 560, ei(min(q, 1), 1.6)) + max(0, t - th) * 260
            L = D.text_layer([(ch, x, y, 300, 1.0, 1.0, -10 + 25 * q, CINNABAR)], fname='serif_black')
            L.A = cv2.GaussianBlur(L.A, (0, 0), 0.5 + 2.0 * max(0, 1 - q))
            fr = D.ink_text(fr, L, bleed=0.2, sig=8)
        fr = vcol(fr, '什么叫', 1745, 300, 108, O[40][5:8], t, (0.42, 0.40, 0.38), fname='serif_black', adv=1.15)   # [r5] 质问递进 1/3：淡墨、中号、右   # [r4] 停用角落小竖排：只留「什么叫」中号，牺牲由巨字承担
        return K.cam(fr, 1.04, -30 + 60 * u, 0), 1.0


class S05_Ren(Shot):
    """ECU 纸面：「什么叫」墨洇显出 →「忍」宋体巨字踩拍砸下（先大后定、墨洇开），「刃」上那一点变朱墨、
    凝成一滴沿纸滑落到左下（→ 下一镜秤盘左盘那枚朱红「人」，圆形匹配剪辑）"""
    t0, t1 = 165.88, 167.25
    paper = 1.0
    REN = (1010, 540, 610)
    DROP = (577, 726)          # [r7] 对齐新天平左盘朱「人」

    def __init__(self):
        x, y, s = self.REN
        self.pap = cv2.resize(D.paper(14)[300:780, 540:1380], (W, H))
        a = T.ink_bleed_glyph('忍', 'serif_black', s, 1.0, seed=5); G = a.shape[0]
        g = T.glyph('忍', 'serif_black', s, True)
        if g.shape != a.shape: g = cv2.resize(g, a.shape[::-1])
        self.ren = g
        self.ren_d = cv2.distanceTransform((g > 0.5).astype(np.uint8), cv2.DIST_L2, 3)
        self.ren_n = cv2.resize(D._tile(57)[:G // 6 + 1, :G // 6 + 1], (G, G))
        n, lab, st, cen = cv2.connectedComponentsWithStats((a > 0.5).astype(np.uint8))
        # 「刃」的那一点：左上方的小连通域
        cand = [i for i in range(1, n) if st[i, 4] < st[1:, 4].max() * 0.4 and cen[i][1] < G / 2 and cen[i][0] < G / 2]
        k = cand[0] if cand else 2
        dm = cv2.dilate((lab == k).astype(np.float32), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
        L = T.Layer(); L.paste(cv2.GaussianBlur(dm, (0, 0), 1.5), x, y, CINNABAR); self.dotA = L.A
        self.dot = (int(x - G / 2 + cen[k][0]), int(y - G / 2 + cen[k][1]))

    def render(self, t):
        u = self.u(t)
        fr = self.pap.copy()
        # [r5] 中景层：一道斜贯纸面的淡墨刀影（「忍」= 刃悬于心上），缓缓滑过
        x_, y_ = K.grid()
        cx_, cy_ = 980 + 120 * u, 520
        th_ = math.radians(-24)
        a_ = (x_ - cx_) * math.cos(th_) + (y_ - cy_) * math.sin(th_); b_ = -(x_ - cx_) * math.sin(th_) + (y_ - cy_) * math.cos(th_)
        wid = 46 * np.clip((1100 - a_) / 1500, 0, 1) ** 0.6
        blade = np.clip((wid - np.abs(b_ - 0.25 * wid)) / 6, 0, 1) * (a_ > -900) * (a_ < 1100)
        blade = cv2.GaussianBlur(blade.astype(np.float32), (0, 0), 9) * 0.16
        fr = fr * (1 - blade[..., None])
        tr = V(O[40][13]); tin = tr - 0.1
        x, y, s = self.REN
        if t < tr:
            Lq = T.Layer()
            for k, (ch, on) in enumerate(zip('什么叫', O[40][10:13])):
                p = cl((t - V(on) + 0.12) / 0.4)
                if p > 0:
                    Lq.paste(T.ink_bleed_glyph(ch, 'serif_black', 220, p, seed=k), 960, 300 + k * 250, INK)
            fr = D.ink_text(fr, Lq, bleed=0.1)
        else:
            fr = vcol(fr, '什么叫', 270, 270, 150, [self.t0] * 3, t, 'ink', emph={'叫': tuple(CINNABAR)}, fname='serif_black', adv=1.12)   # [r5] 递进 2/3：大一号、浓墨、叫朱红
        if t >= tin:
            # 第三棒：「忍」踩拍落定后保持完整清晰的宋体（≥15 帧可读），最后 0.2s 才从笔画边缘碎开、洇进下一镜
            q = cl((t - tin) / 0.1)
            sc = 1.0 + 0.45 * (1 - eo(q, 2))
            a = self.ren
            if sc > 1.01: a = cv2.resize(a, None, fx=sc, fy=sc)
            tb = self.t1 - 0.2                                   # 开始碎
            if t > tb:
                e = cl((t - tb) / 0.2)
                ae = self.ren_d - (self.ren_n - 0.5) * 18 - e * 34   # 距边越近、噪声越大越先碎
                a = self.ren * np.clip(ae / 3 + 0.0, 0, 1)
            L = T.Layer(); L.paste(a, x, y, INK, alpha=0.5 + 0.5 * q)
            if q < 1: L.A = cv2.GaussianBlur(L.A, (0, 0), 0.5 + 6 * (1 - q))
            fr = D.ink_text(fr, L, bleed=0.06, sig=3)
            if t > tb:      # 碎墨屑沿笔画外缘飞散
                fr = D.ink_spray(fr, t, tb, (x + 120, y), n=90, seed=57, power=700, size=(3, 11), life=0.5, grav=300)
                fr = D.ink_spray(fr, t, tb, (x - 160, y - 120), n=60, seed=58, power=600, size=(3, 9), life=0.5, grav=300)
            if t >= tr:
                fr = D.ink_spray(fr, t, tr, (x, y + 300), n=50, seed=55, power=700)
                # 刃上那一点：洇成朱墨
                c = cl((t - tr - 0.05) / 0.3)
                m = self.dotA * c
                fr = fr * (1 - m[..., None]) + m[..., None] * CINNABAR * 0.95
                if t > tr + 0.35:                      # 凝成一滴，滑落到秤盘位置
                    d = cl((t - tr - 0.35) / (self.t1 - tr - 0.38))
                    xx = lerp(self.dot[0], self.DROP[0], ei(d, 2)); yy = lerp(self.dot[1], self.DROP[1], ei(d, 2))
                    m2 = np.zeros((H, W), np.float32)
                    cv2.line(m2, self.dot, (int(xx), int(yy)), 0.55, 9, cv2.LINE_AA)
                    cv2.ellipse(m2, (int(xx), int(yy)), (17, int(20 + 10 * d)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
                    m2 = cv2.GaussianBlur(m2, (0, 0), 1.6)
                    fr = fr * (1 - m2[..., None]) + m2[..., None] * CINNABAR * 0.95
                    hl = np.zeros((H, W), np.float32); cv2.circle(hl, (int(xx - 5), int(yy - 8)), 4, 1.0, -1, cv2.LINE_AA)
                    fr = fr + cv2.GaussianBlur(hl, (0, 0), 2)[..., None] * 0.5
            p2 = cp(t, O[40][14], 0.2)
            if p2 > 0:
                L2 = D.text_layer([('让', 1640, 800, 170, p2, 1 + 0.3 * (1 - p2))], fname='serif_black')
                fr = D.ink_text(fr, L2)
        fr = D.fall_chars(fr, t, '忍让', 505, density=2, sizes=(90, 160), speed=(260, 420), layers=1, alpha=0.4, near_blur=9)   # [r5] 前景虚焦落字
        hit = [tr] if t >= tr else []
        fr = shake_cam(fr, t, hit, 14, z=1.0 + 0.05 * u, rot=1.2 * u)
        return fr, 1.0


def brush_mask(shape, p0, p1, w, seed, dry=0.5, pts=None, closed=False):
    """毛笔干湿笔触蒙版（墨的边缘不规则 + 顺笔方向的飞白丝）；pts 给折线/弧线时按折线画"""
    m = np.zeros(shape, np.float32)
    P = np.array(pts if pts is not None else [p0, p1], np.float32)
    # 笔压：起笔重、行笔略轻、收笔提
    for i in range(len(P) - 1):
        q = i / max(1, len(P) - 2)
        ww = w * (1.0 - 0.25 * math.sin(math.pi * q) + 0.15 * (q < 0.08))
        cv2.line(m, tuple(map(int, P[i])), tuple(map(int, P[i + 1])), 1.0, max(1, int(ww)), cv2.LINE_AA)
    if closed: cv2.line(m, tuple(map(int, P[-1])), tuple(map(int, P[0])), 1.0, int(w), cv2.LINE_AA)
    r = np.random.default_rng(seed)
    n = cv2.resize(r.random((shape[0] // 16 + 1, shape[1] // 16 + 1)).astype(np.float32), (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    m = cv2.GaussianBlur(m, (0, 0), max(0.8, w * 0.18))
    m = np.clip((m - 0.35 - (n - 0.5) * 0.35) * 4, 0, 1)
    d = P[-1] - P[0]
    ang = math.degrees(math.atan2(d[1], d[0]))
    st = r.random((shape[0] // 2, shape[1] // 2)).astype(np.float32)
    k = np.zeros((31, 31), np.float32); cv2.line(k, (0, 15), (30, 15), 1.0, 1)
    k = cv2.warpAffine(k, cv2.getRotationMatrix2D((15, 15), -ang, 1.0), (31, 31)); k /= k.sum() + 1e-6
    st = cv2.resize(cv2.filter2D(st, -1, k), (shape[1], shape[0]))
    return m * np.clip(1 - dry * np.clip((st - 0.52) * 6, 0, 1), 0, 1)


def arc_pts(c, ax, ay, a0, a1, n=40):
    return [(c[0] + ax * math.cos(math.radians(a)), c[1] + ay * math.sin(math.radians(a))) for a in np.linspace(a0, a1, n)]


class S06_Scale(Shot):
    """LS 白纸上的水墨天平（[r7] 换成生图水墨美术 assets/gen/D_r7/scale：干湿笔触、飞白、墨分五色的体积、左上受光/右侧背光），
    投影落在纸上；左盘一枚朱红「人」，右盘堆起上千个墨「人」—— 竟然平衡；句子「什么叫以一人换千人」坐在横梁上逐字落下，
    「一人」朱红。左上主光 + 斜射光束 + 浮尘 + 纸纹浮雕。镜头缓推 + 微仰；横梁（连秤盘）绕支点轻摆，立柱不动。"""
    t0, t1 = 167.25, 168.62
    paper = 1.0
    PIV = (960, 330)
    LP, RP = (577, 752), (1348, 752)        # [r7b] 对齐生图秤盘实测中心（左 576 / 右 1348，盘沿 y≈755）
    _ART = {}

    @classmethod
    def art(cls):
        if 'a' in cls._ART: return cls._ART['a']
        im = cv2.imread(ROOT + '/assets/gen/D_r7/scale_cut.png', cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0
        rgb = im[..., 2::-1].copy(); a = im[..., 3].copy()
        s = 0.536; src_piv = (1275.0, 208.0)
        M = np.float32([[s, 0, cls.PIV[0] - src_piv[0] * s], [0, s, cls.PIV[1] - src_piv[1] * s]])
        R = cv2.warpAffine(rgb, M, (W, H), flags=cv2.INTER_AREA); A = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_AREA)
        # 墨色分级：画里的亮面压成暖纸色的高光，暗部保持焦墨；稍暖
        lum = R.mean(-1, keepdims=True)
        R = np.clip((R - 0.04) * 1.08, 0, 1) * np.array([1.0, 0.97, 0.92], np.float32)
        x, y = K.grid()
        # [r7b] 不动部分 = 立柱 + 底座（实测立柱 x 910–1012、底座 y>815 宽到 ±185）；旧版 ±82 方框切过底座留下竖缝
        post = (((np.abs(x - 961) < 64) & (y > cls.PIV[1] + 50)) | ((np.abs(x - 961) < 215) & (y > 812))).astype(np.float32)
        post = cv2.GaussianBlur(post, (0, 0), 2.5)
        cls._ART['a'] = (R, A, post)
        return cls._ART['a']

    def __init__(self):
        sh = (H, W)
        self.R, self.A, self.postm = self.art()
        x, y = K.grid()
        nn = cv2.resize(D._tile(61)[:H // 4, :W // 4], (W, H))
        self.pool = np.clip(1 - np.sqrt(((x - 960) / 360) ** 2 + ((y - 912) / 40) ** 2) - (nn - 0.5) * 0.7, 0, 1) ** 0.7 * 0.35
        n2 = cv2.resize(D._tile(62)[:H // 4, :W // 4], (W, H))
        self.moon = np.clip((1 - np.sqrt(((x - 960) / 440) ** 2 + ((y - 500) / 420) ** 2)) * 3 - (n2 - 0.5) * 2.2, 0, 1) * 0.10
        r = np.random.default_rng(66)
        items = []
        for i in range(620):                    # [r7b] 字堆坐进右盘（半宽 138、底在盘沿），字号放大到可读「人」
            a = r.uniform(-1, 1); hgt = (1 - a * a) ** 0.75
            items.append(('人', self.RP[0] + a * 138, self.RP[1] - 4 - r.uniform(0, 1) ** 0.8 * hgt * 175, r.uniform(16, 34), 0.95, 1.0, r.uniform(-35, 35)))
        items.sort(key=lambda c: -c[2])
        self.heap = D.text_layer(items, fname='serif_b')
        self.one = D.text_layer([('人', self.LP[0], self.LP[1] - 50, 112, 1.0, 1.0, 0.0, CINNABAR)], fname='serif_black')
        T.warm('什么叫以一人换千人', 'serif_sb', 60, False)

    def _rot(self, L, M):
        L2 = T.Layer(); L2.A = cv2.warpAffine(L.A, M, (W, H)); L2.C = cv2.warpAffine(L.C, M, (W, H)); L2.bb = [0, 0, W, H]
        return L2

    def scene(self, t, sent_a=1.0, ty=0):
        fr = D.paper(15).copy() * D.fiber(5)[..., None]
        fr = D.wash(fr, 0.06, 0.0, 0.5, seed=9)
        fr = R7.paper_relief(fr, 66, amt=0.08)
        fr = D.fall_chars(fr, t, '人', 61, density=5, sizes=(14, 34), alpha=0.40, near_blur=3)
        ang = 0.9 * math.sin(t * 2.1)
        M = cv2.getRotationMatrix2D(self.PIV, ang, 1.0)
        Ab = cv2.warpAffine(self.A * (1 - self.postm), M, (W, H)); Rb = cv2.warpAffine(self.R, M, (W, H))
        Ap = self.A * self.postm
        Aall = np.maximum(Ab, Ap)
        # 投影：左上主光 → 影落右下（近实远虚）
        fr = R7.ink_cast(fr, Aall, ld=(-0.75, -0.6), dist=48, blur=8, amt=0.40)
        fr = fr * (1 - self.moon[..., None])
        fr = fr * (1 - self.pool[..., None] * 0.55) + self.pool[..., None] * INK * 0.55 * (fr / 0.93)
        for Aa, Rr in ((Ap, self.R), (Ab, Rb)):
            col = 0.55 * Rr + 0.45 * Rr * (fr / 0.93)            # 半透纸：纸纹从墨里透出
            fr = fr * (1 - Aa[..., None]) + col * Aa[..., None]
        # 朝光一侧的边缘再提一线湿墨反光
        fr = R7.rim_edge(fr, Aall, (-0.75, -0.6), 3, 0.18, (1.0, 0.95, 0.85), glow=4, gamt=0.0)
        fr = D.ink_text(fr, self._rot(self.heap, M), bleed=0.1)
        fr = D.ink_text(fr, self._rot(self.one, M), bleed=0.2, sig=6)
        fr = D.ink_spray(fr, 200.0, 199.0, (960, 890), n=50, seed=606, power=500, size=(2, 7))
        fr = R7.key_light(fr, (380, 90), 1500, amt=0.12, dark=0.34)
        fr = R7.light_shaft(fr, t, (300, -40), 52, 210, 0.13, seed=66, motes=45, length=1300)
        prog = [cp(t, o, 0.2) for o in O[41][0:9]]
        items = []
        for i, (ch, p) in enumerate(zip('什么叫以一人换千人', prog)):
            if p <= 0: continue
            big = i < 3                                            # [r5] 递进 3/3：「什么叫」在句首放大成 96px
            xx = (360 + i * 96) if big else ((640 + (i - 3) * 86) if i < 6 else (1110 + (i - 6) * 86))   # [r7b] 「以一人」左臂 /「换千人」右臂，让开支点
            yy = (262 if big else 278) + ty - 40 * (1 - eo(p))   # [r7] 坐在横梁上，收进安全框
            c = CINNABAR if i in (2, 4, 5) else 'ink'
            items.append((ch, xx, yy, 88 if big else 60, min(1, p * 1.5) * sent_a, 1 + 0.35 * (1 - eo(p)), 0.0, c))
        L = D.text_layer(items, fname='serif_sb')
        fr = D.ink_text(fr, self._rot(L, M), bleed=0.12)
        return fr

    def render(self, t):
        u = self.u(t)
        fr = self.scene(t)
        return K.cam(fr, 1.0 + 0.07 * eo(u, 2), 0, 24 * (1 - u), rot=-0.6 * u, center=(960, 300)), 1.0   # [r7] 推镜中心上移：顶行不被推出画


class S07_Heap(Shot):
    """CU 右盘：千人字堆被不断加码（「人」从天倾倒），左盘朱红「人」虚焦在远处；竖排「换千人」"""
    t0, t1 = 168.62, 169.55
    paper = 1.0
    def __init__(self):
        self.base = None

    def render(self, t):
        u = self.u(t)
        if self.base is None: self.base = S06_Scale()
        fr = self.base.scene(t)
        fr = K.cam(fr, 2.3 + 0.25 * u, 1348 - 960 + 20 * u, 640 - 540, center=(960, 540))
        x = np.linspace(0, 1, W, dtype=np.float32)[None, :]
        bl = cv2.GaussianBlur(fr, (0, 0), 9)
        m = (1 - K.sstep(0.18, 0.42, x))[..., None]
        fr = fr * (1 - m) + bl * m
        # 倾倒的「人」
        r = np.random.default_rng(71)
        L = T.Layer()
        for i in range(70):
            ph = r.random(); x0 = 1000 + r.normal(0, 220); s = r.uniform(30, 70)
            y = ((t - 168.0) * r.uniform(500, 900) + ph * 900) % 900 - 40
            T.place(L, '人', x0, y, s, 'ink', 'serif_b', alpha=0.9, rot=r.uniform(-60, 60) + t * 40, texture=False)
        fr = D.ink_text(fr, L, bleed=0.08)
        fr = vcol(fr, '换千人', 1752, 300, 96, O[41][6:9], t, 'ink', fname='serif_black')
        return shake_cam(fr, t, [V(O[41][7])], 5), 1.0


_TOPSEAL = {}


def top_seal(fr, ch, cx, cy, size, t, th, rot=-3.0, seed=0, col=(0.80, 0.09, 0.05)):
    """[r4] 不透明朱印：整方压在最上层，朱底 + 干净纸白字（不透出下面的印），落印前 0.12s 自高处落下、落后冲击压痕。"""
    if t < th - 0.12: return fr
    key = (ch, int(size), seed)
    if key not in _TOPSEAL:
        a = T._seal_img(ch, int(size), 'yin', seed)
        box = T._seal_img(' ', int(size), 'yin', seed)
        box = np.clip(cv2.GaussianBlur(box, (0, 0), 6) * 1.6, 0, 1)            # 方块本体（崩边、无颗粒洞）
        rgb = np.ones((*a.shape, 3), np.float32) * np.array(WHITE, np.float32)
        rgb = rgb * (1 - a[..., None]) + np.array(col, np.float32) * a[..., None] * (0.85 + 0.15 * a[..., None])
        _TOPSEAL[key] = (rgb, box)
    rgb, box = _TOPSEAL[key]
    e = cl((t - (th - 0.12)) / 0.12)
    sc = 1.0 + 0.55 * (1 - e) ** 2 + 0.015 * impact(t, th, 0.08)
    s = rgb.shape[0]
    M = cv2.getRotationMatrix2D((s / 2, s / 2), -rot, sc)
    M[0, 2] += cx - s / 2; M[1, 2] += cy - s / 2
    A = cv2.warpAffine(box, M, (W, H)) * (0.35 + 0.65 * e ** 0.6)
    C = cv2.warpAffine(rgb, M, (W, H))
    out = fr.copy()
    # 落下中的投影 / 落定后的压暗环
    sh = cv2.GaussianBlur(cv2.warpAffine(box, M, (W, H)), (0, 0), 8 + 40 * (1 - e))
    sh = np.roll(sh, (int(30 * (1 - e)), int(20 * (1 - e))), (0, 1))
    out = out * (1 - 0.45 * sh[..., None] * (1 - A[..., None]))
    out = out * (1 - A[..., None]) + C * A[..., None]
    return out


class S08_Seals(Shot):
    """[r5] 俯拍纸面：「理」「所」「应」三个朱批——朱砂笔一笔写出、随即一道朱圈圈住，一枚枚圈住纸心那枚朱红「人」；
    170.47「当」= 一方黑铁官印（铁面锻纹、斜面高光、阴刻金字）从高处整方砸下压顶，金字一闪、纸面压出暗环，
    之后整方静止压到切点（≈14 帧）。（第五棒 P0：去掉与副歌一 S040「是非对错」同款的朱印章块）"""
    t0, t1 = 169.55, 170.92
    paper = 1.0
    PI = [('理', 700, 380, 250, 0), ('所', 1230, 420, 250, 1), ('应', 760, 720, 250, 2)]
    DANG = ('当', 960, 540, 560, -3)

    def render(self, t):
        u = self.u(t)
        fr = D.paper(16).copy()
        fr = D.wash(fr, 0.06, 0.0, 1.0, seed=17)
        # [r7b] 后景：画外碑林被左上低角度主光投下的长影（冷灰、软边、随光缓移）+ 纸纹在斜光下起伏
        fr = R7.paper_relief(fr, 81, amt=0.12)
        fr = R7.stele_shadows(fr, t, seed=8, n=5, amt=0.17, drift=14)
        hits = []                                            # [r7] 去掉纸心朱「人」（与三方朱批同屏读成「理人所应」）
        for (ch, x, y, s_, sd), on in zip(self.PI, O[41][9:12]):
            th = V(on)
            p = cl((t - (th - 0.14)) / 0.32)
            if p <= 0: continue
            if t >= th: hits.append(th)
            pre = fr
            fr = R5.zhupi(fr, ch, x, y, s_, p, seed=sd)
            fr = R7.rim_edge(fr, (R7.diff_mask(pre, fr, 5.0) > 0.6).astype(np.float32), (-0.75, -0.6), 2, 0.22, (1.0, 0.85, 0.75), glow=1, gamt=0.0)   # [r7b] 湿朱受光一线
            fr = D.ink_spray(fr, t, th, (x + 60, y + 40), n=26, seed=80 + sd, power=380, col=CINNABAR, size=(2, 6))
        fr = R7.key_light(fr, (240, 120), 1500, amt=0.12, dark=0.36)                       # [r7b] 主光左上，右下角压暗
        fr = R7.light_shaft(fr, t, (120, 20), 36, 200, 0.12, seed=81, motes=45, length=1700)
        ch, x, y, s_, rot = self.DANG
        th = V(O[41][12])
        if t >= th: hits.append(th)
        pre = fr
        fr = R5.iron_seal(fr, ch, x, y, s_, t, th, rot=rot, seed=8)
        if t >= th:                                                                      # [r7b] 铁印受主光：左上暖轮廓 + 右下冷反光
            Ms = (R7.diff_mask(pre, fr, 3.0) > 0.5).astype(np.uint8)
            cs, _ = cv2.findContours(Ms, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            Ms = np.zeros((H, W), np.float32)
            if cs: cv2.fillConvexPoly(Ms, cv2.convexHull(max(cs, key=cv2.contourArea)), 1.0, cv2.LINE_AA)   # 整方外轮廓（不描内部金字）
            Ms = cv2.GaussianBlur(cv2.erode(Ms, np.ones((7, 7), np.uint8)), (0, 0), 1.2)
            fr = R7.rim_edge(fr, Ms, (-0.75, -0.6), 5, 0.55, (1.0, 0.9, 0.72), glow=8, gamt=0.0)
            fr = R7.rim_edge(fr, Ms, (0.8, 0.6), 3, 0.18, (0.7, 0.8, 1.0), glow=5, gamt=0.0)
        fr = R7.fg_debris(fr, t, seed=82, n=12, blur=12, amt=0.5, cinnabar=0.3)            # [r7b] 前景虚焦纸屑 / 朱屑
        if t >= th:
            fr = D.ink_spray(fr, t, th, (x - s_ * 0.55, y + s_ * 0.5), n=40, seed=88, power=700, size=(2, 6))
            fr = D.ink_spray(fr, t, th, (x + s_ * 0.55, y - s_ * 0.45), n=40, seed=89, power=700, size=(2, 6))
        fr = shake_cam(fr, t, hits, 9, z=1.0 + 0.04 * u, rot=-0.6 * u)
        if t >= th: fr = shake_cam(fr, t, [th], 16)
        return fr, 1.0


class S09_Brush(Shot):
    """ECU 太上皇的巨笔：笔锋落纸，宋体「正义」被他一笔一笔写出来（笔尖跟着笔序走）"""
    t0, t1 = 170.92, 171.83
    paper = 1.0
    CH = [('正', 720, 520, 520, 170.95, 171.42), ('义', 1260, 540, 520, 171.40, 171.83)]

    def __init__(self):
        import copy
        base = D.spr('tsh_brush')
        A = base.A; ys, xs = np.nonzero(A > 0.5)
        sel = xs > base.w * 0.5; j = np.argmax(ys * sel)
        self.tip = (xs[j] / base.w, ys[j] / base.h)
        # 只留「握笔的手 + 笔杆 + 笔锋」：沿笔杆的一条带（人和袍子不进 ECU）
        self.sp = copy.copy(base)
        yy, xx = np.mgrid[0:base.h, 0:base.w].astype(np.float32)
        p0 = np.array([0.40 * base.w, 0.22 * base.h]); p1 = np.array([xs[j], ys[j]], np.float32)
        d = p1 - p0; L2 = float(d @ d)
        tt = np.clip(((xx - p0[0]) * d[0] + (yy - p0[1]) * d[1]) / L2, 0, 1)
        dist = np.sqrt((xx - p0[0] - tt * d[0]) ** 2 + (yy - p0[1] - tt * d[1]) ** 2)
        band = np.clip((0.07 * base.w - dist) / (0.02 * base.w), 0, 1)
        self.sp.A = (A * band).astype(np.float32); self.sp.ring = base.ring * band
        for ch, *_ in self.CH: T._brush_prep(ch, 'serif_black', 520, 0)

    def head(self, ch, x, y, s, p):
        B = T._brush_prep(ch, 'serif_black', s, 0)
        O_, a = B['O'], B['a']; G = a.shape[0]
        fy, fx = np.nonzero((np.abs(O_ - p) < 0.015) & (a > 0.5))
        if not len(fy): return None
        return (x - G / 2 + fx.mean(), y - G / 2 + fy.mean())

    def render(self, t):
        u = self.u(t)
        fr = D.paper(17).copy()
        # [r5] 远景层：淡墨宫阙剪影（他的朝堂）随镜头慢移；字写在宫阙之上
        pa = R5.palace_mask(9, y_base=930, hmax=230)
        pa = cv2.GaussianBlur(np.roll(pa, int(-30 * u), 1), (0, 0), 4) * (0.75 + 0.5 * cv2.resize(D._tile(919)[:H // 4, :W // 4], (W, H)))
        fr = fr * (1 - pa[..., None] * 0.10)
        fr = D.wash(fr, 0.10, 0.75, 1.0, seed=171)
        # [r7b] 后景再加一层更远的淡墨山 + 雾（宫阙落在山前），纸纹斜光浮雕
        fr = R7.mist_mountains(fr, 17, y0=560, amp=150, dens=(0.08, 0.14, 0.0), drift=-60 * u)
        fr = R7.paper_relief(fr, 91, amt=0.11)
        L = T.Layer(); hd = None
        for ch, x, y, s, a0, a1 in self.CH:
            p = cl((t - a0) / (a1 - a0))
            if p <= 0: continue
            A = T.brush_glyph(ch, 'serif_black', s, p, 0, 0.15, 0.35)
            L.paste(A, x, y, INK)
            if p < 1: hd = self.head(ch, x, y, s, p) or hd
            else: hd = hd
        fr = D.ink_text(fr, L, bleed=0.3, sig=8)
        fr = R7.ink_sheen(fr, np.clip(L.A, 0, 1).astype(np.float32), (-0.75, -0.6), 4, 0.34, core=0.2)   # [r7b] 湿墨：受光一线反光、墨芯更浓
        fr = R7.key_light(fr, (260, 80), 1500, amt=0.12, dark=0.36)
        fr = R7.light_shaft(fr, t, (60, -20), 30, 230, 0.13, seed=91, motes=50, length=1800)
        if hd is None: hd = (1500, 760)
        # 巨笔（笔尖压在笔序前沿）
        fr, Ab = D.ink_figure(fr, self.sp, t, self.tip, (hd[0] + 14, hd[1] + 18), 1.5, rot=-6 + 4 * math.sin(t * 9), wind=0, k=1.4, dens=0.98)
        fr = R7.ink_cast(fr, Ab, (-0.75, -0.6), 60, 12, 0.30)                                # [r7b] 笔杆投影落纸
        fr = R7.rim_edge(fr, Ab, (-0.75, -0.6), 4, 0.6, (1.0, 0.93, 0.8), glow=7, gamt=0.25)   # 笔杆/手背受光轮廓
        fr = vcol(fr, '若正义由你定义', 1750, 212, 92, O[42][0:7], t, 'ink', fname='serif_black', adv=1.1)   # [r4] 放大（停用小竖排）
        fr = D.fall_chars(fr, t, '正义', 909, density=2, sizes=(100, 170), speed=(240, 380), layers=1, alpha=0.35, near_blur=9)   # [r5] 前景虚焦落字
        fr = R7.fg_debris(fr, t, seed=92, n=9, blur=13, amt=0.45, cinnabar=0.0)                # [r7b] 前景飞墨
        return K.cam(fr, 1.05 + 0.04 * u, (hd[0] - 960) * 0.05, (hd[1] - 540) * 0.05), 1.0


class S10_Giant(Shot):
    """仰拍 LS：太上皇水墨巨像握着巨笔压下来，天幕被他的墨染黑；身后刚写好的「正义」湿墨未干"""
    t0, t1 = 171.83, 172.56
    paper = 1.0
    def __init__(self):
        self.sp = D.spr('tsh_brush')
        self.zy = D.text_layer([('正', 420, 330, 330, 0.85, 1.0, 0.0), ('义', 420, 680, 330, 0.85, 1.0, 0.0)], fname='serif_black')

    def render(self, t):
        u = self.u(t)
        fr = D.paper(18).copy()
        fr = D.wash(fr, 0.55, -0.2, 0.55, seed=19)
        fr = D.ink_text(fr, self.zy, bleed=0.35, sig=12)
        fr = D.fall_chars(fr, t, '正义由你定义', 62, density=5, sizes=(16, 40), alpha=0.5, near_blur=3)
        # [r4] 巨像压下来：前倾旋转 + 下压 + 袍袖风动加大（去 0.7s 静帧）
        fr, _ = D.ink_figure(fr, self.sp, t, D.feet(self.sp), (1150 - 30 * u, 1500 + 60 * eo(u, 2)), D.fit_scale(self.sp, 1500) * (1 + 0.08 * eo(u, 2)),
                             rot=-3.5 * eo(u, 2), wind=11, shadow=0)
        # 笔尖滴墨（两拨）
        fr = D.ink_spray(fr, t, 171.9, (1330, 960), n=30, seed=5, power=300)
        fr = D.ink_spray(fr, t, 172.25, (1300, 940), n=24, seed=6, power=420)
        fr = D.ash(fr, t, 101, n=60, fall=(60, 160), size=(2, 6), amt=0.35, dark=True) if hasattr(D, 'ash') else fr
        fr = vcol(fr, '若正义由你定义', 1750, 212, 92, O[42][0:7], t, 'ink', fname='serif_black', adv=1.1)   # [r4] 放大（停用小竖排）
        return K.cam(fr, 1.0 + 0.09 * eo(u, 2), 0, -34 * u, rot=0.8 * u), 1.0


class S11_Answer(Shot):
    """反打 MCU 仰拍：鬼屠举刀向天（[r4] 换 defy_up 精灵，与 S16/S17/S24 同一张脸），水墨乘纸 + 脸部保留肤色层次；
    反问「谁来定义你的」第一次用手写体（行书）——字体 = 立场，竖排在他视线方向（右侧上方）"""
    t0, t1 = 172.56, 173.66
    paper = 0.8
    def __init__(self):
        self.sp = D.spr('defy_up')

    def render(self, t):
        u = self.u(t)
        fr = D.paper(19).copy()
        fr = D.wash(fr, 0.55, -0.1, 0.7, seed=23)
        fr = D.fall_chars(fr, t, '谁来定义罪状', 63, density=5, sizes=(16, 44), alpha=0.45, near_blur=3)
        # 仰拍缓推 + 人物微升：脚底锚在画框下沿
        fr, Aw = D.ink_figure(fr, self.sp, t, (0.45, 1.0), (760, H - BAR + 30 - 24 * u), 0.66 + 0.04 * u, wind=6, k=1.05,
                              gamma=1.0, dens=0.95, bleed=0.12)
        # [r7b] P1-7：与白纸段同一套光——左上暖主光 + 人物朝光一侧暖轮廓、背光一侧冷反光，纸纹浮雕
        fr = R7.rim_edge(fr, Aw, (-0.75, -0.6), 4, 0.75, (1.0, 0.93, 0.8), glow=8, gamt=0.3)
        fr = R7.rim_edge(fr, Aw, (0.85, -0.3), 3, 0.30, (0.7, 0.8, 1.0), glow=5, gamt=0.15)
        fr = R7.paper_relief(fr, 111, amt=0.07)
        fr = R7.key_light(fr, (300, 60), 1500, amt=0.12, dark=0.32)
        fr = R7.light_shaft(fr, t, (120, -40), 40, 200, 0.10, seed=111, motes=35, length=1500)
        items = []
        for i, (ch, on) in enumerate(zip('谁来定义你的', O[42][7:13])):
            p = cp(t, on, 0.22)
            if p <= 0: continue
            items.append((ch, 1430 - i * 14, 250 + i * 112 - 30 * (1 - eo(p)), 112, min(1, p * 1.5), 1 + 0.4 * (1 - eo(p)), 6.0))
        L = D.text_layer(items, fname='xing')
        fr = D.ink_text(fr, L, bleed=0.2)
        return K.cam(fr, 1.0 + 0.08 * eo(u, 2), 0, 24 * u, center=(900, 300)), 0.8


class S12_Pierce(Shot):
    """ECU 一柄真刀（实拍质感，唯一不是墨的东西）从纸底刺上来，刀尖顶进朱红行书「罪状」；「状」落字那一刻
    一刀两断（字沿刀线裂开滑走），刀继续上冲出画（→ 下一镜纸被撕开）。"""
    t0, t1 = 173.66, 174.59
    paper = 0.8
    TIP = (0.498, 0.03)
    def __init__(self):
        self.sp = D.spr('blade_up_cu')
        self.P = [dict(ch='罪', x=790, y=380, size=330, rot=0.0, font='xing', idx=0, emph=False),
                  dict(ch='状', x=1140, y=400, size=330, rot=0.0, font='xing', idx=1, emph=False)]

    def render(self, t):
        u = self.u(t)
        fr = D.paper(20).copy()
        # [r7] 背景：三层墨山（远淡近浓、干笔皴纹）+ 层间雾带；山脚一排被定罪的跪伏人影没在近雾里；左上暖主光 + 斜射光束 + 纸纹浮雕
        fr = R7.mist_mountains(fr, 12, y0=500, amp=190, drift=-40 * u)
        kn = R5.crowd_mask(1212, n=60, y_far=735, y_near=790, s_far=24, s_near=40, kneel=1.0)
        fr = fr * (1 - cv2.GaussianBlur(kn, (0, 0), 2.5)[..., None] * 0.42)
        fr = R7.paper_relief(fr, 20, amt=0.08)
        fr = R7.key_light(fr, (300, 120), 1400, amt=0.12, dark=0.34)
        fr = R7.light_shaft(fr, t, (180, 60), 33, 190, 0.12, seed=12, motes=40)
        tc = V(O[42][14])
        tipy = lerp(720, 520, eo(cl((t - self.t0) / (tc - self.t0)), 2)) - (520 * ei(cl((t - tc) / 0.35), 2) if t > tc else 0)
        fr = D.fall_chars(fr, t, '罪状', 120, density=4, sizes=(16, 40), alpha=0.35, near_blur=3, emph={'罪': tuple(CINNABAR)})
        # 刀在纸上的投影（暖光从左上 → 影落右下）
        Fw, Aw = D.warp(self.sp, t, self.TIP, (975 + 40, tipy + 30), 1.75, rot=-3, wind=0)
        fr = fr * (1 - cv2.GaussianBlur(Aw, (0, 0), 14)[..., None] * 0.35)
        # 刀尖前方纸面被顶起的隆起（法线高光 + 阴影环）
        x_, y_ = K.grid()
        if t < tc + 0.05:
            bq = 0.6 + 0.4 * math.sin(t * 25)
            dx_, dy_ = (x_ - 975) / 120, (y_ - (tipy - 60)) / 90
            bump = np.exp(-(dx_ ** 2 + dy_ ** 2))
            gy_, gx_ = np.gradient(bump)
            fr = fr * (1 - np.clip(gy_ * 9, 0, 1)[..., None] * 0.35 * bq) + np.clip(-gy_ * 9 - gx_ * 4, 0, 1)[..., None] * 0.22 * bq
        # [r7] 纸被刀从背面刺穿的裂口：参差撕边 + 纸芯白纤维 + 两片翻起的纸舌（左背光 / 右迎光）+ 投影 + 洞内黑（替代旧灰三角）
        ytop = max(560.0, tipy + 120) if t < tc else 560.0 - 30 * cl((t - tc) / 0.3)
        opn = 1.0 + 0.25 * cl((t - tc) / 0.3) if t > tc else 0.85 + 0.15 * cl((t - self.t0) / 0.2)
        fr_slit, over = R7.torn_slit(fr, 975, ytop, H - BAR + 4, 150, seed=12, open_=opn)
        fr = fr_slit
        fr, Aw = D.real_figure(fr, self.sp, t, self.TIP, (975, tipy), 1.75, rot=-3, expo=0.95, sat=0.55, tint=(0.98, 1.0, 1.04),
                               rim=(0.62, 0.76, 1.0), rim_amt=4.5, rim_dir=(0.7, -0.5), wind=0, breathe=0.0,
                               mblur=(0, 10 * impact(t, self.t0 + 0.02, 0.2) + (14 if t > tc else 0)))
        # [r7] 刀身轮廓光：左缘暖白主光一线 + 右缘冷蓝反光，与纸面光向统一
        fr = R7.rim_edge(fr, Aw, (-0.85, -0.5), 4, 1.1, (1.0, 0.95, 0.84), glow=7, gamt=0.35)
        fr = R7.rim_edge(fr, Aw, (0.9, -0.3), 3, 0.55, (0.62, 0.76, 1.0), glow=5, gamt=0.2)
        if over is not None:
            fr = fr * (1 - over[..., None]) + fr_slit * over[..., None]
        # 刃口一线寒光沿刃上行
        Fw, A2 = D.warp(self.sp, t, self.TIP, (975, tipy), 1.75, rot=-3, wind=0)
        lum = Fw.mean(-1)
        fr = D.metal_sheen(fr, A2 * ((Fw.max(-1) - Fw.min(-1)) < 0.12), lum, t, (975, 0), 90, speed=lerp(1100, 200, u), width=50, amt=0.7)
        if t < tc:
            items = []
            for p_, on in zip(self.P, O[42][13:15]):
                p = cp(t, on, 0.16)
                if p > 0: items.append((p_['ch'], p_['x'], p_['y'], 330, min(1, p * 1.5), 1 + 0.35 * (1 - eo(p)), 0.0, CINNABAR))
            L = D.text_layer(items, fname='xing')
            fr = D.ink_text(fr, L, bleed=0.3, sig=8)
        else:
            q = cl((t - tc) / 0.45)
            fr = T.slash_cut(fr, '罪状', 0.02 + 0.98 * q, places=self.P, fname='xing', color=tuple(CINNABAR), angle=-87, cut_at=0.02,
                             offset=-10, slide=0.35, appear=0.0, style_kw=dict(shadow=0.0, outline=0, glow=0.35, glow_color=(0.85, 0.12, 0.05)))
            fr = D.ink_spray(fr, t, tc, (975, 400), n=60, seed=121, power=800, col=CINNABAR)
        return shake_cam(fr, t, [tc], 12, z=1.0 + 0.04 * u), 0.8


# ===================================================================================== 第二幕：被牺牲者 / 白纸烧穿
def papercut(sp, seed=0):
    """把同伴群像转成朱红剪纸：亮处镂空、轮廓线刻空"""
    F, A = sp.F, sp.A
    lum = (F * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1)
    inside = cv2.distanceTransform((A > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    e = cv2.Canny((np.clip(lum, 0, 1) * 255).astype(np.uint8), 40, 110)
    e = cv2.dilate(e, np.ones((3, 3), np.uint8)).astype(np.float32) / 255
    holes = np.clip((lum - 0.55) * 6, 0, 1) * (inside > 10)
    holes = np.maximum(holes, e * (inside > 8) * 0.95)
    holes = cv2.morphologyEx(holes, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    Ac = np.clip(A * 1.3 - 0.15, 0, 1) * (1 - holes)
    return cv2.GaussianBlur(Ac.astype(np.float32), (0, 0), 0.7)


class Companions:
    _A = None
    @classmethod
    def mask(cls):
        if cls._A is None:
            sp = D.spr('companions'); cls._A = (papercut(sp), sp)
        return cls._A


def place_mask(A, sp_w, sp_h, M):
    return cv2.warpAffine(A, M, (W, H), flags=cv2.INTER_LINEAR)


def burn(A_shape_y, t, t_start, speed, seed, x=None, y=None, base=H - BAR):
    """自下而上烧：返回 (intact, glow, char)"""
    x, y = K.grid() if x is None else (x, y)
    n = cv2.resize(D._tile(seed)[:H // 4, :W // 4], (W, H))
    yf = base - (t - t_start) * speed
    f = (yf - y) + (n - 0.5) * 160
    intact = np.clip(f / 6, 0, 1)
    glow = np.exp(-(f / 16) ** 2) * (t > t_start)
    char = np.clip(1 - np.abs(f + 30) / 40, 0, 1) * (f < 0)
    return intact, glow, char


class S13_PaperCut(Shot):
    """LS 剪纸追忆：师兄、师姐、殷若、徒弟四个朱红剪纸剪影立在背光宣纸上；马善政楷竖排「谁又来为 / 被牺牲的」；脚下起火"""
    t0, t1 = 174.59, 175.96
    paper = 0.85
    def render(self, t):
        u = self.u(t)
        Ac, sp = Companions.mask()
        x0, y0, x1, y1 = sp.bbox
        s = 700 / ((y1 - y0) * sp.h)
        cx = (x0 + x1) / 2 * sp.w; by = y1 * sp.h
        ox = -40 + 80 * u
        M = np.float32([[s, 0, 960 + ox - cx * s], [0, s, 905 - by * s]])
        A = cv2.warpAffine(Ac, M, (W, H))
        bg = D.paper(21) * 0.92
        x, y = K.grid()
        glow = np.exp(-(((x - 960) / 900) ** 2 + ((y - 520) / 420) ** 2))
        bg = bg * (0.72 + 0.4 * glow[..., None]) * np.array([1.0, 0.93, 0.8], np.float32)
        sh = cv2.GaussianBlur(np.roll(np.roll(A, 14, 1), 16, 0), (0, 0), 7)
        fr = bg * (1 - sh[..., None] * 0.35)
        red = CINNABAR * (0.85 + 0.25 * D.paper(22)[..., :1] / 0.93)
        intact, gl, ch = burn(None, t, 175.5, 120, 77, x, y)
        Ab = A * intact
        fr = fr * (1 - Ab[..., None]) + red * Ab[..., None]
        fr = fr + (gl * A)[..., None] * EMBER * 2.2 + gl[..., None] * EMBER * 0.25 * cl((t - 175.5) / 0.3)
        fr = fr * (1 - (ch * 0.6)[..., None])
        if t > 175.5: fr = D.embers(fr, t, 13, n=40, area=(0, 700, W, H - BAR), amt=0.8)
        for (txt, xx, ons) in (('谁又来为', 250 + ox, O[43][0:4]), ('被牺牲的', 1680 + ox, O[43][4:8])):
            fr = vcol(fr, txt, xx, 215, 104, ons, t, 'ink', {'牺': CINNABAR, '牲': CINNABAR}, fname='kai', adv=1.08)   # [r4] 放大
        return K.cam(fr, 1.0 + 0.03 * u), 0.85


class S14_Burn(Shot):
    """CU 剪纸殷若被火从脚下烧上来：焦黑卷边、火线、余烬上飘；楷书朱红「牺牲」"""
    t0, t1 = 175.96, 176.87
    paper = 0.4
    def render(self, t):
        u = self.u(t)
        Ac, sp = Companions.mask()
        x0, y0, x1, y1 = sp.bbox
        fx = x0 + (x1 - x0) * 0.635; s = 1500 / ((y1 - y0) * sp.h)
        M = np.float32([[s, 0, 760 - fx * sp.w * s], [0, s, 140 + 60 * u - y0 * sp.h * s]])
        A = cv2.warpAffine(Ac, M, (W, H))
        x, y = K.grid()
        bg = D.paper(23) * (0.55 - 0.25 * u) * np.array([1.0, 0.85, 0.7], np.float32)
        fr = bg.copy()
        intact, gl, ch = burn(None, t, 175.85, 330, 78, x, y)
        Ab = A * intact
        red = CINNABAR * (0.85 + 0.25 * D.paper(24)[..., :1] / 0.93)
        fr = fr * (1 - Ab[..., None]) + red * Ab[..., None]
        fr = fr + (gl * np.maximum(A, 0.25))[..., None] * EMBER * 2.4
        fr = fr * (1 - ch[..., None] * 0.8)
        fr = D.embers(fr, t, 14, n=110, amt=1.1, rise=(80, 260))
        fr = vcol(fr, '牺牲', 1700, 360, 200, [O[43][5], O[43][6]], t, (0.95, 0.85, 0.7), fname='kai', adv=1.1, ink=False)
        return K.cam(fr, 1.0 + 0.06 * u, 0, -20 * u), 0.4


class S15_Hole(Shot):
    """LS 整张白纸世界从中心烧穿：黑洞里余烬中鬼屠单膝跪地；行书「陪葬」火烧显字后成灰飞散，镜头随灰上摇"""
    t0, t1 = 176.87, 178.26
    paper = 0.0
    def __init__(self):
        self.sp = D.spr('kneel_bow')

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        dark = 0.02 + 0.03 * cv2.resize(K.fbm(H // 8, W // 8, 151, base=3, octaves=4), (W, H))
        fr = np.stack([dark * 1.4, dark * 0.9, dark * 0.7], -1).astype(np.float32)
        fr = fr + np.exp(-(((x - 960) / 600) ** 2 + ((y - 980) / 260) ** 2))[..., None] * EMBER * 0.25
        fr, _ = D.real_figure(fr, self.sp, t, D.feet(self.sp), (960, 935), D.fit_scale(self.sp, 430), expo=0.7, sat=0.7,
                              tint=(1.08, 0.88, 0.72), rim=(1.0, 0.55, 0.2), rim_amt=3.5, rim_dir=(0.0, 1.0), wind=4)
        fr = D.embers(fr, t, 15, n=120, amt=1.0, rise=(60, 200))
        # 纸：中心烧开
        R = 40 + 1500 * eo(cl((t - self.t0) / 1.1), 1.6)
        n = cv2.resize(D._tile(79)[:H // 4, :W // 4], (W, H))
        d = np.sqrt((x - 960) ** 2 + ((y - 560) * 1.4) ** 2) + (n - 0.5) * 260
        f = d - R
        intact = np.clip(f / 6, 0, 1); gl = np.exp(-(f / 18) ** 2); chr_ = np.clip(1 - np.abs(f - 25) / 35, 0, 1) * (f > 0)
        pap = D.paper(25) * np.array([1.0, 0.95, 0.86], np.float32)
        fr = fr * (1 - intact[..., None]) + pap * intact[..., None]
        fr = fr * (1 - chr_[..., None] * 0.85) + gl[..., None] * EMBER * 2.5
        p = cl((t - (V(O[43][8]) - 0.32)) / 1.25)
        if p > 0:
            fr = T.burn_in(fr, '陪葬', p, places=[dict(ch='陪', x=760, y=420, size=300, rot=0.0, font='xing', idx=0, emph=True),
                                                  dict(ch='葬', x=1160, y=430, size=300, rot=0.0, font='xing', idx=1, emph=True)],
                           fname='xing', color='red', mode='ash', split=0.55, seed=3, emph='陪葬', emph_color='red')
        fr = fr + impact(t, V(O[43][8]), 0.2) * 0.25
        return K.cam(fr, 1.0 + 0.04 * u, 0, 40 - 90 * eo(u, 2)), 0.0


# ===================================================================================== 第三幕：觉醒 / 闯
def ember_bg(seed, warm=1.0):
    x, y = K.grid()
    d = 0.015 + 0.03 * cv2.resize(K.fbm(H // 8, W // 8, seed, base=3, octaves=4), (W, H))
    fr = np.stack([d * 1.3, d * 0.95, d * 0.8], -1).astype(np.float32)
    return fr + np.exp(-(((y - 1100) / 380) ** 2))[..., None] * EMBER * 0.18 * warm


class S16_Closed(Shot):
    """CU 余烬里低头闭目的侧脸：灰从上方落，火光从下方打上来；宋体竖排「从今往」逐字落 +「后」巨字收句（第三棒：统一宋体系统）"""
    t0, t1 = 178.26, 179.17
    def __init__(self):
        self.sp = D.spr('eyes_closed'); self.bg = ember_bg(161)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        fr = D.embers(fr, t, 160, n=40, amt=0.5, size=(2, 6), blur=4)
        fr, _ = D.real_figure(fr, self.sp, t, (0.5, 0.5), (1120, 560), 1.02, expo=0.78, sat=0.65, tint=(1.06, 0.9, 0.78),
                              rim=(1.0, 0.55, 0.22), rim_amt=3.0, rim_dir=(0.2, 1.0), wind=4)
        fr = D.ash(fr, t, 16, n=70, amt=0.55, col=(0.6, 0.57, 0.53))
        q = cl((t - self.t0) / (self.t1 - self.t0))
        ex, ey = lerp(380, 0.29 * W, eo(q, 2)), lerp(900, 0.555 * H, eo(q, 2))
        m = np.zeros((H, W), np.float32); cv2.circle(m, (int(ex), int(ey)), 5, 1.0, -1, cv2.LINE_AA)
        fr = fr + (cv2.GaussianBlur(m, (0, 0), 2) * 2 + cv2.GaussianBlur(m, (0, 0), 14) * 3)[..., None] * EMBER
        P = O[44]
        its = [(c, 300, 255 + k * 140, 120, cp(t, P[k], 0.18), 'w') for k, c in enumerate('从今往')]
        its.append(('后', 320, 740, 250, cp(t, P[3], 0.14), 'w'))
        fr = D.song(fr, its)
        return K.cam(fr, 1.0 + 0.06 * u), 0.0


class S17_Eye(Shot):
    """ECU 睁眼：瞳孔里一点火光；宋体「我的」落在画右，朱红宋体巨字「刀」伴一道白刃寒光横扫"""
    t0, t1 = 179.17, 180.09
    def __init__(self):
        im = Image.open(ROOT + '/assets/gen/S102/eye_open_raw.png').convert('RGB').resize((W, H), Image.LANCZOS)
        F = np.asarray(im).astype(np.float32) / 255
        lum = F.mean(-1, keepdims=True)
        F = lum + (F - lum) * 0.75
        x, y = K.grid()
        light = 0.35 + 0.75 * np.exp(-(((x - 640) / 700) ** 2 + ((y - 600) / 420) ** 2))
        self.F = (F ** 1.2 * light[..., None] * np.array([1.05, 0.92, 0.82], np.float32)).astype(np.float32)
        self.pupil = (0.29 * W, 0.555 * H)

    def render(self, t):
        u = self.u(t)
        fr = self.F * (0.55 + 0.45 * eo(cl((t - self.t0) / 0.3)))
        x, y = K.grid()
        g = np.exp(-(((x - self.pupil[0]) ** 2 + (y - self.pupil[1]) ** 2) / (2 * 14 ** 2)))
        fr = fr + g[..., None] * EMBER * (1.2 + 0.5 * math.sin(t * 20))
        fr = D.ash(fr, t, 17, n=30, amt=0.4, size=(4, 12))
        tk = V(O[44][6])
        its = [('我', 1330, 300, 125, cp(t, O[44][4], 0.16), 'w'), ('的', 1330, 440, 125, cp(t, O[44][5], 0.16), 'w'),
               ('刀', 1490, 600, 340, cp(t, O[44][6], 0.1), 'r')]
        fr = D.song(fr, its)
        if tk - 0.02 <= t < tk + 0.2:   # 白刃寒光横扫
            q = (t - tk + 0.02) / 0.22
            fr = TR._slash_streak(fr, (lerp(-200, 2100, eo(q, 2)), 520), np.array((math.cos(math.radians(-12)), math.sin(math.radians(-12)))), q, length=2600, width=4)
            fr = fr + 0.25 * (1 - q)
        z = 1.0 + 0.1 * eo(u, 2)
        return shake_cam(fr, t, [tk], 10, z=z, center=self.pupil), 0.0


class S18_Draw(Shot):
    """MS 雨夜：鬼屠横刀出鞘，寒光沿刃走过；脚下积水倒影 + 地雾（第三棒：去漩涡底，换雨夜地面空间）；宋体「只」+ 巨字「听」"""
    t0, t1 = 180.09, 181.0
    def __init__(self):
        self.sp = D.spr('draw_side')       # [r4] 侧身半抽刀（替换正面 T 字横刀站姿）

    def render(self, t):
        u = self.u(t)
        fr = D.night(t, 181, top=(0.05, 0.055, 0.07), bot=(0.015, 0.015, 0.02), glow=(1500, 160, 520, (0.45, 0.5, 0.65), 0.35), clouds=0.6)
        x, y = K.grid()
        cx = 1040 + 40 * u
        fr, Aw = D.real_figure(fr, self.sp, t, D.feet(self.sp), (cx, 1010), D.fit_scale(self.sp, 900), expo=1.0, sat=0.6,
                               rim=COLD, rim_amt=3.4, rim_dir=(0.7, -0.7), wind=7)
        # 积水倒影：画面下缘翻转、压暗、水纹扰动
        gy = 1010
        refl = cv2.flip(fr[gy - 260:gy], 0)
        hh = min(refl.shape[0], H - gy)
        rip = (np.sin(np.arange(hh)[:, None] * 0.35 + t * 9 + np.arange(W)[None, :] * 0.01) * 4).astype(np.float32)
        mx = (np.arange(W)[None, :] + rip).astype(np.float32); my = np.repeat(np.arange(hh, dtype=np.float32)[:, None], W, 1)
        rr = cv2.remap(np.ascontiguousarray(refl[:hh]), mx, my, cv2.INTER_LINEAR)
        fr[gy:gy + hh] = fr[gy:gy + hh] * 0.5 + rr * 0.35
        Fw, A2 = D.warp(self.sp, t, D.feet(self.sp), (cx, 1010), D.fit_scale(self.sp, 860), wind=0)
        lum = Fw.mean(-1)
        sat = Fw.max(-1) - Fw.min(-1)
        metal = A2 * np.clip((lum - 0.28) * 3, 0, 1) * (sat < 0.1)
        fr = D.metal_sheen(fr, metal, np.ones_like(lum), t, (600, 0), 0, speed=lerp(500, 1500, eo(u, 2)), width=90, amt=2.0)
        fr = K.rain(fr, t, 18, n=500, amt=0.3, angle=6)
        fr = K.fog(fr, t, 44, amt=0.35, speed=(60, 0), y0=0.72, y1=1.0, color=(0.25, 0.27, 0.32))
        # [r4] 「只」「听」= 冷钢字：与刃上同一道寒光同步扫过（字和刀是同一块钢），不再是白宋体
        fr = D.steel_glyph(fr, [('只', 330, 300, 140, cp(t, O[44][7], 0.16)), ('听', 360, 600, 310, cp(t, O[44][8], 0.12))], t,
                           sweep_x=lerp(-200, 900, eo(u, 2)))
        return K.cam(fr, 1.03, -20 + 40 * u, 0), 0.0


def stroke_head(ch, fname, x, y, s, p):
    """笔序前沿在画面里的位置（brush_glyph 进度 p 时）"""
    B = T._brush_prep(ch, fname, s, 0)
    O_, a = B['O'], B['a']; G = a.shape[0]
    fy, fx = np.nonzero((np.abs(O_ - p) < 0.02) & (a > 0.5))
    if not len(fy): return None
    return (x - G / 2 + fx.mean(), y - G / 2 + fy.mean())


class S19_Forge(Shot):
    """ECU 刃面斜贯全屏、继续出鞘滑动；刀刃擦出的火星在刀上方的空气里「写」出宋体「主张」（火星就是笔锋，
    写完的笔画从白金冷却成暗红余烬）；左上一方朱印「我」随切入落下（第三棒：行书 → 可读宋体 + 朱印）"""
    t0, t1 = 181.0, 181.91
    CH = [('主', 760, 330, 300), ('张', 1250, 320, 310)]
    FN = 'serif_black'
    def __init__(self):
        self.sp = D.spr('S103/slow_draw')
        for ch, x, y, sz in self.CH: T._brush_prep(ch, self.FN, sz, 0)

    def render(self, t):
        u = self.u(t)
        fr = ember_bg(190, 0.6)
        fr = D.embers(fr, t, 191, n=50, amt=0.6, size=(1, 2.5))
        bx = 980 - 160 * u
        fr, Aw = D.real_figure(fr, self.sp, t, (0.46, 0.27), (bx, 700), 4.0, rot=14, expo=0.95, sat=0.5,
                               rim=COLD, rim_amt=2.0, wind=0, breathe=0.0)
        Fw, A2 = D.warp(self.sp, t, (0.46, 0.27), (bx, 700), 4.0, rot=14, wind=0)
        metal = A2 * ((Fw.max(-1) - Fw.min(-1)) < 0.1)
        fr = D.metal_sheen(fr, metal, Fw.mean(-1), t, (0, 0), -14, speed=lerp(200, 2000, eo(u, 2)), width=80, amt=1.4)
        hits = []
        for k, ((ch, x, y, sz), on) in enumerate(zip(self.CH, O[44][10:12])):
            tv = V(on); a0 = tv - 0.26; a1 = tv + 0.04
            p = cl((t - a0) / (a1 - a0))
            if p <= 0: continue
            if t >= tv: hits.append(tv)
            A = T.brush_glyph(ch, self.FN, sz, p, 0, 0.0, 1.0, splatter=False)
            fo = 1 - cl((t - (self.t1 - 0.1)) / 0.06)          # [r5] 出点遮挡前整组「主张」先熄掉，不让柱子遮出半个字
            L = T.Layer(); L.paste(A, x, y, (1, 1, 1), alpha=fo)
            heat = math.exp(-max(0, t - a1) / 0.6)
            hot = np.array([1.0, 0.86, 0.6], np.float32) * heat + np.array([0.95, 0.3, 0.08], np.float32) * (1 - heat)
            Ab = cv2.GaussianBlur(L.A, (0, 0), 14)
            sh = cv2.GaussianBlur(L.A, (0, 0), 8)
            fr = fr * (1 - sh[..., None] * 0.7)
            fr = fr * (1 - L.A[..., None]) + L.A[..., None] * hot * (1.25 + 0.5 * heat) + Ab[..., None] * np.array([1.0, 0.4, 0.1], np.float32) * (0.35 + 0.5 * heat)
            hd = stroke_head(ch, self.FN, x, y, sz, p) if p < 1 else None
            if hd is not None:      # 笔锋 = 一团火星
                g = np.zeros((H, W), np.float32); cv2.circle(g, (int(hd[0]), int(hd[1])), 10, 1.0, -1, cv2.LINE_AA)
                fr = fr + (cv2.GaussianBlur(g, (0, 0), 4) * 2.5 + cv2.GaussianBlur(g, (0, 0), 30) * 1.5)[..., None] * np.array([1.0, 0.7, 0.35], np.float32)
                fr = K.sparks(fr, t, 1900 + k * 7 + int(p * 20), hd, n=26, life=0.35, speed=(150, 600), dirc=(0, 1), spread=1.4, grav=900, amt=1.0)
        fr = K.sparks(fr, t, 1950, (bx - 200, 640), n=70, life=0.5, speed=(400, 1100), dirc=(0.3, -1), spread=0.5, grav=600, area=(300, 30), amt=0.9)
        sp_ = seal_p(t, 181.1)
        if sp_ > 0:
            fr = T.stamp_seal(fr, '我', 270, 330, 220, sp_, style='yin', rot=-6, seed=19, color='red')
            hits.append(V(181.1))
        return shake_cam(fr, t, hits, 7, z=1.0 + 0.05 * u), 0.0


def _strip_flat_shadow(sp):
    """[r6] run_top 抠图把地上的平灰投影（~RGB 80、无纹理、不饱和、成大块）当成了人：从 alpha 里扣掉，返回该投影的蒙版（另作压暗投影用）。"""
    v8 = sp.F * 255
    v = v8.mean(-1); sat = v8.max(-1) - v8.min(-1)
    mu = cv2.blur(v, (11, 11)); sd = np.sqrt(np.maximum(cv2.blur(v * v, (11, 11)) - mu * mu, 0))
    g = ((sat < 10) & (v > 58) & (v < 200) & (sd < 8) & (sp.A > 0.08)).astype(np.uint8)
    g = cv2.morphologyEx(g, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(g)
    keep = np.isin(lab, [i for i in range(1, n) if st[i, 4] > 1000]).astype(np.uint8)
    big = cv2.dilate(keep, np.ones((15, 15), np.uint8))
    keep = np.maximum(keep, big * ((v > 40) & (sat < 14)).astype(np.uint8)).astype(np.float32)
    keep = cv2.GaussianBlur(keep, (0, 0), 1.2)
    sp.A = np.clip(sp.A * (1 - keep), 0, 1).astype(np.float32)
    ring = sp.A - cv2.erode(sp.A, np.ones((5, 5), np.uint8))
    sp.ring = cv2.GaussianBlur(np.clip(ring, 0, 1), (0, 0), 1.5)
    return np.clip(keep, 0, 1)


class S20_Wall(Shot):
    """[r5 重做] 大俯拍 LS：满地摊开的巨幅竹简（湿、反冷光；竖条竹片 + 竹节 + 两道编绳 + 墨书律令），相机在他头顶后退跟拍，
    他从画面上方朝镜头冲来、踏过竹简；他刚踏过的三片竹简亮起暖白宋体「谁 定 的」；唱到「规矩」时前方左右两片竹简迸出金光、
    「规」「矩」金色巨字从地面立起像两扇门，他从两字之间冲过去 → 接 S21 斩断悬挂的律令木牌。
    （第五棒 P0：去掉与副歌一 S033–S036 撞车的灰色正交字砖网格，材质换成竹简）"""
    t0, t1 = 181.91, 182.81
    def __init__(self):
        self.sp = D.spr('run_top')
        self.shadow = _strip_flat_shadow(self.sp)               # [r6] 去掉抠图残留的平灰投影块，改成真正压暗竹简的投影
        src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
        dst = np.float32([[170, 0], [W - 170, 0], [W + 140, H], [-140, H]])
        self.Mp = cv2.getPerspectiveTransform(src, dst)
        self.rgb, self.gap, self.txt = R5.bamboo_scroll(4)
        self.wet = np.clip((cv2.resize(D._tile(207)[:H // 4, :W // 4], (W, H)) - 0.5) * 3, 0, 1)

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        oy = int(900 - 170 * u)                                # 相机后退：竹简向上走
        sl = (slice(oy, oy + H), slice(200 - 40, 200 - 40 + W))
        base = self.rgb[sl]; gap = self.gap[sl]
        flash = 0.5 * impact(t, 182.2, 0.14) + 0.8 * impact(t, V(O[45][3]), 0.1)
        key = 0.55 + 0.6 * np.exp(-(((x - 1300) / 1100) ** 2 + ((y - 200) / 800) ** 2)) + 0.6 * flash
        fr = base * key[..., None]
        fr = fr * (1 - gap[..., None] * 0.85)
        fr = cv2.warpPerspective(fr, self.Mp, (W, H), borderMode=cv2.BORDER_REPLICATE)
        # 湿面冷高光（随相机移动）+ 远端雾
        wet = np.roll(self.wet, -int(170 * u), 0)
        fr = fr + (wet * key * 0.16)[..., None] * np.array(COLD, np.float32)
        g = (y / H)[..., None]
        fr = fr * (0.55 + 0.45 * g) + (1 - g) * np.array([0.03, 0.032, 0.04], np.float32) * 0.6
        its = []
        for k, (ch, gx, gy) in enumerate((('规', 470, 660), ('矩', 1450, 660))):
            on = O[45][3 + k]
            pre = cl((t - (V(on) - 0.3)) / 0.3)
            if pre > 0:
                gl = np.exp(-(((x - gx) / 60) ** 2 + ((y - gy - 70) / 170) ** 2)) * pre       # 一整片竹简渗金（竖条形）
                fr = fr + gl[..., None] * GOLD * 1.3
            pq = cp(t, on, 0.2)
            if pq > 0:
                its.append((ch, gx, gy + 70 * (1 - eo(pq)), lerp(90, 330, eo(pq)), min(1, pq * 3), 'g'))
        lit = []
        for k, c in enumerate('谁定的'):
            pk = cp(t, O[45][k], 0.16)
            if pk > 0: lit.append((c, 700 + 260 * k, 262, 150, pk, 'w'))
        fr = D.song(fr, lit, glow=0.3)
        h = lerp(560, 660, ei(u, 1.3))
        sc = D.fit_scale(self.sp, h); fa = D.feet(self.sp); fd = (960, 930 + 40 * u)
        M = cv2.getRotationMatrix2D((fa[0] * self.sp.w, fa[1] * self.sp.h), 0, sc)
        M[0, 2] += fd[0] - fa[0] * self.sp.w; M[1, 2] += fd[1] - fa[1] * self.sp.h
        shw = cv2.GaussianBlur(cv2.warpAffine(self.shadow, M, (W, H)), (0, 0), 5)
        fr = fr * (1 - 0.62 * shw[..., None])                    # 投影落在湿竹简上（压暗，不是灰片）
        # [r8] P1-1：人物身后一圈湿竹简冷反光（把暗剪影从地面托出来）
        hy = fd[1] - 0.55 * h
        halo = np.exp(-(((x - fd[0] - 60) / 330) ** 2 + ((y - hy) / 420) ** 2))
        fr = fr + (halo * (0.10 + 0.12 * flash))[..., None] * np.array(COLD, np.float32)
        fr, Aw = D.real_figure(fr, self.sp, t, fa, fd, sc, expo=1.18 + 0.3 * flash, sat=0.55, gamma=1.05,
                               rim=COLD, rim_amt=6.0 + 3 * flash, rim_dir=(0.75, -0.65), wind=10)
        # [r8] 右上雷光冷轮廓：一线亮边勾出头、肩、前伸的手臂与刀，躯干再提亮 ~13%，读成「冲」而不是「爬」
        fr = fr * (1 + 0.13 * Aw[..., None])
        fr = R7.rim_edge(fr, Aw, (0.75, -0.65), 4, 0.95 + 0.8 * flash, (0.72, 0.84, 1.0), glow=8, gamt=0.35)
        fr = R7.rim_edge(fr, Aw, (-0.8, 0.4), 3, 0.35, (0.55, 0.62, 0.8), glow=4, gamt=0.1)
        fr = D.song(fr, its)
        fr = K.rain(fr, t, 20, n=500, amt=0.28, angle=4)
        fr = K.fog(fr, t, 45, amt=0.3, speed=(70, -10), y0=0.0, y1=0.35, color=(0.2, 0.21, 0.25))
        return shake_cam(fr, t, [V(O[45][3]), V(O[45][4])], 6, z=1.04 - 0.03 * eo(u, 2), rot=-1.5 + 1.5 * u), 0.0


class S21_Charge(Shot):
    """[r5 重做] CU 仰拍悬挂的律令木牌林（三层纵深：远处一排小牌在雾里、中景一排、近景两三块大牌虚焦压画边），
    麻绳吊着、在风里摇；183.10 一道刀光从画外斜斩而过（人不出现），中近景木牌齐齐断成两截、下半截翻滚坠落，
    木屑飞回拼成「我」（木纹碎块 + 冷轮廓光），「偏」随后。（第五棒 P0：S21 不再用 charge_front，与 S22 拉开；材质换木牌）"""
    t0, t1 = 182.81, 183.69
    TC = 183.06
    def __init__(self):
        self.P = R5.Plaques(seed=21, n_far=13, n_mid=7, n_near=3, ytop=40, cut=(self.TC, (-100, 780), (2000, 330)), gold_chars=())     # [r7] 木牌不再有金字抢「矩」「我」
        for it in self.P.items:                                 # [r7b] P1-9：中/近景木牌去刻字（只留远景虚焦小字），不和「我」抢视线
            if it['z'] >= 0.5: it['ch'] = ' '

    def render(self, t):
        u = self.u(t)
        fl = impact(t, self.TC, 0.12) + 0.6 * impact(t, 183.35, 0.1)
        fr = D.night(t, 211, top=(0.03, 0.032, 0.042), bot=(0.008, 0.008, 0.012), glow=(1150, 260, 460, (0.5, 0.58, 0.85), 0.28 + 0.9 * fl), clouds=0.6, drift=70)
        fr = D.lightning(fr, t, 183.35, (1650, 100), (1350, 360), seed=3, amt=0.9)
        fr = self.P.render(fr, t, light=1.0, rim=COLD, rim_amt=0.45, flash=fl, fog=(0.03, 0.033, 0.045))
        # [r7] P0「矩」182.92：「规」（上一镜立起的金门余像）+「矩」落拍金字砸在木牌林前；183.06 与木牌一起被同一刀斩断、错开熄灭
        GJ = [dict(ch='规', x=600, y=600, size=250, rot=0.0, font='serif_black', idx=0, emph=False),
              dict(ch='矩', x=960, y=545, size=320, rot=0.0, font='serif_black', idx=1, emph=False)]
        tj = V(O[45][4])
        if t < self.TC:
            pj = cp(t, O[45][4], 0.1)
            its = [('规', 600, 600, 250, 1.0, 'g')]
            if pj > 0: its.append(('矩', 960, 545, 320, pj, 'g'))
            fr = D.song(fr, its)
            fr = fr + impact(t, tj, 0.1) * np.array([0.25, 0.16, 0.05], np.float32) * 0.5
        else:
            q = cl((t - self.TC) / 0.4)
            f2 = T.slash_cut(fr, '规矩', 0.02 + 0.98 * q, places=GJ, fname='serif_black', color=tuple(GOLD), angle=-12.1, cut_at=0.02,
                             offset=0, slide=0.3, appear=0.0, style_kw=dict(shadow=0.6, outline=0, glow=0.45, glow_color=(1.0, 0.55, 0.2)))
            a_ = 1 - cl((t - self.TC - 0.16) / 0.16)
            fr = fr + (f2 - fr) * a_
        if self.TC - 0.03 <= t < self.TC + 0.22:
            q = (t - self.TC + 0.03) / 0.25
            fr = TR._slash_streak(fr, (lerp(-100, 2000, eo(q)), lerp(780, 330, eo(q))), np.array((0.977, -0.21)), q, length=2400, width=7, color=(1.0, 0.92, 0.85))
        fr = K.sparks(fr, t, 2101, (960, 560), n=90, life=0.6, speed=(300, 1000), dirc=(0, -1), spread=2.6, grav=900, burst=True,
                      t0=self.TC, color=(0.85, 0.6, 0.35), amt=0.9)
        fr = K.rain(fr, t, 21, n=380, amt=0.25, angle=8)
        fr = K.fog(fr, t, 212, amt=0.3, speed=(-80, -20), y0=0.6, y1=1.0, color=(0.16, 0.16, 0.2))
        for ch, x_, y_, sz, on, sd in (('我', 1460, 430, 330, O[45][5], 31), ('偏', 1500, 770, 200, O[45][6], 32)):
            tv = V(on)
            pq = cl((t - (tv - 0.24)) / 0.24)
            if pq > 0: fr = D.shard_glyph(fr, ch, x_, y_, sz, pq, seed=sd, spread=620, col=(0.86, 0.64, 0.38), rim=(0.85, 0.9, 1.0))   # [r7] 提亮，压过木牌
        return K.cam(fr, 1.03 + 0.05 * u, *K.shake(t, 4 + 10 * impact(t, self.TC, 0.15), 3, 21)[:2], rot=1.0 - 2.0 * u), 0.0


class S22_Chuang(Shot):
    """朱红宋体巨字「闯」立在镜头前（身后是被斩断、还在狂摆的律令木牌残桩与坠落的半截木牌、尘雾），他从字后冲来，
    184.18 一头撞碎：字裂成碎片朝镜头炸飞；左侧「我偏要」收句（第五棒：背景去灰砖墙）"""
    t0, t1 = 183.69, 184.67
    def __init__(self):
        self.sp = D.spr('S105/charge_front')
        self.P = R5.Plaques(seed=22, n_far=12, n_mid=7, n_near=0, ytop=-40, cut=(183.45, (-100, 520), (2000, 420)))
        self.P2 = [dict(ch='闯', x=1530, y=600, size=500, rot=-4.0, font='serif_black', idx=0, emph=True)]   # [r7b] P1-9：挪到人物右侧，露出冲刺

    def render(self, t):
        u = self.u(t)
        th = V(O[45][8])
        # [r8] P1-2：整镜回到 S21/S23 的冷蓝雨夜（天光、雾都偏冷），不再灰平
        fr = D.night(t, 221, top=(0.028, 0.038, 0.062), bot=(0.008, 0.010, 0.016), glow=(1060, 420, 460, (0.45, 0.56, 0.85), 0.32))
        fr = self.P.render(fr, t, light=0.7, rim=(1.0, 0.55, 0.45), rim_amt=0.8, blur_far=3.5)
        fr = K.fog(fr, t, 222, amt=0.42, speed=(-60, -30), y0=0.35, y1=1.0, color=(0.13, 0.16, 0.24))
        q = cl((t - self.t0) / (th - self.t0))
        h = lerp(820, 1250, ei(q, 2)) + (600 * eo(cl((t - th) / 0.4)) if t > th else 0)
        pin = cp(t, O[45][7], 0.25)
        fr, Aw = D.real_figure(fr, self.sp, t, (0.5, 0.42), (1060, 600), D.fit_scale(self.sp, h), expo=0.95, sat=0.55, gamma=1.2,
                               tint=(0.80, 0.92, 1.16), rim=(0.70, 0.82, 1.0), rim_amt=4.0, rim_dir=(-0.7, -0.7), wind=12)
        # [r8] 「闯」朱红反光：右侧（字一侧）暖红轮廓 + 身体右半边的红色漫反射；脸 / 刀刃左上冷高光一线
        x_, y_ = K.grid()
        red = (1.0, 0.26, 0.14)
        bounce = np.exp(-(((x_ - 1530) / 520) ** 2 + ((y_ - 640) / 420) ** 2)) * (0.35 + 0.65 * min(1.0, pin * 2))
        fr = fr + (Aw * bounce * 0.22)[..., None] * np.array(red, np.float32)
        fr = R7.rim_edge(fr, Aw * np.clip(bounce * 1.6, 0, 1), (0.95, -0.25), 5, 1.3, red, glow=9, gamt=0.35)
        fr = R7.rim_edge(fr, Aw, (-0.75, -0.65), 3, 0.75, (0.80, 0.90, 1.0), glow=5, gamt=0.15)
        fr = K.radial_blur(fr, (1060, 520), 0.015 + 0.03 * q)
        if t < th:
            p_in = cp(t, O[45][7], 0.25)
            L = D.text_layer([('闯', 1530 + 40 * (1 - ei(q, 2)), 700 - 100 * ei(q, 2), 380 + 120 * ei(q, 2), min(1, p_in * 2), 1.0, -4.0 * ei(q, 2), RED)], fname='serif_black')
            fr = T.compose(fr, L, **T.auto_style('red'))
        else:
            fr = T.shatter_out(fr, '闯', cl((t - th) / 0.5), places=self.P2, fname='serif_black', color='red', impact=(1330, 560), power=1.6, seed=7)
        its = [('我', 250, 280, 120, 1.0, 'w'), ('偏', 250, 420, 120, 1.0, 'w'), ('要', 250, 600, 190, cp(t, O[45][7], 0.14), 'w')]
        fr = D.song(fr, its)
        fr = fr + impact(t, th, 0.08) * 0.7 * np.array([0.78, 0.86, 1.0], np.float32)   # [r8] 撞击闪改冷白，不把整帧洗灰
        return shake_cam(fr, t, [th], 14), 0.0


# ===================================================================================== 第四幕：天判 / 刀答
class S23_Eye(Shot):
    """前景遮挡 OTS 大仰拍：近景鬼屠背影（肩背占画左下、冷轮廓光）仰望风暴之眼——漩涡只作背景（全段仅 2 镜用风暴：S23、S30）；
    185.26 一道闪电劈亮云眼，宋体巨字「天」在眼中显形（第三棒 P0 重做：有主体 + 有歌词）"""
    t0, t1 = 184.67, 185.57
    def __init__(self):
        self.sp = D.spr('wall_stand_back')

    def render(self, t):
        u = self.u(t)
        th = V(O[46][0])
        fl = impact(t, th, 0.15)
        fr = D.storm(t, 231, c=(1180, 400), spin=0.09, twist=0.8, base=(0.02, 0.022, 0.032), lit=(0.30, 0.33, 0.42), eye=170, bright=1.0,
                     glow=(1300, 300, 0.6 * fl + 0.4 * impact(t, 184.85, 0.12)))
        fr = D.lightning(fr, t, 184.85, (500, 120), (900, 420), seed=11, amt=1.2)
        fr = D.lightning(fr, t, th, (1650, 120), (1240, 380), seed=12, amt=1.8, life=0.25)
        p = cl((t - th + 0.03) / 0.12)
        p = max(p, 0.62 * cl((t - self.t0) / 0.25) * (0.85 + 0.15 * math.sin(t * 17)))     # [r5] 闪电前「天」已在云眼里可读（≥0.6）
        if p > 0:
            L = D.text_layer([('天', 1180, 410, 420, p * (0.9 + 0.1 * math.sin(t * 30)), 1.0 + 0.1 * (1 - p))], fname='serif_black', color=(0.92, 0.95, 1.0))
            fr = T.compose(fr, L, shadow=0.75, shadow_sigma=26, glow=0.9 + 0.8 * fl, glow_color=(0.6, 0.7, 1.0), glow_sigma=30)
            if t >= th:   # [r5] 185.26 闪电描边：字缘一圈电光（带抖动的分形断续亮边）
                ed = np.clip(cv2.dilate(L.A, np.ones((7, 7), np.uint8)) - L.A, 0, 1)
                nz = (cv2.resize(D._tile(int(t * 30) % 50 + 600)[:135, :240], (W, H)) > 0.45).astype(np.float32)
                fr = fr + (ed * (0.5 + nz) * 1.8 * math.exp(-(t - th) / 0.22))[..., None] * np.array([0.85, 0.92, 1.0], np.float32)
        fr = fr + impact(t, th, 0.06) * 0.12
        x, y = K.grid()
        fr = fr + np.exp(-(((x - 600) / 420) ** 2 + ((y - 620) / 300) ** 2))[..., None] * np.array([0.25, 0.3, 0.42], np.float32) * (0.6 + fl)
        # 前景：背影大特写（肩背压在画左下，头在画左中，抬头看天）
        sc = D.fit_scale(self.sp, 2100)
        fr, _ = D.real_figure(fr, self.sp, t, D.feet(self.sp), (560 - 30 * u, 2520 - 40 * u), sc, expo=0.6 + 0.4 * fl, sat=0.45,
                              tint=(0.9, 0.95, 1.08), rim=(0.75, 0.85, 1.0), rim_amt=8.0 + 6 * fl, rim_dir=(0.75, -0.65), wind=8)
        fr = K.rain(fr, t, 23, n=300, amt=0.25, angle=-6)
        return K.cam(fr, 1.0 + 0.06 * u, 0, -20 * u, rot=2 * u, center=(1180, 400)), 0.0


class S24_Defy(Shot):
    """[r5 重做] 低机位大远景剪影：他只占画高约 1/4，立在地平线上双手举刀直指天顶；头顶正中是 S23 那只风暴云眼
    （S23→S24 云眼位置连续 = 动作/图形匹配）；左上冷白宋体「天」「不」；186.02 一道闪电从云眼劈下落到刀尖，
    朱红「判」顺着闪电从云眼里砸下来、字脚正落在刀尖上（判 = 天劈到刀）。（第五棒 P0：不再镜像 S11 的 defy_up）"""
    t0, t1 = 185.57, 186.5
    EYE = (960, 250)
    def __init__(self):
        self.sp = D.spr('raise_low')
        A = self.sp.A; ys, xs = np.nonzero(A > 0.5)
        j = ys.argmin(); self.tip_src = (xs[j] / self.sp.w, ys[j] / self.sp.h)
        self.h = 285

    def render(self, t):
        u = self.u(t)
        tj = V(O[46][2])
        fl = impact(t, tj, 0.14)
        fr = D.storm(t, 241, c=self.EYE, spin=0.09, twist=0.8, base=(0.02, 0.022, 0.032), lit=(0.24, 0.27, 0.35), eye=150, bright=0.8,
                     glow=(self.EYE[0], self.EYE[1], 0.25 + 0.5 * fl))
        x, y = K.grid()
        fr = fr * (1 - 0.45 * np.clip((y - 500) / 400, 0, 1))[..., None]
        fr = fr + (np.exp(-(((x - 960) / 520) ** 2 + ((y - 830) / 110) ** 2)) * (0.22 + 0.5 * fl))[..., None] * np.array([0.55, 0.62, 0.85], np.float32)   # 剪影背后的地平冷光
        # 地平线 + 低机位地面（黑、上缘一线冷光）
        hor = 905 + 6 * math.sin(x[0] / 210.0)[None, :] if False else 905
        g = np.clip((y - hor) / 6, 0, 1)
        fr = fr * (1 - g[..., None]) + g[..., None] * np.array([0.012, 0.013, 0.018], np.float32)
        fr = fr + (np.exp(-((y - hor) / 3) ** 2) * np.exp(-((x - 960) / 700) ** 2) * (0.25 + 0.8 * fl))[..., None] * np.array(COLD, np.float32)
        fr = K.fog(fr, t, 243, amt=0.35, speed=(60, 0), y0=0.72, y1=0.9, color=(0.16, 0.17, 0.22))
        # 人：剪影 + 冷轮廓
        sc = D.fit_scale(self.sp, self.h * (1 + 0.04 * u))
        feet = (960, hor + 8)
        fr, Aw = D.real_figure(fr, self.sp, t, D.feet(self.sp), feet, sc, expo=0.22 + 0.4 * fl, sat=0.3, tint=(0.85, 0.9, 1.05),
                               rim=(0.8, 0.88, 1.0), rim_amt=10.0 + 10 * fl, rim_dir=(0.0, -1.0), wind=9)
        fx, fy = D.feet(self.sp)
        tip = (feet[0] + (self.tip_src[0] - fx) * self.sp.w * sc, feet[1] + (self.tip_src[1] - fy) * self.sp.h * sc)
        fr = D.lightning(fr, t, 185.7, (300, 140), (620, 520), seed=14, amt=0.8)
        fr = D.lightning(fr, t, tj, (self.EYE[0], self.EYE[1] + 30), (tip[0], tip[1]), seed=13, amt=2.2, branches=5, life=0.3)
        if t > tj:
            gt = np.exp(-(((x - tip[0]) ** 2 + (y - tip[1]) ** 2) / (2 * 30 ** 2))) * 3.0 * math.exp(-(t - tj) / 0.25)
            fr = fr + gt[..., None] * np.array([0.85, 0.9, 1.0], np.float32)
        fr = K.rain(fr, t, 24, n=600, amt=0.32, angle=4, length=(40, 120))
        # 「天」「不」冷白；「判」从云眼砸到刀尖
        fr = D.song(fr, [('天', 300, 300, 150, 1.0, 'w'), ('不', 300, 470, 150, cp(t, O[46][1], 0.14), 'w')])
        pj = cl((t - (tj - 0.16)) / 0.16)
        if pj > 0:
            e = ei(pj, 2)
            sz = lerp(90, 400, e)
            cy = lerp(self.EYE[1] + 20, tip[1] - 400 * 0.5 - 10, e)
            L = D.text_layer([('判', 960, cy, sz, min(1, pj * 2.5), 1.0, 0.0, RED)], fname='serif_black')
            if pj < 1: L.A = cv2.GaussianBlur(L.A, (0, 0), 0.5 + 5 * (1 - pj))
            fr = T.compose(fr, L, shadow=0.6, shadow_sigma=26, outline=3, outline_color=(0.03, 0.02, 0.02), glow=0.6 + 0.8 * fl,
                           glow_color=(0.95, 0.15, 0.06), glow_sigma=30)
            if t > tj:   # 落刀尖瞬间：字缘一圈闪电白
                Ld = cv2.dilate(L.A, np.ones((5, 5), np.uint8)) - L.A
                fr = fr + (np.clip(Ld, 0, 1) * 1.6 * math.exp(-(t - tj) / 0.15))[..., None] * np.array([0.9, 0.93, 1.0], np.float32)
        fr = fr * (1 + fl * 0.3)
        return shake_cam(fr, t, [tj], 12, z=1.0 + 0.05 * u + 0.05 * impact(t, tj, 0.1), oy=-20 * u, center=(960, 600)), 0.0


class S25_Leap(Shot):
    """大仰拍 LS：鬼屠背身跃起向天斜斩，刀光拖出朱白弧线；碎印章雨（被斩碎的「理所应当」朱印残片）三层纵深从天坠落、
    在刀光处炸开；宋体巨字「我」（第三棒：去漩涡底，换「碎印章雨」空间）。刀光斜线 → S26 劈断天平（匹配剪辑）"""
    t0, t1 = 186.5, 187.41
    def __init__(self):
        self.sp = D.spr('slash_sky_back')

    def render(self, t):
        u = self.u(t)
        ts = self.t0 + 0.05
        fr = D.night(t, 251, top=(0.07, 0.03, 0.03), bot=(0.015, 0.012, 0.014), glow=(1300, 140, 600, (0.6, 0.12, 0.06), 0.45), clouds=0.7, drift=60)
        fr = D.shard_rain(fr, t, 25, n=60, depth=(0.25, 0.7), t0=self.t0, burst=(ts, (1300, 300)))
        y = 760 - 120 * eo(u, 2)
        fr, Aw = D.real_figure(fr, self.sp, t, (0.5, 0.6), (1000, y), D.fit_scale(self.sp, 660), expo=0.8, sat=0.6,
                               rim=(1.0, 0.45, 0.35), rim_amt=4.0, rim_dir=(0.7, -0.7), wind=12)
        fr = D.shard_rain(fr, t, 26, n=14, depth=(0.9, 1.5), t0=self.t0, burst=(ts, (1300, 300)))
        q = cl((t - ts) / 0.45)
        if q < 1:
            fr = TR._slash_streak(fr, (lerp(600, 1600, eo(q)), lerp(800, 50, eo(q))), np.array((0.8, -0.6)), q, length=1400, width=5, color=(1.0, 0.75, 0.65))
        # 刀光留下的朱红斜痕（→ S26 斩线）
        x, yy = K.grid()
        d = np.abs((x - 1080) * 0.6 + (yy - 420) * 0.8)
        trail = np.exp(-(d / 5) ** 2) * cl((t - ts) / 0.3) * np.exp(-max(0, t - ts - 0.3) / 0.5)
        fr = fr + trail[..., None] * np.array([1.0, 0.25, 0.15], np.float32) * 1.2
        # [r4] 「我」被刀光沿斩线方向刻出：空心白热描边 + 朱红外发光，斜放在刀光轨迹上（右上）
        tw = V(O[46][3])
        rv = cl((t - (tw - 0.12)) / 0.3)
        if rv > 0: fr = D.light_glyph(fr, '我', 1440, 360, 340, rv, rot=20.0, d=(0.8, -0.6))
        return shake_cam(fr, t, [ts], 8, z=1.02 + 0.05 * u, oy=-15 * u), 0.0


class S26_Judge(Shot):
    """回扣 S06：白纸天平再现——朱红刀光沿上一镜的斜线劈下，天平连同整张纸被斩成两半、沿断口错开滑落（露出纸后的黑与红光）；
    187.94「判」朱红宋体巨字砸在断口上 → 3 帧全屏朱墨炸开（判字反白为墨）→ 退成暗红 → 最后 3 帧黑场憋气，接子弹时间。
    宋体「我来」写在纸上，跟着纸一起被劈开。（第三棒 P1/P2：叙事闭环 + 长短对比）"""
    t0, t1 = 187.41, 188.34
    C = (1080, 420); ANG = -37
    def __init__(self):
        self.sc = None
        x, y = K.grid()
        th = math.radians(self.ANG)
        self.d = np.array([math.cos(th), math.sin(th)], np.float32); self.n = np.array([-self.d[1], self.d[0]], np.float32)
        self.side = ((x - self.C[0]) * self.n[0] + (y - self.C[1]) * self.n[1]).astype(np.float32)
        nn = cv2.resize(D._tile(266)[:H // 4, :W // 4], (W, H))
        self.rd = (np.sqrt((x - 960) ** 2 + ((y - 540) * 1.3) ** 2) + (nn - 0.5) * 420).astype(np.float32)

    def render(self, t):
        u = self.u(t)
        if self.sc is None: self.sc = S06_Scale()
        ts = V(O[46][4]); tj = V(O[46][5])
        pap = self.sc.scene(t, sent_a=1 - cl((t - V(O[46][4])) / 0.2), ty=10)    # [r7] 劈开错位前句子先隐去，不随半张纸滑出画
        pap = D.song(pap, [('我', 390, 440, 140, 1.0, 'k'), ('来', 390, 600, 140, cp(t, O[46][4], 0.1), 'k')])   # [r7b] 下移，让开顶行残句
        s = eo(cl((t - ts - 0.04) / 0.45), 2)
        back = None
        if s <= 0:
            fr = pap; pm = 1.0
        else:
            back = D.night(t, 262, top=(0.06, 0.012, 0.01), bot=(0.01, 0.0, 0.0), glow=(1080, 420, 500, (0.9, 0.12, 0.05), 0.6), clouds=0.4)
            off = 50 * s + 150 * s * s
            out = back.copy()
            for sg in (1, -1):
                dx, dy = self.n * off * sg + self.d * 120 * s * sg
                M = np.float32([[1, 0, dx], [0, 1, dy]])
                half = cv2.warpAffine(pap, M, (W, H), borderMode=cv2.BORDER_CONSTANT)
                mk = (self.side * sg > 0).astype(np.float32)
                mk = cv2.warpAffine(cv2.GaussianBlur(mk, (0, 0), 1.0), M, (W, H))
                out = out * (1 - mk[..., None]) + half * mk[..., None]
            gap = np.exp(-(np.abs(self.side) / (8 + off)) ** 2)
            fr = out + gap[..., None] * np.array([1.0, 0.3, 0.12], np.float32) * 0.9 * (1 - 0.5 * s)
            pm = max(0.0, 1 - s * 2)
        if ts - 0.02 <= t < ts + 0.2:
            q = (t - ts + 0.02) / 0.22
            fr = TR._slash_streak(fr, (lerp(1080 - 900 * 0.8, 1080 + 900 * 0.8, eo(q)), lerp(420 + 900 * 0.6, 420 - 900 * 0.6, eo(q))),
                                  self.d, q, length=2400, width=6, color=(1.0, 0.8, 0.7))
        pj = cp(t, O[46][5], 0.1)
        hits = [ts]
        if pj > 0:
            hits.append(tj)
            burst = cl((t - tj) / 0.08) * (1 - cl((t - tj - 0.12) / 0.14))       # ≈4 帧全屏朱墨
            R = 2400 * eo(cl((t - tj) / 0.1), 2)
            bm = np.clip((R - self.rd) / 60, 0, 1) * burst
            fr = fr * (1 - bm[..., None]) + bm[..., None] * np.array([0.72, 0.04, 0.03], np.float32)
            if t > tj + 0.1:                                    # 炸开之后纸已烧没：朱墨退成暗红夜，只剩「判」
                ember = D.night(t, 263, top=(0.05, 0.01, 0.008), bot=(0.008, 0.0, 0.0), clouds=0.5) + \
                    np.exp(-(self.rd / 800) ** 2)[..., None] * np.array([0.4, 0.03, 0.02], np.float32)
                fr = fr * burst + ember * (1 - burst)
            if burst > 0.5:
                fr = D.song(fr, [('判', 960, 520, 600, pj, 'k')])
            else:
                fr = D.song(fr, [('判', 960, 520, 600, pj, 'r')], glow=0.35)
            fr = fr + impact(t, tj, 0.1) * RED * 0.3
            pm = 0.0
        tb = self.t1 - 0.1                                     # 3 帧黑场憋气
        if t >= tb: fr = fr * 0.0
        return shake_cam(fr, t, hits, 14, z=1.0 + 0.03 * u + 0.06 * impact(t, tj, 0.12)), pm


class S27_Bullet(Shot):
    """[r5 重做] CU 子弹时间：他的刀斜插在雨里（只有刀，人不在画内），雨滴悬停在刀身四周；镜头从刀柄红穗沿刀身下摇（tilt down），
    189.00 朱红「刀」被火星一笔笔烙刻在刀身上（白热 → 暗红余烬，字随刀身斜度）；右侧冷白宋体「不」「答」；
    （第五棒 P0：不再复用 S15 的 kneel_bow 跪姿；景别从 S15 的远景人 → 道具大特写）"""
    t0, t1 = 188.34, 189.71
    SC = 1.25
    def __init__(self):
        self.sp = D.spr('sword_planted')
        A = self.sp.A > 0.5
        rows = [int(f * self.sp.h) for f in (0.35, 0.75)]
        cx = [np.nonzero(A[r])[0].mean() for r in rows]
        self.ax = (cx[0] / self.sp.w, 0.35)                         # 刀身中线上的锚点
        self.slope = (cx[1] - cx[0]) / (rows[1] - rows[0])          # 每下行 1px 的 x 偏移
        self.ang = math.degrees(math.atan(self.slope))
        self.bg = None

    def place(self, t):
        u = self.u(t)
        k = eo(cl((t - self.t0) / 0.75), 3)                          # 0.75s 下摇到刻字处后放慢
        yy = lerp(1700, 330, k) - 50 * cl((t - self.t0 - 0.75) / 0.62)
        return (900 + 30 * u, yy)

    def render(self, t, text=True):
        u = self.u(t)
        if self.bg is None:
            x, y = K.grid()
            self.bg = (0.02 + 0.16 * np.exp(-(((x - 1000) / 520) ** 2 + ((y - 420) / 520) ** 2)) + 0.05 * np.exp(-((y - 760) / 60) ** 2))[..., None] * np.array([0.8, 0.9, 1.15], np.float32)
            r = np.random.default_rng(277); bk = np.zeros((H, W), np.float32)
            for _ in range(40):
                cv2.circle(bk, (int(r.uniform(0, W)), int(r.uniform(BAR, H - BAR))), int(r.uniform(10, 34)), float(r.uniform(0.2, 0.6)), -1, cv2.LINE_AA)
            self.bk = cv2.GaussianBlur(bk, (0, 0), 6)
        dst = self.place(t)
        fr = self.bg.copy()
        bo = int(-(dst[1] - 470) * 0.25)
        fr = fr + np.roll(self.bk, bo, 0)[..., None] * np.array([0.10, 0.12, 0.17], np.float32)
        fr = K.fog(fr, t, 271, amt=0.25, speed=(25, 0), y0=0.55, y1=1.0, color=(0.16, 0.18, 0.23))
        fr = D.droplets(fr, t, 271, n=120, orbit=-0.2 + 0.4 * u, focus=0.9)
        fr, Aw = D.real_figure(fr, self.sp, t, self.ax, dst, self.SC, expo=1.05, sat=0.5, rim=COLD, rim_amt=5.0, rim_dir=(-0.7, -0.7),
                               wind=0, breathe=0.0)
        Fw, A2 = D.warp(self.sp, t, self.ax, dst, self.SC, wind=0)
        metal = A2 * ((Fw.max(-1) - Fw.min(-1)) < 0.12) * np.clip((Fw.mean(-1) - 0.15) * 4, 0, 1)
        fr = D.metal_sheen(fr, metal, Fw.mean(-1), t, (dst[0], 0), 84, speed=700, width=70, amt=0.6)
        # 刀身上烙刻「刀」
        tk = V(O[47][0])
        p = cl((t - (tk - 0.22)) / 0.26)
        if p > 0:
            gy = dst[1] + 0.06 * self.sp.h * self.SC
            gx = dst[0] + self.slope * (gy - dst[1])
            A = T.brush_glyph('刀', 'serif_black', 175, p, 0, 0.0, 1.0, splatter=False)
            M = cv2.getRotationMatrix2D((A.shape[1] / 2, A.shape[0] / 2), -self.ang, 1.0)
            A = cv2.warpAffine(A, M, A.shape[::-1])
            Lc = T.Layer(); Lc.paste(A, gx, gy, (1, 1, 1))
            G = Lc.A * np.clip(cv2.GaussianBlur(A2, (0, 0), 2) * 1.3, 0, 1)
            heat = math.exp(-max(0, t - tk - 0.03) / 0.22)
            hot = np.array([1.0, 0.86, 0.6], np.float32) * heat + np.array([0.92, 0.10, 0.04], np.float32) * (1 - heat)
            sh = cv2.GaussianBlur(G, (0, 0), 3)
            fr = fr * (1 - sh[..., None] * 0.5)
            fr = fr * (1 - G[..., None]) + G[..., None] * hot * (1.1 + 0.6 * heat)
            fr = fr + cv2.GaussianBlur(G, (0, 0), 16)[..., None] * np.array([1.0, 0.25, 0.08], np.float32) * (0.5 + 0.6 * heat)
            if p < 1:
                fr = K.sparks(fr, t, 2701 + int(p * 12), (gx, gy), n=30, life=0.35, speed=(150, 600), dirc=(0, 1), spread=1.6, grav=900, amt=1.0)
        fr = D.droplets(fr, t, 272, n=36, orbit=-0.7 + 1.4 * u, focus=0.2)
        if tk <= t < tk + 0.18:
            q = (t - tk) / 0.18
            fr = TR._slash_streak(fr, (lerp(dst[0] - 200, dst[0] + 120, q), lerp(150, 950, q)), np.array((0.25, 0.97)), q, length=1600, width=1, amt=0.5)
        # 刻完推近：镜头压向刀身上的「刀」（ECU），字在画里变大
        gy = dst[1] + 0.06 * self.sp.h * self.SC; gx = dst[0] + self.slope * (gy - dst[1])
        zq = eo(cl((t - tk + 0.05) / 0.35), 2) + 0.08 * cl((t - tk - 0.3) / 0.45)
        fr = shake_cam(fr, t, [tk], 6, z=1.0 + 0.6 * zq, ox=(gx - 960) * 0.0 - 20 + 40 * u, center=(gx, gy))
        return (self.text_only(fr, t) if text else fr), 0.0

    def text_only(self, fr, t):
        """「不答」：「答」随「不」一起以 35% 亮度入画（整句先读到），189.72 发声时提满；独立图层，不受入点故障影响"""
        pb = cp(t, O[47][1], 0.14)
        fr = D.song(fr, [('不', 1480, 430, 230, pb, 'w')])
        a = max(0.35 * pb, cp(t, O[47][2], 0.08))
        if a > 0:
            f2 = D.song(fr, [('答', 1560, 720, 230, 1.0, 'w')])
            fr = fr * (1 - a) + f2 * a
        return fr


class S28_Spin(Shot):
    """MS 回旋斩：前 0.2s 身体高速旋入（5 层金色残影拖尾），随后整个姿态定格清晰（≥6 帧，无运动模糊），残影慢慢散去；
    唱到「我」时悬停的雨滴被刀圈炸成金点；宋体巨字「我」（第三棒：定格 + 拖影）"""
    t0, t1 = 189.71, 190.61
    def __init__(self):
        self.sp = D.spr('spin_front')
        x0, y0, x1, y1 = self.sp.bbox
        self.anc = ((x0 + x1) / 2, y0 + 0.58 * (y1 - y0))
        self.sc = D.fit_scale(self.sp, 700)
        self.dst = (1080, 1000 - 0.42 * 700)

    def rot(self, t):
        return -55 * (1 - eo(cl((t - self.t0) / 0.2), 3))

    def render(self, t):
        u = self.u(t)
        x_, y_ = K.grid()
        fr = (0.015 + 0.05 * np.exp(-(((x_ - 1000) / 800) ** 2 + ((y_ - 560) / 420) ** 2)))[..., None] * np.array([1.1, 0.95, 0.8], np.float32)
        fr = K.fog(fr, t, 282, amt=0.35, speed=(140, 0), y0=0.55, y1=1.0, color=(0.2, 0.18, 0.16))
        tw = V(O[47][3])
        fr = D.droplets(fr, t, 281, n=150, burst=(tw, (1000, 560)), focus=0.6)
        fade = math.exp(-max(0.0, t - self.t0 - 0.2) / 0.25)
        # [r4] 「我」在他身后：金色定格残影字（残影层随刀圈错位、慢慢收拢），被人物遮挡 → 字在画面空间里，不是贴片
        fr = D.echo_glyph(fr, '我', 640, 450, 480, cp(t, O[47][3], 0.12), n=5, step=(60, -14), fade=0.4 + 0.6 * math.exp(-max(0.0, t - V(O[47][3])) / 0.35))
        for k in range(5, 0, -1):          # 金色残影
            tk = t - k * 0.035
            a = 0.32 * (1 - k / 6) * fade
            if a < 0.02: continue
            fr, _ = D.real_figure(fr, self.sp, t, self.anc, self.dst, self.sc, rot=self.rot(tk), expo=0.9, sat=0.3,
                                  tint=(1.3, 1.0, 0.6), rim=GOLDR, rim_amt=2.0, wind=0, breathe=0.0, alpha=a)
        fr, _ = D.real_figure(fr, self.sp, t, self.anc, self.dst, self.sc, rot=self.rot(t), expo=1.15, sat=0.65,
                              tint=(1.05, 0.98, 0.9), rim=GOLDR, rim_amt=4.0, rim_dir=(0.0, -1.0), wind=10)
        fr = K.sparks(fr, t, 2801, (1000, 560), n=140, life=0.8, speed=(400, 1400), dirc=(0, -1), spread=3.0, grav=200, burst=True,
                      t0=tw, color=tuple(GOLD), amt=1.4)
        return shake_cam(fr, t, [self.t0 + 0.2, tw], 8, z=1.04 - 0.04 * u, rot=-3 + 3 * eo(u)), 0.0


class S29_Thrust(Shot):
    """大仰拍：倒悬的碑林——几十块刻着宋体「律令天条」的石碑倒挂在天上（字也倒着）、三层纵深缓缓压下；
    他在碑林下背身举刀直刺，正中最大的那块碑从刀尖处裂出金缝；宋体巨字「来」（第三棒：去漩涡底，换「倒置碑林」）"""
    t0, t1 = 190.61, 191.54
    TIP = (960, 345)

    def __init__(self):
        self.sp = D.spr('thrust_sky_back')
        self.layers = [self._layer(k) for k in range(3)]
        x, y = K.grid()
        nn = cv2.resize(D._tile(293)[:H // 4, :W // 4], (W, H))
        self.cx = (x - self.TIP[0] - (nn - 0.5) * 70).astype(np.float32); self.y = y

    def _layer(self, k):
        r = np.random.default_rng(290 + k)
        L = T.Layer()
        stone = cv2.resize(D._tile(295 + k)[:256, :256], (W, H))
        A = np.zeros((H + 200, W), np.float32); Cv = np.zeros((H + 200, W, 3), np.float32)
        pal = [0.30, 0.24, 0.20][k]
        n = [16, 11, 1][k]
        chars = '律令天条正邪规矩尊卑名分理所应当大局忍让本分上下'
        for i in range(n):
            if k == 2: x, w, bot = self.TIP[0], 300, self.TIP[1] + 10
            else:
                x = r.uniform(-60, W + 60); w = r.uniform(120, 200) * (0.65 if k == 0 else 1.0); bot = r.uniform(380, 760) * (0.75 if k == 0 else 1.0) + 120
                if k == 1 and abs(x - self.TIP[0]) < 260: x += 520 * (1 if x > self.TIP[0] else -1)
            x0, x1 = int(x - w / 2), int(x + w / 2)
            m = np.zeros((H + 200, W), np.float32)
            cv2.rectangle(m, (x0, 0), (x1, int(bot)), 1.0, -1)
            cv2.ellipse(m, (int(x), int(bot)), (int(w / 2), int(w * 0.18)), 0, 0, 180, 1.0, -1, cv2.LINE_AA)   # 倒置的碑首
            A = np.maximum(A, m)
            sh = np.clip(1 - np.abs((np.arange(W) - x) / (w / 2)), 0, 1) ** 0.5
            Cv = Cv * (1 - m[..., None]) + m[..., None] * pal * (0.6 + 0.6 * sh[None, :, None])
            # 倒刻宋体
            nc = 3 if k < 2 else 0          # [r4] 正中碑留白给「来」
            cs = w * 0.55
            Lc = T.Layer()
            for j in range(nc):
                cy = bot - cs * 0.9 - j * cs * 1.15
                if cy < 40: break
                T.place(Lc, chars[(i * 3 + (nc - 1 - j) + k * 7) % len(chars)], x, cy, cs, 'white', 'serif_black', rot=0, texture=False)   # [r4] 正向可读
            ca = Lc.A[:H + 200] if Lc.A.shape[0] >= H + 200 else np.pad(Lc.A, ((0, H + 200 - Lc.A.shape[0]), (0, 0)))
            ca = ca * m
            Cv = Cv * (1 - ca[..., None] * 0.75) + np.roll(ca, -3, 0)[..., None] * 0.12 * (k + 1)
        Cv = Cv * (0.7 + 0.6 * np.pad(stone, ((0, 200), (0, 0)), mode='edge'))[..., None]
        return A, Cv

    def render(self, t):
        u = self.u(t)
        fr = D.night(t, 291, top=(0.05, 0.045, 0.045), bot=(0.02, 0.018, 0.016), glow=(960, 250, 600, (0.6, 0.45, 0.25), 0.25 + 0.4 * u), clouds=0.4)
        y = self.y
        for k, (A, Cv) in enumerate(self.layers):
            dy = -120 + (30 + 40 * k) * eo(u, 2) if k < 2 else -160 + 160 * eo(cl((t - self.t0) / 0.3), 2)
            M = np.float32([[1, 0, (k - 1) * 30 * u], [0, 1, dy]])
            a = cv2.warpAffine(A, M, (W, H)); c = cv2.warpAffine(Cv, M, (W, H))
            fogk = [0.45, 0.15, 0.0][k]
            c = c * (1 - fogk) + np.array([0.09, 0.08, 0.075], np.float32) * fogk
            fr = fr * (1 - a[..., None]) + c * a[..., None]
            if k == 2:
                # 碑底受金光（刀尖处）+ 金缝自刀尖向上裂开
                rimg = np.exp(-((y - self.TIP[1]) / 18) ** 2) * a
                cr = np.exp(-((self.cx) / (3 + 20 * u)) ** 2) * K.sstep(self.TIP[1] - 420 * eo(u), self.TIP[1] - 40, y) * (y < self.TIP[1] + 4) * a
                dim = 1.0 - 0.7 * cl((t - V(O[47][4]) + 0.1) / 0.25)      # [r4] 「来」裂出后金缝收光，让字可读
                fr = fr + (cr * 1.8 * dim + rimg * 0.6 * u)[..., None] * GOLD
                fr = D.godrays(fr, cr, (960, 140), amt=0.6 * u * dim)
        sc = D.fit_scale(self.sp, 1060 - self.TIP[1])
        fr, _ = D.real_figure(fr, self.sp, t, D.feet(self.sp), (822, 1060), sc, expo=0.8, sat=0.6, tint=(1.04, 0.98, 0.9),
                              rim=GOLDR, rim_amt=3.0 + 2 * u, rim_dir=(0.0, -1.0), wind=12)
        fr = K.fog(fr, t, 292, amt=0.3, speed=(50, 0), y0=0.8, y1=1.0, color=(0.25, 0.22, 0.2))
        # [r4] 「来」被刀尖金光从正中碑里裂出来（金缝沿笔画推进 → 整字爆亮）
        tl = V(O[47][4])
        pq = cl((t - (tl - 0.15)) / 0.4)
        if pq > 0: fr = D.crack_glyph(fr, '来', 960, 285, 200, pq, seed=29)
        return shake_cam(fr, t, [V(O[47][4])], 6, z=1.0 + 0.05 * u, oy=-20 * u), 0.0


def gold_tip(A, B, p, tip=(960, 345), seed=0):
    """[D组] S29→S30：「答」的金光从刀尖射出、以刀尖为圆心铺开，圆内是下一镜（裂开的云），圆缘一圈金焰；中间帧不是纯白"""
    x, y = K.grid()
    d = np.sqrt((x - tip[0]) ** 2 + (y - tip[1]) ** 2)
    n = cv2.resize(D._tile(311 + seed)[:H // 4, :W // 4], (W, H))
    R = 40 + 2300 * ei(p, 2)
    m = np.clip((R - d + (n - 0.5) * 260) / 140, 0, 1)
    out = A * (1 - m[..., None]) + B * m[..., None]
    ring = np.exp(-((d - R + (n - 0.5) * 260) / (40 + 80 * p)) ** 2)
    core = np.exp(-(d / (60 + 500 * p)) ** 2)
    out = out + (ring * 0.8 * (1 - p * 0.6) + core * 0.55 * math.sin(math.pi * p))[..., None] * GOLD
    out = out + D.rays(tip, p, seed=7, n=40)[..., None] * GOLD * 0.35 * math.sin(math.pi * p)
    a = math.sin(math.pi * cl((p - 0.15) / 0.7))
    if a > 0.02:
        L = D.text_layer([('答', 960, 470, 680, a * 0.45, 1.25 - 0.25 * p, 0.0, GOLD)], fname='serif_black')
        out = T.compose(out, L, shadow=0.0, glow=0.6 * a, glow_color=(1.0, 0.6, 0.2), glow_sigma=40)
    return out


class S30_Da(Shot):
    """ELS 镜头升起：风暴云沿刀线裂开，金光倾泻；「答」金色宋体巨字在裂缝里爆开；最后两拍亮度拉满，白金出画接副歌终"""
    t0, t1 = 191.54, 193.24
    def __init__(self):
        self.sp = D.spr('thrust_sky_back')

    def render(self, t):
        u = self.u(t)
        td = V(O[47][5])
        op = eo(cl((t - self.t0) / 1.4), 2)
        fr = D.storm(t, 301, c=(960, 300), spin=0.05, base=(0.035, 0.03, 0.03), lit=(0.4, 0.36, 0.3), eye=200 + 300 * op)
        x, y = K.grid()
        n = cv2.resize(D._tile(303)[:H // 4, :W // 4], (W, H))
        gap = 20 + 520 * op
        open_ = np.clip((gap - np.abs(x - 960 - (n - 0.5) * 120)) / 60, 0, 1) * (1 - K.sstep(700, 1000, y))
        sky = np.array([1.2, 0.95, 0.6], np.float32) * (0.8 + 0.5 * (1 - y / H))[..., None]
        fr = fr * (1 - open_[..., None]) + sky * open_[..., None]
        edge = np.clip(1 - np.abs(np.abs(x - 960 - (n - 0.5) * 120) - gap) / 30, 0, 1) * (1 - K.sstep(700, 1000, y))
        fr = fr + edge[..., None] * GOLD * 1.5
        fr = D.godrays(fr, open_ + edge, (960, 200), amt=0.9)
        fr, _ = D.real_figure(fr, self.sp, t, D.feet(self.sp), (960, 1000 + 160 * eo(u, 2)), D.fit_scale(self.sp, 420), expo=0.5, sat=0.5,
                              tint=(1.05, 0.95, 0.85), rim=GOLDR, rim_amt=5.0, rim_dir=(0.0, -1.0), wind=12, look='sil')
        p = cp(t, O[47][5], 0.1)
        if p > 0:
            L = D.text_layer([('答', 960, 470, 640, min(1, p * 2), 1 + 0.35 * (1 - eo(p)) + 0.05 * u, 0.0, GOLD)], fname='serif_black')
            fr = T.compose(fr, L, shadow=0.85, shadow_sigma=40, glow=0.5, glow_color=(1.0, 0.55, 0.2), glow_sigma=30)
            fr = K.sparks(fr, t, 3001, (960, 470), n=220, life=1.0, speed=(500, 1600), dirc=(0, -1), spread=3.1, grav=150, burst=True,
                          t0=td, color=tuple(GOLD), amt=1.5)
        fr = fr + impact(t, td, 0.12) * GOLD * 0.8
        wo = ei(cl((t - (self.t1 - 0.5)) / 0.5), 2)        # 白金出画（接 E 组 flash_white）
        fr = fr * (1 + 1.0 * wo) + wo * np.array([1.0, 0.92, 0.75], np.float32) * 0.55   # 金白出画但「答」轮廓仍在
        z = 1.0 + 0.04 * u + 0.1 * impact(t, td, 0.15)
        return shake_cam(fr, t, [td], 10, z=z, oy=-60 * eo(u, 2)), 0.0


SHOTS = [S01_Drop, S02_Steles, S03_TypeSlam, S04_Snow, S05_Ren, S06_Scale, S07_Heap, S08_Seals, S09_Brush, S10_Giant,
         S11_Answer, S12_Pierce, S13_PaperCut, S14_Burn, S15_Hole, S16_Closed, S17_Eye, S18_Draw, S19_Forge, S20_Wall,
         S21_Charge, S22_Chuang, S23_Eye, S24_Defy, S25_Leap, S26_Judge, S27_Bullet, S28_Spin, S29_Thrust, S30_Da]
# 入点转场：镜头名 → (转场, 切前秒, 切后秒, 参数)
CUTS = {
    'S02_Steles': ('match_cut', 0, 0.35, dict(shape='circle', center=(960, 560), radius=60, glow=np.array([0.9, 0.2, 0.1], np.float32))),
    'S03_TypeSlam': ('hard_cut_x', 0, 0.07, dict(impact=0.08, tint=(0.10, 0.09, 0.09), amt=0.45, ca=7, jolt=(0, 16))),   # [r6] 纸面镜头不白闪：墨压暗 + 色散 + 下顿
    'S04_Snow': ('smoke_through', 0.12, 0.2, dict(color=(0.93, 0.91, 0.86), seed=4)),
    'S05_Ren': ('ink_bleed_hd', 0.1, 0.2, dict(seed=5, center=(1420, 560))),
    'S06_Scale': ('match_cut', 0, 0.3, dict(shape='circle', center=(577, 726), radius=40, glow=np.array([0.74, 0.1, 0.06], np.float32))),
    'S07_Heap': ('zoom_through', 0.1, 0.15, dict(center=(1348, 640))),
    'S08_Seals': ('seal_iris', 0.1, 0.14, dict(center=(760, 400), ch='理')),
    'S09_Brush': ('ink_bleed_hd', 0.001, 0.28, dict(seed=9, center=(1560, 260))),
    'S10_Giant': ('hard_cut_x', 0, 0.07, dict(impact=0.07, tint=(0.05, 0.05, 0.06), amt=0.5, ca=6, jolt=(0, 20))),
    'S11_Answer': ('match_cut', 0, 0.2, dict(shape='line', center=(1300, 760), angle=-35, mode='cut')),
    'S12_Pierce': ('hard_cut_x', 0, 0.07, dict(impact=0.1, tint=(0.07, 0.10, 0.17), amt=0.5, ca=9, jolt=(0, -22))),   # [r6] 冷墨压暗（不白闪）+ 色散 + 上顶（刀从下刺上）
    'S13_PaperCut': ('paper_tear', 0.1, 0.3, dict(seed=12, angle=6)),
    'S14_Burn': ('burn_wipe', 0.12, 0.12, dict(seed=14)),   # [r7b] 火线自下烧过剪纸 → 露出火烧近景（替换两帧闪白）
    'S15_Hole': ('flash_red', 0.04, 0.1, dict(one_frame=True)),
    'S16_Closed': ('zoom_through', 0.08, 0.14, dict(center=(960, 700))),
    'S17_Eye': ('match_cut', 0, 0.3, dict(shape='circle', center=(int(0.29 * W), int(0.555 * H)), radius=8, glow=EMBER)),
    'S18_Draw': ('slash_wipe', 0.05, 0.2, dict(angle=-12, center=(960, 860))),
    'S19_Forge': ('hard_cut_on_beat', 0, 0.07, dict(frames=2, flash=0.3)),
    'S20_Wall': ('occlusion', 0.1, 0.15, dict(kind='pillar', direction=-1)),   # [r5] 柱从右侧入画：先遮「张」的右半「长」，不再露出错字
    'S21_Charge': ('hard_cut_x', 0, 0.07, dict(impact=0.08, tint=(1.0, 0.72, 0.38), amt=0.3, ca=7, jolt=(-18, 0))),
    'S22_Chuang': ('hard_cut_on_beat', 0, 0.07, dict(frames=2, flash=0.2)),
    'S23_Eye': ('shatter', 0.04, 0.14, dict(center=(1060, 560), seed=23, n=60)),
    'S24_Defy': ('bolt_cut', 0, 0.14, dict(seed=24)),   # [r7b] 闪电劈过切点 + 冷偏色散（替换两帧闪白）
    'S25_Leap': ('slash_wipe', 0.05, 0.2, dict(angle=-40)),
    'S26_Judge': ('match_cut', 0, 0.25, dict(shape='line', center=(1080, 420), angle=-37, mode='grow', glow=np.array([1.0, 0.3, 0.2], np.float32))),
    'S27_Bullet': ('hard_cut_x', 0, 0.07, dict(impact=0.1, tint=(0.62, 0.76, 1.0), amt=0.65, ca=8, jolt=(0, 18))),   # [r6] 冷白雨光闪 + 色散 + 下顿
    'S28_Spin': ('freeze_glitch_keep', 0.12, 0.10, dict(seed=28)),
    'S29_Thrust': ('gold_beam', 0.08, 0.14, dict(x0=960)),
    'S30_Da': ('gold_tip', 0.1, 0.14, dict(tip=(960, 345))),
}


def seal_iris(A, B, p, center=(760, 400), ch='理', rot=-7.0):
    """[r4] 印框转场（替代 S08 入点的 whip 糊条）：一方朱印的方框从高处砸下罩住上一镜（框内先压暗、朱边收拢），
    落定瞬间框内换成下一镜，方框随即外扩出画——中间帧同时有上一镜、下一镜和朱印边。"""
    x, y = K.grid()
    th = math.radians(rot)
    rx = (x - center[0]) * math.cos(th) + (y - center[1]) * math.sin(th)
    ry = -(x - center[0]) * math.sin(th) + (y - center[1]) * math.cos(th)
    d = np.maximum(np.abs(rx), np.abs(ry))
    if p < 0.5:
        q = ei(p / 0.5, 2)
        half = lerp(1500, 150, q)
        inside = np.clip((half - d) / 4, 0, 1)
        out = A * (1 - 0.35 * q * inside[..., None])
    else:
        q = eo((p - 0.5) / 0.5, 2)
        half = lerp(150, 1700, q)
        inside = np.clip((half - d) / 4, 0, 1)
        out = A * (1 - inside[..., None]) + B * inside[..., None]
    edge = np.clip(1 - np.abs(d - half) / (10 + 8 * (1 - abs(p - 0.5) * 2)), 0, 1)
    out = out * (1 - edge[..., None]) + edge[..., None] * np.array([0.08, 0.07, 0.07], np.float32)   # [r5] 墨框（不再是朱印框）
    return out


def hard_cut_x(A, B, dt, impact=0.08, tint=(1, 1, 1), amt=0.3, ca=6, jolt=(0, 0)):
    """[r6] 落拍硬切的冲击帧（critic_D_r3：S12/S27 硬切 flash=0 冲击弱）。切点第 1 帧全量、第 2 帧一半：
    放大 impact + 朝 tint 色偏（暗 tint = 墨压，亮 tint = 冷/暖闪）+ 横向 RGB 色散 ca px + 机位顿挫 jolt px。
    纸面镜头用暗 tint，避免第二轮被扣的「白闪」。"""
    if dt < 0: return A.copy()
    kf = int(round(dt * 30))
    if kf >= 2: return B.copy()
    a = 1.0 if kf == 0 else 0.45
    out = TR._zoom(B, 1 + impact * a)
    Mj = np.float32([[1, 0, jolt[0] * a], [0, 1, jolt[1] * a]])
    out = cv2.warpAffine(out, Mj, (W, H), borderMode=cv2.BORDER_REFLECT)
    tc = np.array(tint, np.float32)
    if tc.mean() < 0.3:
        out = out * (1 - amt * a) + tc * amt * a
    else:
        out = out * (1 - 0.5 * amt * a) + out * tc * (1.6 * amt * a) + tc * 0.12 * amt * a
    d = int(round(ca * a))
    if d:
        out = out.copy()
        out[..., 0] = np.roll(out[..., 0], d, 1); out[..., 2] = np.roll(out[..., 2], -d, 1)
    return out


def burn_wipe(A, B, p, seed=0):
    """[r7b] 火烧边缘擦除（critic_D_r4 P1-10：S14 去掉同款两帧闪白）：一条参差火线自下而上烧过 S13，
    火线下方露出 S14，火线上方纸面先焦黄、再焦黑卷边；火线本身白热→橙红，带上飘火星。"""
    x, y = K.grid()
    key = ('burn', seed)
    if key not in _TOPSEAL:
        _TOPSEAL[key] = (cv2.resize(D._tile(seed + 701)[:H // 8, :W // 8], (W, H), interpolation=cv2.INTER_CUBIC) - 0.5,
                         cv2.resize(D._tile(seed + 702)[:H // 3, :W // 3], (W, H), interpolation=cv2.INTER_CUBIC) - 0.5)
    n1, n2 = _TOPSEAL[key]
    yl = (H + 260) * (1 - eo(p, 2)) - 130 + n1 * 260 + n2 * 50    # 火线高度（越往上 p 越大）
    d = y - yl                                                     # >0：已烧穿
    m = np.clip(d / 3, 0, 1)
    out = A * (1 - m[..., None]) + B * m[..., None]
    scorch = np.clip(1 + d / 90, 0, 1) * (d < 0)                   # 火线上方 90px 焦黄 → 焦黑
    char = np.clip(1 + d / 26, 0, 1) * (d < 0)
    out = out * (1 - scorch[..., None] * 0.45 * np.array([0.2, 0.45, 0.8], np.float32))
    out = out * (1 - char[..., None] * 0.85)
    line = np.exp(-(d / 5) ** 2)
    glow = np.exp(-(d / 38) ** 2) * 0.55
    out = out + line[..., None] * np.array([1.6, 1.0, 0.5], np.float32) + glow[..., None] * EMBER
    ya = int(min(H - BAR - 80, max(BAR, np.median(yl) - 300)))
    out = D.embers(out, p * 2.0, 1400 + seed, n=90, area=(0, ya, W, int(max(ya + 80, min(H - BAR, np.median(yl) + 60)))),
                   rise=(120, 320), amt=1.2)
    return out


def bolt_cut(A, B, dt, seed=24, p0=(1400, 90), p1=(820, 1000)):
    """[r7b] 闪电切（critic_D_r4 P1-10：S24 去掉同款两帧闪白）：切点一道闪电劈过 S24 画面（冷白芯 + 两级辉光 + 频闪），
    叠 hard_cut_x 的冷色偏 + 色散 + 机位下顿；闪电在切后 4 帧内消散。"""
    out = hard_cut_x(A, B, dt, impact=0.06, tint=(0.62, 0.74, 1.0), amt=0.35, ca=10, jolt=(0, 14))
    if dt >= 0:
        out = D.lightning(out, dt, 0.0, p0, p1, seed=seed, life=0.14, amt=1.3, branches=5, width=4)
    return out


def gold_beam(A, B, p, x0=960, seed=0):
    """[r4] 刀尖金光纵向劈开（替代 split_slide）：一道金色竖光自下而上刺穿画面（= 他向天直刺的方向），
    随后光柱向两侧张开、光柱内就是下一镜（倒悬碑林），柱缘金边 + 体积光；中间帧同时带前后两镜元素。"""
    x, y = K.grid()
    nz = cv2.resize(D._tile(seed + 611)[:64, :256], (W, H)) - 0.5
    if p < 0.35:
        q = eo(p / 0.35, 2)
        top = H - (H + 40) * q
        core = np.exp(-((x - x0 - nz * 6) / 4) ** 2) * (y > top)
        glow = np.exp(-((x - x0) / 60) ** 2) * (y > top) * 0.6
        tipg = np.exp(-(((x - x0) / 40) ** 2 + ((y - top) / 40) ** 2)) * 2.0
        return A + (core * 2.2 + glow + tipg)[..., None] * np.array(GOLDR, np.float32)
    q = ei((p - 0.35) / 0.65, 2)
    half = 6 + (W * 0.62) * q
    dx = np.abs(x - x0 + nz * 30 * (1 - q))
    m = np.clip((half - dx) / 6, 0, 1)
    edge = np.exp(-((dx - half) / (8 + 20 * q)) ** 2)
    Bz = K.cam(B, 1.06 - 0.06 * q, 0, 0)
    out = A * (1 - m[..., None]) + Bz * m[..., None]
    out = out + (edge * (1.8 - 1.2 * q))[..., None] * np.array(GOLDR, np.float32)
    out = out + (np.exp(-((x - x0) / (120 + 500 * q)) ** 2) * 0.35 * (1 - q))[..., None] * np.array(GOLDR, np.float32)
    return out


def ink_bleed_hd(A, B, p, seed=0, center=None, edge=0.8, from_cut=False):
    """[r4] 半分辨率场 + 羽化的墨晕转场（替代 trans.ink_bleed 的 1/4 块状边），边缘浓墨带有毛笔纤维感。"""
    if from_cut: p = cl((p - 0.5) * 2)
    hs, ws = H // 2, W // 2
    c = center or (W / 2, H / 2)
    y, x = np.mgrid[0:hs, 0:ws].astype(np.float32)
    d = np.sqrt(((x * 2 - c[0]) / W) ** 2 * 3.1 + ((y * 2 - c[1]) / H) ** 2) / 1.05
    key = ('ibhd', seed)
    if key not in _TOPSEAL:
        _TOPSEAL[key] = ((TR.fbm(hs, ws, seed, 60) - 0.5) * 0.6, (TR.fbm(hs, ws, seed + 3, 12) - 0.5) * 0.12)
    n1, n2 = _TOPSEAL[key]
    f = d + n1 + n2
    thr = -0.15 + p * 1.9
    m = np.clip((thr - f) * 14, 0, 1)
    band = np.exp(-((thr - f - 0.04) / 0.035) ** 2) * (0 < p < 1)
    m = cv2.GaussianBlur(cv2.resize(m, (W, H), interpolation=cv2.INTER_CUBIC), (0, 0), 1.5)
    band = cv2.GaussianBlur(cv2.resize(band.astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC), (0, 0), 1.2)
    out = A * (1 - m[..., None]) + B * m[..., None]
    ink = np.array([0.05, 0.045, 0.045], np.float32)
    return out * (1 - np.clip(band * edge, 0, 1)[..., None]) + ink * np.clip(band * edge, 0, 1)[..., None]


class Bridge:
    def __init__(self):
        self.objs = {}
        self.ids = [S.__name__ for S in SHOTS]

    def shot(self, i):
        S = SHOTS[i]
        if S.__name__ not in self.objs: self.objs[S.__name__] = S()
        return self.objs[S.__name__]

    def idx(self, t):
        for i, S in enumerate(SHOTS):
            if t < S.t1 - 1e-6: return i
        return len(SHOTS) - 1

    def raw(self, t):
        i = self.idx(t)
        for j in (i, i + 1):
            if j <= 0 or j >= len(SHOTS): continue
            name, pre, post, kw = CUTS.get(self.ids[j], ('hard', 0, 0, {}))
            c = SHOTS[j].t0
            if name == 'hard' or not (c - pre - 1e-6 <= t < c + post - 1e-6): continue
            B, pb = self.shot(j).render(max(t, c))
            A, pa = self.shot(j - 1).render(min(t, SHOTS[j - 1].t1 - 1e-3)) if (pre > 0 or t < c) else (B, pb)
            p = (t - (c - pre)) / (pre + post)
            if pre == 0: p = 0.5 + 0.5 * p
            kw2 = dict(kw)
            if name == 'seal_iris':
                out = seal_iris(np.clip(A, 0, 4).astype(np.float32), np.clip(B, 0, 4).astype(np.float32), p, **kw2)
            elif name == 'gold_beam':
                out = gold_beam(np.clip(A, 0, 4).astype(np.float32), np.clip(B, 0, 4).astype(np.float32), p, **kw2)
            elif name == 'ink_bleed_hd':
                out = ink_bleed_hd(np.clip(A, 0, 4).astype(np.float32), np.clip(B, 0, 4).astype(np.float32), p, **kw2)
            elif name == 'freeze_glitch_keep':      # [r5] 故障只撕画面，「不答」是独立图层保持可读（「答」189.72 发声）
                S27 = self.shot(j - 1)
                A0, _ = S27.render(min(t, SHOTS[j - 1].t1 - 1e-3), text=False)
                out = TR.transition('freeze_glitch', np.clip(A0, 0, 4).astype(np.float32), np.clip(B, 0, 4).astype(np.float32), p, **kw2)
                if p < 0.8: out = S27.text_only(out, t)
            elif name == 'hard_cut_x':
                out = hard_cut_x(np.clip(A, 0, 4).astype(np.float32), np.clip(B, 0, 4).astype(np.float32), t - c, **kw2)
            elif name == 'burn_wipe':
                out = burn_wipe(np.clip(A, 0, 4).astype(np.float32), np.clip(B, 0, 4).astype(np.float32), p, **kw2)
            elif name == 'bolt_cut':
                out = bolt_cut(np.clip(A, 0, 4).astype(np.float32), np.clip(B, 0, 4).astype(np.float32), t - c, **kw2)
            elif name == 'gold_tip':
                out = gold_tip(np.clip(A, 0, 4).astype(np.float32), np.clip(B, 0, 4).astype(np.float32), p, **kw2)
            else:
                out = TR.transition(name, np.clip(A, 0, 4).astype(np.float32), np.clip(B, 0, 4).astype(np.float32), p, **kw2)
            return out, (pa if p < 0.5 else pb), 3
        fr, pm = self.shot(i).render(t)
        return fr, pm, 0

    def frame(self, t):
        fr, pm, ca = self.raw(t)
        return D.d_finish(fr, t, ca=ca, vig=0.45 - 0.3 * pm, grain=0.04, paper_mode=pm)


_B = [None]


def frame(f, cache):
    if _B[0] is None: _B[0] = Bridge()
    t = f / 30.0
    return K.to8(_B[0].frame(t))


if __name__ == '__main__':
    import sys as _s
    from PIL import Image as _I
    for a in _s.argv[1:]:
        tt = float(a)
        _I.fromarray(frame(int(round(tt * 30)), {})).save('/tmp/d/f_%.2f.png' % tt)
        print('ok', tt)
