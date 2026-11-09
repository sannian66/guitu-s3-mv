"""副歌一以外段落精灵生图（提交/轮询分离，适配无后台的沙箱）。计划见 tools/sprite_plan_rest.py。
  python3 tools/gen_rest_sprites.py submit [并发上限=6]   提交下一批（先报价；预算上限 BUDGET）
  python3 tools/gen_rest_sprites.py poll                  轮询一次所有进行中任务，完成的下载到 work 候选目录
  python3 tools/gen_rest_sprites.py ok   S010 walk        采用最新一抽 → assets/gen/S010/walk_raw.png
  python3 tools/gen_rest_sprites.py bad  S010 walk 原因   判废（下次 submit 会重抽，最多 3 抽）
  python3 tools/gen_rest_sprites.py status
状态：crew/rest_gen_state.json；日志：crew/genlog.md（含失败）。候选图不进仓库（work/rest_cands/）。
"""
import sys, os, json, time, shutil, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__))
import nb, sprite_plan_rest as plan
ROOT = plan.ROOT
STATE = os.path.join(ROOT, 'crew/rest_gen_state.json')
CANDS = os.path.join(os.path.dirname(ROOT), 'rest_cands')
LOG = os.path.join(ROOT, 'crew/genlog.md')
BUDGET = 150   # 第二轮上限；第三轮（+60，用户 11-09 05:59 同意）见 tools/gen_round3.py（覆盖为 60，独立状态）
MAXTRY = 3
REFS = json.load(open(os.path.join(ROOT, 'assets/characters/asset_urls.json')))


def load():
    return json.load(open(STATE)) if os.path.exists(STATE) else {'spent': 0, 'jobs': {}}


def save(s):
    json.dump(s, open(STATE, 'w'), ensure_ascii=False, indent=1)


def log(sid, pts, tid, res, path, note):
    open(LOG, 'a').write('| %s | %s | RH_image2 | 4K 16:9 | %s | %s | %s | %s | %s |\n' % (
        time.strftime('%m-%d %H:%M'), sid, pts, tid, res, path, note))


def body(j):
    return dict(model='RH_image2', prompt=j['prompt'], ratio='16:9', size='4K', input=[REFS[j['char'] + '.webp']])


def submit(maxc=6):
    s = load(); jobs = plan.jobs()
    running = sum(1 for k, v in s['jobs'].items() if v['tries'] and v['tries'][-1]['status'] == 'running')
    for j in jobs:
        if running >= maxc: break
        k = j['sid'] + ':' + j['pose']
        v = s['jobs'].setdefault(k, {'tries': [], 'accepted': None})
        if v['accepted'] or len(v['tries']) >= MAXTRY: continue
        if v['tries'] and v['tries'][-1]['status'] in ('running', 'done'): continue   # 进行中或待判定
        b = body(j)
        q = json.loads(nb.api('POST', '/api/skills/images/quote', b)[1]).get('billing', {}).get('total_points')
        if q is None: print('quote unavailable, stop'); break
        if s['spent'] + q > BUDGET: print('budget reached', s['spent']); break
        st, raw = nb.api('POST', '/api/skills/generate', b, timeout=60)
        try: d = json.loads(raw)
        except Exception: d = {}
        tid = d.get('task_id') or d.get('skill_task_id') or (d.get('task') or {}).get('id')
        n = len(v['tries']) + 1
        if not tid:
            log(j['sid'], 0, '-', 'submit_failed http_%s' % st, '', '%s try%d' % (j['pose'], n)); print('submit fail', k, st, raw[:200]); continue
        s['spent'] += q
        v['tries'].append({'n': n, 'task_id': tid, 'status': 'running', 'pts': q, 'file': None, 'verdict': None})
        running += 1; print('submitted', k, 'try', n, tid)
        save(s)
    save(s); print('spent', s['spent'], 'running', running)


def _check(tid):
    st, raw = nb.api('GET', '/api/skills/tasks/%s' % tid, timeout=30)
    try: return st, json.loads(raw).get('task') or {}
    except Exception: return st, {}


def poll():
    s = load(); jobs = {j['sid'] + ':' + j['pose']: j for j in plan.jobs()}
    pend = [(k, t) for k, v in s['jobs'].items() for t in v['tries'] if t['status'] == 'running']
    with cf.ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda kt: (kt, _check(kt[1]['task_id'])), pend))
    for (k, t), (st, task) in res:
        sid, pose = k.split(':'); stt = (task.get('status') or '').lower()
        if stt == 'completed' and task.get('result_urls'):
            p = nb.download(task['result_urls'][:1], os.path.join(CANDS, sid), '%s_try%d' % (pose, t['n']))[0]
            t['status'] = 'done'; t['file'] = p
            log(sid, t['pts'], t['task_id'], 'completed', os.path.relpath(p, os.path.dirname(ROOT)), '%s try%d：%s' % (pose, t['n'], jobs[k]['prompt'][:50]))
            print('done', k, p)
        elif stt in nb.FAILED or (st // 100 != 2 and st != 0):
            t['status'] = 'failed'; t['verdict'] = 'api:' + (stt or 'http_%d' % st)
            log(sid, t['pts'], t['task_id'], 'failed ' + str(task.get('error'))[:80], '', '%s try%d' % (pose, t['n']))
            print('FAILED', k, stt, task.get('error'))
        else:
            print('..', k, stt or 'unknown')
    save(s)


def verdict(sid, pose, ok, reason=''):
    s = load(); v = s['jobs'][sid + ':' + pose]; t = v['tries'][-1]
    if ok:
        d = os.path.join(ROOT, 'assets/gen', sid); os.makedirs(d, exist_ok=True)
        from PIL import Image
        Image.open(t['file']).convert('RGB').save(os.path.join(d, pose + '_raw.png'))
        t['verdict'] = 'ok'; v['accepted'] = t['n']
        log(sid, 0, t['task_id'], '采用', 'assets/gen/%s/%s_raw.png' % (sid, pose), '%s try%d 采用' % (pose, t['n']))
    else:
        t['status'] = 'rejected'; t['verdict'] = reason
        log(sid, 0, t['task_id'], '重抽', '', '%s try%d 判废：%s' % (pose, t['n'], reason))
    save(s)


def status():
    s = load(); print('spent', s['spent'])
    for k, v in s['jobs'].items():
        print(k, 'accepted=%s' % v['accepted'], [(t['n'], t['status'], t['verdict']) for t in v['tries']])


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'submit': submit(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    elif c == 'poll': poll()
    elif c == 'ok': verdict(sys.argv[2], sys.argv[3], True)
    elif c == 'bad': verdict(sys.argv[2], sys.argv[3], False, ' '.join(sys.argv[4:]))
    elif c == 'status': status()
