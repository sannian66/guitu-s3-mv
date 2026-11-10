"""D 组联系表 / 关键帧表：按本组自己的镜头表（units/sec_d_bridge.SHOTS / CUTS）取帧。
  tools/cpu_slot.sh python3 tools/d_contact.py contact out/round4/D_contact_vN.jpg [i0 i1]   每镜中点一帧（可分块：镜号区间）
  tools/cpu_slot.sh python3 tools/d_contact.py keys out/round4/D_keys_vN.jpg [i0 i1]       转场中间帧 + 歌词/冲击关键帧
  python3 tools/d_contact.py times out.jpg 1.0 2.5 ...                                      指定秒
  分块渲染时每帧缓存到 /tmp/d/cache/<f>.png，最后一块自动拼表（缓存命中就不重渲）。"""
import os, sys, time, traceback
ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv'); sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + '/units'); sys.path.insert(0, ROOT + '/lib')
os.chdir(ROOT)
os.environ.setdefault('V4_FORCE', 'd_bridge')
from PIL import Image, ImageDraw, ImageFont
import sec_d_bridge as M

FPS = 30
CACHE = '/tmp/d/cache'
os.makedirs(CACHE, exist_ok=True)
font = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 22)


def contact_items():
    return [(S.__name__, S.t0 + 0.55 * (S.t1 - S.t0)) for S in M.SHOTS]


def key_items():
    items = []
    for S in M.SHOTS[1:]:
        c = M.CUTS.get(S.__name__)
        if c and c[0] != 'hard':
            pre, post = c[1], c[2]
            items.append((S.__name__[:3] + '←' + c[0][:11], S.t0 + (post - pre) / 2))
    # 歌词 / 冲击关键帧
    items += [('入口4839', 4839 / 30 + 0.01), ('碑「叫」', 163.75), ('忍落定', 166.75), ('忍碎', 167.2), ('天平句', 168.2), ('当印落', 170.5), ('当印停', 170.85),
              ('罪状斩', 174.35), ('陪葬', 177.7), ('从今往后', 179.1), ('刀', 179.9), ('主张', 181.75), ('规矩门', 182.7), ('我拼合', 183.15), ('我刀刻', 186.85), ('闯碎', 184.35),
              ('天', 185.3), ('判落刀尖', 186.05), ('木牌斩断', 183.12), ('刀刻', 189.1), ('答发声', 189.7), ('天平断', 187.8), ('判炸屏', 188.0), ('黑场', 188.3), ('刀不答', 189.6), ('定格残影', 189.85),
              ('来裂出', 191.35), ('答', 192.3), ('出口5796', 5796 / 30),
              ('r8牲入画', 165.47), ('r8陪葬火轮廓', 177.9), ('r8S20冲刺', 182.1), ('r8S22冷蓝', 184.0), ('r8墨压切点', 171.83), ('r8木牌扫切点', 182.81)]
    return items


def render(t):
    f = int(round(t * FPS))
    p = f'{CACHE}/{f}.png'
    if os.path.exists(p) and os.path.getmtime(p) > os.path.getmtime(ROOT + '/units/sec_d_bridge.py') \
            and os.path.getmtime(p) > os.path.getmtime(ROOT + '/units/d_kit.py'):
        return Image.open(p), 0.0
    a = time.time()
    im = Image.fromarray(M.frame(f, {}))
    im.save(p)
    return im, time.time() - a


def sheet(items, out, cols=5, tw=384, th=216, rng=None):
    todo = range(len(items)) if rng is None else range(rng[0], min(rng[1], len(items)))
    for i in todo:
        label, t = items[i]
        try:
            _, dt = render(t)
            print(label, round(t, 2), round(dt, 2), 's', flush=True)
        except Exception:
            print('ERR', label, round(t, 2)); traceback.print_exc()
    if rng is not None and rng[1] < len(items): return
    rows = (len(items) + cols - 1) // cols
    sh = Image.new('RGB', (cols * tw, rows * (th + 28)), (12, 12, 12)); d = ImageDraw.Draw(sh)
    for i, (label, t) in enumerate(items):
        p = f'{CACHE}/{int(round(t * FPS))}.png'
        x, y = (i % cols) * tw, (i // cols) * (th + 28)
        if os.path.exists(p):
            sh.paste(Image.open(p).resize((tw, th), Image.LANCZOS), (x, y + 28))
        d.text((x + 6, y + 2), f'{label}  {t:.2f}s', fill=(240, 220, 120), font=font)
    sh.save(out, quality=84); print('saved', out, os.path.getsize(out) // 1024, 'KB')


if __name__ == '__main__':
    cmd, out = sys.argv[1], sys.argv[2]
    rng = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 and cmd in ('contact', 'keys') else None
    if cmd == 'contact': sheet(contact_items(), out, rng=rng)
    elif cmd == 'keys': sheet(key_items(), out, rng=rng)
    else: sheet([('t', float(x)) for x in sys.argv[3:]], out, cols=min(4, len(sys.argv) - 3), tw=960, th=540)
