#!/bin/bash
# 共享 CPU 槽（沙箱只有 2 核）：任何超过 1 帧的渲染都必须包一层：tools/cpu_slot.sh python3 render_sprite_full.py ...
# 两个槽，拿到任意一个就跑；都占用就排队等（每 3 秒重试）。
while true; do
  for s in 0 1; do
    exec 9>/tmp/cpu_slot_$s.lock
    if flock -n 9; then "$@"; rc=$?; flock -u 9; exit $rc; fi
  done
  sleep 3
done
