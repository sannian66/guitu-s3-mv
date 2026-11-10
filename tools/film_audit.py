#!/usr/bin/env python3
"""tools/film_audit.py — 成片巡检：从**最终 mp4** 里逐镜抽帧，查崩帧/黑帧/白帧/卡帧，并出联系表

用法（main 第六轮移植版，audit-qp2）：
  python3 tools/film_audit.py --video out/film_r6/delivery/谁定正邪_MV_1080p30_master_crf17.mp4 --out out/round6/film_audit
  python3 tools/film_audit.py --dump-shots /tmp/shots_main.json      # 只导出镜头表，不抽帧
--shots：JSON 列表 [[段, 镜号, t0秒, t1秒], ...]；省略时从 main 的 units/sec_*.py / chorus1.py 的 SHOTS 现取
（只 import，不渲染；约 1 秒）。帧区间与 units/sections.py 一致。
判据（有效区 y=120..960）：
  - 全黑：luma.max() < 0.02        全白：luma.min() > 0.92        无内容：luma.std() < 0.012
  - 卡帧：相邻镜抽帧 luma 差 < 0.002 且 直方图相关 > 0.999（同一画面两镜）
"""
import argparse, json, pathlib, subprocess, sys

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parent.parent
SECS = [('A', 'sec_a_intro_verse1'), ('B1', 'sec_b_pre1'), ('F', 'chorus1'), ('B2', 'sec_b_verse2'),
        ('C', 'sec_c_pre2_chorus2'), ('D', 'sec_d_bridge'), ('E', 'sec_e_final_outro')]


def shots_from_code():
    """main 各段的镜头表 → [[段, 镜号, t0, t1]]（秒）。sec_e 用 IDS/BOUNDS（帧），其余 SHOTS 类带 t0/t1（秒）。"""
    import os
    os.environ.setdefault('SPRITE_MODE', '1')
    for d in (ROOT / 'units', ROOT / 'lib', ROOT):
        sys.path.insert(0, str(d))
    import sections
    rng = {'sec_' + k: (f0 / 30.0, f1 / 30.0) for k, f0, f1, *_ in sections.SECTIONS}
    rng['chorus1'] = (1784 / 30.0, 2586 / 30.0)          # render_sprite_full.C1_F0/C1_F1
    rows = []
    for tag, mod in SECS:
        M = __import__(mod)
        if hasattr(M, 'IDS') and hasattr(M, 'BOUNDS'):
            raw = [(M.IDS[i], M.BOUNDS[i] / 30.0, M.BOUNDS[i + 1] / 30.0) for i in range(len(M.IDS))]
        else:
            raw = [(s.__name__, float(s.t0), float(s.t1)) for s in M.SHOTS]
        lo, hi = rng[mod]                               # 只取本段实际接管的区间（chorus1 的表含段外镜）
        for sid, t0, t1 in raw:
            t0, t1 = max(t0, lo), min(t1, hi)
            if t1 - t0 > 1 / 30.0:
                rows.append([tag, sid, t0, t1])
    return rows


def grab(video, t, out):
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{t:.3f}', '-i', video,
                    '-frames:v', '1', str(out)], check=True)


def stats(png):
    from PIL import Image
    a = np.asarray(Image.open(png).convert('RGB'), np.float32) / 255.0
    reg = a[120:960]
    lum = reg[..., 0] * 0.299 + reg[..., 1] * 0.587 + reg[..., 2] * 0.114
    hist = np.histogram(lum, bins=32, range=(0, 1))[0].astype(np.float32)
    hist /= max(1.0, hist.sum())
    return dict(mean=float(lum.mean()), std=float(lum.std()), mx=float(lum.max()), mn=float(lum.min()), hist=hist)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', help='成片 mp4')
    ap.add_argument('--shots', help='镜头表 JSON（省略 = 从 main 代码现取）')
    ap.add_argument('--dump-shots', metavar='JSON', help='只把镜头表写到这里然后退出')
    ap.add_argument('--out', default='out/round6/film_audit')
    a = ap.parse_args()
    rows = json.load(open(a.shots)) if a.shots else shots_from_code()
    if a.dump_shots:
        json.dump(rows, open(a.dump_shots, 'w'), ensure_ascii=False)
        print(a.dump_shots, len(rows), '镜'); return
    if not a.video:
        ap.error('需要 --video（或用 --dump-shots 只导镜头表）')
    out = pathlib.Path(a.out); raw = out / '_frames'; raw.mkdir(parents=True, exist_ok=True)
    res = []
    for i, (tag, sid, t0, t1) in enumerate(rows):
        t = t0 + 0.55 * (t1 - t0)
        p = raw / f'{i:03d}.png'
        if not p.exists():
            grab(a.video, t, p)
        s = stats(p); s.update(tag=tag, sid=sid, t=t, idx=i)
        res.append(s)
    bad = []
    for s in res:
        if s['mx'] < 0.02: bad.append((s, '全黑'))
        elif s['mn'] > 0.92: bad.append((s, '全白'))
        elif s['std'] < 0.012: bad.append((s, '无内容'))
    stuck = []
    for a_, b_ in zip(res, res[1:]):
        if abs(a_['mean'] - b_['mean']) < 0.002 and float((a_['hist'] * b_['hist']).sum()) > 0.999:
            stuck.append((a_, b_))
    lines = [f'# 成片巡检 · {pathlib.Path(a.video).name}', '',
             f'- 抽帧：{len(res)} 镜（每镜 55% 位置）',
             f'- 崩/黑/白帧：**{len(bad)}**',
             f'- 相邻镜疑似卡帧（画面几乎相同）：**{len(stuck)}**', '']
    for s, why in bad:
        lines.append(f'- ⚠ {why}：{s["tag"]} {s["sid"]} @ {s["t"]:.2f}s')
    for x, y in stuck:
        lines.append(f'- ⚠ 卡帧：{x["tag"]} {x["sid"]} → {y["tag"]} {y["sid"]}（{x["t"]:.2f}s → {y["t"]:.2f}s）')
    lines += ['', '## 逐镜亮度（有效区）', '', '| # | 段 | 镜号 | 时刻 | mean | std |', '|---|---|---|---|---|---|']
    for s in res:
        lines.append(f'| {s["idx"]} | {s["tag"]} | {s["sid"]} | {s["t"]:.2f}s | {s["mean"]:.3f} | {s["std"]:.3f} |')
    (out / 'report.md').write_text('\n'.join(lines))
    # 联系表（按段）
    from PIL import Image, ImageDraw, ImageFont
    font = None
    for fp in (str(ROOT / 'fonts/NotoSerifSC-Bold.otf'),):
        if pathlib.Path(fp).exists():
            font = ImageFont.truetype(fp, 15); break
    tags = []
    for s in res:
        if s['tag'] not in tags: tags.append(s['tag'])
    for tag in tags:
        grp = [s for s in res if s['tag'] == tag]
        cols = 6; TW, TH = 320, 180
        rr = (len(grp) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * TW, rr * (TH + 20) + 26), (16, 16, 18))
        d = ImageDraw.Draw(sheet)
        d.text((8, 4), f'成片巡检 · {tag} · {len(grp)} 镜', fill=(235, 215, 150), font=font) if font else None
        for k, s in enumerate(grp):
            im = Image.open(raw / f'{s["idx"]:03d}.png').convert('RGB').resize((TW, TH), Image.LANCZOS)
            x, y = (k % cols) * TW, (k // cols) * (TH + 20) + 26
            sheet.paste(im, (x, y))
            if font:
                d.text((x + 4, y + TH + 2), f'{s["sid"]} {s["t"]:.2f}s', fill=(210, 200, 140), font=font)
        sheet.save(out / f'audit_{tag}.jpg', quality=86)
    print(f'{out}/report.md  崩帧 {len(bad)} / 卡帧 {len(stuck)}')


if __name__ == '__main__':
    main()
