#!/usr/bin/env python3
"""每个段落每镜一帧 → 分段联系表（给用户逐镜决策用）。"""
import sys, os, json, pathlib
sys.path[:0] = ['code/units', 'code/lib', 'code']
os.environ['SPRITE_MODE'] = '1'
TILE = pathlib.Path('/tmp/shots'); TILE.mkdir(exist_ok=True)

SECS = [('A 组 · 前奏+主歌一', 'sec_a_intro_verse1'),
        ('B 组 · 导歌一', 'sec_b_pre1'),
        ('副歌一（标杆）', 'chorus1'),
        ('B 组 · 主歌二', 'sec_b_verse2'),
        ('C 组 · 导歌二+副歌二', 'sec_c_pre2_chorus2'),
        ('D 组 · 桥段', 'sec_d_bridge'),
        ('E 组 · 终章+尾奏', 'sec_e_final_outro')]


def shot_list(mod):
    if mod == 'chorus1':
        import chorus1 as M
        X = M.Chorus1()
        return [(i, int(round(s.t0 * 30)), int(round(s.t1 * 30))) for i, s in zip(X.ids, X.shots)]
    if mod == 'sec_e_final_outro':
        import sec_e_final_outro as M
        return [(M.IDS[i], M.BOUNDS[i], M.BOUNDS[i + 1]) for i in range(len(M.IDS))]
    M = __import__(mod)
    return [(s.__name__, int(round(s.t0 * 30)), int(round(s.t1 * 30))) for s in M.SHOTS]


def render(args):
    idx, f, out = args
    import prun
    from PIL import Image
    st = prun.load()
    fr = prun.render_frame(f, {}, st)
    Image.fromarray(fr).resize((480, 270), Image.LANCZOS).save(out)
    return out


def main():
    jobs, meta = [], {}
    for name, mod in SECS:
        shots = shot_list(mod)
        rows = []
        for i, (sid, f0, f1) in enumerate(shots):
            f = int(f0 + 0.55 * (f1 - f0))
            out = TILE / f'{mod}_{i:03d}.png'
            jobs.append((i, f, out))
            rows.append((sid, f0, f1, f, out))
        meta[name] = rows
        print(name, len(rows), '镜', flush=True)
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=4) as ex:
        list(ex.map(render, jobs))
    json.dump({k: [[a, b, c, d, str(e)] for a, b, c, d, e in v] for k, v in meta.items()},
              open('/tmp/shot_meta.json', 'w'), ensure_ascii=False)
    print('RENDER_OK', len(jobs))


if __name__ == '__main__':
    main()
