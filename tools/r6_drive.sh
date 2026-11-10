#!/bin/bash
# tools/r6_drive.sh — r6-RENDER 底层断点续渲驱动（后台用：setsid nohup tools/r6_drive.sh base </dev/null >/dev/null 2>&1 &）
#   tools/r6_drive.sh base     渲全部缺失底层块（W=2 并行，每块 tools/cpu_slot.sh 包一层）
#   tools/r6_drive.sh sub      底层齐了以后：逐块离线叠字幕 → out/render_r6/sub/*.mp4（W=2）
#   tools/r6_drive.sh status   已完成块数
# 完成记录：out/render_r6/done_base.tsv / done_sub.tsv（块名 f0 f1 耗时s md5 字节）；已完成块（文件在、帧数对）自动跳过。
# 只重渲某几块：删掉 out/render_r6/base/<块名>.mkv（及 sub/<块名>.mp4）再跑。
cd "${MV_ROOT:-/workspace/work/mv}"
R=out/render_r6; W=${W:-2}
mkdir -p $R/base $R/sub $R/logs
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 R
# 依赖装在 JuiceFS（沙箱重启不丢、不占内存盘）：pip install --target /workspace/work/.pydeps -r requirements.txt
[ -d /workspace/work/.pydeps ] && export PYTHONPATH=/workspace/work/.pydeps${PYTHONPATH:+:$PYTHONPATH}

# 守卫（11-10 第十二任）：沙箱重启会丢 libEGL，skia 静默回退 cv2 → 画质不同。缺就自动装，装不上就拒绝开渲。
if ! python3 -c "import skia" 2>/dev/null; then
  (sudo apt-get update -qq && sudo apt-get install -y -qq libegl1 libgl1) >/dev/null 2>&1
  python3 -c "import skia" 2>/dev/null || { echo "!!! skia 不可用，拒绝渲染" | tee -a $R/logs/fail.log; exit 2; }
fi

nframes() { ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$1" 2>/dev/null || echo 0; }
export -f nframes

list() {  # mode → "name f0 f1" for pending
  python3 -c "
import json
for c in json.load(open('crew/round6/render_r6_chunks.json')): print(c['name'], c['f0'], c['f1'])" | while read n a b; do
    if [ "$1" = base ]; then f=$R/base/$n.mkv; else f=$R/sub/$n.mp4; fi
    [ -s "$f" ] && [ "$(nframes "$f")" = "$((b - a))" ] && continue
    echo "$n $a $b"
  done
}

one_base() {
  n=$1 a=$2 b=$3; part=$R/base/$n.partial.mkv; t=$(date +%s)
  tools/cpu_slot.sh python3 tools/r6_render.py base $a $b $part > $R/logs/$n.base.log 2>&1
  c=$(nframes $part)
  if [ "$c" = "$((b - a))" ]; then
    mv -f $part $R/base/$n.mkv
    echo -e "$n\t$a\t$b\t$(( $(date +%s) - t ))\t$(md5sum $R/base/$n.mkv | cut -c1-32)\t$(stat -c %s $R/base/$n.mkv)\t$(date '+%H:%M')" >> $R/done_base.tsv
  else echo "FAIL $n frames=$c" >> $R/logs/fail.log; fi
}
one_sub() {
  n=$1 a=$2 b=$3; part=$R/sub/$n.partial.mp4; t=$(date +%s)
  tools/cpu_slot.sh python3 tools/r6_render.py sub $a $b $R/base/$n.mkv $part > $R/logs/$n.sub.log 2>&1
  c=$(nframes $part)
  if [ "$c" = "$((b - a))" ]; then
    mv -f $part $R/sub/$n.mp4
    echo -e "$n\t$a\t$b\t$(( $(date +%s) - t ))\t$(md5sum $R/sub/$n.mp4 | cut -c1-32)\t$(stat -c %s $R/sub/$n.mp4)\t$(date '+%H:%M')" >> $R/done_sub.tsv
  else echo "FAIL sub $n frames=$c" >> $R/logs/fail.log; fi
}
export -f one_base one_sub

case "$1" in
  base) echo "start base $(date '+%F %T')" >> $R/logs/drive.log
        list base | xargs -P $W -L 1 bash -c 'one_base $0 $1 $2'
        echo "end base $(date '+%F %T') pending=$(list base | wc -l)" >> $R/logs/drive.log ;;
  sub)  echo "start sub $(date '+%F %T')" >> $R/logs/drive.log
        list sub | xargs -P $W -L 1 bash -c 'one_sub $0 $1 $2'
        echo "end sub $(date '+%F %T') pending=$(list sub | wc -l)" >> $R/logs/drive.log ;;
  status) echo "base pending: $(list base | wc -l) / 34   sub pending: $(list sub | wc -l) / 34" ;;
esac
