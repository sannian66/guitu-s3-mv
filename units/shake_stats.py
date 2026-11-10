"""v2 vs v3 卡点震动量化：python3 units/shake_stats.py → crew/shake_v2_v3.json"""
import sys, json, math
sys.path[:0] = [__import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/units', __import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/lib', __import__('os').environ.get('MV_ROOT', '/workspace/work/mv')]
import numpy as np
import vcam as V2, vcam3 as V3
import chorus1 as C
HM = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/crew/hitmap_c1.json'
c2 = V2.VCam(HM, energy=C.energy); c3 = V3.VCam3(HM, energy=C.energy)
for c in (c2, c3):
    c.hold(C.V(59.13), 59.267); c.hold(84.80, C.V(85.69))
    for S in C.SHOTS: c.moves.append((max(S.t0, 58.5), S.t1, None, C.GAIN.get(S.__name__, 1.0)))
ts = np.arange(1755, 2685) / 30.0
def stats(c):
    I = np.array([c.impulses(t) for t in ts])
    dz, dx, dy, dr = I[:, 0], I[:, 1], I[:, 2], I[:, 3]
    pos = np.hypot(dx, dy)
    jit = np.hypot(np.diff(dx), np.diff(dy))
    active = (np.abs(dz) > 0.003) | (pos > 0.8) | (np.abs(dr) > 0.05)
    return dict(peak_zoom_pct=round(float(np.abs(dz).max() * 100), 2), mean_abs_zoom_pct=round(float(np.abs(dz).mean() * 100), 3),
                peak_shift_px=round(float(pos.max()), 1), rms_shift_px=round(float(np.sqrt((pos ** 2).mean())), 2),
                peak_rot_deg=round(float(np.abs(dr).max()), 2), rms_rot_deg=round(float(np.sqrt((dr ** 2).mean())), 3),
                frame_jitter_px_rms=round(float(np.sqrt((jit ** 2).mean())), 2), frames_shaking_pct=round(float(active.mean() * 100), 1))
s2, s3 = stats(c2), stats(c3)
n2 = dict(kick=len(c2.kicks), snare=len(c2.snares), hat=len(c2.hats), crash=len(c2.crashes), accent=len(c2.accents))
n2['total'] = sum(n2.values())
from collections import Counter
n3 = dict(Counter(e[1] for e in c3.events)); n3['total'] = len(c3.events)
out = dict(window='58.5-89.5s', v2=dict(events=n2, **s2), v3=dict(events=n3, candidates_before_refractory=len(c3.cand_events), **s3))
json.dump(out, open(__import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/crew/shake_v2_v3.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
