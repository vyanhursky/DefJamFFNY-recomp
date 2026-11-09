"""Packed motion conversion, independent storage checks and bounded selection."""
from dataclasses import replace
import random
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_assets import AssetError
from fighter_motion_records import PackedRecord
from fighter_motion import MotionIndex
from test_fighter_motion import stream, table, chunk


@pytest.mark.parametrize('kind,size,native', [('move', 32, 64), ('core', 64, 232), ('parameter', 39, 136)])
def test_random_wire_roundtrip_and_zero_filled_native_gaps(kind, size, native):
    rng = random.Random(904)
    for _ in range(200):
        data = rng.randbytes(size)
        decoded = PackedRecord.decode(kind, data)
        assert decoded.encode() == data
        output = decoded.native_bytes()
        assert len(output) == native
        gaps = {'move': (14, 15, 43), 'core': (155,), 'parameter': (134, 135)}[kind]
        assert all(output[offset] == 0 for offset in gaps)
    assert PackedRecord.decode(kind, bytes(size)).native_bytes() == bytes(native)


def test_move_maxima_signed_byte_sentinel_float_scale_and_tail():
    record = PackedRecord.decode('move', bytes([255]) * 32)
    output = record.native_bytes()
    assert struct.unpack_from('<H', output)[0] == 255
    assert output[2:4] == bytes([63, 255])
    assert output[4:14] == bytes([127, 15, 7, 7, 31, 31, 31, 31, 7, 15])
    assert output[16:36] == bytes.fromhex('9a99c940') * 5  # float32(63 * float32(.1))
    assert output[36:43] == bytes([15, 31, 15, 31, 15, 7, 63])
    assert struct.unpack_from('<II6H', output, 44) == (0xffffffff, 0xffffffff, 255, 1023, 127, 65535, 4095, 4095)
    assert record.tail == 63
    assert replace(record, tail=0).native_bytes() == output
    assert replace(record, tail=0).encode()[-1] == 192
    # Positive and negative edges of the signed six-bit field.
    for raw, expected in ((31, 31), (32, 224), (0, 0)):
        values = list(record.values); values[2] = raw
        assert replace(record, values=tuple(values)).native_bytes()[3] == expected


def test_core_maxima_sentinel_and_fixed_array_boundaries():
    output = PackedRecord.decode('core', bytes([255]) * 64).native_bytes()
    assert struct.unpack_from('<5I', output) == (7, 0xffffffff, 0xffffffff, 31, 31)
    assert struct.unpack_from('<5I', output, 20) == (3, 3, 7, 7, 7)
    assert struct.unpack_from('<17I', output, 40) == (15,) * 17
    assert output[108:155] == bytes([63]) * 47 and output[155] == 0
    assert struct.unpack_from('<8I', output, 156) == (7,) * 8
    assert struct.unpack_from('<6I', output, 188) == (127,) * 6
    assert struct.unpack_from('<4I2H', output, 212) == (255, 255, 255, 255, 65535, 65535)


def test_parameter_wire_order_conditional_sentinel_and_native_float_scale():
    record = PackedRecord.decode('parameter', bytes([255]) * 39)
    output = record.native_bytes()
    assert record.tail == 1
    assert struct.unpack_from('<3I', output) == (2047, 2047, 127)
    assert struct.unpack_from('<2I', output, 0x30) == (0xffffffff, 0xffffffff)
    assert struct.unpack_from('<2I', output, 0x44) == (2047, 2047)
    assert output[0x78:0x84] == bytes.fromhex('33332340') * 3
    fields = {field.offset: i for i, field in enumerate(record.layout[0])}
    values = list(record.values); values[fields[0x44]] = 0
    changed = replace(record, values=tuple(values))
    assert struct.unpack_from('<I', changed.native_bytes(), 0x48)[0] == 0xffffffff
    values[fields[0x48]] = 2046
    assert struct.unpack_from('<I', replace(record, values=tuple(values)).native_bytes(), 0x48)[0] == 2046
    # First eleven wire bits belong to +30; leading native group comes last.
    first = (1 << (312 - 11)).to_bytes(39, 'big')
    decoded = PackedRecord.decode('parameter', first).native_bytes()
    assert struct.unpack_from('<I', decoded, 0x30)[0] == 1 and decoded[:0x30] == bytes(0x30)


@pytest.mark.parametrize('value', [-1, 256, True, 1.0, None])
def test_record_refuses_noninteger_or_out_of_range_values(value):
    record = PackedRecord.decode('move', bytes(32))
    with pytest.raises(AssetError, match='bit width'):
        replace(record, values=(value,) + record.values[1:]).native_bytes()


@pytest.mark.parametrize('kind,data', [('move', b''), ('core', bytes(63)), ('move', bytes(33)),
                                     ('core', bytearray(64)), ('unknown', bytes(32))])
def test_record_requires_exact_wire_envelope(kind, data):
    with pytest.raises(AssetError):
        PackedRecord.decode(kind, data)


def test_record_refuses_wrong_field_count_or_tail():
    record = PackedRecord.decode('move', bytes(32))
    for bad in (replace(record, values=()), replace(record, values=list(record.values)),
                replace(record, tail=64), replace(record, tail=-1), replace(record, tail=True),
                replace(PackedRecord.decode('core', bytes(64)), tail=1)):
        with pytest.raises(AssetError): bad.encode()


def test_motion_index_selects_actual_partition_and_core_offsets():
    a, b = table(moves=2), table(moves=4)
    a[0] = a[0][:-32] + bytes([255]) * 32
    b[0] = b[0][:-32] + bytes([127]) * 32
    data = stream(a + b + [chunk(b'WPAR', bytes([255]) * 64), chunk(b'WWAZ', bytes(780))], cores=0)
    index = MotionIndex(data)
    assert index.record('move', 1).encode() == bytes([255]) * 32
    assert index.record('move', 3, 1).encode() == bytes([127]) * 32
    assert index.record('core', 0).encode() == bytes([255]) * 64
    assert not index.record('core', 0).metadata()['semantic_links_validated']
    for args in [('move', 2), ('move', -1), ('move', True), ('move', 0, 2),
                 ('move', 0, True), ('core', 1), ('core', 0, 1), ('other', 0)]:
        with pytest.raises(AssetError): index.record(*args)


def test_motion_record_cli_returns_raw_fields_and_bounded_errors(tmp_path, monkeypatch, capsys):
    import json
    from test_fighter_probe import driver
    cli = driver(tmp_path, monkeypatch).registry
    path = tmp_path / 'motion.dat'; path.write_bytes(stream())
    monkeypatch.setattr(sys, 'argv', ['fighter-registry.py', 'inspect-motion-record', str(path),
                                    '--kind', 'core', '--index', '0'])
    assert cli.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert len(report['fields']) == 94 and not report['runtime_ready']
    monkeypatch.setattr(sys, 'argv', sys.argv[:-1] + ['2'])
    assert cli.main() == 1
    assert 'exceeds table' in json.loads(capsys.readouterr().out)['error']['message']
