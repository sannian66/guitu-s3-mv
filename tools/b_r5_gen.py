"""[B组 r5] 第五轮生图（上限 45 积分）。
  python3 tools/b_r5_gen.py quote <名字>
  python3 tools/b_r5_gen.py submit <名字..>
  python3 tools/b_r5_gen.py poll
  python3 tools/b_r5_gen.py ok <名字>        → assets/gen/R5_B/<名字>_raw.png
  python3 tools/b_r5_gen.py bad <名字> 原因
状态：crew/round5/B_r5_gen_state.json；日志 crew/genlog.md。Key 在 .env.local（不入库）。"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))
import nb, sprite_plan_rest as plan
ROOT = plan.ROOT
STATE = os.path.join(ROOT, 'crew/round5/B_r5_gen_state.json')
CANDS = '/workspace/work/b5_cands'
OUT = os.path.join(ROOT, 'assets/gen/R5_B')
LOG = os.path.join(ROOT, 'crew/genlog.md')
BUDGET = 45
REFS = json.load(open(os.path.join(ROOT, 'assets/characters/asset_urls.json')))
GT, TSH = plan.GT, plan.TSH
BG = plan.BG
WARM = plan.LIGHT_WARM
COLD = plan.LIGHT_COLD

JOBS = {
 # #13：俯拍生死簿上的执笔手，视角必须与纸面（俯拍 ~65°）一致
 'tsh_brush_top': (TSH, 'HIGH-ANGLE overhead camera looking DOWN at a flat writing desk surface from above at about 65 degrees, as if the camera hangs above the desk: '
                   'ONLY the right hand and wide sleeve cuff of the gaunt pale old emperor (no face, no head, no body), entering the frame from the TOP-RIGHT corner; '
                   'we see the BACK of the bony hand and knuckles from above, long fingernails, holding a thin dark wooden Chinese calligraphy brush in the classic upright five-finger grip, '
                   'the brush shaft tilted slightly toward the lower-left and strongly foreshortened by the overhead view, '
                   'the soft brush tip soaked in bright vermilion red ink PRESSED DOWN onto the flat surface at the lower-left of the hand, the tip bending slightly where it touches, '
                   'the hand and brush cast a soft shadow down onto the flat surface toward the lower left; the wide dark charcoal embroidered silk sleeve drapes over the surface toward the top-right edge of the frame. '
                   'The flat surface under the hand is plain matte neutral mid-grey (RGB about 128,128,128), seamless, nothing on it, no paper, no writing, no props. ',
                   WARM),
}


def prompt(name):
    char, pose, light = JOBS[name]
    look = '' if char is None else (plan.TSH_LOOK if char == TSH else plan.GT_LOOK) + ' '
    return pose + plan.HANDS + look + 'No text, no watermark, no letterbox bars. ' + light


def body(name):
    char = JOBS[name][0]
    b = dict(model='RH_image2', prompt=prompt(name), ratio='16:9', size='4K')
    if char: b['input'] = [REFS[char + '.webp']]
    return b


def load():
    return json.load(open(STATE)) if os.path.exists(STATE) else {'spent': 0, 'jobs': {}}


def save(s):
    json.dump(s, open(STATE, 'w'), ensure_ascii=False, indent=1)


def log(name, pts, tid, res, path, note):
    open(LOG, 'a').write('| %s | B组r5/%s | RH_image2 | 4K 16:9 | %s | %s | %s | %s | %s |\n' % (
        time.strftime('%m-%d %H:%M'), name, pts, tid, res, path, note))


def quote(name):
    st, raw = nb.api('POST', '/api/skills/images/quote', body(name))
    return json.loads(raw).get('billing', {}).get('total_points'), st, raw[:300]


def submit(names):
    s = load()
    for n in names:
        j = s['jobs'].setdefault(n, {'tries': [], 'state': 'todo'})
        if j['state'] in ('running', 'done'): continue
        q, st, raw = quote(n)
        if q is None: print(n, 'quote failed', st, raw); continue
        if s['spent'] + q > BUDGET: print('budget stop', s['spent'], q); break
        stt, raw = nb.api('POST', '/api/skills/generate', body(n), timeout=60)
        d = json.loads(raw)
        tid = d.get('task_id') or d.get('skill_task_id') or (d.get('task') or {}).get('id')
        if not tid: print(n, 'submit failed', stt, raw[:300]); log(n, 0, '-', 'submit_failed', '-', raw[:80]); continue
        s['spent'] += q; j['tries'].append({'tid': tid, 'pts': q}); j['state'] = 'running'
        log(n, q, tid, 'submitted', '-', '[B组 r5] try%d' % len(j['tries']))
        print(n, 'submitted', tid, q)
    save(s); print('spent', s['spent'])


def poll():
    s = load()
    for n, j in s['jobs'].items():
        if j['state'] != 'running': continue
        tid = j['tries'][-1]['tid']
        st, raw = nb.api('GET', '/api/skills/tasks/%s' % tid, timeout=30)
        t = (json.loads(raw) or {}).get('task') or {}
        stt = (t.get('status') or '').lower()
        if stt == 'completed' and t.get('result_urls'):
            p = nb.download(t['result_urls'][:1], CANDS, '%s_try%d' % (n, len(j['tries'])))[0]
            j['state'] = 'review'; j['tries'][-1]['file'] = p
            log(n, 0, tid, 'completed', p, 'try%d' % len(j['tries']))
            print(n, 'done', p)
        elif stt in nb.FAILED:
            j['state'] = 'todo'; log(n, 0, tid, stt, '-', 'failed'); print(n, stt)
        else:
            print(n, stt or st)
    save(s)


def verdict(n, ok, why=''):
    s = load(); j = s['jobs'][n]
    if ok:
        os.makedirs(OUT, exist_ok=True)
        dst = os.path.join(OUT, n + '_raw.png')
        from PIL import Image
        Image.open(j['tries'][-1]['file']).convert('RGB').save(dst)
        j['state'] = 'done'; log(n, 0, j['tries'][-1]['tid'], '采用', 'assets/gen/R5_B/%s_raw.png' % n, 'try%d 采用' % len(j['tries']))
    else:
        j['state'] = 'todo'; log(n, 0, j['tries'][-1]['tid'], '判废', '-', why)
    save(s)


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'quote': print(quote(sys.argv[2]))
    elif c == 'submit': submit(sys.argv[2:])
    elif c == 'poll': poll()
    elif c == 'ok': verdict(sys.argv[2], True)
    elif c == 'bad': verdict(sys.argv[2], False, ' '.join(sys.argv[3:]))
    elif c == 'prompt': print(prompt(sys.argv[2]))
