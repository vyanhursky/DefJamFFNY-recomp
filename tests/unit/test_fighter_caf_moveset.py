import copy
from types import SimpleNamespace
import struct
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
from fighter_caf import encode_rows
from fighter_caf_layout import RECIPE as R, RECIPE_STRIDE
from fighter_caf_moveset import load_recipe
from test_fighter_caf_outfits import fixture


def test_retail_moveset_resolves_verified_core_and_preserves_recipe_data(monkeypatch):
    value={'retail_moveset':'retail/blaze','outfits':[]}
    catalog=SimpleNamespace(rows={'retail/blaze':dict(native_binding=dict(core_id=5),fields={'FightingStyle':dict(word=8)},record_offset=0)},db=SimpleNamespace(word=lambda _:8))
    original={'core':109,'recipe':{'styles':[2]},'outfits':[{'recipe':{'styles':[2]}}]}
    import fighter_caf_face
    monkeypatch.setattr(fighter_caf_face,'load_recipe',lambda *args,**kwargs:copy.deepcopy(original))
    result=load_recipe(None,value,catalog,None)
    assert result['core']==5 and result['retail_styles']==[3] and result['recipe']==original['recipe']
    assert value['retail_moveset']=='retail/blaze'
    for bad in ('retail/missing',99,None):
        with pytest.raises(ValueError):load_recipe(None,dict(value,retail_moveset=bad),catalog,None)
    catalog.rows['retail/blaze']['native_binding']['core_id']=142
    with pytest.raises(ValueError):load_recipe(None,value,catalog,None)


def test_recipe_rows_explicitly_mark_a_retail_core():
    item,report=fixture();item.update(core=51,retail_moveset='retail/d-mob')
    count,data=encode_rows({'example/fighter':item},report)
    assert count==3
    assert struct.unpack_from('<I',data,R['core'])==(51,)
    assert all(data[i*RECIPE_STRIDE+R['retail']]==1 for i in range(3))
