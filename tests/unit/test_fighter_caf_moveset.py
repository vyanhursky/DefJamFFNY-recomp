import copy
from types import SimpleNamespace
import struct
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
from fighter_caf import encode
from fighter_caf_moveset import load_recipe
from test_fighter_caf_outfits import fixture


def test_retail_moveset_resolves_verified_core_and_preserves_recipe_data(monkeypatch):
    value={'retail_moveset':'retail/blaze','outfits':[]}
    catalog=SimpleNamespace(rows={'retail/blaze':dict(native_binding=dict(core_id=5),fields={'FightingStyle':dict(word=8)},record_offset=0)},db=SimpleNamespace(word=lambda _:8))
    original={'core':109,'recipe':{'styles':[2]},'outfits':[{'recipe':{'styles':[2]}}]}
    import fighter_caf_face
    monkeypatch.setattr(fighter_caf_face,'load_recipe',lambda *args:copy.deepcopy(original))
    result=load_recipe(None,value,catalog,None)
    assert result['core']==5 and result['retail_styles']==[3] and result['recipe']==original['recipe']
    assert value['retail_moveset']=='retail/blaze'
    for bad in ('retail/missing',99,None):
        with pytest.raises(ValueError):load_recipe(None,dict(value,retail_moveset=bad),catalog,None)
    catalog.rows['retail/blaze']['native_binding']['core_id']=142
    with pytest.raises(ValueError):load_recipe(None,value,catalog,None)


def test_fca3_explicitly_marks_retail_core_and_keeps_old_rows_compatible():
    item,report=fixture();item.update(core=51,retail_moveset='retail/d-mob')
    data=encode({'example/fighter':item},report)
    assert struct.unpack_from('<4sIII',data)==(b'FCA3',3,3,240)
    assert struct.unpack_from('<I',data,20)==(51,)
    assert all(data[16+i*240+225]==1 for i in range(3))
