"""谁定正邪 MV — pure-code renderer.
Usage: python3 render.py T0 T1 out.mp4 [--fps 30]
Renders the timeline between T0 and T1 seconds (song time) and muxes the matching audio.
"""
import sys, os, math, json, random, subprocess
import numpy as np, cv2
from fx import *
from proc import *

FPS = 30
ROOT = os.path.dirname(os.path.abspath(__file__))
AN = np.load(os.path.join(ROOT, 'analysis.npz'))
A_T, A_RMS, A_LOW, A_ON = AN['t'], AN['rms'], AN['low'], AN['onset']
BEATS = AN['beats']

def env(arr, t, smooth=0.0):
    return float(np.interp(t, A_T, arr))

def ease(x): x = min(max(x, 0), 1); return x * x * (3 - 2 * x)
def eout(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def win(t, a, b, fi=0.4, fo=0.4):
    return ease((t - a) / fi) * (1 - ease((t - (b - fo)) / fo))

# ---------------------------------------------------------------- credits
CREDITS = [  # (start, end, role, names, pos) — times land on bar downbeats (~129 BPM)
    # 2026-11-09 05:52 用户：后期总监跟出品人；片名区只留主副标题，所有署名移到片名之前
    (0.45, 2.10, '出品人', '西几王传媒', (0.30, 0.36)),
    (0.60, 2.10, '后期总监', '沉溺', (0.30, 0.64)),
    (2.21, 4.00, '编剧 / 导演', '苏打', (0.30, 0.46)),
    (4.06, 5.90, '美术设计', 'Cait', (0.30, 0.36)),
    (4.21, 5.90, '音乐', '西几王', (0.30, 0.64)),
    (5.97, 7.75, 'AI画师', '沉溺　雪晴　索恩', (0.30, 0.46)),
]
SPR_HOOK = None           # scenes.py 在 SPRITE_MODE=1 时挂上 rest_sprites 合成
TITLE_HIT = 7.85          # title slam
TITLE_SHEEN = 11.52
TA_X, TDOT_X, TB_X = 0.255, 0.418, 0.61   # 主标题两段与间隔点的横向中心
TITLE_OUT = 13.35
INTRO_END = 15.21

# ---------------------------------------------------------------- shan-shui night world (precomputed)
class ShanShui:
    def __init__(self, seed=2, moon=True):
        self.M = 1.18
        self.w, self.h = int(W * self.M), int(H * self.M)
        w, h = self.w, self.h
        y = np.linspace(0, 1, h)[:, None, None]
        sky = (np.array([0.018, 0.02, 0.028]) * (1 - y) + np.array([0.09, 0.09, 0.10]) * y).astype(np.float32) * np.ones((1, w, 1), np.float32)
        c = np.clip((fbm2(h, w, seed, base=3, octaves=7) - 0.45) * 2.2, 0, 1)
        self.sky = sky + c[..., None] * 0.09
        dawn = (np.array([0.30, 0.31, 0.34]) * (1 - y) ** 1.5 + np.array([0.95, 0.72, 0.45]) * np.exp(-((y - 0.55) / 0.22) ** 2) + 0.25 * y).astype(np.float32) * np.ones((1, w, 1), np.float32)
        self.sky_dawn = dawn + c[..., None] * 0.08
        self.has_moon = moon
        self.moon = (0.78 * w, 0.27 * h, 70 * self.M)
        mx, my, mr = self.moon
        self.mtex = fbm2(h, w, 99, base=40, octaves=4) * 0.6 + fbm2(h, w, 98, base=90, octaves=3) * 0.4 - 0.5
        self.mglow = radial_glow(h, w, mx, my, 170 * self.M)[..., None]
        self.mdisc = disc(h, w, mx, my, mr)[..., None]
        self.layers = []
        tones = [0.24, 0.16, 0.10, 0.05, 0.012]
        for i, tn in enumerate(tones):
            base = h * (0.50 + i * 0.12)
            a = mountain_layer(w, h, base, h * (0.38 - i * 0.04), seed * 10 + i, peaks=2 + i, sharp=2.0)
            m = mist(h, w * 2, seed * 20 + i, scale=2)
            band = np.exp(-((np.arange(h) - (base + 10)) / 55.0) ** 2)[:, None]
            self.layers.append((a, tn, m * band * (0.16 - i * 0.025), 0.15 + i * 0.22))
    def render(self, cam_t, zoom, glow_amt=0.5, dawn=0.0):
        w, h = self.w, self.h
        fr = self.sky if dawn <= 0 else self.sky * (1 - dawn) + self.sky_dawn * dawn
        fr = fr.copy()
        if self.has_moon:
            col = np.array([0.85, 0.12, 0.08], np.float32) * (1 - dawn) + np.array([1.0, 0.80, 0.5], np.float32) * dawn
            fr += self.mglow * col * (glow_amt + 0.6 * dawn)
            fr = fr * (1 - self.mdisc) + self.mdisc * col * (0.95 + 0.25 * self.mtex[..., None] * (1 - dawn) + 0.3 * dawn)
        for li, (a, tn, m, par) in enumerate(self.layers):
            sx = -cam_t * 40 * par  # parallax drift
            M = np.float32([[1, 0, sx], [0, 1, 0]])
            aa = cv2.warpAffine(a, M, (w, h), borderMode=cv2.BORDER_REFLECT)
            tone = tn * (1 + dawn * (1.4 - li * 0.25))
            fr = fr * (1 - aa[..., None]) + tone * aa[..., None]
            off = int((cam_t * 25 * (0.5 + par)) % w)
            fr += m[:, off:off + w][..., None] * np.array([0.95, 0.95, 1.0], np.float32) * (1 + 1.5 * dawn)
        z = zoom / self.M
        cw, ch = w * z, h * z
        M = np.float32([[W / cw, 0, -(w - cw) / 2 * W / cw], [0, H / ch, -(h - ch) / 2 * H / ch]])
        return cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR)

# ---------------------------------------------------------------- ink bloom mask (cached noise)
class InkWipe:
    def __init__(self, seed=0, cx=0.5, cy=0.5):
        h, w = H // 4, W // 4
        n = fbm2(h, w, seed, base=4, octaves=6)
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.sqrt(((x / w - cx) * 1.7) ** 2 + (y / h - cy) ** 2)
        self.f = d + (n - 0.5) * 0.55
    def mask(self, prog):
        m = np.clip((prog * 1.5 - self.f) * 7, 0, 1)
        return cv2.resize(m, (W, H))[..., None]

# ---------------------------------------------------------------- credit block
def credit_block(fr, t, a, b, role, names, pos=(0.30, 0.46)):
    if t < a - 0.05 or t > b + 0.05: return fr
    p_in = (t - a) / 0.55
    out = ease((t - (b - 0.45)) / 0.45)
    # role: letterspaced serif, fades in
    n_r = len(role)
    rev_r = [eout(p_in * 1.6 - k * 0.05) * (1 - out) for k in range(n_r)]
    rgb, al = text_layer(role, F_SERIF, 30, rev_r, spacing=0.55, pos=(pos[0], pos[1] - 0.085), color=(0.66, 0.63, 0.58), scale_in=0.0, blur_in=3)
    fr = comp_text(fr, rgb, al, shadow=0.5)
    # names: brush chars ink in one by one, exit drifts/blur
    n = len(names)
    rev = []
    for k in range(n):
        r = eout((p_in - 0.15 - k * 0.07) * 1.3)
        rev.append(r * (1 - out))
    size = 96 if n <= 5 else 78
    blur_extra = out * 8
    rgb, al = text_layer(names, F_BRUSH, size, rev, spacing=0.08, pos=(pos[0], pos[1] + 0.02 - out * 0.02), scale_in=0.18, blur_in=7 + blur_extra)
    fr = comp_text(fr, rgb, al, shadow=0.7)
    # thin red rule under role
    la = ease(p_in * 1.2) * (1 - out)
    if la > 0:
        x0 = int(W * pos[0] - 60 * la); x1 = int(W * pos[0] + 60 * la); yy = int(H * (pos[1] - 0.045))
        cv2.line(fr, (x0, yy), (x1, yy), (0.62 * la, 0.06 * la, 0.05 * la), 2, cv2.LINE_AA)
    return fr

# ---------------------------------------------------------------- the intro scene
class Intro:
    def __init__(self):
        self.ss = ShanShui(2)
        self.wipe = InkWipe(3, 0.5, 0.48)
        self.emb = Embers(110, 1)
        self.burst = Embers(260, 9)
        self.burst.v *= 2.2
    def frame(self, t, dt):
        low = env(A_LOW, t); rms = env(A_RMS, t)
        # camera: slow push, a kick on the title hit
        hit = max(0.0, 1 - (t - TITLE_HIT) / 0.6) if t >= TITLE_HIT else 0.0
        zoom = 1.0 + 0.06 * (t / INTRO_END) + 0.02 * hit
        fr = self.ss.render(t, zoom, glow_amt=0.42 + 0.25 * low)
        if t >= TITLE_HIT:
            sh = hit ** 2 * 14
            M = np.float32([[1, 0, random.uniform(-sh, sh)], [0, 1, random.uniform(-sh, sh)]])
            fr = cv2.warpAffine(fr, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        fr = self.emb.draw(fr, t, dt, 0.55 + 0.4 * low, energy=low)
        if SPR_HOOK: fr = SPR_HOOK(fr, t)   # SPRITE_MODE：人物精灵在署名/片名之下（units/rest_sprites.py）
        # credits
        for (a, b, role, names, pos) in CREDITS:
            fr = credit_block(fr, t, a, b, role, names, pos=pos)
        # title
        if t >= TITLE_HIT - 0.12:
            fr = self.title(fr, t, dt, hit)
        # opening ink bloom from black
        if t < 2.0:
            m = self.wipe.mask(eout((t - 0.30) / 1.5))
            fr = fr * m
        return fr, (2 if hit > 0.4 else 0)
    def title(self, fr, t, dt, hit):
        # slash streak precedes the title by 4 frames
        sp = (t - (TITLE_HIT - 0.12)) / 0.22
        fr = slash(fr, sp, angle=-9, cy=0.43, width=1.4)
        if t < TITLE_HIT: return fr
        k = t - TITLE_HIT
        out = ease((t - TITLE_OUT) / 1.4)
        if hit > 0.85: fr = fr + (hit - 0.85) / 0.15 * 0.55  # flash
        fr = self.burst.draw(fr, t, dt, 1.4 * max(0, 1 - k / 3.5), energy=hit * 2)
        # 主标题「鬼屠 · 第二季」（书法，两段 + 朱红间隔点），副标题「主题曲《谁定正邪》」
        y0 = 0.43 - 0.01 * eout(k / 6)
        revA = [eout((k - i * 0.035) / 0.28) * (1 - out) for i in range(2)]
        revB = [eout((k - (i + 2) * 0.035) / 0.28) * (1 - out) for i in range(3)]
        rgbA, alA = text_layer('鬼屠', F_BRUSH, 210, revA, spacing=0.10, pos=(TA_X, y0), scale_in=0.45, blur_in=10 + out * 14)
        rgbB, alB = text_layer('第二季', F_BRUSH, 210, revB, spacing=0.10, pos=(TB_X, y0), scale_in=0.45, blur_in=10 + out * 14)
        fr = comp_text(fr, rgbA, alA, shadow=0.75, glowamt=0.25 * hit)
        fr = comp_text(fr, rgbB, alB, shadow=0.75, glowamt=0.25 * hit)
        al = np.maximum(alA, alB)
        da = eout((k - 0.06) / 0.25) * (1 - out)
        if da > 0:
            dot = np.zeros((H, W), np.float32)
            cv2.circle(dot, (int(W * TDOT_X), int(H * (y0 + 0.005))), 11, 1.0, -1, cv2.LINE_AA)
            dot = cv2.GaussianBlur(dot, (0, 0), 1.0)[..., None] * da
            fr = fr * (1 - dot) + dot * np.array([0.72, 0.08, 0.06], np.float32)
        # sheen pass across the title at the second hit
        if TITLE_SHEEN <= t < TITLE_SHEEN + 0.6:
            q = (t - TITLE_SHEEN) / 0.6
            x = np.linspace(0, 1, W)[None, :]
            band = np.exp(-((x - (0.15 + q * 0.7)) / 0.03) ** 2)
            fr += (al * band)[..., None] * 0.9
        sub_r = eout((k - 0.5) / 0.6) * (1 - out)
        sub = '主题曲《谁定正邪》'
        rgb, al = text_layer(sub, F_SERIF, 36, [sub_r] * len(sub), spacing=0.35, pos=(0.47, 0.60), color=(0.80, 0.77, 0.72), scale_in=0, blur_in=4)
        fr = comp_text(fr, rgb, al, shadow=0.5)
        # seal stamps on the next beat
        ks = t - (TITLE_HIT + 0.46)
        if ks > 0:
            a = min(1, ks / 0.06) * (1 - out)
            fr = seal(fr, "鬼屠", x=0.815, y=0.33, size=40, alpha=0.92 * a)
        return fr

# ---------------------------------------------------------------- main
def render(t0, t1, outp, fps=FPS):
    random.seed(int(t0 * 1000)); np.random.seed(int(t0 * 1000))
    intro = Intro()
    # warm up particles so they are already in flight
    for _ in range(60): intro.emb.p += intro.emb.v * 0.03
    tmp = outp + '.video.mp4'
    p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-tune', 'film', tmp], stdin=subprocess.PIPE)
    n = int(round((t1 - t0) * fps)); dt = 1 / fps
    for i in range(n):
        t = t0 + i * dt
        fr, ca = intro.frame(t, dt)
        fr = finish(fr, grain_amt=0.045, vig=0.5, ca=ca)
        p.stdin.write(to8(fr).tobytes())
        if i % 30 == 0: print(f'{t:.2f}s', flush=True)
    p.stdin.close(); p.wait()
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', tmp, '-ss', str(t0), '-t', str(t1 - t0), '-i', os.path.join(ROOT, 'song.mp3'),
                    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-shortest', '-movflags', '+faststart', outp], check=True)
    os.remove(tmp)

if __name__ == '__main__':
    render(float(sys.argv[1]), float(sys.argv[2]), sys.argv[3])
