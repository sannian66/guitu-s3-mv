# 第五轮 · 本机剧组任务书（2026-11-10，总导演）

权威需求：`crew/round5/USER_NOTES_r5.md`（用户 51 条原话 + #52 全片底部字幕，已在主线）。用户时间点 = 成片秒数（30fps，帧 = 秒 × 30）。
本轮在用户自己的 Mac 上跑（8 核 / 16G），**不再是远端沙箱**：

- **不跑 `autosync.sh`，不 push**。每完成一个可见步骤就**本地提交**，只提交自己的路径：
  `git add <路径> && git commit -m "[X组 r5] …" -- <路径>`（遇到 `index.lock` 就等几秒重试）。
- 用户审美、硬规则见 `COMPARE_BRIEF.md` 第 2、3 节（字是道具、配色纪律、对称构图不塞字、不做二维蒙皮）。

## 分组（帧区间不许改）

| 组 | 文件 | 帧 | 条目 |
|---|---|---|---|
| A | `units/sec_a_intro_verse1.py`（+ a_kit / a_r*.py） | 0–1321 | 1–12 |
| B | `units/sec_b_pre1.py` + `units/sec_b_verse2.py`（+ b_kit） | 1321–1784, 2586–3534 | 13–19, 29–33 |
| F | `units/chorus1.py` + `units/chorus1_sprites.py`（+ c1kit） | 1784–2586 | 20–28（用户点名要改，「标杆不许动」本轮作废） |
| C | `units/sec_c_pre2_chorus2.py`（+ c_kit） | 3534–4839 | 34–42，43 的 157–161.3s 部分 |
| D | `units/sec_d_bridge.py`（+ d_kit / d_r*.py） | 4839–5797 | 43 的 161.3s 起，44，45，46 的 182–193.2s 部分 |
| E | `units/sec_e_final_outro.py`（+ e_kit / e_r*.py） | 5797–7241 | 46 的 193.2s 起，47–51，以及「何须伪装」新创意（见下） |

各组只改自己的文件。共享文件（`units/sprite.py`、`units/subtitle.py`、`render_sprite_full.py`、`units/sections.py`、`fx.py`、`scenes.py`）**不要改**；确实需要就在报告里写，由总导演改。

## 文字规则
- 全片歌词字幕由 `units/subtitle.py` 统一画在下黑边，**保留**。用户说「去掉文字」= 去掉画内道具字/标题字，不是去掉底部字幕。
- 用户说保留的保留；**用户没提到的文字不动**。

## 本机渲染
```bash
SNAP=$PWD/out/devsnap_<组> tools/rf.sh 22.0 out/round5/<组>/after_22.0.png        # 改后（同步工作区 → 自己的快照 → 渲帧）
NOSNAP=1 SNAP=$PWD/out/devsnap_base tools/rf.sh 22.0 out/round5/<组>/before_22.0.png  # 改前（冻结在 c1511ea 的基线快照）
```
- 一帧约 5–100s。**同一时间最多 2 个渲染进程**（6 组共享 8 核）。不要渲整片 mp4（总导演最后统一渲）。
- 时序效果（转场、动作、文字动画、卡点）必须出**帧条**：切点/动作前后各 4 帧（9 帧）拼一张图看，单帧验收会骗人。
- 基线快照的 `assets/` 是软链到工作区的：**不许覆盖或删除已有资产文件**，新资产一律新文件名，放 `assets/gen/R5_<组>/`。

## 生图
- **统一纯绿幕 `#00FF00`**，抠图 `tools/cutout_green.py raw.png out_cut.png 2048`（本机没有 rembg，`tools/cutout.py` 不能用）。
- 首选渠道 `tools/gen_openai.py`（OpenAI 协议，`gpt-image-2`，支持多参考图编辑，单张 40–70s）：
  `WENTOKEN_KEY=$(cat ~/.dsh/secrets/wentoken.key) python3 tools/gen_openai.py <jobs.json>`，job 格式见 `docs_openai_channel.md`。**不要传 size**。
  人物参考图（PNG）：`assets/characters/png/男主_鬼屠.png`、`最终boss_太上皇.png` 等。同一角色换姿势时，把相邻镜头已有生图也作为参考图传入，锁画风。
- 备用渠道 `tools/nb.py`（RH_image2 4K = 3 积分）：`NANO_BANANA_KEY=$(cat ~/.dsh/secrets/nb_skills.key) python3 tools/nb.py …`。
- 男主设定：高马尾、中分乱刘海、琥珀眼、苍白清瘦；黑衣、暗红内领、皮护腕、长刀黑柄、刀鞘红穗。画风 = 写实电影感暗调水墨，与相邻镜头一致。
- **每张都记 `crew/genlog.md`**（gen_openai.py 会自动追加）。Key 只从 `~/.dsh/secrets/` 读，绝不写进任何仓库文件。
- 预算：**不设上限**（用户 2026-11-10：「图片不吝啬地出，不设额度，以最好的作品为目的」）。同一镜头多抽几版挑最好的；动作镜头可以出多张关键姿势做顺滑过渡。

## 人物通用改进（每组都做，限自己的镜头）
1. **发丝**：总导演在跑全局「绿幕重抠」，产出 `<名>_gcut.png` 与旧 `_cut.png` 对齐，由 `render_sprite_full.py` 统一替换（`GCUT=1`）。各组不用管旧图重抠；**新出的图直接绿幕生图**。
2. **头发飘动**：自己镜头里的人物精灵，凡是走 `SpriteLayer.draw` 的都开 `wind_amp`（5–8px，发梢/衣摆，脸和刀不动）；直接贴图没走 SpriteLayer 的，改走 SpriteLayer 或用同样的风网格。帧条里要看得出飘动，又不能像果冻。

## 「何须伪装」（E 组，约 210.4–214.0s）
用户创意：把人物轮廓抠出来，人物整个涂成黑色剪影，脸部是一个「？」，「何须伪装」四个字写在身体里面。
- 竖排写在躯干内，字色取宣纸白/骨白（或血红点睛一字）；「？」放在脸的位置，与字同一种字体气质。
- 和 #46「3:32 之后其他文字去掉」不冲突：这个镜头的字是剪影里的道具字。

## 交付（每组）
- `crew/round5/<组>_r5.md`：逐条写「条目 / 怎么改的 / 核对帧（秒）/ 自评分 0–10」，加一节「发丝与飘动」。
- `out/round5/<组>_r5_compare.jpg`：每条一对改前/改后帧（≤1920 宽，可多张）；时序条目附帧条。
- **自评低于 8 分的条目要再改一轮**。交付后总导演另派**独立上下文的评审**（只看用户原话 + 改前/改后图，不看你的报告）打分，低于 8 分的条目会打回重做。以用户的眼光挑刺：「像贴上去的」「抢注意力」「像坏了」「画风不一致」「被裁切」都是不及格。
