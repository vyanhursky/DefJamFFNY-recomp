"""Owned core ordinals must not replace retail rows or narrow at255."""
import hashlib
import struct
from copy import deepcopy

import pytest

from test_fighter_motion import stream
from fighter_assets import AssetError
from fighter_motion import MotionIndex
from fighter_motion_compile import MotionCoreTemplates, encode_core_bindings


def baseline():
    data = bytearray(stream(cores=4))
    index = MotionIndex(bytes(data))
    for ordinal, start in enumerate(index.core_spans):
        data[start:start + 64] = bytes([ordinal]) * 64
        struct.pack_into('<H', data, start + 72, ordinal + 12)
    data = bytes(data)
    return data, MotionCoreTemplates(data, hashlib.sha256(data).hexdigest())


def test_owned_motion_cores_preserve_originals_and_bind_independent_packs():
    source, compiler = baseline()
    data, report = compiler.compose({'beta/moves': 3, 'alpha/moves': 2})
    assert data[:len(source)] == source
    assert compiler.compose({'alpha/moves': 2, 'beta/moves': 3}) == (data, report)
    parsed = MotionIndex(data)
    for ordinal, donor in ((4, 2), (5, 3)):
        start, original = parsed.core_spans[ordinal], parsed.core_spans[donor]
        assert data[start - 8:start + 852] == source[original - 8:original + 852]
    first = report['bindings']['alpha/moves']
    assert first == {'descriptor_index': 4, 'character_core': 5,
                     'donor_descriptor_index': 2, 'inherited_bank_number': 3,
                     'parameters_offset': len(source) + 8, 'actions_offset': len(source) + 80}
    assert not report['runtime_ready']
    assert report['native_descriptor_dispatch_required'] and report['native_bank_mapping_required']


def test_motion_descriptor_and_character_namespaces_cross255_independently():
    _, compiler = baseline()
    data, report = compiler.compose({f'pack/core-{i:03}': 2 for i in range(254)})
    assert len(MotionIndex(data).cores) == report['core_count'] == 258
    for descriptor in (254, 255, 256, 257):
        row = report['bindings'][f'pack/core-{descriptor - 4:03}']
        assert row['descriptor_index'] == descriptor
        assert row['character_core'] == descriptor + 1


@pytest.mark.parametrize('donors', [{}, {'pack/moves': True}, {'pack/moves': -1},
                                   {'pack/moves': 0}, {'pack/moves': 1}, {'pack/moves': 4}])
def test_motion_missing_and_special_donors_fail_before_publication(donors):
    _, compiler = baseline()
    with pytest.raises(AssetError):
        compiler.compose(donors)


def test_motion_template_pin_and_population_budget_are_required(monkeypatch):
    data, compiler = baseline()
    with pytest.raises(AssetError, match='verified'):
        MotionCoreTemplates(data, '0' * 64)
    monkeypatch.setattr('fighter_motion_compile.MAX_CORES', 4)
    with pytest.raises(AssetError, match='population'):
        compiler.compose({'pack/moves': 2})


def test_motion_binding_receipt_uses_relative_offsets_and_a_complete_file_digest():
    _, compiler = baseline()
    data, report = compiler.compose({'beta/moves': 3, 'alpha/moves': 2})
    encoded = encode_core_bindings(data, report)
    assert encoded[:4] == b'FMC1'
    assert struct.unpack_from('<5I', encoded, 4) == (1, 4, 2, len(data), 0)
    assert encoded[24:56] == hashlib.sha256(data).digest()
    assert len(encoded) == 56 + 2 * 16
    index = MotionIndex(data)
    assert struct.unpack_from('<4I', encoded, 56) == (4, index.core_spans[4], index.core_spans[4] + 72, 3)


@pytest.mark.parametrize('field,value', [('descriptor_index', 3), ('character_core', 4),
    ('donor_descriptor_index', 0), ('inherited_bank_number', 5), ('parameters_offset', 0),
    ('actions_offset', 0), ('descriptor_index', True)])
def test_motion_binding_rejects_receipt_identity_or_offset_tampering(field, value):
    _, compiler = baseline()
    data, report = compiler.compose({'pack/moves': 2})
    report = deepcopy(report)
    report['bindings']['pack/moves'][field] = value
    with pytest.raises(AssetError):
        encode_core_bindings(data, report)


def test_motion_binding_rejects_corruption_even_if_the_receipt_digest_is_updated():
    _, compiler = baseline()
    data, report = compiler.compose({'pack/moves': 2})
    altered = bytearray(data)
    altered[report['bindings']['pack/moves']['parameters_offset']] ^= 1
    with pytest.raises(AssetError, match='digest'):
        encode_core_bindings(bytes(altered), report)
    report['sha256'] = hashlib.sha256(altered).hexdigest()
    with pytest.raises(AssetError, match='verified donor'):
        encode_core_bindings(bytes(altered), report)
