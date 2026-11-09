"""A 组逐镜试渲：每镜中点(或指定时刻)一帧，捕获报错与耗时。python3 tools/a_test.py [镜名...]"""
import os, sys, time, traceback
ROOT = '/workspace/work/mv'; sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + '/units'); sys.path.insert(0, ROOT + '/lib')
os.chdir(ROOT)
import numpy as np
from PIL import Image
import sec_a_intro_verse1 as M
names = sys.argv[1:]
cache = {}
sec = M.Section(); cache['sec'] = sec
for S in M.SHOTS:
    if names and S.__name__ not in names: continue
    for fr_ in (0.15, 0.55, 0.92):
        t = S.t0 + fr_ * (S.t1 - S.t0); f = int(round(t * 30))
        a = time.time()
        try:
            im = M.frame(f, cache)
            Image.fromarray(im).resize((960, 540)).save(f'/tmp/at_{S.__name__}_{fr_}.jpg')
            print(S.__name__, fr_, round(t, 2), 'OK', round(time.time() - a, 2), flush=True)
        except Exception as e:
            print(S.__name__, fr_, round(t, 2), 'ERR', type(e).__name__, e, flush=True)
            traceback.print_exc(limit=-3)
            break
