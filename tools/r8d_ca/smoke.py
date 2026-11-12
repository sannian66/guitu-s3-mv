"""CA 单元冒烟：同一进程按步长渲 [F0, F1) 每 N 帧（不存图），报错即停，打印镜号与耗时。
用法：MV_ROOT=.. STYLE_D=1 python tools/r8d_ca/smoke.py 3534 4219 3"""
import os, sys, time
ROOT = os.environ['MV_ROOT']; sys.path[:0] = [ROOT, ROOT + '/units', ROOT + '/lib']
import render_sprite_full as R
f0, f1, st = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
cache = {}; a = time.time()
for f in range(f0, f1, st):
    im = R.frame(f, cache)
    assert im.shape == (1080, 1920, 3), im.shape
print('ok', f0, f1, st, f'{(time.time() - a) / len(range(f0, f1, st)):.2f}s/f', flush=True)
