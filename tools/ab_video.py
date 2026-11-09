#!/usr/bin/env python3
"""tools/ab_video.py — 改造前/改造后 分屏对比片

两个快照（各含 `code/` 源码镜像 + `prun.py` + `pxcheck.py`，用 tools/devsnap.py 建）渲染同一段帧，
拼成左右分屏 mp4。用于「main vs 工作分支」的逐段对比。

用法：
  python3 tools/ab_video.py --old out/snap_main --new out/devsnap --f0 478 --f1 502 \
                            --out out/ab/V01b_cut.mp4 --label-old "改造前" --label-new "改造后"
  可选：--flags "LYRIC_UNI=1 GRADE_UNIFY=1"（同时作用于两边；默认两边都不用新开关）
"""
import argparse, os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
VENV = ROOT / 'out/full_sprite/chunks/local60_149c727_20261109/venv/bin/python'

RENDER = r'''
import sys, os
sys.path[:0] = ['.', 'code/units', 'code/lib', 'code']
import prun
from PIL import Image
st = prun.load(); cache = {}
f0, f1, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
os.makedirs(out, exist_ok=True)
for f in range(f0, f1):
    Image.fromarray(prun.render_frame(f, cache, st)).save(f'{out}/{f:05d}.png')
    print('F', f, flush=True)
'''


def render_snap(snap, f0, f1, outdir, flags, tag):
    outdir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    for kv in flags.split():
        if '=' in kv:
            k, v = kv.split('=', 1)
            env[k] = v
    env.setdefault('SPRITE_MODE', '1')
    script = outdir / f'.render_{tag}.py'
    script.write_text(RENDER)
    r = subprocess.run([str(VENV), str(script), str(f0), str(f1), str(outdir)], cwd=snap, env=env,
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-800:], r.stderr[-3000:], sep='\n'); sys.exit(1)
    n = len(list(outdir.glob('*.png')))
    print(f'  渲染 {tag}: {n} 帧 ({f1 - f0} 期望)', flush=True)
    return sorted(outdir.glob('*.png'))


def label_frames(files, text, font_path):
    """这台机器的 ffmpeg 没有 drawtext（无 libfreetype），所以标签用 PIL 烧进帧里。"""
    from PIL import Image, ImageDraw, ImageFont
    fnt = ImageFont.truetype(str(font_path), 26)
    for p in files:
        im = Image.open(p).convert('RGB')
        d = ImageDraw.Draw(im, 'RGBA')
        bbox = d.textbbox((0, 0), text, font=fnt)
        d.rectangle([8, 6, 8 + (bbox[2] - bbox[0]) + 16, 6 + (bbox[3] - bbox[1]) + 14], fill=(0, 0, 0, 150))
        d.text((16, 10), text, font=fnt, fill=(235, 217, 140))
        im.save(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--old', required=True)
    ap.add_argument('--new', required=True)
    ap.add_argument('--f0', type=int, required=True)
    ap.add_argument('--f1', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--flags', default='')
    ap.add_argument('--label-old', default='改造前')
    ap.add_argument('--label-new', default='改造后')
    ap.add_argument('--fps', type=int, default=30)
    a = ap.parse_args()

    tmp = pathlib.Path(tempfile.mkdtemp(prefix='abvid_'))
    old = render_snap(pathlib.Path(a.old).resolve(), a.f0, a.f1, tmp / 'old', a.flags, 'old')
    new = render_snap(pathlib.Path(a.new).resolve(), a.f0, a.f1, tmp / 'new', a.flags, 'new')
    n = min(len(old), len(new))
    out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    font = str(ROOT / 'fonts/NotoSerifSC-Bold.otf')
    font = ROOT / 'fonts/NotoSerifSC-Bold.otf'
    label_frames(old[:n], a.label_old, font)
    label_frames(new[:n], a.label_new, font)
    fc = "[0:v]scale=960:540[a];[1:v]scale=960:540[b];[a][b]hstack=inputs=2[v]"
    cmd = ['ffmpeg', '-y', '-v', 'error']
    cmd += ['-framerate', str(a.fps), '-start_number', str(a.f0), '-i', str(tmp / 'old' / '%05d.png')]
    cmd += ['-framerate', str(a.fps), '-start_number', str(a.f0), '-i', str(tmp / 'new' / '%05d.png')]
    cmd += ['-filter_complex', fc, '-map', '[v]', '-frames:v', str(n),
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', str(out)]
    subprocess.run(cmd, check=True)
    print(f'{out}  ({n} 帧 × 2 屏, {n / a.fps:.2f}s)', flush=True)
    if '--keep' not in sys.argv:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
