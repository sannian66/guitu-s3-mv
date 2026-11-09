"""units/sec_b_verse2.py — B 组 · 间奏 + 主歌二「大局」（帧 2586–3534，86.192–117.8s）
分镜：crew/round4/B_storyboard.md 第 2 节（25 镜，切点按 align.json 字头修正，见 storyboard「第二棒改动」）。
接口：READY / frame(f, cache) -> uint8 (1080,1920,3)
入口：帧 2586 复刻副歌一 S047 墨退（K.ink_blot seed=47，中心 (960,600)，起点 86.192，同一遮罩/墨色）。
出口：V25 末拍推进 + 压暗到 ~30%，刀痕红线留在画面中线，供 C 组硬切。
色：墨 88 / 朱 6 / 金 6。字体即立场：权力 = 思源宋（金/白）；鬼屠 = 马善政 / 志莽行书 / 流江毛草（朱）。"""
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
import fx2
import paper as PA
import b_crowd as BC

READY = False
F0, F1 = 2586, 3534
T_IN = 86.192                       # 副歌一 S047 的起点（墨退时间基准）

# 切点（秒）：落拍 / 字头（第二棒按 align.json 逐字时间修正，避免字头跨镜）
CUT_T = [86.192, 87.53, 89.40, 90.77, 91.67, 93.34, 93.97, 94.48, 96.10, 97.52, 98.48, 99.47, 100.58, 102.14,
         103.14, 104.30, 105.88, 107.55, 108.34, 109.55, 110.92, 112.29, 113.60, 115.03, 116.42, 117.80]
CUT_F = [F0] + [int(round(t * FPS)) - 1 for t in CUT_T[1:-1]] + [F1]

INK_C = np.array([0.015, 0.014, 0.016], np.float32)
COLDC = np.array([0.80, 0.86, 0.96], np.float32)


def neg_grade(fr):
    """第四棒：黑白颠倒的负片调色——S 曲线拉开反差（纸白 ↔ 墨黑），冷白纸色 + 重暗角，避免整屏中灰。"""
    x, y = K.grid()
    n = 1 - np.clip(fr, 0, 1)
    lum = (n * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
    lo, hi = np.percentile(lum[::6, ::6], [2.0, 99.7])             # 按画面自身明暗拉伸（原画很暗，反相后全挤在高端）
    lum = np.clip((lum - lo) / max(hi - lo, 1e-3), 0, 1)
    lum = 0.06 + 0.90 * (lum * lum * (3 - 2 * lum)) ** 1.15
    vg = np.exp(-(((x - 960) / 1000) ** 2 + ((y - 540) / 560) ** 2))[..., None]
    if 'tex' not in _NEG:
        _NEG['tex'] = cv2.resize(K.fbm(H // 4, W // 4, 6609, 7, 5), (W, H))[..., None].astype(np.float32)
    tex = _NEG['tex']                                               # 宣纸云纹：平涂的城楼/墙面反相后不再是死白块
    return lum * (0.80 + 0.32 * tex) * np.array([0.90, 0.91, 0.95], np.float32) * (0.30 + 0.72 * vg)


_NEG = {}


def prs(li, ks, t, dur=0.18):
    return tp(li, ks, t, dur)


def hitp(t, tt, decay=0.12):
    """视觉帧 tt 起的冲击包络"""
    return pulse(t, V(tt), decay) * (t >= V(tt))


def lum3(v, tint=(1.0, 1.0, 1.0)):
    return np.stack([v * tint[0], v * tint[1], v * tint[2]], -1).astype(np.float32)


# ------------------------------------------------------------------ 共用场景件
def city_wall_far(seed, y_top=520, y_bot=760, tone=0.10, crenel=True):
    """远景城墙剪影（砖纹 + 城垛 + 城楼），返回 (rgb, mask)"""
    wall, seam = K.brick_wall(2200, 600, 70, 30, 4, seed)
    h = y_bot - y_top
    wl = cv2.resize(wall[:400, :2200], (W, h)) * 0.55
    m = np.zeros((H, W), np.float32); m[y_top:y_bot] = 1
    rgb = np.zeros((H, W, 3), np.float32); rgb[y_top:y_bot] = wl * (tone / 0.12)
    if crenel:
        for xx in range(-20, W + 40, 58):
            cv2.rectangle(m, (xx, y_top - 22), (xx + 30, y_top), 1.0, -1)
            cv2.rectangle(rgb, (xx, y_top - 22), (xx + 30, y_top), (tone * 0.8,) * 3, -1)
        # 城楼（重檐）
        cx = int(W * 0.62)
        for k, (wd, hh, yy) in enumerate(((420, 40, y_top - 150), (300, 34, y_top - 230))):
            pts = np.int32([[cx - wd // 2 - 40, yy + hh], [cx + wd // 2 + 40, yy + hh], [cx + wd // 2, yy], [cx - wd // 2, yy]])
            cv2.fillConvexPoly(m, pts, 1.0); cv2.fillConvexPoly(rgb, pts, (tone * 0.7,) * 3)
            cv2.rectangle(m, (cx - wd // 2 + 30, yy + hh), (cx + wd // 2 - 30, yy + hh + 80 - k * 10), 1.0, -1)
            cv2.rectangle(rgb, (cx - wd // 2 + 30, yy + hh), (cx + wd // 2 - 30, yy + hh + 80 - k * 10), (tone * 0.85,) * 3, -1)
    return rgb, m


def night_sky(seed, top=(0.035, 0.04, 0.05), bot=(0.16, 0.17, 0.19), horizon=0.7, cloud=0.9):
    return K.sky(seed=seed, cloud=cloud, horizon=horizon, top=top, bot=bot, stars=0.0).copy()


# 第四棒：生图插地刀 blade_stuck（assets/gen/B_r4/blade_stuck_cut.png，16:9 画布）关键点（归一化）
BS_MUD = (0.470, 0.975)        # 泥堆底中点（锚点）
BS_GUARD = (0.508, 0.300)      # 圆镡下沿中点
BS_ENTRY = (0.462, 0.875)      # 刀身入泥点
BS_DROP = (0.545, 0.338)       # 镡下悬着的水滴
BS_W = 1300.0                  # V01 精灵整幅宽（屏幕像素）→ 柄头到泥约 690px


def bs_pt(src, dst, w=BS_W, anchor=BS_MUD):
    """精灵内归一化点 → 屏幕（与 put_at 同一仿射，无旋转）"""
    sw, sh = w, w * 9 / 16
    return dst[0] + (src[0] - anchor[0]) * sw, dst[1] + (src[1] - anchor[1]) * sh


def sword_stuck():
    """斜插泥地的真刀（blade_face 生图刀身 + 护手，刀尖朝下）+ 代码缠绳刀柄。返回 (F, A, grip_y, guard_y)"""
    if 'stuck' in BK._BL: return BK._BL['stuck']
    F0_, A0_ = BK.blade_prop()                       # 刃尖朝上，底部护手，约 2690×800
    F0_ = F0_[::-1].copy(); A0_ = A0_[::-1].copy()   # 翻转：护手在上，刃尖朝下
    hb, wb = A0_.shape
    HL = 640                                         # 刀柄长（源像素）
    F = np.zeros((hb + HL, wb, 3), np.float32); A = np.zeros((hb + HL, wb), np.float32)
    F[HL:] = F0_; A[HL:] = A0_
    cx = 398; hw = 46
    yy, xx = np.mgrid[0:HL, 0:wb].astype(np.float32)
    grip = ((np.abs(xx - cx) < hw * (1 - 0.05 * (1 - yy / HL))) & (yy > 40)).astype(np.float32)
    # 缠绳菱格
    ph = ((yy + (xx - cx) * 0.9) % 52 < 26).astype(np.float32); ph2 = ((yy - (xx - cx) * 0.9) % 52 < 26).astype(np.float32)
    dia = ph * ph2
    shade = np.clip(1 - ((xx - cx) / hw) ** 2, 0, 1) ** 0.5
    gcol = (0.05 + 0.05 * dia + 0.07 * shade)[..., None] * np.array([1.0, 0.88, 0.80], np.float32)
    # 柄头（金属）
    pom = (((xx - cx) / (hw * 1.15)) ** 2 + ((yy - 50) / 40) ** 2 < 1).astype(np.float32)
    gcol = gcol * (1 - pom[..., None]) + pom[..., None] * np.array([0.30, 0.26, 0.18], np.float32) * (0.6 + 0.6 * shade[..., None])
    gm = np.maximum(grip, pom)
    F[:HL] = gcol; A[:HL] = cv2.GaussianBlur(gm, (0, 0), 1.0)
    BK._BL['stuck'] = (F, A, HL, HL + 120)
    return BK._BL['stuck']


def paste_sword(fr, base, ang, length, alpha=1.0, wet=1.0, t=0.0, blur=0.0):
    """把 sword_stuck 贴到屏幕：base=刀身入泥点（屏幕），ang=偏离竖直角度（度，正=向右倾），length=刀从柄头到入泥点屏幕长度"""
    F, A, HL, gy = sword_stuck()
    hs, ws = A.shape
    y_in = HL + int((hs - HL) * 0.62)                # 刀身 62% 处入泥
    s = length / y_in
    M = cv2.getRotationMatrix2D((398.0, float(y_in)), -ang, s)
    M[0, 2] += base[0] - 398.0; M[1, 2] += base[1] - y_in
    Fw = cv2.warpAffine(F, M, (W, H)); Aw = cv2.warpAffine(A, M, (W, H))
    if blur > 0.6:
        Fw = K.blur_ds(Fw * Aw[..., None], blur, 2); Aw = K.blur_ds(Aw, blur, 2); Fw = Fw / np.clip(Aw[..., None], 1e-3, None)
    Aw = Aw * alpha
    # 冷月顶光：刃面高光带 + 雨水湿反光
    x, y = K.grid()
    Fw = Fw * (0.55 + 0.15 * wet) + np.exp(-((y - base[1] + length * 0.55) / (length * 0.35)) ** 2)[..., None] * COLDC * 0.12 * wet
    out = fr * (1 - Aw[..., None]) + Fw * Aw[..., None]
    return out, Aw, M


def glitch_text(fr, L, k, seed=0, t=0.0):
    """RGB 错位故障字：k 0..1 强度"""
    out = T.compose(fr, L, shadow=0.7, glow=0.2, glow_color=(1.0, 0.6, 0.3))
    if k < 0.02: return out
    r = np.random.default_rng(int(seed + t * 30))
    A = L.A
    sh = int(10 + 30 * k)
    Ar = np.roll(A, sh, 1); Ab = np.roll(A, -sh, 1)
    # 横向条带撕裂
    for _ in range(int(3 + 6 * k)):
        y0 = int(r.uniform(120, 940)); hh = int(r.uniform(6, 40)); dx = int(r.uniform(-80, 80) * k)
        Ar[y0:y0 + hh] = np.roll(Ar[y0:y0 + hh], dx, 1); Ab[y0:y0 + hh] = np.roll(Ab[y0:y0 + hh], -dx, 1)
    out[..., 0] += Ar * 0.8 * k; out[..., 2] += Ab * 0.9 * k
    out[..., 1] -= (Ar + Ab) * 0.15 * k
    return out


def sil_over(fr, tmp, rim_col, rim_w=5, amt=1.0, blur=0.0):
    """把画在黑底上的纸人（tmp）变成逆光剪影：近黑实体 + 背光金边（不要卡通脸）"""
    m = np.clip(tmp.max(-1) * 10, 0, 1)
    if blur > 0: m = K.blur_ds(m, blur, 2)
    er = cv2.erode(m, np.ones((rim_w * 2 + 1, rim_w * 2 + 1), np.uint8))
    rim = np.clip(m - er, 0, 1)
    rim = rim * sstep(0.0, 1.0, np.clip(-cv2.Sobel(m, cv2.CV_32F, 0, 1, ksize=5) * 0.05 + 0.4, 0, 1))   # 上缘更亮（逆光在上）
    out = fr * (1 - m[..., None]) + m[..., None] * np.array([0.012, 0.011, 0.012], np.float32)
    return out + rim[..., None] * np.asarray(rim_col, np.float32) * amt + K.blur_ds(rim, 10)[..., None] * np.asarray(rim_col, np.float32) * 0.3 * amt


# =====================================================================================
# 第六棒：86.19–89.40 按章程归 B 组，副歌一 S047（插地刀）/S048（追进雨滴）不改 → 换概念，与之完全不同：
# V01 86.19–87.53 LS 钟楼：暴雨夜宫城钟楼里一口巨钟（生图 v01_bell），86.66 落拍撞钟——钟体震颤、声波折射环扩散、梁上积尘震落、
#     地面积水起涟漪、窗外远雷；「权力的钟声」召来下一句的「世人」。前＝雨丝/飘尘，中＝巨钟，后＝窗外雷云宫阙。
# V02 87.53–89.40 ELS 顶拍：钟声化作一圈声波环掠过整座宫城广场（生图 v02_plaza），广场上跪满纸扎百官，镜头自上而下压近 + 微旋；
#     88.91 雷闪照亮殿顶琉璃、地面反光。图形匹配：钟口圆 → 广场上扩散的声波环。
def _plate(name, scale=1.12):
    from PIL import Image
    im = np.asarray(Image.open(GEN_B + name + '_raw.png').convert('RGB').resize((int(W * scale), int(H * scale)), Image.LANCZOS)).astype(np.float32) / 255
    return im ** 1.0


GEN_B = ROOT + '/assets/gen/B_r4/'


def plate_view(P, zoom, cx, cy, ang=0.0, ox=0.0, oy=0.0):
    """从放大底板 P 里取景：以底板坐标 (cx,cy) 为中心、zoom 倍（相对屏幕 1:1）、旋转 ang 度，输出 W×H"""
    M = cv2.getRotationMatrix2D((float(cx), float(cy)), ang, zoom)
    M[0, 2] += W / 2 - cx + ox; M[1, 2] += H / 2 - cy + oy
    return cv2.warpAffine(P, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def ring_warp(fr, c, r, w, amp, sy=1.0):
    """声波折射环：半径 r、宽 w 的环带把画面沿径向推开 amp 像素（sy<1 = 透视压扁的椭圆环）"""
    x, y = K.grid()
    dx = x - c[0]; dy = (y - c[1]) / sy
    d = np.sqrt(dx * dx + dy * dy) + 1e-3
    g = np.exp(-((d - r) / w) ** 2) * np.sin((d - r) / w * 2.4)
    mx = (x - dx / d * amp * g).astype(np.float32); my = (y - dy / d * amp * g * sy).astype(np.float32)
    out = cv2.remap(fr, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    edge = np.exp(-((d - r) / (w * 0.35)) ** 2)
    return out, edge


class V01(Shot):
    T_HIT = 86.66
    BELL = (1300, 560)
    HIT_X = 60
    def __init__(self):
        self.P = _plate('v01_bell', 1.14)
        h, w = self.P.shape[:2]
        x, y = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
        lum = self.P.mean(-1)
        self.win = np.clip((lum - 0.10) * 4, 0, 1) * (y < h * 0.80)            # 窗外亮区（雷光只照这里）
        self.win = cv2.GaussianBlur(self.win, (0, 0), 6)[..., None]
        self.rain = fx2.RainSheet(4706, density=0.8)
        self.spl = fx2.Splashes(4707)
        r = np.random.default_rng(4710)
        self.dust = r.uniform(0, 1, (260, 4))
        # 第七棒：撞木（左侧悬吊圆木）抠成独立层，撞钟前后真的摆动——拉后 → 加速撞上钟体 → 回弹。原位用 inpaint 补背景
        S = 1.14
        poly = np.int32([[-40, 395], [975, 588], [975, 718], [-40, 560]]) * S
        m = np.zeros((h, w), np.uint8); cv2.fillConvexPoly(m, poly.astype(np.int32), 255)
        lum0 = cv2.GaussianBlur(self.P.mean(-1), (0, 0), 1.5)
        dark = (lum0 < 0.085).astype(np.uint8)                       # 只取圆木本体（暗），窗外亮天不随之移动 → 不出方块
        dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        m = (m // 255) * dark
        nlab, lab, st, _ = cv2.connectedComponentsWithStats(m)
        if nlab > 1:
            big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])); m = (lab == big).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)) * 255
        small = cv2.resize(self.P, (w // 2, h // 2)); ms = cv2.resize(cv2.dilate(m, np.ones((15, 15), np.uint8)), (w // 2, h // 2))
        bgi = cv2.inpaint((np.clip(small, 0, 1) * 255).astype(np.uint8), ms, 9, cv2.INPAINT_TELEA).astype(np.float32) / 255
        self.Pbg = cv2.resize(bgi, (w, h))
        self.ramA = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 2.0)
        self.ramF = self.P * self.ramA[..., None]
        self.rdir = np.array([0.981, 0.193], np.float32)

    def ram_off(self, t):
        th = V(self.T_HIT)
        if t < th:                                           # 第十棒：拉后 → 加速撞进钟体（+HIT_X 越过原位，撞木头真的顶上钟沿）
            q = clamp01((t - self.t0) / (th - self.t0))
            return -120 + (120 + self.HIT_X) * q ** 2.6
        q = t - th
        return self.HIT_X * math.exp(-q / 0.05) - 75 * math.sin(min(q / 0.34, 1.0) * math.pi * 0.5) * math.exp(-max(0, q - 0.34) / 0.6)   # 弹开

    def plate_at(self, t):
        o = self.ram_off(t); o2 = self.ram_off(t - 1 / 60)
        acc = None; n = 3
        for k in range(n):                                   # 快速摆动时沿运动方向做 3 次采样的运动模糊
            oo = (o + (o2 - o) * k / (n - 1)) * 1.14
            M = np.float32([[1, 0, self.rdir[0] * oo], [0, 1, self.rdir[1] * oo]])
            Fw = cv2.warpAffine(self.ramF, M, (self.P.shape[1], self.P.shape[0])); Aw = cv2.warpAffine(self.ramA, M, (self.P.shape[1], self.P.shape[0]))
            layer = self.Pbg * (1 - Aw[..., None]) + Fw
            acc = layer if acc is None else acc + layer
        return acc / n

    def render(self, t):
        u = self.u(t); e = eio(u)
        th = V(self.T_HIT)
        hk = 0.0 if t < th else math.exp(-(t - th) / 0.35)
        hk2 = 0.0 if t < th else math.exp(-(t - th) / 0.09)          # 撞击瞬间（2–3 帧）
        ring_t = max(0.0, t - th)
        thunder = pulse(t, th + 0.28, 0.18) * (t > th)
        P = self.plate_at(t) * (1 + self.win * (0.20 + 1.6 * thunder))
        # 第十棒：钟体被撞后真的在震——钟区（撞点右侧）做衰减高频横摆 + 轻微摆角，撞木与梁不动
        h_, w_ = P.shape[:2]
        if hk > 0.01:
            if not hasattr(self, '_bm'):
                xx, yy = np.meshgrid(np.arange(w_, dtype=np.float32), np.arange(h_, dtype=np.float32))
                self._xx, self._yy = xx, yy
                self._bm = (np.clip((xx - 1120 * 1.14) / 200, 0, 1) * np.clip((yy - 140 * 1.14) / 80, 0, 1)).astype(np.float32)
            osc = math.sin(ring_t * 2 * math.pi * 11.0) * hk * 5.0 + 8.0 * hk2
            ang = math.sin(ring_t * 2 * math.pi * 3.2 + 0.4) * hk * 0.003
            dxm = self._bm * (osc + (self._yy - 140 * 1.14) * ang)
            P = cv2.remap(P, (self._xx - dxm).astype(np.float32), self._yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        bx, by = self.BELL[0] * 1.14, self.BELL[1] * 1.14
        zoom = (0.93 + 0.07 * e) * (1 + 0.05 * hk2)                    # 撞击帧镜头被震得一顶
        dx, dy, dr = shake(t, 3 + 26 * hk, 13, 471)
        fr = plate_view(P, zoom, W * 1.14 / 2 + 60 * e, H * 1.14 / 2 - 20 * e, 0.0, dx, dy)
        fr = fr * 1.25
        # 雨先画：声波环之后再折射，雨丝在环带处被推弯 → 声音「推开雨幕」
        fr = fx2.ripples(fr, t, [(1290, 960), (900, 1000), (1600, 990)], [th, th + 0.05, th + 0.1], amt=0.7, flat=0.2, speed=260, life=1.0)
        fr = self.spl.draw(fr, t, y_far=900, y_near=1060, rate=90, size=0.9, amt=0.6)
        fr = self.rain.draw(fr, t, intensity=0.8, angle=12, light=(1600, 380), light_r=800)
        bell = (self.BELL[0], self.BELL[1] + 40)
        hit = (1000, 640)                                            # 撞木头顶上钟沿的点
        if t >= th:
            x, y = K.grid()
            for k in range(3):
                rr = 90 + 1500 * (ring_t - 0.10 * k) ** 0.8 if ring_t > 0.10 * k else -1
                if rr > 0:
                    fr, edge = ring_warp(fr, hit if k == 0 else bell, rr, 30 + 10 * k, 30 * hk, sy=0.85)
                    fr = fr + edge[..., None] * np.array([0.80, 0.82, 0.86], np.float32) * 0.16 * hk
            # 撞点：冷白冲击核 + 放射铜屑（2–3 帧）
            d = np.sqrt((x - hit[0]) ** 2 + ((y - hit[1]) * 1.3) ** 2)
            fr = fr + (np.exp(-(d / 55) ** 2) * 0.9 + np.exp(-(d / 240) ** 2) * 0.15)[..., None] * np.array([0.92, 0.93, 0.95], np.float32) * hk2
            sheen = np.exp(-(((x - (1050 + 520 * clamp01(ring_t / 0.5))) / 60) ** 2)) * np.exp(-(((y - 560) / 330) ** 4))
            fr = fr + sheen[..., None] * np.array([0.50, 0.52, 0.55], np.float32) * hk * 0.55
            buf = np.zeros((H // 2, W // 2), np.float32)
            for (a, b, c_, d_) in self.dust:                       # 梁尘震落
                tt = ring_t - c_ * 0.15
                if tt < 0: continue
                px = (200 + a * 1600 + 20 * math.sin(tt * 3 + d_ * 9)) / 2; py = (60 + b * 120 + 420 * tt * tt + 160 * tt) / 2
                cv2.circle(buf, (int(px), int(py)), 1, 0.6 + 0.4 * d_, -1, cv2.LINE_AA)
            for (a, b, c_, d_) in self.dust[:90]:                  # 撞点崩出的铜屑火星（冷白，放射 + 下坠）
                ang_ = -math.pi * (0.15 + 0.95 * a); sp_ = 500 + 900 * b
                tt = ring_t
                if tt > 0.45: continue
                px = (hit[0] + math.cos(ang_) * sp_ * tt) / 2; py = (hit[1] + math.sin(ang_) * sp_ * tt + 900 * tt * tt) / 2
                px2 = (hit[0] + math.cos(ang_) * sp_ * max(0, tt - 0.03)) / 2; py2 = (hit[1] + math.sin(ang_) * sp_ * max(0, tt - 0.03)) / 2
                cv2.line(buf, (int(px2), int(py2)), (int(px), int(py)), 1.4 * (1 - tt / 0.45), 1, cv2.LINE_AA)
            fr = fr + cv2.GaussianBlur(buf, (0, 0), 0.8).repeat(2, 0).repeat(2, 1)[..., None] * np.array([0.62, 0.62, 0.66], np.float32) * 0.8
        # 第十棒：调色压回全段冷灰（原图饱和冷蓝 → 去饱和 82%，微冷）
        lum = fr.mean(-1, keepdims=True)
        fr = (lum + (fr - lum) * 0.18) * np.array([0.95, 0.98, 1.03], np.float32)
        # 墨退：只留接缝 1 帧的朱墨斑（与副歌一 2585 连续），随后 3 帧被雨冲淡、往下淌走，不在钟楼上留红团
        if t < T_IN + 0.12:
            q = clamp01((t - T_IN) / 0.12)
            m = K.ink_blot(0.93 + 0.07 * eout((t - T_IN) / 0.2, 2), seed=47, center=(960, 600), reverse=True)
            m = np.roll(m, int(160 * q * q), 0) * (1 - q) ** 1.5
            fr = over(fr, m, RED * 0.22 + 0.015)
        return fr, (3 if abs(t - th) < 0.04 else 0)


class V02(Shot):
    """第十棒重做：宫城广场顶拍——跪拜人海「动起来」并去复制阵列感。
    人群从底板里按亮度抠成独立层（背景 inpaint），人群层用随机场位移：
      · 静态错位（人形尺度的噪声位移，打乱行列）+ 每人明暗差异（湿袍/干袍、宫灯照到与否）；
      · 叩首波浪：钟声自大殿方向推来，波前经过时人群「沉」下去叩首（下沉 + 压暗 + 背部受顶光），每人早晚不一；
      · 纵深层次：近排虚化、远排雾化；前景钟楼檐角（虚焦、滴水）视差最快；中层雾带漂移。
    调色压回冷灰，只留宫灯一点朱。"""
    T_THUNDER = 88.905
    S = 1.25
    def __init__(self):
        from PIL import Image
        S = self.S
        P = np.asarray(Image.open(GEN_B + 'v02_plaza_raw.png').convert('RGB').resize((int(W * S), int(H * S)), Image.LANCZOS)).astype(np.float32) / 255
        h, w = P.shape[:2]; self.h, self.w = h, w
        lum = P.mean(-1); bgl = cv2.GaussianBlur(lum, (0, 0), 18)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); self.xx, self.yy = xx, yy
        cause = np.zeros((h, w), np.uint8)
        cv2.fillPoly(cause, [np.int32([[0.445 * w, 0.27 * h], [0.555 * w, 0.27 * h], [0.60 * w, h], [0.405 * w, h]])], 1)
        m = ((lum - bgl) > 0.02) & (lum > 0.16) & (yy > 0.27 * h) & (cause == 0)
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        A = cv2.GaussianBlur(cv2.dilate(m.astype(np.float32), np.ones((5, 5), np.uint8)), (0, 0), 1.4)
        sm = cv2.resize(P, (w // 2, h // 2)); ms = cv2.resize((cv2.dilate(m, np.ones((11, 11), np.uint8)) * 255).astype(np.uint8), (w // 2, h // 2))
        bg = cv2.inpaint((np.clip(sm, 0, 1) * 255).astype(np.uint8), ms, 7, cv2.INPAINT_TELEA).astype(np.float32) / 255
        bg = cv2.resize(bg, (w, h))
        # inpaint 留下的灰团压暗成湿地（不让它读成鬼影）
        hole = cv2.GaussianBlur(cv2.dilate(m.astype(np.float32), np.ones((11, 11), np.uint8)), (0, 0), 6)[..., None]
        self.BG = bg * (1 - 0.45 * hole)
        self.F = P; self.A = A
        persp = np.clip((yy / h - 0.25) / 0.75, 0, 1)                  # 0 = 远排（大殿前）… 1 = 近排
        self.persp = persp
        def nz(seed, sc):
            return cv2.resize(K.fbm(max(4, h // sc), max(4, w // sc), seed, 3, 3), (w, h), interpolation=cv2.INTER_CUBIC)
        sc = 0.4 + 0.9 * persp                                         # 位移幅度随透视：近排人大，错位也大
        self.jx = (nz(4821, 70) - 0.5) * 2 * 20 * sc                   # 打乱行列（人形尺度噪声）
        self.jy = (nz(4822, 70) - 0.5) * 2 * 12 * sc
        self.tone = 0.70 + 0.55 * nz(4823, 45)                         # 每人明暗差异
        self.delay = (nz(4824, 45) - 0.5) * 0.30                       # 叩首早晚
        self.depth = 0.55 + 0.6 * nz(4825, 45)                         # 叩首深浅
        self.sc = sc
        red = np.clip((P[..., 0] - P[..., 2]) * 3 - 0.15, 0, 1) * np.clip(P[..., 0] * 2 - 0.4, 0, 1)
        self.lan = cv2.GaussianBlur(red, (0, 0), 10)[..., None]
        self.roof = (np.clip(1 - yy / (h * 0.16), 0, 1))[..., None]
        self.fog1 = K.fbm(h // 6, w // 3, 4826, 3, 5); self.fog2 = K.fbm(h // 6, w // 3, 4827, 3, 5)
        r = np.random.default_rng(4810)
        self.drops = r.uniform(0, 1, (700, 3))
        self.drip = r.uniform(0, 1, (26, 3))

    def bow(self, t):
        """每像素叩首量 0..1：波前从大殿（远排）推向近排"""
        t0 = self.t0 + 0.12
        arr = t0 + 0.95 * self.persp + self.delay
        q = np.clip((t - arr) / 0.30, 0, 1)
        b = q * q * (3 - 2 * q)
        tl = V(self.T_THUNDER)                                         # 雷后第二记：再压一次（颤）
        if t > tl: b = b * (1 + 0.15 * math.exp(-(t - tl) / 0.25) * math.sin((t - tl) * 40))
        return b * self.depth

    def render(self, t):
        u = self.u(t); e = eio(u)
        tl = V(self.T_THUNDER)
        env = 0.0 if t < tl else math.exp(-(t - tl) / 0.28)
        flick = 0.85 + 0.15 * math.sin(t * 17.0) * math.sin(t * 5.3)
        h, w = self.h, self.w
        b = self.bow(t)
        sway = math.sin(t * 2.3) * 2.0
        hfig = 30 + 70 * self.persp                                    # 本地人形高度（px）
        mx = (self.xx - self.jx - sway * self.sc).astype(np.float32)
        my = (self.yy - self.jy - b * hfig * 0.45).astype(np.float32)    # 叩首 = 下沉
        F = cv2.remap(self.F, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        A = cv2.remap(self.A, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)[..., None]
        shade = self.tone * (1 - 0.40 * b)                             # 俯下去的背进阴影
        F = F * shade[..., None]
        # 波前经过时：背上一道冷白顶光（钟声 + 雷光扫过人海）
        tw = t - (self.t0 + 0.12)
        front = np.exp(-((self.persp * 0.95 - tw) / 0.06) ** 2) if tw > -0.2 else np.zeros_like(self.persp)
        F = F + (front * 0.12)[..., None] * np.array([0.85, 0.88, 0.95], np.float32)
        P = self.BG * (1 - A) + F * A
        P = P * (1 + self.lan * (0.6 * flick)) * (1 + self.roof * 2.5 * env) * (1 + 0.5 * env)
        # 中层雾带（两层不同速度漂移）
        f1 = cv2.resize(np.roll(self.fog1, int(t * 40) % self.fog1.shape[1], 1), (w, h))
        f2 = cv2.resize(np.roll(self.fog2, -int(t * 22) % self.fog2.shape[1], 1), (w, h))
        fog = (np.clip(f1 - 0.45, 0, 1) * (0.5 + 0.5 * (1 - self.persp)) * 0.55 + np.clip(f2 - 0.5, 0, 1) * 0.35)[..., None]
        P = P * (1 - fog * 0.6) + fog * np.array([0.30, 0.32, 0.35], np.float32)
        zoom = 0.80 + 0.16 * ein(u, 1.6)                               # 顶拍压近（crane down），大殿宫灯留在画内
        fr = plate_view(P, zoom, w / 2 + 40 * e, h / 2 - 110 + 40 * e, -3.0 + 3.0 * e)
        # 纵深虚化：近排（画面下 1/4）轻虚，强调中层
        bl = cv2.GaussianBlur(fr, (0, 0), 3.2)
        x, y = K.grid()
        dm = np.clip((y - 800) / 240, 0, 1)[..., None] * 0.8
        fr = fr * (1 - dm) + bl * dm
        fr = fr * 1.05
        rt = t - self.t0
        for k in range(2):                                             # 钟声环（与 V01 同形）掠过广场
            rr = 80 + 1500 * max(0.0, rt - 0.18 * k) ** 0.85
            if rt > 0.18 * k:
                fr, edge = ring_warp(fr, (960, 140), rr, 34, 14 * math.exp(-rt / 1.2), sy=0.55)
                fr = fr + edge[..., None] * COLDC * 0.10 * math.exp(-rt / 1.0)
        buf = np.zeros((H // 2, W // 2), np.float32)
        for (a, b_, s_) in self.drops:
            ph = (t * (1.3 + s_) + a) % 1.0
            ang = b_ * 2 * math.pi
            r0 = 60 + 1100 * ph ** 1.6; r1 = r0 + 18 + 70 * ph
            p0 = (int((960 + math.cos(ang) * r0) / 2), int((560 + math.sin(ang) * r0 * 0.8) / 2)); p1 = (int((960 + math.cos(ang) * r1) / 2), int((560 + math.sin(ang) * r1 * 0.8) / 2))
            cv2.line(buf, p0, p1, 0.18 + 0.5 * ph, 1, cv2.LINE_AA)
        fr = fr + cv2.resize(buf, (W, H))[..., None] * COLDC * 0.28
        # 前景：钟楼檐角（虚焦黑剪影 + 冷边 + 滴水），视差最快
        ox = -140 + 260 * e
        ex = x - ox
        edge_y = 300 - 0.42 * ex - 22 * np.abs(np.sin(ex / 40.0))          # 瓦当起伏的檐口线（左上角斜切）
        eave = np.clip((edge_y - y) / 10, 0, 1)
        eave = cv2.GaussianBlur(eave.astype(np.float32), (0, 0), 7)
        rim = np.clip(eave - cv2.GaussianBlur(eave, (0, 0), 6), 0, 1) * 0.0 + np.exp(-((y - edge_y) / 6) ** 2) * (edge_y > 0) * 0.25
        fr = fr * (1 - eave[..., None] * 0.94) + eave[..., None] * 0.012 + cv2.GaussianBlur(rim.astype(np.float32), (0, 0), 3)[..., None] * COLDC * 0.5
        dbuf = np.zeros((H, W), np.float32)
        for (a, b_, s_) in self.drip:                                  # 檐口滴水（虚焦长条）
            xx0 = a * 640
            yy0 = 300 - 0.42 * xx0 - 22 * abs(math.sin(xx0 / 40.0))
            ph = (t * (0.9 + s_) + b_) % 1.0
            yd = yy0 + 900 * ph * ph
            cv2.line(dbuf, (int(xx0 + ox), int(yd)), (int(xx0 + ox), int(yd + 40 + 60 * ph)), 0.7, 3, cv2.LINE_AA)
        fr = fr + cv2.GaussianBlur(dbuf, (0, 0), 3)[..., None] * COLDC * 0.5
        # 调色：冷灰，宫灯保留一点朱
        lum = fr.mean(-1, keepdims=True)
        redm = np.clip((fr[..., 0] - fr[..., 2]) * 4 - 0.1, 0, 1)[..., None]
        fr = (lum + (fr - lum) * (0.20 + 0.55 * redm)) * np.array([0.95, 0.98, 1.03], np.float32)
        fr = np.clip(fr, 0, 4); fr = 0.62 * (fr / 0.62) ** 1.28 * 1.08          # 拉开反差：湿地压黑、人背提亮
        if tl <= t: fr = fr * (1 + 0.35 * pulse(t, tl + 0.05, 0.12))
        return fr, (3 if abs(t - tl) < 0.04 else 0)


def ring_wipe(A, B, p, center=(1300, 600), sy=0.85):
    """B 组第六棒：声波环开门——B 从钟体扩散的折射环里长出来（环带折射 + 冷光边），与 V01 撞钟的声波同形"""
    x, y = K.grid()
    e = eio(p)
    d = np.sqrt((x - center[0]) ** 2 + ((y - center[1]) / sy) ** 2)
    r = 40 + 2400 * e
    m = np.clip((r - d) / 40, 0, 1)[..., None]
    Aw, edge = ring_warp(A, center, r, 40, 22 * math.sin(math.pi * e), sy)
    return Aw * (1 - m) + B * m + edge[..., None] * COLDC * 0.35 * math.sin(math.pi * e)


BK.BTRANS['ring_wipe'] = ring_wipe


# =====================================================================================
# V03 89.40–90.77 LS：雨中纸人队列从队首到队尾依次鞠躬（顾全大局）；前景雨帘，后景雾中金光；
#   「世人教我顾全」思源宋 3 个深度的空间字，随横移视差
class V03(Shot):
    def __init__(self):
        self.figs = BC.figs('crowd_bow')       # 第五棒：代码名帖纸人 → 生图纸扎人（拆 6 个单体，依次鞠躬）
        r = np.random.default_rng(4903)
        self.rows = []                          # (x, foot_y, h, blur, fog, idx, delay)
        for row, (n, fy, hh, bl, fg) in enumerate(((9, 655, 190, 2.5, 0.55), (7, 770, 300, 1.2, 0.3), (5, 975, 480, 0.0, 0.0))):
            for i in range(n):
                # 第八棒（P2-12 人偶阵列感）：间距/身高/站位前后/鞠躬早晚/朝向/景深全部打乱，个别人掉队、两两挨近
                if r.uniform() < 0.12: continue
                x_ = -120 + (2200 / n) * (i + 0.5) + r.uniform(-0.38, 0.38) * (2200 / n) + (row % 2) * 60
                dfy = r.uniform(-22, 22) * (1 + row)
                sc = r.uniform(0.86, 1.12)
                self.rows.append((x_, fy + dfy, hh * sc * (1 + dfy / 900), bl + r.uniform(0, 1.2) * (row < 2), fg, int(r.integers(6)),
                                  (x_ + 200) / 2400 * 0.55 + row * 0.05 + r.uniform(-0.12, 0.18), bool(r.uniform() < 0.8), r.uniform(-7, 7)))
            self.rows.sort(key=lambda q: q[1])
        sk = night_sky(4901, top=(0.03, 0.03, 0.04), bot=(0.13, 0.12, 0.11), horizon=0.75)
        x, y = K.grid()
        sk += np.exp(-(((x - 1450) / 520) ** 2 + ((y - 560) / 260) ** 2))[..., None] * GOLD * 0.22
        self.bg = sk
        self.fog = fx2.Fog(4902)
        self.rain = fx2.RainSheet(4904, density=0.8)
        T.warm('世人教我顾全', 'serif_sb', 120)

    def render(self, t):
        u = self.u(t)
        e = eio(u)
        pan = -180 * e
        fr = self.bg.copy()
        fr = cam(fr, 1.0, -pan * 0.2, 0)
        fr = self.fog.draw(fr, t, density=0.5, y0=480, y1=900, color=(0.34, 0.33, 0.32), speed=(30, 0), light=(1450, 560),
                           light_r=600, light_color=GOLD * 0.8, cam=(pan * 0.3, 0))
        bow = clamp01((t - (V(CT(20, 4)) - 0.4)) / 1.0)
        par = (0.35, 0.6, 1.0)
        for k, (x_, fy, hh, bl, fg, idx, dl, fl, tj) in enumerate(self.rows):
            row = 0 if fy < 720 else (1 if fy < 880 else 2)
            bk = eio(clamp01((t - (V(CT(20, 4)) - 0.55) - dl) / 0.45))          # 依次鞠躬（左 → 右的浪）
            fr, _ = BC.draw(fr, self.figs[idx], (x_ + pan * par[row], fy), hh, tilt=-16 + tj + (18 + 0.6 * tj) * bk + 1.5 * math.sin(t * 2 + k), flip=fl,
                            expo=0.62 - 0.22 * fg, tint=(1.0, 0.95, 0.86), sat=0.5, rim_col=GOLD * 1.1, rim_amt=1.4 - 0.6 * fg, rim_dir=(-1.0, -0.4),
                            blur=bl, wet=0.35)
            nrow = (0 if self.rows[k + 1][1] < 720 else (1 if self.rows[k + 1][1] < 880 else 2)) if k + 1 < len(self.rows) else 9
            if fg > 0 and nrow != row:
                fr = fr * (1 - fg * 0.5) + np.array([0.20, 0.19, 0.18], np.float32) * fg * 0.5      # 远排压雾
        pr = prs(20, [0, 1, 2, 3, 4, 5], t)
        items = [dict(text='世人', x=-520, y=-170, z=1700, size=150, color='white', font='serif_sb', style='h', prog=pr[0:2]),
                 dict(text='教我', x=80, y=-60, z=1250, size=150, color='white', font='serif_sb', style='h', prog=pr[2:4]),
                 dict(text='顾全', x=420, y=110, z=850, size=160, color='gold', font='serif_black', style='h', prog=pr[4:6])]
        fr = T.kinetic_track(fr, items, cam=(-pan * 1.4, 0, 0), focal=1000, focus_z=1250, dof=0.004)
        fr = self.rain.draw(fr, t, intensity=1.1, angle=12, light=(1450, 560), light_r=600, cam=(pan, 0))
        fr = cam(fr, 1.02 + 0.02 * e, 0, 0, 0.6 * e)
        return fr, 0


# =====================================================================================
# V04 90.77–91.67 CU 低机位：第七棒——「大局」不再是悬空金字。四个纸扎百官垂首捧笏（生图 hu_hands），
#   「大」「局」被一记一记阴刻进前两块笏板（刻刀火星 + 嵌金），「退」「让」随后刻在笏板下半（墨色阴刻，字小）——
#   顾全大局 = 写在臣子手里的板子上；每刻一字，捧笏的人再低一分头。前＝雨丝，中＝笏板与手，后＝暗殿里一线金光。
import b_carve as BV


class V04(Shot):
    HU = [((0.326, 0.40), (0.296, 0.63), -10.0), ((0.584, 0.45), (0.560, 0.635), -9.0)]   # 两块笏板：上字 / 下字的精灵内归一化中心、倾角
    SRC, DST, WPX = (0.45, 0.50), (930, 600), 2700
    def __init__(self):
        self.sp = spr('B_r4/hu_hands')
        x, y = K.grid()
        bg = BK.dark_bg(4911, 0.008, 0.03, tint=(1.15, 1.0, 0.86))
        bg += np.exp(-(((x - 1500) / 520) ** 2 + ((y - 220) / 240) ** 2))[..., None] * GOLD * 0.16          # 殿门缝的金光
        bg += np.exp(-((x - 1500) / 60) ** 2)[..., None] * np.exp(-((y - 300) / 400) ** 2)[..., None] * GOLD * 0.10
        self.bg = bg
        self.rain = fx2.RainSheet(4913, density=0.8)
        self.sh = self.sp.h / self.sp.w

    def to_scr(self, n, bow):
        return (self.DST[0] + (n[0] - self.SRC[0]) * self.WPX, self.DST[1] + bow + (n[1] - self.SRC[1]) * self.WPX * self.sh)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        tks = [V(CT(20, k)) for k in (6, 7, 8, 9)]
        tks[0] = max(tks[0], self.t0 + 0.02)
        nb = sum(eout(clamp01((t - tk) / 0.25), 3) for tk in tks)               # 每刻一字低一分头
        bow = 14 * nb + 20 * eio(u)
        fr, Aw = put_at(fr, self.sp, t, self.SRC, (self.DST[0], self.DST[1] + bow), self.WPX,
                        grade=dict(expo=0.62, sat=0.45, tint=(1.04, 0.97, 0.90), lift=0.0, gamma=1.15),
                        rim=dict(col=GOLD * 1.0, amt=1.6, dir=(0.6, -0.8)), wind_amp=0, breathe=0.002,
                        shade=(300, 1900, -0.25, 500, 0.45), wrap=0.25)
        x, y = K.grid()
        fr = fr * (0.75 + 0.45 * np.exp(-(((x - 900) / 800) ** 2 + ((y - 380) / 380) ** 2)))[..., None]   # 顶光落在笏板上半
        spark = []
        chars = [('大', 0, 0, 150, True), ('局', 1, 0, 128, True), ('退', 0, 1, 112, False), ('让', 1, 1, 100, False)]
        for k, (ch, hu, row, sz, gold) in enumerate(chars):
            tk = tks[k]
            p = clamp01((t - (tk - 0.03)) / 0.14)
            if p <= 0: continue
            c = self.to_scr(self.HU[hu][row], bow)
            A = BV.mask([(ch, c[0], c[1], sz, self.HU[hu][2])], fname='serif_black')
            A, front = BV.reveal(A, p)
            hot = pulse(t, tk + 0.1, 0.3) * (t >= tk)
            if gold:
                fr = BV.engrave(fr, A, light=(-0.6, -0.8), depth=4, groove=0.5, fill=(0.95, 0.70, 0.30), fill_k=0.85,
                                hl=0.45, surface=Aw, glow=0.25 + 0.6 * hot, glow_col=(1.0, 0.62, 0.25))
            else:
                fr = BV.engrave(fr, A, light=(-0.6, -0.8), depth=3, groove=0.75, fill=(0.05, 0.03, 0.03), fill_k=0.8, hl=0.3, surface=Aw)
            if front is not None and p < 1: spark.append((front, tk))
        for (fx_, fy_), tk in spark:
            fr = K.sparks(fr, t, 4915 + int(fx_), (fx_, fy_), n=60, life=0.35, speed=(200, 700), dirc=(0.3, -1), spread=1.4, grav=1500,
                          size=1.3, area=(30, 10), color=(1.0, 0.75, 0.4), amt=1.2, t0=tk - 0.03, burst=True)
        fr = self.rain.draw(fr, t, intensity=0.9, angle=6, light=(1500, 260), light_r=700)
        k = max(hitp(t, tks[1], 0.1), hitp(t, tks[2], 0.1))
        dx, dy, dr = shake(t, 3 + 9 * k, 11, 404)
        fr = cam(fr, 1.0 + 0.05 * eio(u) + 0.02 * k, dx, dy, dr)
        return fr, (2 if k > 0.5 else 0)


# =====================================================================================
# V05 91.67–93.34 MS：越过人群背影，烛光照亮的纸屏风，屏风上投着太上皇执权杖的巨大影子；「可大局背后」宋体竖排印在屏风上
class V05(Shot):
    def __init__(self):
        r = np.random.default_rng(5001)
        pap = BK.paper(5001, (0.86, 0.72, 0.50))
        x, y = K.grid()
        # 屏风格栅（木框 + 竖格）
        lat = np.zeros((H, W), np.float32)
        for xx in range(160, W, 400): cv2.rectangle(lat, (xx - 14, 0), (xx + 14, H), 1.0, -1)
        for yy in (150, 560, 940): cv2.rectangle(lat, (0, yy - 10), (W, yy + 10), 1.0, -1)
        self.lat = cv2.GaussianBlur(lat, (0, 0), 1.2)
        self.pap = pap
        self.sp = spr('S050/scepter')
        self.figs = BC.figs('crowd_bow')       # 第五棒：前景人群 = 生图纸扎人单体（第 2 次：大景别逆光剪影、虚焦）
        T.warm('可大局背后', 'serif_black', 110)

    def render(self, t):
        u = self.u(t)
        e = eio(u)
        x, y = K.grid()
        fl = 0.9 + 0.1 * math.sin(t * 17) * math.sin(t * 7.3)
        glow = np.exp(-(((x - 900) / 900) ** 2 + ((y - 1000) / 520) ** 2))
        fr = self.pap * (0.18 + 0.95 * glow[..., None] * fl) * np.array([1.0, 0.8, 0.55], np.float32)
        # 太上皇执杖的投影（精灵 look=shadow，柔边，随烛焰轻晃）
        sh = np.zeros_like(fr)
        _, Aw = put(sh, self.sp, t, 1150, (930 + 12 * math.sin(t * 3), 1060), look='shadow', wind_amp=4, shade=None, wrap=0.0)
        Aw = K.blur_ds(Aw, 7 + 2 * math.sin(t * 5), 2)
        fr = fr * (1 - 0.78 * Aw[..., None])
        # 宋体竖排印在屏风上（乘法墨色，透纸纹）
        pr = prs(21, [0, 1, 2, 3, 4], t)
        L = T.Layer()
        for i, (ch, pc) in enumerate(zip('可大局背后', pr)):
            if pc <= 0: continue
            T.place(L, ch, 1480, 230 + i * 128, 112, color='ink', fname='serif_black', alpha=min(1, pc * 2) * 0.9, scale=1 + 0.25 * (1 - eout(pc)))
        fr = fr * (1 - L.A[..., None] * 0.95) + L.A[..., None] * np.array([0.05, 0.012, 0.008], np.float32)
        # 格栅木框（暗）
        fr = fr * (1 - self.lat[..., None] * 0.88) + self.lat[..., None] * np.array([0.03, 0.02, 0.015], np.float32)
        # 前景：人群背影（纸人背面，深色剪影、景深虚化），dolly 向前 → 背影下沉出画
        sink = 140 * e
        for i in (0, 2, 4, 1, 3):
            xx = 80 + i * 440 + (i % 2) * 40
            fr, _ = BC.draw(fr, self.figs[(i * 2 + 1) % 6], (xx, 1080 + 330 + sink + 40 * (i % 3)), 1050 + 60 * (i % 2), tilt=6 + 2 * math.sin(t * 1.5 + i),
                            flip=(i % 2 == 0), expo=0.5, sat=0.4, rim_col=GOLD * 0.9, rim_amt=1.8, rim_dir=(0.0, -1.0), sil=0.85, blur=5)
        fr = fr + 0.03 * glow[..., None] * GOLD
        fr = cam(fr, 1.0 + 0.07 * e, 0, -30 * e)
        return fr, 0


# =====================================================================================
# V06 93.34–93.97 CU：屏风后真相——太上皇半张脸被烛光从下照亮，冷笑（tsh_smirk）。图形匹配：影子的头 → 真人头同位置
class V06(Shot):
    def __init__(self):
        self.sp = spr('tsh_smirk')
        self.bg = BK.dark_bg(5101, 0.01, 0.035, tint=(1.15, 1.0, 0.9))
        T.warm('是谁的', 'serif_sb', 84)

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        fl = 0.85 + 0.15 * math.sin(t * 19) * math.sin(t * 6.1)
        fr = self.bg + np.exp(-(((x - 960) / 600) ** 2 + ((y - 1100) / 400) ** 2))[..., None] * np.array([0.35, 0.16, 0.05], np.float32) * fl
        fr, _ = put_at(fr, self.sp, t, (0.42, 0.30), (930, 400), 2100,
                       grade=dict(expo=0.78 * fl, sat=0.7, tint=(1.08, 0.94, 0.80), lift=0.0, gamma=1.15),
                       rim=dict(col=(1.0, 0.62, 0.30), amt=2.0, dir=(0.0, 1.0)), wind_amp=2, breathe=0.004,
                       shade=(1300, 1900, 0.35, 300, -0.15), wrap=0.25)
        # 底光：脸下半更亮（烛焰），上半沉入暗部
        fr = fr * (0.55 + 0.55 * sstep(150, 760, y))[..., None]
        pr = prs(21, [5, 6, 7], t)
        L = T.Layer()
        for i, (ch, pc) in enumerate(zip('是谁的', pr)):
            if pc <= 0: continue
            T.place(L, ch, 260, 330 + i * 110, 92, color='gold' if ch == '谁' else 'white', fname='serif_sb', alpha=min(1, pc * 2))
        fr = T.compose(fr, L, shadow=0.85, glow=0.2, glow_color=(1.0, 0.55, 0.2))
        fr = cam(fr, 1.0 + 0.05 * eio(u), 0, 0)
        return fr, 0


def sp_pt(sp, src, dst, width_px, rot, n):
    """精灵内归一化点 n → 屏幕（与 sp.draw 同一仿射：绕 src 旋转 rot、缩放 width_px/sp.w、src→dst）"""
    s_ = width_px / sp.w
    M = cv2.getRotationMatrix2D((src[0] * sp.w, src[1] * sp.h), rot, s_)
    M[0, 2] += dst[0] - src[0] * sp.w; M[1, 2] += dst[1] - src[1] * sp.h
    q = M @ np.array([n[0] * sp.w, n[1] * sp.h, 1.0])
    return float(q[0]), float(q[1])


# =====================================================================================
# V07 93.97–94.48 CU：太上皇的手攥紧权杖（grip_scepter）。第七棒：「权」不再是悬空金字——
#   94.02 烛焰一跳，一扇镂空「权」字的窗棂把光投进暗殿：字形的暖光斜斜地落在攥杖的手背、袖口和后墙上（字 = 照在权力之手上的光）
class V07(Shot):
    T_QUAN = 94.02
    def __init__(self):
        self.sp = spr('B_r4/grip_scepter_hi', work_w=3072)      # 第九棒：原图 3840 直接抠（原 2560 抠图 → 2048 工作宽 → 2700 放大，手指糊成团）
        self.bg = BK.dark_bg(5201, 0.02, 0.06, tint=(1.2, 1.0, 0.85))
        wall = cv2.resize(K.fbm(H // 4, W // 4, 5202, 8, 5), (W, H))[..., None]
        self.bg = self.bg * (0.7 + 0.6 * wall)
        T.warm('权', 'serif_black', 620)

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        fr = self.bg.copy()
        k = eout(clamp01((t - self.t0) / 0.25), 3)                 # 攥紧：手从略松到紧（推进 + 微抖）
        fr, Aw = put_at(fr, self.sp, t, (0.24, 0.30), (820, 560), 2700 * (1.0 + 0.04 * k),
                        grade=dict(expo=0.92, sat=0.75, tint=(1.04, 0.96, 0.86), lift=0.0, gamma=1.04),
                        rim=dict(col=(1.0, 0.66, 0.32), amt=1.6, dir=(0.9, -0.3)), wind_amp=0, shade=None, wrap=0.3)
        # 镂空窗棂投影：字形光斜投（sx 拉伸 + 倾斜），窗格木条把字切成几块
        pq = clamp01((t - (V(self.T_QUAN) - 0.06)) / 0.12)
        fl = 0.85 + 0.15 * math.sin(t * 23) * math.sin(t * 7.1)
        L = T.Layer(); T.place(L, '权', 1180, 540, 600, color='white', fname='serif_black', alpha=1.0, rot=8, sx=1.2, sy=1.0, texture=False)
        lat = ((np.abs(((x + 0.25 * y) % 330) - 165) < 7) | (np.abs((y % 300) - 150) < 6)).astype(np.float32)
        Lm = np.clip(L.A, 0, 1) * (1 - lat)
        Lm = cv2.GaussianBlur(Lm, (0, 0), 5)
        light = Lm * pq * fl * (1 + 0.8 * pulse(t, V(self.T_QUAN), 0.15))
        amb = 0.55 + 0.45 * (1 - pq)
        fr = fr * (amb + light[..., None] * np.array([2.3, 1.45, 0.75], np.float32)) + light[..., None] * np.array([0.06, 0.03, 0.01], np.float32)
        # 光路里的浮尘（体积光）
        fr = fr + K.blur_ds(Lm, 40)[..., None] * np.array([0.10, 0.06, 0.02], np.float32) * pq
        fr = fx2.heat_haze(fr, t, amt=2.5 * pq, scale=40, speed=1.4, seed=52)
        hk = hitp(t, self.T_QUAN, 0.1)
        dx, dy, dr = shake(t, 2 + 8 * hk, 11, 52)
        fr = cam(fr, 1.0 + 0.10 * eio(u) + 0.03 * hk, dx, dy, dr)
        return fr, (3 if hk > 0.5 else 0)


# =====================================================================================
# V08 94.48–96.10 低机位贴地（第九棒重做，critic_B_r3 不可交付 → 不再出手）：雨夜宫阶石板地，太上皇的乌木权杖
#   从画面上方「杵」下来——94.76 第一杵，石板以杖镦为心炸裂出「嚣」；抬杖横移，95.32 第二杵裂出「张」。
#   字 = 杖杵出来的裂痕，槽里积水映着远处宫灯（暖）而不是自发光金字；「柄在」宋体阴刻在杖身上（同一字体 = 权力之字）。
#   与 V07（手 + 竖杖 + 窗棂光，CU 平视）拆开：本镜贴地低机位、无手、横向两杵、雨夜外景。
import b_staff as BSF


class V08(Shot):
    T1, T2 = 94.76, 95.32
    F1, F2 = (680, 715), (1220, 740)
    SC = 0.78
    def __init__(self):
        self.F, self.A = BSF.staff_tex()
        self.bg, self.fl, _ = BSF.floor_plate(5401, hor=380)
        self.rain = fx2.RainSheet(5402, density=0.9)
        self.spl = fx2.Splashes(5403)
        self.G = []
        for ch, (fx, fy), r in (('嚣', self.F1, -4), ('张', self.F2, 3)):
            A = BV.mask([(ch, fx, fy + 75, 380, r)], fname='serif_black')
            M = np.float32([[1.0, 0.0, 0.0], [0.0, 0.55, (fy + 75) * 0.45]])        # 透视压扁贴到地面（字心在杖镦前方，杖不挡字）
            self.G.append(cv2.warpAffine(A, M, (W, H)))
        T.warm('柄在', 'serif_black', 110)

    def foot(self, t):
        T1, T2 = V(self.T1), V(self.T2)
        if t < T1:                                                    # 自上方加速杵下
            q = clamp01((t - self.t0) / (T1 - self.t0))
            return (self.F1[0], self.F1[1] - 330 * (1 - q ** 2.4)), 10.0, (330 * 2.4 * q ** 1.4) / max(T1 - self.t0, 0.1) / 30
        if t < T2 - 0.24:
            return self.F1, 10.0, 0.0
        if t < T2:                                                    # 抬杖 → 横移 → 再杵
            q = clamp01((t - (T2 - 0.24)) / 0.24)
            x = self.F1[0] + (self.F2[0] - self.F1[0]) * eio(q)
            yb = self.F1[1] + (self.F2[1] - self.F1[1]) * q
            lift = 240 * math.sin(math.pi * q ** 0.8)
            return (x, yb - lift), 10.0 - 4.0 * q, 12.0 * (1 - abs(2 * q - 1))
        q = t - T2
        return self.F2, 6.0 + 1.2 * math.sin(q * 30) * math.exp(-q / 0.15), 0.0

    def render(self, t):
        u = self.u(t)
        T1, T2 = V(self.T1), V(self.T2)
        fr = self.bg.copy()
        fr = self.spl.draw(fr, t, y_far=390, y_near=960, rate=110, size=1.0, amt=0.6)
        # 裂字（嚣 / 张）：自杖镦径向裂开，槽内积水映宫灯暖光（不自发光）
        for i, (tk, G, fpt) in enumerate(((T1, self.G[0], self.F1), (T2, self.G[1], self.F2))):
            if t < tk: continue
            p = eout(clamp01((t - tk) / 0.16), 2)
            g, lines = BSF.crack_mask(G, (fpt[0], fpt[1]), p, seed=5410 + i)
            fr = BV.engrave(fr, g, light=(-0.3, -1.0), depth=4, groove=0.75, fill=(0.85, 0.55, 0.24), fill_k=0.42 * p,
                            hl_col=(0.70, 0.78, 0.92), hl=0.45, glow=0.0)
            fr = fr * (1 - lines[..., None] * 0.7) + np.roll(lines, -2, 0)[..., None] * COLDC * 0.12
            fr = fx2.ripples(fr, t, [fpt, (fpt[0] + 40, fpt[1] + 8)], [tk, tk + 0.06], amt=0.9, flat=0.3, speed=420, life=0.9)
        # 权杖 + 积水倒影
        ft, ang, mb = self.foot(t)
        refl, Ar = BSF.draw_staff(np.zeros_like(fr), self.F, self.A, ft, ang, self.SC, mblur=mb)
        Rf = cv2.flip(refl, 0); Ra = cv2.flip(Ar, 0)
        sh = int(2 * ft[1] - H)
        Rf = np.roll(Rf, sh, 0); Ra = np.roll(Ra, sh, 0)
        x, y = K.grid()
        wob = (np.sin(y * 0.09 + t * 11) * 4).astype(np.float32)
        Ra = cv2.remap(Ra, x + wob, y, cv2.INTER_LINEAR) * (y > ft[1]) * 0.35 * np.clip(1 - (y - ft[1]) / 260, 0, 1)
        Rf = cv2.remap(Rf, x + wob, y, cv2.INTER_LINEAR)
        fr = fr * (1 - Ra[..., None]) + Rf * Ra[..., None] / np.maximum(Ar.max(), 1e-3) * 0.6
        fr, Aw = BSF.draw_staff(fr, self.F, self.A, ft, ang, self.SC, mblur=mb)
        # 烛光/宫灯暖轮廓（杖右缘）+ 冷顶光
        rim = np.clip(Aw - np.roll(Aw, 6, 1), 0, 1)
        fr = fr + rim[..., None] * np.array([0.9, 0.55, 0.25], np.float32) * 0.5
        # 「柄在」阴刻在杖身（随杖走）
        pr = prs(21, [9, 10], t)
        if max(pr) > 0:
            a = math.radians(ang); up = (math.sin(a), -math.cos(a))
            pl = []
            for k, ch in enumerate('柄在'):
                if pr[k] <= 0: continue
                dd = 520 - k * 125
                pl.append((ch, ft[0] + up[0] * dd, ft[1] + up[1] * dd, 92, -ang))
            if pl:
                Am = BV.mask(pl, fname='serif_black') * min(1.0, max(pr) * 2)
                fr = BV.engrave(fr, Am, light=(-0.9, -0.3), depth=3, groove=0.6, fill=(0.85, 0.62, 0.30), fill_k=0.85,
                                hl=0.4, surface=np.clip(Aw * 1.3, 0, 1), glow=0.0)
        # 杵地：水冠 + 石屑 + 声浪
        for i, tk in enumerate((T1, T2)):
            if t < tk: continue
            fpt = self.F1 if i == 0 else self.F2
            fr = K.sparks(fr, t, 5420 + i, (fpt[0], fpt[1] - 6), n=140, life=0.55, speed=(250, 900), dirc=(0, -1), spread=1.6, grav=1600,
                          size=1.4, area=(60, 10), color=(0.75, 0.80, 0.90), amt=1.0, t0=tk, burst=True)
            fr = K.sparks(fr, t, 5430 + i, (fpt[0], fpt[1]), n=40, life=0.45, speed=(150, 500), dirc=(0, -1), spread=2.6, grav=1800,
                          size=2.2, area=(40, 8), color=(0.35, 0.34, 0.33), amt=1.0, t0=tk, burst=True)
        fr = self.rain.draw(fr, t, intensity=0.75, angle=9)
        gk = max(hitp(t, self.T1, 0.12), hitp(t, self.T2, 0.14))
        dx, dy, dr = shake(t, 14 * gk, 12, 53)
        e = eio(u)
        fr = cam(fr, 1.02 + 0.06 * e + 0.03 * gk, -40 + 90 * e + dx, dy, dr)
        return fr, (3 if gk > 0.6 else 0)


# =====================================================================================
# V09 96.10–97.52 MS 低机位斜看：雨夜案上一架乌木算盘（第三棒：天平 → 算盘，A/C/D 三组都用了天平）。
#   每唱一个字，一档算珠被「啪」地拨上梁（金光 + 溅水），字一个个烫金刻在梁上：「牺牲多少才」——人命被拨来拨去。匹配：权杖竖线 → 竹档竖线
from PIL import Image as _PImg, ImageDraw as _PDraw, ImageFont as _PFont
import b_abacus as BA
import b_paper as BP

_BFONT = {}


def _bfont(name, sz):
    k = (name, sz)
    if k not in _BFONT:
        _BFONT[k] = _PFont.truetype(ROOT + '/fonts/' + name, sz)
    return _BFONT[k]


def beam_text(chars, cols, size, font='NotoSerifSC-Black.otf', beam_h=BA.BEAM_H):
    """在算盘平面贴图上，把字刻在梁上（落在两档之间）；返回每字一张 (AH,AW) 遮罩"""
    out = []
    for ch, c in zip(chars, cols):
        im = _PImg.new('L', (BA.AW, BA.AH), 0); d = _PDraw.Draw(im)
        x = BA.M0 + (BA.AW - 2 * BA.M0) * c / BA.NR                    # c 为整数 → 落在第 c-1 与第 c 档之间
        d.text((x, BA.BEAM_Y + beam_h / 2 + 2), ch, fill=255, font=_bfont(font, size), anchor='mm')
        out.append(np.asarray(im, np.float32) / 255.)
    return out


def gild(rgb, m, glow=0.0):
    """梁上阴刻金字：凹槽暗边 + 金箔 + 上沿高光"""
    sh = np.clip(np.roll(m, 3, 0) - m, 0, 1); hl = np.clip(np.roll(m, -2, 0) - m, 0, 1)
    gold = np.array([0.95, 0.70, 0.30], np.float32)
    rgb = rgb * (1 - m[..., None]) + m[..., None] * gold * (0.75 + 0.6 * glow)
    rgb = rgb - sh[..., None] * 0.08 + hl[..., None] * np.array([1.0, 0.9, 0.7], np.float32) * 0.35
    return rgb


class V09(Shot):
    QUAD = np.float32([[-380, 230], [1980, 70], [2760, 900], [-820, 1400]])          # 平面 → 画面（算盘平放在案上、低机位斜看）
    def __init__(self):
        self.ab = BA.Abacus(5401, beam_h=170)
        r = np.random.default_rng(5405)
        self.c0 = list(r.choice([0, 0, 1, 2, 3], BA.NR).astype(float))
        self.up0 = list(r.choice([0, 0, 1], BA.NR).astype(float))
        self.cols = [2, 4, 6, 7, 9]                                                    # 每字拨哪一档（字刻在这档右侧梁上）
        self.txt = beam_text('牺牲多少才', [3.0, 4.7, 6.4, 8.1, 9.8], 150, beam_h=170)
        sk = night_sky(5402, top=(0.02, 0.022, 0.028), bot=(0.08, 0.08, 0.09), horizon=0.6)
        x, y = K.grid()
        table = wood_plane(5406)
        tm = sstep(380, 470, y)
        self.bg = sk * (1 - tm[..., None]) + table * tm[..., None]
        self.Mq = cv2.getPerspectiveTransform(np.float32([[0, 0], [BA.AW, 0], [BA.AW, BA.AH], [0, BA.AH]]), self.QUAD)
        self.rain = fx2.RainSheet(5403, density=0.8)
        self.spl = fx2.Splashes(5404)
        self.fog = fx2.Fog(5407)

    def state(self, t):
        c = list(self.c0); g = [0.0] * BA.NR
        for k, col in enumerate(self.cols):
            tk = V(CT(22, k))
            q = clamp01((t - (tk - 0.06)) / 0.12)
            c[col] = self.c0[col] + (5 - self.c0[col]) * q
            g[col] = pulse(t, tk, 0.25) * (t >= tk) * 2.0
        return c, g

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        c, g = self.state(t)
        rgb, al = self.ab.flat(c, self.up0, glow=g)
        for k, m in enumerate(self.txt):
            tk = V(CT(22, k))
            pk = clamp01((t - (tk - 0.04)) / 0.16)
            if pk > 0:
                rgb = gild(rgb, m * pk, glow=pulse(t, tk, 0.3) * (t >= tk))
        # 「牺牲」两字朱红（金里透红）
        for k in (0, 1):
            tk = V(CT(22, k))
            if t >= tk - 0.04:
                rgb = rgb * (1 - self.txt[k][..., None] * 0.5) + self.txt[k][..., None] * np.array([0.85, 0.08, 0.05], np.float32) * 0.5
        W_ = cv2.warpPerspective(rgb, self.Mq, (W, H), flags=cv2.INTER_LINEAR)
        A_ = cv2.warpPerspective(al, self.Mq, (W, H), flags=cv2.INTER_LINEAR)
        # 案面投影 + 远处雾化（景深）
        shd = cv2.GaussianBlur(np.roll(A_, 26, 0), (0, 0), 18)
        fr = fr * (1 - 0.6 * shd[..., None])
        x, y = K.grid()
        far = np.clip((620 - y) / 500, 0, 1)
        Wb = cv2.GaussianBlur(W_, (0, 0), 4)
        W_ = W_ * (1 - far[..., None]) + Wb * far[..., None]
        # 冷顶光 + 金字反光
        W_ = W_ * (0.6 + 0.5 * np.exp(-(((x - 700) / 900) ** 2 + ((y - 500) / 500) ** 2)))[..., None]
        fr = fr * (1 - A_[..., None]) + W_ * A_[..., None]
        fr = fr + A_[..., None] * far[..., None] * np.array([0.10, 0.11, 0.13], np.float32) * 0.6
        # 拨珠金光（bloom）
        hot = np.clip(fr - 0.75, 0, None)
        fr = fr + K.blur_ds(hot.max(-1), 20)[..., None] * GOLD * 0.8
        # 拨珠瞬间溅起雨珠
        for k, col in enumerate(self.cols):
            tk = V(CT(22, k))
            if tk <= t < tk + 0.6:
                fx_, fy_ = BA.M0 + (BA.AW - 2 * BA.M0) * (col + 0.5) / BA.NR, BA.BEAM_Y + 170 + 30
                p = cv2.perspectiveTransform(np.float32([[[fx_, fy_]]]), self.Mq)[0, 0]
                fr = K.sparks(fr, t, 5410 + k, (float(p[0]), float(p[1])), n=50, life=0.5, speed=(200, 700), dirc=(0, -1), spread=1.5, grav=1500,
                              size=1.6, area=(60, 10), color=(0.75, 0.8, 0.9), amt=1.0, t0=tk, burst=True)
        fr = self.spl.draw(fr, t, y_far=420, y_near=1000, rate=110, amt=0.55)
        fr = self.fog.draw(fr, t, density=0.25, y0=200, y1=600, color=(0.25, 0.26, 0.28))
        fr = self.rain.draw(fr, t, intensity=1.0, angle=8, light=(760, 260), light_r=700)
        hk = max(hitp(t, CT(22, k), 0.08) for k in range(5))
        dx, dy, dr = shake(t, 8 * hk, 14, 54)
        fr = cam(fr, 1.0 + 0.07 * eio(u) + 0.02 * hk, dx - 40 * eio(u), dy - 10 * eio(u), dr)
        return fr, (2 if hk > 0.5 else 0)


def wood_plane(seed):
    """湿漉漉的乌木案面（透视纹理 + 反光）"""
    x, y = K.grid()
    wd = BA.wood(H, W * 2, seed, base=(0.05, 0.03, 0.022))
    z = np.clip((y - 380) / 700, 0.02, 1)
    u_ = ((x - 960) / (z * 1.6 + 0.2) + W) % (W * 2)
    v_ = np.clip(380 + (1 / z) * 30 % H, 0, H - 1)
    pl = cv2.remap(wd, u_.astype(np.float32), v_.astype(np.float32) * 0 + y.astype(np.float32), cv2.INTER_LINEAR)
    sheen = np.exp(-(((x - 760) / 520) ** 2 + ((y - 560) / 120) ** 2)) * 0.10
    return (pl + sheen[..., None] * np.array([0.7, 0.75, 0.85], np.float32)).astype(np.float32)


# =====================================================================================
# V10 97.52–98.48 ECU 贴档微距：算珠沿竹档撞上梁（98.37 重拍：整档 5 颗一记砸上去，画面震、水花炸开）；「算够」大字烫金刻在梁上
class V10(Shot):
    T_HIT = 98.373
    QUAD = np.float32([[-2400, -1080], [5200, -1780], [3600, 2820], [-3300, 4020]])  # 只取算盘中段（4–8 档）放大到满屏、斜透视
    def __init__(self):
        self.ab = BA.Abacus(5501, beam_h=120)
        self.txt = beam_text('算够', [5, 7], 112, beam_h=120)
        self.Mq = cv2.getPerspectiveTransform(np.float32([[0, 0], [BA.AW, 0], [BA.AW, BA.AH], [0, BA.AH]]), self.QUAD)
        self.bg = BK.dark_bg(5503, 0.01, 0.03)
        self.rain = fx2.RainSheet(5504, density=0.5)

    def render(self, t):
        u = self.u(t)
        c = [5, 4, 5, 3, 2, 5, 0.0, 4, 5, 2, 3, 5, 1]
        g = [0.0] * BA.NR
        q = clamp01((t - (V(self.T_HIT) - 0.10)) / 0.10)
        c[6] = 5 * q ** 2
        g[6] = pulse(t, V(self.T_HIT), 0.3) * (t >= V(self.T_HIT)) * 1.0
        rgb, al = self.ab.flat(c, [1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1], glow=g)
        for k, m in enumerate(self.txt):
            tk = V(CT(22, 5 + k))
            pk = clamp01((t - (tk - 0.04)) / 0.16)
            if pk > 0:
                rgb = gild(rgb, m * pk, glow=pulse(t, tk, 0.3) * (t >= tk) + 0.3)
        Mq = self.Mq.copy()
        W_ = cv2.warpPerspective(rgb, Mq, (W, H), flags=cv2.INTER_LINEAR)
        A_ = cv2.warpPerspective(al, Mq, (W, H), flags=cv2.INTER_LINEAR)
        x, y = K.grid()
        # 浅景深：焦平面在梁（画面中部斜带），前后都虚
        foc = np.exp(-(((y - 0.18 * (x - 960)) - 460) / 260) ** 2)
        Wb = cv2.GaussianBlur(W_, (0, 0), 9); Ab = cv2.GaussianBlur(A_, (0, 0), 9)
        W_ = W_ * foc[..., None] + Wb * (1 - foc[..., None]); A_ = A_ * foc + Ab * (1 - foc)
        W_ = W_ * (0.7 + 0.7 * np.exp(-(((x - 900) / 800) ** 2 + ((y - 380) / 400) ** 2)))[..., None]
        fr = self.bg * (1 - A_[..., None]) + W_ * A_[..., None]
        hot = np.clip(fr - 0.8, 0, None)
        fr = fr + K.blur_ds(hot.max(-1), 24)[..., None] * GOLD * 0.5
        hk = hitp(t, self.T_HIT, 0.15)
        if t >= V(self.T_HIT):
            p = cv2.perspectiveTransform(np.float32([[[BA.M0 + (BA.AW - 2 * BA.M0) * 6.5 / BA.NR, BA.BEAM_Y + 120 + 20]]]), Mq)[0, 0]
            fr = K.sparks(fr, t, 5505, (float(p[0]), float(p[1])), n=160, life=0.6, speed=(300, 1300), dirc=(0, -1), spread=2.2, grav=1500,
                          size=2.2, area=(140, 10), color=(0.8, 0.85, 0.95), amt=1.0, t0=V(self.T_HIT), burst=True)
        fr = self.rain.draw(fr, t, intensity=0.6, angle=6)
        dx, dy, dr = shake(t, 30 * hk, 14, 55)
        fr = cam(fr, 1.0 + 0.05 * eio(u) + 0.06 * hk, dx + 30 * eio(u), dy, dr)
        return fr, (4 if hk > 0.5 else 0)


# =====================================================================================
# V11 98.48–99.47 ECU 平视微距：第七棒——不再盖「量」方印（撞副歌一 S043）、也不再用账簿纸面（生死簿第 3 次）。
#   雨夜里一杆乌木杆秤（生图 steelyard）横贯画面、浅景深；「分」「量」由秤杆上的铜秤星一颗颗点亮拼成（字 = 秤星），
#   99.0「量」落定时秤砣一沉、秤杆猛地向下一磕，杆上积的雨珠被震飞。前＝虚焦雨珠，中＝秤杆，后＝暗处宫灯散景。
def star_glyph(A, step=9, r=3.2, p=1.0, seed=0, order_y=False):
    """把字形遮罩换成秤星点阵：步长 step 的网格点落在字内 → 圆点；p 控制点亮比例（随机顺序逐颗亮）"""
    ys, xs = np.mgrid[0:H:step, 0:W:step]
    inside = A[ys, xs] > 0.45
    pts = np.stack([xs[inside], ys[inside]], -1)
    if len(pts) == 0: return np.zeros((H, W), np.float32)
    rr = np.random.default_rng(seed).random(len(pts))
    m = np.zeros((H // 1, W // 1), np.float32)
    for (px, py), q in zip(pts, rr):
        if q < p: cv2.circle(m, (int(px), int(py)), int(round(r)), 1.0, -1, cv2.LINE_AA)
    return m


class V11(Shot):
    T_LIANG = 99.0
    PIV, WPX = (1640, 545), 9000
    CH = [('分', 0.683), ('量', 0.746)]
    def __init__(self):
        self.sp = spr('B_r4/steelyard')
        x, y = K.grid()
        bg = BK.dark_bg(5601, 0.008, 0.025, tint=(1.0, 1.0, 1.08))
        r = np.random.default_rng(5602)
        bok = np.zeros((H, W), np.float32)
        for _ in range(16):
            cv2.circle(bok, (int(r.uniform(0, W)), int(r.uniform(150, 900))), int(r.uniform(30, 80)), float(r.uniform(0.3, 1.0)), -1, cv2.LINE_AA)
        bok = cv2.GaussianBlur(bok, (0, 0), 10)
        self.bg = bg + bok[..., None] * np.array([0.30, 0.13, 0.05], np.float32) * 0.5
        self.rain = fx2.RainSheet(5603, density=0.7)
        self.drops = r.uniform(0, 1, (40, 3))

    def ang(self, t):
        th = V(self.T_LIANG)
        if t < th: return -1.5 + 0.6 * math.sin(t * 3.0)
        q = t - th
        return -1.5 + 6.5 * (1 - math.exp(-q / 0.06)) + 2.0 * math.exp(-q / 0.25) * math.sin(q * 30)

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        fr = self.bg.copy()
        rot = self.ang(t)
        pivot = self.PIV                                                              # 提绳处（秤纽）为支点
        fr, Aw = put_at(fr, self.sp, t, (0.80, 0.29), pivot, self.WPX, rot=rot,
                        grade=dict(expo=0.95, sat=0.75, tint=(1.04, 0.97, 0.90), lift=0.0, gamma=1.05),
                        rim=dict(col=(0.85, 0.9, 1.0), amt=1.8, dir=(0.0, -1.0)), wind_amp=0, breathe=0.0, shade=None, wrap=0.25)
        # 浅景深：焦平面在两字之间
        cxs = [sp_pt(self.sp, (0.80, 0.29), pivot, self.WPX, rot, (cx, 0.29)) for _, cx in self.CH]
        fx_ = 0.5 * (cxs[0][0] + cxs[1][0])
        foc = np.exp(-((x - fx_) / 760) ** 2)[..., None]
        fr = fr * foc + K.blur_ds(fr, 9) * (1 - foc)
        fr = fr + np.exp(-((y - (cxs[0][1] - 50)) / 40) ** 2)[..., None] * np.array([0.05, 0.055, 0.065], np.float32) * Aw[..., None]   # 杆面顶光
        th = V(self.T_LIANG)
        for i, (ch, cx) in enumerate(self.CH):
            tk = V(CT(22, 7 + i))
            p = clamp01((t - (tk - 0.12)) / 0.2)
            if p <= 0: continue
            c = cxs[i]
            A = BV.mask([(ch, c[0], c[1], 195, -rot)], fname='serif_black')
            Ab = K.blur_ds(A, 10)
            fr = fr * (1 - Ab[..., None] * 0.6 * Aw[..., None] * min(1, p * 2))          # 字区压暗（原有秤星让位）
            Ap, _ = BV.reveal(A, p, axis='x', soft=30)                                    # 秤星一路亮过去
            st = star_glyph(A, step=7, r=2.6, p=p, seed=5610 + i) * Aw
            hot = pulse(t, tk, 0.3) * (t >= tk)
            fr = BV.engrave(fr, Ap, light=(0.0, -1.0), depth=3, groove=0.5, fill=(0.90, 0.68, 0.36), fill_k=0.7, hl=0.4, surface=Aw)
            fr = fr + st[..., None] * Ap[..., None] * np.array([1.0, 0.85, 0.55], np.float32) * (0.5 + 0.8 * hot)
            fr = fr + K.blur_ds(Ap * Aw, 10)[..., None] * np.array([1.0, 0.6, 0.25], np.float32) * (0.25 + 0.9 * hot)
        # 秤杆上的雨珠：落定前沿杆滚动，99.0 一磕全部震飞
        hk = hitp(t, self.T_LIANG, 0.14)
        if t >= th:
            fr = K.sparks(fr, t, 5606, (fx_, cxs[0][1] - 40), n=140, life=0.6, speed=(250, 900), dirc=(0, -1), spread=1.7, grav=1500, size=1.6,
                          area=(900, 10), color=(0.78, 0.84, 0.95), amt=1.0, t0=th, burst=True)
        else:
            for (a_, b_, c_) in self.drops:
                px = int(a_ * W + 40 * math.sin(t * 2 + c_ * 9)); py = int(cxs[0][1] - 62 + (px - fx_) * math.tan(math.radians(-rot)))
                cv2.circle(fr, (px, py), 3 + int(3 * b_), (0.55, 0.60, 0.70), -1, cv2.LINE_AA)
        fr = self.rain.draw(fr, t, intensity=0.8, angle=6)
        dx, dy, dr = shake(t, 20 * hk, 13, 56)
        fr = cam(fr, 1.02 + 0.04 * eio(u) + 0.03 * hk, dx - 30 * eio(u), dy, dr)
        return fr, (4 if hk > 0.5 else 0)


# =====================================================================================
# V12 99.47–100.58 ECU：一个名帖纸人（身上写着名字）从账簿边被风雨卷落，翻转着朝镜头坠下、越来越大，雨打湿它、名字的墨化开；
#   「被牺牲的人」马善政竖排，随它下坠、遇雨晕开
class V12(Shot):
    def __init__(self):
        self.fig = BC.figs('effigy_fall')[0]     # 第五棒：名帖纸人 → 生图湿透纸扎人坠落
        self.far = self.fig                       # 远处群坠 = 同一张（同镜内）
        self.bg = BK.dark_bg(5702, 0.006, 0.025)
        ab = BA.Abacus(5706, beam_h=120)
        rgb, al = ab.flat([5, 2, 3, 5, 0, 1, 4, 5, 2, 0, 3, 5, 1])
        Q = np.float32([[-300, -900], [2300, -1000], [2200, 240], [-200, 300]])
        Mq = cv2.getPerspectiveTransform(np.float32([[0, 0], [BA.AW, 0], [BA.AW, BA.AH], [0, BA.AH]]), Q)
        self.abW = cv2.GaussianBlur(cv2.warpPerspective(rgb, Mq, (W, H)), (0, 0), 7) * 0.6
        self.abA = cv2.GaussianBlur(cv2.warpPerspective(al, Mq, (W, H)), (0, 0), 7)
        self.rain = fx2.RainSheet(5703, density=0.6)
        self.mist = fx2.Fog(5705)
        T.warm('被牺牲的人', 'kai', 110)
        self.wn = K.tile(256, 5707, 6, 3); self.rr = np.random.default_rng(5708).uniform(0, 1, (22, 3))

    def pose(self, t):
        q = clamp01((t - self.t0) / (self.t1 - self.t0))
        x = 700 + 120 * math.sin(q * 2.6)
        yfoot = 140 + 200 * q                              # 头朝下栽落（tilt≈180：脚在上）
        h = 640 + 460 * q ** 1.3
        tilt = 140 + 70 * q + 6 * math.sin(q * 9)
        card = 28 * math.sin(q * 7.5)                    # 纸在风里翻面
        return x, yfoot, h, tilt, card, q

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        x, y = K.grid()
        # 上方：算盘底框（虚焦）随下摇离开画面；远处还有更多纸人在坠落（景深虚化）
        oy = -380 * eio(u)
        Mt = np.float32([[1, 0, 0], [0, 1, oy]])
        aW = cv2.warpAffine(self.abW, Mt, (W, H)); aA = cv2.warpAffine(self.abA, Mt, (W, H))
        fr = fr * (1 - aA[..., None]) + aW * aA[..., None]
        for i in range(7):
            ph = (i * 0.37) % 1.0
            qq = (u * 0.8 + ph) % 1.0
            fx_ = 160 + i * 250 + 40 * math.sin(t * 2 + i)
            fr, _ = BC.draw(fr, self.far, (fx_, -100 + 1300 * qq), 170 + 30 * (i % 3), tilt=70 * math.sin(i * 1.7 + t * 1.5) + 150, flip=bool(i % 2),
                            expo=0.35, sat=0.3, rim_col=(0.5, 0.55, 0.7), rim_amt=0.4, alpha=0.6, blur=5 + 2 * (i % 3), wet=0.6)
        fr = self.mist.draw(fr, t, density=0.35, y0=300, y1=1000, color=(0.18, 0.19, 0.22))
        # 运动拖影：前 3 个时刻的半透明残影
        for k, dt in enumerate((0.09, 0.05, 0.0)):
            px, py, h, tl, cd, q = self.pose(t - dt)
            wet = 0.25 + 0.6 * clamp01(q * 1.2)                # 第四棒：雨打湿更重（墨晕开）、整体压暗冷调，去「奶油色纸板」感
            fr, _ = BC.draw(fr, self.fig, (980 + 80 * q + 40 * math.sin(q * 2.6), 620 + 300 * q), 500 + 300 * q ** 1.3, tilt=-6 + 30 * q + 4 * math.sin(q * 9),
                            expo=0.95, sat=0.5, tint=(0.94, 0.97, 1.04), rim_col=(0.80, 0.86, 1.0), rim_amt=0.7, rim_dir=(-0.6, -0.8), alpha=(0.15, 0.25, 1.0)[k], blur=(6, 3, 0.6)[k] + 1.2 * q, wet=wet)
        # 第八棒（P2-14：纸人贴在黑底上没有空间）：单一冷顶光柱（左上 → 右下）+ 积水地面 GL=880 + 坠落纸人在水面上的倒影与雨点涟漪
        GL = 880
        beam = np.exp(-(((x - 0.45 * (y - 0)) - 640) / 260) ** 2) * np.clip(1 - y / 1300, 0.2, 1)
        fr = fr * (0.78 + 0.22 * beam[..., None]) + beam[..., None] * np.array([0.08, 0.088, 0.11], np.float32)
        refl = np.zeros_like(fr); refl[GL:] = fr[GL - 1::-1][:H - GL]
        nz = cv2.resize(K.tile_crop(self.wn, t * 25, t * 60, H // 8, W // 8), (W, H))
        refl = cv2.remap(refl, (x + (nz - 0.5) * 14).astype(np.float32), (y + (nz - 0.5) * 6).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        low = sstep(GL - 2, GL + 3, y)[..., None]
        ground = 0.02 + 0.015 * nz[..., None]
        fr = fr * (1 - low) + (ground + refl * np.array([0.60, 0.65, 0.76], np.float32) * np.clip(1.2 - (y - GL) / 260, 0, 1)[..., None]) * low
        fr += np.exp(-((y - GL) / 3.0) ** 2)[..., None] * np.array([0.16, 0.17, 0.20], np.float32) * (0.5 + beam[..., None])
        cs = [(a_ * W, GL + 20 + b_ * 180) for a_, b_, _ in self.rr]; ts = [math.floor(t * 2 + c_ * 2) / 2 - c_ * 0.5 for _, _, c_ in self.rr]
        fr = fx2.ripples(fr, t, cs, ts, amt=0.5, flat=0.3, speed=150, life=0.9)
        pr = prs(23, [0, 1, 2, 3, 4], t, 0.22)
        P = [dict(ch=c, x=1360, y=250 + i * 128 + 60 * eio(u), size=112, rot=0, font='kai', idx=i, emph=c in '牺牲') for i, c in enumerate('被牺牲的人')]
        fr = fr * (1 - 0.65 * K.blur_ds(((np.abs(x - 1360) < 95) & (y > 180) & (y < 980)).astype(np.float32), 30)[..., None])   # 第七棒：暗衬加重，「的人」可读
        fr = T.ink_bleed_in(fr, '被牺牲的人', pr, places=P, color='white', emph_color=(0.90, 0.14, 0.09), bleed=1.4,
                            style_kw=dict(shadow=0.9, glow=0.1))
        fr = self.rain.draw(fr, t * 0.6 + self.t0 * 0.4, intensity=0.8, angle=4)
        fr = cam(fr, 1.04, 0, 0, 2 * u)
        return fr, 0


# =====================================================================================
# V13 100.58–102.14 MS：坠落的纸人剪影落地——匹配剪辑：同一位置同一姿态变成鬼屠，从泥水里起身（rise）；「可曾有机会」马善政右侧
class V13(Shot):
    def __init__(self):
        self.sp = spr('S054/rise')
        sk = night_sky(5801, top=(0.02, 0.022, 0.03), bot=(0.12, 0.125, 0.14), horizon=0.78)
        x, y = K.grid()
        self.gm = sstep(830, 850, y)
        mud = (0.02 + 0.035 * cv2.resize(K.fbm(H // 2, W // 2, 5802, 10, 6), (W, H)))[..., None] * np.ones(3, np.float32)
        self.bg = sk * (1 - self.gm[..., None]) + mud * self.gm[..., None]
        self.fig = BP.NameFigure(5701, name='许平', view='front')
        self.rain = fx2.RainSheet(5803, density=1.0)
        self.spl = fx2.Splashes(5804)
        self.fog = fx2.Fog(5805)
        T.warm('可曾有机会', 'kai', 110)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        fr = self.fog.draw(fr, t, density=0.5, y0=500, y1=860, color=(0.32, 0.34, 0.37))
        # 第六棒：去掉开头 0.2s 纸人剪影坠地（f3017–3022 黑色硬边块穿帮 + 空画面）。人物首帧即在画内（半跪），
        # 入镜 = 落拍 punch + 泥水冲击：他单膝砸进泥水的瞬间，泥浆与水花呈冠状向两侧炸开、冷光冲击环扩散
        tl = self.t0
        k = eout(clamp01((t - tl) / 1.25), 2)          # 起身：从半跪抬升
        fr, _ = put(fr, self.sp, t, 640 + 80 * k, (840, 900 + 80 * (1 - k)), rim=dict(col=(0.70, 0.80, 1.0), amt=2.4, dir=(0.5, -1.0)),
                    wind_amp=6, shade=(500, 1500, 0.25, 600, 0.3))
        if t < tl + 0.45:
            fr = K.sparks(fr, t, 5806, (840, 900), n=140, life=0.55, speed=(300, 900), dirc=(0, -1), spread=1.5, grav=1500,
                          area=(320, 10), color=(0.62, 0.68, 0.78), amt=1.0, t0=tl - 1 / 30, burst=True)
            x_, y_ = K.grid()
            rr = 60 + 1500 * clamp01((t - tl + 1 / 30) / 0.45)
            ring = np.exp(-((np.sqrt(((x_ - 840) / 1.0) ** 2 + ((y_ - 905) * 3.2) ** 2) - rr) / 14) ** 2) * (y_ > 840)
            fr = fr + ring[..., None] * COLDC * 0.35 * (1 - clamp01((t - tl) / 0.45))
        fr = self.spl.draw(fr, t, y_far=850, y_near=1000, rate=120, amt=0.7)
        fr = self.rain.draw(fr, t, intensity=1.1, angle=10)
        pr = prs(23, [5, 6, 7, 8, 9], t)
        P = [dict(ch=c, x=1480 + (i % 2) * 40, y=250 + i * 120, size=104, rot=0, font='kai', idx=i, emph=False) for i, c in enumerate('可曾有机会')]
        fr = T.ink_bleed_in(fr, '可曾有机会', pr, places=P, color='white', style_kw=dict(shadow=0.85, glow=0.12))
        e = eio(u)
        fr = cam(fr, 1.0 + 0.18 * e, 0, -60 * e)
        return fr, (3 if abs(t - tl) < 0.04 else 0)


# =====================================================================================
# V14 102.14–103.14 LS 低机位：第七棒——不再只有字。鬼屠在跪满纸扎百官的雨地里猛然起身（生图 stand_defy，束发、怒吼、刀垂手）；
#   102.18「反」：起身的气浪以他脚下为圆心炸开一圈泥水冲击环，周围跪伏的纸人被掀得向后仰倒；「反」「抗」两字（马善政楷，朱红，同一字体）
#   随气浪从泥地里拔起、带着火星与泥点立定在他身侧。前＝虚焦跪伏纸人，中＝人，后＝雨幕中更多跪着的人影。
class V14(Shot):
    FOOT = (760, 1040)
    def __init__(self):
        self.sp = spr('B_r4/stand_defy')
        self.figs = BC.figs('crowd_bow')
        sk = night_sky(5901, top=(0.02, 0.022, 0.03), bot=(0.12, 0.12, 0.13), horizon=0.75)
        x, y = K.grid()
        self.gm = sstep(760, 790, y)
        mud = (0.02 + 0.035 * cv2.resize(K.fbm(H // 2, W // 2, 5902, 10, 6), (W, H)))[..., None] * np.ones(3, np.float32)
        self.bg = sk * (1 - self.gm[..., None]) + mud * self.gm[..., None]
        self.bg += np.exp(-(((x - 760) / 420) ** 2 + ((y - 520) / 380) ** 2))[..., None] * np.array([0.10, 0.06, 0.05], np.float32)
        r = np.random.default_rng(5903)
        self.back = [(r.uniform(-50, 1970), r.uniform(770, 800), r.uniform(150, 200), int(r.integers(6))) for _ in range(12)]
        self.front = [(80, 1180, 760, 1, True), (1900, 1180, 760, 4, False)]
        self.fog = fx2.Fog(5904)
        self.rain = fx2.RainSheet(5905, density=1.0)
        self.spl = fx2.Splashes(5906)
        T.warm('反抗', 'kai', 270)

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        fr = self.bg.copy()
        tf = V(CT(23, 10)); tk2 = V(CT(23, 11))
        blast = clamp01((t - tf) / 0.5)
        push = eout(blast, 2)
        fr = self.fog.draw(fr, t, density=0.45, y0=520, y1=820, color=(0.30, 0.31, 0.34), speed=(20 + 260 * pulse(t, tf, 0.4), 0))
        for (bx, fy, hh, idx) in self.back:                                   # 远排跪伏的人（被气浪推得后仰）
            away = 1 if bx > self.FOOT[0] else -1
            fr, _ = BC.draw(fr, self.figs[idx], (bx, fy), hh, tilt=-20 + 14 * push * away, flip=bx < self.FOOT[0], expo=0.40, sat=0.4,
                            rim_col=(0.6, 0.65, 0.8), rim_amt=0.6, blur=2.5, wet=0.4)
        rise = eout(clamp01((t - self.t0) / 0.30), 3)                          # 起身：0.3s 内从画下拔起站定
        fr, _ = put(fr, self.sp, t, 860 * (0.96 + 0.04 * rise), (self.FOOT[0], self.FOOT[1] + 170 * (1 - rise)),
                    rim=dict(col=(0.80, 0.86, 1.0), amt=3.0, dir=(0.4, -1.0)),
                    grade=dict(expo=1.05, sat=0.6, tint=(0.95, 0.97, 1.04), lift=0.01, gamma=1.08), wind_amp=10,
                    shade=(500, 1600, 0.15, 600, 0.3), mblur=(0, 30 * (1 - rise)))
        if t >= tf:                                                            # 泥水冲击环
            q = t - tf
            d = np.sqrt((x - self.FOOT[0]) ** 2 + ((y - self.FOOT[1] + 10) * 4.0) ** 2)
            R = 80 + 1800 * eout(clamp01(q / 0.5), 2)
            ring = np.exp(-((d - R) / (16 + 40 * q)) ** 2) * (y > 760) * (1 - clamp01(q / 0.5))
            fr = fr + ring[..., None] * COLDC * 0.5
            fr = K.sparks(fr, t, 5907, (self.FOOT[0], self.FOOT[1] - 10), n=180, life=0.6, speed=(300, 1100), dirc=(0, -1), spread=2.6,
                          grav=1600, size=1.6, area=(260, 10), color=(0.55, 0.55, 0.58), amt=1.0, t0=tf, burst=True)
        # 「反」「抗」从泥里拔起立定（马善政楷，同一字体，朱红）
        for i, (ch, tk, cx, cy) in enumerate((('反', tf, 1300, 420), ('抗', tk2, 1380, 690))):
            p = clamp01((t - (tk - 0.04)) / 0.22)
            if p <= 0: continue
            e = eout(p, 3)
            L = T.Layer(); T.place(L, ch, cx, cy + 320 * (1 - e), 270, color=(0.92, 0.14, 0.07), fname='kai', alpha=min(1, p * 2.5),
                                    sy=0.75 + 0.25 * e, blur=6 * (1 - e))
            fr = fr * (1 - 0.5 * K.blur_ds(L.A, 24)[..., None])
            fr = T.compose(fr, L, shadow=0.9, outline=2, outline_color=(0.10, 0.01, 0.01), glow=0.5 + 0.6 * pulse(t, tk, 0.3), glow_color=(1.0, 0.3, 0.08))
            fr = K.sparks(fr, t, 5910 + i, (cx, cy + 150), n=80, life=0.5, speed=(200, 800), dirc=(0, -1), spread=1.2, grav=1200,
                          size=1.4, area=(160, 10), color=(1.0, 0.55, 0.2), amt=1.0, t0=tk, burst=True)
        for (fx_, fy, hh, idx, fl) in self.front:                             # 前景虚焦跪伏纸人
            fr, _ = BC.draw(fr, self.figs[idx], (fx_ + (-40 if fl else 40) * push, fy), hh, tilt=-24 + 10 * push * (-1 if fl else 1), flip=fl,
                            expo=0.30, sat=0.35, rim_col=(0.6, 0.66, 0.85), rim_amt=0.9, rim_dir=(0.0, -1.0), sil=0.6, blur=9, wet=0.4)
        fr = self.spl.draw(fr, t, y_far=780, y_near=1000, rate=140, amt=0.7)
        fr = self.rain.draw(fr, t, intensity=1.0, angle=8)
        hk = max(hitp(t, CT(23, 10), 0.12), hitp(t, CT(23, 11), 0.12))
        dx, dy, dr = shake(t, 3 + 16 * hk, 10, 59)
        fr = cam(fr, 1.0 + 0.05 * eio(u) + 0.04 * hk, dx, dy, dr)
        return fr, (3 if hk > 0.5 else 0)


# =====================================================================================
# V15 103.14–104.30 LS：鬼屠在暴雨中行走（walk_look_up），103.99 闪电照亮，他抬头；「不听天命」两列竖排，「天命」被朱红斜线划掉
class V15(Shot):
    T_BOLT = 103.987
    def __init__(self):
        self.sp = spr('S055/walk_look_up')
        sk = night_sky(6001, top=(0.02, 0.022, 0.03), bot=(0.10, 0.105, 0.12), horizon=0.8)
        wl, wm = city_wall_far(6002, 600, 820, tone=0.05, crenel=False)
        wl = K.blur_ds(wl, 4); wm = K.blur_ds(wm, 4)
        self.bg = sk * (1 - wm[..., None]) + wl * wm[..., None]
        x, y = K.grid()
        self.gm = sstep(820, 840, y)
        self.bg = self.bg * (1 - self.gm[..., None]) + self.gm[..., None] * 0.03
        self.bolt = fx2.Lightning(6003, p0=(1500, 120), p1=(1700, 700), branches=6)
        self.rain = fx2.RainSheet(6004, density=1.2)
        self.spl = fx2.Splashes(6005)
        T.warm('不听天命', 'kai', 120)

    def render(self, t):
        u = self.u(t)
        e = eio(u)
        tl = V(self.T_BOLT)
        env = 0.0 if t < tl - 0.02 else math.exp(-max(0, t - tl) / 0.3)
        fr = self.bg * (1 + 2.5 * env)
        if t >= tl - 0.06:
            fr = self.bolt.draw(fr, t, tl, intensity=1.1)
        walk = 1120 - 90 * e
        bob = 6 * abs(math.sin(t * 6.5))
        # 第三棒：人物放大提亮（820→1000px，常亮冷轮廓 + 前左方冷补光），闪电时再炸亮
        x_, y_ = K.grid()
        fr = fr + np.exp(-(((x_ - walk) / 380) ** 2 + ((y_ - 560) / 420) ** 2))[..., None] * np.array([0.10, 0.12, 0.16], np.float32)
        fr, _ = put(fr, self.sp, t, 880, (walk, 1100 - bob),   # 第八棒：1000→880，头顶不再顶黑边
                     rim=dict(col=(0.80, 0.88, 1.0), amt=3.6 + 4 * env, dir=(0.7, -0.7)),
                    grade=dict(expo=1.18 + 0.4 * env, sat=0.55, tint=(0.92, 0.97, 1.06), lift=0.02, gamma=1.05), wind_amp=8,
                    shade=(500, 1500, 0.12, 600, 0.2))
        # 积水反光
        ref = fr[::-1].copy(); ref = cv2.warpAffine(ref, np.float32([[1, 0, 0], [0, 1, 2 * 860 - H]]), (W, H))
        fr = fr + ref * (self.gm * 0.25)[..., None]
        fr = self.spl.draw(fr, t, y_far=830, y_near=1000, rate=160, amt=0.8)
        fr = self.rain.draw(fr, t, intensity=1.2, angle=14, light=(1500, 150) if env > 0.1 else None, light_r=900, cam=(80 * e, 0))
        pr = prs(24, [0, 1, 2, 3], t)
        P = [dict(ch='不', x=520, y=300, size=120, rot=0, font='kai', idx=0, emph=False), dict(ch='听', x=520, y=430, size=120, rot=0, font='kai', idx=1, emph=False),
             dict(ch='天', x=380, y=380, size=150, rot=0, font='serif_black', idx=2, emph=False), dict(ch='命', x=380, y=540, size=150, rot=0, font='serif_black', idx=3, emph=False)]
        L = T.Layer()
        for pp, pc in zip(P, pr):
            if pc > 0: T.place(L, pp['ch'], pp['x'], pp['y'], pp['size'], color='gold' if pp['font'] == 'serif_black' else 'white',
                               fname=pp['font'], alpha=min(1, pc * 2), scale=1.2 - 0.2 * eout(pc))
        fr = T.compose(fr, L, shadow=0.85, glow=0.15)
        ps = clamp01((t - (V(CT(24, 3)) + 0.12)) / 0.16)
        if ps > 0: fr = T.strike(fr, P, [2, 3], ps, color='red', width=0.16, seed=60)
        fr = cam(fr, 1.0 + 0.05 * e, 30 * e, 0, (0.8 * math.sin(t * 1.7)))
        return fr, (3 if abs(t - tl) < 0.04 else 0)


# =====================================================================================
# V16 104.30–105.88 低机位仰拍：第七棒——不再是只有字和放射线。暴雨天幕下一通龙首天碑（生图 heaven_stele）顶天立地，
#   云眼金光在碑首后；「上」「苍」随字头被天雷一记记凿进碑心（阴刻嵌金、石屑迸溅），「苍」读满一拍后，
#   105.62 一道刀光自画外斜劈，碑身沿刀线断开、上半截错落下滑、碎石崩飞——「不问上苍」。「不问」志莽行书在左（鬼屠的话），不出画。
class V16(Shot):
    T_SLASH = 105.62
    SRC, DST, WPX = (0.50, 0.50), (1080, 640), 1900
    CH = [('上', (0.500, 0.365), 225), ('苍', (0.500, 0.625), 225)]
    def __init__(self):
        x, y = K.grid()
        self.c = (1080, 120)
        d = np.sqrt((x - 1080) ** 2 + ((y - 120) * 1.4) ** 2); a = np.arctan2(y - 120, x - 1080)
        n = cv2.resize(K.fbm(H // 4, W // 4, 6101, 5, 6), (W, H))
        swirl = cv2.resize(K.tile(512, 6102, 6, 5), (W, H))
        self.d, self.a, self.n, self.sw = d, a, n, swirl
        self.sp = spr('B_r4/heaven_stele')
        self.rain = fx2.RainSheet(6104, density=1.0)
        self.bolt = fx2.Lightning(6105, p0=(300, 120), p1=(560, 760), branches=5)
        T.warm('不问', 'xing', 190)

    def sky(self, t):
        d, a = self.d, self.a
        rot = a + 0.20 * t + 500 / (d + 200)
        tex = self.sw[(np.clip(d * 0.4 + t * 40, 0, 1e6).astype(np.int32)) % H, ((rot % (2 * math.pi)) / (2 * math.pi) * W).astype(np.int32) % W]
        cloud = 0.025 + 0.15 * np.clip(tex * 0.7 + self.n * 0.5 - 0.2, 0, 1) ** 1.4
        eye = np.exp(-(d / 330) ** 2)
        return lum3(cloud, (0.95, 0.98, 1.08)) * (1 - eye[..., None] * 0.6) + eye[..., None] * GOLD * 0.30

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        fr = self.sky(t)
        tb = V(CT(24, 4))                                                       # 「不」104.34 的远雷
        env = math.exp(-max(0.0, t - tb) / 0.25) * (t >= tb - 0.02)
        fr = fr * (1 + 1.6 * env)
        if t >= tb - 0.04: fr = self.bolt.draw(fr, t, tb, intensity=0.9)
        z = np.zeros_like(fr)
        Fz, Aw = put_at(z, self.sp, t, self.SRC, self.DST, self.WPX,
                        grade=dict(expo=0.95, sat=0.35, tint=(0.94, 0.97, 1.04), lift=0.0, gamma=1.05),
                        rim=dict(col=GOLD * 1.1, amt=2.2, dir=(0.0, -1.0)), wind_amp=0, breathe=0.0, shade=(400, 1900, 0.0, 300, 0.55), wrap=0.0)
        Fz = Fz * (0.55 + 0.6 * np.exp(-(((x - 1080) / 500) ** 2 + ((y - 380) / 420) ** 2)))[..., None] * (1 + 0.8 * env)
        chips = []
        for i, (ch, nrm, sz) in enumerate(self.CH):
            tk = V(CT(24, 6 + i))
            p = clamp01((t - (tk - 0.04)) / 0.14)
            if p <= 0: continue
            c = (self.DST[0] + (nrm[0] - self.SRC[0]) * self.WPX, self.DST[1] + (nrm[1] - self.SRC[1]) * self.WPX * self.sp.h / self.sp.w)
            A = BV.mask([(ch, c[0], c[1], sz, 0)], fname='serif_black')
            A, front = BV.reveal(A, p)
            hot = pulse(t, tk, 0.35) * (t >= tk)
            Fz = BV.engrave(Fz, A, light=(0.0, -1.0), depth=6, groove=0.7, fill=(0.92, 0.70, 0.34), fill_k=0.75, hl=0.35,
                            surface=Aw, glow=0.2 + 0.8 * hot, glow_col=(1.0, 0.62, 0.25))
            if front is not None and p < 1: chips.append((front, tk))
        ts = V(self.T_SLASH)
        p0, p1 = (600, 300), (1560, 412)                                        # 刀线：斜穿碑首下、「上」字下沿之上，「苍」不被切
        if t >= ts:
            q = t - ts
            fall = eout(clamp01(q / 0.22), 2)
            Fz, Aw2, line = BV.split_layer(Fz, Aw, p0, p1, (-60 * fall, 70 * fall + 160 * q * q), (6 * fall, 6 * fall))
            Aw = Aw2
            crack = line * Aw * math.exp(-q / 0.25)
            Fz = Fz + crack[..., None] * np.array([1.0, 0.55, 0.25], np.float32) * 1.5
        fr = fr * (1 - Aw[..., None]) + Fz
        for (fx_, fy_), tk in chips:
            fr = K.sparks(fr, t, 6110 + int(fy_), (fx_, fy_), n=70, life=0.4, speed=(200, 800), dirc=(0, -1), spread=2.0, grav=1600,
                          size=1.5, area=(40, 10), color=(1.0, 0.8, 0.5), amt=1.1, t0=tk - 0.04, burst=True)
        if t >= ts - 0.05:                                                     # 刀光：自左上画外斜劈过碑
            ql = clamp01((t - (ts - 0.05)) / 0.10)
            dx_, dy_ = p1[0] - p0[0], p1[1] - p0[1]; nn = math.hypot(dx_, dy_)
            dist = ((x - p0[0]) * dy_ - (y - p0[1]) * dx_) / nn
            along = ((x - p0[0]) * dx_ + (y - p0[1]) * dy_) / nn
            band = np.exp(-(dist / (2 + 14 * (1 - ql))) ** 2) * (along < -500 + 2400 * ql) * math.exp(-max(0.0, t - ts) / 0.18)
            fr = fr + band[..., None] * np.array([1.0, 0.92, 0.85], np.float32) * 1.6 + K.blur_ds(band, 16)[..., None] * RED * 0.9
            fr = K.sparks(fr, t, 6120, (1080, 350), n=70, life=0.7, speed=(200, 800), dirc=(0.3, -1), spread=2.0, grav=1600,
                          size=1.6, area=(220, 20), color=(0.42, 0.40, 0.38), amt=0.9, t0=ts, burst=True)
        fr = self.rain.draw(fr, t, intensity=1.0, angle=8, light=(1080, 120), light_r=700)
        pb = prs(24, [4, 5], t)
        fr = T.scatter_stack(fr, '不问', pb, places=[dict(ch='不', x=360, y=360, size=180, rot=-6, font='xing', idx=0, emph=False),
                                                       dict(ch='问', x=440, y=600, size=210, rot=5, font='xing', idx=1, emph=True)],
                             color='white', emph_color=(0.86, 0.10, 0.06), t_local=u, style_kw=dict(shadow=0.85))
        hk = hitp(t, self.T_SLASH, 0.14)
        dx, dy, dr = shake(t, 3 + 22 * hk, 12, 616)
        fr = cam(fr, 1.0 + 0.06 * eio(u) + 0.04 * hk, dx, dy + 20 * eio(u), dr)
        return fr, (4 if hk > 0.5 else 0)


# =====================================================================================
# V17 105.88–107.55 MCU：张开的手掌承接雨水（palm_open，掌在左前景、脸在中），掌心积水倒映朱红「命」；「谁的」马善政，「都」小字
class V17(Shot):
    PALM = (620, 870)   # 第八棒：760→870，整人下移，发顶束发入画
    def __init__(self):
        self.sp = spr('B_r4/palm_open2')          # 第七棒：束发版（造型统一）
        self.bg = BK.dark_bg(6201, 0.01, 0.035)
        self.rain = fx2.RainSheet(6202, density=0.9)
        T.warm('谁的', 'kai', 120); T.warm('命', 'serif_black', 150); T.warm('都', 'kai', 90)

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        fr = self.bg + np.exp(-(((x - 1000) / 700) ** 2 + ((y - 300) / 500) ** 2))[..., None] * COLDC * 0.08
        fr, _ = put_at(fr, self.sp, t, (0.19, 0.835), self.PALM, 1600,   # 第八棒：1750→1600，发顶入画
                        rim=dict(col=(0.72, 0.80, 1.0), amt=2.2, dir=(-0.6, -0.8)),
                       wind_amp=4, shade=(900, 1900, 0.3, 700, 0.2))
        # 掌心积水 + 倒影「命」（随涟漪抖动），107.08 字头亮起
        cx, cy = self.PALM[0] + 10, self.PALM[1] - 20
        pool = np.exp(-(((x - cx) / 150) ** 2 + ((y - cy) / 60) ** 2) ** 2)
        pm = prs(25, [2], t, 0.3)[0]
        if pm > 0:
            L = T.Layer(); T.place(L, '命', cx, cy, 190, color='red', fname='serif_black', alpha=min(1, pm * 1.5), sy=0.45)
            wob = np.sin((x - cx) * 0.08 + t * 14) * 3 + np.sin((y - cy) * 0.3 + t * 9) * 2
            A = cv2.remap(L.A, x + wob.astype(np.float32), y, cv2.INTER_LINEAR) * pool
            fr = fr * (1 - A[..., None] * 0.7) + A[..., None] * np.array([0.95, 0.10, 0.06], np.float32)
            fr += K.blur_ds(A, 16)[..., None] * RED * 0.6
        fr += pool[..., None] * COLDC * 0.10
        fr = fx2.ripples(fr, t, [(cx - 30, cy), (cx + 40, cy + 6), (cx, cy - 4)], [106.0, 106.5, 107.0], amt=0.6, flat=0.35, speed=90, life=0.9)
        fr = self.rain.draw(fr, t, intensity=0.9, angle=6)
        pr = prs(25, [0, 1, 3], t)
        P = [dict(ch='谁', x=1460, y=330, size=130, rot=0, font='kai', idx=0, emph=False), dict(ch='的', x=1460, y=470, size=110, rot=0, font='kai', idx=1, emph=False),
             dict(ch='都', x=1600, y=640, size=96, rot=0, font='kai', idx=2, emph=False)]
        fr = T.ink_bleed_in(fr, '谁的都', pr, places=P, color='white', style_kw=dict(shadow=0.85, glow=0.12))
        fr = cam(fr, 1.0 + 0.12 * eio(u), 0, 0, center=(cx, cy))
        return fr, 0


# =====================================================================================
# V18 107.55–108.34 CU：107.58「握」猛然握拳（palm_fist），水花炸开；「握在自己」志莽行书从水花中迸出
class V18(Shot):
    """第九棒：critic_B_r3 不可交付（S056/palm_fist 泥团手）→ 重生 fist3（四指分开、指缝 / 指甲 / 指节清楚），
    不再用 2300px 放大 + 运动模糊糊掉；「握在自己」改马善政楷（原志莽行书「握」读成「搖」），与 V17/V19 同一句同一字体"""
    T_WO = 107.58
    FIST = (720, 500)
    def __init__(self):
        self.sp = spr('B_r4/fist3')
        self.bg = BK.dark_bg(6301, 0.01, 0.03)
        self.rain = fx2.RainSheet(6302, density=0.8)
        T.warm('握在自己', 'kai', 200)

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        fr = self.bg + np.exp(-(((x - 900) / 650) ** 2 + ((y - 420) / 420) ** 2))[..., None] * COLDC * 0.12
        th = V(self.T_WO)
        hk = hitp(t, self.T_WO, 0.12)
        q = clamp01((t - self.t0) / max(th - self.t0, 0.02))
        sq = 1.0 + 0.10 * (1 - eout(q, 3)) - 0.03 * hk                    # 攥紧：入镜略大 → 一记收紧
        fr, _ = put_at(fr, self.sp, t, (0.48, 0.36), (self.FIST[0], self.FIST[1] + 60 * (1 - eout(q, 3))), 1750 * sq,
                       rim=dict(col=(0.75, 0.82, 1.0), amt=2.0, dir=(0.5, -1.0)),
                       grade=dict(expo=0.82, sat=0.55, tint=(0.97, 0.98, 1.03), lift=0.0, gamma=1.08),
                       wind_amp=0, breathe=0.0, shade=(1300, 1900, 0.3, 700, 0.3))
        # 握紧挤出的水：从指缝向上、两侧迸开
        fr = K.sparks(fr, t, 6303, (self.FIST[0] - 20, self.FIST[1] - 330), n=110, life=0.6, speed=(300, 1100), dirc=(0, -1), spread=2.2, grav=1500, size=1.3,
                      area=(260, 30), color=(0.8, 0.85, 0.95), amt=1.0, t0=th, burst=True)
        pr = prs(25, [4, 5, 6, 7], t)
        fr = T.scatter_stack(fr, '握在自己', pr, places=[dict(ch='握', x=1360, y=360, size=270, rot=-3, font='kai', idx=0, emph=True),
                                                         dict(ch='在', x=1580, y=560, size=140, rot=0, font='kai', idx=1, emph=False),
                                                         dict(ch='自', x=1460, y=720, size=140, rot=0, font='kai', idx=2, emph=False),
                                                         dict(ch='己', x=1640, y=790, size=150, rot=0, font='kai', idx=3, emph=False)],
                             color='white', emph_color=(0.86, 0.10, 0.06), t_local=u, style_kw=dict(shadow=0.85, glow=0.12))
        fr = self.rain.draw(fr, t, intensity=0.8, angle=8)
        qq = t - th                                                     # 冷色水花冲击环（只亮环，不抬全屏）
        if 0 <= qq < 0.30:
            d = np.sqrt((x - self.FIST[0]) ** 2 + ((y - self.FIST[1]) * 1.25) ** 2)
            R = 260 + 1400 * eout(qq / 0.30, 2)
            ring = np.exp(-((d - R) / (14 + 70 * qq)) ** 2) * (1 - qq / 0.30)
            fr = fr + (ring * 0.6)[..., None] * COLDC
        dx, dy, dr = shake(t, 16 * hk, 14, 63)
        fr = cam(fr, 1.02 + 0.04 * hk, dx, dy, dr)
        return fr, (4 if hk > 0.5 else 0)


# =====================================================================================
# V19 108.34–109.55 MCU：握拳顺势握住刀柄、转身，马尾甩出雨珠（grab_turn）。匹配：拳 → 刀柄上的拳；「手掌」志莽行书右下
class V19(Shot):
    def __init__(self):
        self.sp = spr('B_r4/grab_turn2')          # 第七棒：束发、背后 3/4 侧（与 V17 正面拆开）
        sk = night_sky(6401, top=(0.02, 0.022, 0.03), bot=(0.09, 0.095, 0.11), horizon=0.85)
        self.bg = sk
        self.rain = fx2.RainSheet(6402, density=1.0)
        self.fog = fx2.Fog(6403)
        T.warm('手掌', 'kai', 230)

    def render(self, t):
        u = self.u(t)
        e = eout(clamp01(u * 3.0), 3)          # 第五棒 9/n：甩入转身 0.4s 内落定（原 0.75s 全程糊）
        fr = self.fog.draw(self.bg.copy(), t, density=0.45, y0=400, y1=960, color=(0.30, 0.32, 0.35), speed=(-200 * (1 - e), 0))
        whip = (1 - e)
        fr, _ = put_at(fr, self.sp, t, (0.42, 0.85), (980 - 260 * whip, 950), 1900,   # 第五棒 9/n：下移 70px，头顶不贴黑边
                       rim=dict(col=(0.75, 0.82, 1.0), amt=2.2, dir=(-0.7, -0.7)),
                       wind_amp=14, mblur=(-55 * whip, 0), shade=(600, 1700, 0.25, 600, 0.3))
        fr = K.sparks(fr, t, 6404, (640, 300), n=36, life=0.45, speed=(300, 900), dirc=(-1, -0.2), spread=1.1, grav=900, size=1.0,
                      area=(220, 160), color=(0.8, 0.85, 0.95), amt=0.7, t0=self.t0 + 0.05, burst=True)   # 甩水珠：散开、不成方块
        pr = prs(25, [8, 9], t)
        fr = T.scatter_stack(fr, '手掌', pr, places=[dict(ch='手', x=1500, y=640, size=220, rot=0, font='kai', idx=0, emph=False),
                                                       dict(ch='掌', x=1700, y=800, size=260, rot=0, font='kai', idx=1, emph=True)],
                             color='white', emph_color=(0.86, 0.10, 0.06), t_local=u, style_kw=dict(shadow=0.85, glow=0.15))
        fr = self.rain.draw(fr, t, intensity=1.0, angle=10, cam=(-300 * whip, 0))
        fr = cam(fr, 1.02, 0, 0, -2 * whip)
        return fr, 0


# =====================================================================================
# V20 109.55–110.92 LS 俯：积水倒影成为主画面：倒影里鬼屠背影（back_stand，镜像冷调），世界开始旋转 roll 0°→90°；「若这世」宋体随画面旋转
# V21 110.92–112.29 LS：继续旋转 90°→180° 并翻成负片（黑白颠倒）；「道黑白颠倒」随画面倒置，「黑」「白」因反相互换颜色
class V20(Shot):
    """第五棒重做（评审 P0：倒置人头被下沿裁、背景只有灰蓝椭圆暗角、角上黑椭圆块）：
    LS 贴水面平视——水线压在画面正中 y540：上半 = 雨夜远城墙 + 雾 + 站在浅水上低头看自己倒影的鬼屠（生图 look_down，全身入画，头顶留 50px）；
    下半 = 同一画面的水中倒影（涟漪、冷暗、雨点圈）。上下各自完整，倒影头部在 y≈900、不出 2.39 有效区。
    后半拍（u>0.45）世界开始 roll，V21 接着转到 180° —— 倒影翻到上方成「正面」，正是「黑白颠倒」。"""
    WL = 540
    def __init__(self):
        self.sp = spr('look_down')
        x, y = K.grid()
        sk = night_sky(6501, top=(0.05, 0.055, 0.07), bot=(0.30, 0.31, 0.34), horizon=0.50)
        wl, wm = city_wall_far(6502, 400, self.WL + 4, tone=0.075)
        wm = K.blur_ds(wm, 6)
        sk = sk * (1 - wm[..., None] * 0.55) + K.blur_ds(wl, 9) * wm[..., None] * 0.55
        sk += np.exp(-(((x - 1250) / 520) ** 2 + ((y - 470) / 160) ** 2))[..., None] * np.array([0.10, 0.11, 0.13], np.float32)   # 城楼后冷月雾光
        self.sky = sk
        self.fog = fx2.Fog(6503)
        self.rain = fx2.RainSheet(6504, density=0.6)
        self.r = np.random.default_rng(6505).uniform(0, 1, (34, 3))
        self.wn = K.tile(256, 6506, 6, 3)
        T.warm('若这世', 'serif_black', 140); T.warm('道黑白颠倒', 'serif_black', 140)

    def scene(self, t):
        x, y = K.grid()
        up = self.fog.draw(self.sky.copy(), t, density=0.8, y0=300, y1=self.WL, color=(0.30, 0.32, 0.36), speed=(25, 0), top_fade=200)
        up, _ = put(up, self.sp, t, 395, (760, self.WL + 4), rim=dict(col=(0.78, 0.86, 1.0), amt=3.0, dir=(0.5, -1.0)),
                    grade=dict(expo=0.80, sat=0.55, tint=(0.92, 0.97, 1.06), lift=0.0, gamma=1.12), wind_amp=7, shade=None, wrap=0.3)
        # 倒影：上半关于水线翻转 + 涟漪 + 冷暗
        refl = np.zeros_like(up)
        refl[self.WL:] = up[self.WL - 1::-1][:H - self.WL]
        nz = cv2.resize(K.tile_crop(self.wn, t * 20, t * 55, H // 8, W // 8), (W, H))
        refl = cv2.remap(refl, (x + (nz - 0.5) * 12).astype(np.float32), (y + (nz - 0.5) * 5).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        refl = refl * np.array([0.58, 0.64, 0.74], np.float32) * (0.9 + 0.2 * nz[..., None])
        low = sstep(self.WL - 1, self.WL + 2, y)[..., None]
        fr = up * (1 - low) + refl * low
        fr += np.exp(-((y - self.WL) / 2.5) ** 2)[..., None] * np.array([0.25, 0.28, 0.33], np.float32)      # 水线高光
        cs = [(a * W, self.WL + 30 + b * 400) for a, b, _ in self.r]; ts = [math.floor(t * 2 + c * 2) / 2 - c * 0.5 for _, _, c in self.r]
        fr = fx2.ripples(fr, t, cs, ts, amt=0.5, flat=0.25, speed=160, life=1.0)
        fr = self.rain.draw(fr, t, intensity=0.55, angle=2)
        return fr

    def render(self, t):
        u = self.u(t)
        fr = self.scene(t)
        pr = prs(26, [0, 1, 2], t)
        L = T.Layer()
        for i, (ch, pc) in enumerate(zip('若这世', pr)):
            if pc > 0: T.place(L, ch, 1480, 230 + i * 135, 120, color='white', fname='serif_black', alpha=min(1, pc * 2) * (1 - sstep(0.5, 0.75, u)), scale=1.2 - 0.2 * eout(pc))   # 第八棒：roll 前退场，不被甩出画
        fr = T.compose(fr, L, shadow=0.85, glow=0.12)
        ang = 90 * ein(clamp01((u - 0.45) / 0.55), 2)
        fr = roll_cover(fr, ang, 1.0 + 0.06 * eio(u))
        return fr, 0


def edge_rim(A, dx, dy, blur=2.0):
    """第八棒：轮廓光——A 的 (dx,dy) 方向外缘（自身在、偏移后不在的那一圈），朝光源一侧亮"""
    M = np.float32([[1, 0, -dx], [0, 1, -dy]])
    sh = cv2.warpAffine(A.astype(np.float32), M, (A.shape[1], A.shape[0]))
    e = np.clip(A - sh, 0, 1)
    return cv2.GaussianBlur(e, (0, 0), blur)


def roll_cover(fr, ang, extra=1.0):
    """第五棒：旋转时按角度补足缩放（cos|θ| + 16/9·sin|θ|），画面四角永远被内容填满——不再露出 BORDER_REFLECT 的镜像人/黑角"""
    a = math.radians(ang)
    z = abs(math.cos(a)) + (W / H) * abs(math.sin(a))
    return cam(fr, max(1.0, z) * extra, 0, 0, ang)


class V21(Shot):
    """第八棒：歌词不再随整个世界绕画面中心转（90° 时被放大 1.8× 甩到画外，f3328–3330「道」顶边出画）——
    字列改在屏幕空间、绕自己的列中心 (730,540) 同步转 90°→180°：90° 时横躺在画面中部，180° 时倒立竖排（颠倒），全程在安全区内。"""
    CX, CY = 730, 540
    def __init__(self):
        self.v20 = V20()

    def render(self, t):
        u = self.u(t)
        fr = self.v20.scene(t)
        # 90°→180°，同时反相（黑白颠倒）；「黑」「白」随反相互换
        e = eio(u)
        ang = 90 + 90 * eout(u, 2)
        fr = roll_cover(fr, ang, 1.04 + 0.04 * (1 - e))
        pr = prs(26, [3, 4, 5, 6, 7], t)
        L = T.Layer()
        for i, (ch, pc) in enumerate(zip('道黑白颠倒', pr)):
            if pc <= 0: continue
            col = (0.04, 0.04, 0.045) if ch == '黑' else ('white' if ch != '白' else (0.98, 0.97, 0.94))
            T.place(L, ch, self.CX + (20 if i % 2 else -20), self.CY + (i - 2) * 132, 140 if ch in '黑白' else 116, color=col, fname='serif_black',
                    alpha=min(1, pc * 2), scale=1.2 - 0.2 * eout(pc))
        x, y = K.grid()
        band = K.blur_ds(((np.abs(x - self.CX) < 115) & (np.abs(y - self.CY) < 380)).astype(np.float32), 40)
        M = cv2.getRotationMatrix2D((float(self.CX), float(self.CY)), ang, 1.0)
        band = cv2.warpAffine(band, M, (W, H))
        L.A = cv2.warpAffine(L.A, M, (W, H)); L.C = cv2.warpAffine(L.C, M, (W, H)); L.bb = [0, 0, W, H]
        fr = fr * (1 - 0.45 * band[..., None])
        fr = T.compose(fr, L, shadow=0.6, glow=0.15, outline=3, outline_color=(0.5, 0.5, 0.5))
        k = sstep(0.2, 0.55, u)
        fr = fr * (1 - k) + neg_grade(fr) * k                         # 负片：S 曲线高反差 + 重暗角（第四棒：去灰）
        return fr, 0


# =====================================================================================
# V22 112.29–113.60 MS：负片世界里鬼屠横斩（slash_h），113.34 刀线以上恢复正片、以下仍是负片；「那就用刀」沿刀线一分为二，「刀」朱
class V22(Shot):
    T_CUT = 113.34
    def __init__(self):
        self.sp = spr('slash_h')
        sk = night_sky(6601, top=(0.02, 0.022, 0.03), bot=(0.12, 0.125, 0.14), horizon=0.8)
        wl, wm = city_wall_far(6602, 640, 840, tone=0.05, crenel=False)      # 第五棒：去城楼平涂块（负片里成白色叠矩形）
        wm = K.blur_ds(wm, 8)
        self.bg = sk * (1 - wm[..., None] * 0.7) + K.blur_ds(wl, 8) * wm[..., None] * 0.7
        self.bg = fx2.Fog(6604).draw(self.bg, 0.0, density=0.6, y0=500, y1=900, color=(0.16, 0.17, 0.19), speed=(0, 0))
        self.rain = fx2.RainSheet(6603, density=1.0)
        T.warm('那就用刀', 'kai', 150)

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        fr = self.bg.copy()
        fr, am = put(fr, self.sp, t, 720, (960, 900), rim=dict(col=(0.75, 0.82, 1.0), amt=2.2, dir=(0.6, -0.8)), wind_amp=10,
                    shade=(600, 1600, 0.2, 600, 0.3))
        am = K.blur_ds(np.clip(am, 0, 1).astype(np.float32), 3) if am is not None else np.zeros((H, W), np.float32)
        tc = V(self.T_CUT)
        line_y = 470 + 0.06 * (x - 960)                 # 刀线（沿刀身，略斜）
        q = clamp01((t - tc) / 0.35)
        # 负片：斩前全屏；斩后只剩刀线以下（先做负片，字后合成，朱红「刀」不被反相）
        m = np.ones((H, W), np.float32) if t < tc else sstep(-6, 6, y - line_y)
        m = m * (1 - 0.97 * am)                       # 第四棒：颠倒的是世界，他本人不反相（正片人站在负片世界里）
        fr = fr * (1 - m[..., None]) + neg_grade(fr) * m[..., None]
        fr = self.rain.draw(fr, t, intensity=0.8, angle=10)          # 雨在反相之后画：不变成黑粗条
        P = [dict(ch=c, x=(1215, 1365, 1515, 1680)[i], y=700, size=(135, 135, 135, 180)[i], rot=0, font='kai', idx=i, emph=(c == '刀'))
             for i, c in enumerate('那就用刀')]                     # 第四棒：移到右侧亮墙，不压人物
        pr = prs(27, [0, 1, 2, 3], t)
        if q <= 0:
            L = T.Layer()
            for pp, pc in zip(P, pr):
                if pc > 0: T.place(L, pp['ch'], pp['x'], pp['y'], pp['size'], color='red' if pp['emph'] else 'ink', fname='kai', alpha=min(1, pc * 2))
            fr = T.compose(fr, L, shadow=0.0, glow=0.0)
        else:
            L = T.Layer()                                           # 第五棒：「那就用」保持完整可读，只有「刀」被刀线斩开
            for pp in P[:3]: T.place(L, pp['ch'], pp['x'], pp['y'], pp['size'], color='ink', fname='kai')
            fr = T.compose(fr, L, shadow=0.0, glow=0.0)
            fr = T.slash_cut(fr, '刀', clamp01(0.25 + q * 0.75), places=[dict(P[3], idx=0)], fname='kai', color=(0.03, 0.03, 0.035), emph=('刀',),
                             emph_color=(0.86, 0.10, 0.06), angle=4, cut_at=0.25, slide=0.18, appear=0.0)
        if t >= tc - 0.05:
            ql = clamp01((t - (tc - 0.05)) / 0.15)
            band = np.exp(-((y - line_y) / (3 + 20 * (1 - ql))) ** 2) * (x < W * ql + 200)
            fr += band[..., None] * np.array([1.0, 0.92, 0.85], np.float32) * (1.5 - ql)
        hk = hitp(t, self.T_CUT, 0.12)
        dx, dy, dr = shake(t, 20 * hk, 14, 66)
        fr = cam(fr, 1.0 + 0.06 * eio(u) + 0.03 * hk, dx, dy, dr)
        return fr, (4 if hk > 0.5 else 0)


# =====================================================================================
# V23 113.60–115.03 CU 低：刀尖在泥水里划出发光朱红刀痕（drag_blade），火星与蒸汽，积水被劈开；「锋重新划」沿刀痕排开逐字烫亮
def gash(fr, t, pts, width, heat=1.0, seed=0):
    """地面发光刀痕：pts 屏幕折线（近→远），width 近端宽度；返回 (fr, mask)"""
    m = np.zeros((H // 2, W // 2), np.float32)
    n = len(pts)
    for i in range(n - 1):
        w = max(1, int((width * (1 - i / n) ** 1.6 + 3) / 2))
        cv2.line(m, (int(pts[i][0] / 2), int(pts[i][1] / 2)), (int(pts[i + 1][0] / 2), int(pts[i + 1][1] / 2)), 1.0, w, cv2.LINE_AA)
    m = cv2.resize(m, (W, H))
    nz = cv2.resize(K.fbm(H // 4, W // 4, seed, 10, 4), (W, H))
    core = np.clip(m * (0.7 + 0.6 * nz), 0, 1)
    glow = K.blur_ds(core, 22)
    fr = fr * (1 - core[..., None] * 0.9) + core[..., None] * (RED * 1.6 + GOLD * 0.8 * core[..., None]) * heat
    fr += glow[..., None] * RED * 1.1 * heat + K.blur_ds(core, 80)[..., None] * RED * 0.35 * heat
    return fr, core


def trench(fr, t, hor, camH, z0, z1, width=0.8, f=1000.0, cx=960.0, seed=0, heat=1.0, xc=None, fog_z=200.0):
    """第三棒：地面透视刀痕（按针孔相机逐像素反投影到地面：Z = f·camH/(y-hor)，X = (x-cx)·Z/f）。
    近宽远窄、自动收向消失点；熔芯（金白→朱红）+ 翻起的焦黑唇边 + 唇边受光 + 地面红辉 + 远处雾化 + 热浪闪烁 + 侧向细裂纹。
    xc(Z) 中线横向偏移（米）；返回 (fr, core)"""
    x, y = K.grid()
    dy = np.maximum(y - hor, 0.5)
    Z = f * camH / dy
    X = (x - cx) * Z / f
    ground = (y > hor + 1).astype(np.float32)
    nzz = np.log(Z + 1.0)
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.28, 4)
    wob = 0.10 * np.sin(Z * 0.35 + ph[0]) + 0.05 * np.sin(Z * 1.3 + ph[1]) + 0.025 * np.sin(Z * 4.1 + ph[2])
    cen = wob + (xc(Z) if xc else 0.0)
    d = np.abs(X - cen)
    lod = np.clip(f / Z / 60.0, 0, 1)                          # 远处高频细节淡出，防止横向锯齿条纹
    jag = 1.0 + 0.22 * np.sin(Z * 9.0 + ph[3]) * np.sin(Z * 2.3) * lod + 0.06 * np.sin(Z * 23.0) * lod ** 2 + 0.15 * np.sin(Z * 0.9 + ph[1])
    hw = width * 0.5 * jag
    inz = ((Z >= z0) & (Z <= z1)).astype(np.float32) * ground
    endf = np.clip((z1 - Z) / 3.0, 0, 1) * np.clip((Z - z0) / 0.4, 0, 1)
    px = f / Z                                                   # 1 米在该深度的像素数
    aa = 1.0 / np.maximum(px, 1e-3)                              # 1 像素对应米数（抗锯齿）
    core = np.clip((hw * 0.45 - d) / (aa * 1.5) + 0.5, 0, 1) * inz * endf
    pit = np.clip((hw - d) / (aa * 1.5) + 0.5, 0, 1) * inz * endf
    lip = np.clip(1 - np.abs(d - hw * 1.15) / (hw * 0.35 + aa), 0, 1) * inz * endf
    flick = 0.85 + 0.15 * np.sin(Z * 3.0 - t * 18.0) * np.sin(Z * 0.7 + t * 5.0)
    zf = np.clip(1 - Z / fog_z, 0.15, 1)                         # 远处雾化
    hotc = np.clip(1 - d / (hw * 0.45 + aa), 0, 1)
    molten = (RED * 1.4 + GOLD * 1.1 * hotc[..., None] + np.array([1.0, 0.95, 0.85], np.float32) * 0.6 * hotc[..., None] ** 3)
    fr = fr * (1 - pit[..., None] * 0.85) + pit[..., None] * np.array([0.02, 0.008, 0.006], np.float32)          # 焦黑沟
    fr = fr * (1 - lip[..., None] * 0.5) + lip[..., None] * RED * 0.55 * zf[..., None] * heat                     # 唇边被照亮
    fr = fr * (1 - core[..., None]) + core[..., None] * molten * (flick * heat)[..., None]
    # 地面红辉（按米衰减 → 透视正确）
    glow = np.exp(-np.maximum(d - hw, 0) / (0.9 + 0.02 * Z)) * inz * endf * ground * zf
    fr = fr + glow[..., None] * RED * 0.30 * heat + K.blur_ds(core, 20)[..., None] * RED * 0.8 * heat
    # 侧向细裂纹（地面坐标里画几条短裂口）
    cr = np.zeros_like(d)
    for k in range(6):
        zk = z0 + (z1 - z0) * ((k * 0.137 + 0.05) % 1.0) ** 2.2
        s = 1 if k % 2 else -1
        band = np.exp(-((Z - zk - s * 0.4 * (X - cen)) / (0.03 * Z ** 0.6 + aa)) ** 2)
        cr = np.maximum(cr, band * ((X - cen) * s > hw) * ((X - cen) * s < hw + 0.3 + 0.01 * zk) * inz)
    fr = fr + cr[..., None] * RED * 0.9 * zf[..., None] * heat
    return fr, core


class V23(Shot):
    def __init__(self):
        self.sp = spr('drag_blade')
        x, y = K.grid()
        mud = (0.015 + 0.035 * cv2.resize(K.fbm(H // 2, W // 2, 6701, 12, 6), (W, H)))[..., None] * np.array([1.0, 0.97, 0.95], np.float32)
        self.bg = mud
        self.fog = fx2.Fog(6702)
        self.rain = fx2.RainSheet(6703, density=0.7)
        T.warm('锋重新划', 'kai', 150)

    def render(self, t):
        u = self.u(t)
        e = eio(u)
        fr = self.bg.copy()
        tipx = 520 - 260 * e                               # 刀尖向左拖行
        pts = [(tipx + i * 70, 900 - i * 2) for i in range(int(4 + 22 * clamp01(u * 1.3 + 0.3)))]
        fr, core = gash(fr, t, pts, 34, heat=1.0, seed=6704)
        fr, _ = put_at(fr, self.sp, t, (0.05, 0.955), (tipx, 900), 3600, rim=dict(col=(1.0, 0.45, 0.30), amt=2.0, dir=(0.0, 1.0)),
                       wind_amp=8, shade=(800, 1900, 0.2, 0, -0.2), wrap=0.3)
        fr += np.exp(-(((x := K.grid()[0]) - tipx - 400) / 900) ** 2)[..., None] * RED * 0.08
        fr = K.sparks(fr, t, 6705, (int(tipx), 895), n=110, life=0.5, speed=(300, 1000), dirc=(0.6, -1), spread=0.8, grav=1300, size=1.2,
                      area=(20, 10), amt=1.2)
        fr = self.fog.draw(fr, t, density=0.35, y0=600, y1=960, color=(0.55, 0.42, 0.38), speed=(60, -40))
        fr = self.rain.draw(fr, t, intensity=0.7, angle=8)
        pr = prs(27, [4, 5, 6, 7], t)
        L = T.Layer()
        for i, (ch, pc) in enumerate(zip('锋重新划', pr)):
            if pc <= 0: continue
            xx = 700 + i * 205 - 200 * e                                 # 第五棒：字距 290→205（评审 P2：字距过大）、烫金→亮朱 + 暗衬
            T.place(L, ch, xx, 680 - i * 8, 210 - i * 6, color=(1.0, 0.92, 0.70) if pc < 1 else (1.0, 0.30, 0.12), fname='kai',
                    alpha=min(1, pc * 2), rot=-2)
        if L.box(4) is not None:
            fr = fr * (1 - 0.55 * K.blur_ds(L.A, 26)[..., None])
        fr = T.compose(fr, L, shadow=0.9, outline=2, outline_color=(0.12, 0.02, 0.01), glow=0.7, glow_color=(1.0, 0.3, 0.08))
        hk = hitp(t, 113.64, 0.12)
        dx, dy, dr = shake(t, 4 + 12 * hk, 10, 67)
        fr = cam(fr, 1.04, dx - 60 * e, dy, dr)
        return fr, (3 if hk > 0.5 else 0)


# =====================================================================================
# V24 115.03–116.42 ELS 高：摇臂升高，一道发光朱红刀痕从他脚下延伸向远方雨雾中的城墙；drag_blade 远景逆光剪影（第 2 次）；「出方」沿刀痕透视铺设
class V24(Shot):
    def __init__(self):
        self.sp = spr('drag_blade')
        sk = night_sky(6801, top=(0.03, 0.032, 0.04), bot=(0.20, 0.19, 0.20), horizon=0.6)
        wl, wm = city_wall_far(6802, 300, 420, tone=0.09)
        wl = K.blur_ds(wl, 3); wm = K.blur_ds(wm, 3) * 0.0             # 第七棒：去城墙（城墙背景 5→4 次），地平线只留雨雾
        x, y = K.grid()
        self.gm = sstep(410, 440, y)
        mud = (0.02 + 0.03 * cv2.resize(K.fbm(H // 2, W // 2, 6803, 14, 6), (W, H)))[..., None] * np.ones(3, np.float32)
        self.bg = (sk * (1 - wm[..., None]) + wl * wm[..., None]) * (1 - self.gm[..., None]) + mud * self.gm[..., None]
        self.fog = fx2.Fog(6804)
        self.rain = fx2.RainSheet(6805, density=0.8)
        self.spl = fx2.Splashes(6807)
        T.warm('出方', 'kai', 200)

    def render(self, t):
        u = self.u(t)
        e = eio(u)
        fr = self.bg.copy()
        grow = clamp01(u * 1.25 + 0.15)
        HOR, CH, FF = 432.0, 5.0, 1100.0                              # 高机位（摇臂）
        X0, AX = -2.5, 0.03                                           # 刀痕从左前方斜着划向远墙（不正对镜头 → 读得出是地面）
        zend = 12.5 + (380 - 12.5) * grow ** 2.2                       # 刀痕从脚下向远墙疾速延伸
        fr, core = trench(fr, t, HOR, CH, 12.5, zend, width=1.0, f=FF, seed=6806, fog_z=420.0,
                          xc=lambda Z: X0 + AX * Z + 0.4 * np.sin(Z / 40.0))
        fr = self.fog.draw(fr, t, density=0.5, y0=300, y1=640, color=(0.32, 0.33, 0.36), speed=(30, 0), light=(960, 460), light_r=500,
                           light_color=RED * 0.6)
        # 鬼屠站在刀痕起点（Z=10 m）：逆光剪影，透视尺寸与地面一致
        fy = HOR + FF * CH / 12.0
        # 第七棒：人物放大到画面 ~1/2 高、不再纯黑平贴——冷月轮廓光（上）+ 刀痕红光从脚下反打（下），边缘被雨溅打
        fx0 = 960 + FF * (X0 + AX * 12 - 0.9) / 12.0
        # 人在刀痕左侧，字在右侧不压人；第八棒：原 rim 参数误被写进注释（轮廓光从未生效）→ 恢复
        fr, Am = put(fr, self.sp, t, 500, (fx0 - 300, fy + 40), rim=dict(col=(0.78, 0.86, 1.0), amt=3.4, dir=(0.4, -1.0)),
                     grade=dict(expo=0.42, sat=0.5, tint=(1.05, 0.92, 0.88), lift=0.0, gamma=1.15), wind_amp=8, shade=None, wrap=0.35)
        x_, y_ = K.grid()
        # 第八棒：原红光是整块下半身均匀染红（读成红裤子）→ 方向性：刀痕在人右侧，红光只沿右/下缘反打；冷月轮廓沿左上缘
        fr = fr + (Am * np.clip((y_ - (fy - 300)) / 340, 0, 1))[..., None] * RED * 0.06
        fr = fr + (edge_rim(Am, 10, 4, 3.5) * np.clip((y_ - (fy - 420)) / 300, 0.15, 1))[..., None] * RED * 0.7
        fr = fr + (edge_rim(Am, -6, -8) * np.clip(((fy - 80) - y_) / 300, 0, 1))[..., None] * np.array([0.55, 0.62, 0.75], np.float32)
        fr = self.spl.draw(fr, t, y_far=fy - 30, y_near=fy + 60, rate=60, amt=0.6) if hasattr(self, 'spl') else fr
        # 「出方」立在刀痕两侧（远近两处，近大远小），随刀痕到达时燃起
        pr = prs(27, [8, 9], t)
        for i, (ch, pc, Zc, Xs) in enumerate(zip('出方', pr, (18.0, 40.0), (3.5, 9.0))):
            if pc <= 0: continue
            sx_ = 960 + FF * (X0 + AX * Zc + Xs) / Zc; sy_ = HOR + FF * CH / Zc
            sz = (210, 170)[i]
            L = T.Layer(); T.place(L, ch, sx_, sy_ - sz * 0.45, sz, color=(0.98, 0.22, 0.08), fname='kai', alpha=min(1, pc * 2), sy=0.85)   # 第七棒：行书「出」读成「生」→ 马善政楷
            fr = T.compose(fr, L, shadow=0.6, glow=0.7, glow_color=(1.0, 0.3, 0.08))
        fr = self.rain.draw(fr, t, intensity=0.9, angle=10)
        fr = cam(fr, 1.10 - 0.10 * e, 0, 60 - 60 * e)          # 摇臂升：画面下压 + 拉开
        return fr, 0


# =====================================================================================
# V25 116.42–117.80 LS 低：贴地沿刀痕望去，刀痕直指远墙；鬼屠背影立在刀痕起点（back_stand 逆光剪影，第 2 次）；「向」在刀痕尽头燃起；末拍推进压暗
class V25(Shot):
    T_XIANG = 116.46
    def __init__(self):
        self.sp = spr('back_stand')
        sk = night_sky(6901, top=(0.02, 0.022, 0.03), bot=(0.16, 0.15, 0.15), horizon=0.62)
        x, y = K.grid()
        # 第八棒（P1-8：V20/V24/V25 三镜同为城墙地平线）：V25 去城墙 → 雨雾中的远山脊线（两层，远淡近深），刀痕直指山口
        xs = np.arange(W, dtype=np.float32)
        def ridge(seed, base, amp, oct_):
            r = np.zeros(W, np.float32); rng = np.random.default_rng(seed)
            for k in range(oct_):
                fq = 2 ** k / 900.0; ph = rng.uniform(0, 6.28)
                r += (amp / 2 ** k) * np.abs(np.sin(xs * fq * 3.1 + ph))
            r += 60 * np.exp(-((xs - 960) / 260) ** 2)          # 山口：中间低（刀痕指向）
            return base - r + r.mean()
        wm = np.zeros((H, W), np.float32); wl = np.zeros((H, W, 3), np.float32)
        for seed, base, amp, tone in ((6902, 520, 70, 0.10), (6909, 575, 45, 0.05)):
            rr = ridge(seed, base, amp, 5)
            m = (y > rr[None, :]).astype(np.float32)
            wl = wl * (1 - m[..., None]) + tone * np.ones(3, np.float32) * m[..., None]
            wm = np.maximum(wm, m)
        self.gm = sstep(590, 620, y)
        mud = (0.015 + 0.03 * cv2.resize(K.fbm(H // 2, W // 2, 6903, 12, 6), (W, H)))[..., None] * np.ones(3, np.float32)
        # 第五棒 9/n：城楼平涂块（程序味）→ 远景大气透视：墙体/城楼重虚化 + 檐口上方雾幕吞掉硬边 + 刀痕红光反打墙根
        wmb = cv2.GaussianBlur(wm, (0, 0), 6)
        wall = K.blur_ds(wl, 8) + (0.02 * cv2.resize(K.fbm(H // 4, W // 4, 6907, 6, 5), (W, H)))[..., None] * wmb[..., None]
        bg = sk * (1 - wmb[..., None]) + wall * wmb[..., None]
        haze = np.exp(-((y - 360) / 150) ** 2)[..., None] * np.array([0.11, 0.11, 0.125], np.float32) * (0.6 + 0.4 * cv2.resize(K.fbm(H // 4, W // 4, 6908, 8, 4), (W, H)))[..., None]
        bg = bg + haze
        bg += (wmb * np.exp(-((x - 960) / 460) ** 2) * np.clip((y - 470) / 130, 0, 1))[..., None] * RED * 0.10
        self.bg = bg * (1 - self.gm[..., None]) + mud * self.gm[..., None]
        self.fog = fx2.Fog(6904)
        self.rain = fx2.RainSheet(6905, density=0.8)
        T.warm('方向', 'xing', 260)

    def render(self, t):
        u = self.u(t)
        x, y = K.grid()
        fr = self.bg.copy()
        fr, core = trench(fr, t, 605.0, 0.6, 1.0, 600.0, width=0.75, f=1000.0, seed=6906, fog_z=700.0)
        fr = self.fog.draw(fr, t, density=0.5, y0=420, y1=760, color=(0.30, 0.30, 0.33), light=(960, 600), light_r=500, light_color=RED * 0.8)
        fr, Am = put(fr, self.sp, t, 520, (760, 800), rim=dict(col=(0.78, 0.86, 1.0), amt=3.6, dir=(0.3, -1.0)), wind_amp=9,
                     grade=dict(expo=0.38, sat=0.5, tint=(1.05, 0.92, 0.88), lift=0.0, gamma=1.15), shade=None, wrap=0.4)   # 第七棒：冷轮廓光 + 刀痕红光反打
        fr = fr + (Am * np.clip((y - 520) / 300, 0, 1))[..., None] * RED * 0.10
        fr = fr + (edge_rim(Am, 0, 9, 3.5) + 0.3 * edge_rim(Am, 7, 3, 3.5) + 0.3 * edge_rim(Am, -7, 3, 3.5))[..., None] * RED * 0.6   # 第八棒：红光从脚下刀痕反打 → 只上下缘
        fr = fr + (edge_rim(Am, 0, -8) * np.clip((700 - y) / 300, 0, 1))[..., None] * np.array([0.5, 0.57, 0.7], np.float32)
        pr = prs(27, [10], t, 0.3)[0]
        if pr > 0:
            fr = T.burn_in(fr, '向', pr, places=[dict(ch='向', x=1460, y=450, size=300, rot=0, font='xing', idx=0, emph=False)],
                           color='red', embers=140, seed=69, style_kw=dict(shadow=0.4, glow=0.7, glow_color=(1.0, 0.3, 0.08)))
        Lf = T.Layer(); T.place(Lf, '方', 1170, 470, 250, color=(0.9, 0.16, 0.06), fname='xing', alpha=0.9, rot=-3)   # 第四棒：段尾主词放大、与「向」横排同读
        fr = T.compose(fr, Lf, shadow=0.5, glow=0.5, glow_color=(1.0, 0.3, 0.08))
        fr = self.rain.draw(fr, t, intensity=0.9, angle=8)
        end = clamp01((t - 117.33) / 0.45)
        fr = fr * (1 - 0.7 * eio(end))
        fr = cam(fr, 1.0 + 0.06 * eio(u) + 0.10 * ein(end, 2), 0, 0, center=(960, 600))
        return fr, 0


# ===================================================================================== 段落装配
SHOTS = [V01, V02, V03, V04, V05, V06, V07, V08, V09, V10, V11, V12, V13, V14, V15, V16, V17, V18, V19, V20, V21, V22, V23, V24, V25]
CUTS = {
    'V02': ('ring_wipe', 0.06, 0.16, dict(center=(1300, 600))),    # 第六棒：钟声折射环开门（钟口圆 → 广场声波环）
    'V03': ('zoom_dark', 0.08, 0.14, dict(center=(960, 560))),     # 第六棒：顶拍压进跪拜的人群 → 平视纸人队列
    'V04': ('punch', 0, 0, {}),                                     # 第七棒：金闪 → 落拍推近色散（刻刀第一记）
    'V05': ('occlusion', 0.08, 0.16, dict(kind='pillar', direction=1, seed=5)),
    'V06': ('match_cut', 0.0, 0.12, dict(shape='circle', center=(930, 400), radius=220, glow=np.zeros(3, np.float32))),   # 第五棒：去金圈（≈副歌一 S045 光圈）
    'V07': ('punch', 0, 0, {}),                                     # 第七棒：金闪 → 推近色散（窗棂光一跳）
    'V08': ('rain_curtain', 0.06, 0.14, dict(seed=8)),            # 第九棒：split_slide 中间帧全黑 → 雨帘落幕（由暗殿进雨夜外景）
    'V09': ('match_cut', 0.0, 0.12, dict(shape='rect', center=(960, 520), radius=160)),
    'V10': ('punch', 0, 0, {}),                                     # 第七棒：hard → 推近色散冲击
    'V11': ('slash_wipe', 0.05, 0.12, dict(angle=-70)),
    'V12': ('shatter', 0.04, 0.14, dict(seed=12, center=(960, 520), n=60)),
    'V13': ('punch', 0, 0, {}),                                     # 第六棒：none → 落拍 punch + 泥水冠状冲击（人物首帧在画内）
    'V14': ('punch', 0, 0, {}),                                     # 第七棒：红闪 → 落拍冲击（起身气浪）
    'V15': ('ink_bleed', 0.06, 0.20, dict(seed=15)),
    'V16': ('rain_curtain', 0.08, 0.18, dict(seed=16)),             # 第四棒：灰雾 smoke → 雨帘落幕（b_kit）
    'V17': ('slash_wipe', 0.04, 0.12, dict(angle=7)),               # 第七棒：碑上那一刀顺势划开下一镜（刀线同向）
    'V18': ('punch', 0, 0, {}),
    'V19': ('punch', 0, 0, {}),                                     # 第七棒：hard → 推近色散冲击                                      # 第五棒 9/n：match_cut 中点双影糊 → 落拍硬切冲击（推近+提亮 2 帧），拳 → 张开的手掌
    'V20': ('split_slide', 0.06, 0.14, dict(angle=0.0, center=(960, 560))),   # 第四棒：whip 糊黑 → 水平分屏（水面线），上岸下影反向滑
    'V21': ('none', 0, 0, {}),
    'V22': ('punch', 0, 0, {}),                                     # 第四棒：灰 glitch → 落拍硬切冲击（推近+色散）
    'V23': ('slash_wipe', 0.05, 0.14, dict(angle=4)),
    'V24': ('zoom_dark', 0.08, 0.14, dict(center=(960, 640))),     # 第四棒：去中点白场
    'V25': ('zoom_dark', 0.06, 0.12, dict(center=(960, 620))),     # 第七棒：hard → 沿刀痕推进穿越
}
FG = {'V03': ('rain', 0.3), 'V07': ('ember', 0.3), 'V08': ('rain', 0.3), 'V09': ('rain', 0.3), 'V13': ('rain', 0.35),
      'V14': ('ember', 0.5), 'V15': ('rain', 0.45)}
EXPO = {}


def _bind():
    for _S, _a, _b in zip(SHOTS, CUT_F, CUT_F[1:]):
        _S.t0, _S.t1 = _a / FPS, _b / FPS
    SHOTS[0].t0 = T_IN
_bind()

# 第八棒：节奏表（B_rhythm_v1）里起/中/止近乎同框、静止 >1 拍的镜头补镜内运镜 (z0, z1, dx, dy, rot)
MOVE = {'V01': (1.02, 1.08, 30, 0, 0), 'V02': (1.03, 1.12, 0, 50, 0), 'V05': (1.04, 1.10, 60, 0, 0), 'V11': (1.04, 1.10, -60, 0, 0),
        'V13': (1.0, 1.08, 0, -40, 0), 'V15': (1.0, 1.06, 0, 0, 0), 'V18': (1.03, 1.10, 0, 0, 2.0)}
_SEC = [None]


def section():
    if _SEC[0] is None: _SEC[0] = Section(SHOTS, CUTS, FG, EXPO, expo_all=1.12); _SEC[0].move = MOVE
    return _SEC[0]


_C1 = [None]
SEAM_N = 1                                    # 2586–2595：副歌一 S047 原帧 →（雨幕溶解）→ V01；墨退遮罩两边同一个


def frame(f, cache=None):
    if f < F0 + SEAM_N:
        if _C1[0] is None:
            os.environ.setdefault('SPRITE_MODE', '1')
            import chorus1 as C; _C1[0] = (C, C.Chorus1())
        C, X = _C1[0]
        A = X.frame(f / FPS)[0]
        B = section().frame_f(f / FPS)
        p = (f - F0 + 1) / (SEAM_N + 1)
        nz = _seam_noise()
        m = np.clip((eio(p) * 1.5 - nz) * 4, 0, 1)[..., None]
        return K.to8(A * (1 - m) + B * m)
    return section().frame(f)


_SN = []


def _seam_noise():
    if not _SN:
        x, y = K.grid()
        n = cv2.resize(K.fbm(H // 8, W // 8, 4799, 5, 5), (W, H))
        streak = cv2.resize(np.random.default_rng(4798).random((1, W // 6)).astype(np.float32), (W, H))   # 竖向雨痕
        _SN.append((0.55 * n + 0.45 * streak + 0.15 * (y / H)).astype(np.float32))
    return _SN[0]
