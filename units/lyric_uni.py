"""units/lyric_uni.py —《谁定正邪》全片唯一字幕层（竖排单列 · 右对齐 · 逐字墨显）

为什么有这个文件
    全片 5 个摄制组各写了一套字幕层：A 段主词 150–240px + 余字 70–96px 横排 + 暗衬条、
    B 组自己一套、副歌一右侧竖排 x=1752 / 底部横排 y=850 两套、C 段 fly 飘字碎裂出场、
    D 段宣纸风、E 段又一套。位置与风格全不一致 → 本模块是**唯一**字幕层，位置/字号/颜色/
    衬底/动效只有一套参数，不分段落。各组字幕层用 LYRIC_UNI=1 关掉（各文件只加一行守卫）。

规格（2026-11-09 用户定稿，实现即照此，不许自己另设计）
    1 位置     竖排单列、右对齐；列右缘 x=1792（距右边 128px），列顶 y=160；不横排、不居中。
               可用高 = 960−160 = 800px，上下 120px 黑边一个字都不许碰（2026-11-09 19:2x 组长改：列顶 300→160）。
    2 换列     每列最多 10 字；超过 10 字拆两列，第二列在**左**，列间距 96px，整体右对齐。
    3 字号     思源宋 Bold；列内字数 ≤6 → 84px，7–8 → 76px，9–10 → 68px；行距 1.08。
               再夹一道几何上限：字号 ≤ (800 / 列内字数) / 1.08（保证列高 ≤ 800px，长句不会长出画面）。
    4 颜色     暖白 #F2F0EC；重音字（每句至多一个）朱红 #B3261A + 极轻朱晕。
               无描边、无朱印、无手写笔触 —— 它是字幕，不是道具。
    5 衬底     竖条渐变 scrim，band 按**本句实际占用的列范围**算（2026-11-09 19:3x 组长改）：
                 x_from = 最左列左缘 − 120px，x_to = 1792 + 40px，区间内线性渐变，峰值 alpha 0.42；
               按画面亮度自适应（背后中位亮度 ≤0.10 则减半到 0.21，防压死暗部）；
               亮底破例（组长批准，可读性优先）：背后中位亮度 ≥0.45 → 峰值 0.62 + 1px 极暗半透明描边
               （黑 ×0.35，只在亮底触发，用中位亮度平滑过渡，不逐帧抖）。不超出黑边。
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

几何自检
    tools/lyric_uni_cmp.py geom —— 56 句 × 3 帧（字头 / 中 / 末字后 2 帧）画在黑底上，
    断言 rows[0:120] 与 rows[960:1080] 全黑（max < 0.02），任何一句撞黑边就报错。
    实测：56 句全部通过（最靠下的一句列底 894px，离黑边还有 66px；最靠上 148px，离上黑边 28px）。
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
COL_TOP = 160                 # 1 列顶（2026-11-09 19:2x 组长改：300 → 160）
COL_BOT = H - BAR             # 1 可排到 960（下黑边上沿）
MAX_PER_COL = 10              # 2 每列最多 10 字
COL_GAP = 96                  # 2 第二列往左的列间距
LEAD = 1.08                   # 3 行距
TIERS = ((6, 84), (8, 76), (10, 68))   # 3 (列内字数上限, 字号)

WHITE = (0xF2 / 255.0, 0xF0 / 255.0, 0xEC / 255.0)    # 4 暖白 #F2F0EC
ACCENT = (0xB3 / 255.0, 0x26 / 255.0, 0x1A / 255.0)   # 4 朱红 #B3261A
ACCENT_GLOW = 0.16            # 4 极轻朱晕（additive，占比很小）

SCRIM_PAD_L = 120             # 5 band 左端 = 最左列左缘 − 120px
SCRIM_PAD_R = 40              # 5 band 右端 = 1792 + 40px
SCRIM_A = 0.42                # 5 峰值 alpha（暗底/中性底）
SCRIM_A_BRIGHT = 0.62         # 5 亮底峰值（组长批准破例）
SCRIM_DARK = (0.10, 0.22)     # 5 暗底：背后中位亮度 ≤0.10 → 峰值减半，≥0.22 → 全量
SCRIM_BRIGHT = (0.40, 0.50)   # 5 亮底：中位亮度 0.40→0.50 平滑升到 0.62（0.45 在中点，避免逐帧跳变）
OUTLINE_A = 0.35              # 5 亮底 1px 极暗描边（黑 ×0.35），只在亮底出现

IN_DUR, IN_LEAD = 0.10, 0.06  # 6 逐字墨显：0.10s，起点 = 字头 −0.06s
OUT_HOLD, OUT_DUR = 0.55, 0.28  # 6 末字后 0.55s 起淡出，0.28s 时长
GAP_HOLD = 2.0                # 6 「衔接不留空档」的适用范围：与下一句的间隔 ≤2.0s 时保持到下一句起；
                              #   超长器乐空档（86.2→89.4 = 3.5s 等）按 0.55s 正常退场

# 7 关键词让位：要把字让给画内道具的用 (行号0基, 字序)，默认空。
#   默认空 = 全画；LYRIC_UNI_OUT=1 时自动吃 out/props_dev/hidden_slots.json（props 组已抽走的 45 个字），
#   并在打开时校验每个槽位与 lyrics.json 逐字对得上（对不上就报错，避免两套规则打架）。
OUT_CHARS = set()
HIDDEN_SLOTS = None


def hidden_slots():
    """props 组抽走的字：out/props_dev/hidden_slots.json（line 是 1 基句号，idx 是 0 基字序）。"""
    global HIDDEN_SLOTS
    if HIDDEN_SLOTS is None:
        path = os.path.join(ROOT, 'out', 'props_dev', 'hidden_slots.json')
        try:
            with open(path, encoding='utf-8') as fh:
                HIDDEN_SLOTS = json.load(fh)
        except OSError:
            HIDDEN_SLOTS = []
    return HIDDEN_SLOTS


def out_chars(validate=True):
    """(行号0基, 字序) 集合：由 hidden_slots.json 生成；validate 时逐条核对字与句。"""
    L = lines()
    out = set()
    bad = []
    for it in hidden_slots():
        line0 = int(it['line']) - 1          # 文件里是 1 基句号
        k = int(it['idx'])
        r = L[line0] if 0 <= line0 < len(L) else None
        if r is None or k >= r['n'] or r['chars'][k]['ch'] != it['ch'] or r['text'].replace(' ', '') != it['text'].replace(' ', ''):
            bad.append(it)
            continue
        out.add((line0, k))
    if validate and bad:
        raise ValueError('hidden_slots.json 与 lyrics.json/align 对不上: %r' % bad[:3])
    return out


# 画面内（in-scene）已经有字的词：字幕层要把这些字**留空**（不删画面里的字）。
# 来源 = tools/lyric_uni_cmp.py audit 查出来的「LYRIC_UNI=1 时仍在画字」的站点，逐站点人工分类：
#   键 = (文件, 行号)；值 = (句号0基, 画面里已有的词, 分类说明)
# 分类口径：这类字是**画面元素**（刻/印/烧/散字/巨字），不是字幕层 —— 用户 2026-11-09 明确「2:43 那个巨大的
# 「什么」是画面元素、做得很好、不要删」。所以不关它，改由字幕留空，避免同一个词出现两次。
# hidden_slots.json 里已登记的字不在这里重复（那批由 props 组负责）。
IN_SCENE = {
    ('sec_b_pre1.py', 471):   (10, '我不信', '书法散字压在右上天幕（志莽/毛草，190/150/170px），镜内演出'),
    ('sec_b_pre1.py', 943):   (11, '滚烫',   '刀身烧字（burn_in 120px），用户点名的「滚烫既是歌词又是刻字」'),
    ('sec_b_verse2.py', 1627): (24, '不问',   '书法散字（scatter_stack），镜内演出'),
    ('sec_d_bridge.py', 914): (43, '陪葬',   '宣纸烧字（burn_in），镜内演出'),
    ('sec_d_bridge.py', 311): (40, '什么叫', '纸面墨洇巨字（2:43 用户点名保留的画内元素）'),
    ('sec_d_bridge.py', 282): (40, '忍',   '纸面「忍」宋体巨字砸下（墨洇，镜内演出）'),
    ('sec_d_bridge.py', 353): (40, '让',   '纸面「让」170px 墨字落定（镜内演出，落在字幕带里）'),
    ('sec_e_final_outro.py', 284): (48, '刀不放', '拳上朱印（stamp_seal 118–132px），画内道具'),
    ('chorus1.py', 866):      (17, '是非对错', '朱印阵（seal_grid 540px），画内道具'),
    ('sec_e_final_outro.py', 359): (49, '天理昭彰', '鎏金 3D 巨字（匾额，镜内演出）'),
}

# 场景高光（枪尖/盔缨/刀身高光）在字幕带里也会被「像字」检测抓到 —— 人工核对过的白名单，
# 只用于 dupcheck 归因，不参与留空。键 = 帧号，值 = [(x, y, w, h, 说明)]
SCENE_OK = {
    646:  [(1533, 397, 32, 47, '军阵枪尖高光'), (1750, 405, 29, 29, '枪尖高光')],
    4108: [(1608, 422, 63, 107, '戟刃/盔缨'), (1518, 329, 31, 83, '盔缨'), (1567, 470, 36, 35, '枪尖')],
}

# 画面内字在字幕带里的实测位置（这几处不走 typo.compose，审计抓不到，用实测框归因；只用于 dupcheck）
IN_SCENE_BOX = {
    5011: [(1592, 721, 113, 167, '让（D 纸面墨字，字幕已留空）')],
    5975: [(1500, 318, 205, 385, '天理昭彰（E 鎏金巨字，字幕已留空）')],
    5863: [(1500, 391, 118, 215, '刀不放（E 拳上朱印，字幕已留空）')],
}
IN_SCENE_HIDE = set()          # 由 _maybe_out() 从 IN_SCENE 派生：(句号0基, 字序)


def in_scene_hide(validate=True):
    """IN_SCENE → 要留空的 (行号0基, 字序) 集合；并核对每个词确实是该句的连续子串。"""
    L = lines()
    out, bad = set(), []
    for (fn, line0), (li, w, why) in IN_SCENE.items():
        r = L[li]
        t = ''.join(c['ch'] for c in r['chars'])
        k = t.find(w)
        if k < 0:
            bad.append((fn, line0, li, w, t))
            continue
        out |= {(li, k + i) for i in range(len(w))}
    if validate and bad:
        raise ValueError('IN_SCENE 与歌词对不上: %r' % bad[:3])
    return out


def _maybe_out():
    """留空两档：
    1) IN_SCENE（画面内已经有这个字）→ LYRIC_UNI=1 就留空，否则同一个词会出现两次；
    2) hidden_slots.json（props 组抽走、但还没接进画面）→ 只有 LYRIC_UNI_OUT=1 才留空，
       否则会露出纯空位。
    """
    global OUT_CHARS, IN_SCENE_HIDE
    if not IN_SCENE_HIDE:
        IN_SCENE_HIDE = in_scene_hide()
    if os.environ.get('LYRIC_UNI_OUT') == '1' and not OUT_CHARS:
        OUT_CHARS = out_chars()
    return OUT_CHARS | IN_SCENE_HIDE

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


_RC = {}


def glyph_ring(ch, size):
    """字形外侧 1px 环（描边用）：dilate(二值) − 二值，8 邻域 3×3。"""
    key = (ch, int(size))
    g = _RC.get(key)
    if g is not None:
        return g
    a = glyph(ch, size)
    b = (a > 0.35).astype(np.uint8)
    d = cv2.dilate(b, np.ones((3, 3), np.uint8))
    g = np.clip(d.astype(np.float32) - b.astype(np.float32), 0.0, 1.0)
    _RC[key] = g
    return g


def char_size(n):
    """列内字数 → 字号（3 号规则）+ 几何夹紧 ≤ (可用高 / 字数) / 行距。"""
    px = TIERS[-1][1]
    for lim, p in TIERS:
        if n <= lim:
            px = p
            break
    avail = (COL_BOT - COL_TOP) / float(LEAD)          # 800 / 1.08
    return int(min(px, avail / max(1, n) + 1e-6))


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
        left = min(p['x'] for p in pos) - r['size'] / 2.0
        r['left'] = left
        r['band'] = (left - SCRIM_PAD_L, COL_R + SCRIM_PAD_R)     # 5：按本句实际列范围算
        r['box'] = (int(left) - 34, int(COL_TOP), COL_R + SCRIM_PAD_R + 4, int(r['y_bot']) + 14)
    return out


def lines():
    global _LINES
    if _LINES is None:
        _LINES = _build()
    return _LINES


def active(t):
    return [r for r in lines() if r['t_on'] <= t < r['t_off']]


# ---------------------------------------------------------------- 重复出字审计（LYRIC_UNI_AUDIT=1）
# 为什么需要：守卫是「按站点」加的，容易漏 —— B 段的歌词不走 T.place，还走 T.ink_bleed_in / T.warm /
# T.vertical_column / T.compose 等十几条路径。审计模式把所有「吃 fr 的 typo 绘制函数」包一层，
# 记录 (调用者文件:行号, 函数, 文本)，于是「LYRIC_UNI=1 时还有谁在画字」是查出来的、不是想出来的。
_AUDIT = []


def audit_start():
    global _AUDIT
    if _AUDIT:
        return _AUDIT
    import inspect
    import traceback
    import typo as _T
    names = []
    for nm in dir(_T):
        fn = getattr(_T, nm)
        if not callable(fn) or nm.startswith('_'):
            continue
        try:
            ps = list(inspect.signature(fn).parameters)
        except (TypeError, ValueError):
            continue
        if ps and ps[0] in ('fr', 'A', 'B'):
            names.append(nm)
    for nm in names:
        fn = getattr(_T, nm)

        def make(nm, fn):
            def wrap(*a, **kw):
                try:
                    st = traceback.extract_stack(limit=8)[-2]
                    for cand in reversed(traceback.extract_stack(limit=8)[:-1]):
                        if os.path.basename(cand.filename) not in ('typo.py', 'lyric_uni.py'):
                            st = cand
                            break
                    txt = ''
                    for v in list(a[1:4]) + list(kw.values()):
                        if isinstance(v, str):
                            txt = v
                            break
                    size = next((v for v in list(a[2:6]) + list(kw.values())
                                 if isinstance(v, (int, float)) and 8 <= v <= 900), None)
                    _AUDIT.append(dict(f=os.path.basename(st.filename), line=st.lineno, fn=nm,
                                       txt=txt, size=size))
                except Exception:
                    pass
                return fn(*a, **kw)
            wrap.__name__ = nm
            wrap.__doc__ = fn.__doc__
            return wrap
        setattr(_T, nm, make(nm, fn))
    return _AUDIT


def audit_take():
    out, _AUDIT[:] = list(_AUDIT), []
    return out


# ---------------------------------------------------------------- 歌词判定（B 组守卫用）
_PUNCT = set('，。、！？；：,.!?;:·…—「」『』“”‘’（）()《》 \t')


def _clean(text):
    return ''.join(c for c in str(text) if c not in _PUNCT)


_LYRIC_CHARS = None
_LYRIC_SUB = None


def _lyric_sets():
    global _LYRIC_CHARS, _LYRIC_SUB
    if _LYRIC_CHARS is None:
        _LYRIC_CHARS = set()
        _LYRIC_SUB = set()
        for r in lines():
            t = _clean(r['text'])
            _LYRIC_CHARS |= set(t)
            _LYRIC_SUB.add(t)
            for i in range(len(t)):
                for j in range(i + 2, min(len(t), i + 16) + 1):
                    _LYRIC_SUB.add(t[i:j])
    return _LYRIC_CHARS, _LYRIC_SUB


def is_lyric(text):
    """这段文本是否属于歌词（B 组散在各镜头里的 T.place 守卫用）。

    - 去空格/标点后长度 ≥2：是 56 句之一的子串 → True
    - 长度 1：该字在歌词里出现过 → True（★ 单字最模糊：既可能是字幕也可能是画内刻字/压印，
      接线的 7 处逐点判过、有争议的在 out/lyric_uni/outchars_table.md 里列了人工确认清单）
    - 空/None → False
    """
    t = _clean(text)
    if not t:
        return False
    ch, sub = _lyric_sets()
    if len(t) == 1:
        return t in ch
    return t in sub or t in ch


# ---------------------------------------------------------------- 衬底
def _ssl(lo, hi, x):
    if x <= lo:
        return 0.0
    if x >= hi:
        return 1.0
    t = (x - lo) / (hi - lo)
    return t * t * (3.0 - 2.0 * t)


def _scrim(F, xf, y0, xt, y1, ox=0, oy=0):
    """竖条渐变 scrim（5 号规则）。band = [xf, xt]（整帧坐标，xf = 最左列左缘 −120，xt = 1792+40）。

    F 是整帧的子区（左上角 = (ox, oy)）。返回 (F, 亮底系数 k) —— k 拿去决定要不要上 1px 描边。
    """
    h, w = F.shape[:2]
    xa, xb = max(ox, int(xf)), min(ox + w, int(xt))
    ya, yb = max(oy, int(y0), BAR), min(oy + h, int(y1), H - BAR)
    if xb <= xa or yb <= ya:
        return F, 0.0
    reg = F[ya - oy:yb - oy, xa - ox:xb - ox]
    L = float(np.median(reg[..., 0] * 0.299 + reg[..., 1] * 0.587 + reg[..., 2] * 0.114))
    lo, hi = SCRIM_DARK
    kd = _ssl(lo, hi, L)                             # 0 = 很暗（减半）, 1 = 非暗底（全量）
    lo2, hi2 = SCRIM_BRIGHT
    kb = _ssl(lo2, hi2, L)                           # 0 = 非亮底, 1 = 亮底（0.45 落在中点）
    a = (SCRIM_A * (0.5 + 0.5 * kd)) * (1.0 - kb) + SCRIM_A_BRIGHT * kb
    xs = np.arange(xa, xb, dtype=np.float32)
    ax = np.clip((xs - float(xf)) / max(1.0, float(xt) - float(xf)), 0.0, 1.0) * a
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
    return F, kb


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
    _hide = OUT_CHARS | IN_SCENE_HIDE              # 7：留空集合（画面内已有的字 + props 抽走的字）
    xf, xt = r['band']                             # 5：band = 本句列范围 −120 / +40
    F, kb = _scrim(F, xf, y0 - 48, xt, y1 + 40, ox, oy)
    out_a = OUTLINE_A * kb                         # 亮底才有描边，且随中位亮度平滑淡入
    for key in r['pos']:
        if (r['line'], key['k']) in _hide:         # 7 让位：留空占位，不画（IN_SCENE + props 两档）
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
        gx = key['x'] - a.shape[1] / 2.0
        gy = key['y'] - a.shape[0] / 2.0
        if out_a > 0.0:                            # 5：1px 极暗半透明描边（只在字形外侧）
            ring = glyph_ring(key['ch'], r['size'])
            _paste(F, ring, gx, gy, (0.0, 0.0, 0.0), v * out_a, 0.0, ox, oy)
        _paste(F, a, gx, gy,
               ACCENT if acc else WHITE, v, ACCENT_GLOW if acc else 0.0, ox, oy)
    return F


def scrim_info(fr, f):
    """调试用：量该帧字幕区的（背后中位亮度, scrim 峰值, 描边不透明度）—— 验证亮底描边不闪。
    fr 传 uint8/float 成品帧（叠字幕之前的底帧）。"""
    t = float(f) / FPS
    act = active(t)
    if not act:
        return None
    r = act[0]
    F = (fr.astype(np.float32) / 255.0) if fr.dtype == np.uint8 else np.asarray(fr, np.float32)
    xf, xt = r['band']
    x0, x1 = max(0, int(xf)), min(W, int(xt))
    y0, y1 = max(BAR, int(r['box'][1]) - 48), min(H - BAR, int(r['box'][3]) + 40)
    reg = F[y0:y1, x0:x1]
    L = float(np.median(reg[..., 0] * 0.299 + reg[..., 1] * 0.587 + reg[..., 2] * 0.114))
    lo, hi = SCRIM_DARK
    kb_ = _ssl(*SCRIM_BRIGHT, L)
    a = (SCRIM_A * (0.5 + 0.5 * _ssl(lo, hi, L))) * (1.0 - kb_) + SCRIM_A_BRIGHT * kb_
    left_edge = int(r['left'])
    frac = (left_edge - xf) / max(1.0, xt - xf)   # 最左列左缘落在 band 的比例（=scrim 峰值占比）
    return dict(line=r['line'], band=(int(xf), int(xt)), L=L, peak=a,
                outline=OUTLINE_A * kb_, left_frac=frac, left_alpha=a * frac)


def roi(act):
    """当前同屏句子的绘制区（整帧坐标）：列 + scrim，只在这一块里做浮点运算。"""
    xa = min(r['band'][0] for r in act) - 2         # 含整条 scrim 的起点
    xb = max(r['band'][1] for r in act) + 2         # 含 scrim 的右端（1792+40）
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
    _maybe_out()
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
