"""S043 同一时间点：左 v4 代码人物 | 右 生图抠图精灵（SPRITE_MODE=1），均走 Chorus1.frame 正常剪辑时间线。
python3 lib/rig_test/sprite_vs_v4.py [t=82.70] → lib/rig_test/sprite_vs_v4_S043.jpg"""
import os, sys, subprocess
import numpy as np, cv2
T = float(sys.argv[1]) if len(sys.argv) > 1 else 82.70
R = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv')
code = ("import sys,cv2,numpy as np;sys.path.insert(0,'%s/units');import chorus1 as C;fr,_=C.Chorus1().frame(%f);"
        "cv2.imwrite(sys.argv[1],(np.clip(fr,0,1)[...,::-1]*255+.5).astype(np.uint8))") % (R, T)
for mode, out in (('0', '/tmp/cmp_v4.png'), ('1', '/tmp/cmp_sp.png')):
    subprocess.run([sys.executable, '-c', code, out], env=dict(os.environ, SPRITE_MODE=mode), check=True)
a, b = cv2.imread('/tmp/cmp_v4.png'), cv2.imread('/tmp/cmp_sp.png')
a, b = a[120:960], b[120:960]                      # 去黑边
pad = np.zeros((70, a.shape[1] * 2 + 20, 3), np.uint8)
img = np.vstack([pad, np.hstack([a, np.zeros((a.shape[0], 20, 3), np.uint8), b])])
for x, s in ((40, 'v4 code rig  (HAIR_V4)'), (a.shape[1] + 60, 'AI image + cutout sprite  (SPRITE_MODE=1)')):
    cv2.putText(img, s, (x, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (230, 230, 230), 2, cv2.LINE_AA)
cv2.putText(img, 'S043  t=%.2fs' % T, (img.shape[1] - 330, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (150, 150, 150), 2, cv2.LINE_AA)
img = cv2.resize(img, (img.shape[1] * 2 // 3, img.shape[0] * 2 // 3), interpolation=cv2.INTER_AREA)
cv2.imwrite(R + '/lib/rig_test/sprite_vs_v4_S043.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 90])
print(R + '/lib/rig_test/sprite_vs_v4_S043.jpg', img.shape)
