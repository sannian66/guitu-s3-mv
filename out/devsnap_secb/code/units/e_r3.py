"""units/e_r3.py — E 组第三棒新增工具（只 E 组用）：
  统一副句系统 Sub、描边大字 LyrO、血字两种材质（拓印 / 滴血笔触）、
  直垂挂轴 Scrolls（不变形，只在被斩时断开下坠）、有厚度的纸片/金箔 Shreds、
  碑林纵深 SteleHall、透视地面 ground_persp、暗色系转场（blade_black 刀光黑切 / seal_cover 印章盖屏 / ink_swallow 墨晕吞屏）。"""
import math
import numpy as np, cv2
import c1kit as K
import typo as T
import e_kit as E
from e_kit import W, H, BAR, GOLD, GOLDW, REDT, WHITE_T, GOLD_T, sstep, c01, eio, eout, Lyr, row


# ============================================================== 字
SUB_SIZE = 68                 # 副句字高 68px ≈ 画面高 6.3%
SUB_Y = 862                   # 统一基线：下三分之一，距有效画面下边 ≥60px


def plate(fr, x0, y0, x1, y1, amt=0.55, feather=46):
    """字后暗衬：柔边暗带（不是硬框）。"""
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    m = np.zeros((H // 4, W // 4), np.float32)
    cv2.rectangle(m, (x0 // 4, y0 // 4), (x1 // 4, y1 // 4), 1.0, -1)
    m = cv2.resize(cv2.GaussianBlur(m, (0, 0), feather / 4), (W, H))
    return fr * (1 - amt * m)[..., None]


class LyrO(Lyr):
    """Lyr + 墨色描边（亮底上的大字可读）。"""
    def __init__(self, chars, t_out, outline=4, plate_amt=0.0, **kw):
        super().__init__(chars, t_out, **kw); self.ol = outline; self.pa = plate_amt

    def draw(self, fr, t, alpha=1.0, dx=0.0, dy=0.0):
        L = T.Layer(); Em = T.Layer(); any_ = False
        for i, (ch, x, y, s, f, col, ti) in enumerate(self.c):
            e = (t - (ti - E.IN_D)) / E.IN_D
            if e <= 0: continue
            q = (t - (self.t_out + 0.03 * i)) / E.OUT_D if self.t_out is not None else 0
            if q >= 1: continue
            a, em = E.burn_glyph(ch, f, s, min(1.0, e), max(0.0, q), self.seed + i, self.dir)
            lift = -14 * max(0.0, q)
            L.paste(a, x + dx, y + dy + lift, col, alpha); any_ = True
            if em is not None: Em.paste(np.clip(em * 1.5, 0, 1), x + dx, y + dy + lift, (1.0, 0.85, 0.55), alpha)
        if not any_: return fr
        if self.pa > 0:
            b = L.box(0)
            if b: fr = plate(fr, b[0] - 40, b[1] - 30, b[2] + 40, b[3] + 30, self.pa)
        fr = T.compose(fr, L, shadow=self.shadow, shadow_sigma=20, outline=self.ol, outline_color=(0.03, 0.02, 0.02),
                       glow=self.glow, glow_sigma=16)
        bx = Em.box(30)
        if bx:
            x0, y0, x1, y1 = bx
            A = Em.A[y0:y1, x0:x1]
            fr[y0:y1, x0:x1] += (A * 1.6 + cv2.GaussianBlur(A, (0, 0), 6) * 1.4)[..., None] * np.array([1.0, 0.72, 0.38], np.float32)
        return fr


class Sub:
    """统一副句：横排、68px SemiBold、下三分之一基线 y=862；位置只有三种（left 中心 x=480 / right x=1440 / center 960），
    一律放在主体的对侧；字后柔边暗衬 + 句首一枚小朱印方块。替代原来各镜的角落小竖排。"""
    def __init__(self, text, times, side='right', t_out=None, red='', gold='', seed=0, base=WHITE_T, y=SUB_Y):
        cx = {'left': 480, 'right': 1440, 'center': 960}[side] if isinstance(side, str) else side
        self.ch = row(text, times, cx, y, size=SUB_SIZE, red=red, gold=gold, track=0.22, base=base)
        self.l = Lyr(self.ch, t_out, seed=seed, glow=0.25, shadow=0.85)
        self.t0 = min(times); self.t_out = t_out
        n = len(text); w = n * SUB_SIZE * 1.22
        self.box = (cx - w / 2 - 34, y - SUB_SIZE * 0.75, cx + w / 2 + 34, y + SUB_SIZE * 0.75)
        self.seal = (cx - w / 2 - 22, y)

    def vis(self, t):
        a = c01((t - (self.t0 - 0.25)) / 0.2)
        if self.t_out is not None: a *= 1 - c01((t - self.t_out - 0.1) / 0.3)
        return a

    def draw(self, fr, t, dx=0.0, dy=0.0):
        v = self.vis(t)
        if v <= 0: return fr
        x0, y0, x1, y1 = self.box
        fr = plate(fr, x0 + dx, y0 + dy, x1 + dx, y1 + dy, 0.5 * v, feather=40)
        sx, sy = self.seal; s = 13
        cv2.rectangle(fr, (int(sx - s + dx), int(sy - s + dy)), (int(sx + s + dx), int(sy + s + dy)),
                      tuple(float(c * v + f * (1 - v)) for c, f in zip(REDT, (0, 0, 0))), -1, cv2.LINE_AA)
        return self.l.draw(fr, t, dx=dx, dy=dy)


def _speckle(g, seed, base=0.5):
    r = np.random.default_rng(seed)
    a = cv2.resize(r.random((g // 3, g // 3)).astype(np.float32), (g, g), interpolation=cv2.INTER_NEAREST)
    b = cv2.resize(r.random((g // 14, g // 14)).astype(np.float32), (g, g), interpolation=cv2.INTER_CUBIC)
    return a * 0.45 + b * 0.55


def blood_rub(fr, ch, cx, cy, size, p, seed=1):
    """「血」拓印：碑拓式斑驳红字（字口缺损、石纹透白、边缘吃墨），p 0→1 像一张拓纸压上去（0.12s 压下 + 微缩放）。"""
    if p <= 0: return fr
    a = T.glyph(ch, 'serif_black', size, False)
    g = a.shape[0]
    sp = _speckle(g, seed)
    stone = cv2.resize(K.fbm(g // 2, g // 2, seed + 5, base=10, octaves=5), (g, g))
    hole = np.clip((sp - 0.80) * 8, 0, 1) + np.clip((stone - 0.70) * 5, 0, 1) * 0.7      # 石面麻点 / 字口缺损
    ero = cv2.erode(a, np.ones((5, 5), np.uint8))
    edge = np.clip(a - ero, 0, 1)
    m = np.clip(a * (1 - hole) - edge * np.clip((sp - 0.55) * 3, 0, 1), 0, 1)
    tone = (0.78 + 0.35 * stone)[..., None] * np.array([0.80, 0.07, 0.05], np.float32)
    e = eout(c01(p / 0.6)); sc = 1.12 - 0.12 * e
    M = cv2.getRotationMatrix2D((g / 2, g / 2), 0, sc)
    m = cv2.warpAffine(m, M, (g, g)); tone = cv2.warpAffine(tone, M, (g, g))
    L = T.Layer(); L.paste_rgba(tone, m * e, int(cx - g / 2), int(cy - g / 2))
    out = T.compose(fr, L, shadow=0.75, shadow_sigma=22, outline=2, outline_color=(0.05, 0.01, 0.01), glow=0.25,
                    glow_color=(0.7, 0.05, 0.03), glow_sigma=20)
    return out


def blood_drip(fr, ch, cx, cy, size, t, t_in, seed=2):
    """「血」滴血笔触：行书字自上而下写出（0.16s），随后从笔画下缘挂下血滴、拉长、滴落；旁溅血点。湿润高光。"""
    q = t - (t_in - 0.12)
    if q <= 0: return fr
    a = T.glyph(ch, 'xing', size, False)
    g = a.shape[0]
    yy = np.arange(g, dtype=np.float32)[:, None] / g
    a = a * sstep(0, 0.04, (q / 0.16) * 1.1 - yy)
    r = np.random.default_rng(seed)
    bot = np.clip(a - np.roll(a, 3, 0), 0, 1)                # 笔画下缘
    cols = np.where(bot.max(0) > 0.5)[0]
    D = np.zeros_like(a)
    if len(cols) and q > 0.1:
        for c in r.choice(cols, size=min(14, len(cols)), replace=False):
            ys = np.where(bot[:, c] > 0.5)[0]
            y0 = int(ys.max()); L = (40 + r.uniform(0, 1) * size * 0.35) * eout(c01((q - 0.1 - r.uniform(0, 0.25)) / 0.9), 2)
            w = r.uniform(3, 8) * size / 400
            if L > 2:
                cv2.line(D, (int(c), y0), (int(c), int(min(g - 4, y0 + L))), 1.0, max(2, int(w)), cv2.LINE_AA)
                cv2.circle(D, (int(c), int(min(g - 4, y0 + L))), max(2, int(w * 1.3)), 1.0, -1, cv2.LINE_AA)
    sp = np.zeros_like(a)
    if q > 0.12:
        for _ in range(26):
            ang = r.uniform(0, 6.28); d = r.uniform(0.3, 0.62) * g * c01((q - 0.12) / 0.15) ** 0.5
            rr = r.uniform(2, 9) * size / 400
            cv2.circle(sp, (int(g / 2 + math.cos(ang) * d), int(g / 2 + math.sin(ang) * d * 0.8)), max(1, int(rr)), 1.0, -1, cv2.LINE_AA)
    m = np.clip(a + D + sp, 0, 1)
    hi = np.clip(cv2.GaussianBlur(m, (0, 0), 2) - cv2.GaussianBlur(np.roll(np.roll(m, 4, 0), 4, 1), (0, 0), 2), 0, 1)
    tone = np.ones((g, g, 3), np.float32) * np.array([0.62, 0.03, 0.03], np.float32)
    tone = tone + hi[..., None] * np.array([0.9, 0.5, 0.45], np.float32) * 0.9
    Lr = T.Layer(); Lr.paste_rgba(tone, m, int(cx - g / 2), int(cy - g / 2))
    return T.compose(fr, Lr, shadow=0.7, shadow_sigma=22, glow=0.2, glow_color=(0.6, 0.03, 0.02), glow_sigma=18)


def rub_text(fr, chars, seed=3, outline_gold=True):
    """判/我 同一套材质：红色拓印 + 金描边。chars = [(ch, x, y, size, t_in, t_out, now)]"""
    for i, (ch, x, y, s, ti, to, t) in enumerate(chars):
        p = c01((t - (ti - 0.1)) / 0.16)
        if p <= 0: continue
        if to is not None and t > to: p *= 1 - c01((t - to) / 0.25)
        a = T.glyph(ch, 'serif_black', s, False); g = a.shape[0]
        sp = _speckle(g, seed + i)
        m = np.clip(a * (1 - np.clip((sp - 0.78) * 7, 0, 1)), 0, 1)
        sc = 1.15 - 0.15 * eout(p)
        M = cv2.getRotationMatrix2D((g / 2, g / 2), 0, sc)
        m = cv2.warpAffine(m, M, (g, g))
        if outline_gold:
            ring = np.clip(cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))) - m * 0.9, 0, 1)
            Lg = T.Layer(); Lg.paste(ring, x, y, (1.0, 0.80, 0.45), p)
            fr = T.compose(fr, Lg, shadow=0.8, shadow_sigma=18, glow=0.6, glow_sigma=14, glow_color=(1.0, 0.6, 0.25))
        L = T.Layer(); L.paste(m, x, y, (0.78, 0.07, 0.05), p)
        fr = T.compose(fr, L, shadow=0.0, glow=0.0)
    return fr


# ============================================================== 直垂挂轴
LAW = '天理纲常尊卑上下君臣父子忠孝节义礼法律令不得违者斩逆者诛顺天承命奉天行道刑名正统'


class Scrolls:
    """直垂挂轴（装裱：天头地头深绢、轴杆、竖排律令小字）。每轴是刚体：只绕顶点微摆（≤1.2°），绝不拉伸变形。
    draw(fr, t, ..., cut=(p0,p1,ts)) → 被斩后线下部分断开、下坠、断口烧红。"""
    def __init__(self, seed, n, x_span, top, length, width, text_size=None, big=None, tone=(0.93, 0.87, 0.74), blank=False):
        r = np.random.default_rng(seed)
        self.items = []
        xs = np.linspace(x_span[0], x_span[1], n) + r.uniform(-0.25, 0.25, n) * (x_span[1] - x_span[0]) / max(1, n)
        for i in range(n):
            w = int(r.uniform(*width)); L = int(r.uniform(*length)); tp = top + r.uniform(-30, 30)
            img, a = self._make(w, L, r, text_size, big[i] if big and i < len(big) else None, tone, blank)
            self.items.append(dict(x=float(xs[i]), top=float(tp), w=w, L=L, img=img, a=a, ph=r.uniform(0, 6.28),
                                   amp=r.uniform(0.4, 1.2), fq=r.uniform(0.9, 1.6)))

    @staticmethod
    def _make(w, L, r, ts, big, tone, blank=False):
        img = np.ones((L, w, 3), np.float32) * np.array(tone, np.float32)
        n = cv2.resize(K.fbm(max(8, L // 4), max(8, w // 4), int(r.integers(1e6)), base=6, octaves=4), (w, L))
        fib = cv2.resize(K.fbm(max(8, L // 2), max(8, w // 2), int(r.integers(1e6)), base=40, octaves=2), (w, L))
        img *= (0.86 + 0.16 * n + 0.06 * (fib - 0.5))[..., None]
        silk = np.array([0.30, 0.20, 0.13], np.float32)
        hb = int(L * 0.12); fb = int(L * 0.08); sb = max(4, int(w * 0.07))
        img[:hb] = silk * (0.8 + 0.3 * n[:hb, :, None]); img[L - fb:] = silk * (0.8 + 0.3 * n[L - fb:, :, None])
        img[:, :sb] = silk * 0.9; img[:, w - sb:] = silk * 0.9
        img[hb - 3:hb] = 0.75 * np.array([0.8, 0.62, 0.3], np.float32); img[L - fb:L - fb + 3] = 0.75 * np.array([0.8, 0.62, 0.3], np.float32)
        # 字：大字（题字）或竖排律令小字
        ink = np.zeros((L, w), np.float32)
        if big:
            s = int(w * 0.62); y = hb + s * 0.8
            for ch in big:
                gl = T.glyph(ch, 'xing', s, False); g = gl.shape[0]
                x0, y0 = int(w / 2 - g / 2), int(y - g / 2)
                xs, ys = max(0, x0), max(0, y0); xe, ye = min(w, x0 + g), min(L - fb, y0 + g)
                if xe > xs and ye > ys: ink[ys:ye, xs:xe] = np.maximum(ink[ys:ye, xs:xe], gl[ys - y0:ye - y0, xs - x0:xe - x0])
                y += s * 1.05
        elif not blank:
            s = ts or max(14, int(w * 0.16)); ncol = max(1, int((w - 2 * sb) / (s * 1.5)))
            for c in range(ncol):
                x = w - sb - s * 0.9 - c * s * 1.5; y = hb + s
                while y < L - fb - s:
                    ch = LAW[int(r.integers(len(LAW)))]
                    gl = T.glyph(ch, 'song', s, False); g = gl.shape[0]
                    x0, y0 = int(x - g / 2), int(y - g / 2)
                    xs, ys = max(0, x0), max(0, y0); xe, ye = min(w, x0 + g), min(L, y0 + g)
                    if xe > xs and ye > ys: ink[ys:ye, xs:xe] = np.maximum(ink[ys:ye, xs:xe], gl[ys - y0:ye - y0, xs - x0:xe - x0])
                    y += s * 1.12
        img = img * (1 - 0.85 * ink[..., None]) + 0.04 * ink[..., None]
        # 朱印
        if r.random() < 0.6 and not blank:
            ss = max(10, int(w * 0.22)); y0 = L - fb - ss - 10; x0 = sb + 6
            img[y0:y0 + ss, x0:x0 + ss] = img[y0:y0 + ss, x0:x0 + ss] * 0.3 + np.array([0.62, 0.08, 0.05], np.float32) * 0.7
        # 轴杆（上下）
        rod = np.zeros((L, w), np.float32)
        a = np.ones((L, w), np.float32)
        a = np.pad(a, ((10, 18), (14, 14))); img = np.pad(img, ((10, 18), (14, 14), (0, 0)))
        LL, WW = a.shape
        yy = np.arange(LL)[:, None]
        for y0, hh in ((0, 14), (LL - 22, 22)):
            band = (yy >= y0) & (yy < y0 + hh)
            sh = np.cos((yy - y0 - hh / 2) / hh * math.pi)
            a[band[:, 0]] = 1
            img[band[:, 0]] = (np.array([0.20, 0.12, 0.07], np.float32) * (0.5 + 0.9 * np.clip(sh[band[:, 0]], 0, 1)))[:, None, :]
        a[10:LL - 22, :14] = 0; a[10:LL - 22, WW - 14:] = 0
        a = cv2.GaussianBlur(a, (0, 0), 0.7)
        return img, a

    def layer(self, t, wind=1.0, dx=0.0, scale=1.0, cx=W / 2, cy=H / 2):
        """返回 (C, A) 全幅图层。"""
        C = np.zeros((H, W, 3), np.float32); A = np.zeros((H, W), np.float32)
        for it in self.items:
            ang = it['amp'] * wind * math.sin(t * it['fq'] + it['ph'])
            hx = cx + (it['x'] + dx - cx) * scale; hy = cy + (it['top'] - cy) * scale
            LL, WW = it['a'].shape
            M = cv2.getRotationMatrix2D((WW / 2, 0), ang, scale)
            M[0, 2] += hx - WW / 2; M[1, 2] += hy
            a = cv2.warpAffine(it['a'], M, (W, H)); c = cv2.warpAffine(it['img'], M, (W, H))
            C = C * (1 - a[..., None]) + c * a[..., None]; A = A + a * (1 - A)
        return C, A

    @staticmethod
    def light(C, A, back, backlit=0.8, light=GOLD, blur=0.0):
        """背光：纸透光（背景亮处纸更亮、偏暖），边缘一圈逆光。"""
        lum = back.mean(-1, keepdims=True)
        out = C * (0.55 + backlit * 0.6 * np.clip(lum, 0, 1.5)) + np.asarray(light, np.float32) * 0.12 * backlit * lum
        rim = np.clip(A - cv2.erode(A, np.ones((5, 5), np.uint8)), 0, 1)[..., None]
        out = out + rim * np.asarray(light, np.float32) * 0.5 * backlit
        if blur > 0.5:
            out = cv2.GaussianBlur(out * A[..., None], (0, 0), blur); A = cv2.GaussianBlur(A, (0, 0), blur)
            out = out / np.maximum(A[..., None], 1e-3)
        return out, A


def comp(fr, C, A, k=1.0):
    return fr * (1 - A[..., None] * k) + C * A[..., None] * k


def cut_layer(C, A, p0, p1, q, fall=1.0, side=1):
    """沿 p0→p1 线断开图层：线一侧（side）的部分下坠 + 微转；断口烧红。q=被斩后秒数。返回 (C, A, ember)。"""
    yy, xx = E.grid()
    d = np.array(p1, np.float32) - np.array(p0, np.float32); d /= np.linalg.norm(d)
    s = (xx - p0[0]) * d[1] - (yy - p0[1]) * d[0]
    lo = (s * side > 0).astype(np.float32)
    lo = cv2.GaussianBlur(lo, (0, 0), 0.8)
    dy = 0.5 * 2400 * q * q * fall + 40 * q; rot = -6 * q * fall * side
    c = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    M = cv2.getRotationMatrix2D(c, rot, 1.0); M[1, 2] += dy; M[0, 2] += 30 * q * side
    Al = cv2.warpAffine(A * lo, M, (W, H)); Cl = cv2.warpAffine(C, M, (W, H))
    Au = A * (1 - lo)
    edge = np.exp(-(s / 4) ** 2)
    em = (Au + Al) * 0 + (edge * A + cv2.warpAffine(edge * A, M, (W, H))) * math.exp(-q / 0.6)
    An = Au + Al * (1 - Au)
    Cn = (C * Au[..., None] + Cl * (Al * (1 - Au))[..., None]) / np.maximum(An[..., None], 1e-4)
    return Cn, An, em


# ============================================================== 有厚度的纸片 / 金箔
class Shreds:
    """3D 翻转的碎纸 / 金箔：不规则撕边多边形（7–11 顶点 + 撕口抖动），纸面有纤维纹理与明暗渐变，金箔有皱褶高光；
    焦边 + 余烬边线；按深度分三层虚化（前景大片强虚化）。只在每片包围盒内运算。"""
    def __init__(self, seed, n=80, gold=0.35, size=(30, 120), spread=(1400, 700), zr=(0.4, 3.0)):
        r = np.random.default_rng(seed)
        self.P = []
        for i in range(n):
            k = int(r.integers(7, 12))
            ang = np.sort(r.uniform(0, 2 * math.pi, k)); rad = r.uniform(0.6, 1.0, k)
            rad = rad * (1 + 0.12 * np.sin(ang * r.integers(3, 7) + r.uniform(0, 6)))
            self.P.append(dict(v=np.stack([np.cos(ang) * rad, np.sin(ang) * rad * r.uniform(0.55, 1.0)], 1), s=r.uniform(*size),
                               x=r.uniform(-1, 1) * spread[0], y=r.uniform(-1, 1) * spread[1], z=r.uniform(*zr),
                               vx=r.uniform(-60, 60), vy=r.uniform(-30, 60), vz=-r.uniform(0.3, 0.9),
                               rx=r.uniform(0, 6.28), ry=r.uniform(0, 6.28), wx=r.uniform(-3, 3), wy=r.uniform(-3, 3), wz=r.uniform(-2, 2),
                               gold=r.random() < gold, tone=r.uniform(0.85, 1.05), burn=r.uniform(0.2, 1.0), gd=r.uniform(0, 6.28)))
        self.tex = cv2.resize(K.fbm(H // 2, W // 2, seed + 9, base=30, octaves=4), (W, H))
        self.crin = cv2.resize(K.fbm(H // 2, W // 2, seed + 10, base=90, octaves=3), (W, H))

    def draw(self, fr, t, c=(W / 2, H / 2), f=900.0, to_cam=1.0, light=(0.3, -0.6, -0.75), paper=(0.93, 0.86, 0.70),
             gold=(1.0, 0.78, 0.42), amt=1.0, dof=(1.0, 9.0), zfocus=1.4, emb=1.0, tint_back=(0.25, 0.18, 0.12), znear=0.15):
        lv = np.array(light, np.float32); lv /= np.linalg.norm(lv)
        layers = [np.zeros((H, W, 3), np.float32) for _ in range(3)]; alph = [np.zeros((H, W), np.float32) for _ in range(3)]
        ems = [np.zeros((H, W), np.float32) for _ in range(3)]
        items = []
        for p in self.P:
            z = p['z'] + p['vz'] * t * to_cam
            if z < znear: continue
            items.append((z, p, p['x'] + p['vx'] * t, p['y'] + p['vy'] * t, p['rx'] + p['wx'] * t, p['ry'] + p['wy'] * t, p['wz'] * t))
        items.sort(key=lambda q: -q[0])
        for (z, p, x, y, rx, ry, rz) in items:
            v = p['v'] * p['s']
            cz, sz = math.cos(rz), math.sin(rz)
            v = v @ np.array([[cz, sz], [-sz, cz]], np.float32)
            cyy = math.cos(ry); cxx = math.cos(rx)
            X = v[:, 0] * (0.25 + 0.75 * abs(cyy)) * np.sign(cyy or 1); Y = v[:, 1] * (0.25 + 0.75 * abs(cxx))
            nrm = np.array([math.sin(ry), -math.sin(rx), cxx * cyy], np.float32)
            pts = np.stack([c[0] + (x + X) / z, c[1] + (y + Y) / z], 1)
            x0, y0 = np.floor(pts.min(0)).astype(int) - 4; x1, y1 = np.ceil(pts.max(0)).astype(int) + 4
            x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(W, x1), min(H, y1)
            if x1 - x0 < 2 or y1 - y0 < 2: continue
            m = np.zeros((y1 - y0, x1 - x0), np.float32)
            ip = (pts - [x0, y0]).astype(np.int32)
            cv2.fillPoly(m, [ip], 1.0, cv2.LINE_AA)
            front = nrm[2] > 0
            ndl = abs(float(nrm @ lv))
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            grad = 0.8 + 0.35 * np.sin(((xx - pts[:, 0].mean()) * math.cos(p['gd']) + (yy - pts[:, 1].mean()) * math.sin(p['gd'])) / max(8, p['s'] / z) )
            tx = self.tex[y0:y1, x0:x1]
            if p['gold']:
                cr = self.crin[y0:y1, x0:x1]
                spec = np.clip(ndl * (0.6 + 0.8 * cr), 0, 1.4) ** 6
                col = np.asarray(gold, np.float32) * ((0.3 + 0.5 * ndl) * (0.7 + 0.6 * cr) * grad)[..., None] + spec[..., None] * (1.2 if z > 1.0 else 0.35)
                col = np.minimum(col, 1.3 if z > 1.0 else 0.9)
            else:
                base = np.asarray(paper, np.float32) * p['tone'] if front else np.asarray(paper, np.float32) * np.asarray(tint_back, np.float32) * 2.2
                col = base * ((0.45 + 0.55 * ndl) * (0.8 + 0.35 * tx) * grad)[..., None]
                ink = np.clip((tx - 0.62) * 6, 0, 1) * 0.0
                col = col * (1 - ink[..., None])
            li = 0 if z > zfocus * 1.6 else (1 if z > zfocus * 0.55 else 2)
            Lc, La = layers[li][y0:y1, x0:x1], alph[li][y0:y1, x0:x1]
            Lc[:] = Lc * (1 - m[..., None]) + col * m[..., None]; np.maximum(La, m, out=La)
            if not p['gold']:
                e_ = np.zeros_like(m); cv2.polylines(e_, [ip], True, 1.0, max(1, int(4 / z)), cv2.LINE_AA)
                Lc[:] = Lc * (1 - 0.85 * e_[..., None] * m[..., None])
                np.maximum(ems[li][y0:y1, x0:x1], e_ * m * float(p['burn'] * emb) * (0.4 + 0.6 * tx), out=ems[li][y0:y1, x0:x1])
        out = fr
        for li, sig in zip((0, 1, 2), (dof[0], 0.0, dof[1])):
            Cc, Aa, em = layers[li], alph[li], ems[li]
            if Aa.max() <= 0: continue
            if sig > 0.5:
                Cc = cv2.GaussianBlur(Cc * Aa[..., None], (0, 0), sig); Aa = cv2.GaussianBlur(Aa, (0, 0), sig)
                Cc = Cc / np.maximum(Aa[..., None], 1e-3); em = cv2.GaussianBlur(em, (0, 0), sig) * 0.6
            else: em = cv2.GaussianBlur(em, (0, 0), 1.0)
            out = out * (1 - Aa[..., None] * amt) + Cc * Aa[..., None] * amt
            out = out + (em * 1.3 + cv2.GaussianBlur(em, (0, 0), 6) * 1.2)[..., None] * np.array([1.0, 0.45, 0.12], np.float32) * amt
        return out


# ============================================================== 碑林纵深
class SteleHall:
    """一点透视碑林：两列石碑沿纵深排开（碑面刻律令、阴刻受光），石板地面透视、远端门洞冷白晨光、纵深雾。镜头推轨前进。"""
    def __init__(self, seed=31, n=7, hy=430, f=900.0, camh=520.0, fog=(0.42, 0.48, 0.56)):
        r = np.random.default_rng(seed)
        self.hy, self.f, self.camh, self.fog = hy, f, camh, np.array(fog, np.float32)
        self.st = []
        for i in range(n):
            for side in (-1, 1):
                z = 2.2 + i * 2.2 + r.uniform(-0.3, 0.3)
                self.st.append(dict(x=side * r.uniform(1.25, 1.5), z=z, w=r.uniform(0.75, 0.95), h=r.uniform(2.1, 2.6), side=side,
                                    tex=stone_tex(r)))
        g = 1024
        n1 = K.fbm(g, g, seed + 3, base=6, octaves=5); n2 = K.fbm(g, g, seed + 4, base=24, octaves=3)
        gx = (np.arange(g) % 128 < 3)[None, :] | (np.arange(g) % 128 < 3)[:, None]
        self.floor = (0.07 + 0.09 * n1 + 0.04 * n2 - gx * 0.045).astype(np.float32)

    @staticmethod
    def _tex(r, tw=300, th=760):
        n = K.fbm(th // 2, tw // 2, int(r.integers(1e6)), base=5, octaves=6)
        n = cv2.resize(n, (tw, th))
        base = (0.17 + 0.20 * n)[..., None] * np.array([0.82, 0.86, 0.92], np.float32)
        ink = np.zeros((th, tw), np.float32)
        s = 34; ncol = 4
        for c in range(ncol):
            x = tw - 50 - c * 60; y = 120
            while y < th - 60:
                ch = LAW[int(r.integers(len(LAW)))]
                gl = T.glyph(ch, 'song', s, False); g = gl.shape[0]
                x0, y0 = int(x - g / 2), int(y - g / 2)
                ink[y0:y0 + g, x0:x0 + g] = np.maximum(ink[y0:y0 + g, x0:x0 + g], gl[:min(g, th - y0), :min(g, tw - x0)])
                y += s * 1.15
        # 碑额大字
        for k, ch in enumerate('天理'):
            gl = T.glyph(ch, 'serif_black', 64, False); g = gl.shape[0]
            x0, y0 = int(tw / 2 - g / 2 + (k - 0.5) * 70), int(60 - g / 2)
            ink[max(0, y0):y0 + g, x0:x0 + g] = np.maximum(ink[max(0, y0):y0 + g, x0:x0 + g], gl[max(0, -y0):, :])
        hl = np.clip(np.roll(ink, 2, 0) - ink, 0, 1); sh = np.clip(ink - np.roll(ink, 2, 0), 0, 1)
        img = base * (1 - 0.55 * ink[..., None]) + hl[..., None] * 0.25 - sh[..., None] * 0.1
        brd = np.ones((th, tw), np.float32); brd[:8] = brd[-8:] = 0.6; brd[:, :8] = brd[:, -8:] = 0.7
        return np.clip(img * brd[..., None], 0, 1)

    def render(self, t, dz=0.0, sway=0.0):
        hy, f, camh = self.hy, self.f, self.camh
        cx = W / 2 + sway
        yy, xx = E.grid()
        # 天/门洞：远端冷白晨光
        d = np.hypot((xx - cx) / 1.0, (yy - hy) * 1.6)
        sky = np.exp(-d / 260)[..., None] * np.array([1.0, 0.98, 0.94], np.float32) * 1.3 + self.fog * 0.35
        fr = np.broadcast_to(sky, (H, W, 3)).astype(np.float32).copy()
        top = sstep(0, hy, yy)[..., None]
        fr = fr * (0.25 + 0.75 * top)
        # 地面
        below = yy > hy + 1
        z = np.where(below, f * camh / 1000 / np.maximum(yy - hy, 1), 1e3)
        X = (xx - cx) * z / f * 1000
        u = ((X / 3 + 4096) % 1024).astype(np.float32); v = ((z * 1000 / 3 + dz * 1000 / 3) % 1024).astype(np.float32)
        fl = cv2.remap(self.floor, u, v, cv2.INTER_LINEAR)
        fog = np.clip(1 - np.exp(-z / 9), 0, 1)
        flc = fl[..., None] * np.array([0.85, 0.90, 1.0], np.float32)
        refl = np.exp(-np.abs(xx - cx) / 160)[..., None] * np.exp(-(yy - hy) / 200)[..., None] * 0.45   # 地面反光（湿石板）
        flc = flc + refl * np.array([0.9, 0.92, 0.95], np.float32)
        fl3 = flc * (1 - fog[..., None]) + self.fog * fog[..., None]
        fr = np.where(below[..., None], fl3, fr)
        # 石碑（由远到近）
        for s in sorted(self.st, key=lambda s: -(s['z'] - dz)):
            zz = s['z'] - dz
            if zz < 0.35: continue
            x0 = s['x'] - s['w'] / 2 * (1 if s['side'] > 0 else 1); x1 = x0 + s['w']
            def P(X, Y, Z): return (cx + X * f / Z, hy + (camh / 1000 - Y) * f / Z)
            zb = zz + 0.0
            q = np.float32([P(x0, s['h'], zb), P(x1, s['h'], zb), P(x1, 0, zb), P(x0, 0, zb)])
            th, tw = s['tex'].shape[:2]
            M = cv2.getPerspectiveTransform(np.float32([[0, 0], [tw, 0], [tw, th], [0, th]]), q)
            img = cv2.warpPerspective(s['tex'], M, (W, H)); a = cv2.warpPerspective(np.ones((th, tw), np.float32), M, (W, H))
            # 侧面（朝通道一侧，厚度）
            th2 = 0.22
            xs_in = x0 if s['side'] > 0 else x1
            q2 = np.float32([P(xs_in, s['h'], zb), P(xs_in, s['h'], zb + th2), P(xs_in, 0, zb + th2), P(xs_in, 0, zb)])
            m2 = np.zeros((H, W), np.float32); cv2.fillConvexPoly(m2, q2.astype(np.int32), 1.0, cv2.LINE_AA)
            fz = np.clip(1 - math.exp(-zz / 9), 0, 1)
            side_col = np.array([0.05, 0.055, 0.065], np.float32) * (1 - fz) + self.fog * fz * 0.7
            fr = fr * (1 - m2[..., None]) + side_col * m2[..., None]
            # 碑面受光：越近通道中线越亮（门洞光），加冷边光
            lit = np.clip(1.2 - abs(s['x']) * 0.5, 0.4, 1.0)
            img = img * (0.6 + 0.6 * (1 - fz)) * lit * (1 - fz) + self.fog * fz
            rim = np.clip(a - cv2.erode(a, np.ones((3, 3), np.uint8)), 0, 1)[..., None] * 0.6 * (1 - fz) * np.array([0.85, 0.92, 1.0], np.float32)
            if zz < 1.6:
                bl = (1.6 - zz) * 6
                img = cv2.GaussianBlur(img * a[..., None], (0, 0), bl + 0.1); a = cv2.GaussianBlur(a, (0, 0), bl + 0.1)
                img = img / np.maximum(a[..., None], 1e-3)
            fr = fr * (1 - a[..., None]) + (img + rim) * a[..., None]
        return fr


# ============================================================== 透视地面（刀划的线 → 地平线）
class Ground:
    def __init__(self, seed=261, tone=(1.0, 0.8, 0.6)):
        g = 1024
        n1 = K.fbm(g, g, seed, base=8, octaves=6); cr = K.fbm(g, g, seed + 1, base=26, octaves=3)
        crack = np.clip(1 - np.abs(cr - 0.5) * 30, 0, 1)
        pb = np.clip((K.fbm(g, g, seed + 2, base=160, octaves=2) - 0.62) * 6, 0, 1)
        self.tex = (0.05 + 0.13 * n1 - crack * 0.04 + pb * 0.05).astype(np.float32)
        self.tone = np.array(tone, np.float32)

    def render(self, fr, hy, f=900.0, camh=1.0, dz=0.0, cx=W / 2, line=1.0, line_col=(1.0, 0.75, 0.4), cool=0.0, fog=(1.0, 0.8, 0.5)):
        yy, xx = E.grid()
        below = yy > hy + 0.5
        dy = np.maximum(yy - hy, 0.5)
        z = f * camh / dy
        X = (xx - cx) * z / f
        u = ((X * 90 + 4096 * 4) % 1024).astype(np.float32); v = ((z * 90 + dz * 90) % 1024).astype(np.float32)
        g = cv2.remap(self.tex, u, v, cv2.INTER_LINEAR)
        col = g[..., None] * self.tone
        fogk = np.clip(1 - np.exp(-z / 30), 0, 1)[..., None]
        col = col * (1 - fogk) + np.asarray(fog, np.float32) * fogk * 0.55
        if line > 0:
            wpx = 0.06 * f / z                                     # 线宽（世界 0.06）
            ln = np.exp(-((xx - cx) / np.maximum(wpx, 0.7)) ** 2)
            gl = np.exp(-((xx - cx) / np.maximum(wpx * 8, 2)) ** 2)
            lc = np.asarray(line_col, np.float32)
            col = col * (1 - 0.6 * ln[..., None] * line) + (ln * 1.6 + gl * 0.5)[..., None] * lc * line * (1 - 0.6 * fogk)
        return np.where(below[..., None], col, fr), z


# ============================================================== 暗色系转场（全部带前后镜元素，中间帧不发白）
def blade_black(A, B, p, angle=-20.0, width=180, seed=0):
    """刀光黑切：一道黑色刀身斜扫过画面，刃口一线金光；刀身前是 A、后是 B。中间帧 = A | 黑刃 | B。"""
    yy, xx = E.grid()
    a = math.radians(angle); nx, ny = math.cos(a), math.sin(a)
    s = (xx - W / 2) * nx + (yy - H / 2) * ny
    span = abs(W / 2 * nx) + abs(H / 2 * ny) + width
    pos = -span + 2 * span * eio(p)
    out = np.where((s < pos)[..., None], B, A)
    band = sstep(width * 0.5, width * 0.5 - 30, np.abs(s - pos + width * 0.5))
    edge = np.exp(-((s - pos) / 2.5) ** 2) * 2.0 + np.exp(-((s - pos) / 30) ** 2) * 0.5
    out = out * (1 - band[..., None] * 0.94) + band[..., None] * np.array([0.015, 0.012, 0.01], np.float32)
    return out + edge[..., None] * GOLDW


def seal_cover(A, B, p, center=(W / 2, H / 2), rot=-6.0, color=(0.70, 0.07, 0.05)):
    """印章盖屏：一枚朱红方印自中心压下扩大（印边斑驳），印框内是 B、框外是 A；p>0.75 印框出画。"""
    yy, xx = E.grid()
    a = math.radians(rot)
    u = (xx - center[0]) * math.cos(a) + (yy - center[1]) * math.sin(a)
    v = -(xx - center[0]) * math.sin(a) + (yy - center[1]) * math.cos(a)
    half = 40 + 1500 * eio(p) ** 1.6
    dd = np.maximum(np.abs(u), np.abs(v))
    nz = cv2.resize(K.fbm(H // 8, W // 8, 77, base=6, octaves=4), (W, H))
    inner = (dd < half - 26 + nz * 18).astype(np.float32)
    frame = ((dd < half + nz * 10) & (dd >= half - 26 + nz * 18)).astype(np.float32)
    inner = cv2.GaussianBlur(inner, (0, 0), 1.0); frame = cv2.GaussianBlur(frame, (0, 0), 1.0)
    out = A * (1 - inner[..., None]) + B * inner[..., None]
    shadow = np.exp(-np.maximum(dd - half, 0) / 60)[..., None] * (dd > half)[..., None] * 0.5
    out = out * (1 - shadow)
    return out * (1 - frame[..., None]) + np.asarray(color, np.float32) * (0.8 + 0.3 * nz)[..., None] * frame[..., None]


def ink_swallow(A, B, p, center=(W / 2, H / 2), seed=5, band=0.32):
    """墨晕吞屏：一圈浓墨带从一点洇开向外推，墨带外是 A、墨带内是 B（墨带里透出 B 的暗影 + 火色边）。
    任意中间帧都同时有 A、墨、B 三层，不会整屏发黑/发白。"""
    hs, ws = H // 4, W // 4
    y, x = np.mgrid[0:hs, 0:ws].astype(np.float32)
    d = np.hypot((x * 4 - center[0]) / W * 1.7, (y * 4 - center[1]) / H) + (K.fbm(hs, ws, seed, base=5, octaves=5) - 0.5) * 0.45
    d = cv2.resize(d, (W, H))
    r = -0.05 + (1.75 + band) * eio(p)
    outer = np.clip((d - r) * 10, 0, 1)                      # 1 = 还在 A
    inner = np.clip((r - band - d) * 10, 0, 1)               # 1 = 已是 B
    ink = np.array([0.018, 0.015, 0.016], np.float32)
    mid = ink + B * 0.35 + A * 0.22
    out = A * outer[..., None] + B * inner[..., None] + mid * np.clip(1 - outer - inner, 0, 1)[..., None]
    edge = np.exp(-((d - r) / 0.025) ** 2)
    return out + edge[..., None] * np.array([0.8, 0.38, 0.12], np.float32) * 0.6


def slide(img, dx, dy=0.0):
    """平移（镜像边界，不像 np.roll 那样在接缝处出现竖直硬边）。"""
    h, w = img.shape[:2]
    return cv2.warpAffine(img, np.float32([[1, 0, dx], [0, 1, dy]]), (w, h), borderMode=cv2.BORDER_REFLECT)


# =========================================================================================== 第四棒新增
def push_h(A, B, p, seam=(1.0, 0.45, 0.3), blur=40):
    """横推：B 自左推入、A 被推向右；中间帧 = B 的右半 | 发光接缝 | A 的左半（E16 金脸 vs E17 朱脸正面相对）。带水平动态模糊。"""
    e = eio(p); off = int(round(W * e))
    out = np.empty_like(A)
    out[:, off:] = A[:, :W - off] if off < W else A[:, :0]
    if off > 0: out[:, :off] = B[:, W - off:]
    v = abs(math.sin(math.pi * p))
    k = int(blur * v) | 1
    if k > 2: out = cv2.blur(out, (k, 1))
    xx = np.arange(W, dtype=np.float32)[None, :, None]
    g = np.exp(-((xx - off) / 3.0) ** 2) * 2.0 + np.exp(-((xx - off) / 40.0) ** 2) * 0.5
    return out + g * np.asarray(seam, np.float32) * v


def door_open(A, B, p, cx=960, col=GOLDW):
    """开门：A 沿竖缝 cx 一线金光裂开，两扇向左右滑出（带厚边阴影），露出身后的 B（B 从 1.06 拉回 1.0）。中间帧 = A 左扇 | B | A 右扇。"""
    e = eio(p) ** 1.3; d = int(round((W / 2 + 60) * e))
    z = 1.06 - 0.06 * e
    Bz = cv2.resize(B, None, fx=z, fy=z); y0 = (Bz.shape[0] - H) // 2; x0 = (Bz.shape[1] - W) // 2
    out = Bz[y0:y0 + H, x0:x0 + W].copy() * (0.55 + 0.45 * e)
    xx = np.arange(W, dtype=np.float32)[None, :, None]
    if d < W:
        L = A[:, d:cx] if cx - d > 0 else None
        if L is not None: out[:, :cx - d] = L
        if cx + d < W: out[:, cx + d:] = A[:, cx:W - d]
        sh = np.exp(-np.abs(xx - (cx - d)) / 50) * (xx > cx - d) + np.exp(-np.abs(xx - (cx + d)) / 50) * (xx < cx + d)
        out = out * (1 - 0.6 * sh * (d > 0))
        out = out + (np.exp(-((xx - (cx - d)) / 2.5) ** 2) + np.exp(-((xx - (cx + d)) / 2.5) ** 2)) * np.asarray(col, np.float32) * 1.5
    if p < 0.12: out = out + np.exp(-((xx - cx) / (4 + 200 * p)) ** 2) * np.asarray(col, np.float32) * 2.0
    return out


def _latin_up(word, size, color):
    """署名里的拉丁字母：直立横排（不旋转），按竖排列宽收字号。"""
    from PIL import Image, ImageDraw
    f = T._font('song', int(size * 0.5))
    w = int(f.getlength(word)) + 8; h = int(size * 0.9)
    im = Image.new('L', (w, h), 0); ImageDraw.Draw(im).text((w / 2, h / 2), word, font=f, fill=255, anchor='mm')
    return np.asarray(im).astype(np.float32) / 255


def credit_block_up(*a, **k):
    """T.credit_block 的 E 组版本：拉丁字母（Cait、AI）直立横排，不再顺时针旋转 90°。不改共享库行为（临时替换后立即还原）。"""
    orig = T._latin_vertical
    T._latin_vertical = _latin_up
    try:
        return T.credit_block(*a, **k)
    finally:
        T._latin_vertical = orig


def stone_tex(r, tw=380, th=960, law=None, s=42):
    """碑面石材（第四棒，替 SteleHall._tex）：大块 fbm + 细粒 + 斑点、雨水垂流痕、底部苔痕、裂纹、边缘磨损暗角、
    阴刻律令（受光上沿亮/下沿暗）、碑额「天理」朱砂填色（斑驳脱落）。"""
    seed = int(r.integers(1e6))
    n1 = cv2.resize(K.fbm(th // 4, tw // 4, seed, base=4, octaves=5), (tw, th))
    n2 = cv2.resize(K.fbm(th // 2, tw // 2, seed + 1, base=40, octaves=3), (tw, th))
    sp = (r.random((th, tw)) ** 18).astype(np.float32)
    lum = 0.20 + 0.16 * n1 + 0.06 * (n2 - 0.5) - 0.10 * sp
    rr = r.random((th, tw)).astype(np.float32)
    streak = cv2.GaussianBlur(rr, (0, 0), sigmaX=2.5, sigmaY=70)
    streak = np.clip((streak - streak.mean()) * 9, -1, 1)
    yv = np.linspace(0, 1, th, dtype=np.float32)[:, None]
    lum = lum - 0.07 * np.clip(streak, 0, 1) * (0.3 + 0.7 * yv) + 0.03 * np.clip(-streak, 0, 1)
    col = lum[..., None] * np.array([0.84, 0.87, 0.92], np.float32)
    moss = np.clip((cv2.resize(K.fbm(th // 4, tw // 4, seed + 2, base=8, octaves=4), (tw, th)) - 0.55) * 4, 0, 1) * sstep(0.55, 0.95, yv)
    col = col * (1 - 0.45 * moss[..., None]) + moss[..., None] * np.array([0.16, 0.18, 0.11], np.float32) * 0.45
    ink = np.zeros((th, tw), np.float32)
    LAWS = law or LAW
    for c in range(4):
        x = tw - 60 - c * 76; y = 170
        while y < th - 90:
            ch = LAWS[int(r.integers(len(LAWS)))]
            gl = T.glyph(ch, 'song', s, False); g = gl.shape[0]
            x0, y0 = int(x - g / 2), int(y - g / 2)
            ink[y0:y0 + g, x0:x0 + g] = np.maximum(ink[y0:y0 + g, x0:x0 + g], gl[:min(g, th - y0), :min(g, tw - x0)])
            y += s * 1.15
    red = np.zeros((th, tw), np.float32)
    for k, ch in enumerate('天理'):
        gl = T.glyph(ch, 'serif_black', 84, False); g = gl.shape[0]
        x0, y0 = int(tw / 2 - g / 2 + (k - 0.5) * 92), int(80 - g / 2)
        red[max(0, y0):y0 + g, x0:x0 + g] = np.maximum(red[max(0, y0):y0 + g, x0:x0 + g], gl[max(0, -y0):, :])
    ink = np.maximum(ink, red)
    wear = np.clip((n2 - 0.25) * 3, 0, 1)
    ink = ink * (0.65 + 0.35 * wear)
    hl = np.clip(np.roll(ink, 2, 0) - ink, 0, 1); sh = np.clip(ink - np.roll(ink, 2, 0), 0, 1)
    img = col * (1 - 0.6 * ink[..., None]) + hl[..., None] * 0.22 - sh[..., None] * 0.1
    cin = red * np.clip((n2 - 0.3) * 2.5, 0, 1) * (0.5 + 0.5 * n1)
    img = img * (1 - cin[..., None]) + cin[..., None] * np.array([0.42, 0.06, 0.04], np.float32)
    # 裂纹
    cr = np.zeros((th, tw), np.float32)
    for _ in range(int(r.integers(1, 4))):
        p = np.array([r.uniform(0, tw), r.uniform(0, th * 0.3)]); pts = [p.copy()]
        a = r.uniform(1.2, 1.9)
        for _k in range(int(r.integers(14, 30))):
            a += r.uniform(-0.5, 0.5); p = p + 18 * np.array([math.cos(a), math.sin(a)]); pts.append(p.copy())
        cv2.polylines(cr, [np.int32(pts)], False, 1.0, int(r.integers(1, 3)), cv2.LINE_AA)
    img = img * (1 - 0.6 * cr[..., None]) + np.roll(cr, 1, 1)[..., None] * 0.06
    # 边缘倒角：上/左受光、右/下暗；四边磨损
    ex = np.minimum(np.arange(tw), tw - 1 - np.arange(tw))[None, :].astype(np.float32)
    ey = np.minimum(np.arange(th), th - 1 - np.arange(th))[:, None].astype(np.float32)
    ed = np.minimum(ex, ey) + 6 * n2
    img = img * (0.72 + 0.28 * sstep(0, 26, ed))[..., None]
    img[:6] *= 1.35; img[:, :5] *= 1.2
    return np.clip(img, 0, 1)
