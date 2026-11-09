"""Game-free data-model envelope and relocation trust-boundary fixtures."""
from pathlib import Path
import struct
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_elf import Model, ModelError, SECTION_NAMES


def fixture(root_name='root', import_name='known-data'):
    section_names = b'\0' + b'\0'.join(n.encode() for n in SECTION_NAMES[1:]) + b'\0'
    symbol_names = b'\0' + root_name.encode('ascii') + b'\0' + import_name.encode('ascii') + b'\0'
    names = [0] + [section_names.index(n.encode() + b'\0') for n in SECTION_NAMES[1:]]
    data = bytearray(64)
    data[:16] = b'\x7fELF\x01\x01\x01' + bytes(9)
    payloads = [b'', bytes(16), section_names, symbol_names,
                bytes(16) + struct.pack('<IIIBBH', 1, 0, 16, 17, 0, 1)
                + struct.pack('<IIIBBH', len(root_name) + 2, 0, 0, 16, 0, 0),
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


def test_inline_exports_and_explicit_pointer_graph_are_separate():
    data, rows, _ = fixture()
    model = Model(data)
    assert model.export_offset('root') == 0
    assert model.data_words(0, 4) == (0, 0, 0, 0)
    assert model.local_pointer(0, 16) == 0
    assert model.pointers[4] == {'symbol': 'known-data', 'imported': True, 'target': None}
    with pytest.raises(ModelError, match='explicitly resolved data library'):
        model.local_pointer(4, 1)
    with pytest.raises(ModelError, match='no pointer relocation'):
        model.local_pointer(8, 1)
    with pytest.raises(ModelError, match='Missing model data export'):
        model.export_offset('known-data')
    # A one-past relocation is valid ELF metadata, but cannot be dereferenced.
    modified = bytearray(data)
    struct.pack_into('<I', modified, rows[1][4], 16)
    end = Model(bytes(modified))
    assert end.pointers[0]['target'] == 16
    with pytest.raises(ModelError, match='data range exceeds'):
        end.local_pointer(0, 1)


@pytest.mark.parametrize('offset,size', [(-1, 4), (16, 1), (False, 4), (0, -1), (0, 2**64)])
def test_pointer_reads_cannot_escape_the_data_section(offset, size):
    model = Model(fixture()[0])
    with pytest.raises(ModelError):
        model.local_pointer(offset, size)


def bone_fixture(indices=(0, 1)):
    data, rows, _ = fixture('__Bone:::root.root', '__Bone:::root.hand')
    data = bytearray(data)
    struct.pack_into('<I', data, rows[4][4] + 16 + 8, 4)
    struct.pack_into('<IIIBBH', data, rows[4][4] + 32,
                     len('__Bone:::root.root') + 2, 12, 4, 17, 0, 1)
    struct.pack_into('<II', data, rows[5][4], 8, 1 << 8 | 2)
    struct.pack_into('<I', data, rows[1][4], indices[0])
    struct.pack_into('<I', data, rows[1][4] + 12, indices[1])
    return bytes(data), rows


def test_bone_index_inspection_does_not_claim_full_rig_compatibility():
    data, _ = bone_fixture()
    report = Model(data).metadata()
    assert report['bone_indices'] == {'__Bone:::root.hand': 1, '__Bone:::root.root': 0}
    assert report['bone_index_map_only'] is True
    assert report['runtime_ready'] is False
    assert 'eagl-geometry-skeleton-material-validation' in report['pending']


@pytest.mark.parametrize('indices', [(0, 0), (0, 2), (1, 2), (0, 0xffffffff)])
def test_bone_indices_reject_aliases_and_gaps(indices):
    data, _ = bone_fixture(indices)
    with pytest.raises(ModelError, match='unique and contiguous'):
        Model(data).bone_indices()


def test_bone_index_cannot_be_an_imported_pointer():
    data, rows = bone_fixture()
    data = bytearray(data)
    struct.pack_into('<I', data, rows[5][4], 0)
    with pytest.raises(ModelError, match='bone index field'):
        Model(bytes(data)).bone_indices()


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
