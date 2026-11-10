"""r6-C3：C 组总对比图（改前 C_R6=0 / 改后 默认），帧先渲到 /tmp/c3/cmp/{old,new}_<秒>.png。输出 out/round6/C_r6_compare*.jpg（1600 宽）。"""
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
D = '/tmp/c3/cmp/'; O = 'out/round6/'
FT = ImageFont.truetype('fonts/NotoSerifSC-SemiBold.otf', 24)
FH = ImageFont.truetype('fonts/NotoSerifSC-Bold.otf', 30)

def im(tag, s, w=800, crop=None):
    a = cv2.imread(D + f'{tag}_{s}.png')
    if crop: y0, y1, x0, x1 = crop; a = a[y0:y1, x0:x1]
    return cv2.resize(a, (w, round(a.shape[0] * w / a.shape[1])), interpolation=cv2.INTER_AREA)

def label(a, txt, col=(255, 255, 255)):
    p = Image.fromarray(a[..., ::-1].copy()); d = ImageDraw.Draw(p)
    d.rectangle([0, 0, d.textlength(txt, font=FT) + 16, 36], fill=(0, 0, 0)); d.text((8, 2), txt, font=FT, fill=col)
    return np.array(p)[..., ::-1]

def head(txt, w=1600):
    p = Image.new('RGB', (w, 50), (24, 22, 20)); ImageDraw.Draw(p).text((14, 6), txt, font=FH, fill=(235, 220, 190))
    return np.array(p)[..., ::-1]

def pair(s, note, crop=None):
    return np.hstack([label(im('old', s, crop=crop), f'改前 {s}s'), label(im('new', s, crop=crop), f'改后 {s}s  {note}', (255, 225, 160))])

def save(name, rows):
    cv2.imwrite(O + name, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 86]); print(name)

save('C_r6_compare_1_35_40.jpg', [head('#35 C02「纲」改在「本」后放线、落「提」拍；七线拴字头打结（f6679c8）'), pair(120.2, '纲上线'), pair(120.6, '提纲同拍'),
                                  head('#40 C21 重新构图：「邪」「正」放各半场外侧天幕，先字后人（279d7cb）'), pair(139.5, ''), pair(140.3, '')])
save('C_r6_compare_2_41.jpg', [head('#41 C22 2:21 人始终站在地上：前半脚部特写 + 全景脚踩礁石（6d99b6b，C_R6_FEET）'), pair(140.9, '脚部特写'), pair(141.6, '全景'),
                               head('#41 全景局部（脚 / 接触阴影 / 头部压暗）'), pair(141.6, '局部', crop=(500, 960, 700, 1220))])
save('C_r6_compare_3_42.jpg', [head('#42 C23 铜牌去倒角边 + 墙画框补砖 + 阴刻圆规/曲尺/天平（3e4bd6f）；C28 光只沿裂纹'),
                               pair(142.6, 'C23'), pair(143.0, 'C23'), pair(147.9, 'C28 2:27.9')])
save('C_r6_compare_4_43.jpg', [head('#43 2:37–2:42：C37「判」全去（a9e96b1）/ C38 年轻手（1fd5f6b）/ C39 左半幅补天平（ace4f0d）'),
                               pair(156.6, 'C37 无判'), pair(157.6, 'C38 手'), pair(158.9, 'C39 左半幅')])
S = [125.3, 127.0, 128.9, 130.7, 132.5, 135.0, 136.9, 137.9, 139.7]
def grid(tag):
    c = [label(im(tag, s, 266), f'{s}') for s in S]
    return np.vstack([np.hstack(c[i:i + 3]) for i in (0, 3, 6)])
g0, g1 = grid('old'), grid('new')
save('C_r6_compare_5_39strip.jpg', [head('#39 2:05–2:20 九帧条 左改前/右改后：只留水中「血」（135.0；13bd49f；多数字 r5 已去）'),
                                    np.hstack([g0, np.zeros((g0.shape[0], 1600 - 2 * g0.shape[1], 3), np.uint8), g1])])
