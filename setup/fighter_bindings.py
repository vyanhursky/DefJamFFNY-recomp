"""Append-only identity allocation for the fighter adapter.

This is runtime-owned metadata, not a field in a mod manifest. Removed fighters
remain dormant entries and keep their selection tokens and persistent handles.
Native sorted-row ranks are derived anew for each snapshot and never persisted
as fighter identity. The ledger alone is not a native save migration.
"""
from copy import deepcopy
import hashlib
import re
import struct

from fighter_registry import MAX_DEFINITIONS, key
from fighter_sod import CHARACTER, Database, name_hash

SCHEMA = 'fighter-binding-ledger-1'
ABSENT = 0xffffffff
MAX_RANK = 0x7fffff  # bit 23 is metadata in the native unlock set


def symbol(identifier):
    return 'fm-' + hashlib.sha256(identifier.encode('ascii')).hexdigest()[:16]


def native_rows(db):
    table = list(db.directory).index(CHARACTER)
    if table >= 256:
        raise ValueError('Character table does not fit the native packed handle')
    rows = sorted(db.character_metadata()['characters'], key=lambda row: name_hash(row['name']))
    if len(rows) > MAX_RANK:
        raise ValueError('Character ranks overlap native unlock metadata')
    return {row['name']: dict(row, handle=table << 24 | rank) for rank, row in enumerate(rows)}


def seed(db, source_sha256, retail):
    rows = native_rows(db)
    return {'schema': SCHEMA, 'source_sha256': source_sha256,
            'fighters': {identifier: {'symbol': row['name'], 'handle': rows[row['name']]['handle'],
                                      'selection': row['native_binding']['selection_key']}
                         for identifier, row in sorted(retail.items())}}


def allocate(baseline, identifiers, previous=None):
    """Return a new ledger. Never drop/reuse a key or mutate the supplied state."""
    if not isinstance(baseline, dict) or baseline.get('schema') != SCHEMA:
        raise ValueError('Invalid binding baseline')
    ledger = deepcopy(baseline if previous is None else previous)
    if not isinstance(ledger, dict) or set(ledger) != {'schema', 'source_sha256', 'fighters'}:
        raise ValueError('Invalid binding ledger shape')
    if ledger['schema'] != SCHEMA or ledger['source_sha256'] != baseline['source_sha256']:
        raise ValueError('Binding ledger belongs to a different baseline or schema')
    entries = ledger['fighters']
    if not isinstance(entries, dict) or len(entries) > MAX_DEFINITIONS:
        raise ValueError('Binding ledger exceeds definition budget')
    handles, selections, hashes = set(), set(), set()
    table = next(iter(baseline['fighters'].values()))['handle'] >> 24
    for identifier, entry in entries.items():
        key(identifier)
        if not isinstance(entry, dict) or set(entry) != {'symbol', 'handle', 'selection'}:
            raise ValueError('Invalid binding ledger entry')
        if identifier.startswith('retail/'):
            if baseline['fighters'].get(identifier) != entry:
                raise ValueError('Binding ledger changed a retail identity')
        elif entry['symbol'] != symbol(identifier):
            raise ValueError('Binding symbol does not match its stable key')
        if not isinstance(entry['symbol'], str) or not re.fullmatch(r'[\x20-\x7e]{1,256}', entry['symbol']):
            raise ValueError('Invalid binding symbol')
        handle, selection = entry['handle'], entry['selection']
        if type(handle) is not int or handle >> 24 != table or not 0 <= (handle & 0xffffff) <= MAX_RANK:
            raise ValueError('Invalid persistent fighter handle')
        if type(selection) is not int or not 0 <= selection <= 0x7fffffff:
            raise ValueError('Invalid persistent selection key')
        if not identifier.startswith('retail/') and selection < 100:
            raise ValueError('Custom binding overlaps reserved retail/created selections')
        hashed = name_hash(entry['symbol'])
        if handle in handles or selection in selections or hashed in hashes:
            raise ValueError('Duplicate/colliding persistent fighter binding')
        handles.add(handle); selections.add(selection); hashes.add(hashed)
    if not baseline['fighters'].keys() <= entries.keys():
        raise ValueError('Binding ledger lost retail identities')
    wanted = set(identifiers)
    for identifier in wanted:
        key(identifier)
    if len(entries.keys() | wanted) > MAX_DEFINITIONS:
        raise ValueError('Binding ledger exceeds historical definition budget')
    next_rank = max((value & 0xffffff for value in handles), default=-1) + 1
    next_selection = max(100, max(selections, default=99) + 1)
    for identifier in sorted(wanted - entries.keys()):
        if identifier.startswith('retail/') or next_rank > MAX_RANK or next_selection > 0x7fffffff:
            raise ValueError('Persistent fighter binding space exhausted or unknown retail identity')
        native_symbol = symbol(identifier)
        if name_hash(native_symbol) in hashes:
            raise ValueError('Native symbol hash collision; stable key needs an explicit migration')
        entries[identifier] = {'symbol': native_symbol, 'handle': table << 24 | next_rank,
                               'selection': next_selection}
        hashes.add(name_hash(native_symbol))
        next_rank += 1
        next_selection += 1
    ledger['fighters'] = dict(sorted(entries.items()))
    return ledger


def materialize(db, ledger):
    """Bind historical identity to current rows; unavailable rows stay explicit."""
    rows = native_rows(db)
    result = {}
    for identifier, entry in ledger['fighters'].items():
        row = rows.get(entry['symbol'])
        if row and row['native_binding']['selection_key'] != entry['selection']:
            raise ValueError('Native row changed its allocated selection key')
        result[identifier] = {'stable_handle': entry['handle'], 'native_handle': row['handle'] if row else ABSENT,
                              'symbol_hash': name_hash(entry['symbol']), 'selection_key': entry['selection'],
                              'core_id': row['native_binding']['core_id'] if row else 0,
                              'custom': not identifier.startswith('retail/'), 'available': row is not None}
    return result


def encode_bindings(bindings):
    """FMB1: bounded immutable rows plus checked native/key/selection indexes."""
    if not isinstance(bindings, dict) or not 0 < len(bindings) <= MAX_DEFINITIONS:
        raise ValueError('Invalid runtime fighter binding budget')
    rows = sorted(bindings.values(), key=lambda row: row['stable_handle'])
    table = rows[0]['stable_handle'] >> 24
    active = [i for i, row in enumerate(rows) if row['available']]
    indexes = [sorted(active, key=lambda i: rows[i]['native_handle']),
               sorted(range(len(rows)), key=lambda i: rows[i]['symbol_hash']),
               sorted(range(len(rows)), key=lambda i: rows[i]['selection_key'])]
    output = bytearray(b'FMB1' + struct.pack('<5I', 1, len(rows), len(active), table, 0))
    for row in rows:
        fields = [row['stable_handle'], row['native_handle'], row['symbol_hash'], row['selection_key'], row['core_id'],
                  int(row['custom']) | int(row['available']) << 1]
        if any(type(value) is not int or not 0 <= value <= 0xffffffff for value in fields):
            raise ValueError('Invalid runtime fighter binding word')
        output += struct.pack('<6I', *fields)
    for index in indexes:
        output += struct.pack(f'<{len(index)}I', *index)
    return bytes(output)
