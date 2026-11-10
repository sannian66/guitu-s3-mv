import sys,time; sys.path.insert(0,__import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/lib')
import numpy as np, cv2, rig
def bg():
    g=np.linspace(0.30,0.12,1080)[:,None,None]*np.ones((1,1920,3),np.float32); return g.astype(np.float32)
fr=bg()
cfg=[('side',300,False,450),('side',-300,False,1000),('back',300,False,1550)]
for view,wind,fl,x in cfg:
    sw=rig.Swordsman(1,view=view)
    for k in range(40): sw.pose('stand_wind',k/90,k/30,wind=wind,flip=fl)
    a=time.time(); fr,_=sw.draw(fr,x,1000,780,rim_color=(0.9,0.92,1),rim_dir=(-0.8,-0.6)); print(time.time()-a)
cv2.imwrite(__import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/lib/rig_test/t1.png',np.clip(fr[:,:,::-1]*255,0,255).astype(np.uint8))
