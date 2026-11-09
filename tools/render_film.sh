#!/bin/bash
# tools/render_film.sh — 冻版重渲入口（1080p30，全片 7240 帧 = 241.33s）
#
# 用法：
#   ./tools/render_film.sh              # 从当前工作区建快照 → 并行渲全片 → 出母版/网络版/对比
#   ./tools/render_film.sh --resume     # 复用已有快照，只续渲缺的块
#   OUT=out/snap_final ./tools/render_film.sh
#
# 会把快照目录、环境开关、产物路径写进 $SNAP/RESULT.txt，便于交接。
set -e
cd "$(dirname "$0")/.."
ROOT=$(pwd)
VENV="$ROOT/out/full_sprite/chunks/local60_149c727_20261109/venv/bin/python"
SNAP="${OUT:-$ROOT/out/snap_final}"
W="${W:-7}"           # 并发进程数：实测 6–7 最优（8 核 M2 Air，再多只增抖动）
FINE="${FINE:-120}"   # 分块帧数：120 = 4s（昂贵镜头会被动态均摊）

[ -x "$VENV" ] || { echo "找不到 venv: $VENV"; exit 1; }

if [ "$1" != "--resume" ] || [ ! -d "$SNAP/code" ]; then
  echo "== 1/4 建源码快照 → $SNAP"
  "$VENV" tools/devsnap.py "$SNAP" --clean
else
  echo "== 1/4 复用快照 $SNAP（--resume）"
fi

cp out/devsnap/prun.py "$SNAP/"            # 用带 lyric_uni/grade 钩子的最新渲染器
cp out/devsnap/pxcheck.py "$SNAP/" 2>/dev/null || true

echo "== 2/4 并行渲染：7 进程 × ${FINE} 帧/块，开关 SPRITE_MODE=1 GRADE_UNIFY=1 LYRIC_UNI=1"
cd "$SNAP"
export SPRITE_MODE=1 GRADE_UNIFY=1 LYRIC_UNI=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export W FINE
nohup "$VENV" prun.py run > logs/film.log 2>&1 &
echo "   后台 PID $! ，日志 $SNAP/logs/film.log"
echo "   进度：$VENV prun.py status"

echo "== 3/4 渲染完成后自动拼接 + 混音 + 校验（prun.py run 内已含）"
echo "== 4/4 产物：$SNAP/delivery/谁定正邪_MV_1080p30_master_crf17.mp4"
echo
echo "监控： tail -f $SNAP/logs/film.log"
echo "暂停： pkill -f '[p]run.py'   ；续渲： $0 --resume"
