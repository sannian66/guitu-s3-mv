"""units/d_r7.py — [D组] 第七棒新增：白纸段的光影 / 质感层（只供 units/sec_d_bridge.py 使用）。
- paper_relief：纸纹浮雕（纤维噪声的梯度 · 光向），让纸面在斜光下起伏。
- key_light：主光（左上暖光）径向落差 + 背光角压暗。
- light_shaft：斜射体积光束（带缓慢流动的明暗条与浮尘）。
- ink_cast / ink_sheen：墨笔画的投影与受光面湿墨反光（给天平这种「墨线物件」体积）。
- rim_edge：按光向的轮廓光（刀身、人物）。
- mist_mountains：三层墨色远山（远淡近浓、皴擦干笔纹）+ 每层山脚的雾带。
- torn_slit：纸被刀从背面刺穿的裂口：参差撕边 + 纤维白边 + 两片翻起的纸舌（受光/背光）+ 投影 + 洞内暗。
全部无状态（静态场缓存），按 t 计算。"""
import sys, math
ROOT = '/workspace/work/mv'
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, cv2
import d_kit as D
from d_kit import W, H, BAR, INK

_C = {}
WARM = np.array([1.0, 0.95, 0.86], np.float32)
COOL = np.array([0.80, 0.86, 1.0], np.float32)


def _grid():
    if 'g' not in _C:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        _C['g'] = (x, y)
    return _C['g']


def _noise(seed, sc=1.0):
    key = ('n', seed, sc)
    if key not in _C:
        t = D._tile(seed)
        _C[key] = cv2.resize(t[:max(8, int(H / 4 / sc)), :max(8, int(W / 4 / sc))], (W, H), interpolation=cv2.INTER_CUBIC)
    return _C[key]


def noise1d(n, seed, octs=((90, 1.0), (30, 0.45), (9, 0.2))):
    r = np.random.default_rng(seed)
    x = np.arange(n, dtype=np.float32); out = np.zeros(n, np.float32)
    for per, a in octs:
        k = int(n / per) + 3
        v = r.uniform(-1, 1, k).astype(np.float32)
        out += a * np.interp(x / per, np.arange(k), v).astype(np.float32)
    return out


# ------------------------------------------------------------------ 纸面光
def paper_relief(fr, seed=7, ld=(-0.7, -0.7), amt=0.09):
    key = ('rel', seed, ld)
    if key not in _C:
        r = np.random.default_rng(seed)
        fine = r.standard_normal((H // 2, W // 2)).astype(np.float32)
        fine = cv2.GaussianBlur(cv2.resize(fine, (W, H)), (0, 0), 1.3)
        mid = cv2.GaussianBlur(_noise(seed + 1, 0.25), (0, 0), 2)
        fib = cv2.GaussianBlur(cv2.resize(r.standard_normal((H // 6, W // 2)).astype(np.float32), (W, H)), (0, 0), 1.0)  # 横向纤维
        n = 0.5 * fine / (fine.std() + 1e-6) + 1.2 * (mid - mid.mean()) / (mid.std() + 1e-6) + 0.5 * fib / (fib.std() + 1e-6)
        gy, gx = np.gradient(n)
        e = -(gx * ld[0] + gy * ld[1])
        _C[key] = np.clip(e / (3 * e.std() + 1e-6), -1, 1).astype(np.float32)
    return fr * (1 + amt * _C[key])[..., None]


def key_light(fr, src=(260, 60), r=1500, amt=0.16, dark=0.30, tint=WARM):
    x, y = _grid()
    lit = np.exp(-(((x - src[0]) ** 2 + (y - src[1]) ** 2) / (r * r))).astype(np.float32)
    g = (1 - dark) + (dark + amt) * lit
    col = 1 + (tint - 1) * lit[..., None]
    return fr * g[..., None] * col


def light_shaft(fr, t, origin=(240, 40), angle=34, width=170, amt=0.16, col=(1.0, 0.93, 0.78), seed=3, motes=50, length=1500):
    x, y = _grid()
    th = math.radians(angle)
    d = (math.cos(th), math.sin(th))
    a = (x - origin[0]) * d[0] + (y - origin[1]) * d[1]
    s = -(x - origin[0]) * d[1] + (y - origin[1]) * d[0]
    wa = width * (0.6 + 0.6 * np.clip(a / length, 0, 1))
    band = np.exp(-(s / wa) ** 2) * np.clip(a / 120, 0, 1) * np.clip(1 - a / length, 0, 1) ** 1.2
    stripes = 0.75 + 0.25 * np.sin(s / 23 + 0.7 * np.sin(s / 61) - t * 1.3)
    m = (band * stripes).astype(np.float32)
    out = fr + (1.0 - fr * 0.6) * m[..., None] * amt * np.array(col, np.float32)
    if motes:
        r = np.random.default_rng(seed)
        L = np.zeros((H, W), np.float32)
        for i in range(motes):
            aa = r.uniform(150, length * 0.9); ss = r.normal(0, width * 0.55)
            aa += 25 * math.sin(t * r.uniform(0.6, 1.4) + i); ss += t * r.uniform(-12, 12) + 18 * math.sin(t * 0.9 + i * 1.7)
            px = origin[0] + aa * d[0] - ss * d[1]; py = origin[1] + aa * d[1] + ss * d[0]
            if 0 <= px < W and 0 <= py < H:
                cv2.circle(L, (int(px), int(py)), int(r.uniform(1, 3.2)), r.uniform(0.4, 1.0), -1, cv2.LINE_AA)
        L = cv2.GaussianBlur(L, (0, 0), 1.2)
        out = out + L[..., None] * 0.35 * np.array(col, np.float32)
    return out


# ------------------------------------------------------------------ 墨线物件的体积
def ink_cast(fr, M, ld=(-0.7, -0.6), dist=34, blur=7, amt=0.32):
    """墨笔物件落在纸上的投影（近处实、远处虚：两层模糊叠）"""
    dx, dy = int(-ld[0] * dist), int(-ld[1] * dist)
    s1 = np.roll(np.roll(M, dx // 2, 1), dy // 2, 0)
    s2 = np.roll(np.roll(M, dx, 1), dy, 0)
    sh = 0.55 * cv2.GaussianBlur(s1, (0, 0), blur * 0.5) + 0.45 * cv2.GaussianBlur(s2, (0, 0), blur * 2)
    return fr * (1 - np.clip(sh, 0, 1)[..., None] * amt * np.array([1.0, 1.0, 0.94], np.float32))


def ink_sheen(fr, M, ld=(-0.7, -0.6), w=4, amt=0.38, col=(0.95, 0.9, 0.8), core=0.25):
    """湿墨受光：朝光一侧一线反光 + 墨芯更深、边缘透淡（浓淡）"""
    dx, dy = int(round(ld[0] * w)), int(round(ld[1] * w))
    sh = np.clip(M - np.roll(np.roll(M, -dx, 1), -dy, 0), 0, 1)
    sh = cv2.GaussianBlur(sh, (0, 0), 1.0) * M
    er = cv2.GaussianBlur(cv2.erode(M, np.ones((5, 5), np.uint8)), (0, 0), 2.0)
    edge_thin = np.clip(M - er, 0, 1)
    out = fr * (1 + edge_thin[..., None] * 0.9)                       # 边缘洇淡（墨透纸）
    out = out * (1 - er[..., None] * core)                            # 墨芯更浓
    out = out + sh[..., None] * amt * np.array(col, np.float32)
    return out


def rim_edge(fr, A, ld=(-0.75, -0.65), w=5, amt=0.9, col=(1.0, 0.95, 0.85), glow=6.0, gamt=0.25):
    """轮廓光：A 朝光一侧的边缘一线亮 + 外发光"""
    dx, dy = int(round(ld[0] * w)), int(round(ld[1] * w))
    e = np.clip(A - np.roll(np.roll(A, -dx, 1), -dy, 0), 0, 1)
    e = cv2.GaussianBlur(e, (0, 0), 0.8)
    g = cv2.GaussianBlur(e, (0, 0), glow) * (1 - A)
    c = np.array(col, np.float32)
    return fr + (e * amt + g * gamt)[..., None] * c


# ------------------------------------------------------------------ 三层墨山 + 雾
def mist_mountains(fr, seed=12, y0=560, amp=180, paper_col=None, dens=(0.16, 0.30, 0.52), drift=0.0):
    """远淡近浓三层山（干笔皴纹），每层山脚起一带白雾把下一层的山脊托出来。"""
    key = ('mm', seed, y0, amp, dens)
    if key not in _C:
        layers = []
        x = np.arange(W + 200, dtype=np.float32)
        yy = np.arange(H, dtype=np.float32)[:, None]
        for k in range(3):
            base = y0 + k * 85
            rid = base - amp * (1.0 - 0.22 * k) * (0.55 + 0.45 * noise1d(W + 200, seed * 10 + k, ((420 - 90 * k, 1.0), (130, 0.5), (40, 0.18), (12, 0.06))))
            rid = rid[None, :]
            depth = yy - rid
            A = np.clip(depth / 3, 0, 1)
            # 皴擦：沿坡向的竖向干笔纹 + 山脊处浓、往下渐淡（被雾吃掉）
            r = np.random.default_rng(seed + 40 + k)
            st = cv2.resize(r.random((H // 3, (W + 200) // 14)).astype(np.float32), (W + 200, H))
            st = cv2.GaussianBlur(st, (0, 0), 1.2)
            ridge_dark = 0.55 + 0.45 * np.exp(-np.clip(depth, 0, None) / (40 + 25 * k))
            tex = (0.7 + 0.6 * (st - 0.5)) * ridge_dark
            fall = np.clip(1 - depth / (230 + 70 * k), 0, 1) ** 1.3            # 山脚没入雾
            A = (A * tex * fall).astype(np.float32)
            A = cv2.GaussianBlur(A, (0, 0), 3.0 - k)
            # 雾带：本层山脚往上
            mist = np.exp(-((yy - (base + 120 + 30 * k)) / (70 + 20 * k)) ** 2).astype(np.float32) * np.ones((1, W + 200), np.float32)
            mist *= (0.75 + 0.5 * cv2.resize(D._tile(seed + 70 + k)[:H // 8, :(W + 200) // 8], (W + 200, H)))
            layers.append((A, mist))
        _C[key] = layers
    pc = np.array(paper_col if paper_col is not None else (0.93, 0.915, 0.88), np.float32)
    out = fr
    for k, (A, mist) in enumerate(_C[key]):
        ox = int(100 + drift * (0.3 + 0.5 * k))
        a = A[:, ox:ox + W]; m = mist[:, ox:ox + W]
        col = INK * (1.0 - 0.3 * (2 - k)) + np.array([0.06, 0.07, 0.09], np.float32) * (2 - k)    # 远山偏冷灰
        out = out * (1 - a[..., None] * dens[k]) + col * a[..., None] * dens[k] * 0.4
        out = out * (1 - m[..., None] * 0.55) + pc * m[..., None] * 0.55
    return out


# ------------------------------------------------------------------ 纸被刺穿的裂口
def torn_slit(fr, cx, y_top, y_bot, w_bot, seed=0, ld=(-0.7, -0.7), open_=1.0, flap=1.0, hole_col=(0.035, 0.03, 0.03)):
    """返回 (fr, over)：over = 应画在刀之上的纸舌前缘（刀从纸下穿出，纸舌边缘压住刀根）。"""
    x, y = _grid()
    if y_bot <= y_top + 4: return fr, None
    v = np.clip((y - y_top) / (y_bot - y_top), 0, 1)
    wv = w_bot * open_ * v ** 0.75
    jl = noise1d(H, seed * 7 + 1, ((60, 9), (17, 5), (5, 2.2)))[:, None]
    jr = noise1d(H, seed * 7 + 2, ((60, 9), (17, 5), (5, 2.2)))[:, None]
    inside = (y > y_top)
    dl = (cx - wv + jl * v ** 0.4) - x                 # >0：在左撕边的左侧
    dr = x - (cx + wv + jr * v ** 0.4)                 # >0：在右撕边的右侧
    hole = np.clip(np.minimum(-dl, -dr) / 1.5, 0, 1) * inside
    fw = (26 + 0.55 * wv) * flap
    fl = np.clip(dl / 1.2, 0, 1) * np.clip((fw - dl) / 2.0, 0, 1) * inside * (v > 0.02)
    frt = np.clip(dr / 1.2, 0, 1) * np.clip((fw - dr) / 2.0, 0, 1) * inside * (v > 0.02)
    fl = fl.astype(np.float32); frt = frt.astype(np.float32); hole = hole.astype(np.float32)
    out = fr.copy()
    # 纸舌投影（翻起的纸挡光，落在外侧纸面与洞里）
    flaps = np.maximum(fl, frt)
    sh = cv2.GaussianBlur(np.roll(np.roll(flaps, 16, 1), 12, 0), (0, 0), 9)
    out = out * (1 - sh[..., None] * 0.38)
    # 洞：纸下的黑，越靠撕边越被纸舌遮暗
    hc = np.array(hole_col, np.float32)
    out = out * (1 - hole[..., None]) + hc * hole[..., None]
    # 纸舌：左片背光（法线朝右上）、右片迎光；从折线到撕边有卷曲明暗
    base = fr
    ul = np.clip(dl / np.maximum(fw, 1), 0, 1)        # 0 = 撕边, 1 = 折线
    ur = np.clip(dr / np.maximum(fw, 1), 0, 1)
    shade_l = (0.66 + 0.18 * ul)[..., None] * np.array([0.98, 0.98, 1.0], np.float32)
    shade_r = (1.10 - 0.12 * ur)[..., None] * np.array([1.0, 0.985, 0.95], np.float32)
    out = out * (1 - fl[..., None]) + base * shade_l * fl[..., None]
    out = out * (1 - frt[..., None]) + np.minimum(base * shade_r, 1.0) * frt[..., None]
    # 折线：一道细压痕
    crease = (np.exp(-((dl - fw) / 1.6) ** 2) + np.exp(-((dr - fw) / 1.6) ** 2)) * inside * (v > 0.02)
    out = out * (1 - crease[..., None] * 0.22)
    # 撕边纤维：撕口一线纸芯白 + 细毛
    r = np.random.default_rng(seed + 5)
    hair = cv2.resize(r.random((H // 2, W // 2)).astype(np.float32), (W, H))
    edge = (np.exp(-(dl / 2.2) ** 2) + np.exp(-(dr / 2.2) ** 2)) * inside * (v > 0.01)
    fuzz = (np.exp(-(np.maximum(-dl, 0) / 5) ** 2) * (dl < 0) + np.exp(-(np.maximum(-dr, 0) / 5) ** 2) * (dr < 0)) * inside
    fuzz = fuzz * np.clip((hair - 0.62) * 4, 0, 1)
    ed = np.clip(edge * 0.9 + fuzz * 0.6, 0, 1).astype(np.float32)
    out = out * (1 - ed[..., None]) + np.array([0.99, 0.98, 0.95], np.float32) * ed[..., None]
    over = np.clip((edge + flaps * np.exp(-(np.minimum(np.abs(dl), np.abs(dr)) / 10) ** 2)) * (v > 0.55), 0, 1).astype(np.float32)
    return out, over
