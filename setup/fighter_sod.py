"""Bounded SODB v2 reader for the fighter registry's native-data adapter.

Derived from the owner's dump and our generated reader's data accesses. This
module never changes a dump or executes payloads. Schema members keep their
native descriptors until a consumer proves their interpretation; guessed field
names, save handles and unvalidated writes are deliberately not synthesized.
"""
from dataclasses import dataclass
import hashlib
import struct


MAX_IMAGE = 32 * 1024**2
MAX_ITEMS = 1_000_000
MAX_STRING = 65536
CHARACTER = 0x4ce5b1b2
# Roles independently cross-checked against native StartGame/materialization
# and the owner's XML. These are schema keys, not invented English field names.
SELECTION_FIELD = 0xfcdba74e
CORE_FIELD = 0x232d89a7
STRING_FIELDS = {'DisplayName', 'Entity', 'Model', 'Shadow', 'Thumb'}
INTEGER_FIELDS = {'Charisma', 'CheckIndex', 'Cost', 'Ethnicity', 'FightingStyle',
                  'Health', 'Order', 'Sex', 'Speed', 'Toughness', 'SpeechId', 'BodySize', 'Tier'}


class SodError(ValueError):
    pass


def check(condition, message):
    if not condition:
        raise SodError(message)


def name_hash(value):
    """Native case-sensitive djb2, including the terminating NUL byte."""
    check(isinstance(value, str) and '\0' not in value, 'Invalid native symbol')
    try:
        data = value.encode('ascii')
    except UnicodeEncodeError as error:
        raise SodError('Native symbol must be ASCII') from error
    result = 5381
    for byte in data + b'\0':
        result = (result * 33 + byte) & 0xffffffff
    return result


@dataclass(frozen=True)
class Index:
    tag: int
    keys: tuple
    values: tuple
    keyed: bool


@dataclass(frozen=True)
class Table:
    symbol: int
    count: int
    primary: tuple
    secondary: tuple
    records: tuple


class Database:
    def __init__(self, data):
        check(isinstance(data, bytes) and 24 <= len(data) <= MAX_IMAGE, 'Invalid SODB size')
        self.data = data
        check(data[:4] == b'SODB' and self.word(4) == 2, 'Unsupported SODB version')
        self.schema_fingerprint = self.word(8)
        schema, tables, strings = self.words(12, 3)
        check(24 <= schema < tables < strings <= len(data) - 8, 'Invalid SODB sections')
        self._section(schema, b'SKMA')
        self._section(tables, b'DATA')
        self._section(strings, b'STRT')
        schema_index = self.index(schema, tagged=True)
        check(schema_index.keyed and len(set(schema_index.keys)) == len(schema_index.keys)
              and all(len(v) == 2 for v in schema_index.values), 'Unsupported schema value width/keys')
        self.schema = dict(zip(schema_index.keys, schema_index.values))
        directory = self.index(tables, tagged=True)
        check(directory.keyed and len(set(directory.keys)) == len(directory.keys)
              and all(len(v) == 1 for v in directory.values), 'Unsupported table directory width/keys')
        self.directory = {k: v[0] for k, v in zip(directory.keys, directory.values)}
        check(len(set(self.directory.values())) == len(self.directory), 'Aliased table headers')
        count = self.word(strings + 4)
        self._count(count)
        self.range(strings + 8, count * 8)
        symbols = []
        for i in range(count):
            symbol, offset = self.words(strings + 8 + i * 8, 2)
            if not offset:
                symbols.append((symbol, None))
                continue
            check(offset >= 24, 'String overlaps SODB header')
            self.range(offset, 1)
            end = data.find(b'\0', offset, min(len(data), offset + MAX_STRING + 1))
            check(end >= offset, 'Unterminated/oversized native string')
            try:
                value = data[offset:end].decode('ascii')
            except UnicodeDecodeError as error:
                raise SodError('Unsupported native string encoding') from error
            check(name_hash(value) == symbol, 'Native string hash mismatch')
            symbols.append((symbol, value))
        self.strings = tuple(symbols)
        self._tables = {key: self.table(key) for key in self.directory}

    def range(self, offset, size):
        check(type(offset) is int and type(size) is int and offset >= 0 and size >= 0
              and offset <= len(self.data) and size <= len(self.data) - offset,
              'SODB range exceeds image')

    def word(self, offset):
        self.range(offset, 4)
        return struct.unpack_from('<I', self.data, offset)[0]

    def words(self, offset, count):
        self._count(count)
        self.range(offset, count * 4)
        return struct.unpack_from(f'<{count}I', self.data, offset)

    def _count(self, count):
        check(type(count) is int and 0 <= count <= MAX_ITEMS, 'SODB count exceeds budget')

    def _section(self, offset, tag):
        self.range(offset, 4)
        check(self.data[offset:offset + 4] == tag, 'SODB section tag mismatch')

    def index(self, offset, tagged=False):
        """Native index: optional tag, count, stride; keys then interleaved values."""
        start = offset + (4 if tagged else 0)
        count, stride = self.words(start, 2)
        self._count(count)
        check(stride <= 256, 'SODB index stride exceeds budget')
        width = stride or 1
        self.range(start + 8, count * 4 * (width + bool(stride)))
        keys = self.words(start + 8, count) if stride else ()
        check(all(a <= b for a, b in zip(keys, keys[1:])), 'Unsorted SODB index')
        values_start = start + 8 + (count * 4 if stride else 0)
        values = tuple(self.words(values_start + i * width * 4, width) for i in range(count))
        return Index(self.word(offset) if tagged else 0, keys, values, bool(stride))

    def table(self, symbol):
        check(symbol in self.directory, 'Unknown native table')
        offset = self.directory[symbol]
        tag, primary_offset, secondary_offset, count = self.words(offset, 4)
        check(tag == symbol, 'Table tag mismatch')
        self._count(count)
        primary = self.index(primary_offset)
        secondary = self.index(secondary_offset)
        # BE760/BE870 derive this address as header+16 rather than reading
        # primary_offset. Both access paths must name the same member map.
        check(primary_offset == offset + 16, 'Native primary member map must be inline')
        all_indexes = []
        for group in (primary, secondary):
            check((group.keyed or not group.values) and len(set(group.keys)) == len(group.keys),
                  'Invalid table member map')
            for value in group.values:
                check(len(value) == 1, 'Unsupported table member width')
                subindex = self.index(value[0], tagged=True)
                check(len(subindex.values) == count and all(len(v) == 1 for v in subindex.values),
                      'Table index count/width mismatch')
                pointers = tuple(v[0] for v in subindex.values)
                check(len(set(pointers)) == count, 'Duplicate native records')
                for pointer in pointers:
                    self.range(pointer, 4)
                all_indexes.append(set(pointers))
        check(all_indexes and all(x == all_indexes[0] for x in all_indexes),
              'Table indexes disagree on records')
        return Table(symbol, count, primary.keys, secondary.keys, tuple(sorted(all_indexes[0])))

    def symbol(self, index):
        check(type(index) is int and 0 <= index < len(self.strings), 'Invalid native string index')
        return self.strings[index][1]

    def field(self, table_name, field_name):
        key = name_hash(table_name) if field_name is None else name_hash(table_name) ^ name_hash(field_name)
        check(key in self.schema, 'Unknown native schema field')
        return self.schema[key]

    def record_word(self, offset, table_name, field_name):
        word_offset, descriptor = self.field(table_name, field_name)
        check(word_offset < 4096, 'Native field offset exceeds budget')
        return self.word(offset + word_offset * 4), descriptor

    def character_metadata(self):
        """Inspection evidence only; do not mistake record offsets for permanent IDs."""
        table = self._tables.get(name_hash('Character'))
        check(table is not None, 'Missing Character table')
        check(SELECTION_FIELD in self.schema and CORE_FIELD in self.schema,
              'Missing character identity schema fields')
        rows = []
        for offset in table.records:
            name_index, _ = self.record_word(offset, 'Character', None)
            row = {'record_offset': offset, 'name': self.symbol(name_index), 'fields': {},
                   'native_binding': {'selection_key': self.word(offset + self.schema[SELECTION_FIELD][0] * 4),
                                      'core_id': self.word(offset + self.schema[CORE_FIELD][0] * 4)}}
            for field in ('BodySize', 'Charisma', 'CheckIndex', 'Cost', 'DisplayName', 'Entity',
                          'Ethnicity', 'FightingStyle', 'Health', 'Model', 'Order', 'Sex',
                          'Shadow', 'SpeechId', 'Speed', 'Thumb', 'Toughness', 'Tier'):
                value, descriptor = self.record_word(offset, 'Character', field)
                row['fields'][field] = {'word': value, 'descriptor': descriptor}
                if field in STRING_FIELDS:
                    row['fields'][field]['symbol'] = self.symbol(value)
            rows.append(row)
        return {'source_sha256': hashlib.sha256(self.data).hexdigest(),
                'schema_fingerprint': f'{self.schema_fingerprint:08x}',
                'table_count': len(self._tables), 'schema_fields': len(self.schema),
                'string_count': len(self.strings), 'character_count': table.count, 'characters': rows}

    def extend_character_records(self, additions, edits=None, *, selection_keys=None, deferred_keys=None,
                                 character_cores=None):
        """Native-cache construction experiment, not a runnable mod installer.

        Additions use stable keys, existing template record offsets and named
        native fields. Optional edits change named fields in existing records;
        all other record bytes/string IDs are retained. Rebuilds
        indexes; reports native rank changes that a save bridge MUST account
        for. No native runtime capability is implied by a successful round-trip.
        """
        check(isinstance(additions, list) and len(additions) <= 16384, 'Invalid additions budget')
        if character_cores is not None:
            check(type(character_cores) is dict
                  and set(character_cores) == {a.get('key') for a in additions if isinstance(a, dict)}
                  and all(type(core) is int and 142 <= core <= 16384 for core in character_cores.values()),
                  'Owned character cores must cover exactly the added records within the runtime budget')
        deferred_keys = set() if deferred_keys is None else deferred_keys
        check(isinstance(deferred_keys, set) and deferred_keys <= {a.get('key') for a in additions if isinstance(a, dict)},
              'Deferred native records must identify added templates')
        if selection_keys is not None:
            check(isinstance(selection_keys, dict) and set(selection_keys) == {a.get('key') for a in additions if isinstance(a, dict)},
                  'Selection allocation must cover exactly the added fighter keys')
        edits = [] if edits is None else edits
        check(isinstance(edits, list) and len(edits) <= 16384, 'Invalid edits budget')
        table = self._tables.get(CHARACTER)
        check(table is not None, 'Missing Character table')
        if not additions and not edits:
            return self.data, {'runtime_ready': False, 'bindings': {},
                               'retail_name_index_rank_remap': {}, 'native_signed_byte_overflow': [],
                               'edited_records': []}
        check(SELECTION_FIELD in self.schema and CORE_FIELD in self.schema,
              'Missing character identity schema fields')
        native_offset, native_type = self.schema[SELECTION_FIELD]
        check((native_offset, native_type) == (8, 2), 'Unsupported selection field layout')
        check(self.schema[CORE_FIELD] == (10, 2), 'Unsupported core field layout')
        for offset in table.records:
            self.range(offset, 26 * 4)
        output = bytearray(self.data)
        symbols = list(self.strings)
        symbol_lookup = {s: i for i, (_, s) in enumerate(symbols) if s is not None}
        string_pointers = [self.word(self.word(20) + 8 + i * 8 + 4) for i in range(len(symbols))]

        def emit(blob):
            while len(output) % 4:
                output.append(0)
            check(len(output) + len(blob) <= MAX_IMAGE, 'Expanded SODB exceeds image budget')
            offset = len(output)
            output.extend(blob)
            return offset

        def packed(values):
            return struct.pack(f'<{len(values)}I', *values)

        def intern(value):
            check(isinstance(value, str) and len(value) <= 256, 'Invalid added native string')
            if value in symbol_lookup:
                return symbol_lookup[value]
            hashed = name_hash(value)
            pointer = emit(value.encode('ascii') + b'\0')
            index = len(symbols)
            symbols.append((hashed, value))
            string_pointers.append(pointer)
            symbol_lookup[value] = index
            return index

        def apply_fields(row, fields):
            check(isinstance(fields, dict) and fields.keys() <= STRING_FIELDS | INTEGER_FIELDS,
                  'Unsupported native field')
            for name, value in sorted(fields.items()):
                word_offset, descriptor = self.field('Character', name)
                check(word_offset < 26, 'Native field exceeds character record')
                if name in STRING_FIELDS:
                    check(descriptor == 1, 'Unexpected native string field type')
                    value = intern(value)
                else:
                    check(type(value) is int and 0 <= value <= 0x7fffffff, 'Invalid native integer field')
                    if name == 'Tier':
                        check((word_offset, descriptor) == (24, 6) and value in (1, 2, 4, 8),
                              'Unsupported native roster tier')
                struct.pack_into('<I', row, word_offset * 4, value)

        edited = set()
        check(all(isinstance(e, dict) and set(e) == {'template', 'fields'}
                  and type(e['template']) is int for e in edits), 'Invalid native edit shape')
        for edit in sorted(edits, key=lambda e: e['template']):
            offset = edit['template']
            check(type(offset) is int and offset in table.records and offset not in edited,
                  'Unknown/duplicate native edit record')
            row = bytearray(self.data[offset:offset + 104])
            apply_fields(row, edit['fields'])
            output[offset:offset + 104] = row
            edited.add(offset)

        old_names = [self.symbol(self.word(o)) for o in table.records]
        check(all(n is not None for n in old_names), 'Missing character names')
        names = set(old_names)
        hashes = {name_hash(n) for n in old_names}
        check(len(hashes) == table.count, 'Ambiguous native character names')
        identifiers = {self.word(o + native_offset * 4) for o in table.records}
        # Logical templates and indexed participant banks are separate selection
        # domains. They may share a number, regardless of stable-key sort order,
        # but neither may collide with retail or duplicate within its own domain.
        deferred_identifiers = set(identifiers)
        next_id = max(identifiers, default=0) + 1
        new_rows = []
        bindings = {}
        # Stable input order is not part of the binding policy.
        check(all(isinstance(a, dict) and {'key', 'template', 'fields'} <= a.keys()
                  and a.keys() <= {'key', 'template', 'fields', 'native_name'} for a in additions),
              'Invalid native addition shape')
        check(all(isinstance(a['key'], str) for a in additions), 'Invalid native addition key')
        for addition in sorted(additions, key=lambda a: a['key']):
            key = addition['key']
            check(len(key) <= 161 and key.count('/') == 1
                  and all(part and part[0] != '-' and part[-1] != '-'
                          and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in part)
                          for part in key.split('/')), 'Invalid stable character key')
            check(key not in bindings, 'Duplicate character key')
            native_name = addition.get('native_name', key)
            check(isinstance(native_name, str) and 0 < len(native_name) <= 256,
                  'Invalid native character name')
            check(native_name not in names and name_hash(native_name) not in hashes,
                  'Duplicate/colliding character key')
            check(type(addition['template']) is int and addition['template'] in table.records,
                  'Unknown template record')
            row = bytearray(self.data[addition['template']:addition['template'] + 26 * 4])
            struct.pack_into('<I', row, 0, intern(native_name))
            if selection_keys is not None:
                next_id = selection_keys[key]
                allocated = deferred_identifiers if key in deferred_keys else identifiers
                check(type(next_id) is int and next_id >= 100 and next_id not in allocated,
                      'Invalid/colliding allocated selection key')
            else:
                while next_id in identifiers or next_id in (98, 99):
                    next_id += 1
            check(next_id <= 0x7fffffff, 'Native selection key exhausted')
            struct.pack_into('<I', row, native_offset * 4, next_id)
            apply_fields(row, addition['fields'])
            if character_cores is not None:
                # Internal compiler output, separate from package-authored fields.
                # Bind before building indexes, participant windows and receipts.
                struct.pack_into('<I', row, 40, character_cores[key])
            offset = emit(row)
            # Runtime-owned binding windows retain validated templates/string
            # IDs without exposing every logical fighter to fixed native lists.
            if key not in deferred_keys:
                new_rows.append(offset)
            # Legacy receipt key: this is the final one-based character core;
            # it may now be allocated by the independent motion compiler.
            bindings[key] = {'selection_key': next_id, 'inherited_core_id': struct.unpack_from('<I', row, 40)[0],
                             'record_offset': offset, 'native_name': native_name}
            if key not in deferred_keys:
                identifiers.add(next_id)
            else:
                deferred_identifiers.add(next_id)
            next_id += 1
            names.add(native_name)
            hashes.add(name_hash(native_name))

        def index_blob(tag, keys, values, stride):
            header = ([] if tag is None else [tag]) + [len(values), stride]
            return packed(header + (list(keys) if stride else []) + [w for value in values for w in value])

        native_header = self.directory[CHARACTER]
        groups = []
        for group_offset in self.words(native_header + 4, 2):
            group = self.index(group_offset)
            pointers = []
            for member_key, (old_index_offset,) in zip(group.keys, group.values):
                old_index = self.index(old_index_offset, tagged=True)
                if old_index.keyed:
                    pairs = []
                    word_offset, descriptor = self.schema[member_key]
                    check(word_offset < 26, 'Native index field exceeds character record')
                    for original_key, (pointer,) in zip(old_index.keys, old_index.values):
                        original_value = self.word(pointer + word_offset * 4)
                        if member_key == CHARACTER or descriptor == 1:
                            check(original_value < len(self.strings), 'Bad original indexed string reference')
                            original_value = self.strings[original_value][0]
                        check(original_value == original_key, 'Unsupported native index key encoding')
                    for offset in [value[0] for value in old_index.values] + new_rows:
                        value = struct.unpack_from('<I', output, offset + word_offset * 4)[0]
                        if member_key == CHARACTER or descriptor == 1:
                            check(value < len(symbols), 'Bad indexed string reference')
                            value = symbols[value][0]
                        pairs.append((value, offset))
                    pairs.sort(key=lambda x: (x[0], x[1]))
                    keys = [key for key, _ in pairs]
                    values = [(offset,) for _, offset in pairs]
                else:
                    # An ordinal index must preserve original positions. New
                    # records append; do not pretend sorting preserves handles.
                    keys = []
                    values = list(old_index.values) + [(offset,) for offset in new_rows]
                pointers.append((emit(index_blob(old_index.tag, keys, values, int(old_index.keyed))),))
            # The member set/width is unchanged. Retain its address and rewrite
            # its pointers in place so inline and pointer-based native readers
            # observe the very same rebuilt indexes. Relocating this map alone
            # leaves BE760/BE870 silently using the old Character name index.
            member_map = index_blob(None, group.keys, pointers, 1)
            self.range(group_offset, len(member_map))
            output[group_offset:group_offset + len(member_map)] = member_map
            groups.append(group_offset)
        struct.pack_into('<3I', output, native_header + 4, *groups, table.count + len(new_rows))
        strings_offset = emit(packed([int.from_bytes(b'STRT', 'little'), len(symbols)]
            + [word for (hashed, _), pointer in zip(symbols, string_pointers) for word in (hashed, pointer)]))
        struct.pack_into('<I', output, 20, strings_offset)
        rebuilt = Database(bytes(output))
        check(rebuilt._tables[CHARACTER].count == table.count + len(new_rows), 'Expanded table did not round-trip')
        for offset in table.records:
            if offset not in edited:
                check(rebuilt.data[offset:offset + 104] == self.data[offset:offset + 104], 'Retail record changed')
        primary_group = self.index(self.word(native_header + 4))
        old_index_offset = dict(zip(primary_group.keys, primary_group.values))[CHARACTER][0]
        new_group = rebuilt.index(rebuilt.word(native_header + 4))
        new_index_offset = dict(zip(new_group.keys, new_group.values))[CHARACTER][0]
        old_order = [v[0] for v in self.index(old_index_offset, True).values]
        new_order = [v[0] for v in rebuilt.index(new_index_offset, True).values]
        ranks = {offset: rank for rank, offset in enumerate(new_order)}
        remap = {old: ranks[offset] for old, offset in enumerate(old_order)}
        return bytes(output), {'runtime_ready': False, 'bindings': bindings,
                               'edited_records': sorted(edited),
                               'retail_name_index_rank_remap': remap,
                               'native_signed_byte_overflow': [k for k, v in bindings.items() if v['selection_key'] > 127]}
