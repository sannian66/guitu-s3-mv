"""units/lyric_uni.py —《谁定正邪》全片唯一字幕层（竖排单列 · 右对齐 · 逐字墨显）

为什么有这个文件
    全片 5 个摄制组各写了一套字幕层：A 段主词 150–240px + 余字 70–96px 横排 + 暗衬条、
    B 组自己一套、副歌一右侧竖排 x=1752 / 底部横排 y=850 两套、C 段 fly 飘字碎裂出场、
    D 段宣纸风、E 段又一套。位置与风格全不一致 → 本模块是**唯一**字幕层，位置/字号/颜色/
    衬底/动效只有一套参数，不分段落。各组字幕层用 LYRIC_UNI=1 关掉（各文件只加一行守卫）。

规格（2026-11-09 用户定稿，实现即照此，不许自己另设计）
    1 位置     竖排单列、右对齐；列右缘 x=1792（距右边 128px），列顶 y=300；不横排、不居中。
               上下 120px 黑边不许碰（见下方「已知越界」）。
    2 换列     每列最多 10 字；超过 10 字拆两列，第二列在**左**，列间距 96px，整体右对齐。
    3 字号     思源宋 Bold；列内字数 ≤6 → 84px，7–8 → 76px，9–10 → 68px；行距 1.08。
    4 颜色     暖白 #F2F0EC；重音字（每句至多一个）朱红 #B3261A + 极轻朱晕。
               无描边、无朱印、无手写笔触 —— 它是字幕，不是道具。
    5 衬底     竖条渐变 scrim：x=1792 往左 260px 线性淡出，峰值 alpha 0.42；
               按画面亮度自适应（背后已经很暗则减半）；不压死暗部、不超出黑边。
    6 动效     逐字墨显（每字 0.10s，起点 = 字头 −0.06s）；整句在末字后 0.55s 淡出（0.28s）；
               句与句衔接不留空档；无 fly / 碎裂 / glitch。
    7 让位     已被抽成画内道具的字，字幕里留空占位不画（OUT_CHARS，默认空）。
    8 数据源   align.json（逐字时间）+ lyrics.json（56 句）为权威时间轴；不读各组 SENTS。

接口
    enabled() -> bool                    LYRIC_UNI=1 才生效（默认 0 = 完全回到各组原字幕）
    draw(fr, f) -> fr                    在**统一 grade 之后**叠字幕；fr 可 uint8 也可 float32(0..1)，
                                         返回同类型。未开启时原样返回（可无条件接线）。
    lines() -> [dict]                    56 句的排版/时间（对比工具与报告用）
    spec_table() -> str                  规格 + 实测表（报告用）

接线（顺序 finish() → GU.apply() → lyric_uni.draw() → to8()，全片只有一个叠加点）
    render_sprite_full.frame() 与 out/devsnap/prun.render_frame() 各一行：
        fr = LU.draw(fr, f)

已知越界（照规格实现，报告里提出，未擅改）
    9–10 字列（68px）从 y=300 起排到底边 = 1029px，越过下方 120px 黑边（960）69px。
    6 字 84px 到 754，7–8 字 76px 到 951（贴线），只有 9–10 字会进黑边。
"""
import os
import json
import math

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- 基本量
W, H, BAR, FPS = 1920, 1080, 120, 30
_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = '/workspace/work/mv'                    # devsnap 快照会把这个字面量改写成快照绝对路径
if not os.path.isdir(ROOT):
    ROOT = os.path.dirname(_HERE)

FONT_PATH = ROOT + '/fonts/NotoSerifSC-Bold.otf'

# ---------------------------------------------------------------- 开关
def enabled():
    """LYRIC_UNI=1 生效；默认 0（= 各组原字幕，可随时回滚）。"""
    return os.environ.get('LYRIC_UNI', '0') == '1'


# ---------------------------------------------------------------- 规格常量
COL_R = 1792                  # 1 列右缘（1920-128）
COL_TOP = 300                 # 1 列顶
MAX_PER_COL = 10              # 2 每列最多 10 字
COL_GAP = 96                  # 2 第二列往左的列间距
LEAD = 1.08                   # 3 行距
TIERS = ((6, 84), (8, 76), (10, 68))   # 3 (列内字数上限, 字号)

WHITE = (0xF2 / 255.0, 0xF0 / 255.0, 0xEC / 255.0)    # 4 暖白 #F2F0EC
ACCENT = (0xB3 / 255.0, 0x26 / 255.0, 0x1A / 255.0)   # 4 朱红 #B3261A
ACCENT_GLOW = 0.16            # 4 极轻朱晕（additive，占比很小）

SCRIM_W = 260                 # 5 竖条宽（往左淡出 260px）
SCRIM_A = 0.42                # 5 峰值 alpha
SCRIM_DARK = (0.10, 0.22)     # 5 亮度自适应区间：背后亮度 ≤0.10 → 减半（0.21），≥0.22 → 全量

IN_DUR, IN_LEAD = 0.10, 0.06  # 6 逐字墨显：0.10s，起点 = 字头 −0.06s
OUT_HOLD, OUT_DUR = 0.55, 0.28  # 6 末字后 0.55s 起淡出，0.28s 时长
GAP_HOLD = 2.0                # 6 「衔接不留空档」的适用范围：与下一句的间隔 ≤2.0s 时保持到下一句起；
                              #   超长器乐空档（86.2→89.4 = 3.5s 等）按 0.55s 正常退场

# 7 关键词让位：要把字让给画内道具的用 (行号, 字序)，默认空。
OUT_CHARS = set()
#   OUT_CHARS = {(13, 3), (13, 4)}      # 例：第 13 句「谁人来定正邪一方」的「正」「邪」让给道具

STOPWORDS = set('的了是在我你他她它也就都还又很把被而这那些个不没要有和与')

# 各段已有的朱红标注（A 段 LY2 的 _R / 副歌一 lyric3 的 red= / C 段 Sent red= / E 段 Lyr REDT）
# —— 重音字第一优先级。键 = 行号（0 基），值 = 该句朱红字里最能当关键词的那个字序。
RED_MANUAL = {
    0: 5,    # 长夜压在我「刀」锋之上（A LY2 k5）
    1: 6,    # 五百重甲拦不「住」一道寒光（A LY2 k6）
    4: 1,    # 我「杀」过恶徒也放过混账（A LY2 k1）
    6: 1,    # 若「正」义由权势执掌（A LY2 k1/k2）
    7: 5,    # 那我宁愿做「乱」世的锋芒（A LY2 k5/k6）
    12: 3,   # 血未冷「刀」不放（chorus1 red）
    13: 5,   # 谁人来定正「邪」一方（chorus1 red）
    14: 7,   # 若规则是铁壁铜「墙」（chorus1 red）
    15: 2,   # 那就「劈」开它看个天亮（chorus1 red）
    16: 3,   # 血未冷「骨」未凉（chorus1 red）
    17: 7,   # 是非对错我自己「扛」（chorus1 red）
    18: 2,   # 天不「判」我来量（chorus1 red）
    19: 2,   # 这「一」刀就是我的回答 → 刀（chorus1 red=刀，行 19 字序 2）
    28: 3,   # 谁「定」好规则谁写好剧本提纲（C Sent red=规则）
    30: 1,   # 我「不」低头不认命不信什么大局为上（C Sent red=不）
    31: 3,   # 信这柄「刀」还在发烫（C Sent red=刀）
    32: 3,   # 血未冷「刀」不放（C Sent red=刀）
    36: 0,   # 「血」未冷骨未凉（C Sent red=血）
    37: 7,   # 是非对错我自己「扛」（C Sent red=扛）
    39: 2,   # 这「一」刀就是我（C Sent red=刀→字序 2）
    50: 4,   # 若规则是「谎」言伪装（E Lyr red=谎言）
    51: 7,   # 那就撕碎它自己「定」规章（E Lyr「定」朱红大字）
    52: 3,   # 血未冷「骨」未凉（E Sub red=骨）
    53: 4,   # 对就是对「错」就是错何须伪装（E LyrO「错」朱红）
    55: 2,   # 这「一」刀就是我的正道沧桑（E Lyr「刀」朱红 → 字序 2）
}

# ---------------------------------------------------------------- 字形缓存
_GC = {}


def _font(size):
    key = ('f', size)
    f = _GC.get(key)
    if f is None:
        f = ImageFont.truetype(FONT_PATH, int(size))
        _GC[key] = f
    return f


def glyph(ch, size):
    """单字 alpha 蒙版 float32（方画布 g×g，0..1），按 (字, 字号) 缓存。"""
    key = (ch, int(size))
    a = _GC.get(key)
    if a is not None:
        return a
    size = int(size)
    g = int(round(size * 1.28))
    img = Image.new('L', (g, g), 0)
    ImageDraw.Draw(img).text((g / 2.0, g / 2.0), ch, font=_font(size), fill=255, anchor='mm')
    a = np.asarray(img, np.float32) / 255.0
    # 立即可见的字：把极小残值清掉，免得逐字墨显时出现淡淡底影
    a[a < 0.02] = 0.0
    _GC[key] = a
    return a


def char_size(n):
    """列内字数 → 字号（3 号规则）。"""
    for lim, px in TIERS:
        if n <= lim:
            return px
    return TIERS[-1][1]


# ---------------------------------------------------------------- 时间轴 / 排版
_LINES = None


def _load_json(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as fh:
        return json.load(fh)


def _accents():
    """重音字候选：hitmap 的逐字时间 + accent 标记（来源优先级见下）。

    注意：crew/round4/*_hitmap.json 的 accent 标记是「落在重拍上」，一行常 5–6 个，
    不能直接当「那句的重音字」用。所以这里用它的时间算逐字时长，并给 accent 字加权，
    再由 RED_MANUAL（各段已有朱红标注）优先覆盖。
    """
    hit = {}
    base = os.path.join(ROOT, 'crew', 'round4')
    if os.path.isdir(base):
        for fn in sorted(os.listdir(base)):
            if not fn.endswith('_hitmap.json'):
                continue
            try:
                d = _load_json(os.path.join('crew', 'round4', fn))
            except Exception:
                continue
            for w in (d.get('words') or []):
                if 'line' not in w or 'k' not in w:
                    continue
                hit.setdefault((int(w['line']), int(w['k'])), bool(w.get('accent')))
    return hit


def _build():
    """从 align.json（逐字时间）+ lyrics.json（56 句）建 56 条字幕记录。"""
    al = _load_json('align.json')
    ly = _load_json('lyrics.json')
    hit = _accents()
    segs = al['segments']
    out = []
    for i, seg in enumerate(segs):
        text = ly[i]['text'] if i < len(ly) else seg['text'].strip()
        want = text.replace(' ', '')
        # 把 words 展开成逐字时间（一个 word 可能含 2–3 字，均分该 word 的时长）
        chars, times = [], []
        for w in seg['words']:
            s = w['word'].strip()
            if not s:
                continue
            t0, t1 = float(w['start']), float(w['end'])
            m = len(s)
            for j, c in enumerate(s):
                chars.append(c)
                times.append(t0 + (t1 - t0) * (j / m) if m > 1 else t0)
        if ''.join(chars) != want:                      # 保险：对不上就整句均分（不应该发生）
            chars = list(want)
            n = len(chars)
            times = [float(seg['start']) + (float(seg['end']) - float(seg['start'])) * k / n for k in range(n)]
        n = len(chars)
        dur = [times[k + 1] - times[k] for k in range(n - 1)] + [float(seg['end']) - times[-1]]
        # 重音字：各段朱红标注 > hitmap 逐字时长（accent 加权、虚词降权）
        acc = RED_MANUAL.get(i)
        if acc is None or acc >= n:
            best, acc = -1e9, 0
            for k in range(n):
                sc = dur[k] + (0.06 if hit.get((i, k)) else 0.0) - (0.10 if chars[k] in STOPWORDS else 0.0)
                if sc > best:
                    best, acc = sc, k
        ncol = int(math.ceil(n / float(MAX_PER_COL)))
        size = char_size(min(MAX_PER_COL, n))
        out.append(dict(line=i, sec=(ly[i].get('sec') if i < len(ly) else ''), text=text,
                        chars=[dict(ch=c, t=times[k], dur=dur[k], k=k) for k, c in enumerate(chars)],
                        n=n, ncol=ncol, size=size, accent=acc,
                        accent_src=('标注' if i in RED_MANUAL else '时长')))
    # 出/入场时刻（6 号规则）
    for i, r in enumerate(out):
        heads = [c['t'] for c in r['chars']]
        last = heads[-1]
        r['t_on'] = heads[0] - IN_LEAD
        if i + 1 < len(out):
            nxt = out[i + 1]['chars'][0]['t'] - IN_LEAD
            if nxt - last <= GAP_HOLD + OUT_HOLD:        # 句内衔接：不提空档，淡出正好收在下一句起
                r['t_out'] = nxt - OUT_DUR
            else:                                        # 长器乐空档：末字后 0.55s 正常退
                r['t_out'] = last + OUT_HOLD
        else:
            r['t_out'] = last + OUT_HOLD
        r['t_out'] = max(r['t_out'], last + 0.10)        # 末字至少完整露出 0.1s
        r['t_off'] = r['t_out'] + OUT_DUR
        # 排版：每列最多 10 字，第 2 列在左，整体右对齐
        pos, cols = [], []
        for ci in range(0, r['n'], MAX_PER_COL):
            chunk = r['chars'][ci:ci + MAX_PER_COL]
            xc = COL_R - r['size'] / 2.0 - ci // MAX_PER_COL * (r['size'] + COL_GAP)
            cols.append(chunk)
            for j, c in enumerate(chunk):
                pos.append(dict(k=c['k'], ch=c['ch'], t=c['t'], x=xc,
                                y=COL_TOP + r['size'] / 2.0 + j * r['size'] * LEAD))
        r['pos'] = pos
        r['cols'] = cols
        r['y_bot'] = max(p['y'] + r['size'] / 2.0 for p in pos)
        r['box'] = (int(min(p['x'] for p in pos) - r['size'] / 2.0) - 34, int(COL_TOP),
                    COL_R + 6, int(r['y_bot']) + 14)
    return out


def lines():
    global _LINES
    if _LINES is None:
        _LINES = _build()
    return _LINES


def active(t):
    return [r for r in lines() if r['t_on'] <= t < r['t_off']]


# ---------------------------------------------------------------- 衬底
def _scrim(F, x0, y0, x1, y1, ox=0, oy=0):
    """竖条渐变 scrim（5 号规则）：x=1792 往左 260px 线性淡出，峰值 0.42，亮度自适应。
    F 是整帧的子区（左上角 = (ox, oy)），入参用整帧坐标。"""
    h, w = F.shape[:2]
    xa, xb = max(ox, int(x0)), min(ox + w, int(x1))
    ya, yb = max(oy, int(y0), BAR), min(oy + h, int(y1), H - BAR)
    if xb <= xa or yb <= ya:
        return F
    reg = F[ya - oy:yb - oy, xa - ox:xb - ox]
    L = float(reg[..., 0].mean() * 0.299 + reg[..., 1].mean() * 0.587 + reg[..., 2].mean() * 0.114)
    lo, hi = SCRIM_DARK
    k = 0.0 if L <= lo else (1.0 if L >= hi else (L - lo) / (hi - lo))
    a = SCRIM_A * (0.5 + 0.5 * k)                    # 背后已经很暗 → 减半，绝不压死
    xs = np.arange(xa, xb, dtype=np.float32)
    # 1792 是峰值，往左 260px 线性淡出到 0；1792 右侧到画右边缘保持峰值（不留硬竖缝）
    ax = np.clip((xs - (COL_R - SCRIM_W)) / float(SCRIM_W), 0.0, 1.0) * a
    ny = yb - ya
    fy = np.ones(ny, np.float32)
    fe = min(26, ny // 2)
    if fe > 2:
        r = np.linspace(0.0, 1.0, fe, dtype=np.float32)
        e = 0.5 - 0.5 * np.cos(np.pi * r)
        fy[:fe] = e
        fy[ny - fe:] = e[::-1]
    M = fy[:, None] * ax[None, :]
    reg *= (1.0 - M)[..., None]
    return F


# ---------------------------------------------------------------- 绘制
def _paste(F, mask, x0, y0, color, alpha=1.0, glow=0.0, ox=0, oy=0):
    """把蒙版以 alpha 贴到 (x0,y0)（整帧坐标），可选朱晕。蒙版越界自动裁。"""
    h, w = F.shape[:2]
    g0, g1 = mask.shape[:2]
    xs, ys = int(round(x0)) - ox, int(round(y0)) - oy
    cx0, cy0 = max(0, xs), max(0, ys)
    cx1, cy1 = min(w, xs + g1), min(h, ys + g0)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    m = mask[cy0 - ys:cy1 - ys, cx0 - xs:cx1 - xs]
    if alpha != 1.0:
        m = m * alpha
    sub = F[cy0:cy1, cx0:cx1]
    if glow > 0.0:
        bl = cv2.GaussianBlur(m, (0, 0), max(2.0, g0 * 0.10))
        sub += np.asarray(ACCENT, np.float32) * (bl * glow)[..., None]
    sub *= (1.0 - m)[..., None]
    sub += np.asarray(color, np.float32) * m[..., None]


def _sentence(F, r, t, ox=0, oy=0):
    q = (t - r['t_out']) / OUT_DUR                 # 整句淡出
    v = 1.0 if q <= 0 else max(0.0, 1.0 - q / 1.0)
    if v <= 0.0:
        return F
    x0, y0, x1, y1 = r['box']
    F = _scrim(F, COL_R - SCRIM_W, y0 - 48, W, y1 + 40, ox, oy)
    for key in r['pos']:
        if (r['line'], key['k']) in OUT_CHARS:     # 7 让位：留空占位，不画
            continue
        p = (t - (key['t'] - IN_LEAD)) / IN_DUR   # 6 逐字墨显
        if p <= 0.0:
            continue
        p = 1.0 if p >= 1.0 else (1.0 - (1.0 - p) ** 3)
        a = glyph(key['ch'], r['size'])
        if p < 0.999:                             # 墨显：由虚到实，无位移无缩放
            sig = 2.6 * (1.0 - p) ** 2
            if sig > 0.35:
                a = cv2.GaussianBlur(a, (0, 0), sig)
            a = a * p
        acc = key['k'] == r['accent']
        _paste(F, a,
               key['x'] - a.shape[1] / 2.0, key['y'] - a.shape[0] / 2.0,
               ACCENT if acc else WHITE, v, ACCENT_GLOW if acc else 0.0, ox, oy)
    return F


def roi(act):
    """当前同屏句子的绘制区（整帧坐标）：列 + scrim，只在这一块里做浮点运算。"""
    xa = min(min(r['box'][0] for r in act), COL_R - SCRIM_W - 2)   # 含整条 scrim 的起点
    xb = W                                          # scrim 一路铺到画右边缘（1792 右侧保持峰值）
    ya = min(r['box'][1] for r in act) - 48
    yb = max(r['box'][3] for r in act) + 40
    return max(0, int(xa)), max(0, int(ya)), min(W, int(xb)), min(H, int(yb))


def draw(fr, f):
    """全片唯一字幕叠加点：fr（uint8 或 float32 0..1）+ 帧号 → 叠加后的帧。"""
    if not enabled():
        return fr
    t = float(f) / FPS
    act = active(t)
    if not act:
        return fr
    u8 = fr.dtype == np.uint8
    if u8:                                          # 只把字幕区转成浮点（约 1/6 画面），整帧不搬
        ox, oy, ex, ey = roi(act)
        sub = fr[oy:ey, ox:ex]
        F = sub.astype(np.float32) / 255.0
        for r in act:
            F = _sentence(F, r, t, ox, oy)
        np.multiply(F, 255.0, out=F)
        np.add(F, 0.5, out=F)
        np.clip(F, 0, 255, out=F)
        sub[...] = F.astype(np.uint8)
        return fr
    F = np.array(fr, np.float32, copy=True)
    for r in act:
        F = _sentence(F, r, t)
    return F


# ---------------------------------------------------------------- 报告 / 自测
def spec_table():
    rows = ['| 行号 | 句 | 字数 | 列数 | 字号 | 列顶→列底 | 重音字 | 入场 | 淡出起→收 |',
            '|---|---|---|---|---|---|---|---|---|']
    for r in lines():
        bottom = r['pos'][-1]['y'] + r['size'] / 2.0
        flag = '' if bottom <= H - BAR else f' ✗越黑边{int(round(bottom - (H - BAR)))}px'
        acc = r['chars'][r['accent']]['ch'] if r['n'] else ''
        rows.append('| %d | %s | %d | %d | %d | 300→%d%s | %s(%s) | %.2f | %.2f→%.2f |' % (
            r['line'], r['text'].replace(' ', '·'), r['n'], r['ncol'], r['size'], int(round(bottom)), flag,
            acc, r['accent_src'], r['t_on'], r['t_out'], r['t_off']))
    return '\n'.join(rows)


def _selftest(frames):
    """python3 units/lyric_uni.py [帧…]：报耗时 + 存 /tmp/lu_<帧>.png"""
    import time
    from PIL import Image
    L = lines()
    print('sentences=%d  竖排单列 x_right=%d  col_top=%d  max/col=%d' % (len(L), COL_R, COL_TOP, MAX_PER_COL))
    over = [(r['line'], int(round(r['y_bot'] - (H - BAR)))) for r in L if r['y_bot'] > H - BAR]
    print('越过下方黑边的句子(行号, 越界px):', over)
    os.environ['LYRIC_UNI'] = '1'
    for f in frames:
        act = active(f / FPS)
        base = np.full((H, W, 3), 0.16, np.float32)
        t0 = time.monotonic()
        out = draw(base, f)
        dt = time.monotonic() - t0
        print('frame %d  t=%.2f  句=%s  耗时 %.1f ms' % (f, f / FPS, [r['text'] for r in act], dt * 1000))
        Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save('/tmp/lu_%d.png' % f)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'table':
        print(spec_table())
    else:
        _selftest([int(x) for x in sys.argv[1:]] or [560, 2360, 4000])
