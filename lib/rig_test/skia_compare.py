"""cv2 光栅 vs skia 矢量：同一帧左右对比 + 局部放大 + 计时。输出 skia_cmp_*.png"""
import sys,time; sys.path.insert(0,__import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/lib')
import numpy as np, cv2, rig
def bg(h=1080,w=1920):
    return (np.linspace(0.30,0.10,h)[:,None,None]*np.ones((1,w,3))).astype(np.float32)
def scene_sw(backend):
    rig.set_backend(backend); fr=bg(); T=[]
    for view,wind,x,act in [('side',300,450,'stand_wind'),('3q',-300,1000,'slash_diag'),('back',300,1550,'stand_wind')]:
        sw=rig.Swordsman(1,view=view)
        for k in range(40): sw.pose(act,min(1,k/60),k/30,wind=wind)
        a=time.time(); fr,_=sw.draw(fr,x,1000,780,rim_color=(0.9,0.92,1),rim_dir=(-0.8,-0.6)); T.append(time.time()-a)
    return fr,T
def scene_trail(backend):
    rig.set_backend(backend); fr=(np.linspace(0.16,0.05,1080)[:,None,None]*np.ones((1,1920,3))).astype(np.float32)
    sw=rig.Swordsman(3,view='side'); hist=[]; N=36
    for f in range(N):
        p=f/(N-1); sw.pose('slash_diag',p,f/30,wind=-120)
        if p>=0.47: break
        _,info=sw.draw(np.zeros((1080,1920,3),np.float32),900,1000,800,rim=0); hist.append((info['guard'],info['tip']))
    a=time.time(); fr,info=sw.draw(fr,900,1000,800,rim_color=(0.8,0.88,1),rim_dir=(-0.7,-0.6),shine=0.6)
    hist.append((info['guard'],info['tip'])); fr=rig.blade_trail(fr,hist[-7:],edge_color=(1.0,0.35,0.15)); return fr,[time.time()-a]
def scene_emp(backend):
    rig.set_backend(backend); fr=bg()*0.4; em=rig.Emperor(1,view='front')
    for f in range(20): em.pose('raise_hand_decree',f/19,f/30,wind=120)
    a=time.time(); fr,_=em.draw(fr,960,1040,950,rim_color=(1,0.8,0.5),rim_dir=(0,-1)); return fr,[time.time()-a]
def scene_cu(backend):
    rig.set_backend(backend); fr=bg()*0.5; sw=rig.Swordsman(2,view='side',hair=2.0)
    for k in range(30): rig.profile_cu(np.zeros_like(fr),sw,k/30,960,540,560)
    a=time.time(); fr,_=rig.profile_cu(fr,sw,1.0,960,540,560); T=[time.time()-a]
    h=rig.HandCU(0); a=time.time(); fr2=bg()*0.5; fr2=h.draw(fr2,'grip',0.6,1.0,960,560,520); T.append(time.time()-a)
    fr2=fr2[0] if isinstance(fr2,tuple) else fr2
    return np.hstack([fr[:, 480:1440], fr2[:, 480:1440]]),T
to8=lambda f: np.clip(f*255,0,255).astype(np.uint8)
for name,fn,crop in [('swordsman',scene_sw,(250,700,330,780)),('trail',scene_trail,None),('emperor',scene_emp,(80,530,700,1150)),('closeup',scene_cu,(250,700,300,750))]:
    a,Ta=fn('cv'); b,Tb=fn('skia')
    print(name,'cv %.3f'%sum(Ta),'skia %.3f'%sum(Tb))
    if crop is None:
        ys,xs=np.nonzero(np.abs(b-a).sum(2)>0.05); cy,cx=int(np.median(ys)),int(np.median(xs)); crop=(max(0,cy-225),max(0,cy-225)+450,max(0,cx-225),max(0,cx-225)+450)
    y0,y1,x0,x1=crop
    za=cv2.resize(a[y0:y1,x0:x1],None,fx=2,fy=2,interpolation=cv2.INTER_NEAREST); zb=cv2.resize(b[y0:y1,x0:x1],None,fx=2,fy=2,interpolation=cv2.INTER_NEAREST)
    top=np.hstack([cv2.resize(a,(960,int(960*a.shape[0]/a.shape[1]))),cv2.resize(b,(960,int(960*b.shape[0]/b.shape[1])))])
    bot=np.hstack([cv2.resize(za,(960,960)),cv2.resize(zb,(960,960))])
    img=to8(np.vstack([top,bot]))
    for x,s in ((20,'cv2  %.3fs'%sum(Ta)),(980,'skia %.3fs'%sum(Tb))): cv2.putText(img,s,(x,40),cv2.FONT_HERSHEY_SIMPLEX,1.2,(255,255,255),3)
    cv2.imwrite('skia_cmp_%s.png'%name,img[:,:,::-1])
