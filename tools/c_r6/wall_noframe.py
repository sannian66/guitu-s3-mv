"""C 组 r6：C5/c22_wall 去掉墙上三块画框浮雕（用户 15:28 拍板），补成连续砖墙。
做法：每块框一个多边形遮罩；在同一面墙上搜一块平移来源（砖缝行对齐 = 环带 SSD 最小、来源不碰任何框），
拷来源的高频纹理 + 原图周边 Telea 修补的低频明暗，羽化边缘。输出 assets/gen/R6_C/c22_wall_noframe_raw.png。"""
import cv2, numpy as np
ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/assets/gen/'
im = cv2.imread(ROOT + 'C5/c22_wall_raw.png', cv2.IMREAD_COLOR).astype(np.float32)
H, W = im.shape[:2]
POLY = {
    'L': [(468, 928), (634, 914), (598, 1068), (458, 1072)],
    'C': [(1046, 712), (1370, 702), (1372, 1030), (1044, 1036)],
    'R': [(1936, 780), (2176, 762), (2254, 974), (2004, 988)],
}
BAY = {   # 每块框所在的墙面开间（两根壁柱之间、墙顶以下、礁石以上）；来源只许在开间内取，免得拷到天/水/柱子
    'L': [(560, 690), (840, 610), (850, 1165), (395, 1170)],
    'C': [(1048, 545), (1490, 505), (1495, 1095), (1046, 1105)],
    'R': [(1815, 440), (2240, 380), (2370, 1085), (2005, 1090)],
}
allm = np.zeros((H, W), np.uint8)
masks = {}
for k, p in POLY.items():
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.array(p, np.int32)], 255)
    m = cv2.dilate(m, np.ones((23, 23), np.uint8))
    masks[k] = m; allm |= m
excl = cv2.dilate(allm, np.ones((41, 41), np.uint8))
gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
hp = gray - cv2.GaussianBlur(gray, (0, 0), 6)
lo_fill = cv2.inpaint(np.clip(im, 0, 255).astype(np.uint8), cv2.dilate(allm, np.ones((21, 21), np.uint8)), 25, cv2.INPAINT_TELEA).astype(np.float32)
lo_fill = cv2.GaussianBlur(lo_fill, (0, 0), 28)
out = im.copy()
for k, m in masks.items():
    bay = np.zeros((H, W), np.uint8); cv2.fillPoly(bay, [np.array(BAY[k], np.int32)], 255)
    okm = (bay > 0) & (excl == 0)
    ys, xs = np.nonzero(m)
    Y0, Y1 = ys.min(), ys.max() + 1
    for yb in range(Y0, Y1, 100):
        mb = np.zeros_like(m); mb[max(Y0, yb - 14):min(Y1, yb + 114)] = m[max(Y0, yb - 14):min(Y1, yb + 114)]
        bys, bxs = np.nonzero(mb)
        y0, y1, x0, x1 = bys.min(), bys.max() + 1, bxs.min(), bxs.max() + 1
        mm = mb[y0:y1, x0:x1] > 0
        ring = (cv2.dilate(mb, np.ones((31, 31), np.uint8)) > 0) & (mb == 0) & (allm == 0)
        ry, rx = np.nonzero(ring)
        sel = np.random.default_rng(yb).choice(len(ry), min(3000, len(ry)), replace=False); ry, rx = ry[sel], rx[sel]
        best = None
        for dy in range(-460, 461, 2):
            for dx in range(-300, 301, 4):
                sy0, sy1, sx0, sx1 = y0 + dy, y1 + dy, x0 + dx, x1 + dx
                if sy0 < 0 or sx0 < 0 or sy1 > H or sx1 > W: continue
                if not okm[sy0:sy1, sx0:sx1][mm].all(): continue
                sy, sx = ry + dy, rx + dx
                if sy.min() < 0 or sy.max() >= H or sx.min() < 0 or sx.max() >= W: continue
                e = np.mean((hp[sy, sx] - hp[ry, rx]) ** 2)
                if best is None or e < best[0]: best = (e, dy, dx)
        if best is None: print(k, yb, 'NO SOURCE'); continue
        e, dy, dx = best
        print(k, yb, 'shift', dy, dx, 'err', round(float(e), 2), flush=True)
        src = im[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
        src_hi = src - cv2.GaussianBlur(src, (0, 0), 28)
        fill = lo_fill[y0:y1, x0:x1] + src_hi
        a = cv2.GaussianBlur(mm.astype(np.float32), (0, 0), 5)[..., None]
        a = np.clip(a * 1.2, 0, 1)
        out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - a) + fill * a
cv2.imwrite(ROOT + 'R6_C/c22_wall_noframe_raw.png', np.clip(out, 0, 255).astype(np.uint8))
print('ok')
