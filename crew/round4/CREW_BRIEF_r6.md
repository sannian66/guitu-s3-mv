# 第六棒 / 第九任总导演 开工简报（2026-11-09 12:45 CST 起，新沙箱）

## 环境
- 仓库：`/workspace/projects/5ef139c0-bc08-4b3b-ba11-a31305c292d4/work/guitu-s3-mv`，软链 `/workspace/work/mv`（代码路径写死，用这个）。
- 依赖已装（numpy pillow scipy opencv-python-headless skia-python librosa soundfile、libegl1 libgl1、ffmpeg）。2 核 7GB。
- **超过 1 帧的渲染必须 `tools/cpu_slot.sh <命令>` 排队**；杀自己进程用方括号写法，不许杀别人的。
- hooks 已装（commit 即推送）。总导演跑着每 3 分钟 autosync 循环 + 30 分钟定时任务兜底。

## 生图
- 12:45 Key 已接入（代理注入）；A、E 第六棒 8 张图已取回到 gen_cands/A_r6、gen_cands/E/E_r6。
- 旧沙箱的候选图（/workspace/work/a_cands、c_cands5、gen_cands/E/E_r6 等）多数已丢，以 `assets/gen/*` 为准。

## 同步（用户硬要求）
- 每个 shell 调用带 `credentials: [{"provider":"github"}]`。
- 只提交自己的路径：`git add <文件…> && git commit -m "[X组] …" -- <文件…>`；禁止 `git add -A`。
- 每完成一个可见步骤就 commit；看到 `PUSH FAILED` 立刻 `git pull --rebase --autostash origin main && git push origin HEAD:main`。

## 状态（12:22 用户给的表）
| 组 | 最新评审 | 状态 | 积分 | 下一步 |
|---|---|---|---|---|
| A | 72（r3） | 第六棒 4 图已提交未取 | 57/80 | 取图，改 V08/V09/V17 |
| B | ~73 | 第五棒返工中断 | – | 收尾 → 联系表 → 评审 |
| C | 69 | 第五棒返工中断 | – | 收尾 → 联系表 → 评审 |
| D | 84（r3） | 第六棒完（ce4acaf）：contact v9 / keys v5 | 45/80 | 第四轮评审中 |
| E | 72.5（r3） | 第六棒 4 图已出未入库 | 54/80 | 取图，改 E08/E02/E20 |

## 13:05 进度
| 组 | 评审 | 状态 |
|---|---|---|
| A | 72（r3） | 第六棒进行中（4 图已取回） |
| B | r2 = 74（精致度 10、不重复 6 未达线；V13 不可交付） | 第六棒返工中。裁定：86.19–89.40 归 B，V01/V02 换概念 |
| C | r3 = 76.5（精致度 10 未达线；C06、C41 不可交付） | 第六棒返工中 |
| D | r4 = 83.5 | 第七棒返工中（4 个 P0 + 第一幕光影） |
| E | 72.5（r3） | 第六棒进行中（4 图已取回） |
