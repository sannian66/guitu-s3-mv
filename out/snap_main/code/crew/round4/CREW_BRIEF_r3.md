# 第三棒任务书（2026-11-09 10:05 CST，第六任总导演，新沙箱）
你是《谁定正邪》MV 第四轮剧组的 <组> 组，接手本组第二棒。仓库：/workspace/work/mv（= sannian66/guitu-s3-mv，GitHub 公开仓库；软链到 /workspace/projects/5196904f-65f8-48f0-848c-4c03aa77b35b/guitu-s3-mv）。环境（numpy/cv2/skia/librosa、libegl1/libgl1、hooks）已装好。

## 先读
1. crew/round4/CHARTER.md（地盘、接口、评分表、提交规则、CPU 规则）——全部遵守。
2. crew/round4/HANDOFF_r2.md 本组一节（第二棒停在哪、自评弱点、下一步）。
3. 已评过分的组：crew/round4/critic_<组>_r1.md（评审意见，按 P0→P1→P2 顺序返工，P0 与「不可交付镜头」必须全部解决）。未评的组：crew/round4/critic_baseline.md 本段扣分点。
4. units/chorus1.py（标杆，只读）。

## 这一棒要交付
1. 返工 / 补完 units/sec_<key>.py，逐镜单帧试渲确认跑通。
2. 全段共性问题（评审在 C/D/E 都扣了）一律避免：
   - 白闪转场：全段 flash_white 最多 1 处；转场中间帧不得是纯白/纯灰/纯黑/灰雾，必须带前后镜的画面元素。whip_pan_blur 最多 1 处。
   - 构图套路：「人物居中小剪影 + 程序天空/漩涡/云底」全段最多 2 镜；换大俯、大仰、前景遮挡、纵深。
   - 歌词：字幕安全区（有效画面 1920×840 内四边留 ≥60px），不裁字、不残字、不压脸、灰对灰不可读的要加暗衬/描边；停用角落小竖排；一句短语在一镜内读完。
   - 程序化军阵/道具不能是白模几何体或黑团块：要有轮廓光、材质、层次，否则改成精灵或换构图。
   - 人物身份一致（鬼屠：高马尾、中分乱刘海、琥珀眼、苍白清瘦、黑衣暗红内领）。
3. 联系表 v(N+1) + keys v(N+1)（用本组脚本 tools/<组小写>_contact.py，外面包 tools/cpu_slot.sh），自己 read_file 看图挑毛病再改至少一轮。
4. 更新 crew/round4/<组>_storyboard.md（返工记录 + 接缝 + 未决）。
5. 需要新精灵：python3 tools/nb.py（先 quote 再生成再轮询；Key 由代理注入，绝不写进文件）。若 nb.py 报认证/Key 缺失，不要折腾，改用现有精灵并在 HANDOFF 写明。每张记 crew/genlog.md；本组积分上限 80（含已用）。

## 防丢进度（用户硬要求）
- 每完成一个可见步骤立刻提交并推送：`git add <自己的路径> && GIT_AUTHOR_NAME=sannian66 GIT_AUTHOR_EMAIL=38859572+sannian66@users.noreply.github.com GIT_COMMITTER_NAME=sannian66 GIT_COMMITTER_EMAIL=38859572+sannian66@users.noreply.github.com git commit -m "[<组>组] ..." -- <自己的路径>`。post-commit hook 自动推送；每个 git 命令的 shell 调用必须带 credentials [{"provider":"github"}]。看到 PUSH FAILED 立刻 pull --rebase 处理。禁止 git add -A / commit -a / autosync.sh。
- 至少每 10 分钟有一次提交；长渲染每完成一块就提交中间产物。

## 停下的条件
- 同一个报错修两次还不过，记进 storyboard「未决」并跳过，别死循环。
- 完成或时间不够时：在 crew/round4/HANDOFF_r3.md 追加本组一节（做了什么、积分、联系表路径、对照评审逐条的处理结果、自评弱点、下一步），提交推送后回报总导演。
