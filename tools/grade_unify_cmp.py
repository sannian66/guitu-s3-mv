#!/usr/bin/env python3
"""tools/grade_unify_cmp.py — 全片统一 grade 层（units/grade_unify.py）的 A/B 对拍与验证工具。

  # 1) 指定帧号出「左=GRADE_UNIFY=0 / 右=GRADE_UNIFY=1」对比图 + 统计数字 → out/grade_cmp/
  python tools/grade_unify_cmp.py --frames 1250,1500,2700,3600,4900

  # 2) 材质指纹：用 5 张标准测试板量每组收尾层的颗粒/暗角/辉光/黑位/白点/色温/红纯度（不需要渲染画面）
  python tools/grade_unify_cmp.py --probe

  # 3) 从实拍帧重新拟合接点补偿表（写进 units/grade_unify.py 的 JOINT）
  python tools/grade_unify_cmp.py --fit --frames-dir /tmp/gu/base

渲染走冻结快照 out/full_sprite/chunks/full30_50589e0_20261109 里的 prun.py；
只 import 各组的 finish()，不改任何 sec_*.py / *_kit.py。
"""
import argparse, json, os, pathlib, subprocess, sys, time

REPO = pathlib.Path(__file__).resolve().parents[1]
SNAP = pathlib.Path(os.environ.get('GRADE_SNAP',
        str(REPO / 'out/full_sprite/chunks/full30_50589e0_20261109')))
OUT = REPO / 'out/grade_cmp'
W, H, BAR, FPS = 1920, 1080, 120, 30
JOINTS = [1321, 1784, 2586, 3534, 4839, 5797]
SECTIONS = [('a_intro_verse1', 0, 1321), ('b_pre1', 1321, 1784), ('chorus1', 1784, 2586),
            ('b_verse2', 2586, 3534), ('c_pre2_chorus2', 3534, 4839), ('d_bridge', 4839, 5797),
            ('e_final_outro', 5797, 7240)]
DEFAULT_FRAMES = '300,1000,1250,1500,2100,2700,3150,3600,4300,4900,5600,6100'


def key_of(f):
    for k, a, b in SECTIONS:
        if a <= f < b:
            return k
    return 'a_intro_verse1'


# ---------------------------------------------------------------- 渲染管线（含接线钩子）
def boot():
    """返回 (np, prun, st, grade_unify)：把 grade_unify.apply 接到各组 finish 之后、to8 之前。"""
    sys.path.insert(0, str(SNAP))
    sys.path.insert(0, str(REPO / 'units'))
    os.environ.setdefault('SPRITE_FAST', '1')
    import numpy as np
    import prun                                     # 设好 V4_FORCE / 线程数 / code 的 sys.path
    import grade_unify as G
    st = prun.load()                                # sys.path 现在指向 code/units 快照
    import c1kit
    import d_kit

    orig_finish, orig_d = c1kit.finish, d_kit.d_finish

    def finish_gu(fr, t, *a, **kw):
        out = orig_finish(fr, t, *a, **kw)
        return G.apply(out, t, key_of(int(round(t * FPS))), None,
                       hint={'pm': kw.get('paper_mode', 0.0)})

    def d_finish_gu(fr, t, *a, **kw):
        out = orig_d(fr, t, *a, **kw)
        return G.apply(out, t, key_of(int(round(t * FPS))), None,
                       hint={'pm': kw.get('paper_mode', 0.0)})

    c1kit.finish = finish_gu
    d_kit.d_finish = d_finish_gu
    # `from c1kit import finish` 已经绑定旧引用的模块也要换掉
    for name, mod in list(sys.modules.items()):
        if getattr(mod, 'finish', None) is orig_finish:
            setattr(mod, 'finish', finish_gu)
        if getattr(mod, 'd_finish', None) is orig_d:
            setattr(mod, 'd_finish', d_finish_gu)
        Dm = getattr(mod, 'D', None)
        if Dm is not None and getattr(Dm, 'd_finish', None) is orig_d:
            Dm.d_finish = d_finish_gu
    return np, prun, st, G


# ---------------------------------------------------------------- 统计量
def stats_of(np_mod, fr):
    import cv2
    fr = np_mod.asarray(fr)
    if fr.dtype == np_mod.uint8:
        fr = fr.astype(np_mod.float32) / 255.0
    f = np_mod.clip(fr[BAR:H - BAR], 0, 1).astype(np_mod.float32)
    L = 0.3 * f[..., 0] + 0.59 * f[..., 1] + 0.11 * f[..., 2]
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    mx = np_mod.maximum(r, np_mod.maximum(g, b)); mn = np_mod.minimum(r, np_mod.minimum(g, b))
    sat = mx - mn
    m = (sat < 0.10) & (L > 0.04) & (L < 0.55)
    cast = float((r[m] - b[m]).mean()) if m.sum() > 500 else 0.0
    red = (r - np_mod.maximum(g, b)) > 0.06
    pur = (r - np_mod.maximum(g, b)) / (r + 1e-3)
    strong = (r - np_mod.maximum(g, b)) > 0.15
    s = cv2.resize(L, (W // 4, (H - 2 * BAR) // 4), interpolation=cv2.INTER_AREA)
    hp = s - cv2.GaussianBlur(s, (0, 0), 1.4)
    gx = cv2.Sobel(s, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(s, cv2.CV_32F, 0, 1, ksize=3)
    flat = (np_mod.abs(gx) + np_mod.abs(gy)) < np_mod.percentile(np_mod.abs(gx) + np_mod.abs(gy), 45)
    Ls = cv2.resize(L, (W // 8, (H - 2 * BAR) // 8), interpolation=cv2.INTER_AREA)
    hh, ww = Ls.shape
    cen = float(np_mod.median(Ls[hh // 2 - 6:hh // 2 + 6, ww // 2 - 8:ww // 2 + 8]))
    k = 14
    cor = float(np_mod.median(np_mod.concatenate([x.ravel() for x in
              [Ls[:k, :k], Ls[:k, -k:], Ls[-k:, :k], Ls[-k:, -k:]]])))
    return dict(lum_mean=float(L.mean()), lum_std=float(L.std()), p5=float(np_mod.percentile(L, 5)),
                p99=float(np_mod.percentile(L, 99.5)), cast_rb=cast,
                red_area=float(red.mean()), red_pur=float(pur[red].mean()) if red.sum() > 500 else 0.0,
                red_pur_s=float(pur[strong].mean()) if strong.sum() > 3000 else 0.0,
                grain_hp=float(np_mod.std(hp[flat])) if flat.sum() > 100 else 0.0,
                vig_ratio=float(np_mod.clip(cor / max(cen, 0.05), 0, 2)))


# ---------------------------------------------------------------- 材质指纹（标准测试板）
def probe(tag_only=None):
    """用 5 张标准板量每组收尾层。返回 {case: metrics}。"""
    sys.path.insert(0, str(SNAP)); sys.path.insert(0, str(SNAP / 'code'))
    sys.path.insert(0, str(SNAP / 'code/units')); sys.path.insert(0, str(SNAP / 'code/lib'))
    sys.path.insert(0, str(REPO / 'units'))
    os.environ.setdefault('SPRITE_MODE', '1')
    import numpy as np, cv2
    import c1kit as K
    import d_kit as D
    import grade_unify as G

    def flat(v=0.18):
        return np.full((H, W, 3), v, np.float32)

    def patchboard():
        fr = flat()
        def put(cx, cy, col, s=50):
            fr[cy - s:cy + s, cx - s:cx + s] = col
        put(960, 300, 0.50)
        put(960, 780, np.array([0.62, 0.05, 0.04], np.float32))
        put(700, 540, np.array([0.12, 0.010, 0.008], np.float32))
        put(1220, 540, 0.95)
        put(960, 540, 0.005)
        return fr

    def glowboard():
        fr = flat()
        yy, xx = np.mgrid[0:H, 0:W]
        fr[np.sqrt((xx - 480.) ** 2 + (yy - 540.) ** 2) < 60] = 0.95
        return fr

    def fp(bs):
        ff, fb, fw, fwc, fpch, fgl = bs
        Lf = 0.3 * ff[..., 0] + 0.59 * ff[..., 1] + 0.11 * ff[..., 2]
        hp = Lf[300:900, 1400:1850] - cv2.GaussianBlur(Lf[300:900, 1400:1850], (0, 0), 1.2)
        k = 140
        boxes = [Lf[BAR + 30:BAR + 30 + k, 40:40 + k], Lf[BAR + 30:BAR + 30 + k, W - 180:W - 40],
                 Lf[H - BAR - 30 - k:H - BAR - 30, 40:40 + k], Lf[H - BAR - 30 - k:H - BAR - 30, W - 180:W - 40]]
        cor = float(np.median(np.concatenate([b.ravel() for b in boxes])))
        cen = float(np.median(Lf[220:380, 880:1040]))
        g = lambda cx, cy: fpch[cy - 20:cy + 20, cx - 20:cx + 20].mean((0, 1))
        mid, red, dred, wpt = g(960, 300), g(960, 780), g(700, 540), g(1220, 540)
        pur = lambda p: float((p[0] - max(p[1], p[2])) / (p[0] + 1e-3))
        Lg = 0.3 * fgl[..., 0] + 0.59 * fgl[..., 1] + 0.11 * fgl[..., 2]
        yy, xx = np.mgrid[0:H, 0:W]
        dd = np.sqrt((xx - 480.) ** 2 + (yy - 540.) ** 2)
        halo = float(Lg[(dd > 80) & (dd < 220)].mean()) - float(Lg[(dd > 260) & (dd < 400)].mean())
        return dict(grain=float(hp.std()), vig=cor / (cen + 1e-4),
                    black=float(fb[BAR + 40:H - BAR - 40, 200:1700].mean()),
                    white_clean=float(fwc[BAR + 40:H - BAR - 40, 200:1700].mean()),
                    cast_rb=float(mid[0] - mid[2]), red_pur=pur(red), dred_pur=pur(dred),
                    dred_l=float(dred.mean()), wpatch=float(wpt.mean()), halo=halo)

    LIFT = dict(a_intro_verse1=0.012, b_pre1=0.012, chorus1=0.012, b_verse2=0.012,
                c_pre2_chorus2=0.014, d_bridge=0.0, e_final_outro=0.0)
    cases = [('a_intro_verse1', 'a_intro_verse1', 0.0), ('b_pre1', 'b_pre1', 0.0),
             ('chorus1', 'chorus1', 0.0), ('b_verse2', 'b_verse2', 0.0),
             ('c_pre2_chorus2', 'c_pre2_chorus2', 0.0), ('d_bridge pm=0', 'd_bridge', 0.0),
             ('d_bridge pm=.5', 'd_bridge', 0.5), ('d_bridge pm=1', 'd_bridge', 1.0),
             ('e_final_outro', 'e_final_outro', 0.0)]

    def run(key, pm, grade_on):
        lift = LIFT[key]
        bs = [flat(), flat(0.0), flat(0.95), flat(0.95), patchboard(), glowboard()]
        bs = [b + lift * (1 - np.clip(b, 0, 1)) if lift else b for b in bs]
        t = 100.0

        def fin(x, **kw):
            if key == 'd_bridge':
                return D.d_finish(x, t, ca=0, vig=0.45 - 0.3 * pm, grain=0.04, paper_mode=pm, **kw)
            if key == 'c_pre2_chorus2':
                kw.setdefault('bloom_amt', 0.42); return K.finish(x, t, ca=0, vig=0.40, red_keep=1.0, **kw)
            if key == 'e_final_outro':
                kw.setdefault('bloom_amt', 0.25); return K.finish(x, t, ca=0, grain=0.035, vig=0.38, red_keep=1.0, **kw)
            return K.finish(x, t, ca=0, vig=0.45 if key == 'a_intro_verse1' else 0.42, red_keep=1.0, **kw)

        outs = [fin(bs[0]), fin(bs[1]), fin(bs[2]), fin(bs[3], bloom_amt=0.0), fin(bs[4]), fin(bs[5])]
        os.environ['GRADE_UNIFY'] = '1' if grade_on else '0'
        if grade_on:
            outs = [G.apply(o, t, key, {}, hint={'pm': pm}) for o in outs]
        return fp(outs)

    res = {}
    for name, key, pm in cases:
        res[name] = dict(before=run(key, pm, False), after=run(key, pm, True))
    return res


# ---------------------------------------------------------------- 对拍图
def render_compare(frames, np_mod, prun, st, G):
    import cv2
    from PIL import Image
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    state = {}
    for f in frames:
        t0 = time.monotonic()
        os.environ['GRADE_UNIFY'] = '0'
        cache = state.setdefault('cache', {})
        a = prun.render_frame(f, cache, st).copy()
        os.environ['GRADE_UNIFY'] = '1'
        b = prun.render_frame(f, cache, st).copy()
        dt = time.monotonic() - t0
        sa, sb = stats_of(np_mod, a), stats_of(np_mod, b)
        lab = [('FRAME %d  %s  t=%.2fs' % (f, key_of(f), f / FPS), None),
               ('              GRADE_UNIFY=0  |  GRADE_UNIFY=1', None)]
        for k in ('lum_mean', 'lum_std', 'cast_rb', 'red_pur', 'grain_hp', 'vig_ratio'):
            lab.append(('%-9s %7.4f  |  %7.4f' % (k, sa[k], sb[k]), (sa[k], sb[k])))
        gap, top, bot = 12, 28, 18 + 22 * len(lab)
        canvas = np_mod.zeros((H + top + bot, W * 2 + gap, 3), np_mod.uint8)
        canvas[top:top + H, :W] = a
        canvas[top:top + H, W + gap:] = b
        y = top + H + 20
        for i, (txt, _) in enumerate(lab):
            cv2.putText(canvas, txt, (8, y + i * 22), cv2.FONT_HERSHEY_PLAIN, 1.5, (210, 210, 210), 2)
        Image.fromarray(canvas).save(OUT / ('f_%05d.png' % f))
        rows.append(dict(frame=f, key=key_of(f), secs=round(dt, 2), before=sa, after=sb))
        print('CMP %d %s  lum %.4f→%.4f cast %+.4f→%+.4f  %.1fs' %
              (f, key_of(f), sa['lum_mean'], sb['lum_mean'], sa['cast_rb'], sb['cast_rb'], dt), flush=True)
    (OUT / 'stats.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', default=DEFAULT_FRAMES)
    ap.add_argument('--frames-dir', default='')
    ap.add_argument('--probe', action='store_true')
    ap.add_argument('--fit', action='store_true')
    args = ap.parse_args()

    if args.probe:
        res = probe()
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / 'material_probe.json').write_text(json.dumps(res, indent=1))
        cols = ['grain', 'vig', 'black', 'white_clean', 'cast_rb', 'red_pur', 'dred_pur', 'halo', 'wpatch']
        print(f'{"finish":<17}{"":3}' + ''.join(f'{c:>12}' for c in cols))
        for k, v in res.items():
            print(f'{k:<17}前 ' + ''.join(f'{v["before"][c]:12.4f}' for c in cols))
            print(f'{"":<17}后 ' + ''.join(f'{v["after"][c]:12.4f}' for c in cols))
        for c in cols:
            v0 = [v['before'][c] for v in res.values()]; v1 = [v['after'][c] for v in res.values()]
            print(f'  {c:<12} 前Δ {max(v0) - min(v0):8.4f}  后Δ {max(v1) - min(v1):8.4f}')
        return

    np_mod, prun, st, G = boot()

    if args.fit:
        d = pathlib.Path(args.frames_dir)
        cache = {}
        os.environ['GRADE_UNIFY'] = '0'
        sys.path.insert(0, str(REPO / 'units'))
        base = {}
        for p in sorted(d.glob('f_*.npy')):
            f = int(p.stem.split('_')[1])
            base[f] = np_mod.load(p)
        saved = dict(G.JOINT); G.JOINT = {}
        m = {f: stats_of(np_mod, G.apply(v, f / FPS, key_of(f), cache)) for f, v in base.items()}
        G.JOINT = saved
        lines = ['JOINT = {']
        for J in JOINTS:
            L = [v for k, v in m.items() if J - 15 <= k < J]
            R = [v for k, v in m.items() if J <= k < J + 16]
            if not L or not R:
                continue
            md = lambda dd, c: float(np_mod.median([x[c] for x in dd]))
            mL, sL, cL = md(L, 'lum_mean'), md(L, 'lum_std'), md(L, 'cast_rb')
            mR, sR, cR = md(R, 'lum_mean'), md(R, 'lum_std'), md(R, 'cast_rb')
            mT, sT, cT = (mL + mR) / 2, (sL + sR) / 2, (cL + cR) / 2
            def par(mm, ss, cc):
                g = float(np_mod.clip(mT / max(mm, 1e-3), 0.94, 1.06))
                k = float(np_mod.clip(sT / max(ss * g, 1e-4), 0.95, 1.05))
                t = float(np_mod.clip(0.5 * (cT - cc) / max(mm, 0.08), -0.04, 0.04))
                return (round(g, 3), round(k, 3), round(t, 4), 1.0)
            lines.append(f"    {J / 30:.4f}: dict(l=('{key_of(J - 1)}', %s, %s, %s, 1.000)," % par(mL, sL, cL))
            lines.append(f"                    r=('{key_of(J)}', %s, %s, %s, 1.000))," % par(mR, sR, cR))
        lines.append('}')
        print('\n'.join(lines))
        return

    frames = []
    for part in args.frames.split(','):
        if '-' in part:
            a, b = part.split('-'); frames += list(range(int(a), int(b) + 1))
        elif part.strip():
            frames.append(int(part))
    rows = render_compare(frames, np_mod, prun, st, G)
    print('输出:', OUT)


if __name__ == '__main__':
    main()
