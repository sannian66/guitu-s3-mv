"""副歌一关键帧抽取：python v2_shots.py tag  → /tmp/rt/<tag>_<shot>.png ；env RIGV1=1 用 v1 基线 rig"""
import sys, os, time
sys.path[:0] = [__import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/units', __import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/lib', __import__('os').environ.get('MV_ROOT', '/workspace/work/mv')]
if os.environ.get('RIGV1'):
    sys.path.insert(0, __import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/lib/rig_test')
    import rig_v1_baseline as R; sys.modules['rig'] = R
os.environ.setdefault('C1_RIG', 'live')
import numpy as np, cv2
import chorus1 as C
tag = sys.argv[1]
TS = dict(S029=60.95, S035=70.45, S038=74.5, S043=82.6, S044=83.7, S045=84.62)
only = sys.argv[2].split(',') if len(sys.argv) > 2 else list(TS)
X = C.Chorus1()
for sid in only:
    t = TS[sid]
    # 预跑布料：递增 t
    for k in range(8, 0, -1): X.raw(t - k / 30)
    a = time.time(); fr, _ = X.frame(t); dt = time.time() - a
    cv2.imwrite(f'/tmp/rt/{tag}_{sid}.png', np.clip(fr[..., ::-1] * 255, 0, 255).astype(np.uint8))
    print(sid, t, '%.2fs' % dt, flush=True)
