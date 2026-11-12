"""genlog_CA.md 第二次收尾（评审第一轮返工）：新出的 3 张标「采用」，被替换的旧图标「弃用（评审返工替换）」，合计改为 39 张 117 积分。"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
p = ROOT + '/crew/round8/genlog_CA.md'
L = open(p).read().split('\n')
out = []
REPLACED = {('C20_emp', 'try2'): '评审第一轮 P0-2 返工：换成两套姿势（try3 C20_emp 正面 + C20_turn 回头），黑发为主',
            ('C17_kneel', 'try1'): '评审第一轮 P1-12 返工：刀被画成十字剑 → try4 直刀中式护手'}
NEW = {'C20_emp': '回头前正面姿势（黑发为主、髻与黑簪露出）', 'C20_turn': '回头后 3/4 侧身抬手姿势；C21 太上皇也用这张',
       'C17_kneel': '直刀 + 中式护手 + 黑柄 + 红穗'}
for l in L:
    if l.startswith('合计：'):
        continue
    if '| R8_D/CA/' in l:
        cols = l.split('|'); n = cols[2].strip().split('/')[-1]
        tr = 'try4' if 'try4' in l else 'try3' if 'try3' in l else 'try2' if 'try2' in l else 'try1'
        if (n, tr) in REPLACED and '✔ 采用' in l:
            l = l.replace('| ✔ 采用 |', '| ✘ 弃用 |').rstrip(' |') + '；' + REPLACED[(n, tr)] + ' |'
        if '| 已出图 |' in l and tr in ('try3', 'try4'):
            l = l.replace('| 已出图 |', '| ✔ 采用 |').rstrip(' |') + '；' + NEW.get(n, '') + ' |'
    out.append(l)
s = '\n'.join(out).rstrip('\n')
s += ('\n\n合计：39 张 × 3 = **117 积分**（预算上限 130）。采用 34 张，弃用 5 张：C10_tablets try1（错字）、C20_emp try1 / C02_hand try1'
      '（不像太上皇定妆照）、C20_emp try2 与 C17_kneel try1（评审第一轮返工替换）。'
      '入库 assets/gen/R8_D/CA/：抠像 _cut.png 26 张 + 背景板 .jpg 8 张。\n')
open(p, 'w').write(s)
print('ok')
