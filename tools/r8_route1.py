"""第八轮路线 1 试做：现版副歌一管线（切点/转场/运镜/效果/字幕不动）+ STYLE_D 素材。
用法：python3 tools/r8_route1.py <f0> <f1> <out.mp4>   或  python3 tools/r8_route1.py still <f> <out.png>"""
import os, sys, subprocess
os.environ['SPRITE_MODE'] = '1'; os.environ['STYLE_D'] = os.environ.get('STYLE_D', '1')
os.environ.setdefault('OMP_NUM_THREADS', '2')
ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv')
sys.path[:0] = [ROOT + '/units', ROOT + '/lib', ROOT]
import numpy as np, cv2
import chorus1 as C, subtitle as SUB
X = C.Chorus1()
def frame(f):
    fr, _ = X.frame(f / 30, 1 / 30)
    return SUB.apply(C.to8(fr), f / 30)
if sys.argv[1] == 'still':
    cv2.imwrite(sys.argv[3], cv2.cvtColor(frame(int(sys.argv[2])), cv2.COLOR_RGB2BGR)); sys.exit()
f0, f1, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', '30', '-i', '-',
                      '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for f in range(f0, f1):
    p.stdin.write(np.ascontiguousarray(frame(f)).tobytes())
    if f % 10 == 0: print(f, flush=True)
p.stdin.close(); p.wait(); print('done', out)
