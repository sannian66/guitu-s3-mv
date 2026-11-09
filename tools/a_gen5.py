"""A 组第五轮（r5）生图：python3 tools/a_gen5.py quote|submit <key..>|poll|ok <key> [cand_idx] [cutter]
状态 crew/round5/A_gen_state_r5.json；日志 crew/genlog.md；候选 /workspace/work/a_cands/r5/（仓库外）；采用 → assets/gen/R5_A/<key>_raw.png + _cut.png。
Key 只从 .env.local 读（tools/nb.py），绝不写入仓库。预算：本轮 A 组 45 点。"""
import sys, os, json, time, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import nb
from sprite_plan_rest import GT_LOOK, TSH_LOOK, BG, LIGHT_COLD, FRAME, HANDS
ROOT = '/workspace/work/mv'
STATE = ROOT + '/crew/round5/A_gen_state_r5.json'
LOG = ROOT + '/crew/genlog.md'
CANDS = '/workspace/work/a_cands/r5'
OUT = ROOT + '/assets/gen/R5_A'
BUDGET = 45
REFS = json.load(open(ROOT + '/assets/characters/asset_urls.json'))
GT = '男主_鬼屠'
STYLE = ('Photorealistic high-end dark wuxia film still, same look as a gritty cinematic Chinese period epic, sharp focus, ultra detailed fabric, '
         'leather and skin texture, natural anatomy, elegant strong silhouette. ')
SIDE = 'Lighting: cold moonlight key from the upper left, strong cold rim light from behind outlining hair, shoulders and blade, deep shadows. '

JOBS = {
    # #3 V06 挥刀三段（同机位、同景别、同一人，刀从左后上方横扫向画面右侧）
    'slash_a': (GT, 'LS', 'Full body, three-quarter front view, camera at waist height slightly below: he is WOUND UP just before a powerful horizontal '
                         'sweeping sword cut toward the RIGHT side of the image. Torso twisted far to his own left (image left), both hands gripping the '
                         'black handle of the dao raised beside his left shoulder, the long blade pointing back behind his head and shoulder, '
                         'knees bent in a deep wide stance, right foot forward, eyes locked fiercely toward the right of the frame, black robe hem and '
                         'long dark red sash swinging, high ponytail flying. Whole figure inside the frame with margin.'),
    'slash_b': (GT, 'LS', 'Full body, three-quarter front view, camera at waist height slightly below: he is captured in the MIDDLE of a powerful '
                         'horizontal sweeping sword cut from image left to image right: hips and torso rotating forward explosively, both arms '
                         'extended in front of his chest, the long dao blade sweeping flat across his body at chest height with a subtle motion blur along '
                         'the blade, black robe hem, wide sleeves and long dark red sash whipping around from the rotation, high ponytail swinging, '
                         'fierce focused face. Whole figure inside the frame with margin.'),
    'slash_c': (GT, 'LS', 'Full body, three-quarter front view, camera at waist height slightly below: he has JUST FINISHED a powerful horizontal '
                         'sweeping sword cut toward the image right: deep lunge with the right leg forward and bent, torso rotated toward the right, his '
                         'right arm fully extended out to the image right holding the dao, the long blade continuing past his body pointing out to the '
                         'right and slightly down, left arm swung back for balance, black robe hem and the long dark red sash flaring out in a wide arc '
                         'following the swing, high ponytail whipping, intense cold expression. Whole figure inside the frame with margin.'),
    # #8 V14 拔刀特写（人在画左 2/3，右 1/3 留给火星字列）
    'draw_mcu': (GT, 'MCU', 'Medium close-up, three-quarter view, from chest up, the character placed in the LEFT two thirds of the frame: he slowly '
                            'draws the long dao from its black lacquered scabbard held across his chest — right hand on the black cord-wrapped handle '
                            'pulling the bright steel blade half out, the blade rising diagonally from his chest toward the upper right, left hand '
                            'holding the scabbard mouth, head slightly lowered, amber eyes looking up straight into the camera with a cold calm deadly '
                            'gaze, handsome sharp features, a few wet strands of hair across the forehead, high ponytail visible. The right third of '
                            'the frame is empty grey background.'),
    # #11 V20 撩刀（极低机位、向右上劈出）
    'rise_slash': (GT, 'LS', 'Dynamic heroic low-angle view from below: full body, he rises explosively in a powerful upward diagonal sword cut, the dao '
                             'swung up from low left to high right in his right hand, sword arm extended up and to the image right with the long blade '
                             'high above pointing to the upper right sky, the other arm stretched back and down for balance, body arched in a strong '
                             'elegant S-curve, back leg extended, front knee bent, black robe hem, wide sleeves and long dark red sash swirling upward '
                             'in a spiral, high ponytail whipping, fierce expression looking up toward the upper right. Whole figure inside the frame with margin.'),
    # #10 V16 巨印（以 A_r6/giant_seal 为参考保持同一器物，改仰视三维体积）
    'seal3d': ('SEAL', 'LS', 'The SAME colossal ancient imperial seal as the reference image (same carved crouching qilin beast knob on top, same square '
                             'block with carved cloud band, cracks and chipped corners, traces of old red cinnabar on the bottom rim), now carved from '
                             'dark green nephrite JADE: polished surfaces with real translucency, thin edges glowing with subsurface light, worn gilt in '
                             'the carved grooves. Seen from a dramatic LOW angle from far below at three-quarter view, the seal hanging overhead in the '
                             'sky tilted toward the viewer, so the underside face edge and two side faces show in strong three-point perspective; '
                             'massive, monumental, heavy. Strong warm golden backlight from directly behind and above creating a bright golden rim '
                             'along every edge and the qilin silhouette, warm bounce on the underside, deep shadow on the near faces revealing volume. '
                             'Whole object inside the frame with margin. No people, no hands, no text.'),
}
INPUT = {'seal3d': None}   # 运行时上传 giant_seal_raw.png 填入


def prompt(k):
    c, s, p = JOBS[k]
    if c == 'SEAL':
        return BG + 'Subject: ' + p + ' Photorealistic museum-grade material rendering, cinematic. '
    return BG + 'Subject: ' + p + ' ' + GT_LOOK + ' ' + FRAME[s] + SIDE + HANDS + STYLE


def body(k):
    d = dict(model='RH_image2', prompt=prompt(k), ratio='16:9', size='4K')
    c = JOBS[k][0]
    if c == GT: d['input'] = [REFS[GT + '.webp']]
    if c == 'SEAL':
        s = load()
        if not s.get('seal_ref'):
            s['seal_ref'] = nb.upload(ROOT + '/assets/gen/A_r6/giant_seal_raw.png'); save(s)
        d['input'] = [s['seal_ref']]
    return d


def load(): return json.load(open(STATE)) if os.path.exists(STATE) else {'spent': 0, 'jobs': {}}
def save(s): json.dump(s, open(STATE, 'w'), ensure_ascii=False, indent=1)


def log(k, pts, tid, res, path, note):
    open(LOG, 'a').write('| %s | A_r5/%s | RH_image2 | 4K 16:9 | %s | %s | %s | %s | %s |\n' % (
        time.strftime('%m-%d %H:%M'), k, pts, tid, res, path, note))


def quote(k):
    st, raw = nb.api('POST', '/api/skills/images/quote', body(k))
    return json.loads(raw).get('billing', {}).get('total_points')


def submit(keys):
    s = load()
    for k in keys:
        q = quote(k)
        if q is None: print('quote fail', k); continue
        if s['spent'] + q > BUDGET: print('budget reached', s['spent']); break
        st, raw = nb.api('POST', '/api/skills/generate', body(k), timeout=60)
        try: d = json.loads(raw)
        except Exception: d = {}
        tid = d.get('task_id') or d.get('skill_task_id') or (d.get('task') or {}).get('id')
        if not tid:
            log(k, 0, '-', 'submit_failed http_%s' % st, '', 'A组 r5'); print('fail', k, raw[:300]); continue
        s = load(); s['spent'] += q
        s['jobs'].setdefault(k, []).append(dict(task_id=tid, status='running', pts=q, file=None))
        log(k, q, tid, 'submitted', '-', 'A组 r5 %s try%d' % (k, len(s['jobs'][k])))
        print('submitted', k, tid, q); save(s)
    print('spent', load()['spent'])


def poll():
    s = load()
    for k, tries in s['jobs'].items():
        for i, tr in enumerate(tries):
            if tr['status'] != 'running': continue
            st, raw = nb.api('GET', '/api/skills/tasks/%s' % tr['task_id'])
            try: task = (json.loads(raw) or {}).get('task') or {}
            except Exception: task = {}
            ss = (task.get('status') or '').lower()
            if ss == 'completed' and task.get('result_urls'):
                fs = nb.download(task['result_urls'], CANDS, '%s_try%d' % (k, i + 1))
                tr['status'] = 'done'; tr['file'] = fs[0]
                log(k, 0, tr['task_id'], 'completed', fs[0].replace('/workspace/work/', ''), 'A组 r5 try%d' % (i + 1))
            elif ss in nb.FAILED:
                tr['status'] = ss; log(k, 0, tr['task_id'], ss, '-', 'A组 r5 失败')
            print(k, i + 1, tr['task_id'][:8], ss or st)
    save(s)


def ok(k, idx=-1, cutter='cutout'):
    s = load(); tr = [x for x in s['jobs'][k] if x['file']][idx]
    os.makedirs(OUT, exist_ok=True)
    raw = OUT + '/%s_raw.png' % k
    from PIL import Image
    Image.open(tr['file']).convert('RGB').save(raw)
    if cutter == 'flat': subprocess.run(['python3', ROOT + '/tools/recut_flat.py', raw, raw.replace('_raw', '_cut'), '16'], check=True)
    else: subprocess.run(['python3', ROOT + '/tools/cutout.py', raw, raw.replace('_raw', '_cut')], check=True)
    tr['accepted'] = True; save(s)
    log(k, 0, tr['task_id'], '采用', 'assets/gen/R5_A/%s_raw.png' % k, 'A组 r5 采用')


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'quote':
        for k in (sys.argv[2:] or JOBS): print(k, quote(k))
    elif c == 'submit': submit(sys.argv[2:])
    elif c == 'poll': poll()
    elif c == 'ok': ok(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else -1, sys.argv[4] if len(sys.argv) > 4 else 'cutout')
