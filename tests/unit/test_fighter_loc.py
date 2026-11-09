"""Synthetic localization fixtures; no retail text/assets."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_loc import Localization, LocError


def fixture(locales=1, indexed=True):
    size = 16 + locales * 4
    output = bytearray(b'LOCH' + struct.pack('<III', size, 0, locales) + bytes(locales * 4))
    if indexed:
        output.extend(b'LOCT' + struct.pack('<III', 16, 0x12345678, 0))
        output.extend(struct.pack('<4I', 12, 1, 500, 0))
    for i in range(locales):
        struct.pack_into('<I', output, 16 + i * 4, len(output))
        first, second = f'Original {i}'.encode('utf-16le') + b'\0\0', f'Other {i}'.encode('utf-16le') + b'\0\0'
        length = 24 + len(first) + len(second)
        output.extend(b'LOCL' + struct.pack('<5I', length, 0, 2, 24, 24 + len(first)) + first + second)
    return bytes(output)


def test_indexed_localization_append_preserves_every_locale_and_opaque_header():
    data = fixture(3)
    original = Localization(data)
    additions = {99: ['Alpha', 'Alph\u00e9', '\u732b'], 1: 'Shared'}
    expanded = original.merge(additions)
    result = Localization(expanded)
    assert result.count == 4
    assert result.index_header == original.index_header
    assert result.lookup(12, 2) == 'Other 2'
    assert result.lookup(500) == 'Original 0'
    assert result.lookup(99, 2) == '\u732b'
    assert result.lookup(1, 1) == 'Shared'
    assert expanded == original.merge(dict(reversed(list(additions.items()))))
    assert result.merge(additions) == expanded
    assert original.merge({}) == data
    assert original.data == data


def test_external_index_can_be_inspected_but_not_extended():
    loc = Localization(fixture(4, indexed=False))
    assert len(loc.texts) == 4
    assert loc.merge({}) == loc.data
    with pytest.raises(LocError, match='external'):
        loc.merge({1: 'Name'})


@pytest.mark.parametrize('additions', [{12: 'Conflicting'}, {True: 'Name'}, {-1: 'Name'},
                                        {1: ['Wrong locale count']}, {1: 'embedded\0nul'},
                                        {1: '\ud800'}, {1: 'x' * 20000}])
def test_rejects_conflicts_and_invalid_values(additions):
    with pytest.raises(LocError):
        Localization(fixture(2)).merge(additions)


@pytest.mark.parametrize('offset,value', [(4, 100), (12, 0xffffffff), (16, 0xffffff00),
                                         (24, 1), (36, 0xffffffff), (40, 2)])
def test_malformed_headers_indexes_and_offsets(offset, value):
    data = bytearray(fixture())
    struct.pack_into('<I', data, offset, value)
    with pytest.raises(LocError):
        Localization(bytes(data))


def test_truncated_and_invalid_utf16():
    data = fixture()
    with pytest.raises(LocError):
        Localization(data[:-1])
    loc = Localization(data)
    damaged = bytearray(data)
    start = loc.blocks[0][0] + loc.blocks[0][2][0]
    struct.pack_into('<H', damaged, start, 0xd800)
    with pytest.raises(LocError, match='UTF-16'):
        Localization(bytes(damaged))
