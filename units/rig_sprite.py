"""units/rig_sprite.py — 生图立绘 puppet（2026-11-09 19:35 **收窄版**）

用户 19:2x 拍板：**蒙皮/骨架变形这条路砍掉**（二维单张立绘没有"手臂底下的像素"，硬转出来的
只有"看起来像坏掉的图"：腋下淤积、双影、转头处横向黑带）。本模块只保留三种干净能力，
其余一律 `ValueError` 挡掉，防止以后有人误用。

唯一入口
--------
    rig = PoseRig(base='assets/gen/char', work_w=2048).warm()
    fr, a = rig.play(fr, t, key, dst=(960, 900), h=680,
                     angle='front', angle_from=None, mix=1.0,
                     expr=None, mblur=0.0, alpha=1.0, defocus=0.0, wrap=0.0,
                     grade=None, rim=None, look=None, shade=None, keep_red=None)

三种能力（只有这三种）
----------------------
1. **整姿势键帧替换** `key ∈ {'idle','raise','slash','draw'}`
   直接把整张姿势图按「脚底中点 + 身高」摆进去，不做任何网格变形。
   * `idle`  = 正面 A-pose（angles/gen 里的角度图）
   * `raise` = 横刀举过头（hero_pose_raise_cut.png）
   * `slash` = 下劈中段（hero_pose_slash_cut.png）
   * `draw`  = 半身拔刀（hero_pose_draw_cut.png，自动按脸对齐 = 特写插镜）
   换姿势**只在切点做**；需要过渡就 ≤2 帧交叉 + `mblur ≥ 7`（模糊盖住叠影），
   **不允许「半个姿势」**（`key_w` 之类已删除）。

2. **表情脸部贴片** `expr ∈ {'angry','smirk'}`
   把特写图的脸（眉→下巴）按脸宽/眼行归一化后贴到头部区域，椭圆羽化 + 低频差值修正。
   **静态**：一次贴好，镜内不做渐变（不允许中途变脸）。只允许配 `key='idle'`、`angle_from=None`。
   `calm`/`look` 不提供（`look` 是 3/4 侧脸，和正面图对不上，实测有黑带残影）。

3. **角度交叉溶解** `angle` + `angle_from` + `mix`
   `angle,angle_from ∈ {'front','tq_r','tq_r45','side_r'}`：两张图**各按自己的脚底/眼线摆好直接叠**
   （不做任何几何变形），只在硬切那一两帧用，观众读到的是「切到新机位」。
   `mix=1.0`（默认，无 angle_from）= 单纯换角度。

已废弃（原因见 out/rig_test/report.md「已废弃」一节）
----------------------------------------------------
`head_turn`（角度挤压）/`head_pitch`/`lean`/`twist`/`arm_r`/`arm_l`/`elbow_r`/`elbow_l`/
`knee`/`sword`/`body_turn`/`key_w`/`key_zoom` → 传进来直接 `ValueError`。

坐标约定
--------
* `dst` = 脚底中点的画面像素；`h` = 人物总高（脚底 → 头顶发梢）像素。
* 单位空间只用于内部摆放：y=0 脚底、y=1 眼线、y≈1.11 头顶，1 单位 = 眼线→脚底。
* 颜色：显示空间 float32 0..1；返回 `(fr, alpha_map)`；`grade/rim/look` 复用 `units/sprite.py`。
"""
import math, os, sys
import numpy as np
import cv2
from PIL import Image

# ---------------------------------------------------------------- 复用 sprite.py 的 look / red_mask
_LOOK_FN = None
_RED_FN = None


def _look_import():
    global _LOOK_FN, _RED_FN
    if _LOOK_FN is not None:
        return _LOOK_FN, _RED_FN
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
    from units.sprite import _look, red_mask          # noqa: E402
    _LOOK_FN, _RED_FN = _look, red_mask
    return _LOOK_FN, _RED_FN


FACE_W_U = 0.065           # 脸宽（单位空间）；只用来说明「特写脸 → 全身脸」的缩放
_RAW = {}
_GEOM = {}


def _sstep(a, b, x):
    x = np.clip((x - a) / (b - a), 0, 1)
    return x * x * (3 - 2 * x)


def _load(path, width=2048):
    """解码 + 缩放 mip（uint8 缓存，省内存）：返回 (F uint8 hxwx3, A uint8 hxw)。"""
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
    r, g, b = [F[..., i].astype(np.float32) / 255.0 for i in range(3)]
    lum = (r + g + b) / 3.0
    m = ((r > g + 0.02) & (g > b - 0.01) & (r > b + 0.04) &
         (lum > 0.16) & (lum < 0.92) & (A > 127)).astype(np.uint8)
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def _geom(path, width=2048):
    """实测一张立绘的摆放参数（缓存）。

    返回：H（1 单位 = 眼行→脚底的像素）、eye=(x,y)、facew/faceh（皮肤块宽/高）、
          feet、top、cx（身体中线）、headtop_u（头顶/单位）、bust、bbox。
    """
    key = (os.path.abspath(str(path)), int(width))
    got = _GEOM.get(key)
    if got is not None:
        return got
    # 测量固定在 1024 宽：皮肤分割的连通块结果与解码宽度有关（2048 会碎成小块、最大的块可能
    # 只是脸的一块碎片 → 眼睛位置/脸宽全错）。量完再按比例换算到目标解码宽度。
    MW = 1024
    F, A = _load(path, MW)
    hh, ww = A.shape
    m = A > 127
    if not m.any():
        raise ValueError(f'空 alpha：{path}')
    ys, xs = np.nonzero(m)
    feet, top = float(ys.max()), float(ys.min())
    span = feet - top
    rows = [r for r in range(int(feet - 0.62 * span), int(feet - 0.52 * span), 4) if m[r].any()]
    cx = float(np.median([np.median(np.nonzero(m[r])[0]) for r in rows])) if rows else 0.5 * ww
    # 皮肤块（脸）：最大的连通块
    sk = _skin_mask(F, A)
    nl, lab, st, cen = cv2.connectedComponentsWithStats(sk, 8)
    order = [i for i in np.argsort(-st[1:, cv2.CC_STAT_AREA]) + 1 if st[i, cv2.CC_STAT_AREA] > 300]
    bust = False
    face = None
    canvas_full = (xs.min() <= 2 and ys.min() <= 2 and
                   xs.max() >= ww - 3 and ys.max() >= hh - 3)      # 人物被画框四边裁掉 = 特写
    if order:
        i0 = order[0]
        x, y, w_, h_, ar = st[i0]
        # 特写时 span = 整幅，用 30% 判「靠上」没意义 → 直接认最大皮肤块是脸
        if canvas_full or y < top + 0.30 * span:
            face = (float(cen[i0][0]), float(y), float(w_), float(h_))
            if ar > 0.20 * span * ww:
                bust = True
            if xs.min() <= 2 and ys.min() <= 2 and (xs.max() >= ww - 3 or ys.max() >= hh - 3):
                bust = True
    if face is None:                                    # 无正脸（背面/剪影）：按轮廓比例推眼行
        eye = top + 0.104 * span
        face = (cx, eye, 0.065 * span, 0.104 * span)
    else:
        fx, ftop, fw_, fh_ = face
        eye = ftop + 0.21 * fh_                         # 眉毛/眼 行 = 皮肤块顶 + 21%（实测标定）
    fx, ftop, fw_, fh_ = face
    if not bust and (feet - eye) > 8 and (feet - top) / (feet - eye) > 1.34:
        bust = True                                     # 脚不在画面里（半身横幅）
    if bust:
        H = fw_ / FACE_W_U
        feet = eye + H
        cx = fx
    else:
        H = feet - eye
    # 全部数字都在 **1024 测量空间**（与解码宽度无关，保证同一张图换 work_w 结果一致）；
    # 真正取贴图时由 _affine/_bbox 乘 self.ksrc = work_w/1024 换算。
    got = dict(H=H, cx=cx, eye=(fx, eye), eye_y=eye, facew=fw_, faceh=fh_,
               feet=feet, top=top, bust=bust, headtop_u=(feet - top) / H,
               bbox=(int(xs.min()), int(top), int(xs.max()) + 1, int(feet) + 1),
               w=MW, h=hh)
    _GEOM[key] = got
    return got


# ---------------------------------------------------------------- 图像集合
_ANGLE_FILES = {'front': 'hero_front_cut.png',
                'tq_r': 'hero_tq_r_cut.png',
                'tq_r45': 'hero_view_tq_r45_cut.png',      # 右侧 45°（生图补的；没有时回退 tq_r）
                'side_r': 'hero_side_r_cut.png'}
_KEY_FILES = {'raise': 'hero_pose_raise_cut.png',
              'slash': 'hero_pose_slash_cut.png',
              'draw': 'hero_pose_draw_cut.png'}
_EXPR_FILES = {'angry': 'hero_expr_angry_cut.png', 'smirk': 'hero_expr_smirk_cut.png'}
_KEYS = ('idle', 'raise', 'slash', 'draw')
_EXPRS = ('angry', 'smirk')
_ANGLES = tuple(_ANGLE_FILES)

# 已废弃参数（传进来直接报错，并说明原因）
_REMOVED = {
    'head_turn': '转头靠角度挤压 → 脸会横一道黑带/发团断开，已废弃；改用 angle/angle_from 交叉溶解',
    'head_pitch': '头部旋转需要蒙皮，二维单张立绘会拉变形，已废弃',
    'lean': '脊柱倾斜需要蒙皮，已废弃',
    'twist': '上身扭转需要蒙皮，已废弃',
    'arm_r': '抬臂需要蒙皮（腋下没有像素）→ 会塌成一坨，已废弃；抬刀请用 key="raise"',
    'arm_l': '抬臂需要蒙皮，已废弃',
    'elbow_r': '屈肘需要蒙皮，已废弃',
    'elbow_l': '屈肘需要蒙皮，已废弃',
    'knee': '屈膝需要蒙皮，已废弃；重心起伏请用两档 key 的摆放差',
    'sword': '单独转刀需要把刀切层，已废弃',
    'body_turn': '身体转身需要新的正身图/蒙皮，已废弃',
    'key_w': '「半个姿势」= 两个姿势叠在一起（四把刀那种错帧），已废弃；过渡请 ≤2 帧 + mblur≥7',
    'pose': '旧的 pose 字典接口已废弃，改用 play(key=...)',
    'key_zoom': '已废弃：半身键帧按脸自动对位，构图用 h 控制',
}


class PoseRig:
    """生图立绘 puppet：整姿势键帧 / 表情贴脸 / 角度溶解。**只有这三种。**"""

    def __init__(self, base='assets/gen/char', work_w=2048, images=None):
        """images：给「镜头实验」用的单图覆盖 {名字: 绝对路径}（名字只能是 'idle' 或某个 key/expr）。"""
        self.base = str(base)
        self.work_w = int(np.clip(int(work_w), 512, 2048))
        self.images = dict(images or {})
        single = self.images.get('idle') or self.images.get('front')
        self.angle_paths = {}
        if single:                                        # 单图 rig：只有这一张，就叫 'front'
            self.angle_paths['front'] = single
        else:
            for an, fn in _ANGLE_FILES.items():
                p = self.images.get(an) or os.path.join(self.base, fn)
                if os.path.exists(p):
                    self.angle_paths[an] = p
            if 'front' not in self.angle_paths:
                raise FileNotFoundError(f'{self.base} 下找不到 hero_front_cut.png')
        self.key_paths = {}
        for k, fn in _KEY_FILES.items():
            p = self.images.get(k) or os.path.join(self.base, fn)
            if os.path.exists(p):
                self.key_paths[k] = p
        self.expr_paths = {}
        for e, fn in _EXPR_FILES.items():
            p = self.images.get('expr_' + e) or os.path.join(self.base, fn)
            if os.path.exists(p):
                self.expr_paths[e] = p
        self.front = self.angle_paths['front']
        self.G = _geom(self.front, self.work_w)
        self.single = len(self.angle_paths) == 1

    # ---------------------------------------------------------------- 预热
    def warm(self):
        """预解码全部用到的贴图（管线载入时调一次，之后每帧不会抖）。"""
        for p in list(self.angle_paths.values()) + list(self.key_paths.values()) + \
                list(self.expr_paths.values()):
            _geom(p, self.work_w)
            _load(p, self.work_w)
        _look_import()
        return self

    # ---------------------------------------------------------------- 摆放
    @property
    def ksrc(self):
        return float(self.work_w) / 1024.0

    def _bbox(self, path):
        g = _geom(path, self.work_w)
        k = self.ksrc
        b = g['bbox']
        return (b[0] * k, b[1] * k, b[2] * k, b[3] * k)

    def _affine(self, path, dst, h, mode='auto'):
        """图片像素（work_w 空间）→ 画面仿射。mode='body' 脚底对齐，'face' 眼线对齐。"""
        g = _geom(path, self.work_w)
        k = self.ksrc
        hu = h / g['headtop_u']
        s = hu / (g['H'] * k)
        if mode == 'auto':
            mode = 'face' if g['bust'] else 'body'
        if mode == 'face':
            ax, ay = g['eye'][0] * k, g['eye_y'] * k
            tx, ty = dst[0], dst[1] - hu
        else:
            ax, ay = g['cx'] * k, g['feet'] * k
            tx, ty = dst[0], dst[1]
        return np.array([[s, 0, tx - s * ax], [0, s, ty - s * ay]], np.float32), hu, g

    def _warp(self, path, M, box, src_rect=None):
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
        M2[0, 2] += M[0, 0] * sx0 - x0
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
        q = pts @ M.T
        return (float(q[:, 0].min()), float(q[:, 1].min()), float(q[:, 0].max()), float(q[:, 1].max()))

    # ---------------------------------------------------------------- 表情补丁
    def _expr_patch(self, expr, dst, hu):
        """特写图 → 脸部补丁 (f, a, box, feather)；只贴「眉→下巴 + 两侧颧骨」。"""
        path = self.expr_paths[expr]
        g = _geom(path, self.work_w)
        k = self.ksrc
        fx, eye_y = g['eye'][0] * k, g['eye_y'] * k
        fw, fh = g['facew'] * k, g['faceh'] * k
        s = (FACE_W_U * hu) / fw
        top = eye_y - 0.13 * fh
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
        d = np.sqrt(((u - 0.5) / 0.5) ** 2 + ((v - 0.5) / 0.5) ** 2)
        fe = np.clip(1.0 - _sstep(0.72, 1.02, d), 0, 1)
        return f, np.clip(a * fe, 0, 1), box, fe

    # ---------------------------------------------------------------- 唯一入口
    def play(self, fr, t, key='idle', dst=(960, 900), h=680,
             angle='front', angle_from=None, mix=1.0,
             expr=None, mblur=0.0, alpha=1.0, defocus=0.0, wrap=0.0,
             grade=None, rim=None, look=None, shade=None, keep_red=None, **removed):
        """画一帧。key∈{'idle','raise','slash','draw'}；参数非法直接 ValueError。"""
        # ---- 严挡已废弃参数（错误信息写清原因）
        if removed:
            bad = [k for k in removed if k in _REMOVED]
            if bad:
                raise ValueError(f'{bad[0]!r} 已废弃：{_REMOVED[bad[0]]}')
            raise TypeError(f'play() 不接受的参数：{sorted(removed)}')
        if key not in _KEYS:
            raise ValueError(f'key={key!r} 不在 {_KEYS} 里')
        if expr is not None and expr not in _EXPRS:
            raise ValueError(f'expr={expr!r} 不在 {_EXPRS} 里（calm 直接用 key="idle"；'
                             f'look 是 3/4 侧脸，和正面图对不上，实测有黑带残影）')
        for a in (angle, angle_from):
            if a is not None and a not in _ANGLES:
                raise ValueError(f'angle={a!r} 不在 {_ANGLES} 里')
        if key != 'idle' and (angle != 'front' or angle_from is not None or expr is not None):
            raise ValueError('key=raise/slash/draw 是整姿势键帧，不能再叠角度溶解/表情')
        if expr is not None and angle_from is not None:
            raise ValueError('expr 只能和单一角度一起用（不允许「角度溶解 + 换脸」同帧）')
        if key == 'idle' and angle not in self.angle_paths:
            if angle == 'tq_r45':
                angle = 'tq_r'                        # 45° 图还没生成时的回退
            else:
                raise FileNotFoundError(f'缺少角度图 {angle}')
        if expr is not None and expr not in self.expr_paths:
            raise FileNotFoundError(f'缺少表情特写 {_EXPR_FILES[expr]}')
        if key != 'idle':
            if key not in self.key_paths:
                raise FileNotFoundError(f'缺少姿势图 {_KEY_FILES[key]}')
            if key == 'draw' and not _geom(self.key_paths['draw'], self.work_w)['bust']:
                raise ValueError('pose_draw 不是半身图，无法按特写插镜摆放')

        Hpx, Wpx = fr.shape[:2]
        grade = dict(grade or dict(expo=0.66, sat=0.55, tint=(0.90, 0.96, 1.06), lift=0.0, gamma=1.25))
        if keep_red is not None:
            grade['keep_red'] = float(keep_red)
        rim = rim or dict(col=(0.62, 0.74, 1.0), amt=1.6, dir=(-0.8, -0.6))
        add_look = look_import = None
        _lk, red_fn = _look_import()

        # ---- 选图 + 摆放
        if key == 'idle':
            pA = self.angle_paths[angle]
            pB = self.angle_paths.get(angle_from) if angle_from else None
            mix = float(np.clip(mix, 0.0, 1.0))
            if pB is None:
                layers = [(pA, 1.0)]
            else:
                layers = [(pA, 1.0 - mix), (pB, mix)]
        else:
            layers = [(self.key_paths[key], 1.0)]
        patch = self._expr_patch(expr, dst, h / self.G['headtop_u']) if expr else None

        # ---- 包围盒
        bx0 = by0 = 1e9
        bx1 = by1 = -1e9
        for p, w in layers:
            if w <= 1e-4:
                continue
            M, hu, g = self._affine(p, dst, h)
            r = self._map_rect(M, self._bbox(p))
            bx0, by0 = min(bx0, r[0]), min(by0, r[1])
            bx1, by1 = max(bx1, r[2]), max(by1, r[3])
        if patch is not None:
            bx0, by0 = min(bx0, patch[2][0]), min(by0, patch[2][1])
            bx1, by1 = max(bx1, patch[2][2]), max(by1, patch[2][3])
        mb_abs = (abs(mblur[0]) + abs(mblur[1])) if isinstance(mblur, (tuple, list)) else abs(mblur or 0)
        pad = 16.0 + mb_abs + (3.2 * defocus if defocus > 0.3 else 0.0) + (14 if wrap else 0)
        X0, Y0 = int(math.floor(max(0, bx0 - pad))), int(math.floor(max(0, by0 - pad)))
        X1, Y1 = int(math.ceil(min(Wpx, bx1 + pad))), int(math.ceil(min(Hpx, by1 + pad)))
        if X1 - X0 < 8 or Y1 - Y0 < 8:
            return fr, np.zeros((Hpx, Wpx), np.float32)
        box = (X0, Y0, X1, Y1)
        bw, bh = X1 - X0, Y1 - Y0

        # ---- 图层合成（纯摆放，无变形）
        accF = np.zeros((bh, bw, 3), np.float32)
        accA = np.zeros((bh, bw), np.float32)
        for p, w in layers:
            if w <= 1e-4:
                continue
            M, hu, g = self._affine(p, dst, h)
            f, a = self._warp(p, M, box, self._bbox(p))
            accF += (f * a[..., None]) * w
            accA += a * w
        accA = np.clip(accA, 0, 1)
        accF = accF / np.maximum(accA, 1e-4)[..., None]

        # ---- 表情贴片（静态一次贴好 + 低频差值修正）
        if patch is not None:
            f, a, pbox, feather = patch
            px0, py0 = pbox[0] - X0, pbox[1] - Y0
            fx0, fy0 = max(0, -px0), max(0, -py0)
            fx1, fy1 = min(f.shape[1], bw - px0), min(f.shape[0], bh - py0)
            if fx1 > fx0 and fy1 > fy0:
                sub = (slice(py0 + fy0, py0 + fy1), slice(px0 + fx0, px0 + fx1))
                fa = a[fy0:fy1, fx0:fx1]
                ff = f[fy0:fy1, fx0:fx1].copy()
                m = (feather[fy0:fy1, fx0:fx1] > 0.6) & (fa > 0.9)
                if int(m.sum()) > 120:
                    d = (accF[sub] - ff) * m[..., None]
                    wsum = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 6)
                    d = cv2.GaussianBlur(d, (0, 0), 6) / np.maximum(wsum, 1e-3)[..., None]
                    ff = np.clip(ff + np.clip(d, -0.12, 0.12), 0, 1)
                accF[sub] = accF[sub] * (1 - fa[..., None]) + ff * fa[..., None]
                accA[sub] = np.clip(accA[sub] * (1 - fa) + fa, 0, 1)

        # ---- 调色（与 sprite.py._front 同一套公式）+ shade + rim + look
        if shade:
            xs = np.arange(X0, X1, dtype=np.float32)[None, :]
            ys = np.arange(Y0, Y1, dtype=np.float32)[:, None]
            r2 = (np.clip((xs - shade[0]) / (shade[1] - shade[0]), 0, 1) * shade[2] +
                  np.clip((ys - shade[3]) / (Hpx - shade[3]), 0, 1) * shade[4])
            accF = accF * (1 - r2)[..., None]
        lum = (accF * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
        kr = float(grade.get('keep_red', 1.0))
        redmask = (red_fn(accF)[..., None] * kr) if kr > 0 else np.zeros((bh, bw, 1), np.float32)
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

        # ---- 方向模糊 / 虚化 / 淡出（过渡盖叠影用 mblur≥7）
        if mblur is not None and mb_abs > 0.01:
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
        if wrap > 0:
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

        a3 = accA[..., None]
        fr[Y0:Y1, X0:X1] = fr[Y0:Y1, X0:X1] * (1 - a3) + accF * a3
        amap = np.zeros((Hpx, Wpx), np.float32)
        amap[Y0:Y1, X0:X1] = accA
        return fr, amap


def rig(**kw):
    return PoseRig(**kw)
