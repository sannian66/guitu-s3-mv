# 《谁定正邪》MV 交接计划书

《鬼屠 · 第二季》主题曲《谁定正邪》的歌词 MV。**全部画面由代码生成**，不用 AI 生图、不用立绘和图片素材。

## 0. 硬性规则（用户定的）
- **纯代码**：山、雾、月、军阵、刀客剪影、天平、刀、墙、粒子、印章全部由 numpy/OpenCV 算出来。`_ai_unused/` 里是早期的 AI 生图，**禁止使用**（仓库里没有提交）。
- 视觉语言：2.39 宽银幕黑边，只用黑、白、灰、血红、金色；书法字（马善政体）；红色「鬼屠」印章；刀光贴着鼓点。
- 画幅：16:9，1920×1080，30fps。竖屏版还没做，用户也还没要。

## 1. 片头信息（必须出现）
| 职务 | 名字 |
|---|---|
| 出品人 | 西几王传媒 |
| 编剧 / 导演 | 苏打 |
| 美术设计 | Cait |
| AI画师 | 沉溺、雪晴、索恩 |
| 音乐 | 西几王 |
| 片名 | 鬼屠 · 第二季 |
| 主题曲 | 《谁定正邪》 |

时间都落在小节重拍上（约 129 BPM，一小节约 1.86 秒）：
- 0.30s 墨从黑场晕开，露出夜色山水和血月
- 0.45 出品人 → 2.21 编剧/导演 → 4.06 美术设计 → 5.97 AI画师
- 7.85 **片名重击**：刀光横扫，「谁定正邪」墨字炸出，闪白、震屏、飞火；8.31 印章落下；8.35 出「鬼屠 · 第二季」和「主题曲」
- 9.68 音乐 西几王
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
