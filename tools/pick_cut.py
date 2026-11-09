"""挑选候选 → assets/gen/<镜号>/<姿势>_raw.png（2560 宽）→ tools/cutout.py → _cut.png
用法：python3 tools/pick_cut.py S035/run=/path/cand.png[:flip] ..."""
import sys, os
from PIL import Image, ImageOps
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT + '/tools')
import cutout
def main(args):
  for arg in args:
      job, src = arg.split('=')
      flip = src.endswith(':flip'); src = src.replace(':flip', '')
      shot, pose = job.split('/')
      od = f'{ROOT}/assets/gen/{shot}'; os.makedirs(od, exist_ok=True)
      im = Image.open(src).convert('RGB')
      im = im.resize((2560, round(2560 * im.size[1] / im.size[0])), Image.LANCZOS)
      if flip: im = ImageOps.mirror(im)
      raw = f'{od}/{pose}_raw.png'; im.save(raw)
      if pose != 'eyes':
          cutout.cutout(raw, f'{od}/{pose}_cut.png', 2560)
      print('done', job, flush=True)


def force_poly(shot_pose, pts):
    """刀刃等直边被抠掉时：按 raw 上的多边形（归一化坐标）强制 alpha=1、颜色取原图（直边不羽化）。"""
    import numpy as np, cv2
    od = f'{ROOT}/assets/gen/{shot_pose.split("/")[0]}'; pose = shot_pose.split('/')[1]
    raw = np.asarray(Image.open(f'{od}/{pose}_raw.png').convert('RGB'))
    cut = np.asarray(Image.open(f'{od}/{pose}_cut.png')).copy()
    h, w = raw.shape[:2]
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.int32([[x * w, y * h] for x, y in pts])], 255, cv2.LINE_AA)
    a = np.maximum(cut[..., 3], m)
    rgb = np.where(m[..., None] > 0, raw, cut[..., :3])
    Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), 'RGBA').save(f'{od}/{pose}_cut.png')


if __name__ == '__main__':
    main(sys.argv[1:])
