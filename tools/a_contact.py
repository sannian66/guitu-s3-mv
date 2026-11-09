"""A 组联系表 / 关键帧表：按本组自己的镜头表（units/sec_a_intro_verse1.SHOTS）取帧。
  tools/cpu_slot.sh python3 tools/a_contact.py contact out/round4/A_contact_vN.jpg      每镜 55% 处一帧
  tools/cpu_slot.sh python3 tools/a_contact.py keys out/round4/A_keys_vN.jpg            转场中间帧 + 歌词/冲击关键帧
  python3 tools/a_contact.py times out.jpg 1.0 2.5 ...                                 指定秒"""
import os, sys, time
ROOT = '/workspace/work/mv'; sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + '/units'); sys.path.insert(0, ROOT + '/lib')
os.chdir(ROOT)
from PIL import Image, ImageDraw, ImageFont
import sec_a_intro_verse1 as M

FPS = 30
ACON = os.environ.get('ACON', '/tmp/acon')            # 第八棒：每版用独立缓存目录，part 可续跑
font = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 22)


def sheet(items, out, cols=4, tw=480, th=270):
    rows = (len(items) + cols - 1) // cols
    sh = Image.new('RGB', (cols * tw, rows * (th + 30)), (12, 12, 12)); d = ImageDraw.Draw(sh)
    cache = {}
    for i, (label, t) in enumerate(items):
        a = time.time()
        f = int(round(t * FPS))
        im = Image.fromarray(M.frame(f, cache)).resize((tw, th), Image.LANCZOS)
        x, y = (i % cols) * tw, (i // cols) * (th + 30)
        sh.paste(im, (x, y + 30)); d.text((x + 6, y + 2), f'{label}  {t:.2f}s', fill=(240, 220, 120), font=font)
        print(label, round(t, 2), round(time.time() - a, 2), 's', flush=True)
    sh.save(out, quality=86); print('saved', out)


def items_for(cmd):
    if cmd == 'contact':
        return [(S.__name__, S.t0 + 0.55 * (S.t1 - S.t0)) for S in M.SHOTS]
    if cmd == 'triple':                                   # 第七棒：每镜起/中/止三帧（节奏素材）
        out = []
        for S in M.SHOTS:
            d = S.t1 - S.t0
            out += [(S.__name__ + ' 起', S.t0 + min(0.2, d * 0.15)), (S.__name__ + ' 中', S.t0 + d * 0.5), (S.__name__ + ' 止', S.t1 - min(0.12, d * 0.1))]
        return out
    if cmd == 'keys':                                     # 第七棒 keys v6：转场中点 + 评审点名的关键帧
        items = []
        for S in M.SHOTS[1:]:
            c = M.CUTS.get(S.__name__)
            if c and c[0] != 'hard':
                items.append((S.__name__ + ' ' + c[0][:10] + ' 中点', S.t0 + (c[2] - c[1]) / 2))
        items += [('A06 crane 起', 8.00), ('A06 crane 止', 10.40), ('A07a 片名换机位', 10.90), ('A07a 片名随升镜', 13.10), ('V14 荷兰角 起', 32.62), ('V14 荷兰角 止', 34.30), ('V04 走近 起', 19.80), ('V04 走近 止', 20.52), ('V06 环绕 起', 21.25),
                  ('V06 刀身扫光', 21.40), ('V06 环绕 止', 22.40), ('V13 焦点·跪者', 30.95), ('V13 转焦中', 31.15), ('V13 焦点·鬼屠', 31.60),
                  ('A03 环绕 止', 5.80), ('A04 dolly 止', 7.25), ('V08 tilt 止', 25.10), ('V02 刀锋', 17.81), ('V16 入 主', 36.43),
                  ('V17 正 原样', 39.31), ('V19 起', 40.95), ('V19 中', 41.30), ('V19 止', 41.68), ('V20 slash_coil', 41.90),
                  ('V09入 刷碎 前', 25.24), ('V09入 刷碎 后', 25.38)]
        items += [('V12入 前', 29.80), ('V12入 后', 29.93), ('V21入 前', 42.60), ('V21入 后', 42.76),
                  ('V10 膝部·倒影', 27.98), ('V20 蓄势', 41.95), ('V20 上提', 42.05), ('V21 末段余烬', 43.80), ('Cait 竖排', 5.0),
                  ('署名', 1.6), ('署名2', 4.9), ('片名', 8.6), ('片名化灰', 13.5), ('长夜', 16.4), ('五百', 19.1), ('拦不住', 20.9),
                  ('寒光', 21.6), ('谁在高处', 23.3), ('V08', 23.80), ('V08 落印', 24.44), ('V08 俯拍印痕', 24.62), ('罪状', 24.95),
                  ('沿梁', 26.95), ('V10 铜盘', 27.9), ('称量', 28.7), ('杀', 30.3), ('放', 32.2), ('火星成字', 34.25), ('主张', 36.0),
                  ('若正义', 37.9), ('V17 落前', 38.63), ('V17 落地', 38.72), ('V17 凹坑', 38.85), ('V17 凹坑', 39.20),
                  ('那我 V18', 40.18), ('宁愿', 41.5), ('锋', 43.55), ('出口', 44.0)]
        return items
    items = []
    for S in M.SHOTS[1:]:
        c = M.CUTS.get(S.__name__)
        if c and c[0] != 'hard':
            items.append((S.__name__ + ' ' + c[0][:12] + ' mid', S.t0 + (c[2] - c[1]) / 2))
    items += [('credits', 1.6), ('credits2', 4.9), ('title', 8.6), ('title-sheen', 11.7), ('title-ash', 13.5), ('长夜', 16.4), ('五百', 19.1),
              ('拦不住', 20.9), ('寒光', 21.6), ('谁在高处', 23.3), ('罪状', 24.9), ('沿梁', 26.9), ('称量', 28.7), ('杀', 30.3), ('放', 32.2),
              ('刻刀', 34.2), ('主张', 36.0), ('若正义', 37.9), ('权势', 39.4), ('宁愿', 41.5), ('锋', 43.55), ('exit', 44.0)]
    return items


if __name__ == '__main__' and sys.argv[1] in ('part', 'assemble'):
    # 分块渲染（每次 shell ≤120s）：part <contact|keys> <i0> <i1>  → /tmp/acon/<kind>_<i>.jpg；assemble <kind> <out> [块高 rows]
    kind = sys.argv[2]; its = items_for(kind)
    if sys.argv[1] == 'part':
        os.makedirs(ACON, exist_ok=True); cache = {}
        for i in range(int(sys.argv[3]), min(len(its), int(sys.argv[4]))):
            lab, t = its[i]
            if os.path.exists(ACON + '/%s_%03d.jpg' % (kind, i)): continue
            Image.fromarray(M.frame(int(round(t * FPS)), cache)).resize((480, 270), Image.LANCZOS).save(ACON + '/%s_%03d.jpg' % (kind, i), quality=90)
            print(i, lab, flush=True)
    else:
        out = sys.argv[3]; cols, tw, th = (3 if kind == 'triple' else 4), 480, 270; per = int(sys.argv[4]) if len(sys.argv) > 4 else 4
        rows = (len(its) + cols - 1) // cols
        sh = Image.new('RGB', (cols * tw, rows * (th + 30)), (12, 12, 12)); d = ImageDraw.Draw(sh)
        for i, (lab, t) in enumerate(its):
            x, y = (i % cols) * tw, (i // cols) * (th + 30)
            sh.paste(Image.open(ACON + '/%s_%03d.jpg' % (kind, i)), (x, y + 30)); d.text((x + 6, y + 2), f'{lab}  {t:.2f}s', fill=(240, 220, 120), font=font)
        sh.save(out, quality=86)
        for b in range(0, rows, per):                     # 切块 ≤1920×1400 供查看
            sh.crop((0, b * (th + 30), cols * tw, min(rows, b + per) * (th + 30))).save(out.replace('.jpg', '_p%d.jpg' % (b // per)), quality=86)
        print('saved', out, rows)
    sys.exit(0)


if __name__ == '__main__':
    cmd, out = sys.argv[1], sys.argv[2]
    if cmd == 'contact':
        items = [(S.__name__, S.t0 + 0.55 * (S.t1 - S.t0)) for S in M.SHOTS]
    elif cmd == 'keys':
        items = []
        for S in M.SHOTS[1:]:
            c = M.CUTS.get(S.__name__)
            if c and c[0] != 'hard':
                mid = S.t0 + (c[2] - c[1]) / 2 if c[0] != 'whip' else S.t0 + 1 / FPS
                items.append((S.__name__ + ' ' + c[0][:12] + ' mid', mid))
        items += [('credits', 1.6), ('credits2', 4.6), ('title', 8.6), ('title-ash', 13.5), ('长夜', 17.6), ('五百', 19.1), ('寒光', 21.5),
                  ('罪状', 24.9), ('沿梁', 26.9), ('称量', 28.7), ('杀', 30.3), ('放', 32.2), ('刻刀', 34.2), ('主张', 36.0),
                  ('正印', 38.9), ('权势', 39.6), ('锋', 43.55), ('exit', 44.0)]
    else:
        items = [('t', float(x)) for x in sys.argv[3:]]
    sheet(items, out)
