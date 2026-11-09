import sys, time, numpy as np
from PIL import Image
import scenes as S
from fx import finish, to8
ts=[float(x) for x in sys.argv[2:]]
cache={}; ims=[]
for t in ts:
    a=time.time(); fr,ca=S.frame_at(t,1/30,cache); fr=finish(fr,ca=ca)
    print(t, round(time.time()-a,2), S.TIMELINE[S.seg_at(t)[0]][1], flush=True)
    ims.append(Image.fromarray(to8(fr)).resize((640,360)))
cols=3; rows=(len(ims)+cols-1)//cols
C=Image.new('RGB',(640*cols,360*rows))
for k,i in enumerate(ims): C.paste(i,((k%cols)*640,(k//cols)*360))
C.save(sys.argv[1],quality=85)
