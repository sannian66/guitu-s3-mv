"""[D组 r5] 多时刻核帧：python3 tools/d_peek.py out.jpg 161.4 162.0 ...（640 宽网格，带秒数标签，含全局字幕）
FULL=1 另存全尺寸 /tmp/d5_<秒>.png。时间按成片秒数，帧 = round(秒×30)。"""
import os, sys
sys.argv[0] = 'x'
ROOT = '/workspace/work/mv'
os.chdir(ROOT); sys.path.insert(0, ROOT)
import numpy as np, cv2
import render_sprite_full as R

out = sys.argv[1]
ts = [float(a) for a in sys.argv[2:]]
cache = {}
tiles = []
for t in ts:
    f = int(round(t * 30))
    im = R.frame(f, cache)
    if os.environ.get('FULL'):
        cv2.imwrite('/tmp/d5_%.2f.png' % t, im[:, :, ::-1])
    s = cv2.resize(im, (640, 360), interpolation=cv2.INTER_AREA)[:, :, ::-1].copy()
    cv2.putText(s, '%.2fs f%d' % (t, f), (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    tiles.append(s)
cols = 3
while len(tiles) % cols: tiles.append(np.zeros_like(tiles[0]))
rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
print('ok', out)
