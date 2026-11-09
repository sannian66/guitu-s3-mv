#!/bin/bash
# 本机渲单帧：tools/rf.sh <秒> <out.png>   （先同步快照，再从快照渲）
# 多人并行时各用各的快照：SNAP=$R/out/devsnap_a tools/rf.sh 22.0 /tmp/x.png；NOSNAP=1 跳过同步
R=/Users/sannian/Downloads/guitu-s3-mv
PY=${PY:-/Users/sannian/Downloads/鬼屠OP_new/out/full_sprite/chunks/local60_149c727_20261109/venv/bin/python}
SNAP=${SNAP:-$R/out/devsnap}
[ -z "$NOSNAP" ] && $PY $R/tools/devsnap.py $SNAP >/dev/null
O=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
cd $SNAP/code && $PY render_sprite_full.py frame "$1" "$O"
