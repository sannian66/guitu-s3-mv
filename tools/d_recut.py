"""tools/d_recut.py — [D组] recut_flat 的多连通域版（群像：保留面积 >8% 最大块的所有块）。原文件：tools/recut_flat.py — 纯灰底生图的「色差 + 填洞」重抠（rembg 把同色系皮肤抠穿时用；2026-11-09 第四任，S062）
用法：python3 tools/recut_flat.py raw.png out_cut.png [阈值=16] [宽=2560]
背景：四周边框像素拟合二次曲面 → 与背景色差 → 阈值软化 → 取最大连通域 + 填内部洞 → 只在边缘带保留软 alpha → 反混合去灰边。"""
import sys, numpy as np, cv2
from PIL import Image
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from cutout import fit_bg

def recut(raw, out, thr=16.0, width=2560):
    im = np.asarray(Image.open(raw).convert('RGB')).astype(np.float32)
    h0, w0 = im.shape[:2]
    if w0 != width: im = cv2.resize(im, (width, round(h0 * width / w0)), interpolation=cv2.INTER_AREA)
    h, w = im.shape[:2]
    border = np.zeros((h, w), bool); b = int(0.04 * w)
    border[:, :b] = border[:, -b:] = True; border[:b, :] = True
    # 边框里只取接近中性灰的像素（排除贴边的衣袖）
    g = im.mean(-1); sat = im.max(-1) - im.min(-1)
    med = np.median(g[border])
    bgm = border & (np.abs(g - med) < 25) & (sat < 20)
    B = fit_bg(im, bgm)
    d = np.sqrt(((im - B) ** 2).sum(-1))
    d = cv2.GaussianBlur(d, (0, 0), 1.2)
    hard = (d > thr).astype(np.uint8)
    hard = cv2.morphologyEx(hard, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(hard, 8)
    big = st[1:, cv2.CC_STAT_AREA].max()
    m = np.isin(lab, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 0.08 * big]).astype(np.uint8)
    ff = m.copy(); mask = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(ff, mask, (0, h - 1) if m[h - 1, 0] == 0 else (w - 1, h - 1), 1)   # 外部填 1
    holes = (ff == 0)
    # 洞只填小的（指缝等大的背景区保留）
    nh, lh, sh, _ = cv2.connectedComponentsWithStats(holes.astype(np.uint8), 8)
    for i in range(1, nh):
        if sh[i, cv2.CC_STAT_AREA] < 0.004 * h * w: m[lh == i] = 1
    soft = np.clip((d - thr * 0.5) / thr, 0, 1)
    inner = cv2.erode(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    a = np.where(inner > 0, 1.0, soft * m)
    a = cv2.GaussianBlur(a.astype(np.float32), (0, 0), 0.7)
    af = np.clip(a, 0.05, 1)[..., None]
    F = np.clip((im - (1 - af) * B) / af, 0, 255)
    rgba = np.dstack([F, a * 255]).astype(np.uint8)
    Image.fromarray(rgba, 'RGBA').save(out)
    print(out, rgba.shape, 'alpha>0.5 frac=%.3f' % (a > 0.5).mean())

if __name__ == '__main__':
    recut(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 16.0)
