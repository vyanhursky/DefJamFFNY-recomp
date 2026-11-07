"""Two authored voice resources, independent cores, and occupied namespaces."""
from copy import deepcopy
import hashlib
import struct

import pytest

from test_fighter_archive import fixture, Archive
from test_fighter_voice_bank import template
from fighter_voice import encode_stream
from fighter_voice_compile import VoiceCompiler, encode_voice_bindings, CATEGORIES, FAMILIES
from fighter_assets import AssetError


def source():
    h, d = template()
    entries = {}
    for category in CATEGORIES:
        entries[f'speech\\{category}\\Def_Jam_Characters\\022.hdr'] = h
        entries[f'speech\\{category}\\Def_Jam_Characters\\022.dat'] = d
    entries['speech\\streams\\intro\\600.asf'] = b'existing reserved source'
    data = fixture(entries)
    return data, VoiceCompiler(data, hashlib.sha256(data).hexdigest())


def voice(value):
    pcm = encode_stream(struct.pack('<h', value), 24000)
    return {'template_voice': 22, 'samples': {'Character': {1: pcm}}, 'intro': pcm, 'extro': pcm}


def test_independent_voices_preserve_original_archive_and_have_explicit_cinematics():
    original, compiler = source()
    data, report = compiler.compose({'beta/voice': voice(2), 'alpha/voice': voice(1)})
    archive = Archive(data, native_separators=True)
    assert report['bindings']['alpha/voice']['voice_id'] == 601
    assert report['bindings']['beta/voice']['voice_id'] == 602
    for entry in compiler.archive.entries:
        assert archive.read(entry.name) == compiler.archive.read(entry.name)
    assert compiler.archive.data == original
    receipt = encode_voice_bindings(data, report, {259: 'beta/voice', 256: 'alpha/voice'})
    assert receipt[:4] == b'FVA1' and len(receipt) == 64
    assert struct.unpack_from('<4I', receipt, 48) == (256, 601, 259, 602)
    assert receipt[16:48].hex() == hashlib.sha256(data).hexdigest()
    assert not report['runtime_ready']


def test_shared_voice_can_bind_multiple_cores_without_duplicate_resources():
    _, compiler = source()
    data, report = compiler.compose({'alpha/voice': voice(1)})
    receipt = encode_voice_bindings(data, report, {256: 'alpha/voice', 257: 'alpha/voice'})
    assert struct.unpack_from('<4I', receipt, 48) == (256, 601, 257, 601)


@pytest.mark.parametrize('change', [
    lambda v: v.pop('intro'), lambda v: v.update(extra='code'),
    lambda v: v.update(template_voice=True), lambda v: v.update(template_voice=99),
    lambda v: v.update(samples={'unknown': {}}), lambda v: v.update(intro=b'arbitrary'),
])
def test_unknown_or_incomplete_voice_contract(change):
    _, compiler = source()
    item = voice(1)
    change(item)
    with pytest.raises(AssetError):
        compiler.compose({'alpha/voice': item})


def test_receipts_and_core_namespaces_are_checked_before_emission():
    original, compiler = source()
    with pytest.raises(AssetError, match='verified'):
        VoiceCompiler(original, '0' * 64)
    data, report = compiler.compose({'alpha/voice': voice(1)})
    for cores in ({1: 'alpha/voice'}, {16384: 'alpha/voice'}, {256: 'missing/voice'}, {}):
        with pytest.raises(AssetError):
            encode_voice_bindings(data, report, cores)
    changed = deepcopy(report)
    changed['bindings']['alpha/voice']['categories']['Character']['sha256'][0] = '0' * 64
    with pytest.raises(AssetError, match='receipt'):
        encode_voice_bindings(data, changed, {256: 'alpha/voice'})


def explicit_source():
    header, samples = template()
    entries, banks = {}, {}
    for category, donor in zip(CATEGORIES, (22, 23, 24)):
        h = bytearray(header)
        struct.pack_into('<2H', h, 0, FAMILIES[category][0], donor)
        stem = f'speech/{category}/Def_Jam_Characters/{donor:03d}'
        entries[stem + '.hdr'], entries[stem + '.dat'] = bytes(h), samples
        banks[category] = {'template_voice': donor, 'family': FAMILIES[category][1], 'samples': {}}
    data = fixture(entries)
    item = voice(1)
    return VoiceCompiler(data, hashlib.sha256(data).hexdigest()), {
        'banks': banks, 'intro': item['intro'], 'extro': item['extro']}


def test_per_category_templates_and_explicit_families_preserve_event_metadata():
    compiler, item = explicit_source()
    # One category is authored, the others deliberately retain their templates.
    item['banks']['Character']['samples'][1] = item['intro']
    data, report = compiler.compose({'alpha/voice': item})
    output = Archive(data, native_separators=True)
    for category, bank in item['banks'].items():
        original = compiler.archive.read(f"speech/{category}/Def_Jam_Characters/{bank['template_voice']:03d}.hdr")
        generated = output.read(f'speech/{category}/Def_Jam_IP_Characters/600.hdr')
        assert struct.unpack_from('<2H', generated) == (bank['family'], 600)
        # Equal-length synthetic streams keep offsets as well as all criteria.
        assert generated[4:] == original[4:]
        receipt = report['bindings']['alpha/voice']['categories'][category]
        assert receipt['source_first_key'] == FAMILIES[category][0]
        assert receipt['first_key'] == bank['family']
        assert receipt['template_voice'] == bank['template_voice']
    assert encode_voice_bindings(data, report, {256: 'alpha/voice'})[:4] == b'FVA1'


@pytest.mark.parametrize('change', [
    lambda v: v['banks'].pop('Enviro'),
    lambda v: v['banks']['Character'].update(family=16626),
    lambda v: v['banks']['Character'].update(family=True),
    lambda v: v['banks']['Character'].update(template_voice=True),
    lambda v: v['banks']['Character'].update(code=1),
    lambda v: v['banks']['Character'].update(samples={255: b'x'}),
])
def test_explicit_category_contract_rejects_ambiguity_and_cross_category_families(change):
    compiler, item = explicit_source()
    change(item)
    with pytest.raises(AssetError):
        compiler.compose({'alpha/voice': item})


def test_explicit_absence_omits_members_and_binds_shared_and_all_absent_voices():
    compiler, item = explicit_source()
    for bank in item['banks'].values():
        bank['state'] = 'present'
    item['banks']['Enviro'] = {'state': 'absent'}
    silent = deepcopy(item)
    silent['banks'] = {category: {'state': 'absent'} for category in CATEGORIES}
    data, report = compiler.compose({'alpha/voice': item, 'beta/voice': silent})
    archive = Archive(data, native_separators=True)
    assert report['schema'] == 'fighter-voice-archive-2'
    assert 'speech/enviro/def_jam_ip_characters/600.hdr' not in archive.by_name
    assert 'speech/character/def_jam_ip_characters/601.dat' not in archive.by_name
    receipt = encode_voice_bindings(data, report, {256: 'alpha/voice', 257: 'alpha/voice', 259: 'beta/voice'})
    assert receipt[:4] == b'FVA2'
    assert struct.unpack_from('<9I', receipt, 48) == (256, 600, 3, 257, 600, 3, 259, 601, 0)
    for purpose in ('intro', 'extro'):
        assert archive.read(f'speech/streams/{purpose}/601.asf') == silent[purpose]
    # Legacy formats may share the generation, and keep all three banks.
    compiler, explicit = explicit_source()
    explicit['banks']['Character'] = {'state': 'absent'}
    for category in ('Taunts', 'Enviro'):
        explicit['banks'][category]['state'] = 'present'
    data, report = compiler.compose({'alpha/voice': explicit})
    damaged = deepcopy(report)
    damaged['bindings']['alpha/voice']['categories']['Taunts'] = {'state': 'absent'}
    with pytest.raises(AssetError, match='unexpected archive'):
        encode_voice_bindings(data, damaged, {256: 'alpha/voice'})
    damaged = deepcopy(report)
    damaged['bindings']['alpha/voice']['categories'].pop('Character')
    with pytest.raises(AssetError, match='three explicit'):
        encode_voice_bindings(data, damaged, {256: 'alpha/voice'})


@pytest.mark.parametrize('bad', [
    {}, {'state': 'missing'}, {'state': 'absent', 'samples': {}},
    {'state': 'present'}, {'state': True},
])
def test_absence_contract_rejects_incomplete_or_ambiguous_states(bad):
    compiler, item = explicit_source()
    for bank in item['banks'].values():
        bank['state'] = 'present'
    item['banks']['Enviro'] = bad
    with pytest.raises(AssetError):
        compiler.compose({'alpha/voice': item})


def test_event_identity_ignores_only_physical_layout_and_explicit_family_when_requested():
    from fighter_voice_bank import event_identity
    header, _ = template()
    changed = bytearray(header)
    struct.pack_into('<2H', changed, 0, 1, 626)
    changed[7:10] = bytes((3, 5, 0))
    changed[12:14] = bytes((1, 2))
    assert event_identity(header, include_family=False) == event_identity(bytes(changed), include_family=False)
    assert event_identity(header) != event_identity(bytes(changed))
    changed[14] ^= 1
    assert event_identity(header, include_family=False) != event_identity(bytes(changed), include_family=False)
