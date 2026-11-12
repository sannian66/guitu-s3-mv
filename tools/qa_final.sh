#!/bin/bash
# 第八轮成片质检：规格 / 音轨 / 画幅区亮度 / 联系表 / 首尾帧
# 用法：bash tools/qa_final.sh <成片.mp4> [输出目录]
set -e
cd "$(dirname "$0")/.."
F="$1"; OUT="${2:-out/r8/qa}"
[ -s "$F" ] || { echo "用法：bash tools/qa_final.sh <成片.mp4> [输出目录]"; exit 1; }
PY=$HOME/.venvs/guitu/bin/python
mkdir -p "$OUT"; B=$(basename "$F" .mp4)
T=$(mktemp -d)

echo "=== 1. 视频规格"
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames,pix_fmt \
  -of default=nw=1 "$F"
echo "--- 时长 / 体积"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$F"

echo "=== 2. 音轨"
ffprobe -v error -select_streams a:0 \
  -show_entries stream=codec_name,channels,sample_rate,duration -of default=nw=1 "$F" || echo "!! 无音轨"

echo "=== 3. 画幅区亮度（去掉 2.39 上下黑边，每秒采样）"
read -r W H <<<"$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$F" | tr ',' ' ')"
BAR=$($PY -c "print(int(round(($H - $W / 2.39) / 2)))")
echo "  ${W}x${H}，黑边各 ${BAR}px"
ffmpeg -v error -i "$F" -vf "crop=${W}:$((H-2*BAR)):0:${BAR},fps=1,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=${T}/yavg.txt" -f null - 2>/dev/null || true
$PY - "$T/yavg.txt" <<'PY'
import re, statistics, sys
vals = [float(m.group(1)) for m in re.finditer(r'YAVG=([\d.]+)', open(sys.argv[1], errors='ignore').read())]
if not vals:
    print('  (未采到亮度)'); raise SystemExit
print('  采样 %d 帧  均值 %.1f  中位 %.1f  最低 %.1f  最高 %.1f'
      % (len(vals), statistics.mean(vals), statistics.median(vals), min(vals), max(vals)))
lo = [i for i, v in enumerate(vals) if v < 65]
print('  低于 65：%d 处（%.0f%%）%s' % (len(lo), 100.0 * len(lo) / len(vals),
      ('前几处 @ %s s' % lo[:8]) if lo else ''))
PY

echo "=== 4. 联系表（每 10 秒一格）"
ffmpeg -y -v error -i "$F" -vf "select='not(mod(n\,300))',scale=320:-2" -vsync 0 "$T/s%04d.jpg" 2>/dev/null || true
FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$F")
$PY - "$T" "$OUT/${B}_联系表.jpg" "$FPS" <<'PY'
import cv2, glob, sys, numpy as np
d, out, fr = sys.argv[1], sys.argv[2], sys.argv[3]
num, den = (fr.split('/') + ['1'])[:2]
fps = float(num) / float(den)
step = 300.0 / fps
fs = sorted(glob.glob(d + '/s*.jpg'))
if not fs:
    print('  !! 没抽到帧'); raise SystemExit
cols = 6 if len(fs) > 6 else max(1, len(fs))
rows = (len(fs) + cols - 1) // cols
tile = cv2.imread(fs[0]); h, w = tile.shape[:2]
sheet = np.zeros((rows * h, cols * w, 3), np.uint8)
for i, f in enumerate(fs):
    im = cv2.imread(f)
    if im is None: continue
    r, c = divmod(i, cols)
    sheet[r*h:r*h+im.shape[0], c*w:c*w+im.shape[1]] = im
    cv2.putText(sheet, '%ds' % int(i * step), (c*w+8, r*h+26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
print('  %s  (%d 格, 每 %.1fs)' % (out, len(fs), step))
PY

echo "=== 5. 首尾帧"
ffmpeg -y -v error -ss 0 -i "$F" -frames:v 1 "$OUT/${B}_首帧.jpg" 2>/dev/null || true
ffmpeg -y -v error -sseof -1.5 -i "$F" -update 1 -frames:v 1 "$OUT/${B}_尾帧.jpg" 2>/dev/null || true
ls "$OUT" | sed 's/^/  /'
rm -rf "$T"
echo QA_DONE
