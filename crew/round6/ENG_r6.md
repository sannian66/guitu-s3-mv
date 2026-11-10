# ENG_r6 — 工程组 r6-SPRITE：units/sprite.py 提速移植（feat/quality-pass R1/R2 → main）

> 派单：总导演 16:39（450e931）。范围只有 `units/sprite.py`；不移植转场去重 / A 段加刀 / 歌词道具化 / 骨架 rig / grade_unify；`a_kit.py` 的 SPRITE_WORK_W 两行也没动（A 组文件，且默认不影响画面）。
> 工具（本组路径）：`crew/round6/eng_r6_bench.py`（单帧计时 + draw 计数，固定随机种子）、`eng_r6_diff.py`（逐像素对拍）、`eng_r6_scan.py`（全片逐镜冒烟）。数据：`out/round6/eng_r6/bench.jsonl`、`scan_fast1.jsonl`。

## 1. 移植内容（相对分支原样的改动）
- 取 `origin/feat/quality-pass:units/sprite.py`（R1 包围盒 ROI 合成 + R2 线性基底缓存 + 同 PNG 预处理进程内共享）。
- `SPRITE_FAST` 默认先 `0`（分支是 1）。
- 三处缓存键（wind / _front / 线性基底）补 `id(A)`、`id(ring)`、`id(wind_w)`：main 各组有「改 sp.A / sp.ring 再画」写法（b_kit、chorus1_sprites、sec_d_bridge、sec_b_verse2），分支原键只认 id(F)，会命中旧结果。
- `_support()` 的 `is not` 比整数改 `!=`（分支注释里已知的小 bug，只影响速度）。
- **main 新增用法兼容**：B1 #15 唇红（`sec_b_pre1.py:569/898`）把 `keep_red` 传成精灵空间逐像素数组 `self.kr`，分支版 `float(keep_red)` 直接崩（50.9s TypeError）。改为：数组 keep_red 在线性基底里按裁剪窗口相乘、缓存键用数组身份；调色参数若是逐像素数组则退回整幅精灵空间路径。

## 2. 对拍记录
