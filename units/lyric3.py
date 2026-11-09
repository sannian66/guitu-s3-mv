"""units/lyric3.py — 副歌一 v3 统一字幕层（全片字幕规范的实现，见 crew/chorus1_v2_edit.md「v3 字幕规范」）

规范
- 字体：歌词全部思源宋（Noto Serif SC 多字重）。整句 SemiBold；主字（超大单字）Black；辅助小字 Regular。
- 字号三级：主字 440px 字号（≈ 有效画面高 840 的 50%）；整句 62px；辅助 34px。全段同级一致。
- 版位只有两种：底部三分之一横排居中（字心 y=850，左右安全边距 ≥160）/ 右侧竖排一列（字心 x=1752，首字 y=262）。
  整句字距 0.22em（横）/ 0.30em（竖）；竖排标点用竖排形。同屏只出现一句；不散落单字；读序 = 演唱顺序。
- 颜色：正文暖白；每句至多一个朱红关键字；金只给与光相关的字（天亮）。描边/投影/辉光统一 STYLE 一套参数。
- 入场族「锐光擦入」：每字在演唱字头前 0.24s 开始，沿读向遮罩擦入 + 由虚到实 + 擦入前沿一道细锐白光，字头视觉帧恰好落定。
- 出场族「墨散」：整句按读序逐字（间隔 0.03s）噪声溶解 + 微虚 + 上飘 10px，0.26s。
- 主字特效（砸下/斩开/墨洇）在各镜头内实现，每句至多一个。字与画面互动（刀上刻字、被斩开）保留但用同一字体/颜色规则。
"""
import math
import numpy as np, cv2
import typo as T

W, H = 1920, 1080
WHITE = (0.97, 0.94, 0.88)
RED_T = (0.84, 0.10, 0.07)          # 朱红（字用略提亮，暗底可读）
GOLD_T = (1.0, 0.78, 0.42)
F_SENT, F_MAIN, F_AUX = 'serif_sb', 'serif_black', 'serif_r'
S_SENT, S_MAIN, S_AUX = 62, 440, 34
TRACK_H, TRACK_V = 0.22, 0.30
BOTTOM_Y = 850
RIGHT_X, RIGHT_Y0 = 1752, 262
STYLE = dict(shadow=0.72, shadow_sigma=20, outline=0, glow=0.20, glow_sigma=14)
IN_DUR, OUT_DUR, OUT_STAG = 0.24, 0.26, 0.03
VPUNCT = {'，': '︐', '。': '︒', '、': '︑', '：': '︓', '；': '︔', '！': '︕', '？': '︖', '…': '︙', '—': '︱',
          '「': '﹁', '」': '﹂', '（': '︵', '）': '︶'}


def places(text, layout, size=S_SENT, font=F_SENT, red=(), gold=()):
    """整句排版 → [dict(ch,x,y,size,rot,font,idx,emph)]（T._P 的 places 格式）"""
    chars = [VPUNCT.get(c, c) if layout == 'right' else c for c in text]
    n = len(chars)
    out = []
    if layout == 'bottom':
        adv = size * (1 + TRACK_H)
        x0 = W / 2 - adv * (n - 1) / 2
        for i, c in enumerate(chars):
            out.append(dict(ch=c, x=x0 + adv * i, y=BOTTOM_Y, size=size, rot=0.0, font=font, idx=i, emph=c in red))
    else:
        adv = size * (1 + TRACK_V)
        for i, c in enumerate(chars):
            out.append(dict(ch=c, x=RIGHT_X, y=RIGHT_Y0 + adv * i, size=size, rot=0.0, font=font, idx=i, emph=c in red))
    return out


class Sentence:
    def __init__(self, text, line, ks, layout, out_t, red='', gold='', skip=False):
        self.text, self.line, self.ks, self.layout = text, line, ks, layout
        self.out_t = out_t; self.red = red; self.gold = gold; self.skip = skip
        self.P = places(text, layout, red=tuple(red))

    def color(self, c):
        if c in self.gold: return GOLD_T
        if c in self.red: return RED_T
        return WHITE


def _noise(seed, g):
    r = np.random.default_rng(seed)
    n = cv2.resize(r.random((max(2, g // 9), max(2, g // 9))).astype(np.float32), (g, g), interpolation=cv2.INTER_CUBIC)
    return np.clip(n, 0, 1)


class LyricLayer:
    def __init__(self, sentences, char_time):
        """sentences: [Sentence]；char_time(line, k) → 字头视觉帧时刻"""
        self.S = sentences; self.ct = char_time
        for s in sentences:
            for p in s.P: T.glyph(p['ch'], p['font'], p['size'], False)
            s.tin = [self.ct(s.line, k) for k in s.ks]
            s.t_on = s.tin[0] - IN_DUR
            s.t_off = s.out_t + OUT_STAG * (len(s.P) - 1) + OUT_DUR

    def active(self, t):
        return [s for s in self.S if s.t_on <= t < s.t_off]

    def draw(self, fr, t):
        for s in self.active(t):
            if s.skip: continue
            fr = self._sentence(fr, s, t)
        return fr

    def _sentence(self, fr, s, t):
        L = T.Layer()
        horiz = s.layout == 'bottom'
        for i, p in enumerate(s.P):
            ti = s.tin[i]
            e = (t - (ti - IN_DUR)) / IN_DUR
            if e <= 0: continue
            e = min(1.0, e)
            ee = 1 - (1 - e) ** 3
            a = T.glyph(p['ch'], p['font'], p['size'], False).copy()
            g = a.shape[0]
            # 出场：墨散
            to = s.out_t + OUT_STAG * i
            q = min(1.0, max(0.0, (t - to) / OUT_DUR))
            dy = 0.0
            if q > 0:
                nz = _noise(ord(p['ch']) * 7 + i, g)
                a = a * np.clip((nz - q * 1.15) * 6 + 0.5, 0, 1) * (1 - q * 0.3)
                a = cv2.GaussianBlur(a, (0, 0), 0.5 + 2.5 * q)
                dy = -10 * q
            # 入场：锐光擦入（遮罩擦入 + 由虚到实 + 前沿锐光）
            hot = None
            if e < 1:
                ax = np.linspace(-0.15, 1.15, g, dtype=np.float32)
                front = ee * 1.3 - 0.15
                m1 = np.clip((front - ax) / 0.12, 0, 1)
                band = np.exp(-((ax - front) / 0.03) ** 2) * (1 - ee)
                if horiz: mask, bm = m1[None, :], band[None, :]
                else: mask, bm = m1[:, None], band[:, None]
                sig = 5.0 * (1 - ee) ** 2
                ab = cv2.GaussianBlur(a, (0, 0), sig) if sig > 0.4 else a
                hot = np.clip(cv2.GaussianBlur(a, (0, 0), 1.2) * 1.4, 0, 1) * bm
                a = ab * mask
            L.paste(a, p['x'], p['y'] + dy, s.color(p['ch']))
            if hot is not None and hot.max() > 0.02:
                L.paste(hot, p['x'], p['y'] + dy, (1.0, 1.0, 1.0), alpha=0.9)
        return T.compose(fr, L, **STYLE)
