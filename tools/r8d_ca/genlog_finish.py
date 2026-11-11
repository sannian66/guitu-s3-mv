"""genlog_CA.md 收尾：标注采用 / 弃用、逐字核对结果、积分合计（一次性整理脚本）。"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
p = ROOT + '/crew/round8/genlog_CA.md'
L = open(p).read().split('\n')
DROP = {'C10_tablets': '「大」左上多一点（错字）→ 重抽', 'C20_emp': '太上皇外形与定妆照不符（有须、无黑纱袍）→ 用太上皇定妆照重抽',
        'C02_hand': '同上，袖子不是黑纱 → 用太上皇定妆照重抽'}
OK = {'C01_paper': '「谁定好规则」五字逐字放大核对全对，朱圈圈住「规则」', 'C02_tags': '七字「谁写好剧本提纲」逐字核对全对',
      'C10_tablets': '「大局为上」四字逐字核对全对（大 = 三笔无点）', 'C16_blood': '「血」字形正确', 'C21_split': '「邪」「正」字形正确'}
out = []
for l in L:
    if '| R8_D/CA/' in l and '采用' not in l and '弃用' not in l:
        n = l.split('|')[2].strip().split('/')[-1]; tr = 'try2' in l
        if n in DROP and not tr:
            l = l.replace('| 已出图 |', '| ✘ 弃用 |').rstrip(' |') + '；' + DROP[n] + ' |'
        else:
            l = l.replace('| 已出图 |', '| ✔ 采用 |')
            if n in OK and (n != 'C10_tablets' or tr): l = l.rstrip(' |') + '；' + OK[n] + ' |'
    out.append(l)
s = '\n'.join(out).rstrip('\n')
if '合计' not in s:
    s += ('\n\n合计：36 张 × 3 = **108 积分**（采用 33 张，弃用 3 张；预算上限 130）。'
          '入库 assets/gen/R8_D/CA/：抠像 _cut.png 25 张 + 背景板 .jpg 8 张。\n')
open(p, 'w').write(s)
