#!/bin/bash
# 副歌一 v3 后台分块渲染：2 进程各跑一半（每 90 帧落盘，可断点续跑）→ /tmp 混音 → 拷回 out/
cd /workspace/work/mv; d=out/c1v3chunks; mkdir -p $d
run() { for a in $(seq $1 90 $(($2-1))); do b=$((a+90)); [ $b -gt 2685 ] && b=2685
  [ -s $d/c_$a.mp4 ] || (python3 units/render_chorus1.py seg $a $b /tmp/c3_$a.mp4 > $d/log_$a.txt 2>&1 && cp /tmp/c3_$a.mp4 $d/c_$a.mp4); done; }
run 1755 2205 & run 2205 2685 & wait
python3 units/render_chorus1.py mux3 && \
ffmpeg -y -v error -i out/sample_chorus1_v3.mp4 -c:v libx264 -preset slow -crf 24 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart /tmp/w3.mp4 && cp /tmp/w3.mp4 out/sample_chorus1_v3_web.mp4 && echo ALLDONE > $d/done.txt
