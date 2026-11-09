"""Options unlock projection preserves unrelated bytes and dormant identities."""
from copy import deepcopy
import struct

import pytest

from test_fighter_native import catalog, pack
import fighter_unlocks as unlocks
from fighter_bindings import seed


def fixture():
    source, _, _ = catalog()
    baseline = seed(source.db, source.source_sha256, source.rows)
    _, report = source.compile([pack(count=300)])
    ledger = report['binding_ledger']
    payload = bytearray(bytes(range(256)) * (unlocks.SIZE // 256 + 1))[:unlocks.SIZE]
    struct.pack_into('<I', payload, unlocks.COUNT, 0)
    struct.pack_into('<81I', payload, unlocks.SENTINEL, *([0xffffffff] * 81))
    return source, baseline, ledger, bytes(payload)


def test_more_than_255_unlocks_roundtrip_without_expanding_fixed_native_payload():
    _, baseline, ledger, payload = fixture()
    marks = {key: unlocks.METADATA if index % 2 else 0 for index, key in enumerate(ledger['fighters'])}
    native, extension = unlocks.project(payload, marks, ledger, baseline)
    assert len(native) == unlocks.SIZE
    assert len(unlocks.settings_keys(native)) == len(baseline['fighters'])
    assert len(extension['marks']) == 300
    assert unlocks.restore(native, extension, ledger, baseline) == marks
    changed = set(range(unlocks.COUNT, unlocks.COUNT + 4)) | set(range(unlocks.KEYS, unlocks.KEYS + 320))
    assert all(a == b for index, (a, b) in enumerate(zip(native, payload)) if index not in changed)
    assert unlocks.project(payload, dict(reversed(list(marks.items()))), ledger, baseline) == (native, extension)


def test_removed_reenabled_and_new_packs_keep_progress_by_identity():
    source, baseline, ledger, payload = fixture()
    marks = {'alpha/fighter-0': unlocks.METADATA, 'alpha/fighter-299': 0, next(iter(baseline['fighters'])): 0}
    native, extension = unlocks.project(payload, marks, ledger, baseline)
    _, missing = source.compile([], ledger)
    assert unlocks.restore(native, extension, missing['binding_ledger'], baseline) == marks
    _, updated = source.compile([pack('earlier'), pack(count=300)], ledger)
    old = unlocks.restore(native, extension, ledger, baseline)
    next_native, next_extension = unlocks.project(native, old, updated['binding_ledger'], baseline)
    assert unlocks.restore(next_native, next_extension, updated['binding_ledger'], baseline) == marks
    with pytest.raises(ValueError, match='different save generation'):
        unlocks.restore(native, extension, updated['binding_ledger'], baseline)


@pytest.mark.parametrize('fault', ['size', 'count', 'sentinel', 'duplicate', 'unsorted', 'unknown'])
def test_malformed_native_state_is_rejected(fault):
    _, baseline, ledger, payload = fixture()
    data = bytearray(payload)
    values = [entry['handle'] for entry in baseline['fighters'].values()]
    values.sort()
    if fault == 'size': data.pop()
    elif fault == 'count': struct.pack_into('<I', data, unlocks.COUNT, 81)
    elif fault == 'sentinel': struct.pack_into('<I', data, unlocks.SENTINEL, 0)
    else:
        pair = [values[0], values[0]] if fault == 'duplicate' else [values[1], values[0]] if fault == 'unsorted' else [values[0], 0x7fffff]
        struct.pack_into('<I', data, unlocks.COUNT, 2)
        struct.pack_into('<2I', data, unlocks.KEYS, *pair)
    with pytest.raises(ValueError): unlocks.read(bytes(data), ledger, baseline)


def test_crossed_extensions_bad_metadata_and_foreign_keys_fail_without_mutation():
    _, baseline, ledger, payload = fixture()
    native, extension = unlocks.project(payload, {'alpha/fighter-0': 0}, ledger, baseline)
    original = deepcopy(extension)
    for change in ('settings', 'ledger', 'schema', 'metadata', 'retail', 'unknown'):
        bad = deepcopy(extension)
        if change == 'settings': bad['settings_sha256'] = '0' * 64
        elif change == 'ledger': bad['ledger_sha256'] = '0' * 64
        elif change == 'schema': bad['schema'] = 'future'
        elif change == 'metadata': bad['marks']['alpha/fighter-0'] = True
        elif change == 'retail': bad['marks'][next(iter(baseline['fighters']))] = 0
        else: bad['marks']['missing/new'] = 0
        with pytest.raises(ValueError): unlocks.restore(native, bad, ledger, baseline)
    assert extension == original
