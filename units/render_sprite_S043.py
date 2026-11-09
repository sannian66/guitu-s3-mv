"""S043 生图精灵试点渲染：SPRITE_MODE=1，镜头拉长到试点窗口（默认 82.06–85.56，3.5s），
相机 = 副歌一 vcam3 的 S043 运动（按窗口比例映射回 S043 原时段），前景/曝光/统一字幕层同 Chorus1.frame。
用法：python3 units/render_sprite_S043.py frames T1 T2 ...   → /tmp/s43/sp_<t>.jpg
      python3 units/render_sprite_S043.py video  out.mp4      → 先写 /tmp 再拷贝（带音频）
"""
import os, sys, subprocess, shutil
os.environ['SPRITE_MODE'] = '1'
WIN = (82.059, 85.559)
os.environ['SPRITE_EXT'] = '%f,%f' % WIN
sys.path.insert(0, '/workspace/work/mv/units')
import numpy as np, cv2
import chorus1 as C
from c1kit import finish, to8

c = C.Chorus1()
shot = c.byid['S043']; shot.render(WIN[0])
S = shot.obj
assert type(S).__qualname__ == 'S043Sprite'


def frame(t):
    fr, ca = S.render(t)
    u = (t - WIN[0]) / (WIN[1] - WIN[0])
    tc = S.t0 + 0.12 + u * (S.t1 - S.t0 - 0.26)          # 避开首尾切点冲击/甩镜帧
    shut = 0.5 * (S.t1 - S.t0) / (WIN[1] - WIN[0])       # 镜头被拉长 → 快门按比例缩短，运动模糊与原节奏一致
    fr, st = c.cam.apply(np.clip(fr, 0, 4).astype(np.float32), tc, shutter=shut)
    fr = c.fg.draw(fr, t, st, 'ember', 0.4)
    fr = fr * (C.EXPO_ALL * C.EXPO.get('S043', 1.0))
    fr = fr + 0.012 * (1 - np.clip(fr, 0, 1))
    fr = c.lyr.draw(fr, t)
    return finish(fr, t, ca=0, vig=0.42)


if __name__ == '__main__':
    if sys.argv[1] == 'frames':
        os.makedirs('/tmp/s43', exist_ok=True)
        for a in sys.argv[2:]:
            t = float(a); cv2.imwrite('/tmp/s43/sp_%.2f.jpg' % t, to8(frame(t))[..., ::-1])
    else:
        out = sys.argv[2]; tmp = '/tmp/s43/S043_sprite.mp4'
        n = int(round((WIN[1] - WIN[0]) * 30))
        p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', '30',
                              '-i', '-', '-ss', '%.3f' % WIN[0], '-t', '%.3f' % (n / 30), '-i', '/workspace/work/mv/audio/谁定正邪.mp3',
                              '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                              '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', tmp], stdin=subprocess.PIPE)
        for i in range(n):
            p.stdin.write(to8(frame(WIN[0] + i / 30)).tobytes())
        p.stdin.close(); p.wait()
        os.makedirs(os.path.dirname(out), exist_ok=True); shutil.copy(tmp, out); print(out, os.path.getsize(out))
