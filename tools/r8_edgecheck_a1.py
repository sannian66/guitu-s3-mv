"""§11.7 裁切边自查：给 SpriteLayer.draw / r8d_a1.blit 打补丁，把每个图层画布四边上 alpha>0.25 的像素映射到屏幕，
落在可见画幅区（x 0–1920，y 120–960，内缩 3px）里就记一条。用法：python edgecheck.py F0 F1 step"""
import os, sys, math, collections
os.environ['STYLE_D'] = '1'; os.environ['SPRITE_MODE'] = '1'
ROOT = os.environ['MV_ROOT']
for p in (ROOT, ROOT + '/lib', ROOT + '/units'): sys.path.insert(0, p)
import numpy as np, cv2
import sprite as SPm
HITS = collections.defaultdict(lambda: collections.Counter())
CUR = {'f': None, 'sid': None}


def border_pts(A, thr=0.25):
    h, w = A.shape; pts = []
    for name, sl, mk in (('top', A[0], lambda i: (i, 0)), ('bot', A[h - 1], lambda i: (i, h - 1)),
                         ('left', A[:, 0], lambda i: (0, i)), ('right', A[:, w - 1], lambda i: (w - 1, i))):
        idx = np.nonzero(sl > thr)[0]
        if len(idx): pts.append((name, np.array([mk(i) for i in idx[::4]], np.float32)))
    return pts


def check(A, M, tag):
    for name, P in border_pts(A):
        Q = P @ M[:, :2].T + M[:, 2]
        inside = (Q[:, 0] > 3) & (Q[:, 0] < 1917) & (Q[:, 1] > 123) & (Q[:, 1] < 957)
        n = int(inside.sum())
        if n: HITS[(CUR['sid'], tag, name)][CUR['f']] = n


_orig = SPm.SpriteLayer.draw
def draw(self, fr, t, anchor_src, anchor_dst, scale, rot=0.0, breathe=0.005, *a, **k):
    s = scale * (1 + breathe * math.sin(2 * math.pi * t / 3.4))
    ax, ay = anchor_src[0] * self.w, anchor_src[1] * self.h
    M = cv2.getRotationMatrix2D((ax, ay), rot, s); M[0, 2] += anchor_dst[0] - ax; M[1, 2] += anchor_dst[1] - ay
    check(self.A, M, 'spr%dx%d#%d' % (self.w, self.h, int(self.A.sum()) % 99991))
    return _orig(self, fr, t, anchor_src, anchor_dst, scale, rot, breathe, *a, **k)
SPm.SpriteLayer.draw = draw

import sec_a_intro_verse1 as SA
import r8d_a1 as R
_ob = R.blit
def blit(fr, P, A, Mx, *a, **k):
    check(A, np.asarray(Mx, np.float64), 'blit%dx%d#%d' % (A.shape[1], A.shape[0], int(A.sum()) % 99991))
    return _ob(fr, P, A, Mx, *a, **k)
R.blit = blit
f0, f1, st = map(int, sys.argv[1:4])
sec = SA.Section()
for f in range(f0, f1, st):
    t = f / 30; CUR['f'] = f; CUR['sid'] = sec.ids[sec.idx(t)]
    sec.raw(t)
for key, c in sorted(HITS.items(), key=lambda x: str(x[0])):
    fs = sorted(c)
    print(key, 'frames', fs[0], '..', fs[-1], 'n', len(fs), 'maxpts', max(c.values()), flush=True)
print('DONE')
