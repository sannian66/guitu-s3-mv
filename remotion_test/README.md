# Remotion + three.js 单镜试做（D 段 S06_Scale，167.25–168.62s，41 帧）
- 渲染：`npm install && npx remotion browser ensure && npx remotion render src/index.ts S06 out/s06_remotion.mp4 --gl=swangle --concurrency=2 --crf=16`
- 沙箱 2 核 arm64 无 GPU、swangle 软渲：41 帧约 50 秒（≈1.2 s/帧）。
- 对比图 out/s06_compare.jpg（左现版、右试做，第 30 帧）。
- 结论：真 3D 视差/秤盘铅垂/真实投影到手，但画风偏 CG 模型，失去生图水墨的干湿笔触；要追平需 NPR 着色器 + 手绘贴图。
