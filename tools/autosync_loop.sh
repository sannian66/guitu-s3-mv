#!/bin/bash
# 后台保底：每 3 分钟 autosync 一次（commit 即推送之外的第二道保险）。后台 shell 单次最多约 19 分钟，跑满后由定时任务/下一次调用重启。
cd "$(dirname "$0")/.."
END=$(( $(date +%s) + ${1:-1140} ))
while [ $(date +%s) -lt $END ]; do
  ./autosync.sh 2>&1 | tail -1 | sed "s/^/[loop $(TZ=Asia/Shanghai date +%H:%M)] /" >> /tmp/autosync_loop.log
  sleep 180
done
