#!/bin/bash
# E 组提交：只提交 E 组自己的路径。用法：tools/e_commit.sh "说明"
cd "${MV_ROOT:-/workspace/work/mv}"
export GIT_AUTHOR_NAME=sannian66 GIT_AUTHOR_EMAIL=38859572+sannian66@users.noreply.github.com GIT_COMMITTER_NAME=sannian66 GIT_COMMITTER_EMAIL=38859572+sannian66@users.noreply.github.com
P=()
for p in units/e_r3.py tools/e_gen3.py out/round4/E_contact_v3.jpg out/round4/E_keys_v3.jpg crew/round4/HANDOFF_r3.md units/sec_e_final_outro.py units/e_kit.py tools/e_contact.py tools/e_recut.py tools/e_commit.sh crew/round4/E_storyboard.md crew/round4/E_hitmap.json crew/genlog.md assets/gen/E_r2 out/round4/E_contact_v1.jpg out/round4/E_keys_v1.jpg out/round4/E_contact_v2.jpg out/round4/E_keys_v2.jpg out/round4/E_tmp.jpg; do [ -e "$p" ] && P+=("$p"); done
git add "${P[@]}" && git commit -q -m "[E组] $1" -- "${P[@]}" 2>&1 | tail -3
