#!/bin/bash
# usage: rend.sh <tag> FR_LIST   (renders into out/c_r1/<tag>/ via pxcheck in devsnap)
set -e
VN=/Users/sannian/Downloads/鬼屠OP_new/out/full_sprite/chunks/local60_149c727_20261109/venv/bin/python
TAG=$1; FRs=$2
D=/Users/sannian/Downloads/鬼屠OP_new/out/c_r1/$TAG
mkdir -p "$D"
cd /Users/sannian/Downloads/鬼屠OP_new/out/devsnap
FR="$FRs" LYRIC_UNI=1 GRADE_UNIFY=1 "$VN" pxcheck.py
for f in $(echo $FRs | tr ',' ' '); do cp "/tmp/px_1_$f.png" "$D/f$f.png"; done
echo "done $TAG"
