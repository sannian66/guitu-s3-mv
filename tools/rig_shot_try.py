#!/usr/bin/env python3
"""tools/rig_shot_try.py — 把收窄后的 PoseRig 接进真实镜头做「替换后渲染」实验（**不改别人的文件**）

只用三种能力（用户 19:2x 拍板）：
  · 整姿势键帧替换  key='idle'/'raise'/'slash'/'draw'
  · 表情贴脸        expr='angry'/'smirk'（静态，镜内不变）
  · 角度交叉溶解    angle + angle_from + mix（只在切点 1~2 帧）
不做任何蒙皮/骨架变形。

做法：不碰 units/ 下任何源码，只在运行时把镜头对象里的精灵层（self.sp / self.w1..w3）换成
`RigWrap`（把 SpriteLayer.draw() 的 (anchor, scale) 翻译成 play() 的 (dst 脚底, h 身高)），
同一进程渲两遍（旧=原样，新=替换），再拼左右分屏 mp4。

用法（用 3.12 venv，别用系统 python）：
  PY=/Users/sannian/Downloads/鬼屠OP_new/out/full_sprite/chunks/local60_149c727_20261109/venv/bin/python
  OMP_NUM_THREADS=1 $PY tools/rig_shot_try.py --shot all --step 2 --repeat 2

产物（out/rig_test/）：
  shot_<ID>_old_vs_rig.mp4   左旧右新分屏（15fps，重复 repeat 遍凑 3~5s）
  shot_<ID>_cmp6.jpg         6 格静帧（3 个时间点 × 旧/新），每格标注用的 key
  shot_timings.json          逐帧耗时（旧 sprite vs 新 rig）
"""
import os, sys, json, math, time, argparse, subprocess, shutil

for _k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
           'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ.setdefault(_k, '1')
os.environ.setdefault('SPRITE_MODE', '1')          # 必须：SHOTS 表在 import 时决定 S043 用哪个类
os.environ.setdefault('SPRITE_FAST', '1')
os.environ.setdefault('GRADE_UNIFY', '0')
os.environ.setdefault('C1_CAM', '3')
os.environ.setdefault('C1_LYR', '3')
os.environ.setdefault('C1_RIG', 'live')
os.environ.setdefault('V4_FORCE', 'a_intro_verse1,b_pre1,b_verse2')

import numpy as np
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.environ.get('RIG_CODE', os.path.join(
    ROOT, 'out/full_sprite/chunks/full30_50589e0_20261109/code'))
OUT = os.path.join(ROOT, 'out', 'rig_test')
GEN = os.path.join(ROOT, 'assets', 'gen')
for _d in (CODE + '/units', CODE + '/lib', CODE):
    if _d not in sys.path:
        sys.path.insert(0, _d)

_src = os.path.join(ROOT, 'units', 'rig_sprite.py')
_dst = os.path.join(CODE, 'units', 'rig_sprite.py')
if os.path.abspath(_src) != os.path.abspath(_dst):
    if (not os.path.exists(_dst)) or open(_src, 'rb').read() != open(_dst, 'rb').read():
        shutil.copyfile(_src, _dst)
        print(f'[sync] rig_sprite.py → {_dst}')

from rig_sprite import PoseRig                     # noqa: E402
import chorus1                                     # noqa: E402


def clamp01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


class PassWrap:
    """原样转发，只统计 draw 耗时（旧版基线用）。"""

    def __init__(self, layer):
        self.layer = layer
        self.ms = 0.0
        self.calls = 0

    def __getattr__(self, k):
        return getattr(self.layer, k)

    def draw(self, *a, **kw):
        t = time.perf_counter()
        r = self.layer.draw(*a, **kw)
        self.ms += (time.perf_counter() - t) * 1000.0
        self.calls += 1
        return r


class RigWrap:
    """伪装成 SpriteLayer：draw() → PoseRig.play()。

    plan(t) 返回 dict(key=..., expr=None, mblur=0, h_scale=1.0, mix=1.0, angle_from=None, angle='front')
    mode='feet'：脚底对齐（put() 的 target_h 就是身高）；mode='face'：半身特写（按脸对齐）。
    """

    def __init__(self, layer, rig, plan, mode='feet', tag=''):
        self.layer = layer
        self.rig = rig
        self.plan = plan
        self.mode = mode
        self.tag = tag
        self._th = None
        self.ms = 0.0
        self.calls = 0
        self.last_key = '-'

    def __getattr__(self, k):
        return getattr(self.layer, k)

    def fit(self, target_h=None, foot=None, ref='bbox'):
        self._th = target_h
        return self.layer.fit(target_h, foot, ref)

    def _dst_h(self, anchor_src, anchor_dst, scale, hs=1.0):
        L = self.layer
        if self.mode == 'face':
            g = self.rig.G
            k = self.rig.ksrc                       # _geom 的数字都是 1024 测量空间
            px_per_rig = scale * (L.w / float(self.rig.work_w))
            h = g['headtop_u'] * (g['H'] * k) * px_per_rig * hs
            eye_norm = (g['eye'][0] / float(g['w']), g['eye_y'] / float(g['h']))
            ex = anchor_dst[0] + (eye_norm[0] - anchor_src[0]) * L.w * scale
            ey = anchor_dst[1] + (eye_norm[1] - anchor_src[1]) * L.h * scale
            return (ex, ey + h / g['headtop_u']), h
        h = (self._th if self._th else (L.bbox[3] - L.bbox[1]) * L.h * scale) * hs
        return (anchor_dst[0], anchor_dst[1]), h

    def draw(self, fr, t, anchor_src=(0.5, 1.0), anchor_dst=(960, 900), scale=1.0, rot=0.0,
             mblur=(0.0, 0.0), rim=None, grade=None, wrap=0.0, shade=None, keep_red=None,
             alpha=1.0, defocus=0.0, look=None, **kw):
        pl = self.plan(t, self) or {}
        key = pl.pop('key', 'idle')
        expr = pl.pop('expr', None)
        hs = pl.pop('h_scale', 1.0)
        if pl.get('mblur') is None:
            pl['mblur'] = mblur
        kr = pl.pop('keep_red', keep_red)
        dst, h = self._dst_h(anchor_src, anchor_dst, scale, hs)
        self.last_key = key + (f'+{expr}' if expr else '')
        a = time.perf_counter()
        r = self.rig.play(fr, t, key, dst=dst, h=h, expr=expr, rim=rim, grade=grade,
                          alpha=alpha, defocus=defocus, wrap=wrap, shade=shade,
                          keep_red=kr, look=look, **pl)
        self.ms += (time.perf_counter() - a) * 1000.0
        self.calls += 1
        return r


# ---------------------------------------------------------------- 三个镜头的「新」方案
def plan_S039(t, o):
    """缓行：**不做骨架**。两档 idle 微差（身高 800 / 793 交替 = 每步轻微下沉）+ 位移交给原镜头。"""
    ph = ((t - o.t0) * 1.6) % 1.0
    step = abs(math.sin(math.pi * ph * 2))
    return dict(key='idle', h_scale=1.0 - 0.009 * step)


def plan_S043(t, o):
    """特写：镜内只用一张 idle + 静态表情贴片（angry），不做转头/渐变。"""
    # keep_red=0：特写画面里没有红色戏服元素，关掉「保色红」——否则贴片边缘会被当暗红加饱和，
    # 在眉毛上烧出一条红痕（实测）。
    return dict(key='idle', expr='angry', keep_red=0.0)


def plan_S045_w1(t, o):
    return dict(key='raise')                       # 起手＝举刀键帧


def plan_S045_w2(t, o):
    return dict(key='slash', mblur=(-14, 0))       # 旋斩＝落刀键帧 + 水平甩动模糊


def plan_S045_w3(t, o):
    return dict(key='slash', mblur=(-8, 0))


SHOTS = {
    'S039': dict(t0=75.186, t1=76.579, mode='feet', layers=[('sp', plan_S039)],
                 rig='walk', note='idle 两档微差（身高 ±0.9%）'),
    'S043': dict(t0=82.059, t1=82.988, mode='face', layers=[('sp', plan_S043)],
                 rig='s043', note="idle + expr='angry'（静态贴一次）"),
    'S045': dict(t0=84.100, t1=85.287, mode='feet',
                 layers=[('w1', plan_S045_w1), ('w2', plan_S045_w2), ('w3', plan_S045_w3)],
                 rig='full', note="key='raise' → key='slash' + mblur"),
}

_RIGS = {}


def make_rig(shot):
    got = _RIGS.get(shot)
    if got is not None:
        return got
    kind = SHOTS[shot]['rig']
    if kind == 'walk':                              # 单图 rig：就用这张走路立绘（保住原美术）
        got = PoseRig(images={'idle': os.path.join(GEN, 'S039', 'walk_cut.png')}, work_w=2048)
    elif kind == 's043':                            # 单图 rig：S043 半身特写
        got = PoseRig(images={'idle': os.path.join(GEN, 'hero', 'S043_cut.png')}, work_w=2048)
    else:                                           # 全身多角度 + 键帧 + 表情
        got = PoseRig(base=os.path.join(GEN, 'char'), work_w=1024)
    got.warm()
    _RIGS[shot] = got
    return got


def patch(ch, sid, new=True):
    lay = ch.byid[sid]
    lay.render(lay.t0 + 0.02)
    obj = lay.obj
    cfg = SHOTS[sid]
    out = []
    for attr, fn in cfg['layers']:
        base = getattr(obj, attr)
        w = (RigWrap(base, make_rig(sid), fn, mode=cfg['mode'], tag=attr) if new else PassWrap(base))
        w.t0 = cfg['t0']
        setattr(obj, attr, w)
        out.append(w)
    return out


def render_seq(ch, times):
    frs, ts = [], []
    for t in times:
        a = time.perf_counter()
        fr, ca = ch.frame(t)
        ts.append(time.perf_counter() - a)
        frs.append(np.clip(fr, 0, 1))
    return frs, ts


def tile(fr, label, sub):
    im = cv2.resize(np.clip(fr, 0, 1), (960, 540), interpolation=cv2.INTER_AREA)
    im = (im * 255).astype(np.uint8)[..., ::-1].copy()
    cv2.rectangle(im, (0, 496), (960, 540), (14, 14, 16), -1)
    cv2.putText(im, label, (12, 518), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (238, 238, 244), 1, cv2.LINE_AA)
    cv2.putText(im, sub, (12, 534), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (150, 175, 210), 1, cv2.LINE_AA)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shot', default='all')
    ap.add_argument('--step', type=int, default=2, help='每 N 帧渲一帧（默认 2 → 15fps）')
    ap.add_argument('--repeat', type=int, default=2, help='分屏视频里重复几遍（凑 3~5s）')
    ap.add_argument('--fps', type=float, default=30.0)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    ids = list(SHOTS) if args.shot == 'all' else args.shot.split(',')

    report = {}
    for sid in ids:
        cfg = SHOTS[sid]
        f0 = int(round((cfg['t0'] + 0.08) * args.fps))
        f1 = int(round((cfg['t1'] - 0.08) * args.fps))
        frames = list(range(f0, f1, args.step))
        times = [f / args.fps for f in frames]
        print(f'\n=== {sid}  frames {f0}..{f1} step {args.step} → {len(times)} 帧  方案：{cfg["note"]}',
              flush=True)

        ch_old = chorus1.X()
        wraps_old = patch(ch_old, sid, new=False)
        frs_old, ts_old = render_seq(ch_old, times)

        ch_new = chorus1.X()
        wraps_new = patch(ch_new, sid, new=True)
        frs_new, ts_new = render_seq(ch_new, times)
        keys_used = sorted({w.last_key for w in wraps_new})

        d_old, d_new = float(np.mean(ts_old)), float(np.mean(ts_new))
        sp_old = sum(w.ms for w in wraps_old) / max(1, len(times))
        sp_new = sum(w.ms for w in wraps_new) / max(1, len(times))
        report[sid] = dict(n=len(times), old_mean=round(d_old, 3), new_mean=round(d_new, 3),
                           delta=round(d_new - d_old, 3), sprite_old_ms=round(sp_old, 1),
                           rig_new_ms=round(sp_new, 1), sprite_delta_ms=round(sp_new - sp_old, 1),
                           keys=keys_used, note=cfg['note'])
        print(f'[time] {sid} 整帧 旧 {d_old*1000:.0f} → 新 {d_new*1000:.0f}ms (Δ{(d_new-d_old)*1000:+.0f})'
              f' | 人物 旧 {sp_old:.0f} → 新 {sp_new:.0f}ms (Δ{sp_new-sp_old:+.0f}) | key={keys_used}',
              flush=True)

        # ---- 分屏 mp4
        tmp = os.path.join(OUT, f'_tmp_{sid}')
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp, exist_ok=True)
        k = 0
        for rep in range(max(1, args.repeat)):
            for a, b in zip(frs_old, frs_new):
                left = tile(a, '旧：单张立绘 sprite', '原方案')
                right = tile(b, f'新：PoseRig   key={keys_used[0] if len(keys_used) == 1 else "/".join(keys_used)}',
                             cfg['note'])
                both = np.concatenate([left, right], 1)
                cv2.imwrite(os.path.join(tmp, f'f{k:04d}.png'), both)
                k += 1
        mp4 = os.path.join(OUT, f'shot_{sid}_old_vs_rig.mp4')
        r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', f'{args.fps/args.step:.3f}',
                            '-i', os.path.join(tmp, 'f%04d.png'), '-c:v', 'libx264', '-crf', '18',
                            '-pix_fmt', 'yuv420p', mp4], capture_output=True, text=True)
        shutil.rmtree(tmp, ignore_errors=True)
        print(f'[out] {mp4} ({os.path.getsize(mp4)/1e6:.1f}MB)' if r.returncode == 0
              else f'[ffmpeg] FAIL {r.stderr[:300]}', flush=True)

        # ---- 6 格静帧（3 时间点 × 旧/新，每格标 key）
        idx = [0, len(times) // 2, len(times) - 1]
        rows = []
        for i in idx:
            rows.append(tile(frs_old[i], f'旧 sprite   t={times[i]:.2f}s', f'{sid} 原方案'))
            rows.append(tile(frs_new[i], f'新 PoseRig   t={times[i]:.2f}s', cfg['note']))
        grid = np.zeros((540 * 3, 960 * 2, 3), np.uint8)
        for j, im in enumerate(rows):
            r_, c_ = j // 2, j % 2
            grid[r_ * 540:(r_ + 1) * 540, c_ * 960:(c_ + 1) * 960] = im
        jpg = os.path.join(OUT, f'shot_{sid}_cmp6.jpg')
        cv2.imwrite(jpg, grid, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f'[out] {jpg}', flush=True)

    fp = os.path.join(OUT, 'shot_timings.json')
    old = {}
    if os.path.exists(fp):
        try:
            old = json.load(open(fp))
        except Exception:
            old = {}
    old.update(report)
    json.dump(old, open(fp, 'w'), ensure_ascii=False, indent=2)
    print(f'\n[out] {fp}')
    for k, v in old.items():
        print(f'  {k}: 整帧 {v["old_mean"]*1000:.0f}→{v["new_mean"]*1000:.0f}ms (Δ{v["delta"]*1000:+.0f})'
              f' | 人物 {v.get("sprite_old_ms",0):.0f}→{v.get("rig_new_ms",0):.0f}ms'
              f' (Δ{v.get("sprite_delta_ms",0):+.0f}) | key={v.get("keys")}')


if __name__ == '__main__':
    main()
