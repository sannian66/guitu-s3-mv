"""E 组第三棒新精灵：RH_image2 4K 16:9，参考 男主_鬼屠.webp。复用 tools/e_gen.py 的角色/背景描述。
  python3 tools/e_gen3.py quote
  python3 tools/e_gen3.py <job,job|all> [try]
候选落 ../gen_cands/E/E_r3/；挑选后 tools/e_recut.py 抠到 assets/gen/E_r3/<姿势>_raw.png / _cut.png。日志追加 crew/genlog.md。"""
import sys, os, time, threading
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT + '/tools')
import nb
import e_gen as G

CAND = os.path.join(G.CAND, 'E_r3')
ID = ("East Asian young man with straight (not curly, not wavy) jet-black hair, exactly the same face as the reference: "
      "narrow sharp amber eyes, straight dark brows, pale lean face, slim straight nose, thin lips. ")
JOBS = {
 'profile_up': "Close-up, head and shoulders, pure side profile view facing right, chin slightly raised, he looks up toward the upper right with calm cold resolve. "
               "Center-parted messy straight bangs fall over the forehead, a few straight strands lifted by wind; the high ponytail is tied on top of the head and hangs behind, fully inside the frame. "
               "Crimson inner collar under the black robe. No sword. " + ID,
 'low_raise': "Extreme low-angle worm's-eye view looking steeply up at him from near his feet: he stands tall and raises the dao straight up toward the sky with his right arm fully extended above his head, "
              "blade pointing straight up, his face visible in three-quarter view looking up along the blade, robe hem and red sash cloth blowing. Strong perspective: legs large near the camera, "
              "head and blade small and far. The whole figure including the blade tip fully inside the frame. " + ID,
 'low_stride': "Extreme low-angle worm's-eye view from ground level: he strides straight toward and over the camera, one boot stepping close to the lens and large in the foreground, "
               "dao held low in his right hand with the tip trailing near the ground, he looks down into the camera with cold calm eyes, robe hem and red sash cloth blown back. "
               "Strong perspective, the whole figure inside the frame including the top of the ponytail. " + ID,
 'still_gaze': "Medium shot from the waist up, three-quarter front view: he stands still right after a cut, the dao lowered at his right side, head slightly lowered, eyes raised looking straight "
               "into the camera from under the messy bangs, calm and cold, a few strands of hair and the robe collar stirred by wind. Head, ponytail top and shoulders fully inside the frame. " + ID,
 'strike_low': "Low-angle medium-wide shot from slightly below: at the peak of a huge horizontal slash, both hands on the hilt, the dao sweeping horizontally across the frame toward the camera, "
               "the blade near the camera large and slightly motion-blurred, torso twisted, fierce eyes on the target, ponytail and robe whipping from the motion. Dynamic action pose. "
               "Head, ponytail top and the whole blade inside the frame. " + ID,
}
LOG = ROOT + '/crew/genlog.md'
lk = threading.Lock()


def body(job): return dict(model='RH_image2', prompt=JOBS[job] + ' ' + G.CHAR + G.BG, ratio='16:9', size='4K', input=[G.REF])


def run(job, k):
    r = nb.generate(body(job), None)
    res = r.get('_error') or 'completed'; files = ''
    if not r.get('_error') and r.get('result_urls'):
        files = nb.download(r['result_urls'][:1], CAND, f'{job}_try{k}')[0]
    with lk:
        open(LOG, 'a').write(f"| {time.strftime('%m-%d %H:%M')} | E组/E_r3/{job} | RH_image2 | 4K 16:9 | 3 | {r.get('task_id','')} | {res} | "
                             f"gen_cands/E/E_r3/{os.path.basename(files) if files else '-'} | [E组] 第三棒 {job} try{k} |\n")
    print(job, k, res, files, flush=True)
    return job, k, res, files


if __name__ == '__main__':
    if sys.argv[1] == 'quote':
        j = next(iter(JOBS)); print(j, nb.api('POST', '/api/skills/images/quote', body(j))[1]); sys.exit()
    jobs = list(JOBS) if sys.argv[1] == 'all' else sys.argv[1].split(',')
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    os.makedirs(CAND, exist_ok=True)
    with ThreadPoolExecutor(5) as ex: list(ex.map(lambda j: run(j, k), jobs))
