"""副歌一人物精灵批量生图（RH_image2 4K 16:9，参考 男主_鬼屠.webp）。
用法：python3 tools/gen_c1_sprites.py <job,job,...|all> [try_idx]
候选落到 GEN_CAND（仓库外，避免 4K 大图入库），挑选后拷为 assets/gen/<镜号>/<姿势>_raw.png。日志追加 crew/genlog.md。"""
import sys, os, json, time, threading
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT + '/tools')
import nb
CAND = os.environ.get('GEN_CAND', '/workspace/projects/056c9682-39b0-4dca-a3b4-ab19434e714b/work/gen_cands')
REF = json.load(open(ROOT + '/assets/characters/asset_urls.json'))['男主_鬼屠.webp']
CHAR = ("The same young man as in the reference image: identical face and identical hairstyle. High ponytail tied on top of the head "
        "with long messy black strands, center-parted messy bangs falling over the forehead and between the eyes, amber eyes, "
        "pale lean face, sharp straight brows, sharp jawline. Costume: black layered wuxia robe, dark crimson inner collar, wide dark "
        "leather waist sash, dark leather bracers on the forearms. Weapon: long single-edged Chinese dao with a black cord-wrapped hilt; "
        "black scabbard with a red tassel. ")
BG = ("Background: plain seamless flat neutral mid-gray studio backdrop, completely empty, no objects, no ground, no rain, no smoke, "
      "no text, no watermark. Lighting: cold moonlight backlight from behind creating a thin cool rim outlining the silhouette and hair, "
      "dim cool key light from the front side, moody, cinematic realistic film still, photorealistic, high detail, sharp focus. ")
FULL = "The whole figure is fully inside the frame with generous empty margin on all sides; the top of the ponytail, both feet and the sword tip are fully visible and not cropped. "
HAND = "Anatomically correct hand with exactly five fingers, natural believable grip, realistic knuckles and skin. "
JOBS = {
 'S029/grip': "Close-up shot of his right hand tightly gripping the black cord-wrapped hilt of the dao, fist clenched hard, knuckles tense, "
              "four fingers wrapped around the hilt and the thumb locked over them, dark leather bracer on the wrist and a bit of black sleeve. "
              "The hand and hilt are in the center of the frame; the steel blade rises diagonally toward the upper right. " + HAND,
 'S030/ready': "Long shot, full body, side profile view facing right, he stands still holding the dao low at his right side with the blade pointing down, "
               "chin slightly raised looking up to the upper right, robe hem and ponytail stirred by wind. Figure occupies about 70% of the frame height. " + FULL,
 'S030/raise': "Long shot, full body, side profile view facing right, he raises the dao straight up with his right arm fully extended, the blade pointing vertically "
               "to the sky, face tilted upward, other hand relaxed, robe hem and ponytail stirred by wind. Figure including the raised blade occupies about 80% of the frame height. " + FULL,
 'S035/run': "Medium-wide shot, full body, side view, he sprints fast toward the right, body leaning forward, long stride, dao held back low in his right hand, "
             "robe and ponytail streaming behind him. Dynamic action pose. " + FULL,
 'S035/leap': "Medium-wide shot, full body, side view, he is airborne in a high leap toward the right, knees tucked, both hands holding the dao raised high above and behind his head "
              "ready to strike downward diagonally, robe and ponytail flying. Dynamic action pose. " + FULL,
 'S035/slash': "Medium-wide shot, full body, side view facing right, he lands in a deep low crouch right after a powerful diagonal downward slash, the dao swung down and extended "
               "toward the lower right, front knee bent, back leg extended, robe and ponytail still flying from the motion. Dynamic action pose. " + FULL,
 'S037/stand': "Long shot, full body seen directly from behind (back view), he stands still with feet apart, dao held low in his right hand pointing to the ground, "
               "high ponytail and robe hem blowing in the wind. " + FULL,
 'S038/eyes': "Extreme close-up of his eyes only: a horizontal band of the face from the brows to the bridge of the nose, both amber eyes staring straight ahead coldly and intensely, "
              "sharp straight brows, a few messy black bang strands falling across, pale skin. Very sharp detail on the irises.",
 'S039/walk': "Medium shot to full body, side view, he walks slowly toward the right with a heavy tired gait, head slightly lowered, dao held loosely in his right hand "
              "pointing down behind him, robe hem trailing. " + FULL,
 'S041/shoulder': "Long shot, full body seen from behind (back view, slightly three-quarter), he stands with the long dao resting horizontally across the back of his shoulders, "
                  "right hand holding the hilt, left wrist draped over the blade, high ponytail hanging between, robe hem blowing in the wind. " + FULL,
 'S044/thumb': "Close-up of the sheathed dao at his left hip: his left hand grips the black scabbard just below the guard and his thumb pushes the round sword guard forward, "
               "revealing a thin sliver of bright steel between the guard and the scabbard mouth. Black cord-wrapped hilt, red tassel hanging from the scabbard, "
               "a bit of black robe and leather sash. The hand and guard are in the center of the frame. " + HAND,
 'S044/thumb2': "Close-up, side view of the sheathed dao worn horizontally at his left hip. His left hand wraps around the top of the black scabbard and his left THUMB presses "
                "flat against the back of the round metal sword guard, pushing it forward so a thin sliver of bright polished steel shows between the guard and the scabbard mouth. "
                "The thumb is clearly visible on the guard. Black cord-wrapped hilt to the left, red tassel hanging, a bit of black robe and leather sash. Hand and guard in the center. " + HAND,
 'S045/windup': "Wide shot, full body, three-quarter view, he coils his body for a spinning slash: torso twisted away, knees bent low, the dao drawn back horizontally behind him "
                "at waist height, eyes looking over his shoulder. Dynamic action pose. " + FULL,
 'S045/spin': "Wide shot, full body, he is in the middle of a fast spinning slash, body turned with his back partly to the camera, right arm extended and the dao swung horizontally "
              "at full arm's length, robe skirt flaring outward in a circle, ponytail whipping around. Dynamic action pose. " + FULL,
 'S045/finish': "Wide shot, full body, facing the camera in a low wide stance just after a spinning slash, the dao extended horizontally out to his right side at arm's length, "
                "left hand open for balance, robe hem and ponytail settling, cold stare at the camera. Dynamic action pose. " + FULL,
 'S046/stare': "Medium close-up, head and shoulders, front three-quarter view, he looks straight into the camera with a cold calm stare, slight downward head tilt, "
               "messy bangs over the eyes, the high ponytail visible above his head and fully inside the frame, crimson inner collar visible. No sword in the frame.",
}
LOG = ROOT + '/crew/genlog.md'
lk = threading.Lock()

def prompt(job): return JOBS[job] + " " + CHAR + BG

def run(job, k):
    body = dict(model='RH_image2', prompt=prompt(job), ratio='16:9', size='4K', input=[REF])
    shot, pose = job.split('/')
    od = os.path.join(CAND, shot)
    r = nb.generate(body, None)
    res = r.get('_error') or 'completed'; files = ''
    if not r.get('_error') and r.get('result_urls'):
        ps = nb.download(r['result_urls'][:1], od, f'{pose}_try{k}')
        files = ps[0]
    with lk:
        open(LOG, 'a').write(f"| {time.strftime('%m-%d %H:%M')} | {shot} | RH_image2 | 4K 16:9 | 3 | {r.get('task_id','')} | {res} | "
                             f"gen_cands/{shot}/{os.path.basename(files) if files else ''} | c1sprite {pose} try{k}: {JOBS[job][:70]} |\n")
    print(job, k, res, files, flush=True)
    return job, k, res, files

if __name__ == '__main__':
    jobs = list(JOBS) if sys.argv[1] == 'all' else sys.argv[1].split(',')
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    q = nb.api('POST', '/api/skills/images/quote', dict(model='RH_image2', prompt=prompt(jobs[0]), ratio='16:9', size='4K', input=[REF]))[1]
    print('quote per image', q, 'x', len(jobs), flush=True)
    with ThreadPoolExecutor(int(os.environ.get('NW', '5'))) as ex:
        out = list(ex.map(lambda j: run(j, k), jobs))
    json.dump(out, open(os.path.join(CAND, f'batch_{k}_{int(time.time())}.json'), 'w'))
