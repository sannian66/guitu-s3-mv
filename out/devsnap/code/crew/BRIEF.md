# 《谁定正邪》MV · 剧组总纲（所有子代理必读）

## 作品
- 《鬼屠》第二季片头主题曲《谁定正邪》，4:01（241.34s），武侠/江湖、反抗"大局""规则"、一人一刀问天。
- 出品人 西几王传媒；编剧/导演 苏打；美术设计 Cait；AI画师 沉溺、雪晴、索恩；音乐 西几王。

## 铁律
1. **纯代码**：所有画面由 numpy / OpenCV / PIL 程序化生成。禁止 AI 生图、禁止下载图片素材、禁止立绘。字体只用 `/workspace/work/mv/fonts/` 里的四款（MaShanZheng 马善政楷、ZhiMangXing 志莽行书、LiuJianMaoCao 流江毛草、NotoSerifSC 思源宋）。注意马善政无「·」字形。
2. 输出规格：1920×1080，30fps，上下黑边各 120px（画面有效区 1920×840），帧函数返回 float32 RGB 0–1。
3. 色彩：水墨黑白灰为底，只允许 **朱红**（≈0.72,0.06,0.05）与 **金**（≈1.0,0.76,0.40）两种强调色。
4. 机器：2 vCPU、~7.9GB 内存、无 GPU。单帧 1080p 目标 ≤0.8s。大的静态层在 `__init__` 预计算，逐帧只做变换与合成。
5. 用户对上一版的差评（必须全部解决）：**节奏慢、画面简单、重复多、不够精致、分镜没设计感、没有转场、歌词排版简单**。
   - 镜头时长：主歌 2–4s，预副歌 1.5–3s，副歌 0.9–2s（按小节/半小节切，鼓点上切）。
   - 每个镜头必须有运动：推、拉、摇、移、甩、升降、手持抖动、速度坡度（ramp），至少一种。
   - 景别要变化：大远景/全景/中景/近景/特写/大特写交替；构图有前中后景层次。
   - 三段副歌不得重复同一组镜头；可以有母题（motif）呼应但画面要有变化和递进。
   - 每次切镜都要设计转场或刻意的硬切（匹配剪辑、刀光切、墨晕、甩镜模糊、闪白、纸撕、碎裂、遮挡转场等）。
   - 歌词排版要有设计：竖排、错落、超大单字、逐笔书写、碎字、与画面物体互动（刻在刀上、印在纸上、被斩断）等，按段落变化。

## 数据（/workspace/work/mv/）
- `song.mp3` 音频；`analysis.npz`：t, rms, onset, low（低频能量包络）, beats（522 个节拍时间，≈129 BPM，1 拍≈0.465s，1 小节≈1.86s）。
- `align.json`：56 句歌词，每句 start/end 与 words（逐词时间）。`scenes.py` 里的 `LINES` 已把它展开为逐字时间（`LINES[i]['text'], ['times']`），`CT(line, char)` 取某字时间。
- 段落：前奏 0–15.21（已有 Intro，片名在 7.85s 重击，可保留可重做）；主歌一 15.94–43.5（行0–7）；预副歌一 44.0–58.3（行8–11）；副歌一 59.5–86.2（行12–19）；间奏 86.2–89.4；主歌二 89.4–116.9（行20–27）；预副歌二 117.9–131.7（行28–31）；副歌二 134.5–161.3（行32–39）；Bridge 162.6–192.1（行40–47）；副歌终 193.2–221.2（行48–55）；尾奏 221.2–241.34（片名+出品信息+淡出）。

## 现有代码（可读、可复用，不要改坏）
- `fx.py`：text_layer、comp_text、slash、Embers、Rain、glow、seal、finish、ink_wipe_mask 等。
- `proc.py`：fbm2/fbm1、paper、mountain_layer、mist、army、balance、dao、bricks、ink_bleed、hero（静态剪影）。
- `render.py`：Intro、ShanShui（含 dawn）、InkWipe、env/ease/eout、BEATS、A_LOW。
- `scenes.py`：上一版全片（被嫌弃），可作反面教材与工具来源。

## 剧组分工与文件归属（只写自己的文件）
- 导演组：`crew/storyboard.md`（人读分镜）+ `crew/shots.json`（机读镜头表）。
- 美术·角色组：`lib/rig.py`（可动的刀客骨骼/布料/动作库，及其他角色/群像）。
- 字幕·转场组：`lib/typo.py`（歌词排版与书写动画）、`lib/trans.py`（转场库）。
- 各分段摄制组（第二阶段）：`units/<段名>.py`，实现导演组镜头表里属于自己的时间段。
- 剪辑/质检：`crew/qa.md`。

## 接口约定
- 镜头/段落：`class X: def __init__(self); def frame(self, t, dt) -> (np.float32[H,W,3], ca:int)`，t 为歌曲绝对时间（秒）。
- 库函数无全局副作用；随机数用传入 seed 的 `np.random.default_rng`。
- 自检：用 `/workspace/work/mv/preview.py` 的方式抽帧拼联系表，`read_file` 亲眼看图，检查文字截断、溢出黑边、对比度。
- 沙箱可能丢 pip 包：`pip install --user -q numpy pillow scipy opencv-python-headless librosa soundfile`。
