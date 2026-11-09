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


def key_times(full_text, times, key):
    """从整句逐字时间里切出关键词那几字的时间（关键词必须整句里连续出现，取第一次）。"""
    i = full_text.find(key)
    if i < 0:
        return None
    return list(times[i:i + len(key)])


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


def grid_cells(quad, src_w, src_h, bw, bh, row_mod=37, src_y0=0.0):
    """砖墙载面 → 屏幕上的「砖格」。

    只对 `c1kit.brick_wall()` + `c1kit.warp_quad()` 这条链成立（S034/S041 等砖墙镜都是它）：
      row  = y // bh；off = (row%2)*(bw//2) + (row*row_mod % 23)；col = (x + off) // bw
    quad 顺序与 warp_quad 一致：[[0,0],[w,0],[w,h],[0,h]] → quad 的四个角。
    src_y0 = 源图切片偏移（`wall[off:off+h]` 时传 -off），让砖行号与画面行号对齐。

    返回 {(row, col): dict(cx, cy, w, h, rot)}，单位像素；rot 是该砖在画面里的横向倾角（度）。
    """
    if quad is None:
        return {}
    M = cv2.getPerspectiveTransform(
        np.float32([[0, 0], [src_w, 0], [src_w, src_h], [0, src_h]]), np.float32(quad))

    def P(xs, ys):
        v = M @ np.array([xs, ys, 1.0], np.float64)
        return v[:2] / (v[2] if abs(v[2]) > 1e-9 else 1e-9)

    out = {}
    nrow = int(math.ceil(src_h / bh)) + 3
    ncol = int(math.ceil(src_w / bw)) + 3
    for r in range(nrow):
        roff = (r % 2) * (bw // 2) + (r * row_mod % 23)
        ys = r * bh + bh / 2.0 + src_y0
        for c in range(ncol):
            xs = c * bw - roff + bw / 2.0
            p = P(xs, ys)
            if not (-300 <= p[0] <= W + 300 and -300 <= p[1] <= H + 300):
                continue
            a = P(xs - bw / 2, ys); b = P(xs + bw / 2, ys)
            c_ = P(xs, ys - bh / 2); d_ = P(xs, ys + bh / 2)
            w = float(np.hypot(*(b - a))); h = float(np.hypot(*(d_ - c_)))
            if w < 6 or h < 4:
                continue
            rot = math.degrees(math.atan2(float(b[1] - a[1]), float(b[0] - a[0]) + 1e-9))
            out[(r, c)] = dict(cx=float(p[0]), cy=float(p[1]), w=float(w), h=float(h), rot=float(rot))
    return out


def pick_cells(cells, targets, group=(1, 1), used=None):
    """给一串目标屏幕坐标，各自挑最近的砖格（可 group=(2,2) 把 2×2 块砖并成一格）。
    返回 [{cx,cy,w,h,rot}]（顺序同 targets）。挑不到时跳过该字。"""
    used = set() if used is None else used
    gw = max(1, int(group[0])); gh = max(1, int(group[1]))
    keys = list(cells.keys())
    out = []
    for tx, ty in targets:
        best, bd = None, 1e18
        for (r, c) in keys:
            if any((r + i, c + j) in used for i in range(gh) for j in range(gw)):
                continue
            acc = [cells[(r + i, c + j)] for i in range(gh) for j in range(gw)
                   if (r + i, c + j) in cells]
            if len(acc) < gw * gh:
                continue
            cx = sum(a['cx'] for a in acc) / len(acc); cy = sum(a['cy'] for a in acc) / len(acc)
            w = sum(a['w'] for a in acc) / gw; h = sum(a['h'] for a in acc) / gh
            d = (cx - tx) ** 2 + (cy - ty) ** 2
            if d < bd:
                bd, best = d, (r, c, cx, cy, w, h, acc[0]['rot'])
        if best is None:
            continue
        r, c, cx, cy, w, h, rot = best
        for i in range(gh):
            for j in range(gw):
                used.add((r + i, c + j))
        out.append(dict(cx=cx, cy=cy, w=w, h=h, rot=rot))
    return out


def pick_block(cells, targets, cols=2, rows=4, group=(1, 1)):
    """结构化选格：在砖格图上找「cols 列 × rows 行」的一块（允许列/行各自连续），
    使 8 个字分别落在格心且总位移最小。返回 [{cx,cy,w,h,rot}]（顺序同 targets）。"""
    gw = max(1, int(group[0])); gh = max(1, int(group[1]))
    cel = {}
    for (r, c) in cells:
        acc = [cells.get((r + i, c + j)) for i in range(gh) for j in range(gw)]
        if any(a is None for a in acc):
            continue
        cel[(r, c)] = dict(cx=sum(a['cx'] for a in acc) / len(acc),
                           cy=sum(a['cy'] for a in acc) / len(acc),
                           w=sum(a['w'] for a in acc) / gw,
                           h=sum(a['h'] for a in acc) / gh,
                           rot=acc[0]['rot'])
    if not cel:
        return []
    n = len(targets)
    per = int(math.ceil(n / float(cols)))
    rs = [k[0] for k in cel]; cs = [k[1] for k in cel]
    best, bcost = None, 1e18
    for r0 in range(min(rs) - rows, max(rs) + 2):
        for c0 in range(min(cs), max(cs) + 1):
            picks = []
            ok = True
            k = 0
            for j in range(cols):
                for i in range(per):
                    if k >= n:
                        break
                    key = (r0 + i, c0 - j)          # 竖排先右后左
                    if key not in cel:
                        ok = False; break
                    picks.append((k, cel[key])); k += 1
                if not ok or k >= n:
                    break
            if not ok or len(picks) < n:
                continue
            cost = sum((cel_w['cx'] - targets[i][0]) ** 2 + (cel_w['cy'] - targets[i][1]) ** 2
                       for i, cel_w in picks)
            if cost < bcost:
                bcost, best = cost, picks
    if best is None:
        return []
    out = [None] * n
    for i, cw in best:
        out[i] = cw
    return [o for o in out if o]


def _place_cells(places, cells, fit=0.80, ar=1.0, unify='cap'):
    """把字位改成「一格一个字」：字心 = 格心，字号不越出自己那格。

    unify=True   全部取最小的那格（最保守，透视墙会让字变小）
    unify='cap'  各自按本格定，但封顶在「各格能力的中位数」（默认；近处砖大字大，透视自然）
    unify=False  完全按各自那格（让透视线索最强）
    """
    if not cells:
        return places
    sizes = [min(c['w'] * 0.84 / max(1e-6, ar), c['h'] * fit) for c in cells]
    cap = max(p['size'] for p in places)
    if unify is True:
        cap = min(min(sizes), cap)
        sizes = [cap] * len(sizes)
    elif unify == 'cap':
        cap = min(float(np.median(sizes)), cap)
        sizes = [min(z, cap) for z in sizes]
    out = []
    for pl, c, sz in zip(places, cells, sizes):
        q = dict(pl)
        q['x'] = c['cx']; q['y'] = c['cy']
        q['size'] = float(min(sz, pl['size']) if unify is False else sz)
        q['rot'] = float(np.clip(c['rot'] * 0.7, -7.0, 7.0))
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
                alpha=min(1.0, p * 3.0) * alpha, scale=1.0, texture=False,
                rot=float(pl.get('rot', 0.0)), sx=1.0 / max(1e-6, ar))
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
                 virt_light='auto', virt_amt=None, cells=None, cell_fit=0.80, cell_unify='cap',
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
    if cells:
        places = _place_cells(places, cells, fit=cell_fit, ar=ar, unify=cell_unify)
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
    if virt_light == 'auto':                       # 规则③：镜内没有方向光就自己补一盏
        corr = _dir_light_corr(sub, light)
        va = 0.0 if corr > 0.25 else (0.30 if corr > 0.12 else 0.62)
    else:
        va = 0.0 if virt_light is None else float(virt_light)
    if virt_amt is not None:
        va = float(virt_amt)
    sub = _virt_light(sub, light, va)
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


# ------------------------------------------------------------------ 烧
def _sdf(A):
    """字 alpha → 有符号距离场（<0 在字内），供 burn_hole 直接当洞的形状用。"""
    ins = (A > 0.5).astype(np.uint8)
    din = cv2.distanceTransform(ins, cv2.DIST_L2, 5)
    dout = cv2.distanceTransform(1 - ins, cv2.DIST_L2, 5)
    return (dout - din).astype(np.float32)


def burning_lyric(fr, text, box, prog=1.0, times=None, t=None, layout='v', cols=1, size=None,
                  font='serif_b', ar=1.0, ink=(0.42, 0.035, 0.02), t_burn=None, seed=0,
                  mode='glyph', void=None, hole_scale=1.0, cells=None, cell_fit=0.80,
                  lead=0.05, dur=0.25, alpha=1.0):
    """「烧」：字自燃（mode='glyph'）或烧穿载面（mode='hole'）。

    mode='glyph'  复用 `e_r7.self_burn_glyph`：暗朱墨字身 + 笔画内侧碳化 + 缘上断续火线 + 火星上飘；
                  过渡靠逐字进度（唱到哪个字，哪个字才烧起来 → 火沿读序走过去）。
    mode='hole'   复用 `e_r7.burn_hole`：字当洞的形状（SDF），洞缘焦痕 20–40px + 纤维毛边 + 卷曲碳边，
                  洞里露出 `void`（不给就用载面自身的模糊压暗值，读作「烧穿到后面」）。
    t_burn        火烧的起点时间（默认 = 首字字头），逐字火势用它算 q。
    """
    import e_r7 as R7
    places = prop_layout(text, box, layout=layout, cols=cols, size=size, font=font, ar=ar)
    if not places:
        return fr
    if cells:
        places = _place_cells(places, cells, fit=cell_fit, ar=ar)
    n = len(places)
    pr = _char_progs(text, n, prog, times, t, lead, dur)
    if t is None:                       # 静止证明帧：火已经烧进去
        t = 0.60
        if t_burn is None:
            t_burn = 0.0
    if times is not None and t_burn is None:
        t_burn = min(v for v in times if v is not None)
    L = T.Layer()
    for p, pl in zip(pr, places):
        if p <= 0.004:
            continue
        T.place(L, pl['ch'], pl['x'], pl['y'], pl['size'], (1.0, 1.0, 1.0), pl['font'],
                alpha=min(1.0, p * 3.0) * alpha, texture=False, rot=float(pl.get('rot', 0.0)))
    A = L.A
    if A.max() <= 0.01:
        return fr
    if mode == 'hole':
        F = _sdf(A) * float(hole_scale)
        if void is None:
            bl = cv2.GaussianBlur(fr, (0, 0), 26)
            void = np.clip(bl.mean(-1)[..., None].repeat(3, -1) * 0.35, 0, 1).astype(np.float32)
        return np.clip(R7.burn_hole(fr, void, F, t, seed), 0, 4)
    return np.clip(R7.self_burn_glyph(fr, A, t, float(t_burn if t_burn is not None else t), seed=seed,
                                      ink=ink), 0, 4)


# ------------------------------------------------------------------ 穿线
def threaded_lyric(fr, text, box, prog=1.0, times=None, t=None, layout='v', cols=1, size=None,
                   font='serif_b', ar=1.0, thread=(0.62, 0.05, 0.05), top=None, sway=9.0,
                   track_v=0.26, track_h=0.16,
                   freq=0.9, length_pad=26.0, thread_w=1.6, hang=0.42, beads=0.0,
                   shadow=0.62, glow=0.10, cells=None, cell_fit=0.80,
                   lead=0.05, dur=0.25, alpha=1.0):
    """「穿线」：字挂在朱红丝线上，随线摆。

    每条线从 `top`（默认 = 字块上方 26px）垂到字顶；字的 x 由摆角决定：
        ang_i = sway * sin(2π·freq·t + φ_i) * (i+1)/n * prog_i
        x_i   = x0_i + L_i·sin(ang_i),  y_i = y0_i + L_i·(1-cos(ang_i))
    相位 φ_i 逐字递增（越靠后的字越晚被带动），prog_i 让字「唱到才挂上去」。
    `beads`>0 时线穿过字的上下各打一个红结（像提线木偶的系点）。
    """
    places = prop_layout(text, box, layout=layout, cols=cols, size=size, font=font, ar=ar,
                         track_v=track_v, track_h=track_h)
    if not places:
        return fr
    if cells:
        places = _place_cells(places, cells, fit=cell_fit, ar=ar)
    n = len(places)
    pr = _char_progs(text, n, prog, times, t, lead, dur)
    if t is None:                      # 静止证明帧：取摆幅最大的那一瞬
        t = 0.25 / max(1e-3, freq)
    if top is None:
        top = min(p['y'] - p['size'] * 0.5 for p in places) - length_pad

    thr = np.zeros((H, W), np.float32)                     # 丝线 alpha
    knots = np.zeros((H, W), np.float32)
    rail_y = int(round(top))                               # 挂杆：横贯所有字的顶线（微垂）
    L = T.Layer()
    for i, (p, pl) in enumerate(zip(pr, places)):
        if p <= 0.004:
            continue
        ph = 0.55 * i
        ang = sway * math.sin(2 * math.pi * freq * t + ph) * (0.35 + 0.65 * (i + 1) / n) * p
        Ln = max(40.0, pl['y'] - pl['size'] * 0.5 - top)
        x = pl['x'] + Ln * math.sin(math.radians(ang))
        y = pl['y'] + Ln * (1 - math.cos(math.radians(ang)))
        rt = math.degrees(math.atan2(0, 1)) + ang * 0.55
        T.place(L, pl['ch'], x, y, pl['size'], (1.0, 1.0, 1.0), pl['font'],
                alpha=alpha, texture=False, rot=rt)
        xt = pl['x'] + Ln * math.sin(math.radians(ang)) * 0.5
        cv2.line(thr, (int(round(pl['x'] + Ln * math.sin(math.radians(ang)) * 0.1)), int(round(top))),
                 (int(round(x)), int(round(y - pl['size'] * hang))), float(p), int(round(thread_w)), cv2.LINE_AA)
        if beads > 0:                                       # 系点红结
            cv2.circle(knots, (int(round(x)), int(round(y - pl['size'] * hang))),
                       max(2, int(round(pl['size'] * 0.05 * beads))), float(p), -1, cv2.LINE_AA)
    if L.bb[2] <= L.bb[0]:
        return fr
    xs_ = [p['x'] for p in places]
    if len(xs_) >= 2:
        x0r, x1r = min(xs_) - max(60.0, places[0]['size'] * 0.6), max(xs_) + max(60.0, places[0]['size'] * 0.6)
        sag = max(6.0, (x1r - x0r) * 0.03)
        ts_ = np.linspace(0, 1, 64)
        for k in range(63):
            xa = x0r + (x1r - x0r) * ts_[k]; xb = x0r + (x1r - x0r) * ts_[k + 1]
            ya = rail_y + sag * (1 - (2 * ts_[k] - 1) ** 2); yb = rail_y + sag * (1 - (2 * ts_[k + 1] - 1) ** 2)
            cv2.line(thr, (int(xa), int(ya)), (int(xb), int(yb)), 1.0, max(1, int(round(thread_w * 0.9))), cv2.LINE_AA)
    out = T.compose(fr, L, shadow=shadow, shadow_sigma=18, glow=glow, glow_sigma=14)
    # 丝线要「亮」才看得见：暗背景上加性提亮 + 一圈窄辉光；再补一根横贯的字块挂杆
    colv = np.array(thread, np.float32)
    TH = cv2.GaussianBlur(thr, (0, 0), 0.5)
    glowT = cv2.GaussianBlur(thr, (0, 0), 3.2)
    out = out + TH[..., None] * colv * 2.4 + glowT[..., None] * colv * 1.1
    if knots.max() > 0:
        KN = cv2.GaussianBlur(knots, (0, 0), 0.45)
        out = out + KN[..., None] * colv * 3.0 + cv2.GaussianBlur(knots, (0, 0), 2.4)[..., None] * colv * 1.2
    return np.clip(out, 0, 4)


# ------------------------------------------------------------------ 擦
def wiped_lyric(fr, text, box, prog=1.0, times=None, t=None, layout='v', cols=1, size=None,
                font='serif_b', ar=1.0, ink=(0.055, 0.05, 0.052), wipe=None, wipe_dir=(1.0, -0.15),
                keep=0.18, front=0.5, streak=1.0, seed=0, cells=None, cell_fit=0.80,
                shadow=0.0, lead=0.05, dur=0.25, alpha=1.0):
    """「擦」：字先被「写/刻」上去，再沿 `wipe_dir` 被擦掉（刮擦 / 雨水冲 / 手抹）。

    keep    擦过之后留下的残墨比例（0 = 干净，0.25 = 留一道浅影）
    front   擦除前沿的宽度（0.2–0.8：前沿越窄越像刀刮，越宽越像抹布）
    streak  沿擦除方向的纤维拖痕强度（干笔/纸纤维；换向即为雨冲）
    wipe    擦除进度 0–1；None 时用逐字进度里最后一个字的位置推（唱到哪擦到哪）
    """
    places = prop_layout(text, box, layout=layout, cols=cols, size=size, font=font, ar=ar)
    if not places:
        return fr
    if cells:
        places = _place_cells(places, cells, fit=cell_fit, ar=ar)
    n = len(places)
    pr = _char_progs(text, n, prog, times, t, lead, dur)
    L = T.Layer()
    for p, pl in zip(pr, places):
        if p <= 0.004:
            continue
        T.place(L, pl['ch'], pl['x'], pl['y'], pl['size'], (1.0, 1.0, 1.0), pl['font'],
                alpha=min(1.0, p * 2.6) * alpha, texture=True, rot=float(pl.get('rot', 0.0)))
    A = L.A
    if A.max() <= 0.01:
        return fr
    # 擦除方向 → 归一化进度场
    ys, xs = np.nonzero(A > 0.02)
    ext = np.array([xs.min(), ys.min(), xs.max(), ys.max()], np.float32)
    dx, dy = wipe_dir
    nn = math.hypot(dx, dy) or 1.0
    dx, dy = dx / nn, dy / nn
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    proj = (xx - ext[0]) * dx + (yy - ext[1]) * dy
    span = max(1.0, (ext[2] - ext[0]) * abs(dx) + (ext[3] - ext[1]) * abs(dy))
    q = 0.0 if wipe is None else float(wipe)
    if wipe is None:                                   # 默认：取「最靠后的已唱字」当擦除前沿
        q = float(np.clip(max(pr) if pr else 0.0, 0, 1))
    r = np.random.default_rng(seed)
    fib = cv2.resize(r.random((max(2, H // 26), max(2, W // 6))).astype(np.float32), (W, H),
                     interpolation=cv2.INTER_CUBIC)
    front_px = np.clip(proj / span - (q - front * 0.5), 0, 1) / max(1e-3, front)
    gone = np.clip(front_px * (0.75 + 0.5 * fib), 0, 1)          # 0 = 还在，1 = 已擦掉
    keepm = keep * (0.35 + 0.9 * fib)                            # 残墨（跟着纤维走）
    A2 = A * (1 - gone * (1 - keepm))
    edge = np.clip(1 - np.abs(np.clip(front_px, 0, 1) * 2 - 1), 0, 1) * A * streak
    out = fr.copy()
    inkc = np.array(ink, np.float32)
    out = out * (1 - A2[..., None]) + inkc * A2[..., None]
    if shadow > 0:
        sm = cv2.GaussianBlur(A2, (0, 0), 10)
        out = out * (1 - shadow * sm[..., None] * 0.6)
    out = out + edge[..., None] * np.array([0.72, 0.70, 0.66], np.float32) * 0.5   # 擦痕的冷白粉屑
    return np.clip(out, 0, 4)


# ------------------------------------------------------------------ 印
def stamped_lyric(fr, text, box, prog=1.0, times=None, t=None, layout='v', cols=1, size=None,
                  font='serif_b', ar=1.0, red=(0.72, 0.055, 0.045), press=1.0, wear=0.24,
                  bleed=1.4, frame_box=True, rot=0.0, seed=0, cells=None, cell_fit=0.80,
                  drop=0.35, lead=0.05, dur=0.25, alpha=1.0):
    """「印」：朱印压上去（不是盖在屏幕上，是**压进**载面：印泥乘到底材上，纸/石纹透出来）。

    合成用乘性 + 少量叠加而非盖上去，所以底材纹理始终在印下：
        out = fr·(1 - A·press) + fr·tint·A·press + 印泥浮色
    另外三件事让它像真印：① 边缘纸纤维洇开（`bleed`）② 印面残损（`wear`）③ 落印回弹（`drop`）。
    `frame_box` 时给整句套一圈朱色边框（4 字以上自动走 `props.seal_face` 的印章布局感）。
    """
    places = prop_layout(text, box, layout=layout, cols=cols, size=size, font=font, ar=ar)
    if not places:
        return fr
    if cells:
        places = _place_cells(places, cells, fit=cell_fit, ar=ar)
    n = len(places)
    pr = _char_progs(text, n, prog, times, t, lead, dur)
    L = T.Layer()
    for p, pl in zip(pr, places):
        if p <= 0.004:
            continue
        e = T.ease_out(min(1.0, p), 2.2)
        T.place(L, pl['ch'], pl['x'], pl['y'], pl['size'], (1.0, 1.0, 1.0), pl['font'],
                alpha=min(1.0, p * 3.0) * alpha, scale=1.0 + drop * (1 - e),
                texture=False, rot=rot + float(pl.get('rot', 0.0)))
    A = L.A
    if A.max() <= 0.01:
        return fr
    r = np.random.default_rng(seed)
    nz = cv2.resize(r.random((max(2, H // 14), max(2, W // 14))).astype(np.float32), (W, H),
                    interpolation=cv2.INTER_CUBIC)
    wear_m = np.clip((1 - wear) + wear * (nz * 2.4 - 0.35), 0.25, 1.0)
    A = A * wear_m
    soft = cv2.GaussianBlur(A, (0, 0), bleed)
    A = np.maximum(A, soft * 0.55)                                # 边缘洇开
    if frame_box and n >= 4:
        bx = _mask_box(A, 0)
        if bx is not None:
            x0, y0, x1, y1 = bx
            pad = int(max(10, 0.10 * max(x1 - x0, y1 - y0)))
            cv2.rectangle(A, (max(0, x0 - pad), max(0, y0 - pad)),
                          (min(W - 1, x1 + pad), min(H - 1, y1 + pad)), 1.0,
                          max(2, int(round(min(W, H) * 0.0035))), cv2.LINE_AA)
            A = cv2.GaussianBlur(A, (0, 0), 1.1)
    c = np.array(red, np.float32)
    k = (A * press)[..., None] * alpha
    tint = np.minimum(1.6, c[None, None, :] / 0.55)
    out = fr * (1 - k * 0.55) + fr * tint * k * 0.85 + c[None, None, :] * k * 0.30
    return np.clip(out, 0, 4)


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


# =====================================================================================
# 试点总调度：每一项 = 一帧「改造前」+ 一帧「净板 + 道具字」→ 对比图
# =====================================================================================
def _render(f):
    import prun, random
    st = _render.st = getattr(_render, 'st', None) or prun.load()
    random.seed(int(f)); np.random.seed(int(f))
    return prun.render_frame(int(f), {}, st)


def plate(f, section):
    """取「无字幕净板」——只改运行期开关/模块属性，不动任何源文件。

    chorus1 : 副歌一自带 C1_LYR 开关（`chorus1.py:1577`），设 '0' 即无统一字幕层
    c       : 运行期把 `sec_c_pre2_chorus2.SENTS` 置空（Sec.frame 逐帧读全局）
    a       : 运行期把 `sec_a_intro_verse1.lyrics` 换成恒等函数
    e       : 运行期把 `e_r3.Lyr / e_r3.LyrO / e_r3.Sub` 的 draw 换成恒等
    b_pre1  : 该段字幕就写在镜头 render() 里、没有开关 —— 用 T.place 过滤掉指定字号的那几个字
    """
    import os
    if section == 'chorus1':
        old = os.environ.get('C1_LYR', '3')
        os.environ['C1_LYR'] = '0'
        try:
            return _render(f)
        finally:
            os.environ['C1_LYR'] = old
    if section == 'c':
        import sec_c_pre2_chorus2 as M
        old = M.SENTS; M.SENTS = []
        try:
            return _render(f)
        finally:
            M.SENTS = old
    if section == 'a':
        import sec_a_intro_verse1 as M
        old = M.lyrics; M.lyrics = lambda fr, t: fr
        try:
            return _render(f)
        finally:
            M.lyrics = old
    if section == 'e':
        import e_r3, e_r5
        keep = []
        for M in (e_r3, e_r5):
            for nm in dir(M):
                if not (nm in ('Lyr', 'LyrO') or nm.startswith('Sub')):
                    continue
                cls = getattr(M, nm)
                if isinstance(cls, type) and 'draw' in cls.__dict__:
                    keep.append((cls, cls.__dict__['draw']))
        for cls, _ in keep:
            cls.draw = lambda self, fr, t, **kw: fr
        try:
            return _render(f)
        finally:
            for cls, fn in keep:
                cls.draw = fn
    return _render(f)


def s034_cells(t, picks=((13, 3), (14, 3), (13, 2), (14, 2))):
    """S034「砖墙」的「一字一砖」格（示例：任何 `K.brick_wall()+K.warp_quad()` 的镜头都能照抄）。

    S034 的砖几何是 `K.brick_wall(2400,1600,220,92,9,34)` → `wall[off:off+1300]` → `warp_quad(src, quad(t))`，
    off = int(260*min(1.2,u))。这里把同一套参数喂给 `grid_cells()` 直接算出屏幕上的砖格，
    再手挑 4 个「最大的砖」（透视近端）——这样每个字都能完整坐在一块砖上，笔画不被砖缝切断。
    """
    import chorus1
    S = chorus1.S034
    u = (t - S.t0) / (S.t1 - S.t0)
    off = int(260 * min(1.2, max(0.0, u)))
    try:
        quad = S.quad(S(), t)
    except Exception:
        return None
    cells = grid_cells(quad, 2400, 1300, 220.0, 92.0, src_y0=-off)
    out = [cells.get(k) for k in picks]
    return None if any(c is None for c in out) else out


_ITEMS = [
    # id, 句号, 段, 帧, 文本, box, 函数, 参数
    dict(id='L15', sec='chorus1', f=2071, text='若规则是铁壁铜墙', key='铁壁铜墙', box=(140, 150, 560, 940), fn='刻',
         hot='墙', cells=s034_cells,
         kw=dict(depth=5.0, dark=0.90, cell_fit=0.86, hl=(0.76, 0.84, 1.0), hl_amt=0.70,
                 groove=(0.008, 0.010, 0.016), lip=0.85, bite=0.85, chisel=0.50, seed=34)),
    dict(id='L18', sec='chorus1', f=2385, text='是非对错我自己扛', key='自己扛', box=(1400, 210, 1860, 880), fn='刻'),
    dict(id='L35', sec='c', f=4306, text='若规则是铁壁铜墙', key='铁壁', box=(1080, 180, 1820, 700), fn='刻',
         kw=dict(depth=3.5, dark=0.62, hl=(0.55, 0.62, 0.80), hl_amt=0.75, bite=1.6, lip=0.95)),
    dict(id='L54', sec='e', f=6392, text='对就是对错就是错何须伪装', key='何须伪装', box=(1180, 200, 1830, 880), fn='刻'),
    dict(id='L08', sec='a', f=1281, text='那我宁愿做乱世的锋芒', key='乱世', box=(980, 190, 1780, 640), fn='烧'),
    dict(id='L17', sec='chorus1', f=2278, text='血未冷 骨未凉', key='骨未凉', box=(620, 280, 1320, 800), fn='烧'),
    dict(id='L32', sec='c', f=3931, text='信这柄刀还在发烫', key='发烫', box=(300, 220, 1500, 780), fn='烧'),
    dict(id='L51', sec='e', f=6065, text='若规则是谎言伪装', key='谎言', box=(620, 380, 1300, 820), fn='烧'),
    dict(id='L01', sec='a', f=523, text='长夜压在我刀锋之上', key='长夜', box=(620, 240, 1420, 700), fn='穿线'),
    dict(id='L13', sec='chorus1', f=1841, text='血未冷 刀不放', key='刀不放', box=(600, 200, 1400, 640), fn='穿线'),
    dict(id='L19', sec='chorus1', f=2495, text='天不判 我来量', key='我来量', box=(480, 260, 1300, 720), fn='穿线'),
    dict(id='L33', sec='c', f=4093, text='血未冷 刀不放', key='血未冷', box=(300, 200, 1500, 660), fn='穿线'),
    dict(id='L02', sec='a', f=620, text='五百重甲拦不住一道寒光', key='寒光', box=(760, 190, 1780, 600), fn='擦'),
    dict(id='L07', sec='a', f=1176, text='若正义由权势执掌', key='权势', box=(560, 320, 1240, 860), fn='擦'),
    dict(id='L11', sec='b_pre1', f=1632, text='我不信天不信命不信谁的理所应当', key='理所应当', box=(160, 190, 720, 900), fn='擦'),
    dict(id='L31', sec='c', f=3833, text='我不低头不认命不信什么大局为上', key='大局', box=(200, 200, 1500, 780), fn='擦'),
    dict(id='L03', sec='a', f=735, text='谁在高处定对错罪状', key='罪状', box=(1000, 560, 1720, 950), fn='印'),
    dict(id='L05', sec='a', f=954, text='我杀过恶徒也放过混账', key='混账', box=(200, 560, 1000, 950), fn='印'),
    dict(id='L14', sec='chorus1', f=1945, text='谁人来定正邪一方', key='定', box=(830, 430, 1120, 800), fn='印',
         kw=dict(press=1.0, wear=0.26, bleed=1.8, frame_box=False, seed=27)),
    dict(id='L39', sec='c', f=4748, text='天不判 我来量', key='量', box=(1360, 240, 1760, 620), fn='印',
         kw=dict(press=0.9, wear=0.24, bleed=1.3, frame_box=False, seed=29)),
]

_CLS_DEFAULT = {
    '刻': dict(font='serif_black', cols=1, depth=5.5, dark=0.88, hl=(0.76, 0.84, 1.0), hl_amt=0.62,
               groove=(0.008, 0.010, 0.016), lip=0.78, bite=1.0, chisel=0.55, dust=0.85, seed=34),
    '烧': dict(font='serif_black', cols=1, seed=41),
    '穿线': dict(font='serif_black', cols=1, sway=10.0, freq=0.85, thread=(0.62, 0.05, 0.05), beads=0.8,
               track_v=0.52, length_pad=54.0),
    '擦': dict(font='serif_black', cols=1, wipe=0.55, keep=0.20, front=0.45, seed=13),
    '印': dict(font='serif_black', cols=1, press=1.0, wear=0.22, bleed=1.5, seed=21),
}


def _draw(item, base, t, still=False):
    """按手法派发；返回处理后的帧。"""
    import json, os
    fn = item['fn']
    kw = dict(_CLS_DEFAULT[fn]); kw.update(item.get('kw') or {})
    text, box = item.get('key') or item['text'], item['box']
    if 'cols' not in (item.get('kw') or {}):                 # 多字自动分列：一句最多 4 字一列
        nch = len([c for c in text if c != ' '])
        kw['cols'] = 2 if nch >= 7 else 1
        if nch >= 11:
            kw['cols'] = 3
    if item.get('hot'):
        kw.setdefault('hot', item['hot'])
    _full = T.load_lines()[int(item['id'][1:]) - 1]
    times = key_times(_full['text'], _full['times'], text) or _full['times']
    if still:                                    # 静止证明帧：整字已落（镜头内是按演唱逐字落）
        times, t = None, None
        kw.setdefault('prog', 1.0)
    if fn == '刻':
        cells = item.get('cells')
        if callable(cells):
            cells = cells(t if t is not None else item['f'] / 30.0)
        return etched_lyric(base, text, box, times=times, t=t, cells=cells, **kw)
    if fn == '烧':
        return burning_lyric(base, text, box, times=times, t=t, **kw)
    if fn == '穿线':
        return threaded_lyric(base, text, box, times=times, t=t, **kw)
    if fn == '擦':
        return wiped_lyric(base, text, box, times=times, t=t, **kw)
    if fn == '印':
        return stamped_lyric(base, text, box, times=times, t=t, **kw)
    raise ValueError(fn)


def run_items(ids=None, out_dir=None, only=None):
    """跑指定几项，出 before / plate / after + 一张该类对比图。返回 {id: dict(ms=..., paths=...)}"""
    import os, time
    from PIL import Image, ImageDraw, ImageFont
    out_dir = out_dir or os.environ.get('PROPS_OUT') or os.path.abspath(os.path.join('out', 'props_dev'))
    os.makedirs(out_dir, exist_ok=True)
    sel = [it for it in _ITEMS if (ids is None or it['id'] in ids) and (only is None or it['fn'] in only)]
    try:
        F = ImageFont.truetype(os.path.join(T.ROOT, 'fonts', 'NotoSerifSC.otf'), 26)
    except Exception:
        F = ImageFont.load_default()
    res = {}
    for it in sel:
        f = int(it['f']); t = f / 30.0
        before = _render(f)
        pt = plate(f, it['sec'])
        t0 = time.monotonic()
        after = _draw(it, pt.astype(np.float32) / 255.0, t, still=True)
        ms = (time.monotonic() - t0) * 1000.0
        # 再跑两次取中位（首次含字形缓存预热）
        for _ in range(2):
            t0 = time.monotonic(); _draw(it, pt.astype(np.float32) / 255.0, t, still=True)
            ms = min(ms, (time.monotonic() - t0) * 1000.0)
        after8 = (np.clip(after, 0, 1) * 255).astype(np.uint8)
        p1 = os.path.join(out_dir, '%s_before.png' % it['id'])
        p2 = os.path.join(out_dir, '%s_after.png' % it['id'])
        Image.fromarray(before).save(p1)
        Image.fromarray(after8).save(p2)
        if it.get('tiles') != 'S034':                     # S034 已有专门的完整对比图集
            pass
        res[it['id']] = dict(ms=ms, before=p1, after=p2, fn=it['fn'], sec=it['sec'], f=f, t=t, item=it)
        print('ITEM %s %s %s f=%d %5.0fms' % (it['id'], it['fn'], it['sec'], f, ms), flush=True)

    for cls in sorted({r['fn'] for r in res.values()}):
        rows = [r for r in res.values() if r['fn'] == cls]
        if not rows:
            continue
        Wd, Hd = 760, 428
        sheet = Image.new('RGB', (Wd * 2 + 36, (Hd + 40) * len(rows) + 56), (12, 12, 12))
        d = ImageDraw.Draw(sheet)
        d.text((14, 8), '「%s」类 · 左=改造前（屏幕层字幕）  右=改造后（画内道具字）' % cls,
               font=F, fill=(255, 214, 110))
        for i, r in enumerate(rows):
            y = 66 + i * (Hd + 40)
            sheet.paste(Image.open(r['before']).resize((Wd, Hd), Image.LANCZOS), (12, y))
            sheet.paste(Image.open(r['after']).resize((Wd, Hd), Image.LANCZOS), (Wd + 24, y))
            d.text((12, y - 26), '%s  %s  f=%d  %.0fms' % (r['item']['id'], r['item']['text'][:14], r['f'], r['ms']),
                   font=F, fill=(235, 225, 190))
        p = os.path.join(out_dir, 'class_%s.png' % cls)
        sheet.save(p)
        print('SHEET', p, flush=True)
    return res


if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    if args and args[0] in ('刻', '烧', '穿线', '擦', '印'):
        run_items(only=[args[0]])
    elif args and args[0] == 'items':
        run_items(ids=args[1:] or None)
    else:
        pilot(frame=int(args[0]) if args else 2071)
