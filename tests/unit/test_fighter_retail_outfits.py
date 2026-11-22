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
    assert 'ID=104' in character_parameters(dict(record,outfit_parent=100))
    for bad in (True,-1,99,0x7fffffff,'76'):
        with pytest.raises(ValueError):character_parameters(dict(record,outfit_parent=bad))


def standalone_outfits(count=2):
    value=pack()
    parent=value['fighters'][0]
    for i in range(count):
        value['fighters'].append(dict(id=f'look-{i}',name='Same fighter',inherits='alpha/'+parent['id'],
                                     outfit_of='alpha/'+parent['id'],components={}))
    return value


def test_standalone_outfits_share_parent_combat_menu_and_progress_owner(window_probe,tmp_path):
    source,original,_=retail_catalog_fixture()
    data,report=source.compile([standalone_outfits()],binding_window=True)
    parent=report['binding_ledger']['fighters']['alpha/fighter-0']['selection']
    assert report['menu_roster']['alpha/look-0']['outfit_parent']==parent
    assert report['menu_roster']['alpha/look-1']['outfit_parent']==parent
    assert report['menu_roster']['alpha/look-0']['outfit_order']==0
    assert report['menu_roster']['alpha/look-1']['outfit_order']==1
    assert [r['reserved'] for r in report['window']['fighters']]==[0,parent+1,parent+1]
    raw=encode_window(report['window']);assert raw[:8]==b'FWR3\x03\0\0\0'
    path=tmp_path/'window.bin';path.write_bytes(raw)
    assert subprocess.run([window_probe,path],capture_output=True).returncode==0
    for row in source.rows.values():
        at=row['record_offset'];assert data[at:at+104]==original[at:at+104]
    # Old decoders cannot accidentally interpret the widened parent domain.
    old=bytearray(raw);old[:8]=b'FWR2\x02\0\0\0';path.write_bytes(old)
    assert subprocess.run([window_probe,path],capture_output=True).returncode==1


@pytest.mark.parametrize('mutation',['missing','self','chain','capacity','combat','external'])
def test_standalone_outfit_ownership_is_bounded(mutation):
    source,_,_=retail_catalog_fixture();value=standalone_outfits()
    if mutation=='missing':value['fighters'][1]['outfit_of']='alpha/missing'
    elif mutation=='self':value['fighters'][1]['outfit_of']='alpha/look-0'
    elif mutation=='chain':value['fighters'][2]['outfit_of']='alpha/look-0'
    elif mutation=='capacity':value=standalone_outfits(3)
    elif mutation=='combat':value['fighters'][1]['components']['stats']={'health':66}
    else:value['fighters'][1]['outfit_of']='another/fighter'
    with pytest.raises(RegistryError):source.compile([value],binding_window=True)


def test_standalone_outfits_refuse_legacy_and_caf_parent_adapters():
    source,_,_=retail_catalog_fixture();value=standalone_outfits()
    with pytest.raises(RegistryError,match='participant binding window'):source.compile([value])
    with pytest.raises(RegistryError,match='recipe outfit adapter'):
        source.compile([value],binding_window=True,caf={'alpha/fighter-0':{}})


def test_authored_outfit_order_does_not_renumber_logical_identities():
    source,_,_=retail_catalog_fixture();value=standalone_outfits()
    _,first=source.compile([value],binding_window=True)
    value['fighters'][1:]=reversed(value['fighters'][1:])
    _,second=source.compile([value],binding_window=True)
    assert first['binding_ledger']==second['binding_ledger']
    assert second['menu_roster']['alpha/look-1']['outfit_order']==0
    assert second['menu_roster']['alpha/look-0']['outfit_order']==1


@pytest.mark.parametrize('parent',[True,'101',100,999])
def test_encoder_refuses_invalid_standalone_parents(parent):
    source,_,_=retail_catalog_fixture();_,report=source.compile([standalone_outfits()],binding_window=True)
    report['window']['fighters'][1]['reserved']=parent
    with pytest.raises(ValueError):encode_window(report['window'])


@pytest.mark.parametrize('mutation',['missing','self','chain','core','capacity'])
def test_native_decoder_refuses_invalid_standalone_ownership(window_probe,tmp_path,mutation):
    source,_,_=retail_catalog_fixture();_,report=source.compile([pack(count=4)],binding_window=True)
    rows=report['window']['fighters'];raw=bytearray(encode_window(report['window']))
    raw[:8]=b'FWR3\x03\0\0\0'
    struct.pack_into('<I',raw,120+24+20,rows[0]['selection_key']+1)
    if mutation=='missing':struct.pack_into('<I',raw,120+24+20,999)
    elif mutation=='self':struct.pack_into('<I',raw,120+24+20,rows[1]['selection_key']+1)
    elif mutation=='chain':struct.pack_into('<I',raw,120+20,rows[2]['selection_key']+1)
    elif mutation=='core':struct.pack_into('<I',raw,120+24+16,999)
    else:
        for i in (2,3):struct.pack_into('<I',raw,120+i*24+20,rows[0]['selection_key']+1)
    path=tmp_path/'invalid.bin';path.write_bytes(raw)
    assert subprocess.run([window_probe,path],capture_output=True).returncode==1


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
