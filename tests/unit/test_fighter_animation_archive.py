"""Independent animation resources cannot steal retail banks or core IDs."""
from copy import deepcopy
import hashlib
import struct

import pytest

from test_fighter_archive import fixture
from test_fighter_animation_compile import template, track, RIG
from fighter_animation_archive import AnimationArchive, encode_animation_bindings
from fighter_archive import Archive
from fighter_assets import AssetError


def baseline():
    envelope, _ = template()
    split = envelope.model.sections[2][4]
    data = fixture({'wres005.ord': envelope.model.data[:split],
                    'wres005.orl': envelope.model.data[split:],
                    'wres005.mnl': struct.pack('<2I', 2, 0) + b'A.B.',
                    'wres1000.mnl': b'reserved'})
    return data, AnimationArchive(data, hashlib.sha256(data).hexdigest())


def resource():
    return {'template_bank': 5, 'rig_sha256': RIG, 'bone_count': 4, 'replacements': {'A': track()}}


def test_independent_resources_preserve_retail_and_skip_occupied_bank_numbers():
    source, compiler = baseline()
    data, report = compiler.compose({'beta/motion': resource(), 'alpha/motion': resource()})
    assert report['bindings']['alpha/motion']['bank_number'] == 1001
    assert report['bindings']['beta/motion']['bank_number'] == 1002
    original, result = Archive(source), Archive(data)
    assert all(result.read(e.name) == original.read(e.name) for e in original.entries)
    assert result.read('wres1001.mnl') == result.read('wres005.mnl')
    # Three full core IDs can share two animation resources without narrowing.
    encoded = encode_animation_bindings(data, report, {256: 'alpha/motion', 257: 'beta/motion', 1000: 'alpha/motion'})
    assert encoded[:4] == b'FBA1' and struct.unpack_from('<3I', encoded, 4) == (1, 3, len(data))
    assert struct.unpack_from('<6I', encoded, 48) == (256, 1001, 257, 1002, 1000, 1001)


@pytest.mark.parametrize('core,key', [(140, 'alpha/motion'), (16384, 'alpha/motion'),
                                    (True, 'alpha/motion'), (256, 'unknown/motion')])
def test_invalid_core_or_missing_resource_is_rejected(core, key):
    _, compiler = baseline()
    data, report = compiler.compose({'alpha/motion': resource()})
    with pytest.raises(AssetError):
        encode_animation_bindings(data, report, {core: key})


def test_changed_receipt_or_payload_cannot_publish_binding():
    _, compiler = baseline()
    data, report = compiler.compose({'alpha/motion': resource()})
    wrong = deepcopy(report)
    wrong['bindings']['alpha/motion']['parts_sha256']['mnl'] = '0' * 64
    with pytest.raises(AssetError, match='bank differs'):
        encode_animation_bindings(data, wrong, {256: 'alpha/motion'})
    with pytest.raises(AssetError, match='archive differs'):
        encode_animation_bindings(data[:-1] + bytes([data[-1] ^ 1]), report, {256: 'alpha/motion'})


def test_arbitrary_resource_fields_and_unverified_baselines_are_rejected():
    data, compiler = baseline()
    with pytest.raises(AssetError, match='verified'):
        AnimationArchive(data, '0' * 64)
    with pytest.raises(AssetError, match='requires a template'):
        compiler.compose({'alpha/motion': {**resource(), 'native_hook': 42}})


def test_composition_checks_cumulative_budget_before_collecting_all_resources(monkeypatch):
    source, compiler = baseline()
    monkeypatch.setattr('fighter_animation_archive.MAX_ARCHIVE', len(source) + 1)
    with pytest.raises(AssetError, match='exceeds budget'):
        compiler.compose({'alpha/motion': resource(), 'beta/motion': resource()})


@pytest.mark.parametrize('change', [None, {}, {'parts_sha256': None},
                                  {'parts_sha256': {}, 'animation': {} }])
def test_malformed_resource_receipt_fails_as_validation_error(change):
    _, compiler = baseline()
    data, report = compiler.compose({'alpha/motion': resource()})
    report['bindings']['alpha/motion'] = change
    with pytest.raises(AssetError, match='Malformed'):
        encode_animation_bindings(data, report, {256: 'alpha/motion'})


def test_mixed_core_key_types_are_rejected_before_sorting():
    _, compiler = baseline()
    data, report = compiler.compose({'alpha/motion': resource()})
    with pytest.raises(AssetError, match='owned core'):
        encode_animation_bindings(data, report, {256: 'alpha/motion', '257': 'alpha/motion'})
