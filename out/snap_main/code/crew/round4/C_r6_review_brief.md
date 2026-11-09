# C 段第六轮独立评审简报（交给全新上下文的评审子代理）

只给评审以下材料，不给代码、storyboard、HANDOFF：
1. `crew/round4/CHARTER.md` 的「硬性质量要求」「评审」两节。
2. C 新联系表 `out/round4/C_contact_v10_p0–p3.jpg`、新关键帧 `out/round4/C_keys_v7_p0–p5.jpg`。
3. 对比用：`out/round4/C_contact_v9_p0–p3.jpg`（以及 `C_keys_v6_p0–p5.jpg`）。
4. 标杆：`out/chorus1_v3_contact.jpg`。
5. `crew/round4/critic_C_r5.md`（只用于核对整改）。
6. 用户原话：「我希望你像剧组一样开工，做吧，打分，高质量交付，获奖级别」。

要求：可用 `tools/cpu_slot.sh` 包 `tools/c_peek.py` 补渲单帧；写 `crew/round4/critic_C_r6.md`（分数表 8 项、过线判定、不可交付镜头、与 v9 对比是否退步、返工清单）；只提交该文件：
`git add crew/round4/critic_C_r6.md && git commit -m "[评审] C 组第六轮 N 分" -- crew/round4/critic_C_r6.md`（shell 带 github credentials）。
底线：r5 为 88.0。若低于 88 或判定退步，C 组回退到 v9 对应代码（ca048e5 的 units/sec_c_pre2_chorus2.py、units/c_kit.py）或逐条回退退步镜头。
