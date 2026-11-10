"""Offline retail appearance export and static typed geometry preview."""
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import struct

from fighter_archive import Archive
from fighter_assets import unpack
from fighter_elf import Model
from fighter_geometry import Geometry
from fighter_render import RenderProgram
from fighter_rig import Skeleton
from fighter_skin import Skin
from fighter_resource_files import require, read_appearance
from fighter_xsh import Textures


def export_retail(game, donor, output, catalog, pins):
    require(donor in catalog.rows, 'Unknown retail appearance donor')
    raw=(Path(game)/'assets/v2ip.viv').read_bytes()
    require(hashlib.sha256(raw).hexdigest()==pins['v2ip_sha256'],'Original model archive changed')
    archive=Archive(raw);stem=catalog.rows[donor]['fields']['Model']['symbol']
    output=Path(output);require(not output.exists(),'Appearance output already exists');output.mkdir(parents=True)
    source={'format':'eagl-appearance-1','donor':donor}
    for part,suffix in [('model','.o'),('textures','.xsh'),('face','_F.o')]:
        data=archive.read(stem+suffix);path=output/(part+'.bin');path.write_bytes(data)
        source[part]={'path':path.name,'sha256':hashlib.sha256(data).hexdigest()}
    shapes=[t['name'] for t in Textures(unpack(archive.read(stem+'.xsh'))).images]
    return {'source':source,'shapes':shapes,'origin':donor,'native_playtest':False}


def morton(x,y,width,height):
    value=bit=0
    for n in range(max(width,height).bit_length()-1):
        if 1<<n<width:value|=((x>>n)&1)<<bit;bit+=1
        if 1<<n<height:value|=((y>>n)&1)<<bit;bit+=1
    return value


def raster(texture,tile):
    from PIL import Image
    w,h=tile['width'],tile['height'];pixels=texture.data[tile['pixels_offset']:tile['pixels_offset']+tile['pixels_bytes']]
    if tile['kind'] in (0x60,0x61,0x62):
        require(not tile['swizzled'],'Swizzled compressed preview is unsupported')
        header=[0]*31;header[:7]=[124,0x81007,h,w,len(pixels),0,1]
        header[18:21]=[32,4,int.from_bytes({0x60:b'DXT1',0x61:b'DXT3',0x62:b'DXT5'}[tile['kind']],'little')];header[26]=0x1000
        return Image.open(io.BytesIO(b'DDS '+struct.pack('<31I',*header)+pixels)).convert('RGBA')
    stride=1 if tile['kind']==0x7b else 4
    if tile['swizzled']:
        pixels=b''.join(pixels[morton(x,y,w,h)*stride:morton(x,y,w,h)*stride+stride] for y in range(h) for x in range(w))
    if tile['kind']==0x7b:
        at=tile['palette_offset'];palette=texture.data[at:at+tile['palette_entries']*4]
        pixels=b''.join(palette[i*4:i*4+4] for i in pixels)
    return Image.frombytes('RGBA',(w,h),pixels,'raw','BGRA')


def normal(word):
    result=[]
    for value,bits in [(word,11),(word>>11,11),(word>>22,10)]:
        sign=1<<(bits-1);result.append(max(-1,((value&(sign-1))-(value&sign))/(sign-1)))
    length=sum(v*v for v in result)**.5
    return [v/length for v in result] if length>.1 else [0,1,0]


def surface_triangles(positions,strip):
    """Ignore collapsed source placeholders when framing a static preview."""
    result=[]
    for i in range(2,len(strip)):
        a,b,c=strip[i-2:i+1]
        if len({a,b,c})!=3:continue
        u=[positions[b][k]-positions[a][k] for k in range(3)];v=[positions[c][k]-positions[a][k] for k in range(3)]
        cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        if sum(x*x for x in cross)<=1e-18:continue
        result.extend((a,b,c) if i%2 else (b,a,c))
    return result


def preview(game,folder,catalog,pins):
    from fighter_packages import inventory
    from fighter_registry import resolve
    folder=Path(folder);pack=inventory(folder);snapshot=resolve(catalog.baseline(),[pack])
    added=[v for k,v in snapshot['fighters'].items() if not k.startswith('retail/')]
    if not added:
        targets={row['target'] for row in pack['overrides']}
        added=[snapshot['fighters'][key] for key in targets]
    require(len(added)==1,'Preview one fighter at a time')
    key=added[0]['components']['appearance'];resource=snapshot['resources'][key]
    if 'source' in resource:
        files=read_appearance(folder,resource['source']);raw=unpack(files['model']);texture_data=unpack(files['textures'])
        if resource['source']['format']=='eagl-appearance-png-1':
            from fighter_appearance_png import paint
            texture_data,_,_=paint(texture_data,resource['source']['images'],files['images'])
        textures=Textures(texture_data)
    else:
        donor=catalog.bindings[key]['donor'];stem=catalog.rows[donor]['fields']['Model']['symbol']
        data=(Path(game)/'assets/v2ip.viv').read_bytes();require(hashlib.sha256(data).hexdigest()==pins['v2ip_sha256'],'Original models changed')
        archive=Archive(data);raw=unpack(archive.read(stem+'.o'));textures=Textures(unpack(archive.read(stem+'.xsh')))
    model=Model(raw);geometry=Geometry(model);Skin(model)
    labels={i:g['name'] for g in geometry.groups for i in g['render_resources']};meshes=[];points=[];skipped=[]
    for mesh in geometry.meshes:
        index=mesh['index'];label=labels[index]
        if mesh['strides']!=[12,8,4,4,2]:skipped.append(label+' (helper/sparkle)');continue
        streams=sorted((int(m[1]),model.export_offset(symbol)) for symbol in model.exports
            if (m:=re.fullmatch('__VB:::__GPvb_([0-9]+)_'+str(index)+'_'+re.escape(geometry.name),symbol)))
        buffers=[geometry.vertex_buffer(offset) for _,offset in streams]
        def values(buffer,fmt):
            at=geometry.scalars(buffer['data'],buffer['bytes']);return list(struct.iter_unpack(fmt,model.data[at:at+buffer['bytes']]))
        positions=values(buffers[0],'<3f');uv=values(buffers[1],'<2f');normals=[normal(v[0]) for v in values(buffers[3],'<I')]
        rm=model.export_offset('__RM:::__GP_RM_'+geometry.name+'_'+str(index));program=RenderProgram(model,rm)
        command=program.matching(14)[0];count=model.data_words(command.parameter,1)[0]
        at=geometry.scalars(model.local_pointer(command.parameter+4,count*2),count*2)
        strip=struct.unpack_from('<'+str(count)+'H',model.data,at);indices=surface_triangles(positions,strip)
        if not indices:continue
        used=sorted(set(indices));mapping={old:new for new,old in enumerate(used)}
        positions=[positions[i] for i in used];uv=[uv[i] for i in used];normals=[normals[i] for i in used];indices=[mapping[i] for i in indices]
        refs=[p['symbol'] for at,p in model.pointers.items() if rm<=at<rm+0xe0 and p['imported']]
        shapes={m[1] for ref in refs if (m:=re.search('SHAPENAME=([A-Za-z0-9_]{4}),1;',ref))}
        if len(shapes)!=1:skipped.append(label+' (external material)');continue
        shape=next(iter(shapes));points.extend(positions)
        meshes.append({'name':label+' / '+str(index),'group':label,'positions':positions,'uv':uv,'normals':normals,'indices':indices,'atlas':shape,
                       'transparent':'ALPHA' in label or any('ABM_BLEND' in ref for ref in refs)})
    require(points,'No supported textured surfaces for preview')
    images={}
    for tile in textures.images:
        stream=io.BytesIO();picture=raster(textures,tile)
        if 'source' in resource and resource['source']['format']=='eagl-appearance-png-1' and tile['name'] in files['images']:
            from fighter_appearance_png import png
            picture=png(files['images'][tile['name']]).convert('RGBA')
        picture.putalpha(255);picture.save(stream,format='PNG')
        images[tile['name']]='data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode('ascii')
    return {'meshes':meshes,'textures':images,'bounds':[[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]],
            'shapes':[{'name':t['name'],'width':t['width'],'height':t['height']} for t in textures.images],
            'notices':['Static source pose; no animation or native material emulation.',*sorted(set(skipped))]}
