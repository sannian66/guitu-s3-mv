"""tools/c_dehalo.py — C 组：纯灰底精灵去发丝灰边（recut_flat 填洞后，发丝之间的灰底被当成实体）。
在 alpha 边缘带内按「与灰底色差」重算 alpha，并反混合去灰。用法：python3 tools/c_dehalo.py cut.png [带宽=70] [lo=12] [hi=46]"""
import sys, numpy as np, cv2
from PIL import Image

def dehalo(p, band=70, lo=12.0, hi=46.0):
    im = np.asarray(Image.open(p)).astype(np.float32)
    rgb, a = im[..., :3], im[..., 3] / 255.0
    solid = (a > 0.5).astype(np.uint8)
    dist = cv2.distanceTransform(solid, cv2.DIST_L2, 5)
    ring = (dist > 2) & (dist < 6)
    bg = np.median(rgb[(a > 0) & (a < 0.6)], 0) if ((a > 0) & (a < 0.6)).sum() > 100 else np.array([128, 128, 128], np.float32)
    gray = np.array([np.median(rgb[ring & (np.abs(rgb - 128).max(-1) < 18)][:, c]) if (ring & (np.abs(rgb - 128).max(-1) < 18)).sum() > 50 else 128 for c in range(3)], np.float32)
    d = np.sqrt(((rgb - gray) ** 2).sum(-1))
    am = np.clip((d - lo) / (hi - lo), 0, 1)
    w = np.clip(1 - dist / band, 0, 1)                    # 边缘带权重（越靠外越按色差）
    an = a * (1 - w + w * am)
    an = cv2.GaussianBlur(an, (0, 0), 0.7)
    safe = np.maximum(an, 0.05)[..., None]
    F = np.clip((rgb - (1 - safe) * gray) / safe, 0, 255)
    F = np.where(an[..., None] > 0.97, rgb, F)
    out = np.dstack([F, np.clip(an * 255, 0, 255)]).astype(np.uint8)
    Image.fromarray(out).save(p)
    print(p, 'gray', gray.round(1), 'alpha>0.5', (an > 0.5).mean().round(3))

if __name__ == '__main__':
    a = sys.argv
    dehalo(a[1], *(float(x) for x in a[2:]))
