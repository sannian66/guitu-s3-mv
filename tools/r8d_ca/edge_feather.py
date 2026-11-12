"""硬规则「任何图层都不允许露出裁切边」：抠像素材的 alpha 碰到画布边的，沿该边做有形状（噪声扰动）的羽化，
让内容在边上自然消散，而不是被直线截断。只处理碰边的那几条边；幂等（处理过的文件记在 .feathered 里，不重复处理）。
用法：python tools/r8d_ca/edge_feather.py [--check]"""
import os, sys, glob, json
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = ROOT + '/assets/gen/R8_D/CA/'
DONE = D + '.feathered.json'
done = json.load(open(DONE)) if os.path.exists(DONE) else []
check = '--check' in sys.argv


def touching(a):
    e = {'L': a[:, :3].max(1), 'R': a[:, -3:].max(1), 'T': a[:3].max(0), 'B': a[-3:].max(0)}
    return {k: int((v > 0.3).sum()) for k, v in e.items() if (v > 0.3).sum() > 0}


for p in sorted(glob.glob(D + '*_cut.png')):
    n = os.path.basename(p)
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    a = im[..., 3].astype(np.float32) / 255
    t = touching(a)
    print(n, t or '-', '(已羽化)' if n in done else '')
    if check or not t or n in done: continue
    h, w = a.shape
    r = np.random.default_rng(abs(hash(n)) % 2**32)
    nz = cv2.resize(cv2.GaussianBlur(r.random((h // 16 + 2, w // 16 + 2)).astype(np.float32), (0, 0), 1.0), (w, h), interpolation=cv2.INTER_CUBIC)
    nz = (nz - nz.min()) / (np.ptp(nz) + 1e-6)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    band = 0.045 * w                                       # 约 90px（2048 宽）羽化带，噪声扰动 ±40%
    m = np.ones_like(a)
    for k in t:
        d = {'L': xx, 'R': w - 1 - xx, 'T': yy, 'B': h - 1 - yy}[k]
        m *= np.clip((d - band * 0.15 - nz * band * 0.6) / (band * 0.6), 0, 1)
    im[..., 3] = (np.clip(a * m, 0, 1) * 255 + 0.5).astype(np.uint8)
    cv2.imwrite(p, im)
    done.append(n)
if not check: json.dump(done, open(DONE, 'w'), indent=0)
