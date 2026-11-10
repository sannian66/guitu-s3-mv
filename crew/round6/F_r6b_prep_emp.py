"""F组 r6 第二棒 #21：emp_flat_a_cut → emp_flat_a_f_cut（冕板压薄、alpha 收边羽化、脸压暗、龙纹提饱和与局部对比）"""
import numpy as np, cv2
from PIL import Image
R = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/assets/gen/R6_F/'
im = np.asarray(Image.open(R + 'emp_flat_a_cut.png').convert('RGBA')).astype(np.float32) / 255
h, w = im.shape[:2]
# 1) 冕板（y 60–126，约 66px 厚）纵向压到 44px：板厚上屏 ≈18px
top, bot, newtop = 58, 127, 83
band = im[top:bot]
band = cv2.resize(band, (w, bot - newtop), interpolation=cv2.INTER_AREA)
out = im.copy(); out[:bot] = 0; out[newtop:bot] = band
im = out
rgb, A = im[..., :3], im[..., 3]
# 2) alpha 收 2px + 羽化 σ3（去冕板顶边/肩线的抠像亮边）
A = cv2.erode(A, np.ones((5, 5), np.uint8)); A = cv2.GaussianBlur(A, (0, 0), 3.0)
# 3) 脸 / 颈压暗（逆光：正脸不该是全画面最亮处），胸以下不动
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
face = np.exp(-(((xx - 1042) / 330) ** 2 + ((yy - 760) / 360) ** 2))
rgb = rgb * (1 - 0.32 * face)[..., None]
# 4) 龙纹：胸肩区饱和 ×1.6、局部对比 ×1.35
chest = np.clip((yy - 1150) / 250, 0, 1)[..., None]
lum = rgb.mean(-1, keepdims=True)
sat = lum + (rgb - lum) * 1.6
loc = cv2.GaussianBlur(sat, (0, 0), 18)
con = loc + (sat - loc) * 1.35
rgb = np.clip(rgb * (1 - chest) + con * chest, 0, 1)
Image.fromarray((np.dstack([rgb, A]) * 255 + 0.5).astype(np.uint8)).save(R + 'emp_flat_a_f_cut.png')
print('ok')
