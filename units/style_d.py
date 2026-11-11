"""第八轮风格 D 全片色板兜底：严格黑 / 白 / 灰 / 血红。
STYLE_D=1 时由 render_sprite_full.frame（字幕前）与 c1kit.finish 调用：只保留红色相，其余一律中性去色
（金、暖橙、冷蓝都回到灰阶）。各段自己的调色可以更细，但出画前一定过这一道。"""
import numpy as np


def red_mask(fr):
    """fr: float RGB 0–1。返回 0–1 的「血红保色」权重：按色相比例取红，过暗的红不算（避免噪声）。"""
    r, g, b = fr[..., 0], fr[..., 1], fr[..., 2]
    ratio = (r - np.maximum(g, b)) / (r + 1e-3)
    return np.clip((ratio - 0.38) / 0.24, 0, 1) * np.clip((r - 0.03) / 0.06, 0, 1)


def palette(fr):
    """float RGB → 黑白灰 + 血红。"""
    lum = 0.3 * fr[..., 0] + 0.59 * fr[..., 1] + 0.11 * fr[..., 2]
    m = red_mask(fr)[..., None]
    return lum[..., None] * (1 - m) + fr * m


def palette8(im):
    return (np.clip(palette(im.astype(np.float32) / 255), 0, 1) * 255 + 0.5).astype(np.uint8)
