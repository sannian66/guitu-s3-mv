"""F组 r6 第五棒：一次进程连渲多帧（必须 tools/cpu_slot.sh 包一层）。用法：python3 crew/round6/F_r6e_rf.py <前缀> t1 t2 ..."""
import sys
sys.argv, args = [sys.argv[0]], sys.argv[1:]
sys.path.insert(0, '/workspace/work/mv')
import render_sprite_full as R
from PIL import Image
pre = args[0]
for t in args[1:]:
    Image.fromarray(R.frame(int(round(float(t) * R.FPS)), {})).save(f'{pre}_{t}.png'); print('ok', t, flush=True)
