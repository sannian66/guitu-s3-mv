"""黑白红调色（用户 r5 追加：只改配色，不改画风）。
非红色 → 高反差黑白；红色保留为纯正朱红；橙黄暖色（火、日光）按饱和度部分转红。"""
import numpy as np, cv2

RED = np.array([200, 18, 22], np.float32)  # RGB 朱红

def grade_bwr(rgb, warm_to_red=0.85, contrast=1.12):
    img = rgb.astype(np.float32) / 255.0
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    h, s, v = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
    # 亮度 → S 曲线黑白
    L = img @ np.array([0.299, 0.587, 0.114], np.float32)
    L = np.clip((L - 0.5) * contrast + 0.5, 0, 1)
    L = L * L * (3 - 2 * L) * 0.6 + L * 0.4
    # 红色权重：纯红满权，橙黄按 warm_to_red
    dist = np.minimum(np.abs(h), np.abs(360 - h))          # 离 0° 的角距
    w_red = np.clip(1 - (dist - 12) / 10, 0, 1)            # ≤12° 全红，22° 衰减完
    w_warm = np.clip(1 - np.abs(h - 35) / 25, 0, 1) * warm_to_red * (h < 70)
    w = np.maximum(w_red, w_warm) * np.clip((s - 0.28) / 0.3, 0, 1) * np.clip((v - 0.08) / 0.2, 0, 1)
    w = cv2.GaussianBlur(w.astype(np.float32), (0, 0), 3)       # 去色块边缘
    gray = np.repeat(L[..., None], 3, -1)
    Lr = L[..., None]
    red = (RED / 255)[None, None] * np.clip(0.15 + v[..., None] * 1.05, 0, 1.15)  # 红随明度 V，纯红不变暗
    hot = np.clip((Lr - 0.78) / 0.22, 0, 1) ** 1.5                           # 高光渐入白，不断层
    red = red * (1 - hot) + np.array([1, .93, .9], np.float32) * hot
    out = gray * (1 - w[..., None]) + red * w[..., None]
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)
