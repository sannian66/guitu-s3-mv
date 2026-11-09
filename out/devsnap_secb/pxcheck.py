import sys, os, time
sys.argv=[sys.argv[0],'status']
import prun
from PIL import Image
frames=[int(x) for x in os.environ['FR'].split(',')]
st=prun.load(); cache={}
for f in frames:
    t=time.monotonic(); fr=prun.render_frame(f,cache,st); dt=time.monotonic()-t
    Image.fromarray(fr).save(f'/tmp/px_{os.environ.get("SPRITE_FAST","1")}_{f}.png')
    print(f'FRAME {f} {dt:.2f}s', flush=True)
