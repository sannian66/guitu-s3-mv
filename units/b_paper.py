"""units/b_paper.py — B 组「名帖纸人」（第三棒，替换 lib/paper.PaperFigure 的纸扎造型）
设计：不是纸扎道具，而是从生死簿上裁下来的人形——
  · 一张真宣纸：纤维、毛边（撕裂纤维边）、一道竖向折痕（两面受光不同 → 读得出是纸）
  · 身上竖写一个人名（墨，微晕）：纸人 = 生死簿里被写下的那个人（接 P01/P02 母题）
  · 无脸、无腮红；逆光时透光（纸厚处更暗），正光时有折面明暗
用法：
  F = NameFigure(seed, name='张三', view='front'|'side')
  fr = F.draw(fr, x, y_foot, height, bow=0..1, tilt=deg, light='back'|'front', wet=0..1, alpha=1, blur=0, rim_col=GOLD, card=deg)
"""
import math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv')
H0 = 640                     # 纸人基准高（像素）
_FONT = {}


def _font(sz):
    if sz not in _FONT:
        for p in (ROOT + '/fonts/NotoSerifSC-Bold.otf', ROOT + '/fonts/SourceHanSerifSC-Heavy.otf'):
            try:
                _FONT[sz] = ImageFont.truetype(p, sz); break
            except Exception:
                continue
    return _FONT[sz]


def _chaikin(pts, n=3):
    p = np.asarray(pts, np.float32)
    for _ in range(n):
        q = np.roll(p, -1, 0)
        p = np.stack([0.75 * p + 0.25 * q, 0.25 * p + 0.75 * q], 1).reshape(-1, 2)
    return p


def _noise(h, w, seed, sc):
    r = np.random.default_rng(seed)
    a = r.random((max(2, h // sc), max(2, w // sc))).astype(np.float32)
    return cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def _fbm(h, w, seed):
    return (0.5 * _noise(h, w, seed, 48) + 0.3 * _noise(h, w, seed + 1, 16) + 0.2 * _noise(h, w, seed + 2, 5))


# 轮廓（单位：x 以中线为 0，y 以脚为 0 向上，总高 100）
FRONT_LOW = [(-15, 0), (-12.5, 16), (-11, 34), (-10, 53), (10, 53), (11, 34), (12.5, 16), (15, 0), (5, 1.0), (0, 0.3), (-5, 1.0)]
FRONT_UP = [(-9.5, 42), (-10.8, 55), (-12, 41.5), (-19, 40.5), (-18.6, 60), (-14.5, 73.5), (-10, 77.5), (-4.5, 79.5), (-2.6, 82.3),
            (2.6, 82.3), (4.5, 79.5), (10, 77.5), (14.5, 73.5), (18.6, 60), (19, 40.5), (12, 41.5), (10.8, 55), (9.5, 42)]
SIDE_LOW = [(-7, 0), (-6.6, 20), (-6.2, 53), (6.8, 53), (7.5, 26), (10.5, 6), (12.5, 0), (3, 0.8)]
SIDE_UP = [(-6.2, 42), (-7.4, 62), (-6.6, 76), (-2, 80.5), (0.5, 82.4), (3.6, 80.5), (5.6, 76), (7, 66), (13.5, 50), (14.2, 43.5),
           (9, 43), (6.2, 55), (6.6, 42)]
HEAD_F = (0, 89.4, 6.0, 7.0)       # cx, cy, rx, ry
HEAD_S = (1.6, 89.0, 5.8, 6.8)
HINGE = (0.0, 46.0)


class NameFigure:
    def __init__(self, seed=0, name='', view='front', tone=(0.90, 0.86, 0.76)):
        self.seed, self.name, self.view = seed, name, view
        self.tone = np.array(tone, np.float32)
        self.parts = {}
        for part in ('low', 'up'):
            self.parts[part] = self._build(part)

    # ---------------------------------------------------------- 一块纸（RGBA，带折痕/纤维/毛边/名字）
    def _build(self, part):
        s = H0 / 100.0
        pad = 30
        w = int(46 * s) + 2 * pad
        if part == 'low':
            y0u, y1u = -2, 55
        else:
            y0u, y1u = 40, 98
        h = int((y1u - y0u) * s) + 2 * pad
        ss = 2
        M = np.zeros((h * ss, w * ss), np.uint8)
        def P(pts):
            q = _chaikin(pts, 2)
            X = (q[:, 0] * s + w / 2) * ss
            Y = ((y1u - q[:, 1]) * s + pad) * ss
            return np.stack([X, Y], 1).astype(np.int32)
        if self.view == 'front':
            poly = FRONT_LOW if part == 'low' else FRONT_UP; hd = HEAD_F
        else:
            poly = SIDE_LOW if part == 'low' else SIDE_UP; hd = HEAD_S
        cv2.fillPoly(M, [P(poly)], 255, cv2.LINE_AA)
        if part == 'up':
            cx, cy = (hd[0] * s + w / 2) * ss, ((y1u - hd[1]) * s + pad) * ss
            cv2.ellipse(M, (int(cx), int(cy)), (int(hd[2] * s * ss), int(hd[3] * s * ss)), 0, 0, 360, 255, -1, cv2.LINE_AA)
        m = cv2.resize(M, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.
        r = np.random.default_rng(self.seed * 7 + (0 if part == 'low' else 1))
        # 毛边：边带内用纤维噪声侵蚀 + 外溢细纤维
        edge = cv2.GaussianBlur(m, (0, 0), 2.2)
        fib = _noise(h, w, self.seed + 31, 2) * 0.6 + _noise(h, w, self.seed + 32, 7) * 0.4
        a = np.clip((edge - 0.5) * 3.0 + 0.5 + (fib - 0.5) * 0.9, 0, 1)
        a = np.maximum(a * (m > 0.02), m * (edge > 0.9))
        # 纸面：底色 × fbm 云絮 + 纤维条纹
        n = _fbm(h, w, self.seed + 40)
        streak = cv2.resize(r.random((h // 3 + 1, 6)).astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        streak = cv2.GaussianBlur(streak, (0, 0), 1.0)
        base = self.tone[None, None] * (0.86 + 0.18 * n[..., None] + 0.05 * (streak[..., None] - 0.5))
        # 长纤维（细亮丝）
        fl = np.zeros((h, w), np.float32)
        for _ in range(int(w * h / 3500)):
            x0, y0 = r.uniform(0, w), r.uniform(0, h); ang = r.uniform(0, math.pi); L = r.uniform(8, 30)
            pts = [(x0 + math.cos(ang + 0.3 * math.sin(k)) * L * k / 4, y0 + math.sin(ang + 0.3 * math.sin(k)) * L * k / 4) for k in range(5)]
            cv2.polylines(fl, [np.array(pts, np.int32)], False, float(r.uniform(0.3, 1.0)), 1, cv2.LINE_AA)
        base = base * (1 - 0.06 * fl[..., None]) + 0.04 * fl[..., None]
        # 折痕：中线竖折，左面背光
        X = np.arange(w)[None, :] - w / 2
        fold = 0.80 + 0.20 * (X > 0)
        crease = np.exp(-(X / 2.2) ** 2) * 0.10
        shade = fold + crease
        # 名字（只写在上半身胸前竖排，墨 + 微晕）
        ink = np.zeros((h, w), np.float32)
        if self.name:
            nm = self.name
            if part == 'up':
                fs = int(5.6 * s)
                im = Image.new('L', (w, h), 0); d = ImageDraw.Draw(im)
                ytop = (y1u - 76) * s + pad
                for k, ch in enumerate(nm[:2]):
                    d.text((w / 2 + (2 if self.view == 'side' else 0) * s, ytop + k * fs * 1.05), ch, fill=255, font=_font(fs), anchor='mt')
                ink = np.asarray(im, np.float32) / 255.
            elif len(nm) > 2:
                fs = int(5.6 * s)
                im = Image.new('L', (w, h), 0); d = ImageDraw.Draw(im)
                ytop = (y1u - 37) * s + pad
                for k, ch in enumerate(nm[2:4]):
                    d.text((w / 2, ytop + k * fs * 1.05), ch, fill=255, font=_font(fs), anchor='mt')
                ink = np.asarray(im, np.float32) / 255.
            ink = np.maximum(ink, cv2.GaussianBlur(ink, (0, 0), 2.5) * 0.45) * (n * 0.4 + 0.75)
        # 衣领一笔（淡墨）
        if part == 'up':
            cl = np.zeros((h, w), np.uint8)
            yy = int((y1u - 79) * s + pad)
            cv2.line(cl, (int(w / 2 - 4.5 * s), yy), (int(w / 2), int(yy + 6 * s)), 255, int(1.1 * s), cv2.LINE_AA)
            cv2.line(cl, (int(w / 2 + 4.5 * s), yy), (int(w / 2), int(yy + 6 * s)), 255, int(1.1 * s), cv2.LINE_AA)
            ink = np.maximum(ink, cv2.GaussianBlur(cl.astype(np.float32) / 255., (0, 0), 1.2) * 0.35)
        else:
            cl = np.zeros((h, w), np.uint8)
            yy = int((y1u - 40.5) * s + pad)
            cv2.line(cl, (int(w / 2 - 11 * s), yy), (int(w / 2 + 11 * s), yy), 255, int(1.0 * s), cv2.LINE_AA)
            ink = np.maximum(ink, cv2.GaussianBlur(cl.astype(np.float32) / 255., (0, 0), 1.2) * 0.30)
        thick = cv2.GaussianBlur(m, (0, 0), 9)                 # 厚度（透光时边缘更亮）
        return dict(a=a.astype(np.float32), base=base.astype(np.float32), shade=shade.astype(np.float32), ink=ink.astype(np.float32),
                    thick=thick.astype(np.float32), n=n, w=w, h=h, pad=pad, y1u=y1u)

    # ---------------------------------------------------------- 着色一块
    def _shade(self, P, light, wet, rim_col, ink_k, grade):
        a, base, shade, ink, thick = P['a'], P['base'], P['shade'], P['ink'], P['thick']
        if light == 'back':
            # 逆光：纸透光，暖；中心厚处略暗、边缘亮（轮廓光）
            col = base * (0.55 + 0.25 * shade)[..., None] * np.array([1.05, 0.95, 0.78], np.float32)
            edge = np.clip(a - cv2.GaussianBlur(a, (0, 0), 2.0), 0, 1) * 2.2 * (0.45 + 0.9 * P['n']) + np.clip(1 - thick, 0, 1) * 0.25
            col = col + edge[..., None] * rim_col[None, None] * 0.75
        else:
            col = base * shade[..., None]
            edge = np.clip(a - cv2.GaussianBlur(a, (0, 0), 2.5), 0, 1) * 2.0
            col = col + edge[..., None] * rim_col[None, None] * 0.35
        if wet > 0:
            sp = np.clip((_noise(P['h'], P['w'], self.seed + 77, 5) * 0.5 + _noise(P['h'], P['w'], self.seed + 78, 16) * 0.5 - (0.8 - 0.35 * wet)) * 4, 0, 1)
            col = col * (1 - 0.28 * sp[..., None]) + sp[..., None] * np.array([0.05, 0.045, 0.04], np.float32) * 0.3
            ink = np.maximum(ink, cv2.GaussianBlur(ink, (0, 0), 6 + 10 * wet) * 0.8 * wet)
        col = col * (1 - ink[..., None] * 0.92 * ink_k) + ink[..., None] * ink_k * np.array([0.03, 0.025, 0.03], np.float32)
        if grade is not None:
            col = col * np.asarray(grade, np.float32)[None, None]
        return col

    def draw(self, fr, x, y, height, bow=0.0, tilt=0.0, light='back', wet=0.0, alpha=1.0, blur=0.0, rim_col=(1.0, 0.78, 0.38),
             card=0.0, ink_k=1.0, grade=None, flip=False):
        """x,y = 脚底中点屏幕坐标；bow 0..1（侧面：上身绕腰前折 80°；正面：上身竖向压缩）；tilt 整体旋转（度，顺时针）"""
        rim_col = np.asarray(rim_col, np.float32)
        k = height / H0
        sx = math.cos(math.radians(card)) * (-1 if flip else 1)
        if abs(sx) < 0.04: return fr
        s = H0 / 100.0
        th = math.radians(tilt)
        R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
        out = fr
        for part in ('low', 'up'):
            P = self.parts[part]
            col = self._shade(P, light, wet, rim_col, ink_k, grade)
            a = P['a'] * alpha
            if part == 'up' and bow > 0 and self.view == 'front':
                col = col * (1 - 0.35 * bow)
            # 局部坐标：纸块像素 (u,v) → 人形单位 (X,Y)
            w, h, pad, y1u = P['w'], P['h'], P['pad'], P['y1u']
            # 像素→相对脚底中点（屏幕像素，y 向下），先做 bow
            A = np.array([[sx * k, 0, 0], [0, k, 0]], np.float64)
            off = np.array([-w / 2, -(y1u * s + pad)])          # 纸块左上角相对脚底（基准像素）
            Mloc = np.array([[1, 0, off[0]], [0, 1, off[1]], [0, 0, 1]], np.float64)
            if part == 'up' and bow > 0:
                hy = -HINGE[1] * s
                if self.view == 'side':
                    ang = math.radians(80 * bow)
                    Rb = np.array([[math.cos(ang), -math.sin(ang), 0], [math.sin(ang), math.cos(ang), 0], [0, 0, 1]])
                    T1 = np.array([[1, 0, 0], [0, 1, -hy], [0, 0, 1]]); T2 = np.array([[1, 0, 0], [0, 1, hy], [0, 0, 1]])
                    Mloc = T2 @ Rb @ T1 @ Mloc
                else:
                    c_ = max(0.25, math.cos(bow * 1.25))
                    Sq = np.array([[1, 0, 0], [0, c_, hy * (1 - c_)], [0, 0, 1]])
                    Mloc = Sq @ Mloc
            G = np.array([[sx * k, 0, 0], [0, k, 0], [0, 0, 1]])
            Rt = np.array([[R[0, 0], R[0, 1], x], [R[1, 0], R[1, 1], y], [0, 0, 1]])
            Mfull = (Rt @ G @ Mloc)[:2]
            # 只在目标包围盒内变换
            corners = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]]).T
            cs = Mfull @ corners
            bx0, by0 = int(max(0, math.floor(cs[0].min()) - 2)), int(max(0, math.floor(cs[1].min()) - 2))
            bx1, by1 = int(min(out.shape[1], math.ceil(cs[0].max()) + 2)), int(min(out.shape[0], math.ceil(cs[1].max()) + 2))
            if bx1 <= bx0 or by1 <= by0: continue
            Mb = Mfull.copy(); Mb[0, 2] -= bx0; Mb[1, 2] -= by0
            ww, hh = bx1 - bx0, by1 - by0
            C = cv2.warpAffine(col, Mb, (ww, hh), flags=cv2.INTER_LINEAR, borderValue=0)
            Al = cv2.warpAffine(a, Mb, (ww, hh), flags=cv2.INTER_LINEAR, borderValue=0)
            if blur > 0.3:
                C = cv2.GaussianBlur(C, (0, 0), blur); Al = cv2.GaussianBlur(Al, (0, 0), blur)
            if out is fr: out = fr.copy()
            reg = out[by0:by1, bx0:bx1]
            out[by0:by1, bx0:bx1] = reg * (1 - Al[..., None]) + C * Al[..., None]
        return out


NAMES = ['李四', '王五', '赵六', '陈七', '刘大', '周二', '吴三', '郑九', '孙十', '何青', '许平', '黄安', '林生', '谢远', '冯直', '曹宁',
         '萧汪', '叶董', '姚宋', '熊张', '郭何', '徐许', '魏白', '夏黎', '方崔', '杜卢']


class NameCrowd:
    """名帖纸人队列（侧面朝右），rows 排纵深 × cols 列；draw 时按 wave 从队首（右）到队尾（左）依次鞠躬"""
    def __init__(self, seed, rows=3, cols=10, x_span=(120, 1820), y_front=930, h_front=300, depth_scale=0.72, view='side'):
        r = np.random.default_rng(seed)
        self.items = []
        k = 0
        for row in range(rows - 1, -1, -1):                       # 远排先画
            sc = depth_scale ** row
            y = y_front - (1 - sc) * 520
            n = cols + row * 2
            for c in range(n):
                xx = x_span[0] + (x_span[1] - x_span[0]) * (c + 0.5 + r.uniform(-0.2, 0.2)) / n
                F = NameFigure(int(seed * 10 + k), name=NAMES[k % len(NAMES)], view=view)
                self.items.append(dict(F=F, x=xx, y=y + r.uniform(-8, 8) * sc, h=h_front * sc * r.uniform(0.92, 1.06), row=row,
                                       order=(xx - x_span[0]) / (x_span[1] - x_span[0])))
                k += 1

    def draw(self, fr, t, bow=1.0, wave=0.9, wet=0.0, light='back', dof=1.0, x_off=0.0, rim_col=(1.0, 0.78, 0.38), grade=None, alpha=1.0):
        for it in self.items:
            # 队首（右侧 order≈1）先鞠躬
            b = np.clip(bow * (1 + wave) - (1 - it['order']) * wave, 0, 1)
            b = b * b * (3 - 2 * b)
            par = 1.0 - 0.25 * it['row']
            g = grade if grade is not None else (1.0 - 0.18 * it['row'],) * 3
            fr = it['F'].draw(fr, it['x'] + x_off * par, it['y'], it['h'], bow=0.85 * b, light=light, wet=wet, blur=dof * 2.2 * it['row'],
                              rim_col=rim_col, grade=g, alpha=alpha, tilt=1.5 * math.sin(t * 1.3 + it['x']))
        return fr
