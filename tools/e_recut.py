"""E 组抠图（tools/recut_flat.py 的变体，不改原文件）：发丝缝隙不再被闭运算填成实心灰；脚下地面阴影去掉。
  python3 tools/e_recut.py raw.png out_cut.png [thr=22] [deep=41] [floor=1] [multi=0]（multi>0：保留面积≥该比例的所有连通域）"""
import sys, numpy as np, cv2
from PIL import Image
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from cutout import fit_bg

def recut(raw, out, thr=22.0, deep=41, floor=1, multi=0.0):
    im = np.asarray(Image.open(raw).convert('RGB')).astype(np.float32)
    h, w = im.shape[:2]
    border = np.zeros((h, w), bool); b = int(0.04 * w)
    border[:, :b] = border[:, -b:] = True; border[:b, :] = True
    g = im.mean(-1); sat = im.max(-1) - im.min(-1)
    med = np.median(g[border])
    bgm = border & (np.abs(g - med) < 25) & (sat < 20)
    B = fit_bg(im, bgm)
    d = cv2.GaussianBlur(np.sqrt(((im - B) ** 2).sum(-1)), (0, 0), 1.0)
    hard = (d > thr).astype(np.uint8)
    hard = cv2.morphologyEx(hard, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(hard, 8)
    keep = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])
    m = (lab == keep).astype(np.uint8)
    if multi > 0:   # 多主体（人 + 插地刀）：保留面积 ≥ multi×画幅 的所有连通域
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] >= multi * h * w: m[lab == i] = 1
    # 小碎块（发梢）只要离主体近也保留
    big = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))
    m = np.maximum(m, hard * big)
    soft = np.clip((d - thr * 0.6) / (thr * 1.4), 0, 1)
    inner = cv2.erode(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (deep, deep)))
    inner = cv2.GaussianBlur(inner.astype(np.float32), (0, 0), deep / 6)
    a = np.maximum(soft * m, inner)
    if floor:   # 地面投影：比背景暗、低饱和、中等色差、在人物包围盒底部 10% 内
        ys, xs = np.nonzero(m)
        y1 = ys.max(); y0 = ys.min(); band = (np.arange(h)[:, None] > y1 - 0.10 * (y1 - y0))
        darker = (B.mean(-1) - g) > 0
        sh = band & darker & (sat < 18) & (g > 0.35 * med)
        a = np.where(sh, a * np.clip((0.55 * med - g) / (0.2 * med), 0, 1), a)
    a = cv2.GaussianBlur(a.astype(np.float32), (0, 0), 0.6)
    af = np.clip(a, 0.05, 1)[..., None]
    F = np.clip((im - (1 - af) * B) / af, 0, 255)
    Image.fromarray(np.dstack([F, a * 255]).astype(np.uint8), 'RGBA').save(out)
    print(out, 'alpha>0.5 frac=%.3f' % (a > 0.5).mean())

if __name__ == '__main__':
    a = sys.argv
    recut(a[1], a[2], float(a[3]) if len(a) > 3 else 22.0, int(a[4]) if len(a) > 4 else 41, int(a[5]) if len(a) > 5 else 1,
          float(a[6]) if len(a) > 6 else 0.0)
