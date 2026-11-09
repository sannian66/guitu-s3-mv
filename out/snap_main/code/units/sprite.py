"""units/sprite.py — 人物精灵图层（SPRITE_MODE 试点，2026-11-09）
把抠好的生图人物（RGBA PNG）当作 2.5D 图层合进代码场景：场景/粒子/字幕/运镜仍是代码。
  SpriteLayer(path)                 读入 + 预计算（发区权重、轮廓带）
  .draw(fr, t, cx, cy, h, ...)      2.5D 摆放（随相机推拉/平移）、风吹网格形变、呼吸缩放、调色匹配、冷色 rim、光包裹
开关：环境变量 SPRITE_MODE=1 时 units/chorus1.py 的 S043 改用 S043Sprite；默认 0 = 原代码人物，其他镜头不受影响。
"""
import math, os
import numpy as np, cv2
from PIL import Image

W, H = 1920, 1080


def _sstep(a, b, x):
    x = np.clip((x - a) / (b - a), 0, 1); return x * x * (3 - 2 * x)


class SpriteLayer:
    def __init__(self, path, work_w=2048):
        im = Image.open(path).convert('RGBA')
        hh = round(im.size[1] * work_w / im.size[0])
        a = np.asarray(im.resize((work_w, hh), Image.LANCZOS)).astype(np.float32) / 255
        self.A = a[..., 3].copy()
        self.F = a[..., :3].astype(np.float32)                     # 场景管线是显示空间（finish 不做 gamma）
        self.h, self.w = self.A.shape
        F = a[..., :3]
        lum = F.mean(-1)
        skin = _sstep(0.02, 0.08, F[..., 0] - F[..., 2]) * _sstep(0.18, 0.35, lum)   # 暖亮 = 皮肤（不吹）
        skin = cv2.dilate(skin, np.ones((15, 15), np.uint8))
        # 离轮廓越近越「飘」：发梢、外圈发丝、衣摆边
        inside = (self.A > 0.5).astype(np.uint8)
        dist = cv2.distanceTransform(inside, cv2.DIST_L2, 5)
        edge_w = np.clip(1 - dist / 90.0, 0, 1) ** 1.3
        edge_w = np.maximum(edge_w, (self.A < 0.5) * 1.0)
        hair = _sstep(0.30, 0.12, lum) + _sstep(0.45, 0.65, lum) * (F[..., 2] > F[..., 0])  # 暗发 + 冷色高光发丝
        self.wind_w = cv2.GaussianBlur((edge_w * np.clip(hair, 0, 1) * (1 - skin)).astype(np.float32), (0, 0), 6)
        ring = self.A - cv2.erode(self.A, np.ones((5, 5), np.uint8))
        self.ring = cv2.GaussianBlur(np.clip(ring, 0, 1), (0, 0), 1.5)
        gy, gx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        self.gx, self.gy = gx, gy
        ys, xs = np.nonzero(self.A > 0.5)
        self.bbox = (xs.min() / self.w, ys.min() / self.h, xs.max() / self.w, ys.max() / self.h) if len(xs) else (0, 0, 1, 1)
        self.top = (xs[ys.argmin()] / self.w, ys.min() / self.h) if len(xs) else (0.5, 0)   # 最高点（举刀=刀尖）

    def fit(self, target_h, foot=None, ref='bbox'):
        """按 alpha 包围盒高度缩放：返回 (anchor_src=脚底中点, scale)。"""
        x0, y0, x1, y1 = self.bbox
        return ((x0 + x1) / 2, y1), target_h / ((y1 - y0) * self.h)

    # ---- 风吹：分区网格（粗网格 sin 位移 → 放大 → remap）
    def wind(self, t, amp=7.0, wdir=(-1.0, 0.15), freq=0.9):
        gh, gw = 36, 64
        yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
        yn, xn = yy / gh, xx / gw
        ph = 2 * math.pi * freq * t
        s = (np.sin(ph + yn * 7.0 + xn * 3.0) * 0.6 + np.sin(1.7 * ph + yn * 13.0 - xn * 5.0 + 1.3) * 0.3
             + np.sin(0.45 * ph + yn * 3.0) * 0.4)
        gust = 0.75 + 0.25 * math.sin(2 * math.pi * 0.31 * t)
        dx = cv2.resize((s * wdir[0] * gust).astype(np.float32), (self.w, self.h), interpolation=cv2.INTER_CUBIC)
        dy = cv2.resize((np.cos(ph * 1.3 + xn * 6 + yn * 4) * 0.35 + s * wdir[1]).astype(np.float32), (self.w, self.h),
                        interpolation=cv2.INTER_CUBIC)
        k = self.wind_w * amp
        mx = self.gx - dx * k; my = self.gy - dy * k
        F = cv2.remap(self.F, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        A = cv2.remap(self.A, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        R = cv2.remap(self.ring, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        return F, A, R

    def draw(self, fr, t, anchor_src, anchor_dst, scale, rot=0.0, breathe=0.005, wind_amp=7.0,
             grade=dict(expo=0.66, sat=0.55, tint=(0.90, 0.96, 1.06), lift=0.0, gamma=1.25),
             rim=dict(col=(0.62, 0.74, 1.0), amt=1.6, dir=(-0.8, -0.6)), wrap=0.35, mblur=(0.0, 0.0), extra_A=None, shade=(700, 1600, 0.30, 650, 0.45), keep_red=1.0, alpha=1.0, defocus=0.0, rotblur=0.0, look=None):
        """anchor_src：精灵内归一化锚点（如脸中心）；anchor_dst：画面像素位置；scale：精灵宽 → 画面像素 的倍率。"""
        F, A, R = self.wind(t, wind_amp)
        # 调色匹配：压暗、去饱和一部分、偏冷
        lum = (F * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
        red = red_mask(F)[..., None] * keep_red                     # 保色遮罩：暗红内领、红穗、血保留饱和度
        sat = grade['sat'] * (1 - red) + 1.25 * red
        tint = np.array(grade['tint'], np.float32) * (1 - red) + np.array([1.08, 0.96, 0.96], np.float32) * red
        F = np.clip(lum + (F - lum) * sat, 0, 1) ** grade.get('gamma', 1.0) * grade['expo'] * tint + grade['lift']
        # 冷色 rim：轮廓环带 × 背光方向（法线 · 光向）
        gx = cv2.Sobel(A, cv2.CV_32F, 1, 0, ksize=5); gy = cv2.Sobel(A, cv2.CV_32F, 0, 1, ksize=5)
        n = np.sqrt(gx * gx + gy * gy) + 1e-4
        facing = np.clip(-(gx * rim['dir'][0] + gy * rim['dir'][1]) / n, 0, 1)
        rimm = (R * (0.25 + 0.75 * facing))[..., None] * A[..., None]
        F = F + rimm * np.array(rim['col'], np.float32) * rim['amt'] * 0.25
        if look:                                                   # 2026-11-09 全片整合：复用镜头的变体（剪影/水墨/纸/负片/投影）
            F, A = _look(F, A, rimm, rim, red, look)
        # 呼吸 + 2.5D 摆放（仿射：缩放/旋转/平移；源锚点 → 目标）
        s = scale * (1 + breathe * math.sin(2 * math.pi * t / 3.4))
        ax, ay = anchor_src[0] * self.w, anchor_src[1] * self.h
        M = cv2.getRotationMatrix2D((ax, ay), rot, s)
        M[0, 2] += anchor_dst[0] - ax; M[1, 2] += anchor_dst[1] - ay
        Fw = cv2.warpAffine(F, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        Aw = cv2.warpAffine(A, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        if mblur[0] or mblur[1]:                                   # 甩动时方向模糊（转头的动势）
            L = int(max(abs(mblur[0]), abs(mblur[1])))
            if L >= 2:
                k = np.zeros((2 * L + 1, 2 * L + 1), np.float32)
                cv2.line(k, (L - int(mblur[0] / 2), L - int(mblur[1] / 2)), (L + int(mblur[0] / 2), L + int(mblur[1] / 2)), 1.0, 1)
                k /= k.sum()
                Fw = cv2.filter2D(Fw * Aw[..., None], -1, k); Aw = cv2.filter2D(Aw, -1, k)
                Fw = Fw / np.clip(Aw[..., None], 1e-3, None)
        if shade:                                                  # 屏幕空间主光衰减：背光侧亮、朝镜头侧/胸口暗（主光偏暗）
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            r = np.clip((xx - shade[0]) / (shade[1] - shade[0]), 0, 1) * shade[2] + np.clip((yy - shade[3]) / (H - shade[3]), 0, 1) * shade[4]
            Fw = Fw * (1 - r)[..., None]
        if rotblur:                                                # 旋斩：绕锚点的角向模糊（几张旋转副本平均）
            acc_F = Fw * Aw[..., None]; acc_A = Aw.copy(); n = 5
            for i in range(1, n):
                Mr = cv2.getRotationMatrix2D(tuple(map(float, anchor_dst)), rotblur * i / n, 1.0)
                acc_F += cv2.warpAffine(Fw * Aw[..., None], Mr, (W, H)); acc_A += cv2.warpAffine(Aw, Mr, (W, H))
            Aw = acc_A / n; Fw = (acc_F / n) / np.clip(Aw[..., None], 1e-3, None)
        if defocus > 0.3:                                          # 景深虚化（前景刀在焦时人物在后）
            Fw = cv2.GaussianBlur(Fw * Aw[..., None], (0, 0), defocus); Aw = cv2.GaussianBlur(Aw, (0, 0), defocus)
            Fw = Fw / np.clip(Aw[..., None], 1e-3, None)
        if extra_A is not None: Aw = Aw * extra_A
        Aw = Aw * alpha
        # 光包裹：背景模糊光渗进人物边缘（去贴纸感）
        bgb = cv2.GaussianBlur(fr, (0, 0), 18)
        edge = np.clip(Aw - cv2.GaussianBlur(Aw, (0, 0), 6) * 0.0, 0, 1)
        inner = cv2.GaussianBlur(Aw, (0, 0), 10)
        wrap_m = (Aw * np.clip(1 - inner, 0, 1) * 2.0)[..., None] * wrap
        Fw = Fw + bgb * wrap_m
        a3 = Aw[..., None]
        return fr * (1 - a3) + Fw * a3, Aw


def _look(F, A, rimm, rim, red, look):
    lum = (F * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
    if look == 'sil':        # 背光剪影：几乎全黑 + 轮廓光
        F = F * 0.10 + rimm * np.array(rim['col'], np.float32) * rim['amt'] * 0.45
    elif look == 'ink':      # 宣纸水墨：灰阶墨色，暗红保留为朱色
        ink = np.clip(0.06 + 0.75 * np.clip(lum * 1.6, 0, 1) ** 0.9, 0, 1) * np.array([1.0, 0.96, 0.88], np.float32)
        F = ink * (1 - red) + red * np.array([0.62, 0.10, 0.07], np.float32)
        A = A * 0.94
    elif look == 'paper':    # 纸糊巨影：暖白半透，边缘透光
        F = np.array([0.92, 0.84, 0.66], np.float32) * (0.45 + 0.6 * lum) + rimm * 1.2
        A = A * 0.72
    elif look == 'neg':      # 负片世界
        F = np.clip(1.0 - F * 1.1, 0, 1)
    elif look == 'shadow':   # 烛光投影：纯暗影
        F = F * 0.0 + np.array([0.05, 0.03, 0.02], np.float32)
        A = A * 0.7
    return F, A


def red_mask(F):
    """按色相比例取暗红（与亮度无关）：r 明显高于 g/b，排除肤色、金、棕皮革。"""
    r = F[..., 0]; mx = np.maximum(F[..., 1], F[..., 2])
    ratio = (r - mx) / (r + 1e-3)
    return (_sstep(0.38, 0.62, ratio) * _sstep(0.03, 0.09, r)).astype(np.float32)


_CACHE = {}
def layer(path):
    if path not in _CACHE: _CACHE[path] = SpriteLayer(path)
    return _CACHE[path]
