import sys,time; sys.path.insert(0,'/workspace/work/mv/lib')
import numpy as np, cv2, crowd, fx2
from crowd import W,H
# 1) sprite sheet
cells=[]
for kw in [dict(phase=0),dict(phase=0.25),dict(phase=0.75),dict(phase=None,arm=1.0),dict(phase=None,level=1.0),dict(phase=None,arm=1.0,weapon='dao'),
           dict(phase=None,kneel=1.0,bow=0.8),dict(phase=0.2,view='side'),dict(phase=0.6,view='side',weapon='dao',arm=0.5)]:
    sp=crowd.soldier_sprite(**kw)
    A,B,R=sp['A'],sp['base'],sp['rim']
    cell=np.full((760,520,3),0.22,np.float32)
    C=B+R[...,None]*crowd.COLD
    h,w=A.shape; y0=740-int(sp['foot'][1]); x0=260-int(sp['foot'][0])
    ya,xa=max(0,y0),max(0,x0); hb,wb=min(760,y0+h),min(520,x0+w)
    a=A[ya-y0:hb-y0,xa-x0:wb-x0,None]; cell[ya:hb,xa:wb]=cell[ya:hb,xa:wb]*(1-a)+C[ya-y0:hb-y0,xa-x0:wb-x0]*a
    cells.append(cell)
for b in (0,0.5,1.0):
    sp=crowd.civ_sprite(1.0,b,rim_dir=(0.3,-1)); A,B,R=sp['A'],sp['base'],sp['rim']; cell=np.full((760,520,3),0.22,np.float32)
    C=B+R[...,None]*crowd.GOLD; h,w=A.shape; y0=740-int(sp['foot'][1]); x0=260-int(sp['foot'][0])
    a=A[...,None]; cell[y0:y0+h,x0:x0+w]=cell[y0:y0+h,x0:x0+w]*(1-a)+C*a; cells.append(cell)
img=np.vstack([np.hstack(cells[i:i+6]) for i in range(0,12,6)])
cv2.imwrite('/workspace/work/mv/lib/rig_test/crowd_sprites.jpg',np.clip(img[:,:,::-1]*255,0,255).astype(np.uint8))
