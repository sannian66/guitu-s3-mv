"""把与用户的沟通记录导出为 crew/CONVERSATION.md（autosync.sh 每次同步前自动运行）。
前七任已冻结在 crew/CONVERSATION_part6.md（含 part1–5）；之后的会话从各 journal 目录读取并追加。"""
import json, glob, os, re
REDACT = re.compile(r'(?:bsk__|sk-)[A-Za-z0-9._\-]{12,}')   # 公开仓库：Skills Key / OpenAI 协议 Key 一律打码
HERE = os.path.dirname(os.path.abspath(__file__))
JS = ['/workspace/projects/d79262c3-6e04-4a12-8e03-b8eb93f884fc/.hark/journal']   # 第八任（2026-11-09 11:48 起，新沙箱）；前七任已冻结在 CONVERSATION_part6.md
rows = []
if not any(os.path.isdir(J) for J in JS): JS = []  # 第八任 journal 不在本沙箱：用冻结的 part7
for J in JS:
    for f in sorted(glob.glob(J + '/*.jsonl')):
        for l in open(f, encoding='utf-8'):
            try: rows.append(json.loads(l))
            except Exception: pass
out = [open(os.path.join(HERE, 'CONVERSATION_part7.md'), encoding='utf-8').read().rstrip()] if not JS else [open(os.path.join(HERE, 'CONVERSATION_part6.md'), encoding='utf-8').read().rstrip(), '', '---', '', '## 第八任接手（2026-11-09 11:48 起，新沙箱）', '']
for r in rows:
    if r.get('role') not in ('user', 'assistant'): continue
    who = '用户' if r.get('role') == 'user' else 'Hark'
    out += [f'### {who} · {r.get("time","")}', '', REDACT.sub('***Key已打码***', r.get('text', '').strip()), '']
open(os.path.join(HERE, 'CONVERSATION.md'), 'w', encoding='utf-8').write('\n'.join(out))
# 第九任（2026-11-09 12:40 起，新沙箱 / 新项目）
J9 = '/workspace/projects/5ef139c0-bc08-4b3b-ba11-a31305c292d4/.hark/journal'
rows9 = []
for f in sorted(glob.glob(J9 + '/*.jsonl')):
    for l in open(f, encoding='utf-8'):
        try: rows9.append(json.loads(l))
        except Exception: pass
if rows9:
    out9 = ['', '---', '', '## 第九任接手（2026-11-09 12:40 起，新沙箱）', '']
    for r in rows9:
        if r.get('role') not in ('user', 'assistant'): continue
        who = '用户' if r.get('role') == 'user' else 'Hark'
        out9 += [f'### {who} · {r.get("time","")}', '', REDACT.sub('***Key已打码***', r.get('text', '').strip()), '']
    open(os.path.join(HERE, 'CONVERSATION.md'), 'a', encoding='utf-8').write('\n'.join(out9))
print('exported', len(rows), len(rows9))
