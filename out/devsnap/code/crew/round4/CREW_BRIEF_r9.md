# 第九/十棒 · 第十二任总导演开工简报（2026-11-09 16:05 CST 起，新沙箱）

## 环境（总导演已就绪）
- 仓库：`/workspace/projects/c2263c6d-ad1c-435a-bda7-f2e1040a152a/work/guitu-s3-mv`，软链 `/workspace/work/mv`（代码路径写死，用这个）。
- 依赖已装（numpy pillow scipy opencv-python-headless skia-python librosa soundfile、libegl1/libgl1、ffmpeg）。2 核 7GB。
- hooks 已装（commit 即推送）。总导演跑每 3 分钟 autosync 后台循环 + 30 分钟定时任务兜底。
- GitHub 上接手时最后提交 634d411（15:14 自动同步）。

## 防丢进度（用户硬规则，比以往更严）
- 总导演可能因额度不足随时停下，那时它的循环和定时任务都会失败。**各组子代理自己负责保住进度**：
  1. 每完成一个可见步骤立刻 `git add <自己的文件> && git commit -m "[X组] ..." -- <自己的文件>`（hook 自动推送；看到 PUSH FAILED 立即 `git pull --rebase --autostash origin main && git push origin HEAD:main`）。
  2. 每次提交前看一眼 `tail -1 /tmp/autosync_loop.log`；若不存在或最后时间早于 6 分钟前，用 background shell（带 github credentials）重启 `./tools/autosync_loop.sh 1170`。
  3. 长渲染每 5–10 分钟或每个分块提交一次。
- 每个 shell 调用都带 `credentials: [{"provider":"github"}]`。

## CPU / 生图 / 地盘：照 CHARTER.md 与 CREW_BRIEF_r7/r8，不变
- 超过 1 帧的渲染走 `tools/cpu_slot.sh`；只杀自己的进程（方括号写法）。
- 生图：先试 `tools/nb.py` quote；上沙箱 401 无 Key，若仍 401 就纯代码改，不要卡住。

## 状态与本棒任务
| 组 | 评审 | 本棒任务 |
|---|---|---|
| A | 83（critic_A_r6），各项过线，差总分 2 | 按 r6 P0/P1；补 keys v8 + 节奏表 v3 + 联系表 → 写交接 → 派第七轮独立评审 |
| B | 77（critic_B_r3），精致度 10/15，V18/V08 不可交付（第九棒已修手） | V01 改冷灰去红团做撞钟、V02 人海动起来（去复制阵列）、其余 P1 → 三张表 → 第四轮评审 |
| C | 88（critic_C_r5）READY | 第十棒已推 6 处；重渲改动帧，与 v9 对比确认无退步 → 联系表 v10 → 复评（不得低于 88） |
| D | 87.5 READY | 不动 |
| E | 88 READY | 本轮不动（可选 P1 留后） |

## 目标
五段全部过线并往「获奖级」推，然后总导演做全片接缝核查 + 整片渲染交付。
