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


# ---------------------------------------------------------------- ① 逐字墨显 3（+2）帧条
def reveal(t, r):
    """该时刻已经「出字」的个数（字头 −0.06s 起笔，0.10s 内淡入）。"""
    return sum(1 for c in r['chars'] if t >= c['t'] - 0.06)


def strips(lines_=None):
    """每句给「字头前 1 帧 / 首字+2 帧 / 1/4 处 / 句中 / 末字后 2 帧」5 格帧条，证明逐字墨显。"""
    from PIL import Image, ImageDraw, ImageFont
    L = _lines()
    lines_ = lines_ or [15, 13, 17]
    os.makedirs(OUTDIR, exist_ok=True)
    jobs, rows = [], []
    for ln in lines_:
        r = L[ln]
        h0, h1 = r['chars'][0]['t'], r['chars'][-1]['t']
        span = h1 - h0
        ts = [h0 - 1 / 30.0, h0 + 2 / 30.0, h0 + 0.25 * span, h0 + 0.5 * span, h1 + 2 / 30.0]
        row = []
        for t in ts:
            f = fnum(t)
            p = os.path.join(TMP, f'strip_{ln}_{f}.png')
            jobs.append((1, f, p))
            row.append((f, t, p))
        rows.append((r, row))
    render(jobs)

    f_ttl = ImageFont.truetype(FONT, 26)
    f_cap = ImageFont.truetype(FONT, 19)
    f_sml = ImageFont.truetype(FONT_L, 16)
    TW, TH = 372, 209                       # 整帧缩略
    CW, CH = 372, 380                       # 字幕列裁切（x 1440–1920 缩放）
    RH = 30 + TH + 34 + CH + 16
    W = 20 + 5 * (TW + 14)
    H = 116 + len(rows) * RH
    sheet = Image.new('RGB', (W, H), (14, 14, 15))
    d = ImageDraw.Draw(sheet)
    d.text((20, 12), '逐字墨显实测：每句 5 帧（首字前 1 帧 → 首字+2 帧 → 1/4 → 句中 → 末字后 2 帧）', fill=(236, 232, 224), font=f_ttl)
    d.text((20, 46), '「已出 k/n 字」= 该帧真正画出来的字数（字头 −0.06s 起笔，0.10s 淡入）；下排是该帧字幕列( x1440–1920 )裁切',
           fill=(150, 165, 150), font=f_sml)
    d.text((20, 72), '第 1 格必须几乎是空的、第 5 格必须满 —— 证明不是「整句提前全出」。同帧对比：旧层在副歌一是「半句一条」，统一层是「整句一条」',
           fill=(150, 165, 150), font=f_sml)
    for i, (r, row) in enumerate(rows):
        y = 116 + i * RH
        d.text((20, y), '第 %d 句「%s」 %d 字 · %d 列 · %dpx' % (r['line'], r['text'].replace(' ', '·'), r['n'], r['ncol'], r['size']),
               fill=(232, 200, 120), font=f_cap)
        for j, (f, t, p) in enumerate(row):
            x = 20 + j * (TW + 14)
            if os.path.exists(p):
                im = Image.open(p).convert('RGB')
                sheet.paste(_tile(im, TW, TH), (x, y + 28))
                sheet.paste(_tile(im.crop((1440, 120, 1920, 960)), CW, CH), (x, y + 28 + TH + 34))
            k = reveal(t, r)
            d.text((x, y + TH + 30), '%.3fs  f%d　已出 %d/%d 字' % (t, f, k, r['n']),
                   fill=(120, 210, 160) if 0 < k < r['n'] else (220, 170, 130), font=f_cap)
    out = os.path.join(OUTDIR, 'reveal_strips.jpg')
    sheet.save(out, quality=91)
    print('sheet', out, flush=True)
    return out


# ---------------------------------------------------------------- ② 几何硬测试（--guard）
def guard(real_frames=None):
    """56 句 × 3 帧（字头 / 中 / 末字后 2 帧）画在黑底上，断言上下 120px 黑边全黑。

    这是常驻回归测试：以后改 COL_TOP / TIERS / LEAD / 换列规则，跑一遍就知道有没有长出画面。
    """
    import numpy as np
    sys.path.insert(0, os.path.join(ROOT, 'units'))
    import lyric_uni as LU
    os.environ['LYRIC_UNI'] = '1'
    L = LU.lines()
    bad, rows = [], []
    for r in L:
        h0, h1 = r['chars'][0]['t'], r['chars'][-1]['t']
        worst = (0, 0.0)
        for t in (h0, (h0 + h1) / 2.0, h1 + 2 / 30.0):
            f = fnum(t)
            for dtype in ('u8', 'f32'):
                if dtype == 'u8':
                    canvas = np.zeros((1080, 1920, 3), np.uint8)
                    out = LU.draw(canvas, f)
                    mx_t = int(out[0:LU.BAR].max()) / 255.0
                    mx_b = int(out[1080 - LU.BAR:].max()) / 255.0
                else:
                    canvas = np.zeros((1080, 1920, 3), np.float32)
                    out = LU.draw(canvas, f)
                    mx_t = float(out[0:LU.BAR].max())
                    mx_b = float(out[1080 - LU.BAR:].max())
                worst = max(worst, (t, max(mx_t, mx_b)))
        ok = worst[1] < 0.02
        rows.append((r, worst, ok))
        if not ok:
            bad.append((r['line'], round(worst[1], 4), round(worst[0], 2)))
    os.environ.pop('LYRIC_UNI', None)
    print('== A 合成底硬测试：%d 句 × 3 帧（字头 / 句中 / 末字后 2 帧）× uint8+float32' % len(L))
    print('   断言行：rows[0:120].max() < 0.02 且 rows[960:1080].max() < 0.02')
    print('   列顶 y=%d，可用高 %dpx，行距 %.2f' % (LU.COL_TOP, 960 - LU.COL_TOP, LU.LEAD))
    print('   最靠下：第 %d 句列底 %.0fpx（离下黑边 %.0fpx）｜最靠上：第 %d 句墨迹 %.0fpx（离上黑边 %.0fpx）' % (
        max(L, key=lambda r: r['y_bot'])['line'], max(r['y_bot'] for r in L), 960 - max(r['y_bot'] for r in L),
        L[0]['line'], min(r['pos'][0]['y'] - r['size'] * 0.72 for r in L),
        min(r['pos'][0]['y'] - r['size'] * 0.72 for r in L) - 120))
    if bad:
        print('   ✗ FAIL %d 句撞黑边：' % len(bad))
        for ln, mx, t in bad:
            r = L[ln]
            fit = int((960 - LU.COL_TOP) / max(1, max(len(c) for c in r['cols'])) / LU.LEAD)
            print('     句号 %2d ｜字数 %2d ｜实际列底 y=%.0f（越界 %.0fpx）｜当前字号 %d ｜建议字号 ≤%d' % (
                ln, r['n'], r['y_bot'], r['y_bot'] - 960, r['size'], fit))
    else:
        print('   ✓ PASS  56/56 句（3 帧 × 2 dtype = 336 次断言）上下黑边全黑，max=%.4f' % max(w[1] for _, w, _ in rows))

    with open(os.path.join(OUTDIR, 'geom_report.txt'), 'w', encoding='utf-8') as fh:
        fh.write('句号\t字数\t列数\t字号\t列顶\t列底\t下黑边余量\t3帧越界亮度max\t结果\n')
        for r, w, ok in rows:
            fh.write('%d\t%d\t%d\t%d\t%d\t%.0f\t%.0f\t%.4f\t%s\n' % (
                r['line'], r['n'], r['ncol'], r['size'], LU.COL_TOP, r['y_bot'], 960 - r['y_bot'], w[1],
                'PASS' if ok else 'FAIL'))

    # ---- B 实拍帧（含组长抓到的 3050）：底帧黑边 + 叠字后黑边分别量，出问题能分清是谁的
    rf = real_frames if real_frames is not None else [3050]
    if rf:
        import numpy as np
        from PIL import Image
        print('== B 实拍帧核对（先渲 LYRIC_UNI=0 底帧，量黑边；再叠统一层，量黑边）')
        jobs = []
        for f in rf:
            jobs.append((0, f, os.path.join(TMP, f'real_{f}_base.png')))
            jobs.append((1, f, os.path.join(TMP, f'real_{f}_lu.png')))
        render(jobs)
        allok = True
        for f in rf:
            pb = os.path.join(TMP, f'real_{f}_base.png')
            pa = os.path.join(TMP, f'real_{f}_lu.png')
            if not (os.path.exists(pb) and os.path.exists(pa)):
                print('   frame %d 渲染失败' % f); allok = False; continue
            A = np.asarray(Image.open(pb).convert('RGB'), np.float32) / 255.0
            B = np.asarray(Image.open(pa).convert('RGB'), np.float32) / 255.0
            m = lambda X: (float(X[0:120].max()), float(X[960:1080].max()))
            (t0, b0), (t1, b1) = m(A), m(B)
            ok = t1 < 0.02 and b1 < 0.02
            allok &= ok
            print('   frame %5d  底帧 上%.4f/下%.4f → 叠字后 上%.4f/下%.4f  %s' % (
                f, t0, b0, t1, b1, '✓' if ok else '✗ 撞黑边'))
            if not ok:
                # 只输出越界那一块的范围
                for nm, sl in (('上', slice(0, 120)), ('下', slice(960, 1080))):
                    reg = B[sl]
                    ys, xs = np.where(reg.max(-1) > 0.02)
                    if len(ys):
                        print('       %s黑边异常像素：y %d–%d，x %d–%d，max=%.3f' % (
                            nm, ys.min() + sl.start, ys.max() + sl.start, xs.min(), xs.max(), reg.max()))
        if not allok:
            print('   ✗ 实拍帧有撞黑边')
            raise SystemExit(1)
    print('== 明细 → out/lyric_uni/geom_report.txt')
    return not bad


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'frame':
        cmd_frame(sys.argv[2], sys.argv[3], sys.argv[4])
    elif c == 'pairs':
        pairs()
    elif c == 'consist':
        consist()
    elif c == 'strips':
        strips([int(x) for x in sys.argv[2:]] or None)
    elif c in ('geom', '--guard', 'guard'):
        rest = [x for x in sys.argv[2:] if not x.startswith('--')]
        raise SystemExit(0 if guard([int(x) for x in rest] if rest else None) else 1)
    elif c == 'all':
        pairs()
        consist()
        strips()
