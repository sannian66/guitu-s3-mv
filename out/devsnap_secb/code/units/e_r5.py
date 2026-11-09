"""units/e_r5.py — E 组第五棒辅助：有质感的前景遮挡转场（刀身掠镜 / 雾墙）。"""
import math
import numpy as np, cv2
import c1kit as K
from e_kit import W, H, sstep, c01, eio
import os
LYRIC_UNI = os.environ.get('LYRIC_UNI', '0') == '1'   # [lyric-uni] 全片统一字幕层开关

_TEX = {}
def _tex(seed, h, w, base):
    k = (seed, h, w, base)
    if k not in _TEX: _TEX[k] = K.fbm(h, w, seed, base=base, octaves=5).astype(np.float32)
    return _TEX[k]


def _mblur(img, dx, dy=0.0):
    """方向运动模糊（线核）。"""
    L = int(max(abs(dx), abs(dy)))
    if L < 2: return img
    k = np.zeros((2 * L + 1, 2 * L + 1), np.float32)
    cv2.line(k, (L - int(dx / 2), L - int(dy / 2)), (L + int(dx / 2), L + int(dy / 2)), 1.0, 1)
    k /= k.sum()
    return cv2.filter2D(img, -1, k)


def blade_sweep(A, B, p, direction=1, angle=62.0, width=520, warm=(1.0, 0.82, 0.55)):
    """近景刀身掠过镜头（右上→左下斜贯全屏、强运动模糊）：钢面拉丝纹 + 脊线暗 + 刃口一道暖高光 + 刀身投到画面上的暗影；
    A→B 的切换线藏在刀身最宽处。"""
    h2, w2 = H // 2, W // 2
    yy, xx = np.mgrid[0:h2, 0:w2].astype(np.float32)
    e = eio(c01(p))
    a = math.radians(angle)
    nx, ny = math.sin(a), -math.cos(a)                     # 刀身横截方向（法线）
    span = (w2 + width) * 1.15
    c = -span / 2 + span * e if direction > 0 else span / 2 - span * e
    s = (xx - w2 / 2) * nx + (yy - h2 / 2) * ny - c        # 到刀身中线的有符号距离（半分辨率 px）
    hw = width / 4
    q = s / hw                                             # -1..1 在刀身内
    body = sstep(1.0, 0.94, np.abs(q))
    along = (xx - w2 / 2) * ny - (yy - h2 / 2) * nx
    brush = _tex(5101, h2, w2, 3)
    streak = 0.5 + 0.5 * np.sin(along * 0.0 + q * 40 + brush * 9)
    steel = 0.10 + 0.22 * (1 - np.abs(q)) ** 2 + 0.08 * streak + 0.10 * (brush - 0.5)
    col = steel[..., None] * np.array([0.82, 0.86, 0.95], np.float32)
    spine = np.exp(-((q + 0.15) / 0.06) ** 2)              # 血槽/脊线：暗
    col = col * (1 - 0.6 * spine[..., None])
    edge = np.exp(-((q - 0.92) / 0.03) ** 2)               # 刃口：暖白高光
    col = col + edge[..., None] * np.asarray(warm, np.float32) * 2.2
    sheen = np.exp(-((along - (-600 + 1400 * e)) / 160) ** 2) * body          # 沿刀身滑过的反光
    col = col + sheen[..., None] * np.array([1.0, 0.9, 0.75], np.float32) * 0.5
    shadow = np.exp(-np.clip(np.abs(q) - 1, 0, None) / 0.8) * 0.55            # 刀身投在画面上的暗影
    up = lambda m: cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
    sw = up(s); body_f = up(body); col_f = up(col); sh_f = up(shadow)
    v = 70 * direction
    col_f = _mblur(col_f, v * nx, v * ny); body_f = _mblur(body_f, v * nx, v * ny)
    base = np.where((sw < 0)[..., None], B, A) if direction > 0 else np.where((sw > 0)[..., None], B, A)
    base = base * (1 - sh_f[..., None] * (1 - body_f[..., None]))
    return base * (1 - body_f[..., None]) + col_f * body_f[..., None]


def fog_wall(A, B, p, direction=-1, col=(0.86, 0.80, 0.70), dark=(0.05, 0.05, 0.06)):
    """一堵贴地翻滚的晨雾墙横扫过镜（右→左）：前缘羽化、内部有体积明暗、顶部受晨光偏暖、强横向运动模糊；切换藏在雾最浓处。"""
    h2, w2 = H // 2, W // 2
    yy, xx = np.mgrid[0:h2, 0:w2].astype(np.float32)
    e = eio(c01(p))
    span = w2 * 2.6
    c = (w2 * 1.8 - span * e) if direction < 0 else (-w2 * 0.8 + span * e)
    n1 = _tex(5201, h2, w2 * 2, 4); n2 = _tex(5202, h2, w2 * 2, 14)
    off = int((e * 260) % w2)
    N = (0.65 * n1[:, off:off + w2] + 0.35 * n2[:, off:off + w2])
    d = (xx - c) * (-direction)                               # >0 在雾墙后面（已过）
    core = w2 * 0.42
    dens = sstep(-core - 120, -core + 60, d + (N - 0.5) * 260) * sstep(core + 120, core - 60, d + (N - 0.5) * 260)
    dens = np.clip(dens * (0.8 + 0.5 * N) + 0.25 * dens, 0, 1)
    light = np.clip(1.15 - yy / h2 * 0.9, 0, 1) * (0.7 + 0.6 * N)
    fogc = np.asarray(dark, np.float32) + (np.asarray(col, np.float32) - np.asarray(dark, np.float32)) * light[..., None]
    up = lambda m: cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
    D = _mblur(up(dens), 60, 0); F = _mblur(up(fogc), 60, 0)
    sw = up(d)
    base = np.where((sw > 0)[..., None], B, A)
    return base * (1 - D[..., None]) + F * D[..., None]


def dawn_warm(fr, amt=0.5, hi=(1.10, 0.98, 0.80), lo=(0.96, 0.98, 1.04)):
    """破晓余温：高光偏淡金、暗部保留一点冷（P2：E31–E33 不再倒回长夜的冷灰）。"""
    L = np.clip(fr.mean(-1, keepdims=True), 0, 1)
    w = L ** 0.8
    tint = np.asarray(lo, np.float32) * (1 - w) + np.asarray(hi, np.float32) * w
    return fr * (1 + (tint - 1) * amt)


# ------------------------------------------------------------------ 第五棒：副句去模板化
import e_r3 as _R3


class SubD(_R3.Sub):
    """副句（第五棒）：不再钉死在下三分之一 —— 跟着画面漂（风向：left 档向左上、right 档向右上、center 上浮），
    逐字带一点错位下落感；暗衬变淡、句首小朱印去掉（只在 seal=True 时保留），读起来不像卡拉 OK 条。"""
    def __init__(self, text, times, side='right', t_out=None, drift=None, seal=False, **kw):
        super().__init__(text, times, side, t_out, **kw)
        if drift is None:
            drift = {'left': (-30, -14), 'right': (30, -14), 'center': (0, -20)}.get(side, (0, -16)) if isinstance(side, str) else (0, -16)
        self.dv = drift; self.seal_on = seal

    def draw(self, fr, t, dx=0.0, dy=0.0):
        v = self.vis(t)
        if v <= 0: return fr
        if LYRIC_UNI: return fr               # [lyric-uni] 副句的暗衬 + 朱印一起关（否则留一个空底块）
        q = t - (self.t0 - 0.25)
        dx = dx + self.dv[0] * q + 4 * math.sin(q * 2.3); dy = dy + self.dv[1] * q
        x0, y0, x1, y1 = self.box
        fr = _R3.plate(fr, x0 + dx, y0 + dy, x1 + dx, y1 + dy, 0.32 * v, feather=50)
        if self.seal_on:
            sx, sy = self.seal; s = 11
            cv2.rectangle(fr, (int(sx - s + dx), int(sy - s + dy)), (int(sx + s + dx), int(sy + s + dy)),
                          tuple(float(c * v) for c in _R3.REDT), -1, cv2.LINE_AA)
        return self.l.draw(fr, t, dx=dx, dy=dy)
