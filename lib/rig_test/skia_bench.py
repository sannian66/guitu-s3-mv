import sys,time; sys.path.insert(0,'/workspace/work/mv/lib')
import numpy as np, rig
fr0=np.zeros((1080,1920,3),np.float32)+0.2
sw=rig.Swordsman(1,view='3q'); 
for k in range(40): sw.pose('slash_diag',min(1,k/60),k/30,wind=200)
cu=rig.Swordsman(2,view='side',hair=2.0)
for k in range(30): rig.profile_cu(fr0.copy(),cu,k/30,960,540,560)
em=rig.Emperor(1)
for f in range(20): em.pose('raise_hand_decree',f/19,f/30,wind=120)
def T(fn,n=5):
    b=9
    for i in range(n):
        f=fr0.copy(); a=time.process_time(); fn(f); b=min(b,time.process_time()-a)
    return b
for be in ('cv','skia','cv','skia'):
    rig.set_backend(be)
    print(be,'swordsman 900px %.3f'%T(lambda f: sw.draw(f,960,1000,900)),'profile_cu %.3f'%T(lambda f: rig.profile_cu(f,cu,1.0,960,540,560)),
          'emperor 950 %.3f'%T(lambda f: em.draw(f,960,1040,950)))
