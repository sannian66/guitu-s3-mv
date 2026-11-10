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

---

# 第二节 · 其余 54 个提交审计（audit-qp2，第六轮 15:2x 派）

> 范围：`git log main..origin/feat/quality-pass` 第 1–54、57 号提交（11-09 18:08 → 23:55；第一节已审 55/56/58–64）。
> 方法：只读代码 + 静态工具。对照 main HEAD（本节开写时 01fc865 之后）、`crew/round5/USER_NOTES_r5.md`（#1–#55）、`HANDOFF_r5.md`、`STATUS_r6.md`。
> 未渲任何帧。唯一跑过的分析：把分支的 `tools/edit_audit.py`（只 import 各段 SHOTS/CUTS，不渲染）指向 main 代码的镜像，
> 产出 `out/round6/audit_qp2/edit_audit_main.md`（main 现状 206 镜逐镜转场/闪/硬切表，入库作证据）。
> 关键背景：分支的「第 1 批 51 条」（`crew/round4/user_notes_r1.md`）与 main 的 `USER_NOTES_r5.md` #1–#51 **是同一份用户意见**（逐条时间点一致），
> 两边各做了一遍；main 之后又有独立评审打分和 #52–#55 新口径，所以分支里「按 51 条改画面」的提交原则上**全部以 main 为准**。

## 2.0 已完成：工具移植（ac5d8a3）

| 文件 | 分支原样的问题（在 main 上跑不起来） | 移植后改成 | 验证 |
|---|---|---|---|
| `tools/render_film.sh` | 依赖 Mac venv `out/full_sprite/.../venv/bin/python`、`tools/devsnap.py` 快照、`out/devsnap/prun.py`（分支渲染器，**绕过 main 的 `subtitle.py` 底部字幕**，且要 `lyric_uni` / `GRADE_UNIFY`，main 都没有）、W=7（8 核） | 直接调 main 的 `python3 render_sprite_full.py seg F0 F1 part.mp4`（= sections 路由 + 副歌一 + subtitle + GCUT），每块外包 `tools/cpu_slot.sh`；块帧数校验后改名（断点续渲）；全齐后 concat + 混 `audio/谁定正邪.mp3`（aac 320k，`-shortest`）+ ffprobe/全量解码校验写 `RESULT.txt`。参数：`OUT`(默认 out/film_r6) `W`(2) `FINE`(240) `F0/F1`；子命令 `--help/--dry-run/--status/--finalize/--resume` | `bash -n` 通过；`--help`、`--dry-run`（31 块）、`FINE=120 F0=7000 --dry-run`（2 块）、`--status`、`--finalize`（缺块时正确拒绝）。**未跑任何渲染**，拼接/混音段未端到端实测 |
| `tools/film_audit.py` | 镜头表要 `/tmp/all_shots.json`（分支 `shot_sheets.py` 产物，依赖 prun）；默认输出路径/字体相对路径 | `--shots` 可省：从 main 的 `sec_*.py`/`chorus1.py` SHOTS（E 段用 IDS/BOUNDS）现取并按 `sections.py` 帧区间裁剪（**204 镜**，import 约 1s 不渲染）；新增 `--dump-shots`；字体走仓库绝对路径；默认输出 `out/round6/film_audit` | `--help`；`--dump-shots` 出 204 镜、相邻无断档（B1 末镜 P15 止于 59.30s，59.30–59.47 由 `sec_b_pre1.frame` 转交副歌一，属正常）；用 ffmpeg 合成的 3 秒测试片 + 3 镜表跑通全流程（report.md + 2 张联系表） |

注意（给阶段 5 全片渲染）：
- 分块边界 `render_sprite_full.seg` 会 `random.seed(F0)`；STATUS_r6 记的「229.0 署名动画未设种子」修好之前，块边界附近可能有跳变。
- film_audit 每镜只抽 55% 一帧，**查不出转场里的撕裂**。main 现有 10 处故障/撕裂族入转场（A V03 17.90s shatter、B1 P09 52.73s glitch_cut、B1 P15 58.23s shatter、B2 V12 99.43s / V19 108.30s shatter、B2 V20 109.50s split_slide、C C26 145.67s shatter、C C32 151.63s split_slide、C C37 156.20s bolt_split、D S23_Eye 184.67s shatter），
  分支实测过同族转场会出「整幅撕裂 3–5 帧、像文件坏了」（C30 4471–4475、P07 1513–1515，见分支 592604c / `crew/round4/edit_plan.md` §0.0-9），成片后建议在这 10 个切点各抽 9 帧条复核。

## 2.1 统一调色 / 胶片 look（`units/grade_unify.py`；3b3b0b6、bab7d0f、f993d68、3979841）

- **分支做了什么**：一个 407 行纯后处理模块，`GRADE_UNIFY=1` 才生效（默认恒等）。在各段 `finish()` 之后、`to8()` 之前接一行 `GU.apply(fr, t, 段键)`：
  先按各段 finish 参数等量扣掉作者的颗粒/辉光/暗角/黑位，再按全片唯一一套目标重做（颗粒 0.040、暗角 0.42 β0.6、辉光带 0.25–0.35、黑位 0.010、中性 R−B −0.030、暗红纯度 0.86），切点 ±2s 局部匹配；
  第 9 阶段加「胶片 look」：S 曲线 0.30、clarity 0.08、halation 0.05、边缘色散 0.5px。分支报告（`origin/feat/quality-pass:out/grade_unify_report.md`）：段间离散度 颗粒 ±27%→±7%、暗角差 0.19→0.099、黑位 3×→0.0012；渲染 +0.19 s/帧。
- **main 是否已有等效**：**没有**。main 全仓没有 grade 统一层；main 的 `GRADE_UNIFY` 只出现在 `COMPARE_BRIEF.md` 的参考表里。
- **能不能直接搬**：技术上可以——六处收尾调用的参数与分叉点**完全一致**（A `vig=0.45`、B `0.42`、副歌一 `0.42`、C `0.40/bloom 0.42`、D `d_finish(0.45-0.3pm, pm)`、E `grain 0.035/vig 0.38/bloom 0.25`；`*_kit.py` 自分叉后零改动），模块里的 SEC 指纹表仍然有效。
  但接线要动 6 个组文件（A/B kit/chorus1/C/D/E 各一行），或改共享文件 `render_sprite_full.py` 集中接（需把 uint8 再转 float，且拿不到 D 段 `paper_mode` 提示）。
- **是否被用户意见推翻**：没有被推翻，也**没有用户要求**。动机「每段风格不太一样」出自分支 lead 的转述，main 的 USER_NOTES 里没有这条；用户从没看过开/关对比。
- **风险**：它改的是**全片每一帧**的材质与反差（S 曲线、高光外溢、色散），第六轮各组评审打的 8 分全是在「无 grade 层」画面上打的；开了之后 #26 猩红月 #C8102E 的饱和、#50 逆光剪影、D 段宣纸留白这些已过线条目都可能漂。
- **结论**：值得做，但**不在返工期间做**。建议总导演在阶段 4（全部过线）之后、阶段 5 之前，以默认关闭的开关移植（模块 + 集中接线），出 6–8 张同帧开/关对比给用户一句话拍板。→ **需用户拍板**（见文末）；移植执行建议给**总导演/渲染**（共享层），不派给任何组。

## 2.2 转场去重（闪 67→43；3b3b0b6、592604c、46a74ce，规范见分支 `crew/round4/edit_plan.md` §0.0）

- **分支做了什么**：只改各段 `CUTS` 表的 (name, pre, post, kw)：P0 把硬切自带的提亮闪/闪红换成别的招（A 4、B1 3、C 4、E 7 处），P1 给 match_cut 补 pre 0→0.08、缩过长的 post（A 3、B2 2、C 2、D 6、E 5），二期又改 3 处、E 段 6 处 hard/impact→新招 `impact_nf`（3 帧 8→4→1px 顿挫、不闪）。合计闪 67→43、同招连用组 29→15。
- **main 现状（静态表 `out/round6/audit_qp2/edit_audit_main.md`）**：分支动过的 **50 个 CUTS 键在 main 上全部还是分叉时原值**（唯一例外 V13：main 改成 r6 #7「殺/放一镜到底不切」）。main 静态计数约 **74 处闪**（A 11 / B1 6 / 副歌一 10 / B2 2 / C 13 / D 7 / E 25），比分叉时还多几处（D/E 第六轮按评审加了几处，如 D `S28_Spin` 2 帧闪硬切、E `E25` 冲击切）。`impact_nf` 在 main 不存在。
- **与第五/六轮用户意见、评审的冲突（逐处）**：
  | 分支改动 | 落点 | 与 main 的关系 |
  |---|---|---|
  | A V06 hard→ink_bleed | 0:21.17，#3 挥刀镜的入点 | A 组 r6 刚重做 #3 五姿态挥刀；墨洇会盖住起刀，**冲突**，A 组自判 |
  | A V14 hard→a_zoom2、V16/V17/V18 改长度/改招 | 0:32–0:40，#8/#10 正在 A3 返工 | 等 A3 交付后再议 |
  | A V08 paper_tear→zoom_through | 0:23，#4 | **已覆盖**：main 用 `R5.ON['zoom']` 覆盖成 a_zoom2（#4） |
  | B2 V06/V09、C C02/C07 补 pre；D S02/S06/S11/S13/S17/S26 改 pre/post | 1:33、1:36、1:58、2:04、2:42–3:07 | 落在**用户点名喜欢的三段**（1:30–1:40、1:58–2:04、2:41–2:57，`COMPARE_BRIEF.md` §2）和 #44「做得好全保留」段内 → **不动** |
  | C C17/C22/C30/C36 去闪 | 2:15（#39 水中血）、2:20（#40 正邪）、2:29（#42）、2:35 | C 组 #41/#42 未完，且 C30 的分支替代招曾出 5 帧撕裂、换了两次；**不移植**，C 组如要去闪自行在过线后做 |
  | E E02–E13、E14T/E18/E24/E30/E35 去闪/改 impact_nf | 3:14–3:57 | E 段 r6 已把 E34 拆成 4 镜按鼓点切（`e_r9.py` E_R5_BEAT/R6C），#51 已过线；#46 的「天理昭彰 3:18 / 鬼屠 3:26」是砸字重音，去闪会削弱用户要的卡点 → **被 #51 方向推翻**，不移植 |
  | B1 P07/P11/P13 去闪 | 0:50–0:56（#15/#17/#18 镜） | B 组 8 条待评审，不在返工期插手；可作为过线后的可选项 |
- **结论**：**不整体移植**。分支的 CUTS 改动基于分叉时的画面，main 上这些镜头大多被第五/六轮重做过，逐条套用会碰到正在评审的条目。
  可取的是**规范与工具**：①「单 15 镜窗口内闪 ≤4、全片闪占比 ≤35%」这条规矩；② `tools/edit_audit.py`（只读、约 4 秒、能复现上表）；③ 故障族转场必须 9 帧条验收（见 2.0）。
  → 建议总导演决定是否在阶段 4 之后开一个「剪辑节奏」小轮次；**是否全片降闪需用户拍板**（main 目前约 74 处，E 段 25 处最密）。

## 2.3 A 段加 3 刀（bab7d0f、5323c7d：202→205 镜，A 段均值 1.52→1.376s）

- **分支做了什么**：把 V01（16.10s）、V13（31.67s）、V16（37.17s）各拆成前后两半，后半是子类、`u()` 沿用原区间（镜内动画相位不断），镜内推镜接原终点同向续推；新刀用 `impact_nf`（无闪顿挫）。依据是「正文镜长 0.9–1.4s」的规范和「用户喜欢的段平均镜长 1.0s」。
- **main 现状**：没有。main A 段 29 镜、均值 1.52s（静态表同上，规范下界缺 3 刀，与分支当时的诊断一致）。
- **冲突**：
  - **V13 切点 31.67s 直接撞 main r6 #7**：用户要「殺/放同位置、构图一致、文字做转变动画」，main 第三棒做成「殺/放一镜到底不切」（`sec_a_intro_verse1.py` V13 `'cont'`）；在 31.67 加刀会把这段一镜到底切断 → **被 #7 推翻，禁止移植**。
  - **V16（0:36–0:38 玉玺 #10）**：A3 正在重做玉玺，刀落点要等新画面定了才知道是否合适。
  - **V01（0:15–0:17，#2 走出城门之后）**：理论上可加，但 A 组 r6 的 #2/#3 都刚过线或在复核。
- **结论**：不移植。若用户想要 A 段更快的节奏，应由 **A 组**在 #7–#12 过线后，按 main 当前画面重新选刀点（参考分支的做法：落重拍、离字头 ≥0.10s、后半继承相位）。是否要提速 A 段 → 并入「剪辑节奏」用户问题。

## 2.4 精灵渲染提速（`units/sprite.py` R1/R2；431012f、bab7d0f、70fa740）

- **分支做了什么**：`SpriteLayer.draw` 改「包围盒 ROI 合成 + 精灵空间缓存 + 线性基底缓存」，同一 PNG 的预处理进程内共享；C18（39 个甲士精灵）单帧 **100s→5–6s**，对拍 max diff 1/255（float32 舍入级）；`SPRITE_FAST=0` 回旧实现；`SPRITE_WORK_W` 环境变量可降精灵工作分辨率（`a_kit.py` 同步读它）。
- **main 现状**：`units/sprite.py` **自分叉以来一行没改**（还是 R0 全画布实现），而 main 之后又加了大量精灵（GCUT 178 张、各组 R5/R6 生图）。阶段 5 在 2 核沙箱上全片渲染，C 段 C18 一类镜头会把一个槽钉死。
- **兼容性（静态核过）**：分支版公有接口与 main 一致（`SpriteLayer(path, work_w)`、`.fit/.draw`、`.A/.F/.wind_w/.ring/.h/.w/.bbox/.top/.gx/.gy`）；`c_kit.spr()` 的翻转写法（setattr 翻转拷贝）分支注释里专门照顾过。
  main 各组有几处**直接改精灵数组**：`b_kit.py:79-80,118`、`chorus1_sprites.py:501-502`、`d_kit.py:258`、`sec_a_intro_verse1.py:285,2604`、`sec_b_pre1.py:543` —— 都是**重新赋值**（不是原地写），分支缓存按 `id(self.F)` 取键，理论上会正确失效；但分支在进程内**共享同一 PNG 的 A/F 数组**，一旦哪处改成原地写（`sp.A[...] = …`）就会串到同图的其它实例。目前 main 没有这种写法（`c_kit.py:281` 的原地写是文字层 `L.A/L.C`，不是精灵）。
  `_support()` 里 `self._supp_for is not id(self.A)` 用 `is not` 比整数，永远为真 → 每次重算支撑框（只是少省一点时间，不影响画面）。
- **结论**：**值得移植，优先级高（直接决定阶段 5 能不能在合理时间内渲完）**。`sprite.py` 是共享文件，交**总导演/渲染**做：`git checkout origin/feat/quality-pass -- units/sprite.py`（可连带 `a_kit.py` 的 `SPRITE_WORK_W` 两行），
  然后用 `SPRITE_FAST=0` vs `1` 对拍 4 帧（建议 C18 附近 136.6s、副歌一 S045 83.0s、B1 0:51 唇色镜 50.9s、E34 235.0s），max diff ≤2/255 才合入；时机：各组返工期间不换（避免评审前后底层变化），阶段 4 收尾时做。

## 2.5 统一字幕层 / 歌词道具化 / 骨架 rig —— 已被 main 取代，不移植

| 方向 | 分支提交 | main 的对应 | 结论 |
|---|---|---|---|
| 统一字幕层 `units/lyric_uni.py`（右竖排 → 22:38 改底部横排，含横带 scrim；去重检测 dupcheck、guard 56/56） | 3979841、6024e46、dcb98d4、e30ca35、b77eb8e、5baacbe、aa28a31、7ae42b0、5583752（+ `d_kit/e_kit/e_r5/sec_b_*` 里的 `LYRIC_UNI` 守卫） | `units/subtitle.py`（#52 底部居中，无底色，在下黑边内）+ #53 `R5_NOVLYR` 关竖排 + #55 保留横排/刻印字 | **已覆盖**。分支修过的「B2 V13『可曾有机会』双字幕」（6024e46）main 已按 #53 用 `NOVLYR` 关掉（`sec_b_verse2.py:1515`）。不移植 |
| 歌词道具化 `units/props_dev.py`（刻/烧/印/擦/穿线，最终 14 处；字幕对应字留空 hidden_slots） | 3b3b0b6、bab7d0f、c25d861、020a27f、f993d68、48e3e7b、972c963、58016a2、90a1eb2、581f8ce | main 无。它会在画面里**新增 14 处歌词关键字**并要求字幕「挖字留空」——与用户 #52（字幕完整放下方）、#53（画内歌词字去掉）、「用户没提到的文字先不动」三条口径都相反；用户还当场否决过「整句道具化」（020a27f 记录） | **被第五/六轮意见推翻**，不移植 |
| 骨架/姿势 rig `units/rig_sprite.py`（蒙皮→收窄成姿势键帧播放器） | 7099add、f993d68、9dea0f9、aa28a31 | 用户原话「太抽象了」否决蒙皮（COMPARE_BRIEF §2）；main F 组 #23/#27 用多姿势生图 + 切点换图，评审已 7–8 | 不移植 |

## 2.6 分支按「51 条」改的各段画面（与 main #1–#51 同一批意见）

| 分支提交 | 内容 | main 对应条目现状 | 结论 |
|---|---|---|---|
| 5baacbe / 5d870f1 / 2acf7f8（A） | #1 删署名、#2 走出门、#4 zoom、#5 伪字诏书、#6 剪纸、#7 殺/放 `a_char_morph`、#9 刀尖+「我的主张」改 `etched_lyric`、#10 玉玺绿幕单体、#12「锋芒」重做（`serif_black` 470px） | main A：#1/2/4/5/6/8/10/11/12 评审过线（REVIEW_A_r6），#3/#7/#9 在 A3 返工 | 已覆盖。#7 分支做法（V12→V13 字形转场）与 main「一镜到底」不同、以 main 为准。**可选参考**：A3 做 #9 时可看分支 `etched_lyric` 暗石参数（5d870f1） |
| c2e88e6（B1） | #15 唇红改精灵像素级局部去色（记录「`red_keep` 参数无效已实测」）、#16 P09 焦距 1800→1300、#17 删「谁的」、#19 删「刀还滚烫」 | main B：#16/#17/#19 过线；#15 B 组 r6 已提交待评审 | 已覆盖。**可选参考**：若 #15 评审仍不过，分支「red_keep 无效、必须在精灵像素层去红」的结论值得 B 组看一眼 |
| 2acf7f8（B2） | #30 删「嚣张」柄在、#31 断句、#32 V13 头顶去字、#33 黑白常驻镜像 | main B #31 过线，#30/#32/#33 待评审（#32 105.9 断碑硬边未找到） | 已覆盖，不移植 |
| b77eb8e（C） | C 段十条（#34–#43） | main #41 已用同样的根因修法（人钉在底板坐标 `py=0.845`，`sec_c_pre2_chorus2.py` C22）；#43 分支「判保留」**被用户后令「判字不留了」推翻**；#42 分支把 C25 石「劈」、C28「亮」换成劈缝/光缝，并自己标注「亮」卡在 2:28 边界待用户确认 | 已覆盖 / 被推翻。C 组做 #42 时注意同一个边界问题（2:27.74 的「亮」去不去）——第一节已提过的铜牌去框也归 C 组 |
| dbe9949、581f8ce（D/E） | #46 画内字按保留清单、对错改代码画 ✓✗；#45/#47/#48 裁切方案 | main D #46 过线、#45 重新生图中；E #47/#48 过线 | 已覆盖，不移植 |
| f6ac277（E） | #49 金光用精灵 alpha 挖孔、#50 剪影外圈压暗+头部 rim、#51 尾段 16 颗重音推近+抖 | main E 走得更远：#49/#51 评审过线（a200f95），#50 第四棒做「日面+大气透视山脊+扬尘」 | 已覆盖。**可选参考**：#50 若再不过，分支「人物外圈压一圈暗做分离 + 头部 30% rim 加强」（`sec_e_final_outro` f6ac277 diff）可试 |
| 592604c（B1/C） | C30、B1 P07 换掉自己引入的 freeze_glitch（5 帧撕裂） | main 这两处从未换成 freeze_glitch | 不涉及 main；教训并入 2.0 的 9 帧条建议 |

## 2.7 生图素材（929bc63、6e71002、b036c2d、9f52d59、c809b82、9ccd794、8125b1e、3ae79d0、2dc4ec8、c25d861、7099add、6b719db）

- 分支入库的 `assets/gen/char/`（60）、`r1/`（25）、`wt/`（12）、`rig/`（14）、`green/`（40）、`props/`（4）**在 main 一张都没有**，main 代码也不引用。
- 这些是分支针对同一批意见出的图：主角多角度/表情/姿势、太上皇 2 张、`r1/` 整帧替换（V14 角色、V16 玉玺、V20 姿态、V21 笔手、P12 裁刀、S031 太上皇、S046 刀遮脸、C09 牌匾、C22 双人、D17 主角、E22 天平、E218 崩图）及其绿幕单体版。分支自评：第 1 批 6 张构图漂移、37s 玉玺与 2m20 双人重出后仍漂移；部分是「拿成片帧当参考」画的，字被烙进像素（才有 `tools/clean_gen_text.py`）。
- main 从第五轮起要求人物**按定妆照**（`assets/characters/png/男主_鬼屠.png`）出图并防换脸（ffc2b74），分支这批图不是按这个口径出的。
- **结论**：不移植。仅当某组卡在同一镜（B #13 0:44 手与笔、A #10 玉玺、F #21 太上皇）时，可从分支取一张当**生图参考**（`git show origin/feat/quality-pass:assets/gen/r1/g_v21_hand_cut.png > …`），不要直接上片。

## 2.8 流程/工具/文档类

| 提交 | 内容 | 结论 |
|---|---|---|
| bafb35b、cbe3ffb | 推送规则改成「永不推 main，只推工作分支走 PR」，post-commit 只推当前分支 | **被推翻**：第五/六轮用户明确要求每次提交都推 main（HANDOFF_r5 §1、CHARTER_r6）。不移植 |
| 3b3b0b6 / 020a27f（CLAUDE.md） | 「自主决策、不要问用户拍板」硬规则；「字幕为主 + 道具只抬关键词」 | 前者与第六轮「拿不准的一律先留、列出来问用户」相反，不移植；后者的用户原意（否决整句道具化）已体现在 #53 |
| 1fdef70、5d870f1 | `devsnap.py --ref`、`devsync.py`（Mac 本机镜像源码改 ROOT） | 沙箱 ROOT 本来就是 `/workspace/work/mv`，不需要。不移植 |
| 6715315、4183dde、45bf790、2dc4ec8 | `gen_assets.py`（RH_image2 渠道）、`gen_openai.py`、`WENTOKEN_KEY` 环境变量、`watch_channel.py` 渠道守护 | `gen_openai.py` main 已有且**与分支逐字相同**（已覆盖）；其余是旧渠道/Mac 用，不移植 |
| 431012f | `tools/cutout_green.py` | main 已有且**与分支逐字相同**（已覆盖） |
| 6b719db、ebe2852 | `ab_video.py` 分屏对比片、`shot_sheets.py` 逐镜联系表 | 都依赖分支的 devsnap/prun 快照；main 有 `render_sprite_full.py contact` 与各组 `*_contact.py`。不移植（ab_video 的思路可在评审需要动态对比时再写一个 main 版） |
| 3b3b0b6（`tools/edit_audit.py`） | 只读的转场/镜长审计 | **可选移植**（工具类、无副作用）：本次已证明它在 main 代码镜像上能跑（需把仓库根的 `proc.py/fx.py/scenes.py/analysis.npz` 一起镜像、`crew/` 用软链）。若总导演开「剪辑节奏」轮次再移植 |
| 7f796ca | revert 用户偏好三段分析 | `git cherry` 显示已在 main（等效补丁） |
| 367384f、313d80f、70fa740（文档） | HANDOFF/时间轴更新到 205 镜 | 描述的是分支状态，不移植 |
| 70fa740（代码） | `SPRITE_WORK_W` 环境变量 | 随 2.4 一起移植 |
