"""units/vcam.py — 虚拟摄像机（副歌一 v2 起各摄制组通用）

纯函数式、无逐帧状态：任何时刻 t 的机位都由「基础运镜曲线 + 所有已发生击打的弹簧阻尼脉冲响应之和」解析算出，
所以分块 / 跳帧渲染结果完全一致。

坐标约定（与 c1kit.cam 一致）：z 缩放（>1 推近）、ox/oy 视点平移（正值 = 镜头向右/下看 = 画面内容向左/上走）、rot 度。

组成
1. 卡点脉冲（来自 crew/hitmap_*.json，时间已提前 1 帧 = 感知同步）
   - 底鼓 kick   ：推近 punch-in（瞬时跳入，欠阻尼回弹）+ 一次随机方向衰减抖动
   - 军鼓 snare  ：反向——轻微拉远 + 交替方向旋震 + 垂直顿挫
   - 镲 hat      ：细碎高频抖
   - 重音镲 crash：大号 punch + 强抖
   - 重音字 accent：额外 punch（字落点冲击放大）
   强度乘以段落能量包络 energy(t)（强弱交替 / 呼吸），以及每镜的 gain。
2. 基础运镜 Move：各通道 (起, 止) + 缓动曲线 + 速度坡度 ramp（快-慢-快 'fsf' / 慢-快-慢 'sfs'）。
3. 甩镜衔接 Whip：切点前 n 帧沿方向 v 加速甩出，切点后 m 帧从同方向减速甩入（上一镜甩出方向 = 下一镜进入方向）。
4. 由相机速度自动生成方向运动模糊（快门 180°）+ 推拉径向模糊。
5. 前景视差层 FG：近镜头虚焦粒子（余烬/灰/雨珠），按深度 d 以 d 倍相机位移移动 → 与画面主体形成视差纵深。
"""
import json, math
import numpy as np, cv2

FPS = 30
LEAD = 1.0 / FPS          # 视觉比声音早 1 帧
W, H = 1920, 1080


# ------------------------------------------------------------------ 缓动曲线（不用线性）
def _c(x): return min(1.0, max(0.0, float(x)))
def lin(x): return _c(x)
def sine_io(x): x = _c(x); return 0.5 - 0.5 * math.cos(math.pi * x)
def cubic_io(x): x = _c(x); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def quint_io(x): x = _c(x); return 16 * x ** 5 if x < 0.5 else 1 - (-2 * x + 2) ** 5 / 2
def expo_io(x):
    x = _c(x)
    if x in (0.0, 1.0): return x
    return 2 ** (20 * x - 10) / 2 if x < 0.5 else (2 - 2 ** (-20 * x + 10)) / 2
def expo_out(x): x = _c(x); return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)
def expo_in(x): x = _c(x); return 0.0 if x <= 0 else 2 ** (10 * x - 10)
def quart_out(x): x = _c(x); return 1 - (1 - x) ** 4
def quart_in(x): x = _c(x); return x ** 4
def back_out(x, s=1.70158): x = _c(x) - 1; return 1 + (s + 1) * x ** 3 + s * x ** 2
def circ_out(x): x = _c(x); return math.sqrt(1 - (x - 1) ** 2)

EASE = dict(lin=lin, sine_io=sine_io, cubic_io=cubic_io, quint_io=quint_io, expo_io=expo_io, expo_out=expo_out,
            expo_in=expo_in, quart_out=quart_out, quart_in=quart_in, back_out=back_out, circ_out=circ_out)


def ramp(u, kind=None, k=0.8):
    """速度坡度（时间重映射，保持 0→0、1→1）。
    'fsf' 快-慢-快：导数 1+k·cos(2πu)，两端快中间几乎停住（甩入→憋住→甩出）
    'sfs' 慢-快-慢；'fs' 先快后慢（冲进来刹住）；'sf' 先慢后快（蓄力后爆发）"""
    u = _c(u)
    if kind is None: return u
    if kind == 'fsf': return u + k * math.sin(2 * math.pi * u) / (2 * math.pi)
    if kind == 'sfs': return u - k * math.sin(2 * math.pi * u) / (2 * math.pi)
    if kind == 'fs': return 1 - (1 - u) ** (1 + 2 * k)
    if kind == 'sf': return u ** (1 + 2 * k)
    return u


# ------------------------------------------------------------------ 弹簧阻尼脉冲响应
def spring_punch(tau, f=4.0, zeta=0.45):
    """t=0 瞬时跳到 1（零斜率），欠阻尼衰减回 0：推近冲击的形状"""
    if tau < 0: return 0.0
    w = 2 * math.pi * f; wd = w * math.sqrt(1 - zeta ** 2)
    return math.exp(-zeta * w * tau) * (math.cos(wd * tau) + zeta / math.sqrt(1 - zeta ** 2) * math.sin(wd * tau))


def spring_kick(tau, f=9.0, zeta=0.25):
    """t=0 从 0 以最大速度出发的衰减振荡（位移抖动）；峰值归一约 1"""
    if tau < 0: return 0.0
    w = 2 * math.pi * f; wd = w * math.sqrt(1 - zeta ** 2)
    return math.exp(-zeta * w * tau) * math.sin(wd * tau) * 1.25


class Move:
    """基础运镜：channels = dict(z=(a,b), x=(a,b), y=(a,b), rot=(a,b))，ease 缓动、ramp 速度坡度"""
    def __init__(self, ease='cubic_io', ramp_=None, k=0.8, **ch):
        self.ease = EASE[ease]; self.ramp = ramp_; self.k = k
        self.ch = {c: ch.get(c, (0.0, 0.0) if c != 'z' else (1.0, 1.0)) for c in ('z', 'x', 'y', 'rot')}

    def at(self, u):
        e = self.ease(ramp(u, self.ramp, self.k))
        return {c: a + (b - a) * e for c, (a, b) in self.ch.items()}


class VCam:
    def __init__(self, hitmap, energy=None, lead=LEAD, seed=7):
        d = json.load(open(hitmap)) if isinstance(hitmap, str) else hitmap
        self.d = d
        r = np.random.default_rng(seed)
        self.kicks, self.snares, self.hats, self.crashes, self.accents = [], [], [], [], []
        for h in d['hits']:
            tv = h['t'] - lead; s = h['strength']; ty = h['type']
            if 'kick' in ty: self.kicks.append((tv, s, r.uniform(0, 2 * math.pi)))
            if 'snare' in ty: self.snares.append((tv, s, 1 if len(self.snares) % 2 == 0 else -1))
            if 'hat' in ty and 'snare' not in ty: self.hats.append((tv, s, r.uniform(0, 2 * math.pi)))
            if 'crash' in ty: self.crashes.append((tv, s, r.uniform(0, 2 * math.pi)))
        for w in d['words']:
            if w['accent']: self.accents.append((w['t'] - lead, 1.0, r.uniform(0, 2 * math.pi)))
        self.energy = energy or (lambda t: 1.0)
        self.moves = []          # [(t0, t1, Move, gain)]
        self.whips = []          # [(t_cut, (vx,vy), L, n_out, n_in)]
        self.holds = []          # [(t0, t1)] 定格/憋住段：脉冲静音
        self.hardcuts = []       # 非甩镜切点：运动模糊不跨切点计算

    # -------------------------------------------------------------- 配置
    def shot(self, t0, t1, move=None, gain=1.0):
        self.moves.append((t0, t1, move or Move(), gain))

    def whip(self, t_cut, direction, L=380, n_out=4, n_in=5):
        v = np.array(direction, float); v /= (np.linalg.norm(v) + 1e-9)
        self.whips.append((t_cut, tuple(v), L, n_out, n_in))

    def hold(self, t0, t1): self.holds.append((t0, t1))

    def cut(self, t): self.hardcuts.append(t)

    # -------------------------------------------------------------- 求值
    def _gain(self, t):
        for a, b, m, g in self.moves:
            if a <= t < b: return g
        return 1.0

    def _held(self, t): return any(a <= t < b for a, b in self.holds)

    def impulses(self, t):
        """卡点脉冲叠加 → (dz, dx, dy, drot, punch)；punch 为本帧冲击强度（给色差/闪光用）"""
        dz = dx = dy = dr = 0.0; punch = 0.0
        if self._held(t): return 0.0, 0.0, 0.0, 0.0, 0.0
        E = self.energy(t) * self._gain(t)
        for (tv, s, ang) in self.kicks:
            tau = t - tv
            if tau < 0 or tau > 1.0: continue
            if self._held(tv): continue
            p = spring_punch(tau, 3.6, 0.5)
            dz += 0.045 * s * p
            k = spring_kick(tau, 8.0, 0.28)
            dx += 9 * s * k * math.cos(ang); dy += 9 * s * k * math.sin(ang)
            punch = max(punch, s * math.exp(-tau / 0.06))
        for (tv, s, sg) in self.snares:
            tau = t - tv
            if tau < 0 or tau > 0.8 or self._held(tv): continue
            dz -= 0.018 * s * spring_punch(tau, 4.5, 0.5)                 # 反向：轻拉
            dr += sg * 0.9 * s * spring_kick(tau, 5.5, 0.3)               # 交替旋震
            dy += 7 * s * spring_kick(tau, 7.0, 0.35)
            punch = max(punch, 0.6 * s * math.exp(-tau / 0.05))
        for (tv, s, ang) in self.hats:
            tau = t - tv
            if tau < 0 or tau > 0.25 or self._held(tv): continue
            k = spring_kick(tau, 17.0, 0.45)
            dx += 2.2 * s * k * math.cos(ang); dy += 2.2 * s * k * math.sin(ang)
        for (tv, s, ang) in self.crashes:
            tau = t - tv
            if tau < 0 or tau > 1.4: continue
            dz += 0.08 * s * spring_punch(tau, 2.6, 0.42)
            k = spring_kick(tau, 6.5, 0.2)
            dx += 18 * s * k * math.cos(ang); dy += 18 * s * k * math.sin(ang)
            dr += 1.2 * s * spring_kick(tau, 4.0, 0.3)
            punch = max(punch, 1.3 * s * math.exp(-tau / 0.08))
        for (tv, s, ang) in self.accents:
            tau = t - tv
            if tau < 0 or tau > 0.8 or self._held(tv): continue
            dz += 0.03 * spring_punch(tau, 4.2, 0.45)
            punch = max(punch, 0.5 * math.exp(-tau / 0.05))
        return dz * E, dx * E, dy * E, dr * E, punch * E

    def base(self, t):
        z, x, y, r = 1.0, 0.0, 0.0, 0.0
        for a, b, m, g in self.moves:
            if a - 1e-6 <= t < b - 1e-6:
                c = m.at((t - a) / (b - a)); z, x, y, r = c['z'], c['x'], c['y'], c['rot']
                break
        for (tc, v, L, no, ni) in self.whips:
            to, ti = no / FPS, ni / FPS
            if tc - to - 1e-6 <= t < tc - 1e-6:            # 甩出：加速
                e = expo_in((t - (tc - to)) / to) * 0.85 + quart_in((t - (tc - to)) / to) * 0.15
                x += v[0] * L * e; y += v[1] * L * e
            elif tc - 1e-6 <= t < tc + ti - 1e-6:          # 甩入：同方向减速到位
                e = 1 - expo_out((t - tc) / ti)
                x -= v[0] * L * e; y -= v[1] * L * e
        return z, x, y, r

    def state(self, t):
        z, x, y, r = self.base(t)
        dz, dx, dy, dr, p = self.impulses(t)
        return dict(z=z * (1 + dz), x=x + dx, y=y + dy, rot=r + dr, punch=p)

    # -------------------------------------------------------------- 应用
    def apply(self, fr, t, overscan=1.035, shutter=0.5):
        """把机位施加到已渲染的镜头画面上；返回 (fr, st)。自动方向运动模糊 + 推拉径向模糊。"""
        st = self.state(t)
        tp = t - shutter / FPS
        cb = [c for c in self.hardcuts if tp < c <= t + 1e-6]
        if cb:      # 快门跨过硬切：上一镜的机位不算进本镜速度
            zb, xb, yb, rb = self.base(cb[-1] + 1e-5)
            dz_, dx_, dy_, dr_, _ = self.impulses(tp)
            s0 = dict(z=zb * (1 + dz_), x=xb + dx_, y=yb + dy_)
        else:
            s0 = self.state(tp)
        z = st['z'] * overscan
        M = cv2.getRotationMatrix2D((W / 2, H / 2), st['rot'], z)
        M[0, 2] -= st['x'] * z; M[1, 2] -= st['y'] * z
        out = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        vx, vy = -(st['x'] - s0['x']) * z, -(st['y'] - s0['y']) * z
        if math.hypot(vx, vy) > 3:
            out = motion_blur(out, vx, vy)
        dz = st['z'] / max(1e-6, s0['z']) - 1
        if abs(dz) > 0.006:
            out = radial_blur(out, (W / 2, H / 2), min(0.12, abs(dz) * 2.5))
        st['vel'] = (vx, vy)
        return out, st


def motion_blur(fr, dx, dy, scale=4):
    """方向运动模糊（降采样卷积，长度 = 位移像素）"""
    L = math.hypot(dx, dy) / scale
    if L < 0.75: return fr
    h, w = fr.shape[:2]
    sm = cv2.resize(fr, (w // scale, h // scale), interpolation=cv2.INTER_AREA)
    Lc = min(L, 60.0); k = int(Lc) * 2 + 1
    ker = np.zeros((k, k), np.float32); c = k // 2
    ux, uy = dx / math.hypot(dx, dy), dy / math.hypot(dx, dy)
    for i in range(k):
        s_ = i - c
        ker[int(round(c + uy * s_)), int(round(c + ux * s_))] += 1
    ker /= ker.sum()
    b = cv2.resize(cv2.filter2D(sm, -1, ker, borderType=cv2.BORDER_REFLECT), (w, h), interpolation=cv2.INTER_LINEAR)
    m = min(1.0, L / 3)
    return fr * (1 - m) + b * m


def radial_blur(fr, c, amt, n=6, scale=2):
    h, w = fr.shape[:2]
    sm = cv2.resize(fr, (w // scale, h // scale), interpolation=cv2.INTER_AREA)
    acc = sm.copy(); cc = (c[0] / scale, c[1] / scale)
    for k in range(1, n):
        M = cv2.getRotationMatrix2D(cc, 0, 1 + amt * k / n)
        acc += cv2.warpAffine(sm, M, (sm.shape[1], sm.shape[0]), borderMode=cv2.BORDER_REFLECT)
    return cv2.resize(acc / n, (w, h))


# ------------------------------------------------------------------ 前景视差层
class FGLayer:
    """近镜头虚焦粒子。depth d∈[1.5,3.2]：屏幕位移 = d × 相机位移（比主体快 → 视差纵深），尺寸/虚化随 d 增大。
    kind: 'ember'（金红火星）'ash'（灰烬）'rain'（近景雨珠拉丝）"""
    def __init__(self, seed=0, n=22):
        r = np.random.default_rng(seed)
        self.p = r.uniform(0, 1, (n, 2)); self.d = r.uniform(1.5, 3.2, n)
        self.v = r.normal(0, 1, (n, 2)); self.ph = r.uniform(0, 6.28, n)

    def draw(self, fr, t, st, kind='ash', amt=0.5, wind=(30, -40)):
        if amt <= 0 or kind is None: return fr
        q = 4; h, w = H // q, W // q
        Lm = np.zeros((h, w), np.float32)
        ox, oy, z = st['x'], st['y'], st['z']
        for (px, py), d, v, ph in zip(self.p, self.d, self.v, self.ph):
            sx = (px * (W + 600) + (wind[0] + v[0] * 25) * t * d - ox * d) % (W + 600) - 300
            sy = (py * (H + 400) + (wind[1] + v[1] * 20) * t * d - oy * d) % (H + 400) - 200
            sx = W / 2 + (sx - W / 2) * z ** d; sy = H / 2 + (sy - H / 2) * z ** d
            if kind == 'rain':
                cv2.line(Lm, (int(sx / q), int(sy / q)), (int((sx + 10 * d) / q), int((sy + 90 * d) / q)), 0.6, max(1, int(d * 0.8)), cv2.LINE_AA)
            else:
                rr = (2.5 + 3.5 * d) / q * (1 + 0.15 * math.sin(t * 3 + ph))
                cv2.circle(Lm, (int(sx / q), int(sy / q)), max(1, int(rr)), 0.5 + 0.5 * math.sin(t * 2 + ph) ** 2, -1, cv2.LINE_AA)
        Lm = cv2.GaussianBlur(Lm, (0, 0), 2.2)
        Lm = cv2.resize(Lm, (W, H))
        col = {'ember': np.array([1.0, 0.55, 0.25], np.float32), 'ash': np.array([0.75, 0.76, 0.8], np.float32),
               'rain': np.array([0.8, 0.85, 0.95], np.float32), 'gold': np.array([1.0, 0.76, 0.40], np.float32)}[kind]
        return fr + Lm[..., None] * col * amt
