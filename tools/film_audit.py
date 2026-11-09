#!/usr/bin/env python3
"""tools/film_audit.py — 成片巡检：从**最终 mp4** 里逐镜抽帧，查崩帧/黑帧/白帧/卡帧，并出联系表

用法：
  python3 tools/film_audit.py --video out/snap_final/delivery/xxx_master_crf17.mp4 \
                              --shots /tmp/all_shots.json --out out/audit_final
判据（有效区 y=120..960）：
  - 全黑：luma.max() < 0.02        全白：luma.min() > 0.92        无内容：luma.std() < 0.012
  - 卡帧：相邻镜抽帧 luma 差 < 0.002 且 直方图相关 > 0.999（同一画面两镜）
"""
import argparse, json, pathlib, subprocess, sys

import numpy as np


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
    ap.add_argument('--video', required=True)
    ap.add_argument('--shots', default='/tmp/all_shots.json')
    ap.add_argument('--out', default='out/audit_final')
    a = ap.parse_args()
    out = pathlib.Path(a.out); raw = out / '_frames'; raw.mkdir(parents=True, exist_ok=True)
    rows = json.load(open(a.shots))
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
    for fp in ('fonts/NotoSerifSC-Bold.otf',):
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
