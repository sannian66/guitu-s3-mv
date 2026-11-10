"""tools/c_contact.py — C 组联系表 / 关键帧表（按 units/sec_c_pre2_chorus2.py 自己的 SHOTS/CUT_F 取帧）。
用法（多帧渲染必须包 cpu_slot）：
  V4_FORCE=c_pre2_chorus2 tools/cpu_slot.sh python3 tools/c_contact.py contact out/round4/C_contact_v1.jpg [i0 i1]
  V4_FORCE=c_pre2_chorus2 tools/cpu_slot.sh python3 tools/c_contact.py keys    out/round4/C_keys_v1.jpg    [i0 i1]
i0 i1：只渲第 i0..i1-1 张（缩略图缓存在 /tmp/c_contact_cache/，分批跑避开 120s 超时）；不给则渲剩余并拼图。"""
import os, sys, time
ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv')
sys.path.insert(0, ROOT + '/units')
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sec_c_pre2_chorus2 as M

CACHE = os.environ.get('C_CACHE', '/workspace/work/c_r3/cache'); os.makedirs(CACHE, exist_ok=True)
TW, TH = 480, 270


def items(mode):
    out = []
    if mode == 'contact':
        for i, S in enumerate(M.SHOTS):
            f = (M.CUT_F[i] + M.CUT_F[i + 1]) // 2
            out.append((f, f'{S.__name__} {f / 30:.2f}s ({(M.CUT_F[i + 1] - M.CUT_F[i]) / 30:.2f}s)'))
    else:
        # 转场中间帧（非 hard 的切点 = 切点帧）
        for i, S in enumerate(M.SHOTS[1:], 1):
            name, pre, post = M.CUTS.get(S.__name__, ('hard', 0, 0))[:3]
            # 转场中间帧（p≈0.5）；硬切取切后第 1 帧（冲击帧）
            f = round((M.CUT_F[i] / M.FPS - pre + (pre + post) / 2) * M.FPS) if name != 'hard' else M.CUT_F[i]
            out.append((f, f'{M.SHOTS[i - 1].__name__}>{S.__name__} {name}'))
        # 歌词关键帧：每句屏幕字最后一个字落定后 3 帧
        for s in M.SENTS:
            f = round((s.tin[-1] + 0.10) * 30)
            out.append((f, f'lyric {s.text} {f / 30:.2f}s'))
    return out


def render(mode, i0, i1):
    its = items(mode)
    for k, (f, lab) in enumerate(its[i0:i1], i0):
        p = f'{CACHE}/{mode}_{k:03d}_{f}.jpg'
        if os.path.exists(p): continue
        t0 = time.time()
        im = M.frame(f, {})
        Image.fromarray(im).resize((TW, TH), Image.LANCZOS).save(p, quality=90)
        print(k, f, lab, f'{time.time() - t0:.2f}s', flush=True)


def sheet(mode, out, cols=6):
    its = items(mode)
    rows = (len(its) + cols - 1) // cols
    LH = 26
    S = Image.new('RGB', (cols * TW, rows * (TH + LH)), (12, 12, 12))
    d = ImageDraw.Draw(S)
    try: fnt = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Medium.otf', 18)
    except Exception: fnt = None
    for k, (f, lab) in enumerate(its):
        p = f'{CACHE}/{mode}_{k:03d}_{f}.jpg'
        x, y = (k % cols) * TW, (k // cols) * (TH + LH)
        if os.path.exists(p): S.paste(Image.open(p), (x, y + LH))
        d.text((x + 6, y + 3), lab, fill=(230, 220, 200), font=fnt)
    S.save(out, quality=82, optimize=True)
    print('saved', out, S.size, os.path.getsize(out) // 1024, 'KB')


if __name__ == '__main__':
    mode, out = sys.argv[1], sys.argv[2]
    n = len(items(mode))
    if len(sys.argv) > 4:
        render(mode, int(sys.argv[3]), int(sys.argv[4]))
    else:
        render(mode, 0, n); sheet(mode, ROOT + '/' + out if not out.startswith('/') else out)
