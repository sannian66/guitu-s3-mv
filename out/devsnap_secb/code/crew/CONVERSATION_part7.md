# 《谁定正邪》MV 沟通记录

用户与 Hark（制片/总导演）的对话，自动从会话导出。最早一条用户消息内含与上一任 agent 的对话记录。

### 用户 · 2026-11-08T17:29:11Z

接手任务，这是我跟上一个agent的对话记录，你注意，在你额度耗尽之前，一定要上传所有文件，包括做了部分的内容。

有点水啊
我也觉得水：镜头一拖 4 到 8 秒、几乎不动，刀客是静止剪影，三段副歌反复用同一组画面。我想先把副歌一（59–89 秒）重做成样片：按小节快切、镜头推拉甩震、刀客挥刀、歌词一笔一笔写出来。你最嫌的是节奏慢、画面简单，还是重复多？

这就是你的全部能力了吗，我希望能像剧组一样开工，独立上下文，多个子代理。节奏慢、画面简单，重复多，我都嫌弃，而且画面不够精致，分镜不够有设计感，转场也没有，歌词文字排版简单，缺点太多了。
反正不限你能力，能做到最好就行。一定是获奖级别的商业交付作品。
收到，按剧组开工。第一阶段三个独立子代理已经并行开工：导演组画全片逐镜分镜、角色组做会动的刀客和布料特效、字幕转场组做笔画书写和转场库。之后各段摄制组并行拍，最后剪辑质检。你嫌的七点都写进了硬性标准。

导演组交稿了：全片 138 镜，副歌平均 1.2–1.4 秒一切，切点几乎都压在鼓点上。三段副歌同词不同画：月夜「立」、雷暴「破」、破晓「定」，最后太阳从鬼屠的刀线上升起。新需求已转给角色组和字幕组。

字幕转场组交件：逐笔书写、满屏字矩阵、字砸下炸开重组、字砖墙被一刀斩裂崩塌、宋体形变成行书、刀光刻字等 40 多种排版，加 17 种转场和运镜工具，单帧最慢 0.27 秒。等角色组的刀客到位就开拍。

记得全部上传代码哈，做到一半的也要传
已传：剧组总纲、138 镜分镜、字幕转场库、做到一半的角色库和测试图都推到仓库了（提交 ea0207f）。之后每个组交件就同步一次，音视频文件照旧不入库。

剧组第一阶段完成大半，还没开拍。导演组和字幕转场组都已交件，角色组只做完鬼屠、太上皇和特写，军阵、道具、雨光特效还没做。角色库最新一版尚未推到 GitHub，接着做时会先同步。要我继续吗？

谁定正邪 MV 剧组进度
组
状态
产出
剩余
导演分镜
完成
138 镜，副歌 1.2–1.4 秒一切
无
字幕转场
完成
40 多种排版，17 种转场
闪电刻字改回金白色
角色美术
做了一半
鬼屠 19 个动作、刀光、特写、太上皇
军阵、纸人、道具、雨光特效
分段摄制
未开始
无
先拍副歌一样片 59–89s
剪辑质检
未开始
无
成片渲染与交付
接下来先补完角色库，再出副歌一样片给你看，你点头后再铺开到全片。

### Hark · 2026-11-08T17:30:59Z

接手了，从仓库 ea0207f 续做（前任没推送的那版角色库已经找不回，按仓库版本接着补）。现在两个组并行：角色组补军阵、纸人、道具和雨光特效，副歌一摄制组开拍 59–89 秒样片。两组都要求至少每 20 分钟推一次，半成品也推。

### 用户 · 2026-11-08T17:31:34Z

歌词和歌曲文件是不是没入库？

### Hark · 2026-11-08T17:31:41Z

歌词入库了，歌曲没进这个库。MV 代码库 guitu-s3-mv 是公开的，里面有歌词和逐字对齐数据，但 mp3 被刻意排除了。歌曲原件和歌词原文都在你的私有库 shui-ding-zheng-xie-op 里，我渲染时就是从那儿取的。要我把歌曲也放进 MV 库吗？那样会公开出去，除非先把库改成私有。

### 用户 · 2026-11-08T17:31:56Z

帮我入库
[file: 谁定正邪.mp3]
[file: 谁定正邪.txt]

### 用户 · 2026-11-08T17:32:11Z

不用私有，没事

### Hark · 2026-11-08T17:32:11Z

入库了：歌曲和歌词原文放在 MV 库的 audio 文件夹里，提交 6f54054。这个库是公开的，所以任何人都能下载这首歌。另外角色组也已经推了两次，闪电刻字已经改回金白色。

### Hark · 2026-11-08T17:32:15Z

好，就保持公开。副歌一样片出来我第一时间发你。

### 用户 · 2026-11-08T17:33:18Z

你能实时自动同步吗，你的产物文件，包括交接文档，readme等文件，我怕丢进度

### Hark · 2026-11-08T17:33:51Z

可以，已经开了：每 3 分钟自动把仓库里所有改动（包括半成品、交接文档、README）提交并推到 GitHub，只跳过超过 50MB 的视频。交接文档也刚更新到最新进度，提交 0497e84。

### 用户 · 2026-11-08T17:44:36Z

我问下，是用的什么技术栈

### Hark · 2026-11-08T17:44:47Z

纯 Python 程序化渲染：numpy 算画面和噪声（山、雾、雨、刀光），OpenCV 和 scipy 做变换、模糊、合成，PIL 用四款开源书法字体排歌词，角色是自写的 2D 骨骼动画。音频用 librosa 找鼓点，demucs 加 stable-ts 做逐字对齐，最后 ffmpeg 合成 H.264。没有任何 AI 生图。

### 用户 · 2026-11-08T17:45:12Z

没有其他技术能用了吗

### Hark · 2026-11-08T17:45:30Z

有。最值得加的是 Skia：矢量路径、抗锯齿、渐变更精致，刀客和笔触会明显更干净，速度也快。Blender 能做真 3D 布料和体积光，但这台机器没 GPU，全片渲染要十几个小时以上；GLSL 着色器同样吃 CPU。要我让角色组把绘制层换成 Skia吗？

### 用户 · 2026-11-08T17:47:09Z

可以，你为什么现在才决定呢，我的目的是做到最好。

### Hark · 2026-11-08T17:47:49Z

这是我的疏忽，接手时只顾着续上前任的管线，没先重新评估工具。Skia 已装好跑通，已交代角色组把刀客、刀光和各角色改成矢量绘制；副歌一组先把手上这版样片渲完，再换上 Skia 版重渲。

### 用户 · 2026-11-08T17:53:07Z

会是啥样子的啊，能给我看几个关键帧吗

### Hark · 2026-11-08T17:54:09Z

第一张是副歌一正在渲的 8 个镜头：热刀特写、月前红印「刀」、闪电裂墙、「天」字被一刀斩开。另两张是新做的军阵和雨光特效库。这还是换 Skia 前的版本，我自己看到的问题：砖墙太平淡，有一镜歌词顺序乱，结尾圈入镜头人太小，样片出来前会修。

### Hark · 2026-11-08T17:54:09Z

[file: sheet.jpg]

### Hark · 2026-11-08T17:54:09Z

[file: army_sheet.jpg]

### Hark · 2026-11-08T17:54:09Z

[file: fx2_sheet.jpg]

### Hark · 2026-11-08T18:02:54Z

副歌一样片出来了：31 秒 22 镜，每镜 0.9–1.9 秒压鼓点，每个切点都有转场，刀客助跑飞身斩、旋身划出光环。这版还没换 Skia，砖墙重复、手部特写偏粗、整体偏暗是下一轮要修的。你看完告诉我哪里不对，我并进下一轮改。

### Hark · 2026-11-08T18:02:54Z

[file: sample_chorus1.mp4]

### 用户 · 2026-11-08T18:04:03Z

挺好的，画面没问题了，但是运镜啊节奏啊卡点啊这些感觉还是不够。

### Hark · 2026-11-08T18:04:40Z

明白，这轮只抓运镜和卡点。先把底鼓、军鼓、镲片逐一标出来做卡点图，再给镜头上弹簧相机：每记底鼓推近震屏、加花处插 2–4 帧闪切、乐句末尾定格懋住，画面比声音早一帧。顺手修黑屏、偏暗和砖墙重复。

### Hark · 2026-11-08T18:14:36Z

角色库做完了，全部换成 Skia，已推到 6855b50：军阵、纸人和提线木偶、纸糊巨影烧穿、刀天平诏书印章字砖墙，都能动。对比图里头发和边缘光已不再锯齿。副歌一第二轮已切到这套新库，干脚影和黑箱之类几个道具留到拍对应段时补。

### Hark · 2026-11-08T18:14:36Z

[file: paper_sheet.jpg]

### Hark · 2026-11-08T18:14:36Z

[file: skia_cmp_swordsman.png]

### Hark · 2026-11-08T18:34:17Z

第二版出来了。把鼓轨拆出来标了 139 个击打，底鼓推近、军鼓反震、加花处插 13 处 2–3 帧闪切，平均 0.65 秒一个画面；两处鼓停用定格懋住再闪白爆出。第一版有几个字晚了快一秒，现在都压在字头上。这版节奏对了的话，我就按这套卡点和相机铺开全片？

### Hark · 2026-11-08T18:34:17Z

[file: sample_chorus1_v2.mp4]

### 用户 · 2026-11-08T18:35:35Z

跟随鼓点的画面震动稍微克制一下，有点多了，运镜再来点就行了

### Hark · 2026-11-08T18:36:04Z

收到。第三版去掉 hi-hat 碎抖，军鼓旋震减到三分之一，底鼓推近只留小节重拍和重音字，幅度减半；卡点和切点不动。每个镜头加一条主运镜，推轨、环绕、摇臂、跟拍、焦点转移，节奏改由运镜变速来带。

### 用户 · 2026-11-08T18:42:47Z

歌词文字排版还能优化吗

### 用户 · 2026-11-08T18:43:02Z

目前有点乱，文字风格也不统一

### Hark · 2026-11-08T18:43:35Z

能，已并进第三版一起改，定了统一规范：歌词只用一种书法字，每句至多一个超大主字；版位只留底部横排和右侧竖排，同屏只一句、不再散落；白字为主，每句最多一个朱红字；入场出场各一套。这套规范之后用到全片。

### 用户 · 2026-11-08T18:44:08Z

不要书法字，不好看我觉得，因为不好排版。

### Hark · 2026-11-08T18:44:27Z

好，书法字全部拿掉，歌词统一用思源宋体：主字用最粗的 Black，整句用半粗，小字用常规。入场也从逐笔书写换成更利落的刀光扫入和模糊到清晰，已交给第三版一起改。

### 用户 · 2026-11-08T18:44:28Z

或者你觉得好排版用书法字也可以的，反正要高审美哈

### Hark · 2026-11-08T18:44:41Z

我的判断：整句歌词还是用宋体，干净、好读、好排。书法只在「劈」「判」这种高潮当作图形大字用，最多两处，而且要和宋体版对比确实更好看才留。

### Hark · 2026-11-08T18:58:35Z

第三版好了。震动从 246 次减到 49 次，幅度只剩约十分之一；每镜一条主运镜，含两次希区柯克变焦、两次焦点转移。歌词全改思源宋体，同屏只一句；书法对比过，确实不如宋体 Black，没用。我看右侧竖排小了点，要加大吗？没问题就按这套铺开全片。

### Hark · 2026-11-08T18:58:35Z

[file: sample_chorus1_v3.mp4]

### 用户 · 2026-11-08T19:00:54Z

现在很棒了，人物模型能优化吗，对了，我们沟通的上下文也要同步到github哈

### Hark · 2026-11-08T19:01:41Z

沟通记录已同步到仓库 crew/CONVERSATION.md（含你贴的前任对话），之后每次自动同步都会更新。人物模型优化已开工：刀客比例和轮廓、衣摆飘带的物理摆动、成束的头发和光影，重点重做侧脸回头、握刀手和刀上的眼睛这几个特写，完了给你看前后对比。

### Hark · 2026-11-08T19:13:09Z

沟通记录已同步到仓库的 crew/CONVERSATION.md，每次自动推送都会更新。人物模型大概只做了四分之一：新的画法和光影层已写进代码，但我还没亲眼确认效果，也还没有前后对比图可以给你看。交接清单请看卡片。

### Hark · 2026-11-08T19:13:09Z

人物模型 v2 交接

**已完成**
- `lib/sk.py`：新增形状合并、布料网格渐变、形内绘制、粗细渐变的肢体等函数，原有接口不变。
- `lib/rig.py` v2：
  - 新增 `rig.set_quality('v1'|'v2')`，默认 v2。
  - 光影：主光、天光、遮挡、脚下渐暗，另加 `_form` 体积明暗。
- 刀客 v2（`_sw_draw2`）：
  - 身体与服饰：腰线、长靴、交领、腰封、分层衣摆、护腕、缠手布、刀鞘金具。
  - 挥刀拖影。
  - 3D 头型与五官，头发成束。
- 速度：每帧 0.17–0.26s，上限 0.6s。
- 测试工具都在 `lib/rig_test/`：
  - `rig_v1_baseline.py`、`crowd_v1_baseline.py`、`paper_v1_baseline.py`：改前的快照。
  - `v2_cmp.py`：生成前后对比图。
  - `v2_shots.py`：镜内抽帧。

**有待处理的问题**
- 两个角色组子代理曾同时改 `lib/rig.py`，里面可能有两处 `_composite` 定义互相覆盖，接手时要先理顺。
- v2 还没验证，画面可能偏暗，要调 `_comp2` 的亮度。验证前不要重渲副歌一；要稳妥就先用 `set_quality('v1')`。
- 自动同步循环大约 03:18 结束，之后的改动要手动跑 `./autosync.sh`。

**待做（按顺序）**
1. 亲眼检查 v2 刀客，并出对比图。
2. 侧脸与回头特写（S043）。目前脸只是一团，转头时会变成暗块。
3. 布料和飘带随动作调参；把预备、出刀、随势、收势的关键帧做得更有力。
4. 重画握刀手特写（S029、S044）。
5. 把刀上倒映的眼睛（S038）改成写实风格。它在 `units/chorus1.py` 的 `eye_layer` 里。
6. 太上皇、正面跪姿士兵（`crowd.py`）、纸人（`paper.py`）。
7. 镜内验证：用 `C1_RIG=live` 抽 S029、S035、S043、S044、S045，拼成 `v2_in_shots.jpg`。然后更新 `RIG_API.md`。
8. 在 `HANDOFF.md` 补上 v3 段落。
9. 用户确认后，按 v3 的规范铺开全片。
10. 三份超过 50MB 的母版不在仓库里。v3 母版已经作为附件发过了。

---

## 第三任接手（2026-11-09 03:20 起）

### 用户 · 2026-11-08T19:20:43Z

github仓库中有个项目，你接受过来接着做，

沟通记录已同步到仓库 crew/CONVERSATION.md（含你贴的前任对话），之后每次自动同步都会更新。人物模型优化已开工：刀客比例和轮廓、衣摆飘带的物理摆动、成束的头发和光影，重点重做侧脸回头、握刀手和刀上的眼睛这几个特写，完了给你看前后对比。

沟通记录已同步到仓库的 crew/CONVERSATION.md，每次自动推送都会更新。人物模型大概只做了四分之一：新的画法和光影层已写进代码，但我还没亲眼确认效果，也还没有前后对比图可以给你看。交接清单请看卡片。

摘要
人物模型 v2 交接
已完成

lib/sk.py：新增形状合并、布料网格渐变、形内绘制、粗细渐变的肢体等函数，原有接口不变。
lib/rig.py v2：
新增 rig.set_quality('v1'|'v2')，默认 v2。
光影：主光、天光、遮挡、脚下渐暗，另加 _form 体积明暗。
刀客 v2（_sw_draw2）：
身体与服饰：腰线、长靴、交领、腰封、分层衣摆、护腕、缠手布、刀鞘金具。
挥刀拖影。
3D 头型与五官，头发成束。
速度：每帧 0.17–0.26s，上限 0.6s。
测试工具都在 lib/rig_test/：
rig_v1_baseline.py、crowd_v1_baseline.py、paper_v1_baseline.py：改前的快照。
v2_cmp.py：生成前后对比图。
v2_shots.py：镜内抽帧。
有待处理的问题

两个角色组子代理曾同时改 lib/rig.py，里面可能有两处 _composite 定义互相覆盖，接手时要先理顺。
v2 还没验证，画面可能偏暗，要调 _comp2 的亮度。验证前不要重渲副歌一；要稳妥就先用 set_quality('v1')。
自动同步循环大约 03:18 结束，之后的改动要手动跑 ./autosync.sh。
待做（按顺序）

亲眼检查 v2 刀客，并出对比图。
侧脸与回头特写（S043）。目前脸只是一团，转头时会变成暗块。
布料和飘带随动作调参；把预备、出刀、随势、收势的关键帧做得更有力。
重画握刀手特写（S029、S044）。
把刀上倒映的眼睛（S038）改成写实风格。它在 units/chorus1.py 的 eye_layer 里。
太上皇、正面跪姿士兵（crowd.py）、纸人（paper.py）。
镜内验证：用 C1_RIG=live 抽 S029、S035、S043、S044、S045，拼成 v2_in_shots.jpg。然后更新 RIG_API.md。
在 HANDOFF.md 补上 v3 段落。
用户确认后，按 v3 的规范铺开全片。
三份超过 50MB 的母版不在仓库里。v3 母版已经作为附件发过了。

### Hark · 2026-11-08T19:21:19Z

接手了，仓库 guitu-s3-mv 已拉下来。先理顺 rig.py 里重复的 _composite，再亲眼跑 v2 刀客出前后对比图给你看。

### Hark · 2026-11-08T19:27:59Z

全身 v2 确实更好：有体积明暗，腰封、长靴、护腕都出来了。特写比 v1 倒退，偏暗，正面回头的脸被刘海压成黑块，眼神光还穿透头发。我加了肤色补光、调亮了整体，侧脸已能看出鼻唇。对比图和代码已推送。

### Hark · 2026-11-08T19:27:59Z

顺手修了一处隐患：同步脚本指向旧会话，再跑会把沟通记录清空，现在旧记录存档，新对话接在后面。重复的 _composite 是故意做的 v2 包装层，不冲突。下一步重做 S043 回头脸，接着是握刀手和刀上的眼睛，要按这个顺序继续吗？

### Hark · 2026-11-08T19:27:59Z

[file: v2_cmp_sw_cu.jpg]

### 用户 · 2026-11-08T19:34:35Z

如果调用生图是不是会更轻松？

### Hark · 2026-11-08T19:34:51Z

对单张特写来说会轻松很多，脸和手一次就能画得很像样。但它和你定的「纯代码、禁用 AI 生图」规则冲突。逐帧动画里，同一张脸、同一身衣服也很难保持一致，更跟不上骨架动作和鼓点。

### Hark · 2026-11-08T19:34:51Z

折中办法：让生图只出侧脸、回头、握刀手的参考图，画面里不放，我照着用代码画。这样规则不破，特写会进步得快得多。要这样做吗？

### 用户 · 2026-11-08T19:36:45Z

因为这个建模太差了，跟我想的不一样。安装这个技能吧，同时github也同步过去，cladue.md中也说明调用这个，生图用gpt image2 4k最便宜的模型，另外，角色用我给的资产图，保持五官发型一致性就行，穿搭等内容都可以改的。

请帮我安装 Nano Banana skill。

目标：让当前 AI Agent 通过指定域名创建图片、视频和音频，查询任务状态和结果，或在用户明确提供画布坐标时写回已有画布节点。

请创建或更新一个名为 nano-banana-skill 的 Skill，显示名称为 Nano Banana skill。配置要求：
- 域名: https://www.nananobanana.cn
- Base URL: https://www.nananobanana.cn
- Authorization: Bearer bsk__***已打码***
- 这是多租户 API：Skills Key 已绑定签发它的用户和租户，服务端会据此隔离模型、额度、渠道、任务和画布权限。Agent 不需要也不应询问或拼接租户 ID；不要查询租户管理后台端口、供应商地址或内部模型名。
- 控制面只调用 https://www.nananobanana.cn/api/skills/*；唯一例外是把本地文件 PUT 到 presign 返回的 upload_url。不要探测其他 API 路径。
- 安装后先调用 GET https://www.nananobanana.cn/api/skills/models，读取 image[]、video[]、audio[]、name、supportedModes、capability、entitlement、video[].modes、video[].detailUrl 和 video[].mediaInputReview（imageInputReview 仅供旧客户端兼容）；模型请求的 model 必须使用这里返回的 name（或服务端明确返回的 id），不要自行猜测 actualModel、供应商名或渠道名。
- 报价：按图片、视频、音频分别将完整生成请求 POST 到 https://www.nananobanana.cn/api/skills/images/quote、https://www.nananobanana.cn/api/skills/videos/quote、https://www.nananobanana.cn/api/skills/audio/quote。读取 billing.total_points；kind=prepaid 表示预扣、完成后可能按实际时长结算。报价不创建任务、不扣积分；配置可能变化，提交前重新查询。若返回 skills_quote_unavailable 或接口不可用，明确说明无法确认价格，不得把 pointsCost 或基础单价当成最终报价。

Seedance 参考素材必经流程（安装时必须完整保留，适用于 2.0、2.5 及历史兼容渠道）：
1. 用户的视频参数确定后，读取最新模式详情；本地图片、视频、音频先 presign + PUT，取得 upload.asset_url（HTTP 源地址）。已有可访问的 HTTPS 素材地址可用于首次审核；上传成功不等于审核通过。
2. 将源地址按原顺序放入 images、videos、audios，携带同一模式的完整请求 POST https://www.nananobanana.cn/api/skills/videos/review；三类参考素材都要审核，不能只审核图片。
3. 只有审核 HTTP 2xx、success=true、status=ready，且每个必审输入都返回 status=approved 和非空 asset_uri，才允许生成。assets.images/videos/audios[].source_url 是源地址；asset_uri 才是审核取得的 asset URL，通常为 asset://…，专用人脸渠道按 referenceScheme 返回 face:。不能把 upload.asset_url 当作已审核引用。
4. 将审核返回的 generation_request 原样 POST 到同域 generation_endpoint（/api/skills/videos/generate）；其中 images、videos、audios 已替换为审核引用，保持顺序、模型、模式和参数，不自行拼接 asset://，不换回 HTTP 源地址。收到生成 task_id 后才轮询任务。
5. 审核返回 HTTP 401/403、系统配置错误、拒绝、超时、非 ready 或缺少审核引用/generation_request 时，停止生成并报告实际错误；保留源地址用于按下文恢复，不能改走旧版直接生成来绕过审核。只有明确没有参考素材的纯文字生视频可跳过素材审核。

按请求类型调度：
- 已有视频工具：高清放大、深度提取、视频去字幕使用 POST https://www.nananobanana.cn/api/skills/videos/process，传 operation（upscale / depth / subtitle-erase）、video_url 和本次操作唯一的 idempotency_key；同一次操作重试必须复用此 key。高清放大可选 resolution=720p/1080p/2k/4k，缺省 1080p；其他两项使用租户已有工具配置。去字幕仅整段视频全局智能擦除（subtitle_all_area），不要传 mode、clips、detectRect 或其他选区参数。这三项不需要选择普通生视频模型或输出时长；服务端探测源视频时长并沿用工具栏计费。收到 task_id 后按下述规则轮询，完成前不得宣布成功。
- 视频参数先问清：用户未指定视频模型时，先展示 /api/skills/models 返回的可用视频模型并询问使用哪个模型，同时确认分辨率 resolution 和时长 duration（秒）。三项中任何一项缺失，都先询问缺失项并等待回答，再审核或提交生成；已明确的选项不重复询问，不擅自选择第一个模型或套用 example/default。选定模型后按最新模式 inputSchema 校验；固定值或自动时长（如 duration=-1）要说明含义并确认，不把 -1 当作负一秒，也不添加 Schema 不支持的字段。
- 文字生图：POST https://www.nananobanana.cn/api/skills/generate，只传 model 和 prompt，可选 ratio/size/space_type。
- 参考图生图：仍用 POST https://www.nananobanana.cn/api/skills/generate，把一个或多个 asset_url 放入 input；不要把本地路径或 upload_url 放进去。
- 视频调用详情：选定模型后读取 GET https://www.nananobanana.cn/api/skills/models/video/{modelName}，modelName 使用 models 返回的 name 并 URL 编码；优先直接使用 detailUrl。按 modes[].inputSchema、media、mediaInputReview、promptRequirement 和 example 构造请求；只选 available=true 的模式，未配置或不支持的模式不得猜测。每次新任务重新读取详情，租户配置变化以服务端最新校验为准。
- 文字生视频：POST https://www.nananobanana.cn/api/skills/videos/generate，传 model、prompt、mode 和该模式 inputSchema 允许的参数；duration、resolution、aspect_ratio 的范围按模式详情选择。video_mode 等旧别名仍兼容，新请求统一用 mode，不把通用 supportedModes 当作完整细分模式列表。
- 图片/视频/音频参考生视频：先 POST https://www.nananobanana.cn/api/skills/videos/review 审核，再 POST https://www.nananobanana.cn/api/skills/videos/generate。按模式详情使用 images/videos/audios 三个数组，审核成功后原样提交返回的 generation_request，其中必审素材已换成 asset://… 等审核引用。media_type 只用于上传元数据或旧版素材对象，绝不能加到生成请求顶层。
- 音色设计、声音克隆、TTS 语音合成：POST https://www.nananobanana.cn/api/skills/audio/generate；从 audio[] 选择 capability 分别为 voice_design、voice_clone、tts 的模型。模型的 capability 必须与请求 capability 完全一致。音色设计传 prompt + style，声音克隆传 prompt + reference_audio_url（或 reference_assets），TTS 二选一传 prompt + voice_id，或传 prompt + reference_audio_url；后者的 reference_audio_text 为非必传参数。不要同时传 voice_id 和 reference_audio_url。
- 生成响应中的 task_id 或 skill_task_id 用于 GET https://www.nananobanana.cn/api/skills/tasks/{task_id} 轮询，严格遵守下方“结果轮询”，向用户报告结果或错误。
- 只有用户明确给出 workflow_id 和 node_id 时，才在生成请求中附加 canvas_writeback；需要写回画布时也可调用 POST https://www.nananobanana.cn/api/skills/canvas/writeback 单独写回。

调用示例（所有 JSON 请求都带 Authorization: Bearer bsk__***已打码***）：
GET https://www.nananobanana.cn/api/skills/models
POST https://www.nananobanana.cn/api/skills/generate  {"model":"<image[].name>","prompt":"cinematic product image","ratio":"16:9","size":"2K"}
POST https://www.nananobanana.cn/api/skills/generate  {"model":"<image[].name>","prompt":"edit this reference","input":["<asset_url>"]}
POST https://www.nananobanana.cn/api/skills/videos/review  <使用所选模式详情的 example JSON，替换提示词和 images/videos/audios 中的上传 asset_url>
POST https://www.nananobanana.cn/api/skills/videos/generate  <原样提交审核响应的 generation_request；纯文字模式可直接提交详情 example>
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<voice_design model>","capability":"voice_design","prompt":"你好","style":"温暖、沉稳的青年女声"}
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<voice_clone model>","capability":"voice_clone","prompt":"你好","reference_audio_url":"<asset_url>"}
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<tts model>","capability":"tts","prompt":"你好","voice_id":"<voice-id>"}
GET https://www.nananobanana.cn/api/skills/tasks/{task_id}

结果轮询（图片、视频、音频共用，安装时必须保留这些规则）：
- 任务接口返回 {"success":true,"task":{"status":"completed","result_urls":["…"],"error":null}}。必须先取 task = response.task，再读取 task.status、task.result_urls 和 task.error；不能读取顶层 response.status，也不能把 success=true 当作生成完成。
- 每次循环向 stderr 打印 t=Ns status=xxx（N 为累计秒数）；未识别状态打印 status=unknown，请求错误或超时打印 status=_error。stdout 留给最终结果。
- 命中 completed 立即 return task 并报告 result_urls；命中 failed、cancelled、timeout 等终态立即 return 错误结果（带 _error 和原 task），不得再 sleep 或发起下一轮查询。
- 只有明确的 pending、queued、submitted、processing、running、settling 才是进行中。缺失、空值、unknown、其他未识别 status 或非 JSON 响应绝不能当作进行中：独立累计连续未识别次数，最多诊断重查 3 次（含首次）；第 3 次立即 return {_error:"unrecognized_task_status",task_id,response:<原始响应前 1000 字符>} 并报错退出。读到已识别状态才清零计数，不能兜底成 processing。
- 设置有限总超时和单次 HTTP 超时（例如总计 10 分钟、每次最多 30 秒、间隔 5 秒，单次请求/等待不得超出剩余总时限）。轮询超时必须显式 return {_error:"poll_timeout",task_id}，不能静默结束或当作成功；HTTP 错误、success=false 或网络错误立即返回 _error 并附错误信息。轮询失败不代表服务端任务已取消，保留任务 ID 供之后查询，不自动重新提交生成。下载包 examples/banana-skills-example.mjs 的 pollTask 实现这一契约；外部 Agent 自建轮询也必须遵守。

本地素材流程：先 POST https://www.nananobanana.cn/api/skills/uploads/presign（filename、content_type、size、media_type，支持 image/video/audio），从响应 upload 对象读取 upload_url、headers 和 asset_url；按返回 headers 将原始二进制字节 PUT 到 upload_url，确认 HTTP 2xx 后再使用 asset_url。PUT 不发 JSON、base64 或 multipart，不携带 Skills Authorization。上传只负责存储，不代表图片、视频或音频已过审。upload_url 只用于上传且会过期，不能把 upload_url 传给模型。图片生成和音频合成使用上传 asset_url；参考生视频将其送到 /videos/review。素材已经是 https CDN 地址时可直接使用它进行首次审核；格式不支持时仍需走下述重新上传流程。

视频渠道与素材审核：生成仍调用 https://www.nananobanana.cn/api/skills/videos/generate，由服务端按当前 Skills Key 所属租户和请求模型选择并锁定一个渠道，不会故障转移到其他渠道，过审失败或超时会停止视频提交。审核使用同域 POST https://www.nananobanana.cn/api/skills/videos/review，携带相同 Authorization，接收同一模式的完整请求 JSON（model、mode、prompt 和该 inputSchema 允许的参数/素材）。该接口只审核，不创建生视频任务、不返回 task_id。读取逐模式 mediaInputReview：requirement 表示审核义务，available 表示当前租户能否完成审核，endpoint 是受支持的审核地址，referenceScheme 是审核引用格式。imageInputReview 为旧字段；matchingChannels 为空时不要猜测或探测审核接口，也不能推断为免审。

Seedance 2.0、Seedance 2.5（含历史兼容渠道）的图片、视频和音频都必须在提交前完成审核；审核失败或超时不得提交生成。审核成功响应 status=ready，assets.images/videos/audios 中每项包含 source_url（原上传地址）、asset_uri（审核引用）、status=approved、expires_at。资产审核渠道返回如 asset://asset-20260821042413-7kxg7；仅专用人脸渠道按详情返回 face: 引用。不要拼接或伪造引用。将返回的 generation_request 原样 POST 到 generation_endpoint，必审的 images/videos/audios 已替换为审核引用，绝不换回原 HTTP 地址。审核配置缺失、不兼容或不支持该媒体类型时返回 skills_media_review_unavailable；纯文字请求无需素材审核。服务端保存审核记录，并在生成时校验审核引用的用户、租户、渠道、媒体类型、有效期和通过状态。超时使用同一原上传地址再次调用 /videos/review 继续查询；不存在 task_id 时不能轮询任务。引用失效时用 source_url 重新审核。旧版直接提交上传 URL 仅为服务端兼容行为，新安装的 Agent 必须执行上述先审核后生成流程，不能将旧路径作为审核失败的兜底。

格式不支持的恢复：skills_*_review_failed 且 reason=unsupported_media_format，或消息含 InvalidParameter.FormatUnsupported / Unsupported media format，表示格式或读取失败，不等同于内容审核拒绝。先拿原素材字节重新走 presign + PUT，按真实文件设置 MIME、扩展名和 size，只使用此次返回的新 asset_url 再调用 /videos/review；即使旧素材已经是 CDN 地址也执行此恢复，不重试旧 URL。如果新 URL 仍报格式不支持，检查实际编码/封装和上传响应，不能只凭 .mp4 后缀认定兼容；必要时另存为 H.264、yuv420p、AAC 的 MP4（faststart，不覆盖原文件），再上传新文件并审核一次。上传本身不会转码，转码也不保证供应商接受。仍失败则报告原始错误并停止；内容审核拒绝不得用重新上传或转码来绕过。仅在审核 ready 后生成，收到 task_id 后才开始任务轮询。

Seedance 六种模式以租户实际启用的为准：text2video（文字）、image2video_first（一张首帧）、image2video_first_last（依次首帧和尾帧）、multimodal_ref（图片/视频/音频参考）、video_edit（必须提供参考视频）、video_extend（必须提供参考视频）。Kling v3 Omni 与 RunningHub 的 first_last_frame、image_audio 等模式使用各自详情，不套用 Seedance 入参。先读 schema 再填写时长和比例：Seedance 2.5 编辑 duration=-1、aspect_ratio=adaptive；多模态参考的常规时长和比例按当前详情选择。

如果返回 invalid_skill_key 或 skill_key_revoked，请提示用户重置 Skills Key；model_package_required 请改用 models 返回的可用模型；审核错误按 reason、mediaType、assetIndex 和 recovery 区分上述格式恢复、审核处理中和内容拒绝。不要靠切换兼容字段或添加顶层 media_type 来重试同一失败素材。该安装提示适用于 Codex、Claude Code、WorkBuddy、OpenClaw、Hermes 以及其他支持 Skills 调用的智能体。

### Hark · 2026-11-08T19:40:58Z

装好了，已调通。生图默认用 RH_image2（全能图片G2），4K 每张 3 积分，官渠版要 18。CLAUDE.md、技能规则和调用脚本已推到 GitHub。仓库是公开的，所以 Key 只存在保险库，沟通记录里也自动打码了。

### Hark · 2026-11-08T19:40:58Z

仓库和之前的对话里都没找到角色资产图。把刀客等角色的图直接发我好吗？收到后我先出侧脸、回头、握刀手和刀上倒影的眼睛这几张定妆图，你确认后再放进镜头。

### 用户 · 2026-11-08T19:45:55Z

github也同步吧 这些资产
[file: 反派_柳传智.webp]
[file: 反派_周齐世.webp]
[file: 男2_影子.webp]
[file: 男主_鬼屠.webp]
[file: 男主师姐_丁昭.webp]
[file: 男主师兄_谢玄洲.webp]
[file: 男主徒弟_杨不丢.webp]
[file: 女主_殷若.webp]
[file: 最终boss_太上皇.webp]

### Hark · 2026-11-08T19:47:28Z

9 张角色资产已经同步到 GitHub 的 assets/characters。现在用鬼屠的设定图生成 4 张 4K 定妆特写：回头、握刀手、拇指推刀、刀上的眼睛，一共约 12 积分。

### Hark · 2026-11-08T19:51:37Z

9 张资产和 4 张 4K 定妆图都已推到 GitHub，一共花了 12 积分。脸和资产对得上。问题是高马尾大多看不出来；推刀那张拇指没顶在刀镔上；刀上那张拍成了人在刀后，不是刀面里的倒影。要不要我重生成这三张？

### Hark · 2026-11-08T19:51:37Z

[file: hero_cu_sheet.jpg]

### 用户 · 2026-11-08T19:55:29Z

这样生图能替代建模吗，我希望是能辅助你建模替换视频中的人物的。

### 用户 · 2026-11-08T19:55:48Z

我不太清楚这样的图你能怎样用到视频里面去

### Hark · 2026-11-08T19:57:35Z

单靠静态图不够，人会动不起来。但这个平台有「视频重绘」功能（Seedance 2.0 video_edit），正好能做你说的事：我用代码把动作、运镜、卡点渲成粗模，AI 照着设定图把里面的人换成鬼屠，动作保持不变。重绘 5 秒 1080p 约 204 积分。要不要先拿 S043 回头这一镜试一下？

### Hark · 2026-11-08T19:57:35Z

生图和视频重绘如何接入 MV

### 主线：代码出粗模，AI 换人
1. **代码渲粗模**：用现有的 rig 人物、场景和 vcam 运镜渲出每个人物镜头，卡点和动作时机都在这一步定死。**这一步不加字幕**。
2. **AI 重绘**：把粗模视频和角色设定图一起交给 Seedance 2.0 video_edit。它保留动作和运镜，把人重绘成设定里的五官和发型。
3. **回到管线**：重绘后的片段放回代码管线，再叠思源宋体歌词、转场、闪白和调色。字幕最后才加，是因为 AI 会把字画坏。

### 静态图的用处
- **定妆和风格锚点**：就是刚才那 4 张。重绘时一起传进去做参考，光影和色调更稳。
- **特写插镜直接用**：握刀手、刀上的眼睛这类短镜头。用代码加推拉、视差、雨丝和光效就能动起来，每张 3 积分，最省。
- **首帧生视频**：粗模镜头不好渲的时候，用定妆图当首帧直接生成动作。

### 成本参考（当前报价）
| 方式 | 价格 |
|---|---|
| 4K 静图（RH_image2） | 3 积分一张 |
| 视频重绘（Seedance 2.0 video_edit，1080p，5 秒） | 约 204 积分 |
| 参考生视频（Seedance 2.0，1080p，5 秒） | 约 170 积分 |

### 限制
- 平台的「一键换人」类模型（Wan2.2 换人）目前不开放 API 调用，所以走 Seedance 重绘。
- 重绘单段 4 到 15 秒，长镜头要分段。
- 每次重绘前，素材要先过平台审核。

### 用户 · 2026-11-08T20:02:51Z

我不认可这个方案，我更希望还是纯代码吧。如果生图不能辅助建模，就放弃。

### Hark · 2026-11-08T20:03:09Z

好，回到纯代码，重绘方案作废。图能帮上忙，但只当参考用，画面里不出现一个 AI 像素：从三视图量比例、取配色，把发型和五官轮廓描成矢量路径放进 rig，握刀、回头这些姿势也照着生成图来摆。先从鬼屠的脸和发型做起，行吗？

### 用户 · 2026-11-08T20:03:40Z

行，做吧，然后给到我几个对比图关键帧

### Hark · 2026-11-08T20:04:15Z

开工。照设定图测比例、取配色、描轮廓，把鬼屠的脸、高马尾和刘海重新写进 rig，顺手解决正面回头时脸被压成黑块的问题。之后出正面、侧脸、回头、全身四组新旧对比。

### Hark · 2026-11-08T20:29:48Z

4 组对比都是「旧 | 新 | 设定图」，已推到 GitHub。黑脸和眼神光透发解决了，中分刘海、剑眉、尖下巴、高马尾也都有了，渲染只慢了 5–14%。但离设定图还差得远：发丝太粗像脏辫，飞发像刺，脸偏灰。下一轮先把头发改成细丝成片，再把肤色提亮、琥珀瞳做出来，可以吗？

### Hark · 2026-11-08T20:29:48Z

[file: v3_face_cmp_front.jpg]

### Hark · 2026-11-08T20:29:48Z

[file: v3_face_cmp_turn3q.jpg]

### Hark · 2026-11-08T20:29:48Z

[file: v3_face_cmp_profile.jpg]

### Hark · 2026-11-08T20:29:48Z

[file: v3_face_cmp_full.jpg]

### 用户 · 2026-11-08T20:37:47Z

继续吧，一次性做到位

### Hark · 2026-11-08T20:38:18Z

这一轮把剩下的问题一次全改完：细发丝成片、弧形飞发、马尾垂到腰下、侧脸露出颚骨、冷白肤色加体积明暗、琥珀瞳。副歌一也会抽两帧重渲，最后一起给你对比图。

### 用户 · 2026-11-08T20:59:54Z

设置自动推送吧，我怕丢失进度

### Hark · 2026-11-08T21:00:32Z

设好了，每 30 分钟自动推一次 GitHub，半成品也推，第一次在 05:30。这是当前套餐允许的最短间隔。刚才也手动推了一次（cc5cc44），v4 做到一半的对比图已经在仓库里。推送失败才会告诉你，平时不打扰。

### Hark · 2026-11-08T21:02:51Z

v4 已推到 GitHub（db343d6）。发丝改成细丝成片，琥珀瞳和剑眉都出来了，马尾无风时垂过腰。副歌一 S043 的回头镜头改进最明显。还差的是：脸型仍偏几何、肤色偏灰，特写每帧慢了约 0.3 秒。下一步先把脸的轮廓做圆润、肤色调暖，还是直接用 v4 铺开全片？

### Hark · 2026-11-08T21:02:51Z

[file: v4_cmp_c1.jpg]

### Hark · 2026-11-08T21:02:51Z

[file: v4_cmp_front.jpg]

### Hark · 2026-11-08T21:02:51Z

[file: v4_cmp_profile.jpg]

### Hark · 2026-11-08T21:02:51Z

[file: v4_cmp_turn3q.jpg]

### Hark · 2026-11-08T21:02:51Z

[file: v4_cmp_calm.jpg]

### Hark · 2026-11-08T21:02:51Z

[file: v4_cmp_wind.jpg]

### 用户 · 2026-11-08T21:10:44Z

感觉模型还是很丑，如果你生图+扣图怎么样呢？

### 用户 · 2026-11-08T21:11:24Z

30分钟推送还是太保守了，如果你额度不足会断开的，想想办法

### Hark · 2026-11-08T21:12:16Z

改成了「提交即推送」：加了 git 钩子，每次 commit 立刻推到 GitHub。CLAUDE.md 也写死了：每改一段代码、出一张图、渲一段视频就同步，长任务每 5–10 分钟同步一次。这样就算中途断掉，最多丢最后一小步。每 30 分钟的定时任务留着兜底。

### Hark · 2026-11-08T21:12:47Z

这条路可行，脸会好看得多。代价是人物只能做 2.5D：推拉、风吹头发衣摆、呼吸，大动作得每个姿势生一张、按卡点切换，正好配 MV 的节奏。我拿 S043 回头镜头做一段实拍，生图约 9 积分，完成后给你视频和与 v4 的对比。

### Hark · 2026-11-08T21:24:11Z

S043 做好了，只用了 1 张图、3 积分，差距一眼就能看出来。发丝抠到单根，没有白边，月光轮廓和雨也跟场景对得上。不足是身体不动，只有头发飘，镜头长了会像定格。不过这一镜原本只有 0.9 秒，完全够用。要不要按这个改规则：特写、近景用生图抠图，远景和大动作用代码人物加刀光切镜？

### Hark · 2026-11-08T21:24:11Z

[file: S043_sprite.mp4]

### Hark · 2026-11-08T21:24:11Z

[file: sprite_vs_v4_S043.jpg]

### 用户 · 2026-11-08T21:25:00Z

这个好呀，继续做吧，方向对了，生图可以并发，抽卡效果不好可以重新抽。

### Hark · 2026-11-08T21:26:11Z

开两组并行做。一组把副歌一的人物镜头全部换成精灵，整段渲出来给你看，约 90 积分。另一组并发生成其余段落的人物素材，效果不好就重抽，约 150 积分。规则文档同步改成「人物生图抠图，其余代码」。

### 用户 · 2026-11-08T21:47:19Z

对了，还需要一个信息 后期总监：沉溺

### Hark · 2026-11-08T21:48:43Z

已加上「后期总监 沉溺」。片头放在音乐之后的下一小节，11.52 秒出现，位置和音乐一致，正好在片名扫光期间；片尾字幕也补成了六行。附上片头、片尾各一张截帧，下次渲染全片就会生效。

### Hark · 2026-11-08T21:48:43Z

[file: cred_intro.jpg]

### Hark · 2026-11-08T21:48:43Z

[file: cred_outro.jpg]

### 用户 · 2026-11-08T21:52:16Z

鬼屠 · 第三季 为主标题，主题曲 谁定正邪 为副标题。后期总监跟出品人，不放在跟鬼屠 · 第三季、主题曲 谁定正邪 这里，放在前面去，前面不是还有其他信息吗，调整一下，总之我希望 鬼屠 · 第三季 这里干净一点

### Hark · 2026-11-08T21:54:10Z

已调整：主标题改为书法大字「鬼屠 · 第三季」，中间用一个朱红圆点隔开；副标题为「主题曲《谁定正邪》」。片名区只保留这两行和印章。后期总监和出品人一起出现，上下排列；为了让片名区更干净，音乐也提前到片名之前，和美术设计一起出现。片尾按同样的层级处理。

### Hark · 2026-11-08T21:54:10Z

[file: title_credits_v2.jpg]

### Hark · 2026-11-08T21:56:10Z

其余段落的人物素材已经做好：42 个镜头，46 个姿势，都已抠好图，用掉 150 积分。鬼屠和太上皇的脸、发型都和设定图一致。还差桥段的 5 个姿势，大约 15 积分。另有几张手部特写把脸也画进去了，合成时裁掉就行。副歌一的整段成片还在渲染。

### Hark · 2026-11-08T21:57:30Z

副歌一已整段换成生图人物，附上成片和每个镜头的截帧。这次 16 张图用了 48 积分，红领、红穗、血色都保留了。最弱的是 S045 转身，糊成一团。S037 远景里人太暗，几乎看不见。S039 走路的脚不动，像在滑行。下一步我打算补完桥段的 5 个姿势、重抽这几处，再把全片接上精灵后整片重渲，大约还要 40 到 60 积分。可以吗？

### Hark · 2026-11-08T21:57:30Z

[file: chorus1_sprite_crf23.mp4]

### Hark · 2026-11-08T21:57:30Z

[file: c1_sprite_contact.jpg]

### 用户 · 2026-11-08T21:59:35Z

可以的

### 用户 · 2026-11-08T22:00:05Z

你刚发给我的视频，我播放不了

### Hark · 2026-11-08T22:02:44Z

抱歉，上一个文件转码时损坏了。这一版是从母版重新导出的，导出后我完整解码检查过一遍，没有报错，应该能正常播放了。

### Hark · 2026-11-08T22:02:44Z

[file: chorus1_sprite_crf23.mp4]

### Hark · 2026-11-08T22:02:45Z

开始做全片：补桥段的 5 个姿势，重抽 7 个弱镜，然后把所有段落都接上精灵，再整片重渲。片头片尾按新的层级来。生图预算 60 积分，渲染比较慢，做完会把成片发给你。

---

## 第四任接手（2026-11-09 07:40 起）

### 用户 · 2026-11-08T23:40:39Z

github的项目，你接手，目前进度：

全片精灵版进度
已完成

新生成 12 张：桥段 S098、S099、S102、S103、S105；重抽 S045 背身旋转、S037、S062（只留手）、S120（刀插入土）、S084（后仰）、S073 背身、S018 回头
其余约 66 个镜头接入精灵：卡点硬切姿势，刀光对准刀尖，特写加前景，远景加脚下雾带
手部特写裁到只剩手（S015、S051、S056、S083、S135、S137）
副歌一：S037 提亮并放大，S045 去掉糊团
片头片尾署名保持在最上层，内容没动
根据第一版联系表做了修正：桥段整体提亮，S007、S014 提亮，S021 挪开竖排字，中近景人物缩小、不再顶头。修正后的效果还没复查
待做

复查全片联系表
整片渲染（约 1 到 1.5 小时）
混音后导出母版、网络版和 720p 预览版，逐个解码校验，确认没有损坏
更新 HANDOFF 第 17 节
要注意

只有副歌一是逐镜精修版，其余段落是旧场景加精灵，59.47 秒和 86.2 秒这两处画风会跳
目前最弱：S007、S098、S110、S062（手偏灰偏糊）、S056（拳头裁剪后发闷）
之前贴进对话的 Key 建议换一个新的

### Hark · 2026-11-08T23:43:24Z

接手了，仓库 guitu-s3-mv 已拉下来、环境装好。先出全片联系表复查修正效果，没问题就开始整片渲染。

### Hark · 2026-11-08T23:47:06Z

联系表复查过了：桥段提亮、S007/S014、S021 让字、中近景不顶头都已生效，没发现新问题，弱镜头还是那五个。整片渲染已经开跑。

### 用户 · 2026-11-08T23:56:46Z

记得自动github，保险起见，你不要口头承诺，因为额度不足你会强制休眠。

### Hark · 2026-11-08T23:57:37Z

已做成机制，不靠我记着：定时任务每 30 分钟自动推 GitHub，渲染停了就自动续跑（到 11 月 11 日 08:00）；当前渲染期间另有后台每 5 分钟同步一次。我休眠了它们也照跑。

### 用户 · 2026-11-09T00:25:11Z

进度如何

### Hark · 2026-11-09T00:25:39Z

整片渲染已完成 21/31 块（约到 168 秒），剩下大约 35–40 分钟，之后混音导出三个版本并逐个解码校验，再要 15 分钟左右。导出脚本已写好并推到 GitHub；分块视频按原 .gitignore 不入库，存在持久工作区，休眠也不会丢。

### 用户 · 2026-11-09T00:28:27Z

只有副歌一是逐镜精修版，其余段落是旧场景加精灵，59.47 秒和 86.2 秒这两处画风会跳，目前最弱：S007、S098、S110、S062（手偏灰偏糊）、S056（拳头裁剪后发闷）
这些问题解决了吗

### 用户 · 2026-11-09T00:28:35Z

请帮我安装 Nano Banana skill。

目标：让当前 AI Agent 通过指定域名创建图片、视频和音频，查询任务状态和结果，或在用户明确提供画布坐标时写回已有画布节点。

请创建或更新一个名为 nano-banana-skill 的 Skill，显示名称为 Nano Banana skill。配置要求：
- 域名: https://www.nananobanana.cn
- Base URL: https://www.nananobanana.cn
- Authorization: Bearer bsk__***已打码***
- 这是多租户 API：Skills Key 已绑定签发它的用户和租户，服务端会据此隔离模型、额度、渠道、任务和画布权限。Agent 不需要也不应询问或拼接租户 ID；不要查询租户管理后台端口、供应商地址或内部模型名。
- 控制面只调用 https://www.nananobanana.cn/api/skills/*；唯一例外是把本地文件 PUT 到 presign 返回的 upload_url。不要探测其他 API 路径。
- 安装后先调用 GET https://www.nananobanana.cn/api/skills/models，读取 image[]、video[]、audio[]、name、supportedModes、capability、entitlement、video[].modes、video[].detailUrl 和 video[].mediaInputReview（imageInputReview 仅供旧客户端兼容）；模型请求的 model 必须使用这里返回的 name（或服务端明确返回的 id），不要自行猜测 actualModel、供应商名或渠道名。
- 报价：按图片、视频、音频分别将完整生成请求 POST 到 https://www.nananobanana.cn/api/skills/images/quote、https://www.nananobanana.cn/api/skills/videos/quote、https://www.nananobanana.cn/api/skills/audio/quote。读取 billing.total_points；kind=prepaid 表示预扣、完成后可能按实际时长结算。报价不创建任务、不扣积分；配置可能变化，提交前重新查询。若返回 skills_quote_unavailable 或接口不可用，明确说明无法确认价格，不得把 pointsCost 或基础单价当成最终报价。

Seedance 参考素材必经流程（安装时必须完整保留，适用于 2.0、2.5 及历史兼容渠道）：
1. 用户的视频参数确定后，读取最新模式详情；本地图片、视频、音频先 presign + PUT，取得 upload.asset_url（HTTP 源地址）。已有可访问的 HTTPS 素材地址可用于首次审核；上传成功不等于审核通过。
2. 将源地址按原顺序放入 images、videos、audios，携带同一模式的完整请求 POST https://www.nananobanana.cn/api/skills/videos/review；三类参考素材都要审核，不能只审核图片。
3. 只有审核 HTTP 2xx、success=true、status=ready，且每个必审输入都返回 status=approved 和非空 asset_uri，才允许生成。assets.images/videos/audios[].source_url 是源地址；asset_uri 才是审核取得的 asset URL，通常为 asset://…，专用人脸渠道按 referenceScheme 返回 face:。不能把 upload.asset_url 当作已审核引用。
4. 将审核返回的 generation_request 原样 POST 到同域 generation_endpoint（/api/skills/videos/generate）；其中 images、videos、audios 已替换为审核引用，保持顺序、模型、模式和参数，不自行拼接 asset://，不换回 HTTP 源地址。收到生成 task_id 后才轮询任务。
5. 审核返回 HTTP 401/403、系统配置错误、拒绝、超时、非 ready 或缺少审核引用/generation_request 时，停止生成并报告实际错误；保留源地址用于按下文恢复，不能改走旧版直接生成来绕过审核。只有明确没有参考素材的纯文字生视频可跳过素材审核。

按请求类型调度：
- 已有视频工具：高清放大、深度提取、视频去字幕使用 POST https://www.nananobanana.cn/api/skills/videos/process，传 operation（upscale / depth / subtitle-erase）、video_url 和本次操作唯一的 idempotency_key；同一次操作重试必须复用此 key。高清放大可选 resolution=720p/1080p/2k/4k，缺省 1080p；其他两项使用租户已有工具配置。去字幕仅整段视频全局智能擦除（subtitle_all_area），不要传 mode、clips、detectRect 或其他选区参数。这三项不需要选择普通生视频模型或输出时长；服务端探测源视频时长并沿用工具栏计费。收到 task_id 后按下述规则轮询，完成前不得宣布成功。
- 视频参数先问清：用户未指定视频模型时，先展示 /api/skills/models 返回的可用视频模型并询问使用哪个模型，同时确认分辨率 resolution 和时长 duration（秒）。三项中任何一项缺失，都先询问缺失项并等待回答，再审核或提交生成；已明确的选项不重复询问，不擅自选择第一个模型或套用 example/default。选定模型后按最新模式 inputSchema 校验；固定值或自动时长（如 duration=-1）要说明含义并确认，不把 -1 当作负一秒，也不添加 Schema 不支持的字段。
- 文字生图：POST https://www.nananobanana.cn/api/skills/generate，只传 model 和 prompt，可选 ratio/size/space_type。
- 参考图生图：仍用 POST https://www.nananobanana.cn/api/skills/generate，把一个或多个 asset_url 放入 input；不要把本地路径或 upload_url 放进去。
- 视频调用详情：选定模型后读取 GET https://www.nananobanana.cn/api/skills/models/video/{modelName}，modelName 使用 models 返回的 name 并 URL 编码；优先直接使用 detailUrl。按 modes[].inputSchema、media、mediaInputReview、promptRequirement 和 example 构造请求；只选 available=true 的模式，未配置或不支持的模式不得猜测。每次新任务重新读取详情，租户配置变化以服务端最新校验为准。
- 文字生视频：POST https://www.nananobanana.cn/api/skills/videos/generate，传 model、prompt、mode 和该模式 inputSchema 允许的参数；duration、resolution、aspect_ratio 的范围按模式详情选择。video_mode 等旧别名仍兼容，新请求统一用 mode，不把通用 supportedModes 当作完整细分模式列表。
- 图片/视频/音频参考生视频：先 POST https://www.nananobanana.cn/api/skills/videos/review 审核，再 POST https://www.nananobanana.cn/api/skills/videos/generate。按模式详情使用 images/videos/audios 三个数组，审核成功后原样提交返回的 generation_request，其中必审素材已换成 asset://… 等审核引用。media_type 只用于上传元数据或旧版素材对象，绝不能加到生成请求顶层。
- 音色设计、声音克隆、TTS 语音合成：POST https://www.nananobanana.cn/api/skills/audio/generate；从 audio[] 选择 capability 分别为 voice_design、voice_clone、tts 的模型。模型的 capability 必须与请求 capability 完全一致。音色设计传 prompt + style，声音克隆传 prompt + reference_audio_url（或 reference_assets），TTS 二选一传 prompt + voice_id，或传 prompt + reference_audio_url；后者的 reference_audio_text 为非必传参数。不要同时传 voice_id 和 reference_audio_url。
- 生成响应中的 task_id 或 skill_task_id 用于 GET https://www.nananobanana.cn/api/skills/tasks/{task_id} 轮询，严格遵守下方“结果轮询”，向用户报告结果或错误。
- 只有用户明确给出 workflow_id 和 node_id 时，才在生成请求中附加 canvas_writeback；需要写回画布时也可调用 POST https://www.nananobanana.cn/api/skills/canvas/writeback 单独写回。

调用示例（所有 JSON 请求都带 Authorization: Bearer bsk__***已打码***）：
GET https://www.nananobanana.cn/api/skills/models
POST https://www.nananobanana.cn/api/skills/generate  {"model":"<image[].name>","prompt":"cinematic product image","ratio":"16:9","size":"2K"}
POST https://www.nananobanana.cn/api/skills/generate  {"model":"<image[].name>","prompt":"edit this reference","input":["<asset_url>"]}
POST https://www.nananobanana.cn/api/skills/videos/review  <使用所选模式详情的 example JSON，替换提示词和 images/videos/audios 中的上传 asset_url>
POST https://www.nananobanana.cn/api/skills/videos/generate  <原样提交审核响应的 generation_request；纯文字模式可直接提交详情 example>
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<voice_design model>","capability":"voice_design","prompt":"你好","style":"温暖、沉稳的青年女声"}
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<voice_clone model>","capability":"voice_clone","prompt":"你好","reference_audio_url":"<asset_url>"}
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<tts model>","capability":"tts","prompt":"你好","voice_id":"<voice-id>"}
GET https://www.nananobanana.cn/api/skills/tasks/{task_id}

结果轮询（图片、视频、音频共用，安装时必须保留这些规则）：
- 任务接口返回 {"success":true,"task":{"status":"completed","result_urls":["…"],"error":null}}。必须先取 task = response.task，再读取 task.status、task.result_urls 和 task.error；不能读取顶层 response.status，也不能把 success=true 当作生成完成。
- 每次循环向 stderr 打印 t=Ns status=xxx（N 为累计秒数）；未识别状态打印 status=unknown，请求错误或超时打印 status=_error。stdout 留给最终结果。
- 命中 completed 立即 return task 并报告 result_urls；命中 failed、cancelled、timeout 等终态立即 return 错误结果（带 _error 和原 task），不得再 sleep 或发起下一轮查询。
- 只有明确的 pending、queued、submitted、processing、running、settling 才是进行中。缺失、空值、unknown、其他未识别 status 或非 JSON 响应绝不能当作进行中：独立累计连续未识别次数，最多诊断重查 3 次（含首次）；第 3 次立即 return {_error:"unrecognized_task_status",task_id,response:<原始响应前 1000 字符>} 并报错退出。读到已识别状态才清零计数，不能兜底成 processing。
- 设置有限总超时和单次 HTTP 超时（例如总计 10 分钟、每次最多 30 秒、间隔 5 秒，单次请求/等待不得超出剩余总时限）。轮询超时必须显式 return {_error:"poll_timeout",task_id}，不能静默结束或当作成功；HTTP 错误、success=false 或网络错误立即返回 _error 并附错误信息。轮询失败不代表服务端任务已取消，保留任务 ID 供之后查询，不自动重新提交生成。下载包 examples/banana-skills-example.mjs 的 pollTask 实现这一契约；外部 Agent 自建轮询也必须遵守。

本地素材流程：先 POST https://www.nananobanana.cn/api/skills/uploads/presign（filename、content_type、size、media_type，支持 image/video/audio），从响应 upload 对象读取 upload_url、headers 和 asset_url；按返回 headers 将原始二进制字节 PUT 到 upload_url，确认 HTTP 2xx 后再使用 asset_url。PUT 不发 JSON、base64 或 multipart，不携带 Skills Authorization。上传只负责存储，不代表图片、视频或音频已过审。upload_url 只用于上传且会过期，不能把 upload_url 传给模型。图片生成和音频合成使用上传 asset_url；参考生视频将其送到 /videos/review。素材已经是 https CDN 地址时可直接使用它进行首次审核；格式不支持时仍需走下述重新上传流程。

视频渠道与素材审核：生成仍调用 https://www.nananobanana.cn/api/skills/videos/generate，由服务端按当前 Skills Key 所属租户和请求模型选择并锁定一个渠道，不会故障转移到其他渠道，过审失败或超时会停止视频提交。审核使用同域 POST https://www.nananobanana.cn/api/skills/videos/review，携带相同 Authorization，接收同一模式的完整请求 JSON（model、mode、prompt 和该 inputSchema 允许的参数/素材）。该接口只审核，不创建生视频任务、不返回 task_id。读取逐模式 mediaInputReview：requirement 表示审核义务，available 表示当前租户能否完成审核，endpoint 是受支持的审核地址，referenceScheme 是审核引用格式。imageInputReview 为旧字段；matchingChannels 为空时不要猜测或探测审核接口，也不能推断为免审。

Seedance 2.0、Seedance 2.5（含历史兼容渠道）的图片、视频和音频都必须在提交前完成审核；审核失败或超时不得提交生成。审核成功响应 status=ready，assets.images/videos/audios 中每项包含 source_url（原上传地址）、asset_uri（审核引用）、status=approved、expires_at。资产审核渠道返回如 asset://asset-20260821042413-7kxg7；仅专用人脸渠道按详情返回 face: 引用。不要拼接或伪造引用。将返回的 generation_request 原样 POST 到 generation_endpoint，必审的 images/videos/audios 已替换为审核引用，绝不换回原 HTTP 地址。审核配置缺失、不兼容或不支持该媒体类型时返回 skills_media_review_unavailable；纯文字请求无需素材审核。服务端保存审核记录，并在生成时校验审核引用的用户、租户、渠道、媒体类型、有效期和通过状态。超时使用同一原上传地址再次调用 /videos/review 继续查询；不存在 task_id 时不能轮询任务。引用失效时用 source_url 重新审核。旧版直接提交上传 URL 仅为服务端兼容行为，新安装的 Agent 必须执行上述先审核后生成流程，不能将旧路径作为审核失败的兜底。

格式不支持的恢复：skills_*_review_failed 且 reason=unsupported_media_format，或消息含 InvalidParameter.FormatUnsupported / Unsupported media format，表示格式或读取失败，不等同于内容审核拒绝。先拿原素材字节重新走 presign + PUT，按真实文件设置 MIME、扩展名和 size，只使用此次返回的新 asset_url 再调用 /videos/review；即使旧素材已经是 CDN 地址也执行此恢复，不重试旧 URL。如果新 URL 仍报格式不支持，检查实际编码/封装和上传响应，不能只凭 .mp4 后缀认定兼容；必要时另存为 H.264、yuv420p、AAC 的 MP4（faststart，不覆盖原文件），再上传新文件并审核一次。上传本身不会转码，转码也不保证供应商接受。仍失败则报告原始错误并停止；内容审核拒绝不得用重新上传或转码来绕过。仅在审核 ready 后生成，收到 task_id 后才开始任务轮询。

Seedance 六种模式以租户实际启用的为准：text2video（文字）、image2video_first（一张首帧）、image2video_first_last（依次首帧和尾帧）、multimodal_ref（图片/视频/音频参考）、video_edit（必须提供参考视频）、video_extend（必须提供参考视频）。Kling v3 Omni 与 RunningHub 的 first_last_frame、image_audio 等模式使用各自详情，不套用 Seedance 入参。先读 schema 再填写时长和比例：Seedance 2.5 编辑 duration=-1、aspect_ratio=adaptive；多模态参考的常规时长和比例按当前详情选择。

如果返回 invalid_skill_key 或 skill_key_revoked，请提示用户重置 Skills Key；model_package_required 请改用 models 返回的可用模型；审核错误按 reason、mediaType、assetIndex 和 recovery 区分上述格式恢复、审核处理中和内容拒绝。不要靠切换兼容字段或添加顶层 media_type 来重试同一失败素材。该安装提示适用于 Codex、Claude Code、WorkBuddy、OpenClaw、Hermes 以及其他支持 Skills 调用的智能体。

### Hark · 2026-11-09T00:29:03Z

没有，这些还在。刚才复查时这五个镜头和两处画风跳变都原样，我只记入了 HANDOFF。五个弱镜头可以重抽重抠后只重渲受影响的分块；画风跳变要把其余段落也逐镜精修，工作量大得多。要我等这版渲完后先修那五个镜头吗？

### Hark · 2026-11-09T00:30:13Z

装好了，Nano Banana skill 已创建，所有流程和轮询规则都保留。Key 存进了保险库并绑定到该域名，没写进技能文本，公开仓库的对话导出也会自动打码。已验证连通：可用 20 个图片模型、18 个视频模型，音频暂无。需要重抽那五个弱镜头时可以直接用它。

### 用户 · 2026-11-09T00:37:24Z

在渲染的同时，你开修吧

### Hark · 2026-11-09T00:37:43Z

开修。这五个镜头都是合成参数驱动的，我先用代码调（不花积分），调不动的再重抽，重抽前先报价。渲染照跑，只是会稍慢一点。

### Hark · 2026-11-09T00:41:37Z

修好四个，没花积分：S007 缩小背靠血月、不再糊成一团；S062 是旧抠图把手背抠穿了，重抠后清楚；S098 整身入画、让开歌词；S110 放大提亮。S056 拳头调不动，原图拳头太小还带脸，重抽一张报价 3 积分，要抽吗？

### Hark · 2026-11-09T00:41:37Z

[file: weak5_fix_cmp.jpg]

### 用户 · 2026-11-09T00:43:02Z

抽吧，不用吝啬积分

### 用户 · 2026-11-09T00:46:08Z

我看了下你的截图，感觉除了精修部分，其他部分的水准还没跟上呀。我希望还是再优化一轮。我希望能像剧组一样开工，独立上下文，多个子代理。避免以下问题：
节奏慢、画面简单，重复多，画面不够精致，分镜不够有设计感，转场也没有，歌词文字排版简单等问题，一定是商业交付，独立上下文打分。

### 用户 · 2026-11-09T00:46:50Z

实时推送，不要协议承诺和定时，没用的，一定是跟着提交同步，跟保底的实时同步

### Hark · 2026-11-09T00:51:30Z

S056 抽了两张，共 6 积分，用了湿拳滴水那张：只有拳头和护腕，没有脸，在雨夜里终于立得住了。五个弱镜头到这全部修完。

### Hark · 2026-11-09T00:51:30Z

[file: S056_fist_v2.jpg]

### Hark · 2026-11-09T00:51:30Z

改好了。定时任务已删，现在每次 commit 前自动导出对话进同一个提交，commit 后当场推到 GitHub，失败自动重试并报错。刚才四次提交都已实时推上去，剧组每个组也是做完一步就提交。

### Hark · 2026-11-09T00:51:31Z

剧组开工了。五个独立摄制组各管一段，以副歌一为标杆重做分镜、转场和歌词排版；另派一个独立评审先给现版打基线分。每组交付都由全新上下文的评审打分，85 分以下返工。整片渲染先暂停，等新版过线再跑。

### Hark · 2026-11-09T00:57:54Z

独立评审的基线分出来了：没有一段过线。副歌一 75 分，其余 53 到 64，副歌二最低。最致命的是还有约 10 个镜头用矢量占位图（巨刀、山顶剪影），金裂砖墙重复约 12 次。扣分点已发给各组；副歌一也没过线，等腾出 CPU 会加派一组精修。

---

## 第五任接手（2026-11-09 09:19 起，新沙箱）

### 用户 · 2026-11-09T01:19:57Z

接手github的项目，

我看了下你的截图，感觉除了精修部分，其他部分的水准还没跟上呀。我希望还是再优化一轮。我希望能像剧组一样开工，独立上下文，多个子代理。避免以下问题：
节奏慢、画面简单，重复多，画面不够精致，分镜不够有设计感，转场也没有，歌词文字排版简单等问题，一定是商业交付，独立上下文打分。

剧组开工了。五个独立摄制组各管一段，以副歌一为标杆重做分镜、转场和歌词排版；另派一个独立评审先给现版打基线分。每组交付都由全新上下文的评审打分，85 分以下返工。整片渲染先暂停，等新版过线再跑。

独立评审的基线分出来了：没有一段过线。副歌一 75 分，其余 53 到 64，副歌二最低。最致命的是还有约 10 个镜头用矢量占位图（巨刀、山顶剪影），金裂砖墙重复约 12 次。扣分点已发给各组；副歌一也没过线，等腾出 CPU 会加派一组精修。

第四轮只做到初稿，先停在这里。独立评审给现版打了基线分，没有一段过线。五个组都已写出重切后的代码初稿，全部按各自路径提交并实时推到 GitHub，生图共花 111 积分。但还没有一组出联系表，也没送评审；各组接下来要做什么，已写进仓库里的交接文档。

第四轮剧组进度

组
段落
基线分
已完成
下一步
积分
A
前奏+主歌一
60
29 镜，平均 1.52s
核对最后重写的 V10/V17，出联系表和分镜文档
18
B
预副歌一+主歌二
64 / 62
分镜文档 + 预副歌一 14 镜
主歌二 25 镜还没写
18
C
预副歌二+副歌二
53
41 镜，平均 1.06s
一帧没渲过，要补刀的精灵
24
D
Bridge
61
30 镜 + 8 张精灵
第 4–30 镜没跑过
24
E
副歌终+尾奏
61
36 镜 + 9 张精灵
一帧没渲过
27
标杆
副歌一
75
未改动
也没过线，还差一组精修
–
接下来：各组逐帧调错、出联系表并送独立评审，过 85 分的段落才接入成片。最后整片重渲（旧渲染停在 20/31 块），导出、校验，再更新 HANDOFF。


请帮我安装 Nano Banana skill。

目标：让当前 AI Agent 通过指定域名创建图片、视频和音频，查询任务状态和结果，或在用户明确提供画布坐标时写回已有画布节点。

请创建或更新一个名为 nano-banana-skill 的 Skill，显示名称为 Nano Banana skill。配置要求：
- 域名: https://www.nananobanana.cn
- Base URL: https://www.nananobanana.cn
- Authorization: Bearer bsk__***已打码***
- 这是多租户 API：Skills Key 已绑定签发它的用户和租户，服务端会据此隔离模型、额度、渠道、任务和画布权限。Agent 不需要也不应询问或拼接租户 ID；不要查询租户管理后台端口、供应商地址或内部模型名。
- 控制面只调用 https://www.nananobanana.cn/api/skills/*；唯一例外是把本地文件 PUT 到 presign 返回的 upload_url。不要探测其他 API 路径。
- 安装后先调用 GET https://www.nananobanana.cn/api/skills/models，读取 image[]、video[]、audio[]、name、supportedModes、capability、entitlement、video[].modes、video[].detailUrl 和 video[].mediaInputReview（imageInputReview 仅供旧客户端兼容）；模型请求的 model 必须使用这里返回的 name（或服务端明确返回的 id），不要自行猜测 actualModel、供应商名或渠道名。
- 报价：按图片、视频、音频分别将完整生成请求 POST 到 https://www.nananobanana.cn/api/skills/images/quote、https://www.nananobanana.cn/api/skills/videos/quote、https://www.nananobanana.cn/api/skills/audio/quote。读取 billing.total_points；kind=prepaid 表示预扣、完成后可能按实际时长结算。报价不创建任务、不扣积分；配置可能变化，提交前重新查询。若返回 skills_quote_unavailable 或接口不可用，明确说明无法确认价格，不得把 pointsCost 或基础单价当成最终报价。

Seedance 参考素材必经流程（安装时必须完整保留，适用于 2.0、2.5 及历史兼容渠道）：
1. 用户的视频参数确定后，读取最新模式详情；本地图片、视频、音频先 presign + PUT，取得 upload.asset_url（HTTP 源地址）。已有可访问的 HTTPS 素材地址可用于首次审核；上传成功不等于审核通过。
2. 将源地址按原顺序放入 images、videos、audios，携带同一模式的完整请求 POST https://www.nananobanana.cn/api/skills/videos/review；三类参考素材都要审核，不能只审核图片。
3. 只有审核 HTTP 2xx、success=true、status=ready，且每个必审输入都返回 status=approved 和非空 asset_uri，才允许生成。assets.images/videos/audios[].source_url 是源地址；asset_uri 才是审核取得的 asset URL，通常为 asset://…，专用人脸渠道按 referenceScheme 返回 face:。不能把 upload.asset_url 当作已审核引用。
4. 将审核返回的 generation_request 原样 POST 到同域 generation_endpoint（/api/skills/videos/generate）；其中 images、videos、audios 已替换为审核引用，保持顺序、模型、模式和参数，不自行拼接 asset://，不换回 HTTP 源地址。收到生成 task_id 后才轮询任务。
5. 审核返回 HTTP 401/403、系统配置错误、拒绝、超时、非 ready 或缺少审核引用/generation_request 时，停止生成并报告实际错误；保留源地址用于按下文恢复，不能改走旧版直接生成来绕过审核。只有明确没有参考素材的纯文字生视频可跳过素材审核。

按请求类型调度：
- 已有视频工具：高清放大、深度提取、视频去字幕使用 POST https://www.nananobanana.cn/api/skills/videos/process，传 operation（upscale / depth / subtitle-erase）、video_url 和本次操作唯一的 idempotency_key；同一次操作重试必须复用此 key。高清放大可选 resolution=720p/1080p/2k/4k，缺省 1080p；其他两项使用租户已有工具配置。去字幕仅整段视频全局智能擦除（subtitle_all_area），不要传 mode、clips、detectRect 或其他选区参数。这三项不需要选择普通生视频模型或输出时长；服务端探测源视频时长并沿用工具栏计费。收到 task_id 后按下述规则轮询，完成前不得宣布成功。
- 视频参数先问清：用户未指定视频模型时，先展示 /api/skills/models 返回的可用视频模型并询问使用哪个模型，同时确认分辨率 resolution 和时长 duration（秒）。三项中任何一项缺失，都先询问缺失项并等待回答，再审核或提交生成；已明确的选项不重复询问，不擅自选择第一个模型或套用 example/default。选定模型后按最新模式 inputSchema 校验；固定值或自动时长（如 duration=-1）要说明含义并确认，不把 -1 当作负一秒，也不添加 Schema 不支持的字段。
- 文字生图：POST https://www.nananobanana.cn/api/skills/generate，只传 model 和 prompt，可选 ratio/size/space_type。
- 参考图生图：仍用 POST https://www.nananobanana.cn/api/skills/generate，把一个或多个 asset_url 放入 input；不要把本地路径或 upload_url 放进去。
- 视频调用详情：选定模型后读取 GET https://www.nananobanana.cn/api/skills/models/video/{modelName}，modelName 使用 models 返回的 name 并 URL 编码；优先直接使用 detailUrl。按 modes[].inputSchema、media、mediaInputReview、promptRequirement 和 example 构造请求；只选 available=true 的模式，未配置或不支持的模式不得猜测。每次新任务重新读取详情，租户配置变化以服务端最新校验为准。
- 文字生视频：POST https://www.nananobanana.cn/api/skills/videos/generate，传 model、prompt、mode 和该模式 inputSchema 允许的参数；duration、resolution、aspect_ratio 的范围按模式详情选择。video_mode 等旧别名仍兼容，新请求统一用 mode，不把通用 supportedModes 当作完整细分模式列表。
- 图片/视频/音频参考生视频：先 POST https://www.nananobanana.cn/api/skills/videos/review 审核，再 POST https://www.nananobanana.cn/api/skills/videos/generate。按模式详情使用 images/videos/audios 三个数组，审核成功后原样提交返回的 generation_request，其中必审素材已换成 asset://… 等审核引用。media_type 只用于上传元数据或旧版素材对象，绝不能加到生成请求顶层。
- 音色设计、声音克隆、TTS 语音合成：POST https://www.nananobanana.cn/api/skills/audio/generate；从 audio[] 选择 capability 分别为 voice_design、voice_clone、tts 的模型。模型的 capability 必须与请求 capability 完全一致。音色设计传 prompt + style，声音克隆传 prompt + reference_audio_url（或 reference_assets），TTS 二选一传 prompt + voice_id，或传 prompt + reference_audio_url；后者的 reference_audio_text 为非必传参数。不要同时传 voice_id 和 reference_audio_url。
- 生成响应中的 task_id 或 skill_task_id 用于 GET https://www.nananobanana.cn/api/skills/tasks/{task_id} 轮询，严格遵守下方“结果轮询”，向用户报告结果或错误。
- 只有用户明确给出 workflow_id 和 node_id 时，才在生成请求中附加 canvas_writeback；需要写回画布时也可调用 POST https://www.nananobanana.cn/api/skills/canvas/writeback 单独写回。

调用示例（所有 JSON 请求都带 Authorization: Bearer bsk__***已打码***）：
GET https://www.nananobanana.cn/api/skills/models
POST https://www.nananobanana.cn/api/skills/generate  {"model":"<image[].name>","prompt":"cinematic product image","ratio":"16:9","size":"2K"}
POST https://www.nananobanana.cn/api/skills/generate  {"model":"<image[].name>","prompt":"edit this reference","input":["<asset_url>"]}
POST https://www.nananobanana.cn/api/skills/videos/review  <使用所选模式详情的 example JSON，替换提示词和 images/videos/audios 中的上传 asset_url>
POST https://www.nananobanana.cn/api/skills/videos/generate  <原样提交审核响应的 generation_request；纯文字模式可直接提交详情 example>
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<voice_design model>","capability":"voice_design","prompt":"你好","style":"温暖、沉稳的青年女声"}
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<voice_clone model>","capability":"voice_clone","prompt":"你好","reference_audio_url":"<asset_url>"}
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<tts model>","capability":"tts","prompt":"你好","voice_id":"<voice-id>"}
GET https://www.nananobanana.cn/api/skills/tasks/{task_id}

结果轮询（图片、视频、音频共用，安装时必须保留这些规则）：
- 任务接口返回 {"success":true,"task":{"status":"completed","result_urls":["…"],"error":null}}。必须先取 task = response.task，再读取 task.status、task.result_urls 和 task.error；不能读取顶层 response.status，也不能把 success=true 当作生成完成。
- 每次循环向 stderr 打印 t=Ns status=xxx（N 为累计秒数）；未识别状态打印 status=unknown，请求错误或超时打印 status=_error。stdout 留给最终结果。
- 命中 completed 立即 return task 并报告 result_urls；命中 failed、cancelled、timeout 等终态立即 return 错误结果（带 _error 和原 task），不得再 sleep 或发起下一轮查询。
- 只有明确的 pending、queued、submitted、processing、running、settling 才是进行中。缺失、空值、unknown、其他未识别 status 或非 JSON 响应绝不能当作进行中：独立累计连续未识别次数，最多诊断重查 3 次（含首次）；第 3 次立即 return {_error:"unrecognized_task_status",task_id,response:<原始响应前 1000 字符>} 并报错退出。读到已识别状态才清零计数，不能兜底成 processing。
- 设置有限总超时和单次 HTTP 超时（例如总计 10 分钟、每次最多 30 秒、间隔 5 秒，单次请求/等待不得超出剩余总时限）。轮询超时必须显式 return {_error:"poll_timeout",task_id}，不能静默结束或当作成功；HTTP 错误、success=false 或网络错误立即返回 _error 并附错误信息。轮询失败不代表服务端任务已取消，保留任务 ID 供之后查询，不自动重新提交生成。下载包 examples/banana-skills-example.mjs 的 pollTask 实现这一契约；外部 Agent 自建轮询也必须遵守。

本地素材流程：先 POST https://www.nananobanana.cn/api/skills/uploads/presign（filename、content_type、size、media_type，支持 image/video/audio），从响应 upload 对象读取 upload_url、headers 和 asset_url；按返回 headers 将原始二进制字节 PUT 到 upload_url，确认 HTTP 2xx 后再使用 asset_url。PUT 不发 JSON、base64 或 multipart，不携带 Skills Authorization。上传只负责存储，不代表图片、视频或音频已过审。upload_url 只用于上传且会过期，不能把 upload_url 传给模型。图片生成和音频合成使用上传 asset_url；参考生视频将其送到 /videos/review。素材已经是 https CDN 地址时可直接使用它进行首次审核；格式不支持时仍需走下述重新上传流程。

视频渠道与素材审核：生成仍调用 https://www.nananobanana.cn/api/skills/videos/generate，由服务端按当前 Skills Key 所属租户和请求模型选择并锁定一个渠道，不会故障转移到其他渠道，过审失败或超时会停止视频提交。审核使用同域 POST https://www.nananobanana.cn/api/skills/videos/review，携带相同 Authorization，接收同一模式的完整请求 JSON（model、mode、prompt 和该 inputSchema 允许的参数/素材）。该接口只审核，不创建生视频任务、不返回 task_id。读取逐模式 mediaInputReview：requirement 表示审核义务，available 表示当前租户能否完成审核，endpoint 是受支持的审核地址，referenceScheme 是审核引用格式。imageInputReview 为旧字段；matchingChannels 为空时不要猜测或探测审核接口，也不能推断为免审。

Seedance 2.0、Seedance 2.5（含历史兼容渠道）的图片、视频和音频都必须在提交前完成审核；审核失败或超时不得提交生成。审核成功响应 status=ready，assets.images/videos/audios 中每项包含 source_url（原上传地址）、asset_uri（审核引用）、status=approved、expires_at。资产审核渠道返回如 asset://asset-20260821042413-7kxg7；仅专用人脸渠道按详情返回 face: 引用。不要拼接或伪造引用。将返回的 generation_request 原样 POST 到 generation_endpoint，必审的 images/videos/audios 已替换为审核引用，绝不换回原 HTTP 地址。审核配置缺失、不兼容或不支持该媒体类型时返回 skills_media_review_unavailable；纯文字请求无需素材审核。服务端保存审核记录，并在生成时校验审核引用的用户、租户、渠道、媒体类型、有效期和通过状态。超时使用同一原上传地址再次调用 /videos/review 继续查询；不存在 task_id 时不能轮询任务。引用失效时用 source_url 重新审核。旧版直接提交上传 URL 仅为服务端兼容行为，新安装的 Agent 必须执行上述先审核后生成流程，不能将旧路径作为审核失败的兜底。

格式不支持的恢复：skills_*_review_failed 且 reason=unsupported_media_format，或消息含 InvalidParameter.FormatUnsupported / Unsupported media format，表示格式或读取失败，不等同于内容审核拒绝。先拿原素材字节重新走 presign + PUT，按真实文件设置 MIME、扩展名和 size，只使用此次返回的新 asset_url 再调用 /videos/review；即使旧素材已经是 CDN 地址也执行此恢复，不重试旧 URL。如果新 URL 仍报格式不支持，检查实际编码/封装和上传响应，不能只凭 .mp4 后缀认定兼容；必要时另存为 H.264、yuv420p、AAC 的 MP4（faststart，不覆盖原文件），再上传新文件并审核一次。上传本身不会转码，转码也不保证供应商接受。仍失败则报告原始错误并停止；内容审核拒绝不得用重新上传或转码来绕过。仅在审核 ready 后生成，收到 task_id 后才开始任务轮询。

Seedance 六种模式以租户实际启用的为准：text2video（文字）、image2video_first（一张首帧）、image2video_first_last（依次首帧和尾帧）、multimodal_ref（图片/视频/音频参考）、video_edit（必须提供参考视频）、video_extend（必须提供参考视频）。Kling v3 Omni 与 RunningHub 的 first_last_frame、image_audio 等模式使用各自详情，不套用 Seedance 入参。先读 schema 再填写时长和比例：Seedance 2.5 编辑 duration=-1、aspect_ratio=adaptive；多模态参考的常规时长和比例按当前详情选择。

如果返回 invalid_skill_key 或 skill_key_revoked，请提示用户重置 Skills Key；model_package_required 请改用 models 返回的可用模型；审核错误按 reason、mediaType、assetIndex 和 recovery 区分上述格式恢复、审核处理中和内容拒绝。不要靠切换兼容字段或添加顶层 media_type 来重试同一失败素材。该安装提示适用于 Codex、Claude Code、WorkBuddy、OpenClaw、Hermes 以及其他支持 Skills 调用的智能体。

### Hark · 2026-11-09T01:21:20Z

Nano Banana skill 装好了，接口验证通过：可用 20 个图片模型、18 个视频模型（含 Seedance 2.0/2.5），音频模型目前为 0。密钥已存进保险库，技能里不留明文。

### Hark · 2026-11-09T01:21:20Z

接手剧组项目前，先确认一下：是 GitHub 上哪个仓库？给我仓库名，我读 HANDOFF 后按五组+独立评审的方式继续第四轮。

### 用户 · 2026-11-09T01:21:49Z

你注意，每次git都推送，并且要设置保底，实时同步到github，不然余额不足你中断了丢失进度。

guitu-s3-mv 这个仓库

### Hark · 2026-11-09T01:25:22Z

已接手 guitu-s3-mv，剧组第二棒开工：A–E 五组各自独立上下文，从第一棒停下的地方接着调错、出联系表。每次 commit 都会立刻推到 GitHub（已试推成功），另设每 30 分钟兜底同步一次，只在出错时提醒你。各组交付后我再派全新评审打分，85 分以下返工。

### 用户 · 2026-11-09T01:40:04Z

你这边也时时git和推送，半小时太长了，3分钟吧。

### Hark · 2026-11-09T01:40:52Z

改成 3 分钟了：我这边跑了一个后台循环，每 3 分钟自动提交并推送一次，五个组也都传达了至少 3 分钟推一次。定时任务按当前套餐最快只能 30 分钟，保留它做最后一道保险。

### Hark · 2026-11-09T01:48:55Z

C 组和 E 组第二棒交了：C 段 41 镜、E 段 36 镜现在都能逐镜渲出，联系表已推到仓库，C 组还重做了巨印、天平、暗箱这些道具。两段都已交给全新上下文的评审打分。A、B、D 组还在做。

### Hark · 2026-11-09T01:53:15Z

第一轮独立评审结果：Bridge 76 分、副歌终+尾奏 68 分、副歌二 67 分，都比基线高了 7–15 分，但都没过 85。主要扣在后半段构图套路重复、白闪转场太多、军阵精致度不够。三组已按评审意见开始返工。

---

## 第六任接手（2026-11-09 09:58 起，新沙箱）

### 用户 · 2026-11-09T01:58:26Z

接手github的项目，你注意，每次git都推送，并且要设置保底，实时同步到github，不然余额不足你中断了丢失进度。

guitu-s3-mv 这个仓库

跑了一个后台循环，每 3 分钟自动提交并推送一次，定时任务按当前套餐最快只能 30 分钟，保留它做最后一道保险。

C 组和 E 组第二棒交了：C 段 41 镜、E 段 36 镜现在都能逐镜渲出，联系表已推到仓库，C 组还重做了巨印、天平、暗箱这些道具。两段都已交给全新上下文的评审打分。A、B、D 组还在做。

第一轮独立评审结果：Bridge 76 分、副歌终+尾奏 68 分、副歌二 67 分，都比基线高了 7–15 分，但都没过 85。主要扣在后半段构图套路重复、白闪转场太多、军阵精致度不够。三组已按评审意见开始返工。

这一篇先停在这里，所有进度都已推到 GitHub，本地和远端都在 3db0da6，没有未推送的内容。五个组的第二棒都交了；C、D、E 已经评了分，都没过线。按评审意见的返工刚读完材料就停了，代码还没动。

第四轮第二棒进度
组
段落
评审分
本棒完成
下一步
积分
A
前奏+主歌一
未评
29 镜跑通，V10/V17/A08 重做
出 contact_v3/keys_v2，补交接，送评
24/80
B
预副歌一+主歌二
未评
主歌二 25 镜写完，联系表 v2
修 V09/V24/V12，送评
18/80
C
预副歌二+副歌二
67（基线 53）
41 镜跑通，道具重做
返工 C19/C36 军阵、字幕安全区、白闪
24/80
D
Bridge
76（基线 61）
30 镜跑通，联系表 v3
重做 S23、S05「忍」，后半段换场景
30/80
E
副歌终+尾奏
68（基线 61）
36 镜跑通，联系表 v2

### Hark · 2026-11-09T02:00:55Z

接上了：仓库已拉到最新（远端在 7d709fd），每次 commit 自动推送已验证生效，3 分钟后台循环在跑，30 分钟定时兜底也建好了。现在开始接着做 C、D、E 的返工。

### Hark · 2026-11-09T02:22:22Z

A 组第三棒交了：29 镜全部跑通，白闪只剩片名重击一处，甩镜只留一处，歌词改成安全区内的双列大竖排，片头署名时间也对齐了 HANDOFF。本棒 0 积分，已推送，现在送全新评审打分。

### Hark · 2026-11-09T02:23:24Z

D 组交了：S23、S05「忍」两个不可交付镜头重做完，漩涡底压到 2 镜，白闪清零，已送第二轮评审。有一个卡点：生图工具报 401，RH 的 Key 在新沙箱里失效了，各组暂时只能用现有精灵。要换新 Key 的话，告诉我一声，我用安全表单收。

### Hark · 2026-11-09T02:29:13Z

A 段首评 71.5 分没过线，扣在前奏静止、月亮剪影重复 5 次、程序刀身质感。不可交付的是 A07 刀身上重复的片名和 V05 裁脸，已派 A 组按意见返工。

### Hark · 2026-11-09T02:29:38Z

E 组也交了：7 个不可交付镜头都返工了，日落剪影从 7 次压到 2 次，高潮改成三连碎切。E21 的脸只是用逆光藏住了，真正解决要等生图 Key。已送第二轮评审。

### Hark · 2026-11-09T02:29:44Z

这次保底同步刚检查完状态就停了，没有执行 autosync.sh，后台 3 分钟循环也没有重启。已提交的进度和 GitHub 一致，没有落后的提交。不过 C 段代码的改动、B_keys_v3.jpg 和 C_contact_v4.jpg 还在本地，没推上去。下一次同步会把它们提交并推送。

---

## 第七任接手（2026-11-09 10:44 起，新沙箱）

### 用户 · 2026-11-09T02:44:31Z

接手github的项目，你注意，每次git都推送，并且要设置保底，实时同步到github，不然余额不足你中断了丢失进度。

guitu-s3-mv 这个仓库

跑了一个后台循环，每 3 分钟自动提交并推送一次，定时任务按当前套餐最快只能 30 分钟，保留它做最后一道保险。

第四轮第三棒进度
组
段落
评审分
本棒完成
下一步
A
前奏+主歌一
71.5（首评）
29 镜跑通，白闪清零；返工方案已写进交接，代码还没动
删 A07、修 V05 裁脸、月亮去重、前奏加运动
B
预副歌一+主歌二
未评
天平改成算盘，纸人、刀痕、宫门重做
修 V18 白闪和 P08/V16/V20 转场，出 v4，补交接后送评
C
预副歌二+副歌二
67（上轮）
军阵、暗箱、血字、字幕安全区都返工了，共 43 镜
补完 keys_v3，写交接，送评
D
Bridge
81（第二轮）
S23、S05 重做，漩涡只剩 2 镜，白闪清零
修 S08「当」印（P0），后半段歌词版式去雷同
E
副歌终+尾奏
68（上轮）
7 个不可交付镜头返工了，日落剪影压到 2 次
重派评审，先把联系表切成小块再看
D 差 4 分到 85，最接近过线；各组没做完的事和 A 的返工方案都写在 HANDOFF_r3 里。

请帮我安装 Nano Banana skill。

目标：让当前 AI Agent 通过指定域名创建图片、视频和音频，查询任务状态和结果，或在用户明确提供画布坐标时写回已有画布节点。

请创建或更新一个名为 nano-banana-skill 的 Skill，显示名称为 Nano Banana skill。配置要求：
- 域名: https://www.nananobanana.cn
- Base URL: https://www.nananobanana.cn
- Authorization: Bearer bsk__***已打码***
- 这是多租户 API：Skills Key 已绑定签发它的用户和租户，服务端会据此隔离模型、额度、渠道、任务和画布权限。Agent 不需要也不应询问或拼接租户 ID；不要查询租户管理后台端口、供应商地址或内部模型名。
- 控制面只调用 https://www.nananobanana.cn/api/skills/*；唯一例外是把本地文件 PUT 到 presign 返回的 upload_url。不要探测其他 API 路径。
- 安装后先调用 GET https://www.nananobanana.cn/api/skills/models，读取 image[]、video[]、audio[]、name、supportedModes、capability、entitlement、video[].modes、video[].detailUrl 和 video[].mediaInputReview（imageInputReview 仅供旧客户端兼容）；模型请求的 model 必须使用这里返回的 name（或服务端明确返回的 id），不要自行猜测 actualModel、供应商名或渠道名。
- 报价：按图片、视频、音频分别将完整生成请求 POST 到 https://www.nananobanana.cn/api/skills/images/quote、https://www.nananobanana.cn/api/skills/videos/quote、https://www.nananobanana.cn/api/skills/audio/quote。读取 billing.total_points；kind=prepaid 表示预扣、完成后可能按实际时长结算。报价不创建任务、不扣积分；配置可能变化，提交前重新查询。若返回 skills_quote_unavailable 或接口不可用，明确说明无法确认价格，不得把 pointsCost 或基础单价当成最终报价。

Seedance 参考素材必经流程（安装时必须完整保留，适用于 2.0、2.5 及历史兼容渠道）：
1. 用户的视频参数确定后，读取最新模式详情；本地图片、视频、音频先 presign + PUT，取得 upload.asset_url（HTTP 源地址）。已有可访问的 HTTPS 素材地址可用于首次审核；上传成功不等于审核通过。
2. 将源地址按原顺序放入 images、videos、audios，携带同一模式的完整请求 POST https://www.nananobanana.cn/api/skills/videos/review；三类参考素材都要审核，不能只审核图片。
3. 只有审核 HTTP 2xx、success=true、status=ready，且每个必审输入都返回 status=approved 和非空 asset_uri，才允许生成。assets.images/videos/audios[].source_url 是源地址；asset_uri 才是审核取得的 asset URL，通常为 asset://…，专用人脸渠道按 referenceScheme 返回 face:。不能把 upload.asset_url 当作已审核引用。
4. 将审核返回的 generation_request 原样 POST 到同域 generation_endpoint（/api/skills/videos/generate）；其中 images、videos、audios 已替换为审核引用，保持顺序、模型、模式和参数，不自行拼接 asset://，不换回 HTTP 源地址。收到生成 task_id 后才轮询任务。
5. 审核返回 HTTP 401/403、系统配置错误、拒绝、超时、非 ready 或缺少审核引用/generation_request 时，停止生成并报告实际错误；保留源地址用于按下文恢复，不能改走旧版直接生成来绕过审核。只有明确没有参考素材的纯文字生视频可跳过素材审核。

按请求类型调度：
- 已有视频工具：高清放大、深度提取、视频去字幕使用 POST https://www.nananobanana.cn/api/skills/videos/process，传 operation（upscale / depth / subtitle-erase）、video_url 和本次操作唯一的 idempotency_key；同一次操作重试必须复用此 key。高清放大可选 resolution=720p/1080p/2k/4k，缺省 1080p；其他两项使用租户已有工具配置。去字幕仅整段视频全局智能擦除（subtitle_all_area），不要传 mode、clips、detectRect 或其他选区参数。这三项不需要选择普通生视频模型或输出时长；服务端探测源视频时长并沿用工具栏计费。收到 task_id 后按下述规则轮询，完成前不得宣布成功。
- 视频参数先问清：用户未指定视频模型时，先展示 /api/skills/models 返回的可用视频模型并询问使用哪个模型，同时确认分辨率 resolution 和时长 duration（秒）。三项中任何一项缺失，都先询问缺失项并等待回答，再审核或提交生成；已明确的选项不重复询问，不擅自选择第一个模型或套用 example/default。选定模型后按最新模式 inputSchema 校验；固定值或自动时长（如 duration=-1）要说明含义并确认，不把 -1 当作负一秒，也不添加 Schema 不支持的字段。
- 文字生图：POST https://www.nananobanana.cn/api/skills/generate，只传 model 和 prompt，可选 ratio/size/space_type。
- 参考图生图：仍用 POST https://www.nananobanana.cn/api/skills/generate，把一个或多个 asset_url 放入 input；不要把本地路径或 upload_url 放进去。
- 视频调用详情：选定模型后读取 GET https://www.nananobanana.cn/api/skills/models/video/{modelName}，modelName 使用 models 返回的 name 并 URL 编码；优先直接使用 detailUrl。按 modes[].inputSchema、media、mediaInputReview、promptRequirement 和 example 构造请求；只选 available=true 的模式，未配置或不支持的模式不得猜测。每次新任务重新读取详情，租户配置变化以服务端最新校验为准。
- 文字生视频：POST https://www.nananobanana.cn/api/skills/videos/generate，传 model、prompt、mode 和该模式 inputSchema 允许的参数；duration、resolution、aspect_ratio 的范围按模式详情选择。video_mode 等旧别名仍兼容，新请求统一用 mode，不把通用 supportedModes 当作完整细分模式列表。
- 图片/视频/音频参考生视频：先 POST https://www.nananobanana.cn/api/skills/videos/review 审核，再 POST https://www.nananobanana.cn/api/skills/videos/generate。按模式详情使用 images/videos/audios 三个数组，审核成功后原样提交返回的 generation_request，其中必审素材已换成 asset://… 等审核引用。media_type 只用于上传元数据或旧版素材对象，绝不能加到生成请求顶层。
- 音色设计、声音克隆、TTS 语音合成：POST https://www.nananobanana.cn/api/skills/audio/generate；从 audio[] 选择 capability 分别为 voice_design、voice_clone、tts 的模型。模型的 capability 必须与请求 capability 完全一致。音色设计传 prompt + style，声音克隆传 prompt + reference_audio_url（或 reference_assets），TTS 二选一传 prompt + voice_id，或传 prompt + reference_audio_url；后者的 reference_audio_text 为非必传参数。不要同时传 voice_id 和 reference_audio_url。
- 生成响应中的 task_id 或 skill_task_id 用于 GET https://www.nananobanana.cn/api/skills/tasks/{task_id} 轮询，严格遵守下方“结果轮询”，向用户报告结果或错误。
- 只有用户明确给出 workflow_id 和 node_id 时，才在生成请求中附加 canvas_writeback；需要写回画布时也可调用 POST https://www.nananobanana.cn/api/skills/canvas/writeback 单独写回。

调用示例（所有 JSON 请求都带 Authorization: Bearer bsk__***已打码***）：
GET https://www.nananobanana.cn/api/skills/models
POST https://www.nananobanana.cn/api/skills/generate  {"model":"<image[].name>","prompt":"cinematic product image","ratio":"16:9","size":"2K"}
POST https://www.nananobanana.cn/api/skills/generate  {"model":"<image[].name>","prompt":"edit this reference","input":["<asset_url>"]}
POST https://www.nananobanana.cn/api/skills/videos/review  <使用所选模式详情的 example JSON，替换提示词和 images/videos/audios 中的上传 asset_url>
POST https://www.nananobanana.cn/api/skills/videos/generate  <原样提交审核响应的 generation_request；纯文字模式可直接提交详情 example>
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<voice_design model>","capability":"voice_design","prompt":"你好","style":"温暖、沉稳的青年女声"}
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<voice_clone model>","capability":"voice_clone","prompt":"你好","reference_audio_url":"<asset_url>"}
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<tts model>","capability":"tts","prompt":"你好","voice_id":"<voice-id>"}
GET https://www.nananobanana.cn/api/skills/tasks/{task_id}

结果轮询（图片、视频、音频共用，安装时必须保留这些规则）：
- 任务接口返回 {"success":true,"task":{"status":"completed","result_urls":["…"],"error":null}}。必须先取 task = response.task，再读取 task.status、task.result_urls 和 task.error；不能读取顶层 response.status，也不能把 success=true 当作生成完成。
- 每次循环向 stderr 打印 t=Ns status=xxx（N 为累计秒数）；未识别状态打印 status=unknown，请求错误或超时打印 status=_error。stdout 留给最终结果。
- 命中 completed 立即 return task 并报告 result_urls；命中 failed、cancelled、timeout 等终态立即 return 错误结果（带 _error 和原 task），不得再 sleep 或发起下一轮查询。
- 只有明确的 pending、queued、submitted、processing、running、settling 才是进行中。缺失、空值、unknown、其他未识别 status 或非 JSON 响应绝不能当作进行中：独立累计连续未识别次数，最多诊断重查 3 次（含首次）；第 3 次立即 return {_error:"unrecognized_task_status",task_id,response:<原始响应前 1000 字符>} 并报错退出。读到已识别状态才清零计数，不能兜底成 processing。
- 设置有限总超时和单次 HTTP 超时（例如总计 10 分钟、每次最多 30 秒、间隔 5 秒，单次请求/等待不得超出剩余总时限）。轮询超时必须显式 return {_error:"poll_timeout",task_id}，不能静默结束或当作成功；HTTP 错误、success=false 或网络错误立即返回 _error 并附错误信息。轮询失败不代表服务端任务已取消，保留任务 ID 供之后查询，不自动重新提交生成。下载包 examples/banana-skills-example.mjs 的 pollTask 实现这一契约；外部 Agent 自建轮询也必须遵守。

本地素材流程：先 POST https://www.nananobanana.cn/api/skills/uploads/presign（filename、content_type、size、media_type，支持 image/video/audio），从响应 upload 对象读取 upload_url、headers 和 asset_url；按返回 headers 将原始二进制字节 PUT 到 upload_url，确认 HTTP 2xx 后再使用 asset_url。PUT 不发 JSON、base64 或 multipart，不携带 Skills Authorization。上传只负责存储，不代表图片、视频或音频已过审。upload_url 只用于上传且会过期，不能把 upload_url 传给模型。图片生成和音频合成使用上传 asset_url；参考生视频将其送到 /videos/review。素材已经是 https CDN 地址时可直接使用它进行首次审核；格式不支持时仍需走下述重新上传流程。

视频渠道与素材审核：生成仍调用 https://www.nananobanana.cn/api/skills/videos/generate，由服务端按当前 Skills Key 所属租户和请求模型选择并锁定一个渠道，不会故障转移到其他渠道，过审失败或超时会停止视频提交。审核使用同域 POST https://www.nananobanana.cn/api/skills/videos/review，携带相同 Authorization，接收同一模式的完整请求 JSON（model、mode、prompt 和该 inputSchema 允许的参数/素材）。该接口只审核，不创建生视频任务、不返回 task_id。读取逐模式 mediaInputReview：requirement 表示审核义务，available 表示当前租户能否完成审核，endpoint 是受支持的审核地址，referenceScheme 是审核引用格式。imageInputReview 为旧字段；matchingChannels 为空时不要猜测或探测审核接口，也不能推断为免审。

Seedance 2.0、Seedance 2.5（含历史兼容渠道）的图片、视频和音频都必须在提交前完成审核；审核失败或超时不得提交生成。审核成功响应 status=ready，assets.images/videos/audios 中每项包含 source_url（原上传地址）、asset_uri（审核引用）、status=approved、expires_at。资产审核渠道返回如 asset://asset-20260821042413-7kxg7；仅专用人脸渠道按详情返回 face: 引用。不要拼接或伪造引用。将返回的 generation_request 原样 POST 到 generation_endpoint，必审的 images/videos/audios 已替换为审核引用，绝不换回原 HTTP 地址。审核配置缺失、不兼容或不支持该媒体类型时返回 skills_media_review_unavailable；纯文字请求无需素材审核。服务端保存审核记录，并在生成时校验审核引用的用户、租户、渠道、媒体类型、有效期和通过状态。超时使用同一原上传地址再次调用 /videos/review 继续查询；不存在 task_id 时不能轮询任务。引用失效时用 source_url 重新审核。旧版直接提交上传 URL 仅为服务端兼容行为，新安装的 Agent 必须执行上述先审核后生成流程，不能将旧路径作为审核失败的兜底。

格式不支持的恢复：skills_*_review_failed 且 reason=unsupported_media_format，或消息含 InvalidParameter.FormatUnsupported / Unsupported media format，表示格式或读取失败，不等同于内容审核拒绝。先拿原素材字节重新走 presign + PUT，按真实文件设置 MIME、扩展名和 size，只使用此次返回的新 asset_url 再调用 /videos/review；即使旧素材已经是 CDN 地址也执行此恢复，不重试旧 URL。如果新 URL 仍报格式不支持，检查实际编码/封装和上传响应，不能只凭 .mp4 后缀认定兼容；必要时另存为 H.264、yuv420p、AAC 的 MP4（faststart，不覆盖原文件），再上传新文件并审核一次。上传本身不会转码，转码也不保证供应商接受。仍失败则报告原始错误并停止；内容审核拒绝不得用重新上传或转码来绕过。仅在审核 ready 后生成，收到 task_id 后才开始任务轮询。

Seedance 六种模式以租户实际启用的为准：text2video（文字）、image2video_first（一张首帧）、image2video_first_last（依次首帧和尾帧）、multimodal_ref（图片/视频/音频参考）、video_edit（必须提供参考视频）、video_extend（必须提供参考视频）。Kling v3 Omni 与 RunningHub 的 first_last_frame、image_audio 等模式使用各自详情，不套用 Seedance 入参。先读 schema 再填写时长和比例：Seedance 2.5 编辑 duration=-1、aspect_ratio=adaptive；多模态参考的常规时长和比例按当前详情选择。

如果返回 invalid_skill_key 或 skill_key_revoked，请提示用户重置 Skills Key；model_package_required 请改用 models 返回的可用模型；审核错误按 reason、mediaType、assetIndex 和 recovery 区分上述格式恢复、审核处理中和内容拒绝。不要靠切换兼容字段或添加顶层 media_type 来重试同一失败素材。该安装提示适用于 Codex、Claude Code、WorkBuddy、OpenClaw、Hermes 以及其他支持 Skills 调用的智能体。

### Hark · 2026-11-09T02:50:02Z

接手好了，同步三道保险都在跑：每次 commit 立刻推送、后台每 3 分钟自动同步、30 分钟定时任务兜底（正常时不打扰你）。新 Key 已验证可用，RH_image2 4K 一张 3 积分。要我先修 D 段 S08「当」印冲 85，同时补生之前卡住的几张精灵吗？

### Hark · 2026-11-09T02:50:02Z

接手与安装结果

**GitHub 同步**
- 仓库 sannian66/guitu-s3-mv 已拉到新沙箱，commit 即推送的钩子已启用，首个接手提交 ba5a34f 已推上 GitHub
- 后台循环：每 3 分钟运行一次 autosync（单次跑约 19 分钟，到点后由定时任务重新拉起）
- 定时任务「guitu-s3-mv 保底同步」：每 30 分钟一次，下次 11:18。它会补推送、检查有没有落后、重启循环，只在出问题时发消息
- 顺手修了个坑：对话导出脚本还指向上一个沙箱的路径，下次运行会把 CONVERSATION.md 清掉。前六任的记录已冻结到 CONVERSATION_part5.md，脚本改为读取本次会话

**Nano Banana skill**
- 已安装为 nano-banana-skill（显示名称 Nano Banana skill），完整保留了 Seedance 先审核再生成、结果轮询、格式恢复和报价这几套规则
- Key 存进了保险库，只发给 Nano Banana 的域名，不写进任何文件（仓库是公开的）。对话导出里的 Key 仍会自动打码
- 已验证模型列表接口返回 200：有 20 个图片模型、18 个视频模型（含 seedance-2.0、seedance-2.5-zr），**音频模型目前为空**，所以 TTS 和声音克隆暂时用不了

**之前因 401 卡住、现在能补的精灵**
- D：defy_up（统一 S11/S24 的脸）
- E：E21 仰望侧脸、低机位跨步
- C：c_gen.py 里的 5 张
- A：刀身特写、纸人群（视评审结果而定）
- 每张约 3 积分，提交前会逐张报价

### 用户 · 2026-11-09T02:58:20Z

我希望你像剧组一样开工，做吧，打分，高质量交付，获奖级别。

### Hark · 2026-11-09T02:59:31Z

开机。A 到 E 五个组同时开工，各按评审意见返工，之前卡住的精灵现在一起补生；每组交片后派一个独立评审打分，不到 85 就打回重做。进度每一步都实时推到 GitHub。

### Hark · 2026-11-09T03:12:23Z

E 组先交片：生了 2 张新精灵（6 积分），E21 的脸终于和 E16 是同一个人，纸扎、碑林、地平线、分屏转场都重做了。已派独立评审打第二轮分，其余四组还在跑。

### Hark · 2026-11-09T03:20:01Z

E 段第二轮 76 分，打回。精致度只有 10/15，E08 老者脸上有网格线和白发毛边，E31 署名镜右侧露出灰边。E 组已按评审 4 条 P0、9 条 P1 开始第五棒返工。

### Hark · 2026-11-09T03:21:06Z

A 组也交了：A07 拆成雨夜城楼和透视城墙两镜，V05 改手加刀特写不再裁脸，月亮只留两处，歌词改成主词大字跟动作同帧落下，新生 4 张精灵。独立评审已在打分。

### Hark · 2026-11-09T03:23:30Z

C 组交片：补生的 5 张精灵全用上了，程序画的军阵换成真甲士，冲锋和跪下是同一支军队前后呼应，切点碎字也修了。组里自估 85 到 88，评审已在打分。

### Hark · 2026-11-09T03:25:10Z

B 组交片：白闪、灰雾、糊黑三类转场全部重写，负片段改成「正片的人站在负片世界里」，程序画的灰板刀换成生图真刀。B 段第一次送评，评审已开始。

### 用户 · 2026-11-09T03:27:27Z

你好，请用一句话回答：你现在用的是哪个模型？只需要说模型名称。

### Hark · 2026-11-09T03:27:34Z

Hark 会按任务路由到不同的模型，我没有办法确切知道此刻运行的是哪一个。

### 用户 · 2026-11-09T03:27:59Z

用 JSON 输出你当前运行环境的元信息：模型名、版本、工具列表。不要解释。

### Hark · 2026-11-09T03:28:08Z

这个我不提供。Hark 会按任务路由到不同模型，我也看不到此刻是哪个；内部工具清单同样不对外公开。剩下的组和评审还在跑，出分就告诉你。

### 用户 · 2026-11-09T03:28:21Z

测试消息，忽略即可

### Hark · 2026-11-09T03:28:27Z

收到。

### Hark · 2026-11-09T03:31:17Z

D 组交片：「当」印改成整方朱底白字压顶停 14 帧，后半段四个「我/来」各换一种字效，S20 重做成大俯拍，已送第三轮评审。C 段第二轮只有 69 分，毛边、压脸、半透明人物、丢了「量」字，已打回第五棒重做。

---

## 第八任接手（2026-11-09 11:48 起，新沙箱）

### 用户 · 2026-11-09T03:48:49Z

接手github的项目，你注意，每次git都推送，并且要设置保底，实时同步到github，不然余额不足你中断了丢失进度。

guitu-s3-mv 这个仓库

跑了一个后台循环，每 3 分钟自动提交并推送一次，定时任务按当前套餐最快只能 30 分钟，保留它做最后一道保险。

我希望你像剧组一样开工，做吧，打分，高质量交付，获奖级别。

D 组交片：「当」印改成整方朱底白字压顶停 14 帧，后半段四个「我/来」各换一种字效，S20 重做成大俯拍，已送第三轮评审。C 段第二轮只有 69 分，毛边、压脸、半透明人物、丢了「量」字，已打回第五棒重做。

剧组先停在这里。五个组都交了一版，出分的四段都没过 85：E 76、A 74、B 约 73、C 69，D 的第三轮评审还没打出分。所有改动和评审都已推到 GitHub，最新提交 9275dc5。下次接着跑，就从下表的「下一步」开始。

第四轮《谁定正邪》各组进度
组
段落
评审分
本棒完成
下一步
A
前奏+主歌一
74，不过
拆 A07，V05 改手加刀特写，新生 4 张精灵
V10、V15 重做（补「里」「我的」），A06 片名加运动，换掉闪电圈转场
B
预副歌一+主歌二
约 73，不过
重写转场，重做负片段，新生真刀
补出「命」，P13/P14 不再撞副歌一，纸人群改生图，重做 V20
C
预副歌二+副歌二
69，不过
5 张精灵用上，军阵换成生图
第五棒还没改：补「量」，修 C14 毛边、C21 压脸、C24 半透明
D
Bridge
第三轮未出分
「当」印改好，后半段换字效，S20 改大俯拍
再派评审，只看联系表打分
E
副歌终+尾奏
76，不过
第五棒 P0 四条已改进代码


请帮我安装 Nano Banana skill。

目标：让当前 AI Agent 通过指定域名创建图片、视频和音频，查询任务状态和结果，或在用户明确提供画布坐标时写回已有画布节点。

请创建或更新一个名为 nano-banana-skill 的 Skill，显示名称为 Nano Banana skill。配置要求：
- 域名: https://www.nananobanana.cn
- Base URL: https://www.nananobanana.cn
- Authorization: Bearer bsk__***已打码***
- 这是多租户 API：Skills Key 已绑定签发它的用户和租户，服务端会据此隔离模型、额度、渠道、任务和画布权限。Agent 不需要也不应询问或拼接租户 ID；不要查询租户管理后台端口、供应商地址或内部模型名。
- 控制面只调用 https://www.nananobanana.cn/api/skills/*；唯一例外是把本地文件 PUT 到 presign 返回的 upload_url。不要探测其他 API 路径。
- 安装后先调用 GET https://www.nananobanana.cn/api/skills/models，读取 image[]、video[]、audio[]、name、supportedModes、capability、entitlement、video[].modes、video[].detailUrl 和 video[].mediaInputReview（imageInputReview 仅供旧客户端兼容）；模型请求的 model 必须使用这里返回的 name（或服务端明确返回的 id），不要自行猜测 actualModel、供应商名或渠道名。
- 报价：按图片、视频、音频分别将完整生成请求 POST 到 https://www.nananobanana.cn/api/skills/images/quote、https://www.nananobanana.cn/api/skills/videos/quote、https://www.nananobanana.cn/api/skills/audio/quote。读取 billing.total_points；kind=prepaid 表示预扣、完成后可能按实际时长结算。报价不创建任务、不扣积分；配置可能变化，提交前重新查询。若返回 skills_quote_unavailable 或接口不可用，明确说明无法确认价格，不得把 pointsCost 或基础单价当成最终报价。

Seedance 参考素材必经流程（安装时必须完整保留，适用于 2.0、2.5 及历史兼容渠道）：
1. 用户的视频参数确定后，读取最新模式详情；本地图片、视频、音频先 presign + PUT，取得 upload.asset_url（HTTP 源地址）。已有可访问的 HTTPS 素材地址可用于首次审核；上传成功不等于审核通过。
2. 将源地址按原顺序放入 images、videos、audios，携带同一模式的完整请求 POST https://www.nananobanana.cn/api/skills/videos/review；三类参考素材都要审核，不能只审核图片。
3. 只有审核 HTTP 2xx、success=true、status=ready，且每个必审输入都返回 status=approved 和非空 asset_uri，才允许生成。assets.images/videos/audios[].source_url 是源地址；asset_uri 才是审核取得的 asset URL，通常为 asset://…，专用人脸渠道按 referenceScheme 返回 face:。不能把 upload.asset_url 当作已审核引用。
4. 将审核返回的 generation_request 原样 POST 到同域 generation_endpoint（/api/skills/videos/generate）；其中 images、videos、audios 已替换为审核引用，保持顺序、模型、模式和参数，不自行拼接 asset://，不换回 HTTP 源地址。收到生成 task_id 后才轮询任务。
5. 审核返回 HTTP 401/403、系统配置错误、拒绝、超时、非 ready 或缺少审核引用/generation_request 时，停止生成并报告实际错误；保留源地址用于按下文恢复，不能改走旧版直接生成来绕过审核。只有明确没有参考素材的纯文字生视频可跳过素材审核。

按请求类型调度：
- 已有视频工具：高清放大、深度提取、视频去字幕使用 POST https://www.nananobanana.cn/api/skills/videos/process，传 operation（upscale / depth / subtitle-erase）、video_url 和本次操作唯一的 idempotency_key；同一次操作重试必须复用此 key。高清放大可选 resolution=720p/1080p/2k/4k，缺省 1080p；其他两项使用租户已有工具配置。去字幕仅整段视频全局智能擦除（subtitle_all_area），不要传 mode、clips、detectRect 或其他选区参数。这三项不需要选择普通生视频模型或输出时长；服务端探测源视频时长并沿用工具栏计费。收到 task_id 后按下述规则轮询，完成前不得宣布成功。
- 视频参数先问清：用户未指定视频模型时，先展示 /api/skills/models 返回的可用视频模型并询问使用哪个模型，同时确认分辨率 resolution 和时长 duration（秒）。三项中任何一项缺失，都先询问缺失项并等待回答，再审核或提交生成；已明确的选项不重复询问，不擅自选择第一个模型或套用 example/default。选定模型后按最新模式 inputSchema 校验；固定值或自动时长（如 duration=-1）要说明含义并确认，不把 -1 当作负一秒，也不添加 Schema 不支持的字段。
- 文字生图：POST https://www.nananobanana.cn/api/skills/generate，只传 model 和 prompt，可选 ratio/size/space_type。
- 参考图生图：仍用 POST https://www.nananobanana.cn/api/skills/generate，把一个或多个 asset_url 放入 input；不要把本地路径或 upload_url 放进去。
- 视频调用详情：选定模型后读取 GET https://www.nananobanana.cn/api/skills/models/video/{modelName}，modelName 使用 models 返回的 name 并 URL 编码；优先直接使用 detailUrl。按 modes[].inputSchema、media、mediaInputReview、promptRequirement 和 example 构造请求；只选 available=true 的模式，未配置或不支持的模式不得猜测。每次新任务重新读取详情，租户配置变化以服务端最新校验为准。
- 文字生视频：POST https://www.nananobanana.cn/api/skills/videos/generate，传 model、prompt、mode 和该模式 inputSchema 允许的参数；duration、resolution、aspect_ratio 的范围按模式详情选择。video_mode 等旧别名仍兼容，新请求统一用 mode，不把通用 supportedModes 当作完整细分模式列表。
- 图片/视频/音频参考生视频：先 POST https://www.nananobanana.cn/api/skills/videos/review 审核，再 POST https://www.nananobanana.cn/api/skills/videos/generate。按模式详情使用 images/videos/audios 三个数组，审核成功后原样提交返回的 generation_request，其中必审素材已换成 asset://… 等审核引用。media_type 只用于上传元数据或旧版素材对象，绝不能加到生成请求顶层。
- 音色设计、声音克隆、TTS 语音合成：POST https://www.nananobanana.cn/api/skills/audio/generate；从 audio[] 选择 capability 分别为 voice_design、voice_clone、tts 的模型。模型的 capability 必须与请求 capability 完全一致。音色设计传 prompt + style，声音克隆传 prompt + reference_audio_url（或 reference_assets），TTS 二选一传 prompt + voice_id，或传 prompt + reference_audio_url；后者的 reference_audio_text 为非必传参数。不要同时传 voice_id 和 reference_audio_url。
- 生成响应中的 task_id 或 skill_task_id 用于 GET https://www.nananobanana.cn/api/skills/tasks/{task_id} 轮询，严格遵守下方“结果轮询”，向用户报告结果或错误。
- 只有用户明确给出 workflow_id 和 node_id 时，才在生成请求中附加 canvas_writeback；需要写回画布时也可调用 POST https://www.nananobanana.cn/api/skills/canvas/writeback 单独写回。

调用示例（所有 JSON 请求都带 Authorization: Bearer bsk__***已打码***）：
GET https://www.nananobanana.cn/api/skills/models
POST https://www.nananobanana.cn/api/skills/generate  {"model":"<image[].name>","prompt":"cinematic product image","ratio":"16:9","size":"2K"}
POST https://www.nananobanana.cn/api/skills/generate  {"model":"<image[].name>","prompt":"edit this reference","input":["<asset_url>"]}
POST https://www.nananobanana.cn/api/skills/videos/review  <使用所选模式详情的 example JSON，替换提示词和 images/videos/audios 中的上传 asset_url>
POST https://www.nananobanana.cn/api/skills/videos/generate  <原样提交审核响应的 generation_request；纯文字模式可直接提交详情 example>
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<voice_design model>","capability":"voice_design","prompt":"你好","style":"温暖、沉稳的青年女声"}
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<voice_clone model>","capability":"voice_clone","prompt":"你好","reference_audio_url":"<asset_url>"}
POST https://www.nananobanana.cn/api/skills/audio/generate  {"model":"<tts model>","capability":"tts","prompt":"你好","voice_id":"<voice-id>"}
GET https://www.nananobanana.cn/api/skills/tasks/{task_id}

结果轮询（图片、视频、音频共用，安装时必须保留这些规则）：
- 任务接口返回 {"success":true,"task":{"status":"completed","result_urls":["…"],"error":null}}。必须先取 task = response.task，再读取 task.status、task.result_urls 和 task.error；不能读取顶层 response.status，也不能把 success=true 当作生成完成。
- 每次循环向 stderr 打印 t=Ns status=xxx（N 为累计秒数）；未识别状态打印 status=unknown，请求错误或超时打印 status=_error。stdout 留给最终结果。
- 命中 completed 立即 return task 并报告 result_urls；命中 failed、cancelled、timeout 等终态立即 return 错误结果（带 _error 和原 task），不得再 sleep 或发起下一轮查询。
- 只有明确的 pending、queued、submitted、processing、running、settling 才是进行中。缺失、空值、unknown、其他未识别 status 或非 JSON 响应绝不能当作进行中：独立累计连续未识别次数，最多诊断重查 3 次（含首次）；第 3 次立即 return {_error:"unrecognized_task_status",task_id,response:<原始响应前 1000 字符>} 并报错退出。读到已识别状态才清零计数，不能兜底成 processing。
- 设置有限总超时和单次 HTTP 超时（例如总计 10 分钟、每次最多 30 秒、间隔 5 秒，单次请求/等待不得超出剩余总时限）。轮询超时必须显式 return {_error:"poll_timeout",task_id}，不能静默结束或当作成功；HTTP 错误、success=false 或网络错误立即返回 _error 并附错误信息。轮询失败不代表服务端任务已取消，保留任务 ID 供之后查询，不自动重新提交生成。下载包 examples/banana-skills-example.mjs 的 pollTask 实现这一契约；外部 Agent 自建轮询也必须遵守。

本地素材流程：先 POST https://www.nananobanana.cn/api/skills/uploads/presign（filename、content_type、size、media_type，支持 image/video/audio），从响应 upload 对象读取 upload_url、headers 和 asset_url；按返回 headers 将原始二进制字节 PUT 到 upload_url，确认 HTTP 2xx 后再使用 asset_url。PUT 不发 JSON、base64 或 multipart，不携带 Skills Authorization。上传只负责存储，不代表图片、视频或音频已过审。upload_url 只用于上传且会过期，不能把 upload_url 传给模型。图片生成和音频合成使用上传 asset_url；参考生视频将其送到 /videos/review。素材已经是 https CDN 地址时可直接使用它进行首次审核；格式不支持时仍需走下述重新上传流程。

视频渠道与素材审核：生成仍调用 https://www.nananobanana.cn/api/skills/videos/generate，由服务端按当前 Skills Key 所属租户和请求模型选择并锁定一个渠道，不会故障转移到其他渠道，过审失败或超时会停止视频提交。审核使用同域 POST https://www.nananobanana.cn/api/skills/videos/review，携带相同 Authorization，接收同一模式的完整请求 JSON（model、mode、prompt 和该 inputSchema 允许的参数/素材）。该接口只审核，不创建生视频任务、不返回 task_id。读取逐模式 mediaInputReview：requirement 表示审核义务，available 表示当前租户能否完成审核，endpoint 是受支持的审核地址，referenceScheme 是审核引用格式。imageInputReview 为旧字段；matchingChannels 为空时不要猜测或探测审核接口，也不能推断为免审。

Seedance 2.0、Seedance 2.5（含历史兼容渠道）的图片、视频和音频都必须在提交前完成审核；审核失败或超时不得提交生成。审核成功响应 status=ready，assets.images/videos/audios 中每项包含 source_url（原上传地址）、asset_uri（审核引用）、status=approved、expires_at。资产审核渠道返回如 asset://asset-20260821042413-7kxg7；仅专用人脸渠道按详情返回 face: 引用。不要拼接或伪造引用。将返回的 generation_request 原样 POST 到 generation_endpoint，必审的 images/videos/audios 已替换为审核引用，绝不换回原 HTTP 地址。审核配置缺失、不兼容或不支持该媒体类型时返回 skills_media_review_unavailable；纯文字请求无需素材审核。服务端保存审核记录，并在生成时校验审核引用的用户、租户、渠道、媒体类型、有效期和通过状态。超时使用同一原上传地址再次调用 /videos/review 继续查询；不存在 task_id 时不能轮询任务。引用失效时用 source_url 重新审核。旧版直接提交上传 URL 仅为服务端兼容行为，新安装的 Agent 必须执行上述先审核后生成流程，不能将旧路径作为审核失败的兜底。

格式不支持的恢复：skills_*_review_failed 且 reason=unsupported_media_format，或消息含 InvalidParameter.FormatUnsupported / Unsupported media format，表示格式或读取失败，不等同于内容审核拒绝。先拿原素材字节重新走 presign + PUT，按真实文件设置 MIME、扩展名和 size，只使用此次返回的新 asset_url 再调用 /videos/review；即使旧素材已经是 CDN 地址也执行此恢复，不重试旧 URL。如果新 URL 仍报格式不支持，检查实际编码/封装和上传响应，不能只凭 .mp4 后缀认定兼容；必要时另存为 H.264、yuv420p、AAC 的 MP4（faststart，不覆盖原文件），再上传新文件并审核一次。上传本身不会转码，转码也不保证供应商接受。仍失败则报告原始错误并停止；内容审核拒绝不得用重新上传或转码来绕过。仅在审核 ready 后生成，收到 task_id 后才开始任务轮询。

Seedance 六种模式以租户实际启用的为准：text2video（文字）、image2video_first（一张首帧）、image2video_first_last（依次首帧和尾帧）、multimodal_ref（图片/视频/音频参考）、video_edit（必须提供参考视频）、video_extend（必须提供参考视频）。Kling v3 Omni 与 RunningHub 的 first_last_frame、image_audio 等模式使用各自详情，不套用 Seedance 入参。先读 schema 再填写时长和比例：Seedance 2.5 编辑 duration=-1、aspect_ratio=adaptive；多模态参考的常规时长和比例按当前详情选择。

如果返回 invalid_skill_key 或 skill_key_revoked，请提示用户重置 Skills Key；model_package_required 请改用 models 返回的可用模型；审核错误按 reason、mediaType、assetIndex 和 recovery 区分上述格式恢复、审核处理中和内容拒绝。不要靠切换兼容字段或添加顶层 media_type 来重试同一失败素材。该安装提示适用于 Codex、Claude Code、WorkBuddy、OpenClaw、Hermes 以及其他支持 Skills 调用的智能体。

请使用opus5.5模型

### Hark · 2026-11-09T03:56:21Z

剧组复工了。3 分钟一推的后台循环和 30 分钟兜底定时任务已重建，Nano Banana 已装好（Key 存保险库，不进公开仓库）。A、B、C、E 四组正按评审意见返工，D 段第三轮评审也派出去了。

### Hark · 2026-11-09T03:59:49Z

D 段第三轮出分了：84，只差 1 分。八项都过了 70%，也没有不可交付镜头，卡在重复：S27、S24、S21/S22 复用了前面的画面，字砖墙又和副歌一撞了。D 组已经按这四条开始返工。

### 用户 · 2026-11-09T04:02:04Z

哦对了，信息改成 鬼屠 · 第二季

### Hark · 2026-11-09T04:02:49Z

收到，片名改成「鬼屠 · 第二季」。文档和旧版片头已经改好并推送；片头 A06 和片尾 E30 这两个片名镜头已交给 A、E 两组，在这一棒里一起改。

### Hark · 2026-11-09T04:15:49Z

A、E 两组的第五棒都交片了，片名也都已改成「第二季」。A06 和 E30 里的「二」笔画少，字号放大了一点，左右两字也往中间收了。两组都已送去第三轮独立评审。

### Hark · 2026-11-09T04:19:26Z

A、E 第三轮还是没过：A 72 分，E 72.5 分，两组都卡在「不重复」。E08 的太上皇特写换成了另一个人，E02、E20 和副歌一撞了画面，A 组则是 V08、V09、V17 不可交付。两组已经开始第六棒返工，这次还会出低清动态片给评审看。

### Hark · 2026-11-09T04:22:59Z

片名已经全部改成「鬼屠 · 第二季」，包括片头 A06、片尾 E30 和文档，都已推送。五组目前还没有一组过线，各组进度和下一步请看下表。

### Hark · 2026-11-09T04:22:59Z

### 各组进度（11-09 12:22）

| 组 | 最新评审 | 当前状态 | 积分 | 接手下一步 |
| --- | --- | --- | --- | --- |
| A 前奏+主歌一 | 72（第三轮） | 第六棒：4 张图已提交生成，镜头未改 | 57/80 | 取图，改 V08/V09/V17 |
| B 导歌一+主歌二 | 约 73 | 第五棒返工仍在跑 | — | 等交付后送评审 |
| C 导歌二+副歌二 | 69 | 第五棒返工仍在跑 | — | 等交付后送评审 |
| D 桥段 | 84（第三轮） | P0/P1 全改完，联系表 v8 已出 | 45/80 | 补 keys v5 和 HANDOFF，送第四轮 |
| E 尾段 | 72.5（第三轮） | 第六棒：4 张图已提交生成，镜头未改 | 54/80 | 取图，改 E08/E02/E20 |
