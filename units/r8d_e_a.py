"""units/r8d_e_a.py — 第八轮风格 D（日漫墨线 + 网点 + 黑白血红）：E 组副歌终章 E01–E26（帧 5797–6638，原镜号 S111–S131）。

只在 STYLE_D=1 时由 sec_e_final_outro 末尾的钩子 import 并 apply(本段模块)；STYLE_D=0 完全不加载，现版逐像素不变。
做法：SHOTS 里替换 E01–E26 的类（起帧 / 原镜号 / 景别不变），IDS / BOUNDS 随之重算；CUTS / MOVE 只改本单元镜头的条目。
切点、镜长、入转场、字幕（units/subtitle.py）全部不动；E27a 起（尾奏、片尾）归 E-B 单元，不碰。

素材：assets/gen/R8_D/EA/（nananobanana RH_image2，提示词 jobs/r8_D_EA.json，记录 crew/round8/genlog_EA.md）。
  背景板：EA_sky（白纸晨空 + 墨云）、EA_E03（碑林一点透视）、EA_E04bg（暗殿 + 斜光）、EA_E06（挂轴林）、EA_E08（纸扎太上皇巨脸）、
          EA_topground（俯拍焦土）、EA_check（✓ 白纸 + 红日）、EA_cross（✗ 朱红底）
  抠像：EA_sun（血红日）、EA_ridge（前景山脊）、EA_line（贴地火线一点透视）、EA_blade（竖刀）、EA_plaque（「天理昭彰」匾）、
        EA_tablet（「天理」木律令牌）、EA_E12（「鬼屠」朱印 + 印心插刀，同一张图）、EA_shreds（碎纸）、
        EA_emperor / EA_effigy（太上皇 / 纸扎）、主角 EA_E02 E09b E11 E12man E13 E14 E16 E17 E19 E21 E22 E23 E25
保留的字（都在生图里，代码只做点亮 / 揭开 / 盖印）：E04/E05「天理昭彰」匾、E12「鬼屠」印（剑与印同图生成）、
  E14T/E15「天理」木牌、E16 ✓ / E17 ✗ / E18 ✓✗。其余画面字全部去掉（原 E01 血、E02 刀不放印、E03 世间从来没有、E06 若规则是、
  E07 谎言、E08 伪装、E09 那就撕碎、E10 它自己、E11 定、E12 自己定规章、E13 血、E19 何须伪装、E20 天、E21 我、E22 我来量、
  E24 刀、E25 的正、E26 正道沧桑）。
"""
import copy, math, os, sys
import numpy as np, cv2

ROOT = os.environ.get('MV_ROOT', '/workspace/work/mv')
import c1kit as K
import sprite as SP
import e_r3 as R3
import e_r6 as R6
import e_r7 as R7

W, H, BAR = 1920, 1080, 120
FPS = 30
GEN = ROOT + '/assets/gen/R8_D/EA/'
NEU = dict(expo=1.0, sat=1.0, tint=(1.0, 1.0, 1.0), lift=0.0, gamma=1.0)
NORIM = dict(col=(1.0, 1.0, 1.0), amt=0.0, dir=(0.0, -1.0))
RED = np.array([0.80, 0.04, 0.03], np.float32)
WHITE = np.array([1.0, 1.0, 1.0], np.float32)
INK = np.array([0.02, 0.02, 0.02], np.float32)
M = None          # sec_e_final_outro 模块（apply 时注入）


def c01(x): return float(min(1.0, max(0.0, x)))
def eio(x): x = c01(x); return x * x * (3 - 2 * x)
def eout(x, k=3): x = c01(x); return 1 - (1 - x) ** k
def ein(x, k=3): x = c01(x); return x ** k
def sstep(a, b, x):
    x = np.clip((x - a) / (b - a), 0, 1); return x * x * (3 - 2 * x)
def pulse(t, t0, tau=0.12): return math.exp(-max(0.0, t - t0) / tau) if t >= t0 - 1e-6 else 0.0


def CT(li, k): return M.CT(li, k)


_G = {}
def grid():
    if 'g' not in _G: _G['g'] = tuple(a.astype(np.float32) for a in np.mgrid[0:H, 0:W])
    return _G['g']


# ------------------------------------------------------------------ 素材
# 挂轴林底板（EA_E06）上的律令小字（用户 11-11：「白布上面的小字，可以保留的」）：生图里轴面是空白的，这里按每幅轴的四角透视
# 用马善政楷书竖排密写真实的律令条文（不是假字），乘到纸面上（墨色随纸面明暗，光带 / 阴影照旧），在 sway / 推轨之前写进底板，
# 所以字跟着布一起摆，不会漂。E06 / E07 / E09 / E10 共用这张底板。
SCROLL_QUADS = [   # (左上, 右上, 右下, 左下)，1920×1080 底板坐标；按从后到前写
    ((1057, 345), (1093, 345), (1093, 780), (1053, 780)),
    ((830, 335), (875, 335), (866, 815), (812, 815)),
    ((1760, 342), (1842, 342), (1905, 832), (1812, 832)),
    ((1122, 275), (1206, 275), (1212, 875), (1122, 875)),
    ((1217, 180), (1278, 180), (1297, 760), (1226, 760)),
    ((127, 205), (222, 205), (146, 755), (18, 755)),
    ((664, 172), (818, 172), (803, 873), (628, 873)),
    ((378, 4), (556, 4), (512, 828), (242, 828)),
    ((1368, 4), (1596, 4), (1708, 828), (1390, 828)),
]
LAW = ('凡天下臣民皆当守法不得僭越礼制违者论罪轻者笞杖重者流徙其有谋逆者斩立决家产籍没妻子为奴凡官吏受财枉法者计赃论罪'
       '一贯以下杖七十每五贯加一等至八十贯者绞凡私议朝政妄言天命者斩凡聚众持械抗拒官府者首犯斩从犯流三千里凡婚姻田土钱债'
       '之事皆听有司断决不得私相仇杀凡奉旨行刑者不得稽迟凡律令所载皆为天理所在臣民敬之守之不得有违违者天地不容')


def scroll_text(img):
    from PIL import Image as _I, ImageDraw as _D, ImageFont as _F
    fnt = _F.truetype(ROOT + '/fonts/MaShanZheng-Regular.ttf', 64)
    r = np.random.default_rng(606)
    lum = img.mean(-1)
    for qi, q in enumerate(SCROLL_QUADS):
        q = np.float32(q)
        wq = float(np.linalg.norm(q[1] - q[0])); hq = float(np.linalg.norm(q[3] - q[0]))
        ncol = max(2, int(round(wq / 27)))                               # 每列约 27px 宽（屏幕，§12.6：1080p 下单字可辨），竖排、从右往左
        cw = 80; ch = 74
        nrow = max(6, int(round(hq / wq * ncol * cw / ch)))
        Wc, Hc = ncol * cw + 40, nrow * ch + 60
        can = _I.new('L', (Wc, Hc), 0); d = _D.Draw(can)
        k = int(r.integers(0, len(LAW)))
        for c in range(ncol):
            x = Wc - 20 - (c + 1) * cw + 8
            n = nrow - (int(r.integers(0, 4)) if c % 3 == 2 else 0)        # 段落长短不齐（像条文换段）
            for j in range(n):
                d.text((x, 30 + j * ch), LAW[(k + c * nrow + j) % len(LAW)], fill=255, font=fnt)
        a = np.asarray(can, np.float32) / 255
        src = np.float32([[0, 0], [Wc, 0], [Wc, Hc], [0, Hc]])
        Mq = cv2.getPerspectiveTransform(src, q)
        aw = cv2.warpPerspective(a, Mq, (W, H), flags=cv2.INTER_AREA)
        inside = cv2.warpPerspective(np.ones_like(a), Mq, (W, H)) > 0.5
        paper = np.clip((lum - 0.25) / 0.25, 0, 1) * inside                 # 只写在纸面（亮处），挡在前面的轴 / 木杆不写
        ink = np.clip(aw * 1.4, 0, 1) * paper * 0.85
        img = img * (1 - ink[..., None]) + ink[..., None] * 0.05
    return img


_SB = {}
def _scroll_base(im):
    if 'b' not in _SB: _SB['b'] = scroll_text(im)
    return _SB['b'].copy()


_PL = {}
def plate(name, flip=False, blur=0.0, gain=1.0):
    k = (name, flip, blur, gain)
    if k not in _PL:
        im = cv2.imread(GEN + name + '.png', cv2.IMREAD_COLOR)[..., ::-1]
        im = cv2.resize(im, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        if name == 'EA_E06': im = _scroll_base(im)
        if flip: im = im[:, ::-1]
        if blur:                                                         # SPREAD §11①：不做景深虚化；远景用「白纸雾 + 网点」渐隐（降对比、线条保持清楚）
            hz = min(0.55, blur / 18)
            dots = np.sin(np.arange(W, dtype=np.float32)[None, :] * 0.9) * np.sin(np.arange(H, dtype=np.float32)[:, None] * 0.9)
            im = im * (1 - hz) + (0.90 - 0.06 * (dots > 0.7))[..., None] * hz
        _PL[k] = np.ascontiguousarray(im * gain, np.float32)
    return _PL[k]


def spr(name): return SP.layer(GEN + name + '_cut.png')


def sub_layer(sp, mask):
    """同一张精灵拆层：复制一份 SpriteLayer，只换 alpha（缓存键带 id(A) 与新 uid，不串）。"""
    m = copy.copy(sp)
    m.A = np.ascontiguousarray(sp.A * mask, np.float32)
    m._box = {}; m._supp = None; m._supp_for = None
    SP._UID[0] += 1; m._uid = SP._UID[0]
    return m


def flipped(sp):
    """水平翻转副本（§P1-7 血红日去重）：F / A 同时镜像，缓存 uid 另起，不污染原精灵。"""
    m = sub_layer(sp, 1.0)
    m.F = np.ascontiguousarray(m.F[:, ::-1]); m.A = np.ascontiguousarray(m.A[:, ::-1])
    m.wind_w = np.ascontiguousarray(m.wind_w[:, ::-1]); m.ring = np.ascontiguousarray(m.ring[:, ::-1])
    m.bbox = (1.0 - sp.bbox[2], sp.bbox[1], 1.0 - sp.bbox[0], sp.bbox[3])
    m._box = {}; m._supp = None; m._supp_for = None
    return m


def _wind(w):
    """SPREAD §12.3：置换只做弱的——幅度压到原来的 45%、上限 4.5px（精灵 wind_w 只在发梢 / 衣带边缘非零，脸和身体不动）。"""
    return min(4.5, 0.45 * w)


def shadow_gray(im, floor=0.30, dk=0.45, freq=1.45):
    """SPREAD §10.1：低调光镜的暗部抬到网点灰——L<floor 的区域按权重换成 floor 的网点，
    亮部（光柱、白纸、保留的字）基本不动，暗部不再是一片死黑。"""
    yy, xx = grid()
    d = (np.sin(xx * freq) * np.sin(yy * freq) > 0.45).astype(np.float32)
    d = cv2.GaussianBlur(d, (0, 0), 0.65)[..., None]
    L = im.mean(-1, keepdims=True)
    w = np.clip((floor - L) / max(floor, 1e-3), 0, 1) ** 0.8
    tone = floor * (1 - dk * d)
    return np.ascontiguousarray(im * (1 - w) + tone * w, np.float32)


def put(fr, sp, t, h, foot, wind=6.0, breathe=0.004, **kw):
    """按包围盒高度落脚（脚底中点 → foot）。grade / rim / wrap / shade 一律中性（风格 D 不调色）。"""
    a, s = sp.fit(h)
    return sp.draw(fr, t, a, foot, s, grade=NEU, rim=NORIM, wrap=0, shade=None, wind_amp=_wind(wind), breathe=breathe, **kw)


def put_at(fr, sp, t, src, dst, scale, wind=6.0, breathe=0.004, **kw):
    """源归一化点 src → 屏幕 dst，scale = 精灵工作宽（2048）→ 屏幕像素倍率。"""
    return sp.draw(fr, t, src, dst, scale, grade=NEU, rim=NORIM, wrap=0, shade=None, wind_amp=_wind(wind), breathe=breathe, **kw)


def scr_of(sp, h, foot, p):
    """put() 落脚后，源归一化点 p 的屏幕坐标（不含呼吸）。"""
    a, s = sp.fit(h)
    return (foot[0] + (p[0] - a[0]) * sp.w * s, foot[1] + (p[1] - a[1]) * sp.h * s)


def scr_at(sp, src, dst, scale, p):
    """put_at 摆放后，源归一化点 p 的屏幕坐标（无旋转）。"""
    return (dst[0] + (p[0] - src[0]) * sp.w * scale, dst[1] + (p[1] - src[1]) * sp.h * scale)


def ground_fade(sp, y0=0.93, seed=5):
    """木牌木桩底部（贴画布下沿）改成不规则的入土边：alpha 在 y0 以下按噪声渐隐（不是直线截断）。"""
    h, w = sp.A.shape
    nz = cv2.resize(np.random.default_rng(seed).random((8, 64)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    yv = (np.arange(h, dtype=np.float32) / h)[:, None]
    return sub_layer(sp, np.clip((y0 + 0.04 * nz - yv) / 0.02, 0, 1))


def comp_pick(sp, x0, y0, x1, y1):
    """按连通域挑精灵里的整片（质心落在区域内的整片都要，不切片）。"""
    a = (sp.A > 0.05).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(a, 8)
    h, w = a.shape
    keep = np.zeros(n, np.float32)
    for i in range(1, n):
        cx, cy = cen[i][0] / w, cen[i][1] / h
        if x0 <= cx <= x1 and y0 <= cy <= y1: keep[i] = 1
    return sub_layer(sp, keep[lab])


_FLOW = {}
def _noise2(seed, gh=H // 24, gw=W // 24):
    r = np.random.default_rng(seed)
    out = []
    for _ in range(4):                                                     # 两对低频噪声（x / y 各一对，做时间上的旋转插值）
        n = cv2.GaussianBlur(r.standard_normal((gh, gw)).astype(np.float32), (0, 0), 2.2)
        out.append(n / (n.std() + 1e-6))
    return out


def _flow_maps(t, seed, drift, amp, w=None, omega=0.55):
    """低频噪声流场：整体漂移 drift（px/s）+ 随时间缓慢转动的噪声扰动 amp（px）；w 为逐像素权重（0 处不动）。"""
    key = ('n', seed)
    if key not in _FLOW: _FLOW[key] = _noise2(seed)
    ax, bx, ay, by = _FLOW[key]
    c, s = math.cos(omega * t), math.sin(omega * t)
    nx = cv2.resize(ax * c + bx * s, (W, H), interpolation=cv2.INTER_CUBIC)
    ny = cv2.resize(ay * c + by * s, (W, H), interpolation=cv2.INTER_CUBIC)
    dx = drift[0] * t + amp * nx; dy = drift[1] * t + amp * 0.45 * ny
    if w is not None: dx = dx * w; dy = dy * w
    yy, xx = grid()
    return (xx - dx).astype(np.float32), (yy - dy).astype(np.float32)


def flow_plate(img, t, seed=1, drift_far=(-7.0, 0.0), drift_near=(-22.0, 1.0), amp_far=3.0, amp_near=6.0):
    """SPREAD §12.2：天 / 云不是「一张图平移旋转」——拆两层各走各的流场。
    远层 = 底板把深色云块补底去掉后的白纸 + 浅灰云（慢漂 + 小扰动）；近层 = 深墨云 / 血红云带（快漂 + 大扰动），
    两层速度、扰动相位都不同，云在流、云和天之间有相对运动。底板是生图像素，没有新增 AI 像素。"""
    key = ('p', id(img))
    if key not in _FLOW:
        lum = img.mean(-1)
        red = np.clip((img[..., 0] - img[..., 1]) * 2 - 0.4, 0, 1)
        near = np.clip((0.42 - lum) / 0.12, 0, 1)
        near = np.maximum(near, red * np.clip((0.75 - lum) / 0.2, 0, 1))
        near = cv2.morphologyEx(near.astype(np.float32), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))   # 整团云（含云内亮边）一起走，不撕成碎块
        near = cv2.GaussianBlur(near, (0, 0), 3.0)
        clean = inpaint_mask(img, (near > 0.2).astype(np.float32), rad=11)
        _FLOW[key] = (np.ascontiguousarray(clean, np.float32), np.ascontiguousarray(near, np.float32))
        if len(_FLOW) > 24: [_FLOW.pop(k) for k in [k for k in _FLOW if k[0] == 'p'][:6]]
    clean, near = _FLOW[key]
    mx, my = _flow_maps(t, seed, drift_far, amp_far)
    out = cv2.remap(clean, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    mx, my = _flow_maps(t + 3.7, seed + 50, drift_near, amp_near, omega=0.8)
    ink = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    a = cv2.remap(near, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)[..., None]
    return out * (1 - a) + ink * a


def flow_region(img, t, mask_key, mask, seed=3, amp=10.0, drift=(-6.0, 0.0)):
    """只在 mask 区内做噪声流动（如 E03 的血红天），权重在边界平滑归零，碑 / 地面等硬物不被拖拽。"""
    key = ('m', mask_key)
    if key not in _FLOW:
        _FLOW[key] = cv2.GaussianBlur(cv2.erode(mask.astype(np.float32), np.ones((15, 15), np.uint8)), (0, 0), 9)
    w = _FLOW[key]
    mx, my = _flow_maps(t, seed, drift, amp, w=w)
    return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def _flow_smoke(sm, t, seed, drift, amp):
    """低频烟层：时间上缓慢转动的噪声位移（§12.3：低振幅、低频、只在烟层内部），避免「整张烟平移」。"""
    key = ('s', seed)
    if key not in _FLOW:
        n = _noise2(seed, gh=sm.shape[0], gw=sm.shape[1])
        _FLOW[key] = [cv2.resize(a, (sm.shape[1], sm.shape[0]), interpolation=cv2.INTER_CUBIC) for a in n]
    ax, bx, ay, by = _FLOW[key]
    c, s_ = math.cos(0.5 * t), math.sin(0.5 * t)
    h, w = sm.shape
    gh, gw = np.mgrid[0:h, 0:w].astype(np.float32)
    mx = gw - (drift[0] * t + amp * (ax * c + bx * s_)) * (w / W)
    my = gh - (drift[1] * t + amp * 0.4 * (ay * c + by * s_)) * (h / H)
    return cv2.remap(sm, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


_CH18 = None
def lava_crack_local(fr, x, t, seed=18, width=34, top=120, bot=960):
    """与 R6.lava_crack 同一条裂缝，但喷出的不是灰色平涂多边形：改成墨线勾边的纸片（白 / 网点灰）与墨块，无投影。"""
    global _CH18
    if _CH18 is None:
        _CH18 = (Chips(1817, n=26, size=(10, 30), spread=(210, 430), zr=(0.9, 2.4), tones=(0.95, 0.62, 0.05)),
                 Chips(1818, n=10, size=(8, 20), spread=(160, 380), zr=(0.6, 1.4), tones=(0.88, 0.1)))
    yy = np.arange(H, dtype=np.float32)
    r = np.random.default_rng(seed)
    path = np.zeros(H, np.float32)
    for k in range(5):
        f = r.uniform(0.006, 0.05); path += r.uniform(3, 9) * np.sin(yy * f + r.uniform(0, 6))
    cx = x + path
    xx = np.arange(W, dtype=np.float32)[None, :]
    d = np.abs(xx - cx[:, None])
    wv = width * (0.7 + 0.5 * np.sin(yy * 0.05 + t * 9)[:, None] * 0.3 + 0.3 * np.sin(yy * 0.013)[:, None])
    core = np.exp(-(d / (wv * 0.28)) ** 2)
    hot = np.exp(-(d / (wv * 0.7)) ** 2)
    char = np.clip(1 - d / (wv * 1.6), 0, 1)
    vis = ((yy >= top) & (yy <= bot)).astype(np.float32)[:, None]
    fr = fr * (1 - 0.85 * char * vis)[..., None]
    fr = fr + (hot * vis)[..., None] * np.array([0.9, 0.18, 0.04], np.float32) * 1.25 + (core * vis)[..., None] * np.array([1.0, 0.86, 0.62], np.float32) * 1.4
    gl = cv2.GaussianBlur((hot * vis).astype(np.float32), (0, 0), 30)
    fr = fr + gl[..., None] * np.array([1.0, 0.35, 0.08], np.float32) * 0.55
    q = t - M.CT(53, 7)
    if q > 0:                                                              # 碎屑从缝里往外走（两簇，左右各一层景深）
        for c in _CH18: fr = c.draw(fr, min(q * 0.9, 1.0), c=(960, 560), to_cam=0.35, zf=1.4)
    return fr


def contact(fr, foot, wid, amt=0.55, dirx=-1.0, length=0.0, sq=6.0):
    """SPREAD §12.5 接地：脚下一块压扁的接触暗影 + 可选沿光向的短投影（光从日的方向来，影子拖向反方向），人和地面同一光源。"""
    yy, xx = grid()
    d = ((xx - foot[0]) / wid) ** 2 + ((yy - foot[1]) * sq / wid) ** 2
    m = np.exp(-d * 2.2)
    if length > 0:
        sx = xx - foot[0]; along = np.clip(sx * dirx / length, 0, 1)
        m = np.maximum(m, np.exp(-((yy - foot[1] - 0.04 * sx * dirx) * sq / wid) ** 2 * 2.2) * (1 - along) * (sx * dirx > 0) * (along < 1) * 0.8)
    return fr * (1 - amt * np.clip(m, 0, 1))[..., None]


def warp_plate(img, s, cx, cy, rot=0.0):
    """底板点 (cx,cy) → 屏幕中心，放大 s。"""
    Mt = cv2.getRotationMatrix2D((float(cx), float(cy)), rot, s)
    Mt[0, 2] += 960 - cx; Mt[1, 2] += 540 - cy
    return cv2.warpAffine(img, Mt, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


_DL = {}
def dolly(img, c, z, g):
    """伪 3D 推轨：离灭点越远（越近镜头）放大越多（z 整体放大，g 近景额外放大量）。视差来自同一张图的径向分层。"""
    yy, xx = grid()
    dx, dy = xx - c[0], yy - c[1]
    r = np.sqrt(dx * dx + dy * dy) / 1100.0
    s = z * (1 + g * np.clip(r, 0, 1.6) ** 1.3)
    return cv2.remap(img, (c[0] + dx / s).astype(np.float32), (c[1] + dy / s).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ------------------------------------------------------------------ 风格 D 代码笔触（干笔飞白 / 溅墨 / 墨线速度线 / 墨线碎片）
def ink_slash(fr, p0, p1, prog, fade, width=56, seed=1, core=WHITE, edge=RED, splat=True):
    """干笔斩痕：十几根长短不一的笔毛线（中间白、两侧血红、外沿墨线），沿 p0→p1 扫出 prog，fade 衰减；沿线甩出墨点。"""
    if fade <= 0.01 or prog <= 0: return fr
    r = np.random.default_rng(seed)
    p0 = np.array(p0, np.float32); p1 = np.array(p1, np.float32)
    d = p1 - p0; L = float(np.linalg.norm(d)); d /= L; n = np.array([-d[1], d[0]], np.float32)
    Lw = np.zeros((H // 2, W // 2), np.float32); Lr = np.zeros_like(Lw); Lk = np.zeros_like(Lw)
    nb = 15
    for j in range(nb):
        o = (j / (nb - 1) - 0.5) * 2
        taper = 1 - abs(o) ** 1.6
        a0 = r.uniform(0.0, 0.18) * (1 - taper * 0.8); a1 = min(prog, r.uniform(0.78, 1.0) - (1 - taper) * 0.25)
        if a1 <= a0: continue
        segs = np.sort(r.uniform(a0, a1, 4)); pts = [a0] + list(segs) + [a1]
        for k in range(0, len(pts) - 1, 2 if abs(o) > 0.6 else 1):            # 外侧笔毛断续（飞白）
            q0 = p0 + d * L * pts[k] + n * o * width * 0.5; q1 = p0 + d * L * pts[k + 1] + n * o * width * 0.5
            tgt = Lw if abs(o) < 0.45 else Lr
            th = max(1, int(width / nb * (1.6 if abs(o) < 0.45 else 1.1)))
            cv2.line(tgt, (int(q0[0] * 2), int(q0[1] * 2)), (int(q1[0] * 2), int(q1[1] * 2)), 1.0, th, cv2.LINE_AA, 2)
    for s_ in (-1, 1):                                                       # 外沿墨线
        q0 = p0 + n * s_ * width * 0.62; q1 = p0 + d * L * prog * 0.96 + n * s_ * width * 0.3
        cv2.line(Lk, (int(q0[0] * 2), int(q0[1] * 2)), (int(q1[0] * 2), int(q1[1] * 2)), 1.0, 2, cv2.LINE_AA, 2)
    if splat:
        for i in range(26):
            a = r.uniform(0.2, 1.0) * prog
            q = p0 + d * L * a + n * r.normal(0, width * 1.3)
            cv2.circle(Lk if i % 3 else Lr, (int(q[0] / 2), int(q[1] / 2)), int(r.uniform(1, 5)), 1.0, -1, cv2.LINE_AA)
    Lw = cv2.resize(cv2.GaussianBlur(Lw, (0, 0), 0.7), (W, H)); Lr = cv2.resize(cv2.GaussianBlur(Lr, (0, 0), 0.7), (W, H))
    Lk = cv2.resize(cv2.GaussianBlur(Lk, (0, 0), 0.6), (W, H))
    fr = fr * (1 - np.clip(Lk * 0.9 * fade, 0, 1))[..., None]
    fr = fr * (1 - np.clip(Lr * fade, 0, 1))[..., None] + (Lr * fade)[..., None] * np.asarray(edge, np.float32)
    fr = fr * (1 - np.clip(Lw * fade, 0, 1))[..., None] + (Lw * fade)[..., None] * np.asarray(core, np.float32) * 1.15
    return fr + K.blur_ds(Lw * fade, 14)[..., None] * 0.35


def speed_radial(fr, c, amt, t, seed=7, inner=0.28, white=False):
    """漫画集中线（墨线，向灭点 c 收拢；amt 强度）。"""
    if amt <= 0.01: return fr
    r = np.random.default_rng(seed + int(t * 30))
    L = np.zeros((H // 2, W // 2), np.float32)
    for i in range(120):
        ang = r.uniform(0, 2 * math.pi); r0 = r.uniform(inner, inner + 0.25) * 1100; r1 = 1500
        w = r.uniform(0.6, 2.4)
        a0 = (c[0] + math.cos(ang) * r0, c[1] + math.sin(ang) * r0); a1 = (c[0] + math.cos(ang) * r1, c[1] + math.sin(ang) * r1)
        cv2.line(L, (int(a0[0] * 2), int(a0[1] * 2)), (int(a1[0] * 2), int(a1[1] * 2)), r.uniform(0.5, 1.0), max(1, int(w)), cv2.LINE_AA, 2)
    L = cv2.resize(L, (W, H)) * amt
    if white: return fr + L[..., None] * 0.9
    return fr * (1 - np.clip(L, 0, 1))[..., None]


def speed_h(fr, amt, t, seed=9, y0=BAR, y1=H - BAR, dirx=1):
    """横向速度线（黑白各半）。"""
    if amt <= 0.01: return fr
    r = np.random.default_rng(seed + int(t * 30))
    Lk = np.zeros((H // 2, W // 2), np.float32); Lw = np.zeros_like(Lk)
    for i in range(60):
        y = r.uniform(y0, y1) / 2; x = r.uniform(-200, W) / 2; ln = r.uniform(160, 620) / 2
        cv2.line(Lk if i % 3 else Lw, (int(x), int(y)), (int(x + dirx * ln), int(y)), r.uniform(0.4, 1.0), 1, cv2.LINE_AA)
    Lk = cv2.resize(Lk, (W, H)) * amt; Lw = cv2.resize(Lw, (W, H)) * amt
    return fr * (1 - np.clip(Lk * 0.8, 0, 1))[..., None] + Lw[..., None] * 0.8


class Chips:
    """墨线勾边的碎片（匾 / 纸 / 石）：不规则多边形，白 / 灰 / 黑三种面，外沿一圈墨线；z 深度 → 大小 + 虚化。"""
    def __init__(self, seed, n=40, size=(14, 46), spread=(1100, 520), zr=(0.6, 2.6), tones=(0.95, 0.55, 0.06)):
        r = np.random.default_rng(seed)
        self.P = []
        for i in range(n):
            k = int(r.integers(4, 8)); ang = np.sort(r.uniform(0, 2 * math.pi, k)); rad = r.uniform(0.5, 1.0, k)
            self.P.append(dict(v=np.stack([np.cos(ang) * rad, np.sin(ang) * rad * r.uniform(0.4, 1.0)], 1), s=r.uniform(*size),
                               x=r.uniform(-1, 1) * spread[0], y=r.uniform(-1, 1) * spread[1], z=r.uniform(*zr),
                               vx=r.normal(0, 40), vy=r.normal(-20, 30), w=r.normal(0, 2.0), ph=r.uniform(0, 6.3),
                               tone=float(tones[int(r.integers(0, len(tones)))])))

    def draw(self, fr, q, c=(960, 540), to_cam=0.0, zf=1.4, alpha=1.0):
        order = sorted(self.P, key=lambda p: -(p['z'] - to_cam * q))
        for p in order:
            z = max(0.25, p['z'] - to_cam * q)
            sc = 1.0 / z
            cx = c[0] + (p['x'] + p['vx'] * q) * sc; cy = c[1] + (p['y'] + p['vy'] * q) * sc
            s = p['s'] * sc * 1.4
            if not (-200 < cx < W + 200 and -200 < cy < H + 200): continue
            a = p['ph'] + p['w'] * q; ca, sa = math.cos(a), math.sin(a)
            flip = abs(math.cos(p['ph'] * 2 + q * p['w'] * 1.3))
            v = p['v'] * np.array([1.0, 0.25 + 0.75 * flip])
            pts = np.stack([v[:, 0] * ca - v[:, 1] * sa, v[:, 0] * sa + v[:, 1] * ca], 1) * s + [cx, cy]
            x0, y0 = np.floor(pts.min(0)).astype(int) - 12; x1, y1 = np.ceil(pts.max(0)).astype(int) + 12
            x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
            if x1c <= x0c or y1c <= y0c: continue
            m = np.zeros((y1 - y0, x1 - x0), np.float32); e = np.zeros_like(m)
            pp = ((pts - [x0, y0]) * 4).astype(np.int32)
            cv2.fillPoly(m, [pp], 1.0, cv2.LINE_AA, 2); cv2.polylines(e, [pp], True, 1.0, max(1, int(2 * sc)), cv2.LINE_AA, 2)
            blur = min(0.9, abs(z - zf) * 0.5)
            if blur > 0.6: m = cv2.GaussianBlur(m, (0, 0), blur); e = cv2.GaussianBlur(e, (0, 0), blur)
            m = m[y0c - y0:y1c - y0, x0c - x0:x1c - x0] * alpha; e = e[y0c - y0:y1c - y0, x0c - x0:x1c - x0] * alpha
            tone = p['tone'] * (0.75 + 0.25 * flip)
            roi = fr[y0c:y1c, x0c:x1c]
            roi = roi * (1 - m[..., None]) + tone * m[..., None]
            fr[y0c:y1c, x0c:x1c] = roi * (1 - 0.9 * e[..., None])
        return fr


def ink_ring(fr, c, r, a, squash=4.0, seed=3):
    """落地尘环：灰白尘带 + 墨点（漫画式冲击环）。"""
    if a <= 0.01: return fr
    yy, xx = grid()
    d = np.hypot(xx - c[0], (yy - c[1]) * squash)
    ring = np.exp(-((d - r) / (26 + r * 0.05)) ** 2) * a
    nz = cv2.resize(K.fbm(H // 8, W // 8, seed, base=8, octaves=3), (W, H))
    ring = ring * np.clip(nz * 1.8 - 0.3, 0, 1)
    fr = fr * (1 - ring[..., None] * 0.6) + ring[..., None] * 0.92
    edge = np.exp(-((d - r - 30) / 3) ** 2) * a * (nz > 0.55)
    return fr * (1 - edge[..., None] * 0.8)


def sparks2(fr, t, seed, o, t0=None, n=50, burst=True, dirc=(0, -1), spread=1.1, speed=(400, 1300), grav=900, life=0.55, amt=1.0, area=(30, 20)):
    """火星：白 + 血红两组。"""
    kw = dict(n=n, life=life, speed=speed, dirc=dirc, spread=spread, grav=grav, burst=burst, t0=t0, area=area)
    fr = K.sparks(fr, t, seed, o, color=(1.0, 1.0, 1.0), amt=0.9 * amt, **kw)
    kw['n'] = max(4, n // 2)
    return K.sparks(fr, t, seed + 1, o, color=(0.85, 0.04, 0.03), amt=1.1 * amt, **kw)


def embers(fr, t, seed, n=50, amt=0.6, rise=90):
    """余烬：白 + 血红。"""
    fr = M.RS.fx_embers(fr, t, seed, amt=amt, n=n, col=(1.0, 1.0, 1.0), rise=rise)
    return M.RS.fx_embers(fr, t, seed + 7, amt=amt * 0.9, n=max(6, n // 2), col=(0.85, 0.05, 0.03), rise=rise)


def dust(fr, t, seed, n=60, amt=0.35, drift=(20, -12), size=(1, 3)):
    return M.E.dust_motes(fr, t, seed, n=n, amt=amt, drift=drift, col=(0.95, 0.95, 0.95), size=size, depth=True)


def fog(fr, t, seed, amt=0.35, speed=(30, 0), y0=0.55, y1=1.0, col=(0.92, 0.92, 0.92)):
    return K.fog(fr, t, seed, amt=amt, speed=speed, y0=y0, y1=y1, color=col)


def rays(fr, src, t, strength=0.6, length=1.0, occ=None, src_r=160):
    return M.fx2.god_rays(fr, src, strength=strength, length=length, t=t, src_r=src_r, color=np.array([1.0, 1.0, 1.0], np.float32), occluder=occ)


def flare(fr, p, amt, angle=0.0, length=1.0, scale=1.0, rays=1.0):
    """SPREAD §11②：不用写实镜头光斑 / 鬼影 —— 硬边白色十字星芒（细线，长短两组）+ 小白点，外圈一圈墨线短芒。
    scale 缩星芒尺寸；rays 缩外圈墨线短芒（P1-6：日面上的星芒不能像准星贯穿日轮）。"""
    if amt <= 0.01: return fr
    L = np.zeros((H // 2, W // 2), np.float32); Kk = np.zeros_like(L)
    cx, cy = p[0] / 2, p[1] / 2
    for k, (ln, w) in enumerate(((520 * scale, 2), (520 * scale, 2), (150 * scale, 1), (150 * scale, 1))):
        a = math.radians(angle + 90 * k) if k < 2 else math.radians(angle + 45 + 90 * (k - 2))
        for sgn in (1, -1):
            e = (cx + sgn * math.cos(a) * ln * length / 2, cy + sgn * math.sin(a) * ln * length / 2)
            cv2.line(L, (int(cx * 8), int(cy * 8)), (int(e[0] * 8), int(e[1] * 8)), 1.0, w, cv2.LINE_AA, 3)
    cv2.circle(L, (int(cx * 8), int(cy * 8)), int(7 * 8 * scale), 1.0, -1, cv2.LINE_AA, 3)
    for k in range(8):
        a = math.radians(angle + 22.5 + 45 * k)
        cv2.line(Kk, (int((cx + math.cos(a) * 14 * rays) * 8), int((cy + math.sin(a) * 14 * rays) * 8)),
                 (int((cx + math.cos(a) * 26 * rays) * 8), int((cy + math.sin(a) * 26 * rays) * 8)), 1.0, 1, cv2.LINE_AA, 3)
    L = cv2.resize(L, (W, H)) * min(1.0, amt); Kk = cv2.resize(Kk, (W, H)) * min(1.0, amt)
    fr = fr * (1 - np.clip(Kk * 0.8, 0, 1))[..., None]
    return fr * (1 - np.clip(L, 0, 1))[..., None] + np.clip(L, 0, 1)[..., None] * 1.05


def bloom(fr, thr=0.85, amt=0.3): return K.bloom(fr, thr, amt, 26)


def inpaint_mask(img, mask, rad=9):
    """把生图里的符号笔画先藏起来（代码再按笔顺揭开）：在半分辨率上 Telea 补底，再放大回原尺寸只取蒙版区域。"""
    h, w = img.shape[:2]
    small = cv2.resize((np.clip(img, 0, 1) * 255).astype(np.uint8), (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    ms = cv2.resize((mask > 0.5).astype(np.uint8) * 255, (w // 2, h // 2), interpolation=cv2.INTER_NEAREST)
    ms = cv2.dilate(ms, np.ones((7, 7), np.uint8))
    out = cv2.inpaint(small, ms, rad, cv2.INPAINT_TELEA).astype(np.float32) / 255
    out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
    md = cv2.GaussianBlur(cv2.dilate((mask > 0.5).astype(np.float32), np.ones((13, 13), np.uint8)), (0, 0), 3)[..., None]
    return img * (1 - md) + out * md


def stroke_param(mask, pts):
    """沿笔顺折线 pts 给笔画每个像素一个弧长参数（0..1）：取最近的线段投影。"""
    yy, xx = grid()
    P = np.array(pts, np.float32)
    seg = np.hypot(*np.diff(P, axis=0).T); cum = np.r_[0, np.cumsum(seg)]; tot = cum[-1]
    best = np.full((H, W), 1e9, np.float32); par = np.zeros((H, W), np.float32)
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]; d = (b - a) / seg[i]
        u = np.clip((xx - a[0]) * d[0] + (yy - a[1]) * d[1], 0, seg[i])
        dist = np.hypot(xx - (a[0] + d[0] * u), yy - (a[1] + d[1] * u))
        m = dist < best
        best = np.where(m, dist, best); par = np.where(m, (cum[i] + u) / tot, par)
    return par.astype(np.float32)


# ==================================================================== 镜头基类
class Shot:
    def u(self, t): return (t - self.t0) / (self.t1 - self.t0)
    def render(self, t): return np.zeros((H, W, 3), np.float32)
    def text(self, fr, t): return fr          # 风格 D：本单元镜头没有屏幕字层（保留的字都在生图里）


# ==================================================================== E01 S111 ECU 竖刀迎日（193.23–194.10）
class E01(Shot):
    """白纸晨空（墨云）+ 左下血红日 + 竖刀（生图）纵贯画面偏右；日光自下而上扫过刃口（白光点 + 横向眩光），
    「血」字头起一道血珠沿刃口缓缓下淌（墨线描边）；刀尖白星芒；前景白尘。分层：天 0.25 / 日 0.5 / 刀（锁定）/ 前景尘。"""
    def __init__(self):
        self.sky = plate('EA_sky')
        self.sun = flipped(spr('EA_sun')); self.blade = spr('EA_blade')
        self.tb = CT(48, 0)

    def render(self, t):
        u = self.u(t); pv = u - 0.5
        fr = warp_plate(flow_plate(self.sky, t - self.t0), 1.12, 960 + 60 * pv * 0.25, 600 - 20 * pv * 0.25)
        fr = rays(fr, (420, 900), t, strength=0.35, length=0.8, src_r=300)
        fr, _ = put_at(fr, self.sun, t, (0.5, 0.49), (420 + 50 * pv * 0.5, 900), 980 / 1096, wind=0, breathe=0, rot=-24)
        BH = 1050; foot = (1150, 1200)
        ang = -6.0 + 1.5 * u
        a, s = self.blade.fit(BH)
        fr, A = self.blade.draw(fr, t, a, foot, s, rot=ang, grade=NEU, rim=NORIM, wrap=0, shade=None, wind_amp=0, breathe=0)
        # 刀身中线（屏幕）：从刀尖到底部
        ca, sa = math.cos(math.radians(-ang)), math.sin(math.radians(-ang))
        tip = scr_of(self.blade, BH, (0, 0), self.blade.top)
        tx, ty = foot[0] + tip[0] * ca - tip[1] * sa, foot[1] + tip[0] * sa + tip[1] * ca
        def on_blade(k):                                                   # k=0 刀尖 → 1 刀根
            return (tx + (foot[0] - tx) * k, ty + (foot[1] - ty) * k)
        # 日光自下而上扫刃
        sk = 1 - eio(c01(u * 1.15))
        gx, gy = on_blade(0.1 + 0.85 * sk)
        yy, xx = grid()
        g = np.exp(-(((xx - gx) / 26) ** 2 + ((yy - gy) / 70) ** 2)) * A
        fr = fr + g[..., None] * 1.3
        fr = flare(fr, (gx, gy), 0.55, angle=0, length=0.8)
        # 血珠沿刃口下淌（血 字头起）
        q = t - self.tb
        if q > -0.05:
            k = 0.08 + 0.32 * eout(c01((q + 0.05) / 0.85), 2)
            L = np.zeros((H, W), np.float32)
            P0 = on_blade(0.06); P1 = on_blade(k)
            o = np.array([-ca, -sa]) * 22                                    # 刃口一侧
            cv2.line(L, (int(P0[0] + o[0]), int(P0[1] + o[1])), (int(P1[0] + o[0]), int(P1[1] + o[1])), 1.0, 5, cv2.LINE_AA)
            cv2.circle(L, (int(P1[0] + o[0]), int(P1[1] + o[1] + 6)), 9, 1.0, -1, cv2.LINE_AA)
            L = cv2.GaussianBlur(L, (0, 0), 0.8)
            ink = np.clip(cv2.dilate(L, np.ones((5, 5), np.uint8)) - L, 0, 1)
            fr = K.over(fr, ink, INK); fr = K.over(fr, L, RED * 1.1)
        if u > 0.72:                                                        # 刀尖星芒
            gl = c01((u - 0.72) / 0.1) * (1 - c01((u - 0.92) / 0.08))
            st = np.exp(-(np.abs(xx - tx) / 3 + np.abs(yy - ty) / 70)) + np.exp(-(np.abs(yy - ty) / 3 + np.abs(xx - tx) / 110))
            fr = fr + (st * gl * 1.4)[..., None]
        fr = dust(fr, t, 111, n=60, amt=0.4, drift=(50, -20))
        fr = bloom(fr, 0.85, 0.35)
        k = int(round((t - self.t0) * FPS))                                 # 段落入口（接 D 桥段）：1 帧反白 + 2 帧提亮（原金白闪在白纸天上会整屏冲白）
        if k == 0:
            lum = np.clip(fr.mean(-1, keepdims=True), 0, 1); fr = (1.05 - lum) * np.ones(3, np.float32)
        elif k in (1, 2): fr = fr * (1.10 - 0.04 * k) + 0.03
        return fr


# ==================================================================== E02 S112 LS 极低机位扛刀（194.10–195.60）
class E02(Shot):
    """白纸晨空 + 右上血红日（日在头后偏右）+ 极低机位正面扛刀（生图，发丝 / 红带风吹）；「不」「放」两拍：刃口白光自镡扫到刀尖 + 推镜一记；
    前景虚焦白尘大颗粒。分层：天 0.2 / 日 0.45 / 人（锁定）/ 前景尘 1.6。"""
    BLADE = ((0.33, 0.30), (1.0, 0.62))

    def __init__(self):
        self.sky = plate('EA_sky', flip=True)
        self.sun = spr('EA_sun'); self.sp = spr('EA_E02')
        self.hits = [CT(48, 4), CT(48, 5)]                                    # 不 / 放（第 48 句可见字：血未冷刀不放）

    def render(self, t):
        u = self.u(t); pv = u - 0.5
        fr = warp_plate(flow_plate(self.sky, t - self.t0), 1.5, 700 - 40 * pv * 0.2, 330 + 60 * pv * 0.2)
        fr = rays(fr, (1560, 330), t, strength=0.45, length=0.9, src_r=200)
        fr, _ = put_at(fr, self.sun, t, (0.5, 0.49), (1560 - 30 * pv * 0.45, 330 + 40 * pv * 0.45), 560 / 1096, wind=0, breathe=0, rot=58)
        S2 = 1.06; c2 = (980, 520)                                          # 精灵画布宽 2048×1.06 > 画幅，四边都在画外（不露裁切边）
        fr, A = put_at(fr, self.sp, t, (0.5, 0.5), c2, S2, wind=7.0)
        p0 = scr_at(self.sp, (0.5, 0.5), c2, S2, self.BLADE[0]); p1 = scr_at(self.sp, (0.5, 0.5), c2, S2, self.BLADE[1])
        yy, xx = grid()
        for th in self.hits:
            q = t - (th - 0.03)
            if 0 <= q < 0.3:
                k = eout(q / 0.18)
                gx, gy = p0[0] + (p1[0] - p0[0]) * k, p0[1] + (p1[1] - p0[1]) * k
                g = np.exp(-(((xx - gx) / 60) ** 2 + ((yy - gy) / 30) ** 2)) * A * (1 - q / 0.3)
                fr = fr + g[..., None] * 1.6
                fr = flare(fr, (gx, gy), 0.6 * (1 - q / 0.3), angle=24, length=0.7)
        fr = dust(fr, t, 1121, n=26, amt=0.5, drift=(-40, -50), size=(4, 11))
        z = 1.0 + 0.02 * sum(pulse(t, th, 0.12) for th in self.hits)
        return bloom(K.cam(fr, z), 0.85, 0.3)


# ==================================================================== E03 S113 ELS 碑林推轨（195.60–197.20）
class E03(Shot):
    """碑林一点透视（生图，碑面全空、无字）：伪 3D 推轨（近碑比远碑放大得快）+ 尽头门洞白光体积光 + 两层白雾向外漂 + 白尘。"""
    VP = (956, 700)

    def __init__(self):
        self.img = plate('EA_E03')
        im = self.img
        sky = ((im[..., 0] - im[..., 1] > 0.35) | (im.mean(-1) < 0.30)) & (im.mean(-1) < 0.55)    # 血红天 + 天里的墨云；碑身 / 地面（灰白）不动
        yy = grid()[0]
        self.skym = (sky & (yy < 560)).astype(np.float32)

    def render(self, t):
        u = self.u(t)
        e = eio(u)
        img = flow_region(self.img, t - self.t0, 'E03sky', self.skym, seed=31, amp=5.0, drift=(0.0, 4.0))   # §12.2：天上的云往门洞方向流
        fr = dolly(img, self.VP, 1.0 + 0.10 * e, 0.38 * e)
        fr = rays(fr, (self.VP[0], self.VP[1] - 10), t, strength=0.5, length=1.0, src_r=90)
        fr = fog(fr, t, 1131, amt=0.32, speed=(26, 0), y0=0.62, y1=1.0)
        fr = fog(fr, t + 3.1, 1132, amt=0.22, speed=(-34, 0), y0=0.5, y1=0.9)
        fr = dust(fr, t, 113, n=70, amt=0.35, drift=(10, 6))
        return bloom(fr, 0.86, 0.3)


# ==================================================================== E04 S114 CU 暗殿「天理昭彰」匾（197.20–198.37）
PLAQUE_COLS = ((0.14, 0.345), (0.345, 0.515), (0.515, 0.695), (0.695, 0.87))


def plaque_masks(sp):
    """匾上四个字的笔画蒙版（精灵源坐标）：白、低饱和、在字带内。"""
    F, A = sp.F, sp.A
    lum = F.mean(-1); sat = F.max(-1) - F.min(-1)
    strokes = ((lum > 0.55) & (sat < 0.2) & (A > 0.8)).astype(np.float32)
    h, w = A.shape
    ms = []
    for (x0, x1) in PLAQUE_COLS:
        m = np.zeros_like(strokes); m[int(0.28 * h):int(0.74 * h), int(x0 * w):int(x1 * w)] = 1
        m = cv2.dilate(strokes * m, np.ones((5, 5), np.uint8))
        ms.append(cv2.GaussianBlur(m, (0, 0), 1.2))
    return ms


def lit_plaque(sp, lit, flash):
    """按点亮进度返回一张临时精灵：未点亮的字压暗成「刻着、没有光」，点亮瞬间白闪。lit/flash 各 4 个 0..1。"""
    if not hasattr(sp, '_r8_masks'): sp._r8_masks = plaque_masks(sp); sp._r8_F0 = sp.F
    key = tuple(round(v, 3) for v in lit) + tuple(round(v, 3) for v in flash)
    if getattr(sp, '_r8_key', None) == key: return sp
    F = sp._r8_F0.copy()
    for m, l, f in zip(sp._r8_masks, lit, flash):
        k = (0.78 * (1 - l))
        F = F * (1 - (m * k)[..., None]) + (m * k)[..., None] * 0.06
        if f > 0: F = F + (m * f * 0.6)[..., None]
    sp.F = np.ascontiguousarray(F, np.float32); sp._r8_key = key
    return sp


def plaque_glow(fr, A_scr, lit_amt):
    return fr + K.blur_ds(A_scr, 18)[..., None] * 0.25 * lit_amt


class E04(Shot):
    """暗殿（生图，左上高窗两道白光）+ 「天理昭彰」匾（生图，字是画进去的）：唱到「天」「理」逐字点亮（压暗 → 原图白字 + 白闪 + 光晕），
    匾面一道白光自左扫过；光柱里白尘。分层：殿 0.3 / 匾（锁定，推近 expo_in）/ 前景尘。"""
    def __init__(self):
        self.bg = plate('EA_E04bg')
        self.pl = sub_layer(spr('EA_plaque'), 1.0)
        self.lit_t = [CT(49, 8), CT(49, 9), CT(49, 10), CT(49, 11)]

    def lit(self, t):
        return [c01((t - (x - 0.06)) / 0.12) for x in self.lit_t], [pulse(t, x, 0.12) if t >= x - 0.06 else 0 for x in self.lit_t]

    def render(self, t):
        u = self.u(t); pv = u - 0.5
        fr = warp_plate(self.bg, 1.08, 960 + 30 * pv * 0.3, 560)
        fr = shadow_gray(fr, floor=0.43, dk=0.40)                           # §10.1 暗殿暗部抬到网点灰
        lit, fl = self.lit(t)
        sp = lit_plaque(self.pl, lit, fl)
        fr, A = put_at(fr, sp, t, (0.5, 0.49), (960, 470), 1320 / 2048 / 0.945, wind=0, breathe=0)
        fr = plaque_glow(fr, A, sum(lit) / 4)
        sx = -400 + 2800 * eio(u)                                           # 匾面扫光
        yy, xx = grid()
        sw = np.exp(-(((xx - sx) + (yy - 470) * 0.5) / 90) ** 2) * A
        fr = fr + sw[..., None] * 0.35
        fr = dust(fr, t, 114, n=110, amt=0.4, drift=(12, 8))
        return bloom(fr, 0.85, 0.35)


# ==================================================================== E05 S114b ECU 低角荷兰角：昭、彰亮起即开裂（198.37–199.30）
class E05(Shot):
    """同一块匾（生图）大特写、-9° 荷兰角：「昭」「彰」随唱点亮，点亮即沿字缝裂开——墨线裂缝 + 白热芯 + 血红溢光，
    白光从缝里喷出、墨线勾边碎片剥落。分层：殿（虚化）/ 匾（锁定）/ 裂缝光 / 碎片（三层景深）。"""
    def __init__(self):
        self.bg = plate('EA_E04bg', blur=6, gain=0.55)
        self.pl = sub_layer(spr('EA_plaque'), 1.0)
        self.ta, self.tb = CT(49, 10), CT(49, 11)
        self.chips = Chips(1141, n=36, size=(10, 34), spread=(700, 300), zr=(0.5, 2.2), tones=(0.92, 0.45, 0.05))
        self.chips2 = Chips(1142, n=18, size=(18, 50), spread=(600, 260), zr=(0.4, 1.0), tones=(0.9, 0.06))
        self.cr1 = K.crack_path((1080, 160), (1180, 980), 51, n=36, jag=0.06)
        self.cr2 = K.crack_path((1520, 120), (1400, 990), 52, n=36, jag=0.07)

    def render(self, t):
        u = self.u(t)
        fr = self.bg.copy()
        lit = [1.0, 1.0, c01((t - (self.ta - 0.06)) / 0.12), c01((t - (self.tb - 0.06)) / 0.12)]
        fl = [0, 0, pulse(t, self.ta, 0.12), pulse(t, self.tb, 0.12)]
        sp = lit_plaque(self.pl, lit, fl)
        fr, A = put_at(fr, sp, t, (0.62, 0.50), (1150 - 60 * u, 560), 2.05 * 0.66, wind=0, breathe=0, rot=-9)
        fr = plaque_glow(fr, A, 0.6)
        for tc, cr, w in ((self.ta, self.cr1, 4), (self.tb, self.cr2, 6)):
            q = t - tc
            if q < 0: continue
            m = K.draw_crack((H, W), cr, w, branches=8, seed=int(tc * 7), prog=eout(q / 0.12))
            core = cv2.GaussianBlur(m, (0, 0), 0.8)
            glow = K.blur_ds(m, 16)
            fr = fr * (1 - np.clip(cv2.dilate(m, np.ones((7, 7), np.uint8)) * 0.9, 0, 1))[..., None]
            fr = fr + core[..., None] * 1.6 + glow[..., None] * RED * 1.4 * (0.6 + 0.8 * math.exp(-q / 0.2))
        if t > self.tb:
            q = t - self.tb
            fr = flare(fr, (1400, 470), 1.1 * math.exp(-q / 0.25), angle=-9, length=1.3)
            fr = sparks2(fr, t, 1144, (1420, 480), t0=self.tb, n=60, dirc=(0.3, -1), spread=1.5, speed=(500, 1300))
            fr = self.chips.draw(fr, q * 1.4, c=(1400, 520), to_cam=0.8, zf=1.2)
            fr = self.chips2.draw(fr, q * 1.8, c=(1350, 560), to_cam=0.5, zf=0.35)
        elif t > self.ta:
            fr = self.chips.draw(fr, (t - self.ta) * 0.8, c=(1150, 540), to_cam=0.3, zf=1.2, alpha=0.6)
        return bloom(fr, 0.85, 0.35)


# ==================================================================== E06 S115 MS 律令挂轴林推轨（199.30–200.67）
class E06(Shot):
    """挂轴林（生图，轴面全空、背光透纸）：挂轴整体绕挂点微摆（位移随离挂点距离增大）+ 伪 3D 推轨穿帘 +
    前景代码白纸挂轴（墨线边、强虚化）从两侧擦过镜头。分层：挂轴林（径向分层）/ 前景近轴 ×3。"""
    VP = (900, 450)

    def __init__(self):
        self.img = plate('EA_E06')
        yy, xx = grid()
        self.yy, self.xx = yy, xx
        self.near = [(-260, 320, 0.0), (1880, 360, 1.7), (2300, 300, 3.1)]

    def sway(self, img, t):
        yy, xx = self.yy, self.xx
        dx = (np.sin(xx / 210 + t * 1.6) * 0.6 + np.sin(xx / 77 - t * 2.3) * 0.4) * 7 * np.clip((yy - 40) / 900, 0, 1)
        return cv2.remap(img, xx - dx, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def near_scrolls(self, fr, t, u):
        L = np.zeros((H // 4, W // 4), np.float32); E = np.zeros_like(L)
        for (x, w, ph) in self.near:
            cx = (x - 900 * eio(u) * (1 if x > 960 else -0.6)) / 4
            sw = 6 * math.sin(t * 1.2 + ph)
            pts = np.array([[cx - w / 8, -10], [cx + w / 8, -10], [cx + w / 8 + sw, H / 4 + 10], [cx - w / 8 + sw, H / 4 + 10]], np.int32)
            cv2.fillConvexPoly(L, pts, 1.0, cv2.LINE_AA); cv2.polylines(E, [pts], True, 1.0, 2, cv2.LINE_AA)
        L = cv2.resize(cv2.GaussianBlur(L, (0, 0), 0.5), (W, H)); E = cv2.resize(cv2.GaussianBlur(E, (0, 0), 0.4), (W, H))
        fr = fr * (1 - L[..., None] * 0.92) + L[..., None] * 0.88
        return fr * (1 - E[..., None] * 0.6)

    def render(self, t):
        u = self.u(t)
        fr = self.sway(self.img, t)
        fr = dolly(fr, self.VP, 1.0 + 0.06 * eio(u), 0.35 * eio(u))
        fr = rays(fr, self.VP, t, strength=0.3, length=0.8, src_r=120)
        fr = self.near_scrolls(fr, t, u)
        return bloom(fr, 0.86, 0.3)


# ==================================================================== E07 S116 LS 太上皇 → 纸扎揭示（200.67–202.03）
def side_strips(fr, t, dx, seed=0):
    """前景挂轴（代码：白纸、墨线边、上沿木轴），只在画面两侧，强虚化。"""
    L = np.zeros((H // 4, W // 4), np.float32); E = np.zeros_like(L)
    for (x, w) in ((60, 300), (1880, 340), (-180, 260), (2150, 300)):
        cx = (x + dx * (1 if x > 960 else -1)) / 4
        sw = 5 * math.sin(t * 1.1 + x)
        pts = np.array([[cx - w / 8, -10], [cx + w / 8, -10], [cx + w / 8 + sw, H / 4 + 10], [cx - w / 8 + sw, H / 4 + 10]], np.int32)
        cv2.fillConvexPoly(L, pts, 1.0, cv2.LINE_AA); cv2.polylines(E, [pts], True, 1.0, 2, cv2.LINE_AA)
    L = cv2.resize(cv2.GaussianBlur(L, (0, 0), 0.5), (W, H)); E = cv2.resize(cv2.GaussianBlur(E, (0, 0), 0.4), (W, H))
    fr = fr * (1 - L[..., None] * 0.95) + L[..., None] * 0.86
    return fr * (1 - E[..., None] * 0.7)


class E07(Shot):
    """挂轴缝后（E06 同一张背景板，压暗虚化）站着太上皇本人（生图，定妆照参考，黑纱长袍 + 血红腰带）→ 201.2 一道纸面反光斜扫，
    光带过处换成同一姿势的纸扎（生图）。环绕感：人物与背景反向视差、前景两侧挂轴大视差擦过。"""
    def __init__(self):
        self.bg = plate('EA_E06', flip=True, blur=7, gain=0.55)
        self.emp = spr('EA_emperor'); self.eff = spr('EA_effigy')
        self.tr = 201.2

    def render(self, t):
        u = self.u(t); pv = u - 0.5
        fr = warp_plate(self.bg, 1.06, 960 + 50 * pv, 540)
        fr = rays(fr, (1480, 300), t, strength=0.3, length=0.8, src_r=140)
        rv = eio((t - self.tr) / 0.4)
        foot = (960 - 70 * pv, 990)
        fr0 = fr1 = None
        if rv < 1: fr0, _ = put(fr.copy(), self.emp, t, 860, foot, wind=5.0)
        if rv > 0: fr1, _ = put(fr.copy(), self.eff, t, 860, foot, wind=6.0)
        if rv >= 1: fr = fr1
        elif rv <= 0: fr = fr0
        else:
            yy, xx = grid(); sx = xx - (300 + 1400 * rv) + (yy - 540) * 0.4
            m = sstep(8, -8, sx)[..., None]
            fr = fr1 * m + fr0 * (1 - m)
            fr = fr + np.exp(-(sx / 46) ** 2)[..., None] * 0.8
        fr = side_strips(fr, t, 180 * pv * 2)
        fr = dust(fr, t, 116, n=40, amt=0.3)
        return bloom(fr, 0.86, 0.3)


# ==================================================================== E08 S117 CU 纸扎巨脸自眉心烧穿（202.03–203.40）
def burn_edge(fr, void, F, t, seed=719):
    """风格 D 烧洞边：外圈焦黑（纤维毛边）→ 断续血红火线（白热芯）→ 内圈卷起炭边；洞内 void。F<0 洞内。"""
    lo, mid, hi, hair, brk = R7.hole_noise(seed)
    wsc = 26 + 18 * (mid * 2)
    sc = np.clip(1 - F / np.maximum(wsc, 6), 0, 1) * (F > 0)
    sc = np.clip(sc * 1.6, 0, 1) ** 0.7
    fuzz = np.clip((wsc + 14 - F) / 14, 0, 1) * (F > wsc * 0.6) * hair * 0.85
    S = np.clip(sc + fuzz * 0.6, 0, 1)
    fr = fr * (1 - 0.92 * S[..., None]) + S[..., None] * 0.03
    hole = np.clip(-F / 1.5, 0, 1)[..., None]
    fr = fr * (1 - hole) + void * hole
    wcar = 12 + 10 * np.clip(lo * 2 + 0.5, 0, 1)
    car = np.clip((1 + F / wcar) * 4, 0, 1) * (F < 0)
    fr = fr * (1 - car[..., None]) + car[..., None] * (0.04 + 0.1 * np.abs(hi))[..., None]
    lip = np.exp(-((F + wcar) / 2.0) ** 2) * (0.4 + 0.6 * np.clip(brk * 2 + 0.6, 0, 1))
    fr = fr + lip[..., None] * 0.35
    flick = 0.5 + 0.5 * np.sin(t * 13 + mid * 30)
    on = np.clip((brk + 0.03 + 0.06 * flick) * 5, 0, 1)
    thick = 1.5 + 4.0 * np.clip(mid * 2 + 0.5, 0, 1)
    line = np.exp(-((F + 1.5) / thick) ** 2) * on
    core = np.exp(-((F + 1.5) / (thick * 0.4)) ** 2) * on
    fr = fr + line[..., None] * RED * 1.5 + core[..., None] * 1.0 + K.blur_ds(line, 8)[..., None] * RED * 0.8
    return fr


class E08(Shot):
    """纸扎太上皇巨脸（生图：宣纸皱褶、竹骨、接缝，与 E07 同一张脸）；「伪」字头火从眉心烧出横向不规则洞
    （焦黑毛边 / 断续血红火线 / 卷边炭化），洞内近黑，只露被血红火光从下照亮的鬼屠双眼（E19 同一张生图裁眼）。飞灰白→灰上飘。"""
    CX, CY = 970, 486
    RX, RY = 330, 175

    def __init__(self):
        self.img = plate('EA_E08')
        self.eyes = spr('EA_E19')
        yy, xx = grid()
        lo, mid, hi, hair, brk = R7.hole_noise(719)
        self.D = (np.hypot(xx - self.CX, (yy - self.CY) * self.RX / self.RY) + lo * 150 + mid * 46 + hi * 6).astype(np.float32)
        self.t_in = CT(50, 6)
        em = np.zeros((H, W), np.float32)
        for ex in (self.CX - 120, self.CX + 120):
            em = np.maximum(em, np.exp(-(((xx - ex) / 110) ** 2 + ((yy - (self.CY + 4)) / 52) ** 2) ** 1.4))
        self.eyem = em
        self.void = np.full((H, W, 3), 0.012, np.float32)

    def radius(self, t):
        q = t - (self.t_in + 0.03)
        if q < 0: return -1.0
        return self.RX * (1 - math.exp(-q / 0.30)) ** 0.9 * (0.12 + 0.88 * c01(q / 0.08))

    def render(self, t):
        u = self.u(t)
        fr = warp_plate(self.img, 1.0 + 0.02 * u, 960, 540 - 8 * u)
        fr = shadow_gray(fr, floor=0.34, dk=0.40)                           # §10.1 纸面暗部抬到网点灰（烧洞黑保留）
        R = self.radius(t)
        if R >= 0:
            F = self.D - R
            v, _ = put_at(self.void.copy(), self.eyes, t, (0.5315, 0.378), (self.CX, self.CY + 2 - 4 * u), 240 / 358, wind=0, breathe=0)
            yy, xx = grid()
            under = np.clip((yy - (self.CY - 50)) / 90, 0.3, 1.0)
            keep = self.eyem * np.clip((-F - 36) / 22, 0, 1) * under
            v = self.void + (v * np.array([1.25, 0.9, 0.9], np.float32) - self.void) * keep[..., None] * 1.6
            v = v + (keep * under * 0.25)[..., None] * RED
            fr = burn_edge(fr, v, F, t)
            fr = self.ash(fr, t, F)
        return bloom(fr, 0.88, 0.3)

    def ash(self, fr, t, F):
        ys, xs = np.nonzero(np.abs(F[::4, ::4]) < 2.5)
        if len(xs) == 0: return fr
        P = np.zeros((H, W), np.float32); G = np.zeros((H, W), np.float32)
        r = np.random.default_rng(int(t * 30) * 7 + 3)
        for j in r.choice(len(xs), min(110, len(xs)), replace=False):
            age = r.uniform(0, 0.5)
            x = xs[j] * 4 + 30 * age + 10 * math.sin(j + t * 3); y = ys[j] * 4 - (80 + 160 * r.random()) * age
            cv2.circle(P if age < 0.2 else G, (int(x), int(y)), int(1 + 1.6 * r.random() * (0.5 + age)), float(1 - age / 0.5), -1, cv2.LINE_AA)
        return fr + cv2.GaussianBlur(P, (0, 0), 0.8)[..., None] * np.array([1.2, 0.5, 0.45], np.float32) + cv2.GaussianBlur(G, (0, 0), 1.2)[..., None] * 0.22


# ==================================================================== E09 S118 MS 交叉斩：挂轴沿刀线断开（203.40–204.33）
class E09(Shot):
    """挂轴林（E06 同一背景板）+ 斩击全身（生图，动作收势、剑身低垂向右下，无自带刀弧）：「撕」字头前主角在起势（旋转 +8°、动态模糊），
    字头硬切到斩完姿势 + 一帧反白冲击 + 干笔飞白斩痕贯穿全画面 + 背景挂轴沿刀线断开下坠（断口血红）+ 火星 + 震屏。"""
    P0, P1 = (180.0, 230.0), (1760.0, 900.0)

    def __init__(self):
        self.bg = plate('EA_E06', blur=1.5, gain=1.05)
        # 11-12 重抽：动作收势姿势，生图不带刀弧（不再需要把红斑抹成灰，红带/红袖保留原色）；
        # 刀光完全由代码画在精灵之上。
        self.sp = spr('EA_E09b')
        self.ts = CT(51, 2)

    def render(self, t):
        u = self.u(t)
        q = t - self.ts
        C = self.bg.copy()
        if q >= 0:
            A = np.ones((H, W), np.float32)
            C2, A2, em = R3.cut_layer(C, A, self.P0, self.P1, q, fall=1.0, side=-1)
            fr = C2 * A2[..., None] + 0.03 * (1 - A2[..., None])
            fr = fr + (em * 1.4 + K.blur_ds(em, 8) * 1.4)[..., None] * RED
        else:
            fr = C
        foot = (930 - 30 * u, 1000)
        if q < 0:
            k = c01((t - self.t0) / max(1e-3, self.ts - self.t0))
            fr, A = put(fr, self.sp, t, 920, (foot[0] + 40 * (1 - k), foot[1]), wind=8.0, rot=8 * (1 - k), mblur=(40 * (1 - k), -25 * (1 - k)))
        else:
            fr, A = put(fr, self.sp, t, 920, foot, wind=8.0)
        if -0.04 <= q < 0.4:
            fr = ink_slash(fr, self.P0, self.P1, eout((q + 0.04) / 0.08), 1 - c01((q - 0.12) / 0.28), width=60, seed=91)
        # 刀光（代码画）：斩后 0.1s 起沿一道下压的弧抡出，0.5s 内渐隐；干笔白芯 + 血红外沿，压在精灵之上
        if 0.02 <= q < 0.62:
            e = eout(c01((q - 0.02) / 0.10)); fade = 1 - c01((q - 0.18) / 0.44)
            f = K.blur_ds(np.zeros((H // 2, W // 2), np.float32), 1)
            pts = [(300 + 1330 * (k / 22), 520 + 300 * math.sin(math.pi * (k / 22)) - 90 * (k / 22)) for k in range(23)]
            n = int(e * 22)
            for k in range(max(0, n - 1)):
                q0, q1 = pts[k], pts[k + 1]
                for j, (off, wd, gain) in enumerate(((-9, 2, 0.55), (-4, 3, 1.0), (3, 2, 0.75), (9, 1, 0.35))):
                    aa = (q0[0], q0[1] + off); bb = (q1[0], q1[1] + off * 1.2)
                    cv2.line(f, (int(aa[0] / 2), int(aa[1] / 2)), (int(bb[0] / 2), int(bb[1] / 2)), gain, wd, cv2.LINE_AA)
            Lw = cv2.resize(cv2.GaussianBlur(f, (0, 0), 0.8), (W, H)) * fade
            Lr = cv2.resize(cv2.GaussianBlur(cv2.dilate(f, np.ones((5, 5), np.uint8)), (0, 0), 2.6), (W, H)) * fade
            fr = fr * (1 - np.clip(Lr * 0.8, 0, 1))[..., None] + np.clip(Lr, 0, 1)[..., None] * RED * 1.15
            fr = fr + np.clip(Lw, 0, 1)[..., None] * 1.25
        if q >= 0:
            fr = sparks2(fr, t, 1181, (960, 560), t0=self.ts, n=60, dirc=(0.4, -1), spread=1.4)
        nf = int(round(q * FPS))
        if nf == 0:                                                         # 反白冲击帧（只 1 帧，按帧号判断，避免浮点误差拖成 2 帧）
            lum = fr.mean(-1, keepdims=True); fr = np.clip(1.08 - lum, 0, 1) * np.ones(3, np.float32)
        elif nf in (1, 2): fr = fr * 1.12 + 0.05
        return bloom(fr, 0.85, 0.35)


# ==================================================================== E10 S119 碎纸慢放扑面（204.33–205.23）
class Shred:
    def __init__(self, crop, A):
        self.C, self.A = crop, A


class E10(Shot):
    """被斩碎的律令纸（生图碎纸，按连通域拆成单片，每片一层）：0.45× 慢放朝镜头扑来，3D 翻转（横向压缩 = 翻面）、自转，
    按深度虚化（前景大片强虚化擦镜）；远景挂轴林（同一背景板）压暗虚化；白 / 血红余烬。"""
    def __init__(self):
        self.bg = plate('EA_E06', blur=10, gain=0.38)
        im = cv2.imread(GEN + 'EA_shreds_cut.png', cv2.IMREAD_UNCHANGED)
        im = cv2.resize(im, (1024, 576), interpolation=cv2.INTER_AREA)
        C = im[..., 2::-1].astype(np.float32) / 255; A = im[..., 3].astype(np.float32) / 255
        n, lab, st, _ = cv2.connectedComponentsWithStats((A > 0.3).astype(np.uint8), 8)
        self.pieces = []
        for i in range(1, n):
            x, y, w, h, a = st[i]
            if a < 400: continue
            m = (lab[y:y + h, x:x + w] == i).astype(np.float32)
            m = cv2.GaussianBlur(cv2.dilate(m, np.ones((3, 3), np.uint8)), (0, 0), 0.8) * A[y:y + h, x:x + w]
            self.pieces.append(Shred(C[y:y + h, x:x + w].copy(), m))
        r = np.random.default_rng(1190)
        self.P = []
        for k in range(80):
            self.P.append(dict(i=int(r.integers(0, len(self.pieces))), x=r.uniform(-1, 1) * 900, y=r.uniform(-0.9, 0.9) * 480,
                               z=r.uniform(0.9, 4.6), rot=r.uniform(0, 360), w=r.normal(0, 40), fl=r.uniform(0, 6.3), fw=r.uniform(1.5, 4.0),
                               s=r.uniform(0.5, 1.1), vx=r.normal(0, 60), vy=r.normal(-30, 40)))

    def render(self, t):
        q = (t - self.t0) * 0.45 + 0.4                                       # 慢放
        fr = self.bg.copy()
        fr = rays(fr, (960, 380), t, strength=0.25, length=0.8, src_r=200)
        for p in sorted(self.P, key=lambda p: -(p['z'] - 1.2 * q)):
            z = p['z'] - 1.2 * q
            if z < 0.22: continue
            pc = self.pieces[p['i']]
            sc = p['s'] / z * 0.9
            cx = 960 + (p['x'] + p['vx'] * q) / z; cy = 540 + (p['y'] + p['vy'] * q) / z
            h0, w0 = pc.A.shape
            if not (-w0 * sc < cx < W + w0 * sc and -h0 * sc < cy < H + h0 * sc): continue
            ang = math.radians(p['rot'] + p['w'] * q); fx = math.cos(p['fl'] + p['fw'] * q)
            ca, sa = math.cos(ang), math.sin(ang)
            Mt = np.float32([[sc * fx * ca, -sc * sa, 0], [sc * fx * sa, sc * ca, 0]])
            Mt[:, 2] = np.array([cx, cy], np.float32) - Mt[:, :2] @ np.array([w0 / 2, h0 / 2], np.float32)
            ext = int(max(w0, h0) * sc * 0.75) + 20
            x0, y0 = int(max(0, cx - ext)), int(max(0, cy - ext)); x1, y1 = int(min(W, cx + ext)), int(min(H, cy + ext))
            if x1 <= x0 or y1 <= y0: continue
            Mt[:, 2] -= [x0, y0]
            Cw = cv2.warpAffine(pc.C, Mt, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
            Aw = cv2.warpAffine(pc.A, Mt, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
            shade = 0.55 + 0.45 * abs(fx)
            blur = min(0.9, abs(z - 1.3) * 0.4)
            if blur > 0.7: Cw = cv2.GaussianBlur(Cw, (0, 0), blur); Aw = cv2.GaussianBlur(Aw, (0, 0), blur)
            roi = fr[y0:y1, x0:x1]
            fr[y0:y1, x0:x1] = roi * (1 - Aw[..., None]) + Cw * shade * Aw[..., None]
        fr = embers(fr, t, 1191, n=50, amt=0.6, rise=60)
        return bloom(fr, 0.85, 0.35)


# ==================================================================== E11 S120a 低机位 MS 刀插大地（205.23–206.07）
class E11(Shot):
    """白纸晨空（墨云）+ 前景焦土山脊（生图）+ 双手拄刀插地（生图）；入镜即插地：贴地尘环（灰白 + 墨点）、刀尖处墨线裂纹向外爬（缝里血红）、
    火星白 / 血红、震屏（SHAKE 表）。分层：天 0.25 / 山脊 0.6 / 人（锁定）/ 前景尘。"""
    def __init__(self):
        self.sky = plate('EA_sky')
        self.ridge = spr('EA_ridge'); self.sp = spr('EA_E11')
        self.cr = [K.crack_path((1000, 990), (1000 + 520 * math.cos(a), 990 + 90 * math.sin(a)), 60 + i, n=22, jag=0.12)
                   for i, a in enumerate((0.15, 2.9, 0.6, 2.4))]

    def render(self, t):
        u = self.u(t); pv = u - 0.5; q = t - self.t0
        fr = warp_plate(flow_plate(self.sky, t - self.t0), 1.35, 1300 + 40 * pv * 0.25, 450)
        fr, _ = put_at(fr, self.ridge, t, (0.5, 0.75), (960 + 40 * pv * 0.6, 790), W * 1.1 / 2048, wind=0, breathe=0)
        foot = (1000, 1000)
        fr = contact(fr, foot, 300, amt=0.6, dirx=-1.0, length=520)                  # 日在右上：影子拖向左
        fr, A = put(fr, self.sp, t, 820, foot, wind=7.0)
        for i, cr in enumerate(self.cr):
            m = K.draw_crack((H, W), cr, 3, branches=4, seed=70 + i, prog=eout(q / 0.35))
            fr = fr * (1 - np.clip(m, 0, 1))[..., None] + K.blur_ds(m, 6)[..., None] * RED * 0.9 * math.exp(-q / 0.6)
        fr = ink_ring(fr, foot, 60 + 900 * eout(q / 0.7), 1 - c01(q / 0.8))
        fr = sparks2(fr, t, 1202, foot, t0=self.t0, n=60, dirc=(0, -1), spread=1.3, speed=(400, 1100))
        fr = dust(fr, t, 1203, n=50, amt=0.4, drift=(80, -20))
        return bloom(fr, 0.85, 0.3)


# ==================================================================== E12 S120b ELS 正俯拍「鬼屠」印（206.07–207.27）
class E12(Shot):
    """用户点名：「鬼屠」保留；修人物抠图不完整；字上的剑改成生图。
    焦土俯拍（生图）+ 「鬼屠」朱印与印心插刀同一张生图（剑不再是代码画的）+ 主角俯视全身（完整绿幕抠像，单独一层，站在印外不压字）。
    「章」字头印落地：印从 1.18 倍压下、墨色由斑驳到实（按噪声阈值渐显）、尘环 + 震屏；人物晨光长影拖向左下，发丝 / 红带风吹。
    摇臂升（MOVE expo_out 1.28→1.0）。"""
    SEAL = (820, 520)

    def __init__(self):
        g = plate('EA_topground'); lum = g.mean(-1, keepdims=True)
        self.g = np.ascontiguousarray(lum + (g - lum) * 0.3, np.float32)                 # 地缝红降到 30%，红留给印
        self.seal = sub_layer(spr('EA_E12'), 1.0); self.man = spr('EA_E12man')     # 私有副本：揭印改 alpha 不污染进程级缓存
        self.ts = CT(51, 9) + 0.03
        nz = cv2.resize(K.fbm(self.seal.h // 8, self.seal.w // 8, 1214, base=6, octaves=4), (self.seal.w, self.seal.h))
        self.nz = ((nz - nz.min()) / (np.ptp(nz) + 1e-6)).astype(np.float32)
        self.A0 = self.seal.A
        self._k = None

    def seal_at(self, p):
        k = round(p, 2)
        if self._k != k:
            m = np.clip((p * 1.25 - self.nz) * 6, 0, 1)
            self.seal.A = np.ascontiguousarray(self.A0 * m, np.float32); self._k = k
        return self.seal

    def render(self, t):
        u = self.u(t)
        fr = warp_plate(self.g, 1.05, 960, 540)
        yy, xx = grid()
        fr = fr * (0.72 + 0.4 * np.exp(-((xx - 1300) ** 2 + (yy - 200) ** 2) / (2 * 800 ** 2)))[..., None]
        q = t - self.ts
        if q > -0.12:
            e = eout(c01((q + 0.12) / 0.12), 2)
            p = c01((q + 0.04) / 0.30) if q > -0.04 else 0.0
            sp = self.seal_at(max(p, 0.2 * e))
            sc = 1.18 - 0.18 * e
            fr, Asl = put_at(fr, sp, t, (0.5, 0.497), self.SEAL, 720 / (0.579 * 2048) * sc, wind=0, breathe=0, rot=-4)
            if q < 0: fr = fr * (1 - 0.35 * K.blur_ds(Asl, 20)[..., None] * (1 - e))
        foot = (1420, 790)
        a, s = self.man.fit(430)
        _, Am = self.man.draw(np.zeros((H, W, 3), np.float32), t, a, foot, s, grade=NEU, rim=NORIM, wrap=0, shade=None, wind_amp=_wind(6.0), breathe=0)
        Sh = np.zeros_like(Am)
        for k in range(1, 10):
            Mt = np.float32([[1, 0, -30 * k], [0, 1, 22 * k]]); Sh = np.maximum(Sh, cv2.warpAffine(Am, Mt, (W, H)) * (1 - 0.07 * k))
        fr = fr * (1 - 0.55 * K.blur_ds(Sh, 5)[..., None])
        fr = fr * (1 - 0.4 * K.blur_ds(cv2.dilate(Am, np.ones((9, 9), np.uint8)), 8)[..., None])
        fr, _ = put(fr, self.man, t, 430, foot, wind=6.0, breathe=0)
        if q > 0:
            fr = ink_ring(fr, self.SEAL, 380 + 650 * eout(q / 0.7), 1 - c01(q / 0.8), squash=1.0, seed=1215)
            fr = dust(fr, t, 1213, n=50, amt=0.45 * (1 - c01(q / 0.8)), drift=(40, 30), size=(2, 5))
        return fr


# ==================================================================== E13 S121 MCU 晨风马尾红带（207.27–208.77）
class E13(Shot):
    """白纸晨空虚焦 + 背后血红日（虚化大圆，偏右）+ 侧身迎风（生图：马尾、发丝、红带大幅飘，风吹网格做二级运动）；余烬白 / 血红斜飘。
    分层：天（虚化）0.2 / 日 0.4 / 人（锁定）/ 余烬。"""
    def __init__(self):
        self.sky = plate('EA_sky', blur=9)
        self.sun = spr('EA_sun'); self.sp = spr('EA_E13')

    def render(self, t):
        u = self.u(t); pv = u - 0.5
        fr = warp_plate(flow_plate(self.sky, t - self.t0), 1.7, 520 - 40 * pv * 0.2, 360)
        fr = rays(fr, (1250, 430), t, strength=0.25, length=0.7, src_r=380)
        fr, _ = put_at(fr, self.sun, t, (0.5, 0.49), (1250 + 60 * pv * 0.4, 430), 900 / 1096, wind=0, breathe=0, rot=131)
        fr, _ = put(fr, self.sp, t, 1300, (900 + 30 * u, 1240), wind=12.0, breathe=0.006)      # 画布左缘（发丝）与上下缘都在画外
        fr = embers(fr, t, 1213, n=50, amt=0.7)
        return bloom(fr, 0.86, 0.3)


# ==================================================================== E14T S122 LS 迎镜走来（208.77–209.83）
class E14T(Shot):
    """白纸晨空 + 焦土山脊 + 远处一块「天理」木律令牌（生图，字保留，立在他身后左侧，下一镜被一刀斩断）+ 灰白烟幕横移 +
    低机位迎镜走来（生图，步伐上下起伏 + 渐近放大 + 风吹）+ 前景碎纸强虚化擦镜（生图碎纸）+ 余烬。"""
    def __init__(self):
        self.sky = plate('EA_sky', flip=True)
        self.ridge = spr('EA_ridge'); self.tab = spr('EA_tablet'); self.sp = spr('EA_E14')
        self.fg = comp_pick(spr('EA_shreds'), 0.6, 0.45, 1.0, 1.0)          # 只取右下几片整片碎纸做前景（按连通域，不切片）
        self.tab = ground_fade(self.tab)

    def render(self, t):
        u = self.u(t); pv = u - 0.5
        fr = warp_plate(flow_plate(self.sky, t - self.t0), 1.25, 1200 + 50 * pv * 0.2, 600, rot=-2)
        fr, _ = put_at(fr, self.ridge, t, (0.5, 0.75), (960 + 50 * pv * 0.5, 740), W * 1.12 / 2048, wind=0, breathe=0)
        fr, _ = put(fr, self.tab, t, 420, (560 + 50 * pv * 0.7, 870), wind=0, breathe=0)
        fr = ink_ring(fr, (560 + 50 * pv * 0.7, 868), 46, 0.8, squash=4.0, seed=1225)      # 桩脚土
        fr = fog(fr, t, 1224, amt=0.2, speed=(-40, 0), y0=0.62, y1=0.95, col=(0.85, 0.85, 0.85))
        bob = 6 * abs(math.sin(t * 5.5))
        fr = contact(fr, (1120, 1075 + 30 * u), 260, amt=0.5 * (1 - 0.4 * bob / 6))   # 抬步时影子变淡
        fr, _ = put(fr, self.sp, t, 960 * (1 + 0.06 * u), (1120, 1075 - bob + 30 * u), wind=9.0, breathe=0)   # 画布上沿（马尾顶）在上黑边里
        fr, _ = put_at(fr, self.fg, t, (0.8, 0.7), (1700 + 160 * u, 900), 1.2, wind=0, breathe=0, alpha=0.9)
        fr = embers(fr, t, 1223, n=60, amt=0.7)
        return bloom(fr, 0.86, 0.3)


# ==================================================================== E15 S122b ECU 刀尖拖地火线、斩断「天理」木牌（209.83–210.33）
class E15(Shot):
    """贴地透视的焦土（俯拍底板压成地面）+ 刀尖（生图竖刀，转成斜拖）拖过地面，身后留下一道血红火线（白热芯、远端冷成暗红）；
    刀尖经过「天理」木牌（生图，字保留）那一刻把它斜着斩断——上半截翻落、断口血红、2 帧白闪、火星迸发、震屏。"""
    def __init__(self):
        g = plate('EA_topground'); lum = g.mean(-1, keepdims=True); g = lum + (g - lum) * 0.45      # 地缝红压淡，红留给火线
        self.ground = K.warp_quad(g, [(-600, 360), (2520, 360), (1920, 1080), (0, 1080)], border=cv2.BORDER_REFLECT)
        self.blade = spr('EA_blade'); self.tab = ground_fade(spr('EA_tablet'))
        us = np.linspace(0, 1, 400); xs_ = -100 + 1900 * np.array([eio(0.3 + v * 0.7) for v in us])
        self.tcut = None
        self._us, self._xs = us, xs_

    @staticmethod
    def ly(x): return 700 + (x - 960) * 0.03

    def render(self, t):
        if self.tcut is None: self.tcut = self.t0 + float(self._us[np.argmax(self._xs >= 1180)]) * (self.t1 - self.t0)
        u = self.u(t)
        fr = self.ground.copy()
        yy, xx = grid()
        x = -100 + 1900 * eio(0.3 + u * 0.7)
        tip = (x, self.ly(x))
        lit = np.exp(-((xx - x) ** 2 + ((yy - tip[1]) * 2.2) ** 2) / (2 * 260 ** 2))
        fr = fr * (0.62 + 0.25 * lit)[..., None]
        ly = self.ly(xx); on = 1 - sstep(x - 40, x, xx)
        cool = np.exp(-np.maximum(x - xx, 0) / 700)
        line = np.exp(-((yy - ly) / 3.5) ** 2) * on; glow = np.exp(-((yy - ly) / 24) ** 2) * on * cool
        fr = fr * (1 - 0.6 * np.exp(-((yy - ly) / 8) ** 2) * on)[..., None]
        fr = fr + (line * cool * 1.4)[..., None] + (line * 1.2)[..., None] * RED + glow[..., None] * RED * 0.9
        q = t - self.tcut
        tf = np.zeros((H, W, 3), np.float32)
        wob = 0.0 if q >= 0 else 0.9 * math.sin(t * 7.3) * c01((q + 0.55) / 0.55) ** 2   # P1-9：被斩前 0.5s 木牌轻微晃动（刀风先到）
        tf, At = put(tf, self.tab, t, 520, (1180 + 3.5 * wob, 720), wind=0, breathe=0, rot=wob)
        C = tf / np.maximum(At, 1e-3)[..., None]
        if q >= 0:
            p0 = (900.0, 640.0); p1 = (1460.0, 672.0)                       # 斩在牌身与木桩交界：「天理」整块翻落，字不被切
            C, At, em = R3.cut_layer(C, At, p0, p1, q, fall=1.3, side=1)
            fr = R3.comp(fr, C, At)
            fr = fr + (em * 2.0 + K.blur_ds(em, 10) * 2.0)[..., None] * RED
            if q < 2.5 / 30: fr = fr * 1.3 + 0.25 * (1 - q * 12)
            fr = sparks2(fr, t, 1501, (1180, 656), t0=self.tcut, n=80, dirc=(0.6, -0.8), spread=1.4, grav=1500, speed=(500, 1400))
        else:
            fr = R3.comp(fr, C, At)
        a = (0.494, 0.012); s = 1400 / (0.99 * self.blade.h)
        fr, _ = put_at(fr, self.blade, t, a, tip, s, wind=0, breathe=0, rot=-143)
        fr = sparks2(fr, t, 1230, tip, burst=False, n=40, life=0.3, dirc=(-1, -0.6), spread=0.8, grav=1200, speed=(300, 800))
        return bloom(fr, 0.8, 0.4)


# ==================================================================== E16 S123 CU 正面 + ✓（210.33–211.27）
def symbol_mask(img, region, no_border=False):
    """生图符号的整笔蒙版：暗墨像素的连通域，质心在 region 内就整片保留（不按矩形截笔画）；
    no_border=True 时碰到画布边的大片（如 ✓ 底板下方那道扫笔）不要，免得贴到别处时露出画布边。"""
    m = (img.max(-1) < 0.24).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros(n, np.float32)
    hh, ww = m.shape
    for i in range(1, n):
        if st[i, 4] < 3000: continue
        x, y, w, h = st[i, :4]
        if no_border and (x <= 1 or y <= 1 or x + w >= ww - 1 or y + h >= hh - 1): continue
        if region[0] <= cen[i][0] < region[2] and region[1] <= cen[i][1] < region[3]: keep[i] = 1
    return keep[lab]


def edge_fade(shape, seed=9, w=110):
    """画布四边「干笔收尾」：沿两条对角方向拉出的飞白丝状噪声决定笔画在哪里断，边缘是硬的丝状断口（不是虚化），
    符号层贴到别的底上时不露画布直边。"""
    h, ww = shape
    n = np.random.default_rng(seed).random((h // 4, ww // 4)).astype(np.float32)
    k = np.eye(25, dtype=np.float32) / 25
    sdir = np.maximum(cv2.filter2D(n, -1, k), cv2.filter2D(n, -1, k[::-1].copy()))
    sdir = (sdir - sdir.mean()) / (sdir.std() + 1e-6)
    sdir = cv2.resize(sdir, (ww, h), interpolation=cv2.INTER_LINEAR)
    yy, xx = np.mgrid[0:h, 0:ww].astype(np.float32)
    d = np.minimum(np.minimum(xx, ww - 1 - xx), np.minimum(yy, h - 1 - yy))
    return np.clip((d - w * (0.55 + 0.4 * sdir)) / (w * 0.06), 0, 1).astype(np.float32)


class SymbolShot(Shot):
    """✓ / ✗ 镜共用：符号笔画是生图画进底板的；init 时把笔画补底藏起来，按笔顺（弧长参数）一笔刷出。"""
    def setup_symbol(self, name, region, strokes):
        img = plate(name)
        lum = img.mean(-1)
        keep = symbol_mask(img, region)
        self.sym_m = cv2.GaussianBlur(cv2.dilate(keep, np.ones((5, 5), np.uint8)), (0, 0), 1.2)
        self.full = img
        self.blank = inpaint_mask(img, keep)
        self.strokes = strokes
        # 揭开用「距落笔点的半径」（圆形前缘）而不是沿笔道的弧长参数：
        # 弧长参数在折线转弯处是距离场的等值线，等值线会在两笔交叠区拐成楔形/领结缺口，截出一段直线边。
        # 半径前缘在任何笔画形状上都是圆/滚动的弧，两笔取 max 自然融合，没有硬边界。
        yy, xx = grid()
        self.rp, self.rmax = [], []
        for pts, _, _ in strokes:
            P = np.array(pts, np.float32)
            d = np.full((H, W), 1e9, np.float32)
            for i in range(len(P) - 1):
                a, b = P[i], P[i + 1]; v = b - a; L = np.linalg.norm(v) + 1e-6; dv = v / L
                u = np.clip((xx - a[0]) * dv[0] + (yy - a[1]) * dv[1], 0, L)
                d = np.minimum(d, np.hypot(xx - (a[0] + dv[0] * u), yy - (a[1] + dv[1] * u)))
            self.rp.append(d)
            hits = d[self.sym_m > 0.5]
            self.rmax.append(float(hits.max() if hits.size else d.max()) + 40.0)
        self.ws = [np.ones((H, W), np.float32)] * len(strokes)
        # 前缘干笔：沿笔顺方向的丝状噪声，让揭开边是飞白断口而不是一条干净弧线
        self.noise = []
        for i, (pts, _, _) in enumerate(strokes):
            n = np.random.default_rng(1700 + i).random((H // 4, W // 4)).astype(np.float32)
            n = cv2.filter2D(n, -1, np.eye(9, dtype=np.float32) / 9)
            n = (n - n.mean()) / (n.std() + 1e-6)
            self.noise.append(cv2.resize(n, (W, H), interpolation=cv2.INTER_LINEAR))

    def symbol(self, t):
        rev = np.zeros((H, W), np.float32); fl = 0.0
        for rp, rmx, nz, (pts, t0, dur) in zip(self.rp, self.rmax, self.noise, self.strokes):
            k = c01((t - t0) / dur)
            if k <= 0: continue
            front = np.clip((k * 1.08 * rmx - rp + 26 * nz) / 90.0, 0, 1)      # 半径前缘：宽过渡 + 干笔丝状噪声
            rev = np.maximum(rev, front)
            fl = max(fl, pulse(t, t0 + dur, 0.1))
        m = self.sym_m * rev
        return self.blank * (1 - m[..., None]) + self.full * m[..., None], m, fl

    def splat(self, fr, t, t0, o, seed):
        """落笔一记：墨点四溅（黑）。"""
        q = t - t0
        if not (0 <= q < 0.4): return fr
        return K.sparks(fr, t, seed, o, n=40, life=0.4, speed=(300, 1100), dirc=(0, -1), spread=2.4, grav=1400, burst=True, t0=t0,
                        color=(-0.9, -0.9, -0.9), amt=1.0, area=(40, 30), size=2)


class E16(SymbolShot):
    """白纸 + 红日 + ✓（生图：✓ 是一笔干墨画进底板）；「对」字头一笔刷出（先短后长，落笔墨点四溅 + 白闪），红日缓缓放大；
    正面特写（生图，偏左，直视镜头，发丝风吹 + 呼吸）。分层：底板 0.2 / ✓ 笔画（揭开）/ 人（锁定）。"""
    def __init__(self):
        t0 = CT(53, 0)
        self.setup_symbol('EA_check', (600, 40, 1920, 1000), [([(735, 540), (1080, 960), (1860, 90)], t0 - 0.03, 0.16)])
        self.sp = spr('EA_E16')
        self.tchk = t0

    def render(self, t):
        u = self.u(t); pv = u - 0.5
        img, m, fl = self.symbol(t)
        fr = warp_plate(img, 1.04 + 0.02 * u, 800 - 30 * pv * 0.2, 540)          # ✓ 右移让出左侧给人
        fr = fr + fl * 0.25
        fr = self.splat(fr, t, self.tchk + 0.13, (1250, 940), 1601)
        fr, _ = put(fr, self.sp, t, 1000 * (1 + 0.04 * u), (380 + 30 * u, 1095), wind=6.0)
        return bloom(fr, 0.88, 0.3)


class E17(SymbolShot):
    """用户 11-11 点名重做（3:32）：左右两半——左白纸 + ✓（对）+ 邪笑的脸，右朱红 + ✗（错）+ 痛苦的脸；
    两张脸都是完整的脸部特写生图（鬼屠定妆照参考），贴画幅外侧边放、由画幅左右边界裁成半张脸，脸朝画面中线。
    ✓ 已在 E16 写成，这里整笔在；✗ 两笔按「错」「就」字头刷出（干墨、落笔溅墨）；入镜两张脸从画外推进来，
    第二个「错」（6352）痛苦脸再被推一记 + 中缝裂光闪；中缝一道细熔缝（白热芯 + 血红）一直在跳。
    分层：左底板 / ✓ 墨迹 / 右底板 + ✗（揭开）/ 中缝 / 邪笑脸 / 痛苦脸（发丝风吹，各自视差以镜头中点为零）。"""
    CHK_C = (1270, 560); CROSS_C = (570, 560)          # 两个符号在各自底板里的中心

    def __init__(self):
        tin = CT(53, 4)
        self.setup_symbol('EA_cross', (0, 0, 1150, 1080), [([(120, 90), (1080, 1000)], tin - 0.03, 0.12), ([(960, 120), (110, 1040)], CT(53, 5) - 0.03, 0.12)])
        chk = plate('EA_check')
        yy, xx = grid()
        cm = symbol_mask(chk, (600, 40, 1920, 1000), no_border=True) * edge_fade((H, W), 11)       # 整笔 ✓（不截笔画）+ 画布边毛边渐隐
        cm = cv2.GaussianBlur(cm, (0, 0), 0.7)
        red = plate('EA_cross')
        self.redpaper = np.ascontiguousarray(np.tile(red[:, 1240:1720], (1, 4, 1)), np.float32)    # 右半朱红纸：✗ 底板右侧干净的朱红 + 网点
        self.xfade = edge_fade((H, W), 12)
        paper = np.ascontiguousarray(np.tile(chk[:, :480], (1, 4, 1)), np.float32)        # 左半白纸：取 ✓ 底板左侧的白纸 + 网点
        sc = 0.46
        Mt = np.float32([[sc, 0, 690 - self.CHK_C[0] * sc], [0, sc, 560 - self.CHK_C[1] * sc]])
        cmw = cv2.warpAffine(cm, Mt, (W, H)); inkw = cv2.warpAffine(chk, Mt, (W, H))
        self.left = paper * (1 - cmw[..., None]) + inkw * cmw[..., None]
        self.smirk = spr('EA_smirk'); self.pain = spr('EA_pain')
        self.tin, self.t2, self.tf = tin, CT(53, 5), CT(53, 7)

    def right_panel(self, t):
        img, m, fl = self.symbol(t)
        sc = 0.5
        Mt = np.float32([[sc, 0, 1255 - self.CROSS_C[0] * sc], [0, sc, 540 - self.CROSS_C[1] * sc]])
        ink = cv2.warpAffine(img, Mt, (W, H))
        mk = cv2.warpAffine(np.ascontiguousarray(m * self.xfade, np.float32), Mt, (W, H))      # 只取已刷出的 ✗ 笔画（画布外为 0，不露底板边）
        return self.redpaper * (1 - mk[..., None]) + ink * mk[..., None], fl

    def seam(self, fr, t, width):
        yy, xx = grid()
        fl = 0.75 + 0.25 * math.sin(t * 41) + 0.8 * pulse(t, self.tf, 0.1)
        jit = 3 * np.sin(yy / 23 + t * 9) + 2 * np.sin(yy / 7 - t * 15)
        d = np.abs(xx - 960 - jit)
        core = np.exp(-(d / (width * 0.18)) ** 2); hot = np.exp(-(d / (width * 0.6)) ** 2)
        fr = fr * (1 - 0.8 * np.clip(1 - d / (width * 1.4), 0, 1))[..., None]
        return fr + hot[..., None] * RED * 1.3 * fl + core[..., None] * 1.2 * fl

    def render(self, t):
        u = self.u(t); pv = u - 0.5
        R, fl = self.right_panel(t)
        yy, xx = grid()
        jit = 3 * np.sin(yy / 23 + t * 9) + 2 * np.sin(yy / 7 - t * 15)        # 两半分界跟中缝裂光同一条抖动线（不是直线）
        xm = np.clip((960 + jit - xx) + 0.5, 0, 1)[..., None]
        fr = self.left * xm + R * (1 - xm)
        fr = fr + fl * 0.15 * (1 - xm)
        fr = self.splat(fr, t, self.t2 + 0.09, (1255, 540), 1701)
        fr = self.seam(fr, t, 18)
        e1 = eout(c01((t - self.tin) / 0.2), 3)                            # 入镜推进
        e2 = eout(c01((t - self.tf) / 0.12), 2)                             # 第二个「错」：痛苦脸再被推一记
        fr, _ = put_at(fr, self.smirk, t, (0.55, 0.55), (40 - 160 * (1 - e1) + 14 * pv, 600), 0.92, wind=8.0, breathe=0.006)
        fr, _ = put_at(fr, self.pain, t, (0.40, 0.55), (1880 + 160 * (1 - e1) - 40 * e2 - 14 * pv, 600), 0.92, wind=8.0, breathe=0.006)
        fr = fr * (1 + 0.18 * pulse(t, self.tf, 0.1))
        return bloom(fr, 0.88, 0.25)


# ==================================================================== E18 S124b ✓ | ✗ 同框，中缝裂开（212.10–212.57）
class E18(E17):
    """接 E17 同一构图（两张脸、两个符号）：两半沿中缝向外错开，中缝从细熔缝撕成宽熔岩裂缝（墨黑焦边 → 血红 → 白热芯，喷碎屑）。"""
    def render(self, t):
        u = self.u(t)
        fr = E17.render(self, t)
        o = int(16 + 30 * eout(u))
        fr = np.concatenate([np.roll(fr, -o, 1)[:, :960], np.roll(fr, o, 1)[:, 960:]], 1)
        fr = lava_crack_local(fr, 960, t, seed=18, width=40 + 34 * eout(u))   # 本单元版本：碎屑改墨线纸片 / 墨块（P1-4）
        return fr


# ==================================================================== E19 S125 CU 直视镜头，碎匾片环绕（212.57–213.93）
class E19(Shot):
    """深血红 → 墨黑底（朱红底板压暗虚化）+ 墨烟从两侧升起 + 墨线勾边的碎匾片在他周围缓缓漂浮（前后两层景深）+
    直视镜头的特写（生图：半脸沉在实黑里、发丝风吹 + 呼吸）。推近 expo_in（MOVE）。"""
    def __init__(self):
        bg = plate('EA_cross', blur=14)
        # P1-8：平涂暗灰 → 网点灰（画面区 ~0.65）。底 = 提亮的朱红板（压成中灰）+ 网点；人物半脸的实黑不动
        base = np.roll(bg, -700, 1)
        base = base.mean(-1, keepdims=True) * np.array([1.0, 0.985, 0.97], np.float32)[None, None, :]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        dots = (np.sin(xx * 1.55) * np.sin(yy * 1.55) > 0.62).astype(np.float32)
        dots = cv2.GaussianBlur(dots, (0, 0), 0.6)
        self.bg = np.ascontiguousarray(np.clip(0.66 - 0.11 * dots[..., None] + 0.13 * (base - base.mean()), 0, 1), np.float32)
        self.sp = spr('EA_E19')
        self.chips = Chips(125, n=26, size=(14, 40), spread=(1100, 500), zr=(1.2, 2.8), tones=(0.92, 0.5, 0.05))
        self.chips_f = Chips(126, n=10, size=(20, 50), spread=(1100, 520), zr=(0.45, 0.8), tones=(0.9, 0.08))
        self.smoke = K.fbm(H // 4, W // 4, 1255, base=5, octaves=5).astype(np.float32)
        self.smoke2 = K.fbm(H // 4, W // 4, 1257, base=4, octaves=4).astype(np.float32)

    def render(self, t):
        u = self.u(t); q = t - self.t0
        fr = self.bg.copy()
        yy, xx = grid()
        # 墨烟：两层各走各的（§12.2）——慢层向上，快层斜向上，再叠低频噪声扰动
        for sm0, spd, amp, sxx in ((self.smoke, -18, 0.10, 1255), (self.smoke2, -46, 0.16, 1257)):
            sm = _flow_smoke(sm0, q, sxx, (spd * 0.5, spd), amp)
            sm = cv2.resize(sm, (W, H))
            side = np.clip((np.abs(xx - 960) - 380) / 300, 0, 1)
            fr = fr * (1 - np.clip((sm - 0.42) * 2, 0, 1) * side * 0.35)[..., None] + (np.clip((sm - 0.58) * 2, 0, 1) * side * 0.10)[..., None]
        fr = self.chips.draw(fr, q * 0.5 + 0.2, to_cam=0.3, zf=1.6)
        fr, _ = put_at(fr, self.sp, t, (0.5, 0.5), (960, 560), 1.0, wind=6.0, breathe=0.006)
        fr = self.chips_f.draw(fr, (t - self.t0) * 0.5 + 0.2, to_cam=0.15, zf=1.6)
        return bloom(fr, 0.88, 0.25)


# ==================================================================== E20 S126 ELS 低地平线日出（213.93–215.30）
class E20(Shot):
    """白纸晨空 + 血红日从山脊后缓缓顶出（生图日轮，偏右）+ 前景焦土山脊（生图）+ 山脊上一粒主角剪影（E14 同一张生图，剪影化）；
    「天」字头日面一跳 + 白光柱加强 + 横向眩光。分层：天 0.15 / 日 0.3 / 山脊 0.6 / 剪影（站在山脊上）/ 白尘。"""
    def __init__(self):
        self.sky = plate('EA_sky')
        self.sun = spr('EA_sun'); self.ridge = spr('EA_ridge'); self.man = spr('EA_E14')
        self.tt = CT(54, 0)

    def render(self, t):
        u = self.u(t); pv = u - 0.5
        fr = warp_plate(flow_plate(self.sky, t - self.t0), 1.3, 900 + 30 * pv * 0.15, 520)
        hit = pulse(t, self.tt, 0.18)
        cy = 920 - 200 * eio(u); cx = 1290 + 30 * pv * 0.3
        fr = rays(fr, (cx, cy), t, strength=0.35 + 0.35 * hit, length=1.1, src_r=380)
        fr, As = put_at(fr, self.sun, t, (0.5, 0.49), (cx, cy), 820 / 1096 * (1 + 0.03 * hit), wind=0, breathe=0, rot=96)
        fr = fr + K.blur_ds(As, 30)[..., None] * RED * 0.5 * hit
        fr, Ar = put_at(fr, self.ridge, t, (0.5, 0.75), (960 + 30 * pv * 0.6, 800), W * 1.1 / 2048, wind=0, breathe=0)
        rx = 640 + 30 * pv * 0.6
        col = Ar[:, int(rx)]; ys = np.nonzero(col > 0.5)[0]
        gy = float(ys[0]) + 6 if len(ys) else 800.0
        fr = contact(fr, (rx, gy), 40, amt=0.7, dirx=-1.0, length=170, sq=5.0)      # 日在右后：长影拖向左
        fr, _ = put(fr, self.man, t, 150, (rx, gy), wind=3.0, breathe=0, look='sil')
        sr = 820 / 1096 * 0.5 * 1152 * 0.5                                    # 日轮半径（屏幕 px，按当前摆放倍率）
        fr = flare(fr, (cx + 0.42 * sr, cy - 0.88 * sr), 0.75 * hit, angle=14, length=0.55, scale=0.34, rays=0.55)
        fr = dust(fr, t, 1264, n=50, amt=0.3)
        return bloom(fr, 0.86, 0.35)


# ==================================================================== E21 S127 CU 仰望侧脸（215.30–216.70）
class E21(Shot):
    """白纸晨空 + 左上血红日（他仰望的方向）+ 白光柱斜下 + 仰望侧脸（生图，朝左上、白色轮廓光，马尾与发丝风吹）+ 白尘。"""
    def __init__(self):
        self.sky = plate('EA_sky', blur=4)
        self.sun = flipped(spr('EA_sun')); self.sp = spr('EA_E21')

    def render(self, t):
        u = self.u(t); pv = u - 0.5
        fr = warp_plate(flow_plate(self.sky, t - self.t0), 1.6, 1400 + 40 * pv * 0.2, 330)
        fr = rays(fr, (330, 280), t, strength=0.4, length=1.0, src_r=260)
        fr, _ = put_at(fr, self.sun, t, (0.5, 0.49), (330 - 40 * pv * 0.4, 280), 640 / 1096, wind=0, breathe=0, rot=-61)
        fr, _ = put(fr, self.sp, t, 1000, (1180 + 40 * u, 1095), wind=10.0, breathe=0.006)
        fr = dust(fr, t, 1271, n=70, amt=0.4, drift=(-20, -30))
        return bloom(fr, 0.86, 0.3)


# ==================================================================== E22 S128 LS 横刀成秤（216.70–217.80）
class E22(Shot):
    """白纸晨空 + 刀身正中背后一轮血红日（支点）+ 焦土山脊 + 横刀于胸、两端吊秤盘（生图）。
    秤盘从精灵里拆成两层，各绕刀端吊点摆：「来」左盘一沉、「量」右盘一沉（阻尼摆）+ 刀身白光自左扫到右。"""
    PIV = ((0.075, 0.44), (0.925, 0.44))
    H_, FOOT = 960, (960, 1080)

    def __init__(self):
        self.sky = plate('EA_sky')
        self.sun = spr('EA_sun'); self.ridge = spr('EA_ridge')
        sp = spr('EA_E22')
        self.sp = sp
        self.tl, self.tr = CT(54, 4), CT(54, 5)                              # 来 / 量（第 54 句可见字：天不判我来量）

    def swing(self, t, th):
        a = 0.8 * math.sin(t * 2.1 + th)
        if t > th: a += 5.0 * math.sin(2 * math.pi * 1.5 * (t - th)) * math.exp(-(t - th) / 0.45)
        return a

    def render(self, t):
        u = self.u(t); pv = u - 0.5
        fr = warp_plate(flow_plate(self.sky, t - self.t0), 1.4, 620, 600 - 20 * pv * 0.2)
        a, s = self.sp.fit(self.H_)
        foot = (self.FOOT[0], self.FOOT[1] - 15 * u)
        by = scr_of(self.sp, self.H_, foot, (0.5, 0.43))[1]
        fr = rays(fr, (960, by - 30), t, strength=0.45, length=1.0, src_r=280)
        fr, _ = put_at(fr, self.sun, t, (0.5, 0.49), (960, by - 30), 600 / 1096, wind=0, breathe=0, rot=147)
        fr, _ = put_at(fr, self.ridge, t, (0.5, 0.75), (960 + 30 * pv * 0.6, 830), W * 1.1 / 2048, wind=0, breathe=0)
        z, A = self.sp.draw(np.zeros((H, W, 3), np.float32), t, a, foot, s, grade=NEU, rim=NORIM, wrap=0, shade=None, wind_amp=_wind(6.0), breathe=0)
        yy, xx = grid()
        mx = xx.copy(); my = yy.copy()                                     # 秤盘绕刀端吊点摆：连续形变场（权重在盘外平滑归零，没有图层接缝）
        for piv, th, sg in ((self.PIV[0], self.tl, 1), (self.PIV[1], self.tr, -1)):
            px, py = scr_of(self.sp, self.H_, foot, piv)
            wgt = sstep(py + 5, py + 45, yy) * (1 - sstep(70, 140, sg * (xx - px)))
            ang = np.radians(self.swing(t, th)) * wgt
            dx, dy = xx - px, yy - py
            ca, sa = np.cos(ang), np.sin(ang)
            mx = mx - (dx - (dx * ca + dy * sa))
            my = my - (dy - (-dx * sa + dy * ca))
        z = cv2.remap(z, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR)
        A = cv2.remap(A, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR)
        fr = fr * (1 - A[..., None]) + z
        x0 = scr_of(self.sp, self.H_, foot, (0.05, 0.43))[0]; x1 = scr_of(self.sp, self.H_, foot, (0.95, 0.43))[0]
        kx = np.interp(t, [self.t0, self.tl, self.tr, self.t1], [x0, 0.5 * (x0 + x1) - 200, 0.5 * (x0 + x1) + 200, x1 + 60])
        yy, xx = grid()
        sw = np.exp(-((xx - kx) / 70) ** 2) * np.exp(-((yy - by) / 9) ** 2) * A
        fr = fr + sw[..., None] * 1.6 + K.blur_ds(sw, 14)[..., None] * 0.6
        return bloom(fr, 0.85, 0.35)


# ==================================================================== E23 S129 MCU 后撤蓄力（217.80–218.27）
class E23(Shot):
    """白纸底（晨空虚焦提亮）+ 漫画集中线（墨线，向胸口收拢，强度随推近上升 = 吸气）+ 蓄力横刀（生图：刀身横在眼前，发丝 / 红带风吹）。"""
    def __init__(self):
        self.bg = np.clip(plate('EA_sky', blur=12) * 0.6 + 0.42, 0, 1)
        self.sp = spr('EA_E23')

    def render(self, t):
        u = self.u(t)
        fr = speed_radial(flow_plate(self.bg, t - self.t0, seed=5), (900, 560), 0.25 + 0.6 * ein(u, 2), t, seed=129, inner=0.34)
        fr, _ = put_at(fr, self.sp, t, (0.5, 0.5), (960, 545), 1.06, wind=11.0, breathe=0)      # 画布四边都在画外
        return bloom(fr, 0.88, 0.25)


# ==================================================================== E24 S129b ECU 刃身满屏寒光（218.27–218.97）
class E24(Shot):
    """E23 同一张生图推到刃身大特写（刀身横贯画面），白光自柄扫到刀尖 + 刃口一线白光；横向速度线。"""
    BL = ((0.73, 0.335), (0.0, 0.305))                                  # 新刀（直刃 + 中式方镡）：刀根护手 → 刀尖，沿刀身中线

    def __init__(self):
        self.bg = np.clip(plate('EA_sky', blur=12) * 0.6 + 0.42, 0, 1)
        self.sp = spr('EA_E23')

    def render(self, t):
        u = self.u(t); e = eio(u)
        sc = 1.9 + 0.1 * e
        src = (0.50 - 0.18 * e, 0.322)
        fr = speed_h(flow_plate(self.bg, t - self.t0, seed=6, drift_far=(-20.0, 0.0), drift_near=(-60.0, 0.0)), 0.5, t, seed=1291, dirx=-1)
        fr, A = put_at(fr, self.sp, t, src, (960, 560), sc, wind=4.0, breathe=0, rot=-2)
        k = eio(c01(u * 1.15))
        bx = self.BL[0][0] + (self.BL[1][0] - self.BL[0][0]) * k; byy = self.BL[0][1] + (self.BL[1][1] - self.BL[0][1]) * k
        cr, sr = math.cos(math.radians(-2)), math.sin(math.radians(-2))
        dx, dy = (bx - src[0]) * self.sp.w * sc, (byy - src[1]) * self.sp.h * sc
        p = (960 + dx * cr - dy * sr, 560 + dx * sr + dy * cr)            # 与 draw(rot=-2) 同向：cv2 正角为逆时针
        fr = flare(fr, p, 0.9 * (1 - 0.6 * c01((u - 0.85) / 0.15)), angle=-2, length=0.8)
        yy, xx = grid()
        g = np.exp(-(((xx - p[0]) / 240) ** 2 + ((yy - p[1]) / 26) ** 2)) * A
        fr = fr + g[..., None] * 0.8
        return bloom(fr, 0.85, 0.35)


# ==================================================================== E25 S130 LS 终极横斩（218.97–220.33）
class E25(Shot):
    """白纸晨空 + 焦土山脊 + 横斩后定姿（生图）；「的」字头背景沿刀线裂开（人不裂、地面不裂）：白热光带 + 血红溢光 + 横向墨线速度线 +
    干笔飞白斩痕横贯 + 火星沿刀向右喷 + 脚下扬尘。人压在光带之上（r6 #49 的要求保留）。"""
    def __init__(self):
        self.sky = plate('EA_sky', flip=True)
        self.ridge = spr('EA_ridge'); self.sp = spr('EA_E25')
        self.ts = CT(55, 6)

    def render(self, t):
        u = self.u(t); pv = u - 0.5; q = t - self.ts
        bg = warp_plate(flow_plate(self.sky, t - self.t0), 1.15, 420 + 30 * pv * 0.2, 500, rot=1.5)
        bg, _ = put_at(bg, self.ridge, t, (0.5, 0.75), (960 + 30 * pv * 0.5, 830), W * 1.1 / 2048, wind=0, breathe=0)
        h, foot = 740, (930, 935)
        by = scr_of(self.sp, h, foot, (0.7, 0.28))[1]
        fr = bg
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        if q > 0:
            e = eout(q / 0.25)
            gap = 70 * e * (1 - 0.3 * c01((q - 0.6) / 0.5))
            top = K.cam(bg, 1.0, oy=gap / 2); bot = K.cam(bg, 1.0, oy=-gap / 2)
            wb = 1 - sstep(780, 900, yy); bot = bot * wb + bg * (1 - wb)
            fr = np.where(yy < by, top, bot)
            # P1-5：光剑式发光管 → 一道硬边白芯（细、干笔断口）+ 极窄血红边，辉光压到最低
            yv = np.arange(H, dtype=np.float32)[:, None]                     # (H,1)
            bx_ = np.arange(W, dtype=np.float32)[None, :]                    # (1,W)
            core = np.exp(-((yv - by) / 1.5) ** 2) ** 2              # 硬边细芯（~1px 高斯平方）
            brk = 0.25 + 0.75 * np.clip(cv2.resize(cv2.GaussianBlur(K.fbm(2, W // 8, 1308, base=6, octaves=3).astype(np.float32), (0, 0), 1)[0], (W, 1), interpolation=cv2.INTER_CUBIC), 0, 1)
            dry = np.clip((brk - 0.30) / 0.25, 0, 1) * 0.85 + 0.15               # 干笔：飞白断续，但不是整段断开
            core = core * dry * (1 - sstep(0.90, 1.0, np.abs(bx_ - 960) / 960) * 0.5)
            edge = np.clip(np.exp(-((yv - by) / max(3.5, gap * 0.10)) ** 2) - core, 0, 1)
            fr = fr * (1 - 0.45 * edge[..., None]) + edge[..., None] * RED * 0.45
            fr = fr * (1 - core[..., None] * 0.92) + core[..., None] * 1.06
            fr = speed_h(fr, 0.6 * math.exp(-q / 0.5), t, seed=1305, y0=by - 260, y1=by + 260)
            if q < 0.08: fr = fr * 1.2 + 0.15 * (1 - q / 0.08)
        fr, A = put(fr, self.sp, t, h, foot, wind=6.0, mblur=(80, 0) if 0 <= q < 0.03 else (0, 0))
        if q > -0.02:
            fr = ink_slash(fr, (-60, by + 6), (1980, by - 6), eout((q + 0.02) / 0.06), 1 - c01((q - 0.15) / 0.35), width=50, seed=1306)
            fr = sparks2(fr, t, 1301, (1500, by), t0=self.ts, n=80, dirc=(1, -0.1), spread=0.35, grav=300, speed=(600, 1500))
            fr = ink_ring(fr, (930, 935), 40 + 300 * eout(q / 0.4), 1 - c01(q / 0.6), squash=5.0, seed=1307)
        fr = embers(fr, t, 1303, n=40, amt=0.6)
        return bloom(fr, 0.85, 0.35)


# ==================================================================== E26 S131 ELS 火线到地平线、日从线头升起（220.33–221.27）
class E26(Shot):
    """白纸晨空 + 一点透视焦土（生图，地面正中一道血红火线直通地平线）+ 血红日从火线尽头升起（被地面遮住下半）+
    火线随拍呼吸发光、白 / 血红余烬上飘。拉远（MOVE expo_out 1.25→1.0）。地平线 y=600 对齐入转场的横线 match_cut。"""
    HY = 600

    def __init__(self):
        self.sky = plate('EA_sky')
        self.sun = flipped(spr('EA_sun')); self.gr = spr('EA_line')

    def render(self, t):
        u = self.u(t)
        fr = warp_plate(flow_plate(self.sky, t - self.t0), 1.2, 1500, 650)
        sy = self.HY + 70 - 150 * eout(u, 2)
        fr = rays(fr, (960, sy), t, strength=0.5, length=1.0, src_r=150)
        fr, _ = put_at(fr, self.sun, t, (0.5, 0.49), (960, sy), 300 / 1096, wind=0, breathe=0, rot=-112)
        s = W / 2048 * 1.02
        fr, Ag = put_at(fr, self.gr, t, (0.5, 0.573), (960, self.HY), s * 1.04, wind=0, breathe=0)
        yy, xx = grid()
        lw = 3 + (yy - self.HY).clip(0) * 0.08
        line = np.exp(-((xx - 960) / lw) ** 2) * (yy > self.HY) * Ag
        br = 0.5 + 0.5 * M.kick_punch(t)
        fr = fr + (line * br)[..., None] * 0.8 + K.blur_ds(line, 12)[..., None] * RED * 0.8 * br
        fr = fr + np.exp(-((yy - self.HY) / 2.0) ** 2)[..., None] * 0.6 * np.exp(-((xx - 960) / 700) ** 2)[..., None]
        fr = embers(fr, t, 1312, n=40, amt=0.6)
        return bloom(fr, 0.86, 0.35)


# ==================================================================== 接线
CLASSES = {c.__name__: c for c in (E01, E02, E03, E04, E05, E06, E07, E08, E09, E10, E11, E12, E13, E14T, E15, E16, E17, E18,
                                   E19, E20, E21, E22, E23, E24, E25, E26)}


def apply(mod):
    """替换 SHOTS 里 E01–E26 的类（起帧、原镜号、景别不变）；IDS / BOUNDS 重算；只改本单元镜头的 MOVE / CUTS 条目。"""
    global M
    M = mod
    if getattr(mod, '_r8d_ea', False): return
    mod._r8d_ea = True
    mod.SHOTS[:] = [(CLASSES.get(c.__name__, c) if f < mod.CHORUS_END else c, f, a, b) for (c, f, a, b) in mod.SHOTS]
    mod.IDS[:] = [s[0].__name__ for s in mod.SHOTS]
    mod.BOUNDS[:] = [s[1] for s in mod.SHOTS] + [mod.F1]
    # 运镜：e_r9 把 E22/E23/E24 的 MOVE 去掉了（整图镜头自己推），新版是分层合成，交回统一运镜
    mod.SHAKE['E20'] = [(CT(54, 0), 8)]                                   # 新 E20 冲击在「天」字头（原表落在镜尾帧，不触发）
    mod.SHAKE['E12'] = [(CT(51, 9) + 0.03, 10)]                           # 跟印落地同一帧
    mod.SHAKE['E09'] = [(CT(51, 2), 12)]
    mod.MOVE['E22'] = ('sine', 1.0, 1.04, 0, 0, -20, 0, 0, 0)
    mod.MOVE['E23'] = ('expo_in', 1.0, 1.18, 0, 0, 0, 0, 0, 0)
    mod.MOVE['E24'] = ('sine', 1.04, 1.0, 0, 0, 0, 0, 0, 0)
    mod.MOVE['E25'] = ('expo_out', 1.05, 1.0, 0, 0, 0, 0, 0, 0)
    mod.MOVE['E09'] = ('expo_out', 1.06, 1.0, -40, 30, 0, 0, 1.5, -0.5)
    # 转场：保留种类与时长，金色边光改中性白（风格 D 无金）；E22 入圆对准新日心
    mod.CUTS['E22'] = ('match_cut', 0.0, 0.18, dict(shape='circle', center=(960, 520), radius=150, glow=np.array([1.0, 1.0, 1.0], np.float32)))
    mod.CUTS['E26'] = ('match_cut', 0.0, 0.22, dict(shape='line', center=(960, 600), angle=0, glow=np.array([1.0, 1.0, 1.0], np.float32)))
    mod.CUTS['E01'] = ('cut', 0, 0, {})                                                   # 入口冲击改在 E01.render 里（反白帧）
    mod.CUTS['E05'] = ('impact', 0, 0, dict(col=(1.0, 1.0, 1.0), amp=10))
    mod.CUTS['E23'] = ('impact', 0, 0, dict(col=(1.0, 1.0, 1.0), amp=10, soft=True))
    mod.CUTS['E25'] = ('impact', 0, 0, dict(col=(1.0, 1.0, 1.0), amp=8, soft=True))
    cover_moves(mod)


def cover_moves(mod):
    """运镜平移 / 滚转 / 震屏会让 K.cam 在画幅边露出镜像填充（BORDER_REFLECT：左缘一排对称「人字纹」）。
    逐镜按最坏时刻算出外露像素，把该镜整段 zoom 乘一个刚好盖住的系数（2.39 黑边内的上下外露不算）。"""
    LB = (H - W / 2.39) / 2                                              # 上下黑边高度（约 138px）
    for i, (c, f, _, _) in enumerate(mod.SHOTS):
        if f >= mod.CHORUS_END: break
        sid = mod.IDS[i]; mv = mod.MOVE.get(sid)
        if not mv: continue
        t0, t1 = mod.BOUNDS[i] / FPS, mod.BOUNDS[i + 1] / FPS
        need = 1.0
        for k in range(61):
            u = k / 60; t = t0 + (t1 - t0) * u
            e = mod.ease(mv[0], u)
            z = mv[1] + (mv[2] - mv[1]) * e; x = mv[3] + (mv[4] - mv[3]) * e; y = mv[5] + (mv[6] - mv[5]) * e; r = mv[7] + (mv[8] - mv[7]) * e
            for (ts, amp) in mod.SHAKE.get(sid, []):
                q = t - ts
                if 0 <= q < 0.5:
                    a = amp * math.exp(-q / 0.12); x += a * math.sin(q * 90); y += a * math.cos(q * 73)
            cr, sr = math.cos(math.radians(r)), math.sin(math.radians(r))
            for px, py in ((0, LB), (W, LB), (0, H - LB), (W, H - LB)):
                for g in (1.0, 1.02, 1.04, 1.06, 1.08, 1.10, 1.12):           # 找刚好盖住的最小倍率
                    dx, dy = (px - W / 2) / (z * g), (py - H / 2) / (z * g)
                    qx = cr * dx - sr * dy + W / 2 + x; qy = sr * dx + cr * dy + H / 2 + y
                    if -1 <= qx <= W + 1 and -1 <= qy <= H + 1: break
                need = max(need, g)
        if need > 1.0:
            mod.MOVE[sid] = (mv[0], mv[1] * need, mv[2] * need) + tuple(mv[3:])
