#!/usr/bin/env python3
"""tools/gen_assets.py — 批量生图（RH_image2 4K，绿幕）+ 自动抠图

一份 job 表 → 报价 → 并发提交 → 轮询 → 下载 → `tools/cutout_green.py` 抠图 → 记 genlog。
已存在 `_cut.png` 的 job 自动跳过（幂等，可反复跑补缺）。

用法：
  python3 tools/gen_assets.py jobs/hero_poses.json          # 跑一份 job 表
  python3 tools/gen_assets.py jobs/hero_poses.json --dry    # 只报价，不生图
job 表格式（JSON 数组）：
  [{"name":"hero_side_l", "ref":"男主_鬼屠", "prompt":"...", "ratio":"3:4", "size":"4K", "out":"assets/gen/char"}]
"""
import json, os, pathlib, re, subprocess, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY = pathlib.Path(os.path.expanduser('~/.dsh/secrets/nb_skills.key')).read_text().strip()
BASE = 'https://www.nananobanana.cn'
REFS = json.load(open(ROOT / 'assets/characters/asset_urls.json'))


def ref_url(name):
    """角色名 → 参考图 URL（表里的键带 .webp 后缀，两种写法都接受）。"""
    for k in (name, name + '.webp'):
        if k in REFS:
            return REFS[k]
    raise KeyError(f'asset_urls.json 里没有这个角色: {name}（现有：{list(REFS)}）')
MODEL = os.environ.get('GEN_MODEL', 'RH_image2')
POLL_TOTAL = int(os.environ.get('POLL_TOTAL', '1500'))


def post(path, data):
    req = urllib.request.Request(BASE + path, json.dumps(data).encode(),
                                 {'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=90))


def get(path):
    req = urllib.request.Request(BASE + path, headers={'Authorization': 'Bearer ' + KEY})
    return json.load(urllib.request.urlopen(req, timeout=45))


def find_id(o):
    """生成接口把 id 放在响应顶层（不是 task.id）—— 这个坑踩过一次，别改回去。"""
    if isinstance(o, dict):
        for k in ('id', 'task_id', 'taskId'):
            if isinstance(o.get(k), str) and len(o[k]) > 8:
                return o[k]
        for v in o.values():
            r = find_id(v)
            if r:
                return r
    return None


def quote(job):
    req = {'model': MODEL, 'prompt': job['prompt'], 'ratio': job.get('ratio', '3:4'), 'size': job.get('size', '4K')}
    if job.get('ref'):
        req['input'] = [ref_url(job['ref'])]
    return post('/api/skills/images/quote', req).get('billing', {})


def submit(job):
    req = {'model': MODEL, 'prompt': job['prompt'], 'ratio': job.get('ratio', '3:4'), 'size': job.get('size', '4K')}
    if job.get('ref'):
        req['input'] = [ref_url(job['ref'])]
    return find_id(post('/api/skills/generate', req))


def poll(ids, deadline):
    done = {}
    while time.time() < deadline and len(done) < len(ids):
        for name, tid in ids.items():
            if name in done:
                continue
            try:
                task = get('/api/skills/tasks/' + tid).get('task') or {}
                st = task.get('status')
            except Exception:
                continue
            if st == 'completed':
                done[name] = task
            elif st in ('failed', 'cancelled', 'timeout'):
                done[name] = task
                print(f'  ✗ {name} {st} {task.get("error")}', flush=True)
        print(f'  轮询 t={int(time.time() - start):>4}s 完成 {len(done)}/{len(ids)}', flush=True)
        if len(done) < len(ids):
            time.sleep(10)
    return done


def cut(raw, out, width=2048):
    subprocess.run([sys.executable, str(ROOT / 'tools/cutout_green.py'), str(raw), str(out), str(width)],
                   check=True, stdout=subprocess.DEVNULL)


def main():
    global start
    jobs_file = pathlib.Path(sys.argv[1])
    dry = '--dry' in sys.argv
    jobs = [j for j in json.load(open(jobs_file))
            if not (ROOT / j.get('out', 'assets/gen/char') / f"{j['name']}_cut.png").exists()]
    if not jobs:
        print('全部已存在，无需生成'); return
    print(f'待生成 {len(jobs)} 张（已跳过已存在项）')

    total = 0
    for j in jobs:
        b = quote(j)
        total += b.get('total_points', 0)
        print(f"  报价 {j['name']:<18} {b.get('total_points')} 点 ({b.get('kind')})")
    print(f'合计 **{total} 积分**')
    if dry:
        return

    start = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        ids = dict(zip([j['name'] for j in jobs], ex.map(submit, jobs)))
    print('已提交:', json.dumps(ids, ensure_ascii=False)[:200])

    done = poll(ids, start + POLL_TOTAL)
    log = ['', f'## {time.strftime("%Y-%m-%d %H:%M")} · 批量生图（{jobs_file.name}，{len(jobs)} 张 / {total} 积分）']
    log.append(f'- 渠道 `{MODEL}` 4K，纯绿幕 #00FF00，抠图 `tools/cutout_green.py`')
    for j in jobs:
        task = done.get(j['name']) or {}
        urls = task.get('result_urls') or []
        if not urls:
            log.append(f"- ✗ `{j['name']}` 失败：{task.get('error') or task.get('status')}")
            print('  ✗', j['name']); continue
        outdir = ROOT / j.get('out', 'assets/gen/char')
        outdir.mkdir(parents=True, exist_ok=True)
        raw = outdir / f"{j['name']}_raw.png"
        urllib.request.urlretrieve(urls[0], raw)
        cut(raw, outdir / f"{j['name']}_cut.png")
        tid = ids.get(j['name'], '')
        log.append(f"- ✔ `{j['name']}` 3 点（task {tid[:8]}）→ `{raw.relative_to(ROOT)}` + `_cut.png`")
        print(f"  ✔ {j['name']} → {raw.name}")
    with open(ROOT / 'crew/genlog.md', 'a') as f:
        f.write('\n'.join(log) + '\n')
    print(f'完成 {len([1 for j in jobs if done.get(j["name"], {}).get("result_urls")])}/{len(jobs)}，用时 {int(time.time() - start)}s')


if __name__ == '__main__':
    main()
