from pathlib import Path
import json,struct,math
from PIL import Image,ImageDraw,ImageFont
V=Path(__file__).resolve().parents[2];p=V/'data/fonts/zh_cn.bfn';b=p.read_bytes()
off,size,bitmap_size=struct.unpack_from('<3I',b,8);count=size//4
codes=struct.unpack_from('<%dI'%count,b,off);offsets=struct.unpack_from('<%dI'%count,b,off+size);start=off+size*2
glyphs={code:b[start+offset:start+(offsets[i+1] if i+1<count else bitmap_size)] for i,(code,offset) in enumerate(zip(codes,offsets))}
catalog=json.loads((V/'data/localization/zh_cn.json').read_text('utf8'))
need={c for m in catalog['messages'] for c in m['translation'] if ord(c)>127}
missing=sorted(c for c in need if int.from_bytes(c.encode(),'little') not in glyphs)
font=ImageFont.truetype(str(V/'data/fonts/source/NotoSansCJKsc-Regular.otf'),30)
for char in missing:
    canvas=Image.new('L',(32,32),0);draw=ImageDraw.Draw(canvas)
    draw.text((round((32-font.getlength(char))/2),-2),char,font=font,fill=255)
    data=bytearray()
    for y in range(32):
        for x0 in range(0,32,8):
            value=0
            for bit in range(8):
                if canvas.getpixel((x0+bit,y))>=80:value|=1<<(7-bit)
            data.append(value)
    assert any(data)
    glyphs[int.from_bytes(char.encode(),'little')]=struct.pack('<5H',32,32,32,0,0)+data
new_codes=sorted(glyphs);new_offsets=[];new_bitmap=bytearray()
for code in new_codes:new_offsets.append(len(new_bitmap));new_bitmap.extend(glyphs[code])
header=bytearray(b[:off]);struct.pack_into('<II',header,12,len(new_codes)*4,len(new_bitmap))
p.write_bytes(header+struct.pack('<%dI'%len(new_codes),*new_codes)+struct.pack('<%dI'%len(new_codes),*new_offsets)+new_bitmap)
print(json.dumps(dict(added=missing,total_glyphs=len(new_codes),bytes=p.stat().st_size),ensure_ascii=True))
