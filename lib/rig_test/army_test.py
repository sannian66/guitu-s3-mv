import sys,time; sys.path.insert(0,'/workspace/work/mv/lib')
import numpy as np, cv2, crowd, fx2
from crowd import W,H
def sky(t, moon=(1500,260)):
    fr=np.linspace(0.13,0.05,H)[:,None,None]*np.ones((1,W,3),np.float32)
    cl=cv2.resize(fx2.noise(512,4,base=3,octaves=6),(W,H)); fr=fr+((cl-0.5)*0.06)[...,None]
    cv2.circle(fr,moon,70,(0.85,0.87,0.9),-1,cv2.LINE_AA)
    fr=fx2.god_rays(fr,moon,strength=0.4,color=fx2.COLD,t=t,src_r=70)
    # ground
    g=np.linspace(0,1,H)[:,None]; gm=(g>0.48).astype(np.float32)
    fr=fr*(1-gm[...,None]*0.75)+(gm*0.04)[...,None]
    return fr.astype(np.float32)
fog=fx2.Fog(2)
cells=[]; T=[]
t0=time.time(); A=crowd.Army(1); print('init',time.time()-t0)
A2=crowd.Army(2,rows=8,cols=12,view='side',banners=3,torches=0)
shots=[
 ('S009 ELS top 500 march', dict(cam=dict(x=0,y=26,z=-14,pitch=32,f=1400), t=1.0, kw=dict(advance=0))),
 ('S009 push in', dict(cam=dict(x=0,y=20,z=-4,pitch=30,f=1500), t=1.5, kw=dict(advance=0.6))),
 ('S010 front rank low', dict(cam=dict(x=1.5,y=1.4,z=4,pitch=-4,f=1500), t=2.0, kw=dict(advance=0, march=0, focus=14))),
 ('raise blades', dict(cam=dict(x=0,y=5,z=-6,pitch=10,f=1500), t=3.0, kw=dict(raise_=1.0,march=0))),
 ('kneel wave 0.5', dict(cam=dict(x=0,y=4,z=-2,pitch=8,f=1500), t=3.0, kw=dict(kneel=0.5,march=0,rim_color=fx2.GOLD))),
 ('kneel + part (S122)', dict(cam=dict(x=0,y=2.2,z=2,pitch=2,f=1300), t=3.0, kw=dict(kneel=1.0,part=1.0,march=0,rim_color=fx2.GOLD))),
]
for name,sh in shots:
    fr=sky(sh['t'])
    a=time.time(); fr,info=A.draw(fr,sh['t'],cam=sh['cam'],**sh['kw']); dt=time.time()-a; T.append(dt)
    fr=fog.draw(fr,sh['t'],0.45,y0=560,y1=1000,light=(1500,400))
    f8=np.clip(fr*255,0,255).astype(np.uint8); cv2.putText(f8,'%s %.2fs'%(name,dt),(30,160),cv2.FONT_HERSHEY_SIMPLEX,2,(255,255,255),3)
    cells.append(cv2.resize(f8,(960,540),interpolation=cv2.INTER_AREA))
fr=sky(1)
a=time.time(); fr,_=A2.draw(fr,1.2,cam=dict(x=0,y=1.8,z=-2,pitch=3,f=1400),origin=(-3,0,7),march=1,cadence=2.0,level=1.0,advance=0); dt=time.time()-a
f8=np.clip(fr*255,0,255).astype(np.uint8); cv2.putText(f8,'side charge %.2fs'%dt,(30,160),cv2.FONT_HERSHEY_SIMPLEX,2,(255,255,255),3)
cells.append(cv2.resize(f8,(960,540),interpolation=cv2.INTER_AREA))
fr=sky(1,(960,300)); K=crowd.Kneelers(3,n=28,scale=(0.55,0.8))
a=time.time(); fr=K.draw(fr,1.0,bow=0.6,rim_color=fx2.GOLD); dt=time.time()-a
f8=np.clip(fr*255,0,255).astype(np.uint8); cv2.putText(f8,'kneelers %.2fs'%dt,(30,160),cv2.FONT_HERSHEY_SIMPLEX,2,(255,255,255),3)
cells.append(cv2.resize(f8,(960,540),interpolation=cv2.INTER_AREA))
img=np.vstack([np.hstack(cells[i:i+2]) for i in range(0,8,2)])
cv2.imwrite('/workspace/work/mv/lib/rig_test/army_sheet.jpg',img[:,:,::-1],[cv2.IMWRITE_JPEG_QUALITY,88])
print(T)
