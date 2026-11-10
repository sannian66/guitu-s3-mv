"""F组 r6 第三棒 #21：生图 emp_liu_a_cut（emp_flat_a 为 ref 的编辑：自然玉珠前旒 + 有厚度/透视的冕板）→ emp_liu_a_f_cut
不再压冕板（板厚、底面暗边、透视都由生图自带）；alpha 轻收边羽化（≈2px）；脸压暗（逆光）但玉珠少压，保住玉白；龙纹提饱和与局部对比"""
import numpy as np, cv2
from PIL import Image
R = '/workspace/work/mv/assets/gen/R6_F/'
im = np.asarray(Image.open(R + 'emp_liu_a_cut.png').convert('RGBA')).astype(np.float32) / 255
h, w = im.shape[:2]
rgb, A = im[..., :3], im[..., 3]
A = cv2.erode(A, np.ones((3, 3), np.uint8)); A = cv2.GaussianBlur(A, (0, 0), 1.6)
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
lum = rgb.mean(-1); sat = rgb.max(-1) - rgb.min(-1)
bead = np.clip((lum - 0.55) / 0.2, 0, 1) * np.clip((0.18 - sat) / 0.1, 0, 1) * (yy < 780) * (yy > 120)
bead = cv2.GaussianBlur(bead.astype(np.float32), (0, 0), 2)
face = np.exp(-(((xx - 1042) / 330) ** 2 + ((yy - 760) / 360) ** 2))
rgb = rgb * (1 - (0.32 * face * (1 - 0.6 * bead)))[..., None]
rgb = rgb * (1 - 0.12 * bead)[..., None] + bead[..., None] * np.array([-0.01, 0.0, 0.01], np.float32)   # 玉珠略降一点，偏冷
chest = np.clip((yy - 1150) / 250, 0, 1)[..., None]
l3 = rgb.mean(-1, keepdims=True)
s3 = l3 + (rgb - l3) * 1.6
loc = cv2.GaussianBlur(s3, (0, 0), 18)
con = loc + (s3 - loc) * 1.35
rgb = np.clip(rgb * (1 - chest) + con * chest, 0, 1)
Image.fromarray((np.dstack([rgb, A]) * 255 + 0.5).astype(np.uint8)).save(R + 'emp_liu_a_f_cut.png')
print('ok')
