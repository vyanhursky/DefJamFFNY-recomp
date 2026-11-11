"""HD CAF import, fallbacks, version gating and sealed sidecar composition."""
import hashlib
import io
from pathlib import Path
import struct
from types import SimpleNamespace
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
import pytest
from PIL import Image
from fighter_caf_extras import load
from fighter_caf_hd import encode,ROW
from fighter_packages import runtime_environment


@pytest.mark.parametrize('edge',[512,1024,2048])
def test_hd_import_retains_detail_and_native_fallback(tmp_path,edge):
    image=Image.new('RGBA',(edge,edge),(11,22,33,0))
    image.putpixel((edge//2,edge//2),(99,77,55,0))
    stream=io.BytesIO();image.save(stream,format='PNG');raw=stream.getvalue()
    (tmp_path/'a.png').write_bytes(raw)
    value={'atlases':{'a':{'path':'a.png','sha256':hashlib.sha256(raw).hexdigest()}}}
    with pytest.raises(ValueError,match='HD requires'):load(tmp_path,value,None)
    extra=load(tmp_path,value,None,hd=True)
    assert len(extra['atlases']['a'])==256*256*4
    assert extra['atlases']['a'][:4]==bytes((33,22,11,255))
    block=extra['hd_atlases']['a'];assert struct.unpack_from('<I',block)[0]==edge
    at=4+((edge//2)*edge+edge//2)*4
    assert block[at:at+4]==bytes((55,77,99,255))
    entry={'pack/fighter':{'outfits':[{'extras':extra},{'extras':extra}]}}
    report={'bindings':{'pack/fighter':{'selection_key':100}}}
    sidecar=encode(entry,report)
    assert struct.unpack_from('<4I',sidecar,0)[1:]==(1,2,ROW)
    first=struct.unpack_from('<8I',sidecar,16);second=struct.unpack_from('<8I',sidecar,16+ROW)
    assert first[:2]==(100,0) and second[:2]==(100,1) and first[2]==second[2]==16+2*ROW
    assert sidecar[first[2]:]==block


def test_hd_environment_is_explicit_and_bound_to_hash(tmp_path):
    env=runtime_environment(tmp_path,{'caf_hd_sha256':'a'*64},tmp_path/'screens')
    assert env['RECOMP_FIGHTER_CAF_HD']==str(tmp_path/'fighter-caf-hd.bin')
    assert env['RECOMP_FIGHTER_CAF_HD_SHA256']=='a'*64
    assert 'RECOMP_FIGHTER_CAF_HD' not in runtime_environment(tmp_path,{},tmp_path/'screens')


def test_hd_encoder_refuses_bad_blocks_and_budget(monkeypatch):
    import fighter_caf_hd
    report={'bindings':{'a/b':{'selection_key':100}}}
    def entry(block):return {'a/b':{'extras':{'hd_atlases':{'a':block}}}}
    with pytest.raises(ValueError,match='dimensions'):encode(entry(struct.pack('<I',999)+bytes(8)),report)
    block=struct.pack('<I',512)+bytes(512*512*4)
    monkeypatch.setattr(fighter_caf_hd,'MAX_BYTES',1024)
    with pytest.raises(ValueError,match='budget'):encode(entry(block),report)
    assert encode({'a/b':{'extras':{'atlases':{}}}},report) is None
    assert encode({'a/b':{'extras':None}},report) is None
