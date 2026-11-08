"""Paired external motions use appended identities and preserve retail bytes."""
from copy import deepcopy
import hashlib
import struct

import pytest

from test_fighter_archive import fixture
from test_fighter_cinematic_compile import bank, envelope
from test_fighter_animation_compile import track, RIG
from fighter_animation import AnimationEnvelope, AnimationIndex
from fighter_archive import Archive
from fighter_assets import AssetError
from fighter_blazin_pairs import BlazinPairs, encode_pair_bindings


def original():
    members, tokens = {}, []
    for choice in range(82):
        for role in ('A', 'B'):
            token = f'N{choice:04d}_{role}'
            data = bank(token)
            split = envelope(data).model.sections[2][4]
            members[token + '.ord'], members[token + '.orl'] = data[:split], data[split:]
            tokens.append(token)
    members['blazin.mnl'] = struct.pack('<II', 164, 0) + '.'.join(tokens).encode() + b'.'
    data = fixture(members)
    return data, BlazinPairs(data, hashlib.sha256(data).hexdigest())


def resource():
    return {'template_choice': 2, 'rig_sha256': RIG, 'bone_count': 4,
            'subject': track(), 'counterpart': track()}


def test_full_graph_profile_generates_versioned_seals_and_explicit_slots():
    from test_fighter_animation_graphs import graph_template, motion, palettes, RIG as GRAPH_RIG
    from fighter_animation_graphs import Writer
    from fighter_animation_compile import rebuild
    source,_=original()
    archive=Archive(source)
    replacements={}
    for letter in ('A','B'):
        graph,_=graph_template().compose('A',motion())
        model,index=graph.model,AnimationIndex(graph)
        section=model.sections[1]
        payload=bytearray(model.data[section[4]:section[4]+section[5]])
        writer=Writer(payload,{at:row['target'] for at,row in model.pointers.items()})
        table=model.local_pointer(model.export_offset(graph.bank)+20,4*len(index.names))
        for i,name in enumerate(index.names):
            writer.pointer(table+4*i,writer.append(('N0002_'+letter+name[1:]).encode()+b'\0'))
        data,links=rebuild(model,payload,writer.pointers)
        replacements['N0002_'+letter+'.ord']=data
        replacements['N0002_'+letter+'.orl']=links
    source=archive.compose(replacements=replacements)
    compiler=BlazinPairs(source,hashlib.sha256(source).hexdigest())
    value={'template_choice':2,'rig_sha256':GRAPH_RIG,'bone_count':2,
           'subject':motion(),'counterpart':motion(),'profile':'graph-1',
           'graph_contexts':{'face':palettes(),'hands':palettes(),
                             'allowed_rigs':{'subject':[GRAPH_RIG],'counterpart':[GRAPH_RIG]}}}
    data,report=compiler.compose({'alpha/full':value})
    table=encode_pair_bindings(data,report,{256:{1:'alpha/full'}},slots=True)
    assert table[:8]==b'FBP3\x03\0\0\0'
    assert table[84:88]==b'FGP1'
    assert struct.unpack_from('<III8s8s',table,56)==(1,2,873,b'P0000_A\0',b'P0000_B\0')
    with pytest.raises(AssetError,match='explicit slots'):
        encode_pair_bindings(data,report,{256:{2:'alpha/full'}})
    changed=deepcopy(report)
    changed['bindings']['alpha/full']['roles']['subject']['graph_proof']['data_sha256']='0'*64
    with pytest.raises(AssetError,match='Graph proof differs'):
        encode_pair_bindings(data,changed,{256:{1:'alpha/full'}},slots=True)
    legacy=resource();legacy['template_choice']=0
    data,report=compiler.compose({'alpha/full':value,'beta/legacy':legacy})
    table=encode_pair_bindings(data,report,{256:{1:'alpha/full'},1000:{0:'beta/legacy'}},slots=True)
    assert table[:4]==b'FBP3' and struct.unpack_from('<I',table,52+64+8)[0]==4


def test_independent_pairs_append_external_ordinals_without_replacing_donor():
    source, compiler = original()
    result, report = compiler.compose({'alpha/finisher': resource(), 'beta/finisher': resource()})
    before, after = Archive(source), Archive(result)
    assert all(before.read(e.name) == after.read(e.name) for e in before.entries if e.name != 'blazin.mnl')
    assert report['motion_count'] == 168
    names = after.read('blazin.mnl')
    assert names[8:].startswith(before.read('blazin.mnl')[8:])
    assert names.endswith(b'P0000_A.P0000_B.P0001_A.P0001_B.')
    assert [pair['external_ordinal'] for pair in report['bindings'].values()] == [873, 875]
    for pair in report['bindings'].values():
        for role, item in pair['roles'].items():
            name = item['native_name']
            parsed = AnimationIndex(AnimationEnvelope(*(after.read(name + '.' + ext) for ext in ('ord', 'orl')),
                struct.pack('<II', 1, 0) + name.encode() + b'.'))
            assert parsed.names == [name + '_s', name + '_t']
            assert name.endswith('_A' if role == 'subject' else '_B')
    assert compiler.compose({'beta/finisher': resource(), 'alpha/finisher': resource()}) == (result, report)
    table = encode_pair_bindings(result, report, {256: {2: 'alpha/finisher'}, 1000: {2: 'beta/finisher'}})
    assert table[:4] == b'FBP1' and len(table) == 52 + 2*28
    assert struct.unpack_from('<III8s8s', table, 52) == (256, 2, 873, b'P0000_A\0', b'P0000_B\0')


@pytest.mark.parametrize('field,value', [('template_choice', 82), ('template_choice', True),
                                       ('subject', b'native code'), ('counterpart', None), ('rig_sha256', '0'*64)])
def test_invalid_pair_cannot_compile(field, value):
    _, compiler = original()
    item = resource(); item[field] = value
    with pytest.raises(AssetError):
        compiler.compose({'alpha/finisher': item})


def test_missing_role_or_unknown_fields_fail():
    _, compiler = original()
    for missing in ('subject', 'counterpart'):
        item = resource(); del item[missing]
        with pytest.raises(AssetError):
            compiler.compose({'alpha/finisher': item})
    item = resource(); item['native_address'] = 123
    with pytest.raises(AssetError):
        compiler.compose({'alpha/finisher': item})


def test_binding_cannot_change_behavior_role_ordinal_or_payload():
    _, compiler = original()
    data, report = compiler.compose({'alpha/finisher': resource()})
    for cores in ({True: {2: 'alpha/finisher'}}, {16384: {2: 'alpha/finisher'}},
                  {256: {3: 'alpha/finisher'}}, {256: {2: 'missing/resource'}}):
        with pytest.raises(AssetError):
            encode_pair_bindings(data, report, cores)
    for field, value in [('external_ordinal', 874), ('external_ordinal', 709), ('template_choice', 3)]:
        changed = deepcopy(report); changed['bindings']['alpha/finisher'][field] = value
        with pytest.raises(AssetError):
            encode_pair_bindings(data, changed, {256: {2: 'alpha/finisher'}})
    changed = deepcopy(report)
    changed['bindings']['alpha/finisher']['roles']['counterpart']['parts_sha256']['ord'] = '0'*64
    with pytest.raises(AssetError):
        encode_pair_bindings(data, changed, {256: {2: 'alpha/finisher'}})


def test_slots_using_one_behavior_retain_distinct_owned_pairs():
    _, compiler = original()
    data, receipt = compiler.compose({'alpha/first': resource(), 'alpha/second': resource()})
    table = encode_pair_bindings(data, receipt, {256: {0: 'alpha/first', 3: 'alpha/second'}}, slots=True)
    assert table[:8] == b'FBP2\x02\0\0\0' and len(table) == 52 + 64
    assert struct.unpack_from('<4I', table, 52) == (256, 0, 2, 873)
    assert struct.unpack_from('<4I', table, 84) == (256, 3, 2, 875)
    for selection in (True, -1, 4, '0'):
        with pytest.raises(AssetError):
            encode_pair_bindings(data, receipt, {256: {selection: 'alpha/first'}}, slots=True)
