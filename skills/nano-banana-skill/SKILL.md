---
name: nano-banana-skill
display_name: Nano Banana skill
description: 通过 https://www.nananobanana.cn 的 Skills API 生成图片、视频、音频，查询任务状态与结果，或在用户明确给出画布坐标时写回画布节点。
---

# Nano Banana skill

## 配置
- 域名 / Base URL：`https://www.nananobanana.cn`
- 鉴权：`Authorization: Bearer $NANO_BANANA_KEY`
  - **Key 不入库**（本仓库是公开的）。本地放在已 gitignore 的 `.env.local`：`NANO_BANANA_KEY=bsk__...`；Hark 环境里 Key 存在保险库，按域名自动注入，curl 不需要带 Authorization。
  - 返回 `invalid_skill_key` / `skill_key_revoked` → 提示用户重置 Skills Key。
- 多租户：Key 已绑定用户和租户，服务端隔离模型、额度、渠道、任务、画布权限。不要询问或拼接租户 ID；不要查询租户管理后台端口、供应商地址或内部模型名。
- 控制面只调用 `https://www.nananobanana.cn/api/skills/*`；唯一例外是把本地文件 PUT 到 presign 返回的 `upload_url`。不要探测其他 API 路径。

## 本项目约定（《谁定正邪》MV）
- 生图默认模型：**`RH_image2`（全能图片G2，支持 4K）**，`size:"4K"`。2026-11-09 报价：4K 16:9 = 3 积分（`RH_image2_official` 同规格 18 积分）。每次提交前仍要重新报价。
- 角色：用用户提供的资产图做参考（放在 `assets/characters/`），**五官、发型保持一致**；服装、穿搭、道具可以改。
- 提示词与结果记录到 `crew/genlog.md`（模型、尺寸、积分、task_id、result_urls、落盘路径）。

## 安装后第一步：读取模型
`GET /api/skills/models`，读取 `image[]`、`video[]`、`audio[]`、`name`、`supportedModes`、`capability`、`entitlement`、`video[].modes`、`video[].detailUrl`、`video[].mediaInputReview`（`imageInputReview` 仅供旧客户端兼容）。请求里的 `model` 必须用这里返回的 `name`（或服务端明确返回的 id），不要猜 actualModel、供应商名或渠道名。

## 报价
按类型把完整生成请求 POST 到：`/api/skills/images/quote`、`/api/skills/videos/quote`、`/api/skills/audio/quote`。读 `billing.total_points`；`kind=prepaid` 表示预扣、完成后可能按实际时长结算。报价不创建任务、不扣积分；配置可能变化，提交前重新查询。返回 `skills_quote_unavailable` 或接口不可用时，明确说明无法确认价格，不得把 pointsCost 或基础单价当成最终报价。

## Seedance 参考素材必经流程（2.0、2.5 及历史兼容渠道）
1. 视频参数确定后，读取最新模式详情；本地图片、视频、音频先 presign + PUT，取得 `upload.asset_url`（HTTP 源地址）。已有可访问的 HTTPS 素材地址可用于首次审核；上传成功不等于审核通过。
2. 把源地址按原顺序放入 `images`、`videos`、`audios`，携带同一模式的完整请求 POST `/api/skills/videos/review`；三类参考素材都要审核，不能只审核图片。
3. 只有审核 HTTP 2xx、`success=true`、`status=ready`，且每个必审输入都返回 `status=approved` 和非空 `asset_uri`，才允许生成。`assets.images/videos/audios[].source_url` 是源地址；`asset_uri` 才是审核取得的 asset URL，通常为 `asset://…`，专用人脸渠道按 `referenceScheme` 返回 `face:`。不能把 `upload.asset_url` 当作已审核引用。
4. 把审核返回的 `generation_request` 原样 POST 到同域 `generation_endpoint`（`/api/skills/videos/generate`）；其中 images/videos/audios 已替换为审核引用，保持顺序、模型、模式和参数，不自行拼接 `asset://`，不换回 HTTP 源地址。收到生成 `task_id` 后才轮询任务。
5. 审核返回 HTTP 401/403、系统配置错误、拒绝、超时、非 ready 或缺少审核引用/generation_request 时，停止生成并报告实际错误；保留源地址用于按下文恢复，不能改走旧版直接生成来绕过审核。只有明确没有参考素材的纯文字生视频可跳过素材审核。

## 按请求类型调度
- **已有视频工具**：高清放大、深度提取、去字幕用 POST `/api/skills/videos/process`，传 `operation`（upscale / depth / subtitle-erase）、`video_url` 和本次操作唯一的 `idempotency_key`；同一操作重试复用此 key。高清放大可选 `resolution`=720p/1080p/2k/4k，缺省 1080p；其他两项使用租户已有工具配置。去字幕仅整段全局智能擦除（subtitle_all_area），不要传 mode、clips、detectRect 或其他选区参数。这三项不需要选普通生视频模型或时长；服务端探测源视频时长并沿用工具栏计费。收到 task_id 后按下述规则轮询，完成前不得宣布成功。
- **视频参数先问清**：用户未指定视频模型时，先展示 `/api/skills/models` 返回的可用视频模型并询问用哪个，同时确认分辨率 `resolution` 和时长 `duration`（秒）。任一缺失都先问并等待回答，再审核或提交；已明确的不重复问，不擅自选第一个模型或套用 example/default。选定模型后按最新模式 inputSchema 校验；固定值或自动时长（如 `duration=-1`）要说明含义并确认，不把 -1 当负一秒，不添加 Schema 不支持的字段。
- **文字生图**：POST `/api/skills/generate`，只传 `model` 和 `prompt`，可选 `ratio`/`size`/`space_type`。
- **参考图生图**：同样 POST `/api/skills/generate`，把一个或多个 `asset_url` 放进 `input`；不要放本地路径或 upload_url。
- **视频调用详情**：选定模型后读 GET `/api/skills/models/video/{modelName}`（name 需 URL 编码；优先直接用 `detailUrl`）。按 `modes[].inputSchema`、`media`、`mediaInputReview`、`promptRequirement`、`example` 构造请求；只选 `available=true` 的模式，未配置或不支持的模式不得猜测。每次新任务重新读详情。
- **文字生视频**：POST `/api/skills/videos/generate`，传 `model`、`prompt`、`mode` 和该模式 inputSchema 允许的参数；duration、resolution、aspect_ratio 范围按模式详情。`video_mode` 等旧别名仍兼容，新请求统一用 `mode`，不把通用 supportedModes 当完整细分模式列表。
- **图片/视频/音频参考生视频**：先 POST `/api/skills/videos/review`，再 POST `/api/skills/videos/generate`。按模式详情用 images/videos/audios 三个数组，审核成功后原样提交返回的 generation_request。`media_type` 只用于上传元数据或旧版素材对象，绝不能加到生成请求顶层。
- **音色设计、声音克隆、TTS**：POST `/api/skills/audio/generate`；从 `audio[]` 选 capability 分别为 `voice_design`、`voice_clone`、`tts` 的模型，模型 capability 必须与请求 capability 完全一致。音色设计传 `prompt + style`；声音克隆传 `prompt + reference_audio_url`（或 `reference_assets`）；TTS 二选一：`prompt + voice_id`，或 `prompt + reference_audio_url`（`reference_audio_text` 可选）。不要同时传 voice_id 和 reference_audio_url。
- 生成响应里的 `task_id` 或 `skill_task_id` 用于 GET `/api/skills/tasks/{task_id}` 轮询，严格遵守“结果轮询”。
- 只有用户明确给出 `workflow_id` 和 `node_id` 时，才在生成请求中附加 `canvas_writeback`；也可单独 POST `/api/skills/canvas/writeback`。

## 调用示例（JSON 请求都带 Authorization）
```
GET  /api/skills/models
POST /api/skills/generate        {"model":"<image[].name>","prompt":"cinematic product image","ratio":"16:9","size":"2K"}
POST /api/skills/generate        {"model":"<image[].name>","prompt":"edit this reference","input":["<asset_url>"]}
POST /api/skills/videos/review   <所选模式详情的 example JSON，替换提示词和 images/videos/audios 中的上传 asset_url>
POST /api/skills/videos/generate <原样提交审核响应的 generation_request；纯文字模式可直接提交详情 example>
POST /api/skills/audio/generate  {"model":"<voice_design model>","capability":"voice_design","prompt":"你好","style":"温暖、沉稳的青年女声"}
POST /api/skills/audio/generate  {"model":"<voice_clone model>","capability":"voice_clone","prompt":"你好","reference_audio_url":"<asset_url>"}
POST /api/skills/audio/generate  {"model":"<tts model>","capability":"tts","prompt":"你好","voice_id":"<voice-id>"}
GET  /api/skills/tasks/{task_id}
```

## 结果轮询（图片、视频、音频共用）
- 任务接口返回 `{"success":true,"task":{"status":"completed","result_urls":["…"],"error":null}}`。必须先取 `task = response.task`，再读 `task.status`、`task.result_urls`、`task.error`；不能读顶层 `response.status`，也不能把 `success=true` 当生成完成。
- 每次循环向 stderr 打印 `t=Ns status=xxx`（N 为累计秒数）；未识别状态打印 `status=unknown`，请求错误或超时打印 `status=_error`。stdout 留给最终结果。
- 命中 `completed` 立即 return task 并报告 result_urls；命中 `failed`、`cancelled`、`timeout` 等终态立即 return 错误结果（带 `_error` 和原 task），不得再 sleep 或发起下一轮查询。
- 只有明确的 `pending`、`queued`、`submitted`、`processing`、`running`、`settling` 才是进行中。缺失、空值、unknown、其他未识别 status 或非 JSON 响应绝不能当作进行中：独立累计连续未识别次数，最多诊断重查 3 次（含首次）；第 3 次立即 return `{_error:"unrecognized_task_status",task_id,response:<原始响应前 1000 字符>}` 并报错退出。读到已识别状态才清零计数，不能兜底成 processing。
- 设置有限总超时和单次 HTTP 超时（例如总计 10 分钟、每次最多 30 秒、间隔 5 秒，单次请求/等待不得超出剩余总时限）。轮询超时必须显式 return `{_error:"poll_timeout",task_id}`，不能静默结束或当作成功；HTTP 错误、`success=false` 或网络错误立即返回 `_error` 并附错误信息。轮询失败不代表服务端任务已取消，保留任务 ID 供之后查询，不自动重新提交生成。实现见 `tools/nb.py` 的 `poll_task`（与官方 examples/banana-skills-example.mjs 的 pollTask 同一契约）。

## 本地素材流程
POST `/api/skills/uploads/presign`（`filename`、`content_type`、`size`、`media_type`，支持 image/video/audio），从响应 `upload` 对象读 `upload_url`、`headers`、`asset_url`；按返回 headers 把原始二进制字节 PUT 到 upload_url，确认 HTTP 2xx 后再用 asset_url。PUT 不发 JSON、base64 或 multipart，不带 Skills Authorization。上传只负责存储，不代表已过审。upload_url 只用于上传且会过期，不能传给模型。图片生成和音频合成用上传 asset_url；参考生视频把它送到 /videos/review。素材已是 https CDN 地址时可直接用于首次审核；格式不支持时仍需走下述重新上传流程。

## 视频渠道与素材审核
生成调用 `/api/skills/videos/generate`，服务端按 Key 所属租户和请求模型选择并锁定一个渠道，不会故障转移；过审失败或超时会停止提交。审核用 POST `/api/skills/videos/review`（同 Authorization），接收同一模式的完整请求 JSON（model、mode、prompt 和该 inputSchema 允许的参数/素材）；只审核，不建任务、不返回 task_id。读逐模式 `mediaInputReview`：`requirement` 审核义务，`available` 当前租户能否完成审核，`endpoint` 受支持的审核地址，`referenceScheme` 审核引用格式。`imageInputReview` 为旧字段；`matchingChannels` 为空时不要猜测或探测审核接口，也不能推断为免审。

Seedance 2.0、2.5（含历史兼容渠道）的图片、视频、音频都必须在提交前审核；失败或超时不得提交。成功响应 `status=ready`，`assets.images/videos/audios` 每项含 `source_url`、`asset_uri`、`status=approved`、`expires_at`。资产审核渠道返回如 `asset://asset-20260821042413-7kxg7`；仅专用人脸渠道返回 `face:` 引用。不要拼接或伪造引用。generation_request 原样 POST 到 generation_endpoint，绝不换回原 HTTP 地址。审核配置缺失、不兼容或不支持该媒体类型时返回 `skills_media_review_unavailable`；纯文字请求无需审核。服务端在生成时校验审核引用的用户、租户、渠道、媒体类型、有效期和通过状态。超时用同一原上传地址再次调用 /videos/review 继续查询；没有 task_id 不能轮询任务。引用失效时用 source_url 重新审核。旧版直接提交上传 URL 仅为服务端兼容行为，不能当审核失败的兜底。

## 格式不支持的恢复
`skills_*_review_failed` 且 `reason=unsupported_media_format`，或消息含 `InvalidParameter.FormatUnsupported` / `Unsupported media format`，表示格式或读取失败，不等于内容审核拒绝。先拿原素材字节重新 presign + PUT，按真实文件设置 MIME、扩展名和 size，只用这次返回的新 asset_url 再调 /videos/review；即使旧素材已是 CDN 地址也这样做，不重试旧 URL。新 URL 仍报格式不支持时，检查实际编码/封装和上传响应，不能只凭 .mp4 后缀认定兼容；必要时另存为 H.264、yuv420p、AAC 的 MP4（faststart，不覆盖原文件），再上传并审核一次。上传不会转码，转码也不保证供应商接受。仍失败就报告原始错误并停止；内容审核拒绝不得用重新上传或转码绕过。仅在审核 ready 后生成，收到 task_id 后才开始轮询。

## Seedance 模式
以租户实际启用为准：`text2video`（文字）、`image2video_first`（一张首帧）、`image2video_first_last`（依次首帧和尾帧）、`multimodal_ref`（图片/视频/音频参考）、`video_edit`（必须有参考视频）、`video_extend`（必须有参考视频）。Kling v3 Omni 与 RunningHub 的 first_last_frame、image_audio 等模式用各自详情，不套 Seedance 入参。先读 schema 再填时长和比例：Seedance 2.5 编辑 `duration=-1`、`aspect_ratio=adaptive`；多模态参考的常规时长和比例按当前详情。

## 错误处理
- `invalid_skill_key` / `skill_key_revoked`：提示用户重置 Skills Key。
- `model_package_required`：改用 models 返回的可用模型。
- 审核错误按 `reason`、`mediaType`、`assetIndex`、`recovery` 区分格式恢复、审核处理中和内容拒绝。不要靠切换兼容字段或添加顶层 media_type 重试同一失败素材。
