#!/bin/bash
# 自动同步：把工作区所有改动（含半成品）提交并推到 GitHub main。跳过 >50MB 文件；.gitignore 照常生效（audio/ 已强制入库）。
cd "$(dirname "$0")"
[ -f .git/index.lock ] && { sleep 5; [ -f .git/index.lock ] && { echo "locked, skip"; exit 0; }; }
python3 crew/export_chat.py >/dev/null 2>&1   # pre-commit hook 也会导出（双保险）
git add -A
for f in $(git diff --cached --name-only --diff-filter=AM); do
  [ -f "$f" ] && [ $(wc -c < "$f") -gt 50000000 ] && git reset -q -- "$f" && echo "skip big: $f"
done
git diff --cached --quiet && echo "nothing new" || AUTOSYNC=1 git -c user.name=sannian66 -c user.email=38859572+sannian66@users.noreply.github.com commit -q -m "自动同步 $(TZ=Asia/Shanghai date '+%m-%d %H:%M')"
git pull --rebase --autostash -q origin main && git push -q origin main && git log --oneline -1
