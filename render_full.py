"""Render a frame range of the full MV (video only). Usage: python3 render_full.py F0 F1 out.mp4"""
import sys, subprocess, random, numpy as np
import cv2; cv2.setNumThreads(1)
import scenes as S
from fx import finish, to8, W, H
FPS = 30
f0, f1, outp = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
random.seed(f0); np.random.seed(f0)
cache = {}
p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                      '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', '-tune', 'film', outp], stdin=subprocess.PIPE)
for f in range(f0, f1):
    t = f / FPS
    fr, ca = S.frame_at(t, 1 / FPS, cache)
    fr = finish(fr, grain_amt=0.045, vig=0.5, ca=ca)
    p.stdin.write(to8(fr).tobytes())
    if f % 150 == 0: print(f'{t:.1f}s', flush=True)
p.stdin.close(); p.wait()
print('done', outp)
