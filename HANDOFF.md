# 《谁定正邪》MV 交接计划书

《鬼屠 · 第二季》主题曲《谁定正邪》的歌词 MV。场景/字幕/特效由代码生成；人物自 2026-11-09 05:25 起用生图 + 抠图精灵（见第 0 节）。

## 0. 硬性规则（用户定的）
- **2026-11-09 05:25 用户确认：人物（含手、刀等人物道具特写）使用 RH_image2 生图 + tools/cutout.py 抠图做精灵图层合成；场景/字幕/卡点/运镜/粒子仍纯代码；远景小剪影可继续用代码 rig。**（S043 试点获认可，见第 15、16 节。）
- ~~2026-11-09 04:02 用户决定：回到纯代码；参考图只做测量/描轮廓参考，画面无 AI 像素~~ —— **已被 05:25 的规则取代**。Seedance 重绘方案否决（仍有效）。
- 场景纯代码：山、雾、月、军阵、天平、墙、粒子、印章、刀光全部由 numpy/OpenCV 算出来。`_ai_unused/` 里是早期的 AI 生图，**禁止使用**（仓库里没有提交）。
- 视觉语言：2.39 宽银幕黑边，只用黑、白、灰、血红、金色；书法字（马善政体）；红色「鬼屠」印章；刀光贴着鼓点。
- 画幅：16:9，1920×1080，30fps。竖屏版还没做，用户也还没要。

## 1. 片头信息（必须出现）
| 职务 | 名字 |
|---|---|
| 出品人 | 西几王传媒 |
| 编剧 / 导演 | 苏打 |
| 美术设计 | Cait |
| AI画师 | 沉溺、雪晴、索恩 |
| 后期总监 | 沉溺 |
| 音乐 | 西几王 |
| 主标题 | 鬼屠 · 第二季 |
| 副标题 | 主题曲《谁定正邪》 |

时间都落在小节重拍上（约 129 BPM，一小节约 1.86 秒）：
- 0.30s 墨从黑场晕开，露出夜色山水和血月
- （2026-11-09 05:52 用户改）0.45 出品人 + 0.60 后期总监（上下两块）→ 2.21 编剧/导演 → 4.06 美术设计 + 4.21 音乐（上下两块）→ 5.97 AI画师；所有署名都在片名之前
- 7.85 **片名重击**：刀光横扫，「谁定正邪」墨字炸出，闪白、震屏、飞火；8.31 印章落下；8.35 出「鬼屠 · 第二季」和「主题曲」
- 片名区只留：主标题「鬼屠 · 第二季」（书法 210px，两段+朱红间隔点）+ 副标题「主题曲《谁定正邪》」+ 鬼屠印；片尾同此层级，署名 6 行
- 11.52 片名扫光，13.35 片名开始消散，15.21 前奏结束，15.94 第一句歌词进

## 2. 文件
| 文件 | 内容 |
|---|---|
| `scenes.py` | **全片**：所有场景类、歌词时间轴（从 align.json 逐字展开）、歌词版式（bottom/ink/big）、时间线 `TIMELINE`、转场（墨晕 wipe、闪白、鼓点推镜）。入口 `frame_at(t, dt, cache)` |
| `render_full.py` | 按帧区间渲染无声视频：`python3 render_full.py F0 F1 out.mp4`（30fps，帧号=秒×30） |
| `run_chunks.sh` | 两路并行渲染多个区间到 `chunks/`，已完成的跳过（可断点续跑） |
| `preview.py` | 抽帧预览：`python3 preview.py out.jpg 15.5 60 120 …` 生成联系表 |
| `render.py` | 片头 `Intro`、山水 `ShanShui`（含 dawn 黎明参数）、`InkWipe`；也可单独 `python3 render.py T0 T1 out.mp4` 渲染片段带音频 |
| `fx.py` | 合成工具：调色、镜头、颗粒、暗角、黑边、辉光、色差、飞火 `Embers`、雨 `Rain`、刀光 `slash`、书法字 `text_layer`（逐字墨显，带字形缓存）、`comp_text`、印章 `seal`、`under_grad` |
| `proc.py` | 程序化生成器：`fbm2/fbm1` 噪声、山水 `mountain_layer`、`mist`、`army` 军阵剪影、`hero` 刀客背影、`balance` 天平、`dao` 刀、`bricks` 城墙、`ink_bleed` 墨渗 |
| `sf_proc.py` | 生成五张方向关键帧（输出到 `sfp/`）：片名、军阵、天平、副歌劈墙、烫刀 |
| `lyrics.json` | 56 句歌词，带段落标记 |
| `align.json` | 逐字时间轴（demucs 分人声 + stable-ts small 强制对齐）。`align.log` 是逐句起止时间的可读版 |
| `analysis.npz` | librosa 音频分析：`t`、`rms`、`low`（150Hz 以下能量，鼓点）、`onset`、`beats` |
| `sep.py` / `align.py` | 重跑人声分离和对齐用 |
| `requirements.txt` | 依赖 |
| `fonts/` | 马善政、志莽行、刘建毛草、思源宋体（均为 OFL 开源字体） |
| `previews/` | 关键帧和 10 秒试做 |

**音频没有进仓库**（仓库是公开的）。把歌曲放到仓库根目录，命名 `song.mp3` 即可渲染。

## 3. 歌曲结构（来自 align.json）
| 段落 | 时间 |
|---|---|
| 前奏 + 片头字幕 | 0 – 15.9 |
| 主歌一 | 15.94 – 43.5 |
| Pre-Chorus | 44.0 – 58.3 |
| 副歌一 | 59.5 – 86.2 |
| 主歌二 | 89.4 – 116.9 |
| Pre-Chorus 二 | 117.9 – 131.7 |
| 副歌·高潮 | 134.5 – 161.3 |
| Bridge | 162.6 – 192.1 |
| 副歌·终章 | 193.2 – 221.2 |
| 尾奏 | 221.2 – 241.3 |

## 4. 分镜计划（待实现）
| 段落 | 场景（全程序化） | 歌词版式 |
|---|---|---|
| 主歌一 前四句 | 夜雨军阵，刀客背影，五百重甲；「天平」句切纸面天平滴血 | 底部横排，逐字墨显；关键词点红 |
| 主歌一 后四句 | 雨夜，刀光闪切，剪影杀/放 | 同上 |
| Pre-Chorus | 宣纸「生死簿」：竖排大字自右向左写出，血墨晕染；末句接烫刀特写 | 竖排 |
| 副歌一 | 城墙被劈开，金光从裂缝涌出，飞火爆发；每个「血未冷」重拍闪白震屏 | 大字居中，「血」字红 |
| 主歌二 | 皮影/提线：跪地人群剪影，高台权柄；「黑白颠倒」画面反色 | 底部横排 |
| Pre-Chorus 二 | 暗箱交易：烛光剪影；回到烫刀 | 竖排 |
| 副歌·高潮 | 劈墙加强版，镜头更快，色差更重 | 大字 |
| Bridge | 雨中坟野，插刀的刀客；「什么叫…」排比句逐句压上来叠满屏，「天不判我来判」「刀不答我来答」两记重击清屏 | 叠字 / 满屏 |
| 副歌·终章 | 天书诏令被一刀撕开，黎明金光，山水由夜转晓 | 大字 |
| 尾奏 | 晨雾山水，刀客小剪影远去，红日；片尾重复出品信息和印章 | 居中小字 |

## 4b. 已实现的时间线（scenes.TIMELINE）
intro → army(五百重甲,寒光刀光) → pscales0(纸上天平滴血) → duel(雨中拔刀三闪) → throne(金阶殿堂,锋芒竖斩) → scroll0(生死簿竖排) → blade(刀渐烫) → 副歌一[blade 炽热 / dscales 暗金天平 / wall 裂缝 / wall 劈开 / wall 金光刀客 / peak 血月山巅一刀] → stamp(大局/权柄红印砸下) → pscales1 → storm(闪电) → invert(黑白颠倒, 划刀复原) → scroll1 → blade → 副歌二(同副歌一, 强度1.4) → bridge(雨夜排比叠字, 两记重击) → blade → peak(破晓) → edict(诏书撕开) → wall 金光 → peak(天亮,最后一刀) → outro(片名+全部出品信息, 淡出)

## 5. 下一步
1. ~~用户确认方向~~（2026-11-08 23:30 已确认，「继续吧」）
2. ~~场景全部实现~~（scenes.py）
3. 全片渲染：`./run_chunks.sh 0 600 600 1200 …`（每段 600 帧，共 7241 帧），然后
   `printf "file '%s'\n" chunks/c_*.mp4 > list.txt; ffmpeg -f concat -safe 0 -i list.txt -i song.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart 谁定正邪_MV.mp4`
   原计划：全片分段并行渲染（2 核，每段约 30–40 秒片长，两个进程），再用 concat 拼接后整体混音频。按每帧约 0.5 秒估算，全片约 7200 帧，约 1 小时。
4. 交付前用 ffprobe 核对时长（应为 241.3 秒），抽帧检查文字有没有被截断。
5. 交付：H.264 CRF 16 母版，另出一个 CRF 20 的网络版。

## 6. 已知坑
- 沙箱内存约 8GB，Whisper medium 会被 OOM 杀掉，用 small。`~/.cache` 太大时先清。
- 沙箱重启后 pip 包会丢，重新 `pip install --user -r requirements.txt`。
- 马善政体没有「·」，写在书法字里会变成方块，用全角空格代替；思源宋体有。
- `text_layer` 的 `reveal` 列表长度必须等于字符串长度（空格也算）。

## 7. 状态（2026-11-08 23:45）
- 2026-11-09 00:35 全片 241.3s 渲染完成：master（CRF17, 509MB）与网络版 1080p（CRF23, 209MB）已交付用户；视频文件超 GitHub 100MB 限制，未入库。下一步：等用户逐段反馈后改 scenes.py 对应段，只重渲受影响的 chunk（删掉 chunks/c_XXXXX.mp4 再跑 run_chunks.sh）。

### 旧状态（23:30）
- 已完成：纯代码方向关键帧 5 张，歌词逐字对齐，前奏片头（含全部出品信息）实现并试渲染 0–10 秒。
- 等待：用户看 10 秒试做后的反馈。

## 8. v2 剧组管线状态（2026-11-09 01:35 CST，接手后）
- 用户嫌 v1：节奏慢、画面简单、重复多、不精致、分镜无设计感、无转场、歌词排版简单。v2 按剧组分工重做，总纲见 `crew/BRIEF.md`。
- 已交件：导演组 `crew/storyboard.md` + `crew/shots.json`（138 镜）；字幕转场组 `lib/typo.py`（40+ 排版，闪电刻字已改回金白）、`lib/trans.py`（17 种转场/运镜）。
- 进行中：角色组补军阵、纸人/皮影、道具、雨光特效（`lib/`，API 写在 `lib/RIG_API.md`）；副歌一摄制组做 59–89s 样片 `units/chorus1.py` → `out/sample_chorus1.mp4`。
- 前任最新一版 rig.py 未推送已丢失，以仓库版本为准。
- 歌曲与歌词原文已入库：`audio/谁定正邪.mp3`、`audio/谁定正邪.txt`（渲染时复制为根目录 `song.mp3`）。
- 自动同步：`./autosync.sh` 把所有改动（含半成品）提交推送，跳过 >50MB 文件；每 3 分钟跑一次。
- 下一步：用户审副歌一样片 → 点头后各段摄制组并行铺开全片 → 剪辑质检 `crew/qa.md` → 渲染交付。
- 02:02 副歌一样片完成：`out/sample_chorus1.mp4`（31s/22镜，CRF18，66.6MB 未入库）、网络版 `out/sample_chorus1_web.mp4`（CRF24，已入库）。代码 `units/chorus1.py`、`units/c1kit.py`、`units/render_chorus1.py`；角色库冻结在 `units/c1_rig_frozen.py`（`C1_RIG=live` 切回共享库）。frame() 已含调色/黑边，组装时不要再 finish。
- 样片待改：6 镜砖墙同质、手部特写偏平、S043 回头发丝乱、S038 刀上眼睛示意化、S048 雨滴倒影小、85.9–86.5 近全黑、光环字小、整体偏暗；歌词/刀光/裂缝/光束换 Skia。等用户审片意见。

## 9. 副歌一 v2（摄影指导 + 剪辑组，2026-11-09 02:35 CST）
- 用户审 v1：画面 OK，运镜/节奏/卡点不够。v2 只动运镜与剪辑，画面风格不变。
- 卡点：`units/c1_sep.py`（htdemucs 分离 56–92s 鼓/人声/贝斯 → out/c1_*.wav）+ `units/hitmap.py` → `crew/hitmap_c1.json`、`crew/hitmap_c1.png`。139 击打（底鼓 73 / 军鼓 42 / hat 93 / 重音镲 7），字头在人声轨上精修。
- 相机：`units/vcam.py`（弹簧阻尼卡点脉冲、缓动 + 速度坡度、方向连贯甩镜、速度运动模糊、前景视差层）。
- 剪辑：`units/chorus1.py` 末尾 CUT_F / CUTS / MOVES / REMAP / ENERGY / INSERTS / FG / EXPO 表；说明见 `crew/chorus1_v2_edit.md`。22 镜 + 13 处插入闪切，平均镜长 1.41s。
- 角色库已切共享 Skia 版（C1_RIG 默认 live；frozen 可回退）。
- 产出：`out/sample_chorus1_v2.mp4`（CRF18，未入库）、`out/sample_chorus1_v2_web.mp4`（CRF24，入库）、`out/chorus1_v2_cuts.jpg`（34 个切点/插入前后帧）。渲染：`units/c1v2_render.sh`（后台 2 进程，out/c1v2chunks/）。
- 坑：ffmpeg `+faststart` 直接写 /workspace（juicefs）会在写尾时 I/O error、留下坏文件——先写 /tmp 再拷（mux 已改）。v1 母版曾被误覆盖，已用 out/c1chunks/final.txt 重新拼回。
- 待办：S029/S044 手部、S043 发丝仍粗（角色组）；S048 雨滴倒影仍小；墙镜头 S033/S034/S035/S036 仍是同一砖墙材质，可换 props.CharWall；props.Blade / fx2.RainSheet 尚未替换 c1kit 版。
- 02:33 副歌一 v2（运镜/卡点轮）：`out/sample_chorus1_v2.mp4`（66.7MB 未入库）、`out/sample_chorus1_v2_web.mp4`（已入库）。卡点图 `crew/hitmap_c1.json`（139 击打，htdemucs 拆鼓），相机模块 `units/vcam.py`，剪辑说明 `crew/chorus1_v2_edit.md`；22 镜 + 13 处插入闪切，47 切点。已切到共享 Skia 库。ffmpeg 成片先写 /tmp 再拷进 /workspace（JuiceFS 写 trailer 会报错）。
- v2 待改：手部特写、回头发丝、雨滴倒影小、四个砖墙镜头仍同材质（可换 props.CharWall）、c1kit 旧刀/雨可换 props/fx2。等用户审片。

## 10. 副歌一 v3（摄影指导 + 剪辑组，2026-11-09 03:00 CST）
- 用户审 v2：鼓点震动太多 → 克制；运镜加量；歌词排版乱 → 统一（最终：全部思源宋多字重，不用书法字）。切点/转场/闪切/定格慢放/字落点不变。
- 新文件：`units/vcam3.py`（克制版脉冲 + 2.5D 相机：环绕 yaw / 仰俯 pitch / 变焦推拉 vtg / 焦点转移 focus / beat 速度坡度 / 前景遮挡物 FGOcc）、`units/lyric3.py`（统一字幕层）、`units/shake_stats.py`（v2/v3 震动量化 → crew/shake_v2_v3.json）、`units/c1v3_render.sh`、`units/c1v3_contact.py`。
- 字体：`fonts/NotoSerifSC-{Regular,Medium,SemiBold,Bold,Black}.otf`（noto-cjk 官方 SubsetOTF/SC，OFL，`fonts/NotoSerifSC-OFL.txt`），typo 里注册为 serif_r/serif_m/serif_sb/serif_b/serif_black（chorus1.py 注册；宋体字形不加墨迹纹理）。
- **全片字幕规范**写在 `crew/chorus1_v2_edit.md` 第 4 节，其他段落照此执行（lyric3.LyricLayer + Sentence 表即可复用）。
- 产出：`out/sample_chorus1_v3.mp4`（CRF18，未入库）、`out/sample_chorus1_v3_web.mp4`（CRF24）、`out/chorus1_v3_contact.jpg`、`out/chorus1_v3_mainchar_compare.jpg`。
- 回退：`C1_CAM=2` v2 相机，`C1_LYR=2` 关统一字幕层（但镜头内散字已删，需 git 取回 v2 的 chorus1.py）。

## 11. 人物模型 v2 接手核验（2026-11-09 03:40 CST）
- `_composite` 两处定义不是冲突：第二处是 v2 包装层（`_composite_v1 = _composite` 后重定义，v1/无 skia 时回落），保留。
- 亲眼核验 `v2_cmp.py sw cu`：全身 v2 明显好于 v1（体积明暗、腰封/长靴/护腕、飘带有厚度）；CU 偏暗、正面回头脸被刘海压成黑块、眼神光穿透头发 → 待修。
- v2.1 改动：`rig.FILL`（天光 0.50→0.62、肤色补光 0.42，可 `rig.set_fill()` 调）；正面刘海发束 2.1→1.35×hw。侧脸已能读出鼻/唇/眼。
- 对比图：`lib/rig_test/v2_cmp_sw_cu.jpg`。
- 下一步：S043 回头（眼神光加遮挡判定、刘海分缝露额、头发发束改尖细）→ 握刀手 → 刀上眼睛 → 其余角色。副歌一仍未用 v2 重渲。

## 12. ~~切换到 AI 生图~~（2026-11-09 03:40，已于 04:02 撤销，见第 0 节）
- 用户：代码建模和设想差距大 → 安装 Nano Banana skill，人物用生图。`CLAUDE.md` 写明调用规则；客户端 `tools/nb.py`；生成记录 `crew/genlog.md`。
- 等用户提供角色资产图（放 `assets/characters/`）。

## 13. 人物 v3：鬼屠脸/发型按设定图（2026-11-09 04:05– CST，纯代码）
- 测量：`lib/ref/guitu_hero_ref.py`（设定图 2000x1116 的头身比≈9、五官位置、马尾根高/长、刘海/鬓发/发型轮廓点、取色）。只是数字，渲染不读图。
- rig 改动（`rig.HAIR_V3=True`，置 False 回 v2）：
  - 脸：`HEAD3` 清瘦尖下巴、高颧骨；`_face3` 把五官下移到设定图比例；`_eye_pts3` 细长上挑眼；剑眉粗而上挑；肤色 tone 168→188（苍白）；琥珀瞳走金通道。
  - 发：`Swordsman._hair_v3` 高马尾 16 节（先上扬再垂落，≈50 单位过腰，梢散）；中分刘海 8 缕发帘 + 3 缕过眼；新链 `sidelocks` 鬓发垂到胸前。发盖改为按方位角的窄扇区凸包（`HAIR_CAP3`），弧形中分发际线 —— v2 单凸包横跨两鬓压住整张脸 = 正面黑块的根因。
  - 遮挡：眼神光按金通道判定（头发后画会擦掉瞳孔的金）→ 被发遮住时不再透光。
  - 特写补光：`profile_cu(..., cu_fill=1.0)` 只在本次绘制内抬天光/肤色补光/lift；`cu_fill=None` 等同 v2。
- 接口兼容：Swordsman/profile_cu 签名只加了可选参数；units/scenes 无外部访问头发属性。
- 对比：`lib/rig_test/v3_face_cmp.py` → `lib/rig_test/v3_face_cmp_{front,profile,turn3q,full}.jpg`（v2 | v3 | 设定图裁切）。v2 冻结在 `lib/rig_test/rig_v2_baseline.py`。
- 仍待改：发束仍是少量粗束（设定图是大量细丝）；侧脸鬓发/发帘压脸偏多；颈偏长；副歌一未用 v3 重渲。

## 14. 人物 v4：细发丝 / 马尾下垂 / 体积脸 / 琥珀瞳（2026-11-09 05:xx CST，纯代码）
- 开关：`rig.HAIR_V4=True`（需 `HAIR_V3=True`；置 False 精确回到 v3，Swordsman 在构造时读开关，绘制时读全局）。v3 冻结在 `lib/rig_test/rig_v3_baseline.py`。
- 头发：`_lock4` 每条链 = 窄暗色发团底 + N 根细丝（宽度递减、两级横向抖动、梢部按 u² 分叉散开、长短不齐、少数丝超出束尾）+ 受光侧中段高光丝（tone≤100，冷 sheen）。`_hair4` 统一调度马尾/乱发（隔一取一、无底、细）/刘海（过眼发缕只剩 ≤4 根细丝）/鬓发。`_cap4` 头盖上从发际线梳向发髻的细丝；`_fringe4` 中分向两侧扫开的发帘细丝，打散发盖硬边。飞发 `_fly4`：每 6 取 1、极细、带弧度、两端尖。
- 轮廓光：v4 合成时（`_V4C`）细丝的外轮廓/内轮廓/宽 rim 按粗细衰减 → 不再满屏白线。
- 马尾物理：`rig.PONY4 = dict(wk=0.55 风力系数, turb=0.45 湍流, grav=1.25, drag=2.8, damp=0.93)`；18 束 × 18 节 ≈ 63 单位。静风 2s 后梢 y≈44–54（腰封≈54–62，过腰）；逆风 -200 时向后斜飘（z≈-29）不横飞。`Chains` 新增 `wk/turb` 属性（默认 1，其他链不变）。
- 侧脸：鬓发锚点后移到耳前、宽 0.7–0.8；刘海发帘 ×0.88；头心 Hc 离颈根 10.2→9.4（颈缩短）；`_collar4` 立领 + 暗红内领边盖住颈根；中衣领 v4 改暗红（设定图）。
- 脸：`HEAD4` V 形下颌 + 颊颌外凸弧（去直边）、多边形并集 smooth；肤色 `SKIN4=206`、肤色调 `SKIN4_RGB`（近中性冷白，替代通用冷蓝）；脸上主光过渡柔化（不沿鼻梁硬切）。`_face4`：眼窝/内眼角/颧下凹/颞侧/颧骨亮面/下颌线/下巴颈投影；鼻梁亮线 + 背光侧鼻侧面 + 鼻头高光 + 鼻底影 + 柔和鼻翼；上唇暗/下唇亮 + 高光 + 唇下影 + 人中；剑眉 = 实心底 + 毛流短笔；眼 = 眼白 + 粗上睑线（眼尾上挑）+ 双眼皮 + 下睑。
- 琥珀瞳：虹膜写金通道 213 占位，合成后 `_iris4` 在仍可见处径向着色（`rig.IRIS4`：外圈深棕/琥珀/瞳周暖金/黑瞳/上睑投影）；睑线擦金通道避免误着色。眼神光缩到 0.065·sc，glint>1.2 才加外晕（S043 寒光仍有）。
- 对比：`python lib/rig_test/v4_cmp.py [front|profile|turn3q|calm|wind|c1|all]` → `lib/rig_test/v4_cmp_*.jpg`；速度 `lib/rig_test/v4_speed.json`。`ONLY=v4` 只渲新版到 /tmp 快速迭代。注意 units/typo 硬编码 `/workspace/work/mv`，沙箱需 `ln -s <repo> /workspace/work/mv`。
- 速度（单帧，2 核沙箱，同时有 autosync 干扰）：特写 v3 0.93–1.18s → v4 1.04–1.27s；全身 v3 0.31s → v4 0.31–0.42s。`rig.HAIR_DETAIL`（默认 1.0，可 0.5/0.3）只降细丝数：CU 1.25→1.07s，全身基本不变——瓶颈是 `_comp2` 全画布合成（距离场/模糊），不是发丝。要进一步提速需给 `_comp2` 做降采样明暗，未做。
- 仍待改：脸轮廓仍偏几何（凸包）、肤色整体偏灰；侧脸后脑发盖有硬边暗块；正面马尾/乱发在头两侧仍有大弧；全身尺度马尾丝很细读作一束；特写超 1.0s/帧。

## 15. 人物精灵试点 S043（生图 + 抠图 → 代码管线，2026-11-09 05:15– CST）
- 用户提议：代码人物太丑（见 v4 对比）→ 试「生图 + 抠图」，场景/字幕/卡点/运镜/粒子仍代码。**仅试点，开关控制；默认（SPRITE_MODE=0）全片仍是纯代码人物，第 0 节规则未改，等用户看试点后定。**
- 生图：1 张 RH_image2 4K 16:9（3 积分，task 050acd06…，记录 crew/genlog.md），参考图 = 男主_鬼屠.webp，纯中性灰背景、后方冷月轮廓光。原图 `assets/gen/hero/S043_raw.png`。
- 抠图：`tools/cutout.py`（rembg isnet-general-use 粗蒙版 → 蒙版外拟合二次曲面背景板 → 边缘带内按背景色差做差值抠像 → 前景反混合去灰边 → alpha 收缩 + 0.6px 羽化）→ `assets/gen/hero/S043_cut.png`（2560 宽 RGBA）。绿幕可加 `--green`（色键 + despill）。
- 合成：`units/sprite.py` SpriteLayer（发区/轮廓距离权重的分区网格风吹 remap、呼吸 0.5%、去饱和压暗偏冷 + gamma、屏幕空间主光衰减、按法线·光向的冷色 rim、背景光包裹、甩入方向模糊）。`units/chorus1.py` 新增 `S043Sprite`（`SPRITE_MODE=1` 时替换 S043；背后月光晕 + 远雾远雨（慢推）+ 人物（快推 = 视差）+ 眼中星芒 + 近景火星/雨丝；剪辑/运镜/FG/曝光/字幕表沿用 S043 键）。`SPRITE_EXT=t0,t1` 可把镜头拉长单独试渲。
- 产出：`out/pilot/S043_sprite.mp4`（`units/render_sprite_S043.py video …`，82.06–85.56 共 3.5s 拉长版 + 原曲音频，相机按比例映射 vcam3 的 S043 运动、快门同比缩短）；对比 `lib/rig_test/sprite_vs_v4_S043.jpg`（`lib/rig_test/sprite_vs_v4.py 82.70`，正常剪辑时间线同一帧）。
- 局限：一张静帧做不出真正的转头（现用 0.26s 甩入 + 模糊代替）；头顶马尾被生图裁掉；finish 的去饱和吃掉了暗红内领。

## 16. 副歌一精灵版全段（SPRITE_MODE=1，2026-11-09 05:26– CST）
- 规则：第 0 节 05:25 新规则（人物 = RH_image2 生图 + 抠图精灵；场景/字幕/卡点/运镜/粒子纯代码）。CLAUDE.md 同步改写，04:02 规则标为已取代。
- 方案表：`crew/sprite_plan.md`（镜号｜处理｜姿势数｜提示词要点 + 选图结果）。精灵镜头：S029 S030 S035 S037 S038 S039 S041 S043 S044 S045 S046；保留代码：S028（刃面血滴，无人物）、S031（ELS 一粒黑点）。
- 生图：`tools/gen_c1_sprites.py <镜号/姿势,...|all> <抽次>`（ThreadPoolExecutor 并发，先报价，日志追加 crew/genlog.md，候选落仓库外 `../gen_cands/`）。16 张 = 48 积分，重抽 1 次（S044）。
- 抠图：`tools/pick_cut.py S0xx/pose=<候选>[:flip]` → `assets/gen/<镜号>/<姿势>_raw.png`（2560 宽）+ `_cut.png`；`force_poly()` 用原图多边形补回被抠掉的刀刃直边（S029）。
- 合成：`units/chorus1_sprites.py`（`install(globals())` 返回各 SxxxSprite，继承原镜头类，复用原背景/粒子/刀光/字幕，只换人物）；`units/chorus1.py` 在 SPRITE_MODE=1 时替换 SHOTS，`SPRITE_SHOTS=S030,S035` 可只换部分镜头。镜头时长 = 剪辑表 CUT_F 原值（不拉长）。
  - 动作镜头 = 关键姿势硬切：S030 ready→raise（61.40 闪白，刀尖星芒 61.88 按精灵最高点定位）；S035 run→leap（69.86）→slash（70.00 命中闪白 + 代码弧形刀光/碎砖/火星/速度线）；S045 windup→spin（84.30，角向模糊）→finish（84.47 命中 + 环形刀光 + 雨被斩开）。
  - S038 刃面倒影 = 生图眼部特写（冷色化、留一点琥珀）按刀身蒙版羽化合成；S044 一张图 + 代码鞘口光线随拇指推开渐亮（风停不吹）；S046 人物精灵在后虚焦、代码刀身在前（刻字/墨爆不变）。
- `units/sprite.py` 改动：`fit()`（按 alpha 包围盒高度缩放 + 脚底锚点）、`top`（最高点）、保色遮罩 `red_mask()`（色相比例取暗红，红领/红穗/血不去饱和）、`alpha/defocus/rotblur` 参数。`units/c1kit.finish(..., red_keep=)`：SPRITE_MODE 下按色相比例保住暗红（修试点「去饱和吃掉暗红内领」）。
- 渲染：`units/c1sprite_render.sh`（帧 1784–2586 = 59.47–86.20s，2 进程 × 90 帧分块写 /tmp 再拷 `out/chorus1_sprite/chunks/`，断点续跑；混 `audio/谁定正邪.mp3`）→ `out/chorus1_sprite/chorus1_sprite_master_crf18.mp4`（不入库）+ `out/chorus1_sprite/chorus1_sprite_crf23.mp4`。联系表 `lib/rig_test/c1_sprite_contact.py` → `lib/rig_test/c1_sprite_contact.jpg`。
- 新沙箱注意：skia 需要系统库 `sudo apt-get install -y libegl1 libgl1`（否则 props.CharWall 报 skia None）。
- 产出（05:52）：`out/chorus1_sprite/chorus1_sprite_master_crf18.mp4`（26.73s，1920×1080 30fps + AAC，55.9MB，不入库）、`out/chorus1_sprite/chorus1_sprite_crf23.mp4`（入库）、`lib/rig_test/c1_sprite_contact.jpg`。
- 自评仍待改：S037 远景背影太小太暗，几乎看不见；S045 旋斩中间姿势（84.30–84.47）角向+方向模糊后成一团糊影，读不出转身；S035 斜劈落地的代码弧形刀光与精灵手里的刀不完全对位；S039 缓行只是整张图横移+起伏，脚不动（近看像滑行）；S044 / S029 构图满屏没有景深层次，略像贴图；S043 仍沿用试点图（马尾顶被裁）；S046 人物在刀后虚焦，OK。

## 17. 全片精灵版收尾（第四任接手，2026-11-09 07:40– CST）
- 接手环境：新沙箱，仓库克隆后用软链接 `/workspace/work/mv` 指向克隆目录（代码路径写死）；pip 装 requirements + `libegl1 libgl1`。
- 复查联系表 `out/full_sprite/contact_v2.jpg`（`python3 render_sprite_full.py contact …`，78 个精灵镜头，约 3 分钟）：第一版联系表后的修正全部生效——桥段整体提亮、S007/S014 提亮、S021 竖排字让开手部、中近景人物缩小不再顶头；未发现新问题。
- 仍偏弱（未改）：S007 远景剪影偏淡；S098 前景大黑剪影压住虚化字幕；S110 人物小而暗；S062 手偏灰偏糊；S056 拳头裁剪后发闷。59.47s、86.2s 两处副歌一精修版与旧场景+精灵的画风跳变仍在。
- 整片渲染：`run_sprite_chunks.sh`（31 块 × 240 帧，2 进程，约 1.8 s/帧/进程，整片约 60 分钟）。后台 shell 单次最长约 19 分钟，所以用 `timeout 1150` 分段跑、断点续跑；被 timeout 打断时残留的 python 进程要先 `pkill -9 -f '[r]ender_sprite_full'`（必须用方括号写法，否则 pkill 会匹配并杀掉自己的 shell），并删掉 `/tmp/sfc/tmp_*.mp4`。分块按 .gitignore 不入库，放在持久工作区。
- 导出：`export_full_sprite.sh` → 母版 `full_sprite_master.mp4`（视频流拷贝 CRF17 + AAC 320k，不入库）、网络版 `full_sprite_web.mp4`（1080p CRF21 + AAC 192k，不入库）、预览版 `full_sprite_720p.mp4`（CRF26 + AAC 128k，入库）；每个文件 ffprobe + 全量解码校验，结果写 `out/full_sprite/verify.txt`。
- 同步：`crew/export_chat.py` 改为以 `CONVERSATION_part2.md`（前三任冻结）为底 + 本任 journal（旧版指向上一任的 journal 目录，在新会话里会把前任记录清空）。另设定时任务每 30 分钟 autosync + 渲染中断自动续跑（到 2026-11-11 08:00）。
- 安全：之前贴进对话的 RH Key 建议作废换新（仓库公开，导出时已打码）。

## A 组第六棒交接（2026-11-09）
- **负责文件**：`units/sec_a_intro_verse1.py`（a_intro_verse1，帧 0–1321，29 镜，SHOTS/CUTS 表驱动）、`units/a_r6.py`（第六棒辅助：精灵预处理/去灰边、宣纸、纸面印痕、凹刻字、按原图点锚定，只被 sec_a 用）、`units/a_kit.py`、`units/a_contact6.py`（联系表分块脚本）、`tools/a_test.py`（逐镜试渲）、`crew/round4/A_storyboard.md`、`crew/round4/A_gen_state.json`。
- **本棒改了什么**（对照 `crew/round4/critic_A_r3.md` = 72 分、不可交付 V08/V09/V17；提交 787810e → 8ce2eb6，12:47–13:11 CST）：
  - **V08**：握玺侧面 CU → 俯拍纸面印痕，层级 纸 → 印 → 玺影（精灵 `A_r6/tsh_seal_lift`，只裁手 + 玺）。（08b78d8）
  - **V09**：青铜天平生图 `A_r6/bronze_scale` 作底 + 暗殿三层 + 歌词梁下两列竖排。（08b78d8）
  - **V15**：换 `A_r6/carve_grip` 双手握柄横刻一行「我的主张」；后又改刻完收刀让字。（eecf2ec、8ce2eb6）
  - **V16**：金光里巨印剪影成形（`A_r6/giant_seal`）；入转场改 `a_glyph`（「主」字遮罩，原叠化两脸糊在一起）。（eecf2ec、8ce2eb6）
  - **V17**：重做 = 巨印侧面坠落 → 石坑凹刻「正」，不着红（去红方印）；减体积光。（eecf2ec、8ce2eb6）
  - **V18**：印坑裂缝作人物引导线；入转场 flash_red → 尘浪 `smoke_through`（去红印感）。（6b82d5e、8ce2eb6）
  - **V13**：重构图；入转场 → slash_wipe（6b82d5e），最终 CUTS 表为 `a_split` 沿 V12 斩线一刀两块（8ce2eb6）。
  - **V14**：鞘口火星成字，字不再上刀身（去撞 S046）。**V12**：红雨幕 + 歌词移左下。**V04**：改远处火把光斑长街，军阵背景减到 2 次。**V03**：「五百」切前退净。**A03**：入转场改冷光细线。**A07a**：片名区城楼压暗虚焦、去前景旗。（均 6b82d5e）
  - 歌词错位修正（eecf2ec）。
- **联系表 / 关键帧**：`out/round4/A_contact_v6.jpg` + `A_contact_v6_p0.jpg`、`_p1.jpg`（每镜 55% 帧）；`out/round4/A_keys_v5.jpg` + `A_keys_v5_p0.jpg`–`_p3.jpg`（转场中点 + 关键帧，含 V08 落印前后、V17 落地前后、V09 中帧、A07a 11.5/12.9）。
- **积分**：本棒 4 张 × 3 = 12 点（tsh_seal_lift、bronze_scale、giant_seal、carve_grip，均 try1 采用）；A 组累计 **57/80**（`A_gen_state.json` spent=57；genlog 已记采用行）。
- **生图资产**：`assets/gen/A_r6/{tsh_seal_lift,bronze_scale,giant_seal,carve_grip}_{raw,cut}.png`；候选原图在仓库外 `gen_cands/A_r6/*_try1_0.png`。
- **已知风险 / 未决**：
  - `crew/round4/A_storyboard.md` 只记到第五棒，**第六棒返工没写进 storyboard**（以本节和 git log 为准）。
  - `out/round4` 没有 A 的每镜三帧（triple）联系表或低清 mp4；critic_A_r3「下轮评审要看到的」要求二选一，`a_contact6.py triple` 已支持但未出图。镜内运动仍只靠单帧判断。
  - critic_A_r3 P1 第 18 条（V10 盘体厚度 /「里」字）、P2 15–17、19（Cait 署名、A02 月、脸部特写 5 次、V21 锋芒背景）git log 里没有第六棒对应改动。
- **下一步**：第四轮评审中（总导演派全新上下文评审，看 A_contact_v6_p* + A_keys_v5_p*）。
- **接手要点**：
  - 代码路径写死 `/workspace/work/mv`（软链到仓库）。超过 1 帧的渲染必须 `tools/cpu_slot.sh` 包一层。
  - 单帧 / 逐镜试渲：`python3 tools/a_test.py V08 V17`（每镜 15%/55%/92% 三帧 → `/tmp/at_<镜>_<比例>.jpg`，打印耗时/报错）；代码内取帧 `M.frame(f, cache)`（`import sec_a_intro_verse1 as M`）。
  - 联系表：`tools/cpu_slot.sh python3 units/a_contact6.py part <contact|keys|triple> <i0> <i1>`（→ `/tmp/acon6/`，可续跑，已渲帧跳过）→ `python3 units/a_contact6.py assemble <kind> out/round4/A_contact_v7.jpg [每块行数，默认 4]`（整图 + `_p<n>.jpg` 分块）。
  - 提交只加自己的路径：`git add <文件> && git commit -m "[A组] …" -- <文件>`，shell 带 github 凭据。

## E 组第六棒交接（2026-11-09）
- **负责文件**：`units/sec_e_final_outro.py`（e_final_outro，帧 5797–7241，38 镜）、`units/e_r6.py`（第六棒新增：纸脸材质、light_sweep、gold_leaf、lava_crack、秤）、`units/e_kit.py`、`units/e_r3.py`、`units/e_r5.py`、`tools/e_contact.py`、`tools/e_check.py`、`crew/round4/E_storyboard.md`（「第六棒返工」一节是逐镜权威记录）。
- **本棒改了什么**（对照 `crew/round4/critic_E_r3.md` = 72.5 分、不可交付 E08/E02/E20，主攻「不重复」；提交 d6303ff → 520f821，12:49–13:12 CST，1–18/n）：
  - **E08**：换 `E_r6/emperor_cu`（与 E07 同一白发老者）+ 宣纸叠皱/接缝 `R6.paper_skin`，火从眉心烧洞露出鬼屠双眼（f189950）；亮部去暖，白发不读成金发（9cb299b）。
  - **E02**：去背影举刀指日 → 正面极低机位 3/4 扛刀（`E_r6/shoulder_low`），「刀」「不」「放」三方小朱印随唱盖在拳与护臂上（storyboard；git 里随 22a0218「E02 联动」）。
  - **E20**：低地平线、日轮露上缘偏右，偏左墨色巨字「天」逆光剪影自下熔塌；入转场 → `R6.light_sweep`。（89be222）
  - **E01**：竖刀刀尖朝天（`E_r6/blade_tip`，4K 原图裁刀尖重抠），碑拓「血」在刃面 + 刃面倒影，日光沿刃自下而上扫，「未冷」移右上。（22a0218）
  - **E29/E30**：片名重排（340px 行书、字距 0.14em、墨迹宽 58%，224.57s 前四字成形、「邪」朱红金边）；E30 入点改沿斩线暖闪。（64b8950）
  - **E22**：横刀成秤（「我」「来」两端秤盘、「量」刀心秤砣、日为支点）。（7d267ca）
  - **E27c / E28 / E26**：斩线移到「理｜昭」字缝、去重影与下坠模糊；E28 入转场 impact 不带出匾；「正道沧桑」全金 + 墨描边 + 暗衬、上移。（8506f1d）
  - **E31**：正俯拍微距焦土残纸残字；E34 入转场改灰烟（e0e09c3），烟色压暖（b7febc9）。**E33**：近景黑漆刀鞘 + 红穗（`E_r6/scabbard_tassel`，见 storyboard），署名提前 1.0s 出完（9cb299b）。**E34**：推镜 + 远影向日走（storyboard）。
  - **E11 / E12**：E11 正面压暗 + 右侧暖轮廓光 + 接触阴影；E12 俯拍人物 ×1.5 + 印心插刀。（b7febc9）
  - **E18 / E19**：中缝 → `R6.lava_crack` + 两卡外错，「何」移到 E19；E19 入转场 → `R6.gold_leaf`。（8a5897b）
  - **E28 / E27b**：取景放宽到马尾 + 腰带（去脸）、编织纹 + 逆光透红边；E27b 剪影满画高、轮廓光加倍。（10198fb）
  - **P2**：「骨未凉」在 E14T 内出完；E10「它」改金；E05 whip 减弱留匾纹。（8a6b041）
  - storyboard 记第六棒（c02d29a）。git log 里没有单独的 3/n、9/n 提交。
- **联系表 / 关键帧**：`out/round4/E_contact_v6.jpg` + `E_contact_v6_p0.jpg`–`_p2.jpg`（38 镜中点，1920×≤1184）；`out/round4/E_keys_v6.jpg` + `E_keys_v6_p0.jpg`–`_p3.jpg`（转场中点/冲击帧 + 歌词关键帧）。
- **积分**：本棒 4 张 × 3 = 12 点（emperor_cu、shoulder_low、blade_vert、scabbard_tassel，均 try1 采用，genlog 已记）；E 组累计 **54/80**。
- **生图资产**：`assets/gen/E_r6/{emperor_cu,shoulder_low,blade_vert,blade_tip,scabbard_tassel}_{raw,cut}.png`（blade_tip 由 blade_vert 4K 原图裁出，E01 只用 blade_tip）；候选在仓库外 `gen_cands/E/E_r6/*_try1_0.png`。
- **已知风险 / 未决**：
  - E06 挂轴随机化未做（storyboard 明记）。
  - 第六棒 storyboard 没有写「未决 / 自评弱点」小节；E_storyboard 前几棒遗留项（E07 纸扎近看灯笼感、E03 碑林程序方碑、副句漂移/E36 呼吸只验单帧）未见第六棒改动。
  - 仍未出 mp4，碎切节奏与镜内运动只验单帧。
- **下一步**：第四轮评审中（总导演派全新上下文评审，看 E_contact_v6_p* + E_keys_v6_p*）。
- **接手要点**：
  - 代码路径写死 `/workspace/work/mv`。超过 1 帧的渲染必须 `tools/cpu_slot.sh` 包一层。
  - 单帧核查：`python3 tools/e_check.py /tmp/e.jpg 6080`（多帧：`tools/cpu_slot.sh python3 tools/e_check.py out.jpg f1 f2 …`，640 宽网格；`FULL=1` 另存全尺寸 `/tmp/e_<f>.png`）。
  - 联系表：`tools/cpu_slot.sh python3 tools/e_contact.py contact out/round4/E_contact_v7.jpg`；关键帧：`tools/cpu_slot.sh python3 tools/e_contact.py keys out/round4/E_keys_v7.jpg`；分块：`python3 tools/e_contact.py split out/round4/E_contact_v7.jpg`；只看帧号：`python3 tools/e_contact.py list`。
  - 提交只加自己的路径：`git add <文件> && git commit -m "[E组] …" -- <文件>`，shell 带 github 凭据。

## D 组第七棒（2026-11-09 13:00–13:45 CST）· d_bridge 帧 4839–5797 · 30 镜 · 平均 1.06s
- 对照 critic_D_r4（83.5）：P0 四条全部落实（S12 撕裂口 + 双轮廓光 + 三层山雾；「矩」182.92 落字；S08 去「人」；S06/S26 顶行收进安全框）。P1：天平换水墨生图并修好对位（右盘字堆、底座竖缝）；S08/S09 加主光、体积光束、纸纹浮雕、后景（碑影 / 远山雾）、前景虚焦纸屑飞墨、印/笔轮廓光；S11 同向轮廓光；S21 木牌去字；S22「闯」挪到侧边；两帧闪白 4→2（S14 burn_wipe、S24 bolt_cut）。
- 交付：`out/round4/D_contact_v10.jpg`（+`_p0/_p1`）、`out/round4/D_keys_v6.jpg`（+`_p0/_p1/_p2`）；细节见 `crew/round4/D_storyboard.md` §8。
- 积分：本棒 1 张（D_r7/scale 3 点），D 组累计 48/80。
- 遗留：P2（S04「牲」被裁、S01 开头偏暗、S27 停顿、S30→E 接帧）；S07 字堆缩略图像墨团；未出 mp4 动态验证。下一步：派第五轮评审。

## C 组第七棒（2026-11-09 13:30–14:00 CST）· c_pre2_chorus2 帧 3534–4839 · 43 镜 · 平均 1.01s
- 起点：critic_C_r3 76.5，C06 和 C41 不可交付，精致度 10/15。第六棒已改完 P0 四条，本棒先复渲单帧 124.40 / 145.45 / 161.10 核对，四条都到位。
- P1 已改：
  - C35b 换定妆脸：用已入库的 C6/c35b_bear，新工具 `tools/c_solidify.py` 修补手和刀面的半透明，输出 `assets/gen/C6/c35b_bear2_cut.png`。切点改到「扛」154.70。
  - C33「对」「错」改成刀面镂空字（新函数 `etched_glyph`：暗槽、亮边、暗衬）。
  - C30 上沿裁到颈下。
  - 连续硬切里 7 个改成有设计的转场：whip_pan_blur ×2、match_cut、smoke_through、flash_white、slash_wipe，以及新增的 `units/c_trans.tip`（穿过刀尖光点，不出白卡）。
  - 其余硬切按 `HARD_FX` 分 flash / slam / zoom / ink 四式冲击。
  - C04、C05 字号提到 ≥80px；「这一」移出衣摆。
- 产出：`out/round4/C_contact_v8.jpg`（_p0–_p3）、`out/round4/C_keys_v5.jpg`（_p0–_p5）。逐条记录见 `crew/round4/C_storyboard.md`「第七棒返工」。
- 积分：本棒 0 点，累计 78/80。
- 仍弱：
  - C09 和 C32 同构，C32 换精灵需要生图。
  - C34 的「是」「对」靠左缘。
  - C15 人物小，C19 枪头没有透视。
  - 联系表环境：缓存设 `C_CACHE=/workspace/work/c7tmp/cache`。整表一次渲会被 OOM 杀掉，要按 ≤10 张分批跑。

## E 组第七棒（2026-11-09 13:35–14:10 CST）
- **对照** `crew/round4/critic_E_r4.md`（80 分，精致度 11 贴线；不可交付 E08、E01）。逐镜权威记录见 `crew/round4/E_storyboard.md`「第七棒返工」。
- **负责文件**：`units/sec_e_final_outro.py`、新增 `units/e_r7.py`（宣纸折痕/接缝、三层烧洞 `burn_hole`、笔画自燃字 `self_burn_glyph`、暖雾转场 `warm_veil`），其余 E 组文件同第六棒。
- **P0**：E08 烧洞重做（三层边：暗褐焦痕+纤维毛边 / 断续橙红火线 / 卷起碳化黑边；洞内 ≈1% 亮度只露火光照亮的鬼屠双眼，眼距洞缘 ≥40px；宣纸叠皱 40% + 两条斜接缝；「伪装」去外框改笔画自燃）。E01 竖刀改代码截面着色（镐筋分暖亮刃面/冷暗平地、刃口亮线、冷暖镜面反射、斜尖+横手线、铜鎺+铁镡+缠柄入画、「血」≈刃宽 85% 随扫光反光）。
- **P1**：E12 刀柄/金边镡/红穗甩出印外；E11/E13/E21/E28 去身后日轮改画外光源；E33/E34 入转场改 `warm_veil`（中间帧有内容）；E05 whip→impact；E15 去「骨未凉」；E25「正」出光带；E26 字揭开后淡入。**P2**：E28 发丝焦外虚化。
- **保住未动**：E22、E18、E31/E33/E35 本体、E35→E36。
- **联系表**：`out/round4/E_contact_v7.jpg` + `_p0`–`_p2`；**关键帧**：`out/round4/E_keys_v7.jpg` + `_p0`–`_p3`。
- **积分**：本棒 0；E 组累计 54/80。
- **提交**：c5ddf4d（1/n E08）、66e9997（2/n E01）、2e86249（3/n P1）、a869553（4/n E28）、a15696b（5/n 联系表）、c157f50（6/n storyboard）、7/n keys、8/n 本节。
- **风险**：E01 刀为代码绘制，刃面偏哑光、铁镡无纹；E08 接缝斜穿脸面近看像划痕、洞内眉形偏浓；E12 刀柄穗偏图形化；P2 的 E34 远影、E10、E15 挂轴材质、E30 静置、E06 未做；仍无 mp4。
- **下一步**：派全新上下文第五轮评审（看 E_contact_v7_p* + E_keys_v7_p*）。

## A 组第七棒（2026-11-09 13:32–14:10 CST）
- **对照**：`crew/round4/critic_A_r4.md`（75 分；「不重复」6/10 未达线；不可交付 V17 印坑、V08 后景脸、V12 入、V21 入）。逐镜记录见 `crew/round4/A_storyboard.md`「第七棒返工」。
- **新文件**：`units/a_r7.py`（Crater 凹坑 / flagstones 石板 / tsh_seal_noface / candle_screen / a_cleave / ink_bg / face_shade，只被 sec_a 用）、`tools/a_peek.py`（多时刻核帧网格，`FULL=1` 存全尺寸）。`tools/a_contact.py` 加 `triple` 与新版 `keys`，part 可续跑。
- **P0**：V17 石板真凹坑（崩口、内壁厚度、碎石、裂缝暖光，「正」只凹刻靠侧光读，无框无色；去砖墙/闪电/碎屑/色散）；V08 去脸 → 屏风烛光，「定对错」移右下；V12 入、V21 入改 `a_cleave`（根因：`Section.raw` 在 pre=0 时把 A 设成 B → 两半是同一镜的复制），V21 去印面灰平板；节奏素材 `A_rhythm_v1`。方印母题只剩 V08「罪状」。
- **P1**：V10 铜盘质感 + 盘沿厚度、删竖线；V13 入 → a_glint；A04 入署名提前退净；V05「拦不住」右移；V18 同套石板 + 印坑一角、「那我」160px；V19 压亮冷调 + 侧光；A02 月心出框。
- **交付**：`out/round4/A_contact_v7.jpg`（+`_p0/_p1`）、`out/round4/A_keys_v6.jpg`（+`_p0–_p3`）、`out/round4/A_rhythm_v1.jpg`（+`_p0–_p3`，每镜起/中/止）。低清 mp4 未出。
- **积分**：本棒 0 点；A 组累计 **57/80**（剩 23）。
- **提交**：7996a77（1/n V17）、574f727（2/n V08）、4102d8f（3/n 转场）、c06c1b7（4/n V10）、a03f88a（5/n P1）、8d2f1fd（6/n 联系表）、e41685b / 5a849d5（7–8/n 三帧表 + 歌词）、6800c92（9/n storyboard）。
- **风险**：V18 坑沿横贯亮折边可能读成一条线；V17 方形凹坑本身仍是方形；P2-13/14/16（Cait 横排、V02 字号、V09 入红块）未改；无 mp4。
- **下一步**：派全新上下文第五轮评审（看 A_contact_v7_p* + A_keys_v6_p* + A_rhythm_v1_p*）。

## D 组第八棒（2026-11-09 13:45–14:10 CST）· d_bridge 帧 4839–5797 · 30 镜 · 平均 1.06s（READY=True 不动）
- 对照 critic_D_r5（87.5 已过线）做打磨，镜头表 / 切点 / 节奏不变：
  - P1：S20 冷轮廓 + 提亮 + 身后湿面反光（冲刺可读）；S22 冷蓝调色 + 「闯」朱红反光 + 脸/刃冷高光；S15 火光暖橙轮廓 + 余烬集中。
  - 冲击硬切 7→5：S10 入点 `ink_press`（巨笔墨压），S21 入点 `plaque_sweep`（木牌横扫遮挡），都写在 `units/sec_d_bridge.py`，共享库未改。
  - P2：S04「牲」不再出框；S12 刀身金色碎片去掉；S23「天」右移 + 冷白字缘；S30→E 接帧实测连续（暖白，亮度 239→250），未改。
- 交付：`out/round4/D_contact_v11.jpg`（+`_p0/_p1`）、`out/round4/D_keys_v7.jpg`（+`_p0–_p3`，最后 6 张 r8* 为核对帧）；细节见 `crew/round4/D_storyboard.md` §9。
- 积分 0，D 组累计 48/80。
- 遗留：P2-8（188.30 黑场留刀刃反光）没做；轮廓光是程序描边，动态里精灵边缘可能闪，没出 mp4 验证；S23 改动被 13:53 的「自动同步」提交（257fa62）卷走。

## E 组第八棒（2026-11-09 14:16–14:50 CST）· e_final_outro 帧 5797–7241 · READY=True 不变
- **对照** `crew/round4/critic_E_r5.md`（85.0 贴线过）。打磨轮：镜头表/切点/转场种类全不动，只改镜内画面与 E23 冲击强度。逐镜见 `crew/round4/E_storyboard.md`「第八棒」。
- **核对**：E01 第八棒刃身（`units/e_r8.py` BladeECU）已接线，单帧亲看生效。
- **P1**：E01「血」阴刻槽壁受光方向修正（原读成凸起）+ 残血压暗；E23 入点 impact `soft`（冲白只加亮部、减半，色散减半）；E34 远影 ≈ 画高 6–7%、辉光后压回实黑剪影 + 细金边、脚下向镜头长影 + 接触影。
- **P2**：E10「自」「己」水平并排；E12 俯拍人物锐化 + 紧接触影；E15「天理」挂轴 → 木律令牌（`e_r8.wood_tablet`，阴刻填金）。
- **交付**：`out/round4/E_contact_v8.jpg`（+`_p0`–`_p2`）、`out/round4/E_keys_v8.jpg`（+`_p0`–`_p3`）。与 v7 对比无退步。
- **积分**：本棒 0；E 组累计 54/80。
- **提交**：1/n（E23，被 8f00f58 自动同步卷走）、5d52485（2/n E34）、2606cb4（3/n E10/E12）、4/n E15（被 12d94c3 自动同步卷走）、0b2a03c（5/n E01 血）、47f7e1f（6/n 联系表）、2039832（7/n storyboard）、8434829（8/n keys）、9/n 本节。
- **仍弱**：E01「血」缩略图下仍偏朱红块面；E34 长影是直条，不贴山脊；E15 木牌在橙闪 2 帧泛橙、木纹偏规则；E08 洞形/火线、E28 发丝、E30 静置、hard 切占比未动；无 mp4。
- **下一步**：总导演决定是否派第六轮复评（看 E_contact_v8_p* + E_keys_v8_p*）。

## C 组第九棒（2026-11-09 14:16–14:45 CST）· c_pre2_chorus2 · READY=True 不变 · 打磨
- 复核（单帧亲眼看）：C03–C05 真皮影 ✔、C41 连续烧边 ✔、C32 仰拍逆光剪影与 C09 去同构 ✔（三者代码被 13:59/14:02 自动同步卷入，无 [C组] 提交信息）。
- 本棒改动（critic_C_r4 余项）：P1④ C04「谁的正义」、C05「成了交易的」移到视线中心；C41 刀路焦痕去虚线；P2⑧ C21「一方」放大加暗衬；P2⑨ C16「血」上移；P2⑩ C37 匾心先有暗刻「判」；P2⑪ C27 入改 smoke_through、C28 入改 flash_white（去糊团/鬼影）。
- 修渲染不确定：c_kit.tex 缓存键不含 seed，分块渲染时云/水纹随起点变化（C15 会变成白曝团）；sec_c 导入时预热，任何起点 = 整段顺渲。**整片渲染若分块，C 段现在各块一致。**
- 交付：`out/round4/C_contact_v9.jpg`（_p0–_p3）、`out/round4/C_keys_v6.jpg`（_p0–_p5），与 v8/v5 并排比对无退步。积分 0，累计 78/80。
- 提交：d590282（1/n）、12d94c3（2/n 被 14:21 自动同步卷入）、b53e24f（3/n 预热）、385cc48（4/n 联系表）、9e6bdf5（5/n keys）、本节。
- 仍弱：C26 碎片仍有三角感（试改更差已回退）；C13 风眼平面；C19 枪头无透视；C15 雷光未勾人；C26>C27 石尘中间帧偏素、「看个」暗衬在灰雾上显出一块暗斑；无 mp4。
- 环境：git 用户名没配，提交需带 GIT_AUTHOR_*/GIT_COMMITTER_* 环境变量（sannian66）；联系表缓存 C_CACHE=/workspace/work/c7tmp/cache（换代码后要清空，文件名不含版本）；C18 单帧初始化约 53s，含 C18 的批次要单独跑。
