import sys,time; sys.path.insert(0,'/workspace/work/mv/lib')
import numpy as np, cv2, rig
outs=[]
for act,view,ph in [('slash_h','3q',0.46),('slash_diag','side',0.47),('spin_slash','back',0.55),('slash_up','side',0.5)]:
    sw=rig.Swordsman(3,view=view)
    hist=[]
    fr=(np.linspace(0.16,0.05,540)[:,None,None]*np.ones((1,640,3))).astype(np.float32)
    N=int(1.2*30)
    for f in range(N):
        p=f/(N-1)
        sw.pose(act,p,f/30,wind=-120)
        if p>=ph-0.0001:
            break
        # record trail positions without drawing
        tmp=np.zeros((540,640,3),np.float32)
        _,info=sw.draw(tmp,320,500,400,rim=0)
        hist.append((info['guard'],info['tip']))
    t0=time.time()
    fr,info=sw.draw(fr,320,500,400,rim_color=(0.8,0.88,1),rim_dir=(-0.7,-0.6),shine=0.6)
    hist.append((info['guard'],info['tip']))
    fr=rig.blade_trail(fr,hist[-7:],edge_color=(1.0,0.35,0.15))
    print(act,'trail+draw',time.time()-t0)
    outs.append(fr)
img=np.hstack(outs)
cv2.imwrite('/workspace/work/mv/lib/rig_test/trail.png',np.clip(img[:,:,::-1]*255,0,255).astype(np.uint8))
