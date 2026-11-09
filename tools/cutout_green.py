"""tools/cutout_green.py — 纯绿幕抠像（不依赖 rembg / 模型下载）

生图时背景指定为纯 #00FF00 平涂，抠像只需色键：
  绿度 g = G - max(R,B)；背景绿度的中位数 ref → key = clip(g/ref, 0, 1) → alpha = 1 - key
  再补：去孤立噪点、前景反混合（去绿边）、despill（G 不超过 (R+B)/2）、alpha 轻收缩 + 0.6px 羽化
发丝保留半透明 alpha（正是灰板抠不出来的部分）。

用法：python3 tools/cutout_green.py raw.png out.png [宽=2048]
     python3 tools/cutout_green.py raw.png out.png 2048 --gain 1.15 --erode 0.06
"""
import sys
import numpy as np, cv2
from PIL import Image


def cutout_green(raw, out, width=2048, gain=1.0, shrink=0.06):
    im = Image.open(raw).convert('RGB')
    h = round(im.size[1] * width / im.size[0])
    src = im.resize((width, h), Image.LANCZOS)
    img = np.asarray(src).astype(np.float32) / 255

    g = img[..., 1] - np.maximum(img[..., 0], img[..., 2])            # 绿度
    border = np.concatenate([g[:8].ravel(), g[-8:].ravel(), g[:, :8].ravel(), g[:, -8:].ravel()])
    ref = float(np.median(border[border > 0.05])) if (border > 0.05).any() else float(np.percentile(g, 97))
    ref = max(ref, 0.10)
    key = np.clip(g / ref, 0, 1) ** (1 / max(0.2, gain))
    a = 1.0 - key

    # 去孤立噪点 / 填小洞
    n, lab, st, _ = cv2.connectedComponentsWithStats((a > 0.10).astype(np.uint8), 8)
    keep = np.zeros(n, bool); keep[1:] = st[1:, cv2.CC_STAT_AREA] > max(400, width * 2)
    a = a * keep[lab]
    holes = (a < 0.35).astype(np.uint8)
    holes = cv2.morphologyEx(holes, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    holes = cv2.dilate(holes, np.ones((3, 3), np.uint8)) * (cv2.erode((a > 0.6).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)
    a = np.maximum(a, holes.astype(np.float32))

    # 背景色（纯绿平涂，取 alpha 极低处的中位色）
    bgm = a < 0.02
    B = np.median(img[bgm], 0) if bgm.sum() > 1000 else np.array([0.02, 0.98, 0.06], np.float32)
    ae = np.clip(a, 0.04, 1)[..., None]
    F = np.clip((img - (1 - ae) * B) / ae, 0, 1)                      # 前景反混合：去掉半透边缘的绿
    F[..., 1] = np.minimum(F[..., 1], (F[..., 0] + F[..., 2]) * 0.5)  # despill
    F = np.where(a[..., None] > 0.97, img, F)
    a = np.clip((a - shrink) / (1 - shrink), 0, 1) ** 1.15            # alpha 收缩 + 羽化
    a = cv2.GaussianBlur(a.astype(np.float32), (0, 0), 0.6)
    Image.fromarray((np.dstack([F, a]) * 255 + 0.5).astype(np.uint8), 'RGBA').save(out)
    return ref, float(a.mean())


if __name__ == '__main__':
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    kw = {}
    if '--gain' in sys.argv: kw['gain'] = float(sys.argv[sys.argv.index('--gain') + 1])
    if '--erode' in sys.argv: kw['shrink'] = float(sys.argv[sys.argv.index('--erode') + 1])
    ref, cov = cutout_green(args[0], args[1], int(args[2]) if len(args) > 2 else 2048, **kw)
    print(f'{args[1]}  bg_green={ref:.3f}  alpha_mean={cov:.3f}')
