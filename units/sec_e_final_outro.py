"""units/sec_e_final_outro.py — E 组：副歌终「定」+ 尾奏（帧 5797–7241，193.24–241.34s）
设计说明：crew/round4/E_storyboard.md。36 镜：副歌终 26 镜（平均 1.08s）+ 尾奏 10 镜（含片名再现、6 条署名、收刀落印、收墨）。
接口：READY=False；frame(f, cache) -> uint8 (1080,1920,3) 成品帧（含黑边/颗粒/暗角）。
结构仿 units/chorus1.py：每镜一个类（render(t) 场景 + text(fr,t) 屏幕字层），SHOTS 表驱动切点，CUTS 表驱动转场，MOVE 表驱动运镜。"""
# [r4-props] 终章 1 处：E07 末尾加 PD.play L51（烧穿挂轴）；L54 需 E19 交出精灵 alpha+bg，暂 skip。
import math, os, sys, json
ROOT = '/workspace/work/mv'
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, cv2
import props_dev as PD
import c1kit as K
import typo as T
import trans as TR
import fx2
import props as PR
import paper as PA
import rest_sprites as RS
import e_kit as E
import e_r3 as R3
import e_r5 as R5
import e_r6 as R6
import e_r7 as R7
import e_r8 as R8
import grade_unify as GU                     # 全片统一 grade 层（GRADE_UNIFY=1 生效）
from e_r3 import LyrO
Sub = R5.SubD          # 第五棒：副句随画面漂移、去句首朱印、暗衬变淡（去卡拉 OK 条模板感）
from e_kit import (W, H, BAR, GOLD, GOLDW, RED, REDT, WHITE_T, GOLD_T, INK, put, Lyr, row, sstep, c01, eio, eout, ein,
                   G_DAWN, G_HOT, G_SIL)

READY = True
FPS = 30
F0, F1 = 5797, 7241
LINES = T.load_lines()


def CT(li, k):
    """第 li 句第 k 个可见字的视觉帧时刻（字头最近帧再提前 1 帧）。"""
    ts = [x for x in LINES[li]['times'] if x is not None]
    return (round(ts[min(k, len(ts) - 1)] * FPS) - 1) / FPS


def cts(li, ks): return [CT(li, k) for k in ks]


HM = json.load(open(ROOT + '/crew/round4/E_hitmap.json'))
KICKS = [(h['t'], h['strength']) for h in HM['hits'] if 'kick' in h['type'] and h['strength'] > 0.5]


# [r4-DE#51] 用户：3m55 起 BGM 多记重音 → 跟鼓点做卡点节奏。
# 窗口 234.4–239.6s 就是 E34(尾)+E35 这一整块；击打表来自 crew/round4/E_hitmap.json（HPSS percussive band flux）。
OUTRO_HITS = [(h['t'], h['strength']) for h in HM['hits']
              if 234.4 <= h['t'] <= 239.6 and h['strength'] >= 0.30]
def outro_punch(t):
    """尾段密集重音专用：脉冲更短（0.06s 衰减）更硬，用来做「跟鼓点」的顿挫（不闪、不提亮）。"""
    p = 0.0
    for th, s in OUTRO_HITS:
        if th - 1 / 30 <= t < th + 0.22:
            p = max(p, s * math.exp(-max(0.0, t - th + 1 / 30) / 0.06))
    return p


def kick_punch(t):
    p = 0.0
    for th, s in KICKS:
        if th - 1 / 30 <= t < th + 0.45: p = max(p, s * math.exp(-max(0.0, t - th + 1 / 30) / 0.11))
    return p


class Shot:
    def __init__(self): pass
    def u(self, t): return (t - self.t0) / (self.t1 - self.t0)
    def render(self, t): return np.zeros((H, W, 3), np.float32)
    def text(self, fr, t): return fr


def bloom(fr, thr=0.8, amt=0.5, sig=30): return K.bloom(fr, thr, amt, sig)

# =====================================================================================
# [r4-DE#46] 用户 51 条之 #46：**180–241s 除 5 处保留外全部去文字（画内字）**。
#   保留：E04/E05「天理昭彰」匾、E12「鬼屠」朱印、E15「天理」木牌、E16→✓ / E17→✗（另 D 段 S21「规矩」/S26「判」不动）
#   删除：下面这些镜的**屏幕大字**（LyrO/Lyr 那一层，>160px 的才留得下来）；
#         镜内道具纹理（律令卷轴刻字、木牌、碑林）不在删除范围 —— 那是道具，不是标题字。
#   分类表见 crew/round4/DE_notes_r1.md；回滚 = 把镜号从集合里删掉。
NO_TXT = {'E07', 'E09', 'E10', 'E11', 'E25', 'E26'}
#   E02 的「刀不放」朱印、E08 的「伪装」烧字、E20 的「天」巨字 是在 render() 里画的，用 glyph_off() 守卫
NO_GLYPH = {'E02', 'E08', 'E20'}


def glyph_off(sid): return sid in NO_GLYPH


# [r4-DE#45/47/48] r1 生图当整帧底版。这三张都带「烙进像素」的大字，处理见 tools/clean_gen_text.py：
#   s_d17_eye_crop   = 原图裁到 x0.02–0.665（「我的」「刀」出画）
#   s_e218_hilt_crop = 裁到 x0.02–0.635（「刀」出画）+ 左下小字「就」矩形 inpaint
#   e22_scale_crop   = 原图干净（无字），直接缩放
# 无字新版（文件名带 2）到了以后，只要把文件名和后缀改掉即可替换，挂载参数不用动。
_PLATES = {}


def plate(name):
    if name in _PLATES: return _PLATES[name]
    from PIL import Image as _I
    p = ROOT + '/assets/gen/r1/' + name + '.png'
    if not os.path.exists(p):
        _PLATES[name] = None; return None
    _PLATES[name] = np.asarray(_I.open(p).convert('RGB').resize((W, H), _I.LANCZOS)).astype(np.float32) / 255
    return _PLATES[name]


def _lp(a, b, t): return a + (b - a) * t


def _mark(fr, t, t_on, cx, cy, S, col, kind='tick', rot=-6.0):
    """[r4-DE#46] 用户：「对错」改成 ✓ / ✗ 两个符号，**用代码画**（粗笔画、朱红/金、和原字同位置同大小），不许用字体里的对勾字形。
    手写感做法：分段变宽（起笔 0.72→中段 0.95→收笔 0.42 倍线宽）+ 两笔顺序落笔（0.42s）+ 轻微倾斜 + 暗衬 + 柔光。"""
    p = c01((t - t_on) / 0.42)
    if p <= 0: return fr
    A = np.zeros((H, W), np.float32)
    th = max(6.0, S * 0.155)

    def seg(a, b, q, w0, w1, n=14):
        for i in range(n):
            u0, u1 = i / n, (i + 1) / n
            if u0 >= q: break
            u1 = min(u1, q)
            ww = _lp(w1, w0, 1 - (u0 + u1) / 2) if False else _lp(w0, w1, (u0 + u1) / 2)
            cv2.line(A, (int(_lp(a[0], b[0], u0)), int(_lp(a[1], b[1], u0))),
                     (int(_lp(a[0], b[0], u1)), int(_lp(a[1], b[1], u1))), 1.0, max(1, int(ww)), cv2.LINE_AA)

    if kind == 'tick':                                  # ✓：短笔下行 → 长笔上扬
        p1 = (cx - 0.36 * S, cy + 0.00 * S); p2 = (cx - 0.07 * S, cy + 0.28 * S); p3 = (cx + 0.40 * S, cy - 0.34 * S)
        seg(p1, p2, c01(p / 0.40), th * 0.72, th * 0.95)
        seg(p2, p3, c01((p - 0.40) / 0.60), th * 0.95, th * 0.40)
    else:                                               # ✗：左上→右下，再右上→左下（第二笔更长）
        p1 = (cx - 0.32 * S, cy - 0.30 * S); p2 = (cx + 0.32 * S, cy + 0.32 * S)
        p3 = (cx + 0.36 * S, cy - 0.28 * S); p4 = (cx - 0.38 * S, cy + 0.30 * S)
        seg(p1, p2, c01(p / 0.40), th * 0.72, th * 0.95)
        seg(p3, p4, c01((p - 0.40) / 0.60), th * 0.95, th * 0.40)
    if abs(rot) > 1e-3:
        M = cv2.getRotationMatrix2D((float(cx), float(cy)), rot, 1.0)
        A = cv2.warpAffine(A, M, (W, H))
    A = np.clip(cv2.GaussianBlur(A, (0, 0), 1.8), 0, 1).astype(np.float32)
    c = np.array(col, np.float32)
    fr = np.clip(fr, 0, 4).astype(np.float32)
    fr = fr * (1 - 0.55 * cv2.GaussianBlur(A, (0, 0), 10)[..., None])          # 暗衬
    fr = fr * (1 - A[..., None]) + A[..., None] * c * 1.05
    return fr + cv2.GaussianBlur(A, (0, 0), max(2.0, S * 0.035))[..., None] * c * 0.30



# =========================================================================================== 副歌终「定」
class E01_r7(Shot):   # 第七棒代码刀（第八棒弃用，留作回退）S111 ECU竖刀刀尖朝天、纵贯画面偏右，逆光晨日在左下画外。
    #  刀身按截面着色：镐筋把刀身分成两面 —— 刃面（朝左下日）暖亮、平地（朝右上天）冷暗；刃口一条细亮线、刃文白雾；
    #  冷暖环境反射（刃面映地平线暖晕、平地映天空冷云条纹）；锋利斜尖（刃线直线斜收到背线尖点 + 横手线）；
    #  底部刀镡 + 缠柄入画（离镜最近，浅景深虚化）；碑拓「血」占刃宽 80%，日光自下而上扫过时字面反光；副句「未冷」右上
    V0, V1 = 800, 138            # 刀镡处 / 刀尖 的屏幕 y
    HW = 98                      # 刃宽一半（px）

    def __init__(self):
        self.sky = E.dawn_sky(111, horizon=0.86, sun=(260, 900), mid=(0.40, 0.27, 0.15), cloud=0.55)
        self.l2 = Sub('未冷', cts(48, [1, 2]), 1560, CT(48, 2) + 0.15, seed=2, y=330)
        from PIL import Image as _I
        tip = np.asarray(_I.open(ROOT + '/assets/gen/E_r6/blade_tip_cut.png').convert('RGB')).astype(np.float32) / 255
        tx = tip[250:1190, 286:368].mean(-1)
        tx = cv2.resize(tx, (300, 1100), interpolation=cv2.INTER_CUBIC)
        tx = cv2.GaussianBlur(tx, (0, 0), 2.0)
        self.tex = (tx / tx.mean()).astype(np.float32)                      # 原图金属锻纹（只取明暗细节，弱化，防止读成木纹）
        self.brush = (np.random.default_rng(5).random(300).astype(np.float32) - 0.5)
        self.brush = np.convolve(self.brush, np.ones(3) / 3, 'same').astype(np.float32)
        sw = np.asarray(_I.open(ROOT + '/assets/gen/E_r6/blade_vert_cut.png')).astype(np.float32) / 255
        g = sw[985:1270, 1222:1338]                                           # 刀镡 + 缠柄
        sc = 2 * self.HW * 1.0 / 57.0
        self.hilt = cv2.resize(g, (int(g.shape[1] * sc), int(g.shape[0] * sc)), interpolation=cv2.INTER_CUBIC)
        self.cool_sky = cv2.GaussianBlur(self.sky, (0, 0), 25)

    def geom(self, t):
        u = self.u(t)
        yy, xx = E.grid()
        v = np.clip((self.V0 - yy) / (self.V0 - self.V1), -0.4, 1.2)       # 0 = 刀镡，1 = 刀尖
        cx = 1150 + 22 * u - 150 * v + 30 * v * v                          # 刀身微弯、轻微左倾；推镜时缓慢右移
        hw = self.HW * (1 - 0.14 * np.clip(v, 0, 1))
        xe, xsp = cx - hw, cx + hw                                          # 左 = 刃口（朝日），右 = 刀背
        vt = 0.74                                                           # 横手线：此上刃线直线斜收到刀背顶点
        k = np.clip((v - vt) / (1 - vt), 0, 1)
        xe = xe + (xsp - xe) * (1 - (1 - k) ** 1.35)                       # 刃线微凸地斜收到刀背尖点
        s = (xx - xe) / np.maximum(xsp - xe, 1)                             # 0 = 刃口，1 = 刀背
        inside = (s > 0) & (s < 1) & (v > -0.02) & (v <= 1.0)
        A = inside.astype(np.float32)
        A = cv2.GaussianBlur(A, (0, 0), 0.8)
        return u, v, s, A, k

    def render(self, t):
        u, v, s, A, k = self.geom(t)
        fr = self.sky.copy()
        fr = fx2.god_rays(fr, (260, 900), strength=0.55, length=0.9, t=t, src_r=160)
        yy, xx = E.grid()
        sr = 0.36 + 0.25 * k                                                # 镐筋位置（尖部随横手线收向背）
        bev = np.clip((sr - s) / 0.012 + 0.5, 0, 1)                         # 1 = 刃面（镐筋以下）
        # 环境反射：刃面映左下地平线暖光（随 v 上去渐暗）；平地映天空冷云（取天空模糊镜像、纵向拉伸）
        sv = np.clip(v, 0, 1)
        # 刃面（朝左下日）：镜面映出地平线暖光 —— 下段炽亮、往上迅速转暗，带拉丝竖纹
        mw = self.sky[np.clip((620 + 300 * sv + 40 * (s - sr)).astype(np.int32), 0, H - 1), np.clip((xx * 0.35 + 80).astype(np.int32), 0, W - 1)]
        warm = mw * (1.55 - 1.15 * sv)[..., None] * np.array([1.05, 0.92, 0.80], np.float32)
        warm = warm * (0.65 + 0.7 * ((sr - s) / np.maximum(sr, 1e-3)))[..., None]       # 刃口侧更亮（截面弧度）
        # 平地（朝右上天）：镜面映天空冷云，高反差
        mir = self.cool_sky[np.clip((140 + 520 * (1 - sv)).astype(np.int32), 0, H - 1), np.clip((1900 - xx * 0.8).astype(np.int32), 0, W - 1)].mean(-1)
        mir = np.clip(0.10 + (mir - 0.18) * 1.6, 0.015, 1)
        cool = mir[..., None] * np.array([0.62, 0.74, 1.0], np.float32) + np.array([0.012, 0.016, 0.028], np.float32)
        across = (s - sr) / (1 - sr)
        cool = cool * (0.55 + 0.9 * np.exp(-((across - 0.78) / 0.18) ** 2) * 0.6 + 0.25 * across)[..., None]
        cool = cool + (np.exp(-((across - 0.06) / 0.05) ** 2) * 0.06)[..., None] * np.array([1.0, 0.8, 0.6], np.float32)   # 镐筋下沿接暖
        col = warm * bev[..., None] + cool * (1 - bev[..., None])
        brush = self.brush[np.clip(s * 299, 0, 299).astype(np.int32)]                    # 研磨拉丝（沿刃长方向）
        ti = np.clip((1 - sv) * 1099, 0, 1099).astype(np.int32); si = np.clip(s * 299, 0, 299).astype(np.int32)
        col = col * (0.88 + 0.12 * self.tex[ti, si] + 0.10 * brush)[..., None]
        # 刃文：刃口内侧一道白雾波纹
        ham = 0.10 + 0.025 * np.sin(yy / 23.0) + 0.012 * np.sin(yy / 7.0)
        col = col + (np.exp(-((s - ham) / 0.05) ** 2) * 0.10 * (1 - k))[..., None] * np.array([1.0, 0.95, 0.88], np.float32)
        # 刃口细亮线 + 镐筋棱线（亮）+ 刀背暗棱
        edge = np.exp(-(s / 0.010) ** 2)
        ridge = np.exp(-((s - sr) / 0.006) ** 2)
        spine = np.exp(-((1 - s) / 0.012) ** 2)
        col = col + edge[..., None] * np.array([1.0, 0.92, 0.78], np.float32) * 1.4 + ridge[..., None] * np.array([1.0, 0.85, 0.65], np.float32) * 0.5
        col = col * (1 - 0.6 * spine[..., None])
        # 横手线
        col = col + (np.exp(-((v - 0.74) / 0.0025) ** 2) * (s > 0) * 0.18)[..., None] * np.array([1.0, 0.85, 0.6], np.float32)
        # 日光沿刃自下而上扫（刃面最强）
        sy = 1000 - 1050 * eio(c01(u * 1.15))
        sheen = np.exp(-((yy - sy) / 60) ** 2)
        col = col + (sheen * (0.35 + 0.9 * bev) + sheen * edge * 1.5)[..., None] * np.array([1.0, 0.86, 0.62], np.float32)
        self.sheen_y = sy
        fr = fr * (1 - A[..., None]) + col * A[..., None]
        # 刃根铜鎺 + 刀镡（椭圆铁镡、上沿受暖光）+ 缠柄（菱形缠绳）：离镜最近 → 轻微虚化
        cx0 = 1150 + 22 * u
        th = math.atan2(150 - 30, self.V0 - self.V1); c_, s_ = math.cos(th), math.sin(th)     # 刀柄沿刀身轴线倾斜
        XX = (xx - cx0) * c_ - (yy - self.V0) * s_; YY = self.V0 + (xx - cx0) * s_ + (yy - self.V0) * c_
        L = np.zeros((H, W, 3), np.float32); M = np.zeros((H, W), np.float32)
        hb = (YY > self.V0 - 34) & (YY <= self.V0 + 4) & (np.abs(XX) < self.HW + 8)          # 鎺（铜）
        hbc = np.array([0.55, 0.36, 0.14], np.float32) * (0.6 + 0.8 * np.clip((-XX) / (2 * self.HW) + 0.5, 0, 1))[..., None]
        hbc = hbc + (np.exp(-((YY - (self.V0 - 30)) / 3) ** 2))[..., None] * np.array([1.0, 0.8, 0.5], np.float32) * 0.8
        L[hb] = hbc[hb]; M[hb] = 1
        gy0 = self.V0 + 16
        gd = (XX / 185) ** 2 + ((YY - gy0) / 26) ** 2                                     # 镡：上表面椭圆
        top = gd < 1
        gcol = np.array([0.05, 0.045, 0.04], np.float32) * (0.8 + 0.5 * np.clip((-XX) / 370 + 0.5, 0, 1))[..., None]
        rimg = np.exp(-((np.sqrt(gd) - 0.96) / 0.03) ** 2) * (YY < gy0) * np.clip((100 - XX) / 240, 0, 1)
        gcol = gcol + rimg[..., None] * np.array([1.0, 0.72, 0.38], np.float32) * 1.3
        side = (YY >= gy0) & ((XX / 185) ** 2 + ((YY - gy0 - 16) / 26) ** 2 < 1)
        L[side] = np.array([0.025, 0.022, 0.02], np.float32); M[side] = 1
        L[top] = gcol[top]; M[top] = 1
        hd = (YY > gy0 + 34) & (np.abs(XX) < 74)                                              # 缠柄
        dd = np.abs((XX + (YY - gy0)) % 46 - 23) + np.abs((XX - (YY - gy0)) % 46 - 23)
        wrap = np.clip((dd - 16) / 6, 0, 1)
        hc = np.array([0.035, 0.03, 0.027], np.float32) * (1 - wrap)[..., None] + np.array([0.075, 0.018, 0.014], np.float32) * wrap[..., None]
        hc = hc + (np.exp(-((dd - 15) / 2.0) ** 2) * 0.05)[..., None] * np.array([1.0, 0.75, 0.5], np.float32)   # 缠绳棱受光
        hc = hc * (0.6 + 0.8 * np.clip((-XX) / 148 + 0.5, 0, 1))[..., None]
        L[hd] = hc[hd]; M[hd] = 1
        L = cv2.GaussianBlur(L, (0, 0), 1.6); M = cv2.GaussianBlur(M, (0, 0), 1.6)
        fr = fr * (1 - M[..., None]) + L
        self.blade = (v, s, A)
        tip = (float(1150 + 22 * u - 150 + 30 + self.HW * 0.86), float(self.V1) + 2)
        self.tip = tip
        if u > 0.75: fr = E.flare_streak(fr, tip, amt=1.4 * c01((u - 0.75) / 0.1) * (1 - c01((u - 0.9) / 0.1)), angle=0)
        fr = E.dust_motes(fr, t, 111, n=70, amt=0.5, drift=(60, -20), depth=True)
        return bloom(fr, 0.85, 0.5)

    def text(self, fr, t):
        if hasattr(self, 'blade'):
            v, s, A = self.blade
            p = c01((t - (CT(48, 0) - 0.1)) / 0.22)
            if p > 0:
                cy = 560
                vv = (self.V0 - cy) / (self.V0 - self.V1)
                cx = 1150 + 22 * self.u(t) - 150 * vv + 30 * vv * vv
                base = fr.copy()
                rub = R3.blood_rub(fr.copy(), '血', cx, cy, 172, p, seed=11)          # 碑拓「血」：字宽 ≈ 刃宽 80%
                m = np.clip(np.abs(rub - base).sum(-1) * 3, 0, 1)
                Ab = cv2.erode(A, np.ones((5, 5), np.uint8))
                dark = cv2.GaussianBlur(m, (0, 0), 3) - m                           # 暗边
                out = rub * (1 - np.clip(dark * 1.2, 0, 0.6))[..., None]
                yy = np.arange(H, dtype=np.float32)[:, None]
                sh = np.exp(-((yy - self.sheen_y) / 55) ** 2)                       # 日光扫过 → 字面反光
                out = out + (m * sh * 0.9)[..., None] * np.array([1.0, 0.55, 0.35], np.float32)
                fr = fr * (1 - Ab[..., None]) + out * Ab[..., None]
        return self.l2.draw(fr, t)


class E01(Shot):   # S111 ECU（第八棒重做）：生图真刃身 E_r6/blade_vert 翻转迎日、拉成 1:6 窄长刃（R8.BladeECU），切先朝天、刃口朝左下画外晨日；
    #  冷暖环境反射重新着色 + 原图锻纹/划痕 + 刃文 + 连续刃口亮线；日光自下而上扫刃；「血」阴刻入刃面（自下而上刻出，槽底残血，扫光时字口反光）
    TIP = (1080, 150)
    ANG = -8.0

    def __init__(self):
        self.sky = E.dawn_sky(111, horizon=0.86, sun=(260, 900), mid=(0.40, 0.27, 0.15), cloud=0.55)
        self.l2 = Sub('未冷', cts(48, [1, 2]), 1560, CT(48, 2) + 0.15, seed=2, y=330)
        self.B = R8.BladeECU(self.sky)

    def _pose(self, u):
        return (self.TIP[0] + 18 * u, self.TIP[1] + 6 * (1 - u)), self.ANG + 1.5 * u

    def render(self, t):
        u = self.u(t)
        fr = self.sky.copy()
        fr = fx2.god_rays(fr, (260, 900), strength=0.55, length=0.9, t=t, src_r=160)
        (tx, ty), ang = self._pose(u)
        sy_scr = 1000 - 1050 * eio(c01(u * 1.15))
        sy_loc = (sy_scr - ty) / math.cos(math.radians(ang)) + self.B.top
        col, sh = self.B.layer(t, u, sy_loc)
        p = c01((t - (CT(48, 0) - 0.1)) / 0.22)
        ly = (560 - ty) / math.cos(math.radians(ang)) + self.B.top
        col = self.B.engrave(col, '血', 200, ly, p, sh, sy_loc, font='kai', xc=0.5)
        fr, Aw, _ = self.B.place(fr, col, tx, ty, ang)
        # 刃根往下离镜更近 → 轻微虚化（浅景深）
        bl = cv2.GaussianBlur(fr, (0, 0), 2.2)
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        k = np.clip((yy - 780) / 180, 0, 1) * Aw[..., None]
        fr = fr * (1 - k) + bl * k
        # 刃身贴近日侧的暖色溢光（halation）
        fr = fr + cv2.GaussianBlur(Aw, (0, 0), 14)[..., None] * np.array([0.10, 0.06, 0.03], np.float32) * (1 - 0.6 * Aw[..., None])
        self.tip = (tx, ty)
        if u > 0.75: fr = E.flare_streak(fr, (tx, ty + 4), amt=1.4 * c01((u - 0.75) / 0.1) * (1 - c01((u - 0.9) / 0.1)), angle=0)
        fr = E.dust_motes(fr, t, 111, n=70, amt=0.5, drift=(60, -20), depth=True)
        return bloom(fr, 0.85, 0.5)

    def text(self, fr, t): return self.l2.draw(fr, t)


class E02(Shot):   # S112（第六棒重做，去和副歌一 S030「背影举刀指月」撞构图）：正面极低机位 3/4，刀扛在右肩、刀身向后；
    #  日在画外右上，只给轮廓光与一束斜入体积光；冷灰蓝黎明天。「刀」「不」「放」三方小朱印随唱逐个盖在握刀的拳与护臂上（只用朱印一种，不再有灰字）
    GR = dict(expo=0.80, sat=0.58, tint=(0.96, 0.98, 1.04), lift=0.0, gamma=1.10)
    FIST = (0.305, 0.375)

    def __init__(self):
        self.sky = E.dawn_sky(112, horizon=0.98, top=(0.025, 0.03, 0.055), mid=(0.16, 0.20, 0.28), hor=(0.62, 0.56, 0.52), cloud=0.9, sun=None)
        r = np.random.default_rng(112)
        self.grass = [(r.uniform(-80, 420) if i % 2 else r.uniform(1600, 2000), r.uniform(0.7, 1.5), r.uniform(-0.5, 0.5)) for i in range(26)]
        self.tm = [CT(48, 3) + 0.02, CT(48, 4), CT(48, 5)]

    def render(self, t):
        u = self.u(t)
        fr = self.sky.copy()
        yy, xx = E.grid()
        glow = np.exp(-(((xx - 2000) / 900) ** 2 + ((yy + 50) / 520) ** 2))         # 画外右上日：天角暖晕
        fr = fr + glow[..., None] * np.array([0.9, 0.62, 0.36], np.float32) * 0.55
        fr = fx2.god_rays(fr, (2050, -60), strength=0.55, length=1.0, t=t, src_r=220)
        z, info = put(np.zeros((H, W, 3), np.float32), t, 'E_r6/shoulder_low', (1180 - 30 * u, 1075), h=930, anc=(0.5, 1.0),
                      rim=(1.0, 0.84, 0.6), rim_amt=3.0, rim_dir=(0.7, -0.7), grade=self.GR, wind=8)
        C, A = sprite_clean(z, info['A'], erode=2, rim_col=(1.0, 0.8, 0.55), rim_amt=1.2, rim_dir=(0.7, -0.7), cool_amt=0.25)
        f = (np.clip((0.92 - A) / 0.6, 0, 1) * (A > 0.03))[..., None]          # 逆光飞丝：灰白 → 暖金透光（同画外右上日光）
        C = C * (1 - f) + C * np.array([1.25, 0.92, 0.6], np.float32) * f
        fr = fr * (1 - A[..., None]) + C * A[..., None]
        self.fist = info['to_scr'](self.FIST)
        G = np.zeros((H // 2, W // 2), np.float32)                         # 前景：贴镜头的草叶（强虚化、压暗）
        for (x, s_, lean) in self.grass:
            x0 = (x + 60 * u) / 2
            cv2.line(G, (int(x0), H // 2 - BAR // 2 + 30), (int(x0 + (lean + 0.12 * math.sin(t * 2.3 + x)) * 120 * s_), int(H // 2 - BAR // 2 - 95 * s_)), 1.0, 6, cv2.LINE_AA)
        G = cv2.resize(cv2.GaussianBlur(G, (0, 0), 7), (W, H))
        fr = fr * (1 - np.clip(G * 1.3, 0, 1)[..., None] * 0.92)
        fr = E.dust_motes(fr, t, 1121, n=36, amt=0.5, drift=(-30, -40), size=(3, 9), blur=4, col=(0.9, 0.85, 0.8))
        return bloom(fr, 0.8, 0.4)

    def text(self, fr, t):
        if not hasattr(self, 'fist'): return fr
        fx, fy = self.fist
        spots = [(fx - 20, fy - 10, 128, -8), (fx - 70, fy + 150, 118, 5), (fx - 40, fy + 300, 132, -3)]
        for k, ch in enumerate('刀不放'):
            p = (t - (self.tm[k] - 0.09)) / 0.6
            if p > 0:
                x, y, sz, rt = spots[k]
                if not glyph_off('E02'):                     # [r4-DE#46] 去「刀不放」朱印
                    fr = T.stamp_seal(fr, ch, x, y, sz, min(1, p), style='yin', rot=rt, seed=40 + k, alpha=0.95)
        return fr


class E03(Shot):   # S113（第三棒重做）一点透视碑林：两列刻满律令的「天理」碑沿纵深排开，冷灰蓝晨雾，尽头门洞白光；推轨前进 + 前景碑擦镜虚化。
    #  「世间从来没有」一行横排、按唱的顺序逐字烧出（阅读顺序 = 出现顺序），压在画面下三分之一的暗衬上。
    def __init__(self):
        self.hall = R3.SteleHall(seed=31, n=7, hy=455)
        tm = cts(49, range(6))
        self.l = LyrO(row('世间从来没有', tm, 960, 800, size=100, gold='世间', track=0.18, font='serif_b'), CT(49, 6) - 0.12, seed=10,
                      glow=0.3, outline=3, plate_amt=0.45)

    def render(self, t):
        u = self.u(t)
        fr = self.hall.render(t, dz=0.2 + 1.5 * eio(u), sway=-30 + 60 * u)
        fr = fx2.god_rays(fr, (960, 455), strength=0.55, length=1.0, t=t)
        fr = E.dust_motes(fr, t, 113, n=90, amt=0.45, drift=(10, 6), col=(0.85, 0.9, 1.0), depth=True)
        return bloom(fr, 0.85, 0.4)

    def text(self, fr, t): return self.l.draw(fr, t)


def cloud_blit(fr, lum, a, ox, yoff, tone, amb=0.03, fade=140):
    """云海层横移贴图（层宽 2W，取 [ox%W, ox%W+W] 窗口；顶边软过渡，不留硬切线）。"""
    x0 = int(ox % W)
    L = lum[:, x0:x0 + W]; A = a[:, x0:x0 + W]
    M = np.float32([[1, 0, 0], [0, 1, yoff]])
    L = cv2.warpAffine(L, M, (W, H)); A = cv2.warpAffine(A, M, (W, H))
    A = A * sstep(yoff, yoff + fade, np.arange(H, dtype=np.float32))[:, None]
    R = L[..., None] * np.asarray(tone, np.float32) + amb
    return fr * (1 - A[..., None]) + R * A[..., None]


class E04(Shot):   # S114 CU 暗殿金匾「天理昭彰」：随唱逐字亮起；高窗光柱
    def __init__(self):
        n = K.fbm(H // 2, W // 2, 140, base=3, octaves=5)
        slat = (np.sin(np.linspace(0, 60, W // 2)) * 0.5 + 0.5)[None, :] ** 6
        self.bg = cv2.resize(((0.03 + 0.05 * n + 0.025 * slat)[..., None] * np.array([1.0, 0.8, 0.6], np.float32)).astype(np.float32), (W, H))
        self.pl = PR.Plaque('天理昭彰', seed=3)
        self.l = Sub('什么', cts(49, [6, 7]), 'left', 198.3, seed=20)
        self.lit_t = cts(49, [8, 9, 10, 11])

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        fr = fx2.light_beam(fr, (300, 80), (1100, 1000), 60, 420, t=t, strength=0.55, seed=4)
        fr = fx2.light_beam(fr, (700, 60), (1500, 1000), 30, 260, t=t, strength=0.35, seed=5)
        fr = plaque_lit(self.pl, fr, t, 960, 520, 1300, self.lit_t, crack=0.0, dim=0.35)
        fr = E.dust_motes(fr, t, 114, n=120, amt=0.45, drift=(12, 8), depth=True)
        return fr

    def text(self, fr, t): return self.l.draw(fr, t)


def plaque_lit(pl, fr, t, cx, cy, w, lit_t, crack=0.0, dim=0.35, tilt=0.0, sheen_t=None):
    """金匾：底子压暗，按字头逐字点亮（字形发金光 + 扫光）。"""
    base = fr.copy()
    fr, _ = pl.draw(fr, t, cx, cy, w, crack=crack, tilt=tilt)
    fr = base + (fr - base) * (dim + (1 - dim) * 0.25)
    n = len(pl.text); h = w * 0.36; fs = min(h * 0.62, (w * 0.86) / n)
    L = T.Layer()
    for i, ch in enumerate(pl.text):
        e = (t - (lit_t[i] - 0.12)) / 0.18
        if e <= 0: continue
        x = cx + (i - (n - 1) / 2) * (w * 0.86 / n)
        if tilt:
            c, s = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
            dx, dy = x - cx, 0
            x, y = cx + dx * c - dy * s, cy + dx * s + dy * c
        else: y = cy
        a = T.glyph(ch, 'song', fs, False)
        if tilt:
            g = a.shape[0]; M = cv2.getRotationMatrix2D((g / 2, g / 2), -tilt, 1.0); a = cv2.warpAffine(a, M, (g, g))
        fl = 1.0 + 1.2 * math.exp(-max(0, t - lit_t[i]) / 0.15)
        L.paste(a, x, y, (1.0, 0.82, 0.48), min(1, e) * fl * 0.9)
    return T.compose(fr, L, shadow=0, glow=0.9, glow_sigma=22, glow_color=(1.0, 0.6, 0.25))


class E05(Shot):   # S114b ECU 低角度荷兰角：昭、彰亮起即开裂，金光从裂缝透出，碎屑剥落
    def __init__(self):
        n = K.fbm(H // 2, W // 2, 141, base=3, octaves=5)
        self.bg = cv2.resize(((0.02 + 0.04 * n)[..., None] * np.array([1.0, 0.8, 0.6], np.float32)).astype(np.float32), (W, H))
        self.pl = PR.Plaque('天理昭彰', seed=8)
        self.lit_t = [0, 0] + cts(49, [10, 11])

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        fr = fx2.light_beam(fr, (1700, 60), (900, 1000), 40, 380, t=t, strength=0.5, seed=7)
        ta, tb = CT(49, 10), CT(49, 11)
        crack = 0.0 if t < ta else (0.35 * eout((t - ta) / 0.3) if t < tb else 0.35 + 0.65 * eout((t - tb) / 0.35))
        fr = plaque_lit(self.pl, fr, t, 520, 560, 2700, [ta - 9, ta - 9, ta, tb], crack=crack, dim=0.45, tilt=-9)
        if t > tb:   # 金光爆出
            q = t - tb
            fr = E.flare_streak(fr, (1250, 470), amt=1.3 * math.exp(-q / 0.25), angle=-9, length=1.4)
            fr = RS.fx_sparks(fr, t, tb, (1250, 480), 1141, n=80, spd=1100, dirv=(0.3, -1), spread=1.6, amt=1.2)
        return fr


class E06(Shot):   # S115 MS（第三棒重做）律令挂轴林：远中近三层直垂挂轴（刚体，只绕挂点微摆，不再拉伸变形），背光透纸；
    #  推轨穿帘：近层大轴虚化擦镜；「若规则是」烧在正中偏右的一幅题字轴上（大字竖排，规则 朱红）。
    def __init__(self):
        self.sky = E.dawn_sky(115, horizon=0.7, sun=(900, 520), hor=(1.0, 0.86, 0.6), mid=(0.62, 0.48, 0.30), cloud=0.3)
        self.far = R3.Scrolls(15, 15, (40, 1880), 150, (640, 720), (78, 104), text_size=12)
        self.mid = R3.Scrolls(16, 5, (120, 1100), 110, (820, 880), (150, 180), text_size=17)
        self.title = R3.Scrolls(19, 1, (1400, 1400), 96, (860, 860), (270, 270), tone=(0.95, 0.90, 0.78), blank=True)
        self.title.items[0]['amp'] = 0.25
        self.near = R3.Scrolls(17, 3, (-120, 2040), 40, (1150, 1250), (300, 360), text_size=26)
        tm = cts(50, [0, 1, 2, 3])
        self.l = Lyr(row('若规则是', tm, 1400, 560, size=150, vertical=True, red='规则', base=(0.06, 0.045, 0.04), track=0.12, font='serif_black'),
                     CT(50, 4) - 0.05, seed=30, glow=0.0, shadow=0.0)

    def render(self, t):
        u = self.u(t)
        fr = E.sun_disc(self.sky.copy(), (900, 520), 80, amt=1.0)
        C, A = self.far.layer(t, wind=0.8); C, A = R3.Scrolls.light(C, A, fr, 1.0, blur=1.6)
        fr = R3.comp(fr, C, A)
        fr = fx2.god_rays(fr, (900, 520), strength=0.55, length=0.9, t=t)
        C, A = self.mid.layer(t, wind=1.0); C, A = R3.Scrolls.light(C, A, fr, 0.8)
        fr = R3.comp(fr, C, A)
        C, A = self.title.layer(t, wind=1.0); C, A = R3.Scrolls.light(C, A, fr, 0.55)
        fr = R3.comp(fr, C, A)
        sc = 1.0 + 0.35 * eio(u)
        C, A = self.near.layer(t, wind=1.2, scale=sc, dx=-80 * u); C, A = R3.Scrolls.light(C, A, fr * 0.6, 0.4, blur=9)
        fr = R3.comp(fr, C * 0.55, A)
        return bloom(fr, 0.85, 0.35)

    def text(self, fr, t):
        return self.l.draw(fr, t)


class E07(Shot):   # S116 LS（第三棒重做）挂轴缝后，太上皇本人（实体、正面受光、五官清楚）→ 环绕揭示：原来是纸扎（实体纸扎，不透明）
    def __init__(self):
        self.sky = E.dawn_sky(116, horizon=0.75, sun=(1480, 330), hor=(0.62, 0.46, 0.30), mid=(0.20, 0.15, 0.10), top=(0.03, 0.025, 0.02), cloud=0.3)
        self.cur = R3.Scrolls(17, 6, (-40, 1960), 50, (980, 1050), (190, 240), text_size=22)
        self.l = LyrO(row('谎言', cts(50, [4, 5]), 960, 800, size=230, red='谎言', track=0.08, font='serif_black'), CT(50, 6) - 0.1, seed=40,
                      outline=5, plate_amt=0.6, glow=0.3)

    def render(self, t):
        u = self.u(t)
        fr = self.sky.copy()                                               # 第四棒：背景压暗、日偏右后方（只留光晕），纸扎在暗底上成实体
        fr = fx2.god_rays(fr, (1480, 330), strength=0.35, length=0.8, t=t)
        rv = eio((t - 201.2) / 0.4)
        dx = 70 - 140 * eio(u)
        GE = dict(expo=1.0, sat=0.62, tint=(1.06, 0.99, 0.9), lift=0.02, gamma=1.0)
        if rv < 1:      # 帘后：太上皇本人，前侧受光，五官清楚
            fr0, _ = put(fr.copy(), t, 'S116/emperor', (960 + dx, 1590), h=1500, rim=GOLDW, rim_amt=2.6, grade=GE, wind=2)
        if rv > 0:      # 揭示：纸扎（宣纸蒙竹骨），实体不透明，只在边缘透光
            fr1, info = put(fr.copy() * 0.45, t, 'E_r2/paper_effigy', (960 + dx, 1590), h=1500, rim=GOLDW, rim_amt=3.4, rim_dir=(0.9, -0.4), wind=6,
                            grade=dict(expo=1.05, sat=0.5, tint=(1.06, 1.0, 0.9), lift=0.0, gamma=1.0))   # 第四棒：暗底上亮宣纸，读作实体
            (bx0, by0), (bx1, by1) = info['box']                              # 第四棒：身体部分（头以下）糊上不透光的厚宣纸：抹平透出的灯笼网格，只留竹骨压痕
            yv = np.arange(H, dtype=np.float32)[:, None]
            bm = info['A'] * sstep(by0 + 0.20 * (by1 - by0), by0 + 0.30 * (by1 - by0), yv)
            sm = cv2.GaussianBlur(fr1, (0, 0), 7)
            lum = sm.mean(-1, keepdims=True)
            solid = (0.6 * lum + 0.4 * sm) * np.array([1.08, 0.98, 0.82], np.float32) * 1.05
            fr1 = fr1 * (1 - 0.75 * bm[..., None]) + solid * 0.75 * bm[..., None]
            fr1 = paper_frame(fr1, info['A'], t, amt=0.32)
            A_ = info['A']                                                   # 体积：边缘向内压暗（纸扎是实心的，不是灯笼）+ 左侧冷面
            occ = np.clip(A_ - cv2.GaussianBlur(A_, (0, 0), 28) * 0.0, 0, 1) * (1 - cv2.GaussianBlur((A_ > 0.5).astype(np.float32), (0, 0), 30))
            xx_ = np.arange(W, dtype=np.float32)[None, :]
            side_ = np.clip((1100 + dx - xx_) / 500, 0, 1)
            fr1 = fr1 * (1 - (0.55 * occ + 0.35 * side_ * A_)[..., None])
        if rv >= 1: fr = fr1
        elif rv <= 0: fr = fr0
        else:            # 第四棒：揭示不再叠化（双重曝光读成「半透明」），改为一道纸面反光斜扫 = 硬擦除边界：光带左边已是纸扎、右边还是真人
            yy, xx = E.grid(); sx = xx - (300 + 1400 * rv) + (yy - 540) * 0.4
            m = sstep(8, -8, sx)[..., None]
            fr = fr1 * m + fr0 * (1 - m)
            band = np.exp(-(sx / 50) ** 2)
            fr = fr + band[..., None] * GOLDW * 0.6
        sh = -300 * eio(u) + 150                                          # 前景挂轴从两侧掠过（环绕视差，强虚化）
        C, A = self.cur.layer(t, wind=1.0, dx=sh)
        side = np.clip(np.abs(np.arange(W, dtype=np.float32) - 960) / 160 - 3.6, 0, 1)[None, :]   # 第四棒：前景挂轴只在两侧画边、实体不透明，不再叠在纸扎身上
        C, A = R3.Scrolls.light(C, A, fr * 0.5, 0.5, blur=10)
        fr = R3.comp(fr, C * 0.35, A * side)
        fr = PD.play(fr, 'L51', t)  # [r4-props]
        return bloom(fr, 0.85, 0.35)

    def text(self, fr, t): return self.l.draw(fr, t)


_PF = {}
def paper_frame(fr, A, t, seed=0, amt=0.55):
    """纸扎质感：皱纸纤维（明暗 ±）+ 不规则竹骨（少量歪斜竹篾，透光处亮、骨处暗）+ 糊纸接缝。只在精灵 alpha 内。"""
    if seed not in _PF:
        r = np.random.default_rng(900 + seed)
        yy, xx = E.grid()
        m = np.zeros((H, W), np.float32)
        for k in range(6):                                  # 竖篾：微弯、粗细不一
            x0 = 300 + k * 260 + r.uniform(-60, 60); a = r.uniform(-0.08, 0.08); w = r.uniform(2.5, 6)
            m = np.maximum(m, np.exp(-((xx - (x0 + a * (yy - 540) + 14 * np.sin(yy / r.uniform(90, 160)))) / w) ** 2))
        for k in range(5):                                  # 横篾
            y0 = 200 + k * 180 + r.uniform(-40, 40); a = r.uniform(-0.12, 0.12); w = r.uniform(2.5, 5)
            m = np.maximum(m, np.exp(-((yy - (y0 + a * (xx - 960) + 10 * np.sin(xx / r.uniform(120, 220)))) / w) ** 2))
        crumple = K.fbm(H // 2, W // 2, 910 + seed, base=26, octaves=5)
        crumple = cv2.resize(crumple, (W, H))
        fib = cv2.resize(K.fbm(H // 2, W // 2, 920 + seed, base=180, octaves=2), (W, H))
        seam = np.exp(-((np.sin((xx * 0.8 + yy * 0.6) / 210.0)) / 0.025) ** 2) * 0.5   # 糊纸接缝（斜向）
        _PF[seed] = (cv2.GaussianBlur(m, (0, 0), 1.0), crumple, fib, seam)
    m, cr, fib, seam = _PF[seed]
    tex = 0.86 + 0.22 * cr + 0.08 * (fib - 0.5)
    k = A[..., None]
    out = fr * (1 - k) + fr * k * tex[..., None]
    out = out * (1 - (amt * m + 0.25 * seam * amt)[..., None] * k)
    halo = cv2.GaussianBlur(m, (0, 0), 6) - m * 0.5                     # 骨两侧纸被绷紧 → 微亮
    return out + np.clip(halo, 0, 1)[..., None] * k * np.array([1.0, 0.85, 0.6], np.float32) * 0.08 * (amt / 0.55)


def sprite_clean(z, A, erode=2, rim_col=(1.0, 0.62, 0.30), rim_amt=0.9, rim_dir=(0.8, -0.6), cool=(0.45, 0.55, 0.75), cool_amt=0.35):
    """第五棒：精灵收边（z 为贴在黑底上的预乘色）。alpha 内缩 erode px + 边缘去白（用内部颜色替换边缘色）+ 方向性暖轮廓光 / 反侧冷边。返回 (C, A)。"""
    A = np.clip(A, 0, 1).astype(np.float32)
    C = z / np.maximum(A, 1e-3)[..., None]
    Ae = cv2.erode(A, np.ones((2 * erode + 1, 2 * erode + 1), np.uint8))
    Ae = cv2.GaussianBlur(Ae, (0, 0), 0.9)
    core = (A > 0.97).astype(np.float32)
    core = cv2.erode(core, np.ones((7, 7), np.uint8))
    s = 9
    num = cv2.GaussianBlur(C * core[..., None], (0, 0), s); den = cv2.GaussianBlur(core, (0, 0), s)[..., None]
    Cin = num / np.maximum(den, 1e-4)
    edge = np.clip(1 - cv2.erode(A, np.ones((13, 13), np.uint8)), 0, 1) * (den[..., 0] > 0.02)
    Cin = np.minimum(Cin, C)                                               # 只压亮不提亮：白毛边 → 内部色
    C = C * (1 - edge[..., None]) + Cin * edge[..., None]
    ring = np.clip(Ae - cv2.GaussianBlur(Ae, (0, 0), 7), 0, 1) * 2.2
    gy, gx = np.gradient(cv2.GaussianBlur(Ae, (0, 0), 5))
    n = np.hypot(gx, gy) + 1e-6
    d = -(gx * rim_dir[0] + gy * rim_dir[1]) / n                           # 外法线与光向夹角
    warm = ring * np.clip(d, 0, 1) ** 1.5
    cold = ring * np.clip(-d, 0, 1) ** 1.5
    C = C + warm[..., None] * np.asarray(rim_col, np.float32) * rim_amt + cold[..., None] * np.asarray(cool, np.float32) * cool_amt
    return C, Ae


class E08(Shot):   # S117 CU（第七棒重做烧洞）纸糊太上皇巨脸：宣纸叠皱 + 两条斜向糊纸接缝；火从眉心烧出一个横向不规则的洞
    #  （外圈暗褐焦痕 + 纸纤维毛边 / 中间断续橙红火线 / 内圈卷起碳化黑边），洞内近黑，只露被下方火光照亮的鬼屠双眼；
    #  「伪装」无外框，笔画边缘自燃（碳化 + 火星），位置在脸左侧
    TX, TY, TS = 300, (410, 650), 210
    CX, CY = 1015, 430                    # 老者两眼中点（f6064 实测 900/1130, 415）
    RX, RY = 345, 200                     # 洞终值半轴

    def __init__(self):
        yy, xx = E.grid()
        n = K.fbm(H // 2, W // 2, 1171, base=4, octaves=5)
        self.void = cv2.resize(((0.006 + 0.012 * n)[..., None] * np.array([1.0, 0.75, 0.55], np.float32)).astype(np.float32), (W, H))
        cr = cv2.resize(K.fbm(H // 2, W // 2, 1172, base=30, octaves=5), (W, H))
        fib = cv2.resize(K.fbm(H // 2, W // 2, 1173, base=200, octaves=2), (W, H))
        key = np.exp(-(((xx - 1500) / 900) ** 2 + ((yy - 200) / 700) ** 2))
        self.bg = ((0.05 + 0.20 * key)[..., None] * np.array([1.0, 0.62, 0.32], np.float32) * (0.85 + 0.25 * cr + 0.08 * (fib - 0.5))[..., None]).astype(np.float32)
        self.crease = R7.paper_creases(717)
        self.smul, self.sadd = R7.paper_seams((((540, 120), (1390, 960)), ((1240, 120), (1760, 760))), 718)
        lo, mid, hi, hair, brk = R7.hole_noise(719)
        self.D = (np.hypot(xx - self.CX, (yy - self.CY) * self.RX / self.RY) + lo * 150 + mid * 46 + hi * 6).astype(np.float32)
        self.tm = []
        for k, ch in enumerate('伪装'):
            L1 = T.Layer(); L1.paste(T.glyph(ch, 'serif_black', self.TS, False), self.TX, self.TY[k], (1, 1, 1)); self.tm.append(L1.A.copy())
        self.t_in = [CT(50, 6), CT(50, 7)]
        self.grade = dict(expo=0.92, sat=0.42, tint=(1.06, 0.99, 0.90), lift=0.0, gamma=1.06)
        em = np.zeros((H, W), np.float32)                                  # 洞内鬼屠双眼的受光蒙版（两只眼各一椭圆）
        for ex in (self.CX - 126, self.CX + 126):
            em = np.maximum(em, np.exp(-(((xx - ex) / 105) ** 2 + ((yy - (self.CY + 2)) / 46) ** 2) ** 1.4))
        self.eyem = em

    def radius(self, t):
        q = t - (self.t_in[0] + 0.03)
        if q < 0: return -1.0
        return self.RX * (1 - math.exp(-q / 0.30)) ** 0.9 * (0.12 + 0.88 * c01(q / 0.08))

    def render(self, t):
        u = self.u(t)
        z, info = put(np.zeros((H, W, 3), np.float32), t, 'E_r6/emperor_cu', (1000, 1260), h=1420 * (1 + 0.04 * u), rim=(1.0, 0.6, 0.3), rim_amt=1.2,
                      rim_dir=(0.8, -0.6), wind=1, grade=self.grade)
        C, A = sprite_clean(z, info['A'], erode=2, rim_col=(1.0, 0.58, 0.26), rim_amt=1.4, rim_dir=(0.8, -0.6))
        yy, xx = E.grid()
        key = np.clip(0.55 + 0.6 * ((xx - 1010) / 600 - (yy - 500) / 900), 0.35, 1.0)
        C = C * key[..., None] * np.array([1.03, 0.98, 0.93], np.float32) + (1 - key)[..., None] * np.array([0.075, 0.03, 0.006], np.float32)
        lum = C.mean(-1, keepdims=True); sd = np.clip((lum - 0.30) / 0.30, 0, 1) * 0.75
        C = C * (1 - sd) + lum * np.array([1.0, 0.97, 0.94], np.float32) * sd
        fr = self.bg * (1 - A[..., None]) + C * A[..., None]
        # 宣纸：整幅都是糊纸（脸和底一样），叠皱 40% + 接缝
        pm = 1 + (self.crease - 1) * 0.40 * 2.2
        fr = fr * pm[..., None] * self.smul[..., None] + self.sadd * np.clip(fr.mean(-1, keepdims=True) * 4, 0.25, 1)
        fr = fr * np.array([1.03, 1.0, 0.94], np.float32)
        R = self.radius(t)
        if R >= 0:
            F = self.D - R
            v = self.void.copy()
            v, bi = put(v, t, 'S123/front|crop=0.36,0.25,0.64,0.45', (self.CX, 380 - 6 * u), w=880, anc=(0.5, 0.5),
                        rim=(1.0, 0.6, 0.3), rim_amt=1.0, rim_dir=(0.0, 1.0), grade=dict(expo=1.0, sat=0.65, tint=(1.12, 0.95, 0.80), lift=0.0, gamma=1.0), wind=0)
            under = np.clip((yy - (self.CY - 50)) / 90, 0.3, 1.0)         # 火光从下往上照
            keep = self.eyem * np.clip((-F - 40) / 22, 0, 1) * under
            v = self.void + (v * np.array([1.25, 0.95, 0.72], np.float32) - self.void) * keep[..., None] * 1.9
            v = np.minimum(v, np.where(keep[..., None] > 0.05, 1.0, 0.13))
            fr = R7.burn_hole(fr, v, F, t, 719)
            fr = self.ash(fr, t, F)
        return bloom(fr, 0.9, 0.35)

    def ash(self, fr, t, F):
        """飞灰：沿火线放出、上飘，由亮转灰。"""
        q = t - self.t_in[0]
        ys, xs = np.nonzero(np.abs(F[::4, ::4]) < 2.5)
        if len(xs) == 0: return fr
        P = np.zeros((H, W), np.float32); G = np.zeros((H, W), np.float32)
        r = np.random.default_rng(int(t * 30) * 7 + 3)
        for j in r.choice(len(xs), min(110, len(xs)), replace=False):
            age = r.uniform(0, 0.5)
            x = xs[j] * 4 + 30 * age + 10 * math.sin(j + t * 3); y = ys[j] * 4 - (80 + 160 * r.random()) * age
            tgt = P if age < 0.2 else G
            cv2.circle(tgt, (int(x), int(y)), int(1 + 1.6 * r.random() * (0.5 + age)), float(1 - age / 0.5), -1, cv2.LINE_AA)
        return fr + cv2.GaussianBlur(P, (0, 0), 0.8)[..., None] * np.array([1.4, 0.7, 0.25], np.float32) + cv2.GaussianBlur(G, (0, 0), 1.2)[..., None] * np.array([0.2, 0.18, 0.17], np.float32)

    def text(self, fr, t):
        for k in range(2):
            p = c01((t - (self.t_in[k] - 0.07)) / 0.12)
            if p <= 0: continue
            if not glyph_off('E08'):        # [r4-DE#46] 去「伪装」烧字
                fr = R7.self_burn_glyph(fr, self.tm[k] * p, t, self.t_in[k] - 0.07, seed=50 + k)
        return fr


class E09(Shot):   # S118 MS 交叉斩：一刀斜劈，纸帘沿刀线断开；「那就撕碎」沿刀线排、被一分为二
    def __init__(self):
        self.sky = E.dawn_sky(1180, horizon=0.72, sun=(1500, 500), hor=(1.0, 0.84, 0.55), mid=(0.55, 0.40, 0.24), cloud=0.3)
        self.cur = R3.Scrolls(18, 11, (60, 1860), 70, (880, 960), (120, 160), text_size=17)
        ts = cts(51, [0, 1, 2, 3])
        self.ts = CT(51, 2)
        p0, p1 = np.array([300.0, 300.0]), np.array([1700.0, 780.0])
        self.p0, self.p1 = p0, p1
        pos = [p0 + (p1 - p0) * f for f in (0.18, 0.36, 0.60, 0.80)]
        nrm = np.array([0.32, -0.95])
        cols = [WHITE_T, WHITE_T, REDT, REDT]
        sz = [130, 130, 190, 190]                                            # 第五棒：撕碎 1.6 倍、墨描边 + 字后暗晕，离开斩光（线下侧）
        self.la = LyrO([(c, *(pos[i] - nrm * 150), sz[i], 'serif_black', cols[i], ts[i]) for i, c in enumerate('那就撕碎')], 6129 / 30 - 0.12, seed=60,
                       outline=6, plate_amt=0.7, glow=0.25)

    def render(self, t):
        u = self.u(t)
        fr = E.sun_disc(self.sky.copy(), (1500, 500), 70, amt=1.0)
        ts = self.ts
        C, A = self.cur.layer(t, wind=1.1)
        C, A = R3.Scrolls.light(C, A, fr, 0.9, blur=1.2)
        if t >= ts:                                                          # 挂轴沿刀线断开：线下半截下坠，断口烧红
            C, A, em = R3.cut_layer(C, A, tuple(self.p0), tuple(self.p1), t - ts, fall=1.0, side=-1)
            fr = R3.comp(fr, C, A)
            fr = fr + (em * 1.6 + cv2.GaussianBlur(em, (0, 0), 8) * 1.5)[..., None] * np.array([1.0, 0.5, 0.15], np.float32)
        else:
            fr = R3.comp(fr, C, A)
        pose_mb = (60, -30) if t < ts + 0.05 else (0, 0)
        fr, info = put(fr, t, 'S118/xslash', (900 - 40 * u, 1060), h=820, rim=GOLDW, rim_amt=2.8, wind=10, mblur=pose_mb)
        if t >= ts - 0.03:
            q = t - ts
            c = (900, 560)
            fr = RS.fx_arc(fr, c, 760, 30, 120, min(1, (q + 0.03) / 0.07), max(0, 1 - q / 0.35), w=16, col=(1.0, 0.95, 0.85), edge=(0.85, 0.5, 0.15), squash=0.55)
            if q < 0.1: fr = fr + (0.35 * (1 - q / 0.1))
        return bloom(fr, 0.8, 0.45)

    def text(self, fr, t):
        tb = CT(51, 3) + 0.2                                                  # 第五棒：「碎」完整清晰停留 6 帧后才被斩开
        if t < tb: return self.la.draw(fr, t)
        # 「碎」：沿刀线把整句一分为二，上半往左上、下半往右下错开
        q = eout((t - tb) / 0.25)
        d = (self.p1 - self.p0) / np.linalg.norm(self.p1 - self.p0)
        F1 = self.la.draw(fr.copy(), t, dx=-d[0] * 50 * q - 10 * q, dy=-d[1] * 50 * q - 30 * q)
        F2 = self.la.draw(fr.copy(), t, dx=d[0] * 50 * q + 10 * q, dy=d[1] * 50 * q + 30 * q)
        yy, xx = E.grid()
        side = ((xx - self.p0[0]) * d[1] - (yy - self.p0[1]) * d[0] - 150 > 0)[..., None]
        out = np.where(side, F2, F1)
        g = np.exp(-(((xx - self.p0[0]) * d[1] - (yy - self.p0[1]) * d[0] - 150) / 3) ** 2) * (1 - q * 0.8)
        return out + g[..., None] * GOLDW * 1.2


_TB = {}
def _tex_blade(h, w):
    if (h, w) not in _TB:
        n = K.fbm(h, w, 1195, base=40, octaves=3).astype(np.float32)
        _TB[(h, w)] = cv2.GaussianBlur(n, (0, 0), sigmaX=8, sigmaY=0.6)        # 拉丝
    return _TB[(h, w)]


class E10(Shot):   # S119（第三棒重做）碎纸扑面：被斩碎的律令纸片 + 金箔，有厚度、3D 翻转、焦边余烬，前景大片强虚化擦镜；
    #  墨黑底、残存一点暗红火光（次色调），不再用日前黑剪影；「它 / 自己」大字描边落在纸片之间
    def __init__(self):
        n = K.fbm(H // 2, W // 2, 1190, base=4, octaves=5)
        yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
        glow = np.exp(-(((xx - 480) / 420) ** 2 + ((yy - 300) / 260) ** 2))
        bg = (0.015 + 0.04 * n)[..., None] * np.array([1.0, 0.85, 0.75], np.float32) + glow[..., None] * np.array([0.45, 0.12, 0.04], np.float32) * (0.6 + 0.5 * n[..., None])
        self.bg = cv2.resize(bg.astype(np.float32), (W, H))
        self.sh = R3.Shreds(119, n=70, gold=0.3, size=(60, 200), spread=(1500, 700), zr=(0.5, 3.4))
        self.l = LyrO([('它', 520, 430, 240, 'serif_black', GOLD_T, CT(51, 4)), ('自', 1320, 470, 190, 'serif_black', GOLD_T, CT(51, 5)),
                       ('己', 1520, 470, 190, 'serif_black', GOLD_T, CT(51, 6))], CT(51, 7) - 0.12, seed=70, glow=0.4, outline=4)   # 第八棒：「自」「己」同一水平线并排（不再上下错开）

    def render(self, t):
        fr = self.bg.copy()
        q = (t - self.t0) * 0.45 + 0.6                                          # 慢放
        fr = self.sh.draw(fr, q, light=(-0.5, -0.4, -0.75), dof=(2.5, 14.0), zfocus=1.3, emb=1.2, paper=(1.0, 0.84, 0.62), znear=0.55)
        fr = E.dust_motes(fr, t, 1191, n=80, amt=0.8, drift=(30, -80), col=(1.0, 0.55, 0.25), size=(1, 4))
        fr = self.fg_blade(fr, t)
        return bloom(fr, 0.8, 0.5)

    def fg_blade(self, fr, t):
        """第五棒：前景三层补主体 —— 他斩完收住的刀身从左下斜入画（强虚化、刃口一道暗红反光），碎纸是中景、红底是远景。"""
        u = self.u(t)
        yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
        ang = math.radians(12); c, s_ = math.cos(ang), math.sin(ang)
        ox, oy = -80 + 40 * u, 488 - 8 * u                                  # 刀脊参考点（半分辨率）
        a = (xx - ox) * c - (yy - oy) * s_; b = (xx - ox) * s_ + (yy - oy) * c   # a 沿刀身，b 垂直刀身
        L = 780 + 30 * u
        tip = np.clip((L - a) / 70, 0, 1)                                       # 刀尖收窄
        w = 30 * tip
        body = np.clip((w - np.abs(b)) / 2, 0, 1) * (a > -200) * (a < L)
        edge = np.exp(-((b + w * 0.92) / 2.0) ** 2) * (a > 0) * (a < L) * tip
        n = _tex_blade(h=H // 2, w=W // 2)
        steel = (0.03 + 0.05 * n)[..., None] * np.array([1.0, 0.9, 0.85], np.float32)
        col = steel + edge[..., None] * np.array([1.0, 0.42, 0.14], np.float32) * 2.4
        body = cv2.GaussianBlur(body, (0, 0), 6); col = cv2.GaussianBlur(col, (0, 0), 6)
        body = cv2.resize(body, (W, H)); col = cv2.resize(col, (W, H))
        return fr * (1 - body[..., None]) + col * body[..., None]

    def text(self, fr, t):
        return self.l.draw(fr, t)


class E11(Shot):   # S120a 低机位 MS：刀插大地，尘环冲击；巨字「定」
    def __init__(self):
        self.sky = E.dawn_sky(1200, horizon=0.80, sun=None, mid=(0.36, 0.25, 0.14), hor=(0.85, 0.58, 0.32), cloud=0.6)   # 第七棒：去身后日轮，光源在画外右
        n = K.fbm(H // 2, W // 2, 1201, base=8, octaves=6)
        yy = np.linspace(0, 1, H // 2, dtype=np.float32)[:, None]
        g = (0.04 + 0.10 * n) * (0.6 + 0.8 * yy)
        self.ground = cv2.resize((g[..., None] * np.array([1.0, 0.82, 0.62], np.float32)).astype(np.float32), (W, H))
        self.l1 = Lyr([('定', 430, 520, 440, 'serif_black', REDT, CT(51, 7))], CT(51, 9) + 0.25, seed=80)
        self.l2 = Lyr([('规', 430, 820, 72, 'serif_sb', GOLD_T, CT(51, 8))], CT(51, 9) + 0.25, seed=81)

    def render(self, t):
        u = self.u(t)
        fr = self.sky.copy()
        hy = 820
        m = sstep(hy - 4, hy + 4, np.arange(H, dtype=np.float32))[:, None, None]
        fr = fr * (1 - m) + self.ground * m
        yy0, xx0 = E.grid()
        fr = fr + (np.exp(-(((xx0 - 2150) / 700) ** 2 + ((yy0 - 640) / 380) ** 2)) * 0.6)[..., None] * np.array([1.0, 0.66, 0.34], np.float32)   # 画外右侧低位晨光晕
        fr = fx2.god_rays(fr, (2150, 600), strength=0.5, length=1.0, t=t, src_r=200)
        z, info = put(np.zeros((H, W, 3), np.float32), t, 'S120/plant', (1180, 1010), h=860, rim=GOLDW, rim_amt=2.6, rim_dir=(0.8, -0.3), wind=8)
        C, A = sprite_clean(z, info['A'], erode=2, rim_col=(1.0, 0.66, 0.32), rim_amt=2.6, rim_dir=(0.95, -0.2), cool_amt=0.15)
        C = C * 0.68                                                      # 第六棒：正面压暗（背后低位日光逆光），右侧暖轮廓光与日同向
        yy, xx = E.grid()
        cs = np.exp(-(((xx - 1150) / 330) ** 2 + ((yy - 1000) / 70) ** 2)) + 0.6 * np.exp(-(((xx - 1080) / 260) ** 2 + ((yy - 1060) / 90) ** 2))   # 接触阴影朝镜头拖出
        fr = fr * (1 - 0.7 * np.clip(cs, 0, 1)[..., None])
        fr = fr * (1 - A[..., None]) + C * A[..., None]
        q = t - self.t0
        c = (1180, 1000)
        r = 60 + 900 * eout(q / 0.7)
        yy, xx = E.grid()
        ring = np.exp(-((np.hypot(xx - c[0], (yy - c[1]) * 4) - r) / 30) ** 2) * (1 - c01(q / 0.8))
        fr = fr + ring[..., None] * np.array([0.9, 0.7, 0.45], np.float32) * 0.5
        fr = RS.fx_sparks(fr, t, self.t0, c, 1202, n=70, spd=800, dirv=(0, -1), spread=1.3, amt=1.0)
        fr = E.dust_motes(fr, t, 1203, n=60, amt=0.4, drift=(80, -20))
        return bloom(fr, 0.8, 0.4)

    def text(self, fr, t): return self.l2.draw(self.l1.draw(fr, t), t)   # [r4-DE#46] 该镜（E11「定」）已在 NO_TXT 静音


class E12(Shot):   # S120b ELS 正俯拍（第三棒返工）：大地即印面，「鬼屠」朱印盖下（摇臂升）；人物立在印旁（不压字），
    #  精灵只裁人（去掉插地刀土堆那团圆形物），按地面光调色 + 接触阴影 + 晨光长影
    KEY = 'E_r2/top_down|crop=0,0,0.56,1'

    def __init__(self):
        n = K.fbm(H, W, 1210, base=6, octaves=6)
        cr = K.fbm(H, W, 1211, base=22, octaves=3)
        crack = np.clip(1 - np.abs(cr - 0.5) * 40, 0, 1)
        pb = K.fbm(H // 2, W // 2, 1212, base=220, octaves=2)
        peb = cv2.resize(np.clip((pb - 0.6) * 5, 0, 1), (W, H))
        g = 0.10 + 0.16 * n - crack * 0.06 + peb * 0.05
        self.ground = (g[..., None] * np.array([1.0, 0.80, 0.58], np.float32)).astype(np.float32)
        self.face = PR.seal_face('鬼屠', 640, style='bai', wear=0.25, seed=12)
        self.cap = Sub('自己定规章', [CT(51, 5), CT(51, 6), CT(51, 7), CT(51, 8), CT(51, 9)], 'center', CT(52, 0) - 0.15, red='自己', seed=90)

    def render(self, t):
        u = self.u(t)
        fr = self.ground.copy()
        yy, xx = E.grid()
        fr = fr * (0.55 + 0.6 * np.exp(-((xx - 1300) ** 2 + (yy - 200) ** 2) / (2 * 700 ** 2)))[..., None]   # 晨光斜照
        p = (t - (CT(51, 9) - 0.18)) / 0.7
        c = (820, 500)
        if p > 0: fr = PR.stamp_imprint(fr, self.face, c[0], c[1], 640, min(1, p), angle=-4)
        # 第六棒：插在印心的刀（正俯拍：只见圆镡、缠绳刀柄与红穗，晨光把刀身影子长长拖向左下）
        bs = np.zeros((H, W), np.float32)
        cv2.line(bs, c, (int(c[0] - 34 * 13), int(c[1] + 26 * 13)), 1.0, 14, cv2.LINE_AA)
        fr = fr * (1 - 0.55 * cv2.GaussianBlur(bs, (0, 0), 4)[..., None])
        fr = np.ascontiguousarray(fr, np.float32)
        # 第七棒：俯角 75°——刀柄朝镜头斜伸出（缠绳菱纹 + 柄头），镡椭圆加一圈金色受光边，红穗绳甩出印外
        hx, hy = c[0] + 46, c[1] + 168                                                   # 柄头
        cv2.line(fr, (c[0] + 3, c[1] + 6), (hx + 3, hy + 6), (0.01, 0.01, 0.01), 40, cv2.LINE_AA)   # 柄影
        cv2.ellipse(fr, c, (54, 40), -4, 0, 360, (0.035, 0.03, 0.028), -1, cv2.LINE_AA)            # 镡
        cv2.ellipse(fr, c, (54, 40), -4, 0, 360, (0.95, 0.70, 0.36), 4, cv2.LINE_AA)
        cv2.ellipse(fr, c, (54, 40), -4, 190, 350, (1.0, 0.88, 0.55), 6, cv2.LINE_AA)
        cv2.line(fr, c, (hx, hy), (0.045, 0.035, 0.03), 34, cv2.LINE_AA)                     # 柄
        for k in range(1, 9):                                                            # 缠绳菱纹
            q = k / 9; px, py = c[0] + (hx - c[0]) * q, c[1] + (hy - c[1]) * q
            cv2.line(fr, (int(px - 15), int(py - 6)), (int(px + 15), int(py + 10)), (0.30, 0.06, 0.04), 4, cv2.LINE_AA)
            cv2.line(fr, (int(px - 15), int(py + 10)), (int(px + 15), int(py - 6)), (0.22, 0.05, 0.03), 4, cv2.LINE_AA)
        cv2.line(fr, (c[0] + 16, c[1] + 4), (hx + 16, hy + 4), (0.85, 0.62, 0.35), 2, cv2.LINE_AA)   # 柄右侧受光
        cv2.ellipse(fr, (hx, hy), (20, 14), 15, 0, 360, (0.55, 0.40, 0.20), -1, cv2.LINE_AA)        # 柄头（铜）
        cv2.ellipse(fr, (hx, hy), (20, 14), 15, 200, 340, (1.0, 0.85, 0.5), 3, cv2.LINE_AA)
        sw = 14 * math.sin(t * 3.1)
        pts = [(hx + 10, hy + 6)]
        for k in range(1, 9):                                                            # 红穗绳：甩出印外（右下），随风摆
            q = k / 8; pts.append((hx + 10 + 340 * q, hy + 6 + 120 * q + sw * q * q + 18 * math.sin(q * 5 + t * 4)))
        cv2.polylines(fr, [np.array(pts, np.int32)], False, (0.62, 0.07, 0.04), 5, cv2.LINE_AA)
        ex, ey = pts[-1]
        for k in range(9):                                                               # 穗头散开
            ang = 0.35 + 0.08 * (k - 4) + 0.05 * math.sin(t * 5 + k)
            cv2.line(fr, (int(ex), int(ey)), (int(ex + 70 * math.cos(ang)), int(ey + 70 * math.sin(ang))), (0.70 - 0.03 * k, 0.08, 0.05), 4, cv2.LINE_AA)
        cv2.circle(fr, (int(ex), int(ey)), 9, (0.85, 0.62, 0.30), -1, cv2.LINE_AA)
        at = (1470, 600)
        z, info = put(np.zeros((H, W, 3), np.float32), t, self.KEY, at, h=495, anc=(0.5, 0.5), rim=GOLDW, rim_amt=3.2, rim_dir=(0.7, -0.7),
                      grade=dict(expo=0.95, sat=0.6, tint=(1.1, 0.98, 0.84), lift=0.0, gamma=1.05), wind=4)
        A = info['A']
        z = np.clip(z + 0.9 * (z - cv2.GaussianBlur(z, (0, 0), 1.6)), 0, 4)          # 第八棒：俯拍人物 USM 锐化（不再偏糊）
        Sh = np.zeros_like(A)                                              # 晨光自右上 → 长影拖向左下（印面上也压影）
        for k in range(1, 9):
            M = np.float32([[1, 0, -34 * k], [0, 1, 26 * k]]); Sh = np.maximum(Sh, cv2.warpAffine(A, M, (W, H)) * (1 - 0.07 * k))
        Sh = cv2.GaussianBlur(Sh, (0, 0), 6)
        con = cv2.GaussianBlur(cv2.dilate(A, np.ones((9, 9), np.uint8)), (0, 0), 14)        # 接触阴影
        con2 = cv2.GaussianBlur(cv2.dilate(A, np.ones((5, 5), np.uint8)), (0, 0), 4)         # 第八棒：贴身紧接触影（压实落地感）
        fr = fr * (1 - 0.6 * Sh[..., None]) * (1 - 0.5 * con[..., None]) * (1 - 0.35 * con2[..., None])
        fr = fr * (1 - A[..., None]) + z * A[..., None]
        ring_ = np.clip(A - cv2.GaussianBlur(cv2.erode(A, np.ones((5, 5), np.uint8)), (0, 0), 4), 0, 1)       # 右上轮廓光
        gy, gx = np.gradient(cv2.GaussianBlur(A, (0, 0), 4)); dd = np.clip((-gx * 0.7 + gy * 0.7) / (np.hypot(gx, gy) + 1e-6), 0, 1)
        fr = fr + (ring_ * dd)[..., None] * np.array([1.0, 0.8, 0.5], np.float32) * 1.6
        if p > 0.3:
            q = (p - 0.3) / 0.7
            r = 330 + 600 * eout(q)
            ring = np.exp(-((np.hypot(xx - c[0], yy - c[1]) - r) / 40) ** 2) * (1 - q)
            fr = fr + ring[..., None] * np.array([0.8, 0.5, 0.3], np.float32) * 0.5
            fr = E.dust_motes(fr, t, 1213, n=60, amt=0.5 * (1 - q), drift=(40, 30), col=(0.9, 0.7, 0.5), size=(2, 5))
        return fr

    def text(self, fr, t): return self.cap.draw(fr, t)


class E13(Shot):   # S121 MCU 晨风中马尾与暗红腰带甩动，背景日光虚焦；巨字「血」
    def __init__(self):
        sky = E.dawn_sky(1210, horizon=0.75, sun=None, mid=(0.36, 0.25, 0.14), cloud=0.7)        # 第七棒：去身后日轮，只留画外右上光 + 光斑虚焦
        yy, xx = E.grid()
        sky = sky + (np.exp(-(((xx - 2100) / 900) ** 2 + ((yy + 80) / 600) ** 2)) * 0.7)[..., None] * np.array([1.0, 0.72, 0.4], np.float32)
        self.bg = cv2.GaussianBlur(sky, (0, 0), 18)
        r = np.random.default_rng(121)
        self.bok = [(r.uniform(900, 1900), r.uniform(150, 900), r.uniform(25, 70), r.uniform(0.2, 0.6)) for _ in range(18)]
        self.l2 = Sub('未冷', cts(52, [1, 2]), 'left', CT(52, 3) - 0.1, seed=101)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        L = np.zeros((H // 2, W // 2), np.float32)
        for (x, y, r, a) in self.bok:
            cv2.circle(L, (int((x - 40 * u) / 2), int(y / 2)), int(r / 2), a, -1, cv2.LINE_AA)
        fr = fr + cv2.resize(cv2.GaussianBlur(L, (0, 0), 2), (W, H))[..., None] * GOLDW * 0.6
        fr, info = put(fr, t, 'S121/wind_sash', (1180 + 30 * u, 1160), h=1080, rim=GOLDW, rim_amt=3.2, rim_dir=(0.8, -0.6), wind=14)
        fr = RS.fx_embers(fr, t, 1213, amt=0.8, n=50)
        return bloom(fr, 0.8, 0.4)

    def text(self, fr, t):
        if t < CT(52, 3) - 0.1: fr = R3.blood_drip(fr, '血', 470, 470, 470, t, CT(52, 0), seed=13)   # 「血」滴血笔触（与 E01 碑拓不同）
        return self.l2.draw(fr, t)


class E14(Shot):   # S122（第三棒重做）低机位仰拍：他从烟尘里朝镜头走来，人物偏右占 4/5 高；墨灰冷调烟幕（次色调），
    #  左前景大片焦纸强虚化擦过镜头（前景遮挡），火星斜飞。不再是「居中小剪影 + 日落」。
    def __init__(self):
        self.sky = E.dawn_sky(1220, horizon=0.95, top=(0.02, 0.022, 0.03), mid=(0.12, 0.13, 0.16), hor=(0.42, 0.36, 0.32), cloud=0.9, sun=None)
        n = K.fbm(H // 2, W // 2, 1222, base=10, octaves=5)
        self.ground = cv2.resize(((0.03 + 0.06 * n)[..., None] * np.array([0.9, 0.85, 0.82], np.float32)).astype(np.float32), (W, H))
        self.smoke = K.fbm(H // 4, W // 2, 1224, base=4, octaves=5)
        self.sh = R3.Shreds(122, n=12, gold=0.0, size=(120, 240), spread=(380, 360), zr=(0.35, 1.0))

    def render(self, t):
        u = self.u(t)
        fr = self.sky.copy()
        hy = 905
        m = sstep(hy - 3, hy + 30, np.arange(H, dtype=np.float32))[:, None, None]
        fr = fr * (1 - m) + self.ground * m
        sm = cv2.resize(R3.slide(self.smoke, -40 * (t - self.t0)), (W, H))
        fr = fr + (np.clip(sm - 0.4, 0, 1) * 0.5)[..., None] * np.array([0.55, 0.55, 0.6], np.float32) * sstep(200, 900, np.arange(H, dtype=np.float32))[:, None, None]
        yy, xx = E.grid()
        fr = fr + (np.exp(-(((xx - 1700) / 500) ** 2 + ((yy - 800) / 260) ** 2)) * 0.35)[..., None] * np.array([1.0, 0.45, 0.15], np.float32)  # 右后方余火
        bob = 6 * abs(math.sin(t * 5.5))
        fr, info = put(fr, t, 'E_r4/low_stride', (1180, 1210 - bob + 40 * u), h=960 * (1 + 0.06 * u), rim=(1.0, 0.62, 0.32), rim_amt=3.2,
                       rim_dir=(0.8, -0.3), grade=dict(expo=0.84, sat=0.5, tint=(0.95, 0.97, 1.03), lift=0.0, gamma=1.1), wind=12)
        fr = RS.fx_embers(fr, t, 1223, amt=0.9, n=70)
        fr = self.sh.draw(fr, (t - self.t0) * 0.6 + 0.3, c=(420, 620), dof=(4.0, 18.0), zfocus=2.5, emb=0.8, paper=(0.55, 0.45, 0.36), amt=0.95)
        return bloom(fr, 0.8, 0.45)


L_GU = None
def lyr_gu():
    global L_GU
    if L_GU is None:
        L_GU = Sub('骨未凉', [CT(52, 3), CT(52, 4), min(CT(52, 5), 209.68)], 'left', CT(53, 0) - 0.15, red='骨', seed=110)   # 第六棒：三字在 E14T 内出完（凉 提前 0.3s）
    return L_GU


class E14T(E14):
    def text(self, fr, t):                                               # 第七棒：「骨未凉」在 E15 入点前 3 帧内淡出，不挂到斩轴爆点上
        out = lyr_gu().draw(fr, t)
        a = c01((6295 / 30 - 1 / 60 - t) / 0.1)
        return fr + (out - fr) * a


class E15(Shot):   # S122b ECU 刀尖拖过焦土，划出一道朱金火线（他自己画的线）；刀尖由精灵 alpha 标定，火线头 = 刀尖
    KEY = 'S122/walk_toward|crop=0.26,0.62,0.40,0.92'

    def __init__(self):
        n = K.fbm(H // 2, W // 2, 1230, base=12, octaves=6)
        cr = K.fbm(H // 2, W // 2, 1231, base=30, octaves=3)
        g = 0.05 + 0.13 * n - np.clip(1 - np.abs(cr - 0.5) * 30, 0, 1) * 0.04
        yy = np.linspace(0, 1, H // 2, dtype=np.float32)[:, None]
        g = g * (0.5 + 0.9 * yy)
        self.ground = cv2.resize((g[..., None] * np.array([1.0, 0.8, 0.6], np.float32)).astype(np.float32), (W, H))
        pb = K.fbm(H // 2, W // 2, 1232, base=200, octaves=2)                       # 碎石/焦土颗粒高光
        self.peb = cv2.resize(np.clip((pb - 0.62) * 6, 0, 1), (W, H))
        _, info = put(np.zeros((H, W, 3), np.float32), 0.0, self.KEY, (960, 540), h=760, anc=(0.06, 0.96), rot=62, wind=0)
        ys, xs = np.where(info['A'] > 0.4)
        k = np.argmax(ys)                                                          # 最低点 = 刀尖
        self.off = (float(xs[k]) - 960, float(ys[k]) - 540)
        # 爆点：刀尖拖过时斩断一幅「天理」律令轴（第三棒新增：砍中东西）
        self.scr = R3.Scrolls(150, 1, (1180, 1180), 100, (760, 760), (250, 250), big=['天理'], tone=(0.92, 0.86, 0.72))
        self.scr.items[0]['amp'] = 0.3
        it = self.scr.items[0]; it['img'], it['a'] = R8.wood_tablet(it['a'].shape)   # 第八棒：挂轴（第三幅）→ 竖挂木律令牌「天理」阴刻填金（去重：挂轴只剩 E06/E09）
        us = np.linspace(0, 1, 400); xs_ = -100 + 1900 * np.array([eio(0.3 + v * 0.7) for v in us])
        self.tcut = 209.83 + float(us[np.argmax(xs_ >= 1180)]) * (210.33 - 209.83)

    @staticmethod
    def ly(x): return 640 + (x - 960) * 0.03

    def render(self, t):
        u = self.u(t)
        fr = self.ground.copy()
        yy, xx = E.grid()
        x = -100 + 1900 * eio(0.3 + u * 0.7)
        tip = (x, self.ly(x))
        lit = np.exp(-((xx - x) ** 2 + ((yy - tip[1]) * 2.2) ** 2) / (2 * 260 ** 2))       # 火线照亮刀尖周围焦土
        fr = fr * (0.7 + 0.6 * np.exp(-((yy - 150) / 500) ** 2))[..., None] + (self.peb * lit)[..., None] * np.array([1.0, 0.55, 0.25], np.float32) * 0.22
        fr = fr + lit[..., None] * np.array([0.35, 0.12, 0.04], np.float32)
        ly = self.ly(xx)
        on = 1 - sstep(x - 40, x, xx)
        cool = np.exp(-np.maximum(x - xx, 0) / 700)                                     # 远处冷却成暗红
        line = np.exp(-((yy - ly) / 3.5) ** 2) * on
        glow = np.exp(-((yy - ly) / 24) ** 2) * on * cool
        fr = fr * (1 - 0.6 * np.exp(-((yy - ly) / 8) ** 2) * on)[..., None]
        hot = np.array([1.0, 0.85, 0.5], np.float32) * cool[..., None] + np.array([0.8, 0.12, 0.04], np.float32) * (1 - cool[..., None])
        fr = fr + (line * 1.6)[..., None] * hot + glow[..., None] * np.array([1.0, 0.35, 0.1], np.float32) * 0.9
        C, A = self.scr.layer(t, wind=1.0)
        C = C * (0.55 + 0.5 * lit[..., None]) + lit[..., None] * np.array([0.5, 0.2, 0.05], np.float32)
        q = t - self.tcut
        if q >= 0:
            p0 = (900.0, self.ly(900.0) - 60); p1 = (1460.0, self.ly(1460.0) + 30)
            C, A, em = R3.cut_layer(C, A, p0, p1, q, fall=1.3, side=-1)
            fr = R3.comp(fr, C, A)
            fr = fr + (em * 2.0 + cv2.GaussianBlur(em, (0, 0), 10) * 2.0)[..., None] * np.array([1.0, 0.5, 0.15], np.float32)
            if q < 2.5 / 30: fr = fr * 1.35 + np.array([0.35, 0.14, 0.04], np.float32) * (1 - q * 12)     # 2 帧冲击（橙闪，不发白）
            fr = RS.fx_sparks(fr, t, self.tcut, (1180, self.ly(1180)), 1501, n=90, spd=1300, dirv=(0.6, -0.8), spread=1.4, grav=1500, amt=1.4)
        else:
            fr = R3.comp(fr, C, A)
        fr, info = put(fr, t, self.KEY, (tip[0] - self.off[0], tip[1] - self.off[1]), h=760, anc=(0.06, 0.96), rot=62,
                       rim=(1.0, 0.6, 0.3), rim_amt=2.5, rim_dir=(-0.6, 0.8), wind=0)
        fr = RS.fx_sparks(fr, t, t - 0.3, tip, int(t * 30) % 50 + 1230, n=50, spd=700, dirv=(-1, -0.6), spread=0.8, grav=1200, amt=1.2)
        fr = E.dust_motes(fr, t, 1233, n=50, amt=0.5, drift=(-30, -60), col=(1.0, 0.55, 0.25), size=(1, 3))
        return bloom(fr, 0.75, 0.5)

    def text(self, fr, t): return fr                                   # 第七棒：爆点上不挂「骨未凉」


# ---- 对 / 错：竖分屏镜像（左金右墨 → 左墨右朱）
def half_field(seed, col, sun=None):
    sky = E.dawn_sky(seed, horizon=0.82, top=tuple(np.array(col) * 0.12), mid=tuple(np.array(col) * 0.5), hor=tuple(col), cloud=0.5, sun=sun)
    return sky


class E16(Shot):   # S123（第五棒改版式）CU 正面推近：整幅金色晨光，人物偏左占满画高，右侧被墨烟压暗，金色巨字「对」从烟里烧出（不再硬分屏）
    def __init__(self):
        self.gold = half_field(1230, (1.0, 0.80, 0.48), sun=(380, 640))
        n = cv2.resize(K.fbm(H // 2, W // 2, 1232, base=5, octaves=5), (W, H))
        xx = np.arange(W, dtype=np.float32)[None, :]
        self.wash = np.clip(sstep(900, 1350, xx + (n - 0.5) * 260), 0, 1).astype(np.float32)                 # 右侧墨烟（软边、有烟纹）
        self.ink = ((0.02 + 0.05 * n)[..., None] * np.array([1.0, 0.85, 0.7], np.float32)).astype(np.float32)
        self.l1 = LyrO([('对', 1450, 500, 470, 'serif_black', GOLD_T, CT(53, 0))], CT(53, 4) - 0.1, seed=120, glow=0.6, outline=4)
        self.l2 = Sub('就是对', cts(53, [1, 2, 3]), 'right', CT(53, 4) - 0.1, seed=121)

    def render(self, t):
        u = self.u(t)
        fr = fx2.god_rays(self.gold.copy(), (380, 640), strength=0.6, length=1.0, t=t)
        fr, info = put(fr, t, 'S123/front', (640 + 30 * u, 1330), h=1300 * (1 + 0.05 * u), rim=GOLDW, rim_amt=2.6, rim_dir=(-0.8, -0.6), grade=G_DAWN, wind=5)
        w = (self.wash * (0.85 + 0.15 * math.sin(t * 1.3)))[..., None]
        fr = fr * (1 - w) + self.ink * w
        return bloom(fr, 0.85, 0.4)

    def text(self, fr, t): return _mark(self.l2.draw(fr, t), t, CT(53, 0), 1450, 500, 470, GOLD_T, 'tick')   # [r4-DE#46] 「对」→ ✓（代码画，位置/大小与原字一致）


class E17(Shot):   # S124（第五棒改版式）MS 横向构图：整幅朱光，他在右侧中景回头冷视；左侧朱红巨字「错」，第二个「错」唱出时被一道衣袖暗影扫过、字翻转倒置
    def __init__(self):
        self.red = half_field(1240, (0.85, 0.22, 0.12), sun=(1500, 700))
        n = cv2.resize(K.fbm(H // 2, W // 2, 1242, base=5, octaves=5), (W, H))
        xx = np.arange(W, dtype=np.float32)[None, :]
        self.wash = np.clip(1 - sstep(700, 1150, xx + (n - 0.5) * 260), 0, 1).astype(np.float32)
        self.ink = ((0.02 + 0.05 * n)[..., None] * np.array([1.0, 0.8, 0.7], np.float32)).astype(np.float32)
        self.l1 = LyrO([('错', 480, 500, 470, 'serif_black', REDT, CT(53, 4))], CT(53, 8) - 0.1, seed=130, glow=0.5, outline=4)
        self.l2 = Sub('就是错', cts(53, [5, 6, 7]), 'center', CT(53, 8) - 0.1, seed=131)
        self.tf = CT(53, 7)

    def render(self, t):
        u = self.u(t)
        fr = self.red.copy()
        fr, info = put(fr, t, 'S124/over_shoulder', (1400 - 50 * u, 1060), h=760, rim=(1.0, 0.45, 0.3), rim_amt=2.6,
                       grade=dict(expo=0.8, sat=0.6, tint=(1.08, 0.93, 0.88), lift=0.0, gamma=1.12), wind=5)
        w = (self.wash * (0.85 + 0.15 * math.sin(t * 1.1)))[..., None]
        return bloom(fr * (1 - w) + self.ink * w, 0.85, 0.4)

    def text(self, fr, t):
        F = _mark(fr.copy(), t, CT(53, 4), 480, 500, 470, REDT, 'cross', rot=4.0)   # [r4-DE#46] 「错」→ ✗（代码画；下面那套「衣袖扫过 → 翻转」动效保留）
        q = c01((t - self.tf) / 0.14)
        if q > 0:                                                            # 衣袖扫过 → 字横向翻转倒置
            sx = math.cos(math.pi * eio(q))
            y0, y1, x0, x1 = 160, 860, 120, 840
            src = F[y0:y1, x0:x1]; dst = fr[y0:y1, x0:x1].copy()
            cx = (x1 - x0) / 2
            M = np.float32([[sx if abs(sx) > 0.02 else 0.02, 0, cx * (1 - sx)], [0, 1, 0]])
            M[0, 1] = 0.0
            dst = cv2.warpAffine(src, M, (x1 - x0, y1 - y0), dst=dst, borderMode=cv2.BORDER_TRANSPARENT)
            F = F.copy(); F[y0:y1, x0:x1] = dst
            if q < 1:
                xx = np.arange(W, dtype=np.float32)[None, :]
                bx = -200 + 1300 * q
                sl = np.exp(-((xx - bx) / 140) ** 2)                          # 袖影（暗红带、强横向模糊）
                F = F * (1 - 0.85 * sl[..., None]) + sl[..., None] * np.array([0.08, 0.01, 0.01], np.float32)
        return self.l2.draw(F, t)


class E18(Shot):   # S124b 对/错 同框：两半同时在画，中缝锯齿裂开、金光喷出（下一镜碎裂）
    def __init__(self):
        self.a = E16(); self.b = E17()
        self.a.t0, self.a.t1 = 210.33, 211.27; self.b.t0, self.b.t1 = 211.27, 212.10
        r = np.random.default_rng(124)
        ys = np.linspace(BAR, H - BAR, 14); self.zz = np.stack([960 + r.normal(0, 26, 14), ys], 1)

    def render(self, t):
        u = self.u(t)
        if not hasattr(self, 'AB'):   # 两半是定格（各取上一镜字落定的一帧），只算一次
            self.AB = (self.a.l1.draw(self.a.render(211.05), 211.05), self.b.l1.draw(self.b.render(211.85), 211.85))   # 第五棒：只取大字（副句不带进分屏，避免半句出画）
        A, B = self.AB                                                # 第五棒：左 =「对」（E16 右半），右 =「错」（E17 左半），中缝留给金色「何」
        o = int(20 + 20 * eout(u))                                    # 第六棒：两张字卡沿熔岩裂缝向外错位
        fr = np.concatenate([A[:, 960 - o:1920 - o], B[:, o:960 + o]], 1)
        fr, _ = R6.lava_crack(fr, 960, t, seed=18, width=40 + 34 * eout(u))        # 熔岩裂缝：有厚度、边缘发红、喷碎屑（取代折线）
        return fr

    def text(self, fr, t): return fr                                  # 第六棒：「何」移到 E19 唱（本镜只留 对｜错）


class E19(Shot):   # S125 CU 直视镜头；金匾碎片在他周围漂浮；「何须伪装」灰飞
    def __init__(self):
        sky = E.dawn_sky(1250, horizon=0.9, mid=(0.30, 0.20, 0.11), hor=(0.9, 0.66, 0.36), cloud=0.6, sun=(1500, 900))
        self.bg = cv2.GaussianBlur(sky, (0, 0), 10)
        self.chips = R3.Shreds(125, n=46, gold=0.85, size=(14, 46), spread=(1100, 520), zr=(0.6, 2.6))   # 碎金匾箔片（有厚度、翻转、高光）
        self.l = Sub('何须伪装', cts(53, [8, 9, 10, 11]), 'right', CT(53, 11) + 0.25, red='伪装', seed=140)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        _bg = fr.copy()  # [r4-props] 精灵合成前的背景（同坐标），供脸区真孔取样
        fr, info = put(fr, t, 'E_r5/stare_cu', (960, 1010), h=1000 * (1 + 0.06 * u), rim=GOLDW, rim_amt=2.4, rim_dir=(0.8, -0.6), wind=6,
                       grade=dict(expo=0.9, sat=0.6, tint=(1.06, 0.98, 0.88), lift=0.0, gamma=1.08))   # 第五棒：换同参考脸新生 CU（窄下颌，与 E13/E16/E21 统一）

        fr = PD.silhouette_void_lyric(fr, info.get('A'), '伪装', (1000, 640, 1400, 880), phase=t, rise=0.6, feather=11.0, bore_out=12.0, bore_edge=3.5, hole_damp=0.18, bg=_bg, hole_style='black')  # [r4-props]
        fr = self.chips.draw(fr, (t - self.t0) * 0.5 + 0.2, to_cam=0.3, light=(0.6, -0.5, -0.6), dof=(3.0, 10.0), zfocus=1.4, emb=0.3)
        return bloom(fr, 0.8, 0.4)

    def text(self, fr, t): return self.l.draw(fr, t)


class E20(Shot):   # S126 ELS（第六棒重做，去和副歌一 S042「居中满月 + 中心巨字」撞构图）：低地平线，日轮只露上缘、偏右 1/3 从地平线下顶出；
    #  墨色巨字「天」大于半屏、偏左，逆着日光成剪影，光束从笔画缝里透出；「天」自下而上熔化、坍塌（熔滴下坠）。入转场 = 横向光线扫入（贴地平线）
    HZ = 770

    def __init__(self):
        self.tex = K.fbm(H // 2, W // 2, 1260, base=24, octaves=5)
        self.sky = E.dawn_sky(1262, horizon=self.HZ / H, mid=(0.42, 0.27, 0.13), hor=(1.0, 0.68, 0.32), cloud=0.75)
        self.l = Sub('不', [CT(54, 1)], 'right', CT(54, 2) + 0.1, seed=150)
        self.tt = CT(54, 0)
        r = np.random.default_rng(126)
        self.land = (cv2.resize(K.fbm(H // 4, W // 4, 1263, base=8, octaves=4), (W, H)) * 0.05).astype(np.float32)

    def render(self, t):
        u = self.u(t)
        fr = self.sky.copy()
        R = 430; c = (1290, self.HZ + R * (0.80 - 0.22 * eio(u)))          # 日从地平线下缓缓顶出
        yy, xx = E.grid()
        d = np.hypot(xx - c[0], yy - c[1])
        disc = np.clip((R - d) / 2.5, 0, 1)
        k = cv2.resize(self.tex, (W, H)); k = R3.slide(k, 30 * (t - self.t0))
        limb = np.clip(1 - (d / R) ** 2, 0, 1) ** 0.35
        surf = (0.8 + 0.45 * k) * limb
        col = np.stack([surf * 1.3, surf * 0.98, surf * 0.6], -1)
        fr = fr * (1 - disc[..., None]) + col * disc[..., None]
        halo = np.exp(-np.maximum(d - R, 0) / 190) * (d > R)
        fr = fr + halo[..., None] * GOLD * 1.0
        # 天：墨色剪影巨字（偏左、大于半屏高）→ 熔化坍塌
        e = c01((t - (self.tt - 0.2)) / 0.2)
        A = np.zeros((H, W), np.float32)
        if e > 0 and not glyph_off('E20'):                    # [r4-DE#46] 去「天」墨色巨字（保留光束与日轮）
            a = T.glyph('天', 'serif_black', 640, False).copy()
            g = a.shape[0]
            q = c01((t - (self.tt + 0.22)) / 0.75)
            if q > 0:
                ys, xs = np.mgrid[0:g, 0:g].astype(np.float32)
                wob = np.sin(ys / 45 + t * 7) * 5 * q + np.sin(ys / 13 + t * 19) * 1.5 * q
                drip = ((np.sin(xs / 31) * 0.5 + 0.5) ** 4 * 140 * q) * (ys / g) ** 2 + 40 * q * q      # 下半先软塌，上半横画保持平直
                a = cv2.remap(a, xs + wob, ys - drip, cv2.INTER_LINEAR)
                nz = E._nz(g, 7)
                a = a * np.clip(((ys / g) * -0.7 + 0.7 + nz * 0.3 - q * 1.15 + 0.35) * 6, 0, 1)
            L = T.Layer(); L.paste(a, 640, 470 + 40 * q if e > 0 and q > 0 else 470, (0.04, 0.02, 0.015), e)
            A = L.A
        fr = fx2.god_rays(fr, (c[0], self.HZ - 20), strength=0.85, length=1.1, t=t, src_r=260, occluder=A)   # 光束从笔画缝里透出
        if e > 0:
            ember = np.clip(cv2.GaussianBlur(A, (0, 0), 3) - A, 0, 1)
            fr = fr * (1 - A[..., None] * 0.94) + ember[..., None] * np.array([1.0, 0.42, 0.1], np.float32) * 1.6
        # 地面：暗土，地平线下压住日轮下半
        gnd = sstep(self.HZ - 3, self.HZ + 3, yy)
        land = (0.03 + self.land + 0.12 * np.exp(-((xx - c[0]) / 420) ** 2) * np.exp(-(yy - self.HZ) / 60)) [..., None] * np.array([1.0, 0.62, 0.35], np.float32)
        fr = fr * (1 - gnd[..., None]) + land * gnd[..., None]
        fr = fr + (np.exp(-((yy - self.HZ) / 6) ** 2) * np.exp(-((xx - c[0]) / 600) ** 2))[..., None] * np.array([1.0, 0.8, 0.5], np.float32) * 0.9
        return bloom(fr, 0.85, 0.55)

    def text(self, fr, t): return self.l.draw(fr, t)


class E21(Shot):   # S127 CU（第三棒重做）逆光侧脸：低调光，脸沉在暗部、只留晨光勾出的额-鼻-唇-下颌金边与发丝（不再给写实五官，避免和 E16/E19 对不上）；
    #  「判」「我」同一套材质：红色拓印 + 金描边（不再一红一白混用），在天空侧、离脸
    GR = dict(expo=0.72, sat=0.55, tint=(1.06, 0.97, 0.88), lift=0.0, gamma=1.15)   # 第四棒：新精灵与 E16 同脸，不再藏五官

    def __init__(self):
        sky = E.dawn_sky(1270, horizon=0.7, sun=None, mid=(0.38, 0.27, 0.15), cloud=0.6)          # 第七棒：去身后日轮 → 画外右上光源，只留斜入体积光
        yy, xx = E.grid()
        sky = sky + (np.exp(-(((xx - 2150) / 800) ** 2 + ((yy + 120) / 560) ** 2)) * 0.75)[..., None] * np.array([1.0, 0.74, 0.42], np.float32)
        self.bg = cv2.GaussianBlur(sky, (0, 0), 14)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        fr = fx2.god_rays(fr, (2150, -100), strength=0.7, length=1.0, t=t, src_r=240)
        fr, info = put(fr, t, 'E_r4/profile_up', (560 + 40 * u, 1170), h=1080, rim=(1.0, 0.86, 0.6), rim_amt=4.0, rim_dir=(1.0, -0.35),
                       grade=self.GR, wind=12)
        fr = E.dust_motes(fr, t, 1271, n=80, amt=0.5, drift=(-20, -30), depth=True)
        return bloom(fr, 0.75, 0.55)

    def text(self, fr, t):
        to = CT(54, 4) - 0.1
        return R3.rub_text(fr, [('判', 1230, 400, 230, CT(54, 2), to, t), ('我', 1560, 600, 330, CT(54, 3), to, t)], seed=21)


class E22(Shot):   # S128 LS 横刀于胸，太阳恰落在刀身正中（支点）——他自己成了秤；第六棒：「我」「来」= 两端秤盘，「量」= 刀心下垂的秤砣
    GR = dict(expo=0.55, sat=0.55, tint=(1.04, 0.97, 0.9), lift=0.0, gamma=1.2)

    def __init__(self):
        self.sky = E.dawn_sky(1280, horizon=0.86, mid=(0.42, 0.30, 0.16), cloud=0.6, sun=None)
        self.rd, self.ra = E.ridges(n=2, base=0.82, step=0.05, seed=128, amp=0.05, far=0.35, near=0.03)
        self.cal = None
        self.ts = [CT(54, 3), CT(54, 4), CT(54, 5)]      # [r4-DE#47] 底版路径不跑 _calib，这里先备好时标

    def _calib(self, t, dy):
        """刀身行：精灵 alpha 在 y∈[200,620] 内横向最宽的一行；刀身水平范围取该行 alpha>0.5 的首末列。"""
        z, info = put(np.zeros((H, W, 3), np.float32), t, 'S128/blade_level', (960, 1060 + dy), h=900, grade=self.GR, wind=0)
        A = info['A'] > 0.5
        wid = A[200:620].sum(1); r = 200 + int(np.argmax(wid))
        xs = np.where(A[r])[0]
        self.cal = dict(y=r - dy, x0=int(xs[0]), x1=int(xs[-1]))
        ch = '我来量'; ts = [CT(54, 3), CT(54, 4), CT(54, 5)]
        # 第六棒：去和副歌一 S044「刀身下一行刻字」撞概念 —— 横刀成秤：「我」「来」是刀两端吊着的秤盘、「量」是刀心（日 = 支点）下垂的秤砣
        y = self.cal['y']; x0, x1 = self.cal['x0'], self.cal['x1']
        self.pan = [x0 + 0.13 * (x1 - x0), x1 - 0.13 * (x1 - x0)]
        self.chx = [self.pan[0], self.pan[1], 960]
        PY = y + 205; WY = y + 330
        self.eng = LyrO([('我', self.pan[0], PY - 62, 120, 'serif_black', GOLD_T, ts[0]), ('来', self.pan[1], PY - 62, 120, 'serif_black', GOLD_T, ts[1]),
                         ('量', 960, WY, 150, 'serif_black', REDT, ts[2])],
                        CT(55, 0) - 0.1, seed=170, outline=5, glow=0.7, shadow=0.7, direction=(0.0, -1.0))
        self.PY, self.WY = PY, WY
        self.ts = ts                                                       # 底部重复副句去掉（刀上的字已成立）

    def render(self, t):
        u = self.u(t); dy = -20 * u
        # [r4-DE#47] 用户：3m37 主角用刀当天平 → 直接出图（代码画会漂移）。整帧替换成 e22_scale_crop，
        #   推镜 + 刃口金线高光 + 一点呼吸光都还在；原来的代码 rig（刀身/日轮/秤绳秤盘）只作兜底。
        pl = plate('e22_scale_crop')
        if pl is not None:
            z = 1.02 + 0.06 * eio(u)
            fr = K.cam(pl, z, -14 + 28 * u, dy)
            yy = np.arange(H, dtype=np.float32)[:, None]; xx = np.arange(W, dtype=np.float32)[None, :]
            kx = np.interp(t, [self.t0, self.ts[1], self.ts[2], self.t1], [300, 760, 960, 1500])
            sw = np.exp(-((xx - kx) / 90) ** 2) * np.exp(-((yy - (470 + dy)) / 26) ** 2)
            fr = fr + sw[..., None] * GOLDW * 0.55 + cv2.GaussianBlur(sw, (0, 0), 20)[..., None] * GOLDW * 0.35
            return bloom(fr, 0.82, 0.45)
        if self.cal is None: self._calib(self.t0, 0.0)
        by = self.cal['y'] + dy
        fr = self.sky.copy()
        z, info = put(np.zeros((H, W, 3), np.float32), t, 'S128/blade_level', (960, 1060 + dy), h=900, rim=GOLDW, rim_amt=3.0, grade=self.GR, wind=6)
        sun = (960, by)                                                  # 日心 = 刀身中点
        fr = E.sun_disc(fr, sun, 130, amt=1.15)
        fr = fx2.god_rays(fr, sun, strength=1.0, length=1.0, t=t, occluder=info['A'])
        fr = E.place_layer(fr, self.rd, self.ra)
        a = info['A'][..., None]
        fr = fr * (1 - a) + z * a
        # 日光沿刃线溢出（刀身受光的一条金线）
        yy = np.arange(H, dtype=np.float32)[:, None]; xx = np.arange(W, dtype=np.float32)[None, :]
        span = sstep(self.cal['x0'] + 20, self.cal['x0'] + 120, xx) * (1 - sstep(self.cal['x1'] - 120, self.cal['x1'] - 10, xx))
        edge = np.exp(-((yy - (by - 9)) / 1.6) ** 2) * span * (0.5 + 0.5 * np.exp(-((xx - 960) / 260) ** 2))
        fr = fr + edge[..., None] * GOLDW * 1.4
        # 刀身高光自左扫到右：每个字落下的时刻扫到该字位置（刻痕被光点亮）
        kx = np.interp(t, [self.t0, self.ts[1], self.ts[2], self.t1], [self.cal['x0'], self.chx[1], self.chx[2], self.cal['x1'] + 60])
        sw = np.exp(-((xx - kx) / 70) ** 2) * np.exp(-((yy - (by - 6)) / 7) ** 2) * span
        fr = fr + sw[..., None] * GOLDW * 2.2 + cv2.GaussianBlur(sw, (0, 0), 14)[..., None] * GOLDW * 1.2
        self.by = by
        return bloom(fr, 0.8, 0.5)

    def text(self, fr, t):
        if plate('e22_scale_crop') is not None: return fr      # [r4-DE#47] 秤绳/秤盘已在天平的图里
        if not self.cal: return fr
        dy = getattr(self, 'by', self.cal['y']) - self.cal['y']
        y = self.cal['y'] + dy
        fr = np.ascontiguousarray(fr, np.float32)
        for k in range(3):                                                 # 秤绳 / 秤盘 / 秤砣挂绳：随各自的字一起出现
            a = c01((t - (self.ts[k] - 0.2)) / 0.2)
            if a <= 0: continue
            cx = self.chx[k]
            if k < 2:
                py = self.PY + dy + 6 * math.sin((t - self.ts[k]) * 9) * math.exp(-(t - self.ts[k]) / 0.4) * (t > self.ts[k])
                ov = fr.copy()
                for sx in (-95, 0, 95):
                    cv2.line(ov, (int(cx), int(y + 4)), (int(cx + sx), int(py)), (0.55, 0.42, 0.25), 3, cv2.LINE_AA)
                cv2.ellipse(ov, (int(cx), int(py)), (118, 26), 0, 0, 180, (0.10, 0.07, 0.05), -1, cv2.LINE_AA)
                cv2.ellipse(ov, (int(cx), int(py)), (118, 26), 0, 0, 180, (1.0, 0.72, 0.36), 3, cv2.LINE_AA)
                cv2.line(ov, (int(cx - 118), int(py)), (int(cx + 118), int(py)), (1.0, 0.8, 0.45), 3, cv2.LINE_AA)
                fr = fr * (1 - a) + ov * a
            else:
                ov = fr.copy()
                cv2.line(ov, (960, int(y + 4)), (960, int(self.WY + dy - 95)), (0.75, 0.5, 0.28), 3, cv2.LINE_AA)
                fr = fr * (1 - a) + ov * a
        return self.eng.draw(fr, t, dy=dy)


class E23(Shot):   # S129 MCU 后撤蓄力，速度坡度推近（吸气）
    def __init__(self):
        n = K.fbm(H // 2, W // 2, 1290, base=4, octaves=5)
        self.bg = cv2.resize(((0.10 + 0.18 * n)[..., None] * np.array([1.0, 0.75, 0.45], np.float32)).astype(np.float32), (W, H))
        self.l = Sub('这一', cts(55, [0, 1]), 'left', CT(55, 2) - 0.08, seed=180)
        yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
        self.ang = np.arctan2(yy - 300, xx - 480); self.rad = np.hypot(xx - 480, yy - 300) / 540
        r = np.random.default_rng(129); self.ph = r.uniform(0, 6.28, 7); self.fq = r.integers(40, 160, 7)

    def zoom_lines(self, t, u):
        """径向速度线（以人物胸口为灭点），强度随速度坡度上升 → 吸气蓄力。"""
        v = np.zeros_like(self.ang)
        for p, f in zip(self.ph, self.fq): v += np.sin(self.ang * f + p + t * 0.7)
        v = np.clip((v / 3.2) - 0.55, 0, 1) ** 2 * sstep(0.25, 0.9, self.rad)
        L = cv2.resize(v, (W, H))[..., None]
        return L * np.array([1.0, 0.8, 0.5], np.float32) * (0.10 + 0.45 * ein(u, 2))

    def render(self, t):
        u = self.u(t)
        # [r4-DE#48] 用户：3m38 两镜应是同一张图 → E23/E24 共用 `s_e218_hilt_crop`（r1 生图，已裁掉烙字「刀」）。
        pl = plate('s_e218_hilt_crop')
        if pl is not None:
            fr = K.cam(pl, 1.00 + 0.05 * ein(u, 2), -10 + 20 * u, -8 * u)      # 速度坡度：慢慢推近 = 吸气蓄力
            return bloom(fr + self.zoom_lines(t, u) * 0.8, 0.8, 0.35)
        fr = self.bg.copy()
        fr = fr + self.zoom_lines(t, u)
        fr, info = put(fr, t, 'S129/coil', (1000, 1140), h=1080, rim=GOLDW, rim_amt=2.8, wind=12)
        return bloom(fr, 0.8, 0.35)

    def text(self, fr, t): return self.l.draw(fr, t)


class E24(Shot):   # S129b ECU 刃身满屏，寒光自柄扫到尖；巨字「刀」朱红
    def __init__(self):
        self.bg = E.dawn_sky(1291, horizon=0.5, top=(0.06, 0.05, 0.04), mid=(0.25, 0.18, 0.1), hor=(0.6, 0.42, 0.22), cloud=0.3)
        self.l1 = Lyr([('刀', 1440, 520, 440, 'serif_black', REDT, CT(55, 2))], CT(55, 6) - 0.05, seed=190)
        self.l2 = Sub('就是我', cts(55, [3, 4, 5]), 330, CT(55, 6) - 0.05, seed=191)

    def render(self, t):
        u = self.u(t)
        # [r4-DE#48] 与 E23 同一张图；这里推到刃身 = ECU（放大 + 旋转，寒光自柄扫到尖）
        pl = plate('s_e218_hilt_crop')
        if pl is not None:
            z = 1.55 + 0.10 * eio(u)
            c = (960 - 60 * u, 470)
            M = cv2.getRotationMatrix2D((W / 2, H / 2), -6.0, z)
            M[0, 2] += c[0] - W / 2; M[1, 2] += c[1] - H / 2
            fr = cv2.warpAffine(pl, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            sx = -300 + 2600 * eio(u)
            fr = E.flare_streak(fr, (sx, 420 + (sx - 960) * 0.18), amt=1.1, angle=10)
            return bloom(fr, 0.78, 0.5)
        fr = self.bg.copy()
        fr, info = put(fr, t, 'S129/coil|crop=0,0,0.46,0.42', (900 - 60 * u, 470), w=2300, anc=(0.5, 0.5), rot=-12, rim=GOLDW, rim_amt=3.0, wind=0, grade=G_HOT)
        sx = -300 + 2600 * eio(u)
        fr = E.flare_streak(fr, (sx, 420 + (sx - 960) * 0.18), amt=1.1, angle=10)
        return bloom(fr, 0.78, 0.5)

    def text(self, fr, t): return self.l2.draw(self.l1.draw(fr, t), t)


class E25(Shot):   # S130（第三棒重做）低机位终极横斩：墨黑红天（次色调），人物受刀光照亮、占满画面下 3/4；整个画面沿刀线裂开、金光喷涌
    def __init__(self):
        self.sky = E.dawn_sky(1300, horizon=0.92, top=(0.02, 0.012, 0.012), mid=(0.17, 0.05, 0.03), hor=(0.62, 0.20, 0.08), cloud=0.9, sun=None)
        n = K.fbm(H // 2, W // 2, 1302, base=10, octaves=5)
        self.ground = cv2.resize(((0.02 + 0.05 * n)[..., None] * np.array([1.0, 0.7, 0.6], np.float32)).astype(np.float32), (W, H))
        self.s1 = Sub('的', [CT(55, 6)], 190, CT(55, 8) - 0.12, seed=200, y=700)
        self.l = LyrO([('正', 450, 690, 300, 'serif_black', GOLD_T, CT(55, 7))], CT(55, 8) - 0.12, seed=201, glow=0.35, outline=6, plate_amt=0.55)   # 第七棒：下移出横斩光带 + 暗衬

    def render(self, t):
        u = self.u(t)
        fr = self.sky.copy()
        hy = 930
        m = sstep(hy - 2, hy + 20, np.arange(H, dtype=np.float32))[:, None, None]
        fr = fr * (1 - m) + self.ground * m
        ts = CT(55, 6)
        mb = (90, 0) if t < ts + 0.04 else (0, 0)
        fr, info = put(fr, t, 'S130/hslash', (930, 1200), h=1040, rim=(1.0, 0.7, 0.4), rim_amt=3.4, rim_dir=(-0.9, -0.3), wind=12, mblur=mb,
                       grade=dict(expo=1.15, sat=0.62, tint=(1.1, 0.95, 0.86), lift=0.02, gamma=1.0))
        self.y = by = info['tip'][1] if info['tip'] else 520
        q = t - ts
        if q > 0:
            e = eout(q / 0.25)
            gap = 70 * e * (1 - 0.3 * c01((q - 0.6) / 0.5))
            top = K.cam(fr, 1.0, oy=-gap / 2); bot = K.cam(fr, 1.0, oy=gap / 2)
            yy = np.arange(H, dtype=np.float32)[:, None, None]
            fr = np.where(yy < by, top, bot)
            # [r4-DE#49] 用户：劈开的光把主角挡住了 → ①光带收窄 ②压光（2.2→1.25）③用精灵 alpha 把光带从人物身上挖掉
            band = np.exp(-((yy[..., 0] - by) / max(2, gap * 0.42)) ** 2)
            subj = np.clip(info['A'], 0, 1)                                  # 人物精灵 alpha（H,W）
            msk = 1 - 0.92 * subj                                            # 人物身上不出光带，光从两侧喷
            band = band * msk
            fr = fr * (1 - band[..., None] * 0.85) + band[..., None] * GOLDW * 1.25
            glow = np.exp(-((yy[..., 0] - by) / (gap + 40)) ** 2) * msk
            fr = fr + glow[..., None] * GOLD * 0.5 * (1 + 2 * math.exp(-q / 0.12))
            coreL = np.exp(-((yy[..., 0] - by) / 2.2) ** 2) * (1 - 0.75 * subj)   # 切线上给一道细锐核心（也不盖人物）
            fr = fr + coreL[..., None] * GOLDW * 0.85
            if q < 0.08: fr = fr * 1.18 + np.array([0.3, 0.12, 0.04], np.float32) * (1 - q / 0.08)
            fr = RS.fx_sparks(fr, t, ts, (300, by), 1301, n=90, spd=1400, dirv=(1, -0.1), spread=0.35, grav=300, amt=1.2)
        fr = RS.fx_embers(fr, t, 1303, amt=0.7, n=50)
        return bloom(fr, 0.8, 0.6)

    def text(self, fr, t): return self.l.draw(self.s1.draw(fr, t), t)


class E26(Shot):   # S131（第三棒重做）一点透视：他划下的那道火线贴地一路延伸到地平线（纵深），朝阳正从线的尽头升起；
    #  画面里没有人（不再是日落剪影），「正道沧桑」大字描边升在天上
    def __init__(self):
        self.sky = E.dawn_sky(1310, horizon=0.55, mid=(0.45, 0.31, 0.17), hor=(1.0, 0.82, 0.5), cloud=0.8, sun=(960, 590))
        self.g = R3.Ground(261)
        self.l = LyrO(row('正道沧桑', [CT(55, 7), CT(55, 8), CT(55, 9), CT(55, 10)], 960, 250, size=170, gold='正道沧桑', track=0.22, font='serif_black'),
                      None, seed=210, glow=0.3, outline=7, shadow=0.95, plate_amt=0.45)      # 第六棒：四字全金 + 墨描边、上移离开地平线光带（亮天上对比度够）

    def render(self, t):
        u = self.u(t)
        hy = 600
        fr = self.sky.copy()
        sun = (960, hy + 90 - 170 * eout(u, 2))
        fr = E.sun_disc(fr, sun, 120, amt=1.2)
        fr = fx2.god_rays(fr, sun, strength=0.8, length=1.0, t=t)
        fr, z = self.g.render(fr, hy, f=900, camh=1.0, dz=-6 * u, line=1.0, fog=(1.0, 0.8, 0.5))
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        fr = fr + np.exp(-((yy - hy) / 2.0) ** 2) * GOLDW * 1.4 + np.exp(-((yy - hy) / 24) ** 2) * GOLD * 0.5
        fr = RS.fx_embers(fr, t, 1312, amt=0.6, n=40)
        return bloom(fr, 0.85, 0.5)

    def text(self, fr, t): return self.l.draw(fr, t, alpha=c01((t - (self.t0 + 0.20)) / 0.12))   # 第七棒：线形揭开完成后再淡入，不被揭开边/黑边切字


# ---- 高潮碎切（221.27–223.10，按鼓点 221.28 / 221.97 / 222.65 切）：眼 → 斩 → 匾碎，每镜 0.5–0.67s，取代原 1.83s 慢走
class E27a(Shot):   # 眼：S125 眼部 ECU（第二次用，换景别），墨黑红底，红色轮廓光，急推
    def render(self, t):
        u = self.u(t)
        fr = np.zeros((H, W, 3), np.float32) + np.array([0.03, 0.01, 0.01], np.float32)
        fr, info = put(fr, t, 'S125/stare|crop=0.30,0.31,0.70,0.51', (960, 540), w=2500 * (1 + 0.12 * eout(u)), anc=(0.5, 0.5),
                       rim=(1.0, 0.35, 0.2), rim_amt=2.5, rim_dir=(1.0, 0.0), wind=4,
                       grade=dict(expo=0.85, sat=0.55, tint=(1.12, 0.92, 0.86), lift=0.0, gamma=1.15))
        yy, xx = E.grid()
        fr = fr * (0.35 + 0.8 * np.exp(-((yy - 560) / 260) ** 2))[..., None]                      # 只留眼睛这条光带
        sx = 300 + 1400 * eio(u * 1.4)
        fr = E.flare_streak(fr, (sx, 560), amt=0.6, angle=0, length=0.9, col=(1.0, 0.55, 0.35))
        return bloom(fr, 0.8, 0.4)


class E27b(Shot):   # 斩：纯刀光——一道巨大的金白弧光自左上劈到右下，拖出燃烧的刀痕、火星四溅，暗底震屏（不用精灵）
    def render(self, t):
        u = self.u(t)
        fr = np.zeros((H, W, 3), np.float32) + np.array([0.03, 0.018, 0.015], np.float32)
        fr = fx2.light_beam(fr, (1500, 60), (800, 1000), 40, 500, t=t, strength=0.25, seed=27)
        pr = eout(c01(0.3 + u / 0.45), 4)
        yy, xx = E.grid()
        c = (2300, -900); R = 1900
        d = np.hypot(xx - c[0], yy - c[1])
        ang = np.arctan2(yy - c[1], xx - c[0])
        a0, a1 = math.radians(175), math.radians(175 - 70 * pr)
        on = ((ang <= a0) & (ang >= a1)).astype(np.float32)
        head = np.exp(-((ang - a1) / 0.05) ** 2)
        core = np.exp(-((d - R) / (4 + 10 * head)) ** 2) * on
        glow = np.exp(-((d - R) / 60) ** 2) * on
        trail = np.exp(-((d - R - 30) / 22) ** 2) * on * (0.6 + 0.4 * np.sin(ang * 90 + t * 40)) * math.exp(-u * 1.5)
        fr = fr + core[..., None] * np.array([1.0, 0.96, 0.88], np.float32) * 2.2 + glow[..., None] * GOLD * 0.9 * (1 - 0.5 * u) \
             + trail[..., None] * np.array([1.0, 0.35, 0.08], np.float32) * 1.4
        tipx = c[0] + R * math.cos(a1); tipy = c[1] + R * math.sin(a1)
        fr = RS.fx_sparks(fr, t, self.t0 + 0.03, (tipx, tipy), 2701, n=120, spd=1500, dirv=(0.5, 0.8), spread=1.2, grav=1400, amt=1.4)
        if 0 <= tipx <= W and 0 <= tipy <= H: fr = E.flare_streak(fr, (tipx, tipy), amt=1.0 * (1 - u), angle=-35, length=0.7)
        if u < 0.1: fr = fr * 1.2 + np.array([0.35, 0.16, 0.05], np.float32) * (1 - u / 0.1)
        fr = RS.fx_embers(fr, t, 2702, amt=0.8, n=60)
        # 第四棒：刀光不再无主 —— 他（低机位跨步精灵翻转、第二次用：墨黑剪影 + 朱金轮廓光）随刀光落地，刀尖正是弧光的尽头
        fr, info = put(fr, t, 'E_r4/low_stride|flip', (900 - 60 * pr, 1400 - 40 * pr), h=1300, rim=(1.0, 0.6, 0.28), rim_amt=9.0, rim_dir=(0.7, -0.6),   # 第六棒：放大 + 朱金轮廓光加倍
                       grade=dict(expo=0.30, sat=0.5, tint=(1.05, 0.9, 0.85), lift=0.0, gamma=1.3), wind=16, mblur=(int(30 * (1 - pr)), 0))
        return bloom(fr, 0.7, 0.7)


class E27c(Shot):   # 匾碎（第五棒重做，去和 E04 正面平拍撞构图）：低角度 3/4 透视仰拍，「天理昭彰」匾被一刀从中斩成两半，
    #  两半各自翻转下坠、断口烧红喷金，金箔碎片扑面；背景高窗一道斜光（延续 E04 的殿，但机位换到匾下侧前方）
    def __init__(self):
        self.pl = PR.Plaque('天理昭彰', seed=3)
        self.burst = R3.Shreds(271, n=60, gold=0.9, size=(30, 110), spread=(900, 360), zr=(0.6, 2.0))
        z = np.zeros((H, W, 3), np.float32)
        P = plaque_lit(self.pl, z, 0.0, 960, 540, 1500, [99] * 4, crack=0.25, dim=1.0)          # 第六棒：不再叠第二层发光字（与匾面刻字错位成重影）
        A = np.clip(P.max(-1) * 14, 0, 1)
        src = np.float32([[210, 270], [1710, 270], [1710, 810], [210, 810]])            # 匾的大致四角 → 低角度 3/4 透视（左近右远、仰视）
        dst = np.float32([[120, 330], [1500, 140], [1560, 560], [60, 900]])
        M = cv2.getPerspectiveTransform(src, dst)
        self.P = cv2.warpPerspective(P, M, (W, H)); self.A = cv2.warpPerspective(A, M, (W, H))
        self.cut = (np.array([888.0, 0.0]), np.array([919.0, 960.0]))                     # 第六棒：斩线 = 透视后「理｜昭」字缝（不再落在「理」上）

    def render(self, t):
        u = self.u(t)
        fr = np.zeros((H, W, 3), np.float32) + np.array([0.025, 0.018, 0.015], np.float32)
        fr = fx2.light_beam(fr, (1700, 60), (1100, 1000), 40, 420, t=t, strength=0.45, seed=271)
        p0, p1 = self.cut; d = (p1 - p0) / np.linalg.norm(p1 - p0)
        yy, xx = E.grid()
        side = ((xx - p0[0]) * d[1] - (yy - p0[1]) * d[0]) > 0                            # True = 右半
        q = eout(c01(u / 0.9), 2)
        fall = (q ** 1.6) * 260
        out = fr
        for s_, rot, dx in ((False, -9, -70), (True, 11, 90)):
            m = (side == s_).astype(np.float32)
            C = self.P * m[..., None]; Am = self.A * m
            cx, cy = (600, 520) if not s_ else (1250, 420)
            R = cv2.getRotationMatrix2D((cx, cy), rot * q, 1.0); R[0, 2] += dx * q; R[1, 2] += fall
            C = cv2.warpAffine(C, R, (W, H)); Am = cv2.warpAffine(Am, R, (W, H))
            # 第六棒：去掉下坠运动模糊（读成横向重影）
            sd = np.abs(((xx - p0[0]) * d[1] - (yy - p0[1]) * d[0]))                    # 断口烧红
            edge = np.exp(-(sd / 10) ** 2)
            edge = cv2.warpAffine(edge.astype(np.float32), R, (W, H)) * Am
            out = out * (1 - Am[..., None]) + C * Am[..., None] + edge[..., None] * np.array([1.0, 0.45, 0.12], np.float32) * 2.2
        sl = np.exp(-(((xx - p0[0]) * d[1] - (yy - p0[1]) * d[0]) / (6 + 40 * q)) ** 2) * (1 - q) * 1.4            # 刀线余光
        out = out + sl[..., None] * GOLDW
        out = self.burst.draw(out, 0.2 + u * 1.1, to_cam=1.3, light=(0.2, -0.5, -0.8), dof=(1.5, 10.0), zfocus=1.0, emb=0.2)
        out = RS.fx_embers(out, t, 2711, amt=0.7, n=50)
        return bloom(out, 0.75, 0.6)


class E28(Shot):   # S132b ECU 暗红腰带与马尾在逆光里翻飞（红绳母题收束）
    def __init__(self):
        sky = E.dawn_sky(1330, horizon=0.6, sun=None, mid=(0.42, 0.30, 0.17), cloud=0.9)           # 第七棒：去日轮 → 逆光云隙（左上画外光从云缝漏下）
        yy, xx = E.grid()
        sky = sky + (np.exp(-(((xx + 200) / 900) ** 2 + ((yy - 200) / 420) ** 2)) * 0.55)[..., None] * np.array([1.0, 0.74, 0.42], np.float32)
        self.bg = cv2.GaussianBlur(fx2.god_rays(sky, (-200, 150), strength=0.8, length=1.0, t=0.0, src_r=200), (0, 0), 10)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        z, info = put(np.zeros((H, W, 3), np.float32), t, 'S121/wind_sash|crop=0,0.22,0.45,1', (1000 - 70 * u, 600), w=2000, anc=(0.5, 0.5), rot=-6,
                      rim=GOLDW, rim_amt=3.5, wind=22, grade=G_DAWN)
        A = info['A']                                                     # 第六棒：取景放宽到马尾 + 腰带；腰带给编织纹 + 逆光透红边
        # 第七棒：马尾发丝在焦外（浅景深，焦点在腰带）→ 强虚化 + 横向风动模糊 + 逆光透金，不再读成黑枯枝
        dof = np.clip((560 - np.arange(H, dtype=np.float32)) / 160, 0, 1)[:, None] * (1 - cv2.GaussianBlur((z[..., 0] - 1.6 * z[..., 1] > 0.02).astype(np.float32), (0, 0), 6))
        kz = np.ones((1, 21), np.float32) / 21
        zb = cv2.GaussianBlur(cv2.filter2D(z, -1, kz), (0, 0), 5); Ab = cv2.GaussianBlur(cv2.filter2D(A, -1, kz), (0, 0), 5)
        z = z * (1 - dof[..., None]) + zb * dof[..., None]; A = A * (1 - dof) + Ab * dof
        edge_ = np.clip(Ab - cv2.GaussianBlur(Ab, (0, 0), 8), 0, 1) * dof
        z = z * (1 - 0.3 * dof[..., None]) + (edge_ * 1.6 + Ab * (1 - Ab) * dof * 0.8)[..., None] * np.array([1.0, 0.68, 0.36], np.float32)
        C = z / np.maximum(A, 1e-3)[..., None]
        red = np.clip((C[..., 0] - 1.6 * C[..., 1]) * 12, 0, 1) * (A > 0.3)
        red = cv2.GaussianBlur(red.astype(np.float32), (0, 0), 1.5)
        if not hasattr(self, 'wv'): self.wv = R6.weave(H, W, seed=28, pitch=6)
        C = C * (1 + (0.55 * (self.wv - 0.5) * red))[..., None]
        lum = cv2.GaussianBlur(fr.mean(-1), (0, 0), 20)
        edge = np.clip(red - cv2.GaussianBlur(cv2.erode(red, np.ones((9, 9), np.uint8)), (0, 0), 3), 0, 1)
        C = C + (red * np.clip(lum - 0.3, 0, 1) * 0.55)[..., None] * np.array([0.9, 0.12, 0.04], np.float32) + (edge * (0.4 + lum))[..., None] * np.array([1.0, 0.32, 0.08], np.float32) * 1.4
        fr = fr * (1 - A[..., None]) + C * A[..., None]
        fr = E.dust_motes(fr, t, 1331, n=90, amt=0.6, drift=(-80, -10), depth=True)
        return bloom(fr, 0.8, 0.45)


class Title(Shot):   # 片名底板（第三棒改）：不再是金色云海空镜，改墨黑底 + 低处缓缓涌动的暖金烟 + 余烬上飘（墨黑红次色调）
    def __init__(self):
        n = K.fbm(H // 2, W // 2, 1340, base=4, octaves=5)
        self.ink = cv2.resize(((0.015 + 0.03 * n)[..., None] * np.array([1.0, 0.85, 0.75], np.float32)).astype(np.float32), (W, H))
        self.sm = [K.fbm(H // 4, W // 2, 1341 + i, base=3 + 2 * i, octaves=5) for i in range(2)]

    def base(self, t):
        fr = self.ink.copy()
        yv = np.arange(H, dtype=np.float32)[:, None, None] / H
        for i, sm in enumerate(self.sm):
            m = cv2.resize(R3.slide(sm, (t - 224.0) * (8 + 10 * i)), (W, H))
            m = np.clip((m - 0.45) * 2.2, 0, 1)[..., None] * sstep(0.35, 0.95, yv)
            fr = fr + m * np.array([0.55, 0.28, 0.10], np.float32) * (0.35 + 0.25 * i)
        fr = RS.fx_embers(fr, t, 1342, amt=0.7, n=60)
        return fr


TITLE_S, TITLE_ADV, TITLE_Y = 340, 340 * 0.86, 470       # 第六棒：墨迹宽 ≈ 3×292+245 ≈ 1120px（58% 画宽），字间空隙 ≈ 47px ≈ 0.14em


def title_layer(t, start=223.97, stagger=0.10, dur=0.30, seed=3):
    """片名「谁定正邪」：志莽行书，逐字火线烧出（每字 0.30s，按序错 0.10s → 224.60s 前四字全部成形）；
    「邪」朱红 + 金边；火星只在笔画边缘（burn_glyph 的火线带 = 字内边缘带），不盖字形。返回 (Layer, ember(H,W))。"""
    L = T.Layer(); EM = np.zeros((H, W), np.float32)
    x0 = 960 - TITLE_ADV * 1.5
    for k, ch in enumerate('谁定正邪'):
        e = c01((t - (start + stagger * k)) / dur)
        if e <= 0: continue
        a, em = E.burn_glyph(ch, 'xing', TITLE_S, e, 0.0, seed=seed + k, direction=(0.25, -1.0))
        cx = x0 + TITLE_ADV * k
        if ch == '邪':
            ring = cv2.dilate(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
            L.paste(ring, cx, TITLE_Y, GOLD_T)
            L.paste(a, cx, TITLE_Y, REDT)
        else:
            L.paste(a, cx, TITLE_Y, GOLD_T)
        if em is not None:
            g = em.shape[0]; X0 = int(round(cx - g / 2)); Y0 = int(round(TITLE_Y - g / 2))
            xs, ys = max(0, X0), max(0, Y0); xe, ye = min(W, X0 + g), min(H, Y0 + g)
            EM[ys:ye, xs:xe] += em[ys - Y0:ye - Y0, xs - X0:xe - X0]
    return L, EM


def draw_title(fr, t, **kw):
    L, EM = title_layer(t, **kw)
    fr = T.compose(fr, L, shadow=0.8, shadow_sigma=26, glow=0.45, glow_sigma=20, glow_color=(1.0, 0.55, 0.2))
    return fr + EM[..., None] * np.array([1.6, 0.85, 0.3], np.float32) + cv2.GaussianBlur(EM, (0, 0), 6)[..., None] * np.array([1.0, 0.45, 0.1], np.float32)


class E29(Title):   # S133（第六棒重排）片名《谁定正邪》：字宽 66% 画面、字距 0.12em，224.60s 前四字全部成形、留 0.8s 清楚可读；「邪」朱红金边
    def render(self, t):
        fr = self.base(t)
        fr = draw_title(fr, t)
        return bloom(fr, 0.85, 0.4)


TS = 225.42 - 1 / 30
class E30(Title):   # S133b 刀光斩过片名 → 两半滑开，露出「鬼屠 · 第二季」+「主题曲《谁定正邪》」+ 鬼屠朱印
    def render(self, t):
        fr = self.base(t)
        q = t - TS
        title = draw_title(np.zeros_like(fr), 999.0)
        if q < 0.9:   # 斩开的旧片名：上下两半错开 + 淡出
            e = eout(q / 0.5)
            yy, xx = E.grid()
            ang = math.radians(-12); s = (yy - 470) * math.cos(ang) - (xx - 960) * math.sin(ang)
            up = K.cam(title, 1.0, ox=-60 * e, oy=-50 * e); dn = K.cam(title, 1.0, ox=60 * e, oy=50 * e)
            tt = np.where((s < 0)[..., None], up, dn) * (1 - c01(q / 0.9))
            fr = fr + tt
            line = np.exp(-(s / 3) ** 2) * math.exp(-q / 0.15)
            fr = fr + line[..., None] * GOLDW * 2.5
            if q < 0.1: fr = fr + (np.exp(-(s / 60) ** 2) * 0.5 * (1 - q / 0.1))[..., None] * np.array([1.0, 0.75, 0.4], np.float32)   # 第六棒：只沿斩线暖闪，底板保持墨黑（去平灰帧）
        p = c01((q - 0.25) / 0.6)
        if p > 0:
            L = T.Layer()
            # 用户要求：第二季。「二」只有两横、字面轻且显小 → 字号略放、两侧字距略收，保持「第二季」视觉重心与「鬼屠」等重
            for i, (ch, x, sz) in enumerate((('鬼', 505, 200), ('屠', 705, 200), ('第', 1025, 200), ('二', 1215, 214), ('季', 1405, 200))):
                e = c01(p * 1.6 - i * 0.12)
                T.place(L, ch, x, 470 - 20 * (1 - eout(e)), sz, GOLD_T, 'kai', alpha=eout(e), texture=True)
            fr = T.compose(fr, L, shadow=0.75, shadow_sigma=24, glow=0.5, glow_sigma=18, glow_color=(1.0, 0.6, 0.25))
            cv2.circle(fr, (860, 475), int(13 * eout(p)), tuple(float(v) for v in REDT), -1, cv2.LINE_AA)
            s2 = c01((q - 0.75) / 0.5)
            if s2 > 0:
                L2 = T.Layer()
                for i, ch in enumerate('主题曲《谁定正邪》'):
                    T.place(L2, ch, 960 + (i - 4) * 58, 650, 46, WHITE_T, 'serif_m', alpha=eout(s2), texture=False)
                fr = T.compose(fr, L2, shadow=1.0, shadow_sigma=8, glow=0.2, glow_sigma=10)
            sp = c01((q - 0.55) / 0.5)
            if sp > 0: fr = T.stamp_seal(fr, '鬼屠', 1610, 470, 130, sp, style='yin', rot=-5, seed=9)
        return bloom(fr, 0.85, 0.4)


class Credits(Shot):
    blocks = []      # (role, names, x, y_top, t_start, dur)
    def credits(self, fr, t):
        for (role, names, x, y, ts, dur) in self.blocks:
            p = c01((t - ts) / dur)
            out = c01((t - (self.t1 - 0.35)) / 0.35)
            if p <= 0: continue
            g = R3.credit_block_up(fr.copy(), role, names, x, y, p, role_size=32, name_size=66, seal_text=(role[0] if names[0][0].isascii() else names[0][0]),
                               seal_size=46, color='white', name_font='kai', seed=hash(role) % 50)
            fr = g * (1 - out) + fr * out
        return fr

    def text(self, fr, t): return self.credits(fr, t)


class E31(Credits):   # S134（第六棒重做，去尾奏「地平线 + 中心光」同构）：正俯拍微距 —— 焦土上散着被斩碎的律令残纸（「天」「理」「规」「章」残字），
    #  焦边余烬一明一灭、逐渐冷却，细烟上升；晨光从右上斜掠。署名① 在右侧
    def __init__(self):
        self.blocks = [('出品人', ['西几王传媒'], 1660, 230, 227.85, 0.9), ('编剧 / 导演', ['苏打'], 1430, 230, 228.45, 0.8)]
        yy, xx = E.grid()
        n1 = cv2.resize(K.fbm(H // 2, W // 2, 1350, base=10, octaves=6), (W, H)); n2 = cv2.resize(K.fbm(H // 2, W // 2, 1351, base=60, octaves=3), (W, H))
        key = np.clip(0.35 + 0.75 * np.exp(-(((xx - 1900) / 1400) ** 2 + ((yy - 0) / 900) ** 2)), 0, 1.2)
        self.gnd = ((0.05 + 0.09 * n1 + 0.04 * (n2 - 0.5)) * key)[..., None] * np.array([1.0, 0.80, 0.62], np.float32)
        r = np.random.default_rng(1352)
        self.pcs = []
        for k, (ch, cx, cy, sz, rot) in enumerate((('天', 430, 420, 250, -18), ('理', 820, 690, 220, 24), ('规', 1060, 330, 180, 8), ('章', 320, 790, 170, -40), ('律', 1150, 820, 150, 60))):
            g = int(sz * 1.6)
            yv, xv = np.mgrid[0:g, 0:g].astype(np.float32)
            nz = cv2.resize(r.random((7, 7)).astype(np.float32), (g, g), interpolation=cv2.INTER_CUBIC)
            nf = cv2.resize(r.random((31, 31)).astype(np.float32), (g, g), interpolation=cv2.INTER_LINEAR)
            d = np.hypot((xv - g / 2) / (g * 0.40), (yv - g / 2) / (g * 0.33)) + 0.45 * (nz - 0.5) + 0.12 * (nf - 0.5)
            m = np.clip((1 - d) * 18, 0, 1)
            band = np.exp(-((1 - d) / 0.05) ** 2) * (d < 1.05)
            gl = T.glyph(ch, 'serif_black', sz * 0.8, False)
            G = np.zeros((g, g), np.float32); gs = gl.shape[0]; o = (g - gs) // 2
            if o >= 0: G[o:o + gs, o:o + gs] = gl
            else: G = cv2.resize(gl, (g, g))
            G = np.roll(np.roll(G, int(r.uniform(-0.17, 0.17) * g), 1), int(r.uniform(-0.12, 0.12) * g), 0)     # 字偏出纸边 → 残字
            tone = (0.40 + 0.22 * cv2.resize(K.fbm(g // 2, g // 2, 1360 + k, base=8, octaves=4), (g, g)))[..., None] * np.array([0.92, 0.80, 0.60], np.float32)
            singe = np.clip((1 - d) / 0.35, 0, 1) ** 0.8                     # 焦黄：越近烧边越暗
            C = tone * (0.35 + 0.65 * singe)[..., None] * (1 - 0.85 * G[..., None] * m[..., None]) * (1 - 0.8 * np.clip(band * 2.5, 0, 1))[..., None]
            M = cv2.getRotationMatrix2D((g / 2, g / 2), rot, 1.0)
            self.pcs.append((cv2.warpAffine(C, M, (g, g)), cv2.warpAffine(m, M, (g, g)), cv2.warpAffine(band.astype(np.float32), M, (g, g)), cx, cy, k))
        self.smoke = K.fbm(H // 4, W // 4, 1355, base=5, octaves=5)

    def render(self, t):
        u = self.u(t)
        fr = self.gnd.copy()
        EMB = np.zeros((H, W), np.float32)
        for (C, m, band, cx, cy, k) in self.pcs:
            g = m.shape[0]; x0 = int(cx - g / 2); y0 = int(cy - g / 2)
            xs, ys = max(0, x0), max(0, y0); xe, ye = min(W, x0 + g), min(H, y0 + g)
            if xe <= xs or ye <= ys: continue
            sub = (slice(ys - y0, ye - y0), slice(xs - x0, xe - x0))
            sh = cv2.GaussianBlur(m, (0, 0), 10)[sub]
            F = fr[ys:ye, xs:xe]
            F *= (1 - 0.55 * np.roll(np.roll(sh, 14, 0), -10, 1))[..., None]
            F[:] = F * (1 - m[sub][..., None]) + C[sub] * m[sub][..., None]
            fl = 0.55 + 0.45 * math.sin(t * (7 + k) + k * 1.7)
            EMB[ys:ye, xs:xe] += band[sub] * fl * (1 - 0.65 * u)
        fr = fr + EMB[..., None] * np.array([1.4, 0.48, 0.10], np.float32) + cv2.GaussianBlur(EMB, (0, 0), 8)[..., None] * np.array([0.8, 0.25, 0.05], np.float32)
        Mt = np.float32([[1, 0, 0], [0, 1, -10 * (t - self.t0)]])            # 细烟上升（反射边界，无接缝）
        sm = cv2.resize(cv2.warpAffine(self.smoke.astype(np.float32), Mt, (W // 4, H // 4), borderMode=cv2.BORDER_REFLECT), (W, H))
        sm = np.clip((sm - 0.5) * 2.0, 0, 1) * 0.18
        fr = fr * (1 - sm[..., None]) + sm[..., None] * np.array([0.62, 0.58, 0.55], np.float32)
        fr = RS.fx_embers(fr, t, 1356, amt=0.5, n=30)
        return bloom(fr, 0.85, 0.35)


class E32(Credits):   # S135 CU 手握刀柄，沿刀身滑移；署名②：美术设计 / 后期总监
    def __init__(self):
        n = K.fbm(H // 2, W // 2, 1360, base=4, octaves=5)
        self.bg = cv2.resize(((0.03 + 0.06 * n)[..., None] * np.array([1.0, 0.8, 0.6], np.float32)).astype(np.float32), (W, H))
        self.blocks = [('美术设计', ['Cait'], 1700, 230, 230.15, 0.8), ('后期总监', ['沉溺'], 1470, 230, 230.75, 0.8)]

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        fr = fx2.light_beam(fr, (200, 120), (900, 960), 50, 500, t=t, strength=0.4, seed=11)
        fr, info = put(fr, t, 'S135/sheath_hand|crop=0.28,0.42,0.95,1', (760 - 140 * u, 560), w=1900, anc=(0.5, 0.5), rim=GOLDW, rim_amt=2.6, wind=3)
        sx = -200 + 1600 * eio(u)
        fr = E.flare_streak(fr, (sx, 520 + (sx - 700) * 0.6), amt=0.6, angle=58, length=0.6)
        return bloom(fr, 0.8, 0.35)


class E33(Credits):   # S135b（第六棒重做，去尾奏「地平线 + 中心光」同构）：近景质感 —— 晨光斜掠的焦土上横着一柄黑漆刀鞘，
    #  红穗在晨风里摆，灰烬一片片落在漆面上；浅景深，背景只剩暖色光斑。署名③ 放左侧：一列职务、一列名字（≥40px）
    def __init__(self):
        n = K.fbm(H // 2, W // 2, 1370, base=6, octaves=5)
        yy, xx = E.grid()
        key = np.exp(-(((xx - 2000) / 1300) ** 2 + ((yy - 300) / 700) ** 2))
        self.bg = cv2.GaussianBlur(cv2.resize(((0.035 + 0.05 * n)[..., None] * np.array([1.0, 0.78, 0.58], np.float32)).astype(np.float32), (W, H)), (0, 0), 6) \
                  + key[..., None] * np.array([0.55, 0.36, 0.18], np.float32)
        r = np.random.default_rng(1371)
        self.bok = [(r.uniform(900, 1950), r.uniform(120, 600), r.uniform(18, 60), r.uniform(0.1, 0.35)) for _ in range(22)]
        self.ash = [(r.uniform(0, W), r.uniform(-200, H), r.uniform(4, 13), r.uniform(0.3, 1.0), r.uniform(0, 6.28)) for _ in range(70)]
        self.blocks = [('AI画师', ['沉溺·雪晴·索恩'], 250, 200, 232.35, 1.0)]

    def credits(self, fr, t):
        for (role, names, x, y, ts, dur) in self.blocks:
            p = c01((t - ts) / dur)
            if p <= 0: continue
            fr = R3.credit_block_up(fr, role, names, x, y, p, role_size=40, name_size=62, seal_text='画', seal_size=46, color='white', name_font='kai', seed=7)
        return fr

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        B = np.zeros((H, W), np.float32)
        for (x, y, rr, a) in self.bok:                                     # 背景光斑（浅景深）
            cv2.circle(B, (int(x - 40 * u), int(y)), int(rr), a, -1, cv2.LINE_AA)
        fr = fr + cv2.GaussianBlur(B, (0, 0), 6)[..., None] * np.array([1.0, 0.75, 0.45], np.float32)
        z, info = put(np.zeros((H, W, 3), np.float32), t, 'E_r6/scabbard_tassel', (1130 - 40 * u, 600), w=1900, anc=(0.5, 0.5),
                      rim=(1.0, 0.78, 0.5), rim_amt=2.2, rim_dir=(0.8, -0.6), grade=dict(expo=0.9, sat=0.7, tint=(1.06, 0.98, 0.9), lift=0.0, gamma=1.08), wind=0)
        A = info['A']
        top = info['to_scr']((2010 / 2560, 640 / 1440)); bot = info['to_scr']((1500 / 2560, 1395 / 1440))
        yy, xx = E.grid()
        wy = np.clip((yy - top[1]) / max(1.0, bot[1] - top[1]), 0, 1) ** 1.3
        wx = np.exp(-((xx - (top[0] + bot[0]) / 2) / 420) ** 2)
        dx = (26 * math.sin(t * 2.6) + 9 * math.sin(t * 5.3 + 1.0)) * wy * wx                # 红穗在晨风里摆（越往下摆幅越大）
        mx = (xx - dx).astype(np.float32); my = yy.astype(np.float32)
        z = cv2.remap(z, mx, my, cv2.INTER_LINEAR); A = cv2.remap(A, mx, my, cv2.INTER_LINEAR)
        sh = cv2.GaussianBlur(A, (0, 0), 22)                               # 接触阴影
        fr = fr * (1 - 0.6 * np.roll(np.roll(sh, 26, 0), -18, 1)[..., None])
        fr = fr * (1 - A[..., None]) + z
        sweep = np.exp(-((xx - (300 + 1500 * u) + (yy - 540) * 0.6) / 140) ** 2) * A           # 晨光掠过漆面
        fr = fr + sweep[..., None] * np.array([1.0, 0.8, 0.55], np.float32) * 0.35
        P = np.zeros((H, W), np.float32)
        for (x, y0, sz, sp, ph) in self.ash:                              # 灰烬：一片片飘落（灰白片 + 少量余烬红心）
            y = y0 + (t - self.t0) * 160 * sp
            if y > H: y -= H + 200
            xx_ = x + 30 * math.sin(t * 1.5 + ph) - 50 * u
            cv2.ellipse(P, (int(xx_), int(y)), (int(sz), int(sz * 0.45)), (t * 60 + ph * 57) % 180, 0, 360, 0.55 * sp, -1, cv2.LINE_AA)
        P = cv2.GaussianBlur(P, (0, 0), 1.0)
        fr = fr * (1 - 0.5 * P[..., None]) + P[..., None] * np.array([0.52, 0.48, 0.45], np.float32) * 0.8
        fr = RS.fx_embers(fr, t, 1373, amt=0.4, n=25)
        return bloom(fr, 0.85, 0.35)


class E34(Credits):   # S136 ELS 日出全景，远处一粒走向太阳的人影；署名④：音乐
    def __init__(self):
        self.sky = E.dawn_sky(1380, horizon=0.68, mid=(0.48, 0.34, 0.19), hor=(1.0, 0.86, 0.6), cloud=0.7, sun=(960, 640))
        self.rd, self.ra = E.ridges(n=3, base=0.66, step=0.07, seed=136, amp=0.05, far=0.55, near=0.04)
        self.blocks = [('音乐', ['西几王'], 1660, 260, 234.75, 0.9)]

    def render(self, t):
        u = self.u(t)
        fr = self.sky.copy()
        z = 1.05 - 0.05 * eio(u)
        sun = (960, 690 - 60 * u)
        fr = E.sun_disc(fr, sun, 130, amt=1.15)
        fr = fx2.god_rays(fr, sun, strength=0.8, length=1.1, t=t)
        fr = E.place_layer(fr, self.rd, self.ra, z=z)
        bob = 1.5 * abs(math.sin(t * 6.0))                                 # 第六棒：远影向日走去（步伐起伏 + 越走越小）
        fx, fy = 900 + 40 * u, 758 - 8 * u
        # 第八棒：脚下拖一道向镜头的长影（逆光低日 → 影子朝观众铺开，透视下越近越宽、越远越实）
        yy, xx = E.grid()
        L = 280.0
        dy = (yy - fy) / L
        wv = 5 + 46 * np.clip(dy, 0, 1) ** 0.8
        sh = np.exp(-((xx - fx + 14 * dy) / wv) ** 2) * np.clip((dy + 0.02) / 0.02, 0, 1) * np.clip(1 - dy, 0, 1) ** 2.2
        sh = np.maximum(sh, np.exp(-(((xx - fx) / 11) ** 2 + ((yy - fy) / 3) ** 2)))     # 脚底接触影
        sh = cv2.GaussianBlur(sh.astype(np.float32), (0, 0), 3.5)
        fr = fr * (1 - 0.78 * sh[..., None])
        fr, info = put(fr, t, 'S132/back_walk', (fx, fy - bob), h=80 - 14 * u, rim=GOLDW, rim_amt=6.5, grade=G_SIL, look='sil', wind=4)
        fr = bloom(fr, 0.85, 0.45)
        # 第八棒：辉光吃掉的人形压回去（核心实黑剪影 + 一圈细金边），远影在日面前可读
        A = np.clip(info['A'], 0, 1)
        core = cv2.erode(A, np.ones((3, 3), np.uint8))
        # [r4-DE#50] 用户：逆光剪影头部看不清 → ① 人物外侧压一圈暗做分离（头不再糊进日面）
        #            ② 剪影核心少压 6% + 提亮 8%（0.05→0.054）③ 轮廓光加强，头部那一截再加一道
        halo = np.clip(cv2.GaussianBlur(A, (0, 0), 3.4) * 1.75 - A, 0, 1)
        fr = fr * (1 - 0.78 * halo[..., None])
        fr = fr * (1 - 0.76 * core[..., None]) + core[..., None] * np.array([0.054, 0.038, 0.027], np.float32) * 0.76
        rimL = np.clip(A - core, 0, 1)
        heady = np.clip((np.arange(H, dtype=np.float32) - (fy - bob - (80 - 14 * u))) / max(1.0, 0.30 * (80 - 14 * u)), 0, 1)[:, None]
        rimL = rimL * (1 + 0.9 * (1 - heady))          # 头部（A 顶部 30%）轮廓光再强一档
        return fr + rimL[..., None] * np.array([1.0, 0.84, 0.54], np.float32) * 0.52


class E35(Shot):   # S137 ECU 刀完全入鞘「咔」，朱印「鬼屠」盖在画面中心
    def __init__(self):
        n = K.fbm(H // 2, W // 2, 1390, base=4, octaves=5)
        self.bg = cv2.resize(((0.02 + 0.04 * n)[..., None] * np.array([1.0, 0.82, 0.62], np.float32)).astype(np.float32), (W, H))
        self.tc = 238.24 - 1 / 30

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        fr = fx2.light_beam(fr, (1500, 100), (900, 960), 40, 600, t=t, strength=0.35, seed=13)
        slide = 0 if t >= self.tc else 70 * (1 - eio((t - self.t0) / (self.tc - self.t0)))
        dim = 0.55 if t >= self.tc + 0.4 else 1.0 - 0.45 * c01((t - self.tc) / 0.4) if t >= self.tc else 1.0
        fr, info = put(fr, t, 'S137/sheath_close|crop=0,0.58,1,1', (960 - slide, 600), w=2200, anc=(0.5, 0.5), rim=GOLDW, rim_amt=2.4, wind=2,
                       grade=dict(expo=0.8 * dim, sat=0.6, tint=(1.05, 0.98, 0.9), lift=0.0, gamma=1.12))
        if t >= self.tc:
            q = t - self.tc
            fr = E.flare_streak(fr, (1010, 640), amt=1.4 * math.exp(-q / 0.12), length=0.8)
            fr = RS.fx_sparks(fr, t, self.tc, (1010, 640), 1391, n=40, spd=500, dirv=(0, -1), spread=1.6, amt=0.9)
            p = c01((q - 0.08) / 0.55)
            if p > 0: fr = T.stamp_seal(fr, '鬼屠', 960, 470, 260, p, style='yin', rot=-4, seed=21)
        return bloom(fr, 0.8, 0.35)


class E36(Shot):   # S138 墨从四角收拢，只剩中心一点朱红 → 黑（干净落版）
    def __init__(self):
        self.src = None

    def render(self, t):
        if self.src is None:
            s = E35(); s.t0, s.t1 = 237.30, 239.13
            self.src = s.render(239.10)
        p = c01((t - self.t0) / 0.9)
        if p < 1:
            return TR.transition('iris_moon', self.src, np.zeros_like(self.src), p, mode='collapse', center=(960, 470), dot_color=RED)
        # 第五棒：不再长时间全黑 —— 朱点呼吸一次（像最后一滴血），同时淡朱墨晕从点向外洇开，最后 0.3s 收进黑
        q = t - (self.t0 + 0.9); end = c01((t - (self.t1 - 0.3)) / 0.3)
        yy, xx = E.grid()
        d = np.hypot(xx - 960, yy - 470)
        r = 9 * (1 + 0.45 * math.sin(math.pi * c01(q / 0.5)) ** 2) * (1 - end)
        dot = np.clip(r + 0.8 - d, 0, 1)
        R = 30 + 260 * eout(q / 1.0)
        n = cv2.resize(K.fbm(H // 4, W // 4, 1381, base=6, octaves=4), (W, H))
        ink = np.exp(-((d - R * 0.55) / (R * 0.45)) ** 2) * math.exp(-q / 0.6) * 0.18 * (1 - end) * (0.6 + 0.8 * n)
        return ink[..., None] * np.array([0.45, 0.05, 0.03], np.float32) + dot[..., None] * RED * 1.1


# =========================================================================================== 剪辑表
#   切点 = 卡点（小节拍 / 人声字头）最近帧再提前 1 帧
SHOTS = [  # (类, 起帧, 原镜号, 景别)
    (E01, 5797, 'S111', 'ECU'), (E02, 5823, 'S112', 'LS'), (E03, 5868, 'S113', 'ELS'), (E04, 5916, 'S114', 'CU'),
    (E05, 5951, 'S114b', 'ECU'), (E06, 5979, 'S115', 'MS'), (E07, 6020, 'S116', 'LS'), (E08, 6061, 'S117', 'CU'),
    (E09, 6102, 'S118', 'MS'), (E10, 6130, 'S119', 'ELS'), (E11, 6157, 'S120a', 'MS'), (E12, 6182, 'S120b', 'ELS'),
    (E13, 6218, 'S121', 'MCU'), (E14T, 6263, 'S122', 'LS'), (E15, 6295, 'S122b', 'ECU'), (E16, 6310, 'S123', 'MCU'),
    (E17, 6338, 'S124', 'MCU'), (E18, 6363, 'S124b', 'MS'), (E19, 6377, 'S125', 'CU'), (E20, 6418, 'S126', 'ELS'),
    (E21, 6459, 'S127', 'CU'), (E22, 6501, 'S128', 'LS'), (E23, 6534, 'S129', 'MCU'), (E24, 6548, 'S129b', 'ECU'),
    (E25, 6569, 'S130', 'LS'), (E26, 6610, 'S131', 'ELS'),
    (E27a, 6638, 'S132', 'ECU'), (E27b, 6658, 'S132x', 'LS'), (E27c, 6678, 'S132y', 'CU'), (E28, 6693, 'S132b', 'ECU'), (E29, 6720, 'S133', 'MS'), (E30, 6762, 'S133b', 'MS'),
    (E31, 6830, 'S134', 'ELS'), (E32, 6900, 'S135', 'CU'), (E33, 6968, 'S135b', 'ELS'), (E34, 7037, 'S136', 'ELS'),
    (E35, 7119, 'S137', 'ECU'), (E36, 7174, 'S138', '—'),
]
IDS = [s[0].__name__ for s in SHOTS]
BOUNDS = [s[1] for s in SHOTS] + [F1]
CHORUS_END = 6638

# 入点转场：(名称, pre 秒, post 秒, kw)；'hard' = 切后 2 帧冲击（推近+提亮）
# [round4-edit-audit 2026-11-09] 本轮只改 CUTS 表的 (name, pre, post, kw) 值，切点帧/字层/SHOTS 一律未动：
#   P0 转场去重 7 处：E02→ink_swallow、E04→seal_cover、E07→blade_black、E08→paper_tear、E11→occlusion、E13→ink_swallow、E21 flash_red→door_open
#   P1 过渡长度 5 处：E16/E22/E26 pre 0→0.08、E31 pre 0→0.08+post 0.40→0.20、E34 post 0.30→0.20
#   E 段收尾轮：E14T/E18/E24/E30/E35（原 hard 提亮）+ E27b（原 impact 白金闪）→ 本地新招 'impact_nf'（3 帧 8→4→1px 顿挫，不闪不提亮）
CUTS = {   # 第三棒：亮底上不再用白色系转场（flash_white 0 处、whip 1 处、zoom_through 0 处），换成暗色系：墨晕吞屏 / 刀光黑切 / 印章盖屏
    'E01': ('entry_flash', 0, 0.22, {}),
    'E02': ('ink_swallow', 0.14, 0.08, dict(center=(900, 380), seed=202)),   # [r4-P0] 原 hard（提亮闪）→ 墨吞屏
    'E03': ('ink_swallow', 0.10, 0.22, dict(center=(1150, 360), seed=3)),
    'E04': ('seal_cover', 0.10, 0.08, dict(center=(820, 470), rot=-5)),   # [r4-P0] 原 hard（提亮闪）→ 印章盖屏
    'E05': ('impact', 0, 0, dict(col=(1.0, 0.82, 0.45), amp=10)),   # 第七棒：whip 中间帧纯黄横糊 → 金闪冲击硬切（昭彰开裂的冲击）
    'E06': ('occlusion', 0.08, 0.16, dict(kind='pillar', direction=-1, color=(0.03, 0.02, 0.015))),
    'E07': ('blade_black', 0.10, 0.12, dict(angle=-28, width=210, seed=7)),   # [r4-P0] 原 hard（提亮闪）→ 刀光黑切
    'E08': ('paper_tear', 0.08, 0.12, dict(seed=8, angle=5)),   # [r4-P0] 原 hard（提亮闪）→ 撕纸
    'E09': ('paper_tear', 0.06, 0.18, dict(seed=5)),
    'E10': ('blade_black', 0.06, 0.12, dict(angle=-25, width=200)),
    'E11': ('occlusion', 0.10, 0.14, dict(kind='pillar', direction=-1, color=(0.03, 0.02, 0.015))),   # [r4-P0] 原 hard（提亮闪）→ 前景遮挡
    'E12': ('seal_cover', 0.08, 0.16, dict(center=(820, 500), rot=-4)),
    'E13': ('ink_swallow', 0.16, 0.08, dict(center=(1000, 520), seed=13)),   # [r4-P0] 原 hard（提亮闪）→ 墨吞屏
    'E14T': ('impact_nf', 0, 0, {}),   # [r4-E] 原 hard（提亮 15%）→ 无闪顿挫
    'E15': ('hard', 0, 0, {}),
    'E16': ('door_open', 0.08, 0.20, dict(cx=960)),             # [r4-P1] pre 0→0.08（原注释：第四棒：E15 沿竖缝裂开两扇滑出 → E16 自己的中缝（图形匹配））
    'E17': ('push_h', 0.07, 0.13, {}),                         # 第四棒：横推，中间帧 = 金脸 | 朱缝 | 朱脸 正面相对
    'E18': ('impact_nf', 0, 0, {}),    # [r4-E] 原 hard（提亮 15%）→ 无闪顿挫
    'E19': ('gold_leaf', 0.04, 0.22, dict(center=(960, 540), seed=19, red_frac=0.07)),   # 第六棒：三角碎片 → 有厚度的金箔碎片（与镜内箔片同质）
    'E20': ('light_sweep', 0.06, 0.22, dict(y=770)),           # 第六棒：圆形 iris → 贴地平线的横向光线扫入
    'E21': ('door_open', 0.0, 0.08, dict(cx=960)),   # [r4-P0] 原 flash_red → 门缝开
    'E22': ('match_cut', 0.08, 0.18, dict(shape='circle', center=(960, 330), radius=120)),   # [r4-P1] pre 0→0.08
    'E23': ('impact', 0, 0, dict(col=(1.0, 0.86, 0.6), amp=10, soft=True)),     # 第五棒：硬切加冲击；第八棒 soft：冲白减半护暗部、色散减半
    'E24': ('impact_nf', 0, 0, {}),    # [r4-E] 原 hard（提亮 15%）→ 无闪顿挫
    'E25': ('slash_wipe', 0.03, 0.12, dict(angle=-8)),
    'E26': ('match_cut', 0.08, 0.22, dict(shape='line', center=(960, 600), angle=0)),   # [r4-P1] pre 0→0.08
    'E27a': ('impact', 0, 0, dict(col=(1.0, 0.25, 0.12), amp=12)),   # 第五棒：朱红闪 + 抖
    'E27b': ('impact_nf', 0, 0, {}),     # [r4-E] 原 impact 白金闪 + 抖 → 无闪顿挫（保留 E27a 朱红闪 + E27c 刀线，三连仍成立）
    'E27c': ('slash_wipe', 0.03, 0.10, dict(angle=-78)),               # 第五棒：E27b 刀光延续成斩线 → 匾
    'E28': ('impact', 0, 0, dict(col=(0.9, 0.2, 0.1), amp=10)),      # 第六棒：入转场不再带出匾（匾只在 E04/E05/E27c）
    'E29': ('ink_swallow', 0.18, 0.18, dict(center=(1000, 500), seed=9)),
    'E30': ('impact_nf', 0, 0, {}),    # [r4-E] 原 hard（提亮 15%）→ 无闪顿挫（落版入口）
    'E31': ('ink_bleed', 0.08, 0.20, dict(center=(960, 540), white=False, seed=9)),   # [r4-P1] pre 0→0.08、post 0.40→0.20
    'E32': ('blade_sweep', 0.12, 0.16, dict(direction=1)),      # 第五棒：平灰板 → 近景刀身掠镜（钢纹/脊线/刃口暖光/运动模糊）
    'E33': ('warm_veil', 0.14, 0.20, dict(axis='x', direction=-1, seed=7301, cap=0.66)),   # 第七棒：fog_wall 中间帧满屏平灰 → 暖雾封顶 66%（刀柄/刀穗剪影始终透出）+ 斜入光束 + 翻卷亮边
    'E34': ('warm_veil', 0.20, 0.20, dict(axis='y', seed=7341, cap=0.62, warm=(1.0, 0.82, 0.52), dark=(0.13, 0.09, 0.06))),   # [r4-P1] post 0.30→0.20（原注释：第七棒：灰烟平涂 → 自下翻涌的暖金烟（封顶 62%，烟里带光束与亮边））
    'E35': ('impact_nf', 0, 0, {}),    # [r4-E] 原 hard（提亮 15%）→ 无闪顿挫（落版）
    'E36': ('cut', 0, 0, {}),
}
CUSTOM = {'warm_veil': R7.warm_veil, 'light_sweep': R6.light_sweep, 'gold_leaf': R6.gold_leaf, 'blade_sweep': R5.blade_sweep, 'fog_wall': R5.fog_wall, 'blade_black': R3.blade_black, 'seal_cover': R3.seal_cover, 'ink_swallow': R3.ink_swallow, 'push_h': R3.push_h, 'door_open': R3.door_open}

# 运镜：(缓动, z0, z1, x0, x1, y0, y1, rot0, rot1)
MOVE = {
    'E01': ('expo_out', 1.08, 1.0, 40, -40, 0, 0, -1.5, 0),
    'E02': ('sine', 1.02, 1.08, 0, 0, 40, -30, 0.8, -0.6),      # 第六棒：低机位缓升推
    'E03': ('sine', 1.03, 1.0, 0, 0, -20, 30, 0, 0),
    'E04': ('expo_in', 1.0, 1.12, 0, 0, 0, 0, 0, 0),           # 推进匾
    'E05': ('sine', 1.04, 1.10, -30, 30, 0, 0, -2, 2),
    'E06': ('expo_in', 1.0, 1.16, 0, 0, 0, 0, 0, 0),           # 穿帘推轨
    'E07': ('sine', 1.04, 1.0, 0, 0, 0, 0, 1.5, -1.5),        # 环绕感（配合视差）
    'E08': ('sine', 1.0, 1.08, 0, 0, 20, -20, 0, 0),
    'E09': ('expo_out', 1.08, 1.0, -60, 40, 0, 0, 2, -1),
    'E10': ('sine', 1.0, 1.10, 0, 0, 0, 0, 0, 0),
    'E11': ('expo_out', 1.06, 1.0, 0, 0, -30, 0, 0, 0),
    'E12': ('expo_out', 1.28, 1.0, 0, 0, 0, 0, -6, 0),          # 摇臂升（拉高俯拍）
    'E13': ('sine', 1.0, 1.06, -20, 20, 0, 0, 0, 0),
    'E14T': ('sine', 1.08, 1.0, 0, 0, 0, 0, 0, 0),             # 拉轨
    'E15': ('sine', 1.04, 1.04, 60, -60, 0, 0, 0, 0),
    'E16': ('sine', 1.0, 1.03, -40, 40, 0, 0, 0, 0),
    'E17': ('sine', 1.0, 1.03, 40, -40, 0, 0, 0, 0),
    'E18': ('sine', 1.0, 1.04, 0, 0, 0, 0, 0, 0),
    'E19': ('expo_in', 1.0, 1.10, 0, 0, 0, 0, 0, 0),
    'E20': ('sine', 1.0, 1.06, 20, -30, 10, -10, 0, 0),
    'E21': ('sine', 1.0, 1.06, 30, -10, 0, 0, 0, 0),
    'E22': ('sine', 1.0, 1.04, 0, 0, -30, 0, 0, 0),           # 摇臂降对齐
    'E23': ('expo_in', 1.0, 1.18, 0, 0, 0, 0, 0, 0),           # 吸气
    'E24': ('sine', 1.06, 1.0, 0, 0, 0, 0, 0, 0),
    'E25': ('expo_out', 1.12, 1.0, 0, 0, 0, 0, 0, 0),
    'E26': ('expo_out', 1.25, 1.0, 0, 0, -40, 0, 0, 0),        # 拉远：刀线 → 地平线
    'E27a': ('expo_out', 1.15, 1.0, 0, 0, 0, 0, 0, 0),
    'E27b': ('expo_out', 1.08, 1.0, 40, -40, 0, 0, -2, 1),
    'E27c': ('expo_out', 1.0, 1.1, 0, 0, 0, 0, 0, 0),
    'E28': ('sine', 1.0, 1.05, 0, 0, 0, 0, 0, 0),
    'E29': ('sine', 1.0, 1.04, 0, 0, 0, 0, 0, 0),
    'E30': ('sine', 1.04, 1.07, 0, 0, 0, 0, 0, 0),
    'E31': ('sine', 1.04, 1.09, 0, 0, 0, 0, -1.0, 1.0),         # 第六棒：俯拍缓推 + 微转
    'E32': ('sine', 1.0, 1.04, 0, 0, 0, 0, 0, 0),
    'E33': ('sine', 1.0, 1.06, 30, -30, 0, 0, 0, 0),           # 第六棒：近景缓推 + 横移
    'E34': ('sine', 1.0, 1.06, 0, 0, 30, -10, 0, 0),          # 第六棒：1.0→1.06 推镜（不再 2.73s 静止）
    'E35': ('sine', 1.0, 1.04, 0, 0, 0, 0, 0, 0),
    'E36': ('sine', 1.0, 1.02, 0, 0, 0, 0, 0, 0),
}
SHAKE = {   # 冲击抖：(时刻, 幅度 px)
    'E05': [(CT(49, 11), 10)], 'E09': [(CT(51, 2), 12)], 'E11': [(6157 / 30, 12)], 'E12': [(CT(51, 9), 8)],
    'E25': [(CT(55, 6), 18)], 'E27b': [(6658 / 30, 14)], 'E27c': [(6678 / 30, 7)], 'E15': [(210.058, 16)], 'E30': [(TS, 8)], 'E35': [(238.24 - 1 / 30, 5)], 'E20': [(CT(54, 2), 10)],
}
# [r4-DE#51] 尾段跟鼓点：把 234.4–239.6 的密集重音逐颗变成镜头顿挫（amp = 2.5 + 5×强度，3–6px）
SHAKE['E34'] = SHAKE.get('E34', []) + [(th, 2.5 + 5.0 * s) for th, s in OUTRO_HITS if th < 237.30]
SHAKE['E35'] = SHAKE.get('E35', []) + [(th, 2.5 + 5.0 * s) for th, s in OUTRO_HITS if th >= 237.30]


def ease(kind, u):
    u = c01(u)
    if kind == 'expo_out': return 1 - 2 ** (-8 * u)
    if kind == 'expo_in': return (2 ** (8 * u) - 1) / 255
    return 0.5 - 0.5 * math.cos(math.pi * u)


class _Sec:
    def __init__(self):
        self.objs = {}

    def obj(self, i):
        if i not in self.objs:
            cls = SHOTS[i][0]; o = cls()
            o.t0, o.t1 = BOUNDS[i] / FPS, BOUNDS[i + 1] / FPS; o.id = IDS[i]
            self.objs[i] = o
            if len(self.objs) > 6: self.objs.pop(next(k for k in self.objs if k != i))
        return self.objs[i]

    def full(self, i, t):
        """镜头 i 在时刻 t 的完整画面（场景 + 运镜 + 屏幕字）。"""
        o = self.obj(i); sid = IDS[i]
        fr = o.render(t)
        mv = MOVE.get(sid)
        if mv:
            e = ease(mv[0], o.u(t))
            z = mv[1] + (mv[2] - mv[1]) * e; x = mv[3] + (mv[4] - mv[3]) * e; y = mv[5] + (mv[6] - mv[5]) * e; r = mv[7] + (mv[8] - mv[7]) * e
            z *= 1 + 0.010 * kick_punch(t) + 0.020 * outro_punch(t)   # [r4-DE#51] 尾段跟鼓点：每个重音 2% 推近脉冲 + 抖动
            for (ts, amp) in SHAKE.get(sid, []):
                q = t - ts
                if 0 <= q < 0.5:
                    a = amp * math.exp(-q / 0.12)
                    x += a * math.sin(q * 90); y += a * math.cos(q * 73)
            fr = K.cam(np.clip(fr, 0, 4).astype(np.float32), z, x, y, r)
        if sid in NO_TXT: return fr          # [r4-DE#46] 该镜屏幕大字按用户要求删除
        return o.text(fr, t)

    def frame_f(self, f):
        t = f / FPS
        i = max(k for k in range(len(SHOTS)) if BOUNDS[k] <= f)
        for j in (i, i + 1):
            if j <= 0 or j >= len(SHOTS): continue
            name, pre, post, kw = CUTS.get(IDS[j], ('hard', 0, 0, {}))
            c = BOUNDS[j] / FPS
            if name in ('hard', 'cut', 'entry_flash', 'impact', 'impact_nf') or not (c - pre - 1e-6 <= t < c + post - 1e-6): continue
            B = self.full(j, t)
            A = self.full(j - 1, min(t, c - 1 / FPS) if pre == 0 else t)
            p = (t - (c - pre)) / (pre + post)
            if pre == 0: p = 0.5 + 0.5 * p
            A = np.clip(A, 0, 4).astype(np.float32); B = np.clip(B, 0, 4).astype(np.float32)
            if name in CUSTOM: return CUSTOM[name](A, B, p, **kw), 2
            return TR.transition(name, A, B, p, **kw), 2
        fr = self.full(i, t)
        name = CUTS.get(IDS[i], ('hard',))[0]
        k = f - BOUNDS[i]
        ca = 0
        if name == 'entry_flash':                              # 段落入口：自带金白闪（接 D 组任意尾帧）
            p = c01(k / (0.22 * FPS))
            fr = fr * (0.4 + 0.6 * p) + np.array([1.0, 0.92, 0.78], np.float32) * (1 - p) ** 2 * 1.2
            ca = 3 if k < 3 else 0
        elif name == 'impact' and k < 5 and i > 0:              # 第五棒：硬切冲击 = 2 帧色闪 + 4 帧位移抖 + RGB 分离
            kw = CUTS[IDS[i]][3]; amp = kw.get('amp', 10)
            fl = (1.0, 0.55, 0, 0, 0)[k]
            sx = amp * (1, -0.8, 0.6, -0.35, 0.15)[k]; sy = amp * (-0.6, 0.7, -0.4, 0.25, -0.1)[k]
            fr = K.cam(fr, 1 + 0.03 * (1 - k / 5), ox=sx, oy=sy)
            if kw.get('soft'):                                  # 第八棒（E23）：冲白减半且护暗部——闪只加在亮部，脸/衣暗部保留，色散减半
                lum = np.clip(fr.mean(-1, keepdims=True), 0, 1)
                hi = np.clip((lum - 0.12) / 0.5, 0, 1)
                fr = fr * (1 + 0.3 * fl * hi) + np.asarray(kw.get('col', (1, 1, 1)), np.float32) * 0.16 * fl * hi
                ca = (3, 2, 1, 1, 0)[k]
            else:
                fr = fr * (1 + 0.6 * fl) + np.asarray(kw.get('col', (1, 1, 1)), np.float32) * 0.45 * fl
                ca = (6, 5, 3, 2, 1)[k]
        elif name == 'impact_nf' and k < 3 and i > 0:
            # round4 P2b/E：**无闪落拍顿挫**（与 sec_a 的 impact_nf 同规格，本地实现，不跨文件 import）：
            # 切后 3 帧衰减 (1.0, 0.45, 0.18) + 竖向位移抖 8→4→1px + 1.02 推近；不闪、不提亮、不做 RGB 分离。
            a_ = (1.0, 0.45, 0.18)[k]
            dy = (8.0, -4.0, 1.0)[k]
            fr = K.cam(fr, 1 + 0.02 * a_, oy=dy)
            ca = 2 if k == 0 else 1
        elif name == 'hard' and k < 2 and i > 0:
            a = 1.0 if k == 0 else 0.45
            fr = K.cam(fr, 1 + 0.025 * a) * (1 + 0.15 * a) + 0.04 * a
            ca = 3 if k == 0 else 1
        return fr, ca


_SEC = {}
def frame(f, cache):
    s = cache.get('sec')
    if s is None: s = cache['sec'] = _Sec()
    fr, ca = s.frame_f(int(f))
    t = f / FPS
    if f >= 7174:     # 收墨：不加颗粒/暗角，干净落版
        out = np.clip(fr, 0, 1); out[:BAR] = 0; out[H - BAR:] = 0
        return K.to8(out)
    fr = K.finish(fr, t, ca=ca, grain=0.035, vig=0.38, bloom_amt=0.25, red_keep=1.0)
    fr = GU.apply(fr, t, 'e_final_outro')                 # 统一 grade 层
    return K.to8(fr)


if __name__ == '__main__':
    import time
    from PIL import Image
    f = int(sys.argv[1]); out = sys.argv[2] if len(sys.argv) > 2 else '/tmp/e.png'
    a = time.time(); im = frame(f, {}); print('%.2fs' % (time.time() - a))
    Image.fromarray(im).save(out)
