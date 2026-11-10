"""C 组第五棒生图（统一脸 + 实材质道具）。报价 → 提交 → 轮询，状态并入 crew/round4/C_gen_state.json，日志 crew/genlog.md。
  python3 crew/round4/C_gen5.py ref <img>        上传马尾版定妆脸（C40b point_cam 脸部裁切）→ 记入状态 ref_url
  python3 crew/round4/C_gen5.py quote|submit [名字,...]|poll
Key 由沙箱代理注入，绝不写文件。"""
import sys, os, json, time
ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv')
sys.path.insert(0, ROOT + '/tools')
import nb
from sprite_plan_rest import GT_LOOK, BG, HANDS
STATE = ROOT + '/crew/round4/C_gen_state.json'
CANDS = '/workspace/work/c_cands5'
LOG = ROOT + '/crew/genlog.md'
BUDGET = 80
REFS = json.load(open(ROOT + '/assets/characters/asset_urls.json'))
FACE = ('SAME person as BOTH reference images (character sheet + ponytail close-up): young slender pale man, soft youthful oval face, '
        'NOT square-jawed, sharp straight brows, amber eyes, black hair tied in a HIGH PONYTAIL, loose messy strands over the forehead parted in the middle. ')
STORM = ('Lighting: harsh cold white lightning flash from behind and above as a hard rim light outlining hair and shoulders, dim cold blue fill from the front, '
         'deep shadows, high contrast, soaking wet hair and skin with rain drops, cinematic photorealistic film still. ')
PLATE = ' Cinematic photorealistic film still, no people, no text, no letters, no watermark, no letterbox bars.'
JOBS = {
 'c07_chin': ('hero', 'C07', FACE + GT_LOOK + ' Pose: medium close-up from chest up, three-quarter view facing camera right, he slowly lifts his chin defiantly, '
              'eyes looking down at the camera with cold contempt, jaw set, wet strands stuck to his forehead and cheeks, ponytail visible behind his head. '
              'Framing: chest to top of ponytail inside the frame with margin, head in upper half. ' + STORM + BG),
 'c08_eyes': ('hero', 'C08', FACE + ' Extreme close-up of his eyes and brows ONLY (from mid-nose to forehead), facing camera, amber irises, rain drops on eyelashes and brows, '
              'wet black strands across the forehead, one cold white catchlight of lightning in each pupil, fierce unblinking stare. '
              'Lighting: cold lightning from upper right, dim fill, deep shadow, cinematic photorealistic macro film still. ' + BG),
 'c14_ots': ('hero', 'C14', FACE + GT_LOOK + ' Over-the-shoulder shot from directly BEHIND and slightly BELOW him: back of his head, high ponytail and shoulders fill the lower half of the frame, '
             'head tilted back looking straight up at the sky, only a sliver of his jaw and cheek visible in lost profile, soaking wet hair and black robe shoulders. '
             'Lighting: brilliant cold white lightning from directly ABOVE AND IN FRONT of him making a strong silhouette with a crisp bright rim along hair, ponytail, ear and shoulders, the back of his head mostly dark. '
             'Framing: head and shoulders, nothing cropped at the top. ' + BG),
 'c28_face': ('hero', 'C28', FACE + GT_LOOK + ' Extreme close-up of his FACE ONLY (from chin to top of head, ponytail base visible), three-quarter view turned slightly to camera left, '
              'eyes wide open and fierce, looking past camera into a blinding light, rain water running down his cheek. '
              'Lighting: a hard narrow band of brilliant warm white-gold light falls across his eyes from the front-left (light pouring through a crack), the rest of the face in deep cold shadow, '
              'cold blue rim on the far edge, cinematic photorealistic film still. Framing: face fills about 70% of frame height, margin around the head. ' + BG),
 'c38_grip': ('hero', 'C38', 'Macro close-up of ONLY his right hand and forearm, NO face: the hand clenching the black cord-wrapped handle of a Chinese dao very tightly, knuckles white, veins and tendons '
              'standing out on the back of the hand and wrist, rain water streaming over the skin and dripping from the knuckles, dark leather wrist guard and soaked black sleeve, '
              'the round dark iron guard and the first part of the blade visible, hand rotated toward camera. '
              'Lighting: cold white side-back light from the upper left raking across the knuckles and veins, deep shadows, cinematic photorealistic film still. '
              'Framing: hand and wrist in the center with margin, sleeve entering from the left edge. ' + HANDS + BG),
 'c22_wall': (None, 'C22', 'Extreme low-angle wide shot looking up at a colossal ancient Chinese fortress wall of dark iron-black stone blocks rising vertically into churning thunderstorm clouds, '
              'the top of the wall lost in the clouds, huge cold lightning bolt behind it lighting the wet stone, rain streaking, deep shadows, water flooding the ground at its base reflecting the wall, '
              'the wall spans the full width of the frame, faint carved square stone panels on its surface, dramatic scale.' + PLATE),
 'c37_plaque': (None, 'C37', 'A huge ancient Chinese horizontal ceremonial wooden plaque (bian e), front view, black lacquered wood with an ornate carved gilded dragon frame, '
                'the central panel is completely BLANK smooth black lacquer with no characters, wet with rain, worn gold leaf, iron hanging rings at the top corners. '
                'Lighting: cold lightning light from the top left, gold glints, deep shadows, cinematic photorealistic. Framing: the whole plaque centered, horizontal, with margin. ' + BG),
 'c10_tablets': (None, 'C10', 'Low-angle view of the dark carved wooden eave and roof beam of an ancient Chinese palace at night in heavy rain, with FOUR identical tall narrow blank dark wooden tablets '
                 '(vertical name boards, no characters) hanging in a row on red cords below the beam, evenly spaced across the middle of the frame, rain dripping from the tiles and tablets, '
                 'cold lightning from behind, mist, the lower 40% of the frame is dark rainy night air.' + PLATE),
 'c23_bronze': (None, 'C23', 'Front view of ONE square ancient bronze plaque tile, thick cast bronze with green patina and worn polished edges, a raised border, the central field completely BLANK and flat (no characters), '
                'rain droplets on it, bolted rivets in the corners. Lighting: cold lightning from the upper left, metallic highlights, cinematic photorealistic. Framing: the tile centered with margin, square. ' + BG),
 'c16_drip': ('hero', 'C16', 'Close-up of ONLY the last 40 cm of a Chinese dao blade pointing straight DOWN, tip at the bottom center, the steel wet with rain, a thick dark red drop of blood '
              'running down the edge and hanging from the very tip about to fall, a hand and sleeve are NOT visible. '
              'Lighting: cold white lightning rim from above on the blade edge, dark, cinematic photorealistic macro. Framing: blade vertical in the center, tip with margin below. ' + BG),
}


def load(): return json.load(open(STATE))
def save(s): json.dump(s, open(STATE, 'w'), ensure_ascii=False, indent=1)


def body(k, s):
    ch = JOBS[k][0]; b = dict(model='RH_image2', prompt=JOBS[k][2], ratio='16:9', size='4K')
    if ch == 'hero': b['input'] = [REFS['男主_鬼屠.webp'], s['ref_url']]
    return b


def log(name, pts, tid, res, path, note):
    open(LOG, 'a').write('| %s | C组/%s | RH_image2 | 4K 16:9 | %s | %s | %s | %s | [C组] 第五棒 %s |\n' % (time.strftime('%m-%d %H:%M'), name, pts, tid, res, path, note))


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
