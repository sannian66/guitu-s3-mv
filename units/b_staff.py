"""units/b_staff.py — B 组第九棒：V08「柄在嚣张」去手重做用的公共件。
- staff_tex()：从 S051/grip_scepter 原图（3840 宽，不走 2560 抠图）沿杖身取「握手以下」那段乌木杖，拉直成竖条贴图（无手）
- floor_plate()：低机位雨夜宫阶石板地（透视石缝 + 积水反光 + 远处宫灯）
只依赖 c1kit / numpy / cv2。"""
import math, os
import numpy as np, cv2
import c1kit as K

W, H = 1920, 1080
ROOT = '/workspace/work/mv'
_C = {}


def staff_tex():
    """返回 (F, A)：竖直杖身，上端=远离地面，下端=杖镦（加铜箍）；约 200×1700"""
    if 'tex' in _C: return _C['tex']
    from PIL import Image
    im = np.asarray(Image.open(ROOT + '/assets/gen/S051/grip_scepter_raw.png').convert('RGB')).astype(np.float32) / 255
    # 握手下方的杖段（原图坐标）：上 (952,1330) → 下 (1032,2160)，宽约 200
    p0, p1, wd = np.float32([952, 1330]), np.float32([1032, 2160]), 200
    L = float(np.linalg.norm(p1 - p0)); d = (p1 - p0) / L; n = np.float32([d[1], -d[0]])
    src = np.float32([p0 - n * wd / 2, p0 + n * wd / 2, p1 - n * wd / 2])
    dst = np.float32([[0, 0], [wd, 0], [0, L]])
    M = cv2.getAffineTransform(src, dst)
    seg = cv2.warpAffine(im, M, (wd, int(L)), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    seg = seg[30:]                                               # 去掉贴着手指的那一截
    F = np.concatenate([seg[::-1], seg], 0)                      # 两段对接（纹样上下对称，像一根整杖）
    h = F.shape[0]
    xx = np.linspace(-1, 1, wd, dtype=np.float32)[None]
    A = np.clip((1 - np.abs(xx)) / 0.08, 0, 1) * np.ones((h, 1), np.float32)
    shade = (0.55 + 0.45 * np.cos(np.clip(xx + 0.25, -1.4, 1.4) * 1.1)) ** 1.2      # 圆柱明暗（光从左前）
    F = F * shade[..., None]
    # 杖镦铜箍：下端 70px
    yy = np.arange(h, dtype=np.float32)[:, None]
    band = np.clip((yy - (h - 70)) / 3, 0, 1)
    bronze = np.array([0.20, 0.15, 0.08], np.float32) * (0.6 + 0.9 * np.exp(-((xx + 0.35) / 0.18) ** 2))[..., None]
    bronze = bronze + (np.abs(((yy - (h - 70)) % 22) - 11) < 1.5)[..., None] * 0.04
    F = F * (1 - band[..., None]) + bronze * band[..., None]
    _C['tex'] = (F.astype(np.float32), A.astype(np.float32))
    return _C['tex']


def draw_staff(fr, F, A, foot, ang_deg, scale, alpha=1.0, mblur=0.0):
    """把杖贴到屏幕：杖镦底边中点 → foot，绕 foot 倾 ang_deg（正 = 杖顶向右），返回 (fr, Aw)"""
    h, w = A.shape
    M = cv2.getRotationMatrix2D((w / 2, h), -ang_deg, scale)
    M[0, 2] += foot[0] - w / 2; M[1, 2] += foot[1] - h
    Fw = cv2.warpAffine(F * A[..., None], M, (W, H)); Aw = cv2.warpAffine(A, M, (W, H))
    if mblur > 1:
        k = np.zeros((int(mblur) * 2 + 1, 1), np.float32); k[:, 0] = 1; k /= k.sum()
        Fw = cv2.filter2D(Fw, -1, k); Aw = cv2.filter2D(Aw, -1, k)
    Aw = Aw * alpha
    return fr * (1 - Aw[..., None]) + Fw * alpha, Aw


def floor_plate(seed=5401, hor=420, camH=1.0, f=900.0):
    """低机位雨夜石板地：返回 (bg, floor_mask, (X,Z)) — 地面以上是雨夜远景（宫灯焦外），以下是透视石缝 + 积水反光"""
    key = ('floor', seed, hor)
    if key in _C: return _C[key]
    x, y = K.grid()
    sky = np.clip((y - 0) / hor, 0, 1)[..., None]
    bg = (np.array([0.020, 0.022, 0.030], np.float32) * (1 - sky) + np.array([0.075, 0.080, 0.095], np.float32) * sky)
    fog = cv2.resize(K.fbm(H // 8, W // 8, seed, 4, 5), (W, H))[..., None]
    bg = bg * (0.75 + 0.5 * fog)
    # 远处宫灯焦外（暖），只在地平线上下
    rng = np.random.default_rng(seed)
    lan = np.zeros((H, W), np.float32)
    for _ in range(7):
        lx, ly = rng.uniform(80, W - 80), hor - rng.uniform(40, 150); r = rng.uniform(18, 34)
        lan += np.exp(-(((x - lx) / r) ** 2 + ((y - ly) / r) ** 2)) * rng.uniform(0.5, 1.0)
    # 远处殿基 / 台阶暗影（一道水平暗带，不是城墙：无垛口）
    base = sstep_np(hor - 60, hor - 10, y) * (1 - sstep_np(hor, hor + 4, y))
    bg = bg * (1 - 0.45 * base[..., None])
    # 地面
    fl = (y > hor).astype(np.float32)
    yy = np.maximum(y - hor, 1.0)
    Z = camH * f / yy; X = (x - W / 2) * Z / f
    tile = 0.9
    gx = np.abs(((X / tile) % 1.0) - 0.5); gz = np.abs((((Z + 0.37 * np.floor(X / tile)) / (tile * 0.6)) % 1.0) - 0.5)
    seam = ((0.5 - gx) < 0.018 / np.clip(Z, 0.3, 40) * 6) | ((0.5 - gz) < 0.018 / np.clip(Z, 0.3, 40) * 6)
    seam = cv2.GaussianBlur(seam.astype(np.float32), (0, 0), 0.8)
    stone = cv2.resize(K.fbm(H // 4, W // 4, seed + 1, 6, 6), (W, H))
    flo = np.array([0.075, 0.078, 0.085], np.float32) * (0.7 + 0.6 * stone)[..., None]
    flo = flo * (1 - 0.35 * seam[..., None])
    # 积水反光：远景上下翻转 + 宫灯拉长倒影（越远越亮）
    ref = cv2.flip(bg, 0); sh = 2 * hor - H
    ref = np.roll(ref, sh, axis=0)
    lan_r = np.roll(cv2.flip(lan, 0), sh, axis=0)
    lan_r = cv2.GaussianBlur(lan_r, (0, 0), sigmaX=6, sigmaY=40)
    wet = np.clip(0.35 + 0.5 * cv2.resize(K.fbm(H // 6, W // 6, seed + 2, 3, 4), (W, H)), 0, 1) * (1 - 0.7 * seam)
    fres = np.clip(1.2 - yy / 700, 0.25, 1.0)
    flo = flo + (ref * 1.6 + lan_r[..., None] * np.array([0.55, 0.25, 0.08], np.float32)) * (wet * fres)[..., None]
    bg = bg + lan[..., None] * np.array([0.75, 0.32, 0.10], np.float32)
    out = bg * (1 - fl[..., None]) + flo * fl[..., None]
    _C[key] = (out.astype(np.float32), fl, (X, Z))
    return _C[key]


def sstep_np(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-9), 0, 1); return t * t * (3 - 2 * t)


def crack_mask(A, origin, p, seed=0, n=9, reach=260):
    """碎裂：字形 A 自 origin 径向「裂开」到 p（0..1），外加 n 道放射裂纹；返回 (glyph_mask, crack_lines)"""
    x, y = K.grid()
    d = np.sqrt((x - origin[0]) ** 2 + ((y - origin[1]) * 1.8) ** 2)
    R = 20 + 420 * p
    g = A * np.clip((R - d) / 30, 0, 1)
    lines = np.zeros((H, W), np.float32)
    rng = np.random.default_rng(seed)
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi); L = reach * rng.uniform(0.5, 1.0) * p
        pts = [origin]; cx, cy = origin
        for s in range(6):
            a += rng.uniform(-0.5, 0.5); st = L / 6
            cx += math.cos(a) * st; cy += math.sin(a) * st * 0.55; pts.append((cx, cy))
        cv2.polylines(lines, [np.int32(pts)], False, 1.0, 2, cv2.LINE_AA)
    return g, cv2.GaussianBlur(lines, (0, 0), 0.7)
