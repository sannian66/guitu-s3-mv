"""units/vcam3.py — 虚拟摄像机 v3（副歌一第三轮：震动克制 + 运镜加量）

在 vcam.VCam 之上：
1. 卡点脉冲克制（ImpulseV3）
   - hi-hat 细碎抖：去掉
   - 军鼓：只留强拍（on_beat 且强度≥0.45），幅度 ≈ v2 的 1/3（旋 0.9°→0.3°，顿挫 7px→2.3px，轻拉 0.018→0.006）
   - 底鼓推近：只留小节第 1 拍、重音字、重音镲；幅度 0.045→0.022（约一半），去掉随机方向位移抖；
     弹簧改近临界阻尼（f 5.5Hz ζ0.8）→ 回弹短、干净，无二次振荡
   - 重音镲：推近 0.08→0.04，抖 18px→5px（ζ0.45 两三下就停），旋 1.2°→0.35°
   - 不叠加：所有保留的冲击按时间排序，与上一个保留冲击间隔 < 0.30s 的丢弃（重音镲可顶替）
2. 2.5D 主运镜（Move3 + 速度坡度 'beat'）
   通道：z 推拉、x/y 横移/升降、rot 荷兰角滚转、yaw 环绕（平面绕竖轴转 → 近大远小的透视）、pitch 仰俯/摇臂、
         vtg 变焦推拉（dolly zoom：中心主体不变、四周向外/内拉伸）、focus 焦点转移（0=前景实/场景虚 → 1=场景实/前景虚）
   'beat' 速度坡度：镜头内速度 = 底速 + 每个小节头/重音字后的指数加速脉冲，乐句末（镜尾）减速刹住 → 节奏感来自运镜速度。
   透视/滚转造成的露边由 auto-fit 自动补缩放（只看画面有效区 y∈[120,960]）。
3. 前中后景视差：FGOcc 前景遮挡物（芦苇/碎砖/立柱）按深度 d 倍机位位移移动，焦点转移时与场景反向虚实。
"""
import math
import numpy as np, cv2
from vcam import *          # noqa  缓动、spring、motion_blur、radial_blur、FGLayer、VCam
import vcam as _V

ACTIVE_Y = (120, 960)
FOC = 2300.0                 # 透视焦距（像素）


def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a + 1e-9))); return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ 运镜
class Move3:
    """ch: z,x,y,rot,yaw,pitch,vtg,focus 各 (起, 止)；ease 缓动；ramp_='beat' 时按镜头内的重拍做速度坡度。
    keys: 可选 [(u, {ch: 值}), ...] 多关键帧（u∈[0,1]，段内同一 ease）"""
    DEF = dict(z=1.0, x=0.0, y=0.0, rot=0.0, yaw=0.0, pitch=0.0, vtg=0.0, focus=1.0)

    def __init__(self, ease='sine_io', ramp_='beat', k=0.8, keys=None, note='', **ch):
        self.ease = EASE[ease]; self.ramp = ramp_; self.k = k; self.note = note
        self.ch = {c: ch.get(c, (v, v)) for c, v in self.DEF.items()}
        self.keys = keys
        self.warp = None                      # beat 坡度表（VCam3.shot 里按镜头时间生成）

    def at(self, u):
        if self.warp is not None:
            uu = float(np.interp(u, self.warp[0], self.warp[1]))
        else:
            uu = ramp(u, self.ramp, self.k) if self.ramp != 'beat' else u
        if self.keys:
            ks = self.keys
            for (ua, va), (ub, vb) in zip(ks, ks[1:]):
                if uu <= ub or (ub == ks[-1][0]):
                    e = self.ease((uu - ua) / max(1e-6, ub - ua))
                    out = {}
                    for c, d in self.DEF.items():
                        a = va.get(c, d); b = vb.get(c, va.get(c, d))
                        out[c] = a + (b - a) * e
                    return out
        e = self.ease(uu)
        return {c: a + (b - a) * e for c, (a, b) in self.ch.items()}


def beat_warp(t0, t1, surges, base=0.35, amp=1.0, tau=0.22, tail=0.32, tail_k=0.8, n=240):
    """速度坡度表：v(t) = base + Σ amp·exp(-(t-ts)/tau)（ts=重拍）；镜尾 tail 比例内乘 (1-tail_k·smooth) 刹车。
    返回 (u, U) 单调映射表（U 为累计位移归一）。"""
    ts = np.linspace(t0, t1, n)
    v = np.full(n, base)
    for s, a in surges:
        m = ts >= s
        v[m] += amp * a * np.exp(-(ts[m] - s) / tau)
    d = t1 - t0
    lt = min(0.55, tail * d)
    brake = np.array([1 - tail_k * smooth(t1 - lt, t1, x) for x in ts])
    v = v * brake
    U = np.concatenate([[0], np.cumsum((v[1:] + v[:-1]) / 2 * np.diff(ts))])
    U /= U[-1]
    return np.linspace(0, 1, n), U


# ------------------------------------------------------------------ 相机
class VCam3(VCam):
    REFRACT = 0.30

    def __init__(self, hitmap, energy=None, lead=LEAD, seed=7):
        super().__init__(hitmap, energy, lead, seed)
        d = self.d
        self.downbeats = [b['t'] - lead for b in d['beats'] if b['pos'] == 1]
        acc = [w['t'] - lead for w in d['words'] if w['accent']]
        self.accent_t = acc
        ev = []          # (t, kind, strength)
        for h in d['hits']:
            tv = h['t'] - lead; s = h['strength']; ty = h['type']
            if 'crash' in ty:
                ev.append((tv, 'crash', s)); continue
            near_acc = any(abs(tv - a) < 0.07 for a in acc)
            if 'kick' in ty and ((h['beat_pos'] == 1 and h['on_beat']) or near_acc):
                ev.append((tv, 'kick', s)); continue
            if 'snare' in ty and h['on_beat'] and s >= 0.45:
                ev.append((tv, 'snare', s))
        for a in acc:
            if not any(abs(a - e[0]) < 0.07 for e in ev):
                ev.append((a, 'accent', 1.0))
        ev.sort()
        kept = []
        for e in ev:
            if kept and e[0] - kept[-1][0] < self.REFRACT:
                if e[1] == 'crash' and kept[-1][1] != 'crash':
                    kept[-1] = e
                continue
            kept.append(e)
        self.events = kept
        self.cand_events = ev

    # -------------------------------------------------- 克制版卡点脉冲
    def impulses(self, t):
        dz = dx = dy = dr = 0.0; punch = 0.0
        if self._held(t): return 0.0, 0.0, 0.0, 0.0, 0.0
        E = self.energy(t) * self._gain(t)
        r = 1
        for (tv, kind, s) in self.events:
            tau = t - tv
            if tau < 0 or tau > 0.6 or self._held(tv): continue
            if kind == 'kick':
                dz += 0.022 * s * spring_punch(tau, 5.5, 0.8)
                punch = max(punch, 0.6 * s * math.exp(-tau / 0.05))
            elif kind == 'accent':
                dz += 0.016 * spring_punch(tau, 5.5, 0.8)
                punch = max(punch, 0.35 * math.exp(-tau / 0.05))
            elif kind == 'snare':
                dz -= 0.006 * s * spring_punch(tau, 5.5, 0.8)
                dr += 0.3 * s * spring_kick(tau, 6.0, 0.55)
                dy += 2.3 * s * spring_kick(tau, 7.0, 0.55)
                punch = max(punch, 0.3 * s * math.exp(-tau / 0.04))
            elif kind == 'crash':
                dz += 0.04 * s * spring_punch(tau, 4.0, 0.7)
                k = spring_kick(tau, 6.5, 0.45)
                dx += 5 * s * k * 0.8; dy += 5 * s * k * 0.6
                dr += 0.35 * s * spring_kick(tau, 4.0, 0.5)
                punch = max(punch, 1.0 * s * math.exp(-tau / 0.07))
        return dz * E, dx * E, dy * E, dr * E, punch * E

    # -------------------------------------------------- 配置
    def shot(self, t0, t1, move=None, gain=1.0):
        move = move or Move3()
        if isinstance(move, Move3) and move.ramp == 'beat':
            surges = [(b, 1.0) for b in self.downbeats if t0 - 0.02 <= b < t1 - 0.15]
            surges += [(a, 0.6) for a in self.accent_t if t0 - 0.02 <= a < t1 - 0.15
                       and not any(abs(a - b) < 0.1 for b, _ in surges)]
            if not any(abs(s - t0) < 0.1 for s, _ in surges): surges.append((t0, 0.7))   # 切点即加速
            u, U = beat_warp(t0, t1, surges, tail_k=move.k)
            move.warp = (u, U)
            move.surges = sorted(s for s, _ in surges)
        self.moves.append((t0, t1, move, gain))

    def base3(self, t):
        c = dict(Move3.DEF)
        for a, b, m, g in self.moves:
            if a - 1e-6 <= t < b - 1e-6:
                c.update(m.at((t - a) / (b - a))); break
        if t >= self.moves[-1][1] - 1e-6:
            a, b, m, g = self.moves[-1]; c.update(m.at(1.0))
        mx, my = c['x'], c['y']
        for (tc, v, L, no, ni) in self.whips:
            to, ti = no / FPS, ni / FPS
            if tc - to - 1e-6 <= t < tc - 1e-6:
                e = expo_in((t - (tc - to)) / to) * 0.85 + quart_in((t - (tc - to)) / to) * 0.15
                c['x'] += v[0] * L * e; c['y'] += v[1] * L * e
            elif tc - 1e-6 <= t < tc + ti - 1e-6:
                e = 1 - expo_out((t - tc) / ti)
                c['x'] -= v[0] * L * e; c['y'] -= v[1] * L * e
        c['mx'], c['my'] = mx, my
        return c

    def state(self, t):
        c = self.base3(t)
        dz, dx, dy, dr, p = self.impulses(t)
        c['z'] = c['z'] * (1 + dz); c['x'] += dx; c['y'] += dy; c['rot'] += dr; c['punch'] = p
        c['imp'] = (dz, dx, dy, dr)
        return c

    # -------------------------------------------------- 几何
    @staticmethod
    def _persp(yaw, pitch):
        a, b = math.radians(yaw), math.radians(pitch)
        Ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
        Rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
        R = Rx @ Ry
        P = np.array([[FOC * R[0, 0], FOC * R[0, 1], 0], [FOC * R[1, 0], FOC * R[1, 1], 0], [R[2, 0], R[2, 1], FOC]])
        C = np.array([[1, 0, W / 2], [0, 1, H / 2], [0, 0, 1.0]]); Ci = np.linalg.inv(C)
        Hm = C @ P @ Ci
        return Hm / Hm[2, 2]

    @staticmethod
    def _affine(z, x, y, rot):
        M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, z)
        M[0, 2] -= x * z; M[1, 2] -= y * z
        return np.vstack([M, [0, 0, 1]])

    def homog(self, st, fit=True):
        P = self._persp(st['yaw'], st['pitch'])
        A = self._affine(st['z'], st['x'], st['y'], st['rot'])
        Hm = P @ A
        k = 1.0
        if fit:      # 只按「运镜本身」(不含甩镜/冲击位移) 求补缩放，避免甩镜时突然放大
            A0 = self._affine(st['z'], st['mx'], st['my'], st['rot'])
            k = self._fit(P @ A0)
            if k > 1.0:
                S = np.array([[k, 0, W / 2 * (1 - k)], [0, k, H / 2 * (1 - k)], [0, 0, 1]])
                Hm = S @ Hm
        return Hm, k

    @staticmethod
    def _fit(Hm, margin=2.0):
        """需要多大补缩放，才能让有效区四角 + 边中点的原像落在源图内。"""
        Hi = np.linalg.inv(Hm)
        y0, y1 = ACTIVE_Y
        pts = np.float32([[0, y0], [W, y0], [W, y1], [0, y1], [W / 2, y0], [W / 2, y1], [0, (y0 + y1) / 2], [W, (y0 + y1) / 2]])
        lo, hi = 1.0, 1.6
        def ok(k):
            S = np.array([[k, 0, W / 2 * (1 - k)], [0, k, H / 2 * (1 - k)], [0, 0, 1]])
            q = cv2.perspectiveTransform(pts[None], np.linalg.inv(S @ Hm))[0]
            return (q[:, 0] >= -margin).all() and (q[:, 0] <= W + margin).all() and (q[:, 1] >= -margin).all() and (q[:, 1] <= H + margin).all()
        if ok(1.0): return 1.0
        if not ok(hi): return hi
        for _ in range(12):
            m = (lo + hi) / 2
            if ok(m): hi = m
            else: lo = m
        return hi

    _VG = None

    def vertigo_maps(self, Hm, v):
        """dolly zoom：输出像素 r → 采样 r/s(r)，s(r)=1+v·smooth(r0,r1,r)（中心主体不变，四周拉伸/压缩），再过 H⁻¹。"""
        q = 2
        if VCam3._VG is None:
            ys, xs = np.mgrid[0:H // q, 0:W // q].astype(np.float32)
            VCam3._VG = (xs * q + q / 2, ys * q + q / 2)
        X, Y = VCam3._VG
        cx, cy = W / 2, (ACTIVE_Y[0] + ACTIVE_Y[1]) / 2
        dx, dy = X - cx, Y - cy
        r = np.sqrt(dx * dx + dy * dy)
        rn = r / 1100.0
        s = 1 + v * np.clip((rn - 0.18) / 0.7, 0, 1) ** 1.6
        X2, Y2 = cx + dx / s, cy + dy / s
        Hi = np.linalg.inv(Hm)
        den = Hi[2, 0] * X2 + Hi[2, 1] * Y2 + Hi[2, 2]
        sx = (Hi[0, 0] * X2 + Hi[0, 1] * Y2 + Hi[0, 2]) / den
        sy = (Hi[1, 0] * X2 + Hi[1, 1] * Y2 + Hi[1, 2]) / den
        return cv2.resize(sx.astype(np.float32), (W, H)), cv2.resize(sy.astype(np.float32), (W, H))

    def apply(self, fr, t, shutter=0.5):
        st = self.state(t)
        tp = t - shutter / FPS
        cb = [c for c in self.hardcuts if tp < c <= t + 1e-6]
        if cb:
            s0 = self.base3(cb[-1] + 1e-5)
            dz_, dx_, dy_, dr_, _ = self.impulses(tp)
            s0['z'] *= (1 + dz_); s0['x'] += dx_; s0['y'] += dy_
        else:
            s0 = self.state(tp)
        Hm, k = self.homog(st)
        st['fitk'] = k
        if abs(st['vtg']) > 1e-3:
            mx, my = self.vertigo_maps(Hm, st['vtg'])
            out = cv2.remap(fr, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        else:
            out = cv2.warpPerspective(fr, Hm, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # 速度 → 运动模糊（位移 + 环绕/仰俯折算的画面位移）
        zz = st['z'] * k
        vx = -(st['x'] - s0['x']) * zz - (st['yaw'] - s0['yaw']) * FOC * math.pi / 180 * 0.5
        vy = -(st['y'] - s0['y']) * zz + (st['pitch'] - s0['pitch']) * FOC * math.pi / 180 * 0.5
        if math.hypot(vx, vy) > 3:
            out = motion_blur(out, vx, vy)
        dz = st['z'] / max(1e-6, s0['z']) - 1 + (st['vtg'] - s0['vtg']) * 0.5
        if abs(dz) > 0.006:
            out = radial_blur(out, (W / 2, H / 2), min(0.10, abs(dz) * 2.5))
        ra = st['rot'] - s0['rot']
        st['vel'] = (vx, vy)
        return out, st


# ------------------------------------------------------------------ 前景遮挡物（视差 + 焦点转移）
def _reeds(seed, side):
    r = np.random.default_rng(seed); q = 2
    A = np.zeros((H // q, W // q), np.float32)
    xs = (r.uniform(-80, 520, 26) if side == 'left' else r.uniform(1400, 2000, 26)) if side in ('left', 'right') else r.uniform(-80, 2000, 40)
    for x0 in xs:
        h = r.uniform(260, 620); bend = r.normal(0, 90); wdt = r.uniform(10, 26)
        n = 14; s = np.linspace(0, 1, n)
        cx = x0 + bend * s ** 2; cy = 1120 - h * s
        L = np.stack([cx - wdt * (1 - s), cy], 1); R_ = np.stack([cx + wdt * (1 - s), cy], 1)
        poly = np.vstack([L, R_[::-1]]) / q
        cv2.fillPoly(A, [poly.astype(np.int32)], 1.0, cv2.LINE_AA)
    return A


def _rubble(seed, side):
    r = np.random.default_rng(seed); q = 2
    A = np.zeros((H // q, W // q), np.float32)
    cx0 = 180 if side == 'left' else (1740 if side == 'right' else 960)
    for i in range(16):
        cx = cx0 + r.normal(0, 260); cy = 1080 + r.uniform(-120, 60); s = r.uniform(70, 220)
        ang = r.uniform(0, 180)
        box = cv2.boxPoints(((cx / q, cy / q), (s / q, s * r.uniform(0.4, 0.7) / q), ang))
        cv2.fillConvexPoly(A, box.astype(np.int32), 1.0, cv2.LINE_AA)
    return A


def _post(seed, side):
    q = 2; A = np.zeros((H // q, W // q), np.float32)
    x = 160 if side == 'left' else 1760
    cv2.rectangle(A, ((x - 150) // q, 0), ((x + 150) // q, H // q), 1.0, -1)
    r = np.random.default_rng(seed)
    for y in range(0, H, 92):                                   # 砖缝/木纹刻痕：虚焦后仍可读出材质
        cv2.line(A, ((x - 150) // q, y // q), ((x + 150) // q, (y + r.integers(-6, 6)) // q), 0.55, 2)
    return A


class FGOcc:
    """前景遮挡物：kind ∈ reeds/rubble/post，side ∈ left/right/both/bottom；depth：位移倍数（>1 比主体快）。
    rim：边缘受光颜色；draw 时 blur 由焦点决定（focus=1 场景实 → 遮挡物虚）。"""
    _cache = {}

    def __init__(self, kind, side='left', depth=2.4, seed=0, rim=(0.8, 0.85, 1.0), tone=0.012, off=(0, 0)):
        key = (kind, side, seed)
        if key not in FGOcc._cache:
            A = {'reeds': _reeds, 'rubble': _rubble, 'post': _post}[kind](seed, side)
            FGOcc._cache[key] = A
        self.A = FGOcc._cache[key]; self.kind = kind; self.side = side
        self.d = depth; self.rim = np.asarray(rim, np.float32); self.tone = tone; self.off = off

    def draw(self, fr, st, t=0.0, sharp_blur=1.2, soft_blur=16.0):
        q = 2
        z = st['z'] * st.get('fitk', 1.0)
        sc = z ** self.d
        sx = -(st['x'] * z) * self.d - st['yaw'] * 12 * self.d + self.off[0]
        sy = -(st['y'] * z) * self.d - st['pitch'] * 8 * self.d + self.off[1]
        if self.kind == 'reeds': sx += 14 * math.sin(t * 1.3)
        M = cv2.getRotationMatrix2D((W / 2 / q, H / 2 / q), st['rot'] * 1.3, sc)
        M[0, 2] += sx / q; M[1, 2] += sy / q
        A = cv2.warpAffine(self.A, M, (W // q, H // q), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        f = st.get('focus', 1.0)
        b = sharp_blur + (soft_blur - sharp_blur) * f
        Ab = cv2.GaussianBlur(A, (0, 0), b / q)
        # 边缘受光：alpha 的上沿梯度
        e = np.clip(Ab - cv2.GaussianBlur(Ab, (0, 0), 3 + b / q), 0, 1)
        Ab = cv2.resize(Ab, (W, H)); e = cv2.resize(e, (W, H))
        out = fr * (1 - Ab[..., None]) + self.tone * Ab[..., None] + e[..., None] * self.rim * (0.9 - 0.5 * f)
        return out


def defocus(fr, sigma):
    """场景虚焦（降采样高斯，便宜）"""
    if sigma < 0.4: return fr
    q = 4 if sigma > 6 else 2
    sm = cv2.resize(fr, (W // q, H // q), interpolation=cv2.INTER_AREA)
    sm = cv2.GaussianBlur(sm, (0, 0), sigma / q)
    b = cv2.resize(sm, (W, H), interpolation=cv2.INTER_LINEAR)
    # 高光虚焦成光斑（轻微 bloom）
    return b + np.clip(b - 0.85, 0, None) * 0.3
