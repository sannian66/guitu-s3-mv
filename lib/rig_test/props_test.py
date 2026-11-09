import sys,time,warnings; sys.path.insert(0,'/workspace/work/mv/lib')
import numpy as np, cv2, props, fx2
W,H=1920,1080
def bg(c0=0.10,c1=0.03, glow=None, col=props.GOLD):
    fr=(np.linspace(c0,c1,H)[:,None,None]*np.ones((1,W,3))).astype(np.float32)
    if glow is not None:
        yy,xx=np.mgrid[0:H,0:W]; d=((xx-glow[0])**2+(yy-glow[1])**2)/glow[2]**2
        fr+=(np.exp(-d)*0.5)[...,None].astype(np.float32)*col
    return fr
cells=[];T={}
def run(name,fn):
    a=time.process_time(); fr=fn(); fr=fr[0] if isinstance(fr,tuple) else fr; T[name]=time.process_time()-a
    f8=np.clip(fr*255,0,255).astype(np.uint8); cv2.putText(f8,'%s %.2fs'%(name,T[name]),(30,170),0,1.8,(255,255,255),3)
    cells.append(cv2.resize(f8,(960,540),interpolation=cv2.INTER_AREA))
B=props.Blade(1)
run('Blade sheen + engrave', lambda: B.draw(bg(),1.0,(150,620),(1800,470),150,sheen=0.55,engrave='谁定正邪',engrave_p=0.6))
run('Blade heat 0.9 (S026)', lambda: B.draw(bg(0.05,0.02),1.0,(150,620),(1800,470),150,heat=0.9))
run('Blade blood + beads', lambda: B.draw(bg(),2.3,(150,620),(1800,470),150,blood=1.0,beads=9,wet=1.0))
run('Blade heat+steam (S067)', lambda: B.draw(bg(0.08,0.03),1.5,(150,700),(1800,560),130,heat=0.6,steam=1.0))
bal=props.Balance(1)
run('Balance tilt + drip (S012/13)', lambda: bal.draw(bg(glow=(960,300,600),col=fx2.COLD),1.0,960,330,1000,tilt=-8,drip=1.0))
run('Balance break 0.5 (S091)', lambda: bal.draw(bg(glow=(960,300,600),col=fx2.COLD),1.0,960,330,1000,tilt=-8,break_=0.5))
sc=props.Scroll(1)
run('Scroll unroll 0.7 type 0.5', lambda: sc.draw(bg(),1.0,960,540,1300,620,unroll=0.7,type_=0.5))
run('Scroll tear 0.5', lambda: sc.draw(bg(),1.0,960,540,1300,620,tear=0.5))
gs=props.GiantSeal('正')
run('GiantSeal falling 0.7', lambda: gs.draw(bg(glow=(960,200,800)),1.0,960,860,520,fall=0.7))
run('GiantSeal split 0.4 (S019)', lambda: gs.draw(bg(glow=(960,200,800)),1.0,960,860,520,split=0.4))
face=props.seal_face('是非对错',400)
def stamps():
    fr=bg(0.75,0.65)
    for i,p in enumerate([0.15,0.35,1.0]): fr=props.stamp_imprint(fr,face,480+i*480,540,380,p,angle=3)
    return fr
run('seal_face + stamp_imprint',stamps)
cw=props.CharWall(1)
cr=fx2.CrackLight(4,(980,140),(940,960))
run('CharWall front + crack', lambda: cw.draw(bg(),1.0,crack=cr,crack_kw=dict(prog=0.8,open_=0.8)))
run('CharWall tilt up (S034)', lambda: cw.draw(bg(),1.0,tilt=0.5))
run('CharWall rise 0.6', lambda: cw.draw(bg(),1.0,rise=0.6))
run('CharWall collapse 0.6 (S080)', lambda: cw.draw(bg(glow=(960,540,600)),1.0,collapse=0.6))
pq=props.Plaque('天理昭彰')
run('Plaque sheen', lambda: pq.draw(bg(0.3,0.15),1.0,960,540,1400,sheen=0.4))
run('Plaque crack 0.8 (S114)', lambda: pq.draw(bg(0.3,0.15),1.0,960,540,1400,crack=0.8))
img=np.vstack([np.hstack(cells[i:i+2]) for i in range(0,len(cells)-1,2)])
cv2.imwrite('/workspace/work/mv/lib/rig_test/props_sheet.jpg',img[:,:,::-1],[cv2.IMWRITE_JPEG_QUALITY,85])
for k,v in T.items(): print('%-36s %.3f'%(k,v))
