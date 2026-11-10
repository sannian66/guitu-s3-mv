#!/bin/bash
# 沙箱后台保底：每 3 分钟跑一次 autosync.sh（提交+推送）。用法：tools/autosync_loop.sh [总秒数]
cd "$(dirname "$0")/.."
END=$(( $(date +%s) + ${1:-1140} ))
while [ $(date +%s) -lt $END ]; do
  echo "== $(TZ=Asia/Shanghai date '+%m-%d %H:%M:%S')"; timeout 170 ./autosync.sh 2>&1 | tail -3
  sleep 180
done
