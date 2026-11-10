import copy
import hashlib
import json
from pathlib import Path
import struct
import sys

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
from fighter_caf_face import validate,load,encode,MESHES,ROW
from fighter_packages import runtime_environment


def fixture():
    recipe={'caf_values':[0,0,0,0,0,1,1,1,1,1,1,1]+[0]*26}
    meshes=[]
    for rm,n in MESHES:
        meshes.append(dict(rm=rm,positions=[[0.,19.+i/n,1.] for i in range(n)],deltas=[[0.,0.,0.] if i<n*.15 else [.1,0.,0.] for i in range(n)]))
    return dict(schema='caf-face-coordinates-1',template_sha256='a'*64,basis=[0,1,1,1,1,1],meshes=meshes),recipe


def test_face_descriptor_and_compiled_rows_are_bounded_hash_bound_and_outfit_specific(tmp_path):
    value,recipe=fixture();raw=json.dumps(value).encode();(tmp_path/'face.json').write_bytes(raw)
    spec=dict(path='face.json',sha256=hashlib.sha256(raw).hexdigest())
    assert load(tmp_path,spec,recipe)==value
    entries={'example/fighter':dict(outfits=[dict(recipe=recipe,face=value),dict(recipe=recipe)])}
    report={'bindings':{'example/fighter':{'selection_key':100}}}
    result=encode(entries,report)
    assert len(result)==16+ROW
    assert struct.unpack_from('<4sIII',result)==(b'FCS1',1,1,ROW)
    assert struct.unpack_from('<8I',result,16)==(100,0,0,1,1,1,1,1)
    spec['sha256']='0'*64
    with pytest.raises(ValueError,match='hash'):load(tmp_path,spec,recipe)


@pytest.mark.parametrize('mutate',[
    lambda v:v.update(extra='untrusted'),lambda v:v['basis'].__setitem__(0,1),
    lambda v:v['meshes'][0].update(rm=8),lambda v:v['meshes'][0]['positions'].pop(),
    lambda v:v['meshes'][0]['deltas'][20].__setitem__(0,float('nan')),
    lambda v:v['meshes'][0]['deltas'][20].__setitem__(0,.601),
    lambda v:v['meshes'][0]['deltas'][0].__setitem__(0,.1),
    lambda v:v['meshes'][0]['positions'][20].__setitem__(1,200),
])
def test_invalid_sculpts_refuse_before_native_admission(mutate):
    value,recipe=fixture();mutate(value)
    with pytest.raises(ValueError):validate(value,recipe)


def test_face_setting_is_projected_for_managed_launch(tmp_path):
    env=runtime_environment(tmp_path,{'caf_faces_sha256':'b'*64},tmp_path/'screens.viv')
    assert env['RECOMP_FIGHTER_CAF_FACES']==str(tmp_path/'fighter-caf-faces.bin')
    assert env['RECOMP_FIGHTER_CAF_FACES_SHA256']=='b'*64
