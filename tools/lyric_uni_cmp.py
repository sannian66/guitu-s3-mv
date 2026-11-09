#!/usr/bin/env python3
"""tools/lyric_uni_cmp.py — 全片字幕统一层（units/lyric_uni.py）对比图与位置一致性检查图

  python3 tools/lyric_uni_cmp.py pairs      # out/lyric_uni/cmp_<段>.jpg（7 段 × 3 句，「改造前 | 改造后」并排）
  python3 tools/lyric_uni_cmp.py consist    # out/lyric_uni/consist.jpg（20 帧缩略图拼图 + x=1792 基准线）
  python3 tools/lyric_uni_cmp.py all        # 两者
  python3 tools/lyric_uni_cmp.py frame <lu> <帧> <out.png>     # 内部用：在快照里渲一帧（可从别的目录调用）

渲染统一走 out/devsnap 的 prun.render_frame（源码快照 + pxcheck 同一条路径），每次渲一帧一个子进程，
并行度默认 2（机器上还有别人在渲染）。
"""
import os
import sys
import json
import math
import glob
import subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, 'out', 'devsnap')
OUTDIR = os.path.join(ROOT, 'out', 'lyric_uni')
TMP = '/tmp/lu_cmp'
FONT = os.path.join(ROOT, 'fonts', 'NotoSerifSC-Bold.otf')
FONT_L = os.path.join(ROOT, 'fonts', 'NotoSerifSC-Regular.otf')
PAR = int(os.environ.get('PAR', '2'))          # 同时最多 2 个渲染进程

# 7 个段落 → 行号区间（56 句的 align/lyrics 顺序）与「本段自己的字幕层是否已接线关掉」
SECTIONS = [
    ('1_A_intro_verse1', 'A 段 sec_a_intro_verse1（0–44.0s）', range(0, 8), True),
    ('2_B_pre1',         'B 组 sec_b_pre1（44.0–59.5s）',       range(8, 12), False),
    ('3_chorus1',        '副歌一 chorus1（59.5–86.2s）',        range(12, 20), True),
    ('4_B_verse2',       'B 组 sec_b_verse2（86.2–117.8s）',    range(20, 28), False),
    ('5_C_pre2_chorus2', 'C 段 sec_c_pre2_chorus2（117.8–161.3s）', range(28, 40), True),
    ('6_D_bridge',       'D 段 sec_d_bridge（161.3–193.2s）',   range(40, 48), False),
    ('7_E_final_outro',  'E 段 sec_e_final_outro（193.2–241.3s）', range(48, 56), False),
]


def venv_py():
    p = os.environ.get('PY')
    if p:
        return p
    c = sorted(glob.glob(os.path.join(ROOT, 'out', 'full_sprite', 'chunks', '*', 'venv', 'bin', 'python')))
    return c[0] if c else sys.executable


def _lines():
    sys.path.insert(0, os.path.join(ROOT, 'units'))
    import lyric_uni as LU
    return LU.lines()


# ---------------------------------------------------------------- 渲一帧（子进程内跑）
def cmd_frame(lu, fr, out):
    os.chdir(SNAP)
    sys.path.insert(0, SNAP)
    for key in ('LYRIC_UNI',):
        os.environ.pop(key, None)
    if str(lu) == '1':
        os.environ['LYRIC_UNI'] = '1'
    sys.argv = [sys.argv[0], 'status']            # prun 顶层会读 argv
    import numpy as np
    import prun
    from PIL import Image
    st = prun.load()
    img = prun.render_frame(int(fr), {}, st)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    Image.fromarray(img).save(out)


def render(jobs):
    """jobs: [(lu, frame, path)]；并行 PAR 个进程。"""
    py = venv_py()
    todo = [j for j in jobs if not os.path.exists(j[2]) or os.environ.get('FORCE')]
    print(f'render {len(todo)}/{len(jobs)} frames  par={PAR}', flush=True)

    def run(j):
        lu, fr, path = j
        r = subprocess.run([py, os.path.abspath(__file__), 'frame', str(lu), str(fr), path],
                           cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            print(f'FAIL {fr} lu={lu}\n{r.stderr[-1200:]}', flush=True)
        else:
            print(f'  ok {fr} lu={lu}', flush=True)

    with ThreadPoolExecutor(max_workers=PAR) as ex:
        list(ex.map(run, todo))


# ---------------------------------------------------------------- 选句
def pick_lines(L, rng):
    seg = [L[i] for i in rng]
    long_ = max(seg, key=lambda r: (r['n'], -r['line']))                 # 最长（必为两列）
    short = min(seg, key=lambda r: (r['n'], r['line']))                  # 最短（84px 单列）
    # 重音字最靠句中的那句（能同时看到朱红字 + 白字）
    pick = [long_, short]
    for r in sorted(seg, key=lambda r: (abs(r['accent'] - (r['n'] - 1) / 2.0), -r['n'])):
        if r['line'] not in [p['line'] for p in pick]:
            pick.append(r)
            break
    if len(pick) < 3:
        for r in seg:
            if r['line'] not in [p['line'] for p in pick]:
                pick.append(r)
                break
    return pick[:3]


def t_of(r):
    """句中最稳的一帧：末字已出、还没开始淡出。"""
    heads = [c['t'] for c in r['chars']]
    t = min(heads[-1] + 0.30, r['t_out'] - 0.06)
    t = max(t, heads[0] + 0.45)
    return t


def fnum(t):
    return int(round(t * 30))


# ---------------------------------------------------------------- 拼图
def _tile(img, w, h):
    from PIL import Image
    return img.resize((w, h), Image.LANCZOS)


def pairs():
    from PIL import Image, ImageDraw, ImageFont
    L = _lines()
    os.makedirs(OUTDIR, exist_ok=True)
    plans, jobs = [], []
    for name, title, rng, wired in SECTIONS:
        sel = pick_lines(L, rng)
        rows = []
        for r in sel:
            f = fnum(t_of(r))
            pb = os.path.join(TMP, f'{name}_{r["line"]}_before.png')
            pa = os.path.join(TMP, f'{name}_{r["line"]}_after.png')
            jobs += [(0, f, pb), (1, f, pa)]
            rows.append((r, f, pb, pa))
        plans.append((name, title, wired, rows))
    render(jobs)

    f_ttl = ImageFont.truetype(FONT, 26)
    f_cap = ImageFont.truetype(FONT, 20)
    f_sml = ImageFont.truetype(FONT_L, 17)
    TW, TH = 700, 394                 # 改造前 / 改造后 全幅缩略
    CW, CH = 260, 420                 # 改造后右侧字幕列全分辨率裁切
    x0, x1, x2 = 20, 20 + TW + 20, 20 + 2 * (TW + 20)
    W = x2 + CW + 20
    RH = max(TH, CH) + 36
    H = 78 + len(plans[0][3]) * RH + 12
    made = []
    for name, title, wired, rows in plans:
        sheet = Image.new('RGB', (W, H), (14, 14, 15))
        d = ImageDraw.Draw(sheet)
        d.text((20, 12), title, fill=(236, 232, 224), font=f_ttl)
        d.text((20, 46), '左右 = 改造前（本组原字幕） | 改造后（units/lyric_uni.py 统一层），右端 = 改造后字幕列全分辨率裁切'
                        + ('' if wired else '　⚠ 本段字幕层尚未接线关掉：右图 = 原字幕 + 统一层同屏，只示意统一层位置/风格'),
               fill=(140, 165, 150) if wired else (205, 160, 130), font=f_sml)
        for i, (r, f, pb, pa) in enumerate(rows):
            y = 78 + i * RH
            for j, p in enumerate((pb, pa)):
                x = x0 if j == 0 else x1
                if os.path.exists(p):
                    sheet.paste(_tile(Image.open(p).convert('RGB'), TW, TH), (x, y))
                else:
                    d.rectangle([x, y, x + TW, y + TH], outline=(90, 40, 40))
                    d.text((x + 12, y + 12), 'MISSING', fill=(220, 90, 90), font=f_cap)
                d.text((x, y + TH + 4), ('改造前  ' if j == 0 else '改造后  ') + r['text'],
                       fill=(228, 224, 216), font=f_cap)
            if os.path.exists(pa):
                crop = Image.open(pa).convert('RGB').crop((1400, 200, 1920, 1040))   # 字幕列原始分辨率
                sheet.paste(_tile(crop, CW, CH), (x2, y))
            d.text((x0, y + TH + 24),
                   '第 %d 句 · %d 字 · %d 列 · %dpx · 重音「%s」(%s) · 帧 %d (%.2fs)' % (
                       r['line'], r['n'], r['ncol'], r['size'], r['chars'][r['accent']]['ch'],
                       r['accent_src'], f, f / 30.0), fill=(158, 154, 146), font=f_sml)
        out = os.path.join(OUTDIR, f'cmp_{name}.jpg')
        sheet.save(out, quality=90)
        made.append(out)
        print('sheet', out, flush=True)
    return made


def consist():
    from PIL import Image, ImageDraw, ImageFont
    L = _lines()
    os.makedirs(OUTDIR, exist_ok=True)
    # 20 句均布全片（每 ~3 句取 1）
    idx = [int(round(i * (len(L) - 1) / 19.0)) for i in range(20)]
    idx = sorted(set(idx))
    jobs = []
    for i in idx:
        r = L[i]
        f = fnum(t_of(r))
        jobs.append((1, f, os.path.join(TMP, f'consist_{i}.png')))
    render(jobs)

    cols, TW, TH = 4, 480, 270
    rows = (len(idx) + cols - 1) // cols
    W = cols * (TW + 8) + 8
    H = 62 + rows * (TH + 34) + 8
    sheet = Image.new('RGB', (W, H), (10, 10, 11))
    d = ImageDraw.Draw(sheet)
    f_ttl = ImageFont.truetype(FONT, 24)
    f_cap = ImageFont.truetype(FONT_L, 15)
    d.text((10, 10), '整片字幕位置一致性检查：20 帧缩略图（黄线 = 列右缘 x=1792，绿线 = 列左界）', fill=(236, 232, 224), font=f_ttl)
    d.text((10, 40), '6/7 段未接线（B-pre1 / B-verse2 / D / E 仍带各自原字幕）→ 这些帧里除右侧竖列外还能看到各组旧字幕',
           fill=(200, 160, 130), font=f_cap)
    for k, i in enumerate(idx):
        r = L[i]
        p = os.path.join(TMP, f'consist_{i}.png')
        x = 8 + (k % cols) * (TW + 8)
        y = 62 + (k // cols) * (TH + 34)
        if os.path.exists(p):
            sheet.paste(_tile(Image.open(p).convert('RGB'), TW, TH), (x, y))
            d.line([x + TW * 1792 // 1920, y, x + TW * 1792 // 1920, y + TH], fill=(240, 210, 80), width=1)
            d.line([x + TW * 1532 // 1920, y, x + TW * 1532 // 1920, y + TH], fill=(80, 200, 140), width=1)
            d.line([x, y + TH * 120 // 1080, x + TW, y + TH * 120 // 1080], fill=(120, 120, 130), width=1)
            d.line([x, y + TH * 960 // 1080, x + TW, y + TH * 960 // 1080], fill=(120, 120, 130), width=1)
        d.text((x, y + TH + 2), '第%d句 %.2fs %d字%d列%dpx' % (r['line'], t_of(r), r['n'], r['ncol'], r['size']),
               fill=(210, 205, 195), font=f_cap)
    out = os.path.join(OUTDIR, 'consist.jpg')
    sheet.save(out, quality=90)
    print('sheet', out, flush=True)
    return out


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'frame':
        cmd_frame(sys.argv[2], sys.argv[3], sys.argv[4])
    elif c == 'pairs':
        pairs()
    elif c == 'consist':
        consist()
    elif c == 'all':
        pairs()
        consist()
