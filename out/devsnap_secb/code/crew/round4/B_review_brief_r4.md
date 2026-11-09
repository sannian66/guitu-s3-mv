# B 组第四轮独立评审 · 派发简报（第十棒组长写，供 run_subagent 原样转交）

> 第十棒组长的工具里没有 run_subagent，无法自己派评审。请总导演用**全新上下文**的子代理派出，只给下面这些，不给设计说明。

## 给评审的材料（只这些）
1. 评分规则：`crew/round4/CHARTER.md` 的「硬性质量要求」「评审」两节。
2. B 组新三张表：
   - 联系表 `out/round4/B_contact_v7_p0.jpg` … `_p4.jpg`（40 镜中点）
   - 关键帧 `out/round4/B_keys_v7_p0.jpg` … （转场中间帧 + 歌词关键帧 + 本轮复核帧）
   - 节奏表 `out/round4/B_rhythm_v2_p0.jpg` … （每镜起 / 中 / 止）
3. 标杆：`out/chorus1_v3_contact.jpg`。
4. `crew/round4/critic_B_r3.md`：**只用来核对整改**，不照抄分数。
5. 用户原话：「我希望你像剧组一样开工，做吧，打分，高质量交付，获奖级别」。

## 允许的操作
- 用 `tools/cpu_slot.sh python3 tools/b_peek.py out.jpg f1 f2 …` 补渲单帧（FULL=1 存全尺寸 /tmp/bp_<f>.png，可裁剪放大看手）。帧号：b_pre1 1321–1784，b_verse2 2586–3534（30fps）。
- 只杀自己的进程（方括号写法）。

## 产出
- 写 `crew/round4/critic_B_r4.md`：总分、八项分数表、70% 线、是否有「不可交付」镜头、P0/P1/P2 返工清单。
- 自行提交推送：`git add crew/round4/critic_B_r4.md && git commit -m "[评审] B 组第四轮 …" -- crew/round4/critic_B_r4.md`（shell 带 github credentials；PUSH FAILED 就 `git pull --rebase --autostash origin main && git push origin HEAD:main`）。禁止 git add -A。

## 过线
总分 ≥85、每项 ≥70%、无不可交付 → B 组把 `units/sec_b_pre1.py`、`units/sec_b_verse2.py` 的 READY 设 True。
