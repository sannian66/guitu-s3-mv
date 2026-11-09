import sys,time; sys.path.insert(0,'/workspace/work/mv/lib')
import numpy as np, cv2, crowd
def cell(sp,col=crowd.COLD,h=760,w=520):
    A,B,R=sp['A'],sp['base'],sp['rim']; c=np.full((h,w,3),0.22,np.float32); C=B+R[...,None]*col
    hh,ww=A.shape; y0=h-20-int(sp['foot'][1]); x0=w//2-int(sp['foot'][0])
    ya,xa=max(0,y0),max(0,x0); yb,xb=min(h,y0+hh),min(w,x0+ww)
    a=A[ya-y0:yb-y0,xa-x0:xb-x0,None]; c[ya:yb,xa:xb]=c[ya:yb,xa:xb]*(1-a)+C[ya-y0:yb-y0,xa-x0:xb-x0]*a; return c
rows=[];TT={}
for be in ('cv','skia'):
    crowd.set_backend(be); cs=[]; t=time.process_time()
    for kw in [dict(phase=0.25),dict(phase=None,arm=1.0,weapon='dao'),dict(phase=None,kneel=1.0,bow=0.8),dict(phase=0.2,view='side')]:
        cs.append(cell(crowd.soldier_sprite(**kw)))
    cs.append(cell(crowd.civ_sprite(1.0,0.5,rim_dir=(0.3,-1)),crowd.GOLD)); TT[be]=time.process_time()-t
    rows.append(np.hstack(cs))
img=np.vstack(rows); z=np.hstack([cv2.resize(rows[0][150:500,90:430],None,fx=2,fy=2,interpolation=cv2.INTER_NEAREST),cv2.resize(rows[1][150:500,90:430],None,fx=2,fy=2,interpolation=cv2.INTER_NEAREST)])
z=cv2.resize(z,(img.shape[1],int(z.shape[0]*img.shape[1]/z.shape[1])))
out=np.clip(np.vstack([img,z])*255,0,255).astype(np.uint8)
cv2.putText(out,'cv2 (top row) %.2fs'%TT['cv'],(20,40),0,1.2,(255,255,255),3); cv2.putText(out,'skia (2nd row) %.2fs'%TT['skia'],(20,800),0,1.2,(255,255,255),3)
cv2.imwrite('skia_cmp_crowd.jpg',out[:,:,::-1],[cv2.IMWRITE_JPEG_QUALITY,90]); print(TT)
