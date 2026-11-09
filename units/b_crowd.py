"""units/b_crowd.py — [B组] 第五棒：生图纸扎人群像（crowd_bow / crowd_back / effigy_fall）拆成单体精灵并合成。
- figs('crowd_bow') → 6 个侧身鞠躬纸人单体（按 alpha 列间隙切分），每个可绕脚底单独俯仰（实现「依次鞠躬」）
- draw(fr, fig, foot, h_px, tilt, ...)：脚底锚点、包围盒高度 h_px、绕脚底旋转 tilt（度，正 = 直起），统一调色 + 轮廓光 + 景深"""
import os, math
import numpy as np, cv2
from PIL import Image
from c1kit import W, H, sstep
GEN = '/workspace/work/mv/assets/gen/B_r4/'
_C = {}


class Fig:
    def __init__(self, F, A):
        self.F = F.astype(np.float32); self.A = A.astype(np.float32)
        ys, xs = np.nonzero(self.A > 0.5)
        self.y1 = ys.max(); self.y0 = ys.min()
        self.footx = float(np.median(xs[ys > self.y1 - 12]))
        self.h = self.y1 - self.y0
        gx = cv2.Sobel(self.A, cv2.CV_32F, 1, 0, ksize=5); gy = cv2.Sobel(self.A, cv2.CV_32F, 0, 1, ksize=5)
        self.gx, self.gy = gx, gy
        self.ring = cv2.GaussianBlur(np.clip(self.A - cv2.erode(self.A, np.ones((7, 7), np.uint8)), 0, 1), (0, 0), 1.5)


def _load(name, work_w=2048):
    im = Image.open(GEN + name + '_cutd.png').convert('RGBA')
    im = im.resize((work_w, round(im.size[1] * work_w / im.size[0])), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    return a[..., :3].copy(), a[..., 3].copy()


def figs(name='crowd_bow'):
    if name in _C: return _C[name]
    F, A = _load(name)
    if name == 'crowd_bow':
        col = (A > 0.3).sum(0)
        # 头部前伸会和前一个人重叠：用下半身（腿/袍底）列占用找间隙
        low = (A[int(A.shape[0] * 0.70):] > 0.3).sum(0)
        occ = low > 2
        segs = []; inn = False
        for x in range(len(occ)):
            if occ[x] and not inn: s = x; inn = True
            if not occ[x] and inn: segs.append((s, x)); inn = False
        if inn: segs.append((s, len(occ)))
        segs = [sg for sg in segs if sg[1] - sg[0] > 40]
        out = []
        for i, (a, b) in enumerate(segs):
            # 每人的列范围：左边界 = 本人袍底左缘往左让出头部前伸量
            L = int(max(0, a - (b - a) * 0.55)); R = int(b + 6)
            if i + 1 < len(segs): R = min(R, segs[i + 1][0] - 2)
            m = np.zeros_like(A); m[:, L:R] = 1
            # 去掉前一个人的身体（只保留与本人袍底连通的部分）
            sub = (A[:, L:R] > 0.3).astype(np.uint8)
            n, lab, st, _ = cv2.connectedComponentsWithStats(sub, 8)
            yb = int(A.shape[0] * 0.85); xc = (a + b) // 2 - L
            keep = lab[yb - 40:yb + 40, max(0, xc - 20):xc + 20]
            ids = np.unique(keep[keep > 0])
            mm = np.isin(lab, ids).astype(np.float32)
            mm = cv2.dilate(mm, np.ones((5, 5), np.uint8))
            out.append(Fig(F[:, L:R] * 1, A[:, L:R] * mm))
        _C[name] = out
    else:
        _C[name] = [Fig(F, A)]
    return _C[name]


def draw(fr, fig, foot, h_px, tilt=0.0, expo=0.8, tint=(1.0, 0.97, 0.92), sat=0.6, rim_col=(1.0, 0.8, 0.5), rim_amt=1.0, rim_dir=(0.7, -0.7),
         alpha=1.0, blur=0.0, sil=0.0, flip=False, wet=0.0):
    """sil 0..1：压成逆光剪影（保留一点纸纹）；wet：雨湿压暗+冷"""
    s = h_px / fig.h
    F = fig.F; A = fig.A
    lum = F.mean(-1, keepdims=True)
    G = np.clip(lum + (F - lum) * sat, 0, 1) * expo * np.array(tint, np.float32)
    if wet > 0: G = G * (1 - 0.45 * wet) * np.array([0.92, 0.97, 1.06], np.float32) ** wet
    n = np.sqrt(fig.gx ** 2 + fig.gy ** 2) + 1e-4
    facing = np.clip(-(fig.gx * rim_dir[0] + fig.gy * rim_dir[1]) / n, 0, 1)
    rim = (fig.ring * (0.3 + 0.7 * facing))[..., None]
    if sil > 0: G = G * (1 - 0.88 * sil)
    G = G + rim * np.array(rim_col, np.float32) * rim_amt * 0.5
    px, py = fig.footx, float(fig.y1)
    M = cv2.getRotationMatrix2D((px, py), tilt, s)
    if flip:
        M = cv2.getRotationMatrix2D((px, py), -tilt, s); M[0, 0] *= -1; M[1, 0] *= -1
        M[0, 2] = foot[0] - (M[0, 0] * px + M[0, 1] * py); M[1, 2] = foot[1] - (M[1, 0] * px + M[1, 1] * py)
    else:
        M[0, 2] += foot[0] - px; M[1, 2] += foot[1] - py
    Fw = cv2.warpAffine(G, M, (W, H), flags=cv2.INTER_LINEAR)
    Aw = cv2.warpAffine(A, M, (W, H), flags=cv2.INTER_LINEAR) * alpha
    if blur > 0.5:
        Fw = cv2.GaussianBlur(Fw * Aw[..., None], (0, 0), blur); Aw = cv2.GaussianBlur(Aw, (0, 0), blur)
        Fw = Fw / np.clip(Aw[..., None], 1e-3, None)
    bgb = cv2.GaussianBlur(fr, (0, 0), 14)
    wrap = (Aw * np.clip(1 - cv2.GaussianBlur(Aw, (0, 0), 8), 0, 1) * 1.6)[..., None] * 0.3
    Fw = Fw + bgb * wrap
    return fr * (1 - Aw[..., None]) + Fw * Aw[..., None], Aw
