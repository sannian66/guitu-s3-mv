"""units/r8d_d.py — 第八轮风格 D · D 段「桥段」（帧 4839–5797，S01–S30）。只在 STYLE_D=1 时由 sec_d_bridge 接入。
设计见 crew/round8/D/D_NOTE.md。素材 assets/gen/R8_D/D/（nananobanana RH_image2，提示词 jobs/r8_D_D.json）。

原则（SPREAD_r8）：
- 切点 / 镜长 / 入出转场 / 字幕时刻与现版一致（镜头类的 t0/t1 照抄 sec_d_bridge）。
- 2:41–2:58（本段开头到 S15）的排比句字全部保留，并且全部画进生图：碑刻、秤梁刻字、朱印、圣旨墨书、血书、祭文。
  代码只负责「什么时候露出来」：先把字从生图里藏掉（GlyphPlate 补平载体），唱到哪个字就按载体的方式把原图像素揭开
  （刻：白灰凿痕 → 墨灌；血：从上往下渗；印：砸下；写：笔势方向擦开；血书：斩痕方向一刀划开；烧：火线烧出）。
  字形、笔画、材质全部来自生图，代码没有画任何字。2:58 以后（S16–S30）画面一个字都不出。
- 每镜 = 背景板 + 主体抠像（+ 前景 / 碎片 / 雨 / 火星 / 刀光），视差偏移以镜头中点为零，精灵按包围盒落脚。
- 色板黑 / 白 / 灰 / 血红（出画前 style_d.palette8 兜底），不用金色。
"""
import os, math, hashlib
import numpy as np, cv2
import c1kit as K
import d_kit as D
import sprite as SP
from d_kit import V, W, H, BAR

ROOT = os.environ.get('MV_ROOT', '/workspace/work/mv')
GEN = ROOT + '/assets/gen/R8_D/D/'
CACHE = os.environ.get('MV_TMP', '/tmp') + '/r8dd_cache/'
RED = np.array([0.74, 0.04, 0.04], np.float32)
WHT = np.array([1.0, 1.0, 1.0], np.float32)
INKC = np.array([0.03, 0.03, 0.03], np.float32)
NEU = dict(expo=1.0, sat=1.0, tint=(1.0, 1.0, 1.0), lift=0.0, gamma=1.0)
NORIM = dict(col=(1.0, 1.0, 1.0), amt=0.0, dir=(0.0, -1.0))
SPK = dict(grade=NEU, rim=NORIM, wrap=0, shade=None)


def cl(x): return K.clamp01(x)
def eo(x, k=3): return K.eout(x, k)
def ei(x, k=3): return K.ein(x, k)
def eio(x): return K.eio(x)
def lerp(a, b, u): return a + (b - a) * u
def hit(t, th, d=0.12): return 0.0 if t < th else math.exp(-(t - th) / d)


def imread(path, width=None):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 4: im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA)
    else: im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    if width and im.shape[1] != width:
        im = cv2.resize(im, (width, round(im.shape[0] * width / im.shape[1])), interpolation=cv2.INTER_AREA)
    return im.astype(np.float32) / 255


_PL = {}
def plate(name, width=None):
    k = (name, width)
    if k not in _PL: _PL[k] = imread(GEN + name + '.png', width)
    return _PL[k]


def view(img, cx, cy, vw, rot=0.0, out=(W, H), border=cv2.BORDER_REFLECT, flags=cv2.INTER_LINEAR):
    """源图（归一化中心 cx,cy，可视宽 vw = 源图宽的比例）→ 画面。缩小超过 0.7 倍时先降一级金字塔避免网点摩尔纹。"""
    h, w = img.shape[:2]
    ca, sa = abs(math.cos(math.radians(rot))), abs(math.sin(math.radians(rot)))
    ex = (vw * w * ca + vw * w * out[1] / out[0] * sa) / 2 / w       # 旋转后视窗半宽（归一化）
    ey = (vw * w * sa + vw * w * out[1] / out[0] * ca) / 2 / h
    if ex < 0.5: cx = min(max(cx, ex), 1 - ex)                      # 视窗出板会被镜像：夹回板内
    if ey < 0.5: cy = min(max(cy, ey), 1 - ey)
    s = out[0] / (vw * w)
    src = img
    while s < 0.7 and src.shape[1] > 400:
        src = cv2.pyrDown(src); s *= 2
    sw = src.shape[1] / w
    M = cv2.getRotationMatrix2D((cx * w * sw, cy * h * sw), rot, s)
    M[0, 2] += out[0] / 2 - cx * w * sw; M[1, 2] += out[1] / 2 - cy * h * sw
    return cv2.warpAffine(src, M, out, flags=flags, borderMode=border), M, sw


def to_screen(M, sw, img_shape, nx, ny):
    h, w = img_shape[:2]
    p = np.array([nx * w * sw, ny * h * sw, 1.0])
    return float(M[0] @ p), float(M[1] @ p)


def over(fr, rgba):
    a = rgba[..., 3:4]
    return fr * (1 - a) + rgba[..., :3] * a


def bg_cover(name, t, tm, z=1.0, par=(0.0, 0.0), cx=0.5, cy=0.5, vw=1.0, rot=0.0, blur=0, gain=1.0, rate=(0.0, 0.0)):
    """背景板：中点对齐，视差位移 par（像素/秒，以镜头中点为零）"""
    img = plate(name)
    dt = t - tm
    vis = vw / z                                         # 可视宽（源图宽的比例）；画面 1px = vis / W 个源图宽
    nx = cx - par[0] * dt * vis / W
    ny = cy - par[1] * dt * vis / W * img.shape[1] / img.shape[0]
    ang = rot + rate[0] * dt
    h0, w0 = img.shape[:2]
    ca, sa = abs(math.cos(math.radians(ang))), abs(math.sin(math.radians(ang)))
    hw, hh = vis * w0 / 2, vis * w0 / 2 * H / W            # 视窗半宽 / 半高（源图像素）
    bx, by = (hw * ca + hh * sa) / w0, (hw * sa + hh * ca) / h0   # 旋转后视窗外接框半宽 / 半高（归一化）
    k = max(bx / 0.4995, by / 0.4995, 1.0)                 # 外接框超出整板 → 收小视窗（等于推近）
    if k > 1.0: vis /= k; bx /= k; by /= k
    nx = min(max(nx, bx), 1 - bx)                         # 不让（旋转后的）视窗出板（出板会被镜像，出现对称假景）
    ny = min(max(ny, by), 1 - by)
    fr, _, _ = view(img, nx, ny, vis, ang)
    if blur: fr = haze(fr, blur)                         # 不做景深虚化（评审算 CG）：远景向纸白淡出
    return fr * gain


VID = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets/gen/R8_D/vid/D/')
_VC = {}
def vid_clip(name, t, t0=0.0, fps=24):
    """视频生成片段（SPREAD §13）：assets/gen/R8_D/vid/D/<name>.mp4，已是 2560×1440 / 24fps / 上下黑边各 184px、过色板兜底。
    t = 画面时刻，t0 = 该片段在成片里的起点（片段内时间 = t − t0）；裁掉生成片自带的黑边、按 24fps 时间取帧（30fps 渲染帧之间线性混合），
    缩到 1920×1080 的画幅区（y=BAR..H-BAR）。返回 (画面, 片段内时刻)。"""
    if name not in _VC:
        cap = cv2.VideoCapture(VID + name + '.mp4')
        fr = []
        while True:
            ok, f = cap.read()
            if not ok: break
            fr.append(f)
        cap.release()
        b = int(round((fr[0].shape[0] - fr[0].shape[1] / 2.39) / 2)) if fr else 184
        pic = [f[b:f.shape[0] - b, :, :] for f in fr]                 # 只留 2.39 画幅
        ph = H - 2 * BAR; pw = int(round(pic[0].shape[1] * ph / pic[0].shape[0]))
        ox = (pw - W) // 2
        out = [cv2.resize(f, (pw, ph), interpolation=cv2.INTER_AREA)[:, ox:ox + W] for f in pic]
        _VC[name] = (np.stack(out).astype(np.float32) / 255, fps)
    frames, fps = _VC[name]
    u = max(0.0, t - t0) * fps
    i = int(u); q = u - i
    a = frames[min(i, len(frames) - 1)]; b2 = frames[min(i + 1, len(frames) - 1)]
    canvas = np.zeros((H, W, 3), np.float32)
    canvas[BAR:H - BAR] = a * (1 - q) + b2 * q
    return canvas, u / fps


_FLOWN = {}
def _curl(seed, scale=420.0):
    """静态 curl 噪声速度场（单位幅度，屏幕 1/8 分辨率）：无散度，云沿等势线流、不会挤成一团"""
    if seed not in _FLOWN:
        h8, w8 = (H + 2 * FLOW_M) // 8 + 1, (W + 2 * FLOW_M) // 8 + 1
        r = np.random.default_rng(seed)
        psi = cv2.GaussianBlur(r.standard_normal((h8, w8)).astype(np.float32), (0, 0), scale / 8 / 2.5)
        psi = psi / (psi.std() + 1e-6)
        gy, gx = np.gradient(psi)
        vx, vy = gy, -gx
        k = 1.0 / (np.sqrt(vx ** 2 + vy ** 2).max() + 1e-6)
        _FLOWN[seed] = (vx * k, vy * k)
    return _FLOWN[seed]


FLOW_M = 110            # 流动位移的取样余量（屏幕像素）：视窗按 (W+2M)×(H+2M) 限位，位移永远取不到板外
def bg_flow(name, t, tm, z=1.0, cx=0.5, cy=0.5, par=(0.0, 0.0), blur=0, gain=1.0, rot=0.0,
            swirl=None, drift=None, turb=22.0, seed=0, lum_k=0.6):
    """会流动的天空 / 云 / 烟背景板（SPREAD §12-2：不是整张图旋转 / 平移）。
    以镜头中点 tm 为零做平流：每个屏幕点 p 取源点 p − Δ(p)·(t−tm)。
      swirl=(sx, sy, ω0, r0)：漩涡，(sx,sy) 是板上风眼归一化坐标；角速度 ω(r)=ω0·r0/(r+r0)（度/秒，内快外慢 = 差速旋转）
      drift=(sx, vx, vy)：撕裂云，板上竖缝 x=sx 两侧往外漂 vx（像素/秒），整体 vy
      turb：curl 噪声湍流（像素/秒）；lum_k：亮云带比暗云带快（亮度调速 = 前后两层云的视差）
    返回画面 RGB。"""
    img = plate(name)
    h0, w0 = img.shape[:2]
    dt = t - tm
    m = FLOW_M
    vis = 1.0 / z
    sx_, sy_ = (W + 2 * m) / W, (H + 2 * m) / W
    hw, hh = vis * w0 / 2 * sx_, vis * w0 / 2 * sy_
    ca, sa = abs(math.cos(math.radians(rot))), abs(math.sin(math.radians(rot)))
    bx, by = (hw * ca + hh * sa) / w0, (hw * sa + hh * ca) / h0
    k = max(bx / 0.4995, by / 0.4995, 1.0)
    if k > 1.0: vis /= k; bx /= k; by /= k
    nx = cx - par[0] * dt * vis / W
    ny = cy - par[1] * dt * vis / W * w0 / h0
    nx = min(max(nx, bx), 1 - bx); ny = min(max(ny, by), 1 - by)
    big, M, sw = view(img, nx, ny, vis * sx_, rot, out=(W + 2 * m, H + 2 * m))
    # 位移场（1/8 分辨率算，放大）
    h8, w8 = (H + 2 * m) // 8 + 1, (W + 2 * m) // 8 + 1
    yy, xx = np.mgrid[0:h8, 0:w8].astype(np.float32) * 8
    small = cv2.resize(big, (w8, h8), interpolation=cv2.INTER_AREA)
    lum = cv2.GaussianBlur(small.mean(-1), (0, 0), 3)
    spd = 1.0 + lum_k * (lum - lum.mean())
    dx = np.zeros_like(xx); dy = np.zeros_like(yy)
    if swirl is not None:
        ex, ey = to_screen(M, sw, img.shape, swirl[0], swirl[1])
        rx, ry = xx - ex, yy - ey
        rr = np.sqrt(rx ** 2 + ry ** 2)
        th = -np.radians(swirl[2] * swirl[3] / (rr + swirl[3]) * dt) * spd
        c, s_ = np.cos(th), np.sin(th)
        dx += xx - (ex + rx * c - ry * s_); dy += yy - (ey + rx * s_ + ry * c)
    if drift is not None:
        cx_s = to_screen(M, sw, img.shape, drift[0], 0.5)[0]
        side = np.tanh((xx - cx_s) / 160.0)
        dx += side * drift[1] * dt * spd; dy += drift[2] * dt * spd
    if turb:
        vx, vy = _curl(4100 + seed)
        dx += vx[:h8, :w8] * turb * dt * spd; dy += vy[:h8, :w8] * turb * dt * spd
    lim = m - 4
    mag = np.sqrt(dx ** 2 + dy ** 2); f = np.minimum(1.0, lim / np.maximum(mag, 1e-3))
    dx *= f; dy *= f
    DX = cv2.resize(dx, (W + 2 * m, H + 2 * m), interpolation=cv2.INTER_CUBIC)[m:m + H, m:m + W]
    DY = cv2.resize(dy, (W + 2 * m, H + 2 * m), interpolation=cv2.INTER_CUBIC)[m:m + H, m:m + W]
    gx, gy = K.grid()
    fr = cv2.remap(big, gx + m - DX, gy + m - DY, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if blur: fr = haze(fr, blur)
    return fr * gain


def haze(fr, k):
    """远景纵深：墨线保持清晰，整体向纸白淡出（k 越大越淡），代替高斯虚化"""
    h = min(0.55, 0.045 * k)
    return fr * (1 - h) + 0.94 * h


WIND_K = 0.5            # SPREAD §12-3：发梢 / 衣摆置换减半（sprite.wind 只作用在轮廓带 + 发丝权重上），避免果冻感
_SPR = {}
def spr(name):
    if name not in _SPR: _SPR[name] = SP.layer(GEN + name + '_cut.png')
    return _SPR[name]


EDGE_LOG = []
def _edge_check(tag, src_w, src_h, M, cut):
    """R8D_EDGE=1 时检查：源图四条边里「有内容被截断」的边（cut），变换到画面后是否落进画幅区（左右 0..W，上下 BAR..H-BAR）"""
    if os.environ.get('R8D_EDGE') != '1': return
    corners = {'top': [(0, 0), (src_w, 0)], 'bottom': [(0, src_h), (src_w, src_h)], 'left': [(0, 0), (0, src_h)], 'right': [(src_w, 0), (src_w, src_h)]}
    for side in cut:
        pts = np.array([[x, y, 1.0] for x, y in corners[side]]) @ np.asarray(M, np.float64)[:2].T
        n = 24; seg = np.linspace(pts[0], pts[1], n)
        inside = (seg[:, 0] > 2) & (seg[:, 0] < W - 2) & (seg[:, 1] > BAR + 2) & (seg[:, 1] < H - BAR - 2)
        if inside.any(): EDGE_LOG.append((tag, side, int(inside.sum())))


def cut_sides(A, thr=0.3, frac=0.004):
    h, w = A.shape
    out = []
    for side, v in (('top', A[0]), ('bottom', A[-1]), ('left', A[:, 0]), ('right', A[:, -1])):
        if (v > thr).mean() > frac: out.append(side)
    return out


def _sp_M(sp, anchor, dst, scale, rot):
    ax, ay = anchor[0] * sp.w, anchor[1] * sp.h
    M = cv2.getRotationMatrix2D((ax, ay), rot, scale)
    M[0, 2] += dst[0] - ax; M[1, 2] += dst[1] - ay
    return M


def put(fr, name, t, h, foot, rot=0.0, wind=5.0, breathe=0.004, look=None, alpha=1.0, mblur=(0, 0), defocus=0.0):
    """精灵按包围盒高度落脚（foot = 画面上脚底中点）；返回 (fr, 画面上的 alpha)。fr 会被原地改写。"""
    sp = spr(name)
    a, sc = sp.fit(h)
    if os.environ.get('R8D_EDGE') == '1':
        if not hasattr(sp, '_cut'): sp._cut = cut_sides(sp.A)
        _edge_check(name, sp.w, sp.h, _sp_M(sp, a, foot, sc, rot), sp._cut)
    return sp.draw(fr, t, a, foot, sc, rot=rot, wind_amp=wind * WIND_K, breathe=breathe, look=look, alpha=alpha, mblur=mblur, defocus=defocus, **SPK)


def put2(fr, name, t, anchor, dst, scale, rot=0.0, wind=5.0, breathe=0.004, look=None, alpha=1.0, mblur=(0, 0), defocus=0.0):
    """精灵锚点（归一化）放到画面 dst，scale = 画面像素 / 精灵像素（2048 宽工作分辨率）"""
    sp = spr(name)
    if os.environ.get('R8D_EDGE') == '1':
        if not hasattr(sp, '_cut'): sp._cut = cut_sides(sp.A)
        _edge_check(name, sp.w, sp.h, _sp_M(sp, anchor, dst, scale, rot), sp._cut)
    return sp.draw(fr, t, anchor, dst, scale, rot=rot, wind_amp=wind * WIND_K, breathe=breathe, look=look, alpha=alpha, mblur=mblur, defocus=defocus, **SPK)


def _cover(img, src, dst, s, rot):
    """RGB 背景板必须盖满画幅区（不许露出板边 / 镜像）：必要时平移取景点、不够大就放大"""
    h, w = img.shape[:2]
    src = [float(src[0]), float(src[1])]
    for _ in range(3):
        M = cv2.getRotationMatrix2D((src[0], src[1]), rot, s)
        M[0, 2] += dst[0] - src[0]; M[1, 2] += dst[1] - src[1]
        Mi = cv2.invertAffineTransform(M)
        q = np.array([[0, BAR - 4, 1], [W, BAR - 4, 1], [0, H - BAR + 4, 1], [W, H - BAR + 4, 1]], np.float64) @ Mi.T
        span_x, span_y = q[:, 0].max() - q[:, 0].min(), q[:, 1].max() - q[:, 1].min()
        k = max(span_x / (w - 2), span_y / (h - 2), 1.0)
        if k > 1.0:
            s *= k * 1.002; continue
        dx = max(0.0, 1 - q[:, 0].min()) - max(0.0, q[:, 0].max() - (w - 1))
        dy = max(0.0, 1 - q[:, 1].min()) - max(0.0, q[:, 1].max() - (h - 1))
        if abs(dx) < 0.5 and abs(dy) < 0.5: break
        src[0] += dx; src[1] += dy
    return tuple(src), s


def warp(img, src, dst, s, rot=0.0, border=cv2.BORDER_CONSTANT):
    """源图像素点 src → 画面 dst，缩放 s（画面像素 / 源像素），绕 src 旋转 rot 度。缩小时先降金字塔（防网点摩尔纹）。
    RGB 背景板（border=REFLECT）自动保证盖满画幅区。返回 (画面图, M)：M 把源图像素坐标映射到画面。"""
    if img.ndim == 3 and img.shape[2] == 3 and border == cv2.BORDER_REFLECT:
        src, s = _cover(img, src, dst, s, rot)
    im = img; sw = 1.0; ss = s
    while ss < 0.7 and im.shape[1] > 700:
        im = cv2.pyrDown(im); ss *= 2; sw *= 0.5
    M = cv2.getRotationMatrix2D((src[0] * sw, src[1] * sw), rot, ss)
    M[0, 2] += dst[0] - src[0] * sw; M[1, 2] += dst[1] - src[1] * sw
    out = cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=border)
    M2 = M.copy(); M2[:, :2] *= sw
    if os.environ.get('R8D_EDGE') == '1' and img.ndim == 3:
        h0, w0 = img.shape[:2]
        sides = ['top', 'bottom', 'left', 'right'] if img.shape[2] == 3 else cut_sides(img[..., 3])
        _edge_check('plate%dx%d' % (w0, h0), w0, h0, M2, sides)
    return out, M2


def pt(M, x, y):
    return float(M[0, 0] * x + M[0, 1] * y + M[0, 2]), float(M[1, 0] * x + M[1, 1] * y + M[1, 2])


def sprite_box(name):
    sp = spr(name); return sp.bbox


# ------------------------------------------------------------------------------------------------ 画进生图的字
class GlyphPlate:
    """一张画了字的生图：按列 / 行自动切出每个字的墨迹遮罩，生成「藏字底」（载体补平），按时间逐字揭开原图像素。
    cols: [(x0, x1, y0, y1, n, mode, axis)]，归一化坐标；mode 'dark'|'red'|'seal'；axis 'v'（竖排，上→下）|'h'（横排，左→右）。"""

    def __init__(self, name, cols, width, thr=0.32, rthr=0.22, fill_sig=(18, 18), hp_shift=(0.0, 0.06), dil=9, grow=0.0, hp_k=1.0):
        self.name = name
        st = os.stat(GEN + name + '.png')
        self._key = (name, width, cols, thr, rthr, dil, grow, st.st_size, int(st.st_mtime))
        img = plate(name, width)
        self.rgba = img.shape[2] == 4
        self.F = img[..., :3].copy(); self.A = img[..., 3].copy() if self.rgba else None
        h, w = self.F.shape[:2]; self.h, self.w = h, w
        F = self.F
        lum = F @ np.array([0.3, 0.59, 0.11], np.float32)
        red = F[..., 0] - np.maximum(F[..., 1], F[..., 2])
        self.boxes, self.masks, self.ink = [], [], []
        for (x0, x1, y0, y1, n, mode, axis) in cols:
            X0, X1, Y0, Y1 = int(x0 * w), int(x1 * w), int(y0 * h), int(y1 * h)
            if mode == 'dark': m = lum < thr
            elif mode == 'red': m = red > rthr
            elif mode == 'both': m = (lum < thr) | (red > rthr)
            else: m = red > rthr                      # seal：朱底，下面取凸包把白字一起包进来
            sub = np.zeros((h, w), np.uint8); sub[Y0:Y1, X0:X1] = m[Y0:Y1, X0:X1]
            sub = cv2.morphologyEx(sub, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
            if self.A is not None: sub = sub * (self.A > 0.5)
            prof = sub[Y0:Y1, X0:X1].sum(1 if axis == 'v' else 0).astype(np.float32)
            prof = np.convolve(prof, np.ones(9) / 9, 'same')
            L = len(prof)
            cuts = [0]
            for k in range(1, n):                       # 在期望位置 ±35% 字距内找投影最小处切开
                c = k * L / n; r = 0.35 * L / n
                a, b = int(c - r), int(c + r)
                cuts.append(a + int(np.argmin(prof[a:b])))
            cuts.append(L)
            for k in range(n):
                if axis == 'v': bx = (X0, Y0 + cuts[k], X1, Y0 + cuts[k + 1])
                else: bx = (X0 + cuts[k], Y0, X0 + cuts[k + 1], Y1)
                mk = np.zeros((h, w), np.uint8); mk[bx[1]:bx[3], bx[0]:bx[2]] = sub[bx[1]:bx[3], bx[0]:bx[2]]
                if mode == 'seal':                       # 印：整方（朱底 + 白字 + 印边）一起
                    mk = cv2.morphologyEx(mk, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
                    cs, _ = cv2.findContours(mk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if cs:
                        big = max(cs, key=cv2.contourArea)
                        mk = np.zeros_like(mk); cv2.drawContours(mk, [cv2.convexHull(big)], -1, 1, -1)
                ys, xs = np.nonzero(mk)
                if len(xs): bx = (max(0, xs.min() - 30), max(0, ys.min() - 30), min(w, xs.max() + 31), min(h, ys.max() + 31))
                soft = cv2.dilate(mk, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dil, dil))).astype(np.float32)
                if grow: soft = cv2.dilate(soft, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(grow), int(grow))))
                soft = cv2.GaussianBlur(soft, (0, 0), 1.6)
                self.boxes.append(bx); self.masks.append(np.ascontiguousarray(soft[bx[1]:bx[3], bx[0]:bx[2]]))
                self.ink.append(cv2.GaussianBlur(mk[bx[1]:bx[3], bx[0]:bx[2]].astype(np.float32), (0, 0), 1.0))   # 紧笔画遮罩（凹槽态用）
        self.clean = self._clean(fill_sig, hp_shift, hp_k)

    def _clean(self, sig, shift, hp_k):
        key = hashlib.md5(repr((self._key, self.boxes, sig, shift, hp_k, 4)).encode()).hexdigest()[:12]
        p = CACHE + f'{self.name}_{key}.png'
        if os.path.exists(p):
            return cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        hole = np.zeros((self.h, self.w), np.float32)
        for (x0, y0, x1, y1), m in zip(self.boxes, self.masks):
            hole[y0:y1, x0:x1] = np.maximum(hole[y0:y1, x0:x1], m)
        holeb = cv2.dilate((hole > 0.02).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
        F = self.F
        valid = 1 - holeb
        if self.A is not None: valid = valid * (self.A > 0.5)
        # 归一化卷积补平（多尺度，大洞也能补满），sig=(sx,sy)：木纹用横向长核
        s = 4
        Fs = cv2.resize(F, (self.w // s, self.h // s), interpolation=cv2.INTER_AREA)
        vs = cv2.resize(valid, (self.w // s, self.h // s), interpolation=cv2.INTER_AREA)
        fill = np.zeros_like(Fs); got = np.zeros(vs.shape, np.float32)
        for m in (1, 2, 4, 8):
            num = cv2.GaussianBlur(Fs * vs[..., None], (0, 0), sig[0] * m / s, sigmaY=sig[1] * m / s)
            den = cv2.GaussianBlur(vs, (0, 0), sig[0] * m / s, sigmaY=sig[1] * m / s)
            f = num / np.maximum(den, 1e-4)[..., None]
            ok = np.clip(den * 8, 0, 1) * (1 - got)
            fill = fill + f * ok[..., None]; got = got + ok
            if got.min() > 0.99: break
        fill = cv2.resize(fill, (self.w, self.h), interpolation=cv2.INTER_CUBIC)
        # 高频纹理从邻近无字处搬过来（纸纤维 / 石纹 / 木纹）
        hp = F - cv2.GaussianBlur(F, (0, 0), 3)
        hs = cv2.GaussianBlur(holeb, (0, 0), 2.0)[..., None]
        shifts = shift if isinstance(shift[0], (tuple, list)) else [shift]
        hps = np.zeros_like(F); got = np.zeros((self.h, self.w), np.float32)
        for sx, sy in shifts:                           # 按优先级取第一个落在「无字载体」上的偏移，搬高频纹理
            dx, dy = int(sx * self.w), int(sy * self.h)
            v = np.roll(np.roll(valid, dy, 0), dx, 1) * (1 - got)
            hps += np.roll(np.roll(hp, dy, 0), dx, 1) * v[..., None]; got += v
        vsh = np.ones((self.h, self.w), np.float32)
        clean = F * (1 - hs) + np.clip(fill + hps * vsh[..., None] * hp_k, 0, 1) * hs
        os.makedirs(CACHE, exist_ok=True)
        cv2.imwrite(p, cv2.cvtColor((np.clip(clean, 0, 1) * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR))
        return clean

    def center(self, k):
        x0, y0, x1, y1 = self.boxes[k]
        return (x0 + x1) / 2 / self.w, (y0 + y1) / 2 / self.h

    def compose(self, reveals, base=None):
        """reveals: {k: (r 场 (bh,bw) 或标量, 替换色 rgb (bh,bw,3) 或 None)} → 源空间 RGB（未揭开的字 = 藏字底）"""
        out = (self.clean if base is None else base).copy()
        for k, (r, alt) in reveals.items():
            x0, y0, x1, y1 = self.boxes[k]
            m = self.masks[k]
            if np.isscalar(r): r = np.full(m.shape, r, np.float32)
            a = (m * r)[..., None]
            src = self.F[y0:y1, x0:x1] if alt is None else alt
            out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - a) + src * a
        return out

    def field(self, k, prog, d=(0.0, 1.0), feather=0.18, seed=0, noise=0.12):
        """揭开场：沿方向 d 从 0 推到 1（prog），前沿带毛边；返回 (r, 前沿亮带)"""
        x0, y0, x1, y1 = self.boxes[k]
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        u = ((xx - x0) / max(1, x1 - x0) - 0.5) * d[0] + ((yy - y0) / max(1, y1 - y0) - 0.5) * d[1]
        u = u / (abs(d[0]) * 0.5 + abs(d[1]) * 0.5 + 1e-6) * 0.5 + 0.5
        nz = cv2.resize(D._tile(700 + seed + k * 13)[:32, :32], (x1 - x0, y1 - y0), interpolation=cv2.INTER_CUBIC) - 0.5
        f = prog * (1 + feather + noise) - u - nz * noise * 2
        r = np.clip(f / feather, 0, 1)
        edge = np.exp(-((f - feather * 0.15) / (feather * 0.35)) ** 2) * (0 < prog < 1)
        return r.astype(np.float32), edge.astype(np.float32)


# ------------------------------------------------------------------------------------------------ 风格 D 特效
def ink_rain(fr, t, seed, n=260, angle=12.0, speed=1900, length=(18, 70), amt=0.55, region=(0, BAR, W, H - BAR), white=0.85):
    """雨：细墨线短划，长短粗细有变化；亮处画黑线、暗处画白线（局部亮度自适应）"""
    r = np.random.default_rng(seed)
    x0 = r.uniform(region[0] - 200, region[2] + 200, n); ph = r.random(n); ln = r.uniform(*length, n)
    sp = speed * r.uniform(0.7, 1.3, n); wd = r.choice([1, 1, 1, 2], n)
    a = math.radians(angle); dx, dy = math.sin(a), math.cos(a)
    hgt = region[3] - region[1] + 300
    y = region[1] - 150 + ((t * sp + ph * hgt) % hgt)
    x = x0 + (y - region[1]) * dx / dy
    L = np.zeros((H, W), np.float32)
    for i in range(n):
        cv2.line(L, (int(x[i]), int(y[i])), (int(x[i] - dx * ln[i]), int(y[i] - dy * ln[i])), float(0.5 + 0.5 * ph[i]), int(wd[i]), cv2.LINE_AA)
    lum = cv2.GaussianBlur(fr.mean(-1), (0, 0), 12)
    col = np.where(lum > 0.55, 0.02, white)[..., None]
    a3 = (L * amt)[..., None]
    return fr * (1 - a3) + col * a3


def dry_slash(fr, p0, p1, prog, fade, width=26, seed=0, col=RED, core=True, splat=True):
    """干笔飞白斩痕：沿 p0→p1 推进 prog，笔肚实、两端飞白丝，外沿溅墨；core=True 中心一线白热"""
    if fade <= 0.01 or prog <= 0: return fr
    p0 = np.array(p0, np.float32); p1 = np.array(p1, np.float32)
    d = p1 - p0; Lg = float(np.linalg.norm(d)); d /= max(Lg, 1e-3); nrm = np.array([-d[1], d[0]])
    x, y = K.grid()
    rx = (x - p0[0]) * d[0] + (y - p0[1]) * d[1]
    ry = (x - p0[0]) * nrm[0] + (y - p0[1]) * nrm[1]
    u = rx / Lg
    key = ('dry', seed, W, H)
    if key not in _PL:
        fib = cv2.resize(D._tile(900 + seed)[:6, :], (W * 2, 64), interpolation=cv2.INTER_LINEAR)
        _PL[key] = fib
    fib = _PL[key]
    fu = np.clip(((u + 0.2) * W).astype(np.int32), 0, W * 2 - 1)
    fv = np.clip(((ry / (width * 2) + 0.5) * 63).astype(np.int32), 0, 63)
    fibv = fib[fv, fu]
    taper = np.clip(u * 6, 0, 1) * np.clip((prog - u) * 8, 0, 1) * np.clip((1.0 - u) * 5, 0, 1)
    wv = width * (0.35 + 0.65 * np.clip(np.sin(np.clip(u, 0, 1) * math.pi), 0, 1) ** 0.6)
    body = np.clip((wv - np.abs(ry)) / 3, 0, 1) * taper
    dry = np.clip((fibv - 0.42 + 0.5 * (np.abs(ry) / np.maximum(wv, 1))) * 3, 0, 1)
    m = body * (1 - dry * 0.85) * fade
    fr = fr * (1 - m[..., None]) + col * m[..., None]
    if core:
        c = np.exp(-(ry / (width * 0.12)) ** 2) * taper * fade * (1 - 0.5 * dry)
        fr = fr + c[..., None] * 0.9
    if splat:
        r = np.random.default_rng(seed + 77)
        S = np.zeros((H // 2, W // 2), np.float32)
        for i in range(60):
            uu = r.uniform(0, min(1, prog)); off = r.normal(0, width * 2.2)
            pp = p0 + d * uu * Lg + nrm * off
            cv2.circle(S, (int(pp[0] / 2), int(pp[1] / 2)), int(max(1, r.uniform(1, 6) * (1 - abs(off) / (width * 6)))), 1.0, -1, cv2.LINE_AA)
        S = cv2.resize(cv2.GaussianBlur(S, (0, 0), 0.6), (W, H))[..., None] * fade
        fr = fr * (1 - S) + col * S
    return fr


def chips(fr, t, t0, origin, seed, n=40, power=700, life=0.5, size=(2, 7), dark=True):
    """凿下来的石屑（黑芯白边）+ 白火星"""
    if t < t0 or t > t0 + life: return fr
    age = t - t0
    r = np.random.default_rng(seed)
    ang = r.uniform(-math.pi, 0.2, n); sp = r.uniform(0.3, 1, n) * power; sz = r.uniform(*size, n)
    Lk = np.zeros((H // 2, W // 2), np.float32); Lw = np.zeros_like(Lk)
    for i in range(n):
        px = origin[0] + math.cos(ang[i]) * sp[i] * age; py = origin[1] + math.sin(ang[i]) * sp[i] * age + 1400 * age * age
        k = 1 - age / life
        cv2.circle(Lk, (int(px / 2), int(py / 2)), max(1, int(sz[i] / 2)), k, -1, cv2.LINE_AA)
        cv2.circle(Lw, (int(px / 2 - 1), int(py / 2 - 1)), max(1, int(sz[i] / 4)), k, -1, cv2.LINE_AA)
    Lk = cv2.resize(Lk, (W, H))[..., None]; Lw = cv2.resize(Lw, (W, H))[..., None]
    fr = fr * (1 - Lk * 0.9) + (0.04 if dark else 0.9) * Lk * 0.9
    return fr + Lw * 0.7


def sparks_d(fr, t, seed, origin, n=50, red_frac=0.35, **kw):
    """火星：白 + 血红"""
    nw = int(n * (1 - red_frac))
    fr = K.sparks(fr, t, seed, origin, n=nw, color=(1.0, 1.0, 1.0), **kw)
    return K.sparks(fr, t, seed + 1, origin, n=n - nw, color=tuple(RED * 1.3), **kw)


def embers_d(fr, t, seed, n=70, **kw):
    fr = D.embers(fr, t, seed, n=int(n * 0.6), col=(1.0, 1.0, 1.0), **kw)
    return D.embers(fr, t, seed + 3, n=int(n * 0.4), col=tuple(RED * 1.4), **kw)


def speedlines(fr, t, seed, c=(960, 540), n=90, amt=0.6, r0=380, col=0.02, inward=True):
    """漫画集中线（黑）：从画面四周指向 c，逐帧换种子闪动"""
    r = np.random.default_rng(seed + int(t * 30))
    L = np.zeros((H // 2, W // 2), np.float32)
    for _ in range(n):
        a = r.uniform(0, 2 * math.pi); ra = r.uniform(r0, r0 + 220); rb = 1500
        w = int(r.choice([1, 1, 2, 3]))
        p0 = (c[0] + math.cos(a) * ra, c[1] + math.sin(a) * ra); p1 = (c[0] + math.cos(a) * rb, c[1] + math.sin(a) * rb)
        cv2.line(L, (int(p0[0] / 2), int(p0[1] / 2)), (int(p1[0] / 2), int(p1[1] / 2)), r.uniform(0.5, 1.0), w, cv2.LINE_AA)
    L = cv2.resize(L, (W, H))[..., None] * amt
    return fr * (1 - L) + col * L


def flash_inv(fr, k):
    """反白冲击帧（k=1 全反）"""
    if k <= 0.01: return fr
    return fr * (1 - k) + (1 - np.clip(fr, 0, 1)) * k


def shake_cam(fr, t, hits, amp=10, z=1.0, ox=0.0, oy=0.0, rot=0.0, decay=0.12):
    a = sum(amp * hit(t, h, decay) for h in hits)
    dx, dy, dr = K.shake(t, a, 14, int(t * 3) % 7)
    return K.cam(fr, z * (1 + 0.012 * a / max(1, amp)), ox + dx, oy + dy, rot + dr)
