#!/usr/bin/env python3
"""tools/gen_openai.py — 走 OpenAI 协议渠道（api.wentoken.si）批量生图

比对 nananobanana 的好处：支持**多参考图编辑**（`/v1/images/edits` 的 `image[]`），
所以「保持构图只改画风」「同一角色换姿势」这类需求可以直接做，不必先绿幕再合成。

job 表（JSON 数组）：
  [{"name":"xxx", "prompt":"...", "refs":["out/refs_r1/a.png","out/refs_r1/b.png"],   # 有 refs → edits，无 → generations
    "model":"gpt-image-2", "out":"assets/gen/r1", "nocut":true}]
注意：本渠道 **`size` 参数会触发 400**（返回一段聊天式道歉），所以默认不传 size。

用法：
  python3 tools/gen_openai.py jobs/x.json --dry     # 只列计划
  python3 tools/gen_openai.py jobs/x.json
"""
import base64, json, os, pathlib, subprocess, sys, time, urllib.request, uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY = pathlib.Path(os.path.expanduser('~/.dsh/secrets/wentoken.key')).read_text().strip()
BASE = os.environ.get('WENTOKEN_BASE', 'https://api.wentoken.si/v1')
MODEL = os.environ.get('GEN_MODEL', 'gpt-image-2')


def _req(path, data=None, headers=None, method=None):
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + KEY)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def gen(prompt, model=MODEL):
    body = json.dumps({'model': model, 'prompt': prompt, 'n': 1}).encode()
    return _req('/images/generations', body, {'Content-Type': 'application/json'}, 'POST')


def edit(prompt, refs, model=MODEL):
    """多参考图编辑：multipart/form-data，字段名 image[]"""
    boundary = '----wt' + uuid.uuid4().hex
    parts = []
    for k, v in (('model', model), ('prompt', prompt), ('n', '1')):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for p in refs:
        p = pathlib.Path(p)
        if not p.is_absolute():
            p = ROOT / p
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; filename="{p.name}"\r\n'
                      f'Content-Type: image/png\r\n\r\n').encode() + p.read_bytes() + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    return _req('/images/edits', b''.join(parts),
                {'Content-Type': f'multipart/form-data; boundary={boundary}'}, 'POST')


def save(resp, dst):
    """OpenAI 协议：data[0].b64_json 或 data[0].url"""
    it = (resp.get('data') or [{}])[0]
    if it.get('b64_json'):
        dst.write_bytes(base64.b64decode(it['b64_json']))
        return True
    if it.get('url'):
        urllib.request.urlretrieve(it['url'], dst)
        return True
    return False


def cut(raw, out, width=2048):
    subprocess.run([sys.executable, str(ROOT / 'tools/cutout_green.py'), str(raw), str(out), str(width)],
                   check=True, stdout=subprocess.DEVNULL)


def main():
    jobs_file = pathlib.Path(sys.argv[1])
    jobs = json.load(open(jobs_file))
    todo = [j for j in jobs if not (ROOT / j.get('out', 'assets/gen/r1') / f"{j['name']}{'.png' if j.get('nocut') else '_cut.png'}").exists()]
    print(f'待生成 {len(todo)}/{len(jobs)}（已跳过已存在）')
    if '--dry' in sys.argv:
        for j in todo:
            print('  ', j['name'], '| refs', len(j.get('refs') or []), '|', j.get('model', MODEL))
        return
    log = ['', f'## {time.strftime("%Y-%m-%d %H:%M")} · OpenAI 协议渠道批量生图（{jobs_file.name}，{len(todo)} 张）',
           f'- 渠道 `{BASE}`，模型 `{MODEL}`（多参考图走 `/images/edits`）']
    for j in todo:
        t = time.time()
        try:
            resp = edit(j['prompt'], j['refs'], j.get('model', MODEL)) if j.get('refs') else gen(j['prompt'], j.get('model', MODEL))
        except Exception as e:
            print(f"  ✗ {j['name']} {e}", flush=True)
            log.append(f"- ✗ `{j['name']}` 失败：{str(e)[:120]}")
            continue
        outdir = ROOT / j.get('out', 'assets/gen/r1')
        outdir.mkdir(parents=True, exist_ok=True)
        raw = outdir / f"{j['name']}_raw.png"
        if not save(resp, raw):
            print(f"  ✗ {j['name']} 无图返回", flush=True)
            log.append(f"- ✗ `{j['name']}` 无图返回：{json.dumps(resp)[:120]}")
            continue
        if j.get('nocut'):
            raw.replace(outdir / f"{j['name']}.png")
            p = outdir / f"{j['name']}.png"
        else:
            cut(raw, outdir / f"{j['name']}_cut.png")
            p = outdir / f"{j['name']}_cut.png"
        dt = time.time() - t
        print(f"  ✔ {j['name']} → {p.name} ({dt:.0f}s)", flush=True)
        log.append(f"- ✔ `{j['name']}`（{dt:.0f}s）→ `{p.relative_to(ROOT)}`")
    with open(ROOT / 'crew/genlog.md', 'a') as f:
        f.write('\n'.join(log) + '\n')
    print('done')


if __name__ == '__main__':
    main()
