"""Historical identity survives changes to active packs and sorted native rows."""
from copy import deepcopy
import os
from pathlib import Path
import shutil
import struct
import subprocess

import pytest

from test_fighter_native import catalog, pack
from fighter_bindings import ABSENT, encode_bindings


def test_add_remove_reenable_and_update_preserve_all_historical_identity():
    source, _, _ = catalog()
    alpha, beta = pack(), pack('beta', 'retail/test-beta')
    _, first = source.compile([alpha])
    original = deepcopy(first['binding_ledger'])
    _, second = source.compile([beta, alpha], original)
    assert first['binding_ledger'] == original
    for identity, entry in original['fighters'].items():
        assert second['binding_ledger']['fighters'][identity] == entry
    _, missing = source.compile([beta], second['binding_ledger'])
    dormant = missing['handle_bindings']['alpha/fighter-0']
    assert not dormant['available'] and dormant['native_handle'] == ABSENT and dormant['core_id'] == 0
    assert dormant['stable_handle'] == first['handle_bindings']['alpha/fighter-0']['stable_handle']
    alpha['version'] = '2.0.0'
    alpha['fighters'][0]['name'] = 'Renamed visible label'
    alpha['fighters'][0]['components']['stats']['health'] = 90
    _, restored = source.compile([alpha, beta], missing['binding_ledger'])
    assert restored['binding_ledger'] == second['binding_ledger']
    assert restored['handle_bindings'] == second['handle_bindings']
    assert restored['cache_sha256'] != second['cache_sha256']
    _, all_missing = source.compile([], restored['binding_ledger'])
    assert all_missing['binding_ledger'] == restored['binding_ledger']
    assert sum(not binding['available'] for binding in all_missing['handle_bindings'].values()) == 2


def test_adding_earlier_key_does_not_renumber_existing_fighters():
    source, _, _ = catalog()
    _, first = source.compile([pack('zeta')])
    _, second = source.compile([pack('alpha'), pack('zeta')], first['binding_ledger'])
    assert second['binding_ledger']['fighters']['zeta/fighter-0'] == first['binding_ledger']['fighters']['zeta/fighter-0']
    assert second['bindings']['zeta/fighter-0']['selection_key'] == first['bindings']['zeta/fighter-0']['selection_key']
    assert second['bindings']['alpha/fighter-0']['selection_key'] > second['bindings']['zeta/fighter-0']['selection_key']
    # The physical hash-sorted index can move while the historical handle stays.
    assert any(first['handle_bindings'][key]['native_handle'] != second['handle_bindings'][key]['native_handle']
               for key in first['handle_bindings'])


def test_no_reuse_or_mutation_under_deterministic_pack_reordering():
    source, _, _ = catalog()
    alpha, beta = pack(count=2), pack('beta', 'retail/test-beta')
    assert source.compile([alpha, beta]) == source.compile([beta, alpha])
    _, report = source.compile([alpha, beta])
    before = deepcopy(report['binding_ledger'])
    _, deleted = source.compile([], before)
    _, new = source.compile([pack('new')], deleted['binding_ledger'])
    assert new['binding_ledger']['fighters'].keys() > before['fighters'].keys()
    assert new['binding_ledger']['fighters']['new/fighter-0']['selection'] > max(e['selection'] for e in before['fighters'].values())
    assert before == report['binding_ledger']


@pytest.mark.parametrize('change', ('schema', 'baseline', 'retail', 'missing-retail', 'duplicate-handle', 'duplicate-selection', 'reserved-selection', 'symbol', 'metadata-bit', 'unknown-field'))
def test_corrupt_or_foreign_ledgers_fail_closed(change):
    source, _, _ = catalog()
    _, report = source.compile([pack()])
    ledger = deepcopy(report['binding_ledger'])
    custom = ledger['fighters']['alpha/fighter-0']
    retail = next(entry for identity, entry in ledger['fighters'].items() if identity.startswith('retail/'))
    if change == 'schema': ledger['schema'] = 'future'
    elif change == 'baseline': ledger['source_sha256'] = '0' * 64
    elif change == 'retail': retail['selection'] = 1000
    elif change == 'missing-retail': ledger['fighters'].pop(next(identity for identity in ledger['fighters'] if identity.startswith('retail/')))
    elif change == 'duplicate-handle': custom['handle'] = retail['handle']
    elif change == 'duplicate-selection': custom['selection'] = retail['selection']
    elif change == 'reserved-selection': custom['selection'] = 99
    elif change == 'symbol': custom['symbol'] = 'other'
    elif change == 'metadata-bit': custom['handle'] |= 0x800000
    elif change == 'unknown-field': custom['arbitrary'] = 'not accepted'
    with pytest.raises(ValueError):
        source.compile([pack()], ledger)


def test_historical_budget_includes_dormant_fighters(monkeypatch):
    import fighter_bindings
    source, _, _ = catalog()
    _, report = source.compile([pack()])
    monkeypatch.setattr(fighter_bindings, 'MAX_DEFINITIONS', 3)
    with pytest.raises(ValueError, match='historical definition budget'):
        source.compile([pack('new')], report['binding_ledger'])


PROBE = r'''
#include "fighter_bindings.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv) {
    FILE *f; uint8_t *data; size_t size; FighterBindings bindings; FighterBinding row;
    if(argc<2 || !(f=fopen(argv[1],"rb"))) return 2;
    data=(uint8_t*)malloc(FIGHTER_BINDINGS_MAX_FILE+1); if(!data) return 2;
    size=fread(data,1,FIGHTER_BINDINGS_MAX_FILE+1,f); fclose(f);
    if(!fighter_bindings_decode(&bindings,data,size)) { free(data); return 1; }
    if(argc==4) {
        if(!fighter_bindings_find(&bindings,(FighterBindingKey)strtoul(argv[2],NULL,10),(uint32_t)strtoul(argv[3],NULL,16),&row)) { free(data); return 3; }
        printf("%u,%u,%u,%u,%u",row.stable_handle,row.native_handle,row.selection_key,row.core_id,row.flags);
    } else printf("%u,%u",bindings.count,bindings.active_count);
    free(data); return 0;
}
'''


@pytest.fixture(scope='module')
def native_binding_probe(tmp_path_factory):
    compiler = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not compiler:
        pytest.skip('Native C compiler not available in this shell')
    root = Path(__file__).resolve().parents[2]
    folder = tmp_path_factory.mktemp('fighter-bindings-c')
    path = folder / 'probe.c'; path.write_text(PROBE)
    exe = folder / ('probe.exe' if os.name == 'nt' else 'probe')
    inputs = [str(path), str(root / 'src/hooks/fighter_bindings.c')]
    command = ([compiler, '/nologo', '/TC', '/I' + str(root / 'src/hooks'), *inputs, '/Fe' + str(exe)]
               if os.name == 'nt' else [compiler, '-std=c11', '-I', str(root / 'src/hooks'), *inputs, '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


def run_binding_probe(exe, path, data, *query):
    path.write_bytes(data)
    return subprocess.run([str(exe), str(path), *query], capture_output=True, text=True, timeout=10)


def test_real_native_decoder_roundtrips_all_identity_domains_and_dormant_rows(native_binding_probe, tmp_path):
    source, _, _ = catalog()
    _, first = source.compile([pack('alpha'), pack('beta', 'retail/test-beta')])
    _, missing = source.compile([pack('alpha')], first['binding_ledger'])
    for report in (first, missing):
        bindings = report['handle_bindings']
        data = encode_bindings(bindings)
        path = tmp_path / 'bindings.bin'
        result = run_binding_probe(native_binding_probe, path, data)
        assert result.returncode == 0
        assert result.stdout == f"{len(bindings)},{sum(row['available'] for row in bindings.values())}"
        for row in bindings.values():
            expected = ','.join(str(value) for value in (row['stable_handle'], row['native_handle'], row['selection_key'], row['core_id'], int(row['custom']) | int(row['available']) << 1))
            for domain, field in enumerate(('stable_handle', 'native_handle', 'symbol_hash', 'selection_key')):
                result = run_binding_probe(native_binding_probe, path, data, str(domain), f'{row[field]:x}')
                if domain == 1 and not row['available']:
                    assert result.returncode == 3
                else:
                    assert result.returncode == 0 and result.stdout == expected
        assert run_binding_probe(native_binding_probe, path, data, '0', 'ffffffff').returncode == 3


@pytest.mark.parametrize('mutation', ('truncated', 'trailing', 'version', 'count', 'active-count', 'table', 'reserved', 'stable-order', 'native-table', 'flags', 'inactive-core', 'bad-index', 'duplicate-index'))
def test_native_decoder_rejects_malformed_binding_tables(native_binding_probe, tmp_path, mutation):
    source, _, _ = catalog()
    _, report = source.compile([pack()])
    data = bytearray(encode_bindings(report['handle_bindings']))
    if mutation == 'truncated': data = data[:23]
    elif mutation == 'trailing': data += b'x'
    else:
        count = struct.unpack_from('<I', data, 8)[0]
        native_index = 24 + count * 24
        offset, value = {
            'version': (4, 2), 'count': (8, 0xffffffff), 'active-count': (12, count + 1),
            'table': (16, 256), 'reserved': (20, 1), 'stable-order': (48, struct.unpack_from('<I', data, 24)[0]),
            'native-table': (28, 0x7f000000), 'flags': (44, 4), 'inactive-core': (44, 0),
            'bad-index': (native_index, count),
            'duplicate-index': (native_index + 4, struct.unpack_from('<I', data, native_index)[0]),
        }[mutation]
        struct.pack_into('<I', data, offset, value)
    assert run_binding_probe(native_binding_probe, tmp_path / 'invalid.bin', data).returncode == 1
