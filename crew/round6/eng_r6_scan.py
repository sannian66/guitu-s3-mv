"""r6-SPRITE 全片冒烟：一个进程按镜头表逐镜取中点渲一帧（SPRITE_FAST 取环境变量），记每帧 SpriteLayer.draw 次数/耗时/异常。
python3 crew/round6/eng_r6_scan.py <shots.json> <out.jsonl>   （外包 tools/cpu_slot.sh）"""
import os, sys, time, json, random, traceback
sys.path.insert(0, '/workspace/work/mv')
import numpy as np
import render_sprite_full as R
import sprite as SP
n = [0]; _d = SP.SpriteLayer.draw
def draw(self, *a, **k):
    n[0] += 1; return _d(self, *a, **k)
SP.SpriteLayer.draw = draw
shots = json.load(open(sys.argv[1])); out = open(sys.argv[2], 'a')
cache = {}
for g, sid, a, b in shots:
    t = (a + b) / 2; n[0] = 0; t0 = time.time(); err = None
    random.seed(12345); np.random.seed(12345)
    try: R.frame(int(round(t * R.FPS)), cache)
    except Exception as e: err = traceback.format_exc()[-600:]
    out.write(json.dumps(dict(g=g, id=sid, t=round(t, 3), draws=n[0], secs=round(time.time() - t0, 2), fast=SP.FAST, err=err), ensure_ascii=False) + '\n'); out.flush()
print('SCAN_DONE')
