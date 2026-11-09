# 重复出字审计：LYRIC_UNI=1 时字幕区里还有谁在画字

> 生成：`python3 tools/lyric_uni_cmp.py audit`（21 帧 = 7 段 × 3 句）。拦截口径：所有「第一个参数是帧（fr）」的 typo 绘制函数，记录调用者文件:行号 / 函数 / 文本 / 字号。

| # | 来源 | 函数 | 文本 | 字号 px | 命中帧数 |
|---|---|---|---|---|---|
| 1 | `sec_e_final_outro.py:284` | compose | — | — | 3 |
| 2 | `sec_e_final_outro.py:284` | stamp_seal | 不·刀·放 | 751,781,801 | 3 |
| 3 | `chorus1.py:859` | compose | — | — | 1 |
| 4 | `chorus1.py:866` | seal_grid | 是非对错 | 540 | 1 |
| 5 | `d_kit.py:479` | compose | — | 30 | 1 |
| 6 | `sec_a_intro_verse1.py:844` | compose | — | — | 1 |
| 7 | `sec_a_intro_verse1.py:1784` | compose | — | — | 1 |
| 8 | `sec_a_intro_verse1.py:1784` | slash_layer | — | 560 | 1 |
| 9 | `sec_b_pre1.py:471` | compose | — | — | 1 |
| 10 | `sec_b_pre1.py:471` | scatter_stack | 我不信 | — | 1 |
| 11 | `sec_b_pre1.py:943` | burn_in | 滚烫 | 120 | 1 |
| 12 | `sec_b_pre1.py:943` | compose | — | — | 1 |
| 13 | `sec_b_verse2.py:1411` | compose | — | — | 1 |
| 14 | `sec_b_verse2.py:1411` | ink_bleed_in | 可曾有机会 | — | 1 |
| 15 | `sec_b_verse2.py:1627` | compose | — | — | 1 |
| 16 | `sec_b_verse2.py:1627` | scatter_stack | 不问 | — | 1 |
| 17 | `sec_d_bridge.py:914` | burn_in | 陪葬 | — | 1 |
| 18 | `sec_d_bridge.py:914` | compose | — | — | 1 |
| 19 | `sec_e_final_outro.py:359` | compose | — | 22 | 1 |
