"""units/props_dev.py — 第四轮「歌词道具化」试点（props 组 · 只新增，不改任何现有镜头文件）

为什么做这件事：用户喜欢的三段（1:30–1:40 / 1:58–2:04 / 2:41–2:57）共同点是
**字是画面里的道具，不是屏幕层字幕** —— 算盘珠把「牺牲多少」拨出来、刻刀把「大局」
阴刻进笏板、字挂在朱红丝线上随线摆、宋体铅字块砸进纸面、四方朱印把朱红「人」盖没。
全片 56 句里其余仍有大量屏幕层排版字幕（`scenes.lyric()` / `c_kit.draw_sent()` /
`lyric3.LyricLayer` / `e_kit.Lyr` 那几套），本模块把「道具化」抽成可复用函数，供逐条替换。
20 处清单见 crew/round4/props_plan.md。

五类手法（贯穿全片视觉语言：黑白灰 + 朱红 + 金；2.39 黑边 y∈[120,960) 不变）
    刻    etched_lyric()   阴刻 / 镂空：字槽压暗 + 迎光内壁高光 + 背光内壁投影 + 凿口崩边 + 凿痕 + 石屑
    印    —（待实现）      复用 prop_layout()/prop_mask() + props.seal_face() + a_r6.imprint()
    擦    —（待实现）      复用 prop_mask() + 沿擦除方向的纤维噪声（同 _chisel 的方向化噪声）
    烧    —（待实现）      复用 prop_mask() + e_r7.self_burn_glyph() / e_r7.burn_hole()
    穿线  —（待实现）      复用 prop_layout() + 每字一条丝线的垂吊摆动位移（同 2:41 S05_Ren 的提线）

本轮落地「刻」，因为试点选的是「若规则是铁壁铜墙」（副歌一 S034：整面砖墙 = 最适合阴刻的载面）。
用法（镜头 render() 内，替掉原来那一句 draw_sent / Lyr / lyric）：

    import props_dev as PD
    fr = PD.etched_lyric(fr, '若规则是铁壁铜墙', box=(120, 150, 640, 960), times=L15_times, t=t,
                         cols=2, font='serif_black', light=(-1.0, -0.35), hot='墙')

纯 numpy/OpenCV + lib/typo.py 字形；不读任何生图素材，可独立单测。
"""
import math
import numpy as np, cv2
import typo as T

W, H = 1920, 1080
BAR = 120
SAFE = (60, BAR + 30, W - 60, H - BAR - 30)

try:                      # 阴刻浮雕算法来自 A 组第六棒（units/a_r6.py:engraved），这里做包围盒内版本
    import a_r6 as _A6
except Exception:         # 单独 import 本模块（缺 a_kit 依赖）时无妨：_engrave 自带等价实现
    _A6 = None


# ------------------------------------------------------------------ 字体
_SERIF = (('serif_r', 'Regular'), ('serif_m', 'Medium'), ('serif_sb', 'SemiBold'),
          ('serif_b', 'Bold'), ('serif_black', 'Black'))


def register_fonts():
    """思源宋五档字重注册进 typo.FONTS（chorus1 / e_kit 各注册过一次，这里幂等补充，
    保证单独 import 本模块时 serif_* 也能用）。"""
    import os
    for k, f in _SERIF:
        if k in T.FONTS:
            continue
        p = os.path.join(getattr(T, 'ROOT', ''), 'fonts', 'NotoSerifSC-%s.otf' % f)
        if os.path.exists(p):
            T.FONTS[k] = p


register_fonts()


# ------------------------------------------------------------------ 排版：歌词 → 画内字位
def prop_layout(text, box, layout='v', cols=1, size=None, font='serif_b',
                track_v=0.26, track_h=0.16, fit=0.94, ar=1.0, rows_block=2):
    """把一句歌词排进一个**画内矩形** box=(x0,y0,x1,y1)（砖面 / 石板 / 门板 / 笏板 / 刀身…）。

    layout='v'      竖排；cols>1 自动分列，先右后左（碑刻 / 匾额的传统读序）
    layout='h'      横排一行
    layout='block'  方阵（rows_block 字一行，先右后左、自上而下 —— 刻印 / 铅字块的排法）
    ar              该载面的透视横向压缩比（斜面上字变窄），>1 变窄
    size=None       按 box 自动定字号（保证不溢出 box、不压字）

    返回 [{ch,x,y,size,font,idx,emph}]，空格不出字位；idx = 演唱顺序的可见字序号。
    """
    chars = [c for c in text if c != ' ']
    n = len(chars)
    if n == 0:
        return []
    x0, y0, x1, y1 = box
    bw, bh = float(x1 - x0), float(y1 - y0)
    sx = 1.0 / max(1e-6, ar)

    if layout == 'h':
        if size is None:
            size = min(bh * fit, bw * fit / max(1.0, n * (1 + track_h)))
        adv = size * (1 + track_h) * sx
        xc = x0 + bw / 2 - adv * (n - 1) / 2
        return [dict(ch=c, x=xc + adv * i, y=y0 + bh / 2, size=size, font=font, idx=i, emph=False)
                for i, c in enumerate(chars)]

    if layout == 'block':
        r = max(1, int(rows_block))
        ncol = int(math.ceil(n / float(r)))
        if size is None:
            size = min(bh * fit / (r * (1 + track_v)), bw * fit / max(1.0, ncol))
        advy = size * (1 + track_v)
        advx = size * (1 + track_h * 0.6) * sx
        out = []
        for j in range(ncol):                                   # 先右后左
            seg = chars[j * r:(j + 1) * r]
            cx = x0 + bw / 2 + (ncol - 1) * advx / 2 - j * advx
            yc = y0 + bh / 2 - advy * (len(seg) - 1) / 2
            for i, c in enumerate(seg):
                out.append(dict(ch=c, x=cx, y=yc + advy * i, size=size, font=font,
                                idx=j * r + i, emph=False))
        return out

    cols = max(1, int(cols))                                    # 'v'
    per = int(math.ceil(n / float(cols)))
    if size is None:
        size = min(bh * fit / (per * (1 + track_v)), bw * fit / (cols * 1.06))
    advy = size * (1 + track_v)
    advx = size * 1.06 * sx
    out = []
    for j in range(cols):                                       # 先右后左
        seg = chars[j * per:(j + 1) * per]
        if not seg:
            continue
        cx = x0 + bw / 2 + (cols - 1) * advx / 2 - j * advx
        yc = y0 + bh / 2 - advy * (len(seg) - 1) / 2
        for i, c in enumerate(seg):
            out.append(dict(ch=c, x=cx, y=yc + advy * i, size=size, font=font,
                            idx=j * per + i, emph=False))
    return out


def _char_progs(text, n, prog=1.0, times=None, t=None, lead=0.05, dur=0.25):
    """逐字进度 [0,1]：由演唱字头时间（times + t）或整句标量 prog 得到。"""
    if times is not None and t is not None:
        raw = T.timed_progress(times, t, dur, lead)
        pr = [p for p, c in zip(raw, text) if c != ' ']
    elif np.isscalar(prog):
        pr = T.seq_progress(n, float(prog))
    else:
        pr = [float(p) for p in prog]
    pr = pr[:n]
    return pr + [1.0] * (n - len(pr))


def prop_mask(text, box, prog=1.0, times=None, t=None, lead=0.05, dur=0.25,
              alpha=1.0, layout='v', cols=1, size=None, font='serif_b', ar=1.0,
              track_v=0.26, track_h=0.16, fit=0.94, rows_block=2):
    """字位 → (Layer, places, progs)。Layer.A 就是「这一句在画面上的 alpha」（全帧 1920×1080）。

    刻 / 印 / 擦 / 烧 / 穿线五类都从这里取 alpha，只换最后一步合成。
    逐字上屏用 alpha 斜坡而不是缩放：凿子不会把字「弹大」，只会越凿越深。
    """
    places = prop_layout(text, box, layout=layout, cols=cols, size=size, font=font, ar=ar,
                         track_v=track_v, track_h=track_h, fit=fit, rows_block=rows_block)
    n = len(places)
    pr = _char_progs(text, n, prog, times, t, lead, dur)
    L = T.Layer()
    for p, pl in zip(pr, places):
        if p <= 0.004:
            continue
        T.place(L, pl['ch'], pl['x'], pl['y'], pl['size'], (1.0, 1.0, 1.0), pl['font'],
                alpha=min(1.0, p * 3.0) * alpha, scale=1.0, texture=False, sx=1.0 / max(1e-6, ar))
    return L, places, pr


# ------------------------------------------------------------------ 包围盒子图（省 3× 时间）
# ------------------------------------------------------------------ 砖格 / 载面格（「一字一砖」）
def _seam_peaks(v, k=8):
    """1D 亮度剖面 → 缝线（亮线）位置：去低频 + 局部极大 + 阈值。返回峰值索引数组。"""
    v = np.asarray(v, np.float32)
    n = v.size
    if n < 16:
        return np.zeros(0, np.int32)
    r = v - cv2.GaussianBlur(v.reshape(-1, 1), (0, 0), max(3.0, n / 14.0)).ravel()
    r = cv2.GaussianBlur(r.reshape(-1, 1), (0, 0), 1.0).ravel()
    if r.max() <= 1e-6:
        return np.zeros(0, np.int32)
    thr = 0.30 * float(r.max())
    pk = []
    for i in range(1, n - 1):
        if r[i] >= r[i - 1] and r[i] >= r[i + 1] and r[i] > thr:
            if pk and i - pk[-1] <= max(3, int(n / 120)):        # 合并相邻峰
                if r[i] > r[pk[-1]]:
                    pk[-1] = i
                continue
            pk.append(i)
    return np.asarray(pk, np.int32)


def _pitch_phase(v):
    """剖面 → (步距, 相位)。相位用模长平均，不会因为剖面里混了两种错位而塌成半砖。"""
    pk = _seam_peaks(v)
    if pk.size < 2:
        return 0.0, 0.0
    d = np.diff(pk).astype(np.float32)
    d = d[(d > 6) & (d < d.max() * 0.999 + 1e-6)]
    if d.size == 0:
        return 0.0, 0.0
    pitch = float(np.median(d))
    if pitch < 6:
        return 0.0, 0.0
    ph = np.mod(pk.astype(np.float32), pitch)
    ang = ph / pitch * 2 * np.pi
    ox = float(np.mod(np.arctan2(np.sin(ang).mean(), np.cos(ang).mean()) / (2 * np.pi) * pitch, pitch))
    return pitch, ox


def brick_grid(fr, box, group=2):
    """从画面量「一格载面」的步距与相位。返回 dict(px, py, oy, ox=(偶皮, 奇皮))，量不出来返回 None。

    砖墙每皮错半砖：横向相位必须**按皮分别量**（奇偶两套），否则剖面里两个相位叠加会把步距量成半砖。
    group>1 时把 group 块砖并成一格（默认 2×2 砖 = 一个字的落脚格，字高 ≈0.8×格高，
    笔画永远不会被砖缝高光切断）。
    """
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0 = max(0, x0); y0 = max(0, y0); x1 = min(fr.shape[1], x1); y1 = min(fr.shape[0], y1)
    if x1 - x0 < 48 or y1 - y0 < 48:
        return None
    g = fr[y0:y1, x0:x1]
    g = g.mean(-1) if g.ndim == 3 else g
    h, w = g.shape
    py, oy = _pitch_phase(g.mean(axis=1))                 # 水平砖缝 → 纵向步距/相位
    if not (10 <= py <= h * 0.5):
        return None
    # 横向：按皮分别量（每皮只取一条带，避开砖缝本身）
    band = max(8, int(py * 0.45))
    xs = {0: [], 1: []}
    k = 0
    while True:
        c0 = int(k * py); c1 = min(h, c0 + band)
        if c0 >= h:
            break
        if c1 - c0 >= 8:
            px_, ox_ = _pitch_phase(g[c0:c1].mean(axis=0))
            if 10 <= px_ <= w * 0.5:
                xs[k % 2].append((px_, ox_))
        k += 1
    if not xs[0] and not xs[1]:
        return None
    pool = xs[0] + xs[1]
    px = float(np.median([a for a, _ in pool]))
    oe = float(np.median([b for _, b in xs[0]])) if xs[0] else None
    oo = float(np.median([b for _, b in xs[1]])) if xs[1] else None
    if oe is None:
        oe = (oo + px / 2) % px
    if oo is None:
        oo = (oe + px / 2) % px
    gp = max(1, int(group))
    return dict(px=px * gp, py=py * gp, oy=float(y0) + oy,
                ox=(float(x0) + oe, float(x0) + oo), group=gp)


def _snap_brick(places, grid, ar=1.0):
    """把每个字吸到「自己的那一格」上：隔皮错半格（砖砌的必然结果），字高按格高定死。"""
    px, py, oy, ox = grid['px'], grid['py'], grid['oy'], grid['ox']
    out = []
    for pl in places:
        r = max(0, int(round((pl['y'] - oy) / py - 0.5)))
        phase = ox[r % 2]
        c = int(round((pl['x'] - phase) / px - 0.5))
        q = dict(pl)
        q['x'] = phase + (c + 0.5) * px
        q['y'] = oy + (r + 0.5) * py
        q['size'] = float(min(pl['size'], px * 0.84 / max(1e-6, ar), py * 0.80))
        out.append(q)
    return out


def _dir_light_corr(sub, light):
    """载面自身的方向光强度：亮度沿光向投影的相关系数 |r|。用来判断要不要补虚拟侧光。"""
    h, w = sub.shape[:2]
    if h < 8 or w < 8:
        return 0.0
    yy, xx = np.mgrid[0:h:4, 0:w:4].astype(np.float32)
    px = (xx / max(1.0, w - 1) - 0.5) * 2.0
    py = (yy / max(1.0, h - 1) - 0.5) * 2.0
    lx, ly = light
    n = math.hypot(lx, ly) or 1.0
    proj = (px * (lx / n) + py * (ly / n)).ravel()
    lum = sub[::4, ::4].mean(-1).ravel()
    if lum.std() < 1e-5 or proj.std() < 1e-5:
        return 0.0
    return float(abs(np.corrcoef(proj, lum)[0, 1]))


def _virt_light(sub, light, amt):
    """虚拟侧光（规则③）：镜内没有方向光时，函数自己在载面上压出一盏斜射光，
    暗面沿 light 反方向衰减；边缘 feather 掉，绝不出现矩形亮块。"""
    if amt <= 0.01:
        return sub
    h, w = sub.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    px = (xx / max(1.0, w - 1) - 0.5) * 2.0
    py = (yy / max(1.0, h - 1) - 0.5) * 2.0
    lx, ly = light
    n = math.hypot(lx, ly) or 1.0
    proj = np.clip(px * (lx / n) + py * (ly / n), -1.0, 1.0)
    edge = np.clip((1.0 - np.maximum(np.abs(px), np.abs(py))) / 0.45, 0, 1)
    edge = edge * edge * (3 - 2 * edge)
    return sub * (1.0 + amt * 0.46 * proj * edge)[..., None]


def _block_rect(places, depth=7.0, ar=1.0):
    """字块包围盒 + 刻凿/石屑所需余量 —— 后续所有像素运算都只在这个子矩形里做。"""
    if not places:
        return None
    smax = max(p['size'] for p in places)
    pad = int(max(16.0, 0.10 * smax + 3.0 * depth))
    xs = [p['x'] - p['size'] * 0.62 for p in places] + [p['x'] + p['size'] * 0.62 for p in places]
    ys = [p['y'] - p['size'] * 0.62 for p in places] + [p['y'] + p['size'] * 0.62 for p in places]
    x0 = int(max(0, min(xs) - pad)); x1 = int(min(W, max(xs) + pad))
    y0 = int(max(0, min(ys) - pad)); y1 = int(min(H, max(ys) + pad + 1.3 * smax))   # 下方留石屑落点
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    return (x0, y0, x1, y1)


def _place_sub(places, pr, rect, alpha=1.0, ar=1.0, only=None):
    """在 rect 内栅格化字位 → 子图 alpha。only 给一组字时只放这些字（朱红关键字用）。"""
    x0, y0, x1, y1 = rect
    L = T.Layer(y1 - y0, x1 - x0)
    for p, pl in zip(pr, places):
        if p <= 0.004 or (only is not None and pl['ch'] not in only):
            continue
        T.place(L, pl['ch'], pl['x'] - x0, pl['y'] - y0, pl['size'], (1.0, 1.0, 1.0), pl['font'],
                alpha=min(1.0, p * 3.0) * alpha, scale=1.0, texture=False, sx=1.0 / max(1e-6, ar))
    return L.A


# ------------------------------------------------------------------ 刻
def _bite(m, seed, amt=1.0):
    """凿口：两档噪声啃字缘 —— 手工阴刻的边不会是干净的字体轮廓，会有崩口。"""
    if amt <= 0.01:
        return m
    h, w = m.shape
    r = np.random.default_rng(seed)
    n1 = cv2.resize(r.random((max(2, h // 10), max(2, w // 10))).astype(np.float32), (w, h),
                    interpolation=cv2.INTER_CUBIC)
    n2 = cv2.resize(r.random((max(2, h // 3), max(2, w // 3))).astype(np.float32), (w, h),
                    interpolation=cv2.INTER_CUBIC)
    keep = np.clip((0.7 * n1 + 0.3 * n2 - (0.50 - 0.14 * amt)) * 7.0, 0, 1)
    return m * keep


def _engrave(sub, m, light=(-1.0, -1.0), depth=7.0, dark=0.88,
             hl=(0.86, 0.92, 1.0), hl_amt=0.95, inner_col=None):
    """阴刻浮雕：字槽压暗 + 背光侧内壁投影 + 迎光侧内壁高光。

    公式与 units/a_r6.py:engraved() 完全相同，只把三次全幅 warpAffine 收进子矩形
    （全幅 1080p 每次 ~25ms，子图 ~4ms；一句 8 字每帧要跑 2–3 次，必须收）。
    """
    m = cv2.GaussianBlur(m, (0, 0), 1.0)
    h, w = m.shape
    lx, ly = light
    sh = np.clip(m - cv2.warpAffine(m, np.float32([[1, 0, -lx * depth], [0, 1, -ly * depth]]), (w, h)), 0, 1)
    hi = np.clip(m - cv2.warpAffine(m, np.float32([[1, 0, lx * depth * 0.6], [0, 1, ly * depth * 0.6]]), (w, h)), 0, 1)
    out = sub * (1 - dark * m[..., None])
    if inner_col is not None:
        out = out + m[..., None] * np.array(inner_col, np.float32)
    out = out * (1 - 0.6 * sh[..., None])
    return out + hi[..., None] * np.array(hl, np.float32) * hl_amt


def _lip(sub, m, light, depth, lip, hl, lip_amt):
    """凿口翻起的碎边：迎光侧一道细亮（崩口受光）、背光侧一道投影。
    阴刻在灰面上光靠「槽内压暗」立不住形，靠这一层才读得出（a_r6.engraved 只管槽内）。"""
    if lip <= 0.01:
        return sub
    h, w = m.shape
    lx, ly = light
    d = max(2.0, depth * lip)
    fwd = cv2.warpAffine(m, np.float32([[1, 0, -lx * d], [0, 1, -ly * d]]), (w, h))
    bwd = cv2.warpAffine(m, np.float32([[1, 0, lx * d], [0, 1, ly * d]]), (w, h))
    hi = np.clip(fwd - m, 0, 1) * (m <= 0.02)
    sh = np.clip(bwd - m, 0, 1) * (m <= 0.02)
    out = sub * (1 - (0.55 * sh * lip)[..., None])
    return out + (hi * lip * lip_amt)[..., None] * np.array(hl, np.float32) * 0.8


def _chisel(sub, m, seed, amt):
    """凿痕：槽底一道道横向短凿（各向异性噪声），让字槽深处不是均匀的灰。"""
    if amt <= 0.01:
        return sub
    h, w = m.shape
    r = np.random.default_rng(seed)
    n = cv2.resize(r.random((max(2, h // 9), max(2, w // 3))).astype(np.float32), (w, h),
                   interpolation=cv2.INTER_CUBIC)
    scar = np.clip((n - 0.46) * 3.4, 0, 1)
    return sub * (1 - (amt * 0.5 * scar * m)[..., None])


def _dust(sub, rect, places, pr, seed, amt):
    """石屑：正在凿的那一字下方飞起的石粉（冷白点，0.3–0.9s 落尽）。"""
    if amt <= 0.01:
        return sub
    x0, y0 = rect[0], rect[1]
    h, w = sub.shape[:2]
    P = np.zeros((h, w), np.float32)
    r = np.random.default_rng(seed)
    hit = False
    for pl, p in zip(places, pr):
        if not (0.02 < p < 0.995):
            continue
        s = pl['size']
        age = 1.0 - p
        life = min(0.9, 0.30 + 0.5 * r.random())
        if age > life:
            continue
        hit = True
        k = age / life
        for _ in range(int(18 * amt)):
            ang = -math.pi * r.uniform(0.05, 0.95)
            sp = s * r.uniform(0.10, 0.34)
            x = pl['x'] - x0 + s * r.uniform(-0.42, 0.42) + math.cos(ang) * sp * k
            y = pl['y'] - y0 + 0.42 * s + math.sin(ang) * sp * k + 1.15 * s * k * k
            if not (0 <= x < w and 0 <= y < h):
                continue
            cv2.circle(P, (int(x), int(y)), int(round(0.8 + 1.5 * (1 - k))), float(1.0 - k), -1, cv2.LINE_AA)
    if not hit or P.max() <= 0:
        return sub
    return sub + cv2.GaussianBlur(P, (0, 0), 0.8)[..., None] * np.array([0.95, 0.97, 1.0], np.float32) * (0.42 * amt)


def etched_lyric(fr, text, box, prog=1.0, times=None, t=None, layout='v', cols=1, size=None,
                 font='serif_b', ar=1.0, depth=7.0, light=(-1.0, -1.0), dark=0.88,
                 hl=(0.86, 0.92, 1.0), hl_amt=0.95, groove=None, lip=0.8, lip_amt=1.0,
                 hot='', hot_col=(0.125, 0.012, 0.008), bite=1.0, chisel=0.5, dust=0.8,
                 seed=0, lead=0.05, dur=0.25, alpha=1.0):
    """「刻」：把一句歌词阴刻 / 镂空进 box 指定的画内载面（砖墙 / 石板 / 门板 / 笏板 / 刀身）。

    fr        float32 RGB 帧 (1080,1920,3)，0–1；返回新帧（不改传入帧）
    box       (x0,y0,x1,y1) 载面矩形（像素，直接用成片坐标 —— 函数不裁 2.39 黑边）
    times, t  演唱逐字时间（typo.load_lines()[i]['times']）与当前时间 → 逐字凿进；
              只给 prog 时按整句 0→1 顺序推进
    depth     内壁投影/高光偏移（px）：砖石 5–9、金属 3–5
    light     侧光方向（指向受光侧）：左上来光用 (-1,-1)。
              **刻字必须有侧光**——平光面上的阴刻等于看不见
    dark      槽底压暗 0–1（浅灰石 0.72、深砖 0.88、黑铁 0.60）
    hl        迎光内壁高光色（冷石 (0.86,0.92,1.0) / 暖石 (0.95,0.80,0.58) / 金 (1.0,0.76,0.40)）
    groove    槽底附加色（None = 只压暗；洒了金粉的槽给 (0.35,0.26,0.10) 之类）
    lip       凿口翻起碎边强度（0 = 只有槽内，灰面上会读不出；0.6–1.2 正常）
    hot       朱红关键字（如 '墙'）：这几个字的槽底渗朱，替掉「红字浮在屏幕上」的老做法
    bite / chisel / dust ：崩口 / 凿痕 / 石屑 强度
    """
    places = prop_layout(text, box, layout=layout, cols=cols, size=size, font=font, ar=ar)
    n = len(places)
    if n == 0:
        return fr
    pr = _char_progs(text, n, prog, times, t, lead, dur)
    if max(pr) <= 0.004:
        return fr
    rect = _block_rect(places, depth=depth, ar=ar)
    if rect is None:
        return fr
    x0, y0, x1, y1 = rect

    M = _place_sub(places, pr, rect, alpha=alpha, ar=ar)
    if M.max() <= 0.01:
        return fr
    if bite > 0.01:
        M = _bite(M, seed + 31, bite)

    sub = fr[y0:y1, x0:x1]
    out = _engrave(sub, M, light=light, depth=depth, dark=dark, hl=hl, hl_amt=hl_amt,
                   inner_col=groove)
    if hot:                       # 朱红关键字的凿槽渗朱（保留「每句至多一个朱红字」的规范，色在槽里）
        Mh = _place_sub(places, pr, rect, alpha=alpha, ar=ar, only=set(hot))
        if Mh.max() > 0.01:
            if bite > 0.01:
                Mh = _bite(Mh, seed + 31, bite)
            out = _engrave(out, Mh, light=light, depth=depth * 0.85, dark=dark, hl=hl,
                           hl_amt=hl_amt * 0.7, inner_col=hot_col)
    out = _lip(out, M, light, depth, lip, hl, lip_amt)
    out = _chisel(out, M, seed + 7, chisel)
    out = _dust(out, rect, places, pr, seed + 13, dust)

    fr = fr.copy()
    fr[y0:y1, x0:x1] = out
    return np.clip(fr, 0, 4)


# ------------------------------------------------------------------ 试点（副歌一 S034「若规则是铁壁铜墙」）
def pilot(frame=2071, out_dir=None, text='若规则是铁壁铜墙', line=14,
          box=(120, 150, 640, 960), cols=2, size=None, **kw):
    """冻结快照里跑试点：同一帧渲「改造前（屏幕层字幕）」/「净板」/「改造后（阴刻进砖面）」，
    再拼对比图。必须在快照目录（含 prun.py）里跑：

        cd out/full_sprite/chunks/full30_50589e0_20261109
        PROPS_OUT=<repo>/out/props_dev PYTHONPATH=.:code/lib:code \\
            ../local60_149c727_20261109/venv/bin/python code/units/props_dev.py
    """
    import os, time, random
    from PIL import Image, ImageDraw, ImageFont
    import prun

    frame = int(frame)
    out_dir = out_dir or os.environ.get('PROPS_OUT') or os.path.abspath(os.path.join('out', 'props_dev'))
    os.makedirs(out_dir, exist_ok=True)
    t = frame / 30.0

    def render(lyr):
        os.environ['C1_LYR'] = lyr    # 副歌一自带开关：'3' = 带统一字幕层；其它值 = 净板（不改任何源文件）
        st = prun.load()
        random.seed(frame); np.random.seed(frame)
        return prun.render_frame(frame, {}, st)

    before = render('3')
    plate = render('0')
    times = T.load_lines()[line]['times']

    ARG = dict(cols=cols, size=size, font='serif_black', light=(-1.0, -0.35), depth=5.5,
               dark=0.90, hl=(0.76, 0.84, 1.0), hl_amt=0.48, groove=(0.008, 0.010, 0.016),
               lip=0.70, hot='墙', hot_col=(0.125, 0.012, 0.008), bite=1.1, chisel=0.60,
               dust=0.9, seed=34)
    ARG.update(kw)

    PL = plate.astype(np.float32) / 255.0
    t0 = time.monotonic()
    after = etched_lyric(PL, text, box, times=times, t=t, **ARG)
    ms = (time.monotonic() - t0) * 1000.0
    after8 = (np.clip(after, 0, 1) * 255).astype(np.uint8)

    def save(a, name):
        p = os.path.join(out_dir, name)
        Image.fromarray(a).save(p)
        return p

    p1 = save(before, 'S034_before.png')
    p2 = save(np.asarray(plate, np.uint8), 'S034_plate.png')
    p3 = save(after8, 'S034_after.png')

    try:
        F = ImageFont.truetype(os.path.join(T.ROOT, 'fonts', 'NotoSerifSC.otf'), 34)
    except Exception:
        F = ImageFont.load_default()

    # ---- 对比图：上（改造前）/ 下（改造后）
    Wd, Hd = 1440, 810
    pan = Image.new('RGB', (Wd, Hd * 2 + 132), (10, 10, 10))
    d = ImageDraw.Draw(pan)
    d.text((28, 10), '改造前 · 屏幕层字幕（S034  %s）' % text, font=F, fill=(255, 214, 110))
    d.text((28, Hd + 76), '改造后 · 阴刻进砖面（etched_lyric）', font=F, fill=(255, 214, 110))
    pan.paste(Image.fromarray(before).resize((Wd, Hd), Image.LANCZOS), (0, 54))
    pan.paste(Image.fromarray(after8).resize((Wd, Hd), Image.LANCZOS), (0, Hd + 120))
    p4 = os.path.join(out_dir, 'S034_compare.png')
    pan.save(p4)

    # ---- 细节图：左 = 原字幕位 1:1，右 = 刻字位 1:1
    def crop(a, cx, cy, w, h):
        xx = int(max(0, min(W - w, cx - w / 2))); yy = int(max(0, min(H - h, cy - h / 2)))
        return a[yy:yy + h, xx:xx + w]

    det = Image.new('RGB', (1300, 660), (10, 10, 10))
    det.paste(Image.fromarray(crop(before, 1752, 480, 300, 620)).resize((300, 620)), (10, 20))
    det.paste(Image.fromarray(crop(after8, int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2), 620, 620)), (350, 20))
    p5 = os.path.join(out_dir, 'S034_detail.png')
    det.save(p5)

    # ---- 逐字凿进序列（同一净板，按演唱字头推进；最后一张 = 整句刻完）
    ts = [times[0] + 0.10, times[4] + 0.16, times[6] + 0.20, t]
    seq = Image.new('RGB', (4 * 440 + 20, 610), (10, 10, 10))
    d2 = ImageDraw.Draw(seq)
    for i, tt in enumerate(ts):
        a = np.clip(etched_lyric(PL, text, box, times=times, t=tt, **ARG), 0, 1)
        c2 = (a[140:980, 80:680] * 255).astype(np.uint8)
        seq.paste(Image.fromarray(c2).resize((374, 524), Image.LANCZOS), (10 + i * 440, 46))
        d2.text((10 + i * 440, 7), 't=%.2fs  逐字凿进' % tt, font=F, fill=(255, 214, 110))
    p6 = os.path.join(out_dir, 'S034_seq.png')
    seq.save(p6)

    print('PILOT frame=%d t=%.2fs etched_lyric=%.0fms' % (frame, t, ms))
    for p in (p1, p2, p3, p4, p5, p6):
        print(' ->', p)
    return ms


if __name__ == '__main__':
    import sys
    pilot(frame=int(sys.argv[1]) if len(sys.argv) > 1 else 2071)
