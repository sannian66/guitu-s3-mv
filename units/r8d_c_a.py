"""units/r8d_c_a.py — 第八轮风格 D · CA 单元：Pre-Chorus 二 + 副歌二前半 C01–C21（帧 3534–4218）。
只在 STYLE_D=1 时由 sec_c_pre2_chorus2.py 末尾钩子 import，apply(mod) 替换 mod.SHOTS 里 C01–C21 的镜头类；STYLE_D=0 不加载。
切点 / 镜长 / 入出转场 / 字幕 / 段内 KICKS 与 HARD_FX 冲击全部沿用 sec_c（CUT_F 实表），本模块只换每镜的画面。

素材：assets/gen/R8_D/CA/（nananobanana RH_image2 2K，提示词 jobs/r8_D_CA.json，记录 crew/round8/genlog_CA.md）。
  背景板 *.jpg：CA_room 烛光暗殿 / CA_sky 雷暴天 / CA_water 雷暴积水原 / C03_screen 皮影幕 / C08_eyes 眼部大特写 / C10_eave 雨夜宫檐 /
               C13_vortex 风暴之眼 / C21_split 邪正分天（字画在生图里）
  抠像 *_cut.png：人物 C07/C09×2/C14/C15×2/C17/C18_draw/C19_spin（鬼屠，定妆照参考）、C20_emp、C02_hand（太上皇，太上皇定妆照参考）；
               道具 C01_paper（「谁定好规则」画在纸上）、C02_tags（「谁写好剧本提纲」七块木签）、C10_tablets（「大局为上」四块匾）、
               C16_blood（水中血字「血」）、C03_puppets、C04_balance、C04_seal、C05_box、C06_lid、C11_blade、C18_soldiers、C19_spear；
               特效 CA_rain（前景墨线雨）、CA_slash（干笔飞白刀痕）
用户点名（crew/round8/USER_NOTES_r8.md）：
  保留并画进生图：C01「谁定好规则」、C02「谁写好剧本提纲」、C09/C10「大局为上」、C16「血」、C21「邪」「正」；其余画面字全部去掉（本段本来就无屏幕叠字）。
  C15「跳斩太丑了，换个形式」→ 不跳：雷暴积水原上立定 → 133.79 一记血振（chiburi），血珠被慢放悬停在空中，下一镜（C16）刀尖滴血入水成「血」。
代码只做：字的显影（墨迹逐字洇出 / 朱圈一笔圈出 / 水中血字洇开）、运镜、分层视差、刀光、雷、雨、火星、震屏；不叠任何字体字。
防漂移：每镜位移以镜头中点为零（_par），人物按包围盒高度落脚（fit），同一物体只用一个刚体层（天平拆成「立柱 / 横梁 / 两只秤盘」铰接件）。"""
import os, sys, math
import numpy as np, cv2

ROOT = os.environ.get('MV_ROOT', '/workspace/work/mv')
for _p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if _p not in sys.path: sys.path.insert(0, _p)
import c_kit as K
from c_kit import W, H, FPS, BAR, clamp, sm, eout, ein, eio, lerp, V, pulse, CT, bolt, bolt_env
import sprite as SP
import fx2
import c1kit as C1
from c1kit import sparks, dust, shake, motion_blur, blur_ds

A_DIR = ROOT + '/assets/gen/R8_D/CA/'
MINE = ['C%02d' % i for i in range(1, 22)]
NEU = dict(expo=1.0, sat=1.0, tint=(1.0, 1.0, 1.0), lift=0.0, gamma=1.0)
NORIM = dict(col=(1.0, 1.0, 1.0), amt=0.0, dir=(0.0, -1.0))
WHITE = (1.0, 1.0, 1.0)
BRED = (0.82, 0.04, 0.03)          # 血红（火星 / 血珠）
INK = np.array([0.015, 0.015, 0.015], np.float32)


# ===================================================================================== 素材
_PL = {}
def plate(name, gain=1.0, recede=0.0, size=(W, H), flip=False):
    """背景板。recede>0：远景用「降反差 + 网点」渐隐做纵深（SPREAD §11：不用景深虚化）；flip：水平镜像（跨镜复用时换机位）。"""
    k = (name, gain, recede, size, flip)
    if k not in _PL:
        im = cv2.cvtColor(cv2.imread(A_DIR + name + '.jpg'), cv2.COLOR_BGR2RGB)
        im = cv2.resize(im, size, interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        if flip: im = np.ascontiguousarray(im[:, ::-1])
        if recede: im = tone_recede(im, recede)
        _PL[k] = im * gain
    return _PL[k]


_DOT = {}
def dots(h=H, w=W, pitch=7.0):
    """45° 漫画网点底纹（-1..1），网点密度用阈值控制"""
    k = (h, w, pitch)
    if k not in _DOT:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        u = (xx + yy) / math.sqrt(2); v = (xx - yy) / math.sqrt(2)
        _DOT[k] = ((np.cos(2 * math.pi * u / pitch) + np.cos(2 * math.pi * v / pitch)) / 2).astype(np.float32)
    return _DOT[k]


def tone_recede(im, amt):
    """远景渐隐：反差压向中灰 + 一层细网点（清晰墨线仍在，只是退远）"""
    h, w = im.shape[:2]
    lum = im.mean(-1, keepdims=True)
    out = im * (1 - 0.45 * amt) + (0.30 + 0.25 * lum) * 0.45 * amt
    d = dots(h, w, 6.0)
    dm = np.clip((d - 0.55) / 0.15, 0, 1)[..., None]
    return out * (1 - 0.18 * amt * dm) + 0.10 * amt * dm * (lum < 0.3)


def halo_tone(fr, c, r, amt, col=(1.0, 1.0, 1.0)):
    """网点光晕（代替柔光辉光 / 镜头光斑）：越近中心网点越密越亮，边缘是一颗颗清楚的网点"""
    if amt <= 0.005: return fr
    x, y = _grid()
    g = np.exp(-(((x - c[0]) ** 2 + (y - c[1]) ** 2) / (r * r)))
    d = dots(pitch=8.0)
    m = np.clip((d - (1 - 2 * g * min(1.0, amt * 1.4))) / 0.12, 0, 1) * min(1.0, amt * 1.6)
    return fr * (1 - m[..., None] * 0.55) + m[..., None] * np.asarray(col, np.float32) * 0.85


def view(img, z=1.0, ox=0.0, oy=0.0, rot=0.0, c=None, border=cv2.BORDER_REFLECT):
    """背景板取景：以 c（默认画面中心）为中心缩放 z、旋转 rot，再平移 (ox, oy)。img 可比画面大（按自身中心对齐画面中心）。"""
    ih, iw = img.shape[:2]
    cx, cy = c or (W / 2, H / 2)
    M = cv2.getRotationMatrix2D((iw / 2, ih / 2), rot, z)
    M[0, 2] += cx - iw / 2 + ox; M[1, 2] += cy - ih / 2 + oy
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=border)


def spr(name):
    return SP.layer(A_DIR + name + '_cut.png')


def put(fr, sp, t, h, foot, wind=6.0, rot=0.0, mblur=(0, 0), alpha=1.0, defocus=0.0, breathe=0.004, extra_A=None, rotblur=0.0):
    """人物：按包围盒高度 h 把脚底中点落到 foot（屏幕像素）。风格 D 一律 grade=NEU / rim=NORIM / wrap=0 / shade=None。"""
    a, s = sp.fit(h)
    return sp.draw(fr, t, a, foot, s, rot=rot, breathe=breathe, wind_amp=wind, grade=NEU, rim=NORIM, wrap=0, shade=None,
                   mblur=mblur, alpha=alpha, defocus=defocus, extra_A=extra_A, rotblur=rotblur)


def put_src(fr, sp, t, src, dst, width, wind=5.0, rot=0.0, mblur=(0, 0), alpha=1.0, defocus=0.0, breathe=0.004, extra_A=None):
    """按精灵内归一化锚点 src 落到屏幕 dst；width = 精灵整幅宽在屏幕上的像素。"""
    return sp.draw(fr, t, src, dst, width / sp.w, rot=rot, breathe=breathe, wind_amp=wind, grade=NEU, rim=NORIM, wrap=0, shade=None,
                   mblur=mblur, alpha=alpha, defocus=defocus, extra_A=extra_A)


class Prop:
    """刚体道具层（不吹风、不呼吸）：预乘 RGBA，按仿射摆放；可按 alpha 连通域 / 矩形裁出子件（同一张生图拆成铰接件）。"""
    def __init__(self, name, box=None, mask=None, work=1.0):
        im = cv2.imread(A_DIR + name + '_cut.png', cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
        F = np.ascontiguousarray(im[..., 2::-1]); A = im[..., 3].copy()
        if mask is not None: A = A * mask
        if box is not None:
            x0, y0, x1, y1 = box; F = F[y0:y1, x0:x1]; A = A[y0:y1, x0:x1]; self.off = (x0, y0)
        else:
            self.off = (0, 0)
        if work != 1.0:
            F = cv2.resize(F, None, fx=work, fy=work, interpolation=cv2.INTER_AREA); A = cv2.resize(A, None, fx=work, fy=work, interpolation=cv2.INTER_AREA)
        self.work = work
        self.FA = np.ascontiguousarray(F * A[..., None]); self.A = np.ascontiguousarray(A); self.F = F
        self.h, self.w = A.shape

    def src(self, x, y):
        """原图（2048 宽）像素坐标 → 本层像素坐标"""
        return ((x - self.off[0]) * self.work, (y - self.off[1]) * self.work)

    def M(self, anchor, dst, scale, rot=0.0):
        M = cv2.getRotationMatrix2D((float(anchor[0]), float(anchor[1])), rot, scale / self.work)
        M[0, 2] += dst[0] - anchor[0]; M[1, 2] += dst[1] - anchor[1]
        return M

    def draw(self, fr, anchor, dst, scale, rot=0.0, alpha=1.0, blur=0.0, mblur=None, gain=1.0, M=None, persp=None):
        """anchor：本层像素坐标；scale：原图像素 → 屏幕像素。persp=3×3 透视矩阵（优先）。返回 (fr, Aw)。"""
        if persp is not None:
            FA = cv2.warpPerspective(self.FA, persp, (W, H), flags=cv2.INTER_LINEAR)
            Aw = cv2.warpPerspective(self.A, persp, (W, H), flags=cv2.INTER_LINEAR)
        else:
            M = self.M(anchor, dst, scale, rot) if M is None else M
            FA = cv2.warpAffine(self.FA, M, (W, H), flags=cv2.INTER_LINEAR)
            Aw = cv2.warpAffine(self.A, M, (W, H), flags=cv2.INTER_LINEAR)
        if mblur is not None and math.hypot(*mblur) >= 2:
            FA = motion_blur(FA, mblur[0], mblur[1], 2); Aw = motion_blur(Aw, mblur[0], mblur[1], 2)
        if blur > 0.3:
            FA = cv2.GaussianBlur(FA, (0, 0), blur); Aw = cv2.GaussianBlur(Aw, (0, 0), blur)
        Aw = np.clip(Aw * alpha, 0, 1)
        return fr * (1 - Aw[..., None]) + FA * (alpha * gain), Aw


_CMP = {}
def comps(name, n_expect, min_area=3000, ybox=None):
    """抠像里的各个独立物件（连通域），按 x 排序，返回 [(box, mask)]；件数不足直接报错（换图后防静默错位）"""
    k = (name, min_area, ybox)
    if k not in _CMP: _CMP[k] = _comps(name, min_area, ybox)
    out = _CMP[k]
    if len(out) < n_expect: raise RuntimeError(f'{name}: 只分出 {len(out)} 个物件，需要 {n_expect}')
    return out[:n_expect]


def _comps(name, min_area, ybox):
    im = cv2.imread(A_DIR + name + '_cut.png', cv2.IMREAD_UNCHANGED)
    a = im[..., 3]
    n, lab, st, _ = cv2.connectedComponentsWithStats((a > 60).astype(np.uint8), 8)
    out = []
    for i in range(1, n):
        x, y, w, h, ar = st[i]
        if ar < min_area: continue
        m = (cv2.dilate((lab == i).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0).astype(np.float32)
        if ybox: y, h = max(y, ybox[0]), min(y + h, ybox[1]) - max(y, ybox[0])
        out.append(((x, y, x + w, y + h), m))
    return sorted(out, key=lambda b: b[0][0])


# ===================================================================================== 风格 D 特效笔触
_SL = {}
def brush_slash(fr, p0, p1, q, width=1.0, flip=False, red=0.0, amt=1.0):
    """干笔飞白刀痕（生图 CA_slash）：把笔画弦（源 57,642 → 2015,526）对到 p0→p1，q 0..1 沿弦扫出，之后 0.6 内淡出。
    width：横向厚度倍率；flip：弧向另一侧鼓；red：整笔偏血红（0..1）。"""
    if q <= 0 or q > 1.6: return fr
    if 'p' not in _SL: _SL['p'] = Prop('CA_slash', work=0.5)
    P = _SL['p']
    a0 = np.array(P.src(57, 642)); a1 = np.array(P.src(2015, 526))
    d0 = a1 - a0; L0 = np.linalg.norm(d0); u0 = d0 / L0; n0 = np.array([-u0[1], u0[0]])
    p0 = np.asarray(p0, np.float64); p1 = np.asarray(p1, np.float64)
    d1 = p1 - p0; L1 = np.linalg.norm(d1); u1 = d1 / L1; n1 = np.array([-u1[1], u1[0]])
    s = L1 / L0
    Ms = s * np.outer(u1, u0) + s * width * (-1 if flip else 1) * np.outer(n1, n0)
    M = np.hstack([Ms, (p0 - Ms @ a0)[:, None]]).astype(np.float32)
    FA = cv2.warpAffine(P.FA, M, (W, H), flags=cv2.INTER_LINEAR); Aw = cv2.warpAffine(P.A, M, (W, H), flags=cv2.INTER_LINEAR)
    xx, yy = _grid()
    u = ((xx - p0[0]) * u1[0] + (yy - p0[1]) * u1[1]) / L1
    head = min(1.0, q * 2.6); fade = 1 - sm(0.55, 1.6, q)
    rev = np.clip((head - u) / 0.06, 0, 1) * fade * amt
    a = Aw * rev
    F = FA / np.clip(Aw[..., None], 1e-3, None)
    if red > 0:
        lum = F.mean(-1, keepdims=True)
        F = F * (1 - red) + (lum * np.array([1.0, 0.06, 0.05], np.float32) * 1.05) * red
    return fr * (1 - a[..., None]) + F * a[..., None]


def speed_lines(fr, t, seed, c=None, amt=0.6, n=70, dirx=None, r0=380):
    """漫画速度线（黑 + 白）。c 给定 = 集中线（指向 c）；否则 dirx 方向的横向速度线。"""
    if amt <= 0.01: return fr
    r = np.random.default_rng(seed + int(round(t * 30)))
    Lk = np.zeros((H // 2, W // 2), np.float32); Lw = np.zeros_like(Lk)
    for i in range(n):
        tgt = Lk if i % 3 else Lw
        if c is not None:
            ang = r.uniform(0, 2 * math.pi); ra = r.uniform(r0, r0 + 200); rb = ra + r.uniform(300, 900)
            p = (c[0] + math.cos(ang) * ra, c[1] + math.sin(ang) * ra); q = (c[0] + math.cos(ang) * rb, c[1] + math.sin(ang) * rb)
        else:
            y = r.uniform(140, 940); x = r.uniform(-200, W); ln = r.uniform(180, 700) * (dirx or 1)
            p, q = (x, y), (x + ln, y)
        cv2.line(tgt, (int(p[0] / 2), int(p[1] / 2)), (int(q[0] / 2), int(q[1] / 2)), r.uniform(0.4, 1.0), 1 if i % 4 else 2, cv2.LINE_AA)
    Lk = cv2.resize(cv2.GaussianBlur(Lk, (0, 0), 0.6), (W, H)); Lw = cv2.resize(cv2.GaussianBlur(Lw, (0, 0), 0.6), (W, H))
    fr = fr * (1 - np.clip(Lk * 0.85 * amt, 0, 1))[..., None]
    return fr + (Lw * 0.9 * amt)[..., None]


def sparks2(fr, t, seed, o, t0, n=40, dirc=(0, -1), spread=1.0, speed=(400, 1200), life=0.5, grav=900, area=(30, 20), amt=1.0):
    """火星：白 + 血红两色（风格 D）"""
    fr = sparks(fr, t, seed, o, n=n, life=life, speed=speed, dirc=dirc, spread=spread, grav=grav, burst=True, t0=t0, area=area,
                color=WHITE, amt=0.9 * amt)
    return sparks(fr, t, seed + 50, o, n=max(1, n // 2), life=life * 0.9, speed=(speed[0] * 0.8, speed[1] * 0.8), dirc=dirc, spread=spread,
                  grav=grav, burst=True, t0=t0, area=area, color=BRED, amt=1.0 * amt)


_RAINP = {}
def rain_fg(fr, t, seed=0, amt=0.6, speed=2200.0, scale=1.0, blur=0.0, cam=(0.0, 0.0), freeze=None):
    """前景墨线雨（生图 CA_rain：白 + 黑细划，长短粗细不一），沿雨向循环下落；cam = 视差偏移（以镜头中点为零）。
    freeze=(t_freeze)：之后雨悬停（慢放 0.04）。"""
    if 'p' not in _RAINP: _RAINP['p'] = Prop('CA_rain', work=0.5)
    P = _RAINP['p']
    if freeze is not None and t > freeze: t = freeze + (t - freeze) * 0.04
    d = np.array([-0.42, 1.0]); d /= np.linalg.norm(d)
    sw, sh = P.w * scale * 2, P.h * scale * 2           # 屏幕上一块平铺的尺寸
    off = d * speed * t + np.array(cam) + np.array([seed * 397.0, seed * 211.0])
    ox, oy = off[0] % sw, off[1] % sh
    M = np.float32([[scale * 2, 0, ox - sw], [0, scale * 2, oy - sh]])
    out_FA = np.zeros((H, W, 3), np.float32); out_A = np.zeros((H, W), np.float32)
    for i in range(3):
        for j in range(3):
            Mi = M.copy(); Mi[0, 2] += i * sw; Mi[1, 2] += j * sh
            if Mi[0, 2] > W or Mi[1, 2] > H or Mi[0, 2] + sw < 0 or Mi[1, 2] + sh < 0: continue
            out_FA += cv2.warpAffine(P.FA, Mi, (W, H)); out_A += cv2.warpAffine(P.A, Mi, (W, H))
    if blur > 0.3:
        out_FA = cv2.GaussianBlur(out_FA, (0, 0), blur); out_A = cv2.GaussianBlur(out_A, (0, 0), blur)
    a = np.clip(out_A * amt, 0, 1)
    return fr * (1 - a[..., None]) + out_FA * amt


def rain_code(fr, t, seed, inten=0.8, angle=-22, layers=None, cam=(0, 0), freeze=None):
    """中远景雨（代码细线，中性白）"""
    return K.rain(fr, t, seed, inten=inten, angle=angle, layers=layers, cam=cam, freeze=freeze, color=np.array([0.85, 0.85, 0.85], np.float32))


def mirror(fr, Aw, yf, amt=0.35, t=0.0, wob=4.0):
    """积水倒影：把 Aw 覆盖的主体沿 y=yf 翻下去（带横向水波抖动），只画在 yf 以下"""
    yf = int(yf)
    if yf <= 0 or yf >= H - BAR: return fr
    n = min(yf, H - yf)
    sub = (fr * Aw[..., None])[yf - n:yf][::-1]; a = Aw[yf - n:yf][::-1]
    ys = np.arange(n, dtype=np.float32)[:, None]
    gx = np.arange(W, dtype=np.float32)[None, :] + wob * np.sin(ys / 9.0 + t * 7) * np.clip(ys / 40, 0, 1)
    gy = np.broadcast_to(ys, (n, W)).astype(np.float32)
    gx = np.broadcast_to(gx, (n, W)).astype(np.float32)
    sub = cv2.remap(np.ascontiguousarray(sub), gx, gy, cv2.INTER_LINEAR); a = cv2.remap(np.ascontiguousarray(a), gx, gy, cv2.INTER_LINEAR)
    k = (amt * np.exp(-ys / (n * 0.6)))
    out = fr.copy()
    out[yf:yf + n] = out[yf:yf + n] * (1 - (a * k)[..., None]) + cv2.GaussianBlur(sub, (0, 0), 1.5) * k[..., None]
    return out


def ink_drop(fr, c, r=12, red=True):
    """墨线描边的血珠（漫画）"""
    lay = np.zeros((H, W), np.float32)
    cv2.circle(lay, (int(c[0] * 4), int(c[1] * 4)), int(r * 4), 1.0, -1, cv2.LINE_AA, 2)
    ink = np.clip(cv2.dilate(lay, np.ones((5, 5), np.uint8)) - lay, 0, 1)
    fr = C1.over(fr, ink, INK)
    return C1.over(fr, lay, np.array(BRED, np.float32) * 1.1 if red else WHITE)


def water_ripple(*a, **k):
    import sec_c_pre2_chorus2 as SC        # 运行时取（本模块在 sec_c 导入末尾才被加载，此时函数已定义）
    return SC.water_ripple(*a, **k)


def lit(fr, amt):
    """雷光提亮（中性）"""
    return fr * (1 + 0.55 * amt) + 0.05 * amt


_GR = {}
def _grid():
    """全画幅坐标网格（x, y），进程内只建一次"""
    if 'g' not in _GR: _GR['g'] = C1.grid()
    return _GR['g']


def _par(u, k):
    """视差偏移：镜头中点为零"""
    return k * (u - 0.5)


class Shot:
    t0 = t1 = 0.0; ca = 0
    def u(self, t): return clamp((t - self.t0) / (self.t1 - self.t0))


# ===================================================================================== 预副歌二：剧本 / 提线 / 皮影 / 天平 / 暗箱
class C01(Shot):
    """CU 剧本（保留字「谁定好规则」，画进生图）：烛光暗殿，一页旧宣纸斜铺在案上（俯拍透视），
    五个字随唱逐字由纸里洇出墨迹（谁 117.86 / 定 118.16 / 好 118.34 / 规 118.60 / 则 118.82，每字 3 帧由上而下洇开 + 纸面一记墨晕），
    118.58 起朱笔一笔圈住「规则」（生图里的朱圈按角度逐段露出），硬切 C02 时 match_line 红竖线接上提线。
    分层：L1 暗殿背景板（虚焦，视差 0.35）/ L2 宣纸（锁定主体，透视慢推 + 右移）/ L3 前景血红灯笼虚焦光斑 + 浮尘 / 代码：烛光闪烁。"""
    COLS = [(80, 510), (510, 817), (817, 1174), (1174, 1569), (1569, 1890)]
    def __init__(self):
        self.P = Prop('C01_paper')
        F = self.P.F; A = self.P.A
        lum = F.mean(-1); r, g, b = F[..., 0], F[..., 1], F[..., 2]
        redm = (((r - np.maximum(g, b)) / (r + 1e-3)) > 0.35) & (r > 0.2) & (A > 0.5)
        band = np.zeros_like(A, bool); band[230:800, 60:1900] = True
        ink = (lum < 0.42) & (A > 0.9) & band & ~redm
        self.red = cv2.GaussianBlur(cv2.dilate(redm.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 1.0)
        self.red[:, :900] = 0
        inkd = cv2.dilate(ink.astype(np.uint8), np.ones((7, 7), np.uint8))
        self.ink = cv2.GaussianBlur(inkd.astype(np.float32), (0, 0), 1.2)
        # 去字后的空白宣纸：半分辨率 inpaint（纤维纹理按周围补）
        hole = ((inkd > 0) | (cv2.dilate(redm.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)).astype(np.uint8)
        small = cv2.resize((np.clip(F, 0, 1) * 255).astype(np.uint8), (F.shape[1] // 2, F.shape[0] // 2), interpolation=cv2.INTER_AREA)
        hs = cv2.resize(hole * 255, (F.shape[1] // 2, F.shape[0] // 2), interpolation=cv2.INTER_NEAREST)
        cl = cv2.resize(cv2.inpaint(small, hs, 7, cv2.INPAINT_TELEA), (F.shape[1], F.shape[0])).astype(np.float32) / 255
        r0 = np.random.default_rng(101)
        fib = cv2.GaussianBlur(r0.random(A.shape).astype(np.float32), (0, 0), 0.8)[..., None]
        hf = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 2)[..., None]
        self.clean = F * (1 - hf) + (cl * (0.97 + 0.06 * fib)) * hf
        hh, ww = A.shape
        self.yy, self.xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
        ys, xs = np.nonzero(redm[:, 900:]); self.rc = (xs.mean() + 900, ys.mean())
        self.ang = (np.degrees(np.arctan2(self.yy - self.rc[1], (self.xx - self.rc[0]) * 0.45)) + 360 + 160) % 360   # 从左侧起笔，顺时针
        self.nz = cv2.resize(cv2.GaussianBlur(r0.random((hh // 8, ww // 8)).astype(np.float32), (0, 0), 1.5), (ww, hh))
        self.bg = plate('CA_room', 0.62, recede=0.5)
        self.tins = [V(CT(28, k)) for k in range(5)]
        self.colm = [((self.xx >= x0) & (self.xx < x1)).astype(np.float32) for x0, x1 in self.COLS]

    def render(self, t):
        u = self.u(t)
        R = np.zeros_like(self.ink)
        for cm, ti in zip(self.colm, self.tins):
            k = (t - ti) / (3 / FPS)
            if k <= 0: continue
            if k >= 1: R = np.maximum(R, cm); continue
            wipe = np.clip((k * 1.25 * 900 + 200 - self.yy) / 90 + (self.nz - 0.5) * 1.5, 0, 1)
            R = np.maximum(R, cm * wipe)
        Ri = (R * self.ink)[..., None]
        q = sm(V(118.58), V(118.58) + 0.30, t)
        Rr = (np.clip((q * 380 - self.ang) / 14, 0, 1) * self.red)[..., None] if q > 0 else 0.0
        F = self.clean * (1 - Ri) + self.P.F * Ri
        if q > 0: F = F * (1 - Rr) + self.P.F * Rr
        # 落字那一下：字周围纸面墨晕（湿墨吃纸）
        for (x0, x1), ti in zip(self.COLS, self.tins):
            pk = pulse(t, ti, 0.10) * (t >= ti)
            if pk > 0.02:
                cx = (x0 + x1) / 2
                g = np.exp(-(((self.xx - cx) / 260) ** 2 + ((self.yy - 520) / 230) ** 2))[..., None]
                F = F * (1 - 0.12 * pk * g)
        FA = F * self.P.A[..., None]
        # 透视：纸平铺在案上（俯 30°），慢推 1.00→1.10 + 右移
        z = 1.0 + 0.10 * eio(u); sx = -40 + 90 * eio(u)
        hh, ww = self.P.A.shape
        q0 = np.float32([[0, 0], [ww, 0], [ww, hh], [0, hh]])
        dst = np.float32([[250, 190], [1690, 205], [1860, 950], [70, 930]])
        dst = ((dst - [960, 540]) * z + [960 - sx, 540]).astype(np.float32)
        Mh = cv2.getPerspectiveTransform(q0, dst)
        fr = view(self.bg, 1.06 + 0.04 * u, -_par(u, 36), 0)
        flick = 1.0 + 0.05 * math.sin(t * 21) + 0.03 * math.sin(t * 37)
        fr = halo_tone(fr, (1560, 250), 520, 0.45 * flick)
        Pw = cv2.warpPerspective(FA, Mh, (W, H)); Aw = cv2.warpPerspective(self.P.A, Mh, (W, H))
        # 投影（纸压在案上）
        sh = cv2.GaussianBlur(Aw, (0, 0), 22)
        fr = fr * (1 - 0.55 * np.roll(sh, 18, 0))[..., None]
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        light = (0.80 + 0.22 * (1 - yy)) * flick
        fr = fr * (1 - Aw[..., None]) + Pw * light
        # 前景浮尘（不做焦外光斑：SPREAD §11）
        fr = dust(fr, t, 1011, n=50, amt=0.30, drift=(14, -10), size=(2, 5), color=(0.9, 0.9, 0.9), blur=2.0)
        return fr


class C02(Shot):
    """MS 提线（保留字「谁写好剧本提纲」，七字写在七块木签上，画进生图）：太上皇的手（太上皇定妆照）从画顶垂下，黑纱袖垂落，
    五指张开像牵木偶；每唱一个字，一块木签顺着红丝线从手里落下吊住（谁 118.98 / 写 119.26 / 好 119.50 / 剧 119.80 / 本 120.18 /
    提 120.36），「纲」在「本」后放线、正落「提」那拍（同 r6 #35，整句在本镜内一次写完）；逐拍提线（手往上一拽、木签被拽起）。
    分层：L1 暗殿背景板（虚焦）/ L2 太上皇手 + 黑纱袖（风吹纱摆、提线拽动）/ L3 七块木签（各自摆动、落下回弹）/ 代码：红丝线、打结、浮尘、暗角。"""
    def __init__(self):
        self.hand = spr('C02_hand')
        self.tags = [Prop('C02_tags', box=b, mask=m) for b, m in comps('C02_tags', 7)]
        self.bg = plate('CA_room', 0.55, recede=0.6, flip=True)          # 同殿换机位：镜像 + 上部裁切
        g = np.linspace(0, 1, H, dtype=np.float32)[:, None]
        nz = cv2.resize(cv2.GaussianBlur(np.random.default_rng(202).random((H // 24, W // 24)).astype(np.float32), (0, 0), 1.0), (W, H),
                        interpolation=cv2.INTER_CUBIC)
        self.fadeA = np.clip((540 + (nz - 0.5) * 260 - g * H) / 110, 0, 1).astype(np.float32)   # 纱袖下沿：噪声扰动的不规则羽化
        self.tins = [V(CT(28, k)) for k in range(5, 11)]
        self.td, self.tl = V(120.18) + 1 / FPS, V(120.36)

    def render(self, t):
        u = self.u(t)
        oy = lerp(40, -30, eio(u))
        tug = sum(pulse(t, V(b), 0.18) for b in (119.10, 119.57, 120.03, 120.33))
        fr = view(self.bg, 1.35, -_par(u, 30), 160 + oy * 0.3)
        fr = halo_tone(fr, (960, 160), 520, 0.40)
        hy = 30 - oy * 0.6 - 26 * tug
        fr, _ = put_src(fr, self.hand, t, (0.5, 0.0), (960, hy), 1040, wind=4.0, breathe=0.0, extra_A=self.fadeA)
        s = 1040 / 2048
        tips = [(960 + (x - 1024) * s, hy + y * s) for x, y in ((620, 660), (745, 700), (1015, 690), (1130, 640), (1370, 450))]
        for i in range(7):
            ti = self.tins[i] if i < 6 else self.td
            if t < ti: continue
            x = 960 + (i - 3) * 236
            tip = tips[min(4, int(round(i * 4 / 6)))]
            hit = ti if i < 6 else self.tl
            sw = 3.5 * math.sin(t * 2.6 + i * 1.3) + 9 * pulse(t, hit, 0.25) * (1 if i % 2 else -1)
            ly = 610 + 26 * math.sin(i * 1.9 + 0.4) - oy * 0.4 - 30 * tug - 36 * pulse(t, hit, 0.12)
            k = sm(ti, ti + 4 / FPS, t)
            drop = -(1 - eout(k, 2)) * 260 + 14 * math.sin(max(0.0, t - ti - 4 / FPS) * 24) * math.exp(-max(0.0, t - ti - 4 / FPS) * 8) * (k >= 1)
            if i == 6:
                k = sm(self.td, self.tl, t)
                drop = -(1 - eout(k)) * 360 + 18 * math.sin(max(0.0, t - self.tl) * 26) * math.exp(-max(0.0, t - self.tl) * 9) * (t >= self.tl)
            top = (x, ly + drop)
            fr = _red_line(fr, tip, top)
            P = self.tags[i]
            fr, _ = P.draw(fr, (P.w / 2, 20 * P.work), top, 0.62, rot=-sw)
            fr = _knot(fr, top)
        fr = dust(fr, t, 1021, n=60, amt=0.28, drift=(10, -14), size=(2, 5), color=(0.9, 0.9, 0.9), blur=2.0)
        return fr


def _red_line(fr, p0, p1, w=2, amt=0.95):
    L = np.zeros((H // 2, W // 2), np.float32)
    cv2.line(L, (int(p0[0] * 4), int(p0[1] * 4)), (int(p1[0] * 4), int(p1[1] * 4)), 1.0, max(1, int(w / 2)), cv2.LINE_AA, 3)
    g = cv2.GaussianBlur(L, (0, 0), 3)
    lay = cv2.resize(L + g * 0.4, (W, H))
    m = np.clip(cv2.resize(L, (W, H)), 0, 1)
    return fr * (1 - m[..., None] * 0.9 * amt) + lay[..., None] * np.array(BRED, np.float32) * 1.25 * amt


def _knot(fr, p, r=4.0):
    lay = np.zeros((H, W), np.float32)
    cv2.circle(lay, (int(p[0] * 4), int(p[1] * 4)), int(r * 4), 1.0, -1, cv2.LINE_AA, 2)
    return C1.over(fr, lay, np.array(BRED, np.float32))


class C03(Shot):
    """LS 皮影幕：背光纸幕（生图背景板）前七个皮影人偶（生图），在「纲」(120.96) 与 121.31 两拍被红线齐齐拽起，各自延迟/幅度错开；
    幕上压着太上皇巨手的影子（C02 手的 alpha 投影：离幕远 → 软边 + 半影，拽线时抽动）。
    分层：L1 皮影幕板（视差 0.3）/ L2 手影（软阴影层）/ L3 七个皮影（逐个独立摆动、被拽起）+ 幕上投影 / 代码：红提线、幕后光闪、浮尘、底部薄雾。"""
    def __init__(self):
        self.bg = plate('C03_screen', 0.95)
        self.pp = [Prop('C03_puppets', box=b, mask=m, work=0.5) for b, m in comps('C03_puppets', 7, ybox=(150, 960))]
        hA = cv2.imread(A_DIR + 'C02_hand_cut.png', cv2.IMREAD_UNCHANGED)[..., 3].astype(np.float32) / 255
        self.hA = cv2.resize(hA, (1024, 576), interpolation=cv2.INTER_AREA)
        r = np.random.default_rng(3)
        self.par = [dict(dl=abs(i - 3) * 0.035 + r.uniform(0, 0.03), la=r.uniform(0.6, 1.3), fq=r.uniform(1.5, 3.2), ph=r.uniform(0, 6.3),
                         am=r.uniform(2, 6), sg=1 if r.random() < 0.5 else -1) for i in range(7)]

    def render(self, t):
        u = self.u(t)
        tj, tj2 = V(120.96), V(121.31)
        tw = min(1.0, pulse(t, tj, 0.18) + 0.7 * pulse(t, tj2, 0.15))
        fr = view(self.bg, 1.04 + 0.03 * u, -_par(u, 30), 0)
        fr = fr * (1 + 0.10 * tw)
        # 手影（巨手 + 纱袖，从画顶压下来）
        hx = 960 + 30 * math.sin(t * 0.9); hy = -120 - 50 * tw
        M = np.float32([[1.45, 0, hx - 1024 * 0.725], [0, 1.45, hy]])
        sh = cv2.warpAffine(self.hA, M, (W, H))
        sh = cv2.GaussianBlur(sh, (0, 0), 6) * 0.65 + cv2.GaussianBlur(sh, (0, 0), 20) * 0.35
        fr = fr * (1 - 0.82 * sh[..., None])
        bar_y = 140
        for i, P in enumerate(self.pp):
            p = self.par[i]
            x = 250 + i * 236
            hgt = 560
            lift = p['la'] * (90 * pulse(t, tj + p['dl'], 0.22) + 50 * pulse(t, tj2 + p['dl'], 0.18))
            top = 300 - lift + 7 * math.sin(t * p['fq'] * 1.2 + p['ph'])
            ang = p['am'] * math.sin(t * p['fq'] + p['ph']) + 10 * p['la'] * pulse(t, tj + p['dl'], 0.3) * p['sg']
            sc = hgt / (P.h / P.work)
            fr = _red_line(fr, (x + 10 * math.sin(i), bar_y - 60 * tw), (x, top + 6), w=2, amt=0.8)
            # 幕上投影（贴幕，软）
            Msh = P.M((P.w / 2, 0), (x + 22, top + 14), sc, ang)
            sA = cv2.GaussianBlur(cv2.warpAffine(P.A, Msh, (W, H)), (0, 0), 7)
            fr = fr * (1 - 0.35 * sA[..., None])
            fr, _ = P.draw(fr, (P.w / 2, 0), (x, top), sc, rot=ang, alpha=0.96)
        fr = K.fog(fr, t, 4, density=0.30, y0=780, y1=980, color=(0.75, 0.75, 0.75), speed=(30, 0))
        fr = dust(fr, t, 1031, n=60, amt=0.30, drift=(8, -24), size=(2, 5), color=(1.0, 1.0, 1.0), blur=1.8)
        return fr


class C04(Shot):
    """CU 天平：青铜天平（生图，拆成立柱 / 横梁 / 左右秤盘四个铰接件，同一刚体系统），玉玺（生图）从画顶坠进右盘（121.72），
    横梁绕支点倾 −9°，左盘翘起、盘里皮影小人被颠起甩出盘沿；落盘火星（白 + 血红）、震屏、冲击白光。
    分层：L1 暗殿背景板（虚焦，视差 0.3）/ L2 天平立柱 / L3 横梁（绕支点转）/ L4 左右秤盘（随梁端升降，链条保持竖直）/ L5 玉玺（坠落拖影）/
    L6 皮影小人 ×5 / 代码：火星、灯笼光斑前景、浮尘、震屏。"""
    PIV = (1024, 175)
    def __init__(self):
        im = cv2.imread(A_DIR + 'C04_balance_cut.png', cv2.IMREAD_UNCHANGED)
        h, w = im.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        nz = cv2.resize(np.random.default_rng(404).random((h // 16, w // 16)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        beam = np.clip((236 + (nz - 0.5) * 24 - yy) / 14, 0, 1)                       # 横梁下沿：中央立柱处不规则羽化（梁转动时与立柱自然衔接）
        side = ((xx < 820) | (xx > 1230)).astype(np.float32)
        beam = np.where(side > 0, (yy < 210).astype(np.float32), beam)                 # 两端：梁与链条之间是空隙，直接分
        pans = side * (yy >= 210) * (yy < 870)
        lpan = pans * (xx < 820); rpan = pans * (xx > 1230)
        post = np.clip(1 - beam - lpan - rpan, 0, 1)                                    # 立柱 + 底座（底座横跨两侧，整块不动）
        self.post = Prop('C04_balance', mask=post, work=0.5); self.beam = Prop('C04_balance', mask=beam, work=0.5)
        self.lp = Prop('C04_balance', mask=lpan, work=0.5); self.rp = Prop('C04_balance', mask=rpan, work=0.5)
        self.seal = Prop('C04_seal', work=0.5)
        self.pp = [Prop('C03_puppets', box=b, mask=m, work=0.25) for b, m in comps('C03_puppets', 7, ybox=(150, 960))]
        self.bg = plate('CA_room', 0.55, recede=0.6)
        self.S, self.C = 0.66, (960, 575)         # 原图 → 屏幕：缩放 / 原图中心落点
        self.LH, self.RH = (425, 160), (1625, 160)  # 左右挂点（原图）
        self.LPAN, self.RPAN = (425, 735), (1625, 735)

    def scr(self, x, y):
        return (self.C[0] + (x - 1024) * self.S, self.C[1] + (y - 560) * self.S)

    def render(self, t):
        u = self.u(t)
        td = V(121.72)
        k = max(0.0, t - td)
        tilt = (9 * eout(k / 0.35) + 2.2 * math.sin(k * 14) * math.exp(-k * 5)) if t >= td else 1.2 * math.sin(t * 2)   # +：右端下沉（玉玺落右盘），左盘翘起
        fl = pulse(t, td, 0.10) * (t >= td)
        fr = view(self.bg, 1.5, 260 - _par(u, 40), 60)                  # 同殿换机位：放大取左侧灯笼与立柱
        fr = halo_tone(fr, (1500, 250), 420, 0.35)
        S = self.S; z = 1.0 + 0.06 * eio(u)
        def P(x, y):
            px, py = self.scr(x, y); return (960 + (px - 960) * z, 540 + (py - 540) * z)
        pv = P(*self.PIV)
        # 立柱
        fr, _ = self.post.draw(fr, self.post.src(*self.PIV), pv, S * z)
        # 秤盘：挂点随横梁转，盘保持竖直
        th = math.radians(tilt)
        def hang(hx, hy):
            dx, dy = (hx - self.PIV[0]) * S * z, (hy - self.PIV[1]) * S * z
            return (pv[0] + dx * math.cos(th) - dy * math.sin(th), pv[1] + dx * math.sin(th) + dy * math.cos(th))
        lh, rh = hang(*self.LH), hang(*self.RH)
        lsw = 1.5 * math.sin(t * 3.1) - 4 * pulse(t, td, 0.3) * (t >= td)
        fr, _ = self.lp.draw(fr, self.lp.src(*self.LH), lh, S * z, rot=lsw)
        # 左盘皮影小人：盘被翘起时颠起、两个从盘沿滑出画外
        lpan = (lh[0], lh[1] + (self.LPAN[1] - self.LH[1]) * S * z)
        r = np.random.default_rng(41)
        for i in range(5):
            Pp = self.pp[(i * 3) % 7]
            ox = r.uniform(-0.62, 0.62) * 230 * S * z
            pop = 0.0; ang = r.uniform(-8, 8); dl = r.uniform(0, 0.06)        # 随机数每帧同序抽取（不受 t 影响）
            if t >= td:
                kk = max(0.0, k - dl); out = i in (0, 4)
                pop = 260 * kk - 1300 * kk * kk if not out else 300 * kk - 1500 * kk * kk
                if pop < 0 and not out: pop = 0.0
                ox += (ox / abs(ox + 1e-3)) * (380 * kk if out else 40 * kk)
                ang += (90 if out else 25) * kk * (1 if ox > 0 else -1)
            sc = 150 / (Pp.h / Pp.work) * z
            fr, _ = Pp.draw(fr, (Pp.w / 2, Pp.h), (lpan[0] + ox, lpan[1] - 4 - pop), sc, rot=ang)
        fr, _ = self.rp.draw(fr, self.rp.src(*self.RH), rh, S * z, rot=-lsw)
        rpan = (rh[0], rh[1] + (self.RPAN[1] - self.RH[1]) * S * z)
        # 玉玺
        ssz = 0.17 * z
        if t < td:
            fall = sm(td - 0.32, td, t)
            y = lerp(-260, rpan[1] - 60, ein(fall, 2))
            fr, _ = self.seal.draw(fr, self.seal.src(1150, 1100), (rpan[0], y), ssz, rot=-14 + 18 * fall, mblur=(0, 40 * fall))
        else:
            fr, _ = self.seal.draw(fr, self.seal.src(1150, 1100), (rpan[0], rpan[1] - 40 + 10 * pulse(t, td, 0.08)), ssz, rot=4)
        # 横梁（最前，压住挂钩）
        fr, _ = self.beam.draw(fr, self.beam.src(*self.PIV), pv, S * z, rot=-tilt)
        if t >= td:
            fr = sparks2(fr, t, 401, (rpan[0], rpan[1] - 30), td, n=60, dirc=(0, -1), spread=1.0, speed=(300, 900), life=0.6, area=(120, 10))
            fr = halo_tone(fr, (rpan[0], rpan[1] - 40), 300, 0.9 * fl)
        fr = dust(fr, t, 1041, n=70, amt=0.28, drift=(8, -14), size=(2, 5), color=(1.0, 1.0, 1.0), blur=1.8)
        dx, dy, dr = shake(t, 12 * pulse(t, td, 0.10) * (t >= td) + 0.8, 14, 404)
        return C1.cam(fr, 1.0, dx, dy, dr)


class C05(Shot):
    """ECU 暗箱：黑漆描金方箱（生图，高俯 3/4），箱口一团黑；铜钱（代码墨线钱币）与皮影小人（生图）倾泻进箱口、越过前沿即被吞没；
    镜头推向箱口（交易）1.00→1.25。分层：L1 暗殿背景板（深虚焦）/ L2 箱身（锁定）/ L3 倾泻物（前沿遮挡）/ 代码：箱口幽光、浮尘、接触阴影。"""
    FL, FR, BL, BR = (330, 320), (1490, 530), (660, 80), (1760, 220)     # 箱口四角（原图）
    def __init__(self):
        self.box = Prop('C05_box', work=0.5)
        self.pp = [Prop('C03_puppets', box=b, mask=m, work=0.2) for b, m in comps('C03_puppets', 7, ybox=(150, 960))]
        self.bg = plate('CA_room', 0.50, recede=0.7, flip=True)

    def render(self, t):
        u = self.u(t)
        z = 1.0 + 0.25 * ein(u, 2)
        fr = view(self.bg, 1.6 + 0.1 * u, 0, -220)                     # 同殿换机位：镜像 + 取地面一角
        S = 0.78 * z; C = (960, 560 + 140 * (z - 1))
        sc = lambda p: (C[0] + (p[0] - 1028) * S, C[1] + (p[1] - 570) * S)
        # 接触阴影
        sh = np.zeros((H // 4, W // 4), np.float32)
        cv2.ellipse(sh, (int(C[0] / 4), int((C[1] + 430 * S) / 4)), (int(700 * S / 4), int(90 * S / 4)), 0, 0, 360, 1.0, -1)
        fr = fr * (1 - 0.7 * cv2.resize(cv2.GaussianBlur(sh, (0, 0), 6), (W, H)))[..., None]
        fr, _ = self.box.draw(fr, self.box.src(1028, 570), C, S)
        fl, fr_, bl, br = sc(self.FL), sc(self.FR), sc(self.BL), sc(self.BR)
        def front_y(x):  # 箱口前沿（FL→FR）在 x 处的 y
            k = (x - fl[0]) / (fr_[0] - fl[0]); return fl[1] + (fr_[1] - fl[1]) * k
        cx = (fl[0] + fr_[0] + bl[0] + br[0]) / 4; cy = (fl[1] + fr_[1] + bl[1] + br[1]) / 4
        fr = halo_tone(fr, (cx, cy), 260 * z, 0.25)
        r = np.random.default_rng(13)
        L = np.zeros((H, W), np.float32); Lk = np.zeros((H, W), np.float32)
        RN = r.random((70, 5))                                            # 每件倾泻物的随机数一次抽齐（剔除不影响后续）
        for i in range(70):
            ph, sp, xr, kind, szr = RN[i]; sp = 0.7 + 0.4 * sp
            kk = ((t * sp * 1.3 + ph) % 1.0)
            x = cx + (xr * 1.6 - 0.8) * (fr_[0] - fl[0]) * 0.42 * (1 - kk * 0.3)
            y = lerp(BAR - 60, cy + 60, kk ** 1.7)
            if y > front_y(x) - 10: continue
            if kind < 0.8:
                sz = int((12 + 10 * szr) * z); ang = (t * 340 * sp + i * 40) % 180
                ry = max(2, int(sz * abs(math.cos(math.radians(ang)))))
                cv2.ellipse(Lk, (int(x), int(y)), (sz + 3, ry + 3), i * 23, 0, 360, 1.0, -1, cv2.LINE_AA)
                cv2.ellipse(L, (int(x), int(y)), (sz, ry), i * 23, 0, 360, 1.0, -1, cv2.LINE_AA)
                cv2.rectangle(Lk, (int(x - sz * 0.25), int(y - ry * 0.25)), (int(x + sz * 0.25), int(y + ry * 0.25)), 1.0, -1)
                cv2.rectangle(L, (int(x - sz * 0.25), int(y - ry * 0.25)), (int(x + sz * 0.25), int(y + ry * 0.25)), 0.0, -1)
            else:
                Pp = self.pp[i % 7]
                fr, _ = Pp.draw(fr, (Pp.w / 2, Pp.h / 2), (x, y), 130 / (Pp.h / Pp.work) * z, rot=(t * 220 + i * 50) % 360)
        fr = C1.over(fr, Lk, INK)                        # 钱币：墨线描边 + 白面 + 方孔
        fr = C1.over(fr, L, (0.92, 0.92, 0.92))
        fr = dust(fr, t, 1051, n=60, amt=0.3, drift=(6, 30), size=(2, 5), color=(1.0, 1.0, 1.0), blur=1.6)
        return fr


class C06(Shot):
    """POV 箱底仰望：我们就是被倒进暗箱的「货」——箱盖内壁（生图，旧木板 + 铁箍 + 合页）在头顶，铰链在画顶；
    「暗」123.86 一震、盖板压下一档（落灰 + 震屏），「箱」124.22 后盖板整块朝镜头砸下合上（124.30–124.45），
    烛光被挤成箱沿一道白缝（接 C07 seam 转场）。不刻任何字。
    分层：L1 箱外暗殿背景板（透过箱口，虚焦）/ L2 箱壁（代码墨框四周压暗）/ L3 盖板（透视转动的刚体）/ 代码：落灰、白缝、震屏。"""
    def __init__(self):
        self.lid = Prop('C06_lid', work=0.5)
        self.bg = plate('CA_room', 0.75, recede=0.4)
        yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32) * 4
        e = np.minimum(np.minimum(xx, W - xx), np.minimum(yy - BAR, H - BAR - yy))
        self.wall = cv2.resize(np.clip(1 - e / 170, 0, 1) ** 1.5, (W, H))       # 箱壁四周墨框

    def render(self, t):
        u = self.u(t)
        t1, t2 = V(123.86), V(124.22); tc = t2 + 0.08
        phi = 62 - 16 * eout(clamp((t - t1) / 0.10)) * (t >= t1)
        cl = ein(clamp((t - tc) / 0.18), 2.2)
        phi = phi * (1 - cl)
        bg = view(self.bg, 1.25, 0, 120, rot=180)          # 仰望：殿顶
        fr = bg * (0.8 + 0.25 * np.linspace(1, 0, H, dtype=np.float32)[:, None, None])
        c = math.cos(math.radians(phi))
        hinge = 60
        depth = 40 + 1020 * c
        wf = 1.0 + 0.45 * (1 - math.sin(math.radians(phi)))       # 近端变宽（透视）
        q0 = np.float32([[0, 0], [self.lid.w, 0], [self.lid.w, self.lid.h], [0, self.lid.h]])
        dst = np.float32([[-60, hinge], [W + 60, hinge], [960 + (W / 2 + 120) * wf, hinge + depth], [960 - (W / 2 + 120) * wf, hinge + depth]])
        Mh = cv2.getPerspectiveTransform(q0, dst)
        shade = 0.55 + 0.45 * c
        fr, Aw = self.lid.draw(fr, None, None, None, persp=Mh, gain=shade)
        # 箱壁：四周墨框（越合越黑）
        fr = fr * (1 - 0.75 * self.wall)[..., None]
        if cl > 0:
            fr = fr * (1 - 0.85 * cl)
            ys = lerp(980, 880, cl)
            seam = np.exp(-((np.arange(H, dtype=np.float32)[:, None] - ys) / (2 + 26 * (1 - cl))) ** 2)
            fr = fr + seam[..., None] * np.array([1.0, 1.0, 1.0], np.float32) * (0.4 + 1.0 * cl)
        fr = dust(fr, t, 1061, n=90, amt=0.35 + 0.5 * pulse(t, t1, 0.3) * (t >= t1), drift=(4, 70), size=(2, 6), color=(1.0, 1.0, 1.0), blur=1.6)
        sk = 10 * pulse(t, t1, 0.10) * (t >= t1) + 16 * pulse(t, tc + 0.18, 0.10) * (t >= tc + 0.18)
        dx, dy, dr = shake(t, sk + 0.5, 14, 606)
        return C1.cam(fr, 1.0, dx, dy, dr)


# ===================================================================================== 我不低头
class C07(Shot):
    """MCU 雨夜（「我不低头」）：鬼屠（定妆照）在雷暴里抬起下颌，124.90 背后一道闪电把他勾亮、下颌随之上抬；
    分层：L1 雷暴天背景板（视差 0.3，云缓移）/ L2 远雨（代码细线）/ L3 主体（风吹发丝、抬颌两档）/ L4 近雨（生图墨线雨，视差 1.4）/ 代码：闪电、雷光提亮。"""
    def __init__(self):
        self.sp = spr('C07_face'); self.bg = plate('CA_sky', 0.85)

    def render(self, t):
        u = self.u(t)
        tf = V(124.90)
        fl = bolt_env(t, tf) * 0.9 + 0.4 * bolt_env(t, V(125.46))
        fr = view(self.bg, 1.12, -_par(u, 50), _par(u, 20))
        fr = bolt(fr, t, tf, 71, (1650, 40), (1450, 700), inten=0.9, sky=0.25, width=3.0)
        fr = lit(fr, fl * 0.6)
        fr = rain_code(fr, t, 70, inten=0.6, angle=-22, layers=(0, 1))
        lift = eio(clamp((t - tf + 0.1) / 0.4))
        fr, _ = put_src(fr, self.sp, t, (0.45, 1.0), (1180, 1000), 1500, wind=7, rot=2.0 - 4.0 * lift, breathe=0.0)
        fr = lit(fr, fl * 0.25)
        fr = rain_fg(fr, t, 1, amt=0.55, speed=2400, scale=0.7, cam=(_par(u, 70), 0))
        return fr


class C08(Shot):
    """ECU 同轴跳进眼睛：眼部大特写（生图背景板即主体，定妆照），雨水顺睫毛，126.14「命」一记闪电在瞳孔里一亮 + 推镜冲击。
    分层：L1 眼部板（锁定）/ L2 前额乱发（从板里按暗部分出的发丝层，独立飘动）/ L3 前景墨线雨（视差 1.6）/ 代码：瞳中电光十字星、水珠下滑、雷光。"""
    EYES = ((600, 666), (1335, 666))
    def __init__(self):
        self.bg = plate('C08_eyes', 1.0)
        lum = self.bg.mean(-1)
        yy = np.arange(H, dtype=np.float32)[:, None]
        m = (lum < 0.10).astype(np.float32) * np.clip((560 - yy) / 120, 0, 1)
        self.hairA = cv2.GaussianBlur(m, (0, 0), 1.2)

    def render(self, t):
        u = self.u(t)
        tf = V(126.14)
        fl = bolt_env(t, tf)
        z = 1.03 + 0.05 * u + 0.05 * pulse(t, tf, 0.15) * (t >= tf)
        fr = view(self.bg, z, 0, 0)
        # 发丝层（独立飘动）
        sw = 5 * math.sin(t * 3.1) + 3 * math.sin(t * 7.3)
        hl = view(self.bg * self.hairA[..., None], z, sw, 0); ha = view(self.hairA, z, sw, 0)
        fr = fr * (1 - ha[..., None]) + hl
        fr = lit(fr, fl * 0.4)
        g = fl * 1.4
        x, y = _grid() if g > 0.02 else (None, None)
        for ex, ey in self.EYES:
            ex = 960 + (ex - 960) * z; ey = 540 + (ey - 540) * z
            if g > 0.02:
                st = np.exp(-(np.abs(x - ex) / 2.5 + np.abs(y - ey) / 40)) + np.exp(-(np.abs(y - ey) / 2.5 + np.abs(x - ex) / 60))
                fr = fr + (st * g * 0.9 + np.exp(-((x - ex) ** 2 + (y - ey) ** 2) / 200) * g)[..., None]
        # 水珠沿脸颊下滑
        for i, (x0, sp_) in enumerate(((560, 160), (1390, 120))):
            y = 760 + ((t * sp_ + i * 90) % 260)
            fr = ink_drop(fr, (x0 * z + 960 * (1 - z), y), r=5, red=False)
        fr = rain_fg(fr, t, 2, amt=0.6, speed=2600, scale=0.8, cam=(_par(u, 80), 0))
        return fr


class C09(Shot):
    """LS 仰拍（「不认命 不信什么」）：雷暴积水原上，鬼屠低身蓄势（生图姿势一）→ 126.32 第一个「不」上撩出刀（姿势二，硬切），
    头顶十四根红线左半在 126.32、右半在 127.00 被斩断回弹；每一刀一道干笔飞白刀痕 + 火星（白 + 血红）+ 震屏。
    分层：L1 积水原背景板（视差 0.3）/ L2 远雨 / L3 红线（代码，断线回弹）/ L4 主体两姿势 + 积水倒影 / L5 飞白刀痕 / L6 近雨（生图）。"""
    def __init__(self):
        self.a = spr('C09_ready'); self.b = spr('C09_slash'); self.bg = plate('CA_water', 0.95)

    def render(self, t):
        u = self.u(t)
        cuts = [V(126.32), V(127.00)]
        fl = bolt_env(t, cuts[0]) * 0.7 + bolt_env(t, cuts[1]) * 0.5
        fr = view(self.bg, 1.10, -_par(u, 40), 60 - 40 * u)
        fr = lit(fr, fl * 0.5)
        fr = rain_code(fr, t, 90, inten=0.6, angle=-20, layers=(0, 1))
        r = np.random.default_rng(5)
        for i in range(14):
            x = 200 + i * 118 + r.uniform(-30, 30)
            tc = cuts[0] if x < 960 else cuts[1]
            y_end = 470 + r.uniform(-80, 120)
            if t < tc:
                fr = _red_line(fr, (x + 30 * math.sin(i), BAR), (x + 6 * math.sin(t * 3 + i), y_end), w=2, amt=0.85)
            else:
                k = t - tc; rec = 300 * eout(k / 0.4) + 400 * k
                fr = _red_line(fr, (x + 30 * math.sin(i), BAR), (x + 30 * math.sin(i * 2) * k, max(BAR + 2, y_end - 160 - rec)), w=2, amt=0.85)
                fr = _red_line(fr, (x - 40 * k, y_end - 140 + 900 * k * k), (x - 80 * k, y_end + 120 + 900 * k * k), w=2,
                               amt=0.75 * (1 - sm(0.3, 0.9, k)))
        foot = (980 + _par(u, 14), 885)                  # 脚在 2.39 画幅内（下黑边从 960 起），留出积水倒影
        if t < cuts[0]:
            fr, A = put(fr, self.a, t, 640, foot, wind=7)
        else:
            k = clamp((t - cuts[0]) / 0.08)
            fr, A = put(fr, self.b, t, 660, foot, wind=8, mblur=(0, -30 * (1 - k)))
        fr = mirror(fr, A, foot[1] - 4, amt=0.30, t=t)
        for tc, (a, b), fp in zip(cuts, (((620, 760), (1500, 180)), ((1650, 260), (900, 640))), (False, True)):
            fr = brush_slash(fr, a, b, (t - tc) / 0.22, width=0.55, flip=fp)
            if t >= tc: fr = sparks2(fr, t, int(tc * 10), b, tc, n=40, dirc=(0, 1), spread=1.3, speed=(200, 700))
        fr = rain_fg(fr, t, 3, amt=0.5, speed=2400, scale=0.7, cam=(_par(u, 60), 0))
        sk = pulse(t, cuts[0], 0.10) * (t >= cuts[0]) + 0.7 * pulse(t, cuts[1], 0.10) * (t >= cuts[1])
        dx, dy, dr = shake(t, 10 * sk, 14, 909)
        return C1.cam(fr, 1.0 + 0.02 * sk, dx, dy, dr)


class C10(Shot):
    """CU 雨夜宫檐（保留字「大局为上」，四字阴刻填血红，画进四块乌木匾的生图里）：四块匾用红绳吊在雕梁下随风轻摆，
    唱到哪个字那块匾一记血光脉冲（大 127.22 / 局 127.56 / 为 127.84）；127.86 一道横向干笔刀痕扫断红绳，四匾带着字翻滚坠落。
    分层：L1 宫檐背景板（视差 0.3）/ L2 远雨 / L3 红绳 / L4 四块匾（各自独立刚体摆动、坠落）/ L5 横扫飞白刀痕 + 火星 / L6 近雨（生图）。"""
    def __init__(self):
        self.tabs = [Prop('C10_tablets', box=b, mask=m, work=0.5) for b, m in comps('C10_tablets', 4)]
        self.tins = [V(CT(30, k)) for k in (11, 12, 13, 14)]
        self.bg = plate('C10_eave', 0.9)

    def render(self, t):
        u = self.u(t)
        tc = V(127.86)
        fl = bolt_env(t, tc) * 0.6 + 0.35 * bolt_env(t, V(127.22))
        fr = view(self.bg, 1.08, -_par(u, 40), 30)
        fr = lit(fr, fl * 0.5)
        fr = rain_code(fr, t, 100, inten=0.7, angle=-14, layers=(0, 1, 2))
        tins = self.tins
        for i, P in enumerate(self.tabs):
            x = 960 + (i - 1.5) * 330 + _par(u, 20)
            top0 = 250
            sw = 2.2 * math.sin(t * 2.2 + i)
            if t < tc:
                dy, ang = 0.0, sw
                fr = _red_line(fr, (x, 90), (x, top0 + 4), w=3)
            else:
                k = t - tc
                dy = 1500 * k * k * (0.85 + 0.12 * i) + 40 * k; ang = sw + (40 + 22 * i) * k * (1 if i % 2 else -1)
                rr = 1 - sm(0.3, 0.8, k)
                fr = _red_line(fr, (x, 90), (x + 18 * math.sin(k * 20 + x), 90 + 70 * (1 - min(1, k * 3)) + 30), w=3, amt=0.9 * rr)
            sc = 560 / (P.h / P.work)
            pk = pulse(t, tins[i], 0.18) * (t >= tins[i]) if i < 3 else 0.0
            fr, _ = P.draw(fr, (P.w / 2, 0), (x, top0 + dy), sc, rot=ang, gain=1.0 + 0.35 * pk)
        fr = brush_slash(fr, (60, 240), (1860, 225), (t - tc) / 0.20, width=0.45, flip=True)
        if t >= tc:
            for i in range(4):
                fr = sparks2(fr, t, 1010 + i, (960 + (i - 1.5) * 330, 240), tc, n=26, dirc=(1, -0.3), spread=1.0, speed=(200, 800))
        fr = rain_fg(fr, t, 4, amt=0.5, speed=2300, scale=0.7, cam=(_par(u, 60), 0))
        dx, dy, dr = shake(t, 12 * pulse(t, tc, 0.10) * (t >= tc), 14, 1010)
        return C1.cam(fr, 1.0, dx, dy, dr)


class C11(Shot):
    """CU 横刀（「信这柄刀」）：长刀横贯画面（生图：黑钢刃、刃口烧得血红发白，雨点打上去化作白汽），镜头沿刀身横移；
    分层：L1 雷暴天背景板（深虚焦、压暗，视差 0.25）/ L2 刀（锁定，横移）/ L3 刃口白汽（代码雾，贴刃上升）/ L4 近雨（生图）/ 代码：火星（白 + 血红）、热辉。"""
    def __init__(self):
        self.blade = Prop('C11_blade', work=0.5); self.bg = plate('CA_sky', 0.55, recede=0.7, flip=True)

    def render(self, t):
        u = self.u(t)
        fr = view(self.bg, 1.5, -_par(u, 50), 150)
        x = lerp(-60, -200, eio(u))                                  # 护手压在画左外（刀柄不入画），画面里只有刀身
        fr, A = self.blade.draw(fr, self.blade.src(560, 555), (x, 560), 1.45)
        hot = np.clip(fr[..., 0] - fr[..., 1] * 1.4, 0, 1) * A
        fr = fr + blur_ds(hot, 26)[..., None] * np.array(BRED, np.float32) * (0.9 + 0.2 * math.sin(t * 7))
        fr = K.fog(fr, t, 12, density=0.55, y0=380, y1=560, color=(0.95, 0.95, 0.95), speed=(-60, -90), scale=0.6)
        fr = sparks(fr, t, 111, (1250, 545), n=60, life=0.9, speed=(40, 200), dirc=(0, -1), spread=0.8, grav=-60, amt=0.9, area=(560, 6), color=WHITE)
        fr = sparks(fr, t, 112, (1250, 545), n=30, life=0.8, speed=(40, 200), dirc=(0, -1), spread=0.8, grav=-60, amt=1.0, area=(560, 6), color=BRED)
        fr = rain_fg(fr, t, 5, amt=0.45, speed=2400, scale=0.7, cam=(_par(u, 80), 0))
        return fr


class C12(Shot):
    """ECU 刃口（「还在发烫」）：同一把刀（同一张生图）推到刃口大特写，赤红刃口斜贯画面，白汽翻滚、铁屑火星剥落，热浪扭曲。
    分层：L1 黑底 + 虚焦雷云（视差 0.2）/ L2 刀（2.8 倍，横移）/ L3 白汽两层（近层大虚、快）/ 代码：火星、热浪、刃光扫。"""
    def __init__(self):
        self.blade = Prop('C11_blade', work=1.0); self.bg = plate('CA_sky', 0.35, recede=0.8)

    def render(self, t):
        u = self.u(t)
        fr = view(self.bg, 1.9, -300 - _par(u, 30), 80)
        fr, A = self.blade.draw(fr, self.blade.src(1500, 560), (1120 - 140 * u, 600), 2.6, rot=-6)
        hot = np.clip(fr[..., 0] - fr[..., 1] * 1.4, 0, 1) * A
        fr = fr + blur_ds(hot, 40)[..., None] * np.array(BRED, np.float32) * 0.9
        fr = fx2.heat_haze(fr, t, amt=5.0)
        fr = K.fog(fr, t, 13, density=0.75, y0=200, y1=700, color=(0.95, 0.95, 0.95), speed=(-120, -160), scale=0.5)
        # 刃光：一道白光沿刃口扫过（130.50「还」）
        q = clamp((t - V(130.50)) / 0.25)
        if 0 < q < 1:
            x, y = _grid()
            cx = lerp(300, 1700, q)
            fr = fr + (np.exp(-((x - cx) / 60) ** 2) * A * 0.9)[..., None]
        fr = sparks(fr, t, 121, (900, 640), n=110, life=0.8, speed=(80, 420), dirc=(0.3, -1), spread=0.7, grav=-100, amt=1.0, area=(800, 20), color=WHITE)
        fr = sparks(fr, t, 122, (900, 640), n=60, life=0.8, speed=(80, 420), dirc=(0.3, -1), spread=0.7, grav=-100, amt=1.1, area=(800, 20), color=BRED)
        return fr


class C13(Shot):
    """riser：镜头冲进风暴之眼（生图背景板：黑白云带 + 血红眼壁）。远层整板慢转 + 推近，近层只取亮云带、转得更快放得更大并虚焦（纵深视差），
    雨线沿螺旋吸进眼里；131.61 / 131.96 / 132.07 鼓点上云层里电光一闪。分层：L1 风眼板（远层）/ L2 同板亮云近层 / 代码：螺旋雨线、电光。"""
    def __init__(self):
        self.bg = plate('C13_vortex', 1.0, size=(2400, 1350))
        lum = self.bg.mean(-1)
        self.nearA = np.clip((lum - 0.55) / 0.3, 0, 1).astype(np.float32)

    def render(self, t):
        u = self.u(t)
        hits = [V(x) for x in (131.61, 131.96, 132.07)]
        fl = sum(0.6 * pulse(t, h, 0.07) * (t >= h) for h in hits) + 0.2 * ein(u, 2)
        z = 1.0 + 0.35 * ein(u, 2); rot = 12 * u + 8 * ein(u, 2)      # 转角 ≤20°：远层 1.12 倍即盖满 2.39 画幅（不露板边）
        far = view(self.bg, z * 1.12, 0, 0, rot=rot)
        nz = z * 1.25; nrot = rot * 1.8
        near = view(self.bg, nz * 1.12, 0, 0, rot=nrot); na = view(self.nearA, nz * 1.12, 0, 0, rot=nrot, border=cv2.BORDER_CONSTANT) * 0.55
        fr = far * (1 - na[..., None]) + near * na[..., None]
        fr = lit(fr, fl * 0.6)
        fr = speed_lines(fr, t, 1300, c=(960, 540), amt=0.5 + 0.4 * u, n=60, r0=300 - 150 * u)
        return fr


class C14(Shot):
    """过肩仰拍：镜头贴在他后脑下方，头肩（生图，定妆照后脑 + 高马尾）占画面左下，仰头看头顶的风眼（C13 同一张板），
    132.45 一道落地闪电从风眼劈下。分层：L1 风眼天（同板，虚焦慢转，视差 0.3）/ L2 远雨 / L3 主体（马尾、发丝风吹）/ L4 近雨（生图）/ 代码：闪电、雷光。"""
    def __init__(self):
        self.sp = spr('C14_ots'); self.bg = plate('C13_vortex', 0.85, recede=0.3, size=(2400, 1350), flip=True)

    def render(self, t):
        u = self.u(t)
        tb = V(132.45)
        fl = bolt_env(t, tb) + 0.5 * bolt_env(t, V(132.87))
        fr = view(self.bg, 1.62, 160 - _par(u, 40), 180, rot=8 * u)
        fr = bolt(fr, t, tb, 141, (1100, 220), (1600, 960), inten=1.4, width=5, sky=0.12)
        fr = lit(fr, fl * 0.35)
        fr = rain_code(fr, t, 141, inten=0.7, angle=-18, layers=(0, 1))
        fr, _ = put_src(fr, self.sp, t, (0.55, 1.0), (760 + 25 * u, 1080), 1650, wind=7, breathe=0.0)
        fr = lit(fr, fl * 0.15)
        fr = rain_fg(fr, t, 6, amt=0.5, speed=2400, scale=0.7, cam=(_par(u, 60), 0))
        return fr


class C15(Shot):
    """间奏 ELS（用户：「跳斩太丑了，换个形式」→ 重做，且不重复 S035 的冲刺 + 劈墙分格）：
    不跳。雷暴积水原上他独自立定（姿势一，刀尖垂地），133.38 切点雷劈在身后（与切点同帧），镜头缓推；
    133.79 鼓加花（原 INSERTS 朱红负片帧保留）= 一记血振（chiburi，姿势二硬切）：刀向右下一甩，一扇血珠甩出——
    血珠与雨同时被「慢放到悬停」（速度坡度 1→0.04），一颗颗墨线描边的血珠挂在空中，直到下一镜刀尖那滴落进水里成「血」。
    分层：L1 积水原背景板（视差 0.3）/ L2 远雨（代码，悬停）/ L3 主体两姿势 + 积水倒影 / L4 血珠（代码墨线血珠，悬停）/ L5 近雨（生图，悬停）/ 代码：两道闪电、雷光勾边、水面血点涟漪。"""
    def __init__(self):
        self.a = spr('C15_stand'); self.b = spr('C15_flick'); self.bg = plate('CA_water', 0.9, flip=True)
        r = np.random.default_rng(1515)
        n = 26
        self.drops = [dict(a=math.radians(r.uniform(-75, 15)), v=r.uniform(500, 1300), r=r.uniform(4, 11), d=r.uniform(0, 0.03)) for _ in range(n)]

    def render(self, t):
        u = self.u(t)
        tb, tb2 = V(133.38), V(133.79)
        fl = bolt_env(t, tb) * 1.1 + bolt_env(t, tb2) * 0.8
        tfz = tb2 + 0.12                                   # 血珠 / 雨开始悬停
        fr = view(self.bg, 1.08 + 0.04 * u, -_par(u, 40), 40)
        fr = bolt(fr, t, tb, 151, (1250, 120), (1380, 700), inten=1.3, width=4.5, sky=0.3)
        fr = bolt(fr, t, tb2, 152, (520, 120), (420, 700), inten=1.0, width=3.0, sky=0.2)
        fr = lit(fr, fl * 0.5)
        fr = rain_code(fr, t if t < tfz else tfz + (t - tfz) * 0.04, 150, inten=0.8, angle=-18, layers=(0, 1, 2),
                       freeze=sm(tfz, tfz + 0.2, t) * 0.6)
        foot = (900 + _par(u, 12), 875)
        fr = halo_tone(fr, (foot[0], 560), 420, 0.55 + 0.4 * fl)    # 网点背光把人从血红天边托出
        if t < tb2:
            fr, A = put(fr, self.a, t, 690, foot, wind=7)
        else:
            k = clamp((t - tb2) / 0.06)
            fr, A = put(fr, self.b, t, 700, foot, wind=9 * (1 - 0.7 * sm(tfz, tfz + 0.2, t)), mblur=(30 * (1 - k), 10 * (1 - k)))
        fr = lit(fr, 0.25 * fl)
        fr = mirror(fr, A, foot[1] - 4, amt=0.32, t=t)
        if t >= tb2:
            # 血振：刀尖（姿势二右下）甩出一扇血珠，慢放到悬停
            a_, s_ = self.b.fit(700)
            tip = (foot[0] + (0.80 - a_[0]) * self.b.w * s_, foot[1] + (0.73 - a_[1]) * self.b.h * s_)
            el = t - tb2
            te = el if t < tfz else (tfz - tb2) + (t - tfz) * 0.04
            for i, d in enumerate(self.drops):
                tt = max(0.0, te - d['d'])
                if tt <= 0: continue
                x = tip[0] + math.cos(d['a']) * d['v'] * tt; y = tip[1] + math.sin(d['a']) * d['v'] * tt + 900 * tt * tt
                if y > foot[1] + 40: continue
                fr = ink_drop(fr, (x, y), r=d['r'] * (1 - 0.2 * (i % 3)))
            fr = fr + pulse(t, tb2, 0.05) * 0.25
        fr = rain_fg(fr, t, 7, amt=0.45, speed=2400, scale=0.7, cam=(_par(u, 60), 0), freeze=tfz)
        dx, dy, dr = shake(t, 9 * pulse(t, tb2, 0.08) * (t >= tb2) + 1.0, 12, 1515)
        return C1.cam(fr, 1.0 + 0.03 * pulse(t, tb2, 0.12) * (t >= tb2), dx, dy, dr)


# ===================================================================================== 副歌二前半
class C16(Shot):
    """ECU 贴水面（保留字「血」，生图：血在水里洇成的「血」字）：画顶垂下刀尖，134.50「血」一滴血坠进积水（落水帧），
    涟漪荡开、血在水面洇开成一个躺在水上的「血」字（透视压扁、由落点向外显影）；135.06「冷」第二滴落下，字被涟漪搅动、边缘散成血丝但仍可读。
    分层：L1 积水原背景板（低机位，视差 0.25）/ L2 刀尖（同 C11 那把刀，竖直垂下）+ 倒影 / L3 水中血字（透视贴水面，被涟漪扭曲）/
    L4 近雨（生图，慢放 0.4）/ 代码：血珠、涟漪位移、血花（白 + 血红）、雨染红。"""
    def __init__(self):
        bg = plate('CA_water', 0.85).copy()
        lum = bg.mean(-1, keepdims=True)
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        wet = np.clip((yy * H - 540) / 40, 0, 1)                       # 水面去红（红留给水里的血字），天边保留一线血红
        self.bg = bg * (1 - wet) + (lum * 0.75) * wet
        self.blade = Prop('C11_blade', work=0.5)
        self.ch = Prop('C16_blood', work=0.5)
        hh, ww = self.ch.A.shape
        q0 = np.float32([[0, 0], [ww, 0], [ww, hh], [0, hh]])
        cx, cy, sw, sh = 960, 790, 1500, 600
        dst = np.float32([[cx - sw * 0.40, cy - sh * 0.5], [cx + sw * 0.40, cy - sh * 0.5], [cx + sw * 0.5, cy + sh * 0.5], [cx - sw * 0.5, cy + sh * 0.5]])
        self.Mp = cv2.getPerspectiveTransform(q0, dst)
        self.chA = cv2.warpPerspective(self.ch.A, self.Mp, (W, H)); self.chF = cv2.warpPerspective(self.ch.FA, self.Mp, (W, H))
        r = np.random.default_rng(16)
        self.nz = cv2.resize(cv2.GaussianBlur(r.random((H // 8, W // 8)).astype(np.float32), (0, 0), 2), (W, H))
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(np.float32)

    def render(self, t):
        u = self.u(t)
        t1, t2 = V(134.50), V(135.06)
        fr = view(self.bg, 1.35, 200 - _par(u, 30), -170)
        tip = (960, 430)
        fr, A = self.blade.draw(fr, self.blade.src(2020, 533), tip, 0.70, rot=-90)
        fr = mirror(fr, A, 600, amt=0.25, t=t)
        # 第二滴在刃尖聚起 → 135.06 前坠落
        # 第一滴落水 = 本镜切入帧（V(134.50) 早于 t0，镜头开在落水上）；第二滴在刃尖聚起 → 135.06 正落水
        if t1 <= t < t2:
            tf = t2 - 0.42                                           # 0.42s 自由落体 ≈ 刃尖(438) → 落点(770)
            gr = sm(t1 + 0.1, tf, t)
            yd = tip[1] + 8 + (0 if t < tf else 1900 * (t - tf) ** 2)
            if gr > 0: fr = ink_drop(fr, (960, min(yd, 770)), r=4 + 6 * gr)
        # 水中血字：自落点向外显影，被涟漪扭曲
        k = t - t1; k2 = max(0.0, t - t2)
        if k > 0:
            grow = eout(clamp(k / 0.32), 2)
            rr = np.sqrt((self.xx - 960) ** 2 + ((self.yy - 770) / 0.45) ** 2)
            rev = np.clip((grow * 900 - rr) / 70 + (self.nz - 0.5) * 2, 0, 1)
            amp = 1.5 + 2.5 * sm(0, 0.6, k) + 12.0 * eout(clamp(k2 / 0.6))
            mx = (self.xx + amp * (self.nz - 0.5) * 2 + 3 * math.sin(t * 4)).astype(np.float32)
            my = (self.yy + amp * 0.45 * (self.nz - 0.5) * 2).astype(np.float32)
            a = cv2.remap(self.chA, mx, my, cv2.INTER_LINEAR) * rev
            F = cv2.remap(self.chF, mx, my, cv2.INTER_LINEAR) * rev[..., None]
            if k2 > 0:
                sg = 1 + 6 * eout(clamp(k2 / 0.5)); a = cv2.GaussianBlur(a, (0, 0), sg) * (1 - 0.25 * sm(0, 0.5, k2)); F = cv2.GaussianBlur(F, (0, 0), sg) * (1 - 0.25 * sm(0, 0.5, k2))
            fr = fr * (1 - 0.92 * a[..., None]) + F * 0.92
            hi = np.clip(fr - 0.45, 0, None)
            fr = fr + hi * 0.3 * a[..., None]
        fr = water_ripple(fr, (960, 770), k + 0.02, flat=0.45, speed=700, amp=4 + 6 * sm(0.15, 0.4, k), y_top=600)
        fr = water_ripple(fr, (960, 770), k2 + 0.01 if t >= t2 else -1, flat=0.45, speed=760, amp=12, y_top=600)
        for tt, sd in ((t1, 161), (t2, 162)):
            fr = sparks(fr, t, sd, (960, 770), n=50, life=0.9, speed=(160, 440), dirc=(0, -1), spread=0.9, grav=2200, burst=True, t0=tt,
                        area=(60, 4), color=BRED, amt=0.9)
            fr = sparks(fr, t, sd + 9, (960, 770), n=24, life=0.7, speed=(160, 420), dirc=(0, -1), spread=0.9, grav=2200, burst=True, t0=tt,
                        area=(60, 4), color=WHITE, amt=0.6)
        tr = 134.0 + (t - 134.0) * 0.4
        fr = rain_fg(fr, tr, 8, amt=0.4, speed=2400, scale=0.7, cam=(_par(u, 40), 0))
        self.ca = 4 if 0 <= k2 < 0.1 else 0
        return fr


class C17(Shot):
    """MS 落地：鬼屠从画顶砸进积水单膝跪地、刀插水中（生图），135.71 冲击：水环扩散（涟漪位移）+ 水花（白 + 墨点）+ 冲击白光 + 震屏。
    分层：L1 积水原背景板（视差 0.3）/ L2 低雾 / L3 主体（下落时纵向拖影，落地后衣带、马尾风吹）+ 倒影 / L4 近雨（生图）/ 代码：涟漪、水花、雷光。"""
    def __init__(self):
        self.sp = spr('C17_kneel'); self.bg = plate('CA_water', 0.85, flip=True)

    def render(self, t):
        u = self.u(t)
        tl = V(135.71)
        fl = 0.5 * bolt_env(t, tl)
        fr = view(self.bg, 1.6, -260 - _par(u, 30), 60)
        fr = lit(fr, fl * 0.4)
        fr = K.fog(fr, t, 17, density=0.35, y0=640, y1=940, color=(0.8, 0.8, 0.8), speed=(50, 0))
        y = 890 if t >= tl else lerp(200, 890, ein(sm(self.t0, tl, t), 2))
        fr = water_ripple(fr, (960, 885), t - tl, flat=0.16, speed=1500, amp=16, wl=60, y_top=640)
        fr, A = put(fr, self.sp, t, 560, (960, y), wind=8, mblur=(0, 50) if t < tl else (0, 0))
        if t >= tl: fr = mirror(fr, A, 885, amt=0.25, t=t)
        if t >= tl:
            fr = sparks(fr, t, 171, (960, 885), n=160, life=0.9, speed=(400, 1100), dirc=(0, -1), spread=0.9, grav=2200, burst=True, t0=tl,
                        area=(420, 6), color=WHITE, amt=0.9)
            fr = halo_tone(fr, (960, 870), 420, 1.2 * pulse(t, tl, 0.06))
        fr = rain_fg(fr, t, 9, amt=0.45, speed=2400, scale=0.7, cam=(_par(u, 50), 0))
        self.ca = 5 if 0 <= t - tl < 0.1 else 0
        return fr


class C18(Shot):
    """LS 两翼冲锋（「刀不放」）：低机位，两翼重甲枪兵（生图三人拆成三个精灵）分六排从雨幕里冲来（远排压成雾中剪影，近排实色 + 前景虚化擦镜），
    中间通道里鬼屠起身拔刀（生图，半出鞘）；136.64 闪电把盔缨与枪尖全部勾亮。
    分层：L1 积水原背景板 / L2 远排甲士（雾化）/ L3 中雾 / L4 主体 / L5 近排甲士（大虚焦）/ L6 近雨（生图）/ 代码：闪电、雷光。"""
    def __init__(self):
        self.sold = Prop('C18_soldiers', work=0.5)                  # 三人一组整张刚体（不切：长枪、披风互相交叠）
        self.hero = spr('C18_draw'); self.bg = plate('CA_water', 0.8, recede=0.3)
        r = np.random.default_rng(18)
        self.units = []
        for row, z in enumerate((6.0, 4.6, 3.5, 2.6, 1.9, 1.35)):
            for side in (-1, 1):
                n = 2 if row < 3 else 1
                for i in range(n):
                    xw = side * (0.95 + (i + (0.5 if row % 2 else 0)) * 1.25 + r.uniform(-0.08, 0.08))
                    self.units.append(dict(z=z + r.uniform(-0.1, 0.1), xw=xw, k=int(r.integers(3)), ph=r.uniform(0, 6.28)))
        self.units.sort(key=lambda d: -d['z'])

    def _draw(self, fr, t, d, adv, fl):
        z = d['z'] - adv
        if z < 0.75: return fr
        fade = sm(0.75, 1.05, z)                                     # 最近一排冲过镜头前淡出（不在画内突然消失）
        hz = 600
        x = 960 + d['xw'] * 820 / z
        y = hz + 430 / z + 10 * abs(math.sin(t * 9 + d['ph'])) / z
        h = 760 / z
        if x < -h or x > W + h: return fr
        far = min(1.0, max(0.0, (z - 2.0) / 3.5))
        P = self.sold
        sc = h / 1050
        fr2, Aw = P.draw(fr, P.src(1024, 1080), (x, y), sc, alpha=fade)
        if far > 0.05:   # 雾化：远排压向雾色（中灰）
            fr2 = fr2 * (1 - Aw[..., None] * far * 0.65) + Aw[..., None] * far * 0.65 * (0.28 + 0.2 * fl)
        return fr2

    def render(self, t):
        u = self.u(t)
        fl = 0.8 * bolt_env(t, V(136.64)) + 0.3 * pulse(t, V(136.95), 0.12) * (t >= V(136.95))
        fr = view(self.bg, 1.3, 220 - _par(u, 20), -60)
        fr = bolt(fr, t, V(136.64), 181, (1250, 120), (1380, 560), inten=1.0, sky=0.3)
        fr = lit(fr, fl * 0.4)
        adv = 0.55 * u; hero_z = 1.6
        for d in self.units:
            if d['z'] - adv >= hero_z: fr = self._draw(fr, t, d, adv, fl)
        fr, A = put(fr, self.hero, t, 560, (960, 900 - 30 * eout(u)), wind=8)
        fr = lit(fr, fl * 0.2)
        for d in self.units:
            if d['z'] - adv < hero_z: fr = self._draw(fr, t, d, adv, fl)
        fr = rain_fg(fr, t, 10, amt=0.5, speed=2500, scale=0.7, cam=(_par(u, 60), 0))
        return fr


class C19(Shot):
    """MS 低机位「谁人来」：看不见人，只有四面八方刺进画面的红缨枪（生图枪，按角度排成一圈牢笼对准他），
    137.62「谁」137.92「人」逐拍再逼近一寸；137.92 他旋身一刀（拔刀姿 → 旋斩姿，硬切 + 角向模糊），一圈枪头连红缨被齐齐斩落、向外飞散，
    一道环形干笔飞白刀痕扫过，火星沿切口迸出（白 + 血红）。
    分层：L1 雷暴天背景板（虚焦）/ L2 远枪一圈（雾化轻虚）/ L3 主体两姿势 / L4 环形飞白刀痕 / L5 近枪（焦外大虚）/ L6 近雨（生图）。"""
    N = 15
    def __init__(self):
        im = cv2.imread(A_DIR + 'C19_spear_cut.png', cv2.IMREAD_UNCHANGED)
        h, w = im.shape[:2]; xx = np.broadcast_to(np.arange(w, dtype=np.float32)[None, :], (h, w))
        cut = np.clip((xx - 1240) / 3 + 0.5, 0, 1)                # 斩口在红缨后面的杆上（杆细，切口即刀口）
        self.shaft = Prop('C19_spear', mask=1 - cut, work=0.5)
        self.head = Prop('C19_spear', mask=cut, work=0.5)
        self.a = spr('C18_draw'); self.b = spr('C19_spin'); self.bg = plate('CA_sky', 0.75, recede=0.4, flip=True)
        r = np.random.default_rng(19)
        self.sp = []
        for i in range(self.N):
            a = -math.pi * 0.98 + (i + r.uniform(-0.3, 0.3)) / (self.N - 1) * math.pi * 0.96
            near = i % 4 == 0
            self.sp.append(dict(a=a, rad=r.uniform(400, 470), dep=1.5 if near else r.uniform(0.5, 0.9), near=near, spin=r.uniform(-9, 9),
                                fly=r.uniform(500, 900)))

    def _spear(self, fr, c, sp, close, t, ts, j):
        a = sp['a']; d = np.array([math.cos(a), math.sin(a)])
        P = c + d * sp['rad'] * close * max(0.85, sp['dep'])     # 枪尖
        ang = -math.degrees(math.atan2(-d[1], -d[0]))            # 枪头朝向 c（原图枪头朝右 = 0°）
        sc = 0.55 * sp['dep']
        blur = 0.0
        tip_src = self.head.src(2040, 576)
        cut = t >= ts + 0.012 * j
        kk = max(0.0, t - ts - 0.012 * j)
        if not cut:
            fr, _ = self.shaft.draw(fr, tip_src, tuple(P), sc, rot=ang, blur=blur)
            fr, _ = self.head.draw(fr, tip_src, tuple(P), sc, rot=ang, blur=blur)
        else:
            back = d * 220 * eout(kk / 0.3)
            fr, _ = self.shaft.draw(fr, tip_src, tuple(P + back), sc, rot=ang, blur=blur)
            off = d * sp['fly'] * kk + np.array([0, 1400 * kk * kk])
            fr, _ = self.head.draw(fr, tip_src, tuple(P + off), sc, rot=ang + sp['spin'] * kk * 40, blur=blur)
        return fr

    def render(self, t):
        u = self.u(t)
        ts = V(137.92); ti = [V(137.62), ts]
        fl = 0.6 * bolt_env(t, ts) + 0.4 * bolt_env(t, V(137.55))
        fr = view(self.bg, 1.35, 180 - _par(u, 50), -120)
        fr = lit(fr, fl * 0.4)
        fr = K.fog(fr, t, 19, density=0.4, y0=650, y1=1000, color=(0.8, 0.8, 0.8), speed=(40, 0))
        c = np.array([960.0, 600.0])
        close = 1.0 - 0.08 * sum(eout((t - x) / 0.12) for x in ti if t >= x)
        for j, sp in enumerate(self.sp):
            if not sp['near']: fr = self._spear(fr, c, sp, close, t, ts, j)
        fr = halo_tone(fr, (960, 640), 520, 0.6 + 0.4 * fl)      # 网点背光：把人从暗云里托出来
        fr = brush_slash(fr, (200, 760), (1740, 600), (t - ts) / 0.30, width=0.45)
        if t < ts:
            fr, A = put(fr, self.a, t, 600, (960, 900), wind=7)
        else:
            fr, A = put(fr, self.b, t, 610, (960, 900), wind=10, rotblur=-6 * (t - ts < 2 / FPS))
        if t >= ts:
            for j, sp in enumerate(self.sp):
                a = sp['a']; P = c + np.array([math.cos(a), math.sin(a)]) * sp['rad'] * close * max(0.85, sp['dep'])
                fr = sparks2(fr, t, 193 + j, tuple(P), ts + 0.012 * j, n=18, dirc=(math.cos(a), math.sin(a)), spread=0.9, speed=(200, 700), life=0.45)
        for j, sp in enumerate(self.sp):
            if sp['near']: fr = self._spear(fr, c, sp, close, t, ts, j)
        fr = rain_fg(fr, t, 11, amt=0.45, speed=2400, scale=0.7, cam=(_par(u, 60), 0))
        self.ca = 5 if 0 <= t - ts < 0.1 else 0
        return fr


class C20(Shot):
    """CU 太上皇（太上皇定妆照：长脸深纹、无须、黑白相间长发、黑纱袍、暗红腰带）：电光一亮他缓缓回头（138.42 / 138.88 两道闪电），
    分层：L1 雷暴天背景板（视差 0.3）/ L2 远雨 / L3 太上皇（散发风吹，回头：转角 + 横移两档缓动）/ L4 近雨（生图）/ 代码：闪电、雷光。"""
    def __init__(self):
        self.sp = spr('C20_emp'); self.bg = plate('CA_sky', 0.8)

    def render(self, t):
        u = self.u(t)
        tb, tz = V(138.42), V(138.88)
        fl = bolt_env(t, tb) + 0.8 * bolt_env(t, tz)
        fr = view(self.bg, 1.1, -_par(u, 40), 0, rot=180)
        fr = bolt(fr, t, tb, 201, (300, 120), (520, 900), inten=0.9, sky=0.3)
        fr = lit(fr, fl * 0.5)
        fr = rain_code(fr, t, 200, inten=0.6, angle=-16, layers=(0, 1))
        turn = eio(clamp((t - tb) / 0.6))
        fr, _ = put_src(fr, self.sp, t, (0.45, 1.0), (1180 - 40 * turn, 1000), 1780, wind=8, rot=3 - 4 * turn, breathe=0.0)
        fr = lit(fr, fl * 0.2)
        fr = rain_fg(fr, t, 12, amt=0.45, speed=2400, scale=0.7, cam=(_par(u, 60), 0))
        return fr


class C21(Shot):
    """对角分屏（保留字「邪」「正」，画进生图：左半血红雷云写血红「邪」、右半白云写墨黑「正」）：
    斜刀线（干笔飞白）把画面劈成两半，两半反向缓滑；左下鬼屠（雨中抬颌，定妆照）、右下太上皇（翻转后朝向分屏线）在各自半场对望，
    人物只占下半，不压字；139.48「邪」一拍分屏线白光一跳 + 轻震。
    分层：L1 邪正天背景板（左右两半各自反向滑动，同一张板）/ L2 两个主体（各自风吹）/ L3 分屏飞白刀痕 / L4 近雨（生图）。"""
    def __init__(self):
        self.bg = plate('C21_split', 1.0)
        self.hero = spr('C07_face'); self.emp = spr('C20_emp')
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(np.float32)

    def render(self, t):
        u = self.u(t)
        tx = V(139.48)
        d = (self.xx - 1020) * 0.88 + (self.yy - 540) * 0.47
        m = np.clip(d / 2 + 0.5, 0, 1)[..., None]
        # 用户 11-11：「人物太靠下了，允许人物盖住背景的字」→ 两人放大上移，眼睛约在画幅区上 1/3（y≈400），胸口以下进画；
        # 人物是前景层、字是背景层，人物压住字的一部分，每个字仍露出可认的大半。
        A = view(self.bg, 1.06, -40 - 20 * u, 115 - 8 * u)
        A, _ = put_src(A, self.hero, t, (1095 / 2048, 330 / 1152), (800 - 16 * u, 425 - 6 * u), 1380, wind=7, breathe=0.0)
        B = view(self.bg, 1.06, 60 + 20 * u, 115 + 8 * u)
        B, _ = put_src(B, self.emp, t, (1100 / 2048, 340 / 1152), (1290 + 16 * u, 425 + 6 * u), 1380, wind=7, breathe=0.0)   # 不翻转：散发向左飘（被分屏线切掉），回头看向左边的鬼屠，「正」右下不被头发盖住
        fr = A * (1 - m) + B * m
        pk = pulse(t, tx, 0.18) * (t >= tx)
        line = 0.9 * np.exp(-(d / 2.4) ** 2) + 0.35 * np.exp(-(d / 22) ** 2)
        fr = fr * (1 - np.clip(np.exp(-((np.abs(d) - 6) / 3.0) ** 2), 0, 1) * 0.8)[..., None]     # 刀线两沿墨线
        fr = fr + line[..., None] * (0.75 + 0.5 * pk)
        fr = rain_fg(fr, t, 13, amt=0.4, speed=2400, scale=0.7, cam=(_par(u, 50), 0))
        dx, dy, dr = shake(t, 6 * pk + 0.5, 12, 2121)
        return C1.cam(fr, 1.0, dx, dy, dr)


def _flip_put(fr, name, t, dst, width, src=(0.55, 1.0)):
    """水平翻转的精灵（太上皇在右半场朝左看分屏线）：复用 c_kit.spr 的翻转缓存；src = 翻转后精灵内的归一化锚点"""
    L = K.spr('R8_D/CA/' + name, flip=True)
    return L.draw(fr, t, src, dst, width / L.w, breathe=0.0, wind_amp=7, grade=NEU, rim=NORIM, wrap=0, shade=None)


# ===================================================================================== 接入
CLASSES = dict(C01=C01, C02=C02, C03=C03, C04=C04, C05=C05, C06=C06, C07=C07, C08=C08, C09=C09, C10=C10, C11=C11, C12=C12, C13=C13,
               C14=C14, C15=C15, C16=C16, C17=C17, C18=C18, C19=C19, C20=C20, C21=C21)


# 亮度对标标杆（S028–030 画幅区均值 ≈81，SPREAD §10 要求 ≥65）：每镜出画前一条 gamma 曲线——纯黑 / 纯白不动，只抬中灰（暗殿、雷暴夜）。
TONE = dict(C02=0.72, C04=0.58, C05=0.58, C06=0.68, C07=0.70, C08=0.82, C09=0.74, C10=0.68, C11=0.68, C12=0.85, C13=0.82,
            C14=0.80, C15=0.88, C16=0.68, C17=0.78, C18=0.74, C19=0.82, C20=0.82)


def _toned(cls, g):
    r0 = cls.render
    def render(self, t):
        return np.power(np.clip(r0(self, t), 0, None), g)
    cls.render = render
    return cls


def apply(mod):
    """sec_c_pre2_chorus2 末尾钩子调用：替换 SHOTS 里 C01–C21；t0/t1 取 CUT_F 实表（不改切点）。
    EXPO：段落统一 EXPO_ALL=1.22 是给第六轮暗调场景提亮的，风格 D 生图本身黑白分明 → 本单元镜头抵消回 1.0（同 V09 / 副歌一做法）。"""
    for i, S in enumerate(mod.SHOTS):
        nm = S.__name__
        if nm in CLASSES:
            N = CLASSES[nm]
            if nm in TONE and not getattr(N, '_toned', False):
                _toned(N, TONE[nm]); N._toned = True
            N.t0, N.t1 = S.t0, S.t1
            mod.SHOTS[i] = N
            mod.EXPO[nm] = 1.0 / mod.EXPO_ALL
