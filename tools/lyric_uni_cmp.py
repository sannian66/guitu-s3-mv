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
    ('2_B_pre1',         'B 组 sec_b_pre1（44.0–59.5s）',       range(8, 12), True),
    ('3_chorus1',        '副歌一 chorus1（59.5–86.2s）',        range(12, 20), True),
    ('4_B_verse2',       'B 组 sec_b_verse2（86.2–117.8s）',    range(20, 28), True),
    ('5_C_pre2_chorus2', 'C 段 sec_c_pre2_chorus2（117.8–161.3s）', range(28, 40), True),
    ('6_D_bridge',       'D 段 sec_d_bridge（161.3–193.2s）',   range(40, 48), True),
    ('7_E_final_outro',  'E 段 sec_e_final_outro（193.2–241.3s）', range(48, 56), True),
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
    if os.environ.get('LYRIC_UNI_AUDIT') == '1':
        _audit_render(int(fr), out)
        return
    sys.argv = [sys.argv[0], 'status']            # prun 顶层会读 argv
    import numpy as np
    import prun
    from PIL import Image
    st = prun.load()
    img = prun.render_frame(int(fr), {}, st)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    Image.fromarray(img).save(out)


def _audit_render(fr, out):
    """LYRIC_UNI=1 渲一帧，同时记录「还有谁在画字」（file:line / 函数 / 文本）。"""
    import json
    import numpy as np
    import prun
    from PIL import Image
    st = prun.load()                       # 先 load（它负责把快照的 units/lib 塞进 sys.path）
    import lyric_uni as LU
    LU.audit_start()
    img = prun.render_frame(fr, {}, st)
    rec = LU.audit_take()
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    Image.fromarray(img).save(out)
    with open(out + '.audit.json', 'w', encoding='utf-8') as fh:
        json.dump(rec, fh, ensure_ascii=False)


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
        d.text((20, 46), '左右 = 改造前（本组原字幕） | 改造后（统一层 + 本段字幕层已关），右端 = 改造后字幕列全分辨率裁切'
                        + ('' if wired else '　⚠ 本段字幕层未接线'),
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
    d.text((10, 40), '7 段字幕层全部已接线关掉 → 画面里除右侧竖列外，只剩「镜头自己画的画内大字」（等 props_dev 用 OUT_CHARS 接管，见 outchars_table.md）',
           fill=(150, 200, 160), font=f_cap)
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


# ---------------------------------------------------------------- ③ 「道具接管 vs 字幕出字」对照表
def table():
    """把 props 组抽走的字（hidden_slots.json）与统一层实际出字对齐成一张表。

    - 每个槽位都过 out_chars(validate=True)：句号/字序/字/整句 必须和 lyrics.json+align 完全一致，
      对不上直接抛错（防两套规则打架）。
    - 同时给出 is_lyric 的判定口径（B 段守卫用的就是它）。
    """
    sys.path.insert(0, os.path.join(ROOT, 'units'))
    import lyric_uni as LU
    L = LU.lines()
    slots = LU.out_chars(validate=True)              # {(行号0基, 字序)}
    by = {}
    for (ln, k) in sorted(slots):
        by.setdefault(ln, []).append(k)
    # is_lyric 自检：每句整句、每句的每个 2 字滑窗都必须是 lyric
    bad = []
    for r in L:
        t = LU._clean(r['text'])
        if not LU.is_lyric(t):
            bad.append(('整句', r['line'], t))
        for i in range(len(t) - 1):
            if not LU.is_lyric(t[i:i + 2]):
                bad.append(('二字窗', r['line'], t[i:i + 2]))
    md = ['# 道具接管（OUT_CHARS）vs 统一层出字 对照表', '',
          '> 生成：`python3 tools/lyric_uni_cmp.py table`｜来源 `out/props_dev/hidden_slots.json`'
          '（45 槽）+ `lyrics.json` + `align.json`。槽位已逐条校验（句号/字序/字/整句全对得上）。', '',
          '- **props 接管** = 已被抽成画内道具、字幕层留空不画（`OUT_CHARS`，`LYRIC_UNI_OUT=1` 才启用）',
          '- **统一层出字** = 仍在右侧竖列里出的字', '',
          '## 总账', '',
          '| 项 | 数 |', '|---|---|',
          '| 歌词句 | %d |' % len(L),
          '| 总字数 | %d |' % sum(r['n'] for r in L),
          '| props 接管槽位 | **%d**（分布在 %d 句） |' % (len(slots), len(by)),
          '| 由统一层出字 | %d |' % (sum(r['n'] for r in L) - len(slots) - len(LU.in_scene_hide())),
          '| 整句都被道具接管 | %s |' % ('、'.join('第%d句' % (ln + 1) for ln, ks in sorted(by.items()) if len(ks) == L[ln]['n']) or '无'),
          '',
          '## 逐句对照', '',
          '| 句号 | 句 | 字数 | props 接管（字序:字） | 统一层出字 |', '|---|---|---|---|---|']
    for r in L:
        ks = by.get(r['line'], [])
        take = '、'.join('%d:%s' % (k, r['chars'][k]['ch']) for k in ks) or '—'
        hide = ks + [k for k in range(r['n']) if (r['line'], k) in LU.in_scene_hide()]
        keep = ''.join(c['ch'] if k not in hide else '□' for k, c in enumerate(r['chars']))
        md.append('| %d | %s | %d | %s | %s |' % (r['line'] + 1, r['text'].replace(' ', '·'), r['n'],
                                                  take, keep or '（整句被接管）'))
    ins = LU.in_scene_hide()
    md += ['', '## 画面内已有字（IN_SCENE）→ 字幕留空（不删画面里的字）', '',
           '> 分类口径：**in-scene** = 画面元素（刻/印/烧/散字/巨字），保留；**subtitle** = 字幕层，已加守卫关掉。', '',
           '| 来源（file:line） | 句 | 画面里的词 | 分类 | 说明 | 字幕里留空的字 |', '|---|---|---|---|---|---|']
    for (fn, line0), (li, w, why) in LU.IN_SCENE.items():
        r = L[li]
        blanks = [(k, c['ch']) for k, c in enumerate(r['chars']) if (li, k) in ins]
        md.append('| `%s:%d` | %d | %s | in-scene（保留） | %s | %s |' % (
            fn, line0, li + 1, w, why, '、'.join('%d:%s' % b for b in blanks)))
    sub = [('sec_a_intro_verse1.py', 2297, 'lyrics(fr,t)：整段 LY2 表', 'subtitle'),
           ('sec_c_pre2_chorus2.py', 2471, 'for s in SENTS: draw_sent(...)', 'subtitle'),
           ('chorus1.py', 'harness', 'C1_LYR=0（render_sprite_full.py:18-19 设）', 'subtitle'),
           ('sec_b_pre1.py', 133, "T.place(p['ch'])「写生死簿」整句", 'subtitle'),
           ('sec_b_pre1.py', 424, '「用血来装潢」竖排副句', 'subtitle'),
           ('sec_b_verse2.py', 811, '「可大局背后」竖排副句', 'subtitle'),
           ('sec_b_verse2.py', 852, '「是谁的」竖排副句', 'subtitle'),
           ('sec_b_verse2.py', 1541, '「不听天命」四字块', 'subtitle'),
           ('sec_b_verse2.py', 1836, '「若这世」竖排副句', 'subtitle'),
           ('sec_b_verse2.py', 1877, '「道黑白颠倒」竖排', 'subtitle'),
           ('sec_b_verse2.py', 1929, '「那就用刀」横排', 'subtitle'),
           ('sec_b_verse2.py', 1933, '「那就用」斩开版', 'subtitle'),
           ('sec_b_verse2.py', 2040, '「锋重新划」横排', 'subtitle'),
           ('sec_b_verse2.py', 1412, 'T.ink_bleed_in「可曾有机会」右列 104px ← 用户抓到的 f3050 双字幕', 'subtitle'),
           ('d_kit.py', 201, 'column()：D 段竖排字幕', 'subtitle'),
           ('d_kit.py', 464, 'song()：≤160px 字幕副句', 'subtitle'),
           ('e_kit.py', 246, 'Lyr.draw：≤160px 字幕整句', 'subtitle'),
           ('e_r5.py', 108, 'SubD.draw：副句暗衬 + 朱印', 'subtitle')]
    md += ['', '## 字幕层（subtitle）守卫点位 —— 已全部关掉', '',
           '| 来源（file:line） | 关掉的东西 | 分类 |', '|---|---|---|']
    for fn, line0, what, cls in sub:
        md.append('| `%s:%s` | %s | %s |' % (fn, line0, what, cls))
    md += ['', '## is_lyric 自检（B 段守卫的判定口径）', '',
           '- 判据：去空格/标点后，长度 ≥2 且是 56 句之一的子串 → True；单字 → 该字在歌词里出现过 → True',
           '- 自检：56 句整句 + 全部二字滑窗共 %d 项 → **%s**' % (
               len(L) + sum(r['n'] - 1 for r in L), '全通过' if not bad else '失败 %r' % bad[:5]),
           '', '## 已知「同一句既出字幕、又出画内大字」的段落（等 props 接管，不是字幕层的 bug）', '',
           '| 段 | 镜内大字（镜头自己画的，守卫管不到） | 与统一层重复的句 |', '|---|---|---|',
           '| A 段 | 五百 / 重甲 / 寒光 / 罪状 / 称量 / 杀 / 放 / 主张 / 正 / 锋芒 | 第 2、3、4、5、6、8 句 |',
           '| 副歌一 | 那就劈开它（`lyric3` 里 `skip=True` 的镜内版）、就是我的回答 | 第 15、19 句 |',
           '| B 段 | 善恶框 / 门扇金箔「谁的规矩」/ 纸面「当」压印（判为画内设计，守卫故意不拦） | 第 8、9、10 句 |',
           '| D 段 | 忍 / 让 / 判 / 陪葬（宣纸大字，走 `T.glyph` 直画，不过 `song()`） | 第 40、46、43 句 |',
           '| E 段 | 定 / 错 / 刀 / 谎言 / 正道沧桑（`Lyr` 已关，但这些是镜内直画） | 第 50、51、53、55 句 |', '']
    out = os.path.join(OUTDIR, 'outchars_table.md')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(md))
    print('table →', out, '| 槽位', len(slots), '| is_lyric 自检', 'PASS' if not bad else 'FAIL')
    return out


# ---------------------------------------------------------------- ⑥ 留空重排（compaction）三句三联图
def compact(frames=None):
    """三句「留空 ≥50%」重排后的三联图：左=纯字幕（黑底）/ 中=改造前 / 右=改造后。"""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    sys.path.insert(0, os.path.join(ROOT, 'units'))
    import lyric_uni as LU
    L = LU.lines()
    frames = frames or [5863, 5975, 2389]          # 第49句 血未冷刀不放 / 第50句 …天理昭彰 / 第18句 是非对错我自己扛
    jobs = []
    for f in frames:
        jobs.append((0, f, os.path.join(TMP, f'cmpct_{f}_before.png')))
        jobs.append((1, f, os.path.join(TMP, f'cmpct_{f}_after.png')))
    render(jobs)
    os.environ['LYRIC_UNI'] = '1'
    LU._maybe_out()
    pur = {}
    for f in frames:
        canvas = np.zeros((1080, 1920, 3), np.uint8)
        pur[f] = LU.draw(canvas, f)
    os.environ.pop('LYRIC_UNI', None)
    f_ttl = ImageFont.truetype(FONT, 26)
    f_cap = ImageFont.truetype(FONT, 19)
    f_sml = ImageFont.truetype(FONT_L, 16)
    TW, TH = 560, 315
    W = 20 + 3 * (TW + 16)
    H = 110 + len(frames) * (TH + 74)
    sheet = Image.new('RGB', (W, H), (14, 14, 15))
    d = ImageDraw.Draw(sheet)
    d.text((20, 12), '留空 ≥50% 的三句：改成「抽掉 + 上顺排」（列变短，不留空格）', fill=(236, 232, 224), font=f_ttl)
    d.text((20, 46), '左=纯字幕（黑底）｜中=改造前（各组原字幕）｜右=改造后（统一层）。逐字时间不动：被抽掉的字跳过，后面的字不提前',
           fill=(150, 165, 150), font=f_sml)
    d.text((20, 70), '画面里被让位的词仍在（朱印 / 鎏金巨字 / 印阵）—— 只把字幕里重复的那几个字抽掉', fill=(150, 165, 150), font=f_sml)
    for i, f in enumerate(frames):
        y = 110 + i * (TH + 74)
        tiles = [(Image.fromarray(pur[f]), '纯字幕（黑底，已重排）'),
                 (Image.open(os.path.join(TMP, f'cmpct_{f}_before.png')).convert('RGB'), '改造前'),
                 (Image.open(os.path.join(TMP, f'cmpct_{f}_after.png')).convert('RGB'), '改造后')]
        for j, (im, lab) in enumerate(tiles):
            x = 20 + j * (TW + 16)
            sheet.paste(_tile(im, TW, TH), (x, y))
            d.text((x, y + TH + 3), lab, fill=(228, 224, 216), font=f_cap)
        act = [r for r in L if r['t_on'] <= f / 30.0 < r['t_off']]
        if act:
            r = act[0]
            lay = LU.vis_layout(r, LU.IN_SCENE_HIDE)
            full = ''.join(c['ch'] for c in r['chars'])
            left = ''.join(p['ch'] for p in lay['pos'])
            ncol = max(1, (lay['n'] + 9) // 10)
            d.text((20, y + TH + 26), '第 %d 句 f%d：原句 %s（%d 字）→ 重排后 %d 字「%s」，%d 列 %dpx' % (
                r['line'] + 1, f, full, r['n'], lay['n'], left, ncol, r['size']),
                fill=(160, 156, 148), font=f_sml)
    out = os.path.join(OUTDIR, 'compact_three.jpg')
    sheet.save(out, quality=91)
    print('sheet', out, flush=True)
    return out


# ---------------------------------------------------------------- ⑤ 重复出字：审计 + 像素检测
def _picks21():
    """7 段 × 3 帧（每段取最长句 / 最短句 / 重音句中那帧）。"""
    L = _lines()
    out = []
    for name, title, rng, wired in SECTIONS:
        for r in pick_lines(L, rng):
            out.append((name, r['line'], fnum(t_of(r))))
    out.append(('EVIDENCE_f3050(用户证据帧)', 23, 3050))      # 用户抓到的双字幕帧，必须一直是 0 重复
    return out


def audit():
    """审计：LYRIC_UNI=1 时，字幕区里「还有谁在画字」（file:line / 函数 / 文本 / 字号）。"""
    import json
    from collections import defaultdict
    picks = _picks21()
    os.environ['LYRIC_UNI_AUDIT'] = '1'
    jobs = [(1, f, os.path.join(TMP, f'audit_{f}.png')) for _, _, f in picks]
    render(jobs)
    os.environ.pop('LYRIC_UNI_AUDIT', None)
    agg = defaultdict(lambda: dict(txt=set(), frames=[], sizes=set()))
    for _, ln, f in picks:
        p = os.path.join(TMP, f'audit_{f}.png.audit.json')
        if not os.path.exists(p):
            print('MISSING audit', f)
            continue
        for rec in json.load(open(p, encoding='utf-8')):
            k = (rec['f'], rec['line'], rec['fn'])
            agg[k]['txt'].add(rec['txt'][:18])
            agg[k]['frames'].append(f)
            if rec['size']:
                agg[k]['sizes'].add(int(rec['size']))
    rows = sorted(agg.items(), key=lambda kv: (-len(kv[1]['frames']), kv[0]))
    md = ['# 重复出字审计：LYRIC_UNI=1 时字幕区里还有谁在画字', '',
          '> 生成：`python3 tools/lyric_uni_cmp.py audit`（21 帧 = 7 段 × 3 句）。'
          '拦截口径：所有「第一个参数是帧（fr）」的 typo 绘制函数，记录调用者文件:行号 / 函数 / 文本 / 字号。', '',
          '| # | 来源 | 函数 | 文本 | 字号 px | 命中帧数 |', '|---|---|---|---|---|---|']
    for i, ((fn_, line, func), v) in enumerate(rows, 1):
        txt = '·'.join(sorted(t for t in v['txt'] if t)) or '—'
        md.append('| %d | `%s:%d` | %s | %s | %s | %d |' % (
            i, fn_, line, func, txt[:40], ','.join(str(s) for s in sorted(v['sizes'])) or '—', len(v['frames'])))
    out = os.path.join(OUTDIR, 'dup_audit_table.md')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(md) + '\n')
    print('audit →', out, '| 站点', len(rows), '| 帧', len(picks))
    for (fn_, line, func), v in rows[:40]:
        print('  %-22s:%-5d %-18s %s' % (fn_, line, func, '·'.join(sorted(t for t in v['txt'] if t))[:34]))
    return out


def _textmask(img, box):
    """字幕区里「像字」的像素：局部对比高的暗/亮笔画。"""
    import numpy as np
    import cv2
    x0, y0, x1, y1 = box
    reg = img[y0:y1, x0:x1].astype(np.float32) / 255.0
    L = reg[..., 0] * 0.299 + reg[..., 1] * 0.587 + reg[..., 2] * 0.114
    lo = cv2.GaussianBlur(L, (0, 0), 12)
    hp = np.abs(L - lo)
    m = (hp > 0.11).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    return m


def dupcheck(extra=None):
    """像素检测：字幕带（x>1500, 200<y<900）里除了「我的字形框」之外还有没有成句的字。

    用法（一行命令，#3 要求）：
        python3 tools/lyric_uni_cmp.py dupcheck                # 22 帧标准集（7 段×3 句 + 3050）
        python3 tools/lyric_uni_cmp.py dupcheck 3050 5011      # 额外加帧复检
    以后任何镜头新增「不走 typo 的私有字幕路径」都必须跑这条 —— audit 看不到私有路径，只有它能兜。
    """
    import numpy as np
    import cv2
    from PIL import Image
    sys.path.insert(0, os.path.join(ROOT, 'units'))
    import lyric_uni as LU
    picks = _picks21()
    for f in (extra or []):
        L = LU.lines()
        t = f / 30.0
        act = [r for r in L if r['t_on'] <= t < r['t_off']]
        picks.append(('EXTRA_f%d' % f, act[0]['line'] if act else 0, int(f)))
    jobs = [(1, f, os.path.join(TMP, f'dup_{f}.png')) for _, _, f in picks]
    render(jobs)
    rows, bad = [], []
    for name, ln, f in picks:
        p = os.path.join(TMP, f'dup_{f}.png')
        if not os.path.exists(p):
            continue
        img = np.asarray(Image.open(p).convert('RGB'))
        box = (1500, 200, 1920, 900)
        m = _textmask(img, box)
        # 挖掉我自己画的字形框（含 1px 描边与朱晕）
        os.environ['LYRIC_UNI'] = '1'
        LU._maybe_out()
        for r in LU.active(f / 30.0):
            for key in LU.vis_layout(r, LU.OUT_CHARS | LU.IN_SCENE_HIDE)['pos']:
                cx, cy = key['x'] - box[0], key['y'] - box[1]
                h = int(r['size'] * 0.78)
                cv2.rectangle(m, (int(cx - h), int(cy - h)), (int(cx + h), int(cy + h)), 0, -1)
        os.environ.pop('LYRIC_UNI', None)
        n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
        # 只留「像字」的块：高度/宽度都够、长宽比在汉字范围、面积够（排除雨丝/刀光/横向高光条）
        big = []
        for st in stats[1:]:
            w_, h_, a_ = int(st[2]), int(st[3]), int(st[4])
            if a_ < 220 or min(w_, h_) < 24:
                continue
            ar = w_ / float(max(1, h_))
            if not (0.30 <= ar <= 3.0):
                continue
            big.append((a_, w_, h_, int(st[0]), int(st[1])))
        # 归因：该帧还有哪些「画面内字」（来自 audit 记录 + IN_SCENE 分类表）
        att = []
        ap = os.path.join(TMP, f'audit_{f}.png.audit.json')
        if os.path.exists(ap):
            import json
            for rec in json.load(open(ap, encoding='utf-8')):
                ent = LU.IN_SCENE.get((rec['f'], rec['line']))
                if ent and ent[1] and ent[1] in (rec['txt'] or ''):
                    if ent[1] not in att:
                        att.append(ent[1])
        for (x, y, w_, h_, why) in LU.SCENE_OK.get(f, []):
            att.append('%s(场景高光)' % why)
        for (x, y, w_, h_, why) in LU.IN_SCENE_BOX.get(f, []):
            att.append('画面内字 ' + why)
        ok = (not big) or bool(att)
        bb = sorted(big, reverse=True)[:3]
        rows.append((name, ln, f, len(big), max([b[0] for b in big]) if big else 0, att, ok, bb))
        if not ok:
            bad.append((name, ln, f, len(big), max(b[0] for b in big), att))
    print('== 逐帧像素检测（字幕区 x1500–1920 / y200–900，挖掉我的字形框后剩下的「成块笔画」）')
    print('   判定：残留块 0 → 干净；有残留但能归到 IN_SCENE 画面内字（且字幕已留空）→ 干净；否则 ⚠ 重复')
    for name, ln, f, n_, mx, att, ok, bb in rows:
        print('   %-22s 第%2d句 f%5d  字形块 %2d  最大%5dpx  %s%s%s' % (
            name, ln + 1, f, n_, mx, '✓' if ok else '⚠ 未归因',
            ('  画面内字：' + '、'.join(att)) if att else '',
            ('  位置 ' + ','.join('%d,%d %dx%d' % (x, y, w_, h_) for a_, w_, h_, x, y in bb)) if bb and not ok else ''))
    with open(os.path.join(OUTDIR, 'dup_frames.md'), 'w', encoding='utf-8') as fh:
        fh.write('# 22 帧重复出字复检（像素检测 + 归因）\n\n')
        fh.write('| 段 | 句 | 帧 | 残留笔画块 | 最大面积 | 画面内字（已留空） | 判定 |\n|---|---|---|---|---|---|---|\n')
        for name, ln, f, n_, mx, att, ok, bb in rows:
            fh.write('| %s | %d | %d | %d | %d | %s | %s |\n' % (
                name, ln + 1, f, n_, mx, '、'.join(att) or '—', '✓ 干净' if ok else '⚠ 未归因'))
    print('== 判定：%d/%d 帧干净，重复 %d 处' % (len(rows) - len(bad), len(rows), len(bad)))
    return bad


# ---------------------------------------------------------------- ④ D 段三联图（亮底描边）
def dsheet(frames=None):
    """D 段三联图：左=纯字幕（黑底只画统一层）/ 中=改造前 / 右=改造后 + 亮底描边 3 帧条（带实测亮度）。

    三句取 白纸底(第41句) / 朱红底(第47句) / 暗余烬底(第44句)，覆盖「亮底触发描边」与「暗底不描边」。
    """
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    sys.path.insert(0, os.path.join(ROOT, 'units'))
    import lyric_uni as LU
    L = LU.lines()
    frames = frames or [5011, 5647, 5341]
    jobs = []
    for f in frames:
        jobs.append((0, f, os.path.join(TMP, f'dsheet_{f}_before.png')))
        jobs.append((1, f, os.path.join(TMP, f'dsheet_{f}_after.png')))
    render(jobs)
    os.environ['LYRIC_UNI'] = '1'
    pur = {}
    for f in frames:
        canvas = np.zeros((1080, 1920, 3), np.uint8)
        pur[f] = LU.draw(canvas, f)
    # 亮底描边 3 帧条：第 41 句白纸镜
    strip_f = [frames[0] - 1, frames[0], frames[0] + 1]
    info = []
    for f in strip_f:
        base = os.path.join(TMP, f'dsheet_strip_{f}.png')
        jobs2 = [(0, f, base)]
        render(jobs2)
        im = np.asarray(Image.open(base).convert('RGB'))
        info.append((f, LU.scrim_info(im, f)))
    os.environ.pop('LYRIC_UNI', None)

    f_ttl = ImageFont.truetype(FONT, 26)
    f_cap = ImageFont.truetype(FONT, 19)
    f_sml = ImageFont.truetype(FONT_L, 16)
    TW, TH = 560, 315
    SW = 344 + 142                            # 帧条一格宽（裁切 + 整帧）
    W = 20 + 3 * (TW + 16)
    H = 108 + 3 * (TH + 60) + 62 + 340
    sheet = Image.new('RGB', (W, H), (14, 14, 15))
    d = ImageDraw.Draw(sheet)
    d.text((20, 12), 'D 段三联图：左=纯字幕（黑底只画统一层）｜中=改造前（D 组原字幕）｜右=改造后（统一层 + 亮底破例描边）',
           fill=(236, 232, 224), font=f_ttl)
    d.text((20, 46), '亮底（中位亮度 ≥0.45）→ scrim 峰值 0.62 + 1px 黑×0.35 描边；暗底不描边。三句分别是白纸底 / 朱红底 / 暗余烬底',
           fill=(150, 165, 150), font=f_sml)
    d.text((20, 70), '本段字幕层已接线（d_kit.song / d_kit.column 守卫），所以中图是「只有 D 组原字幕以外的画面」= 原字幕已被关掉，画内大字保留',
           fill=(150, 165, 150), font=f_sml)
    for i, f in enumerate(frames):
        y = 108 + i * (TH + 60)
        tiles = [(Image.fromarray(pur[f]), '纯字幕（黑底）'),
                 (Image.open(os.path.join(TMP, f'dsheet_{f}_before.png')).convert('RGB'), '改造前'),
                 (Image.open(os.path.join(TMP, f'dsheet_{f}_after.png')).convert('RGB'), '改造后')]
        for j, (im, lab) in enumerate(tiles):
            x = 20 + j * (TW + 16)
            sheet.paste(_tile(im, TW, TH), (x, y))
            d.text((x, y + TH + 3), lab, fill=(228, 224, 216), font=f_cap)
        r0 = [r for r in L if r['t_on'] <= f / 30.0 < r['t_off']]
        d.text((20, y + TH + 26), 'frame %d（%.2fs）· %s · %d 字 %d 列 %dpx' % (
            f, f / 30.0, ('第 %d 句「%s」' % (r0[0]['line'] + 1, r0[0]['text'].replace(' ', '·'))) if r0 else '（无字幕）',
            r0[0]['n'] if r0 else 0, r0[0]['ncol'] if r0 else 0, r0[0]['size'] if r0 else 0),
            fill=(160, 156, 148), font=f_sml)
    y2 = 108 + 3 * (TH + 60)
    d.line([20, y2 - 12, W - 20, y2 - 12], fill=(70, 70, 78), width=1)
    d.text((20, y2), '亮底描边 3 帧条（连续 3 帧，同一镜）：实测背后中位亮度 / scrim 峰值 / 描边不透明度 —— 都不跳变 = 不闪',
           fill=(232, 200, 120), font=f_cap)
    for k, (f, inf) in enumerate(info):
        x = 20 + k * (SW + 16)
        p = os.path.join(TMP, f'dsheet_strip_{f}.png')
        if os.path.exists(p):
            im = Image.open(p).convert('RGB')
            sheet.paste(_tile(im.crop((1440, 150, 1832, 960)), 130, 290), (x, y2 + 30))
            sheet.paste(_tile(im, 344, 194), (x + 142, y2 + 30))
        if inf:
            d.text((x, y2 + 28 + 254), 'f%d 亮度中位 %.3f' % (f, inf['L']), fill=(210, 205, 195), font=f_sml)
            d.text((x, y2 + 28 + 274), '峰值 %.3f　描边 %.3f' % (inf['peak'], inf['outline']),
                   fill=(120, 210, 160) if inf['outline'] > 0 else (190, 190, 190), font=f_sml)
            d.text((x, y2 + 28 + 294), '最左列处 %.3f（%.0f%% 峰值）' % (inf['left_alpha'], 100 * inf['left_frac']),
                   fill=(150, 165, 220), font=f_sml)
    out = os.path.join(OUTDIR, 'd_three_panel.jpg')
    sheet.save(out, quality=91)
    print('sheet', out, flush=True)
    for f, inf in info:
        if inf:
            print('  f%d  L=%.3f peak=%.3f outline=%.3f left_alpha=%.3f' % (
                f, inf['L'], inf['peak'], inf['outline'], inf['left_alpha']))
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
    elif c == 'audit':
        audit()
    elif c == 'compact':
        compact([int(x) for x in sys.argv[2:] if not x.startswith('--')] or None)
    elif c == 'dupcheck':
        dupcheck([int(x) for x in sys.argv[2:] if not x.startswith('--')])
    elif c == 'dsheet':
        dsheet([int(x) for x in sys.argv[2:]] or None)
    elif c == 'table':
        table()
    elif c in ('geom', '--guard', 'guard'):
        rest = [x for x in sys.argv[2:] if not x.startswith('--')]
        raise SystemExit(0 if guard([int(x) for x in rest] if rest else None) else 1)
    elif c == 'all':
        pairs()
        consist()
        strips()
