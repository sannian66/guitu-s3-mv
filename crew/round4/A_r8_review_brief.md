# A 段第八轮独立评审简报（交给全新上下文的评审子代理；由总导演派）

只给评审以下材料，不给代码、storyboard、HANDOFF、组内自评：
1. `crew/round4/CHARTER.md` 的「硬性质量要求」「评审」两节。
2. A 新三张表：
   - 联系表 `out/round4/A_contact_v10_p0.jpg`、`A_contact_v10_p1.jpg`（每镜 55% 处一帧，29 镜）
   - 关键帧 `out/round4/A_keys_v9_p0–p3.jpg`（100 格：全部非硬切转场中点 + 上轮点名的关键帧 + 本棒改动点起/止）
   - 节奏表 `out/round4/A_rhythm_v4_p0–p5.jpg`（每镜起/中/止，一行一镜；p3 后半起为上轮错读时刻的**逐帧核对**：V01止/V02起 16.70–17.20、V02止/V03起 17.60–18.20、V03止 19.20–19.80、V20止/V21起 42.30–42.85，每帧一格）
3. 标杆：`out/chorus1_v3_contact.jpg`。
4. `crew/round4/critic_A_r7.md`（只用于核对上轮整改）。
5. 用户原话：「我希望你像剧组一样开工，做吧，打分，高质量交付，获奖级别」。

要求：
- 可用 `tools/cpu_slot.sh python3 tools/a_peek.py <out.jpg> <秒> ...` 补渲单帧（`FULL=1` 另存全尺寸 `/tmp/ap_<秒>.png`）。
- 重点核对（critic_A_r7 的「下轮要看到的」）：V01 止 16.85 / V02 起 17.11 / V03 起 18.10、止 19.61 / V20 止 42.54 单帧原样放大，屏上文字是否始终按歌词顺序、无错读；V06 起/止（21.22 / 22.45）叠图的环绕视差；V04 起/止（19.70 / 20.62）机位运动；V02 起/止（17.05 / 17.85）位移；V19（40.95 / 41.65）方向；V16（36.80 / 37.60）人物立场；V10 倒影（27.60 / 27.98）；V17 起 38.27；Cait 5.00。
- 写 `crew/round4/critic_A_r8.md`（8 项分数表、过线判定、不可交付镜头、与 r7 相比是否退步、返工清单），只提交该文件：
  `git add crew/round4/critic_A_r8.md && git commit -m "[评审] A 组第八轮 N 分" -- crew/round4/critic_A_r8.md`（shell 带 github credentials）。

底线：r7 为 **86**。若低于 86 或判定退步，A 组回退到本棒开始时的提交 **2aa55eb**：
`git checkout 2aa55eb -- units/sec_a_intro_verse1.py tools/a_contact.py`（或按评审逐条回退退步镜头）。
