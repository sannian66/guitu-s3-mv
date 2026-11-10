"""C 组第六棒生图（C06 箱盖内壁底板 / C41 收刀定格 / C35b 统一脸咬牙扛刀）。报价 → 提交 → 轮询，状态并入 crew/round4/C_gen_state.json，日志 crew/genlog.md。
  python3 crew/round4/C_gen6.py ref <img>        上传马尾版定妆脸（C40b point_cam 脸部裁切）→ 记入状态 ref_url
  python3 crew/round4/C_gen6.py quote|submit [名字,...]|poll
Key 由沙箱代理注入，绝不写文件。"""
import sys, os, json, time
ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv')
sys.path.insert(0, ROOT + '/tools')
import nb
from sprite_plan_rest import GT_LOOK, BG, HANDS
STATE = ROOT + '/crew/round4/C_gen_state.json'
CANDS = '/workspace/work/c_cands6'
LOG = ROOT + '/crew/genlog.md'
BUDGET = 80
REFS = json.load(open(ROOT + '/assets/characters/asset_urls.json'))
FACE = ('SAME person as BOTH reference images (character sheet + ponytail close-up): young slender pale man, soft youthful oval face, '
        'NOT square-jawed, sharp straight brows, amber eyes, black hair tied in a HIGH PONYTAIL, loose messy strands over the forehead parted in the middle. ')
STORM = ('Lighting: harsh cold white lightning flash from behind and above as a hard rim light outlining hair and shoulders, dim cold blue fill from the front, '
         'deep shadows, high contrast, soaking wet hair and skin with rain drops, cinematic photorealistic film still. ')
PLATE = ' Cinematic photorealistic film still, no people, no text, no letters, no watermark, no letterbox bars.'
JOBS = {
 'c06_lid': (None, 'C06', 'Looking straight up from INSIDE an antique Chinese chest at the underside of its open hinged lid: the inner face of the lid fills the upper two thirds of the frame, '
             'a flat panel of bare dark aged wood with visible grain, scratches and old scorch marks, framed by a worn black lacquer border with faded gold leaf trim and two dark bronze hinges at the far edge; '
             'the thick near rim of the chest wall crosses the bottom of the frame as a dark out-of-focus foreground band of black lacquer with a chipped gold edge; '
             'warm golden candlelight glows up from inside the chest onto the lid, the far edge of the lid falls into darkness, floating dust in the light. '
             'The central wooden panel is completely BLANK with no characters or carvings.' + PLATE),
 'c41_sweep': ('hero', 'C41', FACE + GT_LOOK + ' Pose: medium full shot from a low front angle, the instant after a huge horizontal slash: torso twisted hard to camera right, '
               'right arm fully extended to the right with the dao held horizontal at shoulder height, blade edge glowing faintly, left hand open behind him for balance, '
               'robe hem, long red sash and ponytail whipping to the left in the wind, wet strands across the face, eyes fierce looking straight into the camera, mouth closed. '
               'Framing: from mid-thigh up to above the top of the ponytail, whole blade inside the frame with margin. ' + STORM + HANDS + BG),
 'c35b_bear': ('hero', 'C35b', FACE + GT_LOOK + ' Pose: medium close-up from a low angle, he holds the dao horizontally ABOVE his head with both hands (one on the handle, one palm pushing the back of the blade), '
               'elbows bent, shoulders hunched, straining under a crushing weight pressing down on the blade from above, jaw clenched, lips pressed tightly together in a grim strained line (NOT smiling, NOT showing teeth), '
               'brows knitted, cold furious eyes looking up, veins on the neck, rain water on the face. '
               'Framing: from mid-chest to the blade above the head, whole blade and both hands inside the frame with margin at the top. ' + STORM + HANDS + BG),
}


def load(): return json.load(open(STATE))
def save(s): json.dump(s, open(STATE, 'w'), ensure_ascii=False, indent=1)


def body(k, s):
    ch = JOBS[k][0]; b = dict(model='RH_image2', prompt=JOBS[k][2], ratio='16:9', size='4K')
    if ch == 'hero': b['input'] = [REFS['男主_鬼屠.webp'], s['ref_url']]
    return b


def log(name, pts, tid, res, path, note):
    open(LOG, 'a').write('| %s | C组/%s | RH_image2 | 4K 16:9 | %s | %s | %s | %s | [C组] 第六棒 %s |\n' % (time.strftime('%m-%d %H:%M'), name, pts, tid, res, path, note))


def quote(k, s): return json.loads(nb.api('POST', '/api/skills/images/quote', body(k, s))[1]).get('billing', {}).get('total_points')


def submit(names):
    s = load()
    for k in names:
        v = s['jobs'].setdefault(k, {'tries': []})
        if v['tries'] and v['tries'][-1]['status'] == 'running': continue
        q = quote(k, s)
        if q is None: print('quote unavailable; stop'); break
        if s['spent'] + q > BUDGET: print('budget reached', s['spent']); break
        st, raw = nb.api('POST', '/api/skills/generate', body(k, s), timeout=60)
        try: d = json.loads(raw)
        except Exception: d = {}
        tid = d.get('task_id') or d.get('skill_task_id') or (d.get('task') or {}).get('id')
        n = len(v['tries']) + 1
        if not tid:
            log(k, 0, '-', 'submit_failed http_%s' % st, '', 'try%d' % n); print('fail', k, st, raw[:200]); continue
        s['spent'] += q; v['tries'].append(dict(n=n, task_id=tid, status='running', pts=q, file=None))
        log(k, q, tid, 'submitted', '-', '%s try%d (quote %s)' % (JOBS[k][1], n, q)); print('submitted', k, tid, q)
        save(s)
    save(s); print('spent', s['spent'])


def poll():
    s = load()
    for k, v in s['jobs'].items():
        tr = v['tries'][-1]
        if tr['status'] != 'running': continue
        st, raw = nb.api('GET', '/api/skills/tasks/%s' % tr['task_id'])
        try: task = json.loads(raw).get('task') or {}
        except Exception: task = {}
        sta = (task.get('status') or '').lower()
        if sta == 'completed' and task.get('result_urls'):
            f = nb.download(task['result_urls'][:1], CANDS, '%s_try%d' % (k, tr['n']))[0]
            tr['status'] = 'done'; tr['file'] = f; log(k, 0, tr['task_id'], 'completed', f, 'try%d' % tr['n']); print('done', k, f)
        elif sta in nb.FAILED:
            tr['status'] = 'failed'; log(k, 0, tr['task_id'], sta, '-', 'try%d' % tr['n']); print('failed', k, sta)
        else: print(k, sta or 'unknown')
    save(s)


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'ref':
        s = load(); s['ref_url'] = nb.upload(sys.argv[2]); save(s); print('ref ok')
    elif c == 'quote':
        s = load()
        for k in JOBS: print(k, quote(k, s))
    elif c == 'submit': submit(sys.argv[2].split(',') if len(sys.argv) > 2 else [k for k in JOBS if k not in load()['jobs']])
    elif c == 'poll': poll()
