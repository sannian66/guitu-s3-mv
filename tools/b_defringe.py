import sys, numpy as np, cv2
from PIL import Image
for n in sys.argv[1:]:
    cutim=Image.open(n+'_cut.png'); raw=np.asarray(Image.open(n+'_raw.png').convert('RGB').resize(cutim.size, Image.LANCZOS)).astype(np.float32)
    cut=np.asarray(Image.open(n+'_cut.png').convert('RGBA')).astype(np.float32)
    A=cut[...,3]/255; F=cut[...,:3]
    # 背景灰估计：raw 四角中值
    h,w=A.shape; c=np.concatenate([raw[:40,:40].reshape(-1,3),raw[:40,-40:].reshape(-1,3),raw[-40:,:40].reshape(-1,3),raw[-40:,-40:].reshape(-1,3)])
    bg=np.median(c,0)
    d=np.abs(raw-bg).max(-1)
    flat=(d<10).astype(np.uint8)
    # 只去掉与边界连通的大片灰
    num,lab,st,_=cv2.connectedComponentsWithStats(flat,8)
    kill=np.zeros_like(flat)
    for i in range(1,num):
        if st[i,4]>9000: kill[lab==i]=1
    A=A*(1-cv2.GaussianBlur(kill.astype(np.float32),(0,0),2))
    # 外圈「近灰」像素（发丝间残留的背景灰）按与背景色差降 alpha
    core=cv2.erode((A>0.9).astype(np.uint8),np.ones((3,3),np.uint8))
    dist=cv2.distanceTransform(1-core,cv2.DIST_L2,5)
    lumraw=raw.mean(-1); lumbg=bg.mean()
    greyish=np.clip((d-8)/26,0,1)
    band=np.clip(dist/6,0,1)
    A=A*(1-band*(1-greyish))
    # 内部大块近灰（被包住的背景洞）
    hole=((d<9)&(A>0.5)).astype(np.uint8)
    num,lab,st,_=cv2.connectedComponentsWithStats(hole,8)
    for i in range(1,num):
        if st[i,4]>400 and n.startswith("tsh"): A[lab==i]=0
    # 半透明边：反预乘去灰（F = (raw - (1-a)*bg)/a）
    a=np.clip(A,1e-3,1)[...,None]
    Fd=np.clip((raw-(1-a)*bg)/a,0,255)
    edge=(A>0.02)&(A<0.97)
    F=np.where(edge[...,None],Fd,F)
    # 边缘环带再压暗一点（去亮边）
    er=cv2.erode((A>0.5).astype(np.uint8),np.ones((7,7),np.uint8))
    ring=((A>0.02)&(er==0)).astype(np.float32)
    F=F*(1-0.35*ring[...,None])
    out=np.dstack([F,A*255]).astype(np.uint8)
    Image.fromarray(out,'RGBA').save(n+'_cutd.png'); print(n,bg)
