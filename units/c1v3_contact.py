"""v3 联系表：每镜主运镜起止帧（从成片抽帧）+ 运镜说明 → out/chorus1_v3_contact.jpg"""
import sys, subprocess, os
sys.path[:0] = ['/workspace/work/mv/units', '/workspace/work/mv/lib', '/workspace/work/mv']
import chorus1 as C
from PIL import Image, ImageDraw, ImageFont
V = '/workspace/work/mv/out/sample_chorus1_v3.mp4'
F = ImageFont.truetype('/workspace/work/mv/fonts/NotoSerifSC-Regular.otf', 15)
FB = ImageFont.truetype('/workspace/work/mv/fonts/NotoSerifSC-SemiBold.otf', 17)
TW, TH = 480, 210
rows = []
for S in C.SHOTS:
    a, b = max(S.t0, 58.5), S.t1
    ins = {f for f in C._INS}
    fa = int(round(a * 30)) + 1; fb = int(round(b * 30)) - 2
    while fa in ins: fa += 1
    while fb in ins: fb -= 1
    ims = []
    for f in (fa, (fa + fb) // 2, fb):
        o = f'/tmp/cf_{f}.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{f / 30 - 58.5 + 0.001:.3f}', '-i', V, '-frames:v', '1',
                        '-vf', f'crop=1920:840:0:120,scale={TW}:{TH}', o], check=True)
        ims.append((f, Image.open(o).convert('RGB')))
    rows.append((S.__name__, a, b, ims, C.MOVES3[S.__name__].note))
S_ = Image.new('RGB', (TW * 3 + 380, (TH + 6) * len(rows)), (24, 24, 28))
d = ImageDraw.Draw(S_)
for r, (n, a, b, ims, note) in enumerate(rows):
    y = r * (TH + 6)
    for c, (f, im) in enumerate(ims):
        S_.paste(im, (c * TW, y))
        d.text((c * TW + 4, y + 2), ['起', '中', '止'][c] + f' {f / 30:.2f}s', font=F, fill=(255, 220, 120))
    d.text((TW * 3 + 12, y + 8), f'{n}  {a:.2f}–{b:.2f}s', font=FB, fill=(255, 230, 190))
    line, yy = '', y + 36
    for ch in note:
        if d.textlength(line + ch, font=F) > 350: d.text((TW * 3 + 12, yy), line, font=F, fill=(220, 220, 225)); yy += 22; line = ''
        line += ch
    d.text((TW * 3 + 12, yy), line, font=F, fill=(220, 220, 225))
S_.save('/workspace/work/mv/out/chorus1_v3_contact.jpg', quality=84)
print('ok', S_.size)
