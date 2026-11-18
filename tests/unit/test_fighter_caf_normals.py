import copy
import struct
import pytest
from test_fighter_caf_face import fixture
from fighter_caf_face import validate, encode_normals
from fighter_caf import encode
import fighter_caf_layout as layout


def normal_fixture():
    face, recipe = fixture()
    face.update(schema='caf-face-coordinates-2', neck_normals=[dict(slot=3,rm=0,vertex=1,position=[0.,19.5,1.],original=1023,replacement=1023<<11)])
    return face,recipe


def normal_entries():
    face,recipe=normal_fixture()
    recipe.update(stats=dict.fromkeys(('upper','lower','speed','toughness','health'),10),styles=[0],caf_colors=[0]*38)
    return {'a/b':dict(core=87,audio_core=5,recipe=recipe,extras=None,outfits=[dict(recipe=recipe,face=face)])},{'bindings':{'a/b':{'selection_key':100}}}


def test_version2_records_bind_outfit_and_preserve_legacy_container_bytes():
    entries,report=normal_entries()
    raw=encode(entries,report);header=layout.unpack_header(raw)
    assert struct.unpack_from('<I',raw,4)==(2,)
    assert header['normals_count']==1
    assert len(raw)-header['normals_offset']==layout.NORMAL_STRIDE
    assert layout.split(raw) is not None
    words=struct.unpack_from('<5I3f2I',raw,header['normals_offset'])
    assert words==(100,0,3,0,1,0.,19.5,1.,1023,1023<<11)
    face=entries['a/b']['outfits'][0]['face']
    face.pop('neck_normals');face['schema']='caf-face-coordinates-1'
    legacy=encode(entries,report)
    assert legacy[4:8]==struct.pack('<I',1) and legacy[52:64]==bytes(12)
    assert len(legacy)==header['normals_offset']


@pytest.mark.parametrize('mutate',[
    lambda v:v['neck_normals'].append(copy.deepcopy(v['neck_normals'][0])),
    lambda v:v['neck_normals'][0].update(slot=2),
    lambda v:v['neck_normals'][0].update(vertex=True),
    lambda v:v['neck_normals'][0].update(original=0),
    lambda v:v['neck_normals'][0].update(replacement=2**32),
    lambda v:v['neck_normals'][0].update(position=[0,float('nan'),1]),
    lambda v:v['neck_normals'][0].update(extra='untrusted'),
])
def test_invalid_normal_corrections_are_rejected_before_compilation(mutate):
    value,recipe=normal_fixture();mutate(value)
    with pytest.raises(ValueError):validate(value,recipe)
