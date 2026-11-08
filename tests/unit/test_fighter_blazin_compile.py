"""Invented four-phase activation resources; no game payloads."""
from copy import deepcopy
import hashlib
import struct

import pytest

from test_fighter_archive import fixture
from test_fighter_cinematic_compile import bank
from test_fighter_animation_compile import track, RIG
from fighter_blazin_compile import BlazinTemplate, BlazinArchive, encode_blazin_bindings
from fighter_cinematic_compile import rename_bank
from fighter_archive import Archive
from fighter_assets import AssetError

TOKENS = ('BT1_01', 'BT2_01', 'BT3_01', 'BT4C01')


def bundle(token, phase):
    suffixes = ('.o', '_f.o', '_h.o') + (('_EYE.o', '_TARGET.o') if phase < 3 else ())
    return fixture({token + suffix: bank(token if suffix in ('.o', '_f.o', '_h.o') else (token + suffix)[:-2])
                    for suffix in suffixes})


def resource():
    return {'rig_sha256': RIG, 'bone_count': 4, 'shots': [
        {'template': token, 'tracks': track() if phase == 0 else None} for phase, token in enumerate(TOKENS)]}


def original():
    data = fixture({token + '.viv': bundle(token, phase) for phase, token in enumerate(TOKENS)})
    return data, BlazinArchive(data, hashlib.sha256(data).hexdigest())


def test_two_resources_four_roles_and_full_core_bindings_preserve_originals():
    source, compiler = original()
    result, receipt = compiler.compose({'alpha/activation': resource(), 'beta/activation': resource()})
    before, after = Archive(source), Archive(result)
    assert all(after.read(e.name) == before.read(e.name) for e in before.entries)
    assert [r['native_name'] for r in receipt['bindings']['alpha/activation']] == ['B00000', 'B00001', 'B00002', 'B00003']
    assert receipt['bindings']['beta/activation'][3]['camera_policy'] == 'native-venue'
    table = encode_blazin_bindings(result, receipt, {256: 'alpha/activation', 257: 'beta/activation', 1000: 'alpha/activation'})
    assert table[:4] == b'FBZ1' and len(table) == 48 + 3*36
    assert struct.unpack_from('<I8s8s8s8s', table, 48) == (256, *(f'B{i:05d}'.encode().ljust(8, b'\0') for i in range(4)))
    assert compiler.compose({'beta/activation': resource(), 'alpha/activation': resource()}) == (result, receipt)


def test_inherited_final_phase_keeps_body_and_venue_camera_contract():
    source = bundle('BT4C01', 3)
    compiler = BlazinTemplate(source, hashlib.sha256(source).hexdigest(), 'BT4C01', 3, RIG, 4)
    data, receipt = compiler.compose('B00007', None)
    result = Archive(data)
    assert {e.name for e in result.entries} == {'B00007.o', 'B00007_f.o', 'B00007_h.o'}
    for name, payload in compiler.members.items():
        assert result.read('B00007' + name[6:]) == rename_bank(payload, 'BT4C01', 'B00007')
    assert receipt['camera_policy'] == 'native-venue'


@pytest.mark.parametrize('damage', ['count', 'role', 'raw-track', 'unknown-field'])
def test_unknown_sequence_control_or_native_payloads_are_rejected(damage):
    _, compiler = original()
    item = resource()
    if damage == 'count':
        item['shots'].pop()
    elif damage == 'role':
        item['shots'][1]['template'] = 'BT1_01'
    elif damage == 'raw-track':
        item['shots'][0]['tracks'] = b'native payload'
    else:
        item['shots'][0]['address'] = 123
    with pytest.raises(AssetError):
        compiler.compose({'alpha/activation': item})


def test_receipts_cannot_change_names_phases_or_payloads():
    _, compiler = original()
    data, report = compiler.compose({'alpha/activation': resource()})
    for field, value in [('phase', 3), ('native_name', '../file'), ('sha256', '0'*64)]:
        changed = deepcopy(report)
        changed['bindings']['alpha/activation'][0][field] = value
        with pytest.raises(AssetError):
            encode_blazin_bindings(data, changed, {256: 'alpha/activation'})
    for cores in ({True: 'alpha/activation'}, {140: 'alpha/activation'}, {16384: 'alpha/activation'}, {256: 'missing/resource'}):
        with pytest.raises(AssetError):
            encode_blazin_bindings(data, report, cores)


def test_cinematic_extension_requires_unbroken_receipt_chain_and_preserved_shots():
    from test_fighter_cinematic_compile import bundle as cinematic
    from fighter_cinematic_compile import CinematicArchive
    source, _ = original()
    source = Archive(source).compose(additions={'CI_0001.viv': cinematic()})
    data, report = BlazinArchive(source, hashlib.sha256(source).hexdigest()).compose({'alpha/activation': resource()})
    final, extension = CinematicArchive(data, hashlib.sha256(data).hexdigest()).compose({
        'intro': {'template': 'CI_0001', 'rig_sha256': RIG, 'bone_count': 4, 'tracks': None}})
    table = encode_blazin_bindings(final, report, {256: 'alpha/activation'}, extension=extension)
    assert table[16:48] == hashlib.sha256(final).digest()
    for bad in ({**extension, 'source_sha256': '0'*64}, {**extension, 'sha256': '0'*64}, {}):
        with pytest.raises(AssetError):
            encode_blazin_bindings(final, report, {256: 'alpha/activation'}, extension=bad)
    changed = Archive(final).compose(replacements={'B00000.viv': b'changed'})
    with pytest.raises(AssetError, match='shot differs'):
        encode_blazin_bindings(changed, report, {256: 'alpha/activation'},
                              extension={**extension, 'sha256': hashlib.sha256(changed).hexdigest()})


def test_full_graph_receipt_marks_required_activation_phases():
    _,compiler=original();data,report=compiler.compose({'alpha/activation':resource()})
    report['bindings']['alpha/activation'][1]['full_graph']=True
    report['bindings']['alpha/activation'][3]['full_graph']=True
    table=encode_blazin_bindings(data,report,{256:'alpha/activation'})
    assert table[:8]==b'FBZ2'+struct.pack('<I',2)
    assert len(table)==48+40 and struct.unpack_from('<I',table,84)==(10,)
    report['bindings']['alpha/activation'][3]['camera_policy']='owned-absolute'
    table=encode_blazin_bindings(data,report,{256:'alpha/activation'})
    assert table[:8]==b'FBZ3'+struct.pack('<I',3)
    assert len(table)==48+44 and struct.unpack_from('<2I',table,84)==(10,8)
