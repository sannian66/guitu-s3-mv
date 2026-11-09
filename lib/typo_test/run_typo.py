"""typo 联系表：每个效果 6 相位，深色水墨背景 / 浅色宣纸背景。用法: python run_typo.py [效果名...]"""
import sys, time, math, os
sys.path.insert(0, '/workspace/work/mv/lib')
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
import typo as T

OUT = os.path.dirname(os.path.abspath(__file__))
W, H, BAR = 1920, 1080, 120


def bg_dark(seed=0):
    r = np.random.default_rng(seed)
    y = np.linspace(0, 1, H)[:, None]
    n = cv2.resize(r.random((9, 16)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    n2 = cv2.resize(r.random((36, 64)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    base = 0.10 + 0.16 * (1 - y) * (0.6 + 0.6 * n) + 0.05 * n2
    x = np.linspace(0, 1, W)[None, :]
    mt = (y > 0.62 + 0.08 * np.sin(x * 9 + 1) + 0.05 * np.sin(x * 23)).astype(np.float32)
    base = base * (1 - mt * 0.7)
    fr = np.stack([base * 0.97, base, base * 1.05], -1).astype(np.float32)
    cv2.circle(fr, (1450, 330), 120, (0.85, 0.84, 0.8), -1, cv2.LINE_AA)
    return cv2.GaussianBlur(fr, (0, 0), 1.2)


def bg_paper(seed=1):
    r = np.random.default_rng(seed)
    n = cv2.resize(r.random((60, 100)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    f = cv2.resize(r.random((H // 2, W // 2)).astype(np.float32), (W, H))
    b = 0.86 + 0.05 * n + 0.03 * f
    return np.stack([b * 0.99, b * 0.95, b * 0.86], -1).astype(np.float32)


def letterbox(fr):
    fr = np.clip(fr, 0, 1); fr[:BAR] = 0; fr[H - BAR:] = 0; return fr


LBLF = ImageFont.truetype('/workspace/work/mv/fonts/NotoSerifSC.otf', 22)
def sheet(name, frames, labels, cols=3):
    ims = []
    for f, l in zip(frames, labels):
        im = Image.fromarray((letterbox(f) * 255).astype(np.uint8)).resize((640, 360), Image.LANCZOS)
        d = ImageDraw.Draw(im); d.text((8, 4), l, font=LBLF, fill=(255, 220, 120))
        ims.append(im)
    rows = (len(ims) + cols - 1) // cols
    C = Image.new('RGB', (640 * cols, 360 * rows), (40, 0, 0))
    for k, i in enumerate(ims): C.paste(i, ((k % cols) * 640, (k // cols) * 360))
    path = os.path.join(OUT, f'{name}.jpg'); C.save(path, quality=88)
    return path


TIMES = {}
def run(name, fn, ps, bg):
    frs = []; ts = []
    fn(bg.copy(), ps[-1])  # 预热缓存
    for p in ps:
        a = time.time(); frs.append(fn(bg.copy(), p)); ts.append(time.time() - a)
    TIMES[name] = (np.mean(ts), np.max(ts))
    print(name, 'avg %.3fs max %.3fs' % TIMES[name], sheet(name, frs, [f'{name} p={p:.2f}' for p in ps]), flush=True)


D, Pp = bg_dark(), bg_paper()
L7 = T.line_text(7)      # 那我宁愿做乱世的锋芒
TESTS = {
    'brush_write': lambda: run('brush_write', lambda f, p: T.brush_write(f, '长夜压在 我刀锋之上', p, style='v', fname='xing', color='white', size=170, anchor=(0.62, 0.3)),
                               [0.05, 0.2, 0.4, 0.6, 0.85, 1.0], D),
    'brush_paper': lambda: run('brush_paper', lambda f, p: T.brush_write(f, '谁定正邪', p, style='h', fname='cao', color='ink', size=300, emph='邪'),
                               [0.1, 0.3, 0.5, 0.7, 0.9, 1.0], Pp),
    'vertical_column': lambda: run('vertical_column', lambda f, p: T.vertical_column(f, '若正义 由权势执掌', p, size=130, emph='权势', anchor=(0.88, 0.0)),
                                   [0.1, 0.3, 0.5, 0.7, 0.9, 1.0], D),
    'scatter_stack': lambda: run('scatter_stack', lambda f, p: T.scatter_stack(f, '我不信天 不信命 不信谁的理所应当', p, emph='天命', size=120, t_local=p),
                                 [0.1, 0.25, 0.45, 0.65, 0.85, 1.0], D),
    'giant_char': lambda: run('giant_char', lambda f, p: T.giant_char(f, '刀', p, mode='window') if p < 0.66 else T.giant_char(f, '血', (p - 0.66) * 3, mode='solid', color='red', fname='xing'),
                              [0.04, 0.12, 0.3, 0.6, 0.75, 0.99], D),
    'carved_on_blade': lambda: run('carved_on_blade', lambda f, p: T.carved_on_blade(_blade(f), '只信这柄刀还滚烫', [(260, 760), (900, 560), (1700, 330)], height=110, p=p, finish='gold' if p < 0.8 else 'steel'),
                                   [0.1, 0.3, 0.5, 0.7, 0.9, 1.0], D),
    'stamp_seal': lambda: run('stamp_seal', lambda f, p: T.stamp_seal(T.brush_write(f, '天不判 我来量', 1.0, style='v', color='ink', size=160, anchor=(0.6, 0.2)), '鬼屠正邪', 1480, 780, 210, p, style='yin'),
                              [0.05, 0.2, 0.3, 0.34, 0.5, 1.0], Pp),
    'slash_cut': lambda: run('slash_cut', lambda f, p: T.slash_cut(f, '若规则是铁壁铜墙', p, size=170, emph='铁壁铜墙', fname='kai'),
                             [0.08, 0.2, 0.27, 0.33, 0.55, 0.95], D),
    'ink_bleed_in': lambda: run('ink_bleed_in', lambda f, p: T.ink_bleed_in(f, '血未冷 骨未凉', p, size=200, emph='血', fname='xing'),
                                [0.1, 0.3, 0.5, 0.7, 0.9, 1.0], Pp),
    'shatter_out': lambda: run('shatter_out', lambda f, p: T.shatter_out(f, '谁的正义成了交易的暗箱', p, size=130, emph='暗箱'),
                               [0.0, 0.08, 0.14, 0.3, 0.5, 0.75], D),
    'kinetic_track': lambda: run('kinetic_track', lambda f, p: T.kinetic_track(f, [
        dict(text='什么叫大局', x=-500, y=-150, z=2400, size=150, color='white'),
        dict(text='什么叫牺牲', x=350, y=120, z=1500, size=150, color='gold'),
        dict(text='什么叫忍让', x=-100, y=260, z=900, size=130, color='red'),
        dict(text='天', x=700, y=-260, z=3800, size=600, color='white', font='cao')], cam=(-250 + 500 * p, 0, -200 + 700 * p), focus_z=1500),
        [0.0, 0.2, 0.4, 0.6, 0.8, 1.0], D),
    'burn_in': lambda: run('burn_in', lambda f, p: T.burn_in(f, '只信这柄刀还滚烫', p, size=170, emph='滚烫'),
                           [0.15, 0.3, 0.45, 0.6, 0.8, 1.0], D),
    'typewriter_brush': lambda: run('typewriter_brush', lambda f, p: T.typewriter_brush(f, '这一刀 就是我的回答', p, size=170, emph='刀', fname='xing'),
                                    [0.1, 0.25, 0.4, 0.55, 0.75, 1.0], D),
    'text_matrix': lambda: run('text_matrix', lambda f, p: T.text_matrix(f, 2 + p * 3, highlight='谁人来定正邪一方', hl_prog=min(1, p * 2), pulse=max(0, 1 - (p * 4 % 1) * 3),
                                                                    shape=T.shape_mask('moon', c=(1500, 380), r=200) if p > 0.5 else None, shape_p=(p - 0.5) * 2),
                               [0.05, 0.2, 0.35, 0.55, 0.8, 1.0], D),
    'char_shape': lambda: run('char_shape', lambda f, p: T.char_shape(f, p * 2, T.glyph_mask('正', 'kai') if p < 0.5 else T.shape_mask('blade', angle=-25, length=1500, width=130), p=min(1, (p % 0.5) * 2.4), color='gold' if p < 0.5 else 'white', sweep='center' if p < .5 else 'right'),
                              [0.1, 0.25, 0.45, 0.6, 0.8, 0.98], D),
    'explode_reform': lambda: run('explode_reform', lambda f, p: T.explode_reform(f, '血未冷', '刀不放', p, size=280, fname='xing', color='red', colorB='gold'),
                                  [0.03, 0.2, 0.35, 0.55, 0.8, 1.0], D),
}


def _blade(f):
    f = f.copy()
    poly = np.array([(180, 820), (1780, 270), (1840, 280), (1790, 330), (260, 880)], np.int32)
    m = np.zeros((H, W), np.float32); cv2.fillPoly(m, [poly], 1.0, cv2.LINE_AA)
    grad = np.linspace(0.55, 0.85, W)[None, :] * np.ones((H, 1))
    steel = np.stack([grad * 0.9, grad * 0.93, grad], -1)
    sheen = np.exp(-((np.arange(H)[:, None] - (820 - np.arange(W)[None, :] * 0.33)) / 30) ** 2)
    steel = steel + sheen[..., None] * 0.15
    return (f * (1 - m[..., None]) + steel * m[..., None] * 0.6).astype(np.float32)


if __name__ == '__main__':
    names = sys.argv[1:] or list(TESTS)
    for n in names: TESTS[n]()
    with open(os.path.join(OUT, 'timing_typo.txt'), 'a') as fh:
        for k, (a, m) in TIMES.items(): fh.write(f'{k}\tavg {a:.3f}s\tmax {m:.3f}s\n')
