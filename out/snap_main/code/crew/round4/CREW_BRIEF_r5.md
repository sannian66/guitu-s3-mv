# 第五棒 / 第八任总导演 开工简报（2026-11-09 12:00 CST 起，新沙箱）

## 环境（已就绪）
- 仓库：`/workspace/projects/d79262c3-6e04-4a12-8e03-b8eb93f884fc/work/guitu-s3-mv`，软链 `/workspace/work/mv`（代码路径写死，用这个）。
- 依赖已装：numpy pillow scipy opencv-python-headless skia-python librosa soundfile、libegl1 libgl1、ffmpeg。音频 `audio/谁定正邪.mp3` 在库。
- 沙箱 2 核 7GB。**超过 1 帧的渲染必须 `tools/cpu_slot.sh <命令>` 排队**。杀自己进程用方括号写法 `pkill -f '[s]ec_x_...'`，不许杀别人的。
- 旧沙箱的 `../gen_cands/` 候选图已丢；需要的候选重新生成或从 `assets/gen/*_raw.png` 取。

## 先读
1. `crew/round4/CHARTER.md`（章程：地盘、接口、硬性质量要求、评分表、过线 = 总分 ≥85 且每项 ≥70% 且无不可交付镜头）。
2. `crew/round4/HANDOFF_r4.md` 里本组最新一节；本组 `crew/round4/<组>_storyboard.md`；本组最新 `crew/round4/critic_<组>_r*.md`（评审意见 = 返工清单，P0 全修、P1 尽量修）。
3. `CLAUDE.md`（人物 = RH_image2 生图 + 抠图精灵；场景/字幕/卡点/运镜/粒子纯代码）。

## 生图（Nano Banana）
- 客户端 `tools/nb.py`（models / quote / upload / gen / poll），规则 `skills/nano-banana-skill/SKILL.md`。Key 由沙箱代理按域名注入，**任何文件、提交、消息里都不许出现 Key**。
- 默认 `RH_image2`，`size:"4K"`，每次提交前 quote；每张（含失败重抽）在 `crew/genlog.md` 追加一行。每组积分上限 80，本棒可再用到上限。
- 参考脸：`assets/characters/asset_urls.json` 的「男主_鬼屠」，五官发型一致（高马尾、中分乱刘海、琥珀眼、苍白清瘦），纯中性灰背景，便于 `python3 tools/recut_flat.py raw.png cut.png 16` 抠图。

## 同步（用户硬要求：防丢进度）
- 每个 shell 调用都带 `credentials: [{"provider":"github"}]`，否则推送静默失败。
- 五组共用一个 git index：**只提交自己的路径**：`git add <文件…> && git commit -m "[X组] 做了什么" -- <文件…>`。post-commit hook 会立刻推送；看到 `PUSH FAILED` 立即 `git pull --rebase --autostash origin main && git push origin HEAD:main` 处理。
- **每完成一个可见步骤就 commit**（一个镜头改完、一张联系表出来、一张生图采用）。不攒。总导演另有每 3 分钟 autosync 循环兜底。
- >50MB 不入库；mp4 预览不入库；联系表 jpg 入库。

## 交付（每组）
1. 按评审清单返工 `units/sec_<key>.py`（READY 保持 False）。
2. 重出联系表 + keys，并切成 ≤1920×1400 的分块（评审只看分块）：`out/round4/<组>_contact_vN_p*.jpg`、`out/round4/<组>_keys_vN_p*.jpg`。
3. 在 `crew/round4/HANDOFF_r4.md` 末尾追加本组「第五棒」一节（做了什么、积分、联系表路径、自评弱点、下一步），在 storyboard 记返工。
4. 回报总导演：同上要点 + 最后一个提交号。
