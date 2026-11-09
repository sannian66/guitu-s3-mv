"""All scenes of the MV, timeline, and lyric overlay. Pure procedural."""
import math, random, json, os
import numpy as np, cv2
from PIL import Image, ImageDraw
from fx import *
from proc import *
import render as R
from render import ShanShui, InkWipe, ease, eout, env, A_LOW, A_RMS, BEATS

ROOT = os.path.dirname(os.path.abspath(__file__))
INKC = (0.06, 0.06, 0.07)
GOLD = np.array([1.0, 0.76, 0.40], np.float32)
REDC = ('血', '刀')

# ------------------------------------------------------------------ lyric timing
def _lines():
    segs = json.load(open(os.path.join(ROOT, 'align.json')))['segments']
    out = []
    for s in segs:
        text = s['text'].strip()
        ct = []
        for w in s['words']:
            ws = w['word'].strip().replace(' ', '')
            if not ws: continue
            for k in range(len(ws)):
                ct.append(w['start'] + (w['end'] - w['start']) * k / len(ws))
        chars = list(text)
        times = []; j = 0
        for c in chars:
            if c == ' ': times.append(None); continue
            times.append(ct[min(j, len(ct) - 1)] if ct else s['start']); j += 1
        out.append(dict(text=text, times=times, start=s['start'], end=s['end']))
    for i, L in enumerate(out):
        nxt = out[i + 1]['start'] if i + 1 < len(out) else 999
        L['d0'] = L['start'] - 0.15
        L['d1'] = min(L['end'] + 0.7, nxt - 0.06)
    return out
LINES = _lines()

def CT(li, ch, nth=0):
    L = LINES[li]; k = -1
    for c, t in zip(L['text'], L['times']):
        if c == ch:
            k += 1
            if k == nth: return t
    return L['start']

def snap(t, tol=0.28):
    i = np.argmin(np.abs(BEATS - t))
    return float(BEATS[i]) if abs(BEATS[i] - t) < tol else t
def cut(li): return snap(LINES[li]['start'] - 0.2)

def reveal_of(L, t, speed=0.22):
    out = ease((t - (L['d1'] - 0.3)) / 0.3)
    r = []
    for c, tc in zip(L['text'], L['times']):
        if tc is None: r.append(0); continue
        r.append(eout((t - tc + 0.05) / speed) * (1 - out))
    return r

def red_idx(text, chars=REDC):
    return tuple(i for i, c in enumerate(text) if c in chars)

def lyric(fr, t, style, strength=1.0):
    if style is None: return fr
    for L in LINES:
        if L['d0'] <= t <= L['d1']:
            txt = L['text']; n = len(txt.replace(' ', ''))
            rev = reveal_of(L, t)
            if style == 'big':
                size = 150 if n <= 7 else (120 if n <= 9 else 100)
                rgb, al = text_layer(txt, F_BRUSH, size, rev, spacing=0.10, pos=(0.5, 0.74), red_idx=red_idx(txt), scale_in=0.35, blur_in=9)
                fr = under_grad(fr, 0.55, 0.45)
                fr = comp_text(fr, rgb, al, shadow=0.85, glowamt=0.22 * strength)
            elif style == 'ink':
                size = 80 if n <= 11 else 70
                rgb, al = text_layer(txt, F_BRUSH, size, rev, spacing=0.08, pos=(0.5, 0.80), color=INKC, red_idx=red_idx(txt), scale_in=0.2, blur_in=6)
                fr = comp_text(fr, rgb, al, shadow=0.0)
            else:
                size = 80 if n <= 11 else 70
                rgb, al = text_layer(txt, F_BRUSH, size, rev, spacing=0.08, pos=(0.5, 0.80), red_idx=red_idx(txt), scale_in=0.2, blur_in=6)
                fr = under_grad(fr, 0.6, 0.5)
                fr = comp_text(fr, rgb, al, shadow=0.85)
    return fr

# ------------------------------------------------------------------ helpers
def zoom_img(img, z, cx=0.5, cy=0.5, dx=0.0, dy=0.0, rot=0.0):
    M = cv2.getRotationMatrix2D((cx * W, cy * H), rot, z)
    M[0, 2] += dx; M[1, 2] += dy
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

def put_hero(fr, Hm, rim=0.35, rimcol=(1, 1, 1), body=0.008, blade_glow=0.6):
    if SPR is not None and SPR.hide_hero(_CUR[0], _CUR[1]): return fr   # SPRITE_MODE：代码人物让位给精灵
    Bh, Sh, Kh = Hm
    fr = fr * (1 - Bh[..., None]) + body * Bh[..., None]
    fr = fr * (1 - Sh[..., None]) + RED * 0.75 * Sh[..., None]
    fr = fr * (1 - Kh[..., None]) + 0.05 * Kh[..., None]
    fr += cv2.GaussianBlur(Kh, (0, 0), 6)[..., None] * blade_glow + (Kh * 0.9)[..., None] * np.array([0.9, 0.92, 1.0], np.float32)
    r = np.clip(Bh - cv2.GaussianBlur(Bh, (0, 0), 3), 0, 1) * 1.2
    fr += r[..., None] * rim * np.array(rimcol, np.float32)
    return fr

def bolt_mask(seed, x0, y0, x1, y1, depth=7):
    rng = np.random.default_rng(seed)
    L = np.zeros((H // 2, W // 2), np.float32)
    def seg(a, b, d, w):
        if d == 0:
            cv2.line(L, (int(a[0] / 2), int(a[1] / 2)), (int(b[0] / 2), int(b[1] / 2)), 1.0, max(1, int(w)), cv2.LINE_AA); return
        m = ((a[0] + b[0]) / 2 + rng.normal(0, 1) * abs(b[1] - a[1]) * 0.18, (a[1] + b[1]) / 2)
        seg(a, m, d - 1, w); seg(m, b, d - 1, w)
        if rng.random() < 0.18 and d > 2:
            e = (m[0] + rng.normal(0, 1) * 160, m[1] + abs(rng.normal(1, 0.5)) * 140)
            seg(m, e, d - 2, max(1, w - 1))
    seg((x0, y0), (x1, y1), depth, 2)
    return cv2.GaussianBlur(L, (0, 0), 0.8) * 1.5 + cv2.GaussianBlur(L, (0, 0), 10) * 5

def stamp_mask(text, size=320, seed=5):
    s = size
    im = Image.new('L', (s, s), 0); d = ImageDraw.Draw(im)
    d.rectangle([6, 6, s - 7, s - 7], fill=255)
    d.rectangle([22, 22, s - 23, s - 23], outline=0, width=6)
    f = font(F_SERIF, int(s * 0.36))
    if len(text) == 2:
        for k, c in enumerate(text):
            d.text((s / 2, s * 0.30 + k * s * 0.40), c, font=f, fill=0, anchor='mm')
    else:
        d.text((s / 2, s / 2), text, font=font(F_SERIF, int(s * 0.62)), fill=0, anchor='mm')
    m = np.asarray(im).astype(np.float32) / 255
    rng = np.random.default_rng(seed)
    rough = cv2.GaussianBlur(rng.random((s, s)).astype(np.float32), (0, 0), 1.6)
    big = cv2.resize(rng.random((12, 12)).astype(np.float32), (s, s), interpolation=cv2.INTER_CUBIC)
    return m * np.clip((rough * 0.6 + big * 0.4 - 0.25) * 4, 0, 1)

def paste_mask(fr, m, cx, cy, col, alpha=1.0, scale=1.0):
    if scale != 1.0:
        m = cv2.resize(m, (max(2, int(m.shape[1] * scale)), max(2, int(m.shape[0] * scale))))
    h, w = m.shape
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xs, ys, xe, ye = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xe <= xs or ye <= ys: return fr
    a = (m[ys - y0:ye - y0, xs - x0:xe - x0] * alpha)[..., None]
    fr[ys:ye, xs:xe] = fr[ys:ye, xs:xe] * (1 - a) + np.array(col, np.float32) * a
    return fr

def prog(t, s0, s1): return min(max((t - s0) / max(1e-3, s1 - s0), 0), 1)

# ------------------------------------------------------------------ scenes
class Army:
    def __init__(self):
        y = np.linspace(0, 1, H)[:, None, None]
        hz = np.exp(-((y - 0.5) / 0.16) ** 2)
        fr = (0.03 + 0.30 * hz + 0.05 * y).astype(np.float32) * np.ones((1, W, 3), np.float32) * np.array([0.95, 0.97, 1.02], np.float32)
        fr += fbm2(H, W, 4, 3, 7)[..., None] * 0.07
        layers, torches = army(W, H, rows=6, seed=5, horizon=0.56, front=0.8)
        for tt, L in layers:
            tone = 0.24 * (1 - tt) ** 1.5 + 0.012
            fog = mist(H, W, int(tt * 100) + 3)
            fr = fr * (1 - L[..., None]) + tone * L[..., None]
            fr += (fog * (1 - tt) * 0.05)[..., None]
        gl = np.zeros((H // 2, W // 2), np.float32)
        for (x, yy, s, tt) in torches:
            cv2.circle(gl, (int(x / 2), int(yy / 2)), max(1, int(3 * s)), 1, -1)
        self.gl = cv2.resize(cv2.GaussianBlur(gl, (0, 0), 2) * 1.5 + cv2.GaussianBlur(gl, (0, 0), 12) * 6, (W, H))[..., None] * np.array([1, 0.3, 0.08], np.float32) * 0.6
        self.bg = fr * (1 - 0.5 * np.clip((np.linspace(0, 1, H) - 0.8) / 0.2, 0, 1)[:, None, None])
        self.hero = hero(H, W, int(W * 0.27), int(H * 0.99), s=1.15, sword_ang=0.55, wind=0.4)
        self.rain = Rain(520, 4); self.emb = Embers(60, 2)
    def frame(self, t, dt, P, s0, s1):
        u = prog(t, s0, s1)
        fl = 0.8 + 0.2 * math.sin(t * 11) * math.sin(t * 7.3)
        fr = zoom_img(self.bg + self.gl * fl, 1.0 + 0.08 * ease(u), 0.55, 0.55)
        fr = self.rain.draw(fr, dt, 0.45)
        fr = put_hero(fr, self.hero)
        fr = self.emb.draw(fr, t, dt, 0.5)
        ca = 0
        for ts in P.get('slash', []):
            sp = (t - ts + 0.08) / 0.22
            fr = slash(fr, sp, angle=-12, cy=0.42, width=1.3)
            if 0 < t - ts < 0.3: ca = 2
        return fr, ca

class PaperScales:
    def __init__(self, seed=0):
        self.seed = seed
        self.bg = paper(seed=11 + seed)
        self.tex = fbm2(H, W, 8 + seed, 10, 6)
        self.tilt1 = -0.13 if seed == 0 else -0.2
        A, p1, p2, ch = balance(H, W, int(W * 0.42), int(H * 0.26), self.tilt1)
        rng = np.random.default_rng(3 + seed)
        sp = np.zeros((H, W), np.float32)
        for k in range(70):
            x = p1[0] + rng.normal(0, 70); yy = p1[1] + ch - 20 - abs(rng.normal(0, 40))
            cv2.circle(sp, (int(x), int(yy)), int(abs(rng.normal(9, 6))), 1, -1, cv2.LINE_AA)
        self.sp = np.clip(cv2.GaussianBlur(sp, (0, 0), 2) * 1.5, 0, 1) * (0.6 + 0.4 * self.tex)
        self.spn = fbm2(H, W, 40 + seed, 6, 4)
        self.drips = [(int(p1[0] + rng.normal(0, 60)), p1[1] + ch + 40, rng.uniform(80, 360), rng.uniform(3, 7), rng.uniform(0, 0.4)) for _ in range(6)]
    def frame(self, t, dt, P, s0, s1):
        k = t - s0
        tilt = self.tilt1 * eout(k / 1.4) + 0.025 * math.sin(k * 3.1) * math.exp(-k * 0.8)
        A, p1, p2, ch = balance(H, W, int(W * 0.42), int(H * 0.26), tilt)
        fr = self.bg * (1 - A[..., None] * (0.85 + 0.15 * self.tex[..., None])) + INK * A[..., None] * 0.9
        pr = ease((k - 1.0) / 2.0)
        if pr > 0:
            sp = self.sp * np.clip((pr * 1.4 - self.spn) * 6, 0, 1)
            D = np.zeros((H, W), np.float32)
            for (x, y0, l, w, d) in self.drips:
                q = ease((k - 1.4 - d) / 2.5)
                if q > 0: cv2.line(D, (x, int(y0)), (x, int(y0 + l * q)), 1, int(w), cv2.LINE_AA)
            sp = np.maximum(sp, D * 0.9)
            fr = fr * (1 - sp[..., None]) + RED * sp[..., None]
        fr = zoom_img(fr, 1.0 + 0.05 * ease(prog(t, s0, s1)), 0.42, 0.4)
        fr = seal(fr, '鬼屠', x=0.88, y=0.66, size=34, alpha=0.85 * ease(k / 0.5))
        return fr, 0

class Duel:
    def __init__(self):
        self.ss = ShanShui(5, moon=False)
        self.poses = [hero(H, W, int(W * 0.40), int(H * 1.04), s=1.55, sword_ang=0.45, wind=0.7, seed=1),
                      hero(H, W, int(W * 0.40), int(H * 1.04), s=1.55, sword_ang=-0.75, wind=0.9, seed=1)]
        self.rain = Rain(700, 7); self.rain2 = Rain(400, 8)
    def frame(self, t, dt, P, s0, s1):
        sl = P.get('slash', [])
        n = sum(1 for ts in sl if t >= ts)
        fr = self.ss.render(t + 30, 1.04 + 0.04 * prog(t, s0, s1), glow_amt=0.0) * 0.5
        fr = self.rain.draw(fr, dt, 0.6); fr = self.rain2.draw(fr, dt * 1.3, 0.35)
        fr = put_hero(fr, self.poses[n % 2], rim=0.45)
        ca = 0
        for i, ts in enumerate(sl):
            sp = (t - ts + 0.06) / 0.18
            fr = slash(fr, sp, angle=[-20, 16, -32][i % 3], cy=[0.42, 0.55, 0.48][i % 3], width=1.6)
            if 0 < t - ts < 0.12: fr = fr + 0.5 * (1 - (t - ts) / 0.12)
            if 0 < t - ts < 0.35: ca = 3
        return fr, ca

class Throne:
    def __init__(self):
        Wb, Hb = W, int(H * 1.25)
        self.Hb = Hb
        y, x = np.mgrid[0:Hb, 0:W].astype(np.float32)
        cx, cy0 = W * 0.5, Hb * 0.08
        self.ang = np.arctan2(x - cx, y - cy0 + 1)
        self.rd = np.sqrt((x - cx) ** 2 + (y - cy0) ** 2)
        self.rayp = fbm1(4096, 12, base=30, octaves=5)
        base = np.zeros((Hb, W, 3), np.float32) + 0.015
        base += fbm2(Hb, W, 13, 3, 6)[..., None] * 0.05
        # stairs in perspective
        S = np.zeros((Hb, W), np.float32)
        top, bot = Hb * 0.42, Hb * 0.98
        for i in range(34):
            q = i / 33
            yy = top + (bot - top) * q ** 1.7
            hw = W * (0.08 + 0.42 * q ** 1.2)
            cv2.line(S, (int(cx - hw), int(yy)), (int(cx + hw), int(yy)), 1, max(1, int(1 + 3 * q)), cv2.LINE_AA)
        st = np.zeros((Hb, W), np.float32)
        poly = np.array([[cx - W * 0.08, top], [cx + W * 0.08, top], [cx + W * 0.5, bot], [cx - W * 0.5, bot]], np.int32)
        cv2.fillPoly(st, [poly], 1, cv2.LINE_AA)
        self.stairs = st; self.steps = S
        # hall / throne silhouette at top
        T = np.zeros((Hb, W), np.float32)
        cv2.rectangle(T, (int(cx - 230), int(top - 260)), (int(cx + 230), int(top)), 1, -1)
        roof = []
        for i in range(41):
            q = i / 40 * 2 - 1
            roof.append([cx + q * 420, top - 260 - 90 * (1 - abs(q) ** 2.2) + 40 * abs(q) ** 6])
        roof = np.array(roof + [[cx + 300, top - 250], [cx - 300, top - 250]], np.int32)
        cv2.fillPoly(T, [roof], 1, cv2.LINE_AA)
        door = np.zeros_like(T)
        cv2.rectangle(door, (int(cx - 55), int(top - 170)), (int(cx + 55), int(top)), 1, -1)
        self.hall = T; self.door = door
        self.base = base
        self.hero = hero(Hb, W, int(cx), int(Hb * 0.97), s=0.42, sword_ang=0.6, wind=0.5)
        self.emb = Embers(120, 13)
    def frame(self, t, dt, P, s0, s1):
        u = prog(t, s0, s1)
        idx = ((self.ang / math.pi + 1) * 2048 + t * 25).astype(np.int32) % 4096
        rays = self.rayp[idx]
        rays = np.clip((rays - 0.45) * 3, 0, 1) * np.exp(-self.rd / 900)
        fr = self.base + rays[..., None] * GOLD * 0.75
        fr += (np.exp(-self.rd / 260) * 0.5)[..., None] * GOLD
        st = self.stairs[..., None]
        fr = fr * (1 - st * 0.85) + st * 0.03 + self.steps[..., None] * GOLD * 0.35 * (0.5 + 0.5 * np.exp(-self.rd / 700))[..., None]
        fr = fr * (1 - self.hall[..., None]) + 0.01 * self.hall[..., None]
        fr += self.door[..., None] * GOLD * (1.1 + 0.2 * math.sin(t * 9))
        fr = put_hero(fr, self.hero, rim=0.6, rimcol=GOLD)
        dy = -(self.Hb - H) * (1 - ease(u))
        M = np.float32([[1, 0, 0], [0, 1, dy]])
        fr = cv2.warpAffine(fr, M, (W, H))
        fr = zoom_img(fr, 1.0 + 0.05 * u, 0.5, 0.4)
        fr = self.emb.draw(fr, t, dt, 0.6)
        ca = 0
        for ts in P.get('vslash', []):
            sp = (t - ts + 0.06) / 0.2
            fr = slash(fr, sp, angle=-78, cy=0.5, width=1.8, color=(1.0, 0.35, 0.25))
            if 0 < t - ts < 0.3: ca = 3
        return fr, ca

SPLITS = {'我不信天不信命不信谁的理所应当': 7, '谁定好规则谁写好剧本提纲': 5, '谁的正义成了交易的暗箱': 4, '我不低头不认命不信什么大局为上': 7}

class Scroll:
    """pre-chorus: lines written as vertical calligraphy columns on paper"""
    def __init__(self, seed=0):
        self.bg = paper(seed=21 + seed)
        self.seed = seed
        rng = np.random.default_rng(seed)
        blot = np.zeros((H, W), np.float32)
        cx, cy = W * 0.22, H * 0.55
        cv2.circle(blot, (int(cx), int(cy)), 170, 1, -1)
        for k in range(30):
            a = rng.uniform(0, 6.28); r = rng.uniform(150, 290)
            cv2.circle(blot, (int(cx + math.cos(a) * r), int(cy + math.sin(a) * r)), int(rng.uniform(4, 26)), 1, -1)
        self.blot = cv2.GaussianBlur(blot, (0, 0), 3)
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / 300
        self.blotf = d * 0.7 + fbm2(H, W, 50 + seed, 6, 5) * 0.5
        self.blottex = fbm2(H, W, 60 + seed, 12, 5)
    def columns(self, lines):
        cols = []
        for li in lines:
            L = LINES[li]
            idx = [i for i, c in enumerate(L['text']) if c != ' ']
            n = len(idx)
            br = SPLITS.get(L['text'])
            if br: parts = [idx[:br], idx[br:]]
            else: parts = [idx] if n <= 8 else [idx[:(n + 1) // 2], idx[(n + 1) // 2:]]
            for p in parts: cols.append((li, p))
        return cols
    def frame(self, t, dt, P, s0, s1):
        fr = self.bg.copy()
        pb = ease((t - s0 - 0.3) / 7.0)
        if pb > 0:
            m = self.blot * np.clip((pb * 1.5 - self.blotf) * 5, 0, 1) * (0.75 + 0.25 * self.blottex)
            fr = fr * (1 - m[..., None]) + RED * 0.95 * m[..., None]
        fr = spr_hook(fr, t)          # SPRITE_MODE：精灵在竖排字之下
        cols = self.columns(P['lines'])
        nc = len(cols)
        step = 0.078
        x0 = 0.84
        size = 72
        for j, (li, p) in enumerate(cols):
            L = LINES[li]
            txt = ''.join(L['text'][i] for i in p)
            rev = [eout((t - L['times'][i] + 0.05) / 0.3) for i in p]
            if max(rev) <= 0: continue
            red = tuple(k for k, i in enumerate(p) if L['text'][i] in REDC)
            tot = len(txt) * size * 1.1
            rgb, al = text_layer(txt, F_BRUSH, size, rev, spacing=0.1, pos=(x0 - j * step, 0.135 + tot / 2 / H), vertical=True, color=INKC, red_idx=red, scale_in=0.12, blur_in=5)
            fr = comp_text(fr, rgb, al, shadow=0.0)
        ks = t - LINES[P['lines'][-1]]['end']
        if ks > 0:
            fr = seal(fr, '鬼屠', x=0.83 - nc * step, y=0.70, size=36, alpha=0.9 * min(1, ks / 0.08))
        dx = 30 - 60 * prog(t, s0, s1)
        fr = zoom_img(fr, 1.04 + 0.03 * prog(t, s0, s1), 0.55, 0.45, dx=dx)
        return fr, 0

class Blade:
    def __init__(self):
        bg = np.zeros((H, W, 3), np.float32) + 0.02
        bg += fbm2(H, W, 30, 3, 6)[..., None] * 0.06
        Bd, E, Hh = dao(H, W, int(W * 0.22), int(H * 0.58), math.radians(-12), length=1350, width=78)
        self.Bd, self.E, self.Hh = Bd, E, Hh
        u = np.linspace(0, 1, W)[None].astype(np.float32)
        self.u = u
        self.bev = np.clip(cv2.GaussianBlur(cv2.dilate(E, np.ones((19, 19), np.uint8)), (0, 0), 4) * 1.4, 0, 1) * Bd
        self.steel = (0.10 + 0.08 * fbm2(H, W, 31, 30, 4))
        self.heatmask = self.bev * np.clip((u - 0.2) * 1.3, 0, 1)
        self.heatglow = cv2.GaussianBlur(self.heatmask, (0, 0), 22)
        self.bg = bg
        self.hrim = np.clip(Hh - cv2.erode(Hh, np.ones((5, 5), np.uint8)), 0, 1)
        self.emb = Embers(220, 9)
    def frame(self, t, dt, P, s0, s1):
        h0, h1 = P.get('heat', (1, 1))
        u = prog(t, s0, s1)
        heat = h0 + (h1 - h0) * ease(u)
        heat *= 0.85 + 0.15 * env(A_LOW, t)
        sp = (t * 0.18) % 1.4 - 0.2
        spec = np.clip(1 - np.abs(self.u - sp) * 4, 0, 1) ** 2
        bev = self.bev[..., None]
        col = self.steel[..., None] * (1 - bev) + (0.35 + 0.5 * spec[..., None]) * bev
        Bd = self.Bd[..., None]
        fr = self.bg * (1 - Bd) + Bd * col * np.array([0.85, 0.88, 0.95], np.float32)
        fr += (self.heatmask * 0.85 * heat)[..., None] * np.array([1.0, 0.28, 0.05], np.float32)
        fr += (self.heatglow * 1.5 * heat)[..., None] * np.array([1.0, 0.3, 0.05], np.float32)
        fr += (self.E * (0.5 + 1.2 * spec))[..., None]
        fr = fr * (1 - self.Hh[..., None]) + 0.03 * self.Hh[..., None] + self.hrim[..., None] * 0.25
        fr = zoom_img(fr, 1.04 + 0.08 * u, 0.45, 0.55, dx=40 - 90 * u, rot=1.5 - 3 * u)
        fr = self.emb.draw(fr, t, dt, 0.5 + 0.9 * heat, energy=heat)
        return fr, (1 if heat > 0.8 else 0)

class DarkScales:
    def __init__(self):
        self.bg = (np.zeros((H, W, 3), np.float32) + 0.015) + fbm2(H, W, 70, 3, 6)[..., None] * 0.05
        self.bg += radial_glow(H, W, W * 0.5, H * 0.35, 380)[..., None] * GOLD * 0.35
        self.emb = Embers(120, 71)
    def frame(self, t, dt, P, s0, s1):
        k = t - s0
        tilt = 0.17 * math.sin(k * 1.9 + 0.6)
        A, p1, p2, ch = balance(H, W, int(W * 0.5), int(H * 0.24), tilt, span=480, chain=300, pan_r=140, lw=6)
        fr = self.bg * (1 - A[..., None]) + 0.01 * A[..., None]
        rim = np.clip(A - cv2.GaussianBlur(A, (0, 0), 4), 0, 1) * 1.5
        fr += rim[..., None] * GOLD * 0.9
        low = p1 if p1[1] > p2[1] else p2
        D = np.zeros((H // 2, W // 2), np.float32)
        rng = np.random.default_rng(int(k * 3) + 5)
        for j in range(14):
            t0 = j * 0.33
            q = (k - t0) % 4.6
            y = low[1] + ch + 20 + 900 * q * q
            x = low[0] + ((j * 53) % 180 - 90)
            if y < H: cv2.circle(D, (int(x / 2), int(y / 2)), 3, 1, -1, cv2.LINE_AA)
        D = cv2.resize(D, (W, H))
        fr = fr * (1 - D[..., None]) + RED * D[..., None]
        fr = zoom_img(fr, 1.02 + 0.05 * prog(t, s0, s1), 0.5, 0.45)
        fr = self.emb.draw(fr, t, dt, 0.5)
        return fr, 1

class Wall:
    def __init__(self):
        B = bricks(H, W, bw=260, bh=110) * 0.55 + fbm2(H, W, 77, 20, 6) * 0.06
        self.B = np.stack([B, B * 0.98, B * 1.02], -1).astype(np.float32)
        ang = math.radians(-62)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = (xx - W * 0.5) * math.sin(ang) - (yy - H * 0.5) * math.cos(ang)
        n = fbm2(H, W, 21, 30, 4) * 40 - 20
        a = np.abs(d + n)
        self.a = a
        self.e10 = np.exp(-a / 10); self.e90 = np.exp(-a / 90); self.e260 = np.exp(-a / 260)[..., None]
        self.hero = hero(H, W, 731, int(H * 0.90), s=0.85, sword_ang=0.5, wind=0.6)
        self.emb = Embers(300, 4)
    def frame(self, t, dt, P, s0, s1):
        mode = P.get('mode', 'crack'); k = t - s0; u = prog(t, s0, s1)
        low = env(A_LOW, t)
        ca = 1; shake = 0
        if mode == 'crack':
            c = 0.15 + 0.85 * ease(u); g = 1 + 4 * ease(u); L = 0.35 * c
            z = 1.0 + 0.06 * u
        elif mode == 'split':
            ts = P['ts']; q = eout((t - ts) / 0.45)
            c = 1.0; g = 5 + 75 * q; L = 0.35 + 0.9 * q
            z = 1.06 - 0.03 * q
            if 0 < t - ts < 0.5: shake = 18 * (1 - (t - ts) / 0.5); ca = 4
        else:
            c = 1.0; g = 130; L = 1.25 * P.get('gold', 1.0)
            z = 1.10 - 0.08 * ease(u)
        gap = np.clip(1 - self.a / g, 0, 1)[..., None]
        fr = self.B * (0.25 + 1.6 * L * self.e260 * np.array([1.0, 0.8, 0.55], np.float32))
        fr = fr * (1 - gap)
        light = (gap[..., 0] * 2.2 + self.e10 * 1.5 * c + self.e90 * 0.5 * L)[..., None] * GOLD * (0.9 + 0.2 * low)
        fr += light
        if mode == 'open':
            fr = put_hero(fr, self.hero, rim=0.9, rimcol=GOLD, blade_glow=0.3)
        fr = glow(fr, 0.6, 0.8)
        fr = zoom_img(fr, z, 0.5, 0.5, dx=random.uniform(-shake, shake), dy=random.uniform(-shake, shake))
        fr = self.emb.draw(fr, t, dt, 0.4 + (0.9 if mode != 'crack' else 0.3 * u), energy=low)
        return fr, ca

class Peak:
    """shan-shui with hero on a foreground cliff; night->dawn"""
    def __init__(self):
        self.ss = ShanShui(4)
        x = np.arange(W) / W
        n = fbm1(W, 17, base=6, octaves=7)
        top = H * (0.72 + 0.55 * np.abs(x - 0.3) ** 1.35 + 0.05 * (n - 0.5))
        y = np.arange(H)[:, None]
        self.cliff = np.clip((y - top[None]) / 2, 0, 1).astype(np.float32)
        self.ctex = fbm2(H, W, 18, 14, 6)
        hx = int(W * 0.3); hy = int(top[hx]) + 6
        self.hero = hero(H, W, hx, hy, s=0.42, sword_ang=0.6, wind=0.8)
        self.emb = Embers(90, 19)
    def frame(self, t, dt, P, s0, s1):
        d = P.get('dawn', 0.0)
        if isinstance(d, tuple): d = d[0] + (d[1] - d[0]) * ease(prog(t, s0, s1))
        fr = self.ss.render(t, 1.03 + 0.04 * math.sin(t * 0.05), glow_amt=0.45 + 0.2 * env(A_LOW, t), dawn=d)
        c = self.cliff[..., None]
        fr = fr * (1 - c) + c * (0.012 + 0.02 * self.ctex[..., None])
        fr += np.clip(self.cliff - cv2.GaussianBlur(self.cliff, (0, 0), 3), 0, 1)[..., None] * (0.15 + 0.3 * d) * np.array([1, 0.85, 0.7], np.float32)
        fr = put_hero(fr, self.hero, rim=0.4 + 0.5 * d, rimcol=(1, 0.85, 0.6))
        fr = self.emb.draw(fr, t, dt, 0.4 * (1 - d) + 0.2)
        ca = 0
        for ts in P.get('slash', []):
            sp = (t - ts + 0.06) / 0.22
            fr = slash(fr, sp, angle=-16, cy=0.45, width=2.2)
            if 0 < t - ts < 0.15: fr = fr + 0.6 * (1 - (t - ts) / 0.15)
            if 0 < t - ts < 0.4: ca = 3
        return fr, ca

class Stamp:
    def __init__(self):
        fr = paper(seed=31)
        layers, _ = army(W, H, rows=5, seed=8, horizon=0.50, front=0.70, torch=False)
        for tt, L in layers:
            tone = 0.80 * (1 - tt) + 0.30
            fr = fr * (1 - L[..., None] * (1 - tone))
        self.bg = fr
        self.masks = {}
    def frame(self, t, dt, P, s0, s1):
        fr = zoom_img(self.bg, 1.02 + 0.05 * prog(t, s0, s1), 0.5, 0.6)
        ca = 0
        for (ts, txt, x, y, s) in P['stamps']:
            k = t - ts
            if k < -0.12: continue
            if txt not in self.masks: self.masks[txt] = stamp_mask(txt, s, seed=len(self.masks) + 5)
            q = eout((k + 0.12) / 0.12)
            sc = 2.2 - 1.2 * q
            fr = paste_mask(fr, self.masks[txt], x * W, y * H, (0.72, 0.05, 0.04), alpha=0.92 * q, scale=sc)
            if 0 < k < 0.3: ca = 2
        return fr, ca

class Storm:
    def __init__(self):
        self.ss = ShanShui(7, moon=False)
        self.hero = hero(H, W, int(W * 0.5), int(H * 1.02), s=1.1, sword_ang=0.5, wind=1.0)
        self.rain = Rain(600, 11)
        self.cloud = fbm2(H // 2, W, 72, 4, 6)
        self.bolts = {}
    def frame(self, t, dt, P, s0, s1):
        fl = 0.0; bm = None
        for i, ts in enumerate(P.get('bolts', [])):
            k = t - ts
            if 0 <= k < 0.45:
                f = math.exp(-k / 0.09) + 0.5 * math.exp(-((k - 0.16) / 0.03) ** 2)
                fl = max(fl, f)
                if i not in self.bolts:
                    rng = np.random.default_rng(i + 40)
                    x0 = rng.uniform(0.2, 0.8) * W
                    self.bolts[i] = bolt_mask(i + 40, x0, H * 0.1, x0 + rng.normal(0, 200), H * 0.62)
                bm = (self.bolts[i], f)
        fr = self.ss.render(t + 60, 1.04, glow_amt=0.0) * (0.55 + 0.9 * fl)
        off = int(t * 60) % W
        cl = np.concatenate([self.cloud[:, off:], self.cloud[:, :off]], 1)
        cl = cv2.resize(cl, (W, H // 2))
        top = np.zeros((H, W), np.float32); top[:H // 2] = np.clip((cl - 0.4) * 1.5, 0, 1) * np.linspace(1, 0, H // 2)[:, None]
        fr = fr * (1 - top[..., None] * 0.6) + top[..., None] * 0.12 * (1 + 3 * fl)
        if bm is not None:
            fr += cv2.resize(bm[0], (W, H))[..., None] * bm[1] * np.array([0.85, 0.9, 1.0], np.float32)
        fr = self.rain.draw(fr, dt, 0.5 + 0.5 * fl)
        fr = put_hero(fr, self.hero, rim=0.3 + 1.2 * fl)
        return fr, (2 if fl > 0.3 else 0)

class Invert:
    def __init__(self):
        self.ss = ShanShui(2)
        self.hero = hero(H, W, int(W * 0.62), int(H * 0.98), s=0.9, sword_ang=0.55, wind=0.5)
        ang = math.radians(-28)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.d = np.abs((xx - W * 0.5) * math.sin(ang) - (yy - H * 0.5) * math.cos(ang))
    def frame(self, t, dt, P, s0, s1):
        ts = P['ts']
        fr = self.ss.render(t, 1.06 - 0.04 * prog(t, s0, s1), glow_amt=0.5)
        fr = put_hero(fr, self.hero)
        ca = 0
        if t < ts:
            g = fr.mean(-1, keepdims=True)
            fr = np.clip(0.95 - g * 1.2, 0, 1) * np.array([0.98, 0.97, 0.94], np.float32)
        else:
            k = t - ts
            line = np.exp(-self.d / 2.0) * 1.2 + np.exp(-self.d / 14) * 0.5
            fr = fr + line[..., None] * np.array([0.85, 0.08, 0.05], np.float32) * (0.6 + 0.4 * math.exp(-k * 2))
            if k < 0.12: fr = fr + 0.7 * (1 - k / 0.12)
            if k < 0.4: ca = 3
        fr = slash(fr, (t - ts + 0.06) / 0.2, angle=-28, cy=0.5, width=2)
        return fr, ca

class Bridge:
    POS = [(0.47, 0.24), (0.53, 0.355), (0.47, 0.47), (0.53, 0.585), (0.47, 0.70), (0.53, 0.815)]
    def __init__(self):
        self.ss = ShanShui(9, moon=False)
        self.hero = hero(H, W, int(W * 0.5), int(H * 0.95), s=0.9, sword_ang=1.35, wind=0.9)
        self.rain = Rain(650, 12)
        self.bolt = bolt_mask(99, W * 0.7, H * 0.08, W * 0.62, H * 0.6)
    def frame(self, t, dt, P, s0, s1):
        slams = P['slams']  # [(line, t)]
        last = max([ts for (_, ts) in slams if t >= ts - 0.05], default=None)
        fl = 0
        if last is not None:
            k = t - last
            fl = math.exp(-max(k, 0) / 0.12)
        fr = self.ss.render(t + 90, 1.05, glow_amt=0.0) * (0.45 + 0.8 * fl)
        fr = self.rain.draw(fr, dt, 0.55)
        if fl > 0.2: fr += cv2.resize(self.bolt, (W, H))[..., None] * fl
        fr = put_hero(fr, self.hero, rim=0.3 + 1.0 * fl)
        fr = fr * 0.85 + 0.0
        fr = spr_hook(fr, t)          # SPRITE_MODE：精灵在排比叠字之下
        ca = 2 if fl > 0.3 else 0
        if last is None:
            act = [li for li in P['stack'] if LINES[li]['d0'] <= t]
            for j, li in enumerate(act):
                L = LINES[li]
                rev = [0 if tc is None else eout((t - tc + 0.05) / 0.22) for tc in L['times']]
                old = j < len(act) - 1 and t > L['end'] + 0.3
                age = (t - LINES[act[-1]]['start']) if old else 0
                col = (0.55, 0.53, 0.5) if old else (0.96, 0.94, 0.9)
                if old: rev = [r * max(0.45, 1 - age * 0.3) for r in rev]
                rgb, al = text_layer(L['text'], F_BRUSH, 70, rev, spacing=0.08, pos=self.POS[j % 6], color=col, red_idx=red_idx(L['text']), scale_in=0.3, blur_in=6)
                fr = comp_text(fr, rgb, al, shadow=0.8)
        else:
            li = [l for (l, ts) in slams if ts == last][0]
            L = LINES[li]
            rev = [0 if tc is None else eout((t - tc + 0.04) / 0.12) for tc in L['times']]
            out = ease((t - (s1 - 0.35)) / 0.3)
            rev = [r * (1 - out) for r in rev]
            red = tuple(i for i, c in enumerate(L['text']) if c in ('判', '答', '刀'))
            rgb, al = text_layer(L['text'], F_BRUSH, 190, rev, spacing=0.1, pos=(0.5, 0.5), red_idx=red, scale_in=0.6, blur_in=10)
            fr = comp_text(fr, rgb, al, shadow=0.9, glowamt=0.3)
        return fr, ca

class Edict:
    def __init__(self):
        bg = paper(seed=41, tone=np.array([0.80, 0.72, 0.58], np.float32))
        rng = np.random.default_rng(4)
        pool = ''.join(L['text'] for L in LINES).replace(' ', '')
        A = np.zeros((H, W), np.float32)
        for j in range(15):
            txt = ''.join(rng.choice(list(pool), 13))
            _, al = text_layer(txt, F_SERIF, 46, [1] * 13, spacing=0.25, pos=(0.92 - j * 0.058, 0.5), vertical=True)
            A = np.maximum(A, al)
        bg = bg * (1 - A[..., None] * 0.75) + np.array(INKC, np.float32) * A[..., None] * 0.75
        bg = paste_mask(bg, stamp_mask('诏', 300, 9), W * 0.2, H * 0.45, (0.72, 0.05, 0.04), alpha=0.85)
        self.bg = bg
        ang = math.radians(-70)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        n = (fbm2(H, W, 43, 25, 5) - 0.5) * 60
        self.sd = (xx - W * 0.5) * math.sin(ang) - (yy - H * 0.5) * math.cos(ang) + n
        self.nx, self.ny = math.sin(ang), -math.cos(ang)
        self.emb = Embers(260, 44)
    def frame(self, t, dt, P, s0, s1):
        ts = P['ts']; k = t - ts
        q = eout(k / 0.5) if k > 0 else 0
        o = 10 + 240 * q + (12 * k if k > 0 else 0)
        burn = np.exp(-np.abs(self.sd) / (6 + 25 * (ease((t - s0) / max(0.1, ts - s0)))))
        if k <= 0:
            fr = self.bg * (1 - burn[..., None] * 0.8)
            fr += (np.exp(-np.abs(self.sd) / 3) * ease((t - s0) / max(0.1, ts - s0)))[..., None] * GOLD
            fr = zoom_img(fr, 1.0 + 0.05 * prog(t, s0, ts), 0.5, 0.5)
            return fr, 0
        side = (self.sd > 0).astype(np.float32)[..., None]
        light = np.zeros((H, W, 3), np.float32) + GOLD * 0.9
        light += (np.exp(-np.abs(self.sd) / 200) * 1.2)[..., None] * GOLD
        Ma = np.float32([[1, 0, self.nx * o], [0, 1, self.ny * o]]); Mb = np.float32([[1, 0, -self.nx * o], [0, 1, -self.ny * o]])
        brn = self.bg * (1 - burn[..., None] * 0.8)
        A = cv2.warpAffine(brn * side, Ma, (W, H)); Am = cv2.warpAffine(side[..., 0], Ma, (W, H))[..., None]
        B = cv2.warpAffine(brn * (1 - side), Mb, (W, H)); Bm = cv2.warpAffine(1 - side[..., 0], Mb, (W, H))[..., None]
        fr = light * (1 - Am - Bm).clip(0, 1) + A + B
        fr = glow(fr, 0.7, 0.6)
        fr = self.emb.draw(fr, t, dt, 1.2 * math.exp(-k / 2) + 0.3, energy=1)
        if k < 0.12: fr = fr + 0.7 * (1 - k / 0.12)
        return fr, (4 if k < 0.4 else 1)

class Outro:
    ROLES = [('出品人', '西几王传媒'), ('后期总监', '沉溺'), ('编剧 / 导演', '苏打'), ('美术设计', 'Cait'), ('音乐', '西几王'), ('AI画师', '沉溺　雪晴　索恩')]
    def __init__(self, peak): self.peak = peak
    def frame(self, t, dt, P, s0, s1):
        fr, ca = self.peak.frame(t, dt, {'dawn': 1.0}, s0, s1)
        fr = fr * (1 - 0.35 * ease((t - s0) / 2.0))
        fr = spr_hook(fr, t)          # SPRITE_MODE：精灵在片名/署名之下
        a = ease((t - (s0 + 0.8)) / 1.0) * (1 - ease((t - 228.6) / 0.8))
        if a > 0:
            # 主标题「鬼屠 · 第二季」，副标题「主题曲《谁定正邪》」（与片头一致）
            for txt, x in (('鬼屠', 0.315), ('第二季', 0.595)):
                rgb, al = text_layer(txt, F_BRUSH, 150, [a] * len(txt), spacing=0.1, pos=(x, 0.45), scale_in=0, blur_in=6)
                fr = comp_text(fr, rgb, al, shadow=0.7)
            dot = np.zeros(fr.shape[:2], np.float32)
            cv2.circle(dot, (int(fr.shape[1] * 0.437), int(fr.shape[0] * 0.455)), 8, 1.0, -1, cv2.LINE_AA)
            dot = dot[..., None] * a
            fr = fr * (1 - dot) + dot * np.array([0.72, 0.08, 0.06], np.float32)
            sub = '主题曲《谁定正邪》'
            rgb, al = text_layer(sub, F_SERIF, 32, [a] * len(sub), spacing=0.35, pos=(0.5, 0.60), color=(0.85, 0.82, 0.76), scale_in=0, blur_in=3)
            fr = comp_text(fr, rgb, al, shadow=0.6)
            fr = seal(fr, '鬼屠', x=0.80, y=0.34, size=36, alpha=0.9 * a)
        b = ease((t - 229.4) / 1.0) * (1 - ease((t - 238.0) / 1.2))
        if b > 0:
            for j, (role, name) in enumerate(self.ROLES):
                y = 0.25 + j * 0.105
                rgb, al = text_layer(role, F_SERIF, 30, [b] * len(role), spacing=0.3, pos=(0.58, y), color=(0.82, 0.79, 0.74), scale_in=0, blur_in=3)
                fr = comp_text(fr, rgb, al, shadow=0.6)
                rgb, al = text_layer(name, F_BRUSH, 58, [b] * len(name), spacing=0.08, pos=(0.76, y), scale_in=0, blur_in=4)
                fr = comp_text(fr, rgb, al, shadow=0.7)
        fr = fr * (1 - ease((t - 239.0) / 2.0))
        return fr, 0

# ------------------------------------------------------------------ timeline
def build_timeline():
    CH1 = 12  # first line index of chorus 1
    def chorus(base, t_start, strength):
        return [
            (t_start, 'blade', 'big', dict(heat=(1, 1), flash=1, strength=strength)),
            (cut(base + 1), 'dscales', 'big', dict(strength=strength)),
            (cut(base + 2), 'wall', 'big', dict(mode='crack', strength=strength)),
            (cut(base + 3), 'wall', 'big', dict(mode='split', ts=CT(base + 3, '劈'), strength=strength)),
            (cut(base + 4), 'wall', 'big', dict(mode='open', strength=strength)),
            (cut(base + 6), 'peak', 'big', dict(dawn=0.0, slash=[CT(base + 7, '刀')], strength=strength)),
        ]
    T = [
        (0.0, 'intro', None, {}),
        (R.INTRO_END, 'army', 'bottom', dict(wipe=0.7, slash=[CT(1, '寒')])),
        (cut(3), 'pscales0', 'ink', {}),
        (cut(4), 'duel', 'bottom', dict(slash=[CT(4, '杀'), CT(4, '放'), CT(5, '拔')])),
        (cut(6), 'throne', 'bottom', dict(vslash=[CT(7, '锋')])),
        (cut(8), 'scroll0', None, dict(lines=[8, 9, 10], wipe=0.6)),
        (cut(11), 'blade', 'bottom', dict(heat=(0.1, 0.9))),
    ]
    T += chorus(12, LINES[12]['start'] - 0.04, 1.0)
    T += [
        (88.9, 'stamp', 'ink', dict(wipe=0.6, stamps=[(CT(20, '大'), '大局', 0.30, 0.36, 300), (CT(21, '权'), '权柄', 0.70, 0.40, 340)])),
        (cut(22), 'pscales1', 'ink', {}),
        (cut(24), 'storm', 'bottom', dict(bolts=[CT(24, '天'), CT(24, '苍'), CT(25, '命'), CT(25, '掌')])),
        (cut(26), 'invert', 'bottom', dict(ts=CT(27, '划'))),
        (cut(28), 'scroll1', None, dict(lines=[28, 29, 30], wipe=0.5)),
        (cut(31), 'blade', 'bottom', dict(heat=(0.1, 0.9))),
    ]
    T += chorus(32, LINES[32]['start'] - 0.04, 1.4)
    T += [
        (cut(40), 'bridge', None, dict(wipe=0.5, stack=[40, 41, 42, 43, 44, 45], slams=[(46, CT(46, '天')), (47, CT(47, '刀'))])),
        (LINES[48]['start'] - 0.04, 'blade', 'big', dict(heat=(1, 1), flash=1)),
        (cut(49), 'peak', 'big', dict(dawn=(0.15, 0.45))),
        (cut(50), 'edict', 'big', dict(ts=CT(51, '撕'))),
        (cut(52), 'wall', 'big', dict(mode='open', gold=1.3)),
        (cut(53), 'peak', 'big', dict(dawn=(0.5, 1.0), slash=[CT(55, '刀')])),
        (LINES[55]['end'] + 0.5, 'outro', None, {}),
    ]
    return T

TIMELINE = build_timeline()
SONG_END = 241.34

def make_scene(key, cache):
    if key in cache: return cache[key]
    if key == 'intro': s = R.Intro()
    elif key == 'army': s = Army()
    elif key.startswith('pscales'): s = PaperScales(int(key[-1]))
    elif key == 'duel': s = Duel()
    elif key == 'throne': s = Throne()
    elif key.startswith('scroll'): s = Scroll(int(key[-1]))
    elif key == 'blade': s = Blade()
    elif key == 'dscales': s = DarkScales()
    elif key == 'wall': s = Wall()
    elif key == 'peak': s = Peak()
    elif key == 'stamp': s = Stamp()
    elif key == 'storm': s = Storm()
    elif key == 'invert': s = Invert()
    elif key == 'bridge': s = Bridge()
    elif key == 'edict': s = Edict()
    elif key == 'outro': s = Outro(make_scene('peak', cache))
    cache[key] = s
    return s

def seg_at(t):
    i = 0
    for k, s in enumerate(TIMELINE):
        if s[0] <= t: i = k
    s0 = TIMELINE[i][0]; s1 = TIMELINE[i + 1][0] if i + 1 < len(TIMELINE) else SONG_END
    return i, s0, s1

def run_scene(i, t, dt, cache):
    s0 = TIMELINE[i][0]; s1 = TIMELINE[i + 1][0] if i + 1 < len(TIMELINE) else SONG_END
    key, style, P = TIMELINE[i][1], TIMELINE[i][2], TIMELINE[i][3]
    sc = make_scene(key, cache)
    _CUR[0], _CUR[1] = t, key; _HOOKED[0] = False
    if key == 'intro':
        fr, ca = sc.frame(t, dt)
    else:
        fr, ca = sc.frame(t, dt, P, s0, s1)
    fr = spr_hook(fr, t)          # 没在场景内部挂过的，在场景帧之后、字幕之前合成精灵
    return fr, ca, style, P, s0

# ---- SPRITE_MODE=1（2026-11-09 05:25 用户确认：人物 = 生图 + 抠图精灵）：副歌一以外的精灵镜头，见 units/rest_sprites.py
SPRITE_MODE = os.environ.get('SPRITE_MODE', '0') == '1'
SPR = None
_CUR = [0.0, None]; _HOOKED = [False]
def spr_hook(fr, t):
    if SPR is None or _HOOKED[0]: return fr
    _HOOKED[0] = True
    return SPR.apply(fr, t, _CUR[1])
if SPRITE_MODE:
    import sys as _sys; _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/units')
    import rest_sprites as SPR
    R.SPR_HOOK = spr_hook

_wipes = {}
def frame_at(t, dt, cache):
    i, s0, s1 = seg_at(t)
    fr, ca, style, P, s0 = run_scene(i, t, dt, cache)
    w = P.get('wipe', 0)
    if w and t - s0 < w and i > 0:
        pf, pca, pst, _, _ = run_scene(i - 1, t, dt, cache)
        pf = lyric(pf, t, pst)
        fr = lyric(fr, t, style)
        if i not in _wipes: _wipes[i] = InkWipe(i, 0.5, 0.5)
        m = _wipes[i].mask(eout((t - s0) / w))
        fr = pf * (1 - m) + fr * m
    else:
        fr = lyric(fr, t, style, P.get('strength', 1.0))
    if P.get('flash') and 0 <= t - s0 < 0.25:
        fr = fr + 0.8 * (1 - (t - s0) / 0.25)
    # beat punch on big chorus characters
    pz = 0.0
    if style == 'big':
        for L in LINES:
            if L['d0'] <= t <= L['d1']:
                for tc in L['times']:
                    if tc is not None and 0 <= t - tc < 0.3:
                        pz += 0.010 * math.exp(-(t - tc) / 0.08) * P.get('strength', 1.0)
    if pz > 0.0005:
        fr = zoom_img(fr, 1 + pz)
    return fr, ca
