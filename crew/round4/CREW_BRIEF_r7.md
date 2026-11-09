# 第七棒 / 第十任总导演 开工简报（2026-11-09 13:30 CST 起，新沙箱）

## 环境
- 仓库：`/workspace/projects/1427a278-c5df-414a-82bf-37a78a4be621/work/guitu-s3-mv`，软链 `/workspace/work/mv`（代码路径写死，用这个）。
- 依赖：numpy pillow scipy opencv-python-headless skia-python librosa soundfile、ffmpeg（总导演 13:30 已装）。2 核 7GB。
- **超过 1 帧的渲染必须 `tools/cpu_slot.sh <命令>` 排队**；杀进程只杀自己的。
- hooks 已装（commit 即推送）。总导演跑着每 3 分钟 autosync 后台循环 + 30 分钟定时任务兜底。
- 生图：`tools/nb.py`，Key 由代理注入（沙箱里不需要也不许写 Key）。每次提交前 quote，记 `crew/genlog.md`；每组积分上限 80。

## 同步（用户硬要求）
- 每个 shell 调用带 `credentials: [{"provider":"github"}]`。
- 只提交自己的路径：`git add <文件…> && git commit -m "[X组] …" -- <文件…>`；禁止 `git add -A`、`git commit -a`。
- 每完成一个可见步骤就 commit；看到 `PUSH FAILED` 立刻 `git pull --rebase --autostash origin main && git push origin HEAD:main`。

## 状态（13:21 用户给的表）
| 组 | 最新评审 | 停在哪 | 积分 | 下一步 |
|---|---|---|---|---|
| A | 72（r3） | 第六棒 P0 全改，联系表 v6 / keys v5 已推 | 57/80 | 补 HANDOFF 一节 → 第四轮评审 |
| B | 74（r2），V13 不可交付 | V13 已修；10 新图入库；V01/V02 改钟楼撞钟未渲染验证 | 75/80 | 验 V01/V02；金字改成字与物件互动；改 V14/V16、P15、P06；联系表 v6 |
| C | 76.5（r3），C06/C41 不可交付 | P0 四条已改（C06、C25、色差、C41） | 78/80 | P1（C35b 换脸、C33、C30、连续硬切）；联系表 v8 / keys v5 |
| D | 83.5（r4） | S12、补「矩」、S08 去「人」已改；S06 天平新图未验证 | 48/80 | 验 S06/S26；S08/S09 加光影；联系表 v10 → 第五轮评审 |
| E | 72.5（r3） | 第六棒做完，联系表 v6 / keys v6 已推 | 54/80 | 补 HANDOFF 一节 → 第四轮评审 |

## 本棒安排
- B、C、D 组各派一个执行子代理并行返工；A、E 由执行子代理补 HANDOFF 一节后，总导演派全新上下文评审。
- 评审规则不变（CHARTER.md）：≥85 且每项 ≥70%、无不可交付镜头才过线。
