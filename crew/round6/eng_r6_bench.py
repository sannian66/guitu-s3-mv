"""r6-SPRITE 对拍工具：python3 crew/round6/eng_r6_bench.py <秒> <0|1> [out_dir]
SPRITE_FAST=<0|1> 渲一帧（与 tools/rf_sb.sh 同一路径 render_sprite_full.frame），记耗时与 SpriteLayer.draw 调用次数，
存 <out_dir>/<秒>_fast<k>.png（默认 out/round6/eng_r6），并把一行 JSON 追加到 <out_dir>/bench.jsonl。
随机种子固定（random / np.random），保证 0/1 两遍除精灵实现外完全同路径。多帧请外包 tools/cpu_slot.sh。"""
import os, sys, time, json, random
sec, fast = float(sys.argv[1]), sys.argv[2]
out = sys.argv[3] if len(sys.argv) > 3 else 'out/round6/eng_r6'
os.environ['SPRITE_FAST'] = fast
sys.path.insert(0, '/workspace/work/mv')
import numpy as np
import render_sprite_full as R            # 会 chdir 到仓库根、装好路径
import sprite as SP
n = [0]
_d = SP.SpriteLayer.draw
def draw(self, *a, **k):
    n[0] += 1; return _d(self, *a, **k)
SP.SpriteLayer.draw = draw
assert SP.FAST == (fast != '0')
random.seed(12345); np.random.seed(12345)
os.makedirs(out, exist_ok=True)
t0 = time.time()
img = R.frame(int(round(sec * R.FPS)), {})
dt = time.time() - t0
from PIL import Image
p = os.path.join(out, f'{sec:g}_fast{fast}.png')
Image.fromarray(img).save(p)
rec = dict(sec=sec, fast=int(fast), secs=round(dt, 2), draws=n[0], png=p)
print(json.dumps(rec, ensure_ascii=False))
with open(os.path.join(out, 'bench.jsonl'), 'a') as f: f.write(json.dumps(rec, ensure_ascii=False) + '\n')
