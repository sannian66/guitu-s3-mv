"""C 组 r6 #42 / C23：把 R6_C/c23_tools_intaglio_v2（黑底三块阴刻铜牌：圆规/曲尺/天平）切成三张独立精灵。
  c23_tool{i}_cut.png    带铜牌自己的倒角边（C_R6_NOBEVEL=0 用）
  c23_tool{i}_nb_cut.png 去倒角边：内缩 5.5% 只留平板牌面（铆钉留着），边缘 1.5px 抗锯齿"""
import cv2, numpy as np
G = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv') + '/assets/gen/R6_C/'
im = cv2.imread(G + 'c23_tools_intaglio_v2.png')
BOX = [(57, 73, 588, 585), (737, 73, 588, 585), (1411, 73, 588, 586)]
for i, (x, y, w, h) in enumerate(BOX):
    for suf, ins in (('', 3), ('_nb', 33)):
        c = im[y + ins:y + h - ins, x + ins:x + w - ins].astype(np.float32)
        hh, ww = c.shape[:2]
        pad = 12
        rgba = np.zeros((hh + 2 * pad, ww + 2 * pad, 4), np.float32)
        rgba[pad:pad + hh, pad:pad + ww, :3] = c
        a = np.zeros(rgba.shape[:2], np.float32); a[pad:pad + hh, pad:pad + ww] = 255
        a = cv2.GaussianBlur(a, (0, 0), 0.8)
        rgba[..., 3] = a
        cv2.imwrite(G + f'c23_tool{i}{suf}_cut.png', np.clip(rgba, 0, 255).astype(np.uint8))
print('ok')
