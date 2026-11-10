"""tools/c_peek.py — C 组核帧：按秒渲若干帧存全尺寸 jpg（多帧必须包 cpu_slot）。
用法：V4_FORCE=c_pre2_chorus2 tools/cpu_slot.sh python3 tools/c_peek.py OUTDIR t1 t2 ...（t 为秒，或 f1234 帧号）"""
import os, sys, time
sys.path.insert(0, __import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/units')
from PIL import Image
import sec_c_pre2_chorus2 as M
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
for a in sys.argv[2:]:
    f = int(a[1:]) if a.startswith('f') else round(float(a) * 30)
    t0 = time.time(); im = M.frame(f, {})
    p = f'{out}/f{f}.jpg'; Image.fromarray(im).save(p, quality=90)
    print(p, f'{time.time() - t0:.1f}s', flush=True)
