"""tools/r6_render.py — 第六轮出片（r6-RENDER）两层渲染：画面底层（SUB_OFF=1，FFV1 无损）+ 离线字幕层。

  python3 tools/r6_render.py plan                     # 按段落/镜头边界切块 → crew/round6/render_r6_chunks.json
  python3 tools/r6_render.py base A B OUT.mkv         # 底层：帧 [A,B) SUB_OFF=1 → FFV1 gbrp 无损（逐像素 = 管线 8bit 输出）
  python3 tools/r6_render.py sub A B BASE.mkv OUT.mp4 # 字幕层：解码底层 → subtitle.apply（默认 serif_h + SUB_FX=1）→ x264 crf17 high yuv420p bt709
  python3 tools/r6_render.py frame T OUT.png          # 从底层块 + 离线字幕取单帧（对拍用）

块边界 = units/sections.py 段落边界 ∪ crew/shots.json 镜头起点，相邻镜头合并到 ≤MAXF 帧。
seg 与 render_sprite_full.seg 相同：块起点 random.seed(A)、np.random.seed(A)，块内共享 cache。
改字幕 / 去画内重复字时：只需重渲受影响镜头所在块的底层（或只重跑 sub），见 crew/round6/RENDER_r6.md。
"""
import os, sys, json, subprocess, time, random
ROOT = '/workspace/work/mv'
OUT = ROOT + '/out/render_r6'
PLAN = ROOT + '/crew/round6/render_r6_chunks.json'
FPS, W, H, N = 30, 1920, 1080, 7240
MAXF = 260
SEC_B = [0, 1321, 1784, 2586, 3534, 4839, 5797, 7240]


def plan():
    shots = json.load(open(ROOT + '/crew/shots.json'))
    starts = {round(s['t0'] * FPS): s['id'] for s in shots}
    b = sorted(set(SEC_B) | set(starts))
    b = [x for x in b if 0 <= x <= N]
    chunks, a = [], 0
    for i in range(1, len(b)):
        x = b[i]
        nxt_sec = x in SEC_B
        if x - a >= MAXF or nxt_sec or x == N:
            # 若加上这一段超过 MAXF，就在上一个边界切
            if x - a > MAXF and b[i - 1] > a:
                chunks.append((a, b[i - 1])); a = b[i - 1]
            if nxt_sec or x - a >= MAXF * 0.6 or x == N:
                chunks.append((a, x)); a = x
    out = []
    for k, (a, c) in enumerate(chunks):
        ids = [starts[f] for f in sorted(starts) if a <= f < c]
        out.append({'k': k, 'f0': a, 'f1': c, 'shots': ids, 'name': f'b{k:02d}_{a:05d}_{c:05d}'})
    assert out[0]['f0'] == 0 and out[-1]['f1'] == N
    assert all(out[i]['f1'] == out[i + 1]['f0'] for i in range(len(out) - 1))
    json.dump(out, open(PLAN, 'w'), ensure_ascii=False, indent=1)
    print(len(out), 'chunks; max', max(c['f1'] - c['f0'] for c in out), 'min', min(c['f1'] - c['f0'] for c in out))


def base(f0, f1, outp):
    os.environ['SUB_OFF'] = '1'
    sys.argv = [sys.argv[0]]
    sys.path.insert(0, ROOT)
    import render_sprite_full as R
    import numpy as np
    random.seed(f0); np.random.seed(f0)
    cache = {}
    p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'ffv1', '-level', '3', '-g', '1', '-slices', '4', '-slicecrc', '1', '-threads', '1',
                          '-pix_fmt', 'gbrp', outp], stdin=subprocess.PIPE)
    a = time.time()
    for f in range(f0, f1):
        p.stdin.write(R.frame(f, cache).tobytes())
        if (f - f0) % 30 == 0: print(f'{f / FPS:.2f}s  {(time.time() - a) / max(1, f - f0 + 1):.2f}s/f', flush=True)
    p.stdin.close(); rc = p.wait()
    print('done', outp, rc, f'{time.time() - a:.0f}s', flush=True)
    sys.exit(rc)


def read_frames(path):
    import numpy as np
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
    p.wait()


ENC709 = ['-vf', 'scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int', '-colorspace', 'bt709',
          '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv']


def sub(f0, f1, basep, outp):
    os.environ.pop('SUB_OFF', None)
    sys.path.insert(0, ROOT + '/units'); sys.path.insert(0, ROOT + '/lib'); sys.path.insert(0, ROOT)
    os.chdir(ROOT)
    import subtitle as SUB
    p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          *ENC709, '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                          '-tune', 'film', '-threads', '2', outp], stdin=subprocess.PIPE)
    f = f0; a = time.time()
    for img in read_frames(basep):
        p.stdin.write(SUB.apply(img.copy(), f / FPS).tobytes()); f += 1
    p.stdin.close(); rc = p.wait()
    print('sub done', outp, f - f0, 'frames', f'{time.time() - a:.0f}s', flush=True)
    if f != f1: print('FRAMECOUNT MISMATCH', f - f0, f1 - f0); sys.exit(3)
    sys.exit(rc)


def frame(t, outp):
    from PIL import Image
    f = int(round(t * FPS))
    c = [c for c in json.load(open(PLAN)) if c['f0'] <= f < c['f1']][0]
    basep = f"{OUT}/base/{c['name']}.mkv"
    os.environ.pop('SUB_OFF', None)
    sys.path.insert(0, ROOT + '/units'); sys.path.insert(0, ROOT + '/lib'); sys.path.insert(0, ROOT); os.chdir(ROOT)
    import subtitle as SUB, numpy as np
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', basep, '-vf', f'select=eq(n\\,{f - c["f0"]})', '-vframes', '1',
                        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE, check=True)
    img = np.frombuffer(r.stdout, np.uint8).reshape(H, W, 3).copy()
    Image.fromarray(SUB.apply(img, f / FPS)).save(outp)


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'plan': plan()
    elif c == 'base': base(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif c == 'sub': sub(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5])
    elif c == 'frame': frame(float(sys.argv[2]), sys.argv[3])
