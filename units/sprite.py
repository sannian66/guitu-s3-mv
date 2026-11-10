"""units/sprite.py — 人物精灵图层（SPRITE_MODE 试点，2026-11-09）
把抠好的生图人物（RGBA PNG）当作 2.5D 图层合进代码场景：场景/粒子/字幕/运镜仍是代码。
  SpriteLayer(path)                 读入 + 预计算（发区权重、轮廓带）
  .draw(fr, t, cx, cy, h, ...)      2.5D 摆放（随相机推拉/平移）、风吹网格形变、呼吸缩放、调色匹配、冷色 rim、光包裹
开关：环境变量 SPRITE_MODE=1 时 units/chorus1.py 的 S043 改用 S043Sprite；默认 0 = 原代码人物，其他镜头不受影响。

2026-11-09 性能前置 R1（渲染组）：draw() 改「包围盒 ROI 合成」+「精灵空间每帧缓存」，数学与旧版逐点相同。
  - 画布空间的所有运算（warpAffine / 主光衰减 / 角向模糊 / 虚化 / 背景光渗 / 合成）只算精灵落点包围盒
  - 精灵空间（风吹 + 调色 + rim + look）按参数缓存：同镜同帧的多个甲士只算一次（39 精灵 → 3~6 次）
  - SPRITE_FAST=0 回到旧的全画布实现（对拍用）

2026-11-09 性能前置 R2（渲染组）：把「每个精灵都要算一遍整幅调色」彻底拆掉（C18 单帧 47s → 5~6s）
  1) 线性基底缓存：精灵空间 F = A0·k0 + Arim·krim + k1，
       A0   = clip(lum + (F-lum)·sat, 0, 1) ** gamma · tint   （风后 F 的调色 + 保色红 + 逐像素色调）
       Arim = (ring·(0.25+0.75·facing))·A                      （冷色 rim 的几何项）
     只跟 (层, 帧, 风幅, sat, gamma, tint, keep_red, rim_dir) 有关，一帧每层算一次；
     每个精灵自己的 expo / lift / rim.col·rim.amt 只剩**标量/三系数**。
     等价性：_front 的 F 对 expo/lift/rim.col·rim.amt 是仿射的，_look 的 None/'sil' 也是仿射的；
     canvas 空间剩下的算子（warpAffine / shade / mblur / rotblur / defocus / wrap / 合成）对 F 全部线性，
     所以「先算整幅 F 再 warp」≡「各基底分别 warp 再线性组合」，只在 float32 舍入级有差别（实测 ≤2.4e-7）。
  2) 精灵空间只在 alpha 支撑 + 余量内算（wind 位移与 rim 模糊半径都落在余量里）；
     A>0 之外 F 只以 Aw 为权进入画面（各处都是 Fw*Aw 再除 clip(Aw)），故裁剪不影响可见像素。
  3) 同一张 PNG 的预处理（LANCZOS 缩放 / 距离变换 / 发区模糊）在进程内共享：flip 变体只做翻转拷贝。
  4) 归一化坐标网格改成广播视图（原来每层一份 2×2048×3051 float32 的 mgrid）。
  SPRITE_FAST=0 仍是旧的全画布实现（对拍基准，逐像素不变）。

2026-11-10 r6-SPRITE（工程组）从 feat/quality-pass 移植到 main：只移植本文件（R1/R2），不含转场去重/加刀/道具化/rig/grade_unify。
  改动：①开关 SPRITE_FAST 默认值见下（对拍 ≤2/255 才改 1）；②三处缓存键补 id(A)/id(ring)/id(wind_w)
  （main 各组有「改 sp.A / sp.ring 再画」的写法，原键只认 id(F) 会命中旧结果）；③_support 的 `is not` 比整数改成 !=。
"""
import math, os
import numpy as np, cv2
from PIL import Image

W, H = 1920, 1080
FAST = os.environ.get('SPRITE_FAST', '0') != '0'          # r6-SPRITE 移植：先默认 0，四帧对拍过线后再改默认

_GRID = {}        # (h, w) -> (gy, gx) 广播视图
_SCACHE = {}      # 整幅精灵空间结果（非线性 look 的回退路径）
_BCACHE = {}      # 线性基底（层 / 帧 / 风参 / 调色形参）
_WCACHE = {}      # wind() 全图结果
_RAW = {}         # 同一 PNG 的预处理（flip 变体共用）
_SMALL = None     # 36×64 的风场网格
_LUMW3 = np.array([[0.3, 0.59, 0.11]] * 3, np.float32)      # 亮度权重×3 行 → cv2.transform 三通道同步输出（避开 stride-0 广播）
_UID = [0]
_BCACHE_MAX = 8


def _scale_to3(a, vec):
    """(h,w) → (h,w,3)：通道 c = vec[c]·a（一次 SIMD transform）。"""
    v = np.asarray(vec, np.float32).reshape(-1)
    if v.size == 1:
        v = np.repeat(v, 3)
    return cv2.transform(a, np.ascontiguousarray(v).reshape(3, 1))


def _scalar3(v):
    return (float(v), float(v), float(v))


def _grid(h, w):
    k = (h, w)
    g = _GRID.get(k)
    if g is None:
        g = _GRID[k] = (np.arange(h, dtype=np.float32)[:, None], np.arange(w, dtype=np.float32)[None, :])
    return g


def _small_grid(gh=36, gw=64):
    global _SMALL
    if _SMALL is None:
        _SMALL = np.mgrid[0:gh, 0:gw].astype(np.float32)
    return _SMALL


def _sstep(a, b, x):
    x = np.clip((x - a) / (b - a), 0, 1); return x * x * (3 - 2 * x)


def _key(v):
    """把参数压成可哈希键。数组（rim['col'] / grade['tint'] 有时调用方传 np.ndarray）按**数值**入键，
    这样每帧新建的等值数组仍然命中缓存（tobytes 不行：布局/步长不同就 miss）。"""
    if isinstance(v, dict):
        return tuple(sorted((k, _key(x)) for k, x in v.items()))
    if isinstance(v, (list, tuple)):
        return tuple(_key(x) for x in v)
    if isinstance(v, np.ndarray):
        return ('nd', v.shape, v.dtype.str, tuple(v.ravel().tolist()))
    try:
        hash(v)
    except TypeError:
        return repr(v)
    return v


def _build(path, work_w=2048):
    """一张 PNG 的预处理（与 R1 逐点相同，只是少了几次整幅拷贝 / 用 cv2 的 SIMD 逐点算子）。"""
    im = Image.open(path).convert('RGBA')
    hh = round(im.size[1] * work_w / im.size[0])
    raw = np.asarray(im.resize((work_w, hh), Image.LANCZOS))    # uint8 (h,w,4)
    A = raw[..., 3].astype(np.float32); A /= 255
    F = np.ascontiguousarray(raw[..., :3]).astype(np.float32); F /= 255   # 场景管线是显示空间（finish 不做 gamma）
    lum = F.mean(-1)                                            # 注意：这里是三通道算术平均（不是亮度权重）
    skin = _sstep(0.02, 0.08, F[..., 0] - F[..., 2]) * _sstep(0.18, 0.35, lum)   # 暖亮 = 皮肤（不吹）
    skin = cv2.dilate(skin, np.ones((15, 15), np.uint8))
    # 离轮廓越近越「飘」：发梢、外圈发丝、衣摆边
    inside = np.ascontiguousarray(A > 0.5).view(np.uint8)
    dist = cv2.distanceTransform(inside, cv2.DIST_L2, 5)
    edge_w = cv2.pow(np.clip(1 - dist / 90.0, 0, 1), 1.3)
    edge_w = np.maximum(edge_w, (A < 0.5) * 1.0)
    hair = _sstep(0.30, 0.12, lum) + _sstep(0.45, 0.65, lum) * (F[..., 2] > F[..., 0])  # 暗发 + 冷色高光发丝
    wind_w = cv2.GaussianBlur((edge_w * np.clip(hair, 0, 1) * (1 - skin)).astype(np.float32), (0, 0), 6)
    ring = A - cv2.erode(A, np.ones((5, 5), np.uint8))
    ring = cv2.GaussianBlur(np.clip(ring, 0, 1), (0, 0), 1.5)
    h, w = A.shape
    ys, xs = np.nonzero(A > 0.5)
    bbox = (xs.min() / w, ys.min() / h, xs.max() / w, ys.max() / h) if len(xs) else (0, 0, 1, 1)
    top = (xs[ys.argmin()] / w, ys.min() / h) if len(xs) else (0.5, 0)   # 最高点（举刀=刀尖）
    return dict(A=A, F=F, wind_w=wind_w, ring=ring, h=h, w=w, bbox=bbox, top=top)


class SpriteLayer:
    def __init__(self, path, work_w=None):
        if work_w is None:
            work_w = int(os.environ.get('SPRITE_WORK_W', 2048))
        key = (os.path.abspath(str(path)), int(work_w))
        st = _RAW.get(key)
        if st is None:
            st = _RAW[key] = _build(path, work_w)
        # 只读共享：flip 变体在 c_kit.spr() 里是「新建实例 + setattr 翻转拷贝」，不会改到这里的数组
        self.A = st['A']; self.F = st['F']; self.wind_w = st['wind_w']; self.ring = st['ring']
        self.h, self.w = st['h'], st['w']
        self.bbox, self.top = st['bbox'], st['top']
        self.gy, self.gx = _grid(self.h, self.w)
        _UID[0] += 1
        self._uid = _UID[0]
        self._supp = None
        self._supp_for = None
        self._box = {}

    def fit(self, target_h, foot=None, ref='bbox'):
        """按 alpha 包围盒高度缩放：返回 (anchor_src=脚底中点, scale)。"""
        x0, y0, x1, y1 = self.bbox
        return ((x0 + x1) / 2, y1), target_h / ((y1 - y0) * self.h)

    # ---- 风吹：分区网格（粗网格 sin 位移 → 放大 → remap）
    def _disp(self, t, wdir, freq):
        """风吹位移场（全图，INTER_CUBIC），供 wind()/裁剪版共用。"""
        gh, gw = 36, 64
        yy, xx = _small_grid(gh, gw)
        yn, xn = yy / gh, xx / gw
        ph = 2 * math.pi * freq * t
        s = (np.sin(ph + yn * 7.0 + xn * 3.0) * 0.6 + np.sin(1.7 * ph + yn * 13.0 - xn * 5.0 + 1.3) * 0.3
             + np.sin(0.45 * ph + yn * 3.0) * 0.4)
        gust = 0.75 + 0.25 * math.sin(2 * math.pi * 0.31 * t)
        dx = cv2.resize((s * wdir[0] * gust).astype(np.float32), (self.w, self.h), interpolation=cv2.INTER_CUBIC)
        dy = cv2.resize((np.cos(ph * 1.3 + xn * 6 + yn * 4) * 0.35 + s * wdir[1]).astype(np.float32), (self.w, self.h),
                        interpolation=cv2.INTER_CUBIC)
        return dx, dy

    def _wind_full(self, t, amp, wdir, freq):
        dx, dy = self._disp(t, wdir, freq)
        k = self.wind_w * amp
        mx = self.gx - dx * k; my = self.gy - dy * k
        F = cv2.remap(self.F, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        A = cv2.remap(self.A, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        R = cv2.remap(self.ring, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        return F, A, R

    def wind(self, t, amp=7.0, wdir=(-1.0, 0.15), freq=0.9):
        key = (self._uid, id(self.F), id(self.A), id(self.ring), id(self.wind_w), round(t, 5), float(amp), tuple(wdir), float(freq))
        got = _WCACHE.get(key)
        if got is not None:
            return got
        got = self._wind_full(t, amp, wdir, freq)
        if len(_WCACHE) > 3:
            _WCACHE.clear()
        _WCACHE[key] = got
        return got

    def _wind_crop(self, t, amp, box, wdir=(-1.0, 0.15), freq=0.9):
        """与 wind() 逐点相同的风吹结果，但只算裁剪窗口（remap 的输出尺寸 = 窗口）。"""
        cx, cy, cw, ch = box
        dxf, dyf = self._disp(t, wdir, freq)
        dx = dxf[cy:cy + ch, cx:cx + cw]
        dy = dyf[cy:cy + ch, cx:cx + cw]
        k = self.wind_w[cy:cy + ch, cx:cx + cw] * amp
        gy, gx = self.gy, self.gx
        mx = gx[:, cx:cx + cw] - dx * k
        my = gy[cy:cy + ch, :] - dy * k
        mx = np.ascontiguousarray(mx, np.float32); my = np.ascontiguousarray(my, np.float32)
        F = cv2.remap(self.F, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        A = cv2.remap(self.A, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        R = cv2.remap(self.ring, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        return F, A, R

    # ---- 裁剪窗口：alpha 支撑 + 余量（覆盖风位移 amp·|dx| ≈ 1.3·amp 与 rim 模糊半径）
    def _support(self):
        if self._supp_for != id(self.A):
            m = np.ascontiguousarray(self.A > 0)
            x, y, w_, h_ = cv2.boundingRect(m.view(np.uint8))
            self._supp = (x, y, x + w_, y + h_)
            self._supp_for = id(self.A)
        return self._supp

    def _crop_box(self, amp):
        # 键带上 alpha 数组身份与支撑框：sec_d_bridge 有 copy.copy(base) 后改 sp.A 的用法，
        # 浅拷贝会共享 _box 这个 dict，不能只按 amp 缓存，否则两个实例会互相串窗口。
        x0, y0, x1, y1 = self._support()
        key = (float(amp), self._supp_for, self._supp)
        got = self._box.get(key)
        if got is None:
            m = int(math.ceil(abs(float(amp)) * 2.0)) + 14
            got = (max(0, x0 - m), max(0, y0 - m),
                   max(1, min(self.w, x1 + m) - max(0, x0 - m)),
                   max(1, min(self.h, y1 + m) - max(0, y0 - m)))
            if len(self._box) > 16:
                self._box.clear()
            self._box[key] = got
        return got

    # ---- 精灵空间：风吹 + 调色 + rim + look（同参数可复用；同镜多精灵只算一次）
    def _front(self, t, wind_amp, grade, rim, look, keep_red):
        key = (self._uid, id(self.F), id(self.A), id(self.ring), id(self.wind_w), round(t, 5), float(wind_amp), _key(grade), _key(rim), look, float(keep_red))
        got = _SCACHE.get(key)
        if got is not None:
            return got
        F, A, R = self.wind(t, wind_amp)
        lum = (F * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
        red = red_mask(F)[..., None] * keep_red                     # 保色遮罩：暗红内领、红穗、血保留饱和度
        sat = grade['sat'] * (1 - red) + 1.25 * red
        tint = np.array(grade['tint'], np.float32) * (1 - red) + np.array([1.08, 0.96, 0.96], np.float32) * red
        F = np.clip(lum + (F - lum) * sat, 0, 1) ** grade.get('gamma', 1.0) * grade['expo'] * tint + grade['lift']
        # 冷色 rim：轮廓环带 × 背光方向（法线 · 光向）
        gx = cv2.Sobel(A, cv2.CV_32F, 1, 0, ksize=5); gy = cv2.Sobel(A, cv2.CV_32F, 0, 1, ksize=5)
        n = np.sqrt(gx * gx + gy * gy) + 1e-4
        facing = np.clip(-(gx * rim['dir'][0] + gy * rim['dir'][1]) / n, 0, 1)
        rimm = (R * (0.25 + 0.75 * facing))[..., None] * A[..., None]
        F = F + rimm * np.array(rim['col'], np.float32) * rim['amt'] * 0.25
        if look:                                                   # 2026-11-09 全片整合：复用镜头的变体（剪影/水墨/纸/负片/投影）
            F, A = _look(F, A, rimm, rim, red, look)
        if len(_SCACHE) > 32:
            _SCACHE.clear()
        _SCACHE[key] = (F, A)
        return F, A

    # ---- R2：线性基底（一次算好 A0 / Arim / A，每个精灵只剩系数）
    def _make_basis(self, rk, t, amp, satv, gmv, tintv, keep_red):
        box = self._crop_box(amp)
        F, A, R = self._wind_crop(t, amp, box)
        # 逐点运算全部走「连续三通道」数组（numpy 对 (h,w,1)/(3,) 广播会退化到 stride-0 内层循环，慢 2~3 倍）
        lum = cv2.transform(F, _LUMW3)                              # (h,w,3)：三通道都是亮度
        red = red_mask(F)                                           # (h,w)
        if keep_red != 1.0:
            red *= np.float32(keep_red)
        sat = cv2.add(_scale_to3(red, np.float32(1.25) - np.float32(satv)), _scalar3(satv))
        tint = cv2.add(_scale_to3(red, np.float32([1.08, 0.96, 0.96]) - np.asarray(tintv, np.float32)),
                       tuple(float(v) for v in tintv))               # 逐像素色调（保色红）
        F1 = np.subtract(F, lum); F1 *= sat; F1 += lum
        np.clip(F1, 0, 1, out=F1)
        A0 = cv2.pow(F1, float(gmv)) if gmv != 1.0 else F1
        A0 *= tint                                                  # 色调折进基底：每精灵只剩 expo 这一个标量
        gx = cv2.Sobel(A, cv2.CV_32F, 1, 0, ksize=5); gy = cv2.Sobel(A, cv2.CV_32F, 0, 1, ksize=5)
        n = cv2.magnitude(gx, gy); n += np.float32(1e-4)
        d0, d1 = np.float32(-rk[0]), np.float32(-rk[1])
        if d0 == 0.0 and d1 == 0.0:
            facing = np.zeros_like(n)
        elif d0 == 0.0:                                             # 轴上光向：省掉一次整幅乘加
            facing = gy * d1
        elif d1 == 0.0:
            facing = gx * d0
        else:
            facing = gx * d0; facing += gy * d1
        facing /= n
        np.clip(facing, 0, 1, out=facing)
        facing *= np.float32(0.75); facing += np.float32(0.25)
        facing *= R; facing *= A
        return (A0, np.ascontiguousarray(A), facing, box)

    def _basis(self, t, wind_amp, grade, rim, look, keep_red):
        """返回 (A0, A, rimm, box, k0, k1, krim)，使精灵空间 F = A0·k0 + rimm·krim + k1；不支持的 look 返回 None。"""
        if look not in (None, 'sil'):
            return None
        rk = (float(rim['dir'][0]), float(rim['dir'][1]))
        tintv = tuple(float(v) for v in grade['tint'])
        bkey = (self._uid, id(self.F), id(self.A), id(self.ring), id(self.wind_w), round(t, 5), float(wind_amp),
                float(grade['sat']), float(grade.get('gamma', 1.0)), tintv, float(keep_red), rk)
        got = _BCACHE.get(bkey)
        if got is None:
            got = self._make_basis(rk, t, wind_amp, float(grade['sat']), float(grade.get('gamma', 1.0)),
                                   tintv, float(keep_red))
            if len(_BCACHE) >= _BCACHE_MAX:
                for k in list(_BCACHE)[:len(_BCACHE) - _BCACHE_MAX + 1]:
                    _BCACHE.pop(k, None)
            _BCACHE[bkey] = got
        A0, A, rimm, box = got
        expo, lift = float(grade['expo']), float(grade['lift'])
        col = np.array(rim['col'], np.float32)
        amt = float(rim['amt'])
        k0 = expo                                                  # 标量（色调已折进 A0）
        k1 = lift
        krim = col * np.float32(amt * 0.25)                         # 3 系数
        if look == 'sil':                                           # _look('sil')：F*0.10 + rimm·col·amt·0.45
            k0 = expo * 0.10
            k1 = lift * 0.10
            krim = krim * np.float32(0.10) + col * np.float32(amt * 0.45)
        return A0, A, rimm, box, k0, k1, krim

    def draw(self, fr, t, anchor_src, anchor_dst, scale, rot=0.0, breathe=0.005, wind_amp=7.0,
             grade=dict(expo=0.66, sat=0.55, tint=(0.90, 0.96, 1.06), lift=0.0, gamma=1.25),
             rim=dict(col=(0.62, 0.74, 1.0), amt=1.6, dir=(-0.8, -0.6)), wrap=0.35, mblur=(0.0, 0.0), extra_A=None, shade=(700, 1600, 0.30, 650, 0.45), keep_red=1.0, alpha=1.0, defocus=0.0, rotblur=0.0, look=None):
        """anchor_src：精灵内归一化锚点（如脸中心）；anchor_dst：画面像素位置；scale：精灵宽 → 画面像素 的倍率。"""
        # 呼吸 + 2.5D 摆放（仿射：缩放/旋转/平移；源锚点 → 目标）
        s = scale * (1 + breathe * math.sin(2 * math.pi * t / 3.4))
        ax, ay = anchor_src[0] * self.w, anchor_src[1] * self.h
        M = cv2.getRotationMatrix2D((ax, ay), rot, s)
        M[0, 2] += anchor_dst[0] - ax; M[1, 2] += anchor_dst[1] - ay
        if not FAST:
            F, A = self._front(t, wind_amp, grade, rim, look, keep_red)
            return self._draw_full(fr, M, F, A, wrap, mblur, extra_A, shade, alpha, defocus, rotblur, anchor_dst)
        # ---- 落点包围盒（含各类模糊所需的边距）
        x0n, y0n, x1n, y1n = self.bbox
        src = np.array([[x0n * self.w, y0n * self.h], [x1n * self.w, y0n * self.h],
                        [x0n * self.w, y1n * self.h], [x1n * self.w, y1n * self.h]], np.float32)
        dst = src @ M[:, :2].T + M[:, 2]
        mb = max(abs(mblur[0]), abs(mblur[1])) if (mblur[0] or mblur[1]) else 0.0
        pad = 2.0 + mb + (3 * defocus if defocus > 0.3 else 0.0) + 30.0        # 30 = 光包裹内模糊 σ10 的 3σ
        bx0, bx1 = dst[:, 0].min() - pad, dst[:, 0].max() + pad
        by0, by1 = dst[:, 1].min() - pad, dst[:, 1].max() + pad
        if rotblur:
            rmax = 0.0
            for cx in (bx0, bx1):
                for cy in (by0, by1):
                    rmax = max(rmax, math.hypot(cx - anchor_dst[0], cy - anchor_dst[1]))
            ext = 2 * rmax * abs(math.sin(math.radians(rotblur) / 2)) + 2
            bx0 -= ext; bx1 += ext; by0 -= ext; by1 += ext
        X0, Y0 = int(math.floor(bx0)), int(math.floor(by0))
        X1, Y1 = int(math.ceil(bx1)), int(math.ceil(by1))
        if X1 <= 0 or Y1 <= 0 or X0 >= W or Y0 >= H:               # 完全出画
            return fr, np.zeros((H, W), np.float32)
        cx0, cy0, cx1, cy1 = max(0, X0), max(0, Y0), min(W, X1), min(H, Y1)
        rw, rh = cx1 - cx0, cy1 - cy0
        M2 = M.copy(); M2[0, 2] -= cx0; M2[1, 2] -= cy0
        b = self._basis(t, wind_amp, grade, rim, look, keep_red)
        if b is None:                                             # 非线性 look：回到整幅精灵空间
            F, A = self._front(t, wind_amp, grade, rim, look, keep_red)
            Fw = cv2.warpAffine(F, M2, (rw, rh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            Aw = cv2.warpAffine(A, M2, (rw, rh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        else:                                                     # 线性基底：各基底 warp 后按系数组合
            A0, Ac, rimc, box, k0, k1, krim = b
            M3 = M2.copy()                                        # 裁剪偏移：源平移 = 线性部分 × 窗口原点
            M3[0, 2] += M2[0, 0] * box[0] + M2[0, 1] * box[1]
            M3[1, 2] += M2[1, 0] * box[0] + M2[1, 1] * box[1]
            A0w = cv2.warpAffine(A0, M3, (rw, rh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            rimw = cv2.warpAffine(rimc, M3, (rw, rh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            Aw = cv2.warpAffine(Ac, M3, (rw, rh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            Fw = A0w * np.float32(k0)
            Fw += rimw[..., None] * krim
            if k1:
                Fw += np.float32(k1)                              # k1·warp(1)：只在 Aw>0 处可见，故常数即可
        if mb:                                                     # 甩动时方向模糊（转头的动势）
            L = int(mb)
            if L >= 2:
                k = np.zeros((2 * L + 1, 2 * L + 1), np.float32)
                cv2.line(k, (L - int(mblur[0] / 2), L - int(mblur[1] / 2)), (L + int(mblur[0] / 2), L + int(mblur[1] / 2)), 1.0, 1)
                k /= k.sum()
                Fw = cv2.filter2D(Fw * Aw[..., None], -1, k); Aw = cv2.filter2D(Aw, -1, k)
                Fw = Fw / np.clip(Aw[..., None], 1e-3, None)
        if shade:                                                  # 屏幕空间主光衰减（坐标与原全画布版逐点相同）
            xs = np.arange(cx0, cx1, dtype=np.float32)[None, :]
            ys = np.arange(cy0, cy1, dtype=np.float32)[:, None]
            r = np.clip((xs - shade[0]) / (shade[1] - shade[0]), 0, 1) * shade[2] + np.clip((ys - shade[3]) / (H - shade[3]), 0, 1) * shade[4]
            Fw = Fw * (1 - r)[..., None]
        if rotblur:                                                # 旋斩：绕锚点的角向模糊（几张旋转副本平均）
            acc_F = Fw * Aw[..., None]; acc_A = Aw.copy(); n = 5
            for i in range(1, n):
                Mr = cv2.getRotationMatrix2D((float(anchor_dst[0]), float(anchor_dst[1])), rotblur * i / n, 1.0)
                Mr[0, 2] -= cx0; Mr[1, 2] -= cy0
                acc_F += cv2.warpAffine(Fw * Aw[..., None], Mr, (rw, rh)); acc_A += cv2.warpAffine(Aw, Mr, (rw, rh))
            Aw = acc_A / n; Fw = (acc_F / n) / np.clip(Aw[..., None], 1e-3, None)
        if defocus > 0.3:                                           # 景深虚化（前景刀在焦时人物在后）
            Fw = cv2.GaussianBlur(Fw * Aw[..., None], (0, 0), defocus); Aw = cv2.GaussianBlur(Aw, (0, 0), defocus)
            Fw = Fw / np.clip(Aw[..., None], 1e-3, None)
        if extra_A is not None:
            Aw = Aw * (extra_A[cy0:cy1, cx0:cx1] if extra_A.shape == (H, W) else extra_A)
        Aw = Aw * alpha
        # 光包裹：背景模糊光渗进人物边缘（只在包围盒 + 3σ 内算）
        m = 56
        y0m, y1m, x0m, x1m = cy0 - m, cy1 + m, cx0 - m, cx1 + m
        oy0, ox0 = max(0, y0m), max(0, x0m)
        oy1, ox1 = min(H, y1m), min(W, x1m)
        if oy1 - oy0 < 8 or ox1 - ox0 < 8:                          # 贴角极端情况：退回全画布
            if b is None:
                Ff, Af = F, A
            else:
                Ff, Af = self._front(t, wind_amp, grade, rim, look, keep_red)
            return self._draw_full(fr, M, Ff, Af, wrap, mblur, extra_A, shade, alpha, defocus, rotblur, anchor_dst)
        crop = fr[oy0:oy1, ox0:ox1]
        pt, pb, pl, pr = oy0 - y0m, y1m - oy1, ox0 - x0m, x1m - ox1
        if pt or pb or pl or pr:
            crop = cv2.copyMakeBorder(crop, pt, pb, pl, pr, cv2.BORDER_REFLECT_101)
        bgb = cv2.GaussianBlur(crop, (0, 0), 18)[cy0 - y0m:cy1 - y0m, cx0 - x0m:cx1 - x0m]
        inner = cv2.GaussianBlur(Aw, (0, 0), 10)
        edge = Aw                                                  # 原式 Aw - blur(Aw,6)*0 == Aw
        wrap_m = (edge * np.clip(1 - inner, 0, 1) * 2.0)[..., None] * wrap
        Fw = Fw + bgb * wrap_m
        a3 = Aw[..., None]
        fr[cy0:cy1, cx0:cx1] = fr[cy0:cy1, cx0:cx1] * (1 - a3) + Fw * a3
        AwF = np.zeros((H, W), np.float32)
        AwF[cy0:cy1, cx0:cx1] = Aw
        return fr, AwF

    # ---- 旧实现（全画布），供 SPRITE_FAST=0 对拍
    def _draw_full(self, fr, M, F, A, wrap, mblur, extra_A, shade, alpha, defocus, rotblur, anchor_dst):
        Fw = cv2.warpAffine(F, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        Aw = cv2.warpAffine(A, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        if mblur[0] or mblur[1]:
            L = int(max(abs(mblur[0]), abs(mblur[1])))
            if L >= 2:
                k = np.zeros((2 * L + 1, 2 * L + 1), np.float32)
                cv2.line(k, (L - int(mblur[0] / 2), L - int(mblur[1] / 2)), (L + int(mblur[0] / 2), L + int(mblur[1] / 2)), 1.0, 1)
                k /= k.sum()
                Fw = cv2.filter2D(Fw * Aw[..., None], -1, k); Aw = cv2.filter2D(Aw, -1, k)
                Fw = Fw / np.clip(Aw[..., None], 1e-3, None)
        if shade:
            yy, xx = _grid(H, W)
            r = np.clip((xx - shade[0]) / (shade[1] - shade[0]), 0, 1) * shade[2] + np.clip((yy - shade[3]) / (H - shade[3]), 0, 1) * shade[4]
            Fw = Fw * (1 - r)[..., None]
        if rotblur:
            acc_F = Fw * Aw[..., None]; acc_A = Aw.copy(); n = 5
            for i in range(1, n):
                Mr = cv2.getRotationMatrix2D(tuple(map(float, anchor_dst)), rotblur * i / n, 1.0)
                acc_F += cv2.warpAffine(Fw * Aw[..., None], Mr, (W, H)); acc_A += cv2.warpAffine(Aw, Mr, (W, H))
            Aw = acc_A / n; Fw = (acc_F / n) / np.clip(Aw[..., None], 1e-3, None)
        if defocus > 0.3:
            Fw = cv2.GaussianBlur(Fw * Aw[..., None], (0, 0), defocus); Aw = cv2.GaussianBlur(Aw, (0, 0), defocus)
            Fw = Fw / np.clip(Aw[..., None], 1e-3, None)
        if extra_A is not None: Aw = Aw * extra_A
        Aw = Aw * alpha
        bgb = cv2.GaussianBlur(fr, (0, 0), 18)
        edge = np.clip(Aw - cv2.GaussianBlur(Aw, (0, 0), 6) * 0.0, 0, 1)
        inner = cv2.GaussianBlur(Aw, (0, 0), 10)
        wrap_m = (Aw * np.clip(1 - inner, 0, 1) * 2.0)[..., None] * wrap
        Fw = Fw + bgb * wrap_m
        a3 = Aw[..., None]
        return fr * (1 - a3) + Fw * a3, Aw


def _look(F, A, rimm, rim, red, look):
    lum = (F * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
    if look == 'sil':        # 背光剪影：几乎全黑 + 轮廓光
        F = F * 0.10 + rimm * np.array(rim['col'], np.float32) * rim['amt'] * 0.45
    elif look == 'ink':      # 宣纸水墨：灰阶墨色，暗红保留为朱色
        ink = np.clip(0.06 + 0.75 * np.clip(lum * 1.6, 0, 1) ** 0.9, 0, 1) * np.array([1.0, 0.96, 0.88], np.float32)
        F = ink * (1 - red) + red * np.array([0.62, 0.10, 0.07], np.float32)
        A = A * 0.94
    elif look == 'paper':    # 纸糊巨影：暖白半透，边缘透光
        F = np.array([0.92, 0.84, 0.66], np.float32) * (0.45 + 0.6 * lum) + rimm * 1.2
        A = A * 0.72
    elif look == 'neg':      # 负片世界
        F = np.clip(1.0 - F * 1.1, 0, 1)
    elif look == 'shadow':   # 烛光投影：纯暗影
        F = F * 0.0 + np.array([0.05, 0.03, 0.02], np.float32)
        A = A * 0.7
    return F, A


def red_mask(F):
    """按色相比例取暗红（与亮度无关）：r 明显高于 g/b，排除肤色、金、棕皮革。"""
    r = F[..., 0]; mx = np.maximum(F[..., 1], F[..., 2])
    ratio = (r - mx) / (r + 1e-3)
    return (_sstep(0.38, 0.62, ratio) * _sstep(0.03, 0.09, r)).astype(np.float32)


_CACHE = {}
def layer(path):
    if path not in _CACHE: _CACHE[path] = SpriteLayer(path)
    return _CACHE[path]
