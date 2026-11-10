"""Synthetic contract checks; native appearance acceptance remains separate."""
import copy
import struct
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
from fighter_caf import source,combination,encode,ROW_BYTES
from fighter_registry import validate_pack


def test_caf_is_declared_data_with_hash_checked_path_and_no_executable_fields():
    p={'schema':'fighter-registry-draft-1','id':'example','version':'1.0.0','requires':{},
       'resources':[{'id':'caf','kind':'caf','compatibility':{},'source':{'format':'caf-fighter-1','selection':{'path':'fighter.json','sha256':'a'*64}}}],
       'fighters':[{'id':'fighter','name':'Example','inherits':'retail/blaze','components':{'caf':'example/caf'}}],'overrides':[]}
    validate_pack(p)
    for bad in ('../fighter.json','/fighter.json'):
        q=copy.deepcopy(p);q['resources'][0]['source']['selection']['path']=bad
        with pytest.raises(ValueError):validate_pack(q)
    q=copy.deepcopy(p);q['resources'][0]['source']['command']='run'
    with pytest.raises(ValueError):validate_pack(q)


def test_all_55_retail_style_combinations_and_duplicate_refusal():
    import itertools
    cores=set()
    for primary in range(5):
        rest=[s for s in range(5) if s!=primary]
        for count in range(3):
            for subset in itertools.combinations(rest,count):cores.add(combination([primary,*subset]))
    assert cores==set(range(87,142))
    with pytest.raises(ValueError):combination([1,1])
    with pytest.raises(ValueError):combination([True])


def test_compiled_caf_row_has_only_selection_training_appearance_and_style():
    recipe={'stats':dict(zip(('upper','lower','speed','toughness','health'),range(5))),
            'styles':[1,4],'caf_values':[0]*38,'caf_colors':[0]*38}
    raw=encode({'example/fighter':{'core':101,'audio_core':5,'recipe':recipe}},{'bindings':{'example/fighter':{'selection_key':100}}})
    assert struct.unpack_from('<4sIII',raw)==(b'FCA1',1,1,ROW_BYTES)
    assert len(raw)==16+ROW_BYTES
    assert struct.unpack_from('<8I',raw,16)==(100,101,0,1,2,3,4,2)
    assert raw[16+222:16+225]==bytes([1,4,255])
    assert raw[16+225:16+228]==bytes(3)
    assert struct.unpack_from('<I',raw,16+228)==(5,)


def test_caf_menu_uses_original_training_conversion_and_style_numbering():
    from fighter_caf import menu_record
    recipe={'stats':dict.fromkeys(('upper','lower','speed','toughness','health'),0),'styles':[0,1,3]}
    r=menu_record(recipe,100)
    assert r=={'selection_key':100,'stats':dict(zip('ULSTHC',(4,3,1,4,0,0))),'styles':[1,0,3]}
    recipe['stats']['health']=41
    assert menu_record(recipe,100)['stats']['H']==34
