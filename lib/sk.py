"""sk.py · 美术·角色组 —— Skia 矢量绘制层

所有角色/道具的“形状”都经由这里用 skia 矢量路径光栅化（解析式抗锯齿、亚像素坐标、贝塞尔曲线、渐变、MaskFilter 模糊），
再以 float32 / uint8 numpy 数组的形式交还给原有的 numpy 合成管线（输出仍为 float32 RGB 0..1）。

核心思路：skia 只负责“覆盖率”(coverage)。每个图元先画进一张与画布同尺寸、包着 numpy 内存的 A8 覆盖率面，
然后在 numpy 里按覆盖率对各通道做 lerp（与旧版 cv2.fillPoly(LINE_AA) 的语义完全一致），因此：
  · 旧代码直接对 C/G/M/D 数组做的 cv2 写入仍然可以与 skia 绘制交错使用（同一块内存）；
  · 一个图元由多个子形状组成（胶囊=矩形+两圆）时，先在覆盖率面里并集，再一次性上色 → 没有接缝/双重 AA 暗边；
  · 条带（ribbon/发丝）按段画时相邻段做 0.6px 重叠，消除 cv2 版本可见的段间细缝。

环境：pip install skia-python ；系统库 sudo apt-get install -y libegl1 libgl1
"""
import math
import numpy as np, cv2

try:
    import skia
    HAVE_SKIA = True
except Exception:                       # 没装 skia 时整个库自动回退到 cv2 光栅化
    skia = None
    HAVE_SKIA = False


# ============================================================== 路径构造
def _pts(p):
    p = np.asarray(p, np.float64).reshape(-1, 2)
    return [skia.Point(float(x), float(y)) for x, y in p]

def path_poly(pts, closed=True, smooth=False):
    """多边形路径；smooth=True 用中点二次贝塞尔把折线磨圆（布料、发丝、袖口）。"""
    p = np.asarray(pts, np.float64).reshape(-1, 2)
    if not smooth or len(p) < 3:
        return skia.Path.Polygon(_pts(p), closed)
    P = skia.Path()
    if closed:
        m = (p + np.roll(p, -1, 0)) / 2
        P.moveTo(*m[-1])
        for i in range(len(p)): P.quadTo(p[i][0], p[i][1], m[i][0], m[i][1])
        P.close()
    else:
        P.moveTo(*p[0])
        for i in range(1, len(p) - 1):
            m = (p[i] + p[i + 1]) / 2; P.quadTo(p[i][0], p[i][1], m[0], m[1])
        P.lineTo(*p[-1])
    return P

def path_circle(c, r):
    P = skia.Path(); P.addCircle(float(c[0]), float(c[1]), float(max(r, 0.15))); return P

def path_ellipse(c, ax, ang_deg=0.0, a0=None, a1=None):
    """椭圆（cv2.ellipse 约定：ax=(半轴x,半轴y)，ang 度，顺时针为正的屏幕坐标）。a0/a1 给定时为扇形弧带（闭合）。"""
    cx, cy = float(c[0]), float(c[1]); rx, ry = float(max(ax[0], 0.15)), float(max(ax[1], 0.15))
    P = skia.Path()
    if a0 is None:
        P.addOval(skia.Rect.MakeLTRB(cx - rx, cy - ry, cx + rx, cy + ry))
    else:
        P.addArc(skia.Rect.MakeLTRB(cx - rx, cy - ry, cx + rx, cy + ry), float(a0), float(a1 - a0)); P.close()
    if ang_deg:
        P.transform(skia.Matrix.RotateDeg(float(ang_deg), skia.Point(cx, cy)))
    return P

def path_capsule_union(a, b, r1, r2):
    """稳妥版胶囊：四边形 + 两圆的并集（Path.op）。"""
    a = np.asarray(a, float); b = np.asarray(b, float); d = b - a; L = float(np.hypot(*d))
    P = path_circle(a, r1)
    if L > 1e-6:
        n = np.array([-d[1], d[0]]) / L
        q = np.array([a + n * r1, b + n * r2, b - n * r2, a - n * r1])
        ar = np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1])
        if ar < 0: q = q[::-1]                      # 与 addCircle(kCW) 同向，避免非零环绕相消
        P.addPoly(_pts(q), True)
        P.addCircle(float(b[0]), float(b[1]), float(max(r2, 0.15)))
    P.setFillType(skia.PathFillType.kWinding)     # 非零环绕 → 自动并集（同向绘制）
    return P

def path_stroke(pts, width, cap='round', closed=False):
    """把折线描边转换成填充路径（用于需要覆盖率的细线）。"""
    P = path_poly(pts, closed=closed)
    paint = skia.Paint(Style=skia.Paint.kStroke_Style, StrokeWidth=float(width),
                       StrokeCap=skia.Paint.kRound_Cap if cap == 'round' else skia.Paint.kButt_Cap,
                       StrokeJoin=skia.Paint.kRound_Join)
    out = skia.Path(); paint.getFillPath(P, out)
    return out


# ============================================================== 覆盖率光栅器
class Coverage:
    """包着 numpy uint8 (h,w) 的 skia A8 面。render(path or [paths]) → (m float32 0..1, (y0,y1,x0,x1))。"""
    def __init__(self, h, w):
        self.h, self.w = h, w
        self.buf = np.zeros((h, w), np.uint8)
        self.surf = skia.Surface(self.buf, colorType=skia.kAlpha_8_ColorType, alphaType=skia.kPremul_AlphaType)
        self.cv = self.surf.getCanvas()
        self.paint = skia.Paint(AntiAlias=True, Color=skia.ColorBLACK)
        self.spaint = skia.Paint(AntiAlias=True, Color=skia.ColorBLACK, Style=skia.Paint.kStroke_Style,
                                 StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)

    def render(self, paths, stroke=None, blur=0.0, alpha=1.0):
        if not isinstance(paths, (list, tuple)): paths = [paths]
        r = None
        for P in paths:
            b = P.computeTightBounds()
            r = b if r is None else skia.Rect.MakeLTRB(min(r.left(), b.left()), min(r.top(), b.top()), max(r.right(), b.right()), max(r.bottom(), b.bottom()))
        if r is None: return None, None
        pad = 2 + (stroke or 0) + blur * 3
        x0 = max(0, int(math.floor(r.left() - pad))); x1 = min(self.w, int(math.ceil(r.right() + pad)))
        y0 = max(0, int(math.floor(r.top() - pad))); y1 = min(self.h, int(math.ceil(r.bottom() + pad)))
        if x1 <= x0 or y1 <= y0: return None, None
        self.buf[y0:y1, x0:x1] = 0
        if stroke:
            p = self.spaint; p.setStrokeWidth(float(stroke))
        else:
            p = self.paint
        if blur > 0 or alpha != 1.0:
            p = skia.Paint(p)
            if blur > 0: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, float(blur)))
            p.setAlphaf(float(alpha))
        for P in paths: self.cv.drawPath(P, p)
        return self.buf[y0:y1, x0:x1].astype(np.float32) * (1 / 255.), (y0, y1, x0, x1)


def lerp_into(arr, m, bb, val):
    """arr[bb] = arr*(1-m) + val*m（uint8 或 float32；arr 可为 2D 或 3D，val 标量或通道向量）。"""
    y0, y1, x0, x1 = bb
    reg = arr[y0:y1, x0:x1]
    if reg.ndim == 3:
        mm = m[..., None]; v = np.asarray(val, np.float32).reshape(1, 1, -1)
    else:
        mm = m; v = np.float32(val)
    out = reg.astype(np.float32) * (1 - mm) + v * mm
    if arr.dtype == np.uint8: out = np.clip(out + 0.5, 0, 255).astype(np.uint8)
    arr[y0:y1, x0:x1] = out


# ============================================================== rig._Canvas 的 skia 版（接口不变）
_DQ = 4096.0          # 深度编码：q = (d + 2048) * 4096 → 24bit（约 0.00025 精度，±2048 范围）

class SkCanvas:
    """与 rig._Canvas 同接口：C(h,w,4 uint8: A,tone,red,metal) / M(h,w,3) / G(h,w) / D(h,w float 深度) / dcur。
    内部是三张 skia 面，直接在 skia 里完成逐通道“按覆盖率 lerp”（与 cv2.fillPoly LINE_AA 语义一致）：
      · B  RGBA8888 预乘：R=tone G=red B=metal A=覆盖（不透明色 SrcOver → RGB 按覆盖率 lerp、A 为覆盖并集）
      · Gs A8：金饰，kSrc 混合（AA 边按覆盖率 lerp 到目标值，可写 0 擦除）
      · Ds RGBA8888：深度 24bit 编码，非 AA 硬写（内轮廓光要用硬边深度）
      · Ms RGBA8888：刀身细节（钢色/刃线/热）
    C/D 在读取时解码（只在合成时读一次）。"""
    backend = 'skia'

    def __init__(self, h, w):
        self.h, self.w = h, w
        self._B = np.zeros((h, w, 4), np.uint8)
        self._Mb = np.zeros((h, w, 4), np.uint8)
        self.G = np.zeros((h, w), np.uint8)
        self._Db = np.zeros((h, w, 4), np.uint8)
        mk = lambda arr, ct: skia.Surface(arr, colorType=ct, alphaType=skia.kPremul_AlphaType).getCanvas()
        self._cB = mk(self._B, skia.kRGBA_8888_ColorType); self._cM = mk(self._Mb, skia.kRGBA_8888_ColorType)
        self._cG = mk(self.G, skia.kAlpha_8_ColorType); self._cD = mk(self._Db, skia.kRGBA_8888_ColorType)
        self._p = skia.Paint(AntiAlias=True)
        self._pg = skia.Paint(AntiAlias=True); self._pg.setBlendMode(skia.BlendMode.kSrc)
        self._pd = skia.Paint(AntiAlias=False); self._pd.setBlendMode(skia.BlendMode.kSrc)
        self.dcur = 0.0
        self._g_used = False

    # ---- 解码视图（兼容旧代码读取）
    @property
    def C(self):
        B = self._B; out = np.empty_like(B)
        out[..., 0] = B[..., 3]; out[..., 1:] = B[..., :3]
        return out
    @property
    def M(self): return self._Mb[..., :3]
    @property
    def D(self):
        Db = self._Db.astype(np.uint32)
        q = (Db[..., 0] << 16) | (Db[..., 1] << 8) | Db[..., 2]
        return np.where(Db[..., 3] > 0, q.astype(np.float32) / _DQ - 2048.0, np.float32(-1e4)).astype(np.float32)

    # ---- 底层
    def _draw(self, P, col, gold=0, stroke=None, depth=True):
        p = self._p
        p.setColor(skia.Color(int(col[1]), int(col[2]), int(col[3]) if len(col) > 3 else 0, 255))
        a = col[0] / 255.0
        if stroke:
            p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(float(stroke)); p.setStrokeCap(skia.Paint.kRound_Cap)
            p.setStrokeJoin(skia.Paint.kRound_Join)
        else:
            p.setStyle(skia.Paint.kFill_Style)
        if a < 0.999: p.setAlphaf(a)
        self._cB.drawPath(P, p)
        if gold or self._g_used:                          # 还没画过金饰时，写 0 是空操作 → 跳过
            self._g_used = self._g_used or bool(gold)
            g = self._pg; g.setStyle(p.getStyle()); g.setStrokeWidth(p.getStrokeWidth()); g.setStrokeCap(skia.Paint.kRound_Cap)
            g.setColor(skia.Color(0, 0, 0, int(gold)))
            self._cG.drawPath(P, g)
        if depth and not stroke:
            q = int(np.clip((self.dcur + 2048.0) * _DQ, 0, 2 ** 24 - 1))
            self._pd.setColor(skia.Color((q >> 16) & 255, (q >> 8) & 255, q & 255, 255))
            self._cD.drawPath(P, self._pd)

    def poly(self, pts, col, gold=0):
        self._draw(path_poly(pts), col, gold)

    def cap(self, a, b, r1, r2, col, gold=0):
        self._draw(path_capsule_union(a, b, r1, r2), col, gold)

    def circ(self, c, r, col, gold=0):
        self._draw(path_circle(c, max(r, 0.3)), col, gold)

    def ell(self, c, ax, ang, col, gold=0):
        self._draw(path_ellipse(c, (max(ax[0], .3), max(ax[1], .3)), ang), col, gold)

    def line(self, a, b, w, col, gold=0):
        if w < 1.6:          # 细线：真·亚像素宽度描边（skia 对 <1px 线按覆盖率衰减）
            self._draw(path_poly([a, b], closed=False), col, gold, stroke=max(0.35, float(w)), depth=False)
        else:
            self.cap(a, b, w / 2, w / 2, col, gold)

    def strand(self, pts, w0, w1, col):
        """发丝/飘带：整根一条贝塞尔磨圆的闭合路径（非逐段拼接）；光泽线为渐细细描边。"""
        pts = np.asarray(pts, float)
        n = len(pts)
        if n < 2: return
        if w0 < 1.3:
            self._draw(path_poly(pts, closed=False, smooth=n >= 3), col, 0, stroke=max(0.35, float(w0)), depth=False)
            return
        if n >= 3: pts = _upsample(pts, 3 if w0 > 2.5 else 2); n = len(pts)
        d = np.gradient(pts, axis=0); nn = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
        u = np.linspace(0, 1, n)
        prof = np.clip(0.55 + 2.2 * u, 0, 1) * (1 - u) ** 0.9 if w1 >= 0 else np.sin(np.pi * np.clip(u * 0.95 + 0.03, 0, 1)) ** 0.7
        w = (max(w1, 0) + (w0 - max(w1, 0)) * prof)[:, None] * 0.5
        poly = np.concatenate([pts + nn * w, (pts - nn * w)[::-1]])
        self._draw(path_poly(poly, smooth=True), col)
        if col[1] > 0 and n > 3 and w0 > 3.0:
            hl = (255, min(255, col[1] + 45), col[2], 0)
            m0, m1 = n // 5, max(n // 5 + 2, int(n * 0.7))
            off = pts[m0:m1] - nn[m0:m1] * w[m0:m1] * 0.35
            self._draw(path_poly(off, closed=False, smooth=True), hl, 0, stroke=max(0.5, w0 * 0.12), depth=False)

    def ribbon(self, pts, widths, normals, cols):
        """逐段着色的带子：相邻段沿切线各外扩 0.6px 重叠 → 无段间细缝。"""
        pts = np.asarray(pts, float)
        for k in range(len(pts) - 1):
            a, b = pts[k], pts[k + 1]
            t = b - a; L = np.hypot(*t)
            e = t / L * 0.6 if L > 1e-6 else t * 0
            q = np.array([a - e + normals[k] * widths[k], b + e + normals[k + 1] * widths[k + 1],
                          b + e - normals[k + 1] * widths[k + 1], a - e - normals[k] * widths[k]])
            self._draw(path_poly(q), cols[k], 0)

    # ---- v2：并集多边形 / 渐变网格 / 内绘（只画在已有覆盖内，不改轮廓与深度）
    def polys(self, polys, col, gold=0, smooth=False, depth=True):
        """多个闭合多边形的并集一次上色（躯干 loft、头部多块凸包）→ 无内部接缝。"""
        P = skia.Path(); P.setFillType(skia.PathFillType.kWinding)
        for q in polys:
            q = np.asarray(q, np.float64).reshape(-1, 2)
            if len(q) < 3: continue
            ar = np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1])
            if ar < 0: q = q[::-1]
            P.addPath(path_poly(q, smooth=smooth))
        self._draw(P, col, gold, depth=depth)

    def path(self, P, col, gold=0, depth=True):
        self._draw(P, col, gold, depth=depth)

    def mesh_tone(self, pos, tones, idx, red=0, outline=None, depth=True):
        """逐顶点色调的三角网格（布料平滑明暗/褶皱）。outline: 可选外轮廓多边形，先以均值色 AA 填充，消除网格锯齿边。"""
        pos = np.asarray(pos, np.float64).reshape(-1, 2); tones = np.clip(np.asarray(tones, np.float64).reshape(-1), 0, 255)
        reds = np.broadcast_to(np.asarray(red, np.float64), tones.shape)
        if outline is not None:
            self._draw(path_poly(outline), (255, float(tones.mean()), float(reds.mean()), 0), 0, depth=depth)
        cols = [skia.Color(int(t + .5), int(r + .5), 0, 255) for t, r in zip(tones, reds)]
        V = skia.Vertices(skia.Vertices.kTriangles_VertexMode, _pts(pos), None, cols, [int(i) for i in idx])
        p = skia.Paint(AntiAlias=True)
        self._cB.drawVertices(V, p, skia.BlendMode.kDst)
        if self._g_used:
            Vg = skia.Vertices(skia.Vertices.kTriangles_VertexMode, _pts(pos), None, None, [int(i) for i in idx])
            g = skia.Paint(self._pg); g.setColor(skia.Color(0, 0, 0, 0)); self._cG.drawVertices(Vg, g)
        if depth:
            q = int(np.clip((self.dcur + 2048.0) * _DQ, 0, 2 ** 24 - 1))
            Vd = skia.Vertices(skia.Vertices.kTriangles_VertexMode, _pts(pos), None, None, [int(i) for i in idx])
            self._pd.setColor(skia.Color((q >> 16) & 255, (q >> 8) & 255, q & 255, 255))
            self._cD.drawVertices(Vd, self._pd)

    def paint_in(self, P, col, alpha=1.0, blur=0.0, stroke=None):
        """在已有覆盖内部作画（SrcATop）：褶皱阴影、眼窝、发束高光等，不改变轮廓 A 与深度。col=(tone, red, metal)。"""
        p = skia.Paint(AntiAlias=True)
        p.setColor(skia.Color(int(np.clip(col[0], 0, 255)), int(np.clip(col[1] if len(col) > 1 else 0, 0, 255)),
                              int(np.clip(col[2] if len(col) > 2 else 0, 0, 255)), 255))
        p.setAlphaf(float(np.clip(alpha, 0, 1)))
        p.setBlendMode(skia.BlendMode.kSrcATop)
        if blur > 0: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, float(blur)))
        if stroke:
            p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(float(stroke))
            p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
        self._cB.drawPath(P, p)

    # ---- 通用：对任意通道填充 / 描边
    def _tgt(self, target, P, val, stroke=None, depth=False):
        if target == 'C':
            self._draw(P, val, 0, stroke=stroke, depth=depth); return
        if target == 'G':
            self._g_used = self._g_used or bool(val)
            g = skia.Paint(self._pg); g.setColor(skia.Color(0, 0, 0, int(val)))
            if stroke: g.setStyle(skia.Paint.kStroke_Style); g.setStrokeWidth(float(stroke)); g.setStrokeCap(skia.Paint.kRound_Cap)
            self._cG.drawPath(P, g); return
        if target == 'M':
            m = skia.Paint(AntiAlias=True); v = list(val) + [0, 0, 0]
            m.setColor(skia.Color(int(v[0]), int(v[1]), int(v[2]), 255))
            if stroke: m.setStyle(skia.Paint.kStroke_Style); m.setStrokeWidth(float(stroke)); m.setStrokeCap(skia.Paint.kRound_Cap)
            self._cM.drawPath(P, m); return
        raise ValueError(target)

    def fill(self, target, pts, val, depth=False): self._tgt(target, path_poly(pts), val, depth=depth)
    def stroke(self, target, pts, val, width, closed=False): self._tgt(target, path_poly(pts, closed=closed), val, stroke=max(0.35, float(width)))
    def fill_ell(self, target, c, ax, ang, val): self._tgt(target, path_ellipse(c, ax, ang), val)


def _upsample(p, k):
    p = np.asarray(p, float); n = len(p)
    P = np.vstack([p[:1] * 2 - p[1:2], p, p[-1:] * 2 - p[-2:-1]])
    u = np.linspace(0, 1, k, endpoint=False)[:, None]
    out = []
    for i in range(n - 1):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        out.append(0.5 * (2 * p1 + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    out.append(p[-1:])
    return np.vstack(out)


# ============================================================== 浮点渲染面（渐变 / 网格 / 模糊直接出 float32）
class FloatSurface:
    """包着 numpy float32 (h,w,4) 的 skia RGBA_F32 面（预乘）。用于渐变填充、带顶点色的网格（刀光扫掠面）、
    MaskFilter 模糊辉光等“连续值”绘制。.rgb() / .alpha() 取回 numpy。"""
    def __init__(self, h, w):
        self.h, self.w = h, w
        self.buf = np.zeros((h, w, 4), np.float32)
        self.surf = skia.Surface(self.buf, colorType=skia.kRGBA_F32_ColorType, alphaType=skia.kPremul_AlphaType)
        self.cv = self.surf.getCanvas()

    def clear(self): self.buf[:] = 0

    def paint(self, color=(1, 1, 1), alpha=1.0, blur=0.0, blend=None, shader=None, stroke=None, cap='round'):
        p = skia.Paint(AntiAlias=True)
        p.setColor4f(skia.Color4f(float(color[0]), float(color[1]), float(color[2]), float(alpha)))
        if blur > 0: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, float(blur)))
        if blend == 'plus': p.setBlendMode(skia.BlendMode.kPlus)
        elif blend == 'src': p.setBlendMode(skia.BlendMode.kSrc)
        elif blend == 'screen': p.setBlendMode(skia.BlendMode.kScreen)
        if shader is not None: p.setShader(shader)
        if stroke:
            p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(float(stroke))
            p.setStrokeCap(skia.Paint.kRound_Cap if cap == 'round' else skia.Paint.kButt_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
        return p

    def path(self, P, **kw): self.cv.drawPath(P, self.paint(**kw))

    def mesh(self, pos, cols, idx, blend='plus'):
        """三角网格 + 逐顶点颜色（RGBA 0..1，非预乘），平滑插值，无缝。pos (n,2), cols (n,4), idx (m,) 三角形索引。"""
        c = np.clip(np.asarray(cols, np.float64), 0, 1)
        cc = (np.clip(c[:, 3] * 255 + 0.5, 0, 255).astype(np.uint32) << 24) | (np.clip(c[:, 0] * 255 + .5, 0, 255).astype(np.uint32) << 16) | \
             (np.clip(c[:, 1] * 255 + .5, 0, 255).astype(np.uint32) << 8) | np.clip(c[:, 2] * 255 + .5, 0, 255).astype(np.uint32)
        V = skia.Vertices(skia.Vertices.kTriangles_VertexMode, _pts(pos), None, [int(x) for x in cc], [int(i) for i in idx])
        p = skia.Paint(AntiAlias=True)
        bm = {'plus': skia.BlendMode.kPlus, 'src': skia.BlendMode.kSrc, 'over': skia.BlendMode.kSrcOver}[blend]
        p.setBlendMode(bm)
        self.cv.drawVertices(V, p, skia.BlendMode.kDst)

    def rgb(self): return self.buf[..., :3]
    def alpha(self): return self.buf[..., 3]


def linear_gradient(p0, p1, colors, stops=None):
    """线性渐变着色器。colors: [(r,g,b,a)...] 0..1。"""
    cs = [skia.Color4f(*map(float, c)).toColor() for c in colors]
    return skia.GradientShader.MakeLinear([skia.Point(*map(float, p0)), skia.Point(*map(float, p1))], cs,
                                          None if stops is None else [float(s) for s in stops])

def radial_gradient(c, r, colors, stops=None):
    cs = [skia.Color4f(*map(float, cc)).toColor() for cc in colors]
    return skia.GradientShader.MakeRadial(skia.Point(*map(float, c)), float(r), cs, None if stops is None else [float(s) for s in stops])


def path_limb(pts, radii, k=4, cap=True):
    """可变半径肢体外形：沿折线（Catmull 加密）两侧按半径偏移 + 两端半圆帽 → 平滑闭合路径（关节过渡自然）。"""
    pts = np.asarray(pts, np.float64); r = np.asarray(radii, np.float64)
    if len(pts) >= 3:
        P = _upsample(pts, k); rr = np.interp(np.linspace(0, len(pts) - 1, len(P)), np.arange(len(pts)), r)
    else:
        P = pts; rr = r
    d = np.gradient(P, axis=0); L = np.linalg.norm(d, axis=1, keepdims=True) + 1e-9; d = d / L
    n = np.stack([-d[:, 1], d[:, 0]], 1)
    left = P + n * rr[:, None]; right = P - n * rr[:, None]
    out = [left]
    if cap:
        a1 = math.atan2(n[-1, 1], n[-1, 0]); out.append(np.stack([P[-1, 0] + rr[-1] * np.cos(a1 - np.linspace(0, math.pi, 7)[1:-1]),
                                                                  P[-1, 1] + rr[-1] * np.sin(a1 - np.linspace(0, math.pi, 7)[1:-1])], 1))
    out.append(right[::-1])
    if cap:
        a0 = math.atan2(-n[0, 1], -n[0, 0]); out.append(np.stack([P[0, 0] + rr[0] * np.cos(a0 - np.linspace(0, math.pi, 7)[1:-1]),
                                                                 P[0, 1] + rr[0] * np.sin(a0 - np.linspace(0, math.pi, 7)[1:-1])], 1))
    poly = np.vstack(out)
    Pth = path_poly(poly, smooth=True); Pth.setFillType(skia.PathFillType.kWinding)
    return Pth, poly


def path_union(polys, smooth=False):
    P = skia.Path(); P.setFillType(skia.PathFillType.kWinding)
    for q in polys:
        q = np.asarray(q, np.float64).reshape(-1, 2)
        if len(q) < 3: continue
        ar = np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1])
        if ar < 0: q = q[::-1]
        P.addPath(path_poly(q, smooth=smooth))
    return P


def path_and(a, b):
    """路径求交（虹膜裁进眼白等）。"""
    try:
        return skia.Op(a, b, skia.PathOp.kIntersect_PathOp)
    except Exception:
        return a


def mask(h, w, paths, blur=0.0, stroke=None):
    """一次性：把路径光栅化为 float32 (h,w) 覆盖率（可带 MaskFilter 高斯模糊）。"""
    cv_ = Coverage(h, w)
    m, bb = cv_.render(paths, stroke=stroke, blur=blur)
    out = np.zeros((h, w), np.float32)
    if m is not None: out[bb[0]:bb[1], bb[2]:bb[3]] = m
    return out
