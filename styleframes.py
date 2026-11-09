import numpy as np, cv2, random
from fx import *
random.seed(2); np.random.seed(2)
A = '/workspace/work/mv/art/'
out = '/workspace/work/mv/sf/'
import os; os.makedirs(out, exist_ok=True)

def warm_embers(fr, n, it, seed):
    e = Embers(n, seed)
    for k in range(30): e.p += e.v * 0.03
    return e.draw(fr, 1.0, 0.0, it)

# 1 title
img = load_art(A + 'k01_night_blade.png')
fr = camera(img, 0.3, 1.0, 1.08, pan=(0.3, 0))
fr *= 0.8
fr = warm_embers(fr, 90, 0.7, 1)
rgb, al = text_layer('谁定正邪', F_BRUSH, 230, [1] * 4, spacing=0.12, pos=(0.62, 0.36))
fr = comp_text(fr, rgb, al, shadow=0.7)
rgb, al = text_layer('鬼屠 · 片头主题曲', F_SERIF, 34, [1] * 20, spacing=0.35, pos=(0.62, 0.52), color=(0.75, 0.72, 0.68))
fr = comp_text(fr, rgb, al, shadow=0.5)
fr = seal(fr, '鬼屠', x=0.905, y=0.255, size=46)
fr = slash(fr, 0.75, angle=-6, cy=0.6, width=0.5)
cv2.imwrite(out + 'sf1_title.jpg', to8(finish(fr))[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92])

# 2 verse
img = load_art(A + 'k02_army.png')
fr = camera(img, 0.5, 1.0, 1.1)
r = Rain(); 
for _ in range(3): fr = r.draw(fr, 0.016, 0.5)
line = '五百重甲拦不住一道寒光'
rev = [1] * 9 + [0.55, 0.2]
fr = under_grad(fr, 0.55, 0.5)
rgb, al = text_layer(line, F_BRUSH, 86, rev, pos=(0.5, 0.8), red_idx=())
fr = comp_text(fr, rgb, al)
fr = slash(fr, 0.6, angle=-14, cy=0.62, width=0.8)
cv2.imwrite(out + 'sf2_verse.jpg', to8(finish(fr, ca=1))[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92])

# 3 prechorus vertical
img = load_art(A + 'k04_ledger.png')
fr = camera(img, 0.6, 1.05, 1.15, pan=(-0.2, 0.1)) * 0.85
rgb, al = text_layer('谁配写生死簿', F_BRUSH, 92, [1] * 6, vertical=True, pos=(0.86, 0.5))
fr = comp_text(fr, rgb, al)
rgb, al = text_layer('谁配画善恶框', F_BRUSH, 92, [1, 1, 1, 1, 0.6, 0.15], vertical=True, pos=(0.78, 0.55), red_idx=(4, 5))
fr = comp_text(fr, rgb, al)
cv2.imwrite(out + 'sf3_prechorus.jpg', to8(finish(fr))[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92])

# 4 chorus
img = load_art(A + 'k05_cleave_wall.png')
fr = camera(img, 0.5, 1.08, 1.08, shake=0.5)
fr = glow(fr, 0.65, 0.7)
fr = warm_embers(fr, 220, 1.2, 4)
fr = under_grad(fr, 0.5, 0.7)
rgb, al = text_layer('血未冷 刀不放', F_BRUSH, 150, [1] * 7, spacing=0.08, pos=(0.5, 0.74), red_idx=(0,))
fr = comp_text(fr, rgb, al, glowamt=0.35)
cv2.imwrite(out + 'sf4_chorus.jpg', to8(finish(fr, ca=3, grain_amt=0.06))[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92])
print('ok')
