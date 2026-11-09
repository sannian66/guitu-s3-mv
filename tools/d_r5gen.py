"""[D组 r5] #45 3:00（S18_Draw 180.09–181.00）主角重新出图：整幅写实暗调电影剧照（不再是灰底精灵贴雨景）。
  python3 tools/d_r5gen.py quote <名字>
  python3 tools/d_r5gen.py submit <名字>..      提交（记 crew/genlog.md），task id 存 crew/round5/D_r5_gen.json
  python3 tools/d_r5gen.py poll                 完成的下载到 assets/gen/R5_D/cands/
Key 由 .env.local / 代理注入，绝不写文件。"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))
import nb
ROOT = '/workspace/work/mv'
STATE = ROOT + '/crew/round5/D_r5_gen.json'
CANDS = ROOT + '/assets/gen/R5_D/cands'
LOG = ROOT + '/crew/genlog.md'
REFS = json.load(open(ROOT + '/assets/characters/asset_urls.json'))

LOOK = ('The man MUST keep exactly the same face and hairstyle as the character reference sheet (first image): young man, sharp straight brows, '
        'amber eyes, pale lean face, long black messy hair tied in a HIGH PONYTAIL on top of the head, loose wet strands over the forehead (center-parted messy bangs). '
        'Outfit: black layered wuxia robe with a dark red inner collar, dark brown leather waist wrap, black leather wrist guards. '
        'Weapon: a long single-edged Chinese dao with a black cord-wrapped handle and a small red cord tassel, black scabbard. '
        'Hands anatomically correct, five fingers. ')
STYLE = ('Photorealistic live-action cinematic film still, shot on ARRI Alexa with anamorphic lens, dark low-key grade, desaturated cold steel-blue night, '
         'real skin texture, real wet fabric, heavy night rain with visible rain streaks, wet black stone ground with puddle reflections, faint mist. '
         'Same realistic look as the second image (an extreme close-up of the same man\'s eye) for skin, grade and grain. '
         'Composed for a 2.39:1 cinemascope crop: keep the whole head and the blade inside the middle 75% of the frame height, '
         'subject on the right half, the left 40% of the frame is dark empty rainy night. No text, no letters, no watermark, no letterbox bars, not anime, not 3D render, not illustration. ')
JOBS = {
 'draw_a': 'Medium shot from the knees up, slightly low angle. The man stands three-quarter facing left in heavy rain, slowly drawing the dao out of the scabbard at his left hip with his right hand, '
           'about two thirds of the bright wet steel blade already out and held horizontally across his body, a cold highlight running along the edge. '
           'Head slightly lowered, eyes raised looking past the camera with cold quiet resolve. Strong cold moonlight rim light from behind right outlining hair, '
           'shoulders and blade, rain drops sparkling in the rim light, water dripping from the hair and the ponytail. ',
 'draw_b': 'Medium close shot from the waist up, the camera at chest height. The man in heavy rain, body turned sideways facing left, head turned toward the camera, '
           'his right hand pulling the dao out of the scabbard at his left hip, the long wet blade half drawn and angled slightly upward across the frame, '
           'cold light glinting on the edge. Determined cold stare, wet hair strands stuck to the forehead and cheek. Hard cold backlight from upper right, '
           'rain streaks lit behind him, dark misty night around. ',
 'draw_c': 'Medium-wide shot from the knees up, eye-level camera. The man stands still in the downpour on a wet stone courtyard at night, body in profile facing left, '
           'right hand gripping the hilt at his left hip and the blade drawn halfway out of the black scabbard, steel catching a thin line of cold light. '
           'Face in three-quarter view, eyes looking ahead with calm killing intent. Cold blue rim light from behind, puddles reflecting his silhouette, '
           'splashes around his boots blurred out of frame. ',
}
EYE = None


def body(n):
    eye = json.load(open(STATE)).get('eye_url') if os.path.exists(STATE) else None
    inp = [REFS['男主_鬼屠.webp']] + ([eye] if eye else [])
    return dict(model='RH_image2', prompt=JOBS[n] + LOOK + STYLE, ratio='16:9', size='4K', input=inp)


def load(): return json.load(open(STATE)) if os.path.exists(STATE) else {'spent': 0, 'jobs': {}}
def save(s): json.dump(s, open(STATE, 'w'), ensure_ascii=False, indent=1)


def log(n, pts, tid, res, path, note):
    open(LOG, 'a').write('| %s | D组/R5_D/%s | RH_image2 | 4K 16:9 | %s | %s | %s | %s | %s |\n' % (time.strftime('%m-%d %H:%M'), n, pts, tid, res, path, note))


if __name__ == '__main__':
    cmd = sys.argv[1]
    s = load()
    if cmd == 'eye':
        s['eye_url'] = nb.upload(ROOT + '/assets/gen/S102/eye_open_raw.png'); save(s); print(s['eye_url'])
    elif cmd == 'quote':
        print(nb.api('POST', '/api/skills/images/quote', body(sys.argv[2]))[1][:400])
    elif cmd == 'submit':
        for n in sys.argv[2:]:
            st, raw = nb.api('POST', '/api/skills/images/quote', body(n))
            q = json.loads(raw).get('billing', {}).get('total_points')
            if q is None or s['spent'] + q > 30: print('stop', n, q, s['spent']); break
            st, raw = nb.api('POST', '/api/skills/generate', body(n), timeout=60)
            d = json.loads(raw); tid = d.get('task_id') or d.get('skill_task_id') or (d.get('task') or {}).get('id')
            if not tid: print(n, 'submit failed', st, raw[:300]); continue
            k = n + '_%d' % (sum(1 for j in s['jobs'] if j.startswith(n + '_')) + 1)
            s['jobs'][k] = {'tid': tid, 'pts': q, 'state': 'running'}; s['spent'] += q
            log(k, q, tid, 'submitted', '-', '[D组 r5] #45 S18 整幅写实重出')
            print(k, tid, q); save(s)
        print('spent', s['spent'])
    elif cmd == 'poll':
        for k, j in s['jobs'].items():
            if j['state'] != 'running': continue
            st, raw = nb.api('GET', '/api/skills/tasks/%s' % j['tid'], timeout=30)
            t = (json.loads(raw) or {}).get('task') or {}
            stt = (t.get('status') or '').lower()
            if stt == 'completed' and t.get('result_urls'):
                p = nb.download(t['result_urls'][:1], CANDS, k)[0]
                j['state'] = 'done'; j['file'] = p
                log(k, 0, j['tid'], 'completed', p.replace(ROOT + '/', ''), '')
                print(k, 'done', p)
            elif stt in nb.FAILED:
                j['state'] = 'failed'; log(k, 0, j['tid'], stt, '-', 'failed'); print(k, stt)
            else: print(k, stt or st)
        save(s)
