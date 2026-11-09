"""E 组：精灵外沿发丝去网（逆光飞丝 + 灰底缝隙在暗底上读成网格/白毛边）。
以原抠图为准：取「实心」alpha(>0.9) 的平滑外包络、再内缩 shrink px → 与原 alpha 取 min，外沿 2px 羽化；外沿 40px 带内亮度压到内侧参考（去白边）。
  python3 tools/e_smoothhair.py in_cut.png out_cut.png [sig=10] [shrink=10] [raw.png]"""
import sys, numpy as np, cv2
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
sig = float(sys.argv[3]) if len(sys.argv) > 3 else 10; shrink = int(sys.argv[4]) if len(sys.argv) > 4 else 10
im = np.asarray(Image.open(src).convert('RGBA')).astype(np.float32)
C, a = im[..., :3], im[..., 3] / 255
RAW = sys.argv[5] if len(sys.argv) > 5 else None
solid = (a > 0.5).astype(np.uint8)
ff = solid.copy(); hh, ww = ff.shape; msk = np.zeros((hh + 2, ww + 2), np.uint8)
ff2 = np.pad(ff, 1); cv2.floodFill(ff2, np.zeros((hh + 4, ww + 4), np.uint8), (0, 0), 2)
solid = (ff2[1:-1, 1:-1] != 2).astype(np.uint8)                     # 填掉内部洞（白发缕与灰底同色被抠成洞）
solid = cv2.morphologyEx(solid, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
env = (cv2.GaussianBlur(solid.astype(np.float32), (0, 0), sig) > 0.55).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(env, 8)
env = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
env = cv2.erode(env, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * shrink + 1, 2 * shrink + 1)))
fill = cv2.morphologyEx(env, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
envf = cv2.GaussianBlur(fill.astype(np.float32), (0, 0), 1.8)
inner = cv2.erode(fill, np.ones((61, 61), np.uint8)).astype(np.float32)
A2 = np.minimum(np.maximum(a, cv2.erode(fill, np.ones((9, 9), np.uint8)).astype(np.float32)), envf)                     # 内部保持原 alpha（内部实心），外沿被平滑包络截掉飞丝
if RAW:                                                        # 内部（填洞后）颜色直接取原图：去掉低 alpha 处去污染算出的杂色斑
    R = np.asarray(Image.open(RAW).convert('RGB')).astype(np.float32)
    kin = cv2.GaussianBlur(cv2.erode(fill, np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 1.5)[..., None]
    C = R * kin + C * (1 - kin)
band = np.clip(envf - inner, 0, 1)
num = cv2.GaussianBlur(C * inner[..., None], (0, 0), 24); den = cv2.GaussianBlur(inner, (0, 0), 24)[..., None]
ref = num / np.maximum(den, 1e-3)
lum = C.mean(-1, keepdims=True); rl = ref.mean(-1, keepdims=True)
Cc = np.where(lum > rl * 1.1, C * (rl * 1.1 / np.maximum(lum, 1)), C)
C2 = C * (1 - band[..., None]) + Cc * band[..., None]
Image.fromarray(np.dstack([np.clip(C2, 0, 255), np.clip(A2, 0, 1) * 255]).astype(np.uint8), 'RGBA').save(dst)
print(dst)
