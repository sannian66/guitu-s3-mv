# 角色库 API（美术·角色组）

供各摄制组调用。所有组件都是**帧级可动画**：给绝对时间 `t`（秒）或进度参数（0..1），不依赖逐帧状态（例外：`Swordsman`/`Emperor` 的布料与头发按 `pose(t)` 连续积分，跳帧时先用递增 t 预跑几十帧）。
画布：`fr` 为 `float32 (1080,1920,3)` RGB 0..1，含黑边；函数原地修改并返回 `fr`（或 `(fr, info)`）。色板只用黑白灰 + `RED (0.72,0.06,0.05)` + `GOLD (1.0,0.76,0.40)`。

## 环境要求（新增）
- 绘制层已换成 **Skia 矢量路径**（skia-python）：解析抗锯齿、贝塞尔曲线、渐变填充、MaskFilter 模糊、描边边缘光。
- 安装：
  ```bash
  pip install --user -q numpy pillow scipy opencv-python-headless skia-python
  sudo apt-get install -y libegl1 libgl1     # skia-python 依赖的系统库
  ```
- 没有 skia 时 `rig` / `crowd` 自动回退到旧版 cv2 光栅（接口不变，画质略低）；`paper` / `props` 必须要 skia。
- 导入：`sys.path.insert(0, '/workspace/work/mv/lib')`，然后 `import rig, crowd, paper, props, fx2, sk`。
- 前后对比：`rig.set_backend('cv'|'skia')`、`crowd.set_backend(...)`；对比图 `lib/rig_test/skia_cmp_*.png`、`skia_cmp_crowd.jpg`。

## 性能（process time，2 核，1080p 单帧，缓存已热）
| 组件 | 典型耗时 |
|---|---|
| Swordsman 全身 900px | ~0.10s |
| profile_cu 头部特写 560px | ~0.3–0.55s（最重，同帧别再叠重物） |
| Emperor 950px | ~0.11s |
| Army 500 人（景深分层） | 0.2–0.35s |
| PaperCrowd 27 人 | ~0.35s；PaperGiant 0.1–0.22s |
| Blade 0.07s（heat 时 0.3s） | CharWall 0.04s（崩塌 0.2s） |
| fx2 雨幕 0.03–0.08s，闪电 0.05s，裂缝金光 0.1s，余烬 0.05s，雾 0.03s |

---

## lib/rig.py —— 鬼屠 / 太上皇 / 特写（接口未变）
- `Swordsman(seed, view='side'|'3q'|'back'|'front'|角度, hair=1.0, ribbons=True)`
  - `pose(action, phase, t, wind=0, flip=None, view=None, sword=None, **over)` → 骨骼
  - `draw(fr, x, y, scale, rim_color, rim_dir, rim, lift, alpha, heat, shine, glint, ...)` → `(fr, info)`；`info['guard'], info['tip']` 供刀光
  - 动作（19）：`stand_wind walk run draw_sword slash_h slash_diag slash_up spin_slash leap land_kneel sword_plant look_up turn_head raise_sword_sky sheath fall_back_recover sword_on_shoulder hold_overhead_strain blade_horizontal_chest`
- `blade_trail(fr, history[(guard,tip)...], color, intensity, glow, edge_color, mode='light'|'ink')` —— skia 版用带逐顶点颜色的三角网格画扫掠面（无条纹缝）
- `profile_cu(fr, sw, t, cx, cy, head_px, light='moon'|'dawn', glint, flip, action, wind, wet)`
- `HandCU(seed).draw(fr, mode='grip'|'thumb_push'|'open_rain', prog, t, x, y, size, angle, flip, wet, heat, ...)`
- `Emperor(seed, view, crown='mian')`：`pose(action, phase, t, wind)`、`draw(fr, x, y, scale, rim_color, rim_dir, paper=0..1, burn=0..1, ...)`；动作 `stand_backlit raise_hand_decree point_down grip_scepter head_turn_flash`
- `rig.set_backend('skia'|'cv')`，`rig.BACKEND`

## lib/sk.py —— Skia 绘制层（给需要自己画形状的组）
- `SkCanvas(h,w)`：与旧 `_Canvas` 同接口（`poly/cap/circ/ell/line/strand/ribbon` + `fill/stroke/fill_ell(target,...)`）
- 路径：`path_poly(pts, closed, smooth)`、`path_circle`、`path_ellipse`、`path_capsule_union`、`path_stroke`
- `FloatSurface(h,w)`：RGBA_F32 面；`.path(P, color, alpha, blur, blend='plus'|'src'|'screen', shader, stroke)`、`.mesh(pos, cols, idx)`
- `linear_gradient / radial_gradient`、`mask(h,w,paths,blur,stroke)` → float 覆盖率

## lib/crowd.py —— 军阵 / 群像
- `Army(seed=0, rows=20, cols=25, dx=1.5, dz=1.7, weapon='spear'|'dao', view='front'|'side', rim_dir, banners=12, torches=40)` （init ~1.9s，预画 24 种姿态精灵）
- `draw(fr, t, cam=dict(x,y,z,pitch,f), advance=0, march=1, cadence=1.075, raise_=0, level=0, kneel=0, kneel_wave=0.6, part=0, focus=None, dof=1, rim_color, rim, fog_color, fog_dist=110, glint=1, wind=1, torch=1, sync=0.06, flip=False, origin=(0,0,12), alpha=1)` → `(fr, info)`
  - 推拉：改 `cam['z']`（米）；俯拍：`y` 高 + `pitch` 大（S009：`dict(x=0,y=26,z=-14,pitch=32,f=1400)`）；前排低机位：`dict(x=1.5,y=1.4,z=4,pitch=-4)` + `focus`
  - `march` 齐步（全体同相 ±sync），`raise_` 举兵器（波浪 0.015/排），`level` 平枪冲锋，`kneel` 跪（前→后、中→侧波浪），`part` 中线让路（S122）
  - 甲光：护心镜/盔顶/枪尖随机闪烁；旗帜（朱/黑，金边）行波飘动；火把金色点光；大气透视 + 分 slab 景深
  - 侧面冲锋（S072）：`Army(seed, rows=8, cols=12, view='side')` + `level=1, cadence=2.0`，左翼用 `flip=True`
- `soldier_sprite(phase, arm, kneel, bow, weapon, view, level)` 单兵精灵
- `Kneelers(seed, n=40, spread, y_base=900, scale, depth_rows=3)`；`draw(fr, t, kneel=1, bow=0..1, wave=0.4, sway=1, rim_color=GOLD, rim, x_off, scale, dof, fog_color)` 平民跪地/叩首剪影

## lib/paper.py —— 纸人 / 纸糊巨影 / 木偶 / 皮影
- `PaperFigure(seed, view='side'|'front', cheeks=True)`；`draw(fr, x, y, height, t, bow, sway, wet, burn, burn_origin, card, tilt, flip, light='back'|'front', light_color, rim, alpha, blur, strings=(x,y)|None, ink)` → `(fr, info)`
- `PaperCrowd(seed, rows=3, cols=9, view, x_span, y_front, h_front)`；`draw(fr, t, bow, wave, wet, strings, string_alpha, burn, fall, light, light_color, dof, rim, x_off)`（S049 鞠躬 / S052–53 雨湿 / S062 提线）
- `draw_strings(fr, attach_pts, control, t, color=RED, alpha, width, cut=0..1, cut_y)` 红丝线（断线回弹）
- `Marionette(seed, style='paper'|'piying')`；`draw(fr, x, y, height, t, ctrl, lift, dance, cut, strings, light_color, rim, alpha, blur, flip, screen)`（S066 斩线：`cut` 0→1）
- `PaperGiant(height=1500, seed, emperor=None, action='stand_backlit', phase)`；`draw(fr, t, x, y(脚底), reveal=0..1, burn=0..1, burn_origin=(0.5,0.12), light_color, backlight, sway, frame_lines, alpha, hole_color, flakes)`（S116 reveal → S117 burn；返回 `info['burn_front']`）
- `PaperShreds(seed, n=120, size)`；`draw(fr, t, t0, origin, spread, to_camera=0..1, gravity, wind, burn, light_color, backlit, dof, emit=点列, scale, amount)`（S118/S119 纸片飞向镜头）
- `PaperCurtain(seed, n=14, x_span, top, length, width, text=True)`；`draw(fr, t, wind, light_color, backlit, cuts=[(p0,p1,t_cut)], alpha, depth_blur)`（S115 纸帘 / S118 交叉两刀斩断）

## lib/props.py —— 道具
- `Blade(seed, curve=0.035)`；`draw(fr, t, p0(护手), p1(刀尖), width, heat, sheen, blood, beads, wet, steam, frost, engrave, engrave_p, edge_up, moon, sparks, haze, glow)` → `(fr, info)`
  - S003/S006 `sheen` 扫光；S015/S103 `engrave='…'`+`engrave_p`；S026 `heat=0.9`；S027 `heat=1`+haze；S028/S038 `blood`；S067 `heat=0.6, steam=1`；S089 `beads=9, wet=1`；S008 `frost`
- `Balance(seed, people=60)`；`draw(fr, t, cx, cy, size, tilt, sway, left_people, right='seal'|'people', right_people, break_, drip, rim_color, rim, alpha, blur)`（S012/S013/S052/S091/S096）
- `Scroll(seed, lines, title='大局', font_)`；`draw(fr, t, cx, cy, w, h, unroll, type_, tear, angle, seal, alpha)`（S061）
- `GiantSeal(text, seed)`；`draw(fr, t, cx, cy, size, fall, tilt, split, split_angle, show_face, rim_color, rim, motion_blur, alpha)`（S017/S019/S085–S087）
- `seal_face(text, size, style='zhu'|'bai', wear, seed, fname)` → RGBA；`stamp_imprint(fr, face, cx, cy, size, prog, angle, alpha)`（S040 田字格四印）
- `CharWall(seed, cols=16, rows=12, brick=(150,64), text=None, chars_ratio, fname='song')`；`draw(fr, t, x0, y0, x1, y1, tilt, rise, crack=CrackLight, crack_kw, collapse, collapse_center, light_color, rim, fog, alpha)`（S033 rise / S034 tilt / S036 crack / S076–S080 collapse / S104）
- `Plaque(text='天理昭彰', seed, fname)`；`draw(fr, t, cx, cy, w, crack, light_color, sheen, tilt, alpha)`（S022「规矩」/ S114）
- `text_path(ch, fname('song'|'kai'|'xing'|'cao'), size, cx, cy)` 单字 skia 路径

## lib/fx2.py —— 雨光特效
- `RainSheet(seed, density)`；`draw(fr, t, intensity, angle, color, light=(x,y), light_r, red=0..1(血雨), freeze=0..1(悬停雨珠), layers, cam)` 四层景深雨
- `Splashes(seed).draw(fr, t, y_far, y_near, x0, x1, rate, color, size, puddle, amt)`；`ripples(fr, t, centers, t0s, ...)`
- `Lightning(seed, p0, p1, branches, rough, depth, gold)`；`draw(fr, t, t0, intensity, color, grow, sky, width, glow)`；`env(t,t0)` 亮度包络（给角色补光）
- `cloud_flash(fr, t, t0, center, radius, seed, intensity, env, mask)` 云内亮/预亮
- `god_rays(fr, src, emit, strength, length, color, t, shafts, src_r, occluder)` 体积光（可用剪影 alpha 作 occluder）
- `light_beam(fr, p0, p1, w0, w1, t, color, strength, dust, stripes)` 丁达尔光束
- `CrackLight(seed, p0, p1, rough, branches)`；`draw(fr, t, prog, open_, spill, color, motes, wall_dark)`；`mask(prog, open_)`（S036/S130 金光喷涌：`open_=2–3`）
- `Embers(seed, n, box, mode='fire'|'gold'|'ash', rise, life)`；`draw(fr, t, intensity, wind, t0, burst=(x,y,速度))`
- `Fog(seed).draw(fr, t, density, y0, y1, color, speed, light, light_r, layers, scale, cam, mask)`
- 工具：`bloom`、`grain`、`heat_haze`、`dof_blur`、`noise`、`scroll`

## 测试 / 联系表（lib/rig_test/）
`fx2_test.py→fx2_sheet.jpg`、`army_test.py→army_sheet.jpg`、`crowd_test.py→crowd_sprites.jpg`、`paper_test.py→paper_sheet.jpg`、`props_test.py→props_sheet.jpg`、`skia_compare.py→skia_cmp_*.png`、`crowd_skia_compare.py→skia_cmp_crowd.jpg`、`skia_bench.py`（计时）。旧测试 `t1.py trail.py emp.py sheet.py` 仍可用。

## 已知缺口
- 暗箱（S063 天平变黑箱）、战场残骸（S039 断枪头盔）、屏风烛影（S050）、巨手阴影（S084）未单独做道具，可用现有组件拼（Balance + 黑色方块路径 / Army 精灵散落 / Emperor 剪影 + god_rays）。
- `profile_cu` 仍是最重的组件（~0.5s），同帧尽量只叠轻量特效。
- 正面跪姿重甲兵在近景（>500px）可读性一般，跪拜近景建议用侧机位或 `Kneelers`。
