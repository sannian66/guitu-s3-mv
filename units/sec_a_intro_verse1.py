"""units/sec_a_intro_verse1.py — A 组：前奏 + 主歌一（帧 0–1321，0–44.03s），第四轮重做。
设计说明：crew/round4/A_storyboard.md（29 镜，平均 1.52s；主歌 21 镜平均 1.37s）。
接口：READY / frame(f, cache) → uint8 (1080,1920,3) 成品帧（含黑边、颗粒、暗角）。
结构仿 units/chorus1.py：每镜一个类 render(t)->(线性帧, ca)；CUTS 表驱动转场；VCam3 主运镜 + 卡点脉冲；屏幕层 = 署名 / 歌词竖排。"""
import os, sys, math, json
ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv')
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
os.environ.setdefault('SPRITE_MODE', '1')
import numpy as np, cv2
import c1kit as K
import typo as T
import trans as TR
import fx2
import props as PR
import vcam3 as V3
import vcam as VC
import a_kit as A
import a_r7 as R7
import a_r8 as R8
import a_r9 as R9
import a_r5 as R5                                     # 第五轮（用户 12 条）开关
from a_kit import clamp01, eio, eout, ein, COLD, GOLD, REDR, WARM

READY = True


# 第六轮 #53（用户 2026-11-10「竖排歌词要全部去掉，因为我们改成横排了呀」）：画内歌词层全部掐掉，歌词只走底部横排字幕 units/subtitle.py。
#   R5_NOVLYR=1（默认）删；R5_NOVLYR=0 回滚到第五轮现状。只掐歌词层：屏幕层 LY2 整句歌词、V09 梁下两列竖排「谁把人命/装进天平」、
#   V14 火星竖排一列「每一次拔刀都是」（火星本身保留）。镜内互动字（五百重甲、寒光、罪状、里/称量、殺/放、我的主张、正、锋芒）与诏文乱码不动。
def _on(k, d='1'): return os.environ.get(k, d) != '0'
def R6B_OFF(k): return k in os.environ.get('A_R6B_OFF', '').split(',') or os.environ.get('A_R6B_OFF', '') == 'all'   # r6 第二棒开关（改前对比用）
def HG_ON(): return os.environ.get('A_R6D_HANGUANG', '') == '1'   # r6 第四棒：用户 11-10 15:28 拍板 V05/V06 画内「寒光」字全去；=1 恢复（改前对比用）
def R6F_OFF(k): return k in os.environ.get('A_R6F_OFF', '').split(',') or os.environ.get('A_R6F_OFF', '') == 'all'   # r6 第六棒开关：slash2b（第二刀刀光压曝光）/ sf7b（#7 双头+恶徒）；POLISH1：sf7c（#7 斩杀刀光起点/命中闪）/ slash2c（653/654f 星芒软肩）
def R6E_OFF(k): return k in os.environ.get('A_R6E_OFF', '').split(',') or os.environ.get('A_R6E_OFF', '') == 'all'   # r6 第五棒开关：slash2（第二刀无字刀光）/ lycut（LY2「拦不住一道」在 V05 切点前退净）
def R6C_OFF(k): return k in os.environ.get('A_R6C_OFF', '').split(',') or os.environ.get('A_R6C_OFF', '') == 'all'   # r6 第三棒开关（改前对比用）：sf7 / stele / …


NOVLYR = _on('R5_NOVLYR')
# 第六轮补充（总导演 13:30，按用户 #55「镜里那些横排……的歌词字，保留」）：屏幕层 LY2 是横排 → 恢复；竖排（V09「谁把人命/装进天平」、V14 火星竖列）继续去掉。
#   R5_NOVLYR=1（默认）只去竖排、保留横排 LY2；R5_NOVLYR=all 横竖都去（#53 原样）；R5_NOVLYR=0 回滚到第五轮现状（横竖都在）。
NOHLYR = os.environ.get('R5_NOVLYR', '1').strip() == 'all'
FPS = 30
W, H, BAR = 1920, 1080, 120
F0, F1 = 0, 1321
HMP = ROOT + '/crew/round4/A_hitmap.json'
HM = json.load(open(HMP))
WT = {(w['line'], w['k']): w['t'] for w in HM['words']}
WT[(0, 1)] = 16.08                     # whisper 把「长夜」压在同一时刻，「夜」顺延
RED = np.array([0.72, 0.06, 0.05], np.float32)
GOLDV = np.array([1.0, 0.76, 0.40], np.float32)
COLDV = np.array([0.62, 0.74, 1.0], np.float32)
INK = np.array([0.02, 0.022, 0.03], np.float32)


def V(t): return (round(t * FPS) - 1) / FPS            # 声音 → 视觉帧（早 1 帧）
def CT(li, k): return V(WT[(li, k)])
def cprog(li, ks, t, dur=0.22):
    return [clamp01((t - (CT(li, k) - dur)) / dur) for k in ks]


def S(key, mode='cut', **kw): return A.src(key, mode, **kw)


_BGF = {}
def BG(ch, fname, size, p, seed=0, **kw):
    """第十一棒（critic_A_r7 P0-1 逐字错读）：笔序书写时半截笔画会读成别的字（「不」先出一横 → 「一」）。
    书写前 1/3 先铺一层整字淡墨影（墨影完整可读），笔触在墨影上走完 → 任何时刻屏上都是整字，不出残笔错读。"""
    g = T.brush_glyph(ch, fname, size, p, seed=seed, **kw)
    if p >= 0.999 or p <= 0: return g
    k = (ch, fname, size, seed)
    if k not in _BGF: _BGF[k] = T.brush_glyph(ch, fname, size, 1.0, seed=seed, **kw)
    return np.maximum(g, _BGF[k] * 0.55 * eout(clamp01(p * 3.0)))


class Shot:
    t0 = t1 = 0.0
    def u(self, t): return clamp01((t - self.t0) / (self.t1 - self.t0))


def night(top=(0.010, 0.013, 0.024), bot=(0.06, 0.07, 0.10), y1=H):
    return A.vgrad(top, bot, 0, y1, 1.3)


def pupil_glint(fr, p, g, size=1.0, col=(1.0, 0.96, 0.9)):
    if g <= 0.01: return fr
    q = 2; yy, xx = np.mgrid[0:H // q, 0:W // q].astype(np.float32)
    X, Y = xx * q - p[0], yy * q - p[1]
    st = np.exp(-(np.abs(X) / (3 * size) + np.abs(Y) / (60 * size))) + np.exp(-(np.abs(Y) / (2.5 * size) + np.abs(X) / (160 * size)))
    st += np.exp(-(X * X + Y * Y) / (200 * size * size)) * 1.5
    return fr + cv2.resize(st, (W, H))[..., None] * g * np.array(col, np.float32)


def streak(fr, y, x0, x1, q, col=(1, 0.97, 0.92), w=3, ang=0.0, amt=1.0):
    """刀光直线：q 0→1 由 x0 扫到 x1，带辉光尾迹。"""
    if q <= 0 or amt <= 0: return fr
    L = np.zeros((H // 2, W // 2), np.float32)
    xe = x0 + (x1 - x0) * min(1, q); xs = x0 + (x1 - x0) * max(0, q - 0.45)
    th = math.radians(ang)
    def P(x): return (int(x / 2), int((y + (x - W / 2) * math.tan(th)) / 2))
    cv2.line(L, P(xs), P(xe), 1.0, max(1, w // 2), cv2.LINE_AA)
    L = cv2.resize(L, (W, H))
    fade = 1.0 if q < 1 else max(0, 1 - (q - 1) * 3)
    return fr + (L * 1.6 + cv2.GaussianBlur(L, (0, 0), 14) * 1.4 + cv2.GaussianBlur(L, (0, 0), 50) * 0.8)[..., None] * np.array(col, np.float32) * fade * amt


def fog(fr, t, seed, y0, y1, amt, col=(0.45, 0.5, 0.6), speed=(30, 0), light=None, cam=(0, 0)):
    return FOG[seed % 3].draw(fr, t, density=amt, y0=y0, y1=y1, color=col, speed=speed, light=light, cam=cam)


FOG = [fx2.Fog(1), fx2.Fog(2), fx2.Fog(3)]
RAIN = fx2.RainSheet(5, density=0.8)
EMB = fx2.Embers(11, n=160, mode='fire')
ASH = fx2.Embers(12, n=140, mode='ash', rise=60)
GDUST = fx2.Embers(13, n=120, mode='gold', rise=40)


# =====================================================================================
# 前奏
# A01 0.00–2.21 ELS 墨滴开天（第四棒：去月）：墨晕开出云海，光藏在云后——三道体积光束扫过云海，云层快速流动 + 三层山脊视差
class A01(Shot):
    def __init__(self):
        self.bg = night((0.012, 0.016, 0.03), (0.09, 0.10, 0.13))
    def scene(self, t):
        fr = self.bg.copy()
        lx = 1180 + 120 * t                                              # 云后光源缓慢横移（光束随之扫）
        fr = A.glow(fr, (lx, 300), 520, 0.30, (0.55, 0.62, 0.82))
        fr = fx2.god_rays(fr, (lx, 280), strength=0.28, length=1.0, color=(0.7, 0.78, 0.95), t=t * 2.5, src_r=160)
        fr = A.clouds(fr, t, 3, speed=(70, 0), y0=0, y1=640, amt=1.0, col=(0.16, 0.18, 0.23), light=(lx, 300), light_r=480, thr=0.40)
        for i, (by, amp, tone) in enumerate(((720, 160, (0.05, 0.06, 0.08)), (800, 120, (0.03, 0.035, 0.05)), (900, 90, (0.012, 0.014, 0.02)))):
            fr, _ = A.ridge(fr, by, amp, 40 + i, tone=tone, rim=(0.5, 0.58, 0.75), rim_amt=0.35 - 0.1 * i, dx=-t * (20 + 40 * i))
            fr = fog(fr, t, i, by - 80, by + 60, 0.35, (0.30, 0.34, 0.42), speed=(40 + 30 * i, 0))
        return fr
    def render(self, t):
        sc = self.scene(t)
        T_DROP = V(0.37)
        if t < T_DROP:                                  # 墨滴：自上而下一道细亮线落向画面中心
            fr = np.zeros_like(sc) + 0.004
            q = clamp01(t / T_DROP)
            y = 120 + (560 - 120) * q ** 2
            fr = A.glow(fr, (960, y), 10, 1.2, (0.9, 0.92, 1.0))
            fr = A.glow(fr, (960, y - 40), 6, 0.6, (0.6, 0.7, 0.9), aspect=0.15)
            return fr, 0
        p = eout((t - T_DROP) / 1.55, 2)
        blk = np.zeros_like(sc) + 0.004
        fr = TR.ink_bleed(blk, sc, p, seed=4, center=(960, 560), edge=0.85)
        k = math.exp(-(t - T_DROP) / 0.12)
        fr = A.glow(fr, (960, 560), 60 + 300 * (1 - k), 0.8 * k, (0.8, 0.85, 1.0))
        return fr, (2 if k > 0.5 else 0)


# A02 2.21–4.06 LS 侧逆光山脊（第四棒：人物移到左 1/3，巨月只露右侧一角出框；避开副歌一「满月前居中剪影」）
class A02(Shot):
    def __init__(self):
        self.bg = night((0.02, 0.025, 0.045), (0.07, 0.08, 0.11))
    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        fr = A.moon(fr, 2080, 300, 400, 0.80, halo=0.9)                      # 第七棒：月心出框，只剩云后一弧月晕（拉开与副歌一满月剪影的距离）
        fr = A.clouds(fr, t, 7, speed=(-60, 0), y0=300, y1=760, amt=0.85, col=(0.22, 0.24, 0.30), light=(1880, 330), light_r=520, thr=0.42)
        fr, _ = A.ridge(fr, 940, 260, 52, tone=(0.035, 0.04, 0.055), rim=(0.6, 0.68, 0.85), rim_amt=0.25, dx=-u * 60)
        fr, rl = A.ridge(fr, 1010, 150, 57, tone=(0.006, 0.007, 0.01), rim=(0.75, 0.82, 1.0), rim_amt=0.5, peaks=2, dx=u * 70)
        fy = float(rl[640]) + 6
        fr, info = A.place(fr, t, S('S002/back_wind'), (640 + 30 * u, fy), h=500, rim=COLD, rim_amt=3.6, rim_dir=(0.9, -0.4), wind=13,
                           grade=dict(expo=0.55, sat=0.5, gamma=1.25), wrap=0.6)
        fr = fog(fr, t, 1, fy - 60, 1000, 0.5, (0.25, 0.28, 0.35), speed=(120, 0))
        fr = ASH.draw(fr, t, 0.7, wind=(220, 10))
        return fr, 0


# A03 4.06–5.97 ECU 拇指推刀出鞘（第四棒：4.53 拍上刀身真实滑出 40px + 鞘口迸尘、手指收紧微颤、扫光）
class A03(Shot):
    def __init__(self):
        self.path = S('S003/thumb_push', 'dm')
        self.bg = night((0.01, 0.012, 0.02), (0.03, 0.035, 0.05))
    def render(self, t):
        u = self.u(t)
        fr = A.glow(self.bg.copy(), (1500 - 200 * u, 300), 420, 0.22, (0.5, 0.58, 0.8))
        push = eout((t - V(4.53)) / 0.35) * 40 + 8 * eout((t - V(5.46)) / 0.25)
        jit = 1.5 * math.sin(t * 47) * clamp01((t - V(4.53)) / 0.1) * math.exp(-max(0, t - V(4.53)) / 0.4)
        fr, info = A.place(fr, t, self.path, (860 - 30 * eio(u) - push, 610 + jit), w=2150 * (1 + 0.04 * u), anc=(0.5, 0.42), rim=COLD,
                           rim_amt=1.4, wind=0.0, grade=dict(expo=0.78, sat=0.6, gamma=1.15), wrap=0.2, breathe=0.0)
        q = clamp01((t - V(4.53)) / 0.95)
        if 0 < q < 1:
            x = 200 + 1500 * eio(q)
            lum = fr.mean(-1); sat = fr.max(-1) - fr.min(-1)
            steel = np.clip((lum - 0.30) / 0.2, 0, 1) * np.clip((0.12 - sat) / 0.08, 0, 1) * info['A']
            xx = np.arange(W, dtype=np.float32)[None]
            band = np.exp(-((xx - x) / 70) ** 2)
            fr = fr + (steel * band)[..., None] * 1.4 * np.array([0.9, 0.95, 1.0], np.float32)
            fr = A.glow(fr, (x, 470), 60, 0.5 * math.sin(math.pi * q), (0.8, 0.88, 1.0), aspect=3)
        mouth = info['to_scr']((0.47, 0.42))
        fr = K.sparks(fr, t, 33, mouth, n=70, life=0.9, speed=(40, 260), dirc=(0, -1), spread=2.4, grav=-60, area=(90, 30), amt=0.55,
                      t0=V(4.53), burst=True, color=(0.75, 0.8, 0.9))
        fr = GDUST.draw(fr, t, 0.35, wind=(-60, -30))
        return fr, (2 if 0 <= t - V(4.53) < 0.07 else 0)


# A04 5.97–7.38 CU 侧脸（第四棒：微转头 + 三层视差：远月晕反向漂、中景尘、近景虚焦光斑快速横移）
class A04(Shot):
    def render(self, t):
        u = self.u(t)
        fr = night((0.01, 0.012, 0.022), (0.025, 0.03, 0.045))
        fr = A.glow(fr, (1560 - 90 * u, 380), 330, 0.55, (0.55, 0.62, 0.82))
        fr = A.glow(fr, (1560 - 90 * u, 380), 110, 0.35, (0.85, 0.9, 1.0))
        fr = fog(fr, t, 2, 300, 1000, 0.25, (0.18, 0.2, 0.26), speed=(-90, 0))
        turn = eio((t - V(6.48)) / 0.5)
        fr, info = A.place(fr, t, S('S004/profile'), (1270 + 70 * u, 1000), h=880 * (1 + 0.03 * u), flip=True, rim=COLD, rim_amt=4.0,
                           rim_dir=(0.8, -0.6), wind=14, rot=-2.5 + 3.5 * turn, grade=dict(expo=0.82, sat=0.5, gamma=1.12))
        for i, (x, y, r) in enumerate(((300, 260, 70), (520, 820, 50), (1750, 760, 90), (980, 200, 40), (160, 600, 60))):
            fr = A.glow(fr, ((x + 420 * u + 30 * i) % 2100 - 90, y - 25 * t), r, 0.10, (0.6, 0.7, 0.9))
        fr = ASH.draw(fr, t, 0.45, wind=(-200, 0))
        return fr, 0


# A05 7.38–7.85 ECU 双眼睁开 → 7.60 眼中寒光 → 末 4 帧压暗（为片名蓄力），7.73 刀光预光条
class A05(Shot):
    def __init__(self):
        self.path = S('A/eyes', 'dm', crop=(0.16, 0.0, 0.84, 1.0))
    def render(self, t):
        u = self.u(t)
        fr = night((0.005, 0.006, 0.01), (0.012, 0.014, 0.02))
        fr, info = A.place(fr, t, self.path, (960, 470), w=2500, anc=(0.5, 0.80), rim=COLD, rim_amt=0.8, wind=3,
                           grade=dict(expo=0.9, sat=0.6, gamma=1.18), wrap=0.1, breathe=0.0)
        yy = np.arange(H, dtype=np.float32)[:, None, None]       # 顶光：额头/眉骨亮，眼下暗
        fr = fr * (0.55 + 0.6 * np.exp(-((yy - 430) / 260) ** 2))
        ex = [info['to_scr']((0.405, 0.80)), info['to_scr']((0.595, 0.80))]
        g = math.exp(-max(0, t - V(7.60)) / 0.10) * (t >= V(7.60))
        for p in ex: fr = pupil_glint(fr, (p[0], p[1] - 8), 0.9 * g, 1.2)
        k = clamp01((t - (self.t1 - 4 / FPS)) / (4 / FPS))
        fr = fr * (1 - 0.75 * k)
        fr = streak(fr, 520, -100, 2100, (t - V(7.73)) / 0.10, amt=0.7)
        return fr, (3 if g > 0.4 else 0)


# A06 7.85–10.61 片名重击：刀光横斩，「鬼屠 · 第二季」志莽行书炸出，飞火 + 墨溅 + 闪白；8.31 鬼屠印；8.35 副标题
TITLE_HIT = V(7.85)
TITLE_Y = 470
class Title:
    """片名层（A06 屏幕位置 / A07 贴到刀面），保持用户 05:52 定的层级：主标题 + 副标题 + 印。"""
    def __init__(self):
        T.warm('鬼屠第二季', 'xing', 210)
        T.warm('主题曲《谁定正邪》', 'song', 50)
    def layer(self, t, out=0.0, sheen=None):
        k = t - TITLE_HIT
        L = T.Layer()
        xs = [520, 735, 1095, 1290, 1485]                    # 「二」笔画少：第/季向内收 15px，「二」放大 1.15 补视觉重心
        for i, (c, x) in enumerate(zip('鬼屠第二季', xs)):
            e = eout((k - i * 0.035) / 0.22)
            if e <= 0: continue
            sc = (1 + 0.35 * (1 - e)) * (1.15 if c == '二' else 1.0)
            T.place(L, c, x, TITLE_Y, 210, (0.96, 0.94, 0.90), 'xing', alpha=e, scale=sc, blur=6 * (1 - e) + 10 * out)
        L2 = T.Layer()
        se = eout((k - 0.06) / 0.25)
        if se > 0:
            dot = np.zeros((40, 40), np.float32); cv2.circle(dot, (20, 20), 11, 1.0, -1, cv2.LINE_AA)
            L2.paste(dot, 908, TITLE_Y + 4, (0.80, 0.08, 0.06), se)
        sr = eout((k - 0.5) / 0.6)
        if sr > 0:
            sub = '主题曲《谁定正邪》'
            for i, c in enumerate(sub):                                   # 第四棒：38→50px + 两侧细金线
                T.place(L2, c, 960 - (len(sub) - 1) * 34 + i * 68, 648, 50, (0.90, 0.86, 0.78), 'song', alpha=sr, blur=4 * (1 - sr))
            ln = np.zeros((4, int(260 * sr)), np.float32) + 1.0
            if ln.shape[1] > 2:
                L2.paste(ln, 960 - 360 - ln.shape[1] / 2, 650, (1.0, 0.78, 0.40), 0.9 * sr)
                L2.paste(ln, 960 + 360 + ln.shape[1] / 2, 650, (1.0, 0.78, 0.40), 0.9 * sr)
        return L, L2

    @staticmethod
    def cam(t):
        """第十棒（critic_A_r6 P0-1「片名卡全程同一机位」）：片名层自己的机位。
        A06：片名随 crane down 缓推 1.00→1.07 + 上浮 + 微旋；A07a：旗杆遮挡那一下换机位 —— 片名缩到 0.80、
        下沉到城楼垛口前（变成「挂在城上」的世界层），随升镜一起下沉、轻推。返回 (scale, dx, dy, rot)。"""
        def a06(t):
            u = eio(clamp01((t - 7.83) / (10.57 - 7.83)))
            return 1.0 + 0.07 * u, -28 * u, -26 * u, -0.7 * u
        def a07(t):
            u = clamp01((t - 10.57) / (13.30 - 10.57))
            return 0.80 + 0.06 * u, 0.0, 140 + 45 * u, 0.0
        if t < 10.45: return a06(t)
        if t >= 10.71: return a07(t)
        m = eio((t - 10.45) / 0.26)
        a, b = a06(10.45), a07(10.71)
        return tuple(x * (1 - m) + y * m for x, y in zip(a, b))

    @staticmethod
    def _warp(LL, Mx):
        LL.A = cv2.warpAffine(LL.A, Mx, (W, H), flags=cv2.INTER_LINEAR)
        LL.C = cv2.warpAffine(LL.C, Mx, (W, H), flags=cv2.INTER_LINEAR)
        ys, xs = np.nonzero(LL.A > 1e-3)
        LL.bb = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else [W, H, 0, 0]

    def draw(self, fr, t, out=0.0, sheen=None, glow=0.0):
        if t < TITLE_HIT: return fr
        L, L2 = self.layer(t, out)
        sc, dx, dy, rot = self.cam(t)
        Mx = cv2.getRotationMatrix2D((960.0, 520.0), rot, sc); Mx[0, 2] += dx; Mx[1, 2] += dy
        for LL in (L, L2): self._warp(LL, Mx)
        if out > 0:
            for LL in (L, L2):
                nz = cv2.resize(A.ink_noise(77, 256), (W, H))
                LL.A *= np.clip((nz - out * 1.15) * 5 + 0.5, 0, 1)
                if not R6B_OFF('title'): LL.A *= (1 - out) ** 1.2      # r6 第二棒：主字/红点/副标题/金线同一条 alpha 曲线，out=1 全部归零（不留残笔）
        if sheen is not None and 0 <= sheen <= 1:
            xx = np.arange(W, dtype=np.float32)[None]
            band = np.exp(-((xx - (300 + 1350 * sheen)) / 45) ** 2)
            fr = fr + (L.A * band)[..., None] * 1.3 * np.array([1.0, 0.93, 0.8], np.float32)
        fr = T.compose(fr, L, shadow=0.8, shadow_sigma=26, glow=0.22 + glow, glow_sigma=18)
        fr = T.compose(fr, L2, shadow=0.6, glow=0.1)
        ks = t - V(8.31)
        if ks > 0:
            px, py = Mx @ np.array([1665.0, 395.0, 1.0])
            fr = T.stamp_seal(fr, '鬼屠', px, py, 78 * sc, min(1, ks / 0.5), style='yin', seed=3, alpha=0.95 * ((1 - out) if R6B_OFF('title') else (1 - out) ** 2.6))   # 印无噪声溶解，用更陡曲线与主字视觉同步退
        return fr


TITLE = Title()


class A06(Shot):
    def __init__(self):
        self.bg = night((0.015, 0.012, 0.016), (0.10, 0.07, 0.07))
    def render(self, t):
        u = self.u(t); k = t - TITLE_HIT
        fr = self.bg.copy()
        # 第五棒：片名镜不再近静止——血月缓升 + 每拍脉动、云层快速横流（腰斩月盘）、三层山脊强视差、每拍一阵火星、9.68 云内赤色闪电、
        #         地面雾浪横扫；配合 MOVES3 的持续推 + 横移
        bp = sum(math.exp(-max(0.0, t - V(b)) / 0.16) * (t >= V(b)) for b in (8.75, 9.22, 9.68, 10.15))
        cr = eio(u)                                                                       # 第九棒（critic_A_r6 P0-1）：crane down —— 机位下降，近山升起越过远山，血月沉向山脊后
        my = 330 + 70 * cr
        fr = A.moon(fr, 1480, my, 150, 0.95, col=(1.0, 0.42, 0.32), halo=0.6 + 0.3 * bp)          # 血月：被云腰斩
        fr = A.glow(fr, (1480, my), 520, 0.22 + 0.18 * bp, (0.6, 0.12, 0.08))
        fr = A.clouds(fr, t - 7.0, 21, speed=(-150, 0), y0=150, y1=620, amt=0.95, col=(0.10, 0.08, 0.09), light=(1480, my), light_r=380,
                      light_col=(1.0, 0.45, 0.32), thr=0.45)
        lt = t - V(9.68)
        if 0 <= lt < 0.5:                                                                # 云内赤色闪电（一拍）
            env = math.exp(-lt / 0.07) + 0.5 * math.exp(-max(0, lt - 0.12) / 0.06) * (lt >= 0.12)
            fr = A.glow(fr, (420, 260), 520, 0.5 * env, (0.9, 0.35, 0.28), aspect=1.6)
            Lb = np.zeros((H // 2, W // 2), np.float32); r_ = np.random.default_rng(968); x_, y_ = 300.0, 80.0
            for _ in range(14):
                nx, ny = x_ + r_.uniform(-25, 45), y_ + r_.uniform(14, 26)
                cv2.line(Lb, (int(x_), int(y_)), (int(nx), int(ny)), 1.0, 1, cv2.LINE_AA); x_, y_ = nx, ny
            Lb = cv2.resize(Lb, (W, H))
            fr = fr + (Lb * 1.2 + cv2.GaussianBlur(Lb, (0, 0), 10) * 1.5)[..., None] * np.array([1.0, 0.6, 0.5], np.float32) * env
        for i, (by, amp, tone) in enumerate(((760, 230, (0.05, 0.035, 0.04)), (860, 170, (0.025, 0.02, 0.025)), (960, 120, (0.006, 0.005, 0.007)))):
            Di = (90, 200, 340)[i]
            by = int(by + Di * (0.75 - cr))                                               # 远山升 90px、中山 200px、近山 340px（视差）
            fr, _ = A.ridge(fr, by, amp, 60 + i, tone=tone, rim=(0.9, 0.35, 0.25), rim_amt=0.25 - 0.06 * i + 0.15 * bp, dx=-t * (30 + 70 * i))
            fr = fog(fr, t, i, by - 70, by + 50, 0.35, (0.25, 0.17, 0.17), speed=(90 + 80 * i, 0))
        fr = R9.fg_bokeh(fr, t, self.t0, seed=6, n=7, col=(1.0, 0.5, 0.22), vel=(-900, -260), size=(28, 70), amt=0.55)   # 前景焦外火星穿过
        if k >= 0:
            fr = EMB.draw(fr, t, (1.6 * max(0.35, 1 - k / 2.5)) * (1 + 0.8 * bp), wind=(220, -60), burst=(960, TITLE_Y, 900) if k < 0.6 else None, t0=TITLE_HIT if k < 0.6 else None)
        if 0 <= k < 0.14:                                                               # 闪白（全段唯一一处，HANDOFF §1；第三棒压短压轻，片名不被洗掉）
            fr = fr * (1 + 1.1 * (1 - k / 0.14)) + 0.22 * (1 - k / 0.14)
        fr = streak(fr, TITLE_Y + 10, -100, 2100, (t - (TITLE_HIT - 0.06)) / 0.12, ang=-3, amt=1.2)
        ca = 6 if 0 <= k < 0.15 else (2 if 0 <= k < 0.4 else 0)
        return fr, ca


# A08 13.35–15.21 ELS 月下城墙绵延；14.28 云内闪电亮，照出云上太上皇巨影（一拍即逝）
class _A08_OLD(Shot):
    """（第四棒：只借 _wall 给 A07b）第二棒重做：城墙不再是一条平涂垛口——透视纵深的长城（近大远小、垛口按深度缩放、砖缝纹理、月光顶边轮廓、
    三座敌楼带飞檐与灯火），远端爬上山脊蜿蜒入云；前景城墙走道雾；闪电时照出云中太上皇巨影。"""
    VP = (1820, 640)
    def __init__(self):
        self.bg = night((0.012, 0.014, 0.024), (0.08, 0.085, 0.10))
        self.wall, self.face_lit, self.edge, self.towers = self._wall()
    def _wall(self):
        q = 2; h, w = H // q, W // q
        vx, vy = self.VP[0] / q, self.VP[1] / q
        Aw, Ht, Hb = 2300 / q, 300 / q, 300 / q
        xx = np.arange(w, dtype=np.float32)
        z = np.clip(Aw / np.maximum(vx - xx, 1e-3), 1.0, 60)            # 每列深度
        top = vy - Ht / z; bot = vy + Hb / z
        yy = np.arange(h, dtype=np.float32)[:, None]
        m = ((yy >= top[None]) & (yy <= bot[None])).astype(np.float32) * (xx[None] < vx - 2)
        # 垛口：世界间距 0.18（深度单位），高 0.06*Ht
        s_ = z - 1
        mer = (np.mod(s_ * 5.5, 1.0) < 0.55)
        mt = top - (Ht * 0.10) / z
        m = np.maximum(m, ((yy >= mt[None]) & (yy < top[None]) & mer[None]).astype(np.float32) * (xx[None] < vx - 2))
        # 砖缝：横缝 22 行，竖缝随行错位
        v = np.clip((yy - top[None]) / np.maximum(bot - top, 1e-3)[None], 0, 1)
        row = np.floor(v * 22)
        jx = np.mod(s_[None] * 14 + 0.5 * np.mod(row, 2), 1.0)
        mort = ((np.mod(v * 22, 1.0) < 0.10) | (jx < 0.07)).astype(np.float32)
        fade = np.clip((z - 1) / 10, 0, 1)[None]                           # 远处砖纹平均掉
        nz = cv2.resize(A.tex(81, 512, 6, 6), (w, h))
        stain = 0.75 + 0.5 * nz * (1 - v * 0.5)
        face = (1 - 0.55 * mort * (1 - fade)) * stain * (1 - 0.6 * v) * m    # 月光自上而下衰减
        # 顶边月光轮廓（含垛口）
        e = np.clip(m - cv2.erode(m, np.ones((3, 3), np.uint8)), 0, 1)
        e = e * (yy < (top[None] + 6))
        # 敌楼
        towers = []
        for zt in (2.4, 5.2, 11.0):
            xt = vx - Aw / zt; sc = 1 / zt
            towers.append((xt * q, top[int(np.clip(xt, 0, w - 1))] * q, sc))
        m = cv2.resize(cv2.GaussianBlur(m, (0, 0), 0.6), (W, H)); face = cv2.resize(face, (W, H)); e = cv2.resize(e, (W, H))
        Tm = np.zeros((H, W), np.float32); Te = np.zeros((H, W), np.float32); wins = []
        for (xt, yt, sc) in towers:
            S_ = 2300 * sc
            bw, bh = 0.30 * S_, 0.20 * S_
            x0, x1 = int(xt - bw / 2), int(xt + bw / 2)
            cv2.rectangle(Tm, (x0, int(yt - bh)), (x1, int(yt + 4)), 1.0, -1)
            for k, (rw, ry, rh) in enumerate(((0.44, bh, 0.05), (0.34, bh + 0.11 * S_, 0.045))):
                y0 = int(yt - ry); W2 = rw * S_ / 2
                pts = np.array([(xt - W2 - 0.03 * S_, y0 + 0.012 * S_), (xt - W2 * 0.82, y0 - rh * S_ * 0.35), (xt - W2 * 0.55, y0 - rh * S_),
                                (xt + W2 * 0.55, y0 - rh * S_), (xt + W2 * 0.82, y0 - rh * S_ * 0.35), (xt + W2 + 0.03 * S_, y0 + 0.012 * S_)], np.int32)
                cv2.fillPoly(Tm, [pts], 1.0, cv2.LINE_AA)
                cv2.polylines(Te, [pts[:4]], False, 1.0, max(1, int(3 * sc * 1.5)), cv2.LINE_AA)
                if k == 0:
                    cv2.rectangle(Tm, (int(xt - 0.11 * S_), int(y0 - 0.11 * S_)), (int(xt + 0.11 * S_), y0), 1.0, -1)
            for j in (-1, 0, 1):                                            # 箭窗（灯火位置）
                wins.append((xt + j * bw * 0.28, yt - bh * 0.55, sc))
        return (m, Tm), face, (e, Te), towers + wins
    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        env = 0.0
        for t0, a in ((V(14.28), 1.0), (V(14.28) + 0.12, 0.6), (V(14.28) + 0.3, 0.4)):
            if t >= t0: env = max(env, a * math.exp(-(t - t0) / 0.09))
        if env > 0.02 or (V(14.28) - 0.05 < t < V(14.28) + 0.9):            # 巨影：闪电时从云里显出
            lit = np.clip(env * 2, 0, 1)
            fr = A.glow(fr, (1000, 380), 560, 0.9 * lit, (0.75, 0.8, 0.95))
            # 第二棒：改用 tsh_raise 举手剪影（预告 V16 召印；S011/backlit 只留给 V07）
            fr, _ = A.place(fr, t, S('A/tsh_raise', 'dm'), (980, 980), h=980, look='sil', rim=(0.85, 0.9, 1.0), rim_amt=5.0, wind=5,
                            alpha=0.12 + 0.8 * lit, defocus=2.0)
        fr = A.moon(fr, 1500, 230, 62, 0.9, halo=0.5)
        fr = A.clouds(fr, t, 31, speed=(25, 0), y0=120, y1=600, amt=0.9, col=(0.13, 0.14, 0.18), light=(1000, 330), light_r=600,
                      light_col=(0.9, 0.92, 1.0), thr=0.44)
        if env > 0: fr = fr + env * 0.18 * np.array([0.8, 0.85, 1.0], np.float32)
        # 远山 + 山脊上蜿蜒的城墙（细线 + 垛点）
        fr, rl = A.ridge(fr, 700, 150, 71, tone=(0.035, 0.04, 0.055), rim=(0.5, 0.56, 0.72), rim_amt=0.3, dx=-u * 15, fogcol=(0.10, 0.11, 0.14), fog=0.6)
        Lw = np.zeros((H, W), np.float32)
        xs = np.arange(1100, W, 3); ys = rl[xs] - 3
        cv2.polylines(Lw, [np.stack([xs, ys], 1).astype(np.int32)], False, 1.0, 3, cv2.LINE_AA)
        for x in range(1100, W, 9): cv2.line(Lw, (x, int(rl[x] - 4)), (x, int(rl[x] - 7)), 1.0, 2)
        fr = fr * (1 - Lw[..., None] * 0.9) + Lw[..., None] * np.array([0.30, 0.34, 0.45], np.float32) * (0.5 + env)
        fr = fog(fr, t, 1, 560, 760, 0.45, (0.20, 0.22, 0.28), speed=(-20, 0))
        # 近处城墙
        (m, Tm), face, (e, Te), towers = self.wall, self.face_lit, self.edge, self.towers
        k = 1 + 1.5 * env
        col = np.array([0.050, 0.056, 0.075], np.float32) * k
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        fr = fr * (1 - np.clip((yy - 700) / 120, 0, 1) * 0.85)                 # 墙下大地压暗
        fr = fr * (1 - m[..., None]) + (face[..., None] * col + 0.006) * m[..., None]
        fr = fr * (1 - Tm[..., None]) + Tm[..., None] * (0.008 + 0.03 * env)
        fr = fr + (e + Te)[..., None] * np.array([0.55, 0.62, 0.82], np.float32) * (0.45 + 1.4 * env)
        for (x, y, sc) in towers[3:]:                                       # 敌楼箭窗灯火（微颤）
            fl = 0.8 + 0.2 * math.sin(t * 17 + x)
            fr = A.glow(fr, (x, y), max(3, 26 * sc * 1.2), 1.2 * fl, (1.0, 0.58, 0.25))
        fr = A.glow(fr, towers[3][:2], 220, 0.10, (1.0, 0.55, 0.25))
        fr = fog(fr, t, 0, 820, 1000, 0.3, (0.16, 0.18, 0.23), speed=(-45, 0))
        fr = ASH.draw(fr, t, 0.5 * clamp01(1 - u * 1.5), wind=(220, -60))
        return fr, (3 if env > 0.6 else 0)


# A07a 10.61–11.98 雨夜城楼大仰角（第四棒新镜，替换原 A07 刀面片名）：前景旗杆 + 大旗擦过左侧（虚焦），城楼占上半——两重飞檐、
#      檐下红灯笼、垛口月光边；城门洞下主角极小的背影；推轨。片名是 A06 延续下来的屏幕层（11.52 扫光）。
def _tower_masks():
    m = np.zeros((H, W), np.float32); roof = np.zeros((H, W), np.float32); arch = np.zeros((H, W), np.float32)
    cv2.fillPoly(m, [np.array([(300, 560), (1620, 560), (2250, H), (-330, H)], np.int32)], 1.0, cv2.LINE_AA)
    for x in range(300, 1620, 66): cv2.rectangle(m, (x, 522), (x + 36, 562), 1.0, -1)
    cv2.rectangle(m, (560, 330), (1360, 560), 1.0, -1)
    cv2.rectangle(m, (690, 210), (1230, 262), 1.0, -1)
    for pts in ([(360, 362), (450, 318), (590, 262), (1330, 262), (1470, 318), (1560, 362), (1540, 376), (380, 376)],
                [(540, 236), (620, 196), (720, 150), (1200, 150), (1300, 196), (1380, 236), (1360, 248), (560, 248)]):
        cv2.fillPoly(roof, [np.array(pts, np.int32)], 1.0, cv2.LINE_AA)
    cv2.ellipse(arch, (960, 880), (170, 200), 0, 180, 360, 1.0, -1, cv2.LINE_AA)
    cv2.rectangle(arch, (790, 880), (1130, H), 1.0, -1)
    return m, roof, arch


class A07a(Shot):
    def __init__(self):
        self.bg = night((0.014, 0.017, 0.03), (0.07, 0.075, 0.095))
        self.m, self.roof, self.arch = _tower_masks()
        self.tex = cv2.resize(A.tex(131, 512, 6, 6), (W, H))
        r = np.random.default_rng(3)
        self.wins = [(x, 450) for x in range(620, 1340, 90)] + [(x, 236) for x in range(740, 1220, 96)]
        self.lanterns = [(450, 410), (1470, 410), (640, 280), (1280, 280)]
    def render(self, t):
        u = self.u(t)
        env = 0.0                                                                                     # 第五棒：11.98 / 12.89 云内闪电照亮城楼
        for t0_, a_ in ((V(11.98), 1.0), (V(11.98) + 0.13, 0.55), (V(12.89), 0.6)):
            if t >= t0_: env = max(env, a_ * math.exp(-(t - t0_) / 0.10))
        fr = self.bg.copy() * (1 + 2.5 * env)
        fr = A.glow(fr, (960, 120), 700, 0.22 + 0.9 * env, (0.45, 0.52, 0.7))
        fr = A.glow(fr, (960, 200), 900, 0.18, (0.4, 0.46, 0.62), aspect=0.5)            # 城楼后天光：让飞檐轮廓从夜空里分出来
        fr = A.clouds(fr, t, 91, speed=(80, 10), y0=0, y1=420, amt=0.9, col=(0.10, 0.11, 0.14), dark=0.7, thr=0.42,
                      light=(960, 120), light_r=800, light_col=(0.6, 0.66, 0.85))
        fr = fog(fr, t, 0, 260, 600, 0.35, (0.16, 0.18, 0.23), speed=(50, 0))
        yy = np.arange(H, dtype=np.float32)[:, None]
        face = (0.75 + 0.5 * self.tex) * (1 - 0.55 * np.clip((yy - 560) / 520, 0, 1))          # 墙面：顶亮下暗 + 湿渍
        m, roof, arch = self.m, self.roof, self.arch
        fr = fr * (1 - m[..., None]) + (face * m)[..., None] * np.array([0.045, 0.05, 0.068], np.float32) * (1 + 3.0 * env)
        fr = fr * (1 - roof[..., None]) + roof[..., None] * 0.006
        e = np.clip(np.maximum(m, roof) - cv2.erode(np.maximum(m, roof), np.ones((3, 3), np.uint8)), 0, 1) * (yy < 600)
        fr = fr + cv2.GaussianBlur(e, (0, 0), 1.0)[..., None] * np.array([0.55, 0.62, 0.82], np.float32) * (0.7 + 2.5 * env)
        fr = fr * (1 - arch[..., None]) + arch[..., None] * np.array([0.03, 0.025, 0.02], np.float32)
        fr = A.glow(fr, (960, 940), 260, 0.25, (1.0, 0.6, 0.3), aspect=0.7)                       # 门洞深处火光
        for i, (x, y) in enumerate(self.wins):
            fl = 0.75 + 0.25 * math.sin(t * 13 + i * 1.7)
            fr = A.glow(fr, (x, y), 9, 0.9 * fl, (1.0, 0.6, 0.28), aspect=0.8)
        for i, (x, y) in enumerate(self.lanterns):                                                   # 檐下红灯笼（随风摆）
            sw = 10 * math.sin(t * 2.6 + i)
            cv2.line(fr, (int(x), int(y - 46)), (int(x + sw * 0.5), int(y - 26)), (0.02, 0.02, 0.02), 2, cv2.LINE_AA)
            Ll = np.zeros((H, W), np.float32)                                                       # 第五棒：灯笼实体（腰鼓形 + 竹骨 + 顶底黑盖）
            cv2.ellipse(Ll, (int(x + sw), int(y)), (30, 38), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
            rib = np.zeros_like(Ll)
            for dx_ in (-18, -6, 6, 18):
                cv2.ellipse(rib, (int(x + sw), int(y)), (abs(dx_) + 1, 38), 0, 0, 360, 1.0, 2, cv2.LINE_AA)
            fr = fr * (1 - Ll[..., None]) + Ll[..., None] * np.array([0.95, 0.18, 0.07], np.float32) * (1 - 0.55 * (rib * Ll)[..., None])
            for yy_ in (y - 40, y + 40):
                cv2.rectangle(fr, (int(x + sw - 14), int(yy_ - 4)), (int(x + sw + 14), int(yy_ + 4)), (0.015, 0.012, 0.01), -1)
            cv2.line(fr, (int(x + sw), int(y + 44)), (int(x + sw + 2), int(y + 70)), (0.6, 0.08, 0.04), 2, cv2.LINE_AA)
            fr = A.glow(fr, (x + sw, y), 22, 0.5, (1.0, 0.45, 0.2), aspect=1.25)
            fr = A.glow(fr, (x + sw, y), 110, 0.28, (1.0, 0.3, 0.12))
        for k, px in enumerate((360, 1560)):                                                        # 城头旗：杆 + 风中旗面
            top = 330; cv2.line(fr, (px, 540), (px, top), (0.01, 0.01, 0.012), 5, cv2.LINE_AA)
            d = 1 if k == 0 else -1
            pts = [(px + d * 180 * s, top + 8 + 14 * math.sin(t * 7 + s * 5 + k)) for s in np.linspace(0, 1, 9)]
            pts += [(px + d * 180 * s, top + 100 + 14 * math.sin(t * 7 + s * 5 + k + 0.6)) for s in np.linspace(1, 0, 9)]
            Lf = np.zeros((H, W), np.float32); cv2.fillPoly(Lf, [np.array(pts, np.int32)], 1.0, cv2.LINE_AA)
            fr = fr * (1 - Lf[..., None]) + Lf[..., None] * np.array([0.16, 0.02, 0.02], np.float32)
        fr, _ = A.place(fr, t, S('A/back_walk'), (960 + 30 * math.sin(t * 2.4), 1030 - 60 * eio(u)), h=210 - 50 * eio(u), look='sil',
                        rim=(1.0, 0.65, 0.35), rim_amt=3.0 + 4 * env, wind=6)
        fr = RAIN.draw(fr, t, 1.0, angle=10, light=(960, 120), layers=(0, 1))
        fr = fog(fr, t, 1, 820, 1060, 0.4, (0.18, 0.2, 0.25), speed=(-60, 0))
        # 前景：虚焦旗杆擦过左侧（推轨视差）；第六棒删掉左上那面读不出的平涂大旗（critic_A_r3 P1-5）
        Lp = np.zeros((H // 2, W // 2), np.float32)
        px = (260 - 420 * u) / 2
        cv2.rectangle(Lp, (int(px - 16), 0), (int(px + 16), H // 2), 1.0, -1)
        Lp = cv2.resize(cv2.GaussianBlur(Lp, (0, 0), 7), (W, H))[..., None]
        fr = fr * (1 - Lp * 0.96) + Lp * np.array([0.02, 0.02, 0.025], np.float32)
        # 片名区：城楼压暗 40% + 虚焦，给「鬼屠 · 第二季」留一块干净暗区（闪电时仍能照出轮廓）
        if not hasattr(self, 'tz'):
            tz = np.zeros((H // 4, W // 4), np.float32)
            cv2.ellipse(tz, (240, 118), (230, 70), 0, 0, 360, 1.0, -1)
            self.tz = cv2.resize(cv2.GaussianBlur(tz, (0, 0), 14), (W, H))[..., None]
        fr = fr * (1 - self.tz) + cv2.GaussianBlur(fr, (0, 0), 6) * self.tz * (0.6 + 0.3 * env)
        fr = RAIN.draw(fr, t, 0.8, angle=10, layers=(2,))
        return fr, 0


# A07b 11.98–13.35 ELS 透视城墙（第四棒新镜，原 A08 城墙移来，去月）：长城近大远小蜿蜒入雨雾，敌楼灯火；斜雨 + 三层雾；13.35 片名化灰
class A07b(Shot):
    VP = (1820, 640)
    def __init__(self):
        self.bg = night((0.012, 0.014, 0.024), (0.075, 0.08, 0.095))
        self.wall, self.face_lit, self.edge, self.towers = _A08_OLD._wall(self)
    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        fr = A.glow(fr, (1300, 260), 700, 0.25, (0.5, 0.56, 0.72))
        fr = A.clouds(fr, t, 31, speed=(60, 0), y0=60, y1=600, amt=0.95, col=(0.12, 0.13, 0.17), light=(1300, 260), light_r=700,
                      light_col=(0.75, 0.8, 0.95), thr=0.42)
        fr, rl = A.ridge(fr, 700, 150, 71, tone=(0.035, 0.04, 0.055), rim=(0.5, 0.56, 0.72), rim_amt=0.25, dx=-u * 40, fogcol=(0.10, 0.11, 0.14), fog=0.6)
        fr = fog(fr, t, 1, 520, 760, 0.55, (0.20, 0.22, 0.28), speed=(-40, 0))
        (m, Tm), face, (e, Te), towers = self.wall, self.face_lit, self.edge, self.towers
        col = np.array([0.050, 0.056, 0.075], np.float32)
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        fr = fr * (1 - np.clip((yy - 700) / 120, 0, 1) * 0.85)
        fr = fr * (1 - m[..., None]) + (face[..., None] * col + 0.006) * m[..., None]
        fr = fr * (1 - Tm[..., None]) + Tm[..., None] * 0.01
        fr = fr + (e + Te)[..., None] * np.array([0.55, 0.62, 0.82], np.float32) * 0.5
        for (x, y, sc) in towers[3:]:
            fl = 0.8 + 0.2 * math.sin(t * 17 + x)
            fr = A.glow(fr, (x, y), max(3, 26 * sc * 1.2), 1.2 * fl, (1.0, 0.58, 0.25))
            fr = A.glow(fr, (x, y + 40 * sc), max(8, 120 * sc), 0.12 * fl, (1.0, 0.5, 0.2))
        fr = fog(fr, t, 2, 640, 900, 0.4, (0.17, 0.19, 0.24), speed=(70, 0))
        fr = RAIN.draw(fr, t, 1.0, angle=14, light=(1300, 260), layers=(0, 1, 2))
        fr = fog(fr, t, 0, 820, 1060, 0.45, (0.16, 0.18, 0.23), speed=(-110, 0))
        return fr, 0


# A08 13.35–15.21 MS 背影推进 + 城门合上（第四棒重做）：门洞深处冷光，两扇包铁城门向中合拢；鬼屠背影走向门前、越走越远；
#      14.28 闪电从门缝外劈亮；15.05 合死只剩一线门缝 → a_seam 门缝里开出 V01
class A08(Shot):
    def __init__(self):
        self.tex = cv2.resize(A.tex(141, 512, 5, 6), (W, H)); self.tex2 = cv2.resize(A.tex(142, 512, 30, 3), (W, H))
    def close(self, t): return eio((t - self.t0) / (V(15.05) - self.t0))
    def render(self, t):
        return self.render_r5(t) if R5.ON['walkout'] else self.render_old(t)
    def render_r5(self, t):
        """第五轮 2：主角真的走出城门 —— 门槛 y=905；门内（近）→ 跨过门槛 → 门外大道上越走越远，
        城门随后在他身后合上（ease-in 先慢后快），14.28 闪电把门外的他打成剪影，15.05 合成一线门缝。"""
        q = clamp01((t - self.t0) / (V(15.05) - self.t0)); c = q ** 2.2
        env = 0.0
        for t0, a in ((V(14.28), 1.0), (V(14.28) + 0.12, 0.6), (V(14.28) + 0.3, 0.4)):
            if t >= t0: env = max(env, a * math.exp(-(t - t0) / 0.09))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        TH, HZ = 905.0, 742.0                                              # 门槛线 / 门外地平线
        # 门洞外：冷雾天光 + 门外大道（地平线 742，路面湿反光向远处收窄）
        fr = A.vgrad((0.10, 0.12, 0.16), (0.05, 0.055, 0.07)) * (1 + 3 * env)
        fr = A.glow(fr, (960, 640), 460, 0.6 + 2.0 * env, (0.6, 0.7, 0.95), aspect=0.6)
        gnd = np.clip((yy - HZ) / 6, 0, 1)
        dz = np.clip((yy - HZ) / (TH - HZ), 0, 1)
        road = np.exp(-((xx - 960) / (30 + 420 * dz)) ** 2)
        sky = fr[int(HZ) - 6:int(HZ) - 5].copy()                                    # 湿路面反射地平线天光：近地平线亮、向门槛渐暗 → 读成往远处去的大道
        refl = (0.85 - 0.62 * dz) * (0.75 + 0.5 * self.tex2)
        gcol = sky * refl[..., None] + road[..., None] * np.array([0.05, 0.06, 0.085], np.float32) * (1 + 2 * env) * (1 - 0.4 * dz[..., None])
        gcol = gcol * (1 - 0.35 * ((np.mod((xx - 960) / (0.25 + dz), 260) < 3) * dz)[..., None])
        fr = fr * (1 - gnd[..., None]) + gcol * gnd[..., None]
        fr = fr + np.exp(-((yy - HZ) / 3) ** 2)[..., None] * np.array([0.25, 0.3, 0.42], np.float32) * (0.3 + 1.2 * env)
        fr = RAIN.draw(fr, t, 0.8, angle=6, light=(960, 400), layers=(0,))
        # 主角：z = 1 + 2.6 s（等速往纵深走）；s≈0.31 跨过门槛
        s = clamp01((t - self.t0) / (V(14.98) - self.t0))
        z = 1 + 2.6 * s
        hh = 760 / z; by = HZ + 298 / z + 7 * abs(math.sin(t * 6.2)) / z
        outside = by < TH - 2
        def hero(fr):
            fr, _ = A.place(fr, t, S('A/back_walk'), (960 + 22 * math.sin(t * 3.1) / z, by), h=hh, rim=COLD, rim_amt=3.0 + 6 * env,
                            rim_dir=(0, -1), grade=dict(expo=0.6 * (1 - 0.75 * env) if outside else 0.6, sat=0.5, gamma=1.2), wind=7)
            return fr
        if outside:                                                        # 门外：先画人，再画门/墙 → 合门把他挡在外面
            sh = np.exp(-(((xx - 960) / (90 / z)) ** 2 + ((yy - by) / (8 / z)) ** 2))
            fr = fr * (1 - 0.6 * sh[..., None])
            fr = hero(fr)
        # 城门两扇（门洞 x 520–1400，门底 = 门槛）
        gx0, gx1 = 520, 1400; half = (gx1 - gx0) / 2
        wL = half * (0.12 + 0.88 * c)
        door = (((xx < gx0 + wL) & (xx >= gx0)) | ((xx > gx1 - wL) & (xx <= gx1))) & (yy < TH)
        door = door.astype(np.float32)
        plank = 0.75 + 0.35 * self.tex2 + 0.15 * (np.mod(xx, 70) < 3)
        studs = ((np.mod(xx - gx0, 88) - 44) ** 2 + (np.mod(yy, 96) - 48) ** 2 < 49).astype(np.float32)
        dcol = (plank * (0.5 + 0.5 * self.tex))[..., None] * np.array([0.05, 0.035, 0.025], np.float32) * (1 + 2 * env)
        dcol = dcol + studs[..., None] * np.array([0.10, 0.09, 0.08], np.float32) * (1 + 3 * env)
        fr = fr * (1 - door[..., None]) + dcol * door[..., None]
        if R6B_OFF('doorline'):
            seamL = np.exp(-((xx - (gx0 + wL)) / 4) ** 2); seamR = np.exp(-((xx - (gx1 - wL)) / 4) ** 2); _sk = 1.0
        else:                                                              # r6 第二棒 #2：门板内沿不再是贯通的亮白硬线 → 羽化 3px + 降亮 35%，上下两端渐隐（与拱券漫射统一）
            seamL = np.exp(-((xx - (gx0 + wL)) / 7) ** 2); seamR = np.exp(-((xx - (gx1 - wL)) / 7) ** 2)
            _sk = 0.65 * np.clip((yy - 200) / 220, 0, 1) * (0.55 + 0.45 * np.clip((TH - yy) / 120, 0, 1)) * (0.8 + 0.4 * self.tex2)
        fr = fr + ((seamL + seamR) * _sk * (yy > 200) * (yy < TH))[..., None] * np.array([0.6, 0.7, 1.0], np.float32) * (0.8 + 3 * env)
        # 城墙 + 拱门
        wall = np.ones((H, W), np.float32)
        hole = ((((xx - 960) / 440) ** 2 + ((yy - 470) / 300) ** 2 < 1) & (yy < 470)) | ((xx > gx0) & (xx < gx1) & (yy >= 470)) | (yy >= TH)
        wall[hole] = 0; wall = cv2.GaussianBlur(wall, (0, 0), 1.2)
        brick = (0.7 + 0.5 * self.tex) * (1 - 0.4 * ((np.mod(yy, 60) < 3) | (np.mod(xx + 60 * (np.mod(yy // 60, 2)), 120) < 3)))
        wcol = brick[..., None] * np.array([0.035, 0.038, 0.05], np.float32) * (1 + 2.5 * env)
        fr = fr * (1 - wall[..., None]) + wcol * wall[..., None]
        if 'archline' in os.environ.get('A_R6_OFF', ''):
            ed = np.clip(cv2.dilate(1 - wall, np.ones((5, 5), np.uint8)) - (1 - wall), 0, 1) * (yy < TH - 4)
            fr = fr + ed[..., None] * np.array([0.5, 0.6, 0.85], np.float32) * (0.5 + 2 * env)
        else:                                                              # r6 #2 补：拱门不再是一圈 5px 冷白描线（读成线稿）→ 门外天光溢到拱券石面上的柔和漫射（向墙内衰减 + 砖纹调制）
            if not hasattr(self, 'spill'):
                op = (1 - wall)
                self.spill = (cv2.GaussianBlur(op, (0, 0), 14) * wall * (yy < TH - 4)).astype(np.float32)
            fr = fr + (self.spill * brick * 0.55)[..., None] * np.array([0.5, 0.6, 0.85], np.float32) * (0.5 + 2 * env)
        # 门内石板地（门槛以下）+ 门槛石 + 门缝光在湿地上的竖条倒影
        fl = np.clip((yy - TH) / 3, 0, 1)
        slab = (0.7 + 0.5 * self.tex) * (1 - 0.35 * ((np.mod(np.maximum(yy - TH, 0), 46 + np.maximum(yy - TH, 0) * 0.3) < 2) | (np.mod((xx - 960) / (1 + np.maximum(yy - TH, 0) / 120), 150) < 2)))
        fcol = slab[..., None] * np.array([0.03, 0.033, 0.042], np.float32) * (1 + 2 * env)
        fr = fr * (1 - fl[..., None]) + fcol * fl[..., None]
        sill = np.exp(-((yy - TH - 4) / 4) ** 2) * (xx > gx0 - 40) * (xx < gx1 + 40)
        fr = fr * (1 - 0.5 * sill[..., None]) + sill[..., None] * np.array([0.12, 0.13, 0.16], np.float32) * (1 + 3 * env)
        gap = max(2.0, (gx1 - gx0) - 2 * wL)
        fr = fr + (fl * np.exp(-((xx - 960) / (gap * 0.45)) ** 2) * np.exp(-(yy - TH) / 160))[..., None] * np.array([0.22, 0.27, 0.40], np.float32) * (1 + 2 * env)
        if not outside:
            fr = hero(fr)
        fr = RAIN.draw(fr, t, 0.9, angle=6, light=(960, 400), layers=(1, 2))
        fr = fog(fr, t, 0, 880, 1060, 0.30, (0.16, 0.18, 0.23), speed=(-45, 0))
        return fr, (3 if env > 0.6 else 0)
    def render_old(self, t):
        u = self.u(t)
        env = 0.0
        for t0, a in ((V(14.28), 1.0), (V(14.28) + 0.12, 0.6), (V(14.28) + 0.3, 0.4)):
            if t >= t0: env = max(env, a * math.exp(-(t - t0) / 0.09))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        # 门洞外：冷雾光 + 远处街道
        fr = A.vgrad((0.10, 0.12, 0.16), (0.04, 0.045, 0.06)) * (1 + 3 * env)
        fr = A.glow(fr, (960, 500), 420, 0.6 + 2.0 * env, (0.6, 0.7, 0.95))
        fr = RAIN.draw(fr, t, 0.8, angle=6, light=(960, 400), layers=(0,))
        # 城门两扇（门洞 x 520–1400）
        c = self.close(t); gx0, gx1 = 520, 1400; half = (gx1 - gx0) / 2
        wL = half * (0.18 + 0.82 * c)
        door = ((xx < gx0 + wL) & (xx >= gx0)) | ((xx > gx1 - wL) & (xx <= gx1))
        door = door.astype(np.float32)
        plank = 0.75 + 0.35 * self.tex2 + 0.15 * (np.mod(xx, 70) < 3)
        studs = ((np.mod(xx - gx0, 88) - 44) ** 2 + (np.mod(yy, 96) - 48) ** 2 < 49).astype(np.float32)
        dcol = (plank * (0.5 + 0.5 * self.tex))[..., None] * np.array([0.05, 0.035, 0.025], np.float32) * (1 + 2 * env)
        dcol = dcol + studs[..., None] * np.array([0.10, 0.09, 0.08], np.float32) * (1 + 3 * env)
        fr = fr * (1 - door[..., None]) + dcol * door[..., None]
        seamL = np.exp(-((xx - (gx0 + wL)) / 4) ** 2); seamR = np.exp(-((xx - (gx1 - wL)) / 4) ** 2)
        fr = fr + ((seamL + seamR) * (yy > 200))[..., None] * np.array([0.6, 0.7, 1.0], np.float32) * (0.8 + 3 * env)
        # 城墙 + 拱门（门洞外沿）
        wall = np.ones((H, W), np.float32)
        hole = ((((xx - 960) / 440) ** 2 + ((yy - 470) / 300) ** 2 < 1) & (yy < 470)) | ((xx > gx0) & (xx < gx1) & (yy >= 470))
        wall[hole] = 0; wall = cv2.GaussianBlur(wall, (0, 0), 1.2)
        brick = (0.7 + 0.5 * self.tex) * (1 - 0.4 * ((np.mod(yy, 60) < 3) | (np.mod(xx + 60 * (np.mod(yy // 60, 2)), 120) < 3)))
        wcol = brick[..., None] * np.array([0.035, 0.038, 0.05], np.float32) * (1 + 2.5 * env)
        fr = fr * (1 - wall[..., None]) + wcol * wall[..., None]
        ed = np.clip(cv2.dilate(1 - wall, np.ones((5, 5), np.uint8)) - (1 - wall), 0, 1)
        fr = fr + ed[..., None] * np.array([0.5, 0.6, 0.85], np.float32) * (0.5 + 2 * env)
        # 湿地面倒影：门缝光的竖条
        g = np.clip((yy - 900) / 30, 0, 1)
        fr = fr * (1 - g[..., None] * 0.5) + (g * np.exp(-((xx - 960) / (40 + 300 * (1 - c))) ** 2))[..., None] * np.array([0.25, 0.3, 0.45], np.float32) * (1 + 2 * env)
        # 主角背影：走向门前（越走越小）
        hh = 760 - 170 * eio(u); by = 1040 - 70 * eio(u)
        fr, _ = A.place(fr, t, S('A/back_walk'), (960 + 25 * math.sin(t * 3.0), by), h=hh, rim=COLD, rim_amt=3.0 + 6 * env,
                        rim_dir=(0, -1), grade=dict(expo=0.6, sat=0.5, gamma=1.2), wind=9)
        fr = RAIN.draw(fr, t, 0.9, angle=6, light=(960, 400), layers=(1, 2))
        fr = fog(fr, t, 0, 860, 1060, 0.35, (0.16, 0.18, 0.23), speed=(-45, 0))
        return fr, (3 if env > 0.6 else 0)


_SILM = {}
def _sil_mask(t):
    k = int(t * 10)
    if k not in _SILM:
        _, info = A.place(np.zeros((H, W, 3), np.float32), t, S('S011/backlit'), (1200, 1040), h=1050, wind=5)
        _SILM.clear(); _SILM[k] = cv2.GaussianBlur(info['A'], (0, 0), 4)[..., None]
    return _SILM[k]


# =====================================================================================
# 主歌一
# V01 15.21–17.00 ECU 雨打刃口微距（第四棒：程序横刀 → blade_rain 精灵刃身，有钢纹/水珠；斜透视指向画面深处），乌云压低逼近刃口；
#     雨点落刃溅起；16.86「刀」一线刀光沿刃走
class V01(Shot):
    def __init__(self):
        self.path = S('A/blade_rain', 'dm', crop=(0.22, 0.69, 1.0, 1.0))
        r = np.random.default_rng(15); self.drops = [(r.uniform(0.15, 0.95), r.uniform(0, 1.8)) for _ in range(26)]
    def render(self, t):
        u = self.u(t)
        fr = night((0.006, 0.007, 0.012), (0.04, 0.045, 0.06))
        fr = A.glow(fr, (1500, 860), 520, 0.25, (0.45, 0.52, 0.7))
        cy = 330 + 230 * eio(u)
        fr = A.clouds(fr, t, 41, speed=(30, 50), y0=100, y1=int(cy + 160), amt=1.0, col=(0.05, 0.055, 0.07), dark=0.85, thr=0.38,
                      light=(1500, 860), light_r=700, light_col=(0.5, 0.55, 0.7))
        fr = RAIN.draw(fr, t, 0.8, angle=8, light=(1500, 300), layers=(0, 1))
        fr, info = A.place(fr, t, self.path, (1080 - 90 * u, 700), w=2500 * (1 + 0.07 * u), anc=(0.5, 0.5), rot=-8, rim=COLD, rim_amt=1.6,
                           rim_dir=(0.3, -1.0), grade=dict(expo=0.95, sat=0.35, gamma=1.08), wind=0, breathe=0.0)
        P0 = info['to_scr']((0.10, 0.80)); P1 = info['to_scr']((0.98, 0.80))
        for i, (s, ph) in enumerate(self.drops):                         # 雨点打刃：小冠状溅射
            k = (t * 1.3 + ph) % 1.8
            if k < 0.18:
                x = P0[0] + (P1[0] - P0[0]) * s; y = P0[1] + (P1[1] - P0[1]) * s - 40
                fr = A.glow(fr, (x, y), 5 + 30 * k, 0.9 * (1 - k / 0.18), (0.8, 0.88, 1.0), aspect=0.45)
        fr = ASH.draw(fr, t, 0.4, wind=(-30, 90))
        fr = RAIN.draw(fr, t, 0.7, angle=8, layers=(2,))
        a = t - CT(0, 5)
        if a >= 0:
            fr = streak(fr, P0[1] - 40, P0[0], P1[0], a / 0.12, amt=1.3, ang=math.degrees(math.atan2(P1[1] - P0[1], P1[0] - P0[0])))
        return fr, (4 if 0 <= a < 0.1 else 0)


# V02 17.00–17.95 CU 低机位：靴子踏进水洼，倒影碎开，雨（「之上」收尾，独行）
class V02(Shot):
    def __init__(self):
        self.spl = fx2.Splashes(4) if hasattr(fx2, 'Splashes') else None
    def render(self, t):
        u = self.u(t)
        fr = night((0.02, 0.022, 0.03), (0.035, 0.04, 0.05), y1=700)
        fr = A.glow(fr, (1300, 300), 400, 0.35, (0.5, 0.58, 0.78))
        fr = RAIN.draw(fr, t, 0.9, angle=8, light=(1300, 300), layers=(0, 1))
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        ground = np.clip((yy - 760) / 30, 0, 1)
        fr = fr * (1 - ground * 0.85)
        # 第十一棒（critic_A_r7 P1-3「V02 近乎静止」）：人真的在走 —— 步伐起伏（每 0.47s 一步）+ 横移 260px + 走近放大 8% + 衣摆风摆加大；
        #   落脚时靴面雨溅（17.46 主溅 + 每步小溅）
        e2 = eio(u); ph2 = (t - self.t0) / 0.47
        dy = -20 * math.sin(math.pi * clamp01((t - self.t0) / 0.5)) - 10 * abs(math.sin(math.pi * ph2))
        bx = 880 + 260 * e2
        fr, info = A.place(fr, t, S('A/boots'), (bx, 830 + dy), h=900 * (1 + 0.08 * e2), anc=(0.5, 0.92), rim=COLD, rim_amt=3.0,
                           grade=dict(expo=0.7, sat=0.6), wind=18, rot=1.5 * math.sin(math.pi * ph2))
        refl = cv2.flip(fr[460:760], 0)                                                 # 水洼倒影（波纹扰动）
        ph = np.sin(np.arange(300, dtype=np.float32)[:, None] / 6 + t * 12) * 6
        mx = (np.arange(W, dtype=np.float32)[None] + ph).astype(np.float32); my = np.repeat(np.arange(300, dtype=np.float32)[:, None], W, 1)
        refl = cv2.remap(refl, mx, my, cv2.INTER_LINEAR)
        m = np.clip((yy[760:1060] - 760) / 40, 0, 1) * 0.45
        fr[760:1060] = fr[760:1060] * (1 - m) + refl[:300] * m * np.array([0.8, 0.88, 1.0], np.float32)
        ts = V(17.46)
        if t >= ts:
            fr = fx2.ripples(fr, t, [(bx, 900)], [ts], speed=520, amt=1.0, life=0.8)
            fr = K.sparks(fr, t, 17, (bx, 900), n=40, life=0.5, speed=(200, 600), dirc=(0, -1), spread=1.2, grav=1400,
                          area=(120, 10), amt=0.5, t0=ts, burst=True, color=(0.7, 0.8, 1.0))
        for k_ in range(3):                                                             # 每步靴面小溅
            ts_ = self.t0 + 0.47 * k_ + 0.42
            if ts_ <= t < ts_ + 0.3:
                fr = K.sparks(fr, t, 170 + k_, (bx + (-60 if k_ % 2 else 50), 880), n=18, life=0.3, speed=(120, 380), dirc=(0, -1), spread=1.3,
                              grav=1500, area=(60, 6), amt=0.45, t0=ts_, burst=True, color=(0.7, 0.8, 1.0))
        fr = RAIN.draw(fr, t, 0.7, angle=8, layers=(2,))
        return fr, 0


# V03 17.95–19.78 ELS 俯瞰五百重甲方阵，火把金点，雾中推进；巨字「五百」半透明压在方阵上，「重甲」随后
class V03(Shot):
    def __init__(self):
        import crowd
        self.army = crowd.Army(seed=3, rows=20, cols=25, torches=50)
        T.warm('五百', 'kai', 330); T.warm('重甲', 'kai', 120)
    def render(self, t):
        u = self.u(t)
        fr = night((0.02, 0.022, 0.03), (0.05, 0.055, 0.065))
        # 第三棒：原俯角 40° 灰白小人方块（评审口径「白模几何体」）→ 俯 30°、前排压到画框下沿铺满画面；
        # 甲胄压暗 + 冷月轮廓光 1.6 + 红缨；火把暖光池 + 行间低雾给纵深
        fr, _ = self.army.draw(fr, t, cam=dict(x=-3 + 5 * u, y=16, z=-8 + 2.5 * u, pitch=30, f=1400), advance=1.2 * u, march=1.0,
                               rim_color=COLDV, rim=1.6, fog_color=(0.04, 0.045, 0.06), fog_dist=70, torch=1.6, origin=(0, 0, 3))
        for (gx, gy, gr) in ((380, 760, 260), (1250, 560, 220), (1650, 900, 300)):
            fr = A.glow(fr, (gx + 40 * u, gy), gr, 0.10, (1.0, 0.55, 0.22))
        fr = fog(fr, t, 1, 300, 960, 0.28, (0.12, 0.13, 0.17), speed=(60, 10))
        fr = A.glow(fr, (1500, 120), 600, 0.15, (0.5, 0.55, 0.7))
        # 巨字
        L = T.Layer()
        for i, (c, x, y, s, k) in enumerate((('五', 380, 360, 330, 0), ('百', 690, 360, 330, 1))):   # 第三棒：右移守左侧安全边
            p = cprog(1, [k], t, 0.3)[0]
            if p > 0: L.paste(T.ink_bleed_glyph(c, 'kai', s, p, seed=i, bleed=0.9), x, y + 20 * (1 - p), (0.92, 0.90, 0.86))
        for i, (c, k) in enumerate((('重', 2), ('甲', 3))):
            p = cprog(1, [k], t, 0.2)[0]
            if p > 0: L.paste(BG(c, 'kai', 120, p, seed=i), 960, 330 + i * 130, (0.86, 0.12, 0.08) if c == '甲' else (0.92, 0.9, 0.86))
        out_ = clamp01((t - V(19.30)) / 0.14)                         # 第十一棒：19.44 前退净，「拦」19.36 才起笔 —— 不再「五百重 / 拦 / 甲」两句同屏被读乱                 # 第六棒：「五百」在 V04 遮挡物过画前退净（critic_A_r3 P1-14）
        fr = T.compose(fr, L, shadow=0.5, glow=0.15, opacity=0.82 * (1 - out_))
        return fr, 0


# V04 19.78–20.69（第六棒：去掉第 3 次军阵渲染 —— 军阵背景本段只剩 V03 俯瞰、V06 横斩两次）
#   LS 低机位雨夜长街：五百重甲只剩远处雾里两排火把光斑（焦外，暗示军阵在前），湿石板倒映火光；鬼屠逆向独行入画，
#   前景两支虚焦枪杆横移遮挡（接 occlusion 入点的枪林）。
class V04(Shot):
    def __init__(self):
        r = np.random.default_rng(44)
        self.torch = [(r.uniform(-100, 2020), 545 + 22 * row + r.uniform(-6, 6), r.uniform(0, 6.28), row) for row in range(2) for _ in range(26)]
        self.tex = cv2.resize(A.tex(144, 512, 6, 5), (W, H))
    def render(self, t):
        u = self.u(t)
        fr = night((0.012, 0.013, 0.02), (0.05, 0.05, 0.06), y1=600)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        gm = np.clip((yy - 600) / 4, 0, 1)[..., None]
        z = 1.0 / np.maximum(yy - 590, 1)
        # 第十一棒（critic_A_r7 P0-2「V04 加真正运镜」）：低机位侧移 truck + 前推 dolly 写进场景层 —— 地砖按深度视差（近处横移最快）、
        #   砖缝向镜头涌来（前推），远处火把只微移，人物中景居中被跟，前景枪杆最快 → 四层视差速度不同 = 真机位移动，不是人在动
        e_ = eio(u); camx = 1.8 * e_; push = 9.0 * e_
        tile = 1 - 0.35 * ((np.mod((xx - 960) * z * 40 - camx, 1.0) < 0.06) | (np.mod(60 * np.log(np.maximum(yy - 590, 1)) - push, 5) < 0.35))
        fr = fr * (1 - gm) + gm * ((0.7 + 0.5 * self.tex) * tile)[..., None] * np.array([0.03, 0.03, 0.036], np.float32)
        for (x, y, ph, row) in self.torch:                                                 # 远处军阵火把（焦外光斑）+ 地面倒影竖条
            x2 = x - 40 * u * (1 + row) - 90 * e_ * (1 + 0.4 * row); fl = 0.8 + 0.2 * math.sin(t * 11 + ph)
            fr = A.glow(fr, (x2, y), 7 + 3 * row, 0.9 * fl, (1.0, 0.55, 0.22), aspect=1.3)
            fr = A.glow(fr, (x2, y), 60, 0.06 * fl, (1.0, 0.45, 0.18))
            fr = fr + (np.exp(-((xx - x2) / 5) ** 2) * np.exp(-np.clip(yy - 600, 0, None) / 160) * (yy > 600))[..., None] * np.array([0.5, 0.25, 0.1], np.float32) * 0.10 * fl
        fr = fog(fr, t, 2, 450, 700, 0.55, (0.20, 0.20, 0.24), speed=(-50, 0), cam=(-160 * e_, 0))
        fr = A.glow(fr, (700 - 60 * e_, 420), 360, 0.15, (0.55, 0.62, 0.8))
        # 第九棒（critic_A_r6 P0-1「人物要动」）：鬼屠迎着镜头走近 —— 由右后方斜走到画面中偏右，身形 640→830px，带步伐起伏与左右摆
        e = eio(u); stp = abs(math.sin(math.pi * (t - self.t0) / 0.31))
        fr, info = A.place(fr, t, S('S010/walk'), (1330 - 200 * e + 6 * math.sin(math.pi * (t - self.t0) / 0.31), 1000 + 190 * e - 14 * stp), h=640 + 170 * e,
                           rim=(1.0, 0.6, 0.3), rim_amt=2.4, rim_dir=(0, -1), wind=8, grade=dict(expo=0.85, sat=0.55), rot=1.2 * math.sin(math.pi * (t - self.t0) / 0.31))
        fr = RAIN.draw(fr, t, 0.7, angle=10, light=(960, 520), layers=(1, 2))
        Lp = np.zeros((H // 2, W // 2), np.float32)                                         # 前景虚焦枪杆 ×2
        for k, (x0, sl) in enumerate(((420 - 1500 * u, 0.25), (1900 - 1700 * u, -0.18))):           # 第十一棒：两支枪杆同向（与机位反向）高速掠过
            cv2.line(Lp, (int(x0 / 2), 0), (int((x0 + sl * H) / 2), H // 2), 1.0, 14 + 6 * k, cv2.LINE_AA)
            cv2.fillConvexPoly(Lp, np.array([(int(x0 / 2) - 16, 0), (int(x0 / 2) + 16, 0), (int(x0 / 2), 70)], np.int32), 1.0)
        Lp = cv2.resize(cv2.GaussianBlur(Lp, (0, 0), 9), (W, H))[..., None]
        fr = fr * (1 - 0.93 * Lp)
        return fr, 0


# V05 20.69–21.20 ECU 手 + 刀特写（第四棒：脸完全出画，hand_draw_cu 精灵）：右手握柄、左拇指推开护手，刃口一线寒光，急推
class V05(Shot):
    def render(self, t):
        u = self.u(t)
        fr = night((0.01, 0.012, 0.02), (0.03, 0.035, 0.05))
        fr = A.glow(fr, (1300, 420), 420, 0.3, (0.5, 0.58, 0.8))
        fr, info = A.place(fr, t, S('A/hand_draw_cu2'), (1040 - 40 * u, 560), w=2300 * (1 + 0.10 * u), anc=(0.5, 0.5), rim=COLD, rim_amt=2.2,
                           wind=0, grade=dict(expo=0.85, sat=0.5, gamma=1.1), breathe=0.0)
        g = math.exp(-max(0, t - V(20.82)) / 0.14) * (t >= V(20.82))
        p = info['to_scr']((0.49, 0.63))
        fr = pupil_glint(fr, p, 1.0 * g, 1.6)
        fr = A.glow(fr, p, 140, 0.5 * g, (0.75, 0.85, 1.0), aspect=0.35)
        fr = RAIN.draw(fr, t, 0.5, angle=10, layers=(2,))
        p = cprog(1, [9], t, 0.16)[0]                                   # 第五棒：「寒」20.82 随刃口寒光落下（与 V06 同位，跨切点连续）
        if p > 0 and HG_ON():                                            # r6 第四棒：默认不出「寒」字
            _hx, _hy = (800, 760) if R6B_OFF('hanguang') else V06.HG[0]                 # r6 第二棒：跟 V06「寒光」新位置（人物右侧）同位
            L = T.Layer(); L.paste(BG('寒', 'kai', 230, p, seed=1), _hx, _hy, (0.94, 0.92, 0.88))
            fr = T.compose(fr, L, shadow=0.8, shadow_sigma=16, glow=0.2)
        return fr, (3 if g > 0.5 else 0)


# V06 21.20–22.52 LS 横斩：21.24 一道横向寒光贯穿画面，前排盔甲裂开红线；「寒光」被斩开错位
class V06(Shot):
    def __init__(self):
        import crowd
        self.army = crowd.Army(seed=6, rows=8, cols=30, torches=20)
        T.warm('寒光', 'kai', 230)
    def render(self, t):
        u = self.u(t); ts = CT(1, 10); ts2 = V(21.86)                     # 第四棒：二次刀光斩字（寒光先完整可读 ≥0.55s）
        fr = night((0.015, 0.017, 0.025), (0.06, 0.065, 0.08), y1=900)
        # 第十一棒（critic_A_r7 P0-2）：真环绕 orbit —— 机位绕人物（距 8m）转 -11°→+11°（共 22°）：机位沿圆弧平移并转向始终对准人物，
        #   军阵（人后 7–30m）随机位同向滑、越远越多；前景枪林（人前）反向急掠；人物本身随视角做透视压缩 + 轮廓光方向转。
        th = math.radians(-11 + 22 * eio(u)); Zp = 8.0
        cxw = -2.5 + Zp * math.sin(th); czw = -2.5 - Zp * (1 - math.cos(th))
        self._th = th
        fr, _ = self.army.draw(fr, t, cam=dict(x=cxw, y=1.8, z=czw, pitch=1, f=1500, cx=W / 2 + 1500 * math.tan(th)),
                               march=0.0, rim_color=COLDV, dof=1.4, fog_dist=50, level=1.0)
        fr = cv2.GaussianBlur(fr, (0, 0), 2.0)
        a = t - ts
        if a >= 0:                                                                     # 前排被斩：一道红热裂线
            L = np.zeros((H, W), np.float32)
            cv2.line(L, (0, 610), (W, 590), 1.0, 3, cv2.LINE_AA)
            fr = fr + (cv2.GaussianBlur(L, (0, 0), 2) * 1.5 + cv2.GaussianBlur(L, (0, 0), 14))[..., None] * RED * 1.5 * math.exp(-a / 0.8)
        fr = fog(fr, t, 0, 640, 960, 0.5, (0.28, 0.3, 0.36), speed=(80, 0))
        ax = 900 + 60 * eout(u)                                                       # 第九棒：收势跟进（人随刀前送 60px、身体由 -2.5° 回正）
        if R5.ON['slash_keys']:
            fr, (g0, g1) = self.r5_keys(fr, t, ts, ts2, th)
        else:
            fr, info = A.place(fr, t, S('S010/slash_h'), (ax, 1000), h=720, rim=COLD, rim_amt=3.0, wind=10, grade=dict(expo=0.9, sat=0.55),
                               mblur=(30 * math.exp(-max(0, a) / 0.08), 0) if a >= 0 else (0, 0), rot=-2.5 * (1 - eout(u)),
                               rim_dir=(-2.2 * math.sin(th), -1.0))                   # 第十一棒：环绕中轮廓光随视角从人物右侧转到左侧
        # 第十一棒：人前 3–4m 的前景枪林（虚焦暗剪影），环绕中与军阵反向急掠（视差 ≈ −f·tanθ·(Zp/Z−1)）
        Lf = np.zeros((H // 4, W // 4), np.float32)
        for (x0, zf, sl, wd) in ((300, 3.0, 0.10, 9), (1500, 3.6, -0.06, 7), (2500, 3.2, 0.08, 8), (-700, 3.4, -0.05, 8)):
            xs = x0 - 1500 * math.tan(th) * (Zp / zf - 1) * 0.55
            cv2.line(Lf, (int(xs / 4), -5), (int((xs + sl * H) / 4), H // 4 + 5), 1.0, wd, cv2.LINE_AA)
        Lf = cv2.resize(cv2.GaussianBlur(Lf, (0, 0), 3.0), (W, H))[..., None]
        fr = fr * (1 - 0.9 * Lf) + Lf * 0.012
        Lr = np.clip(Lf[..., 0] - cv2.GaussianBlur(Lf[..., 0], (0, 0), 6), 0, None)[..., None]   # 枪杆冷月边光，让前景层在暗底上读得出反向视差
        fr = fr + Lr * COLDV * 0.35
        if a >= 0:
            fr = streak(fr, 600, -100, 2100, a / 0.08, w=5, amt=1.6, ang=-0.6)
        # 第九棒（critic_A_r6 P0-1）：寒光沿刀身两次扫过（护手 → 刀尖），每次扫到刀尖，「寒光」被点亮一次
        if not R5.ON['slash_keys']: g0, g1 = (ax + 33, 447), (ax + 480, 424)
        lit = 0.0
        for sa, sd in ((V(21.24), 0.30), (ts2 - 0.26, 0.24)):
            q = (t - sa) / sd
            if -0.1 <= q <= 1.15:
                fr = R9.blade_sheen(fr, g0, g1, eio(clamp01(q)), width=26, amt=1.3 * (1 - clamp01((q - 1.0) / 0.15)), length=180)
            lit = max(lit, math.exp(-max(0.0, t - (sa + sd)) / 0.18) * (t >= sa + sd))
        if 0 <= a < 0.07: fr = fr * 1.55 + 0.06 * COLDV          # 第三棒：冲击改冷色曝光脉冲（不再白闪）
        if R5.ON['slash_keys'] and not HG_ON() and not R6E_OFF('slash2'):
            fr = self.slash2(fr, t, ts2)
        if not R6F_OFF('slash2c') and int(round(t * 30)) - int(round(ts2 * 30)) in (-2, -1):
            # r6 POLISH1：第二刀起刀/过身帧（653/654f）刀弧星芒峰值 255 → 整帧按亮度软肩（>0.78 渐压，顶 0.90），只削死白尖峰，
            # 刀身扫光仍是全帧最亮（不削横扫读感）。开关 A_R6F_OFF=slash2c 回滚
            lum = fr.max(axis=2, keepdims=True); kn, cp = 0.78, 0.90
            lc = np.where(lum > kn, kn + (cp - kn) * np.tanh((lum - kn) / (cp - kn)), lum)
            fr = fr * (lc / np.maximum(lum, 1e-4))
        # 「寒光」斩开：字在屏幕下方，被同一刀切开两半错位
        p = cprog(1, [9], t, 0.25)[0]
        if not HG_ON():                                                  # r6 第四棒：寒光字层、逐字点亮、刀光扫字、斩字火星全部不出；刀身扫光/斩击/裂线保留
            return fr, (5 if 0 <= a < 0.1 else 0)
        if p > 0 and not R6B_OFF('hanguang'):
            return self.r6b_words(fr, t, p, ts2, lit), (5 if 0 <= a < 0.1 else 0)
        if p > 0:
            L = T.Layer()
            L.paste(BG('寒', 'kai', 230, p, seed=1), 800, 760, (0.94, 0.92, 0.88))
            L.paste(BG('光', 'kai', 230, cprog(1, [10], t, 0.12)[0], seed=2), 1080, 760, (0.86, 0.12, 0.08))
            a2 = t - ts2
            # 第十一棒（P0-2「寒光随刀光扫过点亮」）：每次刀身扫光走到刀尖后，一道冷光沿字行由左向右掠过 —— 扫到哪个字哪个字亮（逐字点亮，不是整体闪）
            for sa, sd in ((V(21.24), 0.30), (ts2 - 0.26, 0.24)):
                q2 = (t - sa - sd * 0.5) / 0.30
                if -0.2 <= q2 <= 1.3:
                    sx = 640 + 620 * q2
                    for (gx, gy) in ((800, 760), (1080, 760)):
                        k_ = math.exp(-((gx - sx) / 110.0) ** 2) * (0.25 if (gx == 1080 and cprog(1, [10], t, 0.12)[0] <= 0) else 1.0)
                        if k_ > 0.02: fr = A.glow(fr, (gx, gy), 200, 0.55 * k_, (0.70, 0.85, 1.0), aspect=0.9)
                    fr = streak(fr, 760, sx - 160, sx + 160, 1.0, w=3, amt=0.9 * math.sin(math.pi * clamp01(q2)), ang=-1)
            if a2 < 0:
                fr = T.compose(fr, L, shadow=0.7, glow=0.2 + 0.9 * lit, glow_color=(0.7, 0.85, 1.0))
            else:
                fr = T.slash_layer(fr, L, clamp01(a2 / 0.66), (940, 760), -4, slide=0.25, sz=70, length=900, sparks=50,   # 第十一棒：sz 230→70（断口分离 27→8px、错位 ≤ 笔画宽），「寒光」两半不再读成「宙冬/业儿」
                                   style_kw=dict(shadow=0.7, glow=0.3))
                fr = streak(fr, 760, 300, 1700, a2 / 0.08, w=4, amt=1.2, ang=-4)
        return fr, (5 if 0 <= a < 0.1 else 0)

    # r6 第二棒 #3：「寒光」整组挪到人物右侧空区（x 1150–1600、y 625–855），不再压在腿/袍上；逐字点亮节奏不变，
    #   但冷光只在字形 alpha 内（+ ≤18px 贴字微晕，半径 <80），不叠到人物层；斩字刀光只跨两字（1110–1650），整段同时淡出，不留孤立白段。
    HG = ((1265, 740), (1492, 740))
    def r6b_words(self, fr, t, p, ts2, lit):
        L = T.Layer()
        p2 = cprog(1, [10], t, 0.12)[0]
        L.paste(BG('寒', 'kai', 230, p, seed=1), self.HG[0][0], self.HG[0][1], (0.94, 0.92, 0.88))
        L.paste(BG('光', 'kai', 230, p2, seed=2), self.HG[1][0], self.HG[1][1], (0.86, 0.12, 0.08))
        # 逐字点亮：一道冷光沿字行由左向右掠过（只照亮字形本身）
        xx = np.arange(W, dtype=np.float32)[None, :]
        lightm = np.zeros((H, W), np.float32)
        for sa, sd in ((V(21.24), 0.30), (ts2 - 0.26, 0.24)):
            q2 = (t - sa - sd * 0.5) / 0.30
            if -0.2 <= q2 <= 1.3:
                sx = 1080 + 620 * q2
                lightm = np.maximum(lightm, np.exp(-((xx - sx) / 110.0) ** 2) * math.sin(math.pi * clamp01(q2 + 0.1)) * np.ones((H, 1), np.float32))
        a2 = t - ts2
        if a2 < 0:
            fr = T.compose(fr, L, shadow=0.7, glow=0.2 + 0.5 * lit, glow_color=(0.7, 0.85, 1.0), glow_sigma=14)
            LA = L.A
        else:
            fr = T.slash_layer(fr, L, clamp01(a2 / 0.66), (1378, 740), -4, slide=0.25, sz=70, length=560, sparks=40, light=False,
                               style_kw=dict(shadow=0.7, glow=0.3, glow_sigma=14))
            LA = L.A
            fr = self.cutline(fr, (1378, 740), -4, 1110, 1650, a2)
        if lightm.max() > 0.02:
            m = LA * lightm
            m = m + cv2.GaussianBlur(m, (0, 0), 6) * 0.35 * (cv2.GaussianBlur(LA, (0, 0), 6) > 0.02)
            fr = fr + m[..., None] * 0.85 * np.array([0.70, 0.85, 1.0], np.float32)
        return fr

    @staticmethod
    def slash2(fr, t, ts2):
        """r6 第五棒（总导演：去「寒光」后第二刀偏弱）：第二刀 21.86 补一条不带字的横向刀光。
        命中帧 b 一帧内由护手后扫到右出画（贴鼓点），沿送出姿态刀尖高度（K3 刀尖 ≈(1286,371)）、随刀身 -2° 微斜；
        细冷白芯 2px + 两层冷晕（σ6 / σ24），两端收尖；b+1 起整段同时淡出，b+5 退净（共 5 帧）；命中帧附带轻冷色脉冲（×1.30，弱于第一刀 ×1.55）。
        叠加后在刀光范围内软压到 ≤0.95（≈242/255），不发白一片。"""
        F = int(round(t * 30)); b = int(round(ts2 * 30)); k = F - b
        if not (0 <= k <= 4): return fr
        hd = 0.62 if k == 0 else 1.0                                              # 命中帧刀光头已过刀尖、扫到 62%；下一帧满长
        f = (1.0, 0.82, 0.55, 0.30, 0.12)[k]
        if not R6F_OFF('slash2b'): return V06.slash2b(fr, k, hd, f)
        if k == 0: fr = fr * 1.30 + 0.04 * COLDV
        y0, ang, x0, x1 = 371.0, -2.0, 900.0, W + 80.0           # 起点在护手外（x≈900），不压脸、颈
        th = math.radians(ang); Y = lambda x: y0 + (x - 1286.0) * math.tan(th)
        xe = x0 + (x1 - x0) * hd
        Ls = np.zeros((H // 2, W // 2), np.float32); n = 40
        for i in range(n):
            xa = x0 + (xe - x0) * i / n; xb = x0 + (xe - x0) * (i + 1) / n; s_ = (i + 0.5) / n
            wv = min(1.0, s_ / 0.25) ** 1.2 * (min(1.0, (1 - s_) / 0.12) if hd >= 1 else 1.0)   # 尾端（护手侧）长收尖；出画端满长时也收
            cv2.line(Ls, (int(xa / 2), int(Y(xa) / 2)), (int(xb / 2), int(Y(xb) / 2)), float(wv), 2, cv2.LINE_AA)
        Ls = cv2.resize(Ls, (W, H))
        core = Ls * 1.3
        h1 = cv2.GaussianBlur(Ls, (0, 0), 8) * 3.2
        h2 = cv2.GaussianBlur(Ls, (0, 0), 32) * 2.6
        add = (core[..., None] * np.array([0.95, 0.98, 1.0], np.float32) + h1[..., None] * np.array([0.62, 0.78, 1.0], np.float32)
               + h2[..., None] * np.array([0.35, 0.50, 0.85], np.float32)) * f
        out = fr + add
        m = np.clip(h2 * 8, 0, 1)[..., None]                                      # 只在刀光范围内软压高光
        cap = 0.88
        soft = np.where(out > 0.8, 0.8 + (cap - 0.8) * np.tanh((out - 0.8) / (cap - 0.8)), out)
        return out * (1 - m) + soft * m

    @staticmethod
    def slash2b(fr, k, hd, f):
        """r6 第六棒：655f 峰值 253、刀光是一条 ~24px 宽的平顶白板（刺眼）。改成有层次的三层：
        细芯（≈2px，峰值软压到 ≈0.86）→ 窄冷晕（σ4，≈0.55）→ 宽冷晕（σ20，≈0.18），中间不再有平顶白板；
        冷色脉冲 ×1.30 → ×1.15（第一刀 ×1.55 仍是主冲击）；软压按亮度（不是逐通道）以免压出色偏。"""
        if k == 0: fr = fr * 1.15 + 0.025 * COLDV
        y0, ang, x0, x1 = 371.0, -2.0, 900.0, W + 80.0
        th = math.radians(ang); Y = lambda x: y0 + (x - 1286.0) * math.tan(th)
        xe = x0 + (x1 - x0) * hd
        Ls = np.zeros((H, W), np.float32); n = 48
        for i in range(n):
            xa = x0 + (xe - x0) * i / n; xb = x0 + (xe - x0) * (i + 1) / n; s_ = (i + 0.5) / n
            wv = min(1.0, s_ / 0.25) ** 1.2 * (min(1.0, (1 - s_) / 0.12) if hd >= 1 else 1.0)
            cv2.line(Ls, (int(xa), int(Y(xa))), (int(xb), int(Y(xb))), float(wv), 2, cv2.LINE_AA)
        core = cv2.GaussianBlur(Ls, (0, 0), 0.8)
        h1 = cv2.GaussianBlur(Ls, (0, 0), 6) * 4.2
        h2 = cv2.GaussianBlur(Ls, (0, 0), 24) * 4.0
        add = (core[..., None] * np.array([0.80, 0.86, 0.90], np.float32) + h1[..., None] * np.array([0.42, 0.55, 0.78], np.float32)
               + h2[..., None] * np.array([0.16, 0.24, 0.42], np.float32)) * f
        out = fr + add
        lum = out.max(axis=2, keepdims=True)
        knee, cap = 0.66, 0.86
        lc = np.where(lum > knee, knee + (cap - knee) * np.tanh((lum - knee) / (cap - knee)), lum)
        m = np.clip(cv2.GaussianBlur(Ls, (0, 0), 20) * 30, 0, 1)[..., None]
        out = out * (1 - m) + out * (lc / np.maximum(lum, 1e-4)) * m
        if k <= 1:                                                                # 命中帧 + 次帧：刀弧/星芒/枪尖等其余高光整帧软肩（>0.80 渐压，顶 ≈0.91），不出 250+ 死白
            lum = out.max(axis=2, keepdims=True); kn, cp = 0.80, 0.91
            lc = np.where(lum > kn, kn + (cp - kn) * np.tanh((lum - kn) / (cp - kn)), lum)
            out = out * (lc / np.maximum(lum, 1e-4))
        return out

    @staticmethod
    def cutline(fr, c, ang, x0, x1, a2):
        """斩字刀光：2 帧内由左扫到右（全长只跨两字），之后整段原地 0.22s 淡出 —— 不收缩成孤立白段。"""
        hd = clamp01(a2 / 0.07); f = 1.0 if a2 < 0.07 else max(0.0, 1 - (a2 - 0.07) / 0.22)
        if f <= 0: return fr
        th = math.radians(ang)
        Y = lambda x: c[1] + (x - c[0]) * math.tan(th)
        xe = x0 + (x1 - x0) * hd
        Ls = np.zeros((H // 2, W // 2), np.float32)
        n = 24
        for i in range(n):                                                        # 两端收尖（线宽随位置衰减）
            xa = x0 + (xe - x0) * i / n; xb = x0 + (xe - x0) * (i + 1) / n
            s_ = (i + 0.5) / n; wv = math.sin(math.pi * s_) ** 0.6
            cv2.line(Ls, (int(xa / 2), int(Y(xa) / 2)), (int(xb / 2), int(Y(xb) / 2)), float(wv), 2, cv2.LINE_AA)
        Ls = cv2.resize(Ls, (W, H))
        g = Ls * 1.4 + cv2.GaussianBlur(Ls, (0, 0), 6) * 1.2 + cv2.GaussianBlur(Ls, (0, 0), 18) * 0.5
        return fr + g[..., None] * np.array([1.0, 0.97, 0.92], np.float32) * f

    RC = 21.47                                                                       # 第五轮 3：第一刀后收刀回身后蓄势的时刻
    def r5_keys(self, fr, t, ts, ts2, th):
        """第五轮 3（用户：0:22 挥刀动作难看）：五张同人物关键姿态逐帧切换 —— 第一刀送出 → 收刀到身后蓄势 → 第二刀
        横斩（起刀 / 过身前 / 平出 / 送出），每档 1 帧，配水平动态模糊 + 代码刀弧拖影；脚底中点钉在同一点，比例按原图像素一致。"""
        u = self.u(t)
        cur, prv, mb = R5.sk_schedule(t, ts, V(self.RC), ts2)
        F = int(round(t * 30)); b = int(round(ts2 * 30)); r = int(round(V(self.RC) * 30))
        # 位置：第一刀后与第二刀后各向前送 30px（收势跟进）；蓄势时略后坐 + 微沉
        fw = 30 * eout(clamp01((t - ts) / 0.4)) + 30 * eout(clamp01((t - ts2) / 0.5))
        back = -14 * eio(clamp01((t - V(self.RC)) / 0.25)) * (F < b - 2)
        ax = 880 + fw + back
        ay = 1000 + 4 * eio(clamp01((t - V(self.RC)) / 0.3)) * (F < b - 2)
        s_raw = 0.744 * (0.93 if 'k3' in cur else 1.0)
        SK = 1.0
        if not R6B_OFF('feet'):                                                        # r6 第二棒 #3：脚入画 —— 人物缩 8%、脚点 y 1000→912（有效区下沿 960 之上），脚下接触阴影
            SK = 0.92; ay -= 88; ax -= 80; s_raw *= SK
            yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32)
            sh = np.exp(-(((xx_ - ax) / 330) ** 2 + ((yy_ - ay - 4) / 16) ** 2)) * 0.7 + np.exp(-(((xx_ - ax) / 520) ** 2 + ((yy_ - ay - 6) / 38) ** 2)) * 0.3
            fr = fr * (1 - 0.75 * sh[..., None])
        at = (ax, ay)
        path = R5.sk_path(cur)
        gm = R5.sk_geom(cur)
        import a_r6
        anc = a_r6.anc_for(path, gm['feet'])
        hh = (A.sprite(path, 640).bbox[3] - A.sprite(path, 640).bbox[1]) * gm['size'][1] / gm['k'] * s_raw
        fr, info = A.place(fr, t, path, at, h=hh, anc=anc, rim=COLD, rim_amt=3.0, wind=6, grade=dict(expo=0.9, sat=0.55),
                           mblur=(mb, 0), rim_dir=(-2.2 * math.sin(th), -1.0))
        xf = R5.sk_xf(cur, at, s_raw)
        if prv is not None:                                                            # 刀弧：上一档刀尖 → 本档刀尖，绕护手扫过身前
            gp = R5.sk_geom(prv); xp = R5.sk_xf(prv, at, 0.744 * (0.93 if 'k3' in prv else 1.0) * SK)
            C = tuple((np.array(xp(gp['hilt'])) + np.array(xf(gm['hilt']))) / 2)
            old = F in (b, int(round(ts * 30)) + 1)                                    # 已送出的那一帧：刀弧只剩余辉
            fr = R5.blade_arc(fr, C, xp(gp['tip']), xf(gm['tip']), amt=0.7 if old else 1.4)
        if F in (b + 1, b + 2, int(round(ts * 30)) + 2):                                 # 送出后残留的一道淡弧
            g1_ = R5.sk_geom('slash_k1_windup_v1'); x1_ = R5.sk_xf('slash_k1_windup_v1', at, 0.744 * SK)
            C = tuple(xf(gm['hilt']))
            fr = R5.blade_arc(fr, C, x1_(g1_['tip']), xf(gm['tip']), amt=0.45 if F != b + 2 else 0.22)
        h0, tp = np.array(xf(gm['hilt'])), np.array(xf(gm['tip']))
        return fr, (tuple(h0 + (tp - h0) * 0.06), tuple(h0 + (tp - h0) * 0.80))


# V07 22.52–23.45 LS 仰拍宫阶（第四棒：去月 → 宫灯逆光）：殿檐压顶、两列红宫灯摇晃，太上皇立于丹陛顶端的背光剪影；
#     丹陛顶边 y=600 与 V06 寒光横线匹配剪辑；「谁在高处」由上压下
class V07(Shot):
    def render(self, t):
        u = self.u(t)
        fr = night((0.03, 0.015, 0.012), (0.10, 0.06, 0.04), y1=700)
        fr = A.glow(fr, (960, 420), 520, 0.55, (1.0, 0.55, 0.25))                     # 殿门内烛火大逆光（非月）
        fr = A.glow(fr, (960, 440), 180, 0.6, (1.0, 0.75, 0.45), aspect=0.8)
        fr = fx2.god_rays(fr, (960, 430), strength=0.3, length=1.0, color=(1.0, 0.7, 0.4), t=t, src_r=160)
        m = np.zeros((H, W), np.float32)
        cv2.fillPoly(m, [np.array([(-50, 0), (1970, 0), (1970, 120), (1700, 190), (960, 150), (220, 190), (-50, 120)], np.int32)], 1.0, cv2.LINE_AA)   # 殿檐
        cv2.fillPoly(m, [np.array([(0, 600), (W, 600), (W, H), (0, H)], np.int32)], 1.0)
        for k in range(1, 6):                                                          # 丹陛台阶
            y = 600 + k * 60; cv2.line(m, (0, y), (W, y), 0.6, 2)
        fr = fr * (1 - m[..., None]) + m[..., None] * 0.008
        e = np.clip(m - cv2.erode(m, np.ones((3, 3), np.uint8)), 0, 1)
        fr = fr + e[..., None] * np.array([1.0, 0.7, 0.45], np.float32) * 0.7
        for i, x in enumerate((180, 420, 1500, 1740)):                                 # 宫灯
            y = 270 + (40 if i in (1, 2) else 0); sw = 12 * math.sin(t * 2.2 + i)
            cv2.line(fr, (x, 160), (int(x + sw * 0.6), y - 50), (0.01, 0.01, 0.01), 2, cv2.LINE_AA)
            fr = A.glow(fr, (x + sw, y), 34, 1.6, (1.0, 0.22, 0.08), aspect=1.3)
            fr = A.glow(fr, (x + sw, y), 120, 0.25, (1.0, 0.3, 0.1))
        fr, info = A.place(fr, t, S('S011/backlit'), (960, 602), h=400 * (1 + 0.04 * u), look='sil', rim=GOLD, rim_amt=5.0, wind=7)
        fr = GDUST.draw(fr, t, 0.5, wind=(30, -20))
        return fr, 0


# V08 23.45–25.29（第六棒重做，critic_A_r3 P0 不可交付：朱印叠在手指上、手里看不到玺）
#   前段 23.45–24.58：低机位侧面 CU —— 太上皇枯手攥住盘龙玉玺（tsh_seal_lift 新精灵，脸在右后景虚化压暗作第三层），
#       玺自画上方加速压向烛光下的宣纸（纸面在下沿成一条亮带），纸上玺影随落下收紧；24.48「罪」落印：震 + 纸尘 + 印泥飞点。
#   后段 24.58–25.29：切俯拍纸面 —— 玺已抬走（只剩玺影向右上滑出），宣纸上留下「罪状」白文印痕（印痕乘在纸上、纸纹透出、
#       纤维晕边、朱色降饱和 15%）；层级 = 纸 → 印痕 → 玺影，手与玺不在此画面中，不会再出现「贴纸盖在手上」。24.78「状」印泥再沉一档。
class V08(Shot):
    def __init__(self):
        import a_r6
        self.R = a_r6
        import a_r7
        self.R7 = a_r7
        self.spr = a_r7.tsh_seal_noface()
        self.anc = a_r6.anc_for(self.spr, (0.402, 0.80))          # 玺底前沿中点
        self.pap = a_r6.paper(21)
        T.warm('定对错', 'kai', 96)
    def render(self, t):
        th = CT(2, 7); tsw = th + 0.10
        if t < tsw: return self.side(t, th)
        return self.top(t, th, tsw)
    def side(self, t, th):
        q = clamp01((t - self.t0) / (th - self.t0)); a = t - th
        # 第七棒（critic_A_r4 P0-2）：后景那张虚焦脸去掉 → 殿内屏风窗棂透烛光 + 两团烛焰焦外光斑（手玺仍是唯一焦点）
        fr = self.R7.candle_screen(t)
        fr = fx2.god_rays(fr, (1500, 300), strength=0.18, length=0.7, color=(1.0, 0.7, 0.4), t=t, src_r=80)
        # 宣纸桌面：低机位看成一条带透视的亮带（y 800–960），纸纹纵向压扁
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        band = np.clip((yy - 878) / 5, 0, 1)
        pap = cv2.resize(self.pap[::5], (W, H)) * (0.6 + 0.6 * np.clip((yy - 878) / 80, 0, 1))
        lit = A.glow(np.zeros((H, W, 3), np.float32), (1300, 900), 900, 1.0, (1.0, 0.85, 0.6), aspect=0.2)
        fr = fr * (1 - band) + pap * band * (0.35 + 0.9 * lit)
        drop = 110 * (1 - ein(q, 1.8)) if a < 0 else -5 * math.exp(-a / 0.05)
        at = (700, 880 - drop)
        # 玺影：落在纸上，离纸越近越实越小
        sh = np.zeros((H // 2, W // 2), np.float32)
        sw = 300 + 260 * (1 - q)
        cv2.ellipse(sh, (int((at[0] - 60 * (1 - q)) / 2), 442), (int(sw / 2), int(7 + 6 * (1 - q))), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        sh = cv2.resize(cv2.GaussianBlur(sh, (0, 0), 3 + 16 * (1 - q)), (W, H))[..., None] * band
        fr = fr * (1 - (0.35 + 0.5 * q) * sh)
        fr, info = A.place(fr, t, self.spr, at, w=964, anc=self.anc, rim=GOLD, rim_amt=2.4, rim_dir=(0.8, -0.5),
                           grade=dict(expo=1.12, sat=1.25, tint=(1.0, 1.04, 0.94), gamma=0.95), wind=2, breathe=0.0)
        # 桌面在玺/袖之前：低机位下纸面是一条掠射亮带，桌沿以下（袖摆）被桌前沿挡住
        fr = fr * (1 - band) + pap * band * (0.35 + 0.9 * lit)
        edge = np.clip((yy - 924) / 4, 0, 1)
        fr = fr * (1 - edge) + edge * np.array([0.03, 0.018, 0.012], np.float32) * (1 + 0.6 * lit)
        fr = fr + np.exp(-((yy - 879) / 1.5) ** 2) * lit * np.array([0.9, 0.7, 0.45], np.float32) * 0.5
        if a >= 0:
            fr = fr * (1 + 0.45 * math.exp(-a / 0.06))
            fr = K.sparks(fr, t, 81, (700, 882), n=60, life=0.45, speed=(150, 520), dirc=(0, -1), spread=2.6, grav=900,
                          area=(240, 6), amt=0.55, t0=th, burst=True, color=(0.95, 0.85, 0.7))      # 纸尘
            fr = K.sparks(fr, t, 82, (700, 883), n=16, life=0.35, speed=(200, 600), dirc=(0, -1), spread=2.2, grav=1400,
                          area=(220, 4), amt=0.8, t0=th, burst=True, color=(0.75, 0.10, 0.06))      # 印泥飞点
        fr = GDUST.draw(fr, t, 0.25, wind=(20, -30))
        return fr, (1 if 0 <= a < 0.08 else 0)
    def top(self, t, th, tsw):
        k = t - tsw; a2 = t - CT(2, 8)
        lit = A.vgrad((1.0, 0.96, 0.9), (0.55, 0.48, 0.42))
        lit = A.glow(lit * 0.75, (1550, 160), 1100, 0.55, (1.0, 0.8, 0.55))
        fr = self.pap * lit * 0.9
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        fr = fr * (1 - 0.45 * np.clip((np.hypot(xx - 1300, yy - 300) - 500) / 1300, 0, 1))[..., None]     # 烛光衰减
        # 纸上原有墨书（诏文，淡）：右侧三列小楷
        if not hasattr(self, 'doc') and R5.ON['garble']:
            self.doc = R5.garble_doc(T)                                                        # 第五轮 5：诏文 → 乱码（天书式假字）
        if not hasattr(self, 'doc'):
            L = T.Layer()
            for ci, col in enumerate(('奉旨查办逆犯一名', '目无王法擅杀官兵', '罪证确凿着即拿问')):
                for ri, ch in enumerate(col):
                    T.place(L, ch, 1560 - ci * 92, 200 + ri * 84, 66, (0.06, 0.05, 0.05), 'kai', alpha=0.62, blur=0.9)
            self.doc = L
        fr = fr * (1 - 0.82 * self.doc.A[..., None]) + self.doc.A[..., None] * 0.02
        kk = 0.86 + 0.14 * clamp01(a2 / 0.15) if a2 >= 0 else 0.86
        fr, Lm = self.R.imprint(fr, '罪状', 760, 540, 330, k=kk, rot=-3.0, seed=5)
        # 玺影：玺被抬走，影子变大变虚、向右上滑出（光从右上来 → 影落左下，抬起时影朝光源反向扩散后离开）
        e = eout(clamp01(k / 0.55))
        sh = np.zeros((H // 2, W // 2), np.float32)
        c = (760 + 520 * e - 40, 540 - 300 * e + 50)
        hs = 190 + 140 * e
        cv2.rectangle(sh, (int((c[0] - hs) / 2), int((c[1] - hs) / 2)), (int((c[0] + hs) / 2), int((c[1] + hs) / 2)), 1.0, -1)
        sh = cv2.resize(cv2.GaussianBlur(sh, (0, 0), 6 + 40 * e), (W, H))[..., None]
        fr = fr * (1 - 0.55 * (1 - e) * sh)
        fr = K.sparks(fr, t, 83, (760, 540), n=24, life=0.6, speed=(40, 160), dirc=(0.4, -1), spread=2.0, grav=-40,
                      area=(180, 180), amt=0.35, t0=tsw - 0.02, burst=True, color=(0.95, 0.85, 0.65))      # 纸尘余烟
        return fr, (2 if k < 0.06 else 0)


PAPER_BODY = np.array([(0, -1.0), (-0.07, -0.97), (-0.09, -0.86), (-0.06, -0.80), (-0.22, -0.74), (-0.30, -0.40), (-0.24, -0.38),
                       (-0.20, -0.62), (-0.18, -0.30), (-0.30, 0), (0.30, 0), (0.18, -0.30), (0.20, -0.62), (0.24, -0.38), (0.30, -0.40),
                       (0.22, -0.74), (0.06, -0.80), (0.09, -0.86), (0.07, -0.97)], np.float32)


def paper_crowd(fr, t, cx, cy, wpx, rows=5, per=11, hpx=70, seed=0, light=(0, -1)):
    """第三棒：秤盘里的「千人」= 层层叠叠的剪纸人（宣纸纹理 + 顶光金边 + 每人轻微晃动），后排更小更暗、堆成丘，
    替换原来的白色小方块（评审口径：程序道具不能是白模几何体）。cx,cy = 盘心（脚底线），wpx = 盘宽。"""
    r = np.random.default_rng(seed)
    Lp = np.zeros((H, W), np.float32); Sh = np.zeros((H, W), np.float32)
    for row in range(rows - 1, -1, -1):
        k = row / max(1, rows - 1)
        n = per - row; sc = 1 - 0.12 * row
        span = wpx * (0.92 - 0.12 * row)
        for i in range(n):
            x = cx - span / 2 + span * (i + 0.5 + r.uniform(-0.3, 0.3)) / n
            y = cy - row * hpx * 0.42 - (1 - ((x - cx) / (wpx / 2)) ** 2) * hpx * 0.25 * row
            ang = r.uniform(-8, 8) + 4 * math.sin(t * 2.2 + i + row)
            th = math.radians(ang); Rm = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]], np.float32)
            P = (PAPER_BODY * hpx * sc * r.uniform(0.85, 1.1) @ Rm.T + [x, y]).astype(np.int32)
            tmp = np.zeros_like(Lp); cv2.fillPoly(tmp, [P], 1.0, cv2.LINE_AA)
            tone = 1.0 - 0.45 * k
            Sh = np.maximum(Sh * (1 - tmp), tmp * (1 - tone))          # 近排盖住远排
            Lp = np.maximum(Lp, tmp)
    Lp = cv2.GaussianBlur(Lp, (0, 0), 0.7)
    paper = (0.72 + 0.28 * cv2.resize(A.tex(seed + 102, 256, 10, 4), (W, H)))[..., None] * np.array([0.90, 0.74, 0.50], np.float32)
    shade = 1 - Sh[..., None]
    top = np.clip(Lp - cv2.warpAffine(Lp, np.float32([[1, 0, -light[0] * 3], [0, 1, -light[1] * 3]]), (W, H)), 0, 1)[..., None]
    edge = np.clip(Lp - cv2.erode(Lp, np.ones((3, 3), np.uint8)), 0, 1)[..., None]
    col = paper * 0.80 * shade + top * GOLDV * 0.9 - edge * 0.10
    return fr * (1 - Lp[..., None]) + np.clip(col, 0, 2) * Lp[..., None]


# V09 25.29–27.10（第六棒重做，critic_A_r3 P0 不可交付：矢量线天平 + 平涂金块 + 灰渐变无空间）
#   MS 暗殿中的青铜天平（bronze_scale 新生图：饕餮纹铜梁、铜链、左盘层叠剪纸人、右盘盘龙金玺，梁右低）。
#   三层空间：后景 = 殿内两根朱漆柱 + 远处烛架光斑（焦外）+ 天窗体积光；中景 = 天平（金色主光右上、冷轮廓左后）；
#   前景 = 焦外烛焰与一根横移的暗柱边（环绕视差）；地面 = 磨光金砖，天平倒影。
#   歌词：梁下左右两列竖排（像一副对联挂在梁下）——左「谁把人命」贴着纸人盘，右「装进天平」贴着金玺盘；离梁 ≥80px；
#   「人命」朱红描金边 + 暗衬，缩到 480px 宽仍可读。
class V09(Shot):
    def __init__(self):
        import a_r6
        self.spr = a_r6.clean('A_r6/bronze_scale', lo=0.2, erode=3)
        self.floor = (0.7 + 0.5 * cv2.resize(A.tex(93, 512, 5, 5), (W, H)))[..., None]
        T.warm('谁把人命装进天平', 'kai', 92)
    def render(self, t):
        u = self.u(t)
        fr = A.vgrad((0.004, 0.003, 0.003), (0.022, 0.015, 0.011), 0, 880)
        # 后景：两根朱漆殿柱（焦外）+ 远烛光斑
        xx = np.arange(W, dtype=np.float32)[None, :, None]; yy = np.arange(H, dtype=np.float32)[:, None, None]
        for cx_, w_ in ((250 - 60 * u, 120), (1680 - 60 * u, 130)):
            m = np.clip((w_ / 2 - np.abs(xx - cx_)) / 30, 0, 1) * (yy < 880)
            shade = 0.5 + 0.5 * np.clip((xx - cx_ + w_ / 2) / w_, 0, 1)
            fr = fr * (1 - m) + m * np.array([0.16, 0.025, 0.015], np.float32) * shade * (0.5 + 0.8 * np.clip(1 - np.abs(yy - 500) / 500, 0, 1))
            rim_ = np.exp(-((xx - cx_ - w_ / 2 + 8) / 6) ** 2) * (yy < 880)
            fr = fr + rim_ * np.array([0.5, 0.25, 0.1], np.float32) * 0.35
        for i, (bx, by) in enumerate(((420, 520), (470, 560), (1460, 500), (1520, 540), (1400, 580))):
            fl = 0.85 + 0.15 * math.sin(t * 9 + i * 2)
            fr = A.glow(fr, (bx - 60 * u, by), 26, 0.55 * fl, (1.0, 0.62, 0.3), aspect=1.4)
            fr = A.glow(fr, (bx - 60 * u, by), 120, 0.10 * fl, (1.0, 0.5, 0.2))
        fr = fx2.god_rays(fr, (1180, 40), strength=0.38, length=1.1, color=(1.0, 0.82, 0.55), t=t, src_r=120)
        # 地面：磨光金砖（缝 + 烛光反射）
        fl_m = np.clip((yy - 880) / 3, 0, 1)
        tiles = 1 - 0.35 * ((np.mod(xx + (yy - 880) * (xx - 960) / 300, 240) < 3) | (np.mod(yy, 46) < 2))
        fr = fr * (1 - fl_m) + fl_m * self.floor * tiles * np.array([0.035, 0.024, 0.017], np.float32)
        for bx in (420, 1460):
            fr = fr + fl_m * np.exp(-((xx - bx + 60 * u) / 40) ** 2) * np.exp(-(yy - 880) / 60) * np.array([0.5, 0.3, 0.12], np.float32) * 0.6
        # 天平：先在黑底合成拿到预乘色，再做倒影
        z = np.zeros((H, W, 3), np.float32)
        rot = 0.0
        P, info = A.place(z, t, self.spr, (960, 880), h=740, anc=(0.5, 1.0), rim=COLD, rim_amt=1.4, rim_dir=(-0.8, -0.5),
                          grade=dict(expo=1.05, sat=0.85, tint=(1.04, 1.0, 0.92), gamma=1.0), wind=0, breathe=0.0, rot=rot)
        Al = info['A'][..., None]
        # 第八棒（critic_A_r5 P0-1）：横梁按支点慢摆 —— 装进「人命」后纸人盘被金玺压得往上翘（右盘下沉），带一点阻尼余摆
        sl = 0.075 * eio(u) - 0.020 + 0.012 * math.sin(t * 4.2) * (1 - 0.6 * u)
        P, Al = R8.shear_beam(P, Al, (946, 170), sl, 330, sl * 440, col_half=70, fade=150)
        Rf = cv2.flip(P[880 - 120:880], 0); Ra = cv2.flip(Al[880 - 120:880, :, 0], 0)[..., None]
        g = np.linspace(0.35, 0.0, 80, dtype=np.float32)[:, None, None]
        fr[880:960] = fr[880:960] * (1 - Ra[:80] * g) + cv2.GaussianBlur(Rf[:80], (0, 0), 3) * g
        fr = fr * (1 - Al) + P
        fr = A.glow(fr, info['to_scr']((0.78, 0.63)), 90, 0.25 + 0.1 * math.sin(t * 5), (1.0, 0.8, 0.4))   # 金玺反光
        fr = fog(fr, t, 1, 700, 900, 0.16, (0.20, 0.15, 0.11), speed=(-30, 0), light=(1180, 40))
        # 前景：焦外暗柱边横移 + 焦外烛焰
        fx_ = 2000 - 360 * u
        m = np.clip((xx - fx_) / 40, 0, 1)
        fr = fr * (1 - 0.94 * m) + np.exp(-((xx - fx_ - 30) / 14) ** 2) * np.array([0.35, 0.18, 0.08], np.float32) * 0.4
        fr = A.glow(fr, (140 + 80 * u, 900), 70, 0.5, (1.0, 0.55, 0.25), aspect=1.3)
        # 梁下两列竖排（r6 #53：NOVLYR 时不画）
        L = T.Layer(); Lr = T.Layer()
        cols = () if NOVLYR else (('谁把人命', [0, 1, 2, 3], (0.430, 0.235)), ('装进天平', [4, 5, 6, 7], (0.603, 0.315)))
        for txt, ks, (nx, ny) in cols:
            x0, y0 = info['to_scr']((nx, ny))
            for i, (c, p) in enumerate(zip(txt, cprog(3, ks, t, 0.22))):
                if p <= 0: continue
                red = c in '人命'
                g_ = BG(c, 'kai', 92, p, seed=30 + i + ks[0])
                (Lr if red else L).paste(g_, x0, y0 + 46 + i * 98, (0.98, 0.22, 0.12) if red else (0.96, 0.93, 0.86))
        fr = T.compose(fr, L, shadow=0.85, shadow_sigma=12, glow=0.15)
        fr = T.compose(fr, Lr, shadow=0.9, shadow_sigma=12, outline=2, outline_color=(1.0, 0.78, 0.40), glow=0.35, glow_color=(0.9, 0.15, 0.06))
        return fr, 0


# V10 27.10–28.93 LS 低机位·人在秤盘里（第五棒重做，评审 P0：原纸人像占位素材、缺「里」）：
#     巨大青铜秤盘占下半屏，鬼屠单膝跪在盘中（kneel_pan 精灵，盘沿以下被盘壁挡住），两根铜链自盘沿升出画外；
#     顶上天平金光（主光，体积光束）+ 背后冷雨轮廓光；雨打盘沿溅水；27.66「里」铸文在盘壁上金光灌注亮起；
#     链上一滴朱墨落到盘沿 28.10 溅开 →「称」「量」朱墨在盘壁上晕开。盘体随链轻摆。
class V10(Shot):
    def __init__(self):
        T.warm('里', 'kai', 165); T.warm('称量', 'kai', 160)
        import a_r6; self.R6 = a_r6
        self.tex = cv2.resize(A.tex(101, 512, 5, 6), (W, H)); self.tex2 = cv2.resize(A.tex(103, 512, 40, 3), (W, H))
        self.CX, self.CY, self.AX, self.AY, self.DEP = 960, 600, 1060, 96, 560
    def bowl(self, sway):
        cx, cy, ax, ay, dep = self.CX + sway, self.CY, self.AX, self.AY, self.DEP
        inner = np.zeros((H, W), np.float32); wall = np.zeros((H, W), np.float32)
        cv2.ellipse(inner, (int(cx), cy), (ax, ay), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        cv2.ellipse(wall, (int(cx), cy), (ax, dep), 0, 0, 180, 1.0, -1, cv2.LINE_AA)
        wall = np.clip(wall - inner * (np.arange(H)[:, None] < cy), 0, 1)
        wall = np.clip(wall - inner, 0, 1)
        rimB = np.zeros((H, W), np.float32); rimF = np.zeros((H, W), np.float32)
        cv2.ellipse(rimB, (int(cx), cy), (ax, ay), 0, 180, 360, 1.0, 6, cv2.LINE_AA)
        cv2.ellipse(rimF, (int(cx), cy), (ax, ay), 0, 0, 180, 1.0, 9, cv2.LINE_AA)
        return inner, wall, rimB, rimF
    def render(self, t):
        u = self.u(t); tl = CT(3, 8); td = V(28.10)
        sway = -34 + 68 * eio(u) + 10 * math.sin(t * 3.4)                              # 第八棒：盘在链上从左摆到右（起止差 ~70px）
        bob = 14 * math.sin(t * 3.4 + 0.9) - 52                                        # 人随盘起伏；第十一棒：人退到盘心（−52px），前面空出一片铜面给倒影
        heap = R5.ON['paper_bowl']                                                     # 第五轮 6：盘里仍是 V09 那堆纸人（不再换成主角）
        if heap: bob = 6 * math.sin(t * 3.4 + 0.9) - 20
        fr = night((0.035, 0.026, 0.016), (0.012, 0.012, 0.016))
        fr = A.glow(fr, (960, -60), 760, 0.55, (1.0, 0.74, 0.40))                      # 顶上天平金光（主光）
        fr = fx2.god_rays(fr, (960, -40), strength=0.45, length=1.0, color=(1.0, 0.78, 0.45), t=t, src_r=200)
        fr = RAIN.draw(fr, t, 0.8, angle=6, light=(960, 0), layers=(0, 1))
        fr = fog(fr, t, 2, 380, 760, 0.35, (0.20, 0.16, 0.12), speed=(-40, 0), light=(960, 0))
        # 铜链：自盘沿两侧升出画外（链环交替正/侧）
        for side in (-1, 1):
            x0_, y0_ = self.CX + sway + side * (self.AX - 40), self.CY - 10
            x1_, y1_ = 960 + side * 260 + sway * 0.3, -120
            n = 22
            for k in range(n):
                a_ = k / n; x = x0_ + (x1_ - x0_) * a_; y = y0_ + (y1_ - y0_) * a_
                ang = math.degrees(math.atan2(y1_ - y0_, x1_ - x0_))
                if k % 2 == 0:
                    cv2.ellipse(fr, (int(x), int(y)), (18, 9), ang, 0, 360, (0.30, 0.20, 0.08), 4, cv2.LINE_AA)
                else:
                    cv2.ellipse(fr, (int(x), int(y)), (18, 3), ang, 0, 360, (0.45, 0.32, 0.14), 4, cv2.LINE_AA)
            fr = A.glow(fr, ((x0_ + x1_) / 2, (y0_ + y1_) / 2), 160, 0.06, (1.0, 0.7, 0.35), aspect=0.4)
        inner, wall, rimB, rimF = self.bowl(sway)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        # 盘内：暗铜 + 积水反光
        # 第七棒（critic_A_r4 P1-7）：盘面 = 铜质（同心铸纹环 + 后高前暗的受光 + 金光镜面斑 + 铜锈），不再平涂黑椭圆
        cxs = self.CX + sway
        re = np.sqrt(((xx - cxs) / self.AX) ** 2 + ((yy - self.CY) / self.AY) ** 2)
        ring = 0.78 + 0.22 * (np.cos(re * 38) ** 10) - 0.25 * (np.abs(re - 0.62) < 0.012) - 0.25 * (np.abs(re - 0.86) < 0.010)
        back = np.clip(1.25 - 0.95 * (yy - (self.CY - self.AY)) / (2 * self.AY), 0.25, 1.3)
        inn = ((0.45 + 0.7 * self.tex) * ring * back)[..., None] * np.array([0.27, 0.17, 0.075], np.float32)
        inn = inn + (np.exp(-(((xx - cxs + 260) / 360) ** 2 + ((yy - self.CY + 30) / 40) ** 2)) * (0.6 + 0.4 * self.tex2))[..., None] * np.array([0.55, 0.36, 0.15], np.float32)
        inn = inn + np.clip((self.tex - 0.66) * 4, 0, 1)[..., None] * np.array([0.015, 0.05, 0.045], np.float32)
        lipsh = np.clip(1 - (self.CY + self.AY - yy) / 70, 0, 1) * (yy < self.CY + self.AY)            # 前沿唇口在盘面投下的内影
        inn = inn * (1 - 0.6 * lipsh[..., None])
        fr = fr * (1 - inner[..., None]) + inn * inner[..., None]
        fr = fr + (rimB * 0.7 + cv2.GaussianBlur(rimB, (0, 0), 4) * 0.25)[..., None] * np.array([0.85, 0.60, 0.30], np.float32) * 0.8
        # 第八棒（critic_A_r5 P0-3）：人与盘面的接触 —— 顶光正下方的软接触阴影 + 膝/靴下的暗核；盘面上一抹人影倒影（金面镜反）
        cs = np.zeros((H // 2, W // 2), np.float32)
        cv2.ellipse(cs, (int((930 + sway) / 2), int((self.CY + 70 + bob) / 2)), (300 if heap else 150, 34 if heap else 26), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        cs2 = np.zeros_like(cs)
        cv2.ellipse(cs2, (int((900 + sway) / 2), int((self.CY + 78 + bob) / 2)), (240 if heap else 80, 10), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        cs = cv2.resize(cv2.GaussianBlur(cs, (0, 0), 14) * 0.75 + cv2.GaussianBlur(cs2, (0, 0), 4) * 0.6, (W, H)) * inner
        fr = fr * (1 - np.clip(cs, 0, 0.92)[..., None])
        # 人：单膝跪在盘中，盘沿以下被盘壁挡住（kneel_pan_fix：臂/刀/腿间封闭灰底洞清掉）
        z0 = np.zeros_like(fr)
        if heap:   # 纸人堆：去黄（低饱和、偏冷白纸色），底部 ~40px 被盘面裁线吃掉 → 读作「堆在盘里」；纸人边缘随风轻颤
            Pk, ik = A.place(z0, t, os.path.join(R5._R5A, 'paper_heap_v1_cut.png'), (930 + sway, self.CY + 100 + bob),
                             w=800 * (1 + 0.02 * u), anc=(0.5, 1.0), rim=COLD, rim_amt=2.2, rim_dir=(0.5, -0.85), wind=5,
                             grade=dict(expo=0.66, sat=0.36, gamma=1.16, tint=(1.0, 0.98, 0.96)))
        else:
            Pk, ik = A.place(z0, t, R8.kneel_pan_fix(), (930 + sway, 1030 + bob), h=820 * (1 + 0.02 * u), rim=COLD,
                             rim_amt=3.2, rim_dir=(0.5, -0.85), wind=9, grade=dict(expo=0.80, sat=0.5, gamma=1.12, tint=(1.03, 1.0, 0.96)))
        Ak = ik['A']
        y_c = int(self.CY + 60 + bob)
        hgt = 150
        # 第十一棒：人前铜面一抹顶光镜面亮带（倒影要有亮底才读得出：暗人影压在亮铜上）
        shn = np.exp(-(((xx - (930 + sway)) / 430) ** 2 + ((yy - (y_c + 26)) / 26) ** 2)) * inner * np.clip((yy - y_c + 4) / 6, 0, 1)
        fr = fr + shn[..., None] * np.array([0.60, 0.40, 0.17], np.float32) * (0.9 + 0.2 * self.tex2[..., None])
        if y_c - hgt > 0:
            refl = cv2.flip(Pk[y_c - hgt:y_c], 0); ra = cv2.flip(Ak[y_c - hgt:y_c], 0)[..., None]
            yend = min(H, y_c + hgt)
            g_ = np.linspace(0.80, 0.0, yend - y_c, dtype=np.float32)[:, None, None] ** 1.1 * inner[y_c:yend, :, None]   # 第十一棒：0.62→0.80（倒影区由 36px 扩到 ~90px）
            fr[y_c:yend] = fr[y_c:yend] * (1 - ra[:yend - y_c] * g_ * 0.85) + (cv2.GaussianBlur(refl[:yend - y_c], (0, 0), 2.5) * 1.6 + 0.10 * ra[:yend - y_c]) * g_ * np.array([1.0, 0.82, 0.55], np.float32)
            # 膝/靴压在铜面上的一线接触高光（顶光在盘面掠射）
            hl = np.zeros((H // 2, W // 2), np.float32)
            cv2.ellipse(hl, (int((935 + sway) / 2), int((self.CY + 64 + bob) / 2)), (95, 5), 0, 180, 360, 1.0, 2, cv2.LINE_AA)
            hl = cv2.resize(cv2.GaussianBlur(hl, (0, 0), 1.5), (W, H)) * inner * (1 - Ak)
            fr = fr + hl[..., None] * np.array([0.9, 0.62, 0.28], np.float32) * 0.9
        # 第十一棒（critic_A_r7 P1-5，第二次提）：人后移后，膝下（盘面以下）的精灵部分裁掉（软边），盘面上露出完整倒影
        clip = np.clip((y_c + 14 - yy) / 8, 0, 1)[..., None]
        fr = fr * (1 - Ak[..., None] * clip) + Pk * clip
        fr = A.glow(fr, (930 + sway, 300 + bob + 52), 260, 0.10, (1.0, 0.72, 0.4))
        # 盘壁：青铜（铸纹环带 + 铜锈 + 随摆动滑过的镜面高光）
        rr = (yy - self.CY) / self.DEP
        rings = 0.55 + 0.45 * (np.sin(rr * 46) ** 12)
        spec = np.exp(-((xx - (520 + 900 * u + 3 * sway)) / 220) ** 2) * np.clip(1 - rr * 1.4, 0, 1)
        bronze = ((0.45 + 0.8 * self.tex) * rings * (1.0 - 0.75 * np.clip(rr, 0, 1)))[..., None] * np.array([0.20, 0.13, 0.06], np.float32)
        bronze = bronze + spec[..., None] * np.array([0.65, 0.46, 0.22], np.float32)
        bronze = bronze + np.clip((self.tex - 0.64) * 4, 0, 1)[..., None] * np.array([0.02, 0.07, 0.06], np.float32)
        wet = (np.clip(np.sin(xx / 17 + self.tex2 * 9) * 0.5 + 0.5, 0, 1) ** 10)[..., None] * np.array([0.10, 0.10, 0.12], np.float32)
        fr = fr * (1 - wall[..., None]) + (bronze + wet) * wall[..., None]
        # 「里」：铸文金光灌注（27.66）——先暗刻槽，再自下而上灌满熔金
        a_l = t - tl
        G = T.Layer()
        gp = clamp01((t - (tl - 0.12)) / 0.3)
        if gp > 0:
            g = T.glyph('里', 'kai', 165)
            gx, gy = 640 + sway, 795                                                    # 第八棒：整字落在盘壁上（原 742 顶部被前唇口盖住读成「王」）
            h_, w_ = g.shape
            fill = np.clip((np.arange(h_)[:, None] - h_ * (1 - eout(clamp01(a_l / 0.35)))) / 6, 0, 1) if a_l > 0 else np.zeros((h_, 1))
            groove = g * gp
            Lg = np.zeros((H, W), np.float32); Lf = np.zeros((H, W), np.float32)
            ys, xs = int(gy - h_ / 2), int(gx - w_ / 2)
            Lg[ys:ys + h_, xs:xs + w_] = groove; Lf[ys:ys + h_, xs:xs + w_] = g * fill
            sh = np.clip(Lg - cv2.warpAffine(Lg, np.float32([[1, 0, 4], [0, 1, 5]]), (W, H)), 0, 1)
            fr = fr * (1 - 0.8 * Lg[..., None]) + Lg[..., None] * 0.01
            fr = fr * (1 - 0.5 * sh[..., None])
            hot = (Lf * 2.2 + cv2.GaussianBlur(Lf, (0, 0), 10) * 1.2 + cv2.GaussianBlur(Lf, (0, 0), 40) * 0.5)
            fr = fr + hot[..., None] * np.array([1.0, 0.70, 0.30], np.float32) * (1.0 + 0.8 * math.exp(-max(0, a_l) / 0.2))
            if 0 <= a_l < 0.5:
                fr = K.sparks(fr, t, 271, (gx, gy + 100), n=50, life=0.6, speed=(150, 500), dirc=(0, -1), spread=1.4, grav=700,
                              area=(100, 10), amt=0.7, t0=tl, burst=True, color=(1.0, 0.75, 0.4))
        # 盘沿（前沿金线）+ 雨溅
        # 盘沿厚度：上沿亮铜倒角（随镜面斑走）+ 下沿暗铜唇面 20px（第七棒：去霓虹金线）
        lipT = np.zeros((H, W), np.float32); lipU = np.zeros((H, W), np.float32)
        cv2.ellipse(lipT, (int(cxs), self.CY - 4), (self.AX, self.AY), 0, 0, 180, 1.0, 7, cv2.LINE_AA)
        cv2.ellipse(lipU, (int(cxs), self.CY + 12), (self.AX, self.AY + 4), 0, 0, 180, 1.0, 20, cv2.LINE_AA)
        lipU = np.clip(lipU - lipT, 0, 1)
        fr = fr * (1 - lipU[..., None]) + (lipU * (0.5 + 0.6 * self.tex))[..., None] * np.array([0.10, 0.06, 0.025], np.float32) * (1 + 3 * spec[..., None])
        fr = fr * (1 - lipT[..., None]) + lipT[..., None] * (np.array([0.50, 0.34, 0.15], np.float32) + spec[..., None] * np.array([0.6, 0.45, 0.25], np.float32))
        fr = fr + cv2.GaussianBlur(lipT * spec, (0, 0), 6)[..., None] * np.array([1.0, 0.75, 0.4], np.float32) * 0.5
        for k in range(7):
            ts_ = self.t0 + 0.22 * k + 0.05
            sx = 260 + 230 * k + sway
            ex = (sx - self.CX - sway) / self.AX
            sy = self.CY + self.AY * math.sqrt(max(0, 1 - ex * ex))
            fr = K.sparks(fr, t, 300 + k, (sx, sy), n=14, life=0.35, speed=(120, 320), dirc=(0, -1), spread=1.6, grav=1500, area=(30, 4),
                          amt=0.5, t0=ts_, burst=True, color=(0.75, 0.82, 0.95))
        # 朱墨滴：自右链落下，28.10 打在盘沿溅开 →「称」「量」朱墨在盘壁晕开
        rx = 1380 + sway
        if t < td:
            q = clamp01((t - (td - 0.45)) / 0.45)
            yd = 160 + (self.CY + 60 - 160) * q ** 2
            grow = clamp01((t - self.t0) / 0.5)
            fr = A.glow(fr, (rx, yd), 6 + 6 * grow, 1.5, (0.80, 0.06, 0.04), aspect=1 - 0.5 * q)
            fr = A.glow(fr, (rx - 3, yd - 4), 3, 0.8, (1.0, 0.7, 0.6))
        else:
            a = t - td
            fr = K.sparks(fr, t, 281, (rx, self.CY + 70), n=50, life=0.5, speed=(150, 600), dirc=(0, -1), spread=1.5, grav=1500,
                          area=(30, 6), amt=0.9, t0=td, burst=True, color=(0.85, 0.08, 0.05))
            # 第七棒：去掉「称|量」中间那条竖向墨流线（看不出动机）
        L = T.Layer()
        for i, (ch, k) in enumerate((('称', 9), ('量', 10))):
            p = clamp01((t - (CT(3, k) - 0.12)) / 0.4)
            if p > 0: L.paste(T.ink_bleed_glyph(ch, 'kai', 160, p, seed=9 + i, bleed=1.0), 1250 + 220 * i + sway, 795, (0.82, 0.08, 0.06))
        fr = T.compose(fr, L, shadow=0.5, glow=0.35, glow_color=(0.9, 0.12, 0.06))
        fr = RAIN.draw(fr, t, 0.7, angle=6, layers=(2,))
        return fr, (3 if 0 <= a_l < 0.08 else 0)


# V11 28.93–29.86 ECU 刀身当面（blade_face 精灵，第二棒替换单眼重复）：竖刀把脸劈成两半，两侧各一只眼；
#     左侧朱红轮廓光（承接 V10 朱墨），29.40「我」起一线红光沿刃口自下而上爬升 —— 「我杀过」之前的一口气
class V11(Shot):
    def __init__(self):
        import a_r6                                                                      # 第八棒（P1-7 左上灰残片）：发外灰底按与灰底色距清掉，刀身保护
        self.path = a_r6.hair_clean('A/blade_face', protect=(0.45, 0.0, 0.57, 1.0), thr=0.07, soft=0.08, band=81)
    def render(self, t):
        u = self.u(t)
        fr = night((0.012, 0.005, 0.005), (0.035, 0.012, 0.012))
        fr = A.glow(fr, (300, 500), 600, 0.25, (0.7, 0.10, 0.06))
        fr, info = A.place(fr, t, self.path, (960 + 30 * u, 560), w=2350 * (1 + 0.05 * eio(u)), anc=(0.5, 0.40), rim=REDR, rim_amt=1.3,
                           rim_dir=(-0.8, -0.3), grade=dict(expo=0.70, sat=0.45, tint=(1.0, 0.95, 0.95), gamma=1.2), wind=4, breathe=0.0)
        xx = np.arange(W, dtype=np.float32)[None, :, None]
        fr = fr * (0.45 + 0.65 * np.clip(1 - np.abs(xx - 960) / 1100, 0, 1))
        # 刃口红光：沿刀身（屏幕上 x≈刀中线）自下而上
        bx0, by0 = info['to_scr']((0.5, 1.0)); bx1, by1 = info['to_scr']((0.5, 0.0))
        q = clamp01((t - (self.t0 + 0.22)) / 0.5)
        if q > 0:
            y = by0 + (by1 - by0) * eio(q)
            yy = np.arange(H, dtype=np.float32)[:, None]
            xs = np.exp(-((np.arange(W, dtype=np.float32)[None] - bx0 - 30 * u) / 8) ** 2)
            trail = np.clip((yy - y) / 600, 0, 1) * (yy > y) * np.exp(-np.clip(yy - y, 0, None) / 500)
            head = np.exp(-((yy - y) / 40) ** 2)
            band = (head * 2.0 + trail * 0.8) * xs
            fr = fr + (band * 4.0 + cv2.GaussianBlur(band, (0, 0), 16) * 6.0)[..., None] * np.array([1.0, 0.28, 0.18], np.float32)
        fr = ASH.draw(fr, t, 0.3, wind=(-60, -20))
        return fr, 0


# V12 29.86–30.77 MS 斜斩：左半画面，鬼屠斩倒恶徒（甲兵剪影倒下）；巨字「杀」朱红
class V12(Shot):
    def __init__(self):
        import crowd
        self.vill = crowd.soldier_sprite(None, arm=0.6, view='front', seed=2) if hasattr(crowd, 'soldier_sprite') else None
        T.warm('杀', 'kai', 360)
    def render(self, t):
        if R5.ON['sha_fang'] and not R6C_OFF('sf7'):                               # r6 第三棒 #7：殺/放 一镜到底（见 _sf_sha_world / V13.r6c）
            fr = _sf_sha_world(t)
            return _sf_word(fr, t), ((5 if R6F_OFF('sf7b') else 3) if 0 <= t - CT(4, 1) < 0.1 else 0)   # r6 第六棒：斩杀帧色差 5→3
        u = self.u(t); ts = CT(4, 1)
        fr = night((0.04, 0.008, 0.008), (0.12, 0.02, 0.02))
        fr = A.glow(fr, (1400, 420), 500, 0.35, (0.9, 0.2, 0.12))
        fr = _rain_curtain(fr, t, u, ts)
        a = t - ts
        # 恶徒（第二棒：villain_fall 精灵替换代码剪影）：被斩后沿斩线一刀两断、上半滑落
        fr = _villain_spr(fr, t, a, (1330, 1000), 640)
        fr, info = A.place(fr, t, S('S014/slash_diag'), (720, 990), h=640, rim=REDR, rim_amt=3.0, wind=10, grade=dict(expo=0.85, sat=0.6))
        if a >= 0:
            fr = streak(fr, 480, 1700, 300, a / 0.09, w=6, amt=1.5, ang=32, col=(1.0, 0.85, 0.8))
            fr = K.sparks(fr, t, 31, (1200, 620), n=60, life=0.6, speed=(200, 800), dirc=(1, -0.4), spread=1.0, grav=1200, area=(60, 60), amt=0.8, t0=ts, burst=True)
        L = T.Layer(); p = cprog(4, [1], t, 0.16)[0]
        if R5.ON['sha_fang']:   # 第五轮 7：繁体书法「殺」（cal_sha 生图），与 V13「放」同位同大
            if p > 0: L.paste(R5.ink_write(R5.cal_alpha(*SF_SHA), p, seed=4), *SF_AT, SF_RED)
        elif p > 0: L.paste(BG('杀', 'kai', 360, p, seed=4), 330, 400, (0.88, 0.10, 0.07))
        fr = T.compose(fr, L, shadow=0.6, glow=0.45, glow_color=(0.9, 0.1, 0.06))
        return fr, (5 if 0 <= a < 0.1 else 0)


# 第五轮 7：殺/放 同位同构图（V12 → V13 只换一笔：人物同位置同大小、右侧恶徒 → 跪地混账、字形 殺 → 放 原位变换）
SF_SHA, SF_FANG = ('cal_sha_v1', 420), ('cal_fang_v1', 420)
SF_AT, SF_RED, SF_COLD = (330, 400), (0.88, 0.10, 0.07), (0.72, 0.80, 0.94)

# ---- r6 第三棒 #7（评审 2ce318b 打回 7 分）：殺/放 一镜到底 ----
#   用户原话：「杀」「放」同一位置、用繁体、人物构图一致，文字做转变动画，凸显反差。
#   · V12/V13 之间不再切镜（CUTS 'cont'：无转场、无冲击帧、机位连续）；29.83–31.07「殺」世界不动（鬼屠斩后定势、恶徒两断倒下沉进雾里）。
#   · 唯一的变化 = 31.07 起一线冷刀光（近竖直的擦除前沿）：先随距离场流变一起扫过「殺」（31.07→31.33，与字同速），再甩过全画面（→31.43「放」字拍）；
#     前沿左边是「放」世界（冷光、同位同大的鬼屠收刀、恶徒位上跪地混账），右边仍是「殺」世界。不在殺字静止时换人。
#   · 脚点 990→900（有效区下沿 960 之内）；恶徒断口羽化 + 血雾，下半身随后屈膝沉入地雾，不留硬边黑块。
SF_FEET = 900                                     # 两个世界共用脚点（屏幕 y）
SF_HERO_X, SF_OPP_X = 720, 1330
SF_TIP, SF_HILT = (294.0, 741.0), (630.0, 534.0)       # 殺世界 slash_diag 刀尖 / 护手屏幕位置（h=640、脚点 (720,900)，30.0 实测）
SF_FANG_DX = 110                                  # r6 第六棒：sheath_same 头中心 740 / 胯 737，slash_diag 头 849 / 胯 803（同 h=640、同脚点）→ 放世界整体右移 110px
def _sf_k():
    tm = CT(4, 6); return tm, tm - 0.40                                     # 「放」字拍、变换起点（31.03）
def _sf_edge(t):
    """擦除前沿 x（屏幕顶端 y=120 处）：None = 尚未开始；随字形流变同速扫过字（120→560），再加速甩出画面。"""
    tm, k0 = _sf_k()
    a = t - (k0 + 0.04)
    if a < 0: return None
    if a < 0.26: return 90 + 470 * (a / 0.26)
    b = (a - 0.26) / 0.13
    return 560 + 1700 * ein(min(1.0, b)) + (0 if b <= 1 else 4000)
SF_TILT = math.tan(math.radians(9))                                         # 前沿上端偏右 9°（刀势）
def _sf_mask(xe):
    """1 = 已在前沿左侧（放世界）；前沿 24px 羽化。"""
    yy = np.arange(H, dtype=np.float32)[:, None]; xx = np.arange(W, dtype=np.float32)[None, :]
    xl = xe - (yy - 120) * SF_TILT
    return np.clip((xl - xx) / 24 + 0.5, 0, 1)
def _sf_edge_glow(fr, xe, amt=1.0):
    """前沿刀光：3px 冷白芯 + 14px/50px 冷辉，上下两端收尖；不画实心头。"""
    if xe is None or xe > W + 200: return fr
    yy = np.arange(H, dtype=np.float32)[:, None]; xx = np.arange(W, dtype=np.float32)[None, :]
    d = np.abs(xx - (xe - (yy - 120) * SF_TILT))
    taper = np.clip((yy - 110) / 260, 0, 1) * np.clip((970 - yy) / 260, 0, 1)
    core = np.exp(-(d / 1.6) ** 2) * taper
    g = core * 1.3 + np.exp(-(d / 14) ** 2) * taper * 0.35 + np.exp(-(d / 60) ** 2) * taper * 0.12
    return fr + g[..., None] * np.array([0.80, 0.90, 1.0], np.float32) * amt


def _sf_sha_world(t):
    """「殺」世界（无字）：红雨幕、斩后定势的鬼屠、被斩两断倒下的恶徒。V12 全镜 + V13 擦除前沿右侧共用。"""
    ts = CT(4, 1); a = t - ts
    fr = night((0.04, 0.008, 0.008), (0.12, 0.02, 0.02))
    fr = A.glow(fr, (1400, 420), 500, 0.35, (0.9, 0.2, 0.12))
    u = clamp01((t - V12.t0) / (V13.t1 - V12.t0))
    fr = _rain_curtain(fr, t, u, ts)
    fr = _sf_ground(fr, (0.30, 0.05, 0.04))
    fr = _villain_spr6(fr, t, a, (SF_OPP_X, SF_FEET + 10), 640)
    fr = _sf_contact(fr, SF_HERO_X + 10, SF_FEET)
    sf7c = a >= 0 and not R6F_OFF('sf7b') and not R6F_OFF('sf7c')
    if a >= 0 and not R6F_OFF('sf7b') and R6F_OFF('sf7c'):                      # r6 第六棒 #7：斩杀刀光 = 从恶徒断口穿回鬼屠刀尖的一道细刀弧（画在人物后，被人物遮挡），不再是独立白柱
        q = clamp01(a / 0.09); fd = math.exp(-max(0.0, a - 0.09) / 0.16)
        if fd > 0.03:
            P0 = (1560.0, 702.0); P1 = SF_TIP; Pe = (P0[0] + (P1[0] - P0[0]) * eout(q), P0[1] + (P1[1] - P0[1]) * eout(q))
            fr = R5.blade_arc(fr, SF_HILT, P0, Pe, depth=0.03, width=0.07, amt=1.7 * fd, col=(1.0, 0.86, 0.80))
    fr, info = A.place(fr, t, S('S014/slash_diag'), (SF_HERO_X, SF_FEET), h=640, rim=REDR, rim_amt=3.0, wind=10, grade=dict(expo=0.85, sat=0.6))
    if sf7c: fr = _sf_strike7c(fr, a)
    if a >= 0 and R6F_OFF('sf7b'):
        fr = streak(fr, 480, 1700, 300, a / 0.09, w=6, amt=1.5, ang=32, col=(1.0, 0.85, 0.8))
        fr = K.sparks(fr, t, 31, (1200, 620), n=60, life=0.6, speed=(200, 800), dirc=(1, -0.4), spread=1.0, grav=1200, area=(60, 60), amt=0.8, t0=ts, burst=True)
    return fr


SF_HIT = (1215.0, 575.0)                          # r6 POLISH1：命中点 = 刀弧尾端落在恶徒断口（腰）处的屏幕位置
SF_FLASH_CAP = 0.74
SF_GRIP = (600.0, 553.0)                          # 鬼屠右手握刀处偏刀身一点（护手 SF_HILT 沿刀身 9%）
def _sf_strike7c(fr, a):
    """r6 POLISH1（REVIEW_A_r6e #7-③ 建议）：斩杀刀光起点从袍摆下沿挪到鬼屠右手/刀身。
    · 刀弧画在人物前：刀尖轨迹从恶徒断口（尾，淡）沿一条微微上拱的弧回到鬼屠右手握刀处（前缘，最亮）= 「这一刀是他挥出来的」；
    · 刀身同帧一线冷白刃光（护手→刀尖），把刀弧前缘接到刀上；
    · 命中点 902/903f 两帧冷白闪（峰值软限到成片 ≤235），之后 τ0.12s 衰减。开关 A_R6F_OFF=sf7c 回第六棒。"""
    fd = 1.0 if a < 0.05 else math.exp(-(a - 0.05) / 0.12)
    if fd < 0.03: return fr
    fr = R5.blade_arc(fr, (900.0, 330.0), SF_HIT, SF_GRIP, depth=-0.10, width=0.09, amt=1.25 * fd, col=(0.86, 0.92, 1.0))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # 刀身刃光：护手 → 刀尖细线（σ1.2 芯 + σ7 晕），尖端收细
    hx, hy = SF_HILT; tx, ty = SF_TIP; vx, vy = tx - hx, ty - hy; Lb = math.hypot(vx, vy)
    s_ = np.clip(((xx - hx) * vx + (yy - hy) * vy) / (Lb * Lb), 0, 1)
    d = np.hypot(xx - (hx + s_ * vx), yy - (hy + s_ * vy))
    tp = np.clip(s_ / 0.08, 0, 1) * (1 - 0.5 * s_)
    edge = (np.exp(-(d / 1.2) ** 2) * 0.55 + np.exp(-(d / 7) ** 2) * 0.12) * tp
    fr = fr + edge[..., None] * np.array([0.85, 0.92, 1.0], np.float32) * fd
    # 命中冷白闪：只 2 帧（a<0.05 → 902/903f），中心 = 刀弧尾端落在恶徒断口处；沿刀弧方向拉长的冷白芯 + 宽冷晕
    if a < 0.05:
        k = 1.0 if a < 0.02 else 0.55
        dx_, dy_ = xx - SF_HIT[0], yy - SF_HIT[1]
        th = math.atan2(SF_HIT[1] - SF_GRIP[1], SF_HIT[0] - SF_GRIP[0]); c_, s2 = math.cos(th), math.sin(th)
        u_, v_ = dx_ * c_ + dy_ * s2, -dx_ * s2 + dy_ * c_
        g = (np.exp(-(u_ / 70.0) ** 2 - (v_ / 9.0) ** 2) * 0.50 + np.exp(-(dx_ ** 2 + dy_ ** 2) / (2 * 90.0 ** 2)) * 0.16
             + np.exp(-(dx_ ** 2 + dy_ ** 2) / (2 * 300.0 ** 2)) * 0.07) * k
        add = g[..., None] * np.array([0.88, 0.94, 1.0], np.float32)
        out = fr + add
        cap = SF_FLASH_CAP                                            # 软限：闪光区不顶到高光肩（成片 ≤235）
        m = np.clip(g / 0.04, 0, 1)[..., None]
        lim = np.where(out > cap, cap + (1 - np.exp(-(out - cap) / 0.06)) * 0.06, out)
        fr = out * (1 - m) + lim * m
    return fr


def _sf_fang_world(t):
    """「放」世界（无字）：同光位冷调、同位同大的鬼屠收刀、恶徒位上跪地混账。"""
    u = clamp01((t - V13.t0) / (V13.t1 - V13.t0))
    fr = night((0.012, 0.016, 0.03), (0.05, 0.06, 0.08))
    fr = A.glow(fr, (1400, 420), 520, 0.3, (0.55, 0.62, 0.85))
    fr = fog(fr, t, 0, 200, 900, 0.35, (0.18, 0.21, 0.28), speed=(-30, 0), light=(1400, 420))
    fr = RAIN.draw(fr, t, 0.9, angle=4, light=(1400, 420), layers=(0, 1))
    fr = _sf_ground(fr, (0.20, 0.23, 0.30))
    dx = 0 if R6F_OFF('sf7b') else SF_FANG_DX                                   # r6 第六棒 #7：放世界鬼屠与殺世界同位（头/上身中心对齐），擦换时不出双头
    fr = _sf_contact(fr, SF_HERO_X + 10 + dx, SF_FEET)
    fr, _ = A.place(fr, t, os.path.join(R5._R5A, 'sheath_same_v1_cut.png'), (SF_HERO_X + dx, SF_FEET), h=640, rim=COLD, rim_amt=3.0, wind=7,
                    grade=dict(expo=0.85, sat=0.55))
    bow = 1.0 + 6.0 * eio(u) + 1.6 * math.sin(t * 6.0)
    trem = 2.5 * math.sin(t * 41) + 1.5 * math.sin(t * 67)
    fr = _sf_contact(fr, SF_OPP_X + 10 + dx, SF_FEET + 4, rx=230)
    fr, _ = A.place(fr, t, A.bg_matte('A/kneel_beg'), (SF_OPP_X + 10 + dx + trem, SF_FEET + 4), h=500, anc=(0.5, 1.0), rim=COLD, rim_amt=2.4,
                    rim_dir=(-0.7, -0.6), grade=dict(expo=0.62, sat=0.3, gamma=1.2), wind=3, rot=-bow)
    return fr


_SFG = {}
def _sf_ground(fr, col):
    """脚下地面：脚点线下一片低雾地面 + 微弱反光，人物踩在实处（原脚点在黑边下，画面里没有地）。"""
    k = tuple(col)
    if k not in _SFG:
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        _SFG[k] = (np.clip((yy - (SF_FEET - 40)) / 70, 0, 1) * np.exp(-np.clip(yy - SF_FEET, 0, None) / 160)).astype(np.float32)
    return fr + _SFG[k] * np.array(col, np.float32) * 0.35


def _sf_contact(fr, x, y, rx=200):
    yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32) * 4
    sh = np.exp(-(((xx - x) / rx) ** 2 + ((yy - y - 4) / 14) ** 2)) * 0.8 + np.exp(-(((xx - x) / (rx * 1.7)) ** 2 + ((yy - y - 6) / 34) ** 2)) * 0.35
    return fr * (1 - 0.8 * cv2.resize(sh, (W, H))[..., None])


def _villain_clean_path():
    """r6 第六棒：villain_fall 的 bg_matte 在头发外围留了一团不透明的浅灰原底（≈0.43 灰、低饱和、低纹理）——评审说的「灰白发边」。
    按「浅灰 + 低饱和 + 低纹理」或「半透明 + 浅灰」把这团原底从 alpha 里抠掉，缓存成新 PNG。"""
    out = A.CACHE + '/vf_clean_r6f.png'
    if os.path.exists(out): return out
    im = cv2.imread(A.bg_matte('A/villain_fall'), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
    rgb, a = im[..., :3], im[..., 3]
    lum = rgb.mean(-1); sat = rgb.max(-1) - rgb.min(-1)
    m1 = cv2.GaussianBlur(lum, (0, 0), 3); sd = np.sqrt(np.clip(cv2.GaussianBlur(lum * lum, (0, 0), 3) - m1 * m1, 0, None))
    g = np.clip((lum - 0.26) / 0.08, 0, 1) * np.clip((0.075 - sat) / 0.035, 0, 1) * np.clip((0.075 - sd) / 0.03, 0, 1)
    g = np.maximum(g, np.clip((0.97 - a) / 0.15, 0, 1) * np.clip((lum - 0.24) / 0.08, 0, 1) * np.clip((0.09 - sat) / 0.04, 0, 1))
    g = cv2.GaussianBlur(cv2.morphologyEx(g, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)), (0, 0), 2)
    im[..., 3] = a * (1 - g)
    cv2.imwrite(out, (np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8))
    return out


def _villain_relight(col, Al, at):
    """r6 第六棒 #7（评审：恶徒灰白发边、去色冷灰像贴上去的照片）：
    ① 去边色 decontaminate：alpha<0.97 的边带颜色用内部（alpha≥0.97）颜色向外扩散替换，抠图带进来的浅底色不再成环；
    ② 受同一盏红光：按亮度重新着色成鬼屠同色温的暗红（亮部偏朱、暗部压深），不再是冷灰照片；
    ③ 逆光侧（朝画面右上红光 1400,420）补一道 3–6px 暗红轮廓光。"""
    inner = (Al >= 0.97).astype(np.float32)
    num = cv2.GaussianBlur(col * inner[..., None], (0, 0), 5); den = cv2.GaussianBlur(inner, (0, 0), 5)[..., None]
    fill = num / np.maximum(den, 1e-4)
    band = np.clip((0.97 - Al) / 0.5, 0, 1)[..., None] * (den > 1e-3)
    col = col * (1 - band) + fill * band
    lum = col @ np.array([0.30, 0.55, 0.15], np.float32)
    lum = lum / (1 + lum * 0.4)
    red = np.stack([lum * 1.05, lum * 0.42, lum * 0.36], -1)
    col = col * 0.30 + red * 0.70 + np.array([0.035, 0.006, 0.005], np.float32)
    Ab = (Al > 0.5).astype(np.float32)
    rimw = np.clip(Ab - cv2.erode(Ab, np.ones((9, 9), np.uint8)), 0, 1)
    rimw = cv2.GaussianBlur(rimw, (0, 0), 1.5)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    gx = cv2.Sobel(cv2.GaussianBlur(Ab, (0, 0), 6), cv2.CV_32F, 1, 0); gy = cv2.Sobel(cv2.GaussianBlur(Ab, (0, 0), 6), cv2.CV_32F, 0, 1)
    nrm = np.sqrt(gx * gx + gy * gy) + 1e-6
    lx, ly = 0.75, -0.66                                                                              # 光从右上来
    facing = np.clip(-(gx * lx + gy * ly) / nrm, 0, 1)
    return col + (rimw * facing)[..., None] * np.array([0.55, 0.07, 0.04], np.float32)


def _villain_spr6(fr, t, a, at, h, deg=32):
    """r6 第三棒：恶徒两断改版 —— 断口 3px 羽化 + 朱红血雾（不再是直红线 + 硬边黑块）；剪影带红色环境光（不读成纯黑块）；
    上半沿斩线滑开后受重力坠落，下半身 0.2s 后屈膝后仰下沉，两片都沉进脚下地雾（无原地半透明淡出、无残影）。"""
    z = np.zeros((H, W, 3), np.float32)
    back = 0.0 if a < 0 else 40 * eout(a / 0.4)
    P, info = A.place(z, t, A.bg_matte('A/villain_fall') if R6F_OFF('sf7b') else _villain_clean_path(), (at[0] + back, at[1]), h=h, anc=(0.5, 1.0), rim=REDR, rim_amt=2.6,
                      rim_dir=(0.8, -0.5), grade=dict(expo=0.80, sat=0.12, tint=(1.08, 0.94, 0.90)), wind=8, rot=-6 * eout(max(0, a) / 0.5))
    Al = info['A'][..., None]
    col = P / np.maximum(Al, 1e-3)
    if R6F_OFF('sf7b'):
        Al2 = np.clip((Al - 0.30) / 0.70, 0, 1)
        Al2 = cv2.erode(Al2[..., 0], np.ones((3, 3), np.uint8))                                      # 收 matte 灰边（发外灰晕）
        Al2 = cv2.GaussianBlur(Al2, (0, 0), 0.8)[..., None]                                           # 再 1px 羽化
        col = col + np.array([0.09, 0.014, 0.011], np.float32)                                        # 红色环境光托起暗部
    else:
        col = _villain_relight(col, Al[..., 0], at)
        Al2 = np.clip((Al - 0.45) / 0.55, 0, 1)
        Al2 = cv2.erode(Al2[..., 0], np.ones((5, 5), np.uint8))                                      # r6 第六棒：alpha 内收 ≈2.5px（发梢灰白残边整圈吃掉）
        Al2 = cv2.GaussianBlur(Al2, (0, 0), 0.9)[..., None]
    P = col * Al2; Al = Al2
    if a > 0:
        th = math.radians(deg); cy = at[1] - 0.55 * h
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        n = -(xx - (at[0] + back)) * math.sin(th) + (yy - cy) * math.cos(th)
        side = np.clip(0.5 - n / 3.0, 0, 1)[..., None]                                               # 断口 3px 羽化（原 n<0 硬切）
        sl = 240 * a ** 1.2
        M = np.float32([[1, 0, sl * math.cos(th)], [0, 1, sl * math.sin(th) + 620 * a * a]])
        Pu = cv2.warpAffine(P * side, M, (W, H)); Au = cv2.warpAffine(Al * side, M, (W, H))[..., None]
        q = clamp01((a - 0.20) / 0.55)
        Ml = cv2.getRotationMatrix2D((float(at[0] + back), float(at[1])), -24 * eio(q), 1.0); Ml[1, 2] += 420 * q * q
        Pl = cv2.warpAffine(P * (1 - side), Ml, (W, H)); Alw = cv2.warpAffine(Al * (1 - side), Ml, (W, H))[..., None]
        P = Pl * (1 - Au) + Pu; Al = Alw * (1 - Au) + Au
        gm = np.clip((at[1] + 20 - yy) / 110, 0, 1)[..., None] * (clamp01((a - 0.20) / 0.05) > 0) + (1 - clamp01((a - 0.20) / 0.05))
        fz = clamp01(1 - (a - 0.85) / 0.15)                                                            # 保险：1.0s 后无论如何退净
        P = P * gm * fz; Al = Al * gm * fz
        cut = np.exp(-(n / 4.0) ** 2) * cv2.GaussianBlur(info['A'], (0, 0), 4)                        # 血雾 + 断口余红（沿断面，不画孤立直线）
        mist = cv2.GaussianBlur(cut, (0, 0), 10 + 60 * a) * (1.6 * math.exp(-a / 0.45))
        fr = fr + (cut * 1.4 * math.exp(-a / 0.25) + mist)[..., None] * RED
    fr = fr * (1 - Al) + P
    if a > 0: fr = fog(fr, t, 2, 800, 960, 0.45 * clamp01(a / 0.3), (0.30, 0.05, 0.04), speed=(-40, 0))   # 脚下红地雾（吞下沉的两片）
    return fr


def _sf_word(fr, t, km=None):
    """左上同位的「殺」→「放」：V12 内逐笔写出；变换期距离场流变（前沿 = 擦除刀光）。"""
    if km is None:
        L = T.Layer(); p = cprog(4, [1], t, 0.16)[0]
        if p > 0: L.paste(R5.ink_write(R5.cal_alpha(*SF_SHA), p, seed=4), *SF_AT, SF_RED)
        return T.compose(fr, L, shadow=0.6, glow=0.45, glow_color=(0.9, 0.1, 0.06))
    al, w = R5.cal_morph(SF_SHA[0], SF_FANG[0], SF_SHA[1], km, spread=0.75)
    Lr = T.Layer(); Lc = T.Layer()
    Lr.paste(al * (1 - w), *SF_AT, SF_RED); Lc.paste(al * w, *SF_AT, SF_COLD)
    fr = T.compose(fr, Lr, shadow=0.6, glow=0.45, glow_color=(0.9, 0.1, 0.06))
    fr = T.compose(fr, Lc, shadow=0.7, glow=0.25, glow_color=(0.5, 0.6, 0.9))
    if 0 < km < 1:
        Le = T.Layer(); Le.paste(np.clip(4 * w * (1 - w) * al * 1.4, 0, 1), *SF_AT, (0.92, 0.96, 1.0))
        fr = T.compose(fr, Le, shadow=0.0, glow=0.6, glow_color=(0.7, 0.8, 1.0))
    return fr


def _rain_curtain(fr, t, u, ts):
    """第六棒（critic_A_r3 P1-6：竖条纹读成舞台幕布）：红光透过的纵深雨幕（三层不同速度/粗细的斜雨 + 层间红雾），
    29.96 斩下后雨幕沿 32° 斩线被刀风劈开一道空隙；前景一根焦外竹竿 + 一片焦外雨珠。"""
    fr = fog(fr, t, 0, 200, 900, 0.35, (0.30, 0.06, 0.05), speed=(40, 0), light=(1400, 420))
    a = t - ts
    yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
    th = math.radians(32); n = -(xx * 2 - 1200) * math.sin(th) + (yy * 2 - 620) * math.cos(th)
    gap = np.clip(np.abs(n) / (10 + 260 * eout(clamp01(a / 0.4))), 0, 1) if a >= 0 else np.ones_like(n)
    R0 = RAIN.draw(np.zeros((H, W, 3), np.float32), t, 1.0, angle=4, light=(1400, 420), layers=(0, 1))
    fr = fr + R0 * np.array([1.0, 0.45, 0.4], np.float32) * cv2.resize(gap, (W, H))[..., None] * 1.4
    fr = fog(fr, t, 1, 500, 960, 0.30, (0.25, 0.05, 0.04), speed=(-60, 0))
    Lp = np.zeros((H // 2, W // 2), np.float32)
    x0 = (1780 - 90 * u) / 2; cv2.line(Lp, (int(x0), 0), (int(x0 + 20), H // 2), 1.0, 36, cv2.LINE_AA)
    Lp = cv2.resize(cv2.GaussianBlur(Lp, (0, 0), 12), (W, H))[..., None]
    fr = fr * (1 - 0.9 * Lp)
    return fr


def _bamboo(fr, t, dx):
    """月下竹林竖条纹（后景）"""
    r = np.random.default_rng(91)
    L = np.zeros((H // 2, W // 2), np.float32)
    for i in range(34):
        x = (r.uniform(0, W) + dx * 800 * r.uniform(0.5, 1.5)) / 2
        w = r.uniform(4, 14) / 2; tone = r.uniform(0.3, 1)
        cv2.rectangle(L, (int(x), 0), (int(x + w), H // 2), tone, -1)
        for y in range(0, H // 2, int(r.uniform(40, 80))): cv2.line(L, (int(x - 1), y), (int(x + w + 1), y), tone * 0.5, 1)
    L = cv2.resize(cv2.GaussianBlur(L, (0, 0), 3), (W, H))
    return fr * (1 - 0.65 * L[..., None])


def _villain_spr(fr, t, a, at, h, deg=32):
    """恶徒精灵：先在黑底单独合成（得到预乘色 + alpha），斩后沿 deg 斜线分成两半，上半沿斩线滑开下坠；断口朱红。"""
    z = np.zeros((H, W, 3), np.float32)
    back = 0.0 if a < 0 else 40 * eout(a / 0.4)
    P, info = A.place(z, t, A.bg_matte('A/villain_fall'), (at[0] + back, at[1]), h=h, anc=(0.5, 1.0), rim=REDR, rim_amt=2.4,
                      rim_dir=(-0.8, -0.4), grade=dict(expo=0.75, sat=0.12, tint=(1.06, 0.94, 0.90)), wind=8, rot=-6 * eout(max(0, a) / 0.5))   # 第三棒：sat 0.5→0.12 去腿部青色溢色
    Al = info['A'][..., None]
    col = P / np.maximum(Al, 1e-3); Al2 = np.clip((Al - 0.25) / 0.75, 0, 1)                         # 第三棒：收 matte 灰边
    Al2 = np.minimum(Al2, cv2.erode(Al2[..., 0], np.ones((3, 3), np.uint8))[..., None] + 0.0)
    P = col * Al2; Al = Al2
    if a > 0:
        th = math.radians(deg); cy = at[1] - 0.55 * h
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        n = -(xx - at[0]) * math.sin(th) + (yy - cy) * math.cos(th)
        side = (n < 0).astype(np.float32)[..., None]
        sl = 240 * a ** 1.2
        M = np.float32([[1, 0, sl * math.cos(th)], [0, 1, sl * math.sin(th) + 260 * a * a]])
        Pu = cv2.warpAffine(P * side, M, (W, H)); Au = cv2.warpAffine(Al * side, M, (W, H))[..., None]
        P = P * (1 - side) * (1 - Au) + Pu; Al = Al * (1 - side) * (1 - Au) + Au     # 第三棒：上半盖在下半上（原相加 Al>1 → 背景被减成青色）
        seam = np.exp(-(n / 3.0) ** 2) * (np.abs(xx - at[0]) < h * 0.4)
        fr = fr + seam[..., None] * RED * 2.2 * math.exp(-a / 0.5) * cv2.GaussianBlur(info['A'], (0, 0), 6)[..., None] * 3
    fr = fr * (1 - Al) + P
    return fr


def _villain(fr, x, y, h, ang, red=False, cut=None):
    """恶徒剪影：宽肩甲兵（代码）；cut=(斩后秒, 角度)：沿斜线一刀两断，上半沿斩线滑落。"""
    m = np.zeros((H, W), np.float32)
    s = h / 100
    pts = [(-16, 0), (-12, -45), (-24, -62), (-20, -80), (-8, -86), (-7, -94), (7, -94), (8, -86), (20, -80), (24, -62), (12, -45), (16, 0)]
    th = math.radians(ang)
    P = [(x + (px * math.cos(th) - py * math.sin(th)) * s, y + (px * math.sin(th) + py * math.cos(th)) * s) for px, py in pts]
    cv2.fillPoly(m, [np.array(P, np.int32)], 1.0, cv2.LINE_AA)
    hc = (x + (0 * math.cos(th) + 100 * math.sin(th)) * s, y + (0 * math.sin(th) - 100 * math.cos(th)) * s)
    cv2.circle(m, (int(hc[0]), int(hc[1])), int(9 * s), 1.0, -1, cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), 1.2)
    if cut is not None and cut[0] > 0:
        a, deg = cut; th2 = math.radians(deg)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        side = (-(xx - x) * math.sin(th2) + (yy - (y - 0.55 * h)) * math.cos(th2)) < 0
        sl = 260 * a ** 1.3
        up = cv2.warpAffine(m * side, np.float32([[1, 0, -sl * math.cos(th2)], [0, 1, -sl * math.sin(th2) + 300 * a * a]]), (W, H))
        m = np.maximum(m * (~side), up)
        seam = np.exp(-((-(xx - x) * math.sin(th2) + (yy - (y - 0.55 * h)) * math.cos(th2)) / 3) ** 2) * (np.abs(xx - x) < h * 0.35)
        fr = fr + seam[..., None] * RED * 2.0 * math.exp(-a / 0.5)
    fr = fr * (1 - m[..., None]) + m[..., None] * 0.01
    e = np.clip(m - cv2.erode(m, np.ones((5, 5), np.uint8)), 0, 1)
    return fr + e[..., None] * (np.array([1.0, 0.3, 0.2], np.float32) if red else COLDV) * 0.6


# V13 30.77–32.60 MS 收刀：右半，冷光；跪地求饶的混账剪影在左前景；巨字「放」墨灰
class V13(Shot):
    """第六棒（critic_A_r3 P1-7 构图空）：跪地者放大到左前景（焦外、冷轮廓、磕头起伏），鬼屠在中景右收刀入鞘；
    背景换冷色纵深雨幕（去竹林竖条）；「放」在两人之间，随收刀那一线刀光自左向右写出（冷钢色）。"""
    def __init__(self):
        T.warm('放', 'kai', 360)
    def render(self, t):
        if R5.ON['sha_fang'] and not R6C_OFF('sf7'): return self.r6c(t)
        if R5.ON['sha_fang']: return self.r5(t)
        u = self.u(t)
        fr = night((0.012, 0.016, 0.03), (0.05, 0.06, 0.08))
        fr = A.glow(fr, (1300, 380), 520, 0.3, (0.55, 0.62, 0.85))
        fr = fog(fr, t, 0, 200, 900, 0.35, (0.18, 0.21, 0.28), speed=(-30, 0), light=(1300, 380))
        fr = RAIN.draw(fr, t, 0.9, angle=-4, light=(1300, 380), layers=(0, 1))
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        gm = np.clip((yy - 900) / 30, 0, 1); fr = fr * (1 - 0.6 * gm)
        fr = fog(fr, t, 2, 760, 960, 0.45, (0.22, 0.25, 0.32), speed=(-40, 0))
        # 第九棒（critic_A_r6 P0-1）：焦点转移 rack focus —— 起：前景跪者实、鬼屠与雨幕虚；31.00→31.32 焦点拉到鬼屠（跪者虚成冷剪影），「放」落在焦点到位之后
        fc = eio(clamp01((t - V(31.0)) / 0.32))
        fr = V3.defocus(fr, 7.0 * (1 - fc))
        # 第八棒（critic_A_r5 P0-1）：鬼屠收刀后站定 —— 身体由微侧回正（rot 3°→0）+ 中景缓移；跪者在前景反向大幅横移（视差）并越磕越深、发抖
        fr, info = A.place(fr, t, S('S014/sheath'), (1290 - 70 * eio(u), 930), h=600 * (1 + 0.03 * u), rim=COLD, rim_amt=3.2, wind=8,
                           grade=dict(expo=0.85, sat=0.5), rot=3.0 * (1 - eout(u)), defocus=6.0 * (1 - fc))
        L = T.Layer(); p = cprog(4, [6], t, 0.25)[0]
        if p > 0:
            L.paste(T.ink_bleed_glyph('放', 'kai', 330, p, seed=6, bleed=0.6), 880, 520, (0.70, 0.76, 0.88))
            fr = T.compose(fr, L, shadow=0.7, glow=0.25, glow_color=(0.5, 0.6, 0.9))
            a_ = t - (CT(4, 6) - 0.22)
            fr = streak(fr, 520, 640, 1140, a_ / 0.22, w=3, amt=0.9, ang=-3, col=(0.75, 0.85, 1.0))
        bow = -1.5 + 7.0 * eio(u) + 1.6 * math.sin(t * 6.0)                       # 越磕越深 + 磕头起伏
        trem = 2.5 * math.sin(t * 41) + 1.5 * math.sin(t * 67)                       # 发抖
        fr, _ = A.place(fr, t, A.bg_matte('A/kneel_beg'), (500 - 190 * eio(u) + trem, 1085 + 20 * eio(u)), h=780, anc=(0.55, 1.0), flip=True, rim=COLD, rim_amt=2.6,
                        rim_dir=(0.7, -0.6), grade=dict(expo=0.5 + 0.3 * (1 - fc), sat=0.4, gamma=1.3 - 0.2 * (1 - fc)), wind=3, rot=bow, defocus=0.3 + 5.5 * fc)
        fr = RAIN.draw(fr, t, 0.6, angle=-4, layers=(2,))
        return fr, 0

    def r6c(self, t):
        """r6 第三棒 #7：殺世界延续到 31.07，冷刀光前沿扫过「殺」并甩过全画面，前沿左侧换成放世界（只换对手、只换刀势），字同步流变。"""
        tm, k0 = _sf_k()
        km = clamp01((t - k0) / 0.60)
        xe = _sf_edge(t)
        if xe is None: fr = _sf_sha_world(t)
        elif xe > W + 400: fr = _sf_fang_world(t)
        else:
            m = _sf_mask(xe)[..., None]
            A_ = _sf_sha_world(t); B_ = _sf_fang_world(t)
            fr = A_ * (1 - m) + B_ * m
        fr = _sf_word(fr, t, km if t >= k0 else None)
        fr = _sf_edge_glow(fr, xe)
        fr = RAIN.draw(fr, t, 0.6, angle=4, layers=(2,))
        return fr, 0

    def r5(self, t):
        """第五轮 7：与 V12 同构图 —— 鬼屠同位同大（左，sheath_same 收刀，同一站姿）、右侧恶徒位置换成跪地混账（面朝鬼屠磕头）、
        左上同一位置的「殺」原地变换成「放」：31.18 起一线冷刀光自左向右扫过字，扫过处朱红殺的笔画按距离场流成冷钢色放；
        画面残留的 V12 血红随变换退成冷光。"""
        u = self.u(t); tm = CT(4, 6)
        km = clamp01((t - (tm - 0.40)) / 0.60); kc = eio(km)
        fr = night((0.012, 0.016, 0.03), (0.05, 0.06, 0.08))
        fr = A.glow(fr, (1400, 420), 520, 0.3, (0.55, 0.62, 0.85))                    # 与 V12 同一光位
        fr = fog(fr, t, 0, 200, 900, 0.35, (0.18, 0.21, 0.28), speed=(-30, 0), light=(1400, 420))
        fr = RAIN.draw(fr, t, 0.9, angle=4, light=(1400, 420), layers=(0, 1))
        red = (1 - kc) * 0.7                                                              # V12 的血红余光 → 冷
        fr = fr * (1 - red) + fr.mean(axis=2, keepdims=True) * np.array([2.3, 0.40, 0.34], np.float32) * red
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        fr = fr * (1 - 0.6 * np.clip((yy - 1000) / 30, 0, 1))
        fr = fog(fr, t, 2, 760, 960, 0.40, (0.22, 0.25, 0.32), speed=(-40, 0))
        rim = tuple(np.array(COLD) * kc + np.array(REDR) * (1 - kc))
        fr, info = A.place(fr, t, os.path.join(R5._R5A, 'sheath_same_v1_cut.png'), (720, 990), h=640, rim=rim, rim_amt=3.0, wind=7,
                           grade=dict(expo=0.85, sat=0.55))
        bow = 1.0 + 6.0 * eio(u) + 1.6 * math.sin(t * 6.0)
        trem = 2.5 * math.sin(t * 41) + 1.5 * math.sin(t * 67)
        fr, _ = A.place(fr, t, A.bg_matte('A/kneel_beg'), (1340 + trem, 1000), h=500, anc=(0.5, 1.0), rim=rim, rim_amt=2.4,
                        rim_dir=(-0.7, -0.6), grade=dict(expo=0.62, sat=0.3, gamma=1.2), wind=3, rot=-bow)
        al, w = R5.cal_morph(SF_SHA[0], SF_FANG[0], SF_SHA[1], km, spread=0.75)
        Lr = T.Layer(); Lc = T.Layer()
        Lr.paste(al * (1 - w), *SF_AT, SF_RED); Lc.paste(al * w, *SF_AT, SF_COLD)
        fr = T.compose(fr, Lr, shadow=0.6, glow=0.45, glow_color=(0.9, 0.1, 0.06))
        fr = T.compose(fr, Lc, shadow=0.7, glow=0.25, glow_color=(0.5, 0.6, 0.9))
        if 0 < km < 1:                                                                     # 变换前沿：冷白热线
            Le = T.Layer(); Le.paste(np.clip(4 * w * (1 - w) * al * 1.4, 0, 1), *SF_AT, (0.92, 0.96, 1.0))
            fr = T.compose(fr, Le, shadow=0.0, glow=0.6, glow_color=(0.7, 0.8, 1.0))
        q = (t - (tm - 0.37)) / 0.27                                                    # 刀光头与变换前沿同步
        fr = streak(fr, 400, 100, 560, q, w=3, amt=0.9, ang=-3, col=(0.75, 0.85, 1.0))
        fr = RAIN.draw(fr, t, 0.6, angle=4, layers=(2,))
        return fr, 0


# V14 32.60–34.44 CU 手握刀柄慢拔：刀身阴刻歌词随拔出依次亮起；34.10「刀」朱红 + 白刃闪
class V14(Shot):
    def render(self, t):
        if R5.ON['draw_cu']: return self.render6(t)
        return self.render5(t)

    def render6(self, t):
        """r6 #8（用户：0:33 角色图不好看）：换 draw_cu_v1 生图（定妆照一致：高马尾、中分乱刘海、琥珀眼、黑衣暗红内领）——
        右手握柄、左手按鞘，刀身斜出半鞘；慢推 + 右移（拔刀方向）。#53 后火星不再飞向右侧字位：每个字拍从鞘口刮出一簇火星，
        沿刀身向护手方向擦过、落在刀身上熄灭；「刀」拍一道寒光从鞘口扫到护手 + 白刃闪。"""
        u = self.u(t)
        if not hasattr(self, 'spr'):
            import a_r6
            self.spr = a_r6.hair_clean('R5_A/draw_cu_v1', protect=(0.0, 0.3, 1.0, 1.0))
        fr = night((0.012, 0.011, 0.014), (0.035, 0.032, 0.036))
        fr = A.glow(fr, (1560, 280), 520, 0.30, (1.0, 0.6, 0.3))
        fr = A.glow(fr, (420, 200), 600, 0.10, (0.55, 0.65, 0.9))
        fr = EMB.draw(fr, t, 0.35, wind=(80, -60))
        k = eio(u)
        fr, info = A.place(fr, t, self.spr, (975 - 30 * k, 540), w=1720, anc=(0.5, 0.5), rim=COLD, rim_amt=2.2,
                           rim_dir=(0.7, -0.7), wind=3, grade=dict(expo=0.92, sat=0.62, gamma=1.06), breathe=0.002)
        G = info['to_scr']((0.285, 0.548)); M = info['to_scr']((0.612, 0.775))            # 护手 / 鞘口（原图归一化坐标，人工标定）
        dx, dy = G[0] - M[0], G[1] - M[1]; Ln = math.hypot(dx, dy); ux, uy = dx / Ln, dy / Ln
        for i in range(8):                                                                  # 每个字拍一簇火星：鞘口 → 沿刀身 → 刀身上熄灭
            t0_ = CT(5, i) - 0.12
            if 0 <= t - t0_ < 0.5:
                fr = K.sparks(fr, t, 300 + i, (M[0] - 10 * ux, M[1] - 10 * uy), n=22, life=0.32, speed=(260, 620), dirc=(ux, uy), spread=0.22,
                              grav=60, area=(10, 10), amt=0.85, t0=t0_, burst=True, color=(1.0, 0.62, 0.24))
                fr = A.glow(fr, M, 46, 0.5 * math.exp(-(t - t0_) / 0.12), (1.0, 0.6, 0.25))
        # 拔刀的冷光沿刃口缓慢上移（鞘口 → 护手），每个字拍刷新一次
        ph = (t - (CT(5, 0) - 0.12)) / max(0.1, CT(5, 4) - CT(5, 0))
        if 0 < ph < 1.2:
            q = ph % 1.0 if ph < 1 else 1.0
            P = (M[0] + dx * q, M[1] + dy * q)
            fr = A.glow(fr, P, 70, 0.22 * (1 - max(0, ph - 1) * 5), (0.8, 0.88, 1.0), aspect=0.35)
        a = t - CT(5, 4)
        if a >= 0:
            fr = streak(fr, (M[1] + G[1]) / 2, M[0], G[0], a / 0.12, amt=1.1, ang=math.degrees(math.atan2(G[1] - M[1], G[0] - M[0])))
        g = math.exp(-max(0, a) / 0.15) * (a >= 0)
        for p in ((0.425, 0.365), (0.525, 0.36)):
            fr = pupil_glint(fr, info['to_scr'](p), 0.25 * g, 0.6, col=(1.0, 0.85, 0.6))
        return fr, (4 if 0 <= a < 0.1 else 0)

    def render5(self, t):
        u = self.u(t)
        fr = night((0.01, 0.01, 0.014), (0.03, 0.03, 0.035))
        fr = A.glow(fr, (1500, 300), 450, 0.25, (1.0, 0.6, 0.3))
        fr, info = A.place(fr, t, S('S015/hand_draw'), (960 - 50 * u, 560), w=2350 * (1 + 0.06 * u), anc=(0.5, 0.5), rim=COLD, rim_amt=2.0,
                           grade=dict(expo=0.88, sat=0.55), wind=4)
        P0 = info['to_scr']((0.335, 0.585)); P1 = info['to_scr']((0.585, 0.825))                    # 刀身（护手 → 刀尖方向）
        # 第六棒（critic_A_r3 P1-8：字平铺刃面撞副歌一 S046）：字不上刀 —— 刀出鞘时从鞘口「刮」出火星，火星聚成字，
        #   沿刀身上方一条平行线飞到位（小 → 大，带拖尾），落定后仍是火星质感（逐粒闪烁），朱金色
        txt = '每一次拔刀都是'
        dx, dy = P1[0] - P0[0], P1[1] - P0[1]; Ln = math.hypot(dx, dy); ux, uy = dx / Ln, dy / Ln; nx, ny = uy, -ux
        if ny > 0: nx, ny = -nx, -ny
        Ls = T.Layer()
        for i, c in enumerate(txt):
            a_ = t - (CT(5, i) - 0.12)
            if a_ <= 0: continue
            q = eout(clamp01(a_ / 0.28))
            tx, ty = 1690, 228 + i * 101                                     # 落位：右侧暗区竖排一列（不压脸）
            x = P0[0] + (tx - P0[0]) * q; y = P0[1] + (ty - P0[1]) * q
            if not NOVLYR:                                                   # r6 #53：竖排火星字去掉，鞘口刮出的火星照飞
                T.place(Ls, c, x, y, 92 * (0.35 + 0.65 * q), (1.0, 0.62, 0.22) if c != '刀' else (1.0, 0.25, 0.10), 'kai', alpha=min(1.0, a_ / 0.1))
            if q < 1:
                fr = K.sparks(fr, t, 300 + i, (x, y), n=26, life=0.3, speed=(80, 300), dirc=(-ux, -uy), spread=0.5, grav=300,
                              area=(20, 20), amt=0.8, t0=CT(5, i) - 0.12, burst=True, color=(1.0, 0.6, 0.2))
        if Ls.box() is not None:
            nz = cv2.resize(A.tex(int(t * 24) % 50 + 400, 256, 60, 2), (W, H))
            Ls.A *= np.clip((nz - 0.30) * 3.0, 0.25, 1.0)                                  # 火星颗粒：逐粒闪烁
            fr = T.compose(fr, Ls, shadow=0.6, shadow_sigma=10, glow=0.9, glow_color=(1.0, 0.45, 0.12), glow_sigma=14)
        a = t - CT(5, 4)
        if a >= 0:
            fr = streak(fr, (P0[1] + P1[1]) / 2, P0[0], P1[0], a / 0.12, amt=1.2, ang=math.degrees(math.atan2(P1[1] - P0[1], P1[0] - P0[0])))
        fr = EMB.draw(fr, t, 0.6, wind=(80, -60))
        return fr, (4 if 0 <= a < 0.1 else 0)


# V15 34.44–36.27 MS 刀刻石碑（第五棒重做，评审 P0：缺「我的」、碑线框露边、描边剪影人物）：
#     左 60% 雨中巨碑（粗糙不规则碑边、无线框、雨水流痕），右侧鬼屠侧身 MCU（carve_mcu 精灵）以刀尖刻字，刀尖随当前字移动；
#     右列「我的」(34.68 / 35.07) 先刻、左列「主张」(35.46 / 35.82) 大字后刻（竖排右起），每字迸石屑；左上体积光束穿雨照碑面
class V15(Shot):
    GL = [('我', 7, 400, 650, 150), ('的', 8, 555, 650, 150), ('主', 9, 750, 650, 230), ('张', 10, 970, 650, 230)]   # 第六棒：刀平伸刻一行，人边刻边收刀后撤（刀尖左→右）
    def __init__(self):
        T.warm('我的', 'kai', 170); T.warm('主张', 'kai', 270)
        self.tex = cv2.resize(A.tex(151, 512, 8, 6), (W, H)); self.tex2 = cv2.resize(A.tex(152, 512, 40, 3), (W, H))
        q = 2; edge = cv2.resize(A.tex(153, 256, 6, 4), (W // q, H // q)) * 60
        yy, xx = np.mgrid[0:H // q, 0:W // q].astype(np.float32)
        x0, x1, y0 = (110, 1100, 250) if R5.ON['carve'] else (290, 1230, 140)   # 碑：不规则粗糙边（不再是直线框）；r6 #9：碑左移让人与整把刀入画
        d = np.minimum.reduce([xx * q - x0 + edge, x1 - xx * q + edge * 0.6, yy * q - y0 - 40 * np.sin(xx * q / 300) + edge * 0.8])
        self.st = cv2.resize(np.clip(d / 4, 0, 1), (W, H))
        chip = np.clip((cv2.resize(A.tex(154, 256, 20, 3), (W, H)) - 0.66) * 6, 0, 1) * np.clip(1 - np.abs(cv2.resize(d, (W, H)) - 20) / 30, 0, 1)
        self.chip = chip
        import a_r6
        self.spr = a_r6.hair_clean('A_r6/carve_grip', protect=(0.0, 0.53, 0.60, 0.66))          # 第六棒：双手握柄、刀身平伸向左（原 carve_mcu 托刃）
        self.anc = a_r6.anc_for(self.spr, (0.0, 0.592))
        if R5.ON['carve']:                                                          # r6 #9：全刀入画（carve_full 生图：双手平伸、刀尖 → 原图左缘）+ 真凿刻字
            self.spr = a_r6.clean('R5_A/carve_full_v1', lo=0.2, erode=3)
            self.anc = a_r6.anc_for(self.spr, (0.0396, 0.430))
            self.CV = R5.Carve([(250, 670, 190), (448, 670, 190), (636, 670, 190), (836, 670, 190)])
    def tip(self, t):
        pts = [(355, 652), (510, 652), (675, 652), (895, 652)]                   # 刀尖：每字左缘起刀，我 → 的 → 主 → 张
        ts = [CT(5, k) for (_, k, _, _, _) in self.GL]
        if t <= ts[0]: return pts[0]
        if t >= ts[-1] + 0.06:                                                  # 第六棒：刻完「张」收刀后撤，刀身让开字
            q = eout(clamp01((t - ts[-1] - 0.06) / 0.18)); return (pts[-1][0] + 460 * q, pts[-1][1])
        for i in range(len(ts) - 1):
            if t < ts[i + 1]:
                q = eio(clamp01((t - ts[i]) / (ts[i + 1] - ts[i])))
                return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * q, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * q)
        return pts[-1]
    def tip6(self, t):
        """r6：刀尖 = 当前字的凿刻前沿（左 → 右），字间平移；刻完「张」刀尖下沉离碑。→ (x, y, 当前字 idx 或 None, 各字进度)"""
        ts = [CT(5, k) - 0.10 for (_, k, _, _, _) in self.GL]
        dur = 0.34
        pr = [clamp01((t - a) / dur) for a in ts]
        cv = self.CV
        fx = lambda i, p: cv.bounds(i)[0] + (cv.bounds(i)[1] - cv.bounds(i)[0] + 30) * p
        cur = None
        for i, p in enumerate(pr):
            if 0 < p < 1: cur = i
        if t <= ts[0]: x = fx(0, 0) - 20 * (1 - clamp01((t - self.t0) / (ts[0] - self.t0)))
        elif cur is not None: x = fx(cur, pr[cur])
        else:
            i = max(j for j in range(4) if t >= ts[j])
            if i == 3: x = fx(3, 1)
            else: x = fx(i, 1) + (fx(i + 1, 0) - fx(i, 1)) * eio(clamp01((t - ts[i] - dur) / (ts[i + 1] - ts[i] - dur)))
        y = 670 + (22 * abs(math.sin(pr[cur] * math.pi * 3)) if cur is not None else 0)
        if t > ts[3] + dur:                                                    # 刻完：刀尖下沉、离开碑面
            q = eout(clamp01((t - ts[3] - dur) / 0.25)); x += 6 * q; y += 55 * q
        return x, y, cur, pr

    def render(self, t):
        if R5.ON['carve'] and not R6C_OFF('stele'): return self.render7(t)
        if R5.ON['carve']: return self.render6(t)
        return self.render5(t)

    # ---- r6 第三棒 #9（评审 2ce318b 打回 7 分：碑像湿布、人平移漂移 600px、右肘贴边）----
    #   碑：生图青石碑面 stele_stone_v1（真石材颗粒 + 风化斑）贴进直边碑形（左/右/顶直边，两处顶角崩口、边沿 ≤3px 风化毛口），
    #       顶面受左上冷光一条倒角亮边、右侧背光厚度面、碑后投影；碑底出画（下沿被地雾吃掉）；去掉竖向流痕。
    #   人：刀尖仍是凿刻前沿，但改成「镜头跟刀」——碑（及字、碎屑、火星）整体在画里向左走，人锁在屏幕右侧（刀尖屏幕 x 850→930、人缩 7%、
    #       人体右沿 ≤1800，右留白 ≥120px），每凿一字上身随刀微转（±1.4°）；刻完刀尖下沉离碑。
    def _stele7(self):
        if hasattr(self, 'st7'): return
        from PIL import Image as _I
        x0, x1, y0 = 110, 1100, 250
        rs = np.random.RandomState(77)
        nzx = cv2.resize(rs.rand(1, 64).astype(np.float32), (W, 1), interpolation=cv2.INTER_CUBIC)[0]
        nzy = cv2.resize(rs.rand(64, 1).astype(np.float32), (1, H), interpolation=cv2.INTER_CUBIC)[:, 0]
        fine = cv2.resize(rs.rand(H // 3, W // 3).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        top = y0 + (nzx[None, :] - 0.5) * 3 + (fine - 0.5) * 1.5
        left = x0 + (nzy[:, None] - 0.5) * 3 + (fine - 0.5) * 1.5
        right = x1 + (nzy[::-1][:, None] - 0.5) * 3 + (fine - 0.5) * 1.5
        d = np.minimum.reduce([xx - left, right - xx, yy - top])
        # 顶角崩口：左上一块斜缺、右上一个小缺口
        d = np.minimum(d, (xx - x0) + (yy - y0) - 46 + (fine - 0.5) * 6)
        # 右上崩口：不规则楔形缺（宽 ≈80、深 ≈34，斜坡两侧粗糙），不是半圆
        cx_ = x1 - 230
        wedge = (yy - y0) - np.clip(34 - np.abs(xx - cx_ - 8 * np.sign(xx - cx_)) * 0.8, 0, 34) + (fine - 0.5) * 8
        d = np.where(np.abs(xx - cx_) < 50, np.minimum(d, wedge), d)
        self.st7 = np.clip(d / 1.2 + 0.5, 0, 1).astype(np.float32)
        im = np.asarray(_I.open(os.path.join(R5._R6A, 'stele_stone_v1.png')).convert('RGB'), np.float32) / 255
        bw, bh = x1 - x0 + 60, H - y0 + 40
        sc = max(bw / im.shape[1], bh / im.shape[0])
        im = cv2.resize(im, (int(im.shape[1] * sc) + 1, int(im.shape[0] * sc) + 1), interpolation=cv2.INTER_AREA)[:bh, :bw]
        alb = np.zeros((H, W, 3), np.float32); alb[y0 - 20:y0 - 20 + bh, x0 - 30:x0 - 30 + bw][:H - (y0 - 20)] = im[:H - (y0 - 20)]
        lum = alb.mean(2, keepdims=True)
        alb = alb / max(1e-3, float(lum[self.st7 > 0.5].mean())) * 0.12                          # 夜里碑面平均亮度 ≈0.12（与原碑同档）
        lit = np.clip(1.25 - (xx - x0) / 1250 - (yy - y0) / 1500, 0.30, 1.15)[..., None]
        self.stone7 = (alb * lit * np.array([0.92, 0.97, 1.08], np.float32)).astype(np.float32)
        s0 = self.st7
        self.side7 = np.clip(cv2.warpAffine(s0, np.float32([[1, 0, 24], [0, 1, 5]]), (W, H)) - s0, 0, 1)
        bv = np.zeros_like(s0)
        for k_, wk in ((3, 0.45), (7, 0.30), (12, 0.18), (18, 0.07)):                         # 顶面倒角：上沿最亮、向下 18px 渐暗（不是一根细线）
            bv += wk * np.clip(s0 - cv2.warpAffine(s0, np.float32([[1, 0, 0], [0, 1, k_]]), (W, H)), 0, 1)
        self.bevel7 = cv2.GaussianBlur(bv, (0, 0), 1.2) * (0.6 + 0.8 * fine)
        self.lbevel7 = np.clip(s0 - cv2.warpAffine(s0, np.float32([[1, 0, 6], [0, 1, 0]]), (W, H)), 0, 1) * (0.5 + 0.5 * fine)
        self.cast7 = np.clip(cv2.GaussianBlur(cv2.warpAffine(s0, np.float32([[1, 0, 70], [0, 1, 30]]), (W, H)), (0, 0), 30) - s0 - self.side7, 0, 1)
        self.alpha7 = np.clip(s0 + self.side7, 0, 1)

    def _tipx_smooth(self, t):
        xs = [self.tip6(t + d)[0] for d in (-0.15, -0.1, -0.05, 0, 0.05, 0.1, 0.15)]
        return float(np.mean(xs))

    def render7(self, t):
        self._stele7()
        u = self.u(t)
        bg = night((0.012, 0.014, 0.024), (0.04, 0.045, 0.06))
        bg = A.glow(bg, (200, 60), 800, 0.35, (0.55, 0.62, 0.82))
        bg = RAIN.draw(bg, t, 0.7, angle=8, light=(200, 60), layers=(0,))
        # 世界层（碑 + 刻字 + 碎屑/火星）：先在世界坐标画，再按镜头平移贴到屏幕
        wl = self.stone7.copy()
        side_c = np.array([0.040, 0.042, 0.050], np.float32) * (0.8 + 0.4 * self.stone7.mean(2, keepdims=True) / 0.12)
        wl = wl * (1 - self.side7[..., None]) + side_c * self.side7[..., None]
        wl = wl + (self.bevel7 * 0.22)[..., None] * np.array([0.50, 0.56, 0.70], np.float32) + (self.lbevel7 * 0.12)[..., None] * np.array([0.5, 0.56, 0.7], np.float32)
        tx, ty, cur, pr = self.tip6(t)
        wl = self.CV.draw(wl, pr, mask=self.st7)
        wl = wl * self.alpha7[..., None]
        add = np.zeros((H, W, 3), np.float32)
        for i, (c, k, gx, gy, sz) in enumerate(self.GL):
            a0 = CT(5, k) - 0.10
            if -0.05 <= t - a0 < 0.9:
                add = K.sparks(add, t, 150 + k, (self.CV.bounds(i)[0] + 60, 670), n=46, life=0.7, speed=(120, 420), dirc=(0.5, -0.6), spread=1.5, grav=1300,
                               area=(80, 70), amt=0.55, t0=a0, burst=True, color=(0.55, 0.55, 0.58))
        if cur is not None:
            add = K.sparks(add, t, 159, (tx, ty), n=18, life=0.22, speed=(150, 480), dirc=(0.4, -0.9), spread=1.4, grav=900, area=(6, 6),
                           amt=0.75, t0=self.t0, burst=False, color=(1.0, 0.82, 0.55))
            pq = np.zeros((H // 4, W // 4), np.float32)
            cv2.circle(pq, (int(tx / 4), int(ty / 4)), 9, 1.0, -1)
            pq = cv2.resize(cv2.GaussianBlur(pq, (0, 0), 6), (W, H)) * cv2.resize(A.tex(int(t * 30) % 40 + 500, 256, 12, 3), (W, H))
            add = add + pq[..., None] * np.array([0.10, 0.10, 0.10], np.float32)
        # 镜头跟刀：屏幕刀尖 790 → 900（缓），世界层平移 sx
        txs = self._tipx_smooth(t)
        scr = 850 + 80 * eio(u)
        sx = scr - txs
        M = np.float32([[1, 0, sx], [0, 1, 0]])
        wlS = cv2.warpAffine(wl, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        aS = cv2.warpAffine(self.alpha7, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)[..., None]
        cS = cv2.warpAffine(self.cast7, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)[..., None]
        addS = cv2.warpAffine(add, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        fr = bg * (1 - 0.55 * cS)
        fr = fr * (1 - aS) + wlS
        fr = fx2.god_rays(fr, (200, 40), strength=0.35, length=1.0, color=(0.65, 0.72, 0.9), t=t, src_r=180)
        fr = fr + addS
        # 人：刀尖 = 凿刻前沿的屏幕位置；每字上身随刀微转
        hx = tx + sx
        lean = sum(-1.4 * math.sin(math.pi * p) for p in pr if 0 < p < 1)
        jit = 2.5 * math.sin(t * 47) if cur is not None else 0
        fr, info = A.place(fr, t, self.spr, (hx + jit, ty), w=800, anc=self.anc, rim=COLD, rim_amt=2.6,
                           rim_dir=(-0.7, -0.6), wind=8, grade=dict(expo=0.88, sat=0.55, gamma=1.08), breathe=0.0, rot=lean)
        self._last_box = info['box']
        fr = A.glow(fr, (hx, ty), 40, 0.5 if cur is not None else 0.1, (0.9, 0.9, 1.0))
        fr = fog(fr, t, 0, 820, 1000, 0.40, (0.22, 0.25, 0.32), speed=(-50, 0))
        fr = RAIN.draw(fr, t, 0.8, angle=8, light=(200, 60), layers=(1, 2))
        return fr, 0

    def render6(self, t):
        u = self.u(t)
        fr = night((0.012, 0.014, 0.024), (0.04, 0.045, 0.06))
        fr = A.glow(fr, (200, 60), 800, 0.35, (0.55, 0.62, 0.82))
        fr = RAIN.draw(fr, t, 0.7, angle=8, light=(200, 60), layers=(0,))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        st = self.st[..., None]
        lit = np.clip(1.2 - (xx - 110) / 1300 - (yy - 250) / 1600, 0.25, 1.1)
        stone = ((0.6 + 0.45 * self.tex) * (0.85 + 0.25 * self.tex2) * lit)[..., None] * np.array([0.13, 0.135, 0.15], np.float32)
        wet = np.clip(np.sin(xx / 23 + self.tex * 6) * 0.5 + 0.5, 0, 1) ** 8
        stone = stone + (wet * 0.07)[..., None] * np.array([0.6, 0.7, 0.9], np.float32) - self.chip[..., None] * 0.05
        if 'stele3d' not in os.environ.get('A_R6_OFF', ''):                            # r6 #9 补：碑有厚度 —— 右侧面（背光暗面 26px，透视微斜）+ 顶沿受光高光 + 碑后投影
            if not hasattr(self, 'side'):
                s0 = self.st
                sh_ = cv2.warpAffine(s0, np.float32([[1, 0, 26], [0, 1, 6]]), (W, H))
                self.side = np.clip(sh_ - s0, 0, 1)
                self.rim = cv2.GaussianBlur(np.clip(s0 - cv2.warpAffine(s0, np.float32([[1, 0, 0], [0, 1, 9]]), (W, H)), 0, 1), (0, 0), 2.5) * (0.6 + 0.8 * self.tex)
                self.cast = np.clip(cv2.GaussianBlur(cv2.warpAffine(s0, np.float32([[1, 0, 70], [0, 1, 30]]), (W, H)), (0, 0), 30) - s0 - self.side, 0, 1)
            fr = fr * (1 - 0.55 * self.cast[..., None])
            side_c = ((0.5 + 0.3 * self.tex) * (0.8 + 0.3 * self.tex2))[..., None] * np.array([0.045, 0.047, 0.055], np.float32)
            fr = fr * (1 - self.side[..., None]) + side_c * self.side[..., None]
        fr = fr * (1 - st) + stone * st
        if 'stele3d' not in os.environ.get('A_R6_OFF', ''):
            fr = fr + (self.rim * lit * 0.22)[..., None] * np.array([0.45, 0.5, 0.62], np.float32)
        fr = fx2.god_rays(fr, (200, 40), strength=0.35, length=1.0, color=(0.65, 0.72, 0.9), t=t, src_r=180)
        tx, ty, cur, pr = self.tip6(t)
        fr = self.CV.draw(fr, pr, mask=self.st)
        # 凿刻：刀尖处碎石屑（灰、受重力下落弹开）+ 少量钢石火星 + 石粉烟
        for i, (c, k, gx, gy, sz) in enumerate(self.GL):
            a0 = CT(5, k) - 0.10
            if -0.05 <= t - a0 < 0.9:
                fr = K.sparks(fr, t, 150 + k, (self.CV.bounds(i)[0] + 60, 670), n=46, life=0.7, speed=(120, 420), dirc=(0.5, -0.6), spread=1.5, grav=1300,
                              area=(80, 70), amt=0.55, t0=a0, burst=True, color=(0.55, 0.55, 0.58))
        if cur is not None:
            fr = K.sparks(fr, t, 159, (tx, ty), n=18, life=0.22, speed=(150, 480), dirc=(0.4, -0.9), spread=1.4, grav=900, area=(6, 6),
                          amt=0.75, t0=self.t0, burst=False, color=(1.0, 0.82, 0.55))
            pq = np.zeros((H // 4, W // 4), np.float32)
            cv2.circle(pq, (int(tx / 4), int(ty / 4)), 9, 1.0, -1)
            pq = cv2.resize(cv2.GaussianBlur(pq, (0, 0), 6), (W, H)) * cv2.resize(A.tex(int(t * 30) % 40 + 500, 256, 12, 3), (W, H))
            fr = fr + pq[..., None] * np.array([0.10, 0.10, 0.10], np.float32)                       # 石粉烟
        jit = 2.5 * math.sin(t * 47) if cur is not None else 0
        fr, info = A.place(fr, t, self.spr, (tx + jit, ty), w=860, anc=self.anc, rim=COLD, rim_amt=2.6,
                           rim_dir=(-0.7, -0.6), wind=8, grade=dict(expo=0.88, sat=0.55, gamma=1.08), breathe=0.0)
        fr = A.glow(fr, (tx, ty), 40, 0.5 if cur is not None else 0.1, (0.9, 0.9, 1.0))
        fr = fog(fr, t, 0, 820, 1000, 0.35, (0.22, 0.25, 0.32), speed=(-50, 0))
        fr = RAIN.draw(fr, t, 0.8, angle=8, light=(200, 60), layers=(1, 2))
        return fr, 0

    def render5(self, t):
        u = self.u(t)
        fr = night((0.012, 0.014, 0.024), (0.04, 0.045, 0.06))
        fr = A.glow(fr, (200, 60), 800, 0.35, (0.55, 0.62, 0.82))
        fr = RAIN.draw(fr, t, 0.7, angle=8, light=(200, 60), layers=(0,))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        st = self.st[..., None]
        lit = np.clip(1.2 - (xx - 290) / 1300 - (yy - 140) / 1600, 0.25, 1.1)
        stone = ((0.6 + 0.45 * self.tex) * (0.85 + 0.25 * self.tex2) * lit)[..., None] * np.array([0.13, 0.135, 0.15], np.float32)
        wet = np.clip(np.sin(xx / 23 + self.tex * 6) * 0.5 + 0.5, 0, 1) ** 8
        stone = stone + (wet * 0.07)[..., None] * np.array([0.6, 0.7, 0.9], np.float32) - self.chip[..., None] * 0.05
        fr = fr * (1 - st) + stone * st
        fr = fx2.god_rays(fr, (200, 40), strength=0.35, length=1.0, color=(0.65, 0.72, 0.9), t=t, src_r=180)   # 体积光束穿雨
        G = np.zeros((H, W), np.float32); cur = None
        for (c, k, gx, gy, sz) in self.GL:
            p = clamp01((t - (CT(5, k) - 0.10)) / 0.40)
            if p <= 0: continue
            if p < 1: cur = (gx, gy)
            g = T.ink_bleed_glyph(c, 'kai', sz, p, seed=20 + k, bleed=0.3)
            h_, w_ = g.shape; ys, xs = int(gy - h_ / 2), int(gx - w_ / 2)
            G[ys:ys + h_, xs:xs + w_] = np.maximum(G[ys:ys + h_, xs:xs + w_], g)
        if G.max() > 0:
            Gs = cv2.GaussianBlur(G, (0, 0), 1.2) * self.st
            sh = np.clip(Gs - cv2.warpAffine(Gs, np.float32([[1, 0, 5], [0, 1, 6]]), (W, H)), 0, 1)
            hl = np.clip(Gs - cv2.warpAffine(Gs, np.float32([[1, 0, -4], [0, 1, -5]]), (W, H)), 0, 1)
            fr = fr * (1 - 0.85 * Gs[..., None]) + Gs[..., None] * np.array([0.012, 0.012, 0.016], np.float32)
            fr = fr * (1 - 0.6 * sh[..., None]) + hl[..., None] * np.array([0.6, 0.68, 0.9], np.float32) * 1.0
            for (c, k, gx, gy, sz) in self.GL:
                a = t - CT(5, k)
                if -0.1 <= a < 0.6:
                    fr = K.sparks(fr, t, 150 + k, (gx + sz * 0.2, gy), n=40, life=0.5, speed=(150, 500), dirc=(0.8, -0.4), spread=1.4, grav=900,
                                  area=(sz * 0.4, sz * 0.4), amt=0.6, t0=CT(5, k) - 0.1, burst=True, color=(0.85, 0.85, 0.92))
        # 人：右侧侧身 MCU，刀尖抵住当前在刻的字（随字移动）
        tx, ty = self.tip(t)
        jit = 3 * math.sin(t * 40) if cur is not None else 0
        fr, info = A.place(fr, t, self.spr, (tx + jit, ty), w=1300, anc=self.anc, rim=COLD, rim_amt=3.0,           # 刀尖 = 原图左缘 (0, 0.592)
                           rim_dir=(-0.7, -0.6), wind=8, grade=dict(expo=0.85, sat=0.5, gamma=1.1), breathe=0.0)
        fr = K.sparks(fr, t, 159, (tx, ty), n=14, life=0.25, speed=(120, 420), dirc=(0.6, -0.8), spread=1.6, grav=900, area=(6, 6),
                      amt=0.7 if cur is not None else 0.0, t0=self.t0, burst=False, color=(1.0, 0.85, 0.6))                    # 刀尖抵碑：持续火星
        fr = A.glow(fr, (tx, ty), 50, 0.6 if cur is not None else 0.15, (0.8, 0.88, 1.0))
        fr = fog(fr, t, 0, 800, 1000, 0.4, (0.22, 0.25, 0.32), speed=(-50, 0))
        fr = RAIN.draw(fr, t, 0.8, angle=8, light=(200, 60), layers=(1, 2))
        return fr, 0


# V16 36.27–38.10 LS 仰拍太上皇举手召印：头顶云涡旋开，金光中一方巨印的阴影成形
class V16(Shot):
    def render(self, t):
        u = self.u(t)
        fr = night((0.02, 0.016, 0.012), (0.08, 0.07, 0.06), y1=900)
        c = (720, 230)
        yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
        ang = np.arctan2(yy * 4 - c[1], xx * 4 - c[0]); r = np.hypot(xx * 4 - c[0], yy * 4 - c[1])
        sw = np.sin(ang * 3 + r / 60 - t * 2.5) * 0.5 + 0.5
        vort = cv2.resize((sw * np.exp(-r / 600)).astype(np.float32), (W, H))
        fr = fr + vort[..., None] * np.array([0.25, 0.2, 0.12], np.float32) * (0.5 + u)
        fr = fx2.god_rays(fr, c, strength=0.6 + 0.8 * u, length=1.2, color=(1.0, 0.8, 0.5), t=t, src_r=140)
        # 第六棒：金光里成形的是同一方巨印（giant_seal 生图）的逆光剪影 + 金边，37.0 起自云涡中压出、下沉，云絮从前面掠过；接 V17 坠落
        k = eio(clamp01((t - V(36.9)) / 1.0))
        if k > 0:
            import a_r6
            if R5.ON['jade']:                                                    # r6 #10：玉玺重生成（jade_seal_v2：羊脂白玉、九龙钮、云纹浮雕、金镶缺角）——
                if not hasattr(self, 'seal'): self.seal = a_r6.clean('R5_A/jade_seal_v2', lo=0.2, erode=3)   # 不再是平涂剪影：受金光照亮，有体积与材质
                fr = A.glow(fr, (c[0] + 20, 300 + 90 * k), 300, 0.45 * k, (1.0, 0.82, 0.55))                 # 玉透光的暖晕
                fr, si = A.place(fr, t, self.seal, (c[0] + 20, 500 + 90 * k), w=400 + 70 * k, anc=(0.5, 1.0), rim=GOLD,
                                rim_amt=3.0 * k, rim_dir=(0.2, -1.0), alpha=min(1.0, 1.3 * k), wind=0, breathe=0.0, defocus=2.0 * (1 - k),
                                grade=dict(expo=0.30 + 0.38 * k, sat=0.75, gamma=1.08, tint=(1.04, 1.0, 0.92)))
                fr = R5.under_shade(fr, si['A'], si['box'], amt=0.55, start=0.35)
            else:
                if not hasattr(self, 'seal'): self.seal = a_r6.clean('A_r6/giant_seal', lo=0.2, erode=3)
                fr, _ = A.place(fr, t, self.seal, (c[0] + 20, 470 + 90 * k), w=520 + 80 * k, anc=(0.5, 1.0), look='sil', rim=GOLD,
                                rim_amt=5.0 * k, rim_dir=(0.2, -1.0), alpha=0.92 * k, wind=0, breathe=0.0,
                                grade=dict(expo=0.2, sat=0.3))
            fr = A.clouds(fr, t, 61, speed=(60, -20), y0=120, y1=520, amt=0.55, col=(0.16, 0.12, 0.08), dark=0.3, thr=0.52,
                          light=c, light_r=500, light_col=(1.0, 0.75, 0.4))
        # 第十一棒（critic_A_r7 P1-6 人物身份）：召印的是白发太上皇（权势一方），构图上点明 —— 站上丹陛高台（三级玉阶，阶沿金边），
        #   低机位仰看、身形压暗成背光剪影（金轮廓），与 V07「丹陛顶端太上皇剪影」同一母题；鬼屠全段黑发、冷光、站在地面
        st = np.zeros((H, W), np.float32); ed = np.zeros((H, W), np.float32)
        for i_, (y0_, hw) in enumerate(((835, 330), (900, 420), (965, 520))):
            cv2.rectangle(st, (1270 - hw, y0_), (1270 + hw, y0_ + 65), 1.0, -1)
            cv2.line(ed, (1270 - hw, y0_), (1270 + hw, y0_), 1.0, 3, cv2.LINE_AA)
        st = cv2.GaussianBlur(st, (0, 0), 1.2)[..., None]
        yy_ = np.arange(H, dtype=np.float32)[:, None, None]
        stone = (0.035 + 0.03 * np.clip((yy_ - 835) / 200, 0, 1)) * np.array([1.0, 0.92, 0.82], np.float32)
        fr = fr * (1 - st) + stone * st
        fr = fr + (cv2.GaussianBlur(ed, (0, 0), 1.0) * 0.9 + cv2.GaussianBlur(ed, (0, 0), 8) * 0.35)[..., None] * np.array([1.0, 0.72, 0.36], np.float32) * 0.55
        fr, info = A.place(fr, t, S('A/tsh_raise', 'dm'), (1270, 845), h=740, look=None, rim=GOLD, rim_amt=6.0, rim_dir=(-0.6, -0.8),
                           grade=dict(expo=0.36, sat=0.35, tint=(1.05, 0.97, 0.9)), wind=7)
        if R5.ON['jade'] and not R6C_OFF('jade') and k > 0:                             # r6 第三棒 #10：太上皇受左侧玉玺金光 —— 朝印一侧金色轮廓 + 身上暖色漫射（原灰冷剪影与金光不统一）
            Ae = info['A']; sxy = (c[0] + 20, 300 + 90 * k)
            edge = np.clip(Ae - cv2.warpAffine(Ae, np.float32([[1, 0, 10], [0, 1, 6]]), (W, H)), 0, 1)
            edge = cv2.GaussianBlur(edge, (0, 0), 1.5) + cv2.GaussianBlur(edge, (0, 0), 7) * 0.6
            yy4, xx4 = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32) * 4
            fall = cv2.resize(np.exp(-np.hypot(xx4 - sxy[0], yy4 - sxy[1]) / 650).astype(np.float32), (W, H))
            fr = fr + ((edge * 1.1 + Ae * 0.10) * fall * k)[..., None] * np.array([1.0, 0.72, 0.38], np.float32)
        fr = fog(fr, t, 1, 820, 1000, 0.5, (0.25, 0.22, 0.2), speed=(40, 0))
        return fr, 0


# V17 38.07–39.47（第六棒重做，critic_A_r3 不可交付：红方印「正」撞副歌一 S032 + 平涂贴纸 + glitch 碎屑 + 竖黄线）
#   前段（→ 38.72）：地平线低机位侧看 —— 巨印（giant_seal 生图：青灰玉石、麒麟钮、侧面云纹与裂口、印底残朱）自云层压下，
#       越落越快（竖向运动模糊），印面朝下看不见字；广场石板上玺影由虚变实；雨被巨印推开。
#   38.72「势」落地：压黑一拍 + 震 + 两侧尘浪贴地翻滚。
#   后段：俯拍地面 —— 石板被压出方形印坑，坑底是凹进去的「正」字（石材，不着红，靠左上侧光的内壁投影/高光读字），
#       裂缝里透暖金余热（不是朱红）；尘浪向外推散。红方印母题本段只剩 V08 纸面印痕一处。
class V17(Shot):
    def __init__(self):
        import a_r6
        self.R = a_r6
        self.seal = a_r6.clean('R5_A/jade_seal_v2', lo=0.2, erode=3) if R5.ON['jade'] else a_r6.clean('A_r6/giant_seal', lo=0.2, erode=3)
        r = np.random.default_rng(17)
        self.cracks = [K.crack_path((960 + math.cos(a) * 300, 540 + math.sin(a) * 260), (960 + math.cos(a) * 1400, 540 + math.sin(a) * 800), 17 + i)
                       for i, a in enumerate(r.uniform(0, 2 * math.pi, 9))] if hasattr(K, 'crack_path') else []
        g = 0.75 + 0.5 * cv2.resize(A.tex(5, 512, 8, 5), (W, H)) + 0.25 * cv2.resize(A.tex(6, 512, 40, 3), (W, H))
        sl = np.zeros((H, W), np.float32); rr = np.random.default_rng(5); y = 60
        while y < H:
            cv2.line(sl, (0, y), (W, y + int(rr.uniform(-8, 8))), 1.0, 2, cv2.LINE_AA); x = int(rr.uniform(0, 200))
            while x < W:
                cv2.line(sl, (x, y), (x + int(rr.uniform(-6, 6)), y + 150), 1.0, 2, cv2.LINE_AA); x += int(rr.uniform(220, 380))
            y += int(rr.uniform(130, 170))
        self.ground = (g * (1 - 0.6 * cv2.GaussianBlur(sl, (0, 0), 1.2)))[..., None]
        sq = np.zeros((H, W), np.float32); cv2.rectangle(sq, (960 - 290, 540 - 250), (960 + 290, 540 + 250), 1.0, -1)
        self.sq = sq
        Lg = T.Layer(); T.place(Lg, '正', 960, 540, 400, 'white', 'kai', texture=False); self.zm = Lg.A
        self.ytop = 0
    def side(self, t, th):
        q = clamp01((t - self.t0) / (th - self.t0))
        fr = night((0.03, 0.022, 0.018), (0.10, 0.075, 0.055), y1=720)
        fr = A.clouds(fr, t, 71, speed=(0, -40), y0=120, y1=700, amt=0.9, col=(0.13, 0.10, 0.08), thr=0.42, light=(960, 200),
                      light_r=800, light_col=(1.0, 0.72, 0.40))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        gm = np.clip((yy - 720) / 3, 0, 1)[..., None]                                   # 广场地面（透视石板缝向灭点 960,720 收拢）
        z = 1.0 / np.maximum(yy - 700, 1)
        tile = 1 - 0.4 * ((np.mod((xx - 960) * z * 60, 1.0) < 0.05 * 60 * z) | (np.mod(80 * np.log(np.maximum(yy - 700, 1)), 6) < 0.4))
        gcol = (self.ground * tile[..., None]) * np.array([0.045, 0.04, 0.036], np.float32) * (0.5 + np.clip((yy - 720) / 240, 0, 1))[..., None]
        fr = fr * (1 - gm) + gcol * gm
        fr = fr + gm * (np.exp(-((xx - 960) / 500) ** 2) * np.exp(-np.clip(yy - 720, 0, None) / 80))[..., None] * np.array([0.30, 0.20, 0.10], np.float32) * 0.5   # 远处天光在湿地面上的反光
        fr = fog(fr, t, 1, 640, 780, 0.5, (0.22, 0.17, 0.12), speed=(30, 0))
        by = 360 + 520 * ein(q, 1.8)                                                       # 印底 y（落地 = 880）；第十一棒（P1-7）：起帧 140→360，开镜就露出大半个印身
        sh = np.zeros((H // 2, W // 2), np.float32)
        cv2.ellipse(sh, (480, 440), (int(330 + 140 * (1 - q)), int(26 + 10 * (1 - q))), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        sh = cv2.resize(cv2.GaussianBlur(sh, (0, 0), 4 + 22 * (1 - q)), (W, H))[..., None] * gm
        fr = fr * (1 - (0.25 + 0.6 * q) * sh)
        fr = RAIN.draw(fr, t, 0.7, angle=6, light=(960, 200), layers=(0, 1))
        if R5.ON['jade']:                                                                   # r6 #10：立体玉玺（3/4 侧俯，两个侧面 + 九龙钮都看得见）
            fr, info = A.place(fr, t, self.seal, (960, by), w=880 * (0.92 + 0.08 * q), anc=(0.5, 1.0), rim=GOLD, rim_amt=2.6, rim_dir=(0.3, -1.0),
                               grade=dict(expo=0.62, sat=0.70, tint=(1.05, 1.0, 0.92), gamma=1.10), wind=0, breathe=0.0,
                               mblur=(0, (3 + 20 * q * q) if R6C_OFF('jade') else (1.5 + 10 * q * q)))   # r6 第三棒 #10：竖向动态模糊减半（龙钮可读）
            fr = R5.under_shade(fr, info['A'], info['box'], amt=0.5, start=0.4)
            self._sa = info['A']
        else:
            fr, info = A.place(fr, t, self.seal, (960, by), w=1150 * (0.92 + 0.08 * q), anc=(0.5, 1.0), rim=GOLD, rim_amt=2.2, rim_dir=(0.3, -1.0),
                               grade=dict(expo=0.82, sat=0.55, tint=(1.04, 1.0, 0.95), gamma=1.05), wind=0, breathe=0.0,
                               mblur=(0, 4 + 22 * q * q))
        fr = fx2.god_rays(fr, (960, 130), strength=0.15, length=1.0, color=(1.0, 0.78, 0.45), t=t, src_r=200)
        # 第十一棒（P1-7）：下落速度线 —— 印身两侧被压开的气流/雨线，竖向拉长、随下落加速
        Lv = np.zeros((H // 2, W // 2), np.float32); rr_ = np.random.default_rng(171)
        for k_ in range(26):
            x_ = rr_.uniform(330, 1590); 
            if 560 < x_ < 1360 and rr_.random() < 0.7: x_ = x_ + (-420 if x_ < 960 else 420)
            y0_ = (rr_.uniform(0, 1.0) + (t - self.t0) * (2.0 + 3 * q)) % 1.3 * 900 - 100
            cv2.line(Lv, (int(x_ / 2), int(y0_ / 2)), (int(x_ / 2), int((y0_ + 140 + 160 * q) / 2)), rr_.uniform(0.4, 1.0), 1, cv2.LINE_AA)
        Lv = cv2.resize(cv2.GaussianBlur(Lv, (0, 0), 0.8), (W, H))[..., None] * (1 - gm)
        fr = fr + Lv * np.array([1.0, 0.85, 0.6], np.float32) * (0.25 + 0.35 * q)
        fr = RAIN.draw(fr, t, 0.6, angle=6, layers=(2,))
        return fr
    def top(self, t, a):
        # 第七棒（critic_A_r4 P0-1）：俯拍雨夜不规则石板地 + 真凹坑（崩口坑沿、内壁厚度、碎石、裂缝透暖光）；
        # 「正」只在坑底凹刻、靠左上侧光的阴影读出（不着金红、无框）；去砖墙、去橙色闪电、去白色碎屑
        import a_r7
        if not hasattr(self, 'cr'):
            self.cr = R9.Crater9(c=(960, 585), size=(560, 470), rot=-4.0, seed=17, zsize9=360)   # 第九棒：崩角 + 可读阴刻「正」+ 崩落石块   # 第八棒：受光崩口 + 坑壁厚度 + 投影 + 暖光裂缝
            self.fs, self.wet = a_r7.flagstones(7, n=55)
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            self.lit = (0.55 + 0.75 * np.exp(-(((xx - 520) / 1300) ** 2 + ((yy + 100) / 900) ** 2)))[..., None]
        fr = self.fs * self.lit * 2.0
        fr = a_r7.wet_sheen(fr, self.wet, light=(500, -250), amt=0.30, t=t)
        fr = self.cr.draw(fr, a, light=(-0.75, -0.65), heat=1.0, t=t)
        # 尘浪：贴地低矮暖褐，向外推开后散（不是白圈）
        yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
        d = np.hypot(xx * 2 - 960, (yy * 2 - 585) * 1.15)
        R = 430 + 1100 * eout(min(1, a / 1.0))
        ring = np.exp(-((d - R) / (70 + 220 * a)) ** 2) * math.exp(-a / 0.7) + np.clip((R - d) / R, 0, 1) * 0.25 * math.exp(-a / 0.5)
        rg = cv2.resize(ring, (W, H)) * np.clip(cv2.resize(A.ink_noise(19, 256), (W, H)) * 1.6 - 0.3, 0, 1)
        fr = fr * (1 - 0.3 * rg[..., None]) + rg[..., None] * np.array([0.10, 0.085, 0.07], np.float32)
        fr = fx2.ripples(fr, t, [(420, 820), (1500, 260), (1380, 880), (300, 300), (1650, 640)],
                         [self.t0 + 0.75, self.t0 + 0.9, self.t0 + 1.05, self.t0 + 1.15, self.t0 + 0.8], speed=120, amt=0.35, life=0.8)
        fr = RAIN.draw(fr, t, 0.45, angle=6, light=(500, -250), layers=(1, 2))
        return fr
    def render(self, t):
        th = V(38.72); a = t - th
        if a < 0: return self.side(t, th), 0
        if a < 0.12:                                                                           # 落地：侧面画面压黑一拍（第七棒：去白色碎屑、去色散撕裂）
            if R5.ON['jade'] and not R6C_OFF('jade'):                                       # r6 第三棒 #10：只压黑环境，玉玺本身保持白玉高光与暖透光（原整帧压到 30% → 灰糊一团）
                fr = self.side(t, th); m = np.clip(cv2.GaussianBlur(self._sa, (0, 0), 3) * 1.2, 0, 1)[..., None]
                k_ = 0.22 + 2.5 * max(0, a - 0.05)
                return fr * (m * 1.06 + (1 - m) * k_), 0
            fr = self.side(t, th) * (0.30 + 2.5 * max(0, a - 0.05))
            return fr, 0
        fr = self.top(t, a)
        if a < 0.15: fr = fr * (1 + 0.5 * (1 - a / 0.15))
        return fr, 0


# V18 39.47–40.84 HA 高机位大远景（第四棒：原 MCU 回头 → 俯拍）：印坑边缘的石板地上鬼屠一人极小、长影拖向画外，尘浪掠过，
#     斜雨冷线；降饱和（破晓留给后段）
class V18(Shot):
    def __init__(self):
        g = 0.75 + 0.5 * cv2.resize(A.tex(5, 512, 8, 5), (W, H)) + 0.25 * cv2.resize(A.tex(6, 512, 40, 3), (W, H))
        sl = np.zeros((H, W), np.float32); r = np.random.default_rng(8)
        for y in range(-200, H + 200, 150):
            cv2.line(sl, (0, y), (W, y + 260), 1.0, 2, cv2.LINE_AA)
        for x in range(-400, W + 400, 260):
            cv2.line(sl, (x, 0), (x - 200, H), 1.0, 2, cv2.LINE_AA)
        self.ground = (g * (1 - 0.55 * cv2.GaussianBlur(sl, (0, 0), 1.2)))[..., None]
        pit = np.zeros((H, W), np.float32)
        cv2.fillConvexPoly(pit, np.array([(-300, -200), (820, -60), (640, 420), (-420, 260)], np.int32), 1.0)
        self.pit = cv2.GaussianBlur(pit, (0, 0), 10)
        # 第六棒（critic_A_r3 P1-10）：印坑 → 人物站位的引导线：三道暖金裂缝自坑沿（左上）一路裂到鬼屠脚下
        self.cr = [K.crack_path(a_, b_, 180 + i) for i, (a_, b_) in enumerate((((700, 330), (1160, 880)), ((560, 380), (1000, 960)),
                                                                                ((780, 200), (1400, 760))))] if hasattr(K, 'crack_path') else []
    def render(self, t):
        # 第七棒（critic_A_r4 P1-6）：地面 = V17 同一套雨夜不规则石板，左上是同一个印坑的一角（崩口坑沿 + 内壁 + 碎石 + 裂缝透暖光），
        # 裂缝作引导线指向人物；去掉棕色折线与砖格
        import a_r7
        u = self.u(t)
        if not hasattr(self, 'cr7'):
            # 第八棒（critic_A_r5 P1-6/P0-2）：左侧横贯的浅灰坑壁带读不出是什么 → 坑整体移出画外（左上），画内只留坑里放射出来的暖光裂缝作引导线 + 坑方向的压暗
            self.cr7 = R8.Crater8(c=(-560, -470), size=(1250, 1000), rot=-8.0, seed=18, zheng=False)
            yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32)
            self.pitdark = (1 - 0.55 * np.exp(-(((xx_ + 100) / 900) ** 2 + ((yy_ + 120) / 650) ** 2)))[..., None]
            self.fs7, self.wet7 = a_r7.flagstones(9, n=40)
        fr = self.fs7 * 1.6
        fr = a_r7.wet_sheen(fr, self.wet7, light=(1500, 100), amt=0.35, t=t)
        fr = self.cr7.draw(fr, 0.8 + (t - self.t0), light=(0.6, -0.8), heat=1.3, t=t) * self.pitdark
        if not hasattr(self, 'lead'):                                                              # 自画外印坑裂到人物脚下的三道暖光裂缝（引导线）
            self.lead = [K.crack_path(a_, b_, 280 + i, jag=0.03) for i, (a_, b_) in enumerate((((-40, 260), (1150, 870)), ((150, -20), (1120, 850)),
                                                                                                 ((-60, 620), (1100, 890))))]
        pr = clamp01(0.55 + (t - self.t0) / 0.8)
        for i, cp in enumerate(self.lead):
            cm = K.draw_crack((H, W), cp, 3.0, branches=2, seed=8 + i, prog=pr)
            core = cv2.GaussianBlur(cm, (0, 0), 0.8)
            fr = fr * (1 - 0.85 * cm[..., None]) + (core * 0.8 + cv2.GaussianBlur(core, (0, 0), 5) * 0.45)[..., None] * np.array([1.0, 0.45, 0.15], np.float32) * (0.50 + 0.10 * math.sin(t * 8 + i))
        fr = A.glow(fr, (1500, 200), 600, 0.25, (0.9, 0.7, 0.5))
        at = (1180 + 40 * u, 880)
        sh = np.zeros((H // 2, W // 2), np.float32)                                              # 长影
        cv2.line(sh, (int(at[0] / 2), int(at[1] / 2)), (int((at[0] + 520) / 2), int((at[1] + 300) / 2)), 1.0, 22, cv2.LINE_AA)
        sh = cv2.resize(cv2.GaussianBlur(sh, (0, 0), 6), (W, H))[..., None]
        fr = fr * (1 - 0.6 * sh)
        cs = np.zeros((H // 2, W // 2), np.float32)                                              # 第五棒：脚下接触阴影 + 积水
        cv2.ellipse(cs, (int(at[0] / 2), int(at[1] / 2)), (70, 16), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        cs = cv2.resize(cv2.GaussianBlur(cs, (0, 0), 5), (W, H))[..., None]
        fr = fr * (1 - 0.75 * cs)
        fr = fx2.ripples(fr, t, [(at[0] - 30, at[1] + 4), (at[0] + 50, at[1] + 2)], [self.t0 + 0.1, self.t0 + 0.6], speed=160, amt=0.5, life=1.0)
        fr, info = A.place(fr, t, S('A/stand_ha'), at, h=560, rim=COLD, rim_amt=2.6, rim_dir=(-0.8, -0.5), wind=13,
                           grade=dict(expo=0.80, sat=0.38, tint=(0.97, 0.98, 1.02)), breathe=0.0)
        fog_ = 1  # 第六棒：雾只走人物以下，不盖印坑
        fr = fog(fr, t, 1, 600, 1000, 0.4, (0.30, 0.28, 0.26), speed=(380, 60), light=(1500, 200))
        fr = RAIN.draw(fr, t, 0.7, angle=20, light=(300, 150), layers=(0, 1, 2))
        fr = ASH.draw(fr, t, 0.8, wind=(420, 40))
        return fr, 0


# V19 40.84–41.77 MCU 仰望巨印（第五棒：换 look_up_mcu 统一主角脸 + defringe 去发丝灰边，人物右移让出左上歌词）
class V19(Shot):
    def __init__(self):
        import a_r7; self.R7 = a_r7
        self.spr = S('A/look_up_mcu2')                                     # 自抠：色距 + 连通背景，发丝间灰底清掉
    def render(self, t):
        u = self.u(t)
        # 第九棒（critic_A_r6 P1-5 不重复）：与 V14 拉开 —— 脸换朝左（镜像）、改金色逆光剪影（巨印的光从右上背后压来），
        #   脸只剩一线金轮廓 + 眼中一点寒光；冷灰正面光的「同光特写」去掉；机位 crane up 仰起
        # 第十一棒（critic_A_r7 P1-4）：整镜镜像 —— 人在左、巨印金光自左上背后压来，歌词整句移到右上；与 V14（脸中/字右）、V11（竖刀正脸）方向彻底拉开
        fr = night((0.015, 0.013, 0.012), (0.05, 0.045, 0.04))
        fr = A.glow(fr, (360, 160), 760, 0.95, (1.0, 0.70, 0.36))
        fr = A.glow(fr, (360, 160), 260, 0.45 + 0.1 * math.sin(t * 9), (1.0, 0.85, 0.6))
        fr = fx2.god_rays(fr, (360, 140), strength=0.35, length=1.0, color=(1.0, 0.75, 0.42), t=t, src_r=220)
        fr = RAIN.draw(fr, t, 0.8, angle=4, light=(360, 160), layers=(0, 1))
        hh = 1010 * (1 + 0.05 * eio(u))
        fr, info = A.place(fr, t, self.spr, (450 + 40 * eio(u), 1125 + 20 * u), h=hh, anc=(0.5, 1.0), rim=GOLD, rim_amt=9.0, flip=False,
                           rim_dir=(0.75, -0.65), wind=10, grade=dict(expo=0.20, sat=0.25, gamma=1.35, tint=(1.04, 0.98, 0.92)),
                           mblur=(0, 10 * eio(u)))
        g = math.exp(-max(0, t - V(41.40)) / 0.12) * (t >= V(41.40))
        for p in ((0.514, 0.26), (0.441, 0.26)):
            fr = pupil_glint(fr, info['to_scr'](p), 0.45 * g, 0.7)
        fr = RAIN.draw(fr, t, 0.9, angle=4, light=(360, 160), layers=(1, 2))
        return fr, (3 if g > 0.5 else 0)


# V20 41.77–42.68 LS 极低机位：鬼屠自下而上斜撩一刀，刀光弧线劈向天上的巨印
class V20(Shot):
    def __init__(self):
        import a_r6
        self.coil = a_r6.clean('A/slash_coil', lo=0.3, erode=4)                     # 第九棒：抠图灰边收 4px
        if R5.ON['rise']:                                                          # r6 #11：三张同一人物生图（定妆照一致），脚底中点钉在同一点
            self.K = [(a_r6.clean(k, lo=0.2, erode=3), f, h) for (k, f, h) in (
                ('R5_A/slash_rise_coil_v2', (0.60, 0.967), 500),                   # 蓄势：低伏、双手握柄、刀尖垂向左下
                ('R6_A/rise_mid', (0.474, 0.973), 600),                            # 撩刀中段：刀平扫向右
                ('R6_A/rise_end_a', (0.49, 0.965), 650))]                          # 收势：弓步上冲、双臂送刀指向右上巨印
            self.KA = [a_r6.anc_for(p_, f) for (p_, f, _) in self.K]
            self.KT = [(0.017, 0.734), (0.986, 0.276), (0.94, 0.011)]              # 各图刀尖（原图归一化）
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            gm = np.clip((yy - 880) / 30, 0, 1)
            gt = cv2.resize(A.tex(207, 512, 10, 5), (W, H))
            self.ground = gm[..., None], ((0.025 + 0.02 * gt) * (0.6 + 0.6 * np.exp(-((xx - 1250) / 700) ** 2)))[..., None] * np.array([1.0, 0.9, 0.8], np.float32)

    def render(self, t):
        if R5.ON['rise']: return self.render6(t)
        return self.render5(t)

    def render6(self, t):
        """r6 #11（用户：0:42 角色图丑、姿势不好看）：极低机位全身（头顶留白、脚入画）。41.97 前低伏蓄势（缓缓再压低），
        撩刀 1 帧中段（刀平扫 + 横向动态模糊）→ 弓步上冲收势，双臂把刀送向右上金光里的巨印；新月刀弧从左下刀尖位扫到右上刀尖位。"""
        u = self.u(t)
        fr = night((0.04, 0.035, 0.03), (0.12, 0.10, 0.09), y1=800)
        fr = A.glow(fr, (1300, 200), 520, 0.55, (1.0, 0.8, 0.5))
        fr = A.clouds(fr, t, 83, speed=(0, 60), y0=120, y1=560, amt=0.8, col=(0.12, 0.10, 0.09), light=(1300, 200), light_r=500,
                      light_col=(1.0, 0.8, 0.5), thr=0.44)
        gm, gc = self.ground
        fr = fr * (1 - gm) + gc * gm
        fr = RAIN.draw(fr, t, 0.6, angle=-6, light=(1300, 200), layers=(0, 1))
        ts = V(42.0); a = t - ts
        at = (860, 930)
        sx_, sy_ = R8.shake(t, ts, amp=14, tau=0.10, seed=3)
        cs = np.zeros((H // 2, W // 2), np.float32)                                      # 脚下接触阴影
        cv2.ellipse(cs, (at[0] // 2, at[1] // 2), (170 if a < 0 else 210, 14), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        fr = fr * (1 - 0.7 * cv2.resize(cv2.GaussianBlur(cs, (0, 0), 6), (W, H))[..., None])
        if a < 0:
            i, mb, dy = 0, (0, 0), 6 * eio(clamp01((t - self.t0) / max(1e-3, ts - self.t0)))
        elif a < 1 / 30 - 1e-4:
            i, mb, dy = 1, (34, -10), 0
        else:
            i, mb, dy = 2, (0, 18 * max(0, 1 - a / 0.12)), -12 * eout(clamp01(a / 0.4))
        spr, f, h = self.K[i]
        fr, info = A.place(fr, t, spr, (at[0] + sx_, at[1] + dy + sy_), h=h, anc=self.KA[i], rim=COLD, rim_amt=2.8, rim_dir=(0.6, -0.8),
                           wind=10, grade=dict(expo=0.62 if a < 0 else 0.80, sat=0.42, gamma=1.08), mblur=mb, breathe=0.0)
        if a >= 0:
            P0 = np.array([540.0, 800.0]); P2 = np.array(info['to_scr'](self.KT[2])) if i == 2 else np.array([1160.0, 285.0])
            Pm = np.array([1230.0, 560.0]); Q = 2 * Pm - (P0 + P2) / 2
            q = min(1.0, a / 0.07); fade = max(0.0, 1 - a / 0.45)
            L = np.zeros((H // 2, W // 2), np.float32); N = 40
            pts = [((1 - s_) ** 2 * P0 + 2 * (1 - s_) * s_ * Q + s_ * s_ * P2) for s_ in np.linspace(0, q, N)]
            for j in range(N - 1):
                w_ = 1 + int(16 * (j / N) ** 1.5)
                cv2.line(L, tuple((pts[j] / 2).astype(int)), tuple((pts[j + 1] / 2).astype(int)), 0.35 + 0.65 * j / N, w_, cv2.LINE_AA)
            L = cv2.resize(L, (W, H)) * fade
            fr = fr + (cv2.GaussianBlur(L, (0, 0), 2) * 1.2 + cv2.GaussianBlur(L, (0, 0), 18) * 1.0)[..., None] * np.array([0.95, 0.9, 0.82], np.float32)
            fr = K.sparks(fr, t, 81, (1300, 260), n=70, life=0.6, speed=(200, 900), dirc=(0, 1), spread=1.3, grav=900, area=(260, 10), amt=0.8, t0=ts, burst=True)
            fr = K.sparks(fr, t, 82, at, n=40, life=0.5, speed=(80, 300), dirc=(0, -1), spread=1.6, grav=500, area=(160, 6), amt=0.35, t0=ts, burst=True,
                          color=(0.5, 0.45, 0.4))                                         # 蹬地扬尘
            if a < 0.06: fr = fr * 1.35 + 0.06 * GOLDV
        return fr, (5 if 0 <= a < 0.12 else 0)

    def render5(self, t):
        u = self.u(t)
        fr = night((0.04, 0.035, 0.03), (0.12, 0.10, 0.09), y1=800)
        fr = A.glow(fr, (1300, 200), 500, 0.5, (1.0, 0.8, 0.5))
        fr = A.clouds(fr, t, 83, speed=(0, 60), y0=120, y1=520, amt=0.8, col=(0.12, 0.10, 0.09), light=(1300, 200), light_r=500,
                      light_col=(1.0, 0.8, 0.5), thr=0.44)
        fr = RAIN.draw(fr, t, 0.6, angle=-6, light=(1300, 200), layers=(0, 1))
        # 第八棒（critic_A_r5 P0-1）：两档姿态 —— 42.0 前蓄势（人压低、身体向左后拧 −13°、背光压暗成剪影），
        #   42.0 撩刀瞬间人随刀上提（0.12s 升 150px、回正 +2° 过冲）+ 震屏，之后继续缓升收势
        a = t - V(42.0)
        k = eout(clamp01(a / 0.12)) if a >= 0 else 0.0
        pre = clamp01((t - self.t0) / max(1e-3, V(42.0) - self.t0))
        y_ = 1150 - 8 * pre - 150 * k - 25 * clamp01(a / 0.6) if a >= 0 else 1150 - 12 * eio(pre)
        rot_ = -13 + 15 * k - 2 * clamp01((a - 0.12) / 0.3) if a >= 0 else -13 - 2 * eio(pre)
        sx_, sy_ = R8.shake(t, V(42.0), amp=16, tau=0.10, seed=3)
        expo_ = 0.82 if a >= 0 else 0.55
        if a < 0:                                                                      # 第九棒：蓄势换真低位蓄力精灵 slash_coil（压低、刀低垂右后、仰视），缓缓再压低一点
            fr, info = A.place(fr, t, self.coil, (930 - 20 * eio(pre) + sx_, 1080 + 18 * eio(pre)), h=700, rim=COLD, rim_amt=1.5,
                               rim_dir=(0.6, -0.8), wind=12, grade=dict(expo=0.58, sat=0.38), rot=-1.5 * eio(pre), wrap=0.15)
        else:
            fr, info = A.place(fr, t, S('A/slash_up', 'dm'), (900 + 30 * (1 - k) + sx_, y_ + sy_), h=820 * (0.9 + 0.1 * k), rot=rot_, rim=COLD,
                               rim_amt=3.2, rim_dir=(0.6, -0.8), wind=12,
                               grade=dict(expo=expo_, sat=0.38), mblur=(0, 30 * k * (1 - clamp01(a / 0.2))))
        if a >= 0:
            fr = K.sparks(fr, t, 81, (1300, 330), n=70, life=0.6, speed=(200, 900), dirc=(0, 1), spread=1.3, grav=900, area=(300, 10), amt=0.8, t0=V(42.0), burst=True)
            L = np.zeros((H // 2, W // 2), np.float32)
            q = min(1, a / 0.1)
            cv2.ellipse(L, (int(700 / 2), int(1000 / 2)), (int(900 / 2), int(750 / 2)), 0, -90, -90 + 85 * q, 1.0, 5, cv2.LINE_AA)
            L = cv2.resize(L, (W, H)) * max(0, 1 - a / 0.5)
            fr = fr + (L * 1.4 + cv2.GaussianBlur(L, (0, 0), 16) * 1.5)[..., None] * np.array([1.0, 0.92, 0.8], np.float32)
            if a < 0.06: fr = fr * 1.4 + 0.08 * GOLDV
        return fr, (5 if 0 <= a < 0.12 else 0)


# V21 42.68–44.03 ECU 巨字「锋」压满屏，与巨印「正」一同被斩成两半错开，碎块飞散；末帧墨缝 → 交给 B 组（墨渗成纸）
class V21(Shot):
    def __init__(self):
        T.warm('锋芒', 'xing', 500)
        self.face = PR.seal_face('正', 760, style='bai', wear=0.35, seed=4)
    def render(self, t):
        u = self.u(t); ts = V(43.30)
        # 第七棒：去掉印面方块（读作灰平板 + 又一个方印母题）→ 墨渍体积底 + 冷雨 + 火星
        fr = R7.ink_bg(t) * (1 + 0.04 * u)
        fr = RAIN.draw(fr, t, 0.35, angle=-6, layers=(0, 1))
        a = t - ts
        L = T.Layer()
        p = cprog(7, [8], t, 0.12)[0]
        tf = CT(7, 8)
        if t < tf - 0.14:                                                               # 第十一棒（P0-1）：斩缝里不再露半截「锋」（缝里残块读不出字）→ 42.70 前不出字
            pass
        elif R5.ON['fengmang']:                                                         # r6 #12（用户：锋芒两字不好看）→ 生图狂草书法 cal_feng_v1 / cal_mang_v1
            s_ = clamp01((t - (self.t0 + 0.08)) / (tf + 0.10 - (self.t0 + 0.08)))          #   飞白、枯笔、墨点俱全；位置/节奏/斩开与原版一致
            if t < tf or p > 0:
                g = R5.cal_alpha('cal_feng_v1', 600)
                bl = 10 * math.sin(math.pi * s_) if t < tf else 0.0
                sc = 1.0 if t < tf else 1 + 0.08 * (1 - eout(p))
                if sc > 1.001: g = cv2.resize(g, None, fx=sc, fy=sc)
                if bl > 0.5: g = cv2.blur(g, (int(bl * 3) | 1, 1))
                L.paste(g, 690 + 980 * (1 - eout(s_)), 530, (0.97, 0.94, 0.88), 0.95 if t < tf else max(0.95, eout(p)))
        elif t < tf:                                                                    # 第八棒（P1-6）：转场斩缝里就露出「锋」——随刀势自右滑入，42.80 落定
            s_ = clamp01((t - (self.t0 + 0.08)) / (tf + 0.10 - (self.t0 + 0.08)))
            T.place(L, '锋', 690 + 980 * (1 - eout(s_)), 530, 500, (0.97, 0.94, 0.88), 'xing', alpha=0.9, blur=10 * math.sin(math.pi * s_))
        elif p > 0:
            s_ = clamp01((t - (self.t0 + 0.08)) / (tf + 0.10 - (self.t0 + 0.08)))
            T.place(L, '锋', 690 + 980 * (1 - eout(s_)), 530, 500, (0.97, 0.94, 0.88), 'xing', alpha=max(0.9, eout(p)), scale=1 + 0.08 * (1 - eout(p)))
        p2 = cprog(7, [9], t, 0.12)[0]
        if p2 > 0 and R5.ON['fengmang']:
            g = R5.cal_alpha('cal_mang_v1', 600); sc = 1 + 0.3 * (1 - eout(p2))
            if sc > 1.001: g = cv2.resize(g, None, fx=sc, fy=sc)
            L.paste(g, 1250, 530, (0.86, 0.12, 0.08), eout(p2))
        elif p2 > 0: T.place(L, '芒', 1240, 530, 500, (0.86, 0.12, 0.08), 'xing', alpha=eout(p2), scale=1 + 0.3 * (1 - eout(p2)))
        if a < 0:
            fr = T.compose(fr, L, shadow=0.7, glow=0.25)
        else:
            fr = T.slash_layer(fr, L, clamp01(a / 0.73), (960, 540), -62, slide=0.12, sz=560, length=1500,
                               sparks=(0 if (a < 0.09 and not R6C_OFF('feng')) else 90),   # r6 第三棒 #12：斩下首帧火星全挤在刀光头上 → 锯齿白条（1299f），首帧只留平滑刀光   # 第八棒：错开量 0.35→0.12，「锋芒」两半留在画里到末段
                               style_kw=dict(shadow=0.7, glow=0.3))
            if a < 0.07: fr = fr * 1.5 + 0.07 * RED
            # 墨缝：斩线处渗出墨（给 B 组 ink_bleed 入口）
            k = clamp01((a - 0.58) / 0.15) ** 1.3                                         # 第八棒（P1-6）：墨缝收得更晚，43.9 前「锋芒」余烬仍在
            if k > 0:
                yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
                th = math.radians(-62); n = (-(xx * 2 - 960) * math.sin(th) + (yy * 2 - 540) * math.cos(th))
                nz = cv2.resize(A.ink_noise(5, 256), (W // 2, H // 2))
                ink = np.clip((60 + 900 * k ** 2 + nz * 200 - np.abs(n)) / 40, 0, 1)
                ink = cv2.resize(ink, (W, H))[..., None]
                fr = fr * (1 - ink) + INK * ink
                seam = cv2.resize(np.exp(-(n / 4) ** 2), (W, H))[..., None]
                fr = fr + seam * RED * 1.2 * (1 - k * 0.5)
        return fr, (5 if 0 <= a < 0.1 else 0)


# =====================================================================================
# 剪辑表：切点帧（=拍点最近帧 - 1，见 A_storyboard.md）
SHOTS = [A01, A02, A03, A04, A05, A06, A07a, A08,                    # 第五棒：A07a/A07b 同场景两拍 → 合成一镜 A07a（镜内 11.98 闪电 + 升镜）
         V01, V02, V03, V04, V05, V06, V07, V08, V09, V10, V11, V12, V13, V14, V15, V16, V17, V18, V19, V20, V21]
BEAT_T = [0.0, 2.21, 4.06, 5.97, 7.38, 7.85, 10.61, 13.35,
          15.21, 17.00, 17.95, 19.78, 20.69, 21.20, 22.52, 23.45, 25.29, 27.10, 28.93, 29.86, 30.77, 32.60, 34.44, 36.27, 38.10,
          39.47, 40.84, 41.77, 42.68, 44.034]
CUT_F = [0] + [round(b * FPS) - 1 for b in BEAT_T[1:-1]] + [F1]
for _S, _a, _b in zip(SHOTS, CUT_F, CUT_F[1:]):
    _S.t0, _S.t1 = _a / FPS, _b / FPS

# (名称, pre, post, kw)；'hard' = 硬切 + 切后 2 帧冲击；第四棒：whip 0、occlusion 3→2、slash_wipe 3→2、match_cut 3→2，
# 新增 a_cloud / a_zoom2 / a_seam（中间帧都带前后镜元素）
CUTS = {
    'A02': ('a_cloud', 0.20, 0.24, dict(seed=2)),                                     # 云墙横扫：A01 云海 → A02 山脊
    'A03': ('a_glint', 0.14, 0.18, dict(angle=-12, center=(960, 560))),             # 第五棒：冷光掠刃（山脊线 → 刀身线），替换蓝色闪电圈
    'A04': ('ink_bleed', 0.12, 0.18, dict(seed=7, center=(1300, 400))),
    'A05': ('hard', 0, 0, {}),
    'A06': ('hard', 0, 0, {}),                                                        # 片名刀光在镜内（A05 末帧预光条）
    'A07a': ('occlusion', 0.14, 0.16, dict(kind='pillar', direction=-1, seed=6)),     # 前景旗杆擦过（片名屏幕层不动）
    'A07b': ('zoom_through', 0.16, 0.20, dict(center=(960, 620), variant='raindrop')),  # 穿过一滴雨：滴内倒映城墙
    'A08': ('smoke_through', 0.06, 0.40, dict(seed=8, direction=1, density=0.65)),    # 片名化灰成烟，烟后露出城门
    'V01': ('a_seam', 0.10, 0.20, {}),                                               # 城门合缝，门缝里开出雨刃
    'V02': ('hard', 0, 0, {}),
    'V03': ('shatter', 0.04, 0.20, dict(seed=3, center=(1060, 880), n=60)),
    'V04': ('occlusion', 0.14, 0.14, dict(kind='spear', direction=-1, seed=4)),
    'V05': ('hard', 0, 0, {}),
    'V06': ('hard', 0, 0, {}),
    'V07': ('match_cut', 0.08, 0.10, dict(shape='line', center=(960, 600), angle=0, mode='cut')),   # 寒光横线 ↔ 丹陛顶边
    'V08': ('paper_tear', 0.10, 0.20, dict(seed=8, angle=6)),
    **({'V08': ('a_zoom2', 0.14, 0.20, dict(center=(860, 470), seed=8))} if R5.ON['zoom'] else {}),   # 第五轮 4：撕纸 → 推镜穿越（推进高处剪影，玉玺从中心开出）
    'V09': ('a_brush', 0.14, 0.20, dict(seed=9)),                                    # 第五棒：飞白大笔横扫（水墨），替换蓝色闪电圈
    'V10': ('hard', 0, 0, {}),
    'V11': ('flash_red', 0.03, 0.10, {}),
    'V12': ('a_cleave', 0.10, 0.16, dict(angle=58, center=(960, 540), mode='open')),     # 第七棒：一条斩线把 V11 劈成两块向两侧飞开，缝里露出 V12 的红（原 pre=0 时 A=B，精灵复制/倒置）
    'V13': ('a_glint', 0.10, 0.14, dict(angle=32, center=(960, 600))) if (R6C_OFF('sf7') or not R5.ON['sha_fang']) else ('cont', 0, 0, {}),   # r6 第三棒 #7：殺/放一镜到底不切（'cont'：无转场无冲击、机位连续）  # 第七棒：收刀 —— 一线冷光沿 V12 斩线掠过即换（原 a_split 三条带、人物无头；不再切块）
    'V14': ('hard', 0, 0, {}),
    'V15': ('match_cut', 0.08, 0.12, dict(shape='line', center=(770, 560), angle=90, mode='cut')),   # 刀身刻字 ↔ 碑面刻字
    'V16': ('a_glyph', 0.08, 0.34, dict(ch='主', center=(750, 650), size=230) if (R6C_OFF('stele') or not R5.ON['carve']) else dict(ch='主', center=(598, 668), size=200)),   # r6 第三棒 #9：对准镜头跟刀后碑上「主」的屏幕位置（原 750 落在「张」上）   # 第九棒：post 0.24→0.34          # 第六棒：以「主」字墨槽为遮罩硬边扩开（原叠化两脸糊在一起）
    'V17': ('hard', 0, 0, {}),
    'V18': ('smoke_through', 0.06, 0.30, dict(seed=18, direction=1, density=0.6)),     # 第六棒：尘浪卷过（原 flash_red 把印坑「正」染成红方印）
    'V19': ('hard', 0, 0, {}),
    'V20': ('hard', 0, 0, {}),
    'V21': ('a_cleave', 0.10, 0.16, dict(angle=-62, center=(1420, 540), mode='open', col=(1.0, 0.85, 0.6))),   # 第七棒：V20 撩刀弧光一线斩开画面，露出「锋」（原灰平板 + 半截「锋」重复）
}

M3 = V3.Move3
MOVES3 = {
    'A01': M3('sine_io', None, z=(1.0, 1.05), y=(-120, 0), note='摇臂降 crane down + 缓推'),
    'A02': M3('sine_io', 'beat', x=(-70, 70), z=(1.02, 1.05), note='横移 truck right（前景松枝视差）'),
    'A03': M3('sine_io', 'beat', x=(70, -80), yaw=(-11, 7), z=(1.02, 1.08), note='第九棒：沿刀身环绕 orbit（yaw -11→7°，刀身透视由远端收窄转为近端放大）+ 推'),
    'A04': M3('sine_io', 'beat', z=(1.08, 1.0), vtg=(-0.05, 0.32), x=(20, -20), note='第九棒：dolly zoom 变焦推拉（侧脸不变，背后月晕向外拉开）'),
    'A05': M3('expo_in', None, z=(1.0, 1.10), note='急推（蓄力）'),
    'A06': M3('sine_io', 'beat', z=(1.12, 1.02), y=(-60, 40), pitch=(4, -2), rot=(-1.0, 0.4), note='第九棒：crane down 降镜 + 拉（片名屏幕层不动，山脊视差升起）'),
    'A07a': M3('sine_io', 'beat', z=(1.0, 1.16), x=(50, -70), y=(-40, 60), pitch=(-5, 2), note='第五棒：2.7s 低机位推轨 + 升镜仰（合并 A07b）'),
    'A07b': M3('sine_io', 'beat', x=(60, -60), z=(1.02, 1.06), note='横移（城墙纵深视差）'),
    'A08': M3('sine_io', 'beat', z=(1.0, 1.10), note='背影推进'),
    'V01': M3('sine_io', 'beat', z=(1.0, 1.08), pitch=(2, -1), note='推 + 下摇'),
    'V02': M3('expo_out', None, z=(1.06, 1.0), x=(-40, 30), note='低机位跟步'),
    'V03': M3('sine_io', 'beat', x=(-60, 60), pitch=(6, 0), note='高机位横移 + 俯仰'),
    'V04': M3('sine_io', 'beat', x=(-90, 70), yaw=(7, -6), z=(1.0, 1.07), note='第九棒：侧移环绕 + 推（人迎镜走近，前景枪林反向扫过）'),
    'V05': M3('expo_in', None, z=(1.0, 1.12), note='急推'),
    'V06': M3('expo_out', None, z=(1.12, 1.03), yaw=(-6, 6), note='第十一棒：环绕 orbit 主体写进场景层（22°：军阵同向、前景枪林反向视差）；这里只留透视余量 + 推'),
    'V07': M3('sine_io', 'beat', y=(60, -40), pitch=(-6, 0), note='摇臂升 crane up'),
    'V08': M3('sine_io', 'beat', z=(1.0, 1.08), pitch=(-4, 3), yaw=(6, -4), note='第九棒：随玺下压的俯仰 tilt + 小环绕（落印时机位压下）'),
    'V09': M3('sine_io', 'beat', yaw=(-12, 8), z=(1.0, 1.06), note='环绕 orbit'),
    'V10': M3('sine_io', 'beat', y=(30, -30), z=(1.0, 1.07), note='第五棒：低机位缓推 + 微升'),
    'V11': M3('sine_io', None, z=(1.0, 1.06), note='极慢推'),
    'V12': M3('sine_io', 'beat', x=(-50, 40), rot=(-2, 1), note='手持 + 横移'),
    'V13': M3('sine_io', 'beat', x=(40, -40), z=(1.04, 1.0), note='反向横移 + 拉'),
    'V14': M3('sine_io', 'beat', x=(-50, 50), z=(1.0, 1.05), note='沿刀身滑移'),
    'V15': M3('sine_io', 'beat', z=(1.08, 1.0), x=(30, -30), note='第五棒：缓拉 + 横移跟刀尖'),
    'V16': M3('sine_io', 'beat', y=(40, -30), pitch=(-5, 0), z=(1.0, 1.05), note='仰拍升'),
    'V17': M3('sine_io', 'beat', y=(-60, 40), note='跟印下摇'),
    'V18': M3('sine_io', 'beat', z=(1.08, 1.0), rot=(-2, 0), note='高机位拉 + 回旋'),
    'V19': M3('sine_io', 'beat', z=(1.0, 1.06), y=(50, -40), pitch=(5, -3), note='第九棒：crane up 仰升（金色逆光剪影）'),
    'V20': M3('expo_out', None, y=(60, -20), pitch=(-5, 0), z=(1.06, 1.0), note='硬切冲击后仰摇'),
    'V21': M3('expo_out', None, z=(1.08, 1.0), rot=(2, 0), note='punch 后稳'),
}
if R5.ON['sha_fang'] and not R6C_OFF('sf7'):                                            # r6 第三棒 #7：V12+V13 机位连成一条匀速横移 + 极慢推（交界速度一致）
    MOVES3['V12'] = M3('lin', None, x=(-30, -12), note='殺/放一镜：匀速横移（前半）')
    MOVES3['V13'] = M3('lin', None, x=(-12, 24), note='殺/放一镜：匀速横移（后半）')
FG = {'A02': ('ash', 0.3), 'A04': ('ash', 0.25), 'A06': ('ember', 0.5), 'A07a': ('rain', 0.4), 'A07b': ('rain', 0.35), 'A08': ('rain', 0.3), 'V01': ('ash', 0.3), 'V02': ('rain', 0.45),
      'V04': ('rain', 0.4), 'V06': ('rain', 0.35), 'V07': ('gold', 0.3), 'V09': ('gold', 0.3), 'V12': ('ember', 0.4), 'V13': ('ash', 0.3),
      'V14': ('ember', 0.4), 'V16': ('gold', 0.4), 'V17': ('ash', 0.5), 'V18': ('rain', 0.4), 'V19': ('rain', 0.3), 'V20': ('ember', 0.4), 'V21': ('ember', 0.5)}
EXPO = {}
EXPO_ALL = 1.15

# 段落能量包络（前奏轻 → 片名重击 → 主歌压低 → 「杀」「正义」「锋芒」加码）
ENERGY = [(0, 0.3), (7.8, 0.4), (7.85, 1.3), (9.0, 0.8), (13.3, 0.5), (15.2, 0.7), (21.2, 1.1), (22.5, 0.75), (29.8, 1.0),
          (32.6, 0.8), (38.6, 1.3), (39.5, 0.9), (41.7, 1.2), (44.1, 1.3)]
_ET = np.array([e[0] for e in ENERGY]); _EV = np.array([e[1] for e in ENERGY])
def energy(t): return float(np.interp(t, _ET, _EV))


# ---------------- 屏幕层：署名（前奏）——思源宋职务 + 马善政人名竖排 + 名后小朱印，墨晕逐字显出
CREDITS = [  # (显出起点, 退场起点, 职务, 人名, x, y_top, seal)
    (0.45, 1.95, '出品人', '西几王传媒', 560, 250, '西几王'),
    (0.60, 1.95, '后期总监', '沉溺', 360, 250, None),               # HANDOFF §1：0.45 出品人 + 0.60 后期总监
    (2.21, 3.85, '编剧 / 导演', '苏打', 420, 300, '苏打'),
    (4.06, 5.40, '美术设计', 'Cait', 1640, 250, None),           # 第七棒：5.40 起退场，A04 ink_bleed（5.84）前退净，不叠脸
    (4.21, 5.40, '音乐', '西几王', 1440, 250, '西几王'),
    (5.97, 7.30, 'AI画师', '沉溺　雪晴　索恩', 640, 250, None),
]


def credits(fr, t):
    for (a, b, role, names, x, y, seal) in CREDITS:
        a_, b_ = V(a), V(b)
        if not (a_ - 0.01 <= t < b_ + 0.35): continue
        p = clamp01((t - a_) / 0.55)                     # 第二棒：0.55s 显全（A01 1.2s 时两条署名都已完整）
        out = clamp01((t - b_) / 0.3)
        if names.isascii():                                   # 第四棒：拉丁名横排（不再旋转竖排）——职务竖排，人名横排在职务下方
            g = T.credit_block(fr, role, '', x, y, p, role_size=30, name_size=62, seal_text=None, seed=len(role))
            # 第八棒（critic_A_r5 P1-4，第三次提）：拉丁名不再横排混在竖排署名里 → 字母直立逐个竖排（与中文人名同一列、同字高节奏）
            L = T.Layer(); f = T._font('song', 58)
            from PIL import Image as _I, ImageDraw as _D
            # 第十棒（critic_A_r6 P2-7）：字距按字母墨迹高度收紧（小写 a/i/t 不再按 64px 等距 → 间隙 14px，与中文列同节奏）
            yc = y + 62 - 24
            for j, ch in enumerate(names):
                im = _I.new('L', (80, 80), 0); _D.Draw(im).text((40, 40), ch, font=f, fill=255, anchor='mm')
                a_ = np.asarray(im).astype(np.float32) / 255
                rows = np.nonzero(a_.max(1) > 0.05)[0]; r0, r1 = (int(rows[0]), int(rows[-1]) + 1) if len(rows) else (30, 50)
                a_ = a_[r0:r1]
                L.paste(a_, x, yc + (r1 - r0) / 2, (0.95, 0.94, 0.92), eout(clamp01(p * 1.6 - 0.4 - 0.12 * j)))
                yc += (r1 - r0) + 10                     # 第十一棒（P2，第三次提）：字间 14→10px（再小「i」的点会贴到「a」上读成「Ca·it」）
            g = T.compose(g, L, shadow=0.7, glow=0.1)
        else:
            g = T.credit_block(fr, role, names, x, y, p, role_size=30, name_size=62, seal_text=seal, seed=len(role))
        fr = fr + (g - fr) * (1 - out)
    return fr


LY_TXT = {0: '长夜压在我刀锋之上', 1: '五百重甲拦不住一道寒光', 2: '谁在高处定对错罪状', 4: '我杀过恶徒也放过混账',
          6: '若正义由权势执掌', 7: '那我宁愿做乱世的锋芒'}
if R5.ON['sha_fang'] and 'ly_sha' not in os.environ.get('A_R6_OFF', ''):
    LY_TXT[4] = '我殺过恶徒也放过混账'          # r6 #7：屏幕层小字与镜内大字统一用繁体「殺」（旧：大字「殺」旁边是简体小「杀」）；A_R6_OFF=ly_sha 回滚


# ---------------- 屏幕层：主歌一歌词（第四棒：停用 LY 双列竖排）
# 每句一个主词 150–240px 与动作同帧落下（笔触书写 + 落字微震），余字 70–96px 同一基线横排、暗衬条托底；y 180–900 安全区；
# 主词为朱/金；镜内互动大字（五百重甲、寒光、罪状、称量、杀、放、刀身刻字、主张、正、锋芒）仍由镜头自己画。
# (行, [(字序, 字号, 颜色)], 中心 x, 基线 y, 退场秒, 点亮扫光)
_Wt, _R, _G = (0.95, 0.93, 0.88), (0.86, 0.12, 0.08), (1.0, 0.78, 0.40)
LY2 = [
    # 第十一棒（critic_A_r7 P0-1）：原「长夜」与「压在我刀锋之上」两组分开排，「压」落在「夜」字底下被盖住 → 16.85 读成「长夜在我刀」。
    #   整句并成一行、按歌词顺序从左到右逐字排开；17.70 起整句统一淡出（0.20s），17.90 前退净，不与 V03「五百」同屏
    (0, [(k, (230 if k in (0, 1, 5, 6) else 132), (_R if k == 5 else (_G if k == 6 else _Wt))) for k in range(0, 9)], 960, 440, 17.75, False),   # 第九棒（P1-3）：「刀锋」230 与「长夜」同级，其余 132   # 第八棒（P1-5）：压在我「刀锋」之上 84→100/150，进主词体系
    (1, [(4, 190, _Wt), (5, 190, _Wt), (6, 190, _R), (7, 90, _Wt), (8, 90, _Wt)], 1380, 330, 20.78, False),   # 第七棒：移到右上袍面暗区，不压拳头 # 拦不住·一道（第五棒：移到上方天幕，21.13 前退净，给 20.82「寒」让下方）
    (2, [(0, 190, _Wt), (1, 190, _Wt), (2, 190, _G), (3, 190, _G)], 960, 900, 23.44, False),        # 谁在高处（自殿檐压下）
    (2, [(4, 96, _Wt), (5, 96, _Wt), (6, 96, _Wt)], 1580, 820, 24.40, False),                       # 定对错（第七棒：后景脸已去，落在右下屏风暗部，不压人）
    (4, [(k, 80, _R if k == 1 else _Wt) for k in range(0, 5)], 420, 905, 30.74, False),             # 我杀过恶徒（第六棒：挪到左下暗区鬼屠刀下，不贴恶徒腿）
    (4, [(k, 80, _Wt) for k in range(5, 10)], 640, 880, 32.55, False),                              # 也放过混账
    (6, [(0, 120, _Wt), (1, 220, _R), (2, 220, _R)], 600, 905, 37.90, False),   # 第七棒：38.30 前退净，不与「由权势」叠成残字   # 第六棒：挨着金光里的巨印剪影                       # 若「正义」
    (6, [(3, 80, _Wt), (4, 140, _G), (5, 140, _G), (6, 80, _Wt), (7, 80, _Wt)], 960, 925, 39.85, False),  # 由「权势」执掌（第六棒：离开印面，放到下三分之一）
    (7, [(0, 128, _Wt), (1, 128, _Wt), (2, 145, _G), (3, 145, _G), (4, 80, _Wt), (5, 145, _R), (6, 145, _R), (7, 80, _Wt)],
     1280, 262, 42.48, True),  # r6 #11：整句缩 12%、上移 38px —— V20 新收势刀尖指向右上（y≈280），不再插进字里  # 第十一棒：整句移到右上（V19 镜像后人在左；V18 人头上方、V20 刀弧右侧都是空天幕）   # 第十一棒：42.40→42.48 + 0.15s 等量淡出，「的」(42.36) 完整露出后 42.63 切点前退净   # 第七棒：中心 640→730，首字「那」不出左边画                                                                        # 那我「宁愿」做「乱世」的（随刀光逐字点亮）
]


def lyrics(fr, t):
    if NOHLYR: return fr                                               # r6 #53 → #55：横排 LY2 默认保留；R5_NOVLYR=all 才去
    for (li, chars, cx, by, t_out, sweep) in LY2:
        t_on = CT(li, chars[0][0]) - 0.3
        if li == 2 and chars[0][0] == 0: t_on = max(t_on, V(22.52))          # 第五棒：「谁在高处」等 V06「寒光」切走后再落（不叠团）
        if li == 6 and chars[0][0] == 3: t_on = max(t_on, V(38.30))
        if li == 1 and chars[0][0] == 4: t_on = max(t_on, V(19.37))          # 第十一棒：等 V03「五百重甲」退净再起「拦」（原 19.23 起笔与「甲」右上并存）          # 第六棒：「由权势执掌」等 V16「若正义」切走后再落
        if not (t_on <= t < t_out + 0.4): continue
        if li == 1 and chars[0][0] == 4 and not R6E_OFF('lycut') and t >= V05.t0: continue   # r6 第五棒：20.9 V05 右上暗红「住一道」残影 = 本句淡出拖进 V05 手部特写 → 随 V04→V05 硬切一起退净
        out = clamp01((t - t_out) / (0.15 if li in (0, 7) else 0.25))
        adv = [s * 1.04 for (_, s, _) in chars]
        x = cx - sum(adv) / 2
        L = T.Layer(); pmax = 0.0; big = max(s for (_, s, _) in chars)
        for (k, s, c), a in zip(chars, adv):
            p = clamp01((t - max(CT(li, k) - 0.16, t_on)) / 0.26)
            if li == 1 and k in (7, 8) and not R6E_OFF('lycut'): p = clamp01((t - max(CT(li, k) - 0.16, t_on)) / 0.17)   # r6 第五棒：「一道」写快一点，V05 切点前写完整
            if li == 7 and s >= 150: p = clamp01((t - max(CT(li, k) - 0.10, t_on)) / 0.15)   # 第七棒：「乱世」等大字快写，残笔不超过 4 帧（41.31 红色半字）
            pmax = max(pmax, p)
            if p > 0:
                cxx = x + a / 2; cyy = by - s / 2
                if s >= 150:
                    pop = 1 + 0.12 * math.exp(-max(0, t - CT(li, k)) / 0.09) * (t >= CT(li, k))
                    g = BG(LY_TXT[li][k], 'kai', s, p, seed=li * 13 + k)
                    if pop > 1.001: g = cv2.resize(g, None, fx=pop, fy=pop)
                    L.paste(g, cxx, cyy, c)
                elif LY_TXT[li][k] == '殺':                                     # r6 #7：马善政楷无「殺」→ 用镜内同一张书法生图缩成小字
                    g = R5.cal_alpha(SF_SHA[0], int(s * 1.08)) * eout(p)
                    if p < 1: g = cv2.GaussianBlur(g, (0, 0), 0.3 + 3 * (1 - p))
                    L.paste(g, cxx, cyy + 14 * (1 - eout(p)), c)
                else:
                    T.place(L, LY_TXT[li][k], cxx, cyy + 14 * (1 - eout(p)), s, c, 'kai', alpha=eout(p), blur=3 * (1 - p))
                if sweep:
                    a_ = t - CT(li, k)
                    if 0 <= a_ < 0.5: fr = A.glow(fr, (cxx, cyy), s * 0.9, 0.5 * math.exp(-a_ / 0.15), (1.0, 0.8, 0.5))
            x += a
        if pmax <= 0: continue
        if out > 0:                     # 第十一棒（P0-1「乱世」→「乱七」）：退场不再用墨噪蚀字（会把「世」蚀成「七」）→ 整句等量淡出 + 上浮虚化，每字始终完整
            L.A *= (1 - eout(out))
            if out > 0.05: L.A = cv2.GaussianBlur(L.A, (0, 0), 0.5 + 5 * out)
        # 暗衬条：基线下沿到字顶的柔边暗带（只压字背后，让字在任何底上都可读）
        w_ = sum(adv) + 80; bx0 = int(cx - w_ / 2); bx1 = int(cx + w_ / 2)
        band = np.zeros((H // 4, W // 4), np.float32)
        cv2.rectangle(band, (bx0 // 4, int(by - big * 1.05) // 4), (bx1 // 4, int(by + 18) // 4), 1.0, -1)
        band = cv2.resize(cv2.GaussianBlur(band, (0, 0), 10), (W, H))[..., None]
        fr = fr * (1 - 0.55 * band * min(1, pmax * 2) * (1 - out))
        fr = T.compose(fr, L, shadow=0.75, shadow_sigma=14, glow=0.18)
    return fr


def a_zoom2(A_, B_, p, center=(960, 540), seed=0):
    """第四棒：推镜穿越（替换叠化版 a_zoom）。A 加速推近 + 径向模糊；B 从中心一个墨边圆窗里放大开出，窗沿冷光；
    中间帧 = 外圈 A 的推镜拖影 + 内圈清晰的 B，两镜元素都可读，无灰糊、无白场。"""
    e = TR.ease_in(min(1, p / 0.8), 2.2)
    A2 = TR._radial_blur(TR._zoom(A_, 1 + 0.8 * e, center), center, 0.10 * e)
    q = 1 - TR.ease_out(p, 3); B2 = TR._radial_blur(TR._zoom(B_, 1 + 0.35 * q, center), center, 0.05 * q)
    yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
    d = np.hypot(xx * 2 - center[0], yy * 2 - center[1])
    nz = cv2.resize(A.ink_noise(seed + 31, 256), (W // 2, H // 2)) * 120
    R = 2300 * TR.ease_in(p, 1.8)
    m = cv2.resize(np.clip((R + nz - d) / 30, 0, 1), (W, H))[..., None]
    rim = cv2.resize(np.exp(-((R + nz - d) / 14) ** 2), (W, H))[..., None] * (p < 0.95)
    return A2 * (1 - m) + B2 * m + rim * np.array([0.5, 0.6, 0.85], np.float32) * 0.8


def a_zoom3(A_, B_, p, center=(960, 430), seed=0):
    """r6 #4（用户：撕纸转场 → 拉近 zoom）：纯推镜。A 向高处剪影加速推近（×1→×3.4，径向拖影，宫灯拉成放射光），
    镜头钻进黑色剪影 → 画面被衣袍的暗部吞满的那一刻接 B；B 从 ×1.45 继续推近的余势里落定到 ×1（同一推进方向、同一中心）。
    不再有窗口/圆框/冷光描边（旧 a_zoom2 的蓝色电光边读成闪电圈）。"""
    e = TR.ease_in(clamp01(p / 0.56), 1.9)
    A2 = TR._radial_blur(TR._zoom(A_, 1 + 3.6 * e, center), center, 0.18 * e)
    A2 = A2 * (1 - 0.55 * e)                                                       # 钻进剪影的暗部
    q = 1 - TR.ease_out(clamp01((p - 0.44) / 0.56), 2.6)
    B2 = TR._radial_blur(TR._zoom(B_, 1 + 0.45 * q, center), center, 0.12 * q)
    m = clamp01((p - 0.47) / 0.16); m = m * m * (3 - 2 * m)
    return A2 * (1 - m) + B2 * (0.55 + 0.45 * m) * m


def a_glint(A_, B_, p, angle=-12.0, center=(960, 560)):
    """第六棒（critic_A_r3 P1-12：中点读成灰黑巨型斜板）：只有一根 ≤12px 的冷钢细光沿 -12° 斜线（=山脊线/刀身线）扫过；
    光头过画中点那一帧硬切到 B，光线在 B 上继续扫完并衰减。无板体、无白场。"""
    th = math.radians(angle)
    yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
    n = (-(xx * 2 - center[0]) * math.sin(th) + (yy * 2 - center[1]) * math.cos(th))
    along = ((xx * 2 - center[0]) * math.cos(th) + (yy * 2 - center[1]) * math.sin(th))
    head = -1150 + 2300 * TR.ease_io(p)
    tail = np.clip((head - along) / 900, 0, 1)
    core = np.exp(-(n / 2.5) ** 2) * (along < head) * (1 - tail) ** 1.5
    hd = np.exp(-((along - head) ** 2 + n ** 2 * 6) / 1600)
    L = cv2.resize(core * 1.6 + hd * 2.2, (W, H))
    L = L + cv2.GaussianBlur(L, (0, 0), 10) * 0.9 + cv2.GaussianBlur(L, (0, 0), 40) * 0.35
    base = A_ if p < 0.5 else B_
    return base + L[..., None] * np.array([0.72, 0.82, 1.0], np.float32) * (1.0 if p < 0.85 else (1 - p) / 0.15)


def a_brush(A_, B_, p, seed=0):
    """第五棒（替换 V09 入点蓝色闪电圈）：飞白大笔横扫。一笔浓墨自左向右扫过（笔头湿重、笔尾飞白丝），墨过之处纸后露出 B；
    中间帧 = 左 B / 墨笔 / 右 A，水墨风格、无冷光圈。"""
    yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
    nz = cv2.resize(A.ink_noise(seed + 41, 256), (W // 2, H // 2))
    hair = cv2.resize(A.tex(seed + 43, 256, 40, 3)[:, :6], (W // 2, H // 2), interpolation=cv2.INTER_LINEAR)   # 横向拉长 = 笔毛丝纹
    head = (-0.25 + 1.6 * TR.ease_io(p)) * W
    x = xx * 2 + (yy * 2 - 540) * 0.18 + (nz - 0.5) * 120
    tail = np.clip((head - x) / 1100, 0, 1)                                       # 0 = 笔头, 1 = 笔尾
    body = np.clip((head - x) / 30, 0, 1) * (tail < 1)
    wid = 300 * (1 - 0.35 * tail) + 60 * (nz - 0.5)
    band = np.clip((wid - np.abs(yy * 2 - 560 - 40 * np.sin(xx / 120))) / 25, 0, 1)
    dry = np.clip((hair - 0.25 - 0.55 * tail ** 1.5) * 6, 0, 1)                   # 笔尾飞白
    ink = body * band * dry
    rev = np.clip((head - 650 - x + (nz - 0.5) * 300) / 80, 0, 1)
    m = cv2.resize(rev, (W, H))[..., None]; k = cv2.resize(ink, (W, H))[..., None]
    # 第八棒（P2-8）：笔扫过的 A 被墨刷碎 —— 横向拖拽 + 褪色压暗（「罪状」红块不再整块留在笔后）
    psd = cv2.resize(np.clip((head - x) / 140, 0, 1), (W, H))[..., None]
    if psd.max() > 0:
        Asm = cv2.blur(A_, (91, 3)); g_ = Asm.mean(-1, keepdims=True)
        Asm = (Asm * 0.3 + g_ * 0.7) * 0.35
        A_ = A_ * (1 - psd) + Asm * psd
    out = A_ * (1 - m) + B_ * m
    return out * (1 - 0.95 * k) + k * np.array([0.012, 0.012, 0.016], np.float32)


def a_split(A_, B_, p, angle=32.0, center=(1200, 620)):
    """第六棒：A 沿斩线一刀两分（两块），两半沿斩线反向滑开并向两侧退，缝里露出 B；断口一线红热。"""
    th = math.radians(angle)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    n = -(xx - center[0]) * math.sin(th) + (yy - center[1]) * math.cos(th)
    e = TR.ease_in(p, 1.8); sl = 260 * e; op = 560 * e
    out = B_.copy()
    for sgn in (1, -1):
        M = np.float32([[1, 0, sgn * (sl * math.cos(th)) - sgn * op * math.sin(th) * 0], [0, 1, sgn * (sl * math.sin(th)) + sgn * op * math.cos(th)]])
        half = cv2.warpAffine(A_, M, (W, H), borderMode=cv2.BORDER_CONSTANT)
        mk = cv2.warpAffine(((n > 0) if sgn > 0 else (n <= 0)).astype(np.float32), M, (W, H))[..., None]
        out = out * (1 - mk) + half * mk
    nb = -(xx - center[0]) * math.sin(th) + (yy - center[1]) * math.cos(th)
    seam = np.exp(-(np.abs(nb) - op) ** 2 / 6) * (p < 0.7)
    return out + seam[..., None] * np.array([1.0, 0.25, 0.12], np.float32) * 1.2


def a_glyph(A_, B_, p, ch='主', center=(960, 540), size=230):
    """第六棒：字形遮罩转场 —— B 从「主」字的墨槽里硬边涌出，字形放大到盖满全屏；边缘带墨的毛刺，不叠化。"""
    sc = 1 + 2.6 * eio(min(1.0, p / 0.8)) + 16 * clamp01((p - 0.8) / 0.2) ** 2   # 第九棒（P1-4）：前 80% 只放大到 3.6×，「主」整字可读，最后 20% 才炸开盖满
    L = T.Layer(); T.place(L, ch, center[0], center[1], size, 'white', 'kai', scale=sc, texture=False)
    m = L.A
    nz = cv2.resize(A.ink_noise(77, 256), (W, H))
    # 第八棒（P2-9）：墨边加飞白丝 + 外缘晕染，让遮罩读得出是「主」字的笔画而不是几块黑块
    hair = cv2.resize(A.tex(79, 256, 40, 3)[:, :5], (W, H), interpolation=cv2.INTER_LINEAR)
    hair = cv2.warpAffine(hair, cv2.getRotationMatrix2D((960, 540), -35, 1.3), (W, H), borderMode=cv2.BORDER_REFLECT)
    mb = cv2.GaussianBlur(m, (0, 0), 2 + 4 * p)
    mb2 = cv2.GaussianBlur(m, (0, 0), 14 + 30 * p)
    bandw = np.clip(1 - np.abs(mb2 - 0.5) * 2.0, 0, 1)
    m = np.clip((mb - 0.5 + (nz - 0.5) * 0.25 + (hair - 0.5) * 1.1 * bandw) * 8 + 0.5, 0, 1)
    if p > 0.88: m = np.maximum(m, (p - 0.88) / 0.12)   # 第九棒：0.75→0.88，膨胀阶段不再整屏半透
    edge = np.clip(m * (1 - m) * 4, 0, 1)
    halo = np.clip(cv2.GaussianBlur(m, (0, 0), 14) - m, 0, 1) * (1 - p)
    A_ = A_ * (1 - 0.75 * halo[..., None])
    out = A_ * (1 - m[..., None]) + B_ * m[..., None]
    return out * (1 - 0.8 * edge[..., None]) + edge[..., None] * np.array([1.0, 0.75, 0.4], np.float32) * 0.6


def a_cloud(A_, B_, p, seed=0):
    """第四棒：云层横扫（A01 云海 → A02）：一堵带体积的云墙自左向右推过，云墙前沿后露出 B；中间帧同时有 A、云墙、B。"""
    yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
    nz = cv2.resize(A.tex(seed + 61, 256, 4, 5), (W // 2, H // 2))
    edge = (-0.35 + 1.7 * TR.ease_io(p)) * W
    d = (xx * 2 - edge) + (nz - 0.5) * 520 + 80 * np.sin(yy / 40)
    cloud = np.exp(-(d / 260) ** 2)
    m = cv2.resize(np.clip(-d / 120 + 0.5, 0, 1), (W, H))[..., None]
    c = cv2.resize(cloud * (0.6 + 0.6 * nz), (W, H))[..., None]
    out = A_ * (1 - m) + B_ * m
    return out * (1 - 0.8 * c) + c * np.array([0.14, 0.16, 0.21], np.float32)


def a_seam(A_, B_, p):
    """第四棒：城门合缝 → 门缝里开出 V01（A08 → V01）：前半 A（门正合拢）；后半门缝冷光一线从中缝向两侧拉开成 B。"""
    if p < 0.4: return A_
    q = TR.ease_in((p - 0.4) / 0.6, 1.6)
    xx = np.arange(W, dtype=np.float32)[None, :, None]
    half = 6 + 980 * q
    m = np.clip((half - np.abs(xx - 960)) / 6, 0, 1)
    rim = np.exp(-((np.abs(xx - 960) - half) / 5) ** 2)
    return A_ * (1 - m) + B_ * m + rim * np.array([0.7, 0.8, 1.0], np.float32) * (1.4 - q)


def a_zoom(A_, B_, p, center=(960, 540)):
    """第三棒：推镜穿越（无闪白版）。A 加速推近 + 径向模糊，B 从放大态减速回位；0.35–0.65 两画面按亮度叠化，
    中间帧始终同时带着前后镜的画面元素（不出现白场/灰雾）。"""
    e = TR.ease_in(min(1, p / 0.65), 2.4); A2 = TR._radial_blur(TR._zoom(A_, 1 + 0.7 * e, center), center, 0.09 * e)
    q = 1 - TR.ease_out(max(0, (p - 0.35) / 0.65), 3); B2 = TR._radial_blur(TR._zoom(B_, 1 + 0.4 * q, center), center, 0.08 * q)
    m = TR.ease_io((p - 0.35) / 0.3)
    return np.maximum(A2 * (1 - m), B2 * m) * 0.6 + (A2 * (1 - m) + B2 * m) * 0.4


# 第八棒（critic_A_r5 P0-1）：镜头层镜内运动（在转场与歌词之前），保证起/止两帧机位可见不同
INNER = {
    'A01': dict(z=(1.0, 1.05), c=(960, 600)),
    'A02': dict(z=(1.0, 1.05), c=(900, 560), d=(-50, 0)),
    'A03': dict(z=(1.0, 1.06), c=(900, 520), d=(-40, 0)),
    'A04': dict(z=(1.0, 1.07), c=(1250, 420), d=(-30, 10)),
    'A07a': dict(z=(1.0, 1.12), c=(960, 760), d=(0, 70), ease='lin'),                 # 升镜：城楼在画里下沉 + 推
    'V09': dict(z=(1.0, 1.09), c=(960, 400), d=(0, 10)),
    'V10': dict(z=(1.0, 1.12), c=(930, 880), rot=(-1.6, 1.4), wob=(0.4, 0.55)),       # 秤盘在链上摆：机位随盘倾
    'V13': dict(z=(1.0, 1.07), c=(1250, 560), d=(-50, 0)),
    **({'V12': dict(z=(1.0, 1.012), c=(960, 540), ease='lin'), 'V13': dict(z=(1.012, 1.037), c=(960, 540), ease='lin')}
       if (R5.ON['sha_fang'] and not R6C_OFF('sf7')) else {}),                                     # r6 第三棒 #7：一镜到底匀速极慢推（脚点留在有效区内）
    'V19': dict(z=(1.0, 1.07), c=(500, 380), d=(0, 25)),
    'V04': dict(z=(1.0, 1.10), c=(1180, 560), d=(0, -12)),
    'V02': dict(z=(1.0, 1.06), c=(1000, 760), d=(-30, 0)),                           # 第十一棒：低机位跟步轻推                           # 第十一棒：低机位前推 dolly-in（配合场景层侧移 truck）
    'V14': dict(z=(1.09, 1.13), c=(960, 500), rot=(-9.0, -2.0)),                      # 第十棒：荷兰角回正（-9°→-2°，拔刀时机位随刀「扶正」），与 V11/V19 的正机位脸拉开
    'V20': dict(z=(1.10, 1.0), c=(900, 600), ease='out'),
}


class _Lazy:
    def __init__(self, cls): self.cls = cls; self.t0 = cls.t0; self.t1 = cls.t1; self.obj = None; self.id = cls.__name__
    def render(self, t):
        if self.obj is None: self.obj = self.cls()
        fr, ca = self.obj.render(t)
        sp = INNER.get(self.id)
        if sp: fr = R8.inner_push(fr, (t - self.t0) / max(1e-6, self.t1 - self.t0), t, sp)
        return fr, ca


def build_cam():
    cam = V3.VCam3(HMP, energy=energy)
    for S_ in SHOTS:
        cam.shot(S_.t0, S_.t1, MOVES3.get(S_.__name__))
        c = CUTS.get(S_.__name__)
        if c and c[0] == 'whip': cam.whip(S_.t0, c[3]['dir'], c[3].get('L', 400))
        elif c and c[0] == 'cont': pass                                              # r6 第三棒：不切镜（机位连续）
        else: cam.cut(S_.t0)
    return cam


class Section:
    def __init__(self):
        self.shots = [_Lazy(S_) for S_ in SHOTS]
        self.ids = [S_.__name__ for S_ in SHOTS]
        self.cam = build_cam()
        self.fg = VC.FGLayer(17, n=24)

    def idx(self, t):
        for i, s in enumerate(self.shots):
            if t < s.t1 - 1e-6: return i
        return len(self.shots) - 1

    def raw(self, t):
        i = self.idx(t); s = self.shots[i]
        for j in (i, i + 1):
            if j <= 0 or j >= len(self.shots): continue
            b = self.shots[j]; name, pre, post, kw = CUTS.get(self.ids[j], ('hard', 0, 0, {}))
            c = b.t0
            if name in ('hard', 'whip') or not (c - pre - 1e-6 <= t < c + post - 1e-6): continue
            a = self.shots[j - 1]
            B, ca2 = b.render(t)
            Af, ca1 = a.render(t) if (pre > 0 or t < c) else (B, 0)
            p = (t - (c - pre)) / (pre + post)
            if pre == 0: p = 0.5 + 0.5 * p
            Af = np.clip(Af, 0, 4).astype(np.float32); B = np.clip(B, 0, 4).astype(np.float32)
            if name == 'a_zoom': return a_zoom(Af, B, p, **kw), max(ca1, ca2)
            if name == 'a_zoom2':
                if 'zoom3' in os.environ.get('A_R6_OFF', ''): return a_zoom2(Af, B, p, **kw), max(ca1, ca2)
                return a_zoom3(Af, B, p, center=(960, 470)), max(ca1, ca2)      # r6 #4：纯推镜（A_R6_OFF=zoom3 回旧版）
            if name == 'a_glint': return a_glint(Af, B, p, **kw), max(ca1, ca2)
            if name == 'a_brush': return a_brush(Af, B, p, **kw), max(ca1, ca2)
            if name == 'a_cloud': return a_cloud(Af, B, p, **kw), max(ca1, ca2)
            if name == 'a_seam': return a_seam(Af, B, p), max(ca1, ca2)
            if name == 'a_split': return a_split(Af, B, p, **kw), max(ca1, ca2)
            if name == 'a_glyph': return a_glyph(Af, B, p, **kw), max(ca1, ca2)
            if name == 'a_cleave': return R8.a_cleave8(Af, B, p, **kw), 0
            return TR.transition(name, Af, B, p, **kw), max(ca1, ca2)
        fr, ca = s.render(t)
        name = CUTS.get(self.ids[i], ('hard',))[0]
        if name == 'hard' and i > 0:
            k = int((t - s.t0) * FPS + 1e-6)
            if k < 2:
                a_ = 1.0 if k == 0 else 0.45
                fr = K.cam(fr, 1 + 0.03 * a_) * (1 + 0.22 * a_) + 0.05 * a_
                ca = max(ca, 3 if k == 0 else 1)
        return fr, ca

    def frame(self, f):
        t = f / FPS
        fr, ca = self.raw(t)
        sid = self.ids[self.idx(t)]
        fr, st = self.cam.apply(np.clip(fr, 0, 4).astype(np.float32), t)
        kind, amt = FG.get(sid, (None, 0))
        if sid in ('V12', 'V13') and R5.ON['sha_fang'] and not R6C_OFF('sf7'):      # r6 第三棒 #7：前景粒子随擦除 余烬 → 灰（不在镜界跳变）
            xe = _sf_edge(t); m = 0.0 if xe is None else clamp01(xe / W)
            if m < 1: fr = self.fg.draw(fr, t, st, 'ember', 0.4 * (1 - m))
            if m > 0: fr = self.fg.draw(fr, t, st, 'ash', 0.3 * m)
        elif kind: fr = self.fg.draw(fr, t, st, kind, amt)
        fr = fr * (EXPO_ALL * EXPO.get(sid, 1.0))
        fr = fr + 0.012 * (1 - np.clip(fr, 0, 1))
        if TITLE_HIT <= t < V(13.35) + 0.5:                                     # 第四棒：片名 = 屏幕层（A06 → A07a → A07b 不动，13.35 化灰）
            k = t - TITLE_HIT
            _to = clamp01((t - V(13.35)) / 0.45) if R6B_OFF('title') else clamp01((t - V(13.25)) / 0.19)   # r6 第二棒：片名 13.23→13.42 退净（403f 前）
            fr = TITLE.draw(fr, t, out=_to, sheen=clamp01((t - V(11.52)) / 0.7) if t >= V(11.52) else None,
                            glow=0.5 * math.exp(-max(0, k) / 0.3) + 0.22 * sum(math.exp(-max(0.0, t - V(b)) / 0.15) * (t >= V(b)) for b in (8.75, 9.22, 9.68, 10.15, 10.61, 11.05, 11.98, 12.45, 12.89)))
        if t < 7.9 and not R5.ON['credits_off']: fr = credits(fr, t)          # 第五轮 1：开头署名去掉（片尾已有）
        fr = lyrics(fr, t)
        ca = max(ca, int(round(4 * min(1.0, st['punch']))))
        out = K.finish(fr, t, ca=ca, vig=0.45, red_keep=1.0)
        return K.to8(out)


def frame(f, cache):
    if 'sec' not in cache: cache['sec'] = Section()
    return cache['sec'].frame(int(f))


if __name__ == '__main__':
    # 自测：python3 units/sec_a_intro_verse1.py <秒> [...] → /tmp/a_<秒>.png
    from PIL import Image
    c = {}
    for a in sys.argv[1:]:
        f = int(round(float(a) * FPS))
        Image.fromarray(frame(f, c)).save('/tmp/a_%s.png' % a); print('saved', a, flush=True)
