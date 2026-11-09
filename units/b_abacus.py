"""units/b_abacus.py — B 组 · 「算盘」（第三棒，替换 V09–V11 的天平：A/C/D 三组都用了天平，撞概念）
「牺牲多少才算够」= 算：权力把人命当算珠拨。乌木框、黄铜包角、竹档、红木算珠（双锥体：上半受光、腰棱高光、下半暗）。
平面贴图 AW×AH 上排好框/梁/档/珠，再整张透视贴到画面（字刻在梁上，跟着透视走）。
Abacus(seed).flat(counts, upper, t) -> (rgb, alpha)  counts[i] ∈ [0,5] 浮点：第 i 档被拨上去的下珠数
"""
import math
import numpy as np, cv2

AW, AH = 2600, 1500
M0 = 96                        # 框宽
BEAM_Y, BEAM_H = 470, 74
NR = 13
BW, BH = 168, 100              # 珠宽高


def _noise(h, w, seed, sc):
    r = np.random.default_rng(seed)
    a = r.random((max(2, h // sc), max(2, w // sc))).astype(np.float32)
    return cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def wood(h, w, seed, base=(0.12, 0.055, 0.03), horiz=True):
    g = _noise(h, w, seed, 3)
    if horiz:
        g = cv2.GaussianBlur(g, (0, 0), sigmaX=40, sigmaY=0.8)
    else:
        g = cv2.GaussianBlur(g, (0, 0), sigmaX=0.8, sigmaY=40)
    g = (g - g.min()) / (np.ptp(g) + 1e-6)
    rings = 0.5 + 0.5 * np.sin(g * 40.0)
    n = _noise(h, w, seed + 1, 60)
    v = 0.70 + 0.35 * rings * 0.6 + 0.25 * n
    return np.asarray(base, np.float32)[None, None] * v[..., None]


def bead_sprite(seed=0, tone=(0.30, 0.10, 0.05)):
    """双锥算珠（正视）：RGBA"""
    w, h = BW + 8, BH + 8
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = (xx - w / 2) / (BW / 2); v = (yy - h / 2) / (BH / 2)
    # 轮廓：腰部最宽、上下收成圆角平顶
    half = 1.0 - 0.42 * np.abs(v) ** 1.25
    inside = (np.abs(u) < half) & (np.abs(v) < 1.0)
    a = cv2.GaussianBlur(inside.astype(np.float32), (0, 0), 1.0)
    # 法线近似：上锥面朝上、下锥面朝下；横向按 u/half 弯曲
    s = np.clip(u / np.maximum(half, 1e-3), -1, 1)
    ny = np.where(v < 0, -0.55, 0.55) * np.ones_like(v)
    nx = s * 0.8
    nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0.05, 1))
    L = np.array([-0.35, -0.75, 0.56]); L = L / np.linalg.norm(L)
    diff = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    H_ = np.array([-0.2, -0.5, 1.0]); H_ = H_ / np.linalg.norm(H_)
    spec = np.clip(nx * H_[0] + ny * H_[1] + nz * H_[2], 0, 1) ** 30
    grain = wood(h, w, seed, base=(1, 1, 1), horiz=True)[..., 0]
    base = np.asarray(tone, np.float32)[None, None] * (0.75 + 0.4 * grain[..., None])
    col = base * (0.22 + 1.05 * diff[..., None]) + spec[..., None] * np.array([1.0, 0.85, 0.7], np.float32) * 0.55
    ridge = np.exp(-(v / 0.05) ** 2) * (np.abs(s) < 0.92)
    col = col + ridge[..., None] * np.array([0.55, 0.32, 0.18], np.float32) * 0.6
    rim = np.clip(np.abs(s) - 0.82, 0, 1) * 4
    col = col * (1 - 0.5 * rim[..., None])
    hole = np.exp(-((u / 0.08) ** 2 + ((np.abs(v) - 0.95) / 0.08) ** 2))
    col = col * (1 - 0.7 * hole[..., None])
    return col.astype(np.float32), a.astype(np.float32)


class Abacus:
    def __init__(self, seed=0, beam_h=BEAM_H, corners=False):
        self.seed = seed
        self.bh = beam_h
        r = np.random.default_rng(seed)
        rgb = np.zeros((AH, AW, 3), np.float32); al = np.zeros((AH, AW), np.float32)
        # 档（竹档：细竹杆，带一道高光）
        self.rx = [M0 + (AW - 2 * M0) * (i + 0.5) / NR for i in range(NR)]
        for x in self.rx:
            x0 = int(x - 7); x1 = int(x + 7)
            rgb[:, x0:x1] = np.array([0.36, 0.28, 0.14], np.float32) * np.linspace(0.5, 1.2, x1 - x0)[None, :, None] ** 1.5
            rgb[:, int(x - 2):int(x)] += 0.15
            al[:, x0:x1] = 1
        # 框 + 梁（乌木，倒角）
        def bar(x0, y0, x1, y1, horiz, sd):
            wd = wood(y1 - y0, x1 - x0, sd, horiz=horiz)
            hh = y1 - y0; ww = x1 - x0
            if horiz:
                prof = np.clip(np.linspace(0, 1, hh), 0, 1)[:, None]
                shade = 1.25 - 0.7 * prof + 0.5 * np.exp(-((np.arange(hh)[:, None] - 4) / 3.0) ** 2)
            else:
                prof = np.clip(np.linspace(0, 1, ww), 0, 1)[None, :]
                shade = 1.15 - 0.55 * prof + 0.45 * np.exp(-((np.arange(ww)[None, :] - 4) / 3.0) ** 2)
            rgb[y0:y1, x0:x1] = wd * shade[..., None]; al[y0:y1, x0:x1] = 1
        bar(0, 0, AW, M0, True, seed + 10); bar(0, AH - M0, AW, AH, True, seed + 11)
        bar(0, 0, M0, AH, False, seed + 12); bar(AW - M0, 0, AW, AH, False, seed + 13)
        bar(M0, BEAM_Y, AW - M0, BEAM_Y + beam_h, True, seed + 14)
        # 梁上定位点（铜钉）
        for i in range(0, NR, 3):
            cx, cy = int(self.rx[i]), BEAM_Y + beam_h // 2
            cv2.circle(rgb, (cx, cy), 9, (0.55, 0.42, 0.2), -1, cv2.LINE_AA)
            cv2.circle(rgb, (cx - 3, cy - 3), 3, (1.0, 0.9, 0.7), -1, cv2.LINE_AA)
        # 黄铜包角
        for (cx, cy) in (((0, 0), (AW, 0), (0, AH), (AW, AH)) if corners else ()):
            m = np.zeros((AH, AW), np.uint8)
            cv2.rectangle(m, (cx - 170, cy - 170), (cx + 170, cy + 170), 255, -1)
            mm = (m > 0) & (al > 0) & ~((np.arange(AW)[None, :] > M0) & (np.arange(AW)[None, :] < AW - M0) & (np.arange(AH)[:, None] > M0) & (np.arange(AH)[:, None] < AH - M0))
            g = _noise(AH, AW, seed + 20, 30)
            rgb[mm] = (np.array([0.50, 0.36, 0.15], np.float32) * (0.7 + 0.5 * g[mm][:, None]))
        self.base, self.alpha = rgb, al
        self.bead = [bead_sprite(seed + 30 + k, tone=(0.12 + 0.025 * k, 0.040, 0.026)) for k in range(3)]

    def bead_pos(self, i, counts, upper):
        """返回第 i 档 7 颗珠的中心 y 列表（上 2 + 下 5）"""
        ys = []
        top0 = M0; bot0 = BEAM_Y
        u = upper[i]                                      # 0..1：上珠被拨下靠梁
        ys.append(top0 + BH * 0.5 + (bot0 - top0 - 2 * BH) * u)
        ys.append(top0 + BH * 1.5 + (bot0 - top0 - 2 * BH) * u)
        c = counts[i]
        lt = BEAM_Y + self.bh; lb = AH - M0
        gap = (lb - lt) - 5 * BH
        for k in range(5):
            # 被拨上去的珠（k < c）贴梁；其余在底部
            q = np.clip(c - k, 0, 1)
            q = q * q * (3 - 2 * q)
            y_up = lt + BH * (k + 0.5)
            y_dn = lt + gap + BH * (k + 0.5)
            ys.append(y_dn + (y_up - y_dn) * q)
        return ys

    def flat(self, counts, upper=None, glow=None):
        upper = upper if upper is not None else [0.0] * NR
        rgb = self.base.copy(); al = self.alpha.copy()
        for i, x in enumerate(self.rx):
            ys = self.bead_pos(i, counts, upper)
            for k, y in enumerate(ys):
                C, A = self.bead[(i * 7 + k) % 3]
                h, w = A.shape
                x0, y0 = int(x - w / 2), int(y - h / 2)
                if y0 < 0 or y0 + h > AH: continue
                reg = rgb[y0:y0 + h, x0:x0 + w]
                # 接触阴影
                rgb[y0:y0 + h, x0:x0 + w] = reg * (1 - A[..., None]) + C * A[..., None]
                al[y0:y0 + h, x0:x0 + w] = np.maximum(al[y0:y0 + h, x0:x0 + w], A)
                if glow is not None and glow[i] > 0 and k >= 2:
                    rgb[y0:y0 + h, x0:x0 + w] += (A * min(1.0, glow[i]))[..., None] * np.array([0.9, 0.55, 0.2], np.float32) * 0.28
        return rgb, al
