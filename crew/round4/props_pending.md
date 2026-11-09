# props 组 · 待落地补丁清单（**请勿与其他线同时改同一 sec 文件**）

> 生成 2026-11-09 21:5x。原则：「宁可少做也不做丑」。本轮**只改 `units/props_dev.py` 与两份 JSON，未碰任何 `sec_*.py`**。
> 等 lead 给窗口后，按下面一次性落；落完再跑 `dupcheck`。

## A. 需要注释掉的 6 行（载面丢失 → skip）

| # | 文件 | 当前行号 | 该行原文 | 改成 |
|---|---|---|---|---|
| L05 | `units/sec_a_intro_verse1.py` | **1421** | `        fr = PD.play(fr, 'L05', t)  # [r4-props]` | `        # fr = PD.play(fr, 'L05', t)  # [skip:载面丢失 2026-11-09]` |
| L07 | `units/sec_a_intro_verse1.py` | **1665** | `        fr = PD.play(fr, 'L07', t)  # [r4-props]` | `        # fr = PD.play(fr, 'L07', t)  # [skip:载面丢失 2026-11-09]` |
| L11 | `units/sec_b_pre1.py` | **614** | `        fr = PD.play(fr, 'L11', t)  # [r4-props]` | `        # fr = PD.play(fr, 'L11', t)  # [skip:载面丢失 2026-11-09]` |
| L17 | `units/chorus1.py` | **847** | `        fr = PD.play(fr, 'L17', t)  # [r4-props]` | `        # fr = PD.play(fr, 'L17', t)  # [skip:载面丢失 2026-11-09]` |
| L31 | `units/sec_c_pre2_chorus2.py` | **823** | `        if not PROPS_TEXT_OFF: fr = PD.play(fr, 'L31', t)   # [r4-props] #39/#42/#43 关` | `        # if not PROPS_TEXT_OFF: fr = PD.play(fr, 'L31', t)  # [skip:载面丢失 2026-11-09]` |
| L33 | `units/sec_c_pre2_chorus2.py` | **1212** | `        if not PROPS_TEXT_OFF: fr = PD.play(fr, 'L33', t)   # [r4-props] #39/#42/#43 关` | `        # if not PROPS_TEXT_OFF: fr = PD.play(fr, 'L33', t)  # [skip:载面丢失 2026-11-09]` |

⚠️ **行号随时会漂**：`sec-c` 线已经动过 `sec_c_pre2_chorus2.py`（L31/L33 那两行现在是它加的 `if not PROPS_TEXT_OFF:` 守卫形式）。
落地时请**按 `PD.play(fr, 'Lxx'` 做字符串定位**，不要按行号盲改。

## B. skip 理由（都来自 2026-11-09 载面巡检，`out/props_dev/carrier_check.jpg`）
| 句号 | 理由 |
|---|---|
| L05 | 框内是红雨+刀，整片偏红 → 朱印压红底不可见 |
| L07 | 原计划的石碑被移除，框内是暖色天空+人物剪影（肤色 55%）→ 载面丢失且压脸 |
| L11 | 框内几乎全黑（高频 1.8），榜文纸边不在该位置 |
| L17 | S039 已成眼睛特写（红光）→ 压眼 |
| L31 | C09 已成人脸特写 → 压脸 |
| L33 | 只剩血滴+雨，几乎无结构（高频 2.9） |

## C. 已在 `units/props_dev.py` 里改好的两处（不涉及 sec 文件）
| 句号 | 改动 | 参数 |
|---|---|---|
| **L18** | 「刻在砖上」→**印在纸面**（S041 现为纸面小字榜文） | `fn='印'`、`press=1.0`、`bleed=1.3`、`wear=0.20`、`frame_box=False`、框 (1560,300,1800,600) |
| **L19** | 穿线挂点从「刀身」挪到**画面左上方暗部**（巨字「我」之外） | 框 (240,150,700,430)，线宽/摆幅不变（sway 9.0 / freq 0.8 / track_v 0.52） |

## D. 最终在用清单（**14 处** = 13 处接线 + L54 内联）

| # | 句号 | 关键词 | 手法 | 载面 | 镜号 | 备注 |
|---|---|---|---|---|---|---|
| 1 | L01 | 夜 | 穿线 | 雨幕/刀身（挂杆在顶部） | V01 | 框 (700,220,1300,720) |
| 2 | L02 | 寒光 | 擦 | 天幕右侧 | V04 | wipe 0.75 / keep 0.22 |
| 3 | L03 | 罪状 | 印 | 栏板横条 | V08 | press 1.0 / bleed 1.5 |
| 4 | L08 | 芒 | 烧 | 刀身（自燃） | V19 | 字高 ≈180px、炭色 ink |
| 5 | L13 | 刀不放 | 穿线 | 画面顶端挂杆 | S029 | sway 11 / 0.9Hz |
| 6 | L14 | 定 | 印 | **左下角暗部小朱印（8% 画高≈86px）** | S032 | press 0.75，对称轴留空 |
| 7 | L15 | 铁壁 | 刻 | 砖墙（一字一砖，`s034_cells`） | S034 | virt 自动档 + hot 空 |
| 8 | L18 | 扛 | **印（改）** | **纸面小字榜文** | S041 | press 1.0 / bleed 1.3 |
| 9 | L19 | 判 | 穿线 | **左上暗部（改）** | S043 | 框 (240,150,700,430) |
| 10 | L32 | 发烫 | 烧 | 刀面余烬 | C12 | ink (0.42,0.035,0.02) |
| 11 | L35 | 铁壁 | 刻 | 城墙墙面 | C24 | 强制 virt 0.62 + soft_lift 0.05 |
| 12 | L39 | 判 | 印 | 右上（已下移 ~70px、缩 15%） | C38 | press 0.95 |
| 13 | L51 | 谎言 | 烧穿 | 纸卷挂轴（左） | E07 | `burn_hole` + 纯黑暖雾 + 洞缘焦红 |
| 14 | **L54** | 伪装 | 剪影+真孔+压印 | **人物本体（精灵 alpha）** | E19 | **已在 E19 内联接线，无需补丁** |

## E. 两份 JSON 已同步（lyric-uni 可直接读）
- `out/props_dev/hidden_slots.json`：**21 槽**（原 34 − 6 处 skip 的 13 槽）→ 字幕正好只空这些格。
- `out/props_dev/prop_boxes.json`：**14 条**（13 处 + L54），格式不变 `{句号:{frames,box,key,fn,why}}`。
