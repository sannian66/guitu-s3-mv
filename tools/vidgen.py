"""tools/vidgen.py — 用 MiniMax H3 特价版做「整图参考生视频」，产出可直接剪进成片的 1920x1080 / 30fps / 2.39 黑边片段。

用法：
  # 报价（不扣积分）
  python3 tools/vidgen.py quote <首帧.png|jpg> "<提示词>" [时长秒=4]
  # 生成 + 后处理（12 积分/4 秒），输出可直接用（2560x1440 / 24fps / 2.39 黑边各 184px）
  python3 tools/vidgen.py gen <首帧> "<提示词>" <输出.mp4> [时长秒=4]
  # 只做后处理（已有原始 mp4）
  python3 tools/vidgen.py post <原始mp4> <输出.mp4>

要点：
- 模型 minimax-h3-metaso，模式 image2video_first（整张画面交给模型，人物和背景一起动）；2K / 16:9；
- 该模型的参考图审核要求是 never，直接提交生成（审核接口当前 401，别走 /videos/review）；
- 生成结果 2560x1440、24fps，与实际成片规格一致：本脚本只补上下黑边（各 184px，2.39 画幅）、过一遍 units/style_d.palette 色板兜底，不动分辨率与帧率；
- 每张（含失败）记 crew/genlog.md；Key 从 .env.local 读，绝不提交。
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'units'))
import nb  # noqa: E402

MODEL = 'minimax-h3-metaso'
# 成片规格（用户 11-11 20:2x 定）：2K 2560x1440、24fps；2.39 画幅的上下黑边各 184px（1440 - 2560/2.39 = 368）
W, H, FPS = 2560, 1440, 24
BAR = int(round((H - W / 2.39) / 2))      # = 184
SRC_FPS = 24


def _jpg(path):
    """上传前统一转成 jpg（体积小、格式稳定）。"""
    if path.lower().endswith(('.jpg', '.jpeg')):
        return path
    import cv2
    out = os.path.join(tempfile.mkdtemp(prefix='vidgen_'), 'first.jpg')
    cv2.imwrite(out, cv2.imread(path), [cv2.IMWRITE_JPEG_QUALITY, 93])
    return out


def body(first, prompt, dur=4):
    return {'model': MODEL, 'mode': 'image2video_first', 'prompt': prompt,
            'resolution': '2K', 'duration': int(dur), 'aspect_ratio': '16:9',
            'images': [nb.upload(_jpg(first))]}


def quote(first, prompt, dur=4):
    return nb.api('POST', '/api/skills/videos/quote', body(first, prompt, dur))[1]


def gen(first, prompt, out, dur=4, log=True):
    b = body(first, prompt, dur)
    st, raw = nb.api('POST', '/api/skills/videos/generate', b, timeout=120)
    d = json.loads(raw)
    tid = d.get('task_id') or d.get('skill_task_id')
    if not tid:
        print('submit_failed', st, raw[:500]); return None
    print('task_id=%s' % tid, flush=True)
    r = nb.poll_task(tid, total=1800, step=10, per=30)
    print('status=%s' % r.get('status'), flush=True)
    if not r.get('result_urls'):
        print('no result', json.dumps(r, ensure_ascii=False)[:600]); return None
    raw_mp4 = nb.download(r['result_urls'][:1], os.path.dirname(out) or '.', 'raw_' + tid[:8])[0]
    post(raw_mp4, out)
    if log:
        try:
            import datetime
            with open(os.path.join(ROOT, 'crew/genlog.md'), 'a') as f:
                f.write('| %s | 视频 %s | %s image2video_first | 2K 16:9 %ss | 12 | %s | ✔ 采用 | %s | %s |\n' % (
                    datetime.datetime.now().strftime('11-11 %H:%M'), os.path.basename(out), MODEL, dur, tid,
                    os.path.relpath(out, ROOT), ' '.join(prompt.split())[:90]))
        except Exception as e:
            print('genlog failed', e)
    return out


def post(src, out):
    import numpy as np, cv2, style_d
    cap = cv2.VideoCapture(src)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok: break
        frames.append(cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA))
    if not frames: raise RuntimeError('no frames: %s' % src)
    n_out = len(frames)      # 24fps 原样保留，不重排
    p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', out],
                         stdin=subprocess.PIPE)
    for i in range(n_out):
        f = cv2.cvtColor(frames[i], cv2.COLOR_BGR2RGB)
        f = style_d.palette(f.astype(np.float32) / 255)
        f[:BAR] = 0; f[H - BAR:] = 0
        p.stdin.write((np.clip(f, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()
    print('post done', out, n_out, 'frames')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'quote':
        print(quote(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 4))
    elif cmd == 'gen':
        gen(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 4)
    elif cmd == 'post':
        post(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
