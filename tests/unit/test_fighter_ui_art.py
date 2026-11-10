"""Invented PNG/SHPX fixtures exercise role routing, pixel holds and HD receipts."""
import hashlib
import io
import struct
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'setup'))
from fighter_ui_art import FORMAT,MASTERS,validate,native_hash,render
from fighter_ui_hd import compile_hd,stage,validate_hd_files
from fighter_portrait import PortraitBaseline,Portrait,UITextures,variant_path
from fighter_resource_files import PORTRAIT_ALL_PARTS,PORTRAIT_EXTENDED_PARTS,read_portrait
from fighter_archive import store
from test_fighter_archive import fixture


def png(color=(220,80,20,255)):
    out=io.BytesIO();Image.new('RGBA',(32,32),color).save(out,format='PNG');return out.getvalue()


def spec(roles=('selector',)):
    return {'format':FORMAT,'donor':'retail/test-alpha','hd_scale':4,'images':{
        role:{'path':role+'.png','sha256':hashlib.sha256(png()).hexdigest()} for role in roles}}


def texture(name=1):
    # One8x8 DXT5 raster, followed by its original numeric material attachment.
    data=bytearray(208);data[:4]=b'SHPX';struct.pack_into('<II',data,4,len(data),1)
    struct.pack_into('<4sI',data,16,str(name).ljust(4).encode(),112)
    struct.pack_into('<IHHII',data,112,0x62|(80<<8),8,8,0,0)
    data[192]=0x70;data[196:200]=str(name).encode().ljust(4,b'\0')
    return bytes(data)


@pytest.fixture
def baseline(monkeypatch):
    entries={}
    for part in PORTRAIT_EXTENDED_PARTS:
        path,stem=variant_path(part,1)
        entries[path]=store(fixture({stem+'.apt':b'original actions',stem+'.const':b'original constants',
                                     stem+'.o':b'invented geometry stub',stem+'.xsh':texture()}))
    for count in (2,3,4):
        stem=f'chooseF{count}'
        entries[f'screens/battle/{stem}.big']=store(fixture({stem+'.xsh':texture(1 if count==2 else 3)}))
    raw=fixture(entries)
    # Geometry decoding is qualified separately. Feed a single known rectangle
    # to the real pixel/HD encoders and native-control-preserving compiler here.
    import fighter_ui_model,fighter_caf_portrait
    monkeypatch.setattr(fighter_ui_model,'UIModel',lambda *args:None)
    monkeypatch.setattr(fighter_caf_portrait,'tiles',lambda model,tex:{int(t['name']):{
        'bounds':(0,0,8,8),'logical':(8,8),'image':t} for t in tex.images})
    return PortraitBaseline(raw,hashlib.sha256(raw).hexdigest())


def test_full_png_source_routes_every_role_and_retains_original_controls(baseline):
    source=spec(MASTERS);files={role:png() for role in MASTERS}
    portrait=Portrait('example/ui',source,files,baseline,1,64*1024**2)
    assert len(portrait.summary['variants'])==24 and portrait.source_sha256
    assert set(portrait.summary['png_import'])==set(PORTRAIT_ALL_PARTS)
    assert portrait.summary['png_import']['loading_logo_3p']['source']=='titlecard'
    assert portrait.summary['png_import']['result_4p']['source']=='icon'
    assert portrait.summary['png_import']['grid_selected_2p']['source']=='grid_selected'
    for raw in portrait.hd_images.values():
        with Image.open(io.BytesIO(raw)) as image:
            assert image.size==(32,32) and image.getpixel((16,16))==(220,80,20,255)
    assert len(portrait.hd_images)==1  # Same native bytes/shareable art, one HD PNG.
    native,_,_=render(source,files,baseline,1)
    original=UITextures(texture())
    for raw in native.values():
        assert UITextures(raw).controls==original.controls
        tile=UITextures(raw).images[0];start,size=tile['pixels_offset'],tile['pixels_bytes']
        assert raw[:start]==texture()[:start] and raw[start+size:]==texture()[start+size:]


def test_specific_variant_overrides_master_and_native_only_omits_hd(baseline):
    source=spec(MASTERS);source['images']['selector_3p']={'path':'override.png','sha256':hashlib.sha256(png((0,255,0,255))).hexdigest()}
    files={role:png() for role in MASTERS};files['selector_3p']=png((0,255,0,255))
    _,hd,receipt=render(source,files,baseline,1)
    assert receipt['selector_3p']['source']=='selector_3p' and receipt['selector_2p']['source']=='selector'
    assert len(hd)==2
    source['hd_scale']=1;assert render(source,files,baseline,1)[1]=={}


def test_grid_fits_original_used_region_and_keeps_power_of_two_padding(baseline,monkeypatch):
    original=texture();data=bytearray(original+bytes(16))
    struct.pack_into('<I',data,4,len(data))
    data[208:224]=original[192:208]
    struct.pack_into('<4I',data,192,0x107c,1,6,5)
    monkeypatch.setattr(baseline,'grid_template',lambda part:bytes(data))
    source=spec(('grid_normal','grid_selected'))
    native,hd,receipt=render(source,{role:png() for role in source['images']},baseline,1)
    tile=UITextures(native['grid_normal_2p']).images[0]
    picture=Image.open(io.BytesIO(hd[receipt['grid_normal_2p']['tiles'][0]['native_id']]))
    assert picture.size==(32,32) and picture.getbbox()==(0,0,24,20)
    assert picture.getpixel((12,10))==(220,80,20,255)
    assert UITextures(native['grid_normal_2p']).controls==UITextures(bytes(data)).controls


@pytest.mark.parametrize('damage',[
    lambda s:s.update(commands=['execute']),lambda s:s.update(hd_scale=True),lambda s:s.update(hd_scale=8),
    lambda s:s['images'].update(unknown={'path':'x.png','sha256':'a'*64}),
    lambda s:s['images']['selector'].update(path='../outside.png'),
])
def test_png_contract_rejects_unknown_or_unbounded_data(damage):
    source=spec();damage(source)
    with pytest.raises(ValueError):validate(source)


def test_png_reader_hashes_original_bytes_and_deduplicates_shared_files(tmp_path):
    source=spec();(tmp_path/'selector.png').write_bytes(png())
    source['images']['loading']=source['images']['selector'].copy()
    files=read_portrait(tmp_path,source,len(png()))
    assert files['selector'] is files['loading']
    (tmp_path/'selector.png').write_bytes(png((10,20,30,255)))
    with pytest.raises(ValueError,match='hash mismatch'):read_portrait(tmp_path,source)


def test_png_dimensions_transparency_and_input_digest_fail_closed(baseline):
    source=spec()
    with pytest.raises(ValueError,match='hash changed'):render(source,{'selector':png((1,2,3,255))},baseline,1)
    raw=png((0,0,0,0));source['images']['selector']['sha256']=hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError,match='transparent'):render(source,{'selector':raw},baseline,1)


def test_native_texture_hash_matches_existing_census():
    sys.path.insert(0,str(ROOT/'scripts'))
    from hd_assets import texture_id
    data=texture();parsed=UITextures(data);tile=parsed.images[0]
    assert native_hash(parsed,tile)==texture_id(0x0f,8,8,data[128:192])


def test_hd_pack_is_content_addressed_verified_and_never_overwrites_changed_cache(tmp_path):
    identity='a'*64;portrait=SimpleNamespace(hd_images={identity:png()})
    files,hashes=compile_hd({'example/ui':portrait});report={'portrait_hd_files':hashes}
    assert validate_hd_files(report,files)==set(files)
    cache=tmp_path/'cache'
    for relative,raw in files.items():
        path=cache/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    folder=stage(cache,report,tmp_path/'mods');assert folder.name.startswith('fighter-ui-')
    assert stage(cache,report,tmp_path/'mods')==folder
    image=folder/'textures'/(identity+'.png');image.write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed'):stage(cache,report,tmp_path/'mods')
    assert image.read_bytes()==b'changed'
    conflict=SimpleNamespace(hd_images={identity:png((1,2,3,255))})
    with pytest.raises(ValueError,match='Conflicting'):compile_hd({'a':portrait,'b':conflict})
