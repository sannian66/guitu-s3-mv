"""typo.py —《谁定正邪》MV 歌词排版与文字动画库（字幕·转场组）

纯代码程序化：numpy / OpenCV / PIL。字体仅用 /workspace/work/mv/fonts/ 四款。
所有效果函数：输入 float32 RGB 帧 (1080,1920,3) 0–1，返回新帧（不原地改写传入帧）。
有效区：y ∈ [120, 960)（上下黑边各 120px），layout() 保证文字落在安全框内。

进度参数约定 prog：
  - 标量 p∈[0,1]：整句按顺序逐字推进（seq_progress 自动分配，相邻字有重叠）；
  - 列表/数组：每个字各自的 0–1 进度（可由 timed_progress(times, t, dur) 从逐字时间得到，
    times 来自 load_lines()[i]['times'] 或 scenes.LINES[i]['times']，空格为 None）。

耗时（2 vCPU 沙箱实测，1920×1080 单帧含合成，热缓存，6 相位平均/最大；原始数据 lib/typo_test/timing_typo.txt）：
  brush_write        0.06 / 0.09 s     vertical_column   0.03 / 0.03 s     scatter_stack     0.09 / 0.12 s
  giant_char         0.16 / 0.22 s     carved_on_blade   0.12 / 0.13 s     stamp_seal        0.06 / 0.08 s
  slash_cut          0.13 / 0.21 s     ink_bleed_in      0.03 / 0.05 s     shatter_out       0.13 / 0.16 s
  kinetic_track      0.10 / 0.14 s     burn_in           0.08 / 0.08 s     burn_in(ash/熄)   0.09 / 0.13 s
  typewriter_brush   0.04 / 0.05 s     typewriter(光标+RGB) 0.02 / 0.03 s  text_matrix       0.10 / 0.14 s
  char_shape         0.08 / 0.10 s     explode_reform    0.09 / 0.14 s     char_rain         0.09 / 0.16 s
  text_wall build    0.05 / 0.06 s     crack 0.22 / 0.24 s   collapse 0.08 / 0.10 s   fly 0.15 / 0.25 s
  font_morph         0.08 / 0.09 s     text_on_quad+ring 0.07 / 0.09 s     kinetic_fly       0.06 / 0.17 s
  rotate_invert      0.06 / 0.06 s     blade_write(600px) 0.17 / 0.19 s    credit_block×3    0.05 / 0.06 s
  seal_grid+overprint 0.20 / 0.27 s    seal_caption/斩印/碎印 0.08 / 0.19 s  drip+strike       0.08 / 0.10 s
  冷缓存（首次用到某字/字号）：glyph 3–24ms、笔序场 _brush_prep 8–20ms、距离场 1–22ms（150→600px）；
  建议镜头 __init__ 里 warm(text,font,size) / prepare_brush(text,font,size) 预热。
"""
import math, os, json
from functools import lru_cache
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
BAR = 120
SAFE = (60, BAR + 30, W - 60, H - BAR - 30)   # x0,y0,x1,y1 安全框（含留白）
ROOT = '/workspace/work/mv'
FD = ROOT + '/fonts/'
FONTS = {
    'kai': FD + 'MaShanZheng-Regular.ttf',     # 马善政楷（端正）
    'xing': FD + 'ZhiMangXing-Regular.ttf',    # 志莽行书（飞扬）
    'cao': FD + 'LiuJianMaoCao-Regular.ttf',   # 流江毛草（狂草，巨字用）
    'song': FD + 'NotoSerifSC.otf',            # 思源宋（印章/刻字/矩阵小字）
}
COLORS = {
    'ink': (0.05, 0.05, 0.06),
    'white': (0.96, 0.94, 0.90),
    'red': (0.72, 0.06, 0.05),
    'gold': (1.0, 0.76, 0.40),
}
_NO_GLYPH = {'kai': '·', 'xing': '·', 'cao': '·'}   # 三款手写体缺「·」→ 自动回落思源宋
PUNCT = set('，。、！？；：,.!?;:·…—「」『』“”‘’（）()《》')


def col(c):
    """颜色名或 RGB 元组 → np.float32[3]"""
    if isinstance(c, str):
        c = COLORS[c]
    return np.asarray(c, np.float32)


def _rng(seed):
    return np.random.default_rng(seed)


def ease_out(x, k=3):
    x = np.clip(x, 0, 1); return 1 - (1 - x) ** k


def ease_io(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


def ease_back(x, s=1.7):
    x = np.clip(x, 0, 1) - 1; return 1 + x * x * ((s + 1) * x + s)


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0, 1); return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ 歌词数据
@lru_cache(1)
def load_lines():
    """与 scenes.LINES 相同的逐字时间展开（不 import scenes，避免重依赖）。"""
    segs = json.load(open(os.path.join(ROOT, 'align.json')))['segments']
    out = []
    for s in segs:
        text = s['text'].strip(); ct = []
        for w in s['words']:
            ws = w['word'].strip().replace(' ', '')
            for k in range(len(ws)):
                ct.append(w['start'] + (w['end'] - w['start']) * k / len(ws))
        times = []; j = 0
        for c in text:
            if c == ' ': times.append(None); continue
            times.append(ct[min(j, len(ct) - 1)] if ct else s['start']); j += 1
        out.append(dict(text=text, times=times, start=s['start'], end=s['end']))
    return out


@lru_cache(1)
def beats():
    return np.load(os.path.join(ROOT, 'analysis.npz'))['beats'].astype(np.float64)


def beat_pulse(t, decay=0.18, every=1):
    """最近一个已过节拍后的冲击包络 1→0（指数衰减）。every=2 只取每两拍。"""
    b = beats()[::every]
    i = np.searchsorted(b, t) - 1
    if i < 0: return 0.0
    return float(math.exp(-(t - b[i]) / decay))


def seq_progress(n, p, overlap=0.35):
    """整句进度 p → 每字进度（相邻字重叠 overlap）。"""
    if n <= 0: return []
    span = 1.0 / (n - (n - 1) * overlap) if n > 1 else 1.0
    step = span * (1 - overlap)
    return [float(np.clip((p - i * step) / span, 0, 1)) for i in range(n)]


def timed_progress(times, t, dur=0.25, lead=0.04):
    """逐字时间 → 每字进度；None（空格）给 1。"""
    return [1.0 if tc is None else float(np.clip((t - tc + lead) / dur, 0, 1)) for tc in times]


def _per_char(prog, n):
    if np.isscalar(prog):
        return seq_progress(n, float(prog))
    pr = list(prog)
    assert len(pr) >= n, 'prog 长度应等于可见字数'
    return pr[:n]


# ------------------------------------------------------------------ 字形缓存
@lru_cache(64)
def _font(name, size):
    return ImageFont.truetype(FONTS.get(name, name), int(size))


def _fontname(ch, fname):
    return 'song' if _NO_GLYPH.get(fname) and ch in _NO_GLYPH[fname] else fname


_noise_cache = {}
def _noise(h, w, scale, seed, aniso=(1, 1)):
    """平滑噪声 0–1：低分辨率随机 → 双三次放大。aniso=(sx,sy) 拉伸为纤维/飞白纹理。"""
    k = (h, w, scale, seed, aniso)
    if k not in _noise_cache:
        r = _rng(seed)
        sh = max(2, int(h / scale / aniso[1])); sw = max(2, int(w / scale / aniso[0]))
        n = cv2.resize(r.random((sh, sw)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        if len(_noise_cache) > 400: _noise_cache.clear()
        _noise_cache[k] = np.clip(n, 0, 1)
    return _noise_cache[k]


@lru_cache(3000)
def _glyph_u8(ch, fname, size, texture):
    """返回 (uint8 alpha, cx_off, cy_off)：方形画布，字心在画布中心。texture=True 加墨迹纹理（飞白/毛边）。"""
    fname = _fontname(ch, fname)
    f = _font(fname, size)
    g = int(size * 1.5) + 8
    im = Image.new('L', (g, g), 0)
    ImageDraw.Draw(im).text((g / 2, g / 2), ch, font=f, fill=255, anchor='mm')
    a = np.asarray(im).astype(np.float32) / 255
    if texture and size >= 28:
        seed = (ord(ch) * 131 + size) % 9973
        # 毛边：轻微腐蚀边缘 + 纤维噪声
        fib = _noise(g, g, max(2, size / 60), seed)
        streak = _noise(g, g, max(1.5, size / 110), seed + 1, aniso=(1, 9) if seed % 2 else (9, 1))
        edge = cv2.GaussianBlur(a, (0, 0), max(0.8, size / 140))
        a = np.clip((edge - 0.5 + (fib - 0.5) * 0.35) * 3.5 + 0.5, 0, 1) * a ** 0.3
        # 飞白：只在笔画边缘带（距边 < 4.5% 字号）用拉丝纹理减淡，内部保持实墨 → 干笔毛边而非条纹
        m = (a > 0.5).astype(np.uint8)
        din = cv2.distanceTransform(m, cv2.DIST_L2, 3)
        edge_band = np.clip(1 - din / min(size * 0.035, 10.0), 0, 1)
        dry = np.clip((streak - 0.6) * 3.5, 0, 1) * edge_band * 0.9
        a = a * (1 - dry)
    return (np.clip(a, 0, 1) * 255).astype(np.uint8)


def glyph(ch, fname='kai', size=120, texture=True):
    """float32 alpha 方形画布（边长 ≈1.5×size），字心在中心。"""
    size = max(8, int(round(size / 2) * 2)) if size < 400 else int(round(size / 8) * 8)
    return _glyph_u8(ch, fname, size, texture).astype(np.float32) * (1 / 255)


def warm(text, fname='kai', size=120, texture=True):
    """预热字形缓存（镜头 __init__ 调）。"""
    for c in text:
        if c != ' ': glyph(c, fname, size, texture)


# ------------------------------------------------------------------ 文字图层
class Layer:
    """全帧文字图层：A (H,W) alpha，C (H,W,3) 颜色（非预乘）。只在包围盒内更新。"""
    def __init__(self, h=H, w=W):
        self.A = np.zeros((h, w), np.float32)
        self.C = np.zeros((h, w, 3), np.float32)
        self.bb = [w, h, 0, 0]

    def _touch(self, x0, y0, x1, y1):
        b = self.bb
        self.bb = [min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1)]

    def paste(self, a, cx, cy, color, alpha=1.0, mode='over'):
        """把局部 alpha 图 a 以 (cx,cy) 为中心贴上。"""
        h, w = a.shape[:2]
        x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
        xs, ys = max(0, x0), max(0, y0); xe, ye = min(self.A.shape[1], x0 + w), min(self.A.shape[0], y0 + h)
        if xe <= xs or ye <= ys: return
        sub = a[ys - y0:ye - y0, xs - x0:xe - x0] * alpha
        c = col(color)
        R = self.A[ys:ye, xs:xe]; CC = self.C[ys:ye, xs:xe]
        if mode == 'max':
            m = sub > R
            CC[m] = c; np.maximum(R, sub, out=R)
        else:
            na = sub + R * (1 - sub)
            w_ = (sub / np.maximum(na, 1e-6))[..., None]
            CC[:] = CC * (1 - w_) + c * w_
            R[:] = na
        self._touch(xs, ys, xe, ye)

    def paste_rgba(self, rgb, a, x0, y0):
        h, w = a.shape
        xs, ys = max(0, x0), max(0, y0); xe, ye = min(self.A.shape[1], x0 + w), min(self.A.shape[0], y0 + h)
        if xe <= xs or ye <= ys: return
        sub = a[ys - y0:ye - y0, xs - x0:xe - x0]; sc = rgb[ys - y0:ye - y0, xs - x0:xe - x0]
        R = self.A[ys:ye, xs:xe]; CC = self.C[ys:ye, xs:xe]
        na = sub + R * (1 - sub)
        w_ = (sub / np.maximum(na, 1e-6))[..., None]
        CC[:] = CC * (1 - w_) + sc * w_
        R[:] = na
        self._touch(xs, ys, xe, ye)

    def box(self, m=0):
        b = self.bb
        if b[2] <= b[0]: return None
        return (max(0, b[0] - m), max(0, b[1] - m), min(self.A.shape[1], b[2] + m), min(self.A.shape[0], b[3] + m))


def place(L, ch, cx, cy, size, color='white', fname='kai', alpha=1.0, scale=1.0, rot=0.0, blur=0.0,
          texture=True, sx=1.0, sy=1.0, mode='over'):
    """在图层 L 上画一个字（缩放用重栅格化保证清晰，旋转/拉伸用仿射）。"""
    if ch == ' ' or alpha <= 0.003: return
    s = size * scale
    if s < 4: return
    a = glyph(ch, fname, s, texture)
    if rot != 0 or sx != 1 or sy != 1:
        g = a.shape[0]; d = int(g * max(sx, sy, 1) * 1.15)
        M = cv2.getRotationMatrix2D((g / 2, g / 2), rot, 1.0)
        M[:, :2] = M[:, :2] @ np.array([[sx, 0], [0, sy]])
        M[:, 2] = np.array([d / 2, d / 2]) - M[:, :2] @ np.array([g / 2, g / 2])   # 画布中心为不动点
        a = cv2.warpAffine(a, M, (d, d), flags=cv2.INTER_LINEAR)
    if blur > 0.4:
        p = int(blur * 3)
        a = cv2.GaussianBlur(np.pad(a, p), (0, 0), blur)
    L.paste(a, cx, cy, color, alpha, mode)


def compose(fr, L, shadow=0.65, shadow_sigma=None, outline=0, outline_color='ink', glow=0.0,
            glow_color=None, glow_sigma=18, halo=None, opacity=1.0):
    """把文字图层合成到帧上：墨色晕影(shadow) → 描边(outline px) → 外发光(glow) → 文字本体。
    可读性默认值：白/金字 shadow 0.65；朱红字建议 outline=3 + glow 0.4。"""
    out = fr.copy()
    m = int(max(shadow_sigma or 0, glow_sigma) * 3 + outline + 8)
    bx = L.box(m if (shadow > 0 or glow > 0) else outline + 2)
    if bx is None: return out
    x0, y0, x1, y1 = bx
    A = L.A[y0:y1, x0:x1] * opacity; C = L.C[y0:y1, x0:x1]
    F = out[y0:y1, x0:x1]
    hh, ww = A.shape
    if shadow > 0:
        ss = shadow_sigma or 34
        sm = cv2.resize(A, (max(1, ww // 4), max(1, hh // 4)), interpolation=cv2.INTER_AREA)
        wide = cv2.resize(cv2.GaussianBlur(sm, (0, 0), ss / 4), (ww, hh))
        tight = cv2.resize(cv2.GaussianBlur(sm, (0, 0), 2.2), (ww, hh))
        sh = np.clip(tight * 2.6, 0, 1) * 0.6 + np.clip(wide * 1.8, 0, 1) * 0.4
        F *= (1 - shadow * sh)[..., None]
    if outline > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * outline + 1, 2 * outline + 1))
        D = cv2.dilate(A, k)
        D = cv2.GaussianBlur(D, (0, 0), 0.8)
        F[:] = F * (1 - D[..., None]) + col(outline_color) * D[..., None]
    if glow > 0:
        gc = col(glow_color) if glow_color is not None else None
        sm = cv2.resize(A[..., None] * C if gc is None else A, (max(1, ww // 4), max(1, hh // 4)), interpolation=cv2.INTER_AREA)
        sm = cv2.GaussianBlur(sm, (0, 0), glow_sigma / 4)
        g = cv2.resize(sm, (ww, hh))
        if g.ndim == 2: g = g[..., None] * gc
        F += g * glow
    F[:] = F * (1 - A[..., None]) + C * A[..., None]
    return out


def auto_style(color):
    """按字色给出默认可读性参数。"""
    c = color if isinstance(color, str) else None
    if c == 'red': return dict(shadow=0.55, outline=2, outline_color=(0.03, 0.02, 0.02), glow=0.55, glow_color=(0.9, 0.12, 0.06))
    if c == 'gold': return dict(shadow=0.7, glow=0.5, glow_color=(1.0, 0.55, 0.2))
    if c == 'ink': return dict(shadow=0.0, glow=0.0)
    return dict(shadow=0.8, glow=0.18, glow_color=(1, 0.95, 0.88))


# ------------------------------------------------------------------ 排版
def layout(text, style='h', size=None, fname='kai', box=None, anchor=(0.5, 0.5), spacing=0.06,
           seed=0, emph=(), max_size=None, col_gap=0.35):
    """一句歌词 → 字位列表 [dict(ch,x,y,size,rot,font,idx,emph)]（空格不出字位，idx 对应可见字序号）。
    style:
      'h'       横排居中（过长自动在空格/中点折两行）
      'v'       竖排：空格分列，从右到左，各列行首（顶）对齐；过长列自动折列
      'scatter' 错落叠放：大小对比强烈（emph 字 ×2.4，其余 0.55–1.15 随机），斜向阶梯
      'stair'   阶梯：逐字下移右移
      'giant'   单字占满有效区高度
    box: (x0,y0,x1,y1) 限定区域，默认 SAFE。anchor: 在 box 内的对齐点（0–1）。
    总会缩放以保证完全落在 box 内（不碰黑边）。"""
    bx = box or SAFE
    bw, bh = bx[2] - bx[0], bx[3] - bx[1]
    text = text.replace('\u3000', ' ')
    vis = [c for c in text if c != ' ']
    emph = set(emph) if not isinstance(emph, set) else emph
    r = _rng(seed)
    P = []
    s0 = size or 120
    if style == 'giant':
        s = size or bh * 1.02
        P = [dict(ch=vis[0], x=0.0, y=0.0, size=s, rot=0.0)]
    elif style == 'h':
        groups = _wrap(text, 14)
        y = 0.0
        for g in groups:
            x = 0.0
            for c in g:
                if c == ' ': x += s0 * 0.5; continue
                sz = s0 * (1.0 if c not in PUNCT else 0.5)
                P.append(dict(ch=c, x=x + s0 / 2, y=y, size=sz, rot=0.0)); x += s0 * (1 + spacing)
            # 行内居中
            wl = x - s0 * spacing
            for p_ in P[len(P) - sum(1 for c in g if c != ' '):]: p_['x'] -= wl / 2
            y += s0 * 1.25
    elif style == 'v':
        cols = [c for c in text.split(' ') if c]
        maxn = max(4, int(bh / (s0 * (1 + spacing))))
        cols2 = []
        for c in cols:
            if len(c) > maxn:
                k = math.ceil(len(c) / maxn); n = math.ceil(len(c) / k)
                cols2 += [c[i:i + n] for i in range(0, len(c), n)]
            else: cols2.append(c)
        x = 0.0
        for ci, c in enumerate(cols2):       # 从右到左
            y = 0.0
            for ch in c:
                if ch in PUNCT:              # 竖排标点：缩小、置于格右上
                    P.append(dict(ch=ch, x=x + s0 * 0.3, y=y - s0 * 0.25, size=s0 * 0.5, rot=0.0)); y += s0 * 0.5
                    continue
                P.append(dict(ch=ch, x=x, y=y + s0 / 2, size=s0, rot=0.0)); y += s0 * (1 + spacing)
            x -= s0 * (1 + col_gap)
    elif style == 'scatter':
        # 拼贴式：每个短语一行，行字号大小交替、左右错位阶梯、行距为负使行间咬合；emph 字 2.6× 下沉压住邻行
        phrases = [c for c in text.split(' ') if c]
        if len(phrases) == 1 and len(phrases[0]) > 5:
            t_ = phrases[0]; n_ = math.ceil(len(t_) / 4)
            phrases = [t_[i * len(t_) // n_:(i + 1) * len(t_) // n_] for i in range(n_)]
        mult = [1.0, 0.62, 1.25, 0.72, 1.1, 0.58]
        y = 0.0; bigs = []
        for ri, ph in enumerate(phrases):
            rs = s0 * mult[ri % len(mult)] * (0.9 if len(ph) > 6 else 1.0)
            xoff = (r.uniform(0.1, 0.9) if ri else 0.0) * s0 * (1.6 if ri % 2 else -1.0)
            x = xoff
            for c in ph:
                big = c in emph
                sz = rs * (2.6 if big else r.uniform(0.85, 1.12))
                yy_ = y + (sz - rs) * 0.3 if big else y + r.uniform(-0.08, 0.08) * rs
                if not big:   # 避让上方下沉的巨字
                    for (bx0, by0, bx1, by1) in bigs:
                        if yy_ + sz * 0.45 > by0 and yy_ - sz * 0.45 < by1 and x + sz * 0.9 > bx0 and x < bx1:
                            x = bx1 + sz * 0.05
                P.append(dict(ch=c, x=x + sz / 2, y=yy_, size=sz, rot=float(r.uniform(-6, 6) if not big else r.uniform(-10, 10))))
                if big: bigs.append((x, yy_ - sz * 0.45, x + sz * 0.95, yy_ + sz * 0.45))
                x += sz * (0.84 if big else 0.92)
            y += rs * 1.0
    elif style == 'stair':
        x = y = 0.0
        for c in text:
            if c == ' ': x += s0 * 0.4; y += s0 * 0.5; continue
            P.append(dict(ch=c, x=x, y=y, size=s0, rot=0.0)); x += s0 * 0.78; y += s0 * 0.42
    else:
        raise ValueError(style)
    for i, p_ in enumerate(P):
        p_['idx'] = i; p_['font'] = fname; p_['emph'] = p_['ch'] in emph
    return fit(P, bx, anchor, max_size=max_size, allow_up=size is None)


def _wrap(text, maxn):
    t = text
    if len(t.replace(' ', '')) <= maxn: return [t]
    if ' ' in t:
        parts = t.split(' '); best = None
        for i in range(1, len(parts)):
            a, b = ' '.join(parts[:i]), ' '.join(parts[i:])
            d = abs(len(a) - len(b))
            if best is None or d < best[0]: best = (d, [a, b])
        return best[1]
    m = (len(t) + 1) // 2
    return [t[:m], t[m:]]


def bbox(P, pad=0.55):
    xs0 = min(p['x'] - p['size'] * pad for p in P); xs1 = max(p['x'] + p['size'] * pad for p in P)
    ys0 = min(p['y'] - p['size'] * pad for p in P); ys1 = max(p['y'] + p['size'] * pad for p in P)
    return xs0, ys0, xs1, ys1


def fit(P, box=None, anchor=(0.5, 0.5), max_size=None, allow_up=True, pad=0.55):
    """把字位缩放/平移到 box 内（anchor 对齐）。allow_up=False 时只缩不放。"""
    if not P: return P
    bx = box or SAFE
    x0, y0, x1, y1 = bbox(P, pad)
    bw, bh = bx[2] - bx[0], bx[3] - bx[1]
    s = min(bw / max(1, x1 - x0), bh / max(1, y1 - y0))
    if not allow_up: s = min(s, 1.0)
    if max_size:
        s = min(s, max_size / max(p['size'] for p in P))
    w2, h2 = (x1 - x0) * s, (y1 - y0) * s
    ox = bx[0] + (bw - w2) * anchor[0] - x0 * s
    oy = bx[1] + (bh - h2) * anchor[1] - y0 * s
    for p in P:
        p['x'] = p['x'] * s + ox; p['y'] = p['y'] * s + oy; p['size'] *= s
    return P


def _P(text, places, style, size, fname, box, anchor, seed=0, emph=(), max_size=None):
    if places is not None: return places
    return layout(text, style, size=size, fname=fname, box=box, anchor=anchor, seed=seed, emph=emph, max_size=max_size)


def _colors(P, color, emph_color):
    return [emph_color if (p.get('emph') and emph_color) else color for p in P]


def _finish(fr, L, color, style_kw):
    kw = auto_style(color); kw.update(style_kw or {})
    return compose(fr, L, **kw)


# ------------------------------------------------------------------ 1. 逐笔书写
_brush_cache = {}
def _brush_prep(ch, fname, size, seed=0):
    """笔序场：连通域按“先上后下、先左后右”排序，域内用测地距离（约束膨胀）从起笔点推进。
    返回 dict(a, O, frac, wdir, starts, pad)。"""
    size = int(round(size / 4) * 4)
    k = (ch, fname, size)
    if k in _brush_cache: return _brush_cache[k]
    a = glyph(ch, fname, size, texture=False)
    g = a.shape[0]
    pad = int(size * 0.3)
    a = np.pad(a, pad); G = a.shape[0]
    lo = 112
    sc = lo / G
    al = cv2.resize(a, (lo, lo), interpolation=cv2.INTER_AREA)
    m = (al > 0.35).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, connectivity=8)
    comps = []
    for i in range(1, n):
        if st[i, 4] < 3: continue
        ys, xs = np.nonzero(lab == i)
        sc_ = ys + 0.55 * xs
        j = np.argmin(sc_)
        comps.append((st[i, 1] + 0.45 * st[i, 0], i, (ys[j], xs[j])))
    comps.sort()
    D = np.full((lo, lo), -1.0, np.float32)
    k3 = np.ones((3, 3), np.uint8)
    lens = []; starts = []
    for _, i, (sy, sx) in comps:
        cm = (lab == i).astype(np.uint8)
        fr_ = np.zeros_like(cm); fr_[sy, sx] = 1
        seen = fr_.copy(); d = 0
        dd = np.zeros((lo, lo), np.float32)
        while True:
            nx = cv2.dilate(seen, k3) & cm
            new = nx & (1 - seen)
            if not new.any(): break
            d += 1; dd[new > 0] = d; seen = nx
        D[cm > 0] = dd[cm > 0]
        lens.append(max(1, d)); starts.append((sx / sc, sy / sc))
    tot = sum(lens) + 4 * len(lens)
    O = np.full((lo, lo), 1.0, np.float32); FR = np.zeros((lo, lo), np.float32)
    off = 0; t_starts = []
    for (_, i, _), ln in zip(comps, lens):
        cm = lab == i
        O[cm] = (off + D[cm]) / tot; FR[cm] = D[cm] / ln
        t_starts.append(off / tot); off += ln + 4
    # 向外扩散填充（保证上采样边缘平滑）
    inside = m > 0
    Oi = np.where(inside, O, 0).astype(np.float32); Wt = inside.astype(np.float32)
    Ob = cv2.GaussianBlur(Oi, (0, 0), 1.5); Wb = cv2.GaussianBlur(Wt, (0, 0), 1.5)
    Of = np.where(inside, O, Ob / np.maximum(Wb, 1e-4)).astype(np.float32)
    Of[Wb < 1e-3] = 1.0
    gx = cv2.Sobel(Of, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(Of, cv2.CV_32F, 0, 1, ksize=3)
    wdir = gx * gx / (gx * gx + gy * gy + 1e-9)       # 1=横向行笔，0=纵向
    up = lambda z: cv2.resize(z, (G, G), interpolation=cv2.INTER_LINEAR)
    res = dict(a=a, O=up(Of), frac=up(FR), wdir=up(wdir), starts=starts, t_starts=t_starts, pad=pad, size=size)
    r = _rng(ord(ch) + seed)
    sp = []
    for (sx, sy), ts in zip(starts, t_starts):     # 落笔飞溅墨点
        for _ in range(r.integers(3, 9)):
            ang = r.uniform(0, 2 * math.pi); dist = size * r.uniform(0.04, 0.22) * (1 + r.exponential(0.6))
            sp.append((sx + math.cos(ang) * dist, sy + math.sin(ang) * dist, size * r.uniform(0.006, 0.022), ts))
    res['splat'] = sp
    if len(_brush_cache) > 300: _brush_cache.clear()
    _brush_cache[k] = res
    return res


def prepare_brush(text, fname='xing', size=150):
    for c in text:
        if c != ' ' and c not in PUNCT: _brush_prep(c, fname, size)


def brush_glyph(ch, fname, size, p, seed=0, dry=0.8, wet=1.0, splatter=True):
    """单字书写 alpha（画布含 pad），p∈[0,1]。墨晕：笔锋前沿湿墨扩散；飞白：行笔末段按方向拉丝；落笔墨点。"""
    B = _brush_prep(ch, fname, size, seed)
    G = B['a'].shape[0]
    if p <= 0: return np.zeros((G, G), np.float32)
    O, a = B['O'], B['a']
    w = 0.025
    rev = np.clip((p * 1.02 - O) / w + 0.5, 0, 1)
    A = a * rev
    if p < 0.999:
        front = a * np.exp(-((p - O) / 0.03) ** 2) * (O < p + 0.01)
        bl = cv2.GaussianBlur(front, (0, 0), max(1.5, size / 45))
        A = np.maximum(A, np.clip(bl * 1.3 * wet, 0, 0.85))
    # 飞白：横向/纵向拉丝纹理按行笔方向混合，越靠笔画末端越干
    s = B['size']; sd = (ord(ch) * 7 + seed) % 997
    th = _noise(G, G, max(2, s / 70), sd, aniso=(8, 1)); tv = _noise(G, G, max(2, s / 70), sd + 3, aniso=(1, 8))
    tex = th * B['wdir'] + tv * (1 - B['wdir'])
    dryness = dry * smooth(0.45, 1.0, B['frac']) * smooth(0.35, 0.9, tex)
    A = A * (1 - dryness)
    # 墨晕：整体极淡的扩散边
    halo = cv2.GaussianBlur(A, (0, 0), max(1.2, s / 60)) * 0.22
    A = np.maximum(A, halo)
    if splatter:
        A = A.copy()
        for (x, y, r, ts) in B['splat']:
            e = (p - ts - 0.015) / 0.06
            if e > 0:
                rr = r * (0.4 + 0.6 * ease_out(e))
                cv2.circle(A, (int(x), int(y)), max(1, int(rr)), 0.9, -1, cv2.LINE_AA)
    return A


def brush_write(fr, text, prog, places=None, style='v', size=None, fname='xing', color='white', box=None,
                anchor=(0.5, 0.5), dry=0.8, splatter=True, seed=0, style_kw=None, emph=(), emph_color='red'):
    """逐笔书写：按笔序场显露，笔锋湿墨晕、行笔末段飞白、落笔墨点飞溅。prog 标量或每字列表。"""
    P = _P(text, places, style, size, fname, box, anchor, seed, emph)
    pr = _per_char(prog, len(P)); cs = _colors(P, color, emph_color)
    L = Layer()
    for p_, pc, c in zip(P, pr, cs):
        if pc <= 0: continue
        if p_['ch'] in PUNCT:
            place(L, p_['ch'], p_['x'], p_['y'], p_['size'], c, 'song', alpha=pc); continue
        A = brush_glyph(p_['ch'], p_['font'], p_['size'], pc, seed, dry, splatter=splatter)
        L.paste(A, p_['x'], p_['y'], c)
    return _finish(fr, L, color, style_kw)


# ------------------------------------------------------------------ 2. 竖排
def vertical_column(fr, text, prog, places=None, size=None, fname='kai', color='white', box=None,
                    anchor=(0.85, 0.0), anim='drop', rule=True, emph=(), emph_color='red', seed=0, style_kw=None):
    """竖排（从右到左、行首对齐）。anim: 'drop' 自上落下+去模糊 / 'brush' 逐笔书写 / 'fade'。
    rule=True 在列右侧画一道随进度生长的细墨线（装帧感）。"""
    if places is None:
        P = layout(text, 'v', size=size, fname=fname, box=box, anchor=anchor, emph=emph)
    else: P = places
    pr = _per_char(prog, len(P)); cs = _colors(P, color, emph_color)
    if anim == 'brush':
        return brush_write(fr, text, pr, places=P, color=color, style_kw=style_kw, emph_color=emph_color, seed=seed)
    L = Layer()
    for p_, pc, c in zip(P, pr, cs):
        if pc <= 0: continue
        e = ease_out(pc, 3)
        dy = -(1 - e) * p_['size'] * 0.45 if anim == 'drop' else 0
        place(L, p_['ch'], p_['x'], p_['y'] + dy, p_['size'], c, p_['font'], alpha=min(1, pc * 2.2),
              blur=(1 - e) * p_['size'] * 0.05)
    if rule and P:
        cols = {}
        for p_, pc in zip(P, pr):
            cols.setdefault(round(p_['x'] / 10), []).append((p_, pc))
        for k_, items in cols.items():
            s = items[0][0]['size']; x = items[0][0]['x'] + s * 0.68
            yt = items[0][0]['y'] - s * 0.5; yb = items[-1][0]['y'] + s * 0.5
            g = np.mean([pc for _, pc in items])
            if g <= 0: continue
            y1 = yt + (yb - yt) * ease_out(min(1, g * 1.3))
            seg = np.zeros((int(y1 - yt) + 4, 5), np.float32); seg[:, 1:4] = 0.55; seg[:, 2] = 0.9
            L.paste(seg, x, (yt + y1) / 2, 'gold' if color != 'ink' else 'red', alpha=0.8)
            # 列首朱红小方印点
            dot = np.zeros((int(s * 0.16) + 2,) * 2, np.float32); dot[1:-1, 1:-1] = 1
            L.paste(dot, x, yt - s * 0.1, 'red', alpha=min(1, g * 3))
    return _finish(fr, L, color, style_kw)


# ------------------------------------------------------------------ 3. 错落叠放
def scatter_stack(fr, text, prog, places=None, size=None, fname='xing', color='white', emph=(), emph_color='red',
                  box=None, anchor=(0.5, 0.5), seed=3, t_local=0.0, style_kw=None, fill=True):
    """错落叠放：大小对比强烈（emph 字超大朱红），fill=True 时整块撑满 box；每字从 3× 砸下（带旋转回正与轻微动态模糊），落定后随 t_local 微漂。"""
    if places is None:
        P = layout(text, 'scatter', size=size or 150, fname=fname, box=box, anchor=anchor, seed=seed, emph=emph)
        if fill: P = fit(P, box, anchor)
    else: P = places
    pr = _per_char(prog, len(P)); cs = _colors(P, color, emph_color)
    order = sorted(range(len(P)), key=lambda i: -P[i]['size'])   # 大字在下
    L = Layer()
    r = _rng(seed)
    drift = r.uniform(-1, 1, (len(P), 2))
    for i in order:
        p_, pc, c = P[i], pr[i], cs[i]
        if pc <= 0: continue
        e = ease_out(pc, 4)
        sc = 1 + 2.0 * (1 - e)
        rot = p_['rot'] + (1 - e) * 25 * (1 if i % 2 else -1)
        a = min(1, pc * 3)
        dx, dy = drift[i] * t_local * p_['size'] * 0.08
        place(L, p_['ch'], p_['x'] + dx, p_['y'] + dy, p_['size'], c, p_['font'], alpha=a, scale=sc, rot=rot,
              blur=(1 - e) * 6)
    return _finish(fr, L, color, style_kw)


# ------------------------------------------------------------------ 4. 巨字
def giant_char(fr, ch, p, mode='window', fname='cao', color='white', inner=None, outside=(0.02, 0.02, 0.025),
               cx=None, cy=None, size=None, scale_from=2.2, drift=0.06, rim='gold', rot=0.0, seed=0):
    """单个巨字占满有效区。p∈[0,1]：0→0.25 由 scale_from 冲入，之后缓慢推近 drift。
    mode:
      'window'  字内透出画面 inner（默认 fr），字外压成墨黑 outside（蒙版效果），字缘金色细光
      'solid'   实心字（color）叠在画面上，带墨晕
      'knock'   字内挖空为纸白/outside 反色：画面在外，字内为 outside 色"""
    cx = W / 2 if cx is None else cx; cy = H / 2 if cy is None else cy
    s = size or (H - 2 * BAR) * 0.98
    if size is None:          # 按字形实际墨迹包围盒撑满有效区（0.92 高或 0.9 宽）
        g0 = glyph(ch, fname, s, False); ys_, xs_ = np.nonzero(g0 > 0.3)
        if len(ys_):
            bh, bw = ys_.max() - ys_.min() + 1, xs_.max() - xs_.min() + 1
            k = min(0.92 * (H - 2 * BAR) / bh, 0.9 * W / bw)
            cx -= ((xs_.max() + xs_.min()) / 2 - g0.shape[1] / 2) * k
            cy -= ((ys_.max() + ys_.min()) / 2 - g0.shape[0] / 2) * k
            s *= k
    e = ease_out(min(1, p / 0.25), 4)
    sc = scale_from + (1 - scale_from) * e + drift * max(0, p - 0.25)
    L = Layer()
    place(L, ch, cx, cy, s, 'white', fname, scale=sc, rot=rot)
    A = L.A
    a_in = min(1, p / 0.08)
    out = fr.copy()
    if mode == 'window':
        src = fr if inner is None else inner
        m = (A * a_in)[..., None]
        o = col(outside)
        bg = fr * (1 - a_in) + o * a_in
        out = bg * (1 - m) + src * m
        if rim:
            E = cv2.morphologyEx(A, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
            sm = cv2.GaussianBlur(cv2.resize(E, (W // 4, H // 4)), (0, 0), 3)
            out += (E[..., None] * 0.9 + cv2.resize(sm, (W, H))[..., None] * 1.2) * col(rim) * a_in
        return out
    if mode == 'knock':
        m = (A * a_in)[..., None]
        return out * (1 - m) + col(outside) * m
    L.C[:] = col(color)
    return _finish(out, L, color, dict(opacity=a_in))


# ------------------------------------------------------------------ 5. 刻在刀上（沿曲线+透视）
def _curve(pts, n=200):
    pts = np.asarray(pts, np.float32)
    if len(pts) == 3 or len(pts) == 4:   # 贝塞尔
        t = np.linspace(0, 1, n)[:, None]
        if len(pts) == 3:
            c = (1 - t) ** 2 * pts[0] + 2 * (1 - t) * t * pts[1] + t * t * pts[2]
        else:
            c = (1 - t) ** 3 * pts[0] + 3 * (1 - t) ** 2 * t * pts[1] + 3 * (1 - t) * t * t * pts[2] + t ** 3 * pts[3]
        return c
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); s = np.concatenate([[0], np.cumsum(seg)])
    u = np.linspace(0, s[-1], n)
    return np.stack([np.interp(u, s, pts[:, 0]), np.interp(u, s, pts[:, 1])], 1)


def carved_on_blade(fr, text, pts, height=90, p=1.0, fname='song', finish='gold', taper=(1.0, 0.55),
                    glint=True, spacing=0.12, slices=28, seed=0, align='center', fill=False):
    """沿任意折线/贝塞尔曲线(pts: 2/3/4 个控制点或折线)排布文字并透视变形（taper 起止端字高比例模拟近大远小）。
    finish: 'gold' 鎏金阳刻 / 'steel' 钢上阴刻（暗槽+亮边）/ 'red' 朱砂填刻。
    p: 0→1 刀光从起点扫到终点，扫过处字显出（光带残留高光）。"""
    C = _curve(pts, 400)
    seg = np.linalg.norm(np.diff(C, axis=0), axis=1); S = np.concatenate([[0], np.cumsum(seg)]); Ltot = S[-1]
    vis = [c for c in text if c != ' ']
    hs = int(height)
    n = len(vis)
    sz = hs * 0.86
    adv = sz * (1 + spacing)
    if fill or adv * n > Ltot:                      # fill=True：均匀铺满整条曲线
        adv = Ltot / max(1, n); sz = min(sz, adv / (1 + spacing))
    start = {'start': 0.0, 'end': Ltot - adv * n}.get(align, (Ltot - adv * n) / 2)
    sw = int(Ltot) + 2
    strip = np.zeros((hs, sw), np.float32)
    for i, c in enumerate(vis):
        g = glyph(c, fname, sz, texture=False)
        gh = g.shape[0]; x0 = int(start + adv * (i + 0.5) - gh / 2); y0 = int(hs / 2 - gh / 2)
        xs, ys = max(0, x0), max(0, y0); xe, ye = min(sw, x0 + gh), min(hs, y0 + gh)
        if xe > xs and ye > ys:
            strip[ys:ye, xs:xe] = np.maximum(strip[ys:ye, xs:xe], g[ys - y0:ye - y0, xs - x0:xe - x0])
    # 刻痕光影
    bl = cv2.GaussianBlur(strip, (0, 0), max(1, hs / 60))
    gx = cv2.Sobel(bl, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(bl, cv2.CV_32F, 0, 1, ksize=3)
    sh = np.clip(-(gx * 0.6 + gy * 0.8) * 2.5, -1, 1)
    if finish == 'steel':
        base = np.array([0.10, 0.11, 0.13], np.float32)
        rgb = base + np.clip(-sh, 0, 1)[..., None] * np.array([0.95, 0.97, 1.0]) * 1.1 + np.clip(sh, 0, 1)[..., None] * -0.08
        A = np.clip(strip * 0.95 + np.abs(sh) * 0.5, 0, 1)
    elif finish == 'red':
        rgb = col('red') * (0.85 + 0.4 * sh[..., None]) + np.clip(sh, 0, 1)[..., None] * 0.2
        A = strip
    else:
        rgb = col('gold') * (0.75 + 0.55 * sh[..., None]) + np.clip(sh, 0, 1)[..., None] ** 2 * 0.6
        A = strip
    u_px = np.arange(sw, dtype=np.float32)[None, :]
    head = start - 0.08 * sw + p * (adv * n + 0.2 * sw)
    if p < 1:
        A = A * np.clip((head - u_px) / (sw * 0.04), 0, 1)
    if glint:
        band = np.exp(-((u_px - head) / (sw * 0.035)) ** 2) * (1.0 if p < 1 else 0.0)
        rgb = rgb + band[..., None] * 0.9 * (A[..., None] > 0.05)
    rgb = np.clip(rgb, 0, 2).astype(np.float32); A = A.astype(np.float32)
    out = fr.copy()
    # 法线
    T = np.gradient(C, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    N = np.stack([-T[:, 1], T[:, 0]], 1)
    us = np.linspace(0, sw - 1, slices + 1)
    acc_rgb = np.zeros_like(out); acc_a = np.zeros((H, W), np.float32)
    for i in range(slices):
        u0, u1 = us[i], us[i + 1] + 1
        q = []
        for u in (u0, u1):
            k = int(np.clip(np.searchsorted(S, u), 0, len(C) - 1))
            sc = taper[0] + (taper[1] - taper[0]) * (u / sw)
            q.append((C[k], N[k], sc))
        src = np.float32([[u0, 0], [u1, 0], [u1, hs], [u0, hs]])
        dst = np.float32([q[0][0] - q[0][1] * hs / 2 * q[0][2], q[1][0] - q[1][1] * hs / 2 * q[1][2],
                          q[1][0] + q[1][1] * hs / 2 * q[1][2], q[0][0] + q[0][1] * hs / 2 * q[0][2]])
        x0, y0 = np.floor(dst.min(0)).astype(int) - 1; x1, y1 = np.ceil(dst.max(0)).astype(int) + 2
        x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if x1c <= x0c or y1c <= y0c: continue
        M = cv2.getPerspectiveTransform(src, dst - np.float32([x0c, y0c]))
        sz2 = (x1c - x0c, y1c - y0c)
        wa = cv2.warpPerspective(A, M, sz2, flags=cv2.INTER_LINEAR)
        wr = cv2.warpPerspective(rgb, M, sz2, flags=cv2.INTER_LINEAR)
        R = acc_a[y0c:y1c, x0c:x1c]
        m = wa > R
        acc_rgb[y0c:y1c, x0c:x1c][m] = wr[m]; R[m] = wa[m]
    a = acc_a[..., None]
    # 刻字暗影（让字从刀面“陷入”）
    sm = cv2.GaussianBlur(cv2.resize(acc_a, (W // 4, H // 4)), (0, 0), 2)
    out *= 1 - 0.35 * np.clip(cv2.resize(sm, (W, H)) * 2, 0, 1)[..., None]
    out = out * (1 - a) + acc_rgb * a
    if finish == 'gold':
        gl = cv2.GaussianBlur(cv2.resize(acc_a, (W // 4, H // 4)), (0, 0), 4)
        out += cv2.resize(gl, (W, H))[..., None] * col('gold') * 0.35
    return out


# ------------------------------------------------------------------ 6. 印章
@lru_cache(32)
def _seal_img(text, size, style, seed):
    s = int(size); r = _rng(seed)
    im = Image.new('L', (s, s), 0); d = ImageDraw.Draw(im)
    b = max(3, s // 22)
    n = len(text)
    if style == 'yin':                     # 阴文：红底白字
        d.rectangle([0, 0, s - 1, s - 1], fill=255)
    else:                                  # 阳文：红框红字
        d.rectangle([b, b, s - 1 - b, s - 1 - b], outline=255, width=b * 2)
    fill = 0 if style == 'yin' else 255
    inner = s - 4 * b
    if n == 1: cells = [(s / 2, s / 2, inner * 0.92)]
    elif n == 2: cells = [(s / 2, s / 2 - inner / 4, inner * 0.5), (s / 2, s / 2 + inner / 4, inner * 0.5)]
    elif n == 3: cells = [(s / 2 + inner / 4, s / 2, inner * 0.5)] + [(s / 2 - inner / 4, s / 2 + (k - 0.5) * inner / 2, inner * 0.48) for k in range(2)]
    else:   # 4 字：右上→右下→左上→左下（传统读序）
        cells = [(s / 2 + inner / 4, s / 2 - inner / 4, inner * 0.49), (s / 2 + inner / 4, s / 2 + inner / 4, inner * 0.49),
                 (s / 2 - inner / 4, s / 2 - inner / 4, inner * 0.49), (s / 2 - inner / 4, s / 2 + inner / 4, inner * 0.49)]
    for c, (x, y, fs) in zip(text[:4], cells):
        f = _font('song', int(fs * 1.02))
        tmp = Image.new('L', (int(fs * 1.3),) * 2, 0)
        ImageDraw.Draw(tmp).text((fs * 0.65, fs * 0.65), c, font=f, fill=255, anchor='mm')
        t = np.asarray(tmp)
        bb = Image.fromarray(t).getbbox()
        if bb:  # 拉满方格（篆刻章法）
            t = np.asarray(Image.fromarray(t).crop(bb).resize((int(fs * 0.92), int(fs * 0.92))))
            m = Image.fromarray(t); x0 = int(x - fs * 0.46); y0 = int(y - fs * 0.46)
            im.paste(Image.new('L', m.size, fill), (x0, y0), m)
    a = np.asarray(im).astype(np.float32) / 255
    # 印泥不均：大尺度浓淡 + 细颗粒缺墨 + 边缘崩口
    big = _noise(s, s, s / 5, seed); fine = _noise(s, s, 2.2, seed + 1)
    chip = _noise(s, s, s / 14, seed + 2)
    a = a * np.clip(0.78 + 0.4 * big, 0, 1) * np.clip((fine - 0.06) * 4, 0, 1)
    yy, xx = np.mgrid[0:s, 0:s]
    edge = np.minimum(np.minimum(xx, yy), np.minimum(s - 1 - xx, s - 1 - yy)).astype(np.float32)
    a = a * np.clip((edge - (chip - 0.6) * s * 0.06) / 2, 0, 1)
    # 压痕：边缘一圈印泥更浓
    a = np.clip(a * (1 + 0.35 * np.exp(-edge / (s * 0.03))), 0, 1)
    return a.astype(np.float32)


def stamp_seal(fr, text, cx, cy, size, p, style='yin', rot=-4.0, seed=0, color='red', alpha=0.95):
    """印章盖下：p 0→0.3 自高处落下（放大、阴影收拢）；0.3 落印冲击（纸面压暗环 + 印泥飞溅细点）；之后印泥微洇。
    style 'yin'(红底白字) / 'yang'(白底红字)。印章冲击强度可用 stamp_impact(p) 驱动镜头抖动。"""
    out = fr.copy()
    if p <= 0: return out
    a = _seal_img(text, int(size), style, seed)
    tp = 0.3
    if p < tp:
        e = p / tp; sc = 1 + 0.9 * (1 - e) ** 2; al = e ** 0.7
        # 落下中：阴影
        sh = cv2.GaussianBlur(np.pad(np.ones_like(a), int(size * 0.3)), (0, 0), size * 0.12 * (1 - e) + 3)
        L = Layer(); L.paste(sh, cx + size * 0.12 * (1 - e), cy + size * 0.18 * (1 - e), 'ink', 0.55 * e)
        out = out * (1 - L.A[..., None])
        L2 = Layer(); _paste_rot(L2, a, cx, cy, sc, rot, color, al * 0.9 * alpha)
        return compose(out, L2, shadow=0, glow=0)
    q = (p - tp) / (1 - tp)
    # 压痕：周围纸面被压出一圈暗影（随时间恢复）
    imp = math.exp(-q * 6)
    ring = np.pad(np.ones_like(a), int(size * 0.25))
    ring = cv2.GaussianBlur(ring, (0, 0), size * 0.08)
    Ld = Layer(); _paste_rot(Ld, ring, cx, cy, 1.0, rot, 'ink', 0.35 * imp + 0.12)
    out = out * (1 - Ld.A[..., None])
    bl = cv2.GaussianBlur(a, (0, 0), 0.6 + 1.5 * ease_out(q))
    A = np.maximum(a, bl * 0.5)
    L = Layer(); _paste_rot(L, A, cx, cy, 1.0 + 0.03 * imp, rot, color, alpha)
    r = _rng(seed + 5)                 # 冲击飞溅点
    if q < 0.6:
        for _ in range(26):
            ang = r.uniform(0, 2 * math.pi); d = size * (0.55 + r.exponential(0.25)) * (0.5 + ease_out(q / 0.2))
            rr = size * r.uniform(0.004, 0.014)
            dot = np.zeros((int(rr * 4) + 3,) * 2, np.float32)
            cv2.circle(dot, (dot.shape[0] // 2,) * 2, max(1, int(rr)), 1.0, -1, cv2.LINE_AA)
            L.paste(dot, cx + math.cos(ang) * d, cy + math.sin(ang) * d, color, 0.85)
    return compose(out, L, shadow=0, glow=0)


def stamp_impact(p, tp=0.3):
    """印章落定冲击包络（用于镜头抖动/闪光）。"""
    return 0.0 if p < tp else math.exp(-(p - tp) * 18)


def _paste_rot(L, a, cx, cy, sc, rot, color, alpha):
    g = a.shape[0]; d = int(g * sc * 1.45) + 2
    M = cv2.getRotationMatrix2D((g / 2, g / 2), rot, sc); M[:, 2] += (d - g) / 2
    L.paste(cv2.warpAffine(a, M, (d, d)), cx, cy, color, alpha)


# ------------------------------------------------------------------ 7. 斩字
def _line_layer(P, colors, prog=None, scale=1.0):
    L = Layer()
    for i, p_ in enumerate(P):
        a = 1.0 if prog is None else prog[i]
        if a > 0: place(L, p_['ch'], p_['x'], p_['y'], p_['size'] * scale, colors[i], p_['font'], alpha=a)
    return L


def slash_cut(fr, text, p, places=None, style='h', size=None, fname='kai', color='white', angle=None,
              cut_at=0.25, offset=0.0, slide=0.45, emph=(), emph_color='red', box=None, anchor=(0.5, 0.5), seed=0,
              style_kw=None, appear=0.12):
    """字被一刀斩断：p<appear 字砸入；p=cut_at 一道刀光沿斩线掠过；之后两半沿斩线反向错位滑开（slide×字高），
    断口发红热光并迸出火星。angle 斩线角度（度，None=按句子包围盒自动取能贯穿全部字的斜度；竖排自动近竖斩），
    offset 斩线相对字中心的法向偏移（px）。"""
    P = _P(text, places, style, size, fname, box, anchor, seed, emph)
    cs = _colors(P, color, emph_color)
    pa = min(1, p / appear) if appear > 0 else 1
    L = _line_layer(P, cs, [ease_out(pa)] * len(P), scale=1 + 0.25 * (1 - ease_out(pa, 4)))
    x0, y0, x1, y1 = bbox(P)
    if angle is None:
        bw_, bh_ = x1 - x0, y1 - y0
        angle = -math.degrees(math.atan2(0.3 * bh_, bw_)) if bw_ >= bh_ else -90 + math.degrees(math.atan2(0.3 * bw_, bh_))
    kw = auto_style(color); kw.update(style_kw or {})
    if p < cut_at:
        return compose(fr, L, **kw)
    q = (p - cut_at) / (1 - cut_at)
    return slash_layer(fr, L, q, ((x0 + x1) / 2, (y0 + y1) / 2), angle, offset=offset, slide=slide,
                       sz=max(p_['size'] for p_ in P), length=max(x1 - x0, y1 - y0) * 1.5, style_kw=kw, seed=seed)


def slash_layer(fr, L, q, center, angle, offset=0.0, slide=0.45, sz=200, length=1600, style_kw=None, seed=0,
                sparks=60, hot=True, light=True):
    """通用“一刀两断”：任意图层 L（字/印章/巨字）沿过 center、角度 angle 的直线断开，q 0→1 为斩后进度。
    返回合成后的帧。slash_cut / 斩印 / 斩巨字都走这里。"""
    th = math.radians(angle); d = np.array([math.cos(th), math.sin(th)]); n = np.array([-d[1], d[0]])
    cx, cy = center[0] + n[0] * offset, center[1] + n[1] * offset
    kw = style_kw if style_kw is not None else auto_style('white')
    bx = L.box(int(sz * 1.2))
    if bx is None: return fr.copy()
    X0, Y0, X1, Y1 = bx
    A = L.A[Y0:Y1, X0:X1]; C = L.C[Y0:Y1, X0:X1]
    yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(np.float32)
    sd = (xx - cx) * n[0] + (yy - cy) * n[1]
    side = np.clip(sd / 1.2 + 0.5, 0, 1).astype(np.float32)
    eq = ease_out(min(1, q / 0.7), 3)
    sh = eq * slide * sz; sep = eq * sz * 0.12
    L2 = Layer()
    for s_, sgn in ((1 - side, -1), (side, 1)):
        a = A * s_
        tx, ty = d * sh * sgn * 0.5 + n * sep * sgn
        M = cv2.getRotationMatrix2D((cx - X0, cy - Y0), -sgn * 2.5 * eq, 1.0)   # 两半各自轻微转开
        M[:, 2] += [tx, ty]
        wa = cv2.warpAffine(a, M, (X1 - X0, Y1 - Y0)); wc = cv2.warpAffine(C, M, (X1 - X0, Y1 - Y0))
        L2.paste_rgba(wc, wa, X0, Y0)
    out = compose(fr, L2, **kw)
    if hot and q < 0.8:     # 断口热光
        ht = np.exp(-np.abs(sd) / 3) * (A > 0.3) * (1 - q / 0.8) * min(1.0, q / 0.12)
        hb = cv2.GaussianBlur(ht, (0, 0), 4) * 2 + ht
        out[Y0:Y1, X0:X1] += hb[..., None] * np.array([1.0, 0.45, 0.15], np.float32)
    if light:
        out = _slash_light(out, (cx, cy), d, q, length=length)
    if sparks and q < 0.7:  # 火星
        r = _rng(seed + 11)
        Lp = np.zeros((H // 2, W // 2), np.float32)
        for _ in range(sparks):
            u = r.uniform(-0.5, min(1, q / 0.18) - 0.5) * length / 1.5; v = r.normal(0, 1) * 0.5 + (1 if r.random() < .5 else -1)
            sp = r.uniform(200, 900); ang = math.atan2(n[1] * v, n[0] * v) + r.normal(0, 0.5)
            t_ = q * 0.6
            px = cx + d[0] * u + math.cos(ang) * sp * t_; py = cy + d[1] * u + math.sin(ang) * sp * t_ + 400 * t_ * t_
            qx = px - math.cos(ang) * sp * 0.04; qy = py - math.sin(ang) * sp * 0.04
            cv2.line(Lp, (int(px / 2), int(py / 2)), (int(qx / 2), int(qy / 2)), 1.0 - q / 0.7, 1, cv2.LINE_AA)
        Lp = cv2.GaussianBlur(Lp, (0, 0), 1.2) * 2 + Lp
        out += cv2.resize(Lp, (W, H))[..., None] * np.array([1.0, 0.7, 0.35], np.float32)
    return out


def _slash_light(fr, c, d, q, length=1600, color=(1, 0.96, 0.9)):
    """沿方向 d 过点 c 的刀光：q 0→0.25 光头划过，之后余辉衰减。"""
    if q > 0.6: return fr
    head = min(1, q / 0.18); tail = max(0, (q - 0.08) / 0.3)
    p0 = np.array(c) + d * length * (tail - 0.5); p1 = np.array(c) + d * length * (head - 0.5)
    Ls = np.zeros((H // 2, W // 2), np.float32)
    cv2.line(Ls, tuple((p0 / 2).astype(int)), tuple((p1 / 2).astype(int)), 1.0, 2, cv2.LINE_AA)
    f = 1 - q / 0.6
    core = cv2.GaussianBlur(Ls, (0, 0), 0.8) * 2.5; bloom = cv2.GaussianBlur(Ls, (0, 0), 10) * 5
    return fr + cv2.resize(core + bloom, (W, H))[..., None] * np.array(color, np.float32) * f


# ------------------------------------------------------------------ 8. 墨洇显字
_sdf_cache = {}
def _sdf(ch, fname, size):
    size = int(round(size / 4) * 4); k = (ch, fname, size)
    if k not in _sdf_cache:
        a = glyph(ch, fname, size, texture=False)
        pad = int(size * 0.25); a = np.pad(a, pad)
        m = (a > 0.5).astype(np.uint8)
        din = cv2.distanceTransform(m, cv2.DIST_L2, 5); dout = cv2.distanceTransform(1 - m, cv2.DIST_L2, 5)
        D = (din - dout) / (size * 0.06)
        if len(_sdf_cache) > 300: _sdf_cache.clear()
        _sdf_cache[k] = (D.astype(np.float32), a)
    return _sdf_cache[k]


def ink_bleed_glyph(ch, fname, size, p, seed=0, bleed=0.9):
    """墨从笔画芯部向外洇开：芯→边→溢出纸纤维的淡墨晕。返回 alpha（画布含 pad）。"""
    D, a = _sdf(ch, fname, size)
    G = D.shape[0]; sd = (ord(ch) + seed) % 991
    n1 = _noise(G, G, max(2, size / 18), sd); n2 = _noise(G, G, max(2, size / 90), sd + 1, aniso=(3, 1))
    thr = 3.0 - 4.6 * ease_out(p, 2)                      # 阈值从笔画芯部降到字外
    f = D + (n1 - 0.5) * 1.8 + (n2 - 0.5) * 0.7
    core = np.clip((f - thr) * 1.6, 0, 1)
    A = np.minimum(core, np.clip(a * 1.2, 0, 1) + 0.0)   # 字内实墨
    halo = np.clip((f - thr) * 0.8, 0, 1) * np.clip(1 + D / 1.6, 0, 1) * 0.42 * bleed  # 溢出淡墨
    halo *= (0.5 + 0.8 * n2)
    return np.clip(np.maximum(A, halo), 0, 1)


def ink_bleed_in(fr, text, prog, places=None, style='h', size=None, fname='kai', color='ink', box=None,
                 anchor=(0.5, 0.5), seed=0, emph=(), emph_color='red', style_kw=None, bleed=0.9):
    """墨在宣纸上洇开显字（适合浅色纸背景用 ink/red；暗背景用 white/gold 即“光洇”）。"""
    P = _P(text, places, style, size, fname, box, anchor, seed, emph)
    pr = _per_char(prog, len(P)); cs = _colors(P, color, emph_color)
    L = Layer()
    for p_, pc, c in zip(P, pr, cs):
        if pc <= 0: continue
        L.paste(ink_bleed_glyph(p_['ch'], p_['font'], p_['size'], pc, seed, bleed), p_['x'], p_['y'], c)
    return _finish(fr, L, color, style_kw)


# ------------------------------------------------------------------ 9. 碎字飞散
def _tris(x0, y0, x1, y1, n, seed):
    r = _rng(seed)
    pts = np.concatenate([r.uniform([x0, y0], [x1, y1], (n, 2)),
                          np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float64),
                          np.stack([np.linspace(x0, x1, 7), np.full(7, y0)], 1), np.stack([np.linspace(x0, x1, 7), np.full(7, y1)], 1)])
    sub = cv2.Subdiv2D((int(x0) - 2, int(y0) - 2, int(x1 - x0) + 5, int(y1 - y0) + 5))
    for q in pts: sub.insert((float(np.clip(q[0], x0, x1)), float(np.clip(q[1], y0, y1))))
    T = sub.getTriangleList().reshape(-1, 3, 2)
    ok = (T[..., 0] >= x0 - 1).all(1) & (T[..., 0] <= x1 + 1).all(1) & (T[..., 1] >= y0 - 1).all(1) & (T[..., 1] <= y1 + 1).all(1)
    return T[ok].astype(np.float32)


def shatter_layer(L, p, impact=None, n=90, seed=0, power=1.0, gravity=600.0, spin=360.0):
    """把任意文字图层 L 碎成三角碎片飞散（p 0→1）。impact: 冲击点（默认图层中心）。返回新 Layer。"""
    bx = L.box(2)
    out = Layer()
    if bx is None: return out
    X0, Y0, X1, Y1 = bx
    T = _tris(X0, Y0, X1, Y1, n, seed)
    c = np.array(impact if impact is not None else ((X0 + X1) / 2, (Y0 + Y1) / 2), np.float32)
    r = _rng(seed + 1)
    crack = smooth(0.0, 0.12, p)                       # 0–0.12 裂开（碎片微分离），之后加速飞散
    e = 0.012 * crack + max(0.0, p - 0.1) ** 1.5 * 1.25
    for k, tri in enumerate(T):
        cen = tri.mean(0)
        if L.A[int(np.clip(cen[1], 0, H - 1)), int(np.clip(cen[0], 0, W - 1))] < 0.02:
            # 空白碎片也可能含笔画边缘：抽查包围盒
            bx0, by0 = np.floor(tri.min(0)).astype(int); bx1, by1 = np.ceil(tri.max(0)).astype(int)
            if L.A[max(0, by0):by1, max(0, bx0):bx1].max(initial=0) < 0.05: continue
        v = cen - c; dist = np.linalg.norm(v) + 1e-6; v = v / dist
        sp = (300 + r.uniform(0, 900)) * power * (1.2 - min(1, dist / 900) * 0.6)
        v = v + r.normal(0, 0.35, 2)
        dz = r.uniform(-0.4, 0.8)
        tx = v[0] * sp * e; ty = v[1] * sp * e + gravity * p * p
        ang = r.uniform(-1, 1) * spin * e; sc = 1 + dz * e
        shade = r.uniform(0.7, 1.35)                    # 碎面受光不同
        bx0, by0 = np.floor(tri.min(0)).astype(int); bx1, by1 = np.ceil(tri.max(0)).astype(int) + 1
        bx0, by0 = max(0, bx0), max(0, by0); bx1, by1 = min(W, bx1), min(H, by1)
        if bx1 <= bx0 or by1 <= by0: continue
        pa = L.A[by0:by1, bx0:bx1]; pc = L.C[by0:by1, bx0:bx1]
        m = np.zeros(pa.shape, np.float32)
        cv2.fillConvexPoly(m, np.round((tri - [bx0, by0]) * 4).astype(np.int32), 1.0, cv2.LINE_AA, shift=2)
        pa = pa * m
        hw, hh = bx1 - bx0, by1 - by0
        d = int(max(hw, hh) * max(1.5, sc * 1.5)) + 2
        M = cv2.getRotationMatrix2D((cen[0] - bx0, cen[1] - by0), ang, sc)
        M[:, 2] += [d / 2 - (cen[0] - bx0), d / 2 - (cen[1] - by0)]
        wa = cv2.warpAffine(pa, M, (d, d)); wc = cv2.warpAffine(pc, M, (d, d))
        fade = 1 - smooth(0.6, 1.0, p)
        out.paste_rgba(np.clip(wc * shade, 0, 1.2), wa * fade, int(cen[0] + tx - d / 2), int(cen[1] + ty - d / 2))
    return out


def shatter_out(fr, text, p, places=None, style='h', size=None, fname='kai', color='white', impact=None, n=None,
                seed=0, emph=(), emph_color='red', box=None, anchor=(0.5, 0.5), style_kw=None, power=1.0, flash=True):
    """字碎成多边形碎片飞散（p 0→1）。p≈0 完整；冲击点一圈白闪。"""
    P = _P(text, places, style, size, fname, box, anchor, seed, emph)
    L = _line_layer(P, _colors(P, color, emph_color))
    if p <= 0: return _finish(fr, L, color, style_kw)
    n = n or 9 * len(P)                                # 默认每字约 9 块（碎片要大，才看得出是“字”碎了）
    L2 = shatter_layer(L, p, impact, n, seed, power)
    out = _finish(fr, L2, color, style_kw)
    if flash and 0.08 < p < 0.3:
        x0, y0, x1, y1 = bbox(P)
        c = impact or ((x0 + x1) / 2, (y0 + y1) / 2)
        out = _radial_flash(out, c, 0.55 * (1 - abs(p - 0.12) / 0.18), radius=min(380, (x1 - x0) * 0.18))
    return out


def _radial_flash(fr, c, amt, radius=400, color=(1, 0.97, 0.92)):
    y, x = np.ogrid[0:H // 4, 0:W // 4]
    d2 = ((x - c[0] / 4) ** 2 + (y - c[1] / 4) ** 2) / (radius / 4) ** 2
    g = np.exp(-d2).astype(np.float32) * amt
    return fr + cv2.resize(g, (W, H))[..., None] * np.array(color, np.float32)


# ------------------------------------------------------------------ 10. 2.5D 运动排版
def kinetic_track(fr, items, cam=(0.0, 0.0, 0.0), focal=1000.0, focus_z=None, dof=0.006, fog=(400, 4000),
                  style_kw=None):
    """2.5D 空间文字。items: [dict(text, x, y, z, size, color, font, style('h'|'v'), prog(可选), rot)]，
    世界坐标：x 右 y 下（px，相机正对时 z=focal 处 1:1），z 远离相机。
    cam=(cx,cy,cz)：相机位置，推拉=改 cz，横移=改 cx → 远近字产生视差。
    景深：|z - focus_z| 越大越糊；雾：近/远端淡出。按远→近绘制。"""
    out = fr.copy()
    cx, cy, cz = cam
    fz = focus_z if focus_z is not None else cz + focal
    its = sorted(items, key=lambda it: -(it['z']))
    for it in its:
        zr = it['z'] - cz
        if zr < 60: continue
        s = focal / zr
        color = it.get('color', 'white')
        P = layout(it['text'], it.get('style', 'h'), size=it.get('size', 120), fname=it.get('font', 'kai'),
                   box=(-20000, -20000, 20000, 20000), anchor=(0.5, 0.5))
        x0, y0, x1, y1 = bbox(P); mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        pr = _per_char(it.get('prog', 1.0), len(P))
        L = Layer()
        blur = min(14, abs(it['z'] - fz) * dof * s)
        fa = smooth(fog[1], fog[1] * 0.6, zr) * smooth(fog[0] * 0.3, fog[0], zr)
        for p_, pc in zip(P, pr):
            if pc <= 0: continue
            sx = W / 2 + ((it['x'] + (p_['x'] - mx)) - cx) * s
            sy = H / 2 + ((it['y'] + (p_['y'] - my)) - cy) * s
            sz = p_['size'] * s
            if sz > 1400 or sz < 6: continue
            if sx < -sz or sx > W + sz or sy < -sz or sy > H + sz: continue
            place(L, p_['ch'], sx, sy, sz, color, p_['font'], alpha=fa * min(1, pc * 2), blur=blur,
                  rot=it.get('rot', 0.0), scale=1 + 0.3 * (1 - ease_out(pc)))
        kw = auto_style(color); kw.update(style_kw or {})
        kw['shadow'] = kw.get('shadow', 0.6) * fa * (1 - min(1, blur / 10))
        out = compose(out, L, **kw)
    return out


# ------------------------------------------------------------------ 11. 火烧显字
def burn_in(fr, text, p, places=None, style='h', size=None, fname='xing', color='gold', box=None,
            anchor=(0.5, 0.5), seed=0, direction=(0.3, -1.0), embers=160, emph=(), emph_color='red', style_kw=None,
            mode='keep', split=0.55, cool_color='ink'):
    """火烧显字：噪声火线沿 direction 推进（默认自下而上略斜），火线处橙金发光，烧过的字显出，余烬上飘。
    mode:
      'keep'        显字后保留（片名、刀身字）
      'ash'         p<split 烧出字；之后第二道火线把字烧成灰，灰片+余烬向上飘散（S101「陪葬」）
      'extinguish'  p<split 金字烧起；之后火熄、字冷却回墨色（cool_color）并冒青烟（S037「天亮」）"""
    P = _P(text, places, style, size, fname, box, anchor, seed, emph)
    L = _line_layer(P, _colors(P, color, emph_color))
    bx = L.box(40)
    if bx is None: return fr.copy()
    p1 = p if mode == 'keep' else min(1.0, p / split)
    q = 0.0 if mode == 'keep' else max(0.0, (p - split) / (1 - split))
    X0, Y0, X1, Y1 = bx
    hh, ww = Y1 - Y0, X1 - X0
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    dv = np.array(direction, np.float32); dv /= np.linalg.norm(dv)
    g = ((xx / ww - 0.5) * dv[0] * ww + (yy / hh - 0.5) * dv[1] * hh) / max(ww * abs(dv[0]) + hh * abs(dv[1]), 1) + 0.5
    nz = _noise(hh, ww, 26, seed) * 0.6 + _noise(hh, ww, 7, seed + 1) * 0.4
    F = g * 0.75 + nz * 0.35                     # 燃烧到达时间场
    pp = -0.1 + p1 * 1.35
    burnt = np.clip((pp - F) / 0.02, 0, 1)
    band = np.exp(-((pp - F) / 0.035) ** 2) * (p1 < 1)
    A0 = L.A[Y0:Y1, X0:X1].copy()
    A = A0 * burnt
    hot = np.clip(1 - (pp - F) / 0.12, 0, 1) * burnt
    Cc = L.C[Y0:Y1, X0:X1]
    Cc[:] = Cc * (1 - hot[..., None] * 0.7) + np.array([1.0, 0.9, 0.7], np.float32) * hot[..., None] * 0.7
    kw = auto_style(color); kw.update(style_kw or {})
    band2 = None
    if mode == 'ash' and q > 0:
        F2 = g * 0.5 + _noise(hh, ww, 18, seed + 5) * 0.6
        pp2 = -0.1 + q * 1.25
        gone = np.clip((pp2 - F2) / 0.03, 0, 1)
        band2 = np.exp(-((pp2 - F2) / 0.04) ** 2) * A0 * (1 - gone) * 3
        char_ = np.clip((pp2 + 0.12 - F2) / 0.12, 0, 1)            # 将烧处先焦黑
        Cc[:] = Cc * (1 - char_[..., None] * 0.85) + np.float32(0.05) * char_[..., None]
        A = A * (1 - gone)
    if mode == 'extinguish' and q > 0:
        cq = ease_io(min(1, q / 0.6))
        Cc[:] = Cc * (1 - cq) + col(cool_color) * cq
        kw = dict(kw); kw['glow'] = kw.get('glow', 0) * (1 - cq)
        if cool_color == 'ink': kw['shadow'] = 0.0
    L.A[Y0:Y1, X0:X1] = A
    out = compose(fr, L, **kw)
    fireA = band * np.clip(cv2.dilate(A0, np.ones((9, 9), np.uint8)) * 1.5, 0, 1)
    if band2 is not None: fireA = np.maximum(fireA, np.clip(cv2.dilate(band2, np.ones((5, 5), np.uint8)), 0, 1))
    if fireA.max() > 0.01:
        fl = cv2.GaussianBlur(cv2.resize(fireA, (ww // 3 + 1, hh // 3 + 1)), (0, 0), 4)
        fire = fireA * 1.2 + cv2.resize(fl, (ww, hh)) * 2.2
        out[Y0:Y1, X0:X1] += fire[..., None] * np.array([1.0, 0.42, 0.10], np.float32)
    if mode == 'extinguish' and 0 < q < 1:       # 熄火青烟
        sm = cv2.GaussianBlur(cv2.resize(A0, (ww // 4 + 1, hh // 4 + 1)), (0, 0), 3)
        sm = cv2.resize(sm, (ww, hh))
        rise = int(q * hh * 0.25)
        sm = np.roll(sm, -rise, axis=0) * (_noise(hh, ww, 30, seed + 7 + int(q * 4)) * 1.2)
        sa = np.clip(sm * 1.4, 0, 1) * math.sin(math.pi * q) * 0.55
        out[Y0:Y1, X0:X1] = out[Y0:Y1, X0:X1] * (1 - sa[..., None]) + np.float32(0.42) * sa[..., None]
    r = _rng(seed + 9)
    if embers and p1 < 1.05:   # 显字余烬（无状态，可复现）
        ys, xs = np.nonzero(A0[::3, ::3] > 0.3)
        if len(ys):
            k = r.integers(0, len(ys), embers)
            ex = xs[k] * 3.0; ey = ys[k] * 3.0
            born = (F[ys[k] * 3, xs[k] * 3] + 0.1) / 1.35
            age = (p1 - born) * 2.2
            life = r.uniform(0.25, 0.7, embers)
            Le = np.zeros((H // 2, W // 2), np.float32)
            for i in np.nonzero((age > 0) & (age < life))[0]:
                a_ = age[i]
                x = X0 + ex[i] + math.sin(a_ * 9 + i) * 18 + a_ * 120 * dv[0]
                y = Y0 + ey[i] - a_ * 380
                cv2.circle(Le, (int(x / 2), int(y / 2)), 1, float(1 - a_ / life[i]), -1, cv2.LINE_AA)
            Le = cv2.GaussianBlur(Le, (0, 0), 1.5) * 3 + Le
            out += cv2.resize(Le, (W, H))[..., None] * np.array([1.0, 0.55, 0.18], np.float32)
    if mode == 'ash' and q > 0:  # 灰片飞散
        ys, xs = np.nonzero(A0[::3, ::3] > 0.3)
        if len(ys):
            n_ = 260; k = r.integers(0, len(ys), n_)
            F2 = g * 0.5 + _noise(hh, ww, 18, seed + 5) * 0.6
            born = (F2[ys[k] * 3, xs[k] * 3] + 0.1) / 1.25
            age = (q - born) * 1.6
            Lg = np.zeros((H // 2, W // 2), np.float32); Lr = np.zeros((H // 2, W // 2), np.float32)
            sz_ = r.uniform(1, 3.5, n_); vx = r.normal(60, 50, n_); vy = r.uniform(150, 420, n_)
            for i in np.nonzero(age > 0)[0]:
                a_ = age[i]
                if a_ > 1: continue
                x = X0 + xs[k[i]] * 3 + vx[i] * a_ + math.sin(a_ * 7 + i) * 30
                y = Y0 + ys[k[i]] * 3 - vy[i] * a_ - 80 * a_ * a_
                f_ = 1 - a_
                if i % 5 == 0: cv2.circle(Lr, (int(x / 2), int(y / 2)), 1, float(f_), -1, cv2.LINE_AA)
                else:
                    pts = np.array([[x, y], [x + sz_[i] * 3 * math.cos(a_ * 9 + i), y + sz_[i] * 2 * math.sin(a_ * 7 + i)],
                                    [x - sz_[i] * 2, y + sz_[i] * 2]]) / 2
                    cv2.fillConvexPoly(Lg, pts.astype(np.int32), float(f_ * 0.8), cv2.LINE_AA)
            G_ = cv2.resize(Lg, (W, H))[..., None]
            out = out * (1 - G_ * 0.9) + G_ * 0.9 * np.float32(0.40)
            Lr = cv2.GaussianBlur(Lr, (0, 0), 1.5) * 3 + Lr
            out += cv2.resize(Lr, (W, H))[..., None] * np.array([1.0, 0.5, 0.15], np.float32)
    return out


# ------------------------------------------------------------------ 12. 逐字落笔冲击
def typewriter_brush(fr, text, prog, places=None, style='h', size=None, fname='kai', color='white', box=None,
                     anchor=(0.5, 0.5), seed=0, emph=(), emph_color='red', style_kw=None, shake=True, splash=True):
    """逐字落笔：每字到点从 1.9× 砸下（回弹过冲），落点墨点四溅，整行随冲击轻震。prog 建议用 timed_progress(times,t,0.18)。"""
    P = _P(text, places, style, size, fname, box, anchor, seed, emph)
    pr = _per_char(prog, len(P)); cs = _colors(P, color, emph_color)
    r = _rng(seed)
    jx = jy = 0.0
    if shake:
        for i, pc in enumerate(pr):
            if 0 < pc < 0.5:
                k = (0.5 - pc) / 0.5
                jx += r.uniform(-1, 1) * 8 * k; jy += r.uniform(-1, 1) * 8 * k
    L = Layer()
    for i, (p_, pc, c) in enumerate(zip(P, pr, cs)):
        if pc <= 0: continue
        e = ease_back(min(1, pc / 0.55), 2.2)
        sc = 1.9 - 0.9 * e
        place(L, p_['ch'], p_['x'] + jx, p_['y'] + jy, p_['size'], c, p_['font'], alpha=min(1, pc * 4), scale=max(0.2, sc),
              blur=max(0, (1 - pc / 0.3)) * 3)
        if splash and 0.25 < pc < 1:
            q = (pc - 0.25) / 0.75
            rr = _rng(seed * 31 + i)
            for _ in range(10):
                ang = rr.uniform(0, 2 * math.pi); d = p_['size'] * (0.5 + rr.uniform(0, 0.35)) * (0.6 + 0.6 * ease_out(q))
                rad = p_['size'] * rr.uniform(0.008, 0.026) * (1 - q * 0.5)
                dot = np.zeros((int(rad * 4) + 3,) * 2, np.float32)
                cv2.circle(dot, (dot.shape[0] // 2,) * 2, max(1, int(rad)), 1.0, -1, cv2.LINE_AA)
                L.paste(dot, p_['x'] + jx + math.cos(ang) * d, p_['y'] + jy + math.sin(ang) * d, c, (1 - q) * 0.9)
    return _finish(fr, L, color, style_kw)


# ------------------------------------------------------------------ 13. 满屏文字矩阵 / 字组成图形（图块引擎）
_atlas_cache = {}
def _atlas(pool, cell, fname):
    k = (pool, cell, fname)
    if k not in _atlas_cache:
        chars = sorted(set(pool.replace(' ', '')))
        At = np.zeros((len(chars), cell, cell), np.float32)
        for i, c in enumerate(chars):
            g = glyph(c, fname, int(cell * 0.86), texture=False)
            gh = g.shape[0]; o = (gh - cell) // 2
            At[i] = g[o:o + cell, o:o + cell] if o >= 0 else np.pad(g, ((-o, cell - gh + o),) * 2)[:cell, :cell]
        _atlas_cache[k] = (At, chars)
    return _atlas_cache[k]


def _tile(At, idx):
    R, C_ = idx.shape; c = At.shape[1]
    return At[idx].transpose(0, 2, 1, 3).reshape(R * c, C_ * c)


def all_lyrics():
    return ''.join(L['text'] for L in load_lines()).replace(' ', '')


def text_matrix(fr, t, pool=None, cell=30, fname='song', base=0.10, rain=0.9, rate=9.0, seed=0, pulse=0.0,
                highlight=None, hl_prog=1.0, hl_color='red', hl_font='kai', shape=None, shape_p=1.0,
                shape_color='gold', tint='white', bg_dim=0.75, wave=None):
    """满屏文字矩阵（覆盖有效区）：小字网格随时间闪换；竖向“墨雨”亮头自上而下流（rain）；
    pulse(0–1，接 beat_pulse) 让全屏亮度/字形随鼓点炸亮并从中心扩散一圈冲击波；
    highlight: 一句歌词以大字（hl_font）压在矩阵中央，周围矩阵自动让出暗区；
    shape: (H,W) 0–1 蒙版 → 蒙版内的小字点亮为 shape_color，字组成图形（刀/月/巨字），shape_p 控制点亮进度（随机顺序）。
    bg_dim: 背景画面压暗程度（矩阵是主体）。"""
    pool = pool or all_lyrics()
    At, chars = _atlas(pool, cell, fname)
    nC = W // cell; nR = (H - 2 * BAR) // cell
    ox = (W - nC * cell) // 2; oy = BAR + ((H - 2 * BAR) - nR * cell) // 2
    r = _rng(seed)
    base_idx = r.integers(0, len(chars), (nR, nC)); rates = r.uniform(0.3, 1.6, (nR, nC)) * rate
    phase = r.random((nR, nC)) * 50
    step = np.floor(t * rates + phase).astype(np.int64)
    idx = (base_idx + step * 7919) % len(chars)
    img = _tile(At, idx)
    # 亮度场
    I = np.full((nR, nC), base, np.float32)
    ff = r.random((nR, nC)).astype(np.float32)
    I += 0.06 * (np.sin(t * 3 + ff * 40) * 0.5 + 0.5)
    if rain > 0:
        sp = r.uniform(6, 18, nC); off = r.uniform(0, nR * 2, nC); ln = r.uniform(5, 16, nC)
        head = (t * sp + off) % (nR * 1.8)
        rr = np.arange(nR)[:, None]
        dlt = head[None, :] - rr
        tr = np.where((dlt >= 0) & (dlt < ln[None, :]), np.clip(1 - dlt / ln[None, :], 0, 1) ** 1.5, 0)
        I += rain * tr.astype(np.float32) * 0.8
        hd = (np.abs(dlt) < 0.6) * rain
        I += hd.astype(np.float32) * 0.6
    if pulse > 0:
        I *= 1 + pulse * 1.8
        yy, xx = np.mgrid[0:nR, 0:nC]
        d = np.sqrt(((xx - nC / 2) / nC) ** 2 * 3.2 + ((yy - nR / 2) / nR) ** 2)
        ring = np.exp(-((d - (1 - pulse) * 1.1) / 0.06) ** 2) * pulse
        I += ring.astype(np.float32) * 1.2
    if wave is not None:
        I *= wave
    A_shape = None
    if shape is not None:
        sm = cv2.resize(shape[oy:oy + nR * cell, ox:ox + nC * cell].astype(np.float32), (nC, nR), interpolation=cv2.INTER_AREA)
        order = r.random((nR, nC))
        lit = sm * np.clip((shape_p * 1.25 - order) / 0.25, 0, 1)
        A_shape = lit
        I = I * (1 - lit * 0.95)
    hlL = None
    if highlight:
        P = layout(highlight, 'h', fname=hl_font, box=(120, BAR + 200, W - 120, H - BAR - 200))
        pr = _per_char(hl_prog, len(P))
        hlL = Layer()
        for p_, pc in zip(P, pr):
            if pc <= 0: continue
            e = ease_out(pc, 4)
            place(hlL, p_['ch'], p_['x'], p_['y'], p_['size'], hl_color, hl_font, alpha=min(1, pc * 3), scale=1 + 0.6 * (1 - e))
        # 让出暗区
        bxm = hlL.box(0)
        if bxm:
            dark = cv2.resize(hlL.A[oy:oy + nR * cell, ox:ox + nC * cell], (nC, nR), interpolation=cv2.INTER_AREA)
            dark = cv2.GaussianBlur(dark, (0, 0), 1.6)
            I *= np.clip(1 - dark * 6, 0.05, 1)
            if A_shape is not None: A_shape *= np.clip(1 - dark * 6, 0, 1)
    out = fr * (1 - bg_dim)
    Ifull = cv2.resize(I, (nC * cell, nR * cell), interpolation=cv2.INTER_NEAREST)
    reg = out[oy:oy + nR * cell, ox:ox + nC * cell]
    reg += (img * np.clip(Ifull, 0, 2.5))[..., None] * col(tint)
    if A_shape is not None:
        Sf = cv2.resize(A_shape, (nC * cell, nR * cell), interpolation=cv2.INTER_NEAREST)
        aa = (img * Sf)[..., None]
        reg[:] = reg * (1 - aa) + col(shape_color) * aa * 1.15
        gl = cv2.GaussianBlur(cv2.resize(img * Sf, (nC * cell // 4, nR * cell // 4), interpolation=cv2.INTER_AREA), (0, 0), 3)
        reg += cv2.resize(gl, (nC * cell, nR * cell))[..., None] * col(shape_color) * 0.9
    if hlL is not None:
        kw = auto_style(hl_color); kw['shadow'] = 0.85
        out = compose(out, hlL, **kw)
    return out


def glyph_mask(ch, fname='cao', size=None, cx=W / 2, cy=H / 2, scale=1.0):
    """巨字全帧蒙版（给 text_matrix(shape=) / char_shape 用：字组成字）。"""
    L = Layer(); place(L, ch, cx, cy, size or (H - 2 * BAR) * 0.95, 'white', fname, scale=scale, texture=False)
    return L.A


def shape_mask(kind, p=1.0, **kw):
    """常用图形蒙版（全帧 float32）：'moon' 圆月 / 'blade' 斜刀 / 'circle_ring' 圆环 / 'scale' 天平。"""
    m = np.zeros((H, W), np.float32)
    if kind == 'moon':
        c = kw.get('c', (W / 2, H / 2)); r = kw.get('r', 330)
        cv2.circle(m, (int(c[0]), int(c[1])), int(r), 1.0, -1, cv2.LINE_AA)
        if kw.get('crescent', 0):
            cv2.circle(m, (int(c[0] + r * kw['crescent']), int(c[1] - r * 0.2)), int(r * 0.92), 0.0, -1, cv2.LINE_AA)
    elif kind == 'blade':
        ang = math.radians(kw.get('angle', -20)); L_ = kw.get('length', 1600); w = kw.get('width', 120)
        c = np.array(kw.get('c', (W / 2, H / 2))); d = np.array([math.cos(ang), math.sin(ang)]); n = np.array([-d[1], d[0]])
        tip = c + d * L_ / 2; hilt = c - d * L_ / 2
        poly = np.array([hilt + n * w * 0.5, tip - d * w * 1.5 + n * w * 0.45, tip, tip - d * w * 0.4 - n * w * 0.5, hilt - n * w * 0.5])
        cv2.fillPoly(m, [poly.astype(np.int32)], 1.0, cv2.LINE_AA)
        g0 = hilt - d * w * 0.15  # 护手
        cv2.line(m, tuple((g0 + n * w * 1.1).astype(int)), tuple((g0 - n * w * 1.1).astype(int)), 1.0, int(w * 0.35))
        h1 = hilt - d * w * 2.6
        cv2.line(m, tuple(g0.astype(int)), tuple(h1.astype(int)), 1.0, int(w * 0.45))
    elif kind == 'circle_ring':
        c = kw.get('c', (W / 2, H / 2)); r = kw.get('r', 340)
        cv2.circle(m, (int(c[0]), int(c[1])), int(r), 1.0, int(kw.get('width', 70)), cv2.LINE_AA)
    elif kind == 'scale':   # 天平
        cx, cy = W / 2, H / 2 - 160
        cv2.line(m, (int(cx), int(cy - 60)), (int(cx), int(cy + 420)), 1.0, 34)
        cv2.line(m, (int(cx - 520), int(cy + 20)), (int(cx + 520), int(cy - 20)), 1.0, 26)
        for sx, sy in ((cx - 500, cy + 20), (cx + 500, cy - 20)):
            cv2.ellipse(m, (int(sx), int(sy + 250)), (190, 70), 0, 0, 180, 1.0, -1)
            cv2.line(m, (int(sx), int(sy)), (int(sx - 170), int(sy + 250)), 1.0, 8)
            cv2.line(m, (int(sx), int(sy)), (int(sx + 170), int(sy + 250)), 1.0, 8)
        cv2.rectangle(m, (int(cx - 200), int(cy + 400)), (int(cx + 200), int(cy + 450)), 1.0, -1)
    return m


def char_shape(fr, t, mask, text=None, p=1.0, cell=18, color='gold', fname='song', seed=0, bg_dim=0.55,
               sweep=None, flicker=True, outline_chars=True):
    """字组成图形：用歌词小字（text 循环）铺满 mask（刀/月/天平/巨字），p 控制组成进度。
    sweep=None 随机顺序点亮；'down'/'right'/'center' 按方向扫出。蒙版边缘一圈字更亮（outline_chars）。"""
    pool = (text or all_lyrics()).replace(' ', '')
    At, chars = _atlas(pool, cell, fname)
    nC = W // cell; nR = H // cell
    sm = cv2.resize(mask[:nR * cell, :nC * cell].astype(np.float32), (nC, nR), interpolation=cv2.INTER_AREA)
    r = _rng(seed)
    # 按阅读顺序把歌词铺进图形（行内从左到右）
    seq = np.array([chars.index(c) for c in pool], np.int64)
    cnt = np.cumsum((sm > 0.35).ravel()) - 1
    idx = seq[np.clip(cnt, 0, None) % len(seq)].reshape(nR, nC)
    if flicker:
        jit = (r.random((nR, nC)) < 0.04) & (np.floor(t * 12 + r.random((nR, nC)) * 9) % 5 == 0)
        idx = np.where(jit, (idx + 13) % len(chars), idx)
    img = _tile(At, idx)
    if sweep is None: order = r.random((nR, nC))
    elif sweep == 'down': order = np.repeat(np.linspace(0, 1, nR)[:, None], nC, 1) + r.random((nR, nC)) * 0.08
    elif sweep == 'right': order = np.repeat(np.linspace(0, 1, nC)[None, :], nR, 0) + r.random((nR, nC)) * 0.08
    else:
        yy, xx = np.mgrid[0:nR, 0:nC]; order = np.sqrt(((xx - nC / 2) / nC) ** 2 + ((yy - nR / 2) / nR) ** 2) * 1.4 + r.random((nR, nC)) * 0.06
    lit = (sm > 0.35) * np.clip((p * 1.3 - order) / 0.3, 0, 1)
    I = lit.astype(np.float32)
    if outline_chars:
        e = cv2.morphologyEx((sm > 0.35).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(np.float32)
        I = I * (0.75 + 0.6 * e)
    out = fr * (1 - bg_dim)
    If = cv2.resize(I, (nC * cell, nR * cell), interpolation=cv2.INTER_NEAREST)
    a = img * np.clip(If, 0, 1.4)
    reg = out[:nR * cell, :nC * cell]
    reg[:] = reg * (1 - np.clip(a, 0, 1)[..., None]) + a[..., None] * col(color)
    gl = cv2.GaussianBlur(cv2.resize(a, (nC * cell // 4, nR * cell // 4), interpolation=cv2.INTER_AREA), (0, 0), 4)
    reg += cv2.resize(gl, (nC * cell, nR * cell))[..., None] * col(color) * 0.7
    out[:BAR] = fr[:BAR] * (1 - bg_dim); out[H - BAR:] = fr[H - BAR:] * (1 - bg_dim)
    return out


# ------------------------------------------------------------------ 14. 炸开重组（粒子）
_pt_cache = {}
def _points(key, P, n, seed):
    if key in _pt_cache: return _pt_cache[key]
    L = Layer()
    for p_ in P: place(L, p_['ch'], p_['x'], p_['y'], p_['size'], 'white', p_['font'], texture=False)
    ys, xs = np.nonzero(L.A > 0.5)
    r = _rng(seed)
    k = r.integers(0, len(ys), n)
    pts = np.stack([xs[k], ys[k]], 1).astype(np.float32) + r.uniform(-0.5, 0.5, (n, 2)).astype(np.float32)
    pts = pts[np.argsort(pts[:, 0] + r.uniform(0, 30, n))]     # 按 x 排序 → 重组时左右对应流动
    if len(_pt_cache) > 40: _pt_cache.clear()
    _pt_cache[key] = (pts, L)
    return pts, L


def explode_reform(fr, textA, textB, p, placesA=None, placesB=None, style='h', size=None, fname='kai',
                   color='gold', colorB=None, n=14000, seed=0, burst=None, power=1.0, swirl=1.0, box=None,
                   anchor=(0.5, 0.5), style_kw=None, hold=0.12):
    """字随鼓点炸开重组：textA 的笔画化为粒子炸散（0→0.4），在空中打旋，再汇聚成 textB（0.4→1）。
    p<hold 显示完整 A，p>1-hold 渐现完整 B；把 p 接到鼓点（如 p = 两拍内进度）即“随拍炸开重组”。
    textB 可等于 textA（原地炸开再复原）。"""
    PA = placesA or layout(textA, style, size=size, fname=fname, box=box, anchor=anchor)
    PB = placesB or layout(textB, style, size=size, fname=fname, box=box, anchor=anchor)
    cB = colorB or color
    ptsA, LA = _points((textA, style, fname, size, box, anchor, n, seed, 'A', id(placesA) if placesA else 0), PA, n, seed)
    ptsB, LB = _points((textB, style, fname, size, box, anchor, n, seed + 1, 'B', id(placesB) if placesB else 0), PB, n, seed + 1)
    kwA = auto_style(color); kwA.update(style_kw or {})
    kwB = auto_style(cB); kwB.update(style_kw or {})
    if p <= hold * 0.5:
        LA.C[:] = col(color); return compose(fr, LA, **kwA)
    q = (p - hold * 0.5) / (1 - hold)
    q = float(np.clip(q, 0, 1))
    r = _rng(seed + 7)
    c = np.array(burst if burst is not None else ptsA.mean(0), np.float32)
    v = ptsA - c; dist = np.linalg.norm(v, axis=1, keepdims=True) + 1e-3
    v = v / dist * (110 + r.exponential(150, (n, 1))) * power + r.normal(0, 55, (n, 2)) * power
    e1 = ease_out(min(1, q / 0.45), 3)
    expl = ptsA + v * e1
    # 旋涡
    ang = swirl * (q * 2.5) * (1 + r.random(n)) * 0.6
    rel = expl - c
    ca, sa = np.cos(ang * (1 - q)), np.sin(ang * (1 - q))
    expl = c + np.stack([rel[:, 0] * ca - rel[:, 1] * sa, rel[:, 0] * sa + rel[:, 1] * ca], 1)
    delay = r.uniform(0, 0.18, n)
    w = ease_io(np.clip((q - 0.38 - delay) / 0.45, 0, 1))[:, None]
    pos = expl * (1 - w) + ptsB * w
    # 绘制
    hw, hh = W // 2, H // 2
    xi = (pos[:, 0] / 2).astype(np.int32); yi = (pos[:, 1] / 2).astype(np.int32)
    ok = (xi >= 0) & (xi < hw) & (yi >= 0) & (yi < hh)
    spd = np.linalg.norm(v, axis=1) * (1 - e1 + 0.15) * (1 - w[:, 0])
    acc = np.bincount(yi[ok] * hw + xi[ok], weights=np.ones(ok.sum()), minlength=hw * hh).reshape(hh, hw).astype(np.float32)
    hot = np.bincount(yi[ok] * hw + xi[ok], weights=np.clip(spd[ok] / 400, 0, 1), minlength=hw * hh).reshape(hh, hw).astype(np.float32)
    acc = cv2.GaussianBlur(acc, (0, 0), 0.7) * 1.7
    glow_ = cv2.GaussianBlur(cv2.resize(acc, (hw // 2, hh // 2), interpolation=cv2.INTER_AREA), (0, 0), 3) * 2.0
    out = fr.copy()
    mix = np.clip(q * 1.6 - 0.6, 0, 1)
    pc = col(color) * (1 - mix) + col(cB) * mix
    A = cv2.resize(np.clip(acc, 0, 1.6), (W, H))
    G = cv2.resize(glow_, (W, H))
    Hh = cv2.resize(np.clip(cv2.GaussianBlur(hot, (0, 0), 1), 0, 1), (W, H))
    out *= (1 - 0.35 * np.clip(G, 0, 1))[..., None]
    out += A[..., None] * (pc * 0.9 + Hh[..., None] * np.array([0.3, 0.25, 0.2])) + G[..., None] * pc * 0.6
    # 首尾实体字
    if q < 0.12:
        LA.C[:] = col(color); out = compose(out, LA, **dict(kwA, opacity=1 - q / 0.12))
    if p > 1 - hold:
        LB.C[:] = col(cB); out = compose(out, LB, **dict(kwB, opacity=smooth(1 - hold, 1.0, p)))
    return out


# ------------------------------------------------------------------ 15. 图层工厂（可交给 slash_layer / shatter_layer 二次加工）
def text_layer(text, places=None, style='h', size=None, fname='kai', color='white', emph=(), emph_color='red',
               box=None, anchor=(0.5, 0.5), seed=0, prog=None):
    """整句文字 → Layer（可再交给 slash_layer / shatter_layer / drip_layer / compose）。"""
    P = _P(text, places, style, size, fname, box, anchor, seed, emph)
    return _line_layer(P, _colors(P, color, emph_color), None if prog is None else _per_char(prog, len(P))), P


def giant_layer(ch, fname='xing', color='red', cx=None, cy=None, size=None, scale=1.0, rot=0.0):
    """巨字 Layer（按墨迹包围盒撑满有效区），用于“巨字被斩/被碎”。"""
    cx = W / 2 if cx is None else cx; cy = H / 2 if cy is None else cy
    s = size or (H - 2 * BAR) * 0.98
    if size is None:
        g0 = glyph(ch, fname, s, False); ys_, xs_ = np.nonzero(g0 > 0.3)
        if len(ys_):
            bh, bw = ys_.max() - ys_.min() + 1, xs_.max() - xs_.min() + 1
            k = min(0.92 * (H - 2 * BAR) / bh, 0.9 * W / bw)
            cx -= ((xs_.max() + xs_.min()) / 2 - g0.shape[1] / 2) * k * scale
            cy -= ((ys_.max() + ys_.min()) / 2 - g0.shape[0] / 2) * k * scale
            s *= k
    L = Layer(); place(L, ch, cx, cy, s, color, fname, scale=scale, rot=rot)
    return L


def seal_layer(text, cx, cy, size, style='yin', rot=-4.0, seed=0, color='red', alpha=0.95):
    """印章 Layer（已落定状态），用于“印裂字裂”(slash_layer) / “方印被击碎”(shatter_layer)。"""
    a = _seal_img(text, int(size), style, seed)
    L = Layer(); _paste_rot(L, a, cx, cy, 1.0, rot, color, alpha)
    return L


def drip_layer(L, p, n=6, seed=0, length=None, color=None, region=None):
    """血字下流：从字形底边向下长出细血/墨滴（length×区域高度），p 0→1 增长。原地修改并返回 L。
    region=(x0,y0,x1,y1) 只让该区域（如「血」字：bbox([P[i]])）滴落；默认整个图层。"""
    bx = L.box(0)
    if bx is None or p <= 0: return L
    if region is not None:
        bx = (max(bx[0], int(region[0])), max(bx[1], int(region[1])), min(bx[2], int(region[2])), min(bx[3], int(region[3])))
    X0, Y0, X1, Y1 = bx
    length = length if length is not None else (1.6 if region is not None else 0.35)
    A = L.A[Y0:Y1, X0:X1]
    bottom = (A > 0.5) & (np.roll(A, -1, 0) < 0.2)
    ys, xs = np.nonzero(bottom[:-1])
    if not len(ys): return L
    r = _rng(seed)
    k = r.choice(len(ys), min(n, len(ys)), replace=False)
    hh = Y1 - Y0
    for i in k:
        x, y = xs[i] + X0, ys[i] + Y0
        c_ = L.C[y, x].copy() if color is None else col(color)
        ln = hh * length * r.uniform(0.3, 1.0) * ease_out(min(1, p * r.uniform(0.8, 1.6)), 2)
        w = max(2, int(r.uniform(0.012, 0.03) * hh + 1))
        seg = np.zeros((int(ln) + w * 4 + 2, w * 4 + 2), np.float32)
        cx_ = seg.shape[1] // 2
        cv2.line(seg, (cx_, 0), (cx_, int(ln)), 1.0, w, cv2.LINE_AA)
        cv2.circle(seg, (cx_, int(ln)), int(w * 0.9) + 1, 1.0, -1, cv2.LINE_AA)
        L.paste(seg, x, y + seg.shape[0] / 2 - 1, c_, 1.0)
    return L


def strike(fr, places, idxs, p, color='red', width=0.2, seed=0):
    """一笔斜线划掉指定字（如「天命」「上苍」被划掉）：干笔质感，p 0→1 从起点拖到终点。"""
    if p <= 0: return fr.copy()
    sel = [places[i] for i in idxs]
    x0, y0, x1, y1 = bbox(sel, 0.45)
    vertical = (y1 - y0) > (x1 - x0)
    a = np.array([x0, y0 if not vertical else y0]); b = np.array([x1, y1])
    if not vertical: a = np.array([x0, y1 - (y1 - y0) * 0.25]); b = np.array([x1, y0 + (y1 - y0) * 0.25])
    else: a = np.array([x1 - (x1 - x0) * 0.1, y0]); b = np.array([x0 + (x1 - x0) * 0.1, y1])
    sz = max(q['size'] for q in sel)
    e = ease_out(p, 2)
    L = Layer()
    m = np.zeros((H, W), np.float32)
    pts = [a + (b - a) * u for u in np.linspace(0, e, 24)]
    for k in range(len(pts) - 1):
        u = k / 23
        wv = sz * width * (0.6 + 0.6 * math.sin(math.pi * min(1, u / max(e, 1e-3))))
        cv2.line(m, tuple(pts[k].astype(int)), tuple(pts[k + 1].astype(int)), 1.0, max(2, int(wv)), cv2.LINE_AA)
    tex = _noise(H, W, 3, seed + 3, aniso=(6, 1) if not vertical else (1, 6))
    m = m * np.clip(0.35 + (tex - 0.2) * 2.2, 0, 1)
    L.A = m; L.C[:] = col(color); L.bb = [int(min(a[0], b[0]) - sz), int(min(a[1], b[1]) - sz), int(max(a[0], b[0]) + sz), int(max(a[1], b[1]) + sz)]
    L.bb = [max(0, L.bb[0]), max(0, L.bb[1]), min(W, L.bb[2]), min(H, L.bb[3])]
    return compose(fr, L, **auto_style(color))


# ------------------------------------------------------------------ 16. 印章扩展
def seal_grid(fr, chars, cx, cy, size, prog, colors=None, gap=0.06, style='yin', seed=0, rot=-2.0):
    """2×2 田字格连续落印（「是非对错」：是 非 / 对 错 读序左→右、上→下）。每格一枚单字印，
    prog 标量（四印按序落下）或 4 个进度；colors 每印颜色，例 ['ink','red','ink','red']。"""
    pr = _per_char(prog, 4) if np.isscalar(prog) else list(prog)
    colors = colors or ['red'] * 4
    out = fr
    d = size * (1 + gap) / 2
    pos = [(cx - d, cy - d), (cx + d, cy - d), (cx - d, cy + d), (cx + d, cy + d)]
    for i, (c, (x, y)) in enumerate(zip(chars[:4], pos)):
        if pr[i] > 0:
            out = stamp_seal(out, c, x, y, size, pr[i], style=style, rot=rot + (i - 1.5) * 1.3, seed=seed + i, color=colors[i])
    return out if out is not fr else fr.copy()


def stamp_overprint(fr, text, cx, cy, size, p, n=4, seed=0, style='yin', color='red', spread=0.1):
    """四次叠印：同一方印连盖 n 次，每次位置/角度偏移、印泥越来越淡，层层叠出“理所应当”的压迫感。"""
    r = _rng(seed)
    out = fr
    for i in range(n):
        pi = (p - i / n * 0.85) / 0.4
        if pi <= 0: continue
        dx, dy = r.normal(0, spread * size, 2)
        out = stamp_seal(out, text, cx + dx, cy + dy, size * r.uniform(0.94, 1.06), min(1, pi), style=style,
                         rot=float(r.uniform(-9, 9)), seed=seed + i * 7, color=color, alpha=0.95 - 0.17 * i)
    return out if out is not fr else fr.copy()


def seal_caption(fr, seal_text, caption, cx, cy, size, p, cap_size=60, cap_font='kai', cap_color='white',
                 cap_emph=(), cap_emph_color='gold', style='yang', seed=0, gap=0.18):
    """印面阳文 + 余字横排（S017：印「正义」，下方横排「若…由权势执掌」）。p<0.5 落印，之后余字逐字落笔。"""
    out = stamp_seal(fr, seal_text, cx, cy, size, min(1, p / 0.5), style=style, seed=seed)
    q = (p - 0.42) / 0.58
    if q > 0 and caption:
        y = cy + size * (0.5 + gap) + cap_size * 0.6
        box = (cx - W * 0.45, y - cap_size, cx + W * 0.45, y + cap_size)
        box = (max(SAFE[0], box[0]), max(SAFE[1], box[1]), min(SAFE[2], box[2]), min(SAFE[3], box[3]))
        out = typewriter_brush(out, caption, q, style='h', size=cap_size, fname=cap_font, color=cap_color, box=box,
                               emph=cap_emph, emph_color=cap_emph_color, splash=False)
    return out


# ------------------------------------------------------------------ 17. 字雨落地堆积
def char_rain(fr, t, text, t0=0.0, density=45.0, size_range=(40, 90), speed=(520, 950), pile_max=230,
              ground=None, color='ink', fname='song', emph=(), emph_color='red', seed=0, wind=40.0, bins=40,
              settle_color=(0.55, 0.54, 0.52), max_dur=40.0):
    """宋体字如雨从天而降，落地堆积成雪（Bridge）。t 绝对时间，t0 开始下雨。
    density 字/秒，size_range 字号区间，speed 落速区间(px/s)，pile_max 最大堆积高度，ground 地面 y（默认有效区底）。
    落地后字略倾倒、颜色向 settle_color 过渡。无状态：任意 t 可直接求值。"""
    ground = ground if ground is not None else H - BAR - 6
    vis = [c for c in text if c not in ' \u3000']
    N = int(min(2500, density * max_dur))
    r = _rng(seed)
    ts = t0 + np.arange(N) / density + r.uniform(0, 1 / density, N)
    xs = r.uniform(30, W - 30, N); sz = r.uniform(*size_range, N); v = r.uniform(*speed, N)
    rot0 = r.uniform(-14, 14, N); spin = r.uniform(-22, 22, N); lie = r.uniform(-22, 22, N)
    sway = r.uniform(0, 6.28, N)
    tl = ts + (ground + sz) / v
    order = np.argsort(tl)
    bw = W / bins; pile = np.zeros(bins + 2)
    land_y = np.zeros(N)
    for i in order:
        b = int(xs[i] // bw) + 1
        h_ = max(pile[b], 0.6 * pile[b - 1], 0.6 * pile[b + 1])
        land_y[i] = ground - min(h_, pile_max) - sz[i] * 0.38
        pile[b] = min(pile_max, h_ + sz[i] * 0.5)
    alive = np.nonzero(ts <= t)[0]
    L = Layer()
    sc_ = col(settle_color) if settle_color is not None else None
    for i in alive:
        age = t - ts[i]
        y = -sz[i] + v[i] * age
        x = xs[i] + wind * age + math.sin(age * 2 + sway[i]) * 12
        ch = vis[i % len(vis)]
        c = emph_color if ch in emph else color
        if y >= land_y[i]:
            y = land_y[i]; x = xs[i] + wind * ((land_y[i] + sz[i]) / v[i])
            rot = lie[i]; blur = 0
            if sc_ is not None: c = tuple(col(c) * 0.5 + sc_ * 0.5)
        else:
            rot = rot0[i] + spin[i] * age; blur = 0.6
        if y < BAR - sz[i] or x < -sz[i] or x > W + sz[i]: continue
        place(L, ch, x, y, sz[i], c, fname, rot=rot, blur=blur, texture=False)
    kw = auto_style(color if isinstance(color, str) else 'white'); kw['shadow'] = min(kw.get('shadow', 0), 0.35)
    return compose(fr, L, **kw)


# ------------------------------------------------------------------ 18. 字砖墙
_brick_cache = {}
def _brick(ch, bw, bh, seed, hl=None):
    k = (ch, bw, bh, seed, hl)
    if k in _brick_cache: return _brick_cache[k]
    r = _rng(seed)
    base = 0.30 + 0.06 * r.random()
    tex = _noise(bh, bw, 6, seed) * 0.5 + _noise(bh, bw, 1.6, seed + 1) * 0.5
    face = base * (0.8 + 0.4 * tex)
    yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
    e = np.minimum(np.minimum(xx, yy), np.minimum(bw - 1 - xx, bh - 1 - yy))
    face = face * np.clip(0.55 + e / 6, 0, 1.12) + (xx < 3) * 0.05 + (yy < 3) * 0.06   # 倒角
    rgb = np.stack([face * 0.96, face * 0.97, face * 1.02], -1).astype(np.float32)
    a = np.clip(e / 1.5, 0, 1).astype(np.float32)
    g = glyph(ch, 'song', int(bh * 0.72), texture=False)
    G = g.shape[0]; y0 = (bh - G) // 2; x0 = (bw - G) // 2
    gm = np.zeros((bh, bw), np.float32)
    ys, xs_ = max(0, -y0), max(0, -x0)
    gm[max(0, y0):max(0, y0) + G - ys, max(0, x0):max(0, x0) + G - xs_] = g[ys:ys + bh - max(0, y0), xs_:xs_ + bw - max(0, x0)][:min(G - ys, bh), :min(G - xs_, bw)]
    sh = np.roll(np.roll(gm, 2, 0), 2, 1)
    if hl is None:   # 阴刻：槽暗 + 下右亮边
        rgb = rgb * (1 - 0.65 * gm[..., None]) + np.clip(sh - gm, 0, 1)[..., None] * 0.18
    else:
        c = col(hl)
        rgb = rgb * (1 - gm[..., None]) + c * gm[..., None] * 1.1
    _brick_cache[k] = (rgb, a, gm)
    if len(_brick_cache) > 1500: _brick_cache.clear()
    return _brick_cache[k]


def wall_bricks(text=None, highlight='', hl_color='gold', cols=13, rows=8, brick=(150, 92), mortar=8, center=None,
                hl_row=None, seed=0):
    """墙的砖块清单 [dict(ch,x,y,hl)]（逐行错缝）。highlight 字连续嵌在 hl_row 行中央并高亮。"""
    pool = (text or all_lyrics()).replace(' ', '')
    bw, bh = brick
    cx, cy = center or (W / 2, H / 2)
    tw = cols * (bw + mortar); th = rows * (bh + mortar)
    r = _rng(seed)
    out = []
    hl_row = rows // 2 if hl_row is None else hl_row
    k0 = (cols - len(highlight)) // 2
    for j in range(rows):
        off = (bw + mortar) / 2 if j % 2 else 0
        n = cols + (1 if j % 2 else 0)
        for i in range(n):
            x = cx - tw / 2 + i * (bw + mortar) - off + bw / 2
            y = cy - th / 2 + j * (bh + mortar) + bh / 2
            ch = pool[r.integers(0, len(pool))]; hl = None
            if highlight and j == hl_row and 0 <= i - k0 < len(highlight):
                ch = highlight[i - k0]; hl = hl_color
            out.append(dict(ch=ch, x=x, y=y, hl=hl, i=i, j=j))
    return out


def text_wall(fr, p, mode='build', bricks=None, brick=(150, 92), seed=0, angle=-62.0, crack_at=0.0,
              center=None, focal=1000.0, **kw):
    """字砖墙：每块砖一个宋体阴刻字（高亮字为金/朱），bricks 由 wall_bricks() 生成（可传 highlight）。
    mode:
      'build'    p 0→1 由下而上逐行砌起（砖块弹落）
      'stand'    静止（p 无用）
      'crack'    沿 angle 斜线被一刀斩裂，两半错开（走 slash_layer，带刀光火星）
      'collapse' 斩裂后两半向两侧塌落：砖块按离斩线远近依次脱落、翻滚、坠出画面
      'fly'      字砖朝镜头 3D 透视飞散（z 由 1 → 0.15，近大远小、旋转、远→近排序）"""
    B = bricks or wall_bricks(brick=brick, seed=seed, **kw)
    bw, bh = brick
    cx, cy = center or (W / 2, H / 2)
    L = Layer()
    r = _rng(seed + 3)
    rows = max(b['j'] for b in B) + 1
    th = math.radians(angle); d = np.array([math.cos(th), math.sin(th)]); n = np.array([-d[1], d[0]])
    items = []
    for k, b in enumerate(B):
        rgb, a, _ = _brick(b['ch'], bw, bh, seed * 1000 + k % 97, b['hl'])
        x, y, rot, sc, al = b['x'], b['y'], 0.0, 1.0, 1.0
        if mode == 'build':
            pj = (p * 1.25 - (rows - 1 - b['j']) / rows * 0.9 - r.uniform(0, 0.08)) / 0.25
            if pj <= 0: continue
            e = ease_back(min(1, pj), 1.4)
            y = y - (1 - e) * 260; al = min(1, pj * 3)
        elif mode == 'collapse':
            sd = (x - cx) * n[0] + (y - cy) * n[1]
            delay = 0.05 + (1 - min(1, abs(sd) / 900)) * 0.25 + r.uniform(0, 0.25) + (rows - b['j']) / rows * 0.15
            q = max(0.0, p - delay)
            side = 1 if sd > 0 else -1
            x = x + side * (n[0] * 60 * min(1, p * 4)) + side * 220 * q * r.uniform(0.3, 1)
            y = y + side * n[1] * 60 * min(1, p * 4) + 2600 * q * q
            rot = side * r.uniform(30, 260) * q
        elif mode == 'fly':
            q = max(0.0, p - r.uniform(0, 0.25))
            z = 1 - 0.85 * ease_out(q, 2) * r.uniform(0.7, 1.0)
            vx, vy = (x - cx), (y - cy)
            sc = 1 / z
            x = cx + vx * sc + r.normal(0, 1) * 300 * q; y = cy + vy * sc + r.normal(0, 1) * 200 * q
            rot = r.uniform(-1, 1) * 200 * q
            al = 1 - smooth(0.7, 1.0, q)
            items.append((z, rgb, a, x, y, rot, sc, al)); continue
        items.append((1.0, rgb, a, x, y, rot, sc, al))
    items.sort(key=lambda it: -it[0])
    for z, rgb, a, x, y, rot, sc, al in items:
        if al <= 0: continue
        if sc > 6: continue
        if rot != 0 or sc != 1:
            dd = int(max(bw, bh) * sc * 1.2) + 2
            M = cv2.getRotationMatrix2D((bw / 2, bh / 2), rot, sc); M[:, 2] += [dd / 2 - bw / 2, dd / 2 - bh / 2]
            a2 = cv2.warpAffine(a, M, (dd, dd)); rgb2 = cv2.warpAffine(rgb, M, (dd, dd))
        else: a2, rgb2, dd = a, rgb, None
        hh_, ww_ = a2.shape
        L.paste_rgba(rgb2, a2 * al, int(x - ww_ / 2), int(y - hh_ / 2))
    sty = dict(shadow=0.55, shadow_sigma=24, glow=0.0)
    if mode == 'crack':
        return slash_layer(fr, L, p, (cx, cy), angle, slide=0.3, sz=bh * 3, length=1500, style_kw=sty, seed=seed)
    return compose(fr, L, **sty)


# ------------------------------------------------------------------ 19. 字体切换（宋 → 行书）
def font_morph(fr, text, p, fa='song', fb='xing', places=None, style='h', size=None, color='white', colorB=None,
               box=None, anchor=(0.5, 0.5), emph=(), emph_color='red', seed=0, burst=True, style_kw=None):
    """同一字从字体 fa 形变为 fb（距离场插值，不是简单叠化），中点迸墨点并闪光。p 标量或每字列表。
    用于「反抗」宋体→行书（权力话语 → 鬼屠的手）。colorB：变形完成后的颜色。"""
    P = _P(text, places, style, size, fb, box, anchor, seed, emph)
    pr = _per_char(p, len(P)) if not np.isscalar(p) else [float(p)] * len(P)
    cA = _colors(P, color, emph_color); cB = _colors(P, colorB or color, emph_color)
    L = Layer()
    for p_, pc, ca, cb in zip(P, pr, cA, cB):
        Da, _ = _sdf(p_['ch'], fa, p_['size']); Db, _ = _sdf(p_['ch'], fb, p_['size'])
        e = ease_io(pc)
        D = Da * (1 - e) + Db * e
        jitter = (_noise(D.shape[0], D.shape[1], max(2, p_['size'] / 45), ord(p_['ch'])) - 0.5) * 0.6 * math.sin(math.pi * e)
        A = np.clip((D + jitter) * 2.0 + 0.5, 0, 1)
        c = tuple(col(ca) * (1 - e) + col(cb) * e)
        L.paste(A, p_['x'], p_['y'], c)
        if burst and 0.35 < pc < 0.9:
            q = (pc - 0.35) / 0.55; rr = _rng(seed + ord(p_['ch']))
            for _ in range(16):
                ang = rr.uniform(0, 6.28); dist = p_['size'] * (0.45 + rr.uniform(0, 0.4)) * (0.5 + q)
                rad = p_['size'] * rr.uniform(0.008, 0.03)
                dot = np.zeros((int(rad * 4) + 3,) * 2, np.float32)
                cv2.circle(dot, (dot.shape[0] // 2,) * 2, max(1, int(rad)), 1.0, -1, cv2.LINE_AA)
                L.paste(dot, p_['x'] + math.cos(ang) * dist, p_['y'] + math.sin(ang) * dist, cb, 1 - q)
    out = _finish(fr, L, colorB or color, style_kw)
    fl = max(0.0, 1 - abs(float(np.mean(pr)) - 0.5) / 0.12)
    if fl > 0:
        x0, y0, x1, y1 = bbox(P); out = _radial_flash(out, ((x0 + x1) / 2, (y0 + y1) / 2), 0.35 * fl, radius=(x1 - x0) * 0.4)
    return out


# ------------------------------------------------------------------ 20. 空间排版扩展
def text_on_quad(fr, text, quad, p=1.0, fname='kai', color='white', alpha=1.0, emph=(), emph_color='red',
                 strip_h=200, spacing=0.1, streak=False, style_kw=None):
    """文字贴到任意四边形（TL,TR,BR,BL 屏幕坐标）上并透视变形：天平横梁、地面刀痕、刀面反射等“贴物体”用法。
    p 0→1 左到右逐字出现；alpha=0.4 + streak=True 即“刀面反射字”（带刀纹拉丝）。"""
    vis = [c for c in text if c not in ' \u3000']
    n = len(vis); s = strip_h * 0.86; adv = s * (1 + spacing)
    sw = int(adv * n + s * 0.2); sh = strip_h
    A = np.zeros((sh, sw), np.float32); C = np.zeros((sh, sw, 3), np.float32)
    pr = _per_char(p, n)
    for i, c in enumerate(vis):
        if pr[i] <= 0: continue
        g = glyph(c, fname, s) * min(1, pr[i] * 2)
        G = g.shape[0]; x0 = int(s * 0.1 + adv * (i + 0.5) - G / 2); y0 = int(sh / 2 - G / 2)
        xs, ys = max(0, x0), max(0, y0); xe, ye = min(sw, x0 + G), min(sh, y0 + G)
        sub = g[ys - y0:ye - y0, xs - x0:xe - x0]
        m = sub > A[ys:ye, xs:xe]
        A[ys:ye, xs:xe][m] = sub[m]; C[ys:ye, xs:xe][m] = col(emph_color if c in emph else color)
    if streak:
        A = A * (0.65 + 0.35 * _noise(sh, sw, 2, 5, aniso=(10, 1)))
    src = np.float32([[0, 0], [sw, 0], [sw, sh], [0, sh]])
    M = cv2.getPerspectiveTransform(src, np.float32(quad))
    L = Layer()
    L.A = cv2.warpPerspective(A, M, (W, H)) * alpha
    L.C = cv2.warpPerspective(C, M, (W, H))
    q = np.float32(quad)
    L.bb = [max(0, int(q[:, 0].min())), max(0, int(q[:, 1].min())), min(W, int(q[:, 0].max()) + 1), min(H, int(q[:, 1].max()) + 1)]
    kw = auto_style(color); kw.update(style_kw or {})
    if alpha < 0.8: kw['shadow'] = kw.get('shadow', 0) * alpha
    return compose(fr, L, **kw)


def text_on_ring(fr, text, cx, cy, rx, ry, phase=0.0, size=120, fname='xing', color='white', emph=(),
                 emph_color='red', arc=None, prog=1.0, style_kw=None):
    """字沿 3D 倾斜圆环环绕（刀光圆环/冲击波环）：phase 旋转角（弧度），前半圈大而清晰、后半圈小而虚。
    arc=None 均匀铺满整圈；给弧度则只占一段弧。"""
    vis = [c for c in text if c not in ' \u3000']
    n = len(vis); pr = _per_char(prog, n)
    span = arc if arc is not None else 2 * math.pi
    back, front = Layer(), Layer()
    for i, c in enumerate(vis):
        if pr[i] <= 0: continue
        ang = phase + (i / n if arc is None else (i / max(1, n - 1) - 0.5)) * span
        x = cx + rx * math.cos(ang); y = cy + ry * math.sin(ang)
        depth = math.sin(ang)          # +1 最近（下方）
        s = size * (0.75 + 0.35 * depth)
        tgt = front if depth >= 0 else back
        place(tgt, c, x, y, s, emph_color if c in emph else color, fname, alpha=min(1, pr[i] * 2) * (0.55 + 0.45 * (depth + 1) / 2),
              blur=max(0, -depth) * 3, sy=0.85 + 0.15 * abs(depth))
    kw = auto_style(color); kw.update(style_kw or {})
    out = compose(fr, back, **dict(kw, shadow=kw.get('shadow', 0) * 0.5))
    return out, front, kw


def ring_front(out, front, kw):
    """text_on_ring 返回 (帧, 前半圈图层, 样式)：先在中间画上圆环/刀光，再用 ring_front 合成前半圈，实现字绕物体穿插。"""
    return compose(out, front, **kw)


def kinetic_fly(fr, text, p, size=80, fname='xing', color='white', emph=(), emph_color='red', stagger=0.22,
                z_far=8000.0, focal=1000.0, spread=160.0, seed=0, style_kw=None):
    """逐字从远处飞向镜头并穿过（80px → 600px+ 后出画）：每字错开 stagger，越近越快、动态模糊、穿过时闪白。"""
    vis = [c for c in text if c not in ' \u3000']
    n = len(vis); r = _rng(seed)
    offs = [(r.uniform(-1, 1) * spread, r.uniform(-0.6, 0.6) * spread) for _ in range(n)]
    out = fr
    flash = 0.0
    order = []
    for i, c in enumerate(vis):
        q = (p - i * stagger) / max(0.2, 1 - (n - 1) * stagger)
        if q <= 0: continue
        z = max(1.0, z_far * (1 - min(q, 1.0) ** 1.3))         # 匀速逼近 → 透视下越近越快
        order.append((z, i, c, q))
    order.sort(key=lambda o: -o[0])
    for z, i, c, q in order:
        sz = size * z_far / max(z, 1.0)          # z=z_far 时为 size，越近越大
        if sz > 1700: flash = max(flash, 1 - (sz - 1700) / 1500); continue
        ox, oy = offs[i]
        k = sz / size
        x = W / 2 + ox * k * 0.15; y = H / 2 + oy * k * 0.15
        L = Layer()
        blur = min(10, max(0, (k - 3) * 0.6))
        a = min(1, q * 4) * (1 - smooth(1100, 1700, sz))
        place(L, c, x, y, sz, emph_color if c in emph else color, fname, alpha=a, blur=blur)
        cc = emph_color if c in emph else color
        kw = auto_style(cc); kw.update(style_kw or {})
        out = compose(out, L, **kw)
    if flash > 0: out = out + 0.6 * flash
    return out if out is not fr else fr.copy()


def ease_in(x, k=3):
    x = np.clip(x, 0, 1); return x ** k


def rotate_invert(fr, p, angle=180.0, zoom=0.25, invert=True):
    """整幅（含已合成的字）随进度旋转倒置并反相：0→1 旋转 angle 度（ease_io），中段 0.35–0.65 黑白反相。
    用法：先把字合成到帧上（例如 kinetic_track/typewriter），再整体交给 rotate_invert —— 字随画面一同颠倒，
    「黑」「白」二字因反相自然互换颜色。"""
    e = ease_io(p)
    sc = 1 + zoom * math.sin(math.pi * e)
    M = cv2.getRotationMatrix2D((W / 2, H / 2), angle * e, sc)
    out = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if invert:
        k = smooth(0.35, 0.65, p)
        out = out * (1 - k) + (1 - np.clip(out, 0, 1)) * k
        out = out + 0.22 * max(0, 1 - abs(p - 0.5) / 0.06)
    return out.astype(np.float32)


# ------------------------------------------------------------------ 21. 刀光逐笔刻字
def blade_write(fr, text, p, places=None, style='h', size=None, fname='xing', color='red', box=None,
                anchor=(0.5, 0.5), core=(1.0, 0.96, 0.85), sparks=180, seed=0, lightning=False, style_kw=None):
    """刀光按笔序逐笔“刻”出字（S107「判」刻在天上）：刀尖处白热光点，刚刻过的笔画炽白→冷却为本色，每笔迸火星。
    lightning=True：闪电写字（电白色、随机闪烁、整体亮闪），用于 S088。p 标量或每字列表。"""
    P = _P(text, places, style, size, fname, box, anchor, seed)
    pr = _per_char(p, len(P))
    base = col((1.0, 0.93, 0.78)) if lightning else col(color)   # 闪电刻字：金白
    out = fr.copy()
    Ls = np.zeros((H // 2, W // 2), np.float32)
    L = Layer()
    for p_, pc in zip(P, pr):
        if pc <= 0: continue
        B = _brush_prep(p_['ch'], p_['font'], p_['size'], seed)
        O, a = B['O'], B['a']
        G = a.shape[0]
        rev = np.clip((pc * 1.02 - O) / 0.012 + 0.5, 0, 1) * a
        heat = np.exp(-np.clip(pc - O, 0, 9) / 0.10) * (O <= pc + 0.01) * a
        if lightning:
            fl = 0.6 + 0.4 * _rng(int(pc * 200) + seed).random()
            rev = rev * fl
        rgb = base * (1 - heat[..., None]) + col(core) * heat[..., None]
        x0, y0 = int(p_['x'] - G / 2), int(p_['y'] - G / 2)
        L.paste_rgba(rgb.astype(np.float32), rev.astype(np.float32), x0, y0)
        if pc < 1:   # 刀尖光点
            fy, fx = np.nonzero((np.abs(O - pc) < 0.01) & (a > 0.5))
            if len(fy):
                tx, ty = x0 + fx.mean(), y0 + fy.mean()
                cv2.circle(Ls, (int(tx / 2), int(ty / 2)), max(2, int(p_['size'] / 60)), 3.0, -1, cv2.LINE_AA)
        if sparks:   # 无状态火星：在笔序场上 O≈b_i 处诞生
            key = (p_['ch'], p_['font'], B['size'])
            if 'spk' not in B:
                yy, xx = np.nonzero(a > 0.5)
                ov = O[yy, xx]; idx = np.argsort(ov)
                B['spk'] = (xx[idx].astype(np.float32), yy[idx].astype(np.float32), ov[idx])
            sx, sy, so = B['spk']
            if len(so):
                r = _rng(seed + ord(p_['ch']))
                b = np.sort(r.uniform(0, 1, sparks))
                j = np.clip(np.searchsorted(so, b), 0, len(so) - 1)
                vx = r.normal(0, 1, sparks) * 500; vy = -r.uniform(100, 700, sparks)
                life = r.uniform(0.06, 0.18, sparks)
                age = pc - b
                for k in np.nonzero((age > 0) & (age < life))[0]:
                    tt = age[k] * 2.2
                    px = x0 + sx[j[k]] + vx[k] * tt; py = y0 + sy[j[k]] + vy[k] * tt + 1800 * tt * tt
                    qx, qy = px - vx[k] * 0.02, py - (vy[k] + 3600 * tt) * 0.02
                    cv2.line(Ls, (int(px / 2), int(py / 2)), (int(qx / 2), int(qy / 2)), float(1.6 * (1 - age[k] / life[k])), 1, cv2.LINE_AA)
    kw = auto_style(color); kw.update(style_kw or {})
    kw['glow'] = max(kw.get('glow', 0), 0.6); kw['glow_color'] = tuple(base)
    out = compose(out, L, **kw)
    sp = cv2.GaussianBlur(Ls, (0, 0), 1.0) * 1.6 + cv2.GaussianBlur(Ls, (0, 0), 6) * 2.5
    out += cv2.resize(sp, (W, H))[..., None] * (np.array([0.8, 0.88, 1.0], np.float32) if lightning else np.array([1.0, 0.72, 0.35], np.float32))
    if lightning:
        m = float(np.mean(pr)); out = out + 0.25 * max(0, 1 - abs((m * 7) % 1 - 0.1) / 0.1)
    return out


# ------------------------------------------------------------------ 22. 打字机（光标 + RGB 错位）
def typewriter(fr, text, prog, t=0.0, places=None, style='h', size=None, fname='song', color='white', box=None,
               anchor=(0.5, 0.5), emph=(), emph_color='red', rgb=(), rgb_amt=10, cursor=True, seed=0, style_kw=None):
    """宋体打字机：字到点即“蹦”出（1 帧白闪 + 1.12→1 回弹），文末方块光标（打字时常亮、打完 2Hz 闪烁）。
    rgb：需要 RGB 错位故障的字集合（如 '交易'），按 t 抖动错位并伴随水平切片位移（预副歌二故障段专用）。"""
    P = _P(text, places, style, size, fname, box, anchor, seed, emph)
    pr = _per_char(prog, len(P)); cs = _colors(P, color, emph_color)
    L = Layer(); Lg = Layer()
    last = None
    for p_, pc, c in zip(P, pr, cs):
        if pc <= 0: continue
        last = p_
        e = min(1, pc / 0.35)
        sc = 1.12 - 0.12 * ease_out(e)
        cc = tuple(col(c) * e + np.array([1, 1, 1]) * (1 - e)) if e < 1 else c
        place(Lg if p_['ch'] in rgb else L, p_['ch'], p_['x'], p_['y'], p_['size'], cc, p_['font'], scale=sc, texture=False)
    kw = auto_style(color); kw.update(style_kw or {})
    out = compose(fr, L, **kw)
    if Lg.box(0) is not None:
        r = _rng(int(t * 15) + seed)
        amt = rgb_amt * (0.5 + r.random())
        out = compose(out, Lg, **dict(kw, glow=0))
        bx = Lg.box(int(rgb_amt * 3))
        X0, Y0, X1, Y1 = bx
        A = Lg.A[Y0:Y1, X0:X1]
        sh = int(amt)
        rA = np.roll(A, sh, 1); bA = np.roll(A, -sh, 1)
        reg = out[Y0:Y1, X0:X1]
        reg[..., 0] = np.maximum(reg[..., 0], rA * 0.95); reg[..., 2] = np.maximum(reg[..., 2], bA * 0.95)
        reg[..., 1] *= (1 - 0.6 * np.clip(rA + bA - 2 * A, 0, 1))
        for _ in range(r.integers(1, 4)):    # 水平切片错位
            y = r.integers(0, Y1 - Y0 - 4); hgt = r.integers(3, max(4, (Y1 - Y0) // 6))
            reg[y:y + hgt] = np.roll(reg[y:y + hgt], int(r.normal(0, rgb_amt * 2)), 1)
    if cursor and last is not None:
        done = all(x >= 1 for x in pr)
        on = (not done) or (math.floor(t * 4) % 2 == 0)
        if on:
            s = last['size']
            vert = style == 'v'
            cxx = last['x'] + (0 if vert else s * 0.62); cyy = last['y'] + (s * 0.62 if vert else 0)
            bar = np.ones((int(s * (0.12 if vert else 0.9)), int(s * (0.9 if vert else 0.12))), np.float32)
            Lc = Layer(); Lc.paste(bar, cxx, cyy, emph_color if emph_color else color, 0.95)
            out = compose(out, Lc, shadow=0, glow=0.4, glow_color=col(emph_color))
    return out


# ------------------------------------------------------------------ 23. 署名
_LATIN = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_&.')
def _tokens(s):
    out = []; buf = ''
    for c in s:
        if c in _LATIN: buf += c
        else:
            if buf: out.append(buf); buf = ''
            if c not in ' \u3000': out.append(c)
    if buf: out.append(buf)
    return out


def _latin_vertical(word, size, color):
    f = _font('song', int(size * 0.8))
    w = int(f.getlength(word)) + 8; h = int(size * 1.1)
    im = Image.new('L', (w, h), 0); ImageDraw.Draw(im).text((w / 2, h / 2), word, font=f, fill=255, anchor='mm')
    return np.rot90(np.asarray(im).astype(np.float32) / 255, -1).copy()


def credit_block(fr, role, names, x, y_top, prog, role_size=32, name_size=64, seal_text=None, seal_size=None,
                 color='white', name_font='kai', seal_style='yin', name_gap=1.3, seed=0, anim='bleed'):
    """片头/片尾署名（竖排）：职务思源宋小字在右，人名马善政大字在左（多名各占一列，自右向左），
    名后（最后一列底下）盖小朱印。「·」及拉丁字母自动用思源宋（拉丁词整词顺时针旋转 90° 竖排）。
    prog 0→1：职务淡入 → 人名逐字墨晕显出 → 落印。anim 'bleed' 墨晕 / 'fade' 淡入下落。"""
    if isinstance(names, str): names = [n for n in names.replace('\u3000', ' ').split(' ') if n]
    seq = []                                   # (token, x, y, size, font)
    rx = x + name_size * 0.62 + role_size * 0.5
    y = y_top
    for tk in _tokens(role):
        if len(tk) > 1:
            seq.append((tk, rx, y + len(tk) * role_size * 0.28, role_size, 'latin')); y += len(tk) * role_size * 0.56 + role_size * 0.2
        else:
            seq.append((tk, rx, y + role_size / 2, role_size, 'song')); y += role_size * 1.08
    nr = len(seq)
    last_bottom = y_top; nx = x
    for ni, nm in enumerate(names):
        y = y_top + role_size * 0.9
        for tk in _tokens(nm):
            if len(tk) > 1:
                hh = len(tk) * name_size * 0.5
                seq.append((tk, nx, y + hh / 2, name_size, 'latin')); y += hh + name_size * 0.15
            else:
                seq.append((tk, nx, y + name_size / 2, name_size, 'song' if tk in '·' else name_font)); y += name_size * 1.04
        last_bottom = max(last_bottom, y); lastx = nx
        nx -= name_size * name_gap
    n = len(seq)
    ps = seq_progress(n + (2 if seal_text else 0), prog, overlap=0.4)
    L = Layer()
    for k, (tk, tx, ty, s, f) in enumerate(seq):
        pc = ps[k]
        if pc <= 0: continue
        if f == 'latin':
            a = _latin_vertical(tk, s, color)
            L.paste(a, tx, ty, color, ease_out(pc))
        elif anim == 'bleed' and k >= nr:
            L.paste(ink_bleed_glyph(tk, f, s, pc, seed, bleed=0.5), tx, ty, color)
        else:
            place(L, tk, tx, ty - (1 - ease_out(pc)) * s * 0.3, s, color, f, alpha=ease_out(pc))
    out = compose(fr, L, **auto_style(color))
    if seal_text:
        ss = seal_size or int(name_size * (0.62 if len(seal_text) == 1 else 0.85))
        sp = (prog - (1 - 1.2 / (n + 2))) / (1.2 / (n + 2)) if n else prog
        if sp > 0:
            out = stamp_seal(out, seal_text, lastx, min(H - BAR - ss * 0.6, last_bottom + ss * 0.65), ss, min(1, sp),
                             style=seal_style, seed=seed)
    return out


# ------------------------------------------------------------------ 便捷：按歌词行号
def line_text(i):
    return load_lines()[i]['text']


def line_prog(i, t, dur=0.25):
    """第 i 句在 t 时刻的逐字进度（只含可见字）。"""
    L = load_lines()[i]
    return [x for x, c in zip(timed_progress(L['times'], t, dur), L['text']) if c != ' ']


__all__ = ['W', 'H', 'BAR', 'SAFE', 'FONTS', 'COLORS', 'load_lines', 'beats', 'beat_pulse', 'seq_progress', 'timed_progress',
           'line_text', 'line_prog', 'glyph', 'warm', 'Layer', 'place', 'compose', 'layout', 'fit', 'bbox',
           'brush_write', 'prepare_brush', 'vertical_column', 'scatter_stack', 'giant_char', 'carved_on_blade', 'stamp_seal',
           'stamp_impact', 'slash_cut', 'ink_bleed_in', 'shatter_out', 'shatter_layer', 'kinetic_track', 'burn_in',
           'typewriter_brush', 'text_matrix', 'char_shape', 'glyph_mask', 'shape_mask', 'explode_reform', 'all_lyrics',
           'slash_layer', 'text_layer', 'giant_layer', 'seal_layer', 'drip_layer', 'strike', 'seal_grid', 'stamp_overprint',
           'seal_caption', 'char_rain', 'wall_bricks', 'text_wall', 'font_morph', 'text_on_quad', 'text_on_ring', 'ring_front',
           'kinetic_fly', 'rotate_invert', 'blade_write', 'typewriter', 'credit_block']
