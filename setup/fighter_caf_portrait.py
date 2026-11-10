"""PNG portraits retiled through verified original, axis-aligned UI quads.

No package supplies UI models/actions. Read-only original geometry determines
image placement; only native raster spans are authored. Not game acceptance.
"""
import hashlib
import io
from pathlib import Path
import re
import struct

from fighter_archive import Archive
from fighter_assets import unpack
from fighter_portrait import PortraitBaseline, PortraitTextureTemplate, UITextures, variant_path
from fighter_resource_files import PORTRAIT_PARTS, require
from fighter_ui_model import UIModel


def tiles(model, texture):
    """Read the observed SHORT3 quad stream and its native numeric TAR binding."""
    d=model.parts[1];result={}
    def pointer(at):
        require(at in model.pointers and model.pointers[at][1] is not None,'UI portrait pointer is not local')
        return model.pointers[at][1]
    for name,rm in model.exports.items():
        if not name.startswith('__RM:::'):continue
        start,end=pointer(rm),pointer(rm+8)
        require(0<=start<end<=len(d) and end-start<=4096,'UI portrait render bounds differ')
        at,param,shape,vertices=start,rm+0x3c,None,None
        sequence=[]
        while at<end:
            w=struct.unpack_from('<I',d,at)[0]
            if w==0:
                require(at+4==end,'UI portrait render tail differs');break
            op,n=w>>16,w&65535;sequence.append(op)
            require(op in (4,16,15,38,2,14,6,5,35,9,26) and 1<=n<=4 and at+n*4<end,'Unsupported portrait render command')
            if op==15:
                symbol,target=model.pointers[param+4]
                require(target is None,'Portrait image binding is not an original import')
                match=re.search(r';SHAPENAME=([1-9][0-9]*),1;',model.names[symbol])
                require(match is not None,'Unsupported portrait image identity');shape=int(match[1])
            if op==9:
                require(struct.unpack_from('<3I',d,at+4)==(0,0,6),'Portrait stream is not the observed SHORT3 format')
                data=pointer(param+4)
                require(data>=20 and struct.unpack_from('<3I',d,data-16)==(24,6,1)
                        and data+24<=len(d),'Portrait quad stream dimensions differ')
                vertices=list(struct.iter_unpack('<3h',d[data:data+24]))
            if op not in (4,25,26):param+=8
            at+=n*4
        require(sequence==[4,16,15,38,38,2,14,6,5,35,9,26] and shape is not None and vertices is not None,
                'Portrait render profile differs')
        xs,ys=sorted({v[0] for v in vertices}),sorted({v[1] for v in vertices})
        require(len(xs)==len(ys)==2 and {tuple(v[:2]) for v in vertices}=={(x,y) for x in xs for y in ys}
                and all(v[2]==0 for v in vertices),'Portrait geometry is not a flat rectangle')
        image=next((i for i in texture.images if int(i['name'])==shape),None)
        require(image is not None and shape not in result,'Portrait quad has an unknown or repeated raster')
        root=struct.unpack_from('<I',texture.data,texture.name_sites[image['name']][0]+4)[0]
        at=root;logical=(image['width'],image['height'])
        for _ in range(64):
            w=struct.unpack_from('<I',texture.data,at)[0];kind,delta=w&255,w>>8
            if kind==0x7c:
                flag,width,height=struct.unpack_from('<III',texture.data,at+4)
                require(flag==1 and 0<width<=image['width'] and 0<height<=image['height'],'Unsupported portrait used extents')
                logical=width,height
            if not delta:break
            at+=delta
        result[shape]={'bounds':(xs[0],ys[0],xs[1],ys[1]),'logical':logical,'image':image}
    require(set(result)=={int(i['name']) for i in texture.images},'Portrait geometry does not cover exactly its images')
    return result


def layout(rows):
    bounds=[r['bounds'] for r in rows.values()]
    x0,y0,x1,y1=min(b[0] for b in bounds),min(b[1] for b in bounds),max(b[2] for b in bounds),max(b[3] for b in bounds)
    require(x1>x0 and y1>y0,'Empty portrait layout')
    widths=[r['logical'][0]*(x1-x0)/(r['bounds'][2]-r['bounds'][0]) for r in rows.values()]
    heights=[r['logical'][1]*(y1-y0)/(r['bounds'][3]-r['bounds'][1]) for r in rows.values()]
    width,height=round(sum(widths)/len(widths)),round(sum(heights)/len(heights))
    require(0<width<=2048 and 0<height<=2048 and all(abs(v-width)<1 for v in widths)
            and all(abs(v-height)<1 for v in heights),'Portrait tile scales disagree')
    crops={}
    for key,r in rows.items():
        b=r['bounds'];box=tuple(round((v-origin)*scale/span) for v,origin,scale,span in
                               zip(b,(x0,y0,x0,y0),(width,height,width,height),(x1-x0,y1-y0,x1-x0,y1-y0)))
        require((box[2]-box[0],box[3]-box[1])==r['logical'],'Portrait raster and quad crop differ')
        crops[key]=box
    require(sum((b[2]-b[0])*(b[3]-b[1]) for b in crops.values())<=width*height,'Portrait tiles overlap')
    values=list(crops.values())
    require(not any(max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])
                    for i,a in enumerate(values) for b in values[i+1:]),'Portrait tile crops overlap')
    return width,height,crops


def compile_png(original, model, image, *, exact=False):
    from PIL import Image, ImageOps
    texture=UITextures(original)
    rows=tiles(model,texture);width,height,crops=layout(rows)
    # Some original portraits omit a transparent corner. Fit the complete
    # input inside the largest fully covered rectangle; never silently cut it.
    xs=sorted({v for b in crops.values() for v in (b[0],b[2])});ys=sorted({v for b in crops.values() for v in (b[1],b[3])})
    candidates=[]
    for left in xs:
        for right in xs:
            for top in ys:
                for bottom in ys:
                    area=(right-left)*(bottom-top)
                    if right<=left or bottom<=top:continue
                    covered=sum(max(0,min(right,b[2])-max(left,b[0]))*max(0,min(bottom,b[3])-max(top,b[1])) for b in crops.values())
                    if covered==area:candidates.append((area,left,top,right,bottom))
    require(candidates,'Portrait has no supported rectangular image area')
    _,left,top,right,bottom=max(candidates)
    canvas=ImageOps.contain(image,(right-left,bottom-top),Image.Resampling.LANCZOS)
    full=Image.new('RGBA',(width,height));full.paste(canvas,(left+(right-left-canvas.width)//2,top+(bottom-top-canvas.height)//2))
    if exact:
        full=image.resize((width,height),Image.Resampling.LANCZOS)
    output=bytearray(original)
    for key,row in rows.items():
        target=row['image'];require(target['kind'] in (0x60,0x61,0x62) and not target['swizzled'],'Unsupported PNG portrait raster format')
        tile=Image.new('RGBA',(target['width'],target['height']));tile.paste(full.crop(crops[key]),(0,0))
        stream=io.BytesIO();tile.save(stream,format='DDS',pixel_format={0x60:'DXT1',0x61:'DXT3',0x62:'DXT5'}[target['kind']])
        raw=stream.getvalue();require(raw[:4]==b'DDS ' and len(raw)==128+target['pixels_bytes'],'Portrait encoder output layout differs')
        start=target['pixels_offset'];output[start:start+target['pixels_bytes']]=raw[128:]
    result=bytes(output)
    require(PortraitTextureTemplate(original,hashlib.sha256(original).hexdigest()).compile(result)==result,'Portrait nonpixel controls changed')
    return result,{'canvas':[width,height],'tiles':{str(k):list(v) for k,v in crops.items()}}


def frame_png(image, part):
    """Trim transparent viewport margins; square result/grid art uses the top crop."""
    from PIL import ImageOps
    bounds=image.getchannel('A').getbbox()
    require(bounds is not None,'Portrait PNG is entirely transparent')
    framed=image.crop(bounds)
    if part.startswith('result_'):
        side=min(framed.size)
        framed=ImageOps.fit(framed,(side,side),centering=(0.5,0.0))
    return framed


def export_png(game, png, output, catalog, pin):
    from PIL import Image
    png,output=Path(png),Path(output)
    require(not png.is_symlink() and png.stat().st_size<=4*1024**2,'Invalid portrait PNG input')
    with Image.open(png) as im:
        require(im.format=='PNG' and 32<=im.width<=2048 and 32<=im.height<=2048,'Portrait must be a 32–2048px PNG')
        im.load();image=im.convert('RGBA')
    require(not output.exists(),'Portrait output already exists')
    baseline=PortraitBaseline((Path(game)/'screens/screens.viv').read_bytes(),pin['screens_sha256'])
    donor='retail/blaze';selection=catalog.rows[donor]['native_binding']['selection_key']
    files={};evidence={}
    for part in PORTRAIT_PARTS:
        path,stem=variant_path(part,selection);movie=Archive(unpack(baseline.archive.read(path)))
        raw=unpack(movie.read(stem+'.o'));model=UIModel(raw,hashlib.sha256(raw).hexdigest())
        files[part],evidence[part]=compile_png(unpack(movie.read(stem+'.xsh')),model,frame_png(image,part))
    output.mkdir(parents=True)
    source={'format':'eagl-portrait-1','donor':donor}
    for part,raw in files.items():
        path=output/(part+'.xsh');path.write_bytes(raw);source[part]={'path':part+'.xsh','sha256':hashlib.sha256(raw).hexdigest()}
    return {'source':source,'layouts':evidence,'png_sha256':hashlib.sha256(png.read_bytes()).hexdigest()}
