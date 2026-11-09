"""units/e_r8.py — E 组第八棒辅助（只被 sec_e_final_outro 用）。
blade_ecu：E01 竖刀 ECU —— 用生图 E_r6/blade_vert 的真刃身（锻纹/刃口亮线/切先）翻转迎日、横向 2.35×/纵向 1.45× 拉成 1:6 窄长刃，
          冷暖环境反射重新着色（刃口侧映地平线暖光、平地映天空冷云），日光自下而上扫刃；「血」阴刻入刃面（凹槽暗壁 + 受光壁 + 槽底残血），
          扫光过字时字口反光。"""
import math, os, sys
ROOT = '/Users/sannian/Downloads/鬼屠OP_new/out/devsnap/code'
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, cv2
from PIL import Image
import typo as T

W, H = 1920, 1080


def c01(x): return min(1.0, max(0.0, x))


class BladeECU:
    SX, SY = 2.75, 1.45

    def __init__(self, sky):
        a = np.asarray(Image.open(ROOT + '/assets/gen/E_r6/blade_vert_cut.png')).astype(np.float32) / 255
        c = a[22:985, 1236:1330][:, ::-1]                                  # 刃身（到刀镡上沿为止），水平翻转：刃口朝左（朝日）
        h0, w0 = c.shape[:2]
        self.bw, self.bh = int(w0 * self.SX), int(h0 * self.SY)
        c = cv2.resize(c, (self.bw, self.bh), interpolation=cv2.INTER_CUBIC)
        A0 = c[..., 3] > 0.5
        hh, ww = A0.shape
        xs = np.arange(ww, dtype=np.float32)[None, :]
        rows = A0.any(1)
        top = int(np.argmax(rows))
        left = np.where(rows, np.argmax(A0, 1), ww / 2).astype(np.float32)
        right = np.where(rows, ww - 1 - np.argmax(A0[:, ::-1], 1), ww / 2).astype(np.float32)
        from scipy.ndimage import gaussian_filter1d
        left[top:] = gaussian_filter1d(left[top:], 9, mode='nearest')       # 抠图毛边 → 平滑刃线（拉伸后不再锯齿波浪）
        right[top:] = gaussian_filter1d(right[top:], 14, mode='nearest')
        right[top + 40:] = gaussian_filter1d(right[top + 40:], 40, mode='nearest')   # 刀背基本直
        left[top + 150:] = gaussian_filter1d(left[top + 150:], 45, mode='nearest')
        # 标准切先：刀背直线到顶点，刃线以圆弧从刃宽处收到刀背顶点；横手线 = 切先根部
        bw = float(np.median(right[top + 300:top + 600] - left[top + 300:top + 600]))
        K = int(bw * 1.25); self.K = K
        d = np.arange(K, dtype=np.float32)
        right[top:top + K] = right[top + K]
        wd = bw * np.sqrt(np.clip(1 - (1 - d / K) ** 2, 0, 1))
        left[top:top + K] = right[top:top + K] - wd
        self.yokote = top + K
        A = np.clip(xs - left[:, None] + 0.5, 0, 1) * np.clip(right[:, None] - xs + 0.5, 0, 1)
        A[:top] = 0
        A = A * np.clip((np.arange(hh)[:, None] - top + 1) / 2.0, 0, 1)
        self.A = A.astype(np.float32)
        L = cv2.GaussianBlur(c[..., :3].mean(-1), (0, 0), 1.2)
        self.L = L
        lo = cv2.GaussianBlur(L, (0, 0), 9)
        self.det = np.clip(L - lo, -0.15, 0.15)                             # 锻纹/划痕细节（弱化，防读成树皮）
        self.s = np.clip((xs - left[:, None]) / np.maximum(right - left, 1)[:, None], 0, 1)
        self.v = 1 - np.arange(hh, dtype=np.float32)[:, None] / hh * np.ones((1, ww), np.float32)   # 1 = 尖，0 = 刃根
        self.sky = sky
        self.cool = cv2.GaussianBlur(sky, (0, 0), 30)
        self.top = top

    def layer(self, t, u, sheen_y_local):
        s, v, A, det, L = self.s, self.v, self.A, self.det, self.L
        hh, ww = A.shape
        sr = 0.42                                                            # 镐筋
        bev = np.clip((sr - s) / 0.03 + 0.5, 0, 1)                           # 1 = 刃面（刃口侧）
        yy = np.arange(hh, dtype=np.float32)[:, None] * np.ones((1, ww), np.float32)
        # 刃面：映地平线暖光，下段亮、往上渐暗，横向随截面弧度变化
        warm = np.array([1.0, 0.70, 0.40], np.float32)[None, None] * (0.30 + 0.75 * (1 - v) ** 1.2)[..., None]
        warm = warm * (0.75 + 0.55 * np.clip((sr - s) / sr, 0, 1))[..., None]
        # 平地：映天空冷云（取模糊天空倒影，纵向拉伸、横向压缩），高反差
        iy = np.clip((180 + 600 * (1 - v) + 30 * np.sin(yy / 90.0)).astype(np.int32), 0, H - 1)
        ix = np.clip((1700 - 900 * s - 0.1 * yy).astype(np.int32), 0, W - 1)
        m = self.cool[iy, ix].mean(-1)
        m = np.clip(0.16 + (m - 0.18) * 1.6, 0.06, 1.0)
        cool = m[..., None] * np.array([0.55, 0.68, 0.95], np.float32)
        across = np.clip((s - sr) / (1 - sr), 0, 1)
        cool = cool * (0.5 + 0.7 * np.exp(-((across - 0.65) / 0.22) ** 2))[..., None]
        col = warm * bev[..., None] + cool * (1 - bev[..., None])
        # 保留原图的金属结构：锻纹细节 + 原图明暗
        col = col * (0.80 + 0.45 * L)[..., None] + (det * 0.9)[..., None] * np.array([0.9, 0.9, 0.95], np.float32)
        # 刃文：刃口内侧白雾波纹（直刃小乱）
        ham = 0.16 + 0.03 * np.sin(yy / 31.0) + 0.015 * np.sin(yy / 9.0)
        col = col + (np.exp(-((s - ham) / 0.06) ** 2) * 0.16 * (v < 0.93))[..., None] * np.array([1.0, 0.95, 0.88], np.float32)
        ykt = np.exp(-((yy - self.yokote) / 2.4) ** 2) * (s > 0.04) * (s < 0.95)
        col = col + ykt[..., None] * np.array([1.0, 0.86, 0.62], np.float32) * 0.14
        # 刃口连续细亮线、镐筋亮棱、刀背暗棱
        edge = np.exp(-(s / 0.035) ** 2)
        ridge = np.exp(-((s - sr) / 0.02) ** 2)
        spine = np.exp(-((1 - s) / 0.04) ** 2)
        col = col + edge[..., None] * np.array([1.0, 0.90, 0.72], np.float32) * 0.9 + ridge[..., None] * np.array([1.0, 0.86, 0.66], np.float32) * 0.28
        col = col * (1 - 0.5 * spine[..., None])
        # 日光扫刃（自下而上），刃面最强、刃口沿线最亮
        sh = np.exp(-((yy - sheen_y_local) / 70) ** 2)
        col = col + (sh * (0.25 + 0.85 * bev) + sh * edge * 1.6)[..., None] * np.array([1.0, 0.85, 0.60], np.float32)
        return np.clip(col, 0, 4).astype(np.float32), sh

    def engrave(self, col, ch, size, ly, p, sh, sheen_y_local, seed=11, font='kai', xc=0.5):
        """阴刻字：local 坐标（刃宽中心、ly 行）；p 0→1 自下而上「刻出」（刻线头有一道熔红）。返回新 col。"""
        if p <= 0: return col
        g = T.glyph(ch, font, size, False)
        g = cv2.dilate(g, np.ones((5, 5), np.uint8))                          # 刻字加粗（楷体笔画在窄刃上偏细）
        gh, gw = g.shape
        hh, ww = col.shape[:2]
        M = np.zeros((hh, ww), np.float32)
        rr = int(ly); xm = float(np.argmax(self.s[rr] > xc)) if (self.s[rr] > xc).any() else ww / 2
        x0 = int(xm - gw / 2); y0 = int(ly - gh / 2)
        xa, ya = max(0, x0), max(0, y0); xb, yb = min(ww, x0 + gw), min(hh, y0 + gh)
        M[ya:yb, xa:xb] = g[ya - y0:yb - y0, xa - x0:xb - x0]
        M = M * (self.A > 0.9)
        yy = np.arange(hh, dtype=np.float32)[:, None]
        front = (y0 + gh) - p * (gh + 20)                                    # 刻线自下而上
        rev = np.clip((yy - front) / 6, 0, 1)
        Mr = M * rev
        Mb = cv2.GaussianBlur(Mr, (0, 0), 2.2)
        gy, gx = np.gradient(Mb)
        # 光从左下来：凹槽里朝左下的壁（梯度朝右上的那侧）受光，另一侧投暗
        lit = np.clip((gx * -0.7 + gy * 0.7) * 9, -1, 1)                     # >0 受光壁, <0 背光壁（第八棒翻号：光自左下 → 槽内右上壁亮、左下壁暗，读成凹刻而非凸起）
        wall = np.clip(Mb * (1 - Mb) * 4, 0, 1)
        floor = np.clip((Mr - 0.6) / 0.4, 0, 1)
        rng = np.random.default_rng(seed)
        nz = cv2.GaussianBlur(rng.random((hh, ww)).astype(np.float32), (0, 0), 2.0)
        blood = (0.55 + 0.45 * np.clip((nz - 0.40) * 5, 0, 1)) * floor                       # 槽底残血（不满，斑驳）
        out = col * (1 - 0.72 * Mb[..., None])                               # 凹下去：暗
        out = out + (blood * 0.68)[..., None] * (np.array([0.36, 0.03, 0.018], np.float32) * (0.7 + 0.6 * nz)[..., None] - out * 0.85)   # 第八棒：残血压暗压薄，读成槽里的血而非贴纸
        out = out + (np.clip(lit, 0, 1) * wall * (0.95 + 2.2 * sh))[..., None] * np.array([1.0, 0.82, 0.58], np.float32)
        out = out * (1 - (np.clip(-lit, 0, 1) * wall * 0.85))[..., None]
        # 刻线头熔红
        hot = np.exp(-((yy - front) / 5) ** 2) * M * (p < 1)
        out = out + (hot * 1.4)[..., None] * np.array([1.0, 0.35, 0.08], np.float32)
        return out

    def place(self, fr, col, cx_top, y_top, ang_deg, defocus_bottom=True):
        """把 local 层贴到屏幕：刀尖（local (ww/2, top)）对到 (cx_top, y_top)，绕刀尖转 ang_deg（正 = 顺时针 → 刀身向左下倾）。"""
        hh, ww = self.A.shape
        a = math.radians(ang_deg)
        ca, sa = math.cos(a), math.sin(a)
        px, py = ww * 0.5, float(self.top)
        Mx = np.array([[ca, -sa, cx_top - (ca * px - sa * py)], [sa, ca, y_top - (sa * px + ca * py)]], np.float32)
        Cw = cv2.warpAffine(col, Mx, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        Aw = cv2.warpAffine(self.A, Mx, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        return fr * (1 - Aw[..., None]) + Cw * Aw[..., None], Aw, Mx


def wood_tablet(shape, chars=('天', '理'), seed=150):
    """E15 第八棒：把「天理」挂轴换成竖挂木律令牌（同尺寸，替换 R3.Scrolls 条目的 img/a）。
    木纹（沿长向、噪声扭曲年轮）+ 倒角四边 + 顶部铁环挂绳；「天理」阴刻填金（槽壁暗、槽底旧金、受光边）。返回 (img, a)。"""
    import c1kit as K
    LL, WW = shape
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:LL, 0:WW].astype(np.float32)
    n = cv2.resize(K.fbm(max(8, LL // 6), max(8, WW // 6), seed, base=5, octaves=4), (WW, LL))
    warp = xx + 18 * (n - 0.5) + 6 * np.sin(yy / 140.0)
    grain = 0.5 + 0.5 * np.sin(warp / 3.2 + 2.0 * np.sin(warp / 23.0))
    fine = cv2.resize(r.random((LL // 2, max(2, WW // 8))).astype(np.float32), (WW, LL), interpolation=cv2.INTER_CUBIC)
    base = np.array([0.30, 0.17, 0.085], np.float32)
    img = base[None, None] * (0.70 + 0.30 * grain + 0.18 * (n - 0.5) + 0.08 * (fine - 0.5))[..., None]
    # 板身：上端留挂环位置，四边倒角（左上受光、右下背光）
    top = 26
    m = 10.0
    dl, dr = xx, WW - 1 - xx
    dt, db = yy - top, LL - 1 - yy
    A = np.clip(np.minimum(np.minimum(dl, dr), np.minimum(dt, db)) + 0.5, 0, 1).astype(np.float32)
    bev_l = np.clip(1 - dl / m, 0, 1); bev_t = np.clip(1 - dt / m, 0, 1) * (dt >= 0)
    bev_r = np.clip(1 - dr / m, 0, 1); bev_b = np.clip(1 - db / m, 0, 1)
    img = img * (1 + 0.55 * np.maximum(bev_l, bev_t))[..., None] * (1 - 0.6 * np.maximum(bev_r, bev_b))[..., None]
    # 阴刻填金
    s = int(WW * 0.62); y = top + 40 + s * 0.55
    M = np.zeros((LL, WW), np.float32)
    for ch in chars:
        gl = T.glyph(ch, 'serif_black', s, False); g = gl.shape[0]
        x0, y0 = int(WW / 2 - g / 2), int(y - g / 2)
        xs, ys = max(0, x0), max(0, y0); xe, ye = min(WW, x0 + g), min(LL, y0 + g)
        if xe > xs and ye > ys: M[ys:ye, xs:xe] = np.maximum(M[ys:ye, xs:xe], gl[ys - y0:ye - y0, xs - x0:xe - x0])
        y += s * 1.08
    Mb = cv2.GaussianBlur(M, (0, 0), 1.6)
    gy, gx = np.gradient(Mb)
    lit = np.clip((gx * 0.7 + gy * 0.7) * 8, -1, 1)
    wall = np.clip(Mb * (1 - Mb) * 4, 0, 1)
    gold = np.array([0.72, 0.52, 0.22], np.float32) * (0.75 + 0.5 * n[..., None])
    worn = np.clip((cv2.resize(r.random((LL // 6, WW // 6)).astype(np.float32), (WW, LL)) - 0.25) * 3, 0, 1)   # 金漆斑驳
    fill = M * (0.55 + 0.45 * worn)
    img = img * (1 - 0.75 * Mb[..., None]) + fill[..., None] * gold
    img = img + (np.clip(lit, 0, 1) * wall)[..., None] * np.array([0.9, 0.7, 0.4], np.float32) * 0.6
    img = img * (1 - 0.7 * np.clip(-lit, 0, 1) * wall)[..., None]
    # 挂环 + 绳
    cx = WW / 2
    ring = np.exp(-((np.hypot(xx - cx, yy - (top - 2)) - 11) / 2.2) ** 2) * (yy < top + 6)
    rope = np.exp(-((xx - cx) / 2.0) ** 2) * (yy < top - 12)
    img = img * (1 - ring[..., None]) + ring[..., None] * np.array([0.22, 0.20, 0.19], np.float32) * (1 + 0.8 * (yy < top - 6))[..., None]
    img = img * (1 - rope[..., None]) + rope[..., None] * np.array([0.35, 0.06, 0.04], np.float32)
    A = np.maximum(A, np.clip(ring * 1.4, 0, 1)); A = np.maximum(A, np.clip(rope * 1.4, 0, 1))
    return np.clip(img, 0, 2).astype(np.float32), cv2.GaussianBlur(A, (0, 0), 0.7)
