"""男主鬼屠 定妆特写 4 张（S043 回头 / S029 握刀手 / S044 推刀 / S038 刀上眼睛），RH_image2 4K，参考 assets/characters/男主_鬼屠.webp"""
import sys, json, os, time, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__)); import nb
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ref = json.load(open(os.path.join(ROOT, 'assets/characters/asset_urls.json')))['男主_鬼屠.webp']
STYLE = ('Cinematic wuxia film still, photorealistic, anamorphic 2.39:1 framing inside a 16:9 frame with black letterbox bars, '
         'night, cold moonlight rim light from behind, deep blacks, palette strictly black, white, grey with accents of blood red and dim gold, '
         'fine rain, film grain, shallow depth of field. The character MUST keep exactly the same face and hairstyle as the reference sheet: '
         'young man, sharp brows, amber eyes, pale skin, long black hair in a high messy ponytail with loose strands over the forehead. '
         'Outfit may be the black robe with dark red inner collar and leather wrist guards. No text, no watermark.')
SHOTS = {
 'S043_turn_head': 'Close-up, the swordsman seen from behind over his shoulder, turning his head back toward camera in profile-to-three-quarter, '
                   'one eye catching moonlight, wet hair strands whipping in the wind, calm, resolute, guarded gaze.',
 'S029_grip_hand': 'Extreme close-up of his right hand gripping a long dao sword handle wrapped in black cord, knuckles tense, leather wrist guard, '
                   'rain drops on skin and steel, tsuba-like guard catching a thin line of light, blurred robe behind.',
 'S044_thumb_push': 'Extreme close-up of his left thumb pushing the sword guard out of the scabbard, an inch of bright steel revealed, '
                    'red tassel on the scabbard, his face out of focus in the background.',
 'S038_eye_on_blade': 'Extreme close-up of a polished sword blade held horizontally; his amber eye and brow reflected sharply in the mirror-like steel, '
                      'rain drops beading on the blade, the rest in darkness, a faint red glow along the edge.',
}
def one(k):
    body = dict(model='RH_image2', prompt=SHOTS[k] + ' ' + STYLE, ratio='16:9', size='4K', input=[ref])
    q = json.loads(nb.api('POST', '/api/skills/images/quote', body)[1]).get('billing', {})
    r = nb.generate(body, os.path.join(ROOT, 'out/gen/hero_cu'))
    return k, q, r
log = os.path.join(ROOT, 'crew/genlog.md')
if __name__ == "__main__":
 with cf.ThreadPoolExecutor(4) as ex:
     for k, q, r in ex.map(one, SHOTS):
         files = r.get('files', [])
         if files:
             os.rename(files[0], os.path.join(os.path.dirname(files[0]), k + os.path.splitext(files[0])[1])); files = [os.path.join(os.path.dirname(files[0]), k + os.path.splitext(files[0])[1])]
         print(k, q, r.get('_error'), files, flush=True)
         open(log, 'a').write('| %s | %s | RH_image2 | 4K 16:9 | %s | %s | %s | %s | %s |\n' % (
             time.strftime('%m-%d %H:%M'), k.split('_')[0], q.get('total_points'), r.get('task_id'),
             r.get('_error') or 'ok', ' '.join(os.path.relpath(f, ROOT) for f in files), SHOTS[k][:60]))
