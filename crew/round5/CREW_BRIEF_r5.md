# 第五轮剧组任务书（2026-11-09 21:45 CST，总导演）
权威需求：`crew/round5/USER_NOTES_r5.md`（用户 52 条原话）。用户时间点 = 成片秒数（30fps，帧 = 秒×30）。

## 分组（帧区间不许改）
| 组 | 文件 | 帧 | 条目 |
|---|---|---|---|
| A | units/sec_a_intro_verse1.py | 0–1321 | 1–12 |
| B | units/sec_b_pre1.py + units/sec_b_verse2.py | 1321–1784, 2586–3534 | 13–19, 29–33 |
| F（副歌一） | units/chorus1.py（及 units/chorus1_sprites.py） | 1784–2586 | 20–28 |
| C | units/sec_c_pre2_chorus2.py | 3534–4839 | 34–42, 43 的 157–161.3s 部分 |
| D | units/sec_d_bridge.py | 4839–5797 | 43 的 161.3–162s 部分, 44, 45, 46 的 182–193.2s 部分 |
| E | units/sec_e_final_outro.py | 5797–7241 | 46 的 193.2s 起部分, 47–51 |

## 共同规则
- 全片歌词字幕已由总导演统一加在 `render_sprite_full.frame`（`units/subtitle.py`，下黑边居中）。各组不用再画字幕；用户要求去掉的字直接去掉，用户说保留的保留，**用户没提到的文字不动**。
- 渲帧核对：`python3 render_sprite_full.py frame <秒> /tmp/x.png`（已含字幕；B 组 READY 已置 True）。多帧渲染用 `tools/cpu_slot.sh` 包一层（只有 2 核，6 组共享）。不要渲整片 mp4（总导演最后统一渲）。
- 生图：`python3 tools/nb.py`（Key 在 .env.local，已可用；RH_image2 4K 16:9 = 3 积分，提交前 quote）。人物参考 `assets/characters/asset_urls.json` 的男主_鬼屠（高马尾、中分乱刘海、琥珀眼、苍白清瘦；黑衣暗红内领、皮护腕、长刀黑柄红穗）。画风与相邻镜头的已有生图一致（写实电影感暗调水墨）。抠图 `tools/cutout.py`。每张记 `crew/genlog.md`。新资产放 `assets/gen/R5_<组>/`。
- 同步（硬规则）：每完成一个可见步骤就提交，只加自己的路径：`git add <路径> && git -c user.name=sannian66 -c user.email=38859572+sannian66@users.noreply.github.com commit -m "[X组 r5] …" -- <路径>`（post-commit hook 自动推送；shell 必须带 github 凭据）。
- 交付：`crew/round5/<组>_r5.md` 逐条写「条目 / 怎么改的 / 核对帧（秒）/ 自评分（0–10）」，并出一张改前改后对比联系表 `out/round5/<组>_r5_compare.jpg`（每条一对帧，≤1920 宽）。自评低于 8 的条目要再改一轮。
- Key 绝不能提交；仓库是公开的。
