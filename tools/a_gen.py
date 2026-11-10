"""A 组（前奏 + 主歌一）新精灵生图：报价 → 提交 → 轮询 → 下载候选 → 采用。
  python3 tools/a_gen.py quote             报价全部未提交项
  python3 tools/a_gen.py submit [key ...]  提交（预算 A 组 80 点）
  python3 tools/a_gen.py poll              轮询进行中任务，完成的下载到 /workspace/work/a_cands/
  python3 tools/a_gen.py ok <key>          采用 → assets/gen/A/<key>_raw.png 并抠图 _cut.png
状态：crew/round4/A_gen_state.json；日志 crew/genlog.md。Key 由沙箱代理注入，绝不写文件。"""
import sys, os, json, time, shutil, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import nb
from sprite_plan_rest import GT_LOOK, TSH_LOOK, BG, LIGHT_COLD, FRAME, HANDS
ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv')
STATE = ROOT + '/crew/round4/A_gen_state.json'
LOG = ROOT + '/crew/genlog.md'
CANDS = '/workspace/work/a_cands'
BUDGET = 80
REFS = json.load(open(ROOT + '/assets/characters/asset_urls.json'))
GT, TSH = '男主_鬼屠', '最终boss_太上皇'

JOBS = {
    'eyes': (GT, 'ECU', 'Extreme close-up horizontal strip of ONLY his eyes and brows (from mid-forehead to just below the eyes, nose bridge visible, '
                        'no mouth), loose black hair strands falling across the forehead, amber eyes wide open with a sharp cold killing stare straight into camera, '
                        'a thin cold highlight in each iris.'),
    'blade_face': (GT, 'CU', 'Close-up: he holds the dao vertically right in front of his face, the flat of the steel blade splitting the frame, '
                              'one amber eye visible on each side of the blade edge, cold stare at camera, hair strands across the face, hands on the hilt below the frame edge.'),
    'slash_up': (GT, 'LS', 'Dynamic low-angle view from below: he has just finished a rising diagonal sword cut from low left to high right, '
                            'dao held high above his right shoulder in one hand, blade pointing up to the sky, body twisted, robe and red sash flaring upward, '
                            'fierce expression looking up.'),
    'boots': (GT, 'CU', 'Close-up of ONLY his lower legs and black leather boots mid-stride stepping forward, the lower hem of the black robe and the end of the '
                         'dark red sash swinging, the black scabbard tip hanging beside the leg. NO head, NO upper body.'),
    'tsh_raise': (TSH, 'LS', 'Low-angle view: he stands tall and raises his right arm straight up high above his head, palm open facing the sky as if '
                              'summoning something down from heaven, the very wide sleeve falling down the raised arm, left arm down, cold arrogant expression, '
                              'chin raised, long hair and sleeves moving in wind.'),
    'tsh_hand': (TSH, 'CU', 'Close-up of ONLY his aged long-fingered right hand and the edge of his wide embroidered sleeve, hand descending from the top of the frame, '
                             'pressing down the square handle of a large dark jade imperial seal. NO face.'),
    # 第二棒：V13 跪地求饶者、V12 被斩倒的恶徒（无参考图，纯文字；非主角）
    'kneel_beg': (None, 'LS', 'Full body side view (facing left) of a middle-aged wuxia bandit thug in a torn dark brown hemp robe, leather bracers and a loose '
                              'head cloth, kneeling on the ground and bowing deeply, both palms pressed together raised in front of his lowered face, '
                              'begging for mercy, trembling, his broken sabre dropped on the ground beside his knees. Whole figure inside the frame with margin.'),
    'villain_fall': (None, 'LS', 'Full body side view (facing left) of a burly wuxia bandit in dark leather lamellar armour and a ragged dark cloak, '
                                 'struck by a sword: staggering backwards off balance, head thrown back, one arm flung up, his sabre flying out of his hand, '
                                 'cloak flaring. Whole figure inside the frame with margin.'),
    # 第四棒（r4）：V05 手+刀特写（脸不入画）、V01 雨打刃口微距、A07b 背影走向城门
    'hand_draw_cu': (GT, 'ECU', 'Extreme close-up of ONLY his right hand gripping the black cord-wrapped handle of the dao at his waist and drawing the '
                                 'blade a few inches out of the black lacquered scabbard, his left thumb pushing the brass guard, a bright line of cold light '
                                 'along the exposed steel, leather wrist guard, edge of the black sleeve and the dark red sash. Camera at waist height, '
                                 'NO face, NO head, NO shoulders in frame.'),
    'blade_rain': (GT, 'ECU', 'Macro extreme close-up of ONLY the tip section of the long single-edged dao steel blade, seen in steep perspective with the '
                               'tip pointing toward the camera lens, visible hamon temper line and fine forged steel grain, tiny scratches, raindrops beading '
                               'and splashing on the polished flat of the blade, a cold moonlight specular highlight running along the edge. NO person, NO hand.'),
    'back_walk': (GT, 'MS', 'Full body rear view from behind: he walks away from camera toward the distance, back to camera, long high ponytail and black '
                             'robe hem swaying, the dao in its scabbard at his left hip, dark red sash trailing, shoulders squared, mid-stride. Whole figure '
                             'inside the frame with margin, face not visible.'),
    'stand_ha': (GT, 'LS', 'High-angle view from above and behind (camera about 45 degrees down): full body, he stands alone with feet apart, '
                            'dao held low in his right hand with the tip touching the ground, head tilted up looking up over his shoulder toward the sky, '
                            'robe hem and red sash blown sideways by strong wind. Whole figure inside the frame with margin.'),
    # 第六棒（r6）：V08 手握玉玺抬起、V09 青铜天平道具、V17/V16 巨印侧面体积、V15 握柄刻碑
    'tsh_seal_lift': (TSH, 'CU', 'Close-up of ONLY his aged long-fingered right hand firmly gripping the carved knob of a heavy dark green jade imperial seal '
                                 '(a square jade block about the size of a fist, knob carved as a coiled dragon, glossy polished jade with inner translucency and '
                                 'small chips), lifting it straight up, the flat square base of the seal facing down toward the bottom of the frame with traces of '
                                 'red cinnabar seal paste on the bottom edge, the wide embroidered dark charcoal sleeve edge at the top of the frame. Seen from a '
                                 'low side angle. NO face, NO paper, NO table.', 'WARM'),
    'bronze_scale': ('PROP', 'LS', 'Single object, full view, centered, whole object inside the frame with margin: an ancient Chinese bronze equal-arm balance '
                                   'scale, heavy dark patinated bronze central pillar on a stepped base, thick bronze crossbeam with engraved taotie and cloud patterns '
                                   'and a gilded edge highlight, the beam tilted slightly (right side lower), heavy bronze chains to two deep round bronze pans. '
                                   'LEFT pan: piled high with dozens of small white rice-paper cut-out human figures (paper dolls, simple flat silhouettes with ink '
                                   'line faces), layered and overlapping, some hanging over the rim. RIGHT pan: a single heavy gold imperial seal with a coiled dragon '
                                   'knob, glinting. Photorealistic museum-grade materials, worn bronze with green patina and polished golden wear on edges.', 'WARM'),
    'giant_seal': ('PROP', 'LS', 'Single object, full view, whole object inside the frame with margin: a colossal ancient square imperial seal carved from dark '
                                 'grey-green stone (jade-stone), seen from a low three-quarter side angle so we see two side faces and the underside edge but NOT '
                                 'the carved bottom face, on top a carved crouching qilin beast knob, the side faces weathered with deep cracks, chipped broken '
                                 'corners, carved cloud bands near the top, faint traces of old red cinnabar on the bottom rim. Massive, heavy, monumental.', 'WARM'),
    'carve_grip': (GT, 'MCU', 'Side view medium close-up (facing left): he grips the black cord-wrapped handle of the long dao with BOTH hands near his chest, '
                              'pressing the blade forward and down so the blade extends straight out to the LEFT edge of the frame horizontally, the tip at the '
                              'very left edge, as if carving into a stone wall just outside the frame, intense focused eyes looking along the blade, jaw set, '
                              'rain-wet hair strands.', 'COLD'),
    # 第八棒（r8）：V20 撩刀前蓄势（与 slash_up 组成两档姿态）
    'slash_coil': (GT, 'LS', 'Dynamic low-angle view from below: full body, he is coiled low in a deep crouching lunge just BEFORE a rising sword cut, '
                              'knees bent deeply, weight on the front left leg, torso twisted to his right, both hands gripping the dao held low behind '
                              'his right hip with the blade pointing down and back toward the ground, eyes looking up fiercely toward the sky, '
                              'black robe hem and dark red sash swirling around the legs, long high ponytail whipping. Whole figure inside the frame with margin.'),
}
LIGHTS = dict(WARM='Lighting: warm golden candlelight key from the upper right, a cold faint rim from behind left, deep shadows, cinematic photorealistic. ')
PROP_LOOK = 'Grounded realistic ancient Chinese artifact, no people, no hands, no text, no letters. '
VILLAIN_LOOK = ('Gritty realistic Chinese wuxia film costume, weathered fabric, scarred rough face, no modern items. ')


def prompt(char, size, pose, light=None):
    look = GT_LOOK if char == GT else (TSH_LOOK if char == TSH else (PROP_LOOK if char == 'PROP' else VILLAIN_LOOK))
    lt = LIGHTS.get(light, LIGHT_COLD) if light else LIGHT_COLD
    return (BG + 'Subject: ' + pose + ' ' + look + ' ' + FRAME[size] + lt + ('' if char == 'PROP' else HANDS) +
            'Photorealistic high-end wuxia film still, sharp focus, ultra detailed fabric and skin texture.')


def body(k):
    c, s, p = JOBS[k][:3]; lt = JOBS[k][3] if len(JOBS[k]) > 3 else None
    d = dict(model='RH_image2', prompt=prompt(c, s, p, lt), ratio='16:9', size='4K')
    if c and c != 'PROP': d['input'] = [REFS[c + '.webp']]
    return d


def load():
    return json.load(open(STATE)) if os.path.exists(STATE) else {'spent': 0, 'jobs': {}}


def save(s): json.dump(s, open(STATE, 'w'), ensure_ascii=False, indent=1)


def log(k, pts, tid, res, path, note):
    open(LOG, 'a').write('| %s | A/%s | RH_image2 | 4K 16:9 | %s | %s | %s | %s | %s |\n' % (
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
            log(k, 0, '-', 'submit_failed http_%s' % st, '', 'A组'); print('fail', k, raw[:200]); continue
        s['spent'] += q
        s['jobs'].setdefault(k, []).append(dict(task_id=tid, status='running', pts=q, file=None))
        log(k, q, tid, 'submitted', '-', 'A组 %s try%d' % (k, len(s['jobs'][k])))
        print('submitted', k, tid, q)
        save(s)
    print('spent', s['spent'])


def poll():
    s = load()
    for k, tries in s['jobs'].items():
        for tr in tries:
            if tr['status'] != 'running': continue
            st, raw = nb.api('GET', '/api/skills/tasks/%s' % tr['task_id'])
            task = (json.loads(raw) or {}).get('task') or {}
            ss = (task.get('status') or '').lower()
            if ss == 'completed' and task.get('result_urls'):
                fs = nb.download(task['result_urls'], CANDS, k + '_' + tr['task_id'][:8])
                tr['status'] = 'done'; tr['file'] = fs[0]
                log(k, 0, tr['task_id'], 'completed', fs[0], 'A组 候选')
            elif ss in nb.FAILED:
                tr['status'] = ss; log(k, 0, tr['task_id'], ss, '-', 'A组 失败')
            print(k, tr['task_id'][:8], ss)
    save(s)


def ok(k):
    s = load(); tr = [x for x in s['jobs'][k] if x['file']][-1]
    os.makedirs(ROOT + '/assets/gen/A', exist_ok=True)
    raw = ROOT + '/assets/gen/A/%s_raw.png' % k
    from PIL import Image
    Image.open(tr['file']).convert('RGB').save(raw)
    subprocess.run(['python3', ROOT + '/tools/recut_flat.py', raw, raw.replace('_raw', '_cut'), '16'], check=True)
    tr['accepted'] = True; save(s)
    log(k, 0, tr['task_id'], '采用', 'assets/gen/A/%s_raw.png' % k, 'A组 采用')


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'quote':
        for k in JOBS: print(k, quote(k))
    elif c == 'submit': submit(sys.argv[2:] or list(JOBS))
    elif c == 'poll': poll()
    elif c == 'ok': ok(sys.argv[2])
