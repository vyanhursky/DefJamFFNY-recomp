"""Invented cinematic bundles test independent names and inherited ownership."""
import hashlib
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_animation import AnimationIndex
from fighter_animation_compile import rebuild
from fighter_cinematic_compile import CinematicArchive, CinematicTemplate, envelope, bind_cinematics
from fighter_archive import Archive
from fighter_assets import AssetError
from test_fighter_archive import fixture
from test_fighter_animation_compile import template, track, RIG


def bank(token):
    original, _ = template()
    model = original.model
    model.symbols = [(name.replace('__AnimationBank:::a', '__AnimationBank:::' + token), *rest)
                     for name, *rest in model.symbols]
    payload = bytearray(model.data[model.sections[1][4]:model.sections[1][4] + model.sections[1][5]])
    pointers = {at: value['target'] for at, value in model.pointers.items()}
    for i, suffix in enumerate(('_s', '_t')):
        pointers[32 + 4 * i] = len(payload)
        payload.extend((token + suffix).encode() + b'\0')
    payload.extend(bytes(-len(payload) % 4))
    return b''.join(rebuild(model, payload, pointers))


def bundle(token='CI_0001'):
    suffixes = ('.o', '_f.o', '_h.o') + (('1_EYE.o', '1_TARGET.o', '2_EYE.o', '2_TARGET.o')
                                       if token.startswith('CI_') else ('_EYE.o', '_TARGET.o'))
    return fixture({token + s: bank(token if s in ('.o', '_f.o', '_h.o') else (token + s)[:-2])
                    for s in suffixes})


@pytest.mark.parametrize('token,assigned', [('CI_0001', 'FI00000'), ('CE_0001', 'FV00000')])
def test_authored_body_keeps_native_helpers_and_root_track(token, assigned):
    source = bundle(token)
    compiler = CinematicTemplate(source, hashlib.sha256(source).hexdigest(), token, RIG, 4)
    data, receipt = compiler.compose(assigned, track())
    result = Archive(data)
    body = AnimationIndex(envelope(result.read(assigned + '.o')))
    assert body.names == [assigned + '_s', assigned + '_t']
    assert body.record_types[body.records[0]] == 15
    assert body.record_types[body.children[body.records[0]][0]] == 11
    before = AnimationIndex(envelope(compiler.members[token + '.o']))
    assert body.records[1] == before.records[1]
    for name, original in compiler.members.items():
        if name == token + '.o':
            continue
        old, new = AnimationIndex(envelope(original)), AnimationIndex(envelope(result.read(assigned + name[7:])))
        assert old.records == new.records and old.model.pointers == new.model.pointers
        # Parsed fixed-size names are the only bytes changed in a helper.
        allowed = set()
        for i, (a, b) in enumerate(zip(original, new.model.data)):
            if a != b:
                allowed.add(i)
        assert len(allowed) <= 21
    assert receipt['inherited_camera_face_hair_root_and_timing']
    assert not receipt['runtime_ready']


def test_baseline_hash_and_complete_helper_set_required():
    data = bundle()
    with pytest.raises(AssetError, match='verified'):
        CinematicTemplate(data, '0' * 64, 'CI_0001', RIG, 4)
    incomplete = fixture({'CI_0001.o': bank('CI_0001')})
    with pytest.raises(AssetError, match='helpers'):
        CinematicTemplate(incomplete, hashlib.sha256(incomplete).hexdigest(), 'CI_0001', RIG, 4)


def test_cinematic_kind_and_rig_cannot_be_changed_by_a_track():
    data = bundle()
    compiler = CinematicTemplate(data, hashlib.sha256(data).hexdigest(), 'CI_0001', RIG, 4)
    for assigned in ('FV00000', '../file', 'FI100000', 'FI0000'):
        with pytest.raises(AssetError, match='kind'):
            compiler.compose(assigned, track())
    with pytest.raises(AssetError, match='typed|rig'):
        compiler.compose('FI00000', b'arbitrary bytes')


def test_resource_ids_allocate_independently_and_preserve_all_original_entries():
    data = fixture({'CI_0001.viv': bundle(), 'CE_0001.viv': bundle('CE_0001'), 'FI00000.viv': b'reserved'})
    compiler = CinematicArchive(data, hashlib.sha256(data).hexdigest())
    resources = {key: {'template': token, 'rig_sha256': RIG, 'bone_count': 4, 'tracks': track()}
                 for key, token in [('pack/a', 'CI_0001'), ('pack/b', 'CI_0001'), ('pack/victory', 'CE_0001')]}
    result, receipt = compiler.compose(resources)
    assert {k: r['native_name'] for k, r in receipt['bindings'].items()} == {
        'pack/a': 'FI00001', 'pack/b': 'FI00002', 'pack/victory': 'FV00000'}
    archive = Archive(result)
    for entry in compiler.archive.entries:
        assert archive.read(entry.name) == compiler.archive.read(entry.name)
    assert compiler.compose(dict(reversed(list(resources.items())))) == (result, receipt)
    resources['pack/a']['extra'] = 'raw XML'
    with pytest.raises(AssetError, match='typed'):
        compiler.compose(resources)


def test_core_binding_couples_both_archive_hashes_and_independent_labels():
    source = fixture({'CI_0001.viv': bundle(), 'CE_0001.viv': bundle('CE_0001')})
    banks, receipt = CinematicArchive(source, hashlib.sha256(source).hexdigest()).compose({
        key: {'template': token, 'rig_sha256': RIG, 'bone_count': 4, 'tracks': track()}
        for key, token in [('a', 'CI_0001'), ('b', 'CE_0001')]})
    nis = fixture({'assets/IntroExtro.xml': b'<tauntslist></tauntslist>', 'other.xml': b'unchanged'})
    pin = hashlib.sha256(nis).hexdigest()
    cores = {256: {'intro': 'a', 'victory': 'b'}, 259: {'intro': 'a', 'victory': 'b'}}
    data, bindings, report = bind_cinematics(banks, receipt, nis, pin, cores)
    assert len(bindings) == 88 + 2 * 20
    assert struct.unpack_from('<4s5I', bindings) == (b'FIC1', 1, 2, len(banks), len(data), 0)
    assert bindings[24:56] == hashlib.sha256(banks).digest()
    assert bindings[56:88] == hashlib.sha256(data).digest()
    assert struct.unpack_from('<I8s8s', bindings, 88) == (256, b'FI00000\0', b'FV00000\0')
    archive = Archive(data)
    assert archive.read('other.xml') == b'unchanged'
    assert b'<name>fmc00256</name>' in archive.read('assets/IntroExtro.xml')
    assert b'<name>fmc00259</name>' in archive.read('assets/IntroExtro.xml')
    assert not report['runtime_ready']
    for wrong in ({256: {'intro': 'b', 'victory': 'a'}}, {16384: cores[256]}, {True: cores[256]}):
        with pytest.raises(AssetError):
            bind_cinematics(banks, receipt, nis, pin, wrong)
    with pytest.raises(AssetError, match='receipt'):
        bind_cinematics(banks + b'X', receipt, nis, pin, cores)
    with pytest.raises(AssetError, match='verified'):
        bind_cinematics(banks, receipt, nis, '0' * 64, cores)
    for malformed in (None, [], {'a': None}, {'a': {}}, {'a': {'native_name': 'FI00000'}}):
        wrong = {**receipt, 'bindings': malformed}
        with pytest.raises(AssetError):
            bind_cinematics(banks, wrong, nis, pin, cores)
    with pytest.raises(AssetError):
        bind_cinematics(banks, {k: v for k, v in receipt.items() if k != 'bindings'}, nis, pin, cores)


def test_archive_budget_rejects_growth_before_collecting_more_resources(monkeypatch):
    import fighter_cinematic_compile as module
    source = fixture({'CI_0001.viv': bundle()})
    compiler = CinematicArchive(source, hashlib.sha256(source).hexdigest())
    monkeypatch.setattr(module, 'MAX_ARCHIVE', len(source) + 100)
    with pytest.raises(AssetError, match='byte budget'):
        compiler.compose({'a': {'template': 'CI_0001', 'rig_sha256': RIG, 'bone_count': 4, 'tracks': track()}})
