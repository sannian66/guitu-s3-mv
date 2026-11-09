import sys,time; sys.path.insert(0,'/workspace/work/mv/lib')
import numpy as np, cv2, fx2
from fx2 import W,H
def bg(top=0.10,bot=0.03):
    fr=np.linspace(top,bot,H)[:,None,None]*np.ones((1,W,3),np.float32)
    n=fx2.noise(512,4,base=3,octaves=6); cl=cv2.resize(n,(W,H))
    fr=fr+((cl-0.5)*0.08)[...,None]
    fr[820:]*=0.5
    return fr.astype(np.float32)
T={}
def tm(name,f,*a,**k):
    t0=time.time(); r=f(*a,**k); T[name]=T.get(name,[])+[time.time()-t0]; return r
cells=[]
rain=fx2.RainSheet(1); sp=fx2.Splashes(2); L=fx2.Lightning(3,(800,130),(1150,820)); cr=fx2.CrackLight(4,(960,160),(940,940))
emb=fx2.Embers(5,240); gold=fx2.Embers(6,160,mode='gold',rise=60); ash=fx2.Embers(7,120,mode='ash',rise=80); fog=fx2.Fog(8)
def lab(fr,s):
    f8=np.clip(fr*255,0,255).astype(np.uint8); cv2.putText(f8,s,(30,170),cv2.FONT_HERSHEY_SIMPLEX,2.2,(255,255,255),4); return f8
for name,fn in [
 ('rain+splash t=1', lambda fr: sp.draw(rain.draw(fr,1.0,light=(1400,300)),1.0)),
 ('rain red slow', lambda fr: rain.draw(fr,3.3,red=1.0,angle=4)),
 ('rain freeze', lambda fr: rain.draw(fr,2.0,freeze=1.0)),
 ('lightning lead -0.02', lambda fr: L.draw(fr,9.98,10.0)),
 ('lightning +0.01', lambda fr: L.draw(fr,10.01,10.0)),
 ('lightning +0.15', lambda fr: L.draw(fr,10.15,10.0)),
 ('cloud_flash', lambda fr: fx2.cloud_flash(fr,5.02,5.0,(960,250),800,seed=1)),
 ('god_rays moon', lambda fr: fx2.god_rays(fr,(1300,300),strength=0.8,color=fx2.COLD,t=1.0,src_r=110)),
 ('light_beam', lambda fr: fx2.light_beam(fr,(300,150),(1200,950),40,260,t=2.0,color=fx2.COLD,strength=0.5)),
 ('crack 0.6', lambda fr: cr.draw(fr,1.0,prog=0.6,open_=0.6)),
 ('crack open 2', lambda fr: cr.draw(fr,2.0,prog=1.0,open_=2.0,spill=1.3)),
 ('embers fire', lambda fr: emb.draw(fr,2.0)),
 ('embers burst', lambda fr: emb.draw(fr,0.5,t0=0.0,burst=(960,600,700))),
 ('gold dust', lambda fr: gold.draw(fr,3.0)),
 ('ash', lambda fr: ash.draw(fr,2.0)),
 ('fog lit', lambda fr: fog.draw(fr,2.0,density=0.8,y0=450,light=(960,500))),
 ('heat haze+bloom', lambda fr: fx2.bloom(fx2.heat_haze(fr,1.0,amt=8),0.3,1.0)),
 ('grain', lambda fr: fx2.grain(fr,1.0,0.05)),
]:
    fr=bg(); 
    cv2.circle(fr,(1300,300),100,(0.9,0.9,0.85),-1,cv2.LINE_AA)
    cv2.rectangle(fr,(400,600),(560,960),(0.02,0.02,0.02),-1)
    fr=tm(name,fn,fr)
    cells.append(cv2.resize(lab(fr,name),(640,360),interpolation=cv2.INTER_AREA))
rows=[np.hstack(cells[i:i+3]) for i in range(0,len(cells),3)]
img=np.vstack(rows); cv2.imwrite('/workspace/work/mv/lib/rig_test/fx2_sheet.jpg',img[:,:,::-1],[cv2.IMWRITE_JPEG_QUALITY,88])
for k,v in T.items(): print('%-22s %.3f'%(k,np.mean(v)))
