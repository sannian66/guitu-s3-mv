"""units/a_r6.py — A 组第六棒辅助：新精灵预处理（景深/去灰边/裁切）、宣纸、纸面印痕、凹刻字、按原图点锚定摆放。
只被 units/sec_a_intro_verse1.py 使用。"""
import os, math, hashlib
import numpy as np, cv2
from PIL import Image
import a_kit as A
import typo as T

W, H = 1920, 1080
GEN = A.GEN
CACHE = A.CACHE


def _cached(name, build):
    os.makedirs(CACHE, exist_ok=True)
    out = CACHE + '/r6_' + name + '.png'
    if not os.path.exists(out):
        Image.fromarray(np.clip(build() * 255, 0, 255).astype(np.uint8), 'RGBA').save(out)
    return out


def _load(key):
    return np.asarray(Image.open(GEN + key + '_cut.png').convert('RGBA')).astype(np.float32) / 255


def _clean_alpha(F, lo=0.18, erode=3, despill=True):
    """收灰边：alpha 低端截掉 + 腐蚀；边缘像素颜色向内部颜色收（去中灰溢色）。"""
    a = F[..., 3]
    a2 = np.clip((a - lo) / (1 - lo), 0, 1)
    if erode: a2 = np.minimum(a2, cv2.GaussianBlur(cv2.erode(a2, np.ones((erode, erode), np.uint8)), (0, 0), 0.8))
    out = F.copy(); out[..., 3] = a2
    if despill:
        rgb = F[..., :3]
        inner = cv2.erode((a > 0.97).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
        blur_c = cv2.GaussianBlur(rgb * inner[..., None], (0, 0), 6); blur_w = cv2.GaussianBlur(inner, (0, 0), 6)[..., None]
        fill = blur_c / np.maximum(blur_w, 1e-4)
        edge = np.clip((1 - a2) * 2.2, 0, 1)[..., None] * (a2 > 0)[..., None] * (blur_w > 0.02)
        out[..., :3] = rgb * (1 - edge) + np.minimum(rgb, fill) * edge      # 边缘只许变暗（灰底溢色 → 内部颜色）
    return out


def tsh_seal_dof():
    """太上皇握玺：左半（手 + 玉玺）锐利；右半（脸、发）景深虚化 + 压暗 → 手玺是唯一焦点（脸作后景）。"""
    def b():
        F = _clean_alpha(_load('A_r6/tsh_seal_lift'), lo=0.15, erode=3)
        h, w = F.shape[:2]
        xx = np.arange(w, dtype=np.float32)[None, :] / w
        k = np.clip((xx - 0.53) / 0.10, 0, 1)                           # 0 = 焦内，1 = 焦外
        pre = F[..., :3] * F[..., 3:4]
        Bp = cv2.GaussianBlur(pre, (0, 0), 16); Ba = cv2.GaussianBlur(F[..., 3], (0, 0), 16)
        P = pre * (1 - k[..., None]) + Bp * k[..., None]; Al = F[..., 3] * (1 - k) + Ba * k
        rgb = P / np.maximum(Al[..., None], 1e-4) * (1 - 0.55 * k[..., None])
        return np.dstack([np.clip(rgb, 0, 1), Al])
    return _cached('tsh_seal_dof', b)


def clean(key, lo=0.18, erode=3):
    return _cached(key.replace('/', '_') + '_cl', lambda: _clean_alpha(_load(key), lo=lo, erode=erode))


def anc_for(path, pt):
    """原图归一化点 pt → place() 的 anc（包围盒归一化坐标）。"""
    sp = A.sprite(path, 640); x0, y0, x1, y1 = sp.bbox
    return ((pt[0] - x0) / (x1 - x0), (pt[1] - y0) / (y1 - y0))


_PAPER = {}
def paper(seed=21, warm=(0.80, 0.69, 0.50)):
    """宣纸：纤维纹（横向拉长细噪声）+ 云絮团（低频）+ 偶见纸筋。返回 (H,W,3) 线性色（未打光）。"""
    if seed in _PAPER: return _PAPER[seed]
    f1 = cv2.resize(A.tex(seed, 512, 6, 5), (W, H))
    f2 = cv2.resize(A.tex(seed + 1, 512, 60, 3)[:, :128], (W, H))           # 纤维（横向拉长）
    f3 = cv2.resize(A.tex(seed + 2, 256, 24, 3), (W, H))
    r = np.random.default_rng(seed); fib = np.zeros((H, W), np.float32)
    for _ in range(140):
        x, y = r.uniform(0, W), r.uniform(0, H); a = r.uniform(0, math.pi); L = r.uniform(20, 90)
        cv2.line(fib, (int(x), int(y)), (int(x + L * math.cos(a)), int(y + L * math.sin(a))), 1.0, 1, cv2.LINE_AA)
    v = 0.86 + 0.10 * f1 + 0.07 * (f2 - 0.5) + 0.04 * (f3 - 0.5) - 0.05 * cv2.GaussianBlur(fib, (0, 0), 0.6)
    out = v[..., None] * np.array(warm, np.float32)
    _PAPER[seed] = out
    return out


def imprint(fr, text, cx, cy, size, k=1.0, rot=-3.0, seed=5, col=(0.62, 0.09, 0.07), bleed=1.0):
    """纸面印痕（乘到纸上，纸纹透出来）：白文印，边缘纸纤维洇开，朱色降饱和 15%；k 0→1 印泥加深。"""
    import props as PR
    face = PR.seal_face(text, int(size), style='bai', wear=0.22, seed=seed)
    a = face[..., 3]
    s = a.shape[0]; pad = int(s * 0.12)
    a = np.pad(a, pad)
    nz = cv2.resize(A.tex(seed + 77, 256, 30, 3), a.shape[::-1])
    fib = cv2.resize(A.tex(seed + 78, 256, 90, 2)[:, :64], a.shape[::-1])
    soft = cv2.GaussianBlur(a, (0, 0), 2.2 * bleed)
    a = np.maximum(a * (0.82 + 0.18 * nz), soft * np.clip(0.55 + 0.6 * (fib - 0.5), 0, 1) * 0.75)   # 纤维晕
    M = cv2.getRotationMatrix2D((a.shape[1] / 2, a.shape[0] / 2), rot, 1.0); a = cv2.warpAffine(a, M, a.shape[::-1])
    L = np.zeros((H, W), np.float32)
    h, w = a.shape; x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xs, ys, xe, ye = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    L[ys:ye, xs:xe] = a[ys - y0:ye - y0, xs - x0:xe - x0]
    c = np.array(col, np.float32); g = c.mean(); c = g + (c - g) * 0.85                      # 降饱和 15%
    tint = c / 0.8
    L = L * k
    return fr * (1 - L[..., None]) + fr * tint * L[..., None], L


def engraved(fr, mask, light=(-1, -1), depth=7, dark=0.80, hl=(0.9, 0.75, 0.55), hl_amt=0.8, inner_col=None):
    """凹刻字/凹坑：mask 内压暗，背光一侧内壁投影、迎光一侧内壁高光（石材，靠侧光读形）。"""
    m = cv2.GaussianBlur(mask, (0, 0), 1.0)
    lx, ly = light
    sh = np.clip(m - cv2.warpAffine(m, np.float32([[1, 0, -lx * depth], [0, 1, -ly * depth]]), (W, H)), 0, 1)
    hi = np.clip(m - cv2.warpAffine(m, np.float32([[1, 0, lx * depth * 0.6], [0, 1, ly * depth * 0.6]]), (W, H)), 0, 1)
    out = fr * (1 - dark * m[..., None])
    if inner_col is not None: out = out + m[..., None] * np.array(inner_col, np.float32)
    out = out * (1 - 0.6 * sh[..., None])
    return out + hi[..., None] * np.array(hl, np.float32) * hl_amt


def hair_clean(key, protect=None, thr=0.06, soft=0.08, band=61):
    """黑发灰晕：抠图 alpha × 与灰底的色距（raw 角落估灰），protect=(x0,y0,x1,y1) 归一化区域内保留原 alpha（如刀身）。"""
    def b():
        F = _load(key)
        R = np.asarray(Image.open(GEN + key + '_raw.png').convert('RGB').resize(F.shape[1::-1], Image.LANCZOS)).astype(np.float32) / 255
        h, w = R.shape[:2]; m = 24
        pts = np.concatenate([R[:m].reshape(-1, 3), R[:, -m:].reshape(-1, 3)])
        g = np.median(pts, 0)
        d = np.sqrt(((R - g) ** 2).sum(-1))
        k = np.clip((d - thr) / soft, 0, 1)
        inner = cv2.erode((F[..., 3] > 0.9).astype(np.uint8), np.ones((band, band), np.uint8)).astype(np.float32)
        inner = cv2.GaussianBlur(inner, (0, 0), band / 6)
        a = F[..., 3] * np.maximum(k, inner)                                   # 只在外缘带做色距（脸/手内部不动）
        if protect:
            x0, y0, x1, y1 = protect
            pm = np.zeros((h, w), np.float32); pm[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = 1
            pm = cv2.GaussianBlur(pm, (0, 0), 6)
            a = a * (1 - pm) + F[..., 3] * pm
        a = np.minimum(a, cv2.GaussianBlur(cv2.erode(a, np.ones((3, 3), np.uint8)), (0, 0), 0.7))
        rgb = F[..., :3] * (0.55 + 0.45 * np.clip(a, 0, 1)[..., None] ** 0.5)          # 半透明边只许变暗
        return np.dstack([rgb, a])
    return _cached(key.replace('/', '_') + '_hc2', b)
