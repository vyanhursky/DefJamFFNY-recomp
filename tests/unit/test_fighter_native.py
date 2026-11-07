"""General manifest -> native-cache preview, using only synthetic game-free data."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

import pytest

from test_fighter_sod import native_fixture

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_native import RetailCatalog
from fighter_registry import RegistryError, SCHEMA
from fighter_sod import Database, CHARACTER, name_hash


def catalog(menu=False):
    data, layout = native_fixture(menu=menu)
    data = bytearray(data)
    struct.pack_into('<I', data, 8, 0x86f322ac)
    data = bytes(data)
    return RetailCatalog(data, hashlib.sha256(data).hexdigest()), data, layout


def pack(owner='alpha', donor='retail/test-alpha', count=1):
    return {'schema': SCHEMA, 'id': owner, 'version': '1.0.0', 'requires': {}, 'resources': [],
            'fighters': [{'id': f'fighter-{i}', 'name': f'Example {i}', 'inherits': donor,
                           'components': {'stats': {'health': 65}}} for i in range(count)], 'overrides': []}


def test_verified_baseline_and_exact_noop():
    source, data, _ = catalog()
    baseline = source.baseline()
    assert len(baseline['fighters']) == 2
    assert len(baseline['resources']) == 8
    assert {f['id'] for f in baseline['fighters']} == {'test-alpha', 'test-beta'}
    assert 'record_offset' not in json.dumps(baseline)
    baseline['fighters'].clear()
    assert len(source.baseline()['fighters']) == 2
    compiled, report = source.compile([])
    assert compiled == data
    assert report['cache_sha256'] == report['source_sha256']
    assert not report['runtime_ready'] and not report['launch_allowed']
    with pytest.raises(RegistryError) as caught:
        RetailCatalog(data, '0' * 64)
    assert caught.value.code == 'baseline-hash'


def test_large_logical_roster_keeps_native_database_bounded_and_confirmation_gated():
    source, data, _ = catalog(menu=True)
    compiled, report = source.compile([pack(count=300)], logical_menu=True)
    assert compiled == data and report['native_character_count'] == 2
    assert len(report['menu_roster']) == 300 and report['added_count'] == 300
    assert report['binding_mode'] == 'logical-menu-only' and not report['launch_allowed']
    assert max(row['selection_key'] for row in report['menu_roster'].values()) > 255
    assert all(not row['available'] for key, row in report['handle_bindings'].items() if key.startswith('alpha/'))
    row = report['menu_roster']['alpha/fighter-0']
    assert row['stats'] == dict(U=22, L=21, S=25, T=25, H=65, C=25)
    assert row['styles'] == [0, 3, 4]
    assert source.compile([pack(count=300)], logical_menu=True) == (compiled, report)


def test_two_packs_multiple_fighters_full_pipeline_and_determinism():
    source, data, layout = catalog()
    a, b = pack(count=2), pack('beta', 'retail/test-beta')
    before = deepcopy([a, b])
    compiled, report = source.compile([a, b])
    assert source.compile([b, a]) == (compiled, report)
    assert [a, b] == before
    assert report['added_count'] == 3 and report['fighter_count'] == 5
    db = Database(compiled)
    by_name = {r['name']: r for r in db.character_metadata()['characters']}
    for identifier, expected_core in [('alpha/fighter-0', 101), ('alpha/fighter-1', 101), ('beta/fighter-0', 102)]:
        binding = report['bindings'][identifier]
        row = by_name[binding['native_name']]
        assert row['native_binding']['core_id'] == expected_core
        assert row['fields']['Health']['word'] == 65
        assert row['fields']['DisplayName']['symbol'] in report['localization_entries']
        assert row['name'] != identifier
        assert len(row['name'].encode('ascii')) <= 19
    for offset in layout['records']:
        assert compiled[offset:offset + 104] == data[offset:offset + 104]


@pytest.mark.parametrize('primary, expected', [(9, [0, 3, 4]), (24, [3, 0, 4]), (26, [3, 0, 4])])
def test_menu_uses_first_matching_primary_bit_then_remaining_styles(primary, expected):
    _, data, layout = catalog(menu=True)
    changed = bytearray(data)
    struct.pack_into('<I', changed, layout['records'][0] + 18 * 4, primary)
    source = RetailCatalog(bytes(changed), hashlib.sha256(changed).hexdigest())
    _, report = source.compile([pack()], logical_menu=True)
    assert report['menu_roster']['alpha/fighter-0']['styles'] == expected


def test_composed_retail_edits_preserve_authored_donor_for_addition():
    source, data, layout = catalog()
    edit = pack('balance', count=0)
    edit['overrides'] = [{'target': 'retail/test-alpha', 'components': {'stats': {'health': 80}}, 'supersedes': []}]
    addition = pack()
    addition['fighters'][0]['components'] = {}  # Inherit the authored donor's 25, not the override's 80.
    compiled, report = source.compile([edit, addition])
    rows = {r['name']: r for r in Database(compiled).character_metadata()['characters']}
    assert rows['Test Alpha']['fields']['Health']['word'] == 80
    assert rows[report['bindings']['alpha/fighter-0']['native_name']]['fields']['Health']['word'] == 25
    assert compiled[layout['records'][1]:layout['records'][1] + 104] == data[layout['records'][1]:layout['records'][1] + 104]
    assert report['edited_count'] == 1
    assert report['bindings']['retail/test-alpha']['selection_key'] == 1


def test_unknown_assets_components_and_conflicts_rejected_before_cache():
    source, _, _ = catalog()
    p = pack()
    p['resources'] = [{'id': 'picture', 'kind': 'portrait', 'compatibility': {}}]
    p['fighters'][0]['components']['portrait'] = 'alpha/picture'
    with pytest.raises(RegistryError) as caught:
        source.compile([p])
    assert caught.value.code == 'native-resource'
    p = pack()
    p['resources'] = [{'id': 'brain', 'kind': 'ai', 'compatibility': {}}]
    p['fighters'][0]['components']['ai'] = 'alpha/brain'
    with pytest.raises(RegistryError) as caught:
        source.compile([p])
    assert caught.value.code == 'native-component'
    a, b = pack('alpha', count=0), pack('beta', count=0)
    for p, health in [(a, 80), (b, 90)]:
        p['overrides'] = [{'target': 'retail/test-alpha', 'components': {'stats': {'health': health}}, 'supersedes': []}]
    with pytest.raises(RegistryError) as caught:
        source.compile([a, b])
    assert caught.value.code == 'component-conflict'
    p = pack()
    p['fighters'][0].pop('inherits')
    p['fighters'][0]['components'] = source.baseline()['fighters'][0]['components']
    p['fighters'][0]['components']['stats'] = {'health': 70}
    with pytest.raises(RegistryError) as caught:
        source.compile([p])
    assert caught.value.code == 'native-component'


def test_localization_and_width_remain_explicit_gates():
    source, _, _ = catalog()
    p = pack(count=300)
    p['fighters'][0]['name'] = '\u732b' * 12
    compiled, report = source.compile([p])
    assert len(Database(compiled)._tables[CHARACTER].records) == 302
    assert '\u732b' * 12 in report['localization_entries'].values()
    assert 'native-label-buffer' in report['blockers']
    assert 'localization-registration' in report['blockers']
    assert len(report['native']['native_signed_byte_overflow']) > 0
    assert not report['launch_allowed']


def test_rebuilt_indexes_follow_existing_record_edits():
    source, _, layout = catalog()
    data, _ = source.db.extend_character_records([], [{'template': layout['records'][0],
                                                      'fields': {'Health': 90, 'Model': 'ChangedModel'}}])
    db = Database(data)
    group = db.index(db.word(db.directory[CHARACTER] + 4))
    indexes = dict(zip(group.keys, group.values))
    for member, value in [('Health', 90), ('Model', name_hash('ChangedModel'))]:
        index = db.index(indexes[CHARACTER ^ name_hash(member)][0], tagged=True)
        assert dict(zip(index.keys, index.values))[value] == (layout['records'][0],)
    health = db.index(indexes[CHARACTER ^ name_hash('Health')][0], tagged=True)
    assert health.keys == (25, 90)
    with pytest.raises(ValueError, match='duplicate'):
        source.db.extend_character_records([], [{'template': layout['records'][0], 'fields': {}}] * 2)
    with pytest.raises(ValueError, match='Unsupported'):
        source.db.extend_character_records([], [{'template': layout['records'][0], 'fields': {'core_id': 999}}])
    malformed = bytearray(source.db.data)
    original_group = source.db.index(source.db.word(source.db.directory[CHARACTER] + 4))
    numeric_offset = dict(zip(original_group.keys, original_group.values))[CHARACTER ^ name_hash('Health')][0]
    struct.pack_into('<I', malformed, numeric_offset + 12, 24)  # Sorted but disagrees with indexed row value.
    malformed_db = Database(bytes(malformed))
    with pytest.raises(ValueError, match='index key encoding'):
        malformed_db.extend_character_records([], [{'template': layout['records'][0], 'fields': {'Health': 90}}])


def test_preview_cache_is_immutable_verified_and_kept_under_logs(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[2] / 'scripts/fighter-registry.py'
    spec = importlib.util.spec_from_file_location('native_cli', path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, 'ROOT', tmp_path)
    source, _, _ = catalog()
    data, report = source.compile([pack()])
    monkeypatch.setattr(cli, 'MAX_DOCUMENT', 1)  # Generated reports have a separate budget.
    directory = Path(cli.write_preview(data, report))
    assert directory.is_relative_to(tmp_path / 'logs')
    assert cli.write_preview(data, report) == str(directory)
    (directory / 'report.json').write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='report is corrupt'):
        cli.write_preview(data, report)
    (directory / 'assets/djv2.sod').write_bytes(b'broken')
    with pytest.raises(ValueError, match='cache is corrupt'):
        cli.write_preview(data, report)
    monkeypatch.setattr(cli, 'MAX_REPORT', 1)
    monkeypatch.setattr(cli, 'ROOT', tmp_path / 'too-small')
    with pytest.raises(ValueError, match='report exceeds budget'):
        cli.write_preview(data, report)
    assert not (tmp_path / 'too-small').exists()
