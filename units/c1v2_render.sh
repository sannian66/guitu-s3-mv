#!/bin/bash
# 副歌一 v2 后台分块渲染：2 进程各跑一半（各自内部按 90 帧落盘，可断点续跑），完成后混音 + 网络版
cd "${MV_ROOT:-/workspace/work/mv}"; d=out/c1v2chunks; mkdir -p $d
run() { for a in $(seq $1 90 $(($2-1))); do b=$((a+90)); [ $b -gt 2685 ] && b=2685
  [ -s $d/c_$a.mp4 ] || (python3 units/render_chorus1.py seg $a $b $d/c_$a.tmp.mp4 > $d/log_$a.txt 2>&1 && mv $d/c_$a.tmp.mp4 $d/c_$a.mp4); done; }
run 1755 2205 & run 2205 2685 & wait
python3 units/render_chorus1.py mux sample_chorus1_v2 && \
ffmpeg -y -v error -i out/sample_chorus1_v2.mp4 -c:v libx264 -preset slow -crf 24 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart /tmp/w.mp4 && cp /tmp/w.mp4 out/sample_chorus1_v2_web.mp4 && echo ALLDONE > $d/done.txt
