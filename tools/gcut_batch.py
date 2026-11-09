#!/usr/bin/env python3
"""tools/gcut_batch.py — 全局「绿幕重抠」：旧灰板抠图发丝不干净 → 图生图换纯绿幕 → 色键重抠 → 对齐旧画布

对 assets/gen 下每个 <名>_cut.png / <名>_cutd.png：
  1. 输入 = <名>_raw.png（灰板原图）；没有 raw 的用旧抠图垫中灰
  2. gpt-image-2 edits：只把背景换成 #00FF00，人物/道具/构图不变 → <名>_graw.png
  3. tools/cutout_green.py 色键 → 半透明发丝
  4. 对齐：在旧抠图画布上搜索缩放 + 平移，使主体（alpha>0.5）IoU 最大
  5. 调色：新图前景按旧抠图前景做 Lab 均值/方差匹配（保持已定稿的色调）
  6. 质检：IoU < 0.85 判失败，不出 gcut（渲染继续用旧图）
  7. 产出 <名>_gcut.png（与旧 _cut.png 同尺寸）；render_sprite_full.py 在 GCUT=1 时自动替换
不覆盖任何已有文件。结果写 out/gcut/report.json，并汇总追加 crew/genlog.md。

用法：python tools/gcut_batch.py [--only 子串,子串] [--jobs 6] [--redo-fail] [--dry]
"""
import json, os, pathlib, sys, time, threading, traceback
from concurrent.futures import ThreadPoolExecutor
import numpy as np, cv2
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import gen_openai as G
from cutout_green import cutout_green

GEN = ROOT / 'assets/gen'
OUT = ROOT / 'out/gcut'
PROMPT = ("Edit this image: replace the entire background with a perfectly flat, uniform pure chroma-key green (#00FF00), "
          "edge to edge. Keep the subject absolutely identical: same face, same pose, same framing, same position and scale "
          "in the frame, same clothing, same props and weapon, same lighting and colours, same painterly cinematic style. "
          "Preserve every individual hair strand and flyaway hair at the silhouette edge, sharp and detailed, with green "
          "visible between strands. Do not add or remove anything. No shadows on the background, no gradient, no floor, no vignette.")
IOU_MIN = 0.85
LOCK = threading.Lock()
REPOST = '--repost' in sys.argv          # 只用已有 _graw.png 重新做抠像/对齐/调色（不重新生图），覆盖本工具产出的 _gcut.png


def items():
    seen = {}
    for c in sorted(GEN.rglob('*_cut*.png')):
        n = c.name
        if n.endswith('_cut.png'): base = c.with_name(n[:-8])
        elif n.endswith('_cutd.png'): base = c.with_name(n[:-9])
        else: continue
        if base.name.endswith('_g') or 'gcut' in n: continue
        cut = base.with_name(base.name + '_cut.png')
        seen.setdefault(str(base), {'base': base, 'cut': cut if cut.exists() else c})
    return list(seen.values())


def is_green(p):
    a = np.asarray(Image.open(p).convert('RGB').resize((256, 256))).astype(np.float32) / 255
    b = np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3), a[:, :6].reshape(-1, 3), a[:, -6:].reshape(-1, 3)])
    return float(np.median(b[:, 1] - np.maximum(b[:, 0], b[:, 2]))) > 0.4


def make_input(it, tmp):
    raw = it['base'].with_name(it['base'].name + '_raw.png')
    if raw.exists(): return raw, True
    im = Image.open(it['cut']).convert('RGBA')                        # 无 raw：旧抠图垫中灰
    bg = Image.new('RGBA', im.size, (128, 128, 128, 255)); bg.alpha_composite(im)
    bg.convert('RGB').save(tmp)
    return tmp, False


def register(new, old_a):
    """new: RGBA float (h,w,4)；old_a: 旧 alpha (H,W)。返回对齐到旧画布的 RGBA 与 IoU。"""
    H, W = old_a.shape
    s0 = 384 / W
    oa = cv2.resize((old_a > 0.5).astype(np.float32), (384, round(H * s0)), interpolation=cv2.INTER_AREA) > 0.5
    na_full = new[..., 3]
    ys, xs = np.nonzero(oa)
    if len(ys) < 50: return None, 0.0
    oc = np.array([xs.mean(), ys.mean()]); oh = ys.max() - ys.min() + 1
    nm = (na_full > 0.5)
    nys, nxs = np.nonzero(nm)
    if len(nys) < 50: return None, 0.0
    # 初值：主体高度比
    base = oh / s0 / (nys.max() - nys.min() + 1)
    best = (-1, None)
    hs, ws = oa.shape
    for s in base * np.linspace(0.90, 1.10, 21):
        k = s * s0                                                     # new → 低分辨率旧画布
        M = np.array([[k, 0, 0], [0, k, 0]], np.float32)
        ncx, ncy = nxs.mean() * k, nys.mean() * k
        M[0, 2], M[1, 2] = oc[0] - ncx, oc[1] - ncy
        for dx in range(-6, 7, 2):
            for dy in range(-6, 7, 2):
                M2 = M.copy(); M2[0, 2] += dx; M2[1, 2] += dy
                w = cv2.warpAffine(nm.astype(np.float32), M2, (ws, hs), flags=cv2.INTER_AREA) > 0.5
                iou = (w & oa).sum() / max(1, (w | oa).sum())
                if iou > best[0]: best = (iou, (s, M2[0, 2] / s0, M2[1, 2] / s0))
    iou, (s, tx, ty) = best
    M = np.array([[s, 0, tx], [0, s, ty]], np.float32)
    out = cv2.warpAffine(new, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return np.clip(out, 0, 1), float(iou)


def color_match(new, old):
    """Lab 三通道直方图（CDF）匹配：统计取两边都实心的主体区，映射作用于整张新图。
    比均值/方差匹配更能压住模型「还原」出来的局部饱和色（如 _pt 去色版被画回大红）。"""
    m = (new[..., 3] > 0.95) & (old[..., 3] > 0.95)
    if m.sum() < 500: return new
    to_lab = lambda x: cv2.cvtColor(np.ascontiguousarray(x[..., :3]).astype(np.float32), cv2.COLOR_RGB2LAB)
    nl, ol = to_lab(new), to_lab(old)
    q = np.linspace(0, 100, 257)
    out = np.empty_like(nl)
    for c in range(3):
        src, ref = np.percentile(nl[..., c][m], q), np.percentile(ol[..., c][m], q)
        src = np.maximum.accumulate(src + np.arange(257) * 1e-6)
        out[..., c] = np.interp(nl[..., c], src, ref)
    rgb = np.clip(cv2.cvtColor(out.astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)
    return np.dstack([rgb, new[..., 3]])


def fuse(new, old):
    """2026-11-10 用户：「主角人都变了」——图生图重画会改脸。所以新图只用在轮廓边缘：
    旧抠图实心区（alpha>0.97，内缩 r px）一律保留旧像素（脸、衣服、刀完全不变），
    边缘一圈与轮廓外的发丝才用绿幕新图，过渡带羽化。"""
    H, W = old.shape[:2]
    r = max(4, round(W * 0.004))
    core = (old[..., 3] > 0.97).astype(np.uint8)
    core = cv2.erode(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    w = cv2.GaussianBlur(core.astype(np.float32), (0, 0), r * 0.6)
    w = (np.clip(w * 2 - 1, 0, 1) * core)[..., None]          # 核心内向边缘羽化到 0，核心外全用新图
    return np.clip(old * w + new * (1 - w), 0, 1)


def one(it, redo_fail=False):
    base = it['base']; name = str(base.relative_to(GEN))
    gcut = base.with_name(base.name + '_gcut.png')
    graw = base.with_name(base.name + '_graw.png')
    rec = {'name': name, 'cut': str(it['cut'].relative_to(GEN))}
    if gcut.exists() and not (REPOST and graw.exists()): return {**rec, 'status': 'exists'}
    fail = OUT / 'fail' / (name.replace('/', '__') + '.json')
    if fail.exists() and not redo_fail: return {**rec, 'status': 'skip_fail'}
    t = time.time()
    try:
        src, has_raw = make_input(it, OUT / 'tmp' / (name.replace('/', '__') + '_in.png'))
        rec['has_raw'] = has_raw
        if has_raw and is_green(src):
            return {**rec, 'status': 'already_green'}
        if not graw.exists():
            for k in range(3):
                try:
                    resp = G.edit(PROMPT, [src], 'gpt-image-2')
                    tmp = OUT / 'tmp' / (name.replace('/', '__') + '_graw.png')
                    if G.save(resp, tmp): tmp.replace(graw); break
                except Exception as e:
                    rec['err'] = str(e)[:160]; time.sleep(5 + 10 * k)
            if not graw.exists(): raise RuntimeError('生图失败 ' + rec.get('err', ''))
        old = np.asarray(Image.open(it['cut']).convert('RGBA')).astype(np.float32) / 255
        ctmp = OUT / 'tmp' / (name.replace('/', '__') + '_c.png')
        cutout_green(str(graw), str(ctmp), max(2048, old.shape[1]))
        new = np.asarray(Image.open(ctmp).convert('RGBA')).astype(np.float32) / 255
        reg, iou = register(new, old[..., 3])
        rec['iou'] = round(iou, 3)
        if reg is None or iou < IOU_MIN:
            fail.write_text(json.dumps(rec, ensure_ascii=False))
            return {**rec, 'status': 'fail_iou', 'sec': round(time.time() - t)}
        reg = fuse(color_match(reg, old), old)
        Image.fromarray((reg * 255 + 0.5).astype(np.uint8), 'RGBA').save(gcut)
        return {**rec, 'status': 'ok', 'sec': round(time.time() - t)}
    except Exception as e:
        rec['err'] = (str(e) or repr(e))[:200]
        fail.write_text(json.dumps(rec, ensure_ascii=False))
        traceback.print_exc()
        return {**rec, 'status': 'error'}


def main():
    a = sys.argv[1:]
    only = a[a.index('--only') + 1].split(',') if '--only' in a else None
    nj = int(a[a.index('--jobs') + 1]) if '--jobs' in a else 6
    for d in ('tmp', 'fail'): (OUT / d).mkdir(parents=True, exist_ok=True)
    its = items()
    if only: its = [i for i in its if any(o in str(i['base']) for o in only)]
    print(f'共 {len(its)} 个抠图', flush=True)
    if '--dry' in a:
        for i in its: print(' ', i['base'].relative_to(GEN), '←', i['cut'].name)
        return
    rep_p = OUT / 'report.json'
    rep = json.loads(rep_p.read_text()) if rep_p.exists() else {}
    done = [0]

    def run(it):
        r = one(it, '--redo-fail' in a)
        with LOCK:
            done[0] += 1
            rep[r['name']] = r
            rep_p.write_text(json.dumps(rep, ensure_ascii=False, indent=1))
            print(f"[{done[0]}/{len(its)}] {r['status']:<12} {r['name']}  iou={r.get('iou', '-')} {r.get('err', '')}", flush=True)
        return r

    with ThreadPoolExecutor(nj) as ex:
        res = list(ex.map(run, its))
    ok = [r for r in res if r['status'] == 'ok']
    bad = [r for r in res if r['status'] in ('fail_iou', 'error')]
    log = ['', f'## {time.strftime("%Y-%m-%d %H:%M")} · 第五轮全局绿幕重抠（tools/gcut_batch.py，gpt-image-2 edits，本批 {len(res)} 个）',
           f'- 成功 {len(ok)}，失败 {len(bad)}（IoU<{IOU_MIN} 或生图失败 → 继续用旧图）；产物 `<名>_graw.png`（绿幕原图）、`<名>_gcut.png`（对齐旧画布的新抠图）']
    log += [f"- ✗ `{r['name']}` {r['status']} iou={r.get('iou', '-')} {r.get('err', '')[:80]}" for r in bad]
    with open(ROOT / 'crew/genlog.md', 'a') as f: f.write('\n'.join(log) + '\n')
    print('done ok', len(ok), 'bad', len(bad))


if __name__ == '__main__':
    main()
