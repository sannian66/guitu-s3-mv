# 第四轮「剧组开工」章程（2026-11-09 08:50 CST 起）

## 为什么有这一轮
用户看完全片精灵版截图的原话：「除了精修部分（副歌一），其他部分的水准还没跟上。」要避免：
**节奏慢、画面简单、重复多、画面不够精致、分镜不够有设计感、没有转场、歌词文字排版简单**。
目标：**商业交付**。每段都要达到或超过副歌一（`units/chorus1.py`，59.47–86.2s）的水准，由**独立上下文的评审**打分，不过线就返工。

## 分组与地盘（只许改自己的文件）
| 组 | 段落 key（units/sections.py） | 帧区间 | 镜头 | 自己的文件 |
|---|---|---|---|---|
| A | a_intro_verse1 | 0–1321 | S001–S019 | units/sec_a_intro_verse1.py、crew/round4/A_*.md、out/round4/A_* |
| B | b_pre1 + b_verse2 | 1321–1784、2586–3534 | S020–S027、S047–S060 | units/sec_b_pre1.py、units/sec_b_verse2.py、crew/round4/B_* |
| C | c_pre2_chorus2 | 3534–4839 | S061–S092 | units/sec_c_pre2_chorus2.py、crew/round4/C_* |
| D | d_bridge | 4839–5797 | S093–S110 | units/sec_d_bridge.py、crew/round4/D_* |
| E | e_final_outro | 5797–7241 | S111–S138 | units/sec_e_final_outro.py、crew/round4/E_* |
| 标杆 | 副歌一 | 1784–2586 | S028–S046 | units/chorus1.py（**任何组不许改**） |

- 组内可以新建辅助模块，文件名必须带组前缀：`units/a_*.py`、`lib/` 下不许新建同名覆盖。
- 共享库 `lib/typo.py`、`lib/trans.py`、`lib/fx2.py`、`lib/sk.py`、`units/sprite.py`、`units/vcam*.py`、`units/c1kit.py`：**只许新增函数，不许改已有函数的签名和行为**（副歌一依赖它们）。新增的写进 `crew/round4/lib_changes.md`（组名、函数、用途）。
- `units/rest_sprites.py`、`scenes.py`：旧版，不改；需要里面的东西就 import 或复制到自己的模块。
- 段落边界帧不许改。和相邻段的接缝（第一帧/最后一帧）要能接上：入口/出口转场写清楚在 `crew/round4/<组>_storyboard.md` 的「接缝」一节。

## 接口
`units/sec_<key>.py` 必须提供：
```python
READY = False          # 评审过线后由总导演改 True；组内自测用环境变量 V4_FORCE=<key>
def frame(f: int, cache: dict) -> np.ndarray  # uint8 (1080,1920,3) RGB，成品帧（含黑边 1920×840 有效区、颗粒、暗角）
```
可以照抄 `units/chorus1.py` 的组织方式：每镜一个类、CUTS 表驱动转场、`lyric3.py`/`lib/typo.py` 出字、`units/sprite.py` 贴人物精灵。

## 素材
- 人物 = 生图 + 抠图精灵（`assets/gen/<镜号>/<姿势>_raw.png / _cut.png`，现有 ~90 张）。场景、字幕、卡点、转场 = 纯代码。
- 需要新精灵就生：`tools/nb.py`（报价 → 生成 → 轮询，规则见 `skills/nano-banana-skill/SKILL.md`；沙箱里 Key 由代理注入，**Key 绝不写进任何文件**）。参考图用 `assets/characters/asset_urls.json` 里的角色设定图 URL。
  - 每组积分上限 **80 点**（RH_image2 4K 约 3 点/张）。用户说了「不用吝啬积分」，但每次提交前仍要 quote，并在 `crew/genlog.md` 记一行（时间、镜号、点数、task_id、结果）。
  - 抠图：`python3 tools/recut_flat.py raw.png cut.png 16`（纯灰底，色差+填洞，效果好）；rembg 没装。
  - 角色一致：鬼屠（男主，黑发高马尾、黑衣、刀）、太上皇（白发长袍，权力方）。prompt 写清只要哪一部分（手/背影/剪影），纯中灰背景。
- 歌词逐字时间：`align.json` / `lyric3.py` / `typo.load_lines()`；节拍：`analysis.npz`；鼓件卡点法见 `units/hitmap.py`（可以给自己的段跑一份）。
- 原分镜（v2 导演组）：`crew/storyboard.md` + `crew/shots.json` 是起点，**不是圣旨**：可以重切镜头、改设计，但要在自己的 storyboard 里写明改了什么、为什么。

## 硬性质量要求（评审按这个打分）
1. **节奏**：切点落拍（或人声首字），副歌/高潮段平均镜头时长 ≤ 1.5s，主歌 ≤ 2.5s；每个镜头内部要有运动（运镜/人物/粒子/光），不许出现静止超过 1 拍的画面。
2. **分镜设计感**：每镜写明构图意图（景别、视线引导、前中后景三层、母题）；相邻镜头景别/方向交替；至少 3 个匹配剪辑或图形匹配。
3. **精致度**：光影有层次（主光、轮廓光、体积光/雾）、质感（纸、雨、墨、金属）、无抠图毛边、无穿帮、无糊团、人物不顶头不被裁坏。
4. **不重复**：同一精灵在本段最多用 2 次且必须换景别/方向/处理；不许复用旧 `scenes.py` 的同一场景超过 1 次；和副歌一、其他段不撞画面。
5. **转场**：每个切点都要有设计（硬切也要有冲击：闪、抖、色偏、遮挡）；本段至少 5 种不同转场（`lib/trans.py` 已有 20 种：match_cut、slash_wipe、ink_bleed、whip_pan_blur、paper_tear、shatter、occlusion、iris_moon、smoke_through、zoom_through…）。
6. **歌词排版**：按 `crew/storyboard.md` 第 4 节「每段一套，不复用」；字要和画面互动（被斩开、刻在刀上、随雨落、烧穿…），逐字/逐拍出现，关键字朱红/金；可读、不压脸、不出画。
7. **人物**：精灵统一调色（与场景同光向、同色温），表演姿势和歌词对应。
8. **情绪/叙事**：符合本段在全片叙事弧（长夜→雨夜→风暴之眼→破晓）里的位置。

## 评审（独立上下文）
- 每组交付后，总导演派一个**全新上下文**的评审子代理，只给它：本段联系表、关键帧、本章程的评分表、用户原话。它看不到你的设计说明，不受你说服。
- 评分表（100 分）：节奏卡点 15 · 分镜设计 15 · 精致度 15 · 歌词排版 15 · 不重复 10 · 转场 10 · 人物 10 · 情绪叙事 10。
- **过线 = 总分 ≥ 85 且每项 ≥ 该项满分的 70%，且没有「不可交付」镜头**。不过线 → 按评审意见返工 → 再派新评审。最多 3 轮。

## 同步（用户硬要求：实时，跟着提交走，不靠定时）
- 仓库装了 hooks（`git config core.hooksPath tools/hooks`）：**每次 commit 前自动导出对话，commit 后立刻前台推送 GitHub（带重试，失败会打印 `PUSH FAILED`）**。
- **5 个组共用一个 git index：禁止 `git add -A` / `git commit -a` / `./autosync.sh`。只提交自己的路径：`git add <文件> && git commit -m "[X组] ..." -- <文件>`**（08:57 评审的提交误卷入 E 组 15 个暂存文件后定的）。
- 所以：**每完成一个可见步骤就 commit**（一个镜头做完、一张联系表出来、一次返工），commit 信息写「[组名] 做了什么」。shell 调用必须带 `credentials: [{"provider":"github"}]`。
- 看到 `PUSH FAILED` 要立刻处理（通常是 pull --rebase 冲突），不能放着。
- `>50MB` 文件不入库；out/round4/ 下的联系表 jpg 入库（每张 <2MB），mp4 预览不入库。

## CPU（沙箱 2 核、5 个组共用）
- 单帧测试随便跑。**超过 1 帧的渲染（联系表、片段）必须用 `tools/cpu_slot.sh <命令>` 包一层**，它会排队拿 2 个槽之一。
- 联系表：`V4_FORCE=<key> tools/cpu_slot.sh python3 tools/sec_contact.py <key> out/round4/<组>_contact_vN.jpg`
- 不许 `pkill` 别人的进程。杀自己的进程用方括号写法 `pkill -f '[s]ec_a_...'`，否则会杀掉自己的 shell。
- 新沙箱重建：`mkdir -p /workspace/work && ln -sfn /workspace/projects/bb073534-bbd7-4972-8ee7-8269af99396f/work/guitu-s3-mv /workspace/work/mv（10:44 起第七任新沙箱）`；`pip install numpy pillow scipy opencv-python-headless skia-python librosa soundfile`；`sudo apt-get update && sudo apt-get install -y libegl1 libgl1`。

## 每组交付物
1. `crew/round4/<组>_storyboard.md`：逐镜表（时间、景别、构图意图、运镜、人物精灵、歌词排版手法、入/出转场、改动理由），以及「接缝」一节。
2. `units/sec_<key>.py`（READY=False）。
3. `out/round4/<组>_contact_vN.jpg` 联系表 + `out/round4/<组>_keys_vN.jpg`（转场中间帧、歌词关键帧各若干）。
4. 回报总导演：做了什么、用了多少积分、联系表路径、自评哪里还弱。
