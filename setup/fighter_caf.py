"""Retail CAF recipes compiled from fighter-only data; never a native save import."""
import hashlib
import json
from pathlib import Path
import struct

from fighter_registry import fingerprint
from fighter_resource_files import require
from mods import ordinary_path, safe_relative

# One recipe schema. Everything past the four base fields is an optional section: finishers and atlases,
# an outfit collection (outfit_name, outfits, portraits, face), retail_moveset and voice_donor.
FORMAT = 'caf-fighter-1'
CAPABILITY = FORMAT
OUTFIT_SECTIONS = {'outfit_name', 'outfits', 'portraits', 'face'}


def source(value):
    require(type(value) is dict and set(value) == {'format', 'selection'}, 'CAF source needs format and selection')
    require(value['format'] == FORMAT, 'Unsupported CAF recipe format; export the fighter again with a current Workshop')
    descriptor = value['selection']
    require(type(descriptor) is dict and set(descriptor) == {'path', 'sha256'}, 'Invalid CAF recipe descriptor')
    safe_relative(descriptor['path'])
    import re
    require(type(descriptor['sha256']) is str and re.fullmatch('[0-9a-f]{64}', descriptor['sha256']), 'CAF recipe needs SHA-256')
    return value


def combination(styles):
    require(type(styles) is list and 1 <= len(styles) <= 3 and all(type(s) is int and 0 <= s < 5 for s in styles)
            and len(set(styles)) == len(styles), 'CAF styles must be one to three distinct retail styles')
    a,b,c,d = [s for s in range(5) if s != styles[0]]
    subsets = ((),(a,),(a,b),(a,c),(a,d),(b,),(b,c),(b,d),(c,),(c,d),(d,))
    return 87 + 11*styles[0] + subsets.index(tuple(sorted(styles[1:])))


def recipe(value, database):
    require(type(value) is dict and set(value) == {'stats','styles','caf_values','caf_colors'}, 'CAF recipe contains fighter data only')
    stats, values, colors = (value[k] for k in ('stats','caf_values','caf_colors'))
    keys=('upper','lower','speed','toughness','health')
    require(type(stats) is dict and set(stats) == set(keys) and all(type(n) is int and 0 <= n <= 50 for n in stats.values()), 'Invalid CAF training stats')
    core=combination(value['styles'])
    require(type(values) is list and len(values)==38 and all(type(n) is int and 0<=n<=0xffffffff for n in values), 'Invalid CAF choices')
    require(type(colors) is list and len(colors)==38 and all(type(n) is int and 0<=n<=255 for n in colors), 'Invalid CAF colors')
    require(values[0] < 6 and values[1] <= 36 and 1 <= values[5] <= 8, 'Unsupported CAF body/skin/face')
    # Internal slots are not interpreted by the rebuilding path. Do not permit
    # an arbitrary source payload to supply pointer/control fields.
    for slot in (6,7,8,9,10,11):
        require(1 <= values[slot] <= 99, 'Unsupported CAF facial feature')
    require(colors[8] < 36 and (values[27]==0xffffffff or values[27]<42), 'Unsupported CAF brow/teeth')
    # Every database-backed choice is bounded against this exact original SOD.
    from fighter_sod import Database
    require(isinstance(database, Database), 'CAF requires the verified original SOD')
    # The SOD parser exposes the validated table/index layout via its header.
    data=database.data
    def word(at):
        require(0 <= at <= len(data)-4, 'CAF database pointer is out of range')
        return struct.unpack_from('<I',data,at)[0]
    def mapping(at,tag=None):
        if tag is not None:
            require(data[at:at+4]==tag,'CAF database tag differs');at+=4
        count,stride=word(at),word(at+4);at+=8
        require(0<count<=65536 and 1<=stride<=8 and at+count*(4+4*stride)<=len(data),'CAF database index exceeds bounds')
        return [(word(at+i*4),[word(at+count*4+(i*stride+j)*4) for j in range(stride)]) for i in range(count)]
    tables=mapping(word(16),b'DATA')
    for slot in range(12,38):
        v,c=values[slot],colors[slot]
        if slot in (26,27) or v==0xffffffff:continue
        require(slot!=17,'Right-wrist recipe encoding is not verified')
        expected=0x912016dd if slot<20 else 0x7450591a if slot<22 else 0x426b8667 if slot<29 else 0x30948ea0
        ti,ri,ci=v>>24,v&65535,(v>>16)&255
        require(ti<len(tables) and tables[ti][0]==expected,'CAF item table differs from its slot')
        header=tables[ti][1][0]
        indexes=dict(mapping(word(header+4)))
        require(expected in indexes,'CAF item primary index is missing')
        rows=mapping(indexes[expected][0],expected.to_bytes(4,'little'))
        require(ri<len(rows),'CAF item row is out of range')
        row=rows[ri][1][0]
        if slot<20:
            # Schema fields are authoritative; clothing fitting/color arrays
            # each begin with count then pointers, as the retail shop reader.
            schema=dict(mapping(word(12),b'SKMA'))
            def field(key):
                require(expected^key in schema,'Missing CAF clothing field')
                return word(row+schema[expected^key][0]*4)
            require(word(row+32)<16 and (12,12,12,12,12,13,13,13,14,14,14,14,15,16,18,19)[word(row+32)]==slot, 'CAF garment category differs from its slot')
            fits,cols=field(0x7c853fa8),field(0xac3e66a4)
            require(c<word(fits) and ci<word(cols),'CAF clothing fitting/color is out of range')
        elif slot<22:require(c<36,'CAF hair palette is out of range')
        elif slot<29:
            require(c<word(word(row+12)),'CAF jewelry color is out of range')
    return core


def baseline_pins():
    return json.loads((Path(__file__).resolve().parents[1]/'config/fighter-caf-baseline.json').read_text())


def output_contexts(game):
    """Conservative original CAF template/palette combinations, not donor rigs.

    Native construction chooses from these pinned templates. Admit both choices
    rather than guessing the selected native fit; runtime still hashes the live
    skeleton and checks each actual face/hand palette before owned graph use.
    """
    from fighter_archive import Archive
    from fighter_assets import unpack
    path = ordinary_path(Path(game) / 'assets/v2cp_0.viv')
    with path.open('rb') as stream:
        data = stream.read(128 * 1024**2 + 1)
    require(len(data) <= 128 * 1024**2 and hashlib.sha256(data).hexdigest() == baseline_pins()['archives']['v2cp_0.viv'],
            'CAF graph contexts require the supported original v2cp_0.viv')
    archive = Archive(data)
    return {'caf-context/template-' + fit + '-face-' + str(face):
            (unpack(archive.read('V2CP_Template_' + fit.title() + '.o')),
             unpack(archive.read(f'V2CP_532_{face:04d}_C_F.o')))
            for fit in ('long', 'norm') for face in (1, 2)}


def validate_assets(value, game):
    pins=baseline_pins()
    names=set()
    for name,digest in pins['archives'].items():
        path=ordinary_path(Path(game)/'assets'/name)
        with path.open('rb') as stream:raw=stream.read(128*1024**2+1)
        require(len(raw)<=128*1024**2 and hashlib.sha256(raw).hexdigest()==digest,'CAF requires the supported original '+name)
        require(raw[:4] in (b'BIGF',b'BIG4'),'Unsupported CAF archive')
        size=struct.unpack_from('<I',raw,4)[0]
        count,directory=struct.unpack_from('>II',raw,8)
        require(size==len(raw) and count<=16384 and 16<=directory<=size,'Invalid CAF archive bounds')
        at=16
        for _ in range(count):
            require(at+9<=directory,'Truncated CAF archive directory')
            offset,length=struct.unpack_from('>II',raw,at);at+=8
            end=raw.find(b'\0',at,min(at+256,directory))
            require(end>=at and directory<=offset<=size and length<=size-offset,'Invalid CAF resource bounds')
            names.add(raw[at:end].decode('ascii').lower());at=end+1
    values=value['caf_values']
    for slot,prefix in ((6,541),(7,542),(8,551),(9,561),(10,571),(11,581)):
        n=values[slot]
        if slot in (6,9,10,11) and n==1:continue
        if slot==11 and n==4:n=2
        if slot==11 and n%2==0:continue
        require(f'v2cp_{prefix}_{n:04}_a01_01.xsh' in names,'CAF facial texture is not present in the original resources')
    return pins


def load(root, spec, catalog, game):
    source(spec)
    path=ordinary_path(Path(root).joinpath(*safe_relative(spec['selection']['path'])))
    with path.open('rb') as stream:raw=stream.read(65537)
    require(len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==spec['selection']['sha256'],'CAF recipe hash/size differs')
    from fighter_build import unique,non_finite
    value=json.loads(raw,object_pairs_hook=unique,parse_constant=non_finite)
    require(type(value) is dict, 'CAF recipe must be an object')
    import copy
    clean=copy.deepcopy(value);voice=clean.pop('voice_donor',None)
    require(voice is None or type(voice) is str and voice in catalog.rows
            and 1<=catalog.rows[voice]['native_binding']['core_id']<=86,'CAF voice donor must be an original retail fighter')
    # Each optional section wraps the loader below it: moveset -> outfits and faces -> the flat fighter.
    if 'retail_moveset' in clean:
        from fighter_caf_moveset import load_recipe
    elif OUTFIT_SECTIONS & set(clean):
        from fighter_caf_face import load_recipe
    else:
        load_recipe=load_flat
    result=load_recipe(root,clean,catalog,game)
    result.update(voice_donor=voice,sha256=fingerprint(value))
    return result


def load_flat(root, value, catalog, game):
    """One implicit outfit: the four base fields plus optional finishers and atlases."""
    from fighter_caf_extras import load as load_extras
    require({'stats','styles','caf_values','caf_colors'} <= set(value), 'CAF requires all fighter fields')
    extras = load_extras(root, value, catalog.db)
    base = {k: value[k] for k in ('stats','styles','caf_values','caf_colors')}
    core=recipe(base,catalog.db)
    validate_assets(base,game)
    return {'recipe':base,'core':core,'extras':extras}


def encode_rows(entries,report):
    """Recipe rows for the container: one per fighter outfit, in selection order. Returns (count, bytes)."""
    from fighter_caf_outfits import variants
    from fighter_caf_layout import RECIPE as R, RECIPE_STRIDE, VALUES, COLORS, TRAINING, STYLES
    rows=[]
    for key,item in sorted(entries.items()):
        binding=report['bindings'][key]
        aliases=item.get('outfit_aliases',[binding['selection_key']])
        for index, outfit in enumerate(variants(item)):
            r=outfit['recipe'];s=r['stats'];row=bytearray(RECIPE_STRIDE)
            struct.pack_into('<I',row,R['selection'],binding['selection_key'])
            struct.pack_into('<I',row,R['core'],item['core'])
            struct.pack_into('<%dI'%TRAINING,row,R['training'],*(s[k] for k in ('upper','lower','speed','toughness','health')))
            struct.pack_into('<I',row,R['style_count'],len(r['styles']))
            struct.pack_into('<%dI'%VALUES,row,R['values'],*r['caf_values'])
            row[R['colors']:R['colors']+COLORS]=bytes(r['caf_colors'])
            row[R['styles']:R['styles']+STYLES]=bytes(r['styles']+[255]*(STYLES-len(r['styles'])))
            row[R['retail']]=int(bool(item.get('retail_moveset')))
            struct.pack_into('<I',row,R['voice'],item['audio_core'])
            struct.pack_into('<II',row,R['outfit'],index,aliases[index])
            rows.append(bytes(row))
    return len(rows),b''.join(rows)


def encode(entries,report):
    """The whole fighter-caf.bin container: header, recipes, then the optional extras and face sculpts."""
    import fighter_caf_layout as layout
    from fighter_caf_extras import encode_section as encode_extras
    from fighter_caf_hd import encode_section as encode_hd
    from fighter_caf_face import encode_rows as encode_faces
    recipe_count,recipes=encode_rows(entries,report)
    extras_count,extras=encode_extras(entries,report)
    hd_count,hd=encode_hd(entries,report)
    faces_count,faces=encode_faces(entries,report)
    raw=layout.pack_header(recipe_count,extras_count,len(extras),hd_count,len(hd),faces_count)+recipes+extras+hd+faces
    require(len(raw)<=layout.MAX_FILE,'Compiled CAF fighters exceed the container budget')
    return raw


def menu_record(recipe, selection):
    """Original CreatePlayer.GetAttributesBM (4A442..4A617), no career bonuses.

    The six UI values are distinct from training. Native single-precision
    constants are promoted by the x87 arithmetic before the final truncation.
    Style numbering follows the original formatter's 4A62D..4A69F mapping.
    """
    bonuses=((2,0,0,1,0,0),(0,2,1,0,0,0),(0,1,0,0,2,0),(1,0,0,2,0,0),(0,0,2,0,1,0))
    training=[recipe['stats'][k] for k in ('upper','lower','speed','toughness','health')]+[0]
    values={letter:int(((n//5)*1.274999976158142+sum(bonuses[s][i] for s in recipe['styles'])*0.45000001788139343)*3.3333330154418945+0.5)
            for i,(letter,n) in enumerate(zip('ULSTHC',training))}
    return {'selection_key':selection,'stats':values,'styles':[(1,0,4,3,2)[s] for s in recipe['styles']]}
