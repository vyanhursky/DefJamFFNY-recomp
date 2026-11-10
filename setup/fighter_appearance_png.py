"""RGB atlas import retaining native controls, UV dimensions and material alpha.

Indexed fallback palettes are quantized independently for each exact native
alpha value. The HD raster retains source RGB and nearest original alpha.
"""
import hashlib
import io
import struct
from collections import defaultdict

from fighter_resource_files import require
from fighter_xsh import Textures
from fighter_appearance_authoring import raster,morton


def png(raw):
    from PIL import Image
    require(type(raw) is bytes and 0<len(raw)<=4*1024**2,'Appearance PNG exceeds 4 MiB')
    with Image.open(io.BytesIO(raw)) as image:
        require(image.format=='PNG' and 32<=image.width<=2048 and 32<=image.height<=2048,'Atlas must be a 32–2048px PNG')
        image.load();return image.convert('RGB')


def indexed(image,native,texture,tile):
    from PIL import Image
    groups=defaultdict(list)
    original=list(native.get_flattened_data() if hasattr(native,'get_flattened_data') else native.getdata())
    pixels=list(image.get_flattened_data() if hasattr(image,'get_flattened_data') else image.getdata())
    for i,rgba in enumerate(original):groups[rgba[3]].append(i)
    budget=tile['palette_entries'];require(len(groups)<=budget,'Native alpha classes exceed the palette budget')
    counts={alpha:1 for alpha in groups}
    for _ in range(budget-len(groups)):
        alpha=max(groups,key=lambda a:len(groups[a])/counts[a]);counts[alpha]+=1
    palette=bytearray(budget*4);output=bytearray(len(pixels));start=0
    for alpha,positions in sorted(groups.items()):
        width=min(4096,len(positions));height=(len(positions)+width-1)//width
        source=Image.new('RGB',(width,height));source.putdata([pixels[i] for i in positions]+[(0,0,0)]*(width*height-len(positions)))
        quantized=source.quantize(colors=counts[alpha],method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
        colors=quantized.getpalette();indices=quantized.tobytes()
        for n,position in enumerate(positions):output[position]=start+indices[n]
        for i in range(counts[alpha]):
            r,g,b=colors[i*3:i*3+3];palette[(start+i)*4:(start+i+1)*4]=bytes((b,g,r,alpha))
        start+=counts[alpha]
    if tile['swizzled']:
        swizzled=bytearray(len(output))
        for y in range(image.height):
            for x in range(image.width):swizzled[morton(x,y,image.width,image.height)]=output[y*image.width+x]
        output=swizzled
    return bytes(output),bytes(palette)


def native_identity(texture,tile):
    formats={0x60:0x0c,0x61:0x0e,0x62:0x0f,0x7b:0x0b,0x7d:0x06 if tile['swizzled'] else 0x12}
    palette=(texture.data[tile['palette_offset']:tile['palette_offset']+tile['palette_entries']*4] if tile['kind']==0x7b else b'')
    pixels=texture.data[tile['pixels_offset']:tile['pixels_offset']+tile['pixels_bytes']]
    return hashlib.sha256(b'XRTEX01\0'+struct.pack('<5I',formats[tile['kind']],tile['width'],tile['height'],len(palette)//4,tile['width'])+pixels+palette).hexdigest()


def paint(raw,specs,files):
    from PIL import Image
    texture=Textures(raw);rows={t['name']:t for t in texture.images}
    require(set(specs)==set(files) and set(specs)<=set(rows),'PNG atlas references an unknown texture shape')
    output=bytearray(raw);pictures={};decoded_pixels=0
    for shape,spec in specs.items():
        require(hashlib.sha256(files[shape]).hexdigest()==spec['sha256'],'Appearance PNG hash changed')
        tile=rows[shape];picture=png(files[shape]);native=raster(texture,tile)
        decoded_pixels+=picture.width*picture.height
        require(decoded_pixels<=64*1024**2,'Appearance PNGs exceed 64 megapixels')
        scale=picture.width//tile['width']
        require(scale in (1,2,4) and picture.size==(tile['width']*scale,tile['height']*scale),'Atlas must match the native dimensions at 1×, 2× or 4×')
        down=picture.resize(native.size,Image.Resampling.LANCZOS);candidate=down.convert('RGBA');candidate.putalpha(native.getchannel('A'))
        if candidate.tobytes()==native.tobytes():continue
        if tile['kind']==0x7b:
            pixels,palette=indexed(down,native,texture,tile);at=tile['palette_offset'];output[at:at+len(palette)]=palette
        elif tile['kind']==0x7d:
            pixels=candidate.tobytes('raw','BGRA')
            if tile['swizzled']:
                ordered=bytearray(len(pixels))
                for y in range(tile['height']):
                    for x in range(tile['width']):
                        a=(y*tile['width']+x)*4;b=morton(x,y,tile['width'],tile['height'])*4;ordered[b:b+4]=pixels[a:a+4]
                pixels=bytes(ordered)
        else:
            require(not tile['swizzled'],'Swizzled compressed import is unsupported')
            stream=io.BytesIO();candidate.save(stream,format='DDS',pixel_format={0x60:'DXT1',0x61:'DXT3',0x62:'DXT5'}[tile['kind']]);pixels=stream.getvalue()[128:]
        require(len(pixels)==tile['pixels_bytes'],'Atlas encoder changed native dimensions')
        at=tile['pixels_offset'];output[at:at+len(pixels)]=pixels
        pictures[shape]=picture
    rebuilt=Textures(bytes(output));hd={};receipt={}
    require(rebuilt.controls==texture.controls,'Atlas import changed material controls')
    for tile in rebuilt.images:
        shape=tile['name']
        if shape not in specs:continue
        original=raster(texture,rows[shape]);current=raster(rebuilt,tile)
        require(current.getchannel('A').tobytes()==original.getchannel('A').tobytes(),'Atlas encoder changed native material alpha')
        picture=pictures.get(shape,png(files[shape]));identity=native_identity(rebuilt,tile)
        if picture.size!=original.size:
            candidate=picture.convert('RGBA');candidate.putalpha(original.getchannel('A').resize(picture.size,Image.Resampling.NEAREST))
            stream=io.BytesIO();candidate.save(stream,format='PNG');hd[identity]=stream.getvalue()
        receipt[shape]={'native_id':identity,'native_size':list(original.size),'source_size':list(picture.size),'alpha':'original-exact'}
    return rebuilt.data,hd,receipt
