"""Synthetic native-format databases; no game bytes or extracted fixtures."""
import importlib.util
from pathlib import Path
import struct
import sys

import pytest

spec = importlib.util.spec_from_file_location('fighter_sod',
    Path(__file__).resolve().parents[2] / 'setup/fighter_sod.py')
sod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sod
spec.loader.exec_module(sod)


FIELDS = {'BodySize': (1, 4), 'Charisma': (2, 2), 'CheckIndex': (3, 2), 'Cost': (4, 2),
          'DisplayName': (5, 1), 'SpeechId': (21, 2),
          'Entity': (6, 1), 'Ethnicity': (7, 4), 'FightingStyle': (9, 6),
          'Health': (12, 2), 'Model': (14, 1), 'Order': (15, 2),
          'Sex': (19, 4), 'Shadow': (20, 1), 'Speed': (22, 2),
          'Thumb': (23, 1), 'Toughness': (25, 2)}


def native_fixture():
    image = bytearray(24)

    def emit(data):
        offset = len(image)
        image.extend(data)
        return offset

    def words(values):
        return struct.pack(f'<{len(values)}I', *values)

    def index(tag, keys, values, stride):
        assert not stride or len(keys) == len(values)
        head = ([] if tag is None else [tag]) + [len(values), stride]
        return emit(words(head + (keys if stride else []) + [w for v in values for w in v]))

    character = sod.name_hash('Character')
    schema = {character: (0, 0x02000000)}
    schema[sod.SELECTION_FIELD] = (8, 2)
    schema[sod.CORE_FIELD] = (10, 2)
    schema.update({character ^ sod.name_hash(name): value for name, value in FIELDS.items()})
    keys = sorted(schema)
    schema_at = index(int.from_bytes(b'SKMA', 'little'), keys, [schema[k] for k in keys], 2)
    data_at = emit(words([int.from_bytes(b'DATA', 'little'), 1, 1, character, 0]))
    symbol_names = [None, 'Test Alpha', 'Test Beta', 'SyntheticEntity', 'SyntheticModel', 'SyntheticImage']
    record_offsets = []
    for name_index in (1, 2):
        row = [0] * 26
        row[0] = name_index
        for name, (position, descriptor) in FIELDS.items():
            row[position] = (name_index if name == 'DisplayName' else 3 if name == 'Entity' else
                             4 if name == 'Model' else 5 if name in ('Shadow', 'Thumb') else 25)
        row[8] = name_index
        row[10] = 100 + name_index
        record_offsets.append(emit(words(row)))
    pairs = sorted((sod.name_hash(symbol_names[i + 1]), o) for i, o in enumerate(record_offsets))
    name_index = index(character, [x[0] for x in pairs], [(x[1],) for x in pairs], 1)
    numeric_index = index(sod.SELECTION_FIELD, [1, 2], [(x,) for x in record_offsets], 1)
    health_key = character ^ sod.name_hash('Health')
    health_index = index(health_key, [25, 25], [(x,) for x in record_offsets], 1)
    model_key = character ^ sod.name_hash('Model')
    model_index = index(model_key, [sod.name_hash('SyntheticModel')] * 2, [(x,) for x in record_offsets], 1)
    list_key = sod.name_hash('SyntheticRows')
    record_list = index(list_key, [], [(x,) for x in record_offsets], 0)
    indexes = {character: name_index, sod.SELECTION_FIELD: numeric_index,
               health_key: health_index, model_key: model_index}
    primary = index(None, sorted(indexes), [(indexes[k],) for k in sorted(indexes)], 1)
    secondary = index(None, [list_key], [(record_list,)], 1)
    table_at = emit(words([character, primary, secondary, 2]))
    struct.pack_into('<I', image, data_at + 16, table_at)
    string_offsets = [0] + [emit(s.encode('ascii') + b'\0') for s in symbol_names[1:]]
    while len(image) % 4:
        image.append(0)
    strings_at = emit(words([int.from_bytes(b'STRT', 'little'), len(symbol_names)]
        + [w for name, offset in zip(symbol_names, string_offsets)
           for w in (sod.name_hash(name) if name else 0, offset)]))
    struct.pack_into('<4s5I', image, 0, b'SODB', 2, 0x12345678, schema_at, data_at, strings_at)
    return bytes(image), {'schema': schema_at, 'data': data_at, 'strings': strings_at,
                          'table': table_at, 'primary': primary, 'secondary': secondary,
                          'name_index': name_index, 'numeric_index': numeric_index,
                          'record_list': record_list, 'records': record_offsets}


def changed(data, offset, value):
    result = bytearray(data)
    struct.pack_into('<I', result, offset, value)
    return bytes(result)


def test_native_symbol_algorithm():
    assert sod.name_hash('Character') == 0x4ce5b1b2
    assert sod.name_hash('v00') == 0x7c9e969b
    assert sod.name_hash('Character') != sod.name_hash('character')
    for value in ['embedded\0nul', '\u2603']:
        with pytest.raises(sod.SodError):
            sod.name_hash(value)


def test_schema_and_character_projection():
    data, layout = native_fixture()
    db = sod.Database(data)
    rows = db.character_metadata()
    assert rows['character_count'] == 2
    assert rows['characters'][0]['name'] == 'Test Alpha'
    assert rows['characters'][0]['fields']['Model']['symbol'] == 'SyntheticModel'
    assert db.field('Character', 'Health') == (12, 2)
    assert data == db.data
    assert layout['strings'] > layout['records'][0]  # Relocated directory can follow string payloads.


@pytest.mark.parametrize('field,value', [('version', 3), ('schema_offset', 0xfffffff0),
                                       ('table_offset', 0), ('string_offset', 8)])
def test_bad_header(field, value):
    data, _ = native_fixture()
    offset = {'version': 4, 'schema_offset': 12, 'table_offset': 16, 'string_offset': 20}[field]
    with pytest.raises(sod.SodError):
        sod.Database(changed(data, offset, value))


def test_truncated_and_oversized_counts():
    data, layout = native_fixture()
    for broken in [data[:10], data[:-1], changed(data, layout['schema'] + 4, 0xffffffff),
                   changed(data, layout['strings'] + 4, 0xffffffff)]:
        with pytest.raises(sod.SodError):
            sod.Database(broken)


def test_indexes_must_agree():
    data, layout = native_fixture()
    # Replace one pointer in the unkeyed record list with another in-image pointer.
    broken = changed(data, layout['record_list'] + 12, layout['records'][0] + 4)
    with pytest.raises(sod.SodError, match='disagree'):
        sod.Database(broken)


def test_duplicate_records_and_key_order():
    data, layout = native_fixture()
    for broken in [changed(data, layout['record_list'] + 16, layout['records'][0]),
                   changed(data, layout['name_index'] + 12, 0xffffffff)]:
        with pytest.raises(sod.SodError):
            sod.Database(broken)


def test_string_hash_and_offset_validation():
    data, layout = native_fixture()
    entry = layout['strings'] + 8 + 8  # second string entry
    for broken in [changed(data, entry, 1), changed(data, entry + 4, 0xffffffff),
                   changed(data, entry + 4, 4)]:
        with pytest.raises(sod.SodError):
            sod.Database(broken)


def test_bad_table_and_member_width():
    data, layout = native_fixture()
    for broken in [changed(data, layout['table'], 123),
                   changed(data, layout['primary'] + 4, 257),
                   changed(data, layout['table'] + 12, 3)]:
        with pytest.raises(sod.SodError):
            sod.Database(broken)


def test_general_native_extension_roundtrip_and_original_records_preserved():
    data, layout = native_fixture()
    db = sod.Database(data)
    additions = [{'key': 'alpha/one', 'template': layout['records'][0],
                  'fields': {'Model': 'AddedModel', 'Health': 70}},
                 {'key': 'beta/two', 'template': layout['records'][1], 'fields': {'Health': 80}}]
    expanded, report = db.extend_character_records(additions)
    rows = sod.Database(expanded).character_metadata()
    assert rows['character_count'] == 4
    by_name = {r['name']: r for r in rows['characters']}
    assert by_name['alpha/one']['fields']['Model']['symbol'] == 'AddedModel'
    assert by_name['beta/two']['fields']['Health']['word'] == 80
    assert report['bindings']['alpha/one']['inherited_core_id'] == 101
    assert not report['runtime_ready']
    for offset in layout['records']:
        assert expanded[offset:offset + 104] == data[offset:offset + 104]
    assert expanded == db.extend_character_records(list(reversed(additions)))[0]


def test_native_container_over_255_is_not_engine_acceptance():
    data, layout = native_fixture()
    additions = [{'key': f'large/fighter-{i}', 'template': layout['records'][0], 'fields': {}}
                 for i in range(300)]
    expanded, report = sod.Database(data).extend_character_records(additions)
    assert sod.Database(expanded).character_metadata()['character_count'] == 302
    assert len(report['native_signed_byte_overflow']) > 0
    assert not report['runtime_ready']
    assert len(report['retail_name_index_rank_remap']) == 2


def test_native_extension_rejects_raw_fields_and_bad_templates():
    data, layout = native_fixture()
    for addition in [
        {'key': 'alpha/one', 'template': layout['records'][0] + 4, 'fields': {}},
        {'key': 'alpha/one', 'template': layout['records'][0], 'fields': {'native_address': 123}},
        {'key': 'alpha/one', 'template': layout['records'][0], 'fields': {'Health': True}},
        {'key': 'alpha/one', 'template': layout['records'][0], 'fields': {'Model': '\u2603'}},
    ]:
        with pytest.raises(sod.SodError):
            sod.Database(data).extend_character_records([addition])


def test_empty_native_extension_is_exact_noop():
    data, _ = native_fixture()
    assert sod.Database(data).extend_character_records([])[0] == data


def test_rebuilt_numeric_index_resolves_high_keys_and_skips_created_token():
    data, layout = native_fixture()
    additions = [{'key': f'large/fighter-{i}', 'template': layout['records'][0], 'fields': {}}
                 for i in range(300)]
    expanded, report = sod.Database(data).extend_character_records(additions)
    db = sod.Database(expanded)
    primary = db.index(db.word(db.directory[sod.CHARACTER] + 4))
    index_offset = dict(zip(primary.keys, primary.values))[sod.SELECTION_FIELD][0]
    numeric = db.index(index_offset, tagged=True)
    assert numeric.keys == tuple(sorted(numeric.keys))
    assert len(set(numeric.keys)) == 302
    assert 99 not in numeric.keys
    mapping = dict(zip(numeric.keys, numeric.values))
    for name, binding in report['bindings'].items():
        row = mapping[binding['selection_key']][0]
        assert db.symbol(db.word(row)) == name
        assert db.word(row + 32) == binding['selection_key']
    # The ordinal list retains original positions independently of sorted keys.
    secondary = db.index(db.word(db.directory[sod.CHARACTER] + 8))
    ordinal = db.index(secondary.values[0][0], tagged=True)
    assert ordinal.values[:2] == tuple((r,) for r in layout['records'])
