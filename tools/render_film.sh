#!/bin/bash
# tools/render_film.sh — 全片分块渲染入口（1080p30，7240 帧 = 241.333s）
#
# 来源：feat/quality-pass e9ea92b/5583752（Mac 版：devsnap 快照 + out/devsnap/prun.py + lyric_uni/grade 钩子）。
# 第六轮移植到 main（audit-qp2）：main 没有 prun.py / lyric_uni / grade_unify，也不需要快照
# （ROOT 写死 /workspace/work/mv），所以改成直接调 main 的
#   python3 render_sprite_full.py seg F0 F1 out.mp4      （= sections 路由 + 副歌一 + subtitle.py 底部字幕 + GCUT）
# 每块外包 tools/cpu_slot.sh（沙箱只有 2 核，和单帧渲染共用两个槽）。
#
# 用法：
#   tools/render_film.sh --help
#   tools/render_film.sh --dry-run          # 只列待渲块，不渲
#   tools/render_film.sh                    # 后台并行渲全部缺失块 → 拼接 + 混音 + ffprobe 校验
#   tools/render_film.sh --resume           # 同上（已完成块自动跳过；默认就是续渲）
#   tools/render_film.sh --finalize         # 只做拼接 + 混音 + 校验（所有块都在时）
#   tools/render_film.sh --status           # 已完成块数 / 总块数
# 环境变量：
#   OUT=out/film_r6   产物目录（chunks/ logs/ delivery/）
#   W=2               并发块数（2 核，>2 只会在 cpu_slot 上排队）
#   FINE=240          每块帧数（240 = 8s；块边界会 random.seed(F0)，注意 STATUS_r6「229.0 未设种子」接缝）
#   F0=0 F1=7240      只渲某个帧区间（调试用）
# 产物：$OUT/delivery/谁定正邪_MV_1080p30_master_crf17.mp4（+ RESULT.txt）
set -e
cd "$(dirname "$0")/.."
ROOT=$(pwd)
PY="${PY:-python3}"
OUT="${OUT:-$ROOT/out/film_r6}"; case "$OUT" in /*) ;; *) OUT="$ROOT/$OUT";; esac
W="${W:-2}"
FINE="${FINE:-240}"
F0="${F0:-0}"; F1="${F1:-7240}"; N=7240
AUDIO="$ROOT/audio/谁定正邪.mp3"
MASTER="$OUT/delivery/谁定正邪_MV_1080p30_master_crf17.mp4"

usage() { sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; }

chunks() {   # 输出待渲块 "a b"
  local a=$F0 b
  while [ "$a" -lt "$F1" ]; do
    b=$((a + FINE)); [ "$b" -gt "$F1" ] && b=$F1
    [ -s "$OUT/chunks/f_$(printf %05d $a)_$(printf %05d $b).mp4" ] || echo "$a $b"
    a=$b
  done
}

nframes() { ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$1" 2>/dev/null || echo 0; }

render_one() {   # $1=a $2=b ：渲一块 → 校验帧数 → 改名
  local a=$1 b=$2 tag; tag="f_$(printf %05d $a)_$(printf %05d $b)"
  local part="$OUT/chunks/$tag.partial.mp4" dest="$OUT/chunks/$tag.mp4"
  "$ROOT/tools/cpu_slot.sh" "$PY" "$ROOT/render_sprite_full.py" seg "$a" "$b" "$part" >> "$OUT/logs/$tag.log" 2>&1 || { echo "FAIL $tag" ; return 1; }
  local n; n=$(nframes "$part")
  if [ "$n" = "$((b - a))" ]; then mv -f "$part" "$dest"; echo "OK $tag"; else echo "BADCOUNT $tag $n/$((b - a))"; return 1; fi
}

finalize() {
  local missing; missing=$(F0=0 F1=$N chunks | wc -l)
  [ "$missing" = 0 ] || { echo "还缺 $missing 块，不能拼接"; exit 1; }
  mkdir -p "$OUT/delivery"
  ls "$OUT"/chunks/f_*.mp4 | grep -v partial | sort | sed "s|^|file '|; s|$|'|" > "$OUT/chunks/concat.txt"
  ffmpeg -y -v error -f concat -safe 0 -i "$OUT/chunks/concat.txt" -i "$AUDIO" -map 0:v:0 -map 1:a:0 \
         -c:v copy -c:a aac -b:a 320k -shortest -movflags +faststart "$MASTER"
  local info; info=$(ffprobe -v error -select_streams v:0 -count_packets \
        -show_entries stream=width,height,r_frame_rate,pix_fmt,nb_read_packets -of csv=p=0 "$MASTER")
  local au; au=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$MASTER")
  ffmpeg -v error -xerror -i "$MASTER" -f null - && dec=OK || dec=FAIL
  echo "video=$info audio=$au decode=$dec  (期望 1920,1080,yuv420p,30/1,7240 + aac)" | tee "$OUT/RESULT.txt"
  echo "HEAD=$(git rev-parse --short HEAD) $(date '+%F %T %Z')" >> "$OUT/RESULT.txt"
}

case "$1" in
  -h|--help) usage; exit 0;;
  --dry-run) echo "OUT=$OUT W=$W FINE=$FINE 区间 $F0–$F1"; chunks | awk '{n++; print "  待渲 " $1 "–" $2} END {print "共 " n+0 " 块"}'; exit 0;;
  --status) t=$(( (F1 - F0 + FINE - 1) / FINE )); m=$(chunks | wc -l); echo "已完成 $((t - m))/$t 块（$OUT）"; exit 0;;
  --finalize) finalize; exit 0;;
  ""|--resume) ;;
  --run-chunks) ;;   # 内部：后台执行体
  *) echo "未知参数 $1"; usage; exit 2;;
esac

[ -f "$ROOT/render_sprite_full.py" ] && [ -x "$ROOT/tools/cpu_slot.sh" ] && [ -f "$AUDIO" ] || { echo "缺 render_sprite_full.py / tools/cpu_slot.sh / $AUDIO"; exit 1; }
mkdir -p "$OUT/chunks" "$OUT/logs"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PY OUT FINE F0 F1 ROOT

if [ "$1" = "--run-chunks" ]; then
  export -f render_one nframes
  chunks | xargs -P "$W" -L 1 bash -c 'render_one $0 $1' || echo "有块失败，见 $OUT/logs/；重跑本脚本续渲"
  [ "$F0" = 0 ] && [ "$F1" = "$N" ] && [ "$(chunks | wc -l)" = 0 ] && finalize
  exit 0
fi

echo "== 后台渲染 $(chunks | wc -l) 块（W=$W FINE=$FINE，区间 $F0–$F1）→ $OUT"
nohup "$0" --run-chunks > "$OUT/logs/film.log" 2>&1 &
echo "   PID $!   日志 $OUT/logs/film.log   进度 $0 --status"
echo "   暂停：pkill -f 'render_film.sh --run-chunks'; pkill -f 'render_sprite_full.py seg'   续渲：$0 --resume"
