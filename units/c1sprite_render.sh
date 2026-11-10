#!/bin/bash
# 副歌一精灵版（SPRITE_MODE=1）渲染：帧 1784–2586（59.47–86.20s），2 进程分块（90 帧/块）先写 /tmp 再拷 out/chorus1_sprite/，断点续跑
# → 混音（audio/谁定正邪.mp3 同段）→ CRF18 母版 + CRF23 小文件
cd "${MV_ROOT:-/workspace/work/mv}"; export SPRITE_MODE=1 OMP_NUM_THREADS=1; d=out/chorus1_sprite; mkdir -p $d/chunks
F0=1784; F1=2586; MID=2186
run() { for a in $(seq $1 90 $(($2-1))); do b=$((a+90)); [ $b -gt $2 ] && b=$2
  [ -s $d/chunks/c_$a.mp4 ] || (python3 units/render_chorus1.py seg $a $b /tmp/cs_$a.mp4 > $d/chunks/log_$a.txt 2>&1 && cp /tmp/cs_$a.mp4 $d/chunks/c_$a.mp4); done; }
run $F0 $MID & run $MID $F1 & wait
ls $d/chunks/c_*.mp4 | sort -t_ -k2 -n | sed "s#.*/#file '#; s#\$#'#" > $d/chunks/list.txt
T0=$(python3 -c "print(f'{$F0/30:.4f}')"); DUR=$(python3 -c "print(f'{($F1-$F0)/30:.4f}')")
ffmpeg -y -v error -f concat -safe 0 -i $d/chunks/list.txt -ss $T0 -t $DUR -i "audio/谁定正邪.mp3" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -movflags +faststart /tmp/c1s_master.mp4 && cp /tmp/c1s_master.mp4 $d/chorus1_sprite_master_crf18.mp4
ffmpeg -y -v error -i $d/chorus1_sprite_master_crf18.mp4 -c:v libx264 -preset slow -crf 23 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart /tmp/c1s_web.mp4 && cp /tmp/c1s_web.mp4 $d/chorus1_sprite_crf23.mp4 && echo ALLDONE > $d/done.txt
