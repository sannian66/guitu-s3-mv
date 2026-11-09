"""Procedural generators: everything drawn from math, no image assets."""
import numpy as np, cv2, math
W, H = 1920, 1080

def fbm2(h, w, seed, base=4, octaves=6, persist=0.55):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        gh, gw = max(2, int(base * 2 ** o * h / max(h, w)) + 2), max(2, int(base * 2 ** o * w / max(h, w)) + 2)
        g = rng.random((gh, gw)).astype(np.float32)
        out += cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC) * amp
        tot += amp; amp *= persist
    out /= tot
    out = (out - out.min()) / (out.max() - out.min() + 1e-6)
    return out

def fbm1(n, seed, base=3, octaves=7, persist=0.55):
    rng = np.random.default_rng(seed)
    x = np.zeros(n, np.float32); amp = 1; tot = 0
    for o in range(octaves):
        k = int(base * 2 ** o) + 2
        g = rng.random(k).astype(np.float32)
        xs = np.linspace(0, k - 1, n)
        x += np.interp(xs, np.arange(k), g) * amp if o < 2 else cv2.resize(g[None], (n, 1), interpolation=cv2.INTER_CUBIC)[0] * amp
        tot += amp; amp *= persist
    return x / tot

PAPER = np.array([0.90, 0.87, 0.80], np.float32)
INK = np.array([0.05, 0.05, 0.06], np.float32)
RED = np.array([0.72, 0.06, 0.05], np.float32)

def paper(h=H, w=W, seed=11, tone=PAPER):
    n = fbm2(h, w, seed, base=6, octaves=7)
    fib = cv2.GaussianBlur(np.random.default_rng(seed).random((h, w)).astype(np.float32), (0, 0), 0.6)
    t = 0.92 + 0.06 * n + 0.03 * (fib - 0.5)
    return (tone[None, None] * t[..., None]).astype(np.float32)

def mountain_layer(w, h, base_y, amp, seed, peaks=3, sharp=1.6):
    """returns alpha (h,w): shan-shui ink mountain; dark ridge, misty foot, cun texture"""
    r = fbm1(w, seed, base=peaks, octaves=8)
    r = (r - r.min()) / (r.max() - r.min())
    r = r ** sharp
    ridge = base_y - r * amp  # y of ridge per x
    y = np.arange(h, dtype=np.float32)[:, None]
    d = y - ridge[None]  # depth below ridge
    inside = np.clip(d / 2.0, 0, 1)
    # ink density: strong near ridge, fading with depth (mist)
    dens = np.exp(-np.clip(d, 0, None) / (amp * 0.55 + 40))
    tex = fbm2(h, w, seed + 1, base=10, octaves=6)
    strokes = cv2.resize(fbm2(h // 6, w, seed + 2, base=40, octaves=4), (w, h))  # vertical-ish cun strokes
    a = inside * (0.35 + 0.65 * dens) * (0.75 + 0.35 * tex) * (0.85 + 0.3 * strokes)
    # crisp dry-brush ridge line
    edge = np.exp(-np.abs(d) / 2.5) * (0.6 + 0.6 * tex)
    a = np.clip(a + edge * 0.6, 0, 1)
    return a.astype(np.float32)

def mist(h, w, seed, scale=3):
    m = fbm2(h, w, seed, base=scale, octaves=5)
    return np.clip((m - 0.35) * 1.8, 0, 1).astype(np.float32)

def disc(h, w, cx, cy, r, soft=2.0):
    y, x = np.ogrid[:h, :w]
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    return np.clip((r - d) / soft + 0.5, 0, 1).astype(np.float32)

def radial_glow(h, w, cx, cy, r):
    y, x = np.ogrid[:h, :w]
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
    return (1 / (1 + d * d * 4)).astype(np.float32)

def army(w, h, rows=9, seed=5, horizon=0.52, front=0.92, torch=True):
    """silhouette phalanx: returns alpha (h,w) and torches list [(x,y,size)]"""
    rng = np.random.default_rng(seed)
    A = np.zeros((h, w), np.float32); torches = []
    layers = []
    for i in range(rows):
        t = i / (rows - 1)  # 0 far .. 1 near
        y0 = h * (horizon + (front - horizon) * t ** 1.6)
        s = 0.35 + 0.9 * t ** 1.4  # scale
        L = np.zeros((h, w), np.float32)
        step = 34 * s
        x = -rng.uniform(0, step)
        while x < w + step:
            xx = x + rng.normal(0, step * 0.12)
            bh = 120 * s; bw = 30 * s
            # body (shield-ish trapezoid)
            pts = np.array([[xx - bw * 0.55, y0], [xx + bw * 0.55, y0], [xx + bw * 0.45, y0 - bh * 0.62], [xx - bw * 0.45, y0 - bh * 0.62]], np.int32)
            cv2.fillPoly(L, [pts], 1.0, cv2.LINE_AA)
            # helmet with crest
            cv2.ellipse(L, (int(xx), int(y0 - bh * 0.72)), (max(1, int(bw * 0.3)), max(1, int(bw * 0.36))), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
            cv2.line(L, (int(xx), int(y0 - bh * 0.8)), (int(xx), int(y0 - bh * 0.95)), 1.0, max(1, int(2 * s)), cv2.LINE_AA)
            # spear
            sx = xx + bw * 0.6
            lean = rng.normal(0, 0.05)
            top = y0 - bh * (1.9 + rng.uniform(0, 0.25))
            cv2.line(L, (int(sx), int(y0 - bh * 0.1)), (int(sx + lean * bh), int(top)), 1.0, max(1, int(2.2 * s)), cv2.LINE_AA)
            tip = np.array([[sx + lean * bh - 4 * s, top + 8 * s], [sx + lean * bh + 4 * s, top + 8 * s], [sx + lean * bh, top - 16 * s]], np.int32)
            cv2.fillPoly(L, [tip], 1.0, cv2.LINE_AA)
            if rng.random() < 0.05:  # banner
                cv2.fillPoly(L, [np.array([[sx, top + 10 * s], [sx + 40 * s, top + 18 * s], [sx + 30 * s, top + 50 * s], [sx, top + 60 * s]], np.int32)], 1.0, cv2.LINE_AA)
            if torch and rng.random() < 0.06:
                torches.append((sx + lean * bh * 0.7, top + bh * 0.5, s, t))
            x += step
        layers.append((t, L))
    return layers, torches

def balance(h, w, cx, cy, tilt, span=520, chain=330, pan_r=150, lw=6):
    """scales of judgement silhouette. tilt radians. returns alpha"""
    A = np.zeros((h, w), np.float32)
    # post and hook
    cv2.line(A, (cx, 0), (cx, cy), 1, lw, cv2.LINE_AA)
    cv2.circle(A, (cx, cy), lw * 3, 1, -1, cv2.LINE_AA)
    ex, ey = math.cos(tilt) * span, math.sin(tilt) * span
    p1 = (int(cx - ex), int(cy - ey)); p2 = (int(cx + ex), int(cy + ey))
    # beam tapered
    nx, ny = -math.sin(tilt), math.cos(tilt)
    beam = np.array([[cx - ex + nx * 3, cy - ey + ny * 3], [cx + nx * 12, cy + ny * 12], [cx + ex + nx * 3, cy + ey + ny * 3],
                     [cx + ex - nx * 3, cy + ey - ny * 3], [cx - nx * 12, cy - ny * 12], [cx - ex - nx * 3, cy - ey - ny * 3]], np.int32)
    cv2.fillPoly(A, [beam], 1, cv2.LINE_AA)
    for (px, py) in (p1, p2):
        cv2.circle(A, (px, py), 9, 1, -1, cv2.LINE_AA)
        by = py + chain
        for dx in (-pan_r * 0.85, 0, pan_r * 0.85):
            cv2.line(A, (px, py), (int(px + dx), by), 1, 2, cv2.LINE_AA)
        cv2.ellipse(A, (px, by), (pan_r, int(pan_r * 0.32)), 0, 0, 180, 1, -1, cv2.LINE_AA)
        cv2.ellipse(A, (px, by), (pan_r, 8), 0, 0, 360, 1, -1, cv2.LINE_AA)
    return A, p1, p2, chain

def dao(h, w, cx, cy, ang, length=1300, width=70):
    """single-edged sabre: returns blade alpha, edge-highlight alpha, hilt alpha"""
    B = np.zeros((h, w), np.float32); E = np.zeros_like(B); Hh = np.zeros_like(B)
    ca, sa = math.cos(ang), math.sin(ang)
    def P(u, v):  # u along blade, v across (spine side +)
        return [cx + ca * u - sa * v, cy + sa * u + ca * v]
    n = 40; spine = []; edge = []
    for i in range(n + 1):
        u = length * i / n
        curve = 0.06 * length * (i / n) ** 2  # slight curve
        wd = width * (1 - 0.15 * i / n)
        if i > n * 0.85:  # clipped tip
            k = (i - n * 0.85) / (n * 0.15)
            spine.append(P(u, -curve + wd * 0.45 - k * wd * 0.9))
        else:
            spine.append(P(u, -curve + wd * 0.45))
        edge.append(P(u, -curve - wd * 0.55 + (wd * 0.4 * ((i / n - 0.85) / 0.15) ** 2 if i > n * 0.85 else 0)))
    poly = np.array(spine + edge[::-1], np.int32)
    cv2.fillPoly(B, [poly], 1, cv2.LINE_AA)
    cv2.polylines(E, [np.array(edge, np.int32)], False, 1, 3, cv2.LINE_AA)
    # guard + grip
    g = np.array([P(-12, width * 1.0), P(12, width * 1.0), P(12, -width * 1.1), P(-12, -width * 1.1)], np.int32)
    cv2.fillPoly(Hh, [g], 1, cv2.LINE_AA)
    grip = np.array([P(-12, width * 0.3), P(-330, width * 0.32), P(-330, -width * 0.32), P(-12, -width * 0.3)], np.int32)
    cv2.fillPoly(Hh, [grip], 1, cv2.LINE_AA)
    return B, E, Hh

def bricks(h, w, seed=9, bw=140, bh=56):
    rng = np.random.default_rng(seed)
    T = np.zeros((h, w), np.float32)
    n = fbm2(h, w, seed, base=12, octaves=6)
    for r in range(h // bh + 2):
        off = (r % 2) * bw / 2
        for c in range(-1, w // bw + 2):
            x0 = int(c * bw + off); y0 = r * bh
            v = rng.uniform(0.12, 0.3)
            cv2.rectangle(T, (x0 + 3, y0 + 3), (x0 + bw - 3, y0 + bh - 3), v, -1)
    T = T * (0.6 + 0.8 * n)
    return T

def ink_bleed(mask, prog, seed=0, rough=10):
    """organic reveal of a mask: grows from noise seeds, ragged edges"""
    h, w = mask.shape
    n = fbm2(h // 4, w // 4, seed, base=5, octaves=5)
    n = cv2.resize(n, (w, h))
    dist = cv2.distanceTransform((mask > 0.5).astype(np.uint8), cv2.DIST_L2, 3)
    dn = dist / (dist.max() + 1e-6)
    f = (1 - dn) * 0.5 + n * 0.5
    th = prog * 1.25
    rev = np.clip((th - f) * 12, 0, 1)
    return mask * rev

def hero(h, w, fx, fy, s=1.0, sword_ang=0.35, wind=0.0, seed=1):
    """back-view swordsman silhouette. fx,fy feet center. returns body alpha, sash alpha, blade alpha"""
    B = np.zeros((h, w), np.float32); S = np.zeros_like(B); K = np.zeros_like(B)
    def p(x, y): return [int(fx + x * s), int(fy + y * s)]
    # legs / robe hem flaring with wind
    robe = np.array([p(-70 - wind * 40, 0), p(-30, -10), p(0, 0), p(35, -8), p(80 + wind * 60, 4), p(55 + wind * 50, -120),
                     p(48, -250), p(62, -330), p(40, -380), p(-40, -380), p(-60, -330), p(-48, -250), p(-58, -130)], np.int32)
    cv2.fillPoly(B, [robe], 1, cv2.LINE_AA)
    # shoulders/arms
    cv2.fillPoly(B, [np.array([p(-62, -330), p(-95, -250), p(-85, -180), p(-60, -200), p(-55, -300)], np.int32)], 1, cv2.LINE_AA)
    cv2.fillPoly(B, [np.array([p(60, -330), p(100, -260), p(130, -200), p(112, -186), p(80, -240), p(52, -290)], np.int32)], 1, cv2.LINE_AA)
    # neck/head/topknot
    cv2.ellipse(B, tuple(p(0, -420)), (int(34 * s), int(42 * s)), 0, 0, 360, 1, -1, cv2.LINE_AA)
    cv2.fillPoly(B, [np.array([p(-16, -390), p(16, -390), p(14, -370), p(-14, -370)], np.int32)], 1, cv2.LINE_AA)
    cv2.ellipse(B, tuple(p(0, -470)), (int(14 * s), int(14 * s)), 0, 0, 360, 1, -1, cv2.LINE_AA)
    rng = np.random.default_rng(seed)
    for k in range(0):  # hair strands blowing
        pts = []
        for j in range(8):
            t = j / 7
            pts.append(p(-5 + k * 2 - (60 + 40 * wind) * t + rng.normal(0, 2), -470 + 70 * t + 20 * math.sin(t * 3 + k)))
        cv2.polylines(B, [np.array(pts, np.int32)], False, 1, max(1, int(3 * s)), cv2.LINE_AA)
    # sash tails
    for k in range(2):
        prev = None
        for j in range(24):
            t = j / 23
            q = p(-45 - (170 + 120 * wind) * t, -244 + k * 10 + 34 * math.sin(t * 5 + k * 1.3) * t)
            if prev is not None:
                cv2.line(S, tuple(prev), tuple(q), 1, max(1, int(9 * s * (1 - t) * (1 - 0.4 * k) + 1)), cv2.LINE_AA)
            prev = q
    cv2.fillPoly(S, [np.array([p(-54, -252), p(54, -250), p(55, -240), p(-55, -238)], np.int32)], 1, cv2.LINE_AA)
    S *= (1 - 0) ; S = np.clip(S - B * 0, 0, 1)
    # dao held low right
    hx, hy = p(124, -192)
    L = 520 * s
    ex, ey = hx + math.cos(sword_ang) * L, hy + math.sin(sword_ang) * L
    poly = np.array([[hx, hy - 4 * s], [ex, ey - 2 * s], [ex - 30 * s * math.cos(sword_ang), ey + 12 * s], [hx, hy + 9 * s]], np.int32)
    cv2.fillPoly(K, [poly], 1, cv2.LINE_AA)
    return B, S, K
