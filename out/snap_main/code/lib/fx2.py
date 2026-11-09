"""fx2.py · 美术·角色组 —— 雨光特效库（纯程序化，numpy + OpenCV）

所有函数 / 类都是“帧级可动画”：输入绝对时间 t（秒）或进度 prog，不保存逐帧状态（无状态、可随机跳帧渲染）。
画布约定：fr 为 float32 RGB 0..1，H×W = 1080×1920（含黑边，黑边由 finish 统一压黑）。函数原地或返回新 fr，统一 `return fr`。
色板：只用黑白灰 + 朱红 RED + 金 GOLD；闪电/雨为冷白灰（属于“白”）。
性能：软的东西（辉光、体积光、雾）一律在 1/2 或 1/4 分辨率算再放大。

组件：
  RainSheet      多层雨幕（远/中/近/贴镜四层，景深模糊、逆光闪亮、血雨、悬停雨珠）
  Splashes       地面溅水（皇冠水花 + 飞溅水珠 + 涟漪），透视地面
  ripples        水面涟漪（单点或多点）
  Lightning      闪电（主干 + 递归分叉 + 先导 + 多次回击闪烁），cloud_flash 云内亮
  god_rays       体积光/丁达尔光束（径向缩放累积 + 角向噪声光柱呼吸）
  light_beam     单束锥形光（月光/窗光/裂缝光束），内部条纹 + 浮尘
  CrackLight     裂缝 + 金光涌出（逐段裂开、溢光、光束扇、上浮金尘）
  Embers         飞火余烬 / 金尘 / 灰烬（深度分层：近处焦外光斑）
  Fog            分层流动雾（高度衰减、光源附近散射提亮）
  heat_haze      热浪扭曲；bloom；grain；dof_blur
"""
import math
import numpy as np, cv2

W, H = 1920, 1080
RED = np.array([0.72, 0.06, 0.05], np.float32)
GOLD = np.array([1.0, 0.76, 0.40], np.float32)
COLD = np.array([0.86, 0.89, 0.94], np.float32)      # 月光冷白（灰阶内）
WHITE_GOLD = np.array([1.0, 0.93, 0.78], np.float32)


# ============================================================== 基础工具
def _f32(c): return np.asarray(c, np.float32)

def smooth(a, b, x):
    t = np.clip((np.asarray(x, np.float32) - a) / (b - a + 1e-9), 0, 1); return t * t * (3 - 2 * t)

def blur_ds(a, sig, k=None):
    """大半径高斯：先降采样再模糊再放大（a 可 2D/3D）。"""
    if sig <= 0.5: return a
    h, w = a.shape[:2]
    if k is None: k = int(max(1, min(8, sig // 3)))
    if k > 1:
        s = cv2.resize(a, (max(1, w // k), max(1, h // k)), interpolation=cv2.INTER_AREA)
        s = cv2.GaussianBlur(s, (0, 0), sig / k)
        return cv2.resize(s, (w, h), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(a, (0, 0), sig)

_NZ = {}
def noise(n=512, seed=0, base=6, octaves=5, persist=0.55):
    """可平铺 fbm (n,n) 0..1，缓存。"""
    k = (n, seed, base, octaves, persist)
    if k not in _NZ:
        rng = np.random.default_rng(seed); out = np.zeros((n, n), np.float32); amp = 1.; tot = 0.
        for o in range(octaves):
            g = base * 2 ** o
            a = np.tile(rng.random((g, g)).astype(np.float32), (3, 3))
            out += cv2.resize(a, (n * 3, n * 3), interpolation=cv2.INTER_CUBIC)[n:2 * n, n:2 * n] * amp
            tot += amp; amp *= persist
        out /= tot; out = (out - out.min()) / (out.max() - out.min() + 1e-6)
        _NZ[k] = out
    return _NZ[k]

def tile(tex, x0, y0, h, w):
    n = tex.shape[0]
    ys = (np.arange(h) + int(y0)) % n; xs = (np.arange(w) + int(x0)) % n
    return tex[np.ix_(ys, xs)]

def scroll(tex, ox, oy, h, w, scale=1.0):
    """把平铺纹理按 (ox,oy) 像素偏移、scale 放大后取 h×w（亚像素平滑）。"""
    n = tex.shape[0]
    M = np.array([[1 / scale, 0, ox], [0, 1 / scale, oy]], np.float32)
    return cv2.warpAffine(tex, M, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_WRAP)

def add(fr, layer, color, amt=1.0):
    """加色合成：layer 为 2D（任意分辨率，自动放大）。"""
    if layer.shape[:2] != fr.shape[:2]:
        layer = cv2.resize(layer, (fr.shape[1], fr.shape[0]), interpolation=cv2.INTER_LINEAR)
    fr += layer[..., None] * (_f32(color) * amt)
    return fr

def over(fr, alpha, color):
    if alpha.shape[:2] != fr.shape[:2]:
        alpha = cv2.resize(alpha, (fr.shape[1], fr.shape[0]), interpolation=cv2.INTER_LINEAR)
    a = np.clip(alpha, 0, 1)[..., None]
    fr[:] = fr * (1 - a) + _f32(color) * a
    return fr

def bloom(fr, thr=0.75, amt=0.6, sig=24, tint=None):
    """高光泛光（只取超过 thr 的部分）。"""
    s = cv2.resize(fr, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b = np.clip(s - thr, 0, None)
    g = cv2.GaussianBlur(b, (0, 0), sig / 4) + cv2.GaussianBlur(b, (0, 0), sig / 12) * 0.6
    if tint is not None: g = g.mean(2, keepdims=True) * _f32(tint)
    fr += cv2.resize(g, (fr.shape[1], fr.shape[0])) * amt
    return fr

def grain(fr, t, amt=0.035, size=1.4):
    """胶片颗粒（随帧变，亮部弱暗部强）。"""
    rng = np.random.default_rng(int(t * 30 * 7919) & 0xffffffff)
    h, w = int(H / size), int(W / size)
    g = rng.standard_normal((h, w)).astype(np.float32)
    g = cv2.resize(g, (fr.shape[1], fr.shape[0]), interpolation=cv2.INTER_LINEAR)
    lum = fr.mean(2)
    fr += (g * amt * (1.15 - 0.6 * np.clip(lum, 0, 1)))[..., None]
    return fr

def dof_blur(img, sig):
    return blur_ds(img, sig) if sig > 0.6 else img

def heat_haze(fr, t, mask=None, amt=6.0, scale=40.0, speed=1.2, seed=3):
    """热浪折射扭曲：mask (H,W) 0..1 控制区域；amt 像素位移。"""
    h, w = fr.shape[:2]
    nz = noise(256, seed, base=4, octaves=3)
    dx = scroll(nz, 0, -t * speed * 60, h // 4, w // 4, scale / 10) - 0.5
    dy = scroll(nz, 97, -t * speed * 90, h // 4, w // 4, scale / 10) - 0.5
    dx = cv2.resize(dx, (w, h)); dy = cv2.resize(dy, (w, h))
    if mask is not None: dx *= mask; dy *= mask
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(fr, gx + dx * amt * 2, gy + dy * amt * 2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ============================================================== 雨
RAIN_LAYERS = (   # n, 长度(px), 线宽, 不透明, 模糊σ, 速度(px/s), 视差
    dict(n=1500, L=(10, 22), w=1, a=0.16, blur=0.0, v=1500, par=0.3),
    dict(n=650, L=(28, 60), w=1, a=0.28, blur=0.0, v=2300, par=0.6),
    dict(n=120, L=(110, 230), w=2, a=0.26, blur=2.2, v=3600, par=1.0),
    dict(n=16, L=(380, 720), w=7, a=0.14, blur=8.0, v=5200, par=1.6),
)

class RainSheet:
    """多层雨幕。
    draw(fr, t, intensity=1, angle=10, color=COLD, light=None, light_r=500, red=0, freeze=None, layers=None, cam=(0,0))
      t          绝对时间（雨的位置 = f(t)，可直接做慢放：传入 t_slow）
      intensity  0..1.5 雨量（同时调透明度与数量）
      angle      雨偏角（度，+ 向右下）
      light      (x,y) 逆光源：靠近光源的雨丝提亮成金/白亮线（体积感）
      red        0..1 血雨（S070：雨丝变朱红）
      freeze     None 或 0..1：悬停（S108）——雨丝缩成雨珠（带高光的小圆），值为“冻结程度”
      layers     选用哪些层，例如 (0,1) 只要远中景（被前景遮挡时）
      cam        (dx,dy) 相机平移像素，层按视差偏移
    """
    def __init__(self, seed=0, layers=RAIN_LAYERS, density=1.0):
        rng = np.random.default_rng(seed); self.L = []
        for d in layers:
            n = int(d['n'] * density)
            self.L.append(dict(d, x=rng.uniform(0, W * 1.4, n).astype(np.float32), y=rng.uniform(0, H * 1.6, n).astype(np.float32),
                               l=rng.uniform(*d['L'], n).astype(np.float32), vj=rng.uniform(0.85, 1.15, n).astype(np.float32),
                               br=rng.uniform(0.5, 1.0, n).astype(np.float32)))

    def draw(self, fr, t, intensity=1.0, angle=10.0, color=COLD, light=None, light_r=500, red=0.0, freeze=None,
             layers=None, cam=(0, 0)):
        if intensity <= 0: return fr
        a = math.radians(angle); ux, uy = math.sin(a), math.cos(a)
        col = _f32(color) * (1 - red) + (RED * 1.3) * red
        acc = np.zeros((H // 2, W // 2), np.float32)
        if light is not None:
            gx = np.exp(-(((np.arange(W // 2) * 2 - light[0]) / light_r) ** 2))[None, :]
            gy = np.exp(-(((np.arange(H // 2) * 2 - light[1]) / light_r) ** 2))[:, None]
            lg = (gx * gy).astype(np.float32); accl = np.zeros_like(acc)
        for li, d in enumerate(self.L):
            if layers is not None and li not in layers: continue
            n = int(len(d['x']) * min(1.0, intensity))
            if n == 0: continue
            k = 2 if d['blur'] < 3 else 4                     # 渲染分辨率因子
            h, w = H // k, W // k
            buf = np.zeros((h, w), np.float32)
            v = d['v'] * d['vj'][:n]
            y = (d['y'][:n] + v * t * uy - cam[1] * d['par']) % (H * 1.6) - H * 0.3
            x = (d['x'][:n] + v * t * ux - cam[0] * d['par']) % (W * 1.4) - W * 0.2
            L = d['l'][:n]
            if freeze is not None:
                L = L * (1 - freeze) + 1.0 * freeze
            x1 = x - ux * L; y1 = y - uy * L
            br = d['br'][:n]
            sc = 8.0 / k
            P = np.round(np.stack([np.stack([x1, y1], 1), np.stack([x, y], 1)], 1) * sc).astype(np.int32)
            for b0, b1, val in ((0, 0.4, 0.55), (0.4, 0.75, 0.8), (0.75, 9, 1.0)):
                m = (br >= b0) & (br < b1)
                if m.any():
                    if freeze is not None and freeze > 0.5:
                        rr = int(max(8, d['w'] * 10 * sc / k))
                        for (px, py) in P[m][:, 1]:
                            cv2.circle(buf, (int(px), int(py)), rr, val, -1, cv2.LINE_AA, 3)
                    else:
                        cv2.polylines(buf, list(P[m]), False, val, max(1, int(round(d['w'] / k))), cv2.LINE_AA, 3)
            if d['blur'] > 0: buf = cv2.GaussianBlur(buf, (0, 0), d['blur'] / k)
            amt = d['a'] * min(1.5, intensity) * (1.0 if d['blur'] < 3 else 1.6)
            if k != 2: buf = cv2.resize(buf, (W // 2, H // 2), interpolation=cv2.INTER_LINEAR)
            acc += buf * amt
            if light is not None: accl += buf * amt * lg
        if freeze is not None and freeze > 0.5:                 # 悬停雨珠：加一圈柔光
            acc += cv2.GaussianBlur(acc, (0, 0), 2.0) * 0.8
        lay = cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR)
        col = col * (1 + 0.9 * red)
        fr += lay[..., None] * col * (1.05 - np.clip(fr, 0, 1) * 0.6)
        if light is not None:
            fr = add(fr, accl, WHITE_GOLD, 2.2)
        return fr


class Splashes:
    """地面溅水：皇冠水花 + 抛物线水珠 + 扁椭圆涟漪；无状态。
    draw(fr, t, y_far=640, y_near=960, x0=0, x1=W, rate=120, color=COLD, size=1.0, puddle=0.5, light=None)
      y_far/y_near 地面在屏幕上的远/近边（透视：越近越大）；rate 每秒水花数；puddle 涟漪比重。"""
    def __init__(self, seed=0): self.seed = seed

    def draw(self, fr, t, y_far=640, y_near=960, x0=0, x1=W, rate=120, color=COLD, size=1.0, puddle=0.5, amt=1.0):
        buf = np.zeros((H // 2, W // 2), np.float32)
        life = 0.32
        i0, i1 = int(math.floor((t - life) * rate)), int(math.floor(t * rate))
        for i in range(i0, i1 + 1):
            r = np.random.default_rng((self.seed * 1000003 + i) & 0x7fffffff)
            ti = i / rate + r.uniform(0, 1 / rate); age = t - ti
            if age < 0 or age > life: continue
            u = r.random() ** 0.7                          # 0 远 .. 1 近
            px = r.uniform(x0, x1); py = y_far + (y_near - y_far) * u
            s = (0.25 + 1.6 * u * u) * size * 7
            k = age / life
            # 涟漪
            if r.random() < puddle:
                rr = s * (0.6 + 5 * k)
                cv2.ellipse(buf, (int(px * 4), int(py * 4)), (int(rr * 4), max(1, int(rr * 0.28 * 4))), 0, 0, 360,
                            float(0.6 * (1 - k)), 1, cv2.LINE_AA, 3)
            # 皇冠
            if k < 0.45:
                kk = k / 0.45
                hgt = s * 2.2 * math.sin(math.pi * kk); wid = s * (0.8 + 1.4 * kk)
                for j in range(-3, 4):
                    ex = px + j * wid / 3.0
                    cv2.line(buf, (int((px + j * wid / 6) * 4), int(py * 4)), (int(ex * 4), int((py - hgt * (1 - abs(j) / 4.5)) * 4)),
                             float(0.9 * (1 - kk)), 1, cv2.LINE_AA, 3)
            # 飞溅水珠
            for j in range(int(3 + 4 * u)):
                vx = r.normal(0, 1) * s * 7; vy = -r.uniform(0.6, 1.4) * s * 14
                tt = age
                qx = px + vx * tt; qy = py + vy * tt + 0.5 * 900 * size * (0.3 + u) * tt * tt
                if qy > py + 2: continue
                cv2.circle(buf, (int(qx * 4), int(qy * 4)), max(1, int(s * 0.18 * 4)), float(1 - k), -1, cv2.LINE_AA, 3)
        buf = cv2.GaussianBlur(buf, (0, 0), 0.7)
        return add(fr, buf, color, 0.75 * amt)


def ripples(fr, t, centers, t0s, color=COLD, speed=220, rings=4, flat=0.3, amt=0.8, life=2.0, width=2):
    """水面涟漪：centers [(x,y)], t0s 每个的起始时间。flat 竖直压扁比（俯视=1，平视≈0.25）。"""
    buf = np.zeros((H // 2, W // 2), np.float32)
    for (cx, cy), t0 in zip(centers, t0s):
        age = t - t0
        if age < 0 or age > life: continue
        for k in range(rings):
            a2 = age - k * 0.12
            if a2 <= 0: continue
            r = speed * a2 * (1 - 0.25 * a2 / life)
            v = (1 - age / life) ** 1.5 * (1 - k / rings)
            cv2.ellipse(buf, (int(cx * 2), int(cy * 2)), (int(r * 2), max(1, int(r * flat * 2))), 0, 0, 360, float(v),
                        width, cv2.LINE_AA, 0)
    buf = cv2.GaussianBlur(buf, (0, 0), 1.0)
    return add(fr, buf, color, amt)


# ============================================================== 闪电
def _bolt(rng, p0, p1, rough, depth):
    pts = [np.array(p0, float), np.array(p1, float)]
    disp = np.hypot(*(np.array(p1) - np.array(p0))) * rough
    for _ in range(depth):
        new = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            m = (a + b) / 2; d = b - a; nrm = np.array([-d[1], d[0]]) / (np.hypot(*d) + 1e-9)
            new += [m + nrm * rng.normal(0, 1) * disp, b]
        pts = new; disp *= 0.55
    return np.array(pts)

def _kink(rng, pts, p0, p1, n=9, amp=0.06):
    """在主干上加几处折线式急转（真实闪电的“之”字感）。"""
    L = np.hypot(*(np.array(p1) - np.array(p0))); d = (np.array(p1) - np.array(p0)) / L; nrm = np.array([-d[1], d[0]])
    knots = np.sort(rng.uniform(0, 1, n)); off = np.cumsum(rng.normal(0, amp * L, n)) * 0.6
    off -= np.linspace(0, off[-1], n)
    u = ((pts - np.array(p0)) @ d) / L
    return pts + nrm[None] * np.interp(u, np.concatenate([[0], knots, [1]]), np.concatenate([[0], off, [0]]))[:, None]

class Lightning:
    """闪电：主干（中点位移分形）+ 递归分叉 + 先导生长 + 多次回击闪烁。
    Lightning(seed, p0=(x,y) 云端, p1=(x,y) 落点, branches=7, rough=0.09, depth=8)
    env(t, t0)                    → 0..~1 亮度包络（可给角色/场景补光用）
    draw(fr, t, t0, intensity=1, color=(0.93,0.95,1.0), grow=0.05, sky=0.35, width=3.0, glow=1.0)
      t0 = 闪电主击时刻；t0-grow..t0 先导自上而下生长（暗、细、分叉多），t0 起整根贯通爆亮并按 strokes 闪烁。
    cloud_flash(fr, t, t0, center, radius, seed, intensity) 云内亮（独立函数，可单独用作“云缝预亮”）。"""
    STROKES = ((0.0, 1.0), (0.075, 0.55), (0.14, 0.85), (0.27, 0.35))

    def __init__(self, seed=0, p0=(900, 60), p1=(1060, 900), branches=7, rough=0.09, depth=8, gold=False):
        rng = np.random.default_rng(seed); self.seed = seed
        main = _bolt(rng, p0, p1, rough, depth)
        main = _kink(rng, main, p0, p1)
        self.paths = [(main, 1.0, 0.0)]                  # (pts, 粗细系数, 起点在主干上的进度)
        n = len(main)
        for b in range(branches):
            i = int(rng.uniform(0.08, 0.75) * n); a = main[i]
            d = main[min(n - 1, i + 6)] - a; ang = math.atan2(d[1], d[0]) + rng.choice([-1, 1]) * rng.uniform(0.35, 0.9)
            Lb = np.hypot(*(np.array(p1) - np.array(p0))) * rng.uniform(0.12, 0.38)
            e = a + Lb * np.array([math.cos(ang), math.sin(ang)])
            bp = _bolt(rng, a, e, rough * 1.2, depth - 2)
            self.paths.append((bp, rng.uniform(0.3, 0.55), i / n))
            if rng.random() < 0.6:                      # 二级分叉
                j = int(rng.uniform(0.2, 0.7) * len(bp)); a2 = bp[j]
                ang2 = ang + rng.choice([-1, 1]) * rng.uniform(0.3, 0.8)
                e2 = a2 + Lb * 0.5 * np.array([math.cos(ang2), math.sin(ang2)])
                self.paths.append((_bolt(rng, a2, e2, rough * 1.3, depth - 3), 0.2, i / n + j / len(bp) * 0.1))
        self.p0, self.p1 = np.array(p0, float), np.array(p1, float)
        self.gold = gold

    def env(self, t, t0):
        dt = t - t0
        if dt < -0.08: return 0.0
        if dt < 0: return 0.08 * (1 + dt / 0.08)
        return float(sum(a * math.exp(-max(0, dt - o) / 0.045) * (dt >= o) for o, a in self.STROKES))

    def draw(self, fr, t, t0, intensity=1.0, color=(0.93, 0.95, 1.0), grow=0.05, sky=0.35, width=3.0, glow=1.0):
        dt = t - t0
        if dt < -grow or dt > 0.9: return fr
        e = self.env(t, t0) * intensity
        lead = dt < 0
        prog = 1.0 if not lead else (dt + grow) / grow
        k = 2
        core = np.zeros((H // k, W // k), np.float32)
        for pts, wscale, start in self.paths:
            if lead:
                if start > prog: continue
                m = max(2, int(len(pts) * min(1, (prog - start) / max(1e-3, 1 - start) * 1.3)))
                pp = pts[:m]
            else:
                pp = pts
                if wscale < 0.5 and dt > 0.16: continue    # 后几次回击只亮主干
            P = np.round(pp / k * 8).astype(np.int32)
            wpx = max(1, int(round(width * wscale / k * (0.5 if lead else 1))))
            val = (0.35 if lead else 1.0) * (0.6 + 0.4 * wscale)
            cv2.polylines(core, [P], False, float(val), wpx, cv2.LINE_AA, 3)
        amp = max(e, 0.25 if lead else 0)
        c = WHITE_GOLD if self.gold else _f32(color)
        g1 = cv2.GaussianBlur(core, (0, 0), 3)
        q = cv2.resize(core, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        g2 = cv2.resize(cv2.GaussianBlur(q, (0, 0), 6), (W // k, H // k))
        lay = core * 1.8 + g1 * 1.2 * glow + g2 * 3.0 * glow
        fr = add(fr, lay, c, amp)
        if sky > 0 and not lead:
            fr = cloud_flash(fr, t, t0, center=tuple(self.p0), radius=900, seed=self.seed, intensity=sky * e / max(intensity, 1e-3) * intensity, env=e)
        return fr


def cloud_flash(fr, t, t0=None, center=(960, 150), radius=700, seed=0, intensity=0.6, env=None, color=(0.85, 0.88, 0.95),
                mask=None, cloud=None):
    """云内亮：用 fbm 云纹调制的径向光斑，模拟雷光在云层内部游走照亮云团（不出现闪电主干）。
    env 直接给亮度；否则按 t0 计算单次闪烁（预亮：t0 前 0.3s 微光脉动）。mask=(H,W) 只亮天空区域。"""
    if env is None:
        dt = t - t0
        env = 0.0
        for o, a in ((0, 1.0), (0.09, 0.5), (0.21, 0.7)):
            if dt >= o: env += a * math.exp(-(dt - o) / 0.06)
        if -0.3 < dt < 0: env += 0.12 * (0.5 + 0.5 * math.sin(dt * 90))
    if env <= 0.003: return fr
    h, w = H // 4, W // 4
    cl = cloud if cloud is not None else scroll(noise(256, seed + 11, base=3, octaves=6), t * 6, 0, h, w, 1.6)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d2 = ((xx * 4 - center[0]) ** 2 + (yy * 4 - center[1]) ** 2) / radius ** 2
    L = np.exp(-d2) * (0.35 + 2.4 * np.clip(cl - 0.3, 0, 1) ** 1.2) * env * intensity
    L = cv2.resize(L.astype(np.float32), (W, H))
    if mask is not None: L *= mask
    fr *= (1 + L[..., None] * 2.2)
    return add(fr, L * 0.45, color, 1.0)


# ============================================================== 体积光
def god_rays(fr, src, emit=None, strength=1.0, length=1.0, color=GOLD, t=0.0, shafts=0.6, src_r=120, seed=0, passes=6,
             occluder=None):
    """体积光（丁达尔光柱）：从光源 src=(x,y) 向外的径向光束。
    emit     (H,W) 发光源图（如月盘、云缝、门缝的亮度）；None 则用半径 src_r 的光盘
    occluder (H,W) 0..1 遮挡物（1=挡光，例如人物/城楼剪影 alpha），产生暗光柱（剪影切出的光束）
    length   光束长度（0..1，越大越长），shafts 角向光柱强弱（随 t 缓慢呼吸），strength 总强度。"""
    k = 4; h, w = H // k, W // k
    if emit is None:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.hypot(xx * k - src[0], yy * k - src[1]) / src_r
        E = np.clip(1.3 - d, 0, 1) ** 1.5
    else:
        E = cv2.resize(emit.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
    if occluder is not None:
        E = E * (1 - cv2.resize(occluder.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA))
    if shafts > 0:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        ang = (np.arctan2(yy * k - src[1], xx * k - src[0]) / (2 * math.pi) + 0.5)
        ln = noise(512, seed + 5, base=12, octaves=4)[0]
        ln2 = noise(512, seed + 6, base=30, octaves=2)[0]
        idx = (ang * 511 + t * 3).astype(np.int32) % 512; idx2 = (ang * 511 - t * 5).astype(np.int32) % 512
        mod = (1 - shafts) + shafts * 1.6 * np.clip(ln[idx] * 0.7 + ln2[idx2] * 0.5 - 0.2, 0, 1.2)
        E = E * mod
    acc = E.copy()
    sx, sy = src[0] / k, src[1] / k
    f = 1 + length * 1.2
    for p in range(passes):
        s = 1.0 / f
        M = np.array([[s, 0, sx * (1 - s)], [0, s, sy * (1 - s)]], np.float32)
        acc = 0.5 * acc + 0.5 * cv2.warpAffine(acc, M, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
        f = 1 + (f - 1) * 0.55
        acc = np.maximum(acc, E * 0.5)
    acc = cv2.GaussianBlur(acc, (0, 0), 1.2)
    return add(fr, acc, color, strength * 1.4)


def light_beam(fr, p0, p1, w0, w1, t=0.0, color=GOLD, strength=0.6, dust=80, seed=0, stripes=0.6, soft=0.5):
    """单束锥形体积光（月光斜射、裂缝光束、窗光）：p0 光源端（宽 w0），p1 远端（宽 w1）。
    内部纵向条纹缓慢漂移，浮尘颗粒在光中闪烁上浮。返回 fr。"""
    k = 2
    p0 = np.array(p0, np.float32); p1 = np.array(p1, np.float32)
    ax = p1 - p0; Lx = float(np.hypot(*ax)); ux = ax / (Lx + 1e-6); nx = np.array([-ux[1], ux[0]], np.float32)
    corners = np.array([p0 + nx * w0, p0 - nx * w0, p1 + nx * w1, p1 - nx * w1])
    x0 = int(max(0, corners[:, 0].min() - 20)); x1 = int(min(W, corners[:, 0].max() + 20))
    y0 = int(max(0, corners[:, 1].min() - 20)); y1 = int(min(H, corners[:, 1].max() + 20))
    if x1 <= x0 or y1 <= y0: return fr
    hh, ww = (y1 - y0) // k + 1, (x1 - x0) // k + 1
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    X = xx * k + x0 - p0[0]; Y = yy * k + y0 - p0[1]
    u = (X * ux[0] + Y * ux[1]) / Lx; v = X * nx[0] + Y * nx[1]
    wid = w0 + (w1 - w0) * np.clip(u, 0, 1)
    vn = v / wid
    across = np.clip(1 - np.abs(vn), 0, 1) ** (1.0 + soft * 2)
    along = smooth(-0.02, 0.12, u) * (1 - smooth(0.6, 1.0, u)) * (u <= 1.0)
    I = across * along
    if stripes > 0:
        nz = noise(512, seed + 2, base=20, octaves=3)
        idx = ((vn * 0.5 + 0.5) * 300 + t * 6).astype(np.int32) % 512
        idy = (np.clip(u, 0, 1) * 40 + t * 2).astype(np.int32) % 512
        I = I * ((1 - stripes) + stripes * 1.7 * nz[idy, idx])
    I = I.astype(np.float32)
    lay = np.zeros((H // k, W // k), np.float32)
    ys, xs = y0 // k, x0 // k
    hh2 = min(hh, H // k - ys); ww2 = min(ww, W // k - xs)
    lay[ys:ys + hh2, xs:xs + ww2] = I[:hh2, :ww2]
    if dust:
        rng = np.random.default_rng(seed)
        uu = rng.random(dust); vv = rng.uniform(-1, 1, dust); ph = rng.uniform(0, 6.28, dust)
        uu = (uu - t * 0.015 * rng.uniform(0.5, 1.5, dust)) % 1.0
        vv = vv + 0.08 * np.sin(t * 0.7 + ph)
        wi = w0 + (w1 - w0) * uu
        P = p0[None] + ux[None] * (uu * Lx)[:, None] + nx[None] * (vv * wi * 0.9)[:, None]
        tw = 0.5 + 0.5 * np.sin(t * rng.uniform(2, 6, dust) + ph)
        for (px, py), a_, z in zip(P, tw, rng.random(dust)):
            cv2.circle(lay, (int(px / k * 4), int(py / k * 4)), int(4 + z * 6), float(0.8 * a_ * (1 - abs(0.5 - (px - x0) / max(1, x1 - x0)))), -1, cv2.LINE_AA, 2)
    lay = cv2.GaussianBlur(lay, (0, 0), 1.0)
    return add(fr, lay, color, strength)


# ============================================================== 裂缝金光
class CrackLight:
    """裂缝 + 金光涌出。
    CrackLight(seed, p0, p1, rough=0.12, branches=6, depth=6)
    draw(fr, t, prog=1, open_=1, spill=1, color=GOLD, motes=60, wall_dark=0.6)
      prog  裂缝沿 p0→p1 生长进度（0..1）；open_ 裂开宽度（0 细线 .. 1 张开 .. 3 大开）
      spill 溢光强度（核心白金 + 宽泛光 + 向外光扇），motes 上浮金尘数量
      wall_dark 裂缝两侧压暗（制造深度）
    mask(prog, open_) 返回 (H,W) 裂缝 alpha，可用来给墙体/画面开口。"""
    def __init__(self, seed=0, p0=(960, 140), p1=(960, 960), rough=0.12, branches=6, depth=6):
        rng = np.random.default_rng(seed); self.seed = seed; self.rng = rng
        main = _bolt(rng, p0, p1, rough, depth)
        self.main = main; n = len(main)
        self.br = []
        for b in range(branches):
            i = int(rng.uniform(0.05, 0.92) * n); a = main[i]
            d = main[min(n - 1, i + 3)] - main[max(0, i - 3)]
            ang = math.atan2(d[1], d[0]) + rng.choice([-1, 1]) * rng.uniform(0.5, 1.3)
            L = np.hypot(*(np.array(p1) - np.array(p0))) * rng.uniform(0.04, 0.14)
            e = a + L * np.array([math.cos(ang), math.sin(ang)])
            self.br.append((_bolt(rng, a, e, rough * 1.5, 4), i / n))
        seg = np.hypot(*np.diff(main, axis=0).T); self.cum = np.concatenate([[0], np.cumsum(seg)]) / seg.sum()
        self.wvar = 0.55 + 0.9 * noise(256, seed + 1, base=6, octaves=3)[0][np.linspace(0, 255, n).astype(int)]

    def mask(self, prog=1.0, open_=1.0, k=2):
        m = np.zeros((H // k, W // k), np.float32)
        n = int(np.searchsorted(self.cum, prog)) + 1
        pts = self.main[:max(2, n)]
        wv = self.wvar
        for i in range(len(pts) - 1):
            ww = max(1, int(round((1.0 + 7 * open_ * wv[i]) / k)))
            cv2.line(m, tuple(np.round(pts[i] / k * 8).astype(int)), tuple(np.round(pts[i + 1] / k * 8).astype(int)), 1.0, ww,
                     cv2.LINE_AA, 3)
        for bp, s in self.br:
            if s < prog:
                q = min(1, (prog - s) / 0.15); mm = max(2, int(len(bp) * q))
                cv2.polylines(m, [np.round(bp[:mm] / k * 8).astype(np.int32)], False, 0.8, max(1, int(round((1 + 2 * open_) / k))),
                              cv2.LINE_AA, 3)
        return m

    def draw(self, fr, t, prog=1.0, open_=1.0, spill=1.0, color=GOLD, motes=60, wall_dark=0.6):
        if prog <= 0: return fr
        k = 2
        m = self.mask(prog, open_, k)
        flick = 1 + 0.08 * math.sin(t * 23) + 0.05 * math.sin(t * 37 + 1)
        if wall_dark > 0:
            dk = cv2.GaussianBlur(m, (0, 0), 6 + 6 * open_)
            fr *= (1 - np.clip(cv2.resize(dk, (W, H)) * wall_dark * 1.5, 0, 0.85))[..., None]
        g1 = cv2.GaussianBlur(m, (0, 0), 3)
        q = cv2.resize(m, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        g2 = cv2.resize(cv2.GaussianBlur(q, (0, 0), 5 + 3 * open_), (W // k, H // k))
        g3 = cv2.resize(cv2.GaussianBlur(q, (0, 0), 18), (W // k, H // k))
        fr = add(fr, m, WHITE_GOLD, 1.6 * flick * min(1.5, 0.5 + open_))
        fr = add(fr, g1 * 1.0 + g2 * 2.2 + g3 * 1.6, color, spill * flick)
        if spill > 0.3:                                   # 光扇：从裂缝中心向外的径向光束
            c = self.main[len(self.main) // 2]
            fr = god_rays(fr, tuple(c), emit=cv2.resize(m, (W, H)) * 3, strength=0.35 * spill, length=0.5, color=color, t=t,
                          shafts=0.8, seed=self.seed)
        if motes:
            rng = np.random.default_rng(self.seed + 9)
            lay = np.zeros((H // k, W // k), np.float32)
            n = int(np.searchsorted(self.cum, prog)) + 1
            idx = rng.integers(0, max(1, n - 1), motes); ph = rng.random(motes); sp = rng.uniform(30, 90, motes)
            for i in range(motes):
                age = (t * 0.35 + ph[i]) % 1.0
                bx, by = self.main[idx[i]]
                px = bx + math.sin(t * 1.3 + i) * 30 * age + rng.normal(0, 1) * 0 + (i % 2 * 2 - 1) * age * 60
                py = by - sp[i] * age * 2.5
                a = math.sin(math.pi * age) * (0.6 + 0.4 * math.sin(t * 9 + i))
                cv2.circle(lay, (int(px / k * 4), int(py / k * 4)), 6 + (i % 3) * 3, float(a), -1, cv2.LINE_AA, 2)
            lay = cv2.GaussianBlur(lay, (0, 0), 0.8) + cv2.GaussianBlur(lay, (0, 0), 4) * 0.8
            fr = add(fr, lay, color, 1.2 * min(1, spill + 0.3))
        return fr


# ============================================================== 余烬 / 金尘 / 灰烬
class Embers:
    """飞火余烬（mode='fire'）/ 金色光尘（'gold'）/ 灰烬碎屑（'ash'，灰色、翻转、非发光）。无状态。
    Embers(seed, n=220, box=(0,120,W,960), mode='fire', rise=180, life=(1.2,3.0), depth=True)
    draw(fr, t, intensity=1, wind=(40,0), t0=None, burst=None)
      wind   (vx,vy) 像素/秒 附加风；t0 给定则从 t0 起才出现（爆发式）；burst=(x,y,速度) 从一点爆散（火星爆发）
      深度分层：z 小=近：粒子更大、更快、焦外虚化光斑（景深）；z 大=远：细小锐利。"""
    def __init__(self, seed=0, n=220, box=(0, 120, W, 960), mode='fire', rise=180, life=(1.2, 3.0), depth=True):
        r = np.random.default_rng(seed); self.n = n; self.box = box; self.mode = mode; self.rise = rise
        self.ph = r.random(n); self.life = r.uniform(*life, n)
        self.x = r.uniform(box[0], box[2], n); self.y = r.uniform(box[1], box[3], n)
        self.z = r.random(n) ** (0.7 if depth else 1e9)
        self.f1 = r.uniform(0.5, 2.0, n); self.f2 = r.uniform(0.3, 1.2, n); self.a = r.uniform(0, 6.28, n)
        self.sz = r.uniform(0.6, 1.4, n); self.ang = r.normal(0, 1, n); self.spd = r.uniform(0.6, 1.4, n)

    def draw(self, fr, t, intensity=1.0, wind=(40, 0), t0=None, burst=None, color=None):
        if intensity <= 0: return fr
        k = 2
        sharp = np.zeros((H // k, W // k), np.float32); bokeh = np.zeros((H // 4, W // 4), np.float32)
        hot = np.zeros((H // k, W // k), np.float32)
        ash = self.mode == 'ash'
        if ash: ash_a = np.zeros((H // k, W // k), np.float32); ash_c = np.zeros((H // k, W // k), np.float32)
        bx0, by0, bx1, by1 = self.box
        for i in range(self.n):
            L = self.life[i]
            if burst is not None:
                age = t - (t0 if t0 is not None else 0) - self.ph[i] * 0.15
                if age < 0 or age > L: continue
            else:
                tt = t if t0 is None else t - t0
                if t0 is not None and tt < 0: continue
                age = (tt + self.ph[i] * L) % L
                if t0 is not None and tt < self.ph[i] * L * 0: continue
            u = age / L
            z = self.z[i]; near = 1 - z
            par = 0.4 + 1.4 * near
            if burst is not None:
                ang = self.a[i]; sp = burst[2] * self.spd[i] * (0.5 + near)
                px = burst[0] + math.cos(ang) * sp * age * (1 - 0.35 * age) + wind[0] * age
                py = burst[1] + math.sin(ang) * sp * 0.7 * age * (1 - 0.35 * age) - self.rise * 0.5 * age + wind[1] * age + 60 * age * age
                vx = math.cos(ang) * sp + wind[0]; vy = math.sin(ang) * sp * 0.7 - self.rise * 0.5
            else:
                vx = wind[0] * par + 40 * math.sin(t * self.f1[i] + self.a[i]) * par
                vy = -(self.rise if not ash else -self.rise * 0.35) * par * self.spd[i] + wind[1] * par + 25 * math.cos(t * self.f2[i] + self.a[i])
                px = (self.x[i] + vx * age - bx0) % (bx1 - bx0 + 1) + bx0
                py = self.y[i] + vy * age
                if not (by0 - 100 < py < by1 + 100):
                    py = (py - by0) % (by1 - by0) + by0
            fade = math.sin(math.pi * min(1, u)) ** 0.8
            flick = 0.65 + 0.35 * math.sin(t * (13 + 7 * self.f1[i]) + self.a[i])
            a = fade * flick * intensity
            if ash:
                s = (2 + 7 * near) * self.sz[i]
                rot = t * self.f1[i] * 3 + self.a[i]
                sx = abs(math.cos(rot)) * s + 0.6; sy = s * 0.7
                pts = cv2.ellipse2Poly((int(px / k * 4), int(py / k * 4)), (int(sx * 4 / k + 1), int(sy * 4 / k + 1)),
                                       int(math.degrees(self.ang[i])), 0, 360, 60)
                cv2.fillPoly(ash_a, [pts], float(fade * (0.75 + 0.25 * near)), cv2.LINE_AA, 2)
                cv2.fillPoly(ash_c, [pts], float(fade * (0.75 + 0.25 * near) * (0.2 + 0.8 * abs(math.sin(rot)))), cv2.LINE_AA, 2)
                continue
            sl = 0.03 * (0.6 + near)
            qx, qy = px - vx * sl, py - vy * sl
            if near > 0.78 and burst is None:              # 焦外光斑
                cv2.circle(bokeh, (int(px / 4 * 4), int(py / 4 * 4)), int((3 + 9 * near) * self.sz[i] * 4 / 4), float(a * 0.35), -1,
                           cv2.LINE_AA, 2)
            else:
                w_ = max(1, int(round((0.8 + 2.2 * near) * self.sz[i] / k)))
                cv2.line(sharp, (int(px / k * 8), int(py / k * 8)), (int(qx / k * 8), int(qy / k * 8)), float(a), w_, cv2.LINE_AA, 3)
                if u < 0.45: cv2.circle(hot, (int(px / k * 8), int(py / k * 8)), max(1, w_), float(a * (1 - u / 0.45)), -1, cv2.LINE_AA, 3)
        if ash:
            A = cv2.resize(cv2.GaussianBlur(ash_a, (0, 0), 0.7), (W, H)); C = cv2.resize(cv2.GaussianBlur(ash_c, (0, 0), 0.7), (W, H))
            col = (0.35 + 0.6 * C / np.maximum(A, 1e-3))[..., None] * np.array([1, 0.98, 0.95], np.float32)
            a3 = np.clip(A, 0, 1)[..., None] * intensity
            fr[:] = fr * (1 - a3) + col * a3
            return fr
        if self.mode == 'gold':
            c1, c2 = color if color is not None else (GOLD * 1.6, WHITE_GOLD)
        else:
            c1, c2 = (GOLD * 1.0 + RED * 0.6, WHITE_GOLD) if color is None else color
        g = cv2.GaussianBlur(sharp, (0, 0), 2.5)
        fr = add(fr, sharp * 1.3 + g * 1.4, c1, 1.0)
        fr = add(fr, hot, c2, 0.9)
        fr = add(fr, cv2.GaussianBlur(bokeh, (0, 0), 1.5), c1, 1.0)
        return fr


# ============================================================== 雾
class Fog:
    """分层流动雾。draw(fr, t, density=0.5, y0=500, y1=960, color=(0.55,0.57,0.6), speed=(30,0), light=None, light_r=600,
                     light_color=COLD, layers=2, scale=1.0, cam=(0,0), top_fade=200)
      y0..y1 雾带（屏幕 y），向上淡出 top_fade；speed 像素/秒；light 光源附近雾被照亮（散射）；
      cam 相机位移 → 层间视差。也可 mask=(H,W) 指定任意雾区（如墙后、地面）。"""
    def __init__(self, seed=0):
        self.seed = seed
        self.tex = [noise(512, seed + 31, base=3, octaves=6), noise(512, seed + 32, base=5, octaves=5)]

    def draw(self, fr, t, density=0.5, y0=500, y1=960, color=(0.55, 0.57, 0.6), speed=(30, 0), light=None, light_r=600,
             light_color=COLD, layers=2, scale=1.0, cam=(0, 0), top_fade=200, mask=None):
        if density <= 0: return fr
        k = 4; h, w = H // k, W // k
        A = np.zeros((h, w), np.float32)
        for li in range(layers):
            f = 1 + li * 0.8
            tx = self.tex[li % 2]
            n = scroll(tx, (t * speed[0] * f + cam[0] * f * 0.5) / k / (2.2 * scale), (t * speed[1] * f + cam[1] * f * 0.5) / k / (2.2 * scale),
                       h, w, 2.2 * scale * (1.0 / f) ** 0.4)
            A += np.clip((n - 0.3) * 1.6, 0, 1) * (0.7 if li else 1.0)
        A /= layers * 0.85
        yy = np.arange(h, dtype=np.float32)[:, None] * k
        band = smooth(y0 - top_fade, y0 + top_fade * 0.3, yy) * (1 - smooth(y1, y1 + 120, yy))
        A = A * band * density
        if mask is not None: A *= cv2.resize(mask.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
        A = cv2.GaussianBlur(A, (0, 0), 1.5)
        col = np.broadcast_to(_f32(color), (h, w, 3)).copy()
        if light is not None:
            xx = np.arange(w, dtype=np.float32)[None, :] * k
            g = np.exp(-(((xx - light[0]) ** 2 + (yy - light[1]) ** 2) / light_r ** 2))
            col = col + g[..., None] * _f32(light_color) * 0.8
        Af = cv2.resize(np.clip(A, 0, 0.95), (W, H))[..., None]
        Cf = cv2.resize(col, (W, H))
        fr[:] = fr * (1 - Af) + Cf * Af
        return fr
