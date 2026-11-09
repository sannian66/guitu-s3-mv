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
import sk as K

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
        st = cv2.resize(A.tex(seed + 7, 256, 60, 4), (W, H))
        self.strata = 0.7 + 0.6 * (np.sin(dist * 0.9 + st * 6) * 0.5 + 0.5) * st
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
        lit = band * lam * prof * self.strata * st
        fr = fr + (lit[..., None] * np.array([0.20, 0.19, 0.185], np.float32))
        fr = fr * (1 - (band * (1 - lam) * 0.35)[..., None])
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
            col = np.array([0.10 + hue, 0.097, 0.092 - hue], np.float32) * sc
            reg = reg * (1 - sub[..., None]) + (sub * gr)[..., None] * col
            reg = reg + hi[..., None] * np.array([0.16, 0.16, 0.18], np.float32) * sc
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
