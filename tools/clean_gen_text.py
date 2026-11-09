#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/clean_gen_text.py —— 抹掉整帧生图里「烙进像素」的文字（掩膜 + inpaint + 颗粒回填）。

背景：r1 的生图是「拿成片帧当参考重绘」出来的，原来那层大字被一起画进了像素
（`s_d17_eye.png` 的「我的」「刀」、`s_e218_hilt.png` 的「刀」「就」）。这类字不是文字层，
删文字层没用，只能 mask + inpaint。做法与 B 段 `p12_plate()` 一致（先降到 1080p、残差取字、闭运算+膨胀、
TELEA 半径 18、按邻近干净区的 σ 回填同频颗粒），保证全片一套口径。

用法（框用**归一化坐标** 0–1，和分辨率无关）
  python3 tools/clean_gen_text.py assets/gen/r1/s_d17_eye.png -o assets/gen/r1/s_d17_eye_clean.png \
      --roi 0.42,0.09,0.49,0.25 --roi 0.42,0.18,0.46,0.38 --red-roi 0.42,0.19,0.47,0.37
  --roi       亮度残差取字（灰白/纸白字）
  --red-roi   朱红字（红饱和度取色）——可与 --roi 叠加
"""
import argparse, os, sys
import numpy as np, cv2
from PIL import Image

W, H = 1920, 1080


def box_px(s):
    x0, y0, x1, y1 = [float(v) for v in s.split(',')]
    return int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--roi', action='append', default=[], help='归一化 x0,y0,x1,y1：亮度残差取字')
    ap.add_argument('--red-roi', action='append', default=[], help='归一化 x0,y0,x1,y1：朱红字')
    ap.add_argument('--radius', type=int, default=18)
    ap.add_argument('--thr', type=float, default=0.028, help='亮度残差阈值（越小抹得越狠）')
    ap.add_argument('--dil', type=int, default=13)
    ap.add_argument('--grain-src', default='0.55,0.62,0.75,0.85', help='取颗粒 σ 的干净区（归一化 x0,y0,x1,y1）')
    a = ap.parse_args()

    a_img = np.asarray(Image.open(a.src).convert('RGB').resize((W, H), Image.LANCZOS)).astype(np.float32) / 255
    lum = a_img.mean(-1)
    bgl = cv2.medianBlur((lum * 255).astype(np.uint8), 51).astype(np.float32) / 255
    res = cv2.GaussianBlur(lum - bgl, (0, 0), 2.5)

    reg = np.zeros((H, W), np.float32)
    for s in a.roi:
        x0, y0, x1, y1 = box_px(s); reg[y0:y1, x0:x1] = 1
    m = ((res > a.thr) & (reg > 0)).astype(np.uint8)

    for s in a.red_roi:
        x0, y0, x1, y1 = box_px(s)
        roi = a_img[y0:y1, x0:x1]
        r, g, b = roi[..., 0], roi[..., 1], roi[..., 2]
        rr = (((r - np.maximum(g, b)) > 0.12) & (r > 0.18)).astype(np.uint8)
        sub = np.zeros((H, W), np.uint8); sub[y0:y1, x0:x1] = rr
        m = np.maximum(m, sub)

    if m.max() == 0:
        sys.exit('掩膜为空：检查 --roi / --red-roi')
    m = cv2.dilate(cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)), np.ones((a.dil, a.dil), np.uint8))
    fix = cv2.inpaint((a_img * 255).astype(np.uint8), m, a.radius, cv2.INPAINT_TELEA).astype(np.float32) / 255

    # 颗粒回填（用邻近干净区的 σ，避免「一块干净补丁」）
    x0, y0, x1, y1 = box_px(a.grain_src)
    clean = lum[y0:y1, x0:x1]
    sig = float(np.std(clean - cv2.GaussianBlur(clean, (0, 0), 6)))
    rng = np.random.default_rng(11)
    n = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.75)
    n = n / (n.std() + 1e-6) * max(sig, 0.004)
    kk = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 4)[..., None]
    out = np.clip(fix + n[..., None] * kk, 0, 1)
    Image.fromarray((out * 255).astype(np.uint8)).save(a.out)
    print('mask %.2f%%  σ颗粒 %.4f  → %s' % (100 * float((m > 0).mean()), sig, a.out))


if __name__ == '__main__':
    main()
