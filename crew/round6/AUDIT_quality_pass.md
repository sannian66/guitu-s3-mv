# feat/quality-pass 游离提交审计（audit-qp，第六轮 15:12 派）

> 范围：STATUS_r6 15:10 列出的「10 个游离提交」逐条核对 main（HEAD 1a7298b）是否已有等效修复。
> 只读审计：未改渲染代码、未合并分支。验证帧在 `out/round6/audit_qp/`（main 当前代码，`tools/rf_sb.sh` 单帧）。

## 先说清口径（与交接书不一致处）

- `git log main..origin/feat/quality-pass` 实际是 **64 个提交**（`git cherry`：63 个无等效补丁，1 个是 revert 已在 main），不是 10 个。
  分叉点 `f3c7f74`（11-09 17:36）。之后 **branch 与 main 是两条平行线**：branch 走「第 1 批 51 条」（`crew/round4/user_notes_r1.md`，统一字幕层 `units/lyric_uni.py`），
  main 走「第五轮 52→55 条」（`crew/round5/USER_NOTES_r5.md`，字幕 `units/subtitle.py` + 第六轮返工）。两边处理的是**同一批用户意见**，main 后来又有评审打分和 #53/#55 新口径。
- 总导演列出的 10 项 = branch 最后一段（11-09 23:25 → 11-10 07:07）的用户返工 + 交付，本表逐条核。其余 54 个提交（grade_unify 胶片 look、转场去重、道具化 14 处、rig、批量工具）不在本次范围，末尾单列提示。
- 两份冻版母版（5fa55b3 02:09 / bf7e401 06:08）**不在仓库里**（`out/snap_final/delivery/` 只在用户本机），且内容是 branch 线的成片，已落后于 main 第五/六轮。

## 逐条结论

| # | 提交 | 内容 | main 是否已覆盖 | 证据 | 建议 |
|---|---|---|---|---|---|
| 1 | 5fa55b3 / bf7e401 | 冻版 1080p30 母版（7240 帧）+ 返工版母版；顺带 `lib/trans.py` 补 `luma` 转场（CUTS 引用了不存在的名字导致 480–600 帧崩块） | **不需要**：母版是 branch 线产物、不入库、内容已过时；main 的全片渲染是 STATUS_r6 阶段 5「待」。`luma` 崩溃是 branch 自己的转场去重（3b3b0b6）在 sec_a V04 / sec_c C22 新引用造成的；main 只有 C13 用 `luma`，走 `units/c_trans.py` 的 `CX.NAMES['luma']`（第 37/209 行），不经 `lib/trans.TRANSITIONS`，不会崩 | `units/sec_c_pre2_chorus2.py:2489,2679`；`units/c_trans.py:37,209` | 已覆盖 / 不移植。可选：阶段 5 全片渲染时可参考 branch 的 `tools/render_film.sh`（分块+拼接+混音校验）和 `tools/film_audit.py`（逐镜抽帧查崩/黑/卡），这两个工具 main 没有 → **需总导演拍板**是否移植工具 |
| 2 | 7b1ebff | #23 1:10 跳斩换新精灵（S035_leap_new / S035_slash_new，2 姿势）；并在 S035Sprite 里 LYRIC_UNI=1 时不再画底部「那就劈开它」 | **已覆盖（做法更进一步）**：main F 组用 5 张 R5_F 姿势（963f32f）→ r6 第三棒 e1e5f8a 用 crouch/apex/strike/land 四姿势；「那就劈开它」改成墙面阴刻（y≈252，画内上方），不再压底部。最近评审 REVIEW_F_r6b #23=7 仍在 F 组返工中 | `units/chorus1_sprites.py:194–211`（POSES=R5_F/js1/js3/js4/js5）；帧 `out/round6/audit_qp/main_70.3.png`：上方阴刻 + 底部只有一行字幕 | 已覆盖。branch 的 2 张旧精灵**不移植**（比 main 现有姿势少，且已被评审线取代） |
| 3 | f668d99（+7b1ebff） | #27 1:24 转圈挥刀改「剑光 + 闪白」，关键是改 `chorus1_sprites.S045Sprite` 而非基类 | **已覆盖**：main 4d8aaa3 在 S045Sprite 做了蓄势→横贯剑光→满屏闪白→收刀定格（R5_F/s45_follow_a），r6 第二棒补了猩红月连续性；REVIEW_F_r6b #27=**8 过线** | `units/chorus1_sprites.py:518–525`；`crew/round6/REVIEW_F_r6b.md:22` | 已覆盖，不移植 |
| 4 | d6309ba | 副歌一旧字幕层（lyric3 `SENTENCES` / `self.lyr.draw`）在 LYRIC_UNI=1 时仍在画 → 底部叠字；按开关整段关 | **已覆盖（且按 #55 有意保留了一部分）**：main 用 `R5_NOVLYR`（默认 1）整层关掉 lyric3（`chorus1.py:1710`），但按总导演 13:30 对 #55 的裁定，横排句（血未冷/天不判/我来量，y=850 画内、不进下黑边字幕区）通过 `lyr_h` 保留、「骨未凉」改 S039 镜内横排 | `units/chorus1.py:27–33, 1576–1590, 1627–1630, 1710`；帧 `main_70.3.png`：底部只有一份「那就劈开它看个天亮」 | 已覆盖。**不要移植** branch 的「整段关闭」——会把 #55 要求保留的横排句一起删掉（被用户后续意见推翻） |
| 5 | dc49791 | 19 张主角/太上皇精灵整张换成「AI 重绘到纯绿幕→色键」新版 | **已覆盖（main 有意换了做法）**：main 012c8ca「绿幕重抠全量融合 178 张，**只换边缘发丝、身体内部与旧图逐像素一致**」，GCUT 默认开（`render_sprite_full.py:18,46`）；ffc2b74 写明原因是**防止换脸**。branch 是整张替换（AI 重绘），会改脸/服饰细节，与 main 后来按定妆照（`assets/characters/png/男主_鬼屠.png`）返工的方向冲突 | `render_sprite_full.py:18–46`；`crew/round5/HANDOFF_r5.md` §6 GCUT；提交 012c8ca / ffc2b74 | 已覆盖，**不移植**（branch 做法被 main 有意推翻） |
| 6 | 8a7572e ① | 字幕去底色（不画 scrim，只留按底亮度自适应的极淡描边） | **已覆盖**：main 字幕是 `units/subtitle.py`，白字 + 4px 柔阴影，放在下黑边内（中心 y=1020），**没有任何底色/横带** | `units/subtitle.py:1–43`；帧 `main_70.3.png` / `main_143.3.png` 底部 | 已覆盖，不移植 |
| 7 | 8a7572e ② + 0d1a213（22s） | V05/V06 画内「寒光」巨字去掉（含 V06 斩开分支清空字层） | **未覆盖，且 main 方向相反**：main 保留「寒光」并在 r6 A 组第二棒挪到人物右侧、逐字点亮（`sec_a_intro_verse1.py:868–952`）；文件头注释把寒光列为「镜内互动字不动」（第 30 行）。依据是用户 11-10 13:01 #55「镜里横排或刻、写、印出来的歌词字保留（如五百重甲、锋芒…）」。但 branch 记录用户 11-09 23:2x 点名要去「寒光」巨字、11-10 03:52 又指认「没改」再改了一次 | `units/sec_a_intro_verse1.py:30, 868–952`；帧 `out/round6/audit_qp/main_21.9.png`（寒光两字在人物右侧，被斩开） | **需用户拍板**。时间上 #55 更晚，倾向保留现状（视为被 #55 推翻）；但用户曾两次点名删寒光，#55 例子里没列寒光，建议一句话问清：「22s 的『寒光』两个大字留还是去？」 |
| 8 | 8a7572e ③ | C23 铜牌外圈画框边去掉（改用内缩 6% 的无框资产 `C5/c23_bronze_nb_cut.png`） | **未覆盖**：main C23 仍用 `C5/c23_bronze`（`sec_c_pre2_chorus2.py:1584`），资产 `c23_bronze_nb_cut.png` 不在 main。main USER_NOTES_r5 没有这条记录（用户这条意见只进了 branch）。注意：内缩 6% 只裁掉最外一圈，牌面倒角边框仍在；渲帧里铜牌（现为空白+圆规/曲尺刻纹）边框明显，背景墙上还有一个大画框形浮雕，用户说的「画框」指哪个需确认 | `units/sec_c_pre2_chorus2.py:1564–1592`；帧 `out/round6/audit_qp/main_143.3.png`；branch 资产 `origin/feat/quality-pass:assets/gen/C5/c23_bronze_nb_cut.png` | **需移植**（小改：取资产 + C23 一行换名，带存在性兜底），交 **C 组**做（C23 同时是 C 组 #42 未完项，避免两人改同一镜）；移植前顺带确认「画框」指牌边还是墙上大框 |
| 9 | 0d1a213（26s / 81s） | 26s V09 天平主角改纸剪质感（look='paper'）；81s S042 删「天」字改刀落卡点猩红之月 | **已覆盖**：26s = main #6 `paper_bowl`（2bd5713，`units/a_r5.py:11`），REVIEW_A_r6 #6=**8.5**；81s = main #26（0d6ee5f/f81005e → r6 6072751），S042 猩红之月 #C8102E，REVIEW_F_r6 / r6b #26=**8** | `units/a_r5.py:11`；`units/chorus1.py:998–1015`；`crew/round6/REVIEW_A_r6.md:57`；`crew/round6/REVIEW_F_r6b.md:21` | 已覆盖，不移植 |
| 10 | a7e1e46 | 黑白红风格预览（后处理试色 v1–v4，色相法金/暖→灰白、保饱和红；代价：暗朱印会掉红，需按镜头白名单保红） | **未覆盖**：纯试验，只有 4 张预览图（`out/monored/preview*.jpg`），无代码；main 没有任何黑白红调色的记录或用户意见 | `git show a7e1e46 --stat`；main 全仓 grep「黑白红/monored」无结果 | **需用户拍板**：是否要走黑白红整片调色。没有用户要求就不移植；若要看，可把 `origin/feat/quality-pass:out/monored/preview3.jpg` 发给用户 |

## 汇总

- 已覆盖（7）：#1 母版/luma、#2 #23 跳斩、#3 #27 剑光、#4 lyric3 叠字、#5 绿幕精灵、#6 字幕去底色、#9 26s/81s。
- 需移植（1）：#8 C23 铜牌去框（交 C 组，顺带问清「画框」指哪个）。
- 需用户拍板（2）：#7 22s「寒光」巨字（与 #55 冲突）、#10 黑白红整片调色。
- 被后续意见/做法推翻、禁止照搬（2，已计入「已覆盖」）：#4 整段关 lyric3（会删掉 #55 保留的横排句）、#5 整张换精灵（会换脸）。
- 范围外提示：branch 另有 54 个提交，含 main 没有的 `units/grade_unify.py`（统一 grade/胶片 look）、`units/lyric_uni.py`、`units/props_dev.py`（道具化 14 处）、转场去重（闪 67→43）、A 段 +3 刀（205 镜）、工具 `render_film.sh / film_audit.py / ab_video.py / devsync.py / shot_sheets.py / watch_channel.py / gen_assets.py`。字幕/道具化已被 main 的 subtitle.py + #53/#55 口径取代；**grade 统一与转场去重是否要在 main 上做，没人核过**，需总导演决定是否另派审计。

## 验证帧（main 1a7298b，`tools/rf_sb.sh`；按任务只提交本文件，帧图留在沙箱 `out/round6/audit_qp/` 未入库，可随时重渲）
- `out/round6/audit_qp/main_70.3.png`：1:10 S035，墙面阴刻「那就劈开它」+ 底部单份字幕，无叠字。
- `out/round6/audit_qp/main_21.9.png`：0:22 V06，「寒光」巨字仍在（人物右侧，被斩开）。
- `out/round6/audit_qp/main_143.3.png`：2:23 C23，三块铜牌带边框（牌面空白+圆规/曲尺刻纹）。
