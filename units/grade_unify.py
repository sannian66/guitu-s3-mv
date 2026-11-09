"""units/grade_unify.py — 《谁定正邪》全片统一 grade 层（纯后处理，不改分镜/不改内容）。

背景
    五个摄制组各写一套收尾（a_kit/b_kit/c1kit/d_kit/e_kit），颗粒/辉光/暗角/色温/红纯度/黑位
    各是一组不同的数：vig 0.38–0.45（D 还随 paper_mode 掉到 0.15）、grain 0.035–0.040
    （D paper 再放大 1.4×）、bloom 0.25–0.42、黑位抬升 0 / +0.012 / +0.014。
    结果就是用户说的「每一段风格都不太一样」。

做什么 / 不做什么
    只收敛**材质层**：颗粒强度与频率、辉光量、暗角曲线、黑位/白点、中性色温偏移、红色纯度。
    不动构图、不动明暗设计、不动内容调色（冷灰 / 暖金 / 宣纸留白 / 单点光极暗全部保留）。
    因为「统一」是通过「把作者层换成本层」实现的（逆向补偿 + 重做），而不是「把所有段拉平」：
    同样是 0.62 的中灰，每个组算出来的颗粒/暗角/黑位/色偏变成了同一套数。

接口
    apply(fr, t, section_key, cache) -> np.float32 HxWx3
        fr          float32 线性/显示帧（0..1+），即各组 finish() 的返回值（to8() 之前的帧）
        t           全局时间（秒，= 帧号 / 30；prun.py 里所有收尾调用传的都是全局 t）
        section_key 段落键：a_intro_verse1 / b_pre1 / chorus1 / b_verse2 /
                    c_pre2_chorus2 / d_bridge / e_final_outro
        cache       每进程复用的小 dict（掩膜/颗粒场缓存），可为 None
        hint        可选 dict，目前只认 {'pm': paper_mode}（D 组 d_finish 的 paper_mode）
                    —— 不传也能跑（用段落默认值），传了暗角/辉光/色温补偿更准。

    GRADE_UNIFY=0（默认）→ 恒等返回，方便 A/B 对拍；=1 → 生效。

阶段（顺序即物理顺序）
    1 去作者颗粒 → 2 黑位/白点 → 3 辉光换量 → 4 暗角换曲线 → 5 中性色温+红纯度
    → 6 接点局部匹配（±2s 斜坡）→ 7 加统一颗粒 → 8 复位黑边
"""
import os
from functools import lru_cache
import numpy as np
import cv2

W, H, BAR = 1920, 1080, 120
_GC = {}                      # 默认 cache（接线时可以不传）

# ---------------------------------------------------------------- 开关
def enabled():
    return os.environ.get('GRADE_UNIFY', '0').strip().lower() not in ('0', '', 'off', 'false', 'no')

# ---------------------------------------------------------------- 统一目标：全片唯一一套数
TGT = dict(
    grain=0.040,          # 颗粒等效振幅（作者参数空间；c1kit 默认 0.04）
    grain_jitter=0.10,    # 允许按段落 ±10% 微调（见 SEC[*]['gs']）
    vig=0.42,             # c1kit vignette_mask 强度
    vig_beta=0.60,        # 换曲线指数 <1：只收敛一半，保住「单点光极暗」这类设计
    vig_clip=(0.90, 1.10),
    bloom=(0.25, 0.35),   # 辉光量收进这条带（不硬拉成单一值：宣纸留白段保住通透）
    bloom_thr=0.72, bloom_sig=26.0,               # 辉光阈值/半径（半径全片固定 26）
    bloom_clip=0.06,      # 单向补/扣的绝对亮度上限（避免把宣纸留白灌成雾）
    black=0.0100,         # 纯黑输入经收尾后的目标亮度（黑位）
    black_clip=(-0.005, 0.010),
    white=0.848,          # 纯白输入经收尾后的目标亮度（白点/肩，关掉辉光单测）
    cast_rb=-0.030,       # 中性灰 R−B 目标（保留冷灰底，只收敛「各段偏移」）
    cast_strength=0.40,   # 全局色温收敛力度（接点处另行局部对齐）
    red_pur=0.860,        # 暗红纯度目标 (r−max(g,b))/r
    red_strength=0.50,
)

# ---------------------------------------------------------------- 第 9 阶段「胶片 look」：全片唯一一套
# 四样都是对**亮度**做的（S 曲线 / 微对比）或对**高光**做的（halation）或对**边缘**做的（色散），
# 所以红色纯度（R−B）在原理上不会漂：加性亮度只挪明暗，不动色差。
LOOK_SCURVE = 0.30        # S 曲线强度：0.30 ≈ 中间调斜率 +15%（15–25% 的下沿，克制优先）
LOOK_CLARITY = 0.08       # 微对比（8%，band-pass 在 3–24 px，避开 2 px 颗粒）
LOOK_HALATION = 0.05      # 高光暖白外溢峰值（亮度量，≤0.06）
LOOK_CA_PX = 0.50         # 边缘径向色散：R 外扩 / B 内收各 0.5 px（画幅边缘处；0.8 px 会破红色纯度红线）
TGT['look'] = dict(
    scurve=LOOK_SCURVE,
    scurve_paper=0.60,    # D 段 paper_mode 只做 0.6 倍（保宣纸通透）
    scurve_floor=-0.020,  # 阴影侧压暗的绝对上限（不许压出死黑）
    scurve_dc=0.88,       # 去掉 88% 的整体亮度偏移：只加对比，不改整体曝光
    clarity=LOOK_CLARITY,
    clarity_sig=12.0,     # 微对比半径（px）
    halation=LOOK_HALATION,
    hal_thr=0.80, hal_k=5.5, hal_sig=16.0,   # 只吃 luma>0.8 的高光，半径 16 px
    hal_gate=0.85,        # 已接近纯白的地方不再加光（防高光裁切）
    hi_guard=0.95, hi_guard_lo=0.80,   # S 曲线/微对比在高光肩部收手，绝不把高光推爆
    hal_col=(1.00, 0.50, 0.38),              # 暖白偏红（血月/刀光/金光会「上镜」一点；别偏到糖粉）
    ca_px=LOOK_CA_PX,
    ca_inner=0.85,        # 画面内侧 85% 半径不做，线性衰减到 0
)

# ---------------------------------------------------------------- 各段作者参数（照抄代码里的 finish 调用）
#   meas_* = 用 tools/grade_unify_cmp.py --probe 测出的该段收尾层材质指纹
SEC = {
    'a_intro_verse1': dict(vig=0.45, bloom=0.35, thr=0.72, grain=0.040, gs=1.00,
                           black=0.0126, white_clean=0.8422, cast_rb=-0.0449, red_pur=0.824),
    'b_pre1':         dict(vig=0.42, bloom=0.35, thr=0.72, grain=0.040, gs=1.00,
                           black=0.0127, white_clean=0.8473, cast_rb=-0.0449, red_pur=0.824),
    'chorus1':        dict(vig=0.42, bloom=0.35, thr=0.72, grain=0.040, gs=1.00,
                           black=0.0127, white_clean=0.8473, cast_rb=-0.0449, red_pur=0.824),
    'b_verse2':       dict(vig=0.42, bloom=0.35, thr=0.72, grain=0.040, gs=1.00,
                           black=0.0127, white_clean=0.8473, cast_rb=-0.0449, red_pur=0.824),
    'c_pre2_chorus2': dict(vig=0.40, bloom=0.42, thr=0.72, grain=0.040, gs=0.98,
                           black=0.0142, white_clean=0.8507, cast_rb=-0.0451, red_pur=0.812),
    'd_bridge':       dict(vig=0.45, vig_pm=-0.30, bloom=0.30, bloom_pm=-0.18, thr=0.75, thr_pm=0.17,
                           grain=0.040, grain_pm=0.40, gs=1.04,
                           black=0.0055, black_pm=0.0022, white_clean=0.8418, white_pm=0.0394,
                           cast_rb=-0.0443, cast_pm=0.0792, red_pur=0.8955),
    'e_final_outro':  dict(vig=0.38, bloom=0.25, thr=0.72, grain=0.035, gs=0.96,
                           black=0.0048, white_clean=0.8536, cast_rb=-0.0445, red_pur=0.8992),
}
# 帧区间（= units/sections.py 的 SECTIONS，左闭右开），供 key_for_t 用
_RANGES = [(0, 1321, 'a_intro_verse1'), (1321, 1784, 'b_pre1'), (1784, 2586, 'chorus1'),
           (2586, 3534, 'b_verse2'), (3534, 4839, 'c_pre2_chorus2'), (4839, 5797, 'd_bridge'),
           (5797, 7241, 'e_final_outro')]

def key_for_t(t):
    """按全局时间取段落键。接线时可以直接 apply(fr, t, key_for_t(t), cache)。"""
    f = int(round(t * 30))
    for a, b, k in _RANGES:
        if a <= f < b:
            return k
    return 'a_intro_verse1' if f < 1321 else 'e_final_outro'

_ALIAS = {'a': 'a_intro_verse1', 'b_pre1': 'b_pre1', 'pre1': 'b_pre1', 'chorus1': 'chorus1',
          'b_verse2': 'b_verse2', 'c': 'c_pre2_chorus2', 'd': 'd_bridge', 'e': 'e_final_outro'}

# ---------------------------------------------------------------- 接点局部匹配表（±2 s 斜坡）
# 由 tools/grade_unify_cmp.py --fit 从实拍帧统计拟合，再固化成常量（渲染时零成本、可复算）。
# 每项：(段落键, 曝光增益, 反差增益, 色温 tint[相对 R/B 增益], 红纯度增益)；左=接点前，右=接点后。
JOINT = {
    44.0333: dict(l=('a_intro_verse1', 1.060, 1.050, 0.0400, 1.000),
                    r=('b_pre1', 0.940, 0.950, -0.0263, 1.000)),
    59.4667: dict(l=('b_pre1', 1.060, 1.050, -0.0243, 1.000),
                    r=('chorus1', 0.940, 0.950, 0.0119, 1.000)),
    86.2000: dict(l=('chorus1', 0.940, 0.984, -0.0224, 1.000),
                    r=('b_verse2', 1.060, 1.027, 0.0359, 1.000)),
    117.8000: dict(l=('b_verse2', 1.060, 1.050, 0.0400, 1.000),
                    r=('c_pre2_chorus2', 0.940, 0.950, -0.0221, 1.000)),
    161.3000: dict(l=('c_pre2_chorus2', 0.940, 0.950, -0.0093, 1.000),
                    r=('d_bridge', 1.060, 1.050, 0.0209, 1.000)),
    193.2333: dict(l=('d_bridge', 0.940, 1.020, -0.0008, 1.000),
                    r=('e_final_outro', 1.060, 0.986, 0.0017, 1.000)),
}


JOINT_HOLD = 0.35     # 接点两侧保持满强度的时长（秒）
JOINT_RAMP = 2.00     # 到 2.0 s 时补偿降到 0（smoothstep）

# ---------------------------------------------------------------- 小工具
def _lum(f):
    return 0.3 * f[..., 0] + 0.59 * f[..., 1] + 0.11 * f[..., 2]

def _sstep(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)

def _blur_ds(a, sig, k=4):
    """降采样高斯（1 通道，1080p 上 ~1 ms）：够用且几乎不占预算。"""
    h, w = a.shape[:2]
    s = cv2.resize(a, (max(1, w // k), max(1, h // k)), interpolation=cv2.INTER_AREA)
    s = cv2.GaussianBlur(s, (0, 0), max(0.4, sig / k))
    return cv2.resize(s, (w, h), interpolation=cv2.INTER_LINEAR)

def _vign_mask(strength):
    """c1kit._vig 的同一条曲线（复刻，不 import c1kit，保持本模块独立）。"""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H * 0.42)) ** 2)
    v = np.clip(1 - (d - 0.5) * 0.85, 0, 1) ** 1.5
    return (1 - strength + strength * v).astype(np.float32)

@lru_cache(maxsize=16)
def _kernel(k):
    r = np.random.default_rng(1000 + k)
    return cv2.resize(cv2.GaussianBlur(r.standard_normal((H // 2, W // 2)).astype(np.float32), (0, 0), 0.7), (W, H))

def _grain_kernel(t):
    """c1kit._grain(int(t*30)%12) 的逐像素复刻 —— 全片同一个颗粒场与频率。
    （12 个核，按 int(t*30)%12 取；与各组 finish 里那一句完全同源，所以可以「等量扣除」。）"""
    return _kernel(int(t * 30) % 12)

# ---------------------------------------------------------------- 各阶段
def _grain_mod(L, p, pm=0.0):
    return (0.35 + 0.65 * (1 - np.clip(L, 0, 1)) + p.get('grain_pm', 0.0) * pm).astype(np.float32)

def _grain_measure(g, L, cache):
    """最小二乘估出「作者实际加的颗粒振幅」（与画面内容无关）：
    在半分辨率上，把颗粒场和画面走同一个高通，再求投影系数。
    画面细节与伪随机颗粒不相关，所以估计不被内容带偏。"""
    gs = cv2.resize(g, (W // 2, H // 2), interpolation=cv2.INTER_AREA)[(BAR + 8) // 2:(H - BAR - 8) // 2]
    Lh = cv2.resize(L, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    Lh = Lh[(BAR + 8) // 2:(H - BAR - 8) // 2]        # 只取画面区：黑边的硬边会污染高通
    s = 1.0
    hpL = Lh - cv2.GaussianBlur(Lh, (0, 0), s)
    q = gs * (0.35 + 0.65 * (1 - np.clip(Lh, 0, 1)))
    hpQ = q - cv2.GaussianBlur(q, (0, 0), s)          # 同一个高通：匹配滤波
    gx = cv2.Sobel(Lh, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(Lh, cv2.CV_32F, 0, 1, ksize=3)
    agr = np.abs(gx) + np.abs(gy)
    m = agr < np.percentile(agr, 55)                  # 平坦区：颗粒主导
    num = float((hpL[m] * hpQ[m]).sum())
    den = float((hpQ[m] * hpQ[m]).sum()) + 1e-12
    return float(np.clip(num / den, 0.0, 0.09))

def _tone(fr, L, p, pm):
    corr = float(np.clip(TGT['black'] - (p['black'] + p.get('black_pm', 0.0) * pm), *TGT['black_clip']))
    if abs(corr) > 1e-5:
        fr = fr + (corr * (1 - _sstep(0.0, 0.10, L)))[..., None]
    wh = p['white_clean'] + p.get('white_pm', 0.0) * pm
    k = float(np.clip(TGT['white'] / max(wh, 1e-3), 0.96, 1.04))
    if abs(k - 1) > 1e-4:
        fr = fr * (1 + (k - 1) * _sstep(0.55, 0.98, L))[..., None]
    return fr

def _bloom_swap(fr, p, pm):
    """把作者那一道 bloom 换成统一 bloom：只在 1/4 分辨率上算差量，一次升采样回来。"""
    a_a = p['bloom'] + p.get('bloom_pm', 0.0) * pm
    a_a = float(min(max(a_a, 0.0), 0.9))
    lo, hi = TGT['bloom']
    a_t = float(min(max(a_a, lo), hi))            # 压进带内（带内不动）
    if abs(a_t - a_a) < 1e-4:
        return fr
    thr_a = p['thr'] + p.get('thr_pm', 0.0) * pm
    h, w = fr.shape[:2]
    fh = cv2.resize(fr, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    hi_t = np.clip(fh - TGT['bloom_thr'], 0, None)          # 目标：阈值 0.72 / 半径 26
    hi_a = np.clip(fh - thr_a, 0, None)                      # 作者：C 组 0.42、D paper 抬阈值降量、E 0.25
    sg = TGT['bloom_sig'] / 4.0
    b_t = cv2.GaussianBlur(hi_t, (0, 0), sg) * a_t + cv2.GaussianBlur(hi_t, (0, 0), sg * 0.3) * a_t * 0.5
    b_a = cv2.GaussianBlur(hi_a, (0, 0), sg) * a_a + cv2.GaussianBlur(hi_a, (0, 0), sg * 0.3) * a_a * 0.5
    d = cv2.resize(b_t - b_a, (w, h), interpolation=cv2.INTER_LINEAR)
    lim = TGT['bloom_clip']
    return fr + np.clip(d, -lim, lim)


def _vig_swap(fr, p, pm, cache):
    va = max(0.0, p['vig'] + p.get('vig_pm', 0.0) * pm)
    vt = TGT['vig']
    key = ('v', round(va, 3), round(vt, 3))
    corr = cache.get(key)
    if corr is None:
        lo, hi = TGT['vig_clip']
        r = (_vign_mask(vt) / np.maximum(_vign_mask(va), 1e-3)) ** TGT['vig_beta']
        corr = cache[key] = np.clip(r, lo, hi).astype(np.float32)[..., None]
    return fr * corr

def _color(fr, p, pm, cache, skey):
    """中性色温（R−B）与红色纯度：段落级 3×3 对角补偿（保亮度、只收偏移）。"""
    key = ('c', skey, round(pm, 2))
    g = cache.get(key)
    if g is None:
        cast = p['cast_rb'] + p.get('cast_pm', 0.0) * pm
        Lm = 0.35
        s = float(np.clip(-TGT['cast_strength'] * (cast - TGT['cast_rb']) / Lm, -0.06, 0.06))
        gr, gb = 1.0 + s / 2, 1.0 - s / 2
        gg = -(0.3 * (gr - 1) + 0.11 * (gb - 1)) / 0.59 + 1.0
        kr = float(np.clip(1 + TGT['red_strength'] * (TGT['red_pur'] / max(p['red_pur'], 1e-3) - 1), 0.92, 1.08))
        g = cache[key] = (np.array([gr, gg, gb], np.float32), kr)
    gains, kr = g
    fr = fr * gains
    if abs(kr - 1) > 2e-3:
        r = fr[..., 0]
        mx = np.maximum(fr[..., 1], fr[..., 2])
        ex = r - mx
        m = _sstep(0.015, 0.09, ex) * (ex > 0)
        out = fr.copy()
        out[..., 0] = r + (kr - 1) * ex * m
        fr = out
    return fr

def _joint(fr, t, L, cache):
    """接点前后 ±2 s 的局部统计对齐（曝光/反差/色温/红纯度），满强度 0.35 s 后 smoothstep 收到 2 s。"""
    f = int(round(t * 30))
    best = None
    for J, e in JOINT.items():
        d = abs(t - J)
        if d <= JOINT_RAMP:
            if best is None or d < best[0]:
                best = (d, J, e)
    if best is None:
        return fr
    d, J, e = best
    w = 1.0 if d <= JOINT_HOLD else 1 - _sstep(JOINT_HOLD, JOINT_RAMP, d)
    if w <= 1e-3:
        return fr
    _, gain, con, tint, red = e['l'] if f < int(round(J * 30)) else e['r']
    if abs(gain - 1) < 1e-4 and abs(con - 1) < 1e-4 and abs(tint) < 1e-5 and abs(red - 1) < 1e-4:
        return fr
    m = float(L.mean())
    g = 1 + (gain - 1) * w                # 曝光：整幅乘一个 ≤6% 的增益（保住镜头自身的明暗起伏）
    k = 1 + (con - 1) * w                 # 反差：以帧均值为轴缩放
    out = (fr - m) * (g * k) + m * g
    if abs(tint) > 1e-5:
        sd = tint * w                     # 色温：R/B 反向微调，亮度守恒
        out = out * np.array([1 + sd, 1 - 0.322 * sd, 1 - sd], np.float32)
    if abs(red - 1) > 1e-4:
        kr = 1 + (red - 1) * w
        r = out[..., 0]
        ex = r - np.maximum(out[..., 1], out[..., 2])
        mm = _sstep(0.015, 0.09, ex) * (ex > 0)
        out = out.copy()
        out[..., 0] = r + (kr - 1) * ex * mm
    return out

# ---------------------------------------------------------------- 第 9 阶段：胶片 look
def _look(fr, L, p, pm, cache):
    """全片同一套「摄影机手感」：统一 S 曲线 + 微对比 + 高光 halation + 边缘径向色散。

    红色纯度为什么不会漂：
      S 曲线与微对比都是「三通道加同一个数」→ R−B 严格不变（实测 |Δ|<0.0003）；
      halation 只吃 luma>0.8 的高光，暗红/中红进不来（实测 |Δ|<0.003）；
      色散是空间位移，只有在画幅外侧 15% 半径才生效，实测红色区 R−B 最坏 −0.0075
      （1321 帧片尾名册的 1px 朱红竖线是最苛刻的样本），仍在 0.01 红线内。
    性能：单通道预算 + 就地写 + 1/4 分辨率模糊，1080p 上约 45–55 ms。
    """
    lk = TGT['look']
    mul = 1.0 - (1.0 - lk['scurve_paper']) * pm       # D 段 paper_mode 降到 0.6 倍

    d = None
    s = lk['scurve'] * mul                            # ① 统一 S 曲线（f(0)=0, f(1)=1）
    if s > 1e-4:
        d = L * (1.0 - L)
        d *= (2.0 * L - 1.0)
        d *= s
        np.maximum(d, lk['scurve_floor'], out=d)      # 阴影侧压暗有地板，不压出死黑

    c = lk['clarity'] * mul                           # ② 微对比（band-pass，不放大颗粒）
    if c > 1e-4:
        Ls = _blur_ds(L, 2.0, 2)
        hi = Ls - _blur_ds(Ls, lk['clarity_sig'])
        np.clip(hi, -0.15, 0.15, out=hi)
        hi *= c
        d = hi if d is None else d + hi

    if d is not None:                                 # 两次亮度量合成一次加（省一次整幅加法）
        d -= lk['scurve_dc'] * float(d.mean())
        g = 1.0 - lk['hi_guard'] * np.clip((1.0 - L) / max(1e-3, 1.0 - lk['hi_guard_lo']), 0, 1)
        d *= g                                            # 高光肩部收手，不推爆高光
        fr += d[..., None]

    if lk['halation'] > 1e-5:                         # ③ 高光 halation（暖白外溢一圈）
        m = np.clip((L - lk['hal_thr']) * lk['hal_k'], 0, 1)
        hb = _blur_ds(m, lk['hal_sig'])
        hb *= lk['halation']
        hb *= 1.0 - lk['hal_gate'] * np.minimum(L, 1.0)     # 已接近纯白的地方不再加光
        col = lk['hal_col']
        hb3 = cv2.merge((hb * col[0], hb * col[1], hb * col[2]))
        # 滤色叠加 fr + hb*(1-fr)：永远推不爆高光，且复用 scratch 免分配
        sc = cache.get('scr')
        if sc is None or sc.shape != fr.shape:
            sc = cache['scr'] = np.empty_like(fr)
        np.subtract(1.0, fr, out=sc)
        sc *= hb3
        fr += sc

    if lk['ca_px'] > 1e-3:                            # ④ 极轻边缘径向色散
        key = ('ca', round(lk['ca_px'], 2), round(lk['ca_inner'], 2))
        got = cache.get(key)
        if got is None:
            eps = lk['ca_px'] / (W / 2.0)
            cx, cy = W / 2.0, H / 2.0
            MR = np.array([[1 - eps, 0, eps * cx], [0, 1 - eps, eps * cy]], np.float32)   # R 外扩
            MB = np.array([[1 + eps, 0, -eps * cx], [0, 1 + eps, -eps * cy]], np.float32)  # B 内收
            y, x = np.mgrid[0:H, 0:W].astype(np.float32)
            u = np.sqrt(((x - cx) / cx) ** 2 + ((y - cy) / cy) ** 2)
            mk = np.clip((u - lk['ca_inner']) / (1.0 - lk['ca_inner']), 0, 1).astype(np.float32)
            got = cache[key] = (MR, MB, mk)
        MR, MB, mk = got
        r0 = fr[..., 0]
        b0 = fr[..., 2]
        rw = cv2.warpAffine(r0, MR, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        bw = cv2.warpAffine(b0, MB, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        fr[..., 0] = r0 + (rw - r0) * mk
        fr[..., 2] = b0 + (bw - b0) * mk
    return fr

# ---------------------------------------------------------------- 主入口
def apply(fr, t, section_key, cache=None, hint=None):
    if not enabled():
        return fr
    cache = _GC if cache is None else cache
    key = _ALIAS.get(section_key, section_key)
    key = 'b_pre1' if key == 'b_pre1' else key
    p = SEC.get(key)
    if p is None:
        return fr
    pm = float((hint or {}).get('pm', 0.0))
    src = np.asarray(fr)
    out = (src.astype(np.float32) / 255.0) if src.dtype == np.uint8 else np.array(src, dtype=np.float32, copy=True)

    L = _lum(out)
    g = _grain_kernel(t)
    a_tgt = TGT['grain'] * p['gs']
    a_hat = _grain_measure(g, L, cache)                 # 作者实际加了多少颗粒（逐帧反解）
    nom = p['grain'] + p.get('grain_pm', 0.0) * pm * p['grain']   # 代码里的名义值，做安全带
    a_hat = float(np.clip(a_hat, 0.4 * nom, 1.6 * nom))  # 反解失效的帧不许「加两遍颗粒」
    mod = _grain_mod(L, p, pm)
    if a_hat > 0.002:                                   # 1 先整段扣掉作者颗粒（同核，频率天然一致）
        out = out - (a_hat * g * mod)[..., None]
    out = _tone(out, L, p, pm)                          # 2 黑位/白点
    out = _bloom_swap(out, p, pm)                       # 3 辉光量/半径
    out = _vig_swap(out, p, pm, cache)                  # 4 暗角曲线
    out = _color(out, p, pm, cache, key)                # 5 中性色温 + 红色纯度
    if JOINT:
        out = _joint(out, t, _lum(out), cache)          # 6 接点局部匹配
    if TGT.get('look') and os.environ.get('GRADE_LOOK', '1') != '0':   # 9 胶片 look（放在颗粒之前，见报告 §9）
        out = _look(out, _lum(out), p, pm, cache)
    # 7 加统一颗粒（最后一道，保证全片颗粒在同一层、同一强度）
    L2 = _lum(out)
    out = out + (a_tgt * g * _grain_mod(L2, p, pm))[..., None]
    out = np.clip(out, 0, 1).astype(np.float32)
    out[:BAR] = 0                                       # 8 复位 2.39 黑边
    out[H - BAR:] = 0
    return out
