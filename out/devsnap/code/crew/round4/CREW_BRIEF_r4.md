# 第四棒任务书（2026-11-09 11:00 CST，第七任总导演，新沙箱）
你是《谁定正邪》MV 第四轮剧组的 <组> 组，接手本组第三棒。仓库：/workspace/work/mv（软链到 /workspace/projects/bb073534-bbd7-4972-8ee7-8269af99396f/work/guitu-s3-mv，= GitHub 公开仓库 sannian66/guitu-s3-mv）。
目标：用户要求「像剧组一样开工，高质量交付，获奖级别」。本段评审过线 = 总分 ≥85 且每项 ≥70% 且无不可交付镜头；本棒按 ≥90 来做。

## 环境（先自检，缺了就装，别重复装）
`python3 -c "import numpy,cv2,skia,librosa"` 报错时：`pip install -q numpy pillow scipy opencv-python-headless skia-python librosa soundfile && sudo apt-get install -y -qq libegl1 libgl1`。`git config core.hooksPath` 应为 tools/hooks（否则 `./tools/install_hooks.sh`）。

## 先读
1. crew/round4/CHARTER.md（地盘、接口、评分表、提交规则、CPU 规则）——全部遵守。
2. crew/round4/HANDOFF_r3.md：本组一节 + 「总导演记录（第六任）」里给本组的下一步（A 组的返工方案就在那里，照做）。
3. 本组最新评审 crew/round4/critic_<组>_r*.md（按 P0→P1→P2 返工，P0 与「不可交付镜头」必须全部解决）；未评过的组看 critic_baseline.md 本段扣分点。
4. units/chorus1.py（标杆，只读）。

## 生图已恢复（本棒新变化）
- Nano Banana Key 已在 Hark 保险库、按域名自动注入：`python3 tools/nb.py quote/gen/poll` 直接可用（10:46 验证：RH_image2 4K 16:9 = 3 积分）。**Key 绝不写进任何文件。** 规则见 skills/nano-banana-skill/SKILL.md。
- 之前因 401 搁置的精灵现在就生：D defy_up（统一 S11/S24 面孔）；E21 仰望侧脸 + 低机位跨步；C tools/c_gen.py 五张；A 刀身特写/纸人群（如需）。每张先 quote，记 crew/genlog.md，本组上限 80（含已用）。人物一致性：参考 assets/characters/asset_urls.json 的「男主_鬼屠.webp」。

## 这一棒要交付
1. 返工 units/sec_<key>.py，逐镜单帧试渲确认跑通。
2. 全段共性问题一律避免（同第三棒任务书 CREW_BRIEF_r3.md 第 2 条：白闪≤1、whip≤1、转场中间帧带前后镜元素、居中小剪影+程序天空≤2 镜、字幕安全区与可读、停用角落小竖排、程序道具要有轮廓光/材质、人物一致）。
3. 联系表 + keys 新版本（tools/<组小写>_contact.py，外包 tools/cpu_slot.sh）。**联系表必须切成 ≤1920×1400 的块再 read_file 看**（大图读不出来）。自己看图挑毛病再改至少一轮。
4. 更新 crew/round4/<组>_storyboard.md（返工记录 + 接缝 + 未决）。

## 防丢进度（用户硬要求）
- 每完成一个可见步骤立刻提交并推送：`git add <自己的路径> && GIT_AUTHOR_NAME=sannian66 GIT_AUTHOR_EMAIL=38859572+sannian66@users.noreply.github.com GIT_COMMITTER_NAME=sannian66 GIT_COMMITTER_EMAIL=38859572+sannian66@users.noreply.github.com git commit -m "[<组>组] ..." -- <自己的路径>`。post-commit hook 自动推送；**每个 git 命令的 shell 调用必须带 credentials [{"provider":"github"}]**。看到 PUSH FAILED 立刻 pull --rebase 处理。禁止 git add -A / commit -a / autosync.sh。
- 至少每 10 分钟有一次提交；长渲染每完成一块就提交中间产物。

## 停下的条件
- 同一个报错修两次还不过，记进 storyboard「未决」并跳过。
- 完成或约 60 分钟到时：在 crew/round4/HANDOFF_r4.md 追加本组一节（做了什么、积分、联系表/keys 路径、对照评审逐条处理、自评弱点、下一步），提交推送后回报总导演：一段话 + 联系表路径。
