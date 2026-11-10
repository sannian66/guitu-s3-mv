"""F组 r6 第四棒 #21：生图冕旒「分旒」——从 emp_liu_a_f_cut（生图，自带玉珠前旒）里把画面左眼两侧的两串旒和右眼前一串
抠成独立图层（亮度高、饱和低 = 玉珠；按串所在列 ±24px 限定），原位 cv2.inpaint 补脸，再按「以冕板前沿为支点的摆」
（位移随下垂长度线性增大）把这几串挪到不同位置，出 4 档精灵：
  c0 合旒：左眼前两串向眼心合拢（862→+80、1084→−110），右眼前一串 1185→−28，双眼都沉在旒后
  c1 / c2 过渡（风起分旒）
  c3 分旒：左两串向外分开（862→−46、1084→+26），露出画面左眼；右眼仍在旒后
冕旒仍是生图玉珠本身（只做整体平移/摆），不新画任何珠子。"""
import numpy as np, cv2
from PIL import Image
R = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/assets/gen/R6_F/'
src = np.asarray(Image.open(R + 'emp_liu_a_f_cut.png').convert('RGBA')).astype(np.float32) / 255
raw = np.asarray(Image.open(R + 'emp_liu_a_cut.png').convert('RGB')).astype(np.float32) / 255
h, w = src.shape[:2]
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
lum = raw.mean(-1); sat = raw.max(-1) - raw.min(-1)
bead = np.clip((lum - 0.62) / 0.10, 0, 1) * np.clip((0.09 - sat) / 0.04, 0, 1) * (yy < 840) * (yy > 140)
TOP = 150.0                                   # 冕板前沿（旒的支点）
STR = {862: (80, 0, -36, -46), 1084: (-110, -50, 8, 26), 1185: (-28, -28, -26, -24)}   # 每串在 c0..c3 的末端位移（px，旒底 y≈760 处）
masks = {}
for x0 in STR:
    col = (np.abs(xx - x0) < 24).astype(np.float32)
    m = bead * col
    m = cv2.dilate(m, np.ones((11, 3), np.uint8)); m = cv2.dilate(m, np.ones((3, 5), np.uint8))   # 竖向连珠（串线）+ 横向带上珠子暗侧
    m = np.clip(cv2.GaussianBlur(m, (0, 0), 1.5) * 1.4, 0, 1) * col
    masks[x0] = m
allm = np.clip(sum(masks.values()), 0, 1)
hole = (cv2.dilate(allm, np.ones((5, 5), np.uint8)) > 0.08).astype(np.uint8)
# 补洞：从左右各 ±44px 的同行皮肤/头发克隆纹理（避开别的珠串），羽化拼回——不用 inpaint（会拉成平滑竖带）
holeF = cv2.GaussianBlur(cv2.dilate(allm, np.ones((5, 7), np.uint8)), (0, 0), 2.0)
beadall = cv2.dilate(bead, np.ones((9, 9), np.uint8))
acc = np.zeros_like(src[..., :3]); wsum = np.zeros((h, w), np.float32)
for sx in (-44, 44, -60, 60):
    Msh = np.float32([[1, 0, sx], [0, 1, 0]])
    c = cv2.warpAffine(src[..., :3], Msh, (w, h), borderMode=cv2.BORDER_REFLECT)
    ok = 1 - np.clip(cv2.warpAffine(beadall, Msh, (w, h)), 0, 1)
    acc += c * ok[..., None]; wsum += ok
fill = acc / np.maximum(wsum, 1e-3)[..., None]
plate = src[..., :3] * (1 - holeF[..., None]) + fill * holeF[..., None]
Ap = src[..., 3].copy()
for k in range(4):
    out = plate.copy(); A = Ap.copy()
    for x0, d in STR.items():
        D = d[k]
        dx = D * np.clip((yy - TOP) / (760 - TOP), 0, 1.15)                  # 摆：支点不动，越往下位移越大
        mapx = (xx - dx).astype(np.float32); mapy = yy
        m = cv2.remap(masks[x0], mapx, mapy, cv2.INTER_LINEAR)
        c = cv2.remap(src[..., :3], mapx, mapy, cv2.INTER_LINEAR)
        out = out * (1 - m[..., None]) + c * m[..., None]
        A = np.maximum(A, m)
    Image.fromarray((np.dstack([np.clip(out, 0, 1), A]) * 255 + 0.5).astype(np.uint8)).save(R + f'emp_liu_c{k}_cut.png')
    print('ok', k)
