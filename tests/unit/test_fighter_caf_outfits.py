"""One stable fighter, bounded appearance variants and owned UI-only aliases."""
import copy
import struct
import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
from fighter_caf import encode, menu_record
from fighter_caf_extras import encode as encode_extras, PIXELS
from fighter_caf_outfits import assign_presentation, load
from fighter_menu import character_parameters


def fixture():
    recipe = dict(stats=dict.fromkeys(('upper','lower','speed','toughness','health'), 20),
                  styles=[1,0,3], caf_values=[0]*38, caf_colors=[0]*38)
    recipe['caf_values'][5] = 4
    variants = []
    for i in range(3):
        value = copy.deepcopy(recipe); value['caf_values'][12] = i
        variants.append(dict(id='default' if not i else f'outfit-{i}', name=f'Outfit {i+1}', recipe=value,
                             extras=dict(finishers=[52,38,30,39], atlases={'a': bytes([i])*PIXELS})))
    item = dict(core=101, audio_core=5, recipe=recipe, outfits=variants)
    report = dict(bindings={'example/fighter': {'selection_key':100}},
                  menu_roster={'example/fighter': menu_record(recipe,100)})
    assign_presentation({'example/fighter':item},report)
    return item,report


def test_three_recipes_keep_one_selection_and_shared_combat_with_distinct_art():
    item,report=fixture()
    recipes=encode({'example/fighter':item},report)
    extras=encode_extras({'example/fighter':item},report)
    assert struct.unpack_from('<4sIII',recipes)==(b'FCA2',2,3,240)
    assert struct.unpack_from('<4sIII',extras)==(b'FCX2',2,3,52)
    for index in range(3):
        at=16+index*240
        assert struct.unpack_from('<8I',recipes,at)==(100,101,20,20,20,20,20,3)
        assert struct.unpack_from('<II',recipes,at+232)==(index,item['outfit_aliases'][index])
        assert struct.unpack_from('<4I',extras,16+index*52+8)==(52,38,30,39)
        assert struct.unpack_from('<I',extras,16+index*52+48)==(index,)
    parameters=character_parameters(report['menu_roster']['example/fighter'])
    assert parameters.startswith('CLOTH=1&') and parameters.count('&FE_ID=100&')==1
    assert '1610612736' not in parameters  # No UI alias in ControllerSetup datasets.


def test_ui_aliases_are_deterministic_and_avoid_every_existing_binding():
    item,report=fixture();report['bindings']['other/fighter']={'selection_key':0x60000000}
    assign_presentation({'example/fighter':item},report)
    assert item['outfit_aliases']==[100,0x60000001,0x60000002]
    before=copy.deepcopy(report);assign_presentation({'example/fighter':item},report)
    assert report==before and len(report['menu_roster'])==1


@pytest.mark.parametrize('change',[
    lambda d:d.update(outfits=[{}]*3),
    lambda d:d.update(outfit_name=''),
    lambda d:d['outfits'][0].update(id='default'),
    lambda d:d['outfits'][0].update(stats={}),
    lambda d:d.update(portraits={'absent':'pack/picture'}),
    lambda d:d.update(portraits={'default':'../picture'}),
])
def test_source_refuses_invalid_collections_before_native_construction(monkeypatch,tmp_path,change):
    import fighter_caf, fighter_caf_extras
    from types import SimpleNamespace
    item,_=fixture();v=item['recipe']
    value=dict(v,outfit_name='Default',outfits=[dict(id='second',name='Second',caf_values=v['caf_values'],caf_colors=v['caf_colors'])])
    monkeypatch.setattr(fighter_caf,'recipe',lambda value,db:101)
    monkeypatch.setattr(fighter_caf,'validate_assets',lambda *a:None)
    monkeypatch.setattr(fighter_caf_extras,'load',lambda *a:None)
    change(value)
    with pytest.raises((ValueError,TypeError)):
        load(tmp_path,value,SimpleNamespace(db=None),tmp_path)
