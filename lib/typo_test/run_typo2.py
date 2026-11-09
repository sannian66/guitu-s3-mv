"""导演组新增需求的联系表。python run_typo2.py [名字...]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_typo import *   # noqa
import numpy as np, cv2
import typo as T

def ring_demo(f, p):
    out, front, kw = T.text_on_ring(f, '这一刀', W / 2, H / 2, 520, 150, phase=p * 2 * math.pi, size=140, emph='刀', fname='xing')
    ring = np.zeros((H, W), np.float32)
    cv2.ellipse(ring, (W // 2, H // 2), (520, 150), 0, 0, 360, 1.0, 3, cv2.LINE_AA)
    ring = cv2.GaussianBlur(ring, (0, 0), 2) * 2 + cv2.GaussianBlur(ring, (0, 0), 14) * 4
    out = out + ring[..., None] * np.array([1, 0.9, 0.75], np.float32) * 0.5
    return T.ring_front(out, front, kw)

def wall(f, p, mode):
    B = T.wall_bricks(highlight='铁壁铜墙', hl_color='gold', seed=2)
    return T.text_wall(f, p, mode=mode, bricks=B, seed=2)

def rot_demo(f, p):
    g = T.typewriter(f, '若这世道黑白颠倒', 1.0, t=0, size=110, fname='song', color='white', cursor=False)
    return T.rotate_invert(g, p)

def credits(f, p):
    f = T.credit_block(f, '出品人', '西几王传媒', 1580, 230, min(1, p * 1.6), seal_text='西几王')
    f = T.credit_block(f, '美术设计', 'Cait', 900, 230, min(1, p * 1.4))
    f = T.credit_block(f, 'AI画师', '沉溺\u3000雪晴\u3000索恩', 520, 230, p)
    return T.typewriter(f, '鬼屠 · 第二季', 1.0, size=40, box=(1100, 860, 1840, 940), cursor=False)

def quad_demo(f, p):
    f = T.text_on_quad(f, '谁把人命装进天平里称量', [(260, 420), (1660, 330), (1660, 420), (260, 500)], p=p, emph='人命', strip_h=160)
    return T.text_on_quad(f, '谁定正邪', [(500, 900), (1420, 900), (1300, 700), (620, 700)], p=1, color='white', alpha=0.4, streak=True, fname='xing', emph='邪')

def seal_combo(f, p):
    f = T.seal_grid(f, '是非对错', 560, 540, 250, min(1, p * 1.3), colors=['ink', 'red', 'ink', 'red'])
    return T.stamp_overprint(f, '理所应当', 1400, 540, 300, p)

def seal_break(f, p):
    if p < 0.5:
        return T.seal_caption(f, '正义', '若正义由权势执掌', W / 2, 400, 300, p * 2, cap_emph='权势', cap_color='ink')
    L = T.seal_layer('对错', W / 2, 520, 340, style='yin')
    q = (p - 0.5) * 2
    if q < 0.5: return T.slash_layer(f, L, q * 2, (W / 2, 520), -60, sz=340, length=700, style_kw=dict(shadow=0, glow=0))
    L2 = T.shatter_layer(L, (q - 0.5) * 2, n=40)
    return T.compose(f, L2, shadow=0, glow=0)

def drip_strike(f, p):
    L, P = T.text_layer('谁的规矩用血来装潢', style='v', size=110, fname='cao', emph='血', box=(1200, 160, 1800, 920))
    i = [q['ch'] for q in P].index('血'); T.drip_layer(L, p, n=5, seed=1, region=T.bbox([P[i]], 0.5))
    f = T.compose(f, L, **T.auto_style('white'))
    P2 = T.layout('不听天命 不问上苍', 'v', size=95, fname='kai', box=(300, 160, 900, 920))
    L2 = T._line_layer(P2, ['white'] * len(P2)); f = T.compose(f, L2, **T.auto_style('white'))
    f = T.strike(f, P2, [2, 3], min(1, p * 2))
    return T.strike(f, P2, [6, 7], max(0, p * 2 - 1))

NEW = {
    'char_rain': lambda: run('char_rain', lambda f, p: T.char_rain(f, 162.6 + p * 9, '什么叫大局什么叫牺牲什么叫忍让', t0=162.6, emph='牺牲', color='ink', density=45),
                             [0.05, 0.15, 0.3, 0.5, 0.75, 1.0], Pp),
    'wall_build': lambda: run('wall_build', lambda f, p: wall(f, p, 'build'), [0.1, 0.3, 0.5, 0.7, 0.85, 1.0], D),
    'wall_crack': lambda: run('wall_crack', lambda f, p: wall(f, p, 'crack'), [0.0, 0.05, 0.12, 0.3, 0.6, 1.0], D),
    'wall_collapse': lambda: run('wall_collapse', lambda f, p: wall(f, p, 'collapse'), [0.0, 0.1, 0.25, 0.4, 0.6, 0.85], D),
    'wall_fly': lambda: run('wall_fly', lambda f, p: wall(f, p, 'fly'), [0.0, 0.1, 0.25, 0.45, 0.65, 0.9], D),
    'font_morph': lambda: run('font_morph', lambda f, p: T.font_morph(f, '反抗', p, size=300, color='white', colorB='red'), [0.0, 0.25, 0.45, 0.55, 0.75, 1.0], D),
    'quad_ring': lambda: run('quad_ring', lambda f, p: quad_demo(f, p) if p < 0.5 else ring_demo(f, p), [0.1, 0.3, 0.45, 0.6, 0.75, 0.9], D),
    'kinetic_fly': lambda: run('kinetic_fly', lambda f, p: T.kinetic_fly(f, '刀不放', p, size=80, emph='刀'), [0.1, 0.3, 0.5, 0.65, 0.8, 0.95], D),
    'rotate_invert': lambda: run('rotate_invert', rot_demo, [0.0, 0.2, 0.42, 0.5, 0.7, 1.0], D),
    'blade_write': lambda: run('blade_write', lambda f, p: T.blade_write(f, '判', p if p < 0.7 else (p - 0.7) / 0.3, size=600, color='red') if p < 0.7 else T.blade_write(f, '判', (p - 0.7) / 0.3, size=560, lightning=True),
                               [0.1, 0.3, 0.5, 0.69, 0.8, 0.95], D),
    'burn_modes': lambda: run('burn_modes', lambda f, p: T.burn_in(f, '陪葬', p * 2, size=300, mode='ash', color='red') if p < 0.5 else T.burn_in(f, '天亮', (p - 0.5) * 2, size=300, mode='extinguish', color='gold'),
                              [0.2, 0.33, 0.45, 0.7, 0.85, 0.99], D),
    'typewriter': lambda: run('typewriter', lambda f, p: T.typewriter(f, '谁的正义成了交易的', p, t=p * 3, size=96, rgb='交易', emph='交易', emph_color='gold'), [0.15, 0.4, 0.6, 0.75, 0.9, 1.0], D),
    'credits': lambda: run('credits', credits, [0.15, 0.35, 0.55, 0.75, 0.9, 1.0], D),
    'seal_combo': lambda: run('seal_combo', seal_combo, [0.1, 0.25, 0.45, 0.6, 0.8, 1.0], Pp),
    'seal_break': lambda: run('seal_break', seal_break, [0.15, 0.3, 0.45, 0.6, 0.72, 0.9], Pp),
    'drip_strike': lambda: run('drip_strike', drip_strike, [0.0, 0.2, 0.4, 0.6, 0.8, 1.0], D),
}

if __name__ == '__main__':
    names = sys.argv[1:] or list(NEW)
    for n in names: NEW[n]()
    with open(os.path.join(OUT, 'timing_typo.txt'), 'a') as fh:
        for k, (a, m) in TIMES.items(): fh.write(f'{k}\tavg {a:.3f}s\tmax {m:.3f}s\n')
