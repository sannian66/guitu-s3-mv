#!/bin/bash
# B 组提交：只提交给定路径（B 组自己的）。用法：tools/b_commit.sh "说明" path1 path2 ...
cd "${MV_ROOT:-/workspace/work/mv}"
export GIT_AUTHOR_NAME=sannian66 GIT_AUTHOR_EMAIL=38859572+sannian66@users.noreply.github.com GIT_COMMITTER_NAME=sannian66 GIT_COMMITTER_EMAIL=38859572+sannian66@users.noreply.github.com
msg="$1"; shift
git add -- "$@" && git commit -m "[B组 r6] $msg" -- "$@" 2>&1 | tail -5
