import sys,time; sys.path.insert(0,'/workspace/work/mv/lib')
import numpy as np, cv2, rig
cells=[]
def bgf(w=480,h=540,glow=True):
    yy,xx=np.mgrid[0:h,0:w]; d=np.sqrt((xx-w/2)**2+(yy-h*0.35)**2)/w
    b=np.full((h,w,3),0.03,np.float32)+ (np.exp(-d*d*8)*0.6)[...,None]*np.array([1,0.76,0.4],np.float32)
    return b.astype(np.float32)
rows=[]
for act,view,kw in [('stand_backlit','front',{}),('raise_hand_decree','front',{}),('point_down','3q',{}),('grip_scepter','front',{}),('head_turn_flash','front',{}),('stand_backlit','front',dict(paper=1.0))]:
    em=rig.Emperor(1,view=view); row=[]
    N=36
    for f in range(N):
        p=f/(N-1); em.pose(act,p,f/30,wind=120)
        if f in (0,12,24,35):
            fr=bgf(); a=time.time()
            burn = (f/35)*0.9 if 'paper' in kw else 0
            fr,_=em.draw(fr,240,525,500,rim_color=(1,0.8,0.5),rim_dir=(0,-1),burn=burn,**kw); dt=time.time()-a
            f8=np.clip(fr*255,0,255).astype(np.uint8); cv2.putText(f8,'%s %.2f %.3fs'%(act,p,dt),(5,16),cv2.FONT_HERSHEY_SIMPLEX,0.42,(255,255,255),1)
            row.append(f8)
    rows.append(np.hstack(row))
img=np.vstack([np.hstack(rows[i:i+2]) for i in range(0,6,2)])
cv2.imwrite('/workspace/work/mv/lib/rig_test/emperor.png',img[:,:,::-1])
