#!/bin/bash
# 把一个 90 帧块拆成两个 45 帧并行渲染再拼接（CPU 被其他组占用时用）
cd "${MV_ROOT:-/workspace/work/mv}"; a=$1; m=$((a+45)); b=$((a+90)); [ $b -gt 2685 ] && b=2685
d=out/c1chunks
[ -s $d/h_$a.mp4 ] || python3 units/render_chorus1.py seg $a $m $d/h_$a.mp4 > $d/logh_$a.txt 2>&1 &
[ -s $d/h_$m.mp4 ] || python3 units/render_chorus1.py seg $m $b $d/h_$m.mp4 > $d/logh_$m.txt 2>&1 &
wait
printf "file 'h_$a.mp4'\nfile 'h_$m.mp4'\n" > $d/hl_$a.txt
ffmpeg -y -v error -f concat -safe 0 -i $d/hl_$a.txt -c copy $d/c_$a.mp4 && echo ok $a
