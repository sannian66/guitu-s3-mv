"""units/c_props.py — C 组道具（第二棒新写，替换 props.py 里偏矢量的版本，只被 sec_c_pre2_chorus2 使用）。
- Cuboid：透视长方体，每面贴材质纹理（warpPerspective），朗伯 + 环境 + 边缘轮廓光；输出 RGBA 图层（便于斩开/遮挡）。
- StoneSeal：墨玉巨印（石纹、刻边框、印钮、底面朱砂阳文、侧面金填阴刻铭文），可斩开 + 碎石。
- LacquerBox：黑漆描金暗箱（漆面反光、金包角、金锁片、箱口内暖光）。
- BronzeBalance：青铜天平（圆柱体着色的横梁/立柱/吊链、碗形秤盘、铜绿斑、高光）。
材质全部 numpy 程序生成；不改共享库。"""
import math, sys
ROOT = '/Users/sannian/Downloads/鬼屠OP_new/out/devsnap_secb/code'
for p in (ROOT, ROOT + '/lib', ROOT + '/units'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
import fx2

W, H = 1920, 1080
FONT_B = ROOT + '/fonts/NotoSerifSC-Black.otf'
_NZ = {}


def nz(n, seed, base=6, octaves=5):
    k = (n, seed, base, octaves)
    if k not in _NZ: _NZ[k] = fx2.noise(n, seed, base=base, octaves=octaves).astype(np.float32)
    return _NZ[k]


def text_mask(txt, size, w, h, font=FONT_B, cx=None, cy=None, vertical=False, spacing=1.05):
    """PIL 渲染文字蒙版 (h,w) float32 0..1，居中。"""
    im = Image.new('L', (w, h), 0); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(font, int(size))
    cx = w / 2 if cx is None else cx; cy = h / 2 if cy is None else cy
    if vertical:
        n = len(txt); tot = size * spacing * n
        for i, c in enumerate(txt):
            d.text((cx, cy - tot / 2 + size * spacing * (i + 0.5)), c, fill=255, font=f, anchor='mm')
    else:
        d.text((cx, cy), txt, fill=255, font=f, anchor='mm')
    return np.asarray(im, np.float32) / 255


def emboss(mask, depth=3.0, light=(-1, -1)):
    """蒙版 → 浮雕明暗（-1..1）"""
    m = cv2.GaussianBlur(mask, (0, 0), depth * 0.6)
    gx = cv2.Sobel(m, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(m, cv2.CV_32F, 0, 1, ksize=3)
    l = np.array(light, np.float32); l /= np.linalg.norm(l)
    return np.clip(-(gx * l[0] + gy * l[1]) * depth, -1, 1)


# =============================================================== 材质纹理
def stone_tex(w, h, seed, base=(0.11, 0.125, 0.12), vein=(0.30, 0.33, 0.30), border=True, engrave=None, engrave_gold=True):
    r = np.random.default_rng(seed)
    n1 = cv2.resize(nz(256, seed, 4, 6), (w, h)); n2 = cv2.resize(nz(256, seed + 1, 12, 4), (w, h))
    col = np.array(base, np.float32) * (0.65 + 0.7 * n1[..., None]) * (0.9 + 0.2 * n2[..., None])
    # 石筋：fbm 的等值线
    v = np.abs(np.sin(n1 * 26 + n2 * 9))
    vm = np.clip(1 - v / 0.06, 0, 1) * (n2 > 0.45)
    col = col * (1 - vm[..., None] * 0.6) + vm[..., None] * np.array(vein, np.float32) * 0.6
    # 磨损小坑
    pits = (cv2.resize(r.random((h // 3 + 1, w // 3 + 1)).astype(np.float32), (w, h)) > 0.985).astype(np.float32)
    col *= (1 - 0.5 * cv2.GaussianBlur(pits, (0, 0), 1.2)[..., None])
    sh = np.zeros((h, w), np.float32)
    if border:
        m = np.zeros((h, w), np.float32); b = int(min(w, h) * 0.07)
        cv2.rectangle(m, (b, b), (w - b, h - b), 1.0, max(2, int(min(w, h) * 0.012)))
        sh += -emboss(m, 2.5) * 0.9
    if engrave is not None:
        txt, sz, vert = engrave
        m = text_mask(txt, sz, w, h, vertical=vert)
        e = emboss(m, 2.0)
        sh += e * 0.8
        if engrave_gold:
            g = cv2.erode(m, np.ones((3, 3), np.uint8))
            col = col * (1 - g[..., None] * 0.9) + g[..., None] * np.array([0.78, 0.56, 0.24], np.float32) * (0.7 + 0.5 * n2[..., None])
    col = col * (1 + 0.6 * sh[..., None])
    return np.clip(col, 0, 2).astype(np.float32)


def cinnabar_face(txt, w, h, seed, mirror=False):
    """印底：朱砂阳文（字和边框凸起、朱红；地子下凹、残留朱泥、发暗）"""
    n1 = cv2.resize(nz(256, seed + 5, 8, 5), (w, h)); n2 = cv2.resize(nz(256, seed + 6, 24, 3), (w, h))
    m = text_mask(txt, min(w, h) * 0.74, w, h)
    b = int(min(w, h) * 0.05)
    fr_ = np.zeros((h, w), np.float32); cv2.rectangle(fr_, (b, b), (w - b, h - b), 1.0, int(min(w, h) * 0.045))
    m = np.maximum(m, fr_)
    wear = np.clip((n2 - 0.72) * 6, 0, 1)                       # 残损
    m = np.clip(m - wear * 0.9, 0, 1)
    if mirror: m = m[:, ::-1]
    hi = np.array([0.80, 0.10, 0.06], np.float32); lo = np.array([0.20, 0.035, 0.03], np.float32)
    col = lo[None, None] * (0.6 + 0.8 * n1[..., None]) * (1 - m[..., None]) + hi * (0.75 + 0.5 * n1[..., None]) * m[..., None]
    col *= 1 + 0.7 * emboss(m, 3.0)[..., None]
    return np.clip(col, 0, 2).astype(np.float32)


def lacquer_tex(w, h, seed, trim=True, lock=False, open_top=False):
    n1 = cv2.resize(nz(256, seed + 9, 3, 5), (w, h)); n2 = cv2.resize(nz(256, seed + 10, 30, 2), (w, h))
    col = np.array([0.035, 0.022, 0.02], np.float32) * (0.7 + 0.6 * n1[..., None])
    # 漆面细裂（断纹）
    cr = np.clip(1 - np.abs(np.sin(n2 * 40)) / 0.04, 0, 1) * (n1 > 0.55)
    col *= (1 - 0.4 * cr[..., None])
    gold = np.array([0.85, 0.60, 0.26], np.float32)
    if trim:
        m = np.zeros((h, w), np.float32); b = int(min(w, h) * 0.06)
        cv2.rectangle(m, (b, b), (w - b, h - b), 1.0, max(2, int(min(w, h) * 0.014)))
        cv2.rectangle(m, (int(b * 1.8), int(b * 1.8)), (w - int(b * 1.8), h - int(b * 1.8)), 1.0, max(1, int(min(w, h) * 0.005)))
        # 卷草角花
        for (x, y, sx, sy) in ((b, b, 1, 1), (w - b, b, -1, 1), (b, h - b, 1, -1), (w - b, h - b, -1, -1)):
            for k in range(3):
                cv2.ellipse(m, (int(x + sx * b * (1.6 + k * 0.9)), int(y + sy * b * 1.6)), (int(b * 0.5), int(b * 0.5)), 0,
                            0, 270, 1.0, max(1, int(b * 0.08)), cv2.LINE_AA)
        # 包角
        cs = int(min(w, h) * 0.12)
        for (x, y) in ((0, 0), (w - cs, 0), (0, h - cs), (w - cs, h - cs)):
            m[y:y + cs, x:x + cs] = np.maximum(m[y:y + cs, x:x + cs], 0.9)
        col = col * (1 - m[..., None]) + gold * m[..., None] * (0.55 + 0.6 * n1[..., None]) * (1 + 0.5 * emboss(m, 2)[..., None])
    if lock:
        m = np.zeros((h, w), np.float32)
        cv2.ellipse(m, (w // 2, int(h * 0.42)), (int(w * 0.07), int(w * 0.07)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        cv2.rectangle(m, (int(w * 0.47), int(h * 0.42)), (int(w * 0.53), int(h * 0.62)), 1.0, -1)
        col = col * (1 - m[..., None]) + gold * m[..., None] * (0.6 + 0.6 * n1[..., None]) * (1 + 0.6 * emboss(m, 2)[..., None])
    if open_top:
        b = int(min(w, h) * 0.12)
        hole = np.zeros((h, w), np.float32); cv2.rectangle(hole, (b, b), (w - b, h - b), 1.0, -1)
        hole = cv2.GaussianBlur(hole, (0, 0), 2)
        yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
        inner = np.array([0.30, 0.16, 0.05], np.float32) * (yy ** 2)[..., None] * 0.35       # 箱内深处的暖光
        col = col * (1 - hole[..., None]) + inner * hole[..., None]
    return np.clip(col, 0, 2).astype(np.float32)


# =============================================================== 透视长方体
def _rot(yaw, pitch, roll=0.0):
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Rz @ Rx @ Ry


# 面：名称 → (顶点索引, 法向)；顶点 i = (x±, y 0/1, z±)
_V = np.array([[-.5, 0, -.5], [.5, 0, -.5], [.5, 0, .5], [-.5, 0, .5], [-.5, 1, -.5], [.5, 1, -.5], [.5, 1, .5], [-.5, 1, .5]], float)
_FACES = {  # 纹理角序：左上、右上、右下、左下（从外侧看）
    'front': ([4, 5, 1, 0], (0, 0, -1)), 'back': ([6, 7, 3, 2], (0, 0, 1)),
    'left': ([7, 4, 0, 3], (-1, 0, 0)), 'right': ([5, 6, 2, 1], (1, 0, 0)),
    'top': ([7, 6, 5, 4], (0, 1, 0)), 'bottom': ([0, 1, 2, 3], (0, -1, 0)),
}


class Cuboid:
    def __init__(self, tex):
        """tex: dict 面名 → RGB float 纹理（缺的面用 'side'）"""
        self.tex = tex

    def draw(self, C, A, cx, cy, sx, sy, sz, yaw=20, pitch=0, roll=0, f=1800, light=(-0.5, 0.7, -0.5), amb=0.35, rim=None,
             rim_amt=1.0, flash=0.0, offset=(0, 0, 0), spec=0.25):
        """画到图层 (C 预乘颜色, A)。(cx,cy) = 物体底面中心的屏幕位置。sy>0 高度。pitch>0：仰视（看见底面）。"""
        R = _rot(yaw, pitch, roll)
        P = _V * np.array([sx, sy, sz]) + np.array(offset, float)
        Pc = P @ R.T
        D = f
        Z = Pc[:, 2] + D
        uv = np.stack([cx + f * Pc[:, 0] / Z, cy - f * Pc[:, 1] / Z], 1)
        L = np.array(light, float); L /= np.linalg.norm(L)
        cam = np.array([0, 0, -D], float)
        edges = []
        for name, (idx, n) in _FACES.items():
            nc = R @ np.array(n, float)
            ctr = Pc[idx].mean(0)
            if np.dot(nc, ctr - cam) >= 0: continue
            tx = self.tex.get(name, self.tex.get('side'))
            if tx is None: continue
            th, tw = tx.shape[:2]
            src = np.float32([[0, 0], [tw, 0], [tw, th], [0, th]])
            dst = np.float32(uv[idx])
            M = cv2.getPerspectiveTransform(src, dst)
            x0, y0 = np.floor(dst.min(0)).astype(int) - 2; x1, y1 = np.ceil(dst.max(0)).astype(int) + 2
            x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(W, x1), min(H, y1)
            if x1 <= x0 or y1 <= y0: continue
            T = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]], float) @ M
            wc = cv2.warpPerspective(tx, T, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
            wa = cv2.warpPerspective(np.ones((th, tw), np.float32), T, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
            sh = amb + max(0.0, float(np.dot(nc, L))) * (1 - amb) + flash * 0.8 * max(0.2, float(-nc[2]))
            # 面内渐变（离光远的一端更暗）+ 镜面条
            gy = np.linspace(1.08, 0.86, y1 - y0, dtype=np.float32)[:, None, None]
            wc = wc * sh * gy
            if spec > 0:
                hv = (L + np.array([0, 0, -1])); hv /= np.linalg.norm(hv)
                s = max(0.0, float(np.dot(nc, hv))) ** 12 * spec
                if s > 0.002: wc = wc + s * 0.6 * np.clip(wc.mean(-1, keepdims=True) * 4 + 0.15, 0, 1)
            a = wa[..., None]
            C[y0:y1, x0:x1] = C[y0:y1, x0:x1] * (1 - a) + wc * a
            A[y0:y1, x0:x1] = A[y0:y1, x0:x1] * (1 - wa) + wa
            q = uv[idx]
            for i in range(4): edges.append((q[i], q[(i + 1) % 4], float(max(0.25, nc[1] * 0.6 + 0.6))))
        if rim is not None and edges:
            E = np.zeros((H // 2, W // 2), np.float32)
            for a_, b_, k in edges:
                cv2.line(E, tuple((a_ * 4).astype(int)), tuple((b_ * 4).astype(int)), k, 1, cv2.LINE_AA, 3)
            E = cv2.resize(E + cv2.GaussianBlur(E, (0, 0), 2.5) * 0.8, (W, H))
            C += E[..., None] * np.asarray(rim, np.float32) * rim_amt * (1 + 2 * flash) * A[..., None]
        return uv


def compose(fr, C, A, alpha=1.0, shadow=0.0):
    a = np.clip(A, 0, 1)[..., None] * alpha
    if shadow > 0:
        s = cv2.GaussianBlur(cv2.resize(A, (W // 4, H // 4)), (0, 0), 8)
        fr = fr * (1 - shadow * cv2.resize(s, (W, H))[..., None] * (1 - a))
    return fr * (1 - a) + C * a


def split_layer(C, A, c0, ang, g, s, rot=14.0, fall=0.4):
    """把图层沿过 c0、方向 ang（度）的直线切开，两半沿法向错开并旋转（g 0..1）。返回新的 (C, A) 与切缝亮线。"""
    if g <= 0: return C, A
    a = math.radians(ang); d = np.array([math.cos(a), math.sin(a)]); n = np.array([-d[1], d[0]])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    side = ((xx - c0[0]) * n[0] + (yy - c0[1]) * n[1]) > 0
    C2 = np.zeros_like(C); A2 = np.zeros_like(A)
    for hs in (1, -1):
        m = (side if hs > 0 else ~side).astype(np.float32)
        off = n * hs * g * s * 0.32 + np.array([0, g * g * s * fall])
        M = cv2.getRotationMatrix2D((float(c0[0]), float(c0[1])), float(-hs * g * rot), 1.0); M[:, 2] += off
        Ah = cv2.warpAffine(A * m, M, (W, H)); Ch = cv2.warpAffine(C * m[..., None], M, (W, H))
        C2 = C2 * (1 - Ah[..., None]) + Ch * Ah[..., None] / np.maximum(Ah[..., None], 1e-3) * Ah[..., None]
        A2 = np.maximum(A2, Ah)
    return C2, A2


# =============================================================== 巨印
class StoneSeal:
    def __init__(self, text, seed=0, res=384, front_text=None, base=(0.11, 0.125, 0.12)):
        self.text = text; self.seed = seed
        self.tex = dict(side=stone_tex(res, int(res * 0.9), seed, base=base),
                        front=stone_tex(res, int(res * 0.9), seed + 1, base=base,
                                        engrave=(front_text, res * (0.6 if len(front_text) == 1 else 0.17), len(front_text) > 1)) if front_text else None,
                        top=stone_tex(res, res, seed + 2, base=base, border=False),
                        bottom=cinnabar_face(text, res, res, seed))
        if self.tex['front'] is None: self.tex.pop('front')
        kt = stone_tex(192, 128, seed + 3, base=tuple(np.array(base) * 1.2), border=False)
        self.box = Cuboid(self.tex); self.knob = Cuboid(dict(side=kt, top=kt))
        r = np.random.default_rng(seed)
        self.debris = [(r.uniform(-0.5, 0.5), r.uniform(0, 0.9), r.uniform(0.02, 0.06), r.normal(0, 1, 2), r.uniform(-1, 1)) for _ in range(36)]
        self.chip_tex = stone_tex(48, 48, seed + 4, base=base, border=False)

    def layer(self, cx, cy, size, yaw=18, pitch=8, roll=0, rim=(1.0, 0.76, 0.4), rim_amt=0.8, flash=0.0, light=(-0.5, 0.7, -0.5), f=2200):
        C = np.zeros((H, W, 3), np.float32); A = np.zeros((H, W), np.float32)
        hgt = size * 0.86
        self.box.draw(C, A, cx, cy, size, hgt, size, yaw, pitch, roll, f=f, rim=rim, rim_amt=rim_amt, flash=flash, light=light)
        if pitch < 4:   # 印钮（仰视时被印身挡住）
            self.knob.draw(C, A, cx, cy, size * 0.42, size * 0.30, size * 0.42, yaw, pitch, roll, f=f, rim=rim, rim_amt=rim_amt * 0.8,
                           flash=flash, light=light, offset=(0, hgt, 0))
        return C, A

    def debris_draw(self, C, A, c0, s, g, t_fall=0.0):
        if g <= 0: return
        for i, (dx, dy, sz, v, sp) in enumerate(self.debris):
            p = np.array(c0, float) + np.array([dx * s, -dy * s]) + v * s * 0.8 * g + np.array([0, (g * g) * s * 1.4])
            q = max(3, int(sz * s * (1 - 0.3 * g)))
            if not (0 <= p[0] < W and 0 <= p[1] < H): continue
            ch = cv2.resize(self.chip_tex, (q * 2, q * 2))
            M = cv2.getRotationMatrix2D((q, q), sp * g * 720, 1.0)
            pts = np.array([[0.2, 0], [1, 0.3], [0.8, 1], [0, 0.7]]) * 2 * q
            m = np.zeros((2 * q, 2 * q), np.float32); cv2.fillPoly(m, [pts.astype(np.int32)], 1.0, cv2.LINE_AA)
            m = cv2.warpAffine(m, M, (2 * q, 2 * q)); ch = cv2.warpAffine(ch, M, (2 * q, 2 * q))
            x0, y0 = int(p[0] - q), int(p[1] - q); x1, y1 = x0 + 2 * q, y0 + 2 * q
            xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
            if xb <= xa or yb <= ya: continue
            mm = m[ya - y0:yb - y0, xa - x0:xb - x0] * max(0.0, 1 - g * 0.5)
            C[ya:yb, xa:xb] = C[ya:yb, xa:xb] * (1 - mm[..., None]) + ch[ya - y0:yb - y0, xa - x0:xb - x0] * 1.3 * mm[..., None]
            A[ya:yb, xa:xb] = np.maximum(A[ya:yb, xa:xb], mm)

    def draw(self, fr, cx, cy, size, fall=1.0, split=0.0, split_angle=-62, mblur=True, shadow=0.5, **kw):
        f = float(np.clip(fall, 0, 1))
        by = cy - (1 - f * f) * (cy + size * 1.6)
        C, A = self.layer(cx, by, size, **kw)
        if split > 0:
            c0 = (cx, by - size * 0.43)
            C, A = split_layer(C, A, c0, split_angle, split, size)
            # 切口亮线
            a = math.radians(split_angle); d = np.array([math.cos(a), math.sin(a)]) * size
            E = np.zeros((H // 2, W // 2), np.float32)
            cv2.line(E, tuple(((np.array(c0) - d) * 2).astype(int)), tuple(((np.array(c0) + d) * 2).astype(int)), 1.0, 2, cv2.LINE_AA, 2)
            E = cv2.resize(cv2.GaussianBlur(E, (0, 0), 2), (W, H)) * (1 - split) ** 2
            fr = fr + E[..., None] * np.array([1.0, 0.95, 0.9], np.float32) * 2.0
            self.debris_draw(C, A, c0, size, split)
        if mblur and f < 1:
            k = int((1 - f) * 60) * 2 + 1
            C = cv2.blur(C, (1, k)); A = cv2.blur(A, (1, k))
        return compose(fr, C, A, shadow=shadow), dict(bottom_y=by, impact=f >= 1)


# =============================================================== 暗箱
class LacquerBox:
    def __init__(self, seed=0, res=420):
        self.tex = dict(side=lacquer_tex(res, int(res * 0.62), seed), front=lacquer_tex(res, int(res * 0.62), seed + 1, lock=True),
                        top=lacquer_tex(res, int(res * 0.8), seed + 2, open_top=True), bottom=lacquer_tex(res, res, seed + 3))
        self.box = Cuboid(self.tex)

    def draw(self, fr, cx, cy, size, yaw=0, pitch=-24, f=2000, flash=0.0, rim=(1.0, 0.72, 0.42), rim_amt=0.6, light=(0.3, 0.8, -0.5)):
        C = np.zeros((H, W, 3), np.float32); A = np.zeros((H, W), np.float32)
        uv = self.box.draw(C, A, cx, cy, size, size * 0.5, size * 0.66, yaw, pitch, f=f, rim=rim, rim_amt=rim_amt, flash=flash,
                           light=light, amb=0.5, spec=0.35)
        return compose(fr, C, A, shadow=0.6), uv


# =============================================================== 青铜天平
BRONZE = np.array([0.46, 0.30, 0.14], np.float32)
VERDI = np.array([0.16, 0.26, 0.22], np.float32)


def _cyl(fr, p0, p1, r0, r1, light=(-0.6, -0.8), base=BRONZE, spec=1.0, rim=None, rim_amt=0.0, seed=0, alpha=1.0, band=0.0):
    """圆柱体（端点 p0→p1，半径 r0→r1）圆柱着色 + 铜绿/磨痕纹理，直接画到 fr。band>0：周期性环带（吊链节）。"""
    p0 = np.array(p0, np.float32); p1 = np.array(p1, np.float32)
    rr = max(r0, r1) + 2
    x0, y0 = np.floor(np.minimum(p0, p1) - rr).astype(int); x1, y1 = np.ceil(np.maximum(p0, p1) + rr).astype(int)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0: return fr
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d = p1 - p0; Ln = float(np.hypot(*d)) + 1e-6; u = d / Ln; n = np.array([-u[1], u[0]], np.float32)
    s = ((xx - p0[0]) * u[0] + (yy - p0[1]) * u[1]) / Ln
    q = (xx - p0[0]) * n[0] + (yy - p0[1]) * n[1]
    r = r0 + (r1 - r0) * np.clip(s, 0, 1)
    v = q / np.maximum(r, 0.5)
    inside = np.clip((1 - np.abs(v)) * np.maximum(r, 1) * 0.8, 0, 1) * np.clip(s * Ln + 0.5, 0, 1) * np.clip((1 - s) * Ln + 0.5, 0, 1)
    if inside.max() <= 0: return fr
    vz = np.sqrt(np.clip(1 - v * v, 0, 1))
    lt = np.array(light, np.float32); lt /= np.linalg.norm(lt)
    ldot = (v * (n[0] * lt[0] + n[1] * lt[1])) * 0.8 + vz * 0.45
    diff = np.clip(ldot, 0, 1)
    sp = np.clip(ldot, 0, 1) ** 18 * spec
    tx = cv2.resize(nz(128, seed + 31, 10, 4), (128, 128))
    tu = (s * Ln / 3).astype(np.float32) % 128; tv = ((v + 1) * 20).astype(np.float32) % 128
    tn = cv2.remap(tx, tu, tv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    ver = np.clip((tn - 0.62) * 5, 0, 1)
    col = base * (0.18 + 1.1 * diff[..., None]) * (0.8 + 0.4 * tn[..., None])
    col = col * (1 - ver[..., None] * 0.7) + VERDI * ver[..., None] * (0.4 + 0.8 * diff[..., None])
    col = col + sp[..., None] * np.array([1.0, 0.86, 0.6], np.float32) * (1 - ver[..., None])
    if band > 0:
        bb = 0.5 + 0.5 * np.cos(s * Ln / band * 2 * math.pi)
        col *= (0.45 + 0.75 * bb[..., None])
    if rim is not None and rim_amt > 0:
        e = np.clip((np.abs(v) - 0.72) / 0.28, 0, 1) * (v * (n[0] * lt[0] + n[1] * lt[1]) < 0)
        col = col + e[..., None] * np.asarray(rim, np.float32) * rim_amt
    a = inside[..., None] * alpha
    fr[y0:y1, x0:x1] = fr[y0:y1, x0:x1] * (1 - a) + col * a
    return fr


def _bowl(fr, c, rx, depth, light=(-0.6, -0.8), rim=None, rim_amt=0.6, seed=0, fill=None):
    """碗形秤盘（略俯视）：外壁（下半椭圆，水平圆柱着色）+ 盘口（内面暗、口沿亮）。fill(fr, c, rx, ry)：盘内物体回调。"""
    cx, cy = c; ry = rx * 0.22
    x0, x1 = int(cx - rx - 3), int(cx + rx + 3); y0, y1 = int(cy - ry - 3), int(cy + depth + ry + 3)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0: return fr
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    X = (xx - cx) / rx
    # 外壁：y 在 上椭圆下沿 到 碗底弧 之间
    top_lo = cy + ry * np.sqrt(np.clip(1 - X * X, 0, 1))
    bot = cy + depth * np.sqrt(np.clip(1 - X * X, 0, 1)) ** 0.7 + ry * 0.3
    wall = np.clip((yy - cy) * 1.0, 0, 1) * np.clip(bot - yy, 0, 1) * np.clip((1 - np.abs(X)) * rx, 0, 1)
    lt = np.array(light, np.float32); lt /= np.linalg.norm(lt)
    nx = X; nz_ = np.sqrt(np.clip(1 - X * X, 0, 1))
    diff = np.clip(nx * lt[0] * 0.8 + nz_ * 0.5, 0, 1)
    tn = cv2.resize(nz(128, seed + 41, 8, 4), (x1 - x0, y1 - y0))
    col = BRONZE * (0.15 + 1.1 * diff[..., None]) * (0.75 + 0.5 * tn[..., None])
    col += (np.clip(nx * lt[0] * 0.8 + nz_ * 0.5, 0, 1) ** 16)[..., None] * np.array([1, 0.85, 0.6], np.float32) * 0.8
    vg = np.clip((tn - 0.64) * 5, 0, 1)[..., None]; col = col * (1 - vg * 0.6) + VERDI * vg * 0.5
    a = wall[..., None]
    fr[y0:y1, x0:x1] = fr[y0:y1, x0:x1] * (1 - a) + col * a
    # 盘口：内面
    E = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    inner = np.clip((1 - E) * rx * 0.08, 0, 1)
    ic = BRONZE * 0.18 * (0.7 + 0.6 * tn[..., None]) * (0.6 + 0.8 * np.clip((yy - cy) / ry * 0.5 + 0.5, 0, 1))[..., None]
    fr[y0:y1, x0:x1] = fr[y0:y1, x0:x1] * (1 - inner[..., None]) + ic * inner[..., None]
    lip = np.clip(1 - np.abs(np.sqrt(E) - 1) * rx / 3.5, 0, 1)
    lipc = BRONZE * 1.4 * (0.5 + 0.8 * np.clip(-(yy - cy) / ry * 0.5 + 0.6, 0, 1))[..., None]
    if rim is not None: lipc = lipc + np.asarray(rim, np.float32) * rim_amt * np.clip(-(xx - cx) / rx, 0, 1)[..., None]
    fr[y0:y1, x0:x1] = fr[y0:y1, x0:x1] * (1 - lip[..., None]) + lipc * lip[..., None]
    if fill is not None: fr = fill(fr, (cx, cy), rx, ry)
    return fr


class BronzeBalance:
    """青铜天平。draw(fr, t, cx, cy, size, tilt) —— (cx,cy) 横梁支点；size 横梁全长。
    fill_l / fill_r：盘内物体回调 fill(fr, (x,y), rx, ry)。返回 (fr, info)：info['pan_l']/['pan_r'] 盘口中心。"""
    def __init__(self, seed=0):
        self.seed = seed

    def draw(self, fr, t, cx, cy, size, tilt=0.0, post_len=None, rim=(1.0, 0.78, 0.45), rim_amt=0.6, light=(-0.6, -0.8),
             fill_l=None, fill_r=None, chain=None, base=True, alpha=1.0, break_=0.0):
        s = size / 1000.0
        a = math.radians(tilt)
        dx, dy = math.cos(a) * size / 2, math.sin(a) * size / 2
        L = (cx - dx, cy + dy); R = (cx + dx, cy - dy)     # tilt>0 左盘下沉
        post_len = post_len or 760 * s
        # 立柱 + 底座
        fr = _cyl(fr, (cx, cy - 60 * s), (cx, cy + post_len), 13 * s, 22 * s, light, rim=rim, rim_amt=rim_amt, seed=1)
        for k, yk in enumerate((0.25, 0.55)):
            y = cy + post_len * yk
            fr = _cyl(fr, (cx - 28 * s, y), (cx + 28 * s, y), 9 * s, 9 * s, light, seed=2 + k, rim=rim, rim_amt=rim_amt * 0.6)
        if base:
            for k, (w_, h_) in enumerate(((150, 22), (230, 26), (300, 30))):
                y = cy + post_len + sum((22, 26, 30)[:k]) * s
                fr = _bowl(fr, (cx, y), w_ * s, h_ * s, light, rim=rim, rim_amt=rim_amt * 0.5, seed=5 + k)
        # 顶饰（指针）
        fr = _cyl(fr, (cx, cy - 150 * s), (cx, cy + 10 * s), 2 * s, 11 * s, light, rim=rim, rim_amt=rim_amt, seed=8)
        # 横梁（两端收细）；break_>0：自支点斩断，两半各绕自身中点翻转下坠，秤盘随之甩落
        g = float(np.clip(break_, 0, 1))
        info = {}
        drop = 360 * s
        sw = math.sin(t * 1.7 + self.seed) * 6 * s
        fills = {'l': fill_l, 'r': fill_r}
        for side, sg in (('l', -1), ('r', 1)):
            end = np.array(L if sg < 0 else R, float); piv = np.array((cx, cy), float)
            if g > 0:
                mid = (end + piv) / 2
                ang = math.radians(-sg * 55 * g)
                rot = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
                off = np.array([sg * 120 * s * g, 900 * s * g * g])
                end = mid + rot @ (end - mid) + off; piv2 = mid + rot @ (piv - mid) + off + np.array([sg * 30 * s * g, 0])
            else:
                piv2 = piv
            fr = _cyl(fr, end, piv2, 8 * s, 16 * s, light, rim=rim, rim_amt=rim_amt, seed=9 + (sg > 0))
            fr = _cyl(fr, (end[0] - 0.1, end[1] - 16 * s), (end[0] + 0.1, end[1] + 16 * s), 15 * s, 15 * s, light, seed=11, rim=rim, rim_amt=rim_amt)
            if g > 0:   # 断口：赤热
                fr = _cyl(fr, piv2 - np.array([sg * 6 * s, 0]), piv2, 15 * s, 15 * s, light, base=np.array([1.6, 0.6, 0.2], np.float32), seed=12)
            pc = (end[0] + sw + sg * 260 * s * g, end[1] + drop * (1 - 0.3 * g) + 300 * s * g * g)
            rx = 150 * s
            for k in (-1, 0, 1):
                fr = _cyl(fr, (end[0], end[1] + 10 * s), (pc[0] + k * rx * 0.85, pc[1] + k * k * 4 * s), 2.6 * s, 2.6 * s, light, spec=1.2,
                          seed=20 + k, band=9 * s, rim=rim, rim_amt=rim_amt * 0.8)
            fr = _bowl(fr, pc, rx, 55 * s, light, rim=rim, rim_amt=rim_amt, seed=30 + (sg > 0), fill=fills[side])
            info['pan_' + side] = pc; info['rx'] = rx
        if g <= 0:
            fr = _cyl(fr, (cx - 0.1, cy - 16 * s), (cx + 0.1, cy + 16 * s), 18 * s, 18 * s, light, seed=13, rim=rim, rim_amt=rim_amt)
        return fr, info


# =============================================================== 第三棒：描金漆盒盖（高分辨率，倒角金边 + 回纹带 + 包角铜钉 + 锁扣）
def _bevel_shade(m, width=6.0, light=(-0.6, -0.8), k=5.0):
    """对金属件遮罩做倒角着色：模糊高度 → 法线 → 漫反射 + 高光。返回 (shade, spec)。"""
    hgt = cv2.GaussianBlur(m, (0, 0), width)
    gx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3) * k; gy = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3) * k
    n = np.dstack([-gx, -gy, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    L = np.array([light[0], light[1], 0.7]); L /= np.linalg.norm(L)
    Hh = L + np.array([0, 0, 1.0]); Hh /= np.linalg.norm(Hh)
    return np.clip(n @ L, 0, 1), np.clip(n @ Hh, 0, 1) ** 30


def ornate_lid(w=1200, h=820, seed=66, glyphs='', gsize=300, gpos=None):
    """描金黑漆盒盖（俯视）：漆面断纹 + 倒角金边 + 回纹带 + 包角铜钉 + 锁扣；glyphs 给出时字以金箔阴刻进盖面。
    返回 (col RGB float32, glyph_mask)。"""
    n1 = cv2.resize(nz(256, seed + 9, 3, 5), (w, h)); n2 = cv2.resize(nz(256, seed + 10, 30, 2), (w, h))
    col = np.array([0.045, 0.026, 0.022], np.float32) * (0.65 + 0.7 * n1[..., None])
    cr = np.clip(1 - np.abs(np.sin(n2 * 40)) / 0.04, 0, 1) * (n1 > 0.55)
    col *= (1 - 0.45 * cr[..., None])
    # 漆面高光（一条斜向柔光，表现漆的镜面感）
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    col += (np.exp(-(((xx * 0.6 + yy) - (w * 0.35 + h * 0.3)) / (h * 0.18)) ** 2) * 0.05)[..., None] * np.array([1.0, 0.9, 0.8], np.float32)
    m = np.zeros((h, w), np.float32)
    b = int(h * 0.05)
    cv2.rectangle(m, (b // 2, b // 2), (w - b // 2, h - b // 2), 1.0, int(b * 0.9))                 # 外金边（厚）
    cv2.rectangle(m, (int(b * 2.6), int(b * 2.6)), (w - int(b * 2.6), h - int(b * 2.6)), 1.0, max(3, b // 6))   # 内线
    # 回纹带
    c = int(b * 1.1); y_band = int(b * 1.35)
    def meander(x0, y0, s, rot):
        pts = np.array([[0, 1], [0, 0], [1, 0], [1, 0.75], [0.25, 0.75], [0.25, 0.25], [0.75, 0.25], [0.75, 0.5]], np.float32)
        if rot: pts = pts[:, ::-1]
        p = (pts * s + [x0, y0]).astype(np.int32)
        cv2.polylines(m, [p], False, 1.0, max(2, s // 9), cv2.LINE_AA)
    for x in range(int(b * 2.2), w - int(b * 2.2) - c, c + c // 4):
        meander(x, y_band, c, False); meander(x, h - y_band - c, c, False)
    for y in range(int(b * 2.2), h - int(b * 2.2) - c, c + c // 4):
        meander(y_band, y, c, True); meander(w - y_band - c, y, c, True)
    # 包角（如意云头）+ 铜钉
    cs = int(h * 0.15)
    for (x, y, sx, sy) in ((0, 0, 1, 1), (w, 0, -1, 1), (0, h, 1, -1), (w, h, -1, -1)):
        poly = np.array([[x, y], [x + sx * cs, y], [x + sx * cs * 0.7, y + sy * cs * 0.3], [x + sx * cs * 0.3, y + sy * cs * 0.7], [x, y + sy * cs]], np.int32)
        cv2.fillPoly(m, [poly], 1.0, cv2.LINE_AA)
        for (u, v) in ((0.25, 0.25), (0.62, 0.15), (0.15, 0.62)):
            cv2.circle(m, (int(x + sx * cs * u), int(y + sy * cs * v)), max(3, cs // 14), 0.0, -1, cv2.LINE_AA)
            cv2.circle(m, (int(x + sx * cs * u), int(y + sy * cs * v)), max(2, cs // 18), 1.0, -1, cv2.LINE_AA)
    # 锁扣
    cv2.rectangle(m, (w // 2 - int(w * 0.045), h - int(h * 0.20)), (w // 2 + int(w * 0.045), h - b), 1.0, -1)
    cv2.circle(m, (w // 2, h - int(h * 0.20)), int(w * 0.05), 1.0, -1, cv2.LINE_AA)
    cv2.circle(m, (w // 2, h - int(h * 0.20)), int(w * 0.018), 0.0, -1, cv2.LINE_AA)
    sh, sp = _bevel_shade(m, width=max(2.0, b / 10))
    gold = np.array([0.85, 0.60, 0.26], np.float32)
    metal = gold * (0.35 + 0.9 * sh[..., None]) * (0.8 + 0.4 * n1[..., None]) + sp[..., None] * np.array([1.0, 0.92, 0.75], np.float32) * 0.9
    col = col * (1 - m[..., None]) + metal * m[..., None]
    gm = np.zeros((h, w), np.float32)
    if glyphs:
        gp = gpos or [(w * (i + 1) / (len(glyphs) + 1), h * 0.47) for i in range(len(glyphs))]
        for ch, (gx_, gy_) in zip(glyphs, gp):
            gm = np.maximum(gm, text_mask(ch, gsize, w, h, cx=gx_, cy=gy_))
    return np.clip(col, 0, 3).astype(np.float32), gm


class OrnateBox(LacquerBox):
    """第三棒：暗箱换高分辨率描金纹样（倒角金边 + 回纹 + 包角 + 锁扣），顶面开口内是暖光深处；边线光极弱，去掉“线框盒”感。"""
    def __init__(self, seed=0):
        fr_, _ = ornate_lid(1000, 620, seed + 1)
        sd_, _ = ornate_lid(1000, 620, seed + 2)
        tp_, _ = ornate_lid(1000, 800, seed + 3)
        h, w = tp_.shape[:2]
        hole = np.zeros((h, w), np.float32); cv2.rectangle(hole, (int(w * 0.13), int(h * 0.15)), (int(w * 0.87), int(h * 0.85)), 1.0, -1)
        hole = cv2.GaussianBlur(hole, (0, 0), 2)
        yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
        inner = np.array([0.42, 0.20, 0.06], np.float32) * (0.15 + 0.85 * yy ** 2)[..., None] * 0.6
        tp_ = tp_ * (1 - hole[..., None]) + inner * hole[..., None]
        self.tex = dict(side=sd_, front=fr_, top=tp_, bottom=sd_)
        self.box = Cuboid(self.tex)

    def draw(self, fr, cx, cy, size, yaw=0, pitch=-24, f=2000, flash=0.0, rim=(1.0, 0.72, 0.42), rim_amt=0.12, light=(0.3, 0.8, -0.5)):
        return LacquerBox.draw(self, fr, cx, cy, size, yaw, pitch, f, flash, rim, rim_amt, light)
