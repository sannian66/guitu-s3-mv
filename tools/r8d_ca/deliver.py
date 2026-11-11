"""CA 单元交付物：对比 mp4（左现版 | 右新版，带原音轨）、contact（每镜 55% 帧）、keys（冲击帧 / 出字帧 / 转场中点）。
用法：
  python tools/r8d_ca/deliver.py compare old.mp4 new.mp4 out.mp4      （F0=3534）
  python tools/r8d_ca/deliver.py sheet new.mp4 contact|keys out.jpg
"""
import os, sys, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
ROOT = os.environ.get('MV_ROOT', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
F0, F1 = 3534, 4219
CUT = [3534, 3566, 3622, 3642, 3683, 3710, 3744, 3769, 3786, 3820, 3864, 3903, 3943, 3971, 3999, 4035, 4067, 4095, 4123, 4150, 4178, 4219]
V = lambda t: round(t * 30) - 1
KEYS = [  # (帧, 标签)
    (V(118.16), 'C01 定 出字'), (V(118.82), 'C01 则 + 朱圈'), (V(120.36) + 2, 'C02 提纲 落定'), (V(120.96) + 2, 'C03 纲 拽起'),
    (V(121.72) + 1, 'C04 玉玺落盘'), (V(124.30) + 6, 'C06 合盖'), (V(124.90) + 1, 'C07 闪电'), (V(126.14) + 1, 'C08 瞳中电光'),
    (V(126.32) + 2, 'C09 上撩 一斩'), (V(127.00) + 2, 'C09 二斩'), (V(127.56) + 1, 'C10 大局为上'), (V(127.86) + 2, 'C10 斩绳'),
    (3884, 'C11 横刀'), (V(130.50) + 3, 'C12 刃光'), (V(131.96), 'C13 电光'), (V(132.45) + 1, 'C14 落雷'),
    (V(133.38) + 1, 'C15 雷 · 立定'), (V(133.79) + 2, 'C15 血振'), (V(133.79) + 7, 'C15 血珠悬停'), (V(134.50) + 6, 'C16 血 字'),
    (V(135.71) + 1, 'C17 落地'), (V(136.64) + 1, 'C18 闪电'), (V(137.92) + 3, 'C19 旋斩'), (V(138.42) + 2, 'C20 回头'),
    (V(139.48) + 1, 'C21 邪 正'), (3566, '转场 C01→C02'), (3622 + 1, '转场 C02→C03 whip'), (3744 + 3, '转场 C06→C07 seam'),
]


def read_frames(mp4, idx):
    cap = cv2.VideoCapture(mp4); out = {}
    want = sorted(set(idx)); i = 0; k = 0
    while k < len(want):
        ok, fr = cap.read()
        if not ok: break
        if i == want[k] - F0:
            out[want[k]] = fr[..., ::-1].copy(); k += 1
            while k < len(want) and want[k] == want[k - 1]: k += 1
        i += 1
    return out


def sheet(mp4, kind, outp):
    if kind == 'c21':
        items = [(4184, 'C21 起'), (4198, 'C21 中'), (4216, 'C21 止')]
        fr = read_frames(mp4, [f for f, _ in items])
        tw, th = 800, 450
        S = Image.new('RGB', (tw * 2, (th + 26) * 2), (10, 10, 10)); d = ImageDraw.Draw(S)
        fnt = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 17)
        for k, (f, lb) in enumerate(items):
            x, y = (k % 2) * tw, (k // 2) * (th + 26)
            S.paste(Image.fromarray(fr[f]).resize((tw, th), Image.LANCZOS), (x, y)); d.text((x + 4, y + th + 3), f'{lb}  f{f}', fill=(240, 220, 120), font=fnt)
        S.save(outp, quality=88); print(outp); return
    if kind == 'contact':
        items = [(a + int(0.55 * (b - a)), 'C%02d' % (i + 1)) for i, (a, b) in enumerate(zip(CUT, CUT[1:]))]
        cols = 4
    else:
        items = KEYS; cols = 4
    fr = read_frames(mp4, [f for f, _ in items])
    tw = 1600 // cols; th = int(tw * 1080 / 1920)
    rows = (len(items) + cols - 1) // cols
    S = Image.new('RGB', (cols * tw, rows * (th + 24)), (10, 10, 10)); d = ImageDraw.Draw(S)
    fnt = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 15)
    for k, (f, lb) in enumerate(items):
        if f not in fr: continue
        x, y = (k % cols) * tw, (k // cols) * (th + 24)
        S.paste(Image.fromarray(fr[f]).resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 4, y + th + 3), f'{lb}  f{f}  {f / 30:.2f}s', fill=(240, 220, 120), font=fnt)
    S.save(outp, quality=86)
    print(outp)


def compare(old, new, outp):
    # 本机 ffmpeg 无 drawtext（无 libfreetype）：标签先用 PIL 画成透明 PNG 再 overlay
    fnt = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 26)
    lab = '/tmp/mv_r8d_ca/cmp_label.png'; os.makedirs(os.path.dirname(lab), exist_ok=True)
    L = Image.new('RGBA', (1920, 540), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.text((16, 12), '现版 r6', fill=(255, 255, 255, 216), font=fnt); d.text((976, 12), '风格 D', fill=(255, 255, 255, 216), font=fnt)
    L.save(lab)
    vf = "[0:v]scale=960:540[a];[1:v]scale=960:540[b];[a][b]hstack=inputs=2[s];[s][3:v]overlay=0:0,scale=1280:-2[v]"
    cmd = ['ffmpeg', '-y', '-v', 'error', '-i', old, '-i', new, '-ss', f'{F0 / 30:.4f}', '-t', f'{(F1 - F0) / 30:.4f}', '-i', ROOT + '/audio/谁定正邪.mp3',
           '-i', lab, '-filter_complex', vf, '-map', '[v]', '-map', '2:a', '-c:v', 'libx264', '-crf', '26', '-preset', 'medium', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '160k', outp]
    subprocess.run(cmd, check=True); print(outp)


if __name__ == '__main__':
    if sys.argv[1] == 'compare': compare(*sys.argv[2:5])
    else: sheet(sys.argv[2], sys.argv[3], sys.argv[4])
