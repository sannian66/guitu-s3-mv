# 第六轮分组返工任务书（通用部分）

1. 先读 crew/round6/CHARTER_r6.md、crew/round5/USER_NOTES_r5.md（用户原话，权威）、crew/round5/HANDOFF_r5.md 第 2、3、5、6、7 节中本组条目、本组 round5 报告 crew/round5/<组>_r5.md、#53 交付 crew/round6/VLYR_abf.md / VLYR_cde.md。
2. 只改本组文件（HANDOFF_r5 §5 代码地图）。共享文件不许改：units/sprite.py、units/subtitle.py、units/sections.py、units/fx.py、units/scenes.py、render_sprite_full.py。#53 加的 R5_NOVLYR 开关保留。
3. 渲帧：tools/rf_sb.sh <秒> <png>，2 核且有 3 个组并行 → 一律用 tools/cpu_slot.sh 包一层、串行渲；看图前缩到 ≤1000 宽，一次别看太多张。不渲整片 mp4。不要用 timeout 粗暴杀渲染（会留坏缓存）。
4. 生图：python3 tools/gen_openai.py（api.wentoken.si，Key 由代理注入，不用管 Key；不传 size）。参考定妆照 assets/characters/png/男主_鬼屠.png（高马尾、中分乱刘海、琥珀眼、苍白清瘦、黑衣暗红内领、无头带、无红唇）；太上皇 assets/characters/png/最终boss_太上皇.png。绿幕 #00FF00 + tools/cutout_green.py 抠。本组本轮生图上限 12 张（含重抽），每张记 crew/genlog.md。
5. 质量线 = 获奖级 MV：构图完整（头顶留白、脚入画、刀不被裁）、动作可读、光影统一、与鼓点卡点、没有坏帧/白团/硬边/残影。每条先自评 0–10，<8 的继续改。
6. 同步：每完成一条就提交，前缀「[X组 r6]」，只 git add 自己的路径；所有 git 的 shell 调用必须带 credentials [{"provider":"github"}]，确认 hook 输出 pushed。Key 绝不入库。
7. 交付：crew/round6/<组>_r6.md（每条：用户原话、改了什么、提交号、证据帧秒数、自评分）+ 改前/改后对比图 out/round6/<组>_r6_compare*.jpg（≤1600 宽，入库；改前用 git stash 或开关回滚渲）。九帧条要求的条目要给九帧条。
8. 拿不准用户意思的先按保守做法，列进报告「待问用户」。同一问题循环超过两次就停下回报。
