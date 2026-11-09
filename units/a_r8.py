"""units/a_r8.py — A 组第八棒辅助（只被 units/sec_a_intro_verse1.py 使用）：
- Crater8：V17 凹坑重画 —— 受光崩口（断续的唇口高光 + 唇面倒角）、坑壁 60px 厚度（按坑壁法线做 Lambert 受光 + 往坑底的环境遮蔽 + 层理纹）、
  坑底投影、裂缝贯穿坑壁透暖光、碎石换不规则多边形（7–11 顶点、长短轴不等、各自色差 + 投影）。去掉旧版平涂浅灰内壁带。
- kneel_pan_fix：V10 kneel_pan 精灵 —— 臂/刀/腿围出的封闭灰底洞（抠图残底）按与 raw 灰底色距 + 连通域清掉。
- shear_beam：V09 天平横梁摆动（对已合成的预乘层做竖向剪切：梁按支点转、两盘整体平移、立柱不动）。
"""
import math
import numpy as np, cv2
from PIL import Image
import a_kit as A
import a_r6
import a_r7
import c1kit as K

W, H = 1920, 1080


class Crater8(a_r7.Crater):
    WALL = 60.0

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        seed = kw.get('seed', 17)
        r = np.random.default_rng(seed + 100)
        mb = (self.mask > 0.5).astype(np.uint8)
        dist = cv2.distanceTransform(mb, cv2.DIST_L2, 5).astype(np.float32)
        dist = cv2.GaussianBlur(dist, (0, 0), 2.0)
        self.wall = np.clip(dist / self.WALL, 0, 1)
        self.floor = np.clip((dist - self.WALL) / 6, 0, 1)
        gy, gx = np.gradient(dist)
        n = np.sqrt(gx ** 2 + gy ** 2) + 1e-4
        self.nx, self.ny = gx / n, gy / n                                    # 坑壁法线（指向坑内 = 坑壁面朝向）
        # 层理纹：沿等深线的横纹（坑壁是岩层被压断的断面）
        st = cv2.resize(A.tex(seed + 7, 256, 60, 4), (W, H)); st2 = cv2.resize(A.tex(seed + 8, 512, 120, 3), (W, H))
        # 第八棒核帧：等深线横纹读成「等高线/胶带」→ 改粗糙断口石质（高频噪声 + 少量断续台阶）
        ledge = (np.sin(dist * 0.35 + st * 9) > 0.93).astype(np.float32) * (st2 > 0.5)
        self.strata = (0.65 + 0.55 * st2 * st) * (1 - 0.35 * cv2.GaussianBlur(ledge, (0, 0), 1.0))
        # 唇口：坑外 0–14px 一圈倒角；用低频噪声把它打断（崩口处没有高光）
        out_d = cv2.distanceTransform((1 - mb).astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32)
        self.lip = np.clip(1 - out_d / 14, 0, 1) * (out_d > 0)
        oy, ox = np.gradient(cv2.GaussianBlur(out_d, (0, 0), 2.0)); on = np.sqrt(ox ** 2 + oy ** 2) + 1e-4
        self.ox, self.oy = ox / on, oy / on                                  # 坑外地面离坑方向
        brk = cv2.resize(A.tex(seed + 9, 256, 14, 3), (W, H))
        self.lipbreak = np.clip((brk - 0.42) * 5, 0, 1)
        # 碎石：不规则多边形
        self.rocks = []
        c = self.c
        for _ in range(38):
            ang = r.uniform(0, 2 * math.pi); rad = r.uniform(0.55, 0.95)
            px = c[0] + math.cos(ang) * 330 * rad * (1.2 + 0.4 * r.random())
            py = c[1] + math.sin(ang) * 280 * rad * (1.2 + 0.4 * r.random())
            s = r.uniform(5, 22) * (1.8 if r.random() < 0.12 else 1)
            k = int(r.integers(7, 12)); el = r.uniform(0.45, 1.0); rot = r.uniform(0, math.pi)
            pts = []
            for j in range(k):
                th = 2 * math.pi * j / k + r.uniform(-0.25, 0.25); rr = s * r.uniform(0.45, 1.0)
                x, y = math.cos(th) * rr, math.sin(th) * rr * el
                pts.append((x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)))
            self.rocks.append((px, py, np.array(pts, np.float32), ang, r.uniform(0.7, 1.25), r.uniform(-0.02, 0.02)))
        self.tex_s = cv2.resize(A.tex(seed + 11, 256, 40, 3), (W, H))

    def draw(self, fr, a, light=(-0.75, -0.65), heat=1.0, t=0.0):
        lx, ly = light                                                       # 光的来向（左上）
        m = self.mask; inside = m[..., None]; wall = self.wall
        st = 0.75 + 0.5 * self.tex_s
        # 1) 坑内整体：越深越暗（环境遮蔽）
        fr = fr * (1 - inside * (0.30 + 0.45 * wall[..., None]))
        # 2) 坑壁 Lambert：法线朝光（右下壁朝左上）亮，朝背（左上壁）暗；亮度从唇口向坑底衰减
        lam = np.clip(self.nx * lx + self.ny * ly, 0, 1)                 # 面朝光的程度
        band = (1 - self.floor) * m
        prof = (1 - wall) ** 1.6
        lit = band * lam * (0.45 + 0.55 * prof) * self.strata * st
        fr = fr * (1 - 0.5 * (band * lam)[..., None]) + (lit[..., None] * np.array([0.30, 0.29, 0.285], np.float32))
        fr = fr * (1 - (band * (1 - lam) * 0.35)[..., None])
        # 上亮下暗：迎光坑壁顶端崩口一线亮边（断续），坑壁脚与坑底交界一线暗缝
        crest = np.clip(1 - wall / 0.10, 0, 1) * m * lam * self.lipbreak
        fr = fr + cv2.GaussianBlur(crest, (0, 0), 1.2)[..., None] * np.array([0.45, 0.45, 0.48], np.float32)
        foot = np.clip(1 - np.abs(wall - 0.93) / 0.08, 0, 1) * m
        fr = fr * (1 - 0.55 * cv2.GaussianBlur(foot, (0, 0), 2.0)[..., None])
        # 坑底：去暖褐偏色（往石灰收），叠石面噪声
        fl3 = self.floor[..., None]
        g_ = fr.mean(-1, keepdims=True)
        fr = fr * (1 - 0.9 * fl3) + (g_ * np.array([0.96, 1.0, 1.06], np.float32) * (0.7 + 0.5 * self.tex_s[..., None])) * 0.75 * fl3
        # 3) 坑底投影：左上坑沿挡光，投在坑底（软边）
        sh_off = cv2.warpAffine(m, np.float32([[1, 0, -lx * 70], [0, 1, -ly * 70]]), (W, H))
        shadow = cv2.GaussianBlur(np.clip(m - sh_off, 0, 1) * self.floor, (0, 0), 6)
        fr = fr * (1 - 0.65 * shadow[..., None])
        # 4) 唇口：坑外一圈倒角 —— 朝光侧冷白湿边、断续（崩口没有高光），背光侧压暗
        lipl = self.lip * np.clip(-(self.ox * lx + self.oy * ly) + 0.15, 0, 1) * self.lipbreak
        fr = fr + cv2.GaussianBlur(lipl, (0, 0), 1.0)[..., None] * np.array([0.13, 0.14, 0.16], np.float32) * st[..., None]
        fr = fr * (1 - (self.lip * 0.35 * (1 - self.lipbreak))[..., None])
        # 坑外贴沿的接触暗（地面被压塌的下沉）
        ring = cv2.GaussianBlur(np.clip(cv2.dilate(m, np.ones((31, 31), np.uint8)) - m, 0, 1), (0, 0), 8)
        fr = fr * (1 - 0.25 * ring[..., None])
        # 5) 「正」凹刻（同旧版）
        if self.zm is not None:
            zs = np.clip(self.zm - cv2.warpAffine(self.zm, np.float32([[1, 0, -lx * 9], [0, 1, -ly * 9]]), (W, H)), 0, 1)
            zh = np.clip(self.zm - cv2.warpAffine(self.zm, np.float32([[1, 0, lx * 5], [0, 1, ly * 5]]), (W, H)), 0, 1)
            fr = fr * (1 - 0.35 * self.zm[..., None]) * (1 - 0.55 * zs[..., None]) + zh[..., None] * np.array([0.09, 0.09, 0.10], np.float32)
        # 6) 裂缝：暗缝 + 缝底暖光；进入坑壁的那一段更亮（热从坑里透出），并在坑沿处炸开一点暖晕
        prog = min(1.0, 0.35 + a / 0.35)
        warm = heat * (0.35 + 0.65 * math.exp(-a / 0.7)) * (0.88 + 0.12 * math.sin(t * 9))
        heatz = cv2.GaussianBlur(m, (0, 0), 60)
        for cp in self.cracks:
            cm = K.draw_crack((H, W), cp, 2.6, branches=2, seed=5, prog=prog)
            core = cv2.GaussianBlur(cm, (0, 0), 0.7)
            fr = fr * (1 - 0.9 * cm[..., None])
            boost = (0.6 + 1.6 * heatz)[..., None]
            fr = fr + (core * 0.9 + cv2.GaussianBlur(core, (0, 0), 4) * 0.4)[..., None] * np.array([1.0, 0.45, 0.15], np.float32) * warm * boost
        # 坑壁底部一线余热（裂缝在坑底汇合处）
        seam = np.clip(1 - np.abs(wall - 0.97) / 0.05, 0, 1) * m * (0.5 + 0.5 * self.lipbreak)
        fr = fr + cv2.GaussianBlur(seam, (0, 0), 2)[..., None] * np.array([1.0, 0.42, 0.14], np.float32) * 0.35 * warm
        # 7) 碎石
        fl = min(1.0, a / 0.25); e = 1 - (1 - fl) ** 3
        for (px, py, pts, ang, sc, hue) in self.rocks:
            off = (1 - e) * -50
            x = px + math.cos(ang) * off; y = py + math.sin(ang) * off
            P = (pts + (x, y)).astype(np.int32)
            x0, y0 = P.min(0) - 20; x1, y1 = P.max(0) + 20
            if x1 < 0 or y1 < 0 or x0 > W or y0 > H: continue
            x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(W, x1), min(H, y1)
            sub = np.zeros((y1 - y0, x1 - x0), np.float32)
            cv2.fillPoly(sub, [P - (x0, y0)], 1.0, cv2.LINE_AA)
            shd = cv2.GaussianBlur(np.roll(np.roll(sub, 5, 0), 6, 1), (0, 0), 3)
            hi = np.clip(sub - np.roll(np.roll(sub, 2, 0), 2, 1), 0, 1)
            gr = np.linspace(1.15, 0.7, sub.shape[0], dtype=np.float32)[:, None]
            reg = fr[y0:y1, x0:x1] * (1 - 0.55 * shd[..., None])
            col = np.array([0.16 + hue, 0.155, 0.15 - hue], np.float32) * sc
            sub_lo = np.clip(sub - np.roll(np.roll(sub, -3, 0), -3, 1), 0, 1)                   # 背光面（右下）
            reg = reg * (1 - sub[..., None]) + (sub * gr)[..., None] * col * (1 - 0.5 * sub_lo[..., None])
            reg = reg + hi[..., None] * np.array([0.20, 0.20, 0.22], np.float32) * sc
            fr[y0:y1, x0:x1] = reg
        return fr


def kneel_pan_fix():
    """V10 跪姿精灵：封闭灰底洞（臂、刀、腿之间）清掉 alpha。"""
    def b():
        p = a_r6.hair_clean('A/kneel_pan')
        F = np.asarray(Image.open(p).convert('RGBA')).astype(np.float32) / 255
        R = np.asarray(Image.open(A.GEN + 'A/kneel_pan_raw.png').convert('RGB').resize(F.shape[1::-1], Image.LANCZOS)).astype(np.float32) / 255
        g = np.median(np.concatenate([R[:24].reshape(-1, 3), R[:, -24:].reshape(-1, 3)]), 0)
        d = np.sqrt(((R - g) ** 2).sum(-1))
        sat = R.max(-1) - R.min(-1)
        bgish = ((d < 0.075) & (sat < 0.05) & (F[..., 3] > 0.3)).astype(np.uint8)
        bgish = cv2.morphologyEx(bgish, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        n, lab, stats, _ = cv2.connectedComponentsWithStats(bgish, 8)
        hole = np.zeros_like(bgish)
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] > 600: hole[lab == i] = 1
        hole = cv2.dilate(hole, np.ones((5, 5), np.uint8)).astype(np.float32)
        hole = cv2.GaussianBlur(hole, (0, 0), 1.2)
        a = F[..., 3] * (1 - hole)
        rgb = F[..., :3] * (0.6 + 0.4 * np.clip(a / np.maximum(F[..., 3], 1e-3), 0, 1)[..., None])
        return np.dstack([rgb, a])
    return a_r6._cached('kneel_pan_r8', b)


def shear_beam(P, Al, pivot, slope, beam_y1, pan_dy, col_half=70, fade=60):
    """P 预乘色 (H,W,3)，Al (H,W,1)。梁区 (y < beam_y1)：dy = slope·(x−px)；盘区：dy = ±pan_dy（左右各整体平移）；
    立柱 |x−px| < col_half 不动；两区之间按 y 过渡 fade px。"""
    px, py = pivot
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = xx - px
    beam = slope * dx
    side = np.tanh(dx / 40.0)
    pan = pan_dy * side * np.clip((np.abs(dx) - col_half) / 50, 0, 1)
    k = np.clip((yy - beam_y1) / fade, 0, 1)
    colm = np.clip((np.abs(dx) - col_half * 0.6) / 30, 0, 1)
    dy = (beam * (1 - k) + pan * k) * colm
    my = yy - dy
    P2 = cv2.remap(P, xx, my, cv2.INTER_LINEAR, borderValue=0)
    A2 = cv2.remap(Al[..., 0], xx, my, cv2.INTER_LINEAR, borderValue=0)[..., None]
    return P2, A2


# ---------------------------------------------------------------------------------------------
# 镜内机位运动（critic_A_r5 P0-1）：在镜头层（转场前、歌词前）做缓推 / 平移 / 摆动，起止两帧必有可见差异。
# spec = dict(z=(z0,z1), c=(cx,cy), d=(dx,dy) 终点平移px, rot=(r0,r1) 度, ease='io'|'out'|'lin', wob=(amp_deg, hz))
def inner_push(fr, u, t, spec):
    e = {'io': lambda x: x * x * (3 - 2 * x), 'out': lambda x: 1 - (1 - x) ** 3, 'lin': lambda x: x}[spec.get('ease', 'io')](min(1.0, max(0.0, u)))
    z0, z1 = spec.get('z', (1.0, 1.0)); z = z0 + (z1 - z0) * e
    cx, cy = spec.get('c', (960, 540)); dx, dy = spec.get('d', (0, 0))
    r0, r1 = spec.get('rot', (0.0, 0.0)); rot = r0 + (r1 - r0) * e
    wa, wh = spec.get('wob', (0.0, 0.0)); rot += wa * math.sin(2 * math.pi * wh * t)
    if abs(z - 1) < 1e-4 and abs(rot) < 1e-4 and dx == 0 and dy == 0: return fr
    M = cv2.getRotationMatrix2D((float(cx), float(cy)), float(rot), float(z))
    M[0, 2] += dx * e; M[1, 2] += dy * e
    return cv2.warpAffine(np.ascontiguousarray(fr, np.float32), M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def shake(t, t0, amp=14.0, tau=0.12, seed=0):
    a = t - t0
    if a < 0: return 0.0, 0.0
    k = amp * math.exp(-a / tau)
    return k * math.sin(a * 71 + seed), k * math.cos(a * 57 + 2 * seed)


_FEATH = None
_F2 = []
def _FEATH2():
    if not _F2:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.minimum.reduce([xx, W - 1 - xx, yy, H - 1 - yy])
        _F2.append(np.clip(d / 160.0, 0, 1) ** 1.5)
    return _F2[0]


def a_cleave8(A_, B_, p, angle=32.0, center=(960, 540), mode='open', col=(1.0, 0.35, 0.15)):
    """a_r7.a_cleave 的修正版（critic_A_r5 P1-6/7）：原版两块用「有效画面（黑边内）」作遮罩平移，
    一块往上走时它的下沿取自黑边外 → 遮罩为 0 → 漏出 B 的碎片（V12 入右半脸上的恶徒衣角）。
    这里遮罩按半平面无限延伸（REPLICATE），块移出画框的部分补黑（与黑边同色），碎片不再出现。"""
    global _FEATH
    import a_r7
    if p < 0.3: return a_r7.a_cleave(A_, B_, p, angle, center, mode, col)
    if _FEATH is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        _FEATH = np.clip(np.minimum.reduce([xx, W - 1 - xx, yy, H - 1 - yy]) / 80.0, 0, 1)
    th = math.radians(angle); dv = (math.cos(th), math.sin(th)); nv = (-dv[1], dv[0])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sd = (xx - center[0]) * nv[0] + (yy - center[1]) * nv[1]
    q = (p - 0.3) / 0.7; e = q ** 1.6
    sep, sl = (40 + 1300 * e, 120 * e) if mode == 'open' else (20 + 80 * e, 2400 * e)
    out = B_.copy()
    for sgn in (1, -1):
        tx = sgn * (nv[0] * sep + dv[0] * sl); ty = sgn * (nv[1] * sep + dv[1] * sl)
        M = np.float32([[1, 0, tx], [0, 1, ty]])
        half = cv2.warpAffine(A_ * _FEATH2()[..., None], M, (W, H), borderMode=cv2.BORDER_CONSTANT)   # 块的画框边柔和压黑（不硬切矩形），不漏 B
        mk = cv2.warpAffine(((sd > 0) if sgn > 0 else (sd <= 0)).astype(np.float32), M, (W, H), borderMode=cv2.BORDER_REPLICATE)
        mk = mk * (1 - max(0.0, (q - 0.65) / 0.35))
        edge = np.exp(-((sd - sgn * sep) / 3.0) ** 2) * mk
        out = out * (1 - mk[..., None]) + half * mk[..., None]
        out = out + edge[..., None] * np.array(col, np.float32) * 1.6 * (1 - q)
    return out
