import sys,time; sys.path.insert(0,'/workspace/work/mv/lib')
import numpy as np, cv2, paper, fx2
W,H=1920,1080
def bg(c0=0.10,c1=0.03, glow=None):
    fr=(np.linspace(c0,c1,H)[:,None,None]*np.ones((1,W,3))).astype(np.float32)
    if glow is not None:
        yy,xx=np.mgrid[0:H,0:W]; d=((xx-glow[0])**2+(yy-glow[1])**2)/glow[2]**2
        fr+=(np.exp(-d)*0.7)[...,None].astype(np.float32)*paper.GOLD
    return fr
cells=[];T={}
def run(name,fn):
    a=time.process_time(); fr=fn(); T[name]=time.process_time()-a
    f8=np.clip(fr*255,0,255).astype(np.uint8); cv2.putText(f8,'%s %.2fs'%(name,T[name]),(30,170),0,2,(255,255,255),3)
    cells.append(cv2.resize(f8,(960,540),interpolation=cv2.INTER_AREA))
f1=paper.PaperFigure(1); f2=paper.PaperFigure(2,view='front')
def figs():
    fr=bg(glow=(960,400,700))
    for i,(b,kw) in enumerate([(0,{}),(0.5,{}),(1.0,{}),(0,dict(wet=0.6)),(0,dict(burn=0.45)),(0,dict(card=60))]):
        fr,_=f1.draw(fr,220+i*290,880,420,t=1.0,bow=b,**kw)
    return fr
run('PaperFigure side: bow/wet/burn/card',figs)
def figs2():
    fr=bg(0.75,0.6)
    for i,b in enumerate([0,0.6]):
        fr,_=f2.draw(fr,500+i*500,900,560,t=1,bow=b,light='front',light_color=(0.9,0.9,0.95),rim=0.3)
    fr,_=f2.draw(fr,1550,900,560,t=1,strings=(1450,150),light='front',light_color=(0.9,0.9,0.95),rim=0.3)
    return fr
run('front view / strings (white space)',figs2)
pc=paper.PaperCrowd(3)
run('PaperCrowd rain bow wave', lambda: fx2.RainSheet(1).draw(pc.draw(bg(glow=(960,300,900)),1.0,bow=0.6,wet=0.5)[0],1.0))
pc2=paper.PaperCrowd(4,rows=2,cols=7)
run('crowd on strings (S062)', lambda: pc2.draw(bg(glow=(960,0,600)),1.0,strings=(960,-40))[0])
mar=paper.Marionette(1); pi=paper.Marionette(2,style='piying')
def mars():
    fr=bg(glow=(960,450,800))
    for i,(cut,t) in enumerate([(0,0.5),(0,1.2),(0.4,1.5),(1.0,2)]):
        fr,_=mar.draw(fr,250+i*470,820,480,t=t,cut=cut,ctrl=(250+i*470,60))
    return fr
run('Marionette dance / cut 0.4 / cut 1',mars)
def piy():
    fr=bg(0.5,0.35); fr=fr*np.array([1.0,0.85,0.6],np.float32)
    for i,t in enumerate([0.3,1.4]):
        fr,_=pi.draw(fr,600+i*700,850,600,t=t,screen=1.0,light_color=(1,0.85,0.6),rim=0.3)
    return fr
run('Shadow puppet piying',piy)
t0=time.process_time(); G=paper.PaperGiant(1500,1); print('giant init',time.process_time()-t0)
for b,rev in [(0,0),(0,1),(0.35,1),(0.8,1)]:
    run('PaperGiant reveal %g burn %g'%(rev,b), lambda: G.draw(bg(0.2,0.1,glow=(960,350,900)),2.0,y=1560,reveal=rev,burn=b)[0])
sh=paper.PaperShreds(5)
run('Shreds to camera (S119)', lambda: sh.draw(bg(glow=(960,540,700)),1.2,t0=0,to_camera=1.0,spread=(500,300)))
run('Shreds burning', lambda: sh.draw(bg(),0.8,t0=0,burn=1.0,backlit=0.5))
cur=paper.PaperCurtain(6)
run('PaperCurtain wind', lambda: cur.draw(bg(0.35,0.2,glow=(960,500,900)),1.0))
run('Curtain cut x2 (S118)', lambda: cur.draw(bg(0.35,0.2,glow=(960,500,900)),2.0,cuts=[((0,300),(1920,800),1.4),((0,900),(1920,350),1.6)]))
img=np.vstack([np.hstack(cells[i:i+2]) for i in range(0,len(cells),2)])
cv2.imwrite('/workspace/work/mv/lib/rig_test/paper_sheet.jpg',img[:,:,::-1],[cv2.IMWRITE_JPEG_QUALITY,85])
for k,v in T.items(): print('%-40s %.3f'%(k,v))
