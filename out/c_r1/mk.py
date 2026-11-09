import sys, os
from PIL import Image, ImageDraw
OUT='/Users/sannian/Downloads/鬼屠OP_new/out/c_r1/'
def pair(frames, out, w=640, cols=2):
    """before/after 竖排成对"""
    rows=[]
    for f in frames:
        a=Image.open(OUT+f'base/f{f}.png'); b=Image.open(OUT+f'after/f{f}.png')
        h=int(w*1080/1920)
        a=a.resize((w,h)); b=b.resize((w,h))
        im=Image.new('RGB',(w*2,h)); im.paste(a,(0,0)); im.paste(b,(w,0))
        d=ImageDraw.Draw(im); d.text((6,6),f'{f} BEFORE',fill=(255,255,0)); d.text((w+6,6),f'{f} AFTER',fill=(0,255,120))
        rows.append(im)
    h=rows[0].size[1]
    n=len(rows); c=cols; r=(n+c-1)//c
    sheet=Image.new('RGB',(c*w*2, r*h))
    for i,im in enumerate(rows):
        sheet.paste(im,((i%c)*w*2,(i//c)*h))
    sheet.save(OUT+out,quality=88); print(out, sheet.size)
if __name__=='__main__':
    pass
