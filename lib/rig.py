"""@@HEADER@@"""
import numpy as np, cv2, math

W, H = 1920, 1080
RED = np.array([0.72, 0.06, 0.05], np.float32)     # 朱红
GOLD = np.array([1.0, 0.76, 0.40], np.float32)     # 金
INK = np.array([0.030, 0.030, 0.038], np.float32)
D2R = math.pi / 180

# ============================================================== 基础工具
def _rx(a):
    c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def _ry(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def _rz(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
def _rot(yaw, pitch, roll):
    """度数。yaw+ 向右转，pitch+ 前倾/低头，roll+ 向左侧倾"""
    return _ry(yaw * D2R) @ _rx(pitch * D2R) @ _rz(roll * D2R)
def _nrm(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True); return v / np.maximum(n, 1e-9)
def _sdir(el, az):
    e, a = el * D2R, az * D2R
    return np.array([math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a)])

def ease(u, kind='io'):
    u = min(max(u, 0.0), 1.0)
    if kind == 'lin': return u
    if kind == 'io': return u * u * (3 - 2 * u)
    if kind == 'i': return u ** 3
    if kind == 'i2': return u * u
    if kind == 'o': return 1 - (1 - u) ** 3
    if kind == 'o5': return 1 - (1 - u) ** 5          # 爆发出手
    if kind == 'bk':                                   # 过冲回弹
        c = 1.9; return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2
    if kind == 'step': return 0.0 if u < 1 else 1.0
    return u

def smooth(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-9), 0, 1); return t * t * (3 - 2 * t)

_NOISE = {}
def noise_tex(n=1024, seed=0, base=8, octaves=5):
    """可平铺 fbm 纹理 (n,n) 0..1（缓存）"""
    k = (n, seed, base, octaves)
    if k not in _NOISE:
        rng = np.random.default_rng(seed)
        out = np.zeros((n, n), np.float32); amp = 1; tot = 0
        for o in range(octaves):
            g = base * 2 ** o
            a = rng.random((g, g)).astype(np.float32)
            a = np.tile(a, (3, 3))
            r = cv2.resize(a, (n * 3, n * 3), interpolation=cv2.INTER_CUBIC)[n:2 * n, n:2 * n]
            out += r * amp; tot += amp; amp *= 0.55
        out /= tot; out = (out - out.min()) / (out.max() - out.min() + 1e-6)
        _NOISE[k] = out
    return _NOISE[k]

def _tile(tex, x0, y0, h, w):
    n = tex.shape[0]
    ys = (np.arange(h) + y0) % n; xs = (np.arange(w) + x0) % n
    return tex[np.ix_(ys, xs)]

SH = 3; SHF = float(1 << SH)        # cv2 定点亚像素
def _ip(p): return np.round(np.asarray(p) * SHF).astype(np.int32)

# ============================================================== 动作库（关键帧）
# 单位：身高=100。骨盆坐标系：x=角色右，y=上，z=前；原点在双脚之间的地面。
# 手目标 rh/lh 位于“骨盆系、原点在腰 (y=59)”；刀向 se(仰角)/sa(方位角，0=正前，+90=右侧，180=正后) 亦在骨盆系。
BASE = dict(rx=0., ry=0., rz=0., ryaw=0., rp=0., rr=0., sp=2., sy=0., sr=0., hp=0., hy=0., hr=0.,
            lf=(-6., 4., -2.), rf=(6., 4., 2.), lfa=0., rfa=0.,
            rh=(14., -5., 2.), lh=(-14., -5., 1.), rpole=(1., -.3, -1.), lpole=(-1., -.3, -1.), two=0., grab=0.,
            se=-55., sa=160., drawn=1.)
STEP_CH = ('drawn',)

def K(p, e='io', **kw): return (p, e, kw)

GUARD = dict(rh=(5., 3., 16.), se=22., sa=-4., lh=(-2., 1., 13.), two=0.8, rpole=(1, -.6, -.6), lpole=(-1, -.6, -.6),
             rf=(5., 4., 9.), lf=(-6., 4., -8.), ry=-3., sp=6.)
ACTIONS = {}

def _stand_wind(p):
    s = math.sin(2 * math.pi * p); c = math.cos(2 * math.pi * p)
    return dict(ry=-0.35 * s, sp=2 + 1.2 * s, hp=-3 + 2 * math.sin(2 * math.pi * p + 1), hy=4 * math.sin(2 * math.pi * p * 1 + 2),
                rh=(14., -4.5 + 0.4 * s, 2.5), se=-58. + 2 * c, sa=158., lh=(-13.5, -4.5 + 0.4 * s, 1.5))
ACTIONS['stand_wind'] = dict(fn=_stand_wind, cyc=True, speed=0)

def _gait(p, stride, stance, lift, bob, lean, armsw, run=False):
    out = {}
    fz = {}
    for side, ph in (('r', p), ('l', (p + 0.5) % 1)):
        if ph < stance:
            u = ph / stance; z = stride / 2 - stride * u; y = 4.0
            fa = 0.0 if u < 0.7 else -25 * (u - 0.7) / 0.3 * (1 if run else 0.5)
        else:
            u = (ph - stance) / (1 - stance)
            if run:
                z = -stride / 2 + stride * (ease(u, 'io') ** 1.2)
                y = 4 + lift * math.sin(math.pi * min(1, u * 1.1)) ** 0.8 + (6 * math.sin(math.pi * u * 2) if u < .5 else 0)
            else:
                z = -stride / 2 + stride * ease(u, 'io'); y = 4 + lift * math.sin(math.pi * u)
            fa = 30 * (1 - u) - 15 * u
        x = 6.0 if side == 'r' else -6.0
        out[side + 'f'] = (x * (0.8 if run else 1), y, z); out[side + 'fa'] = fa; fz[side] = z
    out['ry'] = -bob * 0.5 - bob * 0.5 * math.cos(4 * math.pi * p) - (5 if run else 0.5)
    out['ryaw'] = 5 * math.sin(2 * math.pi * p) * (1.4 if run else 1)
    out['sy'] = -out['ryaw'] * 1.6
    out['sp'] = lean; out['rr'] = 2 * math.sin(2 * math.pi * p)
    zl = -fz['l'] * armsw
    out['lh'] = (-13. + (3 if run else 0), -5 + abs(zl) * 0.3 + (12 if run else 0), zl)
    out['lpole'] = (-1, -.6, -.6) if run else (-1, -.3, -1)
    return out

def _walk(p):
    o = _gait(p, 26, 0.6, 5, 2.0, 5, 0.55)
    o.update(rh=(14., -4., 2 - 0.12 * o['lf'][2]), se=-50., sa=165., hp=-2)
    return o
ACTIONS['walk'] = dict(fn=_walk, cyc=True, speed=80)

def _run(p):
    o = _gait(p, 46, 0.36, 13, 3.0, 20, 0.6, run=True)
    o.update(rp=8, hp=-16, rh=(15., 0., -9.), se=-12., sa=178., rpole=(1, .2, -1))
    return o
ACTIONS['run'] = dict(fn=_run, cyc=True, speed=330)

SC_EL, SC_AZ = -34.0, -173.0          # 刀鞘方向（骨盆系）
ACTIONS['draw_sword'] = dict(speed=0, keys=[
    K(0, drawn=0, rh=(14., -5., 2.), sy=0, ry=0),
    K(.22, 'io', drawn=0, grab=1., rh=(-6., -3., 12.), rpole=(1, -.8, .2), sy=-25, sp=10, ry=-4, hp=8, hy=-12, lh=(-11., -4., 4.),
      rf=(6., 4., 6.), lf=(-6., 4., -6.)),
    K(.34, 'io', drawn=1, grab=1., rh=(-6., -3., 13.), rpole=(1, -.8, .2), sy=-30, sp=12, ry=-6, se=SC_EL, sa=SC_AZ, hp=10, hy=-14,
      lh=(-11., -3., 3.), rf=(6., 4., 8.), lf=(-6., 4., -7.)),
    K(.44, 'i2', drawn=1, grab=0., rh=(-4., 8., 22.), rpole=(1, -.8, .2), sy=-14, sp=10, ry=-6, se=SC_EL, sa=SC_AZ, hp=6, hy=-8,
      lh=(-12., -3., 2.), rf=(6., 4., 10.), lf=(-6., 4., -8.)),
    K(.54, 'o5', drawn=1, rh=(18., 14., 14.), rpole=(1, -1, 0), sy=25, sp=4, ry=-3, se=8., sa=40., hp=0, hy=5,
      lh=(-17., 2., -4.), rf=(7., 4., 12.), lf=(-6., 4., -10.)),
    K(.70, 'o', drawn=1, rh=(20., 13., 10.), sy=32, se=-2., sa=75., lh=(-18., 4., -6.), rf=(7., 4., 12.), lf=(-6., 4., -10.)),
    K(1., 'io', drawn=1, **GUARD),
])
ACTIONS['slash_h'] = dict(speed=0, keys=[
    K(0, **GUARD),
    K(.28, 'io', rh=(16., 10., -2.), rpole=(1, -.4, -1), se=8., sa=150., sy=40, ryaw=10, sp=4, ry=-5, hy=-10, two=0.,
      lh=(-10., 6., 12.), lpole=(-1, -.5, 0), rf=(6., 4., 4.), lf=(-6., 4., -6.)),
    K(.40, 'o5', rh=(8., 9., 24.), rpole=(1, -.6, -.3), se=4., sa=10., sy=-5, ryaw=-5, ry=-9, hy=0,
      lh=(-18., 8., -2.), rf=(6., 4., 18.), lf=(-6., 4., -12.)),
    K(.50, 'o', rh=(-14., 8., 16.), rpole=(1, -1, 0), se=0., sa=-100., sy=-45, ryaw=-15, ry=-10,
      lh=(-20., 6., -10.), rf=(6., 4., 18.), lf=(-6., 4., -12.)),
    K(.70, 'o', rh=(-16., 6., 10.), se=-6., sa=-130., sy=-52, ryaw=-18, ry=-10, rf=(6., 4., 18.), lf=(-6., 4., -12.),
      lh=(-20., 6., -10.)),
    K(1., 'io', **GUARD),
])
ACTIONS['slash_diag'] = dict(speed=0, keys=[
    K(0, **GUARD),
    K(.30, 'io', rh=(10., 30., 0.), rpole=(1., .2, -.4), se=40., sa=-170., sy=30, sp=-4, ry=-2, hp=-6, two=0.6, lh=(4., 27., 2.),
      lpole=(-1, .2, -.5), rf=(6., 4., 3.), lf=(-6., 4., -6.)),
    K(.42, 'o5', rh=(4., 14., 22.), rpole=(1, -.4, -.4), se=30., sa=-10., sy=0, sp=14, ry=-10, hp=6, two=0.6, lh=(0., 12., 18.),
      rf=(6., 4., 20.), lf=(-6., 4., -14.)),
    K(.52, 'o', rh=(-10., -4., 18.), rpole=(1, -1, .3), se=-28., sa=-45., sy=-28, sp=30, ry=-16, two=0.5, lh=(-10., -6., 14.),
      rf=(6., 4., 22.), lf=(-6., 4., -15.)),
    K(.72, 'o', rh=(-12., -6., 15.), se=-36., sa=-60., sy=-32, sp=32, ry=-17, rf=(6., 4., 22.), lf=(-6., 4., -15.), two=0.,
      lh=(-18., 0., -8.)),
    K(1., 'io', **GUARD),
])
ACTIONS['slash_up'] = dict(speed=0, keys=[
    K(0, **GUARD),
    K(.28, 'io', rh=(-8., -8., 12.), rpole=(1, -1, .2), se=-40., sa=-150., sy=-35, sp=16, ry=-12, hp=10, two=0.,
      lh=(-16., -2., -4.), rf=(6., 4., 10.), lf=(-6., 4., -10.)),
    K(.42, 'o5', rh=(12., 14., 20.), rpole=(1, -.5, -.6), se=40., sa=30., sy=10, sp=-2, ry=-2, hp=-6,
      lh=(-18., 4., -8.), rf=(6., 4., 16.), lf=(-6., 6., -12.), lfa=30),
    K(.55, 'o', rh=(14., 34., 6.), rpole=(1, .3, -.5), se=78., sa=60., sy=24, sp=-8, ry=3, hp=-14, lfa=40,
      lh=(-20., 8., -6.), rf=(6., 6., 16.), lf=(-6., 9., -12.), rfa=30),
    K(.75, 'o', rh=(14., 35., 4.), se=82., sa=80., sy=26, sp=-9, ry=2, hp=-14, lh=(-20., 8., -6.), rf=(6., 5., 16.),
      lf=(-6., 7., -12.), rfa=20, lfa=30),
    K(1., 'io', **GUARD),
])
ACTIONS['spin_slash'] = dict(speed=0, keys=[
    K(0, **GUARD),
    K(.18, 'io', ryaw=-30, ry=-12, sp=12, rh=(-10., 2., 14.), rpole=(1, -1, 0), se=0., sa=-110., two=0., lh=(-12., 0., 6.),
      rf=(6., 4., 8.), lf=(-7., 4., -8.)),
    K(.40, 'i2', ryaw=120, ry=-6, sp=6, rh=(26., 10., 2.), rpole=(.4, -1, -.4), se=4., sa=92., lh=(-22., 8., -4.)),
    K(.62, 'lin', ryaw=280, ry=-6, sp=6, rh=(26., 10., 2.), se=2., sa=95., lh=(-22., 8., -4.)),
    K(.80, 'o', ryaw=345, ry=-10, sp=10, rh=(18., 6., 14.), se=-10., sa=60., lh=(-20., 6., -6.), rf=(7., 4., 12.),
      lf=(-7., 4., -10.)),
    K(1., 'io', ryaw=360, **GUARD),
])
ACTIONS['leap'] = dict(speed=0, keys=[
    K(0, **GUARD),
    K(.22, 'io', ry=-17, sp=24, rh=(10., -2., 4.), se=-30., sa=170., hp=-10, lh=(-16., -6., -8.), two=0.,
      rf=(6., 4., 6.), lf=(-6., 4., -6.), rfa=0, lfa=0),
    K(.40, 'o5', ry=26, sp=4, rh=(10., 34., 4.), rpole=(1, .3, -.3), se=80., sa=170., hp=-14, lh=(-16., 30., 0.),
      lpole=(-1, .3, -.3), rf=(6., 34., -6.), lf=(-6., 32., -10.), rfa=50, lfa=50),
    K(.62, 'o', ry=40, sp=14, rh=(10., 36., -2.), se=60., sa=-170., hp=-6, lh=(-12., 26., 4.),
      rf=(6., 66., 16.), lf=(-6., 56., -4.), rfa=20, lfa=40),
    K(.85, 'io', ry=26, sp=6, rh=(14., 26., 10.), se=70., sa=180., lh=(-18., 16., 0.), rf=(6., 40., 10.), lf=(-6., 32., -6.),
      rfa=30, lfa=30),
    K(1., 'i2', ry=14, sp=4, rh=(14., 22., 10.), se=75., sa=180., lh=(-20., 12., 0.), rf=(6., 18., 8.), lf=(-6., 13., -6.),
      rfa=20, lfa=10),
])
ACTIONS['land_kneel'] = dict(speed=0, keys=[
    K(0, ry=14, sp=4, rh=(14., 22., 10.), se=75., sa=180., lh=(-20., 12., 0.), rf=(6., 18., 8.), lf=(-6., 13., -6.),
      rfa=20, lfa=10),
    K(.16, 'i2', ry=-25, sp=34, rh=(22., -4., 4.), rpole=(1, .3, -.4), se=-20., sa=110., hp=24, lh=(-8., -16., 14.),
      lpole=(-1, .3, -.4), rf=(7., 4., 14.), lf=(-6., 3., -14.), lfa=-40, rr=4),
    K(.30, 'o', ry=-28, sp=38, rh=(24., -6., 0.), se=-14., sa=120., hp=30, lh=(-8., -18., 15.),
      rf=(7., 4., 15.), lf=(-6., 2.5, -15.), lfa=-50),
    K(.70, 'io', ry=-27, sp=34, rh=(24., -5., 0.), se=-14., sa=122., hp=26, lh=(-8., -17., 14.),
      rf=(7., 4., 15.), lf=(-6., 2.5, -15.), lfa=-50),
    K(1., 'io', ry=-25, sp=18, rh=(23., -5., 2.), se=-16., sa=125., hp=-14, lh=(-10., -14., 14.),
      rf=(7., 4., 15.), lf=(-6., 2.5, -15.), lfa=-50),
])
ACTIONS['sword_plant'] = dict(speed=0, keys=[
    K(0, rh=(14., -4., 4.), se=-50., sa=165.),
    K(.28, 'io', rh=(0., 22., 14.), rpole=(1, -.4, -.5), se=-88., sa=0., two=1., lh=(-2., 22., 13.), lpole=(-1, -.4, -.5),
      hp=-6, sp=-3, ry=1),
    K(.42, 'o5', rh=(0., -5., 15.), se=-90., sa=0., two=1., hp=16, sp=16, ry=-8, rf=(6., 4., 5.), lf=(-6., 4., -5.)),
    K(.58, 'o', rh=(0., -4., 15.), se=-90., sa=0., two=1., hp=20, sp=18, ry=-9, rf=(6., 4., 5.), lf=(-6., 4., -5.)),
    K(.85, 'io', rh=(0., -3., 14.), se=-90., sa=0., two=1., hp=14, sp=3, ry=0),
    K(1., 'io', rh=(0., -3., 14.), se=-90., sa=0., two=1., hp=4, sp=2, ry=0),
])
ACTIONS['look_up'] = dict(speed=0, keys=[
    K(0, hp=4),
    K(.25, 'io', hp=8, sp=4, ry=-1),
    K(.70, 'io', hp=-38, sp=-7, sr=0, ry=0.5, rh=(14.5, -3., 1.)),
    K(1., 'io', hp=-40, sp=-8, rh=(14.5, -3., 1.)),
])
ACTIONS['turn_head'] = dict(speed=0, keys=[
    K(0, hy=0),
    K(.18, 'io', hy=-6, hp=3),
    K(.62, 'o', hy=72, hp=-2, sy=16, hr=-4),
    K(.80, 'io', hy=68, sy=15, hr=-3),
    K(1., 'io', hy=70, sy=15, hr=-3),
])
ACTIONS['raise_sword_sky'] = dict(speed=0, keys=[
    K(0, rh=(14., -4., 4.), se=-50., sa=165.),
    K(.25, 'io', rh=(12., -6., 2.), se=-70., sa=150., ry=-6, sp=10, hp=6),
    K(.48, 'o5', rh=(8., 50., 3.), rpole=(1, .4, -.2), se=88., sa=0., ry=1, sp=-6, hp=-30, lh=(-16., -8., 1.),
      rf=(6., 4., 2.), lf=(-6., 4., -2.)),
    K(.62, 'o', rh=(8., 51., 3.), se=89., sa=0., ry=1.5, sp=-8, hp=-36, lh=(-17., -9., 0.)),
    K(1., 'io', rh=(8., 50., 3.), se=89., sa=0., ry=1, sp=-8, hp=-36, lh=(-17., -9., 0.)),
])
ACTIONS['sheath'] = dict(speed=0, keys=[
    K(0, **GUARD),
    K(.18, 'o5', rh=(20., 6., 12.), rpole=(1, -.5, -.4), se=-30., sa=70., two=0., lh=(-12., -2., 6.), sy=20,
      rf=(5., 4., 9.), lf=(-6., 4., -8.)),
    K(.42, 'io', rh=(-4., 8., 22.), rpole=(1, -.8, .2), se=SC_EL, sa=SC_AZ, two=0., lh=(-10., -4., 4.), sy=-16, sp=8,
      hp=10, ry=-3),
    K(.70, 'io', drawn=1, grab=1., rh=(-6., -3., 13.), rpole=(1, -.8, .2), se=SC_EL, sa=SC_AZ, lh=(-11., -4., 4.), sy=-26, sp=10,
      hp=12, ry=-4),
    K(.76, 'step', drawn=0, grab=1., rh=(-6., -3., 12.), sy=-26, sp=10, hp=12, ry=-4),
    K(1., 'io', drawn=0, grab=0.6, rh=(-5., -3., 11.), rpole=(1, -.8, .2), sy=-10, sp=4, hp=4, ry=-1, lh=(-13., -5., 1.)),
])
ACTIONS['fall_back_recover'] = dict(speed=0, keys=[
    K(0, **GUARD),
    K(.12, 'o5', rz=-6, sp=-24, rp=-6, hp=-20, ry=-2, rh=(22., 12., -4.), se=40., sa=130., two=0., lh=(-22., 14., -2.),
      rf=(6., 6., 6.), lf=(-6., 4., -10.), rfa=-20),
    K(.32, 'o', rz=-14, sp=10, rp=-4, hp=10, ry=-26, rh=(20., 0., 6.), se=-10., sa=110., lh=(-10., -20., -16.),
      lpole=(-1, .5, .3), rf=(7., 4., 4.), lf=(-6., 2.5, -20.), lfa=-50),
    K(.55, 'io', rz=-14, sp=24, hp=-8, ry=-24, rh=(18., 2., 10.), se=10., sa=60., lh=(-10., -18., -12.),
      rf=(7., 4., 4.), lf=(-6., 2.5, -20.), lfa=-50),
    K(.75, 'o5', rz=-10, sp=12, ry=-8, rh=(8., 4., 16.), se=18., sa=0., two=0.6, lh=(-3., 2., 13.), rf=(6., 4., 8.),
      lf=(-6., 4., -10.)),
    K(1., 'io', rz=-8, **GUARD),
])

def _on_shoulder(p, prm):
    """刀横扛右肩，刀身从肩后横过颈后（背影最佳）。phase 循环：呼吸"""
    s = math.sin(2 * math.pi * p)
    return dict(ry=-0.4 * s, sp=1 + s, hp=-4 + 2 * s, rh=(11., 18. + 0.5 * s, 9.), rpole=(1, -1, .2), se=8., sa=-118.,
                lh=(-13.5, -4.5, 1.), rf=(7., 4., 1.), lf=(-7., 4., -1.), sy=-4)
ACTIONS['sword_on_shoulder'] = dict(fn=_on_shoulder, cyc=True, speed=0, prm=True)

def _overhead_strain(p, prm):
    """举刀过顶硬扛：刀身水平在头顶，左手托刀背，膝下沉。phase 循环=颤抖；strain(0..1) 控制下沉与颤抖幅度"""
    k = float(prm.get('strain', 0.8))
    tr = (math.sin(2 * math.pi * p * 9) + 0.6 * math.sin(2 * math.pi * p * 23 + 1)) * 0.5 * k
    return dict(ry=-16 * k + tr * 0.6, sp=6 * k, hp=-22 + 6 * k + tr, rh=(8., 41. - 7 * k + tr, 3.), rpole=(1, .2, -.2),
                se=2. + tr, sa=-92., two=0., lh=(-16., 41. - 7 * k + tr, 3.5), lpole=(-1, .2, -.2),
                rf=(9. + 3 * k, 4., 4.), lf=(-9. - 3 * k, 4., -4.), rr=tr * 0.5)
ACTIONS['hold_overhead_strain'] = dict(fn=_overhead_strain, cyc=True, speed=0, prm=True)

def _horiz_chest(p, prm):
    """双手横刀于胸前，刀身水平指向左侧（正/背面看是一条横梁）"""
    s = math.sin(2 * math.pi * p)
    return dict(ry=-1 + 0.3 * s, sp=2, hp=2 + s, rh=(9., 13. + 0.3 * s, 11.), rpole=(1, -1, 0), se=0.5 * s, sa=-90.,
                two=0., lh=(-12., 13.5 + 0.3 * s, 11.), lpole=(-1, -1, 0), rf=(7., 4., 1.), lf=(-7., 4., -1.))
ACTIONS['blade_horizontal_chest'] = dict(fn=_horiz_chest, cyc=True, speed=0, prm=True)

def _lerp_ch(a, b, u):
    if isinstance(a, tuple): return tuple(x + (y - x) * u for x, y in zip(a, b))
    return a + (b - a) * u

def _catmull(p0, p1, p2, p3, u):
    if isinstance(p1, tuple):
        return tuple(_catmull(a, b, c, d, u) for a, b, c, d in zip(p0, p1, p2, p3))
    u2, u3 = u * u, u * u * u
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u3)

_KEYCACHE = {}
def _full_keys(name):
    if name in _KEYCACHE: return _KEYCACHE[name]
    keys = ACTIONS[name]['keys']; full = []; cur = dict(BASE)
    for p, e, kw in keys:
        cur = dict(cur); cur.update(kw)
        for k2 in ('rpole', 'lpole'):           # 极向量未写则回默认
            if k2 not in kw: cur[k2] = BASE[k2]
        if 'two' not in kw and 'lh' in kw: cur['two'] = 0.
        if 'grab' not in kw: cur['grab'] = 0.
        full.append((p, e, cur))
    _KEYCACHE[name] = full
    return full

def sample_action(name, phase, prm=None):
    """返回该动作在 phase(0..1) 的全部通道 dict"""
    A = ACTIONS[name]
    if 'fn' in A:
        ph = phase % 1.0 if A.get('cyc') else phase
        d = dict(BASE); d.update(A['fn'](ph, prm or {}) if A.get('prm') else A['fn'](ph)); return d
    ks = _full_keys(name); phase = min(max(phase, 0.), 1.)
    i = 0
    while i < len(ks) - 2 and phase > ks[i + 1][0]: i += 1
    p1, _, c1 = ks[i]; p2, e2, c2 = ks[i + 1]
    u = ease((phase - p1) / max(1e-6, p2 - p1), e2) if e2 != 'step' else (1. if phase >= p2 else 0.)
    c0 = ks[i - 1][2] if i > 0 else c1
    c3 = ks[i + 2][2] if i + 2 < len(ks) else c2
    out = {}
    for k in c1:
        if k in STEP_CH: continue
        out[k] = _catmull(c0[k], c1[k], c2[k], c3[k], u)
    out['drawn'] = c2['drawn'] if phase >= p2 - 1e-9 else c1['drawn']
    return out

def blend_poses(a, b, w):
    """两组通道线性混合（用于动作衔接）。w=0→a, 1→b"""
    o = {}
    for k in a:
        if k in STEP_CH: o[k] = b[k] if w > 0.5 else a[k]
        else: o[k] = _lerp_ch(a[k], b[k], w)
    return o

# ============================================================== IK / 布料
def _ik(S, T, L1, L2, pole):
    d = T - S; dist = np.linalg.norm(d)
    dist_c = min(max(dist, abs(L1 - L2) + 1e-3), (L1 + L2) * 0.999)
    u = d / max(dist, 1e-9)
    a = (L1 * L1 - L2 * L2 + dist_c * dist_c) / (2 * dist_c)
    h = math.sqrt(max(L1 * L1 - a * a, 0))
    p = pole - u * np.dot(pole, u); p = p / max(np.linalg.norm(p), 1e-9)
    E = S + u * a + p * h
    return E, S + u * dist_c

class Chains:
    """一组 verlet 链（头发/飘带/裙摆/袖）。P:(C,L,3)。follow-the-leader 约束 + 形状刚度 + 胶囊碰撞。"""
    def __init__(self, C, L, seg, drag, stiff, damp=0.97, grav=1.0, ring=0.0):
        self.C, self.L = C, L
        self.seg = np.broadcast_to(np.asarray(seg, np.float64).reshape(-1, 1) if np.ndim(seg) else seg, (C, L - 1)).copy() \
            if np.ndim(seg) < 2 else np.asarray(seg, np.float64)
        self.drag = drag; self.damp = damp; self.grav = grav
        self.stiff = np.broadcast_to(np.asarray(stiff, np.float64), (C, L)).copy() if np.ndim(stiff) < 2 else np.asarray(stiff)
        self.ring = ring                       # 环向约束强度（裙摆）
        self.P = None; self.Q = None; self.ring_rest = None
        self.phase = np.random.default_rng(C * 31 + L).random((C, 1)) * 6.28
        self.wk = 1.0; self.turb = 1.0         # v4：风力/湍流对本组链的系数（马尾受风小、下垂）

    def reset(self, anc, rest):
        P = np.zeros((self.C, self.L, 3)); P[:, 0] = anc
        for j in range(1, self.L): P[:, j] = P[:, j - 1] + rest[:, j - 1] * self.seg[:, j - 1:j]
        self.P = P; self.Q = P.copy()
        if self.ring > 0:
            self.ring_rest = np.linalg.norm(np.roll(P, -1, 0) - P, axis=-1)

    def step(self, dt, anc, rest, wind, t, cols, ground=0.6):
        P, Q = self.P, self.Q
        v = P - Q
        sp = np.linalg.norm(wind) + 1e-6
        # 湍流：空间相干的正弦场
        ph = self.phase + np.arange(self.L)[None, :] * 0.55
        tb = np.stack([np.sin(t * 7.1 + ph + P[..., 1] * 0.13), 0.6 * np.sin(t * 5.3 + ph * 1.7 + P[..., 0] * 0.11),
                       np.sin(t * 6.3 + ph * 1.3 + P[..., 2] * 0.12)], -1)
        gust = 1 + 0.35 * math.sin(t * 1.1) + 0.2 * math.sin(t * 2.9 + 1)
        wv = wind[None, None] * gust * self.wk + tb * (0.22 * sp + 25) * self.turb
        acc = np.array([0, -560. * self.grav, 0]) + self.drag * (wv - v / dt)
        self.Q = P.copy()
        P = P + v * self.damp + acc * dt * dt
        P[:, 0] = anc
        seg = self.seg; st = self.stiff
        for j in range(1, self.L):
            tgt = P[:, j - 1] + rest[:, j - 1] * seg[:, j - 1:j]
            P[:, j] += (tgt - P[:, j]) * st[:, j:j + 1]
            for (a, b, r) in cols:
                ab = b - a; tt = np.clip(((P[:, j] - a) @ ab) / max(ab @ ab, 1e-9), 0, 1)
                cl = a + tt[:, None] * ab; d = P[:, j] - cl; dist = np.linalg.norm(d, axis=-1)
                m = dist < r
                if m.any(): P[m, j] = cl[m] + d[m] / np.maximum(dist[m], 1e-6)[:, None] * r
            d = P[:, j] - P[:, j - 1]
            P[:, j] = P[:, j - 1] + d / np.maximum(np.linalg.norm(d, axis=-1, keepdims=True), 1e-9) * seg[:, j - 1:j]
        if self.ring > 0 and self.ring_rest is not None:
            for _ in range(2):
                d = np.roll(P, -1, 0) - P; ln = np.linalg.norm(d, axis=-1, keepdims=True)
                corr = (ln - self.ring_rest[..., None]) / np.maximum(ln, 1e-9) * d * 0.5 * self.ring
                corr[:, 0] = 0
                P = P + corr - np.roll(corr, 1, 0) * 1.0
                P[:, 0] = anc
        P[..., 1] = np.maximum(P[..., 1], ground)
        self.P = P

# 侧脸轮廓（头部系 z 前, y 上），额—眉骨—鼻—唇—下巴—颌
HEAD_PROFILE = [(-1.0, 5.6), (3.6, 5.6), (5.0, 3.8), (5.7, 1.6), (6.0, 0.9), (5.55, 0.15), (6.3, -1.0), (7.35, -2.35),
                (6.9, -2.75), (6.05, -2.95), (6.3, -3.55), (6.05, -4.05), (6.2, -4.45), (5.7, -5.0), (5.95, -5.9),
                (5.6, -6.6), (4.2, -7.1), (1.5, -6.2), (-0.5, -4.6), (-1.5, -1.0)]

# ============================================================== 刀客「鬼屠」
HAIR_V3 = True        # v3 发型/脸型（2026-11-09，按设定图）；False 回到 v2
HAIR_V4 = True        # v4（需 HAIR_V3）：细发丝发片、马尾下垂、侧脸收鬓、体积脸、琥珀瞳；False = v3
PONY4 = dict(wk=0.55, turb=0.45, grav=1.25, drag=2.8, damp=0.93)   # v4 马尾物理：风力系数、湍流、重力倍数、阻力
HAIR_DETAIL = 1.0     # v4 发丝密度档位（每束细丝数 ×）：全片可降到 0.5 提速；0.3 为最低可读档
VIEWS = {'back': 0., 'back3q': 35., '3q': 55., 'side': 90., 'front3q': 135., 'front': 180.}

class Swordsman:
    """程序化刀客「鬼屠」：高马尾+乱发碎发、交领长袍、宽皮腰封、腰前暗红长带(流苏)、两条朱红飘带、宽袖、皮护腕、长靴、唐刀。"""
    def __init__(self, seed=0, view='side', hair=1.0, ribbons=True):
        self.rng = np.random.default_rng(seed); rng = self.rng
        self.seed = seed
        self.view = view; self.ribbons = ribbons; self.hair = hair
        self.t_last = None; self.c = None; self.sk = None; self.flip = False
        self.edge_sign = 1.0
        # ---- 头发定义（头部系，原点在头心 Hc）
        nP = int(11 * hair)                    # 马尾束
        self.hair_defs = []
        self.ponytail = Chains(nP, 14, rng.uniform(2.3, 3.0, nP), drag=5.0, damp=0.975,
                               stiff=np.outer(np.ones(nP), np.r_[0, 0.5, 0.3, 0.15, 0.06, np.full(9, 0.012)]))
        self.pt_spread = rng.normal(0, 1, (nP, 2))
        self.pt_w = rng.uniform(0.9, 1.6, nP)
        # 乱发长绺（两侧、后脑）
        nL = int(14 * hair)
        th = rng.uniform(-1, 1, nL) * 95 * D2R           # 绕头 y 轴角，0=后脑
        nf = max(2, nL // 6)
        th[:nf] = rng.choice([-1, 1], nf) * rng.uniform(96, 108, nf) * D2R   # 鬓角垂到脸侧的几绺
        self.lock_anchor = np.stack([np.sin(th) * 5.0, rng.uniform(3.5, 6.0, nL), -np.cos(th) * 4.8 - 0.6], 1)
        self.lock_dir = _nrm(np.stack([np.sin(th) * 0.35, -np.ones(nL), -np.cos(th) * 0.35], 1))
        self.locks = Chains(nL, 7, rng.uniform(2.6, 4.0, nL), drag=6.5, damp=0.97,
                            stiff=np.outer(np.ones(nL), 0.35 * (1 - np.linspace(0, 1, 7)) ** 2 + 0.01))
        self.lock_w = rng.uniform(0.6, 1.1, nL); self.lock_ph = rng.uniform(0, 6.28, nL)
        # 额前碎发
        nB = int(9 * hair)
        bx = np.linspace(-4.2, 4.2, nB) + rng.normal(0, 0.4, nB)
        self.bang_anchor = np.stack([bx, 5.4 - np.abs(bx) * 0.25, 3.6 + rng.normal(0, .3, nB)], 1)
        self.bang_dir = _nrm(np.stack([bx * 0.12 + rng.normal(0, .12, nB), -np.ones(nB), 0.75 * np.ones(nB)], 1))
        self.bangs = Chains(nB, 6, rng.uniform(1.7, 2.6, nB), drag=7.0, damp=0.96,
                            stiff=np.outer(np.ones(nB), 0.45 * (1 - np.linspace(0, 1, 6)) ** 1.5 + 0.02))
        # 飞丝（极细，风中最活）
        nF = int(22 * hair)
        self.fly_src = rng.integers(0, 3, nF)            # 0=马尾根 1=头顶 2=鬓
        self.fly = Chains(nF, 6, rng.uniform(1.4, 2.6, nF), drag=14.0, damp=0.96, stiff=0.04)
        self.fly_off = rng.normal(0, 1, (nF, 3)) * [3.5, 1.5, 3.0]
        # 裙摆（腰下一圈 16 条链）
        nS = 18; self.nS = nS
        ang = np.linspace(0, 2 * math.pi, nS, endpoint=False)
        self.skirt_ring = np.stack([np.sin(ang) * 10.2, np.full(nS, 3.2), np.cos(ang) * 7.0], 1)
        self.skirt_out = np.stack([np.sin(ang), np.zeros(nS), np.cos(ang) * 0.8], 1)
        Ls = 9
        self.skirt = Chains(nS, Ls, 42.0 / (Ls - 1), drag=2.2, damp=0.95, ring=0.6,
                            stiff=np.outer(np.ones(nS), 0.10 * (1 - np.linspace(0, 1, Ls)) + 0.03))
        self.pleat = rng.uniform(0.75, 1.2, nS)
        # 袖（每臂 4 条下垂链）
        self.sleeve = {s: Chains(4, 4, np.array([[4.5, 3.5, 2.5], [6.5, 4.5, 3.0], [7.5, 5.0, 2.5], [4.5, 3., 1.5]]),
                                 drag=4.0, damp=0.95, stiff=0.12) for s in 'lr'}
        # 腰带：两条朱红飘带（后腰结）+ 腰前暗红长带
        self.rib = Chains(2, 16, np.array([2.7, 2.3]), drag=9.0, damp=0.975,
                          stiff=np.outer(np.ones(2), 0.25 * (1 - np.linspace(0, 1, 16)) ** 3 + 0.004))
        self.band = Chains(1, 12, 3.2, drag=3.0, damp=0.96, stiff=np.outer(np.ones(1), 0.3 * (1 - np.linspace(0, 1, 12)) ** 2 + 0.01))
        self.tex = noise_tex(1024, seed=7, base=10, octaves=6)
        self.tex2 = noise_tex(512, seed=3, base=40, octaves=3)
        self.v4 = bool(HAIR_V3 and HAIR_V4)
        if HAIR_V3: self._hair_v3()

    def _hair_v3(self):
        """v3 发型（按设定图 lib/ref/guitu_hero_ref.py）：高马尾（先上扬再垂落、过腰、梢散）、中分刘海发帘 + 垂过眼前的几缕、
        鬓边垂到胸前的长发。独立随机数，不扰动衣物等其他随机量。"""
        rng = np.random.default_rng(self.seed * 7 + 1013); hair = self.hair
        # 高马尾：16 节，根部短节做出上扬发髻弧，后面长节垂落；总长 ≈ 50 单位（头顶 → 腰下）
        nP = max(8, int(15 * hair)); L = 16
        segs = np.r_[1.4, 1.7, 2.1, np.full(L - 4, 3.75)]
        if self.v4:      # v4：更长（≈63 单位，静风时梢过腰）、更多束、马尾受风系数小 → 风大时向后斜飘而不是横飞
            nP = max(10, int(18 * hair)); L = 18
            segs = np.r_[1.4, 1.7, 2.1, np.full(L - 4, 4.1)]
        self.ponytail = Chains(nP, L, np.outer(rng.uniform(0.86, 1.08, nP), segs), drag=2.5, damp=0.975,
                               stiff=np.outer(np.ones(nP), np.r_[0, 0.7, 0.45, 0.25, 0.10, 0.04, np.full(L - 6, 0.007)]))
        if self.v4:
            self.ponytail.wk = PONY4['wk']; self.ponytail.turb = PONY4['turb']; self.ponytail.grav = PONY4['grav']
            self.ponytail.drag = PONY4['drag']; self.ponytail.damp = PONY4['damp']
        self.pt_spread = rng.normal(0, 1, (nP, 2))
        self.pt_w = rng.uniform(0.7, 1.55, nP)
        self.pt_scatter = rng.normal(0, 1, (nP, 3))                    # 发梢散乱方向
        # 刘海：中分。0..2*nc-1 = 两侧发帘（从分缝斜扫到颧骨），其后 3 缕垂过眼前
        nc = 4; rows = []
        for sg in (1, -1):
            for k in range(nc):
                u = k / (nc - 1)
                rows.append(dict(sg=sg, a=[sg * (0.35 + 1.25 * u), 6.55 - 0.55 * u, 1.6 + 1.1 * u], kind='curtain', u=u,
                                 w=1.25 - 0.25 * u))
        for sg, x0, w in ((1, 0.55, 0.9), (-1, -0.7, 0.8), (1, 0.15, 0.6)):
            rows.append(dict(sg=sg, a=[x0, 6.6, 2.0], kind='eye', u=0, w=w))
        self.bang_rows = rows
        nB = len(rows); Lb = 7
        self.bang_anchor = np.array([r['a'] for r in rows], float)
        self.bang_len = np.array([2.05 if r['kind'] == 'curtain' else 2.15 for r in rows]) * rng.uniform(0.92, 1.08, nB)
        self.bangs = Chains(nB, Lb, self.bang_len, drag=6.0, damp=0.95,
                            stiff=np.outer(np.ones(nB), 0.55 * (1 - np.linspace(0, 1, Lb)) ** 1.2 + 0.06))
        self.bang_w = np.array([r['w'] for r in rows])
        if self.v4:      # 侧脸露颧骨：发帘收窄；过眼发缕只剩几根细丝
            self.bang_w = np.array([r['w'] * (0.88 if r['kind'] == 'curtain' else 0.55) for r in rows])
        # 鬓发：两侧各 2 绺，耳前垂到胸前
        ns = 4
        self.side_anchor = np.array([[4.4, 2.4, 0.9], [4.8, 1.6, -0.6], [-4.4, 2.4, 0.9], [-4.8, 1.6, -0.6]])
        self.sidelocks = Chains(ns, 9, rng.uniform(2.5, 2.9, ns), drag=6.0, damp=0.965,
                                stiff=np.outer(np.ones(ns), 0.30 * (1 - np.linspace(0, 1, 9)) ** 2 + 0.02))
        self.side_w = np.array([1.15, 0.95, 1.15, 0.95])
        if self.v4:      # 鬓发后移到耳前、变窄 → 侧脸露出颧骨与下颌线
            self.side_anchor = np.array([[4.5, 2.2, 0.1], [4.7, 1.4, -1.3], [-4.5, 2.2, 0.1], [-4.7, 1.4, -1.3]])
            self.side_w = np.array([0.8, 0.7, 0.8, 0.7])

    # ---------------------------------------------------- 骨骼
    def _skeleton(self, c):
        S = {}
        Rp = _rot(c['ryaw'], c['rp'], c['rr'])
        Pp = np.array([c['rx'], 51 + c['ry'], c['rz']])
        Cw = Pp + Rp @ [0, 8, 0]
        Rc = Rp @ _rot(c['sy'], c['sp'], c['sr'])
        N = Cw + Rc @ [0, 24, 0]
        Rh = Rc @ _rot(c['hy'], c['hp'], c['hr'])
        Hc = N + Rh @ [0, 9.4 if getattr(self, 'v4', False) else 10.2, 0.6]     # v4 颈缩短
        S.update(Rp=Rp, Pp=Pp, Cw=Cw, Rc=Rc, N=N, Rh=Rh, Hc=Hc)
        Ryaw = _ry(c['ryaw'] * D2R); fwd = Ryaw @ [0, 0, 1]; up = np.array([0, 1., 0])
        off = np.array([c['rx'], 0, c['rz']])
        for s, sg in (('l', -1), ('r', 1)):
            Hj = Pp + Rp @ [sg * 5.5, -1, 0]
            F = Ryaw @ np.asarray(c[s + 'f']) + off
            pole = Rp @ [sg * 0.2, 0, 1]
            Kn, A = _ik(Hj, F, 24, 23, pole)
            fa = c[s + 'fa'] * D2R
            def fp(f, u):
                return A + fwd * (f * math.cos(fa) + u * math.sin(fa)) + up * (-f * math.sin(fa) + u * math.cos(fa))
            S[s + 'hip'] = Hj; S[s + 'knee'] = Kn; S[s + 'ank'] = A
            S[s + 'toe'] = fp(8.0, -3.4); S[s + 'heel'] = fp(-2.6, -3.6); S[s + 'ball'] = fp(5.5, -3.6)
            S[s + 'sh'] = Cw + Rc @ [sg * 9.8, 22.0, -0.5]
        # 刀鞘（左胯）
        M = Pp + Rp @ [-9.3, 3.0, 3.6]; sd = Rp @ _nrm(np.array([-0.12, -0.68, -1.0]))
        S['sc_m'] = M; S['sc_d'] = sd
        hilt = M - sd * 5.5
        # 右手
        bd = Rp @ _sdir(c['se'], c['sa'])
        grab = c.get('grab', 0.)
        T = Cw + Rp @ np.asarray(c['rh'])
        if grab > 0:
            T = T * (1 - grab) + (hilt - sd * 0.0 - Rp @ [0, 0, 2.0]) * grab
            bd = _nrm(bd * (1 - grab) + sd * grab)
        E, Wr = _ik(S['rsh'], T, 16.5, 14.0, Rp @ _nrm(np.asarray(c['rpole'], float)))
        fd = _nrm(Wr - E); fist = Wr + fd * 2.2
        S.update(rel=E, rwr=Wr, rfist=fist)
        # 左手（双手握时吸附刀柄）
        TL = Cw + Rp @ np.asarray(c['lh'])
        if c['two'] > 0 and c['drawn'] >= 0.5:
            TL = TL * (1 - c['two']) + (fist - bd * 5.0 - fd * 1.5) * c['two']
        El, Wl = _ik(S['lsh'], TL, 16.5, 14.0, Rp @ _nrm(np.asarray(c['lpole'], float)))
        S.update(lel=El, lwr=Wl, lfist=Wl + _nrm(Wl - El) * 2.2)
        if c['drawn'] >= 0.5 and grab < 0.9:
            g0 = fist + bd * 3.2
            if grab > 0: g0 = g0 * (1 - grab) + (M - sd * 0.6) * grab
            S['guard'] = g0; S['tip'] = g0 + bd * 45; S['pommel'] = g0 - bd * 13.0; S['bd'] = bd
            S['sheathed'] = False
        else:
            S['guard'] = M - sd * 0.6; S['pommel'] = M - sd * 13.5; S['tip'] = M + sd * 44; S['bd'] = sd
            S['sheathed'] = True
        return S

    def _anchors(self, S):
        Rh, Hc, Rp, Pp, Rc = S['Rh'], S['Hc'], S['Rp'], S['Pp'], S['Rc']
        out = {}
        tie = Hc + Rh @ [0, 6.2, -3.2]; S['tie'] = tie
        n = self.ponytail.C
        sp = self.pt_spread
        out['pt'] = (np.repeat(tie[None], n, 0) + (Rh @ np.stack([sp[:, 0] * 0.6, sp[:, 1] * 0.3, np.zeros(n)], 1).T).T)
        a = (62 + 118 * np.linspace(0, 1, 13) ** 0.5) * D2R
        base = np.stack([np.zeros(13), np.cos(a), -np.sin(a)], 1)
        rd = np.repeat(base[None], n, 0)
        rd[..., 0] += sp[:, :1] * 0.05 * np.linspace(1, 0.4, 13)[None]
        out['pt_rest'] = _nrm(rd @ Rh.T)
        out['lk'] = Hc + self.lock_anchor @ Rh.T
        wv_ = np.sin(np.arange(6)[None] * 1.1 + self.lock_ph[:, None]) * 0.35
        ld = np.repeat(self.lock_dir[:, None], 6, 1); ld[..., 0] += wv_; ld[..., 2] += wv_ * 0.6; ld[:, :2] += self.lock_dir[:, None] * [1.3, 0, 1.3] * [1, 0, 1]; ld[..., 1] -= np.linspace(0, 1.2, 6)[None]
        out['lk_rest'] = _nrm(ld @ Rh.T)
        out['bg'] = Hc + self.bang_anchor @ Rh.T
        bd = np.repeat(self.bang_dir[:, None], 5, 1); bd[..., 2] -= np.linspace(0, 1.3, 5)[None]
        out['bg_rest'] = _nrm(bd @ Rh.T)
        src = np.stack([tie, Hc + Rh @ [0, 6.4, 0.5], Hc + Rh @ [0, 2, -4]])[self.fly_src]
        fl = src + self.fly_off @ Rh.T * 0.5
        dv = fl - Hc; out['fl'] = Hc + dv / np.maximum(np.linalg.norm(dv, axis=1, keepdims=True), 1e-6) * 6.3   # 贴头皮
        fd = np.repeat((self.fly_off * [1, 0.2, 1] + [0, 0, -0.6])[:, None], 5, 1) @ Rh.T
        fd[..., 1] -= 0.9                                     # 飞丝受重力，不随低头竖起
        out['fl_rest'] = _nrm(fd)
        # 裙
        out['sk'] = Pp + self.skirt_ring @ Rp.T
        L = self.skirt.L
        down = np.array([0, -1., 0])
        flare = np.linspace(0.16, 0.30, L - 1)
        sr = down[None, None] + (self.skirt_out @ Rp.T)[:, None] * flare[None, :, None]
        out['sk_rest'] = _nrm(sr)
        # 袖
        for s in 'lr':
            sh, el, wr = S[s + 'sh'], S[s + 'el'], S[s + 'wr']
            bk = Rp @ [0, 0, -1.]; ad = _nrm(wr - sh); bk = _nrm(bk - ad * (bk @ ad) + 1e-6)
            A = np.stack([sh + (el - sh) * 0.45, sh + (el - sh) * 0.85, el + (wr - el) * 0.15, el + (wr - el) * 0.38])
            A = A + bk[None] * np.array([1.5, 3.0, 3.2, 2.0])[:, None]
            out['sl' + s] = A
            out['sl' + s + '_rest'] = np.repeat(np.array([[0, -1., 0]]), 4 * 3, 0).reshape(4, 3, 3)
        # 飘带（后腰结，偏左）
        kn = Pp + Rp @ [-3.0, 7.4, -7.2]
        out['rb'] = np.stack([kn, kn + Rp @ [1.2, -0.6, 0]])
        rr = np.repeat(np.array([[0, -0.6, -0.8]]), 15, 0); rr[:, 1] -= np.linspace(0, 1.4, 15)
        out['rb_rest'] = np.repeat(_nrm(rr @ Rp.T)[None], 2, 0)
        out['bd'] = (Pp + Rp @ [2.0, 5.2, 7.3])[None]
        out['bd_rest'] = np.repeat(_nrm(np.array([[0, -1., 0.08]]) @ Rp.T)[None], 11, 1)
        if HAIR_V3 and hasattr(self, 'sidelocks'): out = self._anchors_v3(S, out)
        return out

    def _anchors_v3(self, S, out):
        Rh, Hc = S['Rh'], S['Hc']
        tie = Hc + Rh @ [0, 7.15, -2.3]; S['tie'] = tie
        n = self.ponytail.C; L = self.ponytail.L; sp = self.pt_spread
        out['pt'] = (np.repeat(tie[None], n, 0) + (Rh @ np.stack([sp[:, 0] * 0.55, sp[:, 1] * 0.25, sp[:, 1] * 0.2], 1).T).T)
        u = np.linspace(0, 1, L - 1)
        a = (28 + 152 * u ** 0.3) * D2R                     # 先向上（发髻弧）再折向后、垂下
        rd = np.repeat(np.stack([np.zeros(L - 1), np.cos(a), -np.sin(a)], 1)[None], n, 0)
        sc_ = self.pt_scatter
        g = (u ** 1.6)[None]                                   # 越到发梢越散
        rd[..., 0] += sp[:, :1] * 0.06 + sc_[:, :1] * (0.12 if self.v4 else 0.30) * g
        rd[..., 2] += sc_[:, 2:3] * 0.18 * g
        out['pt_rest'] = _nrm(rd @ Rh.T)
        out['bg'] = Hc + self.bang_anchor @ Rh.T
        nB, Lb = self.bangs.C, self.bangs.L
        bd = np.zeros((nB, Lb - 1, 3)); v = np.linspace(0, 1, Lb - 1)
        for i, r in enumerate(self.bang_rows):
            sg = r['sg']
            if r['kind'] == 'curtain':
                # 从分缝向外、向前扫出，再沿额角—颧骨垂下（外侧发帘更早转下）
                out_ = np.clip(1.0 - v * (1.6 + 0.6 * r['u']), 0, 1)
                bd[i] = np.stack([sg * (0.12 + 0.6 * out_), -0.25 - 1.0 * (1 - out_), 0.6 * out_ + 0.12 * (1 - out_) - 0.1 * r['u']], 1)
            else:
                # 垂过眼前：先向前，再几乎竖直下垂、略向外，末端贴脸前
                bd[i] = np.stack([sg * (0.10 + 0.14 * v), -0.35 - 1.0 * np.clip(v * 2.2, 0, 1), 0.85 * (1 - v) ** 2 - 0.12], 1)
        out['bg_rest'] = _nrm(bd @ Rh.T)
        out['sdl'] = Hc + self.side_anchor @ Rh.T
        ns, Ls = self.sidelocks.C, self.sidelocks.L
        sd = np.zeros((ns, Ls - 1, 3)); w = np.linspace(0, 1, Ls - 1)
        for i in range(ns):
            sg = np.sign(self.side_anchor[i, 0])
            if self.v4: sd[i] = np.stack([sg * (0.16 - 0.04 * w), -np.ones(Ls - 1), 0.05 - 0.20 * w], 1)
            else: sd[i] = np.stack([sg * (0.12 - 0.05 * w), -np.ones(Ls - 1), 0.30 - 0.15 * w + 0.12 * (i % 2 == 0)], 1)
        sd = _nrm(sd @ Rh.T)
        # 低头/回头时鬓发受重力：rest 与世界向下混合
        sd = _nrm(sd * 0.55 + np.array([0, -1.0, 0]) * 0.45 + (S['Rc'] @ [0, 0, 1.0]) * 0.18)
        out['sdl_rest'] = sd
        return out

    def _colliders(self, S):
        cols = [(S['Hc'] + [0, -1, 0], S['Hc'] + [0, 1, 0], 6.6), (S['Pp'] + [0, 2, 0], S['N'] - [0, 4, 0], 8.0),
                (S['lsh'], S['rsh'], 4.5)]
        legs = []
        for s in 'lr':
            legs += [(S[s + 'hip'], S[s + 'knee'], 5.0), (S[s + 'knee'], S[s + 'ank'], 3.8)]
        return cols, legs

    def _groups(self, S, A):
        cols, legs = self._colliders(S)
        g = [(self.ponytail, A['pt'], A['pt_rest'], cols), (self.locks, A['lk'], A['lk_rest'], cols[:2]),
             (self.bangs, A['bg'], A['bg_rest'], []), (self.fly, A['fl'], A['fl_rest'], []),
             (self.skirt, A['sk'], A['sk_rest'], legs),
             (self.sleeve['l'], A['sll'], A['sll_rest'], []), (self.sleeve['r'], A['slr'], A['slr_rest'], [])]
        if HAIR_V3 and hasattr(self, 'sidelocks'):
            Rh, Hc = S['Rh'], S['Hc']
            facecol = (Hc + Rh @ [0, -3.5, 0.9], Hc + Rh @ [0, 3.5, 0.6], 4.9)    # 脸前小胶囊：刘海贴脸但不穿脸
            g[2] = (self.bangs, A['bg'], A['bg_rest'], [facecol])
            g.append((self.sidelocks, A['sdl'], A['sdl_rest'], [(Hc + Rh @ [0, -2, 0], Hc + Rh @ [0, 2, 0], 5.3)] + cols[1:3]))
        if self.ribbons: g.append((self.rib, A['rb'], A['rb_rest'], legs + cols[1:2]))
        g.append((self.band, A['bd'], A['bd_rest'], legs))
        return g

    # ---------------------------------------------------- 姿态 + 物理
    def pose(self, action, phase, t, wind=0.0, flip=None, view=None, channels=None, sword=None, travel=None, **over):
        """action: 动作名；phase 0..1（循环动作可>1）；t 绝对时间(秒)，连续调用时布料按 dt 积分；
        wind: 屏幕向右的风速(单位/秒，常用 0–600) 或 (wx,wy)；sword: None/'drawn'/'sheathed' 强制刀状态；
        over: 直接覆盖任意通道（如 hy=30）。返回骨骼 dict。"""
        if flip is not None: self.flip = flip
        if view is not None: self.view = view
        c = dict(channels) if channels is not None else sample_action(action, phase, over)
        c.update({k: v for k, v in over.items() if k in BASE})
        if sword == 'sheathed': c['drawn'] = 0
        elif sword == 'drawn': c['drawn'] = 1
        S = self._skeleton(c)
        A = self._anchors(S)
        th = VIEWS.get(self.view, self.view) if isinstance(self.view, str) else self.view
        th = th * D2R; fs = -1. if self.flip else 1.
        wx, wy = (wind, 0.) if np.isscalar(wind) else wind
        wv = np.array([fs * wx * math.cos(th), -wy, fs * wx * math.sin(th)]) + np.array([0, 0, -1.]) * 0.15 * abs(wx)
        spd = (ACTIONS.get(action, {}).get('speed', 0) if travel is None else travel)
        wv = wv - S['Rp'] @ [0, 0, 1.] * spd
        groups = self._groups(S, A)
        wet = float(over.get('wet', getattr(self, 'wet', 0.0))); self.wet = wet
        for (ch, _, _, _) in groups:
            if not hasattr(ch, 'g0'): ch.g0 = ch.grav; ch.d0 = ch.drag
            ch.grav = ch.g0 * (1 + 1.6 * wet); ch.drag = ch.d0 * (1 - 0.6 * wet)
        need_reset = self.t_last is None or not (0 < t - self.t_last <= 0.2)
        if need_reset:
            for (ch, anc, rest, cl) in groups: ch.reset(anc, rest)
            tt = t - 0.6
            for k in range(48):
                for (ch, anc, rest, cl) in groups: ch.step(1 / 80, anc, rest, wv, tt + k / 80, cl)
            self.prevA = A
        else:
            dtt = t - self.t_last; n = max(1, int(math.ceil(dtt / (1 / 100))))
            pg = self._groups(self.sk, self.prevA)
            for k in range(n):
                u = (k + 1) / n
                for (ch, anc, rest, cl), (_, anc0, _, _) in zip(groups, pg):
                    ch.step(dtt / n, anc0 + (anc - anc0) * u, rest, wv, self.t_last + dtt * u, cl)
            self.prevA = A
        # 湿：甩水珠（从发梢/飘带/袖口/裙摆末端，按末端速度生成）
        if not hasattr(self, 'drops'): self.drops = np.zeros((0, 7))
        if wet > 0 and not need_reset:
            dtt = t - self.t_last; rng = self.rng
            new = []
            for ch in (self.ponytail, self.locks, self.rib, self.skirt, self.sleeve['l'], self.sleeve['r']):
                v = (ch.P[:, -1] - ch.Q[:, -1]) / max(dtt / max(1, int(math.ceil(dtt / 0.01))), 1e-4)
                spd = np.linalg.norm(v, axis=1)
                pr = np.clip(dtt * wet * (spd - 80) / 25, 0, 3)
                for i in np.nonzero(rng.random(len(pr)) < pr)[0]:
                    new.append(np.r_[ch.P[i, -1], v[i] * 0.9 + rng.normal(0, 30, 3), 0.0])
            d = self.drops
            if len(d):
                d[:, 3:6] += np.array([0, -560., 0]) * dtt; d[:, 0:3] += d[:, 3:6] * dtt; d[:, 6] += dtt
                d = d[(d[:, 6] < 0.7) & (d[:, 1] > 0)]
            self.drops = np.vstack([d] + [np.array(new)]) if new else d
        elif need_reset: self.drops = np.zeros((0, 7))
        # 刃口朝向：随刀尖速度
        if self.sk is not None and not S['sheathed'] and not need_reset:
            vt = S['tip'] - self.sk['tip']
            if np.linalg.norm(vt) > 2: self.edge_vel = vt
        self.t_last = t; self.c = c; self.sk = S
        return S

# ---------------------------------------------------- 渲染工具（局部画布，uint8 4 通道：覆盖/色调/朱红/金属）
class _CanvasCV:
    """旧版 cv2 光栅化画布（保留作对比/回退）。"""
    backend = 'cv'
    def __init__(self, h, w):
        self.C = np.zeros((h, w, 4), np.uint8)       # A, tone, red, metal（预乘）
        self.M = np.zeros((h, w, 3), np.uint8)       # 刀身细节：钢色、刃线、热
        self.G = np.zeros((h, w), np.uint8)          # 金饰
        self.D = np.full((h, w), -1e4, np.float32)   # 内轮廓光用深度图（无 AA）
        self.dcur = 0.0
    def poly(self, pts, col, gold=0):
        p = _ip(pts).reshape(-1, 1, 2)
        cv2.fillPoly(self.C, [p], col, cv2.LINE_AA, SH)
        cv2.fillPoly(self.G, [p], gold, cv2.LINE_AA, SH)
        cv2.fillPoly(self.D, [p], self.dcur, cv2.LINE_8, SH)
    def cap(self, a, b, r1, r2, col, gold=0):
        a = np.asarray(a, float); b = np.asarray(b, float)
        d = b - a; L = np.hypot(*d)
        if L < 1e-6:
            self.circ(a, max(r1, r2), col, gold); return
        n = np.array([-d[1], d[0]]) / L
        self.poly(np.array([a + n * r1, b + n * r2, b - n * r2, a - n * r1]), col, gold)
        self.circ(a, r1, col, gold); self.circ(b, r2, col, gold)
    def circ(self, c, r, col, gold=0):
        cc = tuple(int(v) for v in _ip(c)); rr = int(max(r, 0.3) * SHF)
        cv2.circle(self.C, cc, rr, col, -1, cv2.LINE_AA, SH); cv2.circle(self.G, cc, rr, gold, -1, cv2.LINE_AA, SH)
        cv2.circle(self.D, cc, rr, self.dcur, -1, cv2.LINE_8, SH)
    def ell(self, c, ax, ang, col, gold=0):
        cv2.ellipse(self.C, tuple(int(v) for v in _ip(c)), tuple(int(max(v, .3) * SHF) for v in ax), ang, 0, 360, col, -1,
                    cv2.LINE_AA, SH)
        cv2.ellipse(self.G, tuple(int(v) for v in _ip(c)), tuple(int(max(v, .3) * SHF) for v in ax), ang, 0, 360, gold, -1,
                    cv2.LINE_AA, SH)
        cv2.ellipse(self.D, tuple(int(v) for v in _ip(c)), tuple(int(max(v, .3) * SHF) for v in ax), ang, 0, 360, self.dcur, -1,
                    cv2.LINE_8, SH)
    def line(self, a, b, w, col, gold=0):
        if w < 1.6:          # 细线：1px AA，用 tone 衰减模拟更细
            cv2.line(self.C, tuple(int(v) for v in _ip(a)), tuple(int(v) for v in _ip(b)),
                     tuple(int(c * min(1, w / 1.2 + 0.25)) if i == 0 else c for i, c in enumerate(col)), 1, cv2.LINE_AA, SH)
            cv2.line(self.G, tuple(int(v) for v in _ip(a)), tuple(int(v) for v in _ip(b)), gold, 1, cv2.LINE_AA, SH)
        else:
            self.cap(a, b, w / 2, w / 2, col, gold)
    def strand(self, pts, w0, w1, col):
        pts = np.asarray(pts, float)
        if len(pts) >= 3 and w0 > 2.5: pts = _upsample(pts, 3)
        n = len(pts)
        if w0 < 1.3:                                   # 极细：AA 折线
            for k in range(n - 1): self.line(pts[k], pts[k + 1], w0 + (max(w1, 0) - w0) * k / (n - 1), col)
            return
        d = np.gradient(pts, axis=0); nn = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
        u = np.linspace(0, 1, n)
        prof = np.clip(0.55 + 2.2 * u, 0, 1) * (1 - u) ** 0.9 if w1 >= 0 else np.sin(np.pi * np.clip(u * 0.95 + 0.03, 0, 1)) ** 0.7
        w = (max(w1, 0) + (w0 - max(w1, 0)) * prof)[:, None] * 0.5
        poly = np.concatenate([pts + nn * w, (pts - nn * w)[::-1]])
        self.poly(poly, col)
        if col[1] > 0 and n > 3 and w0 > 3.0:          # 发丝光泽线（大尺度才画）
            hl = (255, min(255, col[1] + 45), col[2], 0)
            m0, m1 = n // 5, max(n // 5 + 2, int(n * 0.7))
            off = pts[m0:m1] - nn[m0:m1] * w[m0:m1] * 0.35
            cv2.polylines(self.C, [_ip(off).reshape(-1, 1, 2)], False, hl, 1, cv2.LINE_AA, SH)
    def ribbon(self, pts, widths, normals, cols):
        for k in range(len(pts) - 1):
            a, b = pts[k], pts[k + 1]
            q = np.array([a + normals[k] * widths[k], b + normals[k + 1] * widths[k + 1],
                          b - normals[k + 1] * widths[k + 1], a - normals[k] * widths[k]])
            p = _ip(q).reshape(-1, 1, 2)
            cv2.fillConvexPoly(self.C, p, cols[k], cv2.LINE_AA, SH)
            cv2.fillConvexPoly(self.G, p, 0, cv2.LINE_AA, SH)
            cv2.fillConvexPoly(self.D, p, self.dcur, cv2.LINE_8, SH)

    # 与 sk.SkCanvas 对齐的通用接口
    def fill(self, target, pts, val, depth=False):
        p = _ip(pts).reshape(-1, 1, 2); arr = getattr(self, target)
        cv2.fillPoly(arr, [p], val if np.ndim(val) else float(val) if arr.dtype != np.uint8 else int(val), cv2.LINE_AA, SH)
        if depth: cv2.fillPoly(self.D, [p], self.dcur, cv2.LINE_8, SH)
    def stroke(self, target, pts, val, width, closed=False):
        cv2.polylines(getattr(self, target), [_ip(pts).reshape(-1, 1, 2)], closed, val, max(1, int(width + 0.5)), cv2.LINE_AA, SH)
    def fill_ell(self, target, c, ax, ang, val):
        cv2.ellipse(getattr(self, target), tuple(int(v) for v in _ip(c)), (int(ax[0] * SHF) + 1, int(ax[1] * SHF)), ang, 0, 360, val,
                    -1, cv2.LINE_AA, SH)


# ---- 绘制后端：默认 skia 矢量（sk.SkCanvas），无 skia 时回退 cv2。rig.set_backend('cv'|'skia') 可切换做前后对比。
try:
    import sk as _sk
except Exception:
    try:
        from . import sk as _sk
    except Exception:
        _sk = None
BACKEND = 'skia' if (_sk is not None and _sk.HAVE_SKIA) else 'cv'
_Canvas = _sk.SkCanvas if BACKEND == 'skia' else _CanvasCV
def set_backend(name):
    """'skia'（默认，矢量路径）或 'cv'（旧 cv2 光栅）。影响之后所有 draw 调用。"""
    global BACKEND, _Canvas
    if name == 'skia' and (_sk is None or not _sk.HAVE_SKIA): raise RuntimeError('skia-python 不可用')
    BACKEND = name; _Canvas = _sk.SkCanvas if name == 'skia' else _CanvasCV

def _upsample(p, k):
    """Catmull-Rom 加密折线点"""
    p = np.asarray(p, float); n = len(p)
    P = np.vstack([p[:1] * 2 - p[1:2], p, p[-1:] * 2 - p[-2:-1]])
    u = np.linspace(0, 1, k, endpoint=False)[:, None]
    out = []
    for i in range(n - 1):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        out.append(0.5 * (2 * p1 + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    out.append(p[-1:])
    return np.vstack(out)

def _blur_ds(a, sig):
    """大半径高斯：降采样后模糊再放大（快）"""
    if sig < 4: return cv2.GaussianBlur(a, (0, 0), sig)
    k = int(min(8, sig // 2)); h, w = a.shape[:2]
    sm = cv2.resize(a, (max(1, w // k), max(1, h // k)), interpolation=cv2.INTER_AREA)
    return cv2.resize(cv2.GaussianBlur(sm, (0, 0), sig / k), (w, h), interpolation=cv2.INTER_LINEAR)

def _shift(a, dx, dy):
    return cv2.warpAffine(a, np.float32([[1, 0, dx], [0, 1, dy]]), (a.shape[1], a.shape[0]), borderMode=cv2.BORDER_CONSTANT)

# ============================================================== v2 体积光照（所有角色共用）
FORM = dict(on=True, key=0.62, shadow=0.42, ao=0.5, terminator=0.18)
def set_form(**kw):
    """v2 体积光照开关/参数：rig.set_form(on=False) 回到 v1 平涂。key=受光面提亮, shadow=背光面压暗, ao=遮蔽强度"""
    FORM.update(kw)

def _form(A, D, px, ldir=(-0.7, -0.7), depth_thr=2.5, lz=0.42, flat=None):
    """从覆盖率 A 与分层深度 D 推出“鼓起”的伪法线（每个部件按深度断层各自成体积），返回 (亮度乘子, AO)。
    px: 体积半径(像素)；ldir: 屏幕光向（指向光源）。二值化的明暗交界（赛璐璐）+ 柔和过渡 + 层间接触阴影。"""
    h, w = A.shape
    if not FORM['on'] or h < 6 or w < 6:
        one = np.ones((h, w), np.float32); return one, one
    inside = A > 0.5
    Dv = np.where(inside, D, np.float32(-1e4)).astype(np.float32)
    ds = int(max(1, min(6, px // 14)))
    if ds > 1:
        Ai = cv2.resize(inside.astype(np.uint8), (max(1, w // ds), max(1, h // ds)), interpolation=cv2.INTER_NEAREST)
        Dd = cv2.resize(Dv, (Ai.shape[1], Ai.shape[0]), interpolation=cv2.INTER_NEAREST)
    else:
        Ai = inside.astype(np.uint8); Dd = Dv
    ed = Ai == 0
    jx = np.abs(np.diff(Dd, axis=1)) > depth_thr; jy = np.abs(np.diff(Dd, axis=0)) > depth_thr
    # 只把“较远”的一侧当边：近处部件完整鼓起，远处部件在被遮挡处下沉
    fx = jx & (Dd[:, 1:] < Dd[:, :-1]); bx = jx & ~fx
    fy = jy & (Dd[1:] < Dd[:-1]); by = jy & ~fy
    ed[:, 1:] |= fx; ed[:, :-1] |= bx; ed[1:] |= fy; ed[:-1] |= by
    dist = cv2.distanceTransform((~ed).astype(np.uint8), cv2.DIST_L2, 3) * ds
    u = np.clip(dist / max(px, 1.0), 0, 1)
    hgt = np.sqrt(1 - (1 - u) ** 2).astype(np.float32) * px
    hgt = cv2.GaussianBlur(hgt, (0, 0), max(0.8, px / ds * 0.08))
    gx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3) / (8 * ds); gy = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3) / (8 * ds)
    lx, ly = ldir; ln = math.hypot(lx, ly) + 1e-6; lx, ly = lx / ln * (1 - lz * lz) ** 0.5, ly / ln * (1 - lz * lz) ** 0.5
    nz = 1.0
    nn = np.sqrt(gx * gx + gy * gy + nz * nz)
    ndl = (-gx * lx - gy * ly + nz * lz) / nn
    tm = FORM['terminator']
    cel = np.clip((ndl - (lz - 0.05)) / tm + 0.5, 0, 1); cel = cel * cel * (3 - 2 * cel)
    soft = np.clip(ndl, 0, 1)
    mul = (1 - FORM['shadow']) + FORM['shadow'] * 0.35 * soft + (FORM['shadow'] * 0.65 + FORM['key']) * cel
    # 接触阴影：附近有更近的部件 → 被遮蔽
    r = max(2, int(px * 0.5 / ds))
    Dn = cv2.dilate(Dd, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    occ = np.clip((Dn - Dd - depth_thr) / 6.0, 0, 1) * (Ai > 0)
    occ = cv2.GaussianBlur(occ.astype(np.float32), (0, 0), r * 0.6)
    # 轮廓内缘环境遮蔽（体积边缘略暗、中心通透）
    edge_ao = 1 - 0.25 * (1 - np.clip(dist / max(px * 0.5, 1), 0, 1))
    ao = (1 - FORM['ao'] * occ) * edge_ao
    if ds > 1:
        mul = cv2.resize(mul.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        ao = cv2.resize(ao.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    return mul.astype(np.float32), ao.astype(np.float32)

def _col(tone, red=0, metal=0):
    return (255, int(np.clip(tone, 0, 255)), int(np.clip(red, 0, 255)), int(metal))

def _sw_draw(self, fr, x, y, scale, flip=None, rim_color=(0.80, 0.86, 1.0), rim_dir=(-0.75, -0.65), rim=1.0, lift=1.0,
             alpha=1.0, heat=0.0, shine=None, blade_glow=1.0, ink=None, return_masks=False, sword_visible=True,
             detail=1.0, glint=0.0):
    if self.sk is None: raise RuntimeError('先调用 pose()')
    S = self.sk
    if flip is not None: self.flip = flip
    fs = -1. if self.flip else 1.
    th = (VIEWS.get(self.view, self.view) if isinstance(self.view, str) else self.view) * D2R
    ct, st = math.cos(th), math.sin(th)
    sc = scale / 100.0
    # 局部画布范围
    allp = [S[k] for k in ('Hc', 'tip', 'pommel', 'ltoe', 'rtoe', 'lheel', 'rheel', 'lfist', 'rfist', 'tie', 'Pp')]
    allp = np.vstack([np.array(allp)] + [g.P.reshape(-1, 3) for g in
                      (self.ponytail, self.locks, self.skirt, self.rib, self.band, self.fly, self.bangs)])
    X = allp[:, 0] * ct + allp[:, 2] * st
    U = x + fs * X * sc; V = y - allp[:, 1] * sc
    mg = scale * 0.06 + 8
    x0 = int(max(0, math.floor(U.min() - mg))); x1 = int(min(fr.shape[1], math.ceil(U.max() + mg)))
    y0 = int(max(0, math.floor(V.min() - mg))); y1 = int(min(fr.shape[0], math.ceil(V.max() + mg)))
    info = dict(bbox=(x0, y0, x1, y1))
    def P2(Pw):
        Pw = np.asarray(Pw, float)
        Xs = Pw[..., 0] * ct + Pw[..., 2] * st
        return np.stack([x + fs * Xs * sc - x0, y - Pw[..., 1] * sc - y0], -1)
    def DP(Pw):
        Pw = np.asarray(Pw, float); return Pw[..., 0] * st - Pw[..., 2] * ct
    def scr(Pw):
        q = P2(Pw); return (float(q[0] + x0), float(q[1] + y0))
    info['tip'] = scr(S['tip']); info['guard'] = scr(S['guard']); info['hand'] = scr(S['rfist'])
    info['head'] = scr(S['Hc']); info['pommel'] = scr(S['pommel'])
    if x1 - x0 < 4 or y1 - y0 < 4:
        return fr, info
    cv_ = _Canvas(y1 - y0, x1 - x0)
    # 光照（模型空间）：屏幕光向 + 来自背后
    rd = np.array(rim_dir, float); rd /= max(np.linalg.norm(rd), 1e-6)
    L3 = np.array([fs * rd[0] * ct, -rd[1], fs * rd[0] * st]) * 0.8 - np.array([st, 0, -ct]) * 0.6
    L3 /= np.linalg.norm(L3)
    cen = DP(S['Pp'])
    E = []                                           # (depth, fn)
    def far(d): return 0.62 if d < cen - 1.5 else 1.0
    base = 70
    # ---- 腿 / 靴
    for s in 'lr':
        hip, kn, an = S[s + 'hip'], S[s + 'knee'], S[s + 'ank']
        d = DP(kn); f = far(d)
        q = P2(np.array([hip, kn, an, S[s + 'toe'], S[s + 'heel'], S[s + 'ball']]))
        def legfn(q=q, f=f):
            cv_.cap(q[0], q[1], 4.4 * sc, 3.4 * sc, _col(base * 0.8 * f))
            cv_.cap(q[1], q[2], 3.3 * sc, 2.4 * sc, _col(base * 0.8 * f))
            bt = q[1] + (q[2] - q[1]) * 0.28
            cv_.cap(bt, q[2], 3.1 * sc, 2.7 * sc, _col(100 * f))                    # 长靴
            cv_.poly(np.array([q[2] + (q[4] - q[2]) * 0.2 + [0, -1.6 * sc], q[4], q[5], q[3], q[2] + (q[3] - q[2]) * 0.35]),
                     _col(100 * f))
            sv = q[2] - bt; sn = np.array([-sv[1], sv[0]]) / (np.hypot(*sv) + 1e-6)
            fw = np.sign((q[3] - q[2]) @ sn) or 1
            cv_.line(bt + sn * fw * 2.2 * sc + sv * 0.1, q[2] + sn * fw * 1.9 * sc, 0.5 * sc, _col(165 * f))   # 靴面高光
            nrm = (q[2] - q[1]); nrm = np.array([-nrm[1], nrm[0]]) / (np.hypot(*nrm) + 1e-6)
            cv_.line(bt - nrm * 3.2 * sc, bt + nrm * 3.2 * sc, max(1, 0.6 * sc), _col(150 * f))   # 靴口
        E.append((d, legfn))
    # ---- 躯干（凸包）
    Rc, Cw, Rp, Pp = S['Rc'], S['Cw'], S['Rp'], S['Pp']
    tor = []
    for (yy, rx, z0, z1) in ((23.4, 9.0, -3.4, 2.6), (21.5, 11.0, -4.4, 3.4), (16, 10.6, -5.4, 4.4), (8, 9.4, -4.8, 4.4), (0, 9.0, -4.6, 4.4)):
        for xx in (-rx, rx):
            for zz in (z0, z1): tor.append(Cw + Rc @ [xx, yy, zz])
    for xx in (-3, 3): tor.append(Cw + Rc @ [xx, 25.5, 0.3])
    for xx in (-10.3, 10.3):
        for zz in (-6.6, 6.8): tor.append(Pp + Rp @ [xx, 2.5, zz])
    tq = P2(np.array(tor)); hull = cv2.convexHull(tq.astype(np.float32)).reshape(-1, 2)
    dt_ = DP(Cw)
    # 交领（前襟）与背缝
    col_pts = [Cw + Rc @ p for p in ([-3.4, 25.0, 1.2], [-1.5, 19, 5.6], [3.5, 9, 5.2], [7.5, 2, 4.4])]
    col_pts2 = [Cw + Rc @ p for p in ([3.4, 25.0, 1.2], [1.8, 18, 5.8], [-1.0, 13.5, 5.9])]
    front_vis = DP(Cw + Rc @ [0, 15, 6]) > DP(Cw + Rc @ [0, 15, -6])
    def torsofn():
        cv_.poly(hull, _col(base))
        if front_vis:
            a = P2(np.array(col_pts)); b = P2(np.array(col_pts2))
            cv_.line(a[0], a[1], 1.2 * sc, _col(120, 170)); cv_.line(b[0], b[1], 1.0 * sc, _col(120, 170))
            for k in range(len(a) - 1): cv_.line(a[k] + [0.0, 0.0], a[k + 1], 0.45 * sc, _col(150))
        else:
            sp = P2(np.array([Cw + Rc @ [0, 23, -4.6], Cw + Rc @ [0, 8, -5.2], Cw + Rc @ [0, 0, -4.6]]))
            cv_.line(sp[0], sp[1], 0.5 * sc, _col(38)); cv_.line(sp[1], sp[2], 0.5 * sc, _col(38))
            for s_ in (-1, 1):                                                  # 肩胛褶
                q = P2(np.array([Cw + Rc @ [s_ * 3, 20, -5.5], Cw + Rc @ [s_ * 8.5, 13, -5.0]]))
                cv_.line(q[0], q[1], 0.6 * sc, _col(95))
    E.append((dt_ - 0.8, torsofn))
    # 宽皮腰封：圆柱带的凸包 + 边线 + 腰结
    ring = []; ang = np.linspace(0, 2 * math.pi, 28, endpoint=False)
    for yy in (2.8, 11.2):
        ring.append(np.stack([np.sin(ang) * 10.6, np.full_like(ang, yy), np.cos(ang) * 7.2], 1) @ Rp.T + Pp)
    ring = np.array(ring); rq = P2(ring.reshape(-1, 3)); rd_ = DP(ring)
    bhull = cv2.convexHull(rq.astype(np.float32)).reshape(-1, 2)
    vis = rd_[0] > DP(Pp) - 0.5
    def beltfn():
        cv_.poly(bhull, _col(118))
        for r in range(2):
            q = rq.reshape(2, -1, 2)[r]
            for k in range(len(ang)):
                k2 = (k + 1) % len(ang)
                if vis[k] and vis[k2]: cv_.line(q[k], q[k2], 0.55 * sc, _col(175))
        mid = (ring[0] + ring[1]) / 2; mq = P2(mid)
        for k in range(0, len(ang), 2):                                         # 皮带中缝
            k2 = (k + 1) % len(ang)
            if vis[k] and vis[k2]: cv_.line(mq[k], mq[k2], 0.35 * sc, _col(70))
    E.append((DP(Pp) + 0.2, beltfn))
    # ---- 裙摆布片（法线明暗 + 褶）
    P = self.skirt.P; nS, Ls = P.shape[:2]
    Pn = np.roll(P, -1, 0)
    t1 = Pn[:, :-1] - P[:, :-1]; t2 = P[:, 1:] - P[:, :-1]
    nrm = _nrm(np.cross(t2, t1))
    cenq = (P[:, :-1] + Pn[:, 1:]) / 2
    radial = cenq - (Pp)[None, None]; radial[..., 1] = 0
    sgn = np.sign((nrm * radial).sum(-1, keepdims=True)); nrm = nrm * np.where(sgn == 0, 1, sgn)
    lam = np.clip((nrm @ L3), -1, 1)
    vdir = np.array([st, 0, -ct])                                                # 指向相机
    face = np.clip(nrm @ vdir, -1, 1)
    q2 = P2(P); qn = P2(Pn)
    dq = DP(cenq)
    tex_sk = 0.85 + 0.3 * self.pleat
    for i in range(nS):
        for j in range(Ls - 1):
            tone = base * tex_sk[i] * (0.55 + 0.75 * max(lam[i, j], 0) + 0.25 * face[i, j])
            if j == Ls - 2: tone *= 1.15
            quad = np.array([q2[i, j], qn[i, j], qn[i, j + 1], q2[i, j + 1]])
            E.append((dq[i, j], (lambda quad=quad, tone=tone: cv_.poly(quad, _col(tone))), cen - dq[i, j]))
    # 褶线（每隔一条链画一道暗褶/亮脊）
    for i in range(0, nS, 2):
        for j in range(1, Ls - 1):
            tn = 25 if (i // 2) % 2 == 0 else 120
            dd_ = DP(P[i, j:j + 2]).mean() + 0.01
            E.append((dd_, (lambda a=q2[i, j], b=q2[i, j + 1], tn=tn: cv_.line(a, b, 0.4 * sc, _col(tn))), cen - dd_))
    # 裙摆底边
    hem = q2[:, -1]; hd = DP(P[:, -1])
    for i in range(nS):
        i2 = (i + 1) % nS
        E.append((max(hd[i], hd[i2]) + 0.01, (lambda a=hem[i], b=hem[i2]: cv_.line(a, b, 0.55 * sc, _col(130))), cen - max(hd[i], hd[i2]) - 0.01))
    # ---- 手臂 + 宽袖 + 护腕
    for s in 'lr':
        sh, el, wr, fist = S[s + 'sh'], S[s + 'el'], S[s + 'wr'], S[s + 'fist']
        d = DP((sh + el) / 2); f = far(d)
        q = P2(np.array([sh, el, wr, fist]))
        SL = self.sleeve[s].P                                                      # (4,4,3)
        sq = P2(SL); sd = DP(SL.mean(1))
        sllam = []
        for k in range(3):
            v1 = SL[k + 1, 0] - SL[k, 0]; v2 = SL[k, -1] - SL[k, 0]
            n_ = _nrm(np.cross(v1, v2)); sllam.append(abs(n_ @ L3))
        def armfn(q=q, sq=sq, f=f, sllam=sllam):
            cv_.cap(q[0], q[1], 3.6 * sc, 4.6 * sc, _col(base * f))
            for k in range(3):
                for j in range(3):
                    quad = np.array([sq[k, j], sq[k + 1, j], sq[k + 1, j + 1], sq[k, j + 1]])
                    cv_.poly(quad, _col(base * f * (0.7 + 0.6 * sllam[k])))
            fa = q[1] + (q[2] - q[1]) * 0.30
            cv_.cap(q[1], fa, 4.4 * sc, 3.0 * sc, _col(base * f))
            cv_.cap(fa, q[2], 2.5 * sc, 2.1 * sc, _col(112 * f))                  # 皮护腕
            dd = q[2] - fa; nn = np.array([-dd[1], dd[0]]) / (np.hypot(*dd) + 1e-6)
            for u in (0.15, 0.55, 0.9):
                c0 = fa + dd * u; cv_.line(c0 - nn * 2.4 * sc, c0 + nn * 2.4 * sc, 0.4 * sc, _col(160 * f))
            cv_.circ(q[3], 2.05 * sc, _col(128 * f))                               # 拳
        E.append((d + (0.5 if s == 'r' else 0), armfn))
    # ---- 刀鞘
    M, sdv = S['sc_m'], S['sc_d']
    scq = P2(np.array([M, M + sdv * 46, M + sdv * 47.5]))
    def scabfn():
        cv_.cap(scq[0], scq[1], 1.75 * sc, 1.5 * sc, _col(50))
        cv_.cap(scq[1], scq[2], 1.6 * sc, 1.2 * sc, _col(160), gold=200)
        cv_.cap(scq[0], scq[0] + (scq[1] - scq[0]) * 0.04, 2.0 * sc, 2.0 * sc, _col(160), gold=200)
    E.append((DP(M + sdv * 20), scabfn))
    # ---- 刀
    if sword_visible:
        g2 = P2(S['guard']); t2 = P2(S['tip']); pm = P2(S['pommel'])
        dv = t2 - g2; l2 = np.hypot(*dv)
        dirv = dv / (l2 + 1e-6); n2 = np.array([-dirv[1], dirv[0]])
        ev = getattr(self, 'edge_vel', None)
        want = 1.0 if n2[1] > 0 else -1.0
        if ev is not None and not S['sheathed']:
            evs = P2(S['tip'] + ev) - t2
            if np.hypot(*evs) > 1: want = 1.0 if (evs @ n2) > 0 else -1.0
        self.edge_sign = want
        n2 = n2 * want                                                             # n2 指向刃口
        wd = 2.4 * sc
        def bl(s, v):                                                              # s 0..1 沿刀, v -1(脊)..1(刃)
            curv = -0.045 * l2 * s * s                                             # 反り
            w = wd * (1 - 0.18 * s)
            return g2 + dirv * l2 * s + n2 * (curv + v * w * 0.5)
        ss = np.linspace(0, 1, 26)
        spine = [bl(s, -1) for s in ss[:-1]]; edge = [bl(s, 1) for s in ss[:-1]]
        kk = np.linspace(0, 1, 6)
        kis = [bl(0.93 + 0.07 * k, 1 - 2 * k ** 1.6) for k in kk]                  # 切先：刃线上挑
        outline = np.array(spine[:24] + [bl(1.0, -1)] + kis[::-1] + edge[:24][::-1]) if False else \
            np.array(spine[:24] + [bl(1.0, -1.0)] + list(reversed(kis[1:])) + edge[:24][::-1])
        shin = np.array([bl(s, -0.2) for s in ss[:24]] + [bl(s, -1) for s in ss[:24][::-1]])
        ha = np.array([bl(s, 0.35 + 0.12 * math.sin(s * 38)) for s in ss[:24]] + [bl(s, 1) for s in ss[:24][::-1]])
        edge_line = np.array([bl(s, 0.95) for s in ss[:24]] + kis[1:])
        info['blade_poly'] = outline + [x0, y0]
        if S['sheathed']:
            bdep = DP(S['guard'])
            def swfn():
                cv_.cap(g2, pm, 1.3 * sc, 1.25 * sc, _col(55))
                cv_.cap(pm, pm + (pm - g2) * 0.04, 1.4 * sc, 1.4 * sc, _col(170), gold=230)
                for u in np.linspace(0.1, 0.9, 6):
                    c0 = g2 + (pm - g2) * u; cv_.line(c0 - n2 * 1.2 * sc + (pm - g2) * 0.04, c0 + n2 * 1.2 * sc, .35 * sc, _col(115))
                cv_.ell(g2, (0.5 * sc, 2.6 * sc), math.degrees(math.atan2(dirv[1], dirv[0])), _col(170))
            E.append((bdep + 0.3, swfn))
        else:
            bdep = DP(S['guard'] + S['bd'] * 12)
            def swfn():
                cv_.fill('C', outline, (255, 0, 0, 255), depth=True)
                cv_.fill('G', outline, 0)
                cv_.fill('M', outline, (120, 0, 90))
                cv_.fill('M', shin, (62, 0, 40))
                cv_.fill('M', ha, (190, 0, 255))
                cv_.stroke('M', edge_line, (255, 255, 255), max(0.6, 0.35 * sc))
                # 柄 + 镡 + 柄头
                cv_.cap(g2, pm, 1.3 * sc, 1.2 * sc, _col(55))
                for u in np.linspace(0.08, 0.92, 7):
                    c0 = g2 + (pm - g2) * u; cv_.line(c0 - n2 * 1.15 * sc, c0 + n2 * 1.15 * sc + (pm - g2) * 0.05, .35 * sc, _col(120))
                cv_.cap(pm, pm + (pm - g2) * 0.05, 1.4 * sc, 1.4 * sc, _col(170), gold=230)
                cv_.ell(g2, (0.55 * sc, 2.7 * sc), math.degrees(math.atan2(dirv[1], dirv[0])), _col(170))
                cv_.fill_ell('G', g2, (0.55 * sc + 0.12, 2.7 * sc), math.degrees(math.atan2(dirv[1], dirv[0])), 200)
            E.append((bdep, swfn))
    # ---- 头 + 头发
    Rh, Hc = S['Rh'], S['Hc']
    hp = []
    for a in np.linspace(0, 2 * math.pi, 14, endpoint=False):
        for b in (-0.9, -0.45, 0, 0.45, 0.9, 1.3):
            hp.append([math.cos(b) * math.sin(a) * 5.1, math.sin(b) * 6.6 if b < 1.2 else 6.6, math.cos(b) * math.cos(a) * 5.8])
    hp += [[2.4, -5.0, 3.2], [-2.4, -5.0, 3.2], [0, -6.0, 3.0]]                                          # 颌
    hq = P2(Hc + np.array(hp) @ Rh.T); hhull = cv2.convexHull(hq.astype(np.float32)).reshape(-1, 2)
    prof = Hc + np.array([[0, y_, z_] for z_, y_ in HEAD_PROFILE]) @ Rh.T
    pq = P2(prof)
    neck = P2(np.array([S['N'] - Rc @ [0, 1, 0], Hc + Rh @ [0, -4, -0.5]]))
    hairc = [[math.cos(b) * math.sin(a) * 5.7, math.sin(b) * 7.1 + 0.4, math.cos(b) * math.cos(a) * 6.3 - 0.5]
             for a in np.linspace(0, 2 * math.pi, 16, endpoint=False) for b in (-0.4, 0.1, 0.6, 1.0, 1.5)
             if not (abs(a) < 1.2 or abs(a - 2 * math.pi) < 1.2) or b > 0.85]
    cq = P2(Hc + np.array(hairc) @ Rh.T); chull = cv2.convexHull(cq.astype(np.float32)).reshape(-1, 2)
    tie2 = P2(S['tie'])
    eye = P2(Hc + Rh @ [2.1, 0.6, 5.2]); eye2 = P2(Hc + Rh @ [-2.1, 0.6, 5.2])
    face_vis = (DP(Hc + Rh @ [0, 0, 6]) - DP(Hc)) > -2.0
    if DP(Hc + Rh @ [-2.1, 0.6, 5.2]) > DP(Hc + Rh @ [2.1, 0.6, 5.2]): eye, eye2 = eye2, eye
    def headfn():
        cv_.cap(neck[0], neck[1], 2.7 * sc, 2.5 * sc, _col(base))
        cv_.poly(hhull, _col(92))
        cv_.poly(pq, _col(92))
        cv_.poly(chull, _col(40))
        cv_.circ(tie2, 1.5 * sc, _col(60, 120))
    E.append((DP(Hc), headfn))
    hair_tone = 42
    hd0 = DP(Hc) + 4.0                                # 所有发丝共用的“轮廓光深度”，避免发与发之间描边
    rng = np.random.default_rng(self.seed + 5)
    def add_strands(ch, w0, w1, tones, dbias=0.0, wscale=None):
        q = P2(ch.P); dd = DP(ch.P).mean(1)
        for k in range(ch.C):
            ws = wscale[k] if wscale is not None else 1
            E.append((dd[k] + dbias, (lambda q=q[k], ws=ws, tn=tones[k]: cv_.strand(q, w0 * ws * sc, w1 * sc, _col(tn))),
                      hd0 - dd[k] - dbias))
    pt_t = [hair_tone + (60 if k % 4 == 1 else 0) for k in range(self.ponytail.C)]
    ctr = self.ponytail.P.mean(0); cq_ = P2(ctr)
    E.append((DP(ctr).mean() - 0.05, (lambda cq_=cq_: cv_.strand(cq_, 2.8 * sc, 0.3 * sc, _col(hair_tone))), hd0 - DP(ctr).mean() + 0.05))
    hw = 1 / math.sqrt(self.hair)
    add_strands(self.ponytail, 2.3 * hw, 0.0, pt_t, 0.0, self.pt_w)
    add_strands(self.locks, 1.6 * hw, 0.0, [hair_tone + (50 if k % 3 == 0 else 0) for k in range(self.locks.C)], 0.0, self.lock_w)
    add_strands(self.bangs, 1.3 * hw, 0.0, [hair_tone + 30] * self.bangs.C, 0.6)
    if detail > 0.5:
        add_strands(self.fly, 0.28, -1, [hair_tone + 70] * self.fly.C, 0.3)
    # ---- 飘带（朱红，扭转）与腰前暗红长带
    def add_ribbon(ch, idx, wbase, redv, tone0, twist_rate, tassel=False):
        Pr = ch.P[idx]; q = P2(Pr)
        d = np.gradient(q, axis=0); nn = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
        tw = np.arange(len(q)) * twist_rate + idx * 1.3 + Pr[:, 1] * 0.05 + (self.t_last or 0) * 2.0
        wid = wbase * sc * (0.3 + 0.7 * np.abs(np.cos(tw))) * np.linspace(1, 0.8, len(q))
        cols = [_col(tone0 * (0.55 + 0.6 * (0.5 + 0.5 * math.cos(tw[k]))), redv) for k in range(len(q))]
        dd = DP(Pr)
        segs = [(dd[k:k + 3].mean(), k) for k in range(0, len(q) - 1, 3)]
        for dk, k in segs:
            kk = slice(k, min(k + 4, len(q)))
            E.append((dk, (lambda qq=q[kk], ww=wid[kk], nn_=nn[kk], cc=cols[kk]: cv_.ribbon(qq, ww, nn_, cc))))
        if tassel:
            end = q[-1]; dv_ = q[-1] - q[-2]; dv_ = dv_ / (np.hypot(*dv_) + 1e-6)
            nv = np.array([-dv_[1], dv_[0]])
            def tas(end=end, dv_=dv_, nv=nv):
                cv_.circ(end, 1.0 * sc, _col(150, 0), gold=220)
                for m in range(7):
                    a = end + nv * (m - 3) * 0.35 * sc
                    cv_.line(a, a + (dv_ * 5.5 + nv * (m - 3) * 0.4) * sc, max(0.6, 0.3 * sc), _col(110, redv))
            E.append((dd[-1] + 0.01, tas))
    if self.ribbons:
        add_ribbon(self.rib, 0, 1.5, 255, 230, 0.55)
        add_ribbon(self.rib, 1, 1.25, 255, 200, 0.6)
        kq = P2(self.rib.P[0, 0])
        E.append((DP(self.rib.P[0, 0]) + 0.05, lambda kq=kq: cv_.circ(kq, 1.5 * sc, _col(200, 255))))
    add_ribbon(self.band, 0, 1.7, 150, 120, 0.18, tassel=True)
    # ---- 绘制（画家算法）
    E.sort(key=lambda e: e[0])
    for e in E:
        cv_.dcur = e[0] + (e[2] if len(e) > 2 else 0.0); e[1]()
    # ---- 合成
    C = cv_.C.astype(np.float32) * (1 / 255.)
    A = C[..., 0]
    inv = 1.0 / np.maximum(A, 1e-3)
    tone = C[..., 1] * inv; red = np.clip(C[..., 2] * inv, 0, 1); met = np.clip(C[..., 3] * inv, 0, 1)
    h_, w_ = A.shape
    ts = max(1, int(round(sc * 0.7)))                     # 纹理随角色尺度放大，避免随机噪
    tt = _tile(self.tex, (x0 // ts) % 1024, (y0 // ts) % 1024, h_ // ts + 2, w_ // ts + 2)
    tt = cv2.resize(tt, ((w_ // ts + 2) * ts, (h_ // ts + 2) * ts), interpolation=cv2.INTER_LINEAR)[:h_, :w_]
    lift_c = np.array([0.24, 0.24, 0.27], np.float32) * lift
    inkc = INK if ink is None else np.asarray(ink, np.float32)
    fmul, fao = _form(A, cv_.D, max(3.0, scale * 0.032), tuple(rd))
    tone = tone * fmul * fao
    tone_t = tone * (0.75 + 0.5 * tt)
    col = inkc[None, None] + tone_t[..., None] * lift_c
    redc = np.array([0.55, 0.045, 0.04], np.float32)
    col = col * (1 - red[..., None]) + (redc * (0.25 + 0.95 * tone)[..., None] * min(1.4, 0.6 + 0.4 * lift)) * red[..., None]
    gold = cv_.G.astype(np.float32) / 255. * inv
    gold = np.clip(gold, 0, 1)
    col = col * (1 - gold[..., None] * 0.6) + GOLD[None, None] * (0.30 * (0.5 + tone) * gold * 0.6)[..., None]
    # 刀身
    rc = np.asarray(rim_color, np.float32)
    if met.max() > 0.01:
        Mm = cv_.M.astype(np.float32) / 255.
        Mm = Mm * inv[..., None]
        steel = Mm[..., 0:1] * np.array([0.50, 0.52, 0.56], np.float32) + Mm[..., 0:1] ** 2 * rc * 0.35
        steel = steel + Mm[..., 1:2] * 0.85
        if shine is not None and 'blade_poly' in info:
            g2_ = np.array(info['guard']) - [x0, y0]; t2_ = np.array(info['tip']) - [x0, y0]
            dvv = t2_ - g2_; ll = (dvv @ dvv) + 1e-6
            yy, xx = np.mgrid[0:h_, 0:w_]
            sp_ = ((xx - g2_[0]) * dvv[0] + (yy - g2_[1]) * dvv[1]) / ll
            band = np.exp(-((sp_ - shine) / 0.06) ** 2).astype(np.float32)
            steel = steel + band[..., None] * (0.5 + 0.8 * Mm[..., 0:1]) * np.array([1.0, 0.97, 0.92], np.float32)
        if heat > 0:
            hh = Mm[..., 2:3] * heat
            steel = steel * (1 - hh * 0.6) + hh * (RED * 1.2 + GOLD * hh * 0.7)
        col = col * (1 - met[..., None]) + steel * met[..., None]
    # 轮廓光
    if rim > 0:
        rw = float(np.clip(scale * 0.0042, 0.8, 3.2))
        dx, dy = rd
        A_s = _shift(A, -dx * rw, -dy * rw)
        r1 = np.clip(A - A_s, 0, 1)
        r2 = _blur_ds(np.clip(A - _shift(A, -dx * scale * 0.012, -dy * scale * 0.012), 0, 1), scale * 0.008 + 1) * A
        Dm = cv_.D; Ds = _shift(Dm, -dx * rw * 1.5, -dy * rw * 1.5)
        inner = ((Dm - Ds) > 3.5).astype(np.float32) * (Ds > -1e3)
        if BACKEND == 'skia':
            inner = cv2.GaussianBlur(inner, (0, 0), 1.0); inner = np.clip((inner - 0.12) * 2.2, 0, 1) * A
        else:
            inner = cv2.GaussianBlur(inner, (0, 0), 0.6) * A
        rmod = 0.65 + 0.7 * tt
        rim_l = (r1 * 0.9 * rmod + inner * 0.32 * rmod + r2 * 0.30 + met * r2 * 0.6) * rim
        col = col + rc[None, None] * rim_l[..., None] / np.maximum(A, 1e-3)[..., None] * (A > 0.02)[..., None]
    # 眼光
    reg = fr[y0:y1, x0:x1]
    a3 = (A * alpha)[..., None]
    out = reg * (1 - a3) + col * a3
    if glint > 0 and face_vis:
        for e_ in (eye, eye2):
            gx, gy = int(e_[0]), int(e_[1])
            if 0 <= gx < w_ and 0 <= gy < h_:
                R = int(4 * sc + 6); ya, yb, xa, xb = max(0, gy - R), min(h_, gy + R), max(0, gx - R), min(w_, gx + R)
                gl = np.zeros((yb - ya, xb - xa), np.float32)
                cv2.ellipse(gl, (gx - xa, gy - ya), (max(1, int(0.75 * sc)), max(1, int(0.10 * sc))), -8, 0, 360, 1, -1, cv2.LINE_AA)
                gl = cv2.GaussianBlur(gl, (0, 0), max(0.5, 0.08 * sc)) * 1.6 + cv2.GaussianBlur(gl, (0, 0), 1.2 * sc) * 0.9
                out[ya:yb, xa:xb] += gl[..., None] * rc * glint * alpha
                break
    if heat > 0 and blade_glow > 0 and met.max() > 0.01:
        gsm = _blur_ds(met * heat, max(2, 1.5 * sc))
        out = out + gsm[..., None] * (RED * 1.2 + GOLD * 0.3) * blade_glow * alpha
    dr = getattr(self, 'drops', None)
    if dr is not None and len(dr):
        q = P2(dr[:, :3]); qv = P2(dr[:, :3] + dr[:, 3:6] * 0.012) - q
        lay = np.zeros(A.shape, np.float32)
        for k in range(len(q)):
            a = q[k]; b = a + qv[k]
            cv2.line(lay, (int(a[0] * 8), int(a[1] * 8)), (int(b[0] * 8), int(b[1] * 8)), float(1 - dr[k, 6] / 0.7),
                     max(1, int(0.35 * sc)), cv2.LINE_AA, 3)
        out = out + cv2.GaussianBlur(lay, (0, 0), 0.6)[..., None] * (0.35 + 0.5 * rc) * alpha
    fr[y0:y1, x0:x1] = out
    if return_masks:
        bm = np.zeros(fr.shape[:2], np.float32); bm[y0:y1, x0:x1] = met * A
        am = np.zeros(fr.shape[:2], np.float32); am[y0:y1, x0:x1] = A * alpha
        info['blade_mask'] = bm; info['alpha'] = am
    info['alpha_local'] = A
    return fr, info

Swordsman.draw = _sw_draw


# ============================================================== 刀光拖尾
def blade_trail(fr, history, color=(1.0, 0.95, 0.88), intensity=1.0, glow=1.0, sub=6, inner=0.28, mode='light',
                edge_color=None, scale_hint=None):
    """刀光（接口不变）。skia 后端：扫掠面用带逐顶点颜色的三角网格一次画成（新→旧、柄→尖的强度连续插值，
    无 cv2 版逐块拼接的条纹缝），刃尖轨迹为渐细的贝塞尔描边，辉光用 MaskFilter 高斯模糊。cv 后端走旧实现。"""
    if BACKEND != 'skia' or len(history) < 2:
        return _blade_trail_cv(fr, history, color, intensity, glow, sub, inner, mode, edge_color, scale_hint)
    skia = _sk.skia
    Hh, Ww = fr.shape[:2]
    lines = []
    for k in range(len(history) - 1):
        g0, t0 = np.array(history[k][0], float), np.array(history[k][1], float)
        g1, t1 = np.array(history[k + 1][0], float), np.array(history[k + 1][1], float)
        v0, v1 = t0 - g0, t1 - g1
        a0, a1 = math.atan2(v0[1], v0[0]), math.atan2(v1[1], v1[0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        l0, l1 = np.hypot(*v0), np.hypot(*v1)
        for i in range(sub):
            u = i / sub
            g = g0 + (g1 - g0) * u; a = a0 + da * u; l = l0 + (l1 - l0) * u
            lines.append((g, g + np.array([math.cos(a), math.sin(a)]) * l))
    lines.append((np.array(history[-1][0], float), np.array(history[-1][1], float)))
    pts = np.array([[g, t] for g, t in lines]).reshape(-1, 2)
    ds = 2
    x0 = int(max(0, pts[:, 0].min() - 60)); x1 = int(min(Ww, pts[:, 0].max() + 60))
    y0 = int(max(0, pts[:, 1].min() - 60)); y1 = int(min(Hh, pts[:, 1].max() + 60))
    if x1 - x0 < 4 or y1 - y0 < 4: return fr
    h, w = (y1 - y0) // ds + 1, (x1 - x0) // ds + 1
    off = np.array([x0, y0], float)
    n = len(lines); ns = 10
    rs = np.random.default_rng(len(history)).random(ns + 1) * 0.35 + 0.8           # 径向条纹（顶点级，平滑）
    S = np.linspace(inner, 1, ns + 1)
    P = np.zeros((n, ns + 1, 2)); V = np.zeros((n, ns + 1)); Vo = np.zeros((n, ns + 1))
    for i in range(n):
        age = 1 - i / (n - 1); fa = (1 - age) ** 2.2
        g, tp = (lines[i][0] - off) / ds, (lines[i][1] - off) / ds
        P[i] = g[None] + (tp - g)[None] * S[:, None]
        rad = ((S - inner) / (1 - inner) * 0.85 + 0.15) ** 1.8 * rs
        V[i] = fa * rad; Vo[i] = (1 - age) ** 0.7 * rad * (1 - fa)
    idx = []
    for i in range(n - 1):
        for j in range(ns):
            a, b, c, d = i * (ns + 1) + j, i * (ns + 1) + j + 1, (i + 1) * (ns + 1) + j + 1, (i + 1) * (ns + 1) + j
            idx += [a, b, c, a, c, d]
    F = _sk.FloatSurface(h, w)
    Pv = P.reshape(-1, 2)
    def mesh(vals):
        F.clear(); v = np.clip(vals.reshape(-1), 0, 1)
        F.mesh(Pv, np.stack([v, v, v, np.ones_like(v)], 1), idx, blend='plus')
        return F.buf[..., 0].copy()
    L = mesh(V); Lo = mesh(Vo)
    # 刃尖轨迹：渐细描边（多段，越新越粗越亮）+ 最新刀身亮线
    F.clear()
    tips = np.array([(l[1] - off) / ds for l in lines])
    for i in range(n - 1):
        age = 1 - (i + 0.5) / (n - 1)
        Pp = skia.Path(); Pp.moveTo(*tips[i]); Pp.lineTo(*tips[i + 1])
        F.path(Pp, color=(1, 1, 1), alpha=float((1 - age) ** 1.2), stroke=0.6 + 1.6 * (1 - age), blend='plus')
    gN, tN = (lines[-1][0] - off) / ds, (lines[-1][1] - off) / ds
    Pp = skia.Path(); Pp.moveTo(*(gN + (tN - gN) * inner)); Pp.lineTo(*tN)
    F.path(Pp, color=(1, 1, 1), alpha=1.0, stroke=2.2, blend='plus')
    Ed = np.clip(F.buf[..., 0], 0, 1.5).copy()
    span = max(np.hypot(*(pts.max(0) - pts.min(0))), 50)
    core = cv2.GaussianBlur(L, (0, 0), 1.0) * 1.1 + cv2.GaussianBlur(Ed, (0, 0), 0.6) * 1.3
    old_ = cv2.GaussianBlur(Lo, (0, 0), 2.5) * 0.55
    bloom = _blur_ds(L + Ed * 0.6, max(3, span / ds * 0.035)) * 1.2
    lay = cv2.resize(core, (x1 - x0, y1 - y0)); bl = cv2.resize(bloom + old_, (x1 - x0, y1 - y0))
    col = np.asarray(color, np.float32); ec = col if edge_color is None else np.asarray(edge_color, np.float32)
    reg = fr[y0:y1, x0:x1]
    if mode == 'ink':
        a = np.clip(lay * 1.2 + bl * 0.3, 0, 1)[..., None] * intensity
        fr[y0:y1, x0:x1] = reg * (1 - a) + INK * a
    else:
        fr[y0:y1, x0:x1] = reg + (lay[..., None] * col + bl[..., None] * ec * glow) * intensity
    return fr

def _blade_trail_cv(fr, history, color=(1.0, 0.95, 0.88), intensity=1.0, glow=1.0, sub=6, inner=0.28, mode='light',
                edge_color=None, scale_hint=None):
    """history: [(guard_xy, tip_xy), ...] 旧→新（每帧一条，取自 Swordsman.draw 返回的 info['guard'], info['tip']）。
    在相邻两帧之间按“绕护手转角+长度插值”细分成弧，填充扫掠面：新→旧渐隐、近柄弱→刀尖强，
    叠加运动模糊与辉光。mode='light' 加法发光；mode='ink' 以墨色压暗（纸面场景）。
    edge_color：外缘色（如朱红 RED），None=与 color 相同。返回 fr。"""
    if len(history) < 2: return fr
    Hh, Ww = fr.shape[:2]
    lines = []
    for k in range(len(history) - 1):
        g0, t0 = np.array(history[k][0], float), np.array(history[k][1], float)
        g1, t1 = np.array(history[k + 1][0], float), np.array(history[k + 1][1], float)
        v0, v1 = t0 - g0, t1 - g1
        a0, a1 = math.atan2(v0[1], v0[0]), math.atan2(v1[1], v1[0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        l0, l1 = np.hypot(*v0), np.hypot(*v1)
        for i in range(sub):
            u = i / sub
            g = g0 + (g1 - g0) * u; a = a0 + da * u; l = l0 + (l1 - l0) * u
            lines.append((g, g + np.array([math.cos(a), math.sin(a)]) * l))
    lines.append((np.array(history[-1][0], float), np.array(history[-1][1], float)))
    pts = np.array([[g, t] for g, t in lines]).reshape(-1, 2)
    ds = 2
    x0 = int(max(0, pts[:, 0].min() - 60)); x1 = int(min(Ww, pts[:, 0].max() + 60))
    y0 = int(max(0, pts[:, 1].min() - 60)); y1 = int(min(Hh, pts[:, 1].max() + 60))
    if x1 - x0 < 4 or y1 - y0 < 4: return fr
    h, w = (y1 - y0) // ds + 1, (x1 - x0) // ds + 1
    L = np.zeros((h, w), np.float32); Ed = np.zeros((h, w), np.float32); Lo = np.zeros((h, w), np.float32)
    n = len(lines); nseg = 8
    off = np.array([x0, y0], float)
    rs = np.random.default_rng(len(history)).random(nseg) * 0.5 + 0.6        # 径向条纹
    for i in range(n - 1):
        age = 1 - (i + 0.5) / (n - 1)                                        # 1=最旧 0=最新
        fa = (1 - age) ** 2.2
        ga, ta = (lines[i][0] - off) / ds, (lines[i][1] - off) / ds
        gb, tb = (lines[i + 1][0] - off) / ds, (lines[i + 1][1] - off) / ds
        for j in range(nseg):
            s0, s1 = inner + (1 - inner) * j / nseg, inner + (1 - inner) * (j + 1) / nseg
            q = _ip(np.array([ga + (ta - ga) * s0, ga + (ta - ga) * s1, gb + (tb - gb) * s1, gb + (tb - gb) * s0])).reshape(-1, 1, 2)
            rad = ((j + 1) / nseg) ** 1.8 * rs[j]
            cv2.fillConvexPoly(L, q, float(fa * rad), cv2.LINE_AA, SH)
            cv2.fillConvexPoly(Lo, q, float((1 - age) ** 0.7 * rad * (1 - fa)), cv2.LINE_AA, SH)
        cv2.line(Ed, tuple(int(v) for v in _ip(ta)), tuple(int(v) for v in _ip(tb)), float((1 - age) ** 1.2), 2, cv2.LINE_AA, SH)
    # 最新一条刀身亮线
    gN, tN = (lines[-1][0] - off) / ds, (lines[-1][1] - off) / ds
    cv2.line(Ed, tuple(int(v) for v in _ip(gN + (tN - gN) * inner)), tuple(int(v) for v in _ip(tN)), 1.0, 2, cv2.LINE_AA, SH)
    core = cv2.GaussianBlur(L, (0, 0), 1.6) * 1.1 + cv2.GaussianBlur(Ed, (0, 0), 0.8) * 1.3
    span = max(np.hypot(*(pts.max(0) - pts.min(0))), 50)
    old_ = cv2.GaussianBlur(Lo, (0, 0), 2.5) * 0.55
    bloom = cv2.GaussianBlur(L + Ed * 0.6, (0, 0), max(3, span / ds * 0.035)) * 1.2
    lay = cv2.resize(core, (x1 - x0, y1 - y0)); bl = cv2.resize(bloom + old_, (x1 - x0, y1 - y0))
    col = np.asarray(color, np.float32); ec = col if edge_color is None else np.asarray(edge_color, np.float32)
    reg = fr[y0:y1, x0:x1]
    if mode == 'ink':
        a = np.clip(lay * 1.2 + bl * 0.3, 0, 1)[..., None] * intensity
        fr[y0:y1, x0:x1] = reg * (1 - a) + INK * a
    else:
        fr[y0:y1, x0:x1] = reg + (lay[..., None] * col + bl[..., None] * ec * glow) * intensity
    return fr

# ============================================================== 通用剪影合成（其他角色/道具复用）
def _composite(fr, cv_, x0, y0, rim_color=(0.85, 0.9, 1.0), rim_dir=(-0.7, -0.7), rim=1.0, rimw=2.0, lift=1.0, alpha=1.0,
               ink=None, tex_scale=1.0, soft=None, paper=0.0, paper_col=(0.92, 0.88, 0.78), inner_thr=3.5, burn=None, form_px=None):
    """把 _Canvas 合成进 fr[y0:, x0:]。返回 (fr, A_local)。paper>0：纸糊透光材质（背光时内部发亮、可见纤维）。
    burn=dict(prog=0..1, y0=脚底屏幕y, y1=头顶屏幕y, seed)：自下而上燃烧——烧穿处透明，焰线金红发光，焦边发黑。"""
    C = cv_.C.astype(np.float32) * (1 / 255.)
    A = C[..., 0]; h_, w_ = A.shape
    if A.max() <= 0: return fr, A
    inv = 1.0 / np.maximum(A, 1e-3)
    tone = C[..., 1] * inv; red = np.clip(C[..., 2] * inv, 0, 1)
    gold = np.clip(cv_.G.astype(np.float32) / 255. * inv, 0, 1)
    fmul, fao = _form(A, cv_.D, form_px if form_px else max(3.0, rimw * 8), tuple(rim_dir))
    tone = tone * fmul * fao
    tex = noise_tex(1024, seed=7, base=10, octaves=6)
    ts = max(1, int(round(tex_scale)))
    tt = _tile(tex, (x0 // ts) % 1024, (y0 // ts) % 1024, h_ // ts + 2, w_ // ts + 2)
    tt = cv2.resize(tt, ((w_ // ts + 2) * ts, (h_ // ts + 2) * ts))[:h_, :w_]
    inkc = INK if ink is None else np.asarray(ink, np.float32)
    col = inkc[None, None] + (tone * (0.75 + 0.5 * tt))[..., None] * np.array([0.24, 0.24, 0.27], np.float32) * lift
    redc = np.array([0.55, 0.045, 0.04], np.float32)
    col = col * (1 - red[..., None]) + redc * (0.25 + 0.95 * tone)[..., None] * red[..., None] * min(1.4, 0.6 + 0.4 * lift)
    col = col * (1 - gold[..., None] * 0.7) + GOLD[None, None] * (0.32 * (0.5 + tone) * gold * 0.7)[..., None]
    rc = np.asarray(rim_color, np.float32)
    glow_add = None
    if burn is not None and burn.get('prog', 0) > 0:
        bp = burn['prog']; yb0, yb1 = burn['y0'], burn['y1']
        nz = _tile(noise_tex(512, seed=burn.get('seed', 5), base=12, octaves=5), x0 % 512, y0 % 512, h_, w_)
        yy = (np.arange(h_, dtype=np.float32)[:, None] + y0 - yb0) / (yb1 - yb0)
        f = yy * 0.8 + nz * 0.35 - 0.05
        th_ = bp * 1.15
        keep = np.clip((f - th_) / 0.012, 0, 1)
        charb = np.clip(1 - (f - th_) / 0.05, 0, 1) * keep
        ember = np.exp(-((f - th_) / 0.010) ** 2) * (A > 0.05)
        col = col * (1 - charb[..., None] * 0.85)
        A = A * keep
        glow_add = ember
    if paper > 0:
        fib = _tile(noise_tex(512, seed=21, base=60, octaves=3), x0 % 512, y0 % 512, h_, w_)
        dist = cv2.distanceTransform((A > 0.5).astype(np.uint8), cv2.DIST_L2, 3)
        thick = np.clip(dist / (rimw * 12 + 1), 0, 1)
        trans = (0.55 + 0.45 * fib) * (1 - 0.55 * thick) * (1 - np.clip(tone - 0.3, 0, 1))   # 骨架/厚处更暗
        pc = np.asarray(paper_col, np.float32) * (0.35 + 0.65 * rc / max(rc.max(), 1e-3))
        col = col * (1 - paper) + (pc[None, None] * trans[..., None] + col * 0.2) * paper
    if rim > 0:
        dx, dy = np.array(rim_dir, float) / max(np.linalg.norm(rim_dir), 1e-6)
        r1 = np.clip(A - _shift(A, -dx * rimw, -dy * rimw), 0, 1)
        sw_ = (soft if soft is not None else rimw * 4)
        r2 = cv2.GaussianBlur(np.clip(A - _shift(A, -dx * sw_, -dy * sw_), 0, 1), (0, 0), sw_ * 0.7 + 0.5) * A
        Dm = cv_.D; Ds = _shift(Dm, -dx * rimw * 1.5, -dy * rimw * 1.5)
        inner = (((Dm - Ds) > inner_thr) * (Ds > -1e3)).astype(np.float32)
        if BACKEND == 'skia':   # 硬边深度 → 平滑后重新收紧成 AA 细线（去台阶）
            inner = cv2.GaussianBlur(inner, (0, 0), 1.0); inner = np.clip((inner - 0.12) * 2.2, 0, 1) * A
        else:
            inner = cv2.GaussianBlur(inner, (0, 0), 0.6) * A
        rmod = 0.65 + 0.7 * tt
        rl = (r1 * 0.9 * rmod + inner * 0.4 * rmod + r2 * 0.3) * rim
        col = col + rc * (rl / np.maximum(A, 1e-3))[..., None] * (A > 0.02)[..., None]
    H_, W_ = fr.shape[:2]
    xa, ya = max(0, x0), max(0, y0); xb, yb = min(W_, x0 + w_), min(H_, y0 + h_)
    if xb <= xa or yb <= ya: return fr, A
    sl = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    a3 = (A[sl] * alpha)[..., None]
    fr[ya:yb, xa:xb] = fr[ya:yb, xa:xb] * (1 - a3) + col[sl] * a3
    if glow_add is not None:
        g = glow_add[sl]
        fr[ya:yb, xa:xb] += (g[..., None] * (GOLD * 1.6 + 0.3) + _blur_ds(g, 6)[..., None] * (RED * 1.5 + GOLD * 0.4)) * alpha
    return fr, A

def _local_canvas(fr, pts, margin):
    pts = np.asarray(pts, float).reshape(-1, 2)
    x0 = int(max(0, math.floor(pts[:, 0].min() - margin))); x1 = int(min(fr.shape[1], math.ceil(pts[:, 0].max() + margin)))
    y0 = int(max(0, math.floor(pts[:, 1].min() - margin))); y1 = int(min(fr.shape[0], math.ceil(pts[:, 1].max() + margin)))
    return x0, y0, x1, y1

# ============================================================== 侧脸特写
LIGHTS = {'moon': dict(rim_color=(0.78, 0.86, 1.0), rim_dir=(-0.85, -0.45), lift=0.8),
          'dawn': dict(rim_color=(1.0, 0.76, 0.40), rim_dir=(0.9, -0.35), lift=0.9)}

def profile_cu(fr, sw, t, cx, cy, head_px, light='moon', glint=1.0, flip=False, action='stand_wind', phase=None, wind=-160,
               wet=0.0, cu_fill=1.0, **over):
    """头部/侧脸 CU：sw 为 Swordsman(view='side', hair≥2)。把头心放在 (cx,cy)，头高 head_px 像素（下巴到头顶≈13单位）。
    light='moon'(冷白月光，背后上方) / 'dawn'(金色晨光，正面侧逆)，glint>0 开一线眼光。连续帧调用请用递增 t。"""
    ph = (t * 0.25) % 1 if phase is None else phase
    S = sw.pose(action, ph, t, wind=wind * (-1 if flip else 1), flip=flip, wet=wet, **over)
    scale = head_px / 13.0 * 100
    sc = scale / 100
    th = (VIEWS.get(sw.view, sw.view) if isinstance(sw.view, str) else sw.view) * D2R
    fs = -1 if flip else 1
    hx = (S['Hc'][0] * math.cos(th) + S['Hc'][2] * math.sin(th)) * fs * sc
    x = cx - hx; y = cy + S['Hc'][1] * sc
    L = dict(LIGHTS[light]) if isinstance(light, str) else dict(light)
    if flip: L['rim_dir'] = (-L['rim_dir'][0], L['rim_dir'][1])
    if not HAIR_V3 or cu_fill is None:
        return sw.draw(fr, x, y, scale, glint=glint, **L)
    # v3 特写补光：抬天光与肤色补光、整体 lift，让面部在逆光里可读（只作用于这一次绘制，结束即恢复全局 FILL）
    keep = dict(FILL)
    FILL.update(amb=keep['amb'] + 0.18 * cu_fill, skin=keep['skin'] + 0.58 * cu_fill)
    L['lift'] = L.get('lift', 1.0) * (1 + 0.22 * cu_fill)
    try:
        return sw.draw(fr, x, y, scale, glint=glint, **L)
    finally:
        FILL.clear(); FILL.update(keep)

# ============================================================== 手部特写
class HandCU:
    """手部大特写（程序化 2D）。mode:
       'grip'       手背视角握刀柄（柄横向，左侧护手+刀身），prog=握紧程度(0..1，越紧指节越凸、微颤)
       'thumb_push' 手握鞘口，拇指推镡出鞘一线（prog 0..1 = 推出距离，habaki 金光+刃线反光扫过）
       'open_rain'  侧视掌心朝上承雨 → prog 0..1 渐握成拳（雨滴落掌、溅水、握拳时指缝滴水）
    draw(fr, mode, prog, t, x, y, size, angle=0, flip=False, rim_color, rim_dir, wet, ...)：x,y=拳心，size=手掌宽像素≈手长的一半。"""
    def __init__(self, seed=0):
        self.rng = np.random.default_rng(seed); self.seed = seed

    def draw(self, fr, mode='grip', prog=0.0, t=0.0, x=960, y=540, size=500, angle=0.0, flip=False,
             rim_color=(0.85, 0.9, 1.0), rim_dir=(-0.7, -0.7), lift=1.0, wet=0.0, rain=1.0, blade_shine=None, heat=0.0):
        k = size / 46.0
        ca, sa_ = math.cos(angle * D2R), math.sin(angle * D2R); fs = -1 if flip else 1
        def T(p):
            p = np.asarray(p, float).reshape(-1, 2)
            q = np.stack([p[:, 0] * fs, p[:, 1]], 1)
            return np.stack([q[:, 0] * ca - q[:, 1] * sa_, q[:, 0] * sa_ + q[:, 1] * ca], 1) * k + [x, y]
        x0, y0, x1, y1 = _local_canvas(fr, T(np.array([[-160, -160], [160, -160], [160, 120], [-160, 120]])), 10)
        if x1 - x0 < 4 or y1 - y0 < 4: return fr
        cv_ = _Canvas(y1 - y0, x1 - x0); off = np.array([x0, y0])
        P = lambda p: T(p) - off
        M = []                                     # 金属/发光叠加（局部坐标多边形, 颜色, 强度）
        tr = math.sin(t * 37) * 0.5 + math.sin(t * 53 + 1) * 0.3
        if mode in ('grip', 'thumb_push'):
            push = prog if mode == 'thumb_push' else 0.0
            gap = 13 * ease(push, 'o')
            tight = prog if mode == 'grip' else 0.6
            jit = tr * 0.7 * tight
            cv_.dcur = 0
            if mode == 'grip':
                # 刀柄（柄卷菱形纹）
                cv_.poly(P([[-40, -9], [80, -8.5], [80, 8.5], [-40, 9]]), _col(80))
                for i in range(-3, 13):
                    xa = i * 9.0
                    cv_.poly(P([[xa, -9], [xa + 4.5, 0], [xa, 9], [xa - 4.5, 0]]), _col(150), gold=0)
                    cv_.poly(P([[xa + 4.5, -6], [xa + 7, 0], [xa + 4.5, 6], [xa + 2, 0]]), _col(30))
                cv_.cap(P([80, 0])[0], P([88, 0])[0], 9.4 * k, 8.6 * k, _col(170), gold=230)       # 柄头
                cv_.poly(P([[-46, -19], [-40, -19], [-40, 19], [-46, 19]]), _col(150), gold=200)      # 镡（侧）
                cv_.poly(P([[-52, -8], [-46, -8.5], [-46, 8.5], [-52, 8]]), _col(180), gold=255)     # habaki
                bl = P([[-52, -7.5], [-200, -6.0], [-205, 7.5], [-52, 7.5]])
                cv_.fill('C', bl, (255, 0, 0, 255))
                cv_.fill('M', bl, (120, 0, 120))
                cv_.stroke('M', P([[-52, 7.0], [-205, 7.0]]), (255, 255, 255), max(0.6, 0.6 * k))
                cv_.fill('M', P([[-52, -7.5], [-200, -6.0], [-200, -2.0], [-52, -2.5]]), (60, 0, 40))
                hx = 20.0
            else:
                # 鞘（黑漆）+ 鲤口金环 + 镡 + 柄
                cv_.poly(P([[-30, -10], [200, -9.5], [200, 9.5], [-30, 10]]), _col(55))
                cv_.line(P([-30, -6])[0], P([200, -5.5])[0], 1.0 * k, _col(140))                    # 漆面高光
                cv_.poly(P([[-34, -10.5], [-28, -10.5], [-28, 10.5], [-34, 10.5]]), _col(170), gold=230)
                if gap > 0.3:
                    cv_.poly(P([[-34 - gap, -7.5], [-34, -7.5], [-34, 7.5], [-34 - gap, 7.5]]), _col(185), gold=255)
                    M.append(('band', P([[-34 - gap, -7.5], [-34, -7.5], [-34, 7.5], [-34 - gap, 7.5]]), push))
                tx = -34 - gap
                cv_.poly(P([[tx - 6, -19], [tx, -19], [tx, 19], [tx - 6, 19]]), _col(150), gold=200)
                cv_.poly(P([[tx - 130, -9], [tx - 6, -9], [tx - 6, 9], [tx - 130, 9]]), _col(80))
                for i in range(14):
                    xa = tx - 12 - i * 9.0
                    cv_.poly(P([[xa, -9], [xa + 4.5, 0], [xa, 9], [xa - 4.5, 0]]), _col(150))
                hx = 6.0
            # 前臂 + 护腕
            cv_.dcur = 1
            cv_.poly(P([[hx - 26, -46], [hx + 24, -50], [hx + 44, -170], [hx - 22, -170]]), _col(70))
            cv_.poly(P([[hx - 24, -52], [hx + 25, -56], [hx + 38, -130], [hx - 20, -128]]), _col(115))
            for yy in (-62, -90, -118):
                cv_.line(P([hx - 23, yy])[0], P([hx + 30, yy - 4])[0], 1.2 * k, _col(170))
                cv_.line(P([hx - 22, yy + 3])[0], P([hx + 30, yy - 1])[0], 0.5 * k, _col(40))
            # 手背
            cv_.dcur = 2
            cv_.poly(P([[hx - 22, -50], [hx + 24, -52], [hx + 28, -16 + jit], [hx + 15, -10], [hx - 26, -12 + jit]]), _col(95))
            for i in range(3):                                                 # 掌骨筋
                cv_.line(P([hx - 10 + i * 10, -46])[0], P([hx - 14 + i * 13, -18])[0], 0.9 * k, _col(125 + 30 * tight))
            for i, kx in enumerate((-19, -7, 5, 17)):                           # 指节
                cv_.ell(P([hx + kx, -15 + jit + (1.2 if i % 3 == 0 else 0)])[0], (6.2 * k, (4.8 + 1.4 * tight) * k), angle, _col(120 + 50 * tight))
            # 四指环握（从指节越过刀柄前方）
            cv_.dcur = 3
            for i, kx in enumerate((-19, -7, 5, 17)):
                w = 11.8 - abs(i - 1.5) * 0.7
                top = -13 + jit; mid = 1.0 + (i % 2) * 0.8; bot = 10.5 - abs(i - 1.2) * 0.8
                cx_ = hx + kx + (i - 1.5) * 0.6
                q = P([[cx_, top], [cx_ + 0.3, mid], [cx_ - 0.6, bot]])
                tn = 108 - i * 7 + 25 * tight
                cv_.cap(q[0], q[1], w / 2 * k, (w / 2 - 0.4) * k, _col(tn))
                cv_.cap(q[1], q[2], (w / 2 - 0.5) * k, (w / 2 - 1.2) * k, _col(tn - 8))
                cv_.line(P([cx_ - w / 2 + 1.2, mid + 0.2])[0], P([cx_ + w / 2 - 1.2, mid - 0.2])[0], 0.6 * k, _col(28))   # 指节褶
                cv_.line(P([cx_ + w / 2 - 2.0, top + 3])[0], P([cx_ + w / 2 - 2.2, mid - 2])[0], 0.5 * k, _col(tn + 40))  # 指背高光
            # 拇指
            cv_.dcur = 4
            if mode == 'grip':
                th_ = P([[hx - 27, -34], [hx - 30, -6], [hx - 18, 6 + jit], [hx - 8, 7 + jit]])
                for a, b, r1, r2 in ((0, 1, 8, 7), (1, 2, 7, 6), (2, 3, 6, 5)):
                    cv_.cap(th_[a], th_[b], r1 * k, r2 * k, _col(110))
                cv_.ell(th_[3], (4.2 * k, 3.2 * k), angle, _col(150))                # 拇指甲
            else:
                tip = [-33 - gap * 0.92, -9]
                th_ = P([[hx - 24, -36], [hx - 30, -22], [tip[0] + 9, -14], tip])
                for a, b, r1, r2 in ((0, 1, 8, 7.5), (1, 2, 7.5, 6.5), (2, 3, 6.5, 5.5)):
                    cv_.cap(th_[a], th_[b], r1 * k, r2 * k, _col(112))
                cv_.ell(P([tip[0] + 3, -13])[0], (4.0 * k, 2.6 * k), angle, _col(160))
        else:   # ---------------- open_rain：侧视掌心朝上（手腕在左，指尖向右）
            c = ease(prog, 'io')
            cv_.dcur = 0
            cv_.poly(P([[-190, -2], [-56, -3], [-50, 14], [-190, 20]]), _col(70))              # 前臂
            cv_.poly(P([[-170, -3], [-66, -4], [-60, 14], [-170, 18]]), _col(112))             # 护腕
            for xx in (-160, -130, -100, -76):
                cv_.line(P([xx, -3])[0], P([xx + 2, 18])[0], 1.0 * k, _col(165))
            cv_.dcur = 1
            palm = P([[-58, -2], [-30, -3 + 2 * c], [0, -2 + 3 * c], [6, 3], [2, 11], [-30, 13], [-58, 13]])
            cv_.poly(palm, _col(100))
            cv_.line(P([-50, -2])[0], P([-6, -1.5 + 3 * c])[0], 0.5 * k, _col(150))               # 掌缘受光
            fing = [(0.80, 0.65, 64), (0.92, 0.45, 74), (1.00, 0.2, 86), (0.94, 0.0, 98)]          # 小指(后)→食指(前)
            for i, (ln, dy, tone) in enumerate(fing):
                base = np.array([2 - i * 0.6, 3.0 - dy * 5])
                L1, L2, L3 = 24 * ln * (1 - 0.25 * c), 15 * ln * (1 - 0.15 * c), 11 * ln
                a0 = -6 - 3 * (3 - i) + tr * 0.6 * (1 - c)
                aM = a0 - 80 * c; aP = aM - 105 * c - 5 * (1 - c); aD = aP - 75 * c - 4 * (1 - c)
                p1 = base + L1 * np.array([math.cos(aM * D2R), math.sin(aM * D2R)])
                p2 = p1 + L2 * np.array([math.cos(aP * D2R), math.sin(aP * D2R)])
                p3 = p2 + L3 * np.array([math.cos(aD * D2R), math.sin(aD * D2R)])
                q = P(np.array([base, p1, p2, p3]))
                cv_.dcur = 2 + i * 0.3
                tn = tone + 12 * c
                fat = 1 + 0.3 * c
                cv_.cap(q[0], q[1], 5.4 * ln * k * fat, 4.8 * ln * k * fat, _col(tn))
                cv_.cap(q[1], q[2], 4.7 * ln * k * fat, 4.2 * ln * k * fat, _col(tn))
                cv_.cap(q[2], q[3], 4.1 * ln * k * fat, 3.3 * ln * k * fat, _col(tn))
                cv_.circ(q[3] + (q[3] - q[2]) / (np.hypot(*(q[3] - q[2])) + 1e-6) * 0.2 * k, 1.0 * k, _col(tn + 40))
            # 拇指：沿掌侧斜出，握拳时压在指上
            cv_.dcur = 4
            tb = np.array([-38, 1.0]); ta = -28 - 22 * c
            t1 = tb + 20 * np.array([math.cos(ta * D2R), math.sin(ta * D2R)])
            tb2 = ta + 10 + 55 * c
            t2 = t1 + 15 * np.array([math.cos(tb2 * D2R), math.sin(tb2 * D2R)])
            q = P(np.array([tb, t1, t2]))
            cv_.cap(q[0], q[1], 7.0 * k, 5.6 * k, _col(112)); cv_.cap(q[1], q[2], 5.6 * k, 4.4 * k, _col(118))
        # 合成
        Ac = cv_.C[..., 3].astype(np.float32) / 255
        fr, A = _composite(fr, cv_, x0, y0, rim_color, rim_dir, rimw=max(1.2, 0.12 * k), lift=lift, tex_scale=k * 0.6)
        reg = fr[y0:y1, x0:x1]; rc = np.asarray(rim_color, np.float32)
        if Ac.max() > 0.01:                                    # 刀身金属
            Mm = cv_.M.astype(np.float32) / 255. / np.maximum(Ac, 1e-3)[..., None]
            steel = Mm[..., 0:1] * np.array([0.5, 0.52, 0.56], np.float32) + Mm[..., 0:1] ** 2 * rc * 0.4 + Mm[..., 1:2] * 0.9
            if blade_shine is not None:
                xx = (np.arange(x1 - x0)[None] + x0 - x) / k
                band = np.exp(-((xx * fs + 52 + blade_shine * 150) / 10.) ** 2).astype(np.float32)
                steel = steel + band[..., None] * Mm[..., 0:1] * 1.6
            if heat > 0: steel = steel + Mm[..., 2:3] * heat * (RED * 1.1 + GOLD * heat * 0.5)
            a3 = Ac[..., None]
            reg[:] = reg * (1 - a3) + steel * a3
        for kind, poly, s_ in M:                                # habaki 闪光
            if kind == 'band':
                gl = np.zeros(A.shape, np.float32); cv2.fillPoly(gl, [_ip(poly).reshape(-1, 1, 2)], 1.0, cv2.LINE_AA, SH)
                g = _blur_ds(gl, 2 * k) * (0.2 + 0.5 * math.sin(math.pi * min(1, s_ * 1.4)))
                reg += g[..., None] * GOLD * 0.6 + gl[..., None] * GOLD * 0.25
                ln_ = np.zeros(A.shape, np.float32)
                ctr = poly.mean(0); dv = (poly[1] - poly[0]); dv = dv / (np.hypot(*dv) + 1e-6)
                cv2.line(ln_, tuple((ctr - dv * 60 * k * s_).astype(int)), tuple((ctr + dv * 60 * k * s_).astype(int)), 1.0, 2, cv2.LINE_AA)
                reg += _blur_ds(ln_, 1.2)[..., None] * rc * 0.5 * s_
        if mode == 'open_rain' and rain > 0:                   # 雨滴落掌 + 溅射 + 握拳滴水
            lay = np.zeros(A.shape, np.float32); rng = np.random.default_rng(self.seed)
            c = ease(prog, 'io')
            n = 70
            px = rng.uniform(-160, 160, n); ph = rng.random(n); spd = rng.uniform(1.3, 2.0, n)
            for i in range(n):
                f = (t * spd[i] + ph[i]) % 1.0
                yy = -260 + f * 420
                land = (-55 < px[i] < 40) and c < 0.6
                ylim = (-3 if px[i] < 2 else -3 - (px[i] - 2) * 0.3) if land else 120
                if yy < ylim:
                    a = P([px[i] - 2, yy - 18])[0]; b = P([px[i], yy])[0]
                    cv2.line(lay, tuple(a.astype(int)), tuple(b.astype(int)), 0.55, max(1, int(0.5 * k)), cv2.LINE_AA)
                elif land and yy < ylim + 40:                  # 溅射
                    u = (yy - ylim) / 40
                    for s in (-1, 1):
                        for m in range(3):
                            sp = P([px[i] + s * (4 + m * 3) * u * 2, ylim - 10 * math.sin(math.pi * u) * (1 + m * 0.4)])[0]
                            cv2.circle(lay, tuple(sp.astype(int)), max(1, int(0.5 * k)), 0.8 * (1 - u), -1, cv2.LINE_AA)
            if c < 0.7:                                        # 掌心积水反光
                e = P([-22, -3 + 3 * c])[0]
                cv2.ellipse(lay, tuple(e.astype(int)), (int(20 * k * (1 - c)), max(1, int(1.2 * k))), angle, 0, 360, 0.35, -1, cv2.LINE_AA)
            if c > 0.5:                                        # 握拳挤出的水滴
                for m in range(4):
                    f = (t * 1.5 + m * 0.27) % 1.0
                    d = P([-6 + m * 6, 26 + f * 90 * (c - 0.4)])[0]
                    cv2.ellipse(lay, tuple(d.astype(int)), (max(1, int(1.0 * k)), max(1, int(1.8 * k))), angle, 0, 360, 0.8, -1, cv2.LINE_AA)
            reg += cv2.GaussianBlur(lay, (0, 0), 0.7)[..., None] * (0.4 + 0.6 * rc)
        if wet > 0:                                            # 湿手：皮肤高光点
            hl = np.clip(_shift(A, 2, 2) - A + 0, 0, 1) * 0
        fr[y0:y1, x0:x1] = reg
        return fr

# ============================================================== 太上皇（背光剪影）
EMP_BASE = dict(sp=0., sy=0., hp=0., hy=0., ryaw=0., ry=0.,
                rh=(6., -36., 9.), lh=(-6., -36., 9.), rpole=(1, -.2, -1), lpole=(-1, -.2, -1), scepter=0., palm=0.)
EMP_ACTIONS = {
    'stand_backlit': [(0, 'io', {}), (1, 'io', {})],
    'raise_hand_decree': [(0, 'io', {}), (.25, 'io', dict(rh=(14., -24., 6.), sp=2, hp=4)),
                          (.55, 'o5', dict(rh=(17., 14., 22.), palm=1., sp=-4, hp=-6, lh=(-8., -32., 8.))),
                          (1, 'io', dict(rh=(17., 16., 22.), palm=1., sp=-5, hp=-8, lh=(-8., -32., 8.)))],
    'point_down': [(0, 'io', {}), (.3, 'io', dict(sp=6, rh=(14., -18., 14.))),
                   (.6, 'o', dict(sp=24, hp=26, rh=(12., -22., 30.), palm=0.5, lh=(-8., -30., 6.))),
                   (1, 'io', dict(sp=26, hp=30, rh=(12., -24., 31.), palm=0.5, lh=(-8., -30., 6.)))],
    'grip_scepter': [(0, 'io', dict(rh=(16., -24., 8.), scepter=1.)), (1, 'io', dict(rh=(16., -22., 8.), scepter=1., hp=-3))],
    'head_turn_flash': [(0, 'io', dict(hy=0.)), (.35, 'o5', dict(hy=72., hp=-4)), (1, 'io', dict(hy=78., hp=-5))],
}

class Emperor:
    """太上皇：极高、冕冠（垂旒）、长发夹白丝、宽大广袖、曳地长袍。只做背光剪影。
    pose(action, phase, t, wind) → draw(fr, x, y, scale, view='front'|'back'|角度, rim_color, rim_dir, paper=0..1, burn=0..1)。
    scale = 全身像素高（含冠）。动作：stand_backlit / raise_hand_decree / point_down / grip_scepter / head_turn_flash。"""
    def __init__(self, seed=0, view='front', crown='mian'):
        rng = np.random.default_rng(seed); self.rng = rng; self.seed = seed
        self.view = view; self.crown = crown; self.t_last = None; self.S = None
        nH = 16
        th = rng.uniform(-70, 70, nH) * D2R
        self.h_anchor = np.stack([np.sin(th) * 6.0, rng.uniform(-1, 4, nH), -np.cos(th) * 5.6], 1)
        self.h_white = rng.random(nH) < 0.35
        self.hair = Chains(nH, 9, rng.uniform(5.0, 6.8, nH), drag=4.0, damp=0.97, stiff=np.outer(np.ones(nH), 0.2 * (1 - np.linspace(0, 1, 9)) ** 2 + 0.01))
        nS = 22; ang = np.linspace(0, 2 * math.pi, nS, endpoint=False)
        self.sk_ring = np.stack([np.sin(ang) * 14, np.zeros(nS), np.cos(ang) * 10], 1); self.sk_out = np.stack([np.sin(ang), np.zeros(nS), np.cos(ang)], 1)
        self.skirt = Chains(nS, 10, 80. / 9, drag=1.5, damp=0.94, ring=0.5, stiff=np.outer(np.ones(nS), 0.12 * (1 - np.linspace(0, 1, 10)) + 0.04))
        self.sleeve = {s: Chains(4, 6, np.array([[5, 5, 4, 4, 3.], [7, 7, 6, 5, 4.], [8, 8, 7, 6, 4.], [6, 6, 5, 4, 3.]]), drag=2.5,
                                 damp=0.95, stiff=0.06) for s in 'lr'}
        nb = 7
        self.liu = Chains(nb * 2, 6, 1.9, drag=1.0, damp=0.96, stiff=0.0)
        bx = np.linspace(-4.2, 4.2, nb)
        self.liu_anchor = np.concatenate([np.stack([bx, np.zeros(nb), np.full(nb, 10.5)], 1), np.stack([bx, np.zeros(nb), np.full(nb, -10.5)], 1)])

    def _sample(self, action, phase):
        keys = EMP_ACTIONS[action]; cur = dict(EMP_BASE); full = []
        for p, e, kw in keys:
            cur = dict(cur); cur.update(kw); full.append((p, e, cur))
        phase = min(max(phase, 0), 1); i = 0
        while i < len(full) - 2 and phase > full[i + 1][0]: i += 1
        (p1, _, c1), (p2, e2, c2) = full[i], full[i + 1]
        u = ease((phase - p1) / max(1e-6, p2 - p1), e2)
        return {k: _lerp_ch(c1[k], c2[k], u) for k in c1}

    def _skel(self, c):
        S = {}
        Rp = _rot(c['ryaw'], 0, 0); Pp = np.array([0, 62 + c['ry'], 0])
        Rc = Rp @ _rot(c['sy'], c['sp'], 0)
        N = Pp + Rc @ [0, 42, 0]; Rh = Rc @ _rot(c['hy'], c['hp'], 0); Hc = N + Rh @ [0, 10, 0.5]
        S.update(Rp=Rp, Pp=Pp, Rc=Rc, N=N, Rh=Rh, Hc=Hc)
        for s, sg in (('l', -1), ('r', 1)):
            sh = N + Rc @ [sg * 13, -2.5, -0.5]
            T = N + Rp @ np.asarray(c[s + 'h'])
            E, Wr = _ik(sh, T, 20, 17, Rp @ _nrm(np.asarray(c[s + 'pole'], float)))
            S[s + 'sh'] = sh; S[s + 'el'] = E; S[s + 'wr'] = Wr; S[s + 'hand'] = Wr + _nrm(Wr - E) * 3.5
        S['scepter'] = c['scepter']; S['palm'] = c['palm']
        return S

    def _anch(self, S):
        A = {}
        Rh, Hc, Rp, Pp = S['Rh'], S['Hc'], S['Rp'], S['Pp']
        A['h'] = Hc + self.h_anchor @ Rh.T
        hr = np.repeat(_nrm(self.h_anchor * [0.3, 0, 0.5] + [0, -1, 0])[:, None], 8, 1) @ Rh.T
        hr[..., 1] -= 0.8; A['h_r'] = _nrm(hr)
        A['sk'] = Pp + self.sk_ring @ Rp.T + [0, 6, 0]
        A['sk_r'] = _nrm(np.array([0, -1., 0])[None, None] + (self.sk_out @ Rp.T)[:, None] * np.linspace(0.12, 0.35, 9)[None, :, None])
        for s in 'lr':
            sh, el, wr = S[s + 'sh'], S[s + 'el'], S[s + 'wr']
            A['sl' + s] = np.stack([sh + (el - sh) * 0.5, el, el + (wr - el) * 0.4, el + (wr - el) * 0.85])
            A['sl' + s + '_r'] = np.repeat(np.array([[[0, -1., 0]]]), 4, 0).repeat(5, 1)
        top = Hc + Rh @ [0, 9.5, 0]
        A['liu'] = top + (self.liu_anchor @ (Rh @ _rx(-6 * D2R)).T)
        A['liu_r'] = np.repeat(np.array([[[0, -1., 0]]]), len(self.liu_anchor), 0).repeat(5, 1)
        S['crown_top'] = top
        return A

    def pose(self, action, phase, t, wind=0.0, **over):
        c = self._sample(action, phase); c.update({k: v for k, v in over.items() if k in EMP_BASE})
        S = self._skel(c); A = self._anch(S)
        th = (VIEWS.get(self.view, self.view) if isinstance(self.view, str) else self.view) * D2R
        wx, wy = (wind, 0.) if np.isscalar(wind) else wind
        wv = np.array([wx * math.cos(th), -wy, wx * math.sin(th)])
        cols = [(S['Hc'] - [0, 2, 0], S['Hc'] + [0, 2, 0], 7.5), (S['Pp'] + [0, 10, 0], S['N'] - [0, 3, 0], 12.0)]
        G = [(self.hair, A['h'], A['h_r'], cols), (self.skirt, A['sk'], A['sk_r'], [(S['Pp'], S['Pp'] - [0, 60, 0], 12.5)]),
             (self.sleeve['l'], A['sll'], A['sll_r'], []), (self.sleeve['r'], A['slr'], A['slr_r'], []), (self.liu, A['liu'], A['liu_r'], [])]
        if self.t_last is None or not (0 < t - self.t_last <= 0.2):
            for ch, an, r, cl in G: ch.reset(an, r)
            for k in range(50):
                for ch, an, r, cl in G: ch.step(1 / 80, an, r, wv, t - 0.6 + k / 80, cl)
        else:
            n = max(1, int(math.ceil((t - self.t_last) / 0.01)))
            for k in range(n):
                for ch, an, r, cl in G: ch.step((t - self.t_last) / n, an, r, wv, t, cl)
        self.t_last = t; self.S = S; self.c = c
        return S

    def draw(self, fr, x, y, scale, view=None, rim_color=(1.0, 0.76, 0.40), rim_dir=(0, -1), rim=1.2, lift=0.6, alpha=1.0,
             paper=0.0, burn=0.0, flip=False, ink=None, gold_trim=1.0):
        S = self.S
        if view is not None: self.view = view
        th = (VIEWS.get(self.view, self.view) if isinstance(self.view, str) else self.view) * D2R
        ct, st = math.cos(th), math.sin(th); fs = -1 if flip else 1
        sc = scale / 135.0
        def P2g(Pw):
            Pw = np.asarray(Pw, float); X = Pw[..., 0] * ct + Pw[..., 2] * st
            return np.stack([x + fs * X * sc, y - Pw[..., 1] * sc], -1)
        def DP(Pw):
            Pw = np.asarray(Pw, float); return Pw[..., 0] * st - Pw[..., 2] * ct
        allp = np.vstack([self.skirt.P.reshape(-1, 3), self.hair.P.reshape(-1, 3), self.sleeve['l'].P.reshape(-1, 3),
                          self.sleeve['r'].P.reshape(-1, 3), S['crown_top'][None] + [0, 3, 0], S['rhand'][None] + np.array([0, 50., 0]) * S['scepter']])
        x0, y0, x1, y1 = _local_canvas(fr, P2g(allp), scale * 0.06 + 6)
        if x1 - x0 < 4: return fr, {}
        cv_ = _Canvas(y1 - y0, x1 - x0); off = np.array([x0, y0])
        P2 = lambda Pw: P2g(Pw) - off
        E = []; base = 62
        Rc, N, Pp, Rh, Hc = S['Rc'], S['N'], S['Pp'], S['Rh'], S['Hc']
        tor = [N + Rc @ [xx, yy, zz] for (yy, rx, z0, z1) in ((-2, 15, -5, 4), (-14, 14, -7, 7), (-30, 13, -6.5, 6.5), (-40, 13.5, -7, 7))
               for xx in (-rx, rx) for zz in (z0, z1)] + [N + Rc @ [xx, 1.5, 0] for xx in (-4, 4)]
        hull = cv2.convexHull(P2(np.array(tor)).astype(np.float32)).reshape(-1, 2)
        lap = P2(np.array([N + Rc @ p for p in ([-4.5, 1, 2], [2, -16, 7.2], [9, -40, 7])]))
        lap2 = P2(np.array([N + Rc @ p for p in ([4.5, 1, 2], [-1, -14, 7.4])]))
        fv = DP(N + Rc @ [0, -10, 7]) > DP(N + Rc @ [0, -10, -7])
        def torso():
            cv_.poly(hull, _col(base))
            if fv:
                cv_.line(lap[0], lap[1], 1.4 * sc, _col(140), gold=int(200 * gold_trim)); cv_.line(lap[1], lap[2], 1.4 * sc, _col(140), gold=int(200 * gold_trim))
                cv_.line(lap2[0], lap2[1], 1.2 * sc, _col(140), gold=int(200 * gold_trim))
            bq = P2(np.array([N + Rc @ [-13.5, -31, 7.2], N + Rc @ [13.5, -31, 7.2], N + Rc @ [13.8, -36, 7.2], N + Rc @ [-13.8, -36, 7.2]]))
            if fv: cv_.poly(bq, _col(120, 90), gold=int(140 * gold_trim))
        E.append((DP(N), torso, 0))
        # 长袍
        P = self.skirt.P; nS, Ls = P.shape[:2]; Pn = np.roll(P, -1, 0)
        q2, qn = P2(P), P2(Pn); dq = DP((P[:, :-1] + Pn[:, 1:]) / 2)
        cen = DP(Pp)
        L3 = np.array([0, 1., 0]) * 0.6 - np.array([st, 0, -ct]) * 0.8
        t1 = Pn[:, :-1] - P[:, :-1]; t2 = P[:, 1:] - P[:, :-1]; nr = _nrm(np.cross(t2, t1))
        rad = (P[:, :-1] - Pp); rad[..., 1] = 0; nr = nr * np.sign((nr * rad).sum(-1, keepdims=True) + 1e-9)
        lam = np.clip(nr @ L3, 0, 1)
        for i in range(nS):
            for j in range(Ls - 1):
                quad = np.array([q2[i, j], qn[i, j], qn[i, j + 1], q2[i, j + 1]])
                tn = base * (0.6 + 0.8 * lam[i, j]) * (1.1 if i % 2 else 0.9)
                gl = int(150 * gold_trim) if j == Ls - 2 else 0
                E.append((dq[i, j], (lambda quad=quad, tn=tn, gl=gl: cv_.poly(quad, _col(tn), gold=gl)), cen - dq[i, j]))
        # 广袖 + 手臂
        for s in 'lr':
            sh, el, wr, hd = S[s + 'sh'], S[s + 'el'], S[s + 'wr'], S[s + 'hand']
            q = P2(np.array([sh, el, wr, hd])); SL = self.sleeve[s].P; sq = P2(SL); d = DP((el + wr) / 2)
            palm = S['palm'] if s == 'r' else 0
            def arm(q=q, sq=sq, palm=palm, s=s):
                cv_.cap(q[0], q[1], 5.5 * sc, 6.5 * sc, _col(base))
                cv_.cap(q[1], q[2], 6.5 * sc, 7.5 * sc, _col(base))
                for k in range(3):
                    for j in range(5):
                        cv_.poly(np.array([sq[k, j], sq[k + 1, j], sq[k + 1, j + 1], sq[k, j + 1]]), _col(base * (0.85 + 0.1 * k)))
                hem = sq[:, -1]
                for k in range(3): cv_.line(hem[k], hem[k + 1], 1.0 * sc, _col(150), gold=int(220 * gold_trim))
                dv = q[3] - q[2]; ln = np.hypot(*dv) + 1e-6; u = dv / ln; nv = np.array([-u[1], u[0]])
                if palm > 0.5:                                          # 张开手掌（掌心向前）
                    cv_.ell(q[3], (3.2 * sc, 3.8 * sc), math.degrees(math.atan2(u[1], u[0])), _col(110))
                    for f in range(4):
                        a = q[3] + u * 2.5 * sc + nv * (f - 1.5) * 1.6 * sc
                        cv_.cap(a, a + (u * (5.5 - abs(f - 1.3)) + nv * (f - 1.5) * 0.5) * sc, 0.8 * sc, 0.65 * sc, _col(110))
                    cv_.cap(q[3] - nv * 2 * sc, q[3] - nv * 4.5 * sc + u * 3 * sc, 0.9 * sc, 0.7 * sc, _col(110))
                else:
                    cv_.circ(q[3], 2.8 * sc, _col(105))
            E.append((d, arm, 0))
        if S['scepter'] > 0.5:
            hd = S['rhand']; top = hd + np.array([0, 34, 2.]); bot = hd - np.array([0, 46, 0.])
            sq3 = P2(np.array([bot, top, top + [0, 6, 0]]))
            def scep(sq3=sq3):
                cv_.cap(sq3[0], sq3[1], 1.1 * sc, 1.1 * sc, _col(120), gold=200)
                cv_.ell(sq3[1] + (sq3[2] - sq3[1]) * 0.5, (3.0 * sc, 4.2 * sc), 0, _col(170), gold=255)
                cv_.ell(sq3[1] + (sq3[2] - sq3[1]) * 0.5, (1.4 * sc, 2.0 * sc), 0, _col(40))
                for m in range(4): cv_.ell(sq3[0] + (sq3[1] - sq3[0]) * (0.15 + m * 0.22), (1.8 * sc, 0.7 * sc), 0, _col(170), gold=230)
            E.append((DP(hd) + 0.5, scep, 0))
        # 头 + 冕冠 + 旒 + 长发
        hp = [[math.cos(b) * math.sin(a) * 5.6, math.sin(b) * 7.0, math.cos(b) * math.cos(a) * 6.2]
              for a in np.linspace(0, 2 * math.pi, 14, endpoint=False) for b in (-1.1, -0.5, 0, 0.6, 1.2)]
        hq = P2(Hc + np.array(hp) @ Rh.T); hh = cv2.convexHull(hq.astype(np.float32)).reshape(-1, 2)
        pq = P2(Hc + np.array([[0, y_ * 1.05, z_ * 1.05] for z_, y_ in HEAD_PROFILE]) @ Rh.T)
        neck = P2(np.array([N - Rc @ [0, 2, 0], Hc - Rh @ [0, 4, 0]]))
        crown = []
        if self.crown == 'mian':
            ctop = S['crown_top']; Rk = Rh @ _rx(-6 * D2R)
            brd = [ctop + Rk @ [xx, yy, zz] for xx in (-5.5, 5.5) for yy in (-0.6, 0.6) for zz in (-11, 11)]
            body = [Hc + Rh @ [xx, yy, zz] for xx in (-3.5, 3.5) for yy in (5, 9.4) for zz in (-3.5, 3.5)]
            crown = (cv2.convexHull(P2(np.array(brd)).astype(np.float32)).reshape(-1, 2), cv2.convexHull(P2(np.array(body)).astype(np.float32)).reshape(-1, 2))
        else:
            knot = Hc + Rh @ [0, 8.5, -1]; pin = P2(np.array([knot + Rh @ [-9, 0.5, 0], knot + Rh @ [9, -0.5, 0]]))
            crown = (P2(knot), pin)
        def head():
            cv_.cap(neck[0], neck[1], 3.6 * sc, 3.4 * sc, _col(base))
            cv_.poly(hh, _col(80)); cv_.poly(pq, _col(80))
            hc2 = P2(Hc + Rh @ [0, 1.5, -1.2]); cv_.ell(hc2, (6.3 * sc, 7.4 * sc), 0, _col(40))
            if self.crown == 'mian':
                cv_.poly(crown[1], _col(90), gold=int(160 * gold_trim)); cv_.poly(crown[0], _col(130), gold=int(220 * gold_trim))
            else:
                cv_.circ(crown[0], 3.2 * sc, _col(50)); cv_.line(crown[1][0], crown[1][1], 0.9 * sc, _col(170), gold=255)
        E.append((DP(Hc), head, 0))
        lq = P2(self.liu.P); ld = DP(self.liu.P).mean(1)
        for i in range(self.liu.C):
            def liu(q=lq[i]):
                for j in range(len(q) - 1): cv_.line(q[j], q[j + 1], max(0.6, 0.25 * sc), _col(150), gold=200)
                for j in range(1, len(q)): cv_.circ(q[j], 0.55 * sc, _col(170), gold=230)
            E.append((ld[i] + 0.3, liu, 0))
        hq2 = P2(self.hair.P); hd2 = DP(self.hair.P).mean(1)
        for i in range(self.hair.C):
            tn = 200 if self.h_white[i] else 40
            E.append((hd2[i], (lambda q=hq2[i], tn=tn: cv_.strand(q, 2.4 * sc, 0, _col(tn))), DP(Hc) + 3 - hd2[i]))
        E.sort(key=lambda e: e[0])
        for d, fn, b in E:
            cv_.dcur = d + b; fn()
        bdict = dict(prog=burn, y0=y, y1=y - scale, seed=self.seed + 3) if burn > 0 else None
        fr, A = _composite(fr, cv_, x0, y0, rim_color, rim_dir, rim=rim, rimw=float(np.clip(scale * 0.004, 1, 3.5)),
                           lift=lift, alpha=alpha, ink=ink, tex_scale=sc * 0.7, paper=paper, burn=bdict,
                           paper_col=(0.95, 0.9, 0.78))
        info = dict(bbox=(x0, y0, x1, y1), head=tuple(P2g(Hc)), hand=tuple(P2g(S['rhand'])))
        return fr, info


# ##########################################################################################
# ============================================================== v2 渲染层（角色组第二轮：精致度）
# 接口不变：Swordsman.draw / profile_cu / HandCU.draw / Emperor.draw / _composite 签名与返回值完全一致。
# rig.set_quality('v1'|'v2') 可切回旧画法做前后对比（默认 v2；无 skia 时自动走 v1）。
# 新增：卡通体积明暗（伪法线：深度分区距离场 → 主光赛璐璐 + 天光环境 + 接触遮蔽 + 地面 AO）、
#       loft 躯干（真实腰线）、可变半径肢体（关节过渡）、分层衣摆（前开衩/里衬/褶皱网格渐变）、
#       3D 头部（多凸块并集侧脸轮廓 + 眼/眉/鼻/唇/耳特征，转头可读）、成束头发（发团 + 发束 + 高光环）、
#       护腕/腰封/刀鞘细节、出刀拖影形变（smear）。
QUALITY = 'v2'
def set_quality(q):
    """'v2'（默认，精致版）或 'v1'（第一轮画法，用于对比）。"""
    global QUALITY
    QUALITY = q


def _cel(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def _shade2(A, D, rd, R, ground=None, key_soft=0.12, occ_k=None, depth_thr=0.9):
    """伪法线体积明暗。A 覆盖、D 深度（-1e4=空）、rd 屏幕光向（光来自 rd 一侧）、R 体积半径（像素，≈肢体半径）。
    返回 (key, amb, ao, nz)：key 主光(赛璐璐软边 0..1)、amb 天光(0.6..1.1)、ao 遮蔽(0..1)。"""
    h, w = A.shape
    Dm = np.where(A > 0.35, D, np.float32(-1e4)).astype(np.float32)
    E = A < 0.5
    dx = np.abs(np.diff(Dm, axis=1)) > depth_thr; dy = np.abs(np.diff(Dm, axis=0)) > depth_thr
    E[:, :-1] |= dx; E[:, 1:] |= dx; E[:-1] |= dy; E[1:] |= dy
    dist = cv2.distanceTransform((~E).astype(np.uint8), cv2.DIST_L2, 3)
    u = np.clip(dist / max(R, 1.0), 0, 1)
    hgt = np.sqrt(u * (2 - u))
    hgt = cv2.GaussianBlur(hgt, (0, 0), max(0.8, R * 0.22))
    gx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3) * (R / 8.0)
    gy = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3) * (R / 8.0)
    inv = 1.0 / np.sqrt(gx * gx + gy * gy + 1.0)
    nx, ny, nz = -gx * inv, -gy * inv, inv
    ndl = nx * rd[0] + ny * rd[1]
    key = _cel(ndl, 0.10 - key_soft, 0.10 + key_soft)
    amb = 0.62 + 0.45 * np.clip(-ny * 0.9 + 0.35, 0, 1)
    # 接触遮蔽：靠近更近部件处变暗（落影/AO）
    k = int(max(3, occ_k if occ_k is not None else R * 1.6)) | 1
    Dn = cv2.dilate(Dm, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    occ = np.clip((Dn - Dm - depth_thr) / 3.0, 0, 1) * (A > 0.02)
    occ = cv2.GaussianBlur(occ, (0, 0), k * 0.35) * (A > 0.02)
    ao = 1.0 - 0.55 * occ
    if ground is not None:
        yy = np.arange(h, dtype=np.float32)[:, None]
        g0, g1 = ground
        ao = ao * (0.62 + 0.38 * _cel(yy, g0, g1))
    return key, amb, ao, nz, dist


_V4C = dict(on=False)          # 当前合成是否 v4 人物（皮肤调色 / 细丝少吃轮廓光）
SKIN4 = 206                     # v4 肤色 tone（v3 188）
SKIN4_RGB = (0.318, 0.305, 0.306)   # v4 肤色调（v3 为通用冷调 0.255/0.258/0.285）
IRIS4 = dict(limbal=(0.20, 0.10, 0.035), mid=(0.70, 0.40, 0.12), inner=(0.95, 0.66, 0.26), pupil=(0.025, 0.018, 0.012), gain=0.85)

def _iris4(out, cv_, alpha):
    """v4 琥珀瞳着色：在虹膜可见处（金通道 213 仍保留 = 没被头发/眼睑盖住）按径向分层上色：外圈深棕、中间琥珀、瞳周暖金、黑瞳；上缘受眼睑投影。"""
    G = cv_.G; h_, w_ = G.shape
    for c2, rx, ry in cv_.iris4:
        rx = max(rx, 0.8); ry = max(ry, 0.8)
        xa, xb = int(max(0, c2[0] - rx * 1.4)), int(min(w_, c2[0] + rx * 1.4 + 1))
        ya, yb = int(max(0, c2[1] - ry * 1.4)), int(min(h_, c2[1] + ry * 1.4 + 1))
        if xb <= xa or yb <= ya: continue
        yy, xx = np.mgrid[ya:yb, xa:xb].astype(np.float32)
        r = np.sqrt(((xx + 0.5 - c2[0]) / rx) ** 2 + ((yy + 0.5 - c2[1]) / ry) ** 2)
        m = np.clip((G[ya:yb, xa:xb].astype(np.float32) - 120) / 80, 0, 1) * np.clip((1.12 - r) / 0.12, 0, 1)
        if m.max() <= 0: continue
        L_, M_, I_, P_ = (np.asarray(IRIS4[k], np.float32) for k in ('limbal', 'mid', 'inner', 'pupil'))
        t1 = np.clip((r - 0.62) / 0.36, 0, 1)[..., None]
        col = M_ * (1 - t1) + L_ * t1
        t2 = np.clip((0.60 - r) / 0.22, 0, 1)[..., None] * np.clip((yy - c2[1]) / ry + 0.6, 0, 1)[..., None]
        col = col * (1 - t2) + I_ * t2
        tp = np.clip((0.36 - r) / 0.07, 0, 1)[..., None]
        col = col * (1 - tp) + P_ * tp
        lid = np.clip(((yy - c2[1]) / ry + 0.15) / 0.6, 0.35, 1.0)[..., None]        # 上睑投影
        col = col * lid * IRIS4['gain']
        a3 = (m * alpha)[..., None]
        out[ya:yb, xa:xb] = out[ya:yb, xa:xb] * (1 - a3) + col * a3

FILL = dict(amb=0.62, skin=0.42)   # v2.1 亮度：天光权重（v2 原 0.50）、肤色补光
def set_fill(**kw): FILL.update(kw)

def _comp2(fr, cv_, x0, y0, rim_color, rim_dir, rim, rimw, lift, alpha, ink, R, ground=None, key=1.0,
           tex_scale=1.0, inner_thr=3.5, spec_tone=None, return_A=False, paper=0.0, paper_col=(0.92, 0.88, 0.78),
           burn=None, met_cb=None):
    """v2 合成：tone/red/gold/金属 + 体积明暗 + 轮廓光 → fr。met_cb(col, A, inv) 可选：刀身金属自行着色。"""
    C = cv_.C.astype(np.float32) * (1 / 255.)
    A = C[..., 0]; h_, w_ = A.shape
    if A.max() <= 0: return (fr, A, None) if return_A else (fr, A)
    inv = 1.0 / np.maximum(A, 1e-3)
    tone = C[..., 1] * inv; red = np.clip(C[..., 2] * inv, 0, 1); met = np.clip(C[..., 3] * inv, 0, 1)
    gold = np.clip(cv_.G.astype(np.float32) / 255. * inv, 0, 1)
    rd = np.array(rim_dir, float); rd /= max(np.linalg.norm(rd), 1e-6)
    Dm = cv_.D
    kk, amb, ao, nz, dist = _shade2(A, Dm, rd, R, ground)
    # 布纹（细，低幅）
    ts = max(1, int(round(tex_scale)))
    tt = _tile(noise_tex(512, seed=3, base=40, octaves=3), (x0 // ts) % 512, (y0 // ts) % 512, h_ // ts + 2, w_ // ts + 2)
    tt = cv2.resize(tt, ((w_ // ts + 2) * ts, (h_ // ts + 2) * ts), interpolation=cv2.INTER_LINEAR)[:h_, :w_]
    inkc = INK if ink is None else np.asarray(ink, np.float32)
    rc = np.asarray(rim_color, np.float32)
    if _V4C['on']:      # v4：脸上主光过渡柔化（不再沿鼻梁硬切成半明半暗）
        skm = _cel(tone, 0.50, 0.60) * (1 - red) * (1 - met)
        kk = kk * (1 - skm) + _blur_ds(kk.astype(np.float32), max(2.0, R * 1.2)) * skm * 0.8 + 0.2 * skm
    shade = (FILL['amb'] * amb + 0.95 * key * kk) * ao * (0.93 + 0.14 * tt)
    # 肤色补光（v2.1）：皮肤（高 tone、非红非金属）在逆光下也保留可读的面部明暗，避免侧脸/回头变成暗块
    skinm = _cel(tone, 0.50, 0.60) * (1 - red) * (1 - met)
    shade = shade + skinm * FILL['skin'] * (0.55 + 0.45 * amb) * (0.6 + 0.4 * ao)
    lum = tone * shade * lift
    cool = np.array([0.255, 0.258, 0.285], np.float32)
    if _V4C['on']:      # v4：皮肤用近中性的冷白（设定图苍白肤色），其余保持冷调
        sm = (skinm * (A > 0.5))[..., None]
        col = inkc[None, None] + lum[..., None] * (cool * (1 - sm) + np.asarray(SKIN4_RGB, np.float32) * sm)
    else:
        col = inkc[None, None] + lum[..., None] * cool
    col = col + (kk * ao * tone * 0.10 * key)[..., None] * rc                # 受光面染一点光色
    redc = np.array([0.60, 0.05, 0.042], np.float32)
    rshade = (0.30 + 0.85 * tone) * (0.55 * amb + 0.75 * key * kk) * ao * min(1.4, 0.6 + 0.4 * lift)
    col = col * (1 - red[..., None]) + (redc * rshade[..., None]) * red[..., None]
    col = col * (1 - gold[..., None] * 0.65) + GOLD[None, None] * (0.34 * (0.45 + tone) * (0.5 + 0.7 * kk) * gold * 0.65)[..., None]
    glow_add = None
    if burn is not None and burn.get('prog', 0) > 0:
        bp = burn['prog']; yb0, yb1 = burn['y0'], burn['y1']
        nzb = _tile(noise_tex(512, seed=burn.get('seed', 5), base=12, octaves=5), x0 % 512, y0 % 512, h_, w_)
        yy = (np.arange(h_, dtype=np.float32)[:, None] + y0 - yb0) / (yb1 - yb0)
        f = yy * 0.8 + nzb * 0.35 - 0.05
        th_ = bp * 1.15
        keep = np.clip((f - th_) / 0.012, 0, 1)
        charb = np.clip(1 - (f - th_) / 0.05, 0, 1) * keep
        glow_add = np.exp(-((f - th_) / 0.010) ** 2) * (A > 0.05)
        col = col * (1 - charb[..., None] * 0.85)
        A = A * keep
    if paper > 0:
        fib = _tile(noise_tex(512, seed=21, base=60, octaves=3), x0 % 512, y0 % 512, h_, w_)
        thick = np.clip(dist / (rimw * 12 + 1), 0, 1)
        trans = (0.55 + 0.45 * fib) * (1 - 0.55 * thick) * (1 - np.clip(tone - 0.3, 0, 1))
        pc = np.asarray(paper_col, np.float32) * (0.35 + 0.65 * rc / max(rc.max(), 1e-3))
        col = col * (1 - paper) + (pc[None, None] * trans[..., None] + col * 0.2) * paper
    if met_cb is not None and met.max() > 0.01:
        col = met_cb(col, A, inv, met)
    if rim > 0:
        dx, dy = rd
        r1 = np.clip(A - _shift(A, -dx * rimw, -dy * rimw), 0, 1)
        sw_ = rimw * 4
        r2 = _blur_ds(np.clip(A - _shift(A, -dx * sw_, -dy * sw_), 0, 1), sw_ * 0.7 + 0.5) * A
        Ds = _shift(Dm, -dx * rimw * 1.5, -dy * rimw * 1.5)
        inner = (((Dm - Ds) > inner_thr) * (Ds > -1e3)).astype(np.float32)
        inner = cv2.GaussianBlur(inner, (0, 0), 1.0); inner = np.clip((inner - 0.12) * 2.2, 0, 1) * A
        thin = np.clip(dist / max(1.0, rimw * 1.2), 0.35, 1.0) if not _V4C['on'] else np.clip((dist - 0.6) / max(1.0, rimw * 2.0), 0.06, 1.0) ** 1.5                  # 极细的东西（飞丝）少吃边缘光，避免满屏白线
        if _V4C['on']:      # v4：细丝内轮廓光也按粗细衰减，否则发丝间满是白线
            hm = (tone < 0.5) * (1 - red) * (1 - met)
            inner = inner * (1 - hm * (1 - thin)); r2 = r2 * (1 - 0.4 * hm)
        rl = (r1 * 0.95 * thin + inner * 0.38 * kk + r2 * 0.34 + met * r2 * 0.6) * rim
        col = col + rc[None, None] * (rl / np.maximum(A, 1e-3))[..., None] * (A > 0.02)[..., None]
    H_, W_ = fr.shape[:2]
    xa, ya = max(0, x0), max(0, y0); xb, yb = min(W_, x0 + w_), min(H_, y0 + h_)
    if xb <= xa or yb <= ya: return (fr, A, col) if return_A else (fr, A)
    sl = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    a3 = (A[sl] * alpha)[..., None]
    fr[ya:yb, xa:xb] = fr[ya:yb, xa:xb] * (1 - a3) + col[sl] * a3
    if glow_add is not None:
        g = glow_add[sl]
        fr[ya:yb, xa:xb] += (g[..., None] * (GOLD * 1.6 + 0.3) + _blur_ds(g, 6)[..., None] * (RED * 1.5 + GOLD * 0.4)) * alpha
    return (fr, A, col) if return_A else (fr, A)


_composite_v1 = _composite
def _composite(fr, cv_, x0, y0, rim_color=(0.85, 0.9, 1.0), rim_dir=(-0.7, -0.7), rim=1.0, rimw=2.0, lift=1.0, alpha=1.0,
               ink=None, tex_scale=1.0, soft=None, paper=0.0, paper_col=(0.92, 0.88, 0.78), inner_thr=3.5, burn=None, vol=None):
    """接口同 v1；v2 下加体积明暗（vol=体积半径像素，缺省按 rimw 推）。"""
    if QUALITY != 'v2' or BACKEND != 'skia':
        return _composite_v1(fr, cv_, x0, y0, rim_color, rim_dir, rim, rimw, lift, alpha, ink, tex_scale, soft, paper, paper_col,
                             inner_thr, burn)
    bdict = burn
    return _comp2(fr, cv_, x0, y0, rim_color, rim_dir, rim, rimw, lift, alpha, ink, vol if vol else rimw * 7, None,
                  tex_scale=tex_scale, inner_thr=inner_thr, paper=paper, paper_col=paper_col, burn=bdict)


# ---------------------------------------------------------------- 3D 头部（头部系：x 右, y 上, z 前；原点 Hc）
def _ellip_pts(c, r, na=18, bs=(-1.2, -0.75, -0.3, 0.15, 0.6, 1.05, 1.45), keep=None):
    out = []
    for b in bs:
        for a in np.linspace(0, 2 * math.pi, na, endpoint=False):
            p = [c[0] + r[0] * math.cos(b) * math.sin(a), c[1] + r[1] * math.sin(b), c[2] + r[2] * math.cos(b) * math.cos(a)]
            if keep is None or keep(p): out.append(p)
    return np.array(out)

def _mirror(pts):
    pts = np.asarray(pts, float); m = pts.copy(); m[:, 0] *= -1
    return np.vstack([pts, m])

HEAD2 = dict(
    cran=_ellip_pts((0, 0.9, -0.55), (4.85, 5.55, 5.75)),
    jaw=_mirror([[4.15, -0.6, 2.4], [3.95, -3.3, -0.2], [3.4, -4.6, 1.2], [2.4, -5.6, 3.3], [1.25, -6.25, 4.35],
                 [3.3, 1.6, 4.1], [3.55, -1.4, 3.6], [1.9, 2.15, 5.15], [1.2, 4.1, 4.9], [0.0, 2.25, 5.72], [0.0, 4.3, 5.1],
                 [0.0, -2.55, 5.25], [0.0, -4.55, 5.15], [0.0, -6.45, 4.1], [1.0, -2.6, 5.0]]),
    nose=_mirror([[0.0, 1.45, 5.55], [0.45, 1.1, 5.3], [0.0, -1.35, 6.85], [0.0, -1.85, 6.6], [1.0, -1.95, 5.55],
                  [0.0, -2.3, 5.85], [0.55, -2.3, 5.3]]),
    ulip=_mirror([[0.0, -2.3, 5.8], [0.0, -2.95, 6.02], [1.35, -3.15, 5.05], [0.0, -3.42, 5.72], [0.85, -2.4, 5.2]]),
    llip=_mirror([[0.0, -3.5, 5.72], [0.0, -3.85, 5.86], [1.05, -3.55, 4.95], [0.0, -4.3, 5.42]]),
    chin=_mirror([[0.0, -4.55, 5.3], [0.0, -5.25, 5.72], [0.0, -5.95, 5.45], [0.0, -6.45, 4.55], [1.35, -5.35, 4.95],
                  [1.3, -6.1, 4.3], [0.8, -4.6, 5.05]]),
)
# 发团（头盖）：略大的椭球，去掉脸部
HAIR_CAP = _ellip_pts((0, 1.25, -0.75), (5.35, 6.05, 6.3), na=22, bs=(-1.0, -0.6, -0.2, 0.2, 0.6, 0.95, 1.25, 1.5),
                      keep=lambda p: not (p[2] > 1.2 and p[1] < 3.6 - max(0, abs(p[0]) - 3.4) * 2.2) and p[1] > -3.2)


def _hair_cap3():
    """v3 发盖扇区：椭球面采样，保留发际线以上的点。发际线连续：中分缝最高 → 弧形降到额角 → 鬓角（耳前）→ 耳后/后脑垂到后颈。
    扇区要窄（发际线有台阶时宽扇区的凸包会横跨眼睛，形成 v2 那种“黑条”）。"""
    c, r = (0, 1.25, -0.75), (5.3, 6.0, 6.25)
    def hl(aa):
        if aa < 1.15: return 3.15 - 1.9 * (aa / 1.15) ** 1.7 + (0.35 if aa < 0.12 else 0.0)
        if aa < 1.45: return 1.25 - 3.05 * (aa - 1.15) / 0.30
        if aa < 2.1: return -1.8 - 1.4 * (aa - 1.45) / 0.65
        return -3.2 - 1.0 * min(1.0, (aa - 2.1) / 0.6)
    pts_a, P = [], []
    for b in np.linspace(-1.05, 1.5, 15):
        for a in np.linspace(-math.pi, math.pi, 72, endpoint=False):
            p = [c[0] + r[0] * math.cos(b) * math.sin(a), c[1] + r[1] * math.sin(b), c[2] + r[2] * math.cos(b) * math.cos(a)]
            if p[1] > hl(abs(a)): pts_a.append(a); P.append(p)
    pts_a = np.array(pts_a); P = np.array(P)
    out = []
    for ca in np.linspace(-math.pi, math.pi, 28, endpoint=False):
        d = np.angle(np.exp(1j * (pts_a - ca)))
        m = (np.abs(d) < 0.16) | ((P[:, 1] > 6.0) & (np.abs(d) < 0.9))
        if m.sum() >= 3: out.append((ca, P[m]))
    return out
HAIR_CAP3 = _hair_cap3()


def _eye_pts(sg, gaze=(0.0, 0.0), open_=1.0):
    """单眼（sg=+1 角色右眼 / -1 左眼）上睑、下睑、虹膜 3D 点（头部系）。外眼角略上挑，冷峻。"""
    u = np.linspace(-1, 1, 15)            # -1 内眼角 → +1 外眼角
    cx, cy = 2.05, 0.55
    x = cx + 1.12 * u
    zf = lambda xx: 5.15 - 0.165 * xx ** 2
    yu = cy + 0.50 * open_ * (1 - u ** 2) ** 0.75 + 0.16 * u - 0.05 * (u < -0.6)
    yl = cy - 0.24 * (1 - u ** 2) ** 1.2 + 0.10 * u
    up = np.stack([sg * x, yu, zf(x) + 0.05], 1); lo = np.stack([sg * x, yl, zf(x)], 1)
    a = np.linspace(0, 2 * math.pi, 20, endpoint=False)
    ic = np.array([sg * (cx + gaze[0] * 0.5 - 0.06), cy + 0.06 + gaze[1] * 0.3, zf(cx) + 0.12])
    ex = _nrm(np.array([1.0, 0, -0.165 * 2 * cx * sg * sg]) * [sg, 1, 1]); ey = np.array([0, 1.0, 0])
    ir = ic + 0.5 * (np.cos(a)[:, None] * ex + np.sin(a)[:, None] * ey * 1.02)
    pu = ic + 0.22 * (np.cos(a)[:, None] * ex + np.sin(a)[:, None] * ey)
    return up, lo, ir, pu, ic


# ---- v3 脸型（按设定图测量 lib/ref/guitu_hero_ref.py：清瘦、尖下巴、高颧骨、眼位下移、细长眼）
HEAD3 = dict(
    cran=_ellip_pts((0, 0.9, -0.55), (4.55, 5.55, 5.75)),
    jaw=_mirror([[4.15, 1.0, 2.4], [3.95, -2.5, -0.2], [3.25, -4.6, 0.6], [2.45, -5.65, 2.8], [1.15, -6.55, 4.15],
                 [3.55, -1.0, 3.45], [3.4, 0.6, 4.0], [2.0, 0.6, 5.1], [1.2, 3.0, 4.9], [0.0, 0.9, 5.65], [0.0, 3.0, 5.1],
                 [2.95, -3.0, 3.0], [0.0, -3.5, 5.3], [0.0, -5.3, 5.15], [0.0, -6.75, 4.0], [1.0, -3.6, 5.0]]),
    nose=_mirror([[0.0, 0.3, 5.5], [0.42, 0.0, 5.25], [0.0, -2.6, 6.7], [0.0, -2.95, 6.5], [0.92, -3.05, 5.5],
                  [0.0, -3.35, 5.8], [0.5, -3.35, 5.3]]),
    ulip=_mirror([[0.0, -3.4, 5.75], [0.0, -3.95, 5.92], [1.22, -4.25, 5.0], [0.0, -4.3, 5.65], [0.8, -3.5, 5.15]]),
    llip=_mirror([[0.0, -4.35, 5.62], [0.0, -4.62, 5.72], [0.92, -4.35, 4.9], [0.0, -5.05, 5.35]]),
    chin=_mirror([[0.0, -5.3, 5.22], [0.0, -5.95, 5.5], [0.0, -6.45, 5.2], [0.0, -6.8, 4.3], [0.88, -6.0, 4.8],
                  [0.62, -6.6, 4.2], [0.7, -5.3, 4.98]]),
)
# v4 脸型：下颌更窄更尖（V 形下巴），颅骨下缘收进，避免正面“方下巴”
HEAD4 = dict(HEAD3)
HEAD4['cran'] = _ellip_pts((0, 0.9, -0.55), (4.5, 5.55, 5.75), keep=lambda p: p[1] > -2.6 or p[2] < 0.5)
HEAD4['jaw'] = _mirror([[4.1, 1.0, 2.4], [3.85, -2.3, -0.2], [3.0, -4.3, 0.6], [2.0, -5.55, 2.6], [0.85, -6.55, 4.05],
                        [3.5, -1.0, 3.45], [3.4, 0.6, 4.0], [2.0, 0.6, 5.1], [1.2, 3.0, 4.9], [0.0, 0.9, 5.65], [0.0, 3.0, 5.1],
                        [2.7, -3.0, 3.0], [0.0, -3.5, 5.3], [0.0, -5.3, 5.15], [0.0, -6.8, 4.0], [1.0, -3.6, 5.0],
                        [3.75, -1.8, 2.9], [3.45, -3.2, 2.4], [2.75, -4.7, 2.2], [1.75, -5.9, 3.3], [3.9, 0.2, 3.0]])   # 颊—颌外凸弧（去直边）
HEAD4['chin'] = _mirror([[0.0, -5.3, 5.22], [0.0, -5.95, 5.5], [0.0, -6.45, 5.2], [0.0, -6.82, 4.3], [0.7, -6.0, 4.8],
                         [0.45, -6.65, 4.2], [0.6, -5.3, 4.98]])
_FYR = np.array([(-9.0, -9.3), (-6.45, -6.75), (-3.45, -4.25), (-1.35, -2.75), (0.55, -0.45), (2.2, 1.45), (5.0, 4.6), (9.0, 9.0)])

def _face3(p):
    """v2 面部特征坐标 → v3（y 分段重映射 + 下半脸收窄成尖下巴）。"""
    p = np.array(p, float); y = p[..., 1]
    y2 = np.interp(y, _FYR[:, 0], _FYR[:, 1])
    tap = 1 - 0.16 * np.clip((-y2 - 1.0) / 5.5, 0, 1) * (p[..., 2] > 1.0)
    p[..., 0] = p[..., 0] * tap; p[..., 1] = y2
    return p

def _eye_pts3(sg, gaze=(0.0, 0.0), open_=1.0, v4=False):
    """v3 单眼：细长（宽高比≈3）、外眼角上挑、眼位下移；虹膜被上睑压住一部分（冷）。v4：略开、虹膜略大（琥珀色要读得出）。"""
    u = np.linspace(-1, 1, 15)
    cx, cy, hw, op = (1.62, -0.45, 1.0, 0.34) if not v4 else (1.62, -0.47, 1.02, 0.42)
    x = cx + hw * u
    zf = lambda xx: 5.12 - 0.165 * xx ** 2
    yu = cy + op * open_ * (1 - u ** 2) ** 0.7 + 0.15 * u - 0.06 * (u < -0.65)
    yl = cy - 0.13 * (1 - u ** 2) ** 1.1 + 0.11 * u
    up = np.stack([sg * x, yu, zf(x) + 0.05], 1); lo = np.stack([sg * x, yl, zf(x)], 1)
    a = np.linspace(0, 2 * math.pi, 20, endpoint=False)
    ic = np.array([sg * (cx + gaze[0] * 0.45 - 0.05), cy + 0.02 + gaze[1] * 0.25, zf(cx) + 0.12])
    ex = _nrm(np.array([1.0, 0, -0.165 * 2 * cx]) * [sg, 1, 1]); ey = np.array([0, 1.0, 0])
    ir = ic + (0.37 if v4 else 0.34) * (np.cos(a)[:, None] * ex + np.sin(a)[:, None] * ey)
    pu = ic + 0.13 * (np.cos(a)[:, None] * ex + np.sin(a)[:, None] * ey)
    return up, lo, ir, pu, ic

# ---------------------------------------------------------------- v4 脸（体积明暗 + 有形体的鼻/唇 + 琥珀瞳 + 毛流剑眉）
def _face4(cv_, P2, W, Wf, Rh, vdir, sc, skin, hair_tone, facing, side, feat, eyefn):
    sk_ = _sk
    lit = -1 if side < 0 else 1          # 受光侧（角色系 x 符号）：与 v3 鼻影一致，背光侧 = -lit
    def vis_(v): return float((Rh @ _nrm(np.array(v, float))) @ vdir)
    def soft(pts3, ax, ang, tone, a, bl):
        cv_.paint_in(sk_.path_ellipse(P2(W(pts3)), (ax[0] * sc, ax[1] * sc), ang), (tone,), a, blur=bl * sc)
    # 体积：眼窝、颧下凹、颞侧、下颌下缘、鼻侧
    for sg in (-1, 1):
        if vis_([sg * 0.45, 0.05, 1.0]) < -0.15: continue
        dk = 1.0 if sg == -lit else 0.75
        soft([sg * 1.55, 0.05, 4.7], (1.35, 0.7), 0, skin * 0.62, 0.5 * dk, 0.55)               # 眼窝（眉下）
        soft([sg * 0.55, -0.55, 5.3], (0.45, 0.7), 0, skin * 0.62, 0.5 * dk, 0.35)               # 内眼角—鼻根
        soft([sg * 2.75, -3.05, 3.6], (0.75, 1.75), -28 * sg, skin * 0.58, 0.62 * dk, 0.75)      # 颧骨下凹
        soft([sg * 3.75, 0.9, 2.3], (0.8, 2.0), 0, skin * 0.66, 0.45 * dk, 0.8)                  # 颞侧
        soft([sg * 2.35, -1.55, 4.15], (1.2, 0.42), -12 * sg, skin * 1.12, 0.35 * (1.6 - dk), 0.5)  # 颧骨亮面
    jaw = P2(Wf(np.array([[4.0, -3.0, -0.2], [3.4, -4.5, 1.3], [2.3, -5.6, 3.3], [1.1, -6.25, 4.4], [0, -6.45, 4.15],
                          [-1.1, -6.25, 4.4], [-2.3, -5.6, 3.3], [-3.4, -4.5, 1.3], [-4.0, -3.0, -0.2]])))
    cv_.paint_in(sk_.path_poly(jaw, closed=False, smooth=True), (skin * 0.45,), 0.55, blur=0.4 * sc, stroke=0.7 * sc)
    if not feat: return
    # 耳
    for sg in (-1, 1):
        en = Rh @ [sg, 0, 0.15]
        if en @ vdir < 0.25: continue
        ring = Wf(np.array([[sg * 4.75, 0.2 + 1.35 * math.sin(a), -0.35 + 0.75 * math.cos(a) - 0.25 * (math.sin(a) < 0)]
                            for a in np.linspace(0, 2 * math.pi, 14, endpoint=False)]))
        q = P2(ring)
        cv_.paint_in(sk_.path_poly(q, smooth=True), (skin * 0.88,), 1.0)
        cv_.paint_in(sk_.path_poly(q, smooth=True), (skin * 0.45,), 0.8, stroke=0.22 * sc)
        inner = P2(Wf(np.array([[sg * 4.8, 0.2 + 0.8 * math.sin(a), -0.25 + 0.4 * math.cos(a)] for a in np.linspace(0.3, 5.0, 9)])))
        cv_.paint_in(sk_.path_poly(inner, closed=False, smooth=True), (skin * 0.5,), 0.7, stroke=0.16 * sc)
    # 剑眉：浓黑实心底 + 毛流短笔（眉头竖向上、眉身斜向外上）
    for sg in (-1, 1):
        if vis_([sg * 0.5, 0.1, 1.0]) < -0.05: continue
        uu = np.linspace(0, 1, 11)
        bx = 0.40 + 2.45 * uu
        bw = np.stack([sg * bx, 0.16 + 0.52 * uu - 0.07 * uu * uu, 5.45 - 0.165 * bx ** 2 * 0.8 + 0.1], 1)
        q = P2(W(bw)); d = np.gradient(q, axis=0); nn = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
        wd = (0.30 - 0.22 * uu ** 1.2)[:, None] * sc
        cv_.paint_in(sk_.path_poly(np.vstack([q + nn * wd * 0.8, (q - nn * wd * 0.8)[::-1]]), smooth=True), (hair_tone * 0.3,), 1.0)
        rng = np.random.default_rng(77 + sg)
        for k in range(int(26 * min(1.0, sc / 20) + 6)):
            u0 = rng.uniform(0, 0.95); i = int(u0 * 10)
            c0 = q[i] + (q[min(i + 1, 10)] - q[i]) * (u0 * 10 - i) + nn[i] * wd[i] * rng.uniform(-0.9, 0.9)
            tg = q[min(i + 1, 10)] - q[i]; tg = tg / (np.hypot(*tg) + 1e-6)
            up = -nn[i] if (nn[i][1] > 0) else nn[i]            # 屏幕上方
            dirv = tg * (0.35 + 0.65 * min(1, u0 * 2.5)) + up * (1.0 - 0.6 * min(1, u0 * 2.5)); dirv /= np.hypot(*dirv) + 1e-6
            ln = (0.30 + 0.25 * rng.random()) * sc * (1 - 0.4 * u0)
            pts = np.array([c0 - dirv * ln * 0.4, c0 + dirv * ln * 0.6])
            cv_.path(sk_.path_poly(_tpoly(np.array([pts[0], (pts[0] + pts[1]) / 2, pts[1]]), np.array([0.07, 0.06, 0.0]) * sc + 0.4)),
                     _col(hair_tone * rng.uniform(0.2, 0.7)), depth=False)
    # 眼：眼白 + 虹膜（金通道占位，合成后着琥珀色）+ 粗上睑线（眼尾上挑）+ 双眼皮 + 下睑
    cv_.iris4 = []
    for sg in (-1, 1):
        if vis_([sg * 0.42, 0.0, 1.0]) < 0.0: continue
        up, lo, ir, pu, ic = eyefn(sg)
        qu, ql = P2(W(up)), P2(W(lo))
        white = sk_.path_poly(np.vstack([qu, ql[::-1]]), smooth=True)
        cv_.paint_in(white, (skin * 1.0,), 1.0)
        irq = P2(W(ic + (ir - ic) * 1.08))
        irp = sk_.path_and(sk_.path_poly(irq, smooth=True), white)
        cv_.paint_in(irp, (70,), 1.0)
        cv_.path(irp, (255, 70, 0, 0), gold=213, depth=False)
        c2 = P2(W(ic)); rx = (irq[:, 0].max() - irq[:, 0].min()) / 2; ry = (irq[:, 1].max() - irq[:, 1].min()) / 2
        cv_.iris4.append((c2, rx, ry))
        tail = qu[-1] + (qu[-1] - qu[-3]) * 1.1 + np.array([0, -0.18 * sc])
        lid = np.vstack([qu, tail[None]])
        prof = np.sin(np.linspace(0.12, 1.0, len(lid)) * math.pi * 0.82) ** 0.6
        lp = sk_.path_poly(_tpoly(lid, (0.16 + 0.34 * prof) * sc), smooth=True)
        cv_.paint_in(lp, (6,), 1.0); cv_._tgt('G', lp, 0)
        cv_.paint_in(sk_.path_and(sk_.path_poly(qu + [0, 0.22 * sc], closed=False, smooth=True), white), (skin * 0.45,), 0.4,
                     blur=0.15 * sc, stroke=0.35 * sc)
        crease = P2(W(up[3:14] + np.array([0, 0.30, 0.0])))
        cv_.paint_in(sk_.path_poly(crease, closed=False, smooth=True), (skin * 0.45,), 0.85, stroke=0.10 * sc)
        cv_.paint_in(sk_.path_poly(ql[4:], closed=False, smooth=True), (skin * 0.5,), 0.85, stroke=0.09 * sc)
        cv_.paint_in(sk_.path_poly(ql[3:] + [0, 0.25 * sc], closed=False, smooth=True), (skin * 0.7,), 0.4, blur=0.2 * sc, stroke=0.35 * sc)
    # 鼻：鼻梁亮线（受光侧）、背光侧鼻侧面、鼻头高光、鼻底投影、鼻翼、鼻孔
    if facing > 0.15:
        sh = P2(Wf(np.array([[-lit * 0.6, 1.0, 5.3], [-lit * 0.62, -0.4, 5.85], [-lit * 0.7, -1.6, 6.1], [-lit * 0.8, -2.0, 5.8]])))
        cv_.paint_in(sk_.path_poly(sh, closed=False, smooth=True), (skin * 0.55,), 0.75, blur=0.35 * sc, stroke=0.8 * sc)
        hl = P2(Wf(np.array([[lit * 0.12, 0.9, 5.6], [lit * 0.14, -0.4, 6.15], [lit * 0.12, -1.5, 6.55]])))
        cv_.paint_in(sk_.path_poly(hl, closed=False, smooth=True), (min(250, skin * 1.16),), 0.6, blur=0.12 * sc, stroke=0.22 * sc)
        cv_.paint_in(sk_.path_ellipse(P2(Wf([lit * 0.1, -1.75, 6.6])), (0.32 * sc, 0.22 * sc), 0), (min(250, skin * 1.15),), 0.55, blur=0.12 * sc)
    cv_.paint_in(sk_.path_ellipse(P2(Wf([0, -2.35, 5.85])), (1.0 * sc, 0.32 * sc), 0), (skin * 0.5,), 0.6, blur=0.2 * sc)   # 鼻底
    for sg in (-1, 1):
        if vis_([sg * 0.6, -0.4, 0.8]) < -0.05: continue
        wing = P2(Wf(np.array([[sg * 0.3, -2.2, 5.95], [sg * 0.88, -2.05, 5.6], [sg * 1.05, -1.6, 5.4], [sg * 0.85, -1.25, 5.45]])))
        cv_.paint_in(sk_.path_poly(wing, closed=False, smooth=True), (skin * 0.6,), 0.7, blur=0.06 * sc, stroke=0.09 * sc)
        cv_.paint_in(sk_.path_ellipse(P2(Wf([sg * 0.95, -1.75, 5.45])), (0.35 * sc, 0.45 * sc), 0), (skin * 0.7,), 0.45, blur=0.2 * sc)
        if facing > 0.3:
            cv_.paint_in(sk_.path_ellipse(P2(Wf([sg * 0.48, -2.15, 5.78])), (0.18 * sc, 0.08 * sc), 0), (skin * 0.35,), 0.85, blur=0.03 * sc)
    # 唇：上唇（朝下，暗）、下唇（朝上，亮 + 高光）、口裂、唇下影、人中
    xs = np.linspace(-1.2, 1.2, 11)
    mv = np.array([vis_([x_ * 0.5, 0, 1.0]) for x_ in xs]) > -0.1
    if mv.sum() >= 3:
        xs = xs[mv]
        ul_top = Wf(np.array([[x_, -2.95 - 0.12 * abs(x_) + 0.1 * np.exp(-((abs(x_) - 0.35) / 0.2) ** 2), 5.95 - 0.38 * x_ * x_] for x_ in xs]))
        mline = Wf(np.array([[x_, -3.45 - 0.06 * abs(x_), 5.78 - 0.38 * x_ * x_] for x_ in xs]))
        ll_bot = Wf(np.array([[x_ * 0.85, -3.95 + 0.25 * (x_ / 1.2) ** 2, 5.6 - 0.36 * x_ * x_] for x_ in xs]))
        qt, qm, qb = P2(ul_top), P2(mline), P2(ll_bot)
        cv_.paint_in(sk_.path_poly(np.vstack([qt, qm[::-1]]), smooth=True), (skin * 0.68, 40), 0.85, blur=0.05 * sc)
        cv_.paint_in(sk_.path_poly(np.vstack([qm, qb[::-1]]), smooth=True), (skin * 0.84, 30), 0.75, blur=0.08 * sc)
        mid = len(qb) // 2
        cv_.paint_in(sk_.path_ellipse((qm[mid] + qb[mid]) / 2 + [0, 0.05 * sc], (0.45 * sc, 0.1 * sc), 0), (min(250, skin * 1.05), 20), 0.45, blur=0.08 * sc)
        cv_.paint_in(sk_.path_poly(qm, closed=False, smooth=True), (skin * 0.3,), 0.95, stroke=0.10 * sc)
        cv_.paint_in(sk_.path_poly(qb + [0, 0.18 * sc], closed=False, smooth=True), (skin * 0.55,), 0.55, blur=0.18 * sc, stroke=0.4 * sc)
        if facing > 0.4:
            ph_ = P2(Wf(np.array([[0, -2.4, 5.9], [0, -2.9, 5.95]])))
            cv_.paint_in(sk_.path_poly(ph_, closed=False), (skin * 0.78,), 0.4, blur=0.12 * sc, stroke=0.35 * sc)

def _cap4(cv_, P2, W, Hc, vdir, sc, hair_tone, S):
    """v4 头盖上的细发丝：从发际线梳向发髻（高马尾），可见面才画；只画在已有覆盖内（paint_in）。"""
    rng = np.random.default_rng(911)
    c, r = np.array([0, 1.25, -0.75]), np.array([5.42, 6.1, 6.35])
    tie = np.array([0, 7.15, -2.3])
    n = int(70 * min(1.0, sc / 18) * HAIR_DETAIL + 14)
    for k in range(n):
        a0 = rng.uniform(-2.9, 2.9)
        hl = 2.9 - 1.6 * min(1, abs(a0) / 1.2) if abs(a0) < 1.5 else -1.5 - 1.2 * min(1, (abs(a0) - 1.5) / 1.2)
        b0 = math.asin(np.clip((hl - c[1]) / r[1], -1, 1))
        p0 = c + r * [math.cos(b0) * math.sin(a0), math.sin(b0), math.cos(b0) * math.cos(a0)]
        uu = np.linspace(0, 1, 9)[:, None] ** rng.uniform(0.8, 1.2)
        L = p0 + (tie - p0) * uu
        dv = L - c; dv /= np.linalg.norm(dv / r, axis=1, keepdims=True); L = c + dv * 1.01 + (tie - c) * 0
        L += np.sin(uu * math.pi) * rng.normal(0, 0.25, 3) * [1, 0.3, 1]
        Wp = W(L); nrm = _nrm((L - c) / r ** 2) @ (S['Rh'].T)
        vis = nrm @ vdir > 0.08
        if vis.sum() < 3: continue
        q = P2(Wp)[vis]
        tn = hair_tone * (rng.uniform(1.6, 3.0) if rng.random() < 0.35 else rng.uniform(0.3, 0.8))
        cv_.paint_in(_sk.path_poly(q, closed=False, smooth=True), (min(118, tn),), rng.uniform(0.5, 0.9), stroke=max(0.5, rng.uniform(0.05, 0.11) * sc))

def _collar4(cv_, P2, S, sc):
    """v4 立领：颈根前半圈的外袍领口（暗）+ 暗红内领边，盖住颈根 → 颈不再显得过长（设定图交领贴颈）。"""
    Rc, N = S['Rc'], S['N']
    a = np.linspace(-1.75, 1.75, 15)
    ring = lambda y, rx, rz, zc: np.stack([np.sin(a) * rx, np.full_like(a, y), np.cos(a) * rz + zc], 1) @ Rc.T + N
    lo, hi = ring(-1.2, 4.2, 3.3, 0.4), ring(1.0, 3.0, 2.7, 0.5)
    vis = (np.cos(a)[:, None] * 0 + 1)[:, 0] > 0
    q = np.vstack([P2(lo), P2(hi)[::-1]])
    cv_.path(_sk.path_poly(q, smooth=True), _col(60))
    cv_.paint_in(_sk.path_poly(P2(ring(0.75, 3.05, 2.75, 0.5)), closed=False, smooth=True), (70, 160), 1.0, stroke=0.35 * sc)

def _fringe4(cv_, P2, W, Rh, vdir, sc, hair_tone, seed=5):
    """v4 发际线碎发：沿额前弧形发际线垂下的短细丝，打散发盖的硬边（细碎刘海）。"""
    rng = np.random.default_rng(seed)
    n = int(60 * min(1.0, sc / 18) * HAIR_DETAIL + 8)
    c, r = np.array([0, 1.25, -0.75]), np.array([5.42, 6.1, 6.35])
    for k in range(n):
        a0 = rng.choice([-1, 1]) * (0.08 + 1.3 * rng.random() ** 1.3)
        hl = 2.9 - 1.6 * min(1, abs(a0) / 1.2) if abs(a0) < 1.5 else -1.5
        b0 = math.asin(np.clip((hl + 0.5 - c[1]) / r[1], -1, 1))
        p0 = c + r * 1.03 * np.array([math.cos(b0) * math.sin(a0), math.sin(b0), math.cos(b0) * math.cos(a0)])
        nrm = _nrm(Rh @ ((p0 - c) / r ** 2))
        if nrm @ vdir < 0.05: continue
        L = rng.uniform(1.5, 3.6) * (1.0 - 0.35 * min(1, abs(a0) / 1.3))
        side = math.copysign(1, a0)
        d = np.array([side * rng.uniform(0.35, 0.8), -1.0, 0.15 - 0.1 * abs(a0)])
        uu = np.linspace(0, 1, 7)[:, None]
        pts = p0 + d * L * uu + np.array([side * 0.35, 0.25, -0.15]) * L * uu ** 2     # 中分后向两侧扫开的发帘细丝
        q = P2(W(pts))
        w = (rng.uniform(0.05, 0.11) * sc + 0.5) * (1 - uu[:, 0]) ** 0.8
        cv_.path(_sk.path_poly(_tpoly(q, w)), _col(hair_tone * rng.uniform(0.4, 1.6)), depth=False)


def _draw_head2(cv_, P2, DP, S, sc, vdir, L3, skin=165, hair_tone=34, detail=1.0, E=None, hd0=0.0):
    """头部 v2：多凸块并集（侧脸轮廓）+ 五官 + 耳 + 发盖。返回绘制函数列表 [(depth, fn, bias)]。"""
    Rh, Hc = S['Rh'], S['Hc']
    W = lambda p: Hc + np.asarray(p, float) @ Rh.T
    V3 = HAIR_V3
    V4 = V3 and HAIR_V4
    Wf = (lambda p: W(_face3(p))) if V3 else W
    HD = (HEAD4 if V4 else HEAD3) if V3 else HEAD2
    eyefn = (lambda sg, *a, **k: _eye_pts3(sg, *a, v4=True, **k)) if V4 else (_eye_pts3 if V3 else _eye_pts)
    out = []
    face_n = Rh @ [0, 0, 1.0]
    facing = float(face_n @ vdir)                       # 1=正脸 0=侧脸 -1=后脑
    side = float((Rh @ [1.0, 0, 0]) @ vdir)              # >0 角色右侧朝镜头
    pieces = [cv2.convexHull(P2(W(np.vstack([HD['cran'], HD['jaw']]))).astype(np.float32)).reshape(-1, 2)]
    for k in ('nose', 'ulip', 'llip', 'chin'):
        pieces.append(cv2.convexHull(P2(W(HD[k])).astype(np.float32)).reshape(-1, 2))
    big = sc > 5.5
    feat = sc > 7.0 and facing > -0.35
    neck = P2(np.array([S['N'] - S['Rc'] @ [0, -1.4 if V4 else 1.5, 0], W([0, -3.2, -0.8]), W([0, -4.6, 1.2])]))

    def headfn():
        # 颈：胸锁乳突肌斜线（侧面）
        cv_.path(_sk.path_limb(neck[:2], ([2.45 * sc, 2.05 * sc] if V3 else [3.05 * sc, 2.65 * sc]), k=2)[0], _col(skin * 0.86))
        if V4 and big:      # 下巴在颈上的投影
            cv_.paint_in(_sk.path_ellipse(P2(W([0, -6.4, 2.2])), (2.1 * sc, 1.1 * sc), 0), (skin * 0.5,), 0.6, blur=0.7 * sc)
        cv_.polys(pieces, _col(skin), smooth=V4)
        if V4: _collar4(cv_, P2, S, sc)
        if not big: return
        if V4:
            _face4(cv_, P2, W, Wf, Rh, vdir, sc, skin, hair_tone, facing, side, feat, eyefn)
            return
        # 颧下/下颌阴影、眼窝（内绘，软）
        sk_ = _sk
        for sg in (-1, 1):
            vis = float((Rh @ _nrm(np.array([sg * 0.45, 0.05, 1.0]))) @ vdir)
            if vis < -0.15: continue
            ec = P2(W([sg * 1.65, -0.3, 4.45] if V3 else [sg * 2.0, 0.75, 4.7]))
            cv_.paint_in(sk_.path_ellipse(ec, (1.55 * sc, 1.05 * sc), 0), (skin * 0.62,), 0.55, blur=0.6 * sc)
            ch = P2(W([sg * 3.05, -2.55, 3.25] if V3 else [sg * 3.3, -2.6, 3.6]))
            cv_.paint_in(sk_.path_ellipse(ch, (0.9 * sc, 1.9 * sc), 15 * sg), (skin * 0.72,), 0.45 * min(1, sc / 10), blur=0.9 * sc)
        jaw_line = P2(Wf(np.array([[4.0, -3.4, -0.2], [3.3, -4.7, 1.3], [2.3, -5.7, 3.3], [1.1, -6.3, 4.4], [0, -6.5, 4.1]])))
        cv_.paint_in(sk_.path_poly(jaw_line, closed=False, smooth=True), (skin * 0.55,), 0.35, blur=0.35 * sc, stroke=0.5 * sc)
        if not feat: return
        # 耳
        for sg in (-1, 1):
            en = Rh @ [sg, 0, 0.15]
            if en @ vdir < 0.25: continue
            ring = Wf(np.array([[sg * 4.75, 0.2 + 1.35 * math.sin(a), -0.35 + 0.75 * math.cos(a) - 0.25 * (math.sin(a) < 0)]
                               for a in np.linspace(0, 2 * math.pi, 14, endpoint=False)]))
            q = P2(ring)
            cv_.paint_in(sk_.path_poly(q, smooth=True), (skin * 0.9,), 1.0)
            cv_.paint_in(sk_.path_poly(q, smooth=True), (skin * 0.45,), 0.8, stroke=0.25 * sc)
            inner = P2(Wf(np.array([[sg * 4.8, 0.2 + 0.8 * math.sin(a), -0.25 + 0.4 * math.cos(a)] for a in np.linspace(0.3, 5.0, 9)])))
            cv_.paint_in(sk_.path_poly(inner, closed=False, smooth=True), (skin * 0.5,), 0.7, stroke=0.18 * sc)
        # 眉（粗、内低外高，冷峻）
        for sg in (-1, 1):
            vis = float((Rh @ _nrm(np.array([sg * 0.5, 0.1, 1.0]))) @ vdir)
            if vis < -0.05: continue
            if V3:   # 剑眉：粗、平直上挑，眉头低而钝、眉尾细而高
                bw = np.array([[sg * (0.42 + 2.5 * u), 0.14 + 0.50 * u - 0.05 * u * u, 5.45 - 0.165 * (0.42 + 2.5 * u) ** 2 * 0.8 + 0.1]
                               for u in np.linspace(0, 1, 9)])
                wd = (0.24 - 0.17 * np.linspace(0, 1, 9) ** 1.3)[:, None] * sc
            else:
                bw = np.array([[sg * (0.65 + 2.75 * u), 1.72 + 0.62 * u - 0.18 * u * u, 5.45 - 0.165 * (0.65 + 2.75 * u) ** 2 * 0.8 + 0.15]
                               for u in np.linspace(0, 1, 9)])
                wd = (0.34 - 0.2 * np.linspace(0, 1, 9) ** 1.5)[:, None] * sc
            q = P2(W(bw)); d = np.gradient(q, axis=0); nn = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
            cv_.paint_in(sk_.path_poly(np.vstack([q + nn * wd, (q - nn * wd)[::-1]]), smooth=True), (hair_tone * (0.45 if V3 else 0.7),), 1.0 if V3 else 0.95)
        # 眼
        for sg in (-1, 1):
            vis = float((Rh @ _nrm(np.array([sg * 0.42, 0.0, 1.0]))) @ vdir)
            if vis < 0.0: continue
            up, lo, ir, pu, ic = eyefn(sg)
            qu, ql = P2(W(up)), P2(W(lo))
            white = sk_.path_poly(np.vstack([qu, ql[::-1]]), smooth=True)
            cv_.paint_in(white, (skin * 1.18,), 1.0)
            irp = sk_.path_and(sk_.path_poly(P2(W(ir)), smooth=True), white)
            if V3:   # 琥珀瞳：金通道着色（后画的头发会把金通道擦掉 → 眼神光据此判定是否被发遮挡）
                cv_.paint_in(irp, (78,), 1.0)
                cv_.path(irp, (255, 78, 0, 0), gold=215, depth=False)
                cv_.paint_in(sk_.path_and(sk_.path_poly(P2(W(ic + (ir - ic) * 0.62)), smooth=True), white), (110,), 0.55, blur=0.12 * sc)
            else:
                cv_.paint_in(irp, (34,), 1.0)
            cv_.paint_in(sk_.path_and(sk_.path_poly(P2(W(pu)), smooth=True), white), (6,), 1.0)
            # 上睑阴影落在眼球上
            cv_.paint_in(sk_.path_and(sk_.path_poly(qu + [0, 0.35 * sc], closed=False, smooth=True), white), (20,), 0.55,
                         blur=0.25 * sc, stroke=0.55 * sc)
            # 上睑线（粗，外眼角拖出眼尾）+ 双眼皮细线 + 下睑
            tail = qu[-1] + (qu[-1] - qu[-3]) * 0.9
            lid = np.vstack([qu, tail[None]])
            d = np.gradient(lid, axis=0); nn = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
            prof = np.sin(np.linspace(0.12, 1.0, len(lid)) * math.pi * 0.82) ** 0.6
            wl = (0.07 + 0.2 * prof)[:, None] * sc
            cv_.paint_in(sk_.path_poly(np.vstack([lid + nn * wl, (lid - nn * wl)[::-1]]), smooth=True), (8,), 1.0)
            crease = P2(W(up[3:13] + np.array([0, 0.26 if V3 else 0.36, 0.0])))
            cv_.paint_in(sk_.path_poly(crease, closed=False, smooth=True), (skin * 0.5,), 0.8, stroke=0.12 * sc)
            cv_.paint_in(sk_.path_poly(ql[5:], closed=False, smooth=True), (skin * 0.55,), 0.8, stroke=0.1 * sc)
        # 鼻：鼻梁暗侧 + 鼻翼 + 鼻孔
        nl = 1 if side < 0 else -1                       # 背光侧
        if facing > 0.15:
            br = P2(Wf(np.array([[nl * 0.55, 1.2, 5.3], [nl * 0.5, -0.4, 6.0], [nl * 0.6, -1.5, 6.3]])))
            cv_.paint_in(sk_.path_poly(br, closed=False, smooth=True), (skin * 0.62,), 0.55, blur=0.25 * sc, stroke=0.45 * sc)
        for sg in (-1, 1):
            nv = float((Rh @ _nrm(np.array([sg * 0.6, -0.4, 0.8]))) @ vdir)
            if nv < -0.05: continue
            wing = P2(Wf(np.array([[sg * 0.25, -2.2, 5.95], [sg * 0.85, -2.05, 5.6], [sg * 1.05, -1.65, 5.45]])))
            cv_.paint_in(sk_.path_poly(wing, closed=False, smooth=True), (skin * 0.45,), 0.85, stroke=0.13 * sc)
            if facing > 0.3:
                cv_.paint_in(sk_.path_ellipse(P2(Wf([sg * 0.5, -2.15, 5.75])), (0.22 * sc, 0.1 * sc), 0), (skin * 0.3,), 0.9)
        # 唇：口裂线 + 下唇阴影
        mouth = P2(Wf(np.array([[x_, -3.45 - 0.05 * abs(x_), 5.72 - 0.38 * x_ * x_] for x_ in np.linspace(-1.3, 1.3, 9)])))
        mz = np.array([float((Rh @ _nrm(np.array([x_ * 0.5, 0, 1.0]))) @ vdir) for x_ in np.linspace(-1.3, 1.3, 9)])
        ok = mz > -0.1
        if ok.sum() >= 2:
            cv_.paint_in(sk_.path_poly(mouth[ok], closed=False, smooth=True), (skin * 0.36,), 0.95, stroke=0.13 * sc)
            ll = P2(Wf(np.array([[x_, -4.3, 5.35 - 0.3 * x_ * x_] for x_ in np.linspace(-0.8, 0.8, 5)])))
            cv_.paint_in(sk_.path_poly(ll, closed=False, smooth=True), (skin * 0.6,), 0.5, blur=0.2 * sc, stroke=0.3 * sc)
    out.append((DP(Hc), headfn, 0.0))
    # 发盖（头顶 + 后脑 + 鬓）
    capq = P2(W(HAIR_CAP))
    cap = cv2.convexHull(capq.astype(np.float32)).reshape(-1, 2)
    if V3:
        # v3 发盖：按方位角分扇区的凸包并集，前额是中分的弧形发际线（设定图），而不是 v2 那种横切的一条直线。
        # 朝后的扇区按自身深度排序（正面时在脸后），朝前/两侧的扇区盖在头皮上。
        cap = []
        for k_, (ca, cpts) in enumerate(HAIR_CAP3):
            hull = cv2.convexHull(P2(W(cpts)).astype(np.float32)).reshape(-1, 2)
            if math.cos(ca) < -0.25:
                out.append((DP(W(cpts.mean(0))), (lambda hull=hull: cv_.polys([hull], _col(hair_tone), smooth=V4)), 0.0))
            else:
                cap.append(hull)
    ring = np.array([[5.2 * math.cos(b) * math.sin(a), 1.2 + 6.0 * math.sin(b), -0.75 + 6.2 * math.cos(b) * math.cos(a)]
                     for a, b in [(a_, 0.85) for a_ in np.linspace(-2.6, 2.6, 22)]])
    ringq = P2(W(ring)); rv = (W(ring) - Hc) @ vdir > -0.5
    part = P2(W(np.array([[0.4 * math.sin(u * 3), 1.2 + 6.05 * math.sin(b_), -0.75 + 6.3 * math.cos(b_)] for u, b_ in
                          zip(np.linspace(0, 1, 8), np.linspace(1.15, 0.2, 8))])))
    def capfn():
        if isinstance(cap, list): cv_.polys(cap, _col(hair_tone), smooth=V4)
        else: cv_.poly(cap, _col(hair_tone))
        if big and V4:
            _cap4(cv_, P2, W, Hc, vdir, sc, hair_tone, S)
            _fringe4(cv_, P2, W, Rh, vdir, sc, hair_tone)
        elif big:
            # 高光环（天使环）：分段短束高光，随头转
            seg = np.nonzero(rv)[0]
            for i in seg[::2]:
                j = min(i + 2, len(ringq) - 1)
                if not rv[j]: continue
                cv_.paint_in(_sk.path_poly(ringq[i:j + 1], closed=False, smooth=True), (hair_tone + 70,), 0.75, blur=0.15 * sc,
                             stroke=0.55 * sc)
            cv_.paint_in(_sk.path_poly(part, closed=False, smooth=True), (hair_tone * 0.4,), 0.6, stroke=0.25 * sc)
    out.append((DP(Hc) + 0.4, capfn, 0.0))
    eyes = []
    for sg in (-1, 1):
        vis = float((Rh @ _nrm(np.array([sg * 0.42, 0.0, 1.0]))) @ vdir)
        if vis > 0.05:
            _, _, _, _, ic = eyefn(sg); eyes.append((vis, P2(W(ic + np.array([-0.12 * sg, 0.18, 0.1])))))
    return out, eyes, facing


def _clump(cv_, q, w0, w1, tone, sc, hl=40, hl_side=1, red=0, depth=True, prof='taper'):
    """一束头发：渐细填充 + 一侧高光线。q (n,2) 局部像素点，w0/w1 根/梢宽（像素）。"""
    q = np.asarray(q, float)
    if len(q) < 2: return
    if len(q) >= 3: q = _upsample(q, 3)
    n = len(q); u = np.linspace(0, 1, n)
    d = np.gradient(q, axis=0); nn = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
    if prof == 'taper':
        pr = np.clip(0.75 + 1.2 * u, 0, 1) * (1 - u) ** 0.85
    else:
        pr = np.sin(np.pi * np.clip(u * 0.9 + 0.08, 0, 1)) ** 0.6
    w = (w1 + (w0 - w1) * pr)[:, None] * 0.5
    poly = np.vstack([q + nn * w, (q - nn * w)[::-1]])
    P = _sk.path_poly(poly, smooth=True)
    cv_.path(P, _col(tone, red), depth=depth)
    if hl and w0 > 2.2:
        m0, m1 = max(1, n // 6), max(n // 6 + 2, int(n * 0.62))
        hq = q[m0:m1] + nn[m0:m1] * w[m0:m1] * 0.35 * hl_side
        cv_.paint_in(_sk.path_poly(hq, closed=False, smooth=True), (tone + hl, red), 0.8, blur=max(0.3, w0 * 0.06),
                     stroke=max(0.6, w0 * 0.16))
        if w0 > 6:
            cv_.paint_in(_sk.path_poly(q[1:-2] - nn[1:-2] * w[1:-2] * 0.55 * hl_side, closed=False, smooth=True), (tone * 0.45, red),
                         0.6, blur=w0 * 0.08, stroke=w0 * 0.18)


# ---------------------------------------------------------------- v4 发丝
def _tpoly(q, w):
    """沿折线 q 的渐细带多边形（w 每点全宽）。"""
    d = np.gradient(q, axis=0); nn = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
    h = (np.asarray(w, float) * 0.5)[:, None]
    return np.vstack([q + nn * h, (q - nn * h)[::-1]])

def _lock4(cv_, q, w0, tone, sc, seed, hl_side=1, splay=1.0, sheen=1.0, base=True, nmax=22, wmin=0.55, red=0, hl_band=(0.10, 0.62)):
    """v4 一束头发 = 暗色发团底（窄、尖）+ 多根细丝（宽度递减、横向抖动、梢分叉散开、长短不齐）+ 少量高光丝。
    q (n,2) 局部像素中心线，w0 根部宽（像素）。细丝数 ∝ 宽度 × HAIR_DETAIL。"""
    q = np.asarray(q, float)
    if len(q) < 2: return
    if len(q) >= 3: q = _upsample(q, 3)
    n = len(q); u = np.linspace(0, 1, n)
    d = np.gradient(q, axis=0); nn = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))]
    rng = np.random.default_rng(seed)
    env = np.clip(0.7 + 1.6 * u, 0, 1) * (1 - 0.55 * u)                 # 发束包络：根部收、梢部不收到一点（留给细丝散开）
    if base and w0 > 2.0:                                                # 底层暗色剪影：窄、在 0.85 处收尖
        m = u <= 0.86
        wb = w0 * 0.58 * np.clip(0.75 + 1.4 * u, 0, 1) * np.clip(1 - u / 0.86, 0, 1) ** 0.8
        cv_.path(_sk.path_poly(_tpoly(q[m], wb[m]), smooth=True), _col(tone * 0.55, red))
    N = int(np.clip(w0 / 2.6, 2, nmax) * HAIR_DETAIL + 0.5)
    N = max(2 if w0 > 1.2 else 1, N)
    sw = max(wmin, min(w0 * 1.25 / N, 0.11 * sc + 0.6))                 # 单丝根宽（像素）
    strands = []
    for k in range(N):
        f = ((k + 0.5) / N - 0.5) * 0.92 + rng.normal(0, 0.05)
        Lk = rng.uniform(0.72, 1.02) if k % 4 else rng.uniform(0.9, 1.06)
        L_ = max(3, int(n * min(Lk, 1.0)))
        if Lk > 1.0 and n > 3:                                            # 少数丝略超出发束末端
            ext = q[-1] + (q[-1] - q[-2]) * (Lk - 1.0) * n * 0.5
            qq = np.vstack([q, ext[None]]); nq = np.vstack([nn, nn[-1:]]); uu = np.r_[u, 1.0 + (Lk - 1.0)]; ee = np.r_[env, env[-1]]
            aa = np.r_[arc, arc[-1] + np.linalg.norm(ext - q[-1])]
        else:
            qq, nq, uu, ee, aa = q[:L_], nn[:L_], u[:L_], env[:L_], arc[:L_]
        v = uu / max(uu[-1], 1e-6)
        jit = (np.sin(aa / (w0 * 1.1 + 4) * rng.uniform(0.7, 1.5) + rng.uniform(0, 6.3)) * 0.09
               + np.sin(aa / (w0 * 0.35 + 2) * rng.uniform(0.7, 1.5) + rng.uniform(0, 6.3)) * 0.03) * (0.3 + v)
        spl = splay * (v ** 2.2) * rng.normal(0, 0.55) * (1.0 + abs(f))   # 梢分叉散开
        off = (f * ee + jit + spl * 0.8) * w0
        cq = qq + nq * off[:, None]
        wv = sw * rng.uniform(0.6, 1.25) * np.clip(1 - v, 0, 1) ** 0.75
        r = rng.random()
        tn = tone * (rng.uniform(0.45, 0.85) if r < 0.45 else rng.uniform(0.9, 1.45))
        strands.append((tn, cq, wv, v, f))
    strands.sort(key=lambda s_: s_[0])
    for tn, cq, wv, v, f in strands:
        cv_.path(_sk.path_poly(_tpoly(cq, wv)), _col(tn, red))
    if sheen > 0 and N >= 2:                                             # 高光丝：只在受光一侧、发束中段（冷月光 sheen）
        nh = max(1, int(N * 0.3))
        for tn, cq, wv, v, f in strands[-nh:]:
            if f * hl_side < -0.25: continue
            m = (v > hl_band[0]) & (v < hl_band[1])
            if m.sum() < 3: continue
            hw_ = wv[m] * 0.55 * np.sin(np.linspace(0, math.pi, m.sum())) ** 0.7
            cv_.path(_sk.path_poly(_tpoly(cq[m], hw_)), _col(min(100, tone + 42 * sheen + rng.uniform(0, 20)), red), depth=False)

def _fly4(cv_, q, sc, tone, seed):
    """v4 飞发：一根极细、带弧度、两端尖的发丝。"""
    q = np.asarray(q, float)
    if len(q) < 3: return
    q = _upsample(q, 3); n = len(q); u = np.linspace(0, 1, n)
    d = np.gradient(q, axis=0); nn = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
    L = np.linalg.norm(np.diff(q, axis=0), axis=1).sum()
    rng = np.random.default_rng(seed)
    bow = rng.choice([-1, 1]) * rng.uniform(0.10, 0.22) * L
    cq = q + nn * (np.sin(np.pi * u) * bow + np.sin(np.pi * u * 2) * bow * 0.25)[:, None]
    w = max(0.45, 0.07 * sc) * np.sin(np.pi * np.clip(u * 0.85 + 0.12, 0, 1)) ** 0.8
    cv_.path(_sk.path_poly(_tpoly(cq, w)), _col(tone), depth=False)

def _hair4(self, cv_, E, P2, DP, sc, hw, hair_tone, hl_side, hd0, detail):
    """v4 头发：每条链 → _lock4 细丝发束；飞发 → _fly4。"""
    sd = self.seed * 1000
    def add(ch, w0, tones, dbias=0.0, wscale=None, every=1, key=0, **kw):
        q = P2(ch.P); dd = DP(ch.P).mean(1)
        for k in range(0, ch.C, every):
            ws = wscale[k] if wscale is not None else 1
            E.append((dd[k] + dbias, (lambda q=q[k], ws=ws, tn=tones[k], k=k: _lock4(cv_, q, w0 * ws * sc, tn, sc, sd + key * 100 + k,
                                                                                     hl_side=hl_side, **kw)), hd0 - dd[k] - dbias))
    pc = self.ponytail.C
    add(self.ponytail, 2.1 * hw, [hair_tone * (1.0 + 0.25 * (k % 3 == 1)) for k in range(pc)], 0.0, self.pt_w, key=1, splay=0.9)
    # 乱发长绺：v4 只留一半、变细（细碎而不是粗绺）
    add(self.locks, 1.25 * hw, [hair_tone * (1.0 + 0.2 * (k % 3 == 0)) for k in range(self.locks.C)], 0.0, self.lock_w, every=2, key=2, splay=1.5,
        base=False)
    nb = self.bangs.C
    for k in range(nb):
        r = self.bang_rows[k]; q = P2(self.bangs.P[k]); dd = DP(self.bangs.P[k]).mean()
        eye = r['kind'] == 'eye'
        E.append((dd + 0.9, (lambda q=q, k=k, eye=eye: _lock4(cv_, q, 1.45 * hw * self.bang_w[k] * sc, hair_tone * (0.9 if eye else 1.0), sc,
                                                                 sd + 300 + k, hl_side=hl_side, base=not eye, splay=0.7,
                                                                 nmax=(4 if eye else 14), sheen=(0.4 if eye else 1.0))), hd0 - dd - 0.9))
    add(self.sidelocks, 2.0 * hw, [hair_tone * 1.05] * self.sidelocks.C, 0.35, self.side_w, key=4, splay=1.2)
    if detail > 0.5:                                      # 飞发：更少（≈每 6 根取 1）、更细、带弧度
        q = P2(self.fly.P); dd = DP(self.fly.P).mean(1)
        for k in range(1, self.fly.C, 6):
            E.append((dd[k] + 0.3, (lambda q=q[k], k=k: _fly4(cv_, q, sc, hair_tone * 1.5, sd + 500 + k)), hd0 - dd[k] - 0.3))



def _sw_draw2(self, fr, x, y, scale, flip=None, rim_color=(0.80, 0.86, 1.0), rim_dir=(-0.75, -0.65), rim=1.0, lift=1.0,
              alpha=1.0, heat=0.0, shine=None, blade_glow=1.0, ink=None, return_masks=False, sword_visible=True,
              detail=1.0, glint=0.0):
    if self.sk is None: raise RuntimeError('先调用 pose()')
    S = self.sk
    if flip is not None: self.flip = flip
    fs = -1. if self.flip else 1.
    th = (VIEWS.get(self.view, self.view) if isinstance(self.view, str) else self.view) * D2R
    ct, st = math.cos(th), math.sin(th)
    sc = scale / 100.0
    allp = [S[k] for k in ('Hc', 'tip', 'pommel', 'ltoe', 'rtoe', 'lheel', 'rheel', 'lfist', 'rfist', 'tie', 'Pp')]
    allp = np.vstack([np.array(allp)] + [g.P.reshape(-1, 3) for g in
                      (self.ponytail, self.locks, self.skirt, self.rib, self.band, self.fly, self.bangs)
                      + ((self.sidelocks,) if hasattr(self, 'sidelocks') else ())])
    X = allp[:, 0] * ct + allp[:, 2] * st
    U = x + fs * X * sc; V = y - allp[:, 1] * sc
    mg = scale * 0.08 + 10
    x0 = int(max(0, math.floor(U.min() - mg))); x1 = int(min(fr.shape[1], math.ceil(U.max() + mg)))
    y0 = int(max(0, math.floor(V.min() - mg))); y1 = int(min(fr.shape[0], math.ceil(V.max() + mg)))
    info = dict(bbox=(x0, y0, x1, y1))
    def P2(Pw):
        Pw = np.asarray(Pw, float)
        Xs = Pw[..., 0] * ct + Pw[..., 2] * st
        return np.stack([x + fs * Xs * sc - x0, y - Pw[..., 1] * sc - y0], -1)
    def DP(Pw):
        Pw = np.asarray(Pw, float); return Pw[..., 0] * st - Pw[..., 2] * ct
    def scr(Pw):
        q = P2(Pw); return (float(q[0] + x0), float(q[1] + y0))
    info['tip'] = scr(S['tip']); info['guard'] = scr(S['guard']); info['hand'] = scr(S['rfist'])
    info['head'] = scr(S['Hc']); info['pommel'] = scr(S['pommel'])
    if x1 - x0 < 4 or y1 - y0 < 4:
        return fr, info
    cv_ = _Canvas(y1 - y0, x1 - x0)
    sk_ = _sk
    rd = np.array(rim_dir, float); rd /= max(np.linalg.norm(rd), 1e-6)
    L3 = np.array([fs * rd[0] * ct, -rd[1], fs * rd[0] * st]) * 0.8 - np.array([st, 0, -ct]) * 0.6
    L3 /= np.linalg.norm(L3)
    vdir = np.array([st, 0, -ct])
    cen = DP(S['Pp'])
    E = []
    def far(d): return 0.66 if d < cen - 1.5 else 1.0
    V4 = getattr(self, 'v4', False) and HAIR_V4
    COAT, PANT, BOOT, LEATH, SKIN = 74, 52, 88, 104, ((SKIN4 if V4 else 188) if HAIR_V3 else 168)    # v3 肤色更苍白（设定图）
    Rc, Cw, Rp, Pp = S['Rc'], S['Cw'], S['Rp'], S['Pp']
    lod = sc > 3.0
    # ---------------------------------------------------------------- 腿：裤（可变半径）+ 长靴 + 绑腿
    for s in 'lr':
        hip, kn, an = S[s + 'hip'], S[s + 'knee'], S[s + 'ank']
        d = DP(kn); f = far(d)
        Pw = np.array([hip, hip + (kn - hip) * 0.38, kn, kn + (an - kn) * 0.3, an])
        q = P2(Pw); ft = P2(np.array([an, S[s + 'toe'], S[s + 'heel'], S[s + 'ball']]))
        def legfn(q=q, ft=ft, f=f):
            cv_.path(sk_.path_limb(q, np.array([5.1, 5.35, 3.85, 4.05, 2.75]) * sc)[0], _col(PANT * f))
            bt0 = q[2] + (q[4] - q[2]) * 0.42
            bq = np.array([bt0, q[3] + (q[4] - q[3]) * 0.55, q[4]])
            cv_.path(sk_.path_limb(bq, np.array([3.75, 3.2, 2.95]) * sc, k=3)[0], _col(BOOT * f))
            a, toe, heel, ball = ft
            sole = np.array([a + (heel - a) * 0.25 + (a - ball) * 0.15, heel, heel + (ball - heel) * 0.5 + (heel - a) * 0.08, ball,
                             toe, toe + (ball - toe) * 0.3 + (a - ball) * 0.25, a + (toe - a) * 0.45 + (a - heel) * 0.15])
            cv_.poly(sole, _col(BOOT * f))
            if lod:
                cv_.paint_in(sk_.path_poly([heel, ball, toe], closed=False, smooth=True), (20,), 0.9, stroke=0.7 * sc)   # 鞋底
                sv = bq[2] - bq[0]; nn = np.array([-sv[1], sv[0]]) / (np.hypot(*sv) + 1e-6)
                cv_.paint_in(sk_.path_poly([bq[0] - nn * 3.9 * sc, bq[0] + nn * 3.9 * sc], closed=False), (BOOT * 1.6 * f,), 0.9,
                             stroke=0.9 * sc)                                                                      # 靴口翻边
                for k_, uu in enumerate((0.25, 0.5, 0.75)):                                                        # 绑带
                    c0 = bq[0] + sv * uu
                    cv_.paint_in(sk_.path_poly([c0 - nn * 3.6 * sc - sv * 0.05, c0 + nn * 3.6 * sc + sv * 0.06], closed=False),
                                 (BOOT * 0.5 * f,), 0.8, stroke=0.35 * sc)
                kv = q[2] - q[0]; kn_ = np.array([-kv[1], kv[0]]) / (np.hypot(*kv) + 1e-6)
                cv_.paint_in(sk_.path_poly([q[1] + kn_ * 1.5 * sc, q[2] - kn_ * 1.0 * sc + kv * 0.05], closed=False, smooth=True),
                             (PANT * 0.45 * f,), 0.6, blur=0.6 * sc, stroke=0.7 * sc)                               # 裤褶
        E.append((d, legfn))
    # ---------------------------------------------------------------- 躯干 loft（真实腰线）
    RINGS = ((-1.0, 8.9, 5.9, 0.0), (5.0, 9.1, 5.9, 0.2), (11.5, 10.3, 6.3, 0.6), (17.5, 11.3, 6.0, 0.4), (21.2, 11.6, 4.9, -0.2),
             (24.3, 5.6, 3.9, 0.1))
    ang = np.linspace(0, 2 * math.pi, 14, endpoint=False)
    rings = [np.stack([np.sin(ang) * rx, np.full_like(ang, yy), np.cos(ang) * rz + zc], 1) @ Rc.T + Cw for yy, rx, rz, zc in RINGS]
    hipr = np.stack([np.sin(ang) * 9.8, np.full_like(ang, 2.5), np.cos(ang) * 6.8], 1) @ Rp.T + Pp
    rings = [hipr] + rings
    rq = [P2(r) for r in rings]
    loft = [cv2.convexHull(np.vstack([a, b]).astype(np.float32)).reshape(-1, 2) for a, b in zip(rq[:-1], rq[1:])]
    dt_ = DP(Cw)
    front_vis = DP(Cw + Rc @ [0, 15, 6]) > DP(Cw + Rc @ [0, 15, -6])
    colA = P2(np.array([Cw + Rc @ p for p in ([-3.0, 25.0, 1.6], [-1.6, 20.5, 5.4], [1.6, 13.5, 6.4], [5.6, 6.0, 5.8], [7.6, 2.0, 5.0])]))
    colB = P2(np.array([Cw + Rc @ p for p in ([3.0, 25.0, 1.6], [1.8, 20.0, 5.5], [-0.4, 15.5, 6.3])]))
    vneck = P2(np.array([Cw + Rc @ p for p in ([-3.0, 25.0, 1.6], [3.0, 25.0, 1.6], [0.4, 15.0, 6.4])]))
    folds = [P2(np.array([Cw + Rc @ p for p in pts])) for pts in
             (([4.0, 3.5, 5.6], [6.5, 11, 5.6], [8.5, 17, 4.8]), ([-5.5, 4.0, 5.4], [-7.6, 10, 5.4], [-9.5, 16, 4.0]),
              ([1.0, 4.0, 6.0], [3.0, 9.0, 6.2]))]
    backf = [P2(np.array([Cw + Rc @ p for p in pts])) for pts in
             (([0, 22.5, -4.6], [0, 9, -5.6], [0, 1, -5.2]), ([-3, 20, -5.6], [-8.5, 13, -5.3]), ([3, 20, -5.6], [8.5, 13, -5.3]))]
    def torsofn():
        cv_.polys(loft, _col(COAT), smooth=False)
        if not lod: return
        if front_vis:
            cv_.paint_in(sk_.path_poly(vneck), ((62, 150) if V4 else (148,)), 1.0)               # 中衣领（v4：暗红内领，设定图）
            for qq in (colA, colB):                                                                # 交领宽边
                cv_.paint_in(sk_.path_poly(qq, closed=False, smooth=True), (COAT * 1.45,), 1.0, stroke=1.25 * sc)
                cv_.paint_in(sk_.path_poly(qq, closed=False, smooth=True), (COAT * 0.45,), 0.8, stroke=0.25 * sc)
            for qq in folds:
                cv_.paint_in(sk_.path_poly(qq, closed=False, smooth=True), (COAT * 0.42,), 0.55, blur=0.7 * sc, stroke=0.9 * sc)
        else:
            for k_, qq in enumerate(backf):
                cv_.paint_in(sk_.path_poly(qq, closed=False, smooth=True), (COAT * (0.45 if k_ == 0 else 0.55),), 0.6,
                             blur=0.6 * sc, stroke=(0.5 if k_ == 0 else 0.9) * sc)
    E.append((dt_ - 0.8, torsofn))
    # ---------------------------------------------------------------- 腰封（宽皮 + 缠绳 + 金扣）
    angb = np.linspace(0, 2 * math.pi, 28, endpoint=False)
    bring = np.array([np.stack([np.sin(angb) * (9.9 + 0.3 * (yy > 5)), np.full_like(angb, yy), np.cos(angb) * 6.9 + 0.3], 1) @ Rp.T + Pp
                      for yy in (3.0, 6.9, 10.8)])
    bq3 = P2(bring.reshape(-1, 3)).reshape(3, -1, 2); bdp = DP(bring)
    bhull = cv2.convexHull(bq3[[0, 2]].reshape(-1, 2).astype(np.float32)).reshape(-1, 2)
    vis = bdp[0] > DP(Pp) - 0.5
    buck = Pp + Rp @ [1.2, 6.9, 7.35]
    bk_vis = (Rp @ [0.15, 0, 1.0]) @ vdir > 0.1
    def beltfn():
        cv_.poly(bhull, _col(LEATH))
        if not lod: return
        for r in (0, 2):
            idx = np.nonzero(vis & np.roll(vis, -1))[0]
            for k in idx:
                cv_.paint_in(sk_.path_poly([bq3[r, k], bq3[r, (k + 1) % len(angb)]], closed=False), (LEATH * 1.7,), 0.9, stroke=0.4 * sc)
        idx = np.nonzero(vis)[0]
        if len(idx) > 2:                                                                            # 中缠暗红绳
            seq = bq3[1, idx]
            cv_.paint_in(sk_.path_poly(seq, closed=False), (90, 170), 1.0, stroke=1.3 * sc)
            cv_.paint_in(sk_.path_poly(seq - [0, 0.35 * sc], closed=False), (170, 150), 0.6, stroke=0.3 * sc)
    E.append((DP(Pp) + 0.2, beltfn))
    if bk_vis and lod:
        bc = P2(buck); bdir = P2(Pp + Rp @ [3.2, 6.9, 7.0]) - bc; bl_ = np.hypot(*bdir) + 1e-6
        def buckfn(bc=bc):
            cv_.ell(bc, (1.5 * sc, 2.0 * sc), 0, _col(165), gold=235)
            cv_.paint_in(sk_.path_ellipse(bc, (0.8 * sc, 1.2 * sc), 0), (60,), 0.9)
        E.append((DP(buck) + 0.3, buckfn))
    # ---------------------------------------------------------------- 衣摆：外袍（前开衩、褶皱网格渐变、里衬）+ 内摆
    P = self.skirt.P; nS, Ls = P.shape[:2]
    Pn = np.roll(P, -1, 0)
    t1 = Pn[:, :-1] - P[:, :-1]; t2 = P[:, 1:] - P[:, :-1]
    nrm = _nrm(np.cross(t2, t1))
    cenq = (P[:, :-1] + Pn[:, 1:]) / 2
    radial = cenq - Pp[None, None]; radial[..., 1] = 0
    sgn = np.sign((nrm * radial).sum(-1, keepdims=True)); nrm = nrm * np.where(sgn == 0, 1, sgn)
    # 顶点法线（相邻面平均）
    vn = np.zeros((nS, Ls, 3)); vn[:, :-1] += nrm; vn[:, 1:] += nrm; vn += np.roll(vn, 1, 0) * 0.0
    vn = _nrm(vn + np.roll(vn, 1, 0))
    lamv = np.clip(vn @ L3, -1, 1); facev = vn @ vdir
    fold = 1.0 + 0.32 * np.cos(np.arange(nS) * math.pi)[:, None] * self.pleat[:, None]
    q2 = P2(P)
    angs = np.linspace(0, 360, nS, endpoint=False)
    def col_tones(i):
        tA = COAT * fold[i] * (0.62 + 0.55 * np.clip(lamv[i], 0, 1))
        tB = COAT * fold[(i + 1) % nS] * (0.62 + 0.55 * np.clip(lamv[(i + 1) % nS], 0, 1))
        bf = (facev[i] + facev[(i + 1) % nS]) * 0.5
        lin = np.where(bf < -0.05, 0.62, 1.0)                                     # 背面=里衬更暗
        return tA * lin, tB * lin
    inner_sc = 0.82
    for i in range(nS):
        i2 = (i + 1) % nS
        a_mid = (angs[i] + 10) % 360
        is_slit = (a_mid < 22 or a_mid > 338)                                        # 前开衩
        dcol = DP(cenq[i]).mean()
        Pi = np.stack([P[i], P[i2]], 1).reshape(-1, 2) if False else None
        quads = np.concatenate([q2[i], q2[i2]], 0)                                   # 2*Ls 个顶点
        idx = []
        for j in range(Ls - 1):
            a_, b_, c_, d_ = j, Ls + j, Ls + j + 1, j + 1
            idx += [a_, b_, c_, a_, c_, d_]
        tA, tB = col_tones(i)
        tones = np.concatenate([tA, tB])
        outline = np.vstack([q2[i], q2[i2][::-1]])
        if is_slit:
            # 内摆（短、收窄）：开衩处露出的暗色里层
            cin = Pp + (P[[i, i2]][:, :int(Ls * 0.7)] - Pp) * [inner_sc, 1, inner_sc]
            qi = P2(cin); Li = qi.shape[1]
            qq = np.concatenate([qi[0], qi[1]], 0)
            idx2 = []
            for j in range(Li - 1):
                idx2 += [j, Li + j, Li + j + 1, j, Li + j + 1, j + 1]
            tin = np.full(2 * Li, PANT * 0.9)
            E.append((dcol - 1.2, (lambda qq=qq, idx2=idx2, tin=tin, ol=np.vstack([qi[0], qi[1][::-1]]):
                                   cv_.mesh_tone(qq, tin, idx2, outline=ol)), cen - dcol + 1.2))
            continue
        E.append((dcol, (lambda qq=quads, tn=tones, idx=idx, ol=outline: cv_.mesh_tone(qq, tn, idx, outline=ol)), cen - dcol))
    # 底边滚边
    hem = q2[:, -1]; hd = DP(P[:, -1])
    for i in range(nS):
        i2 = (i + 1) % nS
        a_mid = (angs[i] + 10) % 360
        if a_mid < 22 or a_mid > 338: continue
        dd_ = max(hd[i], hd[i2]) + 0.02
        E.append((dd_, (lambda a=hem[i], b=hem[i2]: cv_.line(a, b, 0.6 * sc, _col(COAT * 1.65))), cen - dd_))
    # 开衩边（门襟滚边，竖线）
    for i in (17, 1):
        if i >= nS: continue
        dd_ = DP(P[i]).mean() + 0.03
        E.append((dd_, (lambda q=q2[i]: cv_.stroke('C', q, _col(COAT * 1.65), 0.6 * sc)), cen - dd_))
    # ---------------------------------------------------------------- 手臂 + 宽袖 + 护腕 + 拳
    for s in 'lr':
        sh, el, wr, fist = S[s + 'sh'], S[s + 'el'], S[s + 'wr'], S[s + 'fist']
        d = DP((sh + el) / 2); f = far(d)
        q = P2(np.array([sh, sh + (el - sh) * 0.3, el, el + (wr - el) * 0.3, wr, fist]))
        SL = self.sleeve[s].P
        sq = P2(SL)
        n1 = SL[1:, 0] - SL[:-1, 0]
        sl_t = []
        for k in range(4):
            v1 = SL[min(k + 1, 3), 0] - SL[max(k - 1, 0), 0]; v2 = SL[k, -1] - SL[k, 0]
            n_ = _nrm(np.cross(v1, v2)); sl_t.append(0.6 + 0.6 * abs(n_ @ L3))
        sidx = []
        for k in range(3):
            for j in range(3):
                a_, b_, c_, d_ = k * 4 + j, (k + 1) * 4 + j, (k + 1) * 4 + j + 1, k * 4 + j + 1
                sidx += [a_, b_, c_, a_, c_, d_]
        stone = np.array([[COAT * f * sl_t[k] * (1.05 if j == 3 else 1.0 - 0.08 * (j == 1)) for j in range(4)] for k in range(4)]).reshape(-1)
        soutline = np.vstack([sq[0, :], sq[:, -1], sq[3, ::-1], sq[::-1, 0]])
        def armfn(q=q, sq=sq, f=f, stone=stone, soutline=soutline, sidx=sidx):
            cv_.path(sk_.path_limb(q[:3], np.array([4.4, 4.1, 3.4]) * sc, k=3)[0], _col(COAT * f))
            cv_.mesh_tone(sq.reshape(-1, 2), stone, sidx, outline=soutline)
            if lod:
                cv_.paint_in(sk_.path_poly(sq[:, -1], closed=False, smooth=True), (COAT * 1.6 * f,), 0.9, stroke=0.5 * sc)   # 袖口滚边
            cv_.path(sk_.path_limb(q[2:5], np.array([3.5, 3.45, 2.5]) * sc, k=3)[0], _col(COAT * 0.9 * f))
            # 护腕（皮，三道绑带 + 金边）
            fa = q[2] + (q[4] - q[2]) * 0.3
            bp_ = np.array([fa, fa + (q[4] - fa) * 0.5, q[4]])
            cv_.path(sk_.path_limb(bp_, np.array([3.15, 2.85, 2.55]) * sc, k=3)[0], _col(LEATH * 1.05 * f))
            if lod:
                dd = q[4] - fa; nn = np.array([-dd[1], dd[0]]) / (np.hypot(*dd) + 1e-6)
                for u in (0.22, 0.52, 0.82):
                    c0 = fa + dd * u
                    cv_.paint_in(sk_.path_poly([c0 - nn * 3.2 * sc, c0 + nn * 3.2 * sc + dd * 0.05], closed=False), (LEATH * 1.75 * f,),
                                 0.9, stroke=0.42 * sc)
                cv_.paint_in(sk_.path_poly([fa - nn * 3.2 * sc, fa + nn * 3.2 * sc], closed=False), (200,), 0.8, stroke=0.3 * sc)
            # 拳（缠布）
            fd = q[5] - q[4]; fl = np.hypot(*fd) + 1e-6; fu = fd / fl; fn_ = np.array([-fu[1], fu[0]])
            hq = np.array([q[4] - fu * 0.4 * sc, q[4] + fu * 1.3 * sc, q[5] + fu * 0.9 * sc])
            cv_.path(sk_.path_limb(hq, np.array([1.95, 2.35, 2.2]) * sc, k=3)[0], _col(SKIN * 0.82 * f))
            if lod:
                for u in (0.15, 0.55):
                    c0 = hq[0] + (hq[2] - hq[0]) * u
                    cv_.paint_in(sk_.path_poly([c0 - fn_ * 2.4 * sc, c0 + fn_ * 2.4 * sc + fu * 0.6 * sc], closed=False), (190 * f,), 0.85,
                                 stroke=0.55 * sc)
                kn = hq[2] - fu * 0.2 * sc
                cv_.paint_in(sk_.path_poly([kn - fn_ * 1.8 * sc, kn + fn_ * 1.8 * sc], closed=False), (SKIN * 0.5 * f,), 0.6, stroke=0.3 * sc)
        E.append((d + (0.5 if s == 'r' else 0), armfn))
    # ---------------------------------------------------------------- 刀鞘（黑漆 + 金具 + 下緒红绳）
    M, sdv = S['sc_m'], S['sc_d']
    scq = P2(np.array([M, M + sdv * 9, M + sdv * 46, M + sdv * 47.6]))
    def scabfn():
        cv_.path(sk_.path_limb(scq[[0, 2]], np.array([1.85, 1.5]) * sc, k=2)[0], _col(42))
        cv_.cap(scq[2], scq[3], 1.55 * sc, 1.15 * sc, _col(160), gold=210)                              # 鐺（金）
        cv_.cap(scq[0], scq[0] + (scq[2] - scq[0]) * 0.035, 2.05 * sc, 2.05 * sc, _col(165), gold=220)  # 鯉口
        if lod:
            dv = scq[2] - scq[0]; nv = np.array([-dv[1], dv[0]]) / (np.hypot(*dv) + 1e-6)
            sgn_ = 1 if nv @ rd[:2] > 0 else -1
            cv_.paint_in(sk_.path_poly([scq[0] + nv * sgn_ * 0.9 * sc + dv * 0.05, scq[2] + nv * sgn_ * 0.7 * sc], closed=False),
                         (150,), 0.85, stroke=0.35 * sc)                                                 # 漆面高光
            for u in (0.12, 0.17):
                c0 = scq[0] + dv * u
                cv_.cap(c0 - nv * 1.9 * sc, c0 + nv * 1.9 * sc, 0.3 * sc, 0.3 * sc, _col(160), gold=200)
            c1 = scq[0] + dv * 0.145                                                                     # 下緒（暗红绳）
            cord = np.array([c1, c1 + nv * 2.5 * sc + dv * 0.04, c1 + nv * 1.0 * sc + dv * 0.12, c1 + nv * 3.4 * sc + dv * 0.2])
            cv_.stroke('C', cord, _col(110, 190), 0.55 * sc)
    E.append((DP(M + sdv * 20), scabfn))
    # ---------------------------------------------------------------- 刀（同 v1 + 出刀拖影 smear）
    if sword_visible:
        g2 = P2(S['guard']); t2 = P2(S['tip']); pm = P2(S['pommel'])
        dv = t2 - g2; l2 = np.hypot(*dv)
        dirv = dv / (l2 + 1e-6); n2 = np.array([-dirv[1], dirv[0]])
        ev = getattr(self, 'edge_vel', None)
        want = 1.0 if n2[1] > 0 else -1.0
        if ev is not None and not S['sheathed']:
            evs = P2(S['tip'] + ev) - t2
            if np.hypot(*evs) > 1: want = 1.0 if (evs @ n2) > 0 else -1.0
        self.edge_sign = want
        n2 = n2 * want
        wd = 2.4 * sc
        def bl(s, v):
            curv = -0.045 * l2 * s * s
            w = wd * (1 - 0.18 * s)
            return g2 + dirv * l2 * s + n2 * (curv + v * w * 0.5)
        ss = np.linspace(0, 1, 26)
        spine = [bl(s, -1) for s in ss[:-1]]; edge = [bl(s, 1) for s in ss[:-1]]
        kk = np.linspace(0, 1, 6)
        kis = [bl(0.93 + 0.07 * k, 1 - 2 * k ** 1.6) for k in kk]
        outline = np.array(spine[:24] + [bl(1.0, -1.0)] + list(reversed(kis[1:])) + edge[:24][::-1])
        shin = np.array([bl(s, -0.2) for s in ss[:24]] + [bl(s, -1) for s in ss[:24][::-1]])
        ha = np.array([bl(s, 0.35 + 0.12 * math.sin(s * 38)) for s in ss[:24]] + [bl(s, 1) for s in ss[:24][::-1]])
        edge_line = np.array([bl(s, 0.95) for s in ss[:24]] + kis[1:])
        info['blade_poly'] = outline + [x0, y0]
        # 拖影：上一帧刀身 → 本帧刀身之间的扫掠面（金属通道，半透明），表现挥刀形变
        prev = getattr(self, 'sk_prev', None)
        smear = None
        if prev is not None and not S['sheathed'] and not prev.get('sheathed', True):
            pg, pt = P2(prev['guard']), P2(prev['tip'])
            mv = np.hypot(*(pt - t2))
            if mv > 0.10 * l2:
                smear = np.array([g2 + dirv * l2 * 0.3, t2, pt, pg + (pt - pg) * 0.3])
        if S['sheathed']:
            bdep = DP(S['guard'])
            def swfn():
                cv_.cap(g2, pm, 1.3 * sc, 1.25 * sc, _col(48))
                cv_.cap(pm, pm + (pm - g2) * 0.04, 1.4 * sc, 1.4 * sc, _col(170), gold=230)
                for u in np.linspace(0.1, 0.9, 6):
                    c0 = g2 + (pm - g2) * u; cv_.line(c0 - n2 * 1.2 * sc + (pm - g2) * 0.04, c0 + n2 * 1.2 * sc, .35 * sc, _col(125))
                cv_.ell(g2, (0.55 * sc, 2.7 * sc), math.degrees(math.atan2(dirv[1], dirv[0])), _col(170), gold=200)
            E.append((bdep + 0.3, swfn))
        else:
            bdep = DP(S['guard'] + S['bd'] * 12)
            def swfn():
                if smear is not None:
                    cv_.fill('C', smear, (110, 0, 0, 255), depth=False)
                    cv_.fill('M', smear, (70, 0, 40))
                cv_.fill('C', outline, (255, 0, 0, 255), depth=True)
                cv_.fill('G', outline, 0)
                cv_.fill('M', outline, (120, 0, 90))
                cv_.fill('M', shin, (62, 0, 40))
                cv_.fill('M', ha, (190, 0, 255))
                cv_.stroke('M', edge_line, (255, 255, 255), max(0.6, 0.35 * sc))
                cv_.cap(g2, pm, 1.3 * sc, 1.2 * sc, _col(48))
                for u in np.linspace(0.08, 0.92, 7):
                    c0 = g2 + (pm - g2) * u; cv_.line(c0 - n2 * 1.15 * sc, c0 + n2 * 1.15 * sc + (pm - g2) * 0.05, .35 * sc, _col(125))
                cv_.cap(pm, pm + (pm - g2) * 0.05, 1.4 * sc, 1.4 * sc, _col(170), gold=230)
                cv_.ell(g2, (0.55 * sc, 2.7 * sc), math.degrees(math.atan2(dirv[1], dirv[0])), _col(170))
                cv_.fill_ell('G', g2, (0.55 * sc + 0.12, 2.7 * sc), math.degrees(math.atan2(dirv[1], dirv[0])), 200)
            E.append((bdep, swfn))
    # ---------------------------------------------------------------- 头 + 头发
    Rh, Hc = S['Rh'], S['Hc']
    hair_tone = 34
    hd0 = DP(Hc) + 4.0
    hfns, eyes, facing = _draw_head2(cv_, P2, DP, S, sc, vdir, L3, skin=SKIN, hair_tone=hair_tone, detail=detail)
    for dd_, fn, b in hfns: E.append((dd_, fn, b))
    tie2 = P2(S['tie'])
    hw = 1 / math.sqrt(self.hair)
    hl_side = 1 if fs * rd[0] < 0 else -1
    # 马尾：发团主体（体积）+ 发束
    ctr = self.ponytail.P.mean(0); cq_ = P2(ctr)
    spread = np.linalg.norm(self.ponytail.P - ctr[None], axis=-1).mean(0)
    E.append((DP(ctr).mean() - 0.05, (lambda cq_=cq_: _clump(cv_, cq_, ((2.6 if getattr(self, 'v4', False) else 1.7) if hasattr(self, 'sidelocks') else 4.6) * sc,
                                                             0.4 * sc, hair_tone * (0.6 if getattr(self, 'v4', False) else 1), sc,
                                                             hl=(0 if getattr(self, 'v4', False) else 55), hl_side=hl_side, prof='spindle')),
              hd0 - DP(ctr).mean() + 0.05))
    def add_clumps(ch, w0, tones, dbias=0.0, wscale=None, prof='taper', every=1):
        q = P2(ch.P); dd = DP(ch.P).mean(1)
        for k in range(0, ch.C, every):
            ws = wscale[k] if wscale is not None else 1
            E.append((dd[k] + dbias, (lambda q=q[k], ws=ws, tn=tones[k]: _clump(cv_, q, w0 * ws * sc, 0.0, tn, sc, hl=48, hl_side=hl_side, prof=prof)),
                      hd0 - dd[k] - dbias))
    v3h = hasattr(self, 'sidelocks')
    if getattr(self, 'v4', False):
        _hair4(self, cv_, E, P2, DP, sc, hw, hair_tone, hl_side, hd0, detail)
    else:
      add_clumps(self.ponytail, (1.75 if v3h else 2.9) * hw, [hair_tone + (14 if k % 3 == 1 else 0) for k in range(self.ponytail.C)], 0.0, self.pt_w)
      add_clumps(self.locks, (1.8 if v3h else 2.4) * hw, [hair_tone + (10 if k % 3 == 0 else 0) for k in range(self.locks.C)], 0.0, self.lock_w)
    if getattr(self, 'v4', False): pass
    elif hasattr(self, 'sidelocks'):
        # v3：刘海发帘/过眼发缕逐缕定宽；鬓发成束垂到胸前（在脸前一层，但宽度受控，不压成黑块）
        add_clumps(self.bangs, 1.45 * hw, [hair_tone + (8 if k % 2 else 0) for k in range(self.bangs.C)], 0.9, self.bang_w)
        add_clumps(self.sidelocks, 2.2 * hw, [hair_tone + (10 if k % 2 else 2) for k in range(self.sidelocks.C)], 0.35, self.side_w)
    else:
        add_clumps(self.bangs, 1.35 * hw, [hair_tone + 6] * self.bangs.C, 0.6)
    if detail > 0.5 and not getattr(self, 'v4', False):  # 飞丝：少量、渐细、按尺度变宽（不再是 1px 乱线）
        q = P2(self.fly.P); dd = DP(self.fly.P).mean(1)
        for k in range(0, self.fly.C, 4):
            E.append((dd[k] + 0.3, (lambda q=q[k]: _clump(cv_, q, max(0.7, 0.42 * sc), 0.0, hair_tone + 20, sc, hl=0)), hd0 - dd[k] - 0.3))
    # 发绳（朱红缠绕）
    E.append((DP(S['tie']) + 0.2, (lambda: (cv_.circ(tie2, 1.45 * sc, _col(160, 255)),
                                            cv_.paint_in(sk_.path_circle(tie2 + np.array([-0.35, -0.35]) * sc, 0.6 * sc), (230, 255), 0.7)) if True else None),
              hd0 - DP(S['tie']) - 0.2))
    # ---------------------------------------------------------------- 飘带（朱红，扭转渐变）+ 腰前暗红长带
    def add_ribbon(ch, idx, wbase, redv, tone0, twist_rate, tassel=False):
        Pr = ch.P[idx]; q = P2(Pr)
        d = np.gradient(q, axis=0); nn = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
        tw = np.arange(len(q)) * twist_rate + idx * 1.3 + Pr[:, 1] * 0.05 + (self.t_last or 0) * 2.0
        cw = np.cos(tw)
        wid = wbase * sc * (0.32 + 0.68 * np.abs(cw)) * np.linspace(1, 0.8, len(q))
        shade_ = 0.5 + 0.5 * np.clip(cw * 0.8 + 0.2, -1, 1)
        cols = [_col(tone0 * (0.42 + 0.75 * shade_[k]), redv) for k in range(len(q))]
        dd = DP(Pr)
        for k in range(0, len(q) - 1, 3):
            kk_ = slice(k, min(k + 4, len(q)))
            E.append((dd[kk_].mean(), (lambda qq=q[kk_], ww=wid[kk_], nn_=nn[kk_], cc=cols[kk_]: cv_.ribbon(qq, ww, nn_, cc))))
        if tassel:
            end = q[-1]; dv_ = q[-1] - q[-2]; dv_ = dv_ / (np.hypot(*dv_) + 1e-6)
            nv = np.array([-dv_[1], dv_[0]])
            def tas(end=end, dv_=dv_, nv=nv):
                cv_.circ(end, 1.0 * sc, _col(150, 0), gold=220)
                for m in range(7):
                    a = end + nv * (m - 3) * 0.35 * sc
                    cv_.line(a, a + (dv_ * 5.5 + nv * (m - 3) * 0.4) * sc, max(0.6, 0.3 * sc), _col(110, redv))
            E.append((dd[-1] + 0.01, tas))
    if self.ribbons:
        add_ribbon(self.rib, 0, 1.75, 255, 235, 0.5)
        add_ribbon(self.rib, 1, 1.45, 255, 205, 0.58)
        kq = P2(self.rib.P[0, 0])
        E.append((DP(self.rib.P[0, 0]) + 0.05, lambda kq=kq: (cv_.circ(kq, 1.7 * sc, _col(200, 255)),
                                                            cv_.paint_in(sk_.path_circle(kq, 0.8 * sc), (110, 255), 0.8))))
    add_ribbon(self.band, 0, 1.8, 150, 120, 0.18, tassel=True)
    # ---------------------------------------------------------------- 绘制（画家算法）
    E.sort(key=lambda e: e[0])
    for e in E:
        cv_.dcur = e[0] + (e[2] if len(e) > 2 else 0.0); e[1]()
    # ---------------------------------------------------------------- 合成
    rc = np.asarray(rim_color, np.float32)
    def met_cb(col, A, inv, met):
        Mm = cv_.M.astype(np.float32) / 255. * inv[..., None]
        steel = Mm[..., 0:1] * np.array([0.50, 0.52, 0.56], np.float32) + Mm[..., 0:1] ** 2 * rc * 0.35
        steel = steel + Mm[..., 1:2] * 0.85
        if shine is not None and 'blade_poly' in info:
            h_, w_ = A.shape
            g2_ = np.array(info['guard']) - [x0, y0]; t2_ = np.array(info['tip']) - [x0, y0]
            dvv = t2_ - g2_; ll = (dvv @ dvv) + 1e-6
            yy, xx = np.mgrid[0:h_, 0:w_]
            sp_ = ((xx - g2_[0]) * dvv[0] + (yy - g2_[1]) * dvv[1]) / ll
            band = np.exp(-((sp_ - shine) / 0.06) ** 2).astype(np.float32)
            steel = steel + band[..., None] * (0.5 + 0.8 * Mm[..., 0:1]) * np.array([1.0, 0.97, 0.92], np.float32)
        if heat > 0:
            hh = Mm[..., 2:3] * heat
            steel = steel * (1 - hh * 0.6) + hh * (RED * 1.2 + GOLD * hh * 0.7)
        return col * (1 - met[..., None]) + steel * met[..., None]
    ground = (P2(S['ltoe'])[1] - 34 * sc, P2(S['ltoe'])[1] - 4 * sc)
    ground = (min(ground[0], P2(S['rtoe'])[1] - 34 * sc), ground[1])
    gy = max(P2(S['ltoe'])[1], P2(S['rtoe'])[1])
    reg_before = fr[y0:y1, x0:x1].copy()
    _V4C['on'] = V4
    try:
        fr, A, col_ = _comp2(fr, cv_, x0, y0, rim_color, rd, rim, float(np.clip(scale * 0.0042, 0.8, 3.2)), lift * 1.05, alpha, ink,
                             R=3.6 * sc, ground=(gy - 40 * sc, gy - 2 * sc), tex_scale=max(1, sc * 0.5), return_A=True, met_cb=met_cb)
    finally:
        _V4C['on'] = False
    out = fr[y0:y1, x0:x1]
    h_, w_ = A.shape
    Ac = cv_.C[..., 0].astype(np.float32) / 255.
    met = np.clip(cv_.C[..., 3].astype(np.float32) / 255. / np.maximum(Ac, 1e-3), 0, 1)
    if V4 and getattr(cv_, 'iris4', None):
        _iris4(out, cv_, alpha)
    # 眼神光：虹膜上的小高光点 + 晕（替代 v1 的横条）
    if glint > 0 and eyes:
        eyes.sort(key=lambda e: -e[0])
        for vis_, e_ in eyes[:2]:
            gx, gy_ = float(e_[0]), float(e_[1])
            if HAIR_V3 and 0 <= gx < w_ and 0 <= gy_ < h_:
                # 遮挡判定：琥珀瞳写了金通道，之后画上的头发/眼睑会把它擦掉 → 只在瞳孔仍可见处点眼神光
                rr_ = max(1, int(0.12 * sc)); Gw = cv_.G[max(0, int(gy_) - rr_):int(gy_) + rr_ + 1, max(0, int(gx) - rr_):int(gx) + rr_ + 1]
                vis_ = vis_ * float(np.clip((Gw.astype(np.float32).mean() / 255.0 - 0.25) / 0.45, 0, 1)) if Gw.size else 0.0
                if vis_ <= 0.02: continue
            if 0 <= gx < w_ and 0 <= gy_ < h_:
                R = int(3 * sc + 8); ya, yb, xa, xb = max(0, int(gy_) - R), min(h_, int(gy_) + R), max(0, int(gx) - R), min(w_, int(gx) + R)
                gl = np.zeros((yb - ya, xb - xa), np.float32)
                if V4:      # v4：眼神光缩小，不压过虹膜；glint>1 时（如 S043 寒光）才加一点外晕
                    cv2.circle(gl, (int((gx - xa) * 8), int((gy_ - ya) * 8)), max(3, int(0.065 * sc * 8)), 1.0, -1, cv2.LINE_AA, 3)
                    g = gl * 0.75 + cv2.GaussianBlur(gl, (0, 0), max(0.5, 0.05 * sc)) * 0.5 + \
                        cv2.GaussianBlur(gl, (0, 0), 0.6 * sc + 1) * 0.35 * max(0.0, glint - 1.2)
                    g = g / max(1.0, glint * 0.6)
                else:
                    cv2.circle(gl, (int((gx - xa) * 8), int((gy_ - ya) * 8)), max(4, int(0.16 * sc * 8)), 1.0, -1, cv2.LINE_AA, 3)
                    g = gl * 1.4 + cv2.GaussianBlur(gl, (0, 0), max(0.6, 0.12 * sc)) * 1.2 + cv2.GaussianBlur(gl, (0, 0), 0.9 * sc + 1) * 0.6
                out[ya:yb, xa:xb] += g[..., None] * rc * glint * alpha * (0.5 + 0.5 * vis_)
    if heat > 0 and blade_glow > 0 and met.max() > 0.01:
        gsm = _blur_ds(met * Ac * heat, max(2, 1.5 * sc))
        out += gsm[..., None] * (RED * 1.2 + GOLD * 0.3) * blade_glow * alpha
    dr = getattr(self, 'drops', None)
    if dr is not None and len(dr):
        q = P2(dr[:, :3]); qv = P2(dr[:, :3] + dr[:, 3:6] * 0.012) - q
        lay = np.zeros(A.shape, np.float32)
        for k in range(len(q)):
            a = q[k]; b = a + qv[k]
            cv2.line(lay, (int(a[0] * 8), int(a[1] * 8)), (int(b[0] * 8), int(b[1] * 8)), float(1 - dr[k, 6] / 0.7),
                     max(1, int(0.35 * sc)), cv2.LINE_AA, 3)
        out += cv2.GaussianBlur(lay, (0, 0), 0.6)[..., None] * (0.35 + 0.5 * rc) * alpha
    fr[y0:y1, x0:x1] = out
    if return_masks:
        bm = np.zeros(fr.shape[:2], np.float32); bm[y0:y1, x0:x1] = met * Ac
        am = np.zeros(fr.shape[:2], np.float32); am[y0:y1, x0:x1] = A * alpha
        info['blade_mask'] = bm; info['alpha'] = am
    info['alpha_local'] = A
    return fr, info


def _sw_draw_dispatch(self, fr, x, y, scale, *a, **kw):
    if QUALITY == 'v2' and BACKEND == 'skia':
        return _sw_draw2(self, fr, x, y, scale, *a, **kw)
    return _sw_draw(self, fr, x, y, scale, *a, **kw)
Swordsman.draw = _sw_draw_dispatch

# 骨架比例微调（v2）：肩更宽、肩线略低 → 倒三角；记录上一帧骨架供拖影
_pose_v1 = Swordsman.pose
def _pose_v2(self, *a, **kw):
    prev, tl = self.sk, self.t_last
    t = a[2] if len(a) > 2 else kw.get('t')
    S = _pose_v1(self, *a, **kw)
    self.sk_prev = prev if (prev is not None and tl is not None and t is not None and 0 < t - tl <= 0.2) else None
    return S
Swordsman.pose = _pose_v2
