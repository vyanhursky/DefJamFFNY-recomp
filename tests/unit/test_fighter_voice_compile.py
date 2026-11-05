"""Two authored voice resources, independent cores, and occupied namespaces."""
from copy import deepcopy
import hashlib
import struct

import pytest

from test_fighter_archive import fixture, Archive
from test_fighter_voice_bank import template
from fighter_voice import encode_stream
from fighter_voice_compile import VoiceCompiler, encode_voice_bindings, CATEGORIES
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
