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


# ---------------------------------------------------------------- V17 第九棒坑：崩角 + 可读阴刻「正」+ 大小不一带投影的崩落石块
import sys as _sys
import a_kit as A
import a_r7, a_r8
import typo as T


class _Corner(a_r7.Crater):
    """在旧坑遮罩上把四角咬掉大块（崩角），坑不再是规整矩形。"""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        c = kw.get('c', (960, 520)); size = kw.get('size', (600, 520)); rot = kw.get('rot', -4.0)
        r = np.random.default_rng(kw.get('seed', 17) + 300)
        box = cv2.boxPoints((c, size, rot)).astype(np.float32)
        m = (self.mask > 0.5).astype(np.float32)
        ctr = np.array(c, np.float32)
        for i, p in enumerate(box):
            d = p - ctr; d /= np.linalg.norm(d)
            for j in range(2 + (i % 2)):                                       # 每角 2–3 块不规则崩口（向外）
                q = p + d * r.uniform(-10, 40) + r.normal(0, 25, 2)
                k = int(r.integers(6, 10)); R0 = r.uniform(40, 95)
                pts = [q + np.array([math.cos(2 * math.pi * s / k + r.uniform(-.3, .3)), math.sin(2 * math.pi * s / k + r.uniform(-.3, .3))]) * R0 * r.uniform(0.5, 1.0) for s in range(k)]
                cv2.fillPoly(m, [np.array(pts, np.int32)], 1.0, cv2.LINE_AA)
        # 边上 3 处小崩口
        for _ in range(4):
            i = int(r.integers(0, 4)); u = r.uniform(0.25, 0.75); p = box[i] + (box[(i + 1) % 4] - box[i]) * u
            d = p - ctr; d /= np.linalg.norm(d)
            cv2.circle(m, tuple((p + d * 12).astype(int)), int(r.uniform(22, 40)), 1.0, -1, cv2.LINE_AA)
        nz = cv2.resize(A.tex(kw.get('seed', 17) + 5, 256, 30, 3), (W, H))
        self.mask = np.clip((cv2.GaussianBlur(m, (0, 0), 1.5) - 0.5 + (nz - 0.5) * 0.25) * 6 + 0.5, 0, 1)


class Crater9(a_r8.Crater8, _Corner):
    def __init__(self, *a, zsize9=360, **kw):
        kw['zheng'] = False
        super().__init__(*a, **kw)
        c = kw.get('c', (960, 520)); seed = kw.get('seed', 17)
        Lz = T.Layer(); T.place(Lz, '正', c[0] + 8, c[1] + 18, zsize9, 'white', 'kai', texture=False)
        z = cv2.dilate(Lz.A, np.ones((5, 5), np.uint8))                           # 笔画加粗一点（凿刻宽度）
        self.z9 = cv2.GaussianBlur(z, (0, 0), 1.0) * self.floor
        self.zm = None
        # 崩落石块：幂律大小（少数大块 60–110px，多数 8–30px），集中在坑沿外 0–160px，少量落进坑底
        r = np.random.default_rng(seed + 500)
        mb = (self.mask > 0.5).astype(np.uint8)
        out_d = cv2.distanceTransform(1 - mb, cv2.DIST_L2, 5)
        cand = np.argwhere((out_d > 4) & (out_d < 170))
        cand_in = np.argwhere(self.floor > 0.5)
        self.rocks9 = []
        for n in range(64):
            big = n < 7
            if n < 52:
                yx = cand[r.integers(len(cand))]
                dd = out_d[yx[0], yx[1]]
                if r.random() > math.exp(-dd / 70) and not big: continue           # 越靠坑沿越密
            else:
                yx = cand_in[r.integers(len(cand_in))]
            s = r.uniform(55, 105) if big else 8 + 28 * r.random() ** 2.2
            k = int(r.integers(5, 9)); rot = r.uniform(0, math.pi); el = r.uniform(0.5, 0.95)
            pts = []
            for j in range(k):
                th = 2 * math.pi * j / k + r.uniform(-0.3, 0.3); rr = s * r.uniform(0.55, 1.0)
                x, y = math.cos(th) * rr, math.sin(th) * rr * el
                pts.append((x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)))
            ang = math.atan2(yx[0] - c[1], yx[1] - c[0])
            self.rocks9.append((float(yx[1]), float(yx[0]), np.array(pts, np.float32), s, ang, r.uniform(0.75, 1.2), n >= 52))
        self.rocks9.sort(key=lambda q: q[1])
        self.tex9 = cv2.resize(A.tex(seed + 21, 256, 24, 4), (W, H))

    def draw(self, fr, a, light=(-0.75, -0.65), heat=1.0, t=0.0):
        rk = self.rocks; self.rocks = []
        fr = super().draw(fr, a, light=light, heat=heat, t=t)
        self.rocks = rk
        lx, ly = light
        fl = self.floor[..., None]
        # 坑底：冷灰石面（去褐），比坑壁暗但留出中间调，给阴刻对比留空间
        stone = (0.75 + 0.5 * self.tex9)[..., None]
        base = np.array([0.060, 0.064, 0.072], np.float32) * stone
        fr = fr * (1 - 0.75 * fl) + base * 0.75 * fl
        # 坑底积雨薄光：左上天光在湿坑底的一片冷反光（被左上坑沿投影切掉一角）
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        cx, cy = self.c
        sheen = np.exp(-(((xx - cx - 60) / 300) ** 2 + ((yy - cy - 40) / 220) ** 2))
        sh_off = cv2.warpAffine(self.mask, np.float32([[1, 0, -lx * 80], [0, 1, -ly * 80]]), (W, H))
        shade = cv2.GaussianBlur(np.clip(self.mask - sh_off, 0, 1), (0, 0), 8)
        fr = fr + (sheen * self.floor * (1 - shade))[..., None] * np.array([0.05, 0.058, 0.07], np.float32)
        # 阴刻「正」：槽底深暗（积水），背光槽壁（左上）黑，迎光槽壁（右下）一线亮边；槽口外沿再一线细高光
        z = self.z9; d = 7
        litw = np.clip(z - cv2.warpAffine(z, np.float32([[1, 0, lx * d], [0, 1, ly * d]]), (W, H)), 0, 1)      # 右下槽壁
        shdw = np.clip(z - cv2.warpAffine(z, np.float32([[1, 0, -lx * d * 1.6], [0, 1, -ly * d * 1.6]]), (W, H)), 0, 1)
        outer = np.clip(cv2.warpAffine(z, np.float32([[1, 0, lx * 3], [0, 1, ly * 3]]), (W, H)) - z, 0, 1)       # 槽口左上外沿（受光棱）
        z3 = z[..., None]
        fr = fr * (1 - 0.82 * z3)                                                      # 槽底压暗
        fr = fr + z3 * np.array([0.006, 0.008, 0.012], np.float32)
        fr = fr * (1 - 0.6 * shdw[..., None])
        fr = fr + cv2.GaussianBlur(litw, (0, 0), 0.8)[..., None] * np.array([0.30, 0.31, 0.33], np.float32) * (0.85 + 0.3 * self.tex9[..., None])
        fr = fr + cv2.GaussianBlur(outer, (0, 0), 0.7)[..., None] * np.array([0.16, 0.17, 0.19], np.float32)
        # 槽中积水的一线冷反光（沿槽底，低频断续）
        wet = z * np.clip((self.tex9 - 0.55) * 4, 0, 1) * (1 - shade)
        fr = fr + cv2.GaussianBlur(wet, (0, 0), 2)[..., None] * np.array([0.05, 0.06, 0.08], np.float32)
        # 崩落石块：落定动画（从坑中心方向飞出后落定），投影朝右下、长度随石块大小
        fl_ = min(1.0, a / 0.3); e = 1 - (1 - fl_) ** 3
        for (px, py, pts, s, ang, sc, inpit) in self.rocks9:
            off = (1 - e) * -(60 + s)
            x = px + math.cos(ang) * off; y = py + math.sin(ang) * off
            P = (pts + (x, y)).astype(np.int32)
            pad = int(s * 0.6) + 12
            x0, y0 = P.min(0) - pad; x1, y1 = P.max(0) + pad
            if x1 < 0 or y1 < 0 or x0 > W or y0 > H: continue
            x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(W, x1), min(H, y1)
            sub = np.zeros((y1 - y0, x1 - x0), np.float32)
            cv2.fillPoly(sub, [P - (x0, y0)], 1.0, cv2.LINE_AA)
            so = 0.35 * s + 3
            shd = cv2.GaussianBlur(cv2.warpAffine(sub, np.float32([[1, 0, -lx * so], [0, 1, -ly * so]]), (sub.shape[1], sub.shape[0])), (0, 0), 1.5 + s * 0.06)
            hi = np.clip(sub - cv2.warpAffine(sub, np.float32([[1, 0, -lx * 2.5], [0, 1, -ly * 2.5]]), (sub.shape[1], sub.shape[0])), 0, 1)
            lo = np.clip(sub - cv2.warpAffine(sub, np.float32([[1, 0, lx * max(3, s * 0.18)], [0, 1, ly * max(3, s * 0.18)]]), (sub.shape[1], sub.shape[0])), 0, 1)
            reg = fr[y0:y1, x0:x1] * (1 - 0.7 * np.clip(shd - sub, 0, 1)[..., None])
            tx = self.tex9[y0:y1, x0:x1]
            col = np.array([0.10, 0.098, 0.096], np.float32) * sc * (0.7 + 0.6 * tx[..., None])
            if inpit: col = col * 0.7
            reg = reg * (1 - sub[..., None]) + sub[..., None] * col * (1 - 0.55 * lo[..., None])
            reg = reg + cv2.GaussianBlur(hi, (0, 0), 0.8)[..., None] * np.array([0.34, 0.34, 0.37], np.float32) * sc
            fr[y0:y1, x0:x1] = reg
        return fr
