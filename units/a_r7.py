"""units/a_r7.py — A 组第七棒辅助（只被 units/sec_a_intro_verse1.py 使用）。
- flagstones(): 雨夜不规则石板地（Voronoi 石块 + 缝 + 积水）
- Crater: 巨印压出的石板真凹坑（崩口坑沿、内壁厚度/投影、碎石、裂缝透暖光；坑底「正」只靠侧光阴影读出，不着色、无框）
- tsh_seal_noface(): 太上皇握玺精灵去掉后景那张脸（只留手 + 玺 + 袖）
- a_cleave(): 一条斩线把 A 一分为二，两半各自离开，露出 B（A/B 各只出现一次，不复制、不倒置）
- candle_screen(): 殿内烛火 + 屏风虚焦后景"""
import math
import numpy as np, cv2
from PIL import Image
import a_kit as A
import typo as T
import c1kit as K
import a_r6 as R6

W, H = 1920, 1080


def _cellnoise(seed, n_pts, w=W, h=H):
    """Voronoi：返回 (边距场 d2-d1, 块 id)。"""
    from scipy.spatial import cKDTree
    r = np.random.default_rng(seed)
    pts = np.c_[r.uniform(-100, w + 100, n_pts), r.uniform(-100, h + 100, n_pts)]
    yy, xx = np.mgrid[0:h // 2, 0:w // 2].astype(np.float32) * 2
    q = np.c_[xx.ravel(), yy.ravel()]
    # 缝要不规则：坐标先扰动
    nz = cv2.resize(A.tex(seed + 3, 256, 6, 3), (w // 2, h // 2)).ravel()
    q = q + (nz[:, None] - 0.5) * 60
    d, i = cKDTree(pts).query(q, k=2)
    edge = (d[:, 1] - d[:, 0]).reshape(h // 2, w // 2)
    return cv2.resize(edge, (w, h)), cv2.resize(i[:, 0].reshape(h // 2, w // 2).astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)


_FS = {}
def flagstones(seed=7, n=60, base=(0.075, 0.072, 0.07)):
    """不规则大石板（俯拍）：返回 (rgb, wet) —— wet = 积水遮罩（反光用）。"""
    if seed in _FS: return _FS[seed]
    edge, cid = _cellnoise(seed, n)
    r = np.random.default_rng(seed)
    tone = r.uniform(0.75, 1.15, int(cid.max()) + 2)[cid.astype(int)]
    grain = 0.78 + 0.45 * cv2.resize(A.tex(seed + 11, 512, 10, 5), (W, H)) + 0.25 * (cv2.resize(A.tex(seed + 12, 512, 60, 3), (W, H)) - 0.5)
    seam = np.clip(1 - edge / 9, 0, 1)                                       # 石缝（宽 ~7px，暗）
    bevel = np.clip(1 - np.abs(edge - 12) / 4, 0, 1) * 0.22                 # 缝边微倒角亮
    v = tone * grain * (1 - 0.85 * seam) + bevel
    wet = np.clip((cv2.resize(A.tex(seed + 21, 256, 3, 4), (W, H)) - 0.55) * 6, 0, 1)
    wet = np.maximum(wet, seam * 0.9)                                        # 缝里积水
    rgb = v[..., None] * np.array(base, np.float32)
    rgb = rgb * (1 - 0.35 * wet[..., None])
    _FS[seed] = (rgb.astype(np.float32), wet.astype(np.float32))
    return _FS[seed]


def wet_sheen(fr, wet, light=(960, -200), col=(0.55, 0.62, 0.75), amt=0.35, t=0.0):
    """积水反天光：随与光源距离衰减 + 雨点细碎闪动。"""
    yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32) * 2
    d = np.hypot(xx - light[0], (yy - light[1]) * 0.8)
    s = cv2.resize(np.exp(-(d / 1100) ** 2), (W, H))
    fl = cv2.resize(A.tex(int(t * 12) % 50 + 300, 128, 30, 2), (W, H))
    return fr + (wet * s * (0.7 + 0.6 * fl))[..., None] * np.array(col, np.float32) * amt


class Crater:
    """巨印压出的方形凹坑（俯拍）。c=中心，size=(宽,高)，rot=度。"""
    def __init__(self, c=(960, 520), size=(600, 520), rot=-4.0, seed=17, zheng=True, zsize=330):
        self.c = c
        r = np.random.default_rng(seed)
        m = np.zeros((H, W), np.float32)
        box = cv2.boxPoints((c, size, rot)).astype(np.float32)
        # 崩口：沿四边插点并随机向外/向内咬
        poly = []
        for i in range(4):
            p0, p1 = box[i], box[(i + 1) % 4]
            nrm = np.array([-(p1 - p0)[1], (p1 - p0)[0]]); nrm /= np.linalg.norm(nrm) + 1e-6
            for u in np.linspace(0, 1, 16, endpoint=False):
                bite = r.normal(0, 6) + (r.uniform(14, 46) if r.random() < 0.18 else 0)
                poly.append(p0 + (p1 - p0) * u - nrm * bite)     # 正 nrm 朝外？用符号检测
        poly = np.array(poly, np.float32)
        ctr = np.array(c, np.float32)
        # 让 bite 一律朝外（坑沿崩掉 = 坑变大）
        v = poly - ctr; base = np.repeat(box, 16, 0) * 0  # 占位
        cv2.fillPoly(m, [poly.astype(np.int32)], 1.0, cv2.LINE_AA)
        m2 = np.zeros_like(m); cv2.fillPoly(m2, [box.astype(np.int32)], 1.0, cv2.LINE_AA)
        self.mask = np.maximum(m, m2)
        nz = cv2.resize(A.tex(seed + 5, 256, 30, 3), (W, H))
        self.mask = np.clip((cv2.GaussianBlur(self.mask, (0, 0), 1.5) - 0.5 + (nz - 0.5) * 0.25) * 6 + 0.5, 0, 1)
        # 深度场：距坑沿越远越深（内壁斜面宽 ~38px）
        dist = cv2.distanceTransform((self.mask > 0.5).astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32)
        self.wall = np.clip(dist / 38, 0, 1)                                 # 0 = 坑沿, 1 = 坑底
        self.floor = (dist > 38).astype(np.float32)
        # 碎石：坑沿外一圈
        self.rocks = []
        for _ in range(46):
            ang = r.uniform(0, 2 * math.pi)
            rad = r.uniform(0.52, 0.85)
            px = c[0] + math.cos(ang) * size[0] * rad * (1 + 0.25 * abs(math.cos(ang)))
            py = c[1] + math.sin(ang) * size[1] * rad * (1 + 0.25 * abs(math.sin(ang)))
            s = r.uniform(6, 26) * (1.6 if r.random() < 0.15 else 1)
            k = r.integers(5, 8)
            pts = [(math.cos(2 * math.pi * j / k + r.uniform(-0.3, 0.3)) * s * r.uniform(0.6, 1.0),
                    math.sin(2 * math.pi * j / k + r.uniform(-0.3, 0.3)) * s * r.uniform(0.6, 1.0)) for j in range(k)]
            self.rocks.append((px, py, np.array(pts, np.float32), ang, r.uniform(0.6, 1.2)))
        # 裂缝：从四角和边中点向外放射
        self.cracks = []
        for i in range(4):
            p = box[i]; d = p - ctr; d = d / np.linalg.norm(d)
            for j in range(2):
                dd = d + r.normal(0, 0.35, 2); dd /= np.linalg.norm(dd)
                L = r.uniform(380, 900)
                self.cracks.append(K.crack_path(tuple(p), tuple(p + dd * L), seed + 40 + i * 3 + j, jag=0.025))
        self.zm = None
        if zheng:
            Lz = T.Layer(); T.place(Lz, '正', c[0], c[1] + 10, zsize, 'white', 'kai', texture=False)
            self.zm = cv2.GaussianBlur(Lz.A, (0, 0), 1.2) * self.floor

    def draw(self, fr, a, light=(-0.75, -0.65), heat=1.0, t=0.0):
        """a = 落地后秒数（裂缝延伸、余热衰减、碎石落定）。"""
        lx, ly = light
        m = self.mask
        # 坑外投影（光从左上 → 坑沿右下外侧无投影；坑内左上内壁背光 → 投影落在坑底左上）
        inside = m[..., None]
        depth_dark = 0.22 + 0.30 * self.wall[..., None]
        fr = fr * (1 - inside * depth_dark)
        # 内壁：迎光的一侧（右下内壁朝向左上光源）亮；背光侧（左上内壁）在坑底投下宽阴影
        sh_off = cv2.warpAffine(m, np.float32([[1, 0, -lx * 46], [0, 1, -ly * 46]]), (W, H))
        shadow = np.clip(m - sh_off, 0, 1)                                    # 坑底被左上坑沿遮住的部分
        shadow = cv2.GaussianBlur(shadow, (0, 0), 5)
        fr = fr * (1 - 0.70 * shadow[..., None])
        lit_off = cv2.warpAffine(m, np.float32([[1, 0, lx * 30], [0, 1, ly * 30]]), (W, H))
        lit = np.clip(m - lit_off, 0, 1) * (1 - self.floor)                   # 右下内壁斜面
        lit = cv2.GaussianBlur(lit, (0, 0), 3)
        stone = 0.8 + 0.4 * cv2.resize(A.tex(91, 256, 40, 3), (W, H))
        fr = fr + (lit * stone ** 2 * 0.8)[..., None] * np.array([0.26, 0.25, 0.25], np.float32) + (lit * self.wall)[..., None] * np.array([0.10, 0.05, 0.02], np.float32) * heat
        # 坑沿：迎光唇口一线冷高光（雨水湿边），背光唇口暗
        rim = np.clip(cv2.dilate(m, np.ones((5, 5), np.uint8)) - m, 0, 1)
        lip_l = np.clip(rim * (cv2.warpAffine(m, np.float32([[1, 0, -lx * 6], [0, 1, -ly * 6]]), (W, H)) > 0.5), 0, 1)
        fr = fr + cv2.GaussianBlur(lip_l, (0, 0), 1.0)[..., None] * np.array([0.30, 0.32, 0.36], np.float32)
        # 坑底「正」：凹刻，只靠侧光（槽内背光侧投影 + 迎光侧槽壁一线灰白），不着金红、无框
        if self.zm is not None:
            zs = np.clip(self.zm - cv2.warpAffine(self.zm, np.float32([[1, 0, -lx * 9], [0, 1, -ly * 9]]), (W, H)), 0, 1)
            zh = np.clip(self.zm - cv2.warpAffine(self.zm, np.float32([[1, 0, lx * 5], [0, 1, ly * 5]]), (W, H)), 0, 1)
            fr = fr * (1 - 0.35 * self.zm[..., None]) * (1 - 0.55 * zs[..., None]) + zh[..., None] * np.array([0.10, 0.10, 0.11], np.float32)
        # 裂缝：暗缝 + 缝底一线暖光（余热），只在缝内，不外溢成闪电
        prog = min(1.0, 0.35 + a / 0.35)
        for cp in self.cracks:
            cm = K.draw_crack((H, W), cp, 2.4, branches=1, seed=5, prog=prog)
            core = cv2.GaussianBlur(cm, (0, 0), 0.7) * 0.8
            fr = fr * (1 - 0.9 * cm[..., None])
            warm = heat * (0.30 + 0.55 * math.exp(-a / 0.6)) * (0.9 + 0.1 * math.sin(t * 9))
            fr = fr + (core * 0.9 + cv2.GaussianBlur(core, (0, 0), 3) * 0.35)[..., None] * np.array([0.95, 0.42, 0.16], np.float32) * warm
        # 坑底沿缝透出的暖光（四角最深处一点）
        heatmap = cv2.GaussianBlur(self.floor * (1 - cv2.GaussianBlur(self.floor, (0, 0), 30)), (0, 0), 8)
        fr = fr + heatmap[..., None] * np.array([1.0, 0.5, 0.18], np.float32) * heat * 0.10 * (0.5 + math.exp(-a / 0.8))
        # 碎石：落地瞬间被崩出、0.25s 内落定；暗石 + 左上亮边 + 右下接触影
        fl = min(1.0, a / 0.25); e = 1 - (1 - fl) ** 3
        for (px, py, pts, ang, sc) in self.rocks:
            off = (1 - e) * -40
            x = px + math.cos(ang) * off; y = py + math.sin(ang) * off
            P = (pts + (x, y)).astype(np.int32)
            S = np.zeros((H, W), np.float32)
            x0, y0 = P.min(0) - 20; x1, y1 = P.max(0) + 20
            if x1 < 0 or y1 < 0 or x0 > W or y0 > H: continue
            x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(W, x1), min(H, y1)
            sub = np.zeros((y1 - y0, x1 - x0), np.float32)
            cv2.fillPoly(sub, [P - (x0, y0)], 1.0, cv2.LINE_AA)
            shd = cv2.GaussianBlur(np.roll(np.roll(sub, 4, 0), 4, 1), (0, 0), 2.5)
            hi = np.clip(sub - np.roll(np.roll(sub, 2, 0), 2, 1), 0, 1)
            reg = fr[y0:y1, x0:x1]
            reg = reg * (1 - 0.6 * shd[..., None])
            reg = reg * (1 - sub[..., None]) + sub[..., None] * np.array([0.13, 0.125, 0.12], np.float32) * sc
            reg = reg + hi[..., None] * np.array([0.30, 0.30, 0.32], np.float32) * sc
            fr[y0:y1, x0:x1] = reg
        return fr


def tsh_seal_noface():
    """太上皇握玺：右侧后景（脸、发、肩）全部去掉，只留手 + 玉玺 + 左侧袖；去掉的区域由镜头画烛火屏风虚焦补。"""
    def b():
        F = R6._clean_alpha(R6._load('A_r6/tsh_seal_lift'), lo=0.15, erode=3)
        h, w = F.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        xn, yn = xx / w, yy / h
        # 保留区：x < 0.545（玺右沿 ≈0.53），以及袖口下摆不越过 0.56；斜边羽化
        k = np.clip((0.538 - xn + 0.02 * (yn - 0.5)) / 0.014, 0, 1)
        out = F.copy(); out[..., 3] = F[..., 3] * k
        return out
    return R6._cached('tsh_seal_noface', b)


def candle_screen(t, seed=3):
    """殿内后景虚焦：三扇屏风（木框 + 窗棂透烛光）+ 两团烛火光斑。返回 (H,W,3) 线性。"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    fr = A.vgrad((0.020, 0.014, 0.010), (0.045, 0.032, 0.022))
    pan = np.zeros((H // 4, W // 4), np.float32)
    lat = np.zeros((H // 4, W // 4), np.float32)
    for i, x0 in enumerate((780, 1080, 1380, 1680)):
        cv2.rectangle(pan, (x0 // 4, 120 // 4), ((x0 + 270) // 4, 900 // 4), 1.0, -1)
        for gx in range(x0 + 30, x0 + 270, 48):
            cv2.line(lat, (gx // 4, 150 // 4), (gx // 4, 870 // 4), 1.0, 1)
        for gy in range(150, 880, 56):
            cv2.line(lat, ((x0 + 20) // 4, gy // 4), ((x0 + 250) // 4, gy // 4), 1.0, 1)
    pan = cv2.resize(cv2.GaussianBlur(pan, (0, 0), 4), (W, H)); lat = cv2.resize(cv2.GaussianBlur(lat, (0, 0), 3), (W, H))
    paper = pan * (1 - 0.6 * lat)
    glow = np.exp(-(((xx - 1450) / 650) ** 2 + ((yy - 420) / 400) ** 2))
    fl = 1 + 0.06 * math.sin(t * 11) + 0.04 * math.sin(t * 17 + 1)
    fr = fr + paper[..., None] * glow[..., None] * np.array([0.55, 0.33, 0.14], np.float32) * fl
    for (cx, cy, r, a) in ((1500, 300, 70, 1.0), (1760, 360, 55, 0.7)):     # 烛焰光斑（焦外圆斑）
        d = np.hypot(xx - cx, (yy - cy) * 0.8)
        fr = fr + (np.clip((r - d) / 6, 0, 1) * 0.6 + np.exp(-(d / (r * 3)) ** 2) * 0.5)[..., None] * np.array([1.0, 0.70, 0.36], np.float32) * a * fl
    return fr


def a_cleave(A_, B_, p, angle=32.0, center=(960, 540), mode='open', col=(1.0, 0.35, 0.15)):
    """一刀两分：0–0.3 一道斩光沿斩线自一端划到另一端（A 上）；0.3 起 A 沿这条线断成两块，
    mode='open' 两块垂直斩线向外飞开（缝里露出 B），mode='shear' 两块沿斩线反向错滑出画。
    A、B 各只出现一次；两块的空出区一律是 B，不复制、不倒置。"""
    th = math.radians(angle); dv = (math.cos(th), math.sin(th)); nv = (-dv[1], dv[0])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sd = (xx - center[0]) * nv[0] + (yy - center[1]) * nv[1]
    al = (xx - center[0]) * dv[0] + (yy - center[1]) * dv[1]
    if p < 0.3:
        q = p / 0.3
        head = -1200 + 2400 * (1 - (1 - q) ** 2)
        line = np.exp(-(sd / 2.2) ** 2) * (al < head) * np.clip(1 - (head - al) / 1800, 0, 1)
        L = line * 2.0 + cv2.GaussianBlur(line, (0, 0), 8) * 1.2
        return A_ + L[..., None] * np.array([1.0, 0.95, 0.9], np.float32) + cv2.GaussianBlur(line, (0, 0), 30)[..., None] * np.array(col, np.float32) * 0.6
    q = (p - 0.3) / 0.7; e = q ** 1.6
    if mode == 'open':
        sep = 40 + 1300 * e; sl = 120 * e
    else:
        sep = 20 + 80 * e; sl = 2400 * e
    out = B_ * 1.0
    out = cv2.resize(B_, None, fx=1.0, fy=1.0)
    for sgn in (1, -1):
        tx = sgn * (nv[0] * sep + dv[0] * sl); ty = sgn * (nv[1] * sep + dv[1] * sl)
        M = np.float32([[1, 0, tx], [0, 1, ty]])
        half = cv2.warpAffine(A_, M, (W, H), borderMode=cv2.BORDER_CONSTANT)
        mk = cv2.warpAffine(((sd > 0) if sgn > 0 else (sd <= 0)).astype(np.float32), M, (W, H))
        edge = np.exp(-((sd - sgn * sep) / 3.0) ** 2) * mk                           # 断口一线红热
        out = out * (1 - mk[..., None]) + half * mk[..., None]
        out = out + edge[..., None] * np.array(col, np.float32) * 1.6 * (1 - q)
    return out


def ink_bg(t, seed=21):
    """V21 背景：墨渍体积（低频墨晕 + 飞溅点 + 冷雨）—— 不是平板。"""
    nz = cv2.resize(A.tex(seed, 256, 3, 5), (W, H)); nz2 = cv2.resize(A.ink_noise(seed + 2, 256), (W, H))
    v = 0.025 + 0.06 * np.clip(nz - 0.35, 0, 1) + 0.035 * np.clip(nz2 - 0.5, 0, 1)
    fr = v[..., None] * np.array([1.0, 0.92, 0.88], np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    fr = fr + (np.exp(-(((xx - 960) / 700) ** 2 + ((yy - 540) / 400) ** 2)) * 0.05)[..., None] * np.array([0.9, 0.35, 0.25], np.float32)
    return fr
