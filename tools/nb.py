"""Nano Banana Skills API 小客户端（规则见 skills/nano-banana-skill/SKILL.md）。
Key：环境变量 NANO_BANANA_KEY，或仓库根目录 .env.local（已 gitignore）；都没有时不带 Authorization（Hark 沙箱由代理注入）。
用法：
  python3 tools/nb.py models
  python3 tools/nb.py quote  '{"model":"RH_image2","prompt":"...","ratio":"16:9","size":"4K"}'
  python3 tools/nb.py upload path/to/img.png            -> 打印 asset_url
  python3 tools/nb.py gen    '{"model":"RH_image2","prompt":"...","size":"4K","input":["<asset_url>"]}' [out_dir]
  python3 tools/nb.py poll   <task_id> [out_dir]
"""
import json, os, sys, time, mimetypes, urllib.request, urllib.error

BASE = 'https://www.nananobanana.cn'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACTIVE = {'pending', 'queued', 'submitted', 'processing', 'running', 'settling'}
FAILED = {'failed', 'cancelled', 'canceled', 'timeout', 'error', 'expired'}


def _key():
    k = os.environ.get('NANO_BANANA_KEY')
    if not k and os.path.exists(os.path.join(ROOT, '.env.local')):
        for l in open(os.path.join(ROOT, '.env.local')):
            if l.startswith('NANO_BANANA_KEY='): k = l.split('=', 1)[1].strip()
    return k


def api(method, path, body=None, timeout=30, tries=6):
    """5xx / 非 JSON 网关页自动重试（nananobanana 偶发 502）"""
    for i in range(tries):
        st, raw = _api1(method, path, body, timeout)
        if st < 500 and raw[:1] in '{[': return st, raw
        if method == 'POST' and path.endswith('/generate') and st < 500: return st, raw
        time.sleep(3 + 3 * i)
    return st, raw


def _api1(method, path, body=None, timeout=30):
    assert path.startswith('/api/skills/'), '只允许 /api/skills/*'
    h = {'Content-Type': 'application/json'}
    k = _key()
    if k: h['Authorization'] = 'Bearer ' + k
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode('utf-8', 'replace')
            return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')


def upload(path, media_type=None):
    ct = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    mt = media_type or ct.split('/')[0]
    st, raw = api('POST', '/api/skills/uploads/presign',
                  dict(filename=os.path.basename(path), content_type=ct, size=os.path.getsize(path), media_type=mt))
    d = json.loads(raw)
    if st // 100 != 2 or not d.get('success', True): raise RuntimeError('presign failed %s %s' % (st, raw[:500]))
    up = d['upload']
    req = urllib.request.Request(up['upload_url'], data=open(path, 'rb').read(), headers=up.get('headers') or {'Content-Type': ct}, method='PUT')
    with urllib.request.urlopen(req, timeout=120) as r:
        if r.status // 100 != 2: raise RuntimeError('PUT failed %s' % r.status)
    return up['asset_url']


def poll_task(task_id, total=600, step=5, per=30):
    t0 = time.time(); unk = 0
    while True:
        left = total - (time.time() - t0)
        if left <= 0: return {'_error': 'poll_timeout', 'task_id': task_id}
        n = int(time.time() - t0)
        try:
            st, raw = api('GET', '/api/skills/tasks/%s' % task_id, timeout=min(per, max(1, left)))
        except Exception as e:
            print('t=%ds status=_error' % n, file=sys.stderr); return {'_error': 'request_error', 'task_id': task_id, 'detail': str(e)}
        if st // 100 != 2:
            print('t=%ds status=_error' % n, file=sys.stderr); return {'_error': 'http_%d' % st, 'task_id': task_id, 'response': raw[:1000]}
        try:
            d = json.loads(raw)
        except Exception:
            d = None
        if d is not None and d.get('success') is False:
            print('t=%ds status=_error' % n, file=sys.stderr); return {'_error': 'success_false', 'task_id': task_id, 'response': raw[:1000]}
        task = (d or {}).get('task') or {}
        s = task.get('status') if isinstance(task, dict) else None
        s = s.lower() if isinstance(s, str) else None
        if s == 'completed':
            print('t=%ds status=completed' % n, file=sys.stderr); return task
        if s in FAILED:
            print('t=%ds status=%s' % (n, s), file=sys.stderr); return {'_error': s, 'task_id': task_id, 'task': task}
        if s in ACTIVE:
            unk = 0; print('t=%ds status=%s' % (n, s), file=sys.stderr)
        else:
            unk += 1; print('t=%ds status=unknown' % n, file=sys.stderr)
            if unk >= 3: return {'_error': 'unrecognized_task_status', 'task_id': task_id, 'response': raw[:1000]}
        time.sleep(min(step, max(0, total - (time.time() - t0))))


def download(urls, out_dir, stem):
    os.makedirs(out_dir, exist_ok=True); paths = []
    for i, u in enumerate(urls):
        ext = os.path.splitext(u.split('?')[0])[1] or '.png'
        p = os.path.join(out_dir, '%s_%d%s' % (stem, i, ext))
        import subprocess
        for _ in range(5):  # CDN 偶发 SSL EOF / 502，curl 重试
            if subprocess.run(['curl', '-sSf', '--retry', '3', '-o', p, u]).returncode == 0: break
        paths.append(p)
    return paths


def generate(body, out_dir=None):
    st, raw = api('POST', '/api/skills/generate', body, timeout=60)
    d = json.loads(raw)
    tid = d.get('task_id') or d.get('skill_task_id') or (d.get('task') or {}).get('id')
    if st // 100 != 2 or not tid: return {'_error': 'submit_failed', 'http': st, 'response': raw[:1000]}
    print('task_id=%s' % tid, file=sys.stderr)
    r = poll_task(tid)
    if out_dir and not r.get('_error') and r.get('result_urls'):
        r['files'] = download(r['result_urls'], out_dir, tid)
    r.setdefault('task_id', tid)
    return r


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'models': print(api('GET', '/api/skills/models')[1])
    elif cmd == 'quote': print(api('POST', '/api/skills/images/quote', json.loads(sys.argv[2]))[1])
    elif cmd == 'upload': print(upload(sys.argv[2]))
    elif cmd == 'gen': print(json.dumps(generate(json.loads(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None), ensure_ascii=False))
    elif cmd == 'poll':
        r = poll_task(sys.argv[2])
        if len(sys.argv) > 3 and r.get('result_urls'): r['files'] = download(r['result_urls'], sys.argv[3], sys.argv[2])
        print(json.dumps(r, ensure_ascii=False))
