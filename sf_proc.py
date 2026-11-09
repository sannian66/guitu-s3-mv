import numpy as np, cv2, math, random, os
from fx import *
from proc import *
random.seed(3); np.random.seed(3)
out = '/workspace/work/mv/sfp/'; os.makedirs(out, exist_ok=True)
def save(fr, name): cv2.imwrite(out + name, to8(fr)[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92])

def night_sky(seed=1):
    y = np.linspace(0, 1, H)[:, None, None]
    sky = (np.array([0.02, 0.025, 0.035]) * (1 - y) + np.array([0.10, 0.10, 0.11]) * y).astype(np.float32) * np.ones((1, W, 1), np.float32)
    c = fbm2(H, W, seed, base=3, octaves=7)
    c = np.clip((c - 0.45) * 2.2, 0, 1)
    return sky + c[..., None] * 0.10

def shanshui_night(seed=1, moon=(0.7, 0.3), moon_col=(0.85, 0.12, 0.08)):
    fr = night_sky(seed)
    mx, my = int(moon[0] * W), int(moon[1] * H)
    fr += radial_glow(H, W, mx, my, 160)[..., None] * np.array(moon_col, np.float32) * 0.5
    fr = fr * (1 - disc(H, W, mx, my, 70)[..., None]) + disc(H, W, mx, my, 70)[..., None] * np.array(moon_col, np.float32) * 1.1
    tones = [0.24, 0.16, 0.10, 0.05, 0.012]
    for i, tn in enumerate(tones):
        base = H * (0.50 + i * 0.12)
        a = mountain_layer(W, H, base, H * (0.38 - i * 0.04), seed * 10 + i, peaks=2 + i, sharp=2.0)
        fr = fr * (1 - a[..., None]) + tn * a[..., None]
        m = mist(H, W, seed * 20 + i, scale=2)
        band = np.exp(-((np.arange(H) - (base + 10)) / 55.0) ** 2)[:, None]
        fr += (m * band * (0.22 - i * 0.03))[..., None] * np.array([0.95, 0.95, 1.0], np.float32)
    return fr.astype(np.float32)

# 1 title
fr = shanshui_night(2, moon=(0.78, 0.26))
e = Embers(70, 1)
for _ in range(30): e.p += e.v * 0.03
fr = e.draw(fr, 1, 0, 0.6)
rgb, al = text_layer('谁定正邪', F_BRUSH, 230, [1] * 4, spacing=0.12, pos=(0.36, 0.4))
fr = comp_text(fr, rgb, al, shadow=0.6)
rgb, al = text_layer('鬼屠 · 片头主题曲', F_SERIF, 34, [1] * 20, spacing=0.35, pos=(0.36, 0.56), color=(0.72, 0.7, 0.66))
fr = comp_text(fr, rgb, al, shadow=0.4)
fr = seal(fr, '鬼屠', x=0.635, y=0.33, size=40)
save(finish(fr), 'p1_title.jpg')

# 2 army
y = np.linspace(0, 1, H)[:, None, None]
hz = np.exp(-((y - 0.5) / 0.16) ** 2)
fr = (0.03 + 0.30 * hz + 0.05 * y).astype(np.float32) * np.ones((1, W, 3), np.float32) * np.array([0.95, 0.97, 1.02], np.float32)
fr += fbm2(H, W, 4, 3, 7)[..., None] * 0.07
layers, torches = army(W, H, rows=6, seed=5, horizon=0.56, front=0.8)
for t, L in layers:
    tone = 0.24 * (1 - t) ** 1.5 + 0.012
    fog = mist(H, W, int(t * 100) + 3)
    fr = fr * (1 - L[..., None]) + tone * L[..., None]
    fr += (fog * (1 - t) * 0.05)[..., None]
gl = np.zeros((H // 2, W // 2), np.float32)
for (x, yy, s, t) in torches:
    cv2.circle(gl, (int(x / 2), int(yy / 2)), max(1, int(3 * s)), 1, -1)
gl = cv2.GaussianBlur(gl, (0, 0), 2) * 1.5 + cv2.GaussianBlur(gl, (0, 0), 12) * 6
fr += cv2.resize(gl, (W, H))[..., None] * np.array([1, 0.3, 0.08], np.float32) * 0.6
fr = fr * (1 - 0.5 * np.clip((np.linspace(0,1,H)-0.8)/0.2,0,1)[:,None,None])
r = Rain()
for _ in range(3): fr = r.draw(fr, 0.016, 0.4)
Bh, Sh, Kh = hero(H, W, int(W * 0.27), int(H * 0.99), s=1.15, sword_ang=0.55, wind=0.4)
fr = fr * (1 - Bh[..., None]) + 0.008 * Bh[..., None]
fr = fr * (1 - Sh[..., None]) + RED * 0.75 * Sh[..., None]
fr = fr * (1 - Kh[..., None]) + 0.05 * Kh[..., None]
ed = cv2.GaussianBlur(Kh, (0, 0), 1.5) - cv2.GaussianBlur(Kh, (0, 0), 0.5) * 0
fr += cv2.GaussianBlur(Kh, (0,0), 6)[..., None] * 0.6 + (Kh * 0.9)[..., None] * np.array([0.9,0.92,1.0],np.float32)
rim = np.clip(Bh - cv2.GaussianBlur(Bh, (0,0), 3), 0, 1) * 1.2
fr += rim[..., None] * 0.35
fr = under_grad(fr, 0.6, 0.5)
rgb, al = text_layer('五百重甲拦不住一道寒光', F_BRUSH, 86, [1] * 9 + [0.55, 0.2], pos=(0.6, 0.82))
fr = comp_text(fr, rgb, al)
save(finish(fr, ca=1), 'p2_army.jpg')

# 3 scales on paper
fr = paper()
A, p1, p2, ch = balance(H, W, int(W * 0.42), int(H * 0.28), -0.12)
tex = fbm2(H, W, 8, 10, 6)
fr = fr * (1 - A[..., None] * (0.85 + 0.15 * tex[..., None])) + INK * A[..., None] * 0.9
# red thread ink drops in heavier pan (people) - red ink splash
sp = np.zeros((H, W), np.float32); rng = np.random.default_rng(3)
for k in range(60):
    x = p1[0] + rng.normal(0, 70); yy = p1[1] + ch - 20 - abs(rng.normal(0, 40))
    cv2.circle(sp, (int(x), int(yy)), int(abs(rng.normal(9, 6))), 1, -1, cv2.LINE_AA)
sp = np.clip(cv2.GaussianBlur(sp, (0, 0), 2) * 1.5, 0, 1) * (0.6 + 0.4 * tex)
fr = fr * (1 - sp[..., None]) + RED * sp[..., None]
# drip
for k in range(5):
    x = int(p1[0] + rng.normal(0, 60)); y0 = p1[1] + ch + 40; l = int(rng.uniform(60, 320))
    cv2.line(sp, (x, y0), (x, y0 + l), 1, int(rng.uniform(3, 7)), cv2.LINE_AA)
fr = fr * (1 - sp[..., None] * 0.9) + RED * sp[..., None] * 0.9
rgb, al = text_layer('谁在高处定对错罪状', F_BRUSH, 84, [1] * 9, vertical=True, pos=(0.84, 0.5), color=(0.06, 0.06, 0.07), red_idx=(7, 8))
fr = comp_text(fr, rgb, al, shadow=0.0)
fr = seal(fr, '鬼屠', x=0.9, y=0.72, size=36)
save(finish(fr, vig=0.45, grain_amt=0.03), 'p3_scales.jpg')

# 4 chorus wall split
B = bricks(H, W, bw=260, bh=110) * 0.55
B += fbm2(H, W, 77, 20, 6) * 0.06
fr = np.stack([B, B * 0.98, B * 1.02], -1)
ang = math.radians(-62)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
d = (xx - W * 0.5) * math.sin(ang) - (yy - H * 0.5) * math.cos(ang)
jag = cv2.resize(fbm1(H, 33)[None], (1, H))[:, 0] if False else 0
n = fbm2(H, W, 21, 30, 4) * 40
crack = np.exp(-np.abs(d + n) / 10)
gap = np.clip(1 - np.abs(d + n) / 34, 0, 1)
lit = np.exp(-np.abs(d + n) / 260)
fr = fr * (0.25 + 1.6 * lit[..., None] * np.array([1.0, 0.8, 0.55], np.float32))
fr = fr * (1 - gap[..., None])
light = (gap * 2.2 + crack * 1.5 + np.exp(-np.abs(d + n) / 90) * 0.5)[..., None] * np.array([1.0, 0.78, 0.42], np.float32)
fr += light
fr = glow(fr, 0.6, 0.8)
e = Embers(260, 4)
for _ in range(30): e.p += e.v * 0.03
fr = e.draw(fr, 1, 0, 1.3)
fr = under_grad(fr, 0.5, 0.75)
rgb, al = text_layer('血未冷 刀不放', F_BRUSH, 160, [1] * 7, spacing=0.08, pos=(0.5, 0.74), red_idx=(0,))
fr = comp_text(fr, rgb, al, glowamt=0.35)
save(finish(fr, ca=3, grain_amt=0.06), 'p4_chorus.jpg')

# 5 blade
fr = np.zeros((H, W, 3), np.float32) + 0.02
fr += fbm2(H, W, 30, 3, 6)[..., None] * 0.06
Bd, E, Hh = dao(H, W, int(W * 0.22), int(H * 0.62), math.radians(-14), length=1350, width=78)
u = np.linspace(0, 1, W)[None]
bev = np.clip(cv2.GaussianBlur(cv2.dilate(E, np.ones((19, 19), np.uint8)), (0, 0), 4) * 1.4, 0, 1) * Bd
spec = np.clip(1 - np.abs(u - 0.55) * 4, 0, 1) ** 2
steel = 0.10 + 0.08 * fbm2(H, W, 31, 30, 4)
col = steel[..., None] * (1 - bev[..., None]) + (0.35 + 0.5 * spec[..., None]) * bev[..., None]
fr = fr * (1 - Bd[..., None]) + Bd[..., None] * col * np.array([0.85, 0.88, 0.95], np.float32)
heat = bev * np.clip((u - 0.2) * 1.3, 0, 1)
fr += (heat * 0.8)[..., None] * np.array([1.0, 0.28, 0.05], np.float32)
fr += cv2.GaussianBlur(heat, (0, 0), 22)[..., None] * np.array([1.0, 0.3, 0.05], np.float32) * 1.4
fr += (E * (0.5 + 1.2 * spec))[..., None]
fr = fr * (1 - Hh[..., None]) + 0.03 * Hh[..., None]
fr += np.clip(Hh - cv2.erode(Hh, np.ones((5,5),np.uint8)),0,1)[..., None] * 0.25
e = Embers(160, 9)
for _ in range(30): e.p += e.v * 0.03
fr = e.draw(fr, 1, 0, 1.0)
fr = under_grad(fr, 0.6, 0.4)
rgb, al = text_layer('只信这柄刀还滚烫', F_BRUSH, 96, [1] * 8, pos=(0.5, 0.8), red_idx=(6, 7))
fr = comp_text(fr, rgb, al, glowamt=0.25)
save(finish(fr, ca=1), 'p5_blade.jpg')
print('ok')
