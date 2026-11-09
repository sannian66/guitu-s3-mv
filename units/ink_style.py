"""代码版「黑白红国风墨线」滤镜（r5 风格测试，0 积分）。
思路：亮度 → 水墨分层（宣纸白/淡墨/浓墨）；XDoG 提墨线；暗而平的背景 → 朱砂红；原有红/暖光 → 朱砂；叠宣纸纹理。
只改「怎么画」，不改「画什么」。"""
import numpy as np, cv2

PAPER = np.array([238, 230, 214], np.float32) / 255   # 宣纸
INK = np.array([18, 16, 16], np.float32) / 255        # 浓墨
RED = np.array([196, 22, 26], np.float32) / 255       # 朱砂
_rng = np.random.default_rng(7)
_tex = {}

def _paper_tex(h, w):
    if (h, w) not in _tex:
        n = _rng.standard_normal((h // 4, w // 4)).astype(np.float32)
        n = cv2.resize(cv2.GaussianBlur(n, (0, 0), 1.2), (w, h))
        fib = cv2.GaussianBlur(_rng.standard_normal((h, w)).astype(np.float32), (0, 0), 0.7)
        _tex[(h, w)] = (n * 0.035 + fib * 0.02)[..., None]
    return _tex[(h, w)]

def xdog(L, sigma=1.0, k=1.6, p=22, eps=0.62, phi=12):
    g1 = cv2.GaussianBlur(L, (0, 0), sigma); g2 = cv2.GaussianBlur(L, (0, 0), sigma * k)
    d = (1 + p) * g1 - p * g2
    return np.where(d >= eps, 1.0, 1 + np.tanh(phi * (d - eps))).astype(np.float32)

def ink_style(rgb, red_bg=0.9, line=1.0):
    img = rgb.astype(np.float32) / 255
    H0 = img.shape[0]
    rows = img.max(axis=(1, 2))
    top = int(np.argmax(rows > 0.06)); bot = H0 - int(np.argmax(rows[::-1] > 0.06))
    if bot - top < H0 * 0.5: top, bot = 0, H0
    full = img.copy(); img = img[top:bot]; rgb = rgb[top:bot]
    h, w = img.shape[:2]
    L = img @ np.array([0.299, 0.587, 0.114], np.float32)
    # 自动曝光：暗片拉开到全范围
    lo, hi = np.percentile(L, 2), np.percentile(L, 99.5)
    Ln = np.clip((L - lo) / max(hi - lo, 1e-3), 0, 1) ** 0.75
    # 水墨分层：3 阶 + 柔边
    Ls = cv2.bilateralFilter(Ln, 9, 0.12, 6)
    tone = np.clip(Ls * 1.25, 0, 1)
    tone = np.round(tone * 3) / 3 * 0.6 + tone * 0.4
    base = INK[None, None] + (PAPER - INK)[None, None] * tone[..., None]
    # 墨线
    e = xdog(cv2.bilateralFilter(Ln, 7, 0.08, 4), 1.3) ; e = cv2.GaussianBlur(e, (0, 0), 0.6)
    base = base * (1 - line * (1 - e[..., None]) * 0.85)
    # 红：原有红/暖光
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    hh, s, v = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
    warm = ((hh < 60) | (hh > 330)).astype(np.float32) * np.clip((s - 0.3) / 0.3, 0, 1) * np.clip((v - 0.25) / 0.3, 0, 1)
    # 红：暗且平的背景（局部细节少）
    det = cv2.GaussianBlur(np.abs(cv2.Laplacian(Ln, cv2.CV_32F, ksize=3)), (0, 0), 9)
    flat = np.clip(1 - det / 0.05, 0, 1)
    dark = np.clip((0.42 - Ls) / 0.25, 0, 1)
    bg = np.clip(cv2.GaussianBlur(flat * dark, (0, 0), 14) * 1.6, 0, 1) * red_bg
    bright = np.clip((tone - 0.8) / 0.2, 0, 1)
    wr = np.clip(np.maximum(warm, bg) * (1 - bright * (1 - warm)), 0, 1)
    redc = RED[None, None] * (0.92 + 0.25 * np.clip(Ln, 0, 1))[..., None]
    out = base * (1 - wr[..., None]) + np.minimum(redc, base * 0 + redc) * wr[..., None]
    out = out * (1 - (1 - e[..., None]) * 0.35 * wr[..., None])   # 红底上也留墨线
    out = out + _paper_tex(h, w) * (0.35 + 0.3 * tone[..., None])
    full[top:bot] = np.clip(out, 0, 1)
    return (full * 255).astype(np.uint8)

if __name__ == '__main__':
    import sys
    from PIL import Image
    a = np.array(Image.open(sys.argv[1]).convert('RGB'))
    Image.fromarray(ink_style(a)).save(sys.argv[2])
