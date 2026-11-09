#!/usr/bin/env python3
"""tools/rig_shot_try.py — 把 PoseRig 接进真实镜头做「替换后渲染」实验（**不改任何别人的文件**）

做法：不碰 units/ 下的任何源码，只在运行时把镜头对象里的精灵层（self.sp / self.w1..w3）
换成 `RigWrap`（一个把 `SpriteLayer.draw()` 的 (anchor, scale) 接口翻译成 `PoseRig.draw()`
的 (dst 脚底, h 身高) 接口的薄壳），然后同一进程里渲两遍：一遍原样（旧）、一遍替换（新），
再拼成左右分屏 mp4。

镜头：
  S039 缓行 75.186–76.579  旧 = 单张 walk 立绘 + 6px 上下 bob（被吐槽「像滑行」）
                           新 = 侧身 90°（body_turn/head_turn=1）＋ 骨架步态（重心下沉/摆动/肩胯对扭）
  S043 特写 82.059–82.988  旧 = 单张 S043 半身立绘（完全静止，只有运镜）
                           新 = 半身 rig（bust）：expr='angry' + 小转头 + 抬头/呼吸
  S045 旋斩 84.100–85.287  旧 = windup/spin/finish 三张精灵硬切
                           新 = key='raise' → key='slash'（整姿势键帧）+ 镜头自带的 mblur / 刀光

用法：
  PY=/Users/sannian/Downloads/鬼屠OP_new/out/full_sprite/chunks/local60_149c727_20261109/venv/bin/python
  OMP_NUM_THREADS=1 $PY tools/rig_shot_try.py --shot S039
  OMP_NUM_THREADS=1 $PY tools/rig_shot_try.py --shot all        # 三个都要（顺序跑，单进程）
  OMP_NUM_THREADS=1 $PY tools/rig_shot_try.py --shot S045 --step 2 --repeat 3

产物（out/rig_test/）：
  shot_<ID>_old_vs_rig.mp4   左旧右新分屏（默认 15fps，每个镜头重复 repeat 遍凑 3~5s）
  shot_<ID>_cmp.jpg          同帧三联/对比静帧
  shot_timings.json          逐帧耗时（旧 sprite vs 新 rig）与增量
"""
import os, sys, json, math, time, argparse, subprocess, shutil

for _k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
           'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ.setdefault(_k, '1')
os.environ.setdefault('SPRITE_MODE', '1')          # 必须：SHOTS 表在 import 时决定 S043 用哪个类
os.environ.setdefault('SPRITE_FAST', '1')
os.environ.setdefault('GRADE_UNIFY', '0')          # 按要求保持默认 0
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

# 把工程里的 rig 模块同步进快照（快照是构建产物，动它不影响别人）
_src = os.path.join(ROOT, 'units', 'rig_sprite.py')
_dst = os.path.join(CODE, 'units', 'rig_sprite.py')
if os.path.abspath(_src) != os.path.abspath(_dst):
    if (not os.path.exists(_dst)) or open(_src, 'rb').read() != open(_dst, 'rb').read():
        shutil.copyfile(_src, _dst)
        print(f'[sync] rig_sprite.py → {_dst}')

from rig_sprite import PoseRig                     # noqa: E402  （从快照 import，保证和成片同源）
import chorus1                                     # noqa: E402


# ---------------------------------------------------------------- 工具
def clamp01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


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
    """伪装成 SpriteLayer：draw() 转发给 PoseRig.draw()。

    mode='feet'：调用点给的是 (脚底锚点, scale)，用 fit(target_h) 记下的身高；
    mode='face'：半身特写（SpriteLayer 按脸锚点 + 画面宽度铺满），由脸宽反推 rig 的 h。
    """

    def __init__(self, layer, rig, pose_fn, mode='feet', tag='', t0=0.0):
        self.layer = layer
        self.rig = rig
        self.pose_fn = pose_fn
        self.mode = mode
        self.tag = tag
        self.t0 = t0
        self._th = None
        self.ms = 0.0
        self.calls = 0
        self.g = rig.G

    def __getattr__(self, k):                      # w / h / bbox / top / wind ... 全转给原层
        return getattr(self.layer, k)

    def fit(self, target_h=None, foot=None, ref='bbox'):
        self._th = target_h
        return self.layer.fit(target_h, foot, ref)

    def _dst_h(self, anchor_src, anchor_dst, scale):
        L = self.layer
        if self.mode == 'face':                    # 半身：用 rig 自己的脸几何对齐
            g = self.g
            px_per_rig = scale * (L.w / float(self.rig.work_w))
            h = g['headtop_u'] * g['H'] * px_per_rig
            eye_norm = (g['eye'][0] / float(self.rig.work_w), g['eye_y'] / float(g['h']))
            ex = anchor_dst[0] + (eye_norm[0] - anchor_src[0]) * L.w * scale
            ey = anchor_dst[1] + (eye_norm[1] - anchor_src[1]) * L.h * scale
            return (ex, ey + h / g['headtop_u']), h
        h = self._th if self._th else (L.bbox[3] - L.bbox[1]) * L.h * scale
        return (anchor_dst[0], anchor_dst[1]), h

    def draw(self, fr, t, anchor_src=(0.5, 1.0), anchor_dst=(960, 900), scale=1.0, rot=0.0,
             mblur=(0.0, 0.0), rim=None, grade=None, wrap=0.0, shade=None, keep_red=None,
             alpha=1.0, defocus=0.0, look=None, **kw):
        pose = self.pose_fn(t, self)
        dst, h = self._dst_h(anchor_src, anchor_dst, scale)
        a = time.perf_counter()
        r = self.rig.draw(fr, t, pose, dst=dst, h=h, look=look, rim=rim, grade=grade,
                          alpha=alpha, defocus=defocus, mblur=mblur, wrap=wrap,
                          shade=shade, keep_red=keep_red)
        self.ms += (time.perf_counter() - a) * 1000.0
        self.calls += 1
        return r


# ---------------------------------------------------------------- 各镜头的 rig 姿势
def pose_S039(t, o):
    """侧身缓行：骨架加「重心下沉 + 肩胯对扭 + 前后起伏」，去掉滑行感。"""
    ph = ((t - o.t0) * 1.6) % 1.0                  # 与原 S039Sprite 的 bob 同频
    s2 = math.sin(math.pi * 2 * ph)
    step = abs(s2)
    return dict(body_turn=1.0, head_turn=1.0,      # 身体/头都用真实 90° 侧身图（A-pose → 侧身）
                knee=0.045 + 0.030 * step,         # 每步重心下沉（脚底不动）
                lean=0.020 + 0.020 * s2,           # 前倾 + 轻微前后起伏
                twist=0.045 * s2,                  # 肩胯对扭
                head_pitch=-0.035 * step,
                arm_l=5.0 + 4.0 * s2, arm_r=3.0 - 3.0 * s2)


def pose_S043(t, o):
    """半身特写：小转头 + 表情（angry = 寒光）+ 抬头，去掉"完全静止"感。"""
    k = smooth((t - o.t0) / 0.45)
    return dict(expr='angry',
                head_turn=0.06 + 0.14 * k,
                head_pitch=0.06 - 0.05 * k,
                lean=0.04 * k, knee=0.02 * k)


def pose_S045_w1(t, o):
    """起手：举刀（键帧）"""
    return dict(key='raise', key_w=0.55, knee=0.05, lean=-0.02)


def pose_S045_w2(t, o):
    """旋斩：举刀 → 落刀 的整姿势键帧推进（镜头自己再叠 -10px 方向模糊）"""
    T_SPIN, T_HIT = 84.30, 84.50
    k = clamp01((t - T_SPIN) / (T_HIT - T_SPIN))
    return dict(key='slash', key_w=0.40 + 0.60 * k, knee=0.06 + 0.04 * k, lean=0.02 + 0.05 * k)


def pose_S045_w3(t, o):
    return dict(key='slash', key_w=1.0, knee=0.10, lean=0.05, head_pitch=-0.05)


SHOTS = {
    'S039': dict(t0=75.186, t1=76.579, mode='feet', build='sp', poses=[('sp', pose_S039)]),
    'S043': dict(t0=82.059, t1=82.988, mode='face', build='sp', poses=[('sp', pose_S043)]),
    'S045': dict(t0=84.100, t1=85.287, mode='feet', build='w1',
                 poses=[('w1', pose_S045_w1), ('w2', pose_S045_w2), ('w3', pose_S045_w3)]),
}
FACE_MODE = {'S043'}


# ---------------------------------------------------------------- 渲染
_RIGS = {}


def make_rig(shot):
    """每个镜头一个 rig 实例（S039/S045 共用全身 rig；S043 用半身特写 rig）。"""
    got = _RIGS.get(shot)
    if got is not None:
        return got
    if shot in FACE_MODE:
        path = os.path.join(GEN, 'hero', 'S043_cut.png')
        got = PoseRig(base=os.path.dirname(path),
                      angles=[('front', path, 0.0, 'both')], work_w=2048).warm()
    else:
        got = FULL_RIG
    _RIGS[shot] = got
    return got


def patch(ch, sid, new=True):
    """强制构建镜头对象，把精灵层换成 RigWrap（new=True）或只计时的 PassWrap（new=False）。"""
    lay = ch.byid[sid]
    lay.render(lay.t0 + 0.02)                       # 触发 __init__
    obj = lay.obj
    cfg = SHOTS[sid]
    made = []
    for attr, fn in cfg['poses']:
        base = getattr(obj, attr)
        w = (RigWrap(base, make_rig(sid), fn, mode=cfg['mode'], tag=attr, t0=cfg['t0'])
             if new else PassWrap(base))
        setattr(obj, attr, w)
        made.append(w)
    return made


def render_seq(ch, times):
    frs, ts = [], []
    for t in times:
        a = time.perf_counter()
        fr, ca = ch.frame(t)
        ts.append(time.perf_counter() - a)
        frs.append(np.clip(fr, 0, 1))
    return frs, ts


def split_tile(fr, label, sub):
    im = cv2.resize(np.clip(fr, 0, 1), (960, 540), interpolation=cv2.INTER_AREA)
    im = (im * 255).astype(np.uint8)[..., ::-1].copy()       # BGR for cv2 text
    cv2.rectangle(im, (0, 500), (960, 540), (14, 14, 16), -1)
    cv2.putText(im, label, (12, 522), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (235, 235, 240), 1, cv2.LINE_AA)
    cv2.putText(im, sub, (12, 536), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (150, 175, 210), 1, cv2.LINE_AA)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shot', default='all', help='S039 / S043 / S045 / all')
    ap.add_argument('--step', type=int, default=2, help='每 N 帧渲一帧（默认 2 → 15fps）')
    ap.add_argument('--repeat', type=int, default=3, help='分屏视频里把这个镜头放几遍（凑 3~5s）')
    ap.add_argument('--fps', type=float, default=30.0, help='时间轴帧率（成片是 30）')
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    ids = list(SHOTS) if args.shot == 'all' else args.shot.split(',')

    global FULL_RIG
    FULL_RIG = PoseRig(base=os.path.join(GEN, 'char'), work_w=1024)     # S039/S045 共用
    print('[rig] warm…', flush=True)
    t = time.perf_counter()
    FULL_RIG.warm()
    print(f'[rig] warm {time.perf_counter() - t:.1f}s', flush=True)

    report = {}
    for sid in ids:
        cfg = SHOTS[sid]
        # 两端各让 0.08s，避开切点转场帧（否则最后一格可能是下一个镜头的交叉溶）
        f0 = int(round((cfg['t0'] + 0.08) * args.fps))
        f1 = int(round((cfg['t1'] - 0.08) * args.fps))
        frames = list(range(f0, f1, args.step))
        times = [f / args.fps for f in frames]
        print(f'\n=== {sid}  frames {f0}..{f1} step {args.step} → {len(times)} 帧 ===', flush=True)

        # ---- 旧：原样（只加计时外壳）
        ch_old = chorus1.X()
        wraps_old = patch(ch_old, sid, new=False)
        frs_old, ts_old = render_seq(ch_old, times)
        # ---- 新：换 rig
        ch_new = chorus1.X()
        wraps_rig = patch(ch_new, sid, new=True)
        print(f'[patch] {sid}: {[w.tag for w in wraps_rig]}', flush=True)
        frs_new, ts_new = render_seq(ch_new, times)

        d_old, d_new = float(np.mean(ts_old)), float(np.mean(ts_new))
        sp_old = sum(w.ms for w in wraps_old) / max(1, len(times))
        sp_new = sum(w.ms for w in wraps_rig) / max(1, len(times))
        report[sid] = dict(n=len(times), old_mean=round(d_old, 3), new_mean=round(d_new, 3),
                           delta=round(d_new - d_old, 3),
                           old_min=round(float(np.min(ts_old)), 3),
                           new_min=round(float(np.min(ts_new)), 3),
                           sprite_old_ms=round(sp_old, 1), rig_new_ms=round(sp_new, 1),
                           sprite_delta_ms=round(sp_new - sp_old, 1))
        print(f'[time] {sid} 整帧 旧 {d_old*1000:.0f}ms → 新 {d_new*1000:.0f}ms (Δ{(d_new-d_old)*1000:+.0f})'
              f' | 人物绘制 旧 {sp_old:.0f}ms → 新 {sp_new:.0f}ms (Δ{sp_new-sp_old:+.0f})', flush=True)

        # ---- 分屏 mp4
        tmp = os.path.join(OUT, f'_tmp_{sid}')
        os.makedirs(tmp, exist_ok=True)
        n_old, n_new = ('旧：单张立绘 sprite', '新：PoseRig')
        subs = {'S039': 'walk 立绘 + 6px bob（滑行感）| 侧身 90° + 骨架步态',
                'S043': 'S043 半身立绘，完全静止 | 半身 rig：expr angry + 小转头',
                'S045': '3 张精灵硬切 | 键帧 raise→slash + mblur'}[sid]
        k = 0
        for rep in range(max(1, args.repeat)):
            for i, (a, b) in enumerate(zip(frs_old, frs_new)):
                tsec = times[i]
                left = split_tile(a, n_old, subs.split('|')[0].strip())
                right = split_tile(b, n_new, subs.split('|')[-1].strip())
                both = np.concatenate([left, right], 1)
                cv2.putText(both, f'{sid}   t={tsec:.2f}s   (左 旧 / 右 新)', (12, 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (240, 240, 245), 1, cv2.LINE_AA)
                cv2.imwrite(os.path.join(tmp, f'f{k:04d}.png'), both)
                k += 1
        mp4 = os.path.join(OUT, f'shot_{sid}_old_vs_rig.mp4')
        r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', f'{args.fps/args.step:.3f}',
                            '-i', os.path.join(tmp, 'f%04d.png'), '-c:v', 'libx264', '-crf', '18',
                            '-pix_fmt', 'yuv420p', '-vf', 'scale=1920:540', mp4],
                           capture_output=True, text=True)
        shutil.rmtree(tmp, ignore_errors=True)
        if r.returncode != 0:
            print('[ffmpeg] FAIL', r.stderr[:400], flush=True)
        else:
            print(f'[out] {mp4}  ({os.path.getsize(mp4)/1e6:.1f}MB)', flush=True)

        # ---- 同帧静帧
        mid = len(times) // 2
        rows = [np.concatenate([split_tile(frs_old[i], '旧 sprite', f'{sid} t={times[i]:.2f}s'),
                                split_tile(frs_new[i], '新 PoseRig', subs)],
                               1) for i in (0, mid, len(times) - 1)]
        jpg = os.path.join(OUT, f'shot_{sid}_cmp.jpg')
        cv2.imwrite(jpg, np.concatenate(rows, 0), [cv2.IMWRITE_JPEG_QUALITY, 92])
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
        print(f'  {k}: 整帧 {v["old_mean"]*1000:.0f}→{v["new_mean"]*1000:.0f}ms '
              f'(Δ{v["delta"]*1000:+.0f}) | 人物 {v.get("sprite_old_ms",0):.0f}→'
              f'{v.get("rig_new_ms",0):.0f}ms (Δ{v.get("sprite_delta_ms",0):+.0f})')


if __name__ == '__main__':
    main()
