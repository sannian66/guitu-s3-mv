# 第二棒任务书（2026-11-09 09:25 CST，第五任总导演，新沙箱）
你是《谁定正邪》MV 第四轮剧组的 <组> 组，接手本组第一棒的初稿。仓库：/workspace/work/mv（= sannian66/guitu-s3-mv，GitHub 公开仓库）。
## 先读
1. crew/round4/CHARTER.md（章程：地盘、接口、评分表、提交规则、CPU 规则）——全部遵守。
2. crew/round4/HANDOFF_r1.md 本组一节（第一棒停在哪、已知 bug/风险）。
3. crew/round4/critic_baseline.md 本段扣分点；units/chorus1.py（标杆写法，只读）。
## 这一棒要交付
1. 让 units/sec_<key>.py 每一镜都能跑通（逐镜单帧试渲修报错），单帧尽量 ≤3s。
2. 按章程 8 条硬性要求自查并补强：消灭矢量占位感、重复精灵、静止画面；每个切点有设计；歌词排版每段一套、和画面互动。
3. 写本组联系表脚本（按自己 SHOTS/CUT 表逐镜取中点帧，不用 tools/sec_contact.py），用 tools/cpu_slot.sh 包一层渲出 out/round4/<组>_contact_v1.jpg 与 <组>_keys_v1.jpg（转场中间帧 + 歌词关键帧），自己用 read_file 看图挑毛病再返工至少一轮（v2）。
4. 写/补 crew/round4/<组>_storyboard.md（逐镜表 + 接缝）。
5. 需要新精灵：python3 tools/nb.py（先 quote 再生成再轮询；Key 由代理注入，绝不写进文件），每张记 crew/genlog.md；本组积分上限 80（含已用）。
## 防丢进度（用户硬要求）
- 每完成一个可见步骤立刻提交并推送：`git add <自己的路径> && GIT_AUTHOR_NAME=sannian66 GIT_AUTHOR_EMAIL=38859572+sannian66@users.noreply.github.com GIT_COMMITTER_NAME=sannian66 GIT_COMMITTER_EMAIL=38859572+sannian66@users.noreply.github.com git commit -m "[<组>组] ..." -- <自己的路径>`。post-commit hook 自动推送；每个 git 命令的 shell 调用必须带 credentials [{"provider":"github"}]。看到 PUSH FAILED 立刻 pull --rebase 处理。禁止 git add -A / commit -a / autosync.sh。
- 长渲染每 5–10 分钟提交一次中间产物。
## 停下的条件
- 同一个报错修两次还不过，记进 storyboard 的「未决」并跳过，别死循环。
- 完成或预算/时间不够时：在 crew/round4/HANDOFF_r2.md 追加本组一节（做了什么、积分、联系表路径、自评弱点、下一步），提交推送后回报总导演。
