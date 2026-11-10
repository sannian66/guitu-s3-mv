# 第六轮 15:10 后子代理通用须知（总导演写）
1. 仓库 /workspace/work/mv（main）。先读 crew/round6/CHARTER_r6.md、STATUS_r6.md、crew/round5/USER_NOTES_r5.md 里你负责的条目、你组的 <组>_r6.md 和最近的 REVIEW_<组>_r6*.md。
2. 每个 shell 调用凡涉及 git 都必须带 credentials: [{"provider":"github"}]，否则推送静默失败。
3. 每完成一条（一段代码 / 一张对比图）立刻：只 git add 自己的路径 → commit（前缀 `[X组 r6]`）→ post-commit 会自动推送，看到 `[post-commit] pushed` 才算数。不要攒。
4. 同时把进度追加进 crew/round6/<组>_r6.md（逐条：改了什么、提交号、帧号、自评分），这份文件本身也要随每次提交更新——你随时可能被中断，文件就是交接。
5. 渲染：单帧 tools/rf_sb.sh <秒> <out.png>；多帧必须 tools/cpu_slot.sh 包一层（只有 2 核，另有 2 组同时在跑）。看图前降到 ≤1000 宽。
6. 生图：tools/gen_openai.py（Key 代理注入，绝不写入仓库）；每张图记 crew/genlog.md。仓库公开，Key/token 一律不许入库。
7. 自评 <8 的条目不许交付，继续改；全部 ≥8 后出改前/改后对比图 out/round6/<组>_r6*_compare*.jpg（≤1600 宽，入库）。
8. 遇到同一个问题循环超过两次，停下，把现状和卡点写进报告并提交，然后回报。
9. 回报时给：逐条状态、提交号、自评分、仍需用户拍板的问题。
