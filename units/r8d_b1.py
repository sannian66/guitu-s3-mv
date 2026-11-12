"""units/r8d_b1.py — 第八轮风格 D · B1 单元「预副歌一」（帧 1321–1779，P01–P15）。
只在 STYLE_D=1 时由 units/sec_b_pre1.py 末尾 apply(本模块所属段落) 加载；STYLE_D=0 时不 import，现版逐像素不变。

规则（crew/round8/SPREAD_r8.md + USER_NOTES_r8.md）：
- 每镜重新生图分层（assets/gen/R8_D/B1/，nananobanana RH_image2，提示词 jobs/r8_D_B1.json）；切点 / 镜长 / 转场 / 字幕不动。
- 画面字只留 P05 匾「规矩」——画进生图（B1_gate），代码只做「未唱暗槽 → 字头白光灌满」；门上「谁的规矩」去掉。
  其余画面字全部去掉：P01「谁配」→ 朱笔勾决（圈 + 勾）；生死簿人名 → 墨线小像；P04「框」去掉；P08 云隙「天」→ 闪电劈开漩涡天；
  P09「命」印 → 血红锁链（命）被刀柄撞碎；P10/P11 铅字「理所应当」→ 棋盘上被刀尖挑飞的黑白棋子。
- 精灵一律 grade=NEU, rim=NORIM, wrap=0, shade=None；人物有风吹发丝/衣带（wind_amp）+ 呼吸，动作镜两姿势（P09、P13）。
- 视差以镜头中点为零；主体按锚点落位；色板只用黑白灰 + 血红（火星白 + 血红、刀光白、刀痕干笔飞白 + 溅墨）。
"""
import os, math, copy
import numpy as np, cv2
import b_kit as BK
from b_kit import Shot, V, CT, kick_env, shake, W, H, RED
import c1kit as K
from c1kit import clamp01, eio, eout, ein, sstep, pulse, cam, over
import sprite as SP
import typo as T
import fx2

ROOT = os.environ.get('MV_ROOT', '/workspace/work/mv')
GD = ROOT + '/assets/gen/R8_D/B1/'
NEU = dict(expo=1.0, sat=1.0, tint=(1.0, 1.0, 1.0), lift=0.0, gamma=1.0)
NORIM = dict(col=(1.0, 1.0, 1.0), amt=0.0, dir=(0.0, -1.0))
SPK = dict(grade=NEU, rim=NORIM, wrap=0.0, shade=None)
WHITE3 = np.array([0.95, 0.95, 0.95], np.float32)
INK = (0.015, 0.015, 0.015)
BLOOD = np.array([0.62, 0.035, 0.03], np.float32)


# ------------------------------------------------------------------------------- 素材
_P = {}


def plate(name, blur=0.0, gain=1.0):
    """背景板（RGB float，原 2048 宽）"""
    k = (name, blur, gain)
    if k not in _P:
        im = cv2.cvtColor(cv2.imread(GD + name + '.png'), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        if blur: im = cv2.GaussianBlur(im, (0, 0), blur)
        _P[k] = im * gain
    return _P[k]


def rgba(name):
    k = ('rgba', name)
    if k not in _P:
        im = cv2.imread(GD + name + '.png', cv2.IMREAD_UNCHANGED)
        im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255
        A = np.ascontiguousarray(im[..., 3]); A = (A * edge_mask(A, seed=len(name))).astype(np.float32)   # 返工：不露裁切边
        _P[k] = (np.ascontiguousarray(im[..., :3]), A)
    return _P[k]


def edge_mask(A, seed=0, width=0.05):
    """返工（用户硬规则：任何图层不露裁切边）：alpha 贴到画布哪条边，就在那条边做波浪形羽化——
    羽化宽度沿边随噪声变化（0.4–1.6 倍），渐隐线是不规则的墨边，不形成直线或矩形边"""
    h, w = A.shape
    m = np.ones((h, w), np.float32)
    r = np.random.default_rng(seed)
    for side in ('top', 'bot', 'left', 'right'):
        e = {'top': A[0], 'bot': A[-1], 'left': A[:, 0], 'right': A[:, -1]}[side]
        if (e > 0.05).sum() < 0.004 * len(e): continue                          # 刀尖等窄接触不算裁切边（羽化会把刀尖吃掉）
        n = len(e)
        wav = cv2.resize(r.random((1, 12)).astype(np.float32), (n, 1), interpolation=cv2.INTER_CUBIC)[0]
        wav = wav * 0.7 + cv2.resize(r.random((1, 48)).astype(np.float32), (n, 1), interpolation=cv2.INTER_CUBIC)[0] * 0.3
        wd = (0.4 + 1.2 * np.clip(wav, 0, 1)) * width * (h if side in ('top', 'bot') else w)
        if side in ('top', 'bot'):
            d = np.arange(h, dtype=np.float32)[:, None]
            if side == 'bot': d = d[::-1]
            m *= np.clip(d / wd[None, :], 0, 1) ** 1.5
        else:
            d = np.arange(w, dtype=np.float32)[None, :]
            if side == 'right': d = d[:, ::-1]
            m *= np.clip(d / wd[:, None], 0, 1) ** 1.5
    return m


def lay(name, feather=None):
    """精灵层（返工：贴画布边自动波浪羽化，见 edge_mask）；feather=dict(left=, right=, top=) 额外渐隐"""
    k0 = ('lay', name)
    if k0 not in _P:
        sp0 = SP.layer(GD + name + '.png')
        m = edge_mask(sp0.A, seed=len(name))
        if m.min() < 1:
            sp = copy.copy(sp0)
            sp.A = (sp0.A * m).astype(np.float32); sp.ring = (sp0.ring * m).astype(np.float32); sp._box = {}
        else:
            sp = sp0
        _P[k0] = sp
    sp = _P[k0]
    if not feather: return sp
    k = ('feather', name, tuple(sorted((a, tuple(b) if isinstance(b, (list, tuple)) else b) for a, b in feather.items())))
    if k in _P: return _P[k]
    s = copy.copy(sp)
    h, w = s.A.shape
    xx = np.linspace(0, 1, w, dtype=np.float32)[None]; yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    m = np.ones((h, w), np.float32)
    if feather.get('left'):                                                     # 波浪形羽化（不形成直线）
        wv = cv2.resize(np.random.default_rng(len(name)).random((12, 1)).astype(np.float32), (1, h), interpolation=cv2.INTER_CUBIC)
        m = m * sstep(0, feather['left'] * (0.5 + 1.0 * np.clip(wv, 0, 1)), xx)
    if feather.get('right'): m = m * sstep(1, 1 - feather['right'], xx)
    if feather.get('top'): m = m * sstep(0, feather['top'], yy)
    s.A = (s.A * m).astype(np.float32); s.ring = (s.ring * m).astype(np.float32)
    s.wind_w = s.wind_w.copy(); s._box = {}
    _P[k] = s
    return s


def view(img, z, c, dx=0.0, dy=0.0, rot=0.0, fit=1.0):
    """背景板取景：源图点 c（归一化）→ 屏幕中心 + (dx,dy)，缩放 = 适配宽 × fit × z，绕中心旋转 rot（度）"""
    h, w = img.shape[:2]
    s = W / w * fit * z
    M = cv2.getRotationMatrix2D((c[0] * w, c[1] * h), rot, s)
    M[0, 2] += W / 2 + dx - c[0] * w; M[1, 2] += H / 2 + dy - c[1] * h
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def spt(sp, src, dst, width_px, n, rot=0.0):
    """精灵内归一化点 n → 屏幕（与 SpriteLayer.draw 同一映射，breathe=0）"""
    s = width_px / sp.w
    M = cv2.getRotationMatrix2D((src[0] * sp.w, src[1] * sp.h), rot, s)
    M[0, 2] += dst[0] - src[0] * sp.w; M[1, 2] += dst[1] - src[1] * sp.h
    return M @ np.array([n[0] * sp.w, n[1] * sp.h, 1.0])


def put_at(fr, sp, t, src, dst, width_px, rot=0.0, wind=0.0, breathe=0.0, **kw):
    a = dict(SPK); a.update(kw)
    return sp.draw(fr, t, src, dst, width_px / sp.w, rot=rot, breathe=breathe, wind_amp=wind, **a)


def paste(fr, F, A, M, alpha=1.0):
    Fw = cv2.warpAffine(F, M, (W, H), flags=cv2.INTER_LINEAR)
    Aw = cv2.warpAffine(A, M, (W, H), flags=cv2.INTER_LINEAR) * alpha
    return fr * (1 - Aw[..., None]) + Fw * Aw[..., None], Aw


def M_at(src_px, dst, s, rot=0.0, sy=1.0):
    """源像素点 src_px → 屏幕 dst，缩放 s，旋转 rot（度），竖向再压 sy（翻滚的透视）"""
    M = cv2.getRotationMatrix2D((float(src_px[0]), float(src_px[1])), rot, s)
    M[1, :] *= sy
    p = M @ np.array([src_px[0], src_px[1], 1.0])
    M[0, 2] += dst[0] - p[0]; M[1, 2] += dst[1] - p[1]
    return M.astype(np.float32)


# ------------------------------------------------------------------------------- 风格 D 笔触 / 粒子
_NZ = {}


def _streak_noise(seed):
    """干笔飞白纹理（各向异性：沿笔向拉长）"""
    if seed not in _NZ:
        r = np.random.default_rng(seed)
        n = r.random((H // 2, W // 16)).astype(np.float32)
        n = cv2.resize(n, (W // 2, H // 2), interpolation=cv2.INTER_LINEAR)
        n = cv2.GaussianBlur(n, (0, 0), sigmaX=6, sigmaY=0.8)
        n = (n - n.min()) / (n.max() - n.min() + 1e-6)
        _NZ[seed] = n
    return _NZ[seed]


def dry_stroke(pts, prog, w0=30.0, w1=14.0, seed=0, dry=0.55):
    """干笔一笔（0..1 遮罩，全分辨率）：沿折线 pts 画到 prog，起笔顿重、收笔渐细，飞白沿笔向；返回 (mask, 笔头位置)"""
    pts = np.asarray(pts, np.float32)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); L = seg.sum()
    if prog <= 0 or L <= 0: return np.zeros((H, W), np.float32), tuple(pts[0])
    cum = np.concatenate([[0], np.cumsum(seg)]) / L
    m = np.zeros((H // 2, W // 2), np.float32)
    head = pts[0]
    for i in range(len(pts) - 1):
        if cum[i] >= prog: break
        q = min(1.0, (prog - cum[i]) / max(1e-6, cum[i + 1] - cum[i]))
        a = pts[i]; b = a + (pts[i + 1] - a) * q; head = b
        f = cum[i] + (cum[i + 1] - cum[i]) * q * 0.5
        wd = w0 + (w1 - w0) * f
        cv2.line(m, tuple((a * 2).astype(int)), tuple((b * 2).astype(int)), 1.0, max(1, int(wd)), cv2.LINE_AA, 2)
    cv2.circle(m, tuple((pts[0] * 2).astype(int)), int(w0 * 0.62), 1.0, -1, cv2.LINE_AA, 2)   # 起笔顿点
    nz = _streak_noise(seed)
    d = pts[-1] - pts[0]; ang = math.degrees(math.atan2(d[1], d[0]))
    R = cv2.getRotationMatrix2D((W / 4, H / 4), -ang, 1.0)
    nz = cv2.warpAffine(nz, R, (W // 2, H // 2), borderMode=cv2.BORDER_REFLECT)
    edge = cv2.GaussianBlur(m, (0, 0), 3.0)
    fb = np.clip((nz - dry * (0.40 + 0.80 * (1 - edge))) * 5.0, 0, 1)        # 笔芯也有飞白丝，边缘更干更碎
    m = cv2.resize(m * (0.12 + 0.88 * fb), (W, H))
    return np.clip(m * 1.15, 0, 1), (float(head[0]), float(head[1]))


def ink_stroke(fr, m, color=BLOOD, edge=0.8):
    """笔触上色：血红芯 + 墨线外沿（漫画勾边）"""
    out = cv2.dilate(m, np.ones((5, 5), np.uint8)) - m
    fr = over(fr, np.clip(out * edge, 0, 1), INK)
    return over(fr, m, np.asarray(color, np.float32))


def splat(fr, t, t0, seed, c, n=26, r=(120, 520), size=(3, 14), dur=0.12, color=BLOOD, sy=1.0, dirc=None, spread=6.3):
    """溅墨点（血红芯 + 墨边），t0 起 dur 内飞到位后定住"""
    if t < t0: return fr
    rr = np.random.default_rng(seed)
    q = eout((t - t0) / dur, 2)
    m = np.zeros((H // 2, W // 2), np.float32)
    base = 0.0 if dirc is None else math.atan2(dirc[1], dirc[0])
    for i in range(n):
        a = base + rr.uniform(-spread / 2, spread / 2); d = rr.uniform(*r) * q; s = rr.uniform(*size) * (0.6 + 0.4 * q)
        px, py = c[0] + math.cos(a) * d, c[1] + math.sin(a) * d * sy
        cv2.ellipse(m, (int(px / 2 * 8), int(py / 2 * 8)), (max(1, int(s / 2 * 8 * (1 + 0.6 * q))), max(1, int(s / 2 * 8))),
                    math.degrees(a), 0, 360, 1.0, -1, cv2.LINE_AA, 3)
    m = cv2.resize(m, (W, H))
    return ink_stroke(fr, m, color, edge=0.9)


def sparks2(fr, t, seed, origin, **kw):
    """火星：白 + 血红两层"""
    n = kw.pop('n', 60)
    fr = K.sparks(fr, t, seed, origin, n=n, color=(1.0, 0.97, 0.95), **kw)
    return K.sparks(fr, t, seed + 7, origin, n=max(6, n // 2), color=(0.85, 0.05, 0.04), **kw)


def ink_sparks(fr, t, seed, origin, n=40, life=0.5, speed=(300, 900), dirc=(0, -1), spread=1.0, grav=900, t0=None, burst=False,
               area=(0, 0), amt=1.0, red=0.35, length=0.022):
    """风格 D 火星（返工）：硬边短划（白 + 血红，带墨边），不发光、不糊团"""
    r = np.random.default_rng(seed)
    ph = r.random(n); sp = r.uniform(*speed, n)
    ang = math.atan2(dirc[1], dirc[0]) + r.normal(0, spread, n)
    ox = origin[0] + r.uniform(-1, 1, n) * area[0]; oy = origin[1] + r.uniform(-1, 1, n) * area[1]
    lf = life * r.uniform(0.5, 1.2, n); isred = r.random(n) < red
    if burst:
        age = np.full(n, t - (t0 or 0.0)); alive = (age >= 0) & (age < lf)
    else:
        age = ((t / lf + ph) % 1.0) * lf; alive = np.ones(n, bool)
    if not alive.any(): return fr
    vx = np.cos(ang) * sp; vy = np.sin(ang) * sp
    px = ox + vx * age; py = oy + vy * age + 0.5 * grav * age * age
    qx = px - vx * length; qy = py - (vy + grav * age) * length
    Lw = np.zeros((H // 2, W // 2), np.float32); Lr = np.zeros_like(Lw)
    for i in np.nonzero(alive)[0]:
        if not (-50 < px[i] < W + 50 and -50 < py[i] < H + 50): continue
        k = 1 - age[i] / lf[i]
        cv2.line(Lr if isred[i] else Lw, (int(px[i] * 4), int(py[i] * 4)), (int(qx[i] * 4), int(qy[i] * 4)),
                 float(min(1.0, 0.4 + k)), 2 if k > 0.5 else 1, cv2.LINE_AA, 3)
    Lw = cv2.resize(Lw, (W, H)); Lr = cv2.resize(Lr, (W, H))
    Lm = np.maximum(Lw, Lr)
    edge = np.clip(cv2.dilate(Lm, np.ones((3, 3), np.uint8)) - Lm, 0, 1)
    fr = over(fr, edge * 0.7 * amt, INK)
    fr = over(fr, np.clip(Lw * amt, 0, 1), WHITE3)
    return over(fr, np.clip(Lr * amt, 0, 1), BLOOD * 1.3)


def dry_ring(fr, c, r, prog, seed, w=10.0, sy=1.0, color=WHITE3):
    """干笔飞白圈（冲击环，返工）：沿椭圆一笔扫出，墨边"""
    ang = np.linspace(-0.4, -0.4 + 2 * math.pi * 0.92, 36)
    pts = np.stack([c[0] + r * np.cos(ang), c[1] + r * np.sin(ang) * sy], -1)
    m, _ = dry_stroke(pts, prog, w * 1.3, w * 0.5, seed=seed, dry=0.75)
    return ink_stroke(fr, m, np.asarray(color, np.float32), edge=0.6)


_TONE = {}


def screentone(period=7, ang=45):
    k = (period, ang)
    if k not in _TONE:
        x, y = K.grid(); a = math.radians(ang)
        u = (x * math.cos(a) + y * math.sin(a)) * 2 * math.pi / period
        v = (-x * math.sin(a) + y * math.cos(a)) * 2 * math.pi / period
        _TONE[k] = ((np.cos(u) + np.cos(v)) * 0.25 + 0.5).astype(np.float32)
    return _TONE[k]


def tone_fade(fr, amt=0.55, level=0.30, period=7):
    """去景深虚化（返工）：往白纸淡化 + 叠网点（印刷感），替代高斯虚焦"""
    lum = fr.mean(-1, keepdims=True)
    paper = 1 - (1 - lum) * (1 - amt)
    dots = (screentone(period) < level * (1 - lum[..., 0]) * 1.4).astype(np.float32)
    dots = cv2.GaussianBlur(dots, (0, 0), 0.6)[..., None]
    out = fr * (1 - amt) + paper * amt
    return out * (1 - 0.55 * dots)


def lift(fr, black=0.10, gamma=0.80):
    """提亮（返工 #4）：抬黑位 + gamma；红色相按比例保留（在 style_d 兜底前做）"""
    return black + (1 - black) * np.clip(fr, 0, None) ** gamma


def flutter(fr, t, sp, src, dst, wpx, region, amp=10.0, freq=1.3, seed=0, rot=0.0):
    """二级运动（返工二 §12-3）：发丝 / 红带 / 衣摆 / 刀穗拆层，用**低振幅、低频、随时间慢变的噪声位移**驱动（不是规则正弦，不果冻）；
    位移只在轮廓附近一条带宽里生效（离轮廓越远越不动），且离锚边越远越大（发梢 / 带尾飘，根部不动）。振幅上限按屏幕像素算，默认减半。"""
    k = ('flut2', id(sp), region)
    if k not in _P:
        h, w = sp.A.shape
        x0, y0, x1, y1 = region
        xx = np.linspace(0, 1, w, dtype=np.float32)[None]; yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
        m = sstep(x0 - 0.03, x0, xx) * sstep(x1 + 0.03, x1, xx) * sstep(y0 - 0.03, y0, yy) * sstep(y1 + 0.03, y1, yy)
        gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
        fall = np.clip((xx - x1) / (x0 - x1 - 1e-6), 0, 1) if amp >= 0 else np.clip((xx - x0) / (x1 - x0 + 1e-6), 0, 1)
        inside = np.ascontiguousarray(sp.A > 0.5).astype(np.uint8)
        dist = cv2.distanceTransform(inside, cv2.DIST_L2, 5)
        band = np.clip(1 - dist / (0.06 * w), 0, 1).astype(np.float32)              # 只有轮廓 6% 宽度内的像素（发梢、带边）会动
        r = np.random.default_rng(seed + 900)
        nf = [cv2.resize(r.random((6, 10)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC) - 0.5 for _ in range(8)]   # 低频噪声场
        _P[k] = (np.ascontiguousarray((sp.A * m).astype(np.float32)), gx, gy, (fall * band).astype(np.float32), nf)
    Am0, gx, gy, wgt, nf = _P[k]
    h, w = sp.A.shape
    p = (t * freq * 0.6) % len(nf); i = int(p); j = (i + 1) % len(nf); q = p - i; q = q * q * (3 - 2 * q)
    j2 = (i + 3) % len(nf); i2 = (i + 4) % len(nf)
    nx = nf[i] * (1 - q) + nf[j] * q; ny = nf[i2] * (1 - q) + nf[j2] * q
    sc = w / max(1.0, wpx)
    A_ = min(abs(amp), 10.0) * 0.6                                             # 屏幕像素振幅上限 6px
    dx = nx * 2.0 * A_ * wgt * sc * np.sign(amp or 1); dy = ny * 1.2 * A_ * wgt * sc
    mx = (gx - dx).astype(np.float32); my = (gy - dy).astype(np.float32)
    Fm = cv2.remap(sp.F, mx, my, cv2.INTER_LINEAR); Am = cv2.remap(Am0, mx, my, cv2.INTER_LINEAR)
    s = wpx / w
    M = cv2.getRotationMatrix2D((src[0] * w, src[1] * h), rot, s)
    M[0, 2] += dst[0] - src[0] * w; M[1, 2] += dst[1] - src[1] * h
    return paste(fr, Fm, Am, M.astype(np.float32))[0]


def rain(fr, t, seed, amt=0.35, n=450, angle=-8, speed=2300):
    return K.rain(fr, t, seed, n=n, amt=amt, speed=speed, angle=angle, near=0.35, length=(40, 120))


def rain_fg(fr, t, tm, off=(0.0, 0.0), alpha=0.5, speed=900.0, angle=-14.0, blur=0.0):
    """前景生图雨丝层（贴镜头，下落以镜头中点为零）"""
    F, A = rgba('B1_rainfg_cut')
    k = ('rfg', blur)
    if k not in _P:
        fw = int(W * 1.15); fh = int(fw * A.shape[0] / A.shape[1])
        Fr = cv2.resize(F, (fw, fh), interpolation=cv2.INTER_AREA); Ar = cv2.resize(A, (fw, fh), interpolation=cv2.INTER_AREA)
        if blur: Fr = cv2.GaussianBlur(Fr, (0, 0), blur); Ar = cv2.GaussianBlur(Ar, (0, 0), blur)
        _P[k] = (Fr, Ar)
    Fr, Ar = _P[k]
    fh, fw = Ar.shape
    a = math.radians(angle)
    sx = (fw - W) / 2 - off[0] - (t - tm) * speed * math.sin(a)
    sy = (fh - H) / 2 - off[1] - (t - tm) * speed * math.cos(a)
    M = np.float32([[1, 0, -sx], [0, 1, -sy]])
    Fw = cv2.warpAffine(Fr, M, (W, H), borderMode=cv2.BORDER_WRAP)
    Aw = cv2.warpAffine(Ar, M, (W, H), borderMode=cv2.BORDER_WRAP)[..., None] * alpha
    return fr * (1 - Aw) + Fw * Aw


def lightning_bolt(seed, p0, p1, branches=6):
    return fx2.Lightning(seed, p0=p0, p1=p1, branches=branches)


def tm(s): return 0.5 * (s.t0 + s.t1)


# ------------------------------------------------------------------------------- §12-2 流动天空 / 云（返工二：不许整张图旋转或平移）
_FLOW = {}


def _flow_noise(seed, n=6, base=5):
    """n 张循环噪声场（H/8 × W/8），供时间上交叉淡化的 UV 位移；首尾相接成环（6 帧左右一个淡化周期之外的慢变）"""
    k = ('fn', seed, n, base)
    if k not in _FLOW:
        _FLOW[k] = [cv2.resize(K.fbm(H // 8, W // 8, seed * 31 + i, base=base, octaves=4), (W, H)).astype(np.float32) - 0.5 for i in range(n)]
    return _FLOW[k]


def _ring(t, period, n):
    """时间 → (i, j, w)：在 n 张噪声场之间按 period 周期循环交叉淡化"""
    p = (t / period) % n
    i = int(p); j = (i + 1) % n; w = p - i
    return i, j, w * w * (3 - 2 * w)


def flow_layers(img, t, z, c, flow='swirl', speeds=(0.6, 1.0, 1.6), amp=(10.0, 18.0, 28.0), alphas=(1.0, 0.55, 0.40),
                swirl_c=(0.5, 0.42), seed=0, dx=0.0, dy=0.0, crossfade=True):
    """把一张生图天空拆成 3 层同源云层：
       - 每层沿流向（flow='swirl'：绕 swirl_c 的切向，越靠外越慢；flow=(vx,vy)：直线方向）按不同速度做 UV 平移，
       - 叠加随时间滚动的噪声 UV 位移（湍流，低频），
       - 前后两层取同一位置的不同相位并交叉淡化（避免「一张图在转」），
       - 远层（第 0 层）最慢、近层最快 → 视差。返回合成后的 RGB。
    不做整张旋转：漩涡的「转」完全由切向流场驱动，中心几乎不动、外圈拖曳，云团自身在形变。"""
    h, w = img.shape[:2]
    s = W / w * z
    x, y = K.grid()
    # 屏幕 → 源图（基础取景，无旋转）
    sx0 = (x - W / 2 - dx) / s + c[0] * w
    sy0 = (y - H / 2 - dy) / s + c[1] * h
    cxp, cyp = swirl_c[0] * w, swirl_c[1] * h
    rx, ry = sx0 - cxp, sy0 - cyp
    r = np.sqrt(rx * rx + ry * ry) + 1e-3
    nz = _flow_noise(seed)
    out = np.zeros((H, W, 3), np.float32); wsum = 0.0
    for li, (sp, a, al) in enumerate(zip(speeds, amp, alphas)):
        i, j, wj = _ring(t * (0.8 + 0.25 * li), 0.22, len(nz))                 # 噪声场 0.22s 一换（约 6–7 帧）
        n1 = nz[i] * (1 - wj) + nz[j] * wj
        n2 = nz[(i + 2) % len(nz)] * (1 - wj) + nz[(j + 2) % len(nz)] * wj
        if flow == 'swirl':
            ang = t * sp * 0.09 * (0.35 + 0.65 * np.exp(-r / (0.55 * w)))         # 内快外慢的切向流（角速度随半径衰减）
            ca, sa = np.cos(ang), np.sin(ang)
            ux = cxp + rx * ca - ry * sa; uy = cyp + rx * sa + ry * ca
        else:
            ux = sx0 - flow[0] * sp * t * 40.0; uy = sy0 - flow[1] * sp * t * 40.0
        ux = ux + n1 * a * 2.0; uy = uy + n2 * a * 2.0                          # 湍流 UV 位移（随时间滚动）
        L = cv2.remap(img, ux.astype(np.float32), uy.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        if crossfade and li > 0:                                                # 前后层交叉淡化：同层再取一个错相位的版本
            i2, j2, w2 = _ring(t * (0.8 + 0.25 * li) + 0.11, 0.22, len(nz))
            m1 = nz[i2] * (1 - w2) + nz[j2] * w2
            L2 = cv2.remap(img, (ux + m1 * a * 1.5).astype(np.float32), (uy - m1 * a * 1.5).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            k = 0.5 + 0.5 * math.sin(2 * math.pi * t / 0.4 + li)
            L = L * (1 - 0.5 * k) + L2 * (0.5 * k)
        out += L * al; wsum += al
    return out / wsum



# =================================================================================== P01
# ECU 俯拍生死簿（墨线小像代替人名，无字）：太上皇（定妆照：枯瘦、黑纱袖）执朱笔，「谁」圈住一个人、「配」一勾——朱笔勾决
class P01D(Shot):
    C = (0.640, 0.505)                  # 取景中心（右页）
    Z = 1.80
    TGT = (760.0, 650.0)                # 被圈的小像（屏幕，镜头中点时）
    def __init__(self):
        self.bg = plate('B1_ledger')
        self.hand = lay('B1_hand_r2_cut')
        cx, cy = self.TGT
        ang = np.linspace(-2.2, 2.2 * math.pi - 2.0, 40)                     # 朱圈：起笔左上、顺时针、收笔压过起笔
        r = 104 + 9 * np.sin(ang * 1.5)
        self.circ = np.stack([cx + r * np.cos(ang) * 1.05, cy + r * np.sin(ang) * 0.95], -1)
        self.tick = np.array([[cx - 140, cy - 30], [cx - 40, cy + 70], [cx + 240, cy - 200], [cx + 320, cy - 262]], np.float32)   # 勾
        self.HS = (0.345, 0.975)                                            # 笔尖在精灵内
        self.ROT = -38.0                                                    # 顺时针转 38°：袖子从画右入画，手背整只在画内

    def render(self, t):
        u = self.u(t)
        p0 = clamp01((t - V(44.0)) / 0.40); p1 = clamp01((t - V(44.78) + 0.12) / 0.26)
        x, y = K.grid()
        fr = view(self.bg, self.Z, self.C)
        fr = fr * (0.62 + 0.45 * np.exp(-(((x - 1250) / 950) ** 2 + ((y - 300) / 650) ** 2)))[..., None]   # 烛光右上、左下压暗
        m0, h0 = dry_stroke(self.circ, p0, 34, 18, seed=11)
        fr = ink_stroke(fr, m0)
        if p1 > 0:
            m1, h1 = dry_stroke(self.tick, eout(p1, 1.6), 38, 10, seed=12, dry=0.7)
            fr = ink_stroke(fr, m1)
            fr = splat(fr, t, V(44.78) + 0.1, 101, (self.tick[2][0], self.tick[2][1]), n=14, r=(30, 160), size=(2, 8), dirc=(1, -0.8), spread=1.4)
            head = h1
        else:
            head = h0
        if p0 <= 0: head = (self.circ[0][0] + 120 * (1 - eout(clamp01((t - self.t0) / 0.2))), self.circ[0][1] - 60)
        tip = (head[0] + 3 * math.sin(t * 23), head[1] + 2 * math.cos(t * 19))
        # 手：笔尖锁在笔头；投影 = 以笔尖为不动点的接触投影（离纸越高投得越远越虚）
        HW = 1080
        top = spt(self.hand, self.HS, tip, HW, (0.470, 0.020), self.ROT)
        d_ = top - np.array(tip); u_ = (d_ / np.linalg.norm(d_)).astype(np.float32)   # 笔杆「向上」方向（屏幕）
        _, Ah = put_at(np.zeros_like(fr), self.hand, t, self.HS, tip, HW, rot=self.ROT)
        L = np.array([-0.30, 0.40], np.float32); A2 = np.eye(2, dtype=np.float32) + np.outer(L, u_)
        tp_ = np.array(tip, np.float32); M = np.hstack([A2, (tp_ - A2 @ tp_)[:, None]]).astype(np.float32)
        sh = cv2.warpAffine(Ah.astype(np.float32), M, (W, H))
        d = np.sqrt((x - tip[0]) ** 2 + (y - tip[1]) ** 2); ws = np.exp(-d / 260.0)
        shm = cv2.GaussianBlur(sh, (0, 0), 2.0) * ws + cv2.GaussianBlur(sh, (0, 0), 16.0) * (1 - ws)
        fr = fr * (1 - 0.55 * shm[..., None])
        wet = np.exp(-(((x - tip[0]) / 16) ** 2 + ((y - tip[1]) / 11) ** 2))[..., None]
        fr = fr * (1 - 0.7 * wet) + wet * 0.7 * BLOOD
        fr, _ = put_at(fr, self.hand, t, self.HS, tip, HW, rot=self.ROT, wind=1.5, breathe=0.002)
        fr = K.dust(fr, t, 1011, n=30, amt=0.25, size=(2, 5), blur=3, color=(0.9, 0.9, 0.9))
        z = 1.0 + 0.08 * eio(u)
        fr = cam(fr, z, 0, 0, 2.0 * eio(u) - 1.0)
        if t < self.t0 + 0.30:                                               # 入口：墨从黑中洇开成纸（接 A 组）
            m = K.ink_blot(0.86 + 0.14 * eout((t - self.t0) / 0.28, 2), seed=201, center=(930, 520), reverse=True)
            fr = over(fr, m, np.array([0.015, 0.015, 0.015], np.float32))
        return fr, 0


# =================================================================================== P02
# 微距：朱墨一滴坠到圈中人脸上，皇冠状炸开、血晕吞掉小像（45.33 底鼓）
class P02D(Shot):
    T_DROP = V(45.38)
    C0 = (960.0, 470.0)                 # 落点（屏幕）
    def __init__(self):
        self.bg = plate('B1_macro2')                                       # 群演：中年百姓（头巾、胡茬），不是鬼屠
        self.sp = lay('B1_splash_i2i_cut')                                 # 返工二 #8：img2img 重绘为哑光墨红，去湿亮高光
        self.nz = cv2.resize(K.fbm(H // 4, W // 4, 22, base=6, octaves=5), (W, H))

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        cx, cy = self.C0
        fr = view(self.bg, 1.06, (0.5, 0.44))
        fr = fr * (0.70 + 0.38 * np.exp(-(((x - 960) / 800) ** 2 + ((y - 420) / 520) ** 2)))[..., None]
        if t >= self.T_DROP:
            q = eout((t - self.T_DROP) / 0.5, 2)
            d = np.sqrt((x - cx) ** 2 + ((y - cy) * 0.85) ** 2) / 360
            m = np.clip((q - d - (self.nz - 0.5) * 0.5) * 6, 0, 1)
            rim = np.clip(1 - np.abs(q - d - (self.nz - 0.5) * 0.5) * 14, 0, 1) * (q < 0.99)
            fr = fr * (1 - m[..., None] * 0.55) + m[..., None] * 0.55 * BLOOD * (0.6 + 0.6 * fr.mean(-1, keepdims=True))
            fr = over(fr, rim * 0.6, INK)
            k = clamp01((t - self.T_DROP) / 0.11)
            fr, _ = put_at(fr, self.sp, t, (0.52, 0.86), (cx, cy + 40), 300 + 700 * eout(k, 3), alpha=1.0 - 0.35 * clamp01((t - self.T_DROP - 0.25) / 0.3))
            fr = splat(fr, t, self.T_DROP, 23, (cx, cy), n=30, r=(160, 620), size=(4, 16), dur=0.14, sy=0.85)
            fr = fr + (np.exp(-(t - self.T_DROP) / 0.06) * 0.8) * np.exp(-(((x - cx) / 260) ** 2 + ((y - cy) / 200) ** 2))[..., None]
        else:                                                                 # 坠落的朱墨滴（墨线描边 + 白高光，与 S028D 同画法）
            q = clamp01((t - (self.T_DROP - 0.36)) / 0.36)
            yy = -40 + (cy + 40) * q ** 1.7
            L = np.zeros((H, W), np.float32)
            cv2.ellipse(L, (int(cx * 4), int(yy * 4)), (18 * 4, 26 * 4), 0, 0, 360, 1.0, -1, cv2.LINE_AA, 2)
            tri = np.array([[cx - 16, yy - 10], [cx + 16, yy - 10], [cx, yy - 70]]) * 4
            cv2.fillConvexPoly(L, tri.astype(np.int32), 1.0, cv2.LINE_AA, 2)
            L = cv2.GaussianBlur(L, (0, 0), 1.0)
            fr = ink_stroke(fr, L, BLOOD * 1.3)
            hl = np.zeros((H, W), np.float32); cv2.circle(hl, (int(cx - 7), int(yy - 5)), 5, 1.0, -1, cv2.LINE_AA)
            fr += cv2.GaussianBlur(hl, (0, 0), 1.5)[..., None] * 0.9
        k = pulse(t, self.T_DROP, 0.1) * (t >= self.T_DROP)
        z = 1.12 - 0.08 * eio(u) + 0.05 * k
        dx, dy, dr = shake(t, 9 * k, 12, 21)
        fr = cam(fr, z, dx, dy, -1.5 + 1.5 * u + dr, center=(cx, cy))
        return fr, (3 if k > 0.5 else 0)


# =================================================================================== P03 / P04
# 俯拍：纸扎小人立在生死簿上，朱笔干笔沿四边画框把它框住 → 后拉：太上皇巨大指尖按住框（图形匹配）
BOX_C = (960, 560)


def dry_box(fr, c, half, prog, seed=33, width=30.0):
    pts = [(c[0] - half, c[1] - half), (c[0] + half, c[1] - half), (c[0] + half, c[1] + half), (c[0] - half, c[1] + half), (c[0] - half, c[1] - half * 0.82)]
    m, _ = dry_stroke(pts, prog, width * 1.15, width * 0.75, seed=seed, dry=0.5)
    return ink_stroke(fr, m)


class P03D(Shot):
    HALF = 270
    def __init__(self):
        self.bg = plate('B1_ledger')
        self.doll = lay('B1_doll2_cut')

    def scene(self, t, prog, half, c, light=1.0, zbg=None):
        x, y = K.grid()
        sc = half / P03D.HALF
        fr = view(self.bg, zbg or 1.35 * sc, (0.30, 0.52), (c[0] - 960), (c[1] - 560))
        fr = tone_fade(fr, amt=0.40, level=0.25)                             # 返工 §11①：纵深用网点淡化，不用高斯虚焦
        fr = fr * (0.55 + 0.5 * light * np.exp(-(((x - c[0]) / (900 * sc + 300)) ** 2 + ((y - c[1] + 80) / (620 * sc + 200)) ** 2)))[..., None]
        hh = half * 1.75
        foot = (c[0], c[1] + hh * 0.48)
        sh = np.zeros((H, W), np.float32)
        cv2.ellipse(sh, (int(foot[0] + hh * 0.10), int(foot[1] - hh * 0.01)), (int(hh * 0.24), int(hh * 0.06)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        fr = fr * (1 - 0.55 * cv2.GaussianBlur(sh, (0, 0), 8 * sc + 2)[..., None])
        a, s = self.doll.fit(hh)
        fr, _ = self.doll.draw(fr, t, a, foot, s, rot=1.4 * math.sin(t * 1.9), breathe=0.006, wind_amp=2.0, **SPK)
        return dry_box(fr, c, half, prog, width=max(10, half * 0.11))

    def render(self, t):
        u = self.u(t)
        prog = clamp01((t - self.t0 - 0.05) / 0.72)
        fr = self.scene(t, prog, self.HALF, BOX_C)
        fr = K.dust(fr, t, 1031, n=26, amt=0.22, size=(2, 5), blur=3, color=(0.9, 0.9, 0.9))
        fr = cam(fr, 1.0 + 0.03 * eio(u), -20 * eio(u), 0, 0.8 * u)
        return fr, 0


class P04D(Shot):
    """返工 #5：换景别——太上皇手指压框的近景（手占上 2/3，袖纱拆层飘），框与纸扎人在画下方；47.67「框」一压：框微缩、朱墨迸溅、干笔冲击圈"""
    T_KUANG = V(47.70)
    C = (980.0, 840.0)
    HALF = 230
    def __init__(self):
        self.p3 = P03D()
        self.finger = lay('B1_finger_r2_cut')

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        kq = clamp01((t - self.T_KUANG) / 0.08)
        press = eout(kq, 2) * (1 - 0.6 * clamp01((t - self.T_KUANG - 0.12) / 0.3))
        half = self.HALF * (1 - 0.06 * press)
        fr = self.p3.scene(t, 1.0, half, self.C, light=1.1, zbg=2.3)
        k = eout(clamp01((t - self.t0) / 0.45), 3)
        tip = (self.C[0] - 20, self.C[1] - half - 4 - 360 * (1 - k) + 14 * press)
        shm = np.exp(-(((x - tip[0] - 120) / 380) ** 2)) * sstep(tip[1] + 80, tip[1] - 260, y)
        fr = fr * (1 - 0.40 * cv2.GaussianBlur(shm.astype(np.float32), (0, 0), 30)[..., None] * k)
        fr, _ = put_at(fr, self.finger, t, (0.497, 0.968), tip, 2700, wind=4.0, breathe=0.004)
        fr = flutter(fr, t, self.finger, (0.497, 0.968), tip, 2700, (0.20, 0.10, 0.38, 0.85), amp=9, freq=0.9, seed=1)     # 左袖纱
        fr = flutter(fr, t, self.finger, (0.497, 0.968), tip, 2700, (0.62, 0.10, 0.82, 0.85), amp=-9, freq=0.8, seed=2)    # 右袖纱
        if t >= self.T_KUANG:
            fr = splat(fr, t, self.T_KUANG, 47, (tip[0], tip[1] + 10), n=24, r=(60, 340), size=(3, 12), dur=0.1, sy=0.5)
            fr = dry_ring(fr, (tip[0], tip[1] + 12), 60 + 260 * eout(clamp01((t - self.T_KUANG) / 0.2), 2), clamp01((t - self.T_KUANG) / 0.12),
                          44, w=8, sy=0.35, color=BLOOD)
        pk = pulse(t, self.T_KUANG, 0.1) * (t >= self.T_KUANG)
        dx, dy, dr = shake(t, 8 * pk, 12, 41)
        fr = cam(fr, 1.06 - 0.06 * eio(u) + 0.05 * pk, dx, dy + 30 * (1 - eio(u)), 0.8 * (1 - u) + dr, center=(self.C[0], self.C[1] - 200))
        return fr, (3 if pk > 0.5 else 0)


# =================================================================================== P05
# LS 仰：雨夜宫门，匾「规矩」（生图画进去的干笔刻字）。未唱时字是暗槽；「规」「矩」字头各自白光自上而下灌满 + 一闪
class P05D(Shot):
    SRC = (0.490, 0.395)                # 匾中心（精灵）
    DST = (960.0, 540.0)
    WPX = W * 1.10
    GLY = (0.284, 0.290, 0.692, 0.500)  # 匾内字区（精灵归一化 x0,y0,x1,y1）
    SPLIT = 1041 / 2048                 # 「规」「矩」分界
    def __init__(self):
        self.gate = lay('B1_gate_cut')
        self.sky = plate('B1_skyw', blur=1.5, gain=0.95)
        F = self.gate.F; h, w = F.shape[:2]
        x0, y0, x1, y1 = int(self.GLY[0] * w), int(self.GLY[1] * h), int(self.GLY[2] * w), int(self.GLY[3] * h)
        L = F.mean(-1)
        g = np.zeros((h, w), np.float32); g[y0:y1, x0:x1] = np.clip((L[y0:y1, x0:x1] - 0.38) / 0.25, 0, 1)
        g = cv2.GaussianBlur(g, (0, 0), 0.8)
        xs = int(self.SPLIT * w)
        self.g = [g * (np.arange(w)[None] < xs), g * (np.arange(w)[None] >= xs)]
        self.gy = (y0, y1)
        s = self.WPX / self.gate.w
        self.M = np.float32([[s, 0, self.DST[0] - self.SRC[0] * w * s], [0, s, self.DST[1] - self.SRC[1] * h * s]])
        self.rain = fx2.RainSheet(5051, density=0.8)
        self.tk = [V(CT(9, 2)), V(CT(9, 3))]                                 # 「规」48.66「矩」49.00

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        off = 22 * (eio(u) - 0.5)                                            # 主体微升（中点为零），天空视差 0.4
        fr = flow_layers(self.sky, t - tm(self), 1.15, (0.5, 0.40), flow='swirl', speeds=(0.5, 0.9, 1.4), amp=(6.0, 10.0, 16.0), swirl_c=(0.45, 0.35), seed=5, dy=-0.4 * off)   # §12-2：云沿漩涡切向流动
        fr, Ag = put_at(fr, self.gate, t, self.SRC, (self.DST[0], self.DST[1] - off), self.WPX)
        Mo = self.M.copy(); Mo[1, 2] -= off
        # 门面受光：一道冷白光带自左向右扫过门钉（谁 / 的 两拍各提一下）
        sweep = np.exp(-((x - (-300 + 2600 * clamp01((t - self.t0) / 1.3))) / 300) ** 2)
        lum = fr.mean(-1, keepdims=True)
        hl = np.clip((lum - 0.55) * 3, 0, 1) * (y > 560)[..., None]
        beat = sum(pulse(t, V(CT(9, k)), 0.15) * (t >= V(CT(9, k))) for k in (0, 1))
        fr = fr + hl * Ag[..., None] * (0.35 * sweep[..., None] + 0.25 * beat)
        # 字：暗槽 → 字头白光灌满（从上到下，带波纹液面）+ 白闪 + 匾周围压暗（出字帧字周围压暗）
        y0, y1 = self.gy
        for k in range(2):
            gs = cv2.warpAffine(self.g[k], Mo, (W, H), flags=cv2.INTER_LINEAR)
            tk = self.tk[k]
            fill = eout(clamp01((t - tk + 0.034) / 0.16), 2)
            ys0 = Mo[1, 1] * y0 + Mo[1, 2]; ys1 = Mo[1, 1] * y1 + Mo[1, 2]
            front = ys0 + fill * (ys1 - ys0 + 20) + 6 * np.sin(x * 0.05 + k)
            lit = np.clip((front - y) / 5, 0, 1) * (fill > 0)
            dim = gs * (1 - lit) * 0.80
            fr = fr * (1 - dim[..., None])
            fl = pulse(t, tk, 0.12) * (t >= tk - 0.034)
            if fl > 0.01:
                fr = fr + (gs * 0.45 + K.blur_ds(gs, 3) * 0.25)[..., None] * fl * WHITE3          # 返工 #9：字自身亮起，收辉光
        pk = max(pulse(t, tk_, 0.12) * (t >= tk_) for tk_ in self.tk)
        fr = self.rain.draw(fr, t, intensity=0.55, angle=6, color=(0.75, 0.75, 0.75), layers=(1, 2), cam=(0, -off))
        fr = K.fog(fr, t, 952, amt=0.22, y0=0.68, y1=1.0, color=(0.45, 0.45, 0.45))
        fr = rain_fg(fr, t, tm(self), off=(0, -1.6 * off), alpha=0.45, angle=6)
        dx, dy, dr = shake(t, 5 * pk, 12, 55)
        fr = cam(fr, 1.0 + 0.035 * eio(u) + 0.012 * pk, dx, dy, dr, center=(960, 600))
        return fr, (2 if pk > 0.5 else 0)


# =================================================================================== P06
# CU：门钉特写，血幕（生图）从上沿整片淌下盖住门板，门钉在血里泛白光；「血」49.60 字头血幕骤落 + 溅
class P06D(Shot):
    T_XUE = V(49.62)
    def __init__(self):
        self.door = plate('B1_door2')                                      # 返工二 #6：门钉 = 平涂墨线 + 网点，去镜面球体
        self.blood = lay('B1_blood2_cut')
        self.sp = lay('B1_splat2_cut')
        self.sp2 = lay('B1_splash_i2i_cut')
        L = self.door.mean(-1)
        self.stud = np.clip((L - 0.72) * 4, 0, 1).astype(np.float32)      # 只取硬边白高光（哑光板高光本来就少）

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        z0 = 1.08
        fr = view(self.door, z0, (0.5, 0.5)) * 0.92
        st = view(self.stud, z0, (0.5, 0.5))
        q = clamp01((t - self.t0) / (self.t1 - self.t0))
        drop = 260 * eout(clamp01((t - self.T_XUE) / 0.25), 2) * (t >= self.T_XUE)   # 字头骤落
        bw = W * 1.10; bh = bw * self.blood.h / self.blood.w
        # 后层血幕（翻转、更暗、更慢）：流速差 = 液体的层次
        by2 = min(-bh * 0.70 + (bh * 0.55) * ein(q, 1.2) + 0.6 * drop, 60.0)
        _, A2 = put_at(np.zeros_like(fr), self.blood, t, (0.5, 0.0), (980, by2), bw, wind=0.0)
        fr = fr * (1 - 0.55 * A2[..., None]) + A2[..., None] * 0.55 * BLOOD * 0.75
        by = min(-bh * 0.78 + (bh * 0.72) * ein(q, 1.25) + drop, 60.0)        # 顶边压在上黑边里
        fr, Ab = put_at(fr, self.blood, t, (0.5, 0.0), (940, by), bw, wind=3.0)
        cover = np.maximum(Ab, A2 * 0.6)
        fr = fr + (st * cover)[..., None] * 0.55                                      # 门钉在血下露白高光（哑光血，不发红光）
        if t >= self.T_XUE:
            fr, _ = put_at(fr, self.sp, t, (0.22, 0.50), (640, 700), 300 + 900 * eout(clamp01((t - self.T_XUE) / 0.10), 3),
                           alpha=1 - 0.4 * clamp01((t - self.T_XUE - 0.3) / 0.4))
            fr = splat(fr, t, self.T_XUE, 61, (720, 740), n=20, r=(100, 420), size=(4, 13), dur=0.12, sy=0.8)
        k = pulse(t, self.T_XUE, 0.12) * (t >= self.T_XUE)
        dx, dy, dr = shake(t, 10 * k, 12, 61)
        fr = cam(fr, 1.0 + 0.04 * eio(u) + 0.06 * k, dx, 40 - 80 * eio(u) + dy, dr)
        return fr, (3 if k > 0.5 else 0)


# =================================================================================== P07 / P08 天空（同一张漩涡雷云，P07 作背景虚、P08 全幅实）
VORTEX_C = (0.50, 0.42)


def vortex(t, z, rot0=0.0, blur=0.0, gain=1.0, dy=0.0):
    """返工二 §12-2：漩涡天 = 切向流场驱动的三层同源云（内快外慢、各层不同速度）+ 随时间滚动的湍流 UV + 前后层交叉淡化；不整张旋转"""
    img = plate('B1_vortex', blur=blur, gain=gain)
    return flow_layers(img, t + rot0 * 0.01, z, VORTEX_C, flow='swirl', speeds=(0.7, 1.2, 1.9), amp=(8.0, 14.0, 22.0), swirl_c=VORTEX_C, seed=7, dy=dy - 60)


class P07D(Shot):
    """返工 #3/#4：亮天（白纸 + 墨云 + 血红晕）；主角发丝 + 红带拆层随风飘、呼吸"""
    T_FL = 50.95
    SRC = (0.40, 0.50)
    def __init__(self):
        self.sp = lay('B1_lookup_cut', feather=dict(left=0.14))
        self.sky = plate('B1_skyw')

    def render(self, t):
        u = self.u(t)
        crane = -60 + 90 * eio(u)
        fr = flow_layers(self.sky, t - tm(self), 1.25, (0.55, 0.45), flow='swirl', speeds=(0.6, 1.0, 1.5), amp=(6.0, 11.0, 18.0), swirl_c=(0.45, 0.35), seed=11, dy=-0.35 * crane)
        fr = fx2.cloud_flash(fr, t, t0=self.T_FL, center=(1350, 250), radius=650, seed=7, intensity=0.5, color=(0.9, 0.9, 0.9))
        dst = (880, 600 + crane); WP = 1950 * (1 + 0.008 * math.sin(2 * math.pi * t / 2.6))   # 呼吸
        fr, _ = put_at(fr, self.sp, t, self.SRC, dst, WP, wind=2.0)
        fr = flutter(fr, t, self.sp, self.SRC, dst, WP, (0.00, 0.05, 0.42, 0.62), amp=16, freq=1.4, seed=3)      # 左侧发丝 + 红带
        fr = flutter(fr, t, self.sp, self.SRC, dst, WP, (0.00, 0.62, 0.40, 1.00), amp=12, freq=1.1, seed=5)      # 下摆红带
        fr = rain(fr, t, 971, amt=0.42, n=650, angle=-8, speed=2500)
        fr = rain_fg(fr, t, tm(self), off=(0, -1.6 * crane), alpha=0.5, angle=-8)
        fr = cam(fr, 1.04 - 0.04 * eio(u), 0, 0, -4 + 4 * eio(u))
        return fr, 0


class P08D(Shot):
    """去掉云隙「天」字：仰望漩涡雷云，52.10 闪电从右上贯入漩涡眼，整片天沿闪电劈开、两半错开（不信天）"""
    T_TIAN = V(52.14)
    A = np.array([1500.0, 120.0]); B = np.array([860.0, 760.0])
    def __init__(self):
        self.bolt = lightning_bolt(52, tuple(self.A), tuple(self.B), branches=7)
        self.jag = ((cv2.resize(K.fbm(H // 8, W // 8, 82, base=4, octaves=3), (W, H)) - 0.5) * 60
                    + (cv2.resize(K.fbm(H // 2, W // 2, 83, base=24, octaves=4), (W, H)) - 0.5) * 26).astype(np.float32)   # 低频走向 + 高频锯齿（裂口不是光管）
        self.jag2 = (cv2.resize(K.fbm(H // 8, W // 8, 85, base=10, octaves=3), (W, H)) - 0.5).astype(np.float32) * 2
        self.jag2b = (cv2.resize(K.fbm(H // 2, W // 2, 86, base=40, octaves=3), (W, H)) - 0.5).astype(np.float32) * 2
        self.jag2c = (cv2.resize(K.fbm(H // 2, W // 2, 87, base=40, octaves=3), (W, H)) - 0.5).astype(np.float32) * 2

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        sky = vortex(t * 1.3, 1.05 + 0.06 * eio(u), rot0=40, gain=1.0)
        ps = eout(clamp01((t - (self.T_TIAN + 0.04)) / 0.40), 2)
        a, b = self.A, self.B
        d = (b - a) / np.linalg.norm(b - a); nn = np.array([-d[1], d[0]])
        side = (x - a[0]) * nn[0] + (y - a[1]) * nn[1] + self.jag
        if ps > 0:
            off = 18 * ps
            ML = np.float32([[1, 0, -nn[0] * off - d[0] * off * 0.3], [0, 1, -nn[1] * off + 14 * ps]])
            MR = np.float32([[1, 0, nn[0] * off + d[0] * off * 0.3], [0, 1, nn[1] * off - 14 * ps]])
            RL = cv2.getRotationMatrix2D((700, 520), 3 * ps, 1.0); RR = cv2.getRotationMatrix2D((1200, 520), -2.5 * ps, 1.0)
            SL = cv2.warpAffine(cv2.warpAffine(sky, RL, (W, H), borderMode=cv2.BORDER_REFLECT), ML, (W, H), borderMode=cv2.BORDER_REFLECT)
            SR = cv2.warpAffine(cv2.warpAffine(sky, RR, (W, H), borderMode=cv2.BORDER_REFLECT), MR, (W, H), borderMode=cv2.BORDER_REFLECT)
            wv = 1.0 + 1.4 * np.clip(self.jag2, 0, None)                    # 缝宽沿劈线忽宽忽窄（两边各自锯齿）
            sL = side + self.jag2b * 10; sR = side - self.jag2c * 10
            sl = sstep(-off * wv + 3, -off * wv - 3, sL)[..., None]; sr = sstep(off * wv - 3, off * wv + 3, sR)[..., None]
            gap = np.clip(1 - sl - sr, 0, 1)
            core = np.exp(-(side / (1.5 + 2 * ps)) ** 2)[..., None]
            fr = SL * sl + SR * sr + gap * (np.float32(0.02) + BLOOD * 0.9 * core + core ** 3 * 0.9)   # 缝里是墨黑，芯一线血红白热
            edge = (np.exp(-((sL + off * wv) / 2.5) ** 2) + np.exp(-((sR - off * wv) / 2.5) ** 2))[..., None]
            fr = over(fr, edge[..., 0] * 0.9, INK)
        else:
            fr = sky
        lit = 0.82 + 0.18 * clamp01((t - (self.T_TIAN - 0.05)) / 0.06)
        fr = fr * lit
        if t >= self.T_TIAN - 0.05:
            fr = self.bolt.draw(fr, t, self.T_TIAN, intensity=1.0, color=(1.0, 1.0, 1.0))
        fr = rain(fr, t, 1081, amt=0.30, n=400, angle=-6)
        z = 1.0 + 0.06 * eio(u)
        fr = cam(fr, z, 0, 30 - 60 * eio(u), 3 * eio(u))
        return fr, (3 if abs(t - self.T_TIAN) < 0.04 else 0)


# =================================================================================== P09
# MCU：鬼屠握拳（右）；左边一条血红锁链（命）52.80 字头砸进画面；53.13 刀柄回撞，锁链崩断、碎片炸开
class P09D(Shot):
    T_HIT = V(53.17)
    T_MING = V(52.84)
    HIT = (560.0, 470.0)
    def __init__(self):
        self.bg = plate('B1_whitered')
        self.a = lay('B1_fist_cut', feather=dict(left=0.16))
        self.b = lay('B1_pommel_i2i_cut')                                # §12-1：由 B1_fist 图生图衍生（nano-banana-pro），同机位同比例
        self.chain = rgba('B1_chain_cut'); self.shards = lay('B1_shards_cut')
        self.ring_x, self.ring_y = None, None

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        fr = cv2.flip(flow_layers(self.bg, t - tm(self), 1.10, (0.45, 0.5), flow=(0.0, 0.0), speeds=(0.0, 0.0, 0.0), amp=(3.0, 5.0, 7.0), seed=9), 1)   # §12-2：纸上血墨缓慢洇动（不旋转）
        # 锁链（刚体层，左）：斜挂，字头从 2.2 倍砸到位 + 落定抖
        F, A = self.chain
        cs = 0.62
        if t < self.T_HIT:
            q = clamp01((t - (self.T_MING - 0.10)) / 0.10)
            if q > 0:
                s = cs * (1.0 + 1.2 * (1 - eout(q, 3)))
                wob = 2.0 * math.sin((t - self.T_MING) * 40) * math.exp(-max(0, t - self.T_MING) / 0.12) * (t > self.T_MING)
                M = M_at((A.shape[1] * 0.5, A.shape[0] * 0.5), (560, 470), s, rot=8 + wob)
                fr = fr * (1 - 0.5 * K.blur_ds(cv2.warpAffine(A, M, (W, H)), 30)[..., None] * min(1, q * 1.6))
                fr, _ = paste(fr, F, A, M, alpha=min(1.0, q * 1.6))
        else:                                                                 # 崩断：两半沿撞击法线飞开、旋转；生图碎片层炸开
            q = clamp01((t - self.T_HIT) / 0.5); e = eout(q, 2)
            h_, w_ = A.shape
            for sgn in (-1, 1):
                Ah = A.copy()
                if sgn < 0: Ah[:, w_ // 2 - 30:] = 0
                else: Ah[:, :w_ // 2 + 30] = 0
                M = M_at((w_ * 0.5, h_ * 0.5), (560 + sgn * 380 * e - 120 * e, 470 - sgn * 120 * e + 260 * q * q), cs * (1 + 0.15 * e), rot=8 + sgn * 35 * e)
                fr, _ = paste(fr, F, Ah, M, alpha=1 - 0.6 * clamp01((q - 0.5) / 0.5))
            fr, _ = put_at(fr, self.shards, t, (0.5, 0.5), self.HIT, 900 + 1400 * e, alpha=1 - clamp01((q - 0.35) / 0.65))
            fr = ink_sparks(fr, t, 991, self.HIT, n=50, life=0.5, speed=(400, 1200), dirc=(-1, -0.3), spread=1.3, grav=900, area=(40, 80), t0=self.T_HIT, burst=True)
            ring = clamp01((t - self.T_HIT) / 0.18)
            if ring < 1:
                d = np.sqrt((x - self.HIT[0]) ** 2 + (y - self.HIT[1]) ** 2)
                fr = dry_ring(fr, self.HIT, 60 + 640 * eout(ring, 2), clamp01(ring * 3), 92, w=9 * (1 - ring) + 3, color=(0.03, 0.03, 0.03))
        # 人物（右）：握拳 → 刀柄回撞（两姿势，撞击帧硬切 + 横向动势模糊）
        if t < self.T_HIT:
            fr, _ = put_at(fr, self.a, t, (0.45, 0.30), (1270, 380), 1650, wind=2.0, breathe=0.006)
            fr = flutter(fr, t, self.a, (0.45, 0.30), (1270, 380), 1650, (0.00, 0.05, 0.30, 0.95), amp=14, freq=1.3, seed=9)
        else:
            k = clamp01((t - self.T_HIT) / 0.08)
            fr, _ = put_at(fr, self.b, t, (0.45, 0.30), (1270 - 30 * (1 - k), 380), 1650, wind=2.0, mblur=(-60 * (1 - k), 0))   # 同锚点同尺寸 = 姿势不跳
            fr = flutter(fr, t, self.b, (0.45, 0.30), (1270, 380), 1650, (0.00, 0.05, 0.30, 0.95), amp=14, freq=1.3, seed=9)
        k2 = pulse(t, self.T_MING, 0.1) * (t >= self.T_MING) + pulse(t, self.T_HIT, 0.12) * (t >= self.T_HIT)
        dx, dy, dr = shake(t, 6 + 14 * k2, 8, 9)
        fr = cam(fr, 1.0 + 0.05 * k2 + 0.03 * eio(u), dx, dy, dr)
        if self.T_HIT <= t < self.T_HIT + 2 / 30 - 1e-3:
            a_ = 14 if t < self.T_HIT + 1 / 30 else 6
            fr = np.stack([np.roll(fr[..., 0], a_, 1), fr[..., 1], np.roll(fr[..., 2], -a_, 1)], -1)
        return fr, (4 if k2 > 0.5 else 0)


# =================================================================================== P10 / P11
# 棋盘（斜俯）：刀尖从右探入，「理」「所」两拍把两枚棋子挑飞 → 慢放：黑白两子空中翻滚，「当」白子落盘弹起溅火星
_ST = {}
_SEC = {}


def stones():
    if not _ST:
        F, A = rgba('B1_stone2_cut')
        h, w = A.shape
        for key, (x0, x1) in (('b', (0.07, 0.48)), ('w', (0.52, 0.93))):
            a = A.copy(); a[:, :int(x0 * w)] = 0; a[:, int(x1 * w):] = 0
            ys, xs = np.nonzero(a > 0.5)
            _ST[key] = (F, a, ((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2), xs.max() - xs.min())
    return _ST


def paste_stone(fr, key, pos, size, rot=0.0, sy=1.0, alpha=1.0, smear=(0.0, 0.0)):
    F, A, c, wpx = stones()[key]
    s = size / wpx
    for i, k in enumerate((1.0, 0.45, 0.22) if (smear[0] or smear[1]) else (1.0,)):
        p = (pos[0] - smear[0] * i, pos[1] - smear[1] * i)
        fr, _ = paste(fr, F, A, M_at(c, p, s, rot, sy), alpha=alpha * k)
    return fr


class P10D(Shot):
    T_LI, T_SUO = V(54.0), V(54.18)
    POS = {'b': (830.0, 610.0), 'w': (1020.0, 560.0)}
    def __init__(self):
        self.board = plate('B1_board')
        self.tip = lay('B1_tip_cut')

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        pan = 60 - 160 * eio(u)
        fr = view(self.board, 1.42, (0.52, 0.60), pan, 0, rot=-1.5)
        fr = fr * (0.55 + 0.6 * np.exp(-(((x - 1000) / 850) ** 2 + ((y - 520) / 480) ** 2)))[..., None]
        for key, th in (('b', self.T_LI), ('w', self.T_SUO)):
            p0 = (self.POS[key][0] + pan, self.POS[key][1])
            if t < th - 0.02:                                                  # 落在盘上（带接触影）
                sh = np.zeros((H, W), np.float32); cv2.ellipse(sh, (int(p0[0] + 10), int(p0[1] + 22)), (62, 20), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
                fr = fr * (1 - 0.6 * cv2.GaussianBlur(sh, (0, 0), 6)[..., None])
                fr = paste_stone(fr, key, p0, 120, sy=0.62)
            else:                                                              # 挑飞：抛物线 + 翻滚 + 拖影
                q = t - th
                vx, vy = -900, -1500
                px = p0[0] + vx * q; py = p0[1] + vy * q + 1900 * q * q
                fr = paste_stone(fr, key, (px, py), 120 * (1 + 1.6 * q), rot=-q * 260, sy=0.6 + 0.4 * abs(math.cos(q * 12)),
                                 smear=(vx * 0.012, (vy + 3800 * q) * 0.012))
        tgt = np.array(self.POS['b'] if t < self.T_LI + 0.05 else self.POS['w']) + np.array([pan, 0])
        e = eout(clamp01((t - self.t0) / 0.25), 3)
        flick = pulse(t, self.T_LI, 0.08) * (t >= self.T_LI) + pulse(t, self.T_SUO, 0.08) * (t >= self.T_SUO)
        tip = np.array([tgt[0] + 40, tgt[1] + 18 - 110 * flick]) + np.array([900, 0]) * (1 - e)
        fr, Aw = put_at(fr, self.tip, t, (0.074, 0.432), tuple(tip), 1750, rot=-9 - 10 * flick)
        if flick > 0.3:
            fr = ink_sparks(fr, t, 1010, tuple(tip.astype(int)), n=24, life=0.35, speed=(300, 900), dirc=(-1, -0.6), spread=0.9, grav=900, area=(20, 20))
        fr = cam(fr, 1.04, 0, 0, -1.5)
        return fr, (3 if flick > 0.6 else 0)


class P11D(Shot):
    T_DANG = V(55.10)
    def __init__(self):
        self.board = plate('B1_board')

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        fr = view(self.board, 1.6, (0.40, 0.55), 0, 120, rot=6)
        fr = tone_fade(fr, amt=0.62, level=0.35)                             # 返工 #1：背景网点淡化（去景深虚化、去光斑）
        ts = self.t0 + (t - self.t0) * 0.45                                   # 慢放
        for key, (x0, y0, vx, vy, spin) in (('b', (700, 300, 160, -120, 30)), ('w', (1150, 260, -90, -60, -35))):
            q = ts - self.t0
            if key == 'b':
                px, py = x0 + vx * q * 2, y0 + vy * q * 2 + 260 * q * q * 4
                ang = spin * q * 2; sy = 0.35 + 0.65 * abs(math.cos(q * 3.0))
            else:
                tl = (t - self.t0) / (self.T_DANG - self.t0)
                if t < self.T_DANG:
                    px = x0 + vx * tl; py = y0 + (640 - y0) * tl ** 2; ang = spin * tl; sy = 0.35 + 0.65 * abs(math.cos(tl * 3.0))
                else:
                    b = t - self.T_DANG
                    px = x0 + vx + 60 * b; py = 640 - 140 * math.sin(min(math.pi, b * 9)) * math.exp(-b * 3); ang = spin + 20 * math.sin(b * 12) * math.exp(-b * 4); sy = 0.6
                    sh = np.zeros((H, W), np.float32); cv2.ellipse(sh, (int(px + 8), 690), (150, 36), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
                    fr = fr * (1 - 0.5 * cv2.GaussianBlur(sh, (0, 0), 14)[..., None] * (1 - 0.5 * (640 - py) / 140))
            fr = paste_stone(fr, key, (px, py), 330, rot=ang, sy=sy)
        if t >= self.T_DANG:
            ring = clamp01((t - self.T_DANG) / 0.22)                          # 返工 #1：干笔飞白圈 + 溅墨 + 硬边短划火星
            fr = dry_ring(fr, (1060, 690), 80 + 460 * eout(ring, 2), clamp01(ring * 2.5), 111, w=10 * (1 - 0.6 * ring), sy=0.30, color=(0.03, 0.03, 0.03))
            fr = splat(fr, t, self.T_DANG, 112, (1060, 690), n=18, r=(120, 520), size=(3, 9), dur=0.12, sy=0.3)
            fr = ink_sparks(fr, t, 1111, (1060, 660), n=34, life=0.45, speed=(300, 800), dirc=(0, -1), spread=1.1, grav=1300, area=(80, 8), t0=self.T_DANG, burst=True)
        q = clamp01((t - (self.t0 + 0.15)) / 0.25)
        if 0 < q < 1:
            m_, _ = dry_stroke([(-100, 760), (2020, 80)], eout(q / 0.6, 2), 10, 4, seed=113, dry=0.6)     # 刃光改干笔白划
            fr = ink_stroke(fr, m_ * (1 - clamp01((q - 0.5) / 0.5)), WHITE3, edge=0.5)
        k = pulse(t, self.T_DANG, 0.1) * (t >= self.T_DANG)
        dx, dy, dr = shake(t, 10 * k, 12, 11)
        fr = cam(fr, 1.0 + 0.06 * eio(u) + 0.04 * k, dx - 40 * eio(u), dy, dr)
        return fr, (3 if k > 0.5 else 0)


# =================================================================================== P12
# MCU：鬼屠竖刀当面，刀身把脸一分为二（整把刀在画内）；一线寒光自刀尖扫到护手
class P12D(Shot):
    """返工 #2/#6：两个关键姿势——竖刀分脸 →「信」字头刀身翻转、刃面反光一闪（生图 bladeface_b）；发丝 / 红带拆层飘；
    背景红底网点 + 墨渍（生图 redtone，去平滑渐变）。原 f1665–1666 两条横向白线是寒光高斯带越过刀身 → 改成硬边、只在刀身内"""
    SRC, DST, WPX = (0.5, 0.5), (960.0, 572.0), 1460.0
    T_FLIP = V(55.74)
    def __init__(self):
        self.sp = lay('B1_bladeface_r3_cut'); self.sp2 = lay('B1_bladeface_b2_cut')
        self.bg = plate('B1_redtone')

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        fr = view(self.bg, 1.12, (0.5, 0.45), -30 * (eio(u) - 0.5), 0)
        if t < self.T_FLIP:
            fr, Aw = put_at(fr, self.sp, t, self.SRC, self.DST, self.WPX, wind=2.0, breathe=0.006)
            fr = flutter(fr, t, self.sp, self.SRC, self.DST, self.WPX, (0.18, 0.12, 0.44, 0.62), amp=14, freq=1.2, seed=12)   # 左侧发丝
            fr = flutter(fr, t, self.sp, self.SRC, self.DST, self.WPX, (0.05, 0.62, 0.32, 1.00), amp=12, freq=1.0, seed=13)   # 左下红带
        else:
            k = clamp01((t - self.T_FLIP) / 0.08)
            fr, Aw = put_at(fr, self.sp2, t, self.SRC, (self.DST[0], self.DST[1] + 8 * (1 - k)), self.WPX, wind=2.0, breathe=0.006,
                            mblur=(40 * (1 - k), -30 * (1 - k)))
            fr = flutter(fr, t, self.sp2, self.SRC, self.DST, self.WPX, (0.00, 0.55, 0.30, 0.95), amp=12, freq=1.1, seed=14)   # 左下红带
            a = spt(self.sp2, self.SRC, self.DST, self.WPX, (0.37, 0.27)); b = spt(self.sp2, self.SRC, self.DST, self.WPX, (0.80, 0.71))
            q = clamp01((t - self.T_FLIP) / 0.25)                             # 刃面反光：一道硬边白光沿刀身扫下，只在精灵内
            pp = a + (b - a) * eio(q)
            d = b - a; d /= np.linalg.norm(d)
            g = np.exp(-((((x - pp[0]) * d[0] + (y - pp[1]) * d[1]) / 26) ** 2 + (((x - pp[0]) * -d[1] + (y - pp[1]) * d[0]) / 3.2) ** 2))
            g = g * Aw                                                      # 严格裁在刀身 alpha 内（不外溢、不成横向线）
            fr = fr + np.clip(g * 2.2, 0, 1)[..., None] * (1 - q) * 0.85
            fr = fr + (pulse(t, self.T_FLIP, 0.06) * (t >= self.T_FLIP)) * 0.25
        fr = ink_sparks(fr, t, 1212, (960, 980), n=20, life=1.2, speed=(60, 200), dirc=(0, -1), spread=0.8, grav=-60, area=(900, 40), amt=0.8)
        pk = pulse(t, self.T_FLIP, 0.1) * (t >= self.T_FLIP)
        dx, dy, dr = shake(t, 5 * pk, 12, 121)
        fr = cam(fr, 1.0 + 0.03 * eio(u) + 0.02 * pk, dx, dy, dr)
        return fr, (2 if pk > 0.5 else 0)


# =================================================================================== P13
# MS 低机位：鬼屠撩斩（两姿势：出刀 → 收势），56.47「刀」字头一道干笔血红刀弧（生图）自左下扫到右上，雷云漩涡被照亮
class P13D(Shot):
    T_DAO = V(56.50)
    FOOT = (860.0, 975.0)
    def __init__(self):
        self.w = lay('B1_windup_cut'); self.a = lay('B1_slash_i2i_r2_cut'); self.b = lay('B1_slash2_i2i_cut')   # 返工二 #10：三姿势都由图生图衍生，刀形制与 P12/P14 一致   # §12-1：出刀帧由蓄势帧图生图，同脚位同比例
        self.arc = rgba('B1_arc_cut')
        h, w = self.arc[1].shape
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.arc_ang = np.arctan2(yy - h * 1.05, xx - w * 0.35)                # 弧心在下方：角度 = 扫过进度

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        ka = clamp01((t - (self.T_DAO - 0.10)) / 0.14)
        glow = (1 - clamp01((t - self.T_DAO) / 0.5)) * (ka > 0)
        fr = flow_layers(plate('B1_field'), t - tm(self), 1.12, (0.55, 0.52), flow=(1.0, -0.25), speeds=(0.8, 1.5, 2.4), amp=(5.0, 9.0, 14.0), seed=13,
                         dx=-30 * (eio(u) - 0.5), dy=30) * (0.90 + 0.10 * glow)   # §12-2：云条沿风向三层不同速度流过
        fr = fr * (1 - 0.45 * sstep(840, 1000, y))[..., None]                 # 地面压暗
        fr = K.fog(fr, t, 1301, amt=0.22, y0=0.72, y1=1.0, color=(0.5, 0.5, 0.5))
        # 收势姿势的刀尖（刀弧终点、火星发射点）
        a_b, s_b = self.b.fit(840)
        fb = (self.FOOT[0] + 20, self.FOOT[1])
        tipb = (fb[0] + (0.925 - a_b[0]) * self.b.w * s_b, fb[1] + (0.012 - a_b[1]) * self.b.h * s_b)
        if ka > 0:                                                            # 干笔刀弧（在人物身后）：按扫角逐步露出，0.45s 内淡去
            F, A = self.arc
            amin, amax = float(self.arc_ang[A > 0.3].min()), float(self.arc_ang[A > 0.3].max())
            reveal = sstep(amin + (amax - amin) * eout(ka, 2) + 0.05, amin + (amax - amin) * eout(ka, 2) - 0.05, self.arc_ang)
            Ar = A * reveal * (1 - 0.85 * clamp01((t - self.T_DAO - 0.12) / 0.4))
            M = M_at((A.shape[1] * 0.80, A.shape[0] * 0.16), (tipb[0] - 40, tipb[1] + 30), 0.82, rot=-6)
            fr, Aw = paste(fr, F, Ar, M)
            fr = fr + K.blur_ds(Aw, 20)[..., None] * BLOOD * 0.6 * glow
        # 返工 #3：三姿势——蓄势（windup）→「刀」字头硬切出刀（slash_a）→ 收势（slash_b，0.2s 后）
        sp = self.w if t < self.T_DAO else (self.a if t < self.T_DAO + 0.20 else self.b)
        hpx = 760 if sp is self.w else (760 if sp is self.a else 840)
        a_, s_ = sp.fit(hpx) if sp is not self.a else self.w.fit(760)          # 出刀帧沿用蓄势帧的落脚与缩放（同一张底图衍生）
        k = clamp01((t - self.T_DAO) / 0.08)
        fr, _ = sp.draw(fr, t, a_, (self.FOOT[0] + (20 if sp is self.b else 0), self.FOOT[1]), s_, breathe=0.004 if sp is self.w else 0.0, wind_amp=2.0,
                        mblur=(50 * (1 - k), -60 * (1 - k)) if sp is self.a else (0, 0), **SPK)
        if 0 < ka and t < self.T_DAO + 0.1:                                   # 刀尖一线白光（出刀那一下）
            q_ = clamp01((t - self.T_DAO + 0.10) / 0.3)
            m_, _ = dry_stroke([(tipb[0] - 520, tipb[1] + 390), (tipb[0] + 200, tipb[1] - 150)], eout(q_ / 0.5, 2), 9, 3, seed=131, dry=0.6)
            fr = ink_stroke(fr, m_ * (1 - clamp01((q_ - 0.5) / 0.5)), WHITE3, edge=0.5)
        fr = ink_sparks(fr, t, 1313, (int(tipb[0]), int(tipb[1])), n=36, life=0.6, speed=(200, 700), dirc=(0.5, -1), spread=1.0, grav=600, area=(60, 40), t0=self.T_DAO, burst=True)
        fr = rain(fr, t, 1302, amt=0.25, n=350, angle=-6)
        kk = pulse(t, self.T_DAO, 0.1) * (t >= self.T_DAO)
        dx, dy, dr = shake(t, 14 * kk, 10, 13)
        fr = cam(fr, 1.0 + 0.07 * eio(u) + 0.04 * kk, dx, dy, dr - 2 + 3 * eio(u), center=(900, 600))
        return fr, (4 if kk > 0.5 else 0)


# =================================================================================== P14
# CU 斜构图：握刀的手，刀身从护手斜出右上；57.43「滚」热从刀尖往护手烧下来（白热芯 + 血红），57.73「烫」整段通红、火星剥落、热浪
def blade_heat_sprite(sp, src, heat, front, t, seed=0, chips=None, g_src=(0.53, 0.47), tip_src=(1.03, -0.03)):
    """返工二 #3：刀身烧红在**精灵空间**算（跟着精灵一起仿射）→ 贴真实刃口。
    刀身轴 = 护手 g_src → 刀尖 tip_src；along>0 才算刀身（手在负向，不会被烧到）；
    热 = 刃口一侧的一条线起烧、向刀背渗进，渗进边界 wavy + 噪声；只用血红 + 刃口一线白热；
    叠沿刀向的墨线裂纹 + 从刃口剥落的红片。返回 (Frgb, Aout, Ink)。"""
    h, w = sp.A.shape
    ax, ay = src[0] * w, src[1] * h
    P0 = np.array([g_src[0] * w, g_src[1] * h], np.float32); P1 = np.array([tip_src[0] * w, tip_src[1] * h], np.float32)
    dvec = P1 - P0; L = float(np.linalg.norm(dvec)); dvec /= L
    nrm = np.array([-dvec[1], dvec[0]], np.float32)                                       # 指向刀背
    gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
    along = ((gx - P0[0]) * dvec[0] + (gy - P0[1]) * dvec[1]) / L
    side = ((gx - P0[0]) * nrm[0] + (gy - P0[1]) * nrm[1])
    lum = sp.F.mean(-1)
    steel = (sp.A > 0.5) & (lum > 0.42) & (along > 0.02) & (along < 1.02) & (np.abs(side) < 0.10 * h)
    if steel.sum() < 200: return np.zeros((h, w, 3), np.float32), np.zeros((h, w), np.float32), np.zeros((h, w), np.float32)
    hw = float(np.percentile(np.abs(side[steel]), 92)) or (0.02 * h)                       # 刀身半宽（实测）
    edge = side * np.sign(np.median(side[steel]) if np.median(np.abs(side[steel])) > 1e-3 else 1.0)
    e0 = float(np.max(np.abs(side[steel]))) * 0 + hw                                        # 刃口在 -hw 侧（离轴最远的那侧）
    s_in = (hw - np.abs(side)) / max(1.0, hw)                                               # 0 = 刃口边, 1 = 轴
    e_in = 1.0 - s_in                                                                       # 0 = 刃口边, 1 = 刀背
    r = np.random.default_rng(seed)
    wv = cv2.resize(r.random((1, 40)).astype(np.float32), (w, 1), interpolation=cv2.INTER_CUBIC)[0]
    wv2 = cv2.resize(r.random((1, 120)).astype(np.float32), (h, 1), interpolation=cv2.INTER_CUBIC)[:, 0]
    wob = ((wv - 0.5) * 0.85)[None, :] + ((wv2 - 0.5) * 0.45)[:, None]
    depth = clamp01(heat) * 1.28                                                            # 渗进深度（刃口 → 刀背比例）
    hot = np.clip((depth - e_in - wob * 0.18) / 0.10, 0, 1) * steel.astype(np.float32)
    reach = np.ones_like(along, np.float32) if front >= 1 else np.clip((along - (1 - front) * 1.05) / 0.08, 0, 1)
    hot = np.clip(hot * reach, 0, 1)
    cr = np.zeros((h, w), np.float32)
    for a0, s0, l0, a1, s1, w0 in r.random((70, 6)).astype(np.float32):
        c0 = P0 + dvec * (a0 * L * 0.95) + nrm * (hw * (s0 * 1.6 - 0.8))
        c1 = c0 + dvec * (l0 * 0.05 * L) + nrm * (hw * (s1 - 0.5) * 0.7)
        cv2.line(cr, tuple(c0.astype(int)), tuple(c1.astype(int)), 1.0, 1 + int(w0 * 2), cv2.LINE_AA)
    cr = cr * hot
    fl = np.zeros((h, w), np.float32)
    if chips is None: chips = clamp01(heat - 0.55) * 1.6
    if chips > 0.01:
        for a0, s0, l0, r0 in r.random((26, 4)).astype(np.float32):
            c = P0 + dvec * ((0.12 + 0.85 * a0) * L) + nrm * (hw * (1.02 + 0.12 * s0))
            m = np.zeros((h // 2, w // 2), np.float32)
            cv2.ellipse(m, (int(c[0] / 2), int(c[1] / 2)), (max(2, int(3 + 5 * r0)), max(1, int(2 + 2 * r0))), -30 - 60 * l0, 0, 360, 1.0, -1, cv2.LINE_AA, 2)
            fl = np.maximum(fl, cv2.resize(m, (w, h)) * chips)
    rim = np.exp(-((e_in - 0.02) / 0.05) ** 2) * hot * 0.8                                   # 刃口一线白热（细）
    Frgb = hot[..., None] * (BLOOD * 1.3) + rim[..., None] * 0.85 + fl[..., None] * (BLOOD * 1.2)
    Aout = np.clip(hot + rim * 0.8 + fl, 0, 1)
    ink = np.clip(cv2.dilate(hot, np.ones((3, 3), np.uint8)) - hot, 0, 1) * 0.75 + cr * 0.9 + \
        np.clip(cv2.dilate(fl, np.ones((3, 3), np.uint8)) - fl, 0, 1) * 0.9
    return Frgb, Aout, np.clip(ink, 0, 1)


def blade_heat_sprite_UNUSED(fr, Aw, g, tip, half_w, heat, front=1.0, t=0.0, seed=0, edge_side=1.0):
    """返工 #6：刀身烧红 = 由刃口一侧向内推进的血红（硬边 + 墨线裂纹 + 刃口一线白热），不是光剑式整条发光渐变"""
    x, y = K.grid()
    g = np.asarray(g, float); tip = np.asarray(tip, float)
    d = tip - g; L = np.linalg.norm(d); d /= L; n = np.array([-d[1], d[0]])
    along = ((x - g[0]) * d[0] + (y - g[1]) * d[1]) / L
    side = ((x - g[0]) * n[0] + (y - g[1]) * n[1]) / half_w * edge_side            # +1 刃口 … -1 刀背
    band = sstep(1.25, 0.85, np.abs(side)) * sstep(0.04, 0.10, along) * Aw
    reach = sstep(1 - front - 0.08, 1 - front + 0.02, along)
    k = ('hnz', seed)
    if k not in _P:
        _P[k] = cv2.resize(K.fbm(H // 8, W // 8, seed, base=10, octaves=4), (W, H))
    nz = _P[k]
    depth = 2.05 * clamp01(heat)                                                 # 烧进的深度：刃口 → 刀背（刃口一侧大半烧红，刀背留一线钢色）
    hot = ((side + (nz - 0.5) * 0.5) > (1.0 - depth)).astype(np.float32)
    hot = cv2.GaussianBlur(hot, (0, 0), 0.8) * band * reach
    kc = ('crk', seed)
    if kc not in _P:
        _P[kc] = np.random.default_rng(seed).random((40, 6))
    cr = np.zeros((H, W), np.float32)
    for a0, s0, l0, a1, s1, w0 in _P[kc]:                                       # 墨线裂纹：沿刀身的细碎折线
        pa = g + d * L * (0.1 + 0.85 * a0) + n * half_w * edge_side * (s0 * 1.6 - 0.6)
        pb = pa + d * L * 0.04 * (l0 + 0.3) + n * half_w * edge_side * (s1 - 0.5) * 0.8
        cv2.line(cr, tuple(pa.astype(int)), tuple(pb.astype(int)), 1.0, 1 + int(w0 * 1.5), cv2.LINE_AA)
    cr = cr * hot
    out = fr * (1 - hot[..., None]) + hot[..., None] * BLOOD * 1.25
    edge = np.clip(cv2.dilate(hot, np.ones((3, 3), np.uint8)) - hot, 0, 1)
    out = over(out, edge * 0.8, INK)
    out = over(out, cr * 0.9, INK)
    rim = np.exp(-((side - 1.0) / 0.12) ** 2) * band * reach * clamp01(heat)       # 刃口一线白热（硬边细线）
    return out + rim[..., None] * 0.8, band * reach


class P14D(Shot):
    """返工二 #3：刀身烧红 = 贴着真实刃口的一条线起烧、向刀背渗进（wavy 边界 + 墨线 + 红片剥落），
    整个热层在精灵空间算完再跟精灵一起做仿射 → 不会变成横跨刀身的直红条"""
    SRC, DST, WPX = (0.48, 0.52), (880.0, 620.0), 2450.0
    def __init__(self):
        self.sp = lay('B1_grip_i2i_cut')                                  # 返工二 #3：img2img 洗掉刀身上的红色涂条（原图自带），只剩钢色 → 热层自己做刃口烧红
        self.bg = plate('B1_whitered')
        self.tex = K.tile(512, 914, 6, 4)
        self.heat = {}

    def heat_layer(self, t, heat, front):
        k = round(heat, 3), round(front, 3)
        if k not in self.heat:
            self.heat[k] = blade_heat_sprite(self.sp, self.SRC, heat, front, t, seed=14)
        return self.heat[k]

    def render(self, t):
        u = self.u(t)
        z = 1.0 + 0.10 * eio(u)
        dst = (self.DST[0] - 40 * eio(u), self.DST[1] + 30 * eio(u))
        wpx = self.WPX * z
        x, y = K.grid()
        fr = flow_layers(self.bg, t - tm(self), 1.15, (0.45, 0.50), flow=(0.0, 0.0), speeds=(0.0, 0.0, 0.0), amp=(3.0, 5.0, 7.0), seed=14, dx=-12 * eio(u))
        heat = 0.30 + 0.70 * clamp01((t - V(57.48) + 0.10) / 0.42)
        front = clamp01((t - (V(57.48) - 0.15)) / 0.45)                       # 0..1：从刀尖往护手烧过来
        fr, Aw = put_at(fr, self.sp, t, self.SRC, dst, wpx, wind=0.0)
        Frgb, Ah, Ink = self.heat_layer(t, heat, front)
        s = wpx / self.sp.w
        M = cv2.getRotationMatrix2D((self.SRC[0] * self.sp.w, self.SRC[1] * self.sp.h), 0.0, s)
        M[0, 2] += dst[0] - self.SRC[0] * self.sp.w; M[1, 2] += dst[1] - self.SRC[1] * self.sp.h
        M = M.astype(np.float32)
        Fw = cv2.warpAffine(Frgb, M, (W, H)); Aw2 = cv2.warpAffine(Ah, M, (W, H))[..., None]
        Iw = cv2.warpAffine(Ink, M, (W, H))
        fr = fr * (1 - Aw2) + Fw * Aw2
        fr = over(fr, Iw, INK)
        g = spt(self.sp, self.SRC, dst, wpx, (0.53, 0.47)); tip = spt(self.sp, self.SRC, dst, wpx, (1.03, -0.03))
        band = Aw * (np.float32(1.0))
        mid = ((g + tip) / 2).astype(int)
        fr = ink_sparks(fr, t, 1414, tuple(mid), n=44, life=0.9, speed=(120, 420), dirc=(-0.4, -1), spread=0.8, grav=-80, area=(160, 220), amt=min(1.0, 0.5 + 0.6 * front))
        fr = _SEC['mod'].heat_haze(fr, t, self.tex, 3 + 6 * heat * front)
        dx, dy, dr = shake(t, 3 + 5 * front, 13, 14)
        return cam(fr, 1.0, dx, dy, dr), 0


# =================================================================================== P15
# MS 侧身平端横刀（刀尖指画左）：刃口余烬红，缓推 + 火星沿刃剥落；59.10 鼓停：一线寒光由刀镡扫向刀尖，压暗憋住 → 副歌一 S028 横刀
class P15D(Shot):
    T_HOLD = V(59.13)
    SRC, DST, WPX = (0.55, 0.47), (1010.0, 600.0), 1660.0
    def __init__(self):
        self.sp = lay('B1_guard2_cut'); self.sp2 = lay('B1_guard_i2i_cut')   # §12-1：第二拍握紧（guard2 图生图）
        self.tex = K.tile(512, 915, 6, 4)

    def render(self, t):
        tr = t
        if t > self.T_HOLD: t = self.T_HOLD + (t - self.T_HOLD) * 0.05
        u = clamp01((t - self.t0) / (self.T_HOLD - self.t0))
        x, y = K.grid()
        fr = flow_layers(plate('B1_bands'), t - tm(self), 1.12, (0.5, 0.48), flow=(1.0, 0.0), speeds=(0.7, 1.3, 2.1), amp=(5.0, 9.0, 14.0), seed=15)   # §12-2：云带三层不同速度横流
        dst = (self.DST[0] + 30 * (1 - eio(u)), self.DST[1])
        wpx = self.WPX * (1.0 + 0.07 * eio(u))
        fr = K.fog(fr, t, 1501, amt=0.22, y0=0.6, y1=1.0, color=(0.45, 0.45, 0.45))
        spx = self.sp if t < V(58.66) else self.sp2                          # 58.63（军鼓）握紧换第二姿势，同锚点同尺寸
        fr, Aw = put_at(fr, spx, t, self.SRC, dst, wpx, wind=2.0, breathe=0.006)
        fr = flutter(fr, t, spx, self.SRC, dst, wpx, (0.15, 0.62, 0.48, 1.00), amp=18, freq=1.3, seed=15)   # 返工 #3：左下红带拆层飘
        fr = flutter(fr, t, spx, self.SRC, dst, wpx, (0.62, 0.00, 1.00, 0.36), amp=-12, freq=1.1, seed=16)  # 马尾发丝向右飘（刀身行 0.40–0.46 不动）
        fr = flutter(fr, t, spx, self.SRC, dst, wpx, (0.72, 0.72, 1.00, 0.95), amp=-10, freq=1.5, seed=17)  # 右下红带
        g = spt(spx, self.SRC, dst, wpx, (0.680, 0.430)); tip = spt(spx, self.SRC, dst, wpx, (0.020, 0.430))
        qs = clamp01((t - (self.t0 + 0.15)) / 0.35)                            # 返工 #3：入镜后第一道寒光扫过刀身（刀镡 → 刀尖）
        if 0 < qs < 1:
            px = g[0] + (tip[0] - g[0]) * eio(qs); py = g[1] + (tip[1] - g[1]) * eio(qs)
            sh0 = np.exp(-(((x - px) / 80) ** 2 + ((y - py) / 8) ** 2)) * Aw
            fr = fr + np.clip(sh0 * 2, 0, 1)[..., None] * (1 - qs)
        # 返工二：刀身余烬红 = 精灵空间热层（贴刃口一条线；刀身很薄，depth 只给一点点）
        kk = ('p15h', round(t, 2), int(t < V(58.66)))
        if kk not in _P:
            _P[kk] = blade_heat_sprite(spx, self.SRC, 0.22, 1.0, t, seed=15, g_src=(0.680, 0.430), tip_src=(-0.02, 0.430), chips=0.0)
        Frgb, Ah, Inkh = _P[kk]
        sc = wpx / spx.w
        M = cv2.getRotationMatrix2D((self.SRC[0] * spx.w, self.SRC[1] * spx.h), 0.0, sc).astype(np.float32)
        M[0, 2] += dst[0] - self.SRC[0] * spx.w; M[1, 2] += dst[1] - self.SRC[1] * spx.h
        Fw = cv2.warpAffine(Frgb, M, (W, H)); Aw2 = cv2.warpAffine(Ah, M, (W, H))[..., None]
        fr = fr * (1 - Aw2) + Fw * Aw2
        band = Aw
        q = clamp01((t - (self.T_HOLD - 0.20)) / 0.22)
        if q > 0:
            px = g[0] + (tip[0] - g[0]) * eio(q); py = g[1] + (tip[1] - g[1]) * eio(q)
            sh = np.exp(-(((x - px) / 70) ** 2 + ((y - py) / 10) ** 2)) * band
            fr = fr + sh[..., None] * 1.4 + K.blur_ds(sh.astype(np.float32), 14)[..., None] * 0.5
        fr = ink_sparks(fr, t, 1515, tuple(((g + tip) / 2).astype(int)), n=50, life=1.0, speed=(80, 300), dirc=(0.0, -1), spread=0.9, grav=-100,
                        area=(int(abs(g[0] - tip[0]) / 2), 12), amt=0.9)
        fr = rain(fr, t, 1502, amt=0.28, n=420, angle=-6)
        fr = _SEC['mod'].heat_haze(fr, t, self.tex, 3)
        fr = cam(fr, 1.0 + 0.06 * eio(u), 0, 0, 0)
        if tr > self.t1 - 6 / 30:                                              # 返工 #4：压暗推迟到最后 6 帧内
            fr = fr * (1 - 0.5 * clamp01((tr - (self.t1 - 6 / 30)) / (6 / 30)))
        return fr, 0


# =================================================================================== 装配
LIFT = {'P05': (0.10, 0.70), 'P06': (0.12, 0.68), 'P07': (0.06, 0.80), 'P08': (0.12, 0.66), 'P09': (0.04, 0.85),
        'P12': (0.12, 0.70), 'P13': (0.08, 0.78), 'P14': (0.10, 0.75), 'P15': (0.06, 0.78)}   # 返工 #4：(抬黑位, gamma)


D_SHOTS = {'P01': P01D, 'P02': P02D, 'P03': P03D, 'P04': P04D, 'P05': P05D, 'P06': P06D, 'P07': P07D, 'P08': P08D,
           'P09': P09D, 'P10': P10D, 'P11': P11D, 'P12': P12D, 'P13': P13D, 'P14': P14D, 'P15': P15D}


def apply(mod):
    """把 sec_b_pre1 的 SHOTS 换成 D 版（沿用原类名 → CUTS / FG / EXPO / MOVE 键不变；t0/t1 取原类），并改风格 D 下的表项"""
    _SEC['mod'] = mod
    new = []
    for S in mod.SHOTS:
        D = D_SHOTS.get(S.__name__)
        if D is None: new.append(S); continue
        D.t0, D.t1 = S.t0, S.t1
        D.__name__ = S.__name__
        new.append(D)
    mod.SHOTS[:] = new
    W3 = np.full(3, 0.85, np.float32)
    mod.CUTS['P11'] = ('flash', 0, 0, {})                                     # 金闪 → 白闪（风格 D 无金）
    mod.CUTS['P12'] = ('match_cut', 0.0, 0.12, dict(shape='rect', center=(960, 470), radius=140, glow=np.zeros(3, np.float32)))   # 返工二 #1：矩形边光 = 全幅横向白线（f1664–1666 穿帮）→ 取消边光，只保留图形匹配的展开
    for k, (kind, a) in list(mod.FG.items()):
        if kind == 'ember': mod.FG[k] = ('ash', min(0.45, a))                 # 橙余烬 → 灰烬
    for S in mod.SHOTS:
        mod.EXPO[S.__name__] = 1 / 1.12                                       # 抵消段落 expo_all=1.12，保留生图本身的黑白（同 V09D）
    for nm, (bk, gm) in LIFT.items():                                          # 返工 #4：暗镜提亮（抬黑位 + gamma）
        D = D_SHOTS[nm]
        if '_render0' not in D.__dict__:
            D._render0 = D.render
            def _lit(self, t, _b=bk, _g=gm):
                fr, ca = self._render0(t)
                return lift(fr, _b, _g), ca
            D.render = _lit
    mod.MOVE['P12'] = (1.0, 1.03, 0, 20, 0)                                   # 整刀在画：补充推镜 7% → 3%
