import sys,time; sys.path.insert(0,__import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/lib')
import numpy as np, cv2, rig
def sheet(actions, out, view="side", n=6, dur=1.4, cw=320, ch=420, scale=330, wind=-150, flip=False):
    rows=[]
    tt=[]
    for a in actions:
        sw=rig.Swordsman(2,view=view)
        cyc=rig.ACTIONS[a].get('cyc',False)
        frames=int(dur*30); picks=set(np.linspace(0,frames-1,n).astype(int))
        row=[]; hist=[]
        for f in range(frames):
            ph=f/(frames-1)
            if cyc: ph=f/frames*1.0
            sw.pose(a,ph,f/30,wind=wind,flip=flip)
            if f in picks:
                fr=np.full((ch,cw,3),0.0,np.float32)+np.linspace(0.32,0.14,ch)[:,None,None]
                fr[ch-30:]*=0.6
                t0=time.time()
                fr,info=sw.draw(fr,cw//2,ch-30,scale,rim_color=(0.95,0.85,0.7),rim_dir=(-0.7,-0.7),shine=(ph*2)%1.4-0.2)
                tt.append(time.time()-t0)
                f8=np.clip(fr*255,0,255).astype(np.uint8); cv2.putText(f8,'%s %.2f'%(a,ph),(6,18),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,255,255),1)
                row.append(f8)
        rows.append(np.hstack(row))
    img=np.vstack(rows)
    cv2.imwrite(out,img[:,:,::-1])
    print(out,'draw avg %.3f max %.3f'%(np.mean(tt),np.max(tt)))
if __name__=='__main__':
    import sys
    acts=sys.argv[2].split(','); view=sys.argv[3] if len(sys.argv)>3 else 'side'
    sheet(acts,sys.argv[1],view=view)
