#!/bin/bash
# 沙箱版渲单帧：tools/rf_sb.sh <秒> <out.png>（直接在仓库根渲，ROOT=/workspace/work/mv）
cd /workspace/work/mv && python3 render_sprite_full.py frame "$1" "$(realpath -m "$2")"
