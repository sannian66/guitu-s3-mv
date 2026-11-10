#!/bin/bash
# 全片精灵版导出（2026-11-09）：out/full_sprite/chunks/c_*.mp4（31 块，帧 0–7239）→ 拼接 + 混音
#   母版   full_sprite_master.mp4   视频流拷贝（CRF17）+ AAC 320k（>50MB，不入库）
#   网络版 full_sprite_web.mp4      1080p CRF21 slow + AAC 192k
#   预览版 full_sprite_720p.mp4     720p CRF26 + AAC 128k
# 每个文件：ffprobe 时长/流 + 全量解码（ffmpeg -xerror -f null）校验，结果写 out/full_sprite/verify.txt
set -e
cd "${MV_ROOT:-/workspace/work/mv}"
D=out/full_sprite; C=$D/chunks; A="audio/谁定正邪.mp3"
n=$(ls $C/c_*.mp4 | wc -l); [ "$n" -eq 31 ] || { echo "chunks=$n, need 31"; exit 1; }
ls $C/c_*.mp4 | sort | sed "s#.*/#file '#; s#\$#'#" > $C/list.txt
ffmpeg -y -v error -f concat -safe 0 -i $C/list.txt -i "$A" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -shortest -movflags +faststart /tmp/fs_master.mp4
cp /tmp/fs_master.mp4 $D/full_sprite_master.mp4
ffmpeg -y -v error -i $D/full_sprite_master.mp4 -c:v libx264 -preset slow -crf 21 -pix_fmt yuv420p -profile:v high -c:a aac -b:a 192k -movflags +faststart /tmp/fs_web.mp4
cp /tmp/fs_web.mp4 $D/full_sprite_web.mp4
ffmpeg -y -v error -i $D/full_sprite_master.mp4 -vf scale=1280:720:flags=lanczos -c:v libx264 -preset medium -crf 26 -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart /tmp/fs_720.mp4
cp /tmp/fs_720.mp4 $D/full_sprite_720p.mp4
: > $D/verify.txt
for f in full_sprite_master full_sprite_web full_sprite_720p; do
  p=$D/$f.mp4
  info=$(ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,nb_frames -of compact $p | tr '\n' ' ')
  err=$(ffmpeg -v error -xerror -i $p -f null - 2>&1 | head -5)
  fr=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 $p)
  st=OK; [ -n "$err" ] && st="DECODE_ERROR: $err"
  echo "$f | frames_decoded=$fr | $info | $st" >> $D/verify.txt
done
cat $D/verify.txt
