#!/usr/bin/env python3
"""Build the optional Latin-extension BFNT from a supplied licensed font (Pillow)."""
import argparse,json,math,struct
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

def build(font_path,catalog_paths):
    required=set('ÄÖÜäöüßẞĄĆĘŁŃÓŚŹŻąćęłńóśźż°×–—…')
    for path in catalog_paths:
        catalog=json.loads(Path(path).read_text('utf-8'))
        required.update(c for row in catalog['messages'] for c in row['translation'] if ord(c)>127)
    font=ImageFont.truetype(str(font_path),26)
    codes=[];offsets=[];bitmaps=bytearray()
    for char in sorted(required,key=lambda c:int.from_bytes(c.encode(),'little')):
        left,top,right,bottom=font.getbbox(char,anchor='ls')
        if top < -26 or bottom > 6: raise ValueError('glyph exceeds 32px baseline cell: '+repr(char))
        shift=max(0,-left)
        advance=math.ceil(font.getlength(char))+shift
        width=max(1,math.ceil(max(font.getlength(char),right))+shift)
        canvas=Image.new('L',(width,32),0)
        ImageDraw.Draw(canvas).text((shift,26),char,font=font,fill=255,anchor='ls')
        data=bytearray()
        for y in range(32):
            for x0 in range(0,width,8):
                value=0
                for bit in range(8):
                    x=x0+bit
                    if x<width and canvas.getpixel((x,y))>=80:value|=1<<(7-bit)
                data.append(value)
        if not any(data):raise ValueError('missing or empty glyph: '+repr(char))
        codes.append(int.from_bytes(char.encode(),'little'));offsets.append(len(bitmaps))
        bitmaps.extend(struct.pack('<5H',width,32,advance,0,0)+data)
    count=len(codes)
    header=struct.pack('<IHHIII16s',0x00544e46,0xffe2,32,36,count*4,len(bitmaps),b'ML Latin Ext')
    return header+struct.pack('<%dI'%count,*codes)+struct.pack('<%dI'%count,*offsets)+bitmaps,sorted(required)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('font',type=Path);p.add_argument('output',type=Path);p.add_argument('catalogs',type=Path,nargs='+')
    a=p.parse_args();data,chars=build(a.font,a.catalogs)
    a.output.write_bytes(data);print(json.dumps(dict(glyphs=len(chars),bytes=len(data)),ensure_ascii=True))
if __name__=='__main__':main()
