"""CAF v4 head sculpts: fixed retail topology and bounded position deltas.

The native adapter compares every reference XYZ against the assembled original
head before applying a sealed Coordinates-only morph. Imported geometry never
supplies rigging, UVs, programs, native pointers or material definitions.
"""
import copy
import hashlib
import json
import math
import re
import struct
from pathlib import Path

from fighter_caf_layout import FACE_STRIDE
from fighter_resource_files import require
from mods import ordinary_path, safe_relative

MESHES = ((0,54),(1,218),(2,70),(3,92),(4,73),(5,51),(6,51),(7,81),(9,20))
BASIS = (0,5,6,9,10,11)
ROW = FACE_STRIDE
MAX_BYTES = 8*1024*1024


def load(root, descriptor, recipe):
    require(type(descriptor) is dict and set(descriptor)=={'path','sha256'}, 'Invalid CAF face descriptor')
    require(type(descriptor['sha256']) is str and re.fullmatch('[0-9a-f]{64}',descriptor['sha256']), 'CAF face needs SHA-256')
    root=ordinary_path(Path(root));path=ordinary_path(root.joinpath(*safe_relative(descriptor['path'])))
    require(path.is_relative_to(root),'CAF face leaves its package')
    with path.open('rb') as stream:raw=stream.read(256*1024+1)
    require(len(raw)<=256*1024 and hashlib.sha256(raw).hexdigest()==descriptor['sha256'],'CAF face hash/size differs')
    from fighter_build import unique,non_finite
    value=json.loads(raw,object_pairs_hook=unique,parse_constant=non_finite)
    return validate(value,recipe)


def validate(value, recipe):
    keys={'schema','template_sha256','basis','meshes'}
    require(type(value) is dict and set(value)==keys|({'neck_normals'} if value.get('schema')=='caf-face-coordinates-2' else set()),'Invalid CAF sculpt fields')
    require(value['schema'] in ('caf-face-coordinates-1','caf-face-coordinates-2') and type(value['template_sha256']) is str
            and re.fullmatch('[0-9a-f]{64}',value['template_sha256']),'Unsupported CAF sculpt contract')
    if value['schema']=='caf-face-coordinates-2':validate_normals(value['neck_normals'])
    require(type(value['basis']) is list and all(type(v) is int for v in value['basis'])
            and value['basis']==[recipe['caf_values'][i] for i in BASIS],'CAF face basis differs from its outfit')
    meshes=value['meshes']
    require(type(meshes) is list and len(meshes)==len(MESHES),'CAF face must retain all supported retail render meshes')
    for row,(rm,count) in zip(meshes,MESHES):
        require(type(row) is dict and set(row)=={'rm','positions','deltas'} and type(row['rm']) is int and row['rm']==rm,'CAF face render-mesh order differs')
        for key,limit in (('positions',100.),('deltas',.6)):
            require(type(row[key]) is list and len(row[key])==count,'CAF face vertex count differs')
            for p in row[key]:
                require(type(p) is list and len(p)==3 and all(type(v) in (int,float) and math.isfinite(v) and abs(v)<=limit for v in p),'CAF face coordinates exceed finite bounds')
    points=[p for m in meshes for p in m['positions']]
    lo,hi=min(p[1] for p in points),max(p[1] for p in points)
    require(10<lo<hi<30,'CAF face reference is outside native bind space')
    require(all(max(map(abs,d))<=1e-6 for m in meshes for p,d in zip(m['positions'],m['deltas']) if p[1]<=lo+(hi-lo)*.12),'CAF face moves the protected neck seam')
    return copy.deepcopy(value)


def validate_normals(rows):
    require(type(rows) is list and 0<len(rows)<=128,'Invalid neck normal correction count')
    seen=set()
    for row in rows:
        require(type(row) is dict and set(row)=={'slot','rm','vertex','position','original','replacement'},'Invalid neck normal correction fields')
        require(type(row['slot']) is int and row['slot'] in (3,12)
                and type(row['rm']) is int and 0<=row['rm']<16
                and type(row['vertex']) is int and 0<=row['vertex']<65535,'Invalid neck normal target')
        target=(row['slot'],row['rm'],row['vertex'])
        require(target not in seen,'Duplicate neck normal target');seen.add(target)
        p=row['position']
        require(type(p) is list and len(p)==3 and all(type(v) in (int,float) and math.isfinite(v) and abs(v)<=100 for v in p)
                and 10<p[1]<30,'Invalid neck normal reference position')
        for key in ('original','replacement'):
            word=row[key]
            require(type(word) is int and 0<=word<=0xffffffff,'Invalid packed neck normal')
            components=[]
            for shift,bits in ((0,11),(11,11),(22,10)):
                sign=1<<(bits-1);v=word>>shift
                components.append(max(-1,((v&(sign-1))-(v&sign))/(sign-1)))
            require(sum(v*v for v in components)>=.01,'Invalid packed neck normal')
    return rows


def encode_normals(entries, report):
    from fighter_caf_layout import NORMAL_STRIDE, NORMAL_MAX
    from fighter_caf_outfits import variants
    rows=[]
    for key,item in sorted(entries.items()):
        for index,outfit in enumerate(variants(item)):
            face=outfit.get('face')
            if not face or face['schema']!='caf-face-coordinates-2':continue
            validate(face,outfit['recipe'])
            for r in face['neck_normals']:
                rows.append(struct.pack('<5I3f2I',report['bindings'][key]['selection_key'],index,r['slot'],r['rm'],r['vertex'],*r['position'],r['original'],r['replacement']))
    require(len(rows)<=NORMAL_MAX,'CAF neck normals exceed the container budget')
    raw=b''.join(rows)
    require(len(raw)==len(rows)*NORMAL_STRIDE,'Invalid compiled neck normal stride')
    return len(rows),raw


def load_recipe(root, value, catalog, game):
    from fighter_caf_outfits import load as load_outfits
    clean=copy.deepcopy(value)
    outfits=clean.get('outfits',[])
    require(type(outfits) is list and len(outfits)<=2 and all(type(row) is dict for row in outfits),
            'CAF v4 needs a bounded outfit collection')
    descriptors=[clean.pop('face',None)]
    for row in outfits:descriptors.append(row.pop('face',None))
    result=load_outfits(root,clean,catalog,game)
    for row,descriptor in zip(result['outfits'],descriptors):
        if descriptor is not None:row['face']=load(root,descriptor,row['recipe'])
    result['sha256']=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    return result


def encode_rows(entries, report):
    """Sculpt rows for the container, one per fighter outfit that has a face. Returns (count, bytes)."""
    from fighter_caf_outfits import variants
    rows=[]
    for key,item in sorted(entries.items()):
        for index,outfit in enumerate(variants(item)):
            if 'face' not in outfit:continue
            value=validate(outfit['face'],outfit['recipe'])
            raw=struct.pack('<II6I',report['bindings'][key]['selection_key'],index,*value['basis'])
            raw+=b''.join(struct.pack('<6f',*p,*d) for m in value['meshes'] for p,d in zip(m['positions'],m['deltas']))
            require(len(raw)==ROW,'Invalid compiled CAF face stride');rows.append(raw)
    raw=b''.join(rows)
    require(len(raw)<=MAX_BYTES,'CAF face sculpt budget exceeded')
    return len(rows),raw
