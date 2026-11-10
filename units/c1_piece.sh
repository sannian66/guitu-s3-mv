#!/bin/bash
# 并行渲染若干 30 帧小段：c1_piece.sh A B [A B]...  → out/c1chunks/p_A.mp4（成功才落盘）
cd "${MV_ROOT:-/workspace/work/mv}"; d=out/c1chunks
while [ $# -ge 2 ]; do a=$1; b=$2; shift 2
  [ -s $d/p_$a.mp4 ] || (python3 units/render_chorus1.py seg $a $b $d/p_$a.tmp.mp4 > $d/logp_$a.txt 2>&1 && mv $d/p_$a.tmp.mp4 $d/p_$a.mp4) &
done; wait; ls $d/p_*.mp4
