#!/bin/bash
# usage: run_chunks.sh a0 a1 [b0 b1 ...] -> renders pairs in parallel (2 at a time)
cd /workspace/work/mv
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
args=("$@")
for ((i=0; i<${#args[@]}; i+=2)); do
  a=${args[i]}; b=${args[i+1]}
  out=chunks/c_$(printf %05d $a).mp4
  [ -s "$out" ] && continue
  (python3 render_full.py $a $b $out.tmp.mp4 > chunks/log_$a.txt 2>&1 && mv $out.tmp.mp4 $out) &
  while [ $(jobs -r | wc -l) -ge 2 ]; do sleep 2; done
done
wait
ls -la chunks/*.mp4
