"""units/a_r5.py — A 组第五轮（用户 12 条意见）开关 + 小工具。
所有改动挂在 ON 开关下：环境变量 A_R5_OFF=all 全部回退；A_R5_OFF=walkout,zoom 关指定项。"""
import os

ON = dict(
    credits_off=True,     # 1  开头署名全部去掉（片尾已有）
    walkout=True,         # 2  A08 主角走出城门，城门在身后合上
    slash_keys=True,      # 3  V06 关键帧插帧挥刀（蓄势 → 横斩 → 送出）
    zoom=True,            # 4  V07→V08 撕纸转场 → 推镜穿越
    garble=True,          # 5  罪状右侧文书 → 乱码
    paper_bowl=True,      # 6  V10 秤盘里保留纸人（不换成主角）
    sha_fang=True,        # 7  殺/放 繁体同位 + 同构图 + 字形变换
    draw_cu=True,         # 8  V14 拔刀特写换图
    carve=True,           # 9  V15 全刀入画 + 真刻字
    jade=True,            # 10 V16/V17 玉玺重生成（立体）
    rise=True,            # 11 V20 起势/上挑换图
    fengmang=True,        # 12 V21 锋芒书法字
)
_off = os.environ.get('A_R5_OFF', '')
if _off.strip() == 'all':
    for _k in ON: ON[_k] = False
else:
    for _k in _off.split(','):
        if _k.strip() in ON: ON[_k.strip()] = False


# ------------------------------------------------------------------ 5 乱码文书（天书式拼合假字）
_POOL = '奉旨查办逆犯目无王法擅杀官兵罪证确凿着即拿问律令刑狱囚斩首判词审讯案牍押解赦免诏敕谋叛诛戮讼罚赎黥劓'


def fake_glyph(T, rs, size, fname='kai'):
    """两个真字各取一半拼成一个读不出的假字（左右或上下拼合，偶尔镜像一半），笔画质感与原小楷一致。"""
    import numpy as np
    a = T.glyph(_POOL[rs.randint(len(_POOL))], fname, size)
    b = T.glyph(_POOL[rs.randint(len(_POOL))], fname, size)
    n = a.shape[0]; s = int(n * rs.uniform(0.42, 0.58))
    g = np.zeros_like(a)
    if rs.rand() < 0.6:
        g[:, :s] = a[:, :s]; g[:, s:] = b[:, s:]
    else:
        g[:s] = a[:s]; g[s:] = b[s:]
    if rs.rand() < 0.25: g = g[:, ::-1].copy()
    return g


def garble_doc(T, cols=3, rows=8, x0=1560, dx=92, y0=200, dy=84, size=66, seed=5, color=(0.06, 0.05, 0.05), alpha=0.62, blur=0.9):
    """第五轮 5：右侧诏文 → 乱码（同位置、同字号、同墨色的三列假字）。"""
    import numpy as np, cv2
    rs = np.random.RandomState(seed)
    L = T.Layer()
    for ci in range(cols):
        for ri in range(rows):
            g = fake_glyph(T, rs, size)
            p = int(blur * 3); g = cv2.GaussianBlur(np.pad(g, p), (0, 0), blur)
            L.paste(g, x0 - ci * dx + rs.uniform(-2, 2), y0 + ri * dy + rs.uniform(-3, 3), color, alpha * rs.uniform(0.85, 1.0))
    return L


# ------------------------------------------------------------------ 3 V06 关键帧插帧挥刀
# 五张同一人物的挥刀关键姿态（同一绿幕批次，按原图像素等比 → 屏幕同一比例；脚底中点钉在地面同一点）
_R5A = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'gen', 'R5_A')
SK_HILT = {                      # 护手处（原图归一化坐标，人工标定）
    'slash_k1_windup_v1': (0.268, 0.392), 'slash_k1_windup_v2': (0.318, 0.385),
    'slash_k2_mid_v1': (0.548, 0.268), 'slash_k2_mid_v2': (0.552, 0.220),
    'slash_k3_follow_v1': (0.620, 0.240), 'slash_k3_follow_v2': (0.590, 0.244),
}
_SKG = {}


def sk_path(n): return os.path.normpath(os.path.join(_R5A, n + '_cut.png'))


def sk_geom(n):
    """→ dict(feet=脚底中点, tip=刀尖, hilt, k=cut/raw 像素比, size=(w,h))，均为原图归一化坐标。"""
    if n in _SKG: return _SKG[n]
    import numpy as np
    from PIL import Image
    im = Image.open(sk_path(n)); w, h = im.size
    rw = Image.open(sk_path(n).replace('_cut.png', '_raw.png')).size[0]
    a = np.array(im.getchannel('A')) > 128
    ys, xs = np.nonzero(a)
    y1 = ys.max(); y0 = ys.min(); band = ys > y1 - 0.07 * (y1 - y0)
    feet = ((xs[band].min() + xs[band].max()) / 2 / w, y1 / h)
    hx, hy = SK_HILT[n]
    i = xs.argmin() if 'k1' in n else xs.argmax()     # k1 刀在身后左侧，其余刀尖在右
    tip = (xs[i] / w, ys[i] / h)
    _SKG[n] = dict(feet=feet, tip=tip, hilt=(hx, hy), k=w / rw, size=(w, h))
    return _SKG[n]


def sk_xf(n, at, s_raw):
    """不画图，只给出该关键帧摆在 at（脚底中点）时的 原图归一化点 → 屏幕 映射。"""
    g = sk_geom(n); w, h = g['size']; s = s_raw / g['k']
    return lambda p: (at[0] + (p[0] - g['feet'][0]) * w * s, at[1] + (p[1] - g['feet'][1]) * h * s)


def sk_schedule(t, ts, rc, ts2):
    """时间 → (当前关键帧, 上一关键帧或 None(不画刀弧), 水平动态模糊 px)。
    ts=第一刀命中、rc=回收蓄势、ts2=第二刀命中（斩「寒光」）。每档 1 帧（30fps），用帧号判断避免浮点抖动。"""
    f = lambda x: int(round(x * 30))
    F, a, r, b = f(t), f(ts), f(rc), f(ts2)
    K1, K1b, K2, K2b, K3, K3h = ('slash_k1_windup_v1', 'slash_k1_windup_v2', 'slash_k2_mid_v1', 'slash_k2_mid_v2',
                                 'slash_k3_follow_v2', 'slash_k3_follow_v1')
    if F < a: return K2, K1, 24
    if F == a: return K2b, K1, 20
    if F == a + 1: return K3, K1, 14
    if F < r: return K3h, None, 0
    if F == r: return K2, None, -26                    # 回刀（刀从右收回到身后）
    if F == r + 1: return K1b, None, -18
    if F < b - 3: return K1, None, 0
    if F == b - 3: return K1b, None, 8                 # 起刀
    if F == b - 2: return K2, K1b, 26
    if F == b - 1: return K2b, K1b, 20
    if F == b: return K3, K1b, 12
    return K3h, None, 0


def blade_arc(fr, C, P0, P1, depth=0.16, width=0.22, amt=1.6, col=(0.80, 0.88, 1.0), tail=1.0, hot=(1.0, 0.35, 0.22)):
    """刀尖从 P0 扫到 P1 的刀弧拖影（月牙形）：刀尖轨迹为向身前（屏幕下方）微垂的二次曲线，不越过刀尖；
    月牙向护手 C 一侧加宽，前缘（靠 P1）最厚最亮、尾部收尖渐隐；外缘一线冷白高光，内侧一层极淡的血红余温。"""
    import numpy as np, cv2, math
    H_, W_ = fr.shape[:2]; q = 2
    P0 = np.array(P0, np.float32); P1 = np.array(P1, np.float32); C = np.array(C, np.float32)
    D = float(np.linalg.norm(P1 - P0))
    Q = np.array([(P0[0] + P1[0]) / 2, max(P0[1], P1[1]) + depth * D], np.float32)
    N = 48; K = 6
    L = np.zeros((H_ // q, W_ // q), np.float32); E = np.zeros_like(L)
    pts = []
    for i in range(N + 1):
        s = i / N
        B = (1 - s) ** 2 * P0 + 2 * (1 - s) * s * Q + s * s * P1
        n = C - B; n /= (np.linalg.norm(n) + 1e-6)
        w = width * min(D, 700) * (s ** 0.9) * (1 - 0.35 * max(0.0, (s - 0.9) / 0.1))
        pts.append((B, n, w, (s ** 1.4) * tail + (1 - tail)))
    for i in range(N):
        (B0, n0, w0, k0), (B1, n1, w1, k1) = pts[i], pts[i + 1]
        kk = 0.5 * (k0 + k1)
        for j in range(K):
            f0, f1 = j / K, (j + 1) / K
            poly = np.array([B0 + n0 * w0 * f0, B1 + n1 * w1 * f0, B1 + n1 * w1 * f1, B0 + n0 * w0 * f1]) / q
            cv2.fillPoly(L, [poly.astype(np.int32)], float(kk * (1 - f0) ** 1.6), cv2.LINE_AA)
        cv2.line(E, tuple((B0 / q).astype(int)), tuple((B1 / q).astype(int)), float(kk), 2, cv2.LINE_AA)
    L = cv2.GaussianBlur(L, (0, 0), 1.5) * 0.45
    E = cv2.GaussianBlur(E, (0, 0), 1.0) + cv2.GaussianBlur(E, (0, 0), 6) * 0.5
    up = lambda X: cv2.resize(X, (W_, H_))[..., None]
    col = np.asarray(col, np.float32); hot = np.asarray(hot, np.float32)
    return fr + (up(E) * col + up(L) * (0.6 * col + 0.2 * hot)) * amt


# ------------------------------------------------------------------ 7/12 书法字（cal_* 生图：白底黑墨 → alpha）
_CAL = {}


def cal_alpha(name, size):
    """assets/gen/R5_A/<name>.png（白底墨字）→ alpha 图；按墨迹包围盒裁切后缩放到边长 size 的方框（居中、等比、留 4% 边）。"""
    k = (name, size)
    if k in _CAL: return _CAL[k]
    import numpy as np, cv2
    from PIL import Image
    im = np.asarray(Image.open(os.path.join(_R5A, name + '.png')).convert('L'), np.float32) / 255
    a = np.clip((0.92 - im) / 0.80, 0, 1)
    ys, xs = np.nonzero(a > 0.25)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    a = a[y0:y1, x0:x1]
    s = size * 0.92 / max(a.shape)
    a = cv2.resize(a, (max(1, int(a.shape[1] * s)), max(1, int(a.shape[0] * s))), interpolation=cv2.INTER_AREA)
    out = np.zeros((size, size), np.float32)
    oy, ox = (size - a.shape[0]) // 2, (size - a.shape[1]) // 2
    out[oy:oy + a.shape[0], ox:ox + a.shape[1]] = a
    _CAL[k] = out
    return out


def _sdf(a):
    import numpy as np, cv2
    m = (a > 0.5).astype(np.uint8)
    return (cv2.distanceTransform(m, cv2.DIST_L2, 5) - cv2.distanceTransform(1 - m, cv2.DIST_L2, 5)).astype(np.float32)


_SDF = {}


def cal_morph(na, nb, size, k, ang=-3.0, spread=0.55, seed=0):
    """字形变换 na → nb（同一方框同一位置）：两字的有符号距离场插值，变换沿 ang 方向的刀光自左向右扫过（每像素时序错开）。
    → (alpha, w)：alpha = 当前字形；w ∈[0,1] = 该像素已属于 nb 的程度（调色用）；边缘热线 = 4*w*(1-w)。"""
    import numpy as np, cv2, math
    key = (na, nb, size)
    if key not in _SDF:
        A0, B0 = cal_alpha(na, size), cal_alpha(nb, size)
        rs = np.random.RandomState(seed)
        nz = cv2.resize(rs.rand(size // 24 + 2, size // 24 + 2).astype(np.float32), (size, size), interpolation=cv2.INTER_CUBIC)
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size
        th = math.radians(ang); proj = xx * math.cos(th) + yy * math.sin(th)
        proj = (proj - proj.min()) / (proj.max() - proj.min())
        _SDF[key] = (A0, B0, _sdf(A0), _sdf(B0), np.clip(proj * 0.85 + nz * 0.15, 0, 1))
    A0, B0, sa, sb, order = _SDF[key]
    if k <= 0: return A0, np.zeros_like(A0)
    if k >= 1: return B0, np.ones_like(B0)
    w = np.clip((k * (1 + spread) - order * spread) / (1 - spread + 1e-6), 0, 1)
    w = w * w * (3 - 2 * w)
    d = (1 - w) * sa + w * sb
    sharp = np.clip(d / 1.6 + 0.5, 0, 1)
    soft = (1 - w) * A0 + w * B0                       # 飞白/墨点：两端仍保留原图柔边
    edge = (w <= 0.001) | (w >= 0.999)
    alpha = np.where(edge, soft, np.maximum(sharp * 0.95, soft * 0.6))
    return alpha.astype(np.float32), w.astype(np.float32)


def ink_write(a, p, ang=35.0, seed=0, soft=0.18):
    """书法字逐渐写出（不读错字：先 1/3 时间铺整字淡墨影，再沿 ang 方向笔势走完）。"""
    import numpy as np, cv2, math
    if p >= 1: return a
    if p <= 0: return a * 0
    n = a.shape[0]
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n
    th = math.radians(ang); pr = xx * math.cos(th) + yy * math.sin(th); pr = (pr - pr.min()) / (pr.max() - pr.min())
    m = np.clip((p * (1 + soft) - pr) / soft, 0, 1)
    ghost = min(1.0, p * 3.0) * 0.5
    return np.maximum(a * m, a * ghost)


# ------------------------------------------------------------------ 9 V15 真刻字（第六轮）
# 字形 = 生图颜体楷书「我的主张」（assets/gen/R6_A/cal_wodezhuzhang.png，白底黑墨）→ 每字 alpha；
# 刻痕 = 药研刻 V 形槽：槽内深度 ∝ 到笔画边缘的距离，按左上光源（与碑面体积光同向）算法线明暗 —— 迎光槽壁亮、背光槽壁黑；
# 新凿石面比风化碑面浅（新茬）；槽沿崩口（噪声侵蚀笔画边）+ 沿口碎茬浅点 + 笔画下方石粉；揭开 = 跟刀尖从左往右凿过去。
_R6A = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'gen', 'R6_A')


def _cal_split(name='cal_wodezhuzhang'):
    import numpy as np
    from PIL import Image
    im = np.asarray(Image.open(os.path.join(_R6A, name + '.png')).convert('L'), np.float32) / 255
    a = np.clip((0.75 - im) / 0.5, 0, 1)
    col = (a > 0.3).sum(0)
    segs, s = [], None
    for x in range(len(col)):
        if col[x] > 0 and s is None: s = x
        if col[x] == 0 and s is not None:
            if x - s > 40: segs.append((s, x))
            s = None
    if s is not None: segs.append((s, len(col)))
    out = []
    for (x0, x1) in segs:
        c = a[:, x0:x1]; ys = np.nonzero(c.max(1) > 0.3)[0]
        out.append(c[ys.min():ys.max() + 1])
    return out


class Carve:
    def __init__(self, places, light=(-0.55, -0.70, 0.55), seed=9):
        """places = [(cx, cy, 字高 px)]，与 _cal_split 的字一一对应。"""
        import numpy as np, cv2
        import a_kit as A
        gl = _cal_split()
        L = np.array(light, np.float32); L /= np.linalg.norm(L)
        self.items = []
        rs = np.random.RandomState(seed)
        for i, (g, (cx, cy, hh)) in enumerate(zip(gl, places)):
            s = hh / g.shape[0]
            g = cv2.resize(g, (max(1, int(g.shape[1] * s)), int(hh)), interpolation=cv2.INTER_AREA)
            pad = 24
            g = np.pad(g, pad)
            h_, w_ = g.shape
            nz = cv2.resize(rs.rand(h_ // 6 + 2, w_ // 6 + 2).astype(np.float32), (w_, h_), interpolation=cv2.INTER_CUBIC)
            nz2 = cv2.resize(rs.rand(h_ // 2 + 2, w_ // 2 + 2).astype(np.float32), (w_, h_), interpolation=cv2.INTER_LINEAR)
            m = np.clip((g - 0.5 + (nz - 0.5) * 0.55 + (nz2 - 0.5) * 0.25) * 6 + 0.5, 0, 1)        # 崩口：笔画边被噪声侵蚀/崩出
            m = cv2.GaussianBlur(m, (0, 0), 0.7)
            mb = (m > 0.5).astype(np.uint8)
            dt = cv2.distanceTransform(mb, cv2.DIST_L2, 5).astype(np.float32)
            D = max(4.0, np.percentile(dt[mb > 0], 92))
            depth = np.clip(dt / D, 0, 1) ** 0.85                                        # V 形槽（中脊最深）
            hgt = -depth * D * 0.9
            hgt = cv2.GaussianBlur(hgt, (0, 0), 1.0)
            gx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3) / 8; gy = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3) / 8
            n = np.dstack([-gx, -gy, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
            dif = np.clip((n * L).sum(2), 0, 1)
            # 投影：沿光线反方向偏移的槽沿挡光（迎光一侧槽壁下半段被上沿挡住）
            sh = np.zeros_like(depth)
            for k in range(1, 7):
                M = np.float32([[1, 0, L[0] / abs(L[2]) * k * 1.4], [0, 1, L[1] / abs(L[2]) * k * 1.4]])
                outside = 1 - cv2.warpAffine(m, M, (w_, h_), borderValue=0)
                sh = np.maximum(sh, outside * np.clip(depth * D * 0.9 - k * 1.2, 0, 1))
            tex = cv2.resize(A.tex(300 + i, 256, 30, 3), (w_, h_))
            fresh = np.array([0.40, 0.385, 0.36], np.float32)                               # 新凿石茬（比风化碑面浅、偏暖）
            shade = (0.06 + 1.35 * dif) * (1 - 0.65 * sh) * (1 - 0.35 * depth) * (0.85 + 0.3 * tex)
            col = shade[..., None] * fresh
            ring = np.clip(cv2.GaussianBlur(m, (0, 0), 3.0) * 1.6 - m * 1.6, 0, 1)        # 槽外一圈崩茬
            chip = np.clip((nz2 - 0.62) * 5, 0, 1) * ring
            # 石粉：笔画下沿积一层浅灰粉
            dust = np.clip(cv2.warpAffine(cv2.GaussianBlur(m, (0, 0), 4), np.float32([[1, 0, 0], [0, 1, 7]]), (w_, h_)) - m, 0, 1) * (0.5 + 0.5 * nz)
            x0, y0 = int(cx - w_ / 2), int(cy - h_ / 2)
            self.items.append(dict(m=m, col=col.astype(np.float32), chip=chip, dust=dust, x0=x0, y0=y0, w=w_, h=h_,
                                   gx0=x0 + pad, gx1=x0 + w_ - pad, gy0=y0 + pad, gy1=y0 + h_ - pad,
                                   front=cv2.resize(rs.rand(h_ // 10 + 2, 3).astype(np.float32), (1, h_))[:, 0]))

    def bounds(self, i):
        it = self.items[i]; return it['gx0'], it['gx1'], it['gy0'], it['gy1']

    def draw(self, fr, progs, mask=None):
        """progs = 每字凿刻进度 0..1（左 → 右揭开，前沿锯齿）。mask = 碑面 alpha（字只刻在碑上）。"""
        import numpy as np
        for it, p in zip(self.items, progs):
            if p <= 0: continue
            x0, y0, w_, h_ = it['x0'], it['y0'], it['w'], it['h']
            xx = np.arange(w_, dtype=np.float32)[None, :]
            fx = it['gx0'] - x0 + (it['gx1'] - it['gx0'] + 30) * p + (it['front'][:, None] - 0.5) * 40
            rv = np.clip((fx - xx) / 14.0, 0, 1) if p < 1 else np.ones((h_, w_), np.float32)
            m = it['m'] * rv
            if mask is not None: m = m * mask[y0:y0 + h_, x0:x0 + w_]
            R = fr[y0:y0 + h_, x0:x0 + w_]
            R = R * (1 - 0.35 * it['chip'][..., None] * rv[..., None]) + it['chip'][..., None] * rv[..., None] * np.array([0.10, 0.10, 0.10], np.float32)
            R = R + (it['dust'] * rv)[..., None] * np.array([0.05, 0.05, 0.048], np.float32)
            R = R * (1 - m[..., None]) + it['col'] * m[..., None]
            fr[y0:y0 + h_, x0:x0 + w_] = R
        return fr


def under_shade(fr, Aw, box, amt=0.45, start=0.45, col=None):
    """玉玺等实体：精灵下部背光一侧压暗（包围盒内自 start 起向下渐暗），去掉「贴纸」平亮感。Aw = place() 返回的屏幕 alpha。"""
    import numpy as np
    (x0, y0), (x1, y1) = box
    yy = np.arange(fr.shape[0], dtype=np.float32)[:, None]
    g = np.clip((yy - (y0 + start * (y1 - y0))) / max(1.0, (1 - start) * (y1 - y0)), 0, 1)
    k = (Aw * g * amt)[..., None]
    out = fr * (1 - k)
    if col is not None: out = out + k * np.asarray(col, np.float32) * 0.1
    return out
