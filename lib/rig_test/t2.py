import sys,time; sys.path.insert(0,'/workspace/work/mv/lib')
import numpy as np, cv2, rig
fr=(np.linspace(0.30,0.12,1080)[:,None,None]*np.ones((1,1920,3))).astype(np.float32)
# head CU: side, wind from front
for i,(view,wind,x) in enumerate([('side',-200,500),('back',60,1400)]):
    sw=rig.Swordsman(1,view=view,hair=2.5)
    for k in range(40): sw.pose('stand_wind',k/90,k/30,wind=wind)
    fr,_=sw.draw(fr,x,1080+2600,3400,rim_color=(0.9,0.92,1),rim_dir=(-0.8,-0.6),glint=1.0)
cv2.imwrite('/workspace/work/mv/lib/rig_test/t2.png',np.clip(fr[:,:,::-1]*255,0,255).astype(np.uint8))
