"""V04 雨夜长街 · Nano Banana Pro 分层动态样片（约 4 秒，带原曲）。
图层：长安空景（推镜+横移）→ 灯笼呼吸 → 地面倒影 → 人物（绿幕抠像，走近，步伐起伏）→ 墨雨 → 地雾 → 前景虚焦枪杆 → 宣纸颗粒 → 上下黑边。
python3 tools/nb_v04_clip.py out/style_test/v04_nb_clip.mp4"""
import sys, math, subprocess, numpy as np, cv2
W, H, FPS, DUR = 1920, 1080, 30, 4.0
Y0, Y1 = 120, 960; PH = Y1 - Y0
D = 'assets/gen/NB/V04/'
def eio(u): u = min(max(u, 0), 1); return u * u * (3 - 2 * u)

bg = cv2.cvtColor(cv2.imread(D + 'bg_0.jpg'), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
bg = bg[40:1366]                                    # 去掉生图自带黑边
OS = 1.12; bw = int(W * OS); bh = int(bw * bg.shape[0] / bg.shape[1])
bg = cv2.resize(bg, (bw, bh), interpolation=cv2.INTER_AREA)
hsv = cv2.cvtColor((bg * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
lant = ((hsv[..., 2] > 200) & (hsv[..., 1] > 120)).astype(np.float32)
lant = cv2.GaussianBlur(lant, (0, 0), 6)
n, lab = cv2.connectedComponents((lant > 0.3).astype(np.uint8))
phase = np.random.default_rng(3).uniform(0, 6.28, n + 1).astype(np.float32)[lab]

wk = cv2.cvtColor(cv2.imread(D + 'walk_0.jpg'), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
g = wk[..., 1] - np.maximum(wk[..., 0], wk[..., 2])
al = np.clip(1 - (g - 0.12) / 0.25, 0, 1)
al = cv2.GaussianBlur(al, (0, 0), 0.8)
wk[..., 1] = np.minimum(wk[..., 1], np.maximum(wk[..., 0], wk[..., 2]))   # 去绿溢
ys, xs = np.where(al > 0.5); wk = wk[ys.min():ys.max() + 1, xs.min():xs.max() + 1]; al = al[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
fh, fw = al.shape

rng = np.random.default_rng(7)
drops = [(rng.uniform(-300, W + 300), rng.uniform(0, H), rng.uniform(0.5, 1.0)) for _ in range(420)]
grain = rng.standard_normal((H // 2, W // 2)).astype(np.float32)

def noise(t, sx, sy):
    a = cv2.resize(np.random.default_rng(int(sx)).random((9, 16)).astype(np.float32), (W + 400, H), interpolation=cv2.INTER_CUBIC)
    o = int(t * sy) % 400
    return a[:, o:o + W]

def frame(t):
    u = t / DUR; e = eio(u)
    sc = 1.0 + 0.07 * e; dx = -70 * e                               # 推镜 + 横移
    M = np.float32([[sc, 0, (W - bw * sc) / 2 + dx], [0, sc, Y0 + (PH - bh * sc) / 2 + 30 * e]])
    fl = 0.75 + 0.25 * np.sin(t * 7 + phase) * np.sin(t * 3.1 + phase * 2)
    src = bg * (1 + (0.45 * lant * fl)[..., None] * np.array([1.0, 0.35, 0.3], np.float32))
    fr = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # 人物：右后方走到中偏右，变大；步伐起伏
    stp = abs(math.sin(math.pi * t / 0.52))
    hh = int(560 + 210 * e); ww = int(fw * hh / fh)
    cx = 1330 - 170 * e; foot = Y0 + 640 + 150 * e - 10 * stp
    rot = 1.2 * math.sin(math.pi * t / 0.52)
    p = cv2.resize(wk, (ww, hh), interpolation=cv2.INTER_AREA); a = cv2.resize(al, (ww, hh), interpolation=cv2.INTER_AREA)
    R = cv2.getRotationMatrix2D((ww / 2, hh), rot, 1.0); R[0, 2] += cx - ww / 2; R[1, 2] += foot - hh
    P = cv2.warpAffine(p, R, (W, H)); A = cv2.warpAffine(a, R, (W, H))[..., None]
    # 环境融合：人物压暗 + 偏红环境光 + 背光红边
    P = P * np.array([0.86, 0.74, 0.74], np.float32) + 0.04 * np.array([1, 0.2, 0.2], np.float32)
    Ab = cv2.GaussianBlur(A[..., 0], (0, 0), 6)[..., None]
    rim = np.clip(A - Ab, 0, 1) * 1.6
    P = P + rim * np.array([0.9, 0.15, 0.12], np.float32)
    # 倒影：以脚底线翻转，模糊、压暗、水波抖动
    fy = int(foot)
    Pr = np.zeros_like(P); Ar = np.zeros_like(A)
    n_ = min(fy, H - fy)
    Pr[fy:fy + n_] = P[fy - n_:fy][::-1]; Ar[fy:fy + n_] = A[fy - n_:fy][::-1]
    mx, my = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    wob = np.sin(my * 0.30 + t * 9) * 5
    Pr = cv2.remap(Pr, mx + wob, my, cv2.INTER_LINEAR); Ar = cv2.remap(Ar, mx + wob, my, cv2.INTER_LINEAR)[..., None]
    Pr = cv2.GaussianBlur(Pr, (0, 0), 4); Ar = cv2.GaussianBlur(Ar, (0, 0), 4)[..., None] if Ar.ndim == 2 else cv2.GaussianBlur(Ar[..., 0], (0, 0), 4)[..., None]
    fade = np.clip(1 - (my[..., None] - fy) / 260, 0, 1) * 0.5
    fr = fr * (1 - Ar * fade) + Pr * 0.45 * Ar * fade
    # 落脚接触阴影
    sh = np.zeros((H, W), np.float32); cv2.ellipse(sh, (int(cx), fy), (int(ww * 0.45), 14), 0, 0, 360, 1.0, -1)
    fr = fr * (1 - 0.45 * cv2.GaussianBlur(sh, (0, 0), 10)[..., None])
    fr = fr * (1 - A) + P * A
    # 墨雨：两层，白丝为主（红底上可读），斜 10°
    L = np.zeros((H, W), np.float32)
    for i, (x, y, z) in enumerate(drops):
        yy = (y + t * 2200 * z) % (H + 200) - 100; xx = x + (yy) * 0.18
        ln = int(28 + 40 * z)
        cv2.line(L, (int(xx), int(yy)), (int(xx + ln * 0.18), int(yy + ln)), 0.35 + 0.5 * z, 1 + int(z > 0.85), cv2.LINE_AA)
    L = cv2.GaussianBlur(L, (0, 0), 0.6)[..., None]
    fr = fr + L * 0.55 * (np.array([1.0, 0.95, 0.93], np.float32) - fr)
    # 地雾（白墨，向左漂）
    m = noise(t, 11, 60) * np.clip((np.arange(H)[:, None] - 650) / 200, 0, 1) * np.clip((Y1 - np.arange(H)[:, None]) / 60, 0, 1)
    fr = fr + (m * 0.28)[..., None] * (np.array([0.95, 0.9, 0.88], np.float32) - fr)
    # 前景虚焦枪杆（浓墨，高速掠过）
    Lp = np.zeros((H // 2, W // 2), np.float32)
    for k, (x0, sl) in enumerate(((300 - 1500 * u, 0.25), (2100 - 1800 * u, -0.18))):
        cv2.line(Lp, (int(x0 / 2), 0), (int((x0 + sl * H) / 2), H // 2), 1.0, 9 + 4 * k, cv2.LINE_AA)
        cv2.fillConvexPoly(Lp, np.array([(int(x0 / 2) - 16, 0), (int(x0 / 2) + 16, 0), (int(x0 / 2), 70)], np.int32), 1.0)
    Lp = cv2.resize(cv2.GaussianBlur(Lp, (0, 0), 5), (W, H))[..., None]
    fr = fr * (1 - 0.95 * Lp) + 0.02 * Lp
    # 宣纸颗粒 + 暗角
    gr = cv2.resize(np.roll(grain, int(t * 977) % 400, axis=1), (W, H))[..., None]
    fr = fr + gr * 0.018
    vy, vx = np.ogrid[0:H, 0:W]; vig = 1 - 0.28 * (((vx - W / 2) / (W / 2)) ** 2 + ((vy - H / 2) / (H / 1.6)) ** 2)
    fr = fr * vig[..., None]
    fr[:Y0] = 0; fr[Y1:] = 0
    return (np.clip(fr, 0, 1) * 255).astype(np.uint8)

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/style_test/v04_nb_clip.mp4'
    if len(sys.argv) > 2:                                         # 单帧：python3 ... out.png 1.5
        cv2.imwrite(out, cv2.cvtColor(frame(float(sys.argv[2])), cv2.COLOR_RGB2BGR)); sys.exit()
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-ss', '17.0', '-t', str(DUR), '-i', 'audio/谁定正邪.mp3', '-map', '0:v', '-map', '1:a',
                          '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()
