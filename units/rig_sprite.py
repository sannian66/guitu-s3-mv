"""units/rig_sprite.py — 生图贴图 + 代码骨架 puppet（2026-11-09）

把 RH_image2 生图 + 绿幕抠像（tools/cutout_green.py）得到的多角度立绘，变成「能转身、抬刀、劈砍」
的 puppet，而**不按部位硬切图层**（硬切拼贴必露接缝）。做法：

  1) **蒙皮变形**：整张立绘按几何位置 + alpha 轮廓算 12 组权重场（头/颈、肩、上臂、前臂、手、
     躯干、衣摆、腿、刀），骨架（髋→脊柱→肩→肘→腕→刀，含父子链）的仿射位移按权重混合，
     用**一次** `cv2.remap` 把整张图一起揉。权重在关节处平滑过渡（胶囊距离高斯），所以没有拼贴缝。
  2) **转头 = 多角度替换 + 交叉过渡**：front / tq_r / side_r / view_tq_l 按「眼线 → 脚底」归一化到
     同一骨架单位空间，head_turn 在相邻角度之间交叉过渡；头部单独一层，「头框软擦除」把正面旧头
     抹掉再贴侧头（避免双头影），底边羽化融进衣领。身体默认用正面，turn 大时同步换 tq/side。
  3) **表情**：expr 特写图自动定位脸部（皮肤连通块 → 眉毛行 + 脸宽），按脸宽归一化贴到全身图头部，
     软羽化 + 与原脸的均值差修正；expr='calm' 直接用 base。
  4) **举刀/劈砍**：pose_raise / pose_slash / pose_draw 作整姿势键帧交叉过渡（最稳），
     骨架只负责过渡中间帧的形变（键帧权重越高骨架越弱，避免双重形变）。

单位空间（unit space）—— 全部几何都在这里定义，图片像素只在取贴图时出现
---------------------------------------------------------------------
  x 向右、y 向上；y=0 = 脚底，**y=1.0 = 眼线**（每张立绘自动实测），x=0 = 身体中线。
  1 单位 = 「眼线 → 脚底」的像素高度。实测经验值（front：H=1045px）：
    头顶发梢 1.11 / 发髻 1.19 / 眼 1.00 / 下巴 0.94 / 颈 0.92 / 肩 0.89 /
    手 0.56 / 腰 0.565 / 髋 0.545 / 膝 0.25。

接口（与 units/sprite.py 同构：颜色为显示空间 float32 0..1，返回 (fr, alpha_map)）
------------------------------------------------------------------------------
    rig = PoseRig(base='assets/gen/char', work_w=2048)
    fr, a = rig.draw(fr, t, pose, dst=(960, 900), h=680, look=None, rim=None,
                     grade=None, alpha=1.0, defocus=0.0, mblur=0.0)

    dst = 脚底中点的画面坐标；h = 人物总高（脚底 → 头顶发梢）像素。
    pose：head_turn −1..1（负=转向画面左）、head_pitch −.5...5、lean −.3...3（正=后仰）、
          twist −.3...3、arm_r 0..110（**右臂 = 画面左臂 = 持刀手**）、elbow_r 0..90、
          arm_l、elbow_l、knee −.2...2（正=重心下沉）、sword（刀相对手的角度，正=刀尖向内上收）、
          expr 'calm'|'angry'|'smirk'|'look'、body_turn −1..1（可选，身体朝向）、
          key 'raise'|'slash'|'draw' + key_w 0..1（整姿势键帧权重）。

性能：单帧 < 0.25s。所有运算只在落点包围盒内做；权重场在 248×270 的粗网格上算好一次，
每帧只算每根骨的仿射位移（网格级），再插值放大成 remap 贴图。
"""
import math, os, sys
import numpy as np
import cv2
from PIL import Image

# ---------------------------------------------------------------- 复用 sprite.py（不抄一份）
_LOOK_FN = None
_RED_FN = None


def _look_import():
    """延迟 import units/sprite.py 的 _look / red_mask。"""
    global _LOOK_FN, _RED_FN
    if _LOOK_FN is not None:
        return _LOOK_FN, _RED_FN
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
    from units.sprite import _look, red_mask      # noqa: E402
    _LOOK_FN, _RED_FN = _look, red_mask
    return _LOOK_FN, _RED_FN


# ---------------------------------------------------------------- 单位空间常量（眼线为 y=1）
NECK_U = 0.920
SHOULDER_U = 0.890
HIP_U = 0.545
KNEE_U = 0.250
HEAD_C_U = 1.055           # 头几何中心（权重高斯中心）
FACE_W_U = 0.065           # 脸宽（半身特写定尺度用）

GX0, GX1 = -0.62, 0.62     # 权重场覆盖（刀尖在 −0.42）
GY0, GY1 = -0.05, 1.26
GW, GH = 248, 262

_RAW = {}
_GEOM = {}
_WT = {}


def _fill_holes(F, A, preA):
    """蒙皮把某块（手臂/刀/旧头）挪走后露出背景的地方，用 inpaint 补成「原来被挡住的东西」。

    二维贴图蒙皮的固有缺陷：手臂底下没有像素（原图里被手臂挡着）。
    洞 = 原轮廓内、变形后 alpha 掉了的区域；用 TELEA inpaint 填色 + 恢复 alpha，
    相当于「补画被手臂遮住的躯干」。洞很小时（<40px）跳过。
    """
    hole = (preA > 0.6) & (A < 0.45)
    if int(hole.sum()) < 40:
        return F, A
    m = cv2.dilate(hole.astype(np.uint8) * 255, np.ones((3, 3), np.uint8))
    f8 = np.clip(F * 255.0, 0, 255).astype(np.uint8)
    F2 = cv2.inpaint(f8, m, 4, cv2.INPAINT_TELEA).astype(np.float32) / 255.0
    soft = cv2.erode((preA > 0.5).astype(np.float32), np.ones((5, 5), np.uint8))
    soft = cv2.GaussianBlur(soft, (0, 0), 1.2)
    w = hole.astype(np.float32)
    w = cv2.GaussianBlur(w, (0, 0), 1.0)
    F2 = F + (F2 - F) * w[..., None]
    A2 = np.maximum(A, soft * w)
    return F2, A2


def _sstep(a, b, x):
    x = np.clip((x - a) / (b - a), 0, 1)
    return x * x * (3 - 2 * x)


MIR = 'mirror:'          # 虚拟路径前缀：水平镜像（左 3/4 / 左侧脸用；成本 0，不落盘）


def _mirrored(path):
    return str(path).startswith(MIR)


def _load(path, width=1024):
    """解码 + 缩放 mip（缓存）。

    **uint8 存储**（内存省 4 倍、warp 带宽省 4 倍）：13 张全 float32 约 290MB，
    会把 L2/L3 挤爆，实测单帧慢一倍；uint8 存 ~127MB，warp 完再转 float32 只在小盒子里做。
    返回 (F uint8 hxwx3, A uint8 hxw)。
    """
    if _mirrored(path):
        F, A = _load(str(path)[len(MIR):], width)
        return np.ascontiguousarray(F[:, ::-1]), np.ascontiguousarray(A[:, ::-1])
    key = (os.path.abspath(str(path)), int(width))
    got = _RAW.get(key)
    if got is not None:
        return got
    im = Image.open(str(path)).convert('RGBA')
    h = max(1, round(im.size[1] * width / im.size[0]))
    a = np.asarray(im.resize((width, h), Image.LANCZOS))
    got = (np.ascontiguousarray(a[..., :3]), np.ascontiguousarray(a[..., 3]))
    _RAW[key] = got
    return got


def _skin_mask(F, A):
    """F/A 为 uint8（0..255）。"""
    r, g, b = F[..., 0].astype(np.float32), F[..., 1].astype(np.float32), F[..., 2].astype(np.float32)
    F = np.stack([r, g, b], -1) / 255.0
    r, g, b = F[..., 0], F[..., 1], F[..., 2]
    lum = F.mean(-1)
    m = ((r > g + 0.02) & (g > b - 0.01) & (r > b + 0.04) &
         (lum > 0.16) & (lum < 0.92) & (A > 0.5)).astype(np.uint8)
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def _geom(path, width=1024):
    """实测一张立绘的骨架单位空间参数（缓存）。"""
    if _mirrored(path):
        b = _geom(str(path)[len(MIR):], width)
        w = b['w']
        mx = lambda x: w - 1 - x                      # noqa: E731
        m = dict(b)
        m['cx'] = mx(b['cx'])
        m['eye'] = (mx(b['eye'][0]), b['eye'][1])
        m['head'] = (mx(b['head'][2]), b['head'][1], mx(b['head'][0]), b['head'][3])
        m['bbox'] = (mx(b['bbox'][2] - 1), b['bbox'][1], mx(b['bbox'][0] - 1) + 1, b['bbox'][3])
        m['hands'] = {'r': (mx(b['hands']['l'][0]), b['hands']['l'][1]),
                      'l': (mx(b['hands']['r'][0]), b['hands']['r'][1])}
        if b.get('sword'):
            m['sword'] = ((mx(b['sword'][0][0]), b['sword'][0][1]),
                          (mx(b['sword'][1][0]), b['sword'][1][1]))
        m['mirror_of'] = str(path)[len(MIR):]
        return m
    key = (os.path.abspath(str(path)), int(width))
    got = _GEOM.get(key)
    if got is not None:
        return got
    F, A = _load(path, width)
    hh, ww = A.shape
    m = A > 127
    if not m.any():
        raise ValueError(f'空 alpha：{path}')
    ys, xs = np.nonzero(m)
    feet, top = float(ys.max()), float(ys.min())
    span = feet - top
    rows = [r for r in range(int(feet - 0.62 * span), int(feet - 0.52 * span), 4) if m[r].any()]
    cx = float(np.median([np.median(np.nonzero(m[r])[0]) for r in rows])) if rows else 0.5 * ww
    # 皮肤块：脸（最大）→ 手
    sk = _skin_mask(F, A)
    nl, lab, st, cen = cv2.connectedComponentsWithStats(sk, 8)
    order = [i for i in np.argsort(-st[1:, cv2.CC_STAT_AREA]) + 1 if st[i, cv2.CC_STAT_AREA] > 300]
    bust = False
    face = None
    if order:
        i0 = order[0]
        x, y, w_, h_, ar = st[i0]
        if y < top + 0.30 * span:                        # 最大的皮肤块在身体上部 → 那是脸
            face = (float(cen[i0][0]), float(y), float(w_), float(h_))   # (fx, 脸框顶, 脸宽, 脸框高)
            if ar > 0.20 * span * ww:                     # 特写：皮肤块占了画面一大片
                bust = True
            # 半身/胸像：alpha 三边以上顶到画布边缘（人物被画框裁掉）→ 没有脚底
            if xs.min() <= 2 and ys.min() <= 2 and (xs.max() >= ww - 3 or ys.max() >= hh - 3):
                bust = True
    if face is None:
        # 没有正脸（背面图 / 纯剪影）：用 alpha 轮廓按比例推眼行。
        # 标定值来自 front 实测：(眼行-头顶)/(脚底-头顶) = 0.104 → headtop_u 自动落在 1.116
        face = (cx, top + 0.104 * span - 0.21 * (0.104 * span), 0.065 * span, 0.104 * span)
        eye_faceless = top + 0.104 * span
    else:
        eye_faceless = None
    fx, ftop, fw, fh = face
    eye = eye_faceless if eye_faceless is not None else ftop + 0.21 * fh
    # 半身判定的第四条：脚不在画面里时 (脚底-头顶)/(脚底-眼) 会明显 > 1.2（真全身图 1.10~1.19）。
    # S043 那种「脸很大的半身横幅」(1024×576，人物只占中间) 就是被这条抓回来的。
    if not bust and (feet - eye) > 8 and (feet - top) / (feet - eye) > 1.34:
        bust = True
    if bust:
        H = fw / FACE_W_U                               # 半身：用脸宽定尺度（同人物 FACE_W_U 恒定）
        feet = eye + H
        cx = fx                                         # 半身图里「身体中线」没有意义，用脸心
    else:
        H = feet - eye
    # 两只手：脸以外最大的两个皮肤块（画面左 = 人物右手 = 持刀手）
    hands = {}
    cand = [] if bust else [cen[i] for i in order[1:]
                            if st[i, cv2.CC_STAT_AREA] > 800 and cen[i][1] > top + 0.30 * span]
    cand = sorted(cand[:6], key=lambda c: c[0])
    if len(cand) >= 2:
        hands['r'] = (float(cand[0][0]), float(cand[0][1]))
        hands['l'] = (float(cand[-1][0]), float(cand[-1][1]))
    else:
        hands['r'] = (cx - 0.161 * H, feet - 0.561 * H)
        hands['l'] = (cx + 0.163 * H, feet - 0.564 * H)
    # 头框（含发，供头部补丁裁剪）
    hband = int(top + 0.24 * span)
    cols = np.nonzero(m[:hband].any(0))[0]
    headbox = (int(cols.min()), int(top), int(cols.max()), int(eye - 0.02 * H))
    # 刀：右手 → mask 左下极值（A-pose 刀尖朝左下）
    sword = None
    if not bust and cand:
        uu = (xs - cx) / H
        vv = (feet - ys) / H
        low = vv < 0.45
        if low.any() and hands['r'][0] < cx:
            k = int(np.argmin(uu[low]))
            tip = (float(xs[low][k]), float(ys[low][k]))
            if math.hypot(tip[0] - hands['r'][0], tip[1] - hands['r'][1]) > 0.22 * H:
                sword = (hands['r'], tip)
    # alpha 支撑 bbox（裁剪用）
    bbox = (int(xs.min()), int(top), int(xs.max()) + 1, int(feet) + 1)
    got = dict(H=H, cx=cx, eye=(fx, eye), eye_y=eye, facew=fw, faceh=fh, feet=feet, top=top, bust=bust,
               headtop_u=(feet - top) / H, head=headbox, hands=hands, sword=sword,
               bbox=bbox, w=ww, h=hh)
    _GEOM[key] = got
    return got


# ---------------------------------------------------------------- 权重场（单位空间粗网格）
def _capsule(gu, gv, p0, p1, r, pw=4.0):
    """到线段 p0-p1 的距离 → 平顶软边界成员度 exp(-(d/r)^pw)。

    pw=4 让「肢体内部 ≈1、边界外迅速掉到 0」，这样归一化后肢体在自己那块地上压倒躯干
    （pw=2 的高斯太平缓，手臂权重只有 0.5，抬手只抬一半 —— 这是第一版的实际 bug）。
    """
    ax, ay = p0
    dx, dy = p1[0] - ax, p1[1] - ay
    L2 = dx * dx + dy * dy + 1e-9
    t = np.clip(((gu - ax) * dx + (gv - ay) * dy) / L2, 0, 1)
    d = np.sqrt((gu - (ax + t * dx)) ** 2 + (gv - (ay + t * dy)) ** 2)
    return np.exp(-((d / r) ** pw)), d


def _blob(gu, gv, c, a, b, pw=4.0):
    """各向异性平顶软椭圆成员度（头/颈用）。"""
    return np.exp(-(((gu - c[0]) / a) ** 2 + ((gv - c[1]) / b) ** 2) ** (pw / 2))


def _weights(path, width=1024):
    """整张立绘的骨架权重场（单位空间粗网格 GW×GH）+ 关节点。"""
    kk = os.path.abspath(str(path))
    got = _WT.get(kk)
    if got is not None:
        return got
    g = _geom(path, width)
    H, cx, feet = g['H'], g['cx'], g['feet']
    gu = np.linspace(GX0, GX1, GW, dtype=np.float32)[None, :].repeat(GH, 0)
    gv = np.linspace(GY0, GY1, GH, dtype=np.float32)[:, None].repeat(GW, 1)
    F, A = _load(path, width)
    # 细结构（发丝 / 刀身）：离轮廓越近越细
    dt = cv2.distanceTransform((A > 127).astype(np.uint8), cv2.DIST_L2, 5)
    thin_img = (np.clip(1.0 - dt / (0.020 * H), 0, 1) ** 1.5 * (A > 100)).astype(np.float32)
    map_x = np.ascontiguousarray(np.repeat(cx + gu[:1] * H, GH, 0), np.float32)
    map_y = np.ascontiguousarray(np.repeat(feet - gv[:, :1] * H, GW, 1), np.float32)
    A_g = cv2.remap(A, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT).astype(np.float32) / 255.0
    thin = cv2.remap(thin_img, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    mask_g = np.clip((A_g - 0.25) / 0.5, 0, 1)
    # 关节点（单位空间）
    hr, hl = g['hands']['r'], g['hands']['l']
    wr = ((hr[0] - cx) / H, (feet - hr[1]) / H)
    wl = ((hl[0] - cx) / H, (feet - hl[1]) / H)
    sh_r, sh_l = (-0.100, SHOULDER_U), (0.100, SHOULDER_U)
    el_r = (0.5 * (sh_r[0] + wr[0]) - 0.014, 0.5 * (sh_r[1] + wr[1]))
    el_l = (0.5 * (sh_l[0] + wl[0]) + 0.014, 0.5 * (sh_l[1] + wl[1]))
    w = {}
    # 头/颈：头心平顶椭圆 + 头发细丝（发髻、披发跟着头走）
    w['head'] = (_blob(gu, gv, (0.0, HEAD_C_U), 0.098, 0.135) +
                 0.9 * thin * _sstep(0.78, 0.88, gv)).astype(np.float32)
    # 躯干 / 衣摆 / 腿：按高度分层，但让出「手臂自己那块地」（外侧 |x| 大处归手臂）
    core = (1.0 - 0.85 * np.clip((np.abs(gu) - 0.055) / 0.045, 0, 1) *
            _sstep(0.62, 0.72, gv) * _sstep(0.98, 0.86, gv))
    w['spine'] = (core * _sstep(HIP_U - 0.05, HIP_U + 0.05, gv) * _sstep(1.00, 0.93, gv)).astype(np.float32)
    w['skirt'] = (_sstep(HIP_U + 0.03, HIP_U - 0.09, gv) * _sstep(-0.02, 0.07, gv) * 0.85).astype(np.float32)
    w['leg'] = (_sstep(HIP_U + 0.03, HIP_U - 0.05, gv) * _sstep(-0.05, 0.04, gv)).astype(np.float32)
    gate_r = _sstep(0.048, 0.090, -gu)          # 右臂 = 画面左：只在左外侧
    gate_l = _sstep(0.048, 0.090, gu)
    w['sh_r'] = (_capsule(gu, gv, sh_r, el_r, 0.052)[0] * gate_r).astype(np.float32)
    w['el_r'] = (_capsule(gu, gv, el_r, wr, 0.045)[0] * gate_r).astype(np.float32)
    w['sh_l'] = (_capsule(gu, gv, sh_l, el_l, 0.052)[0] * gate_l).astype(np.float32)
    w['el_l'] = (_capsule(gu, gv, el_l, wl, 0.045)[0] * gate_l).astype(np.float32)
    w['ha_r'] = _capsule(gu, gv, wr, wr, 0.042)[0].astype(np.float32)
    w['ha_l'] = _capsule(gu, gv, wl, wl, 0.042)[0].astype(np.float32)
    sw = np.zeros_like(gu, np.float32)
    if g['sword'] is not None:
        t0, t1 = g['sword']
        p0 = ((t0[0] - cx) / H, (feet - t0[1]) / H)
        p1 = ((t1[0] - cx) / H, (feet - t1[1]) / H)
        _, d = _capsule(gu, gv, p0, p1, 0.03)
        # 只要「窄带 ∩ 细结构」：刀身很细，衣摆/腰带是厚的，用 thin 硬门槛挡住它们（否则会挖洞）
        sw = (np.exp(-(d / 0.024) ** 4) * _sstep(0.30, 0.55, thin)).astype(np.float32)
        sw = np.maximum(sw, _capsule(gu, gv, p0, p0, 0.045)[0] * 0.9)    # 刀柄跟手
    w['sword'] = sw
    w['root'] = np.full_like(gu, 0.05, np.float32)                       # 兜底权重（防归一化除零）
    # 实测的「头部区域」遮罩（含发，用于转头时擦掉旧头；矩形窗会啃到肩膀）
    headmask = (np.clip((w['head'] - 0.18) / 0.25, 0, 1) * mask_g).astype(np.float32)
    headmask = cv2.GaussianBlur(headmask, (0, 0), 6.0)
    headmask = np.maximum(headmask, cv2.GaussianBlur(headmask, (0, 0), 18.0) * 0.9)
    out = dict(gx=gu, gy=gv, w=w, thin=thin, mask=mask_g, headmask=headmask,
               joints=dict(sh_r=sh_r, sh_l=sh_l, el_r=el_r, el_l=el_l, wr=wr, wl=wl,
                           hip=(0.0, HIP_U), neck=(0.0, NECK_U)),
               H=H, cx=cx, feet=feet)
    _WT[kk] = out
    return out


# ---------------------------------------------------------------- 骨架：pose → 每根骨的仿射
_PARENT = {'root': None, 'spine': 'root', 'skirt': 'root', 'leg': 'root',
           'head': 'spine', 'sh_r': 'spine', 'el_r': 'sh_r', 'ha_r': 'el_r', 'sword': 'ha_r',
           'sh_l': 'spine', 'el_l': 'sh_l', 'ha_l': 'el_l'}
_ORDER = ('root', 'leg', 'skirt', 'spine', 'head', 'sh_r', 'el_r', 'ha_r', 'sword',
          'sh_l', 'el_l', 'ha_l')


def _rot(a_deg, cx, cy):
    a = math.radians(a_deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, cx - c * cx + s * cy],
                     [s, c, cy - s * cx - c * cy]], np.float32)


def _shear(kx, cy):
    return np.array([[1.0, kx, -kx * cy], [0.0, 1.0, 0.0]], np.float32)


def _mul(A, B):
    M = np.eye(3, dtype=np.float32); M[:2] = A
    N = np.eye(3, dtype=np.float32); N[:2] = B
    return (M @ N)[:2].astype(np.float32)


def bone_affines(joints, pose):
    """pose → dict[bone] = 单位空间 world 仿射（y 向上，正角 = 画面逆时针）。"""
    p = pose or {}
    lean = float(np.clip(p.get('lean', 0.0), -0.6, 0.6))
    twist = float(np.clip(p.get('twist', 0.0), -0.8, 0.8))
    knee = float(np.clip(p.get('knee', 0.0), -0.4, 0.4))
    pitch = float(np.clip(p.get('head_pitch', 0.0), -1.0, 1.0))
    turn = float(np.clip(p.get('head_turn', 0.0), -1.2, 1.2))
    arm_r = math.degrees(0.0) + float(np.clip(p.get('arm_r', 0.0), -40, 170))
    arm_l = float(np.clip(p.get('arm_l', 0.0), -40, 170))
    elb_r = float(np.clip(p.get('elbow_r', 0.0), -20, 140))
    elb_l = float(np.clip(p.get('elbow_l', 0.0), -20, 140))
    swd = float(np.clip(p.get('sword', 0.0), -170, 170))
    hip = joints['hip']; neck = joints['neck']
    A = {}
    A['root'] = np.array([[1, 0, 0.0], [0, 1, -0.10 * max(knee, 0.0)]], np.float32)
    A['leg'] = np.array([[1, 0, 0.0], [0, 1, 0.0]], np.float32)          # 位移在 _disp 里按高度渐变
    A['skirt'] = np.array([[1, 0, 0.0], [0, 1, -0.03 * max(knee, 0.0)]], np.float32)
    Ms = _rot(lean * 13.0, hip[0], hip[1])
    Ms = _mul(_shear(twist * 0.16, hip[1]), Ms)
    A['spine'] = _mul(Ms, A['root'])
    A['head'] = _mul(_rot(pitch * 9.0 - turn * 2.0, neck[0], neck[1]), Ms)
    # 右臂 = 画面左臂：抬手 = 绕肩「顺时针」（y 向上坐标系里负角）
    A['sh_r'] = _mul(_rot(-arm_r, *joints['sh_r']), Ms)
    A['sh_l'] = _mul(_rot(+arm_l, *joints['sh_l']), Ms)
    A['el_r'] = _mul(_rot(+elb_r, *joints['el_r']), A['sh_r'])    # 肘：向体内收
    A['el_l'] = _mul(_rot(-elb_l, *joints['el_l']), A['sh_l'])
    A['ha_r'] = A['el_r']
    A['ha_l'] = A['el_l']
    A['sword'] = _mul(_rot(+swd, *joints['wr']), A['ha_r'])       # 刀：绕腕
    return A


# ---------------------------------------------------------------- 主体
# (名字, 文件, 该图实际的头部偏转, 仅用于哪一层：'both'/'head'/'body')
# 实测：tq_r 只转了约 20°（生图没转够），view_tq_l 转了约 40°。所以右侧的 40° 头用
# view_tq_l 的**镜像**补（头贴片镜像无所谓；身体镜像会左右反穿，故只给 head 用）。
_ANGLE_FILES = [('front', 'hero_front_cut.png', 0.00, 'both'),
                ('tq_r', 'hero_tq_r_cut.png', 0.30, 'body'),
                ('tq_r_m', MIR + 'hero_view_tq_l_cut.png', 0.45, 'head'),
                ('side_r', 'hero_side_r_cut.png', 1.00, 'both'),
                ('tq_l', 'hero_view_tq_l_cut.png', -0.45, 'both'),
                ('side_l', MIR + 'hero_side_r_cut.png', -1.00, 'head'),
                ('back', 'hero_back_cut.png', 1.70, 'both')]
_EXPR_FILES = {'calm': 'hero_expr_calm_cut.png', 'angry': 'hero_expr_angry_cut.png',
               'smirk': 'hero_expr_smirk_cut.png', 'look': 'hero_expr_look_cut.png'}
_KEY_FILES = {'raise': 'hero_pose_raise_cut.png', 'slash': 'hero_pose_slash_cut.png',
              'draw': 'hero_pose_draw_cut.png'}


class PoseRig:
    """生图立绘 puppet：正面 + 转头 + 举刀/劈砍 + 表情。"""

    def __init__(self, base='assets/gen/char', work_w=2048, angles=None):
        self.base = str(base)
        self.work_w = int(min(int(work_w), 2048))     # 解码 mip 宽度上限；全身 1024 足够，特写要 2048
        self.angles = []
        # angles 可覆盖角度表：给「半身特写镜头」用（base 指向那张特写图，只有 1 个角度）。
        # 条目：(名字, 绝对路径或相对 base 的文件名, 头部偏转, 'both'/'head'/'body')
        for name, fn, yaw, use in (angles if angles is not None else _ANGLE_FILES):
            if str(fn).startswith(MIR):
                p = MIR + (fn[len(MIR):] if os.path.isabs(fn[len(MIR):]) else os.path.join(self.base, fn[len(MIR):]))
            else:
                p = fn if os.path.isabs(str(fn)) else os.path.join(self.base, fn)
            chk = str(p)[len(MIR):] if _mirrored(p) else str(p)
            if os.path.exists(chk):
                self.angles.append((name, p, yaw, use))
        if not self.angles:
            raise FileNotFoundError(f'{self.base} 下没有 hero_*_cut.png')
        self.angles.sort(key=lambda a: a[2])
        self.front = [a for a in self.angles if a[0] == 'front'][0][1]
        self.G = _geom(self.front, self.work_w)
        self.W = _weights(self.front, self.work_w)
        self.joints = self.W['joints']
        w = self.W['w']
        tot = np.zeros((GH, GW), np.float32)
        for v in w.values():
            tot += v
        self._wn = {k: (v / np.maximum(tot, 1e-4)).astype(np.float32) for k, v in w.items()}
        self.head_box_u = (-0.132, 0.830, 0.132, 1.28)          # 头部补丁取图范围（单位空间）

    def warm(self):
        """预解码所有贴图 + 算几何（首帧不再有 300ms 抖动）。管线载入时调一次。"""
        for a in self.angles:
            _geom(a[1], self.work_w)
            _load(a[1], self.work_w)
        for fn in list(_KEY_FILES.values()) + list(_EXPR_FILES.values()):
            p = os.path.join(self.base, fn)
            if os.path.exists(p):
                _geom(p, self.work_w)
                _load(p, self.work_w)
        _look_import()
        return self

    # ------------------------------------------------------------ 布局仿射：图片像素 → 画面
    def _affine(self, path, dst, h, mode='body', zoom=1.0, sx=1.0):
        """mode='body'：脚底中点对齐；mode='head'：眼线对齐（转头/键帧/表情用）。"""
        g = _geom(path, self.work_w)
        hu = h / g['headtop_u']                      # 每单位像素（按该图自己的头顶比例）
        s = hu / g['H'] * float(zoom)
        if mode == 'body':
            ax, ay, tx_, ty_ = g['cx'], g['feet'], dst[0], dst[1]
        else:
            ax, ay, tx_, ty_ = g['eye'][0], g['eye_y'], dst[0], dst[1] - hu
        if sx == 1.0:
            return np.array([[s, 0, tx_ - s * ax], [0, s, ty_ - s * ay]], np.float32), s, hu
        # 水平挤压（绕锚点 ax，脸心/脚底中点不动）
        return np.array([[s * sx, 0, tx_ - s * sx * ax], [0, s, ty_ - s * ay]], np.float32), s * sx, hu

    def _angle_plan(self, yaw, squash=False, for_head=True):
        """yaw → [(path, weight, sx)]。

        只有**相邻角度很近**（<0.18）时才做交叉过渡；否则用最近的角度 + 水平余弦挤压
        （cos 投影比只看得出「更侧」），因为把 20° 的脸和 90° 的脸各半叠在一起 = 糊成双影。
        挤压围绕脸心做，face 位置不变。
        """
        arr = [a for a in self.angles if a[3] == 'both' or a[3] == ('head' if for_head else 'body')]
        if not arr:
            arr = self.angles
        yaws = [a[2] for a in arr]
        yaw = float(np.clip(yaw, yaws[0], yaws[-1]))
        d = [abs(yaw - y) for y in yaws]
        i = int(np.argmin(d))
        j = int(np.argmin([dd if k != i else 1e9 for k, dd in enumerate(d)]))
        if squash and d[i] + d[j] < 0.36:            # 两个角度足够近才叠，否则叠出来是双影
            t = d[i] / max(1e-6, d[i] + d[j])
            t = t * t * (3 - 2 * t)
            out = []
            if 1 - t > 1e-3:
                out.append((arr[i][1], 1 - t, 1.0))
            if t > 1e-3:
                out.append((arr[j][1], t, 1.0))
            return out
        sx = 1.0
        if squash:
            ca = math.cos(np.clip(abs(yaws[i]), 0, 1.45) * math.pi / 2)
            cb = math.cos(np.clip(abs(yaw), 0, 1.45) * math.pi / 2)
            sx = float(np.clip(cb / max(ca, 1e-3), 0.70, 1.0))
        return [(arr[i][1], 1.0, sx)]

    def _warp(self, path, M, box, src_rect=None):
        """按 M 把图（可只取 src_rect）画进 box；返回 (F,bh,bw,3),(A,bh,bw)。"""
        x0, y0, x1, y1 = box
        bw, bh = x1 - x0, y1 - y0
        F, A = _load(path, self.work_w)
        if src_rect is None:
            sx0, sy0, sx1, sy1 = 0, 0, F.shape[1], F.shape[0]
        else:
            sx0, sy0, sx1, sy1 = [int(round(v)) for v in src_rect]
            sx0, sy0 = max(0, sx0), max(0, sy0)
            sx1, sy1 = min(F.shape[1], sx1), min(F.shape[0], sy1)
        if sx1 <= sx0 or sy1 <= sy0:
            return np.zeros((bh, bw, 3), np.float32), np.zeros((bh, bw), np.float32)
        M2 = M.copy()
        M2[0, 2] += M[0, 0] * sx0 - x0          # 裁切原点补偿（M 是 src→dst，故是加）
        M2[1, 2] += M[1, 1] * sy0 - y0
        f = cv2.warpAffine(F[sy0:sy1, sx0:sx1], M2, (bw, bh), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT).astype(np.float32) * (1.0 / 255.0)
        a = cv2.warpAffine(A[sy0:sy1, sx0:sx1], M2, (bw, bh), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT).astype(np.float32) * (1.0 / 255.0)
        return f, a

    @staticmethod
    def _map_rect(M, rect):
        x0, y0, x1, y1 = rect
        pts = np.array([[x0, y0, 1], [x1, y0, 1], [x0, y1, 1], [x1, y1, 1]], np.float32)
        q = pts @ M.T                                  # (4,2)
        return (float(q[:, 0].min()), float(q[:, 1].min()), float(q[:, 0].max()), float(q[:, 1].max()))

    # ------------------------------------------------------------ 位移场
    def _disp(self, pose, box, hu, dst):
        x0, y0, x1, y1 = box
        bw, bh = x1 - x0, y1 - y0
        A = bone_affines(self.joints, pose)
        gx, gy = self.W['gx'], self.W['gy']
        du = np.zeros((GH, GW), np.float32)
        dv = np.zeros((GH, GW), np.float32)
        knee = max(float(np.clip(pose.get('knee', 0.0), -0.4, 0.4)), 0.0)
        for name in _ORDER:
            wn = self._wn[name]
            if not wn.any():
                continue
            if name == 'leg':                    # 腿：脚底不动，髋部随 knee 下沉
                dv += wn * (-0.10 * knee * np.clip(gy / HIP_U, 0, 1.2))
                continue
            M = A[name]
            px = M[0, 0] * gx + M[0, 1] * gy + M[0, 2]
            py = M[1, 0] * gx + M[1, 1] * gy + M[1, 2]
            du += wn * (px - gx)
            dv += wn * (py - gy)
        # 单位空间位移 → 画面像素（+v 向上 ⇒ 画面 y 减小）；map 用盒内局部坐标（accF 是盒内数组）
        du_px = cv2.resize(du * hu, (bw, bh), interpolation=cv2.INTER_LINEAR)
        dv_px = cv2.resize(-dv * hu, (bw, bh), interpolation=cv2.INTER_LINEAR)
        xs = np.arange(bw, dtype=np.float32)[None, :]
        ys = np.arange(bh, dtype=np.float32)[:, None]
        return (np.ascontiguousarray(xs - du_px, np.float32),
                np.ascontiguousarray(ys - dv_px, np.float32))

    # ------------------------------------------------------------ 表情补丁（几何对位）
    def _expr_patch(self, expr, dst, hu):
        """expr 特写 → 脸部补丁 (patch_F, patch_A, box)。失败返回 None。

        特写图和全身图之间的定位只用两个几何量（都从皮肤块实测，同一套规则）：
          脸宽 fw（皮肤块宽）、眼行 = 皮肤块顶 + 21%（实测标定）。
        只贴**脸**（眉到下巴 + 两侧颧骨），不换整颗头 —— 特写图本身头发被画框切掉，
        整头替换会在发际线留一圈残影，这是第一版的坑。
        """
        fn = _EXPR_FILES.get(expr)
        if not fn:
            return None
        path = os.path.join(self.base, fn)
        if not os.path.exists(path):
            return None
        g = _geom(path, self.work_w)
        if not g['bust']:
            return None
        F, A = _load(path, self.work_w)
        fx, eye_y = g['eye']
        fw, fh = g['facew'], g['faceh']
        s = (FACE_W_U * hu) / fw                       # 特写脸宽 → 全身脸宽
        # 特写里的脸框：横向 0.84 脸宽，纵向 眉上 0.30 脸框高 → 下巴下 0.04
        top = eye_y - 0.13 * fh          # 只取眉上一点（再往上就带进特写的头发，会在额头上留黑线）
        bot = eye_y + 0.35 * fh
        px0, px1 = fx - 0.42 * fw, fx + 0.42 * fw
        M = np.array([[s, 0, dst[0] - s * fx], [0, s, (dst[1] - hu) - s * eye_y]], np.float32)
        x0 = int(math.floor(M[0, 0] * px0 + M[0, 2])) - 2
        x1 = int(math.ceil(M[0, 0] * px1 + M[0, 2])) + 2
        y0 = int(math.floor(M[1, 1] * top + M[1, 2])) - 2
        y1 = int(math.ceil(M[1, 1] * bot + M[1, 2])) + 2
        box = (x0, y0, x1, y1)
        f, a = self._warp(path, M, box, (px0, top, px1, bot))
        bw, bh = x1 - x0, y1 - y0
        u = np.linspace(0, 1, bw, dtype=np.float32)[None, :]
        v = np.linspace(0, 1, bh, dtype=np.float32)[:, None]
        # 椭圆羽化：中心全不透明，边缘 25% 溶进底图的脸
        d = np.sqrt(((u - 0.5) / 0.5) ** 2 + ((v - 0.5) / 0.5) ** 2)
        fe = np.clip(1.0 - _sstep(0.72, 1.02, d), 0, 1)
        return f, a * fe, box, fe

    # ------------------------------------------------------------ 主入口
    def draw(self, fr, t, pose, dst=(960, 900), h=680, look=None, rim=None, grade=None,
             alpha=1.0, defocus=0.0, mblur=0.0, wrap=0.0, shade=None, keep_red=None):
        pose = dict(pose or {})
        Hpx, Wpx = fr.shape[:2]
        grade = dict(grade or dict(expo=0.66, sat=0.55, tint=(0.90, 0.96, 1.06), lift=0.0, gamma=1.25))
        if keep_red is not None:
            grade['keep_red'] = float(keep_red)
        rim = rim or dict(col=(0.62, 0.74, 1.0), amt=1.6, dir=(-0.8, -0.6))
        turn = float(np.clip(pose.get('head_turn', 0.0), -1.2, 1.2))
        # 身体朝向：默认**不换**（两张不同姿势的正身交叉 = 双影，见 report）；
        # 只有显式 body_turn 才换，或 head_turn 极大（>0.85）时按比例带一点 tq。
        if 'body_turn' in pose:
            bturn = float(np.clip(pose['body_turn'], -1.2, 1.6))
        else:
            bturn = 0.0
        hh = h * (1.0 + 0.004 * math.sin(2 * math.pi * t / 3.4))          # 呼吸
        # ---- 选层
        body_layers = self._angle_plan(bturn, squash=True, for_head=False)
        expr = pose.get('expr', 'calm')
        _, _, hu = self._affine(self.front, dst, hh, 'body')
        head_patch = self._expr_patch(expr, dst, hu) if expr != 'calm' else None
        head_layers = [] if head_patch is not None else self._angle_plan(turn, squash=True, for_head=True)
        # ---- 键帧
        keyw = 0.0
        kname = pose.get('key')
        kp = None
        if kname:
            kp = os.path.join(self.base, _KEY_FILES.get(kname, ''))
            if os.path.exists(kp):
                keyw = float(np.clip(pose.get('key_w', 1.0), 0, 1))
        # ---- 落点包围盒 = 各层源的 alpha 支撑 bbox 映射后并集
        bx0, by0, bx1, by1 = 1e9, 1e9, -1e9, -1e9
        for lay in list(body_layers) + list(head_layers):
            path, _w, _sx = lay[0], lay[1], lay[2]
            in_head = lay in head_layers
            M, _s, _hu = self._affine(path, dst, hh, 'head' if in_head else 'body', sx=_sx)
            r = self._map_rect(M, _geom(path, self.work_w)['bbox'])
            bx0, by0 = min(bx0, r[0]), min(by0, r[1])
            bx1, by1 = max(bx1, r[2]), max(by1, r[3])
        if head_patch is not None:
            bx0, by0 = min(bx0, head_patch[2][0]), min(by0, head_patch[2][1])
            bx1, by1 = max(bx1, head_patch[2][2]), max(by1, head_patch[2][3])
        if kp:
            gk0 = _geom(kp, self.work_w)
            M, _s, _hu = self._affine(kp, dst, hh, 'head' if gk0['bust'] else 'body',
                                      zoom=float(pose.get('key_zoom', 1.0)) if gk0['bust'] else 1.0)
            r = self._map_rect(M, gk0['bbox'])
            bx0, by0 = min(bx0, r[0]), min(by0, r[1])
            bx1, by1 = max(bx1, r[2]), max(by1, r[3])
        mb_abs = (abs(mblur[0]) + abs(mblur[1])) if isinstance(mblur, (tuple, list)) else abs(mblur or 0)
        pad = 18.0 + mb_abs + (3.2 * defocus if defocus > 0.3 else 0.0) + (14 if wrap else 0)
        X0, Y0 = int(math.floor(max(0, bx0 - pad))), int(math.floor(max(0, by0 - pad)))
        X1, Y1 = int(math.ceil(min(Wpx, bx1 + pad))), int(math.ceil(min(Hpx, by1 + pad)))
        if X1 - X0 < 8 or Y1 - Y0 < 8:
            return fr, np.zeros((Hpx, Wpx), np.float32)
        box = (X0, Y0, X1, Y1)
        bw, bh = X1 - X0, Y1 - Y0
        # ---- 身体层
        accF = np.zeros((bh, bw, 3), np.float32)
        accA = np.zeros((bh, bw), np.float32)
        for path, w, sxv in body_layers:
            M, _s, _hu = self._affine(path, dst, hh, 'body', sx=sxv)
            f, a = self._warp(path, M, box, _geom(path, self.work_w)['bbox'])
            accF += (f * a[..., None]) * w
            accA += a * w
        accA = np.clip(accA, 0, 1)
        accF = accF / np.maximum(accA, 1e-4)[..., None]
        # ---- 头部层（多角度替换）：先按「头框软窗」把旧头擦掉，再把新头叠上去
        #      顺序很重要：先 erase 再加补丁，否则擦除会把刚贴上去的新头也擦掉。
        hx0, hy0, hx1, hy1 = self.head_box_u
        fb = None
        if head_layers:                       # 只有「转头」才需要擦掉旧头；表情补丁只盖脸，不擦
            # 擦除窗 = 实测头 mask（网格级，含头发）重采样到画布；再乘一个温和的头框窗
            ghm = self.W['headmask']
            dgx = (GX1 - GX0) / (GW - 1)
            dgy = (GY1 - GY0) / (GH - 1)
            uu = ((np.arange(X0, X1, dtype=np.float32) - dst[0]) / hu - GX0) / dgx
            vv = ((dst[1] - np.arange(Y0, Y1, dtype=np.float32)) / hu - GY0) / dgy
            hm = cv2.remap(ghm, np.ascontiguousarray(np.repeat(uu[None, :], bh, 0), np.float32),
                           np.ascontiguousarray(np.repeat(vv[:, None], bw, 1), np.float32),
                           cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            fb = np.clip(hm, 0, 1).astype(np.float32)
            accF = accF * (1 - fb[..., None])
            accA = np.clip(accA * (1 - fb), 0, 1)
        if head_layers:
            for path, w, sxv in head_layers:
                M, _s, _hu = self._affine(path, dst, hh, 'head', sx=sxv)
                sx0 = (dst[0] + hx0 * hu - M[0, 2]) / M[0, 0]
                sx1 = (dst[0] + hx1 * hu - M[0, 2]) / M[0, 0]
                sy0 = ((dst[1] - hy1 * hu) - M[1, 2]) / M[1, 1]
                sy1 = ((dst[1] - hy0 * hu) - M[1, 2]) / M[1, 1]
                f, a = self._warp(path, M, box, (sx0, sy0, sx1, sy1))
                # 补丁边缘羽化：按**单位空间**坐标做（底边在颈下 0.855→0.945 之间溶进衣领，
                # 侧边略收），这样不同角度的头都以同一套解剖位置收边，不会出现「双衣领」。
                uu2 = ((np.arange(X0, X1, dtype=np.float32) - dst[0]) / hu)[None, :]
                vv2 = ((dst[1] - np.arange(Y0, Y1, dtype=np.float32)) / hu)[:, None]
                fw = (_sstep(0.855, 0.948, vv2) *
                      (1.0 - 0.55 * np.clip((np.abs(uu2) - 0.100) / 0.032, 0, 1)) *
                      (1.0 - 0.30 * np.clip((vv2 - 1.235) / 0.045, 0, 1))).astype(np.float32)
                pa = np.clip(a * fw * w, 0, 1)
                accF = accF * (1 - pa[..., None]) + f * pa[..., None]
                accA = np.clip(accA * (1 - pa) + pa, 0, 1)
        elif head_patch is not None:
            f, a, pbox, feather = head_patch
            px0, py0 = pbox[0] - X0, pbox[1] - Y0
            fx0, fy0 = max(0, -px0), max(0, -py0)
            fx1, fy1 = min(f.shape[1], bw - px0), min(f.shape[0], bh - py0)
            if fx1 > fx0 and fy1 > fy0:
                sub = (slice(py0 + fy0, py0 + fy1), slice(px0 + fx0, px0 + fx1))
                fa = a[fy0:fy1, fx0:fx1]
                ff = f[fy0:fy1, fx0:fx1].copy()
                m = (feather[fy0:fy1, fx0:fx1] > 0.6) & (fa > 0.9)
                if m.sum() > 120:
                    # 与原脸的**低频**差值修正（整块均值差只修正色调偏移；模糊成低频后连
                    # 「补丁边缘一圈亮/暗线」也一起抹平，比全局常数好很多）
                    d = (accF[sub] - ff) * m[..., None]
                    wsum = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 6)
                    d = cv2.GaussianBlur(d, (0, 0), 6) / np.maximum(wsum, 1e-3)[..., None]
                    ff = np.clip(ff + np.clip(d, -0.12, 0.12), 0, 1)
                accF[sub] = accF[sub] * (1 - fa[..., None]) + ff * fa[..., None]
                accA[sub] = np.clip(accA[sub] * (1 - fa) + fa, 0, 1)
        # ---- 整姿势键帧
        if keyw > 1e-3:
            gk = _geom(kp, self.work_w)
            # 半身键帧（draw）：按脸对齐 + key_zoom 放大（默认 1 = 与全身脸同大，很小；
            # 当「特写插镜」用时传 key_zoom≈4 让胸像铺满画面）
            Mk, _sk, _hu = self._affine(kp, dst, hh, 'head' if gk['bust'] else 'body',
                                        zoom=float(pose.get('key_zoom', 1.0)) if gk['bust'] else 1.0)
            fk, ak = self._warp(kp, Mk, box, gk['bbox'])
            accF = accF * (1 - keyw) + fk * keyw
            accA = np.clip(accA * (1 - keyw) + ak * keyw, 0, 1)
        # ---- 蒙皮变形（一次 remap）
        dscale = 1.0 - 0.85 * keyw
        if dscale > 0.02:
            mx, my = self._disp(pose, box, hu, dst)
            if dscale < 0.98:                      # 键帧占比越高，骨架形变越弱（盒内局部坐标！）
                xs = np.arange(bw, dtype=np.float32)[None, :]
                ys = np.arange(bh, dtype=np.float32)[:, None]
                mx = xs + (mx - xs) * dscale
                my = ys + (my - ys) * dscale
            preA = accA.copy()
            accF = cv2.remap(accF, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            accA = cv2.remap(accA, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            accF, accA = _fill_holes(accF, accA, preA)
        if shade:                                   # 屏幕空间主光衰减（与 sprite.py 同义）
            xs2 = np.arange(X0, X1, dtype=np.float32)[None, :]
            ys2 = np.arange(Y0, Y1, dtype=np.float32)[:, None]
            r2 = (np.clip((xs2 - shade[0]) / (shade[1] - shade[0]), 0, 1) * shade[2] +
                  np.clip((ys2 - shade[3]) / (Hpx - shade[3]), 0, 1) * shade[4])
            accF = accF * (1 - r2)[..., None]
        # ---- 调色（与 sprite.py._front 同一套公式）+ rim + look
        lum = (accF * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
        _lk, red_fn = _look_import()
        redmask = red_fn(accF)[..., None] * float(grade.get('keep_red', 1.0))
        sat = grade['sat'] * (1 - redmask) + 1.25 * redmask
        tint = np.array(grade['tint'], np.float32) * (1 - redmask) + \
            np.array([1.08, 0.96, 0.96], np.float32) * redmask
        accF = (np.clip(lum + (accF - lum) * sat, 0, 1) ** grade.get('gamma', 1.0) *
                grade['expo'] * tint + grade['lift'])
        ring = accA - cv2.erode(accA, np.ones((5, 5), np.uint8))
        R = cv2.GaussianBlur(np.clip(ring, 0, 1), (0, 0), 1.5)
        gxs = cv2.Sobel(accA, cv2.CV_32F, 1, 0, ksize=5)
        gys = cv2.Sobel(accA, cv2.CV_32F, 0, 1, ksize=5)
        n = np.sqrt(gxs * gxs + gys * gys) + 1e-4
        facing = np.clip(-(gxs * rim['dir'][0] + gys * rim['dir'][1]) / n, 0, 1)
        rimm = (R * (0.25 + 0.75 * facing))[..., None] * accA[..., None]
        accF = accF + rimm * np.array(rim['col'], np.float32) * rim['amt'] * 0.25
        if look:
            accF, accA = _lk(accF, accA, rimm, rim, redmask, look)
        # ---- 模糊 / 淡出
        if mblur is not None and (mblur if not isinstance(mblur, (tuple, list)) else (abs(mblur[0]) + abs(mblur[1]))):
            # mblur：标量（斜向）或 (dx,dy) 元组（与 sprite.py 的 draw 同义）
            if isinstance(mblur, (tuple, list)):
                mbx, mby = float(mblur[0]), float(mblur[1])
            else:
                mbx, mby = float(mblur), float(mblur) * 0.4
            L = int(max(2, max(abs(mbx), abs(mby)) * 0.5))
            k = np.zeros((2 * L + 1, 2 * L + 1), np.float32)
            cv2.line(k, (L, L), (L + int(mbx), L + int(mby)), 1.0, 1)
            k /= max(k.sum(), 1e-6)
            accF = cv2.filter2D(accF * accA[..., None], -1, k)
            accA = cv2.filter2D(accA, -1, k)
            accF = accF / np.clip(accA[..., None], 1e-3, None)
        if defocus > 0.3:
            accF = cv2.GaussianBlur(accF * accA[..., None], (0, 0), defocus)
            accA = cv2.GaussianBlur(accA, (0, 0), defocus)
            accF = accF / np.clip(accA[..., None], 1e-3, None)
        accA = np.clip(accA * alpha, 0, 1)
        if wrap > 0:                                        # 光包裹（同 sprite.py 的 wrap 思路）
            m = 40
            y0m, y1m, x0m, x1m = Y0 - m, Y1 + m, X0 - m, X1 + m
            oy0, oy1 = max(0, y0m), min(Hpx, y1m)
            ox0, ox1 = max(0, x0m), min(Wpx, x1m)
            crop = fr[oy0:oy1, ox0:ox1]
            pt, pb, pl, pr = oy0 - y0m, y1m - oy1, ox0 - x0m, x1m - ox1
            if pt or pb or pl or pr:
                crop = cv2.copyMakeBorder(crop, pt, pb, pl, pr, cv2.BORDER_REFLECT_101)
            bgb = cv2.GaussianBlur(crop, (0, 0), 18)[m:m + bh, m:m + bw]
            inner = cv2.GaussianBlur(accA, (0, 0), 10)
            accF = accF + bgb * (accA * np.clip(1 - inner, 0, 1) * 2.0)[..., None] * wrap
        # ---- 合成
        a3 = accA[..., None]
        fr[Y0:Y1, X0:X1] = fr[Y0:Y1, X0:X1] * (1 - a3) + accF * a3
        amap = np.zeros((Hpx, Wpx), np.float32)
        amap[Y0:Y1, X0:X1] = accA
        return fr, amap


def rig(**kw):
    return PoseRig(**kw)
