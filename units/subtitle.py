"""全片统一歌词字幕（第五轮用户要求 #52：歌词放居中下方字幕位置）。
在 render_sprite_full.frame 的成品帧上叠加。时间轴 = align.log 逐句起止（56 句），逐字时刻 = align.json words。
环境变量 SUB_OFF=1 关闭。

r6-SUB（用户 11-10 15:28「底部的字幕好丑，能做成之前竖版歌词那种风格吗」）：SUB_STYLE 切换风格
  SUB_STYLE=cur   （默认，现状）下黑边内居中、思源宋体 Medium、白字 + 柔阴影、逐句淡入淡出。
  SUB_STYLE=ink_h  旧竖版歌词风格搬到底部横排：马善政楷书（lib/typo 'kai'），逐字按演唱时刻笔序书写
                   （先铺整字淡墨影 → 笔锋湿墨晕开 → 行笔末段飞白 → 落笔墨点），关键字朱红放大 + 金描边 + 朱红外发光，
                   虚字缩小、大小错落、底边对齐；暖白字 + 墨色晕影；句尾墨散（淡出 + 晕开）。全部落在 y 960–1080 下黑边内。
  SUB_STYLE=ink_v  同上风格，改为画面右侧竖排（右起列，>8 字分两列，右列先唱），不画底部字幕。
  SUB_STYLE=old    = ink_h 的别名（「旧版风格」）。
  SUB_STYLE=serif_h（r6-SUB2，用户 16:08 拍板，**默认**）「我要这种字体和大小，但是横向排版，并且保留之前做的那些文字动画，不需要排版，一行就行」：
                   字形照 lyric3 整句规格（思源宋 SemiBold 62px、暖白、每句至多一个朱红关键字、金只给「天亮」、STYLE 阴影/辉光），
                   全句同一字号、横排一行居中、字距 0.22em，全落在下黑边（y 960–1080）；动画沿用 ink_h（逐字按演唱时刻笔序书写 +
                   整字淡墨影，提前 0.1s 起笔、0.32s 写完，写完收为干净宋体字形；句尾墨散淡出）。
"""
import os, re, json, math, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT = '/workspace/work/mv'
FONT = ROOT + '/fonts/NotoSerifSC-Medium.otf'
SIZE, Y_C = 38, 1020          # 下黑边 120px（1080-120…1080），字幕中心 y=1020
FADE = 0.14
LINES = []
for l in open(ROOT + '/align.log', encoding='utf-8'):
    m = re.match(r'^([0-9.]+) ([0-9.]+)\s+(.+)$', l.strip())
    if m: LINES.append((float(m.group(1)), float(m.group(2)), m.group(3).strip()))
_C = {}


def style():
    s = os.environ.get('SUB_STYLE', 'serif_h').strip().lower()
    return 'ink_h' if s == 'old' else s


def _layer(txt):
    if txt in _C: return _C[txt]
    f = ImageFont.truetype(FONT, SIZE)
    txt_sp = txt.replace(' ', '\u3000')
    w = int(f.getlength(txt_sp)) + 40; h = SIZE + 30
    a = Image.new('L', (w, h), 0); ImageDraw.Draw(a).text((20, 10), txt_sp, font=f, fill=255)
    sh = a.filter(ImageFilter.GaussianBlur(4))
    _C[txt] = (np.asarray(a, np.float32) / 255, np.asarray(sh, np.float32) / 255)
    return _C[txt]


def current(t):
    for t0, t1, s in LINES:
        if t0 - FADE <= t < t1 + 0.25 + FADE:
            k = min(1, (t - (t0 - FADE)) / FADE, (t1 + 0.25 + FADE - t) / FADE)
            return s, max(0.0, k)
    return None, 0


def apply(img, t):
    if os.environ.get('SUB_OFF'): return img
    st = style()
    if st in ('ink_h', 'ink_v'): return ink_apply(img, t, st)
    if st == 'serif_h': return serif_apply(img, t)
    s, k = current(t)
    if not s or k <= 0: return img
    a, sh = _layer(s)
    h, w = a.shape; x0 = (img.shape[1] - w) // 2; y0 = Y_C - h // 2
    out = img.astype(np.float32)
    reg = out[y0:y0 + h, x0:x0 + w]
    reg *= (1 - 0.75 * k * sh)[..., None]
    reg[:] = reg * (1 - 0.93 * k * a)[..., None] + np.array([238, 232, 222], np.float32) * (0.93 * k * a)[..., None]
    return out.clip(0, 255).astype(np.uint8)


# ===================================================================== r6-SUB 墨书风格（ink_h / ink_v）
# 风格要素取自 #53 删掉的旧竖版歌词（sec_a V09「谁把人命/装进天平」、V14「每一次拔刀」、A 段 LY2、sec_b P03「谁配画」）：
#   字体 MaShanZheng 楷（'kai'）/ ZhiMangXing 行（'xing'）；typo.brush_glyph 笔序书写 + BG 整字淡墨影防错读；
#   白字 (0.96,0.93,0.86) shadow 0.85 σ12 glow 0.15；朱红 (0.98,0.22,0.12) 金描边 2px + 朱红外发光 0.35。
INK_FONT = os.environ.get('SUB_INK_FONT', 'kai')
WHITE = (0.96, 0.93, 0.86)
REDC = (0.98, 0.22, 0.12)
# 关键字：按优先级取每句最多 2 个（同字只取首个）
RED_PRI = '血刀骨命罪杀邪墙锋权扛判答闯伪葬黑撕天'
RED_OVR = {                     # 个别句手定（避免自动规则挑到不该红的字）
    '五百重甲拦不住一道寒光': '寒光',
    '谁在高处定对错罪状': '罪',
    '谁把人命装进天平里称量': '命',
    '谁配写生死簿谁配画善恶框': '死框',
    '什么叫以一人换千人理所应当': '千',
    '对就是对错就是错何须伪装': '伪',
    '世间从来没有什么天理昭彰': '天',
    '若这世道黑白颠倒': '黑',
    '什么叫大局什么叫牺牲什么叫忍让': '牺牲',
    '牺牲多少才算够分量': '牺牲',
    '被牺牲的人可曾有机会反抗': '反抗',
    '谁定好规则谁写好剧本提纲': '纲',
    '谁的正义成了交易的暗箱': '暗箱',
    '世人教我顾全大局退让': '退让',
    '那就劈开它看个天亮': '劈',
    '这一刀就是我的回答': '刀',
    '这一刀就是我的正道沧桑': '刀',
}
SMALL = set('之的在了也过是就把被又来为么叫个它都还着与而且所这那')   # 虚字缩小（旧版「长夜 压在我 刀锋」的大小节奏）
_WT = None
_INKC = {}


def _wtimes():
    """每句逐字演唱时刻（align.json words，多字词内均分）。"""
    global _WT
    if _WT is None:
        _WT = {}
        try:
            d = json.load(open(ROOT + '/align.json', encoding='utf-8'))
            for (t0, t1, s), seg in zip(LINES, d['segments']):
                cs = []
                for w in seg['words']:
                    ww = w['word'].strip()
                    for i, c in enumerate(ww): cs.append(w['start'] + (w['end'] - w['start']) * i / max(1, len(ww)))
                if len(cs) == len(s.replace(' ', '')) and abs(cs[0] - t0) < 1.0: _WT[t0] = cs     # 按句起点索引（副歌重复句文字相同）
        except Exception:
            pass
    return _WT


def _reds(s):
    if s in RED_OVR: return set(RED_OVR[s])
    out = []
    for c in RED_PRI:
        if c in s and c not in out: out.append(c)
        if len(out) >= 2: break
    return set(out)


def _line_info(t):
    for t0, t1, s in LINES:
        if t0 - 0.3 <= t < t1 + 0.6:
            return t0, t1, s
    return None


def _plan(s, mode):
    """排版：[(ch, x, y, size, red, idx)]，idx = 去空格后的字序号。"""
    if (s, mode) in _INKC: return _INKC[(s, mode)]
    reds = _reds(s); P = []
    if mode == 'ink_h':
        n = len(s.replace(' ', ''))
        B = 74 if n <= 10 else (68 if n <= 13 else 62)                 # 基础字号；最长 16 字（16×0.96×62≈950px）
        sz = [(round(B * 1.24) if c in reds else round(B * 0.78) if c in SMALL else B) if c != ' ' else 0 for c in s]
        adv = [z * 0.96 if c != ' ' else B * 0.7 for c, z in zip(s, sz)]
        x = 960 - sum(adv) / 2; base = 1054; i = 0                     # 底边对齐 y≈1054（最大字 92px → 顶 ≈962，黑边 960–1080 内）
        for c, z, a in zip(s, sz, adv):
            if c != ' ':
                P.append((c, x + a / 2, base - z * 0.5, z, c in reds, i)); i += 1
            x += a
    else:
        parts = [p for p in s.split(' ') if p]
        if len(parts) == 1 and len(parts[0]) > 10:                       # 长句从中间断成两列（断点避开虚字开头）
            p0 = parts[0]; k = (len(p0) + 1) // 2
            for d in (0, 1, -1, 2, -2):
                if p0[k + d] not in SMALL: k += d; break
            parts = [p0[:k], p0[k:]]
        cols = parts if len(parts) <= 2 else [''.join(parts[:len(parts) // 2]), ''.join(parts[len(parts) // 2:])]
        nmax = max(len(c) for c in cols)
        B = min(92, int(800 / (nmax * 1.04)))
        i = 0
        for ci, ctext in enumerate(cols):
            cx = 1770 - ci * (B * 1.35)
            y = 170 + ci * B * 0.6                                       # 第二列下错半格（旧版「谁把人命/装进天平」错落）
            for c in ctext:
                z = round(B * 1.2) if c in reds else round(B * 0.82) if c in SMALL else B
                y += z * 0.51
                P.append((c, cx, y, z, c in reds, i)); i += 1
                y += z * 0.51
    _INKC[(s, mode)] = P
    return P


def ink_apply(img, t, mode):
    info = _line_info(t)
    if info is None: return img
    import typo as T
    t0, t1, s = info
    wt = _wtimes().get(t0)
    n = len(s.replace(' ', ''))
    if wt is None: wt = [t0 + (t1 - t0) * 0.85 * i / max(1, n) for i in range(n)]
    tend = t1 + 0.25
    ko = 1.0 - min(1.0, max(0.0, (t - tend) / 0.3))                  # 句尾墨散
    if ko <= 0: return img
    P = _plan(s, mode)
    L = T.Layer(); Lr = T.Layer()
    for ch, x, y, z, red, i in P:
        p = min(1.0, max(0.0, (t - (wt[i] - 0.10)) / 0.32))           # 每字 0.32s 写完，提前 0.1s 起笔
        if p <= 0: continue
        g = T.brush_glyph(ch, INK_FONT, z, p, seed=17 + i)
        if p < 0.999:                                                  # 整字淡墨影（BG 写法，防半笔错读）
            gf = T.brush_glyph(ch, INK_FONT, z, 1.0, seed=17 + i)
            g = np.maximum(g, gf * 0.55 * (1 - (1 - min(1.0, p * 3.0)) ** 3))
        if ko < 1:
            import cv2
            g = cv2.GaussianBlur(g, (0, 0), 0.5 + 3.0 * (1 - ko)) * ko  # 墨散：晕开 + 淡出
        (Lr if red else L).paste(g, x, y, REDC if red else WHITE)
    fr = img.astype(np.float32) * (1 / 255)
    fr = T.compose(fr, L, shadow=0.85, shadow_sigma=12, glow=0.15)
    fr = T.compose(fr, Lr, shadow=0.9, shadow_sigma=12, outline=2, outline_color=(1.0, 0.78, 0.40), glow=0.35, glow_color=(0.9, 0.15, 0.06))
    return (fr.clip(0, 1) * 255 + 0.5).astype(np.uint8)


# ===================================================================== r6-SUB2 宋体横排（serif_h，默认）
# 字形/颜色/阴影 = units/lyric3.py 整句规格；动画 = ink_h 的笔序书写 + 墨散。
SF_FONT, SF_SIZE, SF_TRACK = 'serif_sb', 62, 0.22                 # lyric3 F_SENT / S_SENT / TRACK_H
SF_Y = 1020                                                        # 下黑边 960–1080 正中（62px 字墨 ≈992–1048）
SF_WHITE = (0.97, 0.94, 0.88)                                      # lyric3 WHITE
SF_RED = (0.84, 0.10, 0.07)                                        # lyric3 RED_T
SF_GOLD = (1.0, 0.78, 0.42)                                        # lyric3 GOLD_T
SF_STYLE = dict(shadow=0.72, shadow_sigma=20, outline=0, glow=0.20, glow_sigma=14)   # lyric3 STYLE
SF_GOLDW = '天亮'                                                  # 金只给光字（「那就劈开它看个天亮」）
SF_RED1 = {                     # RED_OVR 是两字词的句子：朱红只取 1 字（lyric3「每句至多一个朱红关键字」）
    '五百重甲拦不住一道寒光': '寒',
    '谁配写生死簿谁配画善恶框': '死',
    '什么叫大局什么叫牺牲什么叫忍让': '牺',
    '牺牲多少才算够分量': '牺',
    '被牺牲的人可曾有机会反抗': '抗',
    '谁的正义成了交易的暗箱': '暗',
    '世人教我顾全大局退让': '退',
    '血未冷 骨未凉': '骨',                                         # 用户 16:08 参考图：「骨未凉」骨字朱红
}
SF_MAXW = 1600                                                     # 左右安全边距 160；超宽则全片统一缩字号
_SFC = {}


def _sf_fonts():
    import typo as T
    for k, f in (('serif_sb', 'SemiBold'),):
        if k not in T.FONTS: T.FONTS[k] = ROOT + f'/fonts/NotoSerifSC-{f}.otf'
    return T


def _sf_size():
    """全片统一字号：62px，最长句放不下时统一缩小（现有 56 句最长 15 字 ≈1121px，不缩）。"""
    if 'size' not in _SFC:
        n = max(len(s) for _, _, s in LINES)
        z = SF_SIZE
        while z > 30 and z * (1 + SF_TRACK) * (n - 1) + z > SF_MAXW: z -= 2
        _SFC['size'] = z
    return _SFC['size']


def _sf_red(s):
    if s in SF_RED1: return SF_RED1[s]
    g = SF_GOLDW if SF_GOLDW in s else ''
    r = [c for c in s if c in _reds(s) and c not in g]
    return r[0] if r else ''


def _sf_plan(s):
    """一行居中：[(ch, x, y, color, idx)]，字距 0.22em。"""
    if s in _SFC: return _SFC[s]
    z = _sf_size(); adv = z * (1 + SF_TRACK)
    red = _sf_red(s); gold = SF_GOLDW if SF_GOLDW in s else ''
    xs = []; x = 0.0                                                # 空格占 0.6 格（整格留白偏大，读成两句）
    for c in s:
        if c == ' ': x += adv * 0.6; continue
        xs.append(x); x += adv
    x0 = 960 - xs[-1] / 2; P = []
    for i, (c, xx) in enumerate(zip(s.replace(' ', ''), xs)):
        colr = SF_GOLD if c in gold else SF_RED if c == red else SF_WHITE
        P.append((c, x0 + xx, SF_Y, colr, i))
    _SFC[s] = P
    return P


def _sf_glyph(ch, z, p, seed):
    """宋体字形上的笔序书写：笔序场取 typo.brush_glyph（湿墨前沿 + 轻飞白 + 落笔墨点），叠整字淡墨影防半笔错读，
    p→1 收为干净 SemiBold 字形（静止时与 lyric3 整句一致，无飞白毛边）。返回与 T.glyph(z) 同画布的 alpha。"""
    import typo as T, cv2
    clean = T.glyph(ch, SF_FONT, z, False)
    if p >= 0.999: return clean
    g = clean.shape[0]
    bz = int(round(z / 4) * 4)                                     # brush_prep 字号按 4 取整 → 缩回 z
    b = T.brush_glyph(ch, SF_FONT, z, p, seed=seed, dry=0.30, wet=0.9)
    G = int(round(b.shape[0] * z / bz))
    b = cv2.resize(b, (G, G), interpolation=cv2.INTER_AREA)
    o = (G - g) // 2
    if o >= 0: b = b[o:o + g, o:o + g]
    else: b = np.pad(b, ((-o, g - G + o), (-o, g - G + o)))[:g, :g]
    if b.shape != clean.shape: b = cv2.resize(b, (g, g), interpolation=cv2.INTER_AREA)
    ghost = clean * 0.55 * (1 - (1 - min(1.0, p * 3.0)) ** 3)    # 整字淡墨影（BG 写法）
    w = min(1.0, max(0.0, (p - 0.72) / 0.27)); w = w * w * (3 - 2 * w)   # 末段收笔：书写态 → 干净字形
    return np.maximum(b, ghost) * (1 - w) + clean * w


def serif_apply(img, t):
    info = _line_info(t)
    if info is None: return img
    T = _sf_fonts()
    import cv2
    t0, t1, s = info
    wt = _wtimes().get(t0)
    n = len(s.replace(' ', ''))
    if wt is None: wt = [t0 + (t1 - t0) * 0.85 * i / max(1, n) for i in range(n)]
    ko = 1.0 - min(1.0, max(0.0, (t - (t1 + 0.25)) / 0.3))          # 句尾墨散（同 ink_h）
    if ko <= 0: return img
    z = _sf_size(); L = T.Layer()
    for ch, x, y, colr, i in _sf_plan(s):
        p = min(1.0, max(0.0, (t - (wt[i] - 0.10)) / 0.32))       # 提前 0.1s 起笔、0.32s 写完
        if p <= 0: continue
        g = _sf_glyph(ch, z, p, 17 + i)
        if ko < 1:
            g = cv2.GaussianBlur(g, (0, 0), 0.5 + 3.0 * (1 - ko)) * ko
        L.paste(g, x, y, colr)
    fr = img.astype(np.float32) * (1 / 255)
    fr = T.compose(fr, L, **SF_STYLE)
    return (fr.clip(0, 1) * 255 + 0.5).astype(np.uint8)
