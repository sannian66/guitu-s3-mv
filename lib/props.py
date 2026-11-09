"""props.py · 美术·角色组 —— 道具库（skia 矢量 + numpy 材质）

Blade        刀身特写：钢材渐变、刃纹、樋、刃口高光、月光扫光 sheen、烫红/炽热 heat（内透炭火光 + 火星剥落 + 热浪）、
             血 blood（沿樋流下、刃尖滴落）、雨珠 beads（等距刻度）、蒸汽 steam、刻字 engrave
Balance      天平：立柱/横梁/吊链/秤盘、左盘纸人堆、右盘金印、倾斜摆动、红绳滴血、横梁斩断 break_（两半坠落）
Scroll       诏书/卷轴：双轴展开 unroll、宋体竖排逐字显 type_、朱印、撕开 tear（毛边纤维、两半错开）
GiantSeal    巨印（方印石块，底面阳文）：坠落 fall（运动模糊）、落地尘环、斩开 split（两半错位 + 碎块）
seal_face    印面图（朱底白文/白底朱文 + 残损），stamp_imprint 盖印（印泥纹理、按压进度）
CharWall     城墙字砖：砖缝/砖面凹凸/宋体律令刻字，仰拍透视，升起 rise，裂缝金光 crack，崩塌字砖飞向镜头 collapse
Plaque       金匾（天理昭彰/规矩）：黑漆金框金字，开裂 crack（裂纹 + 碎片剥落）
所有 draw 都以 t（秒）或进度为帧参数，无逐帧状态。
"""
import math
import numpy as np, cv2
import sk
from sk import skia
import fx2

W, H = 1920, 1080
RED = np.array([0.72, 0.06, 0.05], np.float32)
GOLD = np.array([1.0, 0.76, 0.40], np.float32)
INK = np.array([0.03, 0.03, 0.035], np.float32)
EMBER = np.array([1.0, 0.55, 0.18], np.float32)
FONTS = {'song': '/workspace/work/mv/fonts/NotoSerifSC.otf', 'kai': '/workspace/work/mv/fonts/MaShanZheng-Regular.ttf',
         'xing': '/workspace/work/mv/fonts/ZhiMangXing-Regular.ttf', 'cao': '/workspace/work/mv/fonts/LiuJianMaoCao-Regular.ttf'}
_TF = {}
def font(name='song', size=40):
    if name not in _TF: _TF[name] = skia.Typeface.MakeFromFile(FONTS.get(name, name))
    return skia.Font(_TF[name], float(size))

def text_path(ch, fname, size, cx, cy):
    """单字 → 居中于 (cx,cy) 的路径。"""
    f = font(fname, size); P = f.getPath(f.textToGlyphs(ch)[0]) if hasattr(f, 'getPath') else None
    if P is None:
        b = skia.TextBlob.MakeFromString(ch, f); P = skia.Path()
    b = P.computeTightBounds()
    P.offset(cx - (b.left() + b.right()) / 2, cy - (b.top() + b.bottom()) / 2)
    return P

def rgba(c, a=1.0): return skia.Color4f(float(c[0]), float(c[1]), float(c[2]), float(a))

def surf():
    return sk.FloatSurface(H, W)

def over(fr, F, alpha=1.0):
    A = np.clip(F.alpha(), 0, 1)[..., None] * alpha
    fr[:] = fr * (1 - A) + F.rgb() * alpha
    return fr

def lin(p0, p1, cols, stops=None):
    return skia.GradientShader.MakeLinear([skia.Point(*map(float, p0)), skia.Point(*map(float, p1))],
                                          [rgba(c[:3], c[3] if len(c) > 3 else 1).toColor() for c in cols],
                                          None if stops is None else [float(s) for s in stops])

def fillp(F, P, color=(1, 1, 1), alpha=1.0, shader=None, blur=0.0, blend=None):
    F.path(P, color=color, alpha=alpha, shader=shader, blur=blur, blend=blend)

def poly(pts, closed=True, smooth=False): return sk.path_poly(np.asarray(pts, float), closed, smooth)


# ============================================================== 刀
class Blade:
    """刀身特写（单刃微弯的唐/苗刀式）。
    Blade(seed=0, curve=0.035, hamon=True)
    draw(fr, t, p0, p1, width, heat=0, sheen=None, blood=0, beads=0, wet=0, steam=0, frost=0, engrave=None, engrave_p=1,
         edge_up=True, moon=(0.86,0.89,0.94), sparks=1.0, haze=True, glow=1.0)
      p0 护手端、p1 刀尖（屏幕坐标），width 刀身宽(px)；edge_up=刃口朝上（False 朝下）
      heat 0..1：墨钢 → 内透暗红炭火（自刃口向内）→ 金白炽热；>0.3 起火星从刃口剥落，>0.2 起热浪扭曲
      sheen 0..1：月光高光沿刃从 p0 扫到 p1 的位置（None=无）
      blood 0..1：血从刀身中段沿樋流向刀尖并在尖端成滴、坠落（S028/S038）
      beads N：雨珠等距排列（S089 刻度），wet 刀面水光；steam 0..1 白汽升腾（S067）；frost 刃上凝霜（S008）
      engrave 文本：刻字（engrave_p 0..1 逐字亮起，S015/S103）
    返回 (fr, info) info: edge 点列（刃口屏幕坐标）、tip、mask。"""
    def __init__(self, seed=0, curve=0.035, hamon=True):
        self.seed = seed; self.curve = curve; self.hamon = hamon
        r = np.random.default_rng(seed); self.hw = r.uniform(0, 6.28, 6)

    def _geom(self, p0, p1, width, edge_up, n=64):
        p0 = np.array(p0, float); p1 = np.array(p1, float); d = p1 - p0; L = np.hypot(*d); u_ = d / L
        nrm = np.array([-u_[1], u_[0]])                      # 屏幕坐标里“左”法向
        if edge_up and nrm[1] > 0: nrm = -nrm
        if not edge_up and nrm[1] < 0: nrm = -nrm
        u = np.linspace(0, 1, n)
        bow = self.curve * L * np.sin(np.pi * u * 0.9) * 0          # 刀背弯
        back = p0[None] + d[None] * u[:, None] - nrm[None] * (self.curve * L * u ** 2)[:, None]
        wv = width * (1 - 0.18 * u)                                  # 渐窄
        tipk = np.clip((u - 0.9) / 0.1, 0, 1)                        # 切先（尖头）
        edge = back + nrm[None] * (wv * (1 - tipk ** 1.4 * 0.93))[:, None]      # 刃口向刀背收成切先
        back = back + nrm[None] * (wv * 0.07 * tipk ** 2)[:, None]
        return u, back, edge, nrm, wv, L

    def draw(self, fr, t, p0, p1, width, heat=0.0, sheen=None, blood=0.0, beads=0, wet=0.0, steam=0.0, frost=0.0, engrave=None,
             engrave_p=1.0, edge_up=True, moon=(0.86, 0.89, 0.94), sparks=1.0, haze=True, glow=1.0, alpha=1.0):
        u, back, edge, nrm, wv, L = self._geom(p0, p1, width, edge_up)
        mc = np.asarray(moon, np.float32)
        outline = np.vstack([back, edge[::-1]])
        P = poly(outline)
        F = surf()
        # 1) 钢：横向渐变（刀背暗 → 鎬筋亮 → 刃面中灰 → 刃口亮）
        mid = len(u) // 2
        g0 = back[mid]; g1 = edge[mid]
        steel = lin(g0, g1, [(0.10, 0.10, 0.11), (0.30, 0.31, 0.34), (0.16, 0.16, 0.18), (0.26, 0.27, 0.30), (0.62, 0.64, 0.68)],
                    [0.0, 0.32, 0.38, 0.75, 1.0])
        fillp(F, P, shader=steel)
        F.cv.save(); F.cv.clipPath(P, skia.ClipOp.kIntersect, True)      # 细节全部裁在刀身内
        # 2) 樋（血槽）：刀背侧一条暗线 + 下沿高光
        f0 = back + nrm[None] * (wv * 0.22)[:, None]; f1 = back + nrm[None] * (wv * 0.30)[:, None]
        k = int(len(u) * 0.78)
        fillp(F, poly(np.vstack([f0[3:k], f1[3:k][::-1]])), color=(0.05, 0.05, 0.06), alpha=0.9)
        F.path(poly(f1[3:k], closed=False), color=tuple(mc * 0.5), alpha=0.6, stroke=max(0.6, width * 0.02))
        # 3) 刃纹（hamon）：刃口侧波浪雾白带
        if self.hamon:
            ph = sum(np.sin(u * (8 + 5 * i) + self.hw[i]) * (0.04 / (i + 1)) for i in range(4))
            hm = back + nrm[None] * (wv * (0.70 + ph))[:, None]
            fillp(F, poly(np.vstack([hm, edge[::-1]])), color=(0.75, 0.77, 0.80), alpha=0.22, blur=max(0.6, width * 0.03))
            F.path(poly(hm, closed=False), color=(0.9, 0.92, 0.95), alpha=0.28, stroke=max(0.5, width * 0.012), blur=0.6)
        # 4) 刃口细亮线 + 刀背棱线
        F.path(poly(back + nrm[None] * (wv * 0.33)[:, None], closed=False), color=tuple(mc * 0.6), alpha=0.5, stroke=max(0.5, width * 0.012))
        F.cv.restore()
        F.path(poly(edge, closed=False), color=tuple(mc * 1.15), alpha=0.95, stroke=max(0.7, width * 0.025))
        # 5) 霜 / 水光
        if frost > 0:
            fr_ = poly(np.vstack([back + nrm[None] * (wv * 0.6)[:, None], edge[::-1]]))
            fillp(F, fr_, color=(0.85, 0.88, 0.92), alpha=0.25 * frost, blur=width * 0.05)
        if wet > 0:
            fillp(F, poly(np.vstack([back + nrm[None] * (wv * 0.36)[:, None], back[::-1] + nrm[None] * (wv[::-1] * 0.5)[:, None]])),
                  color=tuple(mc), alpha=0.18 * wet, blur=width * 0.04)
        # 6) 月光扫光（沿刃移动的亮斑 + 斜光条）
        if sheen is not None and -0.2 < sheen < 1.2:
            c = p0 + (np.array(p1) - np.array(p0)) * sheen
            sh = skia.GradientShader.MakeRadial(skia.Point(*map(float, c)), float(max(width * 2.5, L * 0.12)),
                                                [rgba(mc * 1.4, 0.95).toColor(), rgba(mc, 0.0).toColor()], None)
            F.cv.save(); F.cv.clipPath(P, skia.ClipOp.kIntersect, True)
            F.cv.drawPaint(F.paint(shader=sh, blend='plus'))
            F.cv.restore()
        # 7) 刻字
        if engrave:
            n = len(engrave); fs = width * 0.42
            for i, ch in enumerate(engrave):
                uu = 0.18 + 0.6 * (i + 0.5) / n; j = int(uu * (len(u) - 1))
                c = back[j] + nrm * wv[j] * 0.52
                lit = float(np.clip(engrave_p * n - i, 0, 1))
                tp = text_path(ch, 'kai', fs, *c)
                ang = math.degrees(math.atan2(*(np.array(p1) - np.array(p0))[::-1]))
                tp.transform(skia.Matrix.RotateDeg(float(ang), skia.Point(*map(float, c))))
                fillp(F, tp, color=(0.04, 0.04, 0.05), alpha=0.85)
                if lit > 0:
                    fillp(F, tp, color=tuple(GOLD * 1.6), alpha=lit, blend='plus')
                    fillp(F, tp, color=tuple(GOLD), alpha=lit * 0.8, blur=fs * 0.15, blend='plus')
        # 8) 血：沿樋流向刀尖 + 尖端成滴坠落
        if blood > 0:
            b0 = 0.35; b1 = b0 + (0.97 - b0) * min(1, blood * 1.3)
            ii = (u >= b0) & (u <= b1)
            if ii.sum() > 2:
                cen = back[ii] + nrm[None] * (wv[ii] * 0.42)[:, None]
                wb = wv[ii] * (0.06 + 0.06 * np.sin(np.linspace(0, 9, ii.sum()) + t * 0.5) ** 2)
                d2 = np.gradient(cen, axis=0); n2 = np.stack([-d2[:, 1], d2[:, 0]], 1) / (np.linalg.norm(d2, axis=1, keepdims=True) + 1e-6)
                bp = poly(np.vstack([cen + n2 * wb[:, None], (cen - n2 * wb[:, None])[::-1]]), smooth=True)
                fillp(F, bp, color=tuple(RED * 0.9), alpha=0.95)
                F.path(poly(cen - n2 * wb[:, None] * 0.4, closed=False), color=(1, 0.5, 0.45), alpha=0.5, stroke=max(0.5, width * 0.01))
                if blood > 0.75:                                   # 刃尖滴落（循环）
                    tip = edge[-1]
                    for kq in range(3):
                        ph = (t * 0.9 + kq / 3) % 1.0
                        r_ = width * 0.05 * (0.5 + ph)
                        dy = 0 if ph < 0.55 else (ph - 0.55) ** 2 * 900
                        c = tip + np.array([0, r_ + dy])
                        dp = skia.Path(); dp.addCircle(float(c[0]), float(c[1]), float(r_))
                        dp.moveTo(float(c[0] - r_ * 0.7), float(c[1] - r_ * 0.5)); dp.lineTo(float(c[0]), float(c[1] - r_ * 2.2)); dp.lineTo(float(c[0] + r_ * 0.7), float(c[1] - r_ * 0.5))
                        fillp(F, dp, color=tuple(RED), alpha=0.95)
        # 9) 雨珠（等距刻度）
        if beads:
            for i in range(int(beads)):
                uu = 0.08 + 0.84 * (i + 0.5) / beads; j = int(uu * (len(u) - 1))
                c = back[j] + nrm * wv[j] * 0.55; r_ = width * 0.07
                bp = skia.Path(); bp.addOval(skia.Rect.MakeXYWH(float(c[0] - r_), float(c[1] - r_ * 0.8), float(2 * r_), float(1.6 * r_)))
                fillp(F, bp, color=(0.10, 0.11, 0.13), alpha=0.6)
                F.path(bp, color=tuple(mc * 0.9), alpha=0.7, stroke=max(0.6, r_ * 0.18))
                hp = skia.Path(); hp.addCircle(float(c[0] - r_ * 0.35), float(c[1] - r_ * 0.3), float(r_ * 0.22))
                fillp(F, hp, color=(1, 1, 1), alpha=0.95)
        A = np.clip(F.alpha(), 0, 1)
        col = F.rgb() / np.maximum(A, 1e-3)[..., None]
        add = None
        if heat > 0:
            # 炭火：从刃口向内的热场 × 噪声闪烁
            m = sk.mask(H, W, P)
            ed = sk.mask(H, W, poly(edge, closed=False), stroke=max(1.0, width * 0.06))
            dist = np.clip(fx2.blur_ds(ed, width * 0.22) * 4.5, 0, 1)
            nz = fx2.scroll(fx2.noise(256, self.seed + 3, base=8, octaves=4), t * 20, -t * 35, H // 2, W // 2, 2.0)
            nz = cv2.resize(nz, (W, H))
            hf = np.clip((dist * 0.8 + 0.2 * heat) * (0.55 + 0.9 * nz) * heat * 1.25, 0, 1.6) * m
            hc = np.clip(hf[..., None], 0, 1) ** 1.3
            heatcol = RED[None, None] * 1.3 * np.clip(hc * 2, 0, 1) + (EMBER - RED * 0.6)[None, None] * np.clip(hc * 2 - 0.6, 0, 1) + \
                      (np.array([1, 0.95, 0.85]) - EMBER)[None, None] * np.clip(hc * 2 - 1.4, 0, 1)
            col = col * (1 - np.clip(hf, 0, 1)[..., None] * 0.6) + heatcol * (0.75 + 0.35 * col.mean(2, keepdims=True))
            add = fx2.blur_ds(hf, width * 0.6)[..., None] * (RED * 0.9 + EMBER * 0.5) * glow * heat
        fr[:] = fr * (1 - A[..., None] * alpha) + col * A[..., None] * alpha
        if add is not None: fr += add * alpha
        if heat > 0.2 and haze:
            hm = fx2.blur_ds(A, width * 1.2) * min(1, (heat - 0.2) * 2)
            hm = np.roll(hm, -int(width * 0.8), axis=0)                    # 热浪在刀上方
            fr[:] = fx2.heat_haze(fr, t, mask=hm, amt=3 + 5 * heat)
        if heat > 0.3 and sparks > 0:
            em = fx2.Embers(self.seed + 5, n=int(90 * sparks), box=(int(min(back[:, 0].min(), edge[:, 0].min())), int(edge[:, 1].min() - 20),
                                                              int(max(back[:, 0].max(), edge[:, 0].max())), int(edge[:, 1].max() + 5)),
                            rise=220, life=(0.5, 1.4))
            fr = em.draw(fr, t, intensity=min(1.0, (heat - 0.3) * 2) * sparks, wind=(30, -20))
        if steam > 0:
            stm = fx2.Fog(self.seed + 7)
            m = fx2.blur_ds(A, width * 0.8)
            m = np.clip(np.maximum(m, np.roll(m, -int(width * 1.5), 0) * 0.8), 0, 1)
            fr = stm.draw(fr, t, density=0.9 * steam, y0=0, y1=H, color=(0.85, 0.86, 0.88), speed=(10, -160), mask=m, scale=0.5,
                          top_fade=1)
        info = dict(edge=edge, back=back, tip=tuple(edge[-1]), mask=A)
        return fr, info


# ============================================================== 天平
class Balance:
    """天平（S012/S052/S091/S096/S128）。
    Balance(seed=0, people=60)
    draw(fr, t, cx, cy, size, tilt=0, sway=1, left_people=1.0, right='seal'|'people'|None, right_people=0, break_=0,
         drip=0, rim_color=GOLD, rim=1, light=(0,-1), alpha=1, blur=0)
      cx,cy = 支点（横梁中心）屏幕坐标；size = 横梁全长(px)
      tilt 度（+ = 左盘下沉）；sway 轻微摆动；left_people 0..1 左盘纸人堆高度（越堆越高）
      right='seal' 右盘一枚金印；'people' 右盘小人（S096 一人 vs 千人用 right_people）
      break_ 0..1：横梁自支点断裂，两半带秤盘翻转坠落（S091）
      drip 0..1：左盘红绳滴血（滴的节奏随 t）
    返回 (fr, info) info: 左/右盘中心、梁端点。"""
    def __init__(self, seed=0, people=60):
        r = np.random.default_rng(seed); self.seed = seed
        self.pile = [(r.normal(0, 0.33), r.random() ** 0.8, r.uniform(0.8, 1.2), r.uniform(-25, 25), r.random() < 0.5) for _ in range(people)]

    @staticmethod
    def _person(cx, cy, h, ang=0.0):
        s = h / 100.0
        P = skia.Path()
        P.addCircle(float(cx), float(cy - 88 * s), float(8 * s))
        P.addPoly(sk._pts([(cx - 11 * s, cy - 78 * s), (cx + 11 * s, cy - 78 * s), (cx + 16 * s, cy), (cx - 16 * s, cy)]), True)
        if ang: P.transform(skia.Matrix.RotateDeg(float(ang), skia.Point(float(cx), float(cy))))
        return P

    def draw(self, fr, t, cx, cy, size, tilt=0.0, sway=1.0, left_people=1.0, right='seal', right_people=0, break_=0.0, drip=0.0,
             rim_color=GOLD, rim=1.0, light=(0, -1), alpha=1.0, blur=0.0):
        s = size / 1000.0; rc = np.asarray(rim_color, np.float32)
        ang = math.radians(tilt + sway * 1.2 * math.sin(t * 0.9))
        F = surf()
        dark = (0.05, 0.05, 0.06)
        # 立柱 + 底座 + 顶饰
        post = poly([(cx - 14 * s, cy + 20 * s), (cx + 14 * s, cy + 20 * s), (cx + 22 * s, cy + 760 * s), (cx - 22 * s, cy + 760 * s)])
        base = poly([(cx - 180 * s, cy + 800 * s), (cx + 180 * s, cy + 800 * s), (cx + 120 * s, cy + 740 * s), (cx - 120 * s, cy + 740 * s)])
        fin = poly([(cx, cy - 90 * s), (cx + 18 * s, cy - 40 * s), (cx + 10 * s, cy - 10 * s), (cx - 10 * s, cy - 10 * s), (cx - 18 * s, cy - 40 * s)])
        for P in (post, base, fin):
            fillp(F, P, color=dark)
            F.path(P, color=tuple(rc), alpha=0.55 * rim, stroke=max(1.0, 3 * s), blur=0.6)
        # 横梁两半（断裂时分别旋转坠落）
        half = size / 2
        bk = np.clip(break_, 0, 1); g = bk ** 1.6
        info = {}
        for side in (-1, 1):
            a = ang + side * 0 + (side * 1.3 * g)
            drop = 900 * s * g * g
            piv = np.array([cx + side * 12 * s * bk * 3, cy + drop * (1.0 if side < 0 else 0.85)])
            ca, sa = math.cos(a), math.sin(a)
            def B(px, py): return piv + np.array([px * ca - py * sa, px * sa + py * ca]) if True else None
            end = B(side * half, 0)
            beam = [B(0, -9 * s), B(side * half * 0.97, -6 * s), B(side * half, 0), B(side * half * 0.97, 6 * s), B(0, 9 * s)]
            if bk > 0:                                      # 断口锯齿
                beam = [B(side * 10 * s, -9 * s)] + beam[1:4] + [B(side * 10 * s, 9 * s), B(side * 2 * s, 3 * s), B(side * 14 * s, -2 * s)]
            bp = poly(beam)
            fillp(F, bp, color=dark); F.path(bp, color=tuple(rc), alpha=0.75 * rim, stroke=max(1.0, 2.5 * s), blur=0.5)
            cp = skia.Path(); cp.addCircle(float(end[0]), float(end[1]), float(12 * s))
            fillp(F, cp, color=tuple(GOLD * 0.6)); F.path(cp, color=tuple(GOLD), alpha=0.9, stroke=max(1, 2 * s))
            # 吊绳 + 秤盘（盘子始终竖直下垂，断裂后翻转）
            chain = 380 * s; pr = 150 * s
            pa = side * 1.6 * g + 0.05 * math.sin(t * 1.3 + side)
            pc = end + np.array([math.sin(pa) * chain, math.cos(pa) * chain]) + np.array([0, 0])
            for k in (-1, 0, 1):
                rim_pt = pc + np.array([k * pr * math.cos(pa), -k * pr * math.sin(pa) * 0.2])
                F.path(poly([end, rim_pt], closed=False), color=tuple(rc * 0.7), alpha=0.8, stroke=max(0.8, 1.6 * s))
            dish = skia.Path()
            dish.addArc(skia.Rect.MakeLTRB(float(pc[0] - pr), float(pc[1] - pr * 0.45), float(pc[0] + pr), float(pc[1] + pr * 0.45)), 0, 180)
            dish.close()
            if pa: dish.transform(skia.Matrix.RotateDeg(float(math.degrees(-pa)), skia.Point(*map(float, pc))))
            # 盘中物
            if side < 0 and left_people > 0:
                for (px, py, sc_, an, fl) in self.pile:
                    if py > left_people: continue
                    hx = pc[0] + px * pr * 1.2 * (1 - 0.5 * py); hy = pc[1] - py * pr * 1.6 * left_people
                    fillp(F, self._person(hx, hy, 46 * s * sc_, an + (side * 120 * g)), color=(0.75, 0.72, 0.65), alpha=0.95)
                    F.path(self._person(hx, hy, 46 * s * sc_, an), color=(0.1, 0.1, 0.1), alpha=0.5, stroke=0.8)
            if side > 0:
                if right == 'seal':
                    sz = 70 * s
                    sp = poly([(pc[0] - sz, pc[1]), (pc[0] + sz, pc[1]), (pc[0] + sz * 0.8, pc[1] - sz * 1.2), (pc[0] - sz * 0.8, pc[1] - sz * 1.2)])
                    knob = skia.Path(); knob.addCircle(float(pc[0]), float(pc[1] - sz * 1.45), float(sz * 0.45))
                    for P in (sp, knob):
                        fillp(F, P, shader=lin((pc[0], pc[1] - sz * 2), (pc[0], pc[1]), [GOLD * 1.3, GOLD * 0.55]))
                        F.path(P, color=tuple(GOLD * 1.5), alpha=0.8, stroke=max(1, 2 * s))
                elif right == 'people' and right_people:
                    for i in range(int(right_people)):
                        fillp(F, self._person(pc[0] + (i - (right_people - 1) / 2) * 30 * s, pc[1], 46 * s), color=(0.75, 0.72, 0.65))
            fillp(F, dish, shader=lin((pc[0], pc[1]), (pc[0], pc[1] + pr * 0.45), [(0.12, 0.12, 0.13), (0.03, 0.03, 0.04)]))
            F.path(dish, color=tuple(rc), alpha=0.8 * rim, stroke=max(1.0, 2.5 * s), blur=0.5)
            info['pan_' + ('L' if side < 0 else 'R')] = tuple(pc); info['end_' + ('L' if side < 0 else 'R')] = tuple(end)
            if side < 0 and drip > 0:                          # 红绳 + 滴血
                rs = pc + np.array([-pr * 0.6, pr * 0.2]); re = rs + np.array([-10 * s, 220 * s])
                F.path(poly([rs, (rs + re) / 2 + np.array([-8 * s, 0]), re], closed=False, smooth=True), color=tuple(RED), alpha=0.95,
                       stroke=max(1, 3 * s))
                for kq in range(2):
                    ph = (t * 0.7 + kq * 0.5) % 1.0
                    r_ = 7 * s * (0.6 + 0.6 * min(1, ph * 2))
                    dy = 0 if ph < 0.5 else (ph - 0.5) ** 2 * 2400 * s
                    c = re + np.array([0, r_ + dy])
                    dp = skia.Path(); dp.addCircle(float(c[0]), float(c[1]), float(r_))
                    dp.addPoly(sk._pts([(c[0] - r_ * 0.75, c[1] - r_ * 0.45), (c[0], c[1] - r_ * 2.3), (c[0] + r_ * 0.75, c[1] - r_ * 0.45)]), True)
                    fillp(F, dp, color=tuple(RED * 1.1), alpha=float(drip))
        # 支点金钉
        pv = skia.Path(); pv.addCircle(float(cx), float(cy), float(16 * s))
        fillp(F, pv, shader=lin((cx - 16 * s, cy - 16 * s), (cx + 16 * s, cy + 16 * s), [GOLD * 1.4, GOLD * 0.4]))
        if blur > 0:
            A = fx2.blur_ds(F.buf, blur); F.buf[:] = A
        fr = over(fr, F, alpha)
        return fr, info


# ============================================================== 卷轴 / 诏书
class Scroll:
    """诏书 / 卷轴（S061 剧本、诏令）。
    Scroll(seed=0, lines=None, title='大局', font='song')
    draw(fr, t, cx, cy, w, h, unroll=1, type_=1, tear=0, angle=0, seal=True, light_color=GOLD, alpha=1, mode='h')
      unroll 0..1：双轴从中线向两侧展开；type_ 0..1：宋体铅字逐字打出（右起竖排）
      tear 0..1：纸面沿竖向毛边撕开，两半向外错开并旋转（可配 PaperShreds 碎屑）
    返回 (fr, info)  info: 纸面矩形、撕口点列。"""
    def __init__(self, seed=0, lines=None, title='大局', font_='song'):
        r = np.random.default_rng(seed); self.seed = seed; self.title = title; self.fname = font_
        self.lines = lines or ['奉天承运诏曰', '为顾全大局', '凡事各安其位', '尊卑有序不得僭越', '违者以罪论处', '钦此']
        ys = np.linspace(-0.5, 0.5, 40); xs = np.cumsum(r.normal(0, 0.012, 40)); xs -= xs.mean()
        self.tear = np.stack([xs + r.normal(0, 0.004, 40), ys], 1)

    def draw(self, fr, t, cx, cy, w, h, unroll=1.0, type_=1.0, tear=0.0, angle=0.0, seal=True, light_color=GOLD, alpha=1.0):
        F = surf()
        F.cv.save(); F.cv.rotate(float(angle), float(cx), float(cy))
        hw = w / 2 * max(0.02, unroll)
        g = np.clip(tear, 0, 1)
        halves = [(-1, 0.0), (1, 0.0)]
        for side in (-1, 1):
            F.cv.save()
            if g > 0:
                F.cv.translate(float(side * g * w * 0.25), float(g * g * h * 0.15))
                F.cv.rotate(float(side * g * 9), float(cx), float(cy + h / 2))
            # 纸面：这一半的多边形（撕口一侧为毛边）
            tl = np.array([cx, cy]) + self.tear * [w, h]
            if side < 0:
                pts = np.vstack([[cx - hw, cy - h / 2], tl[0:1] * [1, 1], tl, [[cx - hw, cy + h / 2]]])
                if g <= 0: pts = np.array([[cx - hw, cy - h / 2], [cx, cy - h / 2], [cx, cy + h / 2], [cx - hw, cy + h / 2]])
            else:
                pts = np.vstack([[[cx + hw, cy - h / 2]], tl, [[cx + hw, cy + h / 2]]])
                if g <= 0: pts = np.array([[cx, cy - h / 2], [cx + hw, cy - h / 2], [cx + hw, cy + h / 2], [cx, cy + h / 2]])
            P = poly(pts)
            fillp(F, P, shader=lin((cx, cy - h / 2), (cx, cy + h / 2), [(0.86, 0.80, 0.64), (0.93, 0.88, 0.74), (0.80, 0.73, 0.56)]))
            # 金色边框（锦边）
            F.cv.save(); F.cv.clipPath(P, skia.ClipOp.kIntersect, True)
            band = skia.Path(); band.addRect(skia.Rect.MakeLTRB(float(cx - w), float(cy - h / 2), float(cx + w), float(cy - h / 2 + h * 0.07)))
            band.addRect(skia.Rect.MakeLTRB(float(cx - w), float(cy + h / 2 - h * 0.07), float(cx + w), float(cy + h / 2)))
            fillp(F, band, shader=lin((cx, cy - h / 2), (cx, cy - h / 2 + h * 0.07), [GOLD * 0.75, GOLD * 1.15, GOLD * 0.6]))
            # 文字：右起竖排
            fs = h * 0.085; cols = [self.title] + self.lines
            total = sum(len(c) for c in cols); shown = int(round(type_ * total)); k = 0
            for ci, col in enumerate(cols):
                x = cx + w * 0.40 - ci * fs * 1.45
                for j, ch in enumerate(col):
                    if k >= shown: break
                    y = cy - h / 2 + h * 0.16 + j * fs * 1.12 + (fs * 0.6 if ci else 0)
                    tp = text_path(ch, self.fname, fs * (1.25 if ci == 0 else 1.0), x, y)
                    fillp(F, tp, color=(0.06, 0.05, 0.05) if ci else tuple(RED * 0.9))
                    if k == shown - 1 and type_ < 1:
                        fillp(F, tp, color=(1, 1, 1), alpha=0.5, blend='plus')
                    k += 1
            if seal and type_ >= 0.98:
                sx_, sy_ = cx - w * 0.30, cy + h * 0.22; ss = h * 0.18
                sp = poly([(sx_ - ss / 2, sy_ - ss / 2), (sx_ + ss / 2, sy_ - ss / 2), (sx_ + ss / 2, sy_ + ss / 2), (sx_ - ss / 2, sy_ + ss / 2)])
                fillp(F, sp, color=tuple(RED), alpha=0.85)
                for i, ch in enumerate('御令'):
                    fillp(F, text_path(ch, 'song', ss * 0.42, sx_ + (0.2 - 0.4 * i) * ss, sy_), color=(0.93, 0.88, 0.76), alpha=0.9)
            F.cv.restore()
            if g > 0:                                          # 撕口白色纤维
                F.path(poly(tl, closed=False), color=(0.98, 0.96, 0.9), alpha=0.9, stroke=max(1.5, w * 0.004), blur=0.8)
            F.cv.restore()
        # 卷轴（两端木轴 + 金帽）
        if g < 0.15:
            for side in (-1, 1):
                x = cx + side * (hw + 8)
                rod = skia.Path(); rod.addRoundRect(skia.Rect.MakeLTRB(float(x - w * 0.018), float(cy - h * 0.56), float(x + w * 0.018), float(cy + h * 0.56)), 6, 6)
                fillp(F, rod, shader=lin((x - w * 0.018, cy), (x + w * 0.018, cy), [(0.05, 0.04, 0.04), (0.25, 0.2, 0.18), (0.04, 0.03, 0.03)]),
                      alpha=1 - g / 0.15)
                for yy in (cy - h * 0.58, cy + h * 0.58):
                    cap = skia.Path(); cap.addOval(skia.Rect.MakeLTRB(float(x - w * 0.028), float(yy - w * 0.012), float(x + w * 0.028), float(yy + w * 0.012)))
                    fillp(F, cap, color=tuple(GOLD), alpha=1 - g / 0.15)
        F.cv.restore()
        fr = over(fr, F, alpha)
        return fr, dict(rect=(cx - hw, cy - h / 2, cx + hw, cy + h / 2), tear=np.array([cx, cy]) + self.tear * [w, h])


# ============================================================== 印
def seal_face(text='正', size=400, style='zhu', wear=0.3, seed=0, fname='song'):
    """印面 RGBA (size,size,4) float32：style='zhu' 朱文（白底朱字感：朱色字 + 朱框），'bai' 白文（朱底留白字）。wear 残损。"""
    F = sk.FloatSurface(size, size); s = size
    frame = skia.Path(); frame.addRect(skia.Rect.MakeLTRB(s * 0.04, s * 0.04, s * 0.96, s * 0.96))
    inner = skia.Path(); inner.addRect(skia.Rect.MakeLTRB(s * 0.11, s * 0.11, s * 0.89, s * 0.89))
    n = len(text)
    if n == 1: places = [(0.5, 0.5, 0.74)]
    elif n == 2: places = [(0.5, 0.29, 0.42), (0.5, 0.71, 0.42)]
    else: places = [(0.72, 0.29, 0.40), (0.72, 0.71, 0.40), (0.28, 0.29, 0.40), (0.28, 0.71, 0.40)][:n]
    glyphs = [text_path(ch, fname, s * sc, s * px, s * py) for ch, (px, py, sc) in zip(text, places)]
    if style == 'bai':
        fillp(F, frame, color=tuple(RED))
        for g in glyphs: fillp(F, g, color=(0, 0, 0), blend='src', alpha=0.0)
    else:
        ring = skia.Op(frame, inner, skia.PathOp.kDifference_PathOp)
        fillp(F, ring, color=tuple(RED))
        for g in glyphs: fillp(F, g, color=tuple(RED))
    A = F.alpha().copy()
    if wear > 0:
        nz = cv2.resize(fx2.noise(256, seed + 2, base=12, octaves=4), (s, s))
        A = A * np.clip((nz - wear * 0.55) / 0.08, 0, 1)
        A = A * (0.85 + 0.15 * cv2.resize(fx2.noise(256, seed + 3, base=40, octaves=2), (s, s)))
    out = np.zeros((s, s, 4), np.float32); out[..., :3] = RED; out[..., 3] = A
    return out

def stamp_imprint(fr, face, cx, cy, size, prog=1.0, angle=0.0, alpha=1.0):
    """把印面盖到画面：prog 0..1 按压（0.0–0.3 印面下落放大 → 0.3 接触 → 墨色加深并微晕）。"""
    if prog <= 0: return fr
    k = min(1.0, prog / 0.3); sc = 1.25 - 0.25 * k
    s = int(size * sc)
    img = cv2.resize(face, (s, s), interpolation=cv2.INTER_AREA)
    M = cv2.getRotationMatrix2D((s / 2, s / 2), angle, 1.0); img = cv2.warpAffine(img, M, (s, s))
    a = img[..., 3] * (0.35 + 0.65 * k) * (1 if prog > 0.3 else 0.6) * alpha
    if prog > 0.3: a = np.maximum(a, cv2.GaussianBlur(a, (0, 0), 1.2) * 0.6 * min(1, (prog - 0.3) * 3))
    x0, y0 = int(cx - s / 2), int(cy - s / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + s), min(H, y0 + s)
    if xb <= xa or yb <= ya: return fr
    aa = a[ya - y0:yb - y0, xa - x0:xb - x0, None]
    fr[ya:yb, xa:xb] = fr[ya:yb, xa:xb] * (1 - aa) + img[ya - y0:yb - y0, xa - x0:xb - x0, :3] * aa
    return fr


class GiantSeal:
    """巨印（S017 天降「正」、S019 斩开、S085–S087 是非对错巨印）。石质方印块：顶面/侧面/印面三色，带印钮。
    GiantSeal(text='正', seed=0)
    draw(fr, t, cx, cy, size, fall=1.0, tilt=12, yaw=0, split=0.0, split_angle=-70, show_face=True, rim_color=GOLD, rim=1,
         motion_blur=True, alpha=1)
      cx,cy 印底中心落点；size 印宽(px)；fall 0..1 自画面上方坠落到位（加速，带竖向运动模糊）
      tilt 俯仰：>0 看得到底面阳文（仰视），<0 看到顶面（俯视）
      split 0..1：沿 split_angle 方向的直线斩开，两半沿法向错开、各自旋转，碎块飞散
    返回 (fr, info)  info: impact（fall 刚到 1 时 True）、bottom_y。"""
    def __init__(self, text='正', seed=0):
        self.text = text; self.seed = seed
        r = np.random.default_rng(seed)
        self.debris = [(r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(0.02, 0.07), r.normal(0, 1, 2), r.uniform(-8, 8)) for _ in range(40)]
        self.face = None

    def draw(self, fr, t, cx, cy, size, fall=1.0, tilt=12.0, yaw=0.0, split=0.0, split_angle=-70.0, show_face=True, rim_color=GOLD,
             rim=1.0, motion_blur=True, alpha=1.0):
        f = np.clip(fall, 0, 1); yoff = -(1 - f ** 2) * (cy + size * 1.5)
        s = size; hgt = s * 0.95
        ty = math.radians(tilt)
        by = cy + yoff
        # 方块投影：底面（菱形压扁）+ 侧面
        dz = math.sin(ty) * s * 0.5
        bottom = np.array([[cx - s / 2, by - dz], [cx + s / 2, by - dz], [cx + s / 2 + 0, by + dz], [cx - s / 2, by + dz]])
        top_y = by - hgt
        side = np.array([[cx - s / 2, top_y], [cx + s / 2, top_y], [cx + s / 2, by - dz * (1 if tilt > 0 else -1)], [cx - s / 2, by - dz * (1 if tilt > 0 else -1)]])
        F = surf()
        sp = math.radians(split_angle); nrm = np.array([math.cos(sp + math.pi / 2), math.sin(sp + math.pi / 2)])
        g = np.clip(split, 0, 1)
        halves = [(1, 1.0), (-1, 1.0)] if g > 0 else [(0, 1.0)]
        c0 = np.array([cx, by - hgt / 2])
        rc = np.asarray(rim_color, np.float32)
        for hs, _ in halves:
            F.cv.save()
            if hs:
                off = nrm * hs * g * s * 0.35 + np.array([0, g * g * s * 0.4])
                F.cv.translate(float(off[0]), float(off[1])); F.cv.rotate(float(hs * g * 14), float(c0[0]), float(c0[1]))
                clip = skia.Path(); d = np.array([math.cos(sp), math.sin(sp)]) * 4000
                q = [c0 - d, c0 + d, c0 + d + nrm * hs * 4000, c0 - d + nrm * hs * 4000]
                clip.addPoly(sk._pts(q), True); F.cv.clipPath(clip, skia.ClipOp.kIntersect, True)
            sideP = poly(side)
            fillp(F, sideP, shader=lin((cx - s / 2, 0), (cx + s / 2, 0), [(0.10, 0.09, 0.09), (0.22, 0.20, 0.19), (0.07, 0.06, 0.06)]))
            # 石纹
            for k in range(5):
                yy = top_y + hgt * (0.15 + 0.17 * k)
                F.path(poly([(cx - s / 2, yy), (cx + s / 2, yy + s * 0.02 * math.sin(k))], closed=False), color=(0.3, 0.28, 0.26), alpha=0.25, stroke=1.2)
            # 印钮（兽钮简化为拱形）
            kn = skia.Path(); kn.addArc(skia.Rect.MakeLTRB(float(cx - s * 0.25), float(top_y - s * 0.32), float(cx + s * 0.25), float(top_y + s * 0.18)), 180, 180); kn.close()
            fillp(F, kn, shader=lin((cx, top_y - s * 0.3), (cx, top_y), [(0.24, 0.22, 0.2), (0.08, 0.07, 0.07)]))
            F.path(kn, color=tuple(rc), alpha=0.6 * rim, stroke=max(1, s * 0.006))
            F.path(sideP, color=tuple(rc), alpha=0.7 * rim, stroke=max(1, s * 0.006))
            if show_face and tilt > 0:                         # 底面阳文（朱）
                if self.face is None: self.face = seal_face(self.text, 512, wear=0.2, seed=self.seed)
                fillp(F, poly(bottom), color=tuple(RED * 0.85))
                fp = text_path(self.text, 'song', s * 0.62, cx, by)
                fp.transform(skia.Matrix.Scale(1.0, max(0.05, math.sin(ty)) * 1.0))
                b = fp.computeTightBounds(); fp.offset(cx - (b.left() + b.right()) / 2, by - (b.top() + b.bottom()) / 2)
                fillp(F, fp, color=(0.93, 0.86, 0.72), alpha=0.95)
                F.path(poly(bottom), color=tuple(GOLD * 1.2), alpha=0.6, stroke=max(1, s * 0.006))
            F.cv.restore()
        if g > 0:                                                # 碎块
            for (dx, dy, sz, v, rot) in self.debris:
                p = c0 + np.array([dx * s * 0.4, dy * s * 0.4]) + (v * s * 0.9 + nrm * np.sign(dx) * s * 0.3) * g + np.array([0, g * g * s * 1.2])
                q = sz * s
                pp = poly([p + [-q, -q * 0.6], p + [q * 0.8, -q], p + [q, q * 0.7], p + [-q * 0.7, q]])
                pp.transform(skia.Matrix.RotateDeg(float(rot * g * 40), skia.Point(*map(float, p))))
                fillp(F, pp, color=(0.15, 0.13, 0.12), alpha=float(max(0, 1 - g * 0.6)))
                F.path(pp, color=tuple(rc), alpha=0.5 * float(max(0, 1 - g * 0.6)), stroke=1)
        if motion_blur and f < 1:
            sig = (1 - f) * 25 + 1
            F.buf[:] = cv2.blur(F.buf, (1, int(sig * 3) | 1))
        fr = over(fr, F, alpha)
        return fr, dict(bottom_y=by, impact=f >= 1.0)


# ============================================================== 城墙字砖
class CharWall:
    """城墙（字砖）。墙面纹理在 __init__ 用 skia 预画（砖块倒角渐变、砖缝、宋体律令刻字），逐帧只做透视与特效。
    CharWall(seed=0, cols=16, rows=12, brick=(150,64), text=None, chars_ratio=0.85, fname='song')
    draw(fr, t, x0=0, y0=120, x1=W, y1=960, tilt=0.0, rise=1.0, crack=None, collapse=0.0, collapse_center=(0.5,0.5),
         light_color=GOLD, rim=0.6, dust=1.0, fog=0.0, alpha=1)
      (x0,y0,x1,y1) 墙在屏幕上的矩形（rise<1 时墙从 y1 向上升起）；tilt>0 仰拍（上窄下宽透视，墙顶消失）
      crack: fx2.CrackLight 实例或 dict(prog,open_,spill) —— 墙上的金光裂缝（在墙面坐标里画）
      collapse 0..1：以 collapse_center 为中心，字砖朝镜头炸飞（放大、旋转、景深虚化），墙后露出背景
    返回 (fr, info)  info: H（墙面→屏幕的单应矩阵）。"""
    RULES = '律令法度纲常尊卑礼制规矩天理昭彰顾全大局理所应当铁壁铜墙上令下行不得僭越违者论罪'

    def __init__(self, seed=0, cols=16, rows=12, brick=(150, 64), text=None, chars_ratio=0.85, fname='song'):
        r = np.random.default_rng(seed); self.seed = seed
        bw, bh = brick; self.bw, self.bh = bw, bh; self.cols, self.rows = cols, rows
        Wt, Ht = cols * bw, rows * bh; self.Wt, self.Ht = Wt, Ht
        F = sk.FloatSurface(Ht, Wt)
        fillp(F, poly([(0, 0), (Wt, 0), (Wt, Ht), (0, Ht)]), color=(0.03, 0.03, 0.035))       # 灰缝
        txt = text or self.RULES; k = 0
        self.bricks = []
        for j in range(rows):
            off = (j % 2) * bw / 2
            for i in range(-1, cols + 1):
                x = i * bw + off; y = j * bh
                if x + bw <= 0 or x >= Wt: continue
                g = 3.0
                rect = skia.Path(); rect.addRoundRect(skia.Rect.MakeLTRB(float(x + g), float(y + g), float(x + bw - g), float(y + bh - g)), 4, 4)
                tone = r.uniform(0.11, 0.2)
                fillp(F, rect, shader=lin((x, y), (x, y + bh), [(tone * 1.5, tone * 1.45, tone * 1.4), (tone, tone, tone * 1.02), (tone * 0.6, tone * 0.6, tone * 0.62)],
                                          [0, 0.25, 1]))
                # 砖面麻点
                for _ in range(4):
                    px, py = x + r.uniform(8, bw - 8), y + r.uniform(8, bh - 8)
                    pp = skia.Path(); pp.addCircle(float(px), float(py), float(r.uniform(1, 3)))
                    fillp(F, pp, color=(0.04, 0.04, 0.045), alpha=0.6)
                if r.random() < chars_ratio:
                    ch = txt[k % len(txt)]; k += 1
                    fs = bh * 0.62
                    tp = text_path(ch, fname, fs, x + bw / 2, y + bh / 2)
                    tp2 = text_path(ch, fname, fs, x + bw / 2 + 1.5, y + bh / 2 + 1.5)
                    fillp(F, tp2, color=(0.3, 0.29, 0.28), alpha=0.6)                # 刻痕下沿受光
                    fillp(F, tp, color=(0.02, 0.02, 0.025), alpha=0.95)
                self.bricks.append((x + g, y + g, bw - 2 * g, bh - 2 * g))
        self.tex = F.rgb().copy(); self.texA = np.ones((Ht, Wt), np.float32)
        self.br = np.array(self.bricks, np.float32)
        rr = np.random.default_rng(seed + 1)
        self.bv = rr.normal(0, 1, (len(self.br), 3)); self.brot = rr.normal(0, 1, len(self.br)); self.bdel = rr.uniform(0, 0.25, len(self.br))

    def _homog(self, x0, y0, x1, y1, tilt, rise):
        top = y1 - (y1 - y0) * rise
        sh = (x1 - x0) * 0.5 * np.clip(tilt, 0, 0.95)
        src = np.float32([[0, 0], [self.Wt, 0], [self.Wt, self.Ht], [0, self.Ht]])
        dst = np.float32([[x0 + sh, top], [x1 - sh, top], [x1, y1 + (y1 - y0) * (1 - rise)], [x0, y1 + (y1 - y0) * (1 - rise)]])
        dst[:, 1] = np.where(dst[:, 1] > y1, dst[:, 1], dst[:, 1])
        dst = np.float32([[x0 + sh, top], [x1 - sh, top], [x1, top + (y1 - y0)], [x0, top + (y1 - y0)]])
        return cv2.getPerspectiveTransform(src, dst)

    def draw(self, fr, t, x0=0, y0=120, x1=W, y1=960, tilt=0.0, rise=1.0, crack=None, collapse=0.0, collapse_center=(0.5, 0.5),
             light_color=GOLD, rim=0.6, dust=1.0, fog=0.0, alpha=1.0, crack_kw=None):
        Hm = self._homog(x0, y0, x1, y1, tilt, rise)
        tex = self.tex; A = self.texA
        if collapse > 0:                                        # 被炸飞的砖从墙面挖掉
            A = A.copy()
            cxw, cyw = collapse_center[0] * self.Wt, collapse_center[1] * self.Ht
            d = np.hypot((self.br[:, 0] + self.br[:, 2] / 2 - cxw) / self.Wt, (self.br[:, 1] + self.br[:, 3] / 2 - cyw) / self.Ht)
            gone = (collapse * 1.4 - d * 1.6 - self.bdel) > 0
            for (bx, by, bw, bh) in self.br[gone]:
                A[int(by) - 3:int(by + bh) + 3, int(bx) - 3:int(bx + bw) + 3] = 0
        else:
            gone = np.zeros(len(self.br), bool)
        img = cv2.warpPerspective(tex, Hm, (W, H), flags=cv2.INTER_LINEAR)
        a = cv2.warpPerspective(A, Hm, (W, H), flags=cv2.INTER_LINEAR)
        # 仰拍：墙顶隐入黑暗
        if tilt > 0:
            yy = np.arange(H, dtype=np.float32)[:, None]
            img = img * (0.25 + 0.75 * fx2.smooth(y0, y0 + (y1 - y0) * 0.7, yy))[..., None]
        if fog > 0: img = img * (1 - fog) + np.float32(0.12) * fog
        fr[:] = fr * (1 - a[..., None] * alpha) + img * a[..., None] * alpha
        # 裂缝（墙面坐标 → 屏幕：用实例的 p0/p1 在屏幕坐标里给出时直接画）
        if crack is not None:
            kw = dict(prog=1.0, open_=1.0, spill=1.0); kw.update(crack_kw or {})
            fr = crack.draw(fr, t, **kw)
        if collapse > 0 and gone.any():                       # 飞向镜头的字砖
            Fl = []
            idx = np.nonzero(gone)[0]
            cxw, cyw = collapse_center[0] * self.Wt, collapse_center[1] * self.Ht
            for i in idx:
                bx, by, bw, bh = self.br[i]
                d = math.hypot((bx + bw / 2 - cxw) / self.Wt, (by + bh / 2 - cyw) / self.Ht)
                age = max(0.0, collapse * 1.4 - d * 1.6 - self.bdel[i]) * 1.2
                z = max(0.08, 1.0 - age * (0.8 + 0.3 * self.bv[i, 2]))
                c = cv2.perspectiveTransform(np.float32([[[bx + bw / 2, by + bh / 2]]]), Hm)[0, 0]
                dirv = c - np.array([W / 2, H / 2]); c = np.array([W / 2, H / 2]) + dirv / z + self.bv[i, :2] * 120 * age + [0, 260 * age * age]
                Fl.append((z, i, c, age))
            Fl.sort(key=lambda q: -q[0])
            for z, i, c, age in Fl[-260:]:
                bx, by, bw, bh = self.br[i]
                sprite = tex[int(by):int(by + bh), int(bx):int(bx + bw)]
                if sprite.size == 0: continue
                sc = (math.hypot(Hm[0, 0], Hm[1, 0]) / max(Hm[2, 2], 1e-6)) / z * 0.9
                ang = self.brot[i] * age * 140
                M = cv2.getRotationMatrix2D((bw / 2, bh / 2), ang, sc); M[:, 2] += c - np.array([bw / 2, bh / 2])
                ww = int(bw * sc * 1.6 + 4); hh = int(bh * sc * 1.6 + 4)
                ox, oy = int(c[0] - ww / 2), int(c[1] - hh / 2)
                if ox > W or oy > H or ox + ww < 0 or oy + hh < 0 or ww > 3000: continue
                M[:, 2] -= [ox, oy]
                spr = cv2.warpAffine(sprite, M, (ww, hh)); sa = cv2.warpAffine(np.ones(sprite.shape[:2], np.float32), M, (ww, hh))
                blur = abs(1 / z - 1.2) * 1.5
                if blur > 0.8: spr = cv2.GaussianBlur(spr, (0, 0), blur); sa = cv2.GaussianBlur(sa, (0, 0), blur)
                spr = spr + np.asarray(light_color, np.float32) * 0.15 * rim
                xa, ya, xb, yb = max(0, ox), max(0, oy), min(W, ox + ww), min(H, oy + hh)
                if xb <= xa or yb <= ya: continue
                aa = sa[ya - oy:yb - oy, xa - ox:xb - ox, None] * alpha
                fr[ya:yb, xa:xb] = fr[ya:yb, xa:xb] * (1 - aa) + spr[ya - oy:yb - oy, xa - ox:xb - ox] * aa
        return fr, dict(H=Hm, gone=int(gone.sum()))


# ============================================================== 金匾
class Plaque:
    """金匾（「天理昭彰」S114、「规矩」S022）。黑漆底、金框、金字（思源宋/马善政），开裂与碎片剥落。
    Plaque(text='天理昭彰', seed=0, fname='song')
    draw(fr, t, cx, cy, w, crack=0, light_color=GOLD, sheen=None, tilt=0, alpha=1)
      crack 0..1：裂纹自中心蔓延（金光微透），>0.5 起碎片剥落下坠；sheen 0..1 金光扫过。"""
    def __init__(self, text='天理昭彰', seed=0, fname='song'):
        self.text = text; self.seed = seed; self.fname = fname
        r = np.random.default_rng(seed)
        self.cracks = []
        for k in range(7):
            ang = r.uniform(0, 2 * math.pi); pts = [np.zeros(2)]
            for j in range(8): ang += r.normal(0, 0.35); pts.append(pts[-1] + np.array([math.cos(ang), math.sin(ang) * 0.5]) * r.uniform(0.04, 0.09))
            self.cracks.append(np.array(pts))
        self.chips = [(r.uniform(-0.45, 0.45), r.uniform(-0.35, 0.35), r.uniform(0.02, 0.06), r.normal(0, 1), r.uniform(0.5, 1)) for _ in range(30)]

    def draw(self, fr, t, cx, cy, w, crack=0.0, light_color=GOLD, sheen=None, tilt=0.0, alpha=1.0):
        h = w * 0.36; F = surf()
        F.cv.save(); F.cv.rotate(float(tilt), float(cx), float(cy))
        outer = skia.Path(); outer.addRoundRect(skia.Rect.MakeLTRB(float(cx - w / 2), float(cy - h / 2), float(cx + w / 2), float(cy + h / 2)), w * 0.01, w * 0.01)
        inner = skia.Path(); inner.addRect(skia.Rect.MakeLTRB(float(cx - w / 2 + w * 0.045), float(cy - h / 2 + w * 0.045), float(cx + w / 2 - w * 0.045), float(cy + h / 2 - w * 0.045)))
        fillp(F, outer, shader=lin((cx, cy - h / 2), (cx, cy + h / 2), [GOLD * 1.25, GOLD * 0.55, GOLD * 1.0, GOLD * 0.45]))
        fillp(F, inner, shader=lin((cx, cy - h / 2), (cx, cy + h / 2), [(0.06, 0.05, 0.05), (0.02, 0.02, 0.02)]))
        n = len(self.text); fs = min(h * 0.62, (w * 0.86) / n)
        for i, ch in enumerate(self.text):
            x = cx + (i - (n - 1) / 2) * (w * 0.86 / n)
            tp = text_path(ch, self.fname, fs, x, cy)
            tp2 = text_path(ch, self.fname, fs, x + fs * 0.02, cy + fs * 0.02)
            fillp(F, tp2, color=(0.2, 0.12, 0.05), alpha=0.8)
            fillp(F, tp, shader=lin((x, cy - fs / 2), (x, cy + fs / 2), [GOLD * 1.35, GOLD * 0.75, GOLD * 1.1]))
        if sheen is not None:
            c = cx - w / 2 + w * sheen
            sh = lin((c - w * 0.12, cy - h), (c + w * 0.12, cy + h), [(1, 1, 1, 0), (1, 0.95, 0.85, 0.75), (1, 1, 1, 0)])
            F.cv.save(); F.cv.clipPath(outer, skia.ClipOp.kIntersect, True)
            F.cv.drawPaint(F.paint(shader=sh, blend='plus')); F.cv.restore()
        if crack > 0:
            g = min(1.0, crack * 1.5)
            for cr in self.cracks:
                m = max(2, int(len(cr) * g)); pts = np.array([cx, cy]) + cr[:m] * [w, w]
                F.path(poly(pts, closed=False), color=(0.0, 0.0, 0.0), alpha=0.95, stroke=max(1.2, w * 0.004))
                F.path(poly(pts, closed=False), color=tuple(np.asarray(light_color) * 1.6), alpha=0.5 * g, stroke=max(0.6, w * 0.0015), blend='plus')
        F.cv.restore()
        fr = over(fr, F, alpha)
        if crack > 0.5:                                         # 碎片剥落
            G = surf(); g = (crack - 0.5) * 2
            for (px, py, sz, v, d) in self.chips:
                age = max(0, g - (1 - d) * 0.5)
                if age <= 0: continue
                p = np.array([cx + px * w, cy + py * h]) + np.array([v * 40 * age, 600 * age * age])
                q = sz * w
                pp = poly([p + [-q, -q * 0.5], p + [q * 0.6, -q], p + [q, q * 0.5], p + [-q * 0.4, q * 0.8]])
                pp.transform(skia.Matrix.RotateDeg(float(v * age * 200), skia.Point(*map(float, p))))
                fillp(G, pp, color=tuple(GOLD * (0.6 + 0.4 * abs(math.sin(v * 3 + age * 9)))))
            fr = over(fr, G, alpha)
        return fr, {}
