"""tools/c_solidify.py — C 组：精灵实体区半透明修补（抠图把皮肤/刀面误判成半透明 → 手、刀发灰透底）。
做法：alpha>lo 的区域腐蚀 r 像素得到「实心核」（细发丝被腐蚀掉，不受影响），核内 alpha 拉到 1，
颜色用原图（raw，按尺寸缩放）替换反混合后的颜色。输出 <out>（不覆盖原 cut）。
用法：python3 tools/c_solidify.py raw.png cut.png out_cut.png [lo=0.25] [r=9]"""
import sys, numpy as np, cv2
from PIL import Image
from scipy import ndimage


def solidify(raw, cut, out, lo=0.25, r=9):
    C = np.asarray(Image.open(cut).convert('RGBA')).astype(np.float32)
    h, w = C.shape[:2]
    R = np.asarray(Image.open(raw).convert('RGB').resize((w, h), Image.LANCZOS)).astype(np.float32)
    a = C[..., 3] / 255.0
    m = (a > lo).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(r) + 1, 2 * int(r) + 1))
    core = cv2.erode(m, k)
    core = core.astype(np.float32)          # 不填洞：双臂+刀围出的背景是真的洞
    core = cv2.GaussianBlur(core, (0, 0), 2.0)
    an = np.maximum(a, core)
    wsrc = np.clip((an - a) / np.maximum(1 - a, 1e-3), 0, 1)[..., None]   # 被抬高多少就混多少原图色
    rgb = C[..., :3] * (1 - wsrc) + R * wsrc
    Image.fromarray(np.dstack([rgb, an * 255]).clip(0, 255).astype(np.uint8)).save(out)
    print(out, 'alpha mean', a.mean().round(3), '->', an.mean().round(3))


if __name__ == '__main__':
    A = sys.argv
    solidify(A[1], A[2], A[3], *(float(x) for x in A[4:]))
