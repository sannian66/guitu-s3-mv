"""units/c_piying.py — C 组第八棒：皮影人偶（critic_C_r4 P1③：C03 扁平「裙装图标」纸人 → 真皮影）。
侧身古装人偶：高冠 + 空脸（镂空脸只留轮廓线与眼眉）+ 分段手臂（肩/肘关节铆钉）+ 宽袍下摆；
袍面是半透明染色牛皮（茜红、石青、藤黄），面上刻镂空纹（圆钱纹、菱纹），边缘是不透光的深色皮边。
合成用「透射」：幕后光穿过皮料被染色（fr * 染色透射率），镂空处直接透出幕光 → 自然背光。"""
import math
import numpy as np, cv2

_CACHE = {}
PALETTES = [
    # (冠, 上衣, 下摆, 腰带)：透射率（0..1，越大越透）
    ((0.85, 0.22, 0.12), (0.30, 0.62, 0.55), (0.88, 0.28, 0.14), (0.95, 0.78, 0.30)),
    ((0.30, 0.25, 0.20), (0.90, 0.70, 0.25), (0.28, 0.50, 0.62), (0.85, 0.25, 0.12)),
    ((0.85, 0.22, 0.12), (0.88, 0.30, 0.16), (0.35, 0.58, 0.40), (0.95, 0.80, 0.35)),
    ((0.30, 0.45, 0.60), (0.85, 0.62, 0.30), (0.80, 0.26, 0.16), (0.30, 0.55, 0.45)),
]


def piying_sprite(seed, h=300):
    """返回 (Tr: h×w×3 透射率, A: h×w 覆盖度, rivets: [(x,y)] 关节铆钉坐标)。人偶面朝右，脚底在 0.96h。"""
    key = (seed, h)
    if key in _CACHE: return _CACHE[key]
    r = np.random.default_rng(seed)
    S = 2                                   # 超采样
    hh = h * S; w = int(h * 0.62) * S; cx = w * 0.46
    A = np.zeros((hh, w), np.float32)
    Tr = np.zeros((hh, w, 3), np.float32)
    pal = PALETTES[seed % len(PALETTES)]
    def P(x, y): return [int(cx + x * hh), int(y * hh)]
    def poly(pts, col, a=1.0):
        m = np.zeros((hh, w), np.uint8); cv2.fillPoly(m, [np.array([P(*p) for p in pts], np.int32)], 255, cv2.LINE_AA)
        m = m.astype(np.float32) / 255 * a
        Tr[:] = Tr * (1 - m[..., None]) + np.asarray(col, np.float32) * m[..., None]
        A[:] = np.maximum(A, m)
        return m
    # 下摆（宽袍，后摆略拖）
    lower = poly([(-0.07, 0.43), (0.06, 0.43), (0.10, 0.62), (0.17, 0.90), (0.04, 0.92), (-0.12, 0.92), (-0.19, 0.89), (-0.11, 0.62)], pal[2])
    # 下摆缘边（藤黄宽边，上刻一排菱纹）
    hem = poly([(-0.175, 0.84), (0.155, 0.845), (0.17, 0.90), (0.04, 0.92), (-0.12, 0.92), (-0.19, 0.89)], pal[3])
    # 靴
    poly([(-0.07, 0.90), (-0.01, 0.90), (-0.01, 0.955), (0.07, 0.96), (0.07, 0.975), (-0.07, 0.975)], (0.18, 0.14, 0.12))
    # 上衣（躯干，微前倾）
    upper = poly([(-0.075, 0.205), (0.055, 0.20), (0.075, 0.30), (0.065, 0.44), (-0.075, 0.44), (-0.09, 0.30)], pal[1])
    # 腰带 + 垂绦
    poly([(-0.08, 0.41), (0.07, 0.41), (0.07, 0.445), (-0.08, 0.445)], pal[3])
    poly([(-0.01, 0.445), (0.015, 0.445), (0.03, 0.62), (0.005, 0.63)], pal[3])
    # 颈
    poly([(-0.018, 0.17), (0.022, 0.17), (0.028, 0.215), (-0.022, 0.215)], (0.95, 0.82, 0.62))
    # 头：侧脸（额-鼻-唇-下巴轮廓）
    face = poly([(-0.045, 0.085), (0.035, 0.085), (0.05, 0.115), (0.062, 0.135), (0.048, 0.142), (0.052, 0.158), (0.040, 0.165),
                 (0.034, 0.185), (-0.01, 0.19), (-0.05, 0.16), (-0.058, 0.12)], (0.97, 0.86, 0.66))
    # 高冠（帽翅后飘）
    poly([(-0.06, 0.095), (-0.05, 0.035), (0.0, 0.0), (0.045, 0.03), (0.048, 0.092)], pal[0])
    poly([(-0.05, 0.05), (-0.16, 0.025), (-0.17, 0.045), (-0.055, 0.075)], pal[0])
    # 发髻后垂
    poly([(-0.058, 0.10), (-0.085, 0.13), (-0.10, 0.24), (-0.07, 0.22), (-0.05, 0.15)], (0.16, 0.13, 0.12))
    # 手臂：肩 → 肘 → 手（两段，宽袖），角度随 seed
    a1 = math.radians(r.uniform(35, 75)); a2 = a1 + math.radians(r.uniform(-70, -20))
    sh = (0.03, 0.235); L1, L2 = 0.13, 0.12
    el = (sh[0] + L1 * math.cos(a1) * 0.8, sh[1] + L1 * math.sin(a1))
    hd = (el[0] + L2 * math.cos(a2), el[1] + L2 * math.sin(a2))
    def limb(p0, p1, w0, w1, col):
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]; n = math.hypot(dx, dy) + 1e-6; nx, ny = -dy / n, dx / n
        return poly([(p0[0] + nx * w0, p0[1] + ny * w0), (p1[0] + nx * w1, p1[1] + ny * w1),
                     (p1[0] - nx * w1, p1[1] - ny * w1), (p0[0] - nx * w0, p0[1] - ny * w0)], col)
    limb(sh, el, 0.032, 0.03, pal[1])
    limb(el, hd, 0.03, 0.04, pal[1])                         # 宽袖口
    cv2.circle(A, tuple(P(*hd)), int(0.016 * hh), 1.0, -1, cv2.LINE_AA)
    cv2.circle(Tr, tuple(P(*hd)), int(0.016 * hh), (0.95, 0.82, 0.62), -1, cv2.LINE_AA)
    # 后臂（较暗，被身体挡一部分）
    b1 = a1 + math.radians(r.uniform(20, 50))
    limb((-0.04, 0.235), (-0.04 + 0.12 * math.cos(b1) * 0.6, 0.235 + 0.12 * math.sin(b1)), 0.028, 0.034, tuple(np.asarray(pal[1]) * 0.7))
    # ---- 镂空：脸（空脸只留眼眉线）、袍面圆钱纹 + 菱纹、冠上一排圆孔
    cut = np.zeros((hh, w), np.float32)
    fm = cv2.erode((face > 0.5).astype(np.uint8), np.ones((int(0.012 * hh), int(0.012 * hh)), np.uint8)).astype(np.float32)
    cut = np.maximum(cut, fm)
    keep = np.zeros_like(cut)
    cv2.line(keep, tuple(P(0.012, 0.118)), tuple(P(0.040, 0.116)), 1.0, max(2, int(0.006 * hh)), cv2.LINE_AA)    # 眉
    cv2.ellipse(keep, tuple(P(0.028, 0.130)), (int(0.013 * hh), int(0.0045 * hh)), -4, 0, 360, 1.0, -1, cv2.LINE_AA)  # 眼
    cv2.line(keep, tuple(P(0.020, 0.170)), tuple(P(0.036, 0.168)), 1.0, max(2, int(0.004 * hh)), cv2.LINE_AA)    # 唇
    sp = 0.056
    for gy in np.arange(0.25, 0.89, sp):
        for gx in np.arange(-0.17, 0.17, sp):
            ox = (sp / 2) if int(round(gy / sp)) % 2 else 0
            x, y = gx + ox, gy
            c = tuple(P(x, y))
            if not (0 <= c[0] < w and 0 <= c[1] < hh): continue
            inside = (upper[c[1], c[0]] > 0.5 and y < 0.40) or (lower[c[1], c[0]] > 0.5 and y > 0.47)
            if not inside: continue
            if y < 0.80 or (int(gx / sp) % 2 == 0):                 # 圆钱纹：环形镂空 + 中心方孔留皮
                cv2.circle(cut, c, int(0.013 * hh), 1.0, -1, cv2.LINE_AA)
                cv2.circle(keep, c, int(0.0075 * hh), 1.0, -1, cv2.LINE_AA)
                q = int(0.003 * hh); cv2.rectangle(cut, (c[0] - q, c[1] - q), (c[0] + q, c[1] + q), 1.0, -1)
            else:                                                       # 菱纹
                d = 0.010 * hh
                pts = np.array([[c[0], c[1] - d], [c[0] + d * 0.7, c[1]], [c[0], c[1] + d], [c[0] - d * 0.7, c[1]]], np.int32)
                cv2.fillPoly(cut, [pts], 1.0, cv2.LINE_AA)
    for k in range(4):
        cv2.circle(cut, tuple(P(-0.03 + k * 0.022, 0.06)), int(0.007 * hh), 1.0, -1, cv2.LINE_AA)
    cut = np.clip(cut - keep, 0, 1)
    A = A * (1 - cut)
    # 皮边：外轮廓与镂空边一圈深色不透光（刻刀边）
    k = max(3, int(0.008 * hh)) | 1
    edge = np.clip(A - cv2.erode(A, np.ones((k, k), np.uint8)), 0, 1)
    edge = np.maximum(edge, np.clip(cv2.dilate(cut, np.ones((k, k), np.uint8)) - cut, 0, 1) * A)
    Tr = Tr * (1 - 0.82 * edge[..., None])
    # 皮料纹理（牛皮纤维 + 不均匀厚度）
    fib = cv2.GaussianBlur(r.random((hh, w)).astype(np.float32), (0, 0), 1.2)
    thick = cv2.resize(r.random((hh // 24 + 2, w // 24 + 2)).astype(np.float32), (w, hh), interpolation=cv2.INTER_CUBIC)
    Tr = Tr * (0.78 + 0.22 * fib[..., None]) * (0.85 + 0.25 * thick[..., None])
    # 缩回
    A = cv2.resize(A, (w // S, h), interpolation=cv2.INTER_AREA)
    Tr = cv2.resize(Tr, (w // S, h), interpolation=cv2.INTER_AREA)
    rv = [(P(*sh)[0] / S, P(*sh)[1] / S), (P(*el)[0] / S, P(*el)[1] / S), (P(-0.04, 0.235)[0] / S, P(-0.04, 0.235)[1] / S),
          (P(0.0, 0.43)[0] / S, P(0.0, 0.43)[1] / S)]
    hand = (P(*hd)[0] / S, P(*hd)[1] / S)
    _CACHE[key] = (Tr.astype(np.float32), A.astype(np.float32), rv, hand)
    return _CACHE[key]


def draw_piying(fr, sp, cx, top, ang, light=1.0, flip=False, base=None):
    """把皮影贴在幕上：fr 在人偶处被染色透射（背光），关节铆钉为不透光的小铜钉（带一点高光）。
    (cx, top) = 头顶挂线点；ang 绕头顶旋转（度）。返回 (fr, 手的画面坐标)。"""
    Tr, A, rv, hand = sp
    h, w = A.shape
    if flip:
        Tr = Tr[:, ::-1]; A = A[:, ::-1]; rv = [(w - x, y) for x, y in rv]; hand = (w - hand[0], hand[1])
    ax = w * 0.46 if not flip else w * 0.54
    M = cv2.getRotationMatrix2D((ax, 0), ang, 1.0); M[0, 2] += cx - ax; M[1, 2] += top
    H_, W_ = fr.shape[:2]
    x0 = int(max(0, cx - h)); x1 = int(min(W_, cx + h)); y0 = int(max(0, top - 10)); y1 = int(min(H_, top + h * 1.3))
    if x1 <= x0 or y1 <= y0: return fr, (cx, top)
    M2 = M.copy(); M2[0, 2] -= x0; M2[1, 2] -= y0
    a = cv2.warpAffine(A, M2, (x1 - x0, y1 - y0))
    tr = cv2.warpAffine(Tr, M2, (x1 - x0, y1 - y0))
    sub = fr[y0:y1, x0:x1]
    src = sub if base is None else np.maximum(sub, np.asarray(base, np.float32))   # base：无幕处用固定暖光（被烛光照亮的皮料）
    lit = src * tr * (1.25 * light)                       # 透射：幕光穿过染色皮料
    fr[y0:y1, x0:x1] = sub * (1 - a[..., None]) + lit * a[..., None]
    def tp(p): return (M[0, 0] * p[0] + M[0, 1] * p[1] + M[0, 2], M[1, 0] * p[0] + M[1, 1] * p[1] + M[1, 2])
    rad = max(2, int(h * 0.011))
    for p in rv:
        x, y = tp(p)
        cv2.circle(fr, (int(x), int(y)), rad, (0.05, 0.035, 0.02), -1, cv2.LINE_AA)
        cv2.circle(fr, (int(x - rad * 0.3), int(y - rad * 0.3)), max(1, rad // 2), (0.55, 0.42, 0.22), -1, cv2.LINE_AA)
    return fr, tp(hand)
