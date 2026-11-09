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
