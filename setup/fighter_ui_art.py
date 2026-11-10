"""Typed PNG fighter UI art, retiled through original geometry and HD overlays."""
import hashlib
import io
import struct

from fighter_assets import unpack
from fighter_archive import Archive
from fighter_resource_files import PORTRAIT_ALL_PARTS, PORTRAIT_GRID_PARTS, require

FORMAT = 'eagl-portrait-png-1'
MASTERS = ('selector', 'loading', 'icon', 'titlecard', 'grid_normal', 'grid_selected')
ROLES = MASTERS + PORTRAIT_ALL_PARTS
MAX_BYTES = 64 * 1024**2


def validate(source):
    from fighter_resource_files import safe_relative
    import re
    require(type(source) is dict and set(source) == {'format','donor','images','hd_scale'} and source['format']==FORMAT,
            'PNG UI source needs format, donor, images and hd_scale')
    require(type(source['donor']) is str and re.fullmatch(r'retail/[a-z0-9]+(?:-[a-z0-9]+)*',source['donor']), 'Invalid UI layout donor')
    require(type(source['hd_scale']) is int and source['hd_scale'] in (1,2,4), 'UI HD scale must be 1, 2 or 4')
    images=source['images']
    require(type(images) is dict and len(images)<=len(ROLES) and set(images)<=set(ROLES), 'Invalid fighter UI image roles')
    for spec in images.values():
        require(type(spec) is dict and set(spec)=={'path','sha256'} and type(spec['sha256']) is str and re.fullmatch('[0-9a-f]{64}',spec['sha256']), 'Invalid UI PNG descriptor')
        safe_relative(spec['path'])
    return source


def image(raw):
    from PIL import Image
    require(type(raw) is bytes and 0<len(raw)<=4*1024**2, 'UI PNG exceeds 4 MiB')
    with Image.open(io.BytesIO(raw)) as im:
        require(im.format=='PNG' and 32<=im.width<=2048 and 32<=im.height<=2048, 'UI art must be a 32–2048px PNG')
        im.load();result=im.convert('RGBA')
    require(result.getchannel('A').getbbox() is not None, 'UI PNG is entirely transparent')
    return result


def role_image(part, images):
    if part in images:return images[part],part
    role=part.rsplit('_',1)[0]
    key='titlecard' if role.endswith('logo') else 'icon' if role=='result' else role
    if key in images:return images[key],key
    if role.startswith('grid_') and 'icon' in images:return images['icon'],'icon'
    return None,None


def native_hash(texture, tile):
    # XRTEX01 is the same documented descriptor used by scripts/hd_assets.py
    # and the native texture loader; hash the actual compiled compressed bytes.
    formats={0x60:0x0c,0x61:0x0e,0x62:0x0f,0x7d:0x12}
    require(tile['kind'] in formats and not tile['swizzled'], 'Unsupported HD UI raster')
    pixels=texture.data[tile['pixels_offset']:tile['pixels_offset']+tile['pixels_bytes']]
    return hashlib.sha256(b'XRTEX01\0'+struct.pack('<5I',formats[tile['kind']],tile['width'],tile['height'],0,tile['width'])+pixels).hexdigest()


def used_size(texture,tile):
    """Original material extents can cover only part of its power-of-two raster."""
    at=struct.unpack_from('<I',texture.data,texture.name_sites[tile['name']][0]+4)[0]
    size=tile['width'],tile['height']
    for _ in range(64):
        word=struct.unpack_from('<I',texture.data,at)[0]
        if word&255==0x7c:
            flag,width,height=struct.unpack_from('<III',texture.data,at+4)
            require(flag==1 and 0<width<=tile['width'] and 0<height<=tile['height'],'Invalid original grid used extents')
            size=width,height
        delta=word>>8
        if not delta:return size
        at+=delta
    raise ValueError('Original grid attachment budget exceeded')


def render(source, files, baseline, selection):
    """Return native24 textures, exact full-resolution PNG tiles and a receipt."""
    from PIL import Image,ImageOps
    from fighter_portrait import UITextures,variant_path,PortraitTextureTemplate
    from fighter_ui_model import UIModel
    from fighter_caf_portrait import tiles,layout,compile_png
    validate(source)
    require(set(files)==set(source['images']), 'UI PNG inputs differ from their declared roles')
    images={};decoded={};pixels=0
    for key,raw in files.items():
        require(hashlib.sha256(raw).hexdigest()==source['images'][key]['sha256'], 'UI PNG source hash changed')
        digest=source['images'][key]['sha256']
        if digest not in decoded:
            decoded[digest]=image(raw);pixels+=decoded[digest].width*decoded[digest].height
            require(pixels<=64*1024**2,'UI source images exceed 64 megapixels')
        images[key]=decoded[digest]
    native,hd,receipt={},{},{}
    scale=source['hd_scale']
    for part in PORTRAIT_ALL_PARTS:
        picture,used=role_image(part,images)
        if part in PORTRAIT_GRID_PARTS:
            original=baseline.grid_template(part);texture=UITextures(original);target=texture.images[0]
            if picture is None:
                picture=retail_image(baseline,selection,'result_'+part.rsplit('_',1)[1]);used='donor result icon'
            width,height=target['width'],target['height']
            used_width,used_height=used_size(texture,target)
            def padded(output_scale):
                output=Image.new('RGBA',(width*output_scale,height*output_scale))
                output.paste(ImageOps.fit(picture,(used_width*output_scale,used_height*output_scale),centering=(.5,0)),(0,0))
                return output
            canvas=padded(1)
            # Single fixed original grid image, retaining all material controls.
            stream=io.BytesIO();canvas.save(stream,format='DDS',pixel_format={0x60:'DXT1',0x61:'DXT3',0x62:'DXT5'}[target['kind']])
            pixels=stream.getvalue()[128:];require(len(pixels)==target['pixels_bytes'],'Grid encoder layout differs')
            output=bytearray(original);at=target['pixels_offset'];output[at:at+len(pixels)]=pixels
            native[part]=PortraitTextureTemplate(original,hashlib.sha256(original).hexdigest()).compile(bytes(output))
            hd_canvases={target['name']:padded(scale)}
        else:
            path,stem=variant_path(part,selection);movie=Archive(unpack(baseline.archive.read(path)))
            original=unpack(movie.read(stem+'.xsh'));texture=UITextures(original)
            if picture is None:
                native[part]=original;receipt[part]={'source':'donor'};continue
            raw=unpack(movie.read(stem+'.o'));model=UIModel(raw,hashlib.sha256(raw).hexdigest())
            rows=tiles(model,texture);width,height,crops=layout(rows)
            exact=picture.width%width==0 and picture.height%height==0 and picture.width//width==picture.height//height in (1,2,4)
            if part.startswith('result_') and not exact:
                side=min(picture.size);picture=ImageOps.fit(picture,(side,side),centering=(.5,0))
            native[part],geometry=compile_png(original,model,picture,exact=exact)
            # Reproduce compile_png's fitted native canvas at the requested HD
            # scale, using original pixels rather than upscaling its DDS output.
            rows=tiles(model,texture);width,height,crops=layout(rows)
            from fighter_ui_art_layout import hd_tiles
            hd_canvases=hd_tiles(picture,rows,width,height,crops,scale)
        compiled=UITextures(native[part]);role_receipt={'source':used,'tiles':[]}
        for tile in compiled.images:
            identifier=native_hash(compiled,tile)
            if scale>1:
                out=io.BytesIO();hd_canvases[tile['name']].save(out,format='PNG');png=out.getvalue()
                require(identifier not in hd or hd[identifier]==png, 'Conflicting HD art for the same native UI texture')
                hd[identifier]=png
            role_receipt['tiles'].append({'native_id':identifier,'native_size':[tile['width'],tile['height']],
                                         'hd_size':[tile['width']*scale,tile['height']*scale]})
        receipt[part]=role_receipt
    require(sum(map(len,native.values()))+sum(map(len,hd.values()))<=MAX_BYTES,'Compiled UI art exceeds 64 MiB')
    return native,hd,receipt


def retail_image(baseline,selection,part):
    from PIL import Image
    from fighter_portrait import UITextures,variant_path
    from fighter_ui_model import UIModel
    from fighter_caf_portrait import tiles,layout
    path,stem=variant_path(part,selection);movie=Archive(unpack(baseline.archive.read(path)))
    raw=unpack(movie.read(stem+'.o'));model=UIModel(raw,hashlib.sha256(raw).hexdigest());texture=UITextures(unpack(movie.read(stem+'.xsh')))
    rows=tiles(model,texture);width,height,crops=layout(rows);canvas=Image.new('RGBA',(width,height))
    for key,row in rows.items():
        tile=row['image'];require(tile['kind'] in (0x60,0x61,0x62) and not tile['swizzled'],'Unsupported original UI PNG reference raster')
        pixels=texture.data[tile['pixels_offset']:tile['pixels_offset']+tile['pixels_bytes']]
        # Same bounded DDS wrapper as the local HD asset census.
        header=[0]*31;header[0:7]=[124,0x81007,tile['height'],tile['width'],len(pixels),0,1]
        header[18:21]=[32,4,int.from_bytes({0x60:b'DXT1',0x61:b'DXT3',0x62:b'DXT5'}[tile['kind']],'little')];header[26]=0x1000
        image=Image.open(io.BytesIO(b'DDS '+struct.pack('<31I',*header)+pixels)).convert('RGBA')
        box=crops[key];canvas.paste(image.crop((0,0,box[2]-box[0],box[3]-box[1])),box[:2])
    return canvas


def export_reference(game,donor,output,catalog,pin):
    from fighter_portrait import PortraitBaseline
    from pathlib import Path
    require(donor in catalog.rows,'Unknown retail UI donor')
    output=Path(output);require(not output.exists(),'UI reference output already exists')
    baseline=PortraitBaseline((Path(game)/'screens/screens.viv').read_bytes(),pin['screens_sha256'])
    selection=catalog.rows[donor]['native_binding']['selection_key'];output.mkdir(parents=True)
    descriptors={};layouts={}
    for part in PORTRAIT_ALL_PARTS:
        picture=retail_image(baseline,selection,('result_'+part.rsplit('_',1)[1]) if part in PORTRAIT_GRID_PARTS else part)
        if part in PORTRAIT_GRID_PARTS:
            from PIL import ImageOps
            picture=ImageOps.fit(picture,(64,64),centering=(.5,0))
        path=output/(part+'.png');picture.save(path)
        descriptors[part]={'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        layouts[part]=list(picture.size)
    return {'source':{'format':FORMAT,'donor':donor,'hd_scale':4,'images':descriptors},'layouts':layouts,'baseline_sha256':baseline.sha256}
