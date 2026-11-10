"""tools/r6_sync.py — 把 out/render_r6/done_base.tsv / done_sub.tsv 同步进 crew/round6/RENDER_r6.md 的块完成记录表。"""
import json, os
ROOT = '/workspace/work/mv'; R = ROOT + '/out/render_r6'
md = ROOT + '/crew/round6/RENDER_r6.md'
plan = {c['name']: c for c in json.load(open(ROOT + '/crew/round6/render_r6_chunks.json'))}
def rd(p):
    d = {}
    if os.path.exists(p):
        for l in open(p):
            x = l.rstrip('\n').split('\t')
            if len(x) >= 7: d[x[0]] = x
    return d
B, S = rd(R + '/done_base.tsv'), rd(R + '/done_sub.tsv')
rows = ['| 块 | 帧 [f0,f1) | 镜头 | 底层耗时 s | s/帧 | 底层 md5（FFV1 mkv） | 底层完成 | 字幕层耗时 s | 字幕层 md5（x264 mp4） |', '|---|---|---|---|---|---|---|---|---|']
for n, c in plan.items():
    b, s = B.get(n), S.get(n)
    nf = c['f1'] - c['f0']
    sh = c['shots'][0] + ('–' + c['shots'][-1] if len(c['shots']) > 1 else '') if c['shots'] else ''
    if b: rows.append(f"| {n} | {c['f0']}–{c['f1']} ({nf}) | {sh} | {b[3]} | {int(b[3]) / nf:.2f} | `{b[4]}` | {b[6]} UTC |")
    else: rows.append(f"| {n} | {c['f0']}–{c['f1']} ({nf}) | {sh} | … | | | |")
    rows[-1] += f" {s[3]} | `{s[4]}` |" if s else " | |"
txt = open(md).read()
head = txt.split('## 块完成记录')[0]
tail = ''
if '\n## 合成' in txt: tail = '\n## 合成' + txt.split('\n## 合成', 1)[1]
open(md, 'w').write(head + f'## 块完成记录（底层 {len(B)}/34，字幕层 {len(S)}/34）\n' + '\n'.join(rows) + '\n' + tail)
print(len(B), len(S))
