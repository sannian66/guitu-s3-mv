# 第八轮改版方案与交接（2026-11-11 04:55 CST）

## 一、用户已定 / 偏好
- 画风：**风格 D**＝用户自己的提示词画风（日漫墨线 + 网点 + 严格黑白血红）。出图渠道 **www.nananobanana.cn**，模型 **RH_image2**（3 积分/张 2K；备选 nano-banana-pro 2 积分/张）。纯文生图效果最好，参考图只用于角色一致（定妆照）。
- **不要字体叠加的巨字**（独立图层、不融入画面）。字只在「画进场景里」时用（刻在墙上、泼在纸上那种）。歌词字幕保留。
- 用户 04:52：**不是非得要 3D**。
- 试做范围：副歌一开头 3 秒（S028–S030，「血未冷 刀不放」）。

## 二、第一版试做（Remotion + three.js 分层）暴露的问题
交付物：`crew/round8/S028-030_新版.mp4`、`S028-030_对比.mp4`（提交 c68fa05），合成 `remotion_test/src/R8Chorus.tsx`（ID `R8-S028-030`）。
1. **素材漂移**（用户 04:48）：相机 lookAt 指向 z=-30 远点而非主体层，升镜时主体跟着滑；对齐时刻是镜头起点；各层手动 dy 偏移。已改（lookAt 主体层、镜头中点严格对齐、粒子运动以中点为零），只出过静帧，未重渲。
2. **节奏不对**（用户 04:49）：试做用了 chorus1.py 类注释里的旧时间（59.48/60.534/61.463），但第六轮实际切点被 `CUT_F` 覆盖为 **帧 1779 / 1800 / 1828 / 1869**（59.30 / 60.00 / 60.933 / 62.30，已用成片场景检测核实）。三镜切点全部错位、不卡鼓。
3. **画面效果没还原**（用户 04:49）：现版每镜的效果见下表，试做几乎都没做。

## 三、现版（第六轮）S028–S030 必须还原的节奏与效果（来源 units/chorus1.py）
| 镜 | 帧 / 时间 | 入转场 | 主运镜（M3） | 镜内效果 |
|---|---|---|---|---|
| S028 ECU 刃上滴血 | 1779–1799，59.30–60.00 | 「血」字头**硬切**（切后 2 帧冲击） | expo_out 拉出 1.12→1.00，横移 x 50→90，滚转 -3°→0，yaw 4°→0；开头 0.15s 冲击脉冲 +6% | 血滴 **0.4x 慢放**坠落，59.70 落刃（=「未」字头）：皇冠飞溅 46 滴 + 刃面血迹扩散 + 冲击白光；速度残影；前景余烬 0.25；59.96 起 0.1s 色差 3px；曝光 GAIN 0.6 |
| S029 MCU 握刀手 | 1800–1827，60.00–60.93 | drop 重音镲 **smash cut + 闪白 0.17s** | sine_io + beat 加速，环绕 yaw -9°→+7° 绕手向右，x -40→40，末段上抬 y 0→-30（接上甩），z 1.06→1.00 | 握刀收紧动画；火星 55 颗斜掠；「刀」字头**白刃一闪**（斜向刀光）+ 震屏加剧；手持抖动 5px；虚焦月；前景余烬 0.6 |
| S030 LS 举刀指月 | 1828–1868，60.93–62.30 | **上甩**（甩镜向上 L=420，运动模糊） | sine_io + beat，摇臂升 y 60→-50、pitch -6°→+2°（仰→平），z 1.00→1.07 | 垂刀→举刀两姿势（刃光处硬切）；61.88 刀尖十字星芒；山脊中景、前景草叶虚焦大视差；前景灰 0.35 |
| 出口 | 1869 → S031 | 月轮 iris | — | — |
全段统一收尾 `c1kit.finish`：颗粒 0.04、暗角 0.5、bloom 0.35、色差、黑边 120px；字幕走统一字幕层 `units/subtitle.py`（serif_h：思源宋 SemiBold、下黑边一行、逐字按演唱时刻书写、句尾墨散；12a 血未冷「血」朱红 bleed+drip，12b 刀不放「刀」seal）。

## 四、两条路线
### 路线 1（推荐，用户倾向）：不换技术栈，只换素材
现有 Python 管线（`units/chorus1.py` + `units/chorus1_sprites.py`，SPRITE_MODE=1）本来就是「生图精灵 + 代码场景/卡点/运镜/粒子/刀光」，2.5D 运镜（M3）、前景遮挡视差（FG）、切点转场（CUTS）、闪切、收尾都在。改版只动素材和调色：
1. 在 `chorus1_sprites.py` 加 `STYLE_D=1` 开关：背景（dark_bg / K.sky / moon_sprite / mountains）换成 D 风格背景板，人物/刀/手换成 D 风格抠像精灵（`put()` 按包围盒高度落脚）。
2. 关掉冷色调色（`put()` 默认 grade 的冷蓝 tint、`finish` 的 grade），改「黑白血红」映射：保留红通道、其余去饱和；颗粒/暗角保留。
3. 去掉 S028 背景巨字「血」（用户偏好），改由 D 背景板里画进去的血墨晕承担。
4. 代码画的血滴、火星、刀光改成黑白红配色（RED 已是朱红，火星改白+血红，去金/冷白边光）。
5. 节奏、切点、转场、运镜、字幕**一行不动**，所以天然和现版一致。
6. 渲染：`tools/r6_drive.sh` 同一套；只渲 1779–1868 帧出试做段，与现版同段左右对比。
优点：零漂移（精灵锚在脚底坐标）、卡点与效果全部继承、无 Remotion 许可问题。缺点：视差是 2.5D（平移缩放 + 前景层），不是真透视。

### 路线 2：Remotion + three.js 分层（已试做一版）
要还原需把第三节逐项重写进 TSX（切点、甩镜、闪白、慢放、粒子、刀光、色差、颗粒），工作量大；Remotion 商用许可未确认（个人或 ≤3 人免费，其余需 Company License）。只建议给少数需要真透视运镜的镜头用。

## 五、提示词（风格 D，nananobanana）
模板 = 头段 + Scene + 尾段约束 + Reminder。全量见 `jobs/r7_styleD_nb.json`（4 镜风格试做）与 `jobs/r8_D_S028-030_layers.json`（试做分层 10 张）。
### 头段（每张一样）
```
ART STYLE: high-contrast Japanese manga ink illustration, sharp pen lines, solid blacks, screentone textures, brushed speed of a modern shonen cover. COLOR SCHEME: strictly black, white and one blood-red. Red used boldly on large graphic shapes (sky, sun, background block or light) and on key details, everything else black and white.
```
### 尾段（每张一样）
```
This is a multi-color palette distributed across different objects and lights, NOT a single-color filter or monochrome tint over the whole image. Anime illustration only, not photorealistic, no real people. Bold but controlled color design, refined and high-end, one clear focal point; not a cheap mobile-game ad, no particle spam. No text, captions, logos or watermark. 16:9 widescreen.

Reminder — art style: high-contrast Japanese manga ink illustration; color scheme: strictly black, white and one blood-red.
```
### 分层 / 精灵 Scene 写法
- 背景板：`Background plate only, no characters, ...`
- 抠像元素：`... Isolated on a perfectly flat pure chroma-key green (#00FF00) background with no shadows; the green is only a keying backdrop, not part of the palette.`（随后 `tools/cutout_green.py raw.png out.png 2048`）
- 角色：`Gui Tu (keep exactly the face, hair and costume of the reference model sheet)`，`input` 传定妆照 CDN 地址（`nb.upload` 偶发 502，直接用已上传地址）。
- 角色描述：a strikingly handsome young Chinese swordsman, sharp cold eyes, he does not smile; long jet-black hair in a high ponytail (pure black, no colored highlights), black robe with a red sash.

| 名 | 模型 | 参考 | Scene |
|---|---|---|---|
| S028_L1 | RH_image2 | 纯文生图 | Background plate only, no characters, no objects. A huge blood-red ink bloom spreading across white paper, wet ink edges, screentone gradient dots at the rims, black ink splatter flecks. Leave the center calm. |
| S028_L2 | RH_image2 | 纯文生图 | Extreme close-up of a long straight Chinese sword blade lying diagonally across the frame, polished steel drawn in sharp black pen lines and white highlights, a single drop of blood just splashing on the blade surface in a crown splash. Isolated on a perfectly flat pure chroma-key green (#00FF00) background with no shadows; the green is only a keying backdrop, not part of the palette. |
| S028_L3 | RH_image2 | 纯文生图 | Foreground element only: a few large blood-red droplets and fine black ink spatter flying toward the camera, motion blurred. Isolated on a perfectly flat pure chroma-key green (#00FF00) background with no shadows; the green is only a keying backdrop, not part of the palette. |
| S029_L1 | RH_image2 | 纯文生图 | Background plate only, no characters. Deep black night with a large blood-red graphic block at right, screentone gradient, speed lines radiating from center. |
| S029_L2 | RH_image2 | 定妆照参考 | Medium close-up of Gui Tu (keep exactly the face, hair and costume of the reference model sheet)'s right hand tightening around the black sword hilt, knuckles straining in silhouette, black leather bracer, red sash edge visible. Isolated on a perfectly flat pure chroma-key green (#00FF00) background with no shadows; the green is only a keying backdrop, not part of the palette. |
| S029_L3 | RH_image2 | 纯文生图 | Foreground element only: a stream of tiny white-hot and blood-red sparks streaking diagonally. Isolated on a perfectly flat pure chroma-key green (#00FF00) background with no shadows; the green is only a keying backdrop, not part of the palette. |
| S030_L1 | RH_image2 | 纯文生图 | Background plate only, no characters. Night sky, a gigantic blood-red full moon in upper center, white sky around it with screentone dots, distant black mountain silhouettes at the bottom. |
| S030_L2 | RH_image2 | 纯文生图 | Element only: a long horizontal band of drifting manga-style clouds in black ink and white with screentone shading. Isolated on a perfectly flat pure chroma-key green (#00FF00) background with no shadows; the green is only a keying backdrop, not part of the palette. |
| S030_L3 | RH_image2 | 定妆照参考 | Full-body long shot of Gui Tu (keep exactly the face, hair and costume of the reference model sheet) standing, raising his long straight sword high with one arm, sword tip pointing at the sky, ponytail and red sash flowing, seen from a slightly low angle. Isolated on a perfectly flat pure chroma-key green (#00FF00) background with no shadows; the green is only a keying backdrop, not part of the palette. |
| S030_L4 | RH_image2 | 纯文生图 | Foreground element only: black jagged rocks and wild grass silhouettes along the bottom edge, drawn in bold black ink. Isolated on a perfectly flat pure chroma-key green (#00FF00) background with no shadows; the green is only a keying backdrop, not part of the palette. |

### 已知生图问题
- S030_L2 云带自己画了一个红月（与背景月重复），已手工抹掉，留淡弧线；下次 Scene 加 `no moon, no sun`。
- S029_L1 背景模型自加城楼，过繁；下次加 `no buildings`。
- 路线 1 需要的精灵（按 chorus1_sprites 现有姿势）：S028 刀身横陈（与现版刀身同角度：左低右高约 -3°）、S029 grip（握刀手 + 半脸）、S030 ready（垂刀仰望）/ raise（举刀指月）——都要绿幕单体；背景：S028 暗底血墨晕、S029 夜空虚焦月、S030 血月夜空 + 远山 + 山脊。

## 六、工具与命令
- 出图：`PYTHONPATH=/workspace/work/.pydeps python3 tools/nb.py gen '{"model":"RH_image2","prompt":"...","ratio":"16:9","size":"2K"}' <outdir>`；nb.py 已对 5xx/非 JSON 自动重试（站点 04:30–04:40 频繁 502）。批量脚本样例 `/tmp/lay.py`（沙箱临时，逻辑：并发 5、每张最多 3 次、已存在跳过）。
- 凭据：保险库 nananobanana（尾号 JTFU）、wentoken；不要复述明文。用户 04:17 在聊天里贴过 wentoken key，已建议轮换。
- 定妆照：`assets/gen/R8_D/guitu_sheet.png`。分层产物：`assets/gen/R8_D/layers/`。
- Remotion 渲染：`cd remotion_test && npx remotion render src/index.ts R8-S028-030 out.mp4 --gl=swangle --concurrency=2 --crf=16`。

## 七、下一步
1. 用户确认走路线 1 → 生成第五节列出的 D 风格精灵与背景 → `STYLE_D=1` 改造 S028–S030 → 渲 1779–1868 → 与现版同段对比交付。
2. 试做通过再按段（副歌一 S027–S048 → 全片 138 镜）铺开，提示词按本文件模板逐镜写进 `jobs/r8_D_<段>.json`。
3. 第六轮遗留 10 项待用户拍板（见项目技能）。

## 路线 1 试做（11-11 05:01，已交）
- 开关 `STYLE_D=1`（配合 SPRITE_MODE=1）：`units/chorus1_sprites.py` 新增 S028D/S029D/S030D，只换素材（assets/gen/R8_D/route1/）与调色；`chorus1.py` EXPO_ALL→1.0、S028/S029 前景余烬改灰烬；`c1kit.finish` 去冷蓝 mono 偏色。
- S028 去掉巨字「血」，血滴改墨线描边；火星改白 + 血红。
- 渲染：`python3 tools/r8_route1.py 1779 1869 out.mp4`（单帧 `still <f> out.png`），90 帧约 2 分钟。
- 成果：crew/round8/S028-030_风格D_现管线.mp4、..._对比.mp4。

## 结论（11-11 05:03 用户通过）
- 用户：「可以的，很棒，我很喜欢」。**路线 1 定稿**：现管线 + STYLE_D，路线 2（Remotion）不再推进，无需商用许可。
- 试做提交 f1838a1；成片 crew/round8/S028-030_风格D_现管线.mp4，对比 ..._对比.mp4。
- 素材：route1/ 下 D028_bg、D028_blade(_cut)、D029_bg、D030_ready(_cut) 为新生图；D029_grip_cut、D030_raise_cut、D030_bg 拷自 layers/（S029_L2_cut、S030_L3_cut、S030_L1）。提示词 jobs/r8_D_route1_sprites.json。
- 小瑕疵（已问用户，未答）：S029 新图看不到刀身，现版能看到；如需，重生一张「握刀手 + 半脸 + 刀身斜出画」。

## 铺开全片的做法（下一步，待用户说开工）
1. 按段：副歌一其余镜（S031–S048）→ 主歌/前奏（sections/sec_*.py）→ 后段。每段先列「镜号 → 需要的精灵/背景」表。
2. 每张图用风格 D 模板（头段 + Scene + 尾段 + Reminder），人物加定妆照参考；单体一律纯绿幕 + cutout_green；背景加 no moon/no sun/no buildings 视需要。
3. 代码只加 `*D` 子类换素材，grade=NEU、rim=NORIM、wrap=0、shade=None；切点/运镜/特效不动；去掉所有字体叠加的巨字，画进场景的字保留。
4. 每段渲完与第六轮同段左右对比交用户；全片通过后走 r6 出片流程（底层块 → 字幕 → 拼接音轨 → ffprobe → 联系表）。
5. 预算：每段约 30–40 张图（RH_image2 3 积分/张）；90 帧渲染约 2 分钟。
