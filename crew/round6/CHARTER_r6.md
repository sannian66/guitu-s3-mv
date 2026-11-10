# 第六轮剧组章程（2026-11-10 12:45 CST 起，总导演 = Hark）

用户原话：「接手github的项目……每次git都推送，并且要设置保底，实时同步到github……像剧组一样开工，做吧，打分，高质量交付，获奖级别。」

## 权威文档
- 需求：`crew/round5/USER_NOTES_r5.md`（54 条用户原话）
- 状态与返工意见：`crew/round5/HANDOFF_r5.md` 第 2、3、4 节（本轮从这里接）
- 本文件：第六轮分工、门槛、同步规则

## 沙箱环境（与 HANDOFF_r5 的 Mac 路径不同）
- 仓库在 `/workspace/work/mv`（代码里 ROOT 写死这个路径，不需要 devsnap 快照）。
- 渲单帧：`tools/rf_sb.sh <秒> <out.png>`（约 5 秒/帧）。2 核：并行渲染用 `tools/cpu_slot.sh` 包一层或串行。
- 依赖已装（含 libegl1/libgl1）；沙箱重置后：`pip install -r requirements.txt` + `sudo apt-get update && sudo apt-get install -y libegl1 libgl1`。
- 生图：`tools/gen_openai.py`（api.wentoken.si，Key 由代理在线路上注入；`~/.dsh/secrets/wentoken.key` 只是占位，**不入库**）。nananobanana 也可用（同样代理注入）。每张图（含失败）记 `crew/genlog.md`。
- 看图前把图降到 ≤1000 宽。

## 同步（硬规则）
1. `tools/hooks/post-commit`：每次 commit 立刻推 main（shell 调用必须带 github 凭据）。
2. 后台循环 `tools/autosync_loop.sh`：每 3 分钟 `autosync.sh`（提交+推送），日志 `/workspace/work/logs/autosync.log`。
3. 定时任务每 30 分钟兜底。
4. 每完成一个可见步骤（一段代码、一张对比图）就提交，前缀 `[X组 r6]` / `[总导演 r6 #53]`。Key 绝不入库。

## 流程与门槛
1. **#53 竖排歌词清理先做**（HANDOFF_r5 §4），独占各 section 文件。
2. 然后返工，同时 ≤3 组：F → E → D，再 A → B → C。
3. 每组交付：`crew/round6/<组>_r6.md`（逐条：改了什么、提交号、帧号）+ 改前/改后对比图 `out/round6/<组>_r6_compare*.jpg`（≤1600 宽，入库）。
4. 独立评审：新上下文的评审员只看对比图 + USER_NOTES 对应条目，逐条 0–10；**<8 打回**，最多返工两轮。
5. 全部过线后：全片并行分块渲染 → ffprobe 校验（1920×1080/30fps/7240 帧/有音轨）→ 全片联系表。

## 状态表
见 `crew/round6/STATUS_r6.md`（总导演维护）。
