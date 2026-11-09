"""units/sec_b_pre1.py — B 组 · 预副歌一「谁配」（帧 1321–1784，44.048–59.47s）
分镜：crew/round4/B_storyboard.md 第 1 节。14 镜 + 副歌一 S028 开头 5 帧（直接调用 chorus1，接缝逐像素一致）。
接口：READY / frame(f, cache) -> uint8 (1080,1920,3)"""
import sys, math, os
ROOT = '/workspace/work/mv'
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, cv2
from b_kit import *
import b_kit as BK
import c1kit as K
import typo as T
import trans as TR
import b_paper as BP

READY = False
F0, F1 = 1321, 1784
C1_FROM = 1779                    # 59.30 起交给副歌一（它的 S028 =「血」字头硬切）

# 切点（秒，落拍/字头）→ 帧（视觉帧 = 最近帧 - 1）
CUT_T = [44.048, 44.95, 45.88, 46.79, 47.72, 49.09, 50.46, 51.85, 52.76, 53.68, 54.59, 55.50, 56.40, 57.33, 58.26, 59.30]   # 第五棒：58.26 拍点加 P15
CUT_F = [F0] + [int(round(t * FPS)) - 1 for t in CUT_T[1:-1]] + [C1_FROM]


# =====================================================================================
# P01 ECU 俯拍生死簿：太上皇执朱笔（tsh_brush_hand），「谁配」流江毛草朱笔逐笔写在纸上
DOCT = '纲常礼法忠孝节义尊卑贵贱王法天道规矩名分本分顺从伦理三纲五常君臣父子上下有序安分守己'   # 第五棒：铅字盘填充改「教条」字（去名单母题）
NAMES = '张王李赵刘陈杨黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟龙万段雷钱汤尹黎易常武乔贺赖龚文'


def ledger(seed, cols=13, size=46, x0=150, x1=1770, y0=150, y1=930, rule=(0.55, 0.12, 0.08), ink=(0.12, 0.10, 0.09), tone=(0.80, 0.74, 0.62), chars=None):
    """生死簿纸面：竖格朱丝栏 + 宋体人名竖排（右起）"""
    fr = BK.paper(seed, tone)
    r = np.random.default_rng(seed)
    L = T.Layer()
    cw = (x1 - x0) / cols
    for c in range(cols + 1):
        x = int(x0 + c * cw)
        cv2.line(fr, (x, y0 - 30), (x, y1 + 30), tuple(float(v) * 0.9 for v in rule), 2, cv2.LINE_AA)
    for c in range(cols):
        cx = x1 - (c + 0.5) * cw
        y = y0 + r.uniform(0, size)
        while y < y1 - size:
            n = int(r.integers(2, 4))
            for k in range(n):
                cs = chars or NAMES
                T.place(L, cs[int(r.integers(len(cs)))], cx, y, size, color=ink, fname='serif_m', alpha=r.uniform(0.6, 0.9))
                y += size * 1.12
            y += size * r.uniform(0.6, 1.4)
    A = L.A
    fr = fr * (1 - A[..., None] * 0.85) + L.C * A[..., None] * 0.85
    return fr.astype(np.float32)


class P01(Shot):
    def __init__(self):
        self.bg = ledger(201)
        self.hand = BK.spr_feather('tsh_brush_hand', left=0.10, right=0.18, bottom=0.32, keep_col=(0.60, 0.68))
        T.prepare_brush('谁配', 'kai', 250)   # 第五棒：草书→楷（评审：「谁」读成淮/渠）
        self.P = [dict(ch='谁', x=640, y=420, size=260, rot=-4, font='kai', idx=0, emph=False),
                  dict(ch='配', x=760, y=700, size=260, rot=3, font='kai', idx=1, emph=False)]

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        # 烛光：右上暖光斑 + 左下压暗
        x, y = K.grid()
        light = np.exp(-(((x - 1400) / 900) ** 2 + ((y - 250) / 600) ** 2))
        fr = fr * (0.35 + 0.75 * light[..., None]) * np.array([1.0, 0.92, 0.80], np.float32)
        p0 = clamp01((t - 44.0) / 0.42); p1 = clamp01((t - (44.78 - 0.22)) / 0.42)
        # 笔尖跟随正在写的字（笔锋在字心附近画小圈）；手在字的右上方，袖子渐隐进暗部
        k = 1 if p1 > 0 else 0
        pc = p1 if k else p0
        pp = self.P[k]
        ang = pc * 9.0
        tip = (pp['x'] + 40 + 90 * pc + 30 * math.sin(ang), pp['y'] - 70 + 150 * pc + 25 * math.cos(ang * 1.3))
        if pc >= 1 and k == 1: tip = (pp['x'] + 130, pp['y'] + 90 - 60 * (t - 45.0))
        sh = np.zeros((H // 4, W // 4), np.float32)
        cv2.line(sh, (int((tip[0] + 40) / 4), int((tip[1] + 30) / 4)), (int((tip[0] + 420) / 4), int((tip[1] - 900) / 4)), 1.0, 9, cv2.LINE_AA)
        sh = cv2.resize(cv2.GaussianBlur(sh, (0, 0), 6), (W, H))
        fr = fr * (1 - 0.45 * sh[..., None])
        # 手：笔尖在精灵内约 (0.638, 0.88)；镜像（手从右上入画，不挡字）
        fr, _ = put_at(fr, self.hand, t, (0.638, 0.88), tip, 1500, grade=GR_WARM, rim=RIM_WARM, wind_amp=0, breathe=0.0,
                       shade=None, wrap=0.2)
        fr = T.brush_write(fr, '谁配', [p0, p1], places=self.P, fname='kai', color=(0.62, 0.06, 0.04), splatter=True,
                           style_kw=dict(shadow=0.15))
        z = 1.0 + 0.08 * eio(u)
        fr = cam(fr, z, 0, 0, 2.0 * eio(u) - 1.0)
        # 入口：墨从黑中洇开成纸（接 A 组）
        if t < self.t0 + 0.30:
            m = K.ink_blot(0.86 + 0.14 * eout((t - self.t0) / 0.28, 2), seed=201, center=(930, 520), reverse=True)
            fr = over(fr, m, np.array([0.015, 0.012, 0.012], np.float32))
        return fr, 0


# =====================================================================================
# P02 微距：朱砂滴落在名字上炸开；「写生死簿」宋体竖排印出，「生死」被朱砂浸红
class P02(Shot):
    T_DROP = V(45.38)
    def __init__(self):
        self.bg = ledger(202, cols=6, size=110, x0=40, x1=1880, y0=130, y1=980)
        T.warm('写生死簿', 'serif_black', 130)
        self.P = [dict(ch=c, x=1010, y=250 + i * 170, size=130, rot=0, font='serif_black', idx=i, emph=c in '生死')
                  for i, c in enumerate('写生死簿')]

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        x, y = K.grid()
        fr = fr * (0.45 + 0.6 * np.exp(-(((x - 1100) / 800) ** 2 + ((y - 400) / 500) ** 2)))[..., None] * np.array([1.0, 0.93, 0.82], np.float32)
        # 朱砂晕开（落点 = 「生」「死」之间）
        cx, cy = 1010, 505
        if t >= self.T_DROP:
            q = eout((t - self.T_DROP) / 0.45, 2)
            nz = cv2.resize(K.fbm(H // 4, W // 4, 22, base=6, octaves=5), (W, H))
            d = np.sqrt((x - cx) ** 2 + ((y - cy) * 0.8) ** 2) / 330
            m = np.clip((q * 1.0 - d - (nz - 0.5) * 0.5) * 6, 0, 1)
            rim = np.clip(1 - np.abs(q - d - (nz - 0.5) * 0.5) * 12, 0, 1) * 0.5
            fr = fr * (1 - m[..., None] * np.array([0.25, 0.85, 0.9], np.float32)) * (1 - rim[..., None] * 0.3)
            # 飞溅
            r = np.random.default_rng(23)
            for i in range(26):
                a = r.uniform(0, 6.28); dd = r.uniform(120, 520) * eout((t - self.T_DROP) / 0.12)
                rr = int(r.uniform(4, 16))
                cv2.circle(fr, (int(cx + math.cos(a) * dd), int(cy + math.sin(a) * dd * 0.8)), rr, (0.5, 0.05, 0.03), -1, cv2.LINE_AA)
        pr = tp(8, [2, 3, 4, 5], t, 0.16)
        cols = [(0.08, 0.06, 0.05) if not p['emph'] else (0.62, 0.05, 0.04) for p in self.P]
        L = T.Layer()
        for p, pc, c in zip(self.P, pr, cols):
            if pc <= 0: continue
            e = eout(pc, 3)
            T.place(L, p['ch'], p['x'], p['y'], p['size'], color=c, fname='serif_black', alpha=min(1, pc * 2), scale=1 + 0.8 * (1 - e))
        fr = T.compose(fr, L, shadow=0.25)
        # 下落的朱砂滴（前景、虚焦、慢）
        if t < self.T_DROP:
            q = clamp01((t - (self.T_DROP - 0.35)) / 0.35)
            yy = -40 + (cy + 40) * q ** 1.7
            dl = np.zeros((H, W), np.float32)
            cv2.ellipse(dl, (cx, int(yy)), (16, 24), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
            dl = cv2.GaussianBlur(dl, (0, 0), 2)
            fr = over(fr, dl, np.array([0.55, 0.03, 0.02], np.float32))
            fr += cv2.GaussianBlur(dl, (0, 0), 8)[..., None] * np.array([0.3, 0.05, 0.03], np.float32)
        k = pulse(t, self.T_DROP, 0.1) * (t >= self.T_DROP)
        z = 1.12 - 0.08 * eio(u) + 0.04 * k
        fr = cam(fr, z, 0, 0, -1.5 + 1.5 * u, center=(cx, cy))
        return fr, (2 if k > 0.5 else 0)


# =====================================================================================
# P03 MS 俯拍：朱笔沿四边画框，把纸面中央的小纸人框住；「谁配画」毛草错落
import paper as PA
BOX_C = (960, 560)


def brush_box(fr, c, half, prog, seed=0, width=26, color=(0.62, 0.06, 0.04)):
    """干笔朱框：四条边依次画出（prog 0→1），飞白 + 起笔顿点"""
    pts = [(c[0] - half, c[1] - half), (c[0] + half, c[1] - half), (c[0] + half, c[1] + half), (c[0] - half, c[1] + half), (c[0] - half, c[1] - half)]
    m = np.zeros((H // 2, W // 2), np.float32)
    for i in range(4):
        q = clamp01(prog * 4 - i)
        if q <= 0: break
        a = np.array(pts[i]); b = np.array(pts[i + 1])
        e = a + (b - a) * q
        n = max(2, int(q * 30))
        for j in range(n):
            s0 = a + (b - a) * q * j / n; s1 = a + (b - a) * q * (j + 1) / n
            w = width * (1.15 - 0.35 * j / n)
            cv2.line(m, tuple((s0 / 2).astype(int)), tuple((s1 / 2).astype(int)), 1.0, max(1, int(w / 2)), cv2.LINE_AA)
        cv2.circle(m, tuple((a / 2).astype(int)), int(width * 0.75 / 2), 1.0, -1, cv2.LINE_AA)
    m = cv2.resize(m, (W, H))
    nz = cv2.resize(K.fbm(H // 2, W // 8, seed, base=8, octaves=4), (W, H))
    dry = np.clip((nz - 0.32) * 4, 0, 1)
    m = m * (0.55 + 0.45 * dry)
    return over(fr, np.clip(m * 1.2, 0, 1), np.array(color, np.float32))


class P03(Shot):
    HALF = 270
    def __init__(self):
        self.bg = BK.paper(203, (0.78, 0.72, 0.60))
        self.fig = spr('effigy')        # 第五棒：代码名帖纸人（圆头+矩形）→ 生图纸扎人
        T.warm('谁配画', 'xing', 200)

    def scene(self, t, prog, half, c):
        fr = self.bg.copy()
        x, y = K.grid()
        fr = fr * (0.42 + 0.65 * np.exp(-(((x - c[0]) / 900) ** 2 + ((y - c[1] + 100) / 600) ** 2)))[..., None] * np.array([1.0, 0.93, 0.82], np.float32)
        hh = half * 1.75
        # 纸人投影 + 纸人
        sh = np.zeros((H, W), np.float32)
        cv2.ellipse(sh, (int(c[0] + hh * 0.12), int(c[1] + hh * 0.48)), (int(hh * 0.28), int(hh * 0.07)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        fr = fr * (1 - 0.5 * cv2.GaussianBlur(sh, (0, 0), 10)[..., None])
        fr, _ = put(fr, self.fig, t, hh, (c[0], c[1] + hh * 0.48), grade=dict(expo=0.95, sat=0.7, tint=(1.04, 0.97, 0.88), lift=0.0, gamma=1.05),
                    rim=dict(col=(1.0, 0.78, 0.5), amt=1.2, dir=(0.6, -0.8)), wind_amp=0, breathe=0.004, rot=1.2 * math.sin(t * 1.7),
                    shade=None, wrap=0.25)
        fr = brush_box(fr, c, half, prog, seed=33, width=max(10, half * 0.11))
        return fr

    def render(self, t):
        u = self.u(t)
        prog = clamp01((t - self.t0 - 0.05) / 0.75)
        fr = self.scene(t, prog, self.HALF, BOX_C)
        pr = tp(8, [6, 7, 8], t, 0.18)
        fr = T.scatter_stack(fr, '谁配画', pr, places=[dict(ch='谁', x=1480, y=300, size=160, rot=-6, font='xing', idx=0, emph=False),
                                                         dict(ch='配', x=1600, y=480, size=180, rot=5, font='xing', idx=1, emph=False),
                                                         dict(ch='画', x=1470, y=700, size=230, rot=-3, font='xing', idx=2, emph=True)],
                             color=(0.10, 0.08, 0.07), emph_color=(0.62, 0.06, 0.04), t_local=u, style_kw=dict(shadow=0.2))
        fr = cam(fr, 1.0 + 0.03 * eio(u), -20 * eio(u), 0, 0.8 * u)
        return fr, 0


# =====================================================================================
# P04 LS 后拉：朱框在太上皇巨大指尖下（图形匹配：P03 的框 = 指下的框）；「善恶框」，「框」字被真框住
class P04(Shot):
    HALF = 170
    C = (960, 610)
    T_KUANG = V(47.70)
    def __init__(self):
        self.p3 = P03()
        self.finger = spr('S021/finger')
        T.warm('善恶', 'xing', 170); T.warm('框', 'xing', 230)

    def render(self, t):
        u = self.u(t)
        fr = self.p3.scene(t, 1.0, self.HALF, self.C)
        # 指尖：从上方压下按住框上沿（finger 精灵：指尖在精灵内 (0.497, 0.300)；第三棒修正，原锚点 0.96 让手整只在画外）
        k = eout(clamp01((t - self.t0) / 0.5), 3)
        tip = (self.C[0] - 40, self.C[1] - self.HALF - 6 - 220 * (1 - k))
        fr = fr * (1 - 0.35 * cv2.GaussianBlur((np.abs(K.grid()[0] - tip[0] - 60) < 220).astype(np.float32) * (K.grid()[1] < tip[1] + 30), (0, 0), 60)[..., None])
        fr, _ = put_at(fr, self.finger, t, (0.497, 0.300), tip, 2600, grade=dict(expo=0.55, sat=0.4, tint=(1.04, 0.96, 0.86), lift=0.0, gamma=1.2),
                       rim=RIM_WARM, wind_amp=0, breathe=0.0, shade=None, wrap=0.25)
        # 「善恶框」：善恶毛草；「框」外画朱红真框，字头时合拢
        pr = tp(8, [9, 10, 11], t, 0.18)
        L = T.Layer()
        for ch, xx, yy, s, pc in (('善', 1450, 330, 160, pr[0]), ('恶', 1590, 500, 160, pr[1])):
            if pc > 0: T.place(L, ch, xx, yy, s, color=(0.10, 0.08, 0.07), fname='xing', alpha=min(1, pc * 2), scale=1 + (1 - eout(pc)) * 1.2)
        if pr[2] > 0: T.place(L, '框', 1520, 720, 200, color=(0.62, 0.06, 0.04), fname='xing', alpha=min(1, pr[2] * 2), scale=1 + (1 - eout(pr[2])) * 1.2)
        fr = T.compose(fr, L, shadow=0.2)
        kq = clamp01((t - (self.T_KUANG - 0.25)) / 0.25)
        if kq > 0:
            fr = brush_box(fr, (1520, 720), 150, kq, seed=44, width=16)
        # 后拉：开头 z=230/170（与 P03 框同大同位），拉到 1.0
        z0 = P03.HALF / self.HALF
        z = z0 + (1.0 - z0) * eout(u, 2.4)
        cx = BOX_C[0] + (self.C[0] - BOX_C[0]); cy = self.C[1]
        pk = pulse(t, self.T_KUANG, 0.1) * (t >= self.T_KUANG)
        fr = cam(fr, z * (1 + 0.05 * pk), (BOX_C[0] - cx) * 0, (BOX_C[1] - cy) * (1 - eout(u, 2.4)), 0.8 * (1 - u), center=(cx, cy))
        return fr, (3 if pk > 0.5 else 0)


# =====================================================================================
# 第三棒：P05/P06 从「砖墙」改为「朱漆宫门 + 门钉」（与副歌一砖墙母题区分）
def palace_gate(w, h, seed, cols=7, rows=7, stud_r=34, margin=0.08, leaves=2):
    """朱漆宫门正面贴图：两扇门 + 竖向门板缝 + 龟裂旧漆 + 铜门钉（半球受光）+ 中缝铺首门环。
    返回 (rgb, seam 缝遮罩, studs 门钉遮罩, centers 门钉中心列表)"""
    r = np.random.default_rng(seed)
    x, y = K.grid(h, w)
    n1 = cv2.resize(K.fbm(h // 8, w // 8, seed, 6, 5), (w, h))
    n2 = cv2.resize(K.fbm(h // 3, w // 3, seed + 1, 12, 4), (w, h))
    lac = np.array([0.21, 0.025, 0.022], np.float32)
    rgb = lac * (0.55 + 0.6 * n1[..., None]) * (0.9 + 0.2 * n2[..., None])
    # 竖向木纹 + 漆面龟裂（暗线）
    grain = cv2.resize(r.random((h // 6 + 1, w // 2 + 1)).astype(np.float32), (w, h))
    grain = cv2.GaussianBlur(grain, (0, 0), sigmaX=0.8, sigmaY=12)
    rgb = rgb * (0.85 + 0.3 * grain[..., None])
    cr = cv2.resize(K.fbm(h // 2, w // 2, seed + 2, 24, 4), (w, h))
    crack = np.clip(1 - np.abs(cr - 0.5) * 60, 0, 1) * (n1 > 0.45)
    rgb = rgb * (1 - 0.55 * crack[..., None])
    worn = np.clip((n2 - 0.72) * 6, 0, 1)                     # 掉漆露木
    rgb = rgb * (1 - worn[..., None]) + worn[..., None] * np.array([0.11, 0.07, 0.045], np.float32) * (0.7 + 0.5 * grain[..., None])
    seam = np.zeros((h, w), np.float32)
    lw = w / leaves
    for L in range(leaves + 1):
        cv2.line(seam, (int(L * lw), 0), (int(L * lw), h), 1.0, 9, cv2.LINE_AA)
    for L in range(leaves):
        x0s = L * lw + lw * margin; x1s = (L + 1) * lw - lw * margin
        for j in range(1, cols, 2):                                # 板缝落在两列门钉之间
            xx = int(x0s + (x1s - x0s) * j / cols + r.uniform(-4, 4))
            cv2.line(seam, (xx, 0), (xx, h), 0.7, 3, cv2.LINE_AA)
    rgb = rgb * (1 - 0.8 * seam[..., None])
    rgb = rgb + np.clip(np.roll(seam, 3, 1) - seam, 0, 1)[..., None] * np.array([0.30, 0.08, 0.05], np.float32) * 0.5
    studs = np.zeros((h, w), np.float32); cen = []
    sh = np.zeros((h, w, 3), np.float32)
    for L in range(leaves):
        x0 = L * lw + lw * margin; x1 = (L + 1) * lw - lw * margin
        for i in range(rows):
            for j in range(cols):
                cx = x0 + (x1 - x0) * (j + 0.5) / cols; cy = h * margin + (h * (1 - 2 * margin)) * (i + 0.5) / rows
                cen.append((cx, cy))
    rr = stud_r
    yy, xx = np.mgrid[-rr - 6:rr + 7, -rr - 6:rr + 7].astype(np.float32)
    d = np.sqrt(xx ** 2 + yy ** 2) / rr
    m = np.clip((1 - d) * rr * 0.6, 0, 1)
    nz = np.sqrt(np.clip(1 - d ** 2, 0, 1))
    lx, ly, lz = -0.45, -0.6, 0.66
    diff = np.clip((xx / rr) * lx + (yy / rr) * ly + nz * lz, 0, 1)
    spec = np.clip((xx / rr) * lx + (yy / rr) * ly + nz * lz, 0, 1) ** 24
    bronze = np.array([0.42, 0.28, 0.11], np.float32)
    patch = bronze * (0.18 + 0.95 * diff[..., None]) + spec[..., None] * np.array([1.0, 0.9, 0.7], np.float32) * 0.9
    shadow = np.clip(1 - np.sqrt((xx - rr * 0.25) ** 2 + (yy - rr * 0.35) ** 2) / (rr * 1.15), 0, 1)
    ph, pw = m.shape
    for (cx, cy) in cen:
        X0, Y0 = int(cx - pw // 2), int(cy - ph // 2)
        if X0 < 0 or Y0 < 0 or X0 + pw > w or Y0 + ph > h: continue
        reg = rgb[Y0:Y0 + ph, X0:X0 + pw]
        reg *= (1 - 0.6 * shadow[..., None])
        tint = 0.85 + 0.3 * r.random()
        rgb[Y0:Y0 + ph, X0:X0 + pw] = reg * (1 - m[..., None]) + patch * tint * m[..., None]
        studs[Y0:Y0 + ph, X0:X0 + pw] = np.maximum(studs[Y0:Y0 + ph, X0:X0 + pw], m)
    return rgb.astype(np.float32), seam, studs, cen


class P05(Shot):
    """LS 仰：夜色里朱漆宫门（门钉成阵）+ 黑漆金字匾「规矩」；「谁的规矩」金箔浮字被门缝/板缝切断（左扇谁的、右扇规矩）"""
    def __init__(self):
        g, seam, studs, _ = palace_gate(2400, 1700, 905, cols=7, rows=7, stud_r=40)
        q = np.float32([[-160, 330], [2080, 330], [1820, 1080 + 320], [100, 1080 + 320]])   # 仰拍梯形（上宽下窄）
        self.gate = K.warp_quad(g, q, (H + 300, W)); self.seam = K.warp_quad(seam[..., None].repeat(3, -1), q, (H + 300, W))[..., 0]
        self.studs = K.warp_quad(studs[..., None].repeat(3, -1), q, (H + 300, W))[..., 0]
        self.m = np.zeros((H + 300, W), np.float32); cv2.fillConvexPoly(self.m, np.int32(q), 1.0)
        # 门楣（深色额枋，带一排金线）
        self.sky = K.sky(seed=905, cloud=0.8, horizon=0.2, stars=0.2)
        self.plq = __import__('props').Plaque('规矩', seed=5, fname='song')
        T.warm('谁的规矩', 'serif_black', 170)

    def render(self, t):
        u = self.u(t)
        oy = 170 - 260 * eio(u)            # 下摇：匾 → 门
        fr = np.zeros((H + 300, W, 3), np.float32)
        fr[:] = cv2.resize(self.sky, (W, H + 300))
        x, y = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H + 300, dtype=np.float32))
        # 门楣额枋
        lin = ((y > 150) & (y < 330) & (x > -100) & (x < 2020)).astype(np.float32)
        fr = fr * (1 - lin[..., None]) + lin[..., None] * np.array([0.05, 0.035, 0.03], np.float32) * (0.8 + 0.4 * np.exp(-((x - 960) / 700) ** 2))[..., None]
        fr += (np.exp(-((y - 318) / 3) ** 2) * (x > -100))[..., None] * GOLD * 0.35
        # 门：冷月顶光 + 匾下暖光 + 灯笼侧光（门钉逐个被扫亮）
        gl = self.gate * (0.50 + 0.75 * np.exp(-((y - 380) / 650) ** 2))[..., None]
        gl += np.exp(-(((x - 960) / 520) ** 2 + ((y - 520) / 220) ** 2))[..., None] * GOLD * 0.10
        sweep = np.exp(-((x - (-200 + 2400 * clamp01((t - self.t0) / 1.3))) / 260) ** 2)
        gl += (self.studs * sweep)[..., None] * GOLD * 0.55
        fr = fr * (1 - self.m[..., None]) + gl * self.m[..., None]
        off = int(150 - oy * 0.5)
        fr = np.ascontiguousarray(fr[off:off + H]); seam = self.seam[off:off + H]; studs = self.studs[off:off + H]
        fr, _ = self.plq.draw(fr, t, 960, 240 - off, 640, sheen=clamp01((t - self.t0) / 1.2) * 1.4 - 0.2)
        # 金箔浮字：左扇「谁的」右扇「规矩」，被中缝与板缝切断（缝里漏出暗红）
        pr = tp(9, [0, 1, 2, 3], t, 0.2)
        L = T.Layer()
        pos = [(560, 0), (790, 0), (1130, 0), (1360, 0)]
        for i, (ch, pc) in enumerate(zip('谁的规矩', pr)):
            if pc > 0: T.place(L, ch, pos[i][0], 760 - off * 0.6, 200, color='white', fname='serif_black', alpha=min(1, pc * 2.5),
                               scale=1 + 0.25 * (1 - eout(pc)))
        A = L.A * (1 - np.clip(seam * 1.8, 0, 1))
        hl = np.clip(A - np.roll(A, 3, 0), 0, 1)
        sh = np.clip(A - np.roll(A, -4, 0), 0, 1)
        leaf = GOLD * (0.65 + 0.35 * cv2.resize(K.fbm(H // 8, W // 8, 953, 6, 4), (W, H)))[..., None]
        fr = fr * (1 - A[..., None]) + A[..., None] * leaf
        fr = fr + hl[..., None] * np.array([1.0, 0.92, 0.7], np.float32) * 0.45 - sh[..., None] * 0.25
        glow = sum(pulse(t, V(CT(9, k)), 0.18) * (t >= V(CT(9, k))) for k in range(4))
        fr = fr + K.blur_ds(A, 14)[..., None] * GOLD * (0.12 + 0.4 * glow)
        fr = np.clip(fr, 0, None)
        fr = BK.rain(fr, t, 951, amt=0.3, n=400, angle=6)
        fr = K.fog(fr, t, 952, amt=0.2, y0=0.65, y1=1.0)
        fr = cam(fr, 1.0 + 0.06 * eio(u), 0, 0)
        return fr, 0


# =====================================================================================
# P06 CU：门钉特写，朱红血水从每颗门钉下渗出、顺门板缝往下流（用血来装潢）；「血」巨字从门缝渗出并下流
class P06(Shot):
    T_XUE = V(49.62)
    def __init__(self):
        g, seam, studs, cen = palace_gate(2300, 1500, 906, cols=7, rows=5, stud_r=62, margin=0.05, leaves=1)
        q = np.float32([[-190, -170], [2110, -110], [2110, 1190], [-190, 1250]])           # 近正面、轻微倾斜
        self.g = K.warp_quad(g, q); self.seam = K.warp_quad(seam[..., None].repeat(3, -1), q)[..., 0]
        self.studs = K.warp_quad(studs[..., None].repeat(3, -1), q)[..., 0]
        M = cv2.getPerspectiveTransform(np.float32([[0, 0], [2300, 0], [2300, 1400], [0, 1400]]), q)
        c = cv2.perspectiveTransform(np.float32(cen)[None], M)[0]
        self.cen = [(float(a), float(b)) for a, b in c if -50 < a < W + 50 and -50 < b < H + 50]
        T.warm('用来装潢', 'serif_sb', 100)
        self.flow_n = cv2.resize(K.fbm(H // 8, W // 8, 906, base=4, octaves=4), (W, H))
        r = np.random.default_rng(907)
        st = cv2.resize(r.random((8, W // 14)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
        self.streak = np.clip(st, 0, 1)
        self.drip = cv2.resize(r.random((1, W // 40)).astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST) ** 3
        self.drip = cv2.GaussianBlur(self.drip, (0, 0), 6)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        hl = np.zeros((H, W), np.float32)
        for (cx, cy) in self.cen:
            hl += np.exp(-(((xx - cx + 18) ** 2 + (yy - cy + 22) ** 2) / 22 ** 2))
        self.stud_hl = 0.5 + 2.0 * np.clip(hl, 0, 1)

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        fr = self.g * 0.9 * (0.40 + 0.75 * np.exp(-(((x - 820) / 1000) ** 2 + ((y - 380) / 700) ** 2)))[..., None]
        # 血幕：从匾底沿门面整片往下淌（朱漆原来是血），前沿不齐、竖向流痕；门钉被血包住后泛红光
        q_ = clamp01((t - self.t0) / 1.25)
        front = 60 + (H + 150) * ein(q_, 1.25) - self.flow_n * 300 - self.drip * 220 * q_
        cover = sstep(front + 30, front - 30, y)
        streak = self.streak
        blood = np.clip(cover * (0.75 + 0.35 * streak), 0, 1)
        blood = np.maximum(blood, np.clip(self.seam * 1.2, 0, 1) * (y < front + 50) * 0.5)
        wet = cv2.GaussianBlur(blood, (0, 0), 8)
        fr = fr * (1 - wet[..., None] * 0.45)
        fr = fr * (1 - blood[..., None] * 0.75) + blood[..., None] * np.array([0.30, 0.012, 0.01], np.float32) * (0.6 + 0.6 * streak[..., None])
        lum = self.g.mean(-1, keepdims=True)
        sb = (self.studs * blood)[..., None]
        fr = fr * (1 - sb) + sb * lum * np.array([2.2, 0.22, 0.16], np.float32) * (0.8 + 0.5 * self.stud_hl[..., None])
        bb = cv2.GaussianBlur(blood, (0, 0), 2.5)
        spec = np.clip(-cv2.Sobel(bb, cv2.CV_32F, 1, 0, ksize=3) * 1.5, 0, 1) + np.clip(-cv2.Sobel(bb, cv2.CV_32F, 0, 1, ksize=3), 0, 1) * 0.5
        fr = fr + spec[..., None] * np.array([1.0, 0.62, 0.52], np.float32) * 0.8
        # 第七棒：去掉朱红「血」巨字（留给副歌一 S028）。「用血来装潢」竖排刻在血幕右侧门板上；「血」一字由门缝流下的血水写成（墨洇 + 下淌），
        #   与其余宋体同一列、同一字号，只是它是湿的、红的、还在往下流
        pr = tp(9, [4, 5, 6, 7, 8], t, 0.18)
        L = T.Layer(); LB = T.Layer()
        for i, (ch, pc) in enumerate(zip('用血来装潢', pr)):
            if pc <= 0: continue
            if ch == '血':
                a = T.ink_bleed_glyph('血', 'kai', 150, max(0.02, pc), seed=6, bleed=1.2)
                LB.paste(a, 1600, 290 + i * 118 + 6, (0.80, 0.07, 0.04))
            else:
                T.place(L, ch, 1600, 290 + i * 118, 100, color=(0.96, 0.94, 0.88), fname='serif_sb', alpha=min(1, pc * 2), scale=1 + 0.4 * (1 - eout(pc)))
        LB = T.drip_layer(LB, clamp01((t - self.T_XUE) / 0.9), n=5, seed=6, length=0.45)
        fr = fr * (1 - 0.5 * K.blur_ds((np.abs(x - 1600) < 80) * (y > 220) * (y < 900) * 1.0, 30)[..., None])
        fr = T.compose(fr, L, shadow=0.85, glow=0.10)
        fr = T.compose(fr, LB, shadow=0.6, glow=0.35, glow_color=(0.7, 0.05, 0.03))
        hb = cv2.GaussianBlur(LB.A, (0, 0), 2)
        fr = fr + np.clip(-cv2.Sobel(hb, cv2.CV_32F, 1, 1, ksize=3), 0, 1)[..., None] * np.array([1.0, 0.6, 0.5], np.float32) * 0.6   # 湿血高光
        k = pulse(t, self.T_XUE, 0.12) * (t >= self.T_XUE)
        fr = cam(fr, 1.0 + 0.04 * eio(u) + 0.06 * k, 0, 40 - 80 * eio(u))
        return fr, (3 if k > 0.5 else 0)


# =====================================================================================
# P07 MS 低机位仰拍：鬼屠仰头，雷云旋转、云缝预亮；「我」「不信」毛草错落
class P07(Shot):
    def __init__(self):
        self.sp = spr('S023/look_up_low')
        self.tex = K.tile(1024, 907, 4, 6)
        T.warm('我不信', 'cao', 200); T.warm('不', 'xing', 150)
        import fx2; self.fx2 = fx2

    def sky(self, t, rot=0.0, seed_off=0):
        x, y = K.grid()
        cx, cy = 960, -200
        ang = np.arctan2(y - cy, x - cx) + t * 0.08 + rot
        rr = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        u_ = (ang * 160) % 1024; v_ = (rr * 0.6 - t * 30) % 1024
        n = self.tex[v_.astype(np.int32) % 1024, u_.astype(np.int32) % 1024]
        n = cv2.GaussianBlur(n, (0, 0), 2)
        l = 0.03 + 0.16 * n ** 1.6
        return np.stack([l * 0.95, l * 0.98, l * 1.08], -1).astype(np.float32)

    def render(self, t):
        u = self.u(t)
        fr = self.sky(t)
        fl = self.fx2.cloud_flash(fr, t, t0=50.95, center=(1350, 250), radius=600, seed=7, intensity=0.8)
        fr = fl if isinstance(fl, np.ndarray) else fl[0]
        crane = -60 + 90 * eio(u)
        fr, _ = put(fr, self.sp, t, 1700, (820, 1080 + 1050 + crane), rim=dict(col=(0.75, 0.82, 1.0), amt=2.2, dir=(0.4, -1.0)),
                    grade=GR_COLD, wind_amp=6, shade=(400, 1500, 0.2, 700, 0.3))
        fr = BK.rain(fr, t, 971, amt=0.42, n=650, angle=-8, speed=2500)
        pr = tp(10, [0, 1, 2], t, 0.18)
        fr = T.scatter_stack(fr, '我不信', pr, places=[dict(ch='我', x=1400, y=330, size=190, rot=-5, font='cao', idx=0, emph=False),
                                                         dict(ch='不', x=1560, y=540, size=150, rot=6, font='xing', idx=1, emph=True),
                                                         dict(ch='信', x=1690, y=720, size=170, rot=-4, font='cao', idx=2, emph=True)],
                             color='white', emph_color=(0.84, 0.10, 0.07), t_local=u, style_kw=dict(shadow=0.75, glow=0.12))
        fr = cam(fr, 1.04 - 0.04 * eio(u), 0, 0, -4 + 4 * eio(u))
        return fr, 0


# =====================================================================================
# P08 ELS 仰天：云隙负形构成「天」（宋体），52.14 闪电劈亮；朱红干笔划掉
class P08(Shot):
    T_TIAN = V(52.14)
    def __init__(self):
        self.p7 = P07()
        self.m = T.glyph_mask('天', 'serif_black', 760, 960, 520) if hasattr(T, 'glyph_mask') else None
        import fx2; self.fx2 = fx2
        self.bolt = fx2.Lightning(52, p0=(1300, 120), p1=(980, 560), branches=6)

    def render(self, t):
        u = self.u(t)
        fr = self.p7.sky(t * 1.3, rot=1.2)
        m = cv2.GaussianBlur(self.m.astype(np.float32), (0, 0), 7)
        nz = cv2.resize(K.fbm(H // 4, W // 4, 81, base=6, octaves=4), (W, H))
        m = np.clip(m * (0.8 + 0.4 * nz), 0, 1)
        # 第五棒：去掉朱红一笔划掉（≈副歌一 S042）→ 闪电沿劈线把云隙「天」劈成两半、两半错开漂离
        ps = eout(clamp01((t - (self.T_TIAN + 0.04)) / 0.45), 2)
        if ps > 0:
            x, y = K.grid()
            a = np.array([1300.0, 120.0]); b = np.array([980.0, 560.0]); d = (b - a) / np.linalg.norm(b - a); nn = np.array([-d[1], d[0]])
            side = ((x - a[0]) * nn[0] + (y - a[1]) * nn[1])
            jag = (cv2.resize(K.fbm(H // 8, W // 8, 82, base=4, octaves=3), (W, H)) - 0.5) * 60
            mL = m * sstep(10, -10, side + jag); mR = m * sstep(-10, 10, side + jag)
            off = 70 * ps
            ML = np.float32([[1, 0, -nn[0] * off - d[0] * off * 0.3], [0, 1, -nn[1] * off + 18 * ps]])
            MR = np.float32([[1, 0, nn[0] * off + d[0] * off * 0.3], [0, 1, nn[1] * off - 18 * ps]])
            RL = cv2.getRotationMatrix2D((800, 520), 4 * ps, 1.0); RR = cv2.getRotationMatrix2D((1100, 520), -3 * ps, 1.0)
            mL = cv2.warpAffine(cv2.warpAffine(mL, RL, (W, H)), ML, (W, H)); mR = cv2.warpAffine(cv2.warpAffine(mR, RR, (W, H)), MR, (W, H))
            m = np.clip(mL + mR, 0, 1)
            crack = np.exp(-((side + jag) / 6) ** 2) * self.m.astype(np.float32) * (1 - ps) * 2.0
            fr = fr + cv2.GaussianBlur(crack, (0, 0), 3)[..., None] * np.array([0.9, 0.95, 1.0], np.float32)
        lit = 0.25 + 0.75 * clamp01((t - (self.T_TIAN - 0.05)) / 0.06) * (0.6 + 0.4 * math.exp(-(t - self.T_TIAN) / 0.4) if t > self.T_TIAN else 1.0)
        glowc = np.array([0.85, 0.88, 1.0], np.float32)
        fr = fr * (1 - m[..., None] * 0.7) + m[..., None] * glowc * 0.75 * lit
        fr += cv2.GaussianBlur(m, (0, 0), 40)[..., None] * glowc * 0.25 * lit
        if t >= self.T_TIAN - 0.05:
            fr = self.fx2.Lightning.draw(self.bolt, fr, t, self.T_TIAN, intensity=1.0)
        # 「不信」（52.38 / 52.58）：楷书白字，从劈开的裂缝下方升起
        pr = tp(10, [4, 5], t, 0.16)
        fr = T.scatter_stack(fr, '不信', pr, places=[dict(ch='不', x=1480, y=760, size=130, rot=-4, font='kai', idx=0, emph=False),
                                                       dict(ch='信', x=1630, y=800, size=150, rot=3, font='kai', idx=1, emph=True)],
                             color='white', emph_color=(0.86, 0.12, 0.08), t_local=u, style_kw=dict(shadow=0.8, glow=0.12))
        z = 1.0 + 0.06 * eio(u)
        fr = cam(fr, z, 0, 30 - 60 * eio(u), 3 * eio(u))
        return fr, (3 if abs(t - self.T_TIAN) < 0.04 else 0)


# =====================================================================================
# P09 MCU：鬼屠握拳（fist）；「命」朱印从背后逼近；53.17 刀柄回撞（pommel_thrust），印碎
class P09(Shot):
    """第五棒：「命」补出画（评审 P0：f1576–1606 从未出画——原印在人物正后方被拳头整块挡住）。
    构图改左右分：左 = 朱红「命」阴文大印（52.84 字头砸进画面，可读停留 ~10 帧），右 = 鬼屠握拳；53.13 刀柄回撞，印从右往左碎开。
    撞击帧不再整屏朱红（P2：f1594 红色糊团），改为撞点冲击环 + 色散。"""
    T_HIT = V(53.17)
    T_MING = V(52.84)
    SC = (610, 470)
    def __init__(self):
        self.a = spr('S024/fist'); self.b = spr('S024/pommel_thrust')
        self.bg = BK.dark_bg(909, 0.02, 0.06, tint=(1.1, 1.0, 1.0))
        self.seal = T.seal_layer('命', self.SC[0], self.SC[1], 470, style='yin', rot=-4, seed=9)
        T.warm('不信', 'kai', 120)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        x, y = K.grid()
        fr += np.exp(-(((x - 700) / 700) ** 2 + ((y - 450) / 420) ** 2))[..., None] * RED * 0.22
        # 人物（右）
        if t < self.T_HIT:
            fr, _ = put_at(fr, self.a, t, (0.5, 0.42), (1320, 540), 2000, grade=GR_COLD, rim=dict(col=(1.0, 0.45, 0.35), amt=1.8, dir=(-1.0, -0.4)),
                           wind_amp=4, shade=(700, 1800, 0.25, 700, 0.35))
        else:
            k = clamp01((t - self.T_HIT) / 0.08)
            fr, _ = put_at(fr, self.b, t, (0.5, 0.45), (1340, 570), 2100 * (1.05 - 0.05 * k), grade=GR_COLD,
                           rim=dict(col=(1.0, 0.45, 0.35), amt=2.0, dir=(-1.0, -0.4)), wind_amp=6, mblur=(-50 * (1 - k), 0), shade=(700, 1800, 0.2, 700, 0.3))
        # 「命」印：字头砸入（2.2→1.0 缩放 + 落地抖）→ 撞碎
        if t < self.T_HIT:
            q = clamp01((t - (self.T_MING - 0.10)) / 0.10)
            if q > 0:
                s = 1.0 + 1.2 * (1 - eout(q, 3))
                M = cv2.getRotationMatrix2D(self.SC, 0, s)
                L = T.Layer(); L.A = cv2.warpAffine(self.seal.A, M, (W, H)); L.C = cv2.warpAffine(self.seal.C, M, (W, H)); L.bb = [0, 0, W, H]
                fr = fr * (1 - 0.6 * K.blur_ds(L.A, 40)[..., None])
                fr = T.compose(fr, L, shadow=0.6, glow=0.15, opacity=min(1.0, q * 1.6))
        else:
            q = clamp01((t - self.T_HIT) / 0.5)
            L = T.shatter_layer(self.seal, q, impact=(self.SC[0] + 230, self.SC[1]), n=80, seed=9, power=1.4)
            fr = T.compose(fr, L, shadow=0.4)
            fr = K.sparks(fr, t, 991, (self.SC[0] + 230, self.SC[1]), n=60, life=0.5, speed=(400, 1200), dirc=(-1, -0.3), spread=1.2, grav=900, area=(60, 120), amt=1.0)
            ring = clamp01((t - self.T_HIT) / 0.18)
            if ring < 1:
                d = np.sqrt((x - self.SC[0] - 230) ** 2 + (y - self.SC[1]) ** 2)
                fr = fr + (np.exp(-((d - 60 - 700 * eout(ring, 2)) / 14) ** 2) * (1 - ring))[..., None] * np.array([1.0, 0.55, 0.42], np.float32) * 0.9
        pr = tp(10, [7, 8], t, 0.18)
        fr = T.scatter_stack(fr, '不信', pr, places=[dict(ch='不', x=1700, y=250, size=110, rot=-6, font='kai', idx=0, emph=False),
                                                       dict(ch='信', x=1760, y=400, size=130, rot=5, font='kai', idx=1, emph=False)],
                             color='white', t_local=u, style_kw=dict(shadow=0.75, glow=0.1))
        k2 = pulse(t, self.T_MING, 0.1) * (t >= self.T_MING) + pulse(t, self.T_HIT, 0.12) * (t >= self.T_HIT)
        dx, dy, dr = shake(t, 6 + 14 * k2, 8, 9)
        fr = cam(fr, 1.0 + 0.05 * k2 + 0.03 * eio(u), dx, dy, dr)
        if self.T_HIT <= t < self.T_HIT + 2 / 30 - 1e-3:                      # 撞击：色散错位（无整屏色闪）
            a_ = 14 if t < self.T_HIT + 1 / 30 else 6
            fr = np.stack([np.roll(fr[..., 0], a_, 1), fr[..., 1], np.roll(fr[..., 2], -a_, 1)], -1)
        return fr, (4 if k2 > 0.5 else 0)


# =====================================================================================
# 铅字块（P10/P11 共用）：金属活字，宋体浮凸
def type_block(ch, size=220, seed=0, face=(0.42, 0.42, 0.45), gold=0.0):
    """返回 (rgb, A)：正方形铅字顶面（含倒角、磨损、浮凸字面）"""
    s = size
    rgb = np.zeros((s, s, 3), np.float32); A = np.zeros((s, s), np.float32)
    r = np.random.default_rng(seed)
    nz = cv2.resize(r.random((s // 6, s // 6)).astype(np.float32), (s, s))
    base = np.array(face, np.float32) * (0.75 + 0.3 * nz[..., None])
    rgb[:] = base * 0.45
    A[4:-4, 4:-4] = 1
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    ed = np.minimum(np.minimum(xx, s - xx), np.minimum(yy, s - yy))
    bev = np.clip(1 - ed / 14, 0, 1)
    rgb += (bev * ((xx < yy) * 0.25 - 0.1))[..., None]
    g = T.glyph(ch, 'serif_black', int(s * 0.74), False)      # 方形画布 ≈1.5×size、字心居中 → 居中裁 s×s
    gh, gw = g.shape
    gm = np.zeros((s, s), np.float32)
    if gh >= s:
        o = (gh - s) // 2; gm[:] = g[o:o + s, o:o + s]
    else:
        o = (s - gh) // 2; gm[o:o + gh, o:o + gw] = g
    hl = np.clip(gm - np.roll(np.roll(gm, 3, 0), 3, 1), 0, 1)
    sd = np.clip(gm - np.roll(np.roll(gm, -3, 0), -3, 1), 0, 1)
    col = np.array(face, np.float32) * 1.6 * (1 - gold) + GOLD * 1.1 * gold
    rgb = rgb * (1 - gm[..., None]) + gm[..., None] * col * (0.8 + 0.25 * nz[..., None])
    rgb = rgb + hl[..., None] * 0.45 - sd[..., None] * 0.25
    return np.clip(rgb, 0, 2).astype(np.float32), A


def tip_blade():
    """真实刀身横置（刀尖在右），尖端按三角形切出"""
    F, A = BK.blade_strip()
    h, w = A.shape
    A = A.copy()
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    L = 260
    tipm = np.clip(((w - xx) / L) * h - np.abs(yy - h * 0.05) * 1.0, 0, 1)   # 背直、刃弧（单刃刀尖）
    A = A * np.where(xx > w - L, np.clip(tipm, 0, 1), 1.0)
    return F, A


class P10(Shot):
    T_LI, T_SUO = V(54.0), V(54.18)
    def __init__(self):
        r = np.random.default_rng(910)
        S = 230
        canvas = np.zeros((1500, 2800, 3), np.float32) + 0.02
        self.pos = {}
        for row in range(6):
            for col in range(11):
                cx, cy = 140 + col * (S + 10), 160 + row * (S + 10)
                main = (row == 3 and 3 <= col <= 6)
                ch = '理所应当'[col - 3] if main else DOCT[int(r.integers(len(DOCT)))]
                if main: self.pos[ch] = (cx, cy)
                rgb, A = type_block(ch, S, seed=row * 20 + col, gold=0.35 if main else 0.0)
                canvas[cy - S // 2:cy + S // 2, cx - S // 2:cx + S // 2] = rgb * (1.0 if main else 0.75)
        self.canvas = canvas; self.S = S
        self.q = np.float32([[-300, -60], [2350, -160], [2050, 1240], [-80, 1180]])     # 斜俯透视
        self.Mq = cv2.getPerspectiveTransform(np.float32([[0, 0], [2800, 0], [2800, 1500], [0, 1500]]), self.q)
        self.blk = {c: type_block(c, S, seed=99 + i, gold=0.35) for i, c in enumerate('理所')}
        self.blade = tip_blade()
        T.warm('不信谁的', 'kai', 110)

    def proj(self, p):
        v = self.Mq @ np.array([p[0], p[1], 1.0]); return v[:2] / v[2]

    def render(self, t):
        u = self.u(t)
        cv_ = self.canvas.copy()
        S = self.S
        flying = []
        for ch, th in (('理', self.T_LI), ('所', self.T_SUO)):
            if t >= th - 0.02:
                cx, cy = self.pos[ch]
                cv_[cy - S // 2:cy + S // 2, cx - S // 2:cx + S // 2] = 0.01      # 空槽
                flying.append((ch, th))
        fr = cv2.warpPerspective(cv_, self.Mq, (W, H), flags=cv2.INTER_LINEAR)
        x, y = K.grid()
        fr = fr * (0.35 + 0.9 * np.exp(-(((x - 1100) / 800) ** 2 + ((y - 450) / 450) ** 2)))[..., None] * np.array([0.95, 0.98, 1.06], np.float32)
        # 飞起的铅字：抛物线 + 旋转 + 动态模糊
        for ch, th in flying:
            q = t - th
            p0 = self.proj(self.pos[ch])
            px = p0[0] - 900 * q; py = p0[1] - 1400 * q + 1800 * q * q
            rgb, A = self.blk[ch]
            sc = 0.82 * (1 + 0.8 * q)
            M = cv2.getRotationMatrix2D((S / 2, S / 2), -q * 110, sc); M[0, 2] += px - S / 2; M[1, 2] += py - S / 2   # 第五棒：不翻到倒置
            fr, _ = BK.paste_rgba(fr, rgb * 1.3, A, M)
        # 刀尖：从右侧探入，挑「理」「所」
        F, A = self.blade
        tgt = self.proj(self.pos['理']) if t < self.T_LI + 0.05 else self.proj(self.pos['所'])
        e = eout(clamp01((t - self.t0) / 0.25), 3)
        flick = pulse(t, self.T_LI, 0.08) * (t >= self.T_LI) + pulse(t, self.T_SUO, 0.08) * (t >= self.T_SUO)
        tip = np.array([tgt[0] + 40, tgt[1] + 30 - 120 * flick]) + np.array([900, 0]) * (1 - e)
        base = tip + np.array([1900, 280 + 200 * flick])
        M = BK.M_line(A.shape[1], A.shape[0], base, tip, 150)
        fr, Aw = BK.paste_rgba(fr, F * 1.15, A, M)
        fr += cv2.GaussianBlur(Aw, (0, 0), 20)[..., None] * np.array([0.6, 0.7, 0.9], np.float32) * 0.15 * (1 + 2 * flick)
        if flick > 0.3:
            fr = K.sparks(fr, t, 1010, tuple(tip.astype(int)), n=40, life=0.35, speed=(300, 900), dirc=(-1, -0.6), spread=0.9, grav=900, area=(20, 20), amt=1.0)
        pr = tp(10, [9, 10], t, 0.18)
        fr = T.scatter_stack(fr, '谁的', pr, places=[dict(ch='谁', x=250, y=260, size=130, rot=-6, font='kai', idx=0, emph=False),
                                                       dict(ch='的', x=380, y=400, size=110, rot=4, font='kai', idx=1, emph=False)],
                             color='white', t_local=u, style_kw=dict(shadow=0.8))
        fr = cam(fr, 1.04, 60 - 160 * eio(u), 0, -1.5)
        return fr, (3 if flick > 0.6 else 0)


# =====================================================================================
# P11 微距慢放：「应」「当」两块铅字在空中翻滚，55.1「当」落地弹起溅火星
class P11(Shot):
    T_DANG = V(55.10)
    def __init__(self):
        self.blk = {c: type_block(c, 300, seed=120 + i, gold=0.35) for i, c in enumerate('应当')}
        self.bok = np.random.default_rng(911).uniform(0, 1, (40, 4))
        # 第三棒：加信息量——后景 = 虚焦的铅字盘（四个空槽 = 理所应当已被挑走）；地面 = 生死簿纸面；散落的铅字
        p10 = P10()
        cv_ = p10.canvas.copy(); S = p10.S
        for ch in '理所应当':
            cx, cy = p10.pos[ch]; cv_[cy - S // 2:cy + S // 2, cx - S // 2:cx + S // 2] = 0.01
        q = np.float32([[-500, -260], [2500, -300], [2250, 820], [-300, 840]])
        M = cv2.getPerspectiveTransform(np.float32([[0, 0], [2800, 0], [2800, 1500], [0, 1500]]), q)
        tray = np.nan_to_num(cv2.warpPerspective(np.ascontiguousarray(cv_), M, (W, H)))
        x, y = K.grid()
        tray = cv2.GaussianBlur(tray, (0, 0), 7) * (0.35 + 0.6 * np.exp(-(((x - 1000) / 700) ** 2 + ((y - 380) / 300) ** 2)))[..., None]
        floor = sstep(770, 800, y)
        pg = BK.paper(912, (0.62, 0.58, 0.52)) * 0.55          # 第五棒：地面去人名（名单母题 ≤2）
        Mf = cv2.getPerspectiveTransform(np.float32([[0, 760], [W, 760], [W, H], [0, H]]), np.float32([[300, 790], [1620, 790], [2600, 1180], [-700, 1180]]))
        pg = cv2.warpPerspective(pg, Mf, (W, H), borderMode=cv2.BORDER_REFLECT)
        self.bg = tray * (1 - floor[..., None]) + pg * floor[..., None] * (0.5 + 0.6 * np.exp(-((x - 1060) / 700) ** 2))[..., None]
        # 散落铅字（地面前景，虚焦）
        r = np.random.default_rng(913)
        for k in range(7):
            ch = DOCT[int(r.integers(len(DOCT)))]
            rgb, A = type_block(ch, 150, seed=300 + k)
            px, py = r.uniform(100, 1800), r.uniform(860, 1000)
            if 850 < px < 1250: px += 500
            Mk = cv2.getRotationMatrix2D((75, 75), r.uniform(-40, 40), 1.0); Mk[1] *= 0.45
            Mk[0, 2] += px - 75; Mk[1, 2] += py - 34
            self.bg, _ = BK.paste_rgba(self.bg, rgb * 0.8, A, Mk)
        self.bg = np.nan_to_num(self.bg.astype(np.float32), nan=0.0, posinf=1.0, neginf=0.0)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        x, y = K.grid()
        # 「当」落地处在纸上留下的朱红压印（55.1 之后逐渐显影）
        if t >= self.T_DANG:
            Li = T.Layer(); T.place(Li, '当', 1060, 790, 220, color='red', fname='serif_black', sy=0.42, alpha=min(1, (t - self.T_DANG) / 0.15) * 0.85)
            fr = fr * (1 - Li.A[..., None] * 0.8) + Li.A[..., None] * np.array([0.55, 0.05, 0.03], np.float32)
        # 背景虚焦光斑（冷/暖）
        Lb = np.zeros((H // 4, W // 4), np.float32)
        for bx, by, br, ph in self.bok:
            cv2.circle(Lb, (int(bx * W / 4), int(by * 180 + 20)), int(6 + br * 14), 0.25 + 0.2 * math.sin(t * 2 + ph * 6), -1, cv2.LINE_AA)
        fr += cv2.resize(cv2.GaussianBlur(Lb, (0, 0), 3), (W, H))[..., None] * np.array([0.6, 0.65, 0.8], np.float32)
        ts = self.t0 + (t - self.t0) * 0.45                   # 慢放
        for ch, (x0, y0, vx, vy, spin, land) in (('应', (700, 300, 160, -120, 30, None)), ('当', (1150, 260, -90, -60, -35, self.T_DANG))):
            rgb, A = self.blk[ch]
            q = ts - self.t0
            if land is None:
                px, py = x0 + vx * q * 2, y0 + vy * q * 2 + 260 * q * q * 4
                ang = spin * q * 2; sy = 0.55 + 0.45 * abs(math.cos(q * 3.0))
            else:
                tl = (t - self.t0) / (self.T_DANG - self.t0)
                if t < self.T_DANG:
                    px = x0 + vx * tl; py = y0 + (640 - y0) * tl ** 2; ang = spin * tl; sy = 0.55 + 0.45 * abs(math.cos(tl * 3.0))
                else:
                    b = t - self.T_DANG
                    px = x0 + vx + 60 * b; py = 640 - 140 * math.sin(min(math.pi, b * 9)) * math.exp(-b * 3); ang = spin + 20 * math.sin(b * 12) * math.exp(-b * 4); sy = 0.9
            M = cv2.getRotationMatrix2D((150, 150), ang, 0.9); M[1] *= sy
            M[0, 2] += px - 150; M[1, 2] += py - 150 * sy
            Mb = M.copy()
            fr, Aw = BK.paste_rgba(fr, rgb * 1.35, A, Mb)
            fr += (cv2.GaussianBlur(Aw, (0, 0), 3) - Aw).clip(0, 1)[..., None] * np.array([0.8, 0.85, 1.0], np.float32) * 0.6
        if t >= self.T_DANG:
            fr = K.sparks(fr, t, 1111, (1060, 760), n=70, life=0.5, speed=(300, 900), dirc=(0, -1), spread=1.3, grav=1200, area=(120, 10), amt=1.1)
        # 刃光掠过（前景斜线）
        q = clamp01((t - (self.t0 + 0.15)) / 0.25)
        if 0 < q < 1:
            fr = T._slash_light(fr, (960, 420), np.array([0.94, -0.34]), q, 2400)
        k = pulse(t, self.T_DANG, 0.1) * (t >= self.T_DANG)
        dx, dy, dr = shake(t, 10 * k, 12, 11)
        fr = cam(fr, 1.0 + 0.06 * eio(u) + 0.04 * k, dx - 40 * eio(u), dy, dr)
        return fr, (3 if k > 0.5 else 0)


# =====================================================================================
# P12 MCU：鬼屠竖刀当面，刀身一分为二的脸（blade_face）；「只信这柄」马善政竖排，逐字光洇
class P12(Shot):
    def __init__(self):
        self.sp = spr('B_r4/blade_face2')                       # 第七棒：束发版（全片造型统一）
        self.bg = BK.dark_bg(912, 0.015, 0.05)
        T.warm('只信这柄', 'kai', 96)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        x, y = K.grid()
        fr += np.exp(-(((x - 960) / 500) ** 2 + ((y - 380) / 300) ** 2))[..., None] * np.array([0.10, 0.11, 0.14], np.float32)
        fr, _ = put_at(fr, self.sp, t, (0.5, 0.36), (960, 470), 2350, grade=dict(expo=0.82, sat=0.6, tint=(0.92, 0.96, 1.05), lift=0.0, gamma=1.12),
                       rim=dict(col=(0.75, 0.82, 1.0), amt=2.2, dir=(-0.9, -0.4)), wind_amp=5, shade=(1100, 1900, 0.25, 760, 0.4))
        # 刀刃上一线寒光自上而下
        q = clamp01((t - self.t0 - 0.1) / 0.6)
        yy = 120 + 600 * eio(q)
        g = np.exp(-(((x - 960) / 26) ** 2 + ((y - yy) / 60) ** 2))
        fr += g[..., None] * np.array([0.9, 0.95, 1.0], np.float32) * 0.8 * (1 - q * 0.5)
        fr = K.sparks(fr, t, 1212, (960, 980), n=30, life=1.2, speed=(60, 200), dirc=(0, -1), spread=0.8, grav=-60, area=(900, 40), amt=0.6)
        pr = tp(11, [0, 1, 2, 3], t, 0.2)
        fr = T.ink_bleed_in(fr, '只信这柄', pr, places=[dict(ch=c, x=1420, y=300 + i * 130, size=104, rot=0, font='kai', idx=i, emph=False)
                                                        for i, c in enumerate('只信这柄')],
                            color='white', style_kw=dict(shadow=0.85, glow=0.12))
        fr = cam(fr, 1.0 + 0.08 * eio(u), 0, 0)
        return fr, 0


# =====================================================================================
# P13 CU：真实刀身横贯，56.5「刀」字头白刃光扫过，刀身内部开始透出炭火红；「刀」志莽行书被刀光斩出
def heat_blade(fr, t, p0, p1, width, heat, shine=0.0, seed=0, haze=0.0):
    F, A = tip_blade()
    M = BK.M_line(A.shape[1], A.shape[0], p0, p1, width)
    Fw = cv2.warpAffine(F, M, (W, H), flags=cv2.INTER_LINEAR)
    Aw = cv2.warpAffine(A, M, (W, H), flags=cv2.INTER_LINEAR)
    lum = Fw.mean(-1, keepdims=True)
    # 炭火：内部透红（亮处更红），刃口一侧更热
    x, y = K.grid()
    d = np.array(p1, float) - np.array(p0, float); d /= np.linalg.norm(d); n = np.array([-d[1], d[0]])
    sd = ((x - p0[0]) * n[0] + (y - p0[1]) * n[1]) / (width / 2)           # -1 背 … +1 刃
    nz = cv2.resize(K.fbm(H // 8, W // 8, seed, base=6, octaves=4), (W, H))
    hz = np.clip(heat * (0.55 + 0.45 * np.clip(sd, -1, 1)) * (0.7 + 0.6 * nz) * (0.9 + 0.1 * math.sin(t * 13)), 0, 1.4)[..., None]
    col = Fw * (1 - 0.6 * hz.clip(0, 1)) + hz * (RED * 1.3 + GOLD * 0.55 * hz) * (0.5 + lum)
    if shine > 0:
        col = col + shine
    fr = fr * (1 - Aw[..., None]) + col * Aw[..., None]
    fr += cv2.GaussianBlur(Aw * hz[..., 0], (0, 0), 30)[..., None] * RED * 0.6 * heat
    return fr, Aw, M


def spt(sp, src, dst, width_px, n):
    """精灵内归一化点 n → 屏幕坐标（put_at 同一映射，rot=0）"""
    s = width_px / sp.w
    return np.array([dst[0] + (n[0] - src[0]) * sp.w * s, dst[1] + (n[1] - src[1]) * sp.h * s])


def blade_heat(fr, Aw, g, tip, half_w, heat, front=1.0, t=0.0, seed=0):
    """第五棒：生图刀身「烧红」——屏幕上刀身带（护手 g → 刀尖 tip，半宽 half_w）× 精灵 alpha；
    front 0..1 = 热从刀尖往护手推进的位置（1 = 全刀身烧透）。刃口一侧更热，内部透出炭火纹。"""
    x, y = K.grid()
    g = np.asarray(g, float); tip = np.asarray(tip, float)
    d = tip - g; L = np.linalg.norm(d); d /= L; n = np.array([-d[1], d[0]])
    along = ((x - g[0]) * d[0] + (y - g[1]) * d[1]) / L           # 0 护手 … 1 刀尖
    side = ((x - g[0]) * n[0] + (y - g[1]) * n[1]) / half_w
    band = sstep(1.25, 0.85, np.abs(side)) * sstep(0.02, 0.08, along) * Aw
    nz = cv2.resize(K.fbm(H // 8, W // 8, seed, base=6, octaves=4), (W, H))
    reach = sstep(1 - front - 0.15, 1 - front + 0.05, along)        # 从刀尖往下烧
    hz = np.clip(heat * band * reach * (0.65 + 0.5 * nz) * (0.92 + 0.08 * math.sin(t * 13)), 0, 1.3)[..., None]
    lum = fr.mean(-1, keepdims=True)
    col = fr * (1 - 0.7 * hz.clip(0, 1)) + hz * (RED * 1.35 + GOLD * 0.7 * hz) * (0.55 + lum)
    out = fr * (1 - band[..., None]) + col * band[..., None]
    out += cv2.GaussianBlur((band * hz[..., 0]).astype(np.float32), (0, 0), 28)[..., None] * RED * 0.9 * heat
    out += cv2.GaussianBlur((band * hz[..., 0]).astype(np.float32), (0, 0), 90)[..., None] * RED * 0.35 * heat
    return out, band * reach


def heat_haze(fr, t, tex, amp):
    x, y = K.grid()
    n = cv2.resize(K.tile_crop(tex, 0, -t * 160, H // 8, W // 8), (W, H))
    return cv2.remap(fr, (x + (n - 0.5) * amp).astype(np.float32), (y + (n - 0.5) * amp * 1.6).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


class P13(Shot):
    """第五棒重做（评审 P0：P13/P14 连续 4.5s 横刀特写 ≈ 副歌一 S028）：
    MS 低机位——鬼屠自左下向右上一记撩斩（生图 slash_up），56.50「刀」字头刀弧白光扫过，「刀」被弧光斩开；
    后景雷云被刀弧照红，地面薄雾。构图对角线（左下→右上），与 P12 竖刀 / P14 斜刀特写交替。"""
    T_DAO = V(56.50)
    SRC, DST, WPX = (0.45, 0.97), (760, 1000), 1480
    def __init__(self):
        self.sp = spr('slash_up')
        self.p7 = P07()
        T.warm('刀', 'xing', 340); T.warm('还', 'kai', 110)
        self.tip = spt(self.sp, self.SRC, self.DST, self.WPX, (0.735, 0.035))
        self.sh = spt(self.sp, self.SRC, self.DST, self.WPX, (0.40, 0.20))

    def render(self, t):
        u = self.u(t)
        fr = self.p7.sky(t * 1.1, rot=2.4) * 0.9
        x, y = K.grid()
        ka = clamp01((t - (self.T_DAO - 0.12)) / 0.16)                # 刀弧扫过进度
        glow = (1 - clamp01((t - self.T_DAO) / 0.5)) * (ka > 0)
        fr += np.exp(-(((x - self.tip[0]) / 700) ** 2 + ((y - self.tip[1] - 100) / 450) ** 2))[..., None] * (RED * 0.35 + 0.15) * (0.3 + 0.7 * glow)
        fr += sstep(700, 1000, y)[..., None] * np.array([0.07, 0.03, 0.03], np.float32)       # 地面暗红反光
        fr = K.fog(fr, t, 1301, amt=0.22, y0=0.72, y1=1.0)
        fr, Aw = put_at(fr, self.sp, t, self.SRC, self.DST, self.WPX, grade=GR_COLD,
                        rim=dict(col=(1.0, 0.55, 0.40), amt=2.2, dir=(0.7, -0.7)), wind_amp=6, shade=(400, 1500, 0.15, 600, 0.35))
        # 刀弧：撩斩轨迹（二次贝塞尔：左下地面 → 左上弓起 → 右上刀尖），细→粗，白热 → 朱红余辉
        if ka > 0:
            P0 = spt(self.sp, self.SRC, self.DST, self.WPX, (0.12, 0.80)); C = spt(self.sp, self.SRC, self.DST, self.WPX, (0.22, 0.02))
            P2 = self.tip
            m = np.zeros((H // 2, W // 2), np.float32)
            N = 28; e = eout(ka, 2)
            pts = [((1 - q) ** 2 * P0 + 2 * (1 - q) * q * C + q * q * P2) for q in np.linspace(0, e, N + 1)]
            for k in range(N):
                w_ = (k + 1) / N
                cv2.line(m, tuple((pts[k] / 2).astype(int)), tuple((pts[k + 1] / 2).astype(int)), 0.2 + 0.8 * w_, max(1, int(2 + 9 * w_)), cv2.LINE_AA)
            m = cv2.resize(m, (W, H)) * (1 - 0.8 * clamp01((t - self.T_DAO) / 0.45))
            fr = fr + cv2.GaussianBlur(m, (0, 0), 2)[..., None] * np.array([1.0, 0.92, 0.85], np.float32) * 1.2 \
                 + cv2.GaussianBlur(m, (0, 0), 18)[..., None] * (RED * 1.2 + 0.1)
        # 「刀」被刀弧斩出（右下，朱红）
        pd = clamp01((t - (self.T_DAO - 0.08)) / 0.2)
        if pd > 0:
            P = [dict(ch='刀', x=1480, y=600, size=360, rot=-8, font='xing', idx=0, emph=True)]
            fr = T.slash_cut(fr, '刀', clamp01(0.2 + pd * 0.25 + (t - self.T_DAO) * 0.3), places=P, color='white', emph=('刀',),
                             emph_color=(0.88, 0.12, 0.08), cut_at=0.25, slide=0.12, angle=35, appear=0.15)
        ph = tp(11, [5], t, 0.18)[0]
        if ph > 0:
            fr = T.ink_bleed_in(fr, '还', [ph], places=[dict(ch='还', x=1700, y=790, size=110, rot=0, font='kai', idx=0, emph=False)], color='white',
                                style_kw=dict(shadow=0.8))
        fr = K.sparks(fr, t, 1313, tuple(self.tip.astype(int)), n=50, life=0.7, speed=(150, 600), dirc=(0.5, -1), spread=1.0, grav=300, area=(60, 60), amt=0.8 * glow + 0.2)
        fr = BK.rain(fr, t, 1302, amt=0.25, n=350, angle=-6)
        k = pulse(t, self.T_DAO, 0.1) * (t >= self.T_DAO)
        dx, dy, dr = shake(t, 14 * k, 10, 13)
        fr = cam(fr, 1.0 + 0.07 * eio(u) + 0.04 * k, dx, dy, dr - 2 + 3 * eio(u), center=(900, 600))
        return fr, (4 if k > 0.5 else 0)


class P14(Shot):
    """第五棒重做：CU 斜构图——握刀的手（生图 hand_hilt），刀身从护手斜向右上出画；
    57.48「滚」热从刀尖往护手烧下来，57.76「烫」整段刀身通红、火星剥落、热浪扭曲；「滚烫」火烧显字落在刀身左侧暗部（被刀的热光照亮）。"""
    SRC, DST, WPX = (0.60, 0.55), (860, 640), 2250
    def __init__(self):
        self.sp = spr_feather('hand_hilt', left=0.30, bottom=0.22, top=0.0)
        self.bg = BK.dark_bg(914, 0.01, 0.035, tint=(1.2, 1.0, 0.95))
        self.tex = K.tile(512, 914, 6, 4)
        T.warm('滚烫', 'xing', 230)

    def render(self, t):
        u = self.u(t)
        z = 1.0 + 0.10 * eio(u)
        dst = (self.DST[0] - 40 * eio(u), self.DST[1] + 30 * eio(u))
        wpx = self.WPX * z
        fr = self.bg.copy()
        x, y = K.grid()
        heat = 0.35 + 0.65 * clamp01((t - V(57.48) + 0.1) / 0.4)
        front = clamp01((t - (V(57.48) - 0.15)) / 0.45)
        g = spt(self.sp, self.SRC, dst, wpx, (0.69, 0.36)); tip = spt(self.sp, self.SRC, dst, wpx, (0.86, -0.06))
        fr += np.exp(-(((x - (g[0] + tip[0]) / 2) / 600) ** 2 + ((y - (g[1] + tip[1]) / 2) / 500) ** 2))[..., None] * RED * 0.18 * heat
        fr, Aw = put_at(fr, self.sp, t, self.SRC, dst, wpx, grade=dict(expo=0.78, sat=0.85, tint=(1.10, 0.94, 0.84), lift=0.0, gamma=1.12),
                        rim=dict(col=(1.0, 0.5, 0.35), amt=2.4, dir=(0.8, -0.6)), wind_amp=0, breathe=0.0, shade=None, wrap=0.3)
        fr, band = blade_heat(fr, Aw, g, tip, 0.045 * wpx, heat, front, t, seed=14)
        # 手背被刀的热光照亮（暖红轮廓）
        fr += (Aw * np.exp(-(((x - g[0]) / 380) ** 2 + ((y - g[1]) / 300) ** 2)))[..., None] * RED * 0.25 * heat
        pb = clamp01((t - (V(CT(11, 6)) - 0.25)) / 0.7)
        if pb > 0:
            P = [dict(ch=ch, x=470 + i * 230, y=300 + i * 40, size=220, rot=-8, font='xing', idx=i, emph=False) for i, ch in enumerate('滚烫')]
            fr = T.burn_in(fr, '滚烫', pb, places=P, color='gold', embers=120, seed=14, style_kw=dict(shadow=0.5, glow=0.5))
        mid = ((g + tip) / 2).astype(int)
        fr = K.sparks(fr, t, 1414, tuple(mid), n=90, life=0.9, speed=(120, 420), dirc=(-0.4, -1), spread=0.8, grav=-80, area=(160, 260), amt=0.5 + 0.6 * front)
        fr = heat_haze(fr, t, self.tex, 4 + 8 * heat * front)
        dx, dy, dr = shake(t, 3 + 5 * front, 13, 14)
        fr = cam(fr, 1.0, dx, dy, dr)
        return fr, 0


class P15(Shot):
    """第七棒重做（评审 P0：LS 举刀向天 ≈ 副歌一 S030 月下举刀）：MS 侧面横刀蓄势（生图 guard_h，束发）——
    他侧身平端长刀于眼前，刀身仍带 P14 的余烬红，刀尖指向画左；缓推 + 火星沿刃口剥落；59.13 鼓停：刀身一线寒光由刀镡扫向刀尖，
    画面压暗憋住 → 副歌一 S028（横刀 CU + 血字）——横刀线同向接，景别 MS → CU。"""
    T_HOLD = V(59.13)
    SRC, DST, WPX = (0.55, 0.35), (1000, 540), 2000
    def __init__(self):
        self.sp = spr('B_r4/guard_h')
        self.p7 = P07()
        self.tex = K.tile(512, 915, 6, 4)

    def render(self, t):
        tr = t
        if t > self.T_HOLD: t = self.T_HOLD + (t - self.T_HOLD) * 0.05
        u = clamp01((t - self.t0) / (self.T_HOLD - self.t0))
        x, y = K.grid()
        fr = self.p7.sky(t * 1.2, rot=0.4) * 0.8
        fr += np.exp(-(((x - 600) / 700) ** 2 + ((y - 450) / 300) ** 2))[..., None] * RED * 0.18
        dst = (self.DST[0] + 30 * (1 - eio(u)), self.DST[1])
        wpx = self.WPX * (1.0 + 0.07 * eio(u))
        fr = K.fog(fr, t, 1501, amt=0.22, y0=0.6, y1=1.0)
        fr, Aw = put_at(fr, self.sp, t, self.SRC, dst, wpx, grade=dict(expo=0.82, sat=0.6, tint=(0.95, 0.96, 1.03), lift=0.0, gamma=1.1),
                        rim=dict(col=(1.0, 0.45, 0.32), amt=2.4, dir=(-0.9, -0.3)), wind_amp=6, shade=(1100, 1900, 0.3, 600, 0.4))
        g = spt(self.sp, self.SRC, dst, wpx, (0.690, 0.350)); tip = spt(self.sp, self.SRC, dst, wpx, (0.010, 0.345))
        fr, band = blade_heat(fr, Aw, g, tip, 0.006 * wpx + 4, 0.38, 1.0, t, seed=15)   # 余烬：刃口暗红，不成光剑
        # 59.13 一线寒光沿刃扫过（蓄势）
        q = clamp01((t - (self.T_HOLD - 0.20)) / 0.22)
        if q > 0:
            px = g[0] + (tip[0] - g[0]) * eio(q); py = g[1] + (tip[1] - g[1]) * eio(q)
            sh = np.exp(-(((x - px) / 70) ** 2 + ((y - py) / 10) ** 2)) * band
            fr = fr + sh[..., None] * np.array([1.0, 0.97, 0.92], np.float32) * 1.4 + K.blur_ds(sh, 14)[..., None] * 0.5
        fr = K.sparks(fr, t, 1515, tuple(((g + tip) / 2).astype(int)), n=90, life=1.0, speed=(80, 300), dirc=(0.0, -1), spread=0.9, grav=-100,
                      area=(int(abs(g[0] - tip[0]) / 2), 12), amt=0.8)
        fr = BK.rain(fr, t, 1502, amt=0.28, n=420, angle=-6)
        fr = heat_haze(fr, t, self.tex, 3)
        fr = cam(fr, 1.0 + 0.06 * eio(u), 0, 0, 0)
        if tr > self.T_HOLD:
            fr = fr * (1 - 0.6 * clamp01((tr - self.T_HOLD) / 0.1))
        return fr, 0


SHOTS = [P01, P02, P03, P04, P05, P06, P07, P08, P09, P10, P11, P12, P13, P14, P15]
for _S, _a, _b in zip(SHOTS, CUT_F, CUT_F[1:]):
    _S.t0, _S.t1 = _a / FPS, _b / FPS
P01.t0 = 44.048

CUTS = {
    'P02': ('flashr', 0, 0, {}),                                    # 落墨帧朱红闪（第三棒：去白闪）
    'P03': ('paper_tear', 0.06, 0.20, dict(seed=3, angle=10)),
    'P04': ('none', 0, 0, {}),                                      # 同一机位连续后拉（图形匹配）
    'P05': ('ink_bleed', 0.06, 0.16, dict(seed=5)),                 # 第三棒：去 whip，墨从指尖洇成宫门
    'P06': ('flashr', 0, 0, {}),
    'P07': ('flash_white', 0.0, 0.17, {}),                          # 雷闪
    'P08': ('cloud_wipe', 0.10, 0.16, dict(seed=8)),                # 第四棒：灰雾 smoke → 云幕下压（b_kit，冷光云边，中点上天下人）
    'P09': ('glitch_cut', 0.03, 0.06, dict(seed=9)),                # 第五棒：缩短，让 52.84「命」干净砸进
    'P10': ('slash_wipe', 0.05, 0.14, dict(angle=-28)),
    'P11': ('gold', 0, 0, {}),                                      # 金属火花金闪（第三棒：去白闪）
    'P12': ('match_cut', 0.0, 0.12, dict(shape='rect', center=(960, 470), radius=140)),
    'P13': ('flash_red', 0.03, 0.12, {}),
    'P14': ('punch', 0, 0, {}),                                     # 第五棒：斜刀特写落拍硬切（色散冲击）
    'P15': ('shatter', 0.06, 0.10, dict(seed=15)),                   # 第五棒：特写碎裂 → LS 举刀（换景别）
}
FG = {'P05': ('rain', 0.35), 'P07': ('rain', 0.45), 'P08': ('ash', 0.25), 'P09': ('ember', 0.35), 'P10': ('ash', 0.25),
      'P12': ('ember', 0.35), 'P13': ('ember', 0.5), 'P14': ('ember', 0.7), 'P15': ('ember', 0.6)}
EXPO = {'P01': 1.05, 'P02': 1.0, 'P03': 1.0, 'P04': 1.0, 'P07': 1.1, 'P12': 1.1}

_SEC = [None]
_C1 = [None]


def section():
    if _SEC[0] is None: _SEC[0] = Section(SHOTS, CUTS, FG, EXPO, expo_all=1.12)
    return _SEC[0]


def frame(f, cache=None):
    if f >= C1_FROM:                            # 59.30 起 = 副歌一自身（S028「血」字头硬切）
        if _C1[0] is None:
            os.environ.setdefault('SPRITE_MODE', '1')
            import chorus1 as C; _C1[0] = (C, C.Chorus1())
        C, X = _C1[0]
        return C.to8(X.frame(f / FPS)[0])
    return section().frame(f)
