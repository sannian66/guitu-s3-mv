"""A 组第六棒联系表（分块、可续跑：已渲染的帧跳过）。必须用 tools/cpu_slot.sh 包一层。
  tools/cpu_slot.sh python3 units/a_contact6.py part <contact|keys|triple> <i0> <i1>   → /tmp/acon6/<kind>_<i>.jpg
  python3 units/a_contact6.py assemble <kind> <out.jpg> [每块行数]                        → 整图 + _p<n>.jpg 分块（≤1920×1400）"""
import os, sys, time
ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv'); sys.path[:0] = [ROOT, ROOT + '/units', ROOT + '/lib']
os.chdir(ROOT)
from PIL import Image, ImageDraw, ImageFont
FPS = 30
TMP = '/tmp/acon6'


def items_for(kind, M):
    if kind == 'contact':
        return [(S.__name__, S.t0 + 0.55 * (S.t1 - S.t0)) for S in M.SHOTS]
    if kind == 'triple':                                  # 每镜起/中/止三帧（核节奏、镜内运动）
        out = []
        for S in M.SHOTS:
            d = S.t1 - S.t0
            out += [(S.__name__ + ' 起', S.t0 + min(0.2, d * 0.15)), (S.__name__ + ' 中', S.t0 + d * 0.5), (S.__name__ + ' 止', S.t1 - min(0.12, d * 0.1))]
        return out
    items = []
    for S in M.SHOTS[1:]:
        c = M.CUTS.get(S.__name__)
        if c and c[0] != 'hard':
            items.append((S.__name__ + ' ' + c[0][:12] + ' 中点', S.t0 + (c[2] - c[1]) / 2))
    items += [('署名', 1.6), ('署名2', 4.9), ('片名', 8.6), ('A07a 片名', 11.5), ('A07a 闪电', 12.9), ('片名化灰', 13.5),
              ('长夜', 16.4), ('五百', 19.1), ('拦不住', 20.9), ('寒光', 21.6), ('谁在高处', 23.3),
              ('V08 落印前', 24.37), ('V08 落印前', 24.40), ('V08 落印', 24.44), ('V08 落印后', 24.50), ('V08 俯拍印痕', 24.62), ('罪状', 24.95),
              ('V09 中', 26.2), ('沿梁', 26.95), ('称量', 28.7), ('杀', 30.3), ('放', 32.2), ('火星成字', 34.25), ('我的', 35.1), ('主张', 36.0),
              ('若正义', 37.9), ('V17 落前', 38.63), ('V17 落前', 38.67), ('V17 落地', 38.72), ('V17 印坑', 38.85), ('权势', 39.3),
              ('那我', 40.4), ('宁愿', 41.5), ('锋', 43.55), ('出口', 44.0)]
    return items


if __name__ == '__main__':
    cmd, kind = sys.argv[1], sys.argv[2]
    if cmd == 'part':
        import sec_a_intro_verse1 as M
        its = items_for(kind, M)
        os.makedirs(TMP, exist_ok=True); cache = {}
        for i in range(int(sys.argv[3]), min(len(its), int(sys.argv[4]))):
            fn = '%s/%s_%03d.jpg' % (TMP, kind, i)
            if os.path.exists(fn): continue
            lab, t = its[i]; a = time.time()
            Image.fromarray(M.frame(int(round(t * FPS)), cache)).resize((480, 270), Image.LANCZOS).save(fn, quality=90)
            print(i, lab, round(time.time() - a, 1), flush=True)
        print('n', len(its))
    elif cmd == 'assemble':
        import sec_a_intro_verse1 as M
        its = items_for(kind, M)
        out = sys.argv[3]; per = int(sys.argv[4]) if len(sys.argv) > 4 else 4
        font = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC-Bold.otf', 22)
        cols, tw, th = 4, 480, 270
        rows = (len(its) + cols - 1) // cols
        sh = Image.new('RGB', (cols * tw, rows * (th + 30)), (12, 12, 12)); d = ImageDraw.Draw(sh)
        for i, (lab, t) in enumerate(its):
            x, y = (i % cols) * tw, (i // cols) * (th + 30)
            sh.paste(Image.open('%s/%s_%03d.jpg' % (TMP, kind, i)), (x, y + 30)); d.text((x + 6, y + 2), f'{lab}  {t:.2f}s', fill=(240, 220, 120), font=font)
        sh.save(out, quality=86)
        for b in range(0, rows, per):
            sh.crop((0, b * (th + 30), cols * tw, min(rows, b + per) * (th + 30))).save(out.replace('.jpg', '_p%d.jpg' % (b // per)), quality=86)
        print('saved', out, rows, 'rows', (rows + per - 1) // per, 'parts')
