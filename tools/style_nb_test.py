import sys, json, time, concurrent.futures as cf
sys.path.insert(0,'tools'); import nb
S='out/style_test/'
def up(p):
    for i in range(5):
        try: return nb.upload(p)
        except Exception as e: print('upload retry',e,file=sys.stderr); time.sleep(4)
    raise RuntimeError('upload failed')
style=up(S+'style_ref.jpg')
COMMON=("Use image 2 ONLY for its color palette and ink-line rendering (black, white, saturated cinnabar red; ink linework). "
 "Do NOT copy any objects or scenery from image 2 (no red sun disc, no waterfalls, no floating islands, no Japanese elements). "
 "Line style: refined Chinese guofeng manhua illustration, elegant medium-thin brush ink lines, gentle hatching, soft ink-wash shading; "
 "not Japanese shonen manga, not hard heavy outlines, not comic. Setting is ancient Tang-dynasty Chang'an. Widescreen 16:9. No text, no seals, no watermark.")
jobs={
'20.0':"Keep image 1's exact composition, camera, figure size, position and walking pose: a lone young swordsman with a high ponytail walks through heavy night rain across a wet stone-paved square holding a long sheathed dao low, a long row of lanterns behind him. Background: the massive city wall and multi-eaved gate tower of Tang Chang'an. Red sky wash behind the tower, lanterns cinnabar red, wet ground mirroring red. ",
'33.5':"Keep image 1's exact composition, face, expression and hand pose: close-up of a handsome young swordsman with messy long black hair and center-parted bangs, cold calm gaze at camera, hand drawing a long Tang dao diagonally across the lower frame. Dark eyes. Background a flat cinnabar-red wash with faint black ink silhouettes of Chang'an palace eaves and a few drifting ink specks; red inner collar. ",
'74.5':"Keep image 1's exact composition: a long straight Tang dao blade diagonally on the right; in the polished steel the reflection of a young swordsman's narrowed eye and messy bangs; one thin line of red blood runs down the blade; the left half empty negative space for lyrics, a cinnabar-red ink-wash field with subtle splatter. ",
'235.6':"Keep image 1's exact composition and scale: wide dawn shot, the sun at the horizon center, a TINY lone swordsman silhouette with ponytail and long robe on the ridge in front of it, layered ridges in the foreground. On the far horizon the faint skyline of Tang Chang'an with the city wall, gate towers and the Giant Wild Goose Pagoda. Sky a cinnabar-red ink wash glowing around the sun (a soft glow, not a flat disc), black ink ridges with white mist. Right side calm for credits. ",
}
def run(t):
    src=S+(f'before_{t}.png')
    a=up(src)
    for i in range(5):
        try:
            st,raw=nb.api('POST','/api/skills/generate',{"model":"gemini-3-pro-image-preview","prompt":jobs[t]+COMMON,"ratio":"16:9","size":"2K","input":[a,style]},timeout=60); break
        except nb.urllib.error.URLError as e:
            if 'Tunnel' not in str(e): raise
            time.sleep(4)
    d=json.loads(raw); tid=d.get('task_id') or d.get('skill_task_id')
    if not tid: return t,('submit_error',st,raw[:300])
    open(S+'nb_tasks.txt','a').write(f'{t} {tid}\n')
    for i in range(6):
        r=nb.poll_task(tid)
        if r.get('_error')=='poll_timeout' or (r.get('_error') and 'task' not in r): time.sleep(5); continue
        break
    if r.get('_error'): return t,r
    return t,nb.download(r['result_urls'],S,f'nb_{t}')
with cf.ThreadPoolExecutor(4) as ex:
    for t,r in ex.map(run,jobs): print(t,r,flush=True)
