#!/bin/bash
# 新沙箱 clone 后运行一次：启用「commit 即推送」
cd "$(dirname "$0")/.." && git config core.hooksPath tools/hooks && echo "hooks on: $(git config core.hooksPath)"
