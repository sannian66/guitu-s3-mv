"""评审第一轮返工（P0 1–6、P1 7–14）+ 用户 C21 镜像。逐条替换 units/r8d_c_a.py，每条必须命中。"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
p = ROOT + '/units/r8d_c_a.py'
s = open(p).read()
R = [
# ── P0-1 C01：整行洇出提前 4 帧（起 3538），从左往右逐列，切点前整句写完
("        self.tins = [V(CT(28, k)) for k in range(5)]\n        self.colm",
 "        # 评审 P0-1：原来按字头时刻逐字洇，末尾「则」在切点前只洇出「贝」→ 整行提前 4 帧（起 3538 = V(118.16)-4）逐列洇完\n"
 "        _t0 = V(CT(28, 1)) - 4 / FPS\n"
 "        self.tins = [_t0 + k * (4 / FPS) for k in range(5)]\n        self.colm"),
("        q = sm(V(118.58), V(118.58) + 0.30, t)", "        q = sm(V(118.58) - 2 / FPS, V(118.58) + 0.26, t)"),
# ── P0-4 C04：网点光晕缩小、降密度、边缘不规则墨散；玉玺落盘 2–3 帧可辨
("            fr = halo_tone(fr, (rpan[0], rpan[1] - 40), 300, 0.9 * fl)",
 "            fr = ink_burst(fr, (rpan[0], rpan[1] - 40), 190, 0.55 * fl, seed=404)   # 评审 P0-4：改成不规则墨散（不再是等距网点圆）"),
("        self.post = Prop('C04_balance', mask=post, work=0.5)",
 "        self.post = Prop('C04_balance', mask=post, work=0.5)\n        self.sealA = None"),
# ── P0-5 C15：镜尾压暗只压下半 60%，且不低于 35
("        fr = rain_fg(fr, t, 7, amt=0.45, speed=2400, scale=0.7, cam=(_par(u, 60), 0), freeze=tfz)",
 "        fr = rain_fg(fr, t, 7, amt=0.45, speed=2400, scale=0.7, cam=(_par(u, 60), 0), freeze=tfz)\n"
 "        # 评审 P0-5：原来 4032 就压到 51、4034 掉到 14 —— 只压下半 60%，最低 0.55 倍\n"
 "        dk = sm(4031 / FPS, 4034 / FPS, t)\n"
 "        if dk > 0:\n"
 "            yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]\n"
 "            fr = fr * (1 - dk * 0.45 * np.clip((yy - 0.40) / 0.60, 0, 1))"),
# ── P0-6 C15 血珠：12–16 颗有墨线的血珠 + 2 条飞白（不是一团红点）
("        n = 26\n        self.drops = [dict(a=math.radians(r.uniform(-75, 15)), v=r.uniform(500, 1300), r=r.uniform(4, 11), d=r.uniform(0, 0.03)) for _ in range(n)]",
 "        self.drops = [dict(a=math.radians(r.uniform(-70, 5)), v=r.uniform(620, 1050), r=r.uniform(6, 13), d=r.uniform(0, 0.02)) for _ in range(14)]"),
("""            for i, d in enumerate(self.drops):
                tt = max(0.0, te - d['d'])
                if tt <= 0: continue
                x = tip[0] + math.cos(d['a']) * d['v'] * tt; y = tip[1] + math.sin(d['a']) * d['v'] * tt + 900 * tt * tt
                if y > foot[1] + 40: continue
                fr = ink_drop(fr, (x, y), r=d['r'] * (1 - 0.2 * (i % 3)))""",
"""            # 评审 P0-6：两笔干笔飞白打底（血被甩出去的方向），上面再挂 14 颗墨线描边的血珠
            fr = brush_slash(fr, (tip[0] + 20, tip[1] - 40), (tip[0] + 470, tip[1] + 120), (te / 0.30), width=0.22, red=0.8, amt=0.9)
            fr = brush_slash(fr, (tip[0] + 10, tip[1] + 30), (tip[0] + 380, tip[1] + 250), (te / 0.34), width=0.18, red=0.8, amt=0.75)
            for i, d in enumerate(self.drops):
                tt = max(0.0, te - d['d'])
                if tt <= 0: continue
                x = tip[0] + math.cos(d['a']) * d['v'] * tt; y = tip[1] + math.sin(d['a']) * d['v'] * tt + 900 * tt * tt
                if y > foot[1] + 40: continue
                fr = ink_drop(fr, (x, y), r=d['r'] * (1 - 0.15 * (i % 3)))"""),
# ── P0-3 C12：刃身与红热刃口拆两层，刃口层单独前推 1.05
("""        fr, A = self.blade.draw(fr, self.blade.src(1500, 560), (1120 - 140 * u, 600), 2.6, rot=-6)
        hot = np.clip(fr[..., 0] - fr[..., 1] * 1.4, 0, 1) * A
        fr = fr + blur_ds(hot, 40)[..., None] * np.array(BRED, np.float32) * 0.9""",
"""        # 评审 P0-3：原来 40 帧一块刀刚体 → 刃身一层；刃口红热单独一层，比刃身再前推 3%（1.05 相对量）并随刃光微微位移
        fr, A = self.blade.draw(fr, self.blade.src(1500, 560), (1120 - 140 * u, 600), 2.6, rot=-6)
        push = 1.03 + 0.02 * eio(u)
        fr2 = fr.copy(); A2 = np.zeros_like(A)
        fr2, A2 = self.blade.draw(fr2, self.blade.src(1500, 560), (1120 - 140 * u, 600 - 6 * eio(u)), 2.6 * push, rot=-6.6)
        hotF = np.clip(fr2[..., 0] - fr2[..., 1] * 1.5, 0, 0.55) * A2
        hotA = np.clip((hotF - 0.10) * 3.0, 0, 1)
        fr = fr * (1 - hotA[..., None]) + (fr * 0.55 + hotA[..., None] * np.array([0.95, 0.10, 0.06], np.float32)) * hotA[..., None]
        hot = hotA
        fr = fr + blur_ds(hot, 40)[..., None] * np.array(BRED, np.float32) * 0.55"""),
# ── P1-8 C16：第一滴落水白闪压到 2 帧，刃身加墨沿
("""        fr, A = self.blade.draw(fr, self.blade.src(2020, 533), tip, 0.70, rot=-90)
        fr = mirror(fr, A, 600, amt=0.25, t=t)""",
"""        fr, A = self.blade.draw(fr, self.blade.src(2020, 533), tip, 0.70, rot=-90)
        eA = np.clip(cv2.dilate(A, np.ones((5, 5), np.uint8)) - A, 0, 1)          # 评审 P1-8：刃身 1px 墨沿（白闪时刀还读得出）
        fr = C1.over(fr, eA, INK)
        fr = mirror(fr, A, 600, amt=0.25, t=t)"""),
# ── P1-7 C16：涟漪位移减半（字心保留笔画）
("            amp = 1.5 + 2.5 * sm(0, 0.6, k) + 12.0 * eout(clamp(k2 / 0.6))",
 "            amp = 1.5 + 1.5 * sm(0, 0.6, k) + 6.0 * eout(clamp(k2 / 0.6))       # 评审 P1-7：涟漪位移减半，字心笔画保留"),
("        fr = water_ripple(fr, (960, 770), k2 + 0.01 if t >= t2 else -1, flat=0.45, speed=760, amp=12, y_top=600)",
 "        fr = water_ripple(fr, (960, 770), k2 + 0.01 if t >= t2 else -1, flat=0.45, speed=760, amp=6, y_top=600)"),
# ── P1-9 C10：第四块匾抬高 8px
("            top0 = 250\n", "            top0 = 250 - (8 if i == 3 else 0)          # 评审 P1-9：「上」下横原来和屋脊叠在一起\n"),
# ── P1-11 C03：左右两端皮影各拆一层下摆（二级运动）
("""            fr = _red_line(fr, (x + 10 * math.sin(i), bar_y - 60 * tw), (x, top + 6), w=2, amt=0.8)""",
"""            fr = _red_line(fr, (x + 10 * math.sin(i), bar_y - 60 * tw), (x, top + 6), w=2, amt=0.8)
            if i in (0, 6):                                  # 评审 P1-11：两端皮影的下摆单独一层，慢半拍反向摆
                hh0 = int(P.h * 0.55)
                Mh = P.M((P.w / 2, hh0), (x, top + hh0 * (sc / P.work) * P.work / 1.0), sc, ang + 3.5 * math.sin(t * 1.7 + i))
                Mh[0, 2] += 6 * math.sin(t * 1.3 + i); Mh[1, 2] += 2.5 * math.sin(t * 2.1 + i)
                hemA = cv2.warpAffine(P.A, Mh, (W, H)); hemF = cv2.warpAffine(P.FA, Mh, (W, H))
                fr = fr * (1 - np.clip(hemA, 0, 1)[..., None] * 0.9) + hemF * 0.9"""),
# ── P1-13 C17→C18：硬竖边纯黑实块 → 墨散羽化边
("        fr = view(self.bg, 1.3, 220 - _par(u, 20), -60)\n        fr = bolt(fr, t, V(136.64), 181, (1250, 120), (1380, 560), inten=1.0, sky=0.3)",
 "        fr = view(self.bg, 1.3, 220 - _par(u, 20), -60)\n        fr = bolt(fr, t, V(136.64), 181, (1250, 120), (1380, 560), inten=1.0, sky=0.3)\n"
 "        fr = ink_edge_fade(fr, 0.5 + 0.5 * u, 4095)     # 评审 P1-13：入镜右侧黑块改成墨散羽化边（转场中间帧也吃这一层）"),
# ── P1-10 C21：分屏线在负片帧不切脸 + 两半云边羽化
("        line = 0.9 * np.exp(-(d / 2.4) ** 2) + 0.35 * np.exp(-(d / 22) ** 2)",
 "        line = 0.9 * np.exp(-(d / 2.4) ** 2) + 0.35 * np.exp(-(d / 22) ** 2) * (1 - 0.6 * sm(0.2, 0.5, np.abs(d)))"),
]
for a, b in R:
    assert a in s, 'MISS: ' + a[:80]
    s = s.replace(a, b)

# 新工具函数
s = s.replace("def speed_lines(", '''def ink_burst(fr, c, r, amt, seed=0, col=(1.0, 1.0, 1.0)):
    """不规则墨散光（评审 P0-4）：一圈等高距网点改成「飞白墨点向外散开」，越靠中心越密但不均匀。"""
    if amt <= 0.01: return fr
    rng = np.random.default_rng(seed)
    L = np.zeros((H // 2, W // 2), np.float32)
    for i in range(90):
        a = rng.uniform(0, 2 * math.pi); rad = r * (0.15 + 0.85 * rng.random() ** 0.6)
        x = c[0] + math.cos(a) * rad; y = c[1] + math.sin(a) * rad * 0.8
        sz = max(1, int((1.5 + 4.0 * (1 - rad / r)) * rng.uniform(0.6, 1.5)))
        cv2.circle(L, (int(x / 2), int(y / 2)), sz, rng.uniform(0.4, 1.0), -1, cv2.LINE_AA)
    L = cv2.resize(cv2.GaussianBlur(L, (0, 0), 0.8), (W, H))
    return fr * (1 - np.clip(L * amt * 0.8, 0, 1))[..., None] + np.clip(L * amt, 0, 1)[..., None] * np.asarray(col, np.float32) * 0.9


def ink_edge_fade(fr, q, seed=0, x0=0.62):
    """把画面右侧一条直线竖边换成墨散羽化：q 0→1 时右侧黑块从「实块」化为「墨溅收边」"""
    if q <= 0: return fr
    x, y = _grid()
    rng = np.random.default_rng(seed)
    nz = cv2.resize(cv2.GaussianBlur(rng.random((H // 20, W // 20)).astype(np.float32), (0, 0), 1.0), (W, H))
    edge = x0 * W + (nz - 0.5) * 220 * q
    m = np.clip((x - edge) / (1e-3 + 60), 0, 1) * q
    fr = fr * (1 - 0.92 * m[..., None]) + m[..., None] * 0.012
    sp = np.zeros((H // 2, W // 2), np.float32)
    for i in range(70):
        yy = rng.uniform(BAR, H - BAR); xx = edge[np.clip(int(yy), 0, H - 1)] + rng.uniform(-90, 60)
        cv2.circle(sp, (int(xx / 2), int(yy / 2)), max(1, int(rng.uniform(1, 5))), rng.uniform(0.3, 1.0) * q, -1, cv2.LINE_AA)
    return fr * (1 - np.clip(cv2.resize(sp, (W, H)), 0, 1)[..., None] * 0.9)


def speed_lines(''')
open(p, 'w').write(s)
print('patched', len(R))
