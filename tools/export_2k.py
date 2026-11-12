"""tools/export_2k.py — 出片统一到 2K 2560×1440 / 24fps（用户 11-11 定的成片规格）。

为什么需要：代码渲的镜头是 1920×1080 / 30fps（画布、坐标、切点表都是按它写的），
视频生成的片段是 2560×1440 / 24fps。出片时统一到 2560×1440 / 24fps：
- 1080p30 的段：升采样到 2560×1440（Lanczos）+ 30→24 帧按时间重采样（ffmpeg fps 滤镜，保持时长）；
- 已经 2560×1440 / 24fps 的段（视频生成）：视频流拷贝，不动。

用法：
  python3 tools/export_2k.py <输入.mp4> <输出.mp4> [--audio song.mp3]
  python3 tools/export_2k.py concat <list.txt> <输出.mp4> [--audio song.mp3]   # 先逐段转码再拼
"""
import json, os, subprocess, sys

W, H, FPS = 2560, 1440, 24


def probe(p):
    out = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                   '-show_entries', 'stream=width,height,r_frame_rate',
                                   '-of', 'json', p])
    s = json.loads(out)['streams'][0]
    num, den = (s['r_frame_rate'].split('/') + ['1'])[:2]
    return int(s['width']), int(s['height']), float(num) / float(den)


def has_audio(p):
    out = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'a',
                                   '-show_entries', 'stream=index', '-of', 'json', p])
    return bool(json.loads(out)['streams'])


def convert(src, dst, audio=None):
    w, h, fps = probe(src)
    native = (w, h) == (W, H) and abs(fps - FPS) < 0.01
    vf = [] if native else ['scale=%d:%d:flags=lanczos' % (W, H), 'fps=%d' % FPS]
    cmd = ['ffmpeg', '-y', '-v', 'error', '-i', src]
    if audio:
        cmd += ['-i', audio]
    if vf:
        cmd += ['-vf', ','.join(vf)]
    cmd += ['-c:v', 'libx264', '-crf', '17', '-preset', 'slow', '-pix_fmt', 'yuv420p']
    keep = audio is None and has_audio(src)      # 没单独给音频时，不要丢掉源文件自带的音轨
    if audio:
        cmd += ['-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '256k', '-shortest']
    elif keep:
        cmd += ['-map', '0:v', '-map', '0:a?', '-c:a', 'copy', '-shortest']
    else:
        cmd += ['-an']
    cmd += ['-movflags', '+faststart', dst]
    subprocess.check_call(cmd)
    print(('%s -> %s  (%dx%d @%.2ffps%s -> %dx%d @%dfps%s%s)' % (
        os.path.basename(src), os.path.basename(dst), w, h, fps, ' native' if native else '', W, H, FPS,
        ' native copy' if native else '', ' +audio' if (audio or keep) else ' 无音轨')).strip())
    return dst


def concat(listfile, dst, audio=None):
    """逐段统一到 2K24，再按 list.txt 顺序拼接。list.txt 每行一个 mp4 路径。"""
    parts = [l.strip() for l in open(listfile) if l.strip()]
    tmpdir = os.path.dirname(os.path.abspath(dst)) + '/_2k_' + os.path.basename(dst).replace('.mp4', '')
    os.makedirs(tmpdir, exist_ok=True)
    conv = [convert(p, os.path.join(tmpdir, '%03d.mp4' % i)) for i, p in enumerate(parts)]
    lst = os.path.join(tmpdir, 'list.txt')
    with open(lst, 'w') as f:
        for c in conv:
            f.write("file '%s'\n" % c)
    out = dst if not audio else os.path.join(tmpdir, 'noloud.mp4')
    subprocess.check_call(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst,
                           '-c', 'copy', out])
    if audio:
        subprocess.check_call(['ffmpeg', '-y', '-v', 'error', '-i', out, '-i', audio,
                               '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k',
                               '-shortest', '-movflags', '+faststart', dst])
    print('concat done', dst)


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    audio = sys.argv[sys.argv.index('--audio') + 1] if '--audio' in sys.argv else None
    if a[0] == 'concat':
        concat(a[1], a[2], audio)
    else:
        convert(a[0], a[1], audio)
