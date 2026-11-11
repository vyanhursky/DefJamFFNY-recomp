"""HD CAF import, native fallbacks and the sealed hd section of the container."""
import hashlib
import io
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
import pytest
from PIL import Image
from fighter_caf_extras import load
from fighter_caf_hd import encode_section
import fighter_caf_layout as layout
from fighter_packages import runtime_environment


@pytest.mark.parametrize('edge',[512,1024,2048])
def test_hd_import_retains_detail_and_native_fallback(tmp_path,edge):
    image=Image.new('RGBA',(edge,edge),(11,22,33,0))
    image.putpixel((edge//2,edge//2),(99,77,55,0))
    stream=io.BytesIO();image.save(stream,format='PNG');raw=stream.getvalue()
    (tmp_path/'a.png').write_bytes(raw)
    value={'atlases':{'a':{'path':'a.png','sha256':hashlib.sha256(raw).hexdigest()}}}
    extra=load(tmp_path,value,None)  # HD sizes are part of the one recipe format
    assert len(extra['atlases']['a'])==256*256*4
    assert extra['atlases']['a'][:4]==bytes((33,22,11,255))
    block=extra['hd_atlases']['a'];assert struct.unpack_from('<I',block)[0]==edge
    at=4+((edge//2)*edge+edge//2)*4
    assert block[at:at+4]==bytes((55,77,99,255))
    entry={'pack/fighter':{'outfits':[{'extras':extra},{'extras':extra}]}}
    report={'bindings':{'pack/fighter':{'selection_key':100}}}
    count,section=encode_section(entry,report)
    assert count==2
    first=struct.unpack_from('<2I6I',section,0);second=struct.unpack_from('<2I6I',section,layout.HD_STRIDE)
    assert first[:2]==(100,0) and second[:2]==(100,1)
    # Both outfits share one block, which follows the rows and is addressed from the section start.
    assert first[2]==second[2]==2*layout.HD_STRIDE and first[3:]==(0,)*5
    assert section[first[2]:]==block


def test_native_256_atlas_has_no_hd_block(tmp_path):
    raw=io.BytesIO();Image.new('RGBA',(256,256),(1,2,3,4)).save(raw,format='PNG');raw=raw.getvalue()
    (tmp_path/'a.png').write_bytes(raw)
    extra=load(tmp_path,{'atlases':{'a':{'path':'a.png','sha256':hashlib.sha256(raw).hexdigest()}}},None)
    assert 'hd_atlases' not in extra and encode_section({'a/b':{'extras':extra}},{'bindings':{'a/b':{'selection_key':100}}})==(0,b'')


def test_unsupported_atlas_sizes_are_refused(tmp_path):
    for size in ((128,128),(768,768),(512,256)):
        raw=io.BytesIO();Image.new('RGBA',size,(1,2,3,4)).save(raw,format='PNG');raw=raw.getvalue()
        (tmp_path/'a.png').write_bytes(raw)
        with pytest.raises(ValueError,match='square 256'):
            load(tmp_path,{'atlases':{'a':{'path':'a.png','sha256':hashlib.sha256(raw).hexdigest()}}},None)


def test_hd_travels_in_the_one_container_environment(tmp_path):
    env=runtime_environment(tmp_path,{'caf_fighters':{'a/b':{}},'caf_sha256':'a'*64},tmp_path/'screens')
    assert env['RECOMP_FIGHTER_CAF']==str(tmp_path/'fighter-caf.bin')
    assert not [name for name in env if 'CAF_HD' in name]


def test_hd_encoder_refuses_bad_blocks_and_budget(monkeypatch):
    import fighter_caf_hd
    report={'bindings':{'a/b':{'selection_key':100}}}
    def entry(block):return {'a/b':{'extras':{'hd_atlases':{'a':block}}}}
    with pytest.raises(ValueError,match='dimensions'):encode_section(entry(struct.pack('<I',999)+bytes(8)),report)
    block=struct.pack('<I',512)+bytes(512*512*4)
    monkeypatch.setattr(fighter_caf_hd,'HD_MAX_BYTES',1024)
    with pytest.raises(ValueError,match='budget'):encode_section(entry(block),report)
    assert encode_section({'a/b':{'extras':{'atlases':{}}}},report)==(0,b'')
    assert encode_section({'a/b':{'extras':None}},report)==(0,b'')
