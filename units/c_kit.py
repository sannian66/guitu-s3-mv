"""units/c_kit.py — C 组（预副歌二 + 副歌二「破」）工具箱：雷暴环境、精灵摆放、C 组字幕体系、相机。
只被 units/sec_c_pre2_chorus2.py 使用；不改任何共享库（只 import）。"""
import os, sys, math, json
ROOT = '/workspace/work/mv'
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, cv2
import typo as T
import fx2
import sprite as SP
from c1kit import fbm

W, H, FPS, BAR = 1920, 1080, 30, 120
RED = np.array([0.80, 0.07, 0.05], np.float32)
GOLD = np.array([1.0, 0.76, 0.40], np.float32)
COLD = np.array([0.82, 0.88, 1.0], np.float32)
WARM = np.array([1.0, 0.72, 0.42], np.float32)
for _k, _f in (('serif_r', 'Regular'), ('serif_m', 'Medium'), ('serif_sb', 'SemiBold'), ('serif_b', 'Bold'), ('serif_black', 'Black')):
    T.FONTS.setdefault(_k, ROOT + f'/fonts/NotoSerifSC-{_f}.otf')

LINES = T.load_lines()
HM = json.load(open(ROOT + '/crew/round4/C_hitmap.json'))


def clamp(x, a=0.0, b=1.0): return float(min(b, max(a, x)))
def sm(a, b, x):
    x = clamp((x - a) / (b - a)); return x * x * (3 - 2 * x)
def eout(x, k=3): x = clamp(x); return 1 - (1 - x) ** k
def ein(x, k=3): x = clamp(x); return x ** k
def eio(x): x = clamp(x); return x * x * (3 - 2 * x)
def lerp(a, b, x): return a + (b - a) * x
def V(t): return (round(t * FPS) - 1) / FPS            # 声音时刻 → 视觉帧（早 1 帧）
def pulse(t, t0, d=0.12): return math.exp(-(t - t0) / d) if t >= t0 else 0.0


def CT(li, k):
    """第 li 句第 k 个可见字的字头时刻（align.json，逐字）"""
    ts = [x for x in LINES[li]['times'] if x is not None]
    return ts[min(k, len(ts) - 1)]


def chars(li):
    return [c for c in LINES[li]['text'] if c.strip()]


# ------------------------------------------------------------------ 相机
def camxf(fr, z=1.0, ox=0.0, oy=0.0, rot=0.0, c=None):
    if abs(z - 1) < 1e-4 and abs(ox) < 0.05 and abs(oy) < 0.05 and abs(rot) < 1e-3: return fr
    c = c or (W / 2, H / 2)
    M = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), rot, z)
    M[0, 2] -= ox * z; M[1, 2] -= oy * z
    return cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


_PG = {}
def perlin(x, seed=0):
    """1D 平滑值噪声，约 -1..1"""
    if seed not in _PG: _PG[seed] = np.random.default_rng(seed).uniform(-1, 1, 1024)
    g = _PG[seed]; i = int(math.floor(x)); f = x - i; u = f * f * (3 - 2 * f)
    return float(g[i % 1024] * (1 - u) + g[(i + 1) % 1024] * u)


def handheld(t, amp, seed=0, freq=1.6):
    return amp * perlin(t * freq, seed), amp * perlin(t * freq + 37.1, seed + 1)


def dirblur(fr, dx, dy):
    L = int(max(abs(dx), abs(dy)))
    if L < 2: return fr
    k = np.zeros((2 * L + 1, 2 * L + 1), np.float32)
    cv2.line(k, (L - int(dx / 2), L - int(dy / 2)), (L + int(dx / 2), L + int(dy / 2)), 1.0, 1)
    k /= k.sum()
    s = cv2.resize(fr, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    k2 = cv2.resize(k, (L + 1, L + 1)) if L > 6 else k
    k2 /= k2.sum()
    return cv2.resize(cv2.filter2D(s, -1, k2), (W, H))


def radial(fr, c, amt, n=6):
    if amt < 0.004: return fr
    s = cv2.resize(fr, (W // 2, H // 2), interpolation=cv2.INTER_AREA); acc = s.copy()
    for i in range(1, n):
        acc += camxf_small(s, 1 + amt * i / n, (c[0] / 2, c[1] / 2))
    return cv2.resize(acc / n, (W, H))


def camxf_small(s, z, c):
    M = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), 0, z)
    return cv2.warpAffine(s, M, (s.shape[1], s.shape[0]), borderMode=cv2.BORDER_REFLECT)


# ------------------------------------------------------------------ 天空 / 地面 / 雨（雷暴）
_TEX = {}
def tex(key, n=512, seed=0, base=4, octaves=6):
    if key not in _TEX: _TEX[key] = fx2.noise(n, seed, base=base, octaves=octaves)
    return _TEX[key]


def storm_sky(t, seed=0, horizon=760, flash=0.0, flash_c=(960, 160), speed=(14, 3), top=(0.010, 0.013, 0.022),
              bot=(0.07, 0.08, 0.105), cloud=1.0, ox=0.0, oy=0.0):
    """雷暴天空：两层体积云（暗底亮边），被云内电光照亮。返回 float32 (H,W,3)。"""
    h, w = H // 4, W // 4
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    g = np.clip(yy * H / max(1, horizon), 0, 1) ** 1.4
    base = np.array(top, np.float32) * (1 - g[..., None]) + np.array(bot, np.float32) * g[..., None]
    base = np.broadcast_to(base, (h, w, 3)).copy()
    n1 = fx2.scroll(tex('c1', seed=seed + 1, base=3), t * speed[0] + ox * 0.15, t * speed[1] + oy * 0.15, h, w, 1.5)
    n2 = fx2.scroll(tex('c2', seed=seed + 2, base=6), t * speed[0] * 2.1 + ox * 0.3, t * speed[1] * 1.6 + oy * 0.3, h, w, 1.0)
    c = np.clip((n1 * 0.7 + n2 * 0.45 - 0.42) * 2.2, 0, 1) * cloud
    edge = np.clip(n2 - 0.5, 0, 1) * c
    L = c * 0.07 + edge * 0.18
    xx = np.linspace(0, W, w, dtype=np.float32)[None, :]; yy2 = yy * H
    if flash > 0:
        d2 = ((xx - flash_c[0]) ** 2 + (yy2 - flash_c[1]) ** 2) / 900 ** 2
        L = L + flash * np.exp(-d2) * (0.25 + 2.2 * np.clip(n1 - 0.35, 0, 1) ** 1.2 + 1.2 * edge)
    out = base + L[..., None] * COLD * 1.0
    out *= (1 - 0.55 * np.clip((yy2 - horizon) / 200, 0, 1))[..., None]
    return cv2.resize(out, (W, H), interpolation=cv2.INTER_LINEAR)


def wet_ground(fr, t, horizon=760, seed=0, refl=0.45, ox=0.0, ripples=1.0, tint=(1, 1, 1)):
    """水面/湿地：天空倒影（模糊、压暗）+ 横向水纹 + 雨点涟漪。"""
    hz = int(horizon)
    if hz >= H - BAR: return fr
    n = H - hz
    src = fr[max(0, hz - n):hz][::-1]
    if src.shape[0] < n: src = np.pad(src, ((0, n - src.shape[0]), (0, 0), (0, 0)), mode='edge')
    ref = cv2.GaussianBlur(cv2.resize(src, (W // 4, max(1, n // 4))), (0, 0), 2.0)
    ref = cv2.resize(ref, (W, n))
    st = fx2.scroll(tex('gw', seed=seed + 7, base=10), ox * 0.6, t * 40, n // 2 + 1, W // 2, 0.6)
    st = cv2.resize(st, (W, n))
    wav = np.clip((st - 0.35) * 2, 0, 1)
    yy = np.linspace(0, 1, n, dtype=np.float32)[:, None]
    ground = np.array([0.016, 0.018, 0.024], np.float32) * (1 + yy[..., None])
    out = ground + ref * refl * (0.4 + 0.8 * wav[..., None]) * (1 - 0.6 * yy[..., None])
    fr = fr.copy(); fr[hz:] = out * np.array(tint, np.float32)
    if ripples > 0:
        r = np.random.default_rng(seed)
        m = np.zeros((n // 2 + 1, W // 2), np.float32)
        for i in range(int(70 * ripples)):
            ph = r.random(); per = r.uniform(0.5, 0.9); tt = ((t + ph * per) % per) / per
            x = r.uniform(0, W / 2); y = r.uniform(0, n / 2) ** 1.0
            sc = 0.3 + 1.4 * y / max(1, n / 2)
            rad = 4 + 26 * tt * sc
            cv2.ellipse(m, (int(x), int(y)), (int(rad), max(1, int(rad * 0.22))), 0, 0, 360, (1 - tt) * 0.5, 1, cv2.LINE_AA)
        fr[hz:] += cv2.resize(m, (W, n))[..., None] * COLD * 0.25
    return fr


_RAIN = {}
def rain(fr, t, seed=0, inten=1.0, angle=10, red=0.0, light=None, freeze=None, cam=(0, 0), layers=None, color=None):
    if seed not in _RAIN: _RAIN[seed] = fx2.RainSheet(seed=seed)
    return _RAIN[seed].draw(fr, t, intensity=inten, angle=angle, red=red, light=light, freeze=freeze, cam=cam, layers=layers,
                            color=COLD * 0.95 if color is None else color)


_FOG = {}
def fog(fr, t, seed=0, **kw):
    if seed not in _FOG: _FOG[seed] = fx2.Fog(seed=seed)
    return _FOG[seed].draw(fr, t, **kw)


_LT = {}
def bolt(fr, t, t0, seed, p0, p1, inten=1.0, sky=0.4, width=3.0, branches=7, gold=False):
    k = (seed, tuple(map(int, p0)), tuple(map(int, p1)), branches)
    if k not in _LT: _LT[k] = fx2.Lightning(seed=seed, p0=p0, p1=p1, branches=branches, gold=gold)
    return _LT[k].draw(fr, t, t0, intensity=inten, sky=sky, width=width)


def bolt_env(t, t0):
    dt = t - t0
    if dt < 0: return 0.0
    return float(sum(a * math.exp(-max(0, dt - o) / 0.05) * (dt >= o) for o, a in ((0, 1.0), (0.075, 0.55), (0.14, 0.85), (0.27, 0.35))))


def vol_light(fr, c, r, col, amt):
    """点光源体积辉光（屏幕叠加）"""
    yy, xx = np.ogrid[0:H // 4, 0:W // 4]
    g = np.exp(-(((xx * 4 - c[0]) ** 2 + (yy * 4 - c[1]) ** 2) / r ** 2)).astype(np.float32)
    return fr + cv2.resize(g, (W, H))[..., None] * np.asarray(col, np.float32) * amt


def grade_contrast(fr, k=1.12, pivot=0.18):
    return np.clip(pivot + (fr - pivot) * k, 0, None)


# ------------------------------------------------------------------ 精灵
_SPR = {}
def spr(name, flip=False):
    """name: 'S071/land_kneel' 或 'C/slash_back'（assets/gen/<name>_cut.png）"""
    k = (name, flip)
    if k not in _SPR:
        L = SP.SpriteLayer(ROOT + f'/assets/gen/{name}_cut.png')
        if flip:
            for a in ('A', 'F', 'wind_w', 'ring'): setattr(L, a, np.ascontiguousarray(getattr(L, a)[:, ::-1]))
            x0, y0, x1, y1 = L.bbox; L.bbox = (1 - x1, y0, 1 - x0, y1); L.top = (1 - L.top[0], L.top[1])
        _SPR[k] = L
    return _SPR[k]


def put(fr, t, name, x, y, h, flip=False, anchor='foot', src=None, rot=0.0, rim=COLD, rim_amt=1.8, rim_dir=(-0.3, -1.0),
        expo=0.9, sat=0.6, tint=(0.93, 0.97, 1.05), gamma=1.12, lift=0.0, look=None, wind=6.0, mblur=(0, 0), alpha=1.0,
        defocus=0.0, flash=0.0, wrap=0.35, shade=None, rotblur=0.0, scale=None, breathe=0.006):
    """把精灵放到 (x,y)：anchor='foot' 时 (x,y)=脚底中点，h=身高像素；anchor='src' 时 src=(u,v) 精灵内归一化点 → (x,y)，h=精灵 alpha 包围盒高。
    flash：闪电补光（0..1+），提亮主体并加强轮廓光。"""
    L = spr(name, flip)
    a_src, s = L.fit(h)
    if scale is not None: s = scale
    if anchor == 'src': a_src = src
    g = dict(expo=expo * (1 + 0.7 * flash), sat=sat, tint=tint, lift=lift, gamma=gamma)
    rr = dict(col=tuple(np.asarray(rim, float)), amt=rim_amt * (1 + 1.6 * flash), dir=rim_dir)
    out, A = L.draw(fr, t, a_src, (x, y), s * (L.w / L.w), rot=rot, breathe=breathe, wind_amp=wind, grade=g, rim=rr, wrap=wrap,
                    mblur=mblur, shade=shade, keep_red=1.0, alpha=alpha, defocus=defocus, rotblur=rotblur, look=look)
    return out, A


# ------------------------------------------------------------------ C 组字幕体系
# 预副歌二「铅字」：思源宋 Medium，打字机逐字（字头落定）+ 朱红块光标 + 关键字 RGB 错位；出场 = 横向切片故障。
# 副歌二「破」：思源宋 Black/SemiBold，逐字从纵深飞入（2.4×、虚 → 实，落点 = 字头视觉帧），电白冷辉 + 朱红关键字；出场 = 碎裂。
WHITE_T = (0.97, 0.95, 0.90)
RED_T = (0.95, 0.16, 0.10)
GOLD_T = (1.0, 0.80, 0.44)
CREAM = (0.93, 0.88, 0.76)


class Sent:
    def __init__(self, li, ks, x, y, size=64, mode='fly', layout='h', red='', gold='', font=None, out=None, exit='shatter',
                 track=0.18, color=None, lead=0.20, sizes=None, offs=None, text=None, glitch='', hold=None, back=0.0):
        self.li, self.ks = li, list(ks)
        cs = chars(li)
        self.text = text or ''.join(cs[k] for k in self.ks)
        self.tin = [V(CT(li, k)) for k in self.ks]
        self.x, self.y, self.size, self.mode, self.layout = x, y, size, mode, layout
        self.red, self.gold, self.glitch = red, gold, glitch
        self.font = font or 'serif_black'      # 第十棒：铅字也改粗黑（铸字）
        self.exit, self.track, self.lead = exit, track, lead
        self.color = color
        self.out = out if out is not None else self.tin[-1] + 0.6
        self.sizes = sizes or [size] * len(self.text)
        self.offs = offs or [(0, 0)] * len(self.text)
        self.P = []
        if layout == 'h':
            tot = sum(s * (1 + track) for s in self.sizes) - self.sizes[-1] * track
            cx = x - tot / 2
            for i, s in enumerate(self.sizes):
                self.P.append((cx + s / 2 + self.offs[i][0], y + self.offs[i][1])); cx += s * (1 + track)
        else:
            cy = y
            for i, s in enumerate(self.sizes):
                self.P.append((x + self.offs[i][0], cy + s / 2 + self.offs[i][1])); cy += s * (1 + track)
        # 第三棒：字幕安全区（有效画面 1920×840 内四边留 ≥60px，再加 14px 余量给镜头漂移）——整句平移进安全区，不裁字
        if self.P:
            M_ = 74
            x0 = min(px - s_ * 0.55 for (px, py), s_ in zip(self.P, self.sizes)); x1 = max(px + s_ * 0.55 for (px, py), s_ in zip(self.P, self.sizes))
            y0 = min(py - s_ * 0.55 for (px, py), s_ in zip(self.P, self.sizes)); y1 = max(py + s_ * 0.55 for (px, py), s_ in zip(self.P, self.sizes))
            ddx = max(0, M_ - x0) - max(0, x1 - (W - M_)); ddy = max(0, BAR + M_ - y0) - max(0, y1 - (H - BAR - M_))
            if ddx or ddy: self.P = [(px + ddx, py + ddy) for px, py in self.P]
        self.back = back      # >0：字后局部暗衬（灰对灰时保证可读）
        for c, s in zip(self.text, self.sizes): T.glyph(c, self.font, s, False)

    def col(self, c):
        if self.color is not None: return self.color
        if c in self.gold: return GOLD_T
        if c in self.red: return RED_T
        return CREAM if self.mode == 'type' else WHITE_T


def _glitch_slices(L, q, seed):
    """横向切片位移（故障出场）"""
    bx = L.box(4)
    if bx is None: return L
    x0, y0, x1, y1 = bx
    r = np.random.default_rng(seed)
    A = L.A[y0:y1, x0:x1].copy(); C = L.C[y0:y1, x0:x1].copy()
    hh = y1 - y0; y = 0
    while y < hh:
        bh = int(r.integers(4, 22)); dx = int(r.normal(0, 60 * q))
        A[y:y + bh] = np.roll(A[y:y + bh], dx, 1); C[y:y + bh] = np.roll(C[y:y + bh], dx, 1)
        if r.random() < q * 0.5: A[y:y + bh] *= 0.2
        y += bh
    L.A[y0:y1, x0:x1] = A * (1 - q * 0.6); L.C[y0:y1, x0:x1] = C
    return L


def _back_shade(fr, L, back):
    """整句一块柔和暗衬（椭圆渐变），不是逐字黑团"""
    a4 = cv2.resize(L.A, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bx_ = L.box(0)
    m = np.zeros_like(a4)
    if bx_ is not None:
        x0_, y0_, x1_, y1_ = [v / 4 for v in bx_]
        cv2.ellipse(m, (int((x0_ + x1_) / 2), int((y0_ + y1_) / 2)), (int((x1_ - x0_) * 0.62 + 10), int((y1_ - y0_) * 0.62 + 10)),
                    0, 0, 360, 1.0, -1)
        m = cv2.GaussianBlur(m, (0, 0), 10)
    m = np.clip(m, 0, 1) * back
    return fr * (1 - cv2.resize(m, (W, H))[..., None] * 0.7)


_CAST_N = {}
def cast_metal(L, seed=0, light=(-0.55, -0.83)):
    """第十棒：铅字/铸字质感。字面 = 原色金属（奶白 → 锡铅灰，金 → 铸铜金）
    · 倒角：alpha 模糊作高度 → 法线 · 烛光方向漫反射 + 边缘高光 · 砂铸麻点（两档噪声）· 字心微凹（冲压）。"""
    bx = L.box(6)
    if bx is None: return L
    x0, y0, x1, y1 = bx
    A = L.A[y0:y1, x0:x1]; C = L.C[y0:y1, x0:x1]
    hh, ww = A.shape
    if seed not in _CAST_N:
        r = np.random.default_rng(seed)
        n1 = cv2.GaussianBlur(r.random((H, W)).astype(np.float32), (0, 0), 1.1)
        n2 = cv2.resize(r.random((H // 18, W // 18)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
        _CAST_N[seed] = (n1, n2)
    n1, n2 = _CAST_N[seed]
    n1 = n1[y0:y1, x0:x1]; n2 = n2[y0:y1, x0:x1]
    hgt = cv2.GaussianBlur(A, (0, 0), 3.2)
    inner = cv2.GaussianBlur(A, (0, 0), 9.0)
    hgt = hgt - 0.08 * np.clip((inner - 0.85) / 0.15, 0, 1)            # 字心微凹（冲压痕）
    gy, gx = np.gradient(hgt)
    nz = 0.09
    nn = np.sqrt(gx * gx + gy * gy + nz * nz)
    lx, ly = light
    dif = np.clip((-gx * lx - gy * ly) / nn * 1.0 + nz / nn * 0.55, 0, None)
    rim = np.clip(np.sqrt(gx * gx + gy * gy) / nn, 0, 1)
    spec = np.clip(dif - 0.75, 0, 1) ** 1.5 * 3.0
    pit = 0.80 + 0.30 * n1 + 0.18 * (n2 - 0.5)
    pit = pit - 0.35 * (n1 > 0.62) * (A > 0.9)                          # 麻点（砂眼）
    lum = C.mean(-1, keepdims=True)
    warm = (C[..., 0:1] - C[..., 2:3]) > 0.35                           # 金字（暖）→ 铸铜金；其余 → 锡铅灰
    base = np.where(warm, np.array([0.95, 0.66, 0.30], np.float32), np.array([0.74, 0.67, 0.56], np.float32) * np.clip(lum + 0.05, 0, 1.2))
    shade = (0.42 + 0.85 * dif)[..., None] * pit[..., None]
    out = base * shade + spec[..., None] * np.array([1.0, 0.86, 0.62], np.float32) * 0.55 - rim[..., None] * 0.10 * (1 - dif[..., None])
    L.C[y0:y1, x0:x1] = np.clip(out, 0, 1.6)
    return L


def draw_sent(fr, s, t, cam=(0.0, 0.0, 1.0)):
    """cam=(dx,dy,z)：字层随镜头轻微漂移（字是空间里的物体，不是死贴屏幕）"""
    if t < s.tin[0] - s.lead - 0.02: return fr
    q_out = clamp((t - s.out) / getattr(s, 'exit_len', 0.30))     # 第四棒：exit_len 让碎裂在下一个切点前收完
    if q_out >= 1: return fr
    L = T.Layer(); Lr = None
    dx, dy, z = cam
    for i, (c, (px, py), sz) in enumerate(zip(s.text, s.P, s.sizes)):
        ti = s.tin[i]
        e = (t - (ti - s.lead)) / s.lead
        if e <= 0: continue
        e = min(1.0, e)
        px = W / 2 + (px - W / 2) * z + dx; py = H / 2 + (py - H / 2) * z + dy
        colr = s.col(c)
        if s.mode == 'type':
            if e < 1: continue                         # 打字机：字头帧直接出现（铅字敲下）
            k = t - ti
            jit = (np.random.default_rng(int(ti * 100) + i).normal(0, 1.2, 2) if k < 0.07 else (0, 0))
            sc = 1.0 + 0.10 * pulse(t, ti, 0.05)
            # 第十一棒（critic_C_r5「红青错位像渲染事故」）：关键字落字不再做 RGB 错位，改「冲压」——
            # 字从 1.32× 砸下、3 帧回到 1.0 并下沉 6px，整句随之一震（铸字落模），没有任何色差
            slam = 0.0
            for j, cj in enumerate(s.text):
                if cj in s.glitch:
                    kj = t - s.tin[j]
                    if 0 <= kj < 0.10: slam = max(slam, (1 - kj / 0.10) ** 2)
            if c in s.glitch and 0 <= k < 0.10:
                sc = 1.0 + 0.32 * (1 - k / 0.10) ** 2
            jy = 6 * slam
            T.place(L, c, px + jit[0], py + jit[1] + jy, sz * z, colr, s.font, scale=sc, texture=False)
        else:
            ee = eout(e, 3)
            sc = lerp(2.4, 1.0, ee)
            bl = 7.0 * (1 - ee) ** 2
            al = min(1.0, e * 2.2)
            k = t - ti
            sc *= 1 + 0.06 * pulse(t, ti, 0.08)
            T.place(L, c, px + (px - W / 2) * (sc - 1) * 0.15, py + (py - H / 2) * (sc - 1) * 0.15, sz * z, colr, s.font,
                    alpha=al, scale=sc, blur=bl, texture=False)
    # 出场
    if q_out > 0:
        if s.exit == 'glitch': L = _glitch_slices(L, q_out, int(t * 30))
        elif s.exit == 'shatter': L = T.shatter_layer(L, q_out * 0.9, None, 9 * len(s.text), seed=s.li, power=0.8, gravity=300)
        else:
            L.A *= (1 - q_out)
    if s.mode == 'type':
        # 第十棒（critic_C_r5 P1①）：去掉打字机朱红光标（古装片出戏）；整句改「铸字」——粗黑体 + 倒角 + 砂铸麻点 + 烛光高光
        L = cast_metal(L, seed=s.li * 13 + 5)
        if getattr(s, 'back', 0) > 0: fr = _back_shade(fr, L, s.back)
        out = T.compose(fr, L, shadow=0.85, shadow_sigma=16, glow=0.10, glow_sigma=12)
    else:
        if getattr(s, 'back', 0) > 0: fr = _back_shade(fr, L, s.back)
        out = T.compose(fr, L, shadow=0.8, shadow_sigma=22, glow=0.45, glow_sigma=16, glow_color=None)
        # 电白冷辉
        bx = L.box(30)
    if Lr is not None:
        out = T.compose(out, Lr, shadow=0, glow=0.0)
    return out


def big_glyph(ch, size, font='serif_black'):
    return T.glyph(ch, font, size, False)


def paste_glyph(fr, ch, cx, cy, size, color, alpha=1.0, font='serif_black', glow=0.6, glow_c=None, shadow=0.7, scale=1.0, rot=0.0, blur=0.0):
    L = T.Layer()
    T.place(L, ch, cx, cy, size, color, font, alpha=alpha, scale=scale, rot=rot, blur=blur, texture=False)
    return T.compose(fr, L, shadow=shadow, shadow_sigma=26, glow=glow, glow_sigma=24, glow_color=glow_c)


def glyph_layer(ch, cx, cy, size, color, font='serif_black', alpha=1.0, scale=1.0, rot=0.0):
    L = T.Layer(); T.place(L, ch, cx, cy, size, color, font, alpha=alpha, scale=scale, rot=rot, texture=False); return L
