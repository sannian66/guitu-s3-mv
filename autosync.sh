#!/bin/bash
# 自动同步：把工作区所有改动（含半成品）提交并推到 GitHub main。跳过 >50MB 文件；.gitignore 照常生效（audio/ 已强制入库）。
cd "$(dirname "$0")"
[ -f .git/index.lock ] && { sleep 5; [ -f .git/index.lock ] && { echo "locked, skip"; exit 0; }; }
python3 crew/export_chat.py >/dev/null 2>&1   # pre-commit hook 也会导出（双保险）
git add -A
for f in $(git diff --cached --name-only --diff-filter=AM); do
  [ -f "$f" ] && [ $(stat -c%s "$f") -gt 50000000 ] && git reset -q -- "$f" && echo "skip big: $f"
done
git diff --cached --quiet && echo "nothing new" || AUTOSYNC=1 git -c user.name=sannian66 -c user.email=38859572+sannian66@users.noreply.github.com commit -q -m "自动同步 $(TZ=Asia/Shanghai date '+%m-%d %H:%M')"
# 2026-11-09 用户硬规则：**永不推主线**，只推当前分支（变更走 PR 合并）
BR=$(git rev-parse --abbrev-ref HEAD)
if [ "$BR" = "main" ] || [ "$BR" = "master" ]; then
  echo "在主线 $BR 上，按规则不推送；请切到工作分支（当前改造分支：feat/quality-pass）"
  git log --oneline -1
else
  git pull --rebase --autostash -q origin "$BR" 2>/dev/null || true
  git push -q -u origin "$BR" && echo "pushed → origin/$BR（走 PR，不推 main）" && git log --oneline -1
fi
