# r6-RENDER 全片出片（17:05 起）

派单：总导演 17:01（725096c）。A–F 全部过线，SPRITE_FAST=1 默认，SUB_STYLE=serif_h + SUB_FX=1 默认。

## 做法（两层）
1. **画面底层**：`SUB_OFF=1`，按段落/镜头边界切 34 块（`crew/round6/render_r6_chunks.json`，相邻镜头合并到 ≤260 帧，段落边界必切），
   每块 `tools/r6_render.py base F0 F1 out.mkv` → **FFV1 gbrp 无损**（≈1.2 MB/帧，全片约 8.5 GB；JuiceFS 余量 1 PB）。
   块起点 `random.seed(F0)`、块内共享 cache，与 `render_sprite_full.seg` 同口径。
   驱动 `tools/r6_drive.sh base`（后台 setsid，W=2，每块 `tools/cpu_slot.sh` 包一层，已完成块跳过 = 断点续渲）。
2. **字幕层**：`tools/r6_drive.sh sub` 逐块解码底层 → `subtitle.apply`（默认 serif_h + SUB_FX=1）→ x264 crf17 high yuv420p（bt709 矩阵 + 标记）。
3. 拼接：concat copy + `audio/谁定正邪.mp3` → AAC 320k → `out/render_r6/guitu_s3_mv_r6.mp4`。
- 产物都在 `out/render_r6/`（.gitignore，不入库）。

**验证（17:06）**：帧 4303（143.43s）底层 FFV1 解码 + 离线 `subtitle.apply` vs `tools/rf_sb.sh 143.4333` 整片管线帧：**逐像素差 0**；底层与成品只在 y≥960 不同。

## 以后只改字幕 / 去画内重复字
- 只改字幕（subtitle.py）：底层不动，删 `out/render_r6/sub/*.mp4`（或只删受影响块）→ `tools/r6_drive.sh sub` → 重新拼接。
- 改某几个镜头画面：查 `render_r6_chunks.json` 找到镜号所在块 → 删该块 `base/<块>.mkv` 与 `sub/<块>.mp4` → `tools/r6_drive.sh base` + `sub` → 拼接。

## 块完成记录（块 / 帧范围 / 镜头 / 耗时 / md5(底层 mkv)）
| 块 | 帧 | 耗时 s | md5 | 完成 |
|---|---|---|---|---|
