"""B 组第五轮：批量渲帧 + 拼网格。
  python3 tools/b_r5_shots.py OUT_PREFIX t1 t2 ...      → OUT_PREFIX_<t>.png 每帧 + OUT_PREFIX_grid.jpg
"""
import sys, os
sys.argv_saved = list(sys.argv)
ROOT = '/workspace/work/mv'
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import importlib.util
spec = importlib.util.spec_from_file_location('rsf', ROOT + '/render_sprite_full.py')
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
import cv2, numpy as np


def main():
    pre = sys.argv_saved[1]
    ts = [float(x) for x in sys.argv_saved[2:]]
    cache = {}
    ims = []
    for t in ts:
        f = int(round(t * 30))
        im = R.frame(f, cache)
        p = f'{pre}_{t:.2f}.png'
        cv2.imwrite(p, cv2.cvtColor(im, cv2.COLOR_RGB2BGR))
        sm = cv2.resize(im, (640, 360), interpolation=cv2.INTER_AREA)
        sm = cv2.cvtColor(sm, cv2.COLOR_RGB2BGR)
        cv2.putText(sm, f'{t:.2f}s f{f}', (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        ims.append(sm)
    cols = 3
    while len(ims) % cols: ims.append(np.zeros_like(ims[0]))
    rows = [np.hstack(ims[i:i + cols]) for i in range(0, len(ims), cols)]
    cv2.imwrite(f'{pre}_grid.jpg', np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print('ok', pre)


main()
