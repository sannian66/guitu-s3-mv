# 生图渠道：OpenAI 协议（api.wentoken.si）

用户 2026-11-09 提供的第二个生图渠道，**比原 nananobanana 渠道更适合"改写已有画面"**：支持多参考图编辑。

## 怎么调用

Base URL：`https://api.wentoken.si/v1`，Authorization: `Bearer <key>`
Key 来源（按优先级）：环境变量 `WENTOKEN_KEY` → `~/.dsh/secrets/wentoken.key`。**Key 绝不入库。**

可用模型（`GET /v1/models` 实际返回，只有这 3 个，都是图像模型）：
- `gpt-image-2`
- `gpt-image-2.5-flare`
- `gpt-image-2.5-sunburst`

### 1) 文生图
```bash
curl -s -X POST https://api.wentoken.si/v1/images/generations \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"gpt-image-2","prompt":"a jade seal, product shot","n":1}'
```

### 2) 参考图编辑（关键能力）
`POST /v1/images/edits`，`multipart/form-data`，参考图字段名是 **`image[]`**（可多张）：
```bash
curl -s -X POST https://api.wentoken.si/v1/images/edits \
  -H "Authorization: Bearer $KEY" \
  -F model=gpt-image-2 \
  -F prompt="保持参考图1 的构图，把画风统一成参考图2：水墨写实、黑白灰、胶片颗粒" \
  -F image[]=@current_frame.png \
  -F image[]=@style_reference.png
```
这就是"锁构图、只改指定部分"的做法：**参考图1 = 当前成片那一帧，参考图2 = 全片画风正确的一帧**。

### 坑（都踩过）
- **`size` 参数会 400**：带上 `size` 会返回一段聊天式的"我不能直接生成图片，但可以帮你写提示词"。**不要传 size**（不传时模型自选，实测出 1672×941 / 1229×1280 等）。
- 同步接口、无 task_id：单张约 **37–70 秒**，直接返回 `data[0].b64_json`（或 `url`）。
- 文生图出的图**没有透明通道**；需要抠图的仍走绿幕 + `tools/cutout_green.py`。

## 本项目里的封装
`tools/gen_openai.py`：读 job 表批量跑
```json
[{"name":"wt_d17_eye", "prompt":"...", "refs":["out/refs_r1/cur.png","out/refs_r1/style.png"],
  "model":"gpt-image-2", "out":"assets/gen/wt", "nocut": true}]
```
- 有 `refs` → 走 `/images/edits`；没有 → `/images/generations`
- `nocut: true` → 整帧替换用，不抠图；否则自动绿幕抠图
- 自动记 `crew/genlog.md`
```bash
python3 tools/gen_openai.py jobs/wt_r1.json --dry   # 先看计划
python3 tools/gen_openai.py jobs/wt_r1.json
```
