"""units/b_carve.py — B 组第七棒：「字和物件互动」公共件（刻进物件表面 / 嵌金 / 烙印 / 投影光 / 碎裂）。
不改共享库；只依赖 typo / c1kit。"""
import math
import numpy as np, cv2
import typo as T
import c1kit as K

W, H = 1920, 1080


def mask(places, fname='serif_black', blur=0.0):
    """places: [(ch, x, y, size, rot)] → (H,W) 字形遮罩"""
    L = T.Layer()
    for ch, x, y, s, r in places:
        T.place(L, ch, x, y, s, color='white', fname=fname, alpha=1.0, rot=r, texture=False)
    A = np.clip(L.A, 0, 1).astype(np.float32)
    if blur > 0.3: A = cv2.GaussianBlur(A, (0, 0), blur)
    return A


def _shift(A, dx, dy):
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(A, M, (A.shape[1], A.shape[0]), borderMode=cv2.BORDER_CONSTANT)


def engrave(fr, A, light=(-0.6, -0.8), depth=6.0, groove=0.6, fill=None, fill_k=0.0, hl_col=(1.0, 0.95, 0.85), hl=0.5,
            surface=None, glow=0.0, glow_col=(1.0, 0.6, 0.2)):
    """阴刻：A 为字形遮罩；light 主光方向（指向光源）；depth 槽壁像素；groove 槽底压暗；
    fill/fill_k 嵌料（金/朱/墨），surface 只在物件 alpha 内生效；glow 嵌金反光辉光"""
    if surface is not None: A = A * surface
    lx, ly = light
    n = math.hypot(lx, ly) + 1e-6; lx, ly = lx / n, ly / n
    out_toward_light = _shift(A, -lx * depth, -ly * depth)     # 朝光一侧的槽壁 → 被槽沿挡住 = 阴影
    sh = np.clip(A - out_toward_light, 0, 1)
    away = _shift(A, lx * depth, ly * depth)
    lit = np.clip(A - away, 0, 1)                               # 背光一侧槽壁受光
    lum = (fr * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
    out = fr * (1 - A[..., None] * groove)
    if fill is not None and fill_k > 0:
        tex = 0.55 + 0.9 * np.clip(lum / (lum.mean() + 1e-3), 0.3, 1.8) * 0.5
        out = out * (1 - A[..., None] * fill_k) + A[..., None] * fill_k * np.asarray(fill, np.float32) * tex
    out = out * (1 - sh[..., None] * 0.75)
    out = out + lit[..., None] * np.asarray(hl_col, np.float32) * hl
    # 槽沿外缘一圈细高光（刻痕边口）
    rim = np.clip(_shift(A, lx * 1.5, ly * 1.5) - A, 0, 1)
    out = out + rim[..., None] * np.asarray(hl_col, np.float32) * hl * 0.35
    if glow > 0:
        out = out + K.blur_ds(A, 14)[..., None] * np.asarray(glow_col, np.float32) * glow
    return out


def reveal(A, p, box=None, axis='y', soft=18.0):
    """刻刀推进：沿 y（自上而下）或 x 显出遮罩；返回 (A', 刀口位置)"""
    ys, xs = np.nonzero(A > 0.2)
    if len(ys) == 0: return A * 0, None
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    yy, xx = np.mgrid[0:A.shape[0], 0:A.shape[1]].astype(np.float32)
    if axis == 'y':
        f = y0 + (y1 - y0 + soft) * p
        m = np.clip((f - yy) / soft, 0, 1)
        front = (float((x0 + x1) / 2), float(min(f, y1)))
    else:
        f = x0 + (x1 - x0 + soft) * p
        m = np.clip((f - xx) / soft, 0, 1)
        front = (float(min(f, x1)), float((y0 + y1) / 2))
    return A * m, front


def light_project(fr, A, col=(1.0, 0.62, 0.25), amt=1.6, blur=6.0, ambient=0.35):
    """投影光：字形镂空窗透进来的光打在场景上（乘性提亮 + 少量加光），场景其余压到 ambient"""
    Ab = cv2.GaussianBlur(A, (0, 0), blur) if blur > 0.3 else A
    c = np.asarray(col, np.float32)
    return fr * (ambient + (1 - ambient) * 0.0 + Ab[..., None] * amt * c) + Ab[..., None] * c * 0.05


def brand(fr, A, heat, surface=None, cool=0.0):
    """烙印：heat 1 = 炽红发光，0 = 焦黑烙痕（cool 留金边）"""
    if surface is not None: A = A * surface
    Ai = cv2.erode(A, np.ones((3, 3), np.uint8))
    scorch = cv2.GaussianBlur(A, (0, 0), 3)
    out = fr * (1 - scorch[..., None] * 0.55)
    hotc = np.array([1.0, 0.35, 0.08], np.float32) * heat + np.array([1.0, 0.85, 0.5], np.float32) * heat ** 3 * 0.6
    out = out * (1 - Ai[..., None] * 0.8) + Ai[..., None] * (np.array([0.035, 0.02, 0.015], np.float32) + hotc)
    out = out + K.blur_ds(A, 12)[..., None] * np.array([1.0, 0.3, 0.06], np.float32) * heat * 0.9
    if cool > 0:
        edge = np.clip(A - cv2.erode(A, np.ones((5, 5), np.uint8)), 0, 1)
        out = out + edge[..., None] * np.array([0.9, 0.66, 0.3], np.float32) * cool * 0.5
    return out


def split_layer(F, A, p0, p1, off_a, off_b):
    """沿直线 p0→p1 把图层 (F 预乘, A) 劈成两半，分别平移 off_a（线左/上侧）、off_b，返回 (F, A, 裂口线遮罩)"""
    yy, xx = np.mgrid[0:A.shape[0], 0:A.shape[1]].astype(np.float32)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    side = (xx - p0[0]) * dy - (yy - p0[1]) * dx
    sa = np.clip(side / 2.0 + 0.5, 0, 1)
    outF = np.zeros_like(F); outA = np.zeros_like(A)
    for s, off in ((sa, off_a), (1 - sa, off_b)):
        M = np.float32([[1, 0, off[0]], [0, 1, off[1]]])
        outF += cv2.warpAffine(F * s[..., None], M, (A.shape[1], A.shape[0]))
        outA += cv2.warpAffine(A * s, M, (A.shape[1], A.shape[0]))
    nrm = math.hypot(dx, dy) + 1e-6
    line = np.exp(-(side / nrm / 3.0) ** 2)
    return outF, np.clip(outA, 0, 1), line
