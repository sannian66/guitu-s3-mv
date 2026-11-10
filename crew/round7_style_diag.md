# 第七轮：风格诊断（2026-11-11，用户反馈「生图不好看、整体风格跳跃」）
逐镜联系表：out/round7/逐镜联系表_1/2.jpg（每镜中点一帧）
## 跳跃来源
1. 画法打架：主体是写实 CG（油亮皮肤、精修脸，S015/S028/S043/S121），桥段 S094–S100/S107 是白宣平涂水墨，S100 红线描、S020/S061 黄卷轴。
2. 主角脸不统一：S004/S015/S027/S081/S121 像不同的人。
3. 字体三套：毛笔字、宋体、金色斜面 3D 字（S114/S132）。
4. 色调三段：冷灰雨夜 → 白宣 → 金色夕阳（S111 起），交界无过渡。
## 生图观感问题
AI 味：皮肤过光、对比塑料、背景糊；缺水墨笔触与纸纹。
## 拟定方案（待用户定调）
- 定一张风格母版 + 主角定妆照，用 Nano Banana 按参考图逐张重绘生图素材（保留构图，换笔触与脸）。
- 全片统一调色 + 纸纹颗粒；字体统一毛笔/宋体，去 3D 金字。
- 色彩弧线可保留（冷→白→金），但金色降饱和、加墨质感，让三段像一个人画的。
- 先 4 镜试做（S015、S043、S096、S121）前后对比。

## 4 镜试做（11-11 03:57）
用户要求加入红色 → 定调：黑墨 + 宣纸白 + 朱红（唯一彩色），尾段金色夕阳改朱红日轮。
母版 assets/gen/R7_style/S043_master.png；S015/S096/S121 以「原帧 + 母版」双参考重绘（gpt-image-2 edits，api.wentoken.si，每张约 45s）。对比 crew/round7_style_test.jpg。jobs/r7_*.json。

## 风格 B + 分层 3D 试做（11-11 04:05）
- 用户给参考图（assets/ref_user/style_B_manga_red.png）：漫画钢笔排线 + 大块平涂朱红。B 版 4 镜 assets/gen/R7_styleB/，A/B 对比 crew/round7_styleAB.jpg。
- S121 分层：天空红日 / 墨云带 / 鬼屠 MCU / 前景红绸，A 版 assets/gen/R7_layersA，B 版 R7_layersB（绿幕生图 + tools/cutout_green.py）。
- Remotion：remotion_test/src/S121Layers.tsx，平面按深度 z=-32/-13/0/4.2 摆放，ShaderMaterial 做云/绸飘动，机位推近 + 横移环绕 + 手持噪声。35 帧约 40s（swangle）。对比 out/round7/S121_分层3D对比.mp4（不入库）。
- 已知：前景红绸层跑出画外，待调位置。

## 风格 C（11-11 04:10）
用户给 3 张丝网版画海报参考（assets/ref_user/style_C_print_1..3.png）：米白纸、黑、朱橙红、群青蓝四色平涂 + 套色偏移颗粒。4 镜 assets/gen/R7_styleC/，A/B/C 对比 crew/round7_styleABC.jpg。脸偏 80 年代动画，略离母版。
风格 C 重做（04:15）：风格图排前、去母版、原帧只管构图；gpt-image-2 与 2.5-flare 各一版（assets/gen/R7_styleC2/，对比 crew/round7_styleC_redo.jpg）。明显更接近参考的大色块剪影；教训：参考图顺序决定画风权重，风格图须排第一、角色母版会把画风拉回漫画。
