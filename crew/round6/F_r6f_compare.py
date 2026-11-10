"""F组 r6 第六棒：#21 改前/改后对比图（改前帧 = 开工时 HEAD 8a21a0c 渲的现状，与 R6F_E=0 画面逐像素一致（仅底部字幕区他组改动有差）；改后 = HEAD）"""
from PIL import Image, ImageDraw, ImageFont
fp = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/fonts/NotoSerifSC-Bold.otf'
F = lambda n: ImageFont.truetype(fp, n)
B = '/tmp/f6/before/b_%s.png'; A = '/tmp/f6/a/a_%s.png'
def lab(im, txt, n=20):
    d = ImageDraw.Draw(im); w = d.textlength(txt, font=F(n)); d.rectangle((0, 0, w + 12, n + 10), fill=(0, 0, 0)); d.text((6, 2), txt, font=F(n), fill=(255, 230, 120))
O = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/out/round6/'
ts = ['63.0', '63.2', '63.4', '63.6']; W, H = 400, 225
im = Image.new('RGB', (W * 4, H * 2))
for i, t in enumerate(ts):
    for r, (p, tag) in enumerate([(B, '改前'), (A, '改后')]):
        x = Image.open(p % t).resize((W, H), Image.LANCZOS); lab(x, f'{tag} {t}s', 18); im.paste(x, (i * W, r * H))
im.save(O + 'F_r6f_compare_21.jpg', quality=90)
ts = ['63.2', '63.4', '63.6']; S = 520
im = Image.new('RGB', (S * 3, S * 2))
for i, t in enumerate(ts):
    for r, (p, tag) in enumerate([(B, '改前'), (A, '改后')]):
        x = Image.open(p % t).crop((780, 330, 1040, 590)).resize((S, S), Image.LANCZOS); lab(x, f'{tag} {t}s 脸部 2×'); im.paste(x, (i * S, r * S))
im.save(O + 'F_r6f_compare_21_face.jpg', quality=90)
ts = ['63.2', '63.233', '63.267', '63.3', '63.333', '63.367', '63.4', '63.433', '63.467', '63.5']; S = 160
im = Image.new('RGB', (S * 10, S * 2))
for i, t in enumerate(ts):
    for r, (p, tag) in enumerate([(B, '前'), (A, '后')]):
        x = Image.open(p % t).crop((780, 330, 1000, 550)).resize((S, S), Image.LANCZOS); lab(x, f'{tag} {t}', 14); im.paste(x, (i * S, r * S))
im.save(O + 'F_r6f_compare_21_seq.jpg', quality=90)
print('ok')
