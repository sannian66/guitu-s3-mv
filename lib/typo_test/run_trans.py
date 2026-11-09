"""trans 联系表：A=深色水墨山月（含字），B=宣纸+朱红巨字。python run_trans.py [名字...]"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_typo import bg_dark, bg_paper, sheet, OUT, W, H
import numpy as np
import typo as T, trans as R

A = T.vertical_column(bg_dark(), '长夜压在 我刀锋之上', 1.0, size=120, anchor=(0.2, 0.0))
B = T.giant_char(bg_paper(), '刀', 1.0, mode='solid', color='red', fname='xing')
TIMES = {}
def run(name, kw=None, ps=(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 0.97, 1.0), label=None):
    kw = kw or {}; frs = []; ts = []
    R.transition(name, A, B, 0.5, **kw)
    for p in ps:
        a = time.time(); frs.append(R.transition(name, A, B, p, **kw)); ts.append(time.time() - a)
    lab = label or name
    TIMES[lab] = (np.mean(ts), np.max(ts))
    print(lab, 'avg %.3f max %.3f' % TIMES[lab], sheet('tr_' + lab, frs, [f'{lab} p={p:.2f}' for p in ps]), flush=True)

TESTS = {
 'hard_cut_on_beat': lambda: run('hard_cut_on_beat', dict(frames=6), ps=(0.3, 0.49, 0.5, 0.6, 0.7, 0.9)),
 'match_cut': lambda: run('match_cut', dict(shape='circle', center=(1450, 330), radius=120)),
 'match_line': lambda: run('match_cut(山脊地平线 → 刀身直线)', dict(center=(960, 700), angle=-8), label='match_line'),
 'slash_wipe': lambda: run('slash_wipe'),
 'slash_v': lambda: run('slash_wipe(竖)', label='slash_v'),
 'spin_slash': lambda: run('slash_wipe(圆形刀光)', label='spin_slash'),
 'ink_bleed': lambda: run('ink_bleed'),
 'whip_pan_blur': lambda: run('whip_pan_blur'),
 'whip_rot': lambda: run('whip_pan_blur(旋转)', label='whip_rot'),
 'flash_white': lambda: run('flash_white'),
 'flash_red': lambda: run('flash_red'),
 'paper_tear': lambda: run('paper_tear'),
 'shatter': lambda: run('shatter', ps=(0.05, 0.12, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 1.0)),
 'occlusion': lambda: run('occlusion(前景松枝扫过)', label='occlusion'),
 'occ_crowd': lambda: run('occlusion(人群背影遮挡入)', label='occ_crowd'),
 'iris_moon': lambda: run('iris_moon', dict(center=(1450, 330), radius=120)),
 'iris_close': lambda: run('iris_moon', dict(mode='close'), label='iris_close'),
 'iris_sun': lambda: run('iris_moon(日轮)', label='iris_sun'),
 'iris_collapse': lambda: run('iris_moon(收墨成一点朱红)', label='iris_collapse'),
 'smoke_through': lambda: run('smoke_through'),
 'zoom_through': lambda: run('zoom_through'),
 'zoom_rain': lambda: run('zoom_through(穿过雨滴)', label='zoom_rain'),
 'zoom_paper': lambda: run('zoom_through(穿过纸片)', label='zoom_paper'),
 'zoom_glint': lambda: run('zoom_through(穿过刀身反光)', label='zoom_glint'),
 'glitch_cut': lambda: run('glitch_cut'),
 'fade_black': lambda: run('fade_black'),
 'split_slide': lambda: run('split_slide'),
 'split_diag': lambda: run('split_slide', dict(angle=35), label='split_diag'),
 'freeze_glitch': lambda: run('freeze_glitch', ps=(0.05, 0.2, 0.35, 0.5, 0.6, 0.7, 0.75, 0.79, 0.85)),
}

def cam_test():
    big = __import__('cv2').resize(A, (int(W * 1.3), int(H * 1.3)))
    specs = [dict(t0=0, t1=2, zoom=(1.0, 1.25), pan=(0, 0, 200, -60), ease='io', shake=8, punch=[0.5, 1.0, 1.5]),
             dict(t0=0, t1=2, whip=(1.0, 0.3, 900, 0), ease='bullet', rot=(-3, 3))]
    frs = []; labs = []; ts = []
    for k, sp in enumerate(specs):
        for t in (0.0, 0.52, 0.9, 1.05, 1.15, 1.9):
            a = time.time(); frs.append(R.camera(big, t, sp)); ts.append(time.time() - a); labs.append(f'cam{k} t={t}')
    TIMES['camera'] = (np.mean(ts), np.max(ts))
    print('camera', TIMES['camera'], sheet('tr_camera', frs, labs))

if __name__ == '__main__':
    names = sys.argv[1:] or list(TESTS) + ['camera']
    for n in names:
        if n == 'camera': cam_test()
        else: TESTS[n]()
    with open(os.path.join(OUT, 'timing_trans.txt'), 'a') as fh:
        for k, (a, m) in TIMES.items(): fh.write(f'{k}\tavg {a:.3f}s\tmax {m:.3f}s\n')
