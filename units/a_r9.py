"""A 组第九棒辅助（critic_A_r6）：前景焦外光斑、刀身扫光、焦点转移工具、V17 坑底可读「正」、崩落石块。"""
import math
import numpy as np, cv2

W, H = 1920, 1080


def fg_bokeh(fr, t, t0, seed=0, n=6, col=(1.0, 0.5, 0.2), vel=(-900, -200), size=(30, 70), amt=0.5):
    """前景焦外光斑：n 颗大而虚的光点以 vel(px/s) 掠过镜头（比场景快很多 → 读作离镜头很近）。"""
    r = np.random.default_rng(seed)
    q = 4
    L = np.zeros((H // q, W // q), np.float32)
    dt = t - t0
    for i in range(n):
        x0 = r.uniform(200, 2600); y0 = r.uniform(200, 1300); s = r.uniform(*size); sp = r.uniform(0.7, 1.3)
        x = x0 + vel[0] * sp * dt; y = y0 + vel[1] * sp * dt
        x = (x + 300) % 2700 - 300
        fl = 0.7 + 0.3 * math.sin(t * 7 + i)
        cv2.circle(L, (int(x / q), int(y / q)), max(2, int(s / q)), fl, -1, cv2.LINE_AA)
    L = cv2.GaussianBlur(L, (0, 0), 3)
    L = cv2.resize(L, (W, H))[..., None]
    return fr + L * np.asarray(col, np.float32) * amt


def blade_sheen(fr, p0, p1, u, width=40, amt=1.4, col=(0.85, 0.92, 1.0), length=220):
    """沿刀身 p0→p1 的一道扫光（u∈[0,1] 扫光中心位置），带十字星芒。"""
    if not (-0.1 <= u <= 1.1): return fr
    q = 2
    L = np.zeros((H // q, W // q), np.float32)
    c = np.array(p0, np.float32) + (np.array(p1, np.float32) - p0) * u
    d = np.array(p1, np.float32) - p0; d /= np.linalg.norm(d) + 1e-6
    a = c - d * length / 2; b = c + d * length / 2
    cv2.line(L, tuple((a / q).astype(int)), tuple((b / q).astype(int)), 1.0, max(1, width // (2 * q)), cv2.LINE_AA)
    L = cv2.GaussianBlur(L, (0, 0), width / q / 2.5)
    st = np.zeros_like(L)
    cv2.line(st, (int(c[0] / q) - 160, int(c[1] / q)), (int(c[0] / q) + 160, int(c[1] / q)), 1.0, 1, cv2.LINE_AA)
    cv2.line(st, (int(c[0] / q), int(c[1] / q) - 60), (int(c[0] / q), int(c[1] / q) + 60), 1.0, 1, cv2.LINE_AA)
    st = cv2.GaussianBlur(st, (0, 0), 1.5) * 0.8
    g = np.zeros_like(L); cv2.circle(g, (int(c[0] / q), int(c[1] / q)), 8, 1.0, -1); g = cv2.GaussianBlur(g, (0, 0), 14) * 2.0
    T = cv2.resize(L + st + g, (W, H))[..., None]
    return fr + T * np.asarray(col, np.float32) * amt
