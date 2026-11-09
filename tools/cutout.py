"""tools/cutout.py — 纯色背景生图抠图（SPRITE 试点用）
步骤：rembg isnet-general-use 粗蒙版 → 估计背景板（蒙版外像素拟合二次曲面）→ 在蒙版边缘带内用「与背景色差」做差值抠像
     → 前景反混合 F=(I-(1-a)B)/a 去掉灰边 → alpha 轻收缩 + 羽化 → RGBA PNG。
用法：python3 tools/cutout.py raw.png out.png [宽=2560] [--green]
"""
import sys, numpy as np, cv2
from PIL import Image


def fit_bg(img, bgm):
    """背景板：蒙版外像素拟合二次曲面（每通道），得到无人物的背景估计。"""
    h, w = bgm.shape
    ys, xs = np.nonzero(bgm)
    sel = np.random.default_rng(0).choice(len(ys), min(200000, len(ys)), replace=False)
    ys, xs = ys[sel], xs[sel]
    def basis(x, y):
        x = x / w - 0.5; y = y / h - 0.5
        return np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], -1)
    A = basis(xs.astype(np.float32), ys.astype(np.float32))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    Bf = basis(xx, yy)
    out = np.zeros_like(img)
    for c in range(3):
        coef, *_ = np.linalg.lstsq(A, img[ys, xs, c], rcond=None)
        out[..., c] = Bf @ coef
    return out


def cutout(raw, out, width=2560, green=False):
    from rembg import remove, new_session
    im = Image.open(raw).convert('RGB')
    H = round(im.size[1] * width / im.size[0])
    im = im.resize((width, H), Image.LANCZOS)
    img = np.asarray(im).astype(np.float32) / 255
    m = np.asarray(remove(im.resize((1920, round(1920 * H / width))), session=new_session('isnet-general-use'),
                          only_mask=True)).astype(np.float32) / 255
    m = cv2.resize(m, (width, H), interpolation=cv2.INTER_CUBIC)
    sure_bg = cv2.erode((m < 0.02).astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
    B = fit_bg(img, sure_bg)
    if green:  # 绿幕：先色键（g 超出 max(r,b) 的量）
        ref = float(np.median((B[..., 1] - np.maximum(B[..., 0], B[..., 2]))[sure_bg]))
        key = np.clip((img[..., 1] - np.maximum(img[..., 0], img[..., 2])) / max(1e-3, ref), 0, 1)
        a_diff = 1 - key
    else:      # 灰板：与背景的色差（亮度差为主 + 色度差）
        d = img - B
        dist = np.sqrt((d ** 2).sum(-1) + 2.0 * (d.mean(-1)) ** 2)
        a_diff = np.clip((dist - 0.035) / 0.22, 0, 1)
    core = cv2.erode((m > 0.9).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    band = cv2.dilate((m > 0.05).astype(np.uint8), np.ones((41, 41), np.uint8)) > 0
    a = np.where(core, 1.0, np.where(band, np.maximum(a_diff, np.clip(m * 1.1 - 0.1, 0, 1) * (a_diff > 0.15)), 0.0))
    a = a.astype(np.float32)
    n, lab, st, _ = cv2.connectedComponentsWithStats((a > 0.1).astype(np.uint8), 8)   # 去孤立噪点
    keep = np.zeros(n, bool); keep[1:] = st[1:, cv2.CC_STAT_AREA] > 400
    a = a * keep[lab]
    ae = np.clip(a, 0.04, 1)[..., None]                       # 前景反混合：去灰/绿边
    F = np.clip((img - (1 - ae) * B) / ae, 0, 1)
    if green:                                                 # despill：g 不超过 (r+b)/2
        F[..., 1] = np.minimum(F[..., 1], (F[..., 0] + F[..., 2]) / 2)
    F = np.where(a[..., None] > 0.97, img, F)
    a = np.clip((a - 0.06) / 0.94, 0, 1) ** 1.15              # alpha 轻收缩 + 羽化
    a = cv2.GaussianBlur(a, (0, 0), 0.6)
    rgba = np.dstack([F, a])
    Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA').save(out)
    return B, m


if __name__ == '__main__':
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    cutout(args[0], args[1], int(args[2]) if len(args) > 2 else 2560, '--green' in sys.argv)
    print(args[1])
