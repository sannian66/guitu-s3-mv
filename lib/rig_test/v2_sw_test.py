import sys, time; sys.path.insert(0, '/workspace/work/mv/lib')
import numpy as np, cv2, rig
def bg(h=1080, w=1920): return (np.linspace(0.30, 0.10, h)[:, None, None] * np.ones((1, w, 3))).astype(np.float32)
def scene(q):
    rig.set_quality(q); fr = bg(); T = []
    for view, wind, x, act, ph in [('side', 300, 330, 'stand_wind', 0.3), ('3q', -300, 800, 'slash_diag', 0.45), ('front3q', 200, 1250, 'draw_sword', 0.6), ('back', 300, 1650, 'stand_wind', 0.2)]:
        sw = rig.Swordsman(1, view=view)
        for k in range(40): sw.pose(act, min(ph, k / 40 * ph * 1.5), k / 30, wind=wind)
        a = time.time(); fr, _ = sw.draw(fr, x, 1010, 820, rim_color=(0.9, 0.92, 1), rim_dir=(-0.8, -0.6)); T.append(time.time() - a)
    return fr, T
to8 = lambda f: np.clip(f * 255, 0, 255).astype(np.uint8)
a, Ta = scene('v1'); b, Tb = scene('v2')
print('v1', ['%.3f' % t for t in Ta], 'v2', ['%.3f' % t for t in Tb])
img = to8(np.vstack([a, b]))
cv2.putText(img, 'v1', (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3); cv2.putText(img, 'v2', (20, 1130), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
cv2.imwrite('/tmp/rt/sw_cmp.jpg', cv2.resize(img, (1920, 2160))[:, :, ::-1])
z = to8(b[150:1030, 600:1100]); cv2.imwrite('/tmp/rt/sw_zoom.png', cv2.resize(z, None, fx=1.5, fy=1.5)[:, :, ::-1])
