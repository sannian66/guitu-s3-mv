#!/bin/bash
# 全片精灵版分块渲染（SPRITE_MODE=1）：帧 0–7239（0–241.3s），每块 240 帧，2 进程并行（2 核沙箱）。
# 先写 /tmp/sfc/，完成后拷一份到 out/full_sprite/chunks/（断点续跑：两处任一已有即跳过）。
# 用法：nohup setsid ./run_sprite_chunks.sh > /tmp/sfc/run.log 2>&1 &
cd "${MV_ROOT:-/workspace/work/mv}"
export SPRITE_MODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
T=/tmp/sfc; D=out/full_sprite/chunks; mkdir -p $T $D
F1=7239; STEP=240
worker() {  # $1 = 0/1：隔块分配
  i=0
  for a in $(seq 0 $STEP $((F1-1))); do
    i=$((i+1)); [ $((i % 2)) -ne $1 ] && continue
    b=$((a+STEP)); [ $b -gt $F1 ] && b=$F1
    n=$(printf %05d $a)
    [ -s $D/c_$n.mp4 ] && { [ -s $T/c_$n.mp4 ] || cp $D/c_$n.mp4 $T/c_$n.mp4; continue; }
    [ -s $T/c_$n.mp4 ] && { cp $T/c_$n.mp4 $D/c_$n.mp4; continue; }
    python3 render_sprite_full.py seg $a $b $T/tmp_$n.mp4 > $T/log_$n.txt 2>&1 && mv $T/tmp_$n.mp4 $T/c_$n.mp4 && cp $T/c_$n.mp4 $D/c_$n.mp4
  done
}
worker 0 & worker 1 & wait
echo ALLDONE $(ls $T/c_*.mp4 | wc -l)
