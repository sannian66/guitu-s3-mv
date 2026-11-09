"""[D组] Bridge 精灵生图（第四轮，预算 ≤80 积分）。提交/轮询分离。
  python3 tools/d_gen.py quote            报价全部待提交
  python3 tools/d_gen.py submit [名字..]   报价 → 提交（记 crew/genlog.md）
  python3 tools/d_gen.py poll             轮询一次，完成的下载到 ../d_cands/
  python3 tools/d_gen.py ok <名字>         采用最新一抽 → assets/gen/D_bridge/<名字>_raw.png
  python3 tools/d_gen.py bad <名字> 原因   判废（下次 submit 重抽）
状态：crew/round4/D_gen_state.json。Key 由代理注入，绝不写文件。"""
import sys, os, json, time, shutil
sys.path.insert(0, os.path.dirname(__file__))
import nb, sprite_plan_rest as plan
ROOT = plan.ROOT
STATE = os.path.join(ROOT, 'crew/round4/D_gen_state.json')
CANDS = os.path.join(os.path.dirname(ROOT), 'd_cands')
OUT = os.path.join(ROOT, 'assets/gen/D_bridge')
LOG = os.path.join(ROOT, 'crew/genlog.md')
BUDGET = 80
REFS = json.load(open(os.path.join(ROOT, 'assets/characters/asset_urls.json')))
GT, TSH = plan.GT, plan.TSH
BG = plan.BG
COLD = plan.LIGHT_COLD
SOFT = 'Lighting: soft even overcast light from above-left, gentle shadows, readable folds and details in the black clothes, cinematic photorealistic film still. '

JOBS = {
 'walk_back': (GT, 'LS', 'seen squarely from behind, walking away from the camera with slow heavy steps, the long dao held low in his right hand with its tip almost touching the ground, head slightly bowed, ponytail and robe hem drifting', SOFT),
 'tsh_brush': (TSH, 'MS', 'standing in three-quarter view, holding a HUGE Chinese calligraphy brush (long dark wooden shaft, thick black wet bristles dripping ink) with both hands like a spear, writing downward with its tip, looking down with cold arrogant contempt, very wide sleeves hanging', SOFT),
 'kneel_bow': (GT, 'LS', 'kneeling on one knee, head bowed low so his face is hidden by loose hair, both hands resting on the hilt of the dao whose point is planted in the ground in front of him, shoulders heavy with grief, ponytail falling forward', SOFT),
 'eyes_closed': (GT, 'CU', 'close-up of his face in three-quarter view turned to the left, head slightly bowed, eyes CLOSED, calm grief, loose black hair strands across his forehead and cheek, the top of the high ponytail visible, shoulders at the bottom edge', SOFT),
 'slash_sky_back': (GT, 'LS', 'seen from BEHIND and slightly from below, his back to the camera, leaping upward mid-air in a huge diagonal upward sword slash toward the sky, right arm swinging the dao from lower left to upper right above his head, the blade a clean sharp straight line, robe hem and ponytail flying, crisp sharp image with no motion blur', COLD),
 'spin_front': (GT, 'MS', 'facing the camera in a low wide stance in the middle of a fast spinning sword sweep, body twisted, the dao held in his right hand extended far out horizontally at waist height, the blade a clean sharp straight line, robe hem flaring outward in a circle, ponytail swinging, fierce stare at the camera, crisp sharp image with no motion blur', COLD),
 'thrust_sky_back': (GT, 'LS', 'seen from BEHIND, his back to the camera, standing with feet apart, right arm raised straight up thrusting the dao vertically into the sky above his head, blade pointing straight up and fully visible, left fist clenched at his side, ponytail and robe hem blown sideways by a strong wind', COLD),
 'blade_up_cu': (GT, 'CU', 'extreme close-up from a low angle: only his right hand and forearm in a black leather bracer at the bottom of the frame gripping the dao hilt, the long single-edged blade pointing STRAIGHT UP and filling the frame vertically up to the top edge, the sharp edge and the blade tip fully visible, a thin red cord tassel on the pommel, no face visible', COLD),
 'wall_stand_back': (GT, 'LS', 'seen squarely from behind, standing perfectly still with feet apart, head tilted up looking at something enormous above him, the dao hanging low in his right hand with the blade angled outward, left hand clenched into a fist, robe hem and ponytail blown to the right by a strong wind', COLD),
 'defy_up': (GT, 'MCU', 'medium close-up from a LOW angle, three-quarter view facing right, chest up, his right arm raised high holding the dao above his head with the blade pointing up and back toward the stormy sky, chin lifted, eyes open looking UP at the sky with fierce cold defiance, jaw clenched, loose black hair strands across the forehead, the high ponytail swinging behind, the full head and the hand on the hilt inside the frame', COLD),
 'draw_side': (GT, 'MS', 'in strict side profile facing LEFT, body turned sideways, slowly half-drawing the long dao out of the black scabbard at his left hip with his right hand, about half of the bright blade visible between hilt and scabbard mouth, head turned a little toward the camera, cold determined eyes, ponytail and loose hair strands blown by wind, rain-wet clothes', COLD),
 'run_top': (GT, 'LS', 'seen from a very HIGH bird-eye angle almost directly above, sprinting forward toward the bottom of the frame with a long stride, upper body leaning forward, the dao held low behind him in his right hand trailing backward, ponytail and robe hem streaming behind, his whole body and his shadow on the ground inside the frame', COLD),
 'sword_planted': (GT, 'CU', 'ONLY THE SWORD, NO PERSON in the image: his long single-edged dao with a black cord-wrapped hilt, a dark iron round guard and a thin red cord tassel on the pommel, its blade planted point-down into the ground at a slight tilt, standing alone and upright, framed vertically from the pommel at the top down to where the blade enters the ground at the bottom, the wet steel blade long and slightly curved with a clean bright edge, the blade cut off cleanly at the bottom edge of the frame where it would enter the ground, a few water droplets beading on the steel', COLD),
 'raise_low': (GT, 'LS', 'full body seen from a very LOW worm-eye angle from in front and below, standing tall with feet planted wide apart, BOTH arms raised straight above his head gripping the dao hilt, the long blade pointing straight up into the sky, chin lifted looking up, ponytail and robe hem whipped sideways by a storm wind, strong silhouette shape with arms and blade clearly separated from the body, his whole body from head to boots and the full blade inside the frame', COLD),
 'companions': (None, 'LS', 'four young martial artists standing side by side in a row, all facing the camera, full body, evenly spaced with clear gaps between them, each with a clearly different silhouette: (1) a tall young man in a long scholar robe with a hair crown and a sword on his back, (2) a slim young woman with a high bun and hairpins holding a long spear upright, (3) a gentle young woman with long loose hair and flowing ribbons on her sleeves, (4) a short teenage boy with a messy topknot holding a short wooden staff, calm sad expressions', SOFT),
}
PROPS = {'sword_planted'}
RATIO = {'sword_planted': '9:16', 'raise_low': '9:16'}
INPUTS = {'companions': ['男主师兄_谢玄洲.webp', '男主师姐_丁昭.webp', '女主_殷若.webp', '男主徒弟_杨不丢.webp']}


def prompt(name):
    char, size, pose, light = JOBS[name]
    if name in PROPS:
        return pose[0].upper() + pose[1:] + '. No hands, no human body parts. Weapon design as in the reference sheet: long single-edged Chinese dao, black cord-wrapped handle, red tassel. ' + BG + light
    look = '' if char is None else (plan.TSH_LOOK if char == TSH else plan.GT_LOOK) + ' '
    extra = ('Keep the faces and outfits of the four reference characters, in order from left to right. ' if name == 'companions' else '')
    return pose[0].upper() + pose[1:] + '. ' + plan.FRAME.get(size, '') + plan.HANDS + look + extra + BG + light


def body(name):
    refs = INPUTS.get(name) or [JOBS[name][0] + '.webp']
    return dict(model='RH_image2', prompt=prompt(name), ratio=RATIO.get(name, '16:9'), size='4K', input=[REFS[r] for r in refs])


def load():
    return json.load(open(STATE)) if os.path.exists(STATE) else {'spent': 0, 'jobs': {}}


def save(s):
    json.dump(s, open(STATE, 'w'), ensure_ascii=False, indent=1)


def log(name, pts, tid, res, path, note):
    open(LOG, 'a').write('| %s | D组/%s | RH_image2 | 4K 16:9 | %s | %s | %s | %s | %s |\n' % (
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
        log(n, q, tid, 'submitted', '-', 'try%d %s' % (len(j['tries']), JOBS[n][2][:60]))
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
            log(n, 0, tid, 'completed', p.replace(os.path.dirname(ROOT) + '/', ''), 'try%d' % len(j['tries']))
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
        j['state'] = 'done'; log(n, 0, j['tries'][-1]['tid'], '采用', 'assets/gen/D_bridge/%s_raw.png' % n, 'try%d 采用' % len(j['tries']))
    else:
        j['state'] = 'todo'; log(n, 0, j['tries'][-1]['tid'], '判废', '-', why)
    save(s)


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'quote':
        for n in JOBS: print(n, quote(n)[0])
    elif c == 'submit': submit(sys.argv[2:] or list(JOBS))
    elif c == 'poll': poll()
    elif c == 'ok': verdict(sys.argv[2], True)
    elif c == 'bad': verdict(sys.argv[2], False, ' '.join(sys.argv[3:]))
    elif c == 'prompt': print(prompt(sys.argv[2]))
