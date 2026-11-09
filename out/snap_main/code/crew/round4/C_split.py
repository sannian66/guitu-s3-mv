# 把 c_contact 的大表按缩略图格子切块（每块 3 列 × 4 行 = 1440×1184，≤1920×1400）
# 用法：python3 crew/round4/C_split.py out/round4/C_contact_vN.jpg（c_contact.py 拼好大表后切块）
import sys; from PIL import Image
src=sys.argv[1]; S=Image.open(src); TW,TH=480,296; cols=6; rows=S.size[1]//TH
k=0
for r0 in range(0,rows,4):
    for c0 in (0,3):
        box=(c0*TW, r0*TH, (c0+3)*TW, min(rows,r0+4)*TH)
        tile=S.crop(box)
        if tile.convert('L').getextrema()[1]<30: continue
        p=src.replace('.jpg',f'_p{k}.jpg'); tile.save(p,quality=85); print(p,tile.size); k+=1
