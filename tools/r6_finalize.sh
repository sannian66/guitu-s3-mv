#!/bin/bash
# tools/r6_finalize.sh — 拼接 34 块字幕层成品 + 音轨 → out/render_r6/guitu_s3_mv_r6.mp4，并 ffprobe 校验
cd "${MV_ROOT:-/workspace/work/mv}"
R=out/render_r6; OUTF=$R/guitu_s3_mv_r6.mp4
python3 -c "
import json
for c in json.load(open('crew/round6/render_r6_chunks.json')): print(\"file 'sub/%s.mp4'\" % c['name'])" > $R/concat.txt
n=$(ls $R/sub/b*_*.mp4 2>/dev/null | grep -v partial | wc -l); [ "$n" = 34 ] || { echo "sub 块只有 $n/34"; exit 1; }
ffmpeg -y -v error -f concat -safe 0 -i $R/concat.txt -i audio/谁定正邪.mp3 -map 0:v:0 -map 1:a:0 \
  -c:v copy -c:a aac -b:a 320k -ar 48000 -t 241.3333 -movflags +faststart /tmp/r6_final.mp4 || exit 1
cp -f /tmp/r6_final.mp4 $OUTF || exit 1   # JuiceFS 上 faststart 写尾会 IO 错，先写 /tmp
echo "== ffprobe"
ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=codec_name,profile,width,height,pix_fmt,r_frame_rate,avg_frame_rate,nb_read_frames,color_space -of default=nw=1 $OUTF
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels,bit_rate,duration -of default=nw=1 $OUTF
ffprobe -v error -show_entries format=duration,size,bit_rate -of default=nw=1 $OUTF
ffmpeg -v error -xerror -i $OUTF -f null - && echo decode=OK || echo decode=FAIL
md5sum $OUTF
