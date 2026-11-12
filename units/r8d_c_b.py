"""units/r8d_c_b.py — 第八轮风格 D（日漫墨线 + 网点 + 黑白血红）· C 段后半 C22–C41（含 C35b、C40b），帧 4219–4839。
由 sec_c_pre2_chorus2.py 末尾的钩子在 STYLE_D=1 时 import 并调用 apply(本段模块)；STYLE_D=0 时不加载，现版逐像素不变。
切点 / 入出转场（CUTS）/ 运镜（MOV）/ 重拍冲击（KICKS）/ 闪切（INSERTS）/ 硬切冲击（HARD_FX）/ 段尾切黑全部沿用本段原表，
这里只替换镜头类（素材换成 assets/gen/R8_D/CB/ 的风格 D 生图分层，特效笔触改墨线 / 飞白 / 白 + 血红）。
用户点名：C24（2:23）「主角拖拽火花不好看，换个形式」→ 疾奔 + 「墙」拍急停仰望、墙体震裂落石；
          C32（2:32）「就一个断一截的剑头，啥意思」→ 全身入画、整把刀可见：蓄势 → 虚晃 → 十字双斩（飞白斩痕 + 反白冲击帧）；
          C23 石墙方牌（11-11）「圆规和直角尺太现代」→ 汉画像石浅浮雕墙石：伏羲执矩 / 女娲执规 / 墨斗弹线（生图 CB_relief），节奏不变；
          C37（2:36）牌匾字保留 → 「天不判」画进生图匾心，代码只做逐字灌血 + 雷劈；
          其余画面字（屏幕层「骨未凉 / 我自己扛 / 天不」、刻字）全部去掉。
评审通用问题（SPREAD §10/§11）：Shot.render = paper(draw)（白纸提亮，墨黑与血红不动，每镜 PK 控强度）+ 白纸背景板分镜换用；
景深虚化 → 向纸白渐隐（haze）；高斯辉光 / 光斑 → 硬边墨线星芒（star）；矢量冲击环 → 干墨水浪笔触；
天空 / 云：按流场推云（advect，§12-2），不是整张图平移；裁切边：背景视窗夹紧在底板内（_view）、贴画布边的精灵按不规则羽化处理（feathered）、CB_EDGECHK=1 逐帧自检。设计与积分见 crew/round8/CB/CB_NOTE.md。"""
import os, math, zlib
import numpy as np, cv2
import c_kit as K
import sprite as SP
import style_d
from c_kit import W, H, BAR, clamp, sm, eout, ein, eio, lerp, V, pulse, CT, bolt_env
from c1kit import crack_path, draw_crack
import c1kit as C1

ROOT = os.environ.get('MV_ROOT', '/workspace/work/mv')
A_DIR = ROOT + '/assets/gen/R8_D/CB/'
RED = np.array([0.80, 0.03, 0.03], np.float32)
WHITE = np.array([0.97, 0.97, 0.97], np.float32)
NEU = dict(expo=1.0, sat=1.0, tint=(1.0, 1.0, 1.0), lift=0.0, gamma=1.0)
NORIM = dict(col=(1.0, 1.0, 1.0), amt=0.0, dir=(0.0, -1.0))
T_C22 = 4219 / 30


# =====================================================================================================================
# 素材
_P = {}
def plate(n):
    """背景板 → float RGB，缩放到宽 1.12W（与原 plate_view 同口径，留运镜余量）"""
    if n not in _P:
        im = cv2.imread(A_DIR + n + '.png', cv2.IMREAD_COLOR)[..., ::-1]
        sc = W * 1.12 / im.shape[1]
        _P[n] = cv2.resize(im, (round(im.shape[1] * sc), round(im.shape[0] * sc)), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    return _P[n]


def _view(n, cx, cy, z, rot=0.0, dx=0.0, dy=0.0):
    """视窗夹紧：保证画面四角（含 dx/dy 视差平移、滚转）都落在底板内——任何一帧都不采到底板外（不出现镜像接缝 / 裁切边）。
    只平移视窗中心；底板放不下时才加大 z。返回 (cx, cy, z)。"""
    ph, pw = plate(n).shape[:2]
    for _ in range(3):
        M = cv2.getRotationMatrix2D((cx * pw, cy * ph), rot, z)
        M[0, 2] += W / 2 - cx * pw + dx; M[1, 2] += H / 2 - cy * ph + dy
        Mi = cv2.invertAffineTransform(M)
        c = np.array([[0, 0, 1], [W, 0, 1], [0, H, 1], [W, H, 1]], np.float64) @ Mi.T
        sx, sy = c[:, 0].max() - c[:, 0].min(), c[:, 1].max() - c[:, 1].min()
        if sx > pw - 2 or sy > ph - 2:
            z *= max(sx / (pw - 2), sy / (ph - 2)) * 1.002; continue
        ox = max(0.0, 1 - c[:, 0].min()) - max(0.0, c[:, 0].max() - (pw - 1))
        oy = max(0.0, 1 - c[:, 1].min()) - max(0.0, c[:, 1].max() - (ph - 1))
        return cx + ox / pw, cy + oy / ph, z
    return cx, cy, z


# 云流场（SPREAD §12-2）：天空不是整张图旋转 / 平移，而是按空间变化的流场推云——
# 每块云按自己所在位置的流向（旋度噪声 + 主风向）漂移，再叠一层随时间缓慢翻涌的湍流；地面板只在地平线以上生效。
# ft = 相对镜头中点的秒数（中点为零，与其他视差同一口径）；位移在底板像素空间算，镜头 ≤1.4s，最大 ±45px，不需要循环交叉淡化（无重影）。
FLOWS = {'CB_storm': ((-1.0, 0.25), None), 'CB_sky_paper': ((-1.0, 0.45), None), 'CB_sky_red': ((-1.0, 0.10), None),
         'CB_storm_ground': ((-1.0, 0.20), 0.62), 'CB_ground_paper': ((-1.0, 0.30), 0.70)}   # CB_gap_els 不加：上半是墙（刚体）
_FL = {}
def _curl(h, w, seed, cell):
    r = np.random.default_rng(seed)
    N = cv2.GaussianBlur(r.standard_normal((h // cell + 3, w // cell + 3)).astype(np.float32), (0, 0), 1.6)
    N = cv2.resize(N, (w, h), interpolation=cv2.INTER_CUBIC)
    gy, gx = np.gradient(N)
    c = np.stack([gy, -gx], -1); return c / (np.abs(c).max() + 1e-6)


def flow_field(n, flip):
    key = (n, flip)
    if key not in _FL:
        ph, pw = plate(n).shape[:2]
        (wx, wy), hor = FLOWS[n]
        base = _curl(ph, pw, zlib.crc32(n.encode()), 90) * 0.75 + np.array([wx, wy], np.float32) * 0.55
        t1, t2 = _curl(ph, pw, zlib.crc32(n.encode()) + 1, 50), _curl(ph, pw, zlib.crc32(n.encode()) + 2, 50)
        if flip: base, t1, t2 = (np.ascontiguousarray(a[:, ::-1] * np.array([-1, 1], np.float32)) for a in (base, t1, t2))
        m = np.ones((ph, 1, 1), np.float32)
        if hor is not None:                                                    # 地平线以下（地面 / 积水）不动
            yy = np.arange(ph, dtype=np.float32)[:, None, None] / ph
            m = np.clip((hor - yy) / 0.06, 0, 1)
        gy, gx = np.mgrid[0:ph, 0:pw].astype(np.float32)
        e = np.clip(np.minimum.reduce([gx, pw - 1 - gx, gy, ph - 1 - gy]) / 70.0, 0, 1)[..., None]   # 底板边 70px 内位移归零：不采到板外（不出镜像接缝）
        m = m * e
        _FL[key] = (base * m, t1 * m, t2 * m, gx, gy)
    return _FL[key]


def advect(P, n, flip, ft, speed=32.0, turb=9.0):
    """流场推云：P(x) ← P(x − F(x)·speed·ft − 湍流(t))"""
    base, t1, t2, gx, gy = flow_field(n, flip)
    w = 2 * math.pi * ft / 2.6
    d = base * (speed * ft) + (t1 * math.cos(w) + t2 * math.sin(w) - t1) * turb
    return cv2.remap(P, gx - d[..., 0], gy - d[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def pv(n, cx, cy, z, rot=0.0, dx=0.0, dy=0.0, redk=1.0, flip=False, ft=None):
    """背景板视窗：底板归一化坐标 (cx,cy) 落在画面中心，缩放 z，滚转 rot；dx/dy = 屏幕平移（视差）；redk<1 压低底板红（红留给斩痕）；
    flip = 左右镜像（同一张板换机位用，避免跨镜同构图）。视窗经 _view 夹紧在底板内。"""
    key = (n, round(redk, 3), flip)
    if key not in _P:
        P0 = plate(n)
        if redk < 1:
            lum = P0.mean(-1, keepdims=True); P0 = lum + (P0 - lum) * redk
        _P[key] = np.ascontiguousarray(P0[:, ::-1]) if flip else P0
    P = _P[key]
    if ft is not None and n in FLOWS: P = advect(P, n, flip, ft)
    ph, pw = P.shape[:2]
    cx, cy, z = _view(n, cx, cy, z, rot, dx, dy)
    M = cv2.getRotationMatrix2D((cx * pw, cy * ph), rot, z)
    M[0, 2] += W / 2 - cx * pw + dx; M[1, 2] += H / 2 - cy * ph + dy
    return cv2.warpAffine(P, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def plate_y(n, cx, cy, z, v):
    """底板归一化纵坐标 v 在画面上的 y（锁主体用：人钉在底板上，随底板一起被摇；与 pv 同一夹紧）"""
    cx, cy, z = _view(n, cx, cy, z)
    return H / 2 + (v - cy) * plate(n).shape[0] * z


def plate_x(n, cx, cy, z, u):
    cx, cy, z = _view(n, cx, cy, z)
    return W / 2 + (u - cx) * plate(n).shape[1] * z


# 白纸提亮（风格 D 亮度对标标杆）：只抬中间调（网点灰 → 纸白），墨黑（<0.04）不动，血红不动
_PX = np.array([0.0, 0.04, 0.12, 0.25, 0.45, 0.70, 1.0], np.float32)
_PY = np.array([0.0, 0.035, 0.19, 0.42, 0.70, 0.90, 1.0], np.float32)
def paper(fr, k=1.0):
    if k <= 0: return fr
    l = np.clip(fr, 0, 1).mean(-1)
    d = (np.interp(l, _PX, _PY).astype(np.float32) - l) * k
    return fr + (d * (1 - style_d.red_mask(fr)))[..., None]                    # 血红（style_d 同一口径）不提


def haze(fr, k, tone=0.86):
    """纵深：向纸白渐隐（压对比、抬黑），替代景深虚化——远处仍是清晰墨线"""
    return fr * (1 - k) + tone * k


def star(fr, c, r, amt, ang=0.0):
    """墨线星芒：硬边白十字（细长四芒 + 墨线勾边），替代高斯辉光 / 写实光斑"""
    if amt <= 0.02 or r < 2: return fr
    S = 2; m = np.zeros((H // S, W // S), np.float32)
    cx, cy = c[0] / S, c[1] / S; rr = r / S
    for da, ln, wd in ((0, 1.0, 0.06), (90, 1.0, 0.06), (45, 0.45, 0.05), (135, 0.45, 0.05)):   # 长十字 + 短斜十字
        a = math.radians(ang + da); ux, uy = math.cos(a), math.sin(a); vx, vy = -uy, ux
        L_ = rr * ln; wd_ = max(1.0, rr * wd)
        pts = np.array([[cx + ux * L_, cy + uy * L_], [cx + vx * wd_, cy + vy * wd_], [cx - ux * L_, cy - uy * L_], [cx - vx * wd_, cy - vy * wd_]])
        cv2.fillPoly(m, [np.round(pts * 4).astype(np.int32)], 1.0, cv2.LINE_AA, 2)
    k = np.clip(cv2.dilate(m, np.ones((3, 3), np.uint8)) - m, 0, 1)
    m = cv2.resize(m, (W, H))[..., None] * min(1.0, amt); k = cv2.resize(k, (W, H))[..., None] * min(1.0, amt)
    fr = fr * (1 - 0.9 * k) + k * 0.02
    return fr * (1 - m) + m * 1.05


_FEATH = {}
def feathered(n):
    """贴到自身画布边的精灵：贴边那几侧乘一道不规则羽化（宽 28–70px、沿边起伏），画布直边永远不会以直线出现在画面里（SPREAD §11-7）。
    处理结果缓存到 MV_TMP，不改素材文件；不贴边的精灵原样返回路径。"""
    if n in _FEATH: return _FEATH[n]
    src = A_DIR + n + '_cut.png'
    im = cv2.imread(src, cv2.IMREAD_UNCHANGED); a = im[..., 3].astype(np.float32) / 255
    h, w = a.shape; r = np.random.default_rng(zlib.crc32(n.encode()))
    f = np.ones_like(a); hit = False
    for side in ('top', 'bottom', 'left', 'right'):
        line = {'top': a[0], 'bottom': a[-1], 'left': a[:, 0], 'right': a[:, -1]}[side]
        if (line > 0.02).sum() < 2: continue
        hit = True
        nl = len(line)
        R = np.interp(np.arange(nl), np.linspace(0, nl - 1, 24), r.uniform(28, 70, 24)).astype(np.float32)
        R = cv2.GaussianBlur(R[None, :], (0, 0), 12)[0]
        if side in ('top', 'bottom'):
            d = np.arange(h, dtype=np.float32)[:, None] if side == 'top' else (h - 1 - np.arange(h, dtype=np.float32))[:, None]
            g = np.clip(d / R[None, :], 0, 1)
        else:
            d = np.arange(w, dtype=np.float32)[None, :] if side == 'left' else (w - 1 - np.arange(w, dtype=np.float32))[None, :]
            g = np.clip(d / R[:, None], 0, 1)
        f = f * (g * g * (3 - 2 * g))
    if not hit:
        _FEATH[n] = src; return src
    im[..., 3] = np.round(a * f * 255).astype(np.uint8)
    d_ = os.path.join(os.environ.get('MV_TMP', '/tmp'), 'cb_feather'); os.makedirs(d_, exist_ok=True)
    out = os.path.join(d_, n + '_cut.png'); cv2.imwrite(out, im)
    _FEATH[n] = out
    return out


def L(n): return SP.layer(feathered(n))


WK = 0.5
def put(fr, t, n, foot=None, h=None, anc=None, dst=None, s=None, rot=0.0, wind=6.0, breathe=0.004, expo=1.0, **kw):
    """精灵合成（风格 D：grade=NEU、rim=NORIM、wrap=0、shade=None）。foot+h：按包围盒高度落脚；anc+dst+s：源锚点 → 屏幕点，s = 精灵像素倍率"""
    sp = L(n)
    if h is not None:
        a, s_ = sp.fit(h)
        if s is None: s = s_
        if anc is None: anc = a
        if dst is None: dst = foot
    g = dict(NEU); g['expo'] = expo
    wind = min(wind * WK, 7.0)                                                 # SPREAD §12-3：风吹位移场是规则正弦叠加 → 降幅、封顶，避免果冻感
    if EDGECHK: _edgechk(n, sp, t, anc, dst, s * (1 + abs(breathe)), rot)
    return sp.draw(fr, t, anc, dst, s, rot=rot, breathe=breathe, wind_amp=wind, grade=g, rim=NORIM, wrap=0, shade=None, **kw)


# 裁切边自检（SPREAD §11-7）：精灵 alpha 贴到自身画布边的那几段，变换到屏幕后不得落在画幅区（去上下黑边）内
EDGECHK = os.environ.get('CB_EDGECHK') == '1'
_EDGE = {}
def _edgechk(n, sp, t, anc, dst, s, rot):
    if n not in _EDGE:
        raw = cv2.imread(A_DIR + n + '_cut.png', cv2.IMREAD_UNCHANGED)[..., 3]          # 原素材 alpha（不是羽化后的）：贴边段 = 潜在裁切边
        A = cv2.resize(raw, (sp.w, sp.h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255; segs = []
        for side, line in (('top', A[0]), ('bottom', A[-1]), ('left', A[:, 0]), ('right', A[:, -1])):
            on = np.where(line > 0.25)[0]
            if len(on) < 3: continue
            ln = len(line) - 1
            for i0, i1 in ((g[0], g[-1]) for g in np.split(on, np.where(np.diff(on) > 3)[0] + 1)):
                pts = {'top': [(i0, 0), (i1, 0)], 'bottom': [(i0, sp.h - 1), (i1, sp.h - 1)],
                       'left': [(0, i0), (0, i1)], 'right': [(sp.w - 1, i0), (sp.w - 1, i1)]}[side]
                segs.append((side, np.array(pts, np.float64)))
        _EDGE[n] = segs
    ax, ay = anc[0] * sp.w, anc[1] * sp.h
    M = cv2.getRotationMatrix2D((ax, ay), rot, s); M[0, 2] += dst[0] - ax; M[1, 2] += dst[1] - ay
    for side, pts in _EDGE[n]:
        q = np.c_[pts, np.ones(2)] @ M.T
        mg = 70 * s                                                          # 羽化带最宽 70 源像素：带内任何一点进画幅区都算
        xy = q[0] + (q[1] - q[0]) * np.linspace(0, 1, 17)[:, None]
        dep = np.minimum.reduce([xy[:, 0], W - xy[:, 0], xy[:, 1] - BAR, H - BAR - xy[:, 1]])   # >0：在画幅区内的深度（px）
        if dep.max() > -mg:
            i = int(dep.argmax())
            print(f'EDGE {n} {side} depth={dep.max() + mg:.0f} t={t:.3f} f={t * 30:.1f} at ({xy[i, 0]:.0f},{xy[i, 1]:.0f})', flush=True)


def spt(n, s, anc, dst, rot, p):
    """精灵内归一化点 p → 屏幕坐标（与 SpriteLayer.draw 同一仿射）"""
    sp = L(n); ax, ay = anc[0] * sp.w, anc[1] * sp.h
    M = cv2.getRotationMatrix2D((ax, ay), rot, s); M[0, 2] += dst[0] - ax; M[1, 2] += dst[1] - ay
    return M @ np.array([p[0] * sp.w, p[1] * sp.h, 1.0])


_RK = []
def rocks():
    """生图碎石（CB_debris）按连通域拆成单块 RGBA，供落石 / 飞石用（不画矢量多边形）"""
    if not _RK:
        im = cv2.imread(A_DIR + 'CB_debris_cut.png', cv2.IMREAD_UNCHANGED)
        im = cv2.resize(im, (1024, 576), interpolation=cv2.INTER_AREA)
        n, lab, st, _ = cv2.connectedComponentsWithStats((im[..., 3] > 40).astype(np.uint8), 8)
        for i in range(1, n):
            x, y, w, h, ar = st[i]
            if ar < 300: continue
            sub = im[y:y + h, x:x + w].astype(np.float32)[..., [2, 1, 0, 3]] / 255
            sub[..., 3] *= (lab[y:y + h, x:x + w] == i)
            lum = sub[..., :3].mean(-1, keepdims=True)
            sub[..., :3] = (lum + (sub[..., :3] - lum) * 0.35) * sub[..., 3:4]   # 碎石上的红压到暗红；预乘 alpha（rgba_put 按预乘反算）
            _RK.append(np.ascontiguousarray(sub))
    return _RK


def rgba_put(fr, rgba, cx, cy, size, rot=0.0, alpha=1.0, blur=0.0, gain=1.0):
    h, w = rgba.shape[:2]; s = size / max(h, w)
    r = int(size * 0.75) + 6
    x0, y0, x1, y1 = max(0, int(cx - r)), max(0, int(cy - r)), min(W, int(cx + r)), min(H, int(cy + r))
    if x1 <= x0 or y1 <= y0 or alpha <= 0.01: return fr
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, s); M[0, 2] += cx - w / 2 - x0; M[1, 2] += cy - h / 2 - y0
    o = cv2.warpAffine(rgba, M, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
    if blur > 0.3: o = cv2.GaussianBlur(o, (0, 0), blur)
    a = o[..., 3:4] * alpha
    fr[y0:y1, x0:x1] = fr[y0:y1, x0:x1] * (1 - a) + np.clip(o[..., :3] / np.clip(o[..., 3:4], 1e-3, None), 0, 1) * gain * a
    return fr


def rockfall(fr, t, t0, seed, n, xr, y0, size=(30, 90), grav=1500, vy=(0, 300), vx=(-80, 80), spin=300, life=1.5, alpha=1.0, blur=0.0):
    if t < t0: return fr
    r = np.random.default_rng(seed); R = rocks()
    dl, x0, vx_, oy, vy_, sz, sp, r0 = (r.uniform(0, 0.25, n), r.uniform(*xr, n), r.uniform(*vx, n), r.uniform(-60, 60, n), r.uniform(*vy, n),
                                        r.uniform(*size, n), r.uniform(-1, 1, n), r.uniform(0, 360, n))     # 每块参数一次取齐（跳过不影响后面的块）
    for i in range(n):
        a = t - t0 - dl[i]
        if a < 0 or a > life: continue
        x = x0[i] + vx_[i] * a; y = y0 + oy[i] + vy_[i] * a + 0.5 * grav * a * a
        if y > H + 100: continue
        fr = rgba_put(fr, R[i % len(R)], x, y, sz[i], rot=sp[i] * spin * a + r0[i], alpha=alpha, blur=blur)
    return fr


# =====================================================================================================================
# 风格 D 特效笔触
def ink_rain(fr, t, seed, n=240, ang=10.0, speed=1900.0, amt=0.75, length=(40, 140), cam=(0.0, 0.0), freeze=None):
    """细墨线短划雨：长短粗细有变化；亮处是墨（黑）、暗处是白丝（漫画雨）。cam 以镜头中点为零"""
    if freeze is not None: t = freeze
    r = np.random.default_rng(seed)
    x0 = r.uniform(-300, W + 300, n); y0 = r.uniform(0, H + 300, n); sp = r.uniform(0.7, 1.3, n) * speed
    ln = r.uniform(*length, n); wd = r.integers(1, 3, n); al = r.uniform(0.35, 1.0, n)
    th = math.radians(ang); dx, dy = math.sin(th), math.cos(th)
    y = (y0 + sp * t) % (H + 300) - 150
    x = (x0 + y * dx / dy + cam[0]) % (W + 600) - 300
    y = y + cam[1]
    m = np.zeros((H // 2, W // 2), np.float32)
    for i in range(n):
        cv2.line(m, (int(x[i] / 2), int(y[i] / 2)), (int((x[i] - dx * ln[i]) / 2), int((y[i] - dy * ln[i]) / 2)), float(al[i]), int(wd[i]), cv2.LINE_AA)
    m = cv2.resize(m, (W, H))[..., None] * amt
    lum = cv2.blur(np.clip(fr, 0, 1).mean(-1), (41, 41))[..., None]
    ink = np.where(lum > 0.52, 0.03, 0.90).astype(np.float32)
    return fr * (1 - m) + ink * m


def brush(fr, p0, p1, q, width=80.0, bend=0.10, seed=0, life=0.35, hot=1.0, splat=1.0, amt=1.0, col=None):
    """干笔飞白斩痕：q = 进度（0→1 笔头划过，>1 后按 life 渐隐）。血红笔身（边缘飞白断丝）+ 白热芯（刚划过时）+ 溅墨 / 溅血。"""
    if q <= 0: return fr
    head = min(1.0, q)
    fade = 1.0 if q <= 1 else math.exp(-(q - 1) / life)
    if fade < 0.03: return fr
    key = (tuple(map(float, p0)), tuple(map(float, p1)), float(width), float(bend), seed, float(splat))
    if head >= 1 and key in _BR:
        Mr, Mk, Mw = _BR[key]
        return _brush_comp(fr, Mr, Mk, Mw, fade, amt, hot, q, col)
    S = 2; h, w = H // S, W // S
    p0 = np.array(p0, np.float64) / S; p1 = np.array(p1, np.float64) / S
    d = p1 - p0; Ln = np.linalg.norm(d); n = np.array([-d[1], d[0]]) / Ln
    c = (p0 + p1) / 2 + n * bend * Ln
    ss = np.linspace(0, head, max(10, int(80 * head)))
    pts = ((1 - ss) ** 2)[:, None] * p0 + (2 * (1 - ss) * ss)[:, None] * c + (ss ** 2)[:, None] * p1
    tap = np.clip(np.sin(np.pi * ss) ** 0.5, 0.06, 1)
    wd = width / S
    r = np.random.default_rng(seed)
    Mr = np.zeros((h, w), np.float32); Mw = np.zeros_like(Mr); Mk = np.zeros_like(Mr)
    core = np.vstack([pts + n * (wd * 0.10 * tap)[:, None], (pts - n * (wd * 0.10 * tap)[:, None])[::-1]])
    cv2.fillPoly(Mr, [np.round(core * 4).astype(np.int32)], 1.0, cv2.LINE_AA, 2)
    for i in range(30):                                                       # 笔毛：外圈断得多（飞白）
        o = (i / 29 - 0.5) + r.normal(0, 0.02)
        g = r.random(60)
        on = np.interp(ss * 59, np.arange(60), g) > (0.22 + 1.1 * abs(o))
        pp = np.round((pts + n * (o * wd * tap)[:, None]) * 4).astype(np.int32)
        th = int(r.integers(1, 4))
        for k in range(len(pp) - 1):
            if on[k]: cv2.line(Mr, tuple(pp[k]), tuple(pp[k + 1]), 1.0, th, cv2.LINE_AA, 2)
        if abs(o) < 0.16:
            for k in range(len(pp) - 1):
                if on[k] and g[int(ss[k] * 59)] > 0.3: cv2.line(Mw, tuple(pp[k]), tuple(pp[k + 1]), 1.0, 1, cv2.LINE_AA, 2)
    for i in range(int(40 * splat)):                                          # 溅墨 / 溅血：沿笔路、偏向笔尾
        sidx = int(np.clip(r.beta(2.2, 1.2) * len(pts), 0, len(pts) - 1))
        off = r.normal(0, 1.1) * wd
        pc = pts[sidx] + n * off + r.normal(0, 3, 2)
        rad = max(1, int(r.uniform(1, 4.5) * (1.4 - min(1, abs(off) / wd) * 0.6)))
        cv2.circle(Mk if i % 3 == 0 else Mr, (int(pc[0] * 4), int(pc[1] * 4)), rad * 4, 1.0, -1, cv2.LINE_AA, 2)
    Mr = cv2.resize(cv2.GaussianBlur(Mr, (0, 0), 0.6), (W, H))[..., None]
    Mk = cv2.resize(Mk, (W, H))[..., None]
    Mw = cv2.resize(Mw, (W, H))[..., None]
    if head >= 1:
        if len(_BR) > 24: _BR.clear()
        _BR[key] = (Mr, Mk, Mw)
    return _brush_comp(fr, Mr, Mk, Mw, fade, amt, hot, q, col)


_BR = {}
def _brush_comp(fr, Mr, Mk, Mw, fade, amt, hot, q, col=None):
    Mr = Mr * (fade * amt); Mk = Mk * (fade * amt)
    hw = hot * math.exp(-max(0.0, q - 0.6) / 0.5) * fade * amt
    fr = fr * (1 - Mk) + Mk * 0.02
    fr = fr * (1 - Mr) + Mr * (RED if col is None else np.asarray(col, np.float32))
    if hw > 0.02:
        fr = fr * (1 - Mw * hw) + Mw * hw * 1.05
        fr = fr + cv2.GaussianBlur(Mw[..., 0], (0, 0), 10)[..., None] * WHITE * 0.6 * hw
    return fr


def invert(fr):
    """反白冲击帧：黑白反转（硬边）"""
    l = np.clip(fr, 0, 1).mean(-1)
    v = np.clip(1.10 - l * 1.08, 0, 1) ** 1.35
    return np.repeat(v[..., None], 3, -1).astype(np.float32)


def speed_lines(fr, t, seed, amt=0.8, horiz=True, y0=140, y1=940):
    if amt <= 0.01: return fr
    r = np.random.default_rng(seed + int(round(t * 30)))
    Lk = np.zeros((H // 2, W // 2), np.float32); Lw = np.zeros_like(Lk)
    for i in range(70):
        yy = r.uniform(y0, y1) / 2; xx = r.uniform(-200, W) / 2; ln = r.uniform(180, 700) / 2
        cv2.line(Lk if i % 3 else Lw, (int(xx), int(yy)), (int(xx + ln), int(yy)), r.uniform(0.4, 1.0), 1 if i % 4 else 2, cv2.LINE_AA)
    Lk = cv2.resize(cv2.GaussianBlur(Lk, (0, 0), 0.6), (W, H)); Lw = cv2.resize(cv2.GaussianBlur(Lw, (0, 0), 0.6), (W, H))
    fr = fr * (1 - np.clip(Lk * 0.85 * amt, 0, 1))[..., None]
    return fr + (Lw * 0.9 * amt)[..., None]


def spark2(fr, t, seed, o, n=80, t0=None, burst=True, **kw):
    """火星：白 + 血红"""
    fr = C1.sparks(fr, t, seed, o, n=n, t0=t0, burst=burst, color=(1.0, 0.97, 0.94), **kw)
    return C1.sparks(fr, t, seed + 7, o, n=max(8, n // 2), t0=t0, burst=burst, color=(0.85, 0.04, 0.03), **kw)


def bright(fr, fl):
    """闪电照亮：暗部抬、亮部推（白光，不加色）"""
    return fr * (1 + 0.55 * fl) + 0.10 * fl


def flash_white(fr, k):
    return fr * (1 + 0.6 * k) + 0.35 * k


def ink_cracks(seed, c, n, reach, jag=0.08):
    cr = np.zeros((H // 4, W // 4), np.float32)
    for i in range(n):
        a0 = i / n * 6.283 + 0.4 + np.random.default_rng(seed + i).uniform(-0.3, 0.3)
        p = crack_path(c, (c[0] + math.cos(a0) * reach, c[1] + math.sin(a0) * reach * 0.7), seed + i, n=22, jag=jag)
        cr = np.maximum(cr, draw_crack(cr.shape, p / 4, 1, branches=2, seed=seed + i, prog=1.0))
    return cr


def stonefog(fr, t, seed, density, y0, y1):
    return K.fog(fr, t, seed, density=density, y0=y0, y1=y1, color=(0.62, 0.62, 0.62), speed=(40, 0))


class Shot:
    t0 = t1 = 0.0; ca = 0                                   # 色差由本段 Sec.frame 统一处理（只在 INSERTS 闪切帧）
    PK = 1.0                                                # 白纸提亮强度（SPREAD §10-1：画幅区平均亮度 ≥65）
    def render(self, t): return paper(self.draw(t), self.PK)
    def u(self, t): return clamp((t - self.t0) / (self.t1 - self.t0))
    def par(self, t): return self.u(t) - 0.5                 # 视差 / 粒子位移以镜头中点为零
    def ft(self, t): return t - 0.5 * (self.t0 + self.t1)     # 云流场时间（秒，中点为零）


# =====================================================================================================================
class C22(Shot):
    """140.63–142.00「若规则是」。前半：脚部特写（黑靴踩湿礁石、刀尖点石、袍角滴水），背后雷暴平原虚焦；
    141.32 雷闪硬切大全景：城墙从积水直插雷云（极低机位仰拍、缓慢上摇），墙脚礁石上一个小小的人背对镜头仰望。人钉在底板礁石上。"""
    PK = 0.8
    def draw(self, t):
        tb = V(141.32); p = self.par(t)
        if t < tb:
            k = clamp((t - self.t0) / (tb - self.t0))
            bg = pv('CB_ground_paper', 0.5, 0.40, 1.10 + 0.02 * k, dx=-30 * p, redk=0.6, ft=self.ft(t))
            fr = haze(bg, 0.25)                                                 # 远景平原：清晰墨线 + 向纸白渐隐（不做景深虚化）
            fr = bright(fr, 0.6 * bolt_env(t, self.t0 + 0.02))
            z = 1.0 + 0.05 * eio(k)
            fr, _ = put(fr, t, 'CB_feet', anc=(0.5, 0.97), dst=(960, 1000), s=W * 1.08 / L('CB_feet').w * z, wind=5, breathe=0)
            fr = C1.sparks(fr, t, 2201, (900, 420), n=22, life=0.8, speed=(10, 60), dirc=(0, 1), spread=0.2, grav=1500, area=(260, 30),
                          color=(0.95, 0.95, 0.95), amt=0.8)                  # 袍角滴水
            fr = stonefog(fr, t, 2202, 0.35, 820, 960)
            return ink_rain(fr, t, 2203, n=200, ang=8, amt=0.7)
        k = clamp((t - tb) / max(1e-3, self.t1 - tb))
        fl = bolt_env(t, tb) + 0.7 * bolt_env(t, V(141.94))
        cy = lerp(0.56, 0.515, eio(k)); z = 1.0 + 0.04 * k
        fr = pv('CB_wall_els', 0.5, cy, z)
        fr = bright(fr, 0.8 * fl)
        fr = K.bolt(fr, t, tb, 2211, (1500, BAR), (1330, 430), inten=0.9)
        fr = K.bolt(fr, t, V(141.94), 2212, (420, BAR), (520, 360), inten=0.6)
        px = plate_x('CB_wall_els', 0.5, cy, z, 0.47); py = plate_y('CB_wall_els', 0.5, cy, z, 0.805)     # 墙脚礁石面
        sh = np.zeros((H // 2, W // 2), np.float32)
        cv2.ellipse(sh, (int(px / 2), int(py / 2)), (34, 5), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        fr = fr * (1 - 0.8 * cv2.resize(cv2.GaussianBlur(sh, (0, 0), 3), (W, H))[..., None])
        fr, _ = put(fr, t, 'CB_lookup', foot=(px, py), h=190 * z, wind=6, expo=1.0 + 0.4 * fl)
        fr = stonefog(fr, t, 2213, 0.4, 800, 960)
        return ink_rain(fr, t, 2214, n=260, ang=8, amt=0.75)


class C23(Shot):
    """142.00–143.37「铁 / 壁 / 铜」。同一面城墙推近（亮墙面板 CB_wall_bright），三块墙石逐拍从墙里推出、逼近镜头——
    用户：「圆规和直角尺……太现代了，换成古风的含义表达」→ 墙石正面是汉画像石浅浮雕（生图 CB_relief，与墙同质：裂缝、雨水、血红渗出）：
    ① 伏羲执矩（曲尺）② 女娲执规（两脚木规）③ 墨斗弹线（准绳）——「规矩」的本义图形，无金属框、无刻度、无文字。
    推出时墙面按石块轮廓凹陷压暗、碎石掉落（生图碎石）、镜头横移；出现节奏与卡点沿用原表（铁 / 壁 / 铜）。"""
    PK = 0.15
    _T = None
    def tiles(self):
        if C23._T is None:
            im = cv2.imread(A_DIR + 'CB_relief_cut.png', cv2.IMREAD_UNCHANGED)
            a = im[..., 3]; cols = np.where((a > 128).sum(0) > 20)[0]
            gaps = np.where(np.diff(cols) > 8)[0]
            xs = [g for g in np.split(cols, gaps + 1) if len(g) > 100]    # 丢掉零星噪点列
            out = []
            for seg in xs:
                x0, x1 = max(0, seg[0] - 24), min(im.shape[1], seg[-1] + 25)
                sub = im[:, x0:x1]; rows = np.where((sub[..., 3] > 128).any(1))[0]
                sub = sub[max(0, rows[0] - 24):rows[-1] + 25].astype(np.float32)[..., [2, 1, 0, 3]] / 255
                sub = cv2.copyMakeBorder(sub, 16, 16, 16, 16, cv2.BORDER_CONSTANT, value=0)   # 四周留透明边：缩放旋转后不出现直线裁切
                sub[..., :3] *= sub[..., 3:4]                                                # 预乘 alpha
                out.append(np.ascontiguousarray(sub))
            assert len(out) == 3, len(out)
            C23._T = out
        return C23._T

    @staticmethod
    def amask(rgba, cx, cy, size):
        h, w = rgba.shape[:2]; s = size / max(h, w)
        M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, s); M[0, 2] += cx - w / 2; M[1, 2] += cy - h / 2
        M /= 2                                                                         # 半分辨率坐标
        return cv2.resize(cv2.warpAffine(np.ascontiguousarray(rgba[..., 3]), M, (W // 2, H // 2), flags=cv2.INTER_LINEAR), (W, H))

    def draw(self, t):
        u = self.u(t); p = self.par(t)
        ks = (4, 5, 6)
        fl = sum(0.6 * bolt_env(t, V(CT(34, k))) for k in ks)
        fr = pv('CB_wall_bright', lerp(0.45, 0.55, eio(u)), 0.5, 1.15 + 0.10 * u)
        fr = bright(fr, 0.5 * fl)
        pos = [(470, 545), (960, 575), (1450, 525)]
        T = self.tiles()
        for i, k in enumerate(ks):
            ti = min(V(CT(34, k)), self.t1 - 0.12)       # 「铜」143.48 落在切点之后：第三块提前到切点前 0.12s 推出，保证三块都看得到
            if t < ti - 0.15: continue
            x, y = pos[i]; x -= 120 * u
            e = eout((t - ti + 0.15) / 0.22)
            sz = 520 * (0.80 + 0.28 * e + 0.06 * (t - ti))
            dx, dy = (x - 960) * 0.08 * e, (y - 540) * 0.08 * e
            hole = self.amask(T[i], x, y, 520 * 0.80)                                      # 墙上留下的石窝：石块轮廓（不是矩形）
            hole = cv2.GaussianBlur(hole, (0, 0), 3)
            fr = fr * (1 - hole[..., None] * 0.85 * e)
            sh = self.amask(T[i], x + dx + 14 + 10 * e, y + dy + 18 + 12 * e, sz)          # 投影：同一轮廓偏移
            fr = fr * (1 - cv2.GaussianBlur(sh, (0, 0), 9)[..., None] * 0.7 * e)
            fr = rgba_put(fr, T[i], x + dx, y + dy, sz, alpha=1.0, gain=1.0 + 0.4 * fl)
            fr = rockfall(fr, t, ti - 0.05, 2300 + i, 5, (x - 140, x + 140), y + 120, size=(14, 40), grav=1800, life=0.9)
            fr = C1.dust(fr, t, 2310 + i, n=60, amt=0.7 * e * (1 - sm(0.2, 0.8, t - ti)), drift=(0, 220),
                        region=(int(x - 150), int(y - 40), int(x + 150), int(y + 280)), size=(1, 4), color=(0.9, 0.9, 0.9))
        return ink_rain(fr, t, 2320, n=200, ang=4, amt=0.6, cam=(-60 * p, 0))


class C24(Shot):
    """143.37–144.77「（铜）墙」——用户：「主角拖拽火花不好看，换个形式」。重做：不再刀尖拖火花。
    横移跟拍：他沿墙根向左疾奔（墙面板疾掠 + 横向运动模糊 + 黑白漫画速度线 + 两层墨色残影）；
    143.94「墙」：急停——换急停仰望姿势（CB_runstop2：以 CB_run 为底图图生图衍生，同朝向、同服装），墙体一记低频震、从顶上裂下一道墨线裂缝、生图碎石砸落，镜头随急停甩停 + 震屏。"""
    PK = 1.0
    def draw(self, t):
        u = self.u(t); tw = V(143.94); p = self.par(t)
        if t < tw:
            k = clamp((t - self.t0) / (tw - self.t0))
            fr = pv('CB_wall_close', 0.66 - 0.24 * k, 0.48, 1.6, flip=True)
            fr = C1.motion_blur(fr, 38, 0)
            fr = speed_lines(fr, t, 2401, 0.7)
            x = 1020 - 90 * k; yb = 945 - 10 * abs(math.sin(t * 13))
            for gk, ga in ((2, 0.14), (1, 0.26)):                                   # 墨色残影（运动尾部）
                fr, _ = put(fr, t - 0.03 * gk, 'CB_run', foot=(x + 70 * gk, yb), h=560, wind=10, alpha=ga, mblur=(-18, 0), expo=0.5)
            fr, _ = put(fr, t, 'CB_run', foot=(x, yb), h=560, wind=10, rot=-1.5 * math.sin(t * 13), mblur=(-8, 0))
            fr = C1.dust(fr, t, 2402, n=50, amt=0.6, drift=(500, -40), region=(0, 860, W, 960), size=(1, 4), color=(0.9, 0.9, 0.9))
            return ink_rain(fr, t, 2403, n=220, ang=-14, amt=0.7)
        a = t - tw
        st = eout(clamp(a / 0.18), 2)
        fr = pv('CB_wall_close', 0.42 - 0.012 * st, 0.48 - 0.03 * eout(clamp(a / 0.9)), 1.6 + 0.05 * eout(clamp(a / 0.9)), flip=True)   # 甩停 + 仰
        q = clamp(a / 0.22)
        cr = ink_cracks(2404, (960, BAR), 5, 700 * eout(q), jag=0.10)
        crm = cv2.resize(cr, (W, H))[..., None]
        fr = fr * (1 - 0.9 * crm) + cv2.resize(cv2.GaussianBlur(cr, (0, 0), 1.2), (W, H))[..., None] * 0.35 * math.exp(-a / 0.3)
        fr = bright(fr, 0.8 * pulse(t, tw, 0.12))
        fr = rockfall(fr, t, tw + 0.02, 2405, 9, (420, 1500), BAR - 80, size=(40, 120), grav=2200, vy=(100, 500), life=1.2)
        fr = C1.dust(fr, t, 2406, n=160, amt=0.8 * math.exp(-a / 0.5), drift=(0, 260), region=(300, BAR, 1620, 700), size=(1, 4),
                    color=(0.9, 0.9, 0.9))
        x = 930 + 22 * (1 - st)
        fr, _ = put(fr, t, 'CB_runstop2', foot=(x, 950), h=580, wind=9, breathe=0.004, mblur=(-30 * (1 - st), 0))
        fr = stonefog(fr, t, 2407, 0.4 * math.exp(-a / 0.6), 760, 960)
        return ink_rain(fr, t, 2408, n=220, ang=6, amt=0.7)


class C25(Shot):
    """144.77–145.67「那就劈」。ECU 仰拍贴墙（荷兰角）：145.14 一柄刀身自下而上竖直贯穿全画（速度拖影），墙沿中轴被劈开、向两侧错开，
    缝里灌出白光（缝心白热线 + 血红边），劈缝上留一道干笔飞白斩痕；火星白 + 血红，碎石落下。"""
    PK = 0.0
    def __init__(self):
        r = np.random.default_rng(25)
        ys = np.linspace(0, H, 28); self.jag = np.interp(np.arange(H), ys, r.normal(0, 7, 28)).astype(np.float32)[:, None]
        b = cv2.imread(A_DIR + 'CB_blade_cut.png', cv2.IMREAD_UNCHANGED).astype(np.float32)[..., [2, 1, 0, 3]] / 255
        ys_, xs_ = np.nonzero(b[..., 3] > 0.01)                                # 包围盒按极淡 alpha 取，裁剪不切到边缘
        b = b[ys_.min():ys_.max() + 1, xs_.min():xs_.max() + 1]
        b[..., :3] *= b[..., 3:4]                                              # 预乘 alpha（缩放 / 拖影模糊后再反算）
        self.blade = np.ascontiguousarray(np.rot90(b, -1))                    # 顺时针 90°：原图左端刀尖 → 朝上

    def draw(self, t):
        u = self.u(t); ts = V(145.14); k = t - ts
        fl = 1.1 * pulse(t, ts, 0.14) + 0.5 * bolt_env(t, V(144.86))
        base = pv('CB_wall_bright', 0.62, lerp(0.58, 0.48, eio(u)), 2.1 + 0.12 * u, rot=6 - 2 * u)
        base = bright(base * 0.9, 0.6 * fl)
        sx = 960; xx = np.arange(W)[None, :]
        gap = 0.0 if k < 0 else 80 * eout(clamp(k / 0.35)) + 20 * clamp((k - 0.35) / 0.3)
        if gap > 0:
            Lh = cv2.warpAffine(base, np.float32([[1, 0, -gap / 2], [0, 1, 6 * clamp(k / 0.3)]]), (W, H), borderMode=cv2.BORDER_REFLECT)
            Rh = cv2.warpAffine(base, cv2.getRotationMatrix2D((960, 1000), -1.2 * clamp(k / 0.3), 1.0 + 0.03 * clamp(k / 0.3)) + np.float32([[0, 0, gap / 2], [0, 0, -4 * clamp(k / 0.3)]]),
                                (W, H), borderMode=cv2.BORDER_REFLECT)
            eL = sx - gap / 2 + self.jag; eR = sx + gap / 2 + self.jag
            mL = np.clip(eL - xx + 0.5, 0, 1)[..., None]; mR = np.clip(xx - eR + 0.5, 0, 1)[..., None]
            d = np.abs(xx - sx - self.jag).astype(np.float32)
            sky = np.clip(0.75 + 0.5 * np.exp(-(d / max(8, gap * 0.25)) ** 2), 0, 1.6)[..., None] * WHITE
            fr = Lh * mL + Rh * mR + sky * np.clip(1 - mL - mR, 0, 1)
            for ex in (eL, eR):                                                 # 断口：墨线 + 血红热边
                e1 = np.exp(-((xx - ex) / 2.2) ** 2)[..., None]; e2 = np.exp(-((xx - ex) / 7.0) ** 2)[..., None]
                fr = fr * (1 - 0.9 * e1) + e2 * RED * 0.9 * math.exp(-k / 0.35)
            fr = brush(fr, (sx + 4, H + 40), (sx - 6, -40), 1.0 + k / 0.08, width=150, bend=0.02, seed=251, life=6.0, hot=0.0, amt=0.75)
            fr = rockfall(fr, t, ts, 252, 8, (sx - 120, sx + 120), 300, size=(20, 70), grav=1600, vy=(-200, 100), vx=(-200, 200), life=1.0)
            fr = spark2(fr, t, 253, (960, 560), n=150, life=0.7, speed=(200, 1000), dirc=(0, 1), spread=2.6, grav=1100, t0=ts, area=(20, 520))
        else:
            fr = base
        sp = clamp((k + 0.06) / 0.14)
        if -0.08 < k < 0.10:                                                    # 刀身自下而上（速度拖影）
            B = self.blade; bh = 1500
            Bs = cv2.resize(B, (110, bh), interpolation=cv2.INTER_AREA)
            ytip = lerp(H + 200, -300, ein(sp, 1.3)) - 40
            ky = int(9 + 140 * pulse(t, ts - 0.01, 0.06)) | 1
            Bs = cv2.GaussianBlur(Bs, (1, ky), 0)
            x0 = int(sx + 6 - Bs.shape[1] / 2); y0 = int(ytip)
            ys0, ys1 = max(0, y0), min(H, y0 + bh); xs0, xs1 = max(0, x0), min(W, x0 + Bs.shape[1])
            if ys1 > ys0 and xs1 > xs0:
                sub = Bs[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]; a = sub[..., 3:4]
                c = np.clip(sub[..., :3] / np.clip(a, 1e-3, None), 0, 1) * (1.0 + 0.6 * fl)
                fr[ys0:ys1, xs0:xs1] = fr[ys0:ys1, xs0:xs1] * (1 - a) + c * a
            G = np.zeros((H, W), np.float32); cv2.line(G, (sx, H), (sx, int(max(0, ytip + 300))), 1.0, 3, cv2.LINE_AA)
            fr = fr + cv2.GaussianBlur(G, (0, 0), 8)[..., None] * WHITE * 0.8 + G[..., None] * RED * 0.6
            fr = spark2(fr, t, 254, (sx, max(BAR, ytip + 40)), n=90, life=0.5, speed=(300, 1100), dirc=(0, 1), spread=1.4, grav=1500,
                        burst=False, amt=1.0)
        fr = stonefog(fr, t, 255, 0.25, 700, 960)
        return ink_rain(fr, t, 256, n=200, ang=-8, amt=0.6)


class C26(Shot):
    """145.67–146.57「开它看」。崩塌（慢放）：同一面墙从劈缝中心炸成上百块真实墙面石片朝镜头飞来（纹理采自墙面板，每块墨线勾边、
    朝缺口一侧白边受光、背光侧压暗），缺口后是被电光照白的雷云天；前景再飞过几块生图碎石。"""
    PK = 0.0
    def __init__(self):
        r = np.random.default_rng(26)
        S = 2; w, h = W // S, H // S
        pts = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
        for _ in range(170):
            a = r.uniform(0, 6.283); d = (r.random() ** 0.85) * 640
            pts.append((min(w - 1, max(0, w / 2 + math.cos(a) * d * 1.2)), min(h - 1, max(0, h / 2 + 20 + math.sin(a) * d * 0.75))))
        sd = cv2.Subdiv2D((-200, -200, w + 400, h + 400))
        for p_ in pts: sd.insert((float(p_[0]), float(p_[1])))
        facets, _ = sd.getVoronoiFacetList([])
        self.tris = []
        for q in facets:
            q = np.asarray(q, np.float32).reshape(-1, 2)
            q[:, 0] = np.clip(q[:, 0], 0, w - 1); q[:, 1] = np.clip(q[:, 1], 0, h - 1)
            if cv2.contourArea(q) < 30: continue
            c = q.mean(0); d = math.hypot(c[0] - w / 2, (c[1] - h / 2 - 20) / 0.75)
            if q[:, 0].min() < 1 or q[:, 0].max() > w - 2 or q[:, 1].min() < BAR / S + 1 or q[:, 1].max() > (H - BAR) / S - 2:
                d = 1e4                                                        # 贴画幅边的石块不飞（飞走会把画布直边带进画面）
            self.tris.append((q, c, d, r.uniform(-1, 1), r.uniform(0.6, 1.3), r.uniform(0.75, 1.1)))
        self.S = S
        self.wall = cv2.resize(pv('CB_wall_bright', 0.62, 0.5, 2.0), (w, h)) * 0.9          # 与 C25 同一面墙
        nz = cv2.GaussianBlur(r.random((h, w)).astype(np.float32), (0, 0), 2.5)
        self.nz = (nz - nz.mean()) / (nz.std() + 1e-6)

    def draw(self, t):
        k = (t - self.t0) * 0.55 + 0.04
        fl = 0.6 + 0.4 * math.sin(t * 13) ** 2
        S = self.S; w, h = W // S, H // S
        sky = pv('CB_storm', 0.62, 0.42, 1.25, ft=self.ft(t))
        lum = sky.mean(-1, keepdims=True)
        sky = np.clip(0.55 + lum * 0.9, 0, 1.2) * np.ones(3, np.float32)            # 缺口后的天：电光照白（云纹仍在）
        sky = cv2.resize(sky, (w, h))
        out = sky.copy()
        for q, c, d, sp, sz, gn in sorted(self.tris, key=lambda z: -z[2]):
            e = max(0.0, k - d / 900.0 * 0.25)
            fly = e * max(0.0, 1.7 - d / 520.0) * sz
            m = np.zeros((h, w), np.float32); cv2.fillPoly(m, [q.astype(np.int32)], 1.0, cv2.LINE_AA)
            x0, y0 = q.min(0).astype(int); x1, y1 = q.max(0).astype(int) + 2
            if fly <= 0.002:
                sub = (slice(max(0, y0), min(h, y1)), slice(max(0, x0), min(w, x1)))
                mm = m[sub][..., None]; out[sub] = out[sub] * (1 - mm) + self.wall[sub] * mm
                continue
            sl = (slice(max(0, y0 - 4), min(h, y1 + 5)), slice(max(0, x0 - 4), min(w, x1 + 5)))
            mb = cv2.GaussianBlur(m[sl], (0, 0), 2.0); m[sl] = np.clip((mb + 0.16 * self.nz[sl] - 0.5) * 6 + 0.5, 0, 1)
            sc = 1 + 1.6 * fly * fly
            dirv = np.array([c[0] - w / 2, c[1] - h / 2 - 20], np.float32); dirv /= (np.linalg.norm(dirv) + 1e-3)
            mv = dirv * (fly * 260 + fly * fly * 300)
            M = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), sp * 160 * fly, sc); M[:, 2] += mv
            src = np.zeros_like(self.wall); src[sl] = self.wall[sl] * m[sl][..., None] * gn
            Am = cv2.warpAffine(m, M, (w, h)); Pm = cv2.warpAffine(src, M, (w, h))
            Ab = cv2.GaussianBlur(Am, (0, 0), 1.2); gy_, gx_ = np.gradient(Ab)
            cxp, cyp = M[0, 0] * c[0] + M[0, 1] * c[1] + M[0, 2], M[1, 0] * c[0] + M[1, 1] * c[1] + M[1, 2]
            lx, ly = w / 2 - cxp, h / 2 + 20 - cyp; ln = math.hypot(lx, ly) + 1e-3; lx, ly = lx / ln, ly / ln
            facing = np.clip(-(gx_ * lx + gy_ * ly) * 2.5, 0, 1)
            back = np.clip((gx_ * lx + gy_ * ly) * 2.5, 0, 1)
            ink = np.clip(Am - cv2.erode(Am, np.ones((3, 3), np.uint8)), 0, 1)       # 墨线勾边
            Pm = Pm * (1 - 0.6 * back[..., None])
            th = np.float32([[1, 0, -dirv[0] * 5 * min(1, fly * 3)], [0, 1, 6 * min(1, fly * 3)]])
            As = cv2.warpAffine(Am, th, (w, h))
            out = out * (1 - As[..., None] * 0.9) + As[..., None] * 0.02
            out = out * (1 - Am[..., None]) + Pm * (1.0 - 0.35 * min(1.0, fly))
            out = out * (1 - 0.85 * ink[..., None]) + (facing * (Am > 0.3))[..., None] * WHITE * 0.6 * fl
        fr = cv2.resize(out, (W, H))
        fr = rockfall(fr, t, self.t0 + 0.05, 261, 6, (300, 1600), 540, size=(80, 220), grav=-200, vy=(-300, 300), vx=(-900, 900),
                      spin=120, life=1.2, blur=2.0)
        fr = C1.dust(fr, t, 262, n=200, amt=0.6, drift=(0, 160), region=(0, BAR, W, H - BAR), color=(0.9, 0.9, 0.9))
        return ink_rain(fr, self.t0 + (t - self.t0) * 0.4, 263, n=200, ang=6, amt=0.6)


class C27(Shot):
    """146.57–147.50「看个天」。ELS 缺口：劈开的墙两半是黑剪影（左右缓缓分开，以镜头中点为零），缺口里天被闪电照得惨白，
    远处一道血红地平线；缺口积水里站着一个小小的人（背影剪影）。146.50 / 147.28 两道闪电。"""
    PK = 0.7
    def draw(self, t):
        u = self.u(t); p = self.par(t)
        tt = V(147.28)
        fs = 0.50 * bolt_env(t, tt) + 0.25 * pulse(t, V(146.5), 0.1)
        z = 1.0 + 0.06 * eio(u)
        base = pv('CB_gap_els', 0.47, 0.50, z, ft=self.ft(t))
        xx = np.arange(W, dtype=np.float32)[None, :]
        gx = plate_x('CB_gap_els', 0.47, 0.50, z, 0.48)
        mL = np.clip((gx - 140 - xx) / 60, 0, 1)[..., None]; mR = np.clip((xx - gx - 140) / 60, 0, 1)[..., None]
        Lh = pv('CB_gap_els', 0.47, 0.50, z, dx=-40 * p, ft=self.ft(t)); Rh = pv('CB_gap_els', 0.47, 0.50, z, dx=40 * p, ft=self.ft(t))
        fr = Lh * mL + Rh * mR + base * np.clip(1 - mL - mR, 0, 1)
        sky = np.clip(1 - mL - mR, 0, 1) * np.clip((560 - np.arange(H, dtype=np.float32)[:, None, None]) / 400, 0, 1)
        fr = fr + sky * fs * 0.6
        fr = K.bolt(fr, t, V(146.5), 271, (1010, BAR + 10), (930, 640), inten=0.8)
        fr = K.bolt(fr, t, tt, 272, (900, BAR + 10), (990, 700), inten=1.0)
        py = plate_y('CB_gap_els', 0.47, 0.50, z, 0.855); px = plate_x('CB_gap_els', 0.47, 0.50, z, 0.47)
        fr, _ = put(fr, t, 'CB_lookup', foot=(px, py), h=150 * z, wind=4, look='sil')
        return ink_rain(fr, t, 273, n=260, ang=8, amt=0.75)


class C28(Shot):
    """147.50–148.27「亮」。伪天亮：左 1/3 墙面上一道闪电裂纹透出白光（光只沿裂纹发出），147.74 光最满 + 整屏 3 帧闪白再收回；
    右侧鬼屠面部特写，裂纹的光横过他的眼睛（生图 CB_face）。"""
    PK = 0.8
    HX = 620
    def __init__(self):
        cr = ink_cracks(281, (self.HX, 470), 9, 1100)
        up = cv2.resize(cr, (W, H), interpolation=cv2.INTER_CUBIC)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        fall = np.exp(-(((xx - self.HX) / 950) ** 2 + ((yy - 470) / 620) ** 2))
        self.core = (np.clip((up - 0.45) / 0.45, 0, 1) ** 1.5 * (0.45 + 0.55 * fall)).astype(np.float32)
        self.h1 = (1 - np.exp(-cv2.resize(cv2.GaussianBlur(cr, (0, 0), 3), (W, H)) * fall * 3.0 / 0.55)).astype(np.float32) * 0.55

    def draw(self, t):
        u = self.u(t); tl = V(147.74)
        lt = sm(self.t0, tl, t) * (1 - 0.75 * sm(tl + 0.25, self.t1, t))
        k_ = int(math.floor((t - tl) * 30 + 1e-6)); fl = (1.0, 0.55, 0.25)[k_] if 0 <= k_ < 3 else 0.0
        fr = pv('CB_wall_bright', 0.30, 0.5, 1.5, flip=True) * 0.42
        lum = fr.mean(-1, keepdims=True); fr = lum + (fr - lum) * 0.3
        glow = (self.core * (0.8 + 2.6 * lt) + self.h1 * (0.15 + 0.55 * lt))[..., None] * WHITE
        glow = 1.4 * (1 - np.exp(-glow / 1.4))
        fr = fr + glow
        acc = np.zeros_like(glow)
        for i in range(10):
            z = 1 + 0.6 * lt * (i + 1) / 10
            acc += cv2.warpAffine(glow, np.float32([[z, 0, self.HX * (1 - z)], [0, z, 470 * (1 - z)]]), (W, H)) * (1 - i / 10)
        fr = fr + acc / 10 * 0.22 * lt
        fr = C1.dust(fr, t, 282, n=140, amt=0.5 * lt, drift=(10, -20), region=(300, BAR, 1620, H - BAR), color=(0.95, 0.95, 0.95))
        sp = L('CB_face')
        fr, _ = put(fr, t, 'CB_face', anc=(0.55, 0.42), dst=(1330 - 20 * u, 520), s=1180 / sp.h * (1 + 0.03 * u), wind=5, breathe=0.004,
                    expo=0.75 + 0.45 * lt + 0.5 * fl)
        fr = ink_rain(fr, t, 283, n=220, ang=6, amt=0.65)
        fr = fr * (1 + 0.35 * fl) + 0.30 * fl
        return fr


class C29(Shot):
    """148.27–149.07「（亮）」。中近景迎面：他从缺口里走向镜头（腰以上占满画面，镜头后退跟），身后缺口白光（背景板虚焦）；
    两侧断墙是失焦的黑前景（墨线勾边），生图碎石擦肩坠落；148.54 余电把轮廓勾亮。"""
    PK = 0.5
    def draw(self, t):
        u = self.u(t); p = self.par(t); tb = V(148.54)
        fl = bolt_env(t, tb)
        bg = pv('CB_gap_els', 0.47, 0.42, 1.55, dx=-20 * p, ft=self.ft(t))
        fr = bright(haze(bg, 0.30, 0.95), 0.6 * fl)                         # 缺口白光：向纸白渐隐（不做景深虚化）
        sp = L('CB_walkfront')
        fr, _ = put(fr, t, 'CB_walkfront', anc=(0.48, 0.0), dst=(960, BAR - 50 + 10 * math.sin(t * 7.5)), s=1000 / sp.h * (1 + 0.10 * eio(u)),
                    wind=7, breathe=0, expo=1.0 + 0.4 * fl)
        r = np.random.default_rng(29)
        m = np.zeros((H // 4, W // 4), np.float32)
        ys = np.linspace(0, H // 4, 16)
        lx = 55 + np.cumsum(r.normal(0, 4, 16)) - 50 * p; rx = W // 4 - 55 + np.cumsum(r.normal(0, 4, 16)) + 50 * p
        cv2.fillPoly(m, [np.array([[0, 0]] + [[int(a_), int(b_)] for a_, b_ in zip(lx, ys)] + [[0, H // 4]], np.int32)], 1.0)
        cv2.fillPoly(m, [np.array([[W // 4, 0]] + [[int(a_), int(b_)] for a_, b_ in zip(rx, ys)] + [[W // 4, H // 4]], np.int32)], 1.0)
        m = cv2.resize(cv2.GaussianBlur(m, (0, 0), 0.8), (W, H))
        edge = np.clip(m - cv2.erode(m, np.ones((7, 7), np.uint8)), 0, 1)                         # 断墙内缘一道白墨线（硬边）
        fr = fr * (1 - m[..., None]) + m[..., None] * 0.02 + edge[..., None] * WHITE * (0.4 + 0.8 * fl)
        R = rocks()
        for i in range(6):
            x = r.choice([r.uniform(200, 560), r.uniform(1360, 1720)]); ph = r.random()
            y = BAR - 80 + ((t * r.uniform(700, 1000) + ph * 900) % 960)
            fr = rgba_put(fr, R[i % len(R)], x, y, r.uniform(40, 90), rot=(t * r.uniform(-300, 300)) % 360, blur=1.2)
        fr = C1.dust(fr, t, 291, n=120, amt=0.5, drift=(0, 120), color=(0.9, 0.9, 0.9))
        return ink_rain(fr, t, 292, n=220, ang=6, amt=0.65)


class C30(Shot):
    """149.07–150.23「血未冷」。CU 腰带：暗红腰带在暴风里狂舞（生图 CB_sash，风吹二级运动），手按刀柄；
    背后雷暴云；149.70 闪电照亮；风里卷过几缕血红细墨。"""
    PK = 1.0
    def draw(self, t):
        u = self.u(t); p = self.par(t); tf = V(149.70)
        fl = bolt_env(t, tf)
        fr = pv('CB_storm', 0.5, 0.5, 1.2, dx=-40 * p, ft=self.ft(t))
        fr = bright(fr * 0.75, 0.5 * fl)
        sp = L('CB_sash')
        fr, _ = put(fr, t, 'CB_sash', anc=(0.45, 0.45), dst=(900 - 60 * u, 520), s=W * 1.12 / sp.w, wind=22, breathe=0.006, expo=1.0 + 0.4 * fl)
        r = np.random.default_rng(301); Lr = np.zeros((H // 2, W // 2), np.float32)
        for i in range(10):
            y = r.uniform(250, 800); x = ((r.uniform(0, W) + 900 * t) % (W + 600)) - 300; ln = r.uniform(120, 320)
            cv2.line(Lr, (int(x / 2), int(y / 2)), (int((x - ln) / 2), int((y + ln * 0.08) / 2)), 1.0, 1, cv2.LINE_AA)
        Lr = cv2.resize(Lr, (W, H))[..., None] * 0.8
        fr = fr * (1 - Lr) + Lr * RED
        return ink_rain(fr, t, 302, n=240, ang=20, amt=0.65)


class C31(Shot):
    """150.23–151.63「骨未凉」。MS 巨掌：雷云里老皇帝枯瘦的巨手（生图 CB_hand，黑纱袖、暗红袖口）从画顶一掌压下，阴影罩住画面；
    他先站定仰望（CB_runstop），150.77 掌落：反白一帧 + 冲击波墨环 + 积水炸起，他被震飞后撤（CB_knock，横向拖影）。"""
    PK = 0.5
    def draw(self, t):
        u = self.u(t); p = self.par(t); ti = V(150.77)
        fr = pv('CB_ground_paper', 0.5, 0.45, 1.05, dx=-20 * p, flip=True, ft=self.ft(t))
        q = ein(sm(self.t0, ti, t), 2.5)
        fr = fr * (1 - 0.40 * q)                                                     # 掌影压下
        fr = bright(fr, 0.9 * pulse(t, ti, 0.15))
        hy = lerp(-640, 40, q) if t < ti else 40 + 20 * math.sin((t - ti) * 30) * math.exp(-(t - ti) * 6)
        sp = L('CB_hand2')
        fr, _ = put(fr, t, 'CB_hand2', anc=(0.38, 0.0), dst=(1260, hy - 40), s=1500 / sp.w, wind=8, breathe=0.006,
                    mblur=(0, 30 * (1 - q)) if t < ti else (0, 0))
        k = max(0.0, t - ti)
        if t < ti:
            fr, _ = put(fr, t, 'CB_runstop', foot=(1040, 950), h=560, wind=8)
        else:
            x = 1000 - 480 * eout(k / 0.5)
            fr, _ = put(fr, t, 'CB_knock', foot=(x, 955), h=560, wind=10, mblur=(-60 * pulse(t, ti, 0.2), 0), expo=1.0 + 0.6 * pulse(t, ti, 0.15))
            for j, (y_, w_) in enumerate(((935, 70), (965, 50))):             # 掌落积水：两笔干墨水浪自落点向两侧横扫（不用矢量冲击环）
                for sd in (-1, 1):
                    fr = brush(fr, (1260, y_), (1260 + sd * 1100, y_ - 30 - 20 * j), (k - 0.03 * j) / 0.22, width=w_, bend=0.05 * sd, seed=315 + j * 2 + (sd > 0),
                               life=0.4, hot=0.0, splat=1.4, amt=0.9, col=(0.03, 0.03, 0.03))
            fr = C1.sparks(fr, t, 311, (1180, 930), n=160, life=0.7, speed=(300, 1100), dirc=(0, -1), spread=0.8, grav=1800, t0=ti, burst=True,
                          area=(320, 10), color=(0.95, 0.95, 0.95), amt=1.0)
            fr = C1.dust(fr, t, 312, n=180, amt=0.9 * min(1, k * 5) * (1 - sm(0.4, 1.2, k)), drift=(-300, -60), region=(300, 700, W, 960),
                        color=(0.9, 0.9, 0.9))
            if int(round(k * 30)) == 0: fr = invert(fr)
        return ink_rain(fr, t, 313, n=240, ang=10, amt=0.7)


class C32(Shot):
    """151.63–152.53「是非」——用户：「就一个断一截的剑头，啥意思啊，换个分镜吧」。重做分镜：
    MS 低机位全身，人在画面中偏左、整把刀始终完整入画（两张关键姿势都画到刀尖）：
    ① 151.63–152.03 蓄势：双手举刀过右肩（CB_c32a），镜头缓推、雷云翻滚；
    ② 152.05「是」虚晃：一道细斩痕自右上划下（干笔飞白）+ 轻震；
    ③ 152.40「非」十字双斩：前一帧反白冲击，硬换斩毕姿势（CB_c32b2：以 CB_c32a 为底图图生图衍生，刀横扫至左），两道交叉的干笔飞白斩痕（血红笔身 + 白热芯 + 溅墨）贯穿全画；
       火星白 + 血红、震屏；斩痕余势甩进 C33（whip 方向 = 挥刀方向，向左）。"""
    PK = 0.5
    def draw(self, t):
        u = self.u(t); p = self.par(t)
        t0_, tx = V(152.05), V(152.40)
        fl = 0.6 * bolt_env(t, tx)
        fr = pv('CB_sky_red', 0.40, 0.42, 1.15 + 0.04 * u, dx=-30 * p, redk=0.55, ft=self.ft(t))
        fr = bright(fr * 0.8, fl)
        fr = K.bolt(fr, t, tx - 0.02, 327, (1500, BAR), (1700, 620), inten=0.7)
        if t < tx - 1 / 30 - 1e-6:
            fr, _ = put(fr, t, 'CB_c32a', foot=(860 + 10 * u, 955), h=760 * (1 + 0.02 * u), wind=9, breathe=0.005, rot=-1.5 * pulse(t, t0_, 0.1))
            fr = brush(fr, (1880, 200), (1180, 760), (t - t0_) / 0.12, width=55, bend=0.10, seed=321, life=1.2, hot=1.0, splat=0.5, amt=0.85)
            sk = pulse(t, t0_, 0.08) * (t >= t0_)
            dx, dy = np.random.default_rng(int(t * 30)).uniform(-1, 1, 2) * 8 * sk
            return ink_rain(K.camxf(fr, 1.0 + 0.012 * sk, dx, dy) if sk > 0.05 else fr, t, 328, n=240, ang=12, amt=0.7)   # 震屏带微推，画边不露反射
        if t < tx:                                                                  # 反白冲击帧（命中前一帧）
            fr, A = put(fr, t, 'CB_c32a', foot=(870, 955), h=780, wind=9)
            fr = invert(fr)
            fr = fr * (1 - A[..., None]) + 0.02 * A[..., None]
            fr = brush(fr, (360, 220), (1560, 880), 0.55, width=120, bend=0.06, seed=322, hot=0.0, splat=0.0)
            return fr
        k = t - tx
        e = eout(clamp(k / 0.10), 2)
        fr, _ = put(fr, t, 'CB_c32b2', foot=(900 - 40 * e, 955), h=740, wind=10, breathe=0.004, mblur=(-40 * (1 - e), 0))
        fr = brush(fr, (300, 200), (1640, 900), k / 0.10, width=120, bend=0.08, seed=322, life=3.0, hot=1.0)
        fr = brush(fr, (1640, 190), (280, 910), (k - 0.03) / 0.10, width=120, bend=-0.08, seed=323, life=3.0, hot=1.0)
        fr = spark2(fr, t, 324, (960, 545), n=120, life=0.6, speed=(300, 1200), dirc=(-1, -0.3), spread=1.6, grav=900, t0=tx, area=(40, 40))
        if int(round(k * 30)) == 0: fr = flash_white(fr, 0.6)
        sk = pulse(t, tx, 0.12)
        dx, dy = np.random.default_rng(int(t * 30) + 7).uniform(-1, 1, 2) * 14 * sk
        fr = K.camxf(fr, 1.0 + 0.03 * sk, dx, dy)
        return ink_rain(fr, t, 328, n=240, ang=12, amt=0.7)


class C33(Shot):
    """152.53–153.00「对 / 错」。CU 刀身横扫过画面（生图 CB_blade，镜内旋转 = 刀在挥）：152.70、152.90 各一挥，
    每一挥留一道干笔飞白斩痕；背后 C32 的十字斩痕余影还没散（淡）。"""
    PK = 0.4
    def draw(self, t):
        u = self.u(t); td, tc = V(152.70), V(152.90)
        fl = 0.5 * bolt_env(t, td) + 0.5 * bolt_env(t, tc)
        fr = pv('CB_sky_paper', 0.55, 0.5, 1.35, redk=0.35, ft=self.ft(t)) * 0.80
        fr = bright(fr, fl)
        fr = brush(fr, (300, 200), (1640, 900), 2.0, width=120, bend=0.08, seed=322, life=3.0, hot=0.0, amt=0.25 * (1 - 0.5 * u))
        fr = brush(fr, (1640, 190), (280, 910), 2.0, width=120, bend=-0.08, seed=323, life=3.0, hot=0.0, amt=0.25 * (1 - 0.5 * u))
        fr = brush(fr, (200, 760), (1720, 300), (t - td) / 0.10, width=90, bend=-0.10, seed=331, life=1.5)
        fr = brush(fr, (1720, 760), (200, 320), (t - tc) / 0.09, width=90, bend=0.10, seed=332, life=1.5)
        wind = lambda x: lerp(-14, 12, ein(clamp((x - self.t0) / 0.2)))             # 起势 → 第一挥从起势停下的角度接着挥（不跳帧）
        a_td = wind(td)
        ang = wind(t) if t < td else lerp(a_td, -16, eout(clamp((t - td) / 0.2)))
        if t >= tc: ang = lerp(lerp(a_td, -16, eout(clamp((tc - td) / 0.2))), 6, eout(clamp((t - tc) / 0.12)))
        sp = L('CB_blade')
        fr, _ = put(fr, t, 'CB_blade', anc=(0.5, 0.505), dst=(960, 560), s=W * 1.25 / sp.w, rot=ang, wind=0, breathe=0, expo=1.0 + 0.5 * fl,
                    mblur=(0, 30 * (pulse(t, td, 0.06) * (t >= td) + pulse(t, tc, 0.06) * (t >= tc))))
        return ink_rain(fr, t, 333, n=220, ang=12, amt=0.6)


class C34(Shot):
    """153.00–153.90「（对错）我」。MS 斜劈：153.12 他一刀斜劈到底（CB_diag2：以 CB_c32a 为底图图生图衍生，跪地、刀斜指右下），
    一道巨大的干笔飞白斜斩痕从右上贯穿到左下；反白冲击帧 + 溅血溅墨 + 积水炸起。"""
    PK = 0.8
    def draw(self, t):
        u = self.u(t); p = self.par(t); ts = V(153.12)
        fl = 0.9 * pulse(t, ts, 0.14)
        fr = pv('CB_storm_ground', 0.5, 0.40, 1.05, dx=-25 * p, redk=0.35, ft=self.ft(t))
        fr = bright(fr * 0.85, fl)
        k = t - ts
        e = eout(clamp((t - self.t0) / 0.12), 2)
        if k < -1 / 30 - 1e-6:                                                    # 关键姿势 1：举刀蓄势（切入后 3 帧），「我」拍硬切到斩毕
            fr, _ = put(fr, t, 'CB_c32a', foot=(820, 955), h=700, wind=9, breathe=0.004, mblur=(0, -20 * (1 - e)))
            return ink_rain(fr, t, 344, n=240, ang=-10, amt=0.7)
        if k < -1e-6:
            fr = brush(fr, (1450, 180), (150, 960), 0.55, width=150, seed=341, hot=0.0, splat=0.0)
            fr, A = put(fr, t, 'CB_diag2', foot=(840, 955 - 20 * (1 - e)), h=600, wind=9, breathe=0.004)
            fr = invert(fr); fr = fr * (1 - A[..., None]) + 0.02 * A[..., None]
            return fr
        fr = brush(fr, (1450, 180), (150, 960), k / 0.14, width=150, bend=0.05, seed=341, life=4.0, hot=1.0)   # 斩痕在人身后（不压脸）
        fr, A = put(fr, t, 'CB_diag2', foot=(840, 955 - 20 * (1 - e)), h=600, wind=9, breathe=0.004, mblur=(0, -30 * (1 - e)))
        if k >= 0:
            fr = C1.sparks(fr, t, 342, (900, 930), n=140, life=0.7, speed=(300, 1000), dirc=(0, -1), spread=0.9, grav=1800, t0=ts, burst=True,
                          area=(300, 10), color=(0.95, 0.95, 0.95), amt=1.0)
            fr = C1.sparks(fr, t, 343, (960, 560), n=60, life=0.6, speed=(300, 900), dirc=(-0.8, 0.6), spread=1.0, grav=900, t0=ts, burst=True,
                          area=(200, 100), color=(0.85, 0.04, 0.03), amt=1.2)
        return ink_rain(fr, t, 344, n=240, ang=-10, amt=0.7)


class C35(Shot):
    """153.90–154.63「（我）自己」。LS 硬扛：一方巨大的石印（生图 CB_seal，印底血红、无字）从雷云里压下，他举刀过顶硬扛
    （CB_bracefull），地面墨线龟裂、泥尘扬起；印与人随下沉一起压低。"""
    PK = 0.6
    def draw(self, t):
        u = self.u(t); p = self.par(t)
        sink = 18 * eout(u)
        fr = pv('CB_ground_paper', 0.42, 0.42, 1.05, dx=-20 * p, flip=True, ft=self.ft(t))
        fr = fr * (1 - 0.30 * eio(u))
        sp = L('CB_seal')
        fr, _ = put(fr, t, 'CB_seal', anc=(0.51, 0.97), dst=(960, 300 + sink + 30 * (1 - eout(u, 2))), s=1300 / (0.76 * sp.w), wind=0, breathe=0,
                    expo=0.95)
        cr = np.zeros((H // 4, W // 4), np.float32)
        for i in range(6):
            pth = crack_path((960, 955), (960 + (i - 2.5) * 330, 1040), 350 + i, n=24, jag=0.06)
            cr = np.maximum(cr, draw_crack(cr.shape, pth / 4, 2, branches=3, seed=i, prog=sm(self.t0, self.t0 + 0.6, t)))
        fr = fr * (1 - 0.85 * cv2.resize(cr, (W, H))[..., None])
        fr, _ = put(fr, t, 'CB_bracefull', foot=(960, 955 + sink), h=700, wind=6, breathe=0.004)
        fr = C1.dust(fr, t, 351, n=160, amt=0.7, drift=(0, -40), region=(300, 820, 1620, 960), color=(0.9, 0.9, 0.9))
        return ink_rain(fr, t, 352, n=220, ang=6, amt=0.65)


class C35b(Shot):
    """154.63–155.30「扛」。MCU 仰拍（同轴跳进）：刀横在头顶（CB_bracecu，咬牙），血红印底从画顶压到刀背上；
    154.70 接触：火星沿刃迸开（白 + 血红），画面重震、整体下沉 34px，再一点点顶回去（被压下 → 顶住）。"""
    PK = 0.8
    def draw(self, t):
        u = self.u(t); tk = V(154.70); k = max(0.0, t - tk)
        hit = pulse(t, tk, 0.10)
        sink = (34 * eout(k / 0.08) - 16 * sm(0.15, 0.6, k)) if t >= tk else 6 * u
        fr = pv('CB_storm', 0.5, 0.35, 1.3, ft=self.ft(t)) * 0.85
        fr = bright(fr, 0.9 * hit)
        sp = L('CB_seal')
        sy = lerp(-30, 40, ein(sm(self.t0, tk, t), 2)) + (sink * 0.9 if t >= tk else 0)   # 切点与接触只差 1 帧：入镜时印已贴近刀背，只压最后 70px
        fr, _ = put(fr, t, 'CB_seal', anc=(0.51, 0.97), dst=(960, sy), s=2600 / (0.76 * sp.w), wind=0, breathe=0, mblur=(0, 20) if t < tk else (0, 0))
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        fr = fr * (1 - 0.35 * np.clip(1.2 - yy * 1.8, 0, 1) * sm(self.t0, tk, t))
        sb = L('CB_bracecu')
        fr, _ = put(fr, t, 'CB_bracecu', anc=(0.5, 0.0), dst=(960, 20 + sink), s=W * 1.06 / sb.w, wind=3, breathe=0.010, expo=1.0 + 0.5 * hit)
        if t >= tk - 0.02:
            for sd, x0, y0 in ((-1, 640, 110), (1, 1280, 110)):
                fr = spark2(fr, t, 353 + sd, (x0, y0 + sink), n=110, life=0.6, speed=(300, 1300), dirc=(sd, 0.15), spread=0.6, grav=1400, t0=tk, amt=1.3)
        fr = C1.dust(fr, t, 354, n=160, amt=0.8 * min(1, k * 8) * (1 - sm(0.3, 0.8, k)), drift=(0, 260), region=(200, BAR, 1720, 600), size=(1, 4),
                    color=(0.9, 0.9, 0.9))
        return ink_rain(fr, t, 355, n=180, ang=4, amt=0.55)


class C36(Shot):
    """155.30–156.20「天」。ELS 跪伏千军（生图 CB_army）：C18 冲锋的那支军此刻全部跪在积水里低头，旗杆插地，中间一条空水道直通天边——
    没有人站着。镜头沿水道低空推进；155.96「天」一道横贯天际的白色闪电把盔顶、旗、水面一齐照亮。"""
    PK = 1.0
    def draw(self, t):
        u = self.u(t); tt = V(155.96)
        fl = bolt_env(t, tt) * 1.2 + 0.4 * bolt_env(t, V(155.40))
        fr = pv('CB_army', 0.5, 0.52 - 0.02 * u, lerp(1.0, 1.09, eio(u))) * 1.25
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        fr = fr * (0.85 + 0.5 * fl * (0.6 + 0.6 * np.clip(1 - yy * 1.6, 0, 1)))
        fr = K.bolt(fr, t, tt, 361, (60, 230), (1860, 270), inten=1.3, branches=12, width=4)
        fr = K.bolt(fr, t, V(155.40), 362, (1400, 140), (1500, 400), inten=0.7)
        fr = stonefog(fr, t, 363, 0.3, 470, 700)
        return ink_rain(fr, t, 364, n=260, ang=8, amt=0.7)


class C37(Shot):
    """156.20–157.10「（天）不判」——用户：「这里牌匾是啥文字来着，保留吧」。牌匾字画进生图（CB_plaque：黑漆盘龙匾，
    匾心「天不判」毛笔阴刻、刻槽灌血红；逐字放大核对字形无误）。代码只做「何时灌血」：
    入镜时「天」已灌满（155.96 已唱），「不」刻槽在 156.24 一拍里由上而下灌血，「判」在 156.70 闪电那拍灌血 + 刻槽白闪；
    156.94 第二道雷正劈匾心：匾沿一道锯齿裂缝裂开（白热→血红的裂缝），两半只错开一点、仍读得出整块匾；匾挂在铁链上摇晃。"""
    PK = 0.5
    def __init__(self):
        im = cv2.imread(A_DIR + 'CB_plaque_cut.png', cv2.IMREAD_UNCHANGED)
        im = cv2.resize(im, (1400, 788), interpolation=cv2.INTER_AREA).astype(np.float32)
        F = im[..., [2, 1, 0]] / 255; A = im[..., 3] / 255
        r, g, b = F[..., 0], F[..., 1], F[..., 2]
        ratio = (r - np.maximum(g, b)) / (r + 1e-3)
        red = np.clip((ratio - 0.35) / 0.25, 0, 1) * np.clip((r - 0.05) / 0.1, 0, 1)
        red = cv2.GaussianBlur(cv2.dilate(red, np.ones((3, 3), np.uint8)), (0, 0), 0.8)
        xs = np.arange(1400, dtype=np.float32)[None, :] / 1400
        board = np.zeros_like(red); board[int(0.20 * 788):int(0.78 * 788), int(0.10 * 1400):int(0.90 * 1400)] = 1
        red = red * board
        self.cm = [red * (xs < 0.375), red * ((xs >= 0.375) & (xs < 0.61)), red * (xs >= 0.61)]
        self.ext = []
        for m in self.cm:
            ys = np.where(m.max(1) > 0.3)[0]; self.ext.append((ys.min(), ys.max()) if len(ys) else (0, 788))
        lum = F.mean(-1, keepdims=True)
        self.F0 = F; self.A = A
        self.Fg = np.clip(lum * 0.18, 0, 1) * np.ones(3, np.float32)            # 未灌血：暗槽
        self.wav = (np.sin(np.arange(1400) / 1400 * 50) * 6).astype(np.float32)[None, :]
        r_ = np.random.default_rng(37)
        xs_ = 960 + np.cumsum(r_.normal(0, 14, 40)); xs_ -= xs_.mean() - 960
        self.crack = np.stack([xs_, np.linspace(BAR - 40, H - BAR + 40, 40)], 1).astype(np.int32)

    def fill(self, t):
        tb, tp = V(156.24), V(156.70)
        f = [1.0, clamp((t - (tb - 0.03)) / 0.22), clamp((t - (tp - 0.03)) / 0.20)]
        yy = np.arange(788, dtype=np.float32)[:, None]
        g = np.zeros((788, 1400), np.float32); wh = np.zeros_like(g)
        for i, (m, (y0, y1)) in enumerate(zip(self.cm, self.ext)):
            if f[i] >= 1: continue
            lev = y0 - 10 + (y1 - y0 + 20) * eout(f[i], 2)
            un = np.clip((yy + self.wav - lev) / 4 + 0.5, 0, 1)
            g = np.maximum(g, m * un)
            if f[i] > 0: wh = np.maximum(wh, m * np.exp(-((yy + self.wav - lev) / 6) ** 2))
        F = self.F0 * (1 - g[..., None]) + self.Fg * g[..., None] + wh[..., None] * WHITE * 0.8
        flash = [0, pulse(t, tb, 0.10) * (t >= tb), pulse(t, tp, 0.12) * (t >= tp)]
        for i in (1, 2):
            if flash[i] > 0.02: F = F + (self.cm[i] * flash[i])[..., None] * WHITE * 0.7
        return F

    def draw(self, t):
        u = self.u(t); tp = V(156.70); ts = tp + 0.24
        fl = bolt_env(t, tp) * 1.1 + bolt_env(t, ts) * 1.3
        fr = pv('CB_sky_paper', 0.45, 0.40, 1.3, flip=True, ft=self.ft(t)) * 0.85
        fr = bright(fr, 0.5 * fl)
        sw = 2.2 * math.sin((t - self.t0) * 3.2)
        Fp = self.fill(t) * (1 + 0.25 * fl)
        sc = 1300 / 1400
        M = cv2.getRotationMatrix2D((700, 40), sw, sc); M[0, 2] += 960 - 700; M[1, 2] += 210 - 40
        Pw = cv2.warpAffine(Fp * self.A[..., None], M, (W, H)); Aw = cv2.warpAffine(self.A, M, (W, H))
        for x in (0.285, 0.715):                                                # 铁链（墨线）
            rx, ry = M @ np.array([x * 1400, 0.03 * 788, 1.0])
            cv2.line(fr, (int(rx + 30), BAR - 10), (int(rx), int(ry)), (0.03, 0.03, 0.03), 5, cv2.LINE_AA)
            cv2.line(fr, (int(rx + 30), BAR - 10), (int(rx), int(ry)), (0.6, 0.6, 0.6), 1, cv2.LINE_AA)
        if t < ts:
            fr = fr * (1 - Aw[..., None]) + Pw
        else:
            q = t - ts
            msk = np.zeros((H, W), np.float32)
            cv2.fillPoly(msk, [np.concatenate([[[0, 0]], self.crack, [[0, H]]]).astype(np.int32)], 1.0, cv2.LINE_AA)
            for sg, m_ in ((-1, msk), (1, 1 - msk)):
                ang = sg * 1.6 * eout(clamp(q / 0.12))
                Mq = cv2.getRotationMatrix2D((960 + sg * 300, 560), ang, 1.0); Mq[0, 2] += sg * 12 * eout(clamp(q / 0.12)); Mq[1, 2] += 6 * eout(clamp(q / 0.12))
                Am = cv2.warpAffine(Aw * m_, Mq, (W, H)); Pm = cv2.warpAffine(Pw * m_[..., None], Mq, (W, H))
                fr = fr * (1 - Am[..., None]) + Pm
            edge = np.zeros((H // 2, W // 2), np.float32); cv2.polylines(edge, [self.crack // 2], False, 1.0, 2, cv2.LINE_AA)
            edge = cv2.resize(cv2.GaussianBlur(edge, (0, 0), 2), (W, H))[..., None] * cv2.dilate(Aw, np.ones((9, 9), np.uint8))[..., None]
            hot = math.exp(-q / 0.08)
            fr = fr + edge * (WHITE * 2.0 * hot + RED * 1.6 * (1 - hot))
            fr = C1.sparks(fr, t, 371, (960, 560), n=140, life=0.7, speed=(300, 1200), dirc=(0, -0.3), spread=3.0, grav=1300, t0=ts, burst=True,
                          color=(1.0, 0.97, 0.94), area=(30, 300))
        fr = K.bolt(fr, t, ts, 372, (1000, 40), (960, 560), inten=1.2, width=4)
        fr = ink_rain(fr, t, 373, n=200, ang=10, amt=0.6)
        E = np.zeros((H // 2, W // 2), np.float32)                              # 前景：左上近景飞檐剪影（硬边墨剪影、白墨线勾边）
        cv2.fillPoly(E, [np.array([[0, 0], [600, 0], [560, 95], [300, 140], [120, 230], [0, 300]], np.int32)], 1.0, cv2.LINE_AA)
        cv2.fillPoly(E, [np.array([[540, 80], [640, 40], [600, 110]], np.int32)], 1.0, cv2.LINE_AA)
        E = cv2.resize(cv2.GaussianBlur(E, (0, 0), 0.8), (W, H))
        Er = np.clip(E - cv2.erode(E, np.ones((5, 5), np.uint8)), 0, 1)       # 飞檐剪影：硬边 + 一道白墨线（不做焦外）
        fr = fr * (1 - 0.95 * E[..., None]) + E[..., None] * 0.01 + Er[..., None] * WHITE * (0.3 + 0.7 * fl)
        return fr


class C38(Shot):
    """157.10–158.47「我来」。CU 握刀手（生图 CB_grip：湿透的袖口和护腕从左入画、年轻的手握紧黑柄，刀身横出画右）：
    缓推 + 手腕微旋（握紧）；157.34 远雷照亮；158.18「我」一道白光沿刀身从护手扫到出画；指节滴水。"""
    PK = 1.0
    def draw(self, t):
        u = self.u(t); tf, tw = V(157.34), V(158.18)
        fl = bolt_env(t, tf) * 0.8 + 0.5 * bolt_env(t, tw)
        fr = pv('CB_storm', 0.3, 0.45, 1.4, flip=True, ft=self.ft(t)) * 0.75
        fr = bright(fr, 0.6 * fl)
        grip = eio(clamp((t - self.t0) / 0.6)) + 0.4 * pulse(t, tw, 0.2)
        sp = L('CB_grip'); s = W * 1.08 / sp.w * (1.0 + 0.05 * u); rot = 1.5 - 2.5 * grip; anc = (0.5, 0.5); dst = (930, 560)
        fr, _ = put(fr, t, 'CB_grip', anc=anc, dst=dst, s=s, rot=rot, wind=0, breathe=0, expo=1.0 + 0.4 * fl)
        q = (t - tw) / 0.30
        if 0 < q < 1:
            p0 = spt('CB_grip', s, anc, dst, rot, (0.70, 0.62)); p1 = spt('CB_grip', s, anc, dst, rot, (1.0, 0.70))
            c = p0 + (p1 - p0) * eio(q)
            fr = star(fr, c, 120 * math.sin(math.pi * q) + 20, 1.0, ang=8)            # 刀身反光：硬边墨线星芒沿刃滑过
        hp = spt('CB_grip', s, anc, dst, rot, (0.82, 0.62))
        fr = C1.sparks(fr, t, 381, (hp[0], hp[1] + 40), n=26, life=0.9, speed=(40, 160), dirc=(0, 1), spread=0.3, grav=1400, amt=0.8,
                      color=(0.95, 0.95, 0.95), area=(140, 20))
        return ink_rain(fr, t, 382, n=200, ang=4, amt=0.6)


class C39(Shot):
    """158.47–159.40「量」。MCU 蓄力（生图 CB_windup：双手把刀拉到右肩后、整把刀入画）：镜头推近 + 慢放雨；
    左半幅远处雷暴里那架青铜天平（C40 要斩的同一架，CB_balance）焦外剪影做铺垫；158.56 一道白光沿刀身从护手扫到刀尖；159.01 落雷从天平背后劈下。"""
    PK = 0.6
    _SK = {}
    def sink(self, cx, cy, s, sp):
        """底座渐隐遮罩：画布底边以上 170px 内按起伏的雾线（墨晕形状）淡出"""
        key = (round(cx), round(cy), round(s, 4))
        if key not in self._SK:
            yb = cy + (sp.h - 1) * 0.5 * s                                          # 画布底边在屏幕上的 y
            xs = np.arange(W, dtype=np.float32)
            r = np.random.default_rng(39)
            wav = np.interp(xs, np.linspace(0, W, 30), r.uniform(-45, 45, 30)).astype(np.float32)
            top = yb - 170 + wav
            yy = np.arange(H, dtype=np.float32)[:, None]
            g = np.clip((yb - 6 - yy) / np.clip(yb - 6 - top[None, :], 1, None), 0, 1)
            if len(self._SK) > 64: self._SK.clear()
            self._SK[key] = (g * g * (3 - 2 * g)).astype(np.float32)
        return self._SK[key]

    def draw(self, t):
        u = self.u(t); p = self.par(t); tq, tl = V(158.56), V(159.01)
        fl = bolt_env(t, tl)
        fr = pv('CB_sky_red', 0.62, 0.40, 1.25, dx=-25 * p, flip=True, redk=0.7, ft=self.ft(t)) * 0.85
        fr = bright(fr, 0.6 * fl + 0.4 * pulse(t, tq, 0.15))
        lay = np.zeros_like(fr)
        sb = L('CB_balance')
        lay, Ab = put(lay, t, 'CB_balance', anc=(0.5, 0.5), dst=(470 - 15 * p, 400), s=640 / sb.w, rot=4 * math.sin(t * 1.6) + 3, wind=0, breathe=0)
        Ab = Ab * self.sink(470 - 15 * p, 400, 640 / sb.w, sb)                    # 天平底座沉进雷雨雾里（不规则渐隐，不露画布底边）
        far = haze(lay / np.clip(Ab[..., None], 1e-3, None), 0.45, 0.80 + 0.15 * fl)   # lay 是预乘色：先反算再向纸白渐隐（不做景深虚化）
        fr = fr * (1 - 0.85 * Ab[..., None]) + far * 0.85 * Ab[..., None]
        fr = K.bolt(fr, t, tl, 392, (300, 0), (520, 300), inten=0.8, branches=5)
        fr = stonefog(fr, t, 391, 0.5, 560, 960)
        sw = L('CB_windup'); s = 0.86 * (1.0 + 0.04 * eout(u)); anc = (0.55, 0.40); dst = (1180, 455)
        fr, _ = put(fr, t, 'CB_windup', anc=anc, dst=dst, s=s, wind=7, breathe=0.004, expo=1.0 + 0.3 * fl + 0.4 * pulse(t, tq, 0.12))
        gq = clamp((t - tq) / 0.30)
        if 0 < gq < 1:
            hilt = spt('CB_windup', s, anc, dst, 0, (0.78, 0.22)); tip = spt('CB_windup', s, anc, dst, 0, (0.03, 0.31))
            g = hilt + (tip - hilt) * eio(gq)
            fr = star(fr, g, 150 * math.sin(math.pi * gq) + 20, 1.0, ang=-12)
        return ink_rain(fr, self.t0 + (t - self.t0) * 0.5, 393, n=220, ang=8, amt=0.6)


class C40(Shot):
    """159.40–159.87「这一刀」。LS 背身横斩：前方雷暴里那架高过云的天平（CB_balance），159.66 一刀横断——
    横向干笔飞白斩痕贯穿全画，天平上半截（横梁 + 秤盘）沿斩线断开、翻落，断口血红；火星白 + 血红；背身斩毕姿势（CB_slashback）。"""
    PK = 0.5
    def draw(self, t):
        u = self.u(t); p = self.par(t); ts = V(159.66)
        fl = 1.0 * pulse(t, ts, 0.15) + 0.6 * bolt_env(t, V(159.50))
        fr = pv('CB_storm_ground', 0.5, 0.40, 1.05, dx=-20 * p, redk=0.35, ft=self.ft(t))
        fr = bright(fr * 0.85, fl)
        tb = 6 * math.sin(t * 1.6)
        lay = np.zeros_like(fr)
        sb = L('CB_balance')
        lay, Ab = put(lay, t, 'CB_balance', anc=(0.5, 0.2), dst=(960, 300), s=1500 / sb.w, rot=tb * 0.3, wind=0, breathe=0, expo=1.0 + 0.4 * fl)
        cut_y = 380
        br = ein(sm(ts, ts + 0.6, t), 1.4)
        yy = np.arange(H, dtype=np.float32)[:, None]
        mu = np.clip((cut_y - yy) / 2 + 0.5, 0, 1)[..., None]
        if br > 0:
            M = cv2.getRotationMatrix2D((960, cut_y), -14 * br, 1.0); M[0, 2] += 60 * br; M[1, 2] += 160 * br
            up = cv2.warpAffine(lay * mu, M, (W, H)); Au = cv2.warpAffine(Ab * mu[..., 0], M, (W, H))[..., None]
            lo_A = (Ab[..., None] * (1 - mu))
            fr = fr * (1 - lo_A) + lay * (1 - mu)
            fr = fr * (1 - Au) + up
            e = np.exp(-((yy - cut_y) / 3.0) ** 2)[..., None] * (Ab[..., None] > 0.3) * math.exp(-(t - ts) / 0.4)
            fr = fr + e * RED * 1.5
        else:
            fr = fr * (1 - Ab[..., None]) + lay
        fr = stonefog(fr, t, 40, 0.4, 600, 960)
        fr, A = put(fr, t, 'CB_slashback', foot=(760, 955), h=700, wind=10, breathe=0.004, expo=1.0 + 0.4 * fl)
        k = t - ts
        if -1 / 30 - 1e-6 <= k < -1e-6:
            fr = invert(fr)
            return fr
        fr = brush(fr, (-80, cut_y + 30), (2000, cut_y - 20), k / 0.10, width=110, bend=0.02, seed=401, life=3.0)
        fr = spark2(fr, t, 402, (960, cut_y), n=160, life=0.8, speed=(200, 900), dirc=(0, 1), spread=2.5, grav=600, t0=ts, area=(80, 10))
        return ink_rain(fr, t, 403, n=220, ang=10, amt=0.65)


class C40b(Shot):
    """159.87–160.30「就是我」。ECU：刀尖直指镜头、直视镜头（生图 CB_point）：159.95「是」一道白光沿刀刃扫过；
    160.08「我」眼中一亮 + 头发被余风甩起；断开的天平余烬（白 + 血红）从右上落下。"""
    PK = 0.6
    def draw(self, t):
        u = self.u(t); ts, tw = V(159.95), V(160.08)
        fl = 0.5 * bolt_env(t, ts) + 0.4 * pulse(t, tw, 0.12)
        fr = pv('CB_sky_paper', 0.30, 0.35, 1.35, ft=self.ft(t)) * 0.70
        fr = bright(fr, fl)
        fr = spark2(fr, t, 404, (1500, 140), n=90, life=1.4, speed=(40, 200), dirc=(0, 1), spread=1.0, grav=200, burst=False, area=(600, 60), amt=0.8)
        sp = L('CB_point'); s = W * 1.13 / sp.w * (1 + 0.05 * u); anc = (0.45, 0.45); dst = (900 - 30 * u, 520)
        fr, _ = put(fr, t, 'CB_point', anc=anc, dst=dst, s=s, wind=10 + 14 * pulse(t, tw, 0.2), breathe=0, expo=1.0 + 0.3 * fl)
        q = (t - ts) / 0.30
        if 0 < q < 1:
            p0 = spt('CB_point', s, anc, dst, 0, (0.40, 0.80)); p1 = spt('CB_point', s, anc, dst, 0, (0.98, 0.99))
            c = p0 + (p1 - p0) * eio(q)
            fr = star(fr, c, 140 * math.sin(math.pi * q) + 20, 1.0, ang=20)
        g = pulse(t, tw, 0.18) * (t >= tw - 0.02)
        if g > 0.02:
            for ex in ((0.42, 0.43), (0.55, 0.42)):
                e = spt('CB_point', s, anc, dst, 0, ex)
                fr = star(fr, e, 60 * g, min(1.0, 1.5 * g), ang=10)
        return ink_rain(fr, t, 405, n=160, ang=10, amt=0.5)


class C41(Shot):
    """160.30–161.30「的回答」。MS 低机位正面：他从横斩里旋进收势定格（生图 CB_final：刀平伸向画右、直视镜头），
    160.37「的」一道横向干笔飞白斩痕自左向右扫过全画，在雨里留一条血红墨痕；161.00「答」一记远雷把他照亮、雨定格；
    段尾最后 4 帧故障切黑交给 D 桥段（沿用本段 Sec.frame）。"""
    PK = 0.5
    def draw(self, t):
        u = self.u(t); p = self.par(t); ts, ta = V(160.37), V(161.00)
        fl = 0.9 * pulse(t, ts, 0.12) + 0.5 * bolt_env(t, V(160.20)) + 0.45 * bolt_env(t, ta)
        fr = pv('CB_sky_red', 0.45, 0.30, 1.2, dx=-20 * p, redk=0.45, ft=self.ft(t)) * 0.85
        fr = bright(fr, fl)
        fr = stonefog(fr, t, 411, 0.35, 700, 960)
        kin = clamp((t - self.t0) / 0.16)
        fr = brush(fr, (-100, 500), (2020, 430), (t - ts + 0.04) / 0.12, width=90, bend=-0.03, seed=412, life=6.0, hot=1.0)   # 刀路墨痕在人身后
        fr, _ = put(fr, t, 'CB_final', anc=(0.41, 0.56), dst=(760, 620), s=0.90 * (1 + 0.02 * u), rot=lerp(-7, 0, eout(kin)), rotblur=6.0 * (1 - kin),
                    wind=8, breathe=0.008, expo=1.0 + 0.4 * fl)
        fr = spark2(fr, t, 413, (1790, 450), n=110, life=0.6, speed=(200, 900), dirc=(1, -0.2), spread=1.0, grav=900, t0=ts, amt=1.0)
        return ink_rain(fr, t, 414, n=200, ang=10, amt=0.6, freeze=ta + (t - ta) * 0.15 if t > ta else None)


# =====================================================================================================================
NEW = dict(C22=C22, C23=C23, C24=C24, C25=C25, C26=C26, C27=C27, C28=C28, C29=C29, C30=C30, C31=C31, C32=C32, C33=C33, C34=C34,
           C35=C35, C35b=C35b, C36=C36, C37=C37, C38=C38, C39=C39, C40=C40, C40b=C40b, C41=C41)


def apply(mod):
    """在 sec_c_pre2_chorus2 里替换 C22–C41 的镜头类；切点（t0/t1）沿用原表。屏幕层字（骨未凉 / 我自己扛 / 天不）去掉。"""
    for i, S in enumerate(mod.SHOTS):
        nm = S.__name__
        if nm in NEW:
            c = NEW[nm]; c.t0, c.t1 = S.t0, S.t1; c.__name__ = nm
            mod.SHOTS[i] = c
            mod.EXPO[nm] = 1.0 / mod.EXPO_ALL                 # 风格 D：不吃段落 1.22 提亮，保留生图本身的黑白
            m = dict(mod.MOV.get(nm, {}))                     # 运镜：z 整体抬到 ≥1.015，手持 / 重拍抖动不在画边露出反射接缝（推拉方向与幅度不变）
            z0, z1 = m.get('z', (1.0, 1.0)); lift = 1.015 / min(z0, z1)
            if lift > 1: m['z'] = (z0 * lift, z1 * lift)
            mod.MOV[nm] = m
    t22 = NEW['C22'].t0
    mod.SENTS = [s for s in mod.SENTS if s.tin[0] < t22 - 1e-6]
