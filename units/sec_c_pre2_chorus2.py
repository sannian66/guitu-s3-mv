"""units/sec_c_pre2_chorus2.py — 第四轮 C 组：预副歌二 + 副歌二「破」（帧 3534–4839，117.795–161.309s）
设计说明：crew/round4/C_storyboard.md（逐镜表 + 接缝）。41 镜，平均 1.06s/镜（预副歌二 15 镜 1.11s，副歌二 26 镜 1.03s）。
接口：READY / frame(f, cache) -> uint8 (1080,1920,3)（已收尾：调色、辉光、色差、暗角、颗粒、2.39 黑边）。
组内自测：V4_FORCE=c_pre2_chorus2 python3 render_sprite_full.py frame 140.0 /tmp/x.png
视觉语言（与副歌一「月夜·砖墙·单色」区分）：预副歌二 = 烛光暗房里的「剧本 / 提线 / 暗箱」（暖金、宋体铅字打字机）→
「我不低头」起切进雨夜；副歌二 = 雷暴（电白 + 朱红血雨），字墙 = 宋体律令砌成，巨印、巨掌、天平，不出现月亮与金裂砖墙。"""
import os, sys, math
ROOT = '/workspace/work/mv'
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, cv2
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import c_kit as K
from c_kit import (W, H, FPS, BAR, RED, GOLD, COLD, WARM, clamp, sm, eout, ein, eio, lerp, V, pulse, CT, camxf, handheld,
                   dirblur, radial, storm_sky, wet_ground, rain, fog, bolt, bolt_env, vol_light, put, Sent, draw_sent,
                   paste_glyph, glyph_layer, RED_T, GOLD_T, WHITE_T, CREAM)
import typo as T, trans as TR, fx2
import props as PR
import c_props as CP
import c_trans as CX
import c_piying as PY
from c1kit import finish, to8, sparks, dust, crack_path, draw_crack, paper_dark, fbm

READY = True
# 第五轮（USER_NOTES_r5 #34–#43 前半）：去画内字 / 纲上线 / 大局为上做进匾 / C21·C22 人物位置。C_R5=0 回到第四轮效果。
R5 = os.environ.get('C_R5', '1') != '0'
# 第六轮（crew/round6/C_r6.md：#35 #36 #39–#43 返工）。C_R6=0 退回第六轮开工时的状态（=第五轮返工版），用于改前/改后对比。
R6 = R5 and os.environ.get('C_R6', '1') != '0'
if R5:   # 第五轮通用：人物精灵 wind_amp 统一 5–8px（0 = 道具/手/刀/影子，保持不动）
    _put0 = put
    def put(fr, t, name, *a, wind=6.0, **kw):
        if wind: wind = min(8.0, max(5.0, float(wind)))
        return _put0(fr, t, name, *a, wind=wind, **kw)

# 第九棒：c_kit.tex 的缓存键只认名字不认 seed —— 'c1'/'c2'/'gw' 三张云/水纹底图由「本进程第一个调用的镜头」决定，
# 导致分块渲染 / 联系表分批时同一帧长得不一样（例：C15 批渲成一团白曝、整段顺渲则是清楚的落地闪电）。
# 这里按整段顺渲的第一个调用者（C07 storm seed=7 → c1/c2；C09 storm seed=9 → gw）预热，任何起点渲出来都 = 顺渲结果。
K.tex('c1', seed=7 + 1, base=3); K.tex('c2', seed=7 + 2, base=6); K.tex('gw', seed=9 + 7, base=10)
F0, F1 = 3534, 4839
T0, T1 = F0 / FPS, F1 / FPS


# =====================================================================================
# 共用：烛光暗房（预副歌二前半）
def candle_room(t, seed=0, glow_c=(1300, 300), amt=1.0):
    fr = paper_dark(31).copy() * 0.55
    fr = K.vol_light(fr, glow_c, 900, WARM * 0.5, 0.35 * amt * (1 + 0.08 * math.sin(t * 23) + 0.05 * math.sin(t * 9.1)))
    return fr


def storm(t, seed=0, horizon=780, flash=0.0, fc=(960, 160), ox=0.0, oy=0.0, refl=0.5, cloud=1.0, ground=True, rip=1.0):
    fr = storm_sky(t, seed, horizon, flash, fc, ox=ox, oy=oy, cloud=cloud)
    if ground: fr = wet_ground(fr, t, horizon, seed, refl=refl * (1 + flash), ox=ox, ripples=rip)
    return fr


# ---------------- 纸人（提线木偶）
_PUP = {}
def puppet_sprite(seed, h=300):
    k = (seed, h)
    if k in _PUP: return _PUP[k]
    r = np.random.default_rng(seed)
    w = int(h * 0.6); A = np.zeros((h, w), np.float32); cx = w // 2
    hr = int(h * 0.075)
    cv2.circle(A, (cx, int(h * 0.12)), hr, 1.0, -1, cv2.LINE_AA)
    body = np.array([[cx - h * 0.09, h * 0.2], [cx + h * 0.09, h * 0.2], [cx + h * 0.2, h * 0.78], [cx - h * 0.2, h * 0.78]], np.int32)
    cv2.fillPoly(A, [body], 1.0, cv2.LINE_AA)
    sw = r.uniform(-0.15, 0.15)
    for s in (-1, 1):
        cv2.line(A, (int(cx + s * h * 0.08), int(h * 0.24)), (int(cx + s * h * (0.22 + sw * s)), int(h * 0.52)), 1.0, max(2, int(h * 0.035)), cv2.LINE_AA)
        cv2.line(A, (int(cx + s * h * 0.07), int(h * 0.76)), (int(cx + s * h * 0.1), int(h * 0.98)), 1.0, max(2, int(h * 0.04)), cv2.LINE_AA)
    # 纸纹 + 毛边
    nz = cv2.resize(r.random((h // 6 + 1, w // 6 + 1)).astype(np.float32), (w, h))
    A = np.clip(A * (0.85 + 0.25 * nz), 0, 1)
    A = cv2.GaussianBlur(A, (0, 0), 0.8)
    fib = cv2.GaussianBlur(r.random((h, w)).astype(np.float32), (0, 0), 1.0)
    _PUP[k] = (A, fib)
    return _PUP[k]


def draw_puppet(fr, A, fib, cx, top, ang, col=(0.92, 0.80, 0.58), back=1.0, alpha=1.0):
    h, w = A.shape
    M = cv2.getRotationMatrix2D((w / 2, 0), ang, 1.0); M[0, 2] += cx - w / 2; M[1, 2] += top
    a = cv2.warpAffine(A, M, (W, H)) * alpha
    f = cv2.warpAffine(fib, M, (W, H))
    c = np.asarray(col, np.float32) * (0.45 + 0.55 * f[..., None]) * back
    return fr * (1 - a[..., None]) + c * a[..., None]


def red_line(fr, p0, p1, w=2, amt=1.0, glow=0.6):
    L = np.zeros((H // 2, W // 2), np.float32)
    cv2.line(L, (int(p0[0] * 4), int(p0[1] * 4)), (int(p1[0] * 4), int(p1[1] * 4)), 1.0, max(1, int(w / 2)), cv2.LINE_AA, 3)
    g = cv2.GaussianBlur(L, (0, 0), 4)
    lay = cv2.resize(L + g * glow, (W, H))
    return fr * (1 - np.clip(cv2.resize(L, (W, H)), 0, 1)[..., None] * 0.9 * amt) + lay[..., None] * RED * 1.2 * amt


def slash_streak(fr, p0, p1, q, width=6, col=(1.0, 0.97, 0.92), amt=1.6):
    """刀光（白刃 + 辉光），q 0..1 生长，之后衰减"""
    if q <= 0: return fr
    p0 = np.array(p0, float); p1 = np.array(p1, float)
    grow = min(1.0, q * 3); fade = 1 - sm(0.35, 1.0, q)
    e = p0 + (p1 - p0) * grow
    L = np.zeros((H // 2, W // 2), np.float32)
    cv2.line(L, tuple((p0 * 4).astype(int)), tuple((e * 4).astype(int)), 1.0, max(1, int(width / 2)), cv2.LINE_AA, 3)
    g1 = cv2.GaussianBlur(L, (0, 0), 3); g2 = cv2.GaussianBlur(L, (0, 0), 14)
    lay = cv2.resize(L * 1.5 + g1 * 1.2 + g2 * 1.4, (W, H))
    return fr + lay[..., None] * np.asarray(col, np.float32) * amt * fade


def arc_streak(fr, c, rx, ry, a0, a1, q, width=8, col=(1, 0.97, 0.92), amt=1.6, rot=0):
    if q <= 0: return fr
    fade = 1 - sm(0.4, 1.0, q); ae = a0 + (a1 - a0) * min(1, q * 2.5)
    L = np.zeros((H // 2, W // 2), np.float32)
    n = 40; th = np.radians(np.linspace(a0, ae, n))
    pts = np.stack([c[0] + rx * np.cos(th), c[1] + ry * np.sin(th)], 1)
    if rot:
        cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        d = pts - c; pts = c + np.stack([d[:, 0] * cr - d[:, 1] * sr, d[:, 0] * sr + d[:, 1] * cr], 1)
    P = (pts / 2 * 8).astype(np.int32)
    for i in range(n - 1):
        wv = max(1, int(width / 2 * (0.3 + 0.7 * i / n)))
        cv2.line(L, tuple(P[i]), tuple(P[i + 1]), 1.0, wv, cv2.LINE_AA, 3)
    g = cv2.GaussianBlur(L, (0, 0), 3); g2 = cv2.GaussianBlur(L, (0, 0), 16)
    lay = cv2.resize(L * 1.4 + g + g2 * 1.3, (W, H))
    return fr + lay[..., None] * np.asarray(col, np.float32) * amt * fade


def shock_ring(fr, c, q, rx=900, flat=0.18, col=COLD, amt=1.0, n=3):
    if q <= 0 or q >= 1: return fr
    L = np.zeros((H // 2, W // 2), np.float32)
    for i in range(n):
        qq = q - i * 0.12
        if qq <= 0: continue
        r = rx * eout(qq, 2.2)
        cv2.ellipse(L, (int(c[0] / 2), int(c[1] / 2)), (int(r / 2), max(1, int(r * flat / 2))), 0, 0, 360, (1 - qq) * (1 - 0.3 * i), 3, cv2.LINE_AA)
    g = cv2.GaussianBlur(L, (0, 0), 3)
    return fr + cv2.resize(L + g * 1.5, (W, H))[..., None] * np.asarray(col, np.float32) * amt


def splash(fr, t, t0, c, seed, n=140, spread=520, up=900, col=COLD, amt=0.9):
    return sparks(fr, t, seed, c, n=n, life=0.9, speed=(up * 0.4, up), dirc=(0, -1), spread=0.9, grav=2200, size=1, amt=amt,
                  t0=t0, burst=True, color=tuple(col), area=(spread * 0.5, 6))


def carve_glyph(fr, ch, cx, cy, size, q, ang=-35.0, color=RED_T, hot=(1.0, 0.75, 0.35), seed=0, t=0.0):
    """第五棒：字被刀刃「刻出」——沿 ang 方向的斜向擦除显形，前沿一条赤热刃口（白→橙），刻过的笔画朱红 + 余烬闪烁。q 0..1+。"""
    if q <= 0: return fr
    L = T.Layer(); T.place(L, ch, cx, cy, size, color, 'serif_black', texture=False)
    bx = L.box(4)
    if bx is None: return fr
    x0, y0, x1, y1 = bx
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    d = (xx - x0) * ca + (yy - y0) * sa
    dmin, dmax = d.min(), d.max(); d = (d - dmin) / max(1.0, dmax - dmin)
    qq = q * 1.15
    rev = np.clip((qq - d) / 0.04, 0, 1)
    edge = np.exp(-((d - qq) / 0.035) ** 2) * (q < 1.1)
    A = L.A[y0:y1, x0:x1]
    L.A[y0:y1, x0:x1] = A * rev
    out = T.compose(fr, L, shadow=0.85, shadow_sigma=20, outline=3, glow=0.6, glow_sigma=20, glow_color=(0.95, 0.12, 0.05))
    ember = (0.35 + 0.25 * math.sin(t * 37 + seed)) * sm(0, 0.3, q) * (1 - sm(1.2, 3.0, q))
    hotm = (A * (edge * 2.2 + ember * rev * 0.0))[..., None]
    out[y0:y1, x0:x1] += hotm * np.asarray(hot, np.float32) * 1.6
    return out


def blade_smear(fr, p0, p1, q, bend=0.25, width=70, col=(0.92, 0.95, 1.0), amt=1.3, seed=0, warm=0.0):
    """第五棒：真实感刀光——不是激光线，而是一道弯月形的运动拖影：前沿锐亮、尾部渐虚，带沿刀路的拉丝纹理。
    p0→p1 为刀路（屏幕坐标），bend 弯度（相对弦长，正 = 向左手侧鼓），q 0..1 扫过、之后 0.35 内消散。"""
    if q <= 0 or q > 1.6: return fr
    p0 = np.asarray(p0, np.float32); p1 = np.asarray(p1, np.float32)
    d = p1 - p0; n = np.array([-d[1], d[0]], np.float32); n /= (np.linalg.norm(n) + 1e-6)
    c = (p0 + p1) / 2 + n * bend * np.linalg.norm(d)
    head = min(1.0, q * 2.2); fade = 1 - sm(0.45, 1.6, q)
    S = 4; M = np.zeros((H // S, W // S), np.float32); Cc = np.zeros_like(M)
    N = 48
    pts = []
    for i in range(N + 1):
        u = head * i / N
        pt = (1 - u) ** 2 * p0 + 2 * (1 - u) * u * c + u * u * p1
        pts.append(pt)
    for i in range(N):
        k = (i + 1) / N                                    # 0 尾 → 1 头
        w = max(1, int(width / S * (0.15 + 0.85 * math.sin(math.pi * min(1, 0.15 + 0.85 * k)))))
        a = (k ** 1.6)
        cv2.line(M, tuple((pts[i] / S).astype(int)), tuple((pts[i + 1] / S).astype(int)), a, w, cv2.LINE_AA)
        cv2.line(Cc, tuple((pts[i] / S).astype(int)), tuple((pts[i + 1] / S).astype(int)), a, 1, cv2.LINE_AA)
    r = np.random.default_rng(seed)
    nz = cv2.GaussianBlur(r.random(M.shape).astype(np.float32), (0, 0), 1.2)
    M = cv2.GaussianBlur(M, (0, 0), 2.0) * (0.55 + 0.9 * nz)
    lay = cv2.resize(M * 0.55 + cv2.GaussianBlur(Cc, (0, 0), 0.8) * 1.8 + cv2.GaussianBlur(M, (0, 0), 8) * 0.6, (W, H))
    colv = np.asarray(col, np.float32) * (1 - warm) + np.array([1.0, 0.55, 0.25], np.float32) * warm
    return fr + lay[..., None] * colv * amt * fade


def water_ripple(fr, c, k, flat=0.28, speed=520.0, amp=14.0, wl=46.0, y_top=0, life=1.4):
    """第五棒：真实积水涟漪——对画面做径向位移（透视压扁的同心波），波峰带冷高光；不画白色椭圆线。k = 落点后秒数。"""
    if k <= 0 or k > life: return fr
    cx, cy = c
    yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32) * 2
    dx = xx - cx; dy = (yy - cy) / flat
    r = np.sqrt(dx * dx + dy * dy) + 1e-3
    R = speed * k
    env = np.exp(-((r - R) / (wl * 2.2)) ** 2) * (1 - k / life) ** 1.5 * (r < R + wl * 3)
    env += 0.5 * np.exp(-((r - R * 0.62) / (wl * 1.6)) ** 2) * (1 - k / life) ** 2
    w = np.sin((r - R) / wl * 6.283) * env
    off = w * amp
    mx = (xx + dx / r * off).astype(np.float32); my = (yy + dy * flat / r * off).astype(np.float32)
    mask = (yy >= y_top).astype(np.float32)
    mx = xx + (mx - xx) * mask; my = yy + (my - yy) * mask
    out = cv2.remap(fr, cv2.resize(mx, (W, H)), cv2.resize(my, (W, H)), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    hl = cv2.resize(np.clip(w, 0, 1) * mask, (W, H))[..., None]
    return out + hl * np.array([0.55, 0.6, 0.7], np.float32) * 0.18


def arc_glyph(fr, ch, c, size, a, rot=0.0, split=0.0, split_ang=-62.0, seed=0, warm=0.0):
    """第五棒：刀光残影里的字（是非对错）——冷白芯 + 冷辉，沿刀势轻微拖影；split>0 时被斜刀分成两半错开、渐隐。"""
    if a <= 0.01: return fr
    col = (0.93, 0.96, 1.0) if warm == 0 else (1.0, 0.82, 0.5)
    if split <= 0:
        return paste_glyph(fr, ch, c[0], c[1], size, col, alpha=a, rot=rot, glow=0.9, glow_c=(0.55, 0.7, 1.0) if warm == 0 else (1, 0.5, 0.2), shadow=0.5)
    L = T.Layer(); T.place(L, ch, c[0], c[1], size, col, 'serif_black', alpha=a * (1 - sm(0.5, 1.0, split)), rot=rot, texture=False)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ca_, sa_ = math.cos(math.radians(split_ang)), math.sin(math.radians(split_ang))
    side = ((xx - c[0]) * sa_ - (yy - c[1]) * ca_) > 0
    A2 = L.A.copy(); L.A[:] = 0
    for sg in (1, -1):
        msk = (side if sg > 0 else ~side).astype(np.float32)
        off = 60 * split * sg
        M = np.float32([[1, 0, ca_ * off], [0, 1, sa_ * off + 80 * split * split]])
        L.A[:] = np.maximum(L.A, cv2.warpAffine(A2 * msk, M, (W, H)))
    return T.compose(fr, L, shadow=0.4, shadow_sigma=18, glow=0.8, glow_sigma=16, glow_color=(0.55, 0.7, 1.0))


def etched_glyph(fr, ch, c, size, a, rot=0.0, edge=(0.85, 0.93, 1.0), seed=0):
    """第七棒（critic_C_r3 P1⑤「对」压在高光刀面读不出）：刀面反光里的镂空字——字心压暗（像刻进钢里的槽），
    外沿一圈冷白亮边 + 字外一圈软暗衬，白刀面/暗雨幕上都读得出。a=0..1 出现度（亮边先亮、字槽后压暗）。"""
    if a <= 0.01: return fr
    L = T.Layer(); T.place(L, ch, c[0], c[1], size, (1, 1, 1), 'serif_black', alpha=1.0, rot=rot, texture=False)
    M = L.A
    x0, y0, x1, y1 = L.box(int(size * 0.35))
    m = M[y0:y1, x0:x1]
    r = max(2, int(size * 0.022))
    dil = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    rim = np.clip(dil - m, 0, 1)
    halo = np.clip(cv2.GaussianBlur(dil, (0, 0), size * 0.06) * 1.4, 0, 1)
    ae = clamp(a * 1.6); ag = clamp(a * 1.2 - 0.2)
    sub = fr[y0:y1, x0:x1]
    sub = sub * (1 - 0.55 * halo * ae)[..., None]                                     # 字外软暗衬
    sub = sub * (1 - 0.88 * m * ag)[..., None] + (m * ag)[..., None] * np.array([0.05, 0.05, 0.06], np.float32)   # 字槽
    gl = cv2.GaussianBlur(rim, (0, 0), 3.0)
    sub = sub + (rim * 1.4 + gl * 0.9)[..., None] * np.asarray(edge, np.float32) * ae   # 亮边 + 微辉
    fr = fr.copy(); fr[y0:y1, x0:x1] = sub
    return fr


def flash_frame(fr, amt, col=(0.92, 0.95, 1.0)):
    return fr * (1 + amt * 0.6) + amt * np.asarray(col, np.float32) * 0.5


def ink_vignette(fr, amt):
    yy, xx = np.ogrid[0:H // 4, 0:W // 4]
    d = np.sqrt(((xx * 4 - W / 2) / (W / 2)) ** 2 + ((yy * 4 - H / 2) / (H / 2.3)) ** 2)
    m = np.clip((d - (1.3 - amt * 1.3)) * 2.5, 0, 1).astype(np.float32)
    nz = cv2.resize(K.tex('inkv', seed=5, base=8), (W // 4, H // 4))
    m = np.clip(m * (0.7 + 0.6 * nz), 0, 1)
    return fr * (1 - cv2.resize(m, (W, H))[..., None])


# =====================================================================================
# 预副歌二
class Shot:
    t0 = t1 = 0.0; ca = 0
    def u(self, t): return clamp((t - self.t0) / (self.t1 - self.t0))


class C01(Shot):
    """CU 剧本：烛光下一页剧本，宋体铅字打出标题「谁定好规则」（字在纸上），太上皇执朱笔圈出「规则」。"""
    def __init__(self):
        r = np.random.default_rng(1)
        pw, ph = 1500, 980; self.pw, self.ph = pw, ph
        n = fbm(ph, pw, 77, base=60, octaves=4)
        fib = cv2.GaussianBlur(r.random((ph, pw)).astype(np.float32), (0, 0), 0.7)
        l = 0.80 + 0.08 * n + 0.05 * fib
        self.paper = np.stack([l * 0.98, l * 0.90, l * 0.74], -1).astype(np.float32)
        # 剧本正文（小号宋体，已印好，暗）
        L = T.Layer(ph, pw)
        body = ['第一回　大局', '众人各安其位　不得僭越', '凡逆命者　以罪论处', '一人之死　可换千人之安', '此乃天理　理所应当',
                '钦定　剧本提纲　不得改动', '违者　斩']
        for j, line in enumerate(body):
            for i, c in enumerate(line):
                if c.strip(): T.place(L, c, 1300 - j * 120, 330 + i * 44, 34, (0.10, 0.08, 0.07), 'serif_r', texture=False)
        self.body = L
        for c in '谁定好规则': T.glyph(c, 'serif_b', 104, False)

    def render(self, t):
        u = self.u(t)
        P = self.paper.copy()
        P = T.compose(P, self.body, shadow=0, glow=0)
        # 标题打字机（铅字敲下 + 光标）
        s = Sent(28, [0, 1, 2, 3, 4], 640, 200, size=104, mode='type', red='规则', glitch='', font='serif_b', out=99)
        L = T.Layer(self.ph, self.pw)
        n = 0
        for i, (c, (px, py)) in enumerate(zip(s.text, s.P)):
            if t < s.tin[i]: continue
            n += 1
            k = t - s.tin[i]
            col = (0.62, 0.06, 0.04) if c in '规则' else (0.07, 0.06, 0.05)
            T.place(L, c, px, py + 3 * pulse(t, s.tin[i], 0.04), 104, col, 'serif_b', scale=1 + 0.08 * pulse(t, s.tin[i], 0.05), texture=False)
        if n < 5 or int(t * 6) % 2 == 0:
            j = max(0, n - 1); px, py = s.P[j]
            L.paste(np.ones((92, 12), np.float32), px + (70 if n else -60), py, (0.7, 0.05, 0.03), 0.9)
        P = T.compose(P, L, shadow=0.0, glow=0.0)
        # 朱笔圈「规则」：118.62–118.95 一笔椭圆
        q = sm(118.58, 118.95, t)
        cx, cy = (s.P[3][0] + s.P[4][0]) / 2, s.P[3][1]
        if q > 0:
            M = np.zeros((self.ph, self.pw), np.float32)
            th = np.radians(np.linspace(-200, -200 + 380 * q, 60))
            pts = np.stack([cx + 165 * np.cos(th), cy + 78 * np.sin(th) + np.linspace(0, 14, 60)], 1).astype(np.int32)
            cv2.polylines(M, [pts], False, 1.0, 9, cv2.LINE_AA)
            M = cv2.GaussianBlur(M, (0, 0), 1.2)
            P = P * (1 - M[..., None] * 0.92) + M[..., None] * np.array([0.60, 0.05, 0.03], np.float32)
            tip = pts[-1]
        else:
            tip = np.array([cx + 260 - 120 * sm(117.8, 118.58, t), cy - 140 + 60 * sm(117.8, 118.58, t)])
        # 纸面 → 画面（透视，俯 30°），慢推 + 右移
        z = 1.0 + 0.10 * eio(u); sx = -40 + 90 * eio(u)
        q0 = np.float32([[0, 0], [self.pw, 0], [self.pw, self.ph], [0, self.ph]])
        dst = np.float32([[230, 140], [1770, 170], [1960, 1010], [-60, 990]])
        dst = ((dst - [960, 540]) * z + [960 - sx, 540]).astype(np.float32)
        Mh = cv2.getPerspectiveTransform(q0, dst)
        fr = candle_room(t) * 0.6
        pw_ = cv2.warpPerspective(P, Mh, (W, H), flags=cv2.INTER_LINEAR)
        A = cv2.warpPerspective(np.ones((self.ph, self.pw), np.float32), Mh, (W, H))
        # 烛光：右上暖光，左下暗
        yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32) * 4
        light = np.exp(-(((xx - 1500) ** 2 + (yy - 150) ** 2) / 1100 ** 2)) * (1.0 + 0.06 * math.sin(t * 21)) + 0.12
        light = cv2.resize(light.astype(np.float32), (W, H))[..., None]
        fr = fr * (1 - A[..., None]) + pw_ * A[..., None] * light * np.array([1.0, 0.93, 0.80], np.float32)
        # 第五轮 #34（用户：上面移动的图层盖住了内容 → 去掉）：太上皇执笔手精灵 C/tsh_brush 及其投影删除；朱笔圈「规则」仍自己画出。
        fr = sparks(fr, t, 11, (1500, 200), n=30, life=2.5, speed=(10, 40), dirc=(0, -1), spread=1.2, grav=-10, amt=0.25, area=(500, 200))
        return fr


class C02(Shot):
    """MS 提线：太上皇的手在画顶，朱红丝线垂下；歌词「谁写好剧本提」一字一线挂在丝线上随线摆（字即提线木偶）。"""
    XS = [520, 760, 980, 1190, 1400, 1610]
    def render(self, t):
        u = self.u(t)
        oy = lerp(70, -40, eio(u))
        fr = candle_room(t, glow_c=(960, 120), amt=1.3) * 0.8
        fr = fog(fr, t, 3, density=0.35, y0=200, y1=900, color=(0.30, 0.22, 0.15), speed=(12, -4))
        tug = sum(pulse(t, V(b), 0.18) for b in ((119.10, 119.57, 120.03, 120.33) if R5 else (119.10, 119.57, 120.03)))   # 第五棒：逐拍提线（手往上一拽，字被拽起）；第五轮：「纲」落线那拍再拽一次
        hand_y = 70 - oy * 0.6 - 26 * tug
        tips = [(830, hand_y + 300), (900, hand_y + 330), (980, hand_y + 340), (1060, hand_y + 320), (1120, hand_y + 280), (790, hand_y + 250)]  # 第四棒：字 72→104px、挂低、画在手前
        bg0 = fr.copy()
        fr, A0 = put(fr, t, 'S062/puppeteer', 960, hand_y, 640, anchor='src', src=(0.5, 0.06), rim=WARM, rim_amt=2.2, rim_dir=(0, -1),
                    expo=0.8, sat=0.4, tint=(1.0, 0.92, 0.82), wind=2)
        # 第四棒：袖口精灵底边是平切——底部 150px 渐隐进烛光暗部
        rows = np.where(A0.max(1) > 0.3)[0] if A0 is not None and A0.ndim == 2 else []
        if len(rows):
            yb = rows[-1]; yy = np.arange(H, dtype=np.float32)[:, None, None]
            g = np.clip((yy - (yb - 160)) / 150, 0, 1)
            fr = fr * (1 - g) + bg0 * g
        s = Sent(28, [5, 6, 7, 8, 9, 10], 0, 0, size=70, mode='type', red='', glitch='剧本')
        if R5:
            return self.render_r5(t, fr, oy, hand_y, tug)
        for i, x in enumerate(self.XS):
            ti = s.tin[i]
            sw = 14 * math.sin(t * 3.0 + i * 1.3) + 22 * pulse(t, ti, 0.25) * (1 if i % 2 else -1)
            ly = 690 + 70 * math.sin(i * 1.7) - oy * 0.4
            jerk = -40 * pulse(t, ti, 0.12) - 34 * tug
            end = (x + sw, ly + jerk - 50)
            fr = red_line(fr, tips[i], end, w=2, amt=0.9)
            if t >= ti:
                c = s.text[i]
                L = glyph_layer(c, end[0], end[1] + 74, 104, CREAM if c not in '剧本' else (1.0, 0.86, 0.6), font='serif_sb',
                                rot=-sw * 0.6, scale=1 + 0.15 * pulse(t, ti, 0.06))
                fr = T.compose(fr, L, shadow=0.6, shadow_sigma=14, glow=0.25, glow_sigma=10)
                if c in '剧本':
                    off = 7 * pulse(t, ti, 0.3) + 3
                    for dx, cc in ((-off, (1, 0.1, 0.1)), (off, (0.1, 0.6, 1.0))):
                        L2 = glyph_layer(c, end[0] + dx, end[1] + 74, 104, cc, font='serif_sb', rot=-sw * 0.6, alpha=0.5)
                        fr = T.compose(fr, L2, shadow=0, glow=0)
        return fr

    def render_r5(self, t, fr, oy, hand_y, tug):
        """第五轮 #35：「剧本」后加第七条红线吊「纲」（提纲），七字以画面中轴对称排开（原来六字挤在右半、提线从左指尖斜拉到最右）。
        「纲」在「提」那拍从手里顺着丝线放下来、120.60 那拍落定一拽，切点挪到「纲」字那拍（121.00 → C03 木偶齐被拽起）。"""
        s = Sent(28, [5, 6, 7, 8, 9, 10, 11], 0, 0, size=70, mode='type', red='', glitch='剧本')
        n = len(s.text)
        td, tl = V(120.07) + 1 / FPS, V(120.33)   # r5 返工：「提」那拍(120.33)前落定，2:00.4 已与其余六字同排
        if R6: td, tl = V(120.18) + 1 / FPS, V(120.36)   # r6 #35：「本」之后才从手里放线，正落在「提」那拍——「提纲」同拍落定，读序不乱（r5 版「纲」先于「提」出现）
        for i in range(n):
            x = 960 + (i - 3) * 200
            tip = (960 + (i - 3) * 64, hand_y + 300 + 40 * math.cos((i - 3) * 0.55) - 10)   # 指尖扇形对称分布
            ti = s.tin[i] if i < 6 else td
            sw = 14 * math.sin(t * 3.0 + i * 1.3) + 22 * pulse(t, ti if i < 6 else tl, 0.25) * (1 if i % 2 else -1)
            ly = 700 + 48 * math.sin(i * 1.9 + 0.4) - oy * 0.4
            jerk = -40 * pulse(t, ti if i < 6 else tl, 0.12) - 34 * tug
            drop = 0.0
            if i == 6:                                       # 纲：从手里放线落下，落定时过冲回弹
                k = sm(td, tl, t)
                drop = -(1 - eout(k)) * 360 + 18 * math.sin(max(0.0, t - tl) * 26) * math.exp(-max(0.0, t - tl) * 9) * (t >= tl)
            end = (x + sw, ly + jerk - 50 + drop)
            if i == 6 and t < td:
                continue
            if R6:   # r6 #35：线一直拴到字头（原来线头停在字上方 ~25px，字像飘着而不是被吊着），线头打个小结
                att = (end[0], end[1] + 30)
                fr = red_line(fr, tip, att, w=2, amt=0.9)
                if t >= ti: fr = _knot(fr, att)
            else:
                fr = red_line(fr, tip, end, w=2, amt=0.9)
            if t >= ti:
                c = s.text[i]
                if c == '纲':
                    a = sm(td, td + 3 / FPS, t)
                    col = (1.0, 0.66, 0.56)                       # r5 返工：与其余字同亮度（暖奶白偏红），红只留在线与微光
                    L = glyph_layer(c, end[0], end[1] + 74, 104, col, font='serif_sb', rot=-sw * 0.6, alpha=a,
                                    scale=1 + 0.10 * pulse(t, tl, 0.08))
                    fr = T.compose(fr, L, shadow=0.6, shadow_sigma=14, glow=0.30, glow_sigma=10)
                    continue
                L = glyph_layer(c, end[0], end[1] + 74, 104, CREAM if c not in '剧本' else (1.0, 0.86, 0.6), font='serif_sb',
                                rot=-sw * 0.6, scale=1 + 0.15 * pulse(t, ti, 0.06))
                fr = T.compose(fr, L, shadow=0.6, shadow_sigma=14, glow=0.25, glow_sigma=10)
                if c in '剧本':
                    off = 2.5 * pulse(t, ti, 0.3) + 1.2              # r5 返工：色散收小（原 7+3px / 0.5）
                    for dx, cc in ((-off, (1, 0.1, 0.1)), (off, (0.1, 0.6, 1.0))):
                        L2 = glyph_layer(c, end[0] + dx, end[1] + 74, 104, cc, font='serif_sb', rot=-sw * 0.6, alpha=0.16)
                        fr = T.compose(fr, L2, shadow=0, glow=0)
        return fr


def _knot(fr, p, r=3.2, col=(0.62, 0.07, 0.05)):
    """r6 #35：红线拴字处的小结（线头压进字头一点，读成「吊着」）。"""
    x, y = int(round(p[0])), int(round(p[1]))
    if not (0 < x < W - 1 and 0 < y < H - 1): return fr
    m = np.zeros((H, W), np.float32)
    cv2.circle(m, (x, y), int(r + 0.5), 1.0, -1, cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), 0.7)[..., None]
    return fr * (1 - 0.9 * m) + m * 0.9 * np.array(col, np.float32)


def hand_shadow_mask(cx, cy, sc, t, tw=0.0, seed=0):
    """纯代码手影（取代 S062 第 3 次使用）：腕从画顶伸下，掌心朝下、五指垂指，指节随 t 微动；tw 抽动（0..1，拽线）。
    返回 (mask 半分辨率 float32, 指尖坐标列表 全分辨率)。"""
    h2, w2 = H // 2, W // 2
    m = np.zeros((h2, w2), np.float32)
    def P(x, y): return (int((cx + x * sc) / 2), int((cy + y * sc) / 2))
    # 小臂 + 袖口（宽袍袖口外翻）
    cv2.fillPoly(m, [np.array([P(-120, -700), P(120, -700), P(95, -40), P(-95, -40)], np.int32)], 1.0, cv2.LINE_AA)
    cv2.fillPoly(m, [np.array([P(-260, -520), P(250, -540), P(170, -260), P(150, -170), P(-150, -170), P(-190, -260)], np.int32)], 1.0, cv2.LINE_AA)
    # 手掌（梯形 + 圆角）
    cv2.fillPoly(m, [np.array([P(-92, -60), P(92, -60), P(118, 120), P(-110, 125)], np.int32)], 1.0, cv2.LINE_AA)
    cv2.ellipse(m, P(4, 118), (int(114 * sc / 2), int(30 * sc / 2)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
    tips = []
    r = np.random.default_rng(seed)
    # 四指（三节，向下垂，带弯曲）+ 拇指
    for i, (x0, ln, ph) in enumerate(((-84, 1.0, 0.0), (-28, 1.12, 1.3), (30, 1.08, 2.1), (84, 0.86, 3.0))):
        curl = 0.25 + 0.12 * math.sin(t * 2.4 + ph) + 0.45 * tw * (1 if i % 2 else 0.6)
        ang = math.radians(90 + (x0 / 10) - 4)
        px, py = x0, 130
        segs = (70 * ln, 52 * ln, 40 * ln); wd = (30, 26, 22)
        for k, (L_, w_) in enumerate(zip(segs, wd)):
            a = ang + curl * (k + 1) * 0.55 * (1 if x0 < 0 else -1) * 0.6
            nx, ny = px + L_ * math.cos(a), py + L_ * math.sin(a)
            cv2.line(m, P(px, py), P(nx, ny), 1.0, max(1, int(w_ * sc / 2)), cv2.LINE_AA)
            cv2.circle(m, P(nx, ny), max(1, int(w_ * sc / 4)), 1.0, -1, cv2.LINE_AA)
            px, py = nx, ny
        tips.append((cx + px * sc, cy + py * sc))
    tc = 0.3 + 0.2 * math.sin(t * 1.9)
    px, py = -100, 40
    for k, (L_, w_) in enumerate(((70, 34), (55, 28))):
        a = math.radians(150 - 30 * tc * (k + 1))
        nx, ny = px + L_ * math.cos(a), py + L_ * math.sin(a)
        cv2.line(m, P(px, py), P(nx, ny), 1.0, max(1, int(w_ * sc / 2)), cv2.LINE_AA); px, py = nx, ny
    tips.append((cx + px * sc, cy + py * sc))
    return m, tips


_PCG = {}
def paper_cut_glyph(fr, ch, cx, cy, size, scale=1.0):
    """第十棒（critic_C_r5 P1②）：「纲」= 贴在皮影幕上的朱砂纸刻字：刀刻毛口（噪声蚀边）+ 刻刀深边 + 纸纤维，幕光从背后透过 → 暗红透色。"""
    k = (ch, size)
    if k not in _PCG:
        a = T.glyph(ch, 'serif_black', size, False)
        r = np.random.default_rng(77)
        n = cv2.GaussianBlur(r.random(a.shape).astype(np.float32), (0, 0), 1.6)
        n2 = cv2.resize(r.random((a.shape[0] // 10 + 2, a.shape[1] // 10 + 2)).astype(np.float32), a.shape[::-1], interpolation=cv2.INTER_CUBIC)
        a2 = np.clip((cv2.GaussianBlur(a, (0, 0), 2.2) - 0.5 + 0.55 * (n - 0.5) + 0.15 * (n2 - 0.5)) * 6 + 0.5, 0, 1)
        e = cv2.GaussianBlur(np.clip(a2 - cv2.erode(a2, np.ones((8, 8), np.uint8)), 0, 1), (0, 0), 0.8)
        fib = (0.70 + 0.55 * cv2.GaussianBlur(r.random(a.shape).astype(np.float32), (0, 0), 0.9)) * (0.72 + 0.5 * n2)   # 纤维 + 染色不匀（纸厚薄）
        _PCG[k] = (a2, e, fib)
    a2, e, fib = _PCG[k]
    if scale != 1.0:
        sz = (int(a2.shape[1] * scale), int(a2.shape[0] * scale))
        a2, e, fib = (cv2.resize(m, sz) for m in (a2, e, fib))
    h, w = a2.shape
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xs, ys = max(0, x0), max(0, y0); xe, ye = min(W, x0 + w), min(H, y0 + h)
    A_ = a2[ys - y0:ye - y0, xs - x0:xe - x0][..., None]; E_ = e[ys - y0:ye - y0, xs - x0:xe - x0][..., None]
    F_ = fib[ys - y0:ye - y0, xs - x0:xe - x0][..., None]
    sub = fr[ys:ye, xs:xe]
    paper = sub * np.array([0.95, 0.16, 0.07], np.float32) * 1.15 * F_          # 朱砂纸被幕光透过
    paper = paper * (1 - 0.85 * E_) + np.array([0.05, 0.015, 0.01], np.float32) * 0.85 * E_   # 刻刀深边
    fr[ys:ye, xs:xe] = sub * (1 - A_) + paper * A_
    return fr


class C03(Shot):
    """LS 皮影幕：一排纸人木偶被红线吊着，在「纲」字上同时被拽起；幕上是巨手的影子（纯代码手影，指节拽线时抽动）。"""
    def render(self, t):
        u = self.u(t)
        fr = candle_room(t, glow_c=(960, 420), amt=1.6) * 0.9
        # 皮影幕（暖光纸幕：纤维纹理 + 竹框阴影）
        yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32) * 4
        scr = np.exp(-(((xx - 980) / 1000) ** 2 + ((yy - 400) / 430) ** 2)) * (0.62 + 0.04 * math.sin(t * 19))
        fib = cv2.resize(K.tex('scrn', seed=33, base=40, octaves=3), (W // 4, H // 4))
        scr = scr * (0.85 + 0.3 * fib)
        # 第十棒（critic_C_r5 P1②）：人偶那一排背后加一盏幕后灯（暖白热区）→ 皮影是被背光透过的，不是正面受光的贴纸
        scr = scr + np.exp(-(((xx - 960) / 980) ** 2 + ((yy - 690) / 250) ** 2)) * 0.42 * (0.85 + 0.3 * fib)
        fr = fr + cv2.resize(scr.astype(np.float32), (W, H))[..., None] * np.array([1.0, 0.70, 0.40], np.float32)
        for xb in (150, 1770):
            fr[:, xb - 9:xb + 9] *= 0.35
        tj = V(120.96); tj2 = V(121.31)
        tw = min(1.0, pulse(t, tj, 0.18) + 0.7 * pulse(t, tj2, 0.15))
        # 手影：离幕远 → 软边（大模糊）+ 半影；轻微晃
        hx = 960 + 40 * math.sin(t * 0.9); hy = 150 - 60 * tw
        m, tips = hand_shadow_mask(hx, hy, 0.95, t, tw)
        # 十字提线板（木偶戏的操纵杆）被手攥着：横杆 + 竖杆，横杆随手倾斜
        bar_y = hy + 250; tilt = 0.06 * math.sin(t * 1.3) + 0.08 * tw * math.sin(t * 9)
        NP = 7                                                            # 第十二棒（critic_C_r6 P1②）：9 → 7 个，互不重叠（间距 ≥ 半个人偶宽）
        xs = [300 + i * 220 for i in range(NP)]
        ends = [(x, bar_y + (x - hx) * tilt) for x in xs]
        cv2.line(m, (int(ends[0][0] / 2 - 20), int(ends[0][1] / 2)), (int(ends[-1][0] / 2 + 20), int(ends[-1][1] / 2)), 1.0, 7, cv2.LINE_AA)
        cv2.line(m, (int(hx / 2), int((bar_y - 120) / 2)), (int(hx / 2), int((bar_y + 90) / 2)), 1.0, 8, cv2.LINE_AA)
        core = cv2.GaussianBlur(m, (0, 0), 2.5); pen = cv2.GaussianBlur(m, (0, 0), 12)
        sh = cv2.resize(core * 0.65 + pen * 0.35, (W, H))
        fr = fr * (1 - sh[..., None] * 0.86)
        r = np.random.default_rng(3)
        FLIP = (False, True, False, True, False, True, True)    # 第十棒：朝向交错（有的相对、有的背对），不再左半/右半一刀切
        for i in range(NP):
            # 第十棒（critic_C_r5 P1②）：每个人偶的身高、挂点偏移（提线斜拉）、摆动频率/相位/幅度、被拽起的延迟/幅度都错开
            dxo = r.uniform(-25, 25); hgt = r.uniform(300, 385); y0_ = r.uniform(520, 600)
            fq = r.uniform(1.5, 3.4); ph = r.uniform(0, 6.3); am = r.uniform(4, 12)
            dl = abs(i - 3) * 0.04 + r.uniform(0, 0.03); la = r.uniform(0.6, 1.35)
            x = min(1640, max(290, xs[i] + dxo))     # 不压竹框
            lift = la * (70 * pulse(t, tj + dl, 0.22) + 40 * pulse(t, tj2 + dl, 0.18))
            top = y0_ - lift + 9 * math.sin(t * fq * 1.2 + ph)
            ang = am * math.sin(t * fq + ph) + 12 * la * pulse(t, tj + dl, 0.3) * (1 if r.random() < 0.5 else -1)
            fr = red_line(fr, ends[i], (x, top + 4), w=2, amt=0.85)
            fr, hp = PY.draw_piying(fr, PY.piying_sprite(i, int(hgt)), x, top, ang, light=1.15 - 0.25 * abs(i - 3) / 3, flip=FLIP[i], glass=0.92, ghost=0.12 if R5 else 0.4)   # r5 返工 #36：双影减弱
            fr = red_line(fr, (ends[i][0] + (60 if not FLIP[i] else -60), ends[i][1] + 6), hp, w=1, amt=0.6)   # 手线（第二根提线）
        if t >= tj and not R5:                 # 第五轮 #36：C03 去掉「纲」（已挪到 C02 第七根红线上）
            fr = paper_cut_glyph(fr, '纲', 960, 330, 270, scale=1 + 0.12 * pulse(t, tj, 0.06))
        fr = fog(fr, t, 4, density=0.4, y0=750, y1=980, color=(0.25, 0.17, 0.10), speed=(30, 0))
        fr = sparks(fr, t, 31, (960, 600), n=40, life=3.0, speed=(8, 30), dirc=(0, -1), spread=1.4, grav=-6, amt=0.25, area=(800, 300))
        return fr


_GSEAL = {}
def gold_seal():
    if 'g' not in _GSEAL: _GSEAL['g'] = CP.StoneSeal('正', seed=404, res=192, front_text=None if R5 else '正', base=(0.62, 0.42, 0.13))   # 第五轮 #37/#43：印身正面不刻「正」（C04 / C40 共用）
    return _GSEAL['g']


def fill_people(n, seed, h, scatter=0.0, t=0.0, spill=False):
    """秤盘回调：盘里一堆纸人（scatter>0 时被抛起）"""
    def f(fr, c, rx, ry):
        r = np.random.default_rng(seed)
        for i in range(n):
            ox = r.uniform(-0.75, 0.75) * rx; oy = r.uniform(-0.5, 0.3) * ry
            hh = int(h * r.uniform(0.8, 1.15))
            k = scatter * r.uniform(0.6, 1.3)
            # 第十二棒（critic_C_r6 P2⑤）：不再抛成左上一团来源不明的彩色碎纸人 —— 秤盘被翘起时人偶只颠起一下、
            # 在盘里东倒西歪，站在盘沿外侧的几个从盘边滑落、掉出画框下方（来源一眼可见：就是这只盘）
            if not spill:   # C40：秤断，人偶被抛飞（原行为）
                x = c[0] + ox + r.uniform(-1, 1) * 260 * k; y = c[1] + oy - hh * 0.95 - (900 * k - 1100 * k * k * 0.6)
                ang = r.uniform(-12, 12) + r.uniform(-200, 200) * k
                fr = PY.draw_piying(fr, PY.piying_sprite(60 + i % 8, hh), x, y, ang, light=1.0, flip=bool(i % 2), base=(0.95, 0.72, 0.45))[0]
                continue
            rest = c[1] + oy - hh * 0.95
            x = c[0] + ox + (ox / max(1.0, rx)) * 140 * k
            y = rest - (170 * k - 420 * k * k)
            if abs(x - c[0]) < rx * 0.82: y = min(y, rest)            # 还在盘里：落回盘面
            ang = r.uniform(-12, 12) + r.uniform(-45, 45) * min(k, 0.6) + (ox / max(1.0, rx)) * 160 * max(0.0, k - 0.3)
            # 第八棒：秤盘里的人也换成 C03 同款皮影（暗房里无幕光透射 → 用暖光衬底提亮）
            fr = PY.draw_piying(fr, PY.piying_sprite(60 + i % 8, hh), x, y, ang, light=1.0, flip=bool(i % 2), base=(0.95, 0.72, 0.45))[0]
        return fr
    return f


def fill_seal(size, fall=1.0, flash=0.0):
    def f(fr, c, rx, ry):
        g = gold_seal()
        fr, _ = g.draw(fr, c[0], c[1] + ry * 0.35, size, fall=fall, yaw=-28, pitch=-14, rim=(1.0, 0.8, 0.45), rim_amt=1.2, flash=flash,
                       light=(0.6, 0.7, -0.4), shadow=0.3)
        return fr
    return f


class C04(Shot):
    """CU 青铜天平：金印「正」从画顶坠进右盘（121.72），右盘沉、左盘的纸人被翘起抛飞；烛光金边，浅景深。"""
    def __init__(self): self.B = CP.BronzeBalance(seed=5)
    def render(self, t):
        u = self.u(t)
        fr = candle_room(t, glow_c=(1500, 250), amt=1.2) * 0.7
        td = V(121.72)
        fall = sm(td - 0.30, td, t) if t < td else 1.0
        k = max(0.0, t - td)
        tilt = -9 * eout(k / 0.35) + 2.5 * math.sin(t * 7) * pulse(t, td, 0.4) if t > td else 1.5 * math.sin(t * 2)
        sc = clamp(k / 0.9)
        fl = pulse(t, td, 0.12)
        fr, info = self.B.draw(fr, t, 960, 250, 1360, tilt=tilt, rim=(1.0, 0.72, 0.42), rim_amt=0.9, light=(0.6, -0.8),
                               fill_l=fill_people(12, 41, 92, scatter=sc * 0.9, t=t, spill=True),
                               fill_r=fill_seal(150, 1.0, fl) if t >= td else None)
        if t < td:   # 坠落中的金印（拖影）
            pr = info['pan_r']
            g = gold_seal()
            y = lerp(-200, pr[1] + 18, ein(fall, 2))
            fr, _ = g.draw(fr, pr[0], y, 150, fall=1.0, yaw=-28 + 60 * (1 - fall), pitch=-14, rim=(1, 0.8, 0.45), rim_amt=1.2, mblur=False)
            fr = K.vol_light(fr, (pr[0], y - 60), 90, GOLD, 0.5)
        fr = sparks(fr, t, 21, info['pan_r'], n=80, life=0.7, speed=(150, 650), dirc=(0, -1), spread=1.0, grav=900, amt=1.0,
                    t0=td, burst=True, color=(1.0, 0.75, 0.35))
        fr = K.vol_light(fr, (1500, 250), 500, WARM, 0.12)
        # 前景虚焦烛焰（浅景深）
        fr = K.vol_light(fr, (180, 900), 150, (1.0, 0.6, 0.25), 0.55 + 0.05 * math.sin(t * 17))
        if not R5:
            fr = K.vol_light(fr, (960, 360), 120, GOLD, 0.6 * pulse(t, V(121.98), 0.12))   # 「正」金闪（第五轮：屏幕层「谁的正义」已去掉，金闪随之去掉）
        fr = dust(fr, t, 42, n=90, amt=0.35, drift=(8, -14), region=(0, BAR, W, H - BAR), color=(1.0, 0.8, 0.5))
        return fr


class C05(Shot):
    """ECU 暗箱：黑漆描金方箱张着口（俯 26°），金印、铜钱、纸人倾泻而入；镜头推向箱口（交易）。"""
    def __init__(self): self.box = CP.OrnateBox(seed=5)
    def render(self, t):
        u = self.u(t)
        fr = candle_room(t, glow_c=(960, 160), amt=1.0) * 0.6
        z = 1.0 + 0.25 * ein(u, 2)
        size = 980 * z
        # 桌面：深色木纹 + 烛光反射
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
        wood = cv2.resize(K.tex('wood', seed=55, base=3, octaves=4), (W, H))
        grain = 0.5 + 0.5 * np.sin(np.linspace(0, 90, W, dtype=np.float32)[None, :] + wood * 14)
        desk = np.array([0.06, 0.035, 0.02], np.float32) * (0.6 + 0.6 * grain[..., None]) * np.clip((yy - 0.62) * 4, 0, 1)[..., None]
        fr = fr * (1 - np.clip((yy - 0.62) * 4, 0, 1)[..., None]) + desk
        fr, uv = self.box.draw(fr, 960, 1020 + 120 * (z - 1), size, yaw=6 - 8 * u, pitch=-26, flash=0.0)
        rim_y = float(np.mean([uv[4][1], uv[5][1], uv[6][1], uv[7][1]]))   # 箱口平面
        front_y = float(max(uv[4][1], uv[5][1]))
        xl, xr = float(min(uv[4][0], uv[7][0])) + 60 * z, float(max(uv[5][0], uv[6][0])) - 60 * z
        # 箱内暖光往上溢
        fr = K.vol_light(fr, (960, rim_y), 260 * z, (1.0, 0.6, 0.25), 0.35)
        # 倾泻物：金币（翻转的椭圆金片，带高光）+ 纸人；落到箱口平面以下即消失（被吞）
        r = np.random.default_rng(13)
        for i in range(80):
            ph = r.random(); sp = r.uniform(0.7, 1.1)
            k = ((t * sp * 1.3 + ph) % 1.0)
            x = 960 + r.uniform(-0.8, 0.8) * (xr - xl) * 0.4 * (1 - k * 0.4)
            y = lerp(BAR - 40, front_y + 20, k ** 1.7)
            if y > rim_y + (front_y - rim_y) * 0.4 + r.uniform(-30, 30): continue
            if r.random() < 0.78:
                sz = int(r.uniform(9, 17) * z); ang = (t * 340 * sp + i * 40) % 180
                ry_ = max(1, int(sz * abs(math.cos(math.radians(ang)))))
                cv2.ellipse(fr, (int(x), int(y)), (sz, ry_), i * 23, 0, 360, tuple(float(v) for v in GOLD * 0.55), -1, cv2.LINE_AA)
                cv2.ellipse(fr, (int(x), int(y)), (sz, ry_), i * 23, 200, 320, tuple(float(v) for v in GOLD * 1.5), 2, cv2.LINE_AA)
                cv2.rectangle(fr, (int(x - sz * 0.2), int(y - ry_ * 0.2)), (int(x + sz * 0.2), int(y + ry_ * 0.2)), (0.02, 0.015, 0.01), -1)
            else:
                fr = PY.draw_piying(fr, PY.piying_sprite(40 + i % 6, int(70 * z)), x, y - 35 * z, (t * 220 + i * 50) % 360,
                                    light=0.9, base=(0.95, 0.72, 0.45))[0]   # 第八棒：皮影
        fr = sparks(fr, t, 51, (960, rim_y - 40), n=50, life=1.2, speed=(30, 120), dirc=(0, -1), spread=1.2, grav=-30, amt=0.5,
                    area=(400, 30), color=(1.0, 0.7, 0.3))
        return fr


class C06(Shot):
    """第六棒重做（critic_C_r3 P0①：金框偏左 + 残片短横线 + 游戏发光字 → 不可交付）。
    POV：我们就是被倒进暗箱的「货」——从箱子里面仰望打开的箱盖内壁（生图底板 C6/c06_lid：旧木板、黑漆描金边、铜合页），
    前景是虚焦的箱沿（底板下缘，烛光从箱里往上打）。构图正对称、居中：棺材式的封闭感，字落在盖板正中。
    「暗」（123.86）「箱」（124.22）逐字被烙进盖板木纹：先一圈焦黑烙痕扩开、字槽里炭火通红，随后冷却成焦黑、冒烟；
    124.30 起箱盖朝镜头压下来合上：盖板逼近、烛光被挤成箱沿一道金缝，只剩两个字的余烬在黑暗里暗红一闪，接 C07 金缝张开。
    无故障条、无发光 UI 字；不设 RGB 分离。"""
    def __init__(self):
        L = T.Layer()
        T.place(L, '暗', 770, 450, 290, (1, 1, 1), 'serif_black', texture=False)
        self.g1 = L.A.copy()
        L = T.Layer()
        T.place(L, '箱', 1150, 450, 290, (1, 1, 1), 'serif_black', texture=False)
        self.g2 = L.A.copy()
        if R5:                                   # 第五轮 #37：「暗箱」两个烙字去掉——只留箱盖、合盖动作与金缝
            self.g1 = np.zeros_like(self.g1); self.g2 = np.zeros_like(self.g2)
        r = np.random.default_rng(66)
        self.nz = cv2.GaussianBlur(r.random((H // 2, W // 2)).astype(np.float32), (0, 0), 1.5)
        self.nz = cv2.resize((self.nz - self.nz.min()) / (np.ptp(self.nz) + 1e-6), (W, H))
        f = cv2.GaussianBlur(r.random((H, W)).astype(np.float32), (0, 0), 2.2)
        self.nf = np.clip(((f - f.mean()) / (f.std() + 1e-6)) * 0.5 + 0.5, 0, 1)        # 细噪声：炭火断续
    def brand(self, fr, g, k, amt=1.0):
        """g = 字形 alpha；k = 烙下后的秒数。焦痕外晕 + 字芯炭化发黑 + 只在烧边和裂纹里留炭火（白→橙→暗红，0.25s 冷却）。"""
        if k <= -0.03: return fr
        e = eout(clamp((k + 0.03) / 0.10))
        sc = cv2.GaussianBlur(g, (0, 0), 9) * e                               # 焦痕外晕
        sc2 = np.clip(cv2.GaussianBlur(g, (0, 0), 2.0) * 1.5, 0, 1) * e        # 字槽（略毛的烧边）
        sc2 = np.clip(sc2 * (0.8 + 0.4 * self.nz), 0, 1)
        fr = fr * (1 - 0.6 * sc[..., None]) * (1 - 0.93 * sc2[..., None])      # 炭化：字芯发黑
        fr = fr + sc2[..., None] * self.nz[..., None] * np.array([0.05, 0.035, 0.025], np.float32)   # 炭面颗粒
        edge = np.clip(sc2 - cv2.erode(sc2, np.ones((7, 7), np.uint8)), 0, 1)
        crack = sc2 * np.clip((self.nz - 0.62) * 5, 0, 1)
        emb = np.clip(edge * np.clip((self.nf - 0.35) * 2.6, 0, 1) * (0.5 + self.nz) + crack, 0, 1)
        heat = math.exp(-max(0.0, k) / 0.25) * e
        col = np.array([1.0, 0.85, 0.55], np.float32) * heat ** 2 + np.array([1.0, 0.36, 0.08], np.float32) * heat + np.array([0.55, 0.07, 0.02], np.float32) * 0.35
        fr = fr + emb[..., None] * col * 1.5 * amt
        fr = fr + cv2.GaussianBlur(emb, (0, 0), 16)[..., None] * np.array([1.0, 0.4, 0.1], np.float32) * (0.6 * heat + 0.08) * amt
        return fr
    def render(self, t):
        u = self.u(t)
        t1, t2 = V(123.86), V(124.22)
        tc = t2 + 0.08                                     # 合盖开始
        cl = ein(clamp((t - tc) / 0.22), 2.2)              # 0 开 → 1 合
        flick = 0.92 + 0.08 * math.sin(t * 23) + 0.05 * math.sin(t * 41 + 1)
        base = plate_view('C6/c06_lid', 0.5, 0.47 - 0.02 * u, 1.0 + 0.04 * u)
        # 烛光从箱底往上打：下亮上暗的暖光梯度 + 闪烁
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        base = base * (0.75 + 0.45 * yy) * flick
        base = self.brand(base, self.g1, t - t1)
        base = self.brand(base, self.g2, t - t2)
        # 烙字白烟（冷却期往上飘）
        for g, ti, sd in ((self.g1, t1, 601), (self.g2, t2, 602)):
            if t > ti and not R5:
                cx = 770 if sd == 601 else 1150
                base = dust(base, t, sd, n=90, amt=0.55 * math.exp(-(t - ti) / 0.6), drift=(10, -90), region=(cx - 150, 320, cx + 150, 560),
                            size=(2, 6), color=(0.75, 0.7, 0.65))
        if cl <= 0:
            fr = base
        else:
            # 合盖：我们在箱里，盖板朝镜头压过来——盖板放大逼近（以字为中心）、光被挤掉，烛光只剩箱沿一道金缝；
            # 两个烙字在逼近的黑暗里被压得重新发红（暗红一闪），合上后余烬呼吸、细烟
            z = lerp(1.0, 2.1, cl)
            M = np.float32([[z, 0, 960 * (1 - z)], [0, z, 450 * (1 - z) + 60 * cl]])
            lid = cv2.warpAffine(base, M, (W, H), borderMode=cv2.BORDER_REFLECT)
            fr = lid * (1 - 0.72 * cl)
            gg = cv2.warpAffine(np.clip(self.g1 + self.g2, 0, 1), M, (W, H))
            edge = np.clip(gg - cv2.erode(gg, np.ones((9, 9), np.uint8)), 0, 1) * np.clip((cv2.warpAffine(self.nf, M, (W, H)) - 0.35) * 2.6, 0, 1) + gg * np.clip((cv2.warpAffine(self.nz, M, (W, H)) - 0.6) * 4, 0, 1)
            br = (0.6 * math.sin(math.pi * min(1.0, cl * 1.25)) + 0.9 * cl) * (0.8 + 0.2 * math.sin(t * 19))
            fr = fr + np.clip(edge, 0, 1)[..., None] * np.array([1.0, 0.25, 0.06], np.float32) * br
            fr = fr + cv2.GaussianBlur(np.clip(edge, 0, 1), (0, 0), 20)[..., None] * np.array([0.9, 0.2, 0.05], np.float32) * 0.5 * br
            # 箱沿金缝（盖板压到箱沿上方 → 一道金线）
            ys = lerp(980, 880, cl)
            seam = np.exp(-((np.arange(H, dtype=np.float32)[:, None] - ys) / (2 + 22 * (1 - cl))) ** 2)
            fr = fr + seam[..., None] * np.array([1.0, 0.68, 0.28], np.float32) * (0.4 + 0.9 * cl) * flick
            fr = dust(fr, t, 603, n=80, amt=0.5 * cl, drift=(6, -50), region=(500, 300, 1420, 700), size=(2, 7), color=(0.6, 0.55, 0.5))
        # 前景：箱沿虚焦的边（再压一层暗边，强化「在箱里」的框）
        fr = fr * (1 - 0.35 * np.clip((yy - 0.86) * 8, 0, 1))
        return fr


class C07(Shot):
    """MCU 雨夜：鬼屠在雨里抬起下颌，闪电从背后勾边——「我不低头」从这里起，字体从铅字换成他自己的重字。
    第五棒：换统一定妆脸（高马尾版，生图 C5/c07_chin，参考 C40b point_cam），镜内 3° 抬颌 + 推近，不再用方下颌披发的 S065。"""
    def render(self, t):
        u = self.u(t)
        tf = V(124.90)
        fl = bolt_env(t, tf) * 0.9 + 0.4 * bolt_env(t, V(125.46))
        fr = storm(t, 7, horizon=1200, flash=0.5 + fl, fc=(1500, 120), ox=30 * u, ground=False)
        fr = bolt(fr, t, tf, 71, (1650, 40), (1500, 700), inten=0.8, sky=0.3, width=2.5)
        fr = rain(fr, t, 70, inten=0.6, angle=14, layers=(0, 1), light=(1500, 300))
        lift = eio(clamp((t - tf + 0.1) / 0.5))
        fr, _ = put(fr, t, 'C5/c07_chin', 1240, 1000, 870, anchor='src', src=(0.5, 1.0), rot=2.5 - 4.0 * lift, rim=COLD, rim_amt=2.8,
                    rim_dir=(0.7, -0.7), flash=fl, expo=0.95, wind=6, tint=(0.92, 0.97, 1.06), breathe=0.0)
        fr = rain(fr, t, 72, inten=0.9, angle=14, layers=(2, 3), light=(1500, 300))
        return fr


class C08(Shot):
    """ECU 同轴跳切进眼睛：雨水顺睫毛，闪电在瞳孔里一亮（「命」126.14 推）。
    第五棒：换统一定妆脸的眼部大特写（生图 C5/c08_eyes），字放到头顶发区（不压脸），「命」亮朱红。"""
    def render(self, t):
        u = self.u(t)
        tf = V(126.14)
        fl = bolt_env(t, tf)
        fr = storm(t, 8, horizon=1200, flash=0.3 + fl * 0.7, ground=False)
        z = 1.0 + 0.05 * pulse(t, tf, 0.15) + 0.04 * u
        fr, _ = put(fr, t, 'C5/c08_eyes', 760, 640, 1500 * z, anchor='src', src=(0.5, 0.72), rim=COLD, rim_amt=1.2,
                    rim_dir=(0.6, -0.8), flash=fl * 0.6, expo=1.0, wind=2, breathe=0.0)
        for ex in (440, 1080):
            fr = K.vol_light(fr, (ex + 20, 640), 26, COLD, 1.8 * fl)          # 瞳中电光
        fr = rain(fr, t, 80, inten=1.0, angle=14, layers=(2, 3))
        return fr


class C09(Shot):
    """LS 仰拍：鬼屠单手上撩（新精灵 slash_strings），头顶数十根红线在每个「不」上被斩断回弹。"""
    def render(self, t):
        u = self.u(t)
        cuts = [V(126.32), V(127.00)]
        fl = bolt_env(t, cuts[0]) * 0.8 + bolt_env(t, cuts[1]) * 0.5
        fr = storm(t, 9, horizon=930, flash=0.4 + fl, fc=(700, 100), oy=-40 * u, refl=0.6)
        fr = bolt(fr, t, cuts[0], 91, (600, 30), (420, 760), inten=0.8)
        r = np.random.default_rng(5)
        for i in range(14):
            x = 200 + i * 118 + r.uniform(-30, 30)
            ci = 0 if x < 960 else 1
            tc = cuts[ci]
            y_end = 520 + r.uniform(-80, 140)
            if t < tc:
                fr = red_line(fr, (x + 30 * math.sin(i), BAR), (x + 6 * math.sin(t * 3 + i), y_end), w=1, amt=0.75)
            else:
                k = t - tc; rec = 300 * eout(k / 0.4) + 400 * k
                fr = red_line(fr, (x + 30 * math.sin(i), BAR), (x + 30 * math.sin(i * 2) * k, max(BAR + 2, y_end - 160 - rec)), w=1, amt=0.75)
                yb = y_end + 900 * k * k
                fr = red_line(fr, (x - 40 * k, y_end - 140 + 900 * k * k), (x - 80 * k, yb + 120), w=1, amt=0.6 * (1 - sm(0.3, 0.9, k)))
        fr, _ = put(fr, t, 'C/slash_strings', 980, 1015, 760, rim=COLD, rim_amt=2.4, rim_dir=(-0.5, -0.9), flash=fl, expo=0.95, wind=7)
        for tc, (a, b) in zip(cuts, (((520, 620), (1050, 260)), ((900, 280), (1500, 560)))):
            fr = blade_smear(fr, a, b, (t - tc) / 0.20, bend=0.22, width=80, seed=int(tc * 10), amt=1.2)   # 第五棒：弯月拖影替代「光剑」白棒
            fr = sparks(fr, t, int(tc * 10), b, n=50, life=0.6, speed=(200, 700), dirc=(0, 1), spread=1.4, grav=900, t0=tc, burst=True,
                        color=(1.0, 0.35, 0.2))
        fr = rain(fr, t, 90, inten=0.9, angle=-8)
        return fr


class C10(Shot):
    """第五棒重做（评审 P1：白横光条 + 红线吊方块 = 程序道具代码味）：生图底板 C5/c10_tablets——雨夜宫檐下真实的雕花檐梁，
    四块乌木竖匾用红绳吊着。「大局为上」逐字（逐拍）以泥金阴刻在四块匾上亮起；127.86 一道弯月刀光横扫，红绳齐断，
    四块木匾带着字翻滚坠入黑暗（匾是从底板抠出的实物，背后是修补好的雨夜天）。"""
    Q = [[(368, 200), (440, 200), (428, 548), (352, 548)], [(528, 200), (602, 200), (602, 552), (528, 552)],
         [(696, 215), (780, 215), (784, 556), (708, 556)], [(864, 222), (948, 222), (962, 560), (890, 560)]]
    CORD = [408, 563, 722, 888]
    def __init__(self):
        # 第五轮 #38：「大局为上」不卡点——图生图把泥金字直接做进四块匾（R5_C/c10_tablets_gl，构图与 C5 底板逐像素对齐），开场就在
        PN = 'R5_C/c10_tablets_gl' if R5 else 'C5/c10_tablets'
        P = plate_view(PN, 0.5, 0.5, 1.0)
        pw = plate(PN).shape[1]; ph = plate(PN).shape[0]
        self.mp = lambda x, y: (W / 2 + (x / 1280 - 0.5) * pw, H / 2 + (y / 720 - 0.5) * ph)
        self.P = P
        hole = np.zeros((H, W), np.uint8); self.tabs = []
        for i, q in enumerate(self.Q):
            poly = np.array([self.mp(*p) for p in q], np.int32)
            m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [poly], 255)
            m = cv2.dilate(m, np.ones((7, 7), np.uint8))
            hole |= m
            x0, y0, w, h = cv2.boundingRect(poly); x0 -= 8; y0 -= 8; w += 16; h += 16
            A = (cv2.GaussianBlur(m, (0, 0), 1.2)[y0:y0 + h, x0:x0 + w].astype(np.float32) / 255)
            Cc = P[y0:y0 + h, x0:x0 + w].copy()
            # 泥金阴刻字（随匾一起运动）
            g = T.glyph('大局为上'[i], 'serif_black', int(w * 0.62), False).astype(np.float32)
            gh, gw = g.shape; cy = int(h * 0.36); cx = w // 2
            G = np.zeros((h, w), np.float32)
            ys, xs = max(0, cy - gh // 2), max(0, cx - gw // 2)
            G[ys:ys + gh, xs:xs + gw] = g[:min(gh, h - ys), :min(gw, w - xs)]
            self.tabs.append(dict(A=A, C=Cc, G=G, x0=x0, y0=y0, w=w, h=h, cx=x0 + w / 2, cy=y0 + h / 2))
        for x in self.CORD:
            a_ = self.mp(x, 90); b_ = self.mp(x, 215)
            cv2.line(hole, (int(a_[0]), int(a_[1])), (int(b_[0]), int(b_[1])), 255, 16)
        small = cv2.resize((np.clip(P, 0, 1) * 255).astype(np.uint8), (W // 2, H // 2))
        hs = cv2.resize(hole, (W // 2, H // 2))
        bg = cv2.inpaint(small, hs, 9, cv2.INPAINT_TELEA).astype(np.float32) / 255
        bg = cv2.GaussianBlur(bg, (0, 0), 2)
        hf = cv2.GaussianBlur(hole.astype(np.float32) / 255, (0, 0), 3)[..., None]
        self.bg = P * (1 - hf) + cv2.resize(bg, (W, H)) * hf
    def render(self, t):
        u = self.u(t)
        tc = V(127.86)
        fl = bolt_env(t, tc) * 0.7 + 0.35 * bolt_env(t, V(127.22))
        tins = [V(CT(30, k)) for k in (11, 12, 13, 14)]
        fr = (self.P if t < tc else self.bg) * (0.85 + 0.6 * fl)
        if t >= tc:
            k = t - tc
            for x in self.CORD:                      # 断绳残段回弹
                a_ = self.mp(x, 100); b_ = self.mp(x, 215 - 260 * min(1, k * 3))
                fr = red_line(fr, a_, (b_[0] + 20 * math.sin(k * 20 + x), max(a_[1] + 6, b_[1])), w=2, amt=0.7 * (1 - sm(0.3, 0.8, k)))
        for i, (tb, ti) in enumerate(zip(self.tabs, tins)):
            sw = 2.0 * math.sin(t * 2.2 + i)
            if t < tc:
                dy, ang = 0.0, sw
            else:
                k = t - tc
                dy = 1400 * k * k * (0.85 + 0.12 * i) + 60 * k; ang = sw + (50 + 25 * i) * k * (1 if i % 2 else -1)
            gl = 0.0 if R5 else sm(ti - 0.06, ti + 0.04, t)
            C = tb['C'].copy()
            gold = np.array([1.0, 0.76, 0.36], np.float32) * (0.75 + 0.9 * pulse(t, ti, 0.25) + 0.5 * fl)
            C = C * (1 - tb['G'][..., None] * gl) + tb['G'][..., None] * gl * gold
            Mx = cv2.getRotationMatrix2D((tb['w'] / 2, tb['h'] * 0.05), ang, 1.0)
            Mx[0, 2] += tb['x0']; Mx[1, 2] += tb['y0'] + dy
            Cw = cv2.warpAffine(C, Mx, (W, H)); Aw = cv2.warpAffine(tb['A'], Mx, (W, H))[..., None]
            fr = fr * (1 - Aw) + Cw * Aw
            if gl > 0:
                fr = K.vol_light(fr, (tb['cx'], tb['y0'] + tb['h'] * 0.36 + dy), 90, (1.0, 0.7, 0.3), 0.5 * pulse(t, ti, 0.3) * (t < tc + 0.3))
        fr = blade_smear(fr, (180, 300), (1760, 330), (t - tc) / 0.22, bend=0.10, width=60, seed=10, amt=1.4)
        fr = sparks(fr, t, 101, (960, 315), n=90, life=0.5, speed=(200, 800), dirc=(1, -0.2), spread=1.2, grav=900, t0=tc, burst=True,
                    color=(1.0, 0.8, 0.5), area=(700, 10)) if t >= tc else fr
        fr = rain(fr, t, 100, inten=0.9, angle=8)
        return fr


class C11(Shot):
    """CU 横刀：刀身烧得通红（生图 blade_hot），雨点打上去瞬间化作白汽；镜头沿刀身横移。"""
    def render(self, t):
        u = self.u(t)
        fr = storm(t, 11, horizon=1300, flash=0.25, ground=False) * 0.8
        x = lerp(1060, 860, eio(u))
        fr, A = put(fr, t, 'C/blade_hot', x, 560, 2100, anchor='src', src=(0.5, 0.5), rim=COLD, rim_amt=1.2, expo=1.05, sat=1.0,
                    tint=(1.04, 0.98, 0.95), gamma=1.0, wind=0, breathe=0.0)
        heat = 0.8 + 0.2 * math.sin(t * 7)
        fr = K.vol_light(fr, (x + 200, 560), 700, (1.0, 0.35, 0.12), 0.18 * heat)
        fr = fog(fr, t, 12, density=0.7, y0=330, y1=560, color=(0.75, 0.75, 0.78), speed=(-60, -90), scale=0.6)
        fr = sparks(fr, t, 111, (x + 300, 560), n=80, life=0.9, speed=(40, 220), dirc=(0, -1), spread=0.8, grav=-60, amt=0.8, area=(700, 10))
        fr = rain(fr, t, 110, inten=0.7, angle=6, layers=(1, 2, 3))
        return fr


class C12(Shot):
    """ECU 刃口：通红的刃口占满画面，白汽翻滚、铁屑火星剥落（同一张生图换成刃口大特写）。"""
    def render(self, t):
        u = self.u(t)
        fr = np.zeros((H, W, 3), np.float32) + 0.015
        fr, A = put(fr, t, 'C/blade_hot', 1100 - 120 * u, 600, 2100 * 2.8, anchor='src', src=(0.66, 0.5), rot=-6, rim=COLD, rim_amt=0.8,
                    expo=1.1, sat=1.1, gamma=0.95, tint=(1.06, 0.97, 0.93), wind=0, breathe=0.0)
        fr = fr + cv2.GaussianBlur(fr * A[..., None], (0, 0), 30) * np.array([1.0, 0.35, 0.12], np.float32) * 0.6
        fr = fx2.heat_haze(fr, t, amt=5.0)
        fr = fog(fr, t, 13, density=0.85, y0=200, y1=700, color=(0.8, 0.8, 0.82), speed=(-120, -160), scale=0.5)
        fr = sparks(fr, t, 121, (900, 640), n=140, life=0.8, speed=(80, 420), dirc=(0.3, -1), spread=0.7, grav=-100, amt=1.2, area=(800, 20))
        return fr


_C13G = {}
def _spiral_layer(rr, th, t, key, seed, twist, omega, flow, z, arms, base=4, rep=4):
    """对数螺旋采样一层体积云：θ' = θ + twist·ln r − ω t（内快外慢），径向坐标 ln r 向内流（被吸进眼里）。返回 (密度, 亮边)。"""
    n = K.tex(key, seed=seed, base=base, octaves=5)
    lr = np.log(np.maximum(rr / z, 1.0))
    thp = th + twist * lr - omega * t * (1.0 + 2.2 / (1 + lr * 0.4))
    u = (thp / (2 * np.pi)) * 512 * rep
    v = (lr * 16 + flow * t * 0.25) % 512                         # 沿旋臂方向慢变 → 纹理被拉成顺着螺旋的长条
    d = cv2.remap(n, (u % 512).astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    # 第十一棒：旋臂边缘被细噪声打碎（原来是一条硬边对数螺旋，读成同心 CG 环线）
    n2 = K.tex(key + 'd', seed=seed + 7, base=18, octaves=4)
    d2 = cv2.remap(n2, ((u * 2.0) % 512).astype(np.float32), ((v * 3.0) % 512).astype(np.float32), cv2.INTER_LINEAR,
                   borderMode=cv2.BORDER_WRAP)
    band = 0.5 + 0.5 * np.cos(arms * thp + 2.4 * (d - 0.5) + 3.2 * (d2 - 0.5))   # 旋臂
    den = np.clip((d * 0.45 + d2 * 0.40 + band * 0.62 - 0.70) * 1.7, 0, 1)
    den = cv2.GaussianBlur(den, (0, 0), 1.1)
    edge = np.clip(den - cv2.GaussianBlur(den, (0, 0), 2.0), 0, 1) * 2.5
    return den, edge


class C13(Shot):
    """riser（第十棒重做，critic_C_r5 P1③）：镜头冲进雷暴之眼。
    三层体积云旋臂（远层冷灰慢转 / 中层主旋臂被电光照亮 / 近层暗色碎云快速掠过、虚焦）做纵深视差，各层推近速度不同；
    正中风眼黑而静，眼壁是陡峭云墙、内缘被刀上带来的赤热余烬烧成不规则红边（承接 C12）；
    雨线和碎云沿螺旋被吸进眼里（不再是平面径向速度线）；鼓点上闪电在云层里亮起并沿眼壁跑一段弧。"""
    def render(self, t):
        u = self.u(t)
        hits = [V(x) for x in (131.61, 131.96, 132.07)]
        fl = sum(0.6 * pulse(t, h, 0.07) for h in hits) + 0.25 * ein(u, 2)
        h4, w4 = H // 4, W // 4
        cx, cy, ell = 960, 520, 1.30
        if 'g' not in _C13G:
            yy, xx = np.mgrid[0:h4, 0:w4].astype(np.float32) * 4
            dx, dy = xx - cx, (yy - cy) * ell
            _C13G['g'] = (np.sqrt(dx * dx + dy * dy) + 1, np.arctan2(dy, dx))
        rr, th = _C13G['g']
        rot = 0.25 * ein(u, 2)                                   # 机位滚转（整体）
        th = th - rot
        R0 = 150 + 190 * ein(u, 2)
        # 远层：原雷暴云底（被漩涡扭转，推近少、虚一点 = 景深最远）
        sk = storm_sky(t * 3, 13, 2000, flash=0.35 + fl, flash_c=(960, 520), speed=(30, -40), cloud=1.6) * 0.95
        sk = cv2.resize(sk, (w4, h4), interpolation=cv2.INTER_AREA)
        tw = (1.4 + 2.2 * ein(u, 2)) * np.exp(-rr / 750)
        ddx, ddy = rr * np.cos(th + rot), rr * np.sin(th + rot)
        z0 = 1.0 + 0.18 * ein(u, 2)
        mx = ((cx + (ddx * np.cos(tw) - ddy * np.sin(tw)) / z0) / 4).astype(np.float32)
        my = ((cy + (ddx * np.sin(tw) + ddy * np.cos(tw)) / ell / z0) / 4).astype(np.float32)
        fr = cv2.remap(sk, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        fr = cv2.GaussianBlur(fr, (0, 0), 1.2)
        # 体积感：从眼壁方向来的光，用密度梯度 · 指向眼的方向做受光面
        ux_, uy_ = -np.cos(th + rot), -np.sin(th + rot)
        puff = cv2.resize(K.tex('c13p', seed=135, base=10, octaves=4), (w4, h4))
        # 中层：主旋臂（团块化：顺螺旋的长条 × 各向同性的云团噪声），被眼壁电光照亮、受光面朝眼
        d1, e1 = _spiral_layer(rr, th, t, 'c13b', 132, 0.85, 0.55, 30, 1.0 + 0.42 * ein(u, 2), 2, base=4)
        d1 = np.clip(d1 * (0.15 + 1.5 * puff ** 1.6), 0, 1)
        d1b = cv2.GaussianBlur(d1, (0, 0), 2.5); gy1, gx1 = np.gradient(d1b)
        face = np.clip(-(gx1 * ux_ + gy1 * uy_) * 9, 0, 1)            # 朝眼一侧（密度向外增加）受光
        near_eye = np.exp(-np.clip(rr - R0, 0, None) / 450)
        lit1 = (0.10 + 0.55 * face + 0.35 * near_eye) * (0.6 + 0.9 * fl * near_eye + 0.3)
        sh1 = cv2.GaussianBlur(d1, (0, 0), 4) * 0.6                 # 中层投在远层上的暗
        fr = fr * (1 - sh1[..., None] * 0.65)
        fr = fr * (1 - d1[..., None] * 0.8) + d1[..., None] * np.array([0.60, 0.66, 0.78], np.float32) * lit1[..., None] \
            + e1[..., None] * d1[..., None] * np.array([0.75, 0.82, 1.0], np.float32) * 0.15 * (0.4 + fl)
        # 第十二棒（critic_C_r6 P1①）：平面黑圆 → 有纵深的漩涡井。眼内用隧道映射（深度 = ln(Rm/r)）：
        # 井壁是三层旋臂（内层快 / 中层 / 外层慢），越往里越暗越红、越小越密，井底透出暗红余烬（承接 C12 赤热刃口）。
        Rm = R0 * 1.7
        dep = np.log(np.maximum(Rm / rr, 1e-3))                 # 0 = 井口，越往里越大
        inside = np.clip(dep / 0.35, 0, 1) ** 1.2
        well = np.zeros_like(fr)
        for li, (sd, tw_, om, flw, arms_, wcol) in enumerate((
                (141, 0.9, 0.45, 40, 2, (0.42, 0.46, 0.56)),      # 外层：慢、冷灰、受电光
                (142, 1.6, 1.10, 90, 3, (0.30, 0.20, 0.22)),      # 中层：暗、开始偏红
                (143, 2.6, 2.20, 170, 4, (0.32, 0.07, 0.03)))):   # 内层：快、余烬红
            n_ = K.tex('c13t%d' % li, seed=sd, base=6, octaves=5)
            ang = th + tw_ * dep - om * t * (1 + 0.6 * li)
            uu = ((ang / (2 * np.pi)) * 512 * (2 + li)) % 512
            vv = (dep * (70 + 40 * li) - flw * t) % 512              # 沿深度向里流（被吸进去）
            dn = cv2.remap(n_, uu.astype(np.float32), vv.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            band = 0.5 + 0.5 * np.cos(arms_ * ang + 3.0 * (dn - 0.5))
            dens = np.clip((dn * 0.6 + band * 0.7 - 0.55) * 2.0, 0, 1)
            zl, zh = ((0.0, 0.9), (0.5, 1.8), (1.1, 3.4))[li]
            wz = np.clip((dep - zl) / 0.25, 0, 1) * np.clip((zh - dep) / 0.35, 0, 1)
            shade = np.exp(-dep * 0.5) * (0.45 + 0.75 * dens) * (1 + 1.3 * fl * np.exp(-dep * 1.5))
            gy_, gx_ = np.gradient(cv2.GaussianBlur(dens, (0, 0), 1.5))
            rimw = np.clip(-(gx_ * np.cos(th + rot) + gy_ * np.sin(th + rot)) * 6, 0, 1)   # 朝井心一侧的受光边
            a_ = (dens * wz)[..., None]
            well = well * (1 - a_ * 0.85) + a_ * np.array(wcol, np.float32) * (shade * (0.7 + 0.8 * rimw))[..., None]
        core = np.exp(-(rr / (0.42 * R0)) ** 2)                   # 井底：暗红透光（不是纯黑）
        well = well + core[..., None] * np.array([0.42, 0.07, 0.02], np.float32) * (0.75 + 0.35 * math.sin(t * 9) + 0.6 * fl)
        deep = np.clip((dep - 0.2) / 2.0, 0, 1)
        well = well + (deep * (1 - core))[..., None] * np.array([0.05, 0.008, 0.004], np.float32)
        fr = fr * (1 - inside[..., None]) + well * inside[..., None]
        # 井口唇：云墙在井口卷边处被电光勾亮（软、不成圈）
        lip = np.exp(-((dep - 0.06) / 0.12) ** 2) * (0.5 + 0.5 * cv2.resize(puff, (w4, h4)))
        fr = fr + lip[..., None] * np.array([0.50, 0.55, 0.66], np.float32) * (0.10 + 0.35 * fl)
        # 近层：暗色碎云快速掠过（虚焦、只在外圈），带冷轮廓光 → 前景层
        d2, e2 = _spiral_layer(rr, th, t, 'c13c', 134, 1.2, 0.95, 60, 1.0 + 0.95 * ein(u, 2), 2, base=3, rep=2)
        d2 = cv2.GaussianBlur(d2 * (0.2 + 1.0 * puff[::-1, ::-1]) * np.clip((rr - R0 * 2.1) / 500, 0, 1), (0, 0), 2.2)
        e2 = cv2.GaussianBlur(e2, (0, 0), 1.5) * d2
        fr = fr * (1 - d2[..., None] * 0.88) + d2[..., None] * np.array([0.02, 0.022, 0.03], np.float32) \
            + e2[..., None] * COLD * 0.30 * (0.5 + fl)
        fr = fr * (0.55 + 0.45 * np.exp(-np.clip(rr - R0 * 1.5, 0, None) / 700))[..., None]   # 外圈压暗：亮在井口，纵深往外沉
        fr = cv2.resize(fr, (W, H), interpolation=cv2.INTER_LINEAR)
        fine = cv2.resize(K.tex('c13f', seed=136, base=28, octaves=3), (W, H))
        Mf = cv2.getRotationMatrix2D((cx, cy), -math.degrees(0.9 * t), 1.0 + 0.3 * u)
        fine = cv2.warpAffine(fine, Mf, (W, H), borderMode=cv2.BORDER_REFLECT)
        lum = np.clip(fr.mean(-1, keepdims=True) * 3, 0, 1)
        fr = fr * (1 + (fine[..., None] - 0.5) * 0.55 * lum)
        # 鼓点：闪电在井口云墙里沿螺旋跑一段弧
        for i, h in enumerate(hits):
            q = (t - h) / 0.12
            if 0 <= q < 1:
                fr = arc_streak(fr, (cx, cy), Rm * 1.05, Rm * 1.05 / ell, i * 110 + 20, i * 110 + 170, min(1, q * 2), width=3,
                                col=(0.85, 0.9, 1.0), amt=1.2)
        # 被吸入的雨线 + 碎云（取代速度线）：沿收紧的对数螺旋卷进井口，越近越细越淡，进井即消失
        r = np.random.default_rng(13)
        Ls = np.zeros((H // 2, W // 2), np.float32); Cl = np.zeros((H // 2, W // 2), np.float32)
        for i in range(70):
            a = r.uniform(0, 6.283); ph = r.random(); sp = r.uniform(0.8, 1.3)
            k = (t * sp * 1.3 + ph) % 1.0
            d0_ = Rm * 0.95 + 1300 * (1 - k) ** 1.5
            a0 = a + 2.4 * k * 6.283 * 0.35 - rot
            pts = []
            for m in range(12):                                   # 每条沿螺旋扫过 ~0.5rad，读成弧，不是直线
                aa = a0 - 0.045 * m; dd = d0_ * math.exp(0.03 * m)
                pts.append((int((cx + math.cos(aa) * dd) / 2), int((cy + math.sin(aa) * dd / ell) / 2)))
            fade = clamp((d0_ - Rm) / 300) * (0.25 + 0.45 * k)
            cv2.polylines(Ls, [np.array(pts[:7], np.int32)], False, float(fade * 1.6), 1, cv2.LINE_AA)
            cv2.polylines(Ls, [np.array(pts[6:], np.int32)], False, float(fade * 0.7), 1, cv2.LINE_AA)
        for i in range(26):                                       # 碎云团：被拉长、顺切向，近大远小
            a = r.uniform(0, 6.283); ph = r.random(); sp = r.uniform(0.5, 0.9)
            k = (t * sp + ph) % 1.0
            dd = Rm * 0.9 + 1100 * (1 - k) ** 1.3
            aa = a + 3.0 * k - rot
            px, py = (cx + math.cos(aa) * dd) / 2, (cy + math.sin(aa) * dd / ell) / 2
            sz = 6 + 34 * (dd / 1400)
            cv2.ellipse(Cl, (int(px), int(py)), (int(sz * 2.4), int(sz * 0.7)), math.degrees(aa) + 90, 0, 360,
                        float(clamp((dd - Rm) / 250) * 0.8), -1, cv2.LINE_AA)
        Cl = cv2.GaussianBlur(Cl, (0, 0), 6); Cl = Cl * (0.5 + cv2.resize(puff, (W // 2, H // 2)))
        Cl = cv2.resize(np.clip(Cl, 0, 1), (W, H))[..., None]
        fr = fr * (1 - Cl * 0.6) + Cl * np.array([0.34, 0.37, 0.44], np.float32) * (0.55 + 0.6 * fl)
        Ls = cv2.GaussianBlur(Ls, (0, 0), 0.7)
        fr = fr + cv2.resize(Ls, (W, H))[..., None] * COLD * (0.30 + 0.25 * u)
        fr = sparks(fr, t, 131, (cx, cy), n=60, life=1.0, speed=(40, 200), dirc=(0, -1), spread=3.1, grav=0, amt=0.6,
                    color=(1.0, 0.45, 0.15), area=(R0 * 1.6, R0 * 1.2))
        return fr


class C14(Shot):
    """过肩大仰拍：镜头贴在他后脑勺下方，头肩占画面下半，他仰头看头顶的风眼（C13 的同一个漩涡），
    132.45 一道落地闪电从风眼劈下。第五棒：换生图 C5/c14_ots（统一定妆脸的后脑+高马尾），逆光剪影处理：
    主体压暗、只留冷白轮廓光（评审 P0 发丝白毛边 → 抠图去灰边 + 毛边被轮廓光吃掉）。"""
    def render(self, t):
        u = self.u(t)
        tb = V(132.45)
        fl = bolt_env(t, tb) + 0.5 * bolt_env(t, V(132.87))
        fr = storm_sky(t * 2, 14, 2000, flash=0.45 + fl * 0.22, flash_c=(1100, 300), speed=(20, -30), cloud=1.3)   # 第十二棒（白闪同质化）：落雷不再把整片天冲白 → 只亮雷路与云底
        yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32) * 2
        dx, dy = xx - 1100, yy - 330; rr = np.sqrt(dx * dx + dy * dy) + 1
        tw = (2.2 + 0.6 * u) * np.exp(-rr / 650)
        ca_, sa_ = np.cos(tw), np.sin(tw)
        mx = (1100 + dx * ca_ - dy * sa_).astype(np.float32); my = (330 + dx * sa_ + dy * ca_).astype(np.float32)
        fr = cv2.remap(fr, cv2.resize(mx, (W, H)), cv2.resize(my, (W, H)), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        fr = K.vol_light(fr, (1100, 330), 200, (1.0, 0.4, 0.15), 0.35)          # 风眼余烬（承接 C13）
        fr = bolt(fr, t, tb, 141, (1100, 330), (1500, 1000), inten=1.6, width=5, sky=0.10)
        fr = rain(fr, t, 141, inten=0.8, angle=12, layers=(0, 1), light=(1100, 330))
        fr, _ = put(fr, t, 'C5/c14_ots', 720 + 25 * u, 1100, 760 * (1 + 0.03 * u), anchor='src', src=(0.53, 1.0), rim=(0.92, 0.95, 1.0),
                    rim_amt=3.6, rim_dir=(0.35, -1), flash=fl, expo=0.42, sat=0.4, wrap=0.5, wind=5, breathe=0.0)
        fr = sparks(fr, t, 142, (720, 420), n=40, life=0.8, speed=(120, 420), dirc=(-0.3, -1), spread=1.3, grav=900, amt=0.4 + 0.8 * fl,
                    color=(0.85, 0.9, 1.0), area=(200, 40))
        fr = rain(fr, t, 140, inten=1.0, angle=12, layers=(2, 3), light=(1100, 330))
        return fr


class C15(Shot):
    """ELS：鬼屠腾空（新精灵 leap_arc），133.22 电光炸开，速度坡度 1→0.1 定格在空中，雨滴悬停。"""
    def render(self, t):
        tb = V(133.38); tb2 = V(133.79)      # 第五棒：切点改到拍点 133.38，雷光与切点同帧
        k = t - self.t0
        ramp = 1 - 0.9 * sm(tb + 0.05, tb + 0.35, t)
        fl = bolt_env(t, tb) * 1.2 + bolt_env(t, tb2) * 0.9
        fr = storm(t, 15, horizon=930, flash=0.6 + fl, fc=(960, 200), refl=0.5)
        fr = bolt(fr, t, tb, 151, (1100, 60), (1300, 920), inten=1.3, width=4.5)
        fr = bolt(fr, t, tb2, 152, (700, 60), (520, 900), inten=1.0, width=3)
        # 起跳轨迹：前 0.4s 快速升起，之后近乎悬停
        # 第四棒：悬停点下移（原来头顶进了遮幅被裁），身高 420→480，顶点 ≥ 有效区上沿 +130px
        y = lerp(1120, 790, eout(k / 0.5, 3)) - 15 * (k - 0.5) * (k > 0.5)
        x = 760 + 260 * eout(k / 0.6, 2) + 20 * k
        # 第五棒（评审 P0：扁平黑剪影）：真实雷光照亮的生图精灵——冷白轮廓光 + 闪电补光 + 体积光，不再填黑
        fr = K.vol_light(fr, (x + 120, y - 330), 520, (0.85, 0.9, 1.0), 0.35 + 0.5 * fl)
        e1_, e2_ = bolt_env(t, tb), bolt_env(t, tb2)          # 第十一棒（critic_C_r5 P2⑥ 雷光未勾人）：哪道闪电亮，轮廓光就从哪一侧勾出整个人
        rdx = (0.75 * e1_ - 0.75 * e2_) / (e1_ + e2_ + 0.25) + 0.3 * 0.25 / (e1_ + e2_ + 0.25)
        fr, _ = put(fr, t, 'C/leap_arc', x, y, 480, rim=(0.9, 0.93, 1.0), rim_amt=3.4 + 3.2 * min(1.0, e1_ + e2_), rim_dir=(rdx, -1), flash=0.6 * fl, expo=0.8 + 0.5 * bolt_env(t, tb),
                    sat=0.55, mblur=(0, 12 * (1 - sm(0.05, 0.22, k))), wind=10 * ramp)
        fr = rain(fr, self.t0 + 0.45 + (t - self.t0 - 0.45) * (0.08 if k > 0.45 else 1), 150, inten=1.1, angle=10,
                  freeze=sm(0.35, 0.6, k) * 0.5)
        return fr


# =====================================================================================
# 副歌二「破」
class C16(Shot):
    """第五棒重做（评审 P1：立体红「血」+滴血 ≈ 副歌一 S038）：贴水面低机位——画顶垂下他刀尖（生图 C5/c16_drip），
    一滴血从刃尖坠进积水（134.50「血」= 落水帧），涟漪荡开，血在水里像墨一样晕开、被透视压扁成一个躺在水面上的「血」字；
    135.06「冷」第二滴落下，字被涟漪搅碎、散成血丝。字是水里的血，不是立在空中的立体字。"""
    def __init__(self):
        g = T.glyph('血', 'serif_black', 600, False).astype(np.float32)
        g = cv2.resize(g, (g.shape[1], int(g.shape[0] * 0.56)), interpolation=cv2.INTER_AREA)
        self.g = np.zeros((H, W), np.float32)
        gh, gw = g.shape; y0, x0 = 700 - gh // 2, 960 - gw // 2   # 第九棒 P2⑨：上移 35px；第十棒再上移 35px（下沿离遮幅 ≥ 110px，落点 770 仍在字内）
        self.g[y0:y0 + gh, x0:x0 + gw] = g
        r = np.random.default_rng(16)
        self.nz = cv2.resize(cv2.GaussianBlur(r.random((H // 8, W // 8)).astype(np.float32), (0, 0), 2), (W, H))
    def render(self, t):
        u = self.u(t)
        t1 = V(134.50); t2 = V(135.06)
        fl = bolt_env(t, t1) * 0.35
        fr = storm(t, 16, horizon=560, flash=0.35 + fl, refl=0.85, rip=0.6, fc=(960, 200))
        fr = fr * np.array([1.0, 0.9, 0.9], np.float32)
        bd = cv2.GaussianBlur(fr[480:660], (0, 0), sigmaX=6, sigmaY=22)          # 水天线：竖向柔化 + 雾，避免硬边
        wv = np.exp(-((np.arange(480, 660) - 562) / 40.0) ** 2)[:, None, None]
        fr[480:660] = fr[480:660] * (1 - wv) + (bd * 0.8 + 0.06) * wv
        # 刀尖（画顶垂下）与它在水里的倒影
        tip_y = 470
        fr, A = put(fr, t, 'C5/c16_drip', 960, tip_y, 470, anchor='src', src=(0.497, 0.92), rim=COLD, rim_amt=2.4, rim_dir=(0.3, -1),
                    flash=fl, expo=0.9, sat=0.9, tint=(1.0, 0.97, 1.0), wind=0, breathe=0.0)
        # 第二滴：在刃尖聚起 → 135.06 前坠落
        if t < t2:
            gr = sm(t1 + 0.1, t2 - 0.12, t)
            yd = tip_y + 6 + (0 if t < t2 - 0.12 else 1900 * (t - (t2 - 0.12)) ** 2)
            fr = K.vol_light(fr, (960, yd), 7 + 5 * gr, (0.55, 0.02, 0.02), 1.2 * gr) if gr > 0 else fr
        # 血在水里晕开成字
        k = t - t1
        grow = eout(clamp(k / 0.35), 2)
        yy = (np.arange(H)[:, None] - 770) / 0.56; xx = np.arange(W)[None, :] - 960
        rr = np.sqrt(xx * xx + yy * yy)
        reveal = np.clip((grow * 520 - rr) / 60 + (self.nz - 0.5) * 2, 0, 1)
        k2 = max(0.0, t - t2)
        sig = 1.5 + 10 * eout(clamp(k2 / 0.5))
        Gb = cv2.GaussianBlur(self.g, (0, 0), sig) * reveal * (1 - 0.45 * sm(0, 0.5, k2))
        Gb = np.clip(Gb * (1 + 0.6 * (self.nz - 0.5)), 0, 1)[..., None]
        fr = fr * (1 - 0.82 * Gb) + Gb * np.array([0.50, 0.02, 0.02], np.float32) * (0.7 + 0.5 * fl)
        fr = water_ripple(fr, (960, 770), k + 0.02, flat=0.45, speed=700, amp=4 + 6 * sm(0.15, 0.4, k), y_top=560)
        fr = water_ripple(fr, (960, 770), k2 + 0.01 if t >= t2 else -1, flat=0.45, speed=760, amp=14, y_top=560)
        fr = splash(fr, t, t1, (960, 770), 161, n=60, spread=160, up=420, col=(0.55, 0.05, 0.04), amt=0.8)
        fr = splash(fr, t, t2, (960, 770), 162, n=60, spread=180, up=460, col=(0.6, 0.06, 0.05), amt=0.8)
        tr = 134.0 + (t - 134.0) * 0.4
        fr = rain(fr, tr, 160, inten=0.9, angle=6, red=0.35 * sm(t1, t1 + 0.4, t))
        self.ca = 5 if 0 <= k2 < 0.1 else 0
        return fr


class C17(Shot):
    """MS 落地：鬼屠从天砸进积水单膝跪地（S071），135.71 冲击波水环扩散、水花弹起。"""
    def render(self, t):
        u = self.u(t)
        tl = V(135.71)
        fl = 0.5 * bolt_env(t, tl)
        fr = storm(t, 17, horizon=760, flash=0.45 + fl, refl=0.7, rip=1.2)
        fr = fog(fr, t, 17, density=0.4, y0=680, y1=940, color=(0.4, 0.42, 0.48), speed=(50, 0))
        y = 960 if t >= tl else lerp(200, 960, ein(sm(self.t0, tl, t), 2))
        fr = water_ripple(fr, (960, 975), t - tl, flat=0.16, speed=1500, amp=16, wl=60, y_top=760)   # 第五棒：真实积水涟漪替代白色椭圆波纹
        fr, _ = put(fr, t, 'S071/land_kneel', 960, y, 560, rim=COLD, rim_amt=2.2, flash=fl + 0.3 * pulse(t, tl, 0.2), expo=0.95,
                    mblur=(0, 40) if t < tl else (0, 0), wind=8)
        fr = splash(fr, t, tl, (960, 975), 171, n=220, spread=900, up=1100)
        fr = rain(fr, t, 170, inten=1.0, angle=10)
        self.ca = 5 if 0 <= t - tl < 0.1 else 0
        return fr


class C18(Shot):
    """LS 两翼冲锋（第四棒重做：去掉程序化 crowd 方阵，换生图甲士 soldiers3 拆出的 3 个精灵）：
    低机位，两翼重甲步兵分 5 排从雨幕里冲来（远排逆光剪影 + 雾，近排实色 + 冷轮廓光 + 前景虚化擦镜），
    中间留一条通道，鬼屠在通道里起身拔刀（S072）；136.64 闪电把盔缨与枪尖全部勾亮。"""
    SPR = ('C/sold_a', 'C/sold_b', 'C/sold_c')
    def __init__(self):
        r = np.random.default_rng(18)
        self.units = []
        for row, z in enumerate((6.0, 4.6, 3.5, 2.6, 1.9, 1.35)):
            for side in (-1, 1):
                n = 4 if row < 3 else 3 if row < 5 else 1
                for i in range(n):
                    xw = side * (0.55 + (i + (0.5 if row % 2 else 0)) * 0.62 + r.uniform(-0.08, 0.08))
                    self.units.append(dict(z=z + r.uniform(-0.1, 0.1), xw=xw, k=int(r.integers(3)), flip=bool(r.integers(2)) ^ (side > 0),
                                           ph=r.uniform(0, 6.28)))
        self.units.sort(key=lambda d: -d['z'])
    def _draw(self, fr, t, d, adv, fl):
        z = d['z'] - adv
        if z < 0.9: return fr
        hz = 560
        x = 960 + d['xw'] * 820 / z
        y = hz + 470 / z + 10 * abs(math.sin(t * 9 + d['ph'])) / z      # 跑动起伏
        h = 780 / z
        if x < -h or x > W + h: return fr
        far = min(1.0, max(0.0, (z - 2.0) / 3.5))
        near = z < 1.6
        fr, _ = put(fr, t, self.SPR[d['k']], x, y, h, flip=d['flip'], look='sil' if far > 0.5 else None, rim=COLD,
                    rim_amt=2.0 + 1.6 * fl, rim_dir=(0, -1), expo=0.7 * (1 - 0.45 * far), sat=0.55, flash=fl, wind=4,
                    defocus=(3.0 if near else 1.0 * far), alpha=1.0 - 0.35 * far, breathe=0.0)
        return fr
    def render(self, t):
        u = self.u(t)
        fl = 0.8 * bolt_env(t, V(136.64)) + 0.3 * pulse(t, V(136.95), 0.12)
        fr = storm(t, 18, horizon=560, flash=0.5 + fl, fc=(960, 140), refl=0.5)
        fr = bolt(fr, t, V(136.64), 181, (1250, 60), (1380, 520), inten=1.0)
        adv = 0.55 * u                                                   # 两翼逼近
        hero_z = 1.6
        for d in self.units:
            if d['z'] - adv >= hero_z: fr = self._draw(fr, t, d, adv, fl)
        fr = fog(fr, t, 18, density=0.55, y0=520, y1=860, color=(0.33, 0.36, 0.43), speed=(30, 0), light=(960, 300), light_r=700)
        fr, _ = put(fr, t, 'S072/rise_draw', 960, 1000 - 30 * eout(u), 640, rim=COLD, rim_amt=2.6, flash=fl, expo=0.95, wind=7)
        for d in self.units:
            if d['z'] - adv < hero_z: fr = self._draw(fr, t, d, adv, fl)
        fr = rain(fr, t, 180, inten=1.1, angle=12)
        return fr


# ---------------- 第三棒：枪林（C19）与旗海（C36）——不再用程序化甲士
def _rotp(pts, ang, c):
    ca, sa = math.cos(ang), math.sin(ang)
    d = pts - c
    return c + np.stack([d[:, 0] * ca - d[:, 1] * sa, d[:, 0] * sa + d[:, 1] * ca], 1)


def draw_spear(C, M, B, P, w=12, tip=1.0, light=(-0.6, -0.8), t=0.0, seed=0, head_off=(0.0, 0.0), head_rot=0.0, head=True, flash=0.0):
    """画一支红缨枪到图层 (C, M)（全分辨率 float32）：枪杆 B→P（木杆 + 冷色边光），P 处铁枪头（叶形、两面明暗 + 刃口亮线）+ 红缨。
    head_off/head_rot：枪头被斩下后的位移与旋转（像素 / 弧度）。"""
    B = np.asarray(B, float); P = np.asarray(P, float)
    d = P - B; L_ = np.linalg.norm(d) + 1e-6; d = d / L_; n = np.array([-d[1], d[0]])
    lt = np.asarray(light, float); lt /= np.linalg.norm(lt)
    side = 1.0 if np.dot(n, -lt) > 0 else -1.0
    # 杆：暗木 + 一侧边光
    q = np.array([B + n * w / 2, P + n * w * 0.35, P - n * w * 0.35, B - n * w / 2]).astype(np.int32)
    cv2.fillPoly(C, [q], (0.05, 0.035, 0.025), cv2.LINE_AA); cv2.fillPoly(M, [q], 1.0, cv2.LINE_AA)
    e0 = B + n * side * w * 0.38; e1 = P + n * side * w * 0.25
    cv2.line(C, tuple(e0.astype(int)), tuple(e1.astype(int)), tuple(float(v) for v in COLD * (0.16 + 0.35 * flash)), max(1, int(w * 0.12)), cv2.LINE_AA)
    if not head: return
    hc = P + d * 10 * tip + np.asarray(head_off, float)
    ang = math.atan2(d[1], d[0]) + head_rot
    dd = np.array([math.cos(ang), math.sin(ang)]); nn = np.array([-dd[1], dd[0]])
    ln, wd = 110 * tip, 30 * tip
    base = hc; mid = hc + dd * ln * 0.35; tipp = hc + dd * ln
    left = np.array([base + nn * wd * 0.25, mid + nn * wd * 0.5, tipp]).astype(np.int32)
    right = np.array([base - nn * wd * 0.25, mid - nn * wd * 0.5, tipp]).astype(np.int32)
    bright = (0.62 + 0.6 * flash, 0.66 + 0.6 * flash, 0.72 + 0.6 * flash); dark = (0.10, 0.11, 0.13)
    ls_ = np.dot(nn, -lt) > 0
    cv2.fillPoly(C, [np.vstack([left, [base]]).astype(np.int32)], bright if ls_ else dark, cv2.LINE_AA)
    cv2.fillPoly(C, [np.vstack([right, [base]]).astype(np.int32)], dark if ls_ else bright, cv2.LINE_AA)
    cv2.fillPoly(M, [np.vstack([left, right[::-1]]).astype(np.int32)], 1.0, cv2.LINE_AA)
    cv2.line(C, tuple(base.astype(int)), tuple(tipp.astype(int)), (0.9, 0.93, 1.0), 2, cv2.LINE_AA)        # 脊线高光
    # 枪头箍（铜）
    cv2.line(C, tuple((base - nn * wd * 0.35).astype(int)), tuple((base + nn * wd * 0.35).astype(int)), (0.45, 0.30, 0.12), max(2, int(8 * tip)), cv2.LINE_AA)
    # 红缨：从箍往后甩，随风 + 下垂
    r = np.random.default_rng(seed)
    for k in range(14):
        a0 = math.pi + ang + r.normal(0, 0.45) + 0.25 * math.sin(t * 9 + k + seed)
        l0 = r.uniform(40, 80) * tip
        p0 = base - dd * 4
        pm = p0 + np.array([math.cos(a0), math.sin(a0)]) * l0 * 0.5
        p1 = p0 + np.array([math.cos(a0), math.sin(a0) + 0.5]) * l0
        col = (0.50 + r.uniform(-0.1, 0.15), 0.03, 0.025)
        cv2.polylines(C, [np.array([p0, pm, p1], np.int32)], False, col, max(1, int(r.uniform(2, 4) * tip)), cv2.LINE_AA)
        cv2.polylines(M, [np.array([p0, pm, p1], np.int32)], False, 1.0, max(1, int(r.uniform(2, 4) * tip)), cv2.LINE_AA)


_BANNER = {}
def banner_tex(seed, w=60, h=220):
    k = (seed, w, h)
    if k not in _BANNER:
        r = np.random.default_rng(seed)
        A = np.ones((h, w), np.float32)
        # 破边：下缘燕尾 + 随机撕口
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        tail = h - 0.28 * h * (1 - np.abs(xx / w * 2 - 1))
        A[yy > tail] = 0
        for _ in range(4):
            cx, cy = r.uniform(0, w), r.uniform(h * 0.3, h); rr = r.uniform(3, 9)
            A[(xx - cx) ** 2 + (yy - cy) ** 2 < rr * rr] = 0
        fib = cv2.GaussianBlur(r.random((h, w)).astype(np.float32), (0, 0), 1.0)
        _BANNER[k] = (A, fib)
    return _BANNER[k]


class C19(Shot):
    """MS 低机位「谁人来」（第三棒重构，去掉白模甲士）：看不见人，只有四面八方刺进画面的红缨枪——枪尖收成一圈牢笼对准他，
    137.62「谁」137.92「人」逐拍再逼近一寸；137.92 他旋身一刀（S073 起势 → 旋斩），一圈枪头连红缨被齐齐斩落、向外飞散，火星沿切口迸出。"""
    N = 15
    def __init__(self):
        r = np.random.default_rng(19)
        self.sp = []
        for i in range(self.N):
            a = -math.pi * 0.98 + (i + r.uniform(-0.3, 0.3)) / (self.N - 1) * math.pi * 0.96 * 1.0
            a = a if i % 2 == 0 else a * 0.98 + math.pi * 0.02
            near = i % 4 == 0
            _d = r.uniform(0.75, 1.0)          # 第十一棒（critic_C_r5 P2⑥ 枪头等大）：拉开透视——远枪 0.45–0.9、近枪 1.6（虚焦）
            self.sp.append(dict(a=a, rad=r.uniform(400, 480), dep=1.6 if near else 0.45 + (_d - 0.75) / 0.25 * 0.45, near=near, seed=190 + i,
                                spin=r.uniform(-9, 9), fly=r.uniform(500, 900)))
    def render(self, t):
        u = self.u(t)
        ts = V(137.92); ti = [V(137.62), ts]
        fl = 0.6 * bolt_env(t, ts) + 0.4 * bolt_env(t, V(137.55))
        fr = storm(t, 19, horizon=980, flash=0.45 + fl, fc=(960, 160), ox=120 * u, refl=0.6)
        fr = fog(fr, t, 19, density=0.5, y0=650, y1=1000, color=(0.35, 0.38, 0.45), speed=(40, 0))
        c = np.array([960.0, 600.0])
        close = 1.0 - 0.08 * sum(eout((t - x) / 0.12) for x in ti if t >= x)
        k = max(0.0, t - ts)
        layers = {}
        for far in (True, False):
            C = np.zeros((H, W, 3), np.float32); M = np.zeros((H, W), np.float32)
            for j, sp in enumerate(self.sp):
                if sp['near'] == far: continue
                a = sp['a']; dirv = np.array([math.cos(a), math.sin(a)])
                P = c + dirv * sp['rad'] * close * max(0.85, sp['dep'])     # 第十一棒：位置圈不随远近缩（不压到人身上），只缩大小
                B = c + dirv * 2600
                cut = t >= ts + 0.012 * j
                kk = max(0.0, t - ts - 0.012 * j)
                if not cut:
                    draw_spear(C, M, B, P, w=16 * sp['dep'], tip=1.15 * sp['dep'], t=t, seed=sp['seed'], flash=fl)
                else:
                    Pc = P + dirv * 30
                    draw_spear(C, M, B + dirv * 220 * eout(kk / 0.3), Pc + dirv * 220 * eout(kk / 0.3), w=16 * sp['dep'], head=False, flash=fl)
                    off = dirv * sp['fly'] * kk + np.array([0, 1400 * kk * kk])
                    draw_spear(C, M, Pc - dirv * 40 + off, Pc + off, w=16 * sp['dep'], tip=1.15 * sp['dep'], t=t, seed=sp['seed'],
                               head_off=(0, 0), head_rot=sp['spin'] * kk, flash=fl)
            if not far:
                C = cv2.GaussianBlur(C, (0, 0), 9); M = cv2.GaussianBlur(M, (0, 0), 9)      # 近枪：焦外大虚
            else:                                                                      # 远枪：大气雾化 + 轻虚（纵深）
                C = cv2.GaussianBlur(C, (0, 0), 0.8) * 0.78 + np.array([0.30, 0.33, 0.40], np.float32) * 0.22
            layers[far] = (C, M)
        C, M = layers[True]
        fr = fr * (1 - M[..., None]) + C * M[..., None] * (1 - 0 * M[..., None])
        pose = 'S073/spin1' if t < ts else 'S073/spin2'
        fr, _ = put(fr, t, pose, 960, 1000, 700, rim=COLD, rim_amt=2.4, flash=fl, expo=0.95, rotblur=-9 * pulse(t, ts, 0.1), wind=9)
        fr = arc_streak(fr, (960, 600), 470, 150, 160, -200, (t - ts) / 0.4, width=7, amt=1.0)
        if t >= ts:
            for j, sp in enumerate(self.sp):      # 火星只在每个枪头切口迸出（不在他身上堆成白团）
                a = sp['a']; P = c + np.array([math.cos(a), math.sin(a)]) * sp['rad'] * close * max(0.85, sp['dep'])
                fr = sparks(fr, t, 193 + j, tuple(P), n=24, life=0.45, speed=(200, 700), dirc=(math.cos(a), math.sin(a)), spread=0.9,
                            grav=900, t0=ts + 0.012 * j, burst=True, color=(1.0, 0.7, 0.35), amt=1.0)
        C, M = layers[False]
        fr = fr * (1 - M[..., None]) + C * M[..., None]
        fr = rain(fr, t, 190, inten=1.0, angle=-14)
        self.ca = 5 if 0 <= k < 0.1 else 0
        return fr


class C20(Shot):
    """CU 太上皇：电光一亮他缓缓侧头（S074），身后雷云里一个金色巨字「定」被闪电照出来。"""
    def render(self, t):
        u = self.u(t)
        tb = V(138.42); td = V(138.56); tz = V(138.88)
        fl = bolt_env(t, tb) + 0.8 * bolt_env(t, tz)
        fr = storm(t, 20, horizon=1300, flash=0.3 + fl, fc=(600, 300), ground=False)
        a = sm(td - 0.06, td + 0.1, t) * (0.35 + 0.65 * min(1, fl + 0.3))
        if not R5:                               # 第五轮 #39/#42：去掉雷云里的金字「定」（连同它的金色体积光）
            fr = paste_glyph(fr, '定', 480, 430, 430, GOLD_T, alpha=a, glow=0.9, glow_c=(1.0, 0.6, 0.2), shadow=0, scale=1 + 0.06 * u)
        fr = bolt(fr, t, tb, 201, (300, 80), (500, 900), inten=0.9)
        fr, _ = put(fr, t, 'S074/head_turn', 1330, 1100, 1100, anchor='foot', rim=(0.9, 0.92, 1.0), rim_amt=3.0, rim_dir=(-0.9, -0.4),
                    flash=fl, expo=0.75, look=None, wind=6, sat=0.5)
        if not R5:
            fr = K.vol_light(fr, (480, 430), 260, GOLD, 0.5 * pulse(t, tz, 0.15))
        fr = rain(fr, t, 200, inten=0.8, angle=8)
        return fr


class C21(Shot):
    """对角分屏：左鬼屠（朱红边光）右太上皇（金边光），斜刀线隔开、两半反向滑；「正」在金侧、「邪」在红侧。"""
    def render(self, t):
        if R5: return self.render_r5(t)
        u = self.u(t)
        tx = V(139.48)
        A = storm(t, 211, horizon=1300, flash=0.3, ground=False) * np.array([1.1, 0.75, 0.72], np.float32)
        A, _ = put(A, t, 'S072/rise_draw', 640 - 60 * u, 1500, 1500, rim=RED * 1.3, rim_amt=3.2, rim_dir=(0.9, -0.4), expo=0.85, wind=7,
                   flash=0.6 * pulse(t, tx, 0.2))
        A = rain(A, t, 211, inten=0.7, angle=10, color=np.array([1.0, 0.5, 0.45], np.float32))
        B = storm(t, 212, horizon=1300, flash=0.3, ground=False) * np.array([1.08, 0.98, 0.82], np.float32)
        B, _ = put(B, t, 'S074/head_turn', 1560 + 50 * u, 1260, 1100, flip=True, rim=GOLD, rim_amt=3.0, rim_dir=(-0.9, -0.4), expo=0.7, wind=5)
        B = rain(B, t, 212, inten=0.7, angle=10, color=np.array([1.0, 0.85, 0.6], np.float32))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = (xx - 960) * 0.88 + (yy - 540) * 0.47              # 斜线（约 62°）
        m = np.clip(d / 2 + 0.5, 0, 1)[..., None]
        fr = A * (1 - m) + B * m
        line = np.exp(-(d / 3) ** 2) + 0.4 * np.exp(-(d / 30) ** 2)
        fr = fr + line[..., None] * np.array([1.0, 0.95, 0.9], np.float32) * (0.9 + 0.8 * pulse(t, tx, 0.2))
        # 第五棒（评审 P0）：「正」移到反派上方空区（不压脸），「邪」对称放左上，不压主角刀身
        fr = paste_glyph(fr, '正', 1330, 300, 230, GOLD_T, glow=0.7, glow_c=(1, 0.6, 0.2), alpha=sm(V(138.88) - 0.2, V(138.88), t) if t < self.t0 + 0.05 else 1.0)
        if t >= tx - 0.12:
            e = eout((t - (tx - 0.12)) / 0.12)
            fr = paste_glyph(fr, '邪', 330, 330, 230, RED_T, glow=0.9, glow_c=(0.9, 0.08, 0.04), scale=lerp(1.8, 1, e), alpha=min(1, e * 2))
        self.ca = 4 if 0 <= t - tx < 0.1 else 0
        return fr

    def render_r5(self, t):
        """第五轮 #40：两人各自完整入画（鬼屠左移下沉、头不顶黑边、肩不压分屏线；太上皇左移、手和脸不被右边裁），
        「邪」「正」不再卡点弹出——开场就在，用各半场的底色（暗血红 / 旧铜金）低调画进雷云里、压在人物身后，雨从字前面落过。"""
        u = self.u(t)
        tx = V(139.48)
        A = storm(t, 211, horizon=1300, flash=0.3, ground=False) * np.array([1.1, 0.75, 0.72], np.float32)
        A = paste_glyph(A, '邪', 300, 430, 330, (0.22, 0.035, 0.025), alpha=0.8, glow=0.2, glow_c=(0.30, 0.04, 0.02), shadow=0, blur=1.6)
        A, _ = put(A, t, 'S072/rise_draw', 385 - 25 * u, 1600, 1440, rim=RED * 0.8, rim_amt=1.1, rim_dir=(0.9, -0.4), expo=0.85, wind=7)   # r5 返工 #40：朱红描边减到 1/3（像抠图光边）；再左移 50，袖口离分屏线留缝
        A = rain(A, t, 211, inten=0.7, angle=10, color=np.array([1.0, 0.5, 0.45], np.float32))
        B = storm(t, 212, horizon=1300, flash=0.3, ground=False) * np.array([1.08, 0.98, 0.82], np.float32)
        B = paste_glyph(B, '正', 1272, 272, 160, (0.40, 0.32, 0.16), alpha=0.85, glow=0.2, glow_c=(0.40, 0.30, 0.14), shadow=0, blur=1.2)   # r5 返工 #40：挪到老者头顶左上的空处，整字可读
        B, _ = put(B, t, 'S074/head_turn', 1530 + 30 * u, 1260, 1100, flip=True, rim=GOLD, rim_amt=3.0, rim_dir=(-0.9, -0.4), expo=0.7, wind=6)
        B = rain(B, t, 212, inten=0.7, angle=10, color=np.array([1.0, 0.85, 0.6], np.float32))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = (xx - 1020) * 0.88 + (yy - 540) * 0.47         # r5 返工 #40：分屏线右移 60px，与袖口留缝
        m = np.clip(d / 2 + 0.5, 0, 1)[..., None]
        fr = A * (1 - m) + B * m
        line = np.exp(-(d / 3) ** 2) + 0.4 * np.exp(-(d / 30) ** 2)
        fr = fr + line[..., None] * np.array([1.0, 0.95, 0.9], np.float32) * (0.9 + 0.5 * pulse(t, tx, 0.2))
        return fr


class C22(Shot):
    """第五棒重做（评审 P1：扁平梯形字墙 = 代码味）：生图底板 C5/c22_wall——乌铁色城墙从积水直插雷云，极低机位仰拍、缓慢上摇；
    墙脚积水里一个小小的人（look_up_back 第 1 次，中景仰望）。「若规则是」逐字在墙心被闪电照出（冷白刻痕，「规」朱红）。"""
    def render(self, t):
        u = self.u(t)
        tb = V(141.32)
        fl = bolt_env(t, tb) + 0.7 * bolt_env(t, V(141.94))
        cy = lerp(0.60, 0.54, eio(u)) if R5 else lerp(0.56, 0.47, eio(u))   # 第五轮 #41：起幅压低、摇幅收小，人始终在画内
        fr = plate_view('C5/c22_wall', 0.5, cy, 1.0 + 0.04 * u) * (0.85 + 0.75 * fl)
        oy = (cy - 0.5) * plate('C5/c22_wall').shape[0]
        fr = bolt(fr, t, tb, 221, (1400, 40), (1250, 420), inten=0.9)
        for i in range(0 if R5 else 4):           # 第五轮 #39/#42：去「若规则是」
            ti = V(CT(34, i))
            if t < ti - 0.1: continue
            e = eout((t - ti + 0.1) / 0.18)
            fr = paste_glyph(fr, '若规则是'[i], 960, 250 + i * 128 - oy * 0.0, 104, (0.95, 0.97, 1.0) if i != 1 else RED_T,
                             glow=0.8, glow_c=(0.7, 0.8, 1.0) if i != 1 else (0.9, 0.1, 0.05), scale=lerp(1.5, 1, e), alpha=e, font='serif_b')
        if R5:   # 第五轮 #41：人钉在底板上（墙脚礁石 py=0.845），随底板一起被上摇带下去，不再跟着镜头飘起来
            z = 1.0 + 0.04 * u; ph = plate('C5/c22_wall').shape[0]
            px, py, ph_ = 930, 540 + (0.845 - cy) * ph * z, 200 * z
            px = 960 + (px - 960) * z
        else:
            px, py, ph_ = 960 + 10 * u, 905, 190
        if R5:   # r5 返工 #41：脚下礁石接触阴影 + 头部压暗（原 rim/flash 把头顶打成灰白一团，像白发）
            sh = np.zeros((H, W), np.float32)
            cv2.ellipse(sh, (int(px), int(py - 2)), (int(ph_ * 0.30), int(ph_ * 0.05)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
            sh = cv2.GaussianBlur(sh, (0, 0), ph_ * 0.03)
            sh2 = cv2.GaussianBlur(sh, (0, 0), ph_ * 0.10)
            fr = fr * (1 - (0.72 * sh + 0.35 * sh2)[..., None])
            fr, Af = put(fr, t, 'C/look_up_back', px, py, ph_, rim=COLD, rim_amt=1.2, rim_dir=(0.2, -1), flash=0.35 * fl, expo=0.55, wind=6)
            if Af is not None and getattr(Af, 'ndim', 0) == 2:
                yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32)
                hm = np.exp(-(((xx_ - px) / (ph_ * 0.16)) ** 2 + ((yy_ - (py - ph_ * 0.90)) / (ph_ * 0.13)) ** 2))
                fr = fr * (1 - (0.62 * hm * Af)[..., None])
        else:
            fr, _ = put(fr, t, 'C/look_up_back', px, py, ph_, rim=COLD, rim_amt=2.8, rim_dir=(0.2, -1), flash=fl, expo=0.7, wind=6)
        fr = fog(fr, t, 22, density=0.5, y0=780, y1=950, color=(0.4, 0.43, 0.5), speed=(40, 0))
        fr = rain(fr, t, 220, inten=1.0, angle=8)
        return fr


def _engrave_tool(fr, kind, cx, cy, s, amt=1.0, fl=0.0):
    """r5 返工 #42：铜牌上阴刻「规矩」的本义图形（不是字）：0 圆规（规）、1 曲尺（矩）、2 天平。刻槽压暗 + 右下倒角高光。"""
    P = {0: [[(0, -0.45), (-0.30, 0.42)], [(0, -0.45), (0.30, 0.42)],
             [(0.62 * math.cos(math.radians(a_)), -0.45 + 0.62 * math.sin(math.radians(a_))) for a_ in range(58, 123, 4)]],
         1: [[(-0.36, -0.46), (-0.36, 0.40), (0.42, 0.40)], [(-0.22, -0.46), (-0.22, 0.26), (0.42, 0.26)],
             [(-0.36, -0.46), (-0.22, -0.46)], [(0.42, 0.40), (0.42, 0.26)]]
            + [[(-0.36 + 0.13 * k, 0.40), (-0.36 + 0.13 * k, 0.34)] for k in range(1, 6)],
         2: [[(0, -0.46), (0, 0.40)], [(-0.20, 0.40), (0.20, 0.40)], [(-0.44, -0.30), (0.44, -0.30)],
             [(-0.44, -0.30), (-0.55, 0.06)], [(-0.44, -0.30), (-0.33, 0.06)], [(-0.58, 0.06), (-0.30, 0.06)],
             [(0.44, -0.30), (0.33, 0.06)], [(0.44, -0.30), (0.55, 0.06)], [(0.30, 0.06), (0.58, 0.06)]]}[kind]
    r = int(s * 0.75) + 8
    x0, y0 = int(cx) - r, int(cy) - r
    m = np.zeros((2 * r, 2 * r), np.float32)
    w = max(2, int(s * 0.045))
    for pl in P:
        pts = np.array([[(px * s + cx - x0), (py * s + cy - y0)] for px, py in pl], np.float32)
        cv2.polylines(m, [np.round(pts * 4).astype(np.int32)], False, 1.0, w, cv2.LINE_AA, shift=2)
    if kind == 0:
        cv2.circle(m, (int(cx - x0), int(cy - 0.45 * s - y0)), max(3, int(s * 0.06)), 1.0, -1, cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), 0.8)
    sh = max(1, int(w * 0.6))
    hi = np.clip(np.roll(np.roll(m, sh, 0), sh, 1) - m, 0, 1)
    ya, yb, xa, xb = max(0, y0), min(H, y0 + 2 * r), max(0, x0), min(W, x0 + 2 * r)
    if ya >= yb or xa >= xb: return fr
    mm = m[ya - y0:yb - y0, xa - x0:xb - x0][..., None]; hh = hi[ya - y0:yb - y0, xa - x0:xb - x0][..., None]
    reg = fr[ya:yb, xa:xb]
    reg = reg * (1 - 0.72 * amt * mm) + hh * amt * (0.10 + 0.25 * fl) * np.array([1.0, 0.82, 0.52], np.float32)
    fr[ya:yb, xa:xb] = reg
    return fr


class C23(Shot):
    """第五棒重做（评审 P1：半透明灰矩形贴片）：同一面城墙推近（C22 底板 2.3× 局部，match cut），三块实铸铜牌（生图 C5/c23_bronze）
    逐拍（铁 142.44 / 壁 142.76 / 铜 143.48）从墙里推出、逼近镜头，字阴刻在铜面上（刻槽积暗 + 倒角高光），推出时墙面碎石掉落、
    镜头横移；砖缝渗水。"""
    def render(self, t):
        u = self.u(t)
        ks = (4, 5, 6)
        fl = sum(0.6 * bolt_env(t, V(CT(34, k))) for k in ks)
        fr = plate_view('C5/c22_wall', lerp(0.46, 0.54, eio(u)), 0.62, 2.3 + 0.15 * u) * (0.9 + 0.7 * fl)
        pos = [(520, 450), (980, 640), (1420, 420)]
        for i, k in enumerate(ks):
            ti = V(CT(34, k))
            x, y = pos[i]; x -= 120 * u
            if t < ti - 0.15: continue
            e = eout((t - ti + 0.15) / 0.22)
            sz = 250 * (0.75 + 0.35 * e + 0.08 * (t - ti))
            hole = np.zeros((H // 2, W // 2), np.float32)
            cv2.rectangle(hole, (int((x - 120) / 2), int((y - 120) / 2)), (int((x + 120) / 2), int((y + 120) / 2)), 1.0, -1)
            fr = fr * (1 - cv2.resize(cv2.GaussianBlur(hole, (0, 0), 6), (W, H))[..., None] * 0.85 * e)
            dx, dy = (x - 960) * 0.08 * e, (y - 540) * 0.08 * e
            fr, _ = put(fr, t, 'C5/c23_bronze', x + dx, y + dy, sz, anchor='src', src=(0.5, 0.5), rim=COLD, rim_amt=1.4, rim_dir=(-0.6, -0.8),
                        flash=fl, expo=1.0, sat=0.8, tint=(1.0, 0.98, 0.95), wind=0, breathe=0.0)
            gs = sz * 0.55
            continue_glyph = not R5              # 第五轮 #39/#42：铜牌照推、字不刻
            if continue_glyph: fr = paste_glyph(fr, '铁壁铜'[i], x + dx + 2, y + dy + 3, gs, (0.85, 0.75, 0.55), glow=0.0, shadow=0.0, alpha=0.55)
            if continue_glyph: fr = paste_glyph(fr, '铁壁铜'[i], x + dx, y + dy, gs, (0.07, 0.06, 0.05), glow=0.25, glow_c=(0.6, 0.45, 0.2), shadow=0.3)
            if R5: fr = _engrave_tool(fr, i, x + dx, y + dy, gs, amt=e, fl=fl)   # r5 返工 #42：空白铜牌刻上规（圆规）/矩（曲尺）/天平图形
            fr = dust(fr, t, 230 + i, n=70, amt=0.8 * e * (1 - sm(0.2, 0.8, t - ti)), drift=(0, 220),
                      region=(int(x - 150), int(y - 40), int(x + 150), int(y + 280)), size=(1, 5))
        fr = rain(fr, t, 230, inten=0.7, angle=4)
        return fr


class C24(Shot):
    """MS 横移跟拍：鬼屠沿墙根疾奔（S078），刀尖在字墙上拖出一路火星长线；143.94「墙」低频震。"""
    def __init__(self): self.wall = PR.CharWall(seed=24, cols=26, rows=10, brick=(150, 64))
    def render(self, t):
        u = self.u(t)
        ox = 900 * u
        # 第五棒：墙换成 C22/C23 同一面生图城墙（横移跟拍墙根），不再用程序字砖墙
        fr = plate_view('C5/c22_wall', lerp(0.62, 0.40, u), 0.70, 2.0) * (0.75 + 0.6 * bolt_env(t, V(143.94)))
        x = 1250 - 80 * u; y = 990
        tip = (x + 370, y - 158)      # 第五棒：火星对准拖在身后的真实刀尖（原来在身前，刀尖与火星脱节）
        # 火星长线（墙面上灼痕：从刀尖拖向他跑来的右侧画外）
        G = np.zeros((H // 2, W // 2), np.float32)
        cv2.line(G, (int(tip[0] / 2), int(tip[1] / 2)), (W // 2, int((tip[1] - 30) / 2)), 1.0, 2, cv2.LINE_AA)
        Gs = cv2.resize(G + cv2.GaussianBlur(G, (0, 0), 6) * 2.5, (W, H))
        fr = fr + Gs[..., None] * np.array([1.0, 0.5, 0.18], np.float32) * 0.9
        fr = sparks(fr, t, 241, tip, n=160, life=0.5, speed=(300, 1100), dirc=(1, -0.4), spread=0.5, grav=1500, amt=1.4)
        # 第五棒（评审 P0「主角半透明」）：主体实体 alpha=1、无整体运动模糊；残影只在运动尾部 2 层 15%/8%；补地面接触阴影 + 火星照亮衣摆
        yb = y + 8 * abs(math.sin(t * 9))
        sh = np.zeros((H // 4, W // 4), np.float32)
        cv2.ellipse(sh, (int(x / 4), int((y + 4) / 4)), (60, 7), 0, 0, 360, 1.0, -1)
        fr = fr * (1 - 0.75 * cv2.resize(cv2.GaussianBlur(sh, (0, 0), 4), (W, H))[..., None])
        for gk, ga in ((2, 0.08), (1, 0.15)):
            fr, _ = put(fr, t - 0.03 * gk, 'S078/run', x + 55 * gk, yb, 640, rim=WARM, rim_amt=1.0, rim_dir=(-1, -0.3), expo=0.6, wind=10,
                        alpha=ga, mblur=(-14, 0))
        fr, _ = put(fr, t, 'S078/run', x, yb, 640, rim=WARM, rim_amt=2.6, rim_dir=(-1, -0.3), expo=1.05, wind=10, alpha=1.0, wrap=0.15)
        fr = K.vol_light(fr, (tip[0] - 160, tip[1] + 30), 260, (1.0, 0.55, 0.22), 0.35)      # 火星照亮衣摆
        fr = K.vol_light(fr, tip, 160, (1.0, 0.5, 0.2), 0.6)
        fr = rain(fr, t, 240, inten=0.9, angle=-6, cam=(ox, 0))
        return fr


_BLADE = {}
def blade_strip():
    """第六棒：从 blade_level 精灵里只裁刀身前段（第二只手之后 → 刀尖，x 0.73–0.995、刀身行带），转成竖直、刀尖朝上的 RGBA（float）。"""
    if 'b' not in _BLADE:
        im = cv2.imread(ROOT_DIR + '/assets/gen/C/blade_level_cut.png', cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0
        h, w = im.shape[:2]
        sub = im[618:752, int(w * 0.73):int(w * 0.995)].copy()
        sub[..., :3] = sub[..., :3][..., ::-1]                      # BGR → RGB
        _BLADE['b'] = np.rot90(sub, 1).copy()                       # 刀尖朝上
    return _BLADE['b']


class C25(Shot):
    """第六棒重做（critic_C_r3 P0③：墙前跃起劈墙 ≈ 副歌一 S035）：不再拍人。ECU 仰拍贴墙——镜头贴着那面生图城墙仰望（荷兰角），
    墙心阴刻一个巨大的「劈」（石刻：刻槽积暗、上沿冷光倒角）；145.14 一柄刀竖直从画底自下而上贯穿全画（只有刀身，速度拖影），
    沿画面中轴留下一道赤热的劈缝，「劈」连同整面墙被这条缝一分为二、向两侧错开，缝里灌出惨白电光、碎石落下。
    景别 ECU（S035 是全身 LS）、方向竖直向上（S035 斜向跃起）、主体是刀与墙（S035 是人）。下一镜 C26 从同一条缝炸开。"""
    def __init__(self):
        L = T.Layer(); T.place(L, '劈', 960, 540, 600, (1, 1, 1), 'serif_black', texture=False)
        self.g = L.A.copy()
        if R5: self.g = np.zeros_like(self.g)     # 第五轮 #39/#42：墙上不刻「劈」，只剩刀把整面墙劈开
    def render(self, t):
        u = self.u(t)
        ts = V(145.14)
        k = t - ts
        fl = 1.1 * pulse(t, ts, 0.14) + 0.5 * bolt_env(t, V(144.86))
        cy = lerp(0.60, 0.50, eio(u))
        base = plate_view('C5/c22_wall', 0.52, cy, 2.7 + 0.12 * u)
        base = cv2.warpAffine(base, cv2.getRotationMatrix2D((960, 540), -6 + 2 * u, 1.0), (W, H), borderMode=cv2.BORDER_REFLECT)
        base = base * (0.75 + 0.45 * fl)
        # 石刻「劈」：刻槽积暗 + 上左倒角冷光 + 下右暗边
        g = self.g
        hi = cv2.GaussianBlur(np.clip(g - np.roll(np.roll(g, 3, 0), 3, 1), 0, 1), (0, 0), 1.0)
        ins = cv2.GaussianBlur(np.clip(g - np.roll(np.roll(g, -9, 0), -9, 1), 0, 1), (0, 0), 3.0)      # 槽内上左壁的投影
        base = base * (1 - 0.72 * g[..., None]) * (1 - 0.6 * ins[..., None]) + hi[..., None] * COLD * (0.30 + 0.6 * fl)
        # 刀扫过之前：刀身在画底蓄势，刃口有冷光
        sp = clamp((k + 0.06) / 0.14)                            # 0..1 刀从画底扫到画顶
        gap = 0.0 if k < 0 else 80 * eout(clamp(k / 0.35)) + 20 * clamp((k - 0.35) / 0.3)
        sx = 960
        if gap > 0:
            # 墙（连同字）沿中轴劈开：左半左移、右半右移并微旋；缝里是惨白电光天
            xx = np.arange(W)[None, :]
            Lh = cv2.warpAffine(base, np.float32([[1, 0, -gap / 2], [0, 1, 6 * clamp(k / 0.3)]]), (W, H), borderMode=cv2.BORDER_REFLECT)
            Rh = cv2.warpAffine(base, cv2.getRotationMatrix2D((960, 1000), -1.2 * clamp(k / 0.3), 1.0) + np.float32([[0, 0, gap / 2], [0, 0, -4 * clamp(k / 0.3)]]),
                                (W, H), borderMode=cv2.BORDER_REFLECT)
            r = np.random.default_rng(25)
            ys = np.linspace(0, H, 28); jag = np.interp(np.arange(H), ys, r.normal(0, 7, 28)).astype(np.float32)[:, None]
            edgeL = sx - gap / 2 + jag; edgeR = sx + gap / 2 + jag
            mL = np.clip(edgeL - xx + 0.5, 0, 1)[..., None]; mR = np.clip(xx - edgeR + 0.5, 0, 1)[..., None]
            sky = storm(t, 25, horizon=1300, flash=1.6 + fl, fc=(960, 400), ground=False) + 0.22
            fr = Lh * mL + Rh * mR + sky * np.clip(1 - mL - mR, 0, 1)
            # 劈缝的热沿着「劈」的刻槽往两边灌：字槽被烧成朱红（关键字），离缝越远越晚、越暗
            gL = cv2.warpAffine(g, np.float32([[1, 0, -gap / 2], [0, 1, 6 * clamp(k / 0.3)]]), (W, H))
            gR = cv2.warpAffine(g, cv2.getRotationMatrix2D((960, 1000), -1.2 * clamp(k / 0.3), 1.0) + np.float32([[0, 0, gap / 2], [0, 0, -4 * clamp(k / 0.3)]]), (W, H))
            spread = np.exp(-np.abs(xx - sx).astype(np.float32) / (40 + 900 * eout(clamp(k / 0.3))))
            gg = (gL * mL[..., 0] + gR * mR[..., 0]) * spread
            gg = gg * (0.6 + 0.4 * cv2.resize(K.tex('c25m', seed=25, base=24), (W, H)))
            fr = fr * (1 - 0.6 * gg[..., None]) + gg[..., None] * (np.array([0.95, 0.16, 0.08], np.float32) * 0.95 + np.array([1.0, 0.6, 0.2], np.float32) * 0.8 * math.exp(-k / 0.2))
            fr = fr + cv2.GaussianBlur(gg, (0, 0), 14)[..., None] * np.array([0.9, 0.1, 0.04], np.float32) * 0.6
            # 断口：赤热→冷却的边
            hot = math.exp(-k / 0.28)
            for ex in (edgeL, edgeR):
                e = np.exp(-((xx - ex) / 5.0) ** 2)[..., None]
                fr = fr + e * (np.array([1.0, 0.5, 0.15], np.float32) * 1.6 * hot + COLD * 0.5 * (1 - hot))
            fr = K.vol_light(fr, (960, 520), 520, (0.9, 0.93, 1.0), 0.55 * (0.4 + 0.6 * math.exp(-k / 0.5)))
            fr = dust(fr, t, 251, n=180, amt=0.9 * math.exp(-k / 0.5), drift=(0, 300), region=(860, BAR, 1060, H - BAR), size=(2, 6))
        else:
            fr = base
        # 赤热劈缝：随刀尖从下往上烧出来（刀过之前不出现）
        if 0 < sp and gap <= 0:
            ytip = lerp(H + 200, -300, ein(sp, 1.3))
            G = np.zeros((H, W), np.float32); cv2.line(G, (sx, H), (sx, int(max(0, ytip + 300))), 1.0, 3, cv2.LINE_AA)
            fr = fr + (cv2.GaussianBlur(G, (0, 0), 10)[..., None] * 1.2 + G[..., None]) * np.array([1.0, 0.55, 0.2], np.float32)
        # 刀：竖直自下而上（只有刀身），速度拖影；刀过后从画顶飞出
        if -0.08 < k < 0.10:
            B = blade_strip(); bh = 1500
            Bs = cv2.resize(B, (110, bh), interpolation=cv2.INTER_AREA)
            ytip = lerp(H + 200, -300, ein(sp, 1.3)) - 40
            ky = int(9 + 140 * pulse(t, ts - 0.01, 0.06)) | 1
            Bs = cv2.GaussianBlur(Bs, (1, ky), 0)
            x0 = int(sx + 6 - Bs.shape[1] / 2); y0 = int(ytip)
            ys0, ys1 = max(0, y0), min(H, y0 + bh); xs0, xs1 = max(0, x0), min(W, x0 + Bs.shape[1])
            if ys1 > ys0 and xs1 > xs0:
                sub = Bs[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
                a = sub[..., 3:4]; c = sub[..., :3] ** 1.1 * (1.1 + 1.2 * fl) + np.array([0.15, 0.17, 0.22], np.float32) * a
                fr[ys0:ys1, xs0:xs1] = fr[ys0:ys1, xs0:xs1] * (1 - a) + c * a
            fr = sparks(fr, t, 252, (sx, max(BAR, ytip + 40)), n=120, life=0.5, speed=(300, 1100), dirc=(0, 1), spread=1.4, grav=1500, amt=1.3,
                        color=(1.0, 0.7, 0.3))
        if k > 0:
            fr = sparks(fr, t, 253, (960, 560), n=220, life=0.7, speed=(200, 1000), dirc=(0, 1), spread=2.6, grav=1100, t0=ts, burst=True,
                        area=(20, 520), color=(1.0, 0.75, 0.4))
        fr = fog(fr, t, 25, density=0.25, y0=700, y1=1000, color=(0.35, 0.38, 0.45), speed=(30, 0))
        fr = rain(fr, t, 250, inten=0.8, angle=-8)
        return fr


class C26(Shot):
    """第五棒重做（评审：程序字砖 + 黑方块碎屑）：崩塌——C22–C24 同一面生图城墙的局部，从劈痕中心炸开成上百块真实石片
    朝镜头飞来（慢放、翻转、越近越大），石片断面被缺口后惨白的电光天逆照勾边。"""
    def __init__(self):
        r = np.random.default_rng(26)
        S = 2; w, h = W // S, H // S
        pts = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
        # 第十一棒（critic_C_r5 P2⑤ 三角碎片低多边形感）：Delaunay 三角 → Voronoi 多边形石块（5–8 边、大小不一），
        # 中心密（碎）外圈疏（大块）；边再被噪声打成毛口
        for _ in range(170):
            a = r.uniform(0, 6.283); d = (r.random() ** 0.85) * 640
            pts.append((min(w - 1, max(0, w / 2 + math.cos(a) * d * 1.2)), min(h - 1, max(0, h / 2 + 20 + math.sin(a) * d * 0.75))))
        sd = cv2.Subdiv2D((-200, -200, w + 400, h + 400))
        for p_ in pts: sd.insert((float(p_[0]), float(p_[1])))
        facets, _ = sd.getVoronoiFacetList([])
        tris = []
        for q in facets:
            q = np.asarray(q, np.float32).reshape(-1, 2)
            q[:, 0] = np.clip(q[:, 0], 0, w - 1); q[:, 1] = np.clip(q[:, 1], 0, h - 1)
            if cv2.contourArea(q) < 30: continue
            c = q.mean(0); d = math.hypot(c[0] - w / 2, (c[1] - h / 2 - 20) / 0.75)
            tris.append((q, c, d, r.uniform(-1, 1), r.uniform(0.6, 1.3), r.uniform(0.72, 1.12), int(r.integers(0, h)), int(r.integers(0, w)),
                         (r.uniform(0.94, 1.06), 1.0, r.uniform(0.92, 1.05))))   # 第十二棒：每块自己的明暗 / 纹理偏移 / 微色偏
        self.tris = tris; self.S = S
        self.wall = cv2.resize(plate_view('C5/c22_wall', 0.5, 0.62, 2.0), (w, h))
        self.nz = cv2.GaussianBlur(r.random((h, w)).astype(np.float32), (0, 0), 2.5)
        self.nz = (self.nz - self.nz.mean()) / (self.nz.std() + 1e-6)          # 石片断口：噪声扰动边缘，不是干净三角
        n2 = K.tex('c26s', seed=262, base=24, octaves=4)
        self.nz2 = np.tile(cv2.resize(n2, (w // 2, w // 2)), (3, 3))                # 石面颗粒（按块错位采样，不是同一张平铺）
    def render(self, t):
        u = self.u(t)
        k = (t - self.t0) * 0.55 + 0.04                         # 慢放
        fl = 0.6 + 0.4 * math.sin(t * 13) ** 2
        S = self.S; w, h = W // S, H // S
        sky = storm(t, 26, horizon=1100, flash=0.9 + fl, fc=(960, 520), ground=False)
        sky = cv2.resize(sky, (w, h)) + 0.15
        out = sky.copy()
        for q, c, d, sp, sz, gn, oy_, ox_, tint in sorted(self.tris, key=lambda z: -z[2]):          # 先远（外圈，动得少）后近（中心，飞得最快）
            delay = d / 900.0 * 0.25
            e = max(0.0, k - delay)
            fly = e * max(0.0, 1.7 - d / 520.0) * sz
            sc = 1 + 1.6 * fly * fly
            dirv = np.array([c[0] - w / 2, c[1] - h / 2 - 20], np.float32); dirv /= (np.linalg.norm(dirv) + 1e-3)
            mv = dirv * (fly * 260 + fly * fly * 300)
            M = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), sp * 160 * fly, sc); M[:, 2] += mv
            m = np.zeros((h, w), np.float32); cv2.fillPoly(m, [q.astype(np.int32)], 1.0, cv2.LINE_AA)
            if fly > 0.002:
                x0_, y0_ = q.min(0).astype(int) - 4; x1_, y1_ = q.max(0).astype(int) + 5
                sl = (slice(max(0, y0_), min(h, y1_)), slice(max(0, x0_), min(w, x1_)))
                mb = cv2.GaussianBlur(m[sl], (0, 0), 2.0)
                m[sl] = np.clip((mb + 0.16 * self.nz[sl] - 0.5) * 6 + 0.5, 0, 1)
            x0, y0 = q.min(0).astype(int); x1, y1 = q.max(0).astype(int) + 2
            if fly <= 0.002:
                sub = (slice(max(0, y0), min(h, y1)), slice(max(0, x0), min(w, x1)))
                mm = m[sub][..., None]; out[sub] = out[sub] * (1 - mm) + self.wall[sub] * mm
                continue
            sl2 = (slice(max(0, y0 - 4), min(h, y1 + 4)), slice(max(0, x0 - 4), min(w, x1 + 4)))
            src = np.zeros_like(self.wall)
            hy_, hx_ = sl2[0].stop - sl2[0].start, sl2[1].stop - sl2[1].start
            gr = self.nz2[oy_ % 400:oy_ % 400 + hy_, ox_ % 400:ox_ % 400 + hx_]
            if gr.shape != (hy_, hx_): gr = cv2.resize(gr, (hx_, hy_))
            src[sl2] = self.wall[sl2] * m[sl2][..., None] * (gn * (0.82 + 0.36 * gr))[..., None] * np.array(tint, np.float32)
            Am = cv2.warpAffine(m, M, (w, h)); Pm = cv2.warpAffine(src, M, (w, h))
            # 第十二棒（critic_C_r6 P2④）：均匀亮描边 → 只在朝缺口电光（画面中心）那一侧的断口有细高光，背光侧压暗
            Ab = cv2.GaussianBlur(Am, (0, 0), 1.2); gy_, gx_ = np.gradient(Ab)
            cxp, cyp = M[0, 0] * c[0] + M[0, 1] * c[1] + M[0, 2], M[1, 0] * c[0] + M[1, 1] * c[1] + M[1, 2]
            lx, ly = w / 2 - cxp, h / 2 + 20 - cyp; ln = math.hypot(lx, ly) + 1e-3; lx, ly = lx / ln, ly / ln
            facing = np.clip(-(gx_ * lx + gy_ * ly) * 2.5, 0, 1)
            back = np.clip((gx_ * lx + gy_ * ly) * 2.5, 0, 1)
            edge = (facing * (Am > 0.3))[..., None]
            Pm = Pm * (1 - 0.6 * back[..., None])
            shade = 1.0 - 0.35 * min(1.0, fly)
            th = np.float32([[1, 0, -dirv[0] * 5 * min(1, fly * 3)], [0, 1, 6 * min(1, fly * 3)]])      # 厚度：暗侧面
            As = cv2.warpAffine(Am, th, (w, h))
            out = out * (1 - As[..., None] * 0.9) + As[..., None] * 0.03
            out = out * (1 - Am[..., None]) + Pm * shade + edge * np.array([0.8, 0.85, 1.0], np.float32) * 0.55 * fl   # 第十二棒：单侧断口高光
        fr = cv2.resize(out, (W, H))
        fr = dust(fr, t, 261, n=200, amt=0.6, drift=(0, 160), region=(0, BAR, W, H - BAR))
        fr = rain(fr, self.t0 + (t - self.t0) * 0.4, 260, inten=0.8, angle=6)
        return fr


class C27(Shot):
    """ELS 缺口：墙的两半剪影之间，天被闪电照得惨白如昼（伪天亮），缺口里站着一个小小的人；雨幕被缺口里的天光逆照。"""
    def render(self, t):
        u = self.u(t)
        tt = V(147.28)
        fl = 0.6 + 1.0 * bolt_env(t, tt) + 0.4 * pulse(t, V(146.5), 0.1)
        fr = storm(t, 27, horizon=900, flash=fl, fc=(960, 400), refl=0.9)
        fr = fr + sm(tt - 0.05, tt + 0.1, t) * 0.18 * (1 - sm(tt + 0.3, tt + 0.8, t))
        fr = K.vol_light(fr, (960, 500), 380, (0.85, 0.9, 1.0), 0.35 * fl)
        r = np.random.default_rng(27)
        ys = np.linspace(BAR - 20, 910, 30)
        lx = 820 + np.cumsum(r.normal(0, 14, 30)) - 40 * u; rx = 1100 + np.cumsum(r.normal(0, 14, 30)) + 40 * u
        m = np.zeros((H, W), np.float32)
        cv2.fillPoly(m, [np.array([[0, BAR - 20]] + [[int(a), int(b)] for a, b in zip(lx, ys)] + [[0, 910]], np.int32)], 1.0, cv2.LINE_AA)
        cv2.fillPoly(m, [np.array([[W, BAR - 20]] + [[int(a), int(b)] for a, b in zip(rx, ys)] + [[W, 910]], np.int32)], 1.0, cv2.LINE_AA)
        # 墙体剪影带砖缝（暗部仍有层次）
        bw = np.zeros((H, W), np.float32)
        for yb in range(BAR, 910, 46): bw[yb:yb + 3] = 1
        for j, yb in enumerate(range(BAR, 910, 46)):
            for xb in range((j % 2) * 55, W, 110): bw[yb:yb + 46, xb:xb + 3] = 1
        wallc = 0.025 + 0.02 * bw[..., None] * (-1) + 0.012 * cv2.resize(K.tex('c27w', seed=27, base=12), (W, H))[..., None]
        edge = cv2.GaussianBlur(m, (0, 0), 3) - cv2.GaussianBlur(m, (0, 0), 12)
        fr = fr * (1 - m[..., None]) + m[..., None] * np.clip(wallc, 0, 1) + np.clip(-edge, 0, 1)[..., None] * COLD * 0.8 * fl
        fr, _ = put(fr, t, 'S082/walk_front', 960, 910, 170, look='sil', rim=(1, 1, 1), rim_amt=3.0, wind=3, flash=fl)
        fr = rain(fr, t, 270, inten=1.0, angle=8, light=(960, 400))
        return fr


HX = 620


class C28(Shot):
    """字即光（第三棒重做，去白底字卡）：劈开的墙上留下一道「亮」字形的裂口，惨白的电光天从字形里灌进来，
    化成一束束体积光扫过画面；他背对镜头站在光里（look_up_back 第 2 次，C14 过肩大特写 → 这里中景逆光剪影），
    147.74 光最满；随后乌云从字形边缘涌回、光束暗下去——只是闪电的伪天亮。"""
    def __init__(self):
        a = T.glyph('亮', 'serif_black', 540, False).astype(np.float32)
        g = a.shape[0]
        r = np.random.default_rng(28)
        nz = cv2.resize(r.random((g // 10, g // 10)).astype(np.float32), (g, g))
        a = np.clip(cv2.dilate(a, np.ones((9, 9), np.uint8)) * (0.75 + 0.5 * nz) - 0.25, 0, 1) * 1.5
        if R5:   # 第五轮 #42：裂口不再是「亮」字形——改成一道不规则的竖向破口（低频起伏 + 小锯齿）
            g = 640
            yy, xx = (np.mgrid[0:g, 0:g].astype(np.float32) - g / 2)
            def _lf(sig, seed):
                q = cv2.GaussianBlur(np.random.default_rng(seed).random((g, g)).astype(np.float32), (0, 0), sig)
                return (q - q.mean()) / (q.std() + 1e-6)
            e = 1 - np.sqrt((xx / 150) ** 2 + ((yy + 10) / 270) ** 2) + 0.28 * _lf(22, 281) + 0.08 * _lf(5, 282)
            a = np.clip(e * 10, 0, 1)
        self.hole = np.zeros((H, W), np.float32)
        y0, x0 = 440 - g // 2, HX - g // 2
        self.hole[y0:y0 + g, x0:x0 + g] = np.clip(a, 0, 1)
        wall = 0.035 + 0.03 * cv2.resize(K.tex('c28w', seed=28, base=14, octaves=4), (W, H))
        bw = np.zeros((H, W), np.float32)
        for j, yb in enumerate(range(BAR, H - BAR, 64)):
            bw[yb:yb + 3] = 1
            for xb in range((j % 2) * 75, W, 150): bw[yb:yb + 64, xb:xb + 3] = 1
        self.wall = (wall * (1 - 0.6 * bw))[..., None] * np.array([0.9, 0.95, 1.0], np.float32)
        # 裂缝：从字形向四周开裂
        cr = np.zeros((H // 4, W // 4), np.float32)
        for i in range(9):
            a0 = i / 9 * 6.283 + 0.3
            p = crack_path((HX, 470), (HX + math.cos(a0) * 1100, 470 + math.sin(a0) * 650), 280 + i, n=22, jag=0.08)
            cr = np.maximum(cr, draw_crack(cr.shape, p / 4, 1, branches=2, seed=i, prog=1.0))
        self.crack = cv2.resize(cr, (W, H))
        h4 = cv2.resize(self.hole, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        self.g120 = cv2.resize(cv2.GaussianBlur(h4, (0, 0), 30), (W, H))[..., None]
        self.g200 = cv2.resize(cv2.GaussianBlur(h4, (0, 0), 50), (W, H))[..., None]
        if R5:   # r5 返工 #42：不再挖白色破口——光只沿闪电裂纹发出（细芯 + 两层晕），离裂心越远越弱
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            fall = np.exp(-(((xx - HX) / 950) ** 2 + ((yy - 470) / 620) ** 2))
            c4 = cv2.GaussianBlur(cr, (0, 0), 0.6)
            self.ck_core = (cv2.resize(c4, (W, H)) * (0.35 + 0.65 * fall)).astype(np.float32)
            self.ck_h1 = (cv2.resize(cv2.GaussianBlur(cr, (0, 0), 3), (W, H)) * fall * 3.0).astype(np.float32)
            self.ck_h2 = (cv2.resize(cv2.GaussianBlur(cr, (0, 0), 14), (W, H)) * fall * 9.0).astype(np.float32)
    def render(self, t):
        if R5: return self.render_r5(t)
        u = self.u(t)
        tl = V(147.74)
        lt = sm(self.t0, tl, t) * (1 - 0.75 * sm(tl + 0.25, self.t1, t))          # 光强：涨到「亮」→ 被乌云吞回
        hole = self.hole
        sky = storm_sky(t, 28, 2000, flash=0.9 + 0.8 * lt, cloud=0.8)
        sky = sky * 0.4 + np.array([0.95, 0.93, 0.88], np.float32) * (0.35 + 0.65 * lt)
        fr = self.wall * (1 + 2.5 * lt * self.g120)
        fr = fr + self.crack[..., None] * np.array([1.0, 0.9, 0.7], np.float32) * (0.25 + 0.9 * lt) * self.g200 * 8
        fr = fr * (1 - hole[..., None]) + sky * hole[..., None]
        # 体积光：字形光源向镜头放射（径向拖影）
        src = (hole[..., None] * sky).astype(np.float32)
        acc = np.zeros_like(src); n = 16
        for i in range(n):
            z = 1 + 0.9 * lt * (i + 1) / n
            acc += cv2.warpAffine(src, np.float32([[z, 0, HX * (1 - z)], [0, z, 470 * (1 - z)]]), (W, H)) * (1 - i / n)
        fr = fr + acc / n * 0.9 * lt * np.array([1.0, 0.92, 0.8], np.float32)
        fr = dust(fr, t, 281, n=160, amt=0.6 * lt, drift=(10, -20), region=(300, BAR, 1620, H - BAR), color=(1.0, 0.9, 0.7))
        # 第四棒：生图 face_lit 大特写——字形里灌出的光正好横过他的双眼（「亮」照在人脸上，而不是白底字卡）
        fr, _ = put(fr, t, 'C5/c28_face', 1400 - 20 * u, 560, 1000 * (1 + 0.04 * u), anchor='src', src=(0.53, 0.50),   # 第五棒：统一定妆脸
                    rim=(1.0, 0.85, 0.6),
                    rim_amt=2.0 + 2.5 * lt, rim_dir=(-1, -0.2), expo=0.55 + 0.6 * lt, sat=0.75, tint=(1.05, 0.98, 0.9), wind=4, breathe=0.004)
        fr = rain(fr, t, 280, inten=0.9, angle=6, light=(HX, 470))
        # 乌云从边缘涌回（墨色）
        fr = ink_vignette(fr, 0.55 * sm(tl + 0.2, self.t1, t))
        return fr

    def render_r5(self, t):
        """r5 返工 #42：①去掉不规则纯白破口：光沿闪电裂纹自然发出（裂纹芯冷白、晕暖金），「亮」那拍整屏短闪白 3 帧再收回；
        ②脸换 R5_C/c28_face_pt_v1（绿幕重抽，头顶、发带、高马尾完整入画），眼睛仍落在那道暖光带上。"""
        u = self.u(t)
        tl = V(147.74)
        lt = sm(self.t0, tl, t) * (1 - 0.75 * sm(tl + 0.25, self.t1, t))
        fl = pulse(t, tl, 0.10)                                          # 整屏短闪白（约 3 帧）
        sky = storm_sky(t, 28, 2000, flash=0.6 + 0.6 * lt, cloud=0.8)
        fr = self.wall * (1 + 1.6 * lt * np.clip(self.ck_h2, 0, 1)[..., None]) + sky * 0.10 * (0.5 + lt)
        glow = (self.ck_core * (0.8 + 2.6 * lt))[..., None] * np.array([0.92, 0.96, 1.0], np.float32) \
            + (self.ck_h1 * (0.15 + 0.55 * lt))[..., None] * np.array([1.0, 0.86, 0.6], np.float32) \
            + (self.ck_h2 * (0.04 + 0.16 * lt))[..., None] * np.array([1.0, 0.8, 0.5], np.float32)
        fr = fr + glow
        # 裂纹光向镜头放射（径向拖影，光源 = 裂纹本身）
        src = np.clip(glow, 0, 2).astype(np.float32)
        acc = np.zeros_like(src); n = 12
        for i in range(n):
            z = 1 + 0.6 * lt * (i + 1) / n
            acc += cv2.warpAffine(src, np.float32([[z, 0, HX * (1 - z)], [0, z, 470 * (1 - z)]]), (W, H)) * (1 - i / n)
        fr = fr + acc / n * 0.5 * lt
        fr = dust(fr, t, 281, n=160, amt=0.5 * lt, drift=(10, -20), region=(300, BAR, 1620, H - BAR), color=(1.0, 0.9, 0.7))
        fr, _ = put(fr, t, 'R5_C/c28_face_pt_v1', 1300 - 20 * u, 650, 900 * (1 + 0.03 * u), anchor='src', src=(0.448, 0.531),
                    rim=(1.0, 0.85, 0.6), rim_amt=1.4 + 1.6 * lt, rim_dir=(-1, -0.2), expo=0.5 + 0.45 * lt, sat=0.75,
                    tint=(1.05, 0.98, 0.9), wind=5, breathe=0.004, flash=0.6 * fl)
        fr = rain(fr, t, 280, inten=0.9, angle=6, light=(HX, 470))
        fr = fr * (1 + 1.4 * fl) + 0.42 * fl                                # 闪白：整屏一下提亮再收回（不是一块白斑）
        fr = ink_vignette(fr, 0.55 * sm(tl + 0.2, self.t1, t))
        return fr


class C29(Shot):
    """中近景迎面（第三棒重构，拆远景小人）：他从缺口里走向镜头，腰以上占满画面，镜头后退跟；两侧断墙是失焦的黑色前景，
    碎石擦着肩坠落，148.54 背后余电把轮廓勾亮。"""
    def render(self, t):
        u = self.u(t)
        tb = V(148.54)
        fl = bolt_env(t, tb)
        fr = storm(t, 29, horizon=1150, flash=0.45 + 0.9 * fl, fc=(960, 260), refl=0.6, ground=False)
        fr = K.vol_light(fr, (960, 380), 520, (0.85, 0.9, 1.0), 0.35 + 0.5 * fl)   # 缺口里的天光逆照
        fr = fog(fr, t, 29, density=0.45, y0=500, y1=1000, color=(0.35, 0.38, 0.45), speed=(30, 0))
        fr, _ = put(fr, t, 'S082/walk_front', 960, 330 + 10 * math.sin(t * 7.5), 1900 * (1 + 0.10 * eio(u)), anchor='src', src=(0.467, 0.094),
                    rim=COLD, rim_amt=3.0, rim_dir=(0, -1), expo=0.95, wind=7, flash=0.7 * fl, breathe=0.0)
        # 两侧断墙前景（失焦、带砖缝和冷边光）
        m = np.zeros((H // 4, W // 4), np.float32)
        r = np.random.default_rng(29)
        ys = np.linspace(0, H // 4, 16)
        lx = 60 + np.cumsum(r.normal(0, 4, 16)) - 40 * u; rx = W // 4 - 60 + np.cumsum(r.normal(0, 4, 16)) + 40 * u
        cv2.fillPoly(m, [np.array([[0, 0]] + [[int(a_), int(b_)] for a_, b_ in zip(lx, ys)] + [[0, H // 4]], np.int32)], 1.0)
        cv2.fillPoly(m, [np.array([[W // 4, 0]] + [[int(a_), int(b_)] for a_, b_ in zip(rx, ys)] + [[W // 4, H // 4]], np.int32)], 1.0)
        m = cv2.resize(cv2.GaussianBlur(m, (0, 0), 3), (W, H))
        wt = 0.03 + 0.03 * cv2.resize(K.tex('c29w', seed=29, base=10), (W, H))
        edge = np.clip(cv2.GaussianBlur(m, (0, 0), 5) - cv2.GaussianBlur(m, (0, 0), 25), 0, 1)
        fr = fr * (1 - m[..., None]) + m[..., None] * wt[..., None] + edge[..., None] * COLD * (0.3 + 0.8 * fl)
        # 坠落碎石（有体积：亮面 + 暗面）
        for i in range(7):
            x = r.choice([r.uniform(220, 640), r.uniform(1280, 1700)]); ph = r.random(); sz = r.uniform(18, 52)
            y = BAR - 60 + ((t * r.uniform(700, 1100) + ph * 900) % 1000)
            ang = (t * r.uniform(-300, 300)) % 360
            # 第五棒（评审：黑方块碎屑）→ 不规则碎石：随机多边形 + 城墙石纹采样 + 顶面冷光、底面暗
            nv = 7; aa = np.sort(r.uniform(0, 6.283, nv)) + math.radians(ang)
            rr_ = sz * r.uniform(0.55, 1.0, nv)
            poly = np.stack([x + np.cos(aa) * rr_, y + np.sin(aa) * rr_ * 0.8], 1).astype(np.int32)
            m_ = np.zeros((H, W), np.float32); cv2.fillPoly(m_, [poly], 1.0, cv2.LINE_AA)
            x0_, y0_ = max(0, int(x - sz - 2)), max(0, int(y - sz - 2)); x1_, y1_ = min(W, int(x + sz + 2)), min(H, int(y + sz + 2))
            if x1_ <= x0_ or y1_ <= y0_: continue
            tex = plate('C5/c22_wall')[200 + i * 37:200 + i * 37 + (y1_ - y0_), 300 + i * 53:300 + i * 53 + (x1_ - x0_)]
            if tex.shape[:2] != (y1_ - y0_, x1_ - x0_): continue
            sh_ = np.clip(1.2 - (np.arange(y0_, y1_)[:, None] - (y - sz)) / (2 * sz), 0.25, 1.2)[..., None]
            mm = m_[y0_:y1_, x0_:x1_, None]
            fr[y0_:y1_, x0_:x1_] = fr[y0_:y1_, x0_:x1_] * (1 - mm) + mm * (tex * 0.5 * sh_ + COLD * 0.25 * fl * sh_)
        fr = dust(fr, t, 291, n=140, amt=0.5, drift=(0, 120))
        fr = rain(fr, t, 290, inten=0.9, angle=6, light=(960, 300))
        return fr


class C30(Shot):
    """CU 腰带：暗红腰带在暴风里狂舞（S083，红绳母题）；「血」写成竖向长条朱红，像被风扯开的布。
    第七棒（critic_C_r3 P1⑥ 裁在嘴上）：精灵再上移 185px，上沿裁在颈下/领口——纯胸腹特写，不露半张脸。"""
    def render(self, t):
        u = self.u(t)
        fr = storm(t, 30, horizon=1300, flash=0.25 + 0.6 * bolt_env(t, V(149.70)), ground=False)
        fr, _ = put(fr, t, 'S083/sash', 900 - 80 * u, 515, 1500, anchor='src', src=(0.5, 0.62), rim=COLD, rim_amt=1.8, expo=1.0, sat=0.9,
                    wind=22, flash=0.4 * bolt_env(t, V(149.70)))
        fr = rain(fr, t, 300, inten=1.0, angle=20)
        self.ca = 3 if 0 <= t - V(149.70) < 0.1 else 0
        return fr


class C31(Shot):
    """MS 巨掌：天上一只巨手的阴影一掌拍下（150.77），鬼屠被震飞后撤（S084）。"""
    def render(self, t):
        u = self.u(t)
        ti = V(150.77)
        fr = storm(t, 31, horizon=860, flash=0.4 + 0.9 * pulse(t, ti, 0.15), refl=0.5)
        q = ein(sm(self.t0, ti, t), 2.5)
        hy = lerp(-700, 80, q) if t < ti else 80 + 20 * math.sin((t - ti) * 30) * math.exp(-(t - ti) * 6)
        fr, A = put(fr, t, 'S062/puppeteer', 1150, hy, 1400, anchor='src', src=(0.5, 0.0), look='shadow', alpha=0.9, wind=0, breathe=0)
        fr = fr * (1 - 0.35 * q)
        k = max(0.0, t - ti)
        x = 1120 - 360 * eout(k / 0.5)
        fr, _ = put(fr, t, 'S084/knock_back', x + 40, 1140, 1050, rim=COLD, rim_amt=2.3, expo=0.95, wind=10, mblur=(-60 * pulse(t, ti, 0.2), 0),
                    flash=0.8 * pulse(t, ti, 0.15))
        fr = dust(fr, t, 311, n=220, amt=0.9 * min(1, k * 5) * (1 - sm(0.4, 1.2, k)), drift=(-300, -60), region=(300, 700, W, 1000))
        fr = rain(fr, t, 310, inten=1.0, angle=10)
        self.ca = 6 if 0 <= k < 0.1 else 0
        return fr


class C32(Shot):
    """第五棒重做（评审 P1：「是非对错」石碑/印章 ≈ 副歌一 S040 印章）：「是非对错」不再是石印，而是刻在他四道刀光残影里的字。
    C32 = MS 低机位：他（slash_strings 第 2 次：翻转、更近、仰角更大）在雨里先虚晃一刀（152.05），152.40 回手十字双斩，
    两道弯月刀光交叉，「是」「非」随刀光同帧烧亮在残影里（字 = 刀光，不是砸下来的物体）。"""
    def render(self, t):
        u = self.u(t)
        t0_, tx = V(152.05), V(152.40)
        fl = 0.6 * bolt_env(t, tx)
        # 第八棒（critic_C_r4 P1② 与 C09 去同构）：C09 = LS 正面全身、侧前光、雨夜地面；
        # C32 改为 MCU 虫视仰拍逆光剪影——只取腰以上、人在左 1/3（C09 在中偏右）、荷兰角 +10°、刀臂向画右上斜举（与 C09 镜像）；
        # 闪电在他身后正上方（逆光），主体压暗成剪影只留冷白轮廓；不见地面，只有翻滚的雷云。
        fr = storm(t, 32, horizon=1400, flash=0.45 + fl, fc=(620, 260), refl=0.0, ground=False, oy=30 * u)
        fr = K.vol_light(fr, (640, 300), 760, COLD, 0.45 + 0.7 * fl)
        fr = bolt(fr, t, tx - 0.02, 327, (420, BAR), (760, 700), inten=0.7)
        fr, _ = put(fr, t, 'C/slash_strings', 560 - 30 * u, 1080, 2150, flip=True, anchor='src', src=(0.52, 0.46), rot=10 - 3 * u,
                    rim=(0.85, 0.92, 1.0), rim_amt=3.6, rim_dir=(-0.1, -1.0), flash=0.5 * fl, expo=0.42, gamma=1.25, wind=10,
                    rotblur=3.0 * pulse(t, tx, 0.12))
        fr = blade_smear(fr, (1860, 300), (1000, 700), (t - t0_) / 0.18, bend=0.18, width=60, seed=321, amt=0.9)   # 第八棒：虚晃一刀移到右半，不过脸
        A1 = ((360, 220), (1560, 880)); A2_ = ((1560, 220), (360, 880))
        fr = blade_smear(fr, *A1, (t - tx) / 0.14, bend=0.12, width=90, seed=322, amt=1.3)
        fr = blade_smear(fr, *A2_, (t - tx - 0.03) / 0.14, bend=-0.12, width=90, seed=323, amt=1.3)
        e = eout(clamp((t - tx + 0.02) / 0.10))
        fr = arc_glyph(fr, '是', (1180, 600), 230 * lerp(1.3, 1, e), e, rot=-8)   # 第八棒：人移左，字移到右半空区
        e2 = eout(clamp((t - tx - 0.01) / 0.10))
        fr = arc_glyph(fr, '非', (1590, 420), 230 * lerp(1.3, 1, e2), e2, rot=8)
        fr = rain(fr, t, 320, inten=1.0, angle=12)
        self.ca = 5 if 0 <= t - tx < 0.1 else 0
        return fr


class C33(Shot):
    """第五棒重做：CU 刀身横扫过画面（刃精灵 c16_drip 第 2 次，镜内旋转 = 刀在挥），每一挥留下一道刀光残影，「对」（152.70）、
    「错」（152.90）逐拍烧亮在残影里；背后「是」「非」的残影还没散（虚、暗），四个字同画。"""
    def render(self, t):
        u = self.u(t)
        td, tc = V(152.70), V(152.90)
        fl = 0.5 * bolt_env(t, td) + 0.5 * bolt_env(t, tc)
        fr = storm(t, 33, horizon=1300, flash=0.3 + fl, ground=False, fc=(500, 200)) * 0.85
        for ch, c in (('是', (1280, 250)), ('非', (1580, 250))):            # 第七棒：残影移到右上空区（原来压在刀后读不出），亮度 0.28 → 0.6
            fr = arc_glyph(fr, ch, c, 150, 0.6 * (1 - u * 0.4), rot=0)
        fr = blade_smear(fr, (200, 760), (1720, 300), (t - td) / 0.12, bend=-0.10, width=80, seed=331, amt=1.2)
        fr = blade_smear(fr, (1720, 760), (200, 320), (t - tc) / 0.10, bend=0.10, width=80, seed=332, amt=1.2)
        ang = lerp(-14, 12, ein(clamp((t - self.t0) / 0.2))) if t < td else lerp(12, -16, eout(clamp((t - td) / 0.2)))
        if t >= tc: ang = lerp(-16, 6, eout(clamp((t - tc) / 0.12)))
        fr, _ = put(fr, t, 'C5/c16_drip', 960, 560, 1500, anchor='src', src=(0.497, 0.5), rot=90 + ang, rim=COLD, rim_amt=2.0, flash=fl,
                    expo=1.0, sat=0.7, wind=0, breathe=0.0)        # 刃（c16_drip 第 2 次：横转、挥动、带血），不露手
        # 第七棒：「对」「错」= 刀面反光里的镂空字（暗槽亮边），跟着刀转（rot 跟刀），不再是白字压白刀面
        e = eout(clamp((t - td + 0.02) / 0.09)); fr = etched_glyph(fr, '对', (700, 560), 250 * lerp(1.25, 1, e), e, rot=-ang * 0.6)
        e = eout(clamp((t - tc + 0.02) / 0.09)); fr = etched_glyph(fr, '错', (1240, 560), 250 * lerp(1.25, 1, e), e, rot=-ang * 0.6,
                                                                   edge=(1.0, 0.72, 0.4))
        fr = rain(fr, t, 330, inten=1.0, angle=12)
        self.ca = 6 if (0 <= t - td < 0.08 or 0 <= t - tc < 0.08) else 0
        return fr


class C34(Shot):
    """第五棒重做：MS 斜劈（slash_diag_down）——「是非对错」四道刀光残影悬在他身周的雨里，153.12 他一刀斜劈到底，
    四个字同时被斩成两半、错开、坠散（他亲手斩掉别人定的是非对错，接「我自己扛」）。"""
    def render(self, t):
        u = self.u(t)
        ts = V(153.12)
        fl = 0.9 * pulse(t, ts, 0.14)
        fr = storm(t, 34, horizon=860, flash=0.35 + fl, fc=(960, 150), refl=0.5)
        sp = sm(ts, ts + 0.6, t)
        for i, (ch, c, rt) in enumerate((('是', (300, 300), -8), ('非', (1560, 290), 8), ('对', (270, 700), -6), ('错', (1720, 560), 6))):
            fr = arc_glyph(fr, ch, (c[0] + 10 * math.sin(t * 2 + i), c[1] + 6 * math.cos(t * 2.3 + i)), 190, 0.85, rot=rt, split=sp,
                           warm=1.0 if ch == '错' else 0.0)
        fr = blade_smear(fr, (1450, 180), (150, 960), (t - ts) / 0.16, bend=0.06, width=110, seed=341, amt=1.6, warm=0.25)
        fr, _ = put(fr, t, 'C/slash_diag_down', 780, 1010, 680, rim=COLD, rim_amt=2.4, rim_dir=(0.4, -1), flash=0.8 * fl,
                    expo=0.95, wind=9)
        fr = rain(fr, t, 340, inten=1.0, angle=-10)
        self.ca = 5 if 0 <= t - ts < 0.1 else 0
        return fr


class C35(Shot):
    """LS 硬扛：最大的一方巨印压下，鬼屠举刀过顶硬扛（S087），地面龟裂、积水被压得往外喷；「扛」朱红竖排。"""
    def __init__(self): self.seal = CP.StoneSeal('令', seed=35, front_text='令')
    def render(self, t):
        u = self.u(t)
        tk = V(154.70)
        sink = 18 * eout(u)
        fr = storm(t, 35, horizon=880, flash=0.35 + 0.8 * pulse(t, tk, 0.2), refl=0.5)
        oy = lerp(-60, 20, eio(u))
        fr, _ = self.seal.draw(fr, 960, 330 + sink - oy * 0.3, 1300, yaw=8, pitch=26, rim=GOLD, rim_amt=0.8, flash=0.5 * pulse(t, tk, 0.2), light=(-0.3, 0.6, -0.7), shadow=0)
        cr = np.zeros((H // 4, W // 4), np.float32)
        for i in range(6):
            p = crack_path((960, 965), (960 + (i - 2.5) * 330, 1060), 350 + i, n=24, jag=0.06)
            cr = np.maximum(cr, draw_crack(cr.shape, p / 4, 2, branches=3, seed=i, prog=sm(self.t0, self.t0 + 0.8, t)))
        crm = cv2.resize(cr, (W, H))
        fr = fr * (1 - crm[..., None] * 0.8) + crm[..., None] * np.array([1.0, 0.5, 0.2], np.float32) * 0.5
        fr, _ = put(fr, t, 'S087/brace_overhead', 960, 1000 + sink, 720, rim=GOLD, rim_amt=1.8, rim_dir=(0, -1), expo=0.95, wind=6,
                    flash=0.5 * pulse(t, tk, 0.2))
        fr = dust(fr, t, 351, n=160, amt=0.7, drift=(0, -40), region=(300, 820, 1620, 1000))
        fr = rain(fr, t, 350, inten=0.9, angle=6)
        return fr


class C35b(Shot):
    """MCU 仰拍「扛」：同轴跳进——刀横在头顶，印底（朱砂「令」）压到刀背上，咬牙、肩塌、膝弯；154.70 接触瞬间火星沿刃迸开，
    画面重震、整体下沉 30px，再一点点顶回去（表演：被压下 → 顶住）。精灵 S087 第 2 次使用（C35 全身 → 这里中近景大仰角）。"""
    def __init__(self): self.seal = CP.StoneSeal('令', seed=35, front_text='令')
    def render(self, t):
        u = self.u(t)
        tk = V(154.70)
        k = max(0.0, t - tk)
        hit = pulse(t, tk, 0.10)
        # 被压下 → 顶回：先沉 34px，0.5s 内顶回一半
        sink = (34 * eout(k / 0.08) - 16 * sm(0.15, 0.6, k)) if t >= tk else 6 * u
        fr = storm(t, 352, horizon=1300, flash=0.25 + 0.9 * hit, fc=(960, 150), ground=False)
        fr = fr * np.array([1.05, 0.88, 0.85], np.float32)          # 红黑段（C33–C35b）整体偏红
        # 印底：从画顶压下，接触后停在刀背上方
        sy = lerp(-260, -40, ein(sm(self.t0, tk, t), 2)) + (sink * 0.9 if t >= tk else 0)
        fr, _ = self.seal.draw(fr, 960, sy, 2600, yaw=4, pitch=40, rim=(1.0, 0.35, 0.2), rim_amt=0.7, flash=0.6 * hit,
                               light=(-0.2, 0.9, -0.5), shadow=0, mblur=t < tk)
        # 印压下来的阴影罩住他上半身
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        fr = fr * (1 - 0.35 * np.clip(1.2 - yy * 1.8, 0, 1) * sm(self.t0, tk, t))
        # 第四棒：换生图 brace_cu（咬牙、肘弯、刀横过顶；S087 只剩 C35 全身一次）
        # 第七棒（critic_C_r3 P1⑦ 定妆脸统一）：brace_cu（刘海、显嫩、咧嘴）→ C6/c35b_bear（定妆脸：中分、长脸、冷峻、抿唇咬牙），
        # tools/c_solidify.py 修补手/刀面半透明 → c35b_bear2；精灵四边出画（宽 2044 > 1920），刀身横在画面上 1/4
        fr, A = put(fr, t, 'C6/c35b_bear2', 960, 175 + sink, 1150, anchor='src', src=(0.5, 0.09), rim=(1.0, 0.45, 0.3), rim_amt=2.2,
                    rim_dir=(0, -1), expo=0.95, wind=3, flash=0.7 * hit, breathe=0.010)
        # 刀背与印底的接触线：火星沿刃喷射（刀身略右低：x700→y261、x1220→y296）
        if t >= tk - 0.02:
            for sd, x0, y0 in ((-1, 700, 180), (1, 1220, 215)):
                fr = sparks(fr, t, 353 + sd, (x0, y0 + sink), n=140, life=0.6, speed=(300, 1300), dirc=(sd, 0.15), spread=0.6, grav=1400,
                            t0=tk, burst=True, color=(1.0, 0.6, 0.25), amt=1.4)
            fr = K.vol_light(fr, (960, 190 + sink), 520, (1.0, 0.45, 0.2), 0.5 * hit + 0.15)   # 第七棒：切点=接触帧，叠 slam 冲击后脸过曝 → 0.9→0.5
        fr = dust(fr, t, 354, n=160, amt=0.8 * min(1, k * 8) * (1 - sm(0.3, 0.8, k)), drift=(0, 260), region=(200, BAR, 1720, 600), size=(1, 4))
        fr = rain(fr, t, 355, inten=0.7, angle=4, layers=(1, 2, 3))
        self.ca = 7 if 0 <= k < 0.1 else 0
        return fr


_PLATE = {}
def plate(name, w=W, h=H):
    """生图整幅底板（assets/gen/<name>_raw.png）→ float32 线性 0..1，缩放到覆盖 w×h。"""
    if name not in _PLATE:
        im = cv2.imread(ROOT_DIR + f'/assets/gen/{name}_raw.png', cv2.IMREAD_COLOR)[..., ::-1]
        sc = max(w * 1.12 / im.shape[1], h * 1.12 / im.shape[0])
        im = cv2.resize(im, (round(im.shape[1] * sc), round(im.shape[0] * sc)), interpolation=cv2.INTER_AREA)
        _PLATE[name] = im.astype(np.float32) / 255.0
    return _PLATE[name]


def plate_view(name, cx, cy, zoom):
    """从底板取以 (cx,cy)（底板归一化坐标）为中心、缩放 zoom 的 W×H 视窗。"""
    P = plate(name)
    ph, pw = P.shape[:2]
    s = zoom
    M = np.float32([[s, 0, W / 2 - s * cx * pw], [0, s, H / 2 - s * cy * ph]])
    return cv2.warpAffine(P, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


class C36(Shot):
    """ELS 跪伏千军「天」（第四棒：换生图底板 army_kneel，去掉程序旗海）：C18 冲锋的同一支军，这时全部跪在积水里低头，
    旗杆插地，中间一条空通道直通天边——没有人站着。镜头沿通道低空推进；155.96「天」一道横贯天际的闪电把盔顶、旗、水面一齐照亮，
    同时字「天不」压在天上（暗衬）。叙事：众人都跪下了，只剩问天的人。"""
    def render(self, t):
        u = self.u(t)
        tt = V(155.96)
        fl = bolt_env(t, tt) * 1.2 + 0.4 * bolt_env(t, V(155.40))
        fr = plate_view('C/army_kneel', 0.49, 0.50 - 0.02 * u, lerp(1.0, 1.09, eio(u)))
        fr = fr * (0.8 + 0.7 * fl)                                                     # 平时略压，闪电照亮
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        fr = fr * (1 + 0.6 * fl * np.clip(1 - yy * 1.6, 0, 1) * np.array([0.9, 0.95, 1.1], np.float32))
        fr = bolt(fr, t, tt, 361, (60, 260), (1860, 300), inten=1.3, branches=12, width=4)
        fr = bolt(fr, t, V(155.40), 362, (1400, 140), (1500, 470), inten=0.7)
        fr = fog(fr, t, 36, density=0.35, y0=470, y1=720, color=(0.30, 0.33, 0.40), speed=(50, 0))
        fr = rain(fr, t, 360, inten=0.9, angle=8)
        return fr


class C37(Shot):
    """第五棒重做（评审 P1：「判」大字 ≈ 副歌一 S042「天」大字；开头空画面）：雷雨里一块御赐大匾（实物：黑漆描金龙框，生图 C5/c37_plaque）
    挂在铁链上摇晃——开场「天不」从上一镜带进来、在匾上方碎裂；156.70 一道闪电照亮，匾心泥金「判」字被电光逐笔描亮；
    156.94 第二道雷正劈匾心，匾沿锯齿裂缝一分为二、两半翻落，金屑和木屑迸散。"""
    def __init__(self):
        Z = np.zeros((H, W, 3), np.float32)
        self.Z = Z
        r = np.random.default_rng(37)
        xs = 960 + np.cumsum(r.normal(0, 14, 40)); xs -= xs.mean() - 960
        self.crack = np.stack([xs, np.linspace(BAR - 40, H - BAR + 40, 40)], 1).astype(np.int32)
    def render(self, t):
        u = self.u(t)
        tp = V(156.70); ts = tp + 0.24
        fl = bolt_env(t, tp) * 1.1 + bolt_env(t, ts) * 1.3
        fr = storm(t, 37, horizon=1300, flash=0.15 + 0.5 * fl, fc=(960, 160), ground=False) * 0.85
        sw = 2.2 * math.sin((t - self.t0) * 3.2)
        # 匾（独立层：先在黑底上合成，再按裂缝分两半）
        P, A = put(self.Z.copy(), t, 'C5/c37_plaque', 960, 560, 560, anchor='src', src=(0.5, 0.5), rot=sw, rim=COLD, rim_amt=1.4,
                   rim_dir=(-0.5, -0.9), flash=0.5 * fl, expo=1.12 + 0.4 * fl, sat=0.9, tint=(1.0, 0.98, 0.94), wind=0, breathe=0.0)   # 第十二棒：匾面提亮一档
        # 第九棒 P2⑩：匾心先有暗刻的「判」（阴刻、暗铜色），不再是半拍空匾；电光再把它逐笔描成泥金
        Ld = T.Layer(); T.place(Ld, '判', 960, 560, 300, (0.30, 0.21, 0.10), 'serif_black', rot=sw, texture=False)
        Ld.A *= 0.85 * sm(self.t0, self.t0 + 0.12, t)
        P = T.compose(P, Ld, shadow=0.7, shadow_sigma=3)
        if t >= tp - 0.30:                      # 泥金「判」：电光逐笔描亮（自上而下）
            prog = sm(tp - 0.30, tp + 0.04, t)
            L = T.Layer(); T.place(L, '判', 960, 560, 300, (1.0, 0.84, 0.46), 'serif_black', rot=sw, texture=False)
            yy = np.arange(H, dtype=np.float32)[:, None]
            L.A *= np.clip((lerp(380, 760, prog) - yy) / 30, 0, 1)
            P = T.compose(P, L, shadow=0.5, shadow_sigma=8, glow=1.0 + 0.8 * pulse(t, tp, 0.2), glow_sigma=16, glow_color=(1.0, 0.6, 0.2))
        for x in (700, 1220):                    # 铁链
            fr = red_line(fr, (x + 30, BAR - 10), (x + sw * 8, 330), w=3, amt=0.25)
        if t < ts:
            fr = fr * (1 - A[..., None]) + P
        else:
            q = t - ts
            msk = np.zeros((H, W), np.float32)
            poly = np.concatenate([[[0, 0]], self.crack, [[0, H]]]).astype(np.int32)
            cv2.fillPoly(msk, [poly], 1.0)
            for sg, m_ in ((-1, msk), (1, 1 - msk)):
                ang = sg * 26 * q * q * 6 + sw
                M = cv2.getRotationMatrix2D((960 + sg * 300, 560), ang, 1.0); M[0, 2] += sg * 220 * q; M[1, 2] += 1500 * q * q
                Am = cv2.warpAffine(A * m_, M, (W, H)); Pm = cv2.warpAffine(P * m_[..., None], M, (W, H))
                fr = fr * (1 - Am[..., None]) + Pm
            edge = np.zeros((H // 2, W // 2), np.float32)
            cv2.polylines(edge, [self.crack // 2], False, 1.0, 2, cv2.LINE_AA)
            fr = fr + cv2.resize(cv2.GaussianBlur(edge, (0, 0), 3), (W, H))[..., None] * np.array([1.0, 0.7, 0.35], np.float32) * 2.0 * pulse(t, ts, 0.15)
            fr = sparks(fr, t, 371, (960, 560), n=160, life=0.7, speed=(300, 1200), dirc=(0, -0.3), spread=3.0, grav=1300, t0=ts, burst=True,
                        color=(1.0, 0.75, 0.35), area=(30, 300))
        fr = bolt(fr, t, ts, 372, (1000, 40), (960, 560), inten=1.2, width=4)
        fr = rain(fr, t, 370, inten=0.8, angle=10)
        # 第十二棒（critic_C_r6 P2⑨）：前景层——左上角近景飞檐（焦外大虚、冷边光）+ 镜头前粗雨帘（焦外），匾退到中景
        E = np.zeros((H // 2, W // 2), np.float32)
        cv2.fillPoly(E, [np.array([[0, 0], [600, 0], [560, 95], [300, 140], [120, 230], [0, 300]], np.int32)], 1.0, cv2.LINE_AA)
        cv2.fillPoly(E, [np.array([[540, 80], [640, 40], [600, 110]], np.int32)], 1.0, cv2.LINE_AA)   # 檐角起翘
        E = cv2.resize(cv2.GaussianBlur(E, (0, 0), 9), (W, H))
        Er = np.clip(E - cv2.GaussianBlur(E, (0, 0), 14), 0, 1) * 2.2
        fr = fr * (1 - 0.95 * E[..., None]) + E[..., None] * 0.006 + Er[..., None] * COLD * (0.35 + 0.8 * fl)
        Rf = np.zeros((H // 2, W // 2), np.float32); rr_ = np.random.default_rng(373)
        for i in range(16):
            x = rr_.uniform(0, W // 2); y = ((t * rr_.uniform(900, 1300) + rr_.uniform(0, 600)) % 800) - 200
            cv2.line(Rf, (int(x), int(y)), (int(x + 30), int(y + 170)), 1.0, int(rr_.uniform(4, 9)), cv2.LINE_AA)
        Rf = cv2.resize(cv2.GaussianBlur(Rf, (0, 0), 5), (W, H))
        fr = fr + Rf[..., None] * COLD * (0.10 + 0.25 * fl)
        self.ca = 6 if (0 <= t - tp < 0.1 or 0 <= t - ts < 0.1) else 0
        return fr


class C38(Shot):
    """第五棒重做（评审 P1：刃面微距 + LED 点刃纹撞副歌一 S027/S028，手指悬空没手臂）：
    CU 握刀手特写——生图 C5/c38_grip：湿透的袖口和护腕从左入画，手背青筋暴起、指节发白，雨水沿指节滴落；
    冷白侧逆光从左上扫过指节。镜头缓推 + 手腕微旋（握紧）；157.34 一道远雷照亮；「我来」紧排刻在刀身上方的空区（不在手指下）。"""
    def render(self, t):
        u = self.u(t)
        tf = V(157.34)
        fl = bolt_env(t, tf) * 0.8 + 0.5 * bolt_env(t, V(158.18))
        fr = storm(t, 38, horizon=1300, flash=0.25 + 0.6 * fl, ground=False, fc=(400, 150)) * 0.8
        fr = K.vol_light(fr, (300, 200), 600, COLD, 0.25 + 0.4 * fl)
        grip = eio(clamp((t - self.t0) / 0.6)) + 0.4 * pulse(t, V(158.18), 0.2)
        fr, _ = put(fr, t, 'C5/c38_grip', 960, 560, 1180 * (1.0 + 0.05 * u), anchor='src', src=(0.5, 0.5), rot=1.5 - 2.5 * grip,
                    rim=COLD, rim_amt=2.6, rim_dir=(-0.8, -0.6), flash=fl, expo=0.95, sat=0.55, wind=0, breathe=0.0)
        # 指节滴水（握紧时甩落）
        fr = sparks(fr, t, 381, (930, 760), n=26, life=0.9, speed=(40, 160), dirc=(0, 1), spread=0.3, grav=1400, amt=0.7,
                    color=(0.85, 0.9, 1.0), area=(140, 20))
        for j, (c, ti) in enumerate(() if R5 else (('我', V(158.18)), ('来', V(158.36)))):   # 第五轮 #43：去「我来」
            if t < ti - 0.08: continue
            e = eout((t - ti + 0.08) / 0.14)
            fr = paste_glyph(fr, c, 1440 + j * 150, 330, 130, (0.95, 0.96, 1.0), glow=0.6, glow_c=(0.6, 0.7, 1.0), alpha=e,
                             scale=lerp(1.6, 1, e), font='serif_black')
        fr = rain(fr, t, 380, inten=0.8, angle=4, layers=(0, 1, 2, 3))
        return fr


class C39(Shot):
    """MCU 蓄力：鬼屠把刀拉到身后（S090），镜头推近 + 慢放；第五棒（评审 P0「量」缺失）：158.56「量」随刀刃出鞘
    被一刀刻在画面左侧空区（朱红大字、赤热刃口沿刀势斜向划过，余烬闪烁），刀身一道冷光扫过；159.01 底鼓暗角收紧。"""
    def render(self, t):
        u = self.u(t)
        tq = V(158.56)
        fr = storm(t, 39, horizon=1300, flash=0.3 + 0.5 * pulse(t, V(159.01), 0.2) + 0.5 * pulse(t, tq, 0.15), ground=False, fc=(500, 200))
        if not R5:                               # 第五轮 #43：去「量」（连同它的红光、刻字火星）；出鞘冷光保留
            fr = K.vol_light(fr, (520, 520), 420, (1.0, 0.35, 0.15), 0.45 * sm(tq - 0.02, tq + 0.12, t) * (1 - 0.4 * sm(tq + 0.3, self.t1, t)))
        fr, _ = put(fr, t, 'S090/wind_up', 1180, 1110, 900 * (1.0 + 0.04 * eout(u)), rim=COLD, rim_amt=2.6, rim_dir=(-0.8, -0.6), expo=1.0,
                    wind=7, flash=0.4 * pulse(t, V(159.01), 0.2) + 0.5 * pulse(t, tq, 0.12))
        gq = clamp((t - tq) / 0.30)                # 第五棒（评审 P1 C39 近静止）：出鞘冷光沿刀身从护手扫到刀尖
        if 0 < gq < 1:
            gx, gy = lerp(1400, 990, eio(gq)), lerp(520, 255, eio(gq))
            fr = K.vol_light(fr, (gx, gy), 38, (0.92, 0.96, 1.0), 0.75 * math.sin(math.pi * gq))
        q = (t - (tq - 0.03)) / 0.16
        if not R5: fr = carve_glyph(fr, '量', 520, 540, 330, q, ang=-35, seed=39, t=t)
        if 0 < q < 2.5 and not R5:
            fr = sparks(fr, t, 391, (lerp(380, 660, min(1, q)), lerp(400, 690, min(1, q))), n=70, life=0.5, speed=(200, 800), dirc=(0.6, 0.8),
                        spread=1.2, grav=1200, t0=tq, burst=True, color=(1.0, 0.45, 0.15), amt=1.2)
        fr = rain(fr, self.t0 + (t - self.t0) * 0.5, 390, inten=0.9, angle=8)
        return fr


class C40(Shot):
    """LS 背身横斩（新精灵 slash_back）：前方雷暴里一架高过云的青铜天平，159.95 一刀横断天平横梁（断口赤热、秤盘甩落）。"""
    def __init__(self): self.B = CP.BronzeBalance(seed=40)
    def render(self, t):
        u = self.u(t)
        ts = V(159.66)          # 第三棒：一刀落在「刀」上；「是我」交给 C40b 的面部特写
        fl = 1.0 * pulse(t, ts, 0.15) + 0.6 * bolt_env(t, V(159.50))
        fr = storm(t, 40, horizon=900, flash=0.4 + fl, fc=(960, 250), refl=0.5)
        br = ein(sm(ts, ts + 0.6, t), 1.4)
        tb = 6 * math.sin(t * 1.6)
        fr = fog(fr, t, 41, density=0.35, y0=200, y1=520, color=(0.30, 0.32, 0.38), speed=(40, 0))
        fr, info = self.B.draw(fr, t, 960, 300, 1560, tilt=tb, rim=(0.85, 0.9, 1.0), rim_amt=0.9 + 1.5 * fl, light=(-0.4, -0.9),
                               fill_l=fill_people(22, 401, 60, scatter=br * 0.6), fill_r=fill_seal(130, 1.0, fl), break_=br)
        fr = fog(fr, t, 40, density=0.5, y0=600, y1=900, color=(0.38, 0.4, 0.46), speed=(30, 0))
        fr, _ = put(fr, t, 'C/slash_back', 760, 1050, 760, rim=COLD, rim_amt=2.6, rim_dir=(0, -1), flash=fl, expo=0.85, wind=10)
        fr = arc_streak(fr, (960, 330), 1100, 140, 200, -20, (t - ts) / 0.4, width=12, amt=2.2)
        fr = sparks(fr, t, 401, (960, 300), n=220, life=0.8, speed=(200, 900), dirc=(0, 1), spread=2.5, grav=600, t0=ts, burst=True,
                    color=(1.0, 0.7, 0.3))
        fr = rain(fr, t, 400, inten=1.0, angle=10)
        self.ca = 6 if 0 <= t - ts < 0.1 else 0
        return fr


class C40b(Shot):
    """ECU「是我」：斩断天平后回头——S090 精灵第 2 次使用（C39 中近景 → 这里大特写脸），琥珀眼直视镜头，
    159.95「是」一道冷光沿刀刃扫过、160.08「我」眼里一亮 + 头发被余风甩起；人物表演落在眼神上。"""
    def render(self, t):
        u = self.u(t)
        ts, tw = V(159.95), V(160.08)
        fl = 0.5 * bolt_env(t, ts) + 0.4 * pulse(t, tw, 0.12)
        fr = storm(t, 402, horizon=1300, flash=0.2 + fl, fc=(1500, 120), ground=False) * 0.85
        # 背景：断开的天平余烬从右上落下（承接 C40）
        fr = sparks(fr, t, 403, (1500, 140), n=120, life=1.4, speed=(40, 200), dirc=(0, 1), spread=1.0, grav=200, amt=0.9,
                    area=(600, 60), color=(1.0, 0.6, 0.25))
        # 第四棒：换生图 point_cam（刀尖指镜、直视镜头；S090 只剩 C39 一次）
        fr, A = put(fr, t, 'C/point_cam', 760 - 30 * u, 470, 1100 * (1 + 0.05 * u), anchor='src', src=(0.39, 0.33), rim=COLD,
                    rim_amt=1.5, rim_dir=(0.8, -0.6), expo=1.0, wind=10 + 14 * pulse(t, tw, 0.2), flash=fl, breathe=0.0)
        # 刀刃上一道冷光扫过（「是」）：沿精灵里刀的方向（右上斜）
        q = (t - ts) / 0.30
        if 0 < q < 1:
            G = np.zeros((H // 2, W // 2), np.float32)
            p0 = np.array([720, 840]); p1 = np.array([1850, 895]); c = p0 + (p1 - p0) * q
            cv2.line(G, tuple((c / 2 - (p1 - p0) / 2 * 0.08).astype(int)), tuple((c / 2 + (p1 - p0) / 2 * 0.08).astype(int)), 1.0, 3, cv2.LINE_AA)
            G = cv2.resize(cv2.GaussianBlur(G, (0, 0), 3) * 2 + G, (W, H))
            fr = fr + G[..., None] * np.array([0.9, 0.95, 1.0], np.float32) * 1.6 * math.sin(math.pi * q)
        # 眼中一亮（「我」）
        for ex in (700, 872):
            fr = K.vol_light(fr, (ex - 30 * u, 490), 26, (1.0, 0.75, 0.4), 1.4 * pulse(t, tw, 0.18))
        fr = rain(fr, t, 404, inten=0.8, angle=10, layers=(2, 3))
        self.ca = 5 if 0 <= t - tw < 0.08 else 0
        return fr


class C41(Shot):
    """第六棒重做（critic_C_r3 P0②：扁平图标纸人 + 秤砣顶块错位 + 橙色弧形物 → 不可交付；最后一拍交给刀光与人物）。
    MS 低机位正面：他（生图 C6/c41_sweep，定妆脸、横斩收势、刀平伸向画右、直视镜头）从横斩里旋进定格——
    160.37「的」一道横刀光自左向右扫过全画、在雨里留下一条炭红的焦痕；焦痕往上引燃，火线沿「答」的笔画爬（160.66「回」起），
    161.00「答」整字烧穿画面：字槽里透出白金色的光、烧边炭红，光从他身后勾亮发梢和刀脊；段尾故障切黑交给 Bridge。
    画面里不再有秤、印、纸人：权力的道具在 C40 已被斩断，最后一帧只留人、刀和他的回答。"""
    def __init__(self):
        L = T.Layer(); T.place(L, '答', 1330, 545, 580, (1, 1, 1), 'serif_black', texture=False)
        g0 = L.A.copy()
        r = np.random.default_rng(41)
        f = cv2.GaussianBlur(r.random((H, W)).astype(np.float32), (0, 0), 2.2)
        self.nf = np.clip(((f - f.mean()) / (f.std() + 1e-6)) * 0.5 + 0.5, 0, 1)
        # 第八棒（critic_C_r4 P1①）：焦边改连续不规则——低频噪声扰动字的符号距离场，得到一条不断开的烧边
        def lf(sig, seed):
            q = cv2.GaussianBlur(np.random.default_rng(seed).random((H, W)).astype(np.float32), (0, 0), sig)
            return (q - q.mean()) / (q.std() + 1e-6)
        b = (g0 > 0.5).astype(np.uint8)
        sd = cv2.distanceTransform(b, cv2.DIST_L2, 5) - cv2.distanceTransform(1 - b, cv2.DIST_L2, 5)   # 字内为正
        sd = sd + 1.3 * lf(9, 411) + 0.5 * lf(3, 412)            # 不规则：大起伏 + 小锯齿（第十二棒：3.2/1.2 → 1.3/0.5，竹字头细笔不再被吃断）
        self.sd = sd.astype(np.float32)
        self.g = np.clip(sd / 1.5 + 0.5, 0, 1).astype(np.float32)          # 烧穿的洞（边缘已不规则）
        self.var = np.clip(0.75 + 0.25 * lf(6, 413), 0.45, 1.0).astype(np.float32)   # 烧边亮度起伏（不归零 → 不断开）
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.ty = 470 + 0.03 * (xx - 960)                         # 焦痕（刀路）高度
        self.d = np.clip(self.ty - yy, 0, None) + 0.35 * np.abs(xx - 1330) + 25 * lf(12, 414)      # 火从焦痕往上、从中间往两边烧
    def render(self, t):
        u = self.u(t)
        ts, tr, ta = V(160.37), V(160.66), V(161.00)
        fl = 0.9 * pulse(t, ts, 0.12) + 0.5 * bolt_env(t, V(160.20))
        fr = storm(t, 41, horizon=1300, flash=0.25 + fl, fc=(1300, 200), ground=False) * 0.8
        fr = fog(fr, t, 41, density=0.35, y0=700, y1=1000, color=(0.30, 0.32, 0.38), speed=(30, 0))
        # 「答」：先是焦痕引燃的火线沿笔画爬，再整字烧穿（字槽透白金光）。第八棒：所有烧边都是连续的带，不用细噪声门限（去「蚂蚁线」）
        g, sd = self.g, self.sd
        front = 60 + 900 * ein(clamp((t - tr + 0.05) / (ta - tr + 0.05)), 1.4) if t > tr - 0.05 else -1
        lit = np.clip((front - self.d) / 30.0 + 0.5, 0, 1) if front > 0 and not R5 else None   # 第五轮 #43：去「答」（火线/烧穿/火星全去），只留刀光与焦痕
        if lit is not None and lit.max() > 0:
            thru = sm(ta - 0.03, ta + 0.05, t)                    # 烧穿
            ring = np.clip(1 - np.abs(sd + 4) / 16.0, 0, 1) * lit                     # 焦黑环（字边内外各约 15px）
            ash = np.clip(1 - np.abs(sd + 20) / 22.0, 0, 1) * lit * 0.55              # 外圈灰烬
            ember = np.exp(-((sd - 2.5) / 3.5) ** 2) * lit * self.var                 # 内缘炭红（连续）
            fire = np.exp(-((self.d - front) / 45.0) ** 2) * np.clip(sd / 3 + 1, 0, 1) * self.var   # 爬行火线（连续）
            body = g * lit                                                             # 已烧到的字身：先焦黑
            fr = fr * (1 - 0.88 * np.maximum(body * (1 - thru), ring)[..., None])
            fr = fr * (1 - 0.25 * ash[..., None]) + ash[..., None] * np.array([0.10, 0.095, 0.09], np.float32)
            fr = fr + fire[..., None] * np.array([1.0, 0.45, 0.12], np.float32) * 2.0 * (1 - 0.85 * thru)   # 第十棒：烧穿后火线退到边缘
            fr = fr + ember[..., None] * np.array([1.0, 0.30, 0.06], np.float32) * (1.1 - 0.35 * thru)   # 第十二棒：烧穿后炭红边收窄，外圈焦黑环露出来
            fr = fr + cv2.GaussianBlur(ember, (0, 0), 6)[..., None] * np.array([1.0, 0.35, 0.08], np.float32) * 0.6 * (1 - 0.7 * thru)
            if thru > 0:
                core = np.clip((sd - 4.0) / 3.0, 0, 1) * lit
                # 第十棒（critic_C_r5 P2④）：字芯不再过曝白黄 → 压回暖红熔芯（越往笔画中心越偏橙），笔画轮廓靠焦黑环读出
                dep = np.clip((sd - 4.0) / 14.0, 0, 1)[..., None]
                hot = (np.array([0.50, 0.07, 0.025], np.float32) * (1 - dep) + np.array([0.80, 0.22, 0.06], np.float32) * dep) \
                    * (0.50 + 0.20 * pulse(t, ta, 0.12))   # 第十二棒（critic_C_r6 P1③）：字芯再压暗一档 → 暖红熔芯，不再一团橙黄 * (0.85 + 0.3 * self.var[..., None])
                fr = fr * (1 - core[..., None] * thru) + core[..., None] * hot * thru
                fr = fr + cv2.GaussianBlur(core, (0, 0), 40)[..., None] * np.array([1.0, 0.30, 0.10], np.float32) * 0.14 * thru
                fr = K.vol_light(fr, (1330, 545), 700, (1.0, 0.45, 0.22), 0.10 * thru)
            # 向上飘的少量火星（从烧边升起，循环发射）
            fr = sparks(fr, t, 415, (1330, 600), n=36, life=1.1, speed=(40, 140), dirc=(0, -1), spread=0.5, grav=-60,
                        area=(240, 220), color=(1.0, 0.55, 0.2), amt=0.7 * float(lit.max()))
        # 焦痕：刀路留在雨里的一条炭红线（刀光过后）
        if t > ts:
            k = t - ts
            G = np.zeros((H // 2, W // 2), np.float32)
            x1 = int(lerp(0, W, eout(clamp(k / 0.12))) / 2)
            cv2.line(G, (0, int(self.ty[0, 0] / 2)), (x1, int((470 + 0.03 * (x1 * 2 - 960)) / 2)), 1.0, 2, cv2.LINE_AA)
            G = cv2.resize(G, (W, H)); G = G * self.var   # 第九棒：原来用细噪声门限 → 断成虚线（蚂蚁线）；改连续带、只做低频明暗起伏
            fr = fr + (G + cv2.GaussianBlur(G, (0, 0), 8) * 1.5)[..., None] * np.array([1.0, 0.35, 0.08], np.float32) * (0.5 + 0.7 * math.exp(-k / 0.3))
        # 人：从横斩里旋进收势（前 0.15s 旋转拖影），之后呼吸、风；身后的「答」光勾亮发梢和刀脊
        kin = clamp((t - self.t0) / 0.16)
        thru = 0.0 if R5 else sm(ta - 0.03, ta + 0.1, t)
        if R5: fl = fl + 0.45 * bolt_env(t, ta)       # 「答」那拍改成一记远雷照亮他（不再是身后字光）
        fr, _ = put(fr, t, 'C6/c41_sweep', 760, 600, 1000, anchor='src', src=(0.41, 0.56), rot=lerp(-7, 0, eout(kin)),
                    rotblur=6.0 * (1 - kin), rim=lerp(np.array(COLD), np.array((1.0, 0.72, 0.4)), thru), rim_amt=2.2 + 1.6 * thru,
                    rim_dir=(0.6, -0.8), flash=fl + 0.6 * thru, expo=0.95, wind=8, breathe=0.008)
        # 刀光：横扫全画（160.37）
        fr = blade_smear(fr, (-100, 520), (2020, 440), (t - ts + 0.06) / 0.14, bend=-0.05, width=90, seed=411, amt=1.5, warm=0.2)
        fr = sparks(fr, t, 412, (1790, 470), n=120, life=0.6, speed=(200, 900), dirc=(1, -0.2), spread=1.0, grav=900, t0=ts, burst=True,
                    color=(1.0, 0.6, 0.25), amt=1.1)
        if not R5: fr = sparks(fr, t, 413, (1330, 545), n=200, life=0.9, speed=(100, 600), dirc=(0, -1), spread=1.6, grav=-80, t0=ta, burst=True,
                    area=(260, 260), color=(1.0, 0.45, 0.18), amt=0.55)
        fr = rain(fr, t, 410, inten=0.8, angle=10, layers=(1, 2, 3), freeze=0.35 if t > ta else None)
        return fr


SHOTS = [C01, C02, C03, C04, C05, C06, C07, C08, C09, C10, C11, C12, C13, C14, C15,
         C16, C17, C18, C19, C20, C21, C22, C23, C24, C25, C26, C27, C28, C29, C30, C31, C32, C33, C34, C35, C35b, C36, C37, C38,
         C39, C40, C40b, C41]
# 切点（声音时刻，秒）：拍 / 人声首字 / 起音；帧 = 视觉帧（最近帧再提前 1 帧）。首尾 = 段落边界。
# 第三棒：按 librosa 起音复核，6 个偏离切点改到最近强起音（118.95→118.92、128.78→128.87、134.50→134.57、135.60→135.63、
# 148.49→148.34、149.30→149.15）；C15 133.22→133.135；新增 C35b（154.545「扛」前）、C40b（159.93「是」）；C39 158.62→158.54。
CUT_T = [117.80, 118.92, 120.53, 121.46, 122.83, 123.74, 124.88, 125.70, 126.27, 127.41, 128.87, 130.17, 131.50, 132.45, 133.38,
         134.57, 135.63, 136.56, 137.49, 138.39, 139.32, 140.69, 142.06, 143.43, 144.82, 145.73, 146.63, 147.56, 148.34, 149.15,
         150.30, 151.70, 152.60, 153.07, 153.97, 154.70, 155.36, 156.27, 157.18, 158.54, 159.47, 159.93, 160.38]
if R5:
    CUT_T[2] = 120.80     # r5 返工 #36：甩镜在 121.0 前收完（切帧 3622=120.733，甩镜 120.67–120.81）；原 121.00 让 2:01.0 正落在甩镜中间。 原注：第五轮 #35：C02→C03 切点挪到「纲」字那拍（切帧 3628 = V(120.96)），「纲」在 C02 的红线上落定后再切、C03 一进来木偶就被拽起
assert len(CUT_T) == len(SHOTS)
# 第十二棒（critic_C_r6 P1①）：C13 起点 131.08 → 131.50（131.498 在拍强起音），镜长 1.37s → 0.97s；C12 顺延到 1.33s。段落边界不动。
# 第五棒：评审 P1「整体比拍点晚 1–2 帧」→ 视觉帧再前移 1 帧（最近帧 -2，切在拍前）；间奏 C14/C15 改到拍点 132.45 / 133.38（评审 P0）
CUT_F = [F0] + [round(x * FPS) - 2 for x in CUT_T[1:]] + [F1]
for _S, _a, _b in zip(SHOTS, CUT_F, CUT_F[1:]):
    _S.t0, _S.t1 = _a / FPS, _b / FPS

# 入切转场：(名称, pre 秒, post 秒, kw)。'hard' = 切后 2 帧冲击（推近 + 提亮）；c_trans 自写的 push/luma/seam/over/whip 中间帧都带两镜内容；
# 其余走 lib/trans.py。第三棒：flash_white 0 处、whip 1 处（C03）、白插帧改电光过曝。
CUTS = {
    'C02': ('match_line', 0.0, 0.12, {}),                                # 朱笔竖笔 ↔ 红丝线（图形匹配）
    'C03': ('whip', 0.10, 0.12, dict(direction=1)),                      # 全段唯一甩镜：沿丝线甩到皮影幕
    'C04': ('paper_tear', 0.06, 0.10, dict(angle=-10, seed=4)),         # 第十二棒（critic_C_r6 P2⑦）：glitch_cut 数码扫描线 → 皮影幕纸被撕开（古装质感）
    'C05': ('push', 0.10, 0.12, dict(center=(1620, 640))),               # 秤盘 → 箱口（推进穿越）
    'C06': ('hard', 0, 0, {}),
    'C07': ('seam', 0.0, 0.20, dict(y=880)),                             # 箱盖金缝张开 → 闪电照亮的脸
    'C08': ('push', 0.06, 0.08, dict(center=(1050, 400), z=0.5)),        # 同轴跳进眼睛
    'C09': ('slash_wipe', 0.05, 0.12, dict(angle=-55)),
    'C10': ('hard', 0, 0, {}),
    'C11': ('slash_wipe', 0.05, 0.12, dict(angle=-2)),                   # 横刀光 ↔ 横刀身（图形匹配）
    'C12': ('push', 0.06, 0.10, dict(center=(1300, 560), z=0.6)),        # 刀身 → 刃口（同轴推进）
    'C13': ('luma', 0.08, 0.12, {}),                                     # 赤热刃口亮处长出风眼
    'C14': ('push', 0.08, 0.12, dict(center=(960, 260), z=-0.25)),       # 风眼拉出 → 他头顶的同一个风眼
    'C15': ('hard', 0, 0, {}),
    'C16': ('over', 0.0, 0.17, dict(center=(960, 420))),                 # 副歌入口：吸气 3 帧 → 电光过曝炸开（非白帧）
    'C17': ('hard', 0, 0, {}),
    'C18': ('occlusion', 0.12, 0.12, dict(kind='spear', direction=1)),  # 枪林掠过遮挡
    'C19': ('hard', 0, 0, {}),
    'C20': ('ink_bleed', 0.06, 0.14, {}),                                # 斩落的枪缨墨溅 → 太上皇
    'C21': ('slash_wipe', 0.05, 0.14, dict(angle=-62)),                  # 对角刀线 = 分屏线
    'C22': ('hard', 0, 0, {}),
    'C23': ('push', 0.08, 0.12, dict(center=(960, 400))),                # 墙远景 → 墙面（同墙推进）
    'C24': ('occlusion', 0.10, 0.10, dict(kind='pillar', direction=1)),  # 横移：墙柱掠过前景
    'C25': ('hard', 0, 0, {}),
    'C26': ('shatter', 0.0, 0.22, dict(center=(960, 540))),        # 第六棒：从 C25 中轴劈缝炸开
    'C27': ('smoke_through', 0.08, 0.14, dict(direction=1, density=1.0, color=(0.62, 0.64, 0.68))),   # 第九棒 P2⑪：luma 中间帧碎片+天光糊团、露出 C27 方边 → 崩墙石尘冲过镜头
    'C28': ('ink_crack', 0.05, 0.12, dict(center=(960, 470), seed=28)),   # 第十二棒（critic_C_r6 P2⑦ 白闪同质化）：电光过曝 → 墨裂：崩墙的墨皮裂开、缝里透出伪天亮   # 第九棒 P2⑪：push 中间帧「亮」与人脸叠鬼影 → 伪天亮那道电光过曝切入
    'C29': ('hard', 0, 0, {}),                                           # 第四棒：luma 会在 C28 亮眼处开洞（像面具）→ 落拍硬切冲击
    'C30': ('flash_red', 0.0, 0.14, {}),
    'C31': ('hard', 0, 0, {}),
    'C32': ('split_slide', 0.06, 0.12, dict(angle=90.0)),                # 掌风压下：画面上下错开
    'C33': ('whip_pan_blur', 0.04, 0.08, dict(direction='left')),       # 第七棒：十字斩的余势甩进刀身横扫（甩镜方向 = 挥刀方向）
    'C34': ('match_cut', 0.04, 0.10, dict(shape='line', center=(800, 570), angle=-31, feather=40, glow=(0.85, 0.92, 1.0))),   # 第七棒：刀线 → 刀线（C34 斜劈沿这条线裂开长出）
    'C35': ('smoke_through', 0.06, 0.12, dict(direction=-1, density=1.1, color=(0.40, 0.38, 0.36))),   # 第七棒：巨印压下扬起泥尘冲过镜头
    'C35b': ('hard', 0, 0, {}),                                          # 同轴跳切：全身硬扛 → 中近景咬牙（「扛」）
    'C36': ('flash_red', 0.0, 0.12, dict(one_frame=True)),               # 扛印 → 1 帧朱闪 → 全景
    'C37': ('bolt_split', 0.04, 0.12, dict(x0=1000, seed=37)),          # 第十二棒（白闪同质化）：整幅过曝 → 「天」那道雷竖着劈开画面，御匾从雷缝里展开   # 第七棒：「天」那道闪电过曝 → 雷光照出御匾
    'C38': ('ink_bleed', 0.05, 0.12, {}),                                # 第五棒：斩开的匾缝墨渗 → 握刀手（去掉擦除边缘亮线）
    'C39': ('hard', 0, 0, {}),
    'C40': ('whip_pan_blur', 0.05, 0.10, dict(direction='right')),     # 第七棒：蓄力 → 甩出去的那一刀（甩镜 = 出刀）
    'C40b': ('slash_wipe', 0.04, 0.12, dict(angle=-3, center=(960, 330))),   # 第七棒：沿 C40 横断天平的刀线斩开 → 回头面部特写（「是我」）
    'C41': ('tip', 0.06, 0.14, dict(center=(1560, 880))),   # 第七棒：穿过刀尖光点（c_trans.tip：星芒 + 圆形开口；zoom_through glint 中点是整白帧，弃用）→ 收刀定格（「的回答」）
}
if R5:
    CUTS['C03'] = ('whip', 0.06, 0.08, dict(direction=1))       # r5 返工 #36：甩镜缩短（0.10/0.12 → 0.06/0.08），121.0 前完全落在 C03
# 第七棒（critic_C_r3 转场：硬切只靠同一种推近提亮，花样单一）：硬切冲击分 4 种，按镜头内容选——
# flash 电白闪（雷/光）、slam 下砸（重物落下：竖向震 + 赤热色偏）、zoom 冲推（径向模糊）、ink 墨眨（落拍那帧压黑再弹亮）
HARD_FX = {'C06': 'slam', 'C10': 'flash', 'C15': 'flash', 'C17': 'slam', 'C19': 'zoom', 'C22': 'strike', 'C25': 'zoom',
           'C29': 'quake', 'C31': 'slam', 'C35b': 'slam', 'C39': 'strike'}   # 第十棒 P2⑧：三处 ink（全黑暗角压场）→ strike
BREATH = {'C16': 3, 'C07': 2}      # 进副歌 / 进「我不低头」前压暗吸气（帧）

# 每镜运镜（叠加在镜头内运动上）：z 推拉、x/y 平移、rot 滚转、hh 手持幅度、ease
MOV = {
    'C01': dict(z=(1.0, 1.04)), 'C02': dict(z=(1.0, 1.06), hh=4), 'C03': dict(z=(1.0, 1.06), rot=(-2, 1), hh=3),
    'C04': dict(z=(1.0, 1.08), x=(-30, 30)), 'C05': dict(), 'C06': dict(z=(1.0, 1.05)),
    'C07': dict(z=(1.0, 1.08), hh=5), 'C08': dict(z=(1.0, 1.05), hh=3), 'C09': dict(z=(1.04, 1.0), y=(30, -30), rot=(3, 1), hh=6),
    'C10': dict(z=(1.0, 1.05), x=(0, 40)), 'C11': dict(z=(1.0, 1.03)), 'C12': dict(z=(1.0, 1.08), rot=(0, -2)),
    'C13': dict(), 'C14': dict(z=(1.0, 1.06), y=(-20, 10), hh=4), 'C15': dict(z=(1.0, 1.04), y=(40, -20)),
    'C16': dict(z=(1.0, 1.08)), 'C17': dict(z=(1.03, 1.0), y=(-40, 0), hh=6), 'C18': dict(z=(1.0, 1.12), hh=8),
    'C19': dict(z=(1.0, 1.05), rot=(-3, 3), hh=6), 'C20': dict(z=(1.0, 1.1)), 'C21': dict(z=(1.0, 1.03)),
    'C22': dict(z=(1.0, 1.05), rot=(-1.5, 0.5)), 'C23': dict(z=(1.0, 1.12)), 'C24': dict(hh=7),
    'C25': dict(z=(1.0, 1.06), hh=4), 'C26': dict(z=(1.1, 1.0)), 'C27': dict(z=(1.0, 1.06)),
    'C28': dict(z=(1.0, 1.06)), 'C29': dict(z=(1.08, 1.0), hh=4), 'C30': dict(z=(1.0, 1.08), hh=6),
    'C31': dict(z=(1.0, 0.95), hh=6), 'C32': dict(z=(1.0, 1.06), hh=5), 'C33': dict(z=(1.04, 1.0), hh=8),
    'C34': dict(z=(1.0, 1.06), rot=(3, -2), hh=6), 'C35': dict(z=(1.0, 1.05), y=(-30, 10), hh=4), 'C35b': dict(z=(1.0, 1.0), y=(0, -12), hh=7),
    'C36': dict(z=(1.0, 1.04), y=(30, -20)), 'C37': dict(z=(1.0, 1.08)), 'C38': dict(z=(1.0, 1.04)),
    'C39': dict(z=(1.0, 1.10), hh=3), 'C40': dict(z=(1.0, 1.08), hh=7), 'C40b': dict(z=(1.06, 1.0), hh=4), 'C41': dict(z=(1.0, 1.12)),
}
EXPO = {'C13': 1.0, 'C28': 1.0, 'C06': 0.9}
EXPO_ALL = 1.22

# 段内重拍冲击（副歌二）：底鼓强拍 → 推镜 1.5% + 抖 3px（克制，按副歌一 v3 用户意见）
KICKS = [h['t'] for h in K.HM['hits'] if h['t'] >= 134.4 and 'kick' in h['type'] and h['strength'] >= 0.72]

# 插入闪切（帧, 帧数, 类型）：副歌里鼓加花处
INSERTS = {}
for _t, _n, _k in ((131.96, 1, 'neg'), (133.79, 1, 'neg'),
                   (140.205, 1, 'white'), (140.408, 2, 'neg'), (148.54, 1, 'white'), (155.385, 2, 'neg'),
                   (160.238, 1, 'white'), (160.679, 2, 'neg')):
    for _i in range(_n): INSERTS[round(_t * FPS) - 1 + _i] = _k


# ---------------- 歌词（屏幕层，字随镜头轻漂）。C01–C03、C06、C10、C20–C23、C25、C28、C37、C38 的字是画内物体，不在此表。
S = Sent
SENTS = [
    # 预副歌二：铅字打字机（权力的话）
    S(29, [0, 1, 2, 3], 1275, 560, size=128, sizes=[128, 128, 146, 146], track=0.05, mode='type', glitch='正义', gold='正义', exit='glitch', out=V(122.79), back=0.45),   # 第十棒 P1①：铸字 128/146px（字高 ≥110），错位只闪 2 帧，去光标   # 第九棒 P1④：左下角 → 画面中心（秤杆下、立柱与右盘吊绳之间），「正义」金                 # 谁的正义（C04）
    S(29, [4, 5, 6, 7, 8], 960, 262, size=128, sizes=[128, 128, 146, 146, 128], track=0.05, back=0.5, mode='type', glitch='交易', gold='交易', exit='glitch', out=V(123.90)),   # 第十棒 P1①：同上   # 第五棒：延续进 C06 前 6 帧，「的」不断档；第九棒 P1④：右上角 → 箱口正上方视线中心  # 成了交易的（C05）
    # 「我不低头」起：他自己的重字（Black，朱红「不」逐拍落下）
    S(30, [0, 1, 2, 3], 420, 330, size=96, mode='fly', layout='v', red='不', exit='shatter', out=V(125.62), track=0.12),
    S(30, [4, 5, 6], 1640, 540, size=120, mode='fly', layout='v', red='不命', exit='cut', out=V(126.22), track=0.12, back=0.7, sizes=[110, 110, 150]),   # 第五棒：脸偏左、字竖排右侧鬓发暗区（不压脸），切点前才收
    S(30, [7, 8, 9, 10], 1560, 300, size=86, mode='fly', layout='v', red='不', exit='shatter', out=V(127.36), track=0.12),
    S(31, [0, 1, 2, 3], 960, 250, size=78, mode='fly', red='刀', exit='shatter', out=V(130.10)),
    S(31, [4, 5, 6, 7], 960, 860, size=110, mode='fly', red='发烫', exit='cut', out=V(131.50), back=0.5),   # 第十二棒：碎裂残片拖进 C13 成了平面多边形贴片 → 切点前干净收
    # 副歌二：kinetic 飞入 + 碎裂
    S(32, [1, 2], 1500, 860, size=70, mode='fly', exit='shatter', out=V(135.55)),                                    # 未冷（C16）
    S(32, [3, 4, 5], 960, 260, size=120, mode='fly', red='刀', exit='shatter', out=V(137.40), track=0.25),           # 刀不放
    S(33, [0, 1, 2], 560, 300, size=100, mode='fly', exit='shatter', out=V(138.33), offs=[(0, 0), (40, 60), (80, 120)]),   # 谁人来（斜）
    S(33, [6, 7], 960, 815, size=150, mode='fly', exit='shatter', out=V(140.62), track=0.45, back=0.85),   # 第十棒 P2⑦：112→150px、暗衬加深，「一」在邪侧「方」在正侧，分屏线从两字间穿过   # 第九棒 P2⑧：76→112px + 暗衬                        # 一方
    S(34, [6, 7], 1560, 470, size=260, mode='fly', exit='shatter', out=V(144.70), sizes=[170, 260], back=0.4),   # 第五棒：补「铜」（143.48 落在 C24 开头，原来丢字）                                      # 墙（C24 低频震）
    S(35, [0, 1], 460, 300, size=84, mode='fly', exit='shatter', out=V(145.60), layout='v'),                        # 那就（C25）
    S(35, [3, 4], 1480, 830, size=84, mode='fly', exit='shatter', out=V(146.40)),                                    # 开它
    S(35, [5, 6, 7], 1560, 300, size=100, mode='fly', layout='v', exit='cut', out=V(147.38), track=0.3, back=0.6),    # 看个天（竖排压在暗墙上）
    S(36, [0, 1, 2], 1600, 230, size=150, mode='fly', layout='v', red='血', exit='shatter', out=V(150.22), track=0.05,
      sizes=[220, 110, 110]),                                                                                          # 血未冷（C30）
    S(36, [3, 4, 5], 1560, 500, size=110, mode='fly', red='骨', exit='shatter', out=V(151.62)),                       # 骨未凉（C31）
    # 第五棒：「是非对错」改为画内刀光残影字（C32–C34），不再走屏幕层
    S(37, [4, 5, 6, 7], 1500, 800, size=100, mode='fly', red='扛', exit='shatter', out=V(155.25), sizes=[96, 96, 96, 190], back=0.6),   # 我自己扛（C35 → C35b）
    S(38, [0, 1], 960, 262, size=130, mode='fly', exit='shatter', out=V(156.38), track=0.3, back=1.0),             # 天不（暗衬，压在闪电天上可读）
    S(39, [0, 1], 1560, 720, size=100, mode='fly', exit='shatter', out=V(159.64), back=0.5),   # 第七棒 P2⑯：移出 C40 人物衣摆                         # 这一
    S(39, [2, 3, 4, 5], 1400, 290, size=110, mode='fly', red='刀', exit='shatter', out=V(160.30), track=0.2, lead=0.06),   # 第十棒 P2⑩：lead 0.20→0.06，「就」不再在「这一」未收时半透明提前出现        # 刀就是我
    S(39, [6, 7], 1330, 196, size=92, mode='fly', exit='glitch', out=V(161.20), track=0.2, back=0.5),   # 第八棒 P1①：横排压在「答」正上方，自上而下读「的回→答」   # 第六棒：的回（「答」由 C41 刀痕引燃、烧穿画面，画内字）
]
if R5:
    # 第五轮 #37/#39/#42/#43：2:02–2:28 与 2:37–2:41 的屏幕层字全部去掉；只留用户没提到的 2:30–2:36「血未冷 / 骨未凉 / 我自己扛 / 天不」
    SENTS = [s for s in SENTS if s.li in (36, 37, 38)]


def _on(k, d='1'): return os.environ.get(k, d) != '0'


# 第六轮 #53（2026-11-10 用户：「竖排歌词要全部去掉，因为我们改成横排了」）：屏幕层竖排歌词（layout='v'）全去，
# 歌词统一走底部横排字幕 units/subtitle.py。R5_NOVLYR=0 回滚到第五轮现状。
# 本段 C_R5=1 时只剩 2:30「血未冷」一条竖排；横排屏幕字「骨未凉 / 我自己扛 / 天不」与画内字（谁定好规矩、剧本提纲/纲、
# 大局为上、水中血、正邪、是非对错、判）一律不动——横排的是否也去，待问用户（crew/round6/VLYR_cde.md）。
NOVLYR = _on('R5_NOVLYR')
if NOVLYR:
    SENTS = [s for s in SENTS if s.layout != 'v']


# 第四棒：碎裂/故障出场不许跨切点（评审：切点帧上的碎字残片像出错）——出场在下一切点前收完，最短 0.12s
_CUTS_S = [f / FPS for f in CUT_F[1:-1]]
for _s in SENTS:
    _nx = next((c for c in _CUTS_S if c > _s.out - 1e-6), None)
    if _s.exit == 'cut':                       # 第五棒：「cut」出场 = 下一切点前一帧干净收掉，不拖进下一镜
        _nx2 = next((c for c in _CUTS_S if c > _s.tin[-1] + 1e-6), None)
        if _nx2 is not None: _s.out = min(_s.out, _nx2 - 1 / FPS)
        _s.exit_len = 1 / FPS
        continue
    if _nx is None: continue
    if _nx - _s.out < 0.30:
        if _nx - _s.out < 0.12: _s.out = _nx - 0.12
        _s.exit_len = max(0.12, _nx - _s.out - 1 / FPS)


# 第五棒（评审 P0 碎字残片）：字层不许早于它首字所在镜头的切点出现（上一镜/转场过渡帧只带出镜那一镜自己的字）
for _s in SENTS:
    _j = max([0] + [j for j, c in enumerate(_CUTS_S, 1) if c <= _s.tin[0] + 1e-6])
    _post = CUTS.get(SHOTS[_j].__name__, ('hard', 0, 0))[2] if _j else 0
    _s.t_start = (CUT_F[_j] / FPS) + 0.6 * _post        # 带内容转场：等入镜画面占上风再出字


class _Lazy:
    def __init__(self, cls): self.cls = cls; self.t0 = cls.t0; self.t1 = cls.t1; self.obj = None; self.id = cls.__name__
    def render(self, t):
        if self.obj is None: self.obj = self.cls()
        fr = self.obj.render(t)
        return np.clip(fr, 0, 6).astype(np.float32), getattr(self.obj, 'ca', 0)


class Sec:
    def __init__(self):
        self.shots = [_Lazy(s) for s in SHOTS]; self.ids = [s.__name__ for s in SHOTS]

    def idx(self, t):
        for i, s in enumerate(self.shots):
            if t < s.t1 - 1e-6: return i
        return len(self.shots) - 1

    def move(self, i, t, fr):
        s = self.shots[i]; m = MOV.get(self.ids[i], {}); u = clamp((t - s.t0) / (s.t1 - s.t0)); e = eio(u)
        z = lerp(*m.get('z', (1, 1)), e); x = lerp(*m.get('x', (0, 0)), e); y = lerp(*m.get('y', (0, 0)), e)
        rot = lerp(*m.get('rot', (0, 0)), e)
        hx, hy = handheld(t, m.get('hh', 0), seed=i)
        # 重拍冲击
        pk = sum(pulse(t, V(k), 0.10) for k in KICKS if 0 <= t - V(k) < 0.4)
        z *= 1 + 0.015 * min(1.5, pk)
        sx, sy = handheld(t * 7, 3 * min(1.5, pk), seed=99)
        return camxf(fr, z, x + hx + sx, y + hy + sy, rot), (x + hx, y + hy, z)

    def shot_frame(self, i, t):
        fr, ca = self.shots[i].render(t)
        fr, cm = self.move(i, t, fr)
        return fr, ca, cm

    def raw(self, t):
        i = self.idx(t); s = self.shots[i]
        for j in (i, i + 1):
            if j <= 0 or j >= len(self.shots): continue
            b = self.shots[j]; name, pre, post, kw = CUTS.get(self.ids[j], ('hard', 0, 0, {}))
            c = b.t0
            if name == 'hard' or not (c - pre - 1e-6 <= t < c + post - 1e-6): continue
            B, cb, cm = self.shot_frame(j, t)
            A, caa, _ = self.shot_frame(j - 1, t) if (pre > 0 or t < c) else (B, 0, cm)
            p = (t - (c - pre)) / (pre + post)
            if pre == 0: p = 0.5 + 0.5 * p
            if name == 'match_line':
                out = B.copy() if t >= c else A
                k = (t - c) / max(post, 1e-3)
                out = out + np.exp(-((np.arange(W)[None, :] - 900) / 6.0) ** 2)[..., None] * RED * 1.5 * (1 - k)
                return out, max(caa, cb), cm
            if name in CX.NAMES: out = CX.NAMES[name](np.clip(A, 0, 4), np.clip(B, 0, 4), p, **kw)
            else: out = TR.transition(name, np.clip(A, 0, 4), np.clip(B, 0, 4), p, **kw)
            return out, max(caa, cb, 2), cm
        fr, ca, cm = self.shot_frame(i, t)
        if i + 1 < len(self.shots) and self.ids[i + 1] in BREATH:      # 吸气：切点前 n 帧压暗
            n = BREATH[self.ids[i + 1]]; k = (self.shots[i + 1].t0 - t) * FPS
            if 0 < k <= n + 1e-6: fr = CX.dark_breath(fr, min(1.0, (n + 1 - k) / n))
        name = CUTS.get(self.ids[i], ('hard',))[0]
        if name == 'hard' and i > 0:
            # 第五棒（评审 P1「硬切没有冲击」）：切后 3 帧 = 电白闪 + 8px 抖 + 推近 + 色偏，强度 1 / 0.5 / 0.2
            k = int((t - s.t0) * FPS + 1e-6)
            if k < 3:
                a = (1.0, 0.5, 0.2)[k]
                st = HARD_FX.get(self.ids[i], 'flash')
                r_ = np.random.default_rng(i * 7 + k).uniform(-1, 1, 2) * 8 * a
                if st == 'slam':
                    dy = (22, -9, 3)[k]
                    fr = camxf(fr, 1 + 0.045 * a, r_[0] * 0.4, dy) * (1 + 0.35 * a) + 0.09 * a * np.array([1.0, 0.38, 0.18], np.float32)
                elif st == 'zoom':
                    fr = TR._radial_blur(camxf(fr, 1 + 0.07 * a, 0, 0), (W / 2, H / 2), 0.05 * a) * (1 + 0.3 * a)
                elif st == 'strike':     # 第十棒（critic_C_r5 P2⑧）：白闪 1 帧（保留画面结构）→ 朱红偏 + 横抖 → 回正
                    if k == 0:
                        fr = camxf(fr, 1.05, r_[0] * 1.4, r_[1] * 0.6) * 1.75 + 0.06 * np.array([0.92, 0.96, 1.0], np.float32)
                    else:
                        sx_ = (14, -5)[k - 1]
                        fr = camxf(fr, 1 + 0.025 * a, sx_, r_[1] * 0.5) * (1 + 0.25 * a)
                        fr = fr * np.array([1 + 0.30 * a, 1 - 0.12 * a, 1 - 0.18 * a], np.float32) + 0.05 * a * np.array([0.9, 0.12, 0.06], np.float32)
                elif st == 'quake':      # 第十二棒（critic_C_r6 P2⑦）：不提亮——落拍地震：竖向大抖 + 竖向拖影 + 轻压暗，朱偏只在第 1 帧
                    dy = (26, -14, 5)[k]
                    g = camxf(fr, 1 + 0.03 * a, r_[0] * 0.6, dy)
                    g = (g + camxf(fr, 1 + 0.03 * a, r_[0] * 0.6, dy * 0.4) + camxf(fr, 1 + 0.03 * a, r_[0] * 0.6, dy * 1.6)) / 3
                    fr = g * (1 - 0.12 * a)
                    if k == 0: fr = fr * np.array([1.18, 0.92, 0.88], np.float32)
                elif st == 'ink':
                    fr = ink_vignette(fr, 0.85) * 0.75 if k == 0 else camxf(fr, 1 + 0.03 * a, r_[0], r_[1]) * (1 + 0.6 * a)
                else:
                    fr = camxf(fr, 1 + 0.035 * a, r_[0], r_[1]) * (1 + 0.55 * a) + 0.07 * a * np.array([0.92, 0.96, 1.0], np.float32)
                ca = max(ca, (7, 4, 2)[k])
        return fr, ca, cm

    def frame(self, f):
        t = f / FPS
        fr, ca, cm = self.raw(t)
        ins = INSERTS.get(f)
        if ins == 'white': fr = fr * 1.9 + 0.04 * np.array([0.9, 0.95, 1.0], np.float32); ca = max(ca, 3)   # 电光过曝（保留画面结构，不是白帧）
        elif ins == 'neg':
            l = np.clip(fr.mean(-1, keepdims=True), 0, 1)
            fr = fr * 0.45 + np.clip(1.0 - l * 1.6, 0, 1) ** 2 * np.array([0.55, 0.05, 0.04], np.float32); ca = max(ca, 5)   # 朱红负片叠原画（保留结构，不是色卡）
        sid = self.ids[self.idx(t)]
        # 第六棒（critic_C_r3 P0④）：RGB 分离只留 C04 glitch_cut（含入切前 0.07s）和 INSERTS 闪切帧，其余一律关掉（原来成了底噪）
        if not ins: ca = 0   # 第十二棒：C04 入切改纸撕，色差只留 INSERTS 闪切帧
        fr = fr * (EXPO_ALL * EXPO.get(sid, 1.0))
        fr = fr + 0.014 * (1 - np.clip(fr, 0, 1))
        dx, dy, z = cm
        for s in SENTS:
            if max(s.tin[0] - s.lead - 0.05, s.t_start) <= t < s.out + 0.32:
                fr = draw_sent(fr, s, t, cam=(dx * 0.35, dy * 0.35, 1 + (z - 1) * 0.35))
        # 段尾：最后 4 帧切黑（接 Bridge 白纸虚空，由 D 组白闪入）
        if f >= F1 - 4:
            fr = TR.freeze_glitch(fr, None, 0.6 + 0.1 * (f - (F1 - 4)), seed=f) * (0.3 if f >= F1 - 2 else 1.0)
        out = finish(fr, t, ca=ca, vig=0.40, bloom_amt=0.42, red_keep=1.0)
        return out


_SEC = [None]
def frame(f, cache):
    if _SEC[0] is None: _SEC[0] = Sec()
    return to8(_SEC[0].frame(int(f)))


if __name__ == '__main__':
    from PIL import Image
    ts = [float(x) for x in sys.argv[2:]]
    for t in ts:
        Image.fromarray(frame(round(t * FPS), {})).save(f'{sys.argv[1]}_{t:.2f}.png')
        print(t, flush=True)
