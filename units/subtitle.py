"""全片统一歌词字幕（第五轮用户要求 #52：歌词放居中下方字幕位置）。
在 render_sprite_full.frame 的成品帧上叠加：下黑边内居中、思源宋体 Medium、白字 + 柔阴影、逐句淡入淡出。
时间轴 = align.log 逐句起止（56 句）。环境变量 SUB_OFF=1 关闭。"""
import os, re, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT = '/workspace/work/mv'
FONT = ROOT + '/fonts/NotoSerifSC-Medium.otf'
SIZE, Y_C = 38, 1020          # 下黑边 120px（1080-120…1080），字幕中心 y=1020
FADE = 0.14
LINES = []
for l in open(ROOT + '/align.log', encoding='utf-8'):
    m = re.match(r'^([0-9.]+) ([0-9.]+)\s+(.+)$', l.strip())
    if m: LINES.append((float(m.group(1)), float(m.group(2)), m.group(3).strip()))
_C = {}

def _layer(txt):
    if txt in _C: return _C[txt]
    f = ImageFont.truetype(FONT, SIZE)
    txt_sp = txt.replace(' ', '\u3000')
    w = int(f.getlength(txt_sp)) + 40; h = SIZE + 30
    a = Image.new('L', (w, h), 0); ImageDraw.Draw(a).text((20, 10), txt_sp, font=f, fill=255)
    sh = a.filter(ImageFilter.GaussianBlur(4))
    _C[txt] = (np.asarray(a, np.float32) / 255, np.asarray(sh, np.float32) / 255)
    return _C[txt]

def current(t):
    for t0, t1, s in LINES:
        if t0 - FADE <= t < t1 + 0.25 + FADE: 
            k = min(1, (t - (t0 - FADE)) / FADE, (t1 + 0.25 + FADE - t) / FADE)
            return s, max(0.0, k)
    return None, 0

def apply(img, t):
    if os.environ.get('SUB_OFF'): return img
    s, k = current(t)
    if not s or k <= 0: return img
    a, sh = _layer(s)
    h, w = a.shape; x0 = (img.shape[1] - w) // 2; y0 = Y_C - h // 2
    out = img.astype(np.float32)
    reg = out[y0:y0 + h, x0:x0 + w]
    reg *= (1 - 0.75 * k * sh)[..., None]
    reg[:] = reg * (1 - 0.93 * k * a)[..., None] + np.array([238, 232, 222], np.float32) * (0.93 * k * a)[..., None]
    return out.clip(0, 255).astype(np.uint8)
