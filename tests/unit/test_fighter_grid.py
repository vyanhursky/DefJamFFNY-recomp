"""Synthetic UI templates: owned symbols, frames, textures and retained originals."""
import hashlib
import struct

import pytest

from test_fighter_portrait import ui
from fighter_assets import AssetError
from fighter_portrait import UITextures
from fighter_ui_model import UIModel
from fighter_grid import append_grid, GridStates
import fighter_apt as apt


def model_fixture():
    data = bytearray(1120)
    data[0x258:0x25c] = b'2\x001\x00'; data[0x320:0x322] = b'1\x00'
    matrix_name = b'ScaleMatrix::1::TextureMatrix\0'
    data[0x2b4:0x2b4 + len(matrix_name)] = matrix_name
    local = [(0x444,0x24c),(0x43c,0x340),(0x434,0x32c),(0x430,0x324),(0x42c,0x258),
             (0x418,0x25c),(0x378,0x2e0),(0x32c,0x320),(0x31c,0),(0x310,0x2b4),
             (0x300,0x2a0),(0x2f0,0x280),(0x2e0,0x260),(0x25c,0x25a),(0x254,0x1d4),
             (0x224,0xb4),(0x214,0x80),(0x204,0x70),(0x1fc,0x50),(0x1f4,0),
             (0x1d4,0x19c),(0x1cc,0x188),(0x1b0,0x184),(0x1a8,0x180),(0x1a4,0x170),
             (0x19c,0xdc),(0xd4,0xb4),(0xb0,0xb4),(0xa0,0xd0)]
    imports = [0x334,0x1e4,0x30c,0x1dc,0x2fc,0x21c,0x2ec,0x20c,0x1ec,0x1c8,0x1b8,0x184,0x180]
    names = ['', '', '__EAGL::TAR:::RUNTIME_ALLOC::UID=1;SHAPENAME=1,1;',
             '__EAGL::GeoPrimState:::RUNTIME_ALLOC::UID=1;;', 'SharedShader']
    symbols = [[0,0,0,0,0,0], [0,0,0,3,0,1]]
    strings = bytearray(b'\0')
    for name in names[2:]:
        symbols.append([len(strings),0,0,0x10,0,0]); strings.extend(name.encode() + b'\0')
    for name, value in [('__Model:::2',0x378),('__BBOX:::2',0x230),('__VB:::__GPvb_9_0_2',0xa0),
                        ('__RM:::__GP_RM_2_0',0x19c),('__EAGL_TOOLLIB_VERSION:::EAGL_TOOLLIB_VERSION-4',0)]:
        symbols.append([len(strings),value,4,0x10,0,1]); strings.extend(name.encode() + b'\0')
    rel = []
    for at, target in local:
        struct.pack_into('<I',data,at,target); rel.append((at,1 << 8 | 2))
    rel.extend((at,(2 if i < 2 else 3 if i < 4 else 4) << 8 | 2) for i,at in enumerate(imports))
    section_names = bytearray(b'\0'); offsets = [0]
    for name in ('.data','.rel.data','.shstrtab','.symtab','.strtab'):
        offsets.append(len(section_names));section_names.extend(name.encode() + b'\0')
    parts = [b'',data,b''.join(struct.pack('<II',*r) for r in rel),section_names,
             b''.join(struct.pack('<IIIBBH',*s) for s in symbols),strings]
    output = bytearray(b'\x7fELF\x01\x01\x01' + bytes(9) + bytes(36));rows = [(0,)*10]
    for i in range(1,6):
        output.extend(bytes(-len(output)%4)); at=len(output);output.extend(parts[i])
        rows.append((offsets[i],(0,1,9,3,2,3)[i],3 if i==1 else 0,0,at,len(parts[i]),
                     4 if i==2 else 5 if i==4 else 0,1 if i==2 else 2 if i==4 else 0,4,8 if i==2 else 16 if i==4 else 0))
    output.extend(bytes(-len(output)%4));at=len(output);output.extend(b''.join(struct.pack('<10I',*r) for r in rows))
    struct.pack_into('<HHIIIIIHHHHHH',output,16,1,8,1,0,0,at,0x20924000,52,0,0,40,6,3)
    result=bytes(output);return UIModel(result,hashlib.sha256(result).hexdigest())


def movie_fixture(grid=False):
    data=bytearray(2560 if grid else 160);data[:8]=b'Apt Data'
    struct.pack_into('<II',data,24,9,0x09876543)
    struct.pack_into('<II',data,44,3,80)
    struct.pack_into('<3I',data,80,24,92,132 if grid else 104)
    struct.pack_into('<III',data,92,7,0x09876543,1)
    struct.pack_into('<II4fI',data,104,1,0x09876543,0.,0.,44.,44.,2)
    if grid:
        struct.pack_into('<3I',data,8,1,64,2);data[64:73]=b'thumbAll\0'
        struct.pack_into('<4I',data,132,5,0x09876543,300,160)
    return bytes(data)


def test_static_model_clones_own_symbols_and_every_image_name_consumer():
    destination,source=model_fixture(),model_fixture()
    original_data=bytes(destination.parts[1]);original_symbols=destination.symbols[:];original_relocations=destination.relocations[:]
    bases=[destination.append_drawable(source,900,901),destination.append_drawable(source,902,903)]
    data=destination.compose();parsed=UIModel(data,hashlib.sha256(data).hexdigest())
    assert parsed.parts[1][:len(original_data)]==original_data
    assert parsed.symbols[:len(original_symbols)]==original_symbols
    assert parsed.relocations[:len(original_relocations)]==original_relocations
    for base,model_id,image_id in zip(bases,(900,902),(901,903)):
        assert parsed.exports[f'__Model:::{model_id}']==base+0x378
        for at in (0x25c,0x32c):assert parsed.string(1,parsed.pointers[base+at][1])==str(image_id)
        assert parsed.string(1,parsed.pointers[base+0x42c][1])==str(model_id)
        assert parsed.string(1,parsed.pointers[base+0x310][1])==f'ScaleMatrix::{image_id}::TextureMatrix'
        assert parsed.pointers[base+0x334][0]==parsed.pointers[base+0x1e4][0]
        assert f'SHAPENAME={image_id},1;' in parsed.names[parsed.pointers[base+0x334][0]]
    assert parsed.pointers[bases[0]+0x334][0]!=parsed.pointers[bases[1]+0x334][0]
    assert sum(n=='__EAGL_TOOLLIB_VERSION:::EAGL_TOOLLIB_VERSION-4' for n in parsed.names)==1
    with pytest.raises(AssetError,match='colliding'):
        destination.append_drawable(source,900,905)
    with pytest.raises(AssetError,match='verified'):
        UIModel(source.data,'0'*64)


def test_static_grid_keeps_original_frames_and_adds_noncolliding_states(monkeypatch):
    movie=movie_fixture(True);source=movie_fixture()
    monkeypatch.setattr(apt,'parse_const',lambda _: (24,[]))
    texture=UITextures(ui());model=model_fixture()
    result,geometry,images=append_grid(movie,b'',model,texture,{300:(source,model_fixture(),texture)})
    count,frames=struct.unpack_from('<II',result,140)
    assert count==450 and result[frames:frames+2400]==movie[160:2560]
    selected=struct.unpack_from('<II',result,frames+300*8)
    ordinary=struct.unpack_from('<II',result,frames+449*8)
    assert selected[0]==ordinary[0]==2 and selected[1]!=ordinary[1]
    assert not set(struct.unpack_from('<II',result,selected[1])) & set(struct.unpack_from('<II',result,ordinary[1]))
    sprite=apt.parse_character(result,132)
    items=sprite['frames'][300];assert [kind for kind,_ in items]==['Action','PlaceObject']
    assert items[1]==sprite['frames'][449][1]
    assert items[1][1]['matrix']==pytest.approx((37/44,0,0,37/44,-18.5,-18.5))
    assert items[1][1]['character']==4
    assert items[1][1]['flags']==7
    assert items[1][1]['clip_depth']==-1
    _,pointers=struct.unpack_from('<II',result,frames+300*8)
    placement=struct.unpack_from('<I',result,pointers+4)[0]
    assert struct.unpack_from('<6I',result,placement+40)==(0xffffffff,0,0,0,0xffffffff,0)
    parsed=UITextures(images);assert len(parsed.images)==2
    old,new=parsed.images
    assert new['pixels_offset']%128==texture.images[0]['pixels_offset']%128
    assert parsed.data[old['pixels_offset']:old['pixels_offset']+old['pixels_bytes']]==ui()[texture.images[0]['pixels_offset']:texture.images[0]['pixels_offset']+old['pixels_bytes']]
    assert new['name'].strip()=='3'
    UIModel(geometry,hashlib.sha256(geometry).hexdigest())
    with pytest.raises(AssetError,match='frames collide'):
        append_grid(movie,b'',model_fixture(),texture,{300:(source,model_fixture(),texture),449:(source,model_fixture(),texture)})


def test_grid_rejects_image_namespace_overflow_and_index_mismatch(monkeypatch):
    monkeypatch.setattr(apt, 'parse_const', lambda _: (24, []))
    texture = UITextures(ui())
    template = (movie_fixture(), model_fixture(), texture)
    movie = bytearray(movie_fixture(True))
    chars = len(movie)
    movie.extend(movie[80:92] + bytes(4 * (2000 - 3)))
    struct.pack_into('<II', movie, 44, 2000, chars)
    with pytest.raises(AssetError, match='four-digit UI image namespace'):
        append_grid(bytes(movie), b'', model_fixture(), texture,
                    {300 + (i // 149) * 300 + i % 149: template for i in range(4096)})
    model = model_fixture()
    model.append_drawable(model_fixture(), 500, 499)
    with pytest.raises(AssetError, match='APT character indices'):
        append_grid(movie_fixture(True), b'', model, texture, {300: template})


def selected_model_fixture():
    model=model_fixture();start=0xF450
    model.parts[1]=bytearray(bytes(start)+model.parts[1])
    for at,(_,target) in model.pointers.items():
        if target is not None:struct.pack_into('<I',model.parts[1],start+at,start+target)
    model.relocations=[(start+at,info) for at,info in model.relocations]
    for row in model.symbols:
        if row[5]==1 and row[3]>>4 and not model.names[model.symbols.index(row)].startswith('__EAGL_TOOLLIB'):
            row[1]+=start
    data=model.compose();return UIModel(data,hashlib.sha256(data).hexdigest())


def test_selected_grid_closure_rebases_all_relocations_and_two_independent_states(monkeypatch):
    selected=selected_model_fixture().selected_grid(2)
    assert selected._grid_profile==(16,2,1)
    assert len(selected.parts[1])==1136 and len(selected.relocations)==42
    assert selected.exports['__Model:::2']==16+0x378
    destination=model_fixture();base=destination.append_drawable(selected,900,901)
    data=destination.compose();parsed=UIModel(data,hashlib.sha256(data).hexdigest())
    assert parsed.string(1,parsed.pointers[base+16+0x310][1])=='ScaleMatrix::901::TextureMatrix'
    # These native Model fields are consumed even when no optional patch list
    # exists. Appended identity strings must never become their pointers.
    model_at=parsed.exports['__Model:::900']
    assert parsed.parts[1][model_at+0xD0:model_at+0xE0]==bytes(16)
    assert model_at+0xE0<=base+len(selected.parts[1])
    monkeypatch.setattr(apt,'parse_const',lambda _: (24,[]))
    source=bytearray(movie_fixture());struct.pack_into('<4f',source,112,-18.5,-18.5,18.5,18.5)
    normal=UITextures(ui());changed=bytearray(ui());image=normal.images[0]
    changed[image['pixels_offset']:image['pixels_offset']+image['pixels_bytes']]=bytes([55])*image['pixels_bytes']
    states=GridStates(bytes(source),b'',selected_model_fixture(),2,normal,UITextures(bytes(changed)))
    result,geometry,rasters=append_grid(movie_fixture(True),b'',model_fixture(),normal,{300:states})
    frames=apt.parse_character(result,132)['frames']
    assert frames[300][1][1]['character']==4 and frames[449][1][1]['character']==6
    assert frames[300][1][1]['matrix']==(1.,0.,0.,1.,0.,0.)
    assert frames[449][1][1]['matrix']==(1.,0.,0.,1.,0.,0.)
    images=UITextures(rasters)
    assert len(images.images)==3
    # Frame301 is reached by selectChar(token+1), frame450 by redraw and
    # deselectChar(token+150). Independently authored colors must follow them.
    assert [images.data[x['pixels_offset']] for x in images.images[-2:]]==[55,ui()[image['pixels_offset']]]
    UIModel(geometry,hashlib.sha256(geometry).hexdigest())


def test_selected_grid_rejects_truncated_or_changed_native_model_tail():
    original=selected_model_fixture()
    original.parts[1]=original.parts[1][:-24]
    with pytest.raises(AssetError,match='closure'):original.selected_grid(2)
    original=selected_model_fixture();original.parts[1][0xF450+0x448]=1
    with pytest.raises(AssetError,match='tail'):original.selected_grid(2)
