"""Retail costumes keep one roster parent and an appearance-only native row."""
import struct
import hashlib
import subprocess

import pytest
from test_fighter_native import catalog,pack
from test_fighter_window import window_probe
from fighter_registry import RegistryError
from fighter_window import encode_window
from fighter_menu import character_parameters
from fighter_menu import compile_menu, functions
from test_fighter_menu import selector_fixture


def retail_catalog_fixture():
    from fighter_native import RetailCatalog
    source,original,layout=catalog(menu=True);raw=bytearray(original)
    for index,row in enumerate(source.rows.values(),1):struct.pack_into('<I',raw,row['record_offset']+40,index)
    original=bytes(raw)
    return RetailCatalog(original,hashlib.sha256(original).hexdigest()),original,layout


def outfit():
    value=pack();value['fighters'][0]['components']={}
    value['fighters'][0]['outfit_of']='retail/test-alpha'
    return value


def test_retail_costume_preserves_original_record_and_core():
    source,original,_=retail_catalog_fixture()
    data,report=source.compile([outfit()],binding_window=True)
    parent=source.rows['retail/test-alpha'];child=report['bindings']['alpha/fighter-0']
    assert data[parent['record_offset']:parent['record_offset']+104]==original[parent['record_offset']:parent['record_offset']+104]
    assert child['core_id']==parent['native_binding']['core_id']
    assert report['menu_roster']['alpha/fighter-0']['outfit_parent']==parent['native_binding']['selection_key']
    assert report['window']['fighters'][0]['reserved']==parent['native_binding']['selection_key']+1
    assert encode_window(report['window'])[:8]==b'FWR2\x02\0\0\0'


def test_native_window_admits_explicit_canonical_parent_only_in_v2(window_probe,tmp_path):
    source,_,_=retail_catalog_fixture();_,report=source.compile([outfit()],binding_window=True)
    raw=encode_window(report['window']);path=tmp_path/'outfit.bin';path.write_bytes(raw)
    assert subprocess.run([window_probe,path],capture_output=True).returncode==0
    for invalid in (100,101,0xffffffff):
        altered=bytearray(raw);struct.pack_into('<I',altered,140,invalid);path.write_bytes(altered)
        assert subprocess.run([window_probe,path],capture_output=True).returncode==1
    altered=bytearray(raw);altered[:8]=b'FWR1\x01\0\0\0';path.write_bytes(altered)
    assert subprocess.run([window_probe,path],capture_output=True).returncode==1


def test_outfits_cannot_change_combat_or_exceed_native_capacity():
    source,_,_=retail_catalog_fixture();value=outfit();value['fighters'][0]['components']['stats']={'health':99}
    with pytest.raises(RegistryError,match='share their parent'):source.compile([value],binding_window=True)
    value=outfit();template=value['fighters'][0]
    value['fighters']=[dict(template,id='outfit-'+str(i)) for i in range(3)]
    with pytest.raises(RegistryError,match='three outfits'):source.compile([value],binding_window=True)


def test_original_selector_parent_is_typed():
    record=dict(selection_key=104,stats=dict.fromkeys('ULSTHC',30),styles=[0],outfit_parent=76)
    assert 'ID=104' in character_parameters(record)
    assert 'ID=104' in character_parameters(dict(record,outfit_parent=0))
    for bad in (True,-1,99,100,'76'):
        with pytest.raises(ValueError):character_parameters(dict(record,outfit_parent=bad))


def test_hidden_costume_extends_native_datasets_and_retains_ready_parent():
    movie,constants=selector_fixture()
    record=dict(selection_key=100,stats=dict.fromkeys('ULSTHC',30),styles=[0],outfit_parent=76)
    changed,updated,_=compile_menu(movie,constants,{100:76},{100:'Pockets'},records=[record])
    _,_,definitions=functions(changed,updated)
    assert any(row['name']=='_recompAppendFighters' for row in definitions)
    assert any(row['name']=='keyBackHandler' for row in definitions)
    assert b'_recompRetailOutfitParents\0' in changed
    assert b'aDataSets\0' in changed
    # Hidden costumes carry a parent dataset, not an ordinary appended cell.
    assert b'CLOTH=1&FE_ID=100' in changed
