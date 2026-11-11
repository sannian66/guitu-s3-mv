# 第八轮风格 D · A1 单元（片头 + 主歌一前半，A01–V07）生图记录

nananobanana RH_image2，2K 16:9，3 积分/张。提示词 `jobs/r8_D_A1.json`（PLAN_r8 第五节头段 + Scene + 尾段 + Reminder；鬼屠加鬼屠定妆照 input，太上皇加太上皇定妆照 input）。候选原图在仓库外 `~/Downloads/gen_cands/R8_D/A1/`；入库的只有用到的背景板和 `_cut.png`。

| 时间 | 名 | 模型 | 规格 | 积分 | task_id | 状态 | 文件 | 备注 |
|---|---|---|---|---|---|---|---|---|
| 11-11 12:31 | R8_D/A1/A01_bg | RH_image2 | 2K 16:9 | 3 | 8910883b-4cb2-4923-bed6-62d135832733 | ✔ 采用 | assets/gen/R8_D/A1/A01_bg.png | 纯文生图 try1； |
| 11-11 12:33 | R8_D/A1/A01_ridge | RH_image2 | 2K 16:9 | 3 | 58b8c6d1-5ff8-444e-910a-3a592ec20995 | ✔ 采用 | assets/gen/R8_D/A1/A01_ridge_cut.png | 纯文生图 try1； |
| 11-11 12:32 | R8_D/A1/A02_bg | RH_image2 | 2K 16:9 | 3 | e6eeb2c2-e1bf-4d02-b8bf-123d7e5420c7 | ✔ 采用 | assets/gen/R8_D/A1/A02_bg.png | 纯文生图 try1；A02 / A06 共用（A06 镜像、换裁切） |
| 11-11 12:33 | R8_D/A1/A02_hero | RH_image2 | 2K 16:9 | 3 | b5630112-6057-4aa5-b0d1-cc3b791cd984 | ✔ 采用 | assets/gen/R8_D/A1/A02_hero_cut.png | 定妆照参考 try1； |
| 11-11 12:34 | R8_D/A1/A03_sword | RH_image2 | 2K 16:9 | 3 | 8d919606-0897-47e9-848a-a96fadcdbbf3 | ✘ 弃用 | — | 定妆照参考 try1；SPREAD §11 返工：原图是武士刀圆刀镡 + 菱形缠柄 → 弃用，见 @s11 |
| 11-11 12:35 | R8_D/A1/A04_face | RH_image2 | 2K 16:9 | 3 | 475aee5e-c164-4ea0-9f25-d1ae130fe117 | ✔ 采用 | assets/gen/R8_D/A1/A04_face_cut.png | 定妆照参考 try1； |
| 11-11 12:34 | R8_D/A1/A05_eyes | RH_image2 | 2K 16:9 | 3 | 00af4388-ec05-4c81-a447-91b051ee262c | ✔ 采用 | assets/gen/R8_D/A1/A05_eyes.png | 定妆照参考 try1； |
| 11-11 12:35 | R8_D/A1/A06_title | RH_image2 | 2K 16:9 | 3 | cb674cb0-c7e7-4b79-b9db-ba82a5082cbe | ✔ 采用 | assets/gen/R8_D/A1/A06_title_cut.png | 纯文生图 try1；画进生图的片名：鬼屠·第二季 / 主题曲《谁定正邪》/ 印「鬼屠」，逐字放大核对无错字缺笔；抠像改用纯色键（cutout_green 的小连通域过滤会吃掉副标题细笔画） |
| 11-11 12:35 | R8_D/A1/A07_sky | RH_image2 | 2K 16:9 | 3 | d805fa88-a584-430f-bf6d-5ecafab386c7 | ✔ 采用 | assets/gen/R8_D/A1/A07_sky.png | 纯文生图 try1； |
| 11-11 12:35 | R8_D/A1/A07_tower | RH_image2 | 2K 16:9 | 3 | d283e200-655a-4323-b66b-6652bb6eaaac | ✔ 采用 | assets/gen/R8_D/A1/A07_tower_cut.png | 纯文生图 try1； |
| 11-11 12:37 | R8_D/A1/A08_walk1 | RH_image2 | 2K 16:9 | 3 | 2beb2853-ac67-45f7-a74b-091d0ae3636f | ✔ 采用 | assets/gen/R8_D/A1/A08_walk1_cut.png | 定妆照参考 try1； |
| 11-11 12:36 | R8_D/A1/A08_walk2 | RH_image2 | 2K 16:9 | 3 | dc213c8d-96a8-4978-9626-dd3f5d82088a | ✔ 采用 | assets/gen/R8_D/A1/A08_walk2_cut.png | 定妆照参考 try1； |
| 11-11 12:37 | R8_D/A1/A08_out | RH_image2 | 2K 16:9 | 3 | 04d56d55-81dc-4a7c-9e00-d82860febf6d | ✔ 采用 | assets/gen/R8_D/A1/A08_out.png | 纯文生图 try1； |
| 11-11 12:37 | R8_D/A1/A08_wall | RH_image2 | 2K 16:9 | 3 | 4db004bb-30e2-4b1f-ac66-4912fe0ae7f1 | ✔ 采用 | assets/gen/R8_D/A1/A08_wall_cut.png | 纯文生图 try1； |
| 11-11 12:37 | R8_D/A1/A08_door | RH_image2 | 2K 16:9 | 3 | 96576953-db0c-4fba-8c96-3aef94565c84 | ✔ 采用 | assets/gen/R8_D/A1/A08_door_cut.png | 纯文生图 try1； |
| 11-11 12:39 | R8_D/A1/V01_bg | RH_image2 | 2K 16:9 | 3 | 9f51de53-3a5b-4e7c-a5b6-0e2d9cc73912 | ✔ 采用 | assets/gen/R8_D/A1/V01_bg.png | 纯文生图 try1； |
| 11-11 12:38 | R8_D/A1/V01_blade | RH_image2 | 2K 16:9 | 3 | 52058f47-90bc-426f-8e1b-6574e7fa3609 | ✔ 采用 | assets/gen/R8_D/A1/V01_blade_cut.png | 纯文生图 try1； |
| 11-11 12:38 | R8_D/A1/RAIN_fg | RH_image2 | 2K 16:9 | 3 | cda5b30d-e0a9-40c4-9aee-1aedb07321d6 | ✔ 采用 | assets/gen/R8_D/A1/RAIN_fg_cut.png | 纯文生图 try1；A07a / A08 / V01 / V02 / V04 共用的前景雨 |
| 11-11 12:38 | R8_D/A1/V02_bg | RH_image2 | 2K 16:9 | 3 | bd82af3a-8827-4578-bec1-5dfb4f030177 | ✔ 采用 | assets/gen/R8_D/A1/V02_bg.png | 纯文生图 try1； |
| 11-11 12:39 | R8_D/A1/V02_boot1 | RH_image2 | 2K 16:9 | 3 | a08dff41-3781-412c-b9d5-b9882d74065f | ✔ 采用 | assets/gen/R8_D/A1/V02_boot1_cut.png | 定妆照参考 try1； |
| 11-11 12:39 | R8_D/A1/V03_army | RH_image2 | 2K 16:9 | 3 | 16e0dc4f-ce17-4911-9433-981a14767b01 | ✔ 采用 | assets/gen/R8_D/A1/V03_army.png | 纯文生图 try1； |
| 11-11 12:41 | R8_D/A1/V04_bg | RH_image2 | 2K 16:9 | 3 | 7adea0b2-9d6e-48ea-9bbf-02d5efe73e24 | ✔ 采用 | assets/gen/R8_D/A1/V04_bg.png | 纯文生图 try1； |
| 11-11 12:40 | R8_D/A1/V04_walk1 | RH_image2 | 2K 16:9 | 3 | 9935601d-b131-491d-8845-3d2f5e273f85 | ✔ 采用 | assets/gen/R8_D/A1/V04_walk1_cut.png | 定妆照参考 try1； |
| 11-11 12:40 | R8_D/A1/V04_walk2 | RH_image2 | 2K 16:9 | 3 | be7d9fe0-3c47-48b6-b710-e5b90c260967 | ✔ 采用 | assets/gen/R8_D/A1/V04_walk2_cut.png | 定妆照参考 try1； |
| 11-11 12:42 | R8_D/A1/V05_draw | RH_image2 | 2K 16:9 | 3 | 22b7acef-c958-4b20-9102-3ebee62dcf13 | ✘ 弃用 | — | 定妆照参考 try1；SPREAD §11 返工：同上（武士刀刀镡 / 菱形缠柄）→ 弃用，见 @s11 |
| 11-11 12:41 | R8_D/A1/V06_bg | RH_image2 | 2K 16:9 | 3 | eace8131-4f4d-4f27-ae79-fecf4084c79e | ✔ 采用 | assets/gen/R8_D/A1/V06_bg.png | 纯文生图 try1； |
| 11-11 12:42 | R8_D/A1/V06_wind | RH_image2 | 2K 16:9 | 3 | 80cd808e-02f2-47d6-976d-aef605389669 | ✔ 采用 | assets/gen/R8_D/A1/V06_wind_cut.png | 定妆照参考 try1； |
| 11-11 12:42 | R8_D/A1/V06_slashA | RH_image2 | 2K 16:9 | 3 | d8bc9320-f2f3-46f6-bb26-a369bd605259 | ✔ 采用 | assets/gen/R8_D/A1/V06_slashA_cut.png | 定妆照参考 try1； |
| 11-11 12:43 | R8_D/A1/V06_slashB | RH_image2 | 2K 16:9 | 3 | 48b911ea-0e3a-4d77-9098-4689a1651a0f | ✔ 采用 | assets/gen/R8_D/A1/V06_slashB_cut.png | 定妆照参考 try1； |
| 11-11 12:43 | R8_D/A1/V06_fg | RH_image2 | 2K 16:9 | 3 | 827be44d-6765-4641-ab3a-1c68fbcc4eb4 | ✘ 弃用 | — | 纯文生图 try1；跑偏：画成了带人物和红天的整幅场景，不能当前景枪林用 |
| 11-11 12:43 | R8_D/A1/V07_bg | RH_image2 | 2K 16:9 | 3 | 3f210e20-9f2d-4af9-9527-77f940f07f47 | ✔ 采用 | assets/gen/R8_D/A1/V07_bg.png | 纯文生图 try1； |
| 11-11 12:44 | R8_D/A1/V07_emperor | RH_image2 | 2K 16:9 | 3 | 1f70adcb-da11-4157-a631-fe855e8b65e9 | ✘ 弃用 | — | 纯文生图 try1；太上皇形象与官方设定不符（白须 + 皇冠 + 龙袍，纯文字描述没带定妆照）→ 弃用，见 @tsh1 |
| 11-11 12:47 | R8_D/A1/V06_fg@try2 | RH_image2 | 2K 16:9 | 3 | 9a2af9b5-c55e-4abc-8f19-422a69882f8b | ✔ 采用 | assets/gen/R8_D/A1/V06_fg_cut.png | 纯文生图 try2；try2：Scene 改成「只画 6 根枪杆，其余全绿」后可用 |
| 11-11 12:57 | R8_D/A1/V07_emperor@tsh1 | RH_image2 | 2K 16:9 | 3 | e8b8fd96-1102-4bd6-9c98-38df6f60c33b | ✔ 采用 | assets/gen/R8_D/A1/V07_emperor_cut.png | 定妆照参考 tsh1；**太上皇定妆照返工**：input = 太上皇风格 D 定妆照（无须无冠、小髻黑簪、黑纱宽袖、暗血红腰带长穗）；抠像后去掉生图自带的台阶（V07 用自己的宫阶背景板） |
| 11-11 15:21 | R8_D/A1/A03_sword@s11 | RH_image2 | 2K 16:9 | 3 | 9d15c38d-9934-46c8-ab51-479266a3f990 | ✔ 采用 | assets/gen/R8_D/A1/A03_sword_cut.png | 定妆照参考 s11；**SPREAD §11 刀统一**：直刀 + 中式护手 + 黑柄环首 + 刀鞘红穗 |
| 11-11 15:22 | R8_D/A1/V05_draw@s11 | RH_image2 | 2K 16:9 | 3 | f91a024a-33f7-40e0-830c-544faa3ecba2 | ✔ 采用 | assets/gen/R8_D/A1/V05_draw_cut.png | 定妆照参考 s11；**SPREAD §11 刀统一**：同上 |
| 11-11 15:22 | R8_D/A1/CU_bg1@s11 | RH_image2 | 2K 16:9 | 3 | bc21f2df-71c9-4f3c-aefd-8816c56044ce | ✔ 采用 | assets/gen/R8_D/A1/CU_bg1.png | 纯文生图 s11；SPREAD §11：特写背景不再用虚焦复用的血月板；A03 / V05（翻转 + 换裁切）共用 |
| 11-11 15:23 | R8_D/A1/A04_bg@s11 | RH_image2 | 2K 16:9 | 3 | c6a5f12b-f6fa-47ff-8396-0e15329b5610 | ✔ 采用 | assets/gen/R8_D/A1/A04_bg.png | 纯文生图 s11；SPREAD §11：A04 原用虚焦血月板 → 清晰风云板 |

合计 38 张 × 3 = **114 积分**（单元预算 120；含太上皇定妆照返工 1 张、SPREAD §11 返工 4 张）。
