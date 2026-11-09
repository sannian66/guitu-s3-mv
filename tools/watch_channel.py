#!/usr/bin/env python3
"""tools/watch_channel.py — 持续监控生图渠道，恢复后自动跑排队的 job 表

用法：
  python3 tools/watch_channel.py jobs/green_respr.json [更多 job 表 ...]
后台跑：
  nohup python3 tools/watch_channel.py jobs/green_respr.json > /tmp/channel_watch.log 2>&1 &
行为：
  每 60s 探一次 `GET /v1/models`（带 20s 超时）；连续 2 次 200 视为恢复 →
  依次跑 `tools/gen_openai.py <job表>`（该脚本自身幂等，已存在的图会跳过），然后退出并写 genlog。
  最多守 WAIT_MIN（默认 240）分钟。
"""
import os, pathlib, subprocess, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY = (os.environ.get('WENTOKEN_KEY')
       or pathlib.Path(os.path.expanduser('~/.dsh/secrets/wentoken.key')).read_text().strip())
BASE = os.environ.get('WENTOKEN_BASE', 'https://api.wentoken.si/v1')
WAIT_MIN = int(os.environ.get('WAIT_MIN', '240'))
VENV = ROOT / 'out/full_sprite/chunks/local60_149c727_20261109/venv/bin/python'


def probe():
    try:
        req = urllib.request.Request(BASE + '/models', headers={'Authorization': 'Bearer ' + KEY})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except Exception as e:
        print(f'  probe FAIL {type(e).__name__}: {str(e)[:80]}', flush=True)
        return False


def main():
    jobs = sys.argv[1:]
    if not jobs:
        raise SystemExit('用法: watch_channel.py <job表> [更多...]')
    t0 = time.time()
    ok_streak = 0
    print(f'[{time.strftime("%H:%M:%S")}] 开始监控渠道 {BASE}，排队 {len(jobs)} 个 job 表，最多守 {WAIT_MIN} 分钟', flush=True)
    while time.time() - t0 < WAIT_MIN * 60:
        if probe():
            ok_streak += 1
            print(f'[{time.strftime("%H:%M:%S")}] 探测成功（连续 {ok_streak}/2）', flush=True)
            if ok_streak >= 2:
                print('渠道恢复，开始跑排队任务', flush=True)
                for j in jobs:
                    subprocess.run([str(VENV), str(ROOT / 'tools/gen_openai.py'), j], cwd=ROOT, check=False)
                with open(ROOT / 'crew/genlog.md', 'a') as f:
                    f.write(f'\n## {time.strftime("%Y-%m-%d %H:%M")} · 渠道恢复后自动补跑：{", ".join(jobs)}\n')
                print('排队任务跑完，监控退出', flush=True)
                return
        else:
            ok_streak = 0
        time.sleep(60)
    print('等待超时，监控退出（渠道仍未恢复）', flush=True)


if __name__ == '__main__':
    main()
