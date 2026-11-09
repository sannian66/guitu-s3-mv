
## C 组（第二棒，09:25–10:00 CST）
- **做了什么**：重下 blade_hot / blade_level（未重生成，0 积分）→ assets/gen/C/ 抠图；41 镜逐镜跑通（修 C01 透视 dtype、C18 Army.draw 返回 (fr,info)，heat_haze / GiantSeal / CharWall 接口实测可用）；单帧 0.3–2.8s。
- 新建 units/c_props.py（只给 C 组用，不改共享库）：墨玉巨印 StoneSeal（透视立方体贴石纹、朱砂阳文底面、金填阴刻、可斩开+碎石）、漆金暗箱 LacquerBox、青铜天平 BronzeBalance（圆柱着色+铜绿+碗形秤盘+斩断）、通用 Cuboid（C23 立体字砖、C10 立体铅活字）。
- 重做：C03 纯代码手影+十字提线板（S062 降到 2 次：C02、C31）；C04/C40/C41 天平；C05/C06 暗箱；C10、C13（风暴之眼漩涡+光速雨线）、C19（甲士轮廓光剪影+切口）、C23、C27、C28（「亮」墨边金芯可读）、C32–C35 巨印、C36（跪伏方阵，呼应 C18 冲锋）。转场去白闪化（C14/C27 smoke_through、C20 ink_bleed、C36 flash_red 1 帧）。
- **积分**：本棒 0；本组累计 24 / 80。
- **联系表**：out/round4/C_contact_v1.jpg（跑通后原样）、out/round4/C_contact_v2.jpg（道具重做后）、out/round4/C_keys_v1.jpg（40 个切点帧 + 23 个歌词关键帧，转场改动前渲；改后 4 处单独抽查过）。脚本 tools/c_contact.py。分镜 crew/round4/C_storyboard.md。
- **自评弱点**：C18/C19/C36 程序化甲士仍可能被评代码味；C41 巨型秤盘口沿偏薄像环；C32 奔跑小人小且糊；C02 提线挂字偏空、手被画顶裁；全程只看了静帧抽样，没出动态预览。
- **下一步**：出 C_contact_v3 / C_keys_v2（含转场改动）；C02 加密构图；C41 秤盘加厚、加盘内侧纹样；出 1–2 段 mp4 预览验证镜内运动与卡点；送评审。

## E 组第二棒（10:05 CST）
- **做了什么**：sec_e_final_outro 36 镜全部跑通（修 E30 ValueError）；稳态单帧 0.4–1.4s，冷启动 ≤2.7s，转场帧 ≤3.4s（E09 paper_tear）。修云层平移 bug（`-ox % W` 优先级，E03/E29/E30/E33 云海原本几乎不显示且右缘硬边）→ cloud_blit。E15 刀尖、E22 刀身行改为精灵 alpha 自动标定（火线头=刀尖；日心=刀身中点，「我来量」刻刀）。E12 换新生真俯视精灵（人+插地刀）+长影；E07 帘后剪影→新生太上皇纸扎精灵揭示，E08 纸纹改皱纸+歪竹篾+接缝。E23 径向速度线；E32/E35 裁切避脸；E14T/E24/E25/E26 字避人；E27/E34 人物放大；E31 冷调晨雾去重复；E18 定格缓存、E22 Lyr 缓存、删未用变量。
- **积分**：本棒 6（E12 top_down 395c4836、太上皇 paper_effigy 599266ee，均采用），E 组累计 **33/80**。
- **联系表**：out/round4/E_contact_v1.jpg、E_keys_v1.jpg、E_contact_v2.jpg、E_keys_v2.jpg（脚本 tools/e_contact.py；提交脚本 tools/e_commit.sh）。分镜：crew/round4/E_storyboard.md（含接缝、未决）。
- **自评弱点**：E10/E34 zoom_through 峰值近乎白屏；E16/E17 分屏互切中间帧乱；E26「正道沧桑」金字在亮天上对比偏低；尾奏 E31/E33/E34 仍是程序天空+山脊为主，精致度低于人物镜；E03 云海偏灰糊；credit_block 拉丁名 Cait 竖排被旋转；只看了中点帧和转场中间帧，未逐帧看运动连续性。
- **下一步**：做一段 mp4 预览（cpu_slot）看运动；E26 字加暗衬/描边；E10/E34 换转场；尾奏署名镜考虑再生 1–2 张人物精灵（远景行走换姿势）替代程序天空。

## D 组（Bridge d_bridge，帧 4839–5797，30 镜，平均 1.06s）— 第二棒 10:05 CST
- **做了什么**：30 镜逐镜跑通（修 S27 `_slash_streak` 方向、`fall_chars` 颜色元组两处报错），单帧 1.2–3.8s（转场叠帧最高 5.6s）。重写 d_kit.storm（三层云+银边光+自阴影+风带，去旋转滤镜味、修接缝）与 lightning（分形）。S05「忍」点位按字形自动定位 + 朱滴匹配到 S06 左盘；S06 天平写意化；S09 巨笔只留手+笔杆；S12 换新精灵 blade_up_cu（point_up 原第 3 次使用超限）；companions 原抠图只剩 1 人 → tools/d_recut.py 多连通域重抠成四人剪纸；S16 余烬改飞向 S17 瞳孔；S19 改为火星在空中写「主张」（避开副歌一 S046 刀身刻字）；S20 仰拍透视字墙 + 新精灵 wall_stand_back；S28 换暗底；若干顶头/压字/过曝修正。
- **积分**：本棒 6 点（blade_up_cu、wall_stand_back 各 3，RH_image2 4K，均已 quote、记 genlog），D 组累计 30/80。
- **联系表**：out/round4/D_contact_v3.jpg（v1、v2 留档）；关键帧 out/round4/D_keys_v1.jpg；分镜 crew/round4/D_storyboard.md（含接缝、未决）；脚本 tools/d_contact.py。
- **接缝**：4839 自黑场 0.18s 渐入；5797 前 0.5s 金白拉满，接 E 组白闪。
- **自评弱点**：风暴底仍占 10 镜（已变中心/亮度/色温）；S21 侧墙、S22「闯」碎片偏平；S16/S23/S29/S30 转场中点静帧近乎纯暗/纯白；S11 水墨脸上红唇略像妆；未出动态片段验证运动。
- **下一步**：出 2–3 段 mp4 片段看运动和卡点；S21/S22 碎片加厚度/石质；再拆 1–2 镜风暴底（如 S29 改雨中地面反打）；送评审。

## B 组（第二棒，09:25–10:00 CST）
**做了什么**
- `units/sec_b_pre1.py`：14 镜全部单帧跑通（含 51.85–59.30s 6 镜）。修 P10 铅字盘越界（canvas 2600→2800 报错）、铅字字形居中裁切（原取左上角，字被裁坏）、P01 太上皇执笔手精灵四边渐隐 + 字后合成（原来手挡字、生图边框成硬边）、P03 纸人放大、P07/P09「不」改志莽行书（流江毛草形似「ふ」）。
- `units/sec_b_verse2.py`：从零写完 25 镜（V01–V25，CUT_T 按 align.json 字头修正，平均 1.26s），READY=False，单帧 0.4–2.3s。帧 2586 复刻副歌一 S047 墨退（ink_blot seed=47、中心 (960,600)、起点 86.192、同墨色），并在 2586–2595 把副歌一 S047 原帧与 V01 做雨痕溶解，接缝连续。
- 转场 14 种：zoom_through、flash_white、gold、occlusion、match_cut×3、whip_pan_blur×4、slash_wipe×2、flash_red、ink_bleed、glitch_cut、smoke_through、flash、连续机位、hard（带推近/提亮冲击）。
- 去灰边：`units/b_kit.py` 新增 `defringe()`（边带色彩去污染 + alpha 收紧），`spr()` 对所有 B 组精灵自动做，并改为独立实例；新增 `spr_feather()`（满幅特写精灵边缘渐隐）。只改了 B 组自己的 b_kit，没动共享库。
- `units/b_hitmap_pre1.py` / `b_hitmap_verse2.py` 画图报错修好（画图窗口原来写死成副歌一 58–90s，超出本段分析窗；音频回退 audio/谁定正邪.mp3），出 `crew/round4/B_hitmap_pre1.png`、`B_hitmap_verse2.png`；json 重跑逐条一致。
- 联系表脚本 `tools/b_contact.py`（按本组 SHOTS/CUT 逐镜中点帧；keys = 每个非硬切切点 +2 帧 + 18 张歌词关键帧；分块渲染，缓存放 workspace——/tmp 在不同 shell 调用间不共享，v1 曾因此缺帧）。
- `crew/round4/B_storyboard.md` 追加第 6 节（切点修正、逐镜实现差异、接缝更新、未决）。
**积分**：本棒 0（没有生新图），累计 18 / 80。
**联系表**：`out/round4/B_contact_v2.jpg`（39 镜）、`out/round4/B_keys_v2.jpg`（48 张）；v1 同名 _v1。
**自评弱点**
- 代码道具味：V09 天平（props 线稿加粗）、V10 刻度盘、V02 雨滴内城墙偏平；与 C 组 C40/C41 天平同概念。
- 纸人（P03/P04、V03、V12）仍是「纸扎道具」造型，V12 坠落纸人太小太平。
- V15 雨中行走人物在闪电前偏暗偏小；V24 刀痕透视还像一根发光棍；V20/V21 倒影里字和人物有重叠。
- P11 铅字镜画面信息量少；P05/P06 砖墙与副歌一砖墙母题接近。
- 只看过单帧和联系表，没出动态预览；镜内运动、转场时长未在动态里验证。
**下一步**：出 pre1/verse2 低清 mp4 预览查运动与卡点 → 重做 V09/V24/V12 → 送评审。
