"""Invented indexed textures prove RGB import and exact material-alpha holds."""
import hashlib
import io
import struct
import sys
from pathlib import Path
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
from fighter_appearance_png import paint,native_identity
from fighter_appearance_authoring import raster,morton,surface_triangles
from fighter_xsh import Textures
from test_fighter_xsh import texture
from test_fighter_appearance import fixture as appearance_fixture
from fighter_appearance import Appearance
from fighter_resource_files import read_appearance
from fighter_ui_hd import compile_hd


def source():
    raw=bytearray(texture(width=32,height=32));tile=Textures(bytes(raw)).images[0]
    raw[tile['palette_offset']+3]=34;raw[tile['palette_offset']+7]=221
    at=tile['pixels_offset']
    for y in range(32):
        for x in range(32):raw[at+morton(x,y,32,32)]=(x+y)%2
    return bytes(raw)


def png(image):
    stream=io.BytesIO();image.save(stream,format='PNG');return stream.getvalue()


def test_indexed_quantization_preserves_every_native_alpha_and_hd_source_rgb():
    raw=source();original=Textures(raw);tile=original.images[0];before=raster(original,tile)
    art=Image.new('RGB',(128,128),(240,50,20));data=png(art);spec={'TEST':{'path':'art.png','sha256':hashlib.sha256(data).hexdigest()}}
    rebuilt,hd,receipt=paint(raw,spec,{'TEST':data});after=Textures(rebuilt);now=raster(after,after.images[0])
    assert original.controls==after.controls and now.getchannel('A').tobytes()==before.getchannel('A').tobytes()
    assert now.getpixel((10,10))[:3]==(240,50,20)
    identity=native_identity(after,after.images[0]);assert set(hd)=={identity}
    image=Image.open(io.BytesIO(hd[identity]));assert image.size==(128,128) and image.getpixel((40,40))[:3]==(240,50,20)
    assert image.getchannel('A').tobytes()==before.getchannel('A').resize((128,128),Image.Resampling.NEAREST).tobytes()
    assert receipt['TEST']['alpha']=='original-exact'
    t=after.images[0];pixels=rebuilt[t['pixels_offset']:t['pixels_offset']+t['pixels_bytes']];palette=rebuilt[t['palette_offset']:t['palette_offset']+t['palette_entries']*4]
    assert identity==hashlib.sha256(b'XRTEX01\0'+struct.pack('<5I',0x0b,32,32,2,32)+pixels+palette).hexdigest()


def test_exact_original_native_import_is_a_byte_identical_noop():
    raw=source();t=Textures(raw);image=raster(t,t.images[0]);data=png(image)
    rebuilt,hd,_=paint(raw,{'TEST':{'path':'original.png','sha256':hashlib.sha256(data).hexdigest()}},{'TEST':data})
    assert rebuilt==raw and hd=={}


@pytest.mark.parametrize('size',[(33,32),(64,32),(96,96),(16,16)])
def test_invalid_atlas_dimensions_refused(size):
    data=png(Image.new('RGB',size));spec={'TEST':{'path':'a.png','sha256':hashlib.sha256(data).hexdigest()}}
    with pytest.raises(ValueError):paint(source(),spec,{'TEST':data})


def test_hash_changed_and_unknown_shape_refused():
    data=png(Image.new('RGB',(32,32)))
    with pytest.raises(ValueError,match='hash'):paint(source(),{'TEST':{'path':'a.png','sha256':'0'*64}},{'TEST':data})
    with pytest.raises(ValueError,match='unknown'):paint(source(),{'NOPE':{'path':'a.png','sha256':hashlib.sha256(data).hexdigest()}},{'NOPE':data})


def test_collapsed_source_placeholders_do_not_expand_preview_bounds():
    positions=[(0,-1000,0)]*3+[(0,0,0),(1,0,0),(0,1,0)]
    indices=surface_triangles(positions,[0,1,2,2,3,3,4,5])
    assert set(indices)=={3,4,5}
    assert surface_triangles([(0,0,0),(1,0,0),(2,0,0)],[0,1,2])==[]


def test_hash_bound_png_appearance_compiles_through_existing_template_and_hd_layer(tmp_path):
    baseline,spec,assets,_=appearance_fixture()
    assets['textures']=source();spec['textures']['sha256']=hashlib.sha256(assets['textures']).hexdigest()
    data=png(Image.new('RGB',(128,128),(130,70,30)))
    spec.update(format='eagl-appearance-png-1',images={'TEST':{'path':'art.png','sha256':hashlib.sha256(data).hexdigest()}},shape_names={'TEST':'N123'})
    for part,raw in assets.items():(tmp_path/spec[part]['path']).write_bytes(raw)
    (tmp_path/'art.png').write_bytes(data)
    parsed=read_appearance(tmp_path,spec)
    appearance=Appearance('synthetic/body',spec,parsed,baseline,'SyntheticModel')
    assert appearance.summary['png_import']['TEST']['alpha']=='original-exact'
    assert set(appearance.texture_shapes)=={'N123'}
    files,hashes=compile_hd({'synthetic/body':appearance})
    assert len(files)==2 and set(files)==set(hashes) and 'fighter-ui-hd/manifest.ini' in files
