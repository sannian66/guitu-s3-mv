"""tools/e_contact.py — E 组联系表 / 关键帧表（按 units/sec_e_final_outro.py 自己的 SHOTS/CUTS 表取帧，不用 sec_contact.py）。
用法：
  tools/cpu_slot.sh python3 tools/e_contact.py contact out/round4/E_contact_v1.jpg     # 每镜中点帧
  tools/cpu_slot.sh python3 tools/e_contact.py keys    out/round4/E_keys_v1.jpg        # 转场中间帧 + 歌词关键帧
  python3 tools/e_contact.py list                                                     # 打印帧号不渲染"""
import sys, os, time
ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv')
sys.path.insert(0, ROOT + '/units'); sys.path.insert(0, ROOT)
os.environ.setdefault('V4_FORCE', 'e_final_outro')
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sec_e_final_outro as S

FONT = ROOT + '/fonts/NotoSerifSC-Regular.otf'


def contact_frames():
    out = []
    for k, (cls, f0, sid, scale) in enumerate(S.SHOTS):
        f1 = S.BOUNDS[k + 1]
        out.append(((f0 + f1) // 2, '%s %s %s  %.2fs  f%d' % (S.IDS[k], sid, scale, (f1 - f0) / 30, (f0 + f1) // 2)))
    return out


def key_frames():
    out = []
    for k in range(1, len(S.SHOTS)):
        name, pre, post, kw = S.CUTS.get(S.IDS[k], ('hard', 0, 0, {}))
        c = S.BOUNDS[k]
        if name in ('hard', 'cut'):
            f = c                                      # 硬切冲击帧
        else:
            f = int(round(c + (post - pre) / 2 * 30)) if pre > 0 else int(round(c + post * 0.5 * 30))
        out.append((f, 'cut→%s %s f%d' % (S.IDS[k], name, f)))
    lyr = [(S.CT(48, 0) + 0.15, '血 烧出'), (S.CT(48, 5) + 0.2, '刀不放 盖印'), (S.CT(49, 11) + 0.15, '彰 裂匾'),
           (S.CT(50, 6) + 0.6, '伪装 烧穿'), (S.CT(51, 3) + 0.12, '碎 字被斩开'), (S.CT(51, 9) + 0.45, '鬼屠 印地'),
           (S.CT(54, 0) + 0.6, '天 被日熔'), (S.CT(54, 5) + 0.15, '我来量 刻刀'), (S.CT(55, 6) + 0.15, '的 横斩裂屏'),
           (S.CT(55, 10) + 0.3, '正道沧桑'), (225.42 + 1.4, '片名斩开'), (229.3, '署名竖排'), (238.24 + 0.5, '入鞘落印'),
           (7174 / 30 + 0.6, '收墨一点朱'), (7174 / 30 + 1.2, '朱点呼吸+墨晕'), (6800 / 30, '鬼屠·第二季'), (7240 / 30, '末帧')]
    for t, lab in lyr:
        f = int(round(t * 30)); out.append((f, '%s f%d' % (lab, f)))
    return out


def sheet(frames, path, cols=4, tw=480):
    th = tw * 9 // 16
    rows = (len(frames) + cols - 1) // cols
    S_ = Image.new('RGB', (cols * tw, rows * (th + 26)), (12, 12, 12))
    d = ImageDraw.Draw(S_); fnt = ImageFont.truetype(FONT, 16)
    cache = {}
    for i, (f, lab) in enumerate(frames):
        a = time.time(); im = Image.fromarray(S.frame(f, cache)).resize((tw, th), Image.LANCZOS)
        x, y = (i % cols) * tw, (i // cols) * (th + 26)
        S_.paste(im, (x, y + 26)); d.text((x + 6, y + 3), lab, font=fnt, fill=(230, 210, 150))
        print('%-40s %.2fs' % (lab, time.time() - a), flush=True)
    S_.save(path, quality=86, optimize=True)
    print(path, os.path.getsize(path) // 1024, 'KB')


def split(path, maxh=1400):
    """评审分块：按行切成 ≤1920×maxh 的 _p0/_p1…（不切断格子）。"""
    im = Image.open(path); W_, H_ = im.size; th = 480 * 9 // 16 + 26
    per = max(1, maxh // th) * th; out = []
    for k, y in enumerate(range(0, H_, per)):
        q = path.replace('.jpg', '_p%d.jpg' % k); im.crop((0, y, W_, min(H_, y + per))).save(q, quality=86); out.append(q)
    print(out)


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'split': split(sys.argv[2]); sys.exit()
    fr = contact_frames() if mode == 'contact' else key_frames()
    if mode == 'list':
        for f, l in contact_frames() + key_frames(): print(f, l)
    else:
        sheet(fr, sys.argv[2])
