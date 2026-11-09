#!/usr/bin/env python3
"""tools/rig_pose_test.py — PoseRig（units/rig_sprite.py）姿势样张 + 与单张立绘 sprite 的对比

渲一组姿势，输出：
  out/rig_test/rig_pose_sheet.jpg   每个姿势一格（标注姿势参数 + 单帧耗时）
  out/rig_test/rig_vs_sprite.jpg    与「现有单张立绘 sprite（units/sprite.py）」的对比
  out/rig_test/timings.json         逐姿势耗时（min/median，毫秒）

用法：
  cd /Users/sannian/Downloads/鬼屠OP_new
  OMP_NUM_THREADS=1 ../local60_*/venv/bin/python tools/rig_pose_test.py     # 或系统 python3
  python3 tools/rig_pose_test.py --h 680 --reps 4

注意：单进程、线程数限死（本脚本自己设 OMP/OPENBLAS/MKL = 1），别并发跑多份。
"""
import os, sys, json, math, time, argparse

for _k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
           'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ.setdefault(_k, '1')

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from units.rig_sprite import PoseRig                      # noqa: E402
from units.sprite import SpriteLayer                      # noqa: E402

OUT = os.path.join(ROOT, 'out', 'rig_test')
FONT = None
for p in ('/System/Library/Fonts/Supplemental/Songti.ttc',
          '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
          '/System/Library/Fonts/PingFang.ttc'):
    if os.path.exists(p):
        try:
            FONT = ImageFont.truetype(p, 22)
            FONT_S = ImageFont.truetype(p, 17)
            break
        except Exception:
            pass
if FONT is None:
    FONT = FONT_S = ImageFont.load_default()

# 检查用的调色（比生产默认亮一点，看得清形变缺陷）
GRADE = dict(expo=0.95, sat=0.78, tint=(0.95, 0.98, 1.04), lift=0.006, gamma=1.05)
RIM = dict(col=(0.62, 0.74, 1.0), amt=1.1, dir=(-0.8, -0.6))

# (名字, pose, 额外 draw 参数, 取景：None=全身  'head'=头部放大)
POSES = [
    ('idle', dict(), {}, None),
    ('head_turn −0.6（左）', dict(head_turn=-0.6), {}, 'head'),
    ('head_turn 0（正）', dict(head_turn=0.0), {}, 'head'),
    ('head_turn +0.6（右）', dict(head_turn=0.6), {}, 'head'),
    ('arm_r 45°', dict(arm_r=45), {}, None),
    ('arm_r 90°', dict(arm_r=90), {}, None),
    ('lean 0.2（后仰）', dict(lean=0.2), {}, None),
    ('slash 中段 key_w .5', dict(key='slash', key_w=0.5), dict(mblur=7), None),
    ('slash 落刀 key_w 1', dict(key='slash', key_w=1.0), {}, None),
    ('expr angry（脸部放大）', dict(expr='angry'), {}, 'head'),
    ('expr smirk（脸部放大）', dict(expr='smirk'), {}, 'head'),
    ('expr look（脸部放大，配 turn 0.5）', dict(expr='look', head_turn=0.5), {}, 'head'),
    ('raise 举刀 key_w 1', dict(key='raise'), {}, None),
]


def bg_plate(w, h, dark=True):
    """深灰渐变底（和成片黑底接近，又不至于看不清黑衣轮廓）。"""
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    top = 0.055 if dark else 0.5
    bot = 0.015 if dark else 0.62
    g = top + (bot - top) * y
    img = np.repeat(g[:, :, None], 3, 2).astype(np.float32)
    vign = np.clip(1.0 - 0.55 * (((np.arange(w)[None, :] / w - .5) ** 2 +
                                  (np.arange(h)[:, None] / h - .5) ** 2) / 0.5), 0.35, 1)
    return img * vign[..., None]


def tile(fr, label, sub, w, h):
    im = Image.fromarray((np.clip(fr, 0, 1) * 255).astype(np.uint8))
    im = im.resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.rectangle([0, h - 52, w, h], fill=(12, 12, 14))
    d.text((10, h - 48), label, font=FONT_S, fill=(226, 226, 230))
    d.text((10, h - 25), sub, font=FONT_S, fill=(150, 170, 200))
    return np.asarray(im)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--h', type=float, default=680, help='人物总高（脚底→头顶）像素')
    ap.add_argument('--reps', type=int, default=4, help='每姿势计时重复次数')
    ap.add_argument('--w', type=int, default=560, help='单格画面宽')
    ap.add_argument('--tile', type=int, default=560, help='样张每格宽')
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    t0 = time.perf_counter()
    rig = PoseRig(base=os.path.join(ROOT, 'assets', 'gen', 'char'), work_w=1024)
    t_init = time.perf_counter() - t0
    tw = time.perf_counter(); rig.warm(); t_warm = time.perf_counter() - tw
    print(f'[rig] warm {t_warm:.2f}s（预解码全部贴图，管线载入时调一次即可）')
    print(f'[rig] init {t_init:.2f}s  (front geom: H={rig.G["H"]:.0f}px, '
          f'facew={rig.G["facew"]:.0f}px, 头/脚比例 headtop_u={rig.G["headtop_u"]:.3f})')

    # ---------- 1) 姿势样张 --------------------------------------------------
    TW, TH = args.tile, int(args.tile * 1.27)

    def render(pose, kw, frame, zoom='full', jitter=0.0, timed=True):
        """画一格。计时永远用全身尺度（h=frame）；zoom='head' 再单独渲一次放大图做内嵌特写。"""
        fr = bg_plate(TW, TH)
        t = time.perf_counter()
        fr, a = rig.draw(fr, jitter, pose, dst=(TW / 2, TH - 26), h=frame, grade=GRADE, rim=RIM, **kw)
        dt = (time.perf_counter() - t) * 1000.0
        if zoom == 'head':
            hz = frame * 2.15
            Hf = int(TH * 2.15)
            big = bg_plate(TW, Hf)
            big, _ = rig.draw(big, jitter, pose, dst=(TW / 2, Hf - 26), h=hz, grade=GRADE,
                              rim=RIM, **kw)
            hu = hz / rig.G['headtop_u']
            cw = int(0.40 * hu)                      # 取景宽（单位空间 0.40）
            cy = (Hf - 26) - hu * 1.02
            x0 = int(np.clip(TW / 2 - cw / 2, 0, TW - 2))
            y0 = int(np.clip(cy - cw * TH / TW * 0.55, 0, Hf - 2))
            fr = big[y0:y0 + int(cw * TH / TW), x0:x0 + cw]
        return fr, dt

    # 预热（首帧含贴图解码 / 距离变换 / inpaint 表，后面才是稳态）
    for _, pose, kw, _z in POSES:
        render(pose, kw, args.h, timed=False)

    timings = {}
    tiles = []
    for name, pose, kw, zoom in POSES:
        ts, fr = [], None
        for i in range(args.reps):
            fr, dt = render(pose, kw, args.h, zoom, 0.11 * i)
            ts.append(dt)
        med = float(np.median(ts))
        timings[name] = dict(min=round(min(ts), 1), med=round(med, 1), pose=pose,
                             extra={k: v for k, v in kw.items()})
        print(f'  {name:24s} {med:6.1f} ms  (min {min(ts):.1f})')
        sub = ' '.join(f'{k}={v}' for k, v in pose.items()) or '{}'
        if kw:
            sub += '  ' + ' '.join(f'{k}={v}' for k, v in kw.items())
        tiles.append(tile(fr, f'{name}   {med:.0f} ms', sub, TW, TH))

    cols = 4
    rows = math.ceil(len(tiles) / cols)
    T = (TW, TH)
    sheet = np.full((rows * T[1] + 64, cols * T[0], 3), 14, np.uint8)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet[64 + r * T[1]:64 + (r + 1) * T[1], c * T[0]:(c + 1) * T[0]] = t
    im = Image.fromarray(sheet)
    d = ImageDraw.Draw(im)
    d.text((16, 16), f'PoseRig 姿势样张  ·  h={args.h:.0f}px  ·  单帧 {min(v["med"] for v in timings.values()):.0f}'
                     f'–{max(v["med"] for v in timings.values()):.0f} ms（8 核机器、单进程、线程=1）',
           font=FONT, fill=(232, 232, 236))
    d.text((16, 42), 'assets/gen/char 生图立绘（绿幕抠像）→ 权重场蒙皮 + 多角度头部替换 + 整姿势键帧',
           font=FONT_S, fill=(140, 160, 190))
    p1 = os.path.join(OUT, 'rig_pose_sheet.jpg')
    im.save(p1, quality=92)
    print(f'[out] {p1}')

    # ---------- 2) 与单张立绘 sprite 对比
    cmp_tiles = []
    # (a) 现有 sprite.py 单张立绘
    spr = SpriteLayer(os.path.join(ROOT, 'assets', 'gen', 'char', 'hero_front_cut.png'), work_w=1024)
    hh_c = TH * 0.93
    ts = []
    W2, H2 = 1920, 1080      # sprite.py 是 1920x1080 画布写死的，必须在原画布上渲，再裁成竖幅格子
    for i in range(args.reps):
        fr = bg_plate(W2, H2)
        # sprite 的接口：anchor 用包围盒中心 x / 脚底，scale = 目标高 / bbox 高
        (axr, ayr), sc = spr.fit(hh_c, ref='bbox')
        axr, ayr, sc = float(axr), float(ayr), float(sc)
        t = time.perf_counter()
        fr, a = spr.draw(fr, 0.0, (axr, ayr), (W2 // 2, H2 - 40), sc, grade=GRADE, rim=RIM,
                         wind_amp=0.0)
        ts.append((time.perf_counter() - t) * 1000.0)
    spr_ms = float(np.median(ts))
    hu_s = hh_c / 1.116
    cw = int(min(W2, TH * 0.80))
    cy = (H2 - 40) - 0.56 * hu_s
    ys0 = int(np.clip(cy - TH / 2, 0, H2 - TH))
    xs0 = int(np.clip(W2 / 2 - cw / 2, 0, W2 - cw))
    fr = fr[ys0:ys0 + TH, xs0:xs0 + cw]
    cmp_tiles.append(tile(fr, f'现有：单张立绘 sprite   {spr_ms:.0f} ms',
                          'units/sprite.py + hero_front_cut.png（1 张图，姿态/朝向固定）', T[0], T[1]))

    for name, pose, kw, note in [
            ('rig: idle', dict(), {}, '同素材，权重场=0 → 恒等映射'),
            ('rig: 转头 +0.6', dict(head_turn=0.6), {}, '换右侧头部贴片（tq_r）'),
            ('rig: 举刀', dict(key='raise'), {}, 'pose_raise 整姿势键帧'),
            ('rig: 左手抬 arm_r=90', dict(arm_r=90), {}, '纯骨架蒙皮（无键帧）')]:
        ts = []
        for i in range(args.reps):
            fr = bg_plate(TW, TH)
            t = time.perf_counter()
            fr, a = rig.draw(fr, 0.0, pose, dst=(TW // 2, TH - 26), h=hh_c, grade=GRADE, rim=RIM, **kw)
            ts.append((time.perf_counter() - t) * 1000.0)
        med = float(np.median(ts))
        cmp_tiles.append(tile(fr, f'{name}   {med:.0f} ms', note, T[0], T[1]))
        timings[name] = dict(min=round(min(ts), 1), med=round(med, 1), pose=pose)

    rows = math.ceil(len(cmp_tiles) / 3)
    sheet = np.full((rows * T[1] + 64, 3 * T[0], 3), 14, np.uint8)
    for i, t in enumerate(cmp_tiles):
        r, c = divmod(i, 3)
        sheet[64 + r * T[1]:64 + (r + 1) * T[1], c * T[0]:(c + 1) * T[0]] = t
    im = Image.fromarray(sheet)
    d = ImageDraw.Draw(im)
    d.text((16, 16), f'对比：现有单张立绘 sprite（{spr_ms:.0f} ms，姿态固定）vs PoseRig（可转身/抬刀/劈砍）',
           font=FONT, fill=(232, 232, 236))
    d.text((16, 42), '同一张 hero_front_cut.png、同一个高度/落点/调色；PoseRig 只是多了一层骨架 + 角度替换',
           font=FONT_S, fill=(140, 160, 190))
    p2 = os.path.join(OUT, 'rig_vs_sprite.jpg')
    im.save(p2, quality=92)
    print(f'[out] {p2}')

    with open(os.path.join(OUT, 'timings.json'), 'w') as f:
        json.dump(dict(init_s=round(t_init, 2), h=args.h, reps=args.reps,
                       sprite_baseline_ms=round(spr_ms, 1), poses=timings), f,
                  ensure_ascii=False, indent=2)
    print(f'[out] {os.path.join(OUT, "timings.json")}')


if __name__ == '__main__':
    main()
