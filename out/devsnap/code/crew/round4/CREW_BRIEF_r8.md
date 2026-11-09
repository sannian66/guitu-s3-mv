# 第八棒 / 第十一任总导演 开工简报（2026-11-09 14:12 CST 起，新沙箱）

## 环境（总导演 14:15 已就绪）
- 仓库：`/workspace/work/guitu-s3-mv`，软链 `/workspace/work/mv`（代码路径写死，用这个）。
- 依赖已装：numpy pillow scipy opencv-python-headless skia-python librosa soundfile + libegl1/libgl1、ffmpeg。2 核 7GB。
- hooks 已装（commit 即推送）。总导演跑着每 3 分钟 autosync 后台循环（`tools/autosync_loop.sh`）+ 30 分钟定时任务兜底（会重启循环）。
- 前任沙箱已丢；GitHub 上最后一次提交 149c727（14:05 自动同步）。以仓库为准，未入库的东西视为丢失。

## 同步 / CPU / 生图规则：照 CHARTER.md 与 CREW_BRIEF_r7.md，不变
- 每个 shell 调用带 `credentials: [{"provider":"github"}]`；只提交自己的路径；每个可见步骤就 commit。
- 超过 1 帧的渲染走 `tools/cpu_slot.sh`；只杀自己的进程（方括号写法）。
- 生图每组上限 80 点，先 quote，记 `crew/genlog.md`。

## 状态（14:07 前任交接）
| 组 | 评审 | 状态 | 本棒任务 |
|---|---|---|---|
| A | 80（r5），八项过线，总分差 5 | `units/a_r8.py`（镜内运动、V17 坑沿）已入库未接线；V20 蓄势图已生，积分 60/80 | 第八棒：按 critic_A_r5 P0/P1 接线 → 联系表 v8 / keys / rhythm → 送第六轮 |
| B | 74（r2），不过线 | 钟楼撞钟、六处金字互动、V14/V16/P15/P06 已推；联系表 v6 未出；P12 发型待核 | 第八棒：核对 critic_B_r2 全部 P0/P1 → 联系表 v6 + keys v6 → 送第三轮 |
| C | 85.5（r4）READY | C03–C05 皮影待核，联系表 v9 未出 | 打磨 critic_C_r4 余项，绝不退步 → 联系表 v9 → 复评 |
| D | 87.5（r5）READY | 完成 | 不动 |
| E | 85.0（r5）READY | `units/e_r8.py` 已入库；E01 待核；E23 冲白、E34 远影未改 | 打磨 critic_E_r5 余项 → 联系表 v8 → 复评 |

## 目标
全部五段过线（≥85、每项 ≥70%、无不可交付），然后总导演做全片接缝核查 + 整片渲染交付。
