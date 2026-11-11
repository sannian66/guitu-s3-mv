"""细线元素（雨丝）绿幕抠像：不做连通域去噪（tools/cutout_green.py 会把细雨丝当噪点删掉）。
用法：python tools/r8d_ca/cut_thin.py raw.png out.png"""
import sys, numpy as np, cv2
from PIL import Image
im = Image.open(sys.argv[1]).convert('RGB').resize((2048, 1152), Image.LANCZOS)
img = np.asarray(im).astype(np.float32) / 255
g = img[..., 1] - np.maximum(img[..., 0], img[..., 2])
ref = float(np.median(g[g > 0.3]))
a = 1 - np.clip(g / ref, 0, 1)
a = np.clip((a - 0.08) / 0.92, 0, 1)
B = np.median(img[a < 0.02], 0)
ae = np.clip(a, 0.04, 1)[..., None]
F = np.clip((img - (1 - ae) * B) / ae, 0, 1)
F[..., 1] = np.minimum(F[..., 1], (F[..., 0] + F[..., 2]) * 0.5)
Image.fromarray((np.dstack([F, a]) * 255 + 0.5).astype(np.uint8), 'RGBA').save(sys.argv[2])
print(sys.argv[2], 'alpha_mean', float(a.mean()))
