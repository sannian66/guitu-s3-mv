"""全片精灵版渲染（SPRITE_MODE=1，2026-11-09）。
  python3 render_sprite_full.py seg F0 F1 out.mp4      帧区间 → 无声 H.264 CRF17（30fps）
  python3 render_sprite_full.py frame T out.png         单帧
  python3 render_sprite_full.py contact out.jpg         每个精灵镜头一帧的联系表（标镜号）
组装：帧 1784–2585（59.47–86.20s）= 副歌一 units/chorus1.py（精灵版，自带收尾）；其余 = scenes.frame_at（场景 + units/rest_sprites.py 精灵）+ fx.finish。
"""
import os, sys, subprocess, time, random
os.environ['SPRITE_MODE'] = '1'
os.environ.setdefault('OMP_NUM_THREADS', '1')
ROOT = '/workspace/work/mv'
os.chdir(ROOT)
sys.path.insert(0, ROOT + '/units'); sys.path.insert(0, ROOT + '/lib'); sys.path.insert(0, ROOT)
import numpy as np, cv2
cv2.setNumThreads(1)
import scenes as S
from fx import finish, to8, W, H
FPS = 30
C1_F0, C1_F1 = 1784, 2586
_C1 = [None]


def chorus1():
    if _C1[0] is None:
        import chorus1 as C; _C1[0] = (C, C.Chorus1())
    return _C1[0]


def frame(f, cache):
    import subtitle as SUB                      # 第五轮 #52：全片统一底部居中歌词字幕
    return SUB.apply(_frame(f, cache), f / FPS)


def _frame(f, cache):
    t = f / FPS
    import sections as SEC                      # 第四轮：各组 units/sec_*.py 接管自己的帧区间（READY=True 时）
    m = SEC.lookup(f)
    if m is not None:
        return m.frame(f, cache.setdefault('_v4_' + m.__name__, {}))
    if C1_F0 <= f < C1_F1:
        C, X = chorus1()
        fr, _ = X.frame(t, 1 / FPS)
        return C.to8(fr)
    fr, ca = S.frame_at(t, 1 / FPS, cache)
    return to8(finish(fr, grain_amt=0.045, vig=0.5, ca=ca))


def seg(f0, f1, outp):
    random.seed(f0); np.random.seed(f0)
    cache = {}
    p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-tune', 'film', outp],
                         stdin=subprocess.PIPE)
    a = time.time()
    for f in range(f0, f1):
        p.stdin.write(frame(f, cache).tobytes())
        if f % 60 == 0: print(f'{f / FPS:.2f}s  {(time.time() - a) / max(1, f - f0 + 1):.2f}s/f', flush=True)
    p.stdin.close(); p.wait()
    print('done', outp, flush=True)


def shot_times():
    """每个精灵镜头取一帧：有切换的取最后一个姿势之后，否则取镜头 55%。"""
    import rest_sprites as RS, chorus1 as C
    out = []
    for sid in RS.ORDER:
        c = RS.S[sid]; t0, t1 = c['t0'], c['t1']
        sw = [s for s, _ in c['poses'] if s]
        t = (max(sw) + t1) / 2 if sw else t0 + 0.55 * (t1 - t0)
        st = c.get('slash_t')
        if st and t0 <= st + 0.06 < t1: t = st + 0.06
        out.append((sid, t))
    X = chorus1()[1]
    for i, sid in enumerate(X.ids):
        if sid in ('S029', 'S030', 'S035', 'S037', 'S038', 'S039', 'S041', 'S043', 'S044', 'S045', 'S046'):
            s = X.shots[i]
            out.append((sid, s.t0 + 0.55 * (s.t1 - s.t0)))
    return sorted(out, key=lambda x: x[1])


def tiles(only):
    """把指定镜头各渲一帧存 /tmp/ctiles/<镜号>.png（每组一个进程，避免场景缓存累积撑爆内存）。"""
    from PIL import Image
    os.makedirs('/tmp/ctiles', exist_ok=True)
    items = [x for x in shot_times() if x[0] in only]
    for sid, t in items:
        cache = {}
        Image.fromarray(frame(int(round(t * FPS)), cache)).resize((480, 270), Image.LANCZOS).save(f'/tmp/ctiles/{sid}.png')
        print(sid, round(t, 2), flush=True)


def contact(outp, only=None, group=10):
    from PIL import Image, ImageDraw, ImageFont
    items = shot_times()
    if only: items = [x for x in items if x[0] in only]
    ids = [s for s, _ in items]
    for i in range(0, len(ids), group):          # 分组子进程渲染
        todo = [s for s in ids[i:i + group] if not os.path.exists(f'/tmp/ctiles/{s}.png')]
        if todo: subprocess.run([sys.executable, __file__, 'tiles', ','.join(todo)], check=False)
    cols = 6; tw, th = 480, 270
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * tw, rows * (th + 28)), (12, 12, 12))
    d = ImageDraw.Draw(sheet)
    fnt = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 20)
    for k, (sid, t) in enumerate(items):
        x, y = (k % cols) * tw, (k // cols) * (th + 28)
        p = f'/tmp/ctiles/{sid}.png'
        if os.path.exists(p): sheet.paste(Image.open(p), (x, y))
        d.text((x + 6, y + th + 2), f'{sid}  {t:.2f}s', fill=(240, 220, 120), font=fnt)
    sheet.save(outp, quality=88)
    print(outp)


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'seg': seg(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif c == 'frame':
        from PIL import Image
        Image.fromarray(frame(int(round(float(sys.argv[2]) * FPS)), {})).save(sys.argv[3])
    elif c == 'tiles': tiles(sys.argv[2].split(','))
    elif c == 'contact': contact(sys.argv[2], sys.argv[3].split(',') if len(sys.argv) > 3 else None)
