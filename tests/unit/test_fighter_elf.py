"""Game-free data-model envelope and relocation trust-boundary fixtures."""
from pathlib import Path
import struct
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_elf import Model, ModelError, SECTION_NAMES


def fixture():
    section_names = b'\0' + b'\0'.join(n.encode() for n in SECTION_NAMES[1:]) + b'\0'
    symbol_names = b'\0root\0known-data\0'
    names = [0] + [section_names.index(n.encode() + b'\0') for n in SECTION_NAMES[1:]]
    data = bytearray(64)
    data[:16] = b'\x7fELF\x01\x01\x01' + bytes(9)
    payloads = [b'', bytes(16), section_names, symbol_names,
                bytes(16) + struct.pack('<IIIBBH', 1, 0, 16, 17, 0, 1)
                + struct.pack('<IIIBBH', 6, 0, 0, 16, 0, 0),
                struct.pack('<II', 0, 1 << 8 | 2) + struct.pack('<II', 4, 2 << 8 | 2)]
    rows = [(0,) * 10]
    for i in range(1, 6):
        align = 16 if i == 1 else 4 if i >= 4 else 1
        data += bytes(-len(data) % align)
        offset = len(data)
        data += payloads[i]
        rows.append((names[i], (0, 1, 3, 3, 2, 9)[i], 3 if i == 1 else 0, 0, offset,
                     len(payloads[i]), 3 if i == 4 else 4 if i == 5 else 0,
                     1 if i in (4, 5) else 0, align, 16 if i == 4 else 8 if i == 5 else 0))
    data += bytes(-len(data) % 4)
    sections = len(data)
    data += b''.join(struct.pack('<10I', *r) for r in rows)
    struct.pack_into('<HHIIIIIHHHHHH', data, 16, 1, 8, 1, 0, 0, sections, 0x20924000, 52, 0, 0, 40, 6, 2)
    return bytes(data), rows, sections


def test_data_model_and_explicit_import_allowlist():
    data, _, _ = fixture()
    model = Model(data)
    assert model.imports == {'known-data'} and model.exports == {'root'}
    assert model.relocations == 2
    assert model.metadata()['data_bytes'] == 16
    assert not model.metadata()['runtime_ready']
    model.require_imports({'known-data'})
    with pytest.raises(ModelError, match='forbidden model imports'):
        model.require_imports({'different-data'})


@pytest.mark.parametrize('mutation', ['truncated', 'machine', 'executable', 'overlap', 'section-count',
                                     'function-symbol', 'absolute-symbol', 'bad-symbol-range',
                                     'duplicate-relocation', 'relocation-range', 'relocation-symbol',
                                     'relocation-method', 'external-addend', 'local-addend'])
def test_rejects_executable_and_malformed_model_inputs(mutation):
    original, rows, sections = fixture()
    data = bytearray(original)
    patches = {
        'machine': (18, '<H', 3), 'executable': (sections + 40 + 8, '<I', 7),
        'overlap': (sections + 80 + 16, '<I', rows[1][4]),
        'section-count': (48, '<H', 65535),
        'function-symbol': (rows[4][4] + 16 + 12, '<B', 18),
        'absolute-symbol': (rows[4][4] + 16 + 14, '<H', 0xfff1),
        'bad-symbol-range': (rows[4][4] + 16 + 8, '<I', 17),
        'duplicate-relocation': (rows[5][4] + 8, '<I', 0),
        'relocation-range': (rows[5][4], '<I', 16),
        'relocation-symbol': (rows[5][4] + 4, '<I', 999 << 8 | 2),
        'relocation-method': (rows[5][4] + 4, '<I', 1 << 8 | 4),
        'external-addend': (rows[1][4] + 4, '<I', 1),
        'local-addend': (rows[1][4], '<I', 0xffffffff),
    }
    if mutation == 'truncated':
        data = data[:-1]
    else:
        offset, format, value = patches[mutation]
        struct.pack_into(format, data, offset, value)
    with pytest.raises(ModelError):
        Model(bytes(data))
