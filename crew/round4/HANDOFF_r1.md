# 第一棒交接（09:10 CST，各组第一棒子代理到时停下的自述）
所有组：代码初稿都已由总导演按路径提交；**都还没出联系表/关键帧，也没送评审**。
共同坑：tools/sec_contact.py 按 shots.json 旧镜头取帧，和各组新切点对不上 → 各组用自己的联系表脚本（按自己的 SHOTS/CUT 表逐镜取中点帧）。git 提交身份用 GIT_AUTHOR_*/GIT_COMMITTER_* 环境变量（sannian66 / 38859572+sannian66@users.noreply.github.com）。

## A 组（29 镜，平均 1.52s，积分 18）
- 未完成：渲 23–44s 检查最后一轮修改（重写的 V10 秤盘墨滴、V17 巨印仰视→落地印痕）并修报错；1–22s 修改后未复看。
- tools/a_contact.py 出 A_contact_v1 / A_keys_v1，自查两轮；写 A_storyboard.md（设计在代码注释里）+ 接缝。
- 已知弱点：A08 城墙太简单、V13 跪地人物一团剪影、多处月亮过曝、A01 署名 1.2s 时未显全。blade_face 精灵未用。
- 出口 1321：斩线渗墨压成墨色留朱缝，给 B 组「墨渗成纸」。

## B 组（预副歌一 14 镜 ~1.09s；主歌二计划 25 镜 ~1.26s；积分 18）
- B_storyboard.md 已有（含接缝）。units/b_kit.py、sec_b_pre1.py、tools/b_frames.py 已提交。
- sec_b_pre1：44.1–51.2s 8 帧渲过未看；51.85–59.30s 6 镜从未渲过。59.30s（帧 1779）起调用副歌一 Chorus1().frame()。
- **sec_b_verse2.py 一行没写**：按分镜第 2 节 25 镜；帧 2586 复刻副歌一 S047 墨退（ink_blot seed=47，中心 (960,600)，起点 86.133s）。
- 抠图遗留：竖刀当面、背影、横斩发丝轻微灰边（assets/gen/B_r4/*_cutd.png，tools/b_defringe.py），合成时冷色轮廓光压住。
- b_hitmap 画图步骤报错没出 png，json 完整。

## C 组（41 镜 ~1.06s，积分 24）
- sec_c_pre2_chorus2.py + c_kit.py 一帧未渲。
- 先把 ../c_cands/blade_hot_try1_0.png、blade_level_try1_0.png（在 /workspace/projects/614ceffe-275f-4d89-90f0-6cbd68b8bafd/work/c_cands/）缩放放入 assets/gen/C/，recut_flat 抠图（C11、C12、C38 依赖）。
- 可能报错的推测接口：crowd.Army()/soldier_sprite 返回格式（C18、C19）、fx2.heat_haze、GiantSeal split 参数、PR.CharWall collapse 参数。
- 写 tools/c_contact.py、C_storyboard.md（含 CUT_T 和接缝：入口 3534 硬切「谁」字进烛光剧本；出口 4839「答」金闪后定格故障、最后 4 帧切黑）。
- S062 精灵用了 3 次（C02、C03、C31），超限：C03 改纯代码手影。C18 军阵、C40/C41 天平、C06 暗箱、C23 字砖是代码道具，有被评「矢量占位」的风险，要做精。

## D 组（30 镜 ~1.06s，积分 24）
- sec_d_bridge.py + d_kit.py 只试渲 161.9/163.5/164.5s 三帧（能跑，未看）。S04–S30 从未跑过；sprite 绘制参数 mblur/rotblur/look/breathe 未核对。
- 摆位数字（笔尖、刀尖、同伴裁切、「忍」点位置）是估的；eyes_closed 顶边要在 y=120 以上。
- 写 D 联系表脚本、D_contact_v1 / D_keys_v1、D_storyboard.md（接缝：4839 自黑场进；5797 金白出，接 E 组白闪）。
- 风险：S06 天平、风暴天空全程序化可能「代码味」；S19 刀身刻字和副歌一 S046 撞概念；S099/point_up 用 2 次须处理不同。

## E 组（36 镜：副歌终 26 镜 ~1.08s、尾奏 10 镜 ~2.0s；积分 27）
- units/e_kit.py 已推送；sec_e_final_outro.py 从未运行。
- 已知 bug：E30 残留无用循环；E14T、E22 未用变量和每帧重建对象；E15 刀尖、E22 刀身裁切比例和锚点是估的。单帧压到 ~3s 内。
- 写 E_storyboard.md + 接缝（5797 自带金白闪入；7174 起收墨成一点朱红再落纯黑，这段不加颗粒暗角）；E 联系表脚本、E_contact_v1 / E_keys_v1。
- 风险：太上皇纸糊（look='paper' + 程序竹骨）质感待验；E12 俯拍小人和刀约 20px 代码图形可能被评占位；署名竖排沿用 credit_block 未看效果。
