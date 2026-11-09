import numpy as np, cv2, math, random
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
BAR = 120  # letterbox
FD = '/Users/sannian/Downloads/鬼屠OP_new/out/devsnap/code/fonts/'
F_BRUSH = FD + 'MaShanZheng-Regular.ttf'
F_WILD = FD + 'ZhiMangXing-Regular.ttf'
F_CAO = FD + 'LiuJianMaoCao-Regular.ttf'
F_SERIF = FD + 'NotoSerifSC.otf'
_fc = {}
def font(path, size):
    k = (path, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]

def load_art(path):
    im = cv2.imread(path)[:, :, ::-1].astype(np.float32) / 255.
    # upscale to cover 1.25x frame for camera moves
    s = max(W * 1.25 / im.shape[1], H * 1.25 / im.shape[0])
    im = cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)), interpolation=cv2.INTER_LANCZOS4)
    return grade(im)

def grade(im):
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    red = np.clip((r - np.maximum(g, b)) * 3.0, 0, 1)[..., None]
    warm = np.clip((r - b) * 2.2, 0, 1)[..., None]  # gold/ember light
    keep = np.clip(red + 0.55 * warm, 0, 1)
    mono = np.stack([lum * 0.97, lum * 0.99, lum * 1.04], -1)  # cold steel
    out = mono * (1 - keep) + im * keep
    # S-curve, crushed blacks
    out = np.clip((out - 0.04) / 0.92, 0, 1)
    out = out * out * (3 - 2 * out) * 0.6 + out * 0.4
    return out.astype(np.float32)

def camera(img, t, zoom0=1.0, zoom1=1.12, pan=(0, 0), shake=0.0, rot=0.0):
    """t in 0..1. returns W x H crop"""
    ih, iw = img.shape[:2]
    z = zoom0 + (zoom1 - zoom0) * (t * t * (3 - 2 * t))
    cw, ch = iw / 1.25 / z, ih / 1.25 / z
    cx = iw / 2 + pan[0] * (t - 0.5) * (iw - cw) + shake * random.uniform(-1, 1) * 18
    cy = ih / 2 + pan[1] * (t - 0.5) * (ih - ch) + shake * random.uniform(-1, 1) * 18
    sx, sy = W / cw, H / ch
    ang = rot * (t - 0.5)
    M = cv2.getRotationMatrix2D((cx, cy), ang, 1.0)
    M[:, :] *= sx
    M[0, 2] += W / 2 - cx * sx
    M[1, 2] += H / 2 - cy * sy
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

_vig = None
def vignette(fr, strength=0.55):
    global _vig
    if _vig is None:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
        _vig = np.clip(1 - (d - 0.45) * 0.9, 0, 1)[..., None] ** 1.6
    return fr * (1 - strength + strength * _vig)

_grain = None
def grain(fr, amt=0.05):
    global _grain
    if _grain is None:
        _grain = [cv2.GaussianBlur(np.random.randn(H // 2, W // 2).astype(np.float32), (0, 0), 0.7) for _ in range(8)]
    g = cv2.resize(random.choice(_grain), (W, H), interpolation=cv2.INTER_LINEAR)
    return fr + g[..., None] * amt * (0.4 + 0.6 * (1 - fr))

def letterbox(fr):
    fr[:BAR] = 0; fr[H - BAR:] = 0
    return fr

def glow(fr, thresh=0.7, amt=0.6, sigma=25):
    hi = np.clip(fr - thresh, 0, 1)
    small = cv2.resize(hi, (W // 4, H // 4))
    b = cv2.GaussianBlur(small, (0, 0), sigma / 4)
    return fr + cv2.resize(b, (W, H)) * amt

def chroma(fr, px=4):
    if px <= 0: return fr
    out = fr.copy()
    out[..., 0] = np.roll(fr[..., 0], px, 1)
    out[..., 2] = np.roll(fr[..., 2], -px, 1)
    return out

class Embers:
    def __init__(self, n=140, seed=1):
        rng = np.random.default_rng(seed)
        self.p = rng.random((n, 2)) * [W, H]
        self.v = np.stack([rng.normal(30, 25, n), -rng.uniform(40, 160, n)], 1)
        self.sz = rng.uniform(1.0, 3.6, n)
        self.ph = rng.random(n) * 6.28
        self.layer = np.zeros((H, W, 3), np.float32)
    def draw(self, fr, t, dt, intensity=1.0, energy=0.0):
        if intensity <= 0: return fr
        self.p += self.v * dt * (1 + energy * 1.5)
        self.p[:, 0] += np.sin(t * 1.3 + self.ph) * 0.8
        m = (self.p[:, 1] < -10) | (self.p[:, 0] > W + 10)
        self.p[m] = np.stack([np.random.rand(m.sum()) * W * 0.9, np.full(m.sum(), H + 10.)], 1)
        L = np.zeros((H // 2, W // 2, 3), np.float32)
        for (x, y), s, ph in zip(self.p, self.sz, self.ph):
            fl = 0.6 + 0.4 * math.sin(t * 8 + ph * 3)
            c = (1.0 * fl, 0.42 * fl, 0.12 * fl)
            cv2.circle(L, (int(x / 2), int(y / 2)), max(1, int(s / 2)), c, -1, cv2.LINE_AA)
        Lb = cv2.GaussianBlur(L, (0, 0), 3) * 2.2 + L
        return fr + cv2.resize(Lb, (W, H)) * intensity

class Rain:
    def __init__(self, n=420, seed=3):
        rng = np.random.default_rng(seed)
        self.p = rng.random((n, 2)) * [W, H]
        self.l = rng.uniform(25, 70, n)
    def draw(self, fr, dt, intensity=1.0):
        if intensity <= 0: return fr
        self.p += np.array([-260, 1900]) * dt
        self.p[:, 1] %= H; self.p[:, 0] %= W
        L = np.zeros((H // 2, W // 2), np.float32)
        for (x, y), l in zip(self.p, self.l):
            cv2.line(L, (int(x / 2), int(y / 2)), (int((x - l * 0.14) / 2), int((y + l) / 2)), 0.35, 1, cv2.LINE_AA)
        return fr + cv2.resize(L, (W, H))[..., None] * intensity * np.array([0.8, 0.85, 0.95], np.float32)

def slash(fr, prog, angle=-18, cy=0.5, width=1.0, color=(1, 0.95, 0.9)):
    """light streak across screen, prog 0..1"""
    if prog <= 0 or prog >= 1.4: return fr
    L = np.zeros((H // 2, W // 2), np.float32)
    a = math.radians(angle)
    length = W * 1.3
    head = min(prog, 1.0); tail = max(0, prog - 0.4) / 1.0
    cx, cyy = W / 4, cy * H / 2
    x0 = cx + math.cos(a) * length / 2 * (tail * 2 - 1); y0 = cyy + math.sin(a) * length / 2 * (tail * 2 - 1)
    x1 = cx + math.cos(a) * length / 2 * (head * 2 - 1); y1 = cyy + math.sin(a) * length / 2 * (head * 2 - 1)
    fade = 1.0 if prog < 1 else max(0, 1 - (prog - 1) / 0.4)
    cv2.line(L, (int(x0), int(y0)), (int(x1), int(y1)), 1.0, max(1, int(3 * width)), cv2.LINE_AA)
    core = cv2.GaussianBlur(L, (0, 0), 1.2)
    bloom = cv2.GaussianBlur(L, (0, 0), 14) * 4
    S = cv2.resize(core * 2 + bloom, (W, H))[..., None] * fade
    return fr + S * np.array(color, np.float32)

def ink_wipe_mask(prog, seed=0):
    """organic ink-spread mask 0..1"""
    rng = np.random.default_rng(seed)
    n = cv2.resize(rng.random((9, 16)).astype(np.float32), (W // 4, H // 4), interpolation=cv2.INTER_CUBIC)
    n2 = cv2.resize(rng.random((36, 64)).astype(np.float32), (W // 4, H // 4), interpolation=cv2.INTER_CUBIC)
    y, x = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
    d = np.sqrt((x / (W / 4) - 0.5) ** 2 * 3 + (y / (H / 4) - 0.5) ** 2 * 1.7)
    f = d + (n - 0.5) * 0.5 + (n2 - 0.5) * 0.15
    m = np.clip((prog * 1.6 - f) * 8, 0, 1)
    return cv2.resize(m, (W, H))[..., None]

# ---------- text ----------
_gc = {}
def glyph(c, fpath, size, gw):
    k = (c, fpath, size)
    if k not in _gc:
        g = Image.new('L', (gw, gw), 0)
        ImageDraw.Draw(g).text((gw / 2, gw / 2), c, font=font(fpath, size), fill=255, anchor='mm')
        _gc[k] = np.asarray(g).astype(np.float32) / 255
    return _gc[k].copy()
def text_layer(chars, fpath, size, reveal, spacing=0.06, color=(0.96, 0.94, 0.9), red_idx=(), pos=(0.5, 0.78), vertical=False, scale_in=0.25, blur_in=6):
    """chars: string. reveal: array per-char 0..1 progress. returns (rgb, alpha) full-frame"""
    f = font(fpath, size)
    adv = [f.getlength(c) if c != ' ' else size * 0.45 for c in chars]
    gap = size * spacing
    rgb = np.zeros((H, W, 3), np.float32); A = np.zeros((H, W), np.float32)
    if vertical:
        total = sum(size + gap for c in chars if c != ' ') + sum(size * 0.5 for c in chars if c == ' ')
        x = pos[0] * W; y = pos[1] * H - total / 2
    else:
        total = sum(adv) + gap * (len(chars) - 1)
        x = pos[0] * W - total / 2; y = pos[1] * H
    for i, c in enumerate(chars):
        if c == ' ':
            if vertical: y += size * 0.5
            else: x += adv[i] + gap
            continue
        r = float(np.clip(reveal[i], 0, 1))
        if r > 0:
            pad = int(size * 0.6)
            gw = int(size * 1.6) + pad
            ga = glyph(c, fpath, size, gw)
            e = 1 - (1 - r) ** 3
            sc = 1 + scale_in * (1 - e)
            if sc != 1:
                M = cv2.getRotationMatrix2D((gw / 2, gw / 2), 0, sc)
                ga = cv2.warpAffine(ga, M, (gw, gw))
            bl = blur_in * (1 - e)
            if bl > 0.3: ga = cv2.GaussianBlur(ga, (0, 0), bl)
            ga *= e
            if vertical: cx, cy = x + 0, y + size / 2
            else: cx, cy = x + adv[i] / 2, y
            x0, y0 = int(cx - gw / 2), int(cy - gw / 2)
            xs, ys = max(0, x0), max(0, y0); xe, ye = min(W, x0 + gw), min(H, y0 + gw)
            if xe > xs and ye > ys:
                sub = ga[ys - y0:ye - y0, xs - x0:xe - x0]
                col = np.array((0.78, 0.06, 0.05) if i in red_idx else color, np.float32)
                rgb[ys:ye, xs:xe] = rgb[ys:ye, xs:xe] * (1 - sub[..., None]) + col * sub[..., None]
                A[ys:ye, xs:xe] = np.maximum(A[ys:ye, xs:xe], sub)
        if vertical: y += size + gap
        else: x += adv[i] + gap
    return rgb, A

def under_grad(fr, y0=0.6, amt=0.55):
    g=np.clip((np.linspace(0,1,H)-y0)/(1-y0),0,1)**1.3
    return fr*(1-amt*g)[:,None,None]

def comp_text(fr, rgb, A, shadow=0.85, glowc=(1.0, 0.35, 0.15), glowamt=0.0):
    # ink shadow halo for legibility
    sh = cv2.GaussianBlur(cv2.resize(A, (W // 2, H // 2)), (0, 0), 9)
    sh = np.clip(cv2.resize(sh, (W, H)) * 1.6, 0, 1)[..., None]
    fr = fr * (1 - sh * shadow)
    if glowamt > 0:
        gl = cv2.GaussianBlur(cv2.resize(A, (W // 4, H // 4)), (0, 0), 6)
        fr = fr + cv2.resize(gl, (W, H))[..., None] * np.array(glowc, np.float32) * glowamt
    a = A[..., None]
    return fr * (1 - a) + rgb * a

def seal(fr, text='鬼屠', x=0.06, y=0.2, size=64, alpha=0.9):
    """red square seal stamp, carved white characters"""
    s = size * 2 + 22
    im = Image.new('L', (s, s), 0); d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, s - 3, s - 3], radius=8, fill=255)
    f = font(F_SERIF, size)
    if len(text) == 2:
        for k, c in enumerate(text):
            d.text((s / 2, 11 + size / 2 + k * size), c, font=f, fill=0, anchor='mm')
    m = np.asarray(im).astype(np.float32) / 255
    rng = np.random.default_rng(7)
    rough = cv2.GaussianBlur(rng.random((s, s)).astype(np.float32), (0, 0), 1.2)
    m = m * np.clip((rough - 0.28) * 4, 0, 1)
    x0, y0 = int(x * W), int(y * H)
    reg = fr[y0:y0 + s, x0:x0 + s]
    a = (m * alpha)[..., None]
    fr[y0:y0 + s, x0:x0 + s] = reg * (1 - a) + np.array([0.72, 0.05, 0.04], np.float32) * a
    return fr

def finish(fr, grain_amt=0.05, vig=0.55, ca=0):
    fr = chroma(fr, ca)
    fr = vignette(fr, vig)
    fr = grain(fr, grain_amt)
    fr = letterbox(fr)
    return np.clip(fr, 0, 1)

def to8(fr):
    return (np.clip(fr, 0, 1) * 255 + 0.5).astype(np.uint8)
