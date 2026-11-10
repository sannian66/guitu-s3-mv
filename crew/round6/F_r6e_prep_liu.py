"""F组 r6 第五棒 #21（评审 REVIEW_F_r6d 打回：鬼珠串 / 克隆补丁 / 脸灰糊 / 分旒跳变）
不再用同行克隆补脸，改用 (a) 同人无旒生图 emp_flat_a 换脸：emp_liu_a 本就是以 emp_flat_a 为 ref 编辑出来的，两张实测对位误差 <1px
（phaseCorrelate −0.71, +0.17），冠身金纹、发际、五官全部重合。
输出（全部 2048² RGBA，源像素坐标与 emp_liu_a 一致）：
  emp_liu_e_plate_cut.png      底板：三条要挪的旒（源 x862 / x1084 / x1185）所在竖带整条换成 emp_flat_a（低频亮度匹配、σ4 羽化），
                              其余五串旒保持生图原样；皮肤 AI 龟裂纹局部平滑；眉骨上沿、鼻梁上沿烘一道冷月逆光轮廓
  emp_liu_e_s{862,1084,1185}_cut.png  三串旒各自独立图层（原位），珠芯 alpha=1、串线 ≥0.9，边缘 1px 羽化
渲染时（units/chorus1_sprites.py S031Sprite，开关 R6F_E=0 回第四棒）按时间把三串做「以冕板前沿为支点的摆」位移插值。"""
import numpy as np, cv2
from PIL import Image
R = '/workspace/work/mv/assets/gen/R6_F/'
ld = lambda n: np.asarray(Image.open(R + n).convert('RGBA')).astype(np.float32) / 255
L4 = ld('emp_liu_a_cut.png'); F4 = ld('emp_flat_a_cut.png')
h, w = L4.shape[:2]
Mf = np.float32([[1, 0, -0.71], [0, 1, 0.17]])                         # flat → liu 亚像素对位
F4 = cv2.warpAffine(F4, Mf, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
liu, A0 = L4[..., :3], L4[..., 3]
flat = F4[..., :3]
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
lum = liu.mean(-1); sat = liu.max(-1) - liu.min(-1)

# ---- 玉珠 / 串线遮罩（亮、低饱和，且与无旒图差异大）
diff = np.abs(liu - flat).mean(-1)
bead = np.clip((lum - 0.58) / 0.10, 0, 1) * np.clip((0.13 - sat) / 0.05, 0, 1) * np.clip((diff - 0.04) / 0.06, 0, 1)   # 苍白额头也亮而低饱和，必须与无旒图有差异才算珠
near = cv2.dilate((bead > 0.5).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(np.float32)   # 只在珠芯 3px 内补珠子暗侧
bead = np.maximum(bead, np.clip((diff - 0.10) / 0.08, 0, 1) * np.clip((lum - 0.30) / 0.1, 0, 1) * near)
bead *= (yy > 118) * (yy < 790)
TOPY = 118
XS = (862, 1084, 1185)
# 每串的实际中线（逐 40 行找珠子质心，防止串略斜）
def centerline(x0):
    cs = []
    for y0 in range(TOPY, 780, 40):
        sl = bead[y0:y0 + 40, x0 - 22:x0 + 23]
        m = sl.sum(0)
        cs.append((y0 + 20, x0 - 22 + (m * np.arange(45)).sum() / max(m.sum(), 1e-3)) if m.sum() > 3 else (y0 + 20, x0))
    cs = np.array(cs)
    return np.interp(np.arange(h), cs[:, 0], cs[:, 1])
strand, band = {}, {}
for x0 in XS:
    cx = centerline(x0)[:, None]
    col = np.clip((19 - np.abs(xx - cx)) / 3, 0, 1)                     # 珠宽 ≈28px → ±19 带 3px 软边
    m = bead * col
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 3), np.uint8))   # 连上珠间串线
    m = np.clip(cv2.GaussianBlur(m, (0, 0), 0.8) * 1.6, 0, 1) * col * (yy > TOPY)
    strand[x0] = m
    b = np.clip((24 - np.abs(xx - cx)) / 4, 0, 1) * np.clip((yy - (TOPY - 6)) / 6, 0, 1) * np.clip((800 - yy) / 10, 0, 1)
    band[x0] = cv2.GaussianBlur(b.astype(np.float32), (0, 0), 2.0)
B = np.clip(sum(band.values()), 0, 1)

# ---- 底板：竖带内换成 emp_flat_a，低频亮度/色彩匹配（排除所有玉珠的归一化卷积，σ14）
allbead = cv2.dilate(bead, np.ones((7, 7), np.uint8))
wv = (1 - np.clip(allbead, 0, 1)) * (A0 > 0.5)
def nblur(img, s=14):
    num = cv2.GaussianBlur(img * wv[..., None], (0, 0), s); den = cv2.GaussianBlur(wv, (0, 0), s)[..., None]
    return num / np.maximum(den, 1e-3)
ratio = np.clip((nblur(liu) + 0.01) / (nblur(flat) + 0.01), 0.7, 1.4)
fill = np.clip(flat * ratio, 0, 1)
plate = liu * (1 - B[..., None]) + fill * B[..., None]

# ---- 处理（沿用 F_r6c 的逆光压脸 / 龙纹提色，脸压暗 0.32 → 0.20，交给成片 grade 控暗部）
def process(rgb, beadm, face_k=0.20):
    bd = cv2.GaussianBlur(beadm.astype(np.float32), (0, 0), 2)
    face = np.exp(-(((xx - 1042) / 330) ** 2 + ((yy - 760) / 360) ** 2))
    rgb = rgb * (1 - (face_k * face * (1 - 0.6 * bd)))[..., None]
    rgb = rgb * (1 - 0.12 * bd)[..., None] + bd[..., None] * np.array([-0.01, 0.0, 0.01], np.float32)
    chest = np.clip((yy - 1150) / 250, 0, 1)[..., None]
    l3 = rgb.mean(-1, keepdims=True); s3 = l3 + (rgb - l3) * 1.6
    loc = cv2.GaussianBlur(s3, (0, 0), 18); con = loc + (s3 - loc) * 1.35
    return np.clip(rgb * (1 - chest) + con * chest, 0, 1)
mov = np.clip(sum(strand.values()), 0, 1)
plate_bead = np.clip(bead * (1 - B) , 0, 1)                              # 底板上仍留着的玉珠
plate = process(plate, plate_bead)
liu_p = process(liu, bead)

# ---- 皮肤：AI 龟裂纹局部平滑（只压 σ≈3.5 源像素以下的细纹，≈成片 σ1.5；五官大结构保留）
pl = plate.mean(-1)
skin = (np.clip((plate[..., 0] - plate[..., 2] - 0.005) / 0.03, 0, 1) * np.clip((pl - 0.20) / 0.08, 0, 1)
        * np.exp(-(((xx - 1042) / 300) ** 2 + ((yy - 760) / 330) ** 2) ** 2) * (1 - np.clip(plate_bead * 3, 0, 1)))
skin = cv2.GaussianBlur(skin.astype(np.float32), (0, 0), 3)
low = cv2.bilateralFilter(plate.astype(np.float32), 9, 0.10, 4)
low = cv2.GaussianBlur(low, (0, 0), 1.2)
# 结构保护：σ6 尺度的梯度大（眼睑、眉、鼻翼、唇线）少平滑
g6 = cv2.GaussianBlur(pl, (0, 0), 3)
gm = np.sqrt(cv2.Sobel(g6, cv2.CV_32F, 1, 0, ksize=5) ** 2 + cv2.Sobel(g6, cv2.CV_32F, 0, 1, ksize=5) ** 2)
prot = np.clip((gm - 0.5) / 1.0, 0, 1)
k = (skin * (0.85 - 0.55 * prot))[..., None]
plate = plate * (1 - k) + low * k

# ---- 冷月逆光轮廓：眉骨上沿（两条眉弓）+ 鼻梁上沿（亮面朝上 = 下方比上方暗的地方），只在脸上、只加冷白
pg = cv2.GaussianBlur(plate.mean(-1), (0, 0), 2.5)
up = np.clip((pg - np.roll(pg, -7, 0)) / 0.06, 0, 1)                   # 本像素比 7px 下方亮 → 朝上的面
brow = (np.exp(-(((xx - 935) / 85) ** 2 + ((yy - 598) / 22) ** 2)) + np.exp(-(((xx - 1150) / 85) ** 2 + ((yy - 598) / 22) ** 2)))
nose = np.exp(-(((xx - 1042) / 16) ** 2)) * np.clip((yy - 640) / 30, 0, 1) * np.clip((805 - yy) / 40, 0, 1)
rimm = cv2.GaussianBlur((up * brow + 0.55 * nose * (0.5 + 0.5 * up)).astype(np.float32), (0, 0), 1.5) * (1 - np.clip(plate_bead * 3, 0, 1))
plate = np.clip(plate + rimm[..., None] * np.array([0.16, 0.18, 0.21], np.float32), 0, 1)

# ---- alpha 同 F_r6c：收边羽化
A = cv2.erode(A0, np.ones((3, 3), np.uint8)); A = cv2.GaussianBlur(A, (0, 0), 1.6)
sv = lambda a, n: Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).save(R + n)
sv(np.dstack([plate, A]), 'emp_liu_e_plate_cut.png')
for x0 in XS:
    m = strand[x0]
    sv(np.dstack([liu_p, m]), f'emp_liu_e_s{x0}_cut.png')
    core = m[strand[x0] > 0.05]
    print('strand', x0, 'alpha p10/p50 of covered', np.percentile(core, 10).round(3), np.percentile(core, 50).round(3))
print('ok')
