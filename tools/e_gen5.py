"""E 组第五棒新精灵（E19 直视 CU 换脸统一）：RH_image2 4K 16:9，参考 男主_鬼屠.webp。
  python3 tools/e_gen5.py quote | submit <job> | poll <job> <task_id>
候选落 ../gen_cands/E/E_r5/；日志追加 crew/genlog.md。"""
import sys, os, time, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT + '/tools')
import nb
import e_gen as G
import e_gen3 as G3

CAND = os.path.join(G.CAND, 'E_r5')
JOBS = {
 'stare_cu': "Close-up portrait, head and upper shoulders, straight frontal view, he stares directly into the camera lens with cold calm unwavering eyes, "
             "lips closed, jaw relaxed, slim narrow jaw and pointed chin, young (about twenty years old), lean face. Center-parted messy straight bangs fall over the forehead, "
             "a few straight strands drift in the wind; the top of the high ponytail visible above the head, fully inside the frame. Crimson inner collar under the black robe. "
             "Warm golden sunrise key light from the upper right, soft rim light on hair. No sword. " + G3.ID,
}
LOG = ROOT + '/crew/genlog.md'


def body(job): return dict(model='RH_image2', prompt=JOBS[job] + ' ' + G.CHAR + G.BG, ratio='16:9', size='4K', input=[G.REF])


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'quote':
        print(nb.api('POST', '/api/skills/images/quote', body(sys.argv[2] if len(sys.argv) > 2 else 'stare_cu'))[1]); sys.exit()
    job = sys.argv[2]
    if c == 'submit':
        st, raw = nb.api('POST', '/api/skills/generate', body(job), timeout=60)
        d = json.loads(raw); tid = d.get('task_id') or d.get('skill_task_id') or (d.get('task') or {}).get('id')
        open(LOG, 'a').write(f"| {time.strftime('%m-%d %H:%M')} | E组/E_r5/{job} | RH_image2 | 4K 16:9 | 3 | {tid} | submitted | - | [E组] 第五棒 E19 统一脸 |\n")
        print(st, tid, raw[:300])
    elif c == 'poll':
        r = nb.poll_task(sys.argv[3], total=100)
        files = nb.download(r['result_urls'][:1], CAND, job)[0] if r.get('result_urls') else None
        if files:
            open(LOG, 'a').write(f"| {time.strftime('%m-%d %H:%M')} | E组/E_r5/{job} | RH_image2 | 4K 16:9 | 0 | {sys.argv[3]} | completed | {files} | [E组] 第五棒 候选 |\n")
        print(json.dumps({k: v for k, v in r.items() if k != 'raw'}, ensure_ascii=False)[:500], files)
