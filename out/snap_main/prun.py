#!/usr/bin/env python3
"""全片 1080p 原生 30fps 并行渲染（源码快照 code/ 冻结，HEAD 见 source_manifest.json）。

  python3 prun.py prep            冻结源码快照
  python3 prun.py frame F out.png 单帧
  python3 prun.py bench W 10 3990 并行标定：W 个进程各渲 10 帧，报吞吐
  python3 prun.py run             并行渲染 + 拼接 + 混音 + 校验（可断点续跑）
  python3 prun.py status
"""
import fcntl, json, math, os, pathlib, subprocess, sys, time, traceback

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
            'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[key] = '1'
os.environ['SPRITE_MODE'] = '1'
os.environ['V4_FORCE'] = 'b_pre1,b_verse2'
os.environ['C1_CAM'] = '3'; os.environ['C1_LYR'] = '3'; os.environ['C1_RIG'] = 'live'
for key in ('V4_OFF', 'V4_ONLY', 'SPRITE_SHOTS', 'SPRITE_EXT'):
    os.environ.pop(key, None)

BASE = pathlib.Path(__file__).resolve().parent
CODE = BASE / 'code'
FPS = 30
N = 7240                      # 帧 0..7239 = 241.333s（音频 241.32s，末帧补齐）
FINE = int(os.environ.get('FINE', '8'))          # 细粒度分块（块越小越好分摊昂贵镜头）
WORKERS = int(os.environ.get('W', '6'))
def complete_ranges():
    out = []
    for p in (BASE / 'chunks').glob('f_*.mp4'):
        if p.name.endswith('.partial.mp4'):
            continue
        a, b = p.stem.split('_')[1:3]
        out.append((int(a), int(b)))
    return sorted(out)


def pending_chunks():
    """尚未被已完成的块覆盖的帧区间（细粒度）。"""
    cov = complete_ranges()
    res = []
    for a in range(0, N, FINE):
        b = min(a + FINE, N)
        if any(ca <= a and b <= cb for ca, cb in cov):
            continue
        res.append((a, b))
    return res


def covered_frames():
    return sum(min(b, N) - a for a, b in complete_ranges() if b > a)


CHUNKS = pending_chunks()
MASTER = BASE / 'delivery/谁定正邪_MV_1080p30_master_crf17.mp4'
WEB = BASE / 'delivery/谁定正邪_MV_1080p30_web_crf21.mp4'


def write_json(path, data):
    p = pathlib.Path(path); tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2)); tmp.replace(p)


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))


def good(path, count):
    try:
        d = probe(path)
        v = next(s for s in d['streams'] if s['codec_type'] == 'video')
        return (int(v['nb_frames']) == count and v['width'] == 1920 and v['height'] == 1080
                and v['r_frame_rate'] == '30/1' and v['pix_fmt'] == 'yuv420p')
    except Exception:
        return False


def load():
    for d in (CODE / 'units', CODE / 'lib', CODE):
        sys.path.insert(0, str(d))
    import numpy as np, cv2, skia  # noqa: F401
    cv2.setNumThreads(1)
    import render_sprite_full as R
    import sections
    return np, R, sections


def render_frame(f, cache, st):
    np, R, sections = st
    f = int(f)
    m = sections.lookup(f)
    if m is not None:
        fr = m.frame(f, cache.setdefault('_v4_' + m.__name__, {}))
    elif 1784 <= f < 2586:
        C, X = R.chorus1()
        fr, _ = X.frame(f / FPS, 1 / FPS)
        fr = C.to8(fr)
    else:
        raise RuntimeError(f'no renderer for frame {f}')
    if fr.shape != (1080, 1920, 3) or fr.dtype != np.uint8:
        raise RuntimeError(f'bad frame {f}: {fr.shape} {fr.dtype}')
    return fr


def rss_mb():
    out = subprocess.check_output(['ps', '-o', 'rss=', '-p', str(os.getpid())], text=True).strip()
    return int(out) / 1024.0


def chunk_paths(a, b):
    return BASE / f'chunks/f_{a:05d}_{b:05d}.partial.mp4', BASE / f'chunks/f_{a:05d}_{b:05d}.mp4'


def worker(a, b, threads=2):
    st = load(); np = st[0]; cache = {}
    import random
    partial, dest = chunk_paths(a, b)
    cmd = ['ffmpeg', '-y', '-v', 'error', '-threads', str(threads), '-filter_threads', '1',
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', '30/1', '-i', 'pipe:0',
           '-an', '-c:v', 'libx264', '-threads', str(threads), '-preset', 'medium', '-crf', '17',
           '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-tune', 'film',
           '-video_track_timescale', '30000', str(partial)]
    t = time.monotonic()
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for f in range(a, b):
            random.seed(f); np.random.seed(f)          # 每帧定种：块边界不影响画面
            p.stdin.write(render_frame(f, cache, st).tobytes())
            if (f - a) % 30 == 0:
                el = time.monotonic() - t
                print('PROGRESS ' + json.dumps({'frame': f, 'chunk': f'{a}-{b}', 'worker_pid': os.getpid(),
                                                'chunk_elapsed': round(el, 1),
                                                's_per_frame': round(el / (f - a + 1), 3),
                                                'rss_mb': round(rss_mb())}), flush=True)
        p.stdin.close()
        rc = p.wait()
        if rc:
            raise RuntimeError(f'ffmpeg exit {rc}')
        if not good(partial, b - a):
            raise RuntimeError('chunk validation failed')
        partial.replace(dest)
        print(f'CHUNK_OK {a} {b} {time.monotonic() - t:.1f}s', flush=True)
    except BaseException:
        if p.stdin and not p.stdin.closed:
            p.stdin.close()
        if p.poll() is None:
            p.terminate()
        p.wait()
        raise


def locks():
    d = BASE / 'locks'; d.mkdir(exist_ok=True); return d


def claim():
    """动态领取下一块（O_EXCL 锁文件）；顺手回收已死进程留下的锁。"""
    d = locks()
    for i, (a, b) in enumerate(CHUNKS):
        lk = d / f'{a:05d}.lock'
        try:
            fd = os.open(lk, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
        return i, a, b
    for lk in sorted(d.glob('*.lock')):
        try:
            pid = int(lk.read_text() or 0)
        except ValueError:
            pid = 0
        if pid and pid != os.getpid():
            try:
                os.kill(pid, 0)
                continue
            except ProcessLookupError:
                pass
        a = int(lk.stem); b = min(a + FINE, N)
        if good(chunk_paths(a, b)[1], b - a):
            continue
        print(f'RECLAIM {lk.name}', flush=True)
        lk.unlink(missing_ok=True)
        return claim()          # 回收后立刻重新领取


def work_loop(tag):
    while True:
        got = claim()
        if got is None:
            return
        i, a, b = got
        print(f'CLAIM {tag} #{i} {a}-{b} t={time.time():.0f}', flush=True)
        try:
            worker(a, b)
        except BaseException:
            print(f'CHUNK_FAIL {a} {b}\n' + traceback.format_exc(), flush=True)
            return


def done_count():
    return covered_frames()


def segments():
    files = {(a, b): chunk_paths(a, b)[1] for a, b in complete_ranges()}
    segs, p = [], 0
    while p < N:
        cands = [k for k in files if k[0] == p and k[1] > p and k[1] <= N]
        if not cands:
            raise RuntimeError(f'frame {p} 没有可用分块')
        a, b = max(cands, key=lambda k: k[1])
        segs.append(files[(a, b)])
        p = b
    return segs


def finalize():
    paths = segments()
    listing = BASE / 'chunks/concat.txt'
    listing.write_text(''.join("file '" + str(p).replace("'", "'\\''") + "'\n" for p in paths))
    tmp = MASTER.with_name(MASTER.stem + '.partial.mp4')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-threads', '4', '-f', 'concat', '-safe', '0', '-i', str(listing),
                    '-i', str(CODE / 'audio/谁定正邪.mp3'), '-map', '0:v:0', '-map', '1:a:0',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k',
                    '-af', f'apad,atrim=duration={N / FPS:.6f}', '-t', f'{N / FPS:.6f}',
                    '-movflags', '+faststart', str(tmp)], check=True)
    d = probe(tmp)
    v = next(s for s in d['streams'] if s['codec_type'] == 'video')
    au = next(s for s in d['streams'] if s['codec_type'] == 'audio')
    if not good(tmp, N):
        raise RuntimeError('master metadata mismatch')
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-threads', '4', '-i', str(tmp), '-f', 'null', '-'],
                   check=True)
    cnt = int(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                                       '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', str(tmp)],
                                     text=True).strip())
    if cnt != N:
        raise RuntimeError(f'decoded {cnt} != {N}')
    tmp.replace(MASTER)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(MASTER), '-c:v', 'libx264', '-preset', 'slow',
                    '-crf', '21', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-c:a', 'aac', '-b:a', '192k',
                    '-movflags', '+faststart', str(WEB)], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(WEB), '-f', 'null', '-'], check=True)
    write_json(BASE / 'delivery/ffprobe_validation.json', {
        'master': {k: v.get(k) for k in ('codec_name', 'width', 'height', 'r_frame_rate', 'nb_frames')},
        'audio': {k: au.get(k) for k in ('codec_name', 'sample_rate', 'channels')},
        'duration': d['format']['duration'], 'size': d['format']['size'],
        'decoded_frames': cnt, 'decode': 'OK', 'fps': '30/1', 'source': '30fps native, 1:1'})
    result = (f'RESULT OK master={MASTER} web={WEB} frames={N} 1920x1080 fps=30/1 '
              f'video=h264_crf17 audio=aac320k decode=OK')
    (BASE / 'RESULT.txt').write_text(result + '\n')
    print(result, flush=True)


def run():
    lockf = open(BASE / 'render.lock', 'a+'); fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    (BASE / 'runner.pid').write_text(str(os.getpid()) + '\n')
    start = time.time()
    log = BASE / 'logs/run.log'
    try:
        write_json(BASE / 'status.json', {'status': 'rendering', 'pid': os.getpid(), 'started': start,
                                          'workers': WORKERS, 'total_frames': N, 'chunks': len(CHUNKS)})
        if CHUNKS:
            for a, b in CHUNKS:
                (locks() / f'{a:05d}.lock').unlink(missing_ok=True)
        print(f'START workers={WORKERS} pending_chunks={len(CHUNKS)} covered_frames={covered_frames()}/{N}', flush=True)
        procs = []
        with log.open('a') as out:
            for w in range(WORKERS):
                procs.append(subprocess.Popen([sys.executable, '-I', str(pathlib.Path(__file__).resolve()),
                                               'worker', f'w{w}'], stdout=out, stderr=subprocess.STDOUT))
            for p in procs:
                p.wait()
        n = done_count()
        print(f'ALL_WORKERS_EXIT covered={n}/{N} elapsed={time.time() - start:.0f}s', flush=True)
        if n != N:
            raise RuntimeError(f'{N - n} frames missing; rerun to resume')
        write_json(BASE / 'status.json', {'status': 'muxing', 'pid': os.getpid(), 'elapsed_seconds': round(time.time() - start, 1)})
        finalize()
        write_json(BASE / 'status.json', {'status': 'complete', 'pid': os.getpid(),
                                          'elapsed_seconds': round(time.time() - start, 1),
                                          'master': str(MASTER), 'web': str(WEB)})
    except BaseException as e:
        write_json(BASE / 'status.json', {'status': 'failed', 'pid': os.getpid(), 'error': str(e),
                                          'done': done_count(), 'total': len(CHUNKS),
                                          'traceback': traceback.format_exc()})
        print('RESULT FAILED ' + str(e), flush=True)
        raise


def bench_worker(f0, n):
    """单进程渲染 n 帧，逐帧打印耗时（供 bench 并行标定用）。"""
    st = load(); cache = {}; ts = []
    for f in range(f0, f0 + n):
        t = time.monotonic(); render_frame(f, cache, st); ts.append(time.monotonic() - t)
    print('BW ' + json.dumps({'times': [round(x, 2) for x in ts], 'rss_mb': round(rss_mb())}), flush=True)


def bench(w, n, f0):
    self_py = str(pathlib.Path(__file__).resolve())
    t = time.monotonic()
    procs = [subprocess.Popen([sys.executable, '-I', self_py, 'bw', str(f0 + n * k), str(n)],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) for k in range(w)]
    outs = [p.communicate()[0] for p in procs]
    wall = time.monotonic() - t
    rows = []
    for o in outs:
        for line in o.splitlines():
            if line.startswith('BW '):
                rows.append(json.loads(line[3:]))
    allt = [x for r in rows for x in r['times']]
    print(json.dumps({'workers': w, 'frames': w * n, 'wall_s': round(wall, 1),
                      'throughput_fps': round(w * n / wall, 2),
                      'mean_s_per_frame': round(sum(allt) / len(allt), 3) if allt else None,
                      'rss_mb_max': round(max((r['rss_mb'] for r in rows), default=0), 0),
                      'errors': [o[-300:] for o in outs if 'BW ' not in o]}), flush=True)


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'frame':
        from PIL import Image
        Image.fromarray(render_frame(int(sys.argv[2]), {}, load())).save(sys.argv[3])
    elif c == 'bw':
        bench_worker(int(sys.argv[2]), int(sys.argv[3]))
    elif c == 'bench':
        bench(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
    elif c == 'worker':
        work_loop(sys.argv[2])
    elif c == 'run':
        run()
    elif c == 'finalize':
        finalize()
    elif c == 'status':
        for name in ('status.json', 'RESULT.txt'):
            p = BASE / name
            if p.exists():
                print(name + '\n' + p.read_text())
        print(f'chunks done {done_count()}/{len(CHUNKS)}')
    else:
        raise SystemExit('unknown command')
