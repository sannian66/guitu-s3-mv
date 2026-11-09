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


def _sstep(a, b, x):
    x = np.clip((x - a) / (b - a), 0, 1)
    return x * x * (3 - 2 * x)


def _load(path, width=1024):
    """解码 + 缩放 mip（缓存）：返回 (F float32 hxwx3, A float32 hxw)。"""
    key = (os.path.abspath(str(path)), int(width))
    got = _RAW.get(key)
    if got is not None:
        return got
    im = Image.open(str(path)).convert('RGBA')
    h = max(1, round(im.size[1] * width / im.size[0]))
    a = np.asarray(im.resize((width, h), Image.LANCZOS)).astype(np.float32) / 255.0
    got = (np.ascontiguousarray(a[..., :3]), np.ascontiguousarray(a[..., 3]))
    _RAW[key] = got
    return got


def _skin_mask(F, A):
    r, g, b = F[..., 0], F[..., 1], F[..., 2]
    lum = F.mean(-1)
    m = ((r > g + 0.02) & (g > b - 0.01) & (r > b + 0.04) &
         (lum > 0.16) & (lum < 0.92) & (A > 0.5)).astype(np.uint8)
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def _geom(path, width=1024):
    """实测一张立绘的骨架单位空间参数（缓存）。"""
    key = (os.path.abspath(str(path)), int(width))
    got = _GEOM.get(key)
    if got is not None:
        return got
    F, A = _load(path, width)
    hh, ww = A.shape
    m = A > 0.5
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
    if order:
        i0 = order[0]
        x, y, w_, h_, ar = st[i0]
        if ar > 0.20 * span * ww:                       # 半身特写：整幅都是人
            bust = True
        face = (float(cen[i0][0]), float(y), float(w_), float(h_))   # (fx, 脸框顶, 脸宽, 脸框高)
    else:
        face = (cx, top + 0.06 * span, 0.06 * span, 0.08 * span)
    fx, ftop, fw, fh = face
    eye = ftop + 0.21 * fh                              # 眉毛/眼 行（实测：皮肤块顶 + 21%）
    if bust:
        H = fw / FACE_W_U                               # 半身：用脸宽定尺度（同人物 FACE_W_U 恒定）
        feet = eye + H
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
    got = dict(H=H, cx=cx, eye=(fx, eye), eye_y=eye, facew=fw, feet=feet, top=top, bust=bust,
               headtop_u=(feet - top) / H, head=headbox, hands=hands, sword=sword,
               bbox=bbox, w=ww, h=hh)
    _GEOM[key] = got
    return got


# ---------------------------------------------------------------- 权重场（单位空间粗网格）
def _capsule(gu, gv, p0, p1, r, sharp=2.0):
    ax, ay = p0
    dx, dy = p1[0] - ax, p1[1] - ay
    L2 = dx * dx + dy * dy + 1e-9
    t = np.clip(((gu - ax) * dx + (gv - ay) * dy) / L2, 0, 1)
    d = np.sqrt((gu - (ax + t * dx)) ** 2 + (gv - (ay + t * dy)) ** 2)
    return np.exp(-(d / r) ** 2 * sharp), d


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
    dt = cv2.distanceTransform((A > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    thin_img = (np.clip(1.0 - dt / (0.020 * H), 0, 1) ** 1.5 * (A > 0.4)).astype(np.float32)
    map_x = np.ascontiguousarray(np.repeat(cx + gu[:1] * H, GH, 0), np.float32)
    map_y = np.ascontiguousarray(np.repeat(feet - gv[:, :1] * H, GW, 1), np.float32)
    A_g = cv2.remap(A, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
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
    # 头/颈：头心各向异性高斯 + 头发细丝（发髻、披发跟着头）
    w['head'] = (np.exp(-((gu - 0.0) / 0.086) ** 2 - ((gv - HEAD_C_U) / 0.115) ** 2) +
                 0.9 * thin * _sstep(0.78, 0.88, gv)).astype(np.float32)
    w['spine'] = (_sstep(HIP_U - 0.05, HIP_U + 0.05, gv) * _sstep(1.00, 0.93, gv)).astype(np.float32)
    w['skirt'] = (_sstep(HIP_U + 0.03, HIP_U - 0.09, gv) * _sstep(-0.02, 0.07, gv) * 0.85).astype(np.float32)
    w['leg'] = (_sstep(HIP_U + 0.03, HIP_U - 0.05, gv) * _sstep(-0.05, 0.04, gv)).astype(np.float32)
    w['sh_r'] = (_capsule(gu, gv, sh_r, el_r, 0.055)[0] * _sstep(0.98, 0.90, gv)).astype(np.float32)
    w['el_r'] = (_capsule(gu, gv, el_r, wr, 0.048)[0] * _sstep(0.98, 0.90, gv)).astype(np.float32)
    w['sh_l'] = (_capsule(gu, gv, sh_l, el_l, 0.055)[0] * _sstep(0.98, 0.90, gv)).astype(np.float32)
    w['el_l'] = (_capsule(gu, gv, el_l, wl, 0.048)[0] * _sstep(0.98, 0.90, gv)).astype(np.float32)
    w['ha_r'] = _capsule(gu, gv, wr, wr, 0.045)[0].astype(np.float32)
    w['ha_l'] = _capsule(gu, gv, wl, wl, 0.045)[0].astype(np.float32)
    sw = np.zeros_like(gu, np.float32)
    if g['sword'] is not None:
        t0, t1 = g['sword']
        p0 = ((t0[0] - cx) / H, (feet - t0[1]) / H)
        p1 = ((t1[0] - cx) / H, (feet - t1[1]) / H)
        _, d = _capsule(gu, gv, p0, p1, 0.03)
        sw = (np.exp(-(d / 0.026) ** 2) * np.clip(thin * 2.2 + 0.15, 0, 1)).astype(np.float32)
        sw = np.maximum(sw, _capsule(gu, gv, p0, p0, 0.05)[0] * 0.9)     # 刀柄跟手
    w['sword'] = sw
    w['root'] = np.full_like(gu, 0.05, np.float32)                       # 兜底权重（防归一化除零）
    out = dict(gx=gu, gy=gv, w=w, thin=thin, mask=mask_g,
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
_ANGLE_FILES = [('front', 'hero_front_cut.png', 0.00),
                ('tq_r', 'hero_tq_r_cut.png', 0.55),
                ('side_r', 'hero_side_r_cut.png', 1.00),
                ('tq_l', 'hero_view_tq_l_cut.png', -0.55),
                ('back', 'hero_back_cut.png', 1.60)]
_EXPR_FILES = {'calm': 'hero_expr_calm_cut.png', 'angry': 'hero_expr_angry_cut.png',
               'smirk': 'hero_expr_smirk_cut.png', 'look': 'hero_expr_look_cut.png'}
_KEY_FILES = {'raise': 'hero_pose_raise_cut.png', 'slash': 'hero_pose_slash_cut.png',
              'draw': 'hero_pose_draw_cut.png'}


class PoseRig:
    """生图立绘 puppet：正面 + 转头 + 举刀/劈砍 + 表情。"""

    def __init__(self, base='assets/gen/char', work_w=2048):
        self.base = str(base)
        self.work_w = int(min(int(work_w), 1280))     # 解码 mip 宽度上限（1024 已足够，2048 只更慢）
        self.angles = []
        for name, fn, yaw in _ANGLE_FILES:
            p = os.path.join(self.base, fn)
            if os.path.exists(p):
                self.angles.append((name, p, yaw))
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
        self.head_box_u = (-0.125, 0.760, 0.125, 1.26)          # 头部补丁范围（单位空间）

    # ------------------------------------------------------------ 布局仿射：图片像素 → 画面
    def _affine(self, path, dst, h, mode='body'):
        """mode='body'：脚底中点对齐；mode='head'：眼线对齐（转头/键帧/表情用）。"""
        g = _geom(path, self.work_w)
        hu = h / g['headtop_u']                      # 每单位像素（按该图自己的头顶比例）
        s = hu / g['H']
        if mode == 'body':
            ax, ay, tx_, ty_ = g['cx'], g['feet'], dst[0], dst[1]
        else:
            ax, ay, tx_, ty_ = g['eye'][0], g['eye_y'], dst[0], dst[1] - hu
        return np.array([[s, 0, tx_ - s * ax], [0, s, ty_ - s * ay]], np.float32), s, hu

    def _angle_plan(self, yaw):
        """yaw → [(path, weight)]，相邻角度 smoothstep 过渡。"""
        arr = self.angles
        yaws = [a[2] for a in arr]
        yaw = float(np.clip(yaw, yaws[0], yaws[-1]))
        for i in range(len(arr) - 1):
            if yaws[i] <= yaw <= yaws[i + 1]:
                t = (yaw - yaws[i]) / max(1e-6, yaws[i + 1] - yaws[i])
                t = t * t * (3 - 2 * t)
                out = []
                if 1 - t > 1e-3:
                    out.append((arr[i][1], 1 - t))
                if t > 1e-3:
                    out.append((arr[i + 1][1], t))
                return out
        return [(arr[-1][1], 1.0)]

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
        M2[0, 2] -= x0 + M[0, 0] * sx0
        M2[1, 2] -= y0 + M[1, 1] * sy0
        f = cv2.warpAffine(F[sy0:sy1, sx0:sx1], M2, (bw, bh), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT)
        a = cv2.warpAffine(A[sy0:sy1, sx0:sx1], M2, (bw, bh), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT)
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
        """expr 特写 → (patch_F, patch_A, box, feather)；失败返回 None。"""
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
        fw = g['facew']
        s = (FACE_W_U * hu) / fw                       # 特写脸宽 → 全身脸宽
        # 特写里取到「头发+脸」的一块，落到全身图的眼线位置
        px0, px1 = fx - 1.30 * fw, fx + 1.30 * fw
        py0, py1 = eye_y - 1.85 * fw, eye_y + 0.95 * fw
        M = np.array([[s, 0, dst[0] - s * fx], [0, s, (dst[1] - hu) - s * eye_y]], np.float32)
        x0, y0 = int(math.floor(M[0, 0] * px0 + M[0, 2])) - 2, int(math.floor(M[1, 1] * py0 + M[1, 2])) - 2
        x1, y1 = int(math.ceil(M[0, 0] * px1 + M[0, 2])) + 2, int(math.ceil(M[1, 1] * py1 + M[1, 2])) + 2
        box = (x0, y0, x1, y1)
        f, a = self._warp(path, M, box, (px0, py0, px1, py1))
        bw, bh = x1 - x0, y1 - y0
        u = np.linspace(0, 1, bw, dtype=np.float32)[None, :]
        v = np.linspace(0, 1, bh, dtype=np.float32)[:, None]
        feather = _sstep(0.0, 0.22, u) * _sstep(1.0, 0.78, u) * _sstep(0.0, 0.16, v) * _sstep(1.0, 0.66, v)
        return f, a * feather, box, feather

    # ------------------------------------------------------------ 主入口
    def draw(self, fr, t, pose, dst=(960, 900), h=680, look=None, rim=None, grade=None,
             alpha=1.0, defocus=0.0, mblur=0.0, wrap=0.0):
        pose = dict(pose or {})
        Hpx, Wpx = fr.shape[:2]
        grade = grade or dict(expo=0.66, sat=0.55, tint=(0.90, 0.96, 1.06), lift=0.0, gamma=1.25)
        rim = rim or dict(col=(0.62, 0.74, 1.0), amt=1.6, dir=(-0.8, -0.6))
        turn = float(np.clip(pose.get('head_turn', 0.0), -1.2, 1.2))
        # 身体朝向：默认**不换**（两张不同姿势的正身交叉 = 双影，见 report）；
        # 只有显式 body_turn 才换，或 head_turn 极大（>0.85）时按比例带一点 tq。
        if 'body_turn' in pose:
            bturn = float(np.clip(pose['body_turn'], -1.2, 1.6))
        else:
            at = abs(turn)
            bturn = 0.0 if at < 0.85 else math.copysign((at - 0.85) * 2.2, turn)
        hh = h * (1.0 + 0.004 * math.sin(2 * math.pi * t / 3.4))          # 呼吸
        # ---- 选层
        body_layers = self._angle_plan(bturn)
        expr = pose.get('expr', 'calm')
        _, _, hu = self._affine(self.front, dst, hh, 'body')
        head_patch = self._expr_patch(expr, dst, hu) if expr != 'calm' else None
        head_layers = [] if head_patch is not None else self._angle_plan(turn)
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
        for path, _w in body_layers + head_layers:
            M, _s, _hu = self._affine(path, dst, hh, 'head' if (path, _w) in head_layers else 'body')
            r = self._map_rect(M, _geom(path, self.work_w)['bbox'])
            bx0, by0 = min(bx0, r[0]), min(by0, r[1])
            bx1, by1 = max(bx1, r[2]), max(by1, r[3])
        if head_patch is not None:
            bx0, by0 = min(bx0, head_patch[2][0]), min(by0, head_patch[2][1])
            bx1, by1 = max(bx1, head_patch[2][2]), max(by1, head_patch[2][3])
        if kp:
            M, _s, _hu = self._affine(kp, dst, hh, 'body')
            r = self._map_rect(M, _geom(kp, self.work_w)['bbox'])
            bx0, by0 = min(bx0, r[0]), min(by0, r[1])
            bx1, by1 = max(bx1, r[2]), max(by1, r[3])
        pad = 18.0 + abs(mblur) + (3.2 * defocus if defocus > 0.3 else 0.0) + (14 if wrap else 0)
        X0, Y0 = int(math.floor(max(0, bx0 - pad))), int(math.floor(max(0, by0 - pad)))
        X1, Y1 = int(math.ceil(min(Wpx, bx1 + pad))), int(math.ceil(min(Hpx, by1 + pad)))
        if X1 - X0 < 8 or Y1 - Y0 < 8:
            return fr, np.zeros((Hpx, Wpx), np.float32)
        box = (X0, Y0, X1, Y1)
        bw, bh = X1 - X0, Y1 - Y0
        # ---- 身体层
        accF = np.zeros((bh, bw, 3), np.float32)
        accA = np.zeros((bh, bw), np.float32)
        for path, w in body_layers:
            M, _s, _hu = self._affine(path, dst, hh, 'body')
            f, a = self._warp(path, M, box, _geom(path, self.work_w)['bbox'])
            accF += (f * a[..., None]) * w
            accA += a * w
        accA = np.clip(accA, 0, 1)
        accF = accF / np.maximum(accA, 1e-4)[..., None]
        # ---- 头部层（多角度替换 + 头框软擦除）
        erase = np.zeros((bh, bw), np.float32)
        hx0, hy0, hx1, hy1 = self.head_box_u
        if head_layers:
            uu = ((np.arange(X0, X1, dtype=np.float32) - dst[0]) / hu)[None, :]
            vv = ((dst[1] - np.arange(Y0, Y1, dtype=np.float32)) / hu)[:, None]
            fb = (_sstep(hx0, hx0 + 0.040, uu) * _sstep(hx1, hx1 - 0.040, uu) *
                  _sstep(hy0, hy0 + 0.090, vv) * _sstep(hy1, hy1 - 0.020, vv))
            for path, w in head_layers:
                M, _s, _hu = self._affine(path, dst, hh, 'head')
                # 头框 → 源像素
                sx0 = (dst[0] + hx0 * hu - M[0, 2]) / M[0, 0]
                sx1 = (dst[0] + hx1 * hu - M[0, 2]) / M[0, 0]
                sy0 = ((dst[1] - hy1 * hu) - M[1, 2]) / M[1, 1]
                sy1 = ((dst[1] - hy0 * hu) - M[1, 2]) / M[1, 1]
                f, a = self._warp(path, M, box, (sx0, sy0, sx1, sy1))
                k = w * fb
                accF = accF * (1 - k[..., None]) + (f * a[..., None]) * w
                accA = np.clip(accA * (1 - k) + a * w, 0, 1)
            erase = fb
        elif head_patch is not None:
            f, a, pbox, feather = head_patch
            px0, py0 = pbox[0] - X0, pbox[1] - Y0
            fx0, fy0 = max(0, -px0), max(0, -py0)
            fx1 = min(f.shape[1], bw - px0)
            fy1 = min(f.shape[0], bh - py0)
            if fx1 > fx0 and fy1 > fy0:
                sub = (slice(py0 + fy0, py0 + fy1), slice(px0 + fx0, px0 + fx1))
                fa = a[fy0:fy1, fx0:fx1]
                ff = f[fy0:fy1, fx0:fx1].copy()
                m = (feather[fy0:fy1, fx0:fx1] > 0.6) & (fa > 0.9)
                if m.sum() > 120:                        # 与原脸的均值差修正
                    d = accF[sub][m].mean(0) - ff[m].mean(0)
                    ff = np.clip(ff + np.clip(d, -0.12, 0.12) * feather[fy0:fy1, fx0:fx1][..., None], 0, 1)
                accF[sub] = accF[sub] * (1 - fa[..., None]) + ff * fa[..., None]
                accA[sub] = np.clip(accA[sub] * (1 - fa) + fa, 0, 1)
        if erase.any():
            accF = accF * (1 - erase[..., None])
            accA = np.clip(accA * (1 - erase), 0, 1)
        # ---- 整姿势键帧
        if keyw > 1e-3:
            gk = _geom(kp, self.work_w)
            Mk, _sk, _hu = self._affine(kp, dst, hh, 'head' if gk['bust'] else 'body')
            fk, ak = self._warp(kp, Mk, box, gk['bbox'])
            accF = accF * (1 - keyw) + fk * keyw
            accA = np.clip(accA * (1 - keyw) + ak * keyw, 0, 1)
        # ---- 蒙皮变形（一次 remap）
        dscale = 1.0 - 0.85 * keyw
        if dscale > 0.02:
            mx, my = self._disp(pose, box, hu, dst)
            if dscale < 0.98:
                xs = np.arange(X0, X1, dtype=np.float32)[None, :]
                ys = np.arange(Y0, Y1, dtype=np.float32)[:, None]
                mx = xs + (mx - xs) * dscale
                my = ys + (my - ys) * dscale
            accF = cv2.remap(accF, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            accA = cv2.remap(accA, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
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
        if mblur:
            L = int(max(2, abs(mblur) * 0.5))
            k = np.zeros((2 * L + 1, 2 * L + 1), np.float32)
            cv2.line(k, (L, L), (L + int(mblur), L + int(mblur * 0.4)), 1.0, 1)
            k /= max(k.sum(), 1e-6)
            accF = cv2.filter2D(accF * accA[..., None], -1, k)
            accA = cv2.filter2D(accA, -1, k)
            accF = accF / np.clip(accA[..., None], 1e-3, None)
        if defocus > 0.3:
            accF = cv2.GaussianBlur(accF * accA[..., None], (0, 0), defocus)
            accA = cv2.GaussianBlur(accA, (0, 0), defocus)
            accF = accF / np.clip(accA[..., None], 1e-3, None)
        accA = np.clip(accA * alpha, 0, 1)
        if wrap > 0:                                        # 光包裹（同 sprite.py 的 wrap）
            bgb = cv2.GaussianBlur(fr[max(0, Y0 - 40):min(Hpx, Y1 + 40),
                                      max(0, X0 - 40):min(Wpx, X1 + 40)], (0, 0), 18)
            oy, ox = max(0, Y0 - 40), max(0, X0 - 40)
            h2, w2 = bgb.shape[:2]
            my0, mx0 = Y0 - oy, X0 - ox
            bgb = cv2.resize(bgb, (bw, bh), interpolation=cv2.INTER_LINEAR) if bgb.shape[:2] != (bh, bw) else bgb
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
