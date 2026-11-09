"""Runtime-owned four-participant binding window, never a package format.

Logical fighters retain historical identities. Only four indexed native rows
are resident; typed, unindexed records supply their values at match setup.
FWR1 contains offsets into the separately hash-verified generated SODB, not
guest pointers, instructions, or author-selected native IDs.
"""
import struct

from fighter_bindings import MAX_RANK, native_rows
from fighter_sod import Database, name_hash

BANKS = 4
FIRST_SELECTION = 100
MAX_FIGHTERS = 16380
MAX_FILE = 24 + BANKS * 24 + MAX_FIGHTERS * 24


def bank_key(index):
    if type(index) is not int or not 0 <= index < BANKS:
        raise ValueError('Invalid fighter bank')
    return f'runtime-bank/slot-{index}'


def build_window(data, native, additions, ledger):
    db = Database(data)
    rows = native_rows(db)
    table = next(iter(rows.values()))['handle'] >> 24
    banks = []
    for index in range(BANKS):
        key = bank_key(index)
        binding = native['bindings'][key]
        row = rows[binding['native_name']]
        banks.append({'native_handle': row['handle'], 'private_handle': table << 24 | (MAX_RANK - BANKS + 1 + index),
                      'symbol_hash': name_hash(row['name']), 'selection_key': FIRST_SELECTION + index,
                      'record_offset': row['record_offset'], 'core_id': row['native_binding']['core_id']})
    fighters = []
    for addition in additions:
        key = addition['key']
        binding, identity = native['bindings'][key], ledger['fighters'][key]
        fighters.append({'stable_handle': identity['handle'], 'selection_key': identity['selection'],
                         'symbol_hash': name_hash(addition['native_name']), 'record_offset': binding['record_offset'],
                         'core_id': binding['inherited_core_id'], 'reserved': 0})
    return {'banks': banks, 'fighters': sorted(fighters, key=lambda row: row['selection_key']),
            'table': table, 'sod_size': len(data)}


def encode_window(window):
    banks, fighters = window['banks'], window['fighters']
    if len(banks) != BANKS or not 0 < len(fighters) <= MAX_FIGHTERS:
        raise ValueError('Invalid fighter window population')
    output = bytearray(b'FWR1' + struct.pack('<5I', 1, len(fighters), BANKS, window['table'], window['sod_size']))
    for rows, fields in ((banks, ('native_handle', 'private_handle', 'symbol_hash', 'selection_key', 'record_offset', 'core_id')),
                         (fighters, ('stable_handle', 'selection_key', 'symbol_hash', 'record_offset', 'core_id', 'reserved'))):
        for row in rows:
            values = [row[field] for field in fields]
            if any(type(value) is not int or not 0 <= value <= 0xffffffff for value in values):
                raise ValueError('Invalid fighter window word')
            output += struct.pack('<6I', *values)
    return bytes(output)
