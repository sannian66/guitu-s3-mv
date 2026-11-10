"""V04（20s 雨夜长街）Nano Banana Pro 分层样片：背景空景 + 人物绿幕。先报价，先记 task_id 再轮询。"""
import sys, json, time, concurrent.futures as cf
sys.path.insert(0,'tools'); import nb
O='assets/gen/NB/V04/'; M='gemini-3-pro-image-preview'
def up(p):
    for i in range(5):
        try: return nb.upload(p)
        except Exception as e: print('upload retry',e,file=sys.stderr); time.sleep(4)
    raise RuntimeError(p)
STY=("Same art style as image 1 exactly: refined Chinese guofeng ink illustration, elegant thin brush ink lines, soft ink-wash shading, "
     "palette only black, white and saturated cinnabar red. No text, no seals, no watermark.")
jobs={
 'bg': (['out/style_test/nb_20.0_0.jpg'],
   "Recreate image 1 as an EMPTY background plate with NO person in it: the same Tang Chang'an city wall and multi-eaved gate tower at night in heavy rain, "
   "red sky wash, wet stone-paved square mirroring red. Lanterns: only about 10 lanterns spaced sparsely along the wall foot, not a dense row. "
   "Leave the right-center foreground clear (a walking figure will be composited there). Slightly wider framing than image 1. 16:9. "+STY),
 'walk': (['assets/gen/S010/walk_raw.png'],
   "Redraw the person from image 1 with the same walking pose, same angle and same costume (young swordsman, high ponytail, long dark robe, long sheathed dao held low), "
   "full body from head to feet, nothing cropped, redrawn as a refined Chinese guofeng ink illustration: elegant thin black brush ink lines, soft grey ink-wash shading, black-and-white robe with a cinnabar-red inner collar, wet from rain. Exactly ONE person. Do not draw any city wall, lanterns, rain, sky or scenery. "
   "Place him alone on a perfectly flat, uniform pure green chroma-key background (#00FF00), no shadow, no ground, no rain on the background, no other objects. 16:9. "
   "No text, no watermark."),
}
def run(k):
    refs,prompt=jobs[k]; urls=[up(p) for p in refs]
    body={"model":M,"prompt":prompt,"ratio":"16:9","size":"2K","input":urls}
    st,raw=nb.api('POST','/api/skills/images/quote',body,timeout=60); print(k,'quote',raw[:120],file=sys.stderr)
    for i in range(5):
        try: st,raw=nb.api('POST','/api/skills/generate',body,timeout=60); break
        except Exception as e: print('submit retry',e,file=sys.stderr); time.sleep(4)
    d=json.loads(raw); tid=d.get('task_id') or d.get('skill_task_id')
    if not tid: return k,('submit_error',st,raw[:300])
    open(O+'tasks.txt','a').write(f'{k} {tid}\n')
    for i in range(6):
        try: r=nb.poll_task(tid)
        except Exception as e: print('poll retry',e,file=sys.stderr); time.sleep(5); continue
        if r.get('_error') and 'task' not in r: time.sleep(5); continue
        break
    if r.get('_error'): return k,r
    return k,nb.download(r['result_urls'],O,k)
sel=sys.argv[1].split(',') if len(sys.argv)>1 else list(jobs)
with cf.ThreadPoolExecutor(2) as ex:
    for k,r in ex.map(run,sel): print(k,r,flush=True)
