"""r6-SPRITE 逐像素对拍：python3 crew/round6/eng_r6_diff.py a.png b.png [heat.jpg]
输出 max/mean（/255）、>2 的像素数、最大差位置与超限像素包围盒；可选存差异热图（×20 放大，≤1000 宽）。"""
import sys, json
import numpy as np
from PIL import Image
a = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(np.int16)
b = np.asarray(Image.open(sys.argv[2]).convert('RGB')).astype(np.int16)
d = np.abs(a - b).max(-1)
y, x = np.unravel_index(int(d.argmax()), d.shape)
over = np.nonzero(d > 2)
rec = dict(a=sys.argv[1], b=sys.argv[2], max=int(d.max()), mean=round(float(np.abs(a - b).mean()), 5),
           n_gt0=int((d > 0).sum()), n_gt2=int((d > 2).sum()), argmax_xy=[int(x), int(y)],
           over_bbox=[int(over[1].min()), int(over[0].min()), int(over[1].max()), int(over[0].max())] if len(over[0]) else None)
print(json.dumps(rec, ensure_ascii=False))
if len(sys.argv) > 3:
    h = np.clip(d * 20, 0, 255).astype(np.uint8)
    im = Image.fromarray(h).convert('RGB'); im.thumbnail((1000, 1000)); im.save(sys.argv[3], quality=90)
