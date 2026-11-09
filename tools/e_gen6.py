"""E 组第六棒新精灵：RH_image2 4K 16:9。
  python3 tools/e_gen6.py quote <job> | run <job,job> [try]
emperor_cu 参考 = 太上皇设定图 + E07 所用 S116/emperor 的脸部裁切（同一身份）；其余参考 男主_鬼屠.webp。
候选落仓库外 ../gen_cands/E/E_r6/；日志追加 crew/genlog.md。"""
import sys, os, time, json, threading
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT + '/tools')
import nb
import e_gen as G
import e_gen3 as G3

CAND = os.path.join(G.CAND, 'E_r6')
UP = os.path.join(CAND, 'uploads.json')
GRAYBG = ("Background: plain seamless flat neutral mid-gray studio backdrop, completely empty, no objects, no ground, no smoke, no sun, no text, no watermark. "
          "Cinematic realistic film still, photorealistic, high detail, sharp focus. ")
JOBS = {
 'emperor_cu': ("Tight close-up portrait, head and top of the shoulders, straight frontal view, of the SAME old East Asian (Chinese) emperor as in both reference images: "
                "identical gaunt East Asian face with high cheekbones, deep nasolabial lines, narrow dark eyes with heavy lower lids, thin downturned lips, sunken cheeks, pale wrinkled skin; "
                "grey-white hair pulled into a tight topknot on the crown held by a long dark hairpin, long grey-white strands hanging down both sides of the face. "
                "He looks down at the camera with cold arrogant contempt, chin slightly raised. Dark layered imperial robe collar. NOT Western, NOT blond, no beard. "
                "Lighting: warm orange key light from the upper right, deep shadow on the left side of the face, a faint cool rim on the left edge. "
                "The whole head including the topknot and hairpin fully inside the frame with margin. " + GRAYBG),
 'shoulder_low': ("Extreme low-angle shot from near the ground, front three-quarter view, from the knees up: he stands tall and still with the long dao resting on his right shoulder, "
                  "the blade lying back over the shoulder and pointing behind him, his right fist gripping the black cord-wrapped hilt just in front of the shoulder, "
                  "left arm hanging relaxed, chin lowered, eyes looking down into the camera with cold calm resolve. Robe hem and red sash cloth stirred by wind. "
                  "Head, the top of the ponytail and the whole blade including the tip fully inside the frame. " + G3.ID + G.CHAR + G.BG),
 'blade_vert': ("Studio product shot of a single long single-edged Chinese dao (the same sword as in the reference image) standing perfectly vertical, tip pointing straight up, "
                "nobody holding it. The whole sword from pommel to tip is inside the frame, centered: black cord-wrapped hilt, round dark iron guard, long polished steel blade "
                "with subtle folded-steel grain, a bright narrow edge bevel and a darker spine, a small red tassel hanging from the pommel. Flat side of the blade facing the camera. "
                "Soft warm rim light along the edge. " + GRAYBG),
 'scabbard_tassel': ("Close-up still life: a black lacquered dao scabbard with worn dark metal fittings lying diagonally across the frame from lower left to upper right, "
                     "a long crimson silk tassel with a knot hanging from the scabbard ring and swaying, nobody in the frame, the scabbard fully inside the frame at both ends. "
                     "Warm low golden morning side light from the right raking across the lacquer, catching scratches and dust. " + GRAYBG),
}
LOG = ROOT + '/crew/genlog.md'
lk = threading.Lock()


def inputs(job):
    if job == 'emperor_cu':
        u = json.load(open(UP)) if os.path.exists(UP) else {}
        if 's116_face' not in u:
            os.makedirs(CAND, exist_ok=True)
            u['s116_face'] = nb.upload('/tmp/s116_face.png'); json.dump(u, open(UP, 'w'))
        return [G.REF_EMP, u['s116_face']]
    return [G.REF]


def body(job): return dict(model='RH_image2', prompt=JOBS[job], ratio='16:9', size='4K', input=inputs(job))


def run(job, k):
    r = nb.generate(body(job), None)
    res = r.get('_error') or 'completed'; files = ''
    if not r.get('_error') and r.get('result_urls'):
        files = nb.download(r['result_urls'][:1], CAND, f'{job}_try{k}')[0]
    with lk:
        open(LOG, 'a').write(f"| {time.strftime('%m-%d %H:%M')} | E组/E_r6/{job} | RH_image2 | 4K 16:9 | 3 | {r.get('task_id','')} | {res} | "
                             f"gen_cands/E/E_r6/{os.path.basename(files) if files else '-'} | [E组] 第六棒 {job} try{k} |\n")
    print(job, k, res, files, json.dumps(r, ensure_ascii=False)[:300] if r.get('_error') else '', flush=True)


if __name__ == '__main__':
    if sys.argv[1] == 'quote':
        print(nb.api('POST', '/api/skills/images/quote', body(sys.argv[2]))[1]); sys.exit()
    jobs = sys.argv[2].split(',')
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    os.makedirs(CAND, exist_ok=True)
    with ThreadPoolExecutor(5) as ex: list(ex.map(lambda j: run(*j) if isinstance(j, tuple) else run(j, k), jobs))
