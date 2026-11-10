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
    si = next((k for k, (a, b, c) in enumerate(LINES) if a == t0), -1)
    wt = _wtimes().get(t0)
    n = len(s.replace(' ', ''))
    if wt is None: wt = [t0 + (t1 - t0) * 0.85 * i / max(1, n) for i in range(n)]
    ko = 1.0 - min(1.0, max(0.0, (t - (t1 + 0.25)) / 0.3))          # 句尾墨散（同 ink_h）
    if ko <= 0: return img
    fxt = _fx_table(si, s) if FX_ON else {}
    S = _FXS() if fxt else None
    dy = _shake(si, s, wt, t) if fxt else 0.0
    z = _sf_size(); L = T.Layer()
    for ch, x, y, colr, i in _sf_plan(s):
        lst = fxt.get(i)
        y = y + dy
        if lst and any(f in BODY_FX for f, _ in lst):
            g = _glyph_canvas(ch, z)                                  # 本字由特效决定怎么出现
        else:
            p = min(1.0, max(0.0, (t - (wt[i] - 0.10)) / 0.32))   # 提前 0.1s 起笔、0.32s 写完
            if p <= 0: continue
            g = _sf_glyph(ch, z, p, 17 + i)
        if lst:
            tau = t - wt[i]
            for f, kw in lst:
                g, colr = FX_FN[f](g, ch, x, y, z, colr, tau, kw, S, ko)
                if g is None: break
            if g is None: continue
        if ko < 1:
            g = cv2.GaussianBlur(g, (0, 0), 0.5 + 3.0 * (1 - ko)) * ko
        L.paste(g, x, y, colr)
    if S is not None:
        for a, cx, cy, c in S.extra: L.paste(a * ko, cx, cy, c)
        L.A[:FX_Y0] = 0                                               # 特效不出下黑边
    fr = img.astype(np.float32) * (1 / 255)
    fr = T.compose(fr, L, **SF_STYLE)
    if S is not None:
        if S.light.any(): fr[FX_Y0:FX_Y1] += S.light
        fr[:FX_Y0] = img[:FX_Y0].astype(np.float32) * (1 / 255)      # 画面（y<960）一像素不动（印块阴影 σ20 会外溢 ≤3/255）
    return (fr.clip(0, 1) * 255 + 0.5).astype(np.uint8)


# ===================================================================== r6-SUB3 逐字特效（SUB_FX，默认开）
# 用户 16:18：「我的意思是这些效果，移植到底部的字幕上面去，哪个字的效果就在哪个字上出现」。
# 画内字特效（斩开 / 滴血 / 刻字 / 砸下 / 墨洇 / 闪电 / 金光 / 盖印 / 朱圈 / 烧出 / 裂字 / 刀光扫过）搬到 serif_h 底部字幕，
# 挂在对应的那个字上、按该字演唱时刻（align.json）触发。版式不变：思源宋 SemiBold 62px 一行；所有特效像素只落在 y 960–1080。
# SUB_FX=0 关（回到 r6-SUB2 serif_h 逐像素一致）。表 FX_OVR：句索引（align.log 顺序 0–55）→ {字: [(特效, 参数)]}；
# 字写法：'血' = 句中第 1 个「血」，'不#2' = 第 2 个「不」，也可直接写字序号 int。τ = t − 该字演唱时刻。
FX_ON = os.environ.get('SUB_FX', '1') != '0'
FX_Y0, FX_Y1 = 960, 1080
BLOOD = (0.66, 0.035, 0.03)
HOT = (1.0, 0.55, 0.18)
COLD = (0.80, 0.90, 1.0)
FX_OVR = {
    0:  {'锋': [('sheen', {})]},                                                    # V01 雨打刃口 / 刀锋
    1:  {'五': [('bleed', {})], '百': [('bleed', {})], '寒': [('sheen', {})], '光': [('slash', dict(mode='close'))]},   # V03 五百墨洇；V05/V06 寒光扫刃 + 斩字（画内已去）
    2:  {'罪': [('seal', dict(kind='imprint'))]},                                   # V08「罪状」朱印压印
    3:  {'称': [('bleed', {})], '量': [('bleed', {})]},                              # V10「称量」朱红墨洇
    4:  {'杀': [('slash', dict(mode='open', angle=-28))], '放': [('bleed', {}), ('sheen', dict(at=0.05))]},   # V12 巨「杀」斜斩；V13「放」墨洇 + 刀光
    5:  {'刀': [('sheen', {})], '主': [('carve', {})], '张': [('carve', {})]},       # V14 拔刀白刃闪；V15 刀刻石碑「我的主张」
    6:  {'正': [('slam', {})]},                                                     # V16/V17 巨印「正」
    7:  {'锋': [('slash', dict(mode='open', angle=-30))], '芒': [('sheen', dict(col=HOT))]},   # V21「锋芒」被斩成两半
    8:  {'框': [('ring', dict(shape='box'))]},                                      # P04 朱笔框住「框」
    9:  {'规': [('sheen', dict(col=(1.0, 0.80, 0.45)))], '矩': [('slash', dict(mode='close', angle=-90, at=0.20))],   # P05 金箔「规矩」被门缝切断
         '血': [('drip', dict(n=3))]},                                              # P06「血」从门缝流下（画内 #53 已去）
    10: {'命': [('seal', {})], '当': [('slam', {})]},                                # P09「命」印砸进；P11 铅字「应当」
    11: {'刀': [('slash', dict(mode='open', angle=-22))], '还': [('bleed', {})], '滚': [('burn', {})], '烫': [('burn', {})]},   # P13 刀被弧光斩开；P14「滚烫」烧出
    12: {'血': [('bleed', dict(dur=0.55)), ('drip', dict(n=3))], '刀': [('seal', {})]},   # S028 巨「血」墨洇 + 血滴落刃；S030「刀」方印盖月
    13: {'正': [('seal', dict(color=(1.0, 0.74, 0.30)))], '邪': [('seal', {}), ('slash', dict(mode='open', angle=-86, at=0.45))]},   # S032 正/邪两印，一刀劈开
    14: {'墙': [('carve', {})]},                                                    # S033/S034 字刻墙砖、「墙」从砖缝浮起
    15: {'劈': [('slash', dict(mode='open', angle=-14))], '看': [('bleed', {})], '个': [('bleed', {})], '天': [('gold', {})], '亮': [('gold', {})]},   # S035 斩断；S036 光洇；S037「天亮」金字烧起
    16: {'血': [('drip', dict(n=3, col=BLOOD))]},                                    # S038 血沿刃纹流下
    17: {'是': [('slam', dict(k=0.6))], '非': [('slam', dict(k=0.6))], '对': [('slam', dict(k=0.6))], '错': [('slam', dict(k=0.6))], '扛': [('crack', {})]},   # S040 四印逐拍落下；C35「扛」硬扛
    18: {'不': [('slash', dict(mode='close', angle=-6))], '量': [('seal', {})]},     # S042「不」一道刀光划过月面；S043「量」方印
    19: {'刀': [('slash', dict(mode='open', angle=-10))], '回': [('carve', {})], '答': [('carve', dict(col=SF_RED))]},   # S045 这一刀；S046 刀身「就是我的回答」（画内 #28 已去）
    20: {'退': [('carve', {})], '让': [('carve', {})]},                              # V04 笏板刻「大局 / 退让」
    21: {'权': [('carve', {})], '嚣': [('crack', {})], '张': [('crack', {})]},        # V07 杖身刻「权」；裂字「嚣张」
    22: {'分': [('sheen', dict(col=(1.0, 0.80, 0.45)))], '量': [('sheen', dict(col=(1.0, 0.80, 0.45)))]},   # V11 秤星一颗颗点亮「分」「量」
    23: {'人': [('slam', {})]},                                                     # V12 秤砣「人」字头砸地
    24: {'天': [('bolt', {})]},                                                     # V15 雷劈（103.99）
    25: {'命': [('bleed', dict(dur=0.5)), ('drip', dict(n=2))]},                     # V17「命」像血一样从掌纹里渗出
    26: {'黑': [('bleed', {})]},                                                    # V20 黑 / 白
    27: {'刀': [('slash', dict(mode='open', angle=-12))], '划': [('carve', dict(col=SF_RED))], '向': [('burn', {})]},   # V22 刀被斩开；V23 朱红刀痕；V25「向」烧出
    28: {'规': [('ring', {})], '则': [('ring', {})], '纲': [('carve', {})]},          # C01 朱笔圈「规则」；C03 朱砂纸刻「纲」
    29: {'正': [('slam', dict(col=(1.0, 0.74, 0.30)))], '暗': [('burn', {})], '箱': [('burn', {})]},   # C04 金印「正」坠入；C06 烙字「暗箱」（画内 #37 已去）
    30: {'不': [('slash', dict(mode='open', angle=-70))], '大': [('carve', dict(col=(1.0, 0.78, 0.42)))], '局': [('carve', dict(col=(1.0, 0.78, 0.42)))],
         '为': [('carve', dict(col=(1.0, 0.78, 0.42)))], '上': [('carve', dict(col=(1.0, 0.78, 0.42)))]},   # C09 红线被斩断；C10「大局为上」泥金阴刻
    31: {'刀': [('sheen', dict(col=HOT))], '烫': [('burn', {})]},                    # C11/C12 刀身烧红
    32: {'血': [('bleed', dict(dur=0.6)), ('drip', dict(n=2))]},                     # C16「血」坠水晕开
    33: {'定': [('bolt', dict(col=(1.0, 0.85, 0.5)))], '正': [('seal', dict(color=(1.0, 0.74, 0.30)))], '邪': [('seal', {})]},   # C20 闪电照出金「定」；C21 正 / 邪
    34: {'铁': [('carve', {})], '壁': [('carve', {})], '铜': [('carve', {})], '墙': [('sheen', dict(col=HOT))]},   # C23 铜牌阴刻；C24 刀尖拖火星
    35: {'劈': [('slash', dict(mode='open', angle=-80))], '亮': [('bolt', dict(col=(1.0, 0.95, 0.85)))]},   # C25 竖劈；C28「亮」字形裂口灌进电光
    36: {'血': [('drip', dict(n=3))]},                                              # C30「血」被风扯开（画内 #53 已去）
    37: {'是': [('sheen', {})], '非': [('sheen', {})], '对': [('sheen', {})], '错': [('slash', dict(mode='open', angle=-35))], '扛': [('slam', {})]},   # C32–C34 刀光残影烧亮 → 斩成两半；C35 巨印压下
    38: {'天': [('bolt', {})], '量': [('carve', dict(col=SF_RED))]},                 # C37 匾「天不」雷劈碎；C39「量」赤热刃口刻出（画内 #43 已去）
    39: {'刀': [('slash', dict(mode='open', angle=-4))]},                            # C40 一刀横断天平
    40: {'什': [('slam', {})], '大': [('slam', dict(k=0.7))], '局': [('slam', dict(k=0.7))], '牺': [('bleed', {})], '忍': [('slam', {}), ('drip', dict(n=1, at=0.35))]},   # S02/S03 砸下；S05「忍」砸下 + 刃点朱墨滑落
    41: {'理': [('ring', {})], '所': [('ring', {})], '应': [('ring', {})], '当': [('seal', dict(color=(0.42, 0.44, 0.48), kind='iron'))]},   # S08 朱批圈 + 黑铁官印砸下
    42: {'状': [('slash', dict(mode='open', angle=-87))]},                           # S12 刀尖顶进「罪状」一刀两断
    43: {'牺': [('burn', {})], '牲': [('burn', {})], '陪': [('burn', {})], '葬': [('burn', {})]},   # S14 剪纸被火烧；S15「陪葬」火烧显字
    44: {'刀': [('sheen', {})], '我#2': [('seal', {})], '主': [('burn', dict(col=HOT))], '张': [('burn', dict(col=HOT))]},   # S17 白刃寒光；S19 朱印「我」+ 火星写「主张」
    45: {'谁': [('sheen', dict(col=(1.0, 0.92, 0.75)))], '定': [('sheen', dict(col=(1.0, 0.92, 0.75)))], '的': [('sheen', dict(col=(1.0, 0.92, 0.75)))],
         '规': [('slash', dict(mode='open', angle=-12))], '矩': [('slash', dict(mode='open', angle=-12))], '闯': [('crack', dict(k=1.4))]},   # S20 竹简亮字；S21 斩断律令牌；S22 撞碎「闯」
    46: {'天': [('bolt', {})], '我': [('carve', dict(col=SF_RED))], '判#2': [('slam', {})]},   # S23 闪电显「天」；S25 刀光刻「我」；S26「判」砸在断口
    47: {'刀': [('burn', dict(col=SF_RED))], '来': [('crack', {})], '答#2': [('gold', {})]},   # S27 火星烙「刀」；S29 裂字「来」；S30 金「答」爆开
    48: {'血': [('carve', dict(col=SF_RED)), ('drip', dict(n=2, at=0.45))], '刀': [('seal', {})], '不': [('seal', {})], '放': [('seal', {})]},   # E01「血」阴刻入刃 + 槽底残血；E02 三方小朱印
    49: {'世': [('burn', {})], '间': [('burn', {})], '从': [('burn', {})], '来': [('burn', {})], '没': [('burn', {})], '有': [('burn', {})],
         '昭': [('crack', dict(col=(1.0, 0.8, 0.45)))], '彰': [('crack', dict(col=(1.0, 0.8, 0.45)))]},   # E03 逐字烧出；E04/E05「天理昭彰」匾开裂
    50: {'伪': [('burn', {})], '装': [('burn', {})]},                                # E08「伪装」笔画自燃
    51: {'撕': [('slash', dict(mode='open', angle=-30))], '碎': [('crack', dict(k=1.4))], '章': [('seal', {})]},   # E09 交叉斩；撕碎；E12 印
    52: {'血': [('drip', dict(n=4, col=BLOOD))]},                                    # E13「血」滴血笔触
    53: {'伪': [('bleed', dict(dur=0.5))]},                                          # 剪影里骨白字「伪」血红
    54: {'天': [('drip', dict(n=3, col=(1.0, 0.72, 0.30), melt=True))]},              # E20 墨色巨字「天」熔化坍塌、熔滴下坠
    55: {'刀': [('sheen', {})], '正': [('gold', {})], '道': [('gold', {})], '沧': [('gold', {})], '桑': [('gold', {})]},   # E23/E24 刃身寒光；E26「正道沧桑」
}
BODY_FX = ('slam', 'bleed', 'carve', 'burn', 'seal')               # 自己负责「字怎么出现」的特效（不走笔序书写）
_FXC = {}


def _ss(e0, e1, x):
    x = min(1.0, max(0.0, (x - e0) / (e1 - e0))) if e1 != e0 else float(x >= e0)
    return x * x * (3 - 2 * x)


def _eo(x, k=3):
    x = min(1.0, max(0.0, x)); return 1 - (1 - x) ** k


def _fx_table(si, s):
    """句 si 的 {字序: [(fx, kw)]}。"""
    k = (si, s)
    if k in _FXC: return _FXC[k]
    chars = s.replace(' ', ''); out = {}
    for key, lst in FX_OVR.get(si, {}).items():
        if isinstance(key, int): idx = key
        else:
            ch, _, nth = key.partition('#'); nth = int(nth or 1); idx = -1; c = 0
            for i, x in enumerate(chars):
                if x == ch:
                    c += 1
                    if c == nth: idx = i; break
        if 0 <= idx < len(chars): out[idx] = list(lst)
    _FXC[k] = out
    return out


def _pad(g, p):
    return np.pad(g, p)


def _rngf(*a):
    import zlib
    return np.random.default_rng(zlib.crc32(repr(a).encode('utf-8')))


class _FXS:
    """一帧的特效状态：光层只开下黑边一条（y 960–1080）。"""
    def __init__(self):
        self.light = np.zeros((FX_Y1 - FX_Y0, 1920, 3), np.float32)
        self.extra = []          # (alpha, cx, cy, color) 进文字图层（吃同一套阴影）

    def add_light(self, a, cx, cy, color, amt=1.0):
        """局部图 a（h,w 或 h,w,3）以 (cx,cy) 为中心加到光层。"""
        h, w = a.shape[:2]
        x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2)) - FX_Y0
        xs, ys = max(0, x0), max(0, y0); xe, ye = min(1920, x0 + w), min(FX_Y1 - FX_Y0, y0 + h)
        if xe <= xs or ye <= ys: return
        sub = a[ys - y0:ye - y0, xs - x0:xe - x0]
        if sub.ndim == 2: sub = sub[..., None] * np.array(color, np.float32)
        self.light[ys:ye, xs:xe] += sub * amt

    def line(self, p0, p1, color, w=1, amt=1.0, blur=0.0):
        import cv2
        L = np.zeros((FX_Y1 - FX_Y0, 1920), np.float32)
        cv2.line(L, (int(p0[0] * 4), int((p0[1] - FX_Y0) * 4)), (int(p1[0] * 4), int((p1[1] - FX_Y0) * 4)), 1.0, max(1, int(w)), cv2.LINE_AA, shift=2)
        if blur > 0: L = cv2.GaussianBlur(L, (0, 0), blur) * (1 + blur)
        self.light += L[..., None] * np.array(color, np.float32) * amt


def _glyph_canvas(ch, z):
    import typo as T
    return T.glyph(ch, SF_FONT, z, False)


def _shake(si, s, wt, t):
    """砸下 / 盖印 / 裂字落地的整行微震（px，只上下 ≤3px）。"""
    dy = 0.0
    for idx, lst in _fx_table(si, s).items():
        for fx, kw in lst:
            if fx in ('slam', 'seal', 'crack'):
                a = t - wt[idx] - (kw.get('at', 0.30) if fx == 'crack' else 0.0)
                if 0 <= a < 0.25:
                    dy += 3.0 * kw.get('k', 1.0) * math.exp(-a / 0.06) * math.cos(a * 60)
    return max(-3.0, min(3.0, dy))


# --------------------------------------------------------------------- 单字特效：每个函数改字形 g（方形画布，字心在中心）/ 颜色，
# 并可往光层 S.light 加光、往 S.extra 加带阴影的附件（血滴、印框、朱圈）。tau = t − 演唱时刻。
def fx_bleed(g, ch, x, y, z, col, tau, kw, S, ko):
    """墨洇：字从笔画芯部洇开显出（typo.ink_bleed_glyph），边缘留一层淡晕。"""
    import typo as T
    dur = kw.get('dur', 0.42)
    p = _ss(-0.10, -0.10 + dur, tau) if tau < dur else 1.0
    if p <= 0: return None, col
    a = T.ink_bleed_glyph(ch, SF_FONT, z, max(0.02, p), seed=kw.get('seed', 3), bleed=kw.get('bleed', 0.8))
    G, g0 = a.shape[0], g.shape[0]
    o = (G - g0) // 2
    if o > 0: g = np.pad(g, ((o, G - g0 - o), (o, G - g0 - o)))
    w = _ss(0.6, 1.0, p)
    return np.maximum(a * (1 - w), np.maximum(a * 0.55, g) * w) if w > 0 else a, col


def fx_slam(g, ch, x, y, z, col, tau, kw, S, ko):
    """砸下：字从 1.55× 大、半透明急落到 1.0×（0.10s），落定一震，墨尘沿字脚横向喷开。"""
    import cv2
    col = kw.get('col', col)
    if tau < -0.12: return None, col
    q = _ss(-0.12, 0.0, tau)
    sc = 1.55 - 0.55 * q * q
    if sc > 1.001:
        G = g.shape[0]; D = int(G * sc) + 2
        M = cv2.getRotationMatrix2D((G / 2, G / 2), 0, sc); M[:, 2] += (D - G) / 2
        g2 = cv2.warpAffine(g, M, (D, D)) * (0.35 + 0.65 * q)
        return g2, col
    if 0 <= tau < 0.45:                                              # 墨尘：字脚两侧
        r = _rngf('slam', ch, int(x))
        a = tau / 0.45
        for _ in range(int(16 * kw.get('k', 1.0))):
            sd = r.choice([-1, 1]); v = r.uniform(80, 260)
            px = x + sd * (z * 0.35 + v * _eo(a, 2)); py = y + z * 0.42 - r.uniform(0, 10) * a
            rr = r.uniform(1.5, 4.0) * (1 + a)
            S.add_light(_dot(rr), px, py, (0.55, 0.50, 0.46), 0.55 * (1 - a) ** 1.5 * ko)
        if tau < 0.08: S.add_light(g * (1 - tau / 0.08), x, y, (1.0, 0.95, 0.85), 0.6 * ko)   # 落地一闪
    return g, col


_DOTC = {}
def _dot(r):
    import cv2
    k = round(r * 2) / 2
    if k not in _DOTC:
        n = int(k * 4) + 3; a = np.zeros((n, n), np.float32)
        cv2.circle(a, (n // 2, n // 2), max(1, int(k)), 1.0, -1, cv2.LINE_AA)
        _DOTC[k] = cv2.GaussianBlur(a, (0, 0), 0.7)
    return _DOTC[k]


def fx_slash(g, ch, x, y, z, col, tau, kw, S, ko):
    """斩开：字写完后一道白热刀光沿斩线横切过字，两半沿斩线反向错开；mode=close 0.5s 后合拢、mode=open 保持断开。
    断口红热、迸火星。angle 斩线角（度，0 = 水平，负 = 右上）。"""
    import cv2
    at = kw.get('at', 0.26); q = tau - at
    if q < 0: return g, col
    ang = math.radians(kw.get('angle', -8)); d = np.array([math.cos(ang), math.sin(ang)]); n = np.array([-d[1], d[0]])
    P = 10; g = np.pad(g, P); G = g.shape[0]; c = G / 2
    yy, xx = np.mgrid[0:G, 0:G].astype(np.float32)
    sd = (xx - c) * n[0] + (yy - c) * n[1]
    e = _eo(q / 0.09, 3)
    if kw.get('mode', 'close') == 'close': e *= 1 - _ss(0.45, 0.70, q)
    sep, slide = 3.2 * e, 7.0 * e
    out = np.zeros_like(g)
    for sgn, m in ((-1, np.clip(0.5 - sd / 1.2, 0, 1)), (1, np.clip(0.5 + sd / 1.2, 0, 1))):
        M = np.float32([[1, 0, sgn * (d[0] * slide + n[0] * sep)], [0, 1, sgn * (d[1] * slide + n[1] * sep)]])
        out = np.maximum(out, cv2.warpAffine(g * m, M, (G, G)))
    hot = np.exp(-np.abs(sd) / 2.0) * (g > 0.3) * (1 - _ss(0.0, 0.8, q)) * min(1.0, q / 0.03)
    if hot.max() > 0: S.add_light(cv2.GaussianBlur(hot, (0, 0), 2.5) * 2 + hot, x, y, HOT, 1.2 * ko)
    if q < 0.30:                                                      # 刀光：光头 0.07s 横贯，余辉 0.3s
        ln = z * 1.35; head = _eo(q / 0.07, 2); tail = _ss(0.04, 0.30, q)
        p0 = np.array([x, y]) + d * ln * (tail * 2 - 1); p1 = np.array([x, y]) + d * ln * (head * 2 - 1)
        f = (1 - q / 0.30) * ko
        S.line(p0, p1, (1.0, 0.97, 0.92), w=2, amt=1.6 * f, blur=0.0)
        S.line(p0, p1, (1.0, 0.90, 0.75), w=3, amt=1.0 * f, blur=5.0)
    if q < 0.45:                                                      # 火星：从断口两端迸出，落在黑边内
        r = _rngf('slash', ch, int(x)); a = q / 0.45
        for _ in range(14):
            u = r.uniform(-0.6, 0.6) * z; v = r.uniform(60, 220); th = r.uniform(0, 2 * math.pi)
            px = x + d[0] * u + math.cos(th) * v * q; py = y + d[1] * u + math.sin(th) * v * q * 0.5 + 220 * q * q
            S.add_light(_dot(1.2), px, py, (1.0, 0.72, 0.35), 1.4 * (1 - a) ** 2 * ko)
    return out, col


def fx_sheen(g, ch, x, y, z, col, tau, kw, S, ko):
    """刀光扫过（寒光）：一道冷白光带沿字形由左向右掠过（只亮字形本身），同时一线细刀光横贯字腰。"""
    import cv2
    at = kw.get('at', 0.22); q = tau - at; dur = kw.get('dur', 0.30)
    if not (0 <= q < dur + 0.25): return g, col
    cc = kw.get('col', COLD)
    G = g.shape[0]; xx = np.arange(G, dtype=np.float32)[None, :] - G / 2
    fr_ = -z * 0.8 + 1.6 * z * _eo(q / dur, 2)
    band = np.exp(-((xx - fr_) / (z * 0.16)) ** 2) * (1 - _ss(dur, dur + 0.25, q))
    S.add_light(g * band * 1.6 + cv2.GaussianBlur(g * band, (0, 0), 3) * 0.8, x, y, cc, ko)
    if q < dur:
        lx = x + fr_
        S.line((lx - z * 0.55, y + 2), (lx + z * 0.12, y - 1), (1.0, 0.98, 0.95), w=2, amt=0.9 * (1 - q / dur) * ko, blur=0.0)
        S.line((lx - z * 0.55, y + 2), (lx + z * 0.12, y - 1), cc, w=3, amt=0.8 * (1 - q / dur) * ko, blur=4.0)
    return g, col


def fx_drip(g, ch, x, y, z, col, tau, kw, S, ko):
    """滴血：字写完后从笔画下缘挂下血珠，拉长成血线流进黑边底部（≤ y 1076），珠子坠落后血线留着；melt=True 为熔金下坠。"""
    import cv2
    at = kw.get('at', 0.26); q = tau - at
    if q < 0: return g, col
    cc = kw.get('col', BLOOD if not kw.get('melt') else (1.0, 0.72, 0.30))
    key = ('drip', ch, z, g.shape[0])
    if key not in _FXC:                                              # 下缘点：字形下边界，按 x 分散取
        b = (g > 0.5) & (np.roll(g, -1, 0) < 0.2); b[-1] = False
        ys, xs = np.nonzero(b); G = g.shape[0]
        sel = ys > G * 0.45
        ys, xs = ys[sel], xs[sel]
        _FXC[key] = (ys, xs)
    ys, xs = _FXC[key]
    if not len(xs): return g, col
    n = kw.get('n', 3); G = g.shape[0]
    order = np.argsort(xs); xs, ys = xs[order], ys[order]
    picks = []
    for k in range(n):
        lo, hi = int(len(xs) * k / n), max(int(len(xs) * k / n) + 1, int(len(xs) * (k + 1) / n))
        j = lo + int(np.argmax(ys[lo:hi]))                            # 每段取最低的那个下缘点
        picks.append((xs[j], ys[j]))
    r = _rngf('drip', ch, int(x))
    for k, (px, py) in enumerate(picks):
        st = k * 0.16 + r.uniform(0, 0.08); a = q - st
        if a <= 0: continue
        sx, sy = x - G / 2 + px, y - G / 2 + py
        Lmax = max(4.0, FX_Y1 - 6 - sy) * r.uniform(0.70, 1.0)
        ln = Lmax * _eo(a / 0.75, 2)
        w = 2.6 if not kw.get('melt') else 3.2
        br = w * 0.55 + 0.9 * min(1.0, a / 0.5)
        canvas = np.zeros((int(ln + br) + 8, 14), np.float32)
        cv2.line(canvas, (28, 0), (28, int(ln * 4)), 1.0, max(1, int(round(w))), cv2.LINE_AA, shift=2)
        cv2.circle(canvas, (28, int(ln * 4)), int(br * 4), 1.0, -1, cv2.LINE_AA, shift=2)
        canvas = cv2.GaussianBlur(canvas, (0, 0), 0.6) * 1.15
        sx -= 0.0
        S.extra.append((np.clip(canvas, 0, 1), sx, sy + canvas.shape[0] / 2 - 1, cc))
        S.add_light(np.clip(canvas, 0, 1) * 0.25, sx - 0.8, sy + canvas.shape[0] / 2 - 1.5, (1.0, 0.55, 0.5) if not kw.get('melt') else (1.0, 0.85, 0.5), 0.35 * ko)   # 湿亮
    if kw.get('melt') and q < 1.2:                                   # 熔化：字下半段微微下坠变形
        import cv2 as _c
        Gs = g.shape[0]; yy = np.arange(Gs, dtype=np.float32)
        sag = 3.0 * float(_eo(q / 0.8)) * np.clip((yy - Gs * 0.45) / (Gs * 0.55), 0, 1)
        mx = np.tile(np.arange(Gs, dtype=np.float32)[None, :], (Gs, 1)); my = np.tile((yy - sag)[:, None], (1, Gs))
        g = _c.remap(g, mx.astype(np.float32), my.astype(np.float32), _c.INTER_LINEAR)
        col = tuple(np.array(col) * (1 - 0.6 * _eo(q / 0.5)) + np.array(cc) * 0.6 * _eo(q / 0.5))
    return g, col


def fx_carve(g, ch, x, y, z, col, tau, kw, S, ko):
    """刻字：一道赤热刃口沿斜向把字「刻」出来（刻过的笔画先红热再冷却），刻槽上沿冷光、下沿压暗。"""
    import cv2
    cc = kw.get('col', col)
    p = _ss(-0.12, 0.24, tau)
    if p <= 0: return None, cc
    G = g.shape[0]; yy, xx = np.mgrid[0:G, 0:G].astype(np.float32)
    u = ((xx - G / 2) * 0.85 + (yy - G / 2) * 0.53) / (z * 0.75)      # 斜向刻进方向（左上 → 右下）
    front = -1.0 + 2.1 * p
    m = np.clip((front - u) * 6, 0, 1)
    gm = g * m
    edge = np.exp(-((u - front) * 7) ** 2) * g * (p < 1)
    if edge.max() > 0: S.add_light(edge * 2.0 + cv2.GaussianBlur(edge, (0, 0), 3), x, y, (1.0, 0.85, 0.6), 1.2 * ko)
    cool = _ss(0.20, 0.85, tau)
    hot = gm * (1 - cool) * np.clip((front - u) * 2, 0, 1)
    if hot.max() > 0: S.add_light(hot, x, y, HOT, 0.9 * ko)
    if p >= 1:                                                       # 刻槽：上沿高光一线
        hl = np.clip(g - np.roll(g, 2, 0), 0, 1)
        S.add_light(hl, x, y, (0.85, 0.88, 0.95), 0.35 * ko)
    c2 = tuple(np.array(cc) * cool + np.array(HOT) * (1 - cool))
    return gm, c2


def fx_burn(g, ch, x, y, z, col, tau, kw, S, ko):
    """烧出：噪声火线自下而上把字烧出来（火线金白），余烬上飘（不出黑边），字色由火色冷却到本色。"""
    import cv2
    cc = kw.get('col', col)
    p = _ss(-0.14, 0.22, tau)
    if p <= 0: return None, cc
    G = g.shape[0]
    k = ('burnN', G)
    if k not in _FXC:
        r = np.random.default_rng(G); nz = cv2.resize(r.random((8, 8)).astype(np.float32), (G, G), interpolation=cv2.INTER_CUBIC)
        _FXC[k] = nz
    nz = _FXC[k]
    v = 1 - np.arange(G, dtype=np.float32)[:, None] / G + (nz - 0.5) * 0.35   # 底 = 0 → 顶 = 1
    front = -0.2 + 1.45 * p
    m = np.clip((front - v) * 8, 0, 1)
    edge = np.exp(-((v - front) * 9) ** 2) * g * (p < 1)
    if edge.max() > 0: S.add_light(edge * 2.2 + cv2.GaussianBlur(edge, (0, 0), 3) * 1.2, x, y, (1.0, 0.78, 0.40), ko)
    if 0 <= tau < 0.9:
        r = _rngf('burn', ch, int(x))
        for _ in range(9):
            a = (tau + r.uniform(0, 0.5)) % 0.9 / 0.9
            px = x + r.uniform(-0.4, 0.4) * z + math.sin(a * 6 + r.uniform(0, 6)) * 4
            py = y + z * 0.3 - a * 52
            if py > FX_Y0 + 4: S.add_light(_dot(1.0), px, py, (1.0, 0.6, 0.25), 1.3 * (1 - a) * (1 - _ss(0.6, 0.9, tau)) * ko)
    cool = _ss(0.15, 0.9, tau)
    return g * m, tuple(np.array(cc) * cool + np.array((1.0, 0.62, 0.25)) * (1 - cool))


def fx_seal(g, ch, x, y, z, col, tau, kw, S, ko):
    """盖印：一方朱红阴文印（字镂空）从 1.35× 落下压在字位上（0.08s），印泥边缘毛口；kind=iron 黑铁官印 + 金字一闪；
    kind=imprint 印抬起后留下的纸面印痕（偏淡）。"""
    import cv2
    if tau < -0.10: return None, col
    cc = kw.get('color', (0.80, 0.10, 0.07)); kind = kw.get('kind', 'seal')
    G = g.shape[0]; s = int(z * 1.14)
    key = ('seal', ch, z, kind)
    if key not in _FXC:
        sq = np.zeros((G, G), np.float32); o = (G - s) // 2
        cv2.rectangle(sq, (o, o), (o + s, o + s), 1.0, -1)
        r = np.random.default_rng(ord(ch)); nz = cv2.resize(r.random((24, 24)).astype(np.float32), (G, G), interpolation=cv2.INTER_CUBIC)
        sq = cv2.GaussianBlur(sq, (0, 0), 1.0)
        sq = np.clip((sq - 0.5 + (nz - 0.5) * 0.5) * 4 + 0.5, 0, 1) * (0.82 + 0.18 * nz)
        gi = cv2.resize(g, None, fx=0.84, fy=0.84, interpolation=cv2.INTER_AREA); gp = np.zeros_like(g)
        oo = (G - gi.shape[0]) // 2; gp[oo:oo + gi.shape[0], oo:oo + gi.shape[1]] = gi
        _FXC[key] = (sq * (1 - gp), gp)
    sq, gp = _FXC[key]
    q = _ss(-0.10, 0.0, tau); sc = 1.35 - 0.35 * q
    a = sq * (0.3 + 0.7 * q) * (0.78 if kind == 'imprint' else 1.0)
    if sc > 1.001:
        D = int(G * sc) + 2; M = cv2.getRotationMatrix2D((G / 2, G / 2), -3 * (1 - q), sc); M[:, 2] += (D - G) / 2
        a = cv2.warpAffine(a, M, (D, D))
    if kind == 'iron' and 0 <= tau < 0.35:
        S.add_light(gp, x, y, (1.0, 0.82, 0.45), 1.6 * (1 - tau / 0.35) * ko)
    if 0 <= tau < 0.06: S.add_light(cv2.GaussianBlur(sq, (0, 0), 4), x, y, (1.0, 0.5, 0.35), 0.5 * ko)
    return a, cc


def fx_ring(g, ch, x, y, z, col, tau, kw, S, ko):
    """朱圈 / 朱框：字写完后一笔朱砂把字圈住（shape=box 为方框），笔锋起收有粗细。"""
    import cv2
    at = kw.get('at', 0.18); q = _ss(at, at + 0.30, tau)
    if q <= 0: return g, col
    rx, ry = z * 0.66, z * 0.60
    n = 64; pts = []
    for i in range(int(n * 1.08 * q) + 1):
        th = -2.2 + 2 * math.pi * i / n
        if kw.get('shape') == 'box':
            c_, s_ = math.cos(th), math.sin(th); k = 1 / max(abs(c_), abs(s_))
            pts.append((x + rx * c_ * k * 0.92, y + ry * s_ * k * 0.92))
        else:
            wob = 1 + 0.05 * math.sin(th * 3 + ord(ch))
            pts.append((x + rx * math.cos(th) * wob, y + ry * math.sin(th) * wob))
    if len(pts) < 2: return g, col
    W_, H_ = int(rx * 2 + 30), int(ry * 2 + 30)
    C = np.zeros((H_ * 4, W_ * 4), np.float32)
    for i in range(len(pts) - 1):
        w = 3.6 * (0.55 + 0.45 * math.sin(math.pi * i / max(1, len(pts) - 1)))
        a0 = (int((pts[i][0] - x + W_ / 2) * 4), int((pts[i][1] - y + H_ / 2) * 4))
        a1 = (int((pts[i + 1][0] - x + W_ / 2) * 4), int((pts[i + 1][1] - y + H_ / 2) * 4))
        cv2.line(C, a0, a1, 1.0, max(4, int(w * 4)), cv2.LINE_AA)
    C = cv2.resize(C, (W_, H_), interpolation=cv2.INTER_AREA)
    S.extra.append((C, x, y, kw.get('col', (0.86, 0.12, 0.08))))
    return g, col


def fx_bolt(g, ch, x, y, z, col, tau, kw, S, ko):
    """闪电刻字：字落定一刻一道锯齿闪电竖劈过字（闪 3 下），字被电光照成冷白、随后退回本色；电光只在黑边内。"""
    if not (0 <= tau < 0.55): return g, col
    cc = kw.get('col', (0.80, 0.88, 1.0))
    fl = [1.0, 0.25, 0.9, 0.15, 0.6, 0.0, 0.3][min(6, int(tau * 30))] * (1 - tau / 0.55)
    r = _rngf('bolt', ch, int(x))
    pts = []; px = x + r.uniform(-8, 8)
    for yy in np.linspace(FX_Y0 + 3, FX_Y1 - 3, 9):
        pts.append((px, yy)); px += r.uniform(-14, 14)
    for i in range(len(pts) - 1):
        S.line(pts[i], pts[i + 1], (1.0, 1.0, 1.0), w=2, amt=1.6 * fl * ko)
        S.line(pts[i], pts[i + 1], cc, w=3, amt=1.2 * fl * ko, blur=5.0)
    b0 = pts[3]; b1 = (b0[0] + r.choice([-1, 1]) * 30, b0[1] + 26)
    S.line(b0, b1, cc, w=1, amt=1.0 * fl * ko)
    S.add_light(g, x, y, cc, 1.1 * fl * ko)
    k = min(1.0, tau / 0.35)
    return g, tuple(np.array(cc) * (1 - k) + np.array(col) * k)


def fx_gold(g, ch, x, y, z, col, tau, kw, S, ko):
    """金光：字转金，落定时一圈金辉亮起又收（「天亮」金字烧起又熄），一道金光掠过字形。"""
    import cv2
    if tau < -0.1: return g, col
    cg = kw.get('col', SF_GOLD)
    pulse = math.exp(-max(0.0, tau - 0.1) / 0.35) * _ss(-0.1, 0.1, tau)
    S.add_light(cv2.GaussianBlur(g, (0, 0), 6), x, y, (1.0, 0.70, 0.30), (0.9 * pulse + 0.15) * ko)
    xx = np.arange(g.shape[0], dtype=np.float32)[None, :] - g.shape[0] / 2
    q = tau - 0.12
    if 0 <= q < 0.4:
        band = np.exp(-((xx - (-z * 0.7 + 1.4 * z * q / 0.4)) / (z * 0.15)) ** 2)
        S.add_light(g * band, x, y, (1.0, 0.95, 0.8), 1.3 * ko)
    return g, cg


def fx_crack(g, ch, x, y, z, col, tau, kw, S, ko):
    """裂字：字被撞 / 压出几道裂纹（裂缝透出熔金红光后变暗），字一震，几粒碎屑掉进黑边。字形保持可读。"""
    import cv2
    at = kw.get('at', 0.30); q = tau - at
    if q < 0: return g, col
    G = g.shape[0]; key = ('crack', ch, G)
    if key not in _FXC:
        r = np.random.default_rng(ord(ch) * 7); C = np.zeros((G * 4, G * 4), np.float32)
        c0 = np.array([G / 2 + r.uniform(-6, 6), G / 2 + r.uniform(-6, 6)])
        for b in range(4):
            th = b * math.pi / 2 + r.uniform(-0.6, 0.6); p = c0.copy()
            for s_ in range(5):
                p2 = p + np.array([math.cos(th), math.sin(th)]) * G * 0.10; th += r.uniform(-0.5, 0.5)
                cv2.line(C, tuple((p * 4).astype(int)), tuple((p2 * 4).astype(int)), 1.0, 6, cv2.LINE_AA); p = p2
        _FXC[key] = cv2.resize(C, (G, G), interpolation=cv2.INTER_AREA)
    C = _FXC[key] * _ss(0.0, 0.06, q) * (g > 0.2)
    k = kw.get('k', 1.0)
    glow = C * (1 - _ss(0.05, 0.9, q))
    cc = kw.get('col', (1.0, 0.55, 0.22))
    S.add_light(glow * 1.8 + cv2.GaussianBlur(glow, (0, 0), 2.5), x, y, cc, ko)
    if q < 0.6:
        r = _rngf('crack', ch, int(x))
        for _ in range(int(5 * k)):
            vx = r.uniform(-60, 60); px = x + r.uniform(-0.3, 0.3) * z + vx * q; py = y + z * 0.2 + 30 * q + 320 * q * q
            if py < FX_Y1 - 3: S.extra.append((_dot(r.uniform(1.2, 2.2)), px, py, tuple(np.array(col) * 0.8)))
    jit = 2.0 * k * math.exp(-q / 0.05) * math.sin(q * 90)
    g2 = g * (1 - 0.85 * C)
    if abs(jit) > 0.2: g2 = cv2.warpAffine(g2, np.float32([[1, 0, jit], [0, 1, 0]]), (G, G))
    return g2, col


FX_FN = dict(bleed=fx_bleed, slam=fx_slam, slash=fx_slash, sheen=fx_sheen, drip=fx_drip, carve=fx_carve, burn=fx_burn,
             seal=fx_seal, ring=fx_ring, bolt=fx_bolt, gold=fx_gold, crack=fx_crack)
